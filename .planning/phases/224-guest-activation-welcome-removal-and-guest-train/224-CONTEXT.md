# Phase 224: Guest Activation — Welcome Removal & Guest Train (SEED-169) - Context

**Gathered:** 2026-09-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Two levers on the guest funnel, measured separately. Lever A: stop forcing 0-game guests
through `/welcome`; `Home.tsx` sends them to `/library/import` like everyone else and
`welcomeDismissal.ts` goes away. Lever B: open Train to guests as the FULL daily warm-up loop
(sessions, streaks, `drill_sessions`/`train_settings`, weekday cadence; reverses Phase 189
D-05), and move the sign-up ask to bot bubbles on the Train score screen and the Import page,
each with a "Why?" + "Sign up free" pair. `/welcome` becomes a short four-delta "What changes
when you sign up" page reachable only from "Why?" and a plain URL. Guest cleanup is
re-reasoned for guest Train rows. Baselines for both levers are recorded before merge and
readable after.

Out of scope (ROADMAP): push reminders for guests; any change to the registered-user score
bubble, reminder slot or QR block; a one-shot demo-session variant; a new milestone or roadmap
regrouping.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from SEED-169 (locked 2026-09-17 in /gsd-explore, not re-opened)
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

### Zero-game Train entry (discussed)
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

### Bot voice for the sign-up ask (discussed)
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

### Purged-guest Train state (discussed)
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

### Metric recording (discussed)
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

### Train settings card for guests (decided at plan-phase, 2026-09-17)
- **D-13:** **`TrainScheduleSettings` hides the reminder toggle and the QR/install block for
  guests.** Research (224-RESEARCH.md Open Question 1) found that D-01 exposes the Train
  landing, and with it this card, to guests, while the reminder fan-out
  (`train_reminder_repository.py`, `User.is_guest.is_(False)`) never sends to a guest: an
  enabled toggle would be a silent lie. S-3's rule (no reminder slot, QR block or push prompt
  for guests) therefore applies to the landing card as well as the score screen. Gate
  `showReminderBlock` and the QR/install branch on `!isGuest`; the rest of the card
  (weekday cadence) stays. Own requirement ID (GUESTACT-15). Owner confirmed at the
  plan-phase gate.

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-169-guest-activation-welcome-removal-and-guest-train.md` — the seven
  locked decisions (S-1..S-7), symptom table, "facts the plan must respect" (in-place
  promotion, cleanup assumption, cross-user herring pool, warm-up copy, FLAWCHESS-64,
  tests to touch).
- `.planning/ROADMAP.md` §"Phase 224" — goal, ten success criteria, out-of-scope list.
- `reports/growth/growth-recommendations-2026-09-15.md` finding 2 — the funnel numbers
  the baselines are compared against (corrected 2026-09-17 in the seed).

### Prior Train phase decisions being reversed or relied on
- `.planning/milestones/v2.9-phases/189-pool-scheduler-backend/189-02-PLAN.md` and `189-VERIFICATION.md` — D-04
  (session history is user progress) and D-05 (`_reject_guest`), the guest gate this phase
  removes.
- `.planning/milestones/v2.13-phases/206-train-warmup-sharp-filler/206-CONTEXT.md` — D-06..D-09
  warm-up label semantics (one server flag, persisted on `drill_sessions`, start screen
  placement), D-14 filler serve order, D-15 `record_solve` branching on `source`.
- `.planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-CONTEXT.md`
  — D-08/D-09 bot copy rules (tone, accuracy rule, no em-dashes); D-04 here deliberately does
  NOT adopt its per-persona table shape.
- `.planning/milestones/v2.15-phases/215-frontend-god-file-decomposition/deferred-items.md` — the `Train.guestGate.test.tsx`
  contamination flake that deletion of the gate closes.

### Guest lifecycle
- `app/services/guest_cleanup_service.py` — purge scope (games, import jobs, derived stats;
  User row survives, 187 D-05); D-08 adds the Train-row deletes here.
- `app/services/guest_service.py` — `promote_guest_with_password` /
  `promote_guest_with_google` UPDATE the same row (`is_guest=False`, `promoted_at=now()`);
  the sign-up copy may promise that Train state carries over.
- `app/core/ip_rate_limiter.py`, `app/routers/auth.py` ~314 — `guest_create_limiter`, the
  D-09 backstop.

### Metrics
- `app/services/activity_queries.py` — `_GUEST_COHORT`, `fetch_funnel` (lever A already
  readable, purged users excluded), `fetch_train`, `fetch_train_funnel`,
  `fetch_purged_excluded`; D-10..D-12 extend this module.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TrainBotBubble` (`frontend/src/components/train/TrainBotBubble.tsx`): `persona`, `state`,
  `children`, `actions` (right-aligned, wraps, `mt-2`) — hosts both new sign-up asks.
- `pickBot(temperament)` (`frontend/src/lib/trainBotCopy.ts`): pools are 7 smart, 9 friendly,
  8 stern; `TrainScoreScreen` memoises `pickBot('smart')` once per mount.
