import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# === Load config from JSON ===
file_path = os.path.join(os.path.dirname(__file__), "..", "json", "assignable_roles.json")
with open(os.path.abspath(file_path)) as f:
    config = json.load(f)

load_dotenv()

SERVER_ID = int(os.getenv("SERVER_ID"))
VERIFIED_STUDENT_ROLE_ID = int(os.getenv("VERIFIED_STUDENT_ROLE_ID"))

ASSIGNABLE_ROLE_IDS = set(config["assignable_roles"])
AUTHORIZED_ROLE_IDS = set(config["authorized_roles"])
ALLOWED_CHANNEL_ID = 546878493200482314  # '#gms-assign-here'

class RoleAssignment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def collect_members(self, ctx: commands.Context, *mentions) -> list:
        members = []
        for mention in mentions:
            member = ctx.guild.get_member_named(mention) or ctx.guild.get_member(int(mention.strip("<@!>")))
            if member:
                members.append(member)
        return members

    def is_valid_nickname(self, member: discord.Member) -> bool:
        return member.nick and " | " in member.nick

    def is_authorized(self, user: discord.Member) -> bool:
        return any(role.id in AUTHORIZED_ROLE_IDS for role in user.roles)

    def is_verified(self, member: discord.Member) -> bool:
        return VERIFIED_STUDENT_ROLE_ID in [role.id for role in member.roles]
    
    @commands.command(name="addrole")
    async def addrole(self, ctx: commands.Context, *args):
        """Assigns one or more roles to one or more mentioned users if they are verified students."""
        if not self.is_authorized(ctx.author):
            return

        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            return

        if not self.is_verified(ctx.author):
            await ctx.send("❌ You must be a verified student to use this command.")
            return

        # Split args into roles and members: roles first, then users
        roles = []
        members = []
        found_user = False
        for arg in args:
            if not found_user and (arg.startswith("<@") and not arg.startswith("<@&")):
                found_user = True
            if found_user:
                # User mention
                member = ctx.guild.get_member(int(arg.strip("<@!>")))
                if member:
                    members.append(member)
            else:
                # Role mention or name
                if arg.startswith("<@&") and arg.endswith(">"):
                    role = ctx.guild.get_role(int(arg.strip("<@&>")))
                    if role:
                        roles.append(role)
                else:
                    role = discord.utils.get(ctx.guild.roles, name=arg)
                    if role:
                        roles.append(role)

        # Filter only assignable roles
        roles = [role for role in roles if role.id in ASSIGNABLE_ROLE_IDS]
        if not roles:
            await ctx.send(
                "❌ Please specify at least one valid assignable team role.\n"
                "If you think this is a mistake, please contact <@214151193998524416>."
            )
            return
        if not members:
            await ctx.send("❌ Please mention at least one valid user.")
            return

        results = []

        for member in members:
            if not self.is_verified(member):
                results.append(f"⚠️ {member.mention} must be a verified student to receive roles.")
                continue

            if not self.is_valid_nickname(member):
                results.append(
                    f"⚠️ {member.mention} does not have a properly formatted nickname. "
                    f"Please tell them to use `FirstName | GamerTag` format, and then try again."
                )
                continue

            for role in roles:
                if role in member.roles:
                    results.append(f"⚠️ {member.mention} already has `{role.name}`.")
                    continue

                try:
                    await member.add_roles(role)
                    results.append(f"✅ `{role.name}` assigned to {member.mention}.")
                except discord.Forbidden:
                    results.append(f"❌ I don’t have permission to assign `{role.name}` to {member.mention}.")
                except Exception as e:
                    results.append(f"❌ Error for {member.mention}: {e}")

        await ctx.send("\n".join(results))

    @commands.command(name="delrole")
    async def delrole(self, ctx: commands.Context, *args):
        """Removes one or more roles from one or more mentioned users if they are verified students."""
        if not self.is_authorized(ctx.author):
            return

        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            return

        if not self.is_verified(ctx.author):
            await ctx.send("❌ You must be a verified student to use this command.")
            return

        # Split args into roles and members: roles first, then users
        roles = []
        members = []
        found_user = False
        for arg in args:
            if not found_user and (arg.startswith("<@") and not arg.startswith("<@&")):
                found_user = True
            if found_user:
                member = ctx.guild.get_member(int(arg.strip("<@!>")))
                if member:
                    members.append(member)
            else:
                if arg.startswith("<@&") and arg.endswith(">"):
                    role = ctx.guild.get_role(int(arg.strip("<@&>")))
                    if role:
                        roles.append(role)
                else:
                    role = discord.utils.get(ctx.guild.roles, name=arg)
                    if role:
                        roles.append(role)

        # Filter only assignable roles
        roles = [role for role in roles if role.id in ASSIGNABLE_ROLE_IDS]
        if not roles:
            await ctx.send(
                "❌ Please specify at least one valid assignable role to remove.\n"
                "If you think this is a mistake, please contact <@214151193998524416>."
            )
            return
        if not members:
            await ctx.send("❌ Please mention at least one valid user.")
            return

        results = []

        for member in members:
            if not self.is_verified(member):
                results.append(f"⚠️ {member.mention} must be a verified student to have roles removed.")
                continue

            if not self.is_valid_nickname(member):
                results.append(
                    f"⚠️ {member.mention} does not have a properly formatted nickname. "
                    f"Please tell them to use `FirstName | GamerTag` format, and then try again."
                )
                continue

            for role in roles:
                if role not in member.roles:
                    results.append(f"⚠️ {member.mention} does not have `{role.name}`.")
                    continue

                try:
                    await member.remove_roles(role)
                    results.append(f"✅ `{role.name}` removed from {member.mention}.")
                except discord.Forbidden:
                    results.append(f"❌ I don’t have permission to remove `{role.name}` from {member.mention}.")
                except Exception as e:
                    results.append(f"❌ Error for {member.mention}: {e}")

        await ctx.send("\n".join(results))

# === Register the Cog ===
async def setup(bot: commands.Bot):
    await bot.add_cog(RoleAssignment(bot))
