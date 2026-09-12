import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_CONFIG = {
    "tracked_user_ids": [],
    "allowed_channel_ids": [],
    "number_pattern": r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b",
    "require_keyword": "U",
    "keyword_case_insensitive": True,
    "ignore_bots": True,
    "timezone": "America/New_York",
    "result_channel_id": None,
}


def load_config(path: str | Path = "config.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    with config_path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)

    merged = DEFAULT_CONFIG.copy()
    merged.update(loaded)
    return merged


def extract_values(content: str, require_keyword: str = "", keyword_case_insensitive: bool = True, pattern: str = r"[-+]?\d+(?:\.\d+)?") -> list[float]:
    text = content or ""
    keyword = (require_keyword or "").strip()

    if keyword:
        haystack = text.lower() if keyword_case_insensitive else text
        target = keyword.lower() if keyword_case_insensitive else keyword
        if target not in haystack:
            return []

    matches = re.findall(pattern, text)
    return [float(value) for value in matches]


def period_bounds(period: str, now: datetime | None = None, timezone_name: str = "America/New_York") -> tuple[datetime, datetime]:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = None

    if now is None:
        current = datetime.now(tz) if tz else datetime.now()
    else:
        current = now

    start_of_day = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "day":
        start = start_of_day
    elif period == "week":
        start = start_of_day - timedelta(days=start_of_day.weekday())
    elif period == "month":
        start = start_of_day.replace(day=1)
    elif period == "year":
        start = start_of_day.replace(month=1, day=1)
    else:
        raise ValueError(f"Unsupported period: {period}")

    return start, current


def reaction_sign(emoji_name: str | None) -> int:
    emoji = (emoji_name or "").lower()
    if emoji in {"green_check", "✅", "check", "checkmark", "success"}:
        return 1
    if emoji in {"red_x", "❌", "x", "cross", "fail"}:
        return -1
    return 0


def format_result_channel_name(day_total: float, week_total: float, year_total: float) -> str:
    return f"D: {day_total:+g} | W: {week_total:+g} | Y: {year_total:+g}"


def build_reaction_key(message_id, user_id, emoji_name: str) -> str:
    return f"{str(message_id)}:{str(user_id)}:{emoji_name}"
