begin;
create table public.api_sports_player_game_stats (
  sport_slug text not null check (sport_slug in ('nfl', 'ncaa', 'basketball', 'football', 'formula-1')),
  game_id bigint not null check (game_id > 0),
  payload jsonb not null check (jsonb_typeof(payload) = 'array'),
  synced_at timestamptz not null,
  primary key (sport_slug, game_id)
);
alter table public.api_sports_player_game_stats enable row level security;
revoke all on public.api_sports_player_game_stats from public, anon, authenticated;
grant select, insert, update on public.api_sports_player_game_stats to service_role;
commit;
