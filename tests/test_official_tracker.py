from datetime import datetime
from zoneinfo import ZoneInfo

from src.bot import build_official_tracker_embed


def test_tracker_uses_only_official_plays_and_settlement_time():
    now = datetime(2026, 9, 21, 12, tzinfo=ZoneInfo("America/New_York"))
    plays = [
        {"id": 1, "user_id": 1, "units": 3, "status": "win", "created_at": "2026-09-20T18:00:00+00:00", "settled_at": "2026-09-21T14:00:00+00:00"},
        {"id": 2, "user_id": 1, "units": 2, "status": "loss", "created_at": "2026-09-20T18:00:00+00:00", "settled_at": "2026-09-21T15:00:00+00:00"},
        {"id": 3, "user_id": 2, "units": 5, "status": "open", "created_at": "2026-09-21T15:00:00+00:00", "settled_at": None},
        {"id": 4, "user_id": 2, "units": 1, "status": "void", "created_at": "2026-09-20T18:00:00+00:00", "settled_at": "2026-09-21T15:00:00+00:00"},
        {"id": 5, "user_id": 2, "units": 1, "status": "win", "created_at": "2026-09-19T18:00:00+00:00", "settled_at": "2026-09-20T19:00:00+00:00"},
    ]
    users = [{"id": 1, "display_name": "MoneyPicks", "username": "money"}, {"id": 2, "display_name": "Lady4", "username": "lady"}]

    embed, top_lines = build_official_tracker_embed(plays, users, now)

    assert [field.name for field in embed.fields] == ["⏳ Pending Bets", "📅 Monthly Units", "🗓️ Yearly Units", "🏆 Playmaker Breakdown"]
    assert embed.fields[0].value == "1 bet"
    assert embed.fields[1].value == "+2u"
    assert embed.fields[2].value == "+2u"
    assert "MoneyPicks" in embed.fields[3].value
    assert "1-1" in embed.fields[3].value
    assert "Lady4" in embed.fields[3].value
    assert "\n\n" in embed.fields[3].value
    assert "MoneyPicks" in top_lines[0]