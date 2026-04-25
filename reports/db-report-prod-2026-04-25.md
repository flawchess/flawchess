# FlawChess DB Report — 2026-04-25

- **DB**: prod
- **Snapshot taken**: 2026-04-25T09:11:53Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 57 | 38 | 19 |

### 10 most recent users

| ID | chess.com? | lichess? | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 64 | yes | no | yes | 2026-04-24 | 2026-04-24 | 0 | 0 |
| 63 | no | no | yes | 2026-04-24 | 2026-04-24 | 0 | 0 |
| 62 | no | no | yes | 2026-04-21 | 2026-04-21 | 0 | 0 |
| 61 | no | no | yes | 2026-04-21 | 2026-04-21 | 0 | 0 |
| 60 | no | no | yes | 2026-04-21 | 2026-04-21 | 0 | 0 |
| 59 | no | no | yes | 2026-04-21 | 2026-04-21 | 0 | 0 |
| 58 | no | yes | no | 2026-04-20 | 2026-04-20 | 2,121 | 142,862 |
| 57 | no | no | yes | 2026-04-20 | 2026-04-20 | 0 | 0 |
| 56 | yes | no | yes | 2026-04-19 | 2026-04-19 | 9,651 | 713,101 |
| 55 | yes | no | no | 2026-04-19 | 2026-04-19 | 18,405 | 1,394,787 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 34 | 181,230 |
| lichess | 23 | 106,961 |

### Notes

- Of the 10 most recent signups, **only 3 imported games** (IDs 55, 56, 58). The other 7 are guest accounts that never linked a platform — typical guest-mode landing-page churn.
- Guest:registered ratio is 19:38 ≈ 1:2 — guest mode is generating real signal, but conversion to data import is low (most guests never import).
- chess.com dominates: 1.7× more games than lichess across a similar user base.
- User 55 alone holds **18.4k games / 1.4M positions** — single largest user, ~6.4% of all games.

---

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | **7,746 MB** |
| Total games | 288,191 |
| Total positions | 20,618,423 |
| Avg positions / game | ~71.5 |

### Per-table breakdown

| Table | Data | Indexes | Total |
|---|---|---|---|
| game_positions | 2,563 MB | 4,282 MB | **6,845 MB** |
| games | 795 MB | 94 MB | 888 MB |
| openings | 1,600 kB | 1,624 kB | 3,224 kB |
| import_jobs | 72 kB | 248 kB | 320 kB |
| llm_logs | 8 kB | 192 kB | 200 kB |
| users | 24 kB | 72 kB | 96 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| position_bookmarks | 24 kB | 64 kB | 88 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| ix_gp_user_full_hash_move_san | game_positions | 1,139 MB |
| ix_gp_user_full_hash | game_positions | 873 MB |
| ix_gp_user_white_hash | game_positions | 665 MB |
| ix_gp_user_black_hash | game_positions | 660 MB |
| game_positions_pkey | game_positions | 482 MB |
| ix_gp_user_endgame_game | game_positions | 236 MB |
| ix_game_positions_game_id | game_positions | 158 MB |
| ix_gp_user_endgame_class | game_positions | 67 MB |
| uq_games_user_platform_game_id | games | 35 MB |
| games_pkey | games | 13 MB |
| ix_games_user_id | games | 6.4 MB |

All other indexes are <1 MB each.

### Storage notes

- `game_positions` is **88% of the database** (6.85 GB of 7.75 GB).
- **Indexes (4.28 GB) are 1.67× larger than the table data (2.56 GB) on `game_positions`** — extreme but expected given the four hash indexes (full/white/black + composite-with-move_san) that power the position-lookup architecture.
- Top 4 hash indexes alone = **3.34 GB** (43% of the DB).
- `game_positions_pkey` is 482 MB but registers **0 idx_scan** — see Section 2 for analysis (likely composite PK on `(game_id, ply)` only used during inserts/FK checks).

---

## 2. Performance Analysis

### Buffer cache hit ratio

**99.93%** — excellent. PostgreSQL is serving virtually all reads from RAM.

