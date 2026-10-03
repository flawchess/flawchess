---
id: SEED-183
status: promoted
promoted_to: Phase 229
promoted: 2026-10-03
planted: 2026-10-03
planted_during: no open milestone (after v2.21), Phase 228 (SEED-175 settings page) in discuss; /gsd-explore
trigger_when: after Phase 228 (settings page), or the next growth/analytics work
scope: medium (one phase: identify wiring + per-page event inventory + Privacy copy + CLAUDE.md rule)
---

# SEED-183: Umami user identification + feature-event instrumentation

## Why This Matters

Umami knows pages but not people, and the prod DB knows people but not UI behavior.
Three questions are currently unanswerable:

1. **Which features go unused.** UI-only interactions (tabs, toggles, filters, board
   tools, popovers, settings) leave no server trace, and today only 5 custom events exist
   (`signup-cta`, `import-cta`, PWA funnel).
2. **Behavior → retention.** "Do users who touch feature X come back more?" needs Umami
   behavior joined to `users` / `user_activity` in the prod DB.
3. **Individual user journeys** (support, UX research).

Context: the 2026-10-03 growth report showed audience-matched acquisition (Noël Studer
newsletter → `/train`) behaves very differently from Reddit traffic. Per-user stitching
would let us see which features that cohort actually used before retaining or churning.

## Decisions (from /gsd-explore 2026-10-03)

### 1. Identity

- Call `umami.identify(String(users.id))` for **every authenticated session, guests
  included**. Guest promotion (`app/services/guest_service.py:69` / `:136`) keeps the same
  `users` row, so guest → registered → retention stitches into one `distinct_id`.
  Pre-guest landing pageviews stay anonymous.
- **Raw `users.id`**, chosen over an opaque `analytics_id` column or HMAC: Umami is
  self-hosted (analytics.flawchess.com), so data stays on our infra, and raw id gives the
  simplest join to the prod DB.
- Keep the existing `account: guest|registered` session tag (`identifyAccountType` in
  `frontend/src/lib/analytics.ts`, call site `frontend/src/App.tsx:678`). Update the
  `window.umami.identify` typing to the `(distinctId, data)` signature.
- Verified 2026-10-03: the self-hosted Umami schema has `session.distinct_id` (v2.18+);
  0 of 1,941 app sessions in the last 30 days use it.

### 2. Feature events: inventory + convention (not auto-capture)

- One pass per page builds an inventory of UI-only interactions (~30-50).
- **Few event names with props** (e.g. `tab-switch` + `page`/`tab`) so the flat Umami
  events list doesn't sprawl into hundreds of near-zero rows.
- Add a `frontend/CLAUDE.md` rule so new features ship with their event.
- **Keep** the existing rule (`frontend/CLAUDE.md:43`): DB-known actions (signups,
  imports, analysis runs) are not duplicated as events. With identify they become
  joinable instead. Its wording needs a touch-up since it frames Umami as anonymous.
- Internal links use `trackEvent()` in `onClick`, never `data-umami-event` on a `<Link>`
  (full-reload downgrade, see `frontend/CLAUDE.md:42`).

### 3. Privacy copy (required, one sentence)

`frontend/src/pages/Privacy.tsx:58` says "No personal data is collected or shared", which
becomes false once sessions carry `users.id` (pseudonymous data is personal data under
GDPR). Replace with one sentence along the lines of: usage analytics (pages visited,
features used) are linked to your account ID for logged-in and guest accounts, stay on
our own servers, and are never shared with third parties. This also closes the
pre-existing undisclosed `user_activity` gap. Legitimate interest covers self-hosted
first-party analytics; the point is not publishing a false statement.

### 4. Supersedes the June identify rejection

The 2026-06-27 rejection of Umami identify in
`.planning/notes/active-engagement-time-tracking.md` (SEED-069) was about measuring
engagement minutes, which Umami can't do. That reasoning doesn't apply to feature usage.
Add a "superseded for usage analytics by SEED-183" pointer there when implementing.

## Open questions (UNVERIFIED, research before planning)

- **(a) Persistence:** does `umami.identify()` persist `distinct_id` (localStorage?) or
  must it be re-called on every page load? If it writes localStorage, an ePrivacy
  storage question arises on top of the Privacy copy.
- **(b) Logout / account switch:** what happens to `distinct_id` on logout or when a
  different user logs in on a shared browser? Needs a reset path so the next user isn't
  attributed to the previous id.

## When to Surface

**Trigger:** after Phase 228 (settings page), or the next growth/analytics work.

## Scope Estimate

**Medium**, one phase: identify wiring + logout reset (small), per-page event inventory
and wiring (bulk of the work), Privacy sentence, CLAUDE.md rule update.

## Breadcrumbs

- `frontend/src/lib/analytics.ts`: `trackEvent`, `identifyAccountType`, `umamiBeforeSend` scrub
- `frontend/src/App.tsx:678`: current identify call site
- `frontend/index.html`: tracker tag (`data-domains`, `data-exclude-hash`, `data-before-send`)
- `frontend/CLAUDE.md:30-43`: Umami event conventions
- `frontend/src/pages/Privacy.tsx:58`: analytics disclosure
- `app/services/guest_service.py:69,136`: guest promotion keeps the user row
- `.planning/notes/active-engagement-time-tracking.md`, SEED-069 (closed): prior rejection
- `reports/growth/growth-recommendations-2026-10-03.md`: attribution/retention context
- MCP `flawchess-umami-db`: read-only Umami DB for verifying `distinct_id` after ship
