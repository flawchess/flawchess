# FlawChess DB Report — 2026-06-17

- **DB**: prod
- **Snapshot taken**: 2026-06-17T16:19:41Z
- **Sections run**: users / storage / performance / sanity
- **Context**: prod has been under sustained load for ~2 days — 4 import workers + tier-3 Stockfish eval drain. `pg_stat_statements` was last reset 2026-06-15T16:24Z, so cumulative perf stats cover almost exactly the hammering window.

## Server Health (host snapshot)

| Metric | Value | Verdict |
|---|---|---|
| Uptime | 12 days, load avg 4.02 / 4.05 / 3.89 (8 vCPU) | ✅ ~50% of cores — expected with 4 workers + eval drain |
| RAM | 5.8Gi used / 9.5Gi available / 15Gi total | ✅ healthy headroom, no pressure |
| Swap | 418Mi used / 4.0Gi | ✅ minimal, no thrash |
| Disk | 26G used / 150G (18%) | ✅ plenty free |
| Containers | backend (20h), db (21h, healthy), caddy (20h), umami (12d) | ✅ all up |

No OOM events; the historical import-OOM failure mode is not recurring under this workload.

## 0. Users Overview

| Total users | Registered | Guests |
|---|---|---|
| 143 | 71 | 72 |

### 10 most recent users

| ID | chess.com | lichess | guest | Registered | Last login | Games | Positions |
|---|---|---|---|---|---|---|---|
| 183 | ✅ | — | no | 2026-06-17 | 2026-06-17 | 754 | 51,195 |
| 182 | ✅ | — | no | 2026-06-16 | 2026-06-16 | 4,635 | 278,386 |
| 181 | ✅ | — | yes | 2026-06-16 | 2026-06-16 | 3,085 | 229,677 |
| 180 | ✅ | — | yes | 2026-06-16 | 2026-06-16 | 5,655 | 304,420 |
| 179 | ✅ | — | no | 2026-06-15 | 2026-06-15 | 5,801 | 409,770 |
| 178 | ✅ | — | no | 2026-06-15 | 2026-06-15 | 189 | 12,298 |
| 177 | ✅ | — | yes | 2026-06-15 | 2026-06-15 | 189 | 12,298 |
| 176 | ✅ | — | no | 2026-06-15 | 2026-06-15 | 1,684 | 101,623 |
| 175 | ✅ | — | no | 2026-06-13 | 2026-06-13 | 2,862 | 204,143 |
| 174 | ✅ | — | yes | 2026-06-11 | 2026-06-11 | 711 | 38,474 |

### Platform breakdown

| Platform | Users | Games |
|---|---|---|
| chess.com | 92 | 411,362 |
| lichess | 57 | 212,215 |

**Activity note:** All 10 recent signups imported games (no dead signups), every one chess.com-only. Roughly even guest/registered split (72/71). chess.com dominates 2:1 by games.

## 1. Storage Report

| Metric | Value |
|---|---|
| Database size | 13 GB |
| Total games | 623,577 |
| Total positions | 46,033,136 |
| Avg positions/game | 73.8 |

### Per-table breakdown

| Table | Data | Index | Total |
|---|---|---|---|
| game_positions | 6,130 MB | 4,417 MB | 10 GB |
| games | 1,791 MB | 491 MB | 2,282 MB |
| game_flaws | 111 MB | 82 MB | 194 MB |
| benchmark_cohort_cdf | 8,184 kB | 4,784 kB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 24 kB | 912 kB | 936 kB |
| import_jobs | 216 kB | 408 kB | 624 kB |
| (remaining tables) | — | — | < 300 kB each |

### Largest indexes

| Index | Table | Size |
|---|---|---|
| game_positions_pkey | game_positions | 1,711 MB |
| ix_gp_user_endgame_game | game_positions | 860 MB |
| ix_gp_user_full_hash_move_san | game_positions | 603 MB |
| ix_game_positions_game_id | game_positions | 397 MB |
| ix_gp_user_white_hash | game_positions | 326 MB |
| ix_gp_user_black_hash | game_positions | 324 MB |
| ix_gp_full_hash_opening | game_positions | 192 MB |
| uq_games_user_platform_game_id | games | 75 MB |
| game_flaws_pkey | game_flaws | 55 MB |

