# FlawChess DB Report — 2026-09-16

- **DB**: prod
- **Snapshot taken**: 2026-09-16T09:20:00Z
- **Sections run**: users / storage / performance / sanity
- **pg_stat stats_reset**: 2026-06-23T20:35:32Z (cumulative window ≈ 12 weeks)

## 0. Users Overview

| total users | registered | guests |
|---|---|---|
| 778 | 318 | 460 |

**10 most recent users**

| id | chess.com | lichess | guest | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 820 | yes | yes | no | 2026-09-16 | 2026-09-16 | 4,423 | 341,424 |
| 819 | no | no | yes | 2026-09-15 | 2026-09-15 | 0 | 0 |
| 818 | no | yes | no | 2026-09-15 | 2026-09-15 | 2,026 | 159,360 |
| 817 | no | no | yes | 2026-09-14 | 2026-09-14 | 0 | 0 |
| 816 | yes | no | no | 2026-09-14 | 2026-09-14 | 431 | 31,889 |
| 815 | yes | no | yes | 2026-09-14 | 2026-09-14 | 57 | 2,842 |
| 814 | yes | no | no | 2026-09-14 | 2026-09-14 | 1,000 | 64,899 |
| 813 | yes | no | yes | 2026-09-14 | 2026-09-14 | 2,000 | 122,835 |
| 812 | yes | yes | no | 2026-09-13 | 2026-09-13 | 2,088 | 139,240 |
| 811 | no | no | yes | 2026-09-13 | 2026-09-13 | 0 | 0 |

**Platform breakdown**

| platform | users | games |
|---|---|---|
| chess.com | 252 | 472,259 |
| lichess | 157 | 220,077 |
| flawchess | 72 | 624 |
| pgn | 6 | 11 |

Activity: 5 of the 10 latest accounts are registered and all 5 imported games (431–4,423 each). Of the 5 guests, 2 imported (57 and 2,000 games) and 3 bounced without linking a platform. Guests are 59% of all accounts. Since the 2026-09-02 report: +42 registered (276 → 318), +80 guests (380 → 460), +29.6k games, +1.9 M positions, +1 GB.

## 1. Storage Report

**Overview**

| db size | games | positions | avg positions/game |
|---|---|---|---|
| 26 GB | 692,971 | 47,527,319 | 68.6 |

**Per-table breakdown** (tables ≥ 1 MB)

| table | data | indexes | total |
|---|---|---|---|
| game_positions | 7,114 MB | 6,954 MB | 14 GB |
| game_flaws | 6,922 MB | 592 MB | 7,514 MB |
| games | 2,705 MB | 1,201 MB | 3,906 MB |
| opening_cache_audit | 349 MB | 120 MB | 468 MB |
| game_best_moves | 227 MB | 187 MB | 414 MB |
| opening_position_eval | 312 MB | 98 MB | 409 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| herring_pool | 2.3 MB | 0.9 MB | 3.3 MB |
| llm_logs | 0.1 MB | 2.8 MB | 2.9 MB |
| opening_cache_repair_games | 1.7 MB | 0.9 MB | 2.6 MB |
| openings | 0.8 MB | 0.9 MB | 1.7 MB |
| opening_cache_repair_rows | 0.8 MB | 0.6 MB | 1.5 MB |
| worker_heartbeats | 0.9 MB | 0.1 MB | 1.0 MB |

**Per-index breakdown** (≥ 10 MB)

| index | table | size |
|---|---|---|
| game_positions_pkey | game_positions | 2,647 MB |
| ix_gp_user_endgame_game | game_positions | 1,262 MB |
| ix_gp_user_full_hash_move_san | game_positions | 976 MB |
| ix_game_positions_game_id | game_positions | 636 MB |
| ix_gp_user_black_hash | game_positions | 536 MB |
| ix_gp_user_white_hash | game_positions | 534 MB |
| ix_gp_full_hash_opening | game_positions | 361 MB |
| game_flaws_pkey | game_flaws | 323 MB |
| game_best_moves_pkey | game_best_moves | 187 MB |
| uq_games_user_platform_game_id | games | 120 MB |
| ix_game_flaws_user_severity | game_flaws | 109 MB |
| opening_position_eval_pkey | opening_position_eval | 97 MB |
| ix_game_flaws_game_id | game_flaws | 94 MB |
| opening_cache_audit_pkey | opening_cache_audit | 83 MB |
| ix_games_user_played_at | games | 71 MB |
| ix_game_flaws_blob_backfill | game_flaws | 64 MB |
| games_pkey | games | 57 MB |
| uq_games_id_user_id | games | 56 MB |
| ix_opening_cache_audit_status | opening_cache_audit | 36 MB |
| ix_games_full_pv_pending | games | 30 MB |
| ix_games_full_evals_pending | games | 29 MB |
| ix_games_needs_engine_full_evals | games | 17 MB |

