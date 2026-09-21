from datetime import datetime, timezone

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


team_summary_service = TeamSummaryService()
