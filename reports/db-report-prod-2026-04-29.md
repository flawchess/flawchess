# FlawChess DB Report — 2026-04-29

- **DB**: prod
- **Snapshot taken**: 2026-04-29T22:23:46Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| total | registered | guest |
|------:|-----------:|------:|
| 63    | 41         | 22    |

### 10 most recent users

| id | chess.com | lichess | guest | created    | last login | games  | positions |
|---:|:---------:|:-------:|:-----:|:-----------|:-----------|-------:|----------:|
| 70 |           |    Y    |   Y   | 2026-04-28 | 2026-04-28 |  2,313 |   173,979 |
| 69 |           |         |       | 2026-04-28 | 2026-04-28 |      0 |         0 |
| 68 |     Y     |         |   Y   | 2026-04-27 | 2026-04-27 | 12,517 |   883,366 |
| 67 |           |    Y    |       | 2026-04-27 | 2026-04-27 |    130 |     8,904 |
| 66 |     Y     |         |       | 2026-04-26 | 2026-04-26 |  8,712 |   570,640 |
| 65 |     Y     |         |   Y   | 2026-04-25 | 2026-04-25 |      0 |         0 |
| 64 |     Y     |         |   Y   | 2026-04-24 | 2026-04-24 |      0 |         0 |
| 63 |           |         |   Y   | 2026-04-24 | 2026-04-24 |      0 |         0 |
| 62 |           |         |   Y   | 2026-04-21 | 2026-04-21 |      0 |         0 |
| 61 |           |         |   Y   | 2026-04-21 | 2026-04-21 |      0 |         0 |

### Platform breakdown

| platform   | users | games   |
|:-----------|------:|--------:|
| chess.com  |    36 | 202,751 |
| lichess    |    26 | 109,755 |

**Notes:** 4 of the 10 most recent signups (40%) actually imported games. The other 6 are guests who linked nothing or registered users who never linked a platform — typical drop-off after curiosity-only signups. User 68 is a guest who imported 12.5k chess.com games (largest single account this week). Across the full base, chess.com is roughly 2× lichess by game volume.

## 1. Storage Report

### Overview

| metric             | value          |
|:-------------------|---------------:|
| database size      | 6,122 MB       |
| total games        |        312,506 |
| total positions    |     22,298,230 |
| avg positions/game |          ~71.4 |

### Per-table breakdown

| table              | data    | indexes | total    |
|:-------------------|--------:|--------:|---------:|
| game_positions     | 2701 MB | 2839 MB | 5540 MB  |
| games              |  504 MB |   67 MB |  571 MB  |
| openings           |  832 kB |  888 kB | 1720 kB  |
| llm_logs           |  8 kB   |  272 kB |  280 kB  |
| import_jobs        |  16 kB  |  240 kB |  256 kB  |
| oauth_account      |  16 kB  |   80 kB |   96 kB  |
| position_bookmarks |  16 kB  |   64 kB |   80 kB  |
| users              |  16 kB  |   64 kB |   80 kB  |
| alembic_version    |  8 kB   |   16 kB |   24 kB  |

### Per-index breakdown (top by size)

| index                              | table          | size    |
|:-----------------------------------|:---------------|--------:|
| ix_gp_user_full_hash_move_san      | game_positions |  789 MB |
| game_positions_pkey                | game_positions |  478 MB |
| ix_gp_user_white_hash              | game_positions |  464 MB |
| ix_gp_user_black_hash              | game_positions |  463 MB |
| ix_gp_user_game_ply                | game_positions |  264 MB |
| ix_gp_user_endgame_game            | game_positions |  231 MB |
| ix_game_positions_game_id          | game_positions |  150 MB |
| uq_games_user_platform_game_id     | games          |   20 MB |
| games_pkey                         | games          | 7272 kB |
| ix_games_user_id                   | games          | 2456 kB |

**Storage notes:** `game_positions` is 90% of the database (5.5 GB of 6.1 GB). Its indexes (2.84 GB) actually exceed its data (2.70 GB) — index-to-data ratio of 1.05×, expected given the seven indexes on this table to support hash matching, transposition lookups, and endgame filtering. DB grew from ~5.4 GB (2026-04-25) to 6.1 GB (~13% in 4 days), driven by the 12.5k-game chess.com import on user 68 and the 8.7k-game import on user 66.

## 2. Performance Analysis

### Buffer cache hit ratio

**96.54%** — good (above 95%, below the 99% "excellent" line). With 7.6 GB RAM, 2 GB swap, and a 6.1 GB DB, the working set mostly fits in cache but heavy `game_positions` scans push some pages out. `stats_reset = NULL` means these are cumulative since DB creation, so the ratio is biased by all historical activity including bulk imports — current steady-state may be higher.

