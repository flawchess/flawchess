---
phase: quick-261014-qj8
plan: 01
subsystem: library-stats
tags: [flaw-comparison, heatmap, benchmark-zones]
status: complete
requirements: [QUICK-261014-qj8]
key-files:
  modified:
    - app/services/flaw_delta_zones.py
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/services/test_flaw_delta_zones.py
    - tests/services/test_flaw_comparison.py
    - frontend/src/lib/gapBar.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/__tests__/gapBar.test.ts
    - frontend/src/components/library/stats/TempoPhaseHeatmap.tsx
    - frontend/src/components/library/stats/__tests__/TempoPhaseHeatmap.test.tsx
    - frontend/src/types/library.ts
    - CHANGELOG.md
actuals:
  tokens: 10400
  tasks: 3
  commits: 3
plan_head_before: 0937e3ef66fbc0ee37d626c500e6e828e6c119e0
plan_head_after: f6cd5bf1622b77ffd96e49711382b8c91fb7dfc4
commits_list: [90b937a01, 62d1a5a61, f6cd5bf16]
---

# Phase quick-261014-qj8 Plan 01: Benchmark bands for the tempo x phase heatmap Summary

The 8 viable crossed tempo x phase cells now carry pooled benchmark bands from a new `TEMPO_PHASE_ZONES` registry, and the heatmap colours exactly like the gap bars: green or red only when the gap is outside the band AND significant, with tint strength read off the GapBar position curve.

## What changed

- `app/services/flaw_delta_zones.py`: `FlawTempoMetric` / `FlawPhaseMetric` Literals moved here (the schema module imports this one, so the registry could not import from it), `TEMPO_PHASE_ZONES` (9 keys, 8 `symmetric_band` entries, `low_clock x opening` = None) with the basis comment citing the PROBE file, and `tempo_phase_zone(tempo, phase, tc)` with the D-08 `ZONE_TC_FOR` mapping. `FLAW_DELTA_METRICS` / `FLAW_DELTA_ZONES` untouched.
- `TempoPhaseCell`: `zone_lo`, `zone_hi`, `has_zone` no longer have defaults; `_build_tempo_phase_cell` (the only constructor) sets them on both return paths, zero-event included. `_compute_tempo_phase_cells` takes the TC.
- Frontend: `gapHeatmapFill(cell)` is single-argument and returns `{ tint, background, percent }`; `gapHeatmapScale` and the scale-based percent helper are deleted; share = distance beyond the band along the GapBar saturating outer span (zoneless: gap relative to the larger rate). Component exposes `data-tint-percent`, legend Grey reads "typical for your level or no clear difference". The GapPopover needed no change (data-driven).
- CHANGELOG: the existing heatmap bullet amended, no second bullet.

## Verification and mutation checks

- Backend mutation: forcing `band = None` in `_build_tempo_phase_cell` made `test_tempo_phase_cells_shape_and_order` FAIL (1 failed); restored, suite green.
- Frontend mutation: replacing the `effectiveVerdict` gate in `gapHeatmapFill` with a significance-only verdict made 3 tests FAIL: `gapBar.test.ts > gapHeatmapFill > renders a significant gap INSIDE the band neutral`, `TempoPhaseHeatmap.test.tsx > renders a significant gap INSIDE its band neutral and keeps the words`, and `... > tints further beyond the band stronger, and neutral cells read percent 0`. Restored: 52/52 pass.
- Gate: ruff format (no change), ruff check, ty (app/ tests/ scripts/), `check_function_size.py app/ --fail-over-depth 4` (no breaches), the 5 listed pytest files with `-n auto` (175 passed), frontend lint, build, full `npm test -- --run` (329 files, 5593 tests passed), knip all exit 0. `git diff --stat 6c961a6a6 -- scripts/benchmarks/ reports/` is empty.

## Deviations from Plan

**1. [Process] Task 1 and 2 code written before the tests, not strictly RED-first.** For Task 1 I wrote the backend registry/service code and then the tests; no standalone RED run was recorded. The backend and frontend mutation checks above are the proof the tests bite.

**2. [Process, self-corrected] Stale backup during the frontend mutation check.** I restored gapBar.ts from a leftover scratchpad file of an earlier session (the pre-qj8 original), which silently reverted my edit. I noticed because the restored run showed 9 failures and `git diff` of gapBar.ts was empty, re-applied the edit, and re-ran: 52/52 pass. The mutation observation itself (3 failures) was taken on the correct edited file (diff stat 33/31 lines at the time). The committed gapBar.ts is the re-applied version.

No other deviations. No lockfile or dependency changes.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Commits 90b937a01, 62d1a5a61, f6cd5bf16 exist on `main`; all modified files present.
