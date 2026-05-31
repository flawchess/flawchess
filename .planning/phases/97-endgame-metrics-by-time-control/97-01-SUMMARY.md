---
phase: 97-endgame-metrics-by-time-control
plan: "01"
subsystem: endgame-zones-codegen
tags: [endgame, time-control, zones, codegen, registry]
dependency_graph:
  requires: []
  provides:
    - TC_METRIC_BANDS Python registry
    - TC_METRIC_BANDS TypeScript export
    - _format_tc_metric_bands codegen emitter
  affects:
    - frontend/src/generated/endgameZones.ts (regenerated)
tech_stack:
  added: []
  patterns:
    - frozen dataclass registry (matches PressureBinBand / PerClassBands pattern)
    - Python-to-TS codegen via gen_endgame_zones_ts.py
key_files:
  created: []
  modified:
    - app/services/endgame_zones.py
    - scripts/gen_endgame_zones_ts.py
    - frontend/src/generated/endgameZones.ts
decisions:
  - TC_METRIC_BANDS placed after PRESSURE_BIN_SCORE_NEUTRAL_ZONES to keep TC-keyed registries grouped
  - Parity bands kept in BUCKETED_ZONE_REGISTRY (global) — TC d < 0.15 per plan decision D-08
  - Float 0.800 renders as 0.8 in codegen output (Python default repr) — consistent with existing constants
metrics:
  duration: ~8 minutes
  completed: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 97 Plan 01: TC_METRIC_BANDS Registry and Codegen Summary

Per-TC Conversion and Recovery neutral bands added to Python zone registry and threaded through the codegen pipeline into `endgameZones.ts` — bulletin-board values from benchmark §3.2.1 (rates) and §3.2.2 (ΔES gaps) split by time control instead of pooled.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TcConvRecovBands dataclass + TC_METRIC_BANDS registry | 3ec6b20a | app/services/endgame_zones.py |
| 2 | _format_tc_metric_bands codegen emitter + regenerate endgameZones.ts | 1033002c | scripts/gen_endgame_zones_ts.py, frontend/src/generated/endgameZones.ts |

## What Was Built

**Task 1:** Added `@dataclass(frozen=True) TcConvRecovBands` with four `tuple[float, float]` fields (`conv_rate`, `recov_rate`, `conv_score_gap`, `recov_score_gap`) and a module-level `TC_METRIC_BANDS: Mapping[Literal["bullet", "blitz", "rapid", "classical"], TcConvRecovBands]` registry immediately after `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`. Band values sourced from `reports/benchmark/benchmarks-latest.md §3.2.1` and `§3.2.2`. `BUCKETED_ZONE_REGISTRY` and `ZONE_REGISTRY` left untouched.

**Task 2:** Extended `scripts/gen_endgame_zones_ts.py` with:
- `TC_METRIC_BANDS` added to the import block
- `_format_tc_metric_bands() -> str` function emitting one TS object line per TC
- Emission appended in `_render()` after the `CLOCK_GAP_NEUTRAL_*` block as a typed `Record<'bullet' | 'blitz' | 'rapid' | 'classical', { ... }>` ending `} as const;`

Regenerated `frontend/src/generated/endgameZones.ts` with the new `TC_METRIC_BANDS` export.

## Verification Results

- Import assertion: `TC_METRIC_BANDS['bullet'].conv_rate == (0.588, 0.719)` and `TC_METRIC_BANDS['classical'].recov_score_gap == (-0.037, 0.035)` — both pass
- All 4 TC keys present: `{'bullet', 'blitz', 'rapid', 'classical'}`
- Drift gate: `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` exits 0 — clean
- `uv run ty check app/` — zero errors
- `uv run ruff check app/ scripts/` — clean
- `./node_modules/.bin/tsc --noEmit` in frontend — zero errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The pre-existing "placeholder" comments in `gen_endgame_zones_ts.py` and `endgameZones.ts` (lines referencing Phase 87.1 SEED-016 D-04 ±5pp placeholder bands) are historical comments from prior phases, not introduced by this plan.

## Threat Flags

None. Both threat items in the plan's threat register are addressed:
- T-97-01 (Tampering — drift gate): CI drift gate confirmed green after commit.
- T-97-02 (Information disclosure — band constants): Band values are public benchmark statistics with no PII.

## Self-Check: PASSED

- `app/services/endgame_zones.py` — contains `class TcConvRecovBands` and `TC_METRIC_BANDS`
- `scripts/gen_endgame_zones_ts.py` — contains `_format_tc_metric_bands` and imports `TC_METRIC_BANDS`
- `frontend/src/generated/endgameZones.ts` — contains `export const TC_METRIC_BANDS`
- Commit 3ec6b20a exists in git log
- Commit 1033002c exists in git log
