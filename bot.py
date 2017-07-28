import discord
from discord.ext import commands
import asyncio
import json
import os.path
import time
import math
import re
import threading
from multiprocessing import Pool
import traceback
import datetime

bot = commands.Bot(command_prefix='$', description="I'm a bot that manages server mutes.")

history = {}
punishments = {}
settings = {}

settingsFile = "settings.json"
punishmentsFile = "punishments.json"
historyFile = "history.json"


def get_json_file(file):
    if os.path.isfile(file):
        with open(file) as data_file:
            try:
                data = json.load(data_file)
            except json.decoder.JSONDecodeError:
                data = {}
    else:
        data = {}
    return data

def put_json_file(file, data):
    with open(file, 'w+') as outfile:
        json.dump(data, outfile)
    return True
    
def verify_punishments():
    global punishments, punishmentsFile
    
    changed = False
    for member in bot.get_all_members():
        if member.id in punishments and member.voice.mute is False:
            del punishments[member.id]
            changed = True
    
    if changed:
        put_json_file(punishmentsFile, punishments)


async def check_punishments():
    global punishments, punishmentsFile
    
    now = int(time.time())
    changed = False
    
    for k,v in list(punishments.items()):
        if v < now:
            changed = True
            member = discord.utils.find(lambda m: m.id == k, bot.get_all_members())
            if member is not None:
                await unballpit_member(member)
                try:
                    if settings['logs'] is not None:
                        logChannel = bot.get_channel(settings['logs'])
                        await bot.send_message(logChannel, "**{0}**'s ballpit has been lifted!".format(member.mention))
                    
                except discord.Forbidden as ex:
                    print("Exception while trying to remove ballpit: {}".format(str(ex)))
                except Exception as ex:
                    print("Exception while trying to remove ballpit: {}".format(str(ex)))

    if changed:
        put_json_file(punishmentsFile, punishments)
     

async def can_moderate(user):
    can_mod = False
    
    roles = user.roles if isinstance(user.roles, list) else [user.roles]
    
    for role in roles:
        if role.permissions.administrator is True or role.permissions.manage_server is True:
            can_mod = True
            break
            
    return can_mod

async def can_mute(user):
    can_mute = False
    
    roles = user.roles if isinstance(user.roles, list) else [user.roles]
    
    for role in roles:
        if role.permissions.mute_members is True:
            can_mute = True
            break
            
    return can_mute

async def has_punishment(member):
    global punishments
    
    if member.id in punishments.keys():
        return True
    
    if member.voice.mute is True:
        return True
        
    return False

async def ballpit_member(member, amount, reason):
    global settings, punishments, punishmentsFile, history, historyFile
    
    if reason is None:
        reason = 'No reason given'
    
    await bot.server_voice_state(member=member, mute=True)
    punishments[member.id] = int(time.time()) + amount
    
    if member.id not in history:
        history[member.id] = []
    
    history[member.id].append([int(time.time()), amount, reason])
    
    put_json_file(punishmentsFile, punishments)
    put_json_file(historyFile, history)
    
    def send():        
        asyncio.ensure_future(check_punishments(), loop=bot.loop)
    
    bot.loop.call_later(amount + 1, send)
    
    if settings['ballpit'] is not None:
        try:
            channel = bot.get_channel(settings['ballpit'])
            await bot.move_member(member, channel)
        except discord.Forbidden:
            print("I don't have permission to move members to other channels")


async def unballpit_member(member):
    global settings, punishments, punishmentsFile
    
    await bot.server_voice_state(member=member, mute=False)
    del punishments[member.id]
    
    await bot.send_message(member, "Your ballpit has been lifted!")
    
    put_json_file(punishmentsFile, punishments)
    return True


@bot.event
async def on_ready():
    global history, settings, punishments, historyFile, settingsFile, punishmentsFile
    
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    punishments = get_json_file(punishmentsFile)
    settings = get_json_file(settingsFile)
    history = get_json_file(historyFile)
    verify_punishments()
    await check_punishments()

    
@bot.event
async def on_member_remove(member):
    print('Member removed: %s' % member)

@bot.event
async def on_member_ban(member):
    print('Member banned: %s' % member)


