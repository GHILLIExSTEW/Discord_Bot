from __future__ import annotations

from src.services.supabase_service import supabase_service
from src.config import WHOP_ACCOUNT_ID, WHOP_PAID_PLAN_IDS, WHOP_HIGHROLLER_PLAN_IDS


class MembershipService:
    """Read paid access from the private ledger; Discord roles are not payment evidence."""

    def __init__(self, database=None) -> None:
        self.db = database or supabase_service

    def has_paid_access(self, discord_user_id: int) -> bool:
        result = self.db._ensure_client().rpc(
            "discord_has_paid_access", {"p_discord_user_id": str(discord_user_id)},
        ).execute().data
        if not isinstance(result, bool):
            raise RuntimeError("Membership lookup returned an invalid access response.")
        return result

    def ready(self) -> None:
        # Fails at startup if the access migration is missing; no role-based fallback.
        self.has_paid_access(0)

    def has_highroller_access(self, discord_user_id: int) -> bool:
        if not WHOP_ACCOUNT_ID or not WHOP_HIGHROLLER_PLAN_IDS or not WHOP_HIGHROLLER_PLAN_IDS <= WHOP_PAID_PLAN_IDS:
            raise RuntimeError("Configure approved Whop HIGHROLLER plans and seller before using stats commands.")
        result = self.db._ensure_client().rpc(
            "discord_has_paid_plan_access", {
                "p_discord_user_id": str(discord_user_id),
                "p_account_id": WHOP_ACCOUNT_ID,
                "p_plan_ids": sorted(WHOP_HIGHROLLER_PLAN_IDS),
            },
        ).execute().data
        if not isinstance(result, bool):
            raise RuntimeError("HIGHROLLER lookup returned an invalid access response.")
        return result

    def paid_discord_ids(self) -> set[int]:
        rows = self.db._ensure_client().rpc("paid_discord_member_ids").execute().data
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or not str(row.get("discord_user_id", "")).isdigit()
            for row in rows
        ):
            raise RuntimeError("Membership lookup returned invalid Discord identities.")
        return {int(row["discord_user_id"]) for row in rows}
