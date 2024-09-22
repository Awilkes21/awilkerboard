# awilkerboard
Discord bot that tracks reactions and announces once a threshold is reached

# Commands
## set-reaction
Tracks a specific emoji's reactions. When the reaction count exceeds the specified threshold, the bot sends a custom message to the target channel.

Usage:
```/track_reaction <emoji> <threshold> <channel>```

Example:
```/track_reaction 👍 5 general```

## remove-reaction
Stops tracking a specific emoji's reactions. Deletes the rule

Usage:
```/untrack_reaction <emoji>```

Example:
```/untrack_reaction 👍```

## show_config
Displays the current bot configuration, including the target channel and tracked reactions.

Usage:
```/show_config```

## clear-awilkerboard-messages

Deletes messages sent by the bot in the specified channel. If no channel specified, uses the channel the command was sent in.

Usage:

```/clear_bot_messages [<channel>]```

Example:
```/clear_bot_messages general```

# Events
## on_ready
Triggers when the bot successfully connects to Discord.

## on_reaction_add
Triggered when a user adds a reaction to a message. If the reaction matches a tracked emoji and meets the threshold, the bot sends a configured message to the target channel.

# Running the Bot
To run the bot, you need to have the token set in a config.py

