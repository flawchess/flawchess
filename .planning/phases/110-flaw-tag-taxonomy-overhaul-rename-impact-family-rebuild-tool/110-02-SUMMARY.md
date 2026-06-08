---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
plan: 02
subsystem: api
tags: [python, alembic, migration, flaws, model, repository, tests]

# Dependency graph
requires:
  - 110-01 (FlawTag Literals reversed/squandered emitted by classifier)
provides:
  - "game_flaws DB columns is_reversed/is_squandered (NOT NULL, no server_default)"
  - "Dropped columns: is_while_ahead, is_result_changing"
  - "Forward alter migration 20260607_alter_game_flaws_impact_cols.py with down_revision=a7e0b4796501"
  - "flaw_record_to_row writer maps 'reversed'->is_reversed, 'squandered'->is_squandered"
  - "_TEMPO_INT keys renamed: impatient->hasty, considered->unrushed"
  - "Tests updated: test_game_flaws_model.py, test_flaws_materialization.py"
affects:
  - 110-03-PLAN.md (library_repository/service/router downstream updates)
  - 110-04-PLAN.md (library_service tempo/impact field renames)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "add-NOT-NULL-with-server_default-then-drop-default pattern for ALTER TABLE on existing data (precedent 24baa961e5cf)"
    - "Alembic alter migration: drop old cols + add new cols with transient server_default, then alter_column to remove it"
    - "Migration literal sa.* types only -- no app constants imported"

key-files:
  created:
    - alembic/versions/20260607_alter_game_flaws_impact_cols.py
  modified:
    - app/models/game_flaw.py
    - app/repositories/game_flaws_repository.py
    - tests/test_game_flaws_model.py
    - tests/test_flaws_materialization.py

key-decisions:
  - "D-01 (retained): existing rows get false placeholder via transient server_default; correct values come from Plan 03 dev backfill"
  - "add-NOT-NULL-then-drop-default pattern preserves sibling no-server_default convention (is_miss/is_lucky_escape)"
  - "down_revision verified via uv run alembic heads before migration was written"

# Metrics
duration: 22min
completed: 2026-06-07
---

# Phase 110 Plan 02: DB Schema + Writer Migration Summary

**Forward Alembic alter migration dropping is_while_ahead/is_result_changing and adding is_reversed/is_squandered; updated flaw_record_to_row writer and tests; round-trip verified on existing dev DB without reset**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-06-07T20:30:17Z
- **Tasks:** 3
- **Files modified:** 4
- **Files created:** 1

## Accomplishments

- Renamed `GameFlaw` ORM columns: `is_while_ahead` -> `is_reversed`, `is_result_changing` -> `is_squandered` (both Boolean NOT NULL, no server_default matching sibling `is_miss`/`is_lucky_escape` convention); updated tempo comment (impatient/considered -> hasty/unrushed)
- Updated `_TEMPO_INT` map keys in `game_flaws_repository.py`: `"impatient"->1` -> `"hasty"->1`, `"considered"->2` -> `"unrushed"->2`
- Updated `flaw_record_to_row` writer lines: `"is_while_ahead": "while-ahead" in tags` -> `"is_reversed": "reversed" in tags`; `"is_result_changing": "result-changing" in tags` -> `"is_squandered": "squandered" in tags`
- Created `alembic/versions/20260607_alter_game_flaws_impact_cols.py` with `down_revision="a7e0b4796501"` (verified current head), using add-NOT-NULL-with-server_default-then-drop pattern
- Forward migration applied to existing dev DB without reset; upgrade/downgrade/upgrade round-trip all succeed
- DB confirmed via information_schema: `is_reversed`/`is_squandered` present (nullable=NO, no server_default), `is_while_ahead`/`is_result_changing` absent
- Updated 28 tests (both test files): renamed impact column assertions, tempo tag names (impatient->hasty, considered->unrushed), tag strings in flaw fixtures; 28 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename model columns + update the FlawRecord->row writer** - `31b9899d` (feat)
2. **Task 2: Write the forward Alembic alter migration** - `66664858` (feat)
3. **Task 3: Update model + materialization tests** - `4c89204a` (test)

## Files Created/Modified

- `app/models/game_flaw.py` - Renamed is_while_ahead->is_reversed, is_result_changing->is_squandered; updated tempo comment
- `app/repositories/game_flaws_repository.py` - _TEMPO_INT keys hasty/unrushed; writer lines map reversed/squandered tags
- `alembic/versions/20260607_alter_game_flaws_impact_cols.py` - New alter migration, down_revision=a7e0b4796501
- `tests/test_game_flaws_model.py` - Renamed column assertions in _make_flaw_row and round-trip test
- `tests/test_flaws_materialization.py` - Renamed tempo test methods, impact boolean tests, bulk-insert fixture, boolean_columns assertions

## Decisions Made

- Migration uses add-NOT-NULL-with-server_default-then-drop pattern so existing rows get a valid `false` placeholder while the model carries no server_default (matching is_miss/is_lucky_escape).
- down_revision verified with `uv run alembic heads` (returned `a7e0b4796501 (head)`) before writing the migration.
- Existing test failures in `test_library_service.py` (`test_chips_exclude_phase_and_dedupe`) are pre-existing from Plan 01 (confirmed via git stash check) and are in scope for Plan 03 -- not introduced by this plan.

## Deviations from Plan

### Known Pending (Not Auto-fixed)

**1. [Scope Limitation] test_library_service.py pre-existing failure**
- **Found during:** Overall verification (uv run pytest -n auto -x)
- **Issue:** `test_chips_exclude_phase_and_dedupe` in `tests/services/test_library_service.py` references old tag names (`impatient`, `while-ahead`, `is_while_ahead`). This failure existed before Plan 02 changes (confirmed by reverting and running the same test).
- **Why not fixed:** This test is in the library_service test file which is explicitly out of scope for Plan 02 (the plan header: "ty may still report errors in app/services/library_service.py / library_repository.py / routers/library.py -- those are fixed in Plan 03"). Fixing it here would make Plan 03 changes redundant or conflicted.
- **Resolution:** Will be fixed in Plan 03 along with the full library_service/library_repository/router downstream updates.

---

**Total deviations:** 1 known-pending (pre-existing, Plan 03 scope)

## Threat Flags

None. Pure internal schema DDL + in-process column writer rename. No new external input, auth, or data exposure.

## Self-Check: PASSED

- `app/models/game_flaw.py` contains `is_reversed`: FOUND (line 54)
- `app/repositories/game_flaws_repository.py` contains `is_reversed`: FOUND (line 109)
- `alembic/versions/20260607_alter_game_flaws_impact_cols.py` exists and contains `a7e0b4796501`: FOUND
- DB column `is_reversed` present in game_flaws (information_schema confirmed): FOUND
- DB column `is_while_ahead` absent from game_flaws: CONFIRMED ABSENT
- Task 1 commit `31b9899d`: FOUND
- Task 2 commit `66664858`: FOUND
- Task 3 commit `4c89204a`: FOUND
- 28 tests (test_game_flaws_model.py + test_flaws_materialization.py): ALL PASSED
