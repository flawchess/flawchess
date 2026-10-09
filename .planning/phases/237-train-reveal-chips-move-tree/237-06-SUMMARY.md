---
phase: 237-train-reveal-chips-move-tree
plan: 06
subsystem: ui
tags: [react, train, move-tree, stockfish, grading, umami, reveal, tests]
status: complete

requires:
  - phase: 237-02 (useTrainRevealTree)
    provides: "playMove / playLine / selectChip / goToRoot, onUserMove {source, forked}, D-04 root focus, isOffLine"
  - phase: 237-04 (TrainMoveTreeList)
    provides: "the wrap-variant move list over the tree"
  - phase: 237-05 (chips + one tree on the reveal)
    provides: "resolveRevealBoardOverlay, handleChipSelect, the inert Your-call card"
provides:
  - "useTreeMoveGrading: per-FEN eval cache + sideline grading lifted from useTrainFreePlay (D-06 root vetted shortcut verbatim)"
  - "useTrainRevealTree owns the ONE reveal Stockfish engine: pvLines, isAnalyzing, evalReading, moveListMarkers, boardMarkers, lastMoveColor; options seedEval, engineEnabled"
  - "TrainMoveTreeList Stockfish row (train-sf-row, btn-train-sf-row-toggle) off the known lines"
  - "post-verdict drops fork a sideline in place; first fork fires 'train-sideline-fork'; 'train-explore-exit' retired"
affects: [237-07, 237-08, 237-09, 237-11]

tech-stack:
  added: []
  patterns:
    - "One engine follows the shown node; the grader reads it through a staleness-guarded live reading"
    - "Per-node quality state keyed to the tree (resetKey) so a restarted node-id space never inherits stale badges"
    - "Stockfish row is a sibling of the list's testid wrapper so list token queries never see engine moves"

key-files:
  created:
    - frontend/src/hooks/useTreeMoveGrading.ts
  modified:
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
    - frontend/src/components/train/TrainMoveTreeList.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/__tests__/TrainMoveTreeList.test.tsx
    - frontend/src/lib/analytics.ts
  deleted:
    - frontend/src/hooks/useTrainFreePlay.ts
    - frontend/src/hooks/__tests__/useTrainFreePlay.test.ts

key-decisions:
  - "The grading engine's seed stays the parent eval of a root fork: the reveal engine now also searches the puzzle position (the eval bar needs it), so the live-capture effect skips the start FEN while a seed exists. Without this the engine's shallow root reading overwrote the seed's best move and eval, breaking the D-06 'engine best still wins' and terminal cases (caught by the ported hook tests, proven by mutation)."
  - "Per-node quality state is keyed to the tree (resetKey = puzzle fen while active): loadMainLine restarts node ids at 0, the old hook cleared qualityByNode by hand in start/reset."
  - "useTreeMoveGrading takes startFen only (no separate rootFen): they are the same value."
  - "TrainMoveTreeList drops its optional markers prop and reads tree.moveListMarkers."
  - "TRAIN_REVEAL_ONLINE_MULTIPV stays module-private (knip: nothing else needs it); the two row-length constants are exported."

patterns-established:
  - "startSideline() / startSidelineWithProbe() test helpers: verdict landed, then a d2d4 fork (no known line carries it) and the Stockfish row visible"
  - "RecordingFakeWorker: per-Worker message log to prove which engines were (not) asked to search"

requirements-completed: [D-03, D-04, D-13, D-14]

duration: 22 min
completed: 2026-10-09
actuals:
  tokens: 54700
  tasks: 3
  commits: 3
plan_head_before: 7de3d72eae12b6fe3b4683441b8a901ec1fc0269
plan_head_after: 6293afd2d1a79add0239de69ae3407cdc55670e0
commits: 3

coverage:
  - id: C1
    description: "A piece moved after the verdict forks a sideline in place on the one tree (close x listed, Stockfish row present); further drops extend it; solvePuzzle runs once"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a post-verdict drop forks a sideline in place on the one tree"
        status: pass
    human_judgment: false
  - id: C2
    description: "SOLV-02: two post-verdict forks never reach grading or the solve POST (solvePuzzle once, the grading Worker is asked for no further search, still exactly two Workers)"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#SOLV-02: two post-verdict forks never reach grading or the solve POST"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#exactly two Workers exist once the verdict lands"
        status: pass
    human_judgment: false
  - id: C3
    description: "Sideline grading keeps its marks incl. Phase 211 D-06 (root vetted key, engine best wins, terminal wins, deeper ply from the engine); proven by reverting the shortcut and the seed guard"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree: root-ply grading reads the served vetted key (D-06)"
        status: pass
    human_judgment: false
  - id: C4
    description: "One reveal engine: MultiPV 1 on the known lines, max(2, arrows) off them, off while engineEnabled is false, staleness-guarded reading feeds the eval bar on every node"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainRevealTree.test.ts#useTrainRevealTree: the one reveal engine"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#on a sideline the bar reads the one reveal engine"
        status: pass
    human_judgment: false
  - id: C5
    description: "D-04 deselect and D-13 counting; D-14 first-fork event fires once from the handler (never on mount/restore), the sideline x keeps board-tool line-delete, train-explore-exit is gone"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#sideline feature events (D-14)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#D-04: a hand-played move that matches a line lights that chip"
        status: pass
    human_judgment: false
  - id: C6
    description: "Full gate: lint, tsc -b build, full vitest suite (318 files, 5349 tests), knip clean"
    verification:
      - kind: command
        ref: "npm run lint && npm run build && npm test -- --run && npm run knip"
        status: pass
    human_judgment: false
  - id: C7
    description: "The Stockfish row height/density and the interim phone bottom-bar controls look right on real devices"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 06: Free Play Folded Into the One Tree Summary