@bot.command(pass_context=True, help="manage settings for bot")
async def config(ctx, param=None, value=None):
    global settings, settingsFile
    
    """Manage settings for this bot."""
    
    realValue = value
    
    if param is None:
        for k,v in settings.items():
            await bot.say("*{0}* = **{1}**".format(k, v))
    else:
        param = param.lower()

        if param in settings.keys():
            if value is not None:
                if param == 'ballpit':
                    if value.lower() == 'none':
                        realValue = None
                    else:
                        try:
                            if len(ctx.message.channel_mentions) == 1:
                                channel = ctx.message.channel_mentions[0]
                            else:
                                channel = discord.utils.find(lambda c: c.name.lower() == value.lower(), bot.get_all_channels())
                                
                            if channel is None:
                                await bot.say("Channel not found: **{0}**".format(value))
                                return
                            elif channel.type is not discord.ChannelType.voice:
                                await bot.say("**{0}** is not a voice channel.".format(channel.mention))
                            
                            realValue = channel.id
                            value = channel.name
                            
                        except discord.NotFound:
                            await bot.say("Channel not found: **{0}**".format(value))
                            return
                        except Exception as ex:
                            print("Exception trying to find channel: {}".format(ex))
                if param == 'logs':                
                    if len(ctx.message.channel_mentions) == 1:
                        channel = ctx.message.channel_mentions[0]
                    else:
                        channel = discord.utils.find(lambda c: c.name.lower() == value.lower(), bot.get_all_channels())
                    
                    if channel is None:
                        await bot.say("Channel not found: **{0}**".format(value))
                        return
                    elif channel.type is not discord.ChannelType.text:
                        await bot.say("**{0}** is not a text channel.".format(channel.mention))
                    
                    realValue = channel.id
                    value = channel.mention
                    
                        
                settings[param] = realValue
                put_json_file(settingsFile, settings)
            await bot.say("*{0}* = **{1}**".format(param, value))
        else:
            await bot.say("Configuration not found: **{}**".format(param))



@bot.command(pass_context=True, help="server mutes a user")
async def ballpit(ctx, who, amount='30m', *, reason=None):
    global this_map, player_count, last_map_change
    
    """Mutes a member for a certain amount of time."""
    
    await bot.send_typing(ctx.message.channel)
    has_perm = await can_mute(ctx.message.author)
    
    if amount is not None and re.sub("s|m|h|d", "", amount).isdigit() is False:
        await bot.say("**To use the ballpit command:**\n{0}ballpit <user> <time=30m> [reason]".format(bot.command_prefix))
        return
    

    reason_str = ' because "{0}"'.format(reason) if reason is not None else ""
    
    if has_perm is not True:
        await bot.say("You don't have permission to mute, **{}**".format(ctx.message.author.mention))
        return
        
    match = None
    cancelled = False
    
    if len(ctx.message.mentions) == 1:
        member = ctx.message.mentions[0]
    else:
        member = discord.utils.find(lambda m: m.name.lower() == who.lower(), ctx.message.channel.server.members)
        
    def nameCheck(msg):
        nonlocal member, matches, match, cancelled
        if msg.content.lower() in ['y', 'yes']:
            member = match
        elif msg.content.lower() in ['n', 'no']:
            member = None
        elif msg.content.lower() in ['c', 'cancel']:
            matches = []
            cancelled = True
        return msg

    print("Found member {}".format(member))

    tmpMessage = None
    if member is None:
        matches = list(filter(lambda m: who.lower() in m.name.lower(), ctx.message.channel.server.members))
        while member is None and len(matches) > 0 and cancelled is False:
            if tmpMessage is not None:
                await bot.delete_message(tmpMessage)
        
            match = matches[0]
            del matches[0]
            
            print("Found match {}".format(match))
            tmpMessage = await bot.say("Did you mean **{}**?\nAnswer 'Y' or 'N', or 'C' to cancel.".format(match.mention))
            await bot.wait_for_message(author=ctx.message.author, timeout=10, channel=ctx.message.channel, check=nameCheck)

        if member is None:
            if cancelled:
                await bot.say("Okay, nevermind then!")
            else:
                await bot.say("Could not find any member matching **{}**".format(who))
            return

    if member is None and cancelled is False:
        await bot.say("Okay, taking no action!")
        return
        
    if await has_punishment(member) is True:
        await bot.say("**{}** is already server-muted or has a punishment.".format(member.mention))
        return
    
    
    if tmpMessage is not None:
        await bot.delete_message(tmpMessage)

    timeAmount = None
    if re.compile("^\d+s|m|h|d$").search(amount) is not None:
        if re.compile("^\d+m$").search(amount):
            timeAmount = int(amount.replace("m", "")) * 60
        elif re.compile("^\d+h$").search(amount):
            timeAmount = int(amount.replace("h", "")) * 60 * 60
        elif re.compile("^\d+d$").search(amount):
            timeAmount = int(amount.replace("d", "")) * 60 * 60 * 24
        else:
            timeAmount = int(re.sub("[^0-9]+", "", amount.replace("s", "")))
    else:
        timeAmount = int(amount)
    
    confirmed = False
    if isinstance(timeAmount, int) or timeAmount.isdigit():
    
        def confirmCheck(msg):
            nonlocal confirmed
            if msg.content.lower() in ['y', 'yes']:
                confirmed = True
            return msg
                
    
        m, s = divmod(timeAmount, 60)
        h, m = divmod(m, 60)
        
        tmpMessage = await bot.say("Ballpit **{0}** for **{1}**{2}?\nAnswer 'Y' or 'N', or 'C' to cancel.".format(member.mention, "%d:%02d:%02d" % (h, m, s), reason_str))
        tmpMessage2 = await bot.wait_for_message(author=ctx.message.author, timeout=20, channel=ctx.message.channel, check=confirmCheck)
        
        try:
            await bot.delete_message(tmpMessage)
            await bot.delete_message(tmpMessage2)
        except discord.Forbidden as ex:
            print("Exception while trying to ballpit: {}".format(str(ex)))
        
        
        if confirmed is True:
            try:
                await ballpit_member(member, timeAmount, reason)
                await bot.say("**{0}** has been ballpitted for **{1}**{2}!".format(member.mention, "%d:%02d:%02d" % (h, m, s), reason_str))
                
                
            except discord.Forbidden as ex:
                print("Exception while trying to ballpit: {}".format(str(ex)))
                await bot.say("I don't have permission to mute members.")
            except Exception as ex:
                print("Exception while trying to ballpit: {}".format(str(ex)))
                traceback.print_exc()
                
            try:    
                if settings['logs'] is not None:
                    logChannel = bot.get_channel(settings['logs'])
                    await bot.send_message(logChannel, "**{0}** was ballpitted by **{1}** for **{2}**{3}!".format(member.mention, ctx.message.author.mention, "%d:%02d:%02d" % (h, m, s), reason_str))
            except discord.Forbidden as ex:
                print("Exception while trying to ballpit: {}".format(str(ex)))
                await bot.say("I don't have permission to post to log channel.")
                
        else:
            await bot.say("Okay, nevermind then!")
    else:
        await bot.say("Uh oh! Unable to parse time value: **{}**".format(timeAmount))
        return


