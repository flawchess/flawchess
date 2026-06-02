# FlawChess DB Report — 2026-06-01

- **DB**: prod
- **Snapshot taken**: 2026-06-01T17:13:14Z
- **Sections run**: users / storage / performance
- **pg_stat_statements last reset**: 2026-05-29T07:43:49Z (~3 days of cumulative stats)

## 0. Users Overview

### User summary

| Total users | Registered | Guest |
|---|---|---|
| 110 | 56 | 54 |

### 10 most recent users

| ID | chess.com | lichess | Guest | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 150 | ✅ | — | ✅ | 2026-06-01 | 2026-06-01 | 241 | 12,903 |
| 149 | ✅ | — | ✅ | 2026-06-01 | 2026-06-01 | 628 | 45,248 |
| 148 | ✅ | — | ✅ | 2026-05-31 | 2026-05-31 | 28 | 1,874 |
| 147 | ✅ | — | — | 2026-05-31 | 2026-05-31 | 5,025 | 337,963 |
| 146 | ✅ | — | — | 2026-05-30 | 2026-05-30 | 41 | 2,514 |
| 145 | ✅ | ✅ | ✅ | 2026-05-29 | 2026-05-29 | 13 | 731 |
| 144 | ✅ | — | — | 2026-05-27 | 2026-05-27 | 76 | 4,458 |
| 143 | ✅ | — | ✅ | 2026-05-27 | 2026-05-27 | 35 | 2,339 |
| 142 | ✅ | — | ✅ | 2026-05-26 | 2026-05-26 | 204 | 12,593 |
| 109 | ✅ | ✅ | — | 2026-05-26 | 2026-05-26 | 12,443 | 1,027,667 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 66 | 306,311 |
| lichess | 50 | 192,189 |

**Activity note:** 110 total users, a near-even registered/guest split (56/54). All 10 most recent signups imported games, so the import funnel is healthy at the top. chess.com dominates (≈61% of games, 66 of the platform-linked users) vs lichess (≈39%). Only 2 of the recent 10 linked both platforms. A couple of heavy users skew volume hard: user 109 alone holds ~1.03M positions and 12.4k games, and user 147 another 338k positions — together roughly 4% of all games but a sizable share of storage.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 9,861 MB (≈9.6 GB) |
| Total games | 498,500 |
| Total positions | 36,571,741 |
| Avg positions / game | ≈73.4 |

### Per-table breakdown

| Table | Data size | Index size | Total size |
|---|---|---|---|
| game_positions | 4,671 MB | 3,713 MB | 8,384 MB |
| games | 1,275 MB | 178 MB | 1,452 MB |
| benchmark_cohort_cdf | 8,184 kB | 4,784 kB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 16 kB | 640 kB | 656 kB |
| import_jobs | 40 kB | 408 kB | 448 kB |
| user_benchmark_percentiles | 112 kB | 96 kB | 208 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| users | 32 kB | 64 kB | 96 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,300 MB |
| ix_gp_user_endgame_game | game_positions | 622 MB |
| ix_gp_user_game_ply | game_positions | 511 MB |
| ix_game_positions_game_id | game_positions | 452 MB |
| ix_gp_user_full_hash_move_san | game_positions | 401 MB |
| ix_gp_user_white_hash | game_positions | 213 MB |
| ix_gp_user_black_hash | game_positions | 212 MB |
| uq_games_user_platform_game_id | games | 55 MB |
| games_pkey | games | 23 MB |
| ix_games_user_id | games | 12 MB |
| ix_games_evals_pending | games | 9,640 kB |
| benchmark_cohort_cdf_pkey | benchmark_cohort_cdf | 3,752 kB |

**Storage summary:** `game_positions` is the whole story — 8,384 MB (85% of the DB). Its indexes alone (3,713 MB) nearly match its 4,671 MB of data, a 0.79 index-to-data ratio driven by seven indexes including six hash/lookup indexes over 200 MB each. The PK (1.3 GB) and `ix_gp_user_endgame_game` (622 MB) are the two largest objects in the database. `games` is a distant second at 1.45 GB. Everything else is rounding error (<13 MB combined). Index bloat on `game_positions` is the single biggest lever on total DB size — see the unused-index note in Section 2.

