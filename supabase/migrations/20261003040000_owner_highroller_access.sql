begin;

create table public.owner_membership_grants (
  discord_user_id text primary key check (discord_user_id ~ '^[0-9]{1,20}$'),
  account_id text not null,
  tier text not null check (tier = 'highroller'),
  vault_access boolean not null default false,
  reason text not null check (length(trim(reason)) > 0),
  starts_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  check (expires_at is null or expires_at > starts_at)
);

create table public.owner_membership_grant_audit (
  id bigint generated always as identity primary key,
  discord_user_id text not null,
  action text not null,
  previous_snapshot jsonb,
  snapshot jsonb,
  changed_at timestamptz not null default now()
);

alter table public.owner_membership_grants enable row level security;
alter table public.owner_membership_grant_audit enable row level security;
revoke all on public.owner_membership_grants, public.owner_membership_grant_audit
from public, anon, authenticated;
grant select, insert, update, delete on public.owner_membership_grants to service_role;
grant select, insert on public.owner_membership_grant_audit to service_role;
grant usage, select on sequence public.owner_membership_grant_audit_id_seq to service_role;

create function public.audit_owner_membership_grant()
returns trigger language plpgsql set search_path = ''
as $$
begin
  insert into public.owner_membership_grant_audit
    (discord_user_id, action, previous_snapshot, snapshot)
  values (
    case when tg_op = 'DELETE' then old.discord_user_id else new.discord_user_id end,
    tg_op,
    case when tg_op = 'INSERT' then null else pg_catalog.to_jsonb(old) end,
    case when tg_op = 'DELETE' then null else pg_catalog.to_jsonb(new) end
  );
  return null;
end;
$$;
revoke all on function public.audit_owner_membership_grant() from public, anon, authenticated;

create trigger owner_membership_grant_audit
after insert or update or delete on public.owner_membership_grants
for each row execute function public.audit_owner_membership_grant();

-- Complimentary owner access is not payment evidence and never enters Whop snapshots.
insert into public.owner_membership_grants
  (discord_user_id, account_id, tier, vault_access, reason, expires_at)
values (
  '761388542965448767', 'biz_rCNwfXRlnl0bFU', 'highroller', true,
  'Lifetime complimentary HIGHROLLER owner access, including Member Vault, explicitly authorized October 3, 2026.',
  null
);

-- Retain existing RPC names for callers; these now report authorized access,
-- not proof of a payment. Paid snapshots retain all existing validation.
create or replace function public.discord_has_paid_access(p_discord_user_id text)
returns boolean language sql stable set search_path = ''
as $$
  select exists (
    select 1 from public.whop_memberships as membership
    where membership.discord_user_id = p_discord_user_id
      and membership.paid and membership.status in ('active', 'completed')
      and membership.paid_from <= now() and membership.paid_through > now()
      and membership.verified_at > now() - interval '15 minutes'
  ) or exists (
    select 1 from public.owner_membership_grants as owner_grant
    where owner_grant.discord_user_id = p_discord_user_id
      and owner_grant.vault_access and owner_grant.revoked_at is null
      and owner_grant.starts_at <= now()
      and (owner_grant.expires_at is null or owner_grant.expires_at > now())
  );
$$;

create or replace function public.paid_discord_member_ids()
returns table (discord_user_id text)
language sql stable set search_path = ''
as $$
  select membership.discord_user_id from public.whop_memberships as membership
  where membership.discord_user_id is not null and membership.paid
    and membership.status in ('active', 'completed')
    and membership.paid_from <= now() and membership.paid_through > now()
    and membership.verified_at > now() - interval '15 minutes'
  union
  select owner_grant.discord_user_id from public.owner_membership_grants as owner_grant
  where owner_grant.vault_access and owner_grant.revoked_at is null
    and owner_grant.starts_at <= now()
    and (owner_grant.expires_at is null or owner_grant.expires_at > now());
$$;

create or replace function public.discord_has_paid_plan_access(
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
  ) or exists (
    select 1 from public.owner_membership_grants as owner_grant
    where owner_grant.discord_user_id = p_discord_user_id
      and owner_grant.account_id = p_account_id and owner_grant.tier = 'highroller'
      and owner_grant.revoked_at is null and owner_grant.starts_at <= now()
      and (owner_grant.expires_at is null or owner_grant.expires_at > now())
      and pg_catalog.cardinality(p_plan_ids) > 0
  );
$$;

revoke all on function public.discord_has_paid_access(text) from public, anon, authenticated;
revoke all on function public.paid_discord_member_ids() from public, anon, authenticated;
revoke all on function public.discord_has_paid_plan_access(text, text, text[]) from public, anon, authenticated;
grant execute on function public.discord_has_paid_access(text) to service_role;
grant execute on function public.paid_discord_member_ids() to service_role;
grant execute on function public.discord_has_paid_plan_access(text, text, text[]) to service_role;

do $$
begin
  if not public.discord_has_paid_access('761388542965448767')
     or not public.discord_has_paid_plan_access(
       '761388542965448767', 'biz_rCNwfXRlnl0bFU', array['plan_10PuOcOt9rHNL']
     ) then
    raise exception 'Owner grant did not authorize vault and HIGHROLLER access';
  end if;
  if public.discord_has_paid_access('0')
     or public.discord_has_paid_plan_access(
       '761388542965448767', 'biz_wrong', array['plan_10PuOcOt9rHNL']
     ) then
    raise exception 'Owner grant authorized an unknown identity or incorrect seller';
  end if;
  if not exists (
    select 1 from public.owner_membership_grant_audit
    where discord_user_id = '761388542965448767' and action = 'INSERT'
  ) then
    raise exception 'Owner grant audit was not recorded';
  end if;
end;
$$;

commit;