### Slowest queries by avg time (top 8 that matter)

| avg_ms  | max_ms  | calls | total_ms | rows   | query (truncated) |
|--------:|--------:|------:|---------:|-------:|:------------------|
| 7741.80 | 7741.80 |     1 |    7,742 |     1  | ad-hoc lichess eval-coverage rollup |
| 2912.48 | 2912.48 |     1 |    2,912 |     2  | ad-hoc per-platform eval coverage |
| 1887.69 | 1887.69 |     1 |    1,888 |     1  | ad-hoc total eval coverage |
| 1378.40 | 2114.24 |     3 |    4,135 | 8,652  | clock-array CTE (time-mgmt service) |
| 1114.57 | 1176.90 |     8 |    8,917 | 3,696  | endgame transitions CTE |
| 1054.37 | 1054.37 |     1 |    1,054 |     0  | `VACUUM ANALYZE game_positions` |
|  864.46 |  864.46 |     1 |      864 |     1  | `count(*) FROM game_positions` |
|  491.40 | 2443.99 |    36 |   17,690 | 11,994 | endgame transitions CTE |

The top 3 queries are one-shot ad-hoc rollups (likely from a `psql` session checking eval coverage), not user-facing — ignore for tuning. The genuinely warm path bottlenecks are the `WITH transitions ... LEAD(full_hash) OVER (PARTITION BY game_id)` CTEs that drive endgame analytics — multiple variants, all 400–1100 ms avg.

### Highest total time queries

| total_ms | calls     | avg_ms | rows      | query |
|---------:|----------:|-------:|----------:|:------|
|   47,995 |       150 | 319.96 |     1,500 | openings explorer hash-rollup |
|   40,649 |       499 |  81.46 |   848,300 | INSERT INTO game_positions (import) |
|   17,690 |        36 | 491.40 |    11,994 | endgame transitions CTE |
|   16,049 |        36 | 445.81 |   213,530 | clock-array CTE |
|   15,844 | 2,223,451 |   0.01 | 2,223,451 | FastAPI-Users `SELECT FROM users WHERE id = $1 FOR KEY SHARE` |
|   13,874 |        34 | 408.06 |     3,386 | endgame transitions CTE variant |
|   11,727 |       260 |  45.10 |       260 | WDL aggregation |
|    8,917 |         8 | 1114.57|     3,696 | endgame transitions CTE variant |
|    7,365 |       130 |  56.66 |     1,153 | next-move WDL |

The openings-explorer query dominates server time (48s total, 320ms avg, 150 calls). The FastAPI-Users session lookup runs 2.2M times at 0.007 ms each — that's the auth middleware on every authenticated request, totally fine.

### Sequential scan analysis

| table              | seq_scans   | idx_scans | live_tup | verdict |
|:-------------------|------------:|----------:|---------:|:--------|
| users              |   1,729,666 |         0 |       63 | ✅ expected (tiny table, optimizer picks seq scan) |
| oauth_account      |       2,423 |         0 |       29 | ✅ expected (tiny) |
| import_jobs        |       2,305 |         0 |       95 | ✅ expected (tiny) |
| openings           |         361 |         1 |    3,641 | ⚠️ 1.3M tuples read — small but hot, may benefit from index hits |
| position_bookmarks |         126 |         0 |       52 | ✅ expected (tiny) |
| game_positions     |          77 |  2,454,361| 22.3M    | ✅ healthy (idx >> seq) |
| games              |          47 | 30,541,785|  312k    | ✅ healthy |
| llm_logs           |          46 |         0 |       13 | ✅ expected (tiny) |

The `users` seq-scan count looks alarming but is correct: PostgreSQL's planner ignores `ix_users_email` on a 63-row table because a heap scan is faster than an index lookup for that size. The 1.7M seq_scans are mostly the FastAPI-Users `FOR KEY SHARE` lookup; total time is ~16s across 2.2M calls = trivial.

### Index usage — unused indexes

| index                              | table          | size    | scans | verdict |
|:-----------------------------------|:---------------|--------:|------:|:--------|
| game_positions_pkey                | game_positions |  478 MB |     0 | keep (PK, FK integrity) |
| ix_gp_user_black_hash              | game_positions |  463 MB |   154 | ⚠️ very low usage vs 464 MB white_hash (3,424 scans) |
| uq_games_user_platform_game_id     | games          |   20 MB |24,858 | keep (uniqueness) |
| llm_logs_*                         | llm_logs       | 16 kB ×5 |    0 | keep (tiny, will populate) |
| oauth_account_*                    | oauth_account  | 16 kB ×3 |    0 | keep (auth-flow) |
| ix_position_bookmarks_user_id      | position_bookmarks | 16 kB |  0 | keep (FK) |
| ix_users_email                     | users          |  16 kB  |     0 | keep (login-flow, optimizer chose seq scan because table is 63 rows) |
| openings_pkey, ix_openings_eco_name, uq_openings_eco_name_pgn | openings | 96-488 kB | 0-1 | keep (uniqueness/FK) |
| ix_import_jobs_user_id             | import_jobs    |  16 kB  |     0 | keep (FK) |

