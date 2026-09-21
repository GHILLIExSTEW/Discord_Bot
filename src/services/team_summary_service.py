from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.services.supabase_service import supabase_service


class TeamSummaryService:
    def __init__(self) -> None:
        self.table = "team_daily_summary"

    def build_daily_summary(self, report_date: str | None = None) -> int:
        if report_date is None:
            report_date = datetime.now(timezone.utc).date().isoformat()

        result = supabase_service.select("plays", "id, team_id, sport_id, league_id, status, units")
        rows = result.data or []

        grouped: dict[tuple[int, int, int], dict] = {}
        for row in rows:
            status = row.get("status")
            if status not in {"win", "loss", "void", "partial"}:
                continue
            if row.get("team_id") is None:
                continue
            key = (int(row["sport_id"]), int(row["team_id"]), int(row["league_id"]) if row.get("league_id") is not None else 0)
            bucket = grouped.setdefault(key, {
                "sport_id": int(row["sport_id"]),
                "team_id": int(row["team_id"]),
                "league_id": int(row["league_id"]) if row.get("league_id") is not None else None,
                "wins": 0,
                "losses": 0,
                "voids": 0,
                "partials": 0,
                "net_units": 0.0,
            })

            units = float(row.get("units") or 0)
            if status == "win":
                bucket["wins"] += 1
                bucket["net_units"] += units
            elif status == "loss":
                bucket["losses"] += 1
                bucket["net_units"] -= units
            elif status == "void":
                bucket["voids"] += 1
            elif status == "partial":
                bucket["partials"] += 1
                bucket["net_units"] += units * 0.5

        for summary in grouped.values():
            payload = {
                "sport_id": summary["sport_id"],
                "league_id": summary["league_id"],
                "team_id": summary["team_id"],
                "report_date": report_date,
                "wins": summary["wins"],
                "losses": summary["losses"],
                "voids": summary["voids"],
                "partials": summary["partials"],
                "net_units": float(summary["net_units"]),
            }
            supabase_service.upsert(self.table, payload, ["sport_id", "team_id", "report_date"])

        return len(grouped)

    def fetch_daily_summary(self, report_date: str | None = None) -> list[dict]:
        if report_date is None:
            report_date = datetime.now(timezone.utc).date().isoformat()

        try:
            response = supabase_service.select("team_daily_summary", "*", {"report_date": report_date})
        except RuntimeError:
            return []
        return response.data or []

    def build_playmaker_report(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        today = now.date()
        plays = supabase_service.select(
            "plays",
            "id,user_id,units,status,created_at,settled_at",
        ).data or []
        users = supabase_service.select("users", "id,display_name,username").data or []
        names = {row["id"]: row.get("display_name") or row.get("username") or str(row["id"]) for row in users}

        def timestamp(row: dict) -> datetime:
            value = row.get("settled_at") if row.get("status") != "open" else row.get("created_at")
            if not value:
                return now
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

        def empty() -> dict:
            return {"net": 0.0, "wins": 0, "losses": 0, "win_units": 0.0, "loss_units": 0.0, "results": 0}

        def add(bucket: dict, row: dict) -> None:
            status = row.get("status")
            units = float(row.get("units") or 0)
            if status == "win":
                bucket["wins"] += 1
                bucket["net"] += units
                bucket["win_units"] += units
            elif status == "loss":
                bucket["losses"] += 1
                bucket["net"] -= units
                bucket["loss_units"] += units
            elif status in {"void", "partial"}:
                if status == "partial":
                    bucket["net"] += units * 0.5
            else:
                return
            bucket["results"] += 1

        periods = {
            "daily": empty(),
            "seven_day": empty(),
            "month": empty(),
            "year": empty(),
            "all_time": empty(),
        }
        playmakers = defaultdict(empty)
        pending = 0
        for row in plays:
            if row.get("status") == "open":
                pending += 1
                continue
            event_time = timestamp(row)
            event_date = event_time.date()
            if event_date == today:
                add(periods["daily"], row)
            if event_date >= today - timedelta(days=6):
                add(periods["seven_day"], row)
            if event_date.year == today.year and event_date.month == today.month:
                add(periods["month"], row)
            if event_date.year == today.year:
                add(periods["year"], row)
            add(periods["all_time"], row)
            add(playmakers[row.get("user_id")], row)

        for bucket in playmakers.values():
            bucket["rate"] = round(bucket["wins"] / bucket["results"] * 100) if bucket["results"] else 0
        top = sorted(playmakers.items(), key=lambda item: (-item[1]["net"], -item[1]["wins"]))
        return {"date": today.isoformat(), "periods": periods, "pending": pending, "playmakers": [(names.get(user_id, str(user_id)), data) for user_id, data in top]}


team_summary_service = TeamSummaryService()
