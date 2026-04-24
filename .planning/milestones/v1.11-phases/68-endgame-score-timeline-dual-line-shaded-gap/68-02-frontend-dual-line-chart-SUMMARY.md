---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 02
subsystem: insights
tags:
  - insights
  - endgame
  - frontend
  - charts
requires:
  - ScoreGapTimelinePoint.endgame_score / non_endgame_score (Plan 01)
  - Recharts 2.15.4 (ComposedChart + Area ranged-data pattern)
  - InfoPopover from @/components/ui/info-popover
provides:
  - EndgameScoreOverTimeChart component (replaces ScoreGapTimelineChart)
  - Theme tokens SCORE_TIMELINE_FILL_ABOVE / _BELOW / _LINE_ENDGAME / _LINE_NON_ENDGAME
  - Test fixtures for sign-band permutations (leads / trails / mixed / epsilon)
affects:
  - Plan 04 (visual polish + manual mobile check) — consumes this component unchanged
tech-stack:
  added: []
  patterns:
    - Recharts <Area> ranged-data pattern for shaded band between two lines
    - testid-carrying <g> wrappers around <Area> so tests assert on presence,
      not computed fill color (jsdom + oklch fills are unreliable)
    - Conditional wrapper rendering — if every point's band data is null, the
      whole <g data-testid> node is omitted, making presence/absence testable
      deterministically
    - vi.mock('recharts') for ResponsiveContainer in jsdom tests (fixed 800x400
      injection via cloneElement)
key-files:
  created:
    - frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx
  modified:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/lib/theme.ts
decisions:
  - Chose Recharts' native <Area dataKey> with ranged `[low, high]` tuples for
    the shaded band rather than building a custom SVG path or using a polygon
    plug-in. The ranged Area approach is a first-class Recharts feature, animates
    cleanly, respects the same X-axis as the lines, and needed no custom geometry.
  - Epsilon = 1 whole-number percentage point on the rounded series (not 1% of the
    raw 0-1 score). This avoids off-by-one flicker at the crossover without
    hiding meaningful gaps of 2%+.
  - Testid-carrying <g> wrapper approach (W6 resolution from the plan) — the
    wrapping element is only rendered when `hasAboveBand`/`hasBelowBand` is true
    for at least one point in the fixture. This lets the epsilon-neutral test
    assert `queryByTestId(...) === null` without depending on computed fill
    color (which is brittle in jsdom with oklch tokens).
  - Removed all references to the old Bar volume-bar series on this chart; the
    dual-line design replaces it. Volume bars survive on the ELO timeline and
    clock pressure charts where they remain informative.
  - Custom inline legend (two labeled spans with explicit data-testids) instead
    of Recharts' <Legend> with a custom content prop — simpler, directly
    testable, and stays tight to the chart on mobile.
metrics:
  duration: ~35m
  completed: 2026-04-24
---

# Phase 68 Plan 02: Frontend Dual-Line Chart Summary

**One-liner:** Replaced the single-line "Endgame vs Non-Endgame Score Gap over Time" chart with a two-line absolute-Score chart (endgame + non-endgame on a 0-100% axis) plus a sign-aware shaded band between the lines (green above, red below, nothing within ±1pp).

## What Changed

### New component: `EndgameScoreOverTimeChart`

**Path:** `frontend/src/components/charts/EndgamePerformanceSection.tsx` (lines 256–494)

**API:** unchanged prop shape from the old component — `{ timeline: ScoreGapTimelinePoint[]; window: number }` — so the Endgames.tsx call site only needed an import rename.

**Rendering:**
- `<ComposedChart>` with a 0–100% Y-axis and week-aligned X-axis.
- Two `<Line>` series: `endgame` (stroke `SCORE_TIMELINE_LINE_ENDGAME` = brand blue, same as MY_SCORE_COLOR) and `non_endgame` (stroke `SCORE_TIMELINE_LINE_NON_ENDGAME`, muted neutral).
- Two `<Area>` ranged-data series for the shaded band:
  - `band_above: [non_endgame, endgame]` when `endgame - non_endgame > 1pp` → green fill
  - `band_below: [endgame, non_endgame]` when `endgame - non_endgame < -1pp` → red fill
  - Both null within the ±1pp epsilon → no fill at that point
