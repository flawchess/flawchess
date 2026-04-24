# FlawChess DB Report — 2026-04-21

- **DB**: prod
- **Snapshot taken**: 2026-04-21T15:52:26Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| Total users | Registered | Guest |
|---|---|---|
| 52 | 38 | 14 |

### 10 most recent users

| ID | Email | chess.com | lichess | Guest? | Created | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|---|
| 59 | guest_bc5f…@guest.local | — | — | yes | 2026-04-21 | 2026-04-21 | 0 | 0 |
| 58 | saip106@msn.com | — | saip106 | no | 2026-04-20 | 2026-04-20 | 2,121 | 142,862 |
| 57 | guest_ec4c…@guest.local | — | — | yes | 2026-04-20 | 2026-04-20 | 0 | 0 |
| 56 | guest_ddf5…@guest.local | Kiyochess7 | — | yes | 2026-04-19 | 2026-04-19 | 9,651 | 713,101 |
| 55 | olivierdeversail1@gmail.com | IvoireChess | — | no | 2026-04-19 | 2026-04-19 | 18,405 | 1,394,787 |
| 54 | mukundakulkarni9@gmail.com | — | — | no | 2026-04-18 | 2026-04-18 | 0 | 0 |
| 53 | guest_7157…@guest.local | — | Na3Enjoyer | yes | 2026-04-18 | 2026-04-18 | 1,051 | 64,327 |
| 52 | juebjueb@gmail.com | — | — | no | 2026-04-18 | 2026-04-18 | 0 | 0 |
| 51 | guest_b459…@guest.local | Sppo | — | yes | 2026-04-18 | 2026-04-18 | 602 | 37,076 |
| 50 | pradippanda.mtk@gmail.com | shubhankarpanda | — | no | 2026-04-17 | 2026-04-17 | 1,653 | 91,948 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 34 | 181,062 |
| lichess | 23 | 106,958 |

**User activity note**: Of the last 10 signups, 6 imported games (3 of them substantial: 2.1k / 9.7k / 18.4k), 4 signed up but never imported (including 2 registered accounts and 2 fresh guests). Guest:registered ratio is 14:38 (~27% guest), with guests contributing some of the heaviest data footprints (user 56 alone has 713k positions).

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 7,743 MB (~7.6 GB) |
| Total games | 288,020 |
| Total positions | 20,601,053 |
| Avg positions/game | ~71.5 |

### Per-table breakdown

| Table | Data | Indexes | Total |
|---|---|---|---|
| game_positions | 2,561 MB | 4,281 MB | 6,842 MB |
| games | 795 MB | 94 MB | 888 MB |
| openings | 1,600 kB | 1,624 kB | 3,224 kB |
| import_jobs | 64 kB | 248 kB | 312 kB |
| users | 24 kB | 72 kB | 96 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| position_bookmarks | 24 kB | 64 kB | 88 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top 15)

| Index | Table | Size |
|---|---|---|
| ix_gp_user_full_hash_move_san | game_positions | 1,139 MB |
| ix_gp_user_full_hash | game_positions | 873 MB |
| ix_gp_user_white_hash | game_positions | 665 MB |
| ix_gp_user_black_hash | game_positions | 660 MB |
| game_positions_pkey | game_positions | 482 MB |
| ix_gp_user_endgame_game | game_positions | 235 MB |
| ix_game_positions_game_id | game_positions | 158 MB |
| ix_gp_user_endgame_class | game_positions | 67 MB |
| uq_games_user_platform_game_id | games | 35 MB |
| games_pkey | games | 13 MB |
| ix_games_user_id | games | 6,584 kB |
| uq_openings_eco_name_pgn | openings | 888 kB |
| ix_openings_eco_name | openings | 512 kB |
| openings_pkey | openings | 184 kB |
| (others) | | ≤ 16 kB each |

**Storage highlights**

- `game_positions` dominates at 88% of total DB size (6,842 of 7,743 MB).
- Index-to-data ratio on `game_positions` is **1.67x** — indexes outweigh the actual row data. Driven by 4 user+hash btrees (~3.3 GB combined) for move-explorer queries, plus the endgame indexes.
- `games` is well-proportioned (94 MB indexes on 795 MB data, ~0.12x).
- Growth outlook: at ~71 positions/game, each additional 100k games adds roughly ~2.4 GB to the DB.

## 2. Performance Analysis

### Buffer cache hit ratio

**99.65%** — excellent. Virtually all reads served from shared buffers / OS cache; disk I/O is not the bottleneck. Note: `stats_reset` is null, so these are cumulative since server start.

### Slowest queries by avg time (filtered to meaningful ones)

