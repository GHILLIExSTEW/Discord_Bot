import asyncio
from types import SimpleNamespace

import src.bot as bot_module


class FakeReaction:
    def __init__(self, emoji, users):
        self.emoji = emoji
        self._users = users

    def users(self):
        async def iterate():
            for user in self._users:
                yield user

        return iterate()


class FakeChannel:
    def __init__(self, message):
        self.message = message

    async def fetch_message(self, message_id):
        assert message_id == 500
        return self.message


def test_reconcile_open_play_reactions_settles_owner_reaction(monkeypatch):
    message = SimpleNamespace(
        reactions=[FakeReaction("✅", [SimpleNamespace(id=999), SimpleNamespace(id=123)])]
    )
    plays = [{"id": 42, "user_id": 7, "status": "open", "message_id": "500"}]
    users = [{"id": 7, "discord_user_id": "123"}]
    settlements = []
    monkeypatch.setattr(
        bot_module.official_play_service,
        "settle_play",
        lambda play_id, result: settlements.append((play_id, result)),
    )

    settled_count = asyncio.run(
        bot_module.reconcile_open_play_reactions(plays, users, [FakeChannel(message)])
    )

    assert settled_count == 1
    assert settlements == [(42, "win")]