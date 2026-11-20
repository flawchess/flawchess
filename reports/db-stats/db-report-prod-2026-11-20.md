# FlawChess DB Report — 2026-11-20

- **DB**: prod
- **Snapshot taken**: 2026-11-20T13:11Z (queries ran over ~25 min)
- **Sections run**: users / storage / performance / sanity (Checks A–D + 11b)
- **Stats windows**: `pg_stat_statements` reset 2026-07-28T20:57Z (≈16 weeks); `pg_stat_database` / table+index counters reset 2026-06-23T20:35Z (≈21 weeks)
- **Previous full prod report**: 2026-09-16 (2026-09-27 was sanity-only)

## 0. Users Overview

### User summary

| total users | registered | guests |
|---|---|---|
| 1,500 | 705 | 795 |

(2026-09-16: 778 total / 318 registered. Registered users more than doubled in ~9 weeks.)

### 10 most recent users

| user id | chess.com | lichess | guest | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 1561 | ✓ | | | 2026-11-20 | 2026-11-20 | 31 | 1,696 |
| 1560 | ✓ | | | 2026-11-20 | 2026-11-20 | 1,080 | 70,400 |
| 1559 | | | ✓ | 2026-11-19 | 2026-11-19 | 0 | 0 |
| 1558 | | | ✓ | 2026-11-19 | 2026-11-19 | 1 | 39 |
| 1557 | | | ✓ | 2026-11-19 | 2026-11-19 | 0 | 0 |
| 1556 | | | ✓ | 2026-11-19 | 2026-11-19 | 1 | 87 |
| 1555 | | | | 2026-11-19 | 2026-11-19 | 0 | 0 |
| 1554 | ✓ | ✓ | | 2026-11-19 | 2026-11-19 | 102 | 5,858 |
| 1553 | | | ✓ | 2026-11-18 | 2026-11-18 | 0 | 0 |
| 1552 | ✓ | | | 2026-11-18 | 2026-11-18 | 477 | 29,324 |

### Platform breakdown

| platform | users | games |
|---|---|---|
| chess.com | 514 | 736,782 |
| lichess | 330 | 370,408 |
| flawchess (bot games) | 135 | 1,631 |
| pgn (upload) | 23 | 54 |

Activity: 4 of the 5 most recent registered signups linked a platform and imported games (31 to 1,080 each). The fifth (1555) registered with no linked account and no games. The 5 guests have 0 or 1 game each; single-game guests are bot games or PGN uploads. Guests are 53% of all accounts. `pgn` is a new platform since the last report (23 users, 54 games).

---

## 1. Storage Report

### Overview

| metric | value | 2026-09-16 | Δ |
|---|---|---|---|
| Database size | **39 GB** | 26 GB | +50% |
| Total games | 1,108,875 | 693k | +60% |
| Total positions | 74,751,619 | 47.5 M | +57% |
| Avg positions / game | 67.4 | 68.5 | ≈ |

### Per-table breakdown (top 10; everything else < 15 MB)

The "index + TOAST" column is `total − heap`, so it includes TOAST. Only `games` has meaningful TOAST (1,190 MB, the PGN text), so its real index footprint is ≈ 500 MB.

| table | heap | index + TOAST | total |
|---|---|---|---|
| game_positions | 8,179 MB | 10 GB | **18 GB** |
| game_flaws | 14 GB | 1,021 MB | **15 GB** |
| games | 2,705 MB | 1,689 MB (1,190 MB TOAST) | 4,394 MB |
| opening_position_eval | 556 MB | 169 MB | 725 MB |
| game_best_moves | 342 MB | 283 MB | 625 MB |
| opening_cache_audit | 349 MB | 141 MB | 490 MB |
| benchmark_cohort_cdf | 22 MB | 15 MB | 37 MB |
| drill_solves | 12 MB | 1.9 MB | 13 MB |
| llm_logs | 256 kB | 5.4 MB | 5.7 MB |
| herring_pool | 2.4 MB | 1.0 MB | 3.4 MB |

