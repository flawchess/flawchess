---
phase: 59-fix-endgame-conv-recov-per-game-stats
plan: 03
subsystem: endgame-analytics
tags: [backend, frontend-types, endgame, cleanup, deletion]
dependency_graph:
  requires:
    - Plan 59-02 completed (frontend consumers removed)
  provides:
    - "Slim EndgamePerformanceResponse (3 fields) end-to-end across Python + TypeScript"
    - "EndgameOverviewResponse without conv_recov_timeline sub-payload"
    - "Backend service/repository surface freed of conv/recov rolling-window code"
  affects:
    - "GET /api/endgames/overview — conv_recov_timeline key no longer in payload"
    - "GET /api/endgames/performance — aggregate_* / endgame_skill / relative_strength / overall_win_rate no longer returned"
tech-stack:
  added: []
  patterns:
    - "del param; retain signature compat note in _get_endgame_performance_from_rows"
key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - app/repositories/endgame_repository.py
    - tests/test_endgame_service.py
    - tests/test_endgames_router.py
    - frontend/src/types/endgames.ts
  deleted: []
decisions:
  - "Schemas trimmed in lockstep with service constructor edits so ty stayed clean after each commit"
  - "Retained entry_rows parameter on _get_endgame_performance_from_rows via del (signature compat with get_endgame_overview) per plan spec"
  - "TestLegacyEndpointsRemoved::test_conv_recov_timeline_returns_404 preserved — still valid, HTTP route gone since Phase 52"
metrics:
  duration: ~25 minutes
  completed: 2026-04-13
  tasks: 7
  files: 6
  commits: 5
---

# Phase 59 Plan 03: Remove orphaned conv/recov backend + frontend types — Summary

End-to-end deletion of the backend code and schemas orphaned by Plan 59-02's UI removal: stripped 9 fields from `EndgamePerformanceResponse`, dropped `conv_recov_timeline` from `EndgameOverviewResponse`, deleted `ConvRecovTimelinePoint` / `ConvRecovTimelineResponse` schemas, deleted `query_conv_recov_timeline_rows` repository function, deleted `_compute_conv_recov_rolling_series` and `get_conv_recov_timeline` service functions, simplified `_get_endgame_performance_from_rows`, updated 2 test modules, and slimmed the matching frontend TypeScript mirrors.

## What Changed

### `app/schemas/endgames.py`
- `EndgamePerformanceResponse`: kept only `endgame_wdl`, `non_endgame_wdl`, `endgame_win_rate`. Removed `overall_win_rate`, `aggregate_conversion_pct`, `aggregate_conversion_wins`, `aggregate_conversion_games`, `aggregate_recovery_pct`, `aggregate_recovery_saves`, `aggregate_recovery_games`, `relative_strength`, `endgame_skill`.
- Deleted `ConvRecovTimelinePoint` and `ConvRecovTimelineResponse` classes.
- `EndgameOverviewResponse`: removed `conv_recov_timeline: ConvRecovTimelineResponse` field.

### `app/services/endgame_service.py`
- Dropped `query_conv_recov_timeline_rows` from the repository-imports block.
- Dropped `ConvRecovTimelinePoint` / `ConvRecovTimelineResponse` from the schema-imports block.
- Deleted `_ENDGAME_SKILL_CONVERSION_WEIGHT` and `_ENDGAME_SKILL_RECOVERY_WEIGHT` constants and their comment.
- Replaced `_get_endgame_performance_from_rows` with a 17-line implementation that returns only the 3 retained fields. Parameter `entry_rows` retained for signature compat with `get_endgame_overview` (shared with `_compute_score_gap_material` and `_aggregate_endgame_stats`), silenced via `del entry_rows`.
- Deleted `_compute_conv_recov_rolling_series` and `get_conv_recov_timeline` entirely.
- `get_endgame_overview`: removed the `conv_recov_timeline = await get_conv_recov_timeline(...)` block and dropped `conv_recov_timeline=conv_recov_timeline` from the `EndgameOverviewResponse(...)` constructor call.
- Left `get_endgame_timeline`, `query_endgame_timeline_rows`, `_aggregate_endgame_stats`, `_compute_score_gap_material`, and `get_endgame_performance` untouched.

### `app/repositories/endgame_repository.py`
- Deleted `query_conv_recov_timeline_rows` (97 lines including docstring).
- Kept `query_endgame_timeline_rows` at its current 3-tuple signature (includes `per_type_rows`) per the plan scope clarification — still consumed by the surviving `EndgameTimelineChart.per_type`.
- Kept all imports (`type_coerce`, `aggregate_order_by`, `ARRAY`, `SmallIntegerType`, `PERSISTENCE_PLIES`) — still used by `query_endgame_entry_rows` and `query_clock_stats_rows`.

### `tests/test_endgame_service.py`
- `TestGetEndgamePerformance::test_zero_games_returns_all_zeros`: dropped assertions for `overall_win_rate`, `relative_strength`, `aggregate_conversion_pct`, `aggregate_recovery_pct`, `endgame_skill`.
- Deleted `test_overall_win_rate_across_all_games`, `test_relative_strength_above_100_possible`, `test_relative_strength_zero_when_overall_win_rate_zero`.
- Deleted the entire `TestEndgameGaugeCalculations` class (3 tests + `_entry_row` helper).
- `TestGetEndgamePerformanceSmoke::test_get_endgame_performance_returns_zeros_for_nonexistent_user`: dropped `overall_win_rate` / `relative_strength` assertions.
- `TestGetEndgameOverview`: removed `ConvRecovTimelineResponse` imports, `patch("...get_conv_recov_timeline")` context managers, `mock_conv.return_value = ConvRecovTimelineResponse(...)` assignments, `mock_conv.assert_called_once()` calls, and all `result.conv_recov_timeline.*` assertions. Renamed `test_overview_passes_window_to_both_timelines` → `test_overview_passes_window_to_timeline`.

