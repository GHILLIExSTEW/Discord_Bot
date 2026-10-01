create or replace function public.public_sport_events(p_sport_slug text)
returns table (
  sport_slug text,
  event_id text,
  league_name text,
  season text,
  round_name text,
  event_name text,
  start_at timestamptz,
  venue jsonb,
  home_name text,
  home_logo text,
  away_name text,
  away_logo text,
  home_score jsonb,
  away_score jsonb,
  status_code text,
  status text,
  synced_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select events.sport_slug, events.event_id, events.league_name, events.season,
         events.round_name, events.event_name, events.start_at, events.venue,
         events.home_name, events.home_logo, events.away_name, events.away_logo,
         events.home_score, events.away_score, events.status_code, events.status,
         events.synced_at
  from public.api_sports_events as events
  where events.sport_slug = p_sport_slug
    and events.sport_slug in ('football', 'basketball', 'baseball', 'hockey', 'rugby', 'handball', 'volleyball', 'formula-1', 'mma', 'ncaa')
  order by events.start_at;
$$;

revoke all on function public.public_sport_events(text) from public;
grant execute on function public.public_sport_events(text) to anon, authenticated;
