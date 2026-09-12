import os
from datetime import datetime

import discord
from dotenv import load_dotenv
from supabase import Client, create_client

from tally_logic import (
    build_reaction_key,
    extract_values,
    format_result_channel_name,
    load_config,
    reaction_sign,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RESULT_CHANNEL_ID = int(os.getenv("RESULT_CHANNEL_ID", "0")) if os.getenv("RESULT_CHANNEL_ID") else None
MONITORED_CHANNEL_ID = int(os.getenv("MONITORED_CHANNEL_ID", "0")) if os.getenv("MONITORED_CHANNEL_ID") else None

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = discord.Client(intents=intents)

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def now_iso_for_config(config: dict) -> str:
    tz_name = config.get("timezone", "America/New_York")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).isoformat()
    except Exception:
        return datetime.now().isoformat()


def fetch_totals_for_window() -> dict[str, float]:
    if supabase is None:
        return {"day": 0.0, "week": 0.0, "year": 0.0}

    now = datetime.now()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_day.replace(day=start_day.day - start_day.weekday())
    start_year = start_day.replace(month=1, day=1)

    totals = {"day": 0.0, "week": 0.0, "year": 0.0}
    windows = [
        ("day", start_day.isoformat(), now.isoformat()),
        ("week", start_week.isoformat(), now.isoformat()),
        ("year", start_year.isoformat(), now.isoformat()),
    ]

    for key, start, end in windows:
        resp = supabase.table("unit_results").select("total_units", "result", "created_at").gte("created_at", start).lt("created_at", end).execute()
        for row in resp.data or []:
            amount = float(row.get("total_units", 0) or 0)
            result = row.get("result")
            if result == "win":
                totals[key] += amount
            elif result == "loss":
                totals[key] -= amount
    return totals


def update_result_channel_name():
    if supabase is None:
        return

    channel_id = RESULT_CHANNEL_ID or MONITORED_CHANNEL_ID
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        return

    totals = fetch_totals_for_window()
    name = format_result_channel_name(totals["day"], totals["week"], totals["year"])
    try:
        bot.loop.create_task(channel.edit(name=name))
    except Exception:
        pass


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
    async for message in channel.history(limit=200):
        if message.author.bot:
            continue
        values = extract_values(
            message.content,
            require_keyword=config.get("require_keyword", ""),
            keyword_case_insensitive=config.get("keyword_case_insensitive", True),
            pattern=config.get("number_pattern", r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b"),
        )
        if not values:
            continue
        insert_unit_entry(message, values[0], config)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await scan_monitored_channel()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.guild:
        return

    if MONITORED_CHANNEL_ID and message.channel.id != MONITORED_CHANNEL_ID:
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
    if payload.emoji is None:
        return

    sign = reaction_sign(getattr(payload.emoji, "name", None))
    if sign == 0:
        return

    if MONITORED_CHANNEL_ID and payload.channel_id != MONITORED_CHANNEL_ID:
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
            return

    insert_unit_result(message, values[0], result, config)
    update_result_channel_name()


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.emoji is None:
        return

    sign = reaction_sign(getattr(payload.emoji, "name", None))
    if sign == 0:
        return

    if MONITORED_CHANNEL_ID and payload.channel_id != MONITORED_CHANNEL_ID:
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
            update_result_channel_name()


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing. Set it in your .env file.")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required.")
    bot.run(TOKEN)