### Per-index breakdown (≥ 10 MB)

| index | table | size |
|---|---|---|
| game_positions_pkey | game_positions | 3,999 MB |
| ix_gp_user_endgame_game | game_positions | 1,806 MB |
| ix_gp_user_full_hash_move_san | game_positions | 1,439 MB |
| ix_game_positions_game_id | game_positions | 949 MB |
| ix_gp_user_black_hash | game_positions | 838 MB |
| ix_gp_user_white_hash | game_positions | 835 MB |
| game_flaws_pkey | game_flaws | 507 MB |
| ix_gp_full_hash_opening | game_positions | 387 MB |
| ix_game_flaws_user_severity | game_flaws | 295 MB |
| game_best_moves_pkey | game_best_moves | 283 MB |
| opening_position_eval_pkey | opening_position_eval | 169 MB |
| ix_game_flaws_game_id | game_flaws | 151 MB |
| uq_games_user_platform_game_id | games | 121 MB |
| opening_cache_audit_pkey | opening_cache_audit | 83 MB |
| ix_games_user_played_at | games | 77 MB |
| ix_game_flaws_blob_backfill | game_flaws | 64 MB |
| games_pkey | games | 63 MB |
| uq_games_id_user_id | games | 61 MB |
| ix_games_user_full_evals | games | 45 MB |
| ix_opening_cache_audit_status | opening_cache_audit | 36 MB |
| ix_games_full_evals_pending | games | 29 MB |
| ix_opening_cache_audit_sample_game_id | opening_cache_audit | 22 MB |
| ix_games_needs_engine_full_evals | games | 17 MB |
| benchmark_cohort_cdf_pkey | benchmark_cohort_cdf | 13 MB |

The remaining ~70 indexes are each under 3 MB.

### Storage notes

- **`game_flaws` doubled (7.5 → 15 GB) while its row count grew ~44% (5.4 M → 7.8 M).** It is not bloat. On-disk bytes per row (1,871) are only ~30% above the planner's average row width (1,421), and that overhead is normal for a table that takes heavy UPDATEs (46.6 M updates, 69% non-HOT, from the Maia/facepalm/blob backfills). The growth is real payload: the per-flaw PV-line JSONB blobs sit just under the TOAST threshold, so they stay in the heap (TOAST is 0 bytes). Rows are now ~1.4 KB each, against ~114 B for a `game_positions` row.
- **`game_positions` is lean.** Its on-disk row size (114 B) matches the estimated width (113 B), so there is no bloat. Indexes are 1.25× the heap. The pkey alone is 4 GB.
- **`games` heap has been flat at 2,705 MB since 2026-09-02** while rows grew 658k → 1.11 M. The free space left behind earlier is being reused, which is good. Its heap still holds ~2.6 KB per live row against an ~0.8 KB average width, so it is roughly 2/3 free space. See the reltuples note in §2.6.
- The Phase 220 repair ledger (`opening_cache_audit` + `opening_cache_repair_*`) is still 494 MB of one-time data. `app/` only references it through the model (`app/models/opening_cache_audit.py`), and `scripts/opening_cache_repair.py` is the only script that uses it.

---

## 2. Performance Analysis

### 2.1 Buffer cache hit ratio

**99.56%**, which is excellent (2026-09-16: 99.58%). The DB grew 50% with no visible cache pressure.

### 2.2 Slowest queries by average time