| avg_ms | max_ms | calls | total_ms | query |
|---|---|---|---|---|
| 42,602 | 746,363 | 58 | 2,470,931 | **clock_per_game join**: games ⋈ array_agg(ply/clock) from game_positions — time-pressure clock curves |
| 40,931 | 40,931 | 1 | 40,931 | endgame WITH `first_endgame` / `endgame_games` CTE (platform+tc rollup) |
| 39,042 | 39,042 | 1 | 39,042 | same endgame CTE variant |
| 38,940 | 38,940 | 1 | 38,940 | same endgame CTE variant |
| 37,232 | 37,232 | 1 | 37,232 | endgame CTE with user_color CASE |
| 34,218 | 34,218 | 1 | 34,218 | endgame CTE variant |
| 32,930 | 578,953 | 53 | 1,745,302 | **span join**: per-game endgame span + entry/after imbalance rollup |
| 32,158 | 32,158 | 1 | 32,158 | endgame CTE variant |
| 26,113 | 26,113 | 1 | 26,113 | endgame CTE variant |
| 18,906 | 376,223 | 62 | 1,172,200 | **per_class_spans**: per-endgame-class WDL timeline |
| 16,053 | 16,053 | 1 | 16,053 | clock_raw CTE |
| 14,676 | 14,676 | 1 | 14,676 | clock_raw CTE variant |
| 14,373 | 14,373 | 1 | 14,373 | clock_raw CTE variant |
| 14,282 | 264,413 | 53 | 756,954 | `count(*) FROM games WHERE user_id … AND id IN (endgame subquery)` |
| 12,901 | 227,192 | 48 | 619,259 | **games list fetch** — full-row SELECT on games |

### Highest total execution time

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 2,470,931 | 58 | 42,602 | clock_per_game join (dominant) |
| 1,745,302 | 53 | 32,930 | endgame span + imbalance rollup |
| 1,172,200 | 62 | 18,906 | per_class_spans endgame WDL timeline |
| 756,954 | 53 | 14,282 | count endgame games |
| 716,511 | 61 | 11,746 | endgame played_at+result rollup |
| 622,361 | 52 | 11,968 | endgame games count via subselect |
| 619,259 | 48 | 12,901 | full games SELECT |
| 291,642 | 53 | 5,502 | entry/after endgame imbalance rollup |
| 105,882 | 1,300 | 81 | INSERT INTO game_positions (write path) |
| 35,767 | 6,421,486 | 0.01 | `SELECT … FROM users WHERE id = … FOR KEY SHARE` (FK lock probe, benign) |

### Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---|---|---|---|
| game_positions | 17 | 138,416,744 | 20.6 M | Healthy — index-driven |
| games | 11 | 14,217,452 | 305 k | Healthy — index-driven |
| users | 3,262,925 | 74 | 52 | **Expected** — 52-row table; planner correctly prefers seq scan. Most seq scans are FK constraint probes from INSERTs (6.4 M `FOR KEY SHARE` calls). |
| openings | 196 | 0 | 0 (stats stale) | Tiny static table, fine |
| import_jobs | 3,495 | 26 | 76 | Fine — small table |
| oauth_account | 2,432 | 0 | 4 | Fine — 4 rows |
| position_bookmarks | 122 | 0 | 4 | Fine — 4 rows |

### Index usage

**Truly unused & worth considering to drop:** none. All indexes listed as 0-scan either protect FK integrity, enforce uniqueness (`uq_openings_eco_name_pgn`, `oauth_account_*`), or back very small tables where the planner doesn't need them yet. `ix_users_email` is used by FastAPI-Users login path but may not have been exercised since last server restart.

**Index-size vs. usage mismatch on `game_positions`:**
- `ix_gp_user_full_hash_move_san` (1,139 MB) — 6,005 scans, heavy column reads. Pulls its weight for move-explorer candidate-move breakdowns.
- `ix_gp_user_full_hash` (873 MB) — only 1,834 scans total. Possibly redundant vs. the full+move_san composite above, but it leads with the same columns so both get used in different query shapes. Worth an EXPLAIN check in a future cleanup phase.
- `ix_gp_user_white_hash` (665 MB) — **143 scans**. Under-used for its size — likely tied to the "system opening" (white-only) filter. Keep for now, re-check after more system-opening traffic.
- `ix_gp_user_black_hash` (660 MB) — **54 scans**. Even lower. Same story as white_hash (black-only filter). Keep for feature parity.
- `ix_gp_user_endgame_game` (235 MB) — **129.6 M scans, 40 B tuples read**. The hottest index in the DB; absolutely pulling its weight.
- `game_positions_pkey` (482 MB) — 0 scans. Can't drop (PK), but confirms nothing in the codebase looks up positions by their surrogate id.