- Each `<Area>` is wrapped in a testid-carrying `<g>` (`score-band-above` / `score-band-below`) that only renders when at least one point in the fixture populates that band. This is the assertion path used by the tests — no fill-color assertions.
- Custom inline legend below the chart with `data-testid="chart-legend-endgame"` and `chart-legend-non-endgame`.
- Tooltip shows both absolute scores, their sample sizes (n=), and the signed gap.

### Theme tokens

Added four tokens to `frontend/src/lib/theme.ts`:

```ts
export const SCORE_TIMELINE_LINE_ENDGAME = MY_SCORE_COLOR;
export const SCORE_TIMELINE_LINE_NON_ENDGAME = 'oklch(0.60 0.02 260)';
export const SCORE_TIMELINE_FILL_ABOVE = 'oklch(0.50 0.14 145 / 0.18)';
export const SCORE_TIMELINE_FILL_BELOW = 'oklch(0.50 0.15 25 / 0.18)';
```

Hue values mirror `WDL_WIN` / `WDL_LOSS` at lower lightness with a 0.18 alpha so the grid and line strokes stay dominant.

### Info popover rewrite

On the WDL-comparison table popover (`perf-section-info`): removed the caveat paragraph "The Score Gap is a comparison, not an absolute measure…". The factual definition about the endgame-phase threshold and the "green = endgame stronger" color legend remain.

On the new chart's own popover (`score-timeline-info`): rewrote to include the sentence "The shaded area between the lines is color-coded: green when your endgame Score leads your non-endgame Score, red when it trails." Kept the rolling-window definition and the ≥10-games-per-side footnote.

### Endgames.tsx mount site

Changed the named import from `ScoreGapTimelineChart` to `EndgameScoreOverTimeChart` (line 20) and the JSX element at line 379. Prop names unchanged. No mobile-only duplicate of this chart existed to update.

## Tests

New test file `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` covers:

1. Container testid + title text — ✓
2. Both shaded-band testids present on mixed-sign fixture — ✓
3. Only `score-band-above` present when endgame leads throughout — ✓
4. Only `score-band-below` present when endgame trails throughout — ✓
5. Neither testid present when `|gap| <= 1pp` on every point — ✓
6. Both legend testids (`chart-legend-endgame` / `chart-legend-non-endgame`) present — ✓
7. Info popover: positive assertion on new shading sentence, negative assertion on removed caveat — ✓
8. Empty timeline → component returns null (no chart testid in the DOM) — ✓

