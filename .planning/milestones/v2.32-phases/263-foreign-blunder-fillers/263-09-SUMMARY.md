---
phase: 263-foreign-blunder-fillers
plan: 09
subsystem: api
tags: [train, migration, own-puzzle-count, warmup-retirement, alembic]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: "263-08 legacy-only handling of source 2 rows; 263-02 client reading own_puzzle_count; 263-01 migration b3d5f7a9c264"
provides:
  - "TrainSessionResponse.own_puzzle_count / ComposedSession.own_puzzle_count, derived per response, never persisted"
  - "Lazy completion in _resume_session: an open session with a solve and nothing servable left completes and credits its day"
  - "Migration c4e6a8b0d375: deletes untouched open sessions with an unsolved source 2 row, drops drill_sessions.is_warmup and drill_solves.sharp_puzzle_id"
  - "tests/test_phase_263_migration.py covering both phase migrations (chain, CHECK round trip, data-step controls, column round trip)"
affects: [263-10]

actuals:
  tokens: 72000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Migration data step proven by a rolled-back transaction with negative controls, each guard proven by revert-and-watch-fail"

key-files:
  created:
    - alembic/versions/20261202_130000_c4e6a8b0d375_phase_263_retire_warmup_and_filler_identity.py
    - tests/test_phase_263_migration.py
  modified:
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/routers/train.py
    - app/models/drill_session.py
    - app/models/drill_solve.py
    - tests/repositories/test_train_repository.py
    - tests/repositories/test_train_legacy_filler.py
    - tests/repositories/test_train_foreign.py
    - tests/repositories/test_train_leaderboard_repository.py
    - tests/repositories/test_train_progress_modes.py
    - tests/routers/test_train.py
    - tests/routers/test_train_leaderboard.py
    - tests/services/test_train_settings_service.py
    - tests/test_guest_cleanup_service.py

key-decisions:
  - "Task 2 decision (owner, 2026-11-23): drop. drill_solves.sharp_puzzle_id is dropped in the same migration that drops drill_sessions.is_warmup; the downgrade re-adds both columns empty"
  - "own_puzzle_count is derived (len of surviving SR keys on fresh composition, one COUNT of SR_ITEM rows on resume), never a persisted flag, so D-04 stays retired"
  - "Lazy completion reuses the _mark_session_complete_if_done + apply_day_completion pair record_solve uses, only for an open session with at least one solve and nothing servable"
  - "The migration test runs inside the rolled-back db_session transaction (Postgres DDL is transactional), so no committed seed rows need cleanup"

patterns-established:
  - "Retired identity column handled in the identity-mapping test by mapping the retired source to None"

requirements-completed: [D-03, D-04, D-08, D-12, D-13]

duration: 70min
completed: 2026-11-23
status: complete
plan_head_before: 349bf660cf312469525eff4754124f3ed423340c
plan_head_after: cd4c9893e1e7c115c81da6f7c8f95f0830377719
---

# Phase 263 Plan 09: Warm-up retirement server side and migration c4e6a8b0d375 Summary

**own_puzzle_count derived end to end, resume completes sessions with nothing servable left, and migration c4e6a8b0d375 drops is_warmup and sharp_puzzle_id while clearing untouched sessions stuck on retired lichess fillers.**

## Performance

- **Tasks:** 3 (Task 2 was the owner decision checkpoint, no commit)
- **Commits:** 2 code commits (measured from the ledger base)

## Accomplishments

