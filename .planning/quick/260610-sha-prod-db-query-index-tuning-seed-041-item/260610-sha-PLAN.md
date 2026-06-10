---
quick_id: 260610-sha
title: Prod DB query & index tuning (SEED-041 items 1-8)
status: in-progress
date: 2026-06-10
---

# Quick Task 260610-sha: Prod DB query & index tuning (SEED-041 items 1-8)

Implements `.planning/seeds/SEED-041-prod-db-query-and-index-tuning.md` items 1-8,
backed by `reports/db-stats/db-schema-analysis-2026-06-10.md`.

**Out of scope (deliberate):** item 9 (`move_count` → `ply_count`) — the seed flags it
as phase-sized (migration + backfill + import path + API/UI churn) and the user
requested no new phase. Independent of items 1-8; left as the dormant seed item.

## Tasks / commits

1. **Batch-1 migration (items 1a, 2, 3, 4) + `Game` model edits + item 8 comment.**
   New Alembic migration off head `f8a2d1c9b345`:
   - 1a: `ALTER TABLE game_positions ALTER COLUMN full_hash SET STATISTICS 2000`
     (idempotent; prod already applied 2026-06-10 — rides for dev/test parity).
   - 4: `ALTER TABLE game_positions SET (autovacuum_vacuum_insert_scale_factor=0.05,
     autovacuum_vacuum_insert_threshold=100000)` (idempotent; prod already applied).
   - 2: `CREATE INDEX CONCURRENTLY ix_games_user_played_at ON games (user_id, played_at DESC)`
     then `DROP INDEX CONCURRENTLY ix_games_user_id` (autocommit_block).
   - 3: `CREATE INDEX CONCURRENTLY ix_games_user_evals_pending ON games (user_id)
     WHERE evals_completed_at IS NULL` (autocommit_block).
   - Model: drop `index=True` on `Game.user_id`; add the two new `Index` entries to
     `Game.__table_args__`. Item 8: one-line comment on `base_time_seconds` SMALLINT safety.

2. **Openings explorer query rewrite (item 1b).** `query_top_openings_sql_wdl()` in
   `stats_repository.py`: materialize the user's qualifying games in a
   `MATERIALIZED` CTE and join positions against it, forcing the hash join the
   planner refuses to pick even with the raised statistics target. Correctness is
   dev-verifiable via the existing suite; the plan-flip payoff is prod-only.

3. **Composite FK migration (item 5) + `GamePosition` model (items 5, 7).**
   - `CREATE UNIQUE INDEX CONCURRENTLY uq_games_id_user_id ON games (id, user_id)`,
     then composite FK `(game_id, user_id) → games(id, user_id)` added `NOT VALID` +
     `VALIDATE CONSTRAINT`, then drop the two single-column FKs.
   - **Real constraint names (verified against live DB, seed was wrong):**
     `fk_game_positions_user_id` (NOT `game_positions_user_id_fkey`) and
     `game_positions_game_id_fkey`.
   - Model: replace per-column `ForeignKey` with a composite `ForeignKeyConstraint`;
     keep `index=True` on `game_id` (keeps `ix_game_positions_game_id` for cascade).
     Item 7: add explicit `PrimaryKeyConstraint("user_id","game_id","ply")` to fix the
     model PK column-order drift vs prod.

4. **Heap densification migration (item 6).** `ALTER TABLE games SET
   (toast_tuple_target = 256)`. The one-time `VACUUM FULL games` (applies it to
   existing rows; ~1-2 min ACCESS EXCLUSIVE on prod) is a **manual prod ops step** —
   VACUUM cannot run inside an Alembic transaction. Documented in the migration
   docstring and the summary.

## Verification
- `uv run ruff format/check`, `uv run ty check app/ tests/`, `uv run pytest -n auto`.
- `uv run alembic upgrade head` + `downgrade` round-trip on dev DB.
- No frontend changes (item 9 was the only UI-touching item; excluded).
