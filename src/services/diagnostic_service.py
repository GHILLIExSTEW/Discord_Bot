from __future__ import annotations

from typing import Any

from src.services.image_play_service import ImagePlayService
from src.services.play_service import PlayService
from src.services.settlement_service import SettlementService


class DiagnosticService:
    def run_checks(self) -> list[dict[str, Any]]:
        checks = [
            self._check("Combined odds", self._combined_odds),
            self._check("Play validation", self._play_validation),
            self._check("Settlement math", self._settlement_math),
            self._check("Image payload validation", self._image_payload),
            self._check("Reaction mapping", self._reaction_mapping),
        ]
        return checks

    @staticmethod
    def _check(name: str, callback) -> dict[str, Any]:
        try:
            detail = callback()
            return {"name": name, "passed": True, "detail": detail}
        except Exception as exc:
            return {"name": name, "passed": False, "detail": str(exc)}

    @staticmethod
    def _combined_odds() -> str:
        odds = PlayService.combine_american_odds([-110, -110])
        if odds != 264:
            raise AssertionError(f"expected +264, got {odds:+d}")
        return "-110 + -110 = +264"

    @staticmethod
    def _play_validation() -> str:
        if PlayService().validate_play(2, 2, 264) is not None:
            raise AssertionError("valid play was rejected")
        if PlayService().validate_play(0, 2, 264) is None:
            raise AssertionError("zero units were accepted")
        return "valid input accepted; invalid units rejected"

    @staticmethod
    def _settlement_math() -> str:
        service = SettlementService()
        expected = {
            "win": 2.0,
            "loss": -2.0,
            "void": 0.0,
            "partial": 1.0,
        }
        for result, value in expected.items():
            if service.tally_for_result(result, 2.0) != value:
                raise AssertionError(f"{result} tally mismatch")
        return "win/loss/void/partial calculations passed"

    @staticmethod
    def _image_payload() -> str:
        data = {"units": "2", "legs": [{"selection": "Moneyline", "odds": "-110"}]}
        ImagePlayService._validate(data)
        if data["units"] != 2.0 or data["legs"][0]["odds"] != -110:
            raise AssertionError("numeric normalization mismatch")
        return "numeric strings normalized and payload accepted"

    @staticmethod
    def _reaction_mapping() -> str:
        reactions = {"✅": "win", "❌": "loss", "🚫": "void", "🌓": "partial"}
        if set(reactions.values()) != {"win", "loss", "void", "partial"}:
            raise AssertionError("reaction mapping incomplete")
        return "✅ win, ❌ loss, 🚫 void, 🌓 partial"


diagnostic_service = DiagnosticService()
