from datetime import datetime, timedelta, timezone
import math

from src.datetime_utils import parse_iso_datetime
from src.services.supabase_service import supabase_service
from src.services.api_budget_service import member_request_user
from src.services.api_sports_service import ApiSportsService, normalize_game
from src.services.api_sports_multi_service import ApiSportsMultiService, DATE_PRODUCTS, DATE_PRODUCT_PARAMS, normalize_event

SPORTS = {
    "nfl": "NFL", "ncaa": "College football", "basketball": "Basketball",
    "football": "Soccer", "hockey": "Hockey", "baseball": "Baseball",
}
FINAL = {"FT", "AOT"}


def score(value) -> float | None:
    if isinstance(value, dict):
        value = value.get("total")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def team_name(value: str) -> str:
    value = " ".join(value.split())
    if not value or len(value) > 100:
        raise ValueError("Enter the full team name (1-100 characters).")
    return value


class MemberStatsService:
    """Read existing event caches only; member requests never refresh providers."""

    def __init__(self, database=None, clock=None):
        self.db = database or supabase_service
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def events(self, sport: str, upcoming: bool, team: str | None = None) -> list[dict]:
        if sport not in SPORTS:
            raise ValueError("Select a supported sport.")
        now = self.clock()
        start = now if upcoming else now - timedelta(days=30)
        end = now + timedelta(days=7) if upcoming else now
        nfl = sport == "nfl"
        table = "api_sports_nfl_games" if nfl else "api_sports_events"
        time_column = "kickoff_at" if nfl else "start_at"
        fields = (
            "game_id,kickoff_at,home_team_name,away_team_name,home_score,away_score,status_short,synced_at"
            if nfl else
            "event_id,start_at,home_name,away_name,home_score,away_score,status_code,synced_at"
        )
        rows = []
        # Two exact-name queries avoid ambiguous substring matches and filter syntax interpolation.
        for side in (["home", "away"] if team is not None else [None]):
            query = self.db._ensure_client().table(table).select(fields)
            if not nfl:
                query = query.eq("sport_slug", sport)
            if side:
                name = team_name(team)
                pattern = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                query = query.ilike(f"{side}_team_name" if nfl else f"{side}_name", pattern)
            data = query.gte(time_column, start.isoformat()).lte(time_column, end.isoformat()).order(
                time_column, desc=not upcoming,
            ).limit(100).execute().data
            if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                raise RuntimeError("Sports cache returned an invalid response.")
            for row in data:
                event = {
                    "id": row["game_id"] if nfl else row["event_id"],
                    "start": row[time_column], "home": row["home_team_name"] if nfl else row["home_name"],
                    "away": row["away_team_name"] if nfl else row["away_name"],
                    "home_score": score(row["home_score"]), "away_score": score(row["away_score"]),
                    "status": row["status_short"] if nfl else row["status_code"],
                    "synced_at": row["synced_at"],
                }
                if team is None or name.casefold() in {str(event["home"]).casefold(), str(event["away"]).casefold()}:
                    rows.append(event)
        unique = {row["id"]: row for row in rows}
        return sorted(unique.values(), key=lambda row: parse_iso_datetime(row["start"]), reverse=not upcoming)

    def report(self, mode: str, sport: str, team: str | None = None, opponent: str | None = None) -> tuple[str, str]:
        if mode not in {"matchup", "teamstats", "schedule", "results"}:
            raise ValueError("Unknown stats report.")
        if team is not None:
            team = team_name(team)
        if mode in {"teamstats", "matchup"} and team is None:
            raise ValueError("Enter a full team name.")
        if mode == "matchup":
            if opponent is None:
                raise ValueError("Enter both full team names.")
            opponent = team_name(opponent)
            if team.casefold() == opponent.casefold():
                raise ValueError("Choose two different teams.")
        rows = self.events(sport, mode in {"schedule", "matchup"}, team)
        if mode == "matchup":
            rows = [row for row in rows if opponent.casefold() in {
                str(row["home"]).casefold(), str(row["away"]).casefold(),
            }]
        if mode in {"results", "teamstats"}:
            rows = [row for row in rows if row["status"] in FINAL]
        title = f"{SPORTS[sport]} • {mode.title()}"
        if not rows:
            return title, "No matching cached events in the next 7 days or past 30 days, as applicable. Use full team names. No live lookup was made."
        selected = rows[:10]
        lines = []
        for row in selected:
            stamp = int(parse_iso_datetime(row["start"]).timestamp())
            home_score, away_score = row["home_score"], row["away_score"]
            result = f"{home_score:g}–{away_score:g}" if home_score is not None and away_score is not None else "Scores unavailable"
            lines.append(f"<t:{stamp}:f> • {row['home']} vs {row['away']} • {row['status']} • {result}")
        if mode == "teamstats":
            wins = losses = ties = 0
            points_for = points_against = 0.0
            for row in selected:
                own, other = (row["home_score"], row["away_score"]) if str(row["home"]).casefold() == team.casefold() else (row["away_score"], row["home_score"])
                if own is not None and other is not None:
                    wins += own > other
                    losses += own < other
                    ties += own == other
                    points_for += own
                    points_against += other
            scored = wins + losses + ties
            summary = f"Recent cached form: {wins}W / {losses}L / {ties}T from {scored} scored games. Not season standings."
            if scored:
                summary += f"\nAverage scored: {points_for / scored:.1f}; conceded: {points_against / scored:.1f}."
            lines.insert(0, summary)
        updated = min(parse_iso_datetime(row["synced_at"]) for row in selected)
        lines.append(f"\nShowing {len(selected)} cached events maximum. Oldest displayed update: <t:{int(updated.timestamp())}:R>. Data may be stale or incomplete; scores are not betting advice.")
        return title, "\n".join(lines)

    def refresh(self, sport: str, user_id: int) -> str:
        if sport not in SPORTS:
            raise ValueError("Select a supported sport.")
        now = self.clock()
        day = now.astimezone(timezone.utc).date().isoformat()
        nfl = sport == "nfl"
        query = self.db._ensure_client().table("api_sports_nfl_games" if nfl else "api_sports_events").select("synced_at")
        if not nfl:
            query = query.eq("sport_slug", sport)
        column = "kickoff_at" if nfl else "start_at"
        midnight = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        data = query.gte(column, midnight.isoformat()).lt(
            column, (midnight + timedelta(days=1)).isoformat(),
        ).order("synced_at", desc=True).limit(1).execute().data
        if not isinstance(data, list):
            raise RuntimeError("Refresh cache returned an invalid response.")
        if data and timedelta(0) <= now - parse_iso_datetime(data[0]["synced_at"]) < timedelta(minutes=5):
            return "Today's cache was updated within five minutes; reused it without a provider call. Other dates remain cached."
        token = member_request_user.set(str(user_id))
        try:
            if sport == "nfl":
                api = ApiSportsService(client=self.db._ensure_client())
                rows = api._request("games", {"date": day, "league": 1})
                api._upsert("api_sports_nfl_games", [normalize_game(row, now) for row in rows], "game_id")
            else:
                api = ApiSportsMultiService(client=self.db._ensure_client())
                rows = api._request(*DATE_PRODUCTS[sport], params={"date": day, **DATE_PRODUCT_PARAMS.get(sport, {})})
                api._store_events([normalize_event(sport, row, now) for row in rows])
        finally:
            member_request_user.reset(token)
        return f"Provider refresh completed for {day} (UTC) only, at <t:{int(now.timestamp())}:T>. Other dates remain cached. Provider data may lag; this is not a real-time guarantee."
