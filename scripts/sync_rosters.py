from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import ROSTER_SYNC_SPORT_FILTERS, ROSTER_SYNC_SPORTS
from src.services.roster_sync_service import RosterSyncService


def main() -> None:
    service = RosterSyncService()
    total = 0
    for sport_slug in ROSTER_SYNC_SPORTS:
        sport_name = sport_slug.replace("-", " ").title()
        count = service.sync_sport(
            sport_name,
            sport_slug,
            ROSTER_SYNC_SPORT_FILTERS.get(sport_slug, []),
        )
        print(f"{sport_name}: teams and players processed: {count}")
        total += count
    print(f"Roster sync complete. Total records processed: {total}")


if __name__ == "__main__":
    main()