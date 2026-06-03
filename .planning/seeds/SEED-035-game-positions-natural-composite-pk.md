---
id: SEED-035
status: resolved
resolved: 2026-06-03
resolved_by: quick task 260603-o8m (commits adc0864f migration, 694f361a ORM+backfill, 9eae456c reindex script, ed5cf4c6 test). Code shipped to main; prod-scale CONCURRENTLY timing + the actual prod run of scripts/reindex_game_positions.py remain DEPLOY/HUMAN-UAT.
planted: 2026-06-01
planted_during: prod /db-report 2026-06-01 review. While comparing index sizes against the 2026-05-29 snapshot (the 2026-05-31 reindex of the three Zobrist hash indexes had just dropped the DB from 14 GB to 9.6 GB), the surrogate `game_positions.id` PK surfaced as the single largest object in the database (1,300 MB) with zero genuine scans and no inbound foreign keys. User proposed promoting a natural composite key.
trigger_when: When reclaiming storage on the largest table becomes worth a migration on it, or alongside a future game_positions schema change so the table is rewritten/reindexed once. Not urgent — no correctness or performance problem today, purely ~1.45 GB of recoverable space. Promote via /gsd-review-backlog.
scope: phase (TBD) — DB migration + ORM model change + small repository edits. Touches the largest table (36.5M rows); must use CONCURRENTLY operations and be validated against a prod-sized dataset.
depends_on: none. Independent of v1.23 LLM work. Can land whenever.
---

# SEED-035: Replace `game_positions` surrogate PK with natural composite `(user_id, game_id, ply)`

## The ask

`game_positions` currently has a surrogate `id integer` primary key. Its index
(`game_positions_pkey`) is **1,300 MB — the single largest object in the database** (the table
itself is 4.7 GB data + 3.7 GB indexes = 8.4 GB, 85% of the 9.6 GB prod DB). The surrogate buys
nothing:

- **No inbound foreign keys** reference `game_positions.id` (verified via `pg_constraint`:
  `confrelid = 'game_positions'` returns empty). Bookmarks match on Zobrist hashes, not row id.
- **Zero genuine lookups by id.** `game_positions_pkey` shows 0 scans, and that zero is real —
  its size was unchanged (1,300 MB) across the 2026-05-29 and 2026-06-01 snapshots, so unlike the
  three hash indexes it was *not* reindexed (a `REINDEX CONCURRENTLY` would have reset the counter
  by swapping OID). No query does `WHERE id = ?`; `id` appears only in `COUNT(gp.id)`.
- `(game_id, ply)` is a **provably unique natural key**: 36,572,979 rows, 36,572,979 distinct
  `(game_id, ply)` pairs (one position per ply per game). `user_id` is functionally determined by
  `game_id`, so `(user_id, game_id, ply)` is trivially unique too.

## The design (decided during exploration)

Promote the existing `ix_gp_user_game_ply` index `(user_id, game_id, ply)` to be the primary key
and drop the surrogate `id` column. That index is already a unique index in disguise.

**Why `(user_id, game_id, ply)` and not `(game_id, ply)`:** `user_id`-leading matches the dominant
"my pieces / my games" access pattern, and it lets the new PK *absorb* `ix_gp_user_game_ply`
(511 MB, 225k scans — identical columns, identical order) at no net index cost.

**Critical constraint — you can retire exactly ONE of the two game-keyed indexes, not both.**
A btree PK has a single column order:

| Index | Columns | Scans | Absorbed by `(user_id, game_id, ply)` PK? |
|---|---|---|---|
| `ix_gp_user_game_ply` | `(user_id, game_id, ply)` | 224,935 | YES — identical columns/order |
| `ix_game_positions_game_id` | `(game_id)` | 467,479 | NO — `game_id` is the 2nd PK column; can't be seeked without `user_id` |

`ix_game_positions_game_id` **must be kept** for two independent reasons:
1. It is the more-used of the two (467k vs 225k scans). Many queries key on `game_id` with no
   leading `user_id` predicate — `JOIN games ON games.id = gp.game_id` nested-loop lookups and
   `gp.game_id.in_(...)` in `stats_repository.py`, `openings_repository.py`,
   `position_bookmark_repository.py`. A `user_id`-leading index cannot serve these.
2. The FK `game_positions_game_id_fkey` is `ON DELETE CASCADE`, and PostgreSQL does **not**
   auto-index FK referencing columns. Without a `game_id`-leading index, every game delete /
   reimport seq-scans 36.5M rows to find children.

## Net storage effect (≈ −1.45 GB on an 8.4 GB table)

| Object | Before | After |
|---|---|---|
| `game_positions_pkey` (surrogate `id`) | 1,300 MB | gone |
| `id` column data | ~140 MB | gone |
| `ix_gp_user_game_ply` | 511 MB | gone (becomes the PK) |
| new PK `(user_id, game_id, ply)` | — | ~500 MB |
| `ix_game_positions_game_id` | 452 MB | **kept** |

Heap table, so no physical reorg is forced by changing the PK.

## What to do when this is promoted

- **Migration**: add the composite PK and drop the surrogate `id`. Use `CONCURRENTLY` for any new
  index build and validate timing against a prod-sized dataset (36.5M rows) before running on prod;
  the existing `ix_gp_user_game_ply` may be promotable in place to avoid a fresh ~500 MB build.
  Drop `ix_gp_user_game_ply` only after the PK exists. **Keep `ix_game_positions_game_id`.**
- **ORM** (`app/models/game_position.py`): set `primary_key=True` on `user_id`, `game_id`, `ply`;
  remove the `id` `mapped_column`. Audit `relationship()` definitions and the identity map for any
  reliance on a single-column PK.
- **Code**: swap the two `COUNT(gp.id)` usages (bookmark depth / past-cap queries in
  `position_bookmark_repository.py`) to `COUNT(*)`. Grep for any other `GamePosition.id` /
  `.id` references. The `COPY`-based bulk import already supplies `game_id`, `user_id`, `ply` and
  does not insert `id`, so the import path needs no change for column supply (verify it doesn't
  read back generated ids).
- **Verify**: no inbound FKs exist today, but re-confirm before dropping `id` in case a new table
  was added that references it.

## Separate, lower-risk quick win (do NOT bundle unless convenient)

Independent of this redesign: `game_positions_pkey` (1,300 MB), `ix_gp_user_endgame_game`
(622 MB), `ix_gp_user_game_ply` (511 MB), and `ix_game_positions_game_id` (452 MB) are all carrying
bloat — only the three hash indexes were reindexed on 2026-05-31. A `REINDEX INDEX CONCURRENTLY`
pass over the four reclaims an estimated ~1 GB with zero schema or code change. If this seed is
promoted, the redesign makes the PK/game_ply reindex moot (those indexes are dropped/rebuilt
anyway), but `ix_gp_user_endgame_game` and `ix_game_positions_game_id` would still benefit.

## Cross-references

- Prod DB report: `reports/db-stats/db-report-prod-2026-06-01.md` (storage + index-usage sections).
- Prior snapshot for index-size deltas: `reports/db-stats/db-report-prod-2026-05-29.md`.
- Related partial-index work on the same table: `SEED-033` (Zobrist hash partial indexes at ply ≤ 28).
