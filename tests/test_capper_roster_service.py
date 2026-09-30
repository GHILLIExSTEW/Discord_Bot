from types import SimpleNamespace

from src.services.capper_roster_service import CapperRosterService


class MemoryRepository:
    def __init__(self):
        self.rows = {}

    def select(self, table, columns, filters):
        matches = [
            row.copy()
            for row in self.rows.values()
            if all(row.get(key) == value for key, value in filters.items())
        ]
        return SimpleNamespace(data=matches)

    def upsert(self, table, payload, conflict_columns):
        rows = payload if isinstance(payload, list) else [payload]
        for row in rows:
            current = self.rows.get(row["discord_user_id"], {})
            self.rows[row["discord_user_id"]] = {**current, **row}

    def update(self, table, payload, match):
        self.rows[match["discord_user_id"]].update(payload)


def test_sync_member_adds_authorized_member_and_updates_display_name(monkeypatch):
    monkeypatch.setattr("src.services.capper_roster_service.OPERATOR_ROLE_IDS", {42})
    repository = MemoryRepository()
    service = CapperRosterService(repository)

    assert service.sync_member("100", "First Name", {42}) is True
    assert service.sync_member("100", "Updated Name", {42}) is True
    assert repository.rows["100"] == {
        "discord_user_id": "100",
        "display_name": "Updated Name",
        "is_authorized": True,
    }


def test_sync_member_accepts_any_configured_operator_role(monkeypatch):
    monkeypatch.setattr("src.services.capper_roster_service.OPERATOR_ROLE_IDS", {42, 84})
    repository = MemoryRepository()
    service = CapperRosterService(repository)

    assert service.sync_member("100", "Capper Name", {84}) is True
    assert repository.rows["100"]["is_authorized"] is True


def test_sync_member_deactivates_role_removed_member_without_deleting_history(monkeypatch):
    monkeypatch.setattr("src.services.capper_roster_service.OPERATOR_ROLE_IDS", {42})
    repository = MemoryRepository()
    repository.rows["100"] = {
        "discord_user_id": "100",
        "display_name": "Former Name",
        "is_authorized": True,
    }
    service = CapperRosterService(repository)

    assert service.sync_member("100", "Latest Name", set()) is False
    assert repository.rows["100"] == {
        "discord_user_id": "100",
        "display_name": "Latest Name",
        "is_authorized": False,
    }


def test_sync_guild_members_deactivates_members_missing_from_guild(monkeypatch):
    monkeypatch.setattr("src.services.capper_roster_service.OPERATOR_ROLE_IDS", {42})
    repository = MemoryRepository()
    repository.rows["100"] = {
        "discord_user_id": "100",
        "display_name": "Former Name",
        "is_authorized": True,
    }
    service = CapperRosterService(repository)

    count = service.sync_guild_members([{
        "discord_user_id": "200",
        "display_name": "Current Capper",
        "role_ids": {42},
    }])

    assert count == 1
    assert repository.rows["100"]["is_authorized"] is False
    assert repository.rows["200"]["is_authorized"] is True