Notes: `game_positions` is 54% of the DB and is index-heavy (indexes ≈ data, 6.95 vs 7.11 GB). `game_flaws` has grown to 7.5 GB (PV-line JSONB blobs) and is now the second-largest table with a lean 8.5% index ratio. The three Phase 220 repair tables (`opening_cache_audit` + `opening_cache_repair_*`) hold 472 MB of one-time repair ledger.

## 2. Performance Analysis

**Buffer cache hit ratio**: 99.58% — excellent.

**Slowest queries by avg time** (filtered to statements that matter; everything above them is one-off operator/research SQL or `pg_dump` COPY)

| avg_ms | max_ms | calls | total_ms | live? | query |
|---|---|---|---|---|---|
| 75,980 | 143,352 | 22 | 1,671,556 | operator script | `SELECT DISTINCT game_id ... max_ply_per_game ... eval_cp IS NULL` — `scripts/resweep_holed_games.py` hole finder (`eval_drain.py:1673`) |
| 1,378 | — | 1,030 | 1,419,425 | background | per-user benchmark percentile slice (`canonical_slice_sql.py`, `compute_stage_a/b`) |
| 966 | — | 458 | 442,542 | background | same family, second metric |
| 158 | — | 3,266 | 514,934 | **on every user delete** | `UPDATE ONLY opening_cache_audit SET sample_game_id = NULL WHERE $1 = sample_game_id` — the FK `ON DELETE SET NULL` RI trigger |
| 153 | — | 4,250 | 651,122 | live | `DELETE FROM games WHERE user_id = $1 RETURNING id` |
| 39 | — | 9,012 | 349,303 | live | `count(*) FROM game_flaws ... LATERAL prior-position` blob-pending count (`train_pool.py:1195`) |

The 5.3M ms row at the very top (`WITH sample AS (SELECT full_hash FROM opening_cache_audit ...)`) is a single ad-hoc SEED-164 research query, not app code.

**Highest total time**

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 7,778,962 | 11,443,371 | 0.68 | tier-3 eval-queue user picker (split-EXISTS form; live, growing ~35 calls/min) |
| 4,389,382 | 11,102,633 | 0.40 | blob-backfill user picker |
| 3,746,140 | 10,976,961 | 0.34 | best-move backfill user picker |
| 1,818,503 | 356,644 | 5.10 | per-user pending-games picker |
| 1,671,556 | 22 | 75,980 | resweep hole finder (operator script) |
| 1,419,425 | 1,030 | 1,378 | benchmark percentile slice |
| 1,021,706 | 13,267 | 77 | `COPY game_positions FROM STDIN (binary)` import |
| 825,840 | 10,783,630 | 0.08 | entry-eval lease picker |
| 651,122 | 4,250 | 153 | `DELETE FROM games WHERE user_id` |
| 531,465 | 11,458,628 | 0.05 | `UPDATE eval_jobs` lease reclaim |
| 514,934 | 3,266 | 158 | opening_cache_audit FK SET NULL trigger |

Server time is dominated by the three worker-poll pickers (~16M ms over 12 weeks, ~34M calls). Per-call cost is sub-millisecond; total is a function of poll frequency, not query shape. No action.

**Sequential scan analysis**