## 2. Performance Analysis

### Buffer cache hit ratio

**98.50%** — good (just under the >99% "excellent" line). The slight dip is expected for this window: stats were reset only 3 days ago, and a `VACUUM ANALYZE game_positions` plus several `CREATE INDEX CONCURRENTLY` builds ran since the reset, all reading cold pages from disk on an 8 GB table and depressing the cumulative ratio. Not a concern.

### Slowest queries by avg time

| avg_ms | max_ms | calls | total_ms | Query |
|---|---|---|---|---|
| 14,645 | 14,814 | 8 | 117,162 | Opening explorer: `openings_dedup` join with `count(distinct games.id)` WDL aggregation |
| 12,170 | 12,170 | 1 | 12,170 | Endgame insights: `bucket_with_next` endgame-class WDL/eval pull |
| 7,685 | 7,685 | 1 | 7,685 | Bookmark-past-cap count (`NOT EXISTS` over hash match, ply ≤ N) |
| 7,011 | 7,011 | 1 | 7,011 | Endgame `span_with_next` WDL/eval pull |
| 4,523 | 4,523 | 1 | 4,523 | Endgame game count (`IN (SELECT … endgame_class IS NOT NULL)`) |
| 4,306 | 4,306 | 1 | 4,306 | Bookmark depth CTE (`bm_depth` MIN(ply) join) |

(Excludes one-off maintenance ops — `VACUUM ANALYZE`, `CREATE INDEX CONCURRENTLY` — which legitimately run 9–15 s.)

The **opening explorer** query is the clear outlier: 14.6 s average across 8 real calls (117 s total). This is the user-facing position/WDL aggregation and the top single-query latency target. The single-call endgame queries (7–12 s) likely reflect the heaviest user (109, ~1M positions) and may be acceptable tail latency, but the opening explorer is hit repeatedly and should be profiled.

### Highest total server time

| total_ms | calls | avg_ms | rows | Query |
|---|---|---|---|---|
| 451,094 | 329 | 1,371 | 295 | `recent_capped` WDL-by-position CTE (variant A) |
| 169,027 | 987 | 171 | 691 | `recent_capped` WDL-by-position CTE (variant B) |
| 147,759 | 329 | 449 | 226 | `recent_capped` CTE (variant C) |
| 135,513 | 329 | 412 | 295 | `recent_capped` CTE (variant D) |
| 117,162 | 8 | 14,645 | 80 | Opening explorer (also slowest by avg) |
| 65,565 | 1,458 | 45 | 13 | Eval-pending / import-status existence check |
| 62,215 | 1,045 | 60 | 1.08M | `COPY game_positions` (bulk import path) |
| 38,699 | 335 | 116 | 286 | `recent_capped` CTE (variant E) |

The **`recent_capped` WDL-by-position CTE family** dominates total server time: the top four variants alone burn ~903 s, and the full family adds several more variants (109–116 ms each). This is the core "WDL for the current board position over recent games" workload behind the opening explorer / insights, run with different filter combinations. Variant A at 1.37 s × 329 calls is the biggest aggregate cost in the database. Optimizing this CTE shape (it appears 10+ times with slightly different params) would have the largest fleet-wide impact.

### Sequential scan analysis

| Table | seq_scan | idx_scan | live rows | Verdict |
|---|---|---|---|---|
| import_jobs | 2,232,434 | 36 | 198 | OK — tiny table, optimizer correctly prefers seq scan |
| users | 1,143,794 | 5 | 110 | OK — tiny table, seq scan is cheapest |
| game_positions | 40 | 270,633,682 | 36.5M | Excellent — virtually all index-driven |
| games | 78 | 9,303,077 | 499k | Excellent — index-driven |
| openings | 189 | 0 | 0 | OK — empty/seed table, full scans trivial |
| oauth_account | 5,732 | 0 | 2 | OK — 2 rows |

No problem scans. The high seq_scan counts on `import_jobs` and `users` are PostgreSQL correctly choosing full scans on sub-200-row tables — index lookups would be slower. The big tables (`game_positions`, `games`) are almost entirely index-served (40 and 78 lifetime seq scans respectively). The 946M `seq_tup_read` on `game_positions` comes from those 40 full scans (maintenance + a few analytical queries), not a hot path.

