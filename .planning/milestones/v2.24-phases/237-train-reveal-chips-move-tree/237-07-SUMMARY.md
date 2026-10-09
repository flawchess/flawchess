---
phase: 237-train-reveal-chips-move-tree
plan: 07
subsystem: ui
tags: [react, train, action-bar, mobile-bottom-bar, keyboard, umami, tests]
status: complete

requires:
  - phase: 237-06 (free play folded into the one tree)
    provides: "revealTree goToRoot / goBack / goForward / canGoBack / canGoForward / isAtRoot, the interim off-root publish, useTrainRevealTree navContainerRef option"
provides:
  - "TrainRevealActionBar: rewind, back, forward, flip + Analyze + Next, one component for the phone bottom bar, the in-flow bar (sm up) and desktop (with the '← → Home' hint)"
  - "MobileBoardControls payload fields onNext / analyzeTo / onAnalyzeClick / highlight; MobileBottomBar Train branch (onNext != null) ahead of the bot-game branch"
  - "TrainSolveScreen publishes for the WHOLE reveal; handleRewind (Umami train-solution); desktop ArrowLeft / ArrowRight / Home through navContainerRef: boardRef"
affects: [237-08, 237-09, 237-10, 237-11]

tech-stack:
  added: []
  patterns:
    - "Published callbacks are ref-backed (useCallback calling through a ref refreshed by a per-render effect), so the cross-tree publish effect does not re-run every render"
    - "MobileBottomBar's three-way bar choice extracted to a module-level renderBoardControlsBar helper"

key-files:
  created:
    - frontend/src/components/train/TrainRevealActionBar.tsx
    - frontend/src/components/train/__tests__/TrainRevealActionBar.test.tsx
  modified:
    - frontend/src/lib/mobileBoardControls.ts
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "Rewind no longer resets board orientation: flip is a permanent bar control now; the per-puzzle effect still restores the solver-colour default (plan's discretion item)"
  - "The bar's Next / Analyze handlers stay plain functions in TrainSolveScreen; the payload and in-flow bar call them through refs refreshed by an effect each render, keeping the published callbacks referentially stable"
  - "The publish block sits after showResultRow (the gate is verdict !== null && showResultRow) rather than at the old interim spot, because it needs showResultRow"
  - "The walkthrough's last step passes lastControl={null}: the ringed bar IS the step's control"

patterns-established:
  - "MobileBoardControlsProbe in TrainSolveScreen.test now also exposes onNext presence, analyzeTo and highlight, and a mbc-btn-next button"

requirements-completed: [D-14]

duration: 38 min
completed: 2026-10-09
actuals:
  tokens: 30400
  tasks: 3
  commits: 2
plan_head_before: d3f0a513f6822b4c0c10fc8438331b062d627962
plan_head_after: 6792d0a15c9fc6d8b6943c174fb180c97f79c380
commits: 2

