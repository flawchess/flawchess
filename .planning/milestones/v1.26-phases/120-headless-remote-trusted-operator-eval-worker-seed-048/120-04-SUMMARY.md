---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
plan: "04"
subsystem: database
tags: [postgresql, sqlalchemy, eval-queue, weighted-random, efraimidis-spirakis]

requires:
  - phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
    provides: "120-01 through 120-03: remote eval worker HTTP lease endpoint and queue infrastructure"

provides:
  - "Weighted-random ES game pick in _claim_tier3_derived Step 2 (D-7): -ln(random())/game_weight replaces deterministic ORDER BY"
  - "Named constants GAME_TC_WEIGHTS, GAME_RECENCY_HALF_LIFE_DAYS, GAME_WEIGHT_FLOOR near SEED-046 block"
  - "Same weighted-random spread applied to residual PV-backfill fallback for symmetry"
  - "TestTier3GamePickSpread: spread, weighting-bias, and single-game-regression tests"

affects:
  - eval-drain
  - eval-queue
  - remote-worker

tech-stack:
  added: []
  patterns:
    - "CAST(:param AS float8) instead of :param::float8 for asyncpg compatibility in sa.text queries with named params"
    - "ES game_weight = tc_multiplier * (exp(-dt/tau_game) + floor) mirrors user-lottery pattern at the game level"
    - "time_control_bucket NULL maps to ELSE branch in CASE; insert None for test games to exercise other/unknown bucket"

key-files:
  created: []
  modified:
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py

key-decisions:
  - "D-7: Replace deterministic within-user game pick with ES key -ln(random())/game_weight; residual fallback gets same spread for symmetry"
  - "CAST(:param AS float8) required instead of :param::float8 — asyncpg parses ::float8 as a second colon token, causing PostgresSyntaxError"
  - "time_control_bucket enum has no other value; use None (nullable column) for the ELSE branch in test fixtures"

patterns-established:
  - "CAST(:param AS float8) pattern for explicit float typing in sa.text with asyncpg"

requirements-completed: [D-7]

duration: 8min
completed: 2026-06-14
---

# Phase 120 Plan 04: Weighted-Random Tier-3 Game Pick Summary

**ES weighted-random within-user game pick (-ln(random())/game_weight) with GAME_TC_WEIGHTS + GAME_RECENCY_HALF_LIFE_DAYS constants, replacing deterministic Step-2 ORDER BY in _claim_tier3_derived and its residual fallback**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-14T17:49:37Z
- **Completed:** 2026-06-14T17:57:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced the deterministic `ORDER BY tc_case, played_at DESC LIMIT 1` in Step 2 of `_claim_tier3_derived` with an Efraimidis-Spirakis key `ORDER BY -ln(random()) / game_weight LIMIT 1` where `game_weight = tc_multiplier * (exp(-dt_played/tau_game) + GAME_WEIGHT_FLOOR)`, so concurrent workers landing on the same user usually pick different games
- Applied the same weighted-random spread to the residual PV-backfill fallback path, which has the identical collision shape and a remote worker can sit on it for long stretches once the needs-engine backlog drains
- Added named constants `GAME_TC_WEIGHTS` (classical=8 > rapid=4 > blitz=2 > bullet=1 > other/NULL=0.5), `GAME_RECENCY_HALF_LIFE_DAYS=30`, `GAME_WEIGHT_FLOOR=0.01` immediately after the SEED-046 user-lottery constants
- Proved real spread (>= 3 of 10 seeded games in 300 draws), preserved weighting bias (top priority picked strictly more than bottom), and single-game regression safety in `TestTier3GamePickSpread`

## Task Commits

1. **Task 1: Weighted-random within-user (and residual) game pick** - `39258098` (feat)
2. **Task 2: Spread, weighting-bias, and single-game-regression tests** - `334a9c10` (test)

## Files Created/Modified

- `app/services/eval_queue_service.py` - Added GAME_TC_WEIGHTS/GAME_RECENCY_HALF_LIFE_DAYS/GAME_WEIGHT_FLOOR constants; rewrote Step-2 and residual fallback to use ES key via sa.text with CAST(:param AS float8) for asyncpg compatibility; updated docstring to cite D-7
- `tests/services/test_eval_queue.py` - Added TestTier3GamePickSpread with three tests: spread (300 draws, >= 3 distinct), weighting bias (400 draws, classical/recent > null-TC/old), single-game regression (50 draws, always returns sole game)

## Decisions Made

- **CAST vs :: syntax**: asyncpg's prepared-statement parser treats `:param::float8` as a syntax error (the second `:` is re-parsed as a new named-param prefix). Used `CAST(:param AS float8)` instead — this is the correct asyncpg/SQLAlchemy pattern for explicit type coercion in sa.text queries.
- **time_control_bucket "other" not in enum**: The PostgreSQL enum `timecontrolbucket` only has `bullet|blitz|rapid|classical`. Test fixtures use `None` (nullable column) for the ELSE branch, which the SQL CASE expression routes to `CAST(:tc_other AS float8)` correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncpg syntax error with :param::float8 cast notation**
- **Found during:** Task 1 (verification run of existing tests)
- **Issue:** PostgreSQL parameter `:tc_classical::float8` caused `PostgresSyntaxError: syntax error at or near ":"` because asyncpg's prepared-statement tokenizer sees the second `::` as a parameter-name prefix character, not a typecast operator
- **Fix:** Replaced all `::float8` casts with `CAST(:param AS float8)` syntax throughout both the Step-2 game pick and residual fallback queries
- **Files modified:** `app/services/eval_queue_service.py`
- **Verification:** All 13 existing tests passed; ty and ruff clean
- **Committed in:** `39258098` (part of Task 1 commit)

**2. [Rule 1 - Bug] "other" is not a valid timecontrolbucket enum value in tests**
- **Found during:** Task 2 (initial test run)
- **Issue:** `_insert_game(..., time_control_bucket="other")` raised `InvalidTextRepresentationError: invalid input value for enum timecontrolbucket: "other"` — the DB enum only has bullet/blitz/rapid/classical
- **Fix:** Replaced `"other"` with `None` in test fixtures (nullable column); None maps to the ELSE branch in the CASE expression, exercising the `tc_other` weight correctly
- **Files modified:** `tests/services/test_eval_queue.py`
- **Verification:** All 3 new tests passed + all 16 tests in the file passed
- **Committed in:** `334a9c10` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs discovered during verification)
**Impact on plan:** Both fixes necessary for correct SQL execution and test validity. No scope change — the fixes implement what the plan intended.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Known Stubs

None — all game weight constants are real values; the ES pick is fully wired.

## Threat Flags

No new threat surface introduced. The T-120-04 mitigation (all weight values bound as :params, no f-string in sa.text) is confirmed: `grep -n 'f"""' app/services/eval_queue_service.py` returns nothing inside the function range.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- D-7 satisfied: Step-2 within-user game pick is weighted-random, residual fallback matches
- Both callers (server pool + 120-02 HTTP lease endpoint) benefit via the shared `_claim_tier3_derived` function with zero caller changes
- Full eval_queue test suite green (16 tests); ty + ruff clean
- Phase 120 is complete (plans 01-04 done)

---
*Phase: 120-headless-remote-trusted-operator-eval-worker-seed-048*
*Completed: 2026-06-14*
