# Discord Value Tally

Record numeric values from specific members’ posts and sum them by **day**, **week**, **month**, and **year**.

This is meant to be added to a bot you already run. A standalone Python example also exists under `discord-value-tally-bot/` if you want a separate process.

---

## Goal

| Piece | Behavior |
|---|---|
| Who | Only members whose Discord user IDs you list |
| What | Numbers found in their messages (optional keyword gate) |
| Where | All channels, or only channels you list |
| When | Each saved row has a timestamp in `America/New_York` (changeable) |
| Report | Totals for today, this week (Monday–now), this month, this year |

Example posts that become stored values (default regex):

- `12.5`
- `sold 12.5 today`
- `hours: 8`
- `qty 3 and 4` → two rows: `3` and `4`

---

## How it works

```
member posts in Discord
        ↓
on_message fires
        ↓
author in tracked list?  channel allowed?  keyword present (if set)?
        ↓
regex pulls numbers from the message text
        ↓
each number is inserted into SQLite (tally.db)
        ↓
/tally day|week|month|year sums rows in that window
```

Nothing is counted while the bot is offline. History before the bot started is not backfilled unless you add a scan command later.

---

## Config

Put this near the top of your bot file, or in `config.json`.

```json
{
  "tracked_user_ids": [111111111111111111, 222222222222222222],
  "allowed_channel_ids": [],
  "number_pattern": "[-+]?\\d+(?:\\.\\d+)?",
  "require_keyword": "",
  "keyword_case_insensitive": true,
  "ignore_bots": true,
  "timezone": "America/New_York"
}
```

| Field | Meaning |
|---|---|
| `tracked_user_ids` | Only these user IDs are recorded. Get an ID: Discord Settings → Advanced → Developer Mode on, then right-click the member → Copy User ID. |
| `allowed_channel_ids` | Empty = every channel. Otherwise only those channel IDs. |
| `number_pattern` | Regex for what counts as a “value”. Default is integers and decimals, optional sign. |
| `require_keyword` | If set (example `"hours"` or `"sold"`), the message must contain that word or nothing is stored. Stops random chat numbers from being logged. |
| `keyword_case_insensitive` | Treat the keyword as case-insensitive. |
| `ignore_bots` | Skip other bots (keep `true`). |
| `timezone` | Used for midnight / Monday / 1st-of-month / Jan 1 cutoffs. Ohio = `America/New_York`. |

Python equivalent if you do not want a JSON file:

```python
TRACKED_USER_IDS = {111111111111111111}
ALLOWED_CHANNEL_IDS = set()          # empty = all channels
REQUIRE_KEYWORD = ""                 # e.g. "hours"
NUMBER_PATTERN = r"[-+]?\d+(?:\.\d+)?"
TZ_NAME = "America/New_York"
IGNORE_BOTS = True
```

---

## Database

SQLite file next to the bot: `tally.db`.

Create once on startup:

```sql
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    value REAL NOT NULL,
    raw_text TEXT,
    channel_id INTEGER,
    message_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entries_user_time
    ON entries(user_id, created_at);
```

| Column | Purpose |
|---|---|
| `user_id` | Discord snowflake |
| `username` | Snapshot of `user#discrim` or display name at record time |
| `value` | The number extracted |
| `raw_text` | First ~500 characters of the message (for audit) |
| `channel_id` | Where it was posted |
| `message_id` | Source message (can be NULL for manual `/tally_add`) |
| `created_at` | ISO timestamp in the configured timezone |

Inspect later:

```bash
sqlite3 tally.db "SELECT username, value, created_at FROM entries ORDER BY id DESC LIMIT 20;"
```

Back up `tally.db`. That file is the entire history.

---

## Time windows

All windows use the configured timezone. “Now” is the moment the command runs.

| Period | Start | End |
|---|---|---|
| `day` | Today 00:00:00 | now |
| `week` | Monday 00:00:00 of the current week | now |
| `month` | 1st of this month 00:00:00 | now |
| `year` | January 1 00:00:00 | now |