**Notable:** `ix_gp_user_black_hash` (463 MB) was used 154 times vs `ix_gp_user_white_hash` (464 MB) used 3,424 times — black-hash queries are ~22× rarer. Both are required for the "system openings" feature (queries on a single color's pieces). Worth investigating whether the asymmetry is a UI default favoring white perspective, or a missing query path that should be using it. Don't drop yet — feature is genuine.

### Dead tuples / autovacuum

| table          | live_tup | dead_tup | dead %  | last autovacuum     |
|:---------------|---------:|---------:|--------:|:--------------------|
| game_positions | 22.3M    |        0 |   0.00% | 2026-04-26          |
| games          |  312k    |   22,909 |   7.30% | 2026-04-26          |
| users          |     63   |       18 |  28.57% | (autoanalyze 04-29) |
| openings       |  3,641   |        0 |   0.00% | 2026-04-26          |

Only `users` has a high dead-tuple ratio (29%), but absolute count is 18 rows on a 63-row table. Trivial — autovacuum threshold is `n_dead_tup > 50 + 0.2 × n_live_tup ≈ 63`, so PostgreSQL is correctly leaving it alone. No action needed.

### Recommendations

**No action needed**
- Buffer cache hit ratio at 96.5% is healthy for a 6 GB DB on 7.6 GB RAM. Will improve as bulk-import workload subsides.
- All `seq_scan`-heavy small tables are correct optimizer behavior — do not add indexes there.
- Dead-tuple ratios are healthy.
- All "0-scan" indexes are either FK/PK/uniqueness-required or auth-flow indexes that activate under specific conditions — keep them.

**Monitor**
- DB grew 13% in 4 days driven by two large imports. At current rate, 6.1 GB → ~7 GB in a month. The 75 GB disk has plenty of headroom but worth watching. The `game_positions` indexes (2.84 GB) are the dominant grower.
- `pg_stat_statements` has never been reset (`stats_reset = NULL`). Consider `SELECT pg_stat_statements_reset()` after the next deploy to get a clean picture of steady-state performance, since current cumulative stats include all bulk-import history.
- `ix_gp_user_black_hash` usage is ~22× lower than its white-hash sibling — investigate whether this reflects user behavior (most analyze games as white-side first) or a missing query path. Don't drop without that answer.

**Recommended**
- The openings-explorer hash-rollup query is the #1 total-time consumer (48s / 150 calls). At 320ms avg it's not slow per-call but it's the most-frequent expensive read. Run `EXPLAIN (ANALYZE, BUFFERS)` on it next time you're investigating hot paths to confirm it's hitting `ix_gp_user_full_hash_move_san` cleanly.
- Endgame transitions CTEs (`WITH transitions AS ... LEAD(full_hash) OVER (PARTITION BY game_id ORDER BY ply)`) average 400–1100ms. Several variants suggest service-level duplication — worth checking if these can share a CTE or be cached at the user level since endgame data is append-only between imports.

**Consider**
- After `pg_stat_statements_reset`, schedule a follow-up report in 7-14 days to compare steady-state vs cumulative. That's the cleanest way to decide whether the endgame CTE work is worth optimizing.

## Summary

- **6.1 GB DB**, 90% in `game_positions` (22.3M rows). Indexes there (2.84 GB) slightly exceed data (2.70 GB) — expected given seven indexes for hash matching and endgame queries.
- **96.54% cache hit ratio** — healthy but cumulative since DB creation. Reset stats for a cleaner read.
- **No bloat or autovacuum issues.**
- **Hot paths**: openings-explorer hash-rollup (320ms × 150 calls) and endgame-transitions CTEs (400–1100ms each) dominate read-side server time. Imports dominate write-side (40s INSERT total). All within acceptable bounds for current scale.
- **Watch**: DB grew 13% in 4 days from two large imports (users 66 and 68). Disk has headroom; just track the rate.
- **One real curiosity**: `ix_gp_user_black_hash` is used 22× less than `ix_gp_user_white_hash` despite being the same size. Worth understanding before considering it a candidate for removal.
