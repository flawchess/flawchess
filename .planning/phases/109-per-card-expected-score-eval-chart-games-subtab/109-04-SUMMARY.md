---
phase: 109-per-card-expected-score-eval-chart-games-subtab
plan: "04"
subsystem: frontend-chart
tags: [eval-chart, recharts, library, games-subtab, frontend, dual-marker]
requirements: [LIBG-10]

dependency_graph:
  requires:
    - "EVAL_CHART_* constants in theme.ts (plan 02)"
    - "EvalPoint/FlawMarker/PhaseTransitions types in library.ts (plan 02)"
    - "GameFlawCard eval_series/flaw_markers/phase_transitions fields (plan 02)"
    - "Backend eval-chart series builder (plan 01)"
    - "Integration tests (plan 03)"
  provides:
    - "EvalChart.tsx: recharts ComposedChart eval chart with dual-marker flaw dots"
    - "LibraryGameCard.tsx: three-equal-thirds desktop grid + mobile stacked chart block"
    - "109-UI-SPEC.md: amended dual-marker dot contract (filled/hollow, 6 styles, You/Opponent tooltip)"
  affects:
    - "frontend/src/components/results/LibraryGameCard.tsx (restructured layout)"
    - "frontend/src/components/library/EvalChart.tsx (new component)"

tech_stack:
  added: []
  patterns:
    - "ComposedChart with Area + invisible Line dot-overlay (EndgameClockDiffOverTimeChart pattern)"
    - "useId() gradient ID for per-instance SVG collision prevention"
    - "Custom dot render prop: filled (player) vs hollow (opponent) circles keyed on is_user"
    - "sm:grid sm:grid-cols-3 three-equal-thirds desktop card layout"
    - "Ply-keyed Map for O(1) flaw marker lookup in dot renderer and tooltip"

key_files:
  created:
    - path: "frontend/src/components/library/EvalChart.tsx"
      role: "White-perspective ES area chart with two-region shading, midline, phase lines, dual-marker dots, per-ply tooltip"
  modified:
    - path: "frontend/src/components/results/LibraryGameCard.tsx"
      role: "Three-thirds desktop grid (sm:grid-cols-3) + mobile EvalChart block; imports EvalChart"
    - path: ".planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-UI-SPEC.md"
      role: "Amended dual-marker dot contract: filled/hollow 6 styles, is_user, You/Opponent tooltip, density note, D-06 ply-0 confirmation"

decisions:
  - "Used custom dot render prop on invisible Line (stroke=none) overlay, not Scatter — recharts 3.8.1 Scatter uses area-based size not radius r (EndgameClockDiffOverTimeChart pattern)"
  - "Inaccuracy dots r=2, B/M dots r=2.5 for density management on 80-96px sparkline (D-09)"
  - "useId() per EvalChart instance prevents SVG gradient ID collisions across 20 simultaneous cards"
  - "user_color narrowed from string to 'white'|'black' union at the LibraryGameCard call site (noUncheckedIndexedAccess)"
  - "Empty <g key=...> returned from dot renderer (not null) per recharts 3.8.1 Pitfall 7"
  - "text-xs on tooltip container is the established project recharts chart-tooltip pattern (CLAUDE.md popover-surface exception)"
  - "data-testid card-col2-{gameId} added to desktop col 2 wrapper for browser automation"

metrics:
  duration: "22m"
  completed: "2026-06-07T01:51:00Z"
  tasks_completed: 3
  tasks_total: 4
  files_modified: 3
---

# Phase 109 Plan 04: EvalChart + LibraryGameCard Three-Thirds Summary

**One-liner:** White-perspective ES ComposedChart with two-region shading, dual-marker flaw dots (filled player / hollow opponent), and three-equal-thirds desktop card grid.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Amend 109-UI-SPEC.md for dual-marker scheme | `128bf50c` | `.planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-UI-SPEC.md` |
| 2 | Build EvalChart.tsx | `4a3979f2` | `frontend/src/components/library/EvalChart.tsx` |
| 3 | Restructure LibraryGameCard into three desktop thirds + mobile stack | `5536987d` | `frontend/src/components/results/LibraryGameCard.tsx` |
| 4 | Visual UAT (auto-approved in --auto mode) | — | See section below |

## What Was Built

### Task 1 — UI-SPEC Amendment (D-07/D-08/D-09)

