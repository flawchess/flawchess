---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 01
subsystem: train
tags: [fastapi, guest-accounts, react-router, vitest, pytest]

# Dependency graph
requires: []
provides:
  - "Train open to every zero-game account (guest or registered), backend and frontend"
  - "app/routers/train.py with no guest authorization gate; docstring names the D-09 backstop"
  - "/train exempt from IMPORT_EXEMPT_ROUTES / ImportRequiredRoute"
  - "TrainGuestGate.tsx and its test file deleted (closes the Phase 215 flake)"
  - "test_guest_zero_game_warmup_end_to_end: HTTP proof of compose -> solve -> streak -> settings round trip"
affects: [224-04-games-less-train-copy, 224-05-guest-lifecycle-purge-and-promotion, 224-06-signup-ask]

# Actuals (#2632)
actuals:
  tokens: 10821
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Route/nav exemption for zero-game accounts via IMPORT_EXEMPT_ROUTES, no is_guest branch"
    - "Account-level streak (session_streak_count) lives only on GET /train/progress, ticked eagerly by _apply_completion_tick when a session's last puzzle is solved — distinct from the per-item SolveResponse.streak, which stays null for herring/sharp-filler puzzles"

key-files:
  created: []
  modified:
    - app/routers/train.py
    - tests/routers/test_train.py
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/pages/Train.tsx
  deleted:
    - frontend/src/components/train/TrainGuestGate.tsx
    - frontend/src/pages/__tests__/Train.guestGate.test.tsx

key-decisions:
  - "Account-level streak proof reads GET /train/progress's session_streak_count, not SolveResponse.streak (which stays null for filler/herring puzzles by design) — the plan's literal wording described the wrong field"
  - "The end-to-end test solves every composed puzzle (loop over puzzle_count), not just the first, because only the session's LAST solve flips session_complete and triggers the eager same-day streak tick (_apply_completion_tick)"
  - "isGuest stays declared but explicitly unused (`void isGuest;`) in Train.tsx per plan instruction to keep it for Plan 04/06, since tsc -b's noUnusedLocals would otherwise fail the build"

requirements-completed: [GUESTACT-02, GUESTACT-03, GUESTACT-04, GUESTACT-14]

coverage:
  - id: D1
    description: "All seven /train/* handlers accept a guest bearer token with 200 instead of 403"
    requirement: "GUESTACT-03"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_composes_session_200"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_settings_round_trip_200"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_onboarding_stamp_200"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_progress_200"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_zero_game_warmup_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "A zero-game guest completes compose -> solve -> streak -> settings round trip over one HTTP-driven integration test"
    requirement: "GUESTACT-04"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_guest_zero_game_warmup_end_to_end"
        status: pass
    human_judgment: false
  - id: D3
    description: "/train is exempt from the import lock in both the nav (all three surfaces) and the route guard"
    requirement: "GUESTACT-02"
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#190-03: Train gating (NAV-02)"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#190-03: empty profile does not crash and renders Train exempt"
        status: pass
    human_judgment: false
  - id: D4
    description: "The module docstring names guest_create_limiter + uq_drill_sessions_user_open as the D-09 backstop and states no Train-specific ceiling is added"
    requirement: "GUESTACT-14"
    verification:
      - kind: other
        ref: "grep -c guest_create_limiter app/routers/train.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "TrainGuestGate.tsx and Train.guestGate.test.tsx no longer exist"
    verification:
      - kind: other
        ref: "test ! -f frontend/src/components/train/TrainGuestGate.tsx && test ! -f frontend/src/pages/__tests__/Train.guestGate.test.tsx"
        status: pass
    human_judgment: false

duration: 45 min
completed: 2026-09-17
status: complete
---

# Phase 224 Plan 1: Guest Train Tracer — Guest Gate Removal, Route Exemption, End-to-End Warm-Up Summary

**Every `/train/*` handler now answers a guest bearer token with 200, `/train` is nav/route-exempt from the import lock, and one new integration test proves a zero-game guest can compose, complete, and re-read a full warm-up session over real HTTP.**

## Performance

- **Duration:** 45 min
- **Tasks:** 2
- **Files modified:** 5 (2 deleted)

## Accomplishments

