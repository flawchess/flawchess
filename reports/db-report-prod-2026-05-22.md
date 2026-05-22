# FlawChess DB Report — 2026-05-22

- **DB**: prod
- **Snapshot taken**: 2026-05-22T08:05:55Z
- **Sections run**: users / storage / performance

---

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 95 | 50 | 45 |

### 10 most recent users

| ID | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---:|---:|
| 103 | no  | no  | yes | 2026-05-22 | 2026-05-22 |       0 |         0 |
| 102 | yes | no  | no  | 2026-05-21 | 2026-05-21 |   3,440 |   244,369 |
| 101 | yes | no  | yes | 2026-05-21 | 2026-05-21 |  12,216 |   871,004 |
| 100 | yes | no  | yes | 2026-05-21 | 2026-05-21 |     572 |    40,672 |
|  99 | yes | yes | no  | 2026-05-20 | 2026-05-20 |  10,700 |   651,854 |
|  98 | no  | yes | yes | 2026-05-17 | 2026-05-17 |     902 |    57,436 |
|  97 | yes | yes | no  | 2026-05-17 | 2026-05-17 |   2,853 |   163,298 |
|  96 | no  | yes | no  | 2026-05-16 | 2026-05-17 |   7,696 |   566,794 |
|  95 | yes | yes | no  | 2026-05-16 | 2026-05-21 |  39,923 | 3,409,290 |
|  93 | no  | yes | yes | 2026-05-13 | 2026-05-13 |   2,455 |   138,988 |

### Platform breakdown (all users)

| Platform | Users | Games |
|---|---:|---:|
| chess.com | 53 | 273,817 |
| lichess   | 45 | 181,714 |

**Notes:**
- Strong recent uptake: 9 of the 10 newest users have actually linked a platform and imported games (only user 103, registered today, has not). Good signup-to-activation ratio.
- User 95 is by far the heaviest account (~40K games, 3.4M positions, ~7.5% of all games and ~10% of all positions in the DB).
- Roughly half the user base (45/95) are guests, but several guests have imported very large libraries (e.g. user 101 with 12K games) — guest accounts are clearly being used as full trials, not throwaways.
- chess.com leads on absolute games (273K vs 181K), driven by chess.com users typically having larger archives per account.

---

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | **13 GB** |
| Total games | 455,531 |
| Total positions | 33,521,625 |
| Avg positions / game | ~73.6 |

### Per-table breakdown

| Table | Table size | Index size | Total |
|---|---:|---:|---:|
| game_positions | 4,127 MB | 7,297 MB | **11 GB** |
| games | 1,294 MB | 162 MB | 1,456 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 16 kB | 592 kB | 608 kB |
| import_jobs | 40 kB | 344 kB | 384 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| users | 24 kB | 64 kB | 88 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top 15)

| Index | Table | Size |
|---|---|---:|
| ix_gp_user_full_hash_move_san | game_positions | 2,122 MB |
| ix_gp_user_white_hash         | game_positions | 1,252 MB |
| ix_gp_user_black_hash         | game_positions | 1,246 MB |
| game_positions_pkey           | game_positions | 1,234 MB |
| ix_gp_user_endgame_game       | game_positions |   562 MB |
| ix_gp_user_game_ply           | game_positions |   448 MB |
| ix_game_positions_game_id     | game_positions |   431 MB |
| uq_games_user_platform_game_id| games          |    52 MB |
| games_pkey                    | games          |    20 MB |
| ix_games_user_id              | games          |  9,848 kB |
| ix_games_evals_pending        | games          |  9,640 kB |
| uq_openings_eco_name_pgn      | openings       |   488 kB |
| ix_openings_eco_name          | openings       |   264 kB |
| openings_pkey                 | openings       |    96 kB |
| import_jobs_pkey              | import_jobs    |    40 kB |

**Storage notes:**
- `game_positions` is the entire DB at scale: 11 GB out of 13 GB total (~85%).
- Index-to-data ratio on `game_positions` is **1.77:1** (7.3 GB index vs 4.1 GB data). That's heavy but expected given the 4 distinct hash lookup paths (`full_hash`, `white_hash`, `black_hash`, `game_id`) plus the endgame composite. Each (user_id, hash) index is roughly 1.2-2.1 GB.
- `ix_gp_user_full_hash_move_san` alone is 2.1 GB — biggest single index, used by the opening-explorer "candidate moves from position" query.
- Postgres is correctly storing `material_signature` etc as efficient narrow columns; growth is hash-index driven, not row-bloat driven.

---

## 2. Performance Analysis

### Buffer cache hit ratio

**92.55%** — below the 95% "good" threshold. Not catastrophic, but the working set (13 GB total, 11 GB of which is game_positions) exceeds Postgres `shared_buffers`. Many queries are reading from the OS page cache or disk. With 7.6 GB RAM on the box and Postgres sharing it with the backend/Stockfish/Caddy, this is roughly what you'd expect — a memory upgrade or a tighter working set would move this north of 99%.

### Slowest queries by avg time (filtered: avg ≥ 50ms)

