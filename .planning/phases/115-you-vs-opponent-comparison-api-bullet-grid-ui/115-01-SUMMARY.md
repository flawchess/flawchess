---
phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, postgresql, statistics, game-flaws]

# Dependency graph
requires:
  - phase: 114-benchmark-flaw-delta-zone-computation
    provides: §5 zone constants Q1/Q3/p05/p95, unified estimator formula, ply_count denominator
  - phase: 113-game-flaws-both-players
    provides: game_flaws table with both-player rows, is_opponent_expr split
provides:
  - "GET /api/library/flaw-comparison endpoint returning 15 FlawBullet objects with mean per-game delta + 95% CI"
  - "FlawDeltaZoneSpec frozen dataclass + FLAW_DELTA_ZONES registry (15 entries, §5 verbatim)"
  - "FlawBullet + FlawComparisonResponse Pydantic schemas"
  - "fetch_flaw_comparison LEFT JOIN per-game aggregation (30 COUNT FILTER columns)"
  - "get_flaw_comparison service with FLAW_COMPARISON_GATE=20 gate and _compute_mean_ci Wald-z CI"
  - "8-test suite: registry integrity, CI math, filter plumbing, severity zones, combos, gate, zero-event"
affects:
  - 115-02-frontend-bullet-grid-ui
  - future-flaw-comparison-consumers

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-game LEFT JOIN anchor pattern: analyzed+filtered games anchor LEFT JOIN game_flaws yields zero-delta row for clean games"
    - "30-column COUNT FILTER aggregation: one func.count(GameFlaw.ply) FILTER pair per metric per side (never func.count() for NULL-safety on LEFT JOIN)"
    - "Backend zone registry embedded in response: no TS codegen, API carries zone_lo/zone_hi/domain per bullet (D-07)"
    - "Early gate short-circuit: count_filtered_and_analyzed before expensive per-game query"

key-files:
  created:
    - app/services/flaw_delta_zones.py
    - tests/services/test_flaw_comparison.py
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/routers/library.py

key-decisions:
  - "FLAW_COMPARISON_GATE=20 matches §5 cohort inclusion basis (D-09)"
  - "Zero-event bullets return delta=None, not 0.0, to distinguish absence-of-events from exactly-typical (D-11)"
  - "Both combo bullets (hasty_miss, low_clock_miss) ship using zero-event fallback machinery (D-12)"
  - "Zone bounds embedded verbatim from §5 Q1/Q3 with no editorial widening (D-05)"
  - "flaw_severity filter narrows which games are in the set but zones stay visible in all 15 bullets (D-13)"

patterns-established:
  - "flaw_delta_zones.py mirrors endgame_zones.py shape but WITHOUT TS codegen (D-07)"

requirements-completed: [FLAWCMP-01, FLAWCMP-03, FLAWCMP-04, FLAWCMP-05]

# Metrics
duration: 14min
completed: 2026-06-11
---

# Phase 115 Plan 01: You-vs-Opponent Comparison API Summary

**Flaw-comparison API with 15-bullet Wald-z CI endpoint: per-game LEFT JOIN aggregation over game_flaws, zone registry from §5 benchmark verbatim, 20-game section gate, zero-event and combo fallback machinery**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-11T15:44:53Z
- **Completed:** 2026-06-11T15:57:45Z
- **Tasks:** 3 (Task 1: registry+schemas+scaffold, Task 2: repo+service+route, Task 3: test suite)
- **Files modified:** 6

## Accomplishments

- Zone registry `flaw_delta_zones.py`: `FlawDeltaZoneSpec` frozen dataclass + `FLAW_DELTA_ZONES` (15 entries, §5 Q1/Q3 verbatim, family-grouped)
- `fetch_flaw_comparison`: per-game LEFT JOIN anchor with ply_count guard; 30 COUNT FILTER columns via `is_opponent_expr` split (no inline ply%2)
- `get_flaw_comparison` service: `FLAW_COMPARISON_GATE=20` early gate, `_compute_mean_ci` (Wald-z, stdlib math only), `_compute_bullets` iterates rows once; zone bounds embedded from registry (D-07)
- `GET /api/library/flaw-comparison` route: same filter surface as `/flaw-stats`; user_id from auth only (IDOR guard T-115-01)
- 8-test suite (all green): registry integrity, CI math, filter plumbing, severity-filter zones, combos, sample gate, zero-event

