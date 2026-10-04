---
phase: 230-weekly-train-leaderboards
plan: 02
subsystem: api
tags: [backend, train, leaderboard, session-delta, sqlalchemy, fastapi]

requires:
  - phase: 230-weekly-train-leaderboards
    provides: "Plan 01: GET /api/train/leaderboard, fetch_week_aggregates, build_board / build_leaderboard, rank_without_session wire key (null)"
provides:
  - "fetch_session_contribution: caller-scoped per-session in-window totals (IDOR guard on user_id)"
  - "totals_without and the session_contribution keyword on build_board / build_leaderboard; session_id keyword on get_weekly_leaderboard"
  - "GET /api/train/leaderboard?session_id= (Query ge=1, le=2**31-1) returning rank_without_session per board, wire shape unchanged"
  - "Real-row repository tests for scoring, filler, window, deadline split and flags; hidden / guest viewer router tests"
affects: [230-03, 230-05, train-leaderboard]

actuals:
  tokens: 21000
  tasks: 3
  commits: 3
plan_head_before: 7f9ef3c10b34b355fcc279d3d1ec331d8ca9ff9f
plan_head_after: d865c46d3f339c993dd7a6147589634e00ed5ee7

tech-stack:
  added: []
  patterns:
    - "Session delta computed server-side in one request from the same aggregate snapshot, against the same visible others as rank (never the combined list)"
    - "Caller-scoped query (user_id in the WHERE) as the IDOR guard; a foreign id yields an empty aggregate rather than an error"
    - "Repository tests own an ISO week each from Monday 2031-01-06 (k table in the module docstring); router tests keep k 10-14 of the reserved 10-29"

key-files:
  created:
    - tests/repositories/test_train_leaderboard_repository.py
  modified:
    - app/repositories/train_leaderboard_repository.py
    - app/services/train_leaderboard.py
    - app/routers/train.py
    - tests/routers/test_train_leaderboard.py
    - tests/services/test_train_leaderboard.py

key-decisions:
  - "rank_without_session is returned exactly as computed: Points can only worsen, Accuracy can improve, and nothing is clamped to rank (D-18 copy rule belongs to Plan 05)"
  - "Points returns null when no puzzles remain without the session; Accuracy returns null when no non-filler puzzles remain (the first session of the week)"
  - "Sentry context on the endpoint carries session_id as context, never in the message text"

patterns-established:
  - "Revert-to-prove mutation checks recorded per guard in the SUMMARY"

requirements-completed: [D-01, D-02, D-06, D-12, D-13, D-14, D-18]

coverage:
  - id: D1
    description: "GET /api/train/leaderboard?session_id= returns the viewer's rank without that session on both boards, null for the first session and when no session_id is given"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_rank_without_session_follows_the_viewer_across_two_sessions"
        status: pass
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py -k without_session"
        status: pass
    human_judgment: false
  - id: D2
    description: "Accuracy rank without a weak session can improve and is returned unclamped; Points never improves"
    requirement: "D-18"
    verification:
      - kind: unit
        ref: "tests/services/test_train_leaderboard.py#test_without_session_accuracy_can_improve_and_is_returned_unclamped"
        status: pass
    human_judgment: false
  - id: D3
    description: "A session id the viewer does not own contributes nothing; non-integer, zero, negative and int4-overflow ids are 422 before SQL"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_foreign_session_id_ignored"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_session_id_validation_rejects_bad_values"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_leaderboard_repository.py#test_contribution_returns_the_callers_in_window_session_totals"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-01 scoring on real rows (incl. legacy NULL tier), unsolved rows excluded, SHARP_FILLER counted on Points only"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_leaderboard_repository.py -k 'points or unsolved or filler'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Half-open weekly window and a session spanning the Sunday deadline contributing one solve to each week"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_leaderboard_repository.py -k 'window or deadline'"
        status: pass
    human_judgment: false
  - id: D6
    description: "Hidden and guest viewers get their private row over HTTP while other viewers never see them and rank as if absent"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_hidden_viewer_sees_private_row"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_guest_viewer_sees_ghost_row"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-04
status: complete
---

# Phase 230 Plan 02: Session-Delta Rank (rank_without_session) Summary

**GET /api/train/leaderboard?session_id= now returns each board's rank without the caller's own session (computed from the same aggregate snapshot against the same visible others), IDOR-safe and int4-validated, with the scoring, window, deadline and hidden/guest rules proven on real rows.**

## Performance

