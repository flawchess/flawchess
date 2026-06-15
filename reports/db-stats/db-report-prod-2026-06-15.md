# FlawChess DB Report — 2026-06-15

- **DB**: prod
- **Snapshot taken**: 2026-06-15T15:41:15Z
- **Sections run**: users / storage / performance / sanity

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|---|---|---|
| 138 | 68 | 70 |

### 10 most recent users

| id | chess.com | lichess | guest? | registered | last login | games | positions |
|---|---|---|---|---|---|---|---|
| 178 | ✅ | — | no | 2026-06-15 | 2026-06-15 | 189 | 12,298 |
| 177 | ✅ | — | yes | 2026-06-15 | 2026-06-15 | 189 | 12,298 |
| 176 | ✅ | — | no | 2026-06-15 | 2026-06-15 | 1,684 | 101,623 |
| 175 | ✅ | — | no | 2026-06-13 | 2026-06-13 | 2,862 | 204,143 |
| 174 | ✅ | — | yes | 2026-06-11 | 2026-06-11 | 711 | 38,474 |
| 173 | ✅ | — | yes | 2026-06-11 | 2026-06-11 | 3,987 | 204,355 |
| 172 | ✅ | — | yes | 2026-06-11 | 2026-06-11 | 1,455 | 106,178 |
| 171 | — | ✅ | yes | 2026-06-11 | 2026-06-11 | 2,141 | 134,343 |
| 170 | — | — | no | 2026-06-11 | 2026-06-11 | 0 | 0 |
| 169 | — | ✅ | yes | 2026-06-10 | 2026-06-10 | 1,102 | 87,943 |

### Platform breakdown

| platform | users | games |
|---|---|---|
| chess.com | 87 | 391,177 |
| lichess | 57 | 212,173 |

**Activity note:** 9 of the 10 most recent signups have imported games — healthy activation. The lone exception (user 170, registered) linked no platform and has 0 games. Guest/registered split is roughly even (70 guests / 68 registered), and guests are actively importing large game sets (e.g. user 173 with ~4k games), so the guest path is doing real work, not just bouncing. chess.com is the dominant source (87 users / 391k games vs lichess 57 users / 212k games).

## 1. Storage Report

### Overview

| Metric | Value |
|---|---|
| Database size | 11 GB |
| Total games | 603,350 |
| Total positions | 44,730,372 |
| Avg positions/game | ~74.1 |

### Per-table breakdown

| table | data size | index size | total size |
|---|---|---|---|
| game_positions | 5,707 MB | 3,636 MB | 9,343 MB |
| games | 1,791 MB | 334 MB | 2,125 MB |
| game_flaws | 44 MB | 37 MB | 81 MB |
| benchmark_cohort_cdf | 8,184 kB | 4,784 kB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 24 kB | 800 kB | 824 kB |
| import_jobs | 48 kB | 408 kB | 456 kB |
| user_benchmark_percentiles | 168 kB | 104 kB | 272 kB |
| position_bookmarks | 56 kB | 64 kB | 120 kB |
| users | 40 kB | 80 kB | 120 kB |
| oauth_account | 24 kB | 80 kB | 104 kB |
| eval_jobs | 8 kB | 96 kB | 104 kB |
| user_rating_anchors | 16 kB | 40 kB | 56 kB |
| alembic_version | 8 kB | 16 kB | 24 kB |

### Per-index breakdown (largest)

| index | table | size |
|---|---|---|
| game_positions_pkey | game_positions | 1,404 MB |
| ix_gp_user_endgame_game | game_positions | 667 MB |
| ix_gp_user_full_hash_move_san | game_positions | 521 MB |
| ix_game_positions_game_id | game_positions | 323 MB |
| ix_gp_user_white_hash | game_positions | 281 MB |
| ix_gp_user_black_hash | game_positions | 279 MB |
| ix_gp_full_hash_opening | game_positions | 160 MB |
| uq_games_user_platform_game_id | games | 73 MB |
| ix_games_user_played_at | games | 36 MB |
| games_pkey | games | 27 MB |
| uq_games_id_user_id | games | 26 MB |
| game_flaws_pkey | game_flaws | 23 MB |
| ix_games_full_pv_pending | games | 15 MB |
| ix_games_full_evals_pending | games | 13 MB |

**Storage summary:** `game_positions` is 9.3 GB total (~83% of the DB), with 3.6 GB of that in indexes (index:data ≈ 0.64 on that table). The seven `game_positions` indexes account for ~3.6 GB; the next-largest table (`games`) is only 2.1 GB. Everything else is sub-100 MB. Nothing is anomalous — the storage profile is exactly what 44.7M position rows × seven indexes should look like.

