# FlawChess DB Report — 2026-07-02

- **DB**: prod
- **Snapshot taken**: 2026-07-02T13:15Z (approx)
- **Sections run**: users / storage / performance / sanity
- **Note**: pg_stat_statements and pg_stat_* counters cover the window since stats reset on **2026-06-23** (~9 days).

## 0. Users Overview

### User summary

| total users | registered | guests |
|---|---|---|
| 174 | 86 | 88 |

### 10 most recent users

| id | chess.com | lichess | guest? | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 215 | yes | no | yes | 2026-07-02 | 2026-07-02 | 472 | 28,348 |
| 214 | no | no | yes | 2026-07-02 | 2026-07-02 | 0 | 0 |
| 213 | yes | no | yes | 2026-07-01 | 2026-07-01 | 409 | 30,037 |
| 212 | yes | no | yes | 2026-07-01 | 2026-07-01 | 60 | 3,606 |
| 211 | no | no | yes | 2026-07-01 | 2026-07-01 | 0 | 0 |
| 210 | yes | yes | no | 2026-07-01 | 2026-07-01 | 1,118 | 60,471 |
| 209 | no | yes | no | 2026-06-30 | 2026-06-30 | 1,233 | 74,595 |
| 208 | yes | yes | no | 2026-06-29 | 2026-06-30 | 854 | 59,107 |
| 207 | yes | no | yes | 2026-06-29 | 2026-06-29 | 185 | 10,684 |
| 206 | yes | yes | no | 2026-06-29 | 2026-06-29 | 6,048 | 412,776 |

### Platform breakdown

| platform | users | games |
|---|---|---|
| chess.com | 114 | 459,375 |
| lichess | 63 | 226,509 |

Activity note: 8 of the 10 most recent signups imported games (healthy funnel); the guest:registered ratio is roughly 1:1. Registered users return (last_login > created_at for the recent registered accounts).

## 1. Storage Report

### Overview

| DB size | games | positions | avg positions/game |
|---|---|---|---|
| 12 GB | 685,884 | 49,949,535 | 72.8 |

### Per-table breakdown

| table | data | indexes | total |
|---|---|---|---|
| game_positions | 4,915 MB | 4,011 MB | 8,926 MB |
| games | 1,791 MB | 546 MB | 2,336 MB |
| game_flaws | 773 MB | 371 MB | 1,144 MB |
| opening_position_eval | 72 MB | 74 MB | 146 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| (all others) | <2 MB each | | |

### Largest indexes

| index | table | size |
|---|---|---|
| game_positions_pkey | game_positions | 1,559 MB |
| ix_gp_user_endgame_game | game_positions | 712 MB |
| ix_gp_user_full_hash_move_san | game_positions | 583 MB |
| ix_game_positions_game_id | game_positions | 351 MB |
| ix_gp_user_white_hash | game_positions | 312 MB |
| ix_gp_user_black_hash | game_positions | 311 MB |
| game_flaws_pkey | game_flaws | 201 MB |
| ix_gp_full_hash_opening | game_positions | 180 MB |
| uq_games_user_platform_game_id | games | 83 MB |

Index-to-data ratio on game_positions is 0.82:1 (4 GB of indexes on 4.9 GB of data). game_positions is 74% of the whole database.

## 2. Performance Analysis

### Buffer cache hit ratio

**99.86%** — excellent. The working set fits in shared_buffers + OS cache.

### Slowest queries by average time