- **Duration:** ~14 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `fetch_session_contribution` reuses Plan 01's module-level points expression and non-filler predicate (no second CASE) and filters on `DrillSolve.user_id == user_id`, so a foreign session id matches no rows.
- `totals_without` (field-wise, clamped at 0) and a small `_rank_without` helper keep `build_board` shallow; the rank counts only `is_public` others that are not the viewer, never the combined list.
- Router: `_SESSION_ID_MAX = 2**31 - 1` bounds the optional `session_id` query parameter (422 instead of an asyncpg overflow 500); contribution fetch runs sequentially after the aggregate. No key of `TrainLeaderboardResponse` and nothing on `SolveResponse` changed (Plan 01's key-set test and `tests/routers/test_train.py` still pass).
- Pinned over HTTP: first session of the week gives null; a second session moved V from rank 2 to rank 1 on Points with `rank_without_session` 2; Accuracy stays 1 / 1; a foreign id leaves `rank_without_session == rank`.

## Task Commits

1. **Task 1 (tracer): rank_without_session end to end** - `51ea6544a` (feat)
2. **Task 2: session-delta rules, contribution, validation tests** - `6ce7e50f6` (test)
3. **Task 3: scoring / window / deadline / flags / hidden / guest on real rows** - `d865c46d3` (test)

## Files Created/Modified

- `app/repositories/train_leaderboard_repository.py` - `fetch_session_contribution`
- `app/services/train_leaderboard.py` - `totals_without`, `_rank_without`, `session_contribution` / `session_id` keywords
- `app/routers/train.py` - `_SESSION_ID_MAX`, `session_id` Query parameter, Sentry context
- `tests/repositories/test_train_leaderboard_repository.py` - new module, user ids 93600-93619 reserved, k table from Monday 2031-01-06
- `tests/routers/test_train_leaderboard.py` - k=10 tracer, k=11 foreign id, k=12 validation, k=13 hidden viewer, k=14 guest viewer
- `tests/services/test_train_leaderboard.py` - six without_session / totals_without unit tests

## Decisions Made

- `rank_without_session` is never clamped to `rank` (D-18 is Plan 05's copy rule).
- Null (not 0 or rank) when nothing remains without the session.

## TDD Gate Compliance

Task 1 shipped the production code (tracer); Tasks 2 and 3 are characterization tests over it, so their first runs passed at once, as the plan anticipates. The red runs that prove each guard bites are the mutation checks below (each reverted with `git checkout -- <file>` on a committed file, then re-verified clean). `gsd_run check tdd-red-evidence` was not run.

Mutation checks (revert-to-prove):

1. Dropped `DrillSolve.user_id == user_id` from `fetch_session_contribution`: `test_contribution_returns_the_callers_in_window_session_totals` and `test_foreign_session_id_ignored` both failed (2 failed); restored.
2. Removed `le=_SESSION_ID_MAX` from the Query: `test_session_id_validation_rejects_bad_values[2147483648]` failed (1 failed, 3 passed); restored.
3. Counted the combined list (public OR viewer) in the rank-without computation: `test_without_session_points_ranks_the_remaining_total_against_unchanged_others`, `test_without_session_hidden_viewer_counts_only_visible_others` and the router tracer test failed (3 failed); restored.
4. Replaced the move-points CASE with the raw `move_quality` column: `test_points_follow_the_guess_and_tier_scoring_including_legacy_null_tier` failed; restored.
5. Dropped `leaderboard_hidden` from the visibility predicate (`is_public = not is_guest`): `test_hidden_viewer_sees_private_row` failed; restored.

## Deviations from Plan

None - plan executed exactly as written. (Validation test is parametrized over `abc`, `0`, `-1`, `2147483648`; the plan listed the first, second and last.)

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the `session_id` query parameter, covered by T-230-04 and T-230-17 with the red runs above.

## Verification Results

- `uv run pytest` on `tests/services/test_train_leaderboard.py`, `tests/services/test_train_score_parity.py`, `tests/repositories/test_train_leaderboard_repository.py`, `tests/routers/test_train_leaderboard.py`, `tests/routers/test_train.py`: 161 passed
- `uv run ruff check .`, `ruff format --check`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean
- Every repository rule token (points, unsolved, filler, window, deadline, flags, contribution) selects at least one test; repository module has 7 tests; the router `hidden or guest or without_session or session` selector picks 8
- Acceptance greps: `DrillSolve.user_id == user_id` 1, `session_contribution: SolveTotals | None = None` 2, `_SESSION_ID_MAX` 2, `gather` 0 in service and repository

## Next Phase Readiness

- Plan 05 can consume `rank_without_session` from the existing endpoint with `?session_id=<completed session id>` and apply the "(up N)" copy rule itself.
- Plan 03 is unaffected (wire shape unchanged). Plan 04 keeps router k 30-39.

---
*Phase: 230-weekly-train-leaderboards*
*Completed: 2026-10-04*

## Self-Check: PASSED

Created file `tests/repositories/test_train_leaderboard_repository.py` exists; commits 51ea6544a, 6ce7e50f6 and d865c46d3 are present; acceptance criteria for all three tasks re-run green.