| avg_ms | max_ms | calls | total_ms | query (truncated) |
|---:|---:|---:|---:|---|
| 4824.87 | 4824.87 | 1 | 4,825 | The /db-report Section 0 user summary join (one-off, this run) |
| 4542.75 | 4542.75 | 1 | 4,543 | `SELECT count(*) FROM game_positions` (full-table count of 33.5M rows — one-off, this run) |
| 1309.07 | 5103.10 | 4 | 5,236 | Opening explorer candidate-move WDL aggregation (gp1 → gp2 join + counts) |
| 1261.78 | 1261.78 | 1 | 1,262 | `SELECT platform, count(*) FROM games GROUP BY platform` (one-off, this run) |
| 297.94 | 525.85 | 12 | 3,575 | Opening WDL `DISTINCT ON (full_hash, games.id)` dedup CTE |
| 154.95 | 849.64 | 8 | 1,240 | Openings list with per-opening game count (ECO/name lookup with deduped opening + game join) |
| 131.32 | 621.11 | 6 | 788 | Same dedup CTE pattern as 297ms entry, narrower filter |
| 83.26 | 99.50 | 5 | 416 | Games list (paginated `SELECT games.* … LIMIT 100`) |
| 79.21 | 89.08 | 6 | 475 | Endgame clock-array aggregation (`array_agg(ply)`, `array_agg(clock)` per game) |
| 77.33 | 119.00 | 4 | 309 | Same dedup CTE but on `white_hash` (system-opening filter) |
| 71.05 | 175.90 | 5 | 355 | Games list count (`SELECT count(*)`) for pagination |
| 58.50 | 91.66 | 5 | 292 | Endgame span-entry aggregation for `endgame_class` |

### Highest total time (cumulative server load)

| total_ms | calls | avg_ms | query |
|---:|---:|---:|---|
| 6,655 | 14,196 | 0.47 | Eval-backfill pending-games scan (`WHERE evals_completed_at IS NULL`) |
| 5,236 | 4 | 1309.07 | Opening-explorer candidate-move WDL |
| 4,825 | 1 | 4824.87 | (Section 0 user join, ignore) |
| 4,543 | 1 | 4542.75 | (Section 1 row count, ignore) |
| 4,429 | 14,686 | 0.30 | `UPDATE game_positions SET eval_cp=..., eval_mate=...` (per-position) |
| 4,149 | 499,254 | 0.01 | FastAPI-Users `SELECT FOR KEY SHARE` on `users` — half a million row locks |
| 3,575 | 12 | 297.94 | Opening WDL dedup CTE |
| 2,379 | 11,450 | 0.21 | Eval UPDATE variant (no endgame_class filter) |
| 1,396 | 1,146 | 1.22 | Bulk position fetch for eval pipeline |
| 1,262 | 1 | 1261.78 | (Section 0 platform breakdown, ignore) |
| 1,240 | 8 | 154.95 | Openings list with WDL |
|   881 | 11,650 | 0.08 | `UPDATE games SET evals_completed_at` |

### Sequential scan analysis

| Table | seq_scans | idx_scans | seq_tup_read | Verdict |
|---|---:|---:|---:|---|
| game_positions | 9 | 1,327,567 | 100,564,875 | OK — only 9 seq scans, but they read 100M tuples (likely full-table scans during the `SELECT count(*)` run above; stats are not yet autovacuumed so n_live_tup shows a stale 244K). |
| users | 255,220 | 0 | 20,167,410 | **Acceptable** — 95-row table, Postgres correctly prefers seq scan. Note this is mostly FastAPI-Users session lookups; the table is so small the planner ignores `users_pkey` and `ix_users_email`. |
| import_jobs | 895 | 1 | 158,315 | OK — 177 live rows, seq scan is cheaper than B-tree lookup at this size. |
| openings | 8 | 0 | 29,128 | OK — small lookup table. |
| oauth_account | 315 | 0 | 10,395 | OK — empty/tiny table. |
| llm_logs | 6 | 0 | 294 | OK — basically unused so far. |
| games | 0 | 507,713 | 0 | Excellent — every read uses an index. |
| position_bookmarks | 0 | 4 | 0 | OK — tiny. |

### Index usage — unused indexes (idx_scan = 0)

| Index | Table | Size | Recommendation |
|---|---|---:|---|
| game_positions_pkey | game_positions | 1,234 MB | **Keep** — PK, required for FK from other tables and UPDATE/DELETE by row. The 0 idx_scan count is because nothing queries by `(id,)`; PK is still load-bearing for writes. |
| users_pkey | users | 16 kB | Keep — PK, required for FK integrity. |
| openings_pkey, uq_openings_eco_name_pgn, ix_openings_eco_name | openings | <1 MB | Keep — required for upsert logic in opening seeding. |
| oauth_account_pkey, ix_oauth_account_account_id, ix_oauth_account_oauth_name | oauth_account | <100 kB | Keep — required for OAuth login lookup; will see usage once users sign in via OAuth. |
| ix_users_email | users | 16 kB | Keep — login lookup; planner currently prefers seq scan because table is 95 rows. Will flip to index scan once it grows. |
| llm_logs_pkey + 5 ix_llm_logs_* | llm_logs | <1 MB total | Keep — table is freshly populated/empty; indexes are tiny and serve the eval/insights pages once usage picks up. |
| import_jobs_pkey, ix_import_jobs_user_id | import_jobs | <50 kB | Keep — PK and FK paths. |
| bookmarks_pkey | position_bookmarks | 16 kB | Keep — PK. |
| alembic_version_pkc | alembic_version | 16 kB | Keep — required by Alembic. |