@bot.command(pass_context=True, help="until your ballpit expires")
async def timeleft(ctx):
    global punishments
    
    if ctx.message.author.id in punishments:
        expires = punishments[ctx.message.author.id]
        timeleft = expires - int(time.time())
        m, s = divmod(timeleft, 60)
        h, m = divmod(m, 60)
        
        await bot.send_message(ctx.message.author, "Your ballpit expires in **%d:%02d:%02d**" % (h, m, s))
    else:
        add_info = " You may still have a server-mute for other reasons. Ask a moderator for more info." if ctx.message.author.voice.mute is True else ""
        await bot.send_message(ctx.message.author, "You are not ballpitted!{0}".format(add_info))


@bot.command(pass_context=True, help="list of punishments")
async def punishments(ctx, who=None):
    global history
    
    member = ctx.message.author
    
    if who is not None:
        match = None
        cancelled = False
        
        if len(ctx.message.mentions) == 1:
            member = ctx.message.mentions[0]
        else:
            member = discord.utils.find(lambda m: m.name.lower() == who.lower(), ctx.message.channel.server.members)
            
        def nameCheck(msg):
            nonlocal member, matches, cancelled
            if msg.content.lower() in ['y', 'yes']:
                member = match
            elif msg.content.lower() in ['n', 'no']:
                member = None
            elif msg.content.lower() in ['c', 'cancel']:
                matches = []
                cancelled = True
            return msg
    
        print("Found member {}".format(member))
    
        tmpMessage = None
        if member is None:
            matches = list(filter(lambda m: who.lower() in m.name.lower(), ctx.message.channel.server.members))
            while member is None and len(matches) > 0 and cancelled is False:
                if tmpMessage is not None:
                    await bot.delete_message(tmpMessage)
            
                match = matches[0]
                del matches[0]
                print("Found match {}".format(match))
                tmpMessage = await bot.say("Did you mean **{}**?\nAnswer 'Y' or 'N', or 'C' to cancel.".format(match.mention))
                await bot.wait_for_message(author=ctx.message.author, timeout=10, channel=ctx.message.channel, check=nameCheck)
    
            if member is None:
                if cancelled:
                    await bot.say("Okay, nevermind then!")
                else:
                    await bot.say("Could not find any member matching **{}**".format(who))
                return
    
        if member is None and cancelled is False:
            await bot.say("Okay, taking no action!")
            return
            
    if member.id not in history:
        if member == ctx.message.author:
            await bot.send_message(ctx.message.author, "You have no punishments, **{0}**. :clap:".format(member.mention))
        else:
            await bot.send_message(ctx.message.author, "**{0}** has no punishments. :clap:".format(member.mention))
        return
    
    my_punishments = history[member.id]
    my_punishment_list = []
    for item in my_punishments:
        ts = datetime.datetime.fromtimestamp(item[0]).strftime('%Y-%m-%d')
        m, s = divmod(item[1], 60)
        h, m = divmod(m, 60)
    
        reason = item[2]
        
        amount = "%d:%02d:%02d" % (h, m, s)
        my_punishment_list.append('[{0}] for {1} because *"{2}"*'.format(ts, amount, reason) if reason is not None else "")
    
    my_punishment_list.reverse()
    await bot.send_message(ctx.message.author, "Punishments for **{0}**:\n{1}".format(member.mention, "\n".join(my_punishment_list)))