| table | rows | seq_scans | seq_tup_read | idx_scans | verdict |
|---|---|---|---|---|---|
| games | 695k | 210,224 | 124 B | 52.6 B | fine (0.0004% of scans; 590k tup/scan = analytic/backfill sweeps) |
| users | 778 | 48.3 M | 22.5 B | 15.8 M | fine (tiny table, poll pickers) |
| game_positions | 47.5 M | 455 | 12.8 B | 185 M | fine (one-off scripts) |
| **opening_cache_audit** | 2.57 M | **3,542** | **9.0 B** | 14.8 M | **flag** — 2.54 M tuples/scan; 3,266 of these are the FK SET NULL trigger (no index on `sample_game_id`) |
| eval_jobs | 1.2k | 9.2 M | 1.25 B | 27 M | fine (tiny) |
| oauth_account | 247 | 773k | 110 M | 473 | fine (tiny) |

**Index usage**

Unused (0 scans since 2026-06-23):

| index | size | verdict |
|---|---|---|
| ix_games_full_pv_pending (partial, `WHERE full_pv_completed_at IS NULL`) | 30 MB | **drop candidate** — superseded by `ix_games_lichess_pv_backfill_pending` (3.6 B scans); the code comment at `app/models/game.py:251` says it lives only in the migration |
| uq_openings_eco_name_pgn / ix_openings_eco_name | 750 kB | keep (uniqueness / lookup, table is 3.6k rows and seq-scanned) |
| ix_herring_pool_recency | 376 kB | keep for now (tiny; Phase 179 recency ordering) |
| ix_opening_cache_repair_rows_hash | 160 kB | keep until the Phase 220 repair tables are retired |
| ix_llm_logs_findings_hash / ix_llm_logs_endpoint_created_at | 96 kB | keep (tiny) |
| feedback_pkey, alembic_version_pkc, ix_oauth_account_oauth_name | — | keep (PK / auth) |

Low-use but large: `ix_gp_user_white_hash` / `ix_gp_user_black_hash` (534 + 536 MB, 592 / 797 scans). These back the per-colour opening tree lookup and are only hit by the openings feature, so low scan counts are expected; keep.

**Dead tuples / autovacuum**

| table | live | dead | dead % | last autovacuum |
|---|---|---|---|---|
| games | 695k | 104k | 14.9% | 2026-09-13 |
| game_positions | 47.5 M | 1.43 M | 3.0% | 2026-09-13 |
| game_flaws | 4.89 M | 375k | 7.7% | 2026-09-12 |
| users | 778 | 111 | 14% | 2026-08-29 |
| drill_sessions | 429 | 125 | 29% | 2026-08-30 (tiny) |
| user_benchmark_percentiles | 3,613 | 633 | 17.5% | 2026-08-29 |

Nothing above 20% except tiny tables. `games` at 15% dead is the steady state of the eval pipeline's UPDATE churn; autovacuum keeps up.

**Recommendations**

- **No action needed**: cache hit 99.58%; worker-poll pickers dominate total time by call count only; the 76 s hole finder is a 22-call operator script; the 1.4 s benchmark percentile slice is a post-import background task (`compute_stage_a/b` via `asyncio.create_task`, not in the request path).
- **Recommended**: add a partial index `opening_cache_audit (sample_game_id) WHERE sample_game_id IS NOT NULL` — or drop the FK `opening_cache_audit_sample_game_id_fkey` outright. Every user delete / re-import currently seq-scans 2.5 M audit rows once per deleted game batch (3,266 scans, 158 ms each, 9 B tuples read). The audit ledger is a one-time Phase 220 artifact; if the plan is to retire the three `opening_cache_*` repair tables, dropping them makes the index moot.
- **Consider**: drop `ix_games_full_pv_pending` (30 MB, 0 scans in 12 weeks, superseded by `ix_games_lichess_pv_backfill_pending`). Small win; needs a migration.
- **Monitor**: `game_flaws` is 7.5 GB and growing with PV-line JSONB; it will overtake `game_positions` data size within a few months at the current backfill pace.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

`flaws_but_all_counts_null` = **0** on every platform.

| platform | counts present | both match | match rate | mistake mismatch | blunder mismatch | mistakes oracle/gf | blunders oracle/gf |
|---|---|---|---|---|---|---|---|
| chess.com | 449,081 | 448,353 | 99.84% | 629 | 481 | 1,329,103 / 1,330,004 (+0.07%) | 2,033,333 / 2,033,792 (+0.02%) |
| lichess | 202,795 | 202,277 | 99.74% | 452 | 337 | 597,997 / 598,533 (+0.09%) | 903,674 / 903,874 (+0.02%) |
| flawchess | 545 | 545 | 100% | 0 | 0 | 1,487 / 1,487 | 2,139 / 2,139 |
| pgn | 11 | 11 | 100% | 0 | 0 | 37 / 37 | 21 / 21 |

