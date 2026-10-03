begin;
create table public.api_request_budget (
  product text not null,
  day date not null,
  system_requests integer not null default 0,
  member_requests integer not null default 0,
  last_member_request timestamptz,
  primary key (product, day)
);
create table public.api_member_request_usage (
  discord_user_id text not null,
  day date not null,
  requests integer not null default 0,
  primary key (discord_user_id, day)
);
alter table public.api_request_budget enable row level security;
alter table public.api_member_request_usage enable row level security;
revoke all on public.api_request_budget, public.api_member_request_usage from public, anon, authenticated;
grant select, insert, update on public.api_request_budget, public.api_member_request_usage to service_role;

create function public.reserve_api_request(p_product text, p_discord_user_id text default null)
returns text language plpgsql set search_path = ''
as $$
declare
  today date := (now() at time zone 'UTC')::date;
  budget public.api_request_budget;
  used integer;
begin
  if p_product not in ('american-football', 'basketball', 'football', 'hockey', 'baseball',
    'rugby', 'handball', 'volleyball', 'mma', 'formula-1') then
    raise exception 'Unknown API product';
  end if;
  -- Shared lock order prevents concurrent callers or restarts exceeding limits.
  if p_discord_user_id is not null then
    if p_discord_user_id !~ '^[0-9]{1,20}$' then raise exception 'Invalid Discord ID'; end if;
    perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('api-user:' || p_discord_user_id, 0));
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('api-product:' || p_product, 0));
  insert into public.api_request_budget(product, day) values(p_product, today)
    on conflict do nothing;
  select * into budget from public.api_request_budget where product = p_product and day = today;
  if p_discord_user_id is null then
    if budget.system_requests >= 80 then return 'System daily allowance exhausted'; end if;
    update public.api_request_budget set system_requests = system_requests + 1
      where product = p_product and day = today;
  else
    if budget.member_requests >= 20 then return 'Shared member daily allowance exhausted'; end if;
    if budget.last_member_request > now() - interval '5 minutes' then
      return 'Shared five-minute cooldown: use the cache and retry later';
    end if;
    select requests into used from public.api_member_request_usage
      where discord_user_id = p_discord_user_id and day = today;
    if coalesce(used, 0) >= 5 then return 'Your five-refresh daily allowance is exhausted'; end if;
    insert into public.api_member_request_usage(discord_user_id, day, requests)
      values(p_discord_user_id, today, 1)
      on conflict(discord_user_id, day) do update
      set requests = public.api_member_request_usage.requests + 1;
    update public.api_request_budget
      set member_requests = member_requests + 1, last_member_request = now()
      where product = p_product and day = today;
  end if;
  return 'reserved';
end;
$$;
revoke all on function public.reserve_api_request(text, text) from public, anon, authenticated;
grant execute on function public.reserve_api_request(text, text) to service_role;
commit;
