import re
from datetime import datetime


def parse_iso_datetime(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    # Python 3.10 requires three or six fractional digits; Postgres trims zeros.
    text = re.sub(
        r"\.(\d{1,6})\d*(?=[+-]\d{2}:\d{2}$)",
        lambda match: "." + match.group(1).ljust(6, "0"),
        text,
    )
    return datetime.fromisoformat(text)
