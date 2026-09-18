---
phase: 224-guest-activation-welcome-removal-and-guest-train
verified: 2026-09-18T06:10:00Z
status: human_needed
score: 10/10 ROADMAP success criteria structurally verified (16/16 GUESTACT requirements satisfied); 2 items routed to human verification (1 external-data reading pending by explicit user decision, 1 visual spot-check recommended)
behavior_unverified: 0
overrides_applied: 0
covered_files:
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-01-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-01-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-02-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-02-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-03-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-03-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-04-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-04-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-05-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-05-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-06-PLAN.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-06-SUMMARY.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-CONTEXT.md
  - .planning/phases/224-guest-activation-welcome-removal-and-guest-train/224-RESEARCH.md
  - app/routers/train.py
  - tests/routers/test_train.py
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/hooks/useUserProfile.ts
  - frontend/src/pages/Home.tsx
  - frontend/src/pages/Welcome.tsx
  - frontend/src/pages/__tests__/Welcome.test.tsx
  - frontend/src/pages/__tests__/Home.redirect.test.tsx
  - frontend/src/lib/botGameSnapshot.ts
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - tests/test_admin_activity_stats.py
  - frontend/src/pages/activity/render.js
  - frontend/src/pages/activity/ActivityPage.tsx
  - reports/growth/guest-activation-baseline-2026-09-17.md
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  - app/services/guest_cleanup_service.py
  - app/repositories/train_reminder_repository.py
  - tests/test_guest_cleanup_service.py
  - tests/test_guest_auth.py
  - frontend/src/components/train/SignupAskActions.tsx
  - frontend/src/components/train/__tests__/SignupAskActions.test.tsx
  - frontend/src/components/import/ImportGuestPromoBubble.tsx
  - frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx
  - frontend/src/pages/Import.tsx
  - CHANGELOG.md
covered_digest: "v1:sha256:e310d42d08ef6d85e77d72383e42f0d6bf3694b7e0d5c0e3e316efafc7c68817"
human_verification:
  - test: "Read /welcome pageviews and the home-visitor denominator from Umami (analytics.flawchess.com) for the window 2026-06-19..2026-09-17, and paste them into reports/growth/guest-activation-baseline-2026-09-17.md's 'Lever A, metric 2' section, replacing the PENDING OPERATOR READING placeholder."
    expected: "The note's 'Lever A, metric 2' result line contains real landings/denominator numbers and a percentage instead of the placeholder; grep -c 'PENDING OPERATOR READING' returns 0."
    why_human: "Umami runs on a separate database whose credentials live in .env, which the project's secret-read guard denies to any agent; this was deferred to the end-of-phase test by the user's own decision (224-03-SUMMARY.md), not an oversight. All three prod-DB numbers and the query SQL are already committed."
  - test: "Visually load the guest Train score screen and the registered Train score screen side by side (or before/after this phase on a registered account) and confirm the registered layout, spacing and copy are pixel-identical to pre-phase, and that the guest bubble's Why?/Sign up free buttons render correctly styled (brand-outline then default) with no reminder/QR content bleeding through."
    expected: "Registered screen looks unchanged; guest screen shows the bot bubble with the sign-up ask and the two buttons, Done alone below, no reminder switch, no QR code, no push prompt."
    why_human: "Automated tests assert DOM structure and the absence of the `.justify-end` actions row / btn-signup- elements for the registered case, and presence of the two testids for guest, but not pixel rendering, spacing or actual button styling. The phase's own ui.plan-gate was deliberately overridden (224-GATE-OVERRIDE.md) on the basis that no new visual layout is introduced beyond CONTEXT.md's locked decisions — a quick visual pass confirms that holds in the browser."
---

# Phase 224: Guest Activation — Welcome Removal & Guest Train Verification Report

**Phase Goal:** Stop new guests from hitting an upsell-shaped interstitial before the product, and
open Train, the one feature built to bring the same person back daily, to guests (two independently
measured levers: A = guest → start an import, B = guest → register).

