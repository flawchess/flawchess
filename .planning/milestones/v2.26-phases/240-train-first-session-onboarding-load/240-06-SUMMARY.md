---
phase: 240-train-first-session-onboarding-load
plan: 06
subsystem: ui
tags: [react, typescript, css, train, onboarding, reveal-tour, spotlight, vitest]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "three-part reveal tour, spotlit() test helper, tour copy and score bubble (plans 03-05)"
provides:
  - "One shared pulsing bronze spotlight (.train-tour-spotlight, --brand-glow vars, static under prefers-reduced-motion) used by every tour target"
  - "TOUR_SPOTLIGHT_CLASS constant in lib/theme.ts"
  - "Chips row, chips-plus-list region (train-lines-tour-target) and the reveal action bar spotlit, in flow (sm+) and in the fixed phone bar (MobileBoardControls.spotlight)"
  - "Dead ring props removed from TrainMoveTreeList and TrainBotBubble"
affects: [240-07, train-frontend]

requirements-completed: [D-20, D-06]

actuals:
  tokens: 10300
  tasks: 2
  commits: 2
plan_head_before: ccb3eb1095e548c9637fe8549fc2d1b13dcda441
plan_head_after: 7a883d44d6a4c810559bd3b8604ac027ea091427

tech-stack:
  added: []
  patterns:
    - "Box-shadow-only spotlight class applied by the caller via className; never combined with a Tailwind ring utility (ring is also box-shadow)"
    - "usePublishMobileBoardControls destructures fields explicitly: any new payload field must be added to the destructure, the setPayload object and the effect deps, or it is silently dropped"

key-files:
  created: []
  modified:
    - frontend/src/index.css
    - frontend/src/lib/theme.ts
    - frontend/src/lib/mobileBoardControls.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/App.tsx
    - frontend/src/components/train/TrainVerdictStrip.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainRevealActionBar.tsx
    - frontend/src/components/train/TrainLineChips.tsx
    - frontend/src/components/train/TrainMoveTreeList.tsx
    - frontend/src/components/train/TrainBotBubble.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/App.test.tsx

key-decisions:
  - "Glow color lives in :root CSS vars (--brand-glow rgba(205,127,50,0.85), --brand-glow-halo 0.35), the exact FLAW_FIXED_GLOW values, because a keyframe can only read CSS; FLAW_FIXED_GLOW and Home literals left as is"
  - "Understand step spotlights one wrapper (train-lines-tour-target, flex-col gap-4) around chips row and list; same gap as the reveal column, so no layout shift"
  - "Phone bar glow is outward and may be partly clipped at the screen bottom; judged at the end-of-phase browser check, a UAT gap if unreadable"

status: complete
duration: 10min
completed: 2026-10-15
---

# Phase 240 Plan 06: Shared pulsing tour spotlight Summary

**Every reveal-tour step now points at its target with one shared bronze box-shadow glow (pulsing, static under reduced motion), including the chips row, the chips-plus-list region and the action bar both in the page flow and in the fixed phone bar.**

## Accomplishments

- `index.css`: `--brand-glow` / `--brand-glow-halo` in `:root`, `@keyframes train-tour-spotlight-pulse`, `.train-tour-spotlight` (2px spread ring plus a halo, 1.6s ease-in-out infinite), and `.train-tour-spotlight { animation: none; }` inside the existing reduced-motion block.
- `theme.ts`: `TOUR_SPOTLIGHT_CLASS`. `TrainVerdictStrip` / `TrainVerdictCard` `ring` prop renamed `spotlight`; `TrainReveal` and `TrainSolveScreen` (board row) switched to the class; no `ring-brand-brown` remains in the five train files covered by the plan's gate. The chip selection ring (`TrainLineChips`) and Hilda's reopen badge (`TrainTourOverlay`) are untouched.
- Chips step glows the chips row (active chip keeps its own ring); the understand step glows the new `train-lines-tour-target` wrapper; the stepping step glows the list alone.
- Action bar: in-flow bar gets the class through `className` when the step targets `bar`; below `sm` the published `MobileBoardControls.spotlight` flag drives `renderBoardControlsBar` in App.tsx.
- Dead `ring` props deleted from `TrainMoveTreeList` and `TrainBotBubble`; `WalkthroughTarget` and `walkthroughTarget` docstrings rewritten.

