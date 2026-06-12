# FlawChess DB Report — 2026-06-12

- **DB**: prod
- **Snapshot taken**: 2026-06-12T06:28:53Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 134 | 65 | 69 |

### 10 most recent users

| ID | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 174 | ✅ | — | ✅ | 2026-06-11 | 2026-06-11 | 711 | 38,474 |
| 173 | ✅ | — | ✅ | 2026-06-11 | 2026-06-11 | 3,987 | 204,355 |
| 172 | ✅ | — | ✅ | 2026-06-11 | 2026-06-11 | 1,455 | 106,178 |
| 171 | — | ✅ | ✅ | 2026-06-11 | 2026-06-11 | 2,141 | 134,343 |
| 170 | — | — | — | 2026-06-11 | 2026-06-11 | 0 | 0 |
| 169 | — | ✅ | ✅ | 2026-06-10 | 2026-06-10 | 1,102 | 87,943 |
| 168 | ✅ | — | — | 2026-06-09 | 2026-06-09 | 1,056 | 69,619 |
| 167 | ✅ | — | ✅ | 2026-06-09 | 2026-06-09 | 55,699 | 4,867,017 |
| 166 | ✅ | ✅ | ✅ | 2026-06-08 | 2026-06-08 | 6,777 | 444,306 |
| 165 | ✅ | — | — | 2026-06-07 | 2026-06-07 | 595 | 42,517 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 83 | 386,168 |
| lichess | 57 | 212,172 |

**Activity note:** 9 of the 10 most recent signups imported games — healthy onboarding. The lone exception is user 170 (registered, no platform linked, 0 games). Guests slightly outnumber registered users (69 vs 65), consistent with the no-friction guest flow. One whale stands out: user 167 with **55,699 games / 4.87M positions** — by far the largest single account and the most likely source of the heavy queries flagged in Section 2.

---

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 11 GB |
| Total games | 598,340 |
| Total positions | 44,394,193 |
| Avg positions / game | ~74 |

### Per-table breakdown (by total size)

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 5,491 MB | 3,322 MB | 8,812 MB |
| games | 1,791 MB | 293 MB | 2,083 MB |
| game_flaws | 34 MB | 27 MB | 61 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 24 kB | 776 kB | 800 kB |
| import_jobs | 48 kB | 408 kB | 456 kB |
| user_benchmark_percentiles | 160 kB | 104 kB | 264 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| users | 40 kB | 64 kB | 104 kB |
| oauth_account | 24 kB | 80 kB | 104 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top by size)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,346 MB |
| ix_gp_user_endgame_game | game_positions | 628 MB |
| ix_gp_user_full_hash_move_san | game_positions | 507 MB |
| ix_game_positions_game_id | game_positions | 301 MB |
| ix_gp_user_white_hash | game_positions | 270 MB |
| ix_gp_user_black_hash | game_positions | 268 MB |
| uq_games_user_platform_game_id | games | 72 MB |
| ix_games_user_played_at | games | 36 MB |
| games_pkey | games | 26 MB |
| uq_games_id_user_id | games | 26 MB |
| game_flaws_pkey | game_flaws | 17 MB |
| ix_game_flaws_game_id | game_flaws | 5,448 kB |
| ix_game_flaws_user_severity | game_flaws | 4,104 kB |

**Storage summary:** `game_positions` dominates at 8.8 GB total (80% of the DB), split 5.5 GB data + 3.3 GB indexes. Its index-to-data ratio is ~0.6 — six indexes on a 44M-row table, all justified by the Zobrist-hash lookup patterns. The single largest index is `game_positions_pkey` (1.35 GB). `games` is the second consumer at 2.1 GB. Everything else is rounding error. No storage concern at 11 GB on a 160 GB disk.

---

## 2. Performance Analysis

### Buffer cache hit ratio

**99.84%** — excellent (>99%). The working set fits comfortably in `shared_buffers` (4 GB). Stats were last reset 2026-06-05, so this reflects ~7 days of activity.

### ⚠️ Slowest queries by avg time