| avg_ms | max_ms | calls | total_ms | query | status |
|---|---|---|---|---|---|
| 267,597 | 326,695 | 3 | 802,792 | `COPY public.game_positions … TO stdout` | pg_dump backup. Ignore |
| **177,276** | **650,428** | **58** | **10,282,030** | `SELECT DISTINCT game_positions.game_id … JOIN (SELECT game_id, max(ply) … GROUP BY game_id)` | **live: daily in-process `resweep_holed_games`** (see 2.7) |
| 89,641 | 120,056 | 3 | 268,923 | `COPY public.games … TO stdout` | pg_dump |
| 76,205 | 79,996 | 3 | 228,616 | `WITH ranked AS (SELECT f.game_id, f.ply, f.allowed_tactic_motif …` | ad-hoc analysis, 3 calls |
| 73,421 | 88,913 | 3 | 220,262 | `COPY public.game_flaws … TO stdout` | pg_dump |
| 58,978 | 128,548 | 11 | 648,759 | `SELECT g.id FROM games g JOIN users u … maia_reply_spread IS NULL …` | Maia/facepalm backfill candidate scan (`scripts/backfill_maia_flaws.py`), operator-run |
| 26,716–16,685 | — | 1–10 each | — | a dozen `count(*) FROM game_flaws JOIN games … maia_* IS NULL / facepalm_*` shapes | backfill progress probes / ad-hoc counts |
| **5,538** | **52,640** | **550** | 3,045,875 | `query_endgame_bucket_rows` (`bucket_with_next`) | **live, user-facing**; fixed on `main` (see 2.8) |
| **3,414** | 31,746 | 550 | 1,877,632 | `query_clock_stats_rows` (`clock_per_game`) | **live, user-facing** |
| **3,167** | 30,407 | 550 | 1,741,600 | `query_endgame_entry_rows` (`span_with_next`) | **live, user-facing** |
| 585 | 42,915 | 6,166 | 3,605,378 | canonical slice `WITH selected_users … recent_capped …` | Stage A/B percentile + ranked-sample fetch. Bimodal (min 2 ms, sd 2 s) |

### 2.3 Highest total time

| total_ms | calls | avg_ms | query | verdict |
|---|---|---|---|---|
| 25,975,043 | 19,252,685 | 1.35 | tier-3 eval user picker (`users u WHERE is_guest … EXISTS games … full_evals_completed_at IS NULL`) | worker polling volume. Live (calls grew 685 → 898 within 2.5 min). Fine at 1.35 ms |
| 14,402,233 | 17,867,324 | 0.81 | best-move picker (`full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`) | polling, returns 0 rows. Fine |
| 13,287,606 | 18,183,764 | 0.73 | tier-4 blob picker (`blobs_completed_at IS NULL`) | polling. Fine |
| 10,282,030 | 58 | 177,276 | `resweep_holed_games` | see 2.7 |
| 6,924,183 | 158,923 | 43.6 | `game_flaws LEFT JOIN game_positions` (pv, maia columns) | backfill loader. Calls frozen between samples, so not running now |
| 5,690,586 | 41,042 | 138.7 | `game_flaws … jsonb_extract_path_text(missed_pv_lines …)` | Phase 252 short-line repair loader. Frozen |
| 4,317,943 | 978,359 | 4.4 | per-user eval-candidate game picker | drain. Fine |
| 4,070,282 | 46,597 | 87.4 | `COPY game_positions FROM STDIN` | import bulk insert. Expected |
| 3,605,378 | 6,166 | 584.7 | canonical slice `recent_capped` | see 2.2 |
| 3,357,948 | 54,322 | 61.8 | `count(*) FROM game_flaws … LEFT JOIN LATERAL game_positions` | backfill/probe |
| 3,045,875 + 1,877,632 + 1,741,600 + 815k | 550 each | — | ranked endgame quartet | see 2.8 |
| 2,392,842 | 5,286 | 452.7 | `UPDATE game_positions SET pv … FROM unnest(…)` | Phase 252 repair writes |

The worker-picker trio is ~54 M ms, the largest consumer by far, but each call is sub-2 ms and they run off the request path. Nothing to fix.

### 2.4 Sequential scans