### `tests/test_endgames_router.py`
- `TestOverviewEmptyUser::test_overview_empty_user_has_all_sub_payloads`: removed `assert "conv_recov_timeline" in data`.
- `TestOverviewEmptyUser::test_overview_default_window_is_50`: removed `assert data["conv_recov_timeline"]["window"] == 50`; docstring updated.
- `TestOverviewComposesAllPayloads::test_overview_with_seeded_games`: removed 3 conv_recov_timeline shape assertions.
- `TestGamesEndpointStillWorks::test_games_window_param_accepted`: removed `assert data["conv_recov_timeline"]["window"] == 25`.
- `TestLegacyEndpointsRemoved::test_conv_recov_timeline_returns_404`: **preserved** (HTTP 404 for the legacy route since Phase 52 still holds).

### `frontend/src/types/endgames.ts`
- `EndgamePerformanceResponse`: kept only the 3 retained fields; removed 9 fields in lockstep with the Python schema.
- Deleted `ConvRecovTimelinePoint` and `ConvRecovTimelineResponse` interfaces.
- `EndgameOverviewResponse`: removed `conv_recov_timeline: ConvRecovTimelineResponse`.

## Verification

- `uv run ty check app/ tests/` → All checks passed (0 errors).
- `uv run pytest -x -q` → 672 passed, 139 warnings.
- `uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py -x -q` → 135 passed.
- `cd frontend && npm run lint` → exit 0.
- `cd frontend && npm run build` → exit 0 (2 prerendered pages, PWA manifest generated).
- `cd frontend && npm run knip` → exit 0 (no transient ignores needed).
- Grep gates:
  - `grep -rn "aggregate_conversion\|aggregate_recovery\|endgame_skill\|relative_strength" app/ frontend/src` → ZERO matches.
  - `grep -rn "ConvRecovTimelinePoint\|ConvRecovTimelineResponse\|_compute_conv_recov_rolling_series\|get_conv_recov_timeline\|query_conv_recov_timeline_rows" app/ frontend/src tests` → ZERO matches.
  - `grep -n "export function EndgamePerformanceSection" frontend/src/components/charts/EndgamePerformanceSection.tsx` → EXACTLY ONE match (preserved).
  - `grep -n "test_conv_recov_timeline_returns_404" tests/test_endgames_router.py` → EXACTLY ONE match (preserved).

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pre-flight grep (read-only) | — | — |
| 2 | Slim EndgamePerformanceResponse / delete ConvRecov schemas | `53b0bc9` | `app/schemas/endgames.py` |
| 3 | Remove conv/recov service helpers; simplify performance builder | `3b1c69c` | `app/services/endgame_service.py` |
| 4 | Delete query_conv_recov_timeline_rows | `f8c124b` | `app/repositories/endgame_repository.py` |
| 5 | Update backend tests | `7099da0` | `tests/test_endgame_service.py`, `tests/test_endgames_router.py` |
| 6 | Slim frontend endgame types + verify build | `e68cb92` | `frontend/src/types/endgames.ts` |
| 7 | Full-suite integration check (verification only) | — | — |

## Deviations from Plan

None in scope. Plan executed as written.

### Plan-text nuance on Task 1 grep gates

The Task 1 acceptance criteria say the first five grep commands must return **zero** matches. In reality, `frontend/src/types/endgames.ts` still contained the removed fields at the start of the plan (they are TS mirrors of the Python schema, scheduled for deletion in Task 6), and `EndgamePerformanceSection.tsx` retained a JSDoc line mentioning the removed `EndgameGaugesSection` by name (historical comment). No surviving **consumer** reads any removed field — every hit was either a type declaration (Task 6 territory) or historical documentation. Task 1 proceeded safely and Task 6 cleared the type-mirror matches. Noting here rather than re-scoping the plan.

## Authentication Gates

None.

## Known Stubs

None.

## Out-of-Scope Discoveries

`uv run ruff check .` reports 2 pre-existing F841 errors at `app/services/endgame_service.py:857` and `:860` (`game_id` and `termination` locals assigned but never used inside `_compute_clock_pressure`). Confirmed pre-existing by `git stash && ruff check` on the base commit `a38e3ba`, and same errors were flagged (and left) by plan 59-01 per its SUMMARY. Out of scope for this plan — touching them would widen surface into Phase 54 clock-pressure code unrelated to the conv/recov removal. They do not cause any test or type-check failure; Task 7's integration check passes for every gate except `ruff check .` (which is affected only by these two unrelated pre-existing errors).

## Self-Check: PASSED

- `app/schemas/endgames.py` — present (modified, commit `53b0bc9`).
- `app/services/endgame_service.py` — present (modified, commit `3b1c69c`).
- `app/repositories/endgame_repository.py` — present (modified, commit `f8c124b`).
- `tests/test_endgame_service.py` — present (modified, commit `7099da0`).
- `tests/test_endgames_router.py` — present (modified, commit `7099da0`).
- `frontend/src/types/endgames.ts` — present (modified, commit `e68cb92`).
- Commits `53b0bc9`, `3b1c69c`, `f8c124b`, `7099da0`, `e68cb92` — all found in `git log`.
- Full 672-test backend suite green; full frontend lint/build/knip green; ty clean.
