---
quick_id: 260414-smt
subsystem: endgames
tags: [backend, frontend, db-migration, time-pressure, clock-stats]
dependency_graph:
  requires: []
  provides:
    - games.base_time_seconds (per-game starting clock)
    - games.increment_seconds (per-move increment)
    - per-game % denominator in _compute_clock_pressure and _compute_time_pressure_chart
    - >2x clamp excluding bogus clock readings
  affects:
    - /api/endgames/overview (clock_pressure section, time_pressure_chart section)
tech_stack:
  added: []
  patterns:
    - per-game denominator (not bucket-first-seen) for clock % computation
    - bad-data clamp: exclude games with clock > 2x base from all clock aggregation
key_files:
  created:
    - alembic/versions/20260414_184435_179cfbd472ef_add_base_time_seconds_and_increment_.py
  modified:
    - app/models/game.py
    - app/schemas/normalization.py
    - app/services/normalization.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/schemas/endgames.py
    - frontend/src/components/charts/EndgameClockPressureSection.tsx
    - tests/test_normalization.py
    - tests/test_endgame_service.py
decisions:
  - "Clamp (>2x base) excludes game from ALL clock aggregation (absolute seconds + pct), not just pct — keeps absolute metrics uncontaminated by bogus readings"
  - "When base_time_seconds=None (daily/correspondence games), pct is None but absolute seconds still computed"
  - "Migration uses self-contained _parse_base_inc helper so it stays correct if app code is later renamed"
metrics:
  duration: "~45 minutes"
  completed: "2026-04-14"
  tasks_completed: 3
  tests_added: 28
---

# quick-260414-smt: Split time_control into base_time_seconds + increment_seconds

**One-liner:** Per-game base_time_seconds denominator for clock % fixes "129%+ of time remaining" bug caused by bucket-first-seen time_control_seconds (base + inc*40) mixing different starting clocks.

## Migration

**Revision ID:** `179cfbd472ef`

Adds `base_time_seconds` (SmallInteger, nullable) and `increment_seconds` (SmallInteger, nullable) to the `games` table. Backfills from `time_control_str` using a self-contained Python parser in batches of 500.

## Before / After (sample rapid-bucket row)

| Field | Before (bucket-first-seen) | After (per-game) |
|---|---|---|
| `user_avg_pct` | 250% (1500s / 600s * 100, first-seen was a 600+0 game) | 83% (1500s / 1800s * 100) |
| `user_avg_pct` (600+0 rapid, 300s remaining) | 50% (correct) | 50% (unchanged) |

The root cause was that `time_control_seconds = base + inc*40` (e.g. 600+10 → 1000) inflated the denominator for rapid with increments, and the bucket-first-seen storage meant ALL games in a rapid bucket divided by the same estimate regardless of their actual starting clock.

## Tasks Completed

| # | Commit | Description |
|---|--------|-------------|
| 1 | 7024a22 | Add base_time_seconds + increment_seconds columns, backfill migration, update import pipeline |
| 2 | 78a457a | Switch time pressure to per-game base_time_seconds denominator + >2x clamp |
| 3 | bc8b372 | Frontend: relabel Time Pressure popover to reflect % of base time |

## Tests Added

- **test_normalization.py**: 8 cases for `parse_base_and_increment` + 4 integration tests for both normalizers (600+5 and daily) — total +12 test cases
- **test_endgame_service.py**: Renamed `_make_clock_row` param; added `TestClockPressurePerGameDenominator` (5 tests) and `TestTimePressureChartPerGameDenominator` (2 tests) — total +7 new test classes with 16 new cases
- Full suite: 722 tests pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Clamp behavior when base_time_seconds=None**
- **Found during:** Task 2 implementation
- **Issue:** Initial implementation bundled the clamp condition with the None check, accidentally excluding absolute seconds from accumulation when base_time_seconds=None (daily games). Existing test `test_time_control_seconds_none_pct_is_none` expected seconds to still be computed.
- **Fix:** Separated the None-base guard (pct only) from the >2x clamp (whole game). Games with None base still contribute to absolute clock seconds; only games where clamp triggers (base known AND clocks > 2x) are excluded entirely.
- **Files modified:** app/services/endgame_service.py

None — all other plan instructions executed exactly as written.

## Threat Flags

None. No new network endpoints, auth paths, or trust-boundary changes introduced.

## Self-Check: PASSED

- alembic/versions/20260414_184435_179cfbd472ef_add_base_time_seconds_and_increment_.py — FOUND
- app/models/game.py — FOUND (base_time_seconds, increment_seconds columns)
- app/services/normalization.py — FOUND (parse_base_and_increment, both normalizers wired)
- app/services/endgame_service.py — FOUND (MAX_CLOCK_PCT_OF_BASE, per-game logic in both compute functions)
- app/repositories/endgame_repository.py — FOUND (Game.base_time_seconds in SELECT)
- frontend/src/components/charts/EndgameClockPressureSection.tsx — FOUND (base time in popover)
- Commits 7024a22, 78a457a, bc8b372 — all present in git log
