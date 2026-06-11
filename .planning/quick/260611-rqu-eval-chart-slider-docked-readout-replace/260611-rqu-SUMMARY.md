---
phase: quick-260611-rqu
plan: 01
subsystem: frontend/library
tags: [eval-chart, slider, readout, tooltip-removal, ux]
dependency_graph:
  requires: []
  provides: [eval-chart-docked-readout, eval-chart-scrub-slider]
  affects: [LibraryGameCard, EvalChart]
tech_stack:
  added: []
  patterns: [native-range-slider, unified-active-ply-state]
key_files:
  created: []
  modified:
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
decisions:
  - Replaced floating tooltip with docked readout + native range slider (no Radix Slider)
  - Unified activePly state (hoverPly ?? sliderPly) drives crosshair, readout, slider, and parent miniboard
  - Inaccuracy severity ticks included on slider (previously hidden from chart except on badge hover)
  - Initial sliderPly = last eval'd ply; reset via useEffect on sliderMax change
  - Focus ping guard in LibraryGameCard via evalChartMountedRef — skips yieldFocus on mount report
  - onHoverPlyChange useEffect excludes dependency to avoid spurious re-fires
metrics:
  duration: ~4 minutes
  completed: 2026-06-11
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 260611-rqu: EvalChart Docked Readout + Scrub Slider Summary

One-liner: Replaced the floating eval tooltip with a fixed docked readout line and a native scrub slider bearing severity tick marks, unifying hover and slider into one active-ply state.

## What Was Built

### Task 1: EvalChart rework (`8d739779`)

**Deleted:** Floating tooltip machinery — `ChartTooltip` import and element, `ChartTooltipBox` import, `buildTooltipContent`, `FlawTooltipDetail`, `suppressTooltip`/`pinned` state, `wrapperRef`, the `pointerdown` outside listener, `touchStartRef`/`draggedRef`/`TOUCH_SLOP_PX`, all touch handlers, `relative z-10` hover hack in wrapper className, `onTouchStart/Move/End/Cancel` wrapper props.

