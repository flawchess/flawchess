---
phase: quick-261014-pb9
plan: 01
subsystem: library-stats
tags: [library, flaw-comparison, heatmap, tempo, game-phase]
status: complete
requires: []
provides:
  - "tempo_phase_cells (9 per TC) on GET /api/library/flaw-comparison"
  - "Clock by game phase 3x3 heatmap card on Library Stats"
key-files:
  created:
    - frontend/src/components/library/stats/TempoPhaseHeatmap.tsx
    - frontend/src/components/library/stats/__tests__/TempoPhaseHeatmap.test.tsx
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/services/test_flaw_comparison.py
    - frontend/src/types/library.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/lib/gapBar.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/__tests__/gapBar.test.ts
    - frontend/src/components/library/stats/GapBar.tsx
    - frontend/src/components/library/stats/GapPopover.tsx
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
    - CHANGELOG.md
decisions:
  - "Tint scale normalised by the strongest SIGNIFICANT cell, not all 9 cells (a huge non-significant gap would otherwise dim real signals)"
  - "Columns = tempo (Clock-card order), rows = phase (game order)"
  - "_paired_series is the single owner of the per-user-moves denominator for bullets and crossed cells"
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
plan_head_before: 9d4cc1c3bba37af52c320a89c6a6053e46e70d90
plan_head_after: 68c5a3caddf60ccca72fa73a8f35fe81a31b7ff7
---

# Quick 261014-pb9: Library Stats 3x3 tempo x game-phase heatmap Summary

Adds a "Clock by game phase" card to Library Stats > You vs. your opponents: low-clock / hasty / unrushed crossed with opening / middlegame / endgame, each cell the paired you-minus-opponents gap per 100 of the user's moves for flaws carrying both tags, tinted green/red only when the 99% CI excludes 0.

## What was built

- **Backend**: 18 crossed `COUNT ... FILTER` columns appended to the existing `fetch_flaw_comparison` select (labels via the one helper `tempo_phase_count_label`), `TempoPhaseCell` schema, `FlawComparisonTc.tempo_phase_cells` (always 9, phase-major). `_compute_bullets` was refactored onto a shared `_paired_series` accumulator so bullets and crossed cells use one denominator rule; `_build_flaw_bullet` signature unchanged. `FLAW_DELTA_METRICS`, FlawBullet and the zone registry are untouched; crossed cells carry `has_zone False`, zones 0.
- **Frontend**: `TempoPhaseHeatmap` card mounted after `ContextTagCards` (above-gate branch only), `gapHeatmapScale` / `gapHeatmapFill` pure tint math in `gapBar.ts`, theme constants `GAP_HEATMAP_TINT_MIN_PERCENT` (35) / `MAX_PERCENT` (90) / `NEUTRAL_FILL`, `tempoPhaseMeta` popover copy, per-cell `GapPopover` (new optional `zonelessSignificantCopy` prop; tactic copy unchanged), `GAP_EMPTY_WORDS` shared with GapBar, legend line, sr-only cell labels.
- CHANGELOG `### Added` bullet under `[Unreleased]`.

## Commits

- b99933d61 feat: tempo x phase crossed cells end-to-end with words-only heatmap card
- ea935299b feat: significance-gated tint, popovers and legend
- 68c5a3cad docs: changelog

## RED / mutation observations

- Backend RED: `test_tempo_phase_cells_shape_and_order` failed before implementation (1 failed with -x; the others failed on the same missing field).
- Backend mutation: removing the `GameFlaw.phase == ...` predicate made `test_tempo_phase_cells_count_both_sides` and `test_tempo_phase_cells_marginal_sum_invariant` fail (2 failed, 23 passed); restored, 25 passed.
- Frontend RED: gapBar.test.ts and TempoPhaseHeatmap.test.tsx failed ("gapHeatmapScale is not a function", 10 failures) before implementation.
- Frontend mutation: making `gapHeatmapFill` ignore significance (tint every non-null cell) failed `gives a non-significant cell with a large gap the neutral fill` and the component test `tints only significant cells and keeps the words on a neutral big gap`; restored, 148 passed.

## Deviations from Plan

- The frontend Task 1 section test (heatmap after context cards, 9 cells, absent below gate) was written together with the implementation rather than observed failing first (backend RED and both mutation checks were observed as specified). Impact: none on coverage.
- The sr-only cell label is a sibling of the words span (not inside it) so the `-words` testid text is exactly the gap words.

None otherwise: plan executed as written. No auto-fixes needed.

## Gate results

- `uv run ruff format app/ tests/`: 427 files left unchanged
- `uv run ruff check .`: All checks passed
- `uv run ty check app/ tests/ scripts/`: All checks passed
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, 1205 functions scanned, no breaches
- `uv run pytest tests/services/test_flaw_comparison.py tests/test_library_router.py tests/test_library_repository.py -n auto`: 146 passed
- frontend `npm run lint`: clean; `npm run build`: built; `npm test -- --run`: 329 files, 5586 tests passed; `npm run knip`: exit 0 (two pre-existing configuration hints only)

## Known Stubs

None.

## Threat Flags

None. The 18 new columns ride the existing user-scoped anchor and outer join; labels are built from Literal constants only; popover testIds use enumerated segments plus the TC.

## Self-Check: PASSED

- FOUND: frontend/src/components/library/stats/TempoPhaseHeatmap.tsx
- FOUND: frontend/src/components/library/stats/__tests__/TempoPhaseHeatmap.test.tsx
- FOUND commits b99933d61, ea935299b, 68c5a3cad on main
