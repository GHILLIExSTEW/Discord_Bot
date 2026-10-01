from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.services.api_sports_multi_service import ApiSportsMultiService, DATE_PRODUCTS, DATE_PRODUCT_PARAMS, normalize_event


@pytest.fixture
def synced_at():
    return datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def test_normalize_football_fixture(synced_at):
    result = normalize_event("football", {
        "fixture": {"id": 100, "date": "2026-10-01T00:00:00+00:00", "venue": {"name": "Park"}, "status": {"short": "FT", "long": "Match Finished"}},
        "league": {"id": 1, "name": "League", "season": 2026, "round": "Week 1"},
        "teams": {"home": {"id": 10, "name": "Home", "logo": "home.png"}, "away": {"id": 20, "name": "Away", "logo": "away.png"}},
        "goals": {"home": 2, "away": 1},
    }, synced_at)

    assert result["event_id"] == "100"
    assert result["event_name"] == "Home vs Away"
    assert result["home_score"] == 2
    assert result["status_code"] == "FT"


def test_normalize_basketball_total_scores(synced_at):
    result = normalize_event("basketball", {
        "id": 200,
        "date": "2026-10-01T00:00:00+00:00",
        "league": {"id": 18, "name": "Liga A", "season": "2026-2027"},
        "teams": {"home": {"id": 30, "name": "Argentino"}, "away": {"id": 31, "name": "Ferro"}},
        "scores": {"home": {"total": 79}, "away": {"total": 68}},
        "status": {"short": "FT", "long": "Game Finished"},
    }, synced_at)

    assert result["home_score"] == {"total": 79}
    assert result["away_score"] == {"total": 68}
    assert result["season"] == "2026-2027"


def test_normalize_formula_one_race_without_teams(synced_at):
    result = normalize_event("formula-1", {
        "id": 300,
        "date": "2026-03-06T01:30:00+00:00",
        "competition": {"id": 1, "name": "Australia Grand Prix", "location": {"country": "Australia", "city": "Melbourne"}},
        "circuit": {"name": "Albert Park Circuit"},
        "season": 2026,
        "type": "Practice",
        "status": "Completed",
    }, synced_at)

    assert result["event_name"] == "Australia Grand Prix"
    assert result["venue"]["name"] == "Albert Park Circuit"
    assert result["status_code"] == "COMPLETED"


class FakeQuery:
    def __init__(self, data=None):
        self.data = data or []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeSupabase:
    def table(self, _table):
        return FakeQuery()


class FakeApiResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"errors": {}, "response": []}


def test_daily_sync_uses_seven_date_requests_per_sport_and_one_formula_one_request(synced_at):
    calls = []

    def fake_get(url, params, **_kwargs):
        calls.append((url, params))
        return FakeApiResponse()

    service = ApiSportsMultiService(api_key="test-key", client=FakeSupabase(), get=fake_get, clock=lambda: synced_at)
    result = service.sync_daily(force=True)

    assert result["total_requests"] == len(DATE_PRODUCTS) * 7 + 1
    assert len(calls) == result["total_requests"]
    assert result["sports"]["formula-1"]["requests"] == 1


def test_live_sync_with_no_active_sports_uses_no_api_requests(synced_at):
    calls = []
    service = ApiSportsMultiService(
        api_key="test-key",
        client=FakeSupabase(),
        get=lambda *args, **kwargs: calls.append((args, kwargs)) or FakeApiResponse(),
        clock=lambda: synced_at,
    )

    result = service.sync_live_scores()

    assert result == {"total_requests": 0, "sports": {}}
    assert calls == []


def test_ncaa_feed_uses_american_football_ncaa_league_filter():
    assert DATE_PRODUCTS["ncaa"] == ("https://v1.american-football.api-sports.io", "games")
    assert DATE_PRODUCT_PARAMS["ncaa"] == {"league": 2}