# FlawChess DB Report — 2026-06-10

- **DB**: prod
- **Snapshot taken**: 2026-06-10T13:31:02Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 129 | 64 | 65 |

### 10 most recent users

| User ID | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 169 | no | yes | yes | 2026-06-10 | 2026-06-10 | 1,102 | 87,943 |
| 168 | yes | no | no | 2026-06-09 | 2026-06-09 | 1,056 | 69,619 |
| 167 | yes | no | yes | 2026-06-09 | 2026-06-09 | 55,699 | 4,867,017 |
| 166 | yes | yes | yes | 2026-06-08 | 2026-06-08 | 6,777 | 444,306 |
| 165 | yes | no | no | 2026-06-07 | 2026-06-07 | 595 | 42,517 |
| 164 | yes | no | yes | 2026-06-07 | 2026-06-07 | 985 | 72,975 |
| 163 | yes | no | yes | 2026-06-07 | 2026-06-07 | 3,712 | 261,454 |
| 162 | yes | no | no | 2026-06-06 | 2026-06-06 | 4,225 | 273,203 |
| 161 | yes | yes | no | 2026-06-05 | 2026-06-05 | 1,706 | 100,613 |
| 160 | no | yes | yes | 2026-06-04 | 2026-06-04 | 396 | 23,587 |

### Platform breakdown (all users)

| Platform | Users | Games |
|---|---|---|
| chess.com | 80 | 380,015 |
| lichess | 56 | 210,021 |

**Activity note:** All 10 most recent signups imported games — onboarding-to-import conversion looks healthy. The split is near-even (64 registered / 65 guests), and guests are importing real volume rather than bouncing. One guest (user 167) imported 55,699 games / 4.87M positions in a single session — roughly 11% of the entire DB's positions sit under one guest account. chess.com dominates both user count and game volume (~64% of games). Some users appear on both platforms, so platform user counts (80 + 56) exceed the 129 total.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 10,116 MB (~9.9 GB) |
| Total games | 590,036 |
| Total positions | 43,910,219 |
| Avg positions / game | ~74.4 |

### Per-table breakdown

| Table | Data size | Index size | Total size |
|---|---|---|---|
| game_positions | 5,405 MB | 3,248 MB | 8,653 MB |
| games | 1,275 MB | 163 MB | 1,438 MB |
| benchmark_cohort_cdf | 8.2 MB | 4.8 MB | 13 MB |
| openings | 832 kB | 888 kB | 1.7 MB |
| llm_logs | 24 kB | 752 kB | 776 kB |
| import_jobs | 48 kB | 408 kB | 456 kB |
| user_benchmark_percentiles | 152 kB | 104 kB | 256 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| users | 40 kB | 64 kB | 104 kB |
| oauth_account | 24 kB | 80 kB | 104 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,321 MB |
| ix_gp_user_endgame_game | game_positions | 614 MB |
| ix_gp_user_full_hash_move_san | game_positions | 493 MB |
| ix_game_positions_game_id | game_positions | 295 MB |
| ix_gp_user_white_hash | game_positions | 263 MB |
| ix_gp_user_black_hash | game_positions | 261 MB |
| uq_games_user_platform_game_id | games | 40 MB |
| games_pkey | games | 15 MB |
| ix_games_user_id | games | 5.6 MB |
| benchmark_cohort_cdf_pkey | benchmark_cohort_cdf | 3.7 MB |
| ix_games_evals_pending | games | 2.5 MB |

(All other indexes are ≤1 MB.)

**Storage summary:** `game_positions` is the whole story — 8,653 MB (86%) of the 9.9 GB DB, with `games` a distant second at 1,438 MB. Everything else combined is under 16 MB. The 5 secondary indexes on `game_positions` total ~1.93 GB on top of a 1.32 GB primary key, so indexes are ~60% of the table's own data size — an expected cost of supporting white/black/full-hash position matching plus the endgame and full_hash+move_san lookups. No bloat or runaway index here; growth is purely a function of imported positions (~74 per game).

