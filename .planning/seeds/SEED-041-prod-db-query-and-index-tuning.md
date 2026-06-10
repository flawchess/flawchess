---
id: SEED-041
status: partial  # items 1-8 implemented 2026-06-10 (quick task 260610-sha); item 9 remains dormant
planted: 2026-06-10
planted_during: v1.25 (Flaw-Stats Opponent Comparison), Phase 114 (benchmark flaw-delta zones) in progress
trigger_when: after Phase 114 merges — run as /gsd-quick tasks (items 1-4 in one task; items 5-6 each need their own migration-bearing task); item 9 (move_count→ply_count) is a larger migration + API/UI change, plan as its own phase
scope: small-medium (items 1-8 are quick/migration tasks; item 9 is a phase-sized migration + UI change)
---

# SEED-041: Prod DB query & index tuning (from 2026-06-10 schema analysis)

> **STATUS 2026-06-10 — items 1-8 IMPLEMENTED** (quick task `260610-sha`, on `main`,
> not yet deployed). Three Alembic migrations off head `f8a2d1c9b345`:
> `b7c1d9e2f3a4` (batch 1: items 1a, 2, 3, 4), `c8d2e0f3a4b5` (item 5 composite FK),
> `d9e3f1a4b5c6` (item 6 toast reloption); query rewrite for item 1b; model
> cleanups for items 7, 8. **Correction logged:** item 5's user_id FK is really
> named `fk_game_positions_user_id` (the checklist's `game_positions_user_id_fkey`
> was wrong — verified vs live DB).
> **Still pending (manual prod ops, NOT in any migration):** item 6's
> `VACUUM FULL games` (applies the toast knob to existing rows; VACUUM can't run in
> an Alembic transaction). **Item 9 is now Phase 114.1** (inserted 2026-06-10,
> `move_count → ply_count`; design path `/gsd-discuss-phase 114.1` → `/gsd-plan-phase 114.1`)
> — no longer dormant. Verify items 1-8 via `pg_stat_statements` deltas +
> `/db-report` ~1 week after deploy.

Implement the findings of `reports/db-stats/db-schema-analysis-2026-06-10.md`
(companion to `db-report-prod-2026-06-10.md`). All findings are backed by prod
`pg_stat_statements` and live `EXPLAIN (ANALYZE, BUFFERS)` runs against the
largest user (167: 55,699 games / 4.87M positions). Read that report first —
it has the full evidence, SQL, and rationale per item. This seed is the
implementation checklist.

## Batch 1 — low-risk (/gsd-quick)

