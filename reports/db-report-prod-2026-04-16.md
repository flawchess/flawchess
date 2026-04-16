# FlawChess DB Report — 2026-04-16

- **DB**: prod
- **Snapshot taken**: 2026-04-16T21:36:01Z
- **Sections run**: users / storage / performance

## 0. Users Overview

### User summary

| Total users | Registered | Guests |
|-------------|------------|--------|
| 42 | 33 | 9 |

### 10 most recent users

| ID | Email | chess.com | lichess | Guest? | Created | Last login | Games | Positions |
|----|-------|-----------|---------|--------|---------|------------|-------|-----------|
| 49 | guest_471b…@guest.local | — | — | yes | 2026-04-16 | 2026-04-16 | 0 | 0 |
| 48 | guest_9eec…@guest.local | bjuzfgjiiu | — | yes | 2026-04-16 | 2026-04-16 | 72 | 4,577 |
| 47 | guest_f75d…@guest.local | — | — | yes | 2026-04-16 | 2026-04-16 | 0 | 0 |
| 46 | guest_5ddf…@guest.local | — | juebjueb | yes | 2026-04-14 | 2026-04-14 | 6,906 | 460,847 |
| 45 | guest_e526…@guest.local | — | tanneywanney25 | yes | 2026-04-14 | 2026-04-14 | 38,953 | 2,860,332 |
| 44 | robin.villoz@gmx.net | Rob3i | — | no | 2026-04-13 | 2026-04-13 | 181 | 10,190 |
| 43 | zaibleid1@gmail.com | — | altfeldeviata | no | 2026-04-12 | 2026-04-12 | 229 | 13,524 |
| 42 | maximus.kuykendall@gmail.com | maxkuykendall | — | no | 2026-04-12 | 2026-04-12 | 82 | 4,108 |
| 41 | guest_5a9e…@guest.local | — | — | yes | 2026-04-11 | 2026-04-11 | 0 | 0 |
| 38 | joel.mueller02@gmail.com | Guapjo | — | no | 2026-04-10 | 2026-04-10 | 45 | 2,423 |

### Platform breakdown

| Platform | Users | Games |
|----------|-------|-------|
| chess.com | 30 | 149,146 |
| lichess | 20 | 102,524 |

**Activity notes**

- 3 of the 10 most recent signups (all guests) have imported zero games — curious who abandons right after signup.
- 2 guest lichess imports (IDs 45 & 46) account for **45,859 games (~18%)** and **3.32M positions (~18%)** of the entire DB — by far the largest individual tenants.
- Registered-to-guest ratio is 33 : 9. Guest accounts skew the storage numbers heavily (mostly via the two big lichess scrapes above).

---

## 1. Storage Report

### Overview

| DB size | Total games | Total positions | Avg positions/game |
|---------|-------------|-----------------|--------------------|
| 6,971 MB | 251,670 | 17,982,102 | 71.5 |

### Per-table breakdown

| Table | Data | Indexes | Total |
|-------|------|---------|-------|
| game_positions | 2,300 MB | 3,780 MB | 6,080 MB |
| games | 795 MB | 84 MB | 878 MB |
| openings | 1,600 kB | 1,624 kB | 3,224 kB |
| import_jobs | 24 kB | 248 kB | 272 kB |
| users | 24 kB | 72 kB | 96 kB |
| oauth_account | 16 kB | 80 kB | 96 kB |
| position_bookmarks | 24 kB | 64 kB | 88 kB |
| alembic_version | 8 B | 16 kB | 24 kB |

### Per-index breakdown

| Index | Table | Size |
|-------|-------|------|
| ix_gp_user_full_hash_move_san | game_positions | 999 MB |
| ix_gp_user_full_hash | game_positions | 788 MB |
| ix_gp_user_white_hash | game_positions | 583 MB |
| ix_gp_user_black_hash | game_positions | 577 MB |
| game_positions_pkey | game_positions | 415 MB |
| ix_gp_user_endgame_game | game_positions | 208 MB |
| ix_game_positions_game_id | game_positions | 144 MB |
| ix_gp_user_endgame_class | game_positions | 65 MB |
| uq_games_user_platform_game_id | games | 32 MB |
| games_pkey | games | 12 MB |
| ix_games_user_id | games | 6,272 kB |
| uq_openings_eco_name_pgn | openings | 888 kB |
| ix_openings_eco_name | openings | 512 kB |
| openings_pkey | openings | 184 kB |
| (others) | users/oauth/bookmarks/… | 16 kB each |

**Storage notes**

- `game_positions` is **87% of DB size** (6,080 / 6,971 MB). All seven Zobrist/endgame indexes on that table dominate.
- Index-to-data ratio on `game_positions` is **1.64×** (3,780 MB indexes vs 2,300 MB data) — this is extreme. Each of the four user-scoped hash indexes alone (`full_hash_move_san`, `full_hash`, `white_hash`, `black_hash`) is larger than the table's own data.
- `ix_gp_user_full_hash` (788 MB) and `ix_gp_user_full_hash_move_san` (999 MB) overlap in purpose — the composite likely makes the simpler one partially redundant for move-explorer lookups (see performance notes below).