## 2. Performance Analysis

> Cumulative stats since last reset: **2026-06-05T07:22:51Z** (~5 days). pg_stat_statements is installed and active.

### Buffer cache hit ratio

**98.72%** — good (in the 95–99% band, just shy of "excellent"). Reasonable for a 9.9 GB DB on a 16 GB host where the 8.6 GB `game_positions` table can't fully fit in cache alongside everything else. Not a concern; the occasional read miss is expected when scanning across many users' positions.

### Slowest queries by avg time

Most of the very-slow entries are **one-off** calls (`calls = 1`) — maintenance and ad-hoc work (this very report's queries, `VACUUM ANALYZE`, a count over `games`). The only recurring slow query that matters:

| avg_ms | max_ms | calls | total_ms | Query |
|---|---|---|---|---|
| 747.74 | 4,769.97 | 126 | 94,215 | Openings explorer aggregation (`openings_dedup` … `count(distinct games.id)` per candidate move) |
| 736.96 | 3,393.64 | 32 | 23,583 | Endgame/insights CTE (`selected_users` → `recent_capped` windowed recent-games cap) |
| 270.82 | 1,698.68 | 22 | 5,958 | Openings explorer aggregation (smaller variant) |

One-off entries excluded as noise: the two `games` full-row selects (9.3 s / 9.1 s, 1 call each), `VACUUM ANALYZE game_positions` (8.6 s), the endgame eval pull (6.6 s, 1 call), and the per-game clock-coverage CTE (3.0 s, 1 call).

### Highest total-time queries (server-time dominators)

| total_ms | calls | avg_ms | Query |
|---|---|---|---|
| 300,666 | 5,017 | 59.93 | `COPY game_positions(...)` — bulk import path (6.2M rows) |
| 186,874 | 7,053 | 26.50 | Import-job "pending evals" guard (`games … evals_completed_at IS NULL` + `import_jobs` status) |
| 137,733 | 12,678,300 | 0.01 | `SELECT … FROM users WHERE id = $1 FOR KEY SHARE` — FK lock on every game/position insert |
| 94,215 | 126 | 747.74 | Openings explorer aggregation (the recurring slow query above) |
| 29,845 | 87,885 | 0.34 | `UPDATE game_positions SET eval_cp/eval_mate …` (with endgame_class) |
| 27,339 | 70,118 | 0.39 | `UPDATE game_positions SET eval_cp/eval_mate …` (without endgame_class) |
| 23,583 | 32 | 736.96 | Endgame insights recent-games CTE |
| 23,301 | 98,073 | 0.24 | `SELECT games.id WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT` |

The top three are import/eval machinery, not user-facing reads: `COPY` (bulk insert), the pending-evals poller, and the per-row FK lock on `users`. They dominate total server time because of call volume during the recent large imports (user 167's 4.9M positions, etc.), not because any single call is slow.

### Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---|---|---|---|
| users | 6,459,686 | 1 | 129 | **Expected** — 129-row table; planner correctly prefers seq scan. Driven by the 12.7M `FOR KEY SHARE` FK checks on inserts. No action. |
| game_positions | 15 | 67,041,425 | 43.9M | Healthy — virtually all index access. |
| games | 18 | 18,186,119 | 588k | Healthy — virtually all index access. |
| openings | 281 | 0 | 3,641 | Small table, seq-scanned. `ix_openings_eco_name` unused. Tolerable at 3.6k rows. |
| import_jobs | 1,588 | 2,497,259 | 234 | Mostly indexed; tiny table. Fine. |
| oauth_account | 3,719 | 0 | 4 | 4-row table; seq scan is optimal. Fine. |

The `users` seq-scan count looks alarming but is benign: at 129 rows PostgreSQL always picks a seq scan over the PK, and each game/position insert does a `FOR KEY SHARE` referential check. 793M tuples read = 6.46M scans × ~129 rows. Zero action needed.

### Index usage

**Genuinely unused (0 scans):**
- `ix_openings_eco_name` (264 kB), `uq_openings_eco_name_pgn` (488 kB), `openings_pkey` (96 kB) — openings are seq-scanned; **keep** `uq_*` (natural-key uniqueness) and `_pkey`. `ix_openings_eco_name` could theoretically be dropped, but at 264 kB it's not worth the migration.
- All 6 `llm_logs` indexes (16 kB each) — table has 6 rows; **keep**, they'll matter as logs grow.
- Both `oauth_account` secondary indexes + `ix_users_email` (16 kB each) — **keep**, required for OAuth/auth lookups even if not exercised in this 5-day window.
- `benchmark_cohort_cdf_pkey`, `bookmarks_pkey`, `alembic_version_pkc` — **keep** (PKs / migration bookkeeping).

No large unused index exists. Nothing worth dropping — the only candidates are sub-500 kB and several are required for integrity or auth. The big `game_positions` indexes are all heavily used (the white_hash index at 82 scans and black_hash at 576 are the lightest, but they back the "my pieces only" / system-opening feature, which is used sporadically — keep).

### Dead tuples / autovacuum

| Table | n_live | n_dead | Dead % | Last autovacuum | Last autoanalyze |
|---|---|---|---|---|---|
| games | 588,326 | 62,915 | ~9.7% | 2026-06-09 14:19 | 2026-06-09 15:12 |
| game_positions | 43.9M | 160,596 | ~0.4% | never | 2026-06-09 14:55 |
| user_rating_anchors | 21 | 13 | ~38% | never | never |
| users | 129 | 42 | ~25% | never | 2026-06-09 16:18 |

All dead-tuple ratios are fine in absolute terms. `users` (42 dead) and `user_rating_anchors` (13 dead) show high *percentages* but trivial *counts* — autovacuum correctly ignores tables this tiny. `games` at ~9.7% is well under the 20% threshold and was autovacuumed yesterday. `game_positions` has never triggered autovacuum (append-mostly via COPY, few updates beyond the eval backfill) but was autoanalyzed yesterday and sits at 0.4% dead — no bloat. No action needed.

## Summary

- **Size:** 9.9 GB, and `game_positions` is 86% of it (8.65 GB incl. 1.93 GB of secondary indexes). DB growth is linear in imported positions (~74/game); there is no bloat. Total is healthy for the CPX42's 160 GB disk.
- **Cache hit 98.72%** — good. Slightly below "excellent" only because the 8.6 GB positions table can't be fully resident on a 16 GB host; not a concern.
- **No user-facing latency problem.** The server-time leaders are all import/eval plumbing (`COPY`, pending-evals poller, per-row FK lock on `users`), inflated by the recent large imports (one guest alone added 4.9M positions). Per-call times there are sub-60 ms.
- **One recurring slow read:** the **openings explorer aggregation** averages **748 ms over 126 calls (94 s total, 4.8 s worst case)**. It's the single user-facing query worth optimizing — the `count(distinct games.id)` per candidate move over `openings_dedup` is the cost center.
- **No index action.** Every large index on `game_positions` is heavily used; the only zero-scan indexes are sub-500 kB and mostly required for auth/integrity. Nothing to drop.
- **Vacuum/dead tuples healthy** across the board (all well under 20% by count-weighted measure).

**Recommended:**
- *Consider* an EXPLAIN ANALYZE pass on the openings explorer query (full text not captured here, only the 300-char prefix) to see whether the per-move `count(distinct games.id)` can be cut — e.g. a precomputed position→WDL rollup, or restructuring the dedup CTE. Worth it if openings is a hot path; the 4.8 s tail is the worst single user wait observed.

**Monitor:**
- Guest data accumulation: user 167's 4.9M positions show a single guest import can move the needle on DB size. If guest retention is low, a periodic guest-data reaper would reclaim meaningful space.
- Stats are only ~5 days old (reset 2026-06-05). Re-check after a full week of steady traffic for a more representative picture before acting on the openings query.

**No action needed:** `users` seq scans (tiny-table FK checks), cache hit ratio, all index sizes, autovacuum cadence.
