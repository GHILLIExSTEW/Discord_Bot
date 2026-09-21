from unittest.mock import Mock, patch

from src.services.roster_sync_service import RosterSyncService


def test_sync_team_roster_upserts_players_and_creates_snapshots():
    service = RosterSyncService()
    service.current_sport_slug = "american-football"
    player_select = Mock(data=[{"id": 42, "api_player_id": "7"}])
    snapshot_insert = Mock(data=[])

    with patch("src.services.roster_sync_service.api_sports_service.get_for_sport", return_value={
        "response": [{"players": [{
                "id": 7,
                "name": "Alex Player",
                "firstname": "Alex",
                "lastname": "Player",
                "position": "Setter",
            }]}]
    }) as api_get, patch("src.services.roster_sync_service.supabase_service.select", return_value=player_select), patch(
        "src.services.roster_sync_service.supabase_service.upsert"
    ) as upsert, patch(
        "src.services.roster_sync_service.supabase_service.insert", return_value=snapshot_insert
    ) as insert:
        count = service.sync_team_roster(1, 2, 3, "99", 2026)

    assert count == 1
    api_get.assert_called_once_with("american-football", "players/squads", {"team": "99"})
    upsert.assert_called_once()
    assert upsert.call_args.args[0] == "players"
    assert upsert.call_args.args[1][0]["api_player_id"] == "7"
    assert insert.call_count == 1
    assert insert.call_args.args[0] == "roster_snapshots"
    assert insert.call_args.args[1][0]["player_id"] == 42