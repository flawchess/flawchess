---
quick_id: 260610-sha
title: Prod DB query & index tuning (SEED-041 items 1-8)
status: complete
date: 2026-06-10
---

# Quick Task 260610-sha — Summary

Implemented SEED-041 items 1-8 (the prod DB query & index tuning from the
2026-06-10 schema analysis). Item 9 (`move_count`→`ply_count`) was deliberately
left out as a phase-sized change, per the user's "no new phase" instruction.

## Commits (on `main`, not pushed)

| Commit | Items | What |
|--------|-------|------|
| `9eab6170` | 1a, 2, 3, 4, 8 | Migration `b7c1d9e2f3a4` + `Game` model |
| `44002345` | 1b | Openings explorer MATERIALIZED-CTE query rewrite |
| `8823c3db` | 5, 7 | Migration `c8d2e0f3a4b5` (composite FK) + `GamePosition` model |
| `de16dc4f` | 6 | Migration `d9e3f1a4b5c6` (`games` toast_tuple_target) |

## What shipped per item

- **1a** — `game_positions.full_hash SET STATISTICS 2000` added to migration
  `b7c1d9e2f3a4` for dev/test parity (already live on prod since 2026-06-10;
  idempotent).
- **1b** — `query_top_openings_sql_wdl()` rewritten: the user's qualifying games
  are materialized in a `WITH user_games AS MATERIALIZED (...)` CTE (all standard
  game filters moved inside it) and positions join against that. The optimizer
  fence forces a hash join over the user's games instead of the planner's
  ~187k-probe nested loop. Correctness preserved (34 stats/insights tests pass);
  the plan-flip itself is prod-only and not observable on the tiny dev DB.
- **2** — CONCURRENTLY swap `ix_games_user_id` → `ix_games_user_played_at
  (user_id, played_at DESC)`. Model: dropped `index=True` on `Game.user_id`,
  declared the new index in `__table_args__`.
- **3** — partial `ix_games_user_evals_pending (user_id) WHERE
  evals_completed_at IS NULL` for the per-import-batch pending-evals gate.
  `ix_games_evals_pending` (on id) kept.
- **4** — `game_positions` autovacuum insert tuning added to the migration for
  dev/test parity (already live on prod; idempotent).
- **5** — composite FK `(game_id, user_id) → games(id, user_id)` (unique index
  `uq_games_id_user_id` built CONCURRENTLY first; FK added `NOT VALID` then
  `VALIDATE CONSTRAINT`), replacing the two single-column FKs. **Constraint-name
  correction:** the user_id FK is really `fk_game_positions_user_id` (the seed's
  assumed `game_positions_user_id_fkey` was wrong — verified vs live DB).
  `ix_game_positions_game_id` kept (backs the cascade). Model: composite
  `ForeignKeyConstraint`.
- **6** — `games SET (toast_tuple_target = 256)` (reloption only).
- **7** — explicit `PrimaryKeyConstraint("user_id","game_id","ply")` on
  `GamePosition` fixes the model PK column-order drift vs prod.
- **8** — one-line `base_time_seconds` SMALLINT-safety comment on `Game`.

## ⚠️ Manual prod ops step still required (not in any migration)

**`VACUUM FULL games;`** (item 6) — the `toast_tuple_target` reloption only
affects rows written *after* it is set; existing rows need a table rewrite to move
their PGNs out-of-line. VACUUM cannot run inside an Alembic transaction. Run it
manually on prod against the live DB after deploy (~1-2 min ACCESS EXCLUSIVE on the
1.4 GB table; or `pg_repack -t games` for a no-lock rewrite). Acceptable downtime
per the user decision 2026-06-10.

## Verification

- All 3 migrations round-trip up→down→up on the dev DB; live schema confirmed via
  MCP (DESC index, partial index, single composite FK, PK order, reloptions).
- Backend gate GREEN: `ruff format`/`check` + `ty check` clean, `pytest -n auto`
  **2491 passed / 10 skipped** (test template rebuilt from the new migrations).
- Frontend gate GREEN: lint clean, vitest **880/880** (no frontend files changed).
- **Prod follow-up:** compare `pg_stat_statements` deltas and re-run `/db-report`
  (prod) ~1 week after each batch deploys — openings explorer avg_ms, the
  `users_with_zero_pending` gate avg_ms, `relallvisible/relpages` on
  `game_positions`, and `games` heap size.

## Out of scope

- **Item 9** (`games.move_count` → `games.ply_count`) — phase-sized (migration +
  backfill + import-path + API/UI churn); independent of items 1-8; left as the
  dormant part of SEED-041.
- Everything under the seed's "Explicitly NOT in scope" section (no per-(user,
  full_hash) rollup table; keep `ix_game_positions_game_id`; keep white/black hash
  partial indexes; no column-order padding rewrite).
