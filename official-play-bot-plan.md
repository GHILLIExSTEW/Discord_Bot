# Official Play Bot — Plan

Track official plays by **units, legs, odds, result**. Save play text only for the Discord post. Do not parse team names or chat.

Existing pieces to keep:

- Proxmox LXC `101` / `DiscordBot`
- Supabase `unit_entries`, `unit_results`
- Tally by day / week / month / year
- Officials only (not LIVE / lean / chat)

---

## Goal

Handicapper runs `/play` → bot stores a row → bot posts a short embed → later they tap WIN / LOSS / VOID / REGRADE / HALF → tally updates.

Chat messages are never the source of truth.

---

## Locked decisions

| Decision | Choice |
|---|---|
| What the tally uses | units, result (and half = 0.5 × units) |
| What is displayed but ignored for math | play text |
| Intake | one `/play` modal, not freeform chat |
| Odds | one ticket price (parlay price, not per-leg) |
| Voids / 3+ legs | REGRADE modal (`legs left` + `new odds`) or HALF shortcut |
| Who may submit / settle | official roles + play author + OPERATOR |
| Deleted messages | do not delete; VOID instead |
| “To win” | bot calculates and shows; users do not type it |

---

## Phase 0 — Snapshot before you touch data

In the **bot** Supabase project (not the shop DB):

```sql
create table public.unit_entries_backup as select * from public.unit_entries;
create table public.unit_results_backup as select * from public.unit_results;
```

Confirm row counts. Do not truncate again without this.

---

## Phase 1 — Schema

Add a plays table. Keep the old tables as a write-through so current tally queries still work.

```sql
create table public.unit_plays (
  id bigint generated always as identity primary key,
  message_id text unique,
  user_id text not null,
  username text,
  units numeric not null check (units > 0),
  legs int not null default 1 check (legs >= 1),
  odds int not null,
  plays_text text,
  status text not null default 'open'
    check (status in ('open','win','loss','void','half')),
  settled_units numeric,
  created_at timestamptz not null default now(),
  settled_at timestamptz
);

create index on public.unit_plays (user_id, created_at);
create index on public.unit_plays (status);

alter table public.unit_results
  drop constraint if exists unit_results_result_check;

alter table public.unit_results
  add constraint unit_results_result_check
  check (result = any (array['win','loss','void','half']));
```

`odds` is American integer: `-110`, `164` (store `+164` as `164`).

`plays_text` is optional. Never used in sums.

Write-through on settle:

- `unit_entries`: one row per play (`user_id`, `total_units` = original units, `message_id`, `created_at`)
- `unit_results`: one row per settled play (`result`, `total_units` = original units, same `message_id`)

Tally SQL:

```sql
sum(case
  when result = 'win'  then total_units
  when result = 'half' then total_units * 0.5
  else 0
end) as units_won,

sum(case when result = 'loss' then total_units else 0 end) as units_lost
-- void ignored
```

---

## Phase 2 — `/play` intake (low friction)

Slash command `/play` → modal.

| Field | Required | Default | Notes |
|---|---|---|---|
| Units | yes | `1` | allow `.5` steps (`0.5`, `1.5`) |
| Legs | yes | `1` | integer |
| Ticket odds | yes | `-110` | accept `-110`, `+164`, `164` |
| Plays | no | empty | multiline, display only |
| Optional slash option `ping` | no | none | role to mention on the post |

Validation:

- units > 0
- legs >= 1
- odds not `0`
- only allowed roles can submit

On submit:

