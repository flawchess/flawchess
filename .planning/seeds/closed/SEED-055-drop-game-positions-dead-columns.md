---
title: Drop write-only intermediate columns from game_positions
trigger_condition: Next migration phase that touches game_positions, OR prod disk pressure returns. Bundle the column drop with a pg_repack rewrite so the table is rewritten once.
planted_date: 2026-06-19
---

# Drop write-only intermediate columns from `game_positions`

## Idea

`game_positions` (the largest table — prod: ~46.7M rows, 6130 MB heap, 11 GB
incl. indexes) carries 7 columns that are **computed at import and written, but
never read by any serving query**. Only the *derived* columns `endgame_class`
and `phase` are consumed. Dropping the 7 frees ~1.6 GB of heap content (~26%)
and shrinks every future import row by 34 bytes.

## Consumption audit (verified 2026-06-19)

None of the 7 is read anywhere:
- Repositories (`endgame_repository`, `stats_repository`, `library_repository`)
  filter/group on `endgame_class` and `phase` only.
- `scripts/reclassify_positions.py` replays the stored PGN through `chess.Board`
  + `classify_position()` — does NOT read these columns.
- Frontend / `app/schemas/` have zero exposure (only a stale comment in
  `endgames.py`).
- `scripts/backfill_eval.py` reads `piece_count`/`backrank_sparse`/`mixedness`
  to locate endgames, but that's redundant with the stored `endgame_class`/
  `phase`, and it's a one-off backfill, not a serving path.
- No index references any of the 7 columns.

## Two groups

**Fully dead — stop computing AND storing:**
- `material_count` — computed, stored, never read.
- `material_imbalance` — killed by REFAC-02 (single-point eval replaced the
  imbalance + 4-ply persistence proxy).
- `has_opposite_color_bishops` — computed, stored, never read.

**Intermediate — keep computing in-memory, drop the persisted copy:**
- `material_signature` — feeds `classify_endgame_class()` → `endgame_class`.
- `piece_count` — feeds `is_endgame` / `is_middlegame`.
- `backrank_sparse` — feeds `is_middlegame`.
- `mixedness` — feeds `is_middlegame`.

## Disk reclaim (prod, measured)

avg `pg_column_size` per row × 46.71M rows:

| Column | Bytes/row | Prod content |
|---|---|---|
| `material_signature` | 24.22 | **~1,131 MB** |
| `material_count` | 2.00 | ~93 MB |
| `material_imbalance` | 2.00 | ~93 MB |
| `piece_count` | 2.00 | ~93 MB |
| `mixedness` | 2.00 | ~93 MB |
| `has_opposite_color_bishops` | 1.00 | ~47 MB |
| `backrank_sparse` | 1.00 | ~47 MB |
| **Total** | **34.22** | **~1.60 GB (≈26% of 6.1 GB heap)** |

`material_signature` is **71% of the prize**. If only one column is dropped,
drop that one.

## Caveats that shape the ROI

1. **`DROP COLUMN` does not reclaim disk.** Postgres just flags `attisdropped`;
   bytes stay in every existing tuple. `game_positions` is append-only (never
   UPDATEd post-import), so no natural churn reclaims it. To realize the 1.6 GB
   on existing rows you need a full rewrite: `VACUUM FULL` (ACCESS EXCLUSIVE
   lock = downtime) or `pg_repack` (online, needs ~2× free space + extension).
   Without a rewrite the only benefit is forward-going (smaller future rows).
   → **This is why the trigger says to bundle with a planned rewrite.**
2. **Alignment padding shrinks the fixed-width reclaim.** The four `smallint`s
   (2B) + two `bool`s (1B) pack into the aligned fixed-width region; dropping
   one bool in isolation may net ~0 bytes after re-pack. `material_signature`
   (varlena) is the only column with guaranteed, large, independent savings
   (~1.1 GB). Treat ~1.6 GB as the all-seven-plus-rewrite figure; ~1.1 GB is the
   safe high-confidence portion.

## Latent value being given up

`material_signature` is the only column that would allow reclassifying
`endgame_class` via a cheap pure-Python pass (`classify_endgame_class` is a pure
function of it) instead of replaying every PGN. Currently unused —
`reclassify_positions.py` replays PGN — but worth a conscious decision before
dropping it.

## Implementation touch points (when actioned)

Remove from: `app/models/game_position.py`, `POSITION_COPY_COLUMNS` in
`app/repositories/game_repository.py`, the insert dict in
`app/services/import_service.py`, the placeholder dict in
`app/services/eval_drain.py`, the mapping in `app/services/zobrist.py`, and the
column-coverage test (`test_bulk_insert_positions_column_coverage`). Keep the
in-memory computations in `position_classifier.py` for the intermediate group;
drop them for the fully-dead group. Alembic migration to `DROP COLUMN` + a
planned `pg_repack`/`VACUUM FULL` window on prod.