Added a dated amendment note at the top of `109-UI-SPEC.md` recording the D-07/D-08/D-09
reconciliation. Specific changes:

- Renamed "Flaw Dots (User's Moves Only)" to "Flaw Dots (Both Players)" with a 6-style
  dot table (3 severities × player/opponent fill/stroke specification).
- Replaced the Scatter `r=3` recommendation with the custom `dot` render prop on a
  `<Line stroke="none">` overlay — recharts 3.8.1 Scatter uses area-based `size`, not `r`.
- Added `is_user: boolean` discriminator to the `FlawMarker` interface block.
- Updated Tooltip Contract: severity line now qualified "You · {Severity}" /
  "Opponent · {Severity}" (D-08); inaccuracy markers show severity+eval only, no tags (D-03).
- Changed Recharts architecture from `AreaChart` to `ComposedChart`.
- Added D-09 density-tuning note: r=2 inaccuracy, r=2.5 B/M, hollow strokeWidth=1.5.
- Confirmed D-06: no ply-0 `ReferenceLine`, at most two phase-transition lines.

### Task 2 — EvalChart.tsx

New component `frontend/src/components/library/EvalChart.tsx` (270 lines). Key implementation:

**Gradient:** `<linearGradient>` with a hard 50% stop — `EVAL_CHART_AREA_WHITE_AHEAD` for
0%-50% (light grey, White-ahead region), `EVAL_CHART_AREA_BLACK_AHEAD` for 50%-100%
(dark grey, Black-ahead region). The Area fills from the ES line down to y=0, so the
gradient creates the visual two-region shading as the line moves around the midline.

**ComposedChart structure:**
- `<XAxis dataKey="ply" hide />` + `<YAxis hide domain={[0, 1]} />`
- `<Area type="monotone" dataKey="es">` with gradient fill, `isAnimationActive={false}`,
  `connectNulls={false}` (breaks line at null eval plies)
- `<ReferenceLine y={0.5}>` dashed midline (`EVAL_CHART_MIDLINE`)
- Up to two `<ReferenceLine x={...}>` for middlegame/endgame phase transitions
  (`EVAL_CHART_PHASE_LINE`); no ply-0 line per D-06
- `<Line stroke="none" dot={customDotRenderer}>` overlay for flaw markers

**Dual-marker dot renderer** (`buildDotRenderer`): builds a ply-keyed `Map` for O(1) lookup.
Renders filled `<circle fill={color}>` for `is_user=true`, hollow `<circle fill="none"
stroke={color} strokeWidth={1.5}>` for `is_user=false`. Returns empty `<g>` (not null)
for non-flaw plies. Radius: 2 for inaccuracy, 2.5 for B/M (D-09 density tuning).

**Tooltip** (`buildTooltipContent`): Ply N · eval string (pawns or "Mate in #N (Side)").
For B/M markers: "You · Blunder" or "Opponent · Mistake" in severity color, plus
comma-joined tags when non-empty. Inaccuracy markers: severity+eval only, no tags (D-03).
Container uses project-standard `text-xs` chart tooltip classes (CLAUDE.md popover-surface
exception, same as all existing recharts tooltip surfaces in the project).

**ARIA/testid:** wrapping `<div role="img" aria-label="Expected score chart for game {gameId}"
data-testid="eval-chart-{gameId}">`.

**Color discipline:** all colors imported from `theme.ts` — no inline hex or oklch literals.

### Task 3 — LibraryGameCard Restructuring

**Desktop body:** Changed container from `hidden sm:flex gap-3 items-start` (two-column flex)
to `hidden sm:grid sm:grid-cols-3 sm:gap-3 sm:items-start` (three equal CSS grid columns).

- Col 1: existing mini board + `openingLine` + `desktopMetadata` in a `flex gap-3` sub-container
- Col 2: `EvalChart` when `analysis_state === 'analyzed'` AND all three eval fields are
  present; `NoAnalysisState` pill otherwise (unanalyzed cards or analyzed with missing data)
- Col 3: `flawContent` (dropped dashed left border — grid layout provides separation)

`data-testid="card-col2-{game.game_id}"` on the col 2 wrapper for browser automation.

