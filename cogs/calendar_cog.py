import discord
from discord.ext import commands
import os
import aiohttp
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.token = None
        self.token_expires = None
        print("[CalendarCog] CalendarCog successfully loaded.")

    def get_access_token(self):
        client_id = os.getenv("MS_CLIENT_ID")
        tenant_id = os.getenv("MS_TENANT_ID")
        client_secret = os.getenv("MS_CLIENT_SECRET")

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        scopes = ["https://graph.microsoft.com/.default"]

        app = ConfidentialClientApplication(
            client_id=client_id,
            authority=authority,
            client_credential=client_secret
        )

        result = app.acquire_token_silent(scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=scopes)

        self.token = result.get("access_token")
        self.token_expires = datetime.now(timezone.utc).timestamp() + result.get("expires_in", 3600)
        return self.token

    async def fetch_calendar_events(self):
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}"
        }

        calendar_id = os.getenv("MS_CALENDAR_ID")
        url = f"https://graph.microsoft.com/v1.0/users/{calendar_id}/calendar/events?$orderby=start/dateTime"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"[CalendarCog] Status code: {response.status}")
                raw = await response.text()
                print(f"[CalendarCog] Raw:\n{raw}")  # Shows what Graph returns
                if response.status != 200:
                    return []
                data = await response.json()
                return data.get("value", [])


    @commands.command(name="getevents")
    async def get_events(self, ctx):
        """Command to test fetching calendar events from shared Outlook calendar."""
        events = await self.fetch_calendar_events()
        if not events:
            await ctx.send("No events found.")
            return

        response = "**Upcoming Events:**\n"
        for event in events[:5]:
            subject = event.get("subject", "No Title")
            start = event.get("start", {}).get("dateTime", "No Start Time")

            try:
                dt_obj = datetime.fromisoformat(start.replace("Z", "+00:00"))
                start = dt_obj.strftime("%A, %b %d at %I:%M %p")
            except Exception:
                pass

            response += f"- **{subject}** at `{start}`\n"

        await ctx.send(response)

async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
    print("[CalendarCog] Cog added to bot.")