Test setup: `beforeAll` stubs `window.matchMedia` (for `useIsMobile`) and `globalThis.ResizeObserver` (for Recharts' ResponsiveContainer). `vi.mock('recharts')` swaps `ResponsiveContainer` for a fixed-size (800×400) wrapper via `cloneElement` so the inner chart's layout code actually runs under jsdom — without this, `score-band-above/below` never reach the DOM and the band tests fail despite correct logic.

## Shading Implementation Path Chosen

From the plan's `<shading_implementation_hint>` option list, option 1 was selected: Recharts' native `<Area dataKey>` with ranged `[low, high]` tuples. Rationale:

- First-class Recharts feature, no custom SVG math.
- Uses the same X-axis ticks as the `<Line>` series automatically.
- `isAnimationActive={false}` kept for test determinism; `connectNulls={false}` kept so the band cleanly breaks at the epsilon zone.

The W6 "assert via testid presence, not fill color" direction rendered cleanly: wrapping each `<Area>` in a conditional `<g data-testid=...>` element and omitting the wrapper entirely when `hasAboveBand` / `hasBelowBand` is false gives the test suite a deterministic presence/absence signal without touching fill-color computations.

## W-notes and B-notes resolution

- **B1** (original wave 1, self-referential fallback `p.endgame_score ?? (p.score_difference + p.non_endgame_score)`): honoured — this plan ran in wave 2 after Plan 01 landed the required schema fields. Chart reads `p.endgame_score` / `p.non_endgame_score` directly with no fallback.
- **B3** (hand-maintained TS interface required fields): honoured — Plan 01 made both fields non-optional, chart consumes them as required.
- **W6** (testid-based band assertions, not fill color): implemented via conditional `<g data-testid>` wrapping. Confirmed by green test suite.

## Mobile Verification

The component reuses the same `useIsMobile()` hook + `ChartContainer`/`ResponsiveContainer` pattern as the removed `ScoreGapTimelineChart` and the peer `ClockDiffTimelineChart`. The container is `w-full h-72` inside `charcoal-texture rounded-md p-4` on the Endgames page — same outer wrapper as before, so no horizontal overflow regressions are possible without a layout-level change.

No live browser verification inside this worktree (executor has no dev-server access). Plan 04 will handle the manual mobile check at ≤400px width per the roadmap's Success Criterion 5. Programmatic mobile smoke is the epsilon-fixture test's deterministic DOM — no chart scrollWidth > clientWidth assertion was added because the underlying chart uses width-100% layout.

## Deviations from Plan

Minor test-infrastructure deviations (Rule 3 — blockers auto-fixed inline):

1. **[Rule 3] Added `window.matchMedia` + `ResizeObserver` stubs to the test file.** These jsdom-missing globals prevented the component from rendering under Vitest. Stubs live in a `beforeAll` block, not a project-wide setup file, because no setup file exists in `frontend/vite.config.ts` and adding one is out of scope.

2. **[Rule 3] Added `vi.mock('recharts')` to fix ResponsiveContainer sizing in jsdom.** Without a non-zero parent size, Recharts logs "The width(0) and height(0) of chart should be greater than 0" and refuses to render the inner surface, so the `<Area>` wrappers never reach the DOM. Mock preserves all other Recharts exports via `importActual` and replaces only `ResponsiveContainer`.

3. **[Rule 3] Popover test opens via `fireEvent.pointerDown` + `mouseDown` + `click` on the trigger.** The original test assumed the popover content was rendered eagerly; Radix uses a Portal that only mounts when open. `@testing-library/user-event` is not installed in this project, so the test uses the built-in `fireEvent` surface. This is the same approach used by `EndgameInsightsBlock.test.tsx` for its Radix-backed assertions.

These are classic jsdom + Recharts + Radix test-infra gaps — identified inline, fixed inline, no architectural implications. Documented here so future test files in this project know the three-stub pattern.

## Follow-ups

- Plan 03 (prompt simplification): consumes the renamed `score_timeline` subsection from Plan 01 and the dual-line narrative framing; no frontend dependency.
- Plan 04 (visual polish / mobile): will take a screenshot of this chart in dev and potentially tweak stroke widths, hide-dot behavior, or legend position based on that observation. Current defaults are best-guess desktop-first.
- Consider promoting the three jsdom test-infra stubs (matchMedia, ResizeObserver, `vi.mock('recharts')` ResponsiveContainer override) into `frontend/src/test/setup.ts` if other future chart components hit the same blockers. Out of scope here.

## Verification

Full checks from the worktree:

- `cd frontend && npm run lint` — clean
- `cd frontend && npm run build` — exits 0 (1 non-blocking chunk-size warning, pre-existing)
- `cd frontend && npm run knip` — no new dead exports reported
- `cd frontend && npm test -- --run` — 9 files, 106 tests pass (including 8 new `EndgameScoreOverTimeChart` tests)
- `grep -rn "ScoreGapTimelineChart" frontend/src/` — zero matches
- `grep -rn "Score Gap over Time" frontend/src/` — zero matches
- `grep -rn "the Score Gap is a comparison" frontend/src/` — zero matches
- New strings present in `EndgamePerformanceSection.tsx`: `EndgameScoreOverTimeChart`, `Endgame vs Non-Endgame Score over Time`, `green when your endgame Score leads` (wrapped), `score-band-above`, `score-band-below`

## Self-Check: PASSED

- e7905c2 (RED) — FOUND
- 8a5ee39 (GREEN) — FOUND
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — FOUND, contains `EndgameScoreOverTimeChart`, removed `ScoreGapTimelineChart`
- `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` — FOUND, 8 tests pass
- `frontend/src/lib/theme.ts` — FOUND, 4 new SCORE_TIMELINE_* tokens present
- `frontend/src/pages/Endgames.tsx` — FOUND, imports + mounts new component
- No reference to `ScoreGapTimelineChart` anywhere in `frontend/src/`