| table | seq_scan | idx_scan | rows | verdict |
|---|---|---|---|---|
| games | 211,523 (124.5 B tuples) | 74.9 B | 1.1 M | fine: 0.0003% of scans; the tuple volume is backfill/analysis sweeps and pg_dump |
| users | 70.3 M | 38.7 M | 1,500 | tiny table, picker subqueries. Seq scan is the right plan |
| game_positions | 705 (was 455) | 634 M | 75 M | fine: pg_dump, daily resweep, scripts |
| opening_cache_audit | 3,546 (was 3,542) | 14.9 M | 2.6 M | **fixed**: `ix_opening_cache_audit_sample_game_id` now exists, and the FK-trigger seq scans flagged on 2026-09-16 stopped (+4 in 9 weeks) |
| eval_jobs, drill_items, drill_sessions, drill_solves, oauth_account, bot_game_settings, import_jobs | 0.1–9.3 M | — | < 25k rows each | tiny tables. Fine |
| game_flaws | 759 | 699 B | 7.8 M | excellent |

### 2.5 Index usage

- **Zero scans in 21 weeks:** `uq_openings_eco_name_pgn` (unique constraint, keep), `ix_herring_pool_recency` (376 kB), `ix_openings_eco_name` (264 kB), `ix_opening_cache_repair_rows_hash`, `ix_llm_logs_findings_hash`, `ix_llm_logs_endpoint_created_at`, `ix_blunder_check_windows_ended_at` (new feature), `ix_oauth_account_oauth_name` (auth, keep), plus several pkeys (keep). All are under 500 kB, so dropping them saves nothing worth a migration.
- **Large but rarely used:** `ix_gp_user_white_hash` / `ix_gp_user_black_hash`: 835 + 838 MB with 1,176 / 1,479 scans. They back the per-color opening tree and the bookmark color-hash lookups, so **keep** (same verdict as 2026-09-16; they grew with the table). `ix_games_full_evals_pending` (29 MB, 47 scans) is worth a look at the next index review.
- `ix_games_full_pv_pending`, flagged as a drop candidate on 2026-09-16, is gone.

### 2.6 Dead tuples / autovacuum

- `game_flaws` 676,646 dead / 7.8 M (8.7%), autovacuumed today. `game_positions` 2.92 M / 74.8 M (3.9%), last autovacuum 2026-11-16. `games` 0.4%. **None of the large tables is above 20%.**
- Tables above 20% are all tiny: `push_subscriptions` 17/35 (never autovacuumed), `worker_heartbeats` 119/329 (vacuumed today), `user_rating_anchors` 237/955, `blunder_check_answers` 103/433. Not worth acting on.
- **`games` planner row estimate is ~50% high:** `reltuples` / `n_live_tup` = 1,658,664 vs a true count of 1,108,875, even though autovacuum and autoanalyze both ran today. This is probably sampling error on a heap that is ~2/3 free space (§1), but I have not confirmed that. It inflates `games` row estimates in every plan (the EXPLAINs below show `rows=1,449,809` for a filter that cannot exceed 1.1 M).
- `game_positions` index-only scans hit the heap often: 65,789 heap fetches for 92k index rows in the EXPLAIN in 2.8, because the visibility map is behind (2.9 M dead tuples, autovacuum 4 days ago). This adds cold reads to every endgame query.

### 2.7 `resweep_holed_games`: live, daily, 37 s – 11 min per run

`app/services/eval_drain.py:1811`. Since the 2026-09-16 report it has been automated (`run_periodic_holed_game_resweep`, every 24 h in-process; the loop sleeps first, so a restart resets the clock). 58 calls in ~16 weeks is consistent with a daily run plus a few manual `scripts/resweep_holed_games.py` runs. Each run aggregates `max(ply) GROUP BY game_id` over **all 75 M** `game_positions` rows. That costs a parallel seq scan plus a 4-partition hash aggregate, and it reads **3.2 M blocks from disk per call (~25 GB)** to find candidates. The docstring notes that prod dry runs return 0 candidates, so it never short-circuits on the `LIMIT 5000`. The code has no "do not simplify" note, and I found no seed for it.

It is not urgent, since it runs off the request path once a day. But it is the single largest disk reader and it grows linearly with the table. The cache hit ratio has not suffered so far.

### 2.8 Ranked endgame stats: intermittent 20–110 s requests (user-facing), fixed on `main`

> **Update (same day):** root cause confirmed and fixed in quick task 261120-li5 (`main` squash commit `d06c5847b`, not yet deployed). See "Root cause (confirmed)" at the end of this section. The original analysis is kept below as it was written.

