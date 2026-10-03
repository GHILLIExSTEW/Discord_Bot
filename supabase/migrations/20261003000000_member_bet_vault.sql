-- Member tickets are deliberately isolated from official plays and public results.
create table public.member_bets (
  id bigint generated always as identity primary key,
  source_message_id text not null unique,
  channel_id text not null,
  guild_id text not null,
  owner_id text not null,
  owner_name text not null,
  image_path text not null unique,
  card_message_id text unique,
  original_removed boolean not null default false,
  status text not null default 'processing'
    check (status in ('processing', 'draft', 'open', 'review', 'win', 'loss', 'void')),
  details jsonb not null default '{}'::jsonb,
  event jsonb,
  units numeric check (units > 0),
  odds integer check (abs(odds) >= 100),
  verification text,
  review_reason text,
  attempts integer not null default 0,
  next_check_at timestamptz not null default now(),
  card_dirty boolean not null default true,
  created_at timestamptz not null default now(),
  confirmed_at timestamptz,
  settled_at timestamptz,
  updated_at timestamptz not null default now()
);

create index member_bets_pending on public.member_bets (next_check_at)
  where status in ('processing', 'open');

create table public.member_bet_audit (
  id bigint generated always as identity primary key,
  bet_id bigint not null references public.member_bets(id),
  actor_id text not null,
  result text not null check (result in ('win', 'loss', 'void')),
  verification text not null,
  reason text not null check (length(btrim(reason)) > 0),
  created_at timestamptz not null default now()
);

alter table public.member_bets enable row level security;
alter table public.member_bet_audit enable row level security;
revoke all on public.member_bets, public.member_bet_audit from public, anon, authenticated;
grant all on public.member_bets, public.member_bet_audit to service_role;
grant usage, select on sequence public.member_bets_id_seq, public.member_bet_audit_id_seq to service_role;

create function public.settle_member_bet(
  p_bet_id bigint, p_actor_id text, p_result text, p_verification text, p_reason text
) returns boolean
language plpgsql
set search_path = ''
as $$
begin
  if p_result not in ('win', 'loss', 'void')
     or p_verification not in ('API-verified', 'Moderator-settled')
     or length(btrim(coalesce(p_reason, ''))) = 0 then
    raise exception 'Invalid member bet settlement';
  end if;
  update public.member_bets
  set status = p_result, verification = p_verification,
      settled_at = now(), updated_at = now(), card_dirty = true
  where id = p_bet_id and status in ('open', 'review') and confirmed_at is not null;
  if not found then
    return false;
  end if;
  insert into public.member_bet_audit (bet_id, actor_id, result, verification, reason)
  values (p_bet_id, p_actor_id, p_result, p_verification, p_reason);
  return true;
end;
$$;

revoke all on function public.settle_member_bet(bigint, text, text, text, text) from public, anon, authenticated;
grant execute on function public.settle_member_bet(bigint, text, text, text, text) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('member-bet-vault', 'member-bet-vault', false, 10485760, array['image/png'])
on conflict (id) do update
set public = false, file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