## Task Commits

1. **Task 1: One shared pulsing glow replaces the verdict, list and board tour rings (tracer)** - `691106d96` (feat)
2. **Task 2: Glow for chips row, chips-plus-list region and action bar (in flow and phone bar); drop dead ring props** - `7a883d44d` (feat)

## Verification

- `npm test -- --run`: 332 files, 5645 tests passed. `npm run build` (tsc -b + vite) clean. `npm run lint` clean. `npm run knip`: no unused exports (only the two pre-existing `knip.json` configuration hints).
- Acceptance greps: keyframes, `var(--brand-glow)`, reduced-motion override, `TOUR_SPOTLIGHT_CLASS` in all three files, `spotlight?: boolean`, `boardControls.spotlight`, `train-lines-tour-target` present; `ring?: boolean` gone; `ring-2 ring-brand-brown` still in TrainLineChips and TrainTourOverlay.
- Mutation check: forcing the App.tsx fixed-bar class condition to `false` fails the "payload with spotlight true" case (1 failed, 74 passed); restored and green. The payload cases in the solve-screen test failed against the first version of `usePublishMobileBoardControls` (it drops unknown fields), which is how the missing destructure was found.
- Tracer gate: Task 1 split-reveal-tour and the whole solve-screen file passed (185), plus tsc and lint, before expansion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `usePublishMobileBoardControls` silently dropped `spotlight`**
- **Found during:** Task 2 tests (probe read `undefined`)
- **Issue:** the hook destructures fields explicitly; the plan only listed the interface, the TrainSolveScreen payload and App.tsx.
- **Fix:** `spotlight` added to the destructure, the `setPayload` object and the effect deps.
- **Files modified:** frontend/src/lib/mobileBoardControls.ts
- **Commit:** 7a883d44d

**2. [Rule 1 - Test fallout] TrainReveal.test.tsx asserted the old rings**
- **Found during:** full frontend run after Task 2 (not in the plan's file list; Task 1's scoped run did not include it)
- **Issue:** four cases asserted `ring-2` on the verdict card/strip and "chips never ringed / lines rings the list".
- **Fix:** rewrote the describe to the shared class: chips row, tree, the lines wrapper (and not its parts), and null/other targets; verdict card and strip. Also reworded the stale `TrainLineChips` row comment.
- **Files modified:** frontend/src/components/train/__tests__/TrainReveal.test.tsx, frontend/src/components/train/TrainLineChips.tsx (comment only)
- **Commit:** 7a883d44d

**3. [Plan expectation vs behavior] "no spotlight after leaving the last step" does not hold in the mounted screen**
- **Issue:** the tour's `target` stays on the last step until the screen unmounts for the next puzzle (existing hook behavior; the Next exit flushes to a new puzzle). With the bar now spotlit on that step the class remains until then. Replaced the Task 1 "after leaving" case with "exactly one element is spotlit at a time and the glow moves with the step"; the stage-3 "nothing spotlit anywhere" case is kept. No production change.

**Total deviations:** 3 (two auto-fixes, one test reformulation). **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-240-14 mitigated: the class is applied only while its step targets the element, one element is spotlit at a time (asserted), and reduced motion disables the animation.

## Issues Encountered

None. Pending for the orchestrator (end of phase, Chrome): the visual human-check at 390x844, 375x667 and desktop for all three parts and once with reduced-motion emulation, in particular glow clipping on the board row and the fixed phone bar, and the chips-row glow next to the active chip's ring.

## Self-Check: PASSED

- FOUND: all 15 modified files; FOUND commits `691106d96`, `7a883d44d` (ancestors of HEAD); acceptance greps and the full frontend chain re-run green.
