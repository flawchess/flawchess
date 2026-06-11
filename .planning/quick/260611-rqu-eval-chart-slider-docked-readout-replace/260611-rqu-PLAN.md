---
phase: quick-260611-rqu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
autonomous: true
requirements: [EVAL-SLIDER]
must_haves:
  truths:
    - "A scrub slider sits below the eval chart; dragging it / arrow-keying it moves the active ply (crosshair + miniboard + readout all follow)"
    - "Severity tick marks appear on the slider track at flaw plies, colored by severity (blunder/mistake/inaccuracy)"
    - "A fixed-height single-line readout sits between the chart and slider showing move label, eval, clock, move time, plus flaw detail on M/B plies"
    - "The floating tooltip and all its touch/pin/outside-pointer machinery are gone"
    - "Desktop chart hover still scrubs; on mouse-leave the active ply reverts to the slider's value"
    - "At rest the slider and readout default to the last eval'd ply"
  artifacts:
    - path: "frontend/src/components/library/EvalChart.tsx"
      provides: "Eval chart + docked readout + scrub slider with severity ticks; tooltip machinery removed"
    - path: "frontend/src/components/results/LibraryGameCard.tsx"
      provides: "Host card with z-index hover hacks removed; same hover-ply contract"
  key_links:
    - from: "EvalChart slider/hover"
      to: "onHoverPlyChange (parent miniboard)"
      via: "unified active-ply state"
      pattern: "onHoverPlyChange"
---

<objective>
Replace the EvalChart's floating tooltip with a fixed docked readout line plus a native-range scrub slider (with severity tick marks) below the chart. Unify hover and slider into one active-ply state, delete all tooltip/touch/pin machinery, and strip the z-index hover hacks in both EvalChart and LibraryGameCard.

Purpose: a tooltip that blankets a 130px sparkline and needs touch-drag/pin/outside-pointer hacks is fragile and covers the chart. A docked readout + slider gives a stable, touch-native, keyboard-accessible scrub UX with no overlay.

Output: reworked `EvalChart.tsx` (readout + slider + ticks, tooltip removed) and `LibraryGameCard.tsx` (z-index hacks removed).
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@frontend/src/components/library/EvalChart.tsx
@frontend/src/components/results/LibraryGameCard.tsx
@frontend/src/lib/theme.ts
@frontend/src/components/library/TagChip.tsx
@frontend/src/types/library.ts

Key facts established from reading the code:
- `EvalPoint`: `{ ply, es, eval_cp, eval_mate, clock_seconds, move_seconds }`. `FlawMarker`: `{ ply, severity, tags, is_user, move_san }`.
- `trimToEvalRange(evalSeries)` yields `chartSeries`; its first/last `.ply` are the slider's min/max. Memoize and reuse the SAME trimmed array for both the chart and the slider bounds.
- Theme colors (import from `@/lib/theme`, never inline): `SEV_BLUNDER`, `SEV_MISTAKE`, `SEV_INACCURACY`, `EVAL_CHART_PHASE_LINE`, `EVAL_CHART_LINE`. Tag family colors live in `TagChip.tsx` (`TAG_FAMILY_COLORS` keyed by `getTagFamily`) — those are not exported, so readout tags use plain muted text (acceptable fallback per locked decision 3); do NOT export/duplicate the family-color map for this quick task.
- `ChartTooltipBox` is imported by 8 OTHER components (ScoreChart, RatingChart, FlawTrendChart, etc.) — do NOT delete `chart-tooltip-box.tsx`. Only remove the import + usage from EvalChart.
- No EvalChart test file exists; no test references the tooltip, `buildTooltipContent`, or eval-chart hover. GamesTab/FlawCard tests render the card but do not assert on chart internals. So no test updates are expected, but knip may flag newly-orphaned exports/helpers inside EvalChart.
- `formatEval` currently returns a `"Eval: …"`-prefixed string; the readout wants the bare value ("+0.3" / "Mate in 5#" / "Checkmate"). Refactor `formatEval` to return the bare eval and compose labels at the call site, or add a small bare-eval helper — keep the mate-priority and `#`-ending "Checkmate" logic intact.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rework EvalChart — unified active-ply state, docked readout, scrub slider with severity ticks; delete tooltip machinery</name>
  <files>frontend/src/components/library/EvalChart.tsx</files>
  <action>
