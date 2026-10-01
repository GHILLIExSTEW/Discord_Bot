create table if not exists public.api_sports_nfl_games (
  game_id bigint primary key,
  league_id bigint not null,
  season integer not null,
  stage text,
  week text,
  kickoff_at timestamptz not null,
  venue_name text,
  venue_city text,
  status_short text not null,
  status_long text not null,
  home_team_id bigint,
  home_team_name text not null,
  home_team_logo text,
  away_team_id bigint,
  away_team_name text not null,
  away_team_logo text,
  home_score integer,
  away_score integer,
  scores jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now()
);

create index if not exists idx_api_sports_nfl_games_season_kickoff
  on public.api_sports_nfl_games(season, kickoff_at);
create index if not exists idx_api_sports_nfl_games_status_kickoff
  on public.api_sports_nfl_games(status_short, kickoff_at);

create table if not exists public.api_sports_nfl_standings (
  league_id bigint not null,
  season integer not null,
  team_id bigint not null,
  team_name text not null,
  team_logo text,
  conference text,
  division text,
  position integer not null default 0,
  wins integer not null default 0,
  losses integer not null default 0,
  ties integer not null default 0,
  points_for integer not null default 0,
  points_against integer not null default 0,
  point_difference integer not null default 0,
  streak text,
  records jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  primary key (league_id, season, team_id)
);

create table if not exists public.api_sports_nfl_teams (
  team_id bigint primary key,
  name text not null,
  code text,
  city text,
  coach text,
  stadium jsonb not null default '{}'::jsonb,
  established integer,
  logo text,
  country jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now()
);

create table if not exists public.api_sports_sync_state (
  sync_key text primary key,
  last_attempt_at timestamptz not null,
  last_success_at timestamptz,
  request_count integer not null default 0,
  success boolean not null default false,
  error_message text
);

alter table public.api_sports_nfl_games enable row level security;
alter table public.api_sports_nfl_standings enable row level security;
alter table public.api_sports_nfl_teams enable row level security;
alter table public.api_sports_sync_state enable row level security;

create or replace function public.public_nfl_games()
returns table (
  game_id bigint,
  season integer,
  stage text,
  week text,
  kickoff_at timestamptz,
  venue_name text,
  venue_city text,
  status_short text,
  status_long text,
  home_team_id bigint,
  home_team_name text,
  home_team_logo text,
  home_score integer,
  away_team_id bigint,
  away_team_name text,
  away_team_logo text,
  away_score integer,
  scores jsonb,
  synced_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select games.game_id, games.season, games.stage, games.week, games.kickoff_at,
         games.venue_name, games.venue_city, games.status_short, games.status_long,
         games.home_team_id, games.home_team_name, games.home_team_logo, games.home_score,
         games.away_team_id, games.away_team_name, games.away_team_logo, games.away_score,
         games.scores, games.synced_at
  from public.api_sports_nfl_games as games
  where games.season = (select max(current_games.season) from public.api_sports_nfl_games as current_games)
  order by games.kickoff_at asc;
$$;

create or replace function public.public_nfl_standings()
returns table (
  season integer,
  team_id bigint,
  team_name text,
  team_logo text,
  conference text,
  division text,
  standing_position integer,
  wins integer,
  losses integer,
  ties integer,
  points_for integer,
  points_against integer,
  point_difference integer,
  streak text,
  synced_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select standings.season, standings.team_id, standings.team_name, standings.team_logo,
         standings.conference, standings.division, standings.position, standings.wins,
         standings.losses, standings.ties, standings.points_for, standings.points_against,
         standings.point_difference, standings.streak, standings.synced_at
  from public.api_sports_nfl_standings as standings
  where standings.season = (select max(current_standings.season) from public.api_sports_nfl_standings as current_standings)
  order by standings.conference, standings.division, standings.position;
$$;

create or replace function public.public_nfl_data_status()
returns table (
  sync_key text,
  last_success_at timestamptz,
  success boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select state.sync_key, state.last_success_at, state.success
  from public.api_sports_sync_state as state
  where state.sync_key in ('daily', 'live_scores');
$$;

revoke all on function public.public_nfl_games() from public;
revoke all on function public.public_nfl_standings() from public;
revoke all on function public.public_nfl_data_status() from public;
grant execute on function public.public_nfl_games() to anon, authenticated;
grant execute on function public.public_nfl_standings() to anon, authenticated;
grant execute on function public.public_nfl_data_status() to anon, authenticated;