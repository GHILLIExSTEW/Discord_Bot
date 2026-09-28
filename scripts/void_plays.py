"""Void specific plays by id. Usage: python scripts/void_plays.py 11 16 75"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.official_play_service import OfficialPlayService
from src.services.supabase_service import supabase_service


def main(play_ids: list[int]) -> None:
    db = supabase_service._ensure_client()
    service = OfficialPlayService()

    rows = db.table("plays").select("id,status,units,message_id").in_("id", play_ids).execute().data or []
    found = {int(row["id"]): row for row in rows}
    missing = [play_id for play_id in play_ids if play_id not in found]
    if missing:
        print("not found:", missing)

    for play_id in play_ids:
        row = found.get(play_id)
        if row is None:
            continue
        if row["status"] != "open":
            print(f"play #{play_id} already {row['status']}, skipping")
            continue
        service.settle_play(play_id, "void")
        print(f"play #{play_id} voided (was open, {row['units']}u)")


if __name__ == "__main__":
    ids = [int(arg) for arg in sys.argv[1:]]
    if not ids:
        raise SystemExit("Pass one or more play ids, e.g. python scripts/void_plays.py 11 16 75")
    main(ids)