`GET /api/endgames/ranked-stats` → `endgame_ranked_service.fetch_ranked_inputs` (`app/services/endgame_ranked_service.py:188`) runs four `game_positions` aggregates in sequence: `query_endgame_performance_rows`, `query_endgame_entry_rows`, `query_endgame_bucket_rows` and `query_clock_stats_rows`. Each is restricted with `game_id = ANY(:ranked_game_ids)` (up to 4 × 1,000 ids). The same inputs also feed insights (`insights_service.py:209`).

Sentry, last 30 days (sampled transactions):

| | count | p50 | p95 | max |
|---|---|---|---|---|
| `/api/endgames/ranked-stats` transaction | 260 | 531 ms | **82.3 s** | **110.6 s** |
| `bucket_with_next` DB span | 250 | 25 ms | 35.2 s | 45.4 s |
| `clock_per_game` DB span | 250 | 77 ms | 20.8 s | 31.8 s |
| `span_with_next` DB span | 250 | 20 ms | 19.0 s | 23.5 s |
| endgame/non-endgame perf-rows span | 250 | 115 ms | 8.6 s | 9.4 s |

Six requests took over 10 s: 2026-10-24 (×2, 43 s each), 11-03 (24 s), 11-06 (75 s), 11-07 (41 s), and 11-13 (**110.6 s**, trace `d23a1cb125bf4ff4aa9b23494b6e9b62`). That makes it live and recurring, not a dead shape. All four shapes are the current source; their SQL text matches `endgame_repository.py:313/545/642`.

The latency is **bimodal**: p50 is tens of ms, but `pg_stat_statements` averages **~2.07 M shared-buffer hits per call** (≈16 GB of buffer touches) for the bucket and entry queries. That is far more than a single user's positions should need. I reconstructed the bucket query for the heaviest user (user 95, 40k games, 2,829 ranked ids). To get the ids in, I had to pass them as an InitPlan array, so the planner did not see a bound array like the app sends; treat this as an approximation, not a repro. It ran in **3.1 s touching 65k buffers**, mostly cold reads plus visibility-map heap fetches, with a sane `Index Only Scan using ix_gp_user_endgame_game` plan. So the slow cases probably use a different plan than my reconstruction, perhaps a generic-plan flip on asyncpg prepared statements or a nested-loop rescan of the ANY array. **That is a hypothesis.** Confirming it needs the actual plan of a slow call: a literal-array EXPLAIN for the user behind trace `d23a1cb1…`, or `auto_explain` with a ~5 s threshold.

#### Root cause (confirmed)

The hypothesis above was wrong: it is neither a generic-plan flip nor related to the heaviest users. A read-only timing run of the app's own `fetch_ranked_inputs` against prod showed the heaviest users (95, 11, 288) finishing in under 5 s, while two mid-size users were slow: user 1388 (1,435 ranked ids) took 25.3 s and user 1521 (1,151 ids) 15.1 s, almost all of it in these queries.

The cause is a redundant predicate. Each of the four queries restricts to the ranked ids twice: inside the grouped `game_positions` aggregation (the selective filter) and again on the outer `games` query, where `apply_game_filters(..., game_ids=game_ids)` adds `games.id = ANY(:ids)`. The outer copy adds nothing, because the join (or `IN`) on `games.id` already limits rows to the inner set. But the planner multiplies `user_id` × `ANY` × platform selectivities into a **1-row estimate** for `games`, picks a nested loop with `games` outer, and **re-executes the whole aggregate once per ranked game**. Whether the estimate collapses to 1 row depends on the user's statistics, which explains the bimodal latency.

EXPLAIN ANALYZE on prod, user 1388, 1,435 literal ids, `query_clock_stats_rows` shape, same warm cache:

| | time | shared buffers | aggregate loops |
|---|---|---|---|
| as shipped | 14,510 ms | 6,564,533 | 1,435 |
| outer `games.id = ANY` removed | 30 ms | 8,908 | 1 |