> Note: `pg_stat_database.stats_reset` is `null` — these are lifetime cumulative stats. Numbers below are not "recent" performance.

### Slowest queries (by avg time, top 10)

| avg_ms | max_ms | calls | total_ms | query summary |
|---|---|---|---|---|
| **7,495,016** | 98,497,982 | 39 | 292,305,620 | `games JOIN (positions array_agg ply, clock_seconds...)` per-game clock series |
| 42,227 | 42,227 | 1 | 42,227 | endgame_games CTE (first_endgame + endgame_games) |
| 39,708 | 39,708 | 1 | 39,708 | endgame_games CTE variant |
| 16,378 | 16,378 | 1 | 16,378 | first_endgame + clock_raw CTE |
| 14,828 | 14,828 | 1 | 14,828 | first_endgame + clock_raw variant |
| 12,556 | 12,818 | 2 | 25,111 | first_endgame + bucketed (ELO buckets) |
| 12,507 | 12,507 | 1 | 12,507 | first_endgame + bucketed variant |
| 10,574 | 10,574 | 1 | 10,574 | first_endgame + bucketed game_id list |
| 2,769 | 2,769 | 1 | 2,769 | the `users` recent-signups query you just ran |
| 1,900 | 2,907 | 2 | 3,799 | endgame_game_ids + WDL rows |

### Highest total time (worst cumulative cost)

| total_ms | calls | avg_ms | rows | query summary |
|---|---|---|---|---|
| **292,305,620** | 39 | 7,495,016 | 222,971 | clock series per-game (same query as above) |
| 42,227 | 1 | 42,227 | 6 | endgame_games CTE |
| 39,708 | 1 | 39,708 | 8 | endgame_games variant |
| 25,111 | 2 | 12,556 | 22 | first_endgame + bucketed |
| 16,378 | 1 | 16,378 | 4 | first_endgame + clock_raw |
| 14,828 | 1 | 14,828 | 40 | first_endgame + clock_raw variant |
| 12,507 | 1 | 12,507 | 6 | first_endgame + bucketed variant |
| 10,574 | 1 | 10,574 | 68 | first_endgame + bucketed game_id list |
| 5,357 | 39 | 137 | 222,868 | Endgame ELO timeline query |
| 4,791 | 25 | 192 | 151,320 | endgame entry/after material delta |

### Sequential scan analysis

| Table | seq_scan | idx_scan | seq_tup_read | verdict |
|---|---|---|---|---|
| game_positions | 22 | 343M | 266M | fine — seq scans are negligible vs index activity |
| users | 3,281,041 | 86 | 87M | **fine** — 57-row table, seq is correctly cheaper than index lookups |
| games | 13 | 16.8M | 3.2M | fine |
| openings | 228 | 0 | 830k | small (~100 rows? **`n_live_tup=0` is suspicious**); seq scans expected for this size |
| import_jobs | 3,542 | 144 | 249k | fine — 81 rows, seq scans cheaper |
| oauth_account | 2,789 | 0 | 67k | fine — 4 rows |
| position_bookmarks | 144 | 0 | 5,829 | fine — 4 rows |
| llm_logs | 18 | 21 | 29 | fine — 5 rows, brand new table |

### Index usage — unused indexes

| Index | Table | Size | Verdict |
|---|---|---|---|
| game_positions_pkey | game_positions | 482 MB | **keep** — required for FK/PK integrity even if not directly scanned |
| ix_users_email | users | 16 kB | **keep** — needed by FastAPI-Users login flow (table tiny anyway) |
| ix_oauth_account_oauth_name | oauth_account | 16 kB | **keep** — OAuth lookup; tiny |
| ix_oauth_account_account_id | oauth_account | 16 kB | **keep** — OAuth lookup; tiny |
| oauth_account_pkey | oauth_account | 16 kB | keep |
| openings_pkey, uq_openings_eco_name_pgn, ix_openings_eco_name | openings | 1.5 MB total | keep — opening matching uses these once tables grow / on cold paths |
| bookmarks_pkey, ix_position_bookmarks_user_id | position_bookmarks | 32 kB | keep — feature has 4 rows so far |
| ix_llm_logs_findings_hash, ix_llm_logs_endpoint_created_at, ix_llm_logs_created_at | llm_logs | 48 kB | keep — table just seeded (5 rows), indexes await traffic |
| alembic_version_pkc | alembic_version | 16 kB | keep |

