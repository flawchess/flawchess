---
phase: 230-weekly-train-leaderboards
plan: 01
subsystem: api
tags: [backend, train, leaderboard, alembic, sqlalchemy, ranking, fastapi]

requires:
  - phase: 224-train-guests
    provides: Train endpoints open to guest accounts, dev_now_utc clock dependency on the Train router
provides:
  - "users.leaderboard_hidden column (NOT NULL, default false) and partial index ix_drill_solves_solved_at (migration c4e7a91d2b58)"
  - "app/services/train_score.py server-side scoring constants pinned to trainScore.ts by a regex parity test"
  - "fetch_week_aggregates: one GROUP BY weekly per-user aggregate query"
  - "app/services/train_leaderboard.py: week_window, display_name, competition ranking, top-5 plus viewer slicing, Points pass target, hidden/guest visibility"
  - "GET /api/train/leaderboard returning both boards with a final wire contract (rank_without_session key present, null until Plan 02)"
affects: [230-02, 230-03, 230-04, 230-05, train-leaderboard, medals]

actuals:
  tokens: 27500
  tasks: 2
  commits: 3
plan_head_before: 4a6d14b50185270dc6fa83b91b73cf1ce080b58f
plan_head_after: 837be243d

tech-stack:
  added: []
  patterns:
    - "Aggregate in SQL, rank in Python: one GROUP BY query, pure dataclass service, DB-free ranking tests"
    - "Visibility enforced before ranking: others = registered and not hidden, the viewer's own entry (any visibility) is re-inserted for the private would-be row"
    - "Router tests pin dev_now_utc into a declared per-test ISO week (k table) because leaderboard data is global"
    - "Frontend/backend constant parity pinned by regex extraction from the .ts file"

key-files:
  created:
    - alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py
    - app/services/train_score.py
    - app/repositories/train_leaderboard_repository.py
    - app/services/train_leaderboard.py
    - tests/routers/test_train_leaderboard.py
    - tests/services/test_train_leaderboard.py
    - tests/services/test_train_score_parity.py
  modified:
    - app/models/user.py
    - app/models/drill_solve.py
    - app/schemas/train.py
    - app/routers/train.py
    - frontend/src/lib/trainScore.ts

key-decisions:
  - "Accuracy is ranked on the floored integer percent (RESEARCH A1), so ties are visible ties and no float equality is involved"
  - "Pass target is computed on the Points board only; Accuracy shows the qualifier line instead (RESEARCH A5)"
  - "The viewer's own entry is always inserted into the combined list regardless of visibility; every other row requires registered and not hidden, filtered before ranking"
  - "rank_without_session is part of the wire contract now but null in every response; Plan 02 adds session_id and computes it without changing any key"

patterns-established:
  - "Router leaderboard tests own an ISO week each: Monday 2032-01-05 plus k weeks, k table in the module docstring, ranges 0-9 / 10-29 / 30-39 reserved per plan"
  - "Tests seed DrillSession(status completed) plus DrillSolve rows directly and delete users in finally (cascade)"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-13, D-14, D-15, D-16, D-19]

coverage:
  - id: D1
    description: "GET /api/train/leaderboard returns Points and Accuracy boards from drill_solves with competition ranks, floored accuracy percent, tentative markers, and guests/opted-out users invisible to others"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_points_and_accuracy_boards_rank_this_week"
        status: pass
    human_judgment: false
  - id: D2
    description: "ISO week window in UTC, half-open, keyed on solved_at (not session_date), time only from dev_now_utc"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k window"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_solves_outside_the_pinned_week_are_ignored"
        status: pass
    human_judgment: false
  - id: D3
    description: "Accuracy qualifier: tentative under 20 non-filler solves, puzzles_to_qualify, no Accuracy entry for filler-only users"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k qualify"
        status: pass
    human_judgment: false
  - id: D4
    description: "Competition ranks, puzzles-desc tie order, top 5 plus viewer with 2 neighbours and gap marker, Points pass target"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k 'rank or slice or pass_target'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Display name precedence lichess, chess.com, Anonymous with blank handling"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k display_name"
        status: pass
    human_judgment: false
  - id: D6
    description: "Hidden and guest visibility: hidden users and guests never appear in or move anyone else's board; hidden and guest viewers get private would-be rows"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k 'hidden or guest'"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_points_and_accuracy_boards_rank_this_week"
        status: pass
    human_judgment: false
  - id: D7
    description: "Server scoring constants cannot drift from trainScore.ts (guess, per-puzzle, tier points), proven red by reverting"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_train_score_parity.py"
        status: pass
    human_judgment: false
  - id: D8
    description: "No user id, email or internal key anywhere in the response"
    requirement: "D-16"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_response_key_set_has_no_user_ids"
        status: pass
    human_judgment: false
  - id: D9
    description: "Migration c4e7a91d2b58 adds users.leaderboard_hidden and ix_drill_solves_solved_at and is reversible"
    requirement: "D-16"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head; downgrade -1; upgrade head; alembic check (no drift)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-04
status: complete
---

# Phase 230 Plan 01: Weekly Train Leaderboards Backend Foundation Summary

