---
phase: 237-train-reveal-chips-move-tree
plan: 03
subsystem: ui
tags: [react, svg, chess-board, train, arrows, opacity]
status: complete

requires:
  - phase: 200 / 260902-qf7 (Train reveal legend spotlight, pristine your/best/game set)
    provides: "applyTrainSpotlight filtering, markerOwners (WR-02), pristineOverlayUcis"
provides:
  - "BoardArrow.opacity and SquareMarker.opacity (optional; only the Train reveal sets them)"
  - "resolveArrowOpacity(arrow): hover > explicit opacity > color default, used by ArrowOverlay"
  - "TRAIN_FOCUS_ARROW_LIT/DIM_OPACITY (0.92/0.22) and TRAIN_FOCUS_BADGE_LIT/DIM_OPACITY (1/0.32) in lib/theme.ts"
  - "buildChipFocusOverlay(overlay, activeUcis): dims instead of filtering (replaces applyTrainSpotlight)"
  - "TrainSolveScreen ChessBoard test mock exposes data-arrow-opacities / data-marker-opacities"
affects: [237-04, 237-05, 237-06]

tech-stack:
  added: []
  patterns:
    - "Dim, never hide: unfocused arrows/badges stay on the board at a low opacity; the lit set is near-opaque and paints on top (onTop flipped per focus)"
    - "Optional per-item opacity on shared board types, so unrelated callers render identically"

key-files:
  created:
    - frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts
  modified:
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/boardMarkers.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/lib/trainArrows.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/board/__tests__/boardMarkers.test.tsx
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx

key-decisions:
  - "A lit arrow gets onTop: true and a dimmed one onTop: false, deliberately overriding the thin game arrow's own onTop while it is dimmed, so the focused move always paints above the faded ones"
  - "Null or empty activeUcis dims everything (D-04 groundwork) rather than returning the overlay unchanged as the old filter did"
  - "TrainSolveScreen keeps the card spotlight as the interim active set (spotlight?.ucis ?? pristine your/best/game); plan 05 re-points it at the focused chip"

patterns-established:
  - "Mutation proof: filter-instead-of-map, dropping the opacity from the SquareMarkerGroup <g>, and ignoring an explicit arrow opacity each turned their tests red"

requirements-completed: [D-04]

duration: 25 min
completed: 2026-10-09
actuals:
  tokens: 30000
  tasks: 2
  commits: 2
plan_head_before: cc888e707d1d9afd1ad0fb3ed66ad664212f765f
plan_head_after: cb03c499f32e2f5afe7a5f5d8a6624c8c79dd9e9
commits: 2

coverage:
  - id: D1
    description: "Unfocused reveal arrows and badges are drawn dimmed (arrows 0.22, badges 0.32), never hidden; the focused set is near-opaque and on top; the pristine board now also draws the vetted Also fine arrows dimmed"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx (six spotlight tests, asserting data-arrow-opacities / data-marker-opacities)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainArrows.test.ts#buildChipFocusOverlay (Phase 237)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A merged role lights both arrows (matched by squares); a badge is lit only when markerOwners says the focused move owns its square (WR-02); null/empty active set dims everything"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainArrows.test.ts#buildChipFocusOverlay (Phase 237)"
        status: pass
    human_judgment: false
  - id: D3
    description: "BoardArrow.opacity / SquareMarker.opacity render only when set; resolveArrowOpacity orders hover > explicit > color default; other board callers are unchanged"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx#SquareMarkerGroup"
        status: pass
    human_judgment: false
  - id: D4
    description: "The 0.22 / 0.32 dim levels look right on the real board (sketch 008 values, owner-approved, tunable)"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 03: Dim, Never Hide Summary

**The reveal's filter-style spotlight is now a dimming one: `buildChipFocusOverlay` keeps every arrow and badge, lights the focused move (0.92 arrows, full badges, painted on top) and fades the rest (0.22 / 0.32), wired through optional `opacity` fields on `BoardArrow` and `SquareMarker`.**

## Performance

- **Duration:** 25 min
- **Tasks:** 2 (1 tracer, 1 TDD-flagged auto)
- **Files:** 1 created, 9 modified (frontend only)

## Accomplishments

- `BoardArrow.opacity?` and `SquareMarker.opacity?`; `resolveArrowOpacity` (exported from `ChessBoard.tsx`) replaces the inline opacity expression in `ArrowOverlay`; `SquareMarkerGroup` puts `opacity` on its root `<g>` (undefined omits the attribute).
- Four `TRAIN_FOCUS_*` opacity constants in `lib/theme.ts` citing sketch 008 and the "fade to ~20-30%, never hidden" rule.
- `buildChipFocusOverlay` replaces `applyTrainSpotlight`: maps arrows to `{ opacity, onTop: lit }` (square-pair matching so a merged You = Game role lights both arrows) and markers by `markerOwners` ownership (WR-02 kept). `alsoFineMoves` and `markerOwners` pass through by reference.
- `TrainSolveScreen` calls it with the spotlit card's UCIs, else the pristine your/best/game set. Behavior change called out in the plan: the pristine board now draws the server-vetted "Also fine" arrows dimmed instead of hiding them until their card is hovered. Sharp puzzles still draw none.
- The ChessBoard mock in `TrainSolveScreen.test.tsx` exposes `data-arrow-opacities` and `data-marker-opacities`; the six named spotlight tests assert lit/dim opacities (via `TRAIN_FOCUS_*` constants, no hardcoded numbers) and unchanged arrow counts.

