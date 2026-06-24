# FlawChess DB Report — 2026-06-24

- **DB**: prod
- **Snapshot taken**: 2026-06-24T06:02:17Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 158 | 79 | 79 |

### 10 most recent users

| User ID | chess.com? | lichess? | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 199 | yes | no | no | 2026-06-23 | 2026-06-23 | 5,965 | 365,627 |
| 197 | yes | no | yes | 2026-06-23 | 2026-06-23 | 863 | 52,163 |
| 196 | yes | no | no | 2026-06-23 | 2026-06-23 | 209 | 9,872 |
| 195 | yes | no | yes | 2026-06-23 | 2026-06-23 | 544 | 30,407 |
| 194 | yes | no | no | 2026-06-22 | 2026-06-22 | 9,282 | 649,589 |
| 193 | yes | no | no | 2026-06-21 | 2026-06-21 | 39 | 2,346 |
| 192 | yes | no | yes | 2026-06-21 | 2026-06-21 | 649 | 35,779 |
| 191 | no | no | yes | 2026-06-20 | 2026-06-20 | 0 | 0 |
| 190 | no | yes | yes | 2026-06-20 | 2026-06-20 | 891 | 49,452 |
| 189 | yes | no | no | 2026-06-20 | 2026-06-20 | 4,888 | 243,904 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 102 | 435,366 |
| lichess | 59 | 223,125 |

**Activity note.** 9 of the 10 most recent signups imported games (only user 191, a guest who linked no platform, has zero). The user base is an even split: 79 registered / 79 guests. chess.com dominates volume (~66% of games) and reach (102 vs 59 linked accounts) — most users link only one platform.

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 11 GB |
| Total games | 658,491 |
| Total positions | 48,162,374 |
| Avg positions / game | 73.1 |

### Per-table breakdown

| Table | Data size | Index size | Total size |
|---|---|---|---|
| game_positions | 4,685 MB | 3,691 MB | 8,376 MB |
| games | 1,791 MB | 506 MB | 2,297 MB |
| game_flaws | 384 MB | 253 MB | 637 MB |
| opening_position_eval | 69 MB | 74 MB | 143 MB |
| benchmark_cohort_cdf | 8.2 MB | 4.8 MB | 13 MB |
| openings | 832 kB | 888 kB | 1.7 MB |
| llm_logs | 32 kB | 992 kB | 1.0 MB |
| import_jobs | 216 kB | 408 kB | 624 kB |
| user_benchmark_percentiles | 200 kB | 112 kB | 312 kB |
| users | 48 kB | 88 kB | 136 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| eval_jobs | 16 kB | 96 kB | 112 kB |
| oauth_account | 32 kB | 80 kB | 112 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| feedback | 8 kB | 40 kB | 48 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,449 MB |
| ix_gp_user_endgame_game | game_positions | 654 MB |
| ix_gp_user_full_hash_move_san | game_positions | 529 MB |
| ix_game_positions_game_id | game_positions | 323 MB |
| ix_gp_user_white_hash | game_positions | 282 MB |
| ix_gp_user_black_hash | game_positions | 280 MB |
| game_flaws_pkey | game_flaws | 174 MB |
| ix_gp_full_hash_opening | game_positions | 172 MB |
| uq_games_user_platform_game_id | games | 81 MB |
| opening_position_eval_pkey | opening_position_eval | 74 MB |
| ix_game_flaws_game_id | game_flaws | 46 MB |
| ix_games_user_played_at | games | 44 MB |
| ix_game_flaws_user_severity | game_flaws | 33 MB |
| games_pkey | games | 31 MB |
| uq_games_id_user_id | games | 31 MB |

**Storage summary.** `game_positions` is the whole story: 8.4 GB total (76% of the 11 GB DB), split 4.7 GB data + 3.7 GB indexes (idx/data ratio 0.79). Six indexes on that table account for ~2.3 GB combined on top of the 1.4 GB PK. `games` adds another 2.3 GB. Everything else is rounding error. Index footprint is reasonable for the query patterns; the two unused `white_hash`/`black_hash` indexes (562 MB combined) are the one place worth a second look (see Performance §5).

## 2. Performance Analysis

> `pg_stat_statements` was last reset **2026-06-23T20:35:32Z** — cumulative stats cover only ~9.5 hours, so totals reflect a short recent window, not long-run behavior.

### 1. Buffer cache hit ratio

**99.71%** — excellent. Working set is comfortably resident in `shared_buffers` (2 GB).

### 2. Slowest queries by avg time

Most of the top "slow" entries are one-off maintenance/admin statements (VACUUM, CREATE INDEX) and this report's own count queries — not application hot paths. Filtering to real application queries:

| avg_ms | max_ms | calls | total_ms | query |
|---|---|---|---|---|
| 1,167 | 1,370 | 2 | 2,334 | opening explorer: per-move WDL aggregation over `game_positions`/`games` (entry_hash, move_san) |
| 508 | 508 | 1 | 508 | game_flaws aggregate (severity/tempo/phase FILTER counts) |
| 222 | 222 | 1 | 222 | flaw-trend per-game mistake/blunder rollup |
| 141 | 1,315 | 14 | 1,980 | opening explorer dedup CTE (DISTINCT ON full_hash) |
| 106 | 1,389 | 22 | 2,330 | opening insights: per-(eco,name) WDL over user games |
| 99 | 974 | 14 | 1,389 | move-tree WDL (gp1→gp2 transition counts) |
| 88 | 1,366 | 24 | 2,118 | opening explorer dedup CTE (variant) |

The opening-explorer/insights family dominates application latency. Per-call averages are tens-to-hundreds of ms but the max values (1.3–1.4 s) show cold-cache tail latency. These scale with a single user's `game_positions` rows, so the heaviest users (9k games / 650k positions) drive the tail.

### 3. Highest total-time queries

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 3,378,057 | 101,156 | 33.39 | eval-queue scan: `games` needing engine eval (`full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL`, non-guest) |
| 33,206 | 101,155 | 0.33 | eval-queue: users with pending non-guest analysis |
| 8,498 | 101,156 | 0.08 | eval_jobs candidate pick CTE |
| 5,847 | 94,454 | 0.06 | entry-eval lease probe |
| 4,560 | 101,156 | 0.05 | eval_jobs lease-expiry UPDATE |
| 1,150 | 6,701 | 0.17 | import-jobs in-progress count |

**The eval-queue scan is the single biggest consumer of server time by a wide margin** — 3.38M ms total over 101k calls in a ~9.5h window (~3 calls/sec, 33 ms each). This is the background worker polling for games to analyze. It uses `ix_games_pv_backfill_pending` / `ix_games_needs_engine_full_evals` (7M+ scans each, see below), so it's index-driven, but 33 ms/call at this frequency is the obvious optimization target if analysis throughput or DB CPU ever becomes a concern.

### 4. Sequential scan analysis

| Table | seq_scan | idx_scan | n_live_tup | Verdict |
|---|---|---|---|---|
| games | 34,840 | 16,683,265 | 656,435 | seq_tup_read 7.6B is high, but idx_scan dominates 478:1 — watch, see below |
| game_positions | 3 | 754,584 | 48,162,374 | Healthy — fully index-driven |
| users | 225,863 | 9,183 | ~158 | Expected — tiny table, seq scan is optimal |
| eval_jobs | 303,489 | 196 | small | Expected — tiny hot queue table |
| import_jobs | 6,817 | 40 | small | Expected — tiny table |
| openings | 24 | 0 | 3,641 | Expected — small lookup, fully cached |

`games` is the only large table doing meaningful sequential scans (34.8k of them, 7.6B tuples read). At ~656k rows, each full seq scan reads the whole table, so 34.8k scans is where most of that 7.6B comes from. Worth confirming which query plans choose a seq scan over the available indexes (likely the broad eval-queue / count aggregates), but the cache hit ratio (99.7%) means these stay in memory and aren't causing disk pressure today.

### 5. Index usage

**Unused indexes (0 scans this window):**

| Index | Table | Size | Recommendation |
|---|---|---|---|
| ix_gp_user_white_hash | game_positions | 282 MB | **Consider dropping** — "my pieces only" (white) system-opening filter; if that feature is live but unused, it's 282 MB idle |
| ix_gp_user_black_hash | game_positions | 280 MB | **Consider dropping** — same, black side |
| ix_gp_full_hash_opening | game_positions | 172 MB | Investigate — opening-explorer path; expected to be used, 0 scans is surprising |
| ix_games_full_evals_pending | games | 18 MB | Keep — eval-queue partial index, likely used in other windows |
| ix_games_full_pv_pending | games | 20 MB | Keep — PV backfill partial index |
| uq_openings_eco_name_pgn, ix_openings_eco_name | openings | <1 MB | Keep — uniqueness/lookup integrity |
| oauth/llm_logs/feedback/bookmark indexes | various | 16 kB each | Keep — FK/auth/integrity, trivially small |

The three `game_positions` hash indexes (734 MB combined: white_hash 282 + black_hash 280 + full_hash_opening 172) are the only large unused indexes. **Caveat:** stats are only ~9.5h old (reset 2026-06-23 20:35Z), so a feature exercised less than daily (system-opening filter, opening explorer deep-links) could legitimately show 0 scans. Do **not** drop these on this window alone — reset stats, let them run a full week of real traffic, then re-check. If still 0 after 7 days, `ix_gp_user_white_hash` + `ix_gp_user_black_hash` (562 MB) are the highest-value drop candidates.

**Heavily used indexes** (confirming the hot paths): `ix_games_needs_engine_full_evals` (8.0M scans) and `ix_games_pv_backfill_pending` (7.1M scans) serve the eval-queue worker; `uq_games_id_user_id` (1.5M), `game_positions_pkey` (650k), and `ix_game_positions_game_id` (95.7k) serve game/position lookups.