| avg_ms | max_ms | calls | total_ms | query |
|---|---|---|---|---|
| **5,918,924** (~98 min) | 20,943,955 (~5.8 h) | 7 | 41,432,465 | `SELECT analyzed_games.played_at, coalesce(flaw_counts.mb_count, …)` — **Flaws Timeline** |
| **3,939,937** (~66 min) | 27,521,230 (~7.6 h) | 7 | 27,579,559 | Flaws Timeline (variant 2) |
| **1,183,643** (~20 min) | 1,834,631 | 2 | 2,367,286 | Flaws Timeline (variant 3) |
| 14,328 | 50,715 | 7 | 100,293 | flaw-stats aggregate (`count(*) FILTER … severity/tempo/phase`) |
| 7,113 | 48,449 | 7 | 49,792 | flaw-stats aggregate (variant) |
| 3,782 | 13,164 | 7 | 26,471 | flaws-tab EXISTS count |

> Note: the four-digit `total_ms` rows near the bottom of the raw top-20 are this report's own Section-3 sanity queries and ad-hoc exploration (sub-1.3 s each) — ignore them as optimization targets.

### Highest total time queries

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 41,432,465 | 7 | 5,918,924 | **Flaws Timeline** (variant 1) |
| 27,579,559 | 7 | 3,939,937 | **Flaws Timeline** (variant 2) |
| 2,367,286 | 2 | 1,183,643 | **Flaws Timeline** (variant 3) |
| 170,096 | 603,818 | 0.28 | `game_positions` bulk row fetch (import/replay) — fine |
| 100,293 | 7 | 14,328 | flaw-stats aggregate |
| 86,941 | 590,479 | 0.15 | `games` row fetch — fine |

Three variants of the **Flaws Timeline** query account for **~71 million ms (~19.7 hours)** of cumulative server time over just 16 calls in a 7-day window. Per-call times of 1–5 hours mean these almost certainly never return to the user (HTTP/client timeout) and instead sit burning a connection + CPU until they finish or are killed.

### EXPLAIN ANALYZE

**Deliberately skipped.** The skill says to EXPLAIN ANALYZE any query averaging >500 ms, but reproducing a query whose *average* runtime is ~98 minutes (max ~5.8 h) against the production DB would tie up a backend for hours and risk the same resource pressure that has OOM-killed Postgres before. This needs to be reproduced and planned against a **non-prod** copy (or with a tight `statement_timeout` and a small test user), not profiled live. Flagged as **Recommended** below.

### Sequential scan analysis

| Table | seq_scan | idx_scan | Verdict |
|---|---|---|---|
| users | 7,062,457 | 2 | Expected — 134-row table; planner correctly prefers seq scan. The FastAPI-Users `… FOR KEY SHARE` row-lock runs per request (630k calls @ 0.02 ms). No action. |
| game_positions | 32 | 82,485,446 | Healthy — overwhelmingly index-driven. |
| games | 63 | 70,701,773 | Healthy. |
| game_flaws | 17 | 8,456,076 | Healthy. |
| openings | 419 | 0 | 3,641-row static table; seq scan fine but see index note. |
| oauth_account | 6,812 | 0 | 5-row table; seq scan optimal. |

### Index usage

- **Unused (0 scans) — keep:** `users_pkey`-adjacent auth indexes, `oauth_account_*` and `ix_users_email` (OAuth/login correctness), all PKs, and `uq_*` unique constraints (data integrity). Keep regardless of scan count.
- **Unused (0 scans) — `llm_logs` indexes** (`ix_llm_logs_created_at`, `_endpoint_created_at`, `_model_created_at`, `_user_id_created_at`, `_findings_hash`): the table has 9 rows; these are forward-looking and trivially small (16 kB each). No action.
- **`openings` indexes 0 scans** (`ix_openings_eco_name`, `openings_pkey`, `uq_openings_eco_name_pgn`): the table is read via seq scan (419 scans, 0 idx). Tiny table, indexes are cheap — keep for the unique constraint; not worth touching.
- No large index is both unused and droppable. Nothing to drop.

### Dead tuples / autovacuum

All tables are well within healthy dead-tuple ratios:
- `game_positions`: 363k dead / 44.4M live (~0.8%), autoanalyzed 2026-06-11.
- `game_flaws`: 16k dead / 290k live (~5.4%), autovacuumed 2026-06-11.
- `games`: 4.2k dead / 597k live (<1%), autovacuumed 2026-06-11.

