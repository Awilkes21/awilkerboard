import os
import json
import discord
import logging
import asyncio
from datetime import datetime, timedelta
import pytz
from discord.utils import format_dt
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

# Dictionary to store message IDs by emote
sent_messages = {}

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:  # Ignore bot reactions
        return

    if reaction.message.author == bot.user:  # Ignore reactions to messages sent by the bot
        return

    emoji = str(reaction.emoji)
    if emoji in config['emoji_configs']:
        emoji_config = config['emoji_configs'][emoji]
        target_channel = bot.get_channel(emoji_config['target_channel_id'])  # Get the specific target channel for this emoji
        threshold = emoji_config['threshold']

        if target_channel:
            message_content = (
                f"**{reaction.count} {emoji} |** "
                f"[{reaction.message.channel.name}]({reaction.message.jump_url})\n\n"
            )

            # Convert the message time to the user's timezone
            created_at = reaction.message.created_at
            user_timezone = pytz.timezone('America/New_York')  # Replace with actual user's timezone
            local_time = created_at.astimezone(user_timezone)

            # Determine the message time format
            now = datetime.now(user_timezone)
            if local_time.date() == now.date():
                message_time = "Today at " + local_time.strftime("%I:%M %p")
            elif local_time.date() == (now - timedelta(days=1)).date():
                message_time = "Yesterday at " + local_time.strftime("%I:%M %p")
            else:
                message_time = local_time.strftime("%m/%d/%Y %I:%M %p")  # mm/dd/yyyy hh:mm AM/PM

            # Initialize user count if it doesn't exist
            if emoji not in emoji_config:
                emoji_config[emoji] = {'user_counts': {}}

            if user.id not in emoji_config['user_counts']:
                emoji_config['user_counts'][user.id] = 0

            # Check the current count and threshold
            current_count = emoji_config['user_counts'][user.id]

            # Increment or decrement the user's count based on the reaction count
            if reaction.count >= threshold and current_count == 0:
                emoji_config['user_counts'][user.id] += 1  # Increment on reaching threshold
            elif reaction.count < threshold and current_count > 0:
                emoji_config['user_counts'][user.id] -= 1  # Decrement if it drops below threshold

            # Check if a message for this emoji already exists
            if emoji in sent_messages:
                sent_message = await target_channel.fetch_message(sent_messages[emoji])
                if reaction.count < threshold:
                    await sent_message.delete()  # Delete the message if below the threshold
                    del sent_messages[emoji]  # Remove the entry from the dictionary
                else:
                    await sent_message.edit(content=message_content)
                    await sent_message.set_footer(text=message_time)
            else:
                if reaction.count >= threshold:
                    # Create the embed for the original message
                    embed = discord.Embed(
                        description=reaction.message.content,
                        color=discord.Color.blue()
                    )
                    embed.set_author(name=reaction.message.author.name, icon_url=reaction.message.author.avatar.url)
                    embed.set_footer(text=message_time)

                    # Send the message and embed
                    sent_message = await target_channel.send(message_content, embed=embed)
                    sent_messages[emoji] = sent_message.id  # Store the sent message ID
                    await sent_message.add_reaction(emoji)


# Update the track_reaction command
@bot.tree.command(name="set-reaction", description="Sets a rule for the bot with a specific target channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(emoji="The emoji to track", threshold="The number of reactions required to trigger the message", channel_name="The name of the channel to send the message")
async def track_reaction(interaction: discord.Interaction, emoji: str, threshold: int, channel_name: str):
    if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
        await interaction.response.send_message("Error: Please provide a single emoji. Custom emojis are also accepted.", ephemeral=True)
        return

    if threshold <= 0:
        await interaction.response.send_message("Error: The threshold must be a positive number.", ephemeral=True)
        return

    # Get the target channel
    channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
    if not channel:
        await interaction.response.send_message(f"Error: Channel '{channel_name}' not found.", ephemeral=True)
        return

    # Update configuration
    config['emoji_configs'][emoji] = {
        'threshold': threshold,
        'target_channel_id': channel.id  # Store the target channel ID with the emoji config
    }
    save_config(config)

    await interaction.response.send_message(f"Reaction {emoji} is now being tracked with threshold {threshold} in {channel.mention}.", ephemeral=True)


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
    # Create an embed with the current configuration
    embed = discord.Embed(title="Current Configuration", color=discord.Color.blue())

    if not config['emoji_configs']:
        embed.add_field(name="Tracked Reactions", value="No reactions are currently being tracked.", inline=False)
    else:
        for emoji, emoji_config in config['emoji_configs'].items():
            target_channel = bot.get_channel(emoji_config['target_channel_id'])
            channel_mention = target_channel.mention if target_channel else "Channel not found"
            embed.add_field(name=emoji, value=f"Threshold: {emoji_config['threshold']}, Target Channel: {channel_mention}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear-awilkerboard-messages", description="Clears all messages except for those generated by reactions")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel to clear messages from (defaults to the current channel)")
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
                should_preserve = any(prefix in message.content for prefix in config_prefixes)
                
                if should_preserve:
                    print(f"Preserving message: {message.content[:50]}...")
                else:
                    print(f"Deleting message: {message.content[:50]}...")
                    await message.delete()
                    await asyncio.sleep(1)


@bot.tree.command(name="leaderboard", description="Shows the leaderboard for reactions.")
@app_commands.describe(emoji="Optional emoji to show the leaderboard for")
async def leaderboard(interaction: discord.Interaction, emoji: str = None):
    embed = discord.Embed(title="Reaction Leaderboard", color=discord.Color.blue())
    
    if emoji:
        emoji_config = config['emoji_configs'].get(emoji)
        if not emoji_config:
            await interaction.response.send_message(f"Error: Emoji {emoji} is not being tracked.", ephemeral=True)
            return

        user_counts = emoji_config.get('user_counts', {})
        if not user_counts:
            embed.add_field(name=emoji, value="No users have reached the threshold yet.", inline=False)
        else:
            sorted_counts = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
            leaderboard_text = "\n".join([f"{interaction.guild.get_member(user_id).mention}: {count}" for user_id, count in sorted_counts])
            embed.add_field(name=emoji, value=leaderboard_text or "No counts yet.", inline=False)
    else:
        for emoji, emoji_config in config['emoji_configs'].items():
            user_counts = emoji_config.get('user_counts', {})
            if user_counts:
                sorted_counts = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
                leaderboard_text = "\n".join([f"{interaction.guild.get_member(user_id).mention}: {count}" for user_id, count in sorted_counts])
                embed.add_field(name=emoji, value=leaderboard_text or "No counts yet.", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)




# Run the bot
bot.run(token, log_handler=handler)
