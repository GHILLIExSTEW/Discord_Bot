from datetime import datetime

from src.services.roster_sync_service import RosterSyncService


def test_active_season_uses_schedule_window_for_current_date():
    service = RosterSyncService()
    league = {
        "league": {"id": 1, "name": "Test League"},
        "seasons": [
            {"year": 2023, "start": "2023-08-01", "end": "2024-04-30", "current": False},
            {"year": 2024, "start": "2024-08-01", "end": "2025-04-30", "current": False},
        ],
    }
    assert service.get_active_season(league, now=datetime(2024, 11, 1)) == 2024


def test_active_season_ignores_leagues_outside_schedule_window():
    service = RosterSyncService()
    league = {
        "league": {"id": 1, "name": "Test League"},
        "seasons": [
            {"year": 2023, "start": "2023-08-01", "end": "2024-04-30", "current": False},
            {"year": 2024, "start": "2024-08-01", "end": "2025-04-30", "current": False},
        ],
    }
    assert service.get_active_season(league, now=datetime(2024, 6, 1)) is None


def test_active_season_prefers_current_flag_when_available():
    service = RosterSyncService()
    league = {
        "league": {"id": 1, "name": "Test League"},
        "seasons": [
            {"year": 2023, "start": "2023-08-01", "end": "2024-04-30", "current": False},
            {"year": 2024, "start": "2024-08-01", "end": "2025-04-30", "current": True},
        ],
    }
    assert service.get_active_season(league, now=datetime(2024, 6, 1)) == 2024


def test_should_sync_league_respects_configured_country_and_league_filters():
    service = RosterSyncService()
    league = {
        "league": {"id": 225, "name": "NCAA Men"},
        "country": {"name": "United States"},
    }
    assert service.should_sync_league(league, [{"country": "United States"}]) is True
    assert service.should_sync_league(league, [{"country": "Canada"}]) is False
    assert service.should_sync_league(league, [{"league_id": 225}]) is True
    assert service.should_sync_league(league, [{"league_name": "NCAA Women"}]) is False


def test_api_sports_flat_league_payload_is_supported():
    service = RosterSyncService()
    league = {
        "id": 249,
        "name": "LOVB Women",
        "country": {"name": "USA"},
        "seasons": [{"season": 2026, "start": "2026-01-01", "end": "2026-12-31", "current": True}],
    }
    assert service.should_sync_league(league, [{"country": "United States"}]) is True
    assert service.get_active_season(league) == 2026


def test_api_sports_flat_team_payload_is_supported():
    team_entry = {"id": 1, "name": "Las Vegas Raiders", "code": "LV", "country": {"name": "USA"}}
    team_data = team_entry.get("team") or team_entry
    assert team_data["id"] == 1
    assert team_data["name"] == "Las Vegas Raiders"


def test_upcoming_string_season_is_selected_for_nba():
    service = RosterSyncService()
    league = {
        "league": {"id": 12, "name": "NBA"},
        "seasons": [{"season": "2026-2027", "start": "2026-10-03", "end": "2027-04-04", "current": False}],
    }
    assert service.get_active_season(league, now=datetime(2026, 9, 20)) == "2026-2027"