---

## 2. Performance Analysis

### Buffer cache hit ratio

**88.87%** — ⚠️ below the 95% "good" threshold. Worth investigating.

The server has 7.6 GB RAM (plus 2 GB swap). The DB is 6,971 MB. Active working set (hash indexes + games data) easily exceeds shared_buffers. Expect disk reads on any cold query.

### Slowest queries by avg time (top 10, >500ms only)

| avg_ms | max_ms | calls | total_ms | query (truncated) |
|--------|--------|-------|----------|-------------------|
| 16,880 | 16,880 | 1 | 16,880 | endgame clock-diff: `first_endgame` + `clock_raw` over all game_positions |
| 13,695 | 17,235 | 2 | 27,390 | endgame clock-raw bucketed by TC / user_color |
| 13,657 | 13,657 | 1 | 13,657 | endgame bucketed by result+color |
| 13,571 | 13,571 | 1 | 13,571 | endgame bucketed by user/tc/rating |
| 9,998 | 9,998 | 1 | 9,998 | endgame bucketed (variant) |
| 9,750 | 10,119 | 2 | 19,501 | endgame bucketed (variant) |
| 7,521 | 7,521 | 1 | 7,521 | endgame bucketed (variant) |
| 7,461 | 7,461 | 1 | 7,461 | endgame clock-raw (variant) |
| 5,529 | 5,529 | 1 | 5,529 | endgame bucketed (variant) |
| 5,093 | 5,093 | 1 | 5,093 | endgame entry_after material_imbalance |
| 4,668 | 4,668 | 1 | 4,668 | endgame bucketed (variant) |
| 1,590 | 2,479 | 2 | 3,180 | endgame_game_ids + rows aggregate |
| 1,408 | 1,408 | 1 | 1,408 | **this report's Query 0b** (users + games + positions join) |
| 1,279 | 1,279 | 1 | 1,279 | endgame_class position counts |

Nearly every slow query shares the same shape:

```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= $N
),
...
```

That `first_endgame` CTE scans the endgame class index for **every game in the DB** (not user-scoped) before joining. On 18M positions this is expensive.

### Highest total-time queries

| total_ms | calls | avg_ms | query |
|----------|-------|--------|-------|
| 27,390 | 2 | 13,695 | endgame clock-raw bucketed |
| 19,501 | 2 | 9,750 | endgame bucketed variant |
| 16,880 | 1 | 16,880 | endgame clock-diff |
| 13,657 | 1 | 13,657 | endgame bucketed |
| 13,571 | 1 | 13,571 | endgame bucketed |
| 10,546 | **264,974** | 0.04 | `UPDATE games SET base_time_seconds/increment/tc_bucket WHERE id = $1` — backfill migration |
| 9,998 | 1 | 9,998 | endgame bucketed |
| 7,521 | 1 | 7,521 | endgame bucketed |
| 1,433 | 3 | 478 | `DELETE FROM game_positions WHERE user_id = $1` (guest cleanup) |

Endgame queries dominate even with just 1-2 calls — each is a full-table scan on `game_positions`.

### Sequential scan analysis

| Table | seq_scan | seq_tup_read | idx_scan | Verdict |
|-------|----------|--------------|----------|---------|
| game_positions | 10 | 110,910,604 | 3,239,549 | OK — 10 seq scans but each reads 11M rows; those 10 are likely the giant endgame CTEs above |
| games | 7 | 1,570,989 | 2,829,134 | OK — mostly indexed |
| openings | 28 | 101,948 | 0 | OK — 5,000-row reference table; Postgres correctly prefers seq scan |
| users | 5,315 | 39,204 | 3 | OK — 42 rows; seq scan is optimal |
| oauth_account | 551 | 12,122 | 0 | OK — tiny table |
| import_jobs | 75 | 5,105 | 0 | OK — tiny table |
| position_bookmarks | 18 | 810 | 0 | OK — tiny table |

### Index usage

**Indexes with 0 scans** (all are either on tiny tables, used for FK/PK integrity, or legitimate auth paths):

| Index | Size | Keep or drop? |
|-------|------|---------------|
| game_positions_pkey | 415 MB | **Keep** — PK required |
| ix_openings_eco_name | 512 kB | Keep — opening-seeding lookups |
| uq_openings_eco_name_pgn | 888 kB | Keep — uniqueness constraint |
| openings_pkey | 184 kB | Keep — PK |
| ix_import_jobs_user_id | 16 kB | Keep — FK |
| import_jobs_pkey | 16 kB | Keep — PK |
| bookmarks_pkey | 16 kB | Keep — PK |
| ix_position_bookmarks_user_id | 16 kB | Keep — FK |
| ix_users_email | 16 kB | Keep — login lookup |
| oauth_account_pkey / ix_oauth_account_* | 16 kB | Keep — OAuth flow |
| alembic_version_pkc | 16 kB | Keep — migrations |

