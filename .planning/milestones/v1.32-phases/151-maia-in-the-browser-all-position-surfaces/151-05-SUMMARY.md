---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 05
subsystem: frontend / analysis-ui
tags: [recharts, react, maia, chart, radix-slider, theme]

requires:
  - phase: 151-04
    provides: "useMaiaEngine hook — UseMaiaEngineState { perElo, expectedScoreAtSelectedElo, wdl, isReady, isAnalyzing }; MoveCurvePoint { elo, moveProbabilities: Record<san, number> }; MAIA_ELO_LADDER"
provides:
  - "EvalBar whiteFraction?/testId? props — one shared bar component for both the Stockfish and Maia expected-score bars"
  - "MovesByRatingChart component + capMovesByPeak helper — Recharts 'Moves by Rating' chart"
  - "EloSelector component — ladder-bounded interactive ELO control"
  - "MOVES_BY_RATING_* theme.ts color constants"
affects:
  - 151-06 (mounts EvalBar with whiteFraction, MovesByRatingChart, and EloSelector into the analysis layout; VALID-01 real-ONNX cross-check will exercise these against live inference)

tech-stack:
  added: []
  patterns:
    - "One component, two data sources: EvalBar's whiteFraction override bypasses the centipawn sigmoid entirely rather than forking a second bar component (D-04/D-05)"
    - "Cap-then-pivot: MovesByRatingChart's cap helper (capMovesByPeak) operates on the raw MoveCurvePoint[] before pivoting to Recharts row data, kept as a standalone exported pure function for direct unit testing (mirrors EndgameClockDiffOverTimeChart's exported computeYDomain precedent)"
    - "Ladder-driven bounds: EloSelector derives min/max/step from its ladder prop (default MAIA_ELO_LADDER) rather than hard-coding 1100-2000, so a future ELO-ladder contract revision needs no component change"

key-files:
  created:
    - frontend/src/components/analysis/MovesByRatingChart.tsx
    - frontend/src/components/analysis/__tests__/MovesByRatingChart.test.tsx
    - frontend/src/components/analysis/EloSelector.tsx
    - frontend/src/components/analysis/__tests__/EloSelector.test.tsx
  modified:
    - frontend/src/components/analysis/EvalBar.tsx
    - frontend/src/components/analysis/__tests__/EvalBar.test.tsx
    - frontend/src/lib/theme.ts

decisions:
  - "EvalBar's whiteFraction override clamps to 0..1 and completely bypasses evalCp/evalMate/depth — no partial blending between the two eval sources, keeping the two callers (Stockfish bar, Maia bar) unambiguous about which value drove the fill"
  - "MovesByRatingChart's custom ChartTooltip content is a factory function (movesTooltipContent(playedSan, bestSan)) rather than a separately-typed component, mirroring ScoreChart.tsx's inline-lambda content prop convention — avoids a recharts generic-variance TS error that a separately-typed TooltipContentProps<number,string> component hit"
  - "MOVES_BY_RATING_PLAYED_LINE reuses SEV_MISTAKE (warm) and MOVES_BY_RATING_BEST_LINE reuses WDL_WIN (green) rather than inventing new hues — keeps the played/best semantic consistent with existing severity/WDL color language elsewhere in the app"
  - "EloSelector uses a single-thumb Slider (Radix, shadcn wrapper) rather than a native <select> — snaps naturally to the ladder's fixed step via the Slider's min/max/step props, and matches the existing PresetRangeFilter/TacticDepthFilter Slider convention already in the codebase"

requirements-completed: [SURF-01, SURF-02, SURF-03]  # SURF-04 is shared with Plan 06 — only partially delivered here (see Deviations)

