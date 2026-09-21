from datetime import datetime, timezone

from src.services.team_summary_service import TeamSummaryService


def test_report_aggregates_net_and_gross_units(monkeypatch):
    service = TeamSummaryService()
    plays = [
        {"id": 1, "user_id": 1, "units": 2, "status": "win", "created_at": "2026-09-20T12:00:00+00:00", "settled_at": "2026-09-20T13:00:00+00:00"},
        {"id": 2, "user_id": 1, "units": 1, "status": "loss", "created_at": "2026-09-20T12:00:00+00:00", "settled_at": "2026-09-20T14:00:00+00:00"},
        {"id": 3, "user_id": 2, "units": 3, "status": "open", "created_at": "2026-09-20T15:00:00+00:00", "settled_at": None},
    ]
    responses = iter([type("Response", (), {"data": plays})(), type("Response", (), {"data": [{"id": 1, "display_name": "Alpha"}, {"id": 2, "display_name": "Beta"}]})()])
    monkeypatch.setattr("src.services.team_summary_service.supabase_service.select", lambda *args, **kwargs: next(responses))

    report = service.build_playmaker_report(datetime(2026, 9, 20, 16, 0, tzinfo=timezone.utc))
    assert report["periods"]["daily"]["net"] == 1
    assert report["periods"]["daily"]["win_units"] == 2
    assert report["periods"]["daily"]["loss_units"] == 1
    assert report["pending"] == 1