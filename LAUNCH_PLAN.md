# Playmaker Sports Analytics Launch Plan

This document is the launch source of truth for Playmaker Picks, operated by
Playmaker Sports Analytics, LLC. It is a planning document, not legal or tax
advice.

## 1. Decisions Already Made

- Legal entity: Playmaker Sports Analytics, LLC.
- Public community name: Playmaker Picks.
- Domain: `playmakersportsanalytics.com`.
- Ownership: single owner; revenue remains in the business account until the
  owner authorizes a business expense or distribution.
- Product: sports analysis and informational plays. The business does not
  accept, place, transmit, or hold wagers.
- Hosting: AWS Amplify hosts the website; the Discord bot continues running on
  the private Proxmox host.
- Repository: private monorepo. The website will live under `web/`, and Amplify
  will publish only the compiled website artifact.
- Data: Supabase remains the system of record for plays and becomes the system
  of record for membership entitlements.
- Promotions: only company-funded, free-to-enter prizes at launch. No
  member-funded cash pools.

## 2. Launch Gates

Do not accept payment until every Gate A item is complete. Do not automate
Discord access until every Gate B item is complete.

### Gate A: Business and Provider Approval

- [ ] LLC formation is accepted and formation records are stored securely.
- [ ] EIN and dedicated business checking account are active.
- [ ] Basic bookkeeping categories are established for revenue, processing
  fees, refunds, chargebacks, advertising, contractors, software, prizes,
  taxes, and owner distributions.
- [ ] A qualified professional reviews the terms, privacy notice, refund policy,
  responsible-play language, promotions rules, and applicable state
  requirements.
- [ ] The selected payment provider gives written approval for paid sports
  analysis and informational picks.
- [ ] The complete provider fee schedule is recorded, including platform,
  processing, payout, dispute, refund, and customer-facing fees.
- [ ] The provider confirms its webhook events, Discord linking support, data
  export options, cancellation behavior, and trial-abuse controls.

### Gate B: Technical Readiness

- [ ] Production and staging environments use separate credentials.
- [ ] Website authentication and Whop-managed Discord account linking are tested.
- [ ] Whop API polling and verified paid identity succeed for a real production purchase.
- [ ] Subscription state is stored independently from Discord roles.
- [ ] Role assignment, expiration, refund, chargeback, cancellation, and manual
  override flows pass automated tests.
- [ ] A scheduled reconciliation job repairs missed webhook and role events.
- [ ] Administrators can inspect an entitlement audit trail without accessing
  payment credentials.
- [ ] Database backups, alerting, and recovery procedures are tested.

The current release uses five-minute Whop API polling, not webhooks. Signed
webhooks and website billing/account linking remain follow-up work. Whop owns
tier roles; the bot independently checks private payment evidence for vault
submissions. Successful empty production sync has been observed, but a positive
production paid-member test remains outstanding.

## 3. Initial Product

The owner selected these tiers, superseding earlier Starter/All Access pricing
and auto-renewing trial proposals:

| Plan | Base price (USD) | Duration |
| --- | ---: | --- |
| ALL-STAR trial option | $0 | Free seven-day ALL-STAR access; no automatic charge; no vault submissions |
| ALL-STAR | $9.99 | One-time 30-day paid pass |
| HIGHROLLER | $29.99 | One-time 30-day paid pass; no trial |

| Offer label | Exact days | Discount | ALL-STAR total (USD) | HIGHROLLER total (USD) |
| --- | ---: | ---: | ---: | ---: |
| 1 month | 30 | 0% | 9.99 | 29.99 |
| 3 months | 90 | 5% | 28.47 | 85.47 |
| 6 months | 180 | 10% | 53.95 | 161.95 |
| 12 months | 365 | 15% | 101.90 | 305.90 |

Paid passes expire without automatic renewal. Labels refer to fixed-day access,
not calendar months. Discounts use multiples of the 30-day base price with one
final rounding to cents. Exact benefits and channels for each tier must be
confirmed before sale. No daily play count or profit is guaranteed. Trial-abuse
prevention is not yet implemented or verified.

