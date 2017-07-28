# discord-punisher-bot
A bot that manages mutes and moves members to a "ballpit" channel

# Instructions
This bot requires the following writable files in same directory:

"history.json", "punishments.json", "settings.json"


Supported commands:

### $config `key` `[value]`
Example settings:
`$config ballpit #sandbox`
`$config logs #admin`

### $ballpit `keyword, username, or @mention` `time=1,1s,1m,1h,1d` [`reason`]

### $unballpit `keyword, username, or @mention`


### $punishments [`keyword, username, or @mention`]

### $timeleft
