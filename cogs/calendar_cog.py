import discord
from discord.ext import commands, tasks
import aiohttp
import pytz
from datetime import datetime, timedelta, time
import json
from icalendar import Calendar
from dateutil.rrule import rrulestr

ICS_URL = "https://outlook.office365.com/owa/calendar/30f33308faff4d53a3ea3afe1ed5fbad@fsu.edu/690a01fda04b4ec1a579221f653489bb7175071983823801560/calendar.ics"
CHANNEL_ID = 1346069503863423059
ROLE_ID = 1399528835837595689
WEEKLY_EMBED_COLOR = 0xCEB888
MORNING_EMBED_COLOR = 0x782F40
DATA_FILE = "../json/calendar_announced.json"

def ensure_timezone(dt):
    if dt and not dt.tzinfo:
        return pytz.utc.localize(dt)
    return dt

class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announced = self.load_announced()
        self.check_calendar.start()
        self.send_weekly_alert.start()
        self.send_day_before_alert.start()

    def cog_unload(self):
        self.check_calendar.cancel()
        self.send_weekly_alert.cancel()
        self.send_day_before_alert.cancel()

    def load_announced(self):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"weekly": [], "daybefore": []}

    def save_announced(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.announced, f, indent=2)

    async def fetch_calendar(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(ICS_URL) as resp:
                return await resp.text()

    async def get_events_by_range(self, start_date, end_date):
        data = await self.fetch_calendar()
        cal = Calendar.from_ical(data)
        events = []

        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            summary = str(component.get('summary', 'Untitled Event'))
            dtstart = component.get('dtstart')
            dtend = component.get('dtend')
            location = str(component.get('location', '')) if component.get('location') else None
            uid = str(component.get('uid', summary + str(dtstart)))
            all_day = False

            if hasattr(dtstart, 'dt'):
                dtstart = dtstart.dt
                if isinstance(dtstart, datetime):
                    dtstart = ensure_timezone(dtstart)
                else:
                    # It's a date (all-day event)
                    all_day = True
                    eastern = pytz.timezone("US/Eastern")
                    dtstart = eastern.localize(datetime.combine(dtstart, time.min))
            else:
                continue

            rrule = component.get('rrule')
            if rrule:
                rrule_bytes = component['rrule'].to_ical()
                rrule_str = rrule_bytes.decode() if isinstance(rrule_bytes, bytes) else str(rrule_bytes)
                if rrule_str.startswith("RRULE:"):
                    rrule_str = rrule_str[len("RRULE:"):]
                rule = rrulestr(rrule_str, dtstart=dtstart)
                for occur in rule.between(start_date, end_date, inc=False):
                    events.append({
                        "name": summary,
                        "begin": occur,
                        "location": location,
                        "uid": uid + str(occur),
                        "all_day": all_day
                    })
            else:
                # Non-recurring event
                events.append({
                    "name": summary,
                    "begin": dtstart,
                    "location": location,
                    "uid": uid,
                    "all_day": all_day
                })
        return events

    @staticmethod
    def format_event_field(event):
        eastern = pytz.timezone("US/Eastern")
        title = f"**{event['name'].upper()}**"
        begin = event["begin"]
        if event.get("all_day", False):
            date_str = begin.astimezone(eastern).strftime("%b %d, %Y")
        else:
            date_str = begin.astimezone(eastern).strftime("%b %d, %Y, %I:%M %p")
        location_line = f"{event['location']}" if event.get("location") else ""
        value = f"{title}\n{date_str}"
        if location_line:
            value += f"\n{location_line}"
        return value

    @commands.command(name="debugevents")
    @commands.has_permissions(administrator=True)
    async def debug_events_command(self, ctx):
        """Fetch and display all events from the calendar."""
        eastern = pytz.timezone("US/Eastern")
        now = datetime.now(eastern)
        year_start = datetime(now.year, 1, 1, 0, 0, 0, tzinfo=eastern)
        year_end = datetime(now.year, 12, 31, 23, 59, 59, tzinfo=eastern)
        events = await self.get_events_by_range(
            year_start.astimezone(pytz.utc),
            year_end.astimezone(pytz.utc)
        )

        # Deduplicate by UID + date
        seen = set()
        event_lines = []
        for event in events:
            event_time = event["begin"].astimezone(eastern)
            key = f"{event['uid']}_{event_time.date()}"
            if key in seen:
                continue
            seen.add(key)
            if event.get("all_day", False):
                date_str = event_time.strftime("%b %d, %Y")
            else:
                date_str = event_time.strftime("%b %d, %Y, %I:%M %p")
            line = f"{event['name']} | {date_str}"
            if event.get("location"):
                line += f" | {event['location']}"
            event_lines.append((event_time, line))

        if not event_lines:
            await ctx.send("No events found in the ICS file for this year.")
            return

        # Sort by event_time
        event_lines.sort(key=lambda x: x[0])
        lines = [line for _, line in event_lines]

        # Discord message limit: 2000 chars
        chunk = []
        total = 0
        for line in lines:
            if total + len(line) + 1 > 1900:
                await ctx.send("\n".join(chunk))
                chunk = []
                total = 0
            chunk.append(line)
            total += len(line) + 1
        if chunk:
            await ctx.send("\n".join(chunk))

    @commands.command(name="getevents")
    async def get_month_events(self, ctx):
        """Fetch and display events for the current month."""
        eastern = pytz.timezone("US/Eastern")
        now = datetime.now(eastern)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)
        events = await self.get_events_by_range(start.astimezone(pytz.utc), (end - timedelta(seconds=1)).astimezone(pytz.utc))

        # Filter by local month/year
        filtered_events = []
        for event in events:
            event_time = event["begin"].astimezone(eastern)
            if event_time.year == now.year and event_time.month == now.month:
                filtered_events.append(event)

        if not filtered_events:
            await ctx.send("No events found for this month.")
            return
        embed = discord.Embed(
            title=f"Events for {now.strftime('%B %Y')}",
            color=WEEKLY_EMBED_COLOR
        )
        for event in sorted(filtered_events, key=lambda e: e["begin"]):
            embed.add_field(name="", value=self.format_event_field(event), inline=False)
        await ctx.send(embed=embed)

    @tasks.loop(hours=1)
    async def check_calendar(self):
        await self.bot.wait_until_ready()
        # Reserved for future hourly tasks if needed
        pass

    @tasks.loop(minutes=1)
    async def send_weekly_alert(self):
        now = datetime.now(pytz.timezone("US/Eastern"))
        if now.weekday() != 0 or now.hour != 10 or now.minute != 0:
            return
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)
        eastern = pytz.timezone("US/Eastern")
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        week_start = datetime.combine(monday, time.min).replace(tzinfo=eastern)
        week_end = datetime.combine(monday + timedelta(days=6), time.max).replace(tzinfo=eastern)
        week_start_date = week_start.date()
        week_end_date = week_end.date()

        # Fetch a little extra in UTC to be sure
        events = await self.get_events_by_range(
            week_start.astimezone(pytz.utc) - timedelta(hours=6),
            week_end.astimezone(pytz.utc) + timedelta(hours=6)
        )

        # Filter in Eastern time using .date() comparison
        filtered_events = []
        for event in events:
            event_time = event["begin"].astimezone(eastern)
            event_date = event_time.date()
            if week_start_date <= event_date <= week_end_date:
                filtered_events.append(event)

        if not filtered_events:
            return
        embed = discord.Embed(
            title="This Week's Events",
            color=WEEKLY_EMBED_COLOR,
            description="Here's what's happening this week:"
        )
        for event in filtered_events:
            if event["uid"] in self.announced["weekly"]:
                continue
            embed.add_field(name="", value=self.format_event_field(event), inline=False)
            self.announced["weekly"].append(event["uid"])
        await channel.send(f"<@&{ROLE_ID}>", embed=embed)
        self.save_announced()

    @tasks.loop(minutes=1)
    async def send_day_before_alert(self):
        now = datetime.now(pytz.timezone("US/Eastern"))
        if now.hour != 12 or now.minute != 0:
            return
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)
        eastern = pytz.timezone("US/Eastern")
        tomorrow = now.date() + timedelta(days=1)

        # Fetch events for the next 2 days (wide net, no UTC math for filtering)
        events = await self.get_events_by_range(
            now.astimezone(pytz.utc),
            (now + timedelta(days=2)).astimezone(pytz.utc)
        )

        filtered_events = []
        for event in events:
            event_time_eastern = event["begin"].astimezone(eastern)
            if event_time_eastern.date() == tomorrow:
                filtered_events.append(event)

        if not filtered_events:
            return
        embed = discord.Embed(
            title="Tomorrow's Events",
            color=MORNING_EMBED_COLOR,
            description="Here's what's happening tomorrow:"
        )
        for event in filtered_events:
            if event["uid"] in self.announced.get("daybefore", []):
                continue
            embed.add_field(name="", value=self.format_event_field(event), inline=False)
            self.announced.setdefault("daybefore", []).append(event["uid"])
        await channel.send(f"<@&{ROLE_ID}>", embed=embed)
        self.save_announced()

    @commands.command(name="testdaybefore")
    @commands.has_permissions(administrator=True)
    async def test_day_before_alert(self, ctx):
        """Manually trigger the day-before alert."""
        await self._send_day_before_alert_manual(ctx)

    async def _send_day_before_alert_manual(self, ctx):
        now = datetime.now(pytz.timezone("US/Eastern"))
        channel = ctx.channel
        eastern = pytz.timezone("US/Eastern")
        tomorrow = now.date() + timedelta(days=1)

        events = await self.get_events_by_range(
            now.astimezone(pytz.utc),
            (now + timedelta(days=2)).astimezone(pytz.utc)
        )

        filtered_events = []
        for event in events:
            event_time_eastern = event["begin"].astimezone(eastern)
            if event_time_eastern.date() == tomorrow:
                filtered_events.append(event)

        if not filtered_events:
            await ctx.send("No events found for tomorrow.")
            return
        embed = discord.Embed(
            title="Tomorrow's Events",
            color=MORNING_EMBED_COLOR,
            description="Here's what's happening tomorrow:"
        )
        for event in filtered_events:
            embed.add_field(name="", value=self.format_event_field(event), inline=False)
        await channel.send(f"<@&{ROLE_ID}>", embed=embed)

    @commands.command(name="testweekly")
    @commands.has_permissions(administrator=True)
    async def test_weekly_alert(self, ctx):
        """Manually trigger the weekly alert."""
        await self._send_weekly_alert_manual(ctx)

    async def _send_weekly_alert_manual(self, ctx):
        now = datetime.now(pytz.timezone("US/Eastern"))
        channel = ctx.channel
        eastern = pytz.timezone("US/Eastern")
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        week_start = datetime.combine(monday, time.min).replace(tzinfo=eastern)
        week_end = datetime.combine(monday + timedelta(days=6), time.max).replace(tzinfo=eastern)
        week_start_date = week_start.date()
        week_end_date = week_end.date()

        # Fetch a little extra in UTC to be sure
        events = await self.get_events_by_range(
            week_start.astimezone(pytz.utc) - timedelta(hours=6),
            week_end.astimezone(pytz.utc) + timedelta(hours=6)
        )

        # Filter in Eastern time using .date() comparison
        filtered_events = []
        for event in events:
            event_time = event["begin"].astimezone(eastern)
            event_date = event_time.date()
            if week_start_date <= event_date <= week_end_date:
                filtered_events.append(event)

        if not filtered_events:
            await ctx.send("No events found for this week.")
            return
        embed = discord.Embed(
            title="This Week's Events",
            color=WEEKLY_EMBED_COLOR,
            description="Here's what's happening this week:"
        )
        for event in filtered_events:
            embed.add_field(name="", value=self.format_event_field(event), inline=False)
        await channel.send(f"<@&{ROLE_ID}>", embed=embed)

async def setup(bot):
    await bot.add_cog(CalendarCog(bot))