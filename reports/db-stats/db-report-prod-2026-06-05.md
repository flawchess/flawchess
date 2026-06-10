# FlawChess DB Report — 2026-06-05

- **DB**: prod
- **Snapshot taken**: 2026-06-05T07:18:11Z
- **Sections run**: users / storage / performance
- **Stats window**: `pg_stat_statements` last reset 2026-05-29T07:43:49Z (~7 days of cumulative activity)

## 0. Users Overview

### User summary

| Total users | Registered | Guest |
|---|---|---|
| 120 | 60 | 60 |

### 10 most recent users

| User ID | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 160 | – | ✓ | guest | 2026-06-04 | 2026-06-04 | 396 | 23,587 |
| 159 | ✓ | – | guest | 2026-06-04 | 2026-06-04 | 178 | 10,839 |
| 158 | ✓ | – | guest | 2026-06-04 | 2026-06-04 | 406 | 25,631 |
| 157 | ✓ | ✓ | registered | 2026-06-03 | 2026-06-03 | 11,226 | 843,030 |
| 156 | ✓ | – | guest | 2026-06-03 | 2026-06-03 | 1,523 | 86,710 |
| 155 | – | – | registered | 2026-06-03 | 2026-06-03 | 0 | 0 |
| 154 | ✓ | – | guest | 2026-06-02 | 2026-06-02 | 1,108 | 71,495 |
| 153 | – | ✓ | registered | 2026-06-02 | 2026-06-02 | 764 | 52,761 |
| 152 | – | – | guest | 2026-06-02 | 2026-06-02 | 0 | 0 |
| 151 | ✓ | – | registered | 2026-06-01 | 2026-06-01 | 27 | 1,238 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 72 | 309,850 |
| lichess | 53 | 204,288 |

**Activity note:** 120 total users, an even 60/60 registered-vs-guest split. Of the 10 most recent signups, 8 imported games (2 — IDs 155 and 152 — linked no platform and have zero games). Healthy engagement: the cohort includes one power user (ID 157, 11.2k games / 843k positions) and several mid-size imports in the 400–1,500 game range. Cross-platform usage is real: 72 + 53 = 125 platform-links across 120 users, so a handful of users have both chess.com and lichess connected.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 8,870 MB (~8.66 GB) |
| Total games | 514,138 |
| Total positions | 37,687,745 |
| Avg positions / game | ~73.3 |

### Per-table breakdown (sorted by total size)

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 4,682 MB | 2,764 MB | 7,445 MB |
| games | 1,275 MB | 125 MB | 1,400 MB |
| benchmark_cohort_cdf | 8,184 kB | 4,784 kB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 24 kB | 680 kB | 704 kB |
| import_jobs | 48 kB | 408 kB | 456 kB |
| user_benchmark_percentiles | 120 kB | 96 kB | 216 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| oauth_account | 24 kB | 80 kB | 104 kB |
| users | 32 kB | 64 kB | 96 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,134 MB |
| ix_gp_user_endgame_game | game_positions | 514 MB |
| ix_gp_user_full_hash_move_san | game_positions | 418 MB |
| ix_game_positions_game_id | game_positions | 253 MB |
| ix_gp_user_white_hash | game_positions | 222 MB |
| ix_gp_user_black_hash | game_positions | 221 MB |
| uq_games_user_platform_game_id | games | 31 MB |
| games_pkey | games | 11 MB |
| ix_games_user_id | games | 3,768 kB |
| benchmark_cohort_cdf_pkey | benchmark_cohort_cdf | 3,752 kB |

All remaining indexes are ≤ 1 MB.

**Storage summary:** `game_positions` is 84% of the database (7.4 GB of 8.66 GB) — expected, it holds 37.7M rows at ~73 positions/game. Its index footprint (2.76 GB) is 59% of its own data size, driven by six indexes over 200 MB each. The primary key alone is 1.13 GB. Everything outside `game_positions` and `games` is rounding error (< 15 MB combined). DB growth is essentially linear in imported positions; nothing here is anomalous.

## 2. Performance Analysis

### Buffer cache hit ratio

**98.03%** — **good** (95–99% band). Slightly below the >99% "excellent" threshold, consistent with a 7.4 GB hot table on a 16 GB host where `shared_buffers=4GB` can't hold all of `game_positions`. Not a concern given the working set; the misses are large analytics scans, not hot-path lookups.

### Slowest queries by avg time (steady-state, excluding one-off DDL/maintenance)

One-off maintenance ran in-window and dominates raw avg-time (REINDEX/VACUUM/CREATE INDEX on `game_positions`, plus an 82 s `count(DISTINCT (game_id, ply))` audit). Those are excluded below as non-recurring. The recurring offenders:

| avg_ms | max_ms | calls | total_ms | Query |
|---|---|---|---|---|
| 14,645 | 14,814 | 8 | 117,162 | openings explorer dedup (`openings_dedup` … `count(distinct games.id)`) |
| ~1,340 | 4,294 | 360 | 482,560 | insights `recent_capped` CTE (recency-capped per-user endgame/opening scan) |
| 1,210 | 2,370 | 4 | 4,841 | openings explorer dedup (smaller variant) |

The 14.6 s openings-explorer dedup query (8 calls) is the worst per-call recurring query. Likely the deep 16-half-move opening scan against a large user's `game_positions`.

### Highest total time queries (server-time optimization targets)