Replace the tooltip-driven interaction model with a slider + docked readout, all driven by one active-ply state.

STATE MODEL (single source of truth for the active ply):
- Keep a `hoverPly: number | null` (transient — chart hover only) and add `sliderPly: number` (persistent — last explicitly-set slider value, also moved by chart-driven scrubs as needed).
- Initialize `sliderPly` to the LAST eval'd ply: the max `.ply` in the trimmed `chartSeries` (locked decision 5). Use a `useState` initializer plus a `useEffect` that resets it when the series identity changes (guard against stale ply after data swap).
- Derive `activePly = hoverPly ?? sliderPly`. This single value drives: the crosshair ReferenceLine (replace `hoverPly` usage with `activePly`), the readout content, the slider thumb position, and `onHoverPlyChange` to the parent (the parent miniboard).
- Report `activePly` to the parent via `onHoverPly Change(activePly)` whenever it changes (use a `useEffect` on `activePly`, or call in the setters). The parent contract is unchanged in shape (a number, never null now — at rest it is the resting ply). Keep the prop name `onHoverPlyChange` (locked decision 9 permits a rename, but keeping it avoids touching the parent's prop wiring; add a one-line comment that it now reports the active scrub ply from any input).

DELETE (locked decision 4):
- The `ChartTooltip` import and its `<ChartTooltip .../>` element, `buildTooltipContent`, `FlawTooltipDetail` (its content moves into the readout — see below), the `ChartTooltipBox` import (NOT the file), `allowEscapeViewBox`, `suppressTooltip`/`pinned` state, the `wrapperRef` only if no longer needed, the document-level outside-pointerdown `useEffect`, `touchStartRef`/`draggedRef`/`TOUCH_SLOP_PX` and all touch handlers (`handleTouchStart`, `handleTouchMoveRaw`, `handleTouchEnd`), the `onTouchStart/Move/End/Cancel` wrapper props, the chart-level `onTouchMove={handlePointerMove}`, and the `relative z-10` hover hack on the wrapper className (the tooltip no longer escapes the viewBox, so no z lift is needed).
- Keep chart `onMouseMove`/`onMouseLeave`: `onMouseMove` sets `hoverPly` from `activeLabel`; `onMouseLeave` sets `hoverPly` back to `null` (activePly then falls back to `sliderPly` — locked decision 6). Remove the `setSuppressTooltip` calls.

DOCKED READOUT (locked decision 3) — a sibling block rendered directly BETWEEN the chart and the slider:
- Single line, FIXED height (e.g. a fixed `h-*` or `min-h`/`leading` constant so there is no layout shift while scrubbing), `truncate` (never wrap), `text-sm` minimum (the text-xs tooltip exception is gone).
- `data-testid={`eval-readout-${gameId}`}`.
- Content for `activePly`: move label (reuse `formatMoveLabel`, visually dominant in `text-foreground`) · eval (bare value via the refactored `formatEval`; "Checkmate" when the SAN ends `#`; mate-priority preserved) · clock (`formatClock`, when present) · move time (`Ns`, when present). When the active ply is an M/B (or revealed) flaw in `markerMap`/`allMarkerMap`: append the existing marker glyph (`MarkerGlyph`) + "You/Opponent · Blunder/Mistake/Inaccuracy" in the severity color + tags (filter out `PHASE_TAGS`). Tags render as plain muted text (or comma-separated) — plain text fallback is acceptable per locked decision 3; do not duplicate TagChip family colors.
- Use the dominant-foreground / muted split: move label `text-foreground font-semibold`, the rest `text-muted-foreground`, flaw glyph+label colored via `severityColor(marker.severity)`.
- Reuse `MarkerGlyph` and `severityColor` (already in the file). The old `FlawTooltipDetail` logic folds into this readout — port it, then delete the standalone function.

SCRUB SLIDER (locked decisions 1, 2) — below the readout:
- Native `<input type="range">`, `min` = first ply of `chartSeries`, `max` = last ply, `step={1}`, `value={activePly}`, `onChange` sets `sliderPly` (and clears `hoverPly` is unnecessary — slider change is an explicit set; just set sliderPly). Styling: full-width, brand-consistent track/thumb (reuse the project's range styling approach seen in `components/ui/slider.tsx` only as reference — a plain styled native input is fine; do NOT pull in the Radix Slider). Track color from theme (`EVAL_CHART_PHASE_LINE` or a muted token); keep it subtle.
- `data-testid={`eval-slider-${gameId}`}`, `aria-label={`Scrub move for game ${gameId}`}`.
- SEVERITY TICKS: position small vertical ticks over the slider track at each flaw ply (from `flawMarkers` — INCLUDE inaccuracies here, locked decision 2, giving the hidden inaccuracy dots a home). Render as absolutely-positioned `<div>`s inside a `relative` wrapper that overlays the input track. Compute each tick's left% as `(ply - min) / (max - min) * 100`. Color by `severityColor`. Distinguish user vs opponent subtly: user = full-height tick, opponent = shorter and/or lower-opacity tick (planner's call — keep it subtle). Ticks are `aria-hidden` and `pointer-events-none` so they never block the input. Extract any tick dimensions/opacity into named constants (no magic numbers): e.g. `TICK_USER_HEIGHT`, `TICK_OPP_HEIGHT`, `TICK_OPP_OPACITY`, `TICK_WIDTH`.
- Wrap the input + tick overlay in a container whose horizontal padding matches the chart's edge inset (the chart fill spans full width with zero margin, so min/max plies land on the exact edges — align the tick math and the input thumb travel to that same 0..100% so ticks line up under the corresponding chart x positions). A small comment explaining the alignment assumption is worth adding.

LAYOUT BUDGET (locked decision 8):
- Desktop: the chart column currently passes `heightClass="h-[132px]"` to match the miniboard. Shrink the CHART to ~90–96px so chart + readout + slider fit within roughly the same 132px envelope. Introduce a constant for the desktop chart height (e.g. consumed via the existing `heightClass` prop from the parent — see Task 2) and let the readout+slider consume the remainder. Mobile keeps the chart near its current height; modest card growth is fine.
- Render order inside the EvalChart wrapper: chart (ChartContainer) → readout → slider. The outer wrapper keeps `data-testid={`eval-chart-${gameId}`}` and `aria-label`/`role="img"`; the focus-outline suppression classes stay.

KEEP INTACT (locked decision 9): `highlightedPlies`, `outlinedPlies`, `focusedPly` (ping), `flipped`, the dual-marker dot renderer, phase lines, midline. The crosshair now reads `activePly` (locked decision 7).

After editing, run `npm run knip` mentally: ensure no helper left orphaned (e.g. if `buildTooltipContent` is deleted, also delete now-unused imports). `formatClock`, `formatEval`, `formatMoveLabel`, `MarkerGlyph`, `severityColor`, `flawDotElement` all remain used.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit -p tsconfig.app.json 2>&1 | grep -i "EvalChart" || echo "no EvalChart type errors"</automated>
  </verify>
  <done>EvalChart renders a chart + docked readout + scrub slider with severity ticks; tooltip/touch/pin/outside-pointer code is gone; crosshair and readout follow the unified activePly; slider defaults to the last eval'd ply; type-checks clean.</done>
</task>

<task type="auto">
  <name>Task 2: Strip z-index hover hacks in LibraryGameCard; adjust chart height budget; full frontend verification</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx</files>
  <action>
LibraryGameCard changes (locked decision 4 + 8):
- Remove the `z-30 while hovering` hack: the `hoverPly != null && 'z-30'` in the `Card` className, and the long explanatory comment block above the `<Card>` about the escaping tooltip / stacking context. The `hoverPly` state itself STAYS (it still drives the miniboard via `handleHoverPlyChange`); only its use as a z-index trigger is removed. If `hoverPly` is now used ONLY for the miniboard (not z), keep it — that is correct.
- Evaluate `overflowVisible` on the `<Card>`: it existed so the tooltip could escape the card border. With the tooltip gone, the readout+slider live INSIDE the card, so `overflowVisible` is likely no longer needed — remove it AND update the related comment, unless something else in the card depends on overflow visibility (check: nothing obvious does). If unsure after a quick check, leave `overflowVisible` and note it; do not break clipping of the rounded header. Also revisit the `rounded-t-md` comment on `CardHeader` which references overflowVisible — leave the class, just don't let the comment go stale if you removed overflowVisible.
- Chart height budget: the parent passes `heightClass="h-[132px]"` (desktop) and `heightClass="h-[130px]"` (mobile) to match the miniboard. For desktop, change the passed height so the CHART is ~90–96px (e.g. `heightClass="h-[92px]"`) leaving room for the readout+slider within the ~132px column envelope. Mobile: keep the chart near its current height (the mobile block is stacked/full-width, so modest card growth is acceptable — leave `h-[130px]` or trim slightly to taste). The `handleHoverPlyChange` still yields focus and sets `hoverPly`; `activePly`/`boardFen`/`cornerDot`/`lastMove` derivation is unchanged (the parent receives a non-null ply at rest now, which clamps fine through the existing `Math.min(Math.max(...))`).
- The parent's `onHoverPlyChange` now fires with a non-null resting ply at mount. Verify this does not cause an unwanted focus-yield on mount: `handleHoverPlyChange` calls `yieldFocus()` when `ply != null`, which would clear the open-focus ping immediately. GUARD THIS: only yield focus on a USER-driven scrub, not the initial resting report. Simplest fix — have EvalChart report `null`-vs-ply semantics OR add a flag; pragmatically, only call `yieldFocus()` in `handleHoverPlyChange` when the ply differs from the resting/last ply, or gate the initial mount report. Pick the minimal correct approach and comment it. (This is the one real behavioral trap in this refactor — the focus ping must still survive until the user actually scrubs.)

Then run the full frontend gate and resolve all output.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run && npm run knip</automated>
  </verify>
  <done>z-30 hover hack removed; chart height shrunk to fit the readout+slider within the desktop envelope; focus ping survives mount and only yields on real user scrub; `npm run lint`, `npm test --run`, and `npm run knip` all pass clean.</done>
</task>

</tasks>

<verification>
- `cd frontend && npm run lint && npm test -- --run && npm run knip` all pass.
- No `text-xs`, raw color literals, or magic tick numbers introduced (constants extracted; theme colors imported).
- `data-testid="eval-slider-{gameId}"` and `data-testid="eval-readout-{gameId}"` present; slider has `aria-label`.
- No remaining references to `ChartTooltip`, `buildTooltipContent`, `suppressTooltip`, `pinned`, `TOUCH_SLOP_PX`, or `allowEscapeViewBox` in EvalChart; `chart-tooltip-box.tsx` file untouched (still used by 8 other components).
</verification>

<success_criteria>
- Floating tooltip fully replaced by a fixed docked readout + scrub slider.
- Slider has severity tick marks (incl. inaccuracies) colored by severity, user vs opponent subtly distinguished.
- Hover (desktop) and slider (all) feed one activePly; mouse-leave reverts to the slider value; resting default is the last eval'd ply.
- z-index/overflow hover hacks removed from both files; focus ping survives mount.
- All frontend gates green.
</success_criteria>

<human_followup>
The user will visually verify on the second dev server at localhost:5174. No automated visual task in this plan. Visual points to check: ticks align under chart x-positions, readout never shifts height while scrubbing, slider thumb tracks hover, desktop chart+readout+slider fit the card envelope without growing every card, mobile layout stacks cleanly.
</human_followup>

<output>
Create `.planning/quick/260611-rqu-eval-chart-slider-docked-readout-replace/260611-rqu-SUMMARY.md` when done.
</output>
