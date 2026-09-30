create table if not exists public.capper_role_roster (
  public_id uuid primary key default gen_random_uuid(),
  discord_user_id text not null unique,
  display_name text not null,
  is_authorized boolean not null default true,
  updated_at timestamptz not null default now()
);

alter table public.capper_role_roster enable row level security;

revoke all on public.capper_role_roster from anon, authenticated;
grant select, insert, update, delete on public.capper_role_roster to service_role;

create or replace view public.public_cappers as
select public_id, display_name
from public.capper_role_roster
where is_authorized = true;

create or replace view public.public_results as
select
  p.id,
  p.created_at,
  p.settled_at,
  coalesce(s.name, 'Unknown sport') as sport,
  coalesce(p.play_text, '') as selection,
  p.odds,
  p.units,
  p.status,
  case
    when p.status = 'win' then p.units * case when p.odds > 0 then p.odds / 100.0 else 100.0 / abs(p.odds) end
    when p.status = 'loss' then -p.units
    when p.status = 'partial' then 0.5 * p.units * case when p.odds > 0 then p.odds / 100.0 else 100.0 / abs(p.odds) end
    else 0
  end as net_units,
  case when roster.is_authorized then roster.display_name else 'Former capper' end as capper,
  case when roster.is_authorized then roster.public_id else null end as capper_public_id
from public.plays p
join public.users u on u.id = p.user_id
join public.capper_role_roster roster on roster.discord_user_id = u.discord_user_id
left join public.sports s on s.id = p.sport_id
where p.status in ('win', 'loss', 'void', 'partial', 'regraded');

create or replace view public.public_capper_plays as
select
  roster.public_id as capper_public_id,
  p.id,
  p.created_at,
  p.settled_at,
  coalesce(s.name, 'Unknown sport') as sport,
  coalesce(p.play_text, '') as selection,
  p.odds,
  p.units,
  p.status,
  case
    when p.status = 'win' then p.units * case when p.odds > 0 then p.odds / 100.0 else 100.0 / abs(p.odds) end
    when p.status = 'loss' then -p.units
    when p.status = 'partial' then 0.5 * p.units * case when p.odds > 0 then p.odds / 100.0 else 100.0 / abs(p.odds) end
    else 0
  end as net_units
from public.plays p
join public.users u on u.id = p.user_id
join public.capper_role_roster roster on roster.discord_user_id = u.discord_user_id
left join public.sports s on s.id = p.sport_id
where roster.is_authorized = true
  and p.status in ('win', 'loss', 'void', 'partial', 'regraded');

revoke all on public.public_cappers, public.public_results, public.public_capper_plays from anon, authenticated;
grant select on public.public_cappers, public.public_results, public.public_capper_plays to anon, authenticated;
