from datetime import datetime, timezone
from typing import Any

from src.config import ROSTER_SYNC_SPORT_FILTERS
from src.services.supabase_service import supabase_service
from src.services.api_sports_service import api_sports_service


class RosterSyncService:
    def __init__(self) -> None:
        self.job_name = "roster_sync"
        self.current_sport_slug = "volleyball"

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get_active_season(league_payload: dict[str, Any], now: datetime | None = None) -> int | str | None:
        seasons = (league_payload.get("seasons") or [])
        if not seasons:
            return None

        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        for season in seasons:
            if season.get("current") is True:
                year = season.get("year", season.get("season"))
                if isinstance(year, (int, str)) and year:
                    return year

        for season in seasons:
            start_text = season.get("start")
            end_text = season.get("end")
            year = season.get("year", season.get("season"))
            if not isinstance(year, (int, str)) or not year:
                continue
            if not start_text or not end_text:
                continue

            try:
                start_dt = datetime.fromisoformat(start_text)
                end_dt = datetime.fromisoformat(end_text)
            except ValueError:
                continue

            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            if start_dt <= now <= end_dt:
                return year

        upcoming = []
        for season in seasons:
            start_text = season.get("start")
            year = season.get("year", season.get("season"))
            if not start_text or not year:
                continue
            try:
                start_dt = datetime.fromisoformat(start_text)
            except ValueError:
                continue
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if now < start_dt and (start_dt - now).days <= 30:
                upcoming.append((start_dt, year))
        if upcoming:
            upcoming.sort(key=lambda item: item[0])
            return upcoming[0][1]

        has_explicit_current_flag = any("current" in season for season in seasons)
        if has_explicit_current_flag:
            return None

        year = seasons[0].get("year", seasons[0].get("season"))
        if isinstance(year, (int, str)) and year:
            return year
        return None

    @staticmethod
    def should_sync_league(league_payload: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
        if not filters:
            return True

        league_data = league_payload.get("league") or league_payload
        country_data = league_payload.get("country") or {}
        league_id = league_data.get("id")
        league_name = (league_data.get("name") or "").strip().lower()

        for filter_values in filters:
            if filter_values.get("country") is not None:
                expected_country = RosterSyncService._normalize_country(filter_values["country"])
                actual_country = RosterSyncService._normalize_country(country_data.get("name"))
                if actual_country != expected_country:
                    continue
            if filter_values.get("league_id") is not None:
                if int(filter_values["league_id"]) != int(league_id):
                    continue
            if filter_values.get("league_name") is not None:
                if league_name != str(filter_values["league_name"]).strip().lower():
                    continue
            return True

        return False

    @staticmethod
    def _normalize_country(country: Any) -> str:
        value = str(country or "").strip().lower()
        return {"united states": "usa", "united states of america": "usa"}.get(value, value)

    @staticmethod
    def _player_data(player_entry: dict[str, Any]) -> dict[str, Any]:
        return player_entry.get("player") or player_entry

    def sync_team_roster(
        self,
        sport_id: int,
        league_id: int,
        team_id: int,
        api_team_id: str,
        season_year: int,
    ) -> int:
        if self.current_sport_slug == "american-football":
            payload = api_sports_service.get_for_sport(
                self.current_sport_slug,
                "players/squads",
                {"team": api_team_id},
            )
            squad = (payload.get("response") or [{}])[0]
            players = squad.get("players") or []
        else:
            roster_season = season_year
            payload = api_sports_service.get_for_sport(
                self.current_sport_slug,
                "players",
                {"team": api_team_id, "season": season_year},
            )
            players = payload.get("response", [])
            if not players and self.current_sport_slug == "basketball" and isinstance(season_year, str) and "-" in season_year:
                start_year, end_year = season_year.split("-", 1)
                roster_season = f"{int(start_year) - 1}-{int(end_year) - 1}"
                payload = api_sports_service.get_for_sport(
                    self.current_sport_slug,
                    "players",
                    {"team": api_team_id, "season": roster_season},
                )
                players = payload.get("response", [])
        player_payloads = []
        api_player_ids = []
        for player_entry in players:
            player_data = self._player_data(player_entry)
            api_player_id = player_data.get("id")
            if api_player_id is None:
                continue
            api_player_id = str(api_player_id)
            api_player_ids.append(api_player_id)
            player_payloads.append({
                "sport_id": sport_id,
                "api_player_id": api_player_id,
                "full_name": player_data.get("name") or "Unknown Player",
                "first_name": player_data.get("firstname"),
                "last_name": player_data.get("lastname"),
                "position": player_data.get("position"),
                "is_active": True,
            })

        if not player_payloads:
            return 0

        supabase_service.upsert("players", player_payloads, ["sport_id", "api_player_id"])
        player_rows = supabase_service.select("players", "id,api_player_id", {"sport_id": sport_id}).data or []
        player_ids = {
            str(row["api_player_id"]): row["id"]
            for row in player_rows
            if str(row.get("api_player_id")) in api_player_ids
        }
        snapshot_payloads = []
        for api_player_id in api_player_ids:
            player_id = player_ids.get(api_player_id)
            if player_id is None:
                continue
            snapshot_payloads.append({
                "sport_id": sport_id,
                "league_id": league_id,
                "team_id": team_id,
                "player_id": player_id,
                "season": str(roster_season if self.current_sport_slug == "basketball" else season_year),
                "source": "api-sports",
                "is_active": True,
            })
        if snapshot_payloads:
            supabase_service.insert("roster_snapshots", snapshot_payloads)
        return len(snapshot_payloads)

    def sync_sport(self, sport_name: str, sport_slug: str, league_filters: list[dict[str, Any]] | None = None) -> int:
        self.current_sport_slug = sport_slug
        league_filters = league_filters or []
        sport_result = supabase_service.select("sports", "id", {"api_slug": sport_slug})
        if sport_result.data:
            sport_id = sport_result.data[0]["id"]
        else:
            sport_row = supabase_service.insert("sports", {"name": sport_name, "api_slug": sport_slug, "is_active": True})
            sport_id = sport_row.data[0]["id"]

        total = 0
        for league_filter in league_filters:
            request_filter = {}
            if league_filter.get("league_id") is not None:
                request_filter["id"] = league_filter["league_id"]
            elif league_filter.get("league_name") is not None:
                request_filter["name"] = league_filter["league_name"]
            # Country aliases are normalized locally because API-Sports uses USA.
            payload = api_sports_service.get_for_sport(sport_slug, "leagues", request_filter)
            leagues = payload.get("response", [])
            for league in leagues:
                if not self.should_sync_league(league, league_filters):
                    continue

                season_year = self.get_active_season(league)
                if season_year is None:
                    continue

                league_data = league.get("league") or league
                country_data = league.get("country") or {}
                api_league_id = str(league_data.get("id"))
                league_name = league_data.get("name") or "Unknown League"

                existing = supabase_service.select("leagues", "id", {"sport_id": sport_id, "api_league_id": api_league_id})
                if existing.data:
                    league_id = existing.data[0]["id"]
                    supabase_service.update(
                        "leagues",
                        {"name": league_name, "country": country_data.get("name"), "is_active": True},
                        {"id": league_id},
                    )
                else:
                    inserted = supabase_service.insert("leagues", {
                        "sport_id": sport_id,
                        "api_league_id": api_league_id,
                        "name": league_name,
                        "country": country_data.get("name"),
                        "is_active": True,
                    })
                    league_id = inserted.data[0]["id"]

                teams_payload = api_sports_service.get_for_sport(
                    sport_slug,
                    "teams",
                    {"league": api_league_id, "season": season_year},
                )
                teams = teams_payload.get("response", [])
                for team_entry in teams:
                    team_data = team_entry.get("team") or team_entry
                    api_team_id = str(team_data.get("id"))
                    team_name = team_data.get("name") or "Unknown Team"
                    short_name = team_data.get("shortName")
                    team_country = (team_data.get("country") or {}).get("name")

                    existing_team = supabase_service.select("teams", "id", {"sport_id": sport_id, "api_team_id": api_team_id})
                    if existing_team.data:
                        team_id = existing_team.data[0]["id"]
                        supabase_service.update(
                            "teams",
                            {
                                "league_id": league_id,
                                "name": team_name,
                                "short_name": short_name,
                                "country": team_country,
                                "is_active": True,
                            },
                            {"id": team_id},
                        )
                    else:
                        inserted_team = supabase_service.insert("teams", {
                            "sport_id": sport_id,
                            "league_id": league_id,
                            "api_team_id": api_team_id,
                            "name": team_name,
                            "short_name": short_name,
                            "country": team_country,
                            "is_active": True,
                        })
                        team_id = inserted_team.data[0]["id"]

                    total += 1
                    total += self.sync_team_roster(
                        sport_id,
                        league_id,
                        team_id,
                        api_team_id,
                        season_year,
                    )

        supabase_service.insert("sync_jobs", {
            "job_name": self.job_name,
            "started_at": self.now_iso(),
            "finished_at": self.now_iso(),
            "success": True,
            "record_count": total,
            "error_message": None,
        })
        return total