1. Insert `unit_plays` with `status=open`, `message_id` null
2. Post embed in the current channel (or a configured #officials channel)
3. Update `unit_plays.message_id`
4. Insert matching `unit_entries` row
5. Add buttons on the embed

Skip any regex on other messages for official tracking. Leave old chat-parser on only until this ships, then disable it so tennis paragraphs stop creating junk rows.

---

## Phase 3 — Posted embed

```
OFFICIAL    1.5u  •  2-leg  •  +164
To win  2.46u

Jeanty u16.5 rush
Sinner ML

Posted by CapnHooks
[ WIN ] [ LOSS ] [ VOID ] [ HALF ] [ REGRADE ]
```

If plays box was empty, omit that block.

To-win (display only):

- American ≥ 0: `units * (odds / 100)`
- American < 0: `units * (100 / abs(odds))`

Buttons visible to everyone, **clicks accepted** only from play author or OPERATOR.

---

## Phase 4 — Settlement

### WIN / LOSS / VOID / HALF

No extra typing.

| Button | `status` | Tally |
|---|---|---|
| WIN | `win` | +units |
| LOSS | `loss` | −units |
| VOID | `void` | 0 |
| HALF | `half` | +0.5 × units |

Overwrite the same `message_id` if they change their mind. Set `settled_at`, `settled_units`, upsert `unit_results`.

Edit the embed footer to `SETTLED • WIN` (etc.) so the room sees state.

### REGRADE (voided legs, 2+ original legs)

Opens a 2-field modal:

- Legs left
- New ticket odds

Bot updates `legs` + `odds` on `unit_plays`, edits the embed, leaves status `open`. Poster then hits WIN / LOSS / VOID / HALF on the **regraded** ticket.

Rules of thumb for the room (put in a pinned message, not in code):

- 2-leg, 1 void → REGRADE to 1-leg at the surviving price, **or** HALF
- 3+ legs, some voids → REGRADE (`legs left` + new book price). Do not default to HALF
- All legs dead → VOID
- Ticket still lost after regrade → LOSS

---

## Phase 5 — Tally commands

Keep existing period commands. Point them at `unit_results` with the new `void` / `half` cases.

`/tally period:[day|week|month|year] [member]`

Optional `/plays open` — list this user’s open tickets so they don’t forget to settle.

Timezone: `America/New_York`.

---

## Phase 6 — Permissions and channel

Config (env or existing config file):

```
OFFICIAL_ROLE_IDS=...
OPERATOR_ROLE_IDS=...
OFFICIAL_CHANNEL_ID=...     # optional; if set, /play only works there
```

LIVE / lean / community chat: no `/play`, no buttons that write rows.

---

## Phase 7 — Cut over

1. Deploy schema
2. Deploy bot with `/play` + buttons; leave old parser on for a day
3. Pin a 6-line how-to in #officials
4. Turn **off** message-regex recording
5. Watch one slate; confirm `unit_plays` + `unit_results` stay 1:1 per message_id
6. Only then delete or archive backup tables

---

## Pin this for the room

```
Officials: use /play
Units + legs + ticket odds required. Plays text optional (shows on the post).
Settle on the post: WIN / LOSS / VOID.
Leg died: REGRADE (legs left + new odds) then WIN/LOSS, or HALF.
Do not delete the message.
Leans and LIVE chat are not tracked.
```

---

## Out of scope (do not build in v1)

- Per-leg odds entry
- Auto-pull from a sportsbook
- Reading tennis chat to detect voids
- Dollar P&L / CLV / closing line
- Editing other people’s plays
- Backfill from old freeform messages (separate one-off if needed)

---

## Build order

1. SQL in Phase 1  
2. `/play` modal + embed + `unit_plays` insert  
3. Four settle buttons + `unit_results` upsert  
4. REGRADE modal  
5. Tally query update  
6. Disable old parser  
7. Pin the room rules  

Estimate if you already have the discord.py bot running: one focused session for 1–4, short follow-up for 5–7.

---

## Test cases before you call it done

| Case | Expected |
|---|---|
| `1u` single `-110`, WIN | +1u |
| `1.5u` `2leg` `+164`, LOSS | −1.5u |
| Same ticket, VOID | 0, not a loss |
| WIN then change to VOID | one row, result void |
| 2-leg, REGRADE to 1-leg `-110`, WIN | + original units |
| 4-leg, REGRADE to 3-leg `+240`, LOSS | − original units |
| HALF on 2-leg void | +0.5 × units |
| Lean posted in chat with no `/play` | no row |
| Random member taps WIN | ignored |
| Plays box empty | embed still posts |
| Plays box filled | text on embed, same tally |