coverage:
  - id: E1
    description: "After the verdict the phone bottom bar becomes rewind, back, forward, flip + Analyze + Next for the WHOLE reveal (also at the puzzle position); null before the verdict, on unmount; the published Next leaves the reveal like the in-flow Next"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#mobileBoardControls publishing"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#a Train reveal payload renders the reveal bar: board buttons, Analyze link with its href, Next; clicking Next / Analyze calls the published callbacks"
        status: pass
    human_judgment: false
  - id: E2
    description: "The same bar renders in the page flow under the board (hidden below sm); Analyze only for an own-game puzzle; the walkthrough's last step rings it and the bar's Next stamps reveal_walkthrough exactly once"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#the last step rings the reveal action bar and leaving through its Next stamps reveal_walkthrough exactly once"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainRevealActionBar.test.tsx"
        status: pass
    human_judgment: false
  - id: E3
    description: "Desktop keyboard: ArrowRight steps into the focused chip's line, ArrowLeft returns, Home returns from deeper; inert (not even default-prevented) before the verdict. Proven by nulling navContainerRef (the test goes red)"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#desktop keyboard navigation"
        status: pass
    human_judgment: false
  - id: E4
    description: "D-14: rewind fires 'action' / 'train-solution' exactly once per press and nothing on render; flip keeps board-tool flip; Analyze tracks through the handler, never data-umami-event"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#rewind sends exactly one train-solution action per press and nothing on render (D-14)"
        status: pass
    human_judgment: false
  - id: E5
    description: "Rewind (the old Solution) returns to the puzzle position and keeps every sideline; a flip survives a rewind; the Solution button, VerdictActions, isBoardDeparted, hasSolution and WALKTHROUGH_SOLUTION_PART are gone"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a flip survives a rewind (flip is a permanent bar control now)"
        status: pass
      - kind: command
        ref: "grep -c btn-train-solution|VerdictActions|hasSolution over the screen, hook, copy and test files prints 0"
        status: pass
    human_judgment: false
  - id: E6
    description: "Full gate: lint, tsc -b build, full vitest suite (5363 tests), knip clean"
    verification:
      - kind: command
        ref: "npm run lint && npm run build && npm test -- --run && npm run knip"
        status: pass
    human_judgment: false
  - id: E7
    description: "The bar fits a 375px phone bar in one row (four icon buttons + Analyze + Next), the sm/lg in-flow placement, and the key hint look right at 390x844 / 768x1024 / 1280x800"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT (jsdom has no layout)"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 07: One Action Bar for the Whole Reveal Summary

**The reveal now has one action bar, `TrainRevealActionBar` (rewind, back, forward, flip, Analyze, Next): published to the phone bottom bar for the whole reveal, rendered in the page flow under the board from `sm` up with a "← → Home" hint, and wired to ArrowLeft / ArrowRight / Home on desktop; the Solution button and the bubble action row are gone, and rewind (which keeps sidelines) fires the kept `train-solution` Umami target.**

## Performance

- **Duration:** 38 min
- **Tasks:** 3 (1 tracer, 1 auto/tdd, 1 auto), 2 commits (see Deviations 1)
- **Files:** 2 created, 9 modified (frontend only)

## Accomplishments

- `TrainRevealActionBar`: `BoardControls flat` (keeps the `board-btn-*` testids and the `board-tool` flip event) + optional key hint + Analyze (router `Link`, analytics from `onClick`, never `data-umami-event`) + Next; `ring-2 ring-brand-brown` when `highlight`.
- `mobileBoardControls`: optional `onNext`, `analyzeTo`, `onAnalyzeClick`, `highlight` (no defaults, like `onResign`), each listed individually in the publish effect deps. `MobileBottomBar` picks the Train bar first when `onNext != null`, via a new module-level `renderBoardControlsBar` (Train / bot / `BoardControls`), so the component itself got shallower.
- `TrainSolveScreen`: `handleRewind` (= `revealTree.goToRoot()` + `trackFeature('action', { target: 'train-solution' })`), `analyzeTo`, ref-backed stable `onNext` / `onAnalyzeClick` publishing, whole-reveal publish (`verdict !== null && showResultRow`), the in-flow bar (`hidden sm:flex`, `showKeyHint`) inside the pinned block, `navContainerRef: boardRef`. Removed: `VerdictActions`, `handleShowSolution`, `isBoardDeparted`, the bubble's action row, and the orientation reset on rewind.
- Walkthrough: `hasSolution` dropped from the hook and `walkthroughCopy`; `WALKTHROUGH_SOLUTION_PART` deleted; the last step carries `lastControl={null}` and the bar rings.

## Task Commits

1. **Task 1 (tracer) + the code halves of Tasks 2 and 3:** `91dbcc0f8` (feat)
2. **Task 2/3 tests: bar unit tests, desktop keyboard, rewind event:** `6792d0a15` (test)

Tracer gate: the `<verify>` set (`-t "reveal bar|mobileBoardControls publishing"` and `npm run build`) passed after the tracer work and was re-run (full suites) before the expansion work.

## Verification