Direction: `game_flaws` slightly over-counts on both platforms (chess.com 548 over / 81 under for mistakes; lichess 371 / 81). chess.com agrees better than lichess, as the source model predicts. Aggregates within 0.1%.

**Verdict: PASS.** (2026-07-31 reference: 99.78% / 99.47%; both improved.)

### Check B — Eval coverage vs oracle presence (Flaws Timeline gate)

| platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| chess.com | 442,048 | 0 | 442,048 |
| lichess | 200,563 | 0 | 200,563 |
| flawchess | 525 | 0 | 525 |
| pgn | 11 | 0 | 11 |

**Verdict: PASS.**

### Check C — Opening cache vs lichess median

| n_checked | n_bad (>150cp) | n_disagreed | n_unconfirmed | cache rows |
|---|---|---|---|---|
| 25,576 | **19** | 28 | 176,022 (7.3%) | 2,395,065 |

First post-Phase-220 measurement: 87 → 19 (0.34% → 0.07%).

The 19 rows were inspected individually. All 19 share one shape: **same sign as the lichess median, already decisive, cache less extreme** (e.g. lichess −1217 / cache −485; +887 / +442; +900 / +478; smallest gap +302 / +147). Zero sign flips, zero near-equal-vs-decisive cases. All 19 are `confirmed = true, n_sources = 2, disagreements = 0`, audit status `screened_clean` (18) / `confirmed_clean` (1). Two independent engine games agreed on each cache value. That is depth disagreement in already-won positions (lichess cloud evals go deeper and find bigger wins), not the SEED-164 poison signature (arbitrary donor eval, wrong sign or wrong magnitude in equal positions).

**Verdict: INVESTIGATE by the >5 rule; investigated, benign.** Suggest tightening the check to count only sign flips or `|lichess_med| < 100 AND |cache| > 150` cases, so the same-sign-decisive band stops tripping it. The 28 `disagreements ≥ 1` rows are the two-source mechanism working (a candidate that was contradicted and re-sourced), and the 7.3% unconfirmed share is the expected fresh-candidate tail five days after release 2.

### Check D — Opening bounce rate (engine games, plies 2–19, 1-in-16 sample on `game_id % 16 = 0`)

| n_checked | n_bounce_any | bounce_pct_any | n_band | n_bounce_band | bounce_pct_band |
|---|---|---|---|---|---|
| 651,642 | 4,125 | **0.633%** | 8,099 | 1,563 | **0.240%** |

Reference floors: cache-free benchmark 0.618% / 0.235%; prod pre-repair legacy 0.798% / 0.298%, mid 0.625% / 0.243%, recent 0.844% / 0.271%. Prod now sits within 0.015 pp of the cache-free floor.

**Verdict: PASS.**

## Summary

- **26 GB**, 693k games, 47.5 M positions, 778 users (318 registered). Cache hit 99.58%. All four sanity checks are healthy; Check A/B are clean, Check D is at the cache-free floor, and Check C dropped from 87 to 19 after Phase 220 with every remaining row being a benign same-sign depth disagreement in decided positions.
- **One real performance finding**: `opening_cache_audit.sample_game_id` has an `ON DELETE SET NULL` FK to `games` with no index, so every user delete/re-import seq-scans the 2.5 M-row audit table per batch (3,266 scans × 158 ms, 9 B tuples read). Add a partial index on `sample_game_id`, or drop the FK / the whole repair table set now that the repair is done.
- **Small cleanup**: `ix_games_full_pv_pending` (30 MB) has had 0 scans in 12 weeks and is superseded by `ix_games_lichess_pv_backfill_pending`; drop candidate.
- **Watch**: `game_flaws` is 7.5 GB (PV-line JSONB) and will pass `game_positions` data size within months.
- `pg_stat_statements` top-N is cluttered with one-off SEED research SQL and `pg_dump` COPYs; a targeted `pg_stat_statements_reset(0,0,<queryid>)` for those, or a blanket reset, would make the next report cleaner.
