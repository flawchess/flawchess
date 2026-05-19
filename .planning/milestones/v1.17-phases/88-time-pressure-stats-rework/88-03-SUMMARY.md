---
phase: 88-time-pressure-stats-rework
plan: "03"
subsystem: endgame-zones
tags:
  - zone-registry
  - codegen
  - time-pressure
  - placeholder-values
dependency_graph:
  requires:
    - 88-01 (score_confidence math helper — provides compute_score_delta_vs_reference)
  provides:
    - PRESSURE_BIN_SCORE_NEUTRAL_ZONES (4x5 placeholder bands)
    - PRESSURE_BIN_NEUTRAL_CAP constant
    - PressureBinBand dataclass
    - clock_gap_pct MetricId + ZONE_REGISTRY entry
    - PRESSURE_BIN_SCORE_NEUTRAL_ZONES TS export
    - CLOCK_GAP_NEUTRAL_MIN / CLOCK_GAP_NEUTRAL_MAX TS exports
  affects:
    - Plans 05-07 (frontend consumers importing from endgameZones.ts)
    - Plan 08 (benchmark calibration — swaps placeholder values)
tech_stack:
  added: []
  patterns:
    - PressureBinBand frozen dataclass mirrors PerClassBands style
    - Mapping[Literal[TC], Mapping[Literal[quintile], PressureBinBand]] nested registry
    - Codegen extends _format_per_class_gauge_zones() pattern with _format_pressure_bin_zones()
    - ty-safe test iteration over typed mapping keys (not set[str])
key_files:
  created: []
  modified:
    - app/services/endgame_zones.py
    - scripts/gen_endgame_zones_ts.py
    - frontend/src/generated/endgameZones.ts
    - tests/services/test_endgame_zones.py
decisions:
  - "Iterate over PRESSURE_BIN_SCORE_NEUTRAL_ZONES.items() in tests rather than a set[str] to satisfy ty's Literal-key inference for Mapping[Literal[...], ...]"
  - "PRESSURE_BIN_NEUTRAL_CAP and ZONE_REGISTRY clock_gap_pct entry use NEUTRAL_PCT_THRESHOLD placeholder; real values land in Plan 08 after /benchmarks §3.3.3"
  - "Confirmed insights_service.py uses named allow-list (not MetricId auto-iteration); no LLM finding guard needed for clock_gap_pct"
metrics:
  duration_minutes: ~25
  completed_date: "2026-05-17"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 4
---

# Phase 88 Plan 03: Zone Constants Scaffold Summary

Zone-constant infrastructure for Phase 88 with PLACEHOLDER values: `PressureBinBand` dataclass, 4x5=20-entry `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` mapping, `PRESSURE_BIN_NEUTRAL_CAP = 0.06`, `clock_gap_pct` MetricId + ZONE_REGISTRY entry, codegen extension emitting both to TypeScript, and registry-shape tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add PressureBinBand + PRESSURE_BIN_SCORE_NEUTRAL_ZONES + clock_gap_pct | 504feff7 | app/services/endgame_zones.py |
| 2 | Extend gen_endgame_zones_ts.py + regenerate endgameZones.ts | c33bb7c0 (88-02 agent) | scripts/gen_endgame_zones_ts.py, frontend/src/generated/endgameZones.ts |
| 3 | Add registry-sanity tests | e4981458 | tests/services/test_endgame_zones.py |

Note: Task 2 file changes were committed by the parallel 88-02 agent which ran concurrently. The 88-02 agent implemented the full codegen extension (import, `_format_pressure_bin_zones()`, `_CLOCK_GAP_SPEC`, `_render()` extension) alongside its benchmarks SKILL.md work. Task 1 (this plan) provided the prerequisite Python symbols that the codegen script imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ty type error in test_pressure_bin_zones_shape**
- **Found during:** Task 3 (ty check of test file)
- **Issue:** Test originally iterated `for tc in tcs` where `tcs: set[str]`. ty rejected indexing `Mapping[Literal["bullet", ...], ...]` with a `str` key (3 errors: invalid-argument-type on line 296, 298 twice).
- **Fix:** Changed test to iterate `for tc, quintile_map in PRESSURE_BIN_SCORE_NEUTRAL_ZONES.items()` and `for q, band in quintile_map.items()`, using the mapping's own typed keys rather than a plain `str` iterator.
- **Files modified:** tests/services/test_endgame_zones.py
- **Commit:** e4981458

## Verification Results

- `uv run python scripts/gen_endgame_zones_ts.py` + `git diff --exit-code frontend/src/generated/endgameZones.ts`: DRIFT-CLEAN
- `uv run pytest tests/services/test_endgame_zones.py -x -q`: 43 passed
- `uv run ty check app/ tests/`: All checks passed
- `cd frontend && npx tsc --noEmit`: 0 errors
- Threat T-88-03-02 mitigated: `insights_service.py` confirmed to use named allow-list; `clock_gap_pct` does not auto-fire any LLM finding

## Known Stubs

| Symbol | Location | Reason |
|--------|----------|--------|
| `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | app/services/endgame_zones.py | PLACEHOLDER: all 20 entries set to ±0.06. Real benchmark-calibrated values land in Plan 08 after running /benchmarks §3.3.3 against the benchmark DB. |
| `ZONE_REGISTRY["clock_gap_pct"]` | app/services/endgame_zones.py | PLACEHOLDER: ±NEUTRAL_PCT_THRESHOLD (±5.0) until benchmarks §3.3.1 clock-gap-% runs. |
| `CLOCK_GAP_NEUTRAL_MIN/MAX` | frontend/src/generated/endgameZones.ts | Generated from above placeholder; swapped in Plan 08. |

These stubs are intentional per the plan objective. Plans 05-07 import the constants' shape (not values) to build and test the card component; values are swapped in Plan 08 without touching any consumer code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan modifies only internal constants and codegen.

## Self-Check: PASSED

- `app/services/endgame_zones.py`: FOUND (modified with 4 new symbols)
- `scripts/gen_endgame_zones_ts.py`: FOUND (modified with _format_pressure_bin_zones + _CLOCK_GAP_SPEC)
- `frontend/src/generated/endgameZones.ts`: FOUND (PRESSURE_BIN_SCORE_NEUTRAL_ZONES + CLOCK_GAP_NEUTRAL_MIN/MAX exported)
- `tests/services/test_endgame_zones.py`: FOUND (test_pressure_bin_zones_shape + clock_gap_pct assertions)
- Commit 504feff7: FOUND (endgame_zones.py Task 1)
- Commit e4981458: FOUND (test_endgame_zones.py Task 3)
