# FlawChess DB Schema & Query Analysis — 2026-06-10

Companion to `db-report-prod-2026-06-10.md`. Sources: prod `pg_stat_statements` (5 days of stats), live `EXPLAIN (ANALYZE, BUFFERS)` runs against the largest user (167: 55,699 games / 4.87M positions), prod catalog introspection, and a full read of `app/models/` + `app/repositories/`.

---

## A. User-facing query bottlenecks

### A1. Openings explorer aggregation — 748 ms avg, 4.8 s max (the #1 user-facing cost)

**Measured plan** (user 167, color=white): 888 ms, 953k buffers. The cost center is **not** the `count(distinct games.id)` itself:

- `ix_gp_user_full_hash_move_san` is probed once per opening (3,281 probes → 187,709 position rows, ~200k buffers). Healthy.
- Those 187,709 rows then drive **187,709 individual `games_pkey` lookups** (751k buffers — 80% of the whole query), of which only 48% survive the `user_color`/`is_computer_game` filter.

The planner picks this nested loop because it estimates **244 join rows vs 89,759 actual (367× under)**. Root cause is bad statistics on `game_positions.full_hash`:

- `pg_stats.n_distinct = 335,826` — the true distinct count is in the tens of millions (post-opening positions are nearly unique). The default statistics sample cannot see the long tail, and there is no MCV list capturing the ultra-common opening hashes (the starting position alone appears ~590k times).

**Recommended, in order:**

1. **Raise the statistics target** (cheap, reversible, no migration):
   ```sql
   ALTER TABLE game_positions ALTER COLUMN full_hash SET STATISTICS 2000;
   ANALYZE game_positions;
   ```
   A large MCV list captures the popular opening hashes, the join estimate rises, and the planner should flip to a hash join over the user's games (one scan of ~30–55k rows instead of 187k random probes). Verify with `EXPLAIN (ANALYZE, BUFFERS)` after; revert with `SET STATISTICS -1` if it doesn't move the plan.
2. **If the plan doesn't flip:** restructure the query in `stats_repository.query_top_openings_sql_wdl()` — materialize the user's qualifying games first (`WITH user_games AS MATERIALIZED (SELECT id, result, user_color, played_at FROM games WHERE user_id = :u AND user_color = :c AND NOT is_computer_game)`) and join positions against that, forcing the hash join the planner refuses to pick.
3. **C1 below** (games heap densification) independently makes each probe ~7× more cache-friendly even if the nested loop stays.

A precomputed per-(user, full_hash) WDL rollup table was considered and **not recommended**: the explorer's filter dimensions (time control, date range, rated, platform, opponent gap) make a rollup either wrong or combinatorially dimensioned. The query-side fixes above get the same UX win without a second write path.

### A2. Recent-games CTE family (`recent_capped`) — 737/397/383/186 ms avg variants

Every percentile/insights query starts with `row_number() OVER (PARTITION BY user_id ORDER BY played_at DESC)` over the user's filtered games. Measured: a bitmap scan reads **all 55,699 of user 167's games (29,458 buffers, ~140 ms)** to keep the most recent ~1,000 qualifying ones. The same pattern is re-executed once per metric × TC, so it multiplies across the percentile batch.

**Recommendation: replace `ix_games_user_id` with `(user_id, played_at DESC)`.**

```sql
CREATE INDEX CONCURRENTLY ix_games_user_played_at ON games (user_id, played_at DESC);
DROP INDEX CONCURRENTLY ix_games_user_id;
```

- With presorted input, the `WindowAgg` run-condition (`rn <= N`) terminates the scan after N qualifying rows instead of reading the user's full history — the win grows with account size.
- The same index serves `query_rating_history()`'s `DISTINCT ON (date, tc) ... ORDER BY played_at`, the matching-games `ORDER BY played_at DESC LIMIT/OFFSET`, and `MAX(played_at)` aggregates.
- Dropping `ix_games_user_id` is safe: the new index serves every `user_id`-only lookup via its prefix (and `uq_games_user_platform_game_id` also leads with `user_id`). The old index had only 9,016 scans in 5 days.

### A3. Pending-evals gate — 26.5 ms × 7,053 calls = 187 s (2nd-highest total server time after COPY)

`users_with_zero_pending()` runs per import batch and does `LEFT JOIN games ON games.user_id = uid AND games.evals_completed_at IS NULL`. There is no index combining the two: the existing partial `ix_games_evals_pending` is on `(id)` (it serves the `ORDER BY id DESC LIMIT` drain poll), so the gate falls back to scanning all of the user's games. 26.5 ms × every batch of a 55k-game import adds up.

**Recommendation: add a second partial index keyed by user:**