**Verified:** 2026-09-18
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–10)

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | Fresh 0-game guest clicking home CTA lands on `/library/import`; no code path forces `/welcome`; `welcomeDismissal.ts` gone | ✓ VERIFIED | `frontend/src/pages/Home.tsx` has exactly one `<Navigate>` (`hasGames ? '/library/games' : '/library/import'`); `frontend/src/lib/welcomeDismissal.ts` does not exist, no reference to it anywhere under `frontend/src`; `Home.redirect.test.tsx` (4 tests) passing, including an explicit "never produces `/welcome`" assertion |
| 2 | A zero-game guest completes a full Train warm-up session end to end (start, solve, score) with no gate; a `drill_sessions` row plus streak persist; same guest gets the weekday cadence on the next visit | ✓ VERIFIED | `_reject_guest` removed from `app/routers/train.py` and all 7 call sites (`grep -c` → 0 in both the router and its test file); `test_guest_zero_game_warmup_end_to_end` composes a filler-only session with zero games/drill items, solves every puzzle, reads `session_streak_count` 0→1 from `/train/progress`, and round-trips a `weekday_mask` through `/train/settings` — ran this session, 1 passed. Nav/route exemption confirmed (`/train` in `IMPORT_EXEMPT_ROUTES`, no `ImportRequiredRoute` wrapper on `/train/*`); `App.test.tsx`'s inverted nav-gating tests pass (Openings/Endgames stay locked as the control) |
| 3 | Guest score screen bot bubble carries the sign-up ask with "Why?"/"Sign up free" in `actions`; no reminder ask, QR/install block or push prompt renders; registered screen byte-identical | ✓ VERIFIED (DOM-level) | `TrainScoreScreen.tsx`: `actions={isGuest ? <SignupAskActions source="train-score" /> : undefined}`; reminder control/below-row wrapped in guard components that render `null` for guests; `useTrainReminderSlot()` still called unconditionally (rules of hooks respected). `TrainScoreScreen.test.tsx`'s "the guest branch" describe block (4 tests, ran this session) asserts guest renders both signup testids + `GUEST_SIGNUP_ASK_SCORE` text and neither reminder stub; registered fixture renders no `btn-signup-` element and no `.justify-end` actions row (byte-identity proxy). True pixel-level visual identity is a human item (see Human Verification) |
| 4 | Signing up from the button promotes the guest in place: `drill_sessions`, `train_settings`, streak and solves still attached afterward | ✓ VERIFIED | `test_train_state_preserved_after_promotion` (tests/test_guest_auth.py) composes a session as guest, solves to streak 1, promotes via `/auth/guest/promote/email`, and asserts unchanged user id, `is_guest=False`, and surviving `drill_sessions`/`drill_solves`/`train_settings` rows plus unchanged streak — ran this session, passing (part of the 65-test run below) |
| 5 | Import page shows a friendly-bot `TrainBotBubble` with the same button pair on every guest visit; old `Alert` and its testids gone | ✓ VERIFIED | `frontend/src/components/import/ImportGuestPromoBubble.tsx` exists, exports `ImportGuestPromoBubble`/`IMPORT_GUEST_SIGNUP_COPY`, uses `useMemo(() => pickBot('friendly'), [])`; `Import.tsx` renders `{profile?.is_guest && <ImportGuestPromoBubble />}` and contains no `import-guest-promo-info`/`import-guest-promo-link`; `ImportGuestPromoBubble.test.tsx` (4 tests) + the three pre-existing Import state-machine/queued/paste-handoff suites all pass |
| 6 | `/welcome` renders the four-delta page with a single "Sign up free" button; old comparison table gone | ✓ VERIFIED | `Welcome.tsx` rewritten: `DELTAS` array of 4 named constants rendered under `welcome-delta-list`/`welcome-delta-1..4`; no `VALUE_ROWS`, no `<table`, no dismissal checkbox; guest-only `welcome-btn-signup` (`data-umami-event-source="welcome"`) + universal `welcome-btn-back`; `Welcome.test.tsx` (6 tests) passing |
| 7 | Guest warm-up copy no longer promises "your own positions"; guest branch of `WARMUP_TAIL`/`INTRO_WARMUP` says import, then sign up, in that order | ✓ VERIFIED | `trainBotCopy.ts`'s `TrainCopyAudience`/`audienceKey` resolver plus 4 audience-keyed `Record<CopyAudienceKey, string>` tables (`has_games` entries byte-identical to the pre-phase strings); `trainBotCopy.test.ts` (27 new tests, ran this session as part of the 240-test frontend batch) assert no zero-game string contains "analyzing", no `no_games` (registered) string mentions signing up, and every `no_games_guest` string reads import before sign up |
| 8 | Guest cleanup re-reasoned and documented: `guest_cleanup_service.py` and the purge test state explicitly what happens to a purged guest's Train rows, and the test proves it | ✓ VERIFIED | `_purge_guest` now runs `delete(DrillSession)` and `delete(TrainSettings)` in the same transaction as the games cascade (no separate `DrillSolve` delete — relies on `ON DELETE CASCADE`); comment names D-08 and the ON DELETE CASCADE reasoning; module docstring updated. `test_purge_guest_cascades_drill_rows` seeds a `game_id IS NULL`/`source=SHARP_FILLER` solve the games cascade cannot reach plus a `TrainSettings` row, and asserts all counts are 0 post-purge — ran this session, passing |
| 9 | Umami `signup-cta` events carry `data-umami-event-source` `train-score` and `import-promo` | ✓ VERIFIED | `SignupAskActions.tsx`: `data-umami-event="signup-cta"` exactly once, `data-umami-event-source={source}` where `source: 'train-score' \| 'import-promo'`; "Why?" carries no umami attribute (internal navigation, documented CLAUDE.md rule); `SignupAskActions.test.tsx` (7 tests) exercises both sources |
| 10 | Baselines recorded before merge, readable after (4 separate numbers, no combined "guest conversion"); lever A = import-start rate + `/welcome` landings; lever B = promotion rate + guest Train sessions completed | ✓ VERIFIED, 1 item pending human read | `reports/growth/guest-activation-baseline-2026-09-17.md` commits all 4 SQL queries and states "no combined" explicitly; 3 of 4 numbers are real prod reads (lever A metric 1: 125/367 = 34.1%; lever B metric 1: 74/468 = 15.8%; lever B metric 2: 0/0, expected pre-merge). The 4th (lever A metric 2, `/welcome` Umami landings) is `PENDING OPERATOR READING` **by explicit user decision** to read it at the end-of-phase test (224-03-SUMMARY.md), not an oversight — see Human Verification. `fetch_guest_train` is wired into the Activity dashboard's Train card (`#tr-guest-note`), so the after-reading needs no hand-run SQL for lever B metric 2 |