| total_ms | calls | avg_ms | rows | Query |
|---|---|---|---|---|
| 482,560 | 360 | 1,340 | 320 | insights `recent_capped` CTE (variant A) |
| 176,071 | 1,080 | 163 | 752 | insights `recent_capped` CTE (variant B) |
| 150,037 | 360 | 417 | 246 | insights `recent_capped` CTE (variant C) |
| 137,735 | 360 | 383 | 320 | insights `recent_capped` CTE (variant D) |
| 117,932 | 2,042 | 58 | 2.2M | `COPY game_positions` (bulk import write path) |
| 117,162 | 8 | 14,645 | 80 | openings explorer dedup |
| 72,329 | 2,610 | 28 | 29 | import/eval polling (`evals_completed_at IS NULL` + import_jobs) |
| 44,068 | 4,505,989 | 0.01 | — | FastAPI-Users `FOR KEY SHARE` row-lock on `users` |

The `recent_capped` insights CTE family (variants A–D plus several smaller ones) is the dominant server-time consumer: well over 1,000,000 ms total across ~2,500 calls. This is the single best optimization target. The `COPY` and the 4.5M-call user row-lock are high-volume but individually cheap (0.01–58 ms) and inherent to the import + auth paths.

### Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---|---|---|---|
| game_positions | 75 | 303,775,946 | 37.7M | Healthy — seq scans negligible vs index scans |
| import_jobs | 2,345,814 | 63,204 | 215 | Tiny table (215 rows) — seq scan is optimal, ignore |
| users | 2,313,628 | 5 | 120 | Tiny table (120 rows) — seq scan is optimal, ignore |
| games | 97 | 15,821,369 | 501k | Healthy — index-driven |
| openings | 315 | 0 | 0 | Empty/seed table, irrelevant |

The two tables with millions of seq scans (`import_jobs`, `users`) are both < 250 rows. PostgreSQL correctly prefers a seq scan over an index for tables this small — these counts are expected and not actionable. The two large tables (`game_positions`, `games`) are overwhelmingly index-driven.

### Index usage

**Unused indexes (0 scans this window):**

- `ix_users_email` — **keep** (login lookup; window had no by-email logins but it's auth-critical).
- `ix_oauth_account_account_id`, `ix_oauth_account_oauth_name`, `oauth_account_pkey` — **keep** (OAuth flow integrity).
- `openings_pkey`, `uq_openings_eco_name_pgn`, `ix_openings_eco_name` — **keep** (openings table is seed data; near-empty live stats but used at seed/lookup time).
- All 6 `llm_logs` indexes — **keep for now**, but worth noting: `llm_logs` has only 5 rows and 680 kB of indexes (its indexes are 28× its data). Over-indexed for its size. Not worth dropping (cost is trivial), just flagged.
- `ix_gp_user_white_hash` (222 MB, 54 scans) and `ix_gp_user_black_hash` (221 MB, 7,410 scans) — **keep**. White-hash usage is low this window but these power the "my pieces only" system-opening filter, a core feature. Low scan count reflects feature usage mix, not redundancy.

No index is both large and genuinely droppable. Nothing recommended for removal.

### Dead tuples / autovacuum

| Table | n_live | n_dead | Dead % | Last autovacuum | Last autoanalyze |
|---|---|---|---|---|---|
| game_positions | 37.7M | 703,782 | 1.9% | never | 2026-06-03 |
| games | 501k | 6,467 | 1.3% | 2026-06-03 | 2026-06-03 |
| users | 120 | 40 | 25% | never | 2026-06-05 |
| import_jobs | 215 | 14 | 6.1% | 2026-06-03 | 2026-06-04 |

All large tables are well under the 20% dead-tuple threshold. `users` shows 25% dead but that's 40 rows on a 120-row table — autoanalyze ran today and autovacuum on a table this size is irrelevant to performance. No bloat concern anywhere. `game_positions` has never been autovacuumed (only autoanalyzed), but at 1.9% dead tuples on an append-mostly table that's fine; the manual `VACUUM ANALYZE` seen in the stats window already handled it.

## Summary

- **Size:** 8.66 GB total, 84% of it (`game_positions`, 7.4 GB / 37.7M rows) plus another 1.4 GB in `games`. Growth is linear in imported positions; storage is healthy and unsurprising.
- **Indexes:** 2.76 GB of indexes on `game_positions`, dominated by the 1.13 GB PK and five 200–520 MB secondary indexes. All are justified by core features (hash matching, endgame, system-opening filter). None droppable.
- **Cache:** 98.03% hit ratio — good, expected for a 7.4 GB hot table on a 16 GB box.
- **Top optimization target:** the insights **`recent_capped` CTE family** dominates server time (>1,000,000 ms across ~2,500 calls, top variant 482 s / 360 calls @ 1.34 s avg). The openings-explorer **dedup query** is the worst per-call recurring query at 14.6 s. Both are analytics endpoints, not hot-path lookups — worth a targeted EXPLAIN/index review next, but not an availability risk.
- **No action needed:** seq scans on `users`/`import_jobs` (tiny tables, optimal), all "unused" indexes (auth/OAuth/seed/feature-critical), dead tuples (all large tables < 2%).
- **Note:** `pg_stat_statements` was last reset 2026-05-29, so the cumulative numbers cover ~7 days and include one-off REINDEX/VACUUM/CREATE INDEX maintenance (excluded from the recurring-query analysis above). Consider resetting stats to get a clean steady-state window before profiling the `recent_capped` query for optimization.
