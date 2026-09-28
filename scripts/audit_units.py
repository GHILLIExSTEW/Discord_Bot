"""Audit unit totals from the most recent plays. Read-only.

Usage: python scripts/audit_units.py [limit]
"""
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bot import TRACKER_TIMEZONE, parse_tracker_time
from src.services.settlement_service import SettlementService
from src.services.supabase_service import supabase_service

SETTLED_STATUSES = {"win", "loss", "void", "partial"}


def main(limit: int) -> None:
    db = supabase_service._ensure_client()
    plays = (
        db.table("plays")
        .select("id,user_id,units,status,created_at,settled_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    users = db.table("users").select("id,discord_user_id,display_name,username").execute().data or []
    names = {str(u["id"]): u.get("display_name") or u.get("username") or str(u["id"]) for u in users}

    now = datetime.now(TRACKER_TIMEZONE)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    by_status = defaultdict(lambda: {"count": 0, "units": 0.0})
    per_user = defaultdict(lambda: {"win": 0, "loss": 0, "void": 0, "partial": 0, "open": 0, "net": 0.0})
    all_time = month_to_date = year_to_date = 0.0

    for play in plays:
        status = play.get("status") or "open"
        units = float(play["units"])
        by_status[status]["count"] += 1
        by_status[status]["units"] += units

        bucket = per_user[names.get(str(play["user_id"]), str(play["user_id"]))]
        bucket[status] = bucket.get(status, 0) + 1

        if status not in SETTLED_STATUSES:
            continue

        tally = SettlementService.tally_for_result(status, units)
        bucket["net"] += tally
        all_time += tally

        settled_at = parse_tracker_time(play.get("settled_at") or play["created_at"], TRACKER_TIMEZONE.key)
        if month_start <= settled_at <= now:
            month_to_date += tally
        if year_start <= settled_at <= now:
            year_to_date += tally

    print(f"plays examined: {len(plays)} (most recent {limit})")
    if plays:
        print(f"date range: {plays[-1]['created_at']}  ->  {plays[0]['created_at']}")
    print()

    print("by status:")
    for status in sorted(by_status):
        data = by_status[status]
        print(f"  {status:<9} count={data['count']:<4} staked={data['units']:g}u")
    print()

    pending = sum(d["count"] for s, d in by_status.items() if s not in SETTLED_STATUSES)
    print(f"pending bets:      {pending}")
    print(f"net units (all):   {all_time:+g}u")
    print(f"net units (month): {month_to_date:+g}u")
    print(f"net units (year):  {year_to_date:+g}u")
    print()

    print("per playmaker (settled only):")
    ranked = sorted(per_user.items(), key=lambda item: item[1]["net"], reverse=True)
    for name, data in ranked:
        decided = data["win"] + data["loss"]
        rate = data["win"] / decided * 100 if decided else 0
        print(
            f"  {name:<28} {data['win']}-{data['loss']}  net={data['net']:+g}u  "
            f"win rate={rate:.0f}%  void={data['void']} partial={data['partial']} open={data['open']}"
        )


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