**No index is a meaningful drop candidate.** All unused-by-count indexes are either PKs, tiny, or serve infrequent flows.

Note also `ix_gp_user_white_hash` (1.25 GB) and `ix_gp_user_black_hash` (1.25 GB) have only 10-12 scans each since stats began. They exist to serve the **system-opening filter** ("my pieces only"). They earn their keep functionally — a `WHERE user_id = X AND white_hash = ?` without the index would scan billions of rows — but they are by far the least-used large indexes. If you ever decide to drop the system-opening feature, those ~2.5 GB go with it.

### Dead tuples / autovacuum

| Table | n_live_tup (stale) | n_dead_tup | last_autovacuum | last_autoanalyze |
|---|---:|---:|---|---|
| game_positions | 244,369 | 26,136 | **null** | **null** |
| games | 3,440 | 16,907 | **null** | **null** |
| users | 2 | 11 | **null** | **null** |
| import_jobs | 177 | 59 | **null** | 2026-05-21 20:32 |
| (others) | — | — | null | null |

**Issue:** `last_autovacuum` and `last_autoanalyze` are null for almost every table, including the two big ones. `n_live_tup` for `game_positions` reads 244,369 — actual count is 33,521,625. That means the planner has wildly stale row-count statistics, which is likely why the row count of `game_positions` had to do a 4.5s full-table scan even though it's a common operation.

Three possible causes:
1. Postgres was recently restarted (last week's hotfix); cumulative pg_stat counters are reset on restart but `stats_reset` shows null, which means the global stats reset was very recent and the views haven't observed an autovacuum cycle yet.
2. `autovacuum` is disabled or `autovacuum_naptime` is large in `postgresql.conf`.
3. Tables grew so fast (Phase 91 import stress test, user 95's 40K-game import) that autovacuum hasn't caught up.

Recommended: run `VACUUM ANALYZE` on `game_positions`, `games`, and `users` manually now, then check `pg_settings` for `autovacuum`, `autovacuum_naptime`, and `autovacuum_analyze_scale_factor`. With a 33M-row table the default `analyze_scale_factor=0.1` means analyze only triggers after 3.3M rows change — likely too lazy for this workload.

---

## Summary

- **DB is 13 GB**, almost entirely `game_positions` (11 GB) with a 1.77:1 index-to-data ratio.
- **Cache hit ratio is 92.55%** — below the 95% "good" line. Working set exceeds shared_buffers; either accept disk reads on cold hashes or upsize the box's RAM.
- **Stats are stale.** `last_autovacuum`/`last_autoanalyze` are null on the big tables and `n_live_tup` is two orders of magnitude off. The planner is running on bad cardinality estimates. **Top recommended action: run `VACUUM ANALYZE` on `game_positions`, `games`, `users` manually and review autovacuum tuning.**
- **Hot path: opening explorer.** The candidate-move WDL query (`gp1 → gp2 join with DISTINCT ON dedup + count filters`) and its dedup-CTE variants are the slowest user-facing queries (1.3s avg, 5.1s max). After re-analyzing tables, run `EXPLAIN (ANALYZE, BUFFERS)` against one of these with a real `user_id` to confirm the index plan is optimal — the 5s tail looks like it could be a planner choosing the wrong hash index after a hash-only filter changes.
- **Eval backfill is dominant cumulative load** — 14K+ pending-eval scans and 26K eval `UPDATE`s account for the most server time, but each call is fast (<1 ms). Healthy background work, no action needed.
- **No index is a real drop candidate.** `ix_gp_user_white_hash` / `ix_gp_user_black_hash` (2.5 GB combined) are lightly used (10-12 scans) but back the system-opening filter feature; only consider dropping if that feature is sunset.
- **User base: 95 total, 50 registered, 45 guests.** Activation looks healthy — 9 of last 10 signups linked a platform. User 95 alone is ~7.5% of all games.
- **Action items (prioritized):**
  1. `VACUUM ANALYZE` on `game_positions`, `games`, `users`; verify autovacuum is enabled in `postgresql.conf`.
  2. Consider tightening `autovacuum_analyze_scale_factor` for `game_positions` to 0.02 (or set a fixed `autovacuum_analyze_threshold`) so stats stay current under heavy ingestion.
  3. After the analyze runs, capture an `EXPLAIN (ANALYZE, BUFFERS)` of the slow opening-explorer query to confirm cardinality estimates improved.
  4. Reset `pg_stat_statements` after the above changes (`SELECT pg_stat_statements_reset();`) and re-check perf numbers in a week.
