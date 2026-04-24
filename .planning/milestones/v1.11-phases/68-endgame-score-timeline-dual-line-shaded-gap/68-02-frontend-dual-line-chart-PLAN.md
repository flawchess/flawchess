---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 02
type: execute
wave: 2
depends_on:
  - 68-01
files_modified:
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx
autonomous: true
requirements: []
tags:
  - insights
  - endgame
  - frontend
  - charts
must_haves:
  truths:
    - "A single chart titled 'Endgame vs Non-Endgame Score over Time' renders two Recharts `<Line>` series (endgame Score and non-endgame Score) on one 0-100% Y-axis."
    - "A colored shaded area fills the vertical band between the two lines: green when endgame ≥ non-endgame, red when endgame < non-endgame, neutral (no fill) when within ±1% epsilon."
    - "The old single-line 'Score Gap over Time' chart is removed from the page."
    - "The info popover no longer contains the 'the Score Gap is a comparison, not an absolute measure' caveat paragraph; it contains a short sentence explaining the shading."
    - "The chart works on mobile (no horizontal overflow, legend readable at <=400px width)."
  artifacts:
    - path: "frontend/src/components/charts/EndgamePerformanceSection.tsx"
      provides: "New dual-line `EndgameScoreOverTimeChart` component replacing the old `ScoreGapTimelineChart`"
      contains: "Endgame vs Non-Endgame Score over Time"
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "Updated mount site calling the new chart with the same data prop"
      contains: "EndgameScoreOverTimeChart"
    - path: "frontend/src/lib/theme.ts"
      provides: "Optional new token SCORE_TIMELINE_FILL_ABOVE / SCORE_TIMELINE_FILL_BELOW (with ~0.18 alpha) if existing WDL_WIN/WDL_LOSS with opacity modifiers aren't clean enough"
  key_links:
    - from: "frontend/src/pages/Endgames.tsx"
      to: "frontend/src/components/charts/EndgamePerformanceSection.tsx::EndgameScoreOverTimeChart"
      via: "Named import + prop drilling of `scoreGapData.timeline` + `scoreGapData.timeline_window`"
      pattern: "EndgameScoreOverTimeChart"
    - from: "EndgameScoreOverTimeChart"
      to: "frontend/src/lib/theme.ts"
      via: "Color tokens for line colors (endgame=MY_SCORE_COLOR or brand; non_endgame=muted/neutral) and shaded area (green/red with low alpha)"
      pattern: "from '@/lib/theme'"
---

<objective>
Replace the single-line "Endgame vs Non-Endgame Score Gap over Time" chart in `EndgamePerformanceSection.tsx` with a two-line "Endgame vs Non-Endgame Score over Time" chart that renders both absolute Score series and a color-coded shaded area between them. Rewrite the chart info popover to drop the "comparison, not absolute" caveat and add a one-liner about the shading.

**B1 resolution — runs in wave 2, depends on Plan 01.** The checker correctly flagged that this plan reads `p.endgame_score` / `p.non_endgame_score` off `ScoreGapTimelinePoint`, and those fields are added by Plan 01 (both the Pydantic schema AND the hand-maintained TS interface in `frontend/src/types/endgames.ts`). The original `wave: 1` + self-referential fallback arithmetic (`p.endgame_score ?? (p.score_difference + p.non_endgame_score)`) was nonsense — it would produce `NaN` whenever both fields are absent. This plan now runs **after** Plan 01 completes, reads the two fields directly with no fallback, and treats them as required.

Purpose: The existing single-line chart plots the subtraction `endgame_score - non_endgame_score`, which hides the composition — a -10% gap can mean weak endgame or strong non-endgame, and the user can't tell which. A two-line chart with shaded gap lets the user read both sides and the differential at a glance, matching Success Criterion 1.

