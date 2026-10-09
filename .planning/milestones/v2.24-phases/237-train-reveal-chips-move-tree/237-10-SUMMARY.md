---
phase: 237-train-reveal-chips-move-tree
plan: 10
subsystem: ui
tags: [react, train, walkthrough, onboarding, tour, copy]
status: complete

requires:
  - phase: 237-05 (chips + tree wiring)
    provides: "notifyChipSelect / notifyTreeStep, train-line-chips"
  - phase: 237-07 (reveal action bar)
    provides: "payload highlight flag, in-flow TrainRevealActionBar highlight"
  - phase: 237-08 (verdict strip)
    provides: "TrainVerdictStrip, desktop verdict bubble, onStripExpand"
  - phase: 237-09 (telemetry v2)
    provides: "puzzleTelemetry.markStripExpanded"
provides:
  - "WalkthroughTarget, WalkthroughContext, walkthroughCopy(step, ctx): six new steps, screen-conditional, within STEPPER_COPY_MAX_CHARS"
  - "TrainReveal tourBubble slot (Hilda above the strip / verdict bubble) and walkthroughTarget prop with data-tour-target wrappers"
  - "useTrainWalkthrough: notifyStripExpand, notifyFork, finish ('Got it'), dismissed flag, phone scroll to data-tour-target"
  - "TrainVerdictStrip ring prop"
affects: [237-11]

tech-stack:
  added: []
  patterns:
    - "Tour bubble rendered by the reveal column (slot prop), not the left chat slot"
    - "Phone scroll prefers the tour bubble under the pinned block when the target still fits, else the target itself"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/TrainVerdictStrip.tsx

key-decisions:
  - "The left chat slot never renders the walkthrough any more (renderTrainBotBubbleBody returns null for the verdict state); resolveBubblePersona lost its walkthrough parameter and Hilda is cast directly for the tour bubble"
  - "Phone scroll deviates slightly from the plan's literal 'target just under the pinned block': scrolling the chips there would push Hilda's copy and Next above the fold, so the tour bubble is aligned under the pinned block when the target still fits above the fixed bottom bar, and the plan's target-first scroll is the fallback"
  - "Open Question 1 stays option (a): no migration, only users with reveal_walkthrough_seen_at IS NULL see the new tour"
  - "'Got it' (btn-train-bot-walkthrough-done) re-adds the end control the actions-in-bubble era dropped; it stamps once and sets a local dismissed flag so the bubble disappears without waiting for the settings refetch"
  - "mergedChip is the You chip's second role (roles[1]); the '=' copy is shown only for that chip"

requirements-completed: [D-09, D-10, D-11]

duration: 12 min
completed: 2026-10-09
actuals:
  tokens: 45000
  tasks: 2
  commits: 2
plan_head_before: a1abe842798a37eaa345a65e39cd1f12a94494db
plan_head_after: 122bafe6af4602d9d7eab99d57cb45cd235c96ac
commits: 2

coverage:
  - deliverable: "D-09: six-step tour whose copy describes only what is on screen, within the 145-char budget in all 12 context combinations"
    verification:
      - kind: test
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#walkthroughCopy"
        status: pass
    human_judgment: false
  - deliverable: "D-10: Hilda's bubble stacks above the strip (phone) / verdict bubble (desktop) and step 1 rings the real strip; rings follow the target through chips, list, board, chips + list, bar"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#tracer: step 1 renders Hilda above the strip and rings the strip"
        status: pass
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#the ring follows the target"
        status: pass
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#Phase 237 plan 10: first-reveal tour rings and bubble slot (D-10)"
        status: pass
    human_judgment: false
  - deliverable: "Auto-advance on strip expand / chip tap / tree step / fork, Next as fallback, 'Got it' ends in place and stamps once, abandoned tour replays"
    verification:
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#Phase 222: first-reveal walkthrough"
        status: pass
    human_judgment: false
  - deliverable: "D-11: tour readability at 390x844, 375x667 and desktop (Hilda bubble plus target visible together, bar ring on the fixed bottom bar)"
    verification: []
    human_judgment: true
    rationale: "Layout readability and the phone scroll heuristic need a real browser; the agent check is scheduled in plan 11"
---

# Phase 237 Plan 10: First-Reveal Tour Rewrite Summary

