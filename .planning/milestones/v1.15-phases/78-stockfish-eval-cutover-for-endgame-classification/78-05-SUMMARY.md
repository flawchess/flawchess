---
phase: 78-stockfish-eval-cutover-for-endgame-classification
plan: "05"
subsystem: database
tags: [sqlalchemy, alembic, endgame, stockfish, eval, tdd]

# Dependency graph
requires:
  - phase: 78-04-import-path-integration
    provides: eval_cp/eval_mate columns populated in game_positions during import
provides:
  - _classify_endgame_bucket(eval_cp, eval_mate, user_color) service helper
  - Rewritten query_endgame_entry_rows, query_endgame_bucket_rows, query_endgame_elo_timeline_rows using eval columns
  - Alembic migration c92af8282d1a reshaping ix_gp_user_endgame_game INCLUDE from material_imbalance to eval_cp/eval_mate
affects: [78-06-cutover-execution, endgame analytics, score gap material, endgame ELO timeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "REFAC-02: SQL projects raw white-perspective eval; service layer applies user-color sign flip via _classify_endgame_bucket"
    - "array_agg(column ORDER BY ply)[1] idiom for index-only span-entry value lookup"
    - "Single-point eval at MIN(ply) replaces material_imbalance + 4-ply persistence proxy"

key-files:
  created:
    - alembic/versions/20260502_125433_c92af8282d1a_reshape_ix_gp_user_endgame_game_for_.py
  modified:
    - app/models/game_position.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_repository.py
    - tests/test_endgame_service.py

key-decisions:
  - "Sign flip responsibility: SQL projects raw white-perspective eval; _classify_endgame_bucket applies user-color sign flip at read time (avoids SQL case() per-column)"
  - "eval_mate > 0 treated as +1_000_000 user_eval (white winning); < 0 as -1_000_000 — guarantees threshold crossing for forced-mate positions"
  - "NULL eval routes to parity bucket — engine error or not-yet-backfilled positions should not influence conversion/recovery counts"
  - "material_imbalance column preserved in GamePosition model per REFAC-05 (used in test_aggregation_sanity.py and other consumers)"

patterns-established:
  - "Eval-based endgame classification: single point at span-entry ply, no persistence window"

requirements-completed: []

# Metrics
duration: 90min
completed: 2026-05-02
---

# Phase 78 Plan 05: Endgame Refactor (eval_cp/eval_mate) Summary

**Replaced material_imbalance + 4-ply persistence proxy with Stockfish eval_cp/eval_mate at span-entry ply; added _classify_endgame_bucket helper; reshaped covering index INCLUDE to eval columns.**

## Performance

- **Duration:** ~90 min (across two sessions, second session resumed from context summary)
- **Started:** 2026-05-02
- **Completed:** 2026-05-02
- **Tasks:** 2 (RED + GREEN, TDD plan)
- **Files modified:** 7

## Accomplishments

- Task 1 (RED): Updated all test fixtures to use `eval_cp`/`eval_mate` tuple shape; added 11 `TestClassifyEndgameBucket` test cases that fail on missing `_classify_endgame_bucket`; updated `_FakeRow`, `_elo_bucket_row`, persistence tests, score gap material tests
- Task 2 (GREEN): Rewrote three repository queries to use `array_agg(eval_cp ORDER BY ply)[1]` / `array_agg(eval_mate ORDER BY ply)[1]` pattern with no SQL color sign flip; added `EVAL_ADVANTAGE_THRESHOLD = 100` and `_classify_endgame_bucket`; updated `_aggregate_endgame_stats`, `_compute_score_gap_material`, `_endgame_skill_from_bucket_rows`; updated model index INCLUDE; created Alembic migration
- All 1172 tests pass; ruff clean; ty zero errors

## Task Commits

1. **Task 1: RED — failing tests for eval-based classification** - `c5da49e` (test)
2. **Task 2: GREEN — production implementation** - `82242ad` (feat)

## Files Created/Modified

- `app/models/game_position.py` - Changed ix_gp_user_endgame_game INCLUDE from `[material_imbalance]` to `[eval_cp, eval_mate]`
- `app/repositories/endgame_repository.py` - Rewrote query_endgame_entry_rows (already done), query_endgame_bucket_rows, query_endgame_elo_timeline_rows; removed `case()` color_sign; removed `PERSISTENCE_PLIES`; removed `case()` imbalance_after_persistence_agg
- `app/services/endgame_service.py` - Replaced `_MATERIAL_ADVANTAGE_THRESHOLD` with `EVAL_ADVANTAGE_THRESHOLD`; added `_classify_endgame_bucket`; updated three aggregation functions
- `alembic/versions/20260502_125433_c92af8282d1a_reshape_ix_gp_user_endgame_game_for_.py` - Symmetric drop+recreate migration
- `tests/test_endgame_repository.py` - Updated `_seed_game_position` to accept `eval_cp`/`eval_mate`; renamed and rewrote three test methods
- `tests/test_endgame_service.py` - Added `TestClassifyEndgameBucket` class (11 cases); updated `_FakeRow`, `_elo_bucket_row`, all row call sites; replaced persistence tests

## Decisions Made

- Sign flip responsibility moved entirely to `_classify_endgame_bucket` in the service layer. SQL projects raw white-perspective values; no `color_sign` case() in any of the three queries. Simpler SQL, single point of sign-flip truth.
- `eval_mate is not None` takes precedence over `eval_cp` in `_classify_endgame_bucket` — guaranteed threshold crossing via ±1_000_000 sentinel.
- NULL eval routes to parity. Same semantics as the old NULL `imbalance_after` parity rule — preserves the sum(material_rows.games) == endgame_wdl.total invariant.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: commit `c5da49e` (test) — tests fail on `ImportError: cannot import name '_classify_endgame_bucket'`
- GREEN gate: commit `82242ad` (feat) — all 1172 tests pass

## Issues Encountered

- Previous session context was lost before any commits were made; this session restarted both tasks from scratch using the plan and context summary.
- `# type: ignore[operator]` needed upgrading to proper `elif eval_cp is not None:` branch to satisfy ty's `unsupported-operator` check on `sign * eval_cp` when eval_cp typed as `int | None`.
- Unused `ty: ignore` directives on `_classify_endgame_bucket` call sites — removed after ty confirmed Row[Any] attribute access does not need suppression.

## Self-Check

Files exist:
- `app/models/game_position.py` — FOUND
- `app/repositories/endgame_repository.py` — FOUND
- `app/services/endgame_service.py` — FOUND
- `alembic/versions/20260502_125433_c92af8282d1a_reshape_ix_gp_user_endgame_game_for_.py` — FOUND

Commits exist:
- `c5da49e` (RED) — FOUND
- `82242ad` (GREEN) — FOUND

## Self-Check: PASSED

## Next Phase Readiness

- Plan 78-06 (cutover execution) can proceed: eval-based classification is wired; the Alembic migration is ready to run against production once eval data is backfilled
- `material_imbalance` column preserved; no risk to other consumers

---
*Phase: 78-stockfish-eval-cutover-for-endgame-classification*
*Completed: 2026-05-02*
