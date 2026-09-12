import os
import asyncio
import logging
from datetime import datetime

import discord
from dotenv import load_dotenv
from supabase import Client, create_client
from discord.ext import tasks

from tally_logic import (
    build_reaction_key,
    extract_values,
    format_result_channel_name,
    load_config,
    reaction_sign,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0")) if os.getenv("GUILD_ID") else None
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RESULT_CHANNEL_ID = int(os.getenv("RESULT_CHANNEL_ID", "0")) if os.getenv("RESULT_CHANNEL_ID") else None
MONITORED_CHANNEL_ID = int(os.getenv("MONITORED_CHANNEL_ID", "0")) if os.getenv("MONITORED_CHANNEL_ID") else None
TRACKED_ROLE_IDS = {
    int(role_id.strip())
    for role_id in os.getenv("TRACKED_ROLE_IDS", os.getenv("TRACKED_ROLE_ID", "")).split(",")
    if role_id.strip().isdigit()
}

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = discord.Client(intents=intents)
command_tree = discord.app_commands.CommandTree(bot)
commands_synced = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("playmaker-bot")

supabase: Client | None = None
channel_update_task: asyncio.Task | None = None
last_channel_name: str | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_rows(table: str, columns: str) -> list[dict]:
    if supabase is None:
        return []

    rows = []
    offset = 0
    while True:
        response = supabase.table(table).select(columns).range(offset, offset + 999).execute()
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        offset += 1000


def now_iso_for_config(config: dict) -> str:
    tz_name = config.get("timezone", "America/New_York")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).isoformat()
    except Exception:
        return datetime.now().isoformat()


def fetch_totals_for_window(tracked_user_ids: set[str] | None = None) -> dict[str, float]:
    if supabase is None:
        return {"day": 0.0, "week": 0.0, "month": 0.0, "year": 0.0}

    config = load_config()
    tz_name = config.get("timezone", "America/New_York")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_day.replace(day=start_day.day - start_day.weekday())
    start_month = start_day.replace(day=1)
    start_year = start_day.replace(month=1, day=1)

    totals = {"day": 0.0, "week": 0.0, "month": 0.0, "year": 0.0}
    windows = [("day", start_day), ("week", start_week), ("month", start_month), ("year", start_year)]
    for row in fetch_all_rows("unit_results", "user_id,total_units,result,created_at"):
        if tracked_user_ids is not None and str(row.get("user_id")) not in tracked_user_ids:
            continue
        try:
            created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        amount = float(row.get("total_units", 0) or 0)
        signed_amount = amount if row.get("result") == "win" else -amount if row.get("result") == "loss" else 0.0
        for key, start in windows:
            if start <= created_at < now:
                totals[key] += signed_amount
    return totals


def update_result_channel_name():
    global channel_update_task, last_channel_name

    if supabase is None:
        print("DEBUG: Supabase is None")
        return

    channel_id = RESULT_CHANNEL_ID or MONITORED_CHANNEL_ID
    if not channel_id:
        print("DEBUG: No channel ID set")
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"DEBUG: Channel {channel_id} not found")
        return

    totals = fetch_totals_for_window()
    name = format_result_channel_name(totals["day"], totals["week"], totals["year"])
    print(f"DEBUG: Updating channel to: {name}")
    if channel.name == name or last_channel_name == name:
        print("DEBUG: Channel name already matches; skipping edit")
        return
    if channel_update_task is not None and not channel_update_task.done():
        print("DEBUG: Channel edit already pending; skipping duplicate edit")
        return

    async def edit_channel_name():
        global last_channel_name
        try:
            await channel.edit(name=name)
            last_channel_name = name
            print(f"DEBUG: Channel name changed to: {name}")
        except discord.HTTPException as error:
            print(f"DEBUG: Discord rejected channel rename: {error}")

    channel_update_task = bot.loop.create_task(edit_channel_name())
    print("DEBUG: Channel edit task created successfully")


