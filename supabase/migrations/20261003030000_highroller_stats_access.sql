create function public.discord_has_paid_plan_access(
  p_discord_user_id text, p_account_id text, p_plan_ids text[]
)
returns boolean language sql stable set search_path = ''
as $$
  select exists (
    select 1 from public.whop_memberships as membership
    where membership.discord_user_id = p_discord_user_id
      and membership.account_id = p_account_id
      and membership.plan_id = any(p_plan_ids)
      and membership.paid and membership.status in ('active', 'completed')
      and membership.paid_from <= now() and membership.paid_through > now()
      and membership.verified_at > now() - interval '15 minutes'
  );
$$;

revoke all on function public.discord_has_paid_plan_access(text, text, text[])
from public, anon, authenticated;
grant execute on function public.discord_has_paid_plan_access(text, text, text[])
to service_role;