**A move played after the verdict now forks a sideline in place on the reveal's single move tree: one Stockfish engine follows the shown node (eval bar, a one-line Stockfish row off the known lines, board arrows, and the sideline grader), `useTrainFreePlay` and the exploration panel are deleted, the first fork per puzzle sends `train-sideline-fork`, and SOLV-02 holds (solvePuzzle once, no extra grading search).**

## Performance

- **Duration:** 22 min
- **Tasks:** 3 (1 tracer, 2 auto/tdd)
- **Files:** 1 created, 9 modified, 2 deleted (frontend only)

## Accomplishments

- `useTreeMoveGrading` lifts the free-play grading verbatim (per-FEN cache with seed and live capture, the Phase 211 D-06 root vetted shortcut and its comment, `qualityByNode`, markers); it grades only free (user-played) nodes and caches every shown position, so a fork off a stepped line position grades.
- `useTrainRevealTree` owns the one `useStockfishEngine`: MultiPV 1 on the known lines and `max(2, Stockfish arrows)` off them, off while `engineEnabled` is false (the Phase 236 instant grade pending), staleness-guarded `pvLines` / `evalReading`.
- `TrainMoveTreeList` shows `train-sf-row` off the known lines: one engine line collapsed, two expanded (`btn-train-sf-row-toggle`), a click on a move plays the whole engine line into the sideline.
- `TrainSolveScreen`: `handlePieceDrop` post-verdict branch is `if (verdict === null) return false; return revealTree.playMove(source, target)` after the unchanged guess and moveApplied guards; the eval-bar engine and `TRAIN_EVAL_BAR_MULTIPV` are gone; `resolveTrainEvalBarReading(fen, evalReading)`; the off-line overlay uses the engine arrows, grade badge and quality last-move colour; `handleShowSolution` rewinds the tree and restores orientation; the phone bottom bar publishes back/forward/rewind/flip while the board is off the root.
- `TrainReveal` lost the exploration panel and every `isExploring` / `freePlay` gate: the Your-call card, chips and list are always shown after the verdict.
- Analytics: `'train-sideline-fork'` registered, `'train-explore-exit'` removed; the first fork fires once per puzzle from the user handler (ref reset in the per-puzzle effect).
- Tests: the free-play hook cases ported into `useTrainRevealTree.test.ts` (D-06 root cases, MultiPV, onUserMove counting, fork from a stepped position), 15 red screen tests re-expressed on the tree, new SOLV-02, D-04, Stockfish-row and Umami tests.

## Task Commits

1. **Task 1 (tracer): a move played after the verdict forks a sideline in place** - `994ea9499` (feat)
2. **Task 2: retire useTrainFreePlay; grading, counting and D-06 cases live on the tree** - `d5f0c2184` (refactor)
3. **Task 3: port the free-play, eval-bar, Worker and bottom-bar tests to the in-place tree** - `6293afd2d` (test)

Tracer gate: the `<verify>` set (the "forks a sideline in place" test and `npm run build`) passed after Task 1 and was re-run before expansion.

## Verification