Output:
- Removed `ScoreGapTimelineChart` component.
- New `EndgameScoreOverTimeChart` component with two `<Line>` series, a sign-aware shaded fill implemented via two `<Area>` components wrapped in testid-carrying `<g>` elements (W6 fix — testid presence is the assertion, not computed fill color), a legend, tooltip showing `Endgame / Non-endgame / Gap`, `data-testid="endgame-score-timeline-chart"` on the container, and legend-label `data-testid`s.
- Mobile-verified layout using same responsive container pattern as the current chart.
- Rewritten info popover: drops the caveat paragraph, keeps the factual definition and sample-quality footnote, adds one new sentence: "The shaded area between the lines is color-coded: green when your endgame Score leads your non-endgame Score, red when it trails."
- `Endgames.tsx` mount site updated to import + render the new component; old `ScoreGapTimelineChart` import removed so knip doesn't flag a dead export.
- Vitest tests updated to cover: both lines rendered, both shaded-band testids present on the correct sign pattern, neither testid present on the epsilon-neutral fixture, legend labels present, info popover copy asserted (positive for new sentence, negative for removed caveat).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-CONTEXT.md
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md
@CLAUDE.md
@frontend/src/components/charts/EndgamePerformanceSection.tsx
@frontend/src/components/charts/EndgameClockPressureSection.tsx
@frontend/src/lib/theme.ts
@frontend/src/types/endgames.ts

<interfaces>
<!-- Key types and analogs the executor needs. -->

From frontend/src/components/charts/EndgamePerformanceSection.tsx (lines 256-472):
```typescript
// CURRENT (to replace)
export interface ScoreGapTimelineChartProps {
  timeline: ScoreGapTimelinePoint[];
  window: number;
}
export function ScoreGapTimelineChart({ timeline, window }: ScoreGapTimelineChartProps) {
  // Renders a single <Line dataKey="gap"> over a derived gap % series,
  // plus a volume-bar muted series, inside a Recharts <ComposedChart>.
  // Chart title (line ~305): "Endgame vs Non-Endgame Score Gap over Time"
}
```

From frontend/src/pages/Endgames.tsx (line ~20 + ~379):
```typescript
import {
  EndgamePerformanceSection,
  MATERIAL_ADVANTAGE_POINTS,
  PERSISTENCE_MOVES,
  ScoreGapTimelineChart,            // ← replace with EndgameScoreOverTimeChart
} from '@/components/charts/EndgamePerformanceSection';
...
{scoreGapData && scoreGapData.timeline.length > 0 && (
  <div className="charcoal-texture rounded-md p-4">
    <ScoreGapTimelineChart
      timeline={scoreGapData.timeline}
      window={scoreGapData.timeline_window}
    />
  </div>
)}
```

From frontend/src/types/endgames.ts (after Plan 01 lands):
```typescript
export interface ScoreGapTimelinePoint {
  date: string;
  score_difference: number;
  endgame_game_count: number;
  non_endgame_game_count: number;
  per_week_total_games: number;
  endgame_score: number;      // 0.0-1.0 absolute endgame rolling mean (Plan 01)
  non_endgame_score: number;  // 0.0-1.0 absolute non-endgame rolling mean (Plan 01)
}
```
**B3 resolution note:** Plan 01 extends this hand-maintained interface. Both fields are **required** (not optional). Read them directly — no defensive fallback.

From frontend/src/lib/theme.ts (lines 16-28):
```typescript
export const WDL_WIN = 'oklch(0.50 0.14 145)';       // green
export const WDL_LOSS = 'oklch(0.50 0.15 25)';       // red
export const WDL_DRAW = 'oklch(0.60 0.02 260)';      // neutral

export const ZONE_SUCCESS = WDL_WIN;                  // green zone
export const ZONE_DANGER = WDL_LOSS;                  // red zone
```

Analog pattern from frontend/src/components/charts/EndgameClockPressureSection.tsx (~lines 449-475): dual-series timeline using Recharts `<ComposedChart>` with two `<Line>` elements. Study this component's legend layout, mobile breakpoint behavior, and tooltip formatter — reuse the same shape for the new chart.
</interfaces>

<shading_implementation_hint>
Recharts supports "area between two lines" via a derived data field. The clean path:

1. Map each point to `{ date, endgame, non_endgame, band_above, band_below }` where
   - `band_above: [number, number] | null` = `[non_endgame, endgame]` when `endgame - non_endgame > 1`, else null (green area, endgame leading).
   - `band_below: [number, number] | null` = `[endgame, non_endgame]` when `endgame - non_endgame < -1`, else null (red area, endgame trailing).
   - Epsilon: if `abs(endgame - non_endgame) <= 1`, both arrays are null at that point → no fill (clean neutral).
