# FlawChess DB Report — 2026-07-07

- **DB**: prod
- **Snapshot taken**: 2026-07-07T07:21:00Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 188 | 97 | 91 |

### 10 most recent users

| User | chess.com | lichess | Guest? | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 229 | ✓ | – | no | 2026-07-06 | 2026-07-06 | 249 | 14,062 |
| 228 | ✓ | – | no | 2026-07-06 | 2026-07-06 | 1,179 | 67,494 |
| 227 | ✓ | – | no | 2026-07-06 | 2026-07-06 | 216 | 9,590 |
| 226 | ✓ | – | no | 2026-07-05 | 2026-07-05 | 1,353 | 99,538 |
| 225 | ✓ | ✓ | yes | 2026-07-04 | 2026-07-04 | 10,060 | 663,975 |
| 224 | – | ✓ | no | 2026-07-04 | 2026-07-04 | 5,185 | 362,546 |
| 223 | ✓ | – | yes | 2026-07-04 | 2026-07-04 | 420 | 22,528 |
| 222 | – | – | no | 2026-07-03 | 2026-07-03 | 0 | 0 |
| 221 | – | – | no | 2026-07-03 | 2026-07-03 | 0 | 0 |
| 220 | ✓ | – | no | 2026-07-03 | 2026-07-03 | 930 | 44,508 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 124 | 471,179 |
| lichess | 66 | 237,953 |

**Activity note:** 97 registered vs 91 guest users (roughly even). Of the 10 most recent signups, 8 imported games and 2 (users 221, 222, both registered, no platform linked) never linked an account or imported anything. chess.com is the dominant platform by games (~66% of all games, 2× lichess). Guest user 225 is by far the heaviest importer in the recent window (10k games, both platforms linked).

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 15 GB |
| Total games | 709,132 |
| Total positions | 51,456,183 |
| Avg positions / game | ~72.6 |

### Per-table breakdown (top consumers)

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 5,123 MB | 4,405 MB | 9,527 MB |
| game_flaws | 3,120 MB | 402 MB | 3,522 MB |
| games | 1,791 MB | 574 MB | 2,365 MB |
| opening_position_eval | 80 MB | 74 MB | 154 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| openings | 0.8 MB | 0.9 MB | 1.7 MB |
| llm_logs | 40 kB | 1.4 MB | 1.4 MB |

All other tables are < 1 MB. `game_positions` + `game_flaws` + `games` account for **~15.4 GB of the 15 GB total** (essentially the whole DB).

### Per-index breakdown (top consumers)

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,716 MB |
| ix_gp_user_endgame_game | game_positions | 794 MB |
| ix_gp_user_full_hash_move_san | game_positions | 615 MB |
| ix_game_positions_game_id | game_positions | 398 MB |
| ix_gp_user_white_hash | game_positions | 333 MB |
| ix_gp_user_black_hash | game_positions | 332 MB |
| ix_gp_full_hash_opening | game_positions | 216 MB |
| game_flaws_pkey | game_flaws | 209 MB |
| uq_games_user_platform_game_id | games | 85 MB |
| opening_position_eval_pkey | opening_position_eval | 74 MB |

**Storage summary:** `game_positions` dominates at 9.5 GB (62% of the DB), split ~54% data / 46% index — a heavy index-to-data ratio driven by the seven Zobrist-hash / endgame / opening lookup indexes that power position matching. That's expected for this schema (indexed integer-equality lookups are the core architecture), not bloat. `game_flaws` is the opposite profile: 3.1 GB of data with only 402 MB of indexes, mostly the JSONB PV blobs.

## 2. Performance Analysis

### Buffer cache hit ratio

**99.95%** — excellent (>99%). Stats last reset 2026-06-23, so ~2 weeks of accumulated activity back this.

### Slowest queries by avg time

