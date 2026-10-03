# Proxmox deployment guide

This project is designed to run as a Python service on a Linux host, such as a Proxmox LXC or VM.

## 1. Prepare the Linux server

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
```

## 2. Clone the repository

```bash
cd /opt
sudo git clone <your-repo-url> discord-bot
cd discord-bot
```

## 3. Create the environment

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in:

- `DISCORD_TOKEN`
- `APPLICATION_ID`
- `GUILD_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `OPENAI_VISION_MODEL`
- `OPENAI_VISION_MODELS`
- `OFFICIAL_ROLE_IDS`
- `OPERATOR_ROLE_IDS`
- `OFFICIAL_CHANNEL_ID`
- `IMAGE_INPUT_CHANNEL_ID`
- `MEMBER_BET_CHANNEL_ID` (optional, separate member photo-submission channel)
- `TEAM_STATS_CHANNEL_ID`

## 4. Validate the Python app

```bash
. .venv/bin/activate
python -m compileall src
python -m pytest -q
```

## 5. Start the bot directly

```bash
. .venv/bin/activate
python -m src.bot
```

## 6. Run as a background service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/discord-bot.service
```

Contents:

```ini
[Unit]
Description=Official Play Discord Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/discord-bot
ExecStart=/opt/discord-bot/.venv/bin/python -m src.bot
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now discord-bot.service
sudo systemctl status discord-bot.service
```

## 7. Useful operational commands

```bash
sudo journalctl -u discord-bot.service -f
sudo systemctl restart discord-bot.service
sudo systemctl stop discord-bot.service
```

## 8. Recommended Proxmox notes

- Run the bot in a Debian LXC or Ubuntu VM.
- Keep the repo on a persistent disk or backup to ensure the `.env` stays intact.
- Put the bot in a dedicated Linux user account if you want tighter controls.
- Keep the `SUPABASE_URL`, `SUPABASE_KEY`, and `DISCORD_TOKEN` in the `.env` file only, never in the repo.

## 9. Member Bet Vault

Before enabling this feature:

1. Apply `supabase/migrations/20261003000000_member_bet_vault.sql` to Supabase.
   Use a server-only **service-role** `SUPABASE_KEY`. The vault tables have RLS
   enabled with no member/public access policies, and `member-bet-vault` is a
   private storage bucket. Never make this bucket public.
   Also apply `supabase/migrations/20261003010000_whop_membership_access.sql`
   and configure the Whop sync below. Without verified paid membership, no new
   submission is accepted.
2. Set `MEMBER_BET_CHANNEL_ID` to a dedicated submission-only channel. It must
   differ from the official, image-input, confirmation, test, result, and
   team-stats channels. Leaving it empty disables the feature.
3. Give the bot View Channel, Read Message History, Send Messages, Embed Links,
   Attach Files, and Manage Messages in that channel. Enable Message Content Intent in the
   Discord developer portal. Give settlement moderators a configured
   `OPERATOR_ROLE_IDS` role or Manage Server permission.
4. Keep the existing vision and API-Sports configuration. Vision processing
   sends the stored photo to the configured OpenAI provider; disclose that
   processing to members. The bot never sends the photo back to a public card.
5. Restart the bot, then submit a test photo and verify deletion, private
   review, confirmation, masked publication, and moderator settlement before
   inviting members to use the channel.

Every human message in this channel is a submission, not conversation. Require
exactly one static JPEG, PNG, or WebP upload, no larger than 10 MB and 16
megapixels; a photo may contain up to ten legs. Text can specify units, but image
links, GIFs, PDFs, and text-only posts are rejected, deleted, and explained by DM.
DMs are not ephemeral interaction responses; when DMs are disabled, failures
are logged without a public reply. Deletion failures are logged and privately
reported to the uploader.

For accepted photos, the bot saves a metadata-stripped copy in private storage
and persists a ticket before deleting the source message. Discord makes the
original visible until deletion, so this is **not zero-exposure concealment**.
Storage failures preserve the original and notify the author rather than lose
the submission. The public processing/draft card contains no extracted game or
selection. Only the uploader and moderators can inspect extracted details through
an ephemeral button response. The uploader confirms actual units, ticket odds,
and public matchup names; selection/event/rule extraction errors require a new,
clearer photo. Confirmed tickets are locked. No member tickets enter official
plays, trackers, website results, or capper records.

After confirmation, public cards show matchup names, units, odds, and a hidden
selection. Safe automatic grading initially supports straight NFL, NCAA
American-football, and basketball full-game moneylines, spreads, and totals
**only when including overtime is explicit**, the author confirms the extracted
fields, and exact home/away names plus the Eastern event date identify one
cached API-Sports event. Pregame checks wait until the scheduled start. Event
requests are shared across tickets within each polling pass, with successful
in-progress checks repeated every 15 minutes. Final FT/AOT scores grade supported
markets; tied moneylines, parlays, props, other sports, unknown rules/dates,
promotions, and cash-outs must not be automatically graded. The author must not
confirm incorrect extraction or special-rule/cashed-out slips as ordinary bets.
API verification verifies an outcome, not proof that a wager was placed.

API/processing failures retry after 5, 10, 20, and 40 minutes; after the fifth
failure the ticket requires moderator review. Cancelled/suspended/postponed
events, unsupported finals, or events unresolved 24 hours after scheduled start
also require review, with selections still hidden. A moderator privately reviews
the ticket and uses **Moderator settle**, entering win/loss/void and a reason.
Authors cannot settle tickets. Only confirmed tickets can settle. Unreadable
photos that exhaust processing retries must be resubmitted; they cannot be
graded. Public cards distinguish `API-verified` from `Moderator-settled`, reveal
sanitized selection text, and never reveal the original photo. Result and audit
reason are written atomically; duplicate settlement requests cannot overwrite
an existing result.

Private reviews include a complete text attachment so long parlays do not lose
details to Discord embed limits. Settled cards attach full sanitized selection
text when it exceeds the embed field limit; open cards never attach that text.

Tickets, private photos, pending checks, and card-update retries persist across
restarts. Persistent card buttons look up the ticket in the database rather than
holding selection data in Discord component IDs. The bot checks pending work
every minute. Moderators should monitor cards marked **Moderator review required**
and the `member_vault_*` / `member_*` error logs. Original photos and audit records
remain in private storage until an administrator removes them under the business's
retention policy; there is no automatic retention cleanup in this release.

## 10. Whop paid-membership verification

### HIGHROLLER cached stats tools

Apply `supabase/migrations/20261003030000_highroller_stats_access.sql` after
the prepaid migration, then deploy/restart the bot. This adds a service-role-only
seller/plan-scoped lookup; missing schema fails closed without preventing the
rest of the bot from starting. `WHOP_HIGHROLLER_PLAN_IDS` defaults to the four
existing HIGHROLLER prepaid IDs in `.env.example`; it must be a nonempty subset
of `WHOP_PAID_PLAN_IDS`. For other Whop products, explicitly override these IDs.
Sync must be enabled. No Discord-role or operator bypass grants these tools.

Commands `/matchup`, `/teamstats`, `/schedule`, and `/results` are private,
guild-only, and require current paid HIGHROLLER access. ALL-STAR, free trials,
refunds, expiry, and stale snapshots deny access. Supported sports: NFL, college
football, basketball, soccer, hockey, and baseball. Use full team names.
Schedule/matchup reads cover the next seven days; results/recent-form reads
cover the past 30 days. Up to ten events are displayed from bounded cached
queries; recent form is not complete season standings. Reports disclose cache
age, missing scores, and incomplete data. There are no member-triggered live
provider calls, refreshes, new API keys, or extra provider quota usage.
Existing bot refresh jobs own freshness. These caches are also used by public
website features; this tier sells convenience, not exclusive underlying data.
Confirm API-Sports display rights before advertising/launching.

### Prepaid offers (current)

The owner replaced automatic renewal with one-time prepaid terms. All eight
offers were created under the existing ALL-STAR/HIGHROLLER products (formerly
Gold/Platinum) and read back to
verify the seller, product, upfront price, expiration, hidden visibility, zero
stock, and disabled unlimited stock. No automatic renewal applies.

| Term | Exact access | Discount | ALL-STAR upfront USD | ALL-STAR plan | HIGHROLLER upfront USD | HIGHROLLER plan |
| --- | --- | --- | --- | --- | --- | --- |
| 1 month | 30 days | 0% | 9.99 | `plan_pkIXO8mx8lOvb` | 29.99 | `plan_10PuOcOt9rHNL` |
| 3 months | 90 days | 5% | 28.47 | `plan_HIqBGKDODgWRI` | 85.47 | `plan_8nWXoogPnIovE` |
| 6 months | 180 days | 10% | 53.95 | `plan_McwH52818Zpyi` | 161.95 | `plan_IFDLF4SdPxcQh` |
| 12 months | 365 days | 15% | 101.90 | `plan_jfOCNP5Ow8Q8g` | 305.90 | `plan_XU4sWniXTjODJ` |

Discounts apply to base price times the term length, rounded once to cents.
These are fixed-day passes, not calendar-month expiration. Only these eight
plan IDs belong in the current paid allowlist. The earlier recurring plans
below remain hidden/zero-stock and are no longer allowlisted; do not publish
them.

On October 3 the owner consolidated to two tier roles. ALL-STAR product
`prod_0Bi4ERPCfSWz1` now has a free seven-day one-time trial
`plan_ejj9LwTfrJp5z` alongside the four paid passes. The trial has no automatic
charge or conversion and never belongs in `WHOP_PAID_PLAN_IDS`. HIGHROLLER
product `prod_6Hh9VAzQnzNiE` remains paid-only. ALL-STAR trial members receive
the same tier role but cannot submit vault tickets; payment verification, not
the role, enforces that restriction. Retire the old ROOKIE Discord configuration
without deleting shared access or changing existing tier mappings. Verify the
ALL-STAR role ID configuration and trial-to-paid overlap before launch.
Product-filtered API listings verified ALL-STAR is attached to Discord
experience `exp_CJFzS7gTGLLsj2` and HIGHROLLER to
`exp_xiSK1tNQP20bvc`; both experiences are private. The experience detail
response's `products` array was empty even for mapped apps, so use the
product-filtered listing to verify attachments. The legacy ROOKIE app was
renamed `Retired ROOKIE` and kept private; its Discord role was not deleted.
The original separate trial and recurring variants are hidden, zero-stock,
with unlimited stock disabled. Nothing was published by this consolidation.

Apply `supabase/migrations/20261003020000_whop_prepaid_access.sql` after the
membership migration. It permits a verified paid snapshot with Whop's
`completed` status to qualify through its finite paid-through date. For that
status the bot also verifies that the matching seller's plan is `one_time` and
has a positive expiration duration. Missing period dates, payment evidence, or
verified identity still deny access; no lifetime access is inferred. Test
actual prepaid membership dates/status and Whop role expiration before launch.
Production polling was enabled on the server and successfully returned zero
memberships. Local sync remains disabled. Checkout remains closed; successful
paid production eligibility, expiry, refund, and trial-to-paid overlap are
still unverified.

### Original draft offers (superseded for paid access)

Created draft offers: Free Trial (`plan_i9kjEGeSzcuOV`, free seven-day
expiration without renewal), Gold (`plan_rAvIzb0XD2Jdz`, USD 9.99 every
30 days), and Platinum (`plan_pvonMenMO9YDa`, USD 29.99 every 30 days).
Each has its own product for tier-specific access configuration. Products and
plans are hidden, plan stock is zero, and unlimited stock is disabled. Do not
open availability until launch gates pass. Only Gold and Platinum belong in
`WHOP_PAID_PLAN_IDS`; the free plan does not qualify for vault submissions.

Whop handles checkout/subscriptions; this bot owns vault authorization and can
optionally own a dedicated Discord paid role. Checkout on the website remains
closed. Do not enable payment collection until Whop has approved the accurately
described sports-analysis/picks service, including member-ticket tracking, and
provided its complete fee schedule.

Apply `supabase/migrations/20261003010000_whop_membership_access.sql` after the
vault migration. This creates private membership snapshots and an audit of
changes, plus server-only eligibility functions. No browser/anonymous account
can write payment evidence, Discord identities, or grant itself access.

Configure these server-only settings (never put them in Vite/browser variables):

- `WHOP_MEMBERSHIP_SYNC_ENABLED=1` to enable API synchronization; default is off.
- `WHOP_API_KEY`: account-scoped key with permission to read memberships,
  payments, and buyer social-account identities. Confirm required scopes in
  Whop's dashboard; incomplete responses fail closed.
- `WHOP_ACCOUNT_ID`: your `biz_...` seller account ID.
- `WHOP_PAID_PLAN_IDS`: comma-separated approved `plan_...` paid plans. Do not
  include free plans.
- `PAID_MEMBER_ROLE_ID`: optional dedicated paid role. Configure `GUILD_ID`,
  enable Members Intent, give the bot Manage Roles, and place its role above
  this role. Do not reuse operator/official/administrator roles.

API contract: `https://api.whop.com/api/v1`, pinned with
`Api-Version-Date: 2026-09-29`, using the current membership `account.id`,
`user_id`, `plan_id`, `current_period_start/end`, `updated_at`, and
`cancel_at_period_end` fields. User identities come from `social_accounts`
entries with platform `discord`, a numeric `external_id`, and `verified=true`;
missing, unverified, or multiple distinct Discord identities do not qualify.
API/database timestamp readers normalize fractional seconds before parsing,
including PostgreSQL timestamps with trimmed trailing zeros, for Python 3.10
deployment compatibility.
Members must connect their own Discord account inside Whop. No typed username,
email match, client metadata, or Discord role is accepted as identity/payment
proof. Verify the actual account's API responses before launch.

