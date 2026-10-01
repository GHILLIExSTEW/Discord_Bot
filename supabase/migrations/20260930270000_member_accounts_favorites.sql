create table if not exists public.member_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  age_verified_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.member_favorite_sports (
  user_id uuid not null references auth.users(id) on delete cascade,
  sport_id bigint not null references public.sports(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, sport_id)
);

create table if not exists public.member_favorite_cappers (
  user_id uuid not null references auth.users(id) on delete cascade,
  sport_id bigint not null references public.sports(id) on delete cascade,
  capper_name text not null check (length(btrim(capper_name)) between 1 and 120),
  created_at timestamptz not null default now(),
  primary key (user_id, sport_id, capper_name)
);

alter table public.member_profiles enable row level security;
alter table public.member_favorite_sports enable row level security;
alter table public.member_favorite_cappers enable row level security;

revoke all on public.member_profiles from public, anon, authenticated;
revoke all on public.member_favorite_sports from public, anon, authenticated;
revoke all on public.member_favorite_cappers from public, anon, authenticated;
grant select on public.member_profiles to authenticated;
grant select, insert, delete on public.member_favorite_sports to authenticated;
grant select, insert, delete on public.member_favorite_cappers to authenticated;

create policy member_profiles_select_self
  on public.member_profiles for select to authenticated
  using (user_id = (select auth.uid()));

create policy member_favorite_sports_select_verified_self
  on public.member_favorite_sports for select to authenticated
  using (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );
create policy member_favorite_sports_insert_verified_self
  on public.member_favorite_sports for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );
create policy member_favorite_sports_delete_verified_self
  on public.member_favorite_sports for delete to authenticated
  using (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );

create policy member_favorite_cappers_select_verified_self
  on public.member_favorite_cappers for select to authenticated
  using (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );
create policy member_favorite_cappers_insert_verified_self
  on public.member_favorite_cappers for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );
create policy member_favorite_cappers_delete_verified_self
  on public.member_favorite_cappers for delete to authenticated
  using (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.member_profiles as profile
      where profile.user_id = (select auth.uid()) and profile.age_verified_at is not null
    )
  );

create or replace function public.verify_member_age(p_birth_date date)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := auth.uid();
begin
  if current_user_id is null then
    raise exception 'Authentication required.' using errcode = '28000';
  end if;

  if p_birth_date is null or p_birth_date > (current_date - interval '21 years')::date then
    return false;
  end if;

  insert into public.member_profiles (user_id, age_verified_at)
  values (current_user_id, now())
  on conflict (user_id) do update
    set age_verified_at = coalesce(public.member_profiles.age_verified_at, excluded.age_verified_at);

  return true;
end;
$$;

create or replace function public.public_favorite_sports()
returns table (id bigint, api_slug text, name text)
language sql
stable
security definer
set search_path = ''
as $$
  select sports.id, sports.api_slug, sports.name
  from public.sports as sports
  where sports.is_active and sports.api_slug <> 'official'
  order by sports.name;
$$;

create or replace function public.public_favorite_cappers()
returns table (sport_id bigint, sport text, capper_name text)
language sql
stable
security definer
set search_path = ''
as $$
  select distinct
    plays.sport_id,
    sports.name,
    coalesce(nullif(btrim(users.display_name), ''), nullif(btrim(users.username), ''), 'Playmaker Picks') as capper_name
  from public.plays as plays
  join public.sports as sports on sports.id = plays.sport_id
  left join public.users as users on users.id = plays.user_id
  where plays.message_id is not null
    and plays.settled_at is not null
    and plays.status in ('win', 'loss', 'void', 'partial')
    and sports.api_slug <> 'official'
  order by sports.name, capper_name;
$$;

revoke all on function public.verify_member_age(date) from public, anon;
grant execute on function public.verify_member_age(date) to authenticated;
revoke all on function public.public_favorite_sports() from public;
grant execute on function public.public_favorite_sports() to anon, authenticated;
revoke all on function public.public_favorite_cappers() from public;
grant execute on function public.public_favorite_cappers() to anon, authenticated;