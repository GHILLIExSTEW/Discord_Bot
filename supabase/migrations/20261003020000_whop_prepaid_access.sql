-- "paid" is verified server-side; completed one-time purchases must have finite access.
create or replace function public.discord_has_paid_access(p_discord_user_id text)
returns boolean language sql stable set search_path = ''
as $$
  select exists (
    select 1 from public.whop_memberships as membership
    where membership.discord_user_id = p_discord_user_id
      and membership.paid and membership.status in ('active', 'completed')
      and membership.paid_from <= now() and membership.paid_through > now()
      and membership.verified_at > now() - interval '15 minutes'
  );
$$;

create or replace function public.paid_discord_member_ids()
returns table (discord_user_id text)
language sql stable set search_path = ''
as $$
  select distinct membership.discord_user_id from public.whop_memberships as membership
  where membership.discord_user_id is not null and membership.paid
    and membership.status in ('active', 'completed')
    and membership.paid_from <= now() and membership.paid_through > now()
    and membership.verified_at > now() - interval '15 minutes';
$$;

revoke all on function public.discord_has_paid_access(text) from public, anon, authenticated;
revoke all on function public.paid_discord_member_ids() from public, anon, authenticated;
grant execute on function public.discord_has_paid_access(text) to service_role;
grant execute on function public.paid_discord_member_ids() to service_role;
