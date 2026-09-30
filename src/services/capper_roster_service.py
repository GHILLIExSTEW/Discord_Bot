from __future__ import annotations

from typing import Any

from src.config import OPERATOR_ROLE_IDS
from src.services.supabase_service import supabase_service


class CapperRosterService:
    TABLE = "capper_role_roster"

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository or supabase_service

    def sync_member(self, discord_user_id: str, display_name: str, role_ids: set[int] | list[int]) -> bool:
        existing = self.repository.select(self.TABLE, "discord_user_id", {"discord_user_id": discord_user_id})
        is_authorized = bool(OPERATOR_ROLE_IDS.intersection(role_ids))
        payload = {
            "discord_user_id": discord_user_id,
            "display_name": display_name,
            "is_authorized": is_authorized,
        }

        if is_authorized:
            self.repository.upsert(self.TABLE, payload, ["discord_user_id"])
        elif existing.data:
            self.repository.update(self.TABLE, payload, {"discord_user_id": discord_user_id})

        return is_authorized

    def sync_guild_members(self, members: list[dict[str, Any]]) -> int:
        authorized_members = {
            member["discord_user_id"]: member
            for member in members
            if OPERATOR_ROLE_IDS.intersection(member["role_ids"])
        }
        if authorized_members:
            self.repository.upsert(self.TABLE, [
                {
                    "discord_user_id": member["discord_user_id"],
                    "display_name": member["display_name"],
                    "is_authorized": True,
                }
                for member in authorized_members.values()
            ], ["discord_user_id"])

        existing = self.repository.select(self.TABLE, "discord_user_id,display_name", {"is_authorized": True})
        for row in existing.data or []:
            discord_user_id = row["discord_user_id"]
            if discord_user_id in authorized_members:
                continue
            member = next((item for item in members if item["discord_user_id"] == discord_user_id), None)
            self.repository.update(self.TABLE, {
                "display_name": member["display_name"] if member else row["display_name"],
                "is_authorized": False,
            }, {"discord_user_id": discord_user_id})

        return len(authorized_members)


capper_roster_service = CapperRosterService()