- `npm run lint`, `npm run build`, `npm run knip` clean; full frontend suite 318 files, 5349 tests pass.
- Mutation proof: removing the D-06 root vetted shortcut turned the two root-key cases red; removing the seed guard turned the "engine best wins" and terminal cases red; dropping the once-per-puzzle fork-event check turned the first-fork test red. All restored.
- Acceptance greps: `useTrainFreePlay` / `uciFromDrop` / `train-explore-exit` / `TrainExplorationPanel` / `train-reveal-exploration` / `makeFreePlayState` appear nowhere in `frontend/src`; `useStockfishEngine(` is in `useTrainRevealTree.ts` and not in `TrainSolveScreen.tsx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The reveal engine's root search overwrote the grading seed**
- **Found during:** Task 2 (hook test port)
- **Issue:** The old free-play engine only started after the first move, so the grading engine's seed was always the parent eval of a root fork. The one reveal engine also searches the puzzle position (the eval bar needs it), and its live-capture effect replaced the seed's cp/best move with a shallow reading, breaking the D-06 "engine best still wins" and terminal-precedence cases.
- **Fix:** The live-capture effect skips the start FEN while a seed exists (commented at the site).
- **Files modified:** frontend/src/hooks/useTreeMoveGrading.ts
- **Commit:** d5f0c2184

**2. [Rule 3 - Blocking] Per-node quality state needs a tree key**
- **Issue:** The old hook cleared `qualityByNode` by hand in `start` / `reset`. The tree now restarts node ids at 0 on a puzzle change or deactivation with no command to hang a clear on.
- **Fix:** `useTreeMoveGrading` takes `resetKey` (the puzzle fen while active, else null) and drops the map when it changes. Covered by a hook test.
- **Commit:** 994ea9499 / d5f0c2184

**3. [Rule 3 - Blocking] Minor shape departures from the plan text**
- `useTreeMoveGrading` takes `startFen` only (the plan listed `rootFen` too; they are the same value).
- `TrainMoveTreeList` drops its optional `markers` prop and reads `tree.moveListMarkers`.
- The Stockfish row is a sibling of the `train-move-tree` wrapper (inside an outer plain div), so tests and queries reading list tokens never match engine-line moves.
- `TRAIN_REVEAL_ONLINE_MULTIPV` is module-private (knip rule: no second consumer).

**4. [Rule 3 - Blocking] Task 2 pulled TrainReveal.test deletions forward**
- Deleting `useTrainFreePlay.ts` left an unresolved import in `TrainReveal.test.tsx` (knip), so the exploration-test deletions listed under Task 3 landed in the Task 2 commit. Task 3 carried the remaining screen/harness tests.

**5. [Rule 1 - Bug (test)] Several ported tests could not keep their exact moves**
- A post-verdict `e2e4` is now a known-line move (played = best = e2e4), not a fork, so the ported tests fork with `d2d4` instead, and the "badge a best move" test plays the reveal engine's own top move (`e7e5`) after the engine has searched the sideline position.

**Total deviations:** 5 auto-fixed (2 Rule 1, 3 Rule 3). **Impact:** no scope change.

### Notes

- **Interim desktop controls:** the in-card board-controls strip (back/forward/reset/flip) went with the exploration panel. Until plan 07 adds the action bar, desktop has the move-list taps, the Solution button and the chip taps, but no flip button; phones keep back/forward/rewind/flip through the published bottom bar. Keyboard navigation (`navContainerRef`) is still not passed to the tree.
- **D-04 "every arrow dimmed on the puzzle position":** `goToRoot` / stepping back onto the root restores the default You focus when no chip is focused (plan 02, RESEARCH A1, "one line to flip"), so the deselected state is observable while the board sits on the fork, not after a rewind. The overlay resolver passes `null` as the lit set whenever `activeChip` is null, so the dimmed root renders correctly if that line is flipped. Not changed here.
- **Eval bar blink:** the staleness guard on `evalReading` means the bar reads neutral for the moment between a step and the engine reaching the new position (the old eval-bar engine kept the previous reading). The plan specified the guarded reading.
- `onCardEngage` / `onCardsTotalChange` remain unfed; plan 09 switches telemetry to the v2 counters.

## Known Stubs

None.

## Threat Flags

None. T-237-09 holds (guard order kept, a test proves one `solvePuzzle` and no extra grading search); T-237-10 holds (enumerated literal in `ACTION_TARGETS`, fired from the user handler only, a restored mount sends nothing); T-237-11 holds (`engineEnabled = instantGrade?.status !== 'pending'`, covered by the existing D-16 eval-bar test).

## Next Phase Readiness

Plan 07 can replace the Solution button and the interim bottom bar with the action bar over `revealTree.goToRoot` / `goBack` / `goForward`; plan 09 can feed `handleRevealUserMove`'s `{source, forked}` into the v2 telemetry counters and pass `snapshot()` / `restored` through the reveal cache. Plan 11's browser UAT owns the row density and phone-bar check (C7 above, pending).

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useTreeMoveGrading.ts (`export function useTreeMoveGrading`, `SEED-137`); `useStockfishEngine(` in useTrainRevealTree.ts; `data-testid="train-sf-row"` in TrainMoveTreeList.tsx; `revealTree.playMove(source, target)` after the `moveApplied` guard in TrainSolveScreen.tsx; `'train-sideline-fork'` in analytics.ts
- GONE: frontend/src/hooks/useTrainFreePlay.ts and its test
- FOUND commits: 994ea9499, d5f0c2184, 6293afd2d