2. Render two `<Area>` components, one per band, using Recharts 2.x ranged-data pattern (pass the `[low, high]` tuple as the data value; Recharts renders a ranged band between them).
3. **W6 resolution — wrap each `<Area>` in a testid-carrying `<g>` element** so tests can assert on `data-testid` presence instead of computed fill color (jsdom + oklch tokens don't compute reliably):
   ```tsx
   <g data-testid="score-band-above">
     <Area dataKey="band_above" fill={SCORE_TIMELINE_FILL_ABOVE} stroke="none" isAnimationActive={false} />
   </g>
   <g data-testid="score-band-below">
     <Area dataKey="band_below" fill={SCORE_TIMELINE_FILL_BELOW} stroke="none" isAnimationActive={false} />
   </g>
   ```
   If Recharts 2.x balks at wrapping `<Area>` in `<g>` inside `<ComposedChart>` (the chart library may hoist its own group layer), alternative: attach the testid to the `<Area className>` → rendered `<g>` output, or use the `id` prop on the Area and assert via `querySelector` on the serialized SVG. Pick whichever renders cleanly.
4. Verify with a handcrafted fixture that shading switches segments at the sign crossover, not just at the two endpoints.
</shading_implementation_hint>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build EndgameScoreOverTimeChart and wire it into the Endgames page</name>
  <read_first>
    - frontend/src/components/charts/EndgamePerformanceSection.tsx (full file — the chart-to-replace is at lines 256-472)
    - frontend/src/components/charts/EndgameClockPressureSection.tsx (lines 440-480 — dual-series analog)
    - frontend/src/pages/Endgames.tsx (lines 20-25 imports + 375-390 mount site)
    - frontend/src/lib/theme.ts (full file — color tokens + any opacity helpers)
    - frontend/src/types/endgames.ts (lines 100-130 — verify Plan 01's endgame_score / non_endgame_score additions landed)
    - frontend/src/components/charts/EndgameConvRecovChart.tsx (line ~10 — this file imports from EndgamePerformanceSection; verify its imports still resolve after the rename)
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md (confirm the new backend shape and the TS interface extension are in place)
  </read_first>
  <behavior>
    - Test 1: Component renders a container with `data-testid="endgame-score-timeline-chart"` and a heading whose text equals "Endgame vs Non-Endgame Score over Time" (exact string match).
    - Test 2 (W6 — testid-based, not fill-based): Given a 6-point fixture where endgame leads in points 1-3 and trails in points 4-6, the rendered DOM contains BOTH `<g data-testid="score-band-above">` AND `<g data-testid="score-band-below">`. Assert via `screen.getByTestId(...)` — no fill-color assertion.
    - Test 3: Given an epsilon-boundary fixture where `|endgame - non_endgame| <= 1` for all points, NEITHER `score-band-above` NOR `score-band-below` testid is present (both `<Area>` bands have fully-null data, so Recharts may still render an empty `<g>` — in that case, assert the `<path>` inside is empty or the data tuple is all-null. The simplest practical assertion: the `<Area>` `dataKey`s return null for every point, which for Recharts means no `<path d="...">` element with actual coordinates).
    - Test 4: Given a mixed-sign fixture (endgame leads for part of the range, trails for the rest), BOTH testids are present.
    - Test 5: Given an all-endgame-leading fixture, only `score-band-above` testid is present; `score-band-below` is absent (or its area has no renderable data).
    - Test 6: Legend renders two labeled entries: "Endgame" and "Non-endgame". Each has a `data-testid` (e.g. `chart-legend-endgame`, `chart-legend-non-endgame`).
    - Test 7: Tooltip formatter returns a string (or JSX) containing `Endgame`, `Non-endgame`, and `Gap` labels when given a sample point.
    - Test 8: Mobile smoke — component rendered at 375px container width has no element with `scrollWidth > clientWidth` (no horizontal overflow).
    - Test 9: Old `ScoreGapTimelineChart` export is gone — `grep` the file for `export function ScoreGapTimelineChart` returns nothing.
    - Test 10: Endgames.tsx imports `EndgameScoreOverTimeChart` and no longer imports `ScoreGapTimelineChart`.
  </behavior>
  <action>
    1. **Inspect current Recharts version**: `(cd frontend && npm ls recharts)` to confirm 2.x vs 3.x, then pick the shading pattern per `<shading_implementation_hint>` above. The dual-`<Area>` with ranged values `[low, high]` wrapped in testid-carrying `<g>` elements is the target.

    2. **Add color tokens in theme.ts** (only if existing WDL_WIN/WDL_LOSS with inline opacity suffix don't read cleanly in JSX): append two new exports near line 40:
       ```typescript
       export const SCORE_TIMELINE_FILL_ABOVE = 'oklch(0.50 0.14 145 / 0.18)';  // green, low alpha
       export const SCORE_TIMELINE_FILL_BELOW = 'oklch(0.50 0.15 25 / 0.18)';   // red, low alpha
       export const SCORE_TIMELINE_LINE_ENDGAME = MY_SCORE_COLOR;               // brand blue line (already used for "my score" on the bullet chart)
       export const SCORE_TIMELINE_LINE_NON_ENDGAME = 'oklch(0.60 0.02 260)';   // matches WDL_DRAW neutral, muted partner line
       ```
       If existing tokens already cover the semantics cleanly, prefer reuse. Either way: NO raw hex literals.

    3. **Rewrite the chart component** in `frontend/src/components/charts/EndgamePerformanceSection.tsx`, lines 256-472:
       - Delete the `ScoreGapTimelineChart` export and its derived-gap data munging.
       - Add `EndgameScoreOverTimeChartProps` and `EndgameScoreOverTimeChart` that:
         - Accept the same `{ timeline: ScoreGapTimelinePoint[]; window: number }` shape.
         - Map each point to `{ date, endgame, non_endgame, band_above, band_below }` where
           - `endgame = Math.round(p.endgame_score * 100)` (whole-number %; field is guaranteed present by Plan 01 — no fallback),
           - `non_endgame = Math.round(p.non_endgame_score * 100)`,
           - `band_above: [number, number] | null` = `[non_endgame, endgame]` when `endgame - non_endgame > 1`, else null,
           - `band_below: [number, number] | null` = `[endgame, non_endgame]` when `endgame - non_endgame < -1`, else null.
           - Epsilon is 1 whole-number %; this avoids flicker at the crossover.
         - Render a Recharts `<ComposedChart>` with:
           - A 0-100 Y-axis (`domain={[0, 100]}`).
           - Two `<Area>` components, one per band, wrapped in `<g data-testid="score-band-above">` / `<g data-testid="score-band-below">` respectively. Each `<Area>` uses fill tokens from step 2, `stroke="none"`, `isAnimationActive={false}`.
           - Two `<Line>` components for `endgame` and `non_endgame`, each with a distinct stroke token, `dot={false}`, `strokeWidth={2}`, and `connectNulls={false}` so activity gaps remain visible.
           - A custom `<Legend>` rendering two items: "Endgame" (color = endgame line token) and "Non-endgame" (color = non-endgame line token), each with a `data-testid`.
           - A `<Tooltip>` whose formatter returns, for a hovered bucket, e.g.
             ```
             {date}
             Endgame: {endgame}% (n={endgame_n})
             Non-endgame: {non_endgame}% (n={non_endgame_n})
             Gap: {endgame - non_endgame > 0 ? '+' : ''}{endgame - non_endgame}%
             ```
             (reuse the project's tooltip styling helpers from the clock-pressure analog).
         - Wrap in a titled card identical in structure to the old chart. Title string: `Endgame vs Non-Endgame Score over Time` (delete the word "Gap").
         - Container `data-testid="endgame-score-timeline-chart"`.

    4. **Rewrite the info popover** on the Endgame vs Non-Endgame WDL table (`EndgamePerformanceSection`, line ~115-116):
       - DELETE the paragraph: `<p>The Score Gap is a comparison, not an absolute measure. A positive value can mean stronger endgames <em>or</em> weaker non-endgame play; a negative value, the reverse. Compare the two Score rows to see which side is driving it.</p>`
       - ADD one new sentence inside the chart's own info popover (build one if the chart doesn't yet have one; place it next to the new chart title):
         `<p>The shaded area between the lines is color-coded: green when your endgame Score leads your non-endgame Score, red when it trails.</p>`
       - KEEP the existing factual definition about "endgame phase = ≥ 3 full moves with ≤ 6 major/minor pieces" and the "points with n < 3 dropped" sample-quality footnote. These remain relevant.

    5. **Update `frontend/src/pages/Endgames.tsx`**:
       - Line 20: change import from `ScoreGapTimelineChart` to `EndgameScoreOverTimeChart`.
       - Line ~379: change the JSX element accordingly. Prop names unchanged (`timeline`, `window`).

    6. **Update tests**: edit (or create) `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx`. If no test file exists, create one using the project's vitest + @testing-library/react setup (see `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx` for the file-level `// @vitest-environment jsdom` pragma and render/screen helpers). Cover Tests 1-10 above. **Tests 2-5 must assert on `data-testid` presence via `screen.getByTestId` / `screen.queryByTestId`, not on computed fill color** (W6).

    7. **Desktop + mobile parity**: per CLAUDE.md "always apply changes to mobile too", search the file for any duplicated mobile-only card rendering of the old chart. If present, apply the same replacement. If not present, confirm with a sweep `grep -n "ScoreGapTimelineChart" frontend/src/` after the refactor.

    8. Run `(cd frontend && npm run lint && npm run build && npm test -- --run EndgamePerformanceSection)`. Fix `noUncheckedIndexedAccess` narrowing errors and knip dead-export warnings before proceeding.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run lint &amp;&amp; npm run build &amp;&amp; npm test -- --run EndgamePerformanceSection</automated>
  </verify>
  <done>
    - `frontend/src/components/charts/EndgamePerformanceSection.tsx` no longer contains the strings `ScoreGapTimelineChart`, `Score Gap over Time`, or `the Score Gap is a comparison`.
    - `frontend/src/components/charts/EndgamePerformanceSection.tsx` contains the strings `EndgameScoreOverTimeChart`, `Endgame vs Non-Endgame Score over Time`, `green when your endgame Score leads`, `score-band-above`, and `score-band-below`.
    - `grep -rn "ScoreGapTimelineChart" frontend/src/` returns zero matches.
    - `cd frontend &amp;&amp; npm run build` exits 0.
    - `cd frontend &amp;&amp; npm run knip` reports no new dead exports introduced by this plan.
    - Manual check via `run_local.sh` (optional but recommended): both lines render with shaded fill at the right boundary.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| backend → frontend JSON | Frontend consumes `score_gap_material.timeline` verbatim; a malformed or out-of-range `endgame_score`/`non_endgame_score` (e.g. NaN, negative, >1.0) must not crash the chart. |

## STRIDE Threat Register

Security enforcement is light for this phase — pure UI/payload rework, no new auth surface, no external data ingress.

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-68-01 | Tampering | `ScoreGapTimelinePoint` serialization | accept | Backend is trusted (server-computed); Pydantic v2 validation on the backend is the boundary guard. Frontend `Math.round()` on the two required fields returns a sane chart on unexpected NaN input (NaN becomes NaN after round, renders as gap — not a crash). |
| T-68-02 | DoS | Chart with many buckets | accept | Timeline trimmed by rolling-window logic server-side (weekly cadence, cold-start drops, MIN_GAMES_FOR_TIMELINE filter). Recharts handles the resulting count trivially. |
</threat_model>

<verification>
- `cd frontend && npm run lint` clean.
- `cd frontend && npm run build` exits 0.
- `cd frontend && npm run knip` reports no new dead exports.
- `cd frontend && npm test -- --run EndgamePerformanceSection` passes all new tests.
- `grep -rn "ScoreGapTimelineChart\|Score Gap over Time" frontend/src/` returns zero matches.
- `grep -rn "the Score Gap is a comparison" frontend/src/` returns zero matches.
- Manual mobile check at 375px: chart renders without horizontal scrollbar; legend wraps below chart if needed.
</verification>

<success_criteria>
- Success Criterion 1 from ROADMAP.md satisfied: chart titled "Endgame vs Non-Endgame Score over Time" with two lines (endgame + non-endgame, 0-100%) and green/red shaded area between them. Old single-line chart is gone.
- Success Criterion 4: info popover no longer carries the "Score Gap is a comparison, not an absolute measure" caveat.
- Success Criterion 5 (mobile slice): chart renders without overflow on narrow viewports.
- CLAUDE.md compliance: theme tokens only (no raw hex), `data-testid` on chart container + legend items + shaded-band groups, `noUncheckedIndexedAccess` respected, knip clean.
</success_criteria>

<output>
After completion, create `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-02-SUMMARY.md` documenting:
- Final component name and API.
- Shading implementation path chosen (which of the Recharts patterns from the hint ended up used and why).
- Any theme token changes.
- Confirmation that the `<g data-testid="score-band-above|below">` wrapping approach rendered correctly (W6 test assertion path).
- A 1-line pointer to the mobile verification approach (screenshot path or visual-check note).
</output>