## 2. Performance Analysis

> Cumulative stats since `stats_reset = 2026-06-05T07:22:51Z` (~10 days).

### Buffer cache hit ratio

**72.16%** — **investigate / contextualize.** Below the 95% "good" threshold, but this is a batch-workload artifact, not an interactive-latency problem (see below).

### Slowest / highest-total-time queries

The single dominant consumer of server time:

| total_ms | calls | avg_ms | rows | query (truncated) |
|---|---|---|---|---|
| 62,768,848 (~17.4 h) | 10,483 | 5,987.68 | 81,947 | `DISTINCT ON (gp1.full_hash) … gp1 JOIN gp2 ON gp1.game_id=gp2.game_id AND gp1.ply=gp2.ply+1 JOIN games … WHERE gp1.full_hash IN (…) AND gp1.ply<=N AND games.full_evals_completed_at IS NOT NULL AND games.lichess_evals_at IS NULL` |
| 12,262,045 | 3,891 | 3,151.39 | 28,964 | `DISTINCT ON (full_hash) … full_hash IN (…) AND ply<=N` (eval lookup, single-table) |
| 12,108,286 | 3,809 | 3,178.86 | 36,183 | `DISTINCT ON (full_hash) … full_hash IN (…) AND ply<=N AND full_evals_completed_at …` |
| 3,009,142 | 7,932 | 379.37 | 7,932 | eval-worker game-pick (`full_evals_completed_at IS NULL`, guest filter, TC ordering) |
| 503,492 | 1,182 | 425.97 | 1,182 | eval-worker game-pick variant (orders by `last_activity`) |

