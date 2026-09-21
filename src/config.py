import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_str(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


DISCORD_TOKEN = get_str("DISCORD_TOKEN")
APPLICATION_ID = get_int("APPLICATION_ID")
GUILD_ID = get_int("GUILD_ID")
SUPABASE_URL = get_str("SUPABASE_URL")
SUPABASE_KEY = get_str("SUPABASE_KEY")
API_SPORTS_KEY = get_str("API_SPORTS_KEY")
OPENAI_API_KEY = get_str("OPENAI_API_KEY")
OPENAI_VISION_MODEL = get_str("OPENAI_VISION_MODEL", "gpt-4.1-mini")
OPENAI_VISION_MODELS_RAW = get_str("OPENAI_VISION_MODELS", "")
VISION_FALLBACK_URL = get_str("VISION_FALLBACK_URL")
VISION_FALLBACK_API_KEY = get_str("VISION_FALLBACK_API_KEY")
VISION_FALLBACK_MODEL = get_str("VISION_FALLBACK_MODEL")
OFFICIAL_CHANNEL_ID = get_int("OFFICIAL_CHANNEL_ID")
TEAM_STATS_CHANNEL_ID = get_int("TEAM_STATS_CHANNEL_ID")
RESULT_CHANNEL_ID = get_int("RESULT_CHANNEL_ID")
MONITORED_CHANNEL_ID = get_int("MONITORED_CHANNEL_ID")

OFFICIAL_ROLE_IDS = {
    int(role_id.strip())
    for role_id in (os.getenv("OFFICIAL_ROLE_IDS", "").split(","))
    if role_id.strip().isdigit()
}
OPERATOR_ROLE_IDS = {
    int(role_id.strip())
    for role_id in (os.getenv("OPERATOR_ROLE_IDS", "").split(","))
    if role_id.strip().isdigit()
}

TIMEZONE = get_str("TIMEZONE", "America/New_York")
ROSTER_SYNC_HOURS = get_int("ROSTER_SYNC_HOURS", 4)
ROSTER_SYNC_CRON = get_str("ROSTER_SYNC_CRON", "0 */4 * * *")
ROSTER_SYNC_DAYS = get_int("ROSTER_SYNC_DAYS", 365)


def parse_csv_values(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


OPENAI_VISION_MODELS = [item.strip() for item in OPENAI_VISION_MODELS_RAW.split(",") if item.strip()]
if not OPENAI_VISION_MODELS:
    OPENAI_VISION_MODELS = [OPENAI_VISION_MODEL]


ROSTER_SYNC_SPORTS = parse_csv_values("ROSTER_SYNC_SPORTS")
ROSTER_SYNC_COUNTRIES = parse_csv_values("ROSTER_SYNC_COUNTRIES")
ROSTER_SYNC_LEAGUE_IDS = [
    int(item)
    for item in parse_csv_values("ROSTER_SYNC_LEAGUE_IDS")
    if item.isdigit()
]
ROSTER_SYNC_LEAGUE_NAMES = parse_csv_values("ROSTER_SYNC_LEAGUE_NAMES")
ROSTER_SYNC_FILTERS: list[dict[str, str | int]] = []
for country in ROSTER_SYNC_COUNTRIES:
    ROSTER_SYNC_FILTERS.append({"country": country})
for league_id in ROSTER_SYNC_LEAGUE_IDS:
    ROSTER_SYNC_FILTERS.append({"league_id": league_id})
for league_name in ROSTER_SYNC_LEAGUE_NAMES:
    ROSTER_SYNC_FILTERS.append({"league_name": league_name})
if not ROSTER_SYNC_FILTERS:
    ROSTER_SYNC_FILTERS = [{"country": "United States"}]

if not ROSTER_SYNC_SPORTS:
    ROSTER_SYNC_SPORTS = ["american-football"]

ROSTER_SYNC_SPORT_FILTERS: dict[str, list[dict[str, str | int]]] = {
    "volleyball": ROSTER_SYNC_FILTERS,
    "american-football": [
        {"league_id": league_id}
        for league_id in (ROSTER_SYNC_LEAGUE_IDS or [2, 1])
    ],
    "basketball": [{"league_id": 12}],
}

DEFAULT_CONFIG = {
    "timezone": TIMEZONE,
    "tracked_user_ids": [],
    "allowed_channel_ids": [],
}