## Task Commits

1. **Task 1 (tracer): dim unfocused arrows and badges instead of hiding them** - `f294faa39` (feat)
2. **Task 2: pin marker opacity rendering and resolveArrowOpacity precedence** - `cb03c499f` (test)

Tracer gate: the `<verify>` set (the three TrainSolveScreen / Train.solveLoop test files, lint, build, knip) ran green end to end after the Task 1 changes; expansion to Task 2 proceeded.

## Verification

- `TrainSolveScreen.test.tsx`, `TrainSolveScreen.restoredGameArrow.test.tsx`, `Train.solveLoop.test.tsx`: 144 pass.
- `trainArrows`, `boardMarkers`, `ChessBoard.arrowOpacity`: 66 pass.
- `npm run lint`, `npm run build` (`tsc -b`), `npm run knip` clean. Full frontend suite after Task 2: 318 files, 5394 tests, all passing.
- `grep applyTrainSpotlight` over `frontend/src` finds nothing.

## Mutation proof

Each critical behavior was reverted, the targeted tests were seen failing, and the file was restored from a backup:

- `buildChipFocusOverlay` filtering arrows instead of mapping: 4 tests red (count preserved, merged pair, null and empty active set).
- `SquareMarkerGroup` `<g>` without `opacity`: the marker opacity test red.
- `resolveArrowOpacity` ignoring an explicit `opacity`: 2 tests red (explicit wins, explicit 0 honoured).

## TDD Gate Compliance

Task 2 was flagged `tdd="true"` but the plan is `type: execute` and the builder already existed from Task 1, so there is no separate failing RED commit. RED-equivalent evidence is the three mutation runs above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] trainArrows.test.ts rewritten inside the Task 1 commit**
- **Found during:** Task 1 (`npm run build`)
- **Issue:** The old `describe('applyTrainSpotlight ...')` imports the deleted function, so `tsc -b` (part of Task 1's verify) fails until that file is rewritten, although the plan lists it under Task 2.
- **Fix:** Rewrote that describe as `buildChipFocusOverlay (Phase 237)` in the Task 1 commit. Task 2 then added the `boardMarkers` and `ChessBoard.arrowOpacity` tests and the mutation proof.
- **Files modified:** frontend/src/lib/__tests__/trainArrows.test.ts
- **Commit:** f294faa39

**2. [Rule 3 - Blocking] eslint react-refresh rule on the new export**
- **Issue:** exporting `resolveArrowOpacity` (required by the plan) from `ChessBoard.tsx` trips `react-refresh/only-export-components`.
- **Fix:** `eslint-disable-next-line` with a reason, the same pattern already used in `TrainScheduleSettings.tsx` and `EndgameClockDiffOverTimeChart.tsx`.
- **Commit:** f294faa39

**3. [Doc hygiene] TrainReveal.tsx comments**
- Two doc comments in `TrainReveal.tsx` named the deleted `applyTrainSpotlight`; reworded to `buildChipFocusOverlay`. Comment-only, not in the plan's file list.
- **Commit:** f294faa39

### Notes

- Only 5 of the 6 named spotlight tests failed before the update; "a puzzle with no played-in-game move draws only the your-move and best-move arrows" already passed. It still gained a lit-opacity assertion.

## Known Stubs

None.

## Threat Flags

None. T-237-06 holds: `buildTrainRevealOverlay` still returns an empty overlay until `hasVerdict`, so dimmed "Also fine" arrows only appear after the solve POST landed (existing "returns an empty overlay when the verdict has not landed" test, plus the new "an empty overlay stays empty" case).

## Next Phase Readiness

Plan 05 can re-point `buildChipFocusOverlay`'s active set from the spotlit card to the focused chip; plan 06 can use the null/empty all-dim case for D-04. Plan 11's browser UAT owns tuning the 0.22 / 0.32 levels (D4 above, pending).

## Self-Check: PASSED

- FOUND: frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts, frontend/src/lib/trainArrows.ts (`export function buildChipFocusOverlay`), frontend/src/components/board/ChessBoard.tsx (`export function resolveArrowOpacity`), frontend/src/lib/theme.ts (`TRAIN_FOCUS_ARROW_DIM_OPACITY = 0.22`)
- FOUND commits: f294faa39, cb03c499f