The top three are the **opening-explorer / scout eval-lookup** queries (match candidate positions by `full_hash`, join to the next ply for its eval, restrict to engine-evaluated non-lichess games). They dominate cumulative server time. The eval-worker game-pick queries (#4/#5) are moderate per-call (~380–430 ms) but high-frequency.

A batch of one-off `WITH …` diagnostic/backfill queries appear at the top of the *avg-time* list (11–38 s, `calls = 1` each). These are manual eval-coverage/hole-analysis probes run during the recent eval-backfill work, not application traffic — ignore for tuning.

**EXPLAIN ANALYZE (dominant query, 3 popular `full_hash` values, warm-ish cache):**

```
Limit (actual time=205.854..234.718 rows=3)
  Buffers: shared hit=106743 read=29219
  -> Unique -> Sort -> Gather (2 workers)
       -> Nested Loop  (rows removed by join filter: 8649)
            -> Nested Loop
                 -> Parallel Bitmap Heap Scan on game_positions gp1
                      using ix_gp_full_hash_opening   (26,136 rows for 3 hashes)
                 -> Index Scan on games via uq_games_id_user_id  (25,974 searches)
                      Filter: full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL
            -> Index Scan on game_positions gp2 via ix_game_positions_game_id
Execution Time: 234.873 ms
```

The plan is **healthy**: it uses the partial index `ix_gp_full_hash_opening` (full_hash WHERE ply≤20) and `uq_games_id_user_id`. The query is intrinsically heavy because popular early-game positions (these three occur 8k–9k times each) fan out to tens of thousands of candidate rows that must each be probed against `games` to filter by analysis status. The 6 s production average vs 235 ms here is driven by **(a) cold cache** (this run read 29k buffers ≈ 228 MB) and **(b) much larger `full_hash` IN-lists** in real explorer calls. There is no missing-index fix — it is the cost of the feature.

### Sequential scan analysis

| table | seq_scan | idx_scan | n_live_tup | verdict |
|---|---|---|---|---|
| games | 27,788 | 7.85 B | 598k | **monitor** — 27.8k full scans of a 1.8 GB / 598k-row table (5.6 B tuples read). Source is the eval-worker aggregate/coverage queries, not interactive traffic. |
| game_positions | 158 | 194 M | 44.7M | fine — negligible seq scans on the big table |
| users | 7.57 M | 32.8k | 138 | fine — tiny table, planner correctly prefers seq scan |
| import_jobs | 27.4k | 5.0 M | 232 | fine — tiny table |
| eval_jobs | 37.1k | 21.7k | 47 | fine — tiny table |
| oauth_account | 16.4k | 0 | 8 | fine — tiny table |
| openings | 597 | 0 | 3,641 | fine — seed table, hash-join access |

Only `games` warrants a glance: those 27.8k sequential scans (5.6 B tuples read) come from the eval-pipeline's count/coverage aggregates, the same workload behind the low cache-hit ratio. Not an interactive-path concern.

### Index usage

**Unused indexes (idx_scan = 0)** — assessment:

- `ix_users_email`, `oauth_account` indexes — **keep** (auth / OAuth login lookups; 138 users means they rarely register a scan but are correct to have).
- `llm_logs` indexes (all 0 scans) — **keep**; low-volume, recently-added table.
- `openings` (`ix_openings_eco_name`, `uq_openings_eco_name_pgn`, `openings_pkey`) — **keep**; seed/lookup table accessed by hash join, and the unique constraint enforces integrity.
- `ix_games_full_pv_pending` (15 MB, 0 scans) — **monitor.** This is the only meaningfully-sized unused index. It backs the Phase 117-era full-PV pending sweep; if that worker path is no longer querying it, it's a 15 MB drop candidate. Confirm against current eval-worker code before removing.
- `position_bookmarks`, `benchmark_cohort_cdf`, `alembic_version` PKs, `user_rating_anchors` — **keep** (PKs / integrity / low traffic).

Everything large is heavily used — `uq_games_id_user_id` (5.8 B scans), `games_pkey` (2.0 B), `ix_game_positions_game_id` (111 M), `game_positions_pkey` (43 M), `ix_gp_user_endgame_game` (38 M).

### Dead tuples / autovacuum

All tables are well within healthy dead-tuple ratios. Largest absolute counts: `game_positions` 742k dead / 44.7M live (1.7%), `games` 52k dead / 598k live (8.0%). Autovacuum/autoanalyze ran on every active table within the last ~24 h (most within hours of the snapshot). No bloat concerns.

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

| Metric | Value |
|---|---|
| lichess games with flaws | 41,665 |
| **flaws_but_all_counts_null** | **0** ✅ |
| exact_match | 41,090 |
| mistake_mismatch | 1,131 |
| blunder_mismatch | 552 |
| Match rate | **98.6%** (41,090 / 41,665) |

Mismatch direction & aggregates (Query 10):

| Metric | lichess oracle | game_flaws | drift |
|---|---|---|---|
| total mistakes | 119,752 | 120,657 | +0.76% |
| total blunders | 190,002 | 190,228 | +0.12% |

`game_flaws` slightly *over*-counts vs the lichess oracle on a per-game basis (mistakes: 974 over vs 157 under; blunders: 421 over vs 131 under), which is the expected direction for two independent classifiers. Aggregate totals agree within ~1%.

**Verdict (Check A): PASS** — NULL-count gap is 0, 98.6% exact match, aggregates within 1%.

### Check B — Eval coverage vs oracle-column presence (Flaws Timeline gate)

| platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| lichess | 42,475 | **0** ✅ | 42,475 |
| chess.com | 14,351 | **0** ✅ | 14,351 |

**Verdict (Check B): PASS** — every game clearing the 0.90 eval-coverage gate also has its user-color oracle columns populated, on both platforms. Notably, 14,351 chess.com games now clear the ≥90% coverage bar (Stockfish backfill) **and** carry oracle columns, so they are correctly visible to the Flaws Timeline. No silent drops.

## Summary

- **Size & shape:** 11 GB DB, 603k games, 44.7M positions (~74/game). `game_positions` is 83% of storage (9.3 GB, 3.6 GB of it indexes). Storage profile is normal for the row count — no anomalies, nothing to prune on size grounds.
- **Data integrity: both sanity checks PASS.** Flaw-count NULL gap = 0, oracle↔game_flaws match rate 98.6% with aggregates within ~1%, and zero eval-covered-but-oracle-null games on either platform (incl. 14.3k chess.com games now correctly Timeline-visible).
- **Cache hit ratio 72%** is below the usual >95% bar, but it is **explained, not alarming**: the opening-explorer/scout `full_hash` eval-lookup queries and the eval-worker coverage aggregates repeatedly scan large slices of the 9.3 GB `game_positions` table against a 4 GB `shared_buffers`, so cold reads are inherent to the recent eval-backfill + explorer workload. EXPLAIN confirms the dominant query has a healthy plan (uses the partial `ix_gp_full_hash_opening`); its 6 s average is cold-cache + large IN-lists, not a missing index.
- **Recommended:** none urgent. **Monitor** (1) the `full_hash` eval-lookup queries — they dominate server time (~17 h cumulative over 10 days) and would be the first target if explorer latency becomes a complaint; (2) `ix_games_full_pv_pending` (15 MB, 0 scans) as a possible drop once its Phase 117 worker path is confirmed dead. **Consider** resetting `pg_stat_statements` after the current eval-backfill push settles, so cumulative numbers reflect steady-state interactive traffic rather than one-off backfill probes.
- **Activity:** healthy activation — 9/10 most recent signups imported games; guests are importing large datasets; chess.com leads lichess ~2:1 on games.