- `npm run lint`, `npm run build`, `npm run knip` clean; full frontend suite 5363 tests pass.
- Mutation proof: passing `navContainerRef: null` turned the keyboard walk test red; restored.
- Acceptance greps: `data-testid="train-reveal-action-bar"`, `onNext?: () => void`, `analyzeTo?: string | null`, `onNext != null`, `navContainerRef: boardRef`, `target: 'train-solution'` (inside `handleRewind`) all match; `btn-train-solution`, `VerdictActions` and `hasSolution` print 0 in the screen, hook, copy and test files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The Task 2 and Task 3 code halves landed in the Task 1 commit**
- **Issue:** Removing the bubble action row and `isBoardDeparted` from `TrainSolveScreen` forced `useTrainWalkthrough` / `walkthroughCopy` to stop taking `hasSolution` (tsc -b), and leaving 20 red Solution-based screen tests would have made the tracer commit non-green. So Task 1's commit carries the `hasSolution` removal, `navContainerRef`, and the whole port of the Solution / action-row / walkthrough / publishing tests; the second commit carries only the new bar unit test, the keyboard tests and the D-14 rewind test.
- **Commits:** 91dbcc0f8, 6792d0a15

**2. [Rule 3 - Blocking] `Train.solveLoop.test.tsx` needed a `TooltipProvider`**
- **Issue:** The in-flow bar's `BoardControls` use `Tooltip`, which requires the provider the App shell supplies; the page-level test rendered `TrainPage` bare and 2 tests crashed.
- **Fix:** Wrapped the render in `TooltipProvider` (comment at the site).
- **Commit:** 91dbcc0f8

**3. [Rule 1 - Bug (test)] Behavior of "controls published" changed meaning**
- The plan 06 interim payload existed only off the root; it now exists for the whole reveal, so tests that asserted "published false at the puzzle position" now assert published true with `canReset` false (rewind disabled), and the "pressing Solution after a flip restores the orientation" test became "a flip survives a rewind" per the plan.

**Total deviations:** 3 auto-fixed (1 Rule 1, 2 Rule 3). **Impact:** no scope change.

### Notes

- **Bar sizing is unverified on a real 375px bar.** The four `BoardControls` icon buttons share the free width (`flex-1 min-w-0`) while Analyze and Next are fixed (`h-12 shrink-0 px-3`, `sm:h-8`); jsdom has no layout, so the one-row fit and the in-flow look at 390x844 / 768x1024 / 1280x800 belong to plan 11's browser UAT (E7, pending).
- The in-flow bar uses `BoardControls`' default `flat` sizing (48px buttons) at every width; only Analyze/Next shrink to `sm:h-8`. If the UAT finds the board buttons too tall on desktop, the lever is `buttonClassName` on the bar's `BoardControls`.
- The walkthrough copy still says "Tap a card" / "arrows inside a card" for the chip steps; plan 10 owns the copy and will name the rewind control.
- `onCardEngage` / `onCardsTotalChange` remain unfed (plan 09).

## Known Stubs

None.

## Threat Flags

None. T-237-12 holds (the publish effect clears on unmount and whenever the payload goes null; tests assert null before the verdict, a fresh probe reads false after unmount, and the published Next flushes the review exactly like the in-flow Next); T-237-13 holds (Analyze is an internal `Link` whose analytics run in the click handler, no `data-umami-event`, no position data in props).

## Next Phase Readiness

Plan 08 can move the verdict copy into the strip / right column with the action bar already owning every control; plan 09 can feed `handleRevealUserMove` and the chip select into the v2 telemetry; plan 10 can rewrite the walkthrough copy against the bar ("⏮"); plan 11's browser UAT owns E7.

## Self-Check: PASSED

- FOUND: frontend/src/components/train/TrainRevealActionBar.tsx (`data-testid="train-reveal-action-bar"`), frontend/src/components/train/__tests__/TrainRevealActionBar.test.tsx
- FOUND: `onNext != null` in App.tsx, `onNext?: () => void` in mobileBoardControls.ts, `navContainerRef: boardRef` and `target: 'train-solution'` in TrainSolveScreen.tsx
- GONE: `btn-train-solution`, `VerdictActions`, `hasSolution`, `WALKTHROUGH_SOLUTION_PART`
- FOUND commits: 91dbcc0f8, 6792d0a15
