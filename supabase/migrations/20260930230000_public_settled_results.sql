create or replace function public.public_settled_results()
returns table (
  created_at timestamptz,
  settled_at timestamptz,
  sport text,
  capper text,
  selection text,
  odds integer,
  units numeric,
  status text,
  net_units numeric
)
language sql
stable
security definer
set search_path = ''
as $$
  with published_settled as (
    select distinct on (plays.message_id)
      plays.id,
      plays.user_id,
      plays.sport_id,
      plays.team_name,
      plays.units,
      plays.odds,
      plays.status,
      plays.created_at,
      plays.settled_at,
      plays.message_id
    from public.plays as plays
    where plays.message_id is not null
      and plays.settled_at is not null
      and plays.status in ('win', 'loss', 'void', 'partial')
    order by plays.message_id, plays.id
  )
  select
    plays.created_at,
    plays.settled_at,
    coalesce(nullif(btrim(sports.name), ''), 'Other') as sport,
    coalesce(nullif(btrim(users.display_name), ''), 'Playmaker Picks') as capper,
    coalesce(
      (
        select string_agg(nullif(btrim(legs.selection), ''), ' / ' order by legs.leg_number)
        from public.play_legs as legs
        where legs.play_id = plays.id
      ),
      nullif(btrim(plays.team_name), ''),
      'Official play'
    ) as selection,
    plays.odds,
    plays.units,
    plays.status,
    case plays.status
      when 'win' then round(plays.units * case when plays.odds > 0 then plays.odds::numeric / 100 else 100::numeric / abs(plays.odds) end, 2)
      when 'loss' then -plays.units
      when 'partial' then round(plays.units * case when plays.odds > 0 then plays.odds::numeric / 100 else 100::numeric / abs(plays.odds) end * 0.5, 2)
      else 0::numeric
    end as net_units
  from published_settled as plays
  left join public.sports as sports on sports.id = plays.sport_id
  left join public.users as users on users.id = plays.user_id
  order by plays.settled_at desc, plays.id desc;
$$;

revoke all on function public.public_settled_results() from public;
revoke all on function public.public_settled_results() from anon, authenticated;
grant execute on function public.public_settled_results() to anon, authenticated;