No table exceeds the 20% threshold. Autovacuum is keeping up.

### Performance recommendations

- **No action needed** — Cache hit 99.84%, dead-tuple ratios all <6%, index usage healthy, `users`/`oauth_account` seq scans are correct planner choices on tiny tables. Bulk `game_positions`/`games` row fetches (sub-0.3 ms) are normal import/replay traffic.
- **Monitor** — Stats were reset 2026-06-05; the window is short. Re-check in a week. The flaw-stats aggregate (~14 s avg, 7 calls) is slow-ish but not yet alarming — watch whether it grows with the heaviest users.
- **🔴 Recommended (high priority)** — Investigate and fix the **Library "Flaws Timeline" query** (`played_at` + `coalesce(flaw_counts.mb_count, …)`, introduced in commit `e39eca22`). Three variants average 20–98 minutes per call and have consumed ~19.7 h of server time in 7 days. Almost certainly a per-game flaw join that explodes for whale accounts (user 167 has 55,699 games). Reproduce on a **non-prod** copy with that user, get an `EXPLAIN ANALYZE`, and add an index or pre-aggregate `mb_count` per game. Until fixed, consider a `statement_timeout` guard on that endpoint so a single request can't pin a connection for hours.
- **Consider** — A partial/pre-aggregated flaw-count-per-game (materialized column on `games`, or a small rollup table) would serve both the Flaws Timeline and the ~14 s flaw-stats aggregate from one cheap lookup.

---

## 3. Sanity Checks

Integrity check: do the `games` per-color move-quality count columns (`white/black_mistakes`, `white/black_blunders`) agree with the independently derived `game_flaws` table? Scoped to `platform = 'lichess'` (chess.com supplies accuracy, not M/B counts, and has zero flaw rows by design).

### Flaw count integrity (Query 9)

| Metric | Value |
|---|---|
| Lichess games with flaw rows | 38,964 |
| **Flaws present but counts all NULL** | **0** ✅ |
| Exact match (mistakes & blunders) | 38,355 |
| Mistake-count mismatches | 1,099 |
| Blunder-count mismatches | 511 |

**Match rate: 98.4%** (38,355 / 38,964).

### Mismatch diagnosis (Query 10)

| | game_flaws under | game_flaws over |
|---|---|---|
| Mistakes | 135 | 964 |
| Blunders | 102 | 409 |

| | lichess total | game_flaws total | Δ |
|---|---|---|---|
| Mistakes | 111,939 | 112,838 | +0.8% |
| Blunders | 177,206 | 177,472 | +0.15% |

Per-game disagreement skews toward `game_flaws` slightly *over*-counting, but aggregate totals agree within ~1%. This is expected behavior of two independent classifiers (lichess win% vs the project's Option-B ES thresholds; the mate-ladder path is a known minor source of drift). Not a data bug.

### Verdict: **PASS** ✅

`flaws_but_all_counts_null = 0` and aggregate totals agree within ~1%. No NULL-count data gap; count drift is within expected classifier tolerance.

---

## Summary

- **DB size 11 GB** on a 160 GB disk — no storage pressure. `game_positions` is 80% of it (8.8 GB across 44.4M rows); all six indexes on it are justified.
- **Cache hit 99.84%**, dead-tuple ratios <6% everywhere, autovacuum keeping up — DB health is good.
- **🔴 One critical performance issue:** the Library **Flaws Timeline** query (commit `e39eca22`) averages **20–98 minutes per call** (max ~5.8 h) and has burned ~19.7 hours of server time in 7 days across 16 calls. It almost certainly never returns to the user and pins a connection while running. **Top priority:** reproduce on a non-prod copy with whale user 167 (55,699 games), `EXPLAIN ANALYZE`, and either index/pre-aggregate per-game flaw counts or guard the endpoint with a `statement_timeout`. A flaw-count rollup would also speed the ~14 s flaw-stats aggregate.
- **Sanity check PASS:** `games` M/B count columns vs `game_flaws` — 0 NULL-when-expected, 98.4% per-game match, aggregate within ~1%. Healthy.
- **No index drops** warranted; unused indexes are all tiny and kept for auth/integrity/forward-use.
