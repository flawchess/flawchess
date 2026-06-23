# FlawChess DB Report — 2026-06-23

- **DB**: prod
- **Snapshot taken**: 2026-06-23T17:59:01Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| total users | registered | guests |
|---|---|---|
| 158 | 79 | 79 |

### 10 most recent users

| id | chess.com | lichess | guest | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 199 | ✓ | | no | 2026-06-23 | 2026-06-23 | 5,965 | 365,627 |
| 197 | ✓ | | yes | 2026-06-23 | 2026-06-23 | 863 | 52,163 |
| 196 | ✓ | | no | 2026-06-23 | 2026-06-23 | 209 | 9,872 |
| 195 | ✓ | | yes | 2026-06-23 | 2026-06-23 | 544 | 30,407 |
| 194 | ✓ | | no | 2026-06-22 | 2026-06-22 | 9,282 | 649,589 |
| 193 | ✓ | | no | 2026-06-21 | 2026-06-21 | 39 | 2,346 |
| 192 | ✓ | | yes | 2026-06-21 | 2026-06-21 | 649 | 35,779 |
| 191 | | | yes | 2026-06-20 | 2026-06-20 | 0 | 0 |
| 190 | | ✓ | yes | 2026-06-20 | 2026-06-20 | 891 | 49,452 |
| 189 | ✓ | | no | 2026-06-20 | 2026-06-20 | 4,888 | 243,904 |

### Platform breakdown

| platform | users | games |
|---|---|---|
| chess.com | 102 | 435,366 |
| lichess | 59 | 223,125 |

**Activity note:** 158 total users, an even 79/79 registered-vs-guest split. Of the 10 most recent signups, 9 imported games (only guest 191 has zero). chess.com dominates (~2x lichess games). Recent signups are heavily chess.com-only.

## 1. Storage Report

### Overview

| metric | value |
|---|---|
| Database size | **15 GB** |
| Total games | 658,491 |
| Total positions | 48,162,374 |
| Avg positions/game | ~73 |

### Per-table breakdown (top consumers)

| table | data | index | total |
|---|---|---|---|
| game_positions | 6,682 MB | 5,815 MB | **12 GB** |
| games | 1,791 MB | 506 MB | 2,297 MB |
| game_flaws | 329 MB | 229 MB | 558 MB |
| opening_position_eval | 69 MB | 74 MB | 143 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 32 kB | 992 kB | 1,024 kB |

(All other tables < 1 MB.)

### Per-index breakdown (top consumers)

| index | table | size |
|---|---|---|
| game_positions_pkey | game_positions | 2,342 MB |
| ix_gp_user_endgame_game | game_positions | 1,104 MB |
| ix_gp_user_full_hash_move_san | game_positions | 720 MB |
| ix_game_positions_game_id | game_positions | 534 MB |
| ix_gp_user_black_hash | game_positions | 408 MB |
| ix_gp_user_white_hash | game_positions | 404 MB |
| ix_gp_full_hash_opening | game_positions | 299 MB |
| game_flaws_pkey | game_flaws | 160 MB |
| uq_games_user_platform_game_id | games | 81 MB |
| opening_position_eval_pkey | opening_position_eval | 74 MB |

**Storage summary:** `game_positions` is 12 GB of the 15 GB total (~80%), split 6.7 GB data / 5.8 GB index. Its index footprint nearly equals its data — seven indexes on 48M rows. The 7 `game_positions` indexes together (~5.7 GB) are the single biggest lever on DB size; all are in active use (see index usage below), so none are droppable. `games` is the next at 2.3 GB.

## 2. Performance Analysis

> `stats_reset` = 2026-06-15T16:24:13Z — cumulative stats span ~8 days.

### Buffer cache hit ratio

**83.14%** — ⚠️ **investigate** (target >99%). This is well below healthy. With `shared_buffers=2GB` and a 12 GB `game_positions` table, the working set doesn't fit in cache, so the heavy eval-queue scans spill to disk reads. Sustained 83% on this workload is expected given the table:buffer ratio, but it's the clearest performance signal in this snapshot. See recommendations.

### Slowest queries by avg time

