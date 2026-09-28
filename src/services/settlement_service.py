from __future__ import annotations

from typing import Any


class SettlementService:
    @staticmethod
    def profit_multiplier(odds: Any) -> float:
        """Profit per unit staked for American odds. Falls back to even money."""
        try:
            odds_value = int(odds)
        except (TypeError, ValueError):
            return 1.0
        if odds_value > 0:
            return odds_value / 100.0
        if odds_value < 0:
            return 100.0 / abs(odds_value)
        return 1.0

    @staticmethod
    def tally_for_result(result: str, units: float, odds: Any = None) -> float:
        normalized = (result or "").strip().lower()
        profit = float(units) * SettlementService.profit_multiplier(odds)
        if normalized == "win":
            return round(profit, 2)
        if normalized == "loss":
            return float(-units)
        if normalized == "partial":
            return round(profit * 0.5, 2)
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