Week starts Monday (ISO). Change `weekday()` math if you want Sunday start.

SQL shape:

```sql
SELECT user_id, username,
       COUNT(*) AS n,
       SUM(value) AS total,
       AVG(value) AS avg_val
FROM entries
WHERE created_at >= :start AND created_at <= :end
  AND (:user_id IS NULL OR user_id = :user_id)
GROUP BY user_id
ORDER BY total DESC;
```

`created_at` must be stored as ISO-8601 (`2026-09-11T21:08:00-04:00` or naive `2026-09-11T21:08:00` consistently). String compare works if every row uses the same format and timezone.

---

## Add to an existing discord.py bot

Intents required:

```python
intents = discord.Intents.default()
intents.message_content = True   # Privileged. Enable in the Developer Portal.
```

Also enable **MESSAGE CONTENT INTENT** on the bot page or the bot cannot read message text.

### Extract + insert (inside your existing `on_message`)

Keep your current handlers. Add this after bot/self checks:

```python
import re
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
DB_PATH = "tally.db"

def extract_values(content: str) -> list[float]:
    keyword = REQUIRE_KEYWORD.strip()
    if keyword and keyword.lower() not in content.lower():
        return []
    return [float(m) for m in NUMBER_RE.findall(content)]

@bot.event
async def on_message(message: discord.Message):
    # --- your existing on_message code can stay ---

    if message.author.bot and IGNORE_BOTS:
        await bot.process_commands(message)
        return
    if not message.guild:
        await bot.process_commands(message)
        return
    if TRACKED_USER_IDS and message.author.id not in TRACKED_USER_IDS:
        await bot.process_commands(message)
        return
    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        await bot.process_commands(message)
        return

    values = extract_values(message.content)
    if values:
        now = datetime.now(TZ).isoformat()
        conn = sqlite3.connect(DB_PATH)
        for value in values:
            conn.execute(
                """INSERT INTO entries
                   (user_id, username, value, raw_text, channel_id, message_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    message.author.id,
                    str(message.author),
                    value,
                    message.content[:500],
                    message.channel.id,
                    message.id,
                    now,
                ),
            )
        conn.commit()
        conn.close()

    await bot.process_commands(message)
```

If you already call `process_commands` once at the bottom, do **not** add a second call.

### Period helper

```python
def period_bounds(period: str, now: datetime | None = None):
    now = now or datetime.now(TZ)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        start = start_of_day
    elif period == "week":
        start = start_of_day - timedelta(days=start_of_day.weekday())
    elif period == "month":
        start = start_of_day.replace(day=1)
    elif period == "year":
        start = start_of_day.replace(month=1, day=1)
    else:
        raise ValueError(period)
    return start, now
```

### Slash commands to register on your existing tree

```python
@bot.tree.command(name="tally", description="Sum recorded values for a time period")
@app_commands.describe(period="day, week, month, or year", member="Optional: one member")
@app_commands.choices(period=[
    app_commands.Choice(name="Today", value="day"),
    app_commands.Choice(name="This week (Mon–now)", value="week"),
    app_commands.Choice(name="This month", value="month"),
    app_commands.Choice(name="This year", value="year"),
])
async def tally(interaction: discord.Interaction,
                period: app_commands.Choice[str],
                member: discord.Member | None = None):
    start, end = period_bounds(period.value)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if member:
        rows = conn.execute(
            """SELECT username, COUNT(*) AS n, SUM(value) AS total, AVG(value) AS avg_val
               FROM entries
               WHERE user_id = ? AND created_at >= ? AND created_at <= ?
               GROUP BY user_id""",
            (member.id, start.isoformat(), end.isoformat()),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT username, COUNT(*) AS n, SUM(value) AS total, AVG(value) AS avg_val
               FROM entries
               WHERE created_at >= ? AND created_at <= ?
               GROUP BY user_id
               ORDER BY total DESC""",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message("No recorded values in this period.")
        return

    lines = [
        f"**{r['username']}** — sum `{r['total']:g}` · {r['n']} entries · avg `{r['avg_val']:.2f}`"
        for r in rows
    ]
    await interaction.response.send_message("\n".join(lines))
```

