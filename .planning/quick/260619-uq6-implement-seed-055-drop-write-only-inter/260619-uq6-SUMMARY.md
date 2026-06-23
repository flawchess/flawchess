---
quick_id: 260619-uq6
title: "Drop 7 write-only intermediate columns from game_positions (SEED-055)"
status: complete
date: 2026-06-19
commit: 41638075
---

# Quick Task 260619-uq6 — Summary

Implemented SEED-055: dropped the 7 `game_positions` columns that were computed at
import and written but never read by any serving query, and moved the seed to
`.planning/seeds/closed/`.

## Dropped columns

`material_count`, `material_imbalance`, `has_opposite_color_bishops`,
`material_signature`, `piece_count`, `backrank_sparse`, `mixedness`.

## Decisions (asked during execution)

- **Drop `material_signature` too** (the seed flagged it for a conscious decision).
  It is 71% of the disk prize and reversible (re-add + PGN-replay backfill if a
  future `endgame_class` reclassification is ever needed). User chose drop-all-7.
- **Remove `reclassify_positions.py` + `test_reclassify.py` + its CLAUDE.md entry.**
  The script's only function was backfilling these raw classification columns; it
  never recomputed `endgame_class`/`phase`, so with the columns gone it had no
  surviving job. User chose removal over repurposing.

## Key principle preserved

`endgame_class` (from `material_signature`) and `phase` (from
`piece_count`/`backrank_sparse`/`mixedness`) are still computed **in-memory** at
import time in `position_classifier.py` + `zobrist.py`, then persisted. Only the
raw intermediate columns were dropped.

## Changes

- **Source:** `app/models/game_position.py`, `app/services/position_classifier.py`
  (removed the 3 fully-dead compute fns + `_side_material` + `_MATERIAL_VALUE_CP`),
  `app/services/zobrist.py` (PlyData), `app/services/import_service.py` (row dict),
  `app/repositories/game_repository.py` (`POSITION_COPY_COLUMNS`),
  `app/services/eval_drain.py` (placeholder dict).
- **backfill_eval.py:** removed the now-obsolete PHASE-FILL-01 phase-backfill block
  (it derived `phase` FROM the dropped columns) + its now-unused threshold imports
  and `PHASE_BACKFILL_CHUNK_SIZE`.
- **Migration:** `b8fddd63bd95` drops the 7 columns. Documents that `DROP COLUMN`
  does not reclaim disk on existing rows — a `pg_repack`/`VACUUM FULL` prod rewrite
  is a separate operational step (NOT in this migration). New rows are 34B smaller.
- **Tests:** removed the 7 columns from every fixture/row-dict/setattr/helper-param
  site; removed the `material_count`/`material_imbalance`/`has_opposite_color_bishops`
  unit tests and the import-service material assertions; trimmed the column-coverage
  `optional_cols` set. Signature/piece_count/backrank/mixedness predicate tests kept.
- **CLAUDE.md:** removed the `reclassify_positions.py` scripts entry.

## Verification

- Migration round-trips on dev DB (upgrade → downgrade → upgrade).
- `ruff format --check` + `ruff check` (app/ tests/) clean; `ty check app/ tests/`
  zero errors.
- Full backend suite green: **2785 passed, 15 skipped**.
- No frontend files touched (frontend gate not applicable).
- Final grep confirms zero persisted-column references remain (only in-memory
  derivation, comments, and the migration).

## Operational follow-up (NOT done here)

To reclaim the ~1.6 GB on prod's existing ~46.7M rows, a one-time table rewrite
(`pg_repack` online, or `VACUUM FULL`) is required after this ships. Forward-going
the row-size reduction is automatic.