Nothing worth dropping. The 0-scan counts on tiny tables simply mean Postgres preferred seq scans (correct).

**Potentially redundant large indexes** (high cost, overlapping coverage):

- `ix_gp_user_full_hash` (788 MB, 336 scans) vs `ix_gp_user_full_hash_move_san` (999 MB, 365 scans) — the composite covers the simpler index's prefix. If all queries using `ix_gp_user_full_hash` filter by `(user_id, full_hash)` and don't need to fetch `move_san`, dropping the shorter one would save **788 MB** but may slow index-only-scan candidates. Needs EXPLAIN ANALYZE on the move-explorer endpoint before acting.
- `ix_gp_user_white_hash` (583 MB, 35 scans) and `ix_gp_user_black_hash` (577 MB, 17 scans) are used an order of magnitude less than the full_hash indexes — they serve the "my pieces only" (system-opening) filter. Keep; low scan count reflects low feature usage, not redundancy.

### Dead tuples / autovacuum

| Table | n_live | n_dead | Dead % | Last autovacuum |
|-------|--------|--------|--------|-----------------|
| game_positions | 0 (!) | 1,007,523 | ∞ | **never** |
| games | 249,859 | 15,223 | 5.7% | 2026-04-14 |
| users | 1 | 12 | — | never |
| others | small | small | — | mostly never |

⚠️ **`game_positions` has never been autovacuumed** and has 1,007,523 dead tuples from recent `DELETE … WHERE user_id = $1` runs (visible in Query 5). `n_live_tup = 0` also means the planner thinks the table is empty — autoanalyze has never run either. This is almost certainly contributing to bad query plans on the endgame CTEs, and is the most likely root cause of the slow endgame queries plus the low cache hit ratio (poor plan → extra reads).

**Note**: `pg_stat_database.stats_reset` is NULL — cumulative stats are since DB inception. So some of the slow-query averages include early unoptimized runs. Cannot isolate "current" behavior without resetting.

### Recommendations

**Recommended (do soon)**

1. **Run `VACUUM ANALYZE game_positions`** manually. This is the single highest-impact action. It will:
   - Reclaim the 1M+ dead tuples from recent guest-account deletes (space back)
   - Populate planner statistics (`n_live_tup` currently 0 — planner has no idea what's in the table)
   - Very likely improve endgame-query performance substantially without any code change
2. **Investigate why autovacuum hasn't run on `game_positions`**. Check `autovacuum_vacuum_scale_factor` — on an 18M-row table the default (20% of live rows) is ~3.6M, so vacuum is gated behind a huge threshold. Set a per-table override: `ALTER TABLE game_positions SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);`

**Monitor**

3. After the VACUUM ANALYZE, `pg_stat_statements_reset()` and re-measure in a week. Current stats include pre-index-tuning history.
4. Cache hit ratio (88.87%) — expected to improve after stats/vacuum. If still <95% after a week, consider bumping `shared_buffers` (currently likely default 128 MB — far too small for a 7 GB DB).

**Consider**

5. **Endgame CTE optimization** — the `first_endgame` CTE materializes a min(ply) per game across ALL users. Most endgame queries are per-user; pushing `WHERE user_id = $N` into the CTE (when applicable) would let `ix_gp_user_endgame_game` do a bounded scan instead of a full 18M-row index scan. Worth an EXPLAIN ANALYZE pass on the endgame-analytics endpoints.
6. **Shared_buffers tuning** — at 7.6 GB RAM, Postgres should have ~2 GB `shared_buffers` (25% rule of thumb). Requires a config change on the server.

**No action needed**

- Index list: none of the 0-scan indexes are dropworthy (all FK/PK/auth).
- Sequential scans on `openings`/`users`/small tables are correct planner behavior.

---

## Summary

- **DB size**: 6,971 MB, dominated by `game_positions` (6,080 MB = 87%). Index overhead on that table is 1.64× the data itself.
- **Two lichess guest imports** account for ~18% of all games and positions.
- **Cache hit ratio is 88.87%** — below healthy. Likely tied to the next issue.
- **`game_positions` has never been autovacuumed or analyzed** — 1M+ dead tuples, `n_live_tup = 0`, so the planner is working blind. **Fix first**: `VACUUM ANALYZE game_positions` + a per-table autovacuum scale factor override.
- **Slow queries are all endgame-analytics CTEs** (5–17 s each). The `first_endgame` CTE scans the entire positions table globally instead of per-user. Post-analyze, re-check with EXPLAIN ANALYZE; if still slow, push user_id into the CTE.
- **Index redundancy candidate**: `ix_gp_user_full_hash` (788 MB) is likely covered by the composite `ix_gp_user_full_hash_move_san` — verify and drop if confirmed. No other indexes worth dropping.
