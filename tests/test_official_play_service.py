from datetime import datetime

from src.services.official_play_service import OfficialPlayService
import src.services.official_play_service as official_play_module


def test_settle_play_updates_valid_play_columns(monkeypatch):
    service = OfficialPlayService()
    updates = []

    monkeypatch.setattr(service, "_fetch_play", lambda play_id: {"units": 2})
    monkeypatch.setattr(
        official_play_module.supabase_service,
        "update",
        lambda table, payload, match: updates.append((table, payload, match)),
    )

    outcome = service.settle_play(42, "win")

    assert outcome == {"result": "win", "tally": 2.0}
    assert updates[0][0] == "plays"
    assert updates[0][2] == {"id": 42}
    assert set(updates[0][1]) == {"status", "settled_at"}
    assert datetime.fromisoformat(updates[0][1]["settled_at"]).tzinfo is not None