**Nothing worth dropping.** All "0-scan" indexes are either tiny or required for integrity.

### Most-used indexes

| Index | Scans | Notes |
|---|---|---|
| ix_gp_user_endgame_game | 331,537,540 | **the workhorse** — endgame analytics |
| games_pkey | 16,778,249 | game lookups by id |
| ix_game_positions_game_id | 11,548,096 | join from games → positions |
| uq_games_user_platform_game_id | 46,617 | dedup on import |
| ix_gp_user_full_hash_move_san | 9,722 | move-explorer queries |
| ix_games_user_id | 5,184 | per-user filters |
| ix_gp_user_full_hash | 2,200 | position lookup |

### Dead tuples / autovacuum

| Table | live | dead | dead % | last_autovacuum |
|---|---|---|---|---|
| game_positions | 20,611,097 | 545,331 | 2.6% | 2026-04-20 23:09 |
| games | 305,411 | 18,883 | 6.2% | 2026-04-21 10:08 |
| users | 57 | 38 | 40% | 2026-04-21 15:12 |
| import_jobs | 81 | 5 | 5.8% | 2026-04-22 02:58 |
| openings | 0 | 0 | — | never |

- `users` 40% dead is cosmetic — 38 rows, autovacuum already ran a few days ago.
- `openings` shows `n_live_tup=0` — stats are stale (table actually has rows; never analyzed). Run `ANALYZE openings` to refresh.
- All other tables healthy.

---

## Summary

**Top findings**

- **One query has destroyed 292 billion ms (≈3.4 days of CPU) across 39 calls** — the per-game clock-array `array_agg` join with `games`. Average 2 hours per call, max 27 hours. Almost certainly running over a power user (e.g. user 55 with 1.4M positions) without LIMIT/pagination, then timing out and retrying.
- DB is **7.75 GB**, 88% in `game_positions`. Indexes on that table (4.28 GB) outweigh the data (2.56 GB) by 1.67×.
- Cache hit ratio **99.93%** — RAM is sized correctly for the working set.
- All 8 endgame-CTE queries averaging 10-42s share a common pattern: `first_endgame AS (SELECT min(ply)... GROUP BY game_id HAVING count(*) >= N)`. This forces a full GROUP BY over the user's `endgame_class IS NOT NULL` rows. Worth investigating an `EXPLAIN ANALYZE`.
- 19 of 57 users are guests; only 3 of the 10 most recent signups actually imported games — guest landing churn is real but most never convert to data import.

**Recommended actions**

- **Investigate the runaway clock-array query** (the 7.5M-ms-avg one). Likely candidates: missing pagination, missing `WHERE user_id = ?` selectivity, or query running unbounded during page render. Find the call site, look for a power-user trigger, and add LIMIT or chunking. This single query is causing 99.9%+ of all measurable DB time.
- Run `ANALYZE openings;` to refresh stale planner stats (currently shows `n_live_tup=0`).
- Reset pg_stat_statements (`SELECT pg_stat_statements_reset();`) **after** investigating the runaway query — current stats span unknown history and the one bad query swamps everything else. Re-check in a week for clean signal.

**No action needed**

- Cache hit ratio, autovacuum cadence, sequential-scan profile on tiny tables (users/openings/oauth/etc.), all "0-scan" indexes (all required for integrity or in tables that haven't received traffic yet).

**Monitor**

- `game_positions` indexes are the dominant disk consumer. As game count grows linearly, index size will too — current 4.28 GB will be ~15 GB at 1M games. Plan for partitioning by `user_id` if a single user ever exceeds ~5M positions, or evaluate dropping `ix_gp_user_white_hash` / `ix_gp_user_black_hash` (660 MB each, only 151 + 74 scans lifetime) if "my pieces only" usage stays this rare.
