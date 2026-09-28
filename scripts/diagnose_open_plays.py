"""Report why open plays are not being reconciled. Read-only."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import discord

from src.config import (
    CONFIRMATION_CHANNEL_ID,
    DISCORD_TOKEN,
    IMAGE_INPUT_CHANNEL_ID,
    OFFICIAL_CHANNEL_ID,
)
from src.services.supabase_service import supabase_service

CHANNEL_SETTINGS = (
    ("CONFIRMATION_CHANNEL_ID", CONFIRMATION_CHANNEL_ID),
    ("OFFICIAL_CHANNEL_ID", OFFICIAL_CHANNEL_ID),
    ("IMAGE_INPUT_CHANNEL_ID", IMAGE_INPUT_CHANNEL_ID),
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        db = supabase_service._ensure_client()
        plays = db.table("plays").select("id,user_id,status,message_id").eq("status", "open").execute().data or []
        users = db.table("users").select("id,discord_user_id,display_name,username").execute().data or []
        owners = {str(u["id"]): str(u.get("discord_user_id")) for u in users}
        names = {str(u["id"]): u.get("display_name") or u.get("username") for u in users}

        channels = []
        for name, channel_id in dict.fromkeys(CHANNEL_SETTINGS):
            if not channel_id:
                continue
            try:
                channels.append((name, client.get_channel(channel_id) or await client.fetch_channel(channel_id)))
            except (discord.NotFound, discord.Forbidden) as exc:
                print(f"channel {name}={channel_id} unavailable: {exc}")
        print("searching channels:", [name for name, _ in channels])
        print()

        for play in plays:
            play_id = play["id"]
            owner_id = owners.get(str(play["user_id"]))
            owner_name = names.get(str(play["user_id"]), "?")
            print(f"play #{play_id} owner={owner_name} discord_id={owner_id} msg={play.get('message_id')}")

            if not owner_id or owner_id == "None":
                print("   SKIPPED: user row has no discord_user_id")
                continue
            if not play.get("message_id"):
                print("   SKIPPED: no message_id stored")
                continue

            found = None
            for name, channel in channels:
                try:
                    found = (name, await channel.fetch_message(int(play["message_id"])))
                    break
                except (discord.NotFound, discord.Forbidden):
                    continue
            if found is None:
                print("   SKIPPED: message not found in any searched channel")
                continue

            channel_name, message = found
            print(f"   found in {channel_name} (#{message.channel.name})")
            if not message.reactions:
                print("   no reactions on message")
            for reaction in message.reactions:
                reactors = [f"{u.id}{' <-- OWNER' if str(u.id) == owner_id else ''}" async for u in reaction.users()]
                print(f"   {reaction.emoji} x{reaction.count}: {', '.join(reactors) or 'none'}")
            print()
    finally:
        await client.close()


client.run(DISCORD_TOKEN)