Most of the very-slow entries are **one-off diagnostic/report queries** (single `calls`, the `db-report` sanity CTE, blob-backfill audits) — not production hot paths. The one recurring slow query that matters:

| avg_ms | calls | total_ms | rows | Query |
|---|---|---|---|---|
| 12,094 | 10 | 120,935 | 400 | `SELECT DISTINCT game_positions.game_id … full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL … max(ply) …` (PV-backfill candidate scan) |

At ~12 s/call this is a real full-scan-flavored query, but with only 10 calls it isn't a server-wide burden yet. Everything else averaging >2 s was a single ad-hoc call.

### Highest total time queries (server-time dominators)

| total_ms | calls | avg_ms | Query |
|---|---|---|---|
| **97,349,598** (~27 h) | 245,296 | 396.87 | `SELECT u.id FROM users … NOT guest AND EXISTS (games JOIN game_flaws … allowed_pv_lines IS NULL)` — tier-3 blob-backfill eligibility poll |
| 8,161,510 (~2.3 h) | 154,277 | 52.90 | `SELECT g.id … full_evals_completed_at IS NOT NULL AND EXISTS(game_flaws … allowed_pv_lines IS NULL) ORDER BY -ln(random())/…` — per-user lottery pick |
| 4,840,246 (~1.3 h) | 91,019 | 53.18 | same lottery pick, variant |
| 300,670 | 447,232 | 0.67 | `game_positions.ply, pv WHERE game_id/user_id/ply IN (…)` |
| 294,639 | 1,698,370 | 0.17 | `UPDATE game_flaws SET allowed_tactic_motif=… missed_tactic_motif=…` (tactic tagging) |

The **tier-3 eligibility poll dominates all server time** — 27 cumulative hours over ~245k calls at ~400 ms each. This is the global blob-backfill lottery gate probing "which non-guest users still have ungated flaws." It's inherent to the ongoing tier-4 blob backfill (which is still filling opportunistically) and will quiet down as `allowed_pv_lines IS NULL` flaws drain. Not a bug, but it's the single biggest optimization lever if backfill throughput ever needs headroom.

### Sequential scan analysis

| Table | seq_scan | idx_scan | Verdict |
|---|---|---|---|
| users | 8,083,114 | 2,493,369 | Fine — 188 rows, seq scan is optimal |
| eval_jobs | 7,676,967 | 639,912 | Fine — 183 rows, seq scan is optimal |
| games | 69,872 | 15.35 B | Mostly indexed; see note |
| game_positions | 61 | 27.0 M | Healthy — 51M-row table, effectively never seq-scanned |
| game_flaws | 176 | 13.57 B | Healthy |
| import_jobs / oauth_account | ~140k–170k | low | Fine — tiny tables |

`games` did 69,872 seq scans reading ~15.6 B tuples. Almost all `games` access is indexed (15.35 B idx scans), so this is a small fraction — but note the ad-hoc `SELECT * FROM games WHERE platform_url = $1` (6.7 s avg, 2 calls) has **no index on `platform_url`** and full-scans the 1.8 GB table. Only 2 calls so far; if that access pattern becomes routine it warrants an index.

### Index usage

- **Zero-scan indexes** are all either keep-by-obligation (PKs, FK-integrity, auth/OAuth lookups `ix_users_email`, `ix_oauth_account_*`, `uq_openings_eco_name_pgn`) or tiny (`llm_logs`, `feedback`, `user_activity` — all < 40 kB). Nothing worth dropping.
- **Large-but-lightly-used:** `ix_gp_user_white_hash` (333 MB, 20 scans), `ix_gp_user_black_hash` (332 MB, 55 scans), `ix_gp_full_hash_opening` (216 MB, 2 scans). These back the **"my pieces only" system-opening filter** and the opening explorer — low scan counts reflect a lower-traffic feature, not a dead index. **Keep** (dropping would break a core product query path and cost ~880 MB to rebuild).
- `ix_games_full_pv_pending` (20 MB, 0 scans) is a partial backfill index; keep until the PV backfill fully completes.