## Task Commits

1. **Task 1: Zone registry + Pydantic schemas (Wave-0 test scaffold)** - `fcb85e812` (feat)
2. **Task 2: Repository per-game aggregation + service + router** - `2e64fe7b` (feat)
3. **Task 3: Backend test suite (fill Wave-0 stubs)** - `a61585b6` (test)
4. **Type fix: ty errors in test file** - `680c20ac` (fix)

## Files Created/Modified

- `app/services/flaw_delta_zones.py` - FlawDeltaZoneSpec dataclass + FLAW_DELTA_ZONES mapping (15 metrics, §5 zone/domain values)
- `app/schemas/library.py` - FlawBullet + FlawComparisonResponse Pydantic models added
- `app/repositories/library_repository.py` - fetch_flaw_comparison LEFT JOIN aggregation function
- `app/services/library_service.py` - FLAW_COMPARISON_GATE, _compute_mean_ci, _compute_bullets, get_flaw_comparison
- `app/routers/library.py` - GET /flaw-comparison route
- `tests/services/test_flaw_comparison.py` - 8 tests covering all FLAWCMP-01/03/04/05 behaviors

## Decisions Made

- Used `func.count(GameFlaw.ply)` (not `func.count()`) throughout the LEFT JOIN aggregation — NULL ply from absent join rows must not increment counts (Pitfall 1).
- `_DEFAULT_FILTER_KWARGS` dict used for `**kwargs` in most test calls; replaced with explicit kwargs where `ty` needed concrete types.
- The `flaw_severity` filter changes which GAMES are in the analyzed set (via EXISTS predicate), not which flaws are counted per game — test_severity_filter_zones accounts for this by using two game cohorts (M+B games vs mistake-only games).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ty errors: test file used string-quoted forward references and dict-merge kwargs**
- **Found during:** Task 3 verification (ty check)
- **Issue:** `"Game"` forward-ref string annotation caused `F821 Undefined name` ty errors; `**{**dict, "key": val}` dict merging produced `Unknown | list[str]` union that ty couldn't match to function params
- **Fix:** Moved `from app.models.game import Game` to module top, replaced string annotations with direct `Game` type, replaced dict-merge kwargs with explicit keyword arguments at two call sites
- **Files modified:** `tests/services/test_flaw_comparison.py`
- **Verification:** `uv run ty check app/ tests/` passed with zero errors
- **Committed in:** `680c20ac`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minimal — type annotation style fix only, no logic change.

## Issues Encountered

- First version of `test_severity_filter_zones` asserted `flaw_rate_all.delta > flaw_rate_blunder.delta` but both were equal (10.0). Root cause: severity filter narrows the game set via EXISTS (only games with blunders included), but when all 20 games have both M+B, the filtered and unfiltered sets are identical. Fixed by seeding two cohorts — 20 games with M+B and 20 with mistake-only — so the blunder filter actually excludes the second cohort.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (frontend bullet-grid UI) can consume `GET /api/library/flaw-comparison` immediately.
- Response shape: `FlawComparisonResponse` with `bullets[15]`, `analyzed_n`, `analyzed_gate=20`, `below_gate`.
- Each bullet carries: `tag`, `delta`, `ci_low`, `ci_high`, `player_events`, `opp_events`, `zone_lo`, `zone_hi`, `domain`, `has_zone=True`.
- Below-gate path returns `bullets=[]` with `below_gate=True` and the current `analyzed_n`.

## Self-Check: PASSED

- All 6 files created/modified confirmed present on disk
- All 4 task commits confirmed in git history (fcb85e812, 2e64fe7b, a61585b6, 680c20ac)
- 8/8 tests passing; ruff + ty zero errors

---
*Phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui*
*Completed: 2026-06-11*
