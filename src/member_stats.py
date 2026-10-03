import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.config import WHOP_MEMBERSHIP_SYNC_ENABLED
from src.services.membership_service import MembershipService
from src.services.member_stats_service import MemberStatsService, SPORTS

logger = logging.getLogger("member_stats")
SPORT_CHOICES = [app_commands.Choice(name=name, value=key) for key, name in SPORTS.items()]


class MemberStats(commands.Cog):
    def __init__(self, membership=None, stats=None):
        self.membership = membership or MembershipService()
        self.stats = stats or MemberStatsService()

    async def respond(self, interaction, mode, sport, team=None, opponent=None):
        await interaction.response.defer(ephemeral=True)
        if not WHOP_MEMBERSHIP_SYNC_ENABLED:
            await interaction.followup.send("Membership verification is not enabled. Stats tools are unavailable.", ephemeral=True)
            return
        try:
            allowed = await asyncio.to_thread(self.membership.has_highroller_access, interaction.user.id)
            if not allowed:
                await interaction.followup.send("These tools require current verified paid HIGHROLLER access. ALL-STAR and trials do not qualify; Discord roles alone do not grant access.", ephemeral=True)
                return
            title, description = await asyncio.to_thread(self.stats.report, mode, sport, team, opponent)
            if len(description) > 4096:
                raise RuntimeError("Cached stats report exceeds Discord's message limit.")
            embed = discord.Embed(title=title, description=description, color=0x9146BF)
            embed.set_footer(text="HIGHROLLER • Cached data only • No live API request")
            await interaction.followup.send(embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            logger.exception("highroller_stats_failed mode=%s user=%s", mode, interaction.user.id)
            await interaction.followup.send("Stats or membership verification is temporarily unavailable. Please retry later or contact support.", ephemeral=True)

    @app_commands.command(name="matchup", description="HIGHROLLER: find a cached upcoming matchup")
    @app_commands.guild_only()
    @app_commands.choices(sport=SPORT_CHOICES)
    async def matchup(self, interaction: discord.Interaction, sport: str, team: str, opponent: str):
        await self.respond(interaction, "matchup", sport, team, opponent)

    @app_commands.command(name="teamstats", description="HIGHROLLER: recent cached team form, not season standings")
    @app_commands.guild_only()
    @app_commands.choices(sport=SPORT_CHOICES)
    async def teamstats(self, interaction: discord.Interaction, sport: str, team: str):
        await self.respond(interaction, "teamstats", sport, team)

    @app_commands.command(name="schedule", description="HIGHROLLER: cached schedule for the next seven days")
    @app_commands.guild_only()
    @app_commands.choices(sport=SPORT_CHOICES)
    async def schedule(self, interaction: discord.Interaction, sport: str, team: str | None = None):
        await self.respond(interaction, "schedule", sport, team)

    @app_commands.command(name="results", description="HIGHROLLER: recent final scores from the event cache")
    @app_commands.guild_only()
    @app_commands.choices(sport=SPORT_CHOICES)
    async def results(self, interaction: discord.Interaction, sport: str, team: str | None = None):
        await self.respond(interaction, "results", sport, team)