Customer policy drafts are available at `/terms`, `/privacy`, and `/refunds`,
linked from the footer and membership page. Owner decisions: minimum age 21
(or higher local legal age); refund requests within seven days for access
failures or duplicate charges, not losing picks alone; applicable legal and
Whop remedies remain intact. Owner confirmed the support and legal inboxes are
working and monitored. Policies remain drafts pending professional review.
Finalize a data-retention schedule and deletion procedure before launch.
Do not open production availability or remove draft notices until Gate A and
the production access test pass.

## 4. Access and Discord Roles

The later tier split supersedes the original HIGHROLLER-only cache proposal:
paid ALL-STAR and HIGHROLLER can use cached reports; HIGHROLLER and approved
moderator roles can request today's data refresh with limits. Refresh remains
disabled pending budget migration, quota-reset confirmation, licensing, and
live validation. Five refreshes per person/day share twenty per API product/day,
with five-minute shared cooldown; eighty requests are allocated separately to
bot operations. Other dates remain cached. Trial access is still excluded.

HIGHROLLER's first implemented tool bundle was private cached `/matchup`,
`/teamstats` (recent form, not season standings), `/schedule`, and `/results`
commands. ALL-STAR and trials do not qualify. Tools require the new
HIGHROLLER-access migration and server deployment; they have not yet passed a
live paid production test. No direct API access or member-triggered live refresh
is offered. Public cache data is not claimed exclusive. Confirm data-display
licensing and deployment before advertising these tools as available.

Current tier roles:

- `Visitor`: joined Discord but has no website entitlement.
- `Free Member`: accepted server rules and linked an account.
- `ALL-STAR`: seven-day trial or current paid ALL-STAR access.
- `HIGHROLLER`: current paid HIGHROLLER access; no free trial.
- `ROOKIE`: retired from membership setup; do not grant it for new trials.

The trial and paid ALL-STAR offers share product `prod_0Bi4ERPCfSWz1`.
Trial variant `plan_ejj9LwTfrJp5z` is free, one-time, expires after seven days,
and is excluded from the paid vault allowlist. The old separate trial offer
remains hidden/zero-stock. Whop's existing ALL-STAR product-to-role mapping must
be verified for the new trial; do not create a second role owner. Trial-to-paid
overlap and expiration need live verification.
- `Founding Member`: time-limited complimentary entitlement for qualifying
  existing members.
- `Promotional Access`: time-limited prize or administrative grant.
- `PLAYMAKER`: approved capper; never inferred from a paid membership.
- `Administrator`: operational access; never inferred from ownership of another
  role.

Discord roles are a projection of database entitlements, not the authority for
billing status. Removing or manually adding a Discord role must not change a
customer's paid subscription.

## 5. Member Journey

1. A visitor inspects pricing, transparent results, policies, and the Discord
   community link. Checkout remains closed until the launch gates pass.
2. The visitor purchases a one-time pass through approved Whop hosted checkout,
   connects their own Discord account, and uses Claim Access.
3. Whop's Discord app assigns the configured tier role.
4. The bot polls Whop every five minutes and records verified payment, period,
   and Discord identity in a private audited ledger.
5. `/membership_status` reports private vault eligibility. Verified paying
   members may submit; trials and complimentary access do not qualify.
6. Expiry or refund denies new vault submissions. Snapshots older than 15
   minutes fail closed. Whop independently manages tier-role expiration.
7. Already-confirmed vault tickets can settle after access expires. A new
   purchase is required for renewed prepaid access.

## 6. Website Scope

Build the usable service first, not a marketing-only landing page.

### Public

- Home dashboard with current verified performance and recent settled results.
- Plans and feature comparison.
- Full verified results with clear filters and methodology.
- How membership and Discord access work.
- Responsible-play statement and age requirements.
- Terms of service, privacy notice, refund policy, and contact details.
- Company identity: "Playmaker Picks is operated by Playmaker Sports Analytics,
  LLC."

