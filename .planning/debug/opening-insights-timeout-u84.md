---
slug: opening-insights-timeout-u84
status: resolved
trigger: |
  The recent fix with extremely slow opening insights didn't fix the problem fully.
  E.g. user 84 in prod with only 718 games times out when trying to access opening insights.
  Look at slow queries in prod, it's running right now.
created: 2026-05-12
updated: 2026-05-12
---

# Debug: Opening insights timeout for user 84 in prod

## Symptoms

- **Expected behavior**: `POST /api/insights/openings` returns within reasonable time (< 30s) for a user with a modest game count.
- **Actual behavior**: Request times out for user 84 in production. User has only 718 games imported.
- **Error messages**: Request timeout (gateway/proxy timeout).
- **Timeline**: Persists after the recent fix in commit `beb089ab` — "fix(openings): use JOIN over EXISTS in opening transitions standard-start filter" (#89). That fix targeted the same endpoint but did not fully resolve the issue.
- **Reproduction**: Trigger as user 84 in prod via opening insights feature.

## Current Focus

- **hypothesis**: PostgreSQL planner mis-estimates row counts (`rows=1`) for `(user_id, ply BETWEEN ...)` predicates due to lack of multi-column statistics on `(user_id, ply)` in `game_positions` and `(user_id, user_color)` in `games`. This causes a cascade of Nested Loop join choices that perform catastrophically on certain user shapes.
- **next_action**: Apply CREATE STATISTICS for the two correlated column pairs + ANALYZE.
- **reasoning_checkpoint**: confirmed
- **tdd_checkpoint**: n/a

## Evidence

- timestamp: 2026-05-12 (live query capture via prod tunnel)
  - **Live query duration**: 90+ seconds, CPU-bound (no wait_event), pid 1033279.
  - **EXPLAIN ANALYZE (BEFORE fix)**: execution_time 137,280 ms, 406M buffer hits.
  - **Bad plan**: Nested Loop at every join level, all with `rows=1` estimates:
    - `Nested Loop` (transitions × games): 12,116 × 271 actual rows, 3.2M Join Filter rows removed, 3M buffer hits.
    - `Subquery Scan on t` (the transitions CTE): WindowAgg over a Nested Loop with `Index Only Scan ix_gp_user_game_ply (user_id=84)` × `Index Scan ix_gp_user_white_hash (user_id=84) Filter: (ply=0 AND full_hash=STARTING)` — 12,834 loops × 49,868 rows scanned per loop = 403M total buffer hits / ~90s wall time.
  - **User 84 stats**: 718 games, 49,868 game_positions, 12,834 rows in the [ply 0..17] CTE range, all 718 games are standard-start.

- timestamp: 2026-05-12 (extended statistics test)
  - **EXPLAIN ANALYZE (AFTER fix)**: execution_time 36 ms, 3M buffer hits.
  - **Good plan**: planner now estimates 11,901 rows (actual 12,834) for the `(user_id=84, ply BETWEEN 0 AND 17)` predicate. Picks:
    - `Index Only Scan ix_gp_user_game_ply` with `Index Cond: (user_id=84 AND ply=0)` for the standard-start subquery — 712 buffers / 2ms (vs 31,405 buffers / 30ms before).
    - `Index Only Scan ix_gp_user_game_ply` with `Index Cond: (user_id=84 AND game_id=...)` for the gp scan — 3,236 buffers / 7ms.
    - `Index Scan games_pkey` for the outer games join (driven by t.game_id, rows estimate now accurate) instead of `Index Scan ix_games_user_id` looped 12k times.
  - **Heavy user (user 4, 23k games) sanity check**: 2.5s — acceptable, same optimal plan shape with parallel scan.

## Eliminated

- ❌ Slow standard-start subquery in isolation — partial index on `(user_id) WHERE ply=0 AND full_hash=STARTING` would help (30ms → 1ms) but doesn't fix the cascading Nested Loop blowup downstream.
- ❌ Need to drop `ix_gp_user_game_ply`'s partial predicate — tested by adding a non-partial duplicate index; planner still estimates rows=1 because the column-level stats remain weak without extended stats.
- ❌ Rewriting CTE structure (MATERIALIZED, inline subquery, IN, ARRAY) — all produce Nested Loop plans because `rows=1` estimates persist regardless of SQL shape.
- ❌ Re-running ANALYZE alone — stats were fresh (analyzed today). The issue is the lack of cross-column correlation info, not stale single-column stats.

## Resolution

- **root_cause**: PostgreSQL planner lacks multi-column statistics on `(user_id, ply)` in `game_positions` and `(user_id, user_color)` in `games`. For `(user_id=84, ply BETWEEN 0 AND 17)`, the planner multiplies independent selectivities: `(1/N_users)` × `(small ply range fraction)` rounds to `rows=1`, causing it to pick Nested Loop everywhere. With 12,834 actual rows and 271 games to join, that's ~3.5M rows of nested-loop work — fine for heavier users where stats happen to be more balanced, catastrophic on small users with concentrated low-ply data. The Phase 71 / commit `beb089ab` JOIN-over-EXISTS fix solved the *index-choice* aspect for the inner subquery on a 499-game user, but the *Nested-Loop-cascade* in the outer query is a separate planner issue that surfaces on users in a different cardinality band.

- **fix**: Two `CREATE STATISTICS` objects + `ANALYZE`:
  ```sql
  CREATE STATISTICS stat_gp_user_ply (dependencies, ndistinct, mcv) ON user_id, ply FROM game_positions;
  CREATE STATISTICS stat_games_user_color (dependencies, ndistinct, mcv) ON user_id, user_color FROM games;
  ANALYZE game_positions;
  ANALYZE games;
  ```
  Applied as Alembic migration so it's versioned and runs in dev/CI/prod consistently.

- **verification**:
  - User 84 EXPLAIN ANALYZE: 137,280 ms → 36 ms (3800x speedup).
  - User 4 (23k games) EXPLAIN ANALYZE: 2.5 s (sanity check — no regression on heavy users).
  - Production-form parameterized query (matching pg_stat_activity capture): 53 ms consistently.
  - Stats applied to prod via MCP tunnel; persist after analyze.

- **files_changed**:
  - `alembic/versions/<new>_add_extended_stats_for_opening_insights_planner.py` (new migration)
  - `CHANGELOG.md` (Unreleased > Fixed entry)