**Storage notes:** `game_positions` is 77% of the DB (10 GB of 13 GB), as expected for a 46M-row position store. Its index footprint (4.4 GB) is 0.72× its data — heavy but justified: 7 indexes serve the Zobrist hash lookups (white/black/full hash), endgame queries, and opening matching that are the product's core. The 10 GB hot table dwarfs `shared_buffers=2GB`, which directly explains the depressed cache-hit ratio below.

## 2. Performance Analysis

### Buffer cache hit ratio: **70.95%** ⚠️ (investigate-band, but explained)

Below the 95% "good" floor, but this is a **workload artifact, not a regression**. Stats were reset 2026-06-15T16:24Z and the entire window since has been the 4-worker import + tier-3 eval drain. That drain streams the full 10 GB `game_positions` table (and a 0.72× index layer) through a 2 GB `shared_buffers` repeatedly — large sequential/index scans that can't stay resident will always miss. The 278-billion `seq_tup_read` on `game_positions` confirms heavy full-table churn. Under normal user-facing traffic the working set is far smaller and the ratio would recover. Worth a re-check once the drain finishes.

### Top time-consuming queries (by total time since 2026-06-15 reset)

| Total (ms) | Calls | Avg (ms) | Query |
|---|---|---|---|
| 89,005,265 | 10,655 | 8,353 | `DISTINCT ON (full_hash) … eval_cp, eval_mate, best_move` — **eval-reuse cache lookup** |
| 3,112,955 | 23 | 135,346 | `count(*) FILTER … game_flaws.severity/tempo …` — flaw-aggregate (benchmark/insights) |
| 2,142,675 | 98,428 | 21.8 | drain candidate scan: `games WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` |
| 498,328 | 2,501,095 | 0.20 | `UPDATE game_positions SET eval_cp/eval_mate/best_move` — drain write-back |
| 475,153 | 7,393 | 64.3 | `COPY game_positions` — import bulk load |
| 328,435 | 21 | 15,640 | flaw-aggregate (second variant) |

### Slowest by average (the real optimization targets)

1. **Flaw-severity/tempo aggregate — 135 s avg, max 2,965 s (49 min!), 23 calls.** This is the single worst per-call query. Low call count so total impact is bounded, but a 49-minute worst case is a real outlier. Likely a full `game_flaws` ⋈ `games` aggregate for benchmark/insights computation running concurrently with the drain (contending for the same buffers). Candidate for EXPLAIN review when load subsides.
2. **Eval-reuse `DISTINCT ON (full_hash)` — 8.4 s avg, 10,655 calls, 89M ms total (~24.7 h cumulative).** Dominates total server time. This is the drain checking for an existing eval at the same position hash before spending Stockfish on it — exactly the dedup that makes the drain efficient, so the cost is "by design," but it's the biggest lever if the drain ever needs to go faster.

### Sequential scan analysis

| Table | seq_scan | idx_scan | Verdict |
|---|---|---|---|
| game_positions | 18,289 | 901,846,661 | ✅ index-dominated; seq scans are the drain's bulk reads |
| users | 1,601,773 | 12,650 | ✅ 143-row table — seq scan is optimal, ignore |
| games | 93 | 7,709,886,904 | ✅ overwhelmingly indexed |
| eval_jobs | 399,323 | 3,373 | ✅ 77-row table — seq scan optimal |
| oauth_account | 32,469 | 0 | ✅ 1-row table — fine |

No problematic seq-scan patterns. The high-count tables (`users`, `eval_jobs`, `oauth_account`) are all tiny, where Postgres correctly prefers seq scans.

### Index usage / unused indexes

Zero-scan indexes since the 2026-06-15 reset, all **keep**:
- `ix_games_full_evals_pending`, `ix_games_full_pv_pending` (18–20 MB) — partial drain-support indexes; the per-user drain candidate scan currently uses a different path, but these back the global-pending queries. Keep.
- `eval_jobs` `ix_eval_jobs_leased` / `ix_eval_jobs_pick`, `ix_users_email`, `oauth_account` / `llm_logs` / `openings` / `feedback` / `position_bookmarks` indexes — all on tiny tables or required for auth/FK/PK integrity. Keep regardless of scan count.

No index is both large and genuinely droppable. (Only-2-day stats window means "0 scans" mostly reflects which queries ran during the drain, not true deadness.)

### Dead tuples / autovacuum

