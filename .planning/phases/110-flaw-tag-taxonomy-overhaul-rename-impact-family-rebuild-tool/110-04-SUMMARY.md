---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
plan: 04
subsystem: infra
tags: [codegen, python-to-typescript, ci, drift-gate, flaw-thresholds]

# Dependency graph
requires:
  - phase: 110-01
    provides: flaw-tag taxonomy rename (reversed/squandered/hasty/unrushed) + flaws_service.py constants confirmed
provides:
  - scripts/gen_flaw_thresholds_ts.py Python-to-TS generator with --check drift mode
  - frontend/src/generated/flawThresholds.ts flat-scalar threshold module (8 constants)
  - CI second drift-gate step for flawThresholds.ts
affects:
  - 110-05 (tagDefinitions.ts imports from @/generated/flawThresholds — direct hard dependency)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Python-to-TS codegen: flat-scalar generator (no _format_* helpers) mirroring gen_endgame_zones_ts.py structure with --check drift mode"
    - "CI dual drift gate: two independent git diff --exit-code steps (endgameZones.ts + flawThresholds.ts) per D-04"

key-files:
  created:
    - scripts/gen_flaw_thresholds_ts.py
    - frontend/src/generated/flawThresholds.ts
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "D-04 honored: gen_flaw_thresholds_ts.py is an independent script, gen_endgame_zones_ts.py untouched, two drift gates never merged"
  - "Flat-scalar _render() with no _format_* helpers: the 8 constants are simple floats, no registry objects or zone arrays requiring formatting helpers"
  - "flawThresholds.ts exports 8 constants: 4 ES impact thresholds (WINNING_LINE_ES, LOSING_LINE_ES, FROM_WINNING_ES, SQUANDERED_EXIT_ES) + 4 tempo thresholds (TIME_PRESSURE_CLOCK_FRACTION, TIME_PRESSURE_CLOCK_ABS_SECONDS, HASTY_MOVE_FRACTION, HASTY_MOVE_ABS_SECONDS)"

patterns-established:
  - "Flat codegen pattern: when all generated exports are plain scalars, skip _format_* helpers and use f-string interpolation directly in _render()"

requirements-completed: [SC-5]

# Metrics
duration: 10min
completed: 2026-06-07
---

# Phase 110 Plan 04: Flaw Thresholds Codegen Summary

**Python-to-TS threshold generator (gen_flaw_thresholds_ts.py) with --check drift mode emits flat scalar module (flawThresholds.ts) gated by a second independent CI drift check, enabling Plan 05's popover to interpolate thresholds with zero hard-coded percentages**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-07T20:52:00Z
- **Completed:** 2026-06-07T20:55:46Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Created `scripts/gen_flaw_thresholds_ts.py` mirroring `gen_endgame_zones_ts.py` 1:1 in structure (module docstring, sys.path bootstrap, authoritative-constant import, `_render()`, `main()` with `--check` mode)
- Generated `frontend/src/generated/flawThresholds.ts` with 8 flat `export const` scalars (4 ES impact + 4 tempo) sourced from `app/services/flaws_service.py`
- Added "Flaw thresholds drift check" CI step immediately after the existing "Zone drift check" step — two independent, never-merged drift gates

## Task Commits

1. **Task 1: Write gen_flaw_thresholds_ts.py + generate flawThresholds.ts** - `f4192828` (feat)
2. **Task 2: Add the second CI drift-gate step for flawThresholds.ts** - `8d768535` (chore)

## Files Created/Modified

- `scripts/gen_flaw_thresholds_ts.py` - Python-to-TS generator; flat-scalar _render(), --check drift mode, no _format_* helpers
- `frontend/src/generated/flawThresholds.ts` - Generated module with 8 threshold constants; consumed by Plan 05's tagDefinitions.ts
- `.github/workflows/ci.yml` - Second drift-gate step "Flaw thresholds drift check" added (lines 54-57)

## Decisions Made

- D-04 honored: `gen_flaw_thresholds_ts.py` is an independent script; `gen_endgame_zones_ts.py` was not modified and the two generators are not merged. Two separate CI drift gates exist.
- Flat-scalar `_render()` with no `_format_*` helpers: all 8 exported values are plain Python floats — no registry objects or zone arrays requiring intermediate formatting helpers (unlike `gen_endgame_zones_ts.py` which needs `_format_bucket_zones()` etc. for complex nested structures).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None. The generated file exports real constants sourced from `flaws_service.py` — no placeholder values.

## Knip Status (Expected-Until-Plan-05)

`npm run knip` flags `frontend/src/generated/flawThresholds.ts` as an unused file. This is expected: the consumer (`tagDefinitions.ts`) is rebuilt in Plan 05. The unused-file warning will resolve when Plan 05 adds the import. No fake consumer was added.

## Threat Flags

None new. T-110-04 (tampering via config drift) is mitigated by the CI `git diff --exit-code` drift gate added in Task 2.

## Next Phase Readiness

Plan 05 (`tagDefinitions.ts` rebuild + TagChip popover restore) can import from `@/generated/flawThresholds` with all 8 threshold constants available. No further codegen work needed for the popover copy.

---
*Phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool*
*Completed: 2026-06-07*
