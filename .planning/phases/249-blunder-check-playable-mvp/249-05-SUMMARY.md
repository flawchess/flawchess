---
phase: 249-blunder-check-playable-mvp
plan: 05
subsystem: blunder-check
tags: [blunder-check, better-move, solution, grading, fastapi, beta-gate]
status: complete

requires:
  - phase: 249-04
    provides: window lifecycle, grading module, answers path with row lock and claiming UPDATE
provides:
  - resolve_better_move_tier, is_legal_uci (app/services/blunder_check_grading.py)
  - submit_better_move, window_solution and the SolutionData variants (app/services/blunder_check_service.py)
  - claim_better_move, GameInfoRow, game_info_for (app/repositories/blunder_check_repository.py)
  - POST /api/blunder-check/sessions/{id}/windows/{position}/better-move
  - GET /api/blunder-check/sessions/{id}/windows/{position}/solution (discriminated union)
affects: [249-06, 249-07, 249-08]

tech-stack:
  added: []
  patterns:
    - "Better-move submit mirrors the answer path: window row locked FOR UPDATE, then a claiming UPDATE guarded by outcome = CAUGHT AND better_move_tier IS NULL"
    - "Solution dispatches per outcome to three small builders; the false-alarm builder reads only the FALSE_ALARM answer row and the snapshot"
    - "Router maps service dataclasses to the discriminated pydantic union with isinstance dispatch"

key-files:
  created:
    - tests/routers/test_blunder_check_solution.py
  modified:
    - app/services/blunder_check_grading.py
    - app/services/blunder_check_service.py
    - app/repositories/blunder_check_repository.py
    - app/routers/blunder_check.py
    - app/schemas/blunder_check.py
    - tests/services/test_blunder_check_grading.py

key-decisions:
  - "Tier precedence has no window-case input (D-17): key good, the user's own blunder wrong (beats a graded entry for the same move), first server-graded match, else the client tier; points come from MOVE_TIER_POINTS only"
  - "The better-move submit takes the same row lock as the answer path; the claiming UPDATE is the second defence (both mutation-checked)"
  - "refutation_uci on a blunder solution falls back to the game's own reply from the snapshot when the stored refutation is NULL"
  - "game_info is filled only for foreign windows whose game still exists; own windows and deleted games return null"

patterns-established:
  - "tests/routers/test_blunder_check_solution.py reuses _setup/_Spec/_Clock/_new_window from the drill tests and defines its own clock fixture (importing a fixture trips F811)"

requirements-completed: [D-09, D-12, D-14, D-16, D-17]

actuals:
  tokens: 40000
  tasks: 2
  commits: 3
plan_head_before: ccf303990fb9a54992b69b5dc78778c8d4547679
plan_head_after: 22d0526237efd2c16076dd1592e8703576664d1d
---

# Phase 249 Plan 05: Better move and solution endpoints Summary

After a caught blunder the user submits one better move that the server grades (key good, own blunder wrong, server-graded tier, else the browser tier) and scores once, and every ended window serves a solution that reveals exactly what D-09, D-10, D-14 and D-16 allow.

## Tasks

1. **Task 1 (tracer)**, commit `716ed1c32`: `resolve_better_move_tier`, `claim_better_move`, `game_info_for`, `submit_better_move`, a blunder-kind `window_solution`, both routes, all wire schemas, and a tracer test (key submitted with client tier "wrong" resolves to "good", +2, window points 5, solution carries game id, blunder ply, key and blunder UCI). Verified end to end before expansion.
2. **Task 2 (TDD)**, RED `f57210e4f`, GREEN `22d052623`: unit tests for the tier precedence and `is_legal_uci`; router tests for precedence (own blunder, server-graded runner-up overriding the client, all three client tiers off-key), claim guards (twice, not_caught on missed/cleared/false-alarm/open, session_closed, illegal and malformed UCI, IDOR 404, non-beta 403), the three solution kinds with exact key sets, foreign `game_info` with a recursive identity-key scan, own windows with null game info, and a deleted source game. RED failed on 10 tests for real reasons (guard reasons, and a false-alarm window leaking the full blunder block). GREEN added `_check_better_move_claimable`, the herring and false-alarm builders, foreign `game_info`, and the union dispatch. A concurrent double submit test was added on top of the plan.

## Verification

- `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/services/ -k blunder_check`: 167 passed, 1 skipped (pre-existing). Grading unit tests and solution router tests: 68 passed.
- `ruff check .`, `ruff format`, `ty check app/ tests/ scripts/` clean; `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Mutation checks (reverted with `git checkout -- <file>`, tree confirmed clean): removing the CAUGHT and `better_move_tier IS NULL` guards from both the claim and the service fails 4 tests (twice, concurrent, not_caught x2); keeping the service checks but dropping the SQL claim guard and the row lock fails the concurrent submit test.

## Deviations from Plan

### Auto-fixed / judgement calls

**1. [Rule 2 - Correctness] Row lock on the better-move path**
- **Issue:** the plan names only the claiming UPDATE; the answer path of plan 04 showed a lock is needed so concurrent submits read consistent window points.
- **Fix:** `get_window_for_user(..., for_update=True)` in `submit_better_move` (per the hand-off); added `test_better_move_concurrent_submits_award_once`.
- **Files:** app/services/blunder_check_service.py, tests/routers/test_blunder_check_solution.py

**2. [Scope note] Tracer withheld the guards and two solution kinds on purpose**
- The tracer commit had the claim UPDATE as the only guard and a blunder-only solution, so Task 2's RED failed for real reasons. Net result matches the plan.

**3. refutation fallback**
- `BlunderSolution.refutation_uci` uses the stored opponent best reply and falls back to the game's own reply from the snapshot when the stored value is NULL, so the Game line is never missing a reply the snapshot holds. Not specified in the plan.

**4. Helper reuse**
- The solution tests import `_setup`, `_Spec`, `_Clock`, `_new_window` and friends from `tests/routers/test_blunder_check_drill.py` and declare their own `clock` fixture. Promoting the helpers to `tests/blunder_check_seed.py` was left for a later plan.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-249-15 (claim guard, server-side points, second submit 409 with unchanged points, concurrent submit awards once), T-249-17 (409 until the window ends; false-alarm key set is exactly flagged move, FEN, points for blunder and herring windows), T-249-18 (game_info four neutral fields; recursive scan bans username/email/user_id keys) are mitigated and tested. T-249-16 stays accepted: an off-key, ungraded move uses the client tier.

## Hand-off notes for plans 06 to 08

- Wire contract is in `app/schemas/blunder_check.py`. 409 `detail` values on the new routes: `session_closed`, `not_caught`, `better_move_done` (better-move) and `window_open` (solution); 422 `"Illegal move"` for an illegal UCI, plus pydantic's 422 for a malformed one.
- `BetterMoveResponse` carries `window_points` and `session_points` after the better move, so the client can update the strip without another call.
- `HerringSolution` and `FalseAlarmSolution` have no `window_case`; `FalseAlarmSolution` has no game id, is_own or analysis_ply (the client cannot offer an Analyze link for it).
- A foreign window's `game_id` is returned for blunder and herring solutions while the game exists; own windows use the library game card (`game_info` null).

## Self-Check: PASSED

- Files exist: solution router test, grading unit tests, service, repository, router and schema edits.
- Commits `716ed1c32`, `f57210e4f`, `22d052623` are ancestors of HEAD.
