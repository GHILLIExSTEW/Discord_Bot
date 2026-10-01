alter table public.member_profiles
  add column if not exists display_name text not null default 'Playmaker Member',
  add column if not exists public_handle text,
  add column if not exists avatar_url text,
  add column if not exists public_profile_enabled boolean not null default false,
  add column if not exists timezone text not null default 'America/New_York',
  add column if not exists discord_alerts_enabled boolean not null default false,
  add column if not exists email_alerts_enabled boolean not null default false;

update public.member_profiles
set public_handle = 'member-' || substr(replace(user_id::text, '-', ''), 1, 12)
where public_handle is null;

update public.member_profiles as profile
set display_name = coalesce(
  nullif(profile.display_name, 'Playmaker Member'),
  nullif(account.raw_user_meta_data ->> 'full_name', ''),
  nullif(account.raw_user_meta_data ->> 'name', ''),
  nullif(account.raw_user_meta_data ->> 'username', ''),
  'Playmaker Member'
)
from auth.users as account
where account.id = profile.user_id
  and profile.display_name = 'Playmaker Member';

alter table public.member_profiles
  alter column public_handle set default ('member-' || substr(replace(gen_random_uuid()::text, '-', ''), 1, 12)),
  alter column public_handle set not null;

create unique index if not exists idx_member_profiles_public_handle
  on public.member_profiles(public_handle);

do $$
begin
  alter table public.member_profiles
    add constraint member_profiles_public_handle_format
    check (public_handle ~ '^member-[a-f0-9]{12}$' or public_handle ~ '^[a-z0-9][a-z0-9-]{2,29}$');
exception when duplicate_object then null;
end;
$$;

do $$
begin
  alter table public.member_profiles
    add constraint member_profiles_display_name_length
    check (length(btrim(display_name)) between 1 and 60);
exception when duplicate_object then null;
end;
$$;

do $$
begin
  alter table public.member_profiles
    add constraint member_profiles_avatar_https
    check (avatar_url is null or avatar_url like 'https://%');
exception when duplicate_object then null;
end;
$$;

do $$
begin
  alter table public.member_profiles
    add constraint member_profiles_timezone_not_empty
    check (length(btrim(timezone)) between 1 and 80);
exception when duplicate_object then null;
end;
$$;

revoke all on public.member_profiles from public, anon, authenticated;
grant select on public.member_profiles to authenticated;
grant update (display_name, public_handle, avatar_url, public_profile_enabled, timezone, discord_alerts_enabled, email_alerts_enabled)
  on public.member_profiles to authenticated;

drop policy if exists member_profiles_select_self on public.member_profiles;
create policy member_profiles_select_self
  on public.member_profiles for select to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists member_profiles_update_self on public.member_profiles;
create policy member_profiles_update_self
  on public.member_profiles for update to authenticated
  using (user_id = (select auth.uid()) and age_verified_at is not null)
  with check (user_id = (select auth.uid()) and age_verified_at is not null);

create or replace function public.public_member_profile(p_public_handle text)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'display_name', profile.display_name,
    'public_handle', profile.public_handle,
    'avatar_url', case
      when coalesce(profile.avatar_url, account.raw_user_meta_data ->> 'avatar_url', account.raw_user_meta_data ->> 'picture') like 'https://%'
      then coalesce(profile.avatar_url, account.raw_user_meta_data ->> 'avatar_url', account.raw_user_meta_data ->> 'picture')
      else null
    end,
    'created_at', profile.created_at,
    'favorite_sports', coalesce((
      select jsonb_agg(jsonb_build_object('id', sports.id, 'name', sports.name) order by sports.name)
      from public.member_favorite_sports as favorite
      join public.sports as sports on sports.id = favorite.sport_id
      where favorite.user_id = profile.user_id
    ), '[]'::jsonb),
    'favorite_cappers', coalesce((
      select jsonb_agg(jsonb_build_object('sport', sports.name, 'capper', favorite.capper_name) order by sports.name, favorite.capper_name)
      from public.member_favorite_cappers as favorite
      join public.sports as sports on sports.id = favorite.sport_id
      where favorite.user_id = profile.user_id
    ), '[]'::jsonb)
  )
  from public.member_profiles as profile
  join auth.users as account on account.id = profile.user_id
  where profile.public_handle = lower(btrim(p_public_handle))
    and profile.public_profile_enabled
    and profile.age_verified_at is not null;
$$;

create or replace function public.delete_member_account()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'Authentication required.' using errcode = '28000';
  end if;
  delete from auth.users where id = auth.uid();
  return found;
end;
$$;

revoke all on function public.public_member_profile(text) from public;
grant execute on function public.public_member_profile(text) to anon, authenticated;
revoke all on function public.delete_member_account() from public, anon;
grant execute on function public.delete_member_account() to authenticated;