Most high-avg entries are **one-off analytical/maintenance queries** (`calls = 1`: missing-PV audits, this report's own queries, a single user DELETE at 6.4s). The one recurring slow query that matters:

| avg_ms | max_ms | calls | total_ms | query |
|---|---|---|---|---|
| 8,576 | 14,273 | 7 | 60,033 | `SELECT count(*) … game_positions JOIN games … need_bm/need_pv` (PV/best-move backfill coverage count) |

The 25.6s / 15.7s / 10s entries are all single-call missing-PV region audits — diagnostics, not user-facing.

### Highest total time queries (server-time dominators)

| total_ms | calls | avg_ms | rows | query |
|---|---|---|---|---|
| 78,663,590 | 191,099 | 411.64 | 103,244 | eval-queue tier-2 pick: `games … full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL AND NOT is_guest` |
| 3,530,095 | 275,870 | 12.80 | 275,870 | eval-queue tier-3 lottery pick (per-user `-ln(random())/weight`) |
| 691,196 | 466,970 | 1.48 | 275,870 | eval-queue tier-3 user eligibility `EXISTS` |
| 337,195 | 390,070 | 0.86 | 504 | entry-eval pick `LIMIT 1 OFFSET` |
| 281,649 | 427,594 | 0.66 | 30.8M | per-game ply eval fetch |

**The dominant server cost is the eval-queue tier-2 pick: 78.7M ms (~21.8 hours of cumulative exec over 8 days), 191k calls at 412ms avg.** This single query is ~95% of total tracked query time. It's a polling query for the analysis worker queue. At 412ms × 191k calls it's both frequent and not cheap — the top optimization target.

### Sequential scan analysis

| table | seq_scan | idx_scan | verdict |
|---|---|---|---|
| game_positions | 18,347 | 1.10B | OK — overwhelmingly index-driven; seq scans are bulk maintenance |
| games | 228,243 | 8.59B | OK — index-dominated; seq scans likely the eval-queue counts |
| users | 5,337,314 | 627,731 | tiny table (158 rows) — seq scan is correct/optimal |
| eval_jobs | 1,850,510 | 7,972 | tiny table (94 rows) — seq scan is correct |
| import_jobs | 92,868 | 2,204,641 | tiny table (266 rows) — fine |
| oauth_account | 44,573 | 0 | tiny table (8 rows) — fine |

No problematic seq-scan patterns. The high seq_scan counts are all on tiny tables where PostgreSQL correctly prefers a scan.

### Index usage — unused indexes (0 scans)

All "keep" — required for FK/PK/auth integrity or recently added:

- `ix_users_email`, `oauth_account_pkey`, `ix_oauth_account_*` — **keep** (auth/OAuth flows).
- `llm_logs_*` (5 indexes), `feedback_pkey`, `ix_feedback_user_id`, `bookmarks_pkey`, `benchmark_cohort_cdf_pkey` — **keep** (low-volume tables, integrity/PK).
- `openings_pkey`, `ix_openings_eco_name`, `uq_openings_eco_name_pgn` — **keep** (openings table currently shows 0 live tuples in stats but is reference data).
- `ix_games_full_pv_pending` (20 MB, 0 scans), `ix_eval_jobs_pick`, `ix_eval_jobs_leased` — **keep/monitor**: queue indexes that may only be hit in specific worker states. `ix_games_full_pv_pending` is the only sizeable one (20 MB) — worth confirming it's still referenced by the PV-backfill path before considering a drop.

No index is both large and genuinely droppable. The big `game_positions` indexes are all heavily used (`ix_gp_user_endgame_game` 1.67M scans, `ix_gp_full_hash_opening` 241k scans, etc.).

### Dead tuples / autovacuum

All healthy. Largest absolute dead-tuple count is `game_positions` at 825k dead / 48.2M live (1.7%). `games` 30.8k / 808k (3.8%). Autovacuum/autoanalyze ran today (2026-06-23) on all hot tables. No bloat concerns.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

| metric | value |
|---|---|
| lichess games with flaws | 138,004 |
| **flaws but all counts NULL** | **0** ✅ |
| exact match | 138,733 |
| mistake mismatch | 1,331 |
| blunder mismatch | 756 |

Match rate ≈ **98.5%** (mismatches are a small fraction; the two classifiers are independent by design).

**Mismatch direction & aggregate totals:**

| | game_flaws under | game_flaws over |
|---|---|---|
| mistakes | 212 | 1,119 |
| blunders | 191 | 565 |

| | lichess oracle | game_flaws | diff |
|---|---|---|---|
| total mistakes | 424,235 | 425,517 | +0.30% |
| total blunders | 641,037 | 641,555 | +0.08% |

Aggregate totals agree within **0.3%**. `game_flaws` slightly over-counts vs lichess (expected ES-threshold vs lichess-win% classifier drift).

**Verdict (Check A): PASS** — NULL-count gap is 0, aggregate totals within ~0.3%.

### Check B — Eval coverage ≥90% vs oracle-column presence (Flaws Timeline gate)

| platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| chess.com | 281,661 | **0** ✅ | 281,661 |
| lichess | 139,078 | **0** ✅ | 139,078 |

**Verdict (Check B): PASS** — zero eval-covered games with NULL oracle columns on either platform. The Flaws Timeline's oracle-present gate loses no analyzed games. (Notably chess.com now has 281k games at ≥90% coverage with oracle columns populated — full backfill is complete there.)

## Summary

- **DB size: 15 GB.** `game_positions` (48.2M rows) is ~80% of it — 6.7 GB data + 5.8 GB across 7 indexes. That table is the only thing that materially moves total size.
- **Data integrity: clean.** Both sanity checks PASS. Flaw counts match within 0.3% aggregate, zero NULL-count gaps, and zero eval-covered-but-oracle-null games on either platform (chess.com oracle backfill is fully landed).
- **⚠️ Cache hit ratio 83%** — the one real concern. The 12 GB `game_positions` table vastly exceeds `shared_buffers=2GB`, so heavy queue scans hit disk. **Do not raise `shared_buffers` above 2 GB** (CLAUDE.md: it amplifies checkpoint flush size and revisits the OOM history). Mitigate via the query below instead.
- **⚠️ Eval-queue tier-2 pick query dominates server time** — 78.7M ms cumulative (~95% of all tracked query time), 191k calls at 412ms avg. This is the worker polling for tier-2 analysis candidates (`full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL AND NOT is_guest`). Worth an `EXPLAIN ANALYZE` to confirm it has a covering partial index; at 412ms/call it's scanning more than it should. **Top optimization target.** This also explains much of the low cache-hit ratio (repeated large scans of `games`/`game_positions`).
- **Indexes:** nothing droppable. All large `game_positions` indexes are actively used; the 0-scan indexes are all small auth/integrity/queue indexes worth keeping.
- **Vacuum/bloat:** healthy, autovacuum current on all hot tables.

**Recommended next step:** `EXPLAIN (ANALYZE, BUFFERS)` the tier-2 eval-queue pick query — if it's not served by a tight partial index on `(full_evals_completed_at) WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL`, adding/tuning one would cut both the 412ms avg and the disk-read pressure dragging the cache-hit ratio down.
