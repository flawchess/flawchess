---
phase: 239-library-stats-you-vs-opponents
plan: 03
subsystem: frontend
tags: [react, gap-bar, popover, tc-switch, localStorage, vitest]
requires: []
provides:
  - "frontend/src/lib/gapBar.ts: gap-bar math, words, verdicts, standout ranking"
  - "GapBar, GapGateSlot, GapRow, GapPopover (library/stats)"
  - "MetricInfoPopover: shared Search-icon popover shell"
  - "createTcSelectionStore, useLibraryStatsTc, TcSwitchButtons"
affects: [239-05, 239-08, 239-10]
tech-stack:
  added: []
  patterns: ["store factory returning a use... hook", "shared popover shell with children body"]
key-files:
  created:
    - frontend/src/lib/gapBar.ts
    - frontend/src/components/library/stats/GapBar.tsx
    - frontend/src/components/library/stats/GapPopover.tsx
    - frontend/src/components/library/stats/GapRow.tsx
    - frontend/src/components/ui/metric-info-popover.tsx
    - frontend/src/components/stats/TcSwitchButtons.tsx
    - frontend/src/hooks/tcSelectionStore.ts
    - frontend/src/hooks/useLibraryStatsTc.ts
  modified:
    - frontend/src/components/endgames/stats/RankedMetricPopover.tsx
    - frontend/src/components/endgames/stats/TcSwitch.tsx
    - frontend/src/hooks/useEndgameStatsTc.ts
decisions:
  - "Zoneless dot scale, typical-range-in-words, gate-slot and 'No flaws yet' copy follow the plan's planner_assumptions unchanged"
  - "Popover rates use two decimals (matches the tiles and the plan's '5.46'); the sketch's fmt would print 5.5"
  - "formatSignedGap uses two decimals below 10 so a CI bound reads -1.00 (plan copy), unlike the sketch's one-decimal fmt"
  - "Shared default-TC selection extracted as pickMostPopulatedTc so Endgame and Library defaults use one implementation"
metrics:
  duration: ~35min
  completed: 2026-10-12
status: complete
actuals:
  tokens: 17000
  tasks: 3
  commits: 3
plan_head_before: 58cb1ee58c2337595d829dfbbf0eac5d166be234
plan_head_after: e991c53db7d7bfe0ba2d8ed65ff0d2c60e22e17c
---

# Phase 239 Plan 03: Gap-bar building blocks Summary

One zero-centred gap bar (sketch 010 round 5 math plus zero-width guards), the shared Search-icon popover shell used by both the Endgame percentile popover and the new gap popover, the gap row, the What-stands-out ranking function, and a TC selection store factory backing two independent localStorage keys.

## What was built

- **Task 1 (tracer, 8232a4696)**: `gapBar.ts` (position with `s === 0` and zero-band-width guards, verdict, words, `cellPosition` with the virtual band for zoneless cells, `bandRange`, `standoutDistance`, `pickStandouts`) and `GapBar` / `GapGateSlot`. Zoneless: no band, blue dot, no verdict. Low-sample: band drawn, blue dot, no verdict, container fades. Delta null: "No flaws yet", no track.
- **Task 2 (9e3d3957c)**: `MetricInfoPopover` lifted verbatim from `RankedMetricPopover` (which now wraps its body in it; its test is untouched and green). `GapPopover` follows D-00c order with flaws-only wording; `GapRow` fades low-sample rows with `UNRELIABLE_OPACITY`.
- **Task 3 (e991c53db)**: `createTcSelectionStore` owns the choice, pinned default (FE-IN-05), validated try/catch storage read and best-effort write. `useEndgameStatsTc` is a thin wrapper (key `endgame_stats_tc`, same exports). `useLibraryStatsTc` uses `library_stats_tc` and the D-04 default. `TcSwitchButtons` extracted; `TcSwitch` keeps props, testids and tracking.

## Verification

- New tests: gapBar (37), GapBar (12), GapPopover + GapRow (14), useLibraryStatsTc (17); existing `RankedMetricPopover.test.tsx` and `useEndgameStatsTc.test.ts` pass with no edits.
- `npm run lint`, `npm run build` (tsc -b), `npm run knip` all clean (knip exit 0).
- Mutation checks (each reverted afterwards):
  1. Removed the `s === 0` guard: the zero-band guard test failed.
  2. Flipped the `delta < 0` side in `gapPosition`: 8 position tests failed.
  3. Rendered the verdict sentence for a low-sample popover: the "Too few flaws to call it." test failed.
  4. Pointed the Library store at `endgame_stats_tc`: the restore and key-isolation tests failed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CI bound and rate precision**
- **Found during:** Task 2
- **Issue:** The plan's popover copy ("You: 5.46 per 100 moves", "gap 95% CI −1.00 to −0.32") disagrees with the sketch helper `fmt`, which prints 1 decimal at or above 1 (5.5, −1.0). Using `formatGapNumber` for both would have contradicted the plan's behavior bullets.
- **Fix:** Rates use `toFixed(2)` (like the tiles); `formatSignedGap` prints two decimals below 10. `formatGapNumber` keeps the sketch thresholds for the gap words.
- **Files modified:** frontend/src/lib/gapBar.ts, frontend/src/components/library/stats/GapPopover.tsx
- **Commit:** 9e3d3957c

**2. [Scope note] Exports limited to what is consumed**
- Only `GAP_EDGE_POS`, `GAP_CENTRE` and `TOP_STANDOUTS` are exported as constants (the others stay module-private) so knip stays clean until plans 239-05/08/10 consume the rest.

**3. [Scope note] Extra shared helper**
- Added `pickMostPopulatedTc` to `tcSelectionStore.ts` so `pickDefaultTc` and `pickDefaultLibraryTc` share one tie-break implementation instead of duplicating the loop.

## Deferred / Observations

- The full frontend suite shows load-dependent flakes in untouched Train files (`Train.solveLoop.test.tsx`, `TrainStreakCard.test.tsx`; 1 to 2 failures per full run, different each time); both pass when run alone. Not touched by this plan.

## Known Stubs

None. GapRow, GapPopover, GapGateSlot, `pickStandouts`, `useLibraryStatsTc` and `TcSwitchButtons` are not yet mounted by any page; plans 239-05/08/10 assemble the page from them.

## Threat Flags

None. T-239-06 (storage tampering) mitigated: stored value validated against `TIME_CONTROL_ORDER` and the offered list, try/catch on read and write, tested. T-239-07: popover testIds are caller-supplied metric key + TC segment only; documented in `MetricInfoPopover` and `GapPopover`.

## Self-Check: PASSED

All created files exist and commits 8232a4696, 9e3d3957c, e991c53db are ancestors of HEAD.