### Authenticated Member

- Discord connection status.
- Current plan, entitlement source, and access expiration.
- Checkout or upgrade link supplied by the approved provider.
- Billing-management link supplied by the provider.
- Account and privacy controls.
- Support request path.

### Administrator

- Member search by Discord ID, username, provider customer ID, or email.
- Entitlement status and immutable event history.
- Time-limited complimentary access with reason and issuing administrator.
- Reconciliation status and actionable failures.
- Read-only subscription summaries; no card data is stored or displayed.

## 7. Technical Architecture

### Public Website

- Create `web/` as a React and TypeScript application built with Vite.
- Configure Amplify with `web/` as the application root.
- Publish only `web/dist/`.
- Use responsive, accessible components and automated browser checks at desktop
  and mobile widths.

### Future Webhook Backend (Not Implemented in the Polling Release)

- Receive payment webhooks in an AWS Lambda, Supabase Edge Function, or another
  server-only endpoint supported by the selected provider.
- Verify the raw request signature before parsing or processing an event.
- Store the provider event ID before applying a state transition so retries are
  safe.
- Place privileged membership operations behind a service role that is never
  available to browser code.
- Let the Proxmox bot consume entitlement state and perform Discord role work.

### Future Membership Table Proposal (Not the Current Whop Ledger)

Add membership tables through a new migration rather than changing the meaning
of `users.role`:

The current implementation uses private `whop_memberships` and
`whop_membership_audit` tables instead. The following is an earlier future
architecture proposal, not deployed schema or a launch-completion claim.

- `membership_plans`: internal plan key, provider price ID, rank, and active
  status.
- `customer_accounts`: application user, Discord ID, provider customer ID, and
  account-link status.
- `subscriptions`: provider subscription ID, plan, state, paid-through date,
  cancel-at-period-end, and timestamps.
- `entitlements`: account, plan, source, start, expiration, revocation reason,
  and optional subscription reference.
- `provider_events`: unique provider event ID, type, received time, processing
  state, and sanitized failure detail.
- `entitlement_events`: append-only audit history for grants, changes,
  revocations, reconciliations, and administrator actions.
- `discord_role_sync`: desired role, observed role, last attempt, retry count,
  and last error.

Enable row-level security before exposing any table to the website. Members may
read only their own safe account and entitlement fields. Provider payloads,
internal notes, service credentials, and other members' data remain private.

## 8. Security Rules

- Keep the repository private and require multifactor authentication for GitHub,
  AWS, Supabase, Discord, the registrar, email, and the payment provider.
- Keep bot tokens, service-role keys, payment secrets, and webhook secrets out
  of Git and out of the browser bundle.
- Treat every `VITE_*` value as public.
- Use separate least-privilege credentials for the website, webhook processor,
  and bot.
- Add `web/.env.local`, Node build output, coverage output, and Amplify local
  artifacts to `.gitignore` when the website is scaffolded.
- Sanitize logs; never record full webhook payloads, access tokens, payment
  methods, or unnecessary personal data.
- Rate-limit account linking, verification, complimentary grants, and webhook
  failure retries.
- Rotate any credential that enters Git history or a frontend build.

## 9. Promotions and Prizes

Permitted launch prizes include a seven-day All Access pass, a 30-day upgrade,
a subscription extension, merchandise, or a company-funded fixed prize.

- Random promotions must have a free entry method and published official rules.
- A purchase must not improve the chance of winning.
- Access prizes have no cash value, are nontransferable, and expire
  automatically.
- Existing subscribers receive an extension instead of overlapping access.
- Record the promotion, eligible entries, selection event, winner response, and
  any redraw in an audit trail.
- Do not operate member-funded cash pools or let the bot custody entry fees or
  prize balances.

## 10. Capper Governance

- Begin with no more than three approved cappers.
- Require a documented trial of at least 30 days and 75-100 graded plays.
- Publish unit limits, grading rules, accepted odds sources, and correction
  procedures.