def insert_unit_entry(message: discord.Message, value: float, config: dict):
    if supabase is None:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.")

    existing = supabase.table("unit_entries").select("id").eq("message_id", str(message.id)).execute()
    if existing.data:
        return

    payload = {
        "user_id": str(message.author.id),
        "total_units": float(value),
        "message_id": str(message.id),
        "created_at": now_iso_for_config(config),
    }
    supabase.table("unit_entries").insert(payload).execute()


def member_has_tracked_role(member: discord.Member | discord.User | None) -> bool:
    if not TRACKED_ROLE_IDS:
        return True
    return bool(member and any(role.id in TRACKED_ROLE_IDS for role in getattr(member, "roles", [])))


async def current_tracked_user_ids(user_ids: set[str], guild: discord.Guild) -> set[str]:
    if not TRACKED_ROLE_IDS:
        return user_ids

    tracked = set()
    for user_id in user_ids:
        try:
            member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
        except (ValueError, discord.HTTPException):
            continue
        if member_has_tracked_role(member):
            tracked.add(user_id)
    return tracked


async def fetch_member_for_payload(payload: discord.RawReactionActionEvent) -> discord.Member | None:
    if not payload.guild_id:
        return None
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return None
    member = guild.get_member(payload.user_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(payload.user_id)
    except discord.HTTPException:
        return None


def insert_unit_result(message: discord.Message, value: float, result: str, config: dict):
    if supabase is None:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.")

    existing = supabase.table("unit_results").select("id").eq("message_id", str(message.id)).eq("user_id", str(message.author.id)).eq("result", result).execute()
    if existing.data:
        return

    payload = {
        "user_id": str(message.author.id),
        "total_units": float(value),
        "message_id": str(message.id),
        "result": result,
        "created_at": now_iso_for_config(config),
    }
    supabase.table("unit_results").insert(payload).execute()


async def scan_monitored_channel():
    if supabase is None:
        return
    if MONITORED_CHANNEL_ID in (None, 0):
        return

    channel = bot.get_channel(MONITORED_CHANNEL_ID)
    if channel is None:
        return

    config = load_config()
    async for message in channel.history(limit=1000):
        if message.author.bot:
            continue
        
        # Extract U values
        values = extract_values(
            message.content,
            require_keyword=config.get("require_keyword", ""),
            keyword_case_insensitive=config.get("keyword_case_insensitive", True),
            pattern=config.get("number_pattern", r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b"),
        )
        if not values:
            continue
        
        # Check reactions on this message
        for reaction in message.reactions:
            emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else getattr(reaction.emoji, "name", None)
            sign = reaction_sign(emoji_name)
            if sign == 0:
                continue
            
            result = "win" if sign > 0 else "loss"
            message_created_at = message.created_at.isoformat()
            # Record result for each user who reacted
            async for user in reaction.users():
                if user.bot:
                    continue
                member = channel.guild.get_member(user.id)
                if member is None:
                    try:
                        member = await channel.guild.fetch_member(user.id)
                    except discord.HTTPException:
                        continue
                if not member_has_tracked_role(member):
                    continue
                
                opposite = "loss" if result == "win" else "win"
                supabase.table("unit_results").delete().eq("message_id", str(message.id)).eq("user_id", str(user.id)).eq("result", opposite).execute()
                existing = supabase.table("unit_results").select("id").eq("message_id", str(message.id)).eq("user_id", str(user.id)).eq("result", result).execute()
                if not existing.data:
                    payload = {
                        "user_id": str(user.id),
                        "total_units": float(values[0]),
                        "message_id": str(message.id),
                        "result": result,
                        "created_at": message_created_at,
                    }
                    supabase.table("unit_results").insert(payload).execute()


@tasks.loop(hours=4)
async def scheduled_channel_update():
    try:
        await update_daily_breakdown()
    except (discord.HTTPException, Exception):
        logger.exception("Scheduled tracker update failed")


@scheduled_channel_update.before_loop
async def wait_before_first_scheduled_update():
    await asyncio.sleep(300)


async def update_daily_breakdown():
    if supabase is None or not RESULT_CHANNEL_ID:
        return

    channel = bot.get_channel(RESULT_CHANNEL_ID)
    if channel is None:
        return

    config = load_config()
    tz_name = config.get("timezone", "America/New_York")
    try:
        from zoneinfo import ZoneInfo
        timezone = ZoneInfo(tz_name)
    except Exception:
        timezone = None

    now = datetime.now(timezone) if timezone else datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    all_time_rows = fetch_all_rows("unit_results", "user_id,message_id,total_units,result,created_at")
    settled_message_ids = {str(row.get("message_id")) for row in all_time_rows}
    tracked_user_ids = await current_tracked_user_ids(
        {str(row.get("user_id")) for row in all_time_rows},
        channel.guild,
    )
    all_time_rows = [row for row in all_time_rows if str(row.get("user_id")) in tracked_user_ids]
    rows = []
    for row in all_time_rows:
        try:
            created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if start <= created_at < now:
            rows.append(row)
    wins = sum(float(row.get("total_units", 0) or 0) for row in rows if row.get("result") == "win")
    losses = sum(float(row.get("total_units", 0) or 0) for row in rows if row.get("result") == "loss")
    net = wins - losses
    date_label = now.strftime("%B %-d, %Y") if os.name != "nt" else now.strftime("%B %#d, %Y")
    totals = fetch_totals_for_window(tracked_user_ids)
    all_time_wins = sum(float(row.get("total_units", 0) or 0) for row in all_time_rows if row.get("result") == "win")
    all_time_losses = sum(float(row.get("total_units", 0) or 0) for row in all_time_rows if row.get("result") == "loss")
    player_totals = {}
    for row in all_time_rows:
        user_id = str(row.get("user_id", "unknown"))
        player = player_totals.setdefault(user_id, {"wins": 0.0, "losses": 0.0, "win_count": 0, "loss_count": 0, "results": 0})
        amount = float(row.get("total_units", 0) or 0)
        if row.get("result") == "win":
            player["wins"] += amount
            player["win_count"] += 1
        elif row.get("result") == "loss":
            player["losses"] += amount
            player["loss_count"] += 1
        player["results"] += 1

    player_lines = []
    ranked_players = []
    for user_id, player in sorted(player_totals.items(), key=lambda item: item[1]["wins"] - item[1]["losses"], reverse=True):
        try:
            member = channel.guild.get_member(int(user_id))
            if member is None:
                member = await channel.guild.fetch_member(int(user_id))
            if not member_has_tracked_role(member):
                continue
            player_name = member.display_name
        except (ValueError, discord.HTTPException):
            continue
        player_net = player["wins"] - player["losses"]
        ranked_players.append((player_name, player, player_net))
        player_lines.append(
            f"**{player_name}**\n"
            f"Wins: +{player['wins']:g} units  |  Losses: -{player['losses']:g} units\n"
            f"Net: {player_net:+g} units  |  Record: {player['win_count']}-{player['loss_count']} "
            f"({player['win_count'] / player['results'] * 100:.0f}% win rate)"
        )

    all_time_net = all_time_wins - all_time_losses
    entry_rows = fetch_all_rows("unit_entries", "message_id,user_id,total_units")
    pending_rows = [
        row for row in entry_rows
        if str(row.get("message_id")) not in settled_message_ids
        and str(row.get("user_id")) in tracked_user_ids
    ]
    pending_units = sum(float(row.get("total_units", 0) or 0) for row in pending_rows)
    embed_color = discord.Color.green() if net > 0 else discord.Color.red() if net < 0 else discord.Color.gold()
    status_icon = "📈" if net > 0 else "📉" if net < 0 else "➖"
    embed = discord.Embed(
        title="Playmaker Picks | Unit Summary",
        description=f"Results for **{date_label}**",
        color=embed_color,
    )
    embed.set_author(name="Playmaker Picks Team", icon_url=bot.user.display_avatar.url)
    embed.add_field(
        name=f"{status_icon} Daily Results",
        value=f"Net\n**{net:+g} units**\n\n✅ Wins\n+{wins:g} units\n\n❌ Losses\n-{losses:g} units\n\n📋 Results\n{len(rows)}\n\n⏳ Pending\n{len(pending_rows)} bets",
        inline=True,
    )
    embed.add_field(
        name="📊 Period Totals",
        value=f"📈 **7-Day**\n**{totals['week']:+g} units**\n\n🔄 **Month-to-Date**\n**{totals['month']:+g} units**\n\n🏆 **Year-to-Date**\n**{totals['year']:+g} units**",
        inline=True,
    )
    embed.add_field(
        name="🏆 All-Time Summary",
        value=f"Net\n**{all_time_net:+g} units**\n\n✅ Wins\n+{all_time_wins:g} units\n\n❌ Losses\n-{all_time_losses:g} units\n\n📋 Results\n{len(all_time_rows)}",
        inline=True,
    )
    leaderboard_lines = []
    for index, (player_name, player, player_net) in enumerate(ranked_players[:3]):
        medal = ("🥇", "🥈", "🥉")[index]
        win_rate = player["win_count"] / player["results"] * 100
        leaderboard_lines.append(f"{medal} **{player_name}** — **{player_net:+g} units**\n{player['win_count']}-{player['loss_count']} record | {win_rate:.0f}% win rate")
    if leaderboard_lines:
        embed.add_field(name="🏅 Top Playmakers", value="\n".join(leaderboard_lines), inline=False)
    breakdown_chunks = []
    current_chunk = []
    current_length = 0
    for line in player_lines:
        if current_chunk and current_length + len(line) + 1 > 1000:
            breakdown_chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(line)
        current_length += len(line) + 1
    if current_chunk:
        breakdown_chunks.append("\n".join(current_chunk))
    for index, chunk in enumerate(breakdown_chunks[:20]):
        field_name = "Playmaker Breakdown" if index == 0 else "Playmaker Breakdown (continued)"
        embed.add_field(name=field_name, value=chunk, inline=False)
    embed.set_footer(text=f"Updated every 4 hours • {now.strftime('%I:%M %p ET').lstrip('0')}")

    async for message in channel.history(limit=50):
        if message.author == bot.user and message.embeds and message.embeds[0].title == "Playmaker Picks | Unit Summary":
            await message.edit(content=None, embed=embed)
            return

    await channel.send(embed=embed)


def is_tracker_admin(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild and interaction.user.guild_permissions.manage_guild)


async def validate_tracking_data() -> dict[str, int]:
    summary = {"entries_checked": 0, "results_checked": 0, "matches": 0, "mismatches": 0}
    if supabase is None or not MONITORED_CHANNEL_ID:
        return summary

    channel = bot.get_channel(MONITORED_CHANNEL_ID)
    if channel is None:
        return summary

    entries = fetch_all_rows("unit_entries", "message_id,user_id,total_units")
    results = fetch_all_rows("unit_results", "message_id,user_id,total_units,result")
    result_keys = {(str(row.get("message_id")), str(row.get("user_id")), row.get("result")) for row in results}
    messages = {}

    async def get_message(message_id: str):
        if message_id not in messages:
            try:
                messages[message_id] = await channel.fetch_message(int(message_id))
            except (discord.NotFound, discord.HTTPException):
                messages[message_id] = None
        return messages[message_id]

    for entry in entries:
        summary["entries_checked"] += 1
        message_id = str(entry.get("message_id"))
        message = await get_message(message_id)
        values = extract_values(message.content) if message else []
        member = None
        if message:
            member = channel.guild.get_member(message.author.id)
            if member is None:
                try:
                    member = await channel.guild.fetch_member(message.author.id)
                except discord.HTTPException:
                    member = None
        valid = bool(
            message
            and str(message.author.id) == str(entry.get("user_id"))
            and values
            and float(values[0]) == float(entry.get("total_units", 0) or 0)
            and member_has_tracked_role(member)
        )
        if valid:
            summary["matches"] += 1
            logger.info("TRACKING_MATCH entry message=%s user=%s", message_id, entry.get("user_id"))
        else:
            summary["mismatches"] += 1
            logger.warning("TRACKING_MISMATCH entry message=%s user=%s", message_id, entry.get("user_id"))

    for result in results:
        summary["results_checked"] += 1
        message_id = str(result.get("message_id"))
        message = await get_message(message_id)
        valid = False
        if message:
            values = extract_values(message.content)
            member = None
            try:
                member = channel.guild.get_member(int(result["user_id"]))
            except (TypeError, ValueError):
                member = None
            if member is None and result.get("user_id"):
                try:
                    member = await channel.guild.fetch_member(int(result["user_id"]))
                except (ValueError, discord.HTTPException):
                    member = None
            emoji = "✅" if result.get("result") == "win" else "❌"
            reaction_users = set()
            for reaction in message.reactions:
                reaction_name = reaction.emoji if isinstance(reaction.emoji, str) else getattr(reaction.emoji, "name", None)
                if reaction_name == emoji:
                    async for user in reaction.users():
                        reaction_users.add(str(user.id))
            valid = bool(
                values
                and float(values[0]) == float(result.get("total_units", 0) or 0)
                and str(result.get("user_id")) in reaction_users
                and member_has_tracked_role(member)
                and (message_id, str(result.get("user_id")), result.get("result")) in result_keys
            )
        if valid:
            summary["matches"] += 1
            logger.info("TRACKING_MATCH result message=%s user=%s result=%s", message_id, result.get("user_id"), result.get("result"))
        else:
            summary["mismatches"] += 1
            logger.warning("TRACKING_MISMATCH result message=%s user=%s result=%s", message_id, result.get("user_id"), result.get("result"))

    return summary


@command_tree.command(name="refresh_tracker", description="Refresh the Playmaker Picks tracker embed now")
async def refresh_tracker(interaction: discord.Interaction):
    if not is_tracker_admin(interaction):
        await interaction.response.send_message("You need Manage Server permission to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await update_daily_breakdown()
    await interaction.followup.send("Tracker refreshed.", ephemeral=True)


@command_tree.command(name="rescan_history", description="Rescan recent betting history and refresh the tracker")
async def rescan_history(interaction: discord.Interaction):
    if not is_tracker_admin(interaction):
        await interaction.response.send_message("You need Manage Server permission to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await scan_monitored_channel()
    await update_daily_breakdown()
    await interaction.followup.send("History rescanned and tracker refreshed.", ephemeral=True)


@command_tree.command(name="validate_tracking", description="Validate database entries against Discord messages and reactions")
async def validate_tracking(interaction: discord.Interaction):
    if not is_tracker_admin(interaction):
        await interaction.response.send_message("You need Manage Server permission to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    summary = await validate_tracking_data()
    await interaction.followup.send(
        f"Validation complete. Entries: {summary['entries_checked']}; "
        f"results: {summary['results_checked']}; matches: {summary['matches']}; "
        f"mismatches: {summary['mismatches']}. Details were recorded in the bot log.",
        ephemeral=True,
    )


@command_tree.command(name="role_members", description="List current members of the tracking role")
async def role_members(interaction: discord.Interaction):
    if not is_tracker_admin(interaction):
        await interaction.response.send_message("You need Manage Server permission to use this command.", ephemeral=True)
        return
    members_by_id = {}
    if interaction.guild:
        for role_id in TRACKED_ROLE_IDS:
            role = interaction.guild.get_role(role_id)
            if role:
                members_by_id.update({member.id: member for member in role.members})
    members = list(members_by_id.values())
    names = ", ".join(member.display_name for member in members) or "No members found."
    await interaction.response.send_message(f"Tracking role members ({len(members)}): {names}", ephemeral=True)


@bot.event
async def on_ready():
    global commands_synced

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    guild = bot.get_guild(GUILD_ID) if GUILD_ID else None
    if guild and TRACKED_ROLE_IDS:
        members_by_id = {}
        for role_id in TRACKED_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                members_by_id.update({member.id: member for member in role.members})
        members = list(members_by_id.values())
        print(f"Tracking role members: {len(members)}")
        print("Tracking role names: " + ", ".join(member.display_name for member in members))
    try:
        if bot.user.name != "Playmaker Picks Team":
            await bot.user.edit(username="Playmaker Picks Team")
    except discord.HTTPException as error:
        print(f"DEBUG: Could not update bot username: {error}")
    await update_daily_breakdown()
    if not scheduled_channel_update.is_running():
        scheduled_channel_update.start()
    if not commands_synced:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            command_tree.copy_global_to(guild=guild)
            await command_tree.sync(guild=guild)
        else:
            await command_tree.sync()
        commands_synced = True
    asyncio.create_task(scan_monitored_channel())


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.guild:
        return

    if MONITORED_CHANNEL_ID and message.channel.id != MONITORED_CHANNEL_ID:
        return
    if not member_has_tracked_role(message.author):
        return

    config = load_config()
    tracked = set(config.get("tracked_user_ids", []))
    if tracked and message.author.id not in tracked:
        return

    values = extract_values(
        message.content,
        require_keyword=config.get("require_keyword", ""),
        keyword_case_insensitive=config.get("keyword_case_insensitive", True),
        pattern=config.get("number_pattern", r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b"),
    )
    if not values:
        return

    insert_unit_entry(message, values[0], config)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    print(f"DEBUG: Reaction detected - emoji: {payload.emoji}, channel: {payload.channel_id}, message: {payload.message_id}")
    
    if payload.emoji is None:
        print("DEBUG: Emoji is None, returning")
        return

    sign = reaction_sign(getattr(payload.emoji, "name", None))
    print(f"DEBUG: Reaction sign: {sign} (emoji name: {getattr(payload.emoji, 'name', None)})")
    if sign == 0:
        print("DEBUG: Sign is 0, not a tracked reaction")
        return

    if MONITORED_CHANNEL_ID and payload.channel_id != MONITORED_CHANNEL_ID:
        print(f"DEBUG: Channel {payload.channel_id} != monitored {MONITORED_CHANNEL_ID}")
        return

    reacting_member = await fetch_member_for_payload(payload)
    if not member_has_tracked_role(reacting_member):
        print(f"DEBUG: User {payload.user_id} does not have tracked role")
        return

    config = load_config()
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        print(f"DEBUG: Channel {payload.channel_id} not found")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        print(f"DEBUG: Message {payload.message_id} not found")
        return

    values = extract_values(
        message.content,
        require_keyword=config.get("require_keyword", ""),
        keyword_case_insensitive=config.get("keyword_case_insensitive", True),
        pattern=config.get("number_pattern", r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b"),
    )
    print(f"DEBUG: Extracted values: {values}")
    if not values:
        print("DEBUG: No U values found in message")
        return

    result = "win" if sign > 0 else "loss"
    print(f"DEBUG: Recording result: {result} for {values[0]}U")
    if supabase is not None:
        opposite = "loss" if result == "win" else "win"
        supabase.table("unit_results").delete().eq("message_id", str(payload.message_id)).eq("user_id", str(payload.user_id)).eq("result", opposite).execute()
        existing = supabase.table("unit_results").select("id").eq("message_id", str(payload.message_id)).eq("user_id", str(payload.user_id)).eq("result", result).execute()
        if existing.data:
            return

    insert_unit_result(message, values[0], result, config)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.emoji is None:
        return

    sign = reaction_sign(getattr(payload.emoji, "name", None))
    if sign == 0:
        return

    if MONITORED_CHANNEL_ID and payload.channel_id != MONITORED_CHANNEL_ID:
        return

    reacting_member = await fetch_member_for_payload(payload)
    if not member_has_tracked_role(reacting_member):
        return

    config = load_config()
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return

    values = extract_values(
        message.content,
        require_keyword=config.get("require_keyword", ""),
        keyword_case_insensitive=config.get("keyword_case_insensitive", True),
        pattern=config.get("number_pattern", r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b"),
    )
    if not values:
        return

    result = "win" if sign > 0 else "loss"
    if supabase is not None:
        existing = supabase.table("unit_results").select("id").eq("message_id", str(payload.message_id)).eq("user_id", str(payload.user_id)).eq("result", result).execute()
        if existing.data:
            supabase.table("unit_results").delete().eq("message_id", str(payload.message_id)).eq("user_id", str(payload.user_id)).eq("result", result).execute()


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing. Set it in your .env file.")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required.")
    bot.run(TOKEN)