coverage:
  - id: D1
    description: "EvalBar: optional whiteFraction override (clamped 0..1) bypasses evalCp/evalMate/depth entirely; optional testId (default analysis-eval-bar) lets a second bar instance coexist; aria-label reads 'Maia expected score: NN%' when override-driven — the MECHANISM half of SURF-04; Plan 06 still must mount both bars LEFT/RIGHT on the analysis board"
    requirement: "SURF-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/EvalBar.test.tsx (14 tests: 8 pre-existing + 6 new whiteFraction/testId cases)"
        status: pass
    human_judgment: true
    rationale: "SURF-04's full text requires both bars actually rendered LEFT/RIGHT of the board for all positions — that mounting is Plan 06's job (its own frontmatter lists SURF-04 again). This plan only proves the shared whiteFraction/testId mechanism works; the requirement is not fully closable from unit tests until Plan 06 ships."
  - id: D2
    description: "MovesByRatingChart: Recharts LineChart pivoting useMaiaEngine's perElo into one Line per shown SAN, capMovesByPeak (top-N-by-peak union {played,best}), 'you are here' ReferenceLine at selectedElo with a testid-bearing label, custom per-ELO tooltip, played/best emphasized via thicker stroke + theme accent, other lines cycling a muted palette"
    requirement: "SURF-01, SURF-02, SURF-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/MovesByRatingChart.test.tsx (7 tests: cap-helper membership/count/dedup/null-safety, container testid, rendered line count, you-are-here label text, empty-state placeholder)"
        status: pass
    human_judgment: false
  - id: D3
    description: "EloSelector: single-thumb Slider snapped to a ladder prop (default MAIA_ELO_LADDER), bounds/step derived from the ladder (not hard-coded), data-testid + aria-label, fires onChange with the new ladder ELO on interaction"
    requirement: "SURF-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/EloSelector.test.tsx (7 tests: current-value render, testid/aria-label, ladder-derived bounds custom + default, ArrowRight/ArrowLeft/Home keyboard interaction)"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-05
status: complete
---

# Phase 151 Plan 05: Maia Presentational Surfaces (EvalBar override, MovesByRatingChart, EloSelector) Summary

**Extended EvalBar with a whiteFraction override for the Maia expected-score bar, ported spike 006's "Moves by Rating" chart to an idiomatic Recharts component with the top-N∪{played,best} cap and a "you are here" reference line, and built a ladder-bounded EloSelector — all three standalone-tested, ready for Plan 06 to mount.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-05
- **Tasks:** 3 (all auto)
- **Files modified:** 7 (2 new components + 2 new test files + EvalBar + its test + theme.ts)

## Accomplishments

- `EvalBar.tsx`: added an optional `whiteFraction` prop that bypasses the centipawn sigmoid entirely (clamped 0..1) and an optional `testId` (default `analysis-eval-bar`) — one component now serves both the Stockfish bar and the Maia expected-score bar, sharing the exact same flip/testid contract (SURF-04, D-04/D-05). aria-label switches to "Maia expected score: NN%" only when the override drives the bar.
- `MovesByRatingChart.tsx`: idiomatic Recharts `<LineChart>` port of spike 006's hand-rolled SVG — pivots `useMaiaEngine`'s `perElo` into per-ELO row data, one `<Line>` per shown SAN, the `capMovesByPeak` cap rule (top-N-by-peak, always unioned with `{playedSan, bestSan}`, exported for direct unit testing), a `<ReferenceLine>` "you are here" marker at `selectedElo`, and a custom `ChartTooltip` body listing every shown move's probability at the hovered ELO. Played/best lines render thicker with distinct theme accents; other shown lines cycle a muted palette. Renders a minimal testid-bearing placeholder while `perElo` is `[]` (Maia not yet ready).
- `EloSelector.tsx`: a single-thumb Radix `Slider` bounded by a `ladder` prop (defaults to `MAIA_ELO_LADDER`) — bounds and step derive from the ladder array rather than any hard-coded 1100-2000 range, so a future ladder-contract revision needs no component change.
- `theme.ts`: added `MOVES_BY_RATING_PLAYED_LINE`, `MOVES_BY_RATING_BEST_LINE`, `MOVES_BY_RATING_OTHER_LINES`, `MOVES_BY_RATING_REFERENCE_LINE` — no inline oklch/hex in the chart component.

## Task Commits

