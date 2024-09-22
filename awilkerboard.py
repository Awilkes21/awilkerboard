import os
import json
import discord
import logging
import asyncio
from discord.ext import commands
from discord import app_commands
from config import token

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
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:  # Ignore bot reactions
        return

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



@bot.tree.command(name="set-channel", description="Sets the default channel for the bot")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel_name = "The name of the channel the bot will write to")
async def set_channel(interaction: discord.Interaction, channel_name: str):
    if channel_name is None:
        await interaction.response.send_message("Error: Please provide a channel name.", ephemeral=True)
        return

    channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
    if channel:
        config['target_channel_id'] = channel.id
        save_config(config)
        await interaction.response.send_message(f"Target channel set to {channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: Channel '{channel_name}' not found.", ephemeral=True)

@bot.tree.command(name="set-reaction", description="Sets a rule for the bot")
@commands.has_permissions(administrator=True)
@app_commands.describe(emoji = "The emoji to track", threshold = "The number of reactions required to trigger the message", message = "The message to send when the threshold is reached")
async def track_reaction(interaction: discord.Interaction, emoji: str, threshold: int, message: str):
    if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
        await interaction.response.send_message("Error: Please provide a single emoji. Custom emojis are also accepted.", ephemeral=True)
        return
    
    if threshold <= 0:
        await interaction.response.send_message("Error: The threshold must be a positive number.", ephemeral=True)
        return
    
    # Update configuration
    config['emoji_configs'][emoji] = {
        'threshold': threshold,
        'message': message
    }
    save_config(config)

    await interaction.response.send_message(f"Reaction {emoji} is now being tracked with threshold {threshold} and custom message.", ephemeral=True)


@bot.tree.command(name="remove-reaction", description="Given an emote, remove its tracking rule")
@commands.has_permissions(administrator=True)
@app_commands.describe(emoji = "The emoji to stop tracking")
async def untrack_reaction(interaction: discord.Interaction, emoji: str):
    if not emoji:
        await interaction.response.send_message("Error: Please provide an emote.", ephemeral=True)
        return

    if emoji in config['emoji_configs']:
        del config['emoji_configs'][emoji]
        save_config(config)
        await interaction.response.send_message(f"Reaction {emoji} is no longer being tracked.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: Reaction {emoji} was not being tracked.", ephemeral=True)

@bot.tree.command(name="show-config", description="Show how the bot is currently configured")
@commands.has_permissions(administrator=True)
async def show_config(interaction: discord.Interaction):
    try:
        channel = bot.get_channel(config['target_channel_id'])
        channel_mention = channel.mention if channel else "Not set"
    except AttributeError:
        channel_mention = "Invalid channel ID"

    
    # Create an embed with the current configuration
    embed = discord.Embed(title="Current Configuration", color=discord.Color.blue())
    embed.add_field(name="Target Channel", value=channel_mention, inline=False)
    
    if not config['emoji_configs']:
        embed.add_field(name="Tracked Reactions", value="No reactions are currently being tracked.", inline=False)
    else:
        for emoji, emoji_config in config['emoji_configs'].items():
            embed.add_field(name=emoji, value=f"Threshold: {emoji_config['threshold']}, Message: {emoji_config['message']}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear-awilkerboard-messages", description="Clears all messages except for those generated by reactions")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel = "The channel to clear messages from (defaults to the current channel)")
async def clear_bot_messages(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    
    config_prefixes = [
        "Target channel set to",
        "Reaction",
        "Current Configuration",
        "Error:"  # Include error messages related to configuration
    ]

    await interaction.response.defer()  # Defer the interaction to allow time for processing
    
    async for message in target_channel.history(limit=None):
        if message.author == bot.user:
            # Check if the message should be preserved
            if not message.reference or message.reference.resolved.author != bot.user:
                should_preserve = (
                    any(prefix in message.content for prefix in config_prefixes) or
                    any(f"{emoji} reacted with" in message.content for emoji in config['emoji_configs']) or
                    any(emoji_config['message'].split('{')[0] in message.content for emoji_config in config['emoji_configs'].values())
                )
                
                if should_preserve:
                    print(f"Preserving message: {message.content[:50]}...")
                else:
                    print(f"Deleting message: {message.content[:50]}...")
                    await message.delete()
                    await asyncio.sleep(1)  


# Run the bot
bot.run(token, log_handler=handler)
