import os
import json
import discord
import logging
from discord.ext import commands

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Configuration file
CONFIG_FILE = 'bot_config.json'

# Default configuration
DEFAULT_CONFIG = {
    'target_channel_id': None,
    'emoji_configs': {}
}

# Load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

# Save configuration
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_reaction_add(reaction, user):
    emoji = str(reaction.emoji)
    if emoji in config['emoji_configs']:
        emoji_config = config['emoji_configs'][emoji]
        target_channel = bot.get_channel(config['target_channel_id'])
        if target_channel:
            message = emoji_config['message'].format(
                channel=reaction.message.channel.mention,
                count=reaction.count,
                emoji=emoji,
                url=reaction.message.jump_url
            )
            await target_channel.send(message)


@bot.command()
@commands.has_permissions(administrator=True)
async def set_channel(ctx, *, channel_name=None):
    if channel_name is None:
        await ctx.send("Error: Please provide a channel name. Usage: !set_channel <channel_name>")
        return

    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if channel:
        config['target_channel_id'] = channel.id
        save_config(config)
        await ctx.send(f"Target channel set to {channel.mention}")
    else:
        await ctx.send(f"Error: Channel '{channel_name}' not found. Please provide a valid channel name.")

@bot.command()
@commands.has_permissions(administrator=True)
async def track_reaction(ctx, emoji: str = None, threshold: str = None, *, message=None):
    if emoji is None or threshold is None or message is None:
        await ctx.send("Error: Invalid syntax. Usage: !track_reaction <emoji> <threshold> <message>")
        return

    try:
        threshold_value = int(threshold)
        if threshold_value <= 0:
            await ctx.send("Error: The threshold must be a positive number.")
            return
        
        if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
            await ctx.send("Error: Please provide a single emoji. Custom emojis are also accepted.")
            return
        
        config['emoji_configs'][emoji] = {
            'threshold': threshold_value,
            'message': message
        }
        save_config(config)
        await ctx.send(f"Reaction {emoji} is now being tracked with threshold {threshold_value} and custom message.")
    except ValueError:
        await ctx.send("Error: Please provide a valid number for the threshold. Usage: !track_reaction <emoji> <threshold> <message>")

@bot.command()
@commands.has_permissions(administrator=True)
async def untrack_reaction(ctx, emoji: str = None):
    if emoji is None:
        await ctx.send("Error: Please provide an emoji. Usage: !untrack_reaction <emoji>")
        return

    if emoji in config['emoji_configs']:
        del config['emoji_configs'][emoji]
        save_config(config)
        await ctx.send(f"Reaction {emoji} is no longer being tracked.")
    else:
        await ctx.send(f"Error: Reaction {emoji} was not being tracked.")

@bot.command()
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    try:
        channel = bot.get_channel(config['target_channel_id'])
        channel_mention = channel.mention if channel else "Not set"
    except AttributeError:
        channel_mention = "Invalid channel ID"

    
    embed = discord.Embed(title="Current Configuration", color=discord.Color.blue())
    embed.add_field(name="Target Channel", value=channel_mention, inline=False)
    
    if not config['emoji_configs']:
        embed.add_field(name="Tracked Reactions", value="No reactions are currently being tracked.", inline=False)
    else:
        for emoji, emoji_config in config['emoji_configs'].items(): 
            embed.add_field(name=emoji, value=f"Threshold: {emoji_config['threshold']}, Message: {emoji_config['message']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_bot_messages(ctx, channel: discord.TextChannel = None):
    target_channel = channel or ctx.channel
    
    config_prefixes = [
        "Target channel set to",
        "Reaction",
        "Current Configuration",
        "Error:"  # Include error messages related to configuration
    ]
    
    async with ctx.typing():
        async for message in target_channel.history(limit=None):
            if message.author == bot.user:
                if not message.reference or message.reference.resolved.author != bot.user:
                    should_preserve = any(prefix in message.content for prefix in config_prefixes) or \
                                      any(f"{emoji} reacted with" in message.content for emoji in config['emoji_configs']) or \
                                      any(emoji_config['message'].split('{')[0] in message.content for emoji_config in config['emoji_configs'].values())
                    
                    if should_preserve:
                        print(f"Preserving message: {message.content[:50]}...")
                    else:
                        print(f"Deleting message: {message.content[:50]}...")
                        await message.delete()

    # Delete the command message itself
    await ctx.message.delete()




# Run the bot
bot.run(os.getenv('AWILKERBOARD_TOKEN'), log_handler=handler)