### Index usage — unused indexes

Three large `game_positions` indexes show **0 scans** since the 2026-05-29 stats reset:

| Index | Size | Scans (3 days) | Recommendation |
|---|---|---|---|
| ix_gp_user_full_hash_move_san | 401 MB | 0 | **Monitor** — likely serves opening-explorer hash+SAN lookups not exercised in this window |
| ix_gp_user_white_hash | 213 MB | 0 | **Monitor** — "my white pieces only" system-opening queries |
| ix_gp_user_black_hash | 213 MB | 0 | **Monitor** — "my black pieces only" queries |

That is ~827 MB of indexes idle for 3 days. **Do not drop yet** — the stats window is short (3 days) and these back specific, intermittently-used query paths (system-opening color filters, exact-position SAN lookups). Re-check after a fuller week of traffic before considering any drop. All other zero-scan indexes are PKs, unique/FK, or auth/OAuth indexes (`ix_users_email`, `oauth_account_*`, `import_jobs_pkey`, `llm_logs_*`) and must be **kept** regardless of scan count.

Note: the `*_partial` (`WHERE ply <= 28`) indexes seen in `pg_stat_statements` `CREATE INDEX CONCURRENTLY` history do **not** currently exist — they were one-off build operations since dropped, not live objects.

### Dead tuples / autovacuum

| Table | live | dead | dead % | Last autoanalyze |
|---|---|---|---|---|
| games | 499,428 | 59,374 | 11.9% | 2026-05-29 |
| game_positions | 36,512,717 | 720,589 | 2.0% | 2026-05-29 |
| users | 110 | 39 | 26% | 2026-05-31 |
| import_jobs | 198 | 51 | 20% | 2026-05-31 |

No action needed. `games` at 11.9% and `game_positions` at 2.0% are well under the 20% concern line. `users` (26%) and `import_jobs` (20%) are high *ratio* but trivial *absolute* (39 and 51 dead rows) — autovacuum reasonably ignores tables this small; a single scan reclaims them. `last_autovacuum` is null on the big tables only because the row-churn threshold hasn't been crossed; autoanalyze is running and current.

## Summary

- **Size:** 9.6 GB total, and `game_positions` is 85% of it (8.4 GB). Its indexes (3.7 GB) almost equal its data — the PK (1.3 GB) and `ix_gp_user_endgame_game` (622 MB) are the two biggest objects. 498k games, 36.6M positions, ~73 positions/game.
- **Users:** 110 (56 registered / 54 guest). chess.com leads lichess ~61/39 by game volume. Two power users (109, 147) hold a disproportionate share of storage. Recent-signup import funnel is healthy.
- **Cache hit 98.5%** — fine; slightly under 99% only because of post-reset cold reads from a VACUUM + index builds in the 3-day window.
- **Top latency target:** the **opening explorer** query at 14.6 s avg (8 calls). **Top total-time target:** the **`recent_capped` WDL-by-position CTE family** (~900+ s aggregate across 10+ variants) — the dominant server-time consumer and the highest-leverage optimization.
- **~827 MB of `game_positions` hash indexes idle 3 days** (`full_hash_move_san`, `white_hash`, `black_hash`) — flagged **Monitor, not drop**; the window is too short and they back intermittent color/SAN query paths. Re-check after a fuller week.
- **Eval backfill fully caught up** (0 games pending eval).
- **No vacuum/scan red flags.** Dead-tuple ratios healthy; large-table access is essentially 100% index-driven.

**Recommended next steps:**
- **Recommended:** profile the opening-explorer / `recent_capped` CTE with `EXPLAIN (ANALYZE, BUFFERS)` against the heaviest user (e.g. user 109) — one query shape drives both the worst per-call latency and the largest total cost.
- **Monitor:** revisit the three zero-scan hash indexes after ~1 week of post-reset traffic before deciding on any drop; ~827 MB is recoverable if they stay idle.
- **Monitor:** cumulative stats are only 3 days old and skewed by maintenance ops. Consider re-running this report in a week for a cleaner steady-state picture.
