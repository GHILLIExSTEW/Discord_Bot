import asyncio
import logging
import uuid

import discord
from discord.ext import commands

from src.config import APPLICATION_ID, DISCORD_TOKEN, GUILD_ID, OFFICIAL_CHANNEL_ID, OFFICIAL_ROLE_IDS, TEAM_STATS_CHANNEL_ID
from src.services.official_play_service import OfficialPlayService
from src.services.team_ranking_service import TeamRankingService
from src.services.team_summary_service import TeamSummaryService
from src.services.play_service import PlayService
from src.services.image_play_service import image_play_service
from src.services.diagnostic_service import diagnostic_service

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
play_service = PlayService()


def build_play_embed(payload: dict) -> discord.Embed:
    embed = discord.Embed(title="Official Play", description=payload["summary"], color=discord.Color.blurple())
    embed.add_field(name="Units", value=f"{payload['units']}u", inline=True)
    embed.add_field(name="Legs", value=str(payload["legs"]), inline=True)
    embed.add_field(name="Odds", value=str(payload["odds"]), inline=True)
    embed.add_field(name="To win", value=f"{payload['to_win']}u", inline=True)
    if payload.get("team_name"):
        embed.add_field(name="Team", value=payload["team_name"], inline=False)
    if payload.get("play_text"):
        embed.add_field(name="Notes", value=payload["play_text"][:1024], inline=False)
    return embed