**The first-reveal tour now teaches the chips + single move tree screen in six steps (result, chips, stepping, sidelines + rewind, "understand, don't memorize", action bar), with Hilda's bubble stacked directly above the real strip (or verdict bubble on desktop), rings on every new target including the bottom bar, interaction auto-advance, and a "Got it" end.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2 (1 tracer, 1 TDD-flagged auto)
- **Files modified:** 8 (frontend only, no migration)

## Accomplishments

- `walkthroughCopy(step, { hasAnalyze, mergedChip, isDesktop })`: phone says "Tap it to read the full feedback" and "in the bar"; desktop drops the strip wording and names the arrow keys and Home; "You = Best" / "You = Game" is explained only when that merged chip is on screen; Analyze only when the puzzle has it; no card or Solution wording. Longest string is 142 chars (budget 145).
- `TrainReveal` gets a `tourBubble` slot rendered first (wrapped in `data-tour-target="bubble"`), `walkthroughTarget` replacing `walkthroughLinesRing`, `data-tour-target` wrappers for chips and list, and a ring on the verdict bubble (`TrainBotBubble ring`) or the strip (`TrainVerdictStrip ring`).
- `TrainSolveScreen` builds the tour bubble with `renderTourBubble` (Hilda, `data-state="verdict"`), computes `mergedChip`, rings the board row for `board`, and publishes `highlight: walkthroughTarget === 'bar'` for the phone bar plus the in-flow bar.
- `useTrainWalkthrough`: `notifyStripExpand` (step 0 to 1), `notifyChipSelect` (1 to 2), `notifyTreeStep` (2 to 3), `notifyFork` (3 to 4); step 4 to 5 only by Next; `finish()` stamps once and dismisses in place.

## Task Commits

1. **Task 1 (tracer): copy, targets, tour bubble slot, rings, phone scroll** - `a70eecbbb`
2. **Task 2: auto-advance, Got it, rewritten walkthrough tests** - `122bafe6a`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Phone scroll would hide Hilda's copy and Next**
- **Found during:** Task 1
- **Issue:** The plan's "scroll the target just under the pinned block" puts the chips row at the top of the visible area, but the tour bubble and strip sit above the chips, so the bubble (copy, Next) would scroll out of view on the very step that asks the user to read it.
- **Fix:** `computeTourScrollDelta` aligns the tour bubble under the pinned block when the target's bottom still fits above the fixed bottom bar (72 px reserve), else falls back to the plan's target-first scroll. Two tests cover both branches.
- **Files modified:** frontend/src/hooks/useTrainWalkthrough.ts, TrainSolveScreen.test.tsx
- **Commit:** a70eecbbb

**2. [Rule 3 - Blocking] Wave plans' `hasAnalyze`-only signatures replaced**
- **Found during:** Task 1
- **Issue:** `renderTrainBotBubbleBody` deps (`activeWalkthroughStep`, `onWalkthroughNext`, `hasAnalyze`) and `resolveBubblePersona`'s walkthrough parameter became dead once the tour moved out of the left slot.
- **Fix:** removed them; Hilda is cast directly for the tour bubble.
- **Commit:** a70eecbbb

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking). **Impact:** none on scope; the scroll heuristic is the one behavior that needs the plan 11 browser check.

## Authentication Gates

None.

## Issues Encountered

None. Full gate run green: `npm run lint`, `npm run build`, `npm test -- --run` (320 files, 5421 tests), `npm run knip` (only the pre-existing css configuration hint).

## Known Stubs

None.

## Next Phase Readiness

Plan 11 checks tour readability at 390x844, 375x667 and desktop (D-11), in particular: Hilda's bubble plus the ringed target visible together on 375x667 (likely not both fit, in which case the fallback scrolls the target and the bubble is above the fold), and the bar ring reaching the fixed bottom bar.

## Self-Check: PASSED

- Files exist: all 8 modified files present on disk (committed in a70eecbbb and 122bafe6a).
- Commits exist on this branch: a70eecbbb, 122bafe6a.
- Acceptance greps: `export type WalkthroughTarget`, `export interface WalkthroughContext`, `tourBubble`, `data-tour-target="chips"`, `notifyFork`, `notifyStripExpand`, `finish`, `btn-train-bot-walkthrough-done` all match; "The cards below" count is 0.
