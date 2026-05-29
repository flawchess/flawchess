# FlawChess DB Report — 2026-05-29

- **DB**: prod
- **Snapshot taken**: 2026-05-29T07:01:47Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 104 | 54 | 50 |

### 10 most recent users

| User | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 144 | ✅ | — | no | 2026-05-27 | 2026-05-27 | 76 | 4,458 |
| 143 | ✅ | — | yes | 2026-05-27 | 2026-05-27 | 35 | 2,339 |
| 142 | ✅ | — | yes | 2026-05-26 | 2026-05-26 | 204 | 12,593 |
| 109 | ✅ | ✅ | no | 2026-05-26 | 2026-05-26 | 12,443 | 1,027,667 |
| 108 | ✅ | ✅ | no | 2026-05-25 | 2026-05-25 | 3,738 | 230,076 |
| 107 | ✅ | ✅ | no | 2026-05-24 | 2026-05-24 | 13,942 | 892,553 |
| 106 | ✅ | — | yes | 2026-05-24 | 2026-05-24 | 22 | 788 |
| 105 | — | — | yes | 2026-05-23 | 2026-05-23 | 0 | 0 |
| 104 | ✅ | ✅ | yes | 2026-05-22 | 2026-05-22 | 133 | 6,705 |
| 103 | — | — | yes | 2026-05-22 | 2026-05-22 | 0 | 0 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 60 | 300,271 |
| lichess | 50 | 192,179 |

**Activity note:** 104 total users, ~52% registered / ~48% guest. Of the 10 most recent, 8 imported games and 2 (both guests, IDs 103 & 105) linked no platform and have 0 games — the typical "signed up, never imported" drop-off. A handful of power users dominate volume: users 107, 109, and 108 alone account for ~30k games and ~2.15M positions, roughly 6% of all games but a large share of position storage.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 14 GB |
| Total games | 492,450 |
| Total positions | 36,165,257 |
| Avg positions / game | ~73.4 |

### Per-table breakdown

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 4,706 MB | 7,684 MB | 12 GB |
| games | 1,275 MB | 177 MB | 1,452 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 16 kB | 632 kB | 648 kB |
| import_jobs | 40 kB | 408 kB | 448 kB |
| user_benchmark_percentiles | 88 kB | 72 kB | 160 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| users | 24 kB | 64 kB | 88 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| ix_gp_user_full_hash_move_san | game_positions | 2,210 MB |
| ix_gp_user_white_hash | game_positions | 1,303 MB |
| game_positions_pkey | game_positions | 1,300 MB |
| ix_gp_user_black_hash | game_positions | 1,294 MB |
| ix_gp_user_endgame_game | game_positions | 622 MB |
| ix_gp_user_game_ply | game_positions | 499 MB |
| ix_game_positions_game_id | game_positions | 452 MB |
| uq_games_user_platform_game_id | games | 55 MB |
| games_pkey | games | 22 MB |
| ix_games_user_id | games | 12 MB |
| ix_games_evals_pending | games | 9,640 kB |

All remaining indexes are ≤ 488 kB.

**Storage summary:** `game_positions` is the entire story — 12 GB of the 14 GB DB (86%). Its indexes (7.7 GB) outweigh its own data (4.7 GB) by 1.6×, which is expected given six hash/lookup indexes on a 36M-row table. The four Zobrist/lookup indexes (`full_hash_move_san`, `white_hash`, `black_hash`, PK) total ~6.1 GB and are the core of the position-matching architecture. Everything outside `game_positions` and `games` is negligible (< 5 MB combined).

## 2. Performance Analysis

### Buffer cache hit ratio

**82.10%** — below the 95% "good" floor, but **the cumulative stats have never been reset** (`stats_reset` is NULL), so this number is dominated by one-time bulk operations rather than steady-state serving. The two `COPY ... TO stdout` backfills alone streamed the full 36M-row `game_positions` table and 492k-row `games` table to disk (148s and 36s), plus several full-table `DELETE`/re-import passes — all of which generate large `blks_read` that never recur in normal operation. Steady-state per-user index lookups (the dominant real workload) are almost certainly cached far better. Not actionable as-is; see recommendations about resetting stats.

### Slowest queries by avg time (steady-state, excluding one-off backfills)

| avg_ms | max_ms | calls | total_ms | Query |
|---|---|---|---|---|
| 5,987 | 8,868 | 168 | 1,005,767 | benchmark percentile CTE (`recent_capped` → `endgame_game_ids` → achievable-gap) |
| 5,758 | 8,588 | 168 | 967,355 | benchmark percentile CTE (variant) |
| 5,732 | 6,594 | 168 | 963,002 | benchmark percentile CTE (variant) |
| 1,227 | 1,746 | 168 | 206,121 | benchmark percentile CTE (variant) |
| 1,227 | 6,137 | 180 | 220,807 | benchmark percentile CTE (variant) |
| 707 | 707 | 1 | 706 | endgame entry-eval aggregation (one-off) |
| 359 | 1,960 | 504 | 180,705 | benchmark percentile CTE (variant) |

One-off `COPY` / `DELETE` backfills (148s, 36s, etc.) are excluded above as non-recurring.

### Highest total server time