All entries above ~500 ms avg are **one-off ad-hoc/monitoring queries** (blob-backfill audit CTEs, this report's own queries, `SELECT t.* FROM games ORDER BY ... LIMIT 501` browsing queries). No recurring application query averages above ~300 ms. The worst recurring app-adjacent queries:

| avg_ms | calls | rows | query |
|---|---|---|---|
| 228 | 2 | 8 | opening explorer candidate-move WDL aggregate (gp1/gp2 self-join) |
| 203 | 3 | 3 | `WITH dedup AS (SELECT DISTINCT ON (full_hash, game_id) ...)` position WDL |
| 196 | 2 | 175 | opening insights 16-half-move scan aggregate |

### Highest total execution time (the real optimization targets)

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 1,951,678 | 15,219 | 128.2 | tier-4 drain: pick user — `SELECT u.id FROM users WHERE NOT is_guest AND EXISTS (games JOIN game_flaws ... allowed_pv_lines IS NULL) ORDER BY -ln(random())/weight LIMIT n` |
| 773,527 | 15,219 | 50.8 | tier-4 drain: pick game for user — same softmax-random ORDER BY over all qualifying games |
| 24,169 | 112,788 | 0.21 | drain: users with lichess-eval games poll |
| 21,583 | 112,593 | 0.19 | drain: lichess-evals game poll |
| 14,909 | 48,238 | 0.31 | full `games` row fetch by id (drain) |
| 13,974 | 100,423 | 0.14 | `UPDATE game_flaws SET *_tactic_* ...` |

The two tier-4 poller queries together account for **~45 minutes of DB time in 9 days (~0.35% duty cycle)** and dominate everything else by 30x. Each call computes a softmax weight for *every* qualifying user/game and sorts, just to pick 1–n rows. At current scale this is 128 ms every ~50 s — affordable but the top optimization target as data grows (cost is O(qualifying games), and the EXISTS anti-join over `game_flaws.allowed_pv_lines IS NULL` re-scans work that shrinks only as backfill completes).

### Sequential scan analysis

| table | seq_scan | seq_tup_read | idx_scan | verdict |
|---|---|---|---|---|
| games | 69,817 | 15.6 B | 6.0 B | **Investigate**: ~224k tuples/scan avg = regular full-table scans of an 839k-row table. EXPLAIN ANALYZE of the tier-4 user-poll shows it uses bitmap index scans (60k buffer hits/run, no seq scan), so the seq scans come from something else — likely the per-user game-pick weighting query on large accounts and/or monitoring queries. Worth an `auto_explain` session to pin down. |
| users | 6.3 M | 962 M | 944 k | OK (174 rows; seq scan is optimal) |
| eval_jobs | 7.3 M | 510 M | 176 k | OK (~170 rows; polling table) |
| game_positions | 14 | 448 M | 19.5 M | Excellent — effectively never seq-scanned |
| game_flaws | 116 | 166 M | 362 M | OK |
| import_jobs | 127 k | 36 M | 524 k | OK (309 rows) |

### Index usage highlights

- **`uq_games_id_user_id`: 5.59 B scans in 9 days (~7,000/s)** — the composite (id, user_id) unique index is the join target for every per-flaw/per-position games probe in the drain loops. It works (all index hits), but the volume shows how hot the drain polling is.
- **`ix_game_flaws_blob_backfill`: 347 M scans, 25.2 B tuples read, only 80 M fetched** — huge read amplification (~73 tuples read per useful fetch); the backfill predicate re-reads the same pending rows constantly.
- **`ix_games_pv_backfill_pending` / `ix_games_needs_engine_full_evals`: ~210 M scans each** — hot poll indexes, tiny fetch counts, working as designed (partial indexes doing their job).
- **Near-unused large indexes** (since 2026-06-23): `ix_gp_user_white_hash` (312 MB, 10 scans), `ix_gp_user_black_hash` (311 MB, 32 scans) — these back the system-opening filter feature, so they're feature-required but cost ~620 MB for a rarely-used feature. `ix_gp_full_hash_opening` (180 MB, 2 scans) — investigate whether anything still uses it. `ix_games_full_pv_pending` (20 MB, **0 scans**) — likely superseded by `ix_games_pv_backfill_pending`; candidate to drop after code check.
- Zero-scan small indexes (llm_logs ×5, openings, oauth_account, feedback, ix_users_email) — all tiny; keep (auth/FK/lookup roles).

### Dead tuples / autovacuum

game_positions 2.1% dead, game_flaws 6.9% dead, games 0.9% — all healthy; autovacuum ran within the last day on all big tables.

## 3. Sanity Checks

### Check A — games oracle columns vs game_flaws

- **NULL-count gap: 0** (no lichess game has derived flaws but NULL count columns).
- Match rate: 142,171 exact / ~144k with counts = **98.6%** (1,277 mistake mismatches, 726 blunder mismatches).
- Direction: game_flaws slightly over-counts (1,077 games over vs 200 under on mistakes). Aggregate totals: mistakes 433,502 (lichess) vs 434,730 (game_flaws) = **+0.28%**; blunders 654,861 vs 655,365 = **+0.08%**. Well within the ~1% tolerance; expected independent-classifier drift.

**Verdict: PASS**

### Check B — ≥90% eval coverage vs oracle columns (Flaws Timeline gate)

| platform | games ≥90% coverage | oracle NULL | oracle present |
|---|---|---|---|
| chess.com | 297,018 | **0** | 297,018 |
| lichess | 142,432 | **0** | 142,432 |

`ge90_but_oracle_null = 0` on both platforms — no analyzed game is invisible to the Flaws Timeline. Notably, chess.com full-coverage games (297k) now all carry oracle columns, i.e. the Stockfish oracle backfill is keeping up.

**Verdict: PASS**

## Summary

- **12 GB total; game_positions is 74% of it** (8.9 GB, of which 4 GB indexes). ~620 MB of that is the two per-color hash indexes serving a rarely-used feature (10 + 32 scans in 9 days) — a conscious cost, but worth remembering.
- **Cache hit 99.86%, autovacuum healthy, both data-integrity checks PASS** (0 null-count gap, aggregates within 0.3%; 0 timeline-invisible analyzed games).
- **The eval-drain tier-4 pollers are the dominant DB load**: two softmax-random selection queries burn ~45 min of DB time per 9 days (128 ms + 51 ms per call, every ~50 s) and drive regular full-table seq scans of `games` plus billions of index probes (`uq_games_id_user_id` at ~7k scans/s, `ix_game_flaws_blob_backfill` reading 73 tuples per useful row). Not urgent at today's scale, but this is the first thing to restructure as data grows (e.g. maintain a materialized pending-work set or sample candidates before weighting, instead of weighting the full qualifying set per poll).

EXPLAIN ANALYZE of the user-poll query (2026-07-02): Nested Loop Semi Join over all 86 registered users, bitmap-scanning each user's games (~5,000 index rows read per user) and probing `ix_game_flaws_blob_backfill` 16,226 times; 60,502 shared buffer hits, 0 disk reads, 187 ms. All cache, no seq scan — the cost is CPU/buffer churn proportional to (users × games), repeated every poll cycle.
- **Candidate index drop**: `ix_games_full_pv_pending` (20 MB, 0 scans, apparently superseded by `ix_games_pv_backfill_pending`) — verify no code path uses it, then drop. `ix_gp_full_hash_opening` (180 MB, 2 scans) deserves the same check.
- No recurring application query averages above ~300 ms; the slow-query top list is ad-hoc admin/monitoring noise.
