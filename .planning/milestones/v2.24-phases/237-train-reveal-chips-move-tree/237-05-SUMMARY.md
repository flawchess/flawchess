---
phase: 237-train-reveal-chips-move-tree
plan: 05
subsystem: ui
tags: [react, train, chips, move-tree, reveal, walkthrough, tests]
status: complete

requires:
  - phase: 237-02 (chip model + useTrainRevealTree)
    provides: "buildChipGroups, ChipGroup, GameMoveLineState, useTrainRevealTree (selectChip, activeChip, stepInfo, listView, goToRoot, currentPathUcis)"
  - phase: 237-03 (dim, never hide)
    provides: "buildChipFocusOverlay(overlay, activeUcis)"
  - phase: 237-04 (chips row + move list components)
    provides: "TrainLineChips, TrainMoveTreeList"
provides:
  - "TrainReveal mounts TrainLineChips + a treeList slot in place of the three line cards; props chips/activeChip/onChipSelect/treeList/onGameMoveLineStateChange"
  - "TrainSolveScreen builds chips once, drives useTrainRevealTree, resolveRevealBoardOverlay (free play / step overlay / off-line / chip-focus root), handleChipSelect, gameMoveLineState"
  - "useTrainWalkthrough notifyChipSelect / notifyTreeStep, WALKTHROUGH_STEP_CHIPS / WALKTHROUGH_STEP_TREE; scroll targets train-line-chips"
  - "revealTestUtils.waitForReveal()"
affects: [237-06, 237-07, 237-08, 237-09, 237-11]

tech-stack:
  added: []
  patterns:
    - "Board owner builds chips once and hands them to both the tree hook and the presentational reveal"
    - "Walkthrough hook declared after the tree (it reads isBoardDeparted); the tree's step callback reaches it through a ref filled in an effect"
    - "Search-state reporting without a parent reset: the child's cleanup reports idle, so a restored reveal's synchronous loading report is never wiped"

key-files:
  created:
    - frontend/src/components/train/__tests__/revealTestUtils.ts
  modified:
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  deleted:
    - frontend/src/components/train/TrainLineStepper.tsx
    - frontend/src/components/train/__tests__/TrainLineStepper.test.tsx
    - frontend/src/components/icons/ArrowGlyphIcon.tsx

key-decisions:
  - "gameMoveLineState is NOT reset in the per-puzzle effect (the plan said to): TrainReveal reports loading synchronously from its own effect, which runs before the parent's on the same commit for a restored reveal, so a reset would wipe it and leave the game chip loading forever. The search's own cleanup reports idle."
  - "The board follows revealTree.fen in the same render the verdict lands; the old setBoardFen(puzzle.fen) effect is kept only for the first free-play drop's boardFen use"
  - "Keyboard navigation (navContainerRef) is not wired here, the plan's hook call omits it; free play still owns piece drops until plan 06"
  - "handleChipSelect calls selectChip then notifyChipSelect; the tree hook's own onChipSelect option is left for plan 09's telemetry"

patterns-established:
  - "tapListMove(index) test helper: taps the nth variation-node token inside train-move-tree"
  - "Mutation proof: no-op selectChip and an always-jump selectChip each turned the tracer / D-01 own-line test red"

requirements-completed: [D-01, D-02, D-03]

duration: 22 min
completed: 2026-10-09
actuals:
  tokens: 12750
  tasks: 3
  commits: 3
plan_head_before: 69580e320adad5b46f472647336d4765c23b6c39
plan_head_after: 27497d7b9af0deed9d57d935c5c7125df674a413
commits: 3