- Timestamp every play with the available line and odds.
- Never delete losses; corrections create an audit event.
- Prohibit claims such as "lock," "guaranteed winner," and "risk-free."
- Keep capper status and compensation separate from membership roles.
- Use written contractor terms before paying a capper. Compensation should come
  from a defined, capped business budget rather than a share of customer wagers
  or winnings.

## 11. Delivery Phases

### Phase 0: Foundation

- Complete Gate A.
- Establish domain security, business email, and records storage.
- Select the provider and freeze initial plan names, prices, and cancellation
  terms.
- Create approved policy copy and brand assets.

Exit condition: the business is permitted and operationally ready to accept
subscriptions, but checkout remains disabled.

### Phase 1: Public Website

- Scaffold `web/` and configure linting, tests, and production builds.
- Build the public dashboard, results, plans, policies, and contact experience.
- Add analytics that avoid collecting unnecessary personal data.
- Configure Amplify preview deployments and the production domain.

Exit condition: the public site is useful without payment and passes desktop,
mobile, accessibility, and production-build checks.

### Phase 2: Identity and Membership

- Add website authentication and Discord OAuth linking.
- Apply the membership database migration and row-level security.
- Integrate hosted checkout and the provider billing portal.
- Implement signed, idempotent webhooks and entitlement transitions.
- Add account and administrator membership views.

Exit condition: test purchases produce correct, auditable entitlements without
manual database edits.

### Phase 3: Discord Automation

- Add plan and onboarding role configuration to the bot environment.
- Implement entitlement-to-role mapping as a dedicated service.
- Process immediate role-sync requests after entitlement changes.
- Run scheduled full reconciliation and alert on repeated failures.
- Add administrator diagnostics and manual retry controls.

Exit condition: purchase, renewal, upgrade, downgrade, cancellation, expiration,
refund, chargeback, complimentary access, and Discord reconnect scenarios pass
integration tests.

### Phase 4: Controlled Pilot

- Grant existing qualifying members a clearly dated Founding Member entitlement.
- Invite 25-50 paid pilot members.
- Review support demand, access failures, refunds, disputes, conversion, and
  churn every week.
- Fix operational failures before purchasing broad advertising.

Exit condition: four stable weeks with no unresolved access-control incidents,
manageable support volume, and acceptable provider risk metrics.

### Phase 5: Growth

- Add annual plans only when retention data supports them.
- Test Premium with member interviews and a limited cohort before public launch.
- Introduce referrals and free-entry promotions with approved rules.
- Increase advertising gradually and measure retained subscribers rather than
  raw Discord joins.

## 12. Launch Metrics

Track these separately for free, trial, promotional, founding, and paid users:

- Website visitor to checkout conversion.
- Checkout completion rate.
- Trial to paid conversion.
- Monthly paid churn and cancellation reason.
- Gross and net monthly recurring revenue.
- Refund and chargeback rates.
- Payment-to-Discord-access latency.
- Failed role syncs and time to resolution.
- Support requests per 100 paid members.
- Starter-to-All-Access upgrades and downgrades.

Suggested pilot targets are hypotheses, not guarantees: trial conversion above
30%, monthly paid churn below 10%, chargebacks below 1%, and at least 99% of
successful payments receiving correct Discord access within five minutes.

## 13. Immediate Work Queue

1. Obtain written provider approval and the complete fee schedule.
2. Finalize the initial prices and customer-facing cancellation/refund terms.
3. Have the legal and promotions documents reviewed for the launch locations.
4. Secure the domain, business email, and all administrative accounts with MFA.
5. Scaffold the `web/` application and Amplify build configuration.
6. Build the public results and plans experience using existing play data.
7. Design and migrate the membership schema with row-level security.
8. Add authentication, Discord linking, hosted checkout, and billing management.
9. Implement webhooks, entitlements, bot role synchronization, and audit tools.
10. Complete Gate B and run the controlled pilot.
