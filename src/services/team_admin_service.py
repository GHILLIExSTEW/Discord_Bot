from __future__ import annotations

from typing import Any

from src.config import ROSTER_SYNC_SPORT_FILTERS, ROSTER_SYNC_SPORTS
from src.services.supabase_service import supabase_service


class TeamAdminService:
    def ensure_user(self, discord_user_id: str, username: str, display_name: str | None = None) -> dict[str, Any]:
        existing = supabase_service.select("users", "*", {"discord_user_id": discord_user_id})
        if existing.data:
            return existing.data[0]

        inserted = supabase_service.insert("users", {
            "discord_user_id": discord_user_id,
            "username": username,
            "display_name": display_name or username,
            "role": "member",
            "is_active": True,
        })
        return inserted.data[0]

    def ensure_team(self, team_name: str, sport_id: int | None = None, league_id: int | None = None, short_name: str | None = None) -> dict[str, Any]:
        normalized_name = " ".join((team_name or "").strip().split())
        if not normalized_name:
            raise ValueError("Team name is required.")

        existing = supabase_service.select("teams", "*", {"name": normalized_name})
        if existing.data:
            return existing.data[0]

        payload = {
            "sport_id": sport_id,
            "league_id": league_id,
            "api_team_id": f"manual-{normalized_name.lower().replace(' ', '-')}",
            "name": normalized_name,
            "short_name": short_name or normalized_name[:3].upper(),
            "country": "Manual",
            "is_active": True,
        }
        inserted = supabase_service.insert("teams", payload)
        return inserted.data[0]

    def assign_user_to_team(self, discord_user_id: str, team_id: int) -> dict[str, Any]:
        user = self.ensure_user(discord_user_id, discord_user_id)
        user_id = int(user["id"])
        updated = supabase_service.update("users", {"team_id": team_id}, {"id": user_id})
        return updated.data[0]

    def force_roster_sync(self) -> dict[str, Any]:
        from src.services.roster_sync_service import RosterSyncService

        service = RosterSyncService()
        total = 0
        for sport_slug in ROSTER_SYNC_SPORTS:
            total += service.sync_sport(
                sport_slug.replace("-", " ").title(),
                sport_slug,
                ROSTER_SYNC_SPORT_FILTERS.get(sport_slug, []),
            )
        return {"synced_record_count": total}


team_admin_service = TeamAdminService()
