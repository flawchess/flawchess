# FlawChess DB Report — 2026-06-23

- **DB**: prod
- **Snapshot taken**: 2026-06-23T20:05:22Z (post-`VACUUM FULL game_positions`; supersedes the 17:59 pre-vacuum snapshot)
- **Sections run**: users / storage / performance / sanity
- **Note**: `pg_stat_statements` was reset at 2026-06-23T19:52:49Z, so query stats below cover only the ~12 min since. `pg_stat_database` (cache-hit ratio) was **not** reset — `stats_reset` = 2026-06-15, still 8-day cumulative.

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

**Activity note:** 158 total users, an even 79/79 registered-vs-guest split. Of the 10 most recent signups, 9 imported games (only guest 191 has zero). chess.com dominates (~2x lichess games). Unchanged since the earlier snapshot.

## 1. Storage Report

### Overview

| metric | value |
|---|---|
| Database size | **11 GB** (was 15 GB pre-vacuum) |
| Total games | 658,491 |
| Total positions | 48,162,374 |
| Avg positions/game | ~73 |

### Storage delta vs 17:59 pre-vacuum snapshot

A `VACUUM FULL game_positions` (320s) + `VACUUM ANALYZE` (170s) reclaimed bloat. **Row count is identical** (48.16M) — pure bloat reclaim, no data deleted.

| object | before | after | Δ |
|---|---|---|---|
| **DB total** | 15 GB | **11 GB** | **−4 GB (−27%)** |
| game_positions total | 12 GB | 8,376 MB | −3.6 GB |
| ↳ data | 6,682 MB | 4,685 MB | −2.0 GB |
| ↳ index | 5,815 MB | 3,691 MB | −2.1 GB |
| games | 2,297 MB | 2,297 MB | unchanged (not vacuumed) |
| game_flaws | 558 MB | 637 MB | +79 MB (ongoing writes) |

### Per-table breakdown (top consumers)

| table | data | index | total |
|---|---|---|---|
| game_positions | 4,685 MB | 3,691 MB | **8,376 MB** |
| games | 1,791 MB | 506 MB | 2,297 MB |
| game_flaws | 384 MB | 253 MB | 637 MB |
| opening_position_eval | 69 MB | 74 MB | 143 MB |
| benchmark_cohort_cdf | 8 MB | 5 MB | 13 MB |
| openings | 832 kB | 888 kB | 1,720 kB |
| llm_logs | 32 kB | 992 kB | 1,024 kB |

(All other tables < 1 MB.)

**Storage summary:** `game_positions` is now 8.4 GB of the 11 GB total (~76%), down from 12 GB. Its seven indexes shrank from 5.8 GB to 3.7 GB. `games` is unchanged at 2.3 GB and is now the largest un-reclaimed target — if more space is needed, a `VACUUM FULL games` would be the next lever (it carries ~28% dead-tuple-era bloat from the eval-backfill UPDATE churn).

## 2. Performance Analysis

> `pg_stat_statements` reset 2026-06-23T19:52:49Z — the window below is only ~12 min and reflects light post-maintenance traffic plus the vacuum itself. Not representative of steady-state load; re-check after a full day.

### Buffer cache hit ratio

**83.67%** — ⚠️ but **not a clean post-vacuum reading**. This counter lives in `pg_stat_database`, which was *not* reset (still cumulative since 2026-06-15), so it can't yet reflect the smaller table. To measure whether the 8.4 GB table improves cache residency, run `SELECT pg_stat_reset();` and re-check in a day. With `shared_buffers=2GB` the table still won't fully fit, but bloat removal should raise residency. **Do not raise `shared_buffers` above 2GB** (CLAUDE.md: amplifies checkpoint flush, revisits OOM history).

### Highest total time queries (post-reset window)

| total_ms | calls | avg_ms | query |
|---|---|---|---|
| 380,348 | 1,347 | **282.37** | eval-queue tier-2 pick (`full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL AND NOT is_guest`) |
| 320,364 | 1 | 320,364 | `VACUUM FULL VERBOSE game_positions` (one-off maintenance) |
| 169,540 | 1 | 169,540 | `VACUUM ANALYZE game_positions` (one-off maintenance) |
| 3,237 | 3 | 1,079 | game_flaws fetch (analytics) |

Excluding the two one-off VACUUMs, the **eval-queue tier-2 pick query again dominates** — and is the only recurring query of any weight (next recurring query is <80ms total).

### Tier-2 pick query: per-call improved post-vacuum

| | pre-vacuum (8-day window) | post-vacuum (12-min window) | Δ |
|---|---|---|---|
| avg_ms | 411.64 | 282.37 | **−31%** |
| max_ms | (n/a) | 523.24 | — |

The compacted heap means fewer pages per scan, so VACUUM FULL cut the hot query's per-call time by ~third, not just disk size. It remains the top optimization target — a tight partial index on `(full_evals_completed_at) WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL` should beat 282ms and cut the disk-read pressure behind the low cache-hit ratio.

### Sequential scans / index usage / dead tuples

Stats views (`pg_stat_user_tables`/`indexes`) accumulate independently of the pg_stat_statements reset; the 17:59 assessment still holds: no problematic seq-scan patterns (high counts only on tiny tables), no droppable indexes (all large `game_positions` indexes actively used), autovacuum current. The VACUUM FULL additionally reset `game_positions` dead tuples to ~0.

## 3. Sanity Checks

Both checks re-run identically (data unchanged since 17:59; vacuum doesn't alter row contents).

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

| metric | value |
|---|---|
| lichess games with flaws | 138,004 |
| **flaws but all counts NULL** | **0** ✅ |
| exact match | 138,733 |
| mistake mismatch | 1,331 |
| blunder mismatch | 756 |

Aggregate totals: mistakes 424,235 (oracle) vs 425,517 (game_flaws), +0.30%; blunders 641,037 vs 641,555, +0.08%.

**Verdict (Check A): PASS** — NULL-count gap 0, aggregates within ~0.3%.

### Check B — Eval coverage ≥90% vs oracle-column presence (Flaws Timeline gate)

| platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| chess.com | 281,661 | **0** ✅ | 281,661 |
| lichess | 139,078 | **0** ✅ | 139,078 |

**Verdict (Check B): PASS** — zero eval-covered games with NULL oracle columns on either platform.

## Summary

- **DB shrank 15 GB → 11 GB (−27%)** via `VACUUM FULL game_positions` — pure bloat reclaim, row count unchanged. `game_positions` went 12 GB → 8.4 GB (data −2.0 GB, indexes −2.1 GB).
- **`games` is now the largest un-reclaimed table** (2.3 GB, untouched). If more space is wanted, `VACUUM FULL games` is the next candidate — it churns heavily from eval-backfill UPDATEs.
- **Data integrity: clean.** Both sanity checks PASS, unchanged.
- **Hot query got faster:** the eval-queue tier-2 pick dropped 412ms → 282ms avg per call after the heap compaction. It's still the dominant query and still the top optimization target (wants a tight partial index).
- **Cache-hit ratio (83.67%) is not yet a valid post-vacuum reading** — `pg_stat_database` wasn't reset. Run `SELECT pg_stat_reset();` and re-check in a day to see if the smaller table improves cache residency.
- **Query stats window is only ~12 min** (pg_stat_statements reset at 19:52) — re-run this report after a day of normal traffic for a representative performance picture.
