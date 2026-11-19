---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 02
subsystem: api
tags: [leaderboard, medals, train, blunder-check, alembic, fastapi, sqlalchemy]

requires:
  - phase: 251-01
    provides: ix_blunder_check_windows_ended_at partial index and the dated blunder-check sessions
  - phase: 251-12
    provides: both-modes streak rule (no code dependency, ordered first to keep Alembic heads serial)
provides:
  - "fetch_week_bc_aggregates over blunder_check_windows (ended windows by ended_at)"
  - "Per-board spec in train_leaderboard: four boards through one ranking implementation"
  - "GET /train/leaderboard with blunder_check_points and blunder_check_score next to points and accuracy"
  - "Alembic revision ed1ca360aec4 widening ck_train_weekly_standings_board to four keys"
  - "finalize_due_weeks, unclaimed list, tallies and claims for all four board keys"
affects: [251-03, 251-04, 251-10, 251-11, 251-13]

plan_head_before: 85fe46969e4e547db3d1da9977bf77df8ff2444b
plan_head_after: 11604ca816c7b36f226e1d16f40a34d082ccf61a

actuals:
  tokens: 12000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Board behaviour lives in a frozen _BoardSpec per LeaderboardBoardKind (metric, qualify minimum, rank-key rule, session-delta flag); no `if kind ==` branches"
    - "Board key tuples (BOARD_KINDS, _BOARDS, _BOARD_BY_TEXT) are derived from typing.get_args(LeaderboardBoardKind)"
    - "A spec's metric returns None for the other mode's totals (fail closed), so a mode mix-up yields no entry"

key-files:
  created:
    - alembic/versions/20261118_210227_ed1ca360aec4_phase_251_blunder_check_boards.py
  modified:
    - app/repositories/train_leaderboard_repository.py
    - app/services/train_leaderboard.py
    - app/schemas/train.py
    - app/models/train_weekly_standing.py
    - app/services/train_medals.py
    - app/repositories/train_medals_repository.py
    - tests/services/test_train_leaderboard.py
    - tests/routers/test_train_leaderboard.py
    - tests/repositories/test_train_medals_finalization.py
    - tests/repositories/test_train_medals_repository.py

key-decisions:
  - "DECISION RECORD (checkpoint resolved by the orchestrator with the owner's answer option-a): stored board keys are `blunder_check_points` and `blunder_check_score`; the feature-route step ID for blunder check is `blunder-check` (plan 251-10 reads it from here)"
  - "Per-board tallies stay per board on all four boards (D-23 intent met without combining the two puzzle boards, which would change puzzle behaviour)"
  - "rank_without_session is null on both blunder-check boards (RESEARCH Open Question 4; the score screen links to the boards, D-24)"
  - "Blunder-check Points ties share a rank (value alone, like puzzle Points); Score % rank key is value then windows (like Accuracy); display order is value, count, name for both"
  - "LeaderboardRow.puzzles carries the ended-window count and LeaderboardViewer.puzzles_to_qualify the windows still needed on the blunder-check boards"

patterns-established:
  - "Adding a board is a spec entry plus a Literal member; ranking, slicing, visibility, finalization and tallies need no change"

requirements-completed: []

coverage:
  - id: D1
    description: "GET /train/leaderboard returns the two blunder-check boards from ended windows by ended_at; unended windows, windows outside the half-open week, guests and hidden users stay off them; an ended window of an expired session counts"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_bc_boards_rank_ended_windows_of_this_week"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_bc_boards_guest_viewer_private_row_and_hidden_user_invisible"
        status: pass
    human_judgment: false
  - id: D2
    description: "Score % is tentative and unranked below 18 ended windows (D-22), floors the percent, ties break by windows"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py#test_bc_board_score_tentative_below_eighteen_windows_is_unranked_below_qualified"
        status: pass
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py#test_bc_board_qualify_constant_is_eighteen_windows"
        status: pass
    human_judgment: false
  - id: D3
    description: "A closed week finalizes four boards under one marker; a tentative Score % entry gets no row but keeps its Points row"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_finalize_writes_four_boards"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_finalize_bc_score_skips_tentative"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unclaimed medals order newest week first then points, accuracy, blunder-check points, blunder-check score; a claim stamps only the posted board key"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_repository.py#test_unclaimed_orders_four_boards"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_repository.py#test_claim_bc_medal"
        status: pass
    human_judgment: false
  - id: D5
    description: "A blunder-check medal shows on the blunder-check tally and on no puzzle board tally (D-23)"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_repository.py#test_bc_medal_tally_isolated"
        status: pass
    human_judgment: false
  - id: D6
    description: "Migration ed1ca360aec4 upgrades, round-trips and leaves alembic check clean"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic check; downgrade -1 then upgrade head; one head"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 02: Blunder-check weekly boards with medals Summary

