---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "01"
subsystem: backend
tags: [model, migration, database, game_flaws, materialization]
dependency_graph:
  requires: []
  provides:
    - "GameFlaw ORM model (app/models/game_flaw.py)"
    - "game_flaws table with composite PK (user_id, game_id, ply)"
    - "ix_game_flaws_user_severity index"
    - "Model round-trip + CASCADE test coverage"
  affects:
    - "Plans 108-02..08 — all downstream plans read/write game_flaws"
tech_stack:
  added:
    - "GameFlaw SQLAlchemy ORM model (app/models/game_flaw.py)"
    - "Alembic migration a7e0b4796501_add_game_flaws_table"
  patterns:
    - "Composite PK (user_id, game_id, ply) — mirrors game_positions SEED-035"
    - "SmallInteger for ordered enumerations (severity, tempo, phase)"
    - "Typed boolean columns for tag families (is_miss, is_lucky_escape, is_while_ahead, is_result_changing)"
    - "CONCURRENTLY index via autocommit_block"
key_files:
  created:
    - app/models/game_flaw.py
    - alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py
    - tests/test_game_flaws_model.py
  modified:
    - app/models/__init__.py
decisions:
  - "fen stored as String column per RESEARCH §1/Pitfall 4 — avoids O(page × game_length) PGN replay per Flaws-tab request"
  - "ix_game_flaws_game_id plain btree index added alongside the CONCURRENTLY severity index to back CASCADE FK walk on games.id"
  - "Spurious ix_games_evals_pending drop removed from migration (pre-existing model-vs-DB reflection mismatch, same pattern as 02099d78ce65)"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-06"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 1
---

# Phase 108 Plan 01: GameFlaw ORM Model, Migration, and Round-Trip Test Summary

GameFlaw ORM model and Alembic migration creating the `game_flaws` materialization table — composite PK `(user_id, game_id, ply)`, M+B-only severity encoding, typed tag-family columns, display payload (`es_before`, `es_after`, `move_san`, `fen`), and CASCADE FK integrity verified by four green tests.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create the GameFlaw ORM model | 04bffa59 | app/models/game_flaw.py, app/models/__init__.py |
| 2 | Create the Alembic migration for game_flaws | 83babb14 | alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py |
| 3 | Model round-trip + FK CASCADE test | e8e2e16b | tests/test_game_flaws_model.py |

## What Was Built

### GameFlaw ORM model (`app/models/game_flaw.py`)

`class GameFlaw(Base)` with `__tablename__ = "game_flaws"`. Composite PK `(user_id, game_id, ply)` mirrors the `game_positions` SEED-035 pattern. Both FKs use `ondelete="CASCADE"` per the mandatory CLAUDE.md DB design rule. The model encodes the SEED-038 typed-column schema:

- **Severity**: `SmallInteger` 1=mistake, 2=blunder (ordered, never 0=inaccuracy per D-03)
- **Tempo**: nullable `SmallInteger` 0=low-clock, 1=impatient, 2=considered
- **Phase**: non-nullable `SmallInteger` 0=opening, 1=middlegame, 2=endgame
- **Opportunity family**: `is_miss`, `is_lucky_escape` (Boolean, non-nullable)
- **Impact family**: `is_while_ahead`, `is_result_changing` (Boolean, non-nullable)
- **Display payload**: `es_before`, `es_after` (Float), `move_san` (nullable String), `fen` (non-nullable String)
- **Index**: `ix_game_flaws_user_severity` on `(user_id, severity)` for severity scans

### Alembic migration (`20260606_151439_a7e0b4796501_add_game_flaws_table.py`)

Creates the `game_flaws` table with all columns, two FK constraints, composite PK, a plain btree index on `game_id` (backs ON DELETE CASCADE FK walk), and `ix_game_flaws_user_severity` built `CONCURRENTLY` via `autocommit_block`. Added `server_default=""` on `fen` column. Removed the spurious `ix_games_evals_pending` drop that autogenerate emitted (pre-existing model-vs-DB reflection mismatch, same fix as migration `02099d78ce65`). Upgrade/downgrade round-trip verified against the dev DB.

### Tests (`tests/test_game_flaws_model.py`)

Four tests using the `db_session` rollback fixture (no dev DB reset):

1. **Insert round-trip**: all typed columns persist and read back correctly
2. **Composite PK uniqueness**: duplicate `(user_id, game_id, ply)` raises `IntegrityError`
3. **Game CASCADE**: deleting the parent game removes all its `game_flaws` rows
4. **User CASCADE**: deleting the parent user removes all that user's `game_flaws` rows

## Verification

```
uv run alembic upgrade head     → OK
uv run ty check app/ tests/     → All checks passed!
uv run pytest tests/test_game_flaws_model.py -x → 4 passed
```

## Deviations from Plan

**1. [Rule 2 - Missing Critical Functionality] Added ix_game_flaws_game_id plain btree index**

- **Found during:** Task 2 (migration autogenerate output)
- **Issue:** Autogenerate detected the `index=True` on `game_id` in the model and generated `ix_game_flaws_game_id`. The plan mentioned only the CONCURRENTLY severity index. The plain `game_id` index is required to back the ON DELETE CASCADE FK walk on `games.id` — without it, PostgreSQL must do a sequential scan of `game_flaws` for every game delete.
- **Fix:** Kept the autogenerate-detected `ix_game_flaws_game_id` as a regular (non-CONCURRENTLY) index created inside the transaction-safe `create_table` context.
- **Files modified:** `alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py`
- **Commit:** 83babb14

**2. [Rule 1 - Bug] Removed spurious ix_games_evals_pending drop from autogenerate**

- **Found during:** Task 2
- **Issue:** Autogenerate emitted a drop of the pre-existing `ix_games_evals_pending` partial index — a known model-vs-DB reflection mismatch that has appeared before (documented in migration `02099d78ce65`).
- **Fix:** Removed the spurious drop; it is not related to the game_flaws table change.
- **Files modified:** `alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py`
- **Commit:** 83babb14

## Known Stubs

None — this plan creates only the storage layer (model + migration + tests). No UI rendering or data flow stubs.

## Threat Flags

No new network endpoints or auth paths introduced. The `game_flaws` table user-scoping (T-108-01) is established by the `user_id` PK column and both CASCADE FK constraints verified in the test suite (T-108-02). Security mitigations documented in the plan's threat model are fully implemented.

## Self-Check: PASSED