1. **Task 1: Extend EvalBar with a whiteFraction override** - `b2c83a8f` (feat)
2. **Task 2: MovesByRatingChart — Recharts port of spike 006** - `c65287f2` (feat)
3. **Task 3: EloSelector — interactive ELO control** - `d8af0fa7` (feat)

## Files Created/Modified

- `frontend/src/components/analysis/EvalBar.tsx` - added `whiteFraction?`/`testId?` props; `computeWhiteFraction` short-circuits on the override
- `frontend/src/components/analysis/__tests__/EvalBar.test.tsx` - 6 new tests covering the override, clamping, flipped orientation, aria-label, distinct testId
- `frontend/src/components/analysis/MovesByRatingChart.tsx` - the chart component + `capMovesByPeak` cap helper
- `frontend/src/components/analysis/__tests__/MovesByRatingChart.test.tsx` - cap-helper + rendered-DOM tests
- `frontend/src/components/analysis/EloSelector.tsx` - the ELO control
- `frontend/src/components/analysis/__tests__/EloSelector.test.tsx` - interaction + bounds tests
- `frontend/src/lib/theme.ts` - `MOVES_BY_RATING_*` color constants

## Component Contracts for Plan 06

```typescript
// EvalBar — extended, backward-compatible (existing Stockfish callers unchanged)
interface EvalBarProps {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
  flipped?: boolean;
  className?: string;
  whiteFraction?: number;   // NEW — overrides the fill directly (0..1), bypasses evalCp/evalMate/depth
  testId?: string;          // NEW — defaults to 'analysis-eval-bar'; Plan 06's Maia bar should pass 'analysis-maia-eval-bar'
}
// Plan 06 usage: <EvalBar evalCp={null} evalMate={null} depth={0}
//                  whiteFraction={expectedScoreAtSelectedElo ?? 0.5}
//                  flipped={boardFlipped} testId="analysis-maia-eval-bar" />

// MovesByRatingChart — new
interface MovesByRatingChartProps {
  perElo: MoveCurvePoint[];   // useMaiaEngine's perElo verbatim
  playedSan: string | null;
  bestSan: string | null;
  selectedElo: number;        // EloSelector's current value
}
export function capMovesByPeak(
  perElo: MoveCurvePoint[], playedSan: string | null, bestSan: string | null, topN?: number,
): string[]; // exported for tests; default topN = 6

// EloSelector — new
interface EloSelectorProps {
  value: number;
  onChange: (elo: number) => void;
  ladder?: readonly number[];  // defaults to MAIA_ELO_LADDER
}
```

## Decisions Made

