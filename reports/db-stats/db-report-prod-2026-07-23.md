# FlawChess DB Report — 2026-07-23

- **DB**: prod
- **Snapshot taken**: 2026-07-23T19:18:12Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 228 | 107 | 121 |

### 10 most recent users

| id | chess.com | lichess | guest? | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 269 | ✓ | ✓ | yes | 2026-07-23 | 2026-07-23 | 17,462 | 1,200,388 |
| 268 | ✓ | — | yes | 2026-07-23 | 2026-07-23 | 9,783 | 664,931 |
| 267 | — | ✓ | yes | 2026-07-23 | 2026-07-23 | 391 | 19,462 |
| 266 | ✓ | — | yes | 2026-07-23 | 2026-07-23 | 3,877 | 267,421 |
| 265 | — | — | yes | 2026-07-23 | 2026-07-23 | 1 | 61 |
| 264 | ✓ | — | yes | 2026-07-23 | 2026-07-23 | 269 | 22,991 |
| 263 | — | — | yes | 2026-07-23 | 2026-07-23 | 0 | 0 |
| 262 | ✓ | — | **no** | 2026-07-23 | 2026-07-23 | 4,226 | 256,178 |
| 261 | — | ✓ | yes | 2026-07-23 | 2026-07-23 | 448 | 31,732 |
| 260 | ✓ | ✓ | yes | 2026-07-23 | 2026-07-23 | 1,441 | 78,200 |

### Platform breakdown (all users)

| Platform | Users | Games |
|---|---|---|
| chess.com | 140 | 591,995 |
| lichess | 79 | 276,658 |
| flawchess | 6 | 54 |

**Activity note:** All 10 most-recent users signed up today (2026-07-23) — a busy import day. 8 of 10 imported games; only 2 (ids 263, 265) linked/imported nothing meaningful. Just 1 of the 10 is a registered account (id 262); the rest are guests. Overall the base is 47% registered / 53% guest. chess.com dominates game volume (~68% of imported games) with roughly 2× the linked users of lichess. The `flawchess` platform rows (54 games, 6 users) are bot games, not imports.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 21 GB |
| Total games | 868,707 |
| Total positions | 63,595,530 |
| Avg positions / game | ~73.2 |

### Per-table breakdown (by total size)

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 6,119 MB | 5,946 MB | 12 GB |
| game_flaws | 4,980 MB | 433 MB | 5,412 MB |
| games | 2,705 MB | 907 MB | 3,612 MB |
| game_best_moves | 154 MB | 128 MB | 282 MB |
| opening_position_eval | 96 MB | 74 MB | 170 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 56 kB | 1,544 kB | 1,600 kB |
| worker_heartbeats | 936 kB | 56 kB | 992 kB |
| import_jobs | 216 kB | 440 kB | 656 kB |

(remaining tables all < 400 kB)

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 2,285 MB |
| ix_gp_user_endgame_game | game_positions | 1,086 MB |
| ix_gp_user_full_hash_move_san | game_positions | 803 MB |
| ix_game_positions_game_id | game_positions | 553 MB |
| ix_gp_user_black_hash | game_positions | 439 MB |
| ix_gp_user_white_hash | game_positions | 439 MB |
| ix_gp_full_hash_opening | game_positions | 339 MB |
| game_flaws_pkey | game_flaws | 218 MB |
| game_best_moves_pkey | game_best_moves | 128 MB |
| uq_games_user_platform_game_id | games | 104 MB |

**Storage summary:** `game_positions` alone is 12 GB (~57% of the DB), split almost evenly between heap (6.1 GB) and 5.9 GB of indexes — a ~0.97 index:data ratio, driven by the seven Zobrist/endgame/opening indexes that are the core of the position-matching design. `game_flaws` (5.4 GB) is heap-heavy (the PV-line blobs), with a lean 8% index footprint. Together the top three tables are >20 GB of the 21 GB total. Nothing anomalous — this is the expected shape for a Zobrist-hash position store.

## 2. Performance Analysis

### Buffer cache hit ratio

**99.96%** — excellent (>99%). `shared_buffers=2GB` is comfortably serving the working set. Stats last reset 2026-06-23, so this reflects ~30 days of cumulative activity.