### Dead tuples / autovacuum

All healthy. Highest ratios: `users` 48/188 (25%, but 188 rows — negligible), `game_flaws` 225k/3.53M (6.4%), `game_positions` 1.1M/51.5M (2.1%). Autovacuum/autoanalyze are running recently on all hot tables (game_flaws vacuumed 2026-07-07, game_positions analyzed 2026-07-06). No action needed.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws` (lichess)

| Metric | Value |
|---|---|
| Lichess games with flaws | 147,975 |
| **flaws_but_all_counts_null** | **0** ✅ |
| Exact match (counts present) | 148,918 |
| Mistake mismatches | 1,277 |
| Blunder mismatches | 717 |

Match rate ≈ **148,918 / ~150,912 ≈ 98.7%** of counts-present games (the two classifiers are independent, so minor per-game drift is expected).

**Mismatch direction & aggregate totals (Query 10):**

| | game_flaws under | game_flaws over |
|---|---|---|
| Mistakes | 200 | 1,077 |
| Blunders | 178 | 539 |

| Aggregate | lichess counts | game_flaws | Δ |
|---|---|---|---|
| Mistakes | 452,387 | 453,612 | +0.27% |
| Blunders | 685,050 | 685,532 | +0.07% |

`game_flaws` slightly over-counts vs lichess on both (consistent with the known mate-ladder / ES-threshold drift), but aggregate totals agree to **well within 1%**.

**Verdict A: PASS** — no NULL-count gap, aggregates within 1%.

### Check B — Eval coverage ≥90% vs oracle-column presence (Flaws Timeline gate)

| Platform | games ≥90% coverage | ge90_but_oracle_null | ge90 oracle present |
|---|---|---|---|
| chess.com | 303,106 | **0** ✅ | 303,106 |
| lichess | 149,134 | **0** ✅ | 149,134 |

**Verdict B: PASS** — the Timeline's oracle-present gate drops zero eval-covered games.

**Notable shift:** unlike prior snapshots (where chess.com games rarely cleared the 0.90 coverage gate because their evals were sparse entry-ply only), **303k chess.com games now have ≥90% full-ply coverage *and* populated oracle columns**. The full-game Stockfish backfill has landed broadly on chess.com, and oracle columns tracked it — no games fell into the "analyzed but invisible to the Timeline" hole this check guards against. Good state.

## Summary

- **DB is 15 GB**, 709k games / 51.5M positions. `game_positions` (9.5 GB) + `game_flaws` (3.5 GB) + `games` (2.4 GB) are essentially the entire database. The large index footprint on `game_positions` (4.4 GB across 7 hash/endgame/opening indexes) is architectural, not bloat.
- **Cache hit 99.95%**, dead-tuple ratios low, autovacuum current — health is excellent.
- **One query dominates server time:** the tier-3 blob-backfill eligibility poll (`is_guest = false AND EXISTS ungated flaws`) at ~27 cumulative hours over 245k calls. Inherent to the ongoing tier-4 blob backfill; it self-quiets as `allowed_pv_lines IS NULL` flaws drain. The main lever if backfill needs more headroom.
- **Both sanity checks PASS.** Flaw counts agree with `game_flaws` within 0.3% in aggregate (no NULL-count gap); the Flaws Timeline gate loses zero eval-covered games on either platform.
- **Notable:** 303k chess.com games now clear ≥90% eval coverage with oracle columns present — the full-game Stockfish backfill has reached chess.com broadly, closing the historical "sparse chess.com evals" gap.
- **Minor watch items (no action needed now):** `platform_url` lookups on `games` are un-indexed and full-scan the 1.8 GB table (only 2 calls so far); the `game_positions` `full_evals/lichess_evals` PV-backfill scan runs ~12 s/call (only 10 calls). Both are fine at current volume.