async def publish_play_webhook(interaction: discord.Interaction, payload: dict) -> discord.Message:
    channel = interaction.channel
    if not hasattr(channel, "create_webhook"):
        raise RuntimeError("The play channel does not support webhook posts.")
    webhook = await channel.create_webhook(name="Official Play Publisher")
    try:
        return await webhook.send(
            embed=build_play_embed(payload),
            username=interaction.user.display_name,
            avatar_url=interaction.user.display_avatar.url,
            wait=True,
        )
    finally:
        await webhook.delete(reason="Temporary user-attributed official play webhook")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def record_modal_play(
    interaction: discord.Interaction,
    units: float,
    legs: int,
    odds_values: list[int],
    team_name: str,
    play_text: str,
    leg_records: list[dict],
) -> None:
    logger.info("play_modal_deferred interaction=%s", interaction.id)
    try:
        logger.info("play_db_start interaction=%s", interaction.id)
        payload = await asyncio.to_thread(
            official_play_service.create_play_record,
            discord_user_id=str(interaction.user.id),
            username=interaction.user.display_name,
            units=units,
            legs=legs,
            odds=play_service.combine_american_odds(odds_values),
            team_name=team_name,
            play_text=play_text,
            leg_records=leg_records,
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

    logger.info("play_webhook_start interaction=%s", interaction.id)
    try:
        message = await publish_play_webhook(interaction, payload)
    except Exception as exc:
        await interaction.followup.send(f"Could not publish the play: {exc}", ephemeral=True)
        return

    logger.info("play_webhook_complete interaction=%s message_id=%s", interaction.id, message.id)
    await asyncio.to_thread(official_play_service.attach_message_id, payload["play_id"], message.id)
    logger.info("play_complete interaction=%s play_id=%s", interaction.id, payload["play_id"])


class LegModal(discord.ui.Modal):
    leg_details = discord.ui.TextInput(
        label="Leg details",
        placeholder="Enter the pick or selection for this leg",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )
    leg_odds = discord.ui.TextInput(
        label="Leg odds",
        placeholder="Example: -110 or +150",
        required=True,
        max_length=20,
    )

    def __init__(self, draft_id: str, units: float, legs: int, odds_values: list[int], team_name: str, leg_number: int, collected: list[str], progress_message=None):
        super().__init__(title=f"Enter Leg {leg_number} of {legs}")
        self.draft_id = draft_id
        self.units = units
        self.legs = legs
        self.odds_values = odds_values
        self.team_name = team_name
        self.leg_number = leg_number
        self.collected = collected
        self.progress_message = progress_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            leg_odds = play_service.normalize_odds(self.leg_odds.value)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        self.collected.append(f"Leg {self.leg_number}: {self.leg_details.value.strip()} ({leg_odds:+d})")
        self.odds_values.append(leg_odds)
        await interaction.response.defer()
        await asyncio.to_thread(
            official_play_service.save_draft_leg,
            self.draft_id,
            str(interaction.user.id),
            self.units,
            self.legs,
            self.leg_number,
            self.leg_details.value.strip(),
            leg_odds,
            self.team_name,
        )
        logger.info("leg_modal_submit interaction=%s leg=%s/%s", interaction.id, self.leg_number, self.legs)
        if self.leg_number < self.legs:
            next_view = LegEntryView(
                    self.draft_id,
                    self.units,
                    self.legs,
                    self.odds_values,
                    self.team_name,
                    self.leg_number + 1,
                    self.collected,
                )
            if self.progress_message is not None:
                next_view.message = self.progress_message
                await self.progress_message.edit(
                    content=f"Leg {self.leg_number} saved. Continue with leg {self.leg_number + 1}.",
                    view=next_view,
                )
            else:
                await interaction.followup.send(
                    f"Leg {self.leg_number} saved. Continue with leg {self.leg_number + 1}.",
                    ephemeral=True,
                    view=next_view,
                )
            return

        draft_legs = await asyncio.to_thread(official_play_service.get_draft_legs, self.draft_id, str(interaction.user.id))
        combined = "\n".join(f"Leg {leg['leg_number']}: {leg['selection']} ({int(leg['odds']):+d})" for leg in draft_legs)
        await record_modal_play(interaction, self.units, self.legs, [int(leg["odds"]) for leg in draft_legs], self.team_name, combined, draft_legs)
        await asyncio.to_thread(official_play_service.clear_draft_legs, self.draft_id, str(interaction.user.id))


class LegEntryView(discord.ui.View):
    def __init__(self, draft_id: str, units: float, legs: int, odds_values: list[int], team_name: str, leg_number: int, collected: list[str]):
        super().__init__(timeout=900)
        self.draft_id = draft_id
        self.units = units
        self.legs = legs
        self.odds_values = odds_values
        self.team_name = team_name
        self.leg_number = leg_number
        self.collected = collected
        self.message = None

    @discord.ui.button(label="Enter next leg", style=discord.ButtonStyle.primary)
    async def enter_next_leg(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.message = interaction.message
        await interaction.response.send_modal(LegModal(
            self.draft_id,
                self.units,
                self.legs,
                self.odds_values,
                self.team_name,
                self.leg_number,
                self.collected,
                self.message,
            ))


class PlayModal(discord.ui.Modal, title="Record Official Play"):
    units = discord.ui.TextInput(label="Units risked", placeholder="Example: 2", required=True, max_length=20)
    legs = discord.ui.TextInput(label="Number of legs", placeholder="Example: 3", required=True, max_length=10)
    leg_one = discord.ui.TextInput(label="Leg 1 selection", placeholder="Enter the first pick or selection", required=True, max_length=1000)
    leg_one_odds = discord.ui.TextInput(label="Leg 1 odds", placeholder="Example: -110 or +150", required=True, max_length=20)
    team_name = discord.ui.TextInput(label="Team (optional)", placeholder="Enter a team, including an untracked team", required=False, max_length=100)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger.info("play_modal_submit interaction=%s user=%s channel=%s", interaction.id, interaction.user.id, interaction.channel_id)
        try:
            units = float(self.units.value)
            legs = int(self.legs.value)
        except ValueError:
            logger.warning("play_modal_invalid_numbers interaction=%s", interaction.id)
            await interaction.response.send_message("Units must be a number and legs must be a whole number.", ephemeral=True)
            return

        if legs < 1 or legs > 10:
            await interaction.response.send_message("Legs must be between 1 and 10.", ephemeral=True)
            return

        try:
            first_odds = play_service.normalize_odds(self.leg_one_odds.value)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        collected = [f"Leg 1: {self.leg_one.value.strip()}"]
        draft_id = str(uuid.uuid4())
        await interaction.response.defer()
        await asyncio.to_thread(
            official_play_service.save_draft_leg,
            draft_id,
            str(interaction.user.id),
            units,
            legs,
            1,
            self.leg_one.value.strip(),
            first_odds,
            self.team_name.value,
        )
        if legs > 1:
            await interaction.followup.send(
                "Start entering the legs one at a time.",
                ephemeral=True,
                view=LegEntryView(
                    draft_id,
                    units,
                    legs,
                    [first_odds],
                    self.team_name.value,
                    2,
                    collected,
                ),
            )
            return

        draft_legs = await asyncio.to_thread(official_play_service.get_draft_legs, draft_id, str(interaction.user.id))
        await record_modal_play(
            interaction,
            units,
            legs,
            [first_odds],
            self.team_name.value,
            "\n".join(collected),
            draft_legs,
        )
        await asyncio.to_thread(official_play_service.clear_draft_legs, draft_id, str(interaction.user.id))


class ConfirmImageView(discord.ui.View):
    def __init__(self, parsed: dict):
        super().__init__(timeout=900)
        self.parsed = parsed

    @discord.ui.button(label="Confirm and record", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        legs = self.parsed["legs"]
        odds_values = [int(leg["odds"]) for leg in legs]
        try:
            payload = await asyncio.to_thread(
                official_play_service.create_play_record,
                discord_user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                units=float(self.parsed["units"]),
                legs=len(legs),
                odds=play_service.combine_american_odds(odds_values),
                team_name=self.parsed.get("team_name") or "",
                play_text="\n".join(f"Leg {index}: {leg['selection']} ({int(leg['odds']):+d})" for index, leg in enumerate(legs, start=1)),
                leg_records=legs,
            )
            if payload.get("error"):
                await interaction.followup.send(payload["error"], ephemeral=True)
                return
            message = await publish_play_webhook(interaction, payload)
            await asyncio.to_thread(official_play_service.attach_message_id, payload["play_id"], message.id)
            await interaction.followup.send(f"Play {payload['play_id']} recorded.", ephemeral=True)
            self.stop()
        except Exception as exc:
            logger.exception("image_play_confirm_failed interaction=%s", interaction.id)
            await interaction.followup.send(f"Could not record the play: {exc}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Image import cancelled.", embed=None, view=None)
        self.stop()


@bot.tree.command(name="importimage", description="Read a betting slip image and prepare an official play")
@discord.app_commands.describe(image="Betting slip or play screenshot")
async def import_image_command(interaction: discord.Interaction, image: discord.Attachment):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
        return
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to import plays.", ephemeral=True)
        return
    if OFFICIAL_CHANNEL_ID and interaction.channel_id != OFFICIAL_CHANNEL_ID:
        await interaction.response.send_message(f"Use this command in the official channel: <#{OFFICIAL_CHANNEL_ID}>", ephemeral=True)
        return
    if not image.content_type or not image.content_type.startswith("image/"):
        await interaction.response.send_message("Attach an image file.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        parsed = await asyncio.to_thread(image_play_service.extract_play, image.url)
    except Exception as exc:
        logger.exception("image_play_extract_failed interaction=%s", interaction.id)
        await interaction.followup.send(f"Could not read that image: {exc}", ephemeral=True)
        return

    legs = parsed["legs"]
    odds = play_service.combine_american_odds([int(leg["odds"]) for leg in legs])
    embed = discord.Embed(title="Image play detected", color=discord.Color.orange())
    embed.add_field(name="Units", value=str(parsed["units"]), inline=True)
    embed.add_field(name="Legs", value=str(len(legs)), inline=True)
    embed.add_field(name="Combined odds", value=f"{odds:+d}", inline=True)
    embed.description = "\n".join(f"{index}. {leg['selection']} ({int(leg['odds']):+d})" for index, leg in enumerate(legs, start=1))
    if parsed.get("team_name"):
        embed.set_footer(text=f"Team: {parsed['team_name']}")
    await interaction.followup.send(embed=embed, content="Review the detected play before recording it:", view=ConfirmImageView(parsed), ephemeral=True)


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


@bot.tree.command(name="test", description="Run safe play-system diagnostics")
async def test_command(interaction: discord.Interaction):
    if OFFICIAL_ROLE_IDS and not any(role.id in OFFICIAL_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("Only officials can run diagnostics.", ephemeral=True)
        return

    checks = diagnostic_service.run_checks()
    passed = sum(check["passed"] for check in checks)
    embed = discord.Embed(
        title="Play System Diagnostics",
        description=f"{passed}/{len(checks)} checks passed. No database records were changed.",
        color=discord.Color.green() if passed == len(checks) else discord.Color.red(),
    )
    for check in checks:
        marker = "PASS" if check["passed"] else "FAIL"
        embed.add_field(name=f"{marker} • {check['name']}", value=check["detail"][:1024], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
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


async def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not configured.")
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