1. ~~**Fix `full_hash` planner statistics**~~ **DONE in prod 2026-06-10** —
   `SET STATISTICS 2000` + ANALYZE applied (n_distinct 336k → 3.8M, 1,766 MCVs).
   **Outcome: the plan did NOT flip** — the join goes through the
   `openings_dedup` view's `DISTINCT ON` subquery, which blocks MCV propagation,
   so the nested loop remains (809 ms, unchanged). Keep the stats setting (it
   helps direct `full_hash IN (...)` estimates). **The phase must do the
   fallback**: MATERIALIZED-CTE rewrite of `query_top_openings_sql_wdl()` in
   `stats_repository.py` (§A1, fix #2) to force a hash join over the user's
   games. Pending: add the stats target to an Alembic migration so dev/test
   DBs get it too (`ALTER COLUMN full_hash SET STATISTICS 2000`).
2. **Replace `ix_games_user_id` with `(user_id, played_at DESC)`** (§A2):
   lets the `recent_capped` window run-condition early-terminate instead of
   scanning the user's full game history (29k buffers for user 167). Serves
   rating history, matching-games pagination, and all `user_id` prefix lookups.
3. **Add partial index `(user_id) WHERE evals_completed_at IS NULL`** (§A3):
   the per-import-batch pending-evals gate is the #2 server-time consumer
   (26.5 ms × 7,053 calls). Keep the existing `ix_games_evals_pending (id)`.
4. ~~**`game_positions` autovacuum insert tuning**~~ **DONE in prod 2026-06-10**
   — reloptions set (`autovacuum_vacuum_insert_scale_factor = 0.05,
   autovacuum_vacuum_insert_threshold = 100000`) and catch-up
   `VACUUM (ANALYZE)` run (~10 s; visibility map 76% → 100%, 158k dead item
   pointers removed). Pending: mirror the reloptions in an Alembic migration
   for dev/test parity.

Items 2-3 are Alembic migrations using CONCURRENTLY (autocommit_block pattern,
prior art: `20260603_153628_f4d88c3659c6_gp_natural_composite_pk_seed_035.py`).
The already-applied prod settings of items 1 and 4 should ride in the same
migration as plain DDL (idempotent; prod already has them).

## Batch 2 — separate quick tasks (a few minutes of downtime is acceptable; no special deploy window needed)

5. **Composite FK** `(game_id, user_id) → games(id, user_id)` replacing both
   FKs on `game_positions` (§B1): halves per-row FK trigger work on COPY
   (the 12.7M `FOR KEY SHARE` locks on `users`) AND enforces the invariant
   that a position's denormalized `user_id` matches the owning game — which
   the current `user_id → users` FK does not check. Needs a unique index on
   `games (id, user_id)` (~20 MB) built CONCURRENTLY first, and the new FK
   should be added `NOT VALID` + `VALIDATE CONSTRAINT` to avoid a long lock.
6. **`games` heap densification** (§C1): avg PGN is 2.6 KB and stays inline,
   so the hot heap is 1,275 MB at ~3.6 rows/page. `ALTER TABLE games SET
   (toast_tuple_target = 256)` + one-time `VACUUM FULL games` to apply it to
   existing rows (ACCESS EXCLUSIVE lock for ~1-2 min on the 1.4 GB table —
   acceptable downtime per user decision 2026-06-10) → hot heap ~10× denser,
   cache-resident. The reloption alone only affects newly written rows.

## Batch 3 — schema change with UI impact (own migration-bearing task)

9. **Replace `games.move_count` with `games.ply_count`** (raised 2026-06-10 during
   Phase 114). `move_count` is the FULL-move count (`zobrist.py` ~L271:
   `(len(nodes)+1)//2`); on the DB it equals `ceil(plies/2)`, so it pins half-moves
   only to ±1 — verified on the benchmark DB: `max_ply ∈ {2·move_count,
   2·move_count−1}` (the −1 when the game ended on White's move). That ±1 ambiguity
   blocks deriving an exact per-game **user move count** without scanning
   `game_positions` (190M rows / 44 GB on benchmark). Store the exact half-move count
   instead.
   - **Migration** (Alembic, `add → backfill → enforce`): add `ply_count INT` nullable;
     backfill `ply_count = max(ply)` from `game_positions` per game in batches (dev +
     prod; prod via `bin/prod_db_tunnel.sh`); then drop `move_count` once all readers
     are migrated. Plies are 0-based and contiguous, so `max(ply) = count(ply>=1)` = the
     exact half-move total.
   - **Import path**: `zobrist.py` ~L271 set `ply_count = len(nodes)` (half-moves), not
     `(len(nodes)+1)//2`; `import_service.py` bulk UPDATE (~L738-770) writes `ply_count`.
   - **Display is user-facing — keep showing FULL moves.** `move_count` renders as
     "N Moves" in `LibraryGameCard.tsx`, `GameCard.tsx`, `FlawCard.tsx`. Expose
     `ply_count` in the API schemas (`app/schemas/openings.py`, `app/schemas/library.py`)
     and derive the displayed count as `(ply_count + 1) // 2` (frontend, or a computed
     API field) so the label is unchanged. Update readers: `library_service`,
     `library_repository`, `openings_service`, `endgame_service`, frontend
     `types/api.ts` + `types/library.ts` + the 3 cards, and the `test_zobrist` /
     `test_import_service` fixtures.
   - **Payoff**: exact per-game `user_moves = floor(ply_count/2)` (white) /
     `ceil(ply_count/2)` (black) with ZERO `game_positions` access. Speeds the §5
     benchmark chapter (drops its ~87M-row user-move scan) and — the stronger reason —
     the Phase 115 live "you vs opponent" endpoint, which computes the same per-game
     denominator on every request.
   - **Follow-on**: once shipped, simplify `scripts/benchmarks/chapter5.py`
     `user_moves_per_game` to read `games.ply_count` instead of counting
     `game_positions`, and regenerate §5.

   Bigger than a /gsd-quick (Alembic migration + backfill + import-path change + API/UI
   churn). Plan as its own phase or a dedicated migration-bearing task. Independent of
   items 1-8.

## Code-only cleanups (fold into either batch)

7. Add explicit `PrimaryKeyConstraint("user_id", "game_id", "ply")` to
   `GamePosition.__table_args__` — model metadata currently declares the PK
   in the wrong column order vs prod/migration (§B2).
8. One-line comment on `games.base_time_seconds`: SMALLINT is safe (prod max
   10,800; daily games store NULL) but would overflow if daily base times
   were ever stored (§B3).

## Explicitly NOT in scope (decided in the analysis)

- No per-(user, full_hash) WDL rollup table — the explorer's filter dimensions
  make rollups wrong or combinatorial (§A1).
- Keep `ix_game_positions_game_id` (backs FK cascade + eval-drain updates).
- Keep white/black hash partial indexes (524 MB, low usage) — re-check usage
  at the next db-report before considering a drop (§C4).
- Column-order padding rewrite (~250 MB) — only if some future migration
  rewrites the table anyway (§C3).

## Verification

`pg_stat_statements` deltas + re-run `/db-report` (prod) a week after each
batch: openings explorer avg_ms, the `users_with_zero_pending` gate avg_ms,
`relallvisible/relpages` on game_positions, and games heap size.