**Added — unified active-ply state:**
- `sliderPly: number` — persistent, defaults to `sliderMax` (last eval'd ply), reset via `useEffect` on `sliderMax` change
- `hoverPly: number | null` — transient, set by chart `onMouseMove`, cleared on `onMouseLeave`
- `activePly = hoverPly ?? sliderPly` — single value for crosshair `ReferenceLine`, readout content, slider value, and parent `onHoverPlyChange` report

**Docked readout** (`data-testid="eval-readout-{gameId}"`): fixed `h-6` single line between chart and slider — move label (semibold foreground), eval (bare value via `formatEvalBare`), clock, move time, flaw glyph+label+tags for M/B/I plies. No layout shift while scrubbing.

**Scrub slider** (`data-testid="eval-slider-{gameId}"`, `aria-label="Scrub move for game {gameId}"`): native `<input type="range">` with Tailwind-styled track/thumb. Severity ticks as absolutely-positioned `<div>` overlays — all `flawMarkers` included (inaccuracies get a tick even when hidden from the chart). User ticks full-height (`TICK_USER_HEIGHT = 8px`), opponent ticks shorter (`TICK_OPP_HEIGHT = 5px`) and lower opacity (`TICK_OPP_OPACITY = 0.55`).

**Kept intact:** `highlightedPlies`, `outlinedPlies`, `focusedPly` (ping), `flipped`, dual-marker dot renderer, phase lines, midline, all existing exports.

**`formatEval` refactored to `formatEvalBare`** — returns bare value without "Eval:" prefix; mate-priority and `#`-ending "Checkmate" logic preserved.

### Task 2: LibraryGameCard cleanup (`25fc04f4`)

- Removed `overflowVisible` prop from `<Card>` (readout and slider live inside)
- Removed `hoverPly != null && 'z-30'` from `<Card>` className (tooltip escape no longer needed)
- Updated `rounded-t-md` comment to remove stale `overflowVisible` reference
- Desktop `heightClass` changed from `h-[132px]` to `h-[92px]` — chart + readout (h-6) + slider (h-4) fit within the ~132px column envelope
- Mobile `heightClass` unchanged at `h-[130px]`
- **Focus ping guard:** `evalChartMountedRef` in `handleHoverPlyChange` — skips `yieldFocus()` on the initial mount report from EvalChart (which fires the non-null resting ply immediately via `useEffect`). Every subsequent call is treated as a user-driven scrub and yields the focus ping correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ESLint: cannot access/update refs during render**
- **Found during:** Task 2 lint gate (after writing Task 1)
- **Issue:** The `prevSeriesRef` pattern (reading/writing `.current` during render) and the `onHoverPlyChangeRef.current = ...` assignment during render are banned by the `react-hooks/refs` ESLint rule
- **Fix:** Replaced `prevSeriesRef` render-time diff with a `useEffect` on `sliderMax`; removed the `onHoverPlyChangeRef` pattern entirely, using `onHoverPlyChange?.(activePly)` directly in the `useEffect` with a `// eslint-disable-next-line` comment for the intentional dep exclusion; removed unused `useRef` import
- **Files modified:** `frontend/src/components/library/EvalChart.tsx`
- **Commit:** `25fc04f4`

## Known Stubs

None. The docked readout wires live data from `evalByPly`, `allMarkerMap`, and `moves` — no placeholders.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- `frontend/src/components/library/EvalChart.tsx` — FOUND
- `frontend/src/components/results/LibraryGameCard.tsx` — FOUND
- Commit `8d739779` — FOUND
- Commit `25fc04f4` — FOUND
- `npm run lint` — PASSED (0 errors)
- `npm test -- --run` — PASSED (885/885 tests)
- `npm run knip` — PASSED (no unused exports)
- No `ChartTooltip`, `buildTooltipContent`, `suppressTooltip`, `pinned`, `TOUCH_SLOP_PX`, `allowEscapeViewBox` in EvalChart — CONFIRMED
- `chart-tooltip-box.tsx` untouched — CONFIRMED (only import removed from EvalChart)
- `data-testid="eval-slider-{gameId}"` and `data-testid="eval-readout-{gameId}"` present — CONFIRMED
- Slider has `aria-label` — CONFIRMED
- No `text-xs` in new code — CONFIRMED (readout uses `text-sm`)
- No raw color literals — CONFIRMED (all from `@/lib/theme`)
- No magic tick numbers — CONFIRMED (`TICK_WIDTH`, `TICK_USER_HEIGHT`, `TICK_OPP_HEIGHT`, `TICK_OPP_OPACITY`)

## Post-review iteration (commit cfae29ed)

User visual review on :5174 requested a rework of the readout/ticks half:

- Severity tick marks under the slider removed (slider itself stays).
- Docked readout replaced by the original floating-tooltip content (move/eval,
  clock/move time, M/B flaw detail with glyph + tags), now rendered as a
  self-positioned div anchored at the active datapoint's x (side-flips at the
  chart midpoint, vertically centered on the chart), semi-transparent
  (`bg-background/80 backdrop-blur-[2px]`), `pointer-events-none`, and shown
  only while interacting (chart hover OR slider focus — a focused slider keeps
  it up after a drag; blur dismisses).
- Crosshair is now a solid `EVAL_CHART_CURSOR` line (new theme constant,
  `oklch(0.985 0 0)` = forced-dark `--foreground`, same as the slider thumb),
  with a white `ReferenceDot` highlighting the active datapoint where the
  crosshair meets the ES line (severity dots read as a colored ring around it
  on flaw plies).
- No recharts Tooltip machinery reintroduced — positioning uses the same
  ply→percent mapping the slider thumb relies on, so no z-index/overflow hacks
  returned. recharts 3.x note: `isFront` no longer exists on ReferenceDot;
  JSX document order provides the stacking.

Gates re-run: tsc, eslint, vitest 885/885, knip — all clean.
