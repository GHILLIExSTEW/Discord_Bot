begin;
create table public.api_sports_player_directory (
  sport_slug text not null,
  league_id text not null,
  player_id bigint not null check (player_id > 0),
  name text not null,
  team_name text,
  synced_at timestamptz not null,
  primary key (sport_slug, league_id, player_id)
);
create index player_directory_name on public.api_sports_player_directory
  (sport_slug, league_id, lower(name) text_pattern_ops);
create table public.api_sports_player_seasons (
  sport_slug text not null,
  league_id text not null,
  player_id bigint not null check (player_id > 0),
  season text not null,
  groups jsonb not null check (jsonb_typeof(groups) = 'array'),
  coverage text not null,
  synced_at timestamptz not null,
  primary key (sport_slug, league_id, player_id, season)
);
create table public.api_sports_player_leagues (
  sport_slug text not null,
  league_id text not null,
  name text not null,
  current_season text not null,
  primary key (sport_slug, league_id)
);
create table public.api_sports_player_season_metadata (
  sport_slug text not null,
  league_id text not null,
  season text not null,
  payload jsonb not null check (jsonb_typeof(payload) = 'array'),
  synced_at timestamptz not null,
  primary key (sport_slug, league_id, season)
);
alter table public.api_sports_player_directory enable row level security;
alter table public.api_sports_player_seasons enable row level security;
alter table public.api_sports_player_leagues enable row level security;
alter table public.api_sports_player_season_metadata enable row level security;
revoke all on public.api_sports_player_directory, public.api_sports_player_seasons,
  public.api_sports_player_leagues, public.api_sports_player_season_metadata from public, anon, authenticated;
grant select, insert, update on public.api_sports_player_directory, public.api_sports_player_seasons,
  public.api_sports_player_leagues, public.api_sports_player_season_metadata to service_role;

insert into public.api_sports_player_leagues
select distinct on (sport_slug, league_id) sport_slug, league_id, league_name, season
from public.api_sports_events
where sport_slug in ('ncaa', 'basketball', 'football') and season is not null
  and league_id is not null and league_name is not null and start_at <= now()
order by sport_slug, league_id, start_at desc;
insert into public.api_sports_player_leagues
select 'nfl', '1', 'NFL', max(season)::text from public.api_sports_nfl_games where kickoff_at <= now()
having max(season) is not null;
insert into public.api_sports_player_leagues
select 'formula-1', 'f1', 'Formula 1', max(season) from public.api_sports_events
where sport_slug = 'formula-1' and start_at <= now() having max(season) is not null;

-- Seed autocomplete from already verified game snapshots; no provider requests.
insert into public.api_sports_player_directory
select distinct on (s.sport_slug, coalesce(e.league_id, '1'), p.value->'player'->>'id')
  s.sport_slug, coalesce(e.league_id, '1'), (p.value->'player'->>'id')::bigint,
  p.value->'player'->>'name', t.value->'team'->>'name', s.synced_at
from public.api_sports_player_game_stats s
left join public.api_sports_events e on e.sport_slug = s.sport_slug and e.event_id = s.game_id::text
cross join lateral jsonb_array_elements(s.payload) t
cross join lateral jsonb_array_elements(t.value->'groups') g
cross join lateral jsonb_array_elements(g.value->'players') p
where s.sport_slug in ('nfl', 'ncaa') and (s.sport_slug = 'nfl' or e.league_id is not null)
  and (p.value->'player'->>'id') ~ '^[1-9][0-9]*$'
order by s.sport_slug, coalesce(e.league_id, '1'), p.value->'player'->>'id', s.synced_at desc;
insert into public.api_sports_player_directory
select distinct on (e.league_id, p.value->'player'->>'id')
  'football', e.league_id, (p.value->'player'->>'id')::bigint,
  p.value->'player'->>'name', t.value->'team'->>'name', s.synced_at
from public.api_sports_player_game_stats s
join public.api_sports_events e on e.sport_slug = s.sport_slug and e.event_id = s.game_id::text
cross join lateral jsonb_array_elements(s.payload) t
cross join lateral jsonb_array_elements(t.value->'players') p
where s.sport_slug = 'football' and (p.value->'player'->>'id') ~ '^[1-9][0-9]*$'
order by e.league_id, p.value->'player'->>'id', s.synced_at desc;
insert into public.api_sports_player_directory
select distinct on (s.sport_slug, case when s.sport_slug = 'formula-1' then 'f1' else e.league_id end,
  coalesce(p.value->'player'->>'id', p.value->'driver'->>'id'))
  s.sport_slug, case when s.sport_slug = 'formula-1' then 'f1' else e.league_id end,
  coalesce(p.value->'player'->>'id', p.value->'driver'->>'id')::bigint,
  coalesce(p.value->'player'->>'name', p.value->'driver'->>'name'),
  coalesce(p.value->'team'->>'name', case when p.value->'team'->>'id' = e.home_id then e.home_name else e.away_name end),
  s.synced_at
from public.api_sports_player_game_stats s
join public.api_sports_events e on e.sport_slug = s.sport_slug and e.event_id = s.game_id::text
cross join lateral jsonb_array_elements(s.payload) p
where s.sport_slug in ('basketball', 'formula-1')
order by s.sport_slug, case when s.sport_slug = 'formula-1' then 'f1' else e.league_id end,
  coalesce(p.value->'player'->>'id', p.value->'driver'->>'id'), s.synced_at desc;

create function public.reserve_api_requests(p_product text, p_discord_user_id text, p_requests integer)
returns text language plpgsql set search_path = ''
as $$
declare
  today date := (now() at time zone 'UTC')::date;
  budget public.api_request_budget;
  used integer;
begin
  if p_product not in ('american-football', 'basketball', 'football', 'hockey', 'baseball',
    'rugby', 'handball', 'volleyball', 'mma', 'formula-1')
    or p_requests is null or p_requests not between 1 and 5 then raise exception 'Invalid request batch'; end if;
  if p_discord_user_id is null or p_discord_user_id !~ '^[0-9]{1,20}$' then raise exception 'Invalid Discord ID'; end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('api-user:' || p_discord_user_id, 0));
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('api-product:' || p_product, 0));
  insert into public.api_request_budget(product, day) values(p_product, today) on conflict do nothing;
  select * into budget from public.api_request_budget where product = p_product and day = today;
  if budget.member_requests + p_requests > 20 then return 'Shared member daily allowance exhausted'; end if;
  if budget.last_member_request > now() - interval '5 minutes' then return 'Shared five-minute cooldown: use the cache and retry later'; end if;
  select requests into used from public.api_member_request_usage where discord_user_id = p_discord_user_id and day = today;
  if coalesce(used, 0) + p_requests > 5 then return 'Your five-request daily allowance cannot cover this lookup'; end if;
  insert into public.api_member_request_usage(discord_user_id, day, requests)
    values(p_discord_user_id, today, p_requests)
    on conflict(discord_user_id, day) do update set requests = public.api_member_request_usage.requests + p_requests;
  update public.api_request_budget set member_requests = member_requests + p_requests, last_member_request = now()
    where product = p_product and day = today;
  return 'reserved';
end;
$$;
revoke all on function public.reserve_api_requests(text, text, integer) from public, anon, authenticated;
grant execute on function public.reserve_api_requests(text, text, integer) to service_role;
commit;
