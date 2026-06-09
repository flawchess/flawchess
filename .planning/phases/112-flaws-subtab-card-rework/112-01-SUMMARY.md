---
phase: 112-flaws-subtab-card-rework
plan: "01"
subsystem: library/flaws
tags: [schema, migration, query, tdd]
dependency_graph:
  requires: []
  provides:
    - "FlawListItem with white_rating/black_rating + eval_cp/eval_mate before/after"
    - "game_positions eval join (two aliased LEFT JOINs) in query_flaws"
    - "game_flaws schema without es_before/es_after/move_san (Alembic migration f8a2d1c9b345)"
    - "flaw_record_to_row stops persisting dropped columns"
  affects:
    - "app/repositories/library_repository.py"
    - "app/schemas/library.py"
    - "app/models/game_flaw.py"
    - "app/repositories/game_flaws_repository.py"
tech_stack:
  added: []
  patterns:
    - "SQLAlchemy aliased() for self-joins on game_positions"
    - "TDD RED/GREEN/REFACTOR flow"
key_files:
  created:
    - alembic/versions/20260609_drop_game_flaws_display_cols.py
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/models/game_flaw.py
    - app/repositories/game_flaws_repository.py
    - tests/test_library_repository.py
    - tests/test_flaws_repository.py
    - tests/test_flaws_materialization.py
    - tests/test_flaw_predicate.py
    - tests/test_library_router.py
    - tests/test_game_flaws_model.py
    - tests/services/test_library_service.py
    - frontend/src/types/library.ts
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
decisions:
  - "LEFT JOIN (outerjoin) used instead of INNER JOIN so flaws at ply=0/1 with no prior position row are not lost"
  - "FlawRecord TypedDict keeps es_before/es_after/move_san for kernel-internal use (Pitfall 6); only the DB write path drops them"
  - "fen column retained in game_flaws: game_positions stores only Zobrist hashes, not FEN strings (Pitfall 4)"
metrics:
  duration: "session-spanning (context compaction mid-execution)"
  completed: "2026-06-09"
  tasks_completed: 3
  files_changed: 13
---

# Phase 112 Plan 01: Schema slim + eval join Summary

Slimmed `game_flaws` schema by dropping display-only columns `es_before`, `es_after`, `move_san`, and re-sourced those values at query time via two aliased LEFT JOINs on `game_positions` (ply N for move/eval-after, ply N-1 for eval-before). Added `white_rating`, `black_rating`, and raw before/after eval fields (`eval_cp_before`, `eval_mate_before`, `eval_cp_after`, `eval_mate_after`) to `FlawListItem`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Add failing tests for eval join + schema | 71db9330 | tests/test_library_repository.py, tests/test_flaws_repository.py |
| 1+2 | Add game_positions eval join + update FlawListItem schema | c3068e3f | app/repositories/library_repository.py, app/schemas/library.py, frontend/src/types/library.ts, frontend/src/pages/library/__tests__/FlawsTab.test.tsx |
| 3 | Drop columns: model + migration + classifier write-path | f3613ea6 | app/models/game_flaw.py, app/repositories/game_flaws_repository.py, alembic/versions/20260609_drop_game_flaws_display_cols.py, 9 test files |

## Key Changes

### FlawListItem schema (app/schemas/library.py)
- Removed: `es_before: float`, `es_after: float`
- Added: `eval_cp_before: int | None`, `eval_mate_before: int | None`, `eval_cp_after: int | None`, `eval_mate_after: int | None`, `white_rating: int | None`, `black_rating: int | None`
- `move_san: str | None` retained but now sourced from `game_positions` join (not stored in `game_flaws`)

### query_flaws join (app/repositories/library_repository.py)
Two aliased LEFT JOINs added to the base statement:
- `PositionAt = aliased(GamePosition, name="pos_at")` — ply=N: move_san + eval_after
- `PositionBefore = aliased(GamePosition, name="pos_before")` — ply=N-1: eval_before

Join conditions are scoped on `(game_id, user_id, ply)` to prevent cross-user data leakage (T-112-02 IDOR mitigation).

### game_flaws schema (D-07)
- Removed columns: `es_before FLOAT`, `es_after FLOAT`, `move_san VARCHAR`
- Kept: `fen VARCHAR` (cannot be recovered from Zobrist hashes — Pitfall 4)
- Migration revision: `f8a2d1c9b345` (down_revision `e1a7c93b6f02`)

### flaw_record_to_row write-path (app/repositories/game_flaws_repository.py)
Removed `"es_before"`, `"es_after"`, `"move_san"` keys from the returned dict. The `FlawRecord` TypedDict still carries these fields for kernel-internal use (Pitfall 6) — they are intentionally not persisted.

## TDD Gate Compliance

- RED commit: `71db9330` — `test(112-01): add failing tests for eval join + schema (RED)`
- GREEN commit: `c3068e3f` — `feat(112-01): add game_positions eval join + update FlawListItem schema (Tasks 1+2)`
- Task 3 commit: `f3613ea6` — schema drop gated on Pitfall-1 regression guard passing first

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing fix] test_library_router.py _seed_flaw_committed still used dropped columns**
- **Found during:** Task 3 test run
- **Issue:** `_seed_flaw_committed` in `tests/test_library_router.py` passed `es_before`, `es_after`, `move_san` to the `GameFlaw` ORM constructor after the migration dropped those columns, causing `TypeError` on all router tests.
- **Fix:** Removed the three dropped params from the helper signature and constructor call.
- **Files modified:** `tests/test_library_router.py`
- **Commit:** f3613ea6 (included in Task 3 commit)

**2. [Rule 2 - Missing fix] test_game_flaws_model.py still asserted dropped columns**
- **Found during:** ty check after Task 3
- **Issue:** `_make_flaw_row` and `test_insert_and_read_back` referenced `es_before`, `es_after`, `move_san` on `GameFlaw` ORM model that no longer had those attributes.
- **Fix:** Removed from constructor, replaced assertions with `not hasattr` guards.
- **Files modified:** `tests/test_game_flaws_model.py`
- **Commit:** f3613ea6

**3. [Rule 2 - Missing fix] tests/services/test_library_service.py had two constructor callsites**
- **Found during:** test run after Task 3
- **Issue:** Both `_make_game_flaw` (attribute assignment path) and `_seed_db_game_flaw` (constructor kwarg path) still used the dropped columns.
- **Fix:** Removed dropped fields from both callsites.
- **Files modified:** `tests/services/test_library_service.py`
- **Commit:** f3613ea6

## Known Stubs

None. All new fields (`eval_cp_before`, `eval_mate_before`, `eval_cp_after`, `eval_mate_after`, `white_rating`, `black_rating`, `move_san`) are wired to live data from the `game_positions` join and `games` table.

## Threat Flags

None. The two aliased LEFT JOINs are scoped on `(game_id, user_id, ply)` — the `user_id` clause is the T-112-02 IDOR mitigation, preventing one user from reading another user's position rows.

## Self-Check: PASSED

- [x] `app/schemas/library.py` exists with `eval_cp_before`, `white_rating` fields
- [x] `app/repositories/library_repository.py` has `aliased(GamePosition, name="pos_at")`
- [x] `app/models/game_flaw.py` has no `es_before`/`es_after`/`move_san` mapped columns
- [x] `alembic/versions/20260609_drop_game_flaws_display_cols.py` exists with revision `f8a2d1c9b345`
- [x] Commits `71db9330`, `c3068e3f`, `f3613ea6` all present in git log
- [x] 113 backend tests pass; 839 frontend tests pass; ty clean; ruff clean
