-- Server-only Whop snapshots. Roles and client-supplied metadata are not proof of payment.
create table public.whop_memberships (
  membership_id text primary key,
  whop_user_id text,
  discord_user_id text check (discord_user_id is null or discord_user_id ~ '^[0-9]{1,20}$'),
  account_id text not null,
  plan_id text not null,
  status text not null,
  paid_from timestamptz,
  paid_through timestamptz,
  payment_id text,
  paid boolean not null,
  cancel_at_period_end boolean not null,
  source_updated_at timestamptz not null,
  verified_at timestamptz not null,
  verification_reason text not null,
  check (not paid or (payment_id is not null and paid_through > paid_from and discord_user_id is not null))
);

create table public.whop_membership_audit (
  id bigint generated always as identity primary key,
  membership_id text not null,
  snapshot jsonb not null,
  created_at timestamptz not null default now()
);

alter table public.whop_memberships enable row level security;
alter table public.whop_membership_audit enable row level security;
revoke all on public.whop_memberships, public.whop_membership_audit from public, anon, authenticated;
grant all on public.whop_memberships, public.whop_membership_audit to service_role;
grant usage, select on sequence public.whop_membership_audit_id_seq to service_role;

create function public.record_whop_membership(p_snapshot jsonb)
returns boolean language plpgsql set search_path = ''
as $$
declare
  incoming public.whop_memberships;
  previous jsonb;
begin
  incoming := pg_catalog.jsonb_populate_record(null::public.whop_memberships, p_snapshot);
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(incoming.membership_id, 0));
  select pg_catalog.to_jsonb(membership) - 'verified_at' into previous
  from public.whop_memberships as membership where membership_id = incoming.membership_id;
  insert into public.whop_memberships select incoming.*
  on conflict (membership_id) do update set
    whop_user_id = excluded.whop_user_id, discord_user_id = excluded.discord_user_id,
    account_id = excluded.account_id, plan_id = excluded.plan_id, status = excluded.status,
    paid_from = excluded.paid_from, paid_through = excluded.paid_through,
    payment_id = excluded.payment_id, paid = excluded.paid,
    cancel_at_period_end = excluded.cancel_at_period_end,
    source_updated_at = excluded.source_updated_at, verified_at = excluded.verified_at,
    verification_reason = excluded.verification_reason
  where public.whop_memberships.source_updated_at <= excluded.source_updated_at
    and public.whop_memberships.verified_at < excluded.verified_at;
  if not found then return false; end if;
  if previous is distinct from (p_snapshot - 'verified_at') then
    insert into public.whop_membership_audit (membership_id, snapshot)
    values (incoming.membership_id, p_snapshot - 'verified_at');
  end if;
  return true;
end;
$$;

create function public.discord_has_paid_access(p_discord_user_id text)
returns boolean language sql stable set search_path = ''
as $$
  select exists (
    select 1 from public.whop_memberships as membership
    where membership.discord_user_id = p_discord_user_id
      and membership.paid and membership.status = 'active'
      and membership.paid_from <= now() and membership.paid_through > now()
      and membership.verified_at > now() - interval '15 minutes'
  );
$$;

create function public.paid_discord_member_ids()
returns table (discord_user_id text)
language sql stable set search_path = ''
as $$
  select distinct membership.discord_user_id from public.whop_memberships as membership
  where membership.discord_user_id is not null and membership.paid
    and membership.status = 'active'
    and membership.paid_from <= now() and membership.paid_through > now()
    and membership.verified_at > now() - interval '15 minutes';
$$;

revoke all on function public.record_whop_membership(jsonb) from public, anon, authenticated;
revoke all on function public.discord_has_paid_access(text) from public, anon, authenticated;
revoke all on function public.paid_discord_member_ids() from public, anon, authenticated;
grant execute on function public.record_whop_membership(jsonb) to service_role;
grant execute on function public.discord_has_paid_access(text) to service_role;
grant execute on function public.paid_discord_member_ids() to service_role;