### Slowest queries by avg time

The top of the "by avg time" list is **self-inflicted admin/diagnostic queries**, not app hot paths — including this report's own Check B coverage query (the 54s one) and several one-shot blob-backfill audit queries run manually. Filtering those out, the meaningful recurring app queries are:

| avg_ms | max_ms | calls | total_ms | query (truncated) |
|---|---|---|---|---|
| 12,636 | 18,272 | 20 | 252,728 | `SELECT DISTINCT game_positions.game_id … full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL … max(ply)` (tier-4b lottery scoping) |
| 5,845 | 26,479 | 5 | 29,224 | recent-capped per-user WDL window (analysis/stats) |
| 6,749 | 7,062 | 2 | 13,498 | `SELECT … FROM games WHERE platform_url = $1` (dedup lookup) |

The rest of the high-avg list is one-off (`calls`=1) maintenance/UPDATE migrations (accuracy backfill UPDATEs at 35–41s each, run once).

### Highest total time queries (server-time dominators)

| total_ms | calls | avg_ms | query (truncated) |
|---|---|---|---|
| **1,814,850,791** | 2,495,576 | 727 | user-selection: guests-excluded, has game_flaws with `allowed_pv_lines IS NULL` (**tier-4b blob-backfill lottery, QUEUE-08**) |
| 184,100,846 | 371,307 | 496 | user-selection: `full_pv_completed_at NOT NULL AND best_moves_completed_at IS NULL` (best-move backfill) |
| 20,322,640 | 322,802 | 63 | game-pick: per-user flaws-with-null-blob lottery |
| 7,748,802 | 7,815 | 992 | user-selection: needs-engine / lichess-pv composite |
| 6,051,161 | 278,588 | 22 | game-pick: best-move backfill lottery |

This is the headline: **the tier-4b blob-backfill user-selection query dominates total server time — 1.8 billion ms (~504 hours) across 2.5M calls at 727ms each.** It's the top consumer by a wide margin (10× the #2 query). This is the opportunistic backfill lottery polling constantly; it's a known, expected background load (see the "best-move backfill = two populations" and "tier-4 blob backfill" project notes), but it's also the single biggest optimization lever on the box.

### Sequential scan analysis

| Table | seq_scan | idx_scan | Verdict |
|---|---|---|---|
| games | 77,883 | 36.6 B | Fine — huge idx_scan dominance; seq scans are a rounding error |
| game_positions | 107 | 47.6 M | Fine — index-driven as intended |
| users | 14,665,276 | 6.3 M | **Expected** — 228-row table, seq scan is optimal; these are the constant queue `EXISTS(...)` user-selection scans |
| eval_jobs | 8,049,494 | 4.5 M | **Expected** — 227-row table, seq scan cheaper than index |
| oauth_account | 199,769 | 0 | Expected — 81-row table |

No action: every high-seq-scan table is tiny (<500 live rows) where PostgreSQL correctly prefers seq scans. The large tables are overwhelmingly index-served.

### Index usage — unused indexes

Genuinely-unused (0 scans) indexes, and whether they're droppable:

- `ix_gp_full_hash_opening` (339 MB, 2 scans) — **large and almost never used.** Candidate to review — but verify it isn't reserved for an opening-explorer path before dropping. Worth a closer look given its size.
- `ix_games_full_pv_pending` (22 MB, 0 scans) — partial pending-work index; **keep** (drains to 0 when backfill is caught up; used by the pipeline intermittently).
- `oauth_account` indexes (0 scans) — **keep** (OAuth login path, low traffic but correctness-critical).
- `ix_users_email` (2 scans) — **keep** (auth/login lookup).
- `llm_logs_*`, `feedback_*`, `openings_*`, `bot_game_settings_pkey`, `benchmark_cohort_cdf_pkey` (0 scans) — **keep** (PK/FK integrity or low-volume features; all tiny).

Only `ix_gp_full_hash_opening` is both large and effectively unused — everything else at 0 scans is either tiny or integrity/auth-required.

### Dead tuples / autovacuum

