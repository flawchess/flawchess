---
phase: quick-260603-o8m
plan: 01
subsystem: database / game_positions
tags: [SEED-035, schema, alembic, composite-pk, index-bloat, ops-script]
requires:
  - alembic head 84fd28051d7d (SEED-033 partial hash indexes)
provides:
  - game_positions natural composite PK (user_id, game_id, ply)
  - committed prod-only reindex ops script (bin/reindex_game_positions.sh)
affects:
  - app/models/game_position.py
  - scripts/backfill_eval.py
  - tests/repositories/test_opening_insights_repository.py
tech-stack:
  added: []
  patterns:
    - "Fresh CONCURRENTLY unique index + ADD CONSTRAINT ... USING INDEX promotion (partial+INCLUDE index cannot be promoted in place)"
    - "Pre-drop FK guard via DO/RAISE block at top of upgrade()"
key-files:
  created:
    - alembic/versions/20260603_153628_f4d88c3659c6_gp_natural_composite_pk_seed_035.py
    - bin/reindex_game_positions.sh
  modified:
    - app/models/game_position.py
    - scripts/backfill_eval.py
    - tests/repositories/test_opening_insights_repository.py
decisions:
  - "PK index built fresh (not USING INDEX on ix_gp_user_game_ply) because that index is partial + INCLUDE and cannot back a PK"
  - "ix_game_positions_game_id kept (backs CASCADE FK, 467k scans); its bloat reclaimed by the separate ops script, not the migration"
  - "Reindex quick-win scoped to exactly 2 indexes (the migration rebuilds/drops the other 2)"
metrics:
  duration: ~25min
  completed: 2026-06-03
  commits: 4
  files_changed: 5
---

# Quick Task 260603-o8m: SEED-035 game_positions Natural Composite PK Summary

Replaced the ~1.3 GB surrogate `game_positions.id` PK with the natural composite PK
`(user_id, game_id, ply)`, dropped the redundant `ix_gp_user_game_ply` index, rekeyed
the eval-backfill script onto `(game_id, ply)`, and shipped a committed (unrun) prod-only
reindex ops script for the two indexes the migration leaves bloated.

## What Was Built

- **Hand-written Alembic migration** (`f4d88c3659c6`): pre-drop FK guard → fresh
  non-partial `uq_gp_user_game_ply` UNIQUE index built CONCURRENTLY → `ADD CONSTRAINT
  ... PRIMARY KEY USING INDEX` promotion (renames to `game_positions_pkey`) → drop
  surrogate `id` column → drop `ix_gp_user_game_ply` CONCURRENTLY. `ix_game_positions_game_id`
  explicitly retained. Round-trips upgrade→downgrade→upgrade on the dev DB.
- **ORM model**: composite PK on `user_id`/`game_id`/`ply`, surrogate `id` removed,
  `ix_gp_user_game_ply` `Index()` block removed from `__table_args__` (tombstone comment),
  `game_id` keeps `index=True` (`ix_game_positions_game_id`).
- **backfill_eval.py**: batched `UPDATE ... FROM (VALUES ...)` now joins on
  `(game_id, ply)` instead of the dropped `id`; SELECTs, write-buffer tuple shape, param
  prefixes (`gid_`/`ply_`), type annotations, docstrings, and the Sentry context dict all
  rekeyed. No `GamePosition.id` / `row.id` / `id_{` references remain (grep clean).
- **bin/reindex_game_positions.sh**: prod-only, human-run, tunnel + privileged-role
  guarded, no committed secrets. `REINDEX INDEX CONCURRENTLY` for exactly
  `ix_gp_user_endgame_game` + `ix_game_positions_game_id`. `--dry-run` prints commands
  without connecting; `--verify` reports index sizes. Validated with `bash -n` + dry-run
  only — NOT executed against any DB.

## Migration Strategy (chosen approach)

The seed proposed promoting `ix_gp_user_game_ply` to the PK in place via
`ADD CONSTRAINT ... PRIMARY KEY USING INDEX`. That is **impossible**: the index is a
*partial* index (`WHERE ply BETWEEN 0 AND 17`) with `INCLUDE(full_hash, move_san)`, and a
PRIMARY KEY requires a non-partial unique index over exactly the key columns. So the PK
index was built **fresh** (`uq_gp_user_game_ply`, CONCURRENTLY, non-partial, no INCLUDE),
then promoted via `USING INDEX` (no second build), then `id` dropped, then the old partial
index dropped. All wrapped in one `op.get_context().autocommit_block()` because
CONCURRENTLY cannot run in a transaction.