- Removed `_reject_guest` and its seven call sites from `app/routers/train.py` (Phase 189 D-05 reversed); rewrote the module docstring to name the Phase 224 D-09 backstop (`guest_create_limiter`, Cf-Connecting-Ip-aware, 5/hour/IP) and the `uq_drill_sessions_user_open` partial unique index, and to state explicitly that no Train-specific guest ceiling or filler-only mode is added
- Inverted and renamed the four guest-gate tests in `tests/routers/test_train.py` (`test_403_guest` -> `test_guest_composes_session_200`, `test_settings_403_guest` -> `test_guest_settings_round_trip_200`, `test_onboarding_403_guest` -> `test_guest_onboarding_stamp_200`, `test_progress_403_guest` -> `test_guest_progress_200`), all asserting 200 plus a shape-specific follow-up assertion (echoed settings fields, stamped onboarding column, full progress key set)
- Added `/train` to `IMPORT_EXEMPT_ROUTES` and dropped the `ImportRequiredRoute` wrapper from the `/train/*` route in `frontend/src/App.tsx`; inverted the `190-03` locked-state and empty-profile nav tests in `App.test.tsx` to assert Train is never `aria-disabled` while Openings/Endgames stay locked as the control assertion
- Removed the guest-gate early return and `TrainGuestGate` import from `frontend/src/pages/Train.tsx`, simplified `canTrain` to `profile != null`; deleted `TrainGuestGate.tsx` and `Train.guestGate.test.tsx` (closes the Phase 215 deferred cross-test contamination flake)
- Added `test_guest_zero_game_warmup_end_to_end`: a zero-game guest composes a filler-only warm-up session, solves every puzzle in it, sees `/train/progress`'s `session_streak_count` advance 0 -> 1, and round-trips a `weekday_mask` through `/train/settings` — all over one `httpx.AsyncClient` session with no game and no drill item seeded

## Task Commits

Each task was committed atomically:

1. **Task 1: Zero-game guest reaches and runs Train, end to end** - `e46909d37` (feat)
2. **Task 2: End-to-end guest warm-up session integration test** - `7683dea98` (test)

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `app/routers/train.py` - `_reject_guest` and all seven call sites removed; module docstring names the D-09 backstop
- `tests/routers/test_train.py` - four guest tests inverted/renamed; new `test_guest_zero_game_warmup_end_to_end`; stale docstring bullets updated
- `frontend/src/App.tsx` - `/train` added to `IMPORT_EXEMPT_ROUTES`; `ImportRequiredRoute` wrapper removed from the `/train/*` route; route comment and `useTrainProgress` gating comment updated
- `frontend/src/App.test.tsx` - `190-03` locked-state and empty-profile tests inverted for Train, with Openings/Endgames kept as the control assertion
- `frontend/src/pages/Train.tsx` - guest-gate early return and `TrainGuestGate` import removed; `canTrain` simplified to `profile != null`; stale FLAWCHESS-64 comment blocks replaced
- `frontend/src/components/train/TrainGuestGate.tsx` - deleted (S-2)
- `frontend/src/pages/__tests__/Train.guestGate.test.tsx` - deleted (S-2; closes the Phase 215 flake)

## Decisions Made