**GET /api/train/leaderboard serves Points and Accuracy weekly boards from drill_solves (SQL aggregate, pure-Python competition ranking, server-enforced hidden/guest visibility, Points pass target) on top of a reversible users.leaderboard_hidden migration and a regex parity test pinning server scoring to trainScore.ts.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-04T02:21:52Z
- **Completed:** 2026-10-04T02:28:00Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 12 (7 created, 5 modified)

## Accomplishments

- One endpoint, one aggregate query, one pure service: the wire contract (including `rank_without_session`, null here) is final, so Plan 03 can mirror it while Plan 02 extends the same endpoint.
- Migration `c4e7a91d2b58` (down_revision `3b7e2f9c41a6`) applied to the dev DB; `downgrade -1` then `upgrade head` round trip ran clean and `alembic check` reports no model drift.
- Every ranking, window, qualifier, naming and visibility rule is pinned by DB-free tests (49 service tests, 6 parity tests) plus 4 router tests; pinned over HTTP: 388800 s remaining on Wednesday 12:00 UTC, Points order A 12 / B 8 / V 6, Accuracy order A 100 (4) / V 100 (2) / B 55 (3), V's `puzzles_to_qualify` 18, pass target `{name, points_needed: 4}`.
- Docstrings that said scoring must never run server-side (`SolvedResult`, `DrillMoveQuality`) now describe the deliberate parity-pinned port; trainScore.ts gained comment lines only (no value change).

## Task Commits

1. **Task 1 (tracer): GET /api/train/leaderboard end to end** - `afa55057d` (feat)
2. **Task 2 RED: failing tests for pass target, rules, parity** - `9a9940317` (test)
3. **Task 2 GREEN: Points pass target, doc drift fixes** - `837be243d` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py` - users.leaderboard_hidden column and partial solved_at index, with downgrade
- `app/services/train_score.py` - GUESS_POINTS, MOVE_TIER_POINTS, TRAIN_POINTS_PER_PUZZLE, MOVE_QUALITY_TIER (read-only mappings)
- `app/repositories/train_leaderboard_repository.py` - SolveTotals, WeeklyAggregate, fetch_week_aggregates (points CASE built from the constants)
- `app/services/train_leaderboard.py` - week_window, display_name, accuracy_percent, build_board, build_leaderboard, get_weekly_leaderboard
- `app/schemas/train.py` - Leaderboard* models and Literal aliases
- `app/routers/train.py` - GET /train/leaderboard
- `app/models/user.py`, `app/models/drill_solve.py` - column and index
- `tests/routers/test_train_leaderboard.py`, `tests/services/test_train_leaderboard.py`, `tests/services/test_train_score_parity.py`
- `frontend/src/lib/trainScore.ts` - parity-test comments only

## Decisions Made

- Accuracy ranks on the floored integer percent, so equal displayed percents are visible ties (A1).
- Pass target on the Points board only (A5); at rank 1 or with no viewer entry it is null.
- `build_board` keeps the viewer's own entry regardless of visibility and filters everyone else to registered, non-hidden users before ranking, slicing and pass-target selection.

## TDD Gate Compliance

Task 2 followed RED then GREEN: `test(230-01)` commit `9a9940317` precedes `feat(230-01)` commit `837be243d`. RED run: 4 failures, all assertion failures on the planned behavior (3 service pass_target / hidden-viewer-target assertions, 1 router key-set test reading the null pass_target). The other 55 tests already passed because the ranking, window and visibility rules shipped in Task 1's tracer; they are characterization tests of that code. `gsd_run check tdd-red-evidence` was not run (no evidence record persisted).

Mutation checks (revert-to-prove):
- `good: 2` changed to `good: 3` in trainScore.ts: `test_move_tier_points_match_frontend` failed (1 failed, 5 passed); restored.
- pass target `>` changed to `>=` (accepting a tied row): `test_pass_target_is_the_nearest_strictly_better_row_skipping_ties` failed (1 failed, 4 passed); restored.

## Deviations from Plan

None - plan executed exactly as written.

The tracer feedback gate ran as an automated-only verify (migration current, router tests 4/4, ty and size gate clean) with no checkpoint, per the end-of-phase default.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The new endpoint and column match the plan's threat register (T-230-01..03, T-230-07); no extra surface.

## Verification Results

- `uv run pytest tests/services/test_train_leaderboard.py tests/services/test_train_score_parity.py tests/routers/test_train_leaderboard.py tests/routers/test_train.py` : 140 passed
- `uv run ruff check .`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean
- `uv run alembic heads`: `c4e7a91d2b58 (head)`
- `-k` selection: every rule token selects at least one test; the combined selector selects 45 (gate is 8)
- Frontend: eslint clean and the trainScore vitest file passes (comment-only edit)

## Next Phase Readiness

- Plan 02 can add `?session_id` to the endpoint, `fetch_session_contribution`, and the `session_contribution` keyword on `build_board` / `build_leaderboard` (k 10-29 reserved).
- Plan 03 can mirror the Leaderboard* schemas on the frontend now; the wire shape will not change.
- Plan 04 can write `users.leaderboard_hidden` through the profile endpoint (k 30-39 reserved).

---
*Phase: 230-weekly-train-leaderboards*
*Completed: 2026-10-04*

## Self-Check: PASSED

All 7 created files exist on disk; commits afa55057d, 9a9940317 and 837be243d are present; acceptance criteria for both tasks re-run green.