Useful extras (optional):

| Command | Who | What |
|---|---|---|
| `/tally_recent [member] [limit]` | anyone | Last N stored rows |
| `/tally_add member value [note]` | Manage Server | Manual row (missed post, correction) |
| `/tally_reload` | Manage Server | Re-read `config.json` without restarting |

After adding slash commands, sync the tree the same way your bot already does (`tree.sync()` or guild sync). Guild sync with your server ID is instant.

---

## Add to an existing discord.js bot (outline)

Same rules. In `messageCreate`:

1. Ignore bots.
2. Check `TRACKED_USER_IDS` and optional channel list.
3. Optional keyword check.
4. `content.match(/[-+]?\d+(?:\.\d+)?/g)` → parse floats.
5. `INSERT` into SQLite (`better-sqlite3`) with `new Date().toISOString()` or a zoned timestamp.

Slash command `/tally` with a string choice for period, same date-boundary math using a library that understands timezones (`luxon` is enough).

---

## Parsing rules (tune these)

**Default:** every number in the message is a row.

That is wrong if people type dates, prices, and the value you care about in the same line.

Ways to tighten:

1. **Keyword gate** — `"require_keyword": "hours"` so only messages containing `hours` are scanned.
2. **Stricter regex** — only a number after a label:
   - hours: `hours[:\s]+([-+]?\d+(?:\.\d+)?)`
   - money: `\$(\d+(?:\.\d{1,2})?)`
   - qty: `qty[:\s]+(\d+)`
3. **First number only** — use `values[:1]` instead of the full list.
4. **Dedicated channel** — put the channel ID in `allowed_channel_ids` and keep chat elsewhere.

Write one real example of a post you want counted and one you do not. Adjust keyword + regex until only the first matches.

---

## Developer Portal checklist

1. Application → Bot → token (already have this).
2. Privileged Gateway Intents → **Message Content Intent** = on.
3. OAuth invite already includes `bot`. If slash commands are new, also need scope `applications.commands`.
4. Bot role can Read Messages / View Channels and Send Messages in the channels you care about.

---

## Standalone folder (optional)

If you would rather run this as its own process instead of editing the live bot:

```
discord-value-tally-bot/
  bot.py
  config.json
  .env.example
  requirements.txt
  README.md
  tally.db          (created on first run)
```

```bash
cd discord-value-tally-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and config.json
python bot.py
```

`.env`:

```
DISCORD_TOKEN=existing_or_new_token
GUILD_ID=your_server_id
```

Two bots cannot share one token. If the existing bot must stay as-is, create a second application for the tally bot.

---

## Hosting

The process has to stay up. Offline = missed posts.

- Same machine / same process as the current bot is simplest.
- systemd example if this is a separate service:

```
[Unit]
Description=Discord Value Tally
After=network.target

[Service]
WorkingDirectory=/path/to/bot
ExecStart=/path/to/bot/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Common problems

| Symptom | Likely cause |
|---|---|
| Commands do not appear | Tree not synced, or missing `applications.commands` scope. Set `GUILD_ID` and sync to that guild. |
| Bot never records | Message Content Intent off, user ID not in the list, wrong channel filter, keyword not in the message. |
| Too many junk numbers | No keyword / regex too loose. Add `require_keyword` or a labeled pattern. |
| Totals look “a day off” | Timezone not `America/New_York`, or `created_at` stored in UTC without conversion. |
| Duplicate rows on edit | `on_message` fires for new messages only. Message edits are ignored unless you also hook `on_message_edit`. |
| Multiple numbers from one post | Expected with the default regex. Use first-match only or a labeled pattern. |

---

## What to send if you want this wired into *your* file

1. Language (`discord.py` / `discord.js` / other)
2. Whether you already have `on_message` / `messageCreate` and slash commands
3. One example post that should count, one that should not
4. Whether only certain channels matter
5. The relevant snippet of your current bot file
