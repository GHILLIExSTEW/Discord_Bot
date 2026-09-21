from __future__ import annotations

from typing import Any


class SettlementService:
    @staticmethod
    def tally_for_result(result: str, units: float) -> float:
        normalized = (result or "").strip().lower()
        if normalized == "win":
            return float(units)
        if normalized == "loss":
            return float(-units)
        if normalized == "partial":
            return float(units * 0.5)
        if normalized == "void":
            return 0.0
        if normalized == "regraded":
            return 0.0
        raise ValueError(f"Unsupported result: {result}")

    @staticmethod
    def validate_regrade(legs_left: Any, odds: Any) -> dict[str, int]:
        try:
            legs_value = int(legs_left)
        except (TypeError, ValueError) as exc:
            raise ValueError("Legs left must be an integer.") from exc

        try:
            odds_value = int(odds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Odds must be an integer.") from exc

        if legs_value < 1:
            raise ValueError("Legs left must be at least 1.")
        if odds_value == 0:
            raise ValueError("Odds cannot be zero.")

        return {"legs_left": legs_value, "odds": odds_value}

    @staticmethod
    def regrade_summary(play_text: str, legs_left: int, odds: int) -> str:
        note = play_text.strip() or "No notes"
        return f"Regraded: {legs_left}-leg • {odds} • {note[:180]}"
