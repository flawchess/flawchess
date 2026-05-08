# FlawChess DB Report — 2026-05-08

- **DB**: prod
- **Snapshot taken**: 2026-05-08T14:00:00Z
- **Sections run**: users / storage / performance
- **pg_stat_statements reset**: 2026-05-03T13:43:09Z (~5 days of data)

---

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---:|---:|---:|
| 66 | 42 | 24 |

### 10 most recent users (by created_at)

| ID | chess.com? | lichess? | Guest? | Registered | Last login | Games | Positions |
|---:|:---:|:---:|:---:|:---|:---|---:|---:|
| 73 | yes | yes | yes | 2026-05-03 | 2026-05-03 | 0 | 0 |
| 72 | yes | no  | yes | 2026-05-01 | 2026-05-01 | 4,796 | 415,700 |
| 71 | yes | no  | no  | 2026-04-30 | 2026-04-30 | 2,483 | 152,626 |
| 70 | no  | yes | yes | 2026-04-28 | 2026-04-28 | 2,313 | 173,979 |
| 69 | no  | no  | no  | 2026-04-28 | 2026-04-28 | 0 | 0 |
| 68 | yes | no  | yes | 2026-04-27 | 2026-04-27 | 12,517 | 883,366 |
| 67 | no  | yes | no  | 2026-04-27 | 2026-04-27 | 130 | 8,904 |
| 66 | yes | no  | no  | 2026-04-26 | 2026-04-26 | 8,712 | 570,640 |
| 65 | yes | no  | yes | 2026-04-25 | 2026-04-25 | 0 | 0 |
| 64 | yes | no  | yes | 2026-04-24 | 2026-04-24 | 0 | 0 |

### Platform breakdown

| Platform | Users | Games |
|---|---:|---:|
| chess.com | 38 | 210,299 |
| lichess | 26 | 109,800 |

### Notes on user activity

- **Activation rate among recent 10:** 6 of 10 actually imported games. The other 4 linked at least one platform but never completed an import — worth checking whether something is failing in the import flow for those, or whether they bounced at a step before kicking it off.
- User 69 is unusual: registered (not guest), no platform linked, no games. Likely abandoned signup.
- **Guest dominance in recent signups:** 6 of the last 10 created accounts are guests, including ones that imported real volume (12.5k / 4.8k games). Guests are clearly being used as a real exploration path, not just throwaway accounts.
- chess.com still ahead of lichess ~2:1 in both users and games.

---

## 1. Storage Report

### Overview

| Metric | Value |
|---|---:|
| Database size | **10,103 MB** (~10.1 GB) |
| Total games | 320,099 |
| Total positions | 22,888,052 |
| Avg positions per game | ~71.5 |

### Per-table breakdown

| Table | Data | Indexes | Total |
|---|---:|---:|---:|
| **game_positions** | 3,659 MB | 5,792 MB | **9,451 MB** |
| games | 568 MB | 73 MB | 641 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 8 kB | 344 kB | 352 kB |
| import_jobs | 32 kB | 240 kB | 272 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| position_bookmarks | 16 kB | 64 kB | 80 kB |
| users | 16 kB | 64 kB | 80 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top 10)

| Index | Table | Size |
|---|---|---:|
| ix_gp_user_full_hash_move_san | game_positions | 1,577 MB |
| game_positions_pkey | game_positions | 1,005 MB |
| ix_gp_user_white_hash | game_positions | 927 MB |
| ix_gp_user_black_hash | game_positions | 924 MB |
| ix_gp_user_game_ply | game_positions | 681 MB |
| ix_game_positions_game_id | game_positions | 358 MB |
| ix_gp_user_endgame_game | game_positions | 318 MB |
| uq_games_user_platform_game_id | games | 21 MB |
| games_pkey | games | 8 MB |
| ix_games_user_id | games | 3 MB |

### Storage observations