@bot.command(pass_context=True, help="removes server mute")
async def unballpit(ctx, who, amount='30m'):
    global this_map, player_count, last_map_change
    
    """Removes a member's mute."""
    
    await bot.send_typing(ctx.message.channel)
    has_perm = await can_mute(ctx.message.author)
    
    if has_perm is not True:
        await bot.say("You don't have permission to mute, **{}**".format(ctx.message.author.mention))
        return
        
    match = None
    cancelled = False
    
    if len(ctx.message.mentions) == 1:
        member = ctx.message.mentions[0]
    else:
        member = discord.utils.find(lambda m: m.name.lower() == who.lower(), ctx.message.channel.server.members)
        
    def nameCheck(msg):
        nonlocal member, matches, cancelled
        if msg.content.lower() in ['y', 'yes']:
            member = match
        elif msg.content.lower() in ['n', 'no']:
            member = None
        elif msg.content.lower() in ['c', 'cancel']:
            matches = []
            cancelled = True
        return msg

    print("Found member {}".format(member))

    tmpMessage = None
    if member is None:
        matches = list(filter(lambda m: who.lower() in m.name.lower(), ctx.message.channel.server.members))
        while member is None and len(matches) > 0 and cancelled is False:
            if tmpMessage is not None:
                await bot.delete_message(tmpMessage)
        
            match = matches[0]
            del matches[0]
            print("Found match {}".format(match))
            tmpMessage = await bot.say("Did you mean **{}**?\nAnswer 'Y' or 'N', or 'C' to cancel.".format(match.mention))
            await bot.wait_for_message(author=ctx.message.author, timeout=10, channel=ctx.message.channel, check=nameCheck)

        if member is None:
            if cancelled:
                await bot.say("Okay, nevermind then!")
            else:
                await bot.say("Could not find any member matching **{}**".format(who))
            return

    if member is None and cancelled is False:
        await bot.say("Okay, taking no action!")
        return
        
    if await has_punishment(member) is False:
        await bot.say("**{}** is not ballpitted.".format(member.mention))
        return
    


    try:
        await unballpit_member(member)
        await bot.say("**{0}** is no longer ballpitted!".format(member.mention))
        
        
    except discord.Forbidden as ex:
       await bot.say("I don't have permission to unmute members.")
       
    try:
        if settings['logs'] is not None:
            logChannel = bot.get_channel(settings['logs'])
            await bot.send_message(logChannel, "**{0}**'s ballpit was removed by **{1}**!".format(member.mention, ctx.message.author.mention))
        
    except discord.Forbidden as ex:
       print("Exception while trying to unballpit: {}".format(str(ex)))
       traceback.print_exc()
       await bot.say("I don't have permission to post to log channel.")
            
    
    

bot.run('MjE0NDA4Njk0MTY5OTkzMjE2.CpIjMA.fXk2Z8Q2aNwGWEA62EBXmXUHWLI')