**GET /train/leaderboard now returns four boards: the unchanged puzzle Points and Accuracy plus blunder-check Points and Score % (tentative below 18 ended windows), all through one per-board spec, and weekly finalization writes standings and medals for every board under the keys `blunder_check_points` / `blunder_check_score`.**

## Performance

- **Duration:** about 45 min
- **Tasks:** 3 (1 tracer, 1 resolved decision checkpoint, 1 TDD)
- **Commits:** 3 (measured from `plan_head_before`)
- **Files:** 11 (1 created, 10 modified)

## Decision record (Task 2 checkpoint)

The orchestrator presented the checkpoint to the project owner, who chose **option-a**. Recorded here so plan 251-10 can read it:

- Stored board keys: **`blunder_check_points`**, **`blunder_check_score`**
- Feature-route step ID for blunder check: **`blunder-check`** (append-only in `app/schemas/feature_route.py`, implemented in plan 251-10)

Task 1 already used these names, so no rename pass was needed.

## Accomplishments

- `fetch_week_bc_aggregates`: one grouped SELECT over `blunder_check_windows` joined to `users` (columns only), counting every window with `outcome IS NOT NULL` and `ended_at` in the half-open week, whatever the session status. `BlunderCheckTotals(points_scored, points_possible, windows)` and `BlunderCheckAggregate` are the return types.
- `train_leaderboard`: `_BoardSpec` per kind (`mode`, `metric`, `qualify_min`, `count_in_rank_key`, `has_session_delta`) replaces the `if kind == ...` branches in `_entry_for`, `_rank_key`, `_rank_without` and the viewer's `puzzles_to_qualify`. `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS = 18` sits next to `ACCURACY_QUALIFY_MIN_PUZZLES`. `BOARD_KINDS`, `aggregates_for_board` and `score_percent` are new. `fold_medal_tallies` initialises from every board key. `build_leaderboard`/`get_weekly_leaderboard` build all four boards (sequential awaits), tally visible ids and last-week blocks over all four, with the guest/hidden path unchanged.
- Schemas: `LeaderboardBoardKind` widened; `TrainLeaderboardResponse` gained the two additive board fields; field comments describe the window-count meaning on the blunder-check boards.
- Migration `ed1ca360aec4` (down_revision `ccc5e4f91f6d`) drops and recreates `ck_train_weekly_standings_board` with four keys, mirrored in the model. Downgrade deletes `blunder_check_*` rows first (comment explains the serial-CI round-trip reason).
- Medals: `_BOARDS` and `_BOARD_BY_TEXT` derive from the Literal; `finalize_due_weeks` fetches the blunder-check aggregates after the puzzle aggregates and hands each kind its own mode's aggregates; `fetch_unclaimed` orders points, accuracy, blunder-check points, blunder-check score.

## Task Commits

1. **Task 1 (tracer): live blunder-check boards** - `ee14ce10c` (feat)
2. **Task 2:** decision checkpoint, resolved by the orchestrator (option-a), no commit
3. **Task 3 RED** - `f2737e3fd` (test); **GREEN** - `11604ca81` (feat)

## TDD notes (Task 3)