**Fix** (quick 261120-li5): `game_ids=None` in `apply_game_filters` for the entry, bucket and clock queries and the endgame (`IN`) half of the performance rows. The non-endgame (`NOT IN`) half keeps it, since there it is the only ranked-id restriction. A shape test pins the outer predicate's absence and fails with the fix reverted.

Prod timing with the fixed code (read-only, `fetch_ranked_inputs` end to end):

| user | ranked ids | before | after |
|---|---|---|---|
| 1388 | 1,435 | 25.3 s | 0.9 s |
| 1521 | 1,151 | 15.1 s | 0.5 s |
| 11 | 2,852 | 4.7 s | 1.0 s |
| 288 | 2,342 | 3.7 s | 1.0 s |

Every endgame query is now 35–216 ms for every user tested. After the deploy, the next report should show the ranked-stats p95 in Sentry far below the 82 s seen here. Dropping the predicate changes the parse tree, so `pg_stat_statements` will record the fixed queries under new queryids. The four old queryids (`-1032788173682241665`, `7761188096581029246`, `-1497969583499870477`, `-7666038889394100895`) will freeze at their historical 3–5 s averages. They are dead shapes from then on, not a regression (see the skill's "MANDATORY before recommending any query rewrite" check).

---

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

| platform | flaw rows | **counts null gap** | counts present | both match | match rate | mistake mm | blunder mm |
|---|---|---|---|---|---|---|---|
| chess.com | 692,124 | **0** | 707,775 | 707,047 | **99.90%** | 629 | 481 |
| lichess | 355,209 | **0** | 363,081 | 362,558 | **99.86%** | 455 | 344 |
| flawchess | 1,581 | **0** | 1,612 | 1,612 | 100.00% | 0 | 0 |
| pgn | 53 | **0** | 54 | 54 | 100.00% | 0 | 0 |

Aggregate totals (oracle / `game_flaws`):

| platform | mistakes | blunders | gf over / under (mistakes) | gf over / under (blunders) |
|---|---|---|---|---|
| chess.com | 2,058,292 / 2,059,193 (+0.04%) | 3,128,035 / 3,128,494 (+0.01%) | 548 / 81 | 313 / 168 |
| lichess | 1,029,196 / 1,029,695 (+0.05%) | 1,555,377 / 1,555,497 (+0.01%) | 369 / 86 | 222 / 122 |
| flawchess | 4,170 / 4,170 | 5,821 / 5,821 | 0 / 0 | 0 / 0 |
| pgn | 191 / 191 | 238 / 238 | 0 / 0 | 0 / 0 |

Both rates improved on the 2026-07-31 reference (99.78% / 99.47%). chess.com still agrees better than lichess, as the source model predicts. `game_flaws` leans toward over-counting, but by ≤ 0.05% in aggregate. **Verdict: PASS.**

### Check B — Eval coverage ≥ 90% vs oracle presence (Flaws Timeline gate)

| platform | games ≥ 90% coverage | **ge90_but_oracle_null** | oracle present |
|---|---|---|---|
| chess.com | 694,301 | **0** | 694,301 |
| lichess | 358,425 | **0** | 358,425 |
| flawchess | 1,576 | **0** | 1,576 |
| pgn | 54 | **0** | 54 |

**Verdict: PASS.**

#### Query 11b — full evals done, oracle NULL

| platform | full_evald_oracle_null | short_mates | nonstd_start | latest |
|---|---|---|---|---|
| chess.com | 56 | 54 | 56 | 2026-11-17 |

All 56 are non-standard-start games (chess.com "from position", `initial_fen IS NOT NULL`), which is the documented expected residue. The 54 `short_mates` are a subset of the same games: a follow-up count of standard-start short mates returned **0**. So this is **not** a 260927-ajg regression, although the probe's `short_mates` column double-counts non-standard starts. **Verdict: PASS** (expected residue only).

### Check C — Opening cache vs lichess median

| n_checked | **n_bad** | n_gross (> 150 cp) |
|---|---|---|
| 42,390 | **0** | 44 |

n_gross rose from 19 to 44 since 2026-09-16 (2.3×). As a rate, though, it is 0.074% → 0.104% (1.4×), because the checkable set grew 66%. No row trips the poison-shape gate.

| n_disagreed | n_unconfirmed | total rows |
|---|---|---|
| 1,645 | 2,765,525 (53%) | 5,188,650 |

`n_disagreed` went from 337 (2026-09-27) to 1,645. The weekly breakdown shows disagreements tracking write volume at a steady ~0.05% of new rows. Peaks of 308 and 324 in the weeks of 09-28 and 10-05 coincide with the 611k / 583k-row write peaks. Each week's rows come from almost as many distinct source games (e.g. 324 rows / 307 games), all on one engine version. That is spread-out depth noise caught by two-source confirmation, not one bad writer. **Verdict: PASS.**

### Check D — Opening bounce rate (plies 2–19, engine games, 1-in-16 sample by `game_id % 16`)

| n_checked | bounce_pct_any | n_band (250–360 cp drops) | bounce_pct_band |
|---|---|---|---|
| 1,051,987 | **0.625%** | 13,349 | **0.232%** |

This is at the cache-free benchmark floor (0.618% / 0.235%) and below every recorded prod reference (0.625–0.844% / 0.243–0.298%). **Verdict: PASS.**

---

## Summary

- **Growth:** 39 GB (+50% in 9 weeks), 1.11 M games, 74.8 M positions, 1,500 users (705 registered, up from 318). `game_flaws` (15 GB) is now nearly as large as `game_positions` (18 GB). That is real payload (inline PV-line JSONB blobs, ~1.4 KB per row), not bloat. Cache hit is 99.56%, unchanged.
- **Data integrity is clean.** Checks A–D all PASS. The NULL-count and coverage gaps are 0 on every platform, flaw-count agreement is ≥ 99.86% with aggregates within 0.05%, n_bad = 0, and the bounce rate is at the cache-free floor. The 11b residue is the 56 expected non-standard-start games.
- **Fixed on `main`, deploy pending (user-facing):** `/api/endgames/ranked-stats` had p50 531 ms but p95 82 s, and the worst request took 111 s (2026-11-13). The cause was a redundant outer `games.id = ANY(:ranked_game_ids)` predicate. It made the planner estimate 1 `games` row and re-run the grouped `game_positions` aggregate once per ranked game (14.5 s vs 30 ms for the same query on prod). Quick task 261120-li5 (`d06c5847b`) drops it. Prod timing with the fixed code: user 1388 went from 25.3 s to 0.9 s and user 1521 from 15.1 s to 0.5 s. Details in §2.8.
- **Consider:** `resweep_holed_games` now runs daily in-process. It reads ~25 GB per run (avg 3 min, max 11 min) to aggregate `max(ply)` over all of `game_positions` and usually finds 0 candidates. A partial index on `game_positions (game_id) WHERE eval_cp IS NULL AND eval_mate IS NULL` would make the candidate search proportional to the number of holes instead of the table size. Using `games.ply_count` instead of the `max(ply)` aggregate is the cheaper code change, but its EXPLAIN cost is not clearly lower, so it would need measuring. Seed-worthy, not urgent.
- **Monitor:** the `games` planner row estimate is 50% high (reltuples 1.66 M vs 1.11 M real, despite today's autovacuum and analyze). A one-off `VACUUM (ANALYZE) games` as superuser would show whether it self-corrects. Visibility-map lag on `game_positions` (2.9 M dead tuples, last autovacuum 11-16) costs heap fetches on the endgame index-only scans.
- **Already fixed since 2026-09-16:** the `opening_cache_audit` FK-trigger seq scans (index added, +4 scans in 9 weeks) and the dead `ix_games_full_pv_pending` (dropped).
- **No action:** the worker-picker polling shapes (the largest share of total DB time, all < 2 ms per call); pg_dump COPYs; backfill and probe queries (frozen between samples); the tiny-table seq scans and zero-scan indexes (all under 500 kB).
