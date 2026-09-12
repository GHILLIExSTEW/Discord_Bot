# Discord_Bot

Python Discord bot for tracking numeric values from specific users and summarizing them by day, week, month, and year.

## Features

- Track selected Discord user IDs
- Optional keyword gate before recording values
- Optional channel allowlist
- SQLite storage for each recorded value
- Slash commands for tally totals by time window

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   . .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your Discord token and guild ID.
4. Update `config.json` with your tracked users and settings.
5. Run the bot:
   ```bash
   python bot.py
   ```

## Commands

- `/tally period:day|week|month|year [member]`
- `/tally_recent [member] [limit]`

## Files

- `bot.py` — Discord bot entry point
- `tally_logic.py` — regex, SQLite, and time-window helpers
- `config.json` — runtime configuration
- `tally.db` — SQLite database created automatically