- **RED** (`f2737e3fd`): five behaviour tests, all five failed on the planned behaviour: `CheckViolationError` on `ck_train_weekly_standings_board` for the new keys (unclaimed order, tally, claim) and finalization writing only `accuracy`/`points` (`KeyError: 'blunder_check_score'`, "Right contains 2 more items"). Semantic assessment: every failure was the planned missing behaviour, not a collection, import or fixture fault. `gsd_run check tdd-red-evidence` was not run (pytest report format unsupported; the plan is `type: execute`).
- **GREEN** (`11604ca81`): all five pass, plus the pre-existing medal and leaderboard suites.
- No REFACTOR commit.
- Task 1 bite check by mutation: changing the window upper bound `< week_end` to `<= week_end` fails `test_bc_boards_rank_ended_windows_of_this_week`; restored. (Removing `outcome IS NOT NULL` alone does not fail a test because the `ended_at` range already excludes unended windows, whose `ended_at` is NULL; the filter is kept as the explicit statement of A5.)

## Deviations from Plan

**1. [Rule 1 - Pre-existing assertions made stale by the plan's own change] Two existing assertions updated**
- **Found during:** Task 1 verify
- **Issue:** `test_tally_fold_builds_per_board_maps_with_zero_filled_missing_types` asserted `fold_medal_tallies([]) == {"points": {}, "accuracy": {}}`, and `test_response_key_set_has_no_user_ids` pinned the exact response key set and read `board["viewer"]` on every board. The plan requires the fold to start from every board key and the response to gain two fields.
- **Fix:** the empty-fold assertion lists all four keys; the key-set test lists the two new top-level keys, expects the two blunder-check boards to have no rows and a null viewer (it seeds no windows), and keeps the full row and viewer key checks on the puzzle boards. No puzzle ranking assertion changed.
- **Files modified:** `tests/services/test_train_leaderboard.py`, `tests/routers/test_train_leaderboard.py`
- **Commit:** `ee14ce10c`

**Total deviations:** 1 (test restatement, no behaviour change). **Impact:** none on scope.

## Issues Encountered

None. Full backend suite `uv run pytest -n auto`: 7040 passed, 19 skipped. `ruff format`, `ruff check`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4` and `alembic check` are clean. The frontend was not touched.

Note for the orchestrator: `uv run alembic upgrade head` was run against the shared dev DB, so it is now at `ed1ca360aec4`. Other worktrees on older code keep working because tests clone from a template that refreshes on head change.

## Notes for later plans

- Plan 251-10: the feature-route step ID is `blunder-check` (see the decision record).
- Frontend plans (251-11, 251-13): `GET /train/leaderboard` has `blunder_check_points` and `blunder_check_score` boards; `LeaderboardRow.puzzles` is the ended-window count there and `viewer.puzzles_to_qualify` the windows still needed (qualify at 18, `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS`); `rank_without_session` is always null on those boards. `MedalKey.board`, `UnclaimedMedal.board` and the claim body accept the two new keys. A frontend parity test for the 18 should mirror the existing `ACCURACY_QUALIFY_MIN_PUZZLES` one (the backend half is pinned by `test_bc_board_qualify_constant_is_eighteen_windows`).
- Weeks finalized before deploy keep only the two puzzle boards (no public blunder-check boards existed then). `MEDALS_START_WEEK` and the grace are unchanged.
- `PUT /train/settings` still does not write `blunder_check_per_session` (noted in plan 12's summary as owned by "plan 02"). This plan's `files_modified` and tasks do not include it, so it was not touched; whichever plan owns the settings endpoint should confirm it.

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary. T-251-05 is mitigated by reusing `_rank_board`/`resolve_viewer_visibility` unchanged (tests: guest and hidden users never appear on or shift a viewer's blunder-check board, a guest viewer still gets a private row). T-251-06 is covered by the widened Literal and the caller-scoped claim (`test_claim_bc_medal`). T-251-07: `fetch_week_bc_aggregates` selects columns only and ids stay in the service layer.

## Self-Check: PASSED

- Created files exist: the migration and this SUMMARY.
- Commits `ee14ce10c`, `f2737e3fd`, `11604ca81` are ancestors of HEAD.
- `alembic heads` prints one head (`ed1ca360aec4`); `async def fetch_week_bc_aggregates`, `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS = 18`, both new Literal members and response fields, and `get_args(LeaderboardBoardKind)` in `train_medals.py` and `train_leaderboard.py` are present; `-k bc_board` selects 16 tests.
