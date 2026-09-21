# Multi-sport official play tracker

This project is a Discord bot + Supabase-backed app for:
- official play entry
- roster syncing via API-Sports
- team-only rankings
- daily team summary
- play settlement and regrade flow

## Project structure

- src/config.py: environment configuration
- src/services/supabase_service.py: Supabase access layer
- src/services/api_sports_service.py: API-Sports adapter
- src/services/roster_sync_service.py: 4-hour roster sync loop
- src/services/team_summary_service.py: daily team summary generator
- src/database/schema.sql: database schema
- src/bot.py: bot entry point

## Required environment variables

Create a .env file with values such as:

```env
DISCORD_TOKEN=your_token
GUILD_ID=your_guild_id
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_key
API_SPORTS_KEY=your_api_key
OFFICIAL_CHANNEL_ID=12345
TEAM_STATS_CHANNEL_ID=67890
TIMEZONE=America/New_York
```

## Local run

```bash
python -m venv .venv
. .venv\Scripts\activate
pip install -r requirements.txt
python -m src.bot
```

## Notes

- The roster job runs every 4 hours.
- The app is deliberately built to be multi-sport and generic.
- Team summaries are generated from settled play records and stored in `team_daily_summary`.
