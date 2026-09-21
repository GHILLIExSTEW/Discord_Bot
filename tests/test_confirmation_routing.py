import asyncio
from types import SimpleNamespace

import src.bot as bot_module


class CapturingChannel:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


def test_confirmation_uses_dedicated_channel(monkeypatch):
    confirmation_channel = CapturingChannel()
    requested_channel_ids = []

    async def fetch_channel(channel_id):
        requested_channel_ids.append(channel_id)
        return confirmation_channel

    monkeypatch.setattr(bot_module, "CONFIRMATION_CHANNEL_ID", 101)
    monkeypatch.setattr(bot_module, "TRACKING_CHANNEL_ID", 202)
    monkeypatch.setattr(bot_module.bot, "get_channel", lambda channel_id: None)
    monkeypatch.setattr(bot_module.bot, "fetch_channel", fetch_channel)
    monkeypatch.setattr(bot_module.official_play_service, "get_play_legs", lambda play_id: [])

    interaction = SimpleNamespace(user=SimpleNamespace(id=1, display_name="Test User"))
    payload = {"play_id": 1, "summary": "Test play", "units": 1, "legs": 1, "odds": -110, "to_win": 0.91}

    asyncio.run(bot_module.send_confirmation_message(interaction, payload))

    assert requested_channel_ids == [101]
    assert len(confirmation_channel.sent) == 1