- `game_positions` is **93%** of the database. Indexes on this table are **5.79 GB** — 1.58× the table data itself. This is by design (multi-column user-scoped indexes are how Zobrist matching gets sub-ms lookups), but it makes the table the only thing that matters for sizing.
- Average positions per game (~71.5) is consistent with prior reports.
- Everything outside `game_positions` and `games` is < 2 MB combined. No drift to chase there.

---

## 2. Performance Analysis

### Buffer cache hit ratio

**97.29 %** — *Good*, but on the lower edge of healthy. Aiming for >99% means the working set comfortably fits in shared_buffers; 95–99% means you're paying disk reads for some cold lookups.

Stats were reset 2026-05-03 (~5 days), so this reflects current behavior including cold reads after restart, not legacy noise.

### Slowest queries by avg time (top 8 worth attention)

| avg ms | max ms | calls | total ms | rows | What |
|---:|---:|---:|---:|---:|---|
| 3,729 | 3,729 | 1 | 3,729 | 10 | *(this report — recent users + games + positions JOIN)* |
| 3,684 | 3,684 | 1 | 3,684 | 6,584 | endgame clock-array aggregation (one-off) |
| 1,816 | 1,816 | 1 | 1,816 | 1 | `count(*) FROM game_positions` (this report) |
| 967 | 967 | 1 | 967 | 2 | platform breakdown (this report) |
| **519** | 3,034 | **20** | 10,377 | 3,409 | openings transitions CTE (insights) |
| **448** | 2,483 | **138** | **61,823** | 31,548 | openings transitions CTE (insights) — **dominant cost** |
| 290 | 428 | 4 | 1,158 | 174 | openings transitions CTE (smaller variant) |
| 271 | 3,781 | 29 | 7,861 | 98,507 | endgame clock-array aggregation |

The top 4 are one-shot diagnostic queries from this report itself — ignore. Real production hotspot is the **openings transitions CTE** family (rows 5–7, all the same query shape).

### Highest total time queries — server-time hogs

| total ms | calls | avg ms | rows | What |
|---:|---:|---:|---:|---|
| **61,823** | 138 | 448 | 31,548 | openings transitions CTE |
| **56,896** | 235 | 242 | 1,492 | openings move/result counts (full_hash) |
| 43,184 | 391 | 110 | 3,879 | openings dedup CTE |
| 26,845 | 262 | 102 | 2,620 | openings_dedup ECO/name aggregate |
| 12,018 | 466 | 26 | 466 | WDL count over dedup |
| 10,377 | 20 | 519 | 3,409 | openings transitions CTE (variant) |
| 7,861 | 29 | 271 | 98,507 | endgame clock-array aggregation |
| 7,136 | 59 | 121 | 59 | dedup full_hash WDL |

Opening Insights and the explorer dominate ~80% of the total time budget. The endgame clock-array aggregation is the only non-openings query on the heavy list.

### Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---:|---:|---:|---|
| game_positions | 48 | 3,049,554 | 22.9M | ✅ index-driven |
| games | 33 | 32,031,520 | 771* | ✅ index-driven |
| **users** | **57,773** | 4 | 66 | ✅ tiny table — planner correctly uses seq scan |
| openings | 434 | 0 | 0* | ⚠️ stats stale (table actually has data) |
| oauth_account | 2,139 | 0 | 0 | ✅ tiny |
| import_jobs | 417 | 0 | 8 | ✅ tiny |
| position_bookmarks | 133 | 0 | 0 | ✅ tiny |

*The `n_live_tup = 771` for `games` and `0` for `openings` is stats-collector lag — `last_autoanalyze` is null on most tables. Worth running `ANALYZE` (see recommendations).

### Index usage

**Hot:** `games_pkey` (32M scans), `ix_game_positions_game_id` (1.1M), `ix_gp_user_game_ply` (993k), `ix_gp_user_full_hash_move_san` (901k), `ix_gp_user_endgame_game` (12k).