| total_ms | calls | avg_ms | Query |
|---|---|---|---|
| 1,005,767 | 168 | 5,987 | benchmark percentile CTE |
| 967,355 | 168 | 5,758 | benchmark percentile CTE (variant) |
| 963,002 | 168 | 5,732 | benchmark percentile CTE (variant) |
| 259,799 | 3,984 | 65 | `COPY game_positions(...)` (import inserts) |
| 220,807 | 180 | 1,227 | benchmark percentile CTE (variant) |
| 206,121 | 168 | 1,227 | benchmark percentile CTE (variant) |
| 180,705 | 504 | 359 | benchmark percentile CTE (variant) |
| 112,860 | 4,263 | 26 | eval-pending poller (`NOT EXISTS import_jobs` + games join) |
| 98,704 | 10,130,567 | 0.01 | FK `KEY SHARE` lock on `users` (auth/FK enforcement) |
| 73,344 | 1,100 | 67 | `INSERT ... user_benchmark_percentiles ON CONFLICT` |

The benchmark percentile CTE family dominates server time: across all its variants it accounts for **~3.5M ms (~58 min) of cumulative execution** — by far the largest controllable cost.

### Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---|---|---|---|
| game_positions | 540 | 52,508,727 | 36.1M | OK — seq scans are the rare COPY/backfill passes; index scans dominate by 5 orders of magnitude |
| users | 5,171,973 | 2 | 104 | OK — 104-row table, planner correctly prefers seq scan (FK `KEY SHARE` lookups) |
| import_jobs | 1,419,328 | 93 | 184 | OK — tiny table, seq scan is faster than index here |
| games | 305 | 12,677,263 | 482k | OK — index-driven |
| openings | 181 | 0 | 0 | OK — tiny lookup table, full scans expected |
| oauth_account | 8,323 | 0 | 1 | OK — 1 row |

No problematic seq-scan patterns. The high `seq_tup_read` on `game_positions` (15B) comes entirely from the 540 full-table backfill scans, not normal queries.

### Index usage

**Used heavily:** `ix_gp_user_endgame_game` (50M scans), `games_pkey` (12.5M), `ix_gp_user_game_ply`, `ix_game_positions_game_id`, `ix_gp_user_full_hash_move_san`, `ix_games_user_id`, `ix_games_evals_pending`.

**Zero scans (keep anyway):**
- `ix_gp_user_white_hash` (580 scans) / `ix_gp_user_black_hash` (148 scans) — low but non-zero; these back the "my-pieces-only" / system-opening queries (e.g. London filter). Keep. Together ~2.6 GB, the largest low-traffic indexes — worth monitoring if the feature stays rarely used, but they are core architecture, not droppable.
- `ix_users_email` — 0 scans but **required** for login/auth uniqueness. Keep.
- `oauth_account` indexes (`account_id`, `oauth_name`) — 0 scans but **required** for OAuth flow. Keep.
- `uq_*` / `*_pkey` (openings, llm_logs, import_jobs, game_positions, bookmarks) — 0 scans but enforce PK/unique constraints and FK integrity. Keep.
- `llm_logs` indexes (5×, all 0 scans) — table has only 5 rows; indexes are trivially small (16 kB each) and will matter as logging grows. Keep.

**No index is both large and genuinely droppable.** Nothing to remove.

### Dead tuples / autovacuum

| Table | n_live | n_dead | Dead % | Last autovacuum | Verdict |
|---|---|---|---|---|---|
| game_positions | 36.1M | 790,316 | 2.1% | 2026-05-27 | Healthy |
| games | 482k | 2,845 | 0.6% | 2026-05-28 | Healthy |
| users | 104 | 25 | — | never | Fine (tiny; autoanalyze ran 2026-05-27) |
| import_jobs | 184 | 50 | — | never | Fine (tiny) |

No table exceeds the 20% dead-tuple threshold. Autovacuum/autoanalyze are running recently on the large tables. Healthy.

## Summary

- **Size:** 14 GB total, and `game_positions` is 86% of it (12 GB). Its indexes (7.7 GB) exceed its data (4.7 GB) — inherent to the six-index Zobrist position-matching design, not a problem.
- **The one real optimization target** is the benchmark percentile CTE query family (`recent_capped → endgame_game_ids → entry_rows → scored`), which avgs ~6s/call and dominates server time at ~58 min cumulative. The culprit is the **`endgame_game_ids` and `entry_rows` CTEs, which scan and aggregate `game_positions` globally (no `user_id` predicate)** before the final join narrows to one user. Scoping those CTEs to the selected user's `recent_capped` game IDs (or pushing `user_id`/`game_id` filters down into them) should cut these from seconds to milliseconds. **Recommended** — biggest win available. If these run as a background batch (percentile precompute) the user-facing impact is limited, but it's still the largest controllable DB cost.
- **Cache hit ratio (82%)** looks low but is an artifact of never-reset cumulative stats skewed by one-time `COPY`/`DELETE` backfills. Not actionable directly. **Monitor:** the prod read-only role can't run `pg_stat_statements_reset()` / `pg_stat_reset()` — if you want a true steady-state read, reset stats from the app DB role (or on the server) and re-snapshot in a week.
- **Indexes:** no unused index is worth dropping; the zero/low-scan ones are all FK/PK/auth/architecture-critical. The `white_hash`/`black_hash` pair (~2.6 GB combined, low traffic) is the only thing worth keeping an eye on if system-opening queries stay rare.
- **Seq scans, dead tuples, autovacuum:** all healthy. No action.