coverage:
  - id: D1
    description: "On the real reveal a chip tap lights its arrow at the puzzle position (others dimmed, never hidden) and a tap on a list move steps the board with the single blue next-move arrow"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#tracer: tapping the Best chip lights its arrow at the puzzle position and a list tap steps the line"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-01: a chip tap while stepped into another line returns the board to the puzzle position with that chip lit; tapping the chip whose own line is on the board does not move it"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#D-01: tapping a chip while stepped into another line returns the board to the puzzle position"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#D-01: tapping the chip whose own line is on the board does not move the board"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-02: coinciding roles render as ONE chip (You = Best), one lit arrow; the reveal opens with You lit and Best/Game/Also fine dimmed"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#D-02: playing the best move shows ONE chip labelled \"You = Best\" and one lit arrow"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#the reveal opens with You lit"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 236 D-14/D-15 states survive as chip states: loading spinner then fill, failed shows SAN with no eval, standalone game chip loads then fills, SAN-only game move is a non-interactive chip"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx (instant-path chip tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#a game move with a SAN but no UCI renders a non-interactive game chip"
        status: pass
    human_judgment: false
  - id: D5
    description: "Card-era code removed (TrainLineStepper, ArrowGlyphIcon, trainGlyphColor, spotlight/hover/tap-away, cards-total); walkthrough follows chips and list steps"
    verification:
      - kind: command
        ref: "npm run lint && npm run build && npm run knip && npm test -- --run (319 files, 5347 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The chips row + list layout under the guess card, the walkthrough copy ('Tap a card') and the phone scroll target look right on real devices"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 05: Chips and One Move Tree on the Reveal Summary

**The Train reveal now shows a You / Best / Game chips row and one numbered move list over a single `useTrainRevealTree` tree: a chip tap jumps the board to the puzzle position with that arrow lit and the rest dimmed (D-01), coinciding roles merge into one chip (D-02), a list tap steps the line with the existing step overlay (D-03), and the three line cards, `TrainLineStepper`, the arrow-glyph legend and the card spotlight/hover/tap-away machinery are gone.**

## Performance

- **Duration:** 22 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 1 created, 9 modified, 3 deleted (frontend only; net -2,409 lines)

## Accomplishments

- `TrainReveal` is presentational about chips: it renders `TrainLineChips` and a `treeList` slot (only when chips exist), reports every state of the game-move search through `onGameMoveLineStateChange` (idle on cleanup), and keeps the reveal GET, game footer, exploration panel and the Your-call card (label, score chip, prose, Also fine SAN list, motif) without handlers.
- `TrainSolveScreen` builds `chips` once (empty until the verdict, T-237-07), seeds `useTrainRevealTree`, follows `revealTree.fen` after the verdict, and resolves the board overlay in one module-level `resolveRevealBoardOverlay` (free play, stepped line, off-line, or the root with `buildChipFocusOverlay` on the focused chip).
- `useTrainWalkthrough` lost the spotlight/line-step wrappers; `notifyChipSelect` / `notifyTreeStep` advance the same two steps, and the phone scroll targets the chips row.
- Deleted `TrainLineStepper` (+ test), `ArrowGlyphIcon` and `trainGlyphColor` (+ its trainArrows cases); knip clean without ignores.
- Tests ported: TrainReveal (presentational chips/slot/search-state coverage), TrainSolveScreen (tracer, D-01 jump and own-line, D-02, chip focus, Phase 236 chip states, walkthrough on chips, telemetry via list taps), restoredGameArrow and solveLoop.

## Task Commits

1. **Task 1 (tracer): chips row and one move tree on the real reveal** - `e9c97cca7` (feat)
2. **Task 2: remove the card-era stepper, arrow glyph and glyph color helper** - `acf5bc001` (refactor)
3. **Task 3: port the reveal tests off the card structure** - `27497d7b9` (test)

Tracer gate: the `<verify>` set (tracer test, `npm run build`) passed after Task 1 and was re-run before expansion.

## Verification

- `npm run lint`, `npm run build`, `npm run knip` clean; full frontend suite 319 files, 5347 tests pass.
- Acceptance greps: no `train-line-box-` / `train-line-stepper` in the four test files or `TrainReveal.tsx`; `trainGlyphColor` has no non-comment hit; `TrainLineStepper` appears only in three comments and the pre-existing TrainBotBubble negative test.
- Mutation proof: a no-op `selectChip` turned the tracer red; an always-jump `selectChip` turned the D-01 own-line test red; both restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] gameMoveLineState is not reset in the per-puzzle effect**
- **Found during:** Task 1 design
- **Issue:** The plan said to reset it to idle there. TrainReveal reports `loading` synchronously from its own effect, which runs before the parent's puzzle effect on the same commit for a restored reveal (reveal query cached), so the reset would erase the search state and leave the standalone game chip loading forever (the same class of bug the existing `gameMoveUci` comment documents).
- **Fix:** No reset; the search's cleanup reports `{ status: 'idle' }` on every re-dispatch, puzzle change and unmount. Documented at the state declaration.
- **Files modified:** frontend/src/components/train/TrainSolveScreen.tsx
- **Commit:** e9c97cca7