- EvalBar's `whiteFraction` override clamps to 0..1 and completely bypasses `evalCp`/`evalMate`/`depth` — no partial blending, so it's unambiguous which eval source drove the fill for either caller.
- `MovesByRatingChart`'s custom tooltip is a factory function (`movesTooltipContent(playedSan, bestSan)` returning the content renderer) rather than a separately `TooltipContentProps<number,string>`-typed component — the latter hit a recharts generic-variance TS2322 (`ValueType`/`NameType` defaults don't structurally match a narrowed `number`/`string` instantiation). The factory-function form (mirroring `ScoreChart.tsx`'s inline-lambda `content` prop) sidesteps the variance issue while keeping the same behavior.
- `MOVES_BY_RATING_PLAYED_LINE` reuses `SEV_MISTAKE` and `MOVES_BY_RATING_BEST_LINE` reuses `WDL_WIN` rather than inventing new hues, keeping the played/best color language consistent with the app's existing severity/WDL palette.
- `EloSelector` uses the existing shadcn/Radix `Slider` wrapper (single-thumb, `value={[elo]}`) rather than a `<select>`, matching the `PresetRangeFilter`/`TacticDepthFilter` Slider convention already established in `components/filters/`.

## Deviations from Plan

Plan execution itself required no Rule 1/2/3 auto-fixes — all three tasks landed exactly as written. One correction was needed in the state-update step:

### Auto-fixed Issues

**1. [Rule 3 - Blocking/correctness] Reverted a premature SURF-04 requirement-complete flip**
- **Found during:** State updates (after `requirements.mark-complete SURF-01 SURF-02 SURF-03 SURF-04`)
- **Issue:** This plan's frontmatter declares `requirements: [SURF-01, SURF-02, SURF-03, SURF-04]`, so the standard `requirements.mark-complete` step initially flipped `SURF-04` to `[x]` Complete in REQUIREMENTS.md. But `SURF-04` is ALSO listed in `151-06-PLAN.md`'s frontmatter (per ROADMAP.md's Wave 4 line: `SURF-04/05, MAIA-04/05/06, LIC-02, VALID-01`), which has not executed yet. SURF-04's actual text requires the Maia bar to render on the LEFT of the board and Stockfish on the RIGHT, "shown simultaneously for all positions" — an analysis-board layout fact that only exists once Plan 06 mounts both bars. This plan only built the shared `whiteFraction`/`testId` mechanism both bars will use, mirroring the exact MAIA-04 partial-delivery pattern documented in 151-03-SUMMARY.md.
- **Fix:** Reverted `SURF-04`'s checkbox to `[ ]` Pending in REQUIREMENTS.md's requirement list and its Traceability table row, both annotated with a partial-delivery note ("Plan 05 delivered the EvalBar whiteFraction/testId mechanism; Plan 06 still needs to mount both bars LEFT/RIGHT"). `requirements-completed` in this SUMMARY's frontmatter excludes SURF-04 accordingly; SURF-01/02/03 stay Complete since Plan 06's own requirement list does NOT include them (the roadmap's intent is that those three close entirely in this plan).
- **Files modified:** .planning/REQUIREMENTS.md
- **Verification:** Confirmed 151-06-PLAN.md doesn't exist yet (Wave 4 not started) and ROADMAP.md's Wave 4 line still lists SURF-04 against 151-06.
- **Committed in:** the final docs commit for this plan (state/roadmap/requirements update)

---

**Total deviations:** 1 auto-fixed (1 blocking/correctness — a requirement-tracking correction, not a code change)
**Impact on plan:** No impact on the shipped components or tests; corrects REQUIREMENTS.md's traceability accuracy only.

## Issues Encountered

- Recharts 3's `ChartTooltip content` prop is contravariant in its `ValueType`/`NameType` generics — an initial attempt to type the tooltip body against `TooltipContentProps<number, string>` produced a TS2322 (`Type '(props: TooltipContentProps<number, string>) => ...' is not assignable to type 'ContentType<ValueType, NameType>'`). Resolved by loosely typing the payload item shape inline (matching `ScoreChart.tsx`'s established pattern) instead of importing recharts' internal `TooltipContentProps` generic.
- Radix `Slider`'s internal `useSize` hook calls `ResizeObserver` even in a size-1 single-thumb configuration — `EloSelector.test.tsx` needed the same `ResizeObserverStub` global stub already used by the chart test files (not obvious from the component code alone, only surfaced when running the test).

## User Setup Required

None - no external service configuration required; these are pure presentational components with no new dependencies (Recharts, Radix Slider, and the theme module are already in the codebase).

## Next Phase Readiness

- All three components (`EvalBar` whiteFraction/testId, `MovesByRatingChart`, `EloSelector`) are standalone-tested and export the exact prop shapes documented above — Plan 06 can mount them directly against `useMaiaEngine`'s live output with no further contract changes expected.
- `npm test`, `npx tsc -b`, `npm run lint`, and `npm run knip` are all clean as of this plan's final commit.
- No blockers. Plan 06's VALID-01 real-ONNX cross-check (verifying `useMaiaEngine`'s policy-vocab reconstruction against the live model, per 151-04's "Known Limitations") is unaffected by this plan — these are pure presentation components consuming whatever `perElo`/`wdl` shape the hook produces.

---
*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Completed: 2026-07-05*

## Self-Check: PASSED
All 7 created/modified files exist on disk (EvalBar.tsx + test, MovesByRatingChart.tsx + test, EloSelector.tsx + test, theme.ts); all 3 task commits (b2c83a8f, c65287f2, d8af0fa7) present in git log.