```sql
CREATE INDEX CONCURRENTLY ix_games_user_evals_pending
  ON games (user_id) WHERE evals_completed_at IS NULL;
```

Near-zero size at steady state (only pending games are indexed), makes the gate and `count_pending_evals()` (1.2 ms × 1,186) sub-millisecond. Keep `ix_games_evals_pending` for the id-ordered drain poll.

---

## B. Schema integrity & write path

### B1. FK check churn during import: `users FOR KEY SHARE` 12.7M executions (137 s)

Every `game_positions` row written by COPY fires **two** per-row FK triggers: `user_id → users.id` (the 12.7M `FOR KEY SHARE` seq scans on the 129-row `users` table) and `game_id → games.id` (a large share of the 18M `games_pkey` scans). At ~74 positions/game this is the import path's hidden tax, and import CPU pressure has real history here (the OOM incidents).

**Recommendation: replace both FKs on `game_positions` with one composite FK:**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_games_id_user_id ON games (id, user_id);
ALTER TABLE game_positions
  ADD CONSTRAINT game_positions_game_user_fkey
  FOREIGN KEY (game_id, user_id) REFERENCES games (id, user_id) ON DELETE CASCADE;
ALTER TABLE game_positions DROP CONSTRAINT game_positions_game_id_fkey;
ALTER TABLE game_positions DROP CONSTRAINT game_positions_user_id_fkey;
```

- Halves FK trigger work per position (one check instead of two).
- **Strengthens integrity**: it enforces that a position's denormalized `user_id` actually matches the owning game's `user_id` — an invariant the current `user_id → users` FK does not check at all (any valid user id passes). Today a code bug could silently write positions attributed to the wrong user.
- Referential chain to `users` stays intact transitively via `games.user_id → users.id` (CASCADE), so the "FKs are mandatory" rule is fully honored.
- Cost: one extra ~20 MB unique index on `games`. `ix_game_positions_game_id` must stay (it backs the CASCADE on the positions side).

### B2. Model vs prod PK column-order drift on `game_positions`

The SEED-035 migration (and prod) define the PK as **`(user_id, game_id, ply)`**; the model in `app/models/game_position.py` declares `game_id` first, so SQLAlchemy metadata believes the PK is `(game_id, user_id, ply)`. Tests run against migration-built DBs so nothing is broken today, but any metadata-derived DDL (`create_all`, future autogenerate diffs) and human readers get the wrong order. Fix by adding an explicit `PrimaryKeyConstraint("user_id", "game_id", "ply")` to `__table_args__` (column declaration order can stay as-is).

### B3. `base_time_seconds` SMALLINT — verified safe, document it

Prod max is 10,800 s; daily/correspondence games (4,112 of them) store NULL. The 32,767 ceiling is fine for live chess but would overflow if daily base times were ever stored. Worth a one-line comment on the column so a future "support daily time controls" change doesn't trip it.

---

## C. Storage & maintenance

### C1. `games` heap is mostly PGN ballast — densify it (big cache win, zero code change)

- Avg `pgn` length: 2,622 bytes; 75% of games exceed 1,900 bytes. With the default 2 KB TOAST threshold most PGNs stay **inline** (compressed): main heap is 1,275 MB (~3.6 rows/page) while the TOAST table holds only 99 MB.
- Consequence: every per-game lookup (the openings explorer's 187k probes, endgame joins, WDL dedups — none of which read `pgn`) drags ~2.2 KB rows through the buffer cache. This is why the explorer plan touched 751k buffers on the games side, and it dilutes the 98.7% cache hit ratio.

**Recommendation:**

```sql
ALTER TABLE games SET (toast_tuple_target = 256);
-- then one-time rewrite to apply to existing rows (pick a quiet window):
VACUUM FULL games;  -- ~1.4 GB table; or pg_repack for no-lock
```

PGN moves out-of-line for effectively all rows; the hot heap shrinks to roughly 150–250 MB (~25 rows/page) and becomes permanently cache-resident on the 16 GB host. Queries that do read `pgn` (game detail, reclassify scripts) pay one extra TOAST fetch — they are rare paths. Alternative considered: a separate 1:1 `game_pgns` table — same physical effect but requires model/repository changes; the TOAST knob is strictly cheaper.

### C2. `game_positions` has never been vacuumed — visibility map at 76%, freeze debt growing

- `relallvisible/relpages = 76.1%`. Index-only scans on the endgame covering index (`ix_gp_user_endgame_game`, 37.8M scans — the busiest index in the DB) degrade to heap fetches on the ~24% of pages not all-visible, exactly the INCLUDE(eval_cp, eval_mate) optimization REFAC-02 paid for.
- The table is append-mostly via COPY; insert-driven autovacuum (default scale factor 0.2) needs ~8.8M new rows to trigger, so big imports accrue unfrozen pages until a future anti-wraparound vacuum hits the 8.6 GB table all at once.

**Recommendation:**

```sql
ALTER TABLE game_positions SET (
  autovacuum_vacuum_insert_scale_factor = 0.05,
  autovacuum_vacuum_insert_threshold = 100000
);
```

Vacuum then runs incrementally after large imports, keeps the visibility map near 100% (restoring true index-only scans), and amortizes freezing. Optionally run one manual `VACUUM (ANALYZE) game_positions` off-peak now to catch up.

### C3. Row-alignment padding in `game_positions` (~250 MB) — low priority

Physical column order is `game_id(4), user_id(4), ply(2), full_hash(8)…` — 6 padding bytes per row before the first BIGINT, ≈ 250 MB across 43.9M rows (~2.5% of the DB). Only recoverable via a full table rewrite with reordered columns (hashes first, 2-byte columns grouped). Not worth a dedicated rewrite of an 8.6 GB table; fold into the column-order DDL **only if** some future migration rewrites the table anyway.

### C4. White/black hash partial indexes — expensive insurance, keep for now

`ix_gp_user_white_hash` + `ix_gp_user_black_hash` cost 524 MB plus write amplification on every import, for 82 + 576 scans in 5 days (the system-opening "my pieces only" filter). The feature is real and the indexes are correctly partial (`ply <= 28`), so keep — but if usage stays this low as the table doubles, dropping one side (or both, accepting a slow first-use) is the single biggest reclaimable chunk of index space. Re-check usage at the next report.

### C5. Guest-data deletion path

User 167 (a guest) alone holds 11% of all positions. When a guest reaper lands, note the delete path is sound: `games` CASCade → `game_positions` via `ix_game_positions_game_id`, but a 4.9M-position cascade in one transaction will bloat WAL and hold locks — delete per-game-batch (e.g. 500 games per transaction). No schema change needed.

---

## D. Verified healthy (no action)

- **Partial hash indexes** (`ply <= 28`, SEED-033) confirmed working: EXPLAIN shows hash lookups using the partial index with the predicate satisfied implicitly.
- **Endgame covering index** is the most-scanned index in the DB (37.8M scans / 5 days) and earns its 614 MB (C2 makes it better still).
- **`ix_game_positions_game_id`** is NOT redundant with the PK (prod PK leads with `user_id`); it backs the FK cascade and the eval-drain `UPDATE … WHERE game_id = ? AND ply = ?` (158k calls, 0.34 ms avg). Keep.
- **COPY import path**: 59.9 ms avg per 1,700-row binary chunk, 100% cache hit. Healthy.
- **`users` seq scans** (6.5M) are the 129-row FK-check pattern — benign in itself; B1 removes most of them as a side effect.
- **`openings_dedup`** is a plain view recomputed per query (~13 ms over 3,641 rows) — negligible; not worth materializing.
- **`games` enum/typing choices**, `llm_logs` index set, `benchmark_cohort_cdf` PK + `(anchor_elo, tc)` index, and the new (unreleased) `game_flaws` table (user-led PK, cascade index on `game_id`, `(user_id, severity)` secondary) all check out against their query patterns.
- **No SMALLINT overflow risk** found anywhere (`base_time_seconds` max 10,800; daily games NULL).

---

## Suggested implementation order

| # | Change | Type | Expected effect |
|---|--------|------|-----------------|
| 1 | `full_hash` STATISTICS 2000 + ANALYZE (A1) | 2 statements, reversible | Openings explorer 748 ms → likely 200–400 ms |
| 2 | `(user_id, played_at DESC)` index, drop `ix_games_user_id` (A2) | migration, CONCURRENTLY | Recent-games CTE family scales with recency cap, not account size |
| 3 | Partial `(user_id) WHERE evals_completed_at IS NULL` (A3) | migration, CONCURRENTLY | Import-batch gate 26.5 ms → sub-ms; −187 s/5 days server time |
| 4 | `game_positions` autovacuum insert tuning + catch-up VACUUM (C2) | reloptions | Restores index-only scans on the busiest index; prevents wraparound cliff |
| 5 | Composite FK `(game_id, user_id) → games(id, user_id)` (B1) | migration | Halves per-row FK work on import; strengthens integrity |
| 6 | `games` toast_tuple_target + rewrite (C1) | reloptions + maintenance window | games hot heap ~10× denser; cache-resident |
| 7 | Model PK-order fix + `base_time_seconds` comment (B2, B3) | code-only | Removes metadata drift |

Items 1–4 are low-risk and independently verifiable in prod via `pg_stat_statements` deltas. Items 5–6 want a GSD phase (migration + deploy-window planning). Re-run the db-report a week after each batch to confirm.