### 6. Dead tuples / autovacuum

All tables show **near-zero dead tuples** (games: 15, users: 22, oauth: 3, rest 0). No bloat. `last_autovacuum` / `last_autoanalyze` read NULL across the board — consistent with the recent manual `VACUUM ANALYZE games` / `VACUUM ANALYZE game_positions` (visible in the slow-query log) having reset the counters, or autovacuum stats being cleared. No action needed; dead-tuple ratios are excellent.

### Performance recommendations

- **No action needed** — Cache hit 99.71%, zero table bloat, `game_positions` (the 48M-row table) is fully index-driven with only 3 lifetime seq scans. The big tables are healthy.
- **Monitor** — (1) The eval-queue scan dominates total server time (3.38M ms / 9.5h). It's index-backed and individually cheap (33 ms), but it's the first thing to optimize if analysis throughput or DB CPU climbs. (2) `games` seq scans (34.8k, 7.6B tuples) — confirm which plans pick seq over index. (3) Stats are only ~9.5h old; re-check after a full week before acting on "unused" indexes.
- **Consider** — After a 7-day stats window, if `ix_gp_user_white_hash` (282 MB) and `ix_gp_user_black_hash` (280 MB) are still at 0 scans, drop them to reclaim ~562 MB and cut write amplification on the largest table. Verify the "my pieces only" system-opening filter is the only consumer first.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws` (lichess only)

| Metric | Value |
|---|---|
| lichess games with flaws | 138,004 |
| **flaws_but_all_counts_null** | **0** ✅ |
| exact_match | 138,733 |
| mistake_mismatch | 1,331 (0.96%) |
| blunder_mismatch | 756 (0.54%) |

Mismatch direction & aggregate totals (Query 10):

| Metric | Value |
|---|---|
| mistakes: gf under / over lichess | 212 / 1,119 |
| blunders: gf under / over lichess | 191 / 565 |
| total lichess mistakes vs gf | 424,235 vs 425,517 (+0.30%) |
| total lichess blunders vs gf | 641,037 vs 641,555 (+0.08%) |

**Verdict: PASS.** The headline NULL-count gap is **0** — no lichess game has derived flaws with unpopulated source columns. Per-game match rate is ~99% (only 0.96% / 0.54% of games disagree on mistakes / blunders), and aggregate totals agree within 0.3% (mistakes) and 0.08% (blunders). The small drift is `game_flaws` slightly over-counting relative to lichess (1,119 over vs 212 under on mistakes), which is expected independent-classifier disagreement (our Option-B ES thresholds vs lichess win%, plus the known mate-ladder path), not a bug.

### Check B — Eval coverage ≥90% vs oracle-column presence (Flaws Timeline gate)

| Platform | Games ≥90% coverage | **ge90_but_oracle_null** | Oracle present |
|---|---|---|---|
| chess.com | 281,661 | **0** ✅ | 281,661 |
| lichess | 139,078 | **0** ✅ | 139,078 |

**Verdict: PASS.** `ge90_but_oracle_null = 0` on both platforms — every game with ≥90% per-ply eval coverage also has its oracle columns populated, so the Flaws Timeline's oracle-present gate drops nothing. Notably, **281,661 chess.com games now clear the 0.90 coverage bar with oracle columns present** — full-game Stockfish backfill has landed broadly on chess.com and the oracle columns were backfilled alongside it, exactly the case the check warns could otherwise go silently missing. No gap.

## Summary

- **Size**: 11 GB total. `game_positions` (48.2M rows, 73 positions/game) is 8.4 GB / 76% of the DB; `games` adds 2.3 GB. Everything else is negligible.
- **Health**: Excellent. Cache hit 99.71%, near-zero dead tuples, large tables fully index-driven. No bloat, no urgent action.
- **Top server-time consumer**: the background eval-queue scan (3.38M ms over 101k calls in ~9.5h). Index-backed and cheap per call (33 ms), but it's the #1 optimization target if DB CPU or analysis throughput ever pressures.
- **Largest idle indexes**: `ix_gp_user_white_hash` + `ix_gp_user_black_hash` (562 MB combined, 0 scans). **Do not drop yet** — stats are only ~9.5h old (reset 2026-06-23 20:35Z). Re-check after a full week; if still unused, dropping reclaims ~562 MB and reduces write cost on the biggest table.
- **Sanity checks**: both **PASS**. Flaw-count integrity is clean (0 NULL-count gaps, ~99% match, aggregates within 0.3%). Flaws Timeline gate loses no eval-covered games on either platform; chess.com Stockfish backfill (281k games) is now fully reflected in the oracle columns.
- **Users**: 158 total (79 registered / 79 guests). chess.com leads on both volume (435k games) and reach (102 linked accounts). 9 of 10 recent signups imported games.