**2. [Rule 3 - Blocking] Task 2 items landed inside the Task 1 commit**
- **Issue:** Removing `TrainRevealStep` and the card props from `TrainReveal` forced the `useTrainWalkthrough` rewrite and the TrainReveal card-code deletion into Task 1 to keep `tsc -b` green. Task 2 then removed the remaining dead files and `trainGlyphColor`.
- **Commit:** e9c97cca7, acf5bc001

**3. [Rule 3 - Blocking] jsdom `scrollIntoView` stub in test files**
- **Issue:** `HorizontalMoveList` (inside the mounted move list) calls `scrollIntoView`, which jsdom lacks; the reveal screen tests crashed on first render of a list. Added the file-local `Element.prototype.scrollIntoView = vi.fn()` guard (the convention in Analysis/Bots/Openings tests) to TrainSolveScreen.test and restoredGameArrow.test.
- **Commit:** e9c97cca7, 27497d7b9

**4. [Rule 1 - Bug (test)] "board holds the played-move position through grading" read a one-render window**
- **Issue:** The board now snaps to the puzzle position in the same render the verdict lands (it follows the tree), so the old assertion, which only passed in the one-render gap before the snap effect, failed. The behavior is intentional and unchanged for users.
- **Fix:** The test holds the played-position search with `HeldPositionWorker`, asserts the played position while grading, releases, then asserts the snap.
- **Commit:** 27497d7b9

### Notes

- Chips + list render below the Your-call card (inside the exploration ternary, where the line boxes were), not above it where the Your-move box used to sit; plan 08 restructures the card anyway.
- Keyboard navigation (`navContainerRef`) is deliberately not passed to the tree yet (the plan's call omits it); free play still handles piece drops and `useBoardNavigationInput` stays inert.
- `onCardEngage` / `onCardsTotalChange` stay on the telemetry hook but are no longer fed; plan 09 switches the payload to the v2 chips counters. List taps still count as line steps via `onLineUserStep`.
- Walkthrough copy ("Tap a card", "arrows inside a card") is unchanged; copy edits are outside this plan.

**Total deviations:** 4 auto-fixed (2 Rule 1, 2 Rule 3). **Impact:** no scope change.

## Known Stubs

None.

## Threat Flags

None. T-237-07 holds: `chips` is `[]` while `verdict === null`, the tree hook's `active` is `verdict !== null`, and the reveal GET and game-move search keep their existing `verdict !== null` gates; the "arrows prop is empty before the verdict" test is unchanged and green.

## Next Phase Readiness

Plan 06 can fold piece drops into the tree (`playMove`, `onUserMove`) and delete the free-play mode and `TrainExplorationPanel`; plan 07 replaces Solution with the action bar's rewind (`revealTree.goToRoot` is already what `handleShowSolution` calls); plan 08 restructures the Your-call card into the verdict strip; plan 09 feeds the tree's `onUserMove` / `onChipSelect` into the v2 telemetry and passes `snapshot()` / `restored` through the reveal cache. Plan 11's browser UAT owns the real-device layout check (D6 above, pending).

## Self-Check: PASSED

- FOUND: frontend/src/components/train/__tests__/revealTestUtils.ts; `<TrainLineChips` in TrainReveal.tsx; `useTrainRevealTree(`, `buildChipGroups(`, `function resolveRevealBoardOverlay`, `<TrainMoveTreeList` in TrainSolveScreen.tsx; `notifyChipSelect` / `notifyTreeStep` in useTrainWalkthrough.ts
- GONE: TrainLineStepper.tsx, ArrowGlyphIcon.tsx
- FOUND commits: e9c97cca7, acf5bc001, 27497d7b9