**Mobile body:** Added a full-width `EvalChart` block (with `heightClass="h-20"`) between the
board+info row and the flaw content block. Guarded by the same analysis gate as desktop col 2.
Unanalyzed cards show no chart on mobile (the `flawContent` renders `NoAnalysisState` pill
as before).

**Type narrowing:** `game.user_color as 'white' | 'black'` before passing to EvalChart —
`GameFlawCard.user_color` is `string`; the prop requires the literal union.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The custom dot render prop approach was already
the primary recommendation in `109-PATTERNS.md` (not a deviation); Scatter was the
"fall back" that was never attempted.

## Visual UAT — NOT yet human-verified

**Auto-approved in `--auto` mode.** All automated gates passed (see Automated Gate Results
section), but the visual UAT below requires human browser verification.

A human must open the app at /library → Games subtab and verify:

| Check | Description | Status |
|-------|-------------|--------|
| (a) Desktop three-thirds layout | Analyzed card shows three equal columns: miniboard+info / eval chart / tags on desktop (sm+) | **Pending human UAT** |
| (b) Unanalyzed card col 2 | Unanalyzed card shows NoAnalysisState pill in col 2 with no layout shift | **Pending human UAT** |
| (c) Mobile stacking (375px) | Board+info block / full-width chart / tags stack vertically on mobile; chart is shorter (h-20) | **Pending human UAT** |
| (d) Area shading + midline | Light-grey region above 0.5 midline, dark-grey below; dashed midline visible | **Pending human UAT** |
| (e) Phase lines | At most two vertical phase lines (middlegame, endgame); no line at ply 0 (leftmost edge) | **Pending human UAT** |
| (f) Dual-marker dots | Filled circles for your flaws, hollow (outline-only) for opponent's; colored by severity (blunder red, mistake orange, inaccuracy yellow) | **Pending human UAT** |
| (g) Dot legibility (D-09) | Dot density on compact 80-96px sparkline is acceptable; inaccuracy dots smaller (r=2) than B/M (r=2.5) | **Pending human UAT** |
| (h) Tooltips on hover/tap | Ply N + eval in pawns or "Mate in #N (Side)"; B/M dots show "You · Blunder" / "Opponent · Mistake" + tags; inaccuracy shows severity+eval only | **Pending human UAT** |

If any of these checks fail, the issues to fix are:
- Layout shift: adjust col 2 min-height or center alignment
- Dot density: reduce inaccuracy radius to 1.5 or lower opacity
- Hollow dots invisible: check fill="none" is not overridden by chart defaults
- Tooltip missing tags: verify backend is populating tags in flaw_markers

## Automated Gate Results

All gates run after Task 3 (and re-verified before SUMMARY):

```
cd frontend && npm run lint        # PASSED — ESLint clean
cd frontend && npx tsc --noEmit    # PASSED — zero type errors
cd frontend && npm test -- --run   # PASSED — 825 tests, 71 test files
cd frontend && npm run knip        # PASSED — no unused exports
```

EvalChart is imported by LibraryGameCard, so knip reports no dead export.

## Known Stubs

None. The EvalChart component renders real `eval_series`/`flaw_markers`/`phase_transitions`
data from the backend (delivered by plan 01/03). The plan 02 types are already wired.
Unanalyzed cards render the existing `NoAnalysisState` pill, which is not a stub — it is
intentional behavior for games without engine analysis.

## Threat Flags

No new trust-boundary surfaces. Per the plan's threat model:
- T-109-05 (Information Disclosure): The chart renders only the authenticated user's own
  game data; server enforces user scoping in plan 01. No cross-user data reaches the component.
- T-109-06 (Tampering/XSS): Tags and severities are a fixed server-side Literal set rendered
  as React text nodes (auto-escaped). No `dangerouslySetInnerHTML`, no user free-text.

No additional surfaces found during implementation.

## Self-Check: PASSED

- `frontend/src/components/library/EvalChart.tsx` exists with ComposedChart: FOUND
- `frontend/src/components/results/LibraryGameCard.tsx` contains EvalChart and sm:grid sm:grid-cols-3: FOUND
- `.planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-UI-SPEC.md` contains hollow, is_user, Opponent: FOUND
- Commit `128bf50c` exists (UI-SPEC amendment): FOUND
- Commit `4a3979f2` exists (EvalChart.tsx): FOUND
- Commit `5536987d` exists (LibraryGameCard restructure): FOUND