- **Task 1 (b04c6b5fa):** `ComposedSession.own_puzzle_count` and `TrainSessionResponse.own_puzzle_count` replace the frozen warm-up flag; the model column mapping, schema field and router mapping are gone. `_resume_session` takes `now_utc` and completes an open session that has a solve and no servable puzzle left, crediting the day (the stuck case for legacy rows at deploy and for deleted games).
- **Task 2 (decision, no commit):** the owner answered "drop" on 2026-11-23: `drill_solves.sharp_puzzle_id` is dropped together with `drill_sessions.is_warmup`.
- **Task 3 (cd4c9893e):** migration `c4e6a8b0d375` (head) with `UPGRADE_STATEMENTS` (data DELETE, DROP COLUMN is_warmup, DROP COLUMN sharp_puzzle_id) and `DOWNGRADE_STATEMENTS` (re-add both, empty). `DrillSolve.sharp_puzzle_id` left the model; every test seed that passed it was adjusted (11 test files). No CHECK constraint referenced either dropped column, so none needed handling. `tests/test_phase_263_migration.py` has four tests: chain, CHECK round trip of b3d5f7a9c264 (downgrade deletes source 3 rows before narrowing, then source 3 insert violates, upgrade re-admits), data-step controls, column round trip.

## Mutation checks

- **Task 1 lazy completion:** forcing the new lazy-completion branch in `_resume_session` off made `test_resume_completes_session_whose_remaining_rows_are_unservable` fail while the other 5 tests in that file passed; restored and green.
- **Task 3 data step (each run against `tests/test_phase_263_migration.py`, then restored):**
  - removing the `NOT EXISTS ... solved_at IS NOT NULL` ("has a solve") guard: `test_untouched_open_sessions_with_unsolved_legacy_filler_are_deleted` failed (3 others passed)
  - replacing `s.status = 'open'` with `true`: the same test failed, after the control was tightened (see Deviations)
  - dropping `d.source = 2` from the EXISTS: the same test failed
  - restored: 4 passed.

## Verification observed

- `uv run pytest -n auto -q` (full backend suite, run after the last edit): 7065 passed, 9 skipped.
- Serial `tests/test_phase_263_migration.py tests/routers/test_train.py tests/routers/test_blunder_check_points_migration.py`: 154 passed.
- `uv run ruff check .` clean, `ruff format --check` clean, `uv run ty check app/ tests/ scripts/` clean, `scripts/check_function_size.py app/ --fail-over-depth 4` OK, `uv run alembic heads` prints `c4e6a8b0d375 (head)`.
- `git grep sharp_puzzle_id -- app tests/repositories tests/routers tests/services` is empty; `is_warmup` appears 3 times in the migration (docstring, drop, re-add).
- The dev DB was NOT upgraded (the main checkout's backend reads the dropped columns); the dev upgrade is a manual item for plan 263-10.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test gap] Completed-session control did not isolate the status guard**
- **Found during:** Task 3 mutation check (replacing the status guard left the test green)
- **Issue:** the "completed session with a source 2 row" control had a solved row, so the "no solve" guard alone excluded it and the status guard was untested.
- **Fix:** the completed control (and a new expired control) hold an unsolved legacy row and no solve, so only the status guard keeps them; the mutation now fails the test.
- **Files modified:** tests/test_phase_263_migration.py
- **Commit:** cd4c9893e

**2. [Rule 3 - Blocking] sharp_puzzle_id seeds beyond the plan's file list**
- **Found during:** Task 3 (removing the model column)
- **Issue:** seven more test files than the plan listed passed `sharp_puzzle_id=` (leaderboard, progress modes, foreign, settings service, guest cleanup, plus the identity-mapping test in test_train_repository.py).
- **Fix:** removed the keyword from each seed; in `_IDENTITY_COLUMN_BY_SOURCE` the retired source now maps to `None` and the mutual-exclusivity check covers `herring_pool_id` only.
- **Commit:** cd4c9893e

**3. [Plan wording] Migration test uses the rolled-back db_session** rather than `test_engine.connect()` with committed seeds and `finally` cleanup, since Postgres DDL is transactional; nothing is committed, so no cleanup is needed.

## Known Stubs

None.

## Threat Flags

None. T-263-23 (destructive DELETE) is mitigated by the data-step test with three negative controls and the three mutation results above; T-263-24 by the CHECK round-trip test; T-263-25 by the Task 1 lazy-completion scoping.

## Self-Check: PASSED

- Migration file, `tests/test_phase_263_migration.py` present; commits b04c6b5fa and cd4c9893e are ancestors of HEAD.