- `game_positions`: 1.24M dead / 46.0M live = **2.6%** ✅ — well under the 20% threshold despite millions of drain UPDATEs; autovacuum ran 2026-06-17T08:47Z, autoanalyze 15:36Z. Keeping up nicely under load.
- `games`: 12,216 dead / 755,127 live = 1.6% ✅, autovacuumed 14:02Z.
- `game_flaws`: 0 dead ✅.
- All hot tables analyzed today. Autovacuum is healthy under the sustained write load.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws` — ✅ PASS

- **NULL-count gap (`flaws_but_all_counts_null`): 0** ✅ — no lichess game has derived flaws with NULL source counts.
- **Match rate: 99.04%** (57,449 exact / 58,008 lichess games with flaws). Mismatches: 1,505 mistake, 801 blunder — expected independent-classifier drift.
- **Aggregate totals (within ~1%):**
  - Mistakes: 169,564 (lichess) vs 170,975 (game_flaws) → **+0.83%**
  - Blunders: 264,394 vs 264,917 → **+0.20%**
  - `game_flaws` runs slightly over on mistakes (1,297 over / 208 under) and blunders (612 over / 189 under) — consistent with the known mate-ladder drift, no NULL gaps.

**Verdict: PASS** (NULL gap = 0, aggregates well within 1%).

### Check B — Eval coverage vs oracle-column presence (Flaws Timeline gate) — ✅ PASS

| Platform | Games ≥90% coverage | ge90 but oracle NULL | ge90 oracle present |
|---|---|---|---|
| chess.com | 82,773 | **0** | 82,773 |
| lichess | 58,912 | **0** | 58,912 |

**Notable shift from prior snapshots:** chess.com now shows 82,773 games clearing the 0.90 eval-coverage gate — historically this was near-zero because chess.com evals were sparse (entry-ply only). The tier-3 Stockfish drain has backfilled full per-ply coverage on these games **and** populated their oracle columns (`ge90_but_oracle_null = 0`). This is exactly the good outcome the check was designed to catch the failure of: the drain isn't leaving fully-analyzed chess.com games invisible to the Flaws Timeline.

**Verdict: PASS** (`ge90_but_oracle_null = 0` on both platforms — the Timeline's oracle-present gate loses no eval-covered games).

## Eval Drain Progress (tier-3)

| Metric | Value |
|---|---|
| Games full-evals done | 129,843 / 623,577 (20.8%) |
| Full PV done | 104,229 |
| Engine evals still pending (no lichess freebie) | 480,146 |
| lichess freebie evals | 39,332 |
| **Completed last 1h** | 2,075 |
| **Completed last 24h** | 54,877 |
| **Completed last 48h** | 91,855 |
| eval_jobs | 77 completed (queue drained) |
| import_jobs | 222 completed, 22 failed |

At ~50k games/day the remaining ~480k engine evals are roughly **9–10 days** out at current throughput. The 22 failed import jobs are worth a glance but aren't blocking the drain.

## Summary

**Overall: healthy under sustained 2-day load. No action required.**

- **Server**: load ~4/8 cores, 9.5Gi RAM free, swap barely touched, disk 18%, all containers up. The historical import-OOM failure mode is not recurring — the workload is comfortably within the CPX42 envelope.
- **Storage**: 13 GB total, 77% in `game_positions` (46M rows, 10 GB). Index footprint is heavy (0.72×) but every index earns its keep (Zobrist hashes, endgame, openings). Growing steadily with imports; no bloat.
- **Performance**: cache-hit ratio **70.95%** looks alarming but is a direct artifact of the eval drain streaming a 10 GB table through 2 GB `shared_buffers` — re-check after the drain finishes rather than retuning. Autovacuum is keeping dead-tuple ratios low (2.6% on `game_positions`) despite millions of UPDATEs.
- **Watch item**: the flaw-severity/tempo aggregate query (135 s avg, 49 min max) is the one genuine outlier — worth an EXPLAIN review once load subsides, though its low call count bounds the damage. The eval-reuse `DISTINCT ON (full_hash)` lookup is the top total-time consumer (~24.7 h cumulative) but is the dedup that keeps the drain efficient.
- **Sanity**: both integrity checks **PASS**. Notably, the drain has backfilled 82,773 chess.com games to full eval coverage *with* oracle columns populated (zero Timeline-gate gaps) — a real improvement over prior snapshots where chess.com coverage was sparse.
- **Drain**: 20.8% of games fully evaluated, ~50k/day, ~9–10 days of runway left. Steady and on track.
