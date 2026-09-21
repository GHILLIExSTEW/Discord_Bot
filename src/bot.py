import asyncio
import logging

import discord
from discord.ext import commands

from src.config import APPLICATION_ID, DISCORD_TOKEN, GUILD_ID, OFFICIAL_CHANNEL_ID, OFFICIAL_ROLE_IDS, TEAM_STATS_CHANNEL_ID
from src.services.official_play_service import OfficialPlayService
from src.services.roster_sync_service import RosterSyncService
from src.services.team_admin_service import team_admin_service
from src.services.team_management_service import TeamManagementService
from src.services.team_ranking_service import TeamRankingService
from src.services.team_summary_service import TeamSummaryService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("official_play_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class OfficialBot(commands.Bot):
    async def setup_hook(self) -> None:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced guild commands: {', '.join(command.name for command in synced)}")
        else:
            synced = await self.tree.sync()
            print(f"Synced global commands: {', '.join(command.name for command in synced)}")


bot = OfficialBot(command_prefix="!", intents=intents, application_id=APPLICATION_ID)
official_play_service = OfficialPlayService()
team_ranking_service = TeamRankingService()
team_summary_service = TeamSummaryService()
team_management_service = TeamManagementService()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    asyncio.create_task(RosterSyncService().run_annually())


class PlayModal(discord.ui.Modal, title="Record Official Play"):
    units = discord.ui.TextInput(label="Units risked", placeholder="Example: 2", required=True, max_length=20)
    legs = discord.ui.TextInput(label="Number of legs", placeholder="Example: 3", required=True, max_length=10)
    odds = discord.ui.TextInput(label="American odds", placeholder="Example: -110 or +150", required=True, max_length=20)
    team_name = discord.ui.TextInput(label="Team (optional)", placeholder="Enter a team, including an untracked team", required=False, max_length=100)
    play_text = discord.ui.TextInput(label="Notes (optional)", style=discord.TextStyle.paragraph, required=False, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger.info("play_modal_submit interaction=%s user=%s channel=%s", interaction.id, interaction.user.id, interaction.channel_id)
        try:
            units = float(self.units.value)
            legs = int(self.legs.value)
        except ValueError:
            logger.warning("play_modal_invalid_numbers interaction=%s", interaction.id)
            await interaction.response.send_message("Units must be a number and legs must be a whole number.", ephemeral=True)
            return

        logger.info("play_modal_defer interaction=%s units=%s legs=%s odds=%s team=%s", interaction.id, units, legs, self.odds.value, self.team_name.value or "<none>")
        await interaction.response.defer()
        logger.info("play_modal_deferred interaction=%s", interaction.id)
        try:
            logger.info("play_db_start interaction=%s", interaction.id)
            payload = await asyncio.to_thread(
                official_play_service.create_play_record,
                discord_user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                units=units,
                legs=legs,
                odds=self.odds.value,
                team_name=self.team_name.value,
                play_text=self.play_text.value,
            )
            logger.info("play_db_complete interaction=%s play_id=%s error=%s", interaction.id, payload.get("play_id"), bool(payload.get("error")))
        except Exception as exc:
            logger.exception("play_db_failed interaction=%s", interaction.id)
            await interaction.followup.send(f"Could not record the play: {exc}", ephemeral=True)
            return

        if payload.get("error"):
            logger.warning("play_validation_failed interaction=%s error=%s", interaction.id, payload["error"])
            await interaction.followup.send(payload["error"], ephemeral=True)
            return

        embed = discord.Embed(title="Official Play", description=payload["summary"], color=discord.Color.blurple())
        embed.add_field(name="Units", value=f"{payload['units']}u", inline=True)
        embed.add_field(name="Legs", value=str(payload["legs"]), inline=True)
        embed.add_field(name="Odds", value=str(payload["odds"]), inline=True)
        embed.add_field(name="To win", value=f"{payload['to_win']}u", inline=True)
        embed.add_field(name="Posted by", value=payload["user_name"], inline=False)
        if payload.get("team_name"):
            embed.add_field(name="Team", value=payload["team_name"], inline=False)
        if payload.get("play_text"):
            embed.add_field(name="Notes", value=payload["play_text"][:1024], inline=False)

        logger.info("play_followup_start interaction=%s", interaction.id)
        message = await interaction.followup.send(embed=embed, wait=True)
        logger.info("play_followup_complete interaction=%s message_id=%s", interaction.id, message.id)
        await asyncio.to_thread(official_play_service.attach_message_id, payload["play_id"], message.id)
        logger.info("play_complete interaction=%s play_id=%s", interaction.id, payload["play_id"])


@bot.tree.command(name="play", description="Open the official play entry form")
async def play_command(interaction: discord.Interaction):
    logger.info("play_command_received interaction=%s user=%s channel=%s", interaction.id, interaction.user.id, interaction.channel_id)
    if not interaction.guild:
        logger.warning("play_rejected_no_guild interaction=%s", interaction.id)
        await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
        return

    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        logger.warning("play_rejected_role interaction=%s user=%s", interaction.id, interaction.user.id)
        await interaction.response.send_message("You do not have permission to log official plays.", ephemeral=True)
        return

    if OFFICIAL_CHANNEL_ID and interaction.channel_id != OFFICIAL_CHANNEL_ID:
        logger.warning("play_rejected_channel interaction=%s channel=%s expected=%s", interaction.id, interaction.channel_id, OFFICIAL_CHANNEL_ID)
        await interaction.response.send_message(f"Use this command in the official channel: <#{OFFICIAL_CHANNEL_ID}>", ephemeral=True)
        return

    logger.info("play_modal_open_start interaction=%s", interaction.id)
    await interaction.response.send_modal(PlayModal())
    logger.info("play_modal_open_complete interaction=%s", interaction.id)


@bot.tree.command(name="settle", description="Settle an official play")
@discord.app_commands.describe(play_id="The play record ID", result="win, loss, void, partial, or regraded")
async def settle_command(interaction: discord.Interaction, play_id: str, result: str):
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("Only officials can settle plays.", ephemeral=True)
        return

    try:
        outcome = official_play_service.settle_play(int(play_id), result)
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    await interaction.response.send_message(f"Play {play_id} settled as {outcome['result']} with tally {outcome['tally']}.", ephemeral=True)


@bot.tree.command(name="regrade", description="Regrade an official play")
@discord.app_commands.describe(play_id="The play record ID", legs_left="Remaining legs", odds="New American odds", note="Optional regrade notes")
async def regrade_command(interaction: discord.Interaction, play_id: str, legs_left: int, odds: str, note: str | None = None):
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("Only officials can regrade plays.", ephemeral=True)
        return

    try:
        outcome = official_play_service.regrade_play(int(play_id), legs_left, odds, note or "")
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    await interaction.response.send_message(
        f"Play {play_id} regraded to {outcome['legs_left']}-leg at {outcome['odds']}.",
        ephemeral=True,
    )


@bot.tree.command(name="rankings", description="Show the current team ranking summary")
async def rankings_command(interaction: discord.Interaction):
    if TEAM_STATS_CHANNEL_ID and interaction.channel_id != TEAM_STATS_CHANNEL_ID:
        await interaction.response.send_message(f"Use this command in <#{TEAM_STATS_CHANNEL_ID}>", ephemeral=True)
        return

    try:
        rankings = team_ranking_service.fetch_rankings_from_supabase()
    except RuntimeError:
        rankings = []

    if not rankings:
        rankings = [
            {"team_id": 1, "wins": 0, "losses": 0, "voids": 0, "partials": 0, "net_units": 0.0},
        ]

    embed = discord.Embed(title="Team Rankings", color=discord.Color.gold())
    if not rankings or all(item.get("net_units") == 0 and item.get("wins") == 0 and item.get("losses") == 0 and item.get("voids") == 0 and item.get("partials") == 0 for item in rankings):
        embed.description = "No settled results yet."
    else:
        lines = []
        for index, item in enumerate(rankings[:10], start=1):
            label = item.get("team_name") or f"Team {item['team_id']}"
            lines.append(f"{index}. {label} — {item['net_units']:+.2f}u | W{item['wins']} L{item['losses']} V{item['voids']} P{item['partials']}")
        embed.description = "\n".join(lines)

    await interaction.response.send_message(embed=embed, ephemeral=False)


@bot.tree.command(name="summary", description="Build the current daily team summary")
async def summary_command(interaction: discord.Interaction):
    if TEAM_STATS_CHANNEL_ID and interaction.channel_id != TEAM_STATS_CHANNEL_ID:
        await interaction.response.send_message(f"Use this command in <#{TEAM_STATS_CHANNEL_ID}>", ephemeral=True)
        return

    try:
        total_rows = team_summary_service.build_daily_summary()
    except RuntimeError:
        await interaction.response.send_message("Supabase is not configured for summary generation.", ephemeral=True)
        return

    rows = team_summary_service.fetch_daily_summary()
    embed = discord.Embed(title="Daily Team Summary", color=discord.Color.green())
    if not rows:
        embed.description = "No team summary records created yet."
    else:
        lines = []
        for item in rows[:10]:
            lines.append(f"Team {item['team_id']} — {float(item.get('net_units', 0)):+.2f}u | W{item['wins']} L{item['losses']} V{item['voids']} P{item['partials']}")
        embed.description = "\n".join(lines)
    embed.set_footer(text=f"Rows processed: {total_rows}")
    await interaction.response.send_message(embed=embed, ephemeral=False)


@bot.tree.command(name="assignteam", description="Assign a Discord user to a team")
@discord.app_commands.describe(member="Discord member", team_id="Internal team ID")
async def assign_team_command(interaction: discord.Interaction, member: discord.Member, team_id: int):
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("Only officials can assign team memberships.", ephemeral=True)
        return

    try:
        result = team_admin_service.assign_user_to_team(str(member.id), team_id)
    except Exception as exc:
        await interaction.response.send_message(f"Assignment failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Assigned {member.mention} to team ID {team_id}.", ephemeral=True)


@bot.tree.command(name="forcesync", description="Trigger an immediate roster sync pass")
async def force_sync_command(interaction: discord.Interaction):
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("Only officials can force a sync.", ephemeral=True)
        return

    outcome = team_admin_service.force_roster_sync()
    await interaction.response.send_message(f"Roster sync triggered. Records processed: {outcome['synced_record_count']}", ephemeral=True)


async def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not configured.")
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
