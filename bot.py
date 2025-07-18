import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# ========== Load Environment ==========
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in environment variables!")

# ========== Set Up Bot ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    await client.load_extension("cogs.gm_role_assignment")
    print("✅ Loaded gm_role_assignment cog.")
    await client.load_extension("cogs.calendar_cog")
    print("✅ Loaded calendar_cog.")
    await client.load_extension("cogs.student_verification")
    print("✅ Loaded student_verification cog.")
    await client.load_extension("cogs.shadowban")
    print("✅ Loaded shadowban cog.")

@client.event
async def on_ready():
    print(f"🤖 Bot is ready as {client.user}")

async def main():
    async with client:
        await load_cogs()
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