**Cold but light (negligible size, keep):** all `llm_logs` indexes, `oauth_account` indexes, `users.ix_users_email`, `position_bookmarks`, `import_jobs.ix_import_jobs_user_id`. These are < 16 kB each — no point dropping them, and most are required for FK / OAuth flows or new feature paths still warming up.

**Cold + huge (worth questioning):**
- `ix_gp_user_white_hash` (927 MB, 167 scans)
- `ix_gp_user_black_hash` (924 MB, 275 scans)

→ Combined ~1.85 GB for ~440 scans across 5 days. These power the **System Opening Filter** ("user's pieces only"). Low scan count is consistent with that being a niche filter, not a sign the index is unused. **Keep**, but worth tracking — if it stays under ~10 scans/day for a quarter, the cost-benefit may flip.

### Dead tuples / autovacuum

| Table | live | dead | dead % | last_autovacuum |
|---|---:|---:|---:|---|
| game_positions | 22,886,746 | 470 | <0.01% | never |
| games | 771* | 713 | n/a | never |
| users | 66 | 4 | 6% | never |
| import_jobs | 8 | 37 | n/a | never |

`last_autovacuum` is **null on every table.** Either autovacuum has genuinely never fired since the stats reset (likely — only 5 days of data, and dead-tuple ratios are low so the threshold hasn't been hit), or it's running but not getting recorded. Either way, no action needed *yet* — but worth re-checking next week.

### Recommendations

**No action needed**
- Storage growth is dominated by `game_positions`, which is the product. Indexes are large by design.
- Most `seq_scan` counts are on tables small enough that the planner correctly avoids the index.
- Cold `llm_logs` / `oauth_account` indexes are < 16 kB each — not worth dropping.

**Monitor**
- **Cache hit ratio at 97.29%.** Watch over the next week. If it drops below 95% under load, consider `shared_buffers` tuning or a memory bump (server has 7.6 GB; PostgreSQL default `shared_buffers` is 25% of RAM ≈ 1.9 GB, while hot indexes alone are ~5 GB).
- `ix_gp_user_white_hash` and `ix_gp_user_black_hash` (~1.85 GB combined) — System Opening Filter usage is low. Check again at the next milestone boundary; if scan count is still under ~50/week, evaluate dropping or making them partial.

**Recommended**
- **Run `ANALYZE` across all tables.** Stats-collector data is stale (`last_autoanalyze` null on most, `games.n_live_tup = 771` is wrong — actual count is 320k). Affects query planner choices.
  ```sql
  ANALYZE; -- runs across all tables, fast
  ```
- **Top hotspot is the Opening Insights transitions CTE** — 448 ms × 138 calls = 62 s of server time over 5 days, ~25% of measured workload. Already known territory; an `EXPLAIN (ANALYZE, BUFFERS)` after the `ANALYZE` above would show whether the plan is still optimal post-stats-refresh, before any index work.

**Consider**
- Reset `pg_stat_statements` after running `ANALYZE`, then re-snapshot in 1 week for a clean baseline reflecting current data + plans:
  ```sql
  SELECT pg_stat_statements_reset();
  ```

---

## Summary

- **DB at 10.1 GB**, dominated by `game_positions` (9.4 GB / 93%) — 22.9M positions across 320k games, ~71.5 positions/game. Indexes on that one table are 5.8 GB.
- **66 users (42 registered, 24 guest); chess.com 2:1 over lichess.** 4 of the last 10 signups linked accounts but never imported — likely a funnel drop-off worth investigating.
- **Cache hit 97.29 %** — borderline-good, watch it. Hot indexes already exceed default `shared_buffers`.
- **Performance hotspot: Opening Insights transitions CTE** — ~62 s / 5 days of server time across 138 calls. Single biggest target if optimization budget is available.
- **Stats are stale.** `last_autoanalyze` is null on most tables and `games.n_live_tup` is wrong. Run `ANALYZE` to refresh planner stats before any further perf work.
- No alarming dead-tuple buildup; no large unused indexes worth dropping today.
