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
    'reaction_threshold': 5,
    'target_channel_id': None,
    'trigger_emoji': '👎'
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
    if str(reaction.emoji) == config['trigger_emoji']:
        if reaction.count >= config['reaction_threshold']:
            target_channel = bot.get_channel(config['target_channel_id'])
            if target_channel:
                message = f"A message in {reaction.message.channel.mention} has reached {reaction.count} {reaction.emoji} reactions!\n"
                message += f"Original message: {reaction.message.jump_url}"
                await target_channel.send(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_threshold(ctx, threshold: int):
    config['reaction_threshold'] = threshold
    save_config(config)
    await ctx.send(f"Reaction threshold set to {threshold}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_channel(ctx, *, channel_name):
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if channel:
        config['target_channel_id'] = channel.id
        save_config(config)
        await ctx.send(f"Target channel set to {channel.mention}")
    else:
        await ctx.send(f"Channel '{channel_name}' not found")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_emoji(ctx, emoji):
    config['trigger_emoji'] = emoji
    save_config(config)
    await ctx.send(f"Trigger emoji set to {emoji}")

@bot.command()
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    channel = bot.get_channel(config['target_channel_id'])
    channel_mention = channel.mention if channel else "Not set"
    await ctx.send(f"Current configuration:\n"
                   f"Reaction threshold: {config['reaction_threshold']}\n"
                   f"Target channel: {channel_mention}\n"
                   f"Trigger emoji: {config['trigger_emoji']}")

# Run the bot
bot.run(os.getenv('AWILKERBOARD_TOKEN'))
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
    'reaction_threshold': 5,
    'target_channel_id': None,
    'trigger_emoji': '👎'
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
    if str(reaction.emoji) == config['trigger_emoji']:
        if reaction.count >= config['reaction_threshold']:
            target_channel = bot.get_channel(config['target_channel_id'])
            if target_channel:
                message = f"A message in {reaction.message.channel.mention} has reached {reaction.count} {reaction.emoji} reactions!\n"
                message += f"Original message: {reaction.message.jump_url}"
                await target_channel.send(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_threshold(ctx, threshold: str):
    try:
        threshold_value = int(threshold)
        if threshold_value <= 0:
            await ctx.send("The threshold must be a positive number.")
            return
        config['reaction_threshold'] = threshold_value
        save_config(config)
        await ctx.send(f"Reaction threshold set to {threshold_value}")
    except ValueError:
        await ctx.send("Please provide a valid number for the threshold. Usage: !set_threshold <number>")

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
async def set_emoji(ctx, emoji: str):
    if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
        await ctx.send("Please provide a single emoji. Custom emojis are also accepted.")
        return
    config['trigger_emoji'] = emoji
    save_config(config)
    await ctx.send(f"Trigger emoji set to {emoji}")

@bot.command()
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    channel = bot.get_channel(config['target_channel_id'])
    channel_mention = channel.mention if channel else "Not set"
    await ctx.send(f"Current configuration:\n"
                   f"Reaction threshold: {config['reaction_threshold']}\n"
                   f"Target channel: {channel_mention}\n"
                   f"Trigger emoji: {config['trigger_emoji']}")

# Run the bot
bot.run(os.getenv('AWILKERBOARD_TOKEN'))
