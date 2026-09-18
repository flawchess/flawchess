# Phase 224: Guest Activation — Welcome Removal & Guest Train (SEED-169) - Research

**Researched:** 2026-09-17
**Domain:** In-repo product change (React 19 + TS frontend, FastAPI/SQLAlchemy backend, Postgres analytics SQL). No new dependencies.
**Confidence:** HIGH (every claim below is a file read performed this session; no external package or API research was required)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from SEED-169 (locked 2026-09-17 in /gsd-explore, not re-opened)
- **S-1:** Drop the forced `/welcome` redirect in `Home.tsx`; delete `welcomeDismissal.ts`
  and the `welcome_dismissed` flag. `/welcome` stays routable, never forced.
- **S-2:** Train opens to guests as the full loop, not a demo. `_reject_guest` (all seven
  handlers in `app/routers/train.py`) and `TrainGuestGate.tsx` are removed.
- **S-3:** Guest score screen: the warm-up variant's reminder ask (`WARMUP_REMINDER_ASK_COPY`)
  is REPLACED by a sign-up ask naming the payoff (own blunders come back instead of warm-ups;
  streak and history carry over because promotion is in-place). No reminder slot, no QR/install
  block, no push subscription for guests. The nudge repeats every session.
- **S-4:** Buttons live in `TrainBotBubble`'s existing `actions` slot: **"Why?"**
  (`brand-outline`) + **"Sign up free"** (primary, existing `logoutForPromotion()` +
  `/login?tab=register` flow). Done stays alone in the row below, unchanged.
- **S-5:** `/welcome` rewritten: four deltas only (automatic Stockfish analysis of imported
  games, Train from your own mistakes, use on any device, no 30-day inactivity purge), one
  "Sign up free" button, table dropped.
- **S-6:** Import page: the guest `Alert` (`import-guest-promo-info`/`-link`) becomes a
  `TrainBotBubble` hosted by `pickBot('friendly')`, shown on every guest visit, same button
  pair. First persona appearance outside a game/puzzle context, accepted.
- **S-7:** Two metrics, before and after, never combined: lever A = guest import-start rate
  (48%, 226/468) and Umami `/welcome` landings (390 of 1,051); lever B = guest promotion
  rate (`users.promoted_at IS NOT NULL` among guests created in the window) and guest Train
  sessions completed. Umami `signup-cta` gains `data-umami-event-source="train-score"`,
  keeps `import-promo`.

#### Zero-game Train entry (discussed)
- **D-01:** **Everyone** can open Train with zero games, not only guests. Add `/train` to
  `IMPORT_EXEMPT_ROUTES` in `frontend/src/App.tsx` and remove the `ImportRequiredRoute`
  wrapper from the `/train/*` route. Registered 0-game accounts get the same warm-up loop.
  Rationale: compose already serves herrings + sharp filler with zero games and no rating
  input (`compose_and_materialize_session` widens eligibility with
  `sharp_filler_available()`); one rule, no `is_guest` branch in nav or route guards.
  — **Reversibility:** reversible — two-line revert in `App.tsx`.
- **D-02:** **Discovery = the unlocked nav item only.** No Train pitch or third button in the
  Import bubble; the Import surface stays a lever A page with the sign-up ask. Whether the
  Phase 222 "reworked Train" red dot (`showTrainDot`, currently gated on `navUnlocked`) is
  decoupled so it also shows for 0-game accounts is Claude's discretion (see below).
