import os
import json
import discord
import logging
import asyncio
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
from discord import app_commands
from config import token

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Directory for server-specific configurations
CONFIG_DIR = 'bot_configs'

# Ensure config directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)

# Load configuration for a specific guild
def load_config(guild_id):
    config_file = os.path.join(CONFIG_DIR, f'{guild_id}.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {'emoji_configs': {}}

# Save configuration for a specific guild
def save_config(guild_id, config):
    config_file = os.path.join(CONFIG_DIR, f'{guild_id}.json')
    with open(config_file, 'w') as f:
        json.dump(config, f)

# Dictionary to store message IDs by guild and emoji
sent_messages = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot or reaction.message.author == bot.user:
        return

    guild_id = reaction.message.guild.id
    config = load_config(guild_id)

    emoji = str(reaction.emoji)
    if emoji in config['emoji_configs']:
        emoji_config = config['emoji_configs'][emoji]
        target_channel = bot.get_channel(emoji_config['target_channel_id'])
        threshold = emoji_config['threshold']

        if target_channel:
            message_content = f"{reaction.count} {emoji} | {reaction.message.jump_url}\n\n"

            # Convert the message time to the user's timezone
            created_at = reaction.message.created_at
            user_timezone = pytz.timezone('America/New_York')  # Replace with actual user's timezone
            local_time = created_at.astimezone(user_timezone)

            # Time formatting
            now = datetime.now(user_timezone)
            if local_time.date() == now.date():
                message_time = "Today at " + local_time.strftime("%I:%M %p")
            elif local_time.date() == (now - timedelta(days=1)).date():
                message_time = "Yesterday at " + local_time.strftime("%I:%M %p")
            else:
                message_time = local_time.strftime("%m/%d/%Y %I:%M %p")

            # Initialize sent_messages for the guild if it doesn't exist
            if guild_id not in sent_messages:
                sent_messages[guild_id] = {}
            
            # Use the message ID to store the message
            message_id = reaction.message.id

            if message_id in sent_messages[guild_id]:
                sent_message = await target_channel.fetch_message(sent_messages[guild_id][message_id]['message_id'])
                if reaction.count >= threshold:
                    await sent_message.edit(content=message_content)
                    embed = sent_message.embeds[0]  # Get the first embed from the message
                    embed.set_footer(text=message_time)  # Set the footer text
                    await sent_message.edit(embed=embed)
                elif reaction.count < threshold:
                    await sent_message.delete()
                    del sent_messages[guild_id][message_id]
            else:
                if reaction.count >= threshold:
                    embed = discord.Embed(description=reaction.message.content, color=discord.Color.purple())
                    embed.set_author(name=reaction.message.author.name, icon_url=reaction.message.author.avatar.url)
                    embed.set_footer(text=message_time)

                    sent_message = await target_channel.send(message_content, embed=embed)
                    sent_messages[guild_id][message_id] = {'message_id': sent_message.id, 'emoji': emoji}
                    await sent_message.add_reaction(emoji)



@bot.tree.command(name="set-reaction", description="Sets a rule for the bot with a specific target channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(emoji="The emoji to track", threshold="The number of reactions required to trigger the message", channel_name="The name of the channel to send the message")
async def track_reaction(interaction: discord.Interaction, emoji: str, threshold: int, channel_name: str):
    guild_id = interaction.guild.id
    config = load_config(guild_id)

    # Check if the emoji is already being tracked
    if emoji in config['emoji_configs']:
        await interaction.response.send_message(f"Error: Reaction {emoji} is already being tracked.", ephemeral=True)
        return

    if len(emoji) != 1 and not emoji.startswith('<:') and not emoji.startswith('<a:'):
        await interaction.response.send_message("Error: Please provide a single emoji. Custom emojis are also accepted.", ephemeral=True)
        return

    if threshold <= 0:
        await interaction.response.send_message("Error: The threshold must be a positive number.", ephemeral=True)
        return

    channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
    if not channel:
        await interaction.response.send_message(f"Error: Channel '{channel_name}' not found.", ephemeral=True)
        return

    config['emoji_configs'][emoji] = {
        'threshold': threshold,
        'target_channel_id': channel.id
    }
    save_config(guild_id, config)

    await interaction.response.send_message(f"Reaction {emoji} is now being tracked with threshold {threshold} in {channel.mention}.", ephemeral=True)


@bot.tree.command(name="remove-reaction", description="Given an emote, remove its tracking rule")
@commands.has_permissions(administrator=True)
@app_commands.describe(emoji="The emoji to stop tracking")
async def untrack_reaction(interaction: discord.Interaction, emoji: str):
    guild_id = interaction.guild.id
    config = load_config(guild_id)

    if emoji in config['emoji_configs']:
        del config['emoji_configs'][emoji]
        save_config(guild_id, config)
        await interaction.response.send_message(f"Reaction {emoji} is no longer being tracked.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: Reaction {emoji} was not being tracked.", ephemeral=True)

@bot.tree.command(name="show-config", description="Show how the bot is currently configured")
@commands.has_permissions(administrator=True)
async def show_config(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    config = load_config(guild_id)

    embed = discord.Embed(title="Current Configuration", color=discord.Color.blue())

    if not config['emoji_configs']:
        embed.add_field(name="Tracked Reactions", value="No reactions are currently being tracked.", inline=False)
    else:
        for emoji, emoji_config in config['emoji_configs'].items():
            target_channel = bot.get_channel(emoji_config['target_channel_id'])
            if not target_channel:
                print(f"Target channel not found for emoji {emoji} in guild {guild_id}")
                return
            channel_mention = target_channel.mention if target_channel else "Channel not found"
            embed.add_field(name=emoji, value=f"Threshold: {emoji_config['threshold']}, Target Channel: {channel_mention}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear-bot-messages", description="Clears all messages sent by the bot.")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel to clear messages from (defaults to the current channel)")
async def clear_bot_messages(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel

    await interaction.response.defer()

    async for message in target_channel.history(limit=None):
        if message.author == bot.user:
            print(f"Deleting message: {message.content[:50]}...")
            await message.delete()
            await asyncio.sleep(1)

    await interaction.followup.send("All bot messages have been deleted.", ephemeral=True)

# Run the bot
bot.run(token, log_handler=handler)
