import discord
from discord.ext import commands

SHADOWBAN_ROLE_ID = 1399529049461620876  # The role that indicates a user is shadowbanned
ADMIN_ROLE_ID = 447957885540892692       # The role that can use the shadowban commands
ALLOWED_CHANNEL_ID = 545734391419371550 # The channel where the shadowban commands can be used

EXEMPT_ROLE_IDS = {
    447957885540892692,  
    695489702723059742,
    543268440656314370,
    347642526011883521,
}

class Shadowban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin(self, member: discord.Member):
        return any(role.id == ADMIN_ROLE_ID for role in member.roles)

    def is_exempt(self, member: discord.Member):
        return any(role.id in EXEMPT_ROLE_IDS for role in member.roles)

    async def process_members(self, ctx, members, action):
        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            await ctx.send("❌ This command can only be used in the designated channel.")
            return
        if not self.is_admin(ctx.author):
            await ctx.send("❌ You do not have permission to use this command.")
            return
        if not members:
            await ctx.send("❌ You must mention at least one user.")
            return
        if len(members) > 50:
            await ctx.send("❌ You can only process up to 50 users at once.")
            return

        role = ctx.guild.get_role(SHADOWBAN_ROLE_ID)
        if not role:
            await ctx.send("❌ Shadowban role not found.")
            return

        results = []
        for member in members:
            try:
                if self.is_exempt(member):
                    results.append(f"❌ {member.mention} is exempt from being shadowbanned.")
                    continue
                if action == "add":
                    if role in member.roles:
                        results.append(f"⚠️ {member.mention} is already shadowbanned.")
                    else:
                        await member.add_roles(role, reason=f"Shadowbanned by {ctx.author}")
                        results.append(f"✅ {member.mention} shadowbanned.")
                elif action == "remove":
                    if role not in member.roles:
                        results.append(f"⚠️ {member.mention} is not shadowbanned.")
                    else:
                        await member.remove_roles(role, reason=f"Absolved by {ctx.author}")
                        results.append(f"✅ {member.mention} absolved.")
            except Exception as e:
                results.append(f"❌ {member.mention}: {e}")

        await ctx.send("\n".join(results))

    @commands.command(name="shadowban")
    async def shadowban(self, ctx, *members: discord.Member):
        """Assigns the shadowban role to up to 50 mentioned users."""
        await self.process_members(ctx, members, "add")

    @commands.command(name="absolve")
    async def absolve(self, ctx, *members: discord.Member):
        """Removes the shadowban role from up to 50 mentioned users."""
        await self.process_members(ctx, members, "remove")

async def setup(bot):
    await bot.add_cog(Shadowban(bot))