| Table | live | dead | dead % | last autovacuum |
|---|---|---|---|---|
| game_flaws | 3,602,549 | 197,960 | 5.2% | 2026-07-19 |
| games | 866,679 | 74,345 | 7.9% | 2026-07-23 |
| opening_position_eval | 1,939,815 | 19,976 | 1.0% | never (autoanalyze only) |
| users | 228 | 54 | — | never (tiny; autoanalyze runs) |
| eval_jobs | 227 | 59 | — | 2026-07-23 |

All dead-tuple ratios are healthy (<10%). Autovacuum is keeping up on the big churny tables (`games`, `game_flaws`, `game_positions` all vacuumed today). `opening_position_eval` has never been autovacuumed but its dead ratio is 1% — fine.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws` (lichess only)

- **NULL-count gap (`flaws_but_all_counts_null`): 0** ✓ — no lichess game has derived flaws with all count columns NULL.
- **Match rate:** 164,519 exact matches; 890 mistake-mismatches, 482 blunder-mismatches out of ~166k lichess games with counts present (>99% agreement).
- **Mismatch direction (Query 10):** slight `game_flaws` over-count vs lichess (mistakes: 775 over / 115 under; blunders: 352 over / 130 under).
- **Aggregate totals (the number that matters):**
  - Mistakes: lichess 497,820 vs game_flaws 498,767 (**+0.19%**)
  - Blunders: lichess 758,091 vs game_flaws 758,388 (**+0.04%**)

Aggregate totals agree to well within 1%; per-game drift is the expected disagreement between the two independent classifiers (lichess win% vs our ES thresholds).

**Verdict (Check A): PASS.**

### Check B — Eval coverage ≥90% vs oracle-column presence (Flaws Timeline gate)

| Platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| chess.com | 310,388 | **0** | 310,388 |
| lichess | 164,079 | **0** | 164,079 |
| flawchess | 53 | **0** | 53 |

`ge90_but_oracle_null = 0` on **every** platform — the Timeline's oracle-present gate drops no eval-covered game.

Notable (positive) deviation from the skill's stated expectation: **310k chess.com games now clear the 0.90 coverage bar AND have oracle columns fully populated.** The background note assumed chess.com would rarely clear 0.90 (sparse entry-ply evals only) and that oracle columns are lichess-only. Reality: our Stockfish backfill + oracle-column computation has caught chess.com up to full coverage with matching oracle data. This is healthy — no chess.com games are silently excluded from the Flaws Timeline.

**Verdict (Check B): PASS.**

## Summary

- **Size & shape:** 21 GB total. `game_positions` (12 GB, ~57%) and `game_flaws` (5.4 GB) dominate — expected for a 63.6M-position Zobrist store across 868k games. Index:data on `game_positions` is ~0.97 (seven hash/endgame/opening indexes), the deliberate cost of exact-position matching.
- **Health:** Cache hit 99.96% (excellent). Dead-tuple ratios all <10%, autovacuum current on the churny tables. No integrity issues — both sanity checks PASS (NULL-count gap 0, oracle-null 0 everywhere; flaw aggregates within 0.2%).
- **#1 server-time consumer:** the **tier-4b blob-backfill user-selection lottery** — 1.8 billion ms cumulative (~504h over 30 days) at 727ms × 2.5M calls, 10× the next query. Known/expected opportunistic backfill, but it's the single biggest optimization lever. If backfill throughput matters, this `WHERE is_guest=false AND EXISTS(game_flaws … allowed_pv_lines IS NULL)` user scan is where to look (it re-scans to find any user with a pending blob every poll).
- **Only droppable large index:** `ix_gp_full_hash_opening` (339 MB, 2 lifetime scans) — review whether any opening-explorer path still needs it before dropping. Everything else at 0 scans is tiny or auth/integrity-required (keep).
- **Positive surprise:** chess.com is now fully oracle-covered (310k games ≥90% coverage, 0 oracle-null), so the Flaws Timeline no longer silently drops chess.com games — contradicting the older assumption baked into the Check B background.
- **No urgent action required.** One thing worth monitoring/considering: the blob-backfill lottery's constant full re-scan cost, if you want to reduce background DB load.