- **D-03:** **Games-less copy branches on two orthogonal flags**, not on `is_guest` alone:
  `hasGames` (from `useUserProfile().data` game counts, the `Home.tsx` pattern) selects
  "import your games" wording for ANY 0-game account; `isGuest` appends the sign-up ask. A
  registered 0-game user reads import-only copy; a guest reads import, then sign up, in that
  order; users with games keep today's strings verbatim. Applies to every string that
  currently presumes analysis is running: the start-screen warm-up banner in
  `TrainStartScreen.tsx` ("We're analyzing your games to find your blunders"), `INTRO_WELCOME`
  ("puzzles created from your own games"), `INTRO_WARMUP`, `WARMUP_TAIL`, and the
  `scoreBubbleCopy` warm-up opener ("Once your games are analyzed, your own mistakes take
  over"). `is_guest` MUST come from `useUserProfile().data`, never `useAuth().user`
  (FLAWCHESS-64).

#### Bot voice for the sign-up ask (discussed)
- **D-04:** **Persona-neutral copy**, like today's `scoreBubbleCopy` lines: one sign-up ask
  string per surface (score-screen warm-up, Import). The avatar and name carry the persona;
  223 D-08's per-persona `Record<PersonaId, string>` shape is NOT used here so conversion
  copy stays a single tunable sentence.
- **D-05:** **"Why?" navigates to `/welcome`** (no inline dialog). The rewritten `/welcome`
  gets a plain Back affordance (browser back or a small link) so a guest can return to Train
  or Import.
- **D-06:** **Import bubble payoff is import-specific**: automatic Stockfish analysis of
  imported games + use on any device (today's alert message in bot voice). The score-screen
  ask names blunders-come-back + streak/history carry over. The two surfaces do not share a
  sentence.
- **D-07:** **Post-sign-up landing = existing flow (`/`)**: Home routes to `/library/import`
  or the games library. No return-to parameter is threaded through `promote_intent` /
  `LoginForm` / `googleAuth.ts`. Train state is intact when the user comes back to it.

#### Purged-guest Train state (discussed)
- **D-08:** **The 30-day purge wipes the guest's Train rows with the games**:
  `guest_cleanup_service.purge_guest` also deletes that guest's `drill_sessions`,
  `drill_solves` and `train_settings`. Honest to the `/welcome` "no 30-day inactivity purge"
  delta; the streak has drained to 0 by then anyway (shield cap 7). Supersedes the
  "preserved by design" comment at `guest_cleanup_service.py` ~108 and the D-04 reading in
  `test_purge_guest_cascades_drill_rows` for guests only (registered users' D-04 preservation
  is untouched). Comments and the test must state the new rule explicitly (ROADMAP SC 8).
  — **Reversibility:** reversible — a delete block; purged data is gone either way.
- **D-09:** **No new abuse guard.** The guest-creation limiter (5/hour/IP,
  Cf-Connecting-Ip aware, `app/core/ip_rate_limiter.py`) plus the one-session-per-day compose
  rule is the backstop for the cross-user herring pool. Research verifies that
  `POST /auth/guest` still runs through `guest_create_limiter` with the Cloudflare header
  path; no guest-specific Train ceiling or filler-only mode.

#### Metric recording (discussed)
- **D-10:** **Baseline note + Activity dashboard split.** (a) A dated markdown under
  `reports/growth/` holding the exact prod SQL and the pre-merge numbers for both levers
  (lever A: guest import-start rate and `/welcome` landings; lever B: guest promotion rate
  and guest Train sessions completed). (b) The Activity dashboard's Train card
  (`app/services/activity_queries.py::fetch_train`, `frontend/src/pages/activity/`) gains a
  guest-cohort row: sessions completed while a guest, and promotions in the window, so the
  "after" reading needs no hand-run SQL.
- **D-11:** **"Guest Train session completed"** = `drill_sessions.status = 'completed'` with
  `session_date < coalesce(users.promoted_at, 'infinity')` for users in the existing
  `_GUEST_COHORT` (`is_guest OR promoted_at IS NOT NULL`) created in the window. A promoted
  user's later sessions count as registered.
- **D-12:** **Purged users are excluded from the guest Train row** with the same
  `games_purged_at IS NULL` predicate the funnel cards use, footnoted via the existing
  `fetch_purged_excluded` count. No retained lifetime counter on `users`.

### Claude's Discretion
- Whether `showTrainDot` is decoupled from `navUnlocked` for `/train` so 0-game accounts see
  the Phase 222 dot (D-02).
- `TrainBotBubble` `state` kind and persona stability for the Import bubble (re-pick per
  mount vs `useMemo` once, mirroring `TrainScoreScreen`'s `useMemo(() => pickBot('smart'), [])`).
- `/welcome` behaviour for a registered visitor (render, or redirect to `/library`).
- Whether `useTrainProgress` in `App.tsx` (nav badge) is enabled for guests now that the 403
  reason is gone; `useReminderResurfaceRedirect` and `useDevicePushResync` stay guest-gated
  (no push for guests, S-3).
- Exact wording of every new string within S-3/D-03/D-04/D-06 (no em-dashes; the
  `HumanLikeOpponentsCard` accuracy rule from 223 D-08 holds for any bot-voiced line).
- Which frontend tests are deleted vs rewritten: `Train.guestGate.test.tsx` (delete; it also
  carries the known cross-test contamination flake), `Welcome.test.tsx` (rewrite), `Home.tsx`
  redirect coverage, Import guest-alert testids, `TrainScoreScreen.test.tsx` guest branch.

### Deferred Ideas (OUT OF SCOPE)
- Return-to-`/train` after sign-up from the score screen (D-07 rejected for now; revisit if
  promotion rate from `train-score` is high but Train retention after promotion is not).
- Import bubble pitching Train / a "Try Train" third button (D-02 rejected; keeps lever A and
  B surfaces separate for measurement).
- A guest-specific Train ceiling or filler-only mode (D-09 rejected unless the herring pool
  shows abuse).

**Also out of scope (ROADMAP):** push reminders for guests; any change to the registered-user
score bubble, reminder slot or QR block; a one-shot "demo session" variant; a new milestone or
roadmap regrouping.
</user_constraints>

<phase_requirements>
## Phase Requirements

No active `REQUIREMENTS.md` exists; IDs are minted at planning time (same pattern as Phases
204–223). The breakdown below is a **proposal** the planner may adopt verbatim; each row maps to a
ROADMAP success criterion (SC) or a CONTEXT decision, and each has a test row in
[Validation Architecture](#validation-architecture).

| Proposed ID | Description | Source | Research support |
|---|---|---|---|
| GUESTACT-01 | No code path forces `/welcome`; `welcomeDismissal.ts` and its flag deleted | SC 1 / S-1 | Finding: `Home.tsx:777-784` redirect + full importer list (Pitfall 4) |
| GUESTACT-02 | `/train` opens for any zero-game account (route + nav) | D-01 / D-02 | `App.tsx:160` `IMPORT_EXEMPT_ROUTES`, `:791` `ImportRequiredRoute`, `:970` route; Pitfall 6 (tests to invert) |
| GUESTACT-03 | `_reject_guest` removed from all seven handlers + module docstring | SC 2 / S-2 | Finding A (exact call-site table); Finding B (nothing else branches on `is_guest`) |
| GUESTACT-04 | A guest completes a full warm-up session; `drill_sessions` row + streak persist; weekday cadence on the next visit | SC 2 | Finding C (four legs of the zero-game compose path, incl. `sharp_filler_available()` streak accrual) |
| GUESTACT-05 | Guest score screen: sign-up ask in the bubble `actions`; no reminder ask / QR / push; registered screen byte-identical | SC 3 / S-3 / S-4 | Pattern 3 (`actions` is `undefined` today), Pitfall 1 (2 branches headroom), Pitfall 3 |
| GUESTACT-06 | Promotion in place preserves `drill_sessions`/`train_settings`/streak/solves | SC 4 | Finding F (verbatim UPDATE + the test to extend) |
| GUESTACT-07 | Import page shows the friendly-bot bubble on every guest visit; old `Alert` + testids gone | SC 5 / S-6 | Pitfall 1 (ImportPage has zero headroom → extract), Pattern 4 (memoise `pickBot('friendly')`) |
| GUESTACT-08 | `/welcome` is the four-delta page with one "Sign up free" + a Back affordance | SC 6 / S-5 / D-05 | `Welcome.tsx` full read; Pitfall 8 (route is inside `ProtectedLayout`) |
| GUESTACT-09 | Games-less copy branch on `hasGames` × `isGuest` across all five strings, import before sign up | SC 7 / D-03 | Finding E (all five sites quoted verbatim + the recommended pure-function shape) |
| GUESTACT-10 | Guest purge deletes `drill_sessions`/`drill_solves`/`train_settings`; comments + test state the rule | SC 8 / D-08 | Finding G (FK table, the two deletes, the exact comment to supersede, the test to rewrite) |
| GUESTACT-11 | `signup-cta` carries `train-score` and `import-promo` sources | SC 9 / S-7 | Existing source inventory (9 call sites) + the `<Link>` umami prohibition |
| GUESTACT-12 | Baseline note under `reports/growth/` with committed SQL and pre-merge numbers | SC 10 / D-10(a) | Finding I (the growth report commits no SQL; `fetch_funnel` predicate to reuse) |
| GUESTACT-13 | Activity Train card gains the guest-cohort row (D-11 definition, D-12 exclusion) | D-10(b)/D-11/D-12 | Finding J (extension points, draft SQL, `fake_payload` coupling, chart-harness warning) |
| GUESTACT-14 | Guest-creation limiter confirmed as the backstop; no new guard | D-09 | Finding H (four verified links, incl. uvicorn's leftmost-XFF behaviour) |
| GUESTACT-15 | *(discovered, needs confirmation)* No reminder toggle / QR block renders for a guest in `TrainScheduleSettings` | Open Question 1 | Pitfall 2 |
| GUESTACT-16 | Stale gate-dependent docstrings updated (`train_reminder_repository.py:43-46`) | Runtime State Inventory | Runtime State Inventory, "Code invariants written on the gate" |
</phase_requirements>

## Summary

This phase is 100% in-repo surgery on code that already exists. There is no library question, no
new package, and no external API: the only "research" that matters is (a) exactly which call
sites hold the guest gate, (b) which invariants elsewhere in the codebase were written ON TOP of
that gate and go stale the moment it is removed, and (c) the complexity/lint headroom in the four
files the phase must edit. All three are answered below with file:line evidence.

The good news: the compose path is genuinely guest-safe and rating-free. `compose_and_materialize_session`
has no `is_guest` branch, the red-herring query is global (never filtered on the caller's games),
and the sharp-filler pool is a committed CC0 file. A zero-game account composes a full warm-up
session today; only `_reject_guest` stops it. Promotion is an in-place `UPDATE users`, so every
`drill_sessions`/`train_settings`/`drill_solves` row survives registration untouched — the sign-up
copy may promise this truthfully.

The bad news, and the three findings the planner most needs: **(1)** the Train settings card on the
landing screen (`TrainScheduleSettings`, which guests will now reach) contains a reminder toggle and
a QR/install block, and the reminder fan-out query hard-filters `User.is_guest.is_(False)` — a guest
who flips that switch gets a promise the backend provably never keeps. That is the exact "silent
lie" Phase 202 D-06 exists to rule out, and it is *not* covered by the CONTEXT's score-screen-only
S-3. **(2)** CONTEXT's `code_context` claim that "`_pool_state` … with filler always available the
empty landing state is unreachable" is only half right: `_material_flags` feeds `_pool_state` from
`pool_entry_stmt(user_id)` — the user's OWN blunders — not the global herring pool, so every
0-game account gets `pool_state = "no_material"`. It happens not to matter (composition returns a
real session, so the landing resolves to `warmup`, not `empty`), but the planner must not build on
the stated reason. **(3)** `ImportPage` sits at complexity **29 with its baseline at exactly 29**
(zero headroom) and `TrainScoreScreen` at **13 against the un-baselined cap of 15** (two branches of
headroom). Both new bubbles must be extracted into their own components, not inlined.

**Primary recommendation:** Plan this as five sequenced slices — (A) lever A: Home redirect +
`welcomeDismissal` deletion + `/welcome` rewrite; (B) backend gate removal + test inversion +
guest-cleanup D-08; (C) route/nav opening for zero-game accounts (D-01) and the games-less copy
branch (D-03); (D) the two sign-up bubbles, each as a NEW extracted component so neither host file
gains a branch; (E) metrics (baseline note + Activity guest row). Slice B is the only one with a
migration-free backend footprint; slices A and E are independently shippable.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Guest gate removal (`_reject_guest`) | API / Backend | — | Authorization lives at the router, never inferred client-side (Phase 189 Pitfall 7) |
| Zero-game Train access | Frontend Server (SPA route guard) | API | `ImportRequiredRoute`/`IMPORT_EXEMPT_ROUTES` are pure client routing; the API never gated on game count |
| Sign-up ask copy + buttons | Browser / Client | — | Pure presentational; `logoutForPromotion()` + hard nav already exists |
| Guest Train-row purge (D-08) | Database / Storage (via service) | — | FK policy + explicit deletes inside the existing purge transaction |
| Guest-creation abuse backstop | API / Backend (+ CDN) | CDN / Caddy | In-process limiter keyed on the Cloudflare-resolved client IP |
| Lever A/B baselines | Database / Storage (prod SQL) + external (Umami) | — | `users`/`drill_sessions` reachable via the read-only MCP; Umami is a separate DB (see Environment Availability) |
| Activity guest-cohort row | API / Backend (raw SQL) | Browser (render.js table) | `activity_queries.py` owns every dashboard query as a raw string |

## Standard Stack

No new libraries. Everything this phase needs already ships in the repo.

### Core (already installed — reuse, do not add)
| Library / module | Version | Purpose | Why standard |
|---|---|---|---|
| React | 19 | UI | Existing stack [VERIFIED: CLAUDE.md "Frontend: React 19 + TypeScript + Vite 8"] |
| FastAPI | 0.115.x | Router layer | Existing stack [VERIFIED: CLAUDE.md "Backend: FastAPI 0.115.x, Python 3.14"] |
| SQLAlchemy 2.x async | — | ORM + raw `text()` analytics SQL | Existing stack |
| uvicorn | 0.52.4 | ASGI server (proxy-header handling matters for D-09) | [VERIFIED: `.venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"` → `0.52.4`] |

### Supporting (in-repo modules this phase composes)
| Module | Path | Use |
|---|---|---|
| `TrainBotBubble` | `frontend/src/components/train/TrainBotBubble.tsx` | Hosts both sign-up asks via its `actions` slot |
| `pickBot(temperament)` | `frontend/src/lib/trainBotCopy.ts:164` | Persona selection; pools verified below |
| `logoutForPromotion()` | `frontend/src/hooks/useAuth.ts:170` | The promotion handoff |
| `trackEvent` / `data-umami-event` | `frontend/src/lib/analytics.ts:24` | Umami attribution |
| `guest_create_limiter` | `app/core/ip_rate_limiter.py` | D-09 backstop |
| `activity_queries` | `app/services/activity_queries.py` | D-10..D-12 metric home |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Inline guest branch in `ImportPage` | Extracted `<ImportGuestPromoBubble />` | REQUIRED, not optional: `ImportPage` is at its complexity baseline exactly (see Pitfall 1) |
| Inline guest branch in `TrainScoreScreen` | Extracted actions component + a pure copy function in `trainBotCopy.ts` | Strongly recommended: 2 branches of headroom left before the un-baselined cap of 15 |
| Two independent button pairs | One shared `<SignupAskActions source={...} />` | Recommended: identical markup, identical umami contract, one place to keep `brand-outline` + `default` correct |

**Installation:** none. No `npm install`, no `uv add`.

**Version verification:** not applicable — no package is added or upgraded by this phase.

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** No `npm install`, `uv add`, `pip install`
or lockfile change is required by any decision in CONTEXT.md or the ROADMAP. If planning discovers a
need for one (it should not), run the legitimacy gate before adding it.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Project Constraints (from CLAUDE.md / frontend/CLAUDE.md)

Extracted directives the plan must comply with. These have the same authority as locked decisions.

| Constraint | Source | Impact on this phase |
|---|---|---|
| No magic numbers — named constants | CLAUDE.md Coding Guidelines | New copy strings must be module-level named constants, matching `WARMUP_REMINDER_ASK_COPY`'s shape |
| Never bare `str` for a fixed set — `Literal[...]` | CLAUDE.md | Any new backend param/response field naming a cohort or source must be `Literal` |
| `uv run ty check app/ tests/ scripts/` zero errors | CLAUDE.md | Gate for slices B and E |
| Explicit return type annotations on all functions | CLAUDE.md | New backend query functions |
| Sentry `capture_exception()` in non-trivial `except` in services/routers | CLAUDE.md | The removed `_reject_guest` sits *before* the existing try/except blocks; do not disturb them |
| Never embed variables in Sentry error messages | CLAUDE.md | New guest-cleanup code uses `set_context`, never f-strings |
| Function size: nesting depth hard 4, logic LOC hard 200 | CLAUDE.md + `scripts/check_function_size.py` | `guest_cleanup_service._purge_guest` gains two deletes — currently well under |
| Comment bug fixes at the fix site | CLAUDE.md | D-08's supersession comment is mandatory (ROADMAP SC 8) |
| Frontend `complexity` 15 / `max-depth` 4 / `max-statements` 100 at **error**; a NEW breach must be fixed, not baselined | frontend/CLAUDE.md | See Pitfall 1 — the binding constraint of this phase |
| `noUncheckedIndexedAccess` is on | frontend/CLAUDE.md | Narrow before indexing in any new copy array |
| Knip runs in CI — remove exports with the feature | frontend/CLAUDE.md + `.github/workflows/ci.yml:217` | Deleting `welcomeDismissal.ts` and `TrainGuestGate.tsx` must remove every import AND any now-dead sibling export |
| Minimum font size `text-sm` | frontend/CLAUDE.md | New bubble/`/welcome` copy |
| Primary = `variant="default"`, secondary = `variant="brand-outline"`; never hand-rolled button colors | frontend/CLAUDE.md | Matches S-4 exactly |
| `data-testid` on every interactive element, kebab-case, component-prefixed | frontend/CLAUDE.md | Every new button |
| **Never put `data-umami-event` on an internal react-router `<Link>`** — it downgrades to a full page reload; use `trackEvent()` in `onClick` | frontend/CLAUDE.md | The "Why?" control must be a `<Button onClick={navigate('/welcome')}>` or carry no umami attribute |
| Only signup-CTA attribution, guest starts and the PWA install funnel are tracked | frontend/CLAUDE.md | Do not add new event names beyond `signup-cta` sources |
| Em-dashes sparingly in UI copy | CLAUDE.md | All new strings |
| Do not add unplanned features/refactors outside phase scope | CLAUDE.md Project Management | The `TrainScheduleSettings` finding (Open Question 1) needs an explicit decision, not a silent fix |
| Frontend has no Prettier — never run `prettier --write` | MEMORY | — |
| `npm run build` (`tsc -b && vite build`) is the ONLY frontend type check | `frontend/package.json:13` | Must be in the verify command set; lint+test do not type-check |

## Architecture Patterns

### System Architecture Diagram

```
                       ┌──────────────────────────────────────────────┐
  Guest clicks CTA ───▶│  HomePage (frontend/src/pages/Home.tsx:752)  │
                       │  token? → profile → hasGames?                │
                       └───────┬──────────────────────┬───────────────┘
            LEVER A: delete    │                      │
            this branch ──────▶│ is_guest && !hasGames│ else
                               │   && !dismissed      │
                               ▼                      ▼
                        /welcome (interstitial)   /library/import ◀── new single destination
                               │                      │
                               │                      ├─▶ ImportPage
                               │                      │     └─ guest? ──▶ [NEW] friendly-bot bubble
                               │                      │          ("Why?" → /welcome, "Sign up free")
                               ▼                      │
                    [REWRITE] 4-delta page ◀──────────┘ ("Why?" target)
                       one "Sign up free" + Back

  Nav "Train" ──▶ isNavLocked('/train', navUnlocked)          ImportRequiredRoute
                   │  D-01: add '/train' to                    │  D-01: unwrap /train/*
                   ▼  IMPORT_EXEMPT_ROUTES                     ▼
                  ┌──────────────────────────────────────────────────────┐
                  │ TrainPage (Train.tsx)                                │
                  │  DELETE the isGuest → <TrainGuestGate/> early return │
                  └───────┬──────────────────────────────────────────────┘
                          │ POST /train/sessions  ── _reject_guest ✂ (7 sites)
                          ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │ compose_and_materialize_session (train_repository.py:2195)         │
     │  _material_flags → (False, False) for 0 games                      │
     │  _stamp_pool_eligibility(has_material = … OR sharp_filler_available())  ← streak accrues
     │  _assemble_session_items → SR(0) + herring(global pool) + sharp filler  │
     │  is_warmup = len(surviving_sr_keys) == 0  → TRUE                   │
     └───────┬────────────────────────────────────────────────────────────┘
             ▼
   TrainStartScreen (warmup banner: WARMUP_BODY_COLD_START ← D-03 lies for 0 games)
             ▼ solve loop
   TrainScoreScreen  ── guest? ──▶ [NEW] sign-up ask replaces WARMUP_REMINDER_ASK_COPY
             │                        actions: "Why?" + "Sign up free"
             │                        suppress reminderControl / belowRow (QR, push)
             └── registered? ──▶ byte-identical to today (SC 3)

  Promotion: POST /auth/guest/promote/{email,google} → UPDATE users SET is_guest=false,
             promoted_at=now()   (SAME ROW → drill_sessions/train_settings/solves survive)

  30-day purge: guest_cleanup_service._purge_guest → [D-08 NEW] delete DrillSession (cascades
             DrillSolve) + TrainSettings, alongside the existing games cascade
```

### Component Responsibilities

| File | Today | After this phase |
|---|---|---|
| `frontend/src/pages/Home.tsx:777-784` | Redirects 0-game guests to `/welcome` | Single `Navigate` to `hasGames ? '/library/games' : '/library/import'` |
| `frontend/src/lib/welcomeDismissal.ts` | localStorage flag helper (22 LOC) | **DELETED** |
| `frontend/src/pages/Welcome.tsx` | 10-row comparison table + checkbox + 2 buttons (202 LOC) | 4 deltas, one primary "Sign up free", a Back affordance |
| `frontend/src/components/train/TrainGuestGate.tsx` | Guest landing for `/train` (56 LOC) | **DELETED** |
| `frontend/src/pages/Train.tsx:176-186` | `if (isGuest) return <TrainGuestGate/>` | Removed; `canTrain` becomes `profile != null` |
| `frontend/src/components/train/TrainScoreScreen.tsx` | Reminder ask + slot + QR + Done | Guest branch: sign-up ask in the bubble's `actions`, reminder slot suppressed |
| `frontend/src/pages/Import.tsx:419-433` | Guest `Alert` + inline link | `<ImportGuestPromoBubble />` (new file) |
| `app/routers/train.py` | `_reject_guest` at 7 call sites + module docstring | Function and all call sites removed; docstring rewritten |
| `app/services/guest_cleanup_service.py:~108` | Comment: guests never accumulate Train rows | D-08 deletes + superseding comment |
| `app/services/activity_queries.py` | 20 dashboard queries | + guest-cohort Train row |

### Recommended file layout for the new pieces

```
frontend/src/components/train/
├── SignupAskActions.tsx          # NEW — "Why?" + "Sign up free" pair, takes source: 'train-score' | 'import-promo'
└── TrainScoreScreen.tsx          # guest branch delegates to the above + a pure copy fn

frontend/src/components/import/    (or pages/import/)
└── ImportGuestPromoBubble.tsx    # NEW — pickBot('friendly') + bubble + SignupAskActions

frontend/src/lib/trainBotCopy.ts  # + GUEST_SIGNUP_ASK_* constants, + hasGames/isGuest copy branch
reports/growth/
└── guest-activation-baseline-2026-09-XX.md   # NEW — D-10(a)
```

### Pattern 1: Guest reads come from `useUserProfile()`, never `useAuth()`

**What:** `is_guest` and the two game counts live on the profile query only.
**When:** every guest branch this phase adds.
**Evidence** [VERIFIED: `frontend/src/pages/Train.tsx:66-70`], quoted verbatim:

```tsx
  // FLAWCHESS-64: is_guest read from useUserProfile(), never useAuth().user
  // (always null, carries no is_guest — D-02, cf. the Analysis.tsx:789
  // free-play ELO source comment).
  const { data: profile, isError: profileError } = useUserProfile();
  const isGuest = profile?.is_guest === true;
```

Every existing guest branch in the app follows this: `Bots.tsx:603`, `Import.tsx:419`,
`library/FlawsTab.tsx:248`, `GlobalStats.tsx:113`, `library/GamesTab.tsx:286`, `App.tsx:218/354/570/658/661/705`
[VERIFIED: grep over `frontend/src` for `is_guest`, this session]. `useAuth().user` appears in **zero**
guest branches.

**`hasGames` (D-03) uses the `Home.tsx` pattern** [VERIFIED: `frontend/src/pages/Home.tsx:778-779`]:

```tsx
    const hasGames =
      (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;
```

### Pattern 2: Structural absence, never a disabled placeholder

The Train surface's established idiom for "this affordance does not apply to you" is to render
nothing at all [VERIFIED: `frontend/src/components/train/TrainScheduleSettings.tsx:355-357`]:

```tsx
  // D-10/D-12: a clean structural absence, not a disabled placeholder, until
  // both feature detection and the VAPID-key query have resolved.
  const showReminderBlock = capability.isResolved && capability.available;
```

Apply the same shape for the guest suppression of the reminder slot / QR block.

### Pattern 3: `TrainBotBubble`'s `actions` slot is already the right container

[VERIFIED: `frontend/src/components/train/TrainBotBubble.tsx:63-65, 148-152`], verbatim:

```tsx
  /** Optional action row (guess buttons, or Next/Solution/Analyze), rendered
   * as its own row INSIDE the bubble, below `children`. */
  actions?: ReactNode;
```
```tsx
        {actions !== undefined && (
          <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
        )}
```

Note the score screen currently passes **no** `actions` at all [VERIFIED: `TrainScoreScreen.tsx:260`
— `<TrainBotBubble persona={bot} state="verdict">`]. The guest branch is therefore purely additive,
which is exactly what SC 3 (registered screen byte-identical) needs.

### Pattern 4: Persona memoisation

[VERIFIED: `frontend/src/components/train/TrainScoreScreen.tsx:154-158`], verbatim:

```tsx
  // D-04: a random smart bot hosts the score bubble regardless of the
  // session's rating band — memoised once per mount so a re-render can never
  // recast mid-read (no deps: pickBot('smart') has no external inputs, so
  // exhaustive-deps raises nothing here).
  const bot = useMemo(() => pickBot('smart'), []);
```

Recommendation for the Import bubble (Claude's discretion in CONTEXT): mirror this exactly —
`useMemo(() => pickBot('friendly'), [])`. `ImportPage` re-renders on every import-job poll tick, so
without the memo the persona would recast mid-read, which is precisely the failure the score-screen
comment names. Pool sizes confirmed [VERIFIED: `grep -c "temperament: '<t>'" frontend/src/lib/personas/personaRegistry.ts`
→ friendly **9**, smart **7**, stern **8**].

### Anti-Patterns to Avoid

- **Inlining either new bubble into its host page.** `ImportPage` has zero complexity headroom (Pitfall 1).
- **Adding `data-umami-event` to a `<Link to="/welcome">`.** Documented full-page-reload bug (frontend/CLAUDE.md).
- **Branching the score screen on `is_guest` alone.** D-03 requires two orthogonal flags; a registered
  0-game user must read import-only copy with no sign-up ask.
- **Deleting `drill_solves` explicitly in the purge.** `drill_solves.session_id` is `ondelete="CASCADE"`
  to `drill_sessions` (verified below) — deleting the sessions is sufficient and one fewer statement.
- **Leaving `reminder_enabled` reachable for guests.** See Open Question 1.
- **Refactoring `Train.tsx`.** Baselined at complexity 24; the phase only removes a branch from it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| "Sign up free" handoff | A new promote flow | `logoutForPromotion()` + `window.location.href = '/login?tab=register'` | Sets `sessionStorage.promote_intent = '1'`, clears the query cache and the auth token in the right order [VERIFIED: `frontend/src/hooks/useAuth.ts:170-182`] |
| Guest abuse ceiling | A per-guest Train quota | `guest_create_limiter` (5/hour/IP) + the one-session-per-day compose rule | D-09; verified end-to-end below |
| Purging a guest's solves | A `delete(DrillSolve)` statement | Deleting `DrillSession` | FK cascade does it |
| Cohort SQL predicates | New ad-hoc guest predicates | `_GUEST_COHORT` and `games_purged_at IS NULL` | Already the dashboard-wide convention |
| Day arithmetic in copy | `new Date()` math | `differenceInCalendarDays` + `parseISO` | `trainBotCopy.ts` D-15 bans client clock reads |
| Persona art / names | Anything new | `TrainBotBubble` + `PERSONA_REGISTRY` | 24 personas with avatars already wired |

**Key insight:** every piece of this phase is a deletion or a re-composition of something already
shipped. The risk is not "can we build it" but "what else was written assuming the gate exists".

## Runtime State Inventory

This is not a rename phase, but it IS a gate-removal phase, which has the same shape of hazard:
invariants asserted elsewhere on the basis of the gate. Every category answered explicitly.

| Category | Items found | Action required |
|---|---|---|
| **Stored data** | None new. Guests already have `users` rows; `drill_sessions`/`train_settings`/`drill_solves` rows will start appearing for guests where none existed. No backfill, no migration. | None — code only |
| **Code invariants written on the gate** | **3 found.** (1) `app/repositories/train_reminder_repository.py:43-46` docstring: "Guest exclusion (REMIND-07) is defence in depth: `/train/*` already 403s guests, so a guest cannot reach `reminder_enabled=True` through the API today". The *filter* stays correct and load-bearing; the *docstring* becomes false. (2) `app/services/guest_cleanup_service.py` purge comment: "in practice a guest never accumulates Train rows in the first place: `_reject_guest` … rejects every /train/* request with 403". (3) `frontend/src/components/train/TrainGuestGate.tsx:9-14` and `frontend/src/pages/Train.tsx:85-89` both restate "correct, and it stays". | Update (1); D-08 rewrites (2); (3) is deleted with the files |
| **Live service config** | None. No n8n/Datadog/Cloudflare object references the gate. | None |
| **OS-registered state** | None. | None ("verified by absence of any scheduler/systemd reference to train endpoints") |
| **Secrets / env vars** | None. Umami site id and VAPID keys unchanged. | None |
| **Build artifacts** | Frontend bundle only (`npm run build`). Knip will flag the deleted modules' importers if any are missed. | Re-run `npm run knip` |
| **Test invariants written on the gate** | **7 found.** Backend: `tests/routers/test_train.py::test_403_guest` (:967), `::test_settings_403_guest` (:2551), `::test_onboarding_403_guest` (:2580), `::test_progress_403_guest` (:2992), plus 4 docstring references at :12/:54/:65/:78-80/:104. Frontend: `frontend/src/App.test.tsx` "190-03: Train gating (NAV-02)" locked/unlocked pair (:495-551) and "190-03: empty profile … renders Train locked" (:553+); `frontend/src/pages/__tests__/Train.guestGate.test.tsx` (293 LOC, 6 tests); `frontend/src/pages/__tests__/Welcome.test.tsx` (117 LOC). | Invert / rewrite / delete — see Validation Architecture |

**The canonical question for this phase:** *after `_reject_guest` is gone, which assertion, comment or
query elsewhere still believes a guest has no Train state?* Answer: the three code invariants and the
seven tests above — nothing else. Verified by grepping `is_guest` across `app/` and `frontend/src`
this session (full result sets reviewed).

## Findings the planner must not skip

### Finding A — the seven `_reject_guest` call sites, exactly

[VERIFIED: `app/routers/train.py`, grep with line numbers, this session]

| Line | Handler | Route |
|---|---|---|
| 71 | `compose_or_resume_session` | `POST /train/sessions` |
| 138 | `solve_puzzle` | `POST /train/sessions/{session_id}/solve` |
| 189 | `reveal_puzzle` | `GET /train/sessions/{session_id}/puzzles/{position}/reveal` |
| 230 | `get_train_progress` | `GET /train/progress` |
| 284 | `get_train_settings` | `GET /train/settings` |
| 324 | `update_train_settings` | `PUT /train/settings` |
| 364 | `stamp_onboarding_step` | `POST /train/onboarding/{step}` |

The definition sits at `app/routers/train.py:50-57`, verbatim:

```python
def _reject_guest(user: User) -> None:
    """D-05: explicit gate, not an empty-result inference.

    Every /train/* handler calls this before touching any pool/session/
    settings repository — centralized so no route can forget it (Pitfall 7).
    """
    if user.is_guest:
        raise HTTPException(status_code=403, detail="Train requires a full account")
```

The module docstring's first paragraph must go too [VERIFIED: `app/routers/train.py:1-5`]:

```python
"""Train router: session composition (Phase 189).

D-05 (LOCKED): Train is not available to guest accounts. Every handler calls
`_reject_guest` as its FIRST statement — an explicit 403 gate, not an
inference from an empty pool result (Pitfall 7 in 189-RESEARCH.md).
```

After removal, `User` may become an unused import — it is still used in the handler signatures
(`user: Annotated[User, Depends(current_active_user)]`), so it stays. Ruff will confirm.

### Finding B — nothing else in the Train service/repository layer branches on `is_guest`

[VERIFIED: `grep -rn "is_guest" app/`, full output reviewed this session]. Inside the Train stack the
ONLY occurrences are `app/routers/train.py:56` (the gate) and
`app/repositories/train_reminder_repository.py:58` (`User.is_guest.is_(False)` in the reminder
fan-out). `train_repository.py`, `train_pool.py`, `train_scheduler.py`, `sharp_filler.py` contain
**zero** `is_guest` references. No DB constraint mentions guests: `drill_sessions`, `drill_solves`,
`drill_items` and `train_settings` all key on `users.id` alone.

### Finding C — the compose path works with zero games, and why

Three independent legs, each verified:

1. **Eligibility stamping already counts filler as material** [VERIFIED: `app/repositories/train_repository.py:2278-2288`], verbatim:
   ```python
       # ROADMAP Success Criterion 5 (Phase 206): widened with sharp_filler_available()
       # so a filler-only session still stamps the eligibility floor tick_days
       # reads — without this term a warm-up user accrues NO streak regardless
       # of what the UI says. Do not "simplify" this third term away.
       await _stamp_pool_eligibility(
           session,
           user_id=user_id,
           settings_row=settings_row,
           today=today,
           has_material=has_drill_items or has_pool_candidates or sharp_filler_available(),
       )
   ```
   → a 0-game guest accrues streak. SC 2's "streak state persists" is satisfied by existing code.

2. **The red-herring source is global, never scoped to the caller's games** [VERIFIED: `app/services/train_pool.py:928-944` + the D-10 note inside `herring_stmt`'s body], verbatim from the docstring:
   > "a global, phase-balanced pool of positions … drawn across ALL signed-up users' games" and
   > "D-10: this function NEVER filters on `HerringPool.user_id`".

3. **Sharp filler is a committed static CC0 set with a per-user served-exclusion only** [VERIFIED: `app/repositories/train_repository.py:1770-1810`] — `served_sharp_ids_stmt(user_id)` then `pick_sharp_fillers(served, limit=shortfall)`. No rating input, no games input.

4. **The warm-up label is a plain equality** [VERIFIED: `app/repositories/train_repository.py:2047-2051`], verbatim:
   ```python
       # Phase 206 (D-06/D-07): the warm-up discriminant is a plain equality
       # against zero — never a ratio, never a threshold — computed from
       # surviving_sr_keys alone and frozen onto the drill_sessions row below.
       is_warmup = len(surviving_sr_keys) == 0
   ```
   → every guest session is `is_warmup = true` until they have analyzed own blunders.

**Corollary the copy must respect (accuracy rule, 223 D-08):** a guest's imported games are NOT
auto-analyzed. `eval_queue_service` excludes guests from every tier except explicit tier-1
[VERIFIED: `app/services/eval_queue_service.py:253` — `AND (u.is_guest = false OR ej.tier = 1)`; and
`:1158-1170` docstring: "Tier-1 is an explicit per-game request that a guest may make for their own
game (QUEUE-08 guest gate opened for tier-1)"]. So "import your games and your own mistakes take
over" is **false for a guest who only imports**; it becomes true only after they sign up (automatic
analysis) or manually analyze game by game. This is exactly why CONTEXT D-03/ROADMAP SC 7 fix the
order as *import, then sign up* — the plan must keep that order and must not promise automatic
analysis to a guest.

### Finding D — `_pool_state` returns `no_material` for every 0-game account (CONTEXT's stated reason is wrong; the conclusion happens to hold)

[VERIFIED: `app/repositories/train_repository.py:1206-1250`], resolution rule verbatim:

```python
    if not has_drill_items and not has_pool_candidates and blob_pending_count == 0:
        return "no_material"
```

and `has_pool_candidates` comes from the user's OWN blunders, not the herring pool
[VERIFIED: `app/repositories/train_repository.py:590-592`]:

```python
    has_pool_candidates = (
        await session.execute(select(pool_entry_stmt(user_id).exists()))
    ).scalar_one()
```

with [VERIFIED: `app/services/train_pool.py:762-764`] — `pool_entry_stmt` is documented as
"Own-blunder pool-entry candidates for `user_id` (POOL-01)".

**Why it does not break anything:** `TrainEmptyBody` (which renders the `no_material` "Import &
analyze your games to start training" empty state) is only reached from the `empty` landing state,
and `empty` requires a null `session_id` [VERIFIED: `frontend/src/components/train/TrainStartScreen.tsx:298-305`
— `if (state.kind === 'empty') { … <TrainEmptyBody …/> }`]. A 0-game guest composes a real filler
session, so `session_id` is non-null and the landing resolves to `warmup`
[VERIFIED: `TrainStartScreen.tsx:170-172` — `if (session.is_warmup) { return { kind: 'warmup', … } }`].
**Planner action:** do not restate CONTEXT's reason in the plan; state the real one. And do NOT
"fix" `_pool_state` — it is not in scope and nothing reads it on this path.

### Finding E — the exact false string a 0-game account sees today

[VERIFIED: `frontend/src/components/train/TrainStartScreen.tsx:97-100`], verbatim:

```tsx
const WARMUP_BODY_COLD_START =
  "We're analyzing your games to find your blunders. In the meantime, here are some practice puzzles.";
const WARMUP_BODY_CAUGHT_UP =
  "You're all caught up on your own mistakes. In the meantime, here are some practice puzzles.";
```

selected at `TrainStartScreen.tsx:345`: `const warmupBody = nextDueDate === null ? WARMUP_BODY_COLD_START : WARMUP_BODY_CAUGHT_UP;`
→ a 0-game account (`next_due_date === null`) gets the cold-start string, which claims an analysis
that is not running. This is D-03's primary target. The D-03 branch is a THIRD case, not a
re-purposing of either existing string (both remain true of their own case, per the 206 UAT note in
the same docstring).

The other four D-03 sites, verbatim:

- `INTRO_WELCOME` [VERIFIED: `frontend/src/lib/trainBotCopy.ts:229-234`]: `'Welcome to FlawChess Train, my chess boot camp! You will improve by solving puzzles ' + 'created from your own games.'`
- `INTRO_WARMUP` [VERIFIED: `trainBotCopy.ts:260-265`]: `"We're still analyzing your games to find your mistakes. In the meantime, " + "let's start with a warm-up session."`
- `WARMUP_TAIL` [VERIFIED: `trainBotCopy.ts:384`]: `const WARMUP_TAIL = "That one was a warm-up, so it won't come back. Your own positions will.";`
- `scoreBubbleCopy` warm-up opener [VERIFIED: `trainBotCopy.ts:681-689`]:
  ```ts
    if (input.isWarmup) {
      return {
        lines: [
          `${sessionOpener(input.band)} Those were warm-ups, nothing to bring back yet. ` +
            'Once your games are analyzed, your own mistakes take over.',
          WARMUP_REMINDER_ASK_COPY[input.reminderAsk],
        ],
      };
    }
  ```

`WARMUP_REMINDER_ASK_COPY` — the string S-3 replaces for guests [VERIFIED: `trainBotCopy.ts:559-566`]:

```ts
const WARMUP_REMINDER_ASK_COPY: Record<ReminderAsk, string> = {
  remind_me: 'Turn on Remind me so the habit is there when they arrive.',
  scan_qr:
    'Scan the code below to install FlawChess on your phone and turn on reminders, so ' +
    'the habit is ready when they arrive.',
  none: 'Your reminders are on, so the habit will be there when they arrive.',
};
```

**Recommended shape:** extend `ScoreBubbleInput` with two booleans (`isGuest`, `hasGames`) and keep the
precedence table intact — the warm-up variant's SECOND line becomes
`isGuest ? GUEST_SIGNUP_ASK : WARMUP_REMINDER_ASK_COPY[input.reminderAsk]`, and the FIRST line's
"Once your games are analyzed…" clause becomes `hasGames ? … : IMPORT_FIRST_CLAUSE`. That keeps the
whole change inside a pure function with 100% unit-testable surface and adds ~2 to
`scoreBubbleCopy`'s complexity (currently **4**, cap 15 — ample).

### Finding F — promotion is an in-place UPDATE (SC 4 is free; prove it with a test)

[VERIFIED: `app/services/guest_service.py:102-118`], verbatim:

```python
    await session.execute(
        sa_update(User)
        .where(User.id == user.id)
        .values(
            email=email,
            hashed_password=hashed_password,
            is_guest=False,
            is_verified=True,
            promoted_at=func.now(),
        )
    )
```

`promote_guest_with_google` is structurally identical [VERIFIED: `app/services/guest_service.py:169-178`].
No row is created or deleted, so every `drill_sessions.user_id` / `train_settings.user_id` /
`drill_solves.user_id` FK still points at the same PK.

**Existing test to extend** [VERIFIED: `tests/test_guest_auth.py:614-646` —
`test_data_preserved_after_promotion`], which already proves in-place identity via `created_at`. The
new GUESTACT test should follow the same httpx-ASGI shape: create guest → `POST /train/sessions` →
promote → assert the `drill_sessions` / `train_settings` rows still resolve for that user id and the
streak snapshot is unchanged. Google-path equivalents live in `tests/test_guest_google_promotion.py`
(`test_promotion_preserves_user_id`, :169).

### Finding G — guest cleanup: the exact FK reality for D-08

[VERIFIED, model files read this session]:

| Table | Column | FK policy | Consequence for a purged guest today |
|---|---|---|---|
| `drill_items` | `user_id` PK part → `users.id` | `ondelete="CASCADE"` [`app/models/drill_item.py:76`] | survives (user row survives) |
| `drill_items` | `game_id` PK part → `games.id` | `ondelete="CASCADE"` [`app/models/drill_item.py:82`] | **deleted** by the games cascade |
| `drill_solves` | `session_id` PK part → `drill_sessions.id` | `ondelete="CASCADE"` [`app/models/drill_solve.py:132-134`] | survives |
| `drill_solves` | `game_id` → `games.id` | `ondelete="SET NULL"` [`app/models/drill_solve.py:143-145`] | **survives with `game_id` nulled** |
| `drill_solves` | `herring_pool_id` → `herring_pool.id` | `ondelete="SET NULL"` [`app/models/drill_solve.py:149-151`] | survives |
| `drill_sessions` | `user_id` → `users.id` | `ondelete="CASCADE"` [`app/models/drill_session.py:64`] | survives |
| `train_settings` | `user_id` PK → `users.id` | `ondelete="CASCADE"` [`app/models/train_settings.py:61-63`] | survives |

**Therefore D-08 needs exactly two new statements** inside `_purge_guest`'s single transaction:
`delete(DrillSession).where(DrillSession.user_id == guest_id)` (which cascades every `drill_solves`
row, including the filler/herring ones that the games cascade cannot reach) and
`delete(TrainSettings).where(TrainSettings.user_id == guest_id)`. Ordering: before or after the
existing deletes is immaterial (no FK between them and `games`), but placing them next to the
existing "Phase 189 Plan 02 (POOL-09, D-04/D-05)" comment block is where the superseded comment lives.

The comment to supersede [VERIFIED: `app/services/guest_cleanup_service.py` purge body, verbatim]:

```python
        # Phase 189 Plan 02 (POOL-09, D-04/D-05): the Train tables need NO
        # handling here either. `drill_items`/`drill_solves` ride the same
        # `games` cascade `delete_all_games_for_user` already triggered above
        # (D-02). `drill_sessions`/`train_settings` are preserved by design
        # (D-04, session history is user progress, not game-derived data) --
        # do NOT add a delete for them. And in practice a guest never
        # accumulates Train rows in the first place: `_reject_guest` (Phase
        # 189's D-05) rejects every /train/* request with 403 before any pool
        # query runs, so this purge never needs to reason about a guest's
        # drill state. See tests/test_guest_cleanup_service.py::
        # test_purge_guest_cascades_drill_rows.
```

Note the D-04 preservation for **registered** users is untouched (CONTEXT D-08) — the deletes live
inside `_purge_guest`, which re-verifies `User.is_guest.is_(True)` in the same transaction
[VERIFIED: `app/services/guest_cleanup_service.py` WR-01 block, `still_eligible` query], so it is
structurally impossible for this to reach a registered user.

**Test to rewrite** [VERIFIED: `tests/test_guest_cleanup_service.py:418-499` —
`test_purge_guest_cascades_drill_rows`]. Its current assertions are the exact inverse of D-08:

```python
        assert await _count(DrillSession, DrillSession.id == drill_session_id) == 1, (
            "drill_sessions must survive the guest purge (D-04)"
        )
        # D-05: the drill_solves row survives with game_id nulled (SET NULL,
        # not CASCADE) — never deleted alongside drill_items.
        assert await _count(DrillSolve, DrillSolve.user_id == guest_id) == 1
```

The rewrite must (a) flip these to `== 0`, (b) add a `TrainSettings` row to the seed and assert it is
gone, (c) add a `drill_solves` row with `game_id=None, source=2` (SHARP_FILLER) to prove the
non-game-derived solve is reached too — that row is invisible to the games cascade and is the whole
reason the explicit delete is needed, (d) restate the rule in the docstring (ROADMAP SC 8). Helpers
available: `_seed_eligible_guest_with_game` (:531) and the autouse `_cleanup_leaked_guest_rows`
fixture (:122). `DrillSource` values are verbatim [VERIFIED: `app/models/drill_solve.py:123` —
`CheckConstraint("source IN (0, 1, 2)", name="ck_drill_solves_source")`].

### Finding H — the guest-creation limiter IS the Cf-Connecting-Ip-aware backstop (D-09 verified end to end)

Four links in the chain, each read this session:

1. Caddy resolves the real visitor IP only from trusted Cloudflare peers [VERIFIED: `deploy/Caddyfile:25-42`], verbatim ending: `client_ip_headers Cf-Connecting-Ip`.
2. Uvicorn is started with `--proxy-headers --forwarded-allow-ips='*'` [VERIFIED: `deploy/entrypoint.sh:10`], verbatim:
   `exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'`
3. With `always_trust`, uvicorn 0.52.4 takes the **leftmost** `X-Forwarded-For` entry — the real client [VERIFIED: `.venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py:169-178`], verbatim:
   ```python
        x_forwarded_for_hosts = _parse_raw_hosts(x_forwarded_for)

        if self.always_trust:
            return _parse_host_port(x_forwarded_for_hosts[0])
   ```
4. The endpoint keys the limiter on that value [VERIFIED: `app/routers/auth.py:306-317`], verbatim:
   ```python
       client_ip = request.client.host if request.client else "unknown"
       if not guest_create_limiter.is_allowed(client_ip):
           raise HTTPException(
               status_code=status.HTTP_429_TOO_MANY_REQUESTS,
               detail="Too many guest accounts created from this IP",
           )
   ```
   with limits [VERIFIED: `app/core/ip_rate_limiter.py:11-12`], verbatim:
   ```python
   _GUEST_CREATE_MAX_REQUESTS = 5
   _GUEST_CREATE_WINDOW_SECONDS = 3600  # 1 hour
   ```

**Caveat worth one sentence in the plan** [VERIFIED: `app/core/ip_rate_limiter.py:1-5` docstring]: "In-process
limiter — resets on server restart. Acceptable for single-process Uvicorn deployment." A deploy
restart clears the window. Existing coverage: `tests/test_guest_auth.py::test_rate_limit_blocks_after_5_creates`
(:287) and the two unit tests at :56/:67. **No new guard, no new test needed** — D-09 asks research to
verify, and it verifies.

### Finding I — Umami + growth-report provenance for the lever A baseline

The 2026-09-15 growth report contains **no committed SQL** [VERIFIED: `reports/growth/growth-recommendations-2026-09-15.md`,
full read of §1/§2/§3 and grep for `SQL`]. Its stated sources are "prod DB … , Umami DB (both sites,
via SSH read-only), the in-app Activity Pulse dashboard" (line 3), and the two lever-A numbers appear
only as prose in finding 2: "468 created, 226 start an import (48%)" and "390 of 1,051 home visitors
who clicked anything landed there". The 2026-09-17 correction block at the top of the file explains
why the earlier `import_jobs`-derived reading was an artifact — purged rows.

**Consequence for D-10(a):** the baseline note must author the SQL from scratch. The import-start
half is reproducible exactly against the prod DB, because `fetch_funnel` already encodes the
definition [VERIFIED: `app/services/activity_queries.py:471-491`] — cohort
`u.created_at >= :first AND u.games_purged_at IS NULL`, guest split `_GUEST_COHORT`, started
`(u.first_import_started_at IS NOT NULL OR u.linked)`. Reuse that predicate verbatim so the
before/after readings are the same query. The `/welcome` landings half is **Umami**, a separate
database (`postgresql://…@db:5432/umami` [VERIFIED: `docker-compose.yml` umami service
`DATABASE_URL`]) that the read-only `flawchess-prod-db` MCP role does not reach — see Environment
Availability and Open Question 3.

### Finding J — the Activity dashboard extension points (D-10b/D-11/D-12)

[VERIFIED: `app/services/activity_queries.py`]

- `fetch_train` (:284-302) currently has **no `users` join at all** — it groups `drill_sessions` by `session_date` only. The guest row therefore needs a new query (or a join added), not a filter tweak.
- `_GUEST_COHORT` (:58), verbatim: `_GUEST_COHORT = "(u.is_guest OR u.promoted_at IS NOT NULL)"`
- `_PROMOTED_GUEST` (:52), verbatim: `_PROMOTED_GUEST = "u.promoted_at IS NOT NULL"`
- `fetch_conversion` (:631-661) already computes the lever-B promotion rate (`sessions`, `converted`) over exactly the D-11 cohort. **Lever B metric 1 needs no new query** — it is on the dashboard today.
- `fetch_purged_excluded` (:504-531) supplies the D-12 footnote count.
- Every query is a raw string executed through `_rows(conn, sql, **params)`; the result is packed into `Payload` (:61-86, a `TypedDict`) by `build_payload` (`app/services/activity_stats.py:57-92`).
- **Test coupling:** `tests/test_admin_activity_stats.py:103-129` builds a "minimal, schema-complete Payload"; a new `Payload` key must be added there or ~8 tests fail.
- **Render side:** `frontend/src/pages/activity/render.js:311-323` draws `#c-train` (chart) and `#t-train` (table); the card markup is `frontend/src/pages/activity/ActivityPage.tsx:460-476`. **Recommendation: render the guest cohort as extra columns in the existing `t-train` table or as a `hero` pair, NOT as a new chart** — charts are validated by `npm run check:activity-layout`, a node:vm harness over `charts.js` at four phone widths [VERIFIED: `frontend/scripts/check-activity-layout.mjs:1-31`], and a new chart series adds a geometry surface for no analytical gain.

**Proposed D-11 SQL** (draft for the planner; must be run against prod before merge):

```sql
-- Guest Train sessions completed (D-11/D-12), cohort = guests created in the window
SELECT count(*) AS guest_sessions_completed,
       count(DISTINCT d.user_id) AS guest_users
FROM drill_sessions d
JOIN users u ON u.id = d.user_id
WHERE u.created_at >= CAST(:first AS date)
  AND (u.is_guest OR u.promoted_at IS NOT NULL)   -- _GUEST_COHORT
  AND u.games_purged_at IS NULL                   -- D-12
  AND d.status = 'completed'
  AND d.session_date < COALESCE(u.promoted_at::date, 'infinity'::date);  -- D-11
```

Two type notes the planner must carry: `drill_sessions.session_date` is a `Date`
[VERIFIED: `app/models/drill_session.py:67` — `session_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)`]
while `users.promoted_at` is a `DateTime(timezone=True)` [VERIFIED: `app/models/user.py:47`], hence
the explicit `::date` cast; and `status` is TEXT with a CHECK
[VERIFIED: `app/models/drill_session.py:45-47`, verbatim:
`CheckConstraint("status IN ('open', 'completed', 'expired')", name="ck_drill_sessions_status")`],
so `'completed'` is the correct literal.

## Common Pitfalls

### Pitfall 1: The complexity gate, which two of the four host files cannot absorb

**What goes wrong:** `npm run lint` fails in CI, and frontend/CLAUDE.md forbids baselining a NEW breach.
**Measured this session** with the documented defeat-the-baseline command
(`npx eslint --no-inline-config --rule 'complexity: ["error", 1]' <path>`):

| Function | Current | Effective cap | Headroom |
|---|---|---|---|
| `ImportPage` (`src/pages/Import.tsx:258`) | **29** | 29 (baselined, `eslint.config.js:166-172`) | **0** |
| `TrainScoreScreen` (`src/components/train/TrainScoreScreen.tsx:142`) | **13** | 15 (not baselined) | **2** |
| `TrainScoreScreen` max-statements | **20** | 100 | ample |
| `TrainPage` (`src/pages/Train.tsx`) | — | 24 (baselined, `eslint.config.js:139-146`) | phase only removes a branch |
| `HomePage` (`src/pages/Home.tsx:752`) | **12** | 15 | phase removes a branch → 11 |
| `WelcomePage` max-statements | 6 | 100 | ample |
| `scoreBubbleCopy` (`trainBotCopy.ts:680`) | **4** | 15 | ample |

**How to avoid:** extract `<ImportGuestPromoBubble />` into its own file (removes the
`{profile?.is_guest && (…)}` branch from `ImportPage`, taking it 29 → 28) and put the score-screen
guest branch in (a) the pure `scoreBubbleCopy` function and (b) an extracted `<SignupAskActions />`.
Passing `isGuest`/`hasGames` as props from `Train.tsx` costs `TrainScoreScreen` zero complexity;
calling `useUserProfile()` inside it and branching costs 2+ and will breach.
**Warning signs:** any new `&&`, `?:`, `??` or `if` added directly inside `ImportPage` or
`TrainScoreScreen`'s body.

### Pitfall 2: The reminder toggle a guest can reach on the Train landing (not covered by S-3)

**What goes wrong:** S-3 suppresses the reminder ask, QR block and push subscription on the **score
screen**. But the Train **landing** renders `<TrainScheduleSettings />` unconditionally
[VERIFIED: `frontend/src/components/train/TrainStartScreen.tsx:316` and `:380`], and that card contains
a master "Remind me to train" `Switch` + hour `Select` + a permanent QR/install block
[VERIFIED: `TrainScheduleSettings.tsx:25-48` module docstring, `:355-395` handlers]. A guest can flip
it, `PUT /train/settings` will happily persist `reminder_enabled = true` (the handler round-trips it
[VERIFIED: `app/routers/train.py:324-337`]), the device will subscribe — and the reminder job will
never select them, because the fan-out query filters `User.is_guest.is_(False)`
[VERIFIED: `app/repositories/train_reminder_repository.py:57`]. That is a silent broken promise of
exactly the kind Phase 202 D-06 exists to prevent, and it contradicts S-3's stated rationale ("a push
promise for an account purged after 30 idle days cannot be kept").
**How to avoid:** gate `showReminderBlock` (and the QR branch) on `!isGuest` using the structural-absence
idiom already in that file. **This is a scope discovery, not a locked decision — see Open Question 1.**
**Warning signs:** a guest sees a Bell switch anywhere under `/train`.

### Pitfall 3: SC 3's "byte-identical registered score screen" is easy to break by accident

**What goes wrong:** any refactor of `TrainScoreScreen` that reorders the `useTrainReminderSlot()`
call, changes the `reminderAsk` resolution, or wraps the bubble differently will change registered
output even if the rendered pixels look the same to a human.
**How to avoid:** the guest branch must be additive and guarded — `isGuest ? <SignupAskActions/> : undefined`
passed to the existing `actions` prop (today `undefined`), and `isGuest ? null : reminderControl`.
Do NOT conditionally skip the `useTrainReminderSlot()` hook call (rules of hooks) — call it always,
discard its output for guests.
**Warning signs:** a diff in `TrainScoreScreen.test.tsx`'s existing non-guest assertions.

### Pitfall 4: Deleting files without clearing their importers (knip + build fail)

**What goes wrong:** `npm run knip` is a CI gate [VERIFIED: `.github/workflows/ci.yml:217`].
**Concrete importer list, verified this session:**
- `welcomeDismissal.ts` is imported by `Welcome.tsx:8` (`setWelcomeDismissed`), `Home.tsx:2` (`isWelcomeDismissed`), and `pages/__tests__/Welcome.test.tsx:15` (both). `lib/botGameSnapshot.ts:5,16` only *mentions* it in comments — those comments reference a deleted file after this phase and should be reworded.
- `TrainGuestGate.tsx` is imported by `Train.tsx:49` and `pages/__tests__/Train.guestGate.test.tsx`.
- After removing the Import `Alert`, `DoorOpen` [VERIFIED: `frontend/src/pages/Import.tsx:3`] and `logoutForPromotion`/`useAuth` [VERIFIED: `Import.tsx:26,259`] become unused **in that file** — ruff's TS equivalent (eslint `no-unused-vars`) will fail the build. `Alert` itself stays (used at `:250` and `:580`).
**Warning signs:** `npm run knip` output naming an unused export; `tsc -b` unused-import errors.

### Pitfall 5: `npm run lint && npm test` does not type-check

**What goes wrong:** esbuild strips types; a prop-signature change to `TrainScoreScreen` compiles
fine under vitest and fails only in `npm run build`.
**How to avoid:** `npm run build` is mandatory in every plan's verify block for this phase (it changes
shared types: `ScoreBubbleInput` gains fields, `TrainScoreScreenProps` gains props).
[VERIFIED: `frontend/package.json:13` — `"build": "tsc -b && vite build"`; MEMORY `feedback_frontend_run_tsc_build`]

### Pitfall 6: The App.test.tsx Train-gating tests assert the OPPOSITE of D-01

**What goes wrong:** D-01 adds `/train` to `IMPORT_EXEMPT_ROUTES`, and three existing tests assert
`nav-train` / `mobile-nav-train` / `drawer-nav-train` are `aria-disabled="true"` in the zero-game
state [VERIFIED: `frontend/src/App.test.tsx:495-551` and the null-profile case at `:553+`].
**How to avoid:** invert them in the same commit as the `IMPORT_EXEMPT_ROUTES` edit. The unlocked-state
test (`:528-551`) stays valid; the locked-state test becomes "Train is never aria-disabled, while
Openings/Endgames still are" — keeping an assertion that the lock mechanism itself still works
(the file already has that control-assertion pattern at `:282-301`).

### Pitfall 7: The `Train.guestGate.test.tsx` contamination flake disappears — do not chase it

[VERIFIED: `.planning/milestones/v2.15-phases/215-frontend-god-file-decomposition/deferred-items.md:8-21`]:
2 of 6 tests fail only in a full-suite run, pass in isolation; pre-existing cross-test contamination.
Deleting the file closes the deferred item. The plan should say so explicitly so a future reader does
not re-open it. **Warning sign:** anyone proposing to "fix the flake first".

### Pitfall 8: `/welcome` lives inside `ProtectedLayout`

[VERIFIED: `frontend/src/App.tsx:957-964`] — `/welcome` is declared under
`<Route element={<ProtectedLayout />}>`, i.e. it is NOT a public page. "Reachable by a plain URL"
means reachable by a logged-in guest or user. The `/welcome` rewrite must therefore decide what a
registered visitor sees (CONTEXT lists this as Claude's discretion) but must NOT assume an anonymous
visitor can land there. Also: the prerender list is `['/privacy']` plus `/`
[VERIFIED: `frontend/vite.config.ts:107-110`], so `/welcome` is not prerendered — no SEO surface changes.

### Pitfall 9: Guest-Train sessions will pull from a cross-user herring pool

Not a new risk introduced by any code change, but the population changes. ~91% of served herrings
come from another user's game (MEMORY `project_herring_pool_cross_user_ownership`), and the D-06
"Played in game: …" ownership copy already accounts for it. No action; D-09 settles the abuse
question. Listed here so the plan does not re-litigate it.

## Code Examples

### Guest branch in `scoreBubbleCopy` (pure, fully unit-testable)

```ts
// Source: extends frontend/src/lib/trainBotCopy.ts:680-703 (verbatim precedence preserved)
export function scoreBubbleCopy(input: ScoreBubbleInput): ScoreBubbleCopy {
  if (input.isWarmup) {
    return {
      lines: [
        `${sessionOpener(input.band)} Those were warm-ups, nothing to bring back yet. ` +
          (input.hasGames ? WARMUP_OWN_MISTAKES_CLAUSE : WARMUP_IMPORT_FIRST_CLAUSE),
        input.isGuest ? GUEST_SIGNUP_ASK_SCORE : WARMUP_REMINDER_ASK_COPY[input.reminderAsk],
      ],
    };
  }
  // …three remaining variants unchanged…
}
```

### Additive `actions` on the score bubble (registered path byte-identical)

```tsx
// Source: extends frontend/src/components/train/TrainScoreScreen.tsx:259-269
<div className="w-full max-w-sm text-left" data-testid="train-score-bubble">
  <TrainBotBubble
    persona={bot}
    state="verdict"
    actions={isGuest ? <SignupAskActions source="train-score" /> : undefined}
  >
    {/* unchanged */}
  </TrainBotBubble>
</div>
```

### The shared action pair (one definition, two surfaces)

```tsx
// Source: composes frontend/src/hooks/useAuth.ts:170 + frontend/CLAUDE.md button/umami rules
export function SignupAskActions({ source }: { source: 'train-score' | 'import-promo' }) {
  const navigate = useNavigate();
  const { logoutForPromotion } = useAuth();
  return (
    <>
      <Button
        variant="brand-outline"
        data-testid={`btn-signup-why-${source}`}
        onClick={() => navigate('/welcome')}
      >
        Why?
      </Button>
      <Button
        variant="default"
        data-testid={`btn-signup-free-${source}`}
        data-umami-event="signup-cta"
        data-umami-event-source={source}
        onClick={() => { logoutForPromotion(); window.location.href = '/login?tab=register'; }}
      >
        Sign up free
      </Button>
    </>
  );
}
```

Note: `data-umami-event` sits on a `<button>`, which is the sanctioned placement; the "Why?" control
carries no umami attribute because it is an internal navigation (frontend/CLAUDE.md).

### The two purge deletes (D-08)

```python
# Source: app/services/guest_cleanup_service.py::_purge_guest, same transaction as the games cascade
# Phase 224 D-08 SUPERSEDES the Phase 189 D-04 preservation FOR GUESTS ONLY: guests now hold real
# Train state (Phase 224 removed _reject_guest), and /welcome promises "no 30-day inactivity purge"
# as a sign-up delta — so a purged guest's Train rows go with their games. Deleting the sessions
# cascades drill_solves (drill_solves.session_id is ON DELETE CASCADE), which is what reaches the
# warm-up filler/herring solves the `games` cascade cannot see (their game_id is NULL / foreign).
# Registered users' D-04 preservation is untouched: this function only ever runs for is_guest rows
# (re-verified in this same transaction above).
await session.execute(delete(DrillSession).where(DrillSession.user_id == guest_id))
await session.execute(delete(TrainSettings).where(TrainSettings.user_id == guest_id))
```

## State of the Art

| Old approach (pre-224) | Current approach (this phase) | Why it changed |
|---|---|---|
| Explain the guest/account split up front on `/welcome` | Put the product first; explain at the moment of value | 48% vs 85% import-start gap sits entirely at step 1 [CITED: reports/growth/growth-recommendations-2026-09-15.md §2 finding 2] |
| Train is a registered-only feature (189 D-05) | Train is the guest's daily loop, warm-up-only until they have analyzed games | Phase 206's sharp filler + red herrings made a zero-material session real |
| Guest Train state provably empty | Guest Train state real, and purged with the games at 30 days | D-08 |
| Sign-up CTA as a dedicated gate screen | Sign-up CTA as a bot-voiced ask inside the flow | Phase 222/223 established the persona bubble as the app's voice |

**Deprecated by this phase:**
- `welcomeDismissal.ts` and the `welcome_dismissed` localStorage key — gone. Note there is no cleanup path for the key already written in existing browsers; it simply becomes inert (acceptable, no PII).
- `TrainGuestGate.tsx` and the `train-gate` umami source — the `signup-cta` source `train-gate` stops being emitted. Historical Umami rows keep it; the baseline note should say so.
- `welcome` as a `signup-cta` source **survives** (the rewritten page keeps its button) [VERIFIED: `frontend/src/pages/Welcome.tsx:192-195`].

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Wording of every new string is unspecified; the examples above are illustrative placeholders, not approved copy | Code Examples | Low — CONTEXT lists exact wording as Claude's discretion; UAT will catch tone |
| A2 | The guest row on the Activity Train card is better as table columns than a new chart | Finding J | Low — reversible; driven by the `check-activity-layout` harness surface |
| A3 | Prod numbers for the baseline note cannot be produced from this environment (no tunnel open, Umami credentials not readable) | Environment Availability | Medium — if wrong, one manual step disappears; if right, the plan needs an operator checkpoint |
| A4 | Deleting `drill_sessions` in `_purge_guest` cannot deadlock against a concurrent compose (the purge re-checks eligibility and a 30-day-idle guest is by definition not composing) | Finding G | Low — worst case an `IntegrityError` caught by the per-guest try/except that already exists |
| A5 | No `alembic` migration is needed anywhere in this phase | throughout | Low — no schema change was identified in any decision |

## Open Questions (RESOLVED)

> All four resolved at plan-phase on 2026-09-17: Q1 → CONTEXT D-13 / GUESTACT-15 (plan 04 task 3); Q2 → leave `useTrainProgress`/`showTrainDot` gated (plan 01 discretion note, recorded as a prohibition); Q3 → Umami `/welcome` landings read at a blocking human checkpoint (plan 03 task 4); Q4 → `reports/growth/guest-activation-baseline-2026-09-17.md`, committed pre-merge (plan 03 task 3).

1. **The `TrainScheduleSettings` reminder toggle + QR block for guests (Pitfall 2).** RESOLVED: D-13 / GUESTACT-15, plan 04 task 3.
   - What we know: S-3 forbids reminder slot / QR / push **for guests** and gives the reason (a push promise for a purged account cannot be kept); the reminder fan-out hard-filters guests, so a guest who enables it gets nothing; the landing screen renders this card to guests after D-01.
   - What's unclear: CONTEXT scopes S-3 to the score screen and does not mention the settings card. Silently extending it is a scope addition; leaving it is a shipped silent lie.
   - Recommendation: **treat it as in-scope** and gate `showReminderBlock` + the QR branch on `!isGuest`, mint it as its own requirement (GUESTACT-15), and flag it in the plan's first checkpoint for a one-line user confirmation. It is 2 lines and squarely inside SC 3's spirit.

2. **`useTrainProgress` for guests / 0-game accounts (CONTEXT's Claude's-discretion item).** RESOLVED: leave both gated; plan 01 discretion + prohibition.
   - What we know: `App.tsx:218` enables it on `navUnlocked && profile != null && !profile.is_guest`; `navUnlocked = totalGames > 0 && tier1` [VERIFIED: `App.tsx:206`]. The badge value is `waiting_count`, which is 0 for every warm-up-only account by construction. The 403 reason for the guest clause disappears with the gate.
   - Recommendation: **leave both clauses as they are.** Enabling it buys a badge that is provably always 0 and costs one request per app load for the exact cohort the phase is trying not to slow down. Same for `showTrainDot` (gated on `navUnlocked`): leaving it means 0-game accounts get no "reworked Train" dot, which matches D-02's "discovery = the unlocked nav item only".

3. **How the `/welcome`-landings baseline is actually read.** RESOLVED: blocking human checkpoint, plan 03 task 4.
   - What we know: the number is Umami-sourced; Umami runs on its own database on the prod Postgres instance [VERIFIED: `docker-compose.yml` umami `DATABASE_URL: postgresql://${UMAMI_DB_USER}:${UMAMI_DB_PASSWORD}@db:5432/umami`]; the `flawchess-prod-db` MCP server points at a dedicated read-only role on the app database [VERIFIED: `docs/dev-tooling.md:29`]; the credentials live in `.env`, which the secret-read-guard hook denies (MEMORY `project_env_example_deny_rule`).
   - Recommendation: plan the `/welcome` landings number as an **operator checkpoint** (read it from the Umami UI at `analytics.flawchess.com`, or via `ssh flawchess` + `docker compose exec`), and commit the query text next to the number in the baseline note so the "after" reading is reproducible. Do not plan an automated fetch.

4. **Does the baseline note go under `reports/growth/` before or after merge?** RESOLVED: `reports/growth/guest-activation-baseline-2026-09-17.md`, plan 03 task 3.
   - CONTEXT D-10 says "before merge"; `reports/growth/` currently holds exactly one file. Recommendation: same directory, `guest-activation-baseline-<YYYY-MM-DD>.md`, committed in the metrics slice, with the pre-merge numbers filled in at the checkpoint (an empty-numbers file merged is a silent failure of SC 10).

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Dev PostgreSQL (docker compose dev) | backend tests | assumed ✓ (standard workflow) | PG 18 | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| `uv` toolchain | ruff / ty / pytest | ✓ | — | — |
| Node + npm (frontend) | lint / build / vitest | ✓ (`npx eslint` ran successfully this session) | — | — |
| `mcp__flawchess-prod-db__query` + `bin/prod_db_tunnel.sh` | lever-A import-start and lever-B baselines | ✗ not open in this session | — | Operator opens the tunnel at the metrics checkpoint |
| Umami DB / UI | `/welcome` landings baseline | ✗ (separate DB, credentials in `.env`, hook-denied) | — | Read from the Umami UI, or via `ssh flawchess`; **record as a human checkpoint** |
| `scripts/reset_train_state.py` | dev smoke of the guest Train loop after dev-clock travel | ✓ (file present) | — | — |
| Dev clock (`X-Dev-Clock-Offset-Minutes`) | weekday-cadence leg of SC 2 | ✓ (`app/core/dev_clock.py`, dev-only) | — | — |

**Missing dependencies with no fallback:** none — nothing blocks code execution.
**Missing dependencies with fallback:** prod DB + Umami reads; both become operator checkpoints in the metrics slice, not blockers for slices A–D.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Backend framework | pytest + pytest-asyncio, per-session cloned PostgreSQL template |
| Backend config | `pyproject.toml` (`addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`) |
| Backend quick run | `uv run pytest tests/routers/test_train.py tests/test_guest_cleanup_service.py -x` |
| Backend full suite | `uv run pytest -n auto -x` (CI runs serial: `uv run pytest`) |
| Frontend framework | Vitest (jsdom per-file pragma) + @testing-library/react |
| Frontend config | `frontend/vite.config.ts` `test:` block (`testTimeout`, `setupFiles: ['src/vitest.setup.ts']`) — never add per-file timeouts (MEMORY) |
| Frontend quick run | `cd frontend && npm test -- --run src/<path>` |
| Frontend full suite | `cd frontend && npm test -- --run` |
| Type check | `uv run ty check app/ tests/ scripts/` and `cd frontend && npm run build` |
| Extra gates | `uv run ruff check . --fix`, `uv run ruff format app/ tests/ scripts/ analysis/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200`, `cd frontend && npm run lint && npm run knip` |

### Proposed requirement IDs → test map

| Req ID | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| GUESTACT-01 | No code path forces `/welcome`; `welcomeDismissal.ts` gone | unit | `cd frontend && npm test -- --run src/pages/__tests__/Home.redirect.test.tsx` | ❌ Wave 0 (no Home test exists today — verified) |
| GUESTACT-02 | `/train` reachable with zero games; nav item unlocked for everyone | unit | `cd frontend && npm test -- --run src/App.test.tsx` | ✅ rewrite `:495-551` + null-profile case |
| GUESTACT-03 | All seven `/train/*` handlers return 2xx for a guest | integration | `uv run pytest tests/routers/test_train.py -k guest -x` | ✅ invert 4 tests (`:967`, `:2551`, `:2580`, `:2992`); add solve + reveal coverage |
| GUESTACT-04 | Guest completes a warm-up session; `drill_sessions` row + streak persist; weekday cadence next visit | integration | `uv run pytest tests/routers/test_train.py -k guest_session -x` | ❌ Wave 0 |
| GUESTACT-05 | Guest score screen: sign-up ask in `actions`, no reminder ask / QR / push; registered screen unchanged | unit | `cd frontend && npm test -- --run src/components/train/__tests__/TrainScoreScreen.test.tsx` | ✅ extend (488 LOC, mocks `useTrainReminderSlot`/`useTrainSettings` already) |
| GUESTACT-06 | Promotion preserves `drill_sessions`/`train_settings`/streak/solves | integration | `uv run pytest tests/test_guest_auth.py -k promotion -x` | ✅ extend beside `test_data_preserved_after_promotion` (`:614`) |
| GUESTACT-07 | Import page renders the friendly-bot bubble for guests; old testids gone | unit | `cd frontend && npm test -- --run src/pages/__tests__/Import.guestPromo.test.tsx` | ❌ Wave 0 (no test covers `import-guest-promo-*` today — verified by grep) |
| GUESTACT-08 | `/welcome` renders four deltas + one Sign-up button; table gone | unit | `cd frontend && npm test -- --run src/pages/__tests__/Welcome.test.tsx` | ✅ rewrite (117 LOC; 3 of its 7 tests target the deleted helper) |
| GUESTACT-09 | Games-less copy: import first, then sign up; no "your own positions" for a 0-game account | unit | `cd frontend && npm test -- --run src/lib/__tests__/trainBotCopy.test.ts` | ✅ extend `describe('scoreBubbleCopy')` (`:509`) + a new `introSteps`/`TrainStartScreen` case |
| GUESTACT-10 | Purge deletes a guest's `drill_sessions`/`drill_solves`/`train_settings`, including a filler solve with `game_id IS NULL` | integration | `uv run pytest tests/test_guest_cleanup_service.py -k drill -x` | ✅ rewrite `test_purge_guest_cascades_drill_rows` (`:418`) |
| GUESTACT-11 | `signup-cta` carries `train-score` and `import-promo` sources | unit | covered by GUESTACT-05 + GUESTACT-07 assertions on `data-umami-event-source` | ✅/❌ |
| GUESTACT-12 | Baseline note exists with committed SQL and pre-merge numbers | manual | human checkpoint + file presence | ❌ Wave 0 (operator) |
| GUESTACT-13 | Activity payload exposes the guest Train row; purged users excluded | integration | `uv run pytest tests/test_admin_activity_stats.py -x` | ✅ extend + update `fake_payload` (`:103`) |
| GUESTACT-14 | `POST /auth/guest` still rate-limited 5/hour on the resolved client IP | integration | `uv run pytest tests/test_guest_auth.py -k rate_limit -x` | ✅ exists (`:287`) — assert-only, no change |
| GUESTACT-15 | *(if adopted, Open Question 1)* No reminder toggle / QR block renders for a guest | unit | `cd frontend && npm test -- --run src/components/train/__tests__/TrainScheduleSettings.test.tsx` | ✅ extend |

### Sampling rate
- **Per task commit:** the single quick command for the file(s) touched (from the table above).
- **Per wave merge:** `uv run pytest -n auto -x` **and** `cd frontend && npm run lint && npm run build && npm test -- --run`.
- **Phase gate:** full pre-merge gate from CLAUDE.md (formatter, ruff --fix, ty ×2, `check_function_size.py`, pytest -n auto -x, frontend lint+test) **plus** `npm run knip` (file deletions) and `npm run build` (shared type changes). Then `/gsd-verify-work`.

### Wave 0 gaps
- [ ] `frontend/src/pages/__tests__/Home.redirect.test.tsx` — covers GUESTACT-01 (none exists; `HomePage` has zero test coverage today)
- [ ] `frontend/src/pages/__tests__/Import.guestPromo.test.tsx` — covers GUESTACT-07
- [ ] Guest end-to-end session test in `tests/routers/test_train.py` — covers GUESTACT-04 (the existing `_set_guest` helper at `:390` makes this cheap)
- [ ] Delete `frontend/src/pages/__tests__/Train.guestGate.test.tsx` (293 LOC) — closes the 215 deferred flake
- [ ] No new framework install needed

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (the key is absent), so this
section is included.

### Applicable ASVS categories

| ASVS category | Applies | Standard control in this phase |
|---|---|---|
| V1 Architecture | yes | Authorization stays at the router; no client-side authz is introduced. Removing `_reject_guest` **widens** an authorization boundary — it must be a deliberate, reviewed removal, which it is (ROADMAP + CONTEXT) |
| V2 Authentication | yes | Unchanged. Guest JWT (30-day) and promotion flow untouched |
| V3 Session Management | yes | `logoutForPromotion()` clears `auth_token` and the query cache before the hard nav; `promote_intent` is the only promotion signal [VERIFIED: `useAuth.ts:170-182`] — do not reintroduce gating on `guest_token` presence (the documented 2026-06-23 regression) |
| V4 Access Control | **yes — the phase's core risk** | Every `/train/*` handler still scopes by `user.id` from `current_active_user`; `load_session_puzzles` filters by `user_id` IN ADDITION to `session_id` as an explicit IDOR guard [VERIFIED: `train_repository.py` docstring: "a session id arriving from a request body/path parameter is untrusted client input (T-189-12 / V4 IDOR guard)"]. Removing the guest gate does NOT weaken per-user scoping — verify no new handler trusts a client-supplied user id |
| V5 Input Validation | yes | No new request bodies. `TrainSettingsUpdate` unchanged |
| V6 Cryptography | no | Nothing cryptographic changes |
| V7 Error handling / logging | yes | Existing `sentry_sdk.capture_exception()` blocks in `train.py` sit after the removed gate and stay intact. Note the removal **eliminates** the FLAWCHESS-64 403 source |
| V11 Business logic | yes | Guest resource consumption: the herring pool is now reachable by throwaway accounts. Backstop verified (Finding H): 5 guest accounts/hour/IP + one session per day. No new ceiling per D-09 |
| V13 API | yes | No new endpoint; seven existing endpoints widen their audience |

### Known threat patterns for this change

| Pattern | STRIDE | Standard mitigation | Status |
|---|---|---|---|
| Guest account farming to mine the cross-user herring pool | Information disclosure / DoS | Per-IP guest-creation limiter on the Cloudflare-resolved client IP | ✅ verified (Finding H) |
| Guest floods composition to burn DB/CPU | DoS | One open session per user enforced by a partial unique index [VERIFIED: `app/models/drill_session.py:53-61` — `Index("uq_drill_sessions_user_open", "user_id", unique=True, postgresql_where=text("status = 'open'"))`] + daily window | ✅ existing |
| Guest reads another user's session | Information disclosure | `user_id` predicate on every session query (V4 above) | ✅ existing, unchanged |
| Guest persists a push subscription that is never honored | Repudiation / broken promise | Gate the reminder UI (Open Question 1); the fan-out filter already excludes guests | ⚠️ needs the decision |
| Purged guest's Train history lingering after the advertised 30-day cleanup | Privacy / data-retention promise | D-08 deletes | ⚠️ this phase's job |
| Limiter reset on deploy restart | DoS (window) | Accepted, documented in the module | ℹ️ note only |

## Sources

### Primary (HIGH confidence — files opened this session)
- `app/routers/train.py` (gate + 7 call sites + docstring), `app/services/guest_service.py`, `app/services/guest_cleanup_service.py`, `app/core/ip_rate_limiter.py`, `app/routers/auth.py`, `app/repositories/train_repository.py`, `app/repositories/train_reminder_repository.py`, `app/services/train_pool.py`, `app/services/eval_queue_service.py`, `app/services/activity_queries.py`, `app/services/activity_stats.py`
- `app/models/{drill_session,drill_solve,drill_item,train_settings,user,herring_pool}.py`
- `frontend/src/pages/{Home,Welcome,Import,Train}.tsx`, `frontend/src/App.tsx`, `frontend/src/lib/{welcomeDismissal,trainBotCopy,analytics}.ts`, `frontend/src/hooks/useAuth.ts`
- `frontend/src/components/train/{TrainBotBubble,TrainGuestGate,TrainScoreScreen,TrainStartScreen,TrainScheduleSettings,TrainReminderButton,TrainReminderResurfaceBanner}.tsx`
- `frontend/src/components/library/{NoEngineAnalysisFlawsState,EvalCoverageBadge}.tsx`
- Tests: `tests/routers/test_train.py`, `tests/test_guest_cleanup_service.py`, `tests/test_guest_auth.py`, `tests/test_guest_google_promotion.py`, `tests/test_admin_activity_stats.py`, `frontend/src/App.test.tsx`, `frontend/src/pages/__tests__/{Welcome,Train.guestGate}.test.tsx`, `frontend/src/lib/__tests__/trainBotCopy.test.ts`, `frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx`
- Infra: `deploy/Caddyfile`, `deploy/entrypoint.sh`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `frontend/{package.json,vite.config.ts,eslint.config.js}`, `pyproject.toml`
- Measurements: `npx eslint --no-inline-config --rule 'complexity: ["error", 1]' …` (run this session), `.venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"`, `grep -c "temperament: …"`
- Third-party source read: `.venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py`

### Secondary (MEDIUM confidence — project documents)
- `.planning/phases/224-.../224-CONTEXT.md`, `.planning/seeds/SEED-169-*.md`, `.planning/ROADMAP.md` §Phase 224, `.planning/STATE.md`
- `reports/growth/growth-recommendations-2026-09-15.md` (with the 2026-09-17 correction)
- `.planning/milestones/v2.15-phases/215-frontend-god-file-decomposition/deferred-items.md`
- `CLAUDE.md`, `frontend/CLAUDE.md`, `docs/dev-tooling.md`

### Tertiary (LOW confidence)
- None. No web search or external documentation lookup was performed or needed: this phase adds no dependency and touches no third-party API.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every reused module read at source
- Architecture / call sites: HIGH — every line number and quote verified against the file this session
- Pitfalls: HIGH for 1, 2, 4, 5, 6, 8 (measured or quoted); MEDIUM for 3 (byte-identical is a review property, not a measurable one)
- Metrics / SQL: MEDIUM — schema and predicates verified in-repo; the draft SQL has NOT been executed against prod (no tunnel this session)
- Environment: MEDIUM — prod/Umami availability inferred from config, not probed

**Research date:** 2026-09-17
**Valid until:** 2026-10-17 (in-repo facts; invalidated by any edit to `app/routers/train.py`, `frontend/src/pages/Train.tsx`, `TrainScoreScreen.tsx`, `Import.tsx` or `activity_queries.py`)
