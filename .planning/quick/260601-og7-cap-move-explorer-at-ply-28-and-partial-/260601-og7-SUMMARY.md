---
phase: quick-260601-og7
plan: 01
subsystem: openings/db-indexes
tags: [performance, opening-explorer, db-index, partial-index, zobrist, migration]
dependency_graph:
  requires: []
  provides: [MAX_EXPLORER_PLY constant, partial hash indexes, capped hash queries, frontend explorer cap]
  affects: [game_positions table indexes, opening explorer WDL queries, bookmark suggestion queries]
tech_stack:
  added: [frontend/src/lib/explorer.ts]
  patterns: [CONCURRENTLY partial index migration, temp-name + rename trick]
key_files:
  created:
    - app/models/game_position.py (MAX_EXPLORER_PLY constant + partial postgresql_where on 3 indexes)
    - alembic/versions/20260601_154355_84fd28051d7d_partial_index_hash_columns_at_ply_28_.py
    - frontend/src/lib/explorer.ts
  modified:
    - app/repositories/stats_repository.py
    - app/repositories/openings_repository.py
    - app/services/openings_service.py
    - CHANGELOG.md
decisions:
  - "MAX_EXPLORER_PLY=28 confirmed via SEED-033: ECO ceiling 28, openings.ply_count max=36, 28 covers full ECO headroom"
  - "position_bookmark_repository needs no ply predicate: ply_max=8 is already well within the partial index boundary"
  - "query_wdl_counts: covered via _build_base_query which received the ply predicate (see deviation note)"
metrics:
  duration: ~45 minutes
  completed: 2026-06-01
  tasks_completed: 4
  files_modified: 7
---

# Phase quick-260601-og7 Plan 01: Cap Explorer at Ply 28 + Partial Hash Indexes Summary

**One-liner:** Partial Zobrist-hash indexes (`WHERE ply <= 28`) and hard frontend explorer cap tied to a shared `MAX_EXPLORER_PLY=28` constant, reclaiming ~3 GB of index footprint with no data loss.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| 1: Model constant + partial indexes | 557fceed | MAX_EXPLORER_PLY=28 + postgresql_where on 3 hash indexes |
| 2: Alembic migration | 1fcedea3 | CONCURRENTLY rebuild + verified upgrade/downgrade/upgrade cycle |
| 3: Capped hash queries | 0948ab61 | ply <= MAX_EXPLORER_PLY in all game_positions hash lookups |
| 4: Frontend explorer cap | deb0b25f | explorer.ts + makeMove guard |
| CHANGELOG | b7735b38 | Changelog entry added |

## Pre-PR Gate Results

All gates green (2026-06-01):

```
ruff format app/ tests/     -> 203 files left unchanged
ruff check app/ tests/ --fix -> All checks passed!
ty check app/ tests/         -> All checks passed!
pytest -n auto -x            -> 2198 passed, 16 skipped (83.64s)
npm run lint                 -> no output (clean)
npm test -- --run            -> 63 test files, 745 tests passed
```

## Deviations from Plan

### query_wdl_counts vs SEED-033 divergence (confirmed, documented)

The SEED-033 seed stated that `query_wdl_counts` in `openings_repository.py` was "already bounded by `ix_gp_user_game_ply WHERE ply BETWEEN 0 AND 17`". This is **incorrect for the hash lookup path**.

`query_wdl_counts` delegates to `_build_base_query` which (when `target_hash is not None`) does:
```python
.join(GamePosition, GamePosition.game_id == Game.id)
.where(GamePosition.user_id == user_id, hash_column == target_hash)
```

This `hash_column == target_hash` IS a game_positions hash equality lookup that should use the partial hash index. It is NOT served by `ix_gp_user_game_ply` (which serves the transition aggregation for opening insights, not point lookups by hash). The plan correctly identified this divergence and instructed us to add the predicate regardless.

Fix applied: added `GamePosition.ply <= MAX_EXPLORER_PLY` to `_build_base_query` (in the position-filtered branch), which propagates to all callers: `query_wdl_counts`, `query_all_results`, and `query_matching_games`.

### position_bookmark_repository: no change needed (confirmed)

`get_top_positions_for_color`, `suggest_match_side`, and the representative-row fetch in the inner loop all use `GamePosition.ply.between(ply_min, ply_max)` where `ply_max` comes from the router constant `PLY_MAX = 8`. Since 8 << 28, these queries are already strictly within the partial index boundary. Adding a redundant `MAX_EXPLORER_PLY` predicate would add noise without benefit.

## Known Stubs

None. All code paths are fully wired.

## Threat Flags

None. This change is index-only (no new endpoints, no auth path changes, no schema changes beyond index rebuild).

## Pending: Prod Bookmark Depth Check (Task 5, Item 1)

This MUST be run by the human before shipping to main:

1. Open tunnel: `bin/prod_db_tunnel.sh`
2. Via `mcp__flawchess-prod-db__query` tool, run:
   ```sql
   SELECT count(*) FROM position_bookmarks pb
   WHERE NOT EXISTS (
     SELECT 1 FROM game_positions gp
     WHERE gp.user_id = pb.user_id
       AND (gp.full_hash = pb.target_hash
            OR gp.white_hash = pb.target_hash
            OR gp.black_hash = pb.target_hash)
       AND gp.ply <= 28
   );
   ```
   Expected: **0**. If > 0, stop and surface to Adrian for the degraded/grandfather decision.
3. Close tunnel: `bin/prod_db_tunnel.sh stop`

Only after this check returns 0 (or a decision is recorded) should this branch be squash-merged to main.

## Self-Check

### Created files exist:
- [x] `app/models/game_position.py` - MAX_EXPLORER_PLY constant present
- [x] `alembic/versions/20260601_154355_84fd28051d7d_partial_index_hash_columns_at_ply_28_.py` - exists
- [x] `frontend/src/lib/explorer.ts` - created
- [x] Migration verified on dev DB: all 3 indexes show `WHERE (ply <= 28)` in pg_indexes

### Commits exist:
- [x] 557fceed - Task 1 model
- [x] 1fcedea3 - Task 2 migration
- [x] 0948ab61 - Task 3 hash queries
- [x] deb0b25f - Task 4 frontend cap
- [x] b7735b38 - CHANGELOG

## Self-Check: PASSED