- **Account-level streak proof reads `/train/progress`, not the solve response.** The plan's Task 2 action text said "`_solve(...)` returns 200 and the response's `streak` is 1", but `SolveResponse.streak` is a per-`drill_items` field that stays `null` for every herring/sharp-filler puzzle by design (confirmed against the pre-existing `test_solve_sharp_filler_touches_no_drill_item`). The account-level daily habit streak the plan actually means (`ROADMAP` SC 2's "streak state persist") lives on `TrainProgressResponse.session_streak_count`, which only advances via `_apply_completion_tick` — an EAGER same-day tick that fires the instant a session's last puzzle is solved, distinct from the lazy backward-looking `tick_days` walk that never judges "today." The new test therefore loops over every composed puzzle (not just the first) so the session actually completes, then asserts `session_streak_count == 1` from `_get_progress`, not from the solve response.
- **`isGuest` stays declared but unused in `Train.tsx` for now**, per the plan's explicit instruction that Plans 04/06 consume it later. Since `tsc -b` runs with `noUnusedLocals: true`, a genuinely-unused local fails the build — resolved with a one-line `void isGuest;` (an existing codebase pattern, e.g. `lib/maiaEncoding.ts:180`, `pages/Analysis.tsx:1816`) rather than deferring the variable's declaration or suppressing the compiler.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected which endpoint the end-to-end test reads the streak from**
- **Found during:** Task 2 (writing `test_guest_zero_game_warmup_end_to_end`)
- **Issue:** The plan's action text asserted `_solve(...)`'s response `streak` field would be `1` after one solve. Empirically (and per `test_solve_sharp_filler_touches_no_drill_item`), a herring/sharp-filler solve always returns `streak: null` — there is no per-item SR state for a zero-game guest's filler-only session. Additionally, the account-level `session_streak_count` only advances same-day via the eager `_apply_completion_tick` path when the session's LAST puzzle is solved, not on any single solve.
- **Fix:** The test loops over every puzzle in the composed session (`range(puzzle_count)`), asserts the final solve's `session_complete is True`, then reads `session_streak_count == 1` from a fresh `_get_progress` call — proving the exact SC 2 claim ("a `drill_sessions` row plus streak state persist for that guest") through the field that actually carries it.
- **Files modified:** `tests/routers/test_train.py`
- **Verification:** `uv run pytest tests/routers/test_train.py -k guest_zero_game -x -q` -> 1 passed; full file -> 79 passed
- **Committed in:** `7683dea98` (Task 2 commit)

**2. [Rule 3 - Blocking] `void isGuest;` to keep `tsc -b` green with a deliberately-unused local**
- **Found during:** Task 1 (Train.tsx guest-gate removal)
- **Issue:** The plan explicitly keeps `const isGuest = profile?.is_guest === true;` declared for Plan 04/06 to consume later, but removing the guest-gate early return (the only consumer in this plan) leaves it genuinely unused. `frontend/tsconfig.app.json` sets `noUnusedLocals: true`, so `npm run build` (`tsc -b`) fails with `TS6133` on an unused local, and the plan's own `<verify>` block requires that build to pass.
- **Fix:** Added `void isGuest;` immediately after the declaration, with a comment naming which future plans consume it — mirroring the existing codebase pattern for placeholder/forward-looking variables (`frontend/src/lib/maiaEncoding.ts:180`, `frontend/src/pages/Analysis.tsx:1816`).
- **Files modified:** `frontend/src/pages/Train.tsx`
- **Verification:** `npx tsc -b` clean; `npm run build` succeeds; `npm run lint` clean
- **Committed in:** `e46909d37` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in the plan's technical narrative, 1 blocking build issue)
**Impact on plan:** Both fixes preserve the plan's actual intent (prove a zero-game guest's streak persists; keep `isGuest` available for later plans) while making the test and the build match the system's real behavior. No scope creep — no other file touched beyond what Task 1/2 specified.

## Authentication Gates

None - no external service auth encountered.

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The tracer slice is proven end to end: guest bearer tokens reach every `/train/*` handler at 200, `/train` is nav/route-reachable with zero games, and one HTTP-driven integration test proves compose -> solve -> streak -> settings all work for a guest.
- Ready for Plan 02 (Lever A: Home redirect + `/welcome` rewrite) and Plan 04 (games-less Train copy + `isGuest`-gated reminder/QR block), which both build on the route/nav exemption and the still-declared `isGuest` this plan preserved.
- No blockers.

## Self-Check: PASSED

- `app/routers/train.py` exists and contains `guest_create_limiter` (FOUND)
- `frontend/src/components/train/TrainGuestGate.tsx` does not exist (FOUND, i.e. confirmed absent)
- `frontend/src/pages/__tests__/Train.guestGate.test.tsx` does not exist (FOUND, i.e. confirmed absent)
- Commit `e46909d37` present in `git log` (FOUND)
- Commit `7683dea98` present in `git log` (FOUND)
- `uv run pytest tests/routers/test_train.py -x -q` -> 79 passed
- `( cd frontend && npx vitest run src/App.test.tsx )` -> 61 passed
- `( cd frontend && npm run lint && npm run build && npm run knip )` -> all green
- `uv run ty check app/ tests/ scripts/ && uv run ruff check . && uv run ruff format --check app/ tests/ scripts/` -> all green
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` -> OK, no breaches

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-17*