- `scoreBubbleCopy` / `ScoreBubbleInput` (`trainBotCopy.ts` ~680): four-variant precedence
  (warm-up first); the guest branch slots into the warm-up variant.
- `introSteps(sideToMove, isWarmup)` (`trainBotCopy.ts` ~277) and `returnPhrase` (~426):
  the D-03 copy branch points.
- `TrainStartScreen.tsx` ~98: the warm-up banner body string; `TrainEmptyBody`'s
  `no_material` state ("Import & analyze your games") never fires once compose serves filler,
  but its copy is the existing import-CTA precedent.
- `logoutForPromotion()` (`frontend/src/hooks/useAuth.ts`) + `window.location.href =
  '/login?tab=register'`: the promotion flow used by `Welcome.tsx`, `Import.tsx`,
  `TrainGuestGate.tsx`.
- `trackEvent('signup-cta', { source })` (`frontend/src/lib/analytics.ts`) and the
  `data-umami-event` / `data-umami-event-source` attribute pattern (`Import.tsx` ~426).
- `EmptyState`, `Alert`, `Button` variants `default` / `brand-outline`; `TRAIN_BUTTON_CLASS`.

### Established Patterns
- Guest gating in the frontend reads `useUserProfile().data.is_guest` (Train.tsx:66
  comment, FLAWCHESS-64). `useAuth().user` is always null.
- Import lock: `IMPORT_EXEMPT_ROUTES` + `isNavLocked()` (App.tsx ~160) for nav styling, and
  `ImportRequiredRoute` (App.tsx ~791) for the route; both keyed on
  `totalGames > 0 && tier1`. D-01 touches both for `/train`.
- Compose (`app/repositories/train_repository.py::compose_and_materialize_session`) has no
  guest or rating branch; `_stamp_pool_eligibility` counts `sharp_filler_available()` as
  material so warm-up-only users accrue streak.
- `_pool_state` returns `no_material` only when there are no drill items, no pool candidates
  and no pending blobs; with filler always available the empty landing state is unreachable.
- Every non-trivial `except` in services/routers calls `sentry_sdk.capture_exception()`;
  removing `_reject_guest` also removes the FLAWCHESS-64 403 source, so the `enabled:
  !is_guest` guards in `App.tsx` exist only for push hooks after this phase.
- Activity SQL lives as raw strings in `activity_queries.py` with `_GUEST_COHORT` and
  `games_purged_at IS NULL` predicates; cards are rendered by `frontend/src/pages/activity/`.

### Integration Points
- `frontend/src/pages/Home.tsx` ~777-784 (redirect), `frontend/src/lib/welcomeDismissal.ts`
  (delete), `frontend/src/pages/Welcome.tsx` (rewrite), `frontend/src/pages/Import.tsx`
  ~419-433 (alert → bubble), `frontend/src/pages/Train.tsx` ~70-84 and ~176-186 (`canTrain`,
  guest gate), `frontend/src/components/train/TrainScoreScreen.tsx` (guest branch: bubble
  actions, suppress `useTrainReminderSlot` output and `resolveReminderAsk`),
  `frontend/src/App.tsx` (`IMPORT_EXEMPT_ROUTES`, `/train/*` route, `useTrainProgress`
  enable).
- `app/routers/train.py` (`_reject_guest` + seven call sites and the module docstring),
  `app/services/guest_cleanup_service.py` (D-08 deletes),
  `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows`,
  `tests/test_train_router.py` or equivalent guest-403 tests (invert to 200).
- `app/services/activity_queries.py` + `activity_stats.py` + `frontend/src/pages/activity/`
  (D-10 guest Train row).
- `reports/growth/` (D-10 baseline note); `CHANGELOG.md` `[Unreleased]`.

</code_context>

<specifics>
## Specific Ideas

- Guest copy order is fixed: import first, then sign up ("import, then sign up, in that
  order", ROADMAP SC 7).
- Registered-user score screen must be byte-identical to before (ROADMAP SC 3); the guest
  branch is additive and guarded.
- The `/welcome` "no 30-day inactivity purge" delta is now literally true for Train state
  too (D-08).
- Baselines are prod numbers taken over the tunnel before merge, with the SQL committed
  next to them so the after-reading is the same query.

</specifics>

<deferred>
## Deferred Ideas

- Return-to-`/train` after sign-up from the score screen (D-07 rejected for now; revisit if
  promotion rate from `train-score` is high but Train retention after promotion is not).
- Import bubble pitching Train / a "Try Train" third button (D-02 rejected; keeps lever A and
  B surfaces separate for measurement).
- A guest-specific Train ceiling or filler-only mode (D-09 rejected unless the herring pool
  shows abuse).

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — keyword match on "score";
  unrelated Tailwind class bug on the Score Y-axis label.
- `172-deferred-review-findings.md` — Phase 172 review leftovers, no overlap.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — database idea, unrelated.
- `2026-08-29-variation-tree-nested-button.md` — analysis-board markup nit, unrelated.

</deferred>

---

*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Context gathered: 2026-09-17*