The bot paginates the seller's memberships every five minutes and reads payments
for approved plans. Paid eligibility requires an active, unexpired period and a
positive successful current-period payment for the same seller, membership,
and plan. Trials, zero-cost memberships, past-due states, any refunded amount,
automatic refunds, dispute alerts, and missing period/payment evidence do not
qualify. Cancellation at period end preserves eligibility through the paid
period. Timestamp comparisons use a five-minute boundary tolerance for payment
creation/collection; older successful payments cannot satisfy a later cycle.
One-time indefinite purchases are not supported; expiring prepaid purchases
are supported by the prepaid-access migration described above.

This first integration uses **API polling, not a public webhook receiver**.
Changes normally propagate on the next five-minute pass. Snapshots older than
15 minutes cannot authorize new tickets. If synchronization fails, it logs
`whop_membership_reconciliation_failed` and does not run mass role removal.
Successful role synchronization grants/removes only the dedicated paid role,
and retries Discord failures on the next pass. Configure the vault channel so
@everyone cannot Send Messages and the paid role can; inspect other role
overrides for unintended posting grants. The bot still checks private paid
eligibility independently, before downloading a photo, again before saving,
and at confirmation. Moderators do not get a payment bypass for new tickets.
Already-confirmed tickets remain eligible for settlement after membership ends.

Choose one owner for paid-role automation. If this bot owns the role, do not
also configure Whop's Discord app to manage that same role. An expired or stale
role does not authorize vault submission. If Members Intent, Manage Roles,
hierarchy, or configured role safety checks fail, the bot logs the error.

Members can use `/membership_status` for an ephemeral eligibility check without
exposing billing details. No Whop secrets, payment amount, original receipt, or
buyer email are published to Discord.

Before launch, test a paid member, free/trial member, cancellation with remaining
paid time, expiry, failed renewal, refund, dispute, missing Discord link, API
failure, role hierarchy failure, and bot restart against your actual Whop
account. Local tests mock API responses; they do not prove live scopes or
account approval. Signed webhooks, website Whop OAuth/account linking, embedded
checkout, and instant refund/dispute revocation are follow-up work, not part of
this polling release.
