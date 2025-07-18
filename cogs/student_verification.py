import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import time
import shutil
from datetime import datetime, timezone, timedelta
import asyncio
import re

from dotenv import load_dotenv
load_dotenv()
SERVER_ID = int(os.getenv("SERVER_ID"))
VERIFIED_STUDENT_ROLE_ID = int(os.getenv("VERIFIED_STUDENT_ROLE_ID"))

class StudentVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========== Utility Functions ==========
    def load_verified_codes(self):
        try:
            with open('json/verified.json') as f:
                data = json.load(f)
            for email, entry in data.items():
                if not isinstance(entry, dict) or 'code' not in entry or 'timestamp' not in entry:
                    raise ValueError(f"Invalid entry format for {email}")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"⚠️ Error loading verified.json: {e}")
            return {}

        now = time.time()
        valid = {
            email: v for email, v in data.items()
            if now - v['timestamp'] <= 72 * 3600
        }

        if len(valid) != len(data):
            self.save_verified_codes(valid)

        return valid

    def save_verified_codes(self, data):
        json_path = 'json/verified.json'
        backup_path = 'json/verified_backup.json'
        tmp_path = 'json/verified.tmp'
        try:
            if os.path.exists(json_path):
                shutil.copy(json_path, backup_path)
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp_path, json_path)
        except Exception as e:
            print(f"❌ Failed to save verified.json safely: {e}")
            raise e

    def log_verification_attempt(self, user, code, result):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=3)
        log_file = "verification.log"

        timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
        new_line = f"[{timestamp_str} UTC] {user.name}#{user.discriminator} ({user.id}) tried code '{code}': {result}\n"

        timestamp_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\]")

        kept_lines = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    match = timestamp_pattern.search(line)
                    if match:
                        entry_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                        if entry_time >= cutoff:
                            kept_lines.append(line)
        except FileNotFoundError:
            pass

        kept_lines.append(new_line)

        with open(log_file, "w", encoding="utf-8") as f:
            f.writelines(kept_lines)

    # ========== Slash Command: /verify ==========
    @app_commands.command(
        name="verify",
        description="[DMs ONLY] Verify your student email using a one-time code."
    )
    async def verify(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is not None:
            await interaction.followup.send("❌ Please DM this command to the bot — it only works in private.", ephemeral=True)
            self.log_verification_attempt(interaction.user, code, "❌ Used in server channel")
            return

        verified = self.load_verified_codes()
        matched_email = None

        for email, entry in verified.items():
            if entry['code'].lower() == code.lower():
                matched_email = email
                break

        if matched_email is None:
            await interaction.followup.send("❌ Invalid or expired verification code.")
            self.log_verification_attempt(interaction.user, code, "❌ Invalid or expired")
            return

        guild = self.bot.get_guild(SERVER_ID)
        if guild is None:
            await interaction.followup.send("❌ Server not found.")
            self.log_verification_attempt(interaction.user, code, "❌ Server not found")
            return

        member = guild.get_member(interaction.user.id)
        if member is None:
            await interaction.followup.send("❌ You must be a member of the server to verify.")
            self.log_verification_attempt(interaction.user, code, "❌ Not in server")
            return

        role = guild.get_role(VERIFIED_STUDENT_ROLE_ID)
        if role is None:
            await interaction.followup.send("❌ Verified role not found.")
            self.log_verification_attempt(interaction.user, code, "❌ Role not found")
            return

        if role in member.roles:
            await interaction.followup.send("✅ You are already verified!")
            self.log_verification_attempt(interaction.user, code, f"✅ Already verified (email: {matched_email})")
            return

        await member.add_roles(role)
        await interaction.followup.send(f"✅ Verification successful! Your email `{matched_email}` has been verified.")
        self.log_verification_attempt(interaction.user, code, f"✅ Verified successfully (email: {matched_email})")

        if matched_email in verified:
            del verified[matched_email]
            self.save_verified_codes(verified)
            print(f"✅ Deleted used code for {matched_email}")

    # ========== Background DM Reminder Task ==========
    async def send_dm_reminders(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guild = self.bot.get_guild(SERVER_ID)
            if guild is None:
                print("⚠️ Server not found.")
                await asyncio.sleep(10)
                continue

            verified = self.load_verified_codes()
            changed = False

            for email, entry in verified.items():
                tag = entry.get("discord_tag", "").strip().lower()
                if not tag or entry.get("dm_sent") is True or entry.get("dm_attempted") is True:
                    continue

                member = discord.utils.find(lambda m: m.name.lower() == tag, guild.members)
                if member:
                    try:
                        embed = discord.Embed(
                            title="FSU Esports Verification",
                            description=(
                                "Hi there! Thanks for submitting the FSU Esports student verification form.\n\n"
                                "We've sent a verification code to your FSU email address.\n\n"
                                "Please check your inbox (especially your junk folder—it loves to end up there!) "
                                "and then DM me: `/verify YOURCODE` to complete the process."
                            ),
                            color=0xCEB888
                        )
                        await member.send(embed=embed)
                        print(f"📩 Sent DM to {tag}")
                        entry["dm_sent"] = True
                        changed = True
                    except Exception as e:
                        print(f"⚠️ Could not DM {tag}: {e}")
                        entry["dm_attempted"] = True
                        changed = True
                else:
                    print(f"⚠️ No matching user for tag '{tag}' — will not retry.")
                    entry["dm_attempted"] = True
                    changed = True

            if changed:
                self.save_verified_codes(verified)
            await asyncio.sleep(60)

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Prefix commands are working.")

    async def cog_load(self):
        # Start the background task
        self.bot.loop.create_task(self.send_dm_reminders())

async def setup(bot):
    await bot.add_cog(StudentVerification(bot))