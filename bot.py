import discord
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower() == '!ping':
        await message.channel.send('Pong!')

client.run(TOKEN)