### Dead tuples / autovacuum

| Table | Live | Dead | Dead % | Last autovac | Last autoanalyze |
|---|---|---|---|---|---|
| game_positions | 20.59 M | 545 k | 2.6% | 2026-04-20 | 2026-04-21 |
| games | 305 k | 19 k | 6.3% | 2026-04-21 | 2026-04-21 |
| users | 52 | 17 | 33% | 2026-04-21 | 2026-04-19 |
| import_jobs | 76 | 388 | 510% | 2026-04-21 | 2026-04-21 |

- `import_jobs` dead-tuple ratio is dramatic in relative terms but absolute size is trivial (a few KB). Not a concern.
- `users` has 33% dead — again, 17 dead rows on a 52-row table is fine.
- `game_positions` and `games` dead ratios are healthy; autovacuum running regularly.

### EXPLAIN ANALYZE

Queries in the 30–40 s range are all endgame CTE variants with `first_endgame` that scan `game_positions WHERE endgame_class IS NOT NULL GROUP BY game_id`. The slow bits are per-user rollups that scale linearly with the user's position count (millions for the largest users). These are end-user analytics queries that already use `ix_gp_user_endgame_game` and `ix_gp_user_endgame_class`. Not running EXPLAIN ANALYZE inline — the queries require specific user_ids and the cumulative stats include pre-optimization runs, so a single plan wouldn't give a full picture.

### Recommendations

**No action needed**
- Cache hit ratio 99.65% — disk I/O is not the bottleneck.
- `users` table seq scans: expected and optimal for a 52-row table.
- Dead-tuple ratios on `game_positions` and `games`: autovacuum is keeping up.

**Monitor**
- `ix_gp_user_black_hash` (660 MB, 54 scans) and `ix_gp_user_white_hash` (665 MB, 143 scans): low usage per MB. These back "my pieces only" / system-opening filters. Revisit after more system-opening traffic accumulates. Dropping one would reclaim ~660 MB but break the feature.
- `ix_gp_user_full_hash` (873 MB) vs. `ix_gp_user_full_hash_move_san` (1,139 MB): possible redundancy. Candidate for a future consolidation phase — check with EXPLAIN whether the (user, full_hash) prefix of the composite index serves the same queries.
- Consider resetting pg_stat_statements (`SELECT pg_stat_statements_reset()`) so the next report reflects only current query behavior — cumulative stats are polluted by any pre-optimization runs. Same for `pg_stat_database` (`stats_reset` is null, cumulative since server start).

**Recommended**
- **Endgame CTE family is the hot path**: the top 8 by total execution time are all endgame span / imbalance / WDL-timeline queries, collectively consuming ~5.7 M ms. For users with 1M+ positions these regularly exceed 30 s. Phase-level optimization target: either precompute per-game endgame-span rows into a materialized table (one row per (game_id, endgame_class)) or add a partial index `(user_id, game_id) WHERE endgame_class IS NOT NULL`. A GSD phase dedicated to endgame query perf would pay off — this is where users experience slowness.
- The `clock_per_game` join (2.47 M ms total, 42.6 s avg) is the single biggest time sink. Same fix class: precompute per-game clock arrays at import time rather than aggregating on read.

**Consider**
- With 52 users and 20.6 M positions, the DB is on track to cross 10 GB within the next few imports of heavy users. Monitor disk usage on the server (75 GB NVMe, plenty of headroom, but plan for v2 partitioning of `game_positions` by user_id).

## Summary

- **Database**: 7.74 GB total. `game_positions` is 88% of it (6.84 GB), and its indexes (4.28 GB) outweigh the row data (2.56 GB) by 1.67x — expected for a Zobrist-hash position store.
- **Users**: 52 total (38 registered, 14 guest). Recent signup-to-import conversion is decent (6/10 of latest signups imported games); guests contribute some of the largest datasets.
- **Cache hit ratio 99.65%** and `game_positions` runs on indexes (17 seq scans vs. 138 M index scans). Infrastructure is healthy.
- **Main pain point**: endgame CTE queries. Eight distinct endgame/clock analytics queries with 18–42 s average times dominate total server time (~5.7 M ms combined). Most likely optimization: precompute per-game endgame spans and clock arrays at import time rather than aggregating across millions of positions on every read.
- **No indexes need dropping**. Two large user+hash indexes (white/black, ~1.3 GB combined) are under-scanned, but they back feature functionality; revisit after more system-opening traffic.
- Consider `pg_stat_statements_reset()` before the next perf report so averages reflect current code, not pre-optimization history.