**Score:** 10/10 ROADMAP success criteria structurally verified; 0 failed; 2 items routed to human verification (1 external-data reading intentionally deferred, 1 visual spot-check recommended).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/routers/train.py` | No guest gate; docstring names D-09 backstop | ✓ VERIFIED | `_reject_guest` gone from router + docstring names `guest_create_limiter` and `uq_drill_sessions_user_open` |
| `tests/routers/test_train.py` | Inverted guest tests + e2e warm-up test | ✓ VERIFIED | 5 guest-keyed tests pass (`pytest -k guest`, ran this session) |
| `frontend/src/App.tsx` | `/train` exempt from import lock, both nav and route | ✓ VERIFIED | `IMPORT_EXEMPT_ROUTES` contains `/train`; `/train/*` route unwrapped |
| `frontend/src/lib/welcomeDismissal.ts` | Deleted | ✓ VERIFIED | File absent, zero references |
| `frontend/src/pages/Welcome.tsx` | Four-delta page | ✓ VERIFIED | `welcome-delta-list` + 4 items, guest-only signup button, universal back |
| `app/services/activity_queries.py` | `fetch_guest_train` reader | ✓ VERIFIED | Function present, wired into `build_payload`, tested (26 tests in `test_admin_activity_stats.py`) |
| `reports/growth/guest-activation-baseline-2026-09-17.md` | Baseline note, 4 SQL blocks, real numbers | ✓ VERIFIED (3/4 numbers filled) | 4 fenced SQL blocks present; 3 real reads; 1 `PENDING OPERATOR READING` by design |
| `frontend/src/lib/trainBotCopy.ts` | `TrainCopyAudience` + audience-keyed copy | ✓ VERIFIED | Exports present, `has_games` entries verified byte-identical to pre-phase strings |
| `frontend/src/components/train/TrainScheduleSettings.tsx` | Guest-aware visibility resolver | ✓ VERIFIED | `resolveScheduleCardVisibility` hides reminder block + phone/QR section when `isGuest` |
| `app/services/guest_cleanup_service.py` | Two Train-row deletes | ✓ VERIFIED | `delete(DrillSession)`, `delete(TrainSettings)`, no redundant `delete(DrillSolve)` |
| `frontend/src/components/train/SignupAskActions.tsx` | Shared Why?/Sign up free pair | ✓ VERIFIED | Exports `SignupAskActions`, `SignupAskSource`; umami contract asserted by 7 tests |
| `frontend/src/components/import/ImportGuestPromoBubble.tsx` | Friendly-bot Import bubble | ✓ VERIFIED | Exports present, `pickBot('friendly')` memoised, 4 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `frontend/src/App.tsx` | `frontend/src/pages/Train.tsx` | `/train/*` route unwrapped from `ImportRequiredRoute` | ✓ WIRED | Confirmed by reading `App.tsx`'s route block; `useTrainProgress`/dot gating deliberately left `!is_guest`-gated per Claude's Discretion (unchanged) |
| `frontend/src/pages/Train.tsx` | `app/routers/train.py` | Guest bearer token reaches `POST /train/sessions` and gets 200 | ✓ WIRED | Backend test proves 200 + full session lifecycle |
| `app/services/guest_cleanup_service.py` | `app/models/drill_solve.py` | `delete(DrillSession)` cascades `drill_solves` via `ON DELETE CASCADE` | ✓ WIRED | Test seeds a `game_id IS NULL` solve unreachable by the games cascade and confirms it's deleted (proves the cascade path, not just the session delete) |
| `app/repositories/train_reminder_repository.py` | `app/models/user.py` | `User.is_guest.is_(False)` fan-out filter stays, now load-bearing | ✓ WIRED | Filter unchanged (`git diff` scoped to docstring only, per the plan's own acceptance criterion, re-confirmed via grep) |
| `frontend/src/components/train/TrainScoreScreen.tsx` | `frontend/src/components/train/SignupAskActions.tsx` | `actions={isGuest ? <SignupAskActions source="train-score" /> : undefined}` | ✓ WIRED | Confirmed in source; registered path renders `undefined`, guest path renders the component |
| `frontend/src/pages/Import.tsx` | `frontend/src/components/import/ImportGuestPromoBubble.tsx` | Guest branch renders the bubble instead of the old `Alert` | ✓ WIRED | Confirmed in source and by passing Import test suites |
| `app/services/activity_stats.py` | `app/services/activity_queries.py` | `guest_train=await queries.fetch_guest_train(...)` | ✓ WIRED | Confirmed in source |
| `frontend/src/pages/activity/render.js` | `frontend/src/pages/activity/ActivityPage.tsx` | `#tr-guest-note` write/render pair | ✓ WIRED | Both files contain the id; `npm run check:activity-layout` passes at all 4 phone widths |

### Behavioral Spot-Checks / Test Runs (this session)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Backend guest-gate tests | `uv run pytest tests/routers/test_train.py -k guest -q` | 5 passed | ✓ PASS |
| Backend guest lifecycle + activity stats | `uv run pytest tests/test_guest_cleanup_service.py tests/test_guest_auth.py tests/test_admin_activity_stats.py -q` | 65 passed | ✓ PASS |
| Backend type/lint | `uv run ty check app/ tests/ scripts/` / `uv run ruff check .` | All checks passed / All checks passed | ✓ PASS |
| Frontend targeted suites (8 files) | `npx vitest run src/pages/__tests__/Home.redirect.test.tsx src/pages/__tests__/Welcome.test.tsx src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainScoreScreen.test.tsx src/components/train/__tests__/SignupAskActions.test.tsx src/components/import/__tests__/ImportGuestPromoBubble.test.tsx src/App.test.tsx` | 240 passed | ✓ PASS |
| Frontend production build | `npm run build` | Built successfully (2 prerendered pages, PWA precache) | ✓ PASS |
| Frontend dead-code scan | `npm run knip` | Clean (only a pre-existing config hint) | ✓ PASS |
| Activity dashboard layout gate | `npm run check:activity-layout` | OK at 320/360/390/414px | ✓ PASS |
| Complexity baseline drift (whole phase) | `git diff --quiet $(git merge-base HEAD main)..HEAD -- frontend/eslint.config.js` | No drift | ✓ PASS |
| Full backend/frontend suites | Not re-run by this verifier (already run green by the orchestrator per the task brief: backend 4726 passed, frontend 4327 passed) | — | Trusted per task instructions; targeted re-runs above corroborate no regression in touched areas |

### Requirements Coverage (GUESTACT-01..16, minted at planning time — no active REQUIREMENTS.md)

Per project convention for Phases 204–223 (confirmed: `.planning/REQUIREMENTS.md` does not exist for
the current milestone), requirement IDs are declared only in each PLAN.md's frontmatter and closed
out in the matching SUMMARY.md's `requirements-completed` field. This is **not** a gap — it is the
established brownfield-GSD pattern for this project's milestone cadence.

| Requirement | Plan | Description | Status | Evidence |
|---|---|---|---|---|
| GUESTACT-01 | 224-02 | No code path forces `/welcome`; `welcomeDismissal.ts` deleted | ✓ SATISFIED | `Home.redirect.test.tsx`, file absence confirmed |
| GUESTACT-02 | 224-01 | `/train` opens for any zero-game account (route + nav) | ✓ SATISFIED | `App.tsx` exemption, `App.test.tsx` inversion |
| GUESTACT-03 | 224-01 | `_reject_guest` removed from all 7 handlers + docstring | ✓ SATISFIED | `grep -c "_reject_guest"` → 0 in router and test file |
| GUESTACT-04 | 224-01 | Guest completes full warm-up session; streak/cadence persist | ✓ SATISFIED | `test_guest_zero_game_warmup_end_to_end`, ran passing |
| GUESTACT-05 | 224-06 | Guest score screen sign-up ask; no reminder/QR/push; registered unchanged | ✓ SATISFIED | `TrainScoreScreen.test.tsx` guest-branch block |
| GUESTACT-06 | 224-05 | Promotion preserves Train state | ✓ SATISFIED | `test_train_state_preserved_after_promotion` |
| GUESTACT-07 | 224-06 | Import page friendly-bot bubble; old Alert gone | ✓ SATISFIED | `ImportGuestPromoBubble.test.tsx`, Import.tsx grep |
| GUESTACT-08 | 224-02 | `/welcome` four-delta page + Back affordance | ✓ SATISFIED | `Welcome.tsx`, `Welcome.test.tsx` |
| GUESTACT-09 | 224-04 | Games-less copy branches on `hasGames` × `isGuest`, import before signup | ✓ SATISFIED | `trainBotCopy.test.ts` (27 new tests) |
| GUESTACT-10 | 224-05 | Guest purge deletes Train rows; comments + test state the rule | ✓ SATISFIED | `test_purge_guest_cascades_drill_rows` inverted |
| GUESTACT-11 | 224-06 | `signup-cta` carries `train-score`/`import-promo` sources | ✓ SATISFIED | `SignupAskActions.tsx` + tests |
| GUESTACT-12 | 224-03 | Baseline note under `reports/growth/` with committed SQL + numbers | ✓ SATISFIED (1 human-pending row) | Baseline note, 3/4 rows filled |
| GUESTACT-13 | 224-03 | Activity Train card gains guest-cohort row | ✓ SATISFIED | `fetch_guest_train`, `#tr-guest-note` |
| GUESTACT-14 | 224-01 | Guest-creation limiter confirmed as backstop; no new guard | ✓ SATISFIED | Docstring names `guest_create_limiter`; no new rate-limit code added anywhere in the phase |
| GUESTACT-15 | 224-04 | No reminder toggle/QR block for guest in `TrainScheduleSettings` | ✓ SATISFIED | `resolveScheduleCardVisibility`, `TrainScheduleSettings.test.tsx` |
| GUESTACT-16 | 224-05 | Stale gate-dependent docstrings updated | ✓ SATISFIED | `train_reminder_repository.py` docstring rewritten, filter untouched |

No orphaned requirements found (all 16 IDs proposed in 224-RESEARCH.md are claimed by exactly one plan and closed by its SUMMARY).

### Anti-Patterns Found

None. Scanned all 18 non-test source files touched by this phase for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|coming soon|not yet implemented` — zero matches. No stub returns, no hardcoded-empty props flowing to render, no debt markers requiring a follow-up reference.

### CONTEXT.md Decisions Honored (spot-checked against code)

- S-1/D-01: single redirect rule, `/train` exempt for every zero-game account — confirmed in `App.tsx` and `Home.tsx`.
- S-2: `_reject_guest` and `TrainGuestGate.tsx` removed — confirmed (both files/symbols absent).
- S-3/D-13: no reminder slot, QR/install block or push prompt for guests on either the score screen or the Train landing settings card — confirmed via `TrainScoreScreen.tsx` guard components and `TrainScheduleSettings.tsx`'s `resolveScheduleCardVisibility`; `useReminderResurfaceRedirect`/`useDevicePushResync` remain `!is_guest`-gated in `App.tsx`.
- S-4: button pair "Why?" (`brand-outline`) then "Sign up free" (`default`) — confirmed in `SignupAskActions.tsx`.
- S-5/D-05: `/welcome` four deltas, one button, Back affordance — confirmed.
- S-6/D-06: Import bubble uses `pickBot('friendly')`, import-specific copy distinct from the score-screen ask — confirmed.
- S-7: `signup-cta` sources `train-score`/`import-promo` added, `welcome` unchanged; no combined guest-conversion number anywhere — confirmed in code and in the baseline note.
- D-02: no Train pitch/third button in the Import bubble — confirmed (`ImportGuestPromoBubble.test.tsx` asserts exactly two buttons).
- D-07: no return-to parameter threaded through `promote_intent`/`LoginForm`/`googleAuth.ts` — confirmed (no diff to those files; `SignupAskActions.tsx` lifts the handoff verbatim).
- D-08: purge deletes guest Train rows — confirmed.
- D-09: no new abuse guard — confirmed (no rate-limiter/quota code added anywhere in the phase's diff).
- D-13: `TrainScheduleSettings` hides reminder/QR for guests — confirmed.
- Out-of-scope items respected: no push reminders for guests, no change to the registered score bubble/reminder slot/QR block, no one-shot demo variant, no new milestone/roadmap regrouping.

### Human Verification Required

1. **Umami `/welcome` landings reading** (lever A metric 2, ROADMAP SC 10). See frontmatter `human_verification` entry. This is an intentional, user-directed deferral (224-03-SUMMARY.md: "the user chose 'Continue, I'll test at the end'"), not a discovered gap. Everything automatable for the baseline is already done and correct.
2. **Visual spot-check of the guest/registered Train score screen and `/welcome`.** DOM-structure tests are strong (absence of reminder/QR elements, presence of the two signup testids, absence of the actions-row class for registered users), but true pixel rendering was not visually inspected in a browser this session. The phase's `ui.plan-gate` was deliberately overridden by the owner (224-GATE-OVERRIDE.md) on the basis that no new visual layout is introduced beyond what's already locked in CONTEXT.md — a quick look confirms that holds.

### Gaps Summary

None found. All 10 ROADMAP success criteria have code-level, test-verified evidence. All 16 GUESTACT
requirements are satisfied and closed out by their owning plan's SUMMARY. No anti-patterns, no broken
key links, no complexity-baseline drift, no missing artifacts. The only reason this report is not
`passed` is that Step 9's decision tree routes any phase with outstanding human-verification items to
`human_needed` regardless of how clean the automated evidence is — and this phase has exactly one
intentionally-deferred external reading (Umami) plus one recommended visual spot-check, both of which
the phase's own SUMMARYs already flagged rather than concealed.

---

*Verified: 2026-09-18*
*Verifier: Claude (gsd-verifier)*
