---
phase: 52
plan: 1
subsystem: backend
tags: [performance, endgame, query-consolidation, api]
dependency_graph:
  requires: []
  provides: [GET /api/endgames/overview, 2-query timeline implementation]
  affects: [app/repositories/endgame_repository.py, app/services/endgame_service.py, app/schemas/endgames.py, app/routers/endgames.py]
tech_stack:
  added: []
  patterns: [sequential AsyncSession queries, Python-side row deduplication, composed response model]
key_files:
  created:
    - tests/test_endgames_router.py
  modified:
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/schemas/endgames.py
    - app/routers/endgames.py
    - tests/test_endgame_repository.py
    - tests/test_endgame_service.py
decisions:
  - "Used GROUP BY (game_id, endgame_class) single-pass query instead of UNION ALL — cleaner and exploits ix_gp_user_endgame_game index"
  - "Overall endgame series derived in Python from Query A rows by deduplicating game_ids — eliminates old separate overall-endgame query"
  - "Preserved public signature tuple[list[Row], list[Row], dict[int, list[Row]]] for zero-change service layer compatibility"
  - "get_endgame_stats/performance/timeline/get_conv_recov_timeline kept as internal helpers called sequentially by get_endgame_overview"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-11T07:51:46Z"
  tasks_completed: 1
  files_changed: 7
---

# Phase 52 Plan 01: Backend — Timeline Query Collapse + Overview Endpoint Consolidation Summary

**One-liner:** Rewrote `query_endgame_timeline_rows` from 8 sequential DB queries down to 2 (one grouped per-class pass + one non-endgame NOT IN), and added `GET /api/endgames/overview` composing all four endgame dashboard payloads on a single AsyncSession, removing the four legacy individual endpoints.

## What Was Built

### Repository: `query_endgame_timeline_rows` (2-query rewrite)

**Before:** 8 sequential `session.execute()` calls — 1 overall endgame, 1 non-endgame, 6 per-class.

**After:** 2 `session.execute()` calls:
- **Query A:** Single pass over `game_positions` grouped by `(game_id, endgame_class)` with `HAVING count(ply) >= 6`. Returns `(game_id, endgame_class, played_at, result, user_color)` rows ordered by `played_at ASC`. Python side buckets into `per_type_rows` dict and deduplicates `game_id` to produce the overall `endgame_rows` list.
- **Query B:** Non-endgame games via `NOT IN` subquery (unchanged logic).

All 6 class slots (1..6) are pre-initialized to empty lists for deterministic downstream iteration. The public function signature is preserved exactly so the service layer required zero changes.

### Schema: `EndgameOverviewResponse`

New Pydantic model in `app/schemas/endgames.py` composing the four existing response models:
```python
class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    conv_recov_timeline: ConvRecovTimelineResponse
```

### Service: `get_endgame_overview`

New function in `app/services/endgame_service.py` that calls the four individual service functions **sequentially** on one `AsyncSession` (no `asyncio.gather`):
1. `get_endgame_stats`
2. `get_endgame_performance`
3. `get_endgame_timeline` (with `window`)
4. `get_conv_recov_timeline` (with `window`)

### Router: consolidated to 2 endpoints

Removed: `GET /stats`, `GET /performance`, `GET /timeline`, `GET /conv-recov-timeline`

Added: `GET /overview` with the union of all four parameter surfaces plus `window` (default 50, clamped 5–200).

Kept: `GET /games` (unchanged, orthogonal to overview filters).

### Tests

- **`test_endgame_repository.py`:** Added `TestQueryEndgameTimelineRows` with 4 tests covering empty user, per-class bucketing for selective classes (1/3/5 populated, 2/4/6 empty), 3-tuple shape verification, and non-endgame bucketing.
- **`test_endgame_service.py`:** Added `TestGetEndgameOverview` with 3 tests — composition (all 4 sub-functions called once), window forwarding to both timelines, and empty-user smoke test.
- **`tests/test_endgames_router.py`:** New file, 14 integration tests — auth guard, empty user shape, seeded payload composition, legacy 404s for all 4 removed paths, and `/games` parity.

## Verification

- `ruff check .` → All checks passed
- `uv run ty check app/ tests/` → zero errors
- `uv run pytest -x` → 599 passed (no failures, no regressions)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

The `ruff format --check` exits non-zero on ~83 pre-existing files (unrelated to this plan's changes — `app/models/game.py` fails format check on the base commit). The plan only requires `ruff check .` (lint), which passes. Pre-existing format state not touched per scope boundary rule.

## Threat Flags

None — no new network endpoints beyond the planned `/overview` route, no new auth paths, no schema changes, no file access patterns.

## Known Stubs

None — all four sub-payloads are wired to real DB queries with no hardcoded placeholders.

## Self-Check: PASSED

- FOUND: app/repositories/endgame_repository.py
- FOUND: app/schemas/endgames.py
- FOUND: app/services/endgame_service.py
- FOUND: app/routers/endgames.py
- FOUND: tests/test_endgames_router.py
- FOUND: commit d8483f7
