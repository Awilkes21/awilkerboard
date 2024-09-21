import os
import json
import discord
from discord.ext import commands

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

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
async def set_channel(ctx, *, channel_name):
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if channel:
        config['target_channel_id'] = channel.id
        save_config(config)
        await ctx.send(f"Target channel set to {channel.mention}")
    else:
        await ctx.send(f"Channel '{channel_name}' not found. Please provide a valid channel name.")

@bot.command()
@commands.has_permissions(administrator=True)
async def track_reaction(ctx, emoji: str, threshold: str, *, message):
    try:
        threshold_value = int(threshold)
        if threshold_value <= 0:
            await ctx.send("The threshold must be a positive number.")
            return
        
        if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
            await ctx.send("Please provide a single emoji. Custom emojis are also accepted.")
            return
        
        config['emoji_configs'][emoji] = {
            'threshold': threshold_value,
            'message': message
        }
        save_config(config)
        await ctx.send(f"Reaction {emoji} is now being tracked with threshold {threshold_value} and custom message.")
    except ValueError:
        await ctx.send("Please provide a valid number for the threshold. Usage: !track_reaction <emoji> <threshold> <message>")

@bot.command()
@commands.has_permissions(administrator=True)
async def untrack_reaction(ctx, emoji: str):
    if emoji in config['emoji_configs']:
        del config['emoji_configs'][emoji]
        save_config(config)
        await ctx.send(f"Reaction {emoji} is no longer being tracked.")
    else:
        await ctx.send(f"Reaction {emoji} was not being tracked.")

@bot.command()
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    channel = bot.get_channel(config['target_channel_id'])
    channel_mention = channel.mention if channel else "Not set"
    
    embed = discord.Embed(title="Current Configuration", color=discord.Color.blue())
    embed.add_field(name="Target Channel", value=channel_mention, inline=False)
    
    for emoji, emoji_config in config['emoji_configs'].items():
        await ctx.send(embed=embed)

# Run the bot
bot.run(os.getenv('AWILKERBOARD_TOKEN'))