## Seed-Spec Corrections Applied

1. The seed claimed the only `id` consumers were two `COUNT(gp.id)` calls in
   `position_bookmark_repository.py`. **Those no longer exist** — no edit was made there.
2. The **real** load-bearing `GamePosition.id` consumer was `scripts/backfill_eval.py`
   (SELECTs `id`, threads `row.id` through the write buffer, JOINs on `gp.id = v.id`).
   Rekeyed onto `(game_id, ply)`.
3. The `USING INDEX`-in-place promotion was not possible (see Migration Strategy).
4. The COPY import path already excluded `id`; its coverage test filters `c.name != "id"`
   and self-healed. No edit needed.

## Quick-Win Scope Reduction

The seed listed four bloated indexes for a REINDEX pass. The migration rebuilds/drops two,
so only two still need reindexing:
- `game_positions_pkey` → rebuilt fresh by the migration ⇒ not bloated ⇒ excluded.
- `ix_gp_user_game_ply` → dropped by the migration ⇒ excluded.
- `ix_gp_user_endgame_game` (~622 MB) → untouched by the migration ⇒ included.
- `ix_game_positions_game_id` (~452 MB) → kept-not-rebuilt ⇒ included.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retargeted stale index test to the composite PK**
- **Found during:** Task 3 (full-suite gate)
- **Issue:** `tests/repositories/test_opening_insights_repository.py::test_partial_index_predicate_alignment`
  hard-asserted that `ix_gp_user_game_ply` (with its partial predicate + INCLUDE columns)
  exists in the DB. SEED-035 deliberately drops that index, so the test failed.
- **Fix:** The `(user_id, game_id, ply)` ordered access path the test guards is now served
  by `game_positions_pkey`. Re-pointed the test to assert the PK's key columns and their
  order; dropped the now-inapplicable partial-predicate and INCLUDE assertions. Updated the
  module docstring precondition. The test's intent (the window function's ordered key path
  exists) is preserved.
- **Files modified:** tests/repositories/test_opening_insights_repository.py
- **Commit:** ed5cf4c6

### Out-of-scope discovery (NOT actioned)

The autogenerate drift check surfaced one drift item: `ix_games_evals_pending` on the
`games` table. This is a **pre-existing** model-vs-DB reflection quirk documented in
migration `20260531_082903_02099d78ce65` and predates this task's base commit. It does not
touch `game_positions`, `games.py` was not modified by this task, and it is unrelated to
SEED-035. Left untouched per the scope boundary. The `game_positions` portion of the
autogenerate check was empty (ORM and migration agree); the throwaway drift-check revision
was deleted.

## Deferred DEPLOY / HUMAN-UAT Items

1. **Prod-scale CONCURRENTLY index build timing.** The migration's fresh ~500 MB unique
   index build against prod's 36.5M-row table was NOT timed here (dev table is tiny). Time
   it against a prod-sized dataset before the deploy. Migrations run automatically on
   backend container start, so the build runs unattended at deploy — confirm it completes
   within an acceptable window.
2. **Actual prod execution of bin/reindex_game_positions.sh.** The reindex quick win is
   SHIPPED as a committed, self-documenting ops script but is UNRUN. Running it against prod
   (tunnel open + privileged role) is a human deploy-time step. Expected reclaim: combined
   with the migration's PK shrink (~1.45 GB), ~1 GB more from this reindex pass.

## Verification

- `alembic upgrade head` applies cleanly; upgrade→downgrade→upgrade round-trips; single head.
- `\d game_positions` confirms PK `(user_id, game_id, ply)`, no `id` column, no
  `ix_gp_user_game_ply`, `ix_game_positions_game_id` retained.
- `uv run ty check app/ tests/` → zero errors.
- `uv run pytest -n auto -x` → 2243 passed, 10 skipped.
- ruff format + check clean.
- Autogenerate drift for `game_positions` → empty; throwaway file deleted.
- `bash -n bin/reindex_game_positions.sh` clean; script scoped to exactly the two correct
  indexes; NOT executed against any DB; no committed secrets.

## Commits

- adc0864f: feat — migration for game_positions natural composite PK (SEED-035)
- 694f361a: feat — ORM composite PK + rekey backfill_eval onto (game_id, ply)
- 9eae456c: feat — prod-only reindex ops script for game_positions bloat
- ed5cf4c6: test — retarget index test to composite PK after SEED-035 drop

## Self-Check: PASSED

All created files exist on disk; all four task commits exist in git history.
