from __future__ import annotations

from src.services.play_service import PlayService
from src.services.settlement_service import SettlementService
from src.services.supabase_service import supabase_service


class OfficialPlayService:
    def __init__(self) -> None:
        self.play_service = PlayService()
        self.settlement_service = SettlementService()

    def _ensure_default_sport(self) -> int:
        result = supabase_service.select("sports", "id", {"api_slug": "official"})
        if result.data:
            return int(result.data[0]["id"])

        inserted = supabase_service.insert("sports", {"name": "Official", "api_slug": "official", "is_active": True})
        return int(inserted.data[0]["id"])

    def _ensure_user(self, discord_user_id: str, username: str) -> int:
        existing = supabase_service.select("users", "id", {"discord_user_id": discord_user_id})
        if existing.data:
            return int(existing.data[0]["id"])

        inserted = supabase_service.insert("users", {
            "discord_user_id": discord_user_id,
            "username": username,
            "display_name": username,
            "role": "official",
            "is_active": True,
        })
        return int(inserted.data[0]["id"])

    def create_play_record(
        self,
        discord_user_id: str,
        username: str,
        units: float,
        legs: int,
        odds: str,
        play_text: str = "",
        team_name: str | None = None,
    ) -> dict:
        validation_error = self.play_service.validate_play(units, legs, odds)
        if validation_error:
            return {"error": validation_error["message"]}

        try:
            odds_value = self.play_service.normalize_odds(odds)
        except ValueError as exc:
            return {"error": str(exc)}

        to_win = self.play_service.calculate_to_win(float(units), odds_value)
        sport_id = self._ensure_default_sport()
        user_id = self._ensure_user(discord_user_id, username)

        payload = {
            "user_id": user_id,
            "team_id": None,
            "sport_id": sport_id,
            "league_id": None,
            "team_name": " ".join((team_name or "").strip().split()) or None,
            "units": float(units),
            "legs": int(legs),
            "odds": odds_value,
            "status": "open",
            "play_text": play_text or "",
            "message_id": None,
        }

        inserted = supabase_service.insert("plays", payload)
        play_id = int(inserted.data[0]["id"])

        return {
            "play_id": play_id,
            "units": float(units),
            "legs": int(legs),
            "odds": odds_value,
            "odds_text": str(odds_value),
            "to_win": to_win,
            "user_name": username,
            "team_name": payload["team_name"],
            "play_text": play_text or "",
            "summary": f"{float(units):g}u • {int(legs)}-leg • {odds_value}",
        }

    def attach_message_id(self, play_id: int, message_id: int) -> dict:
        return supabase_service.update("plays", {"message_id": str(message_id)}, {"id": int(play_id)})

    def settle_play(self, play_id: int, result: str) -> dict:
        if result not in {"win", "loss", "void", "partial", "regraded"}:
            raise ValueError(f"Unsupported result: {result}")

        tally = self.settlement_service.tally_for_result(result, float(self._fetch_play(play_id)["units"]))
        supabase_service.update(
            "plays",
            {"status": result, "settled_at": "now()", "settled_units": tally},
            {"id": int(play_id)},
        )
        return {"result": result, "tally": tally}

    def regrade_play(self, play_id: int, legs_left: int, odds: int, note: str = "") -> dict:
        validated = self.settlement_service.validate_regrade(legs_left, odds)
        supabase_service.update(
            "plays",
            {
                "status": "regraded",
                "legs": validated["legs_left"],
                "odds": validated["odds"],
                "play_text": note,
            },
            {"id": int(play_id)},
        )
        return {"result": "regraded", **validated}

    def _fetch_play(self, play_id: int) -> dict:
        result = supabase_service.select("plays", "*", {"id": int(play_id)})
        if not result.data:
            raise ValueError(f"Play {play_id} not found.")
        return result.data[0]


official_play_service = OfficialPlayService()
