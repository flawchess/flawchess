---
phase: 240-train-first-session-onboarding-load
plan: 03
subsystem: ui
tags: [react, typescript, train, onboarding, reveal-tour, vitest]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "reveal_tour_stage (0..3) on TrainSettingsResponse and POST /train/onboarding/reveal_tour_1..3 (plan 01)"
provides:
  - "Three-part reveal tour model in lib/trainBotCopy.ts (TourStepId, TourPart, tourPartSteps, tourPartForStage, isRevealTourDone, TourAnswerKind, tourAnswerKind, tourStepCopy)"
  - "useTrainWalkthrough: one part latched per reveal, per-part step index, stamps reveal_tour_{part+1} on leaving the last step"
  - "Part 1 result bubble worded per device and answer type (D-19 verbatim, no points sentence), Next bubble, per-part n / m counter"
  - "Landing reminder ask gated on isRevealTourDone (D-22); Hilda out of the host pool while stage < 3"
  - "Whole frontend free of the retired walkthrough settings field and step name; build, lint, knip, tests green"
affects: [240-04, 240-06, 240-07, train-frontend]

actuals:
  tokens: 17500
  tasks: 2
  commits: 2
plan_head_before: 8df24af2a31081f386231e30a45a020c6614e8b5
plan_head_after: 378c59161acea975424a413cd7e68d977612ed9f

tech-stack:
  added: []
  patterns:
    - "Per-reveal part latch in state (set once from the live stage, cleared per puzzle) so a mid-reveal setQueryData never switches the part"
    - "Restored reveals (restoredSolve !== null) never start a tour part; the latch alone cannot cover this because it is component state lost on unmount"
    - "Test-local spotlit() helper so plan 06 swaps one body instead of every spotlight assertion"

key-files:
  created: []
  modified:
    - frontend/src/types/train.ts
    - frontend/src/hooks/useTrainOnboarding.ts
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainBotStepper.tsx
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainReminderButton.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "TOUR_PART_COUNT stays module-private in trainBotCopy.ts (only isRevealTourDone/tourPartForStage use it), so knip stays clean"
  - "A restored reveal never starts a part (differs from the old tour, which restarted on the restored reveal); a part left halfway replays on the next puzzle's reveal"
  - "Hilda host exclusion keeps stage < 3: she narrates whichever part is due"
  - "markWalkthroughActive telemetry unchanged: review_walkthrough is true on every reveal where a part ran"

patterns-established:
  - "Tour spotlight assertions go through a test-local spotlit(element) helper"

requirements-completed: [D-03, D-04, D-05, D-06, D-07, D-08, D-10, D-11, D-12, D-19, D-22, D-23]

duration: 8min
completed: 2026-10-15
status: complete
---

# Phase 240 Plan 03: Split Reveal Tour (frontend) Summary

**The six-step first-reveal walkthrough is now three parts driven by the server's `reveal_tour_stage`: part 1 (result bubble teaching "only one" vs "several" per answer type, then Next) runs on a stage-0 reveal and stamps `reveal_tour_1` on leaving, while the model and hook already carry parts 2 and 3.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-10-15
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- `lib/trainBotCopy.ts`: replaced `WalkthroughStep`, `WALKTHROUGH_STEP_COUNT`, `walkthroughCopy`, `walkthroughActionsCopy` with the part model. Stage 0/1/2 map to `[result, next]`, `[chips, stepping]`, `[sidelines, understand, analyze]`; stage 3 maps to none. The four result variants (phone/desktop x sharp/several), Next and the two Analyze variants are the D-19 strings verbatim; chips, stepping, sidelines and understand are unchanged. No points sentence, no em-dash, all within the 145-char budget.
- `hooks/useTrainWalkthrough.ts`: latches `tourPartForStage` once per reveal (only while the latch is empty, only with a verdict, loaded settings and `!isRestored`), so the leave stamp's cache write cannot switch parts mid-reveal. `consumeNext` advances within the part, `leave` stamps `REVEAL_TOUR_STAMP[part]` only from the part's last step, so an abandoned part stamps nothing and replays. Exposes `stepIndex`, `stepCount`, `part` for the per-part counter (D-23).
- `TrainSolveScreen.tsx`: passes `answerKind` from `verdict.puzzle_type` and `isRestored: restoredSolve !== null`, renders the per-part counter, and keeps Hilda out of the host pool while `!isRevealTourDone`.
- `TrainStartScreen.tsx`: the landing reminder ask waits for `isRevealTourDone(settings.reveal_tour_stage)` (stage 3 shows it, stage 2 does not).
- `types/train.ts` / `useTrainOnboarding.ts`: `RevealTourStage`, `reveal_tour_stage` on the settings response, `OnboardingStep` mirrors the server Literal exactly; no frontend file names the retired field or step.

## Task Commits

1. **Task 1: Tour part 1 end to end (tracer)** - `8e5228e3a` (feat)
2. **Task 2: Landing reminder ask on the stage and the frontend-wide field swap** - `378c59161` (feat)

**Plan metadata:** committed separately after this file (docs).

## Verification

- `npm test -- --run`: 332 files, 5622 tests passed. `-t "split reveal tour"`: 5 passed.
- `npm run build` (tsc -b + vite): exit 0. `npm run lint`: clean. `npm run knip`: exit 0 (two pre-existing configuration hints about `knip.json`, unrelated).
- `grep -rn "reveal_walkthrough" frontend/src` and `grep -rn "WALKTHROUGH_STEP_COUNT\|walkthroughCopy(" frontend/src`: no hits.
- Task 1 left `npm run build` red between the two commits as the plan predicted; Task 2 turned it green.

## Deviations from Plan

None - plan executed exactly as written. Two notes for plan 04:

- The old walkthrough describe in `TrainSolveScreen.test.tsx` was replaced, not migrated, as the plan directs. Its later-part cases (chips/stepping/sideline/analyze copy, overlay hide/reopen on phone and desktop, the three phone scroll-to-chips cases, arrow-set invariance, abandon-replay) are in `main` history and need re-adding on parts 2 and 3.
- The `animateScrollTop` import in that test file was removed because the scroll cases left with the describe (ESLint no-unused-vars). The `vi.mock('@/lib/animatedScroll')` stays; plan 04 re-adds the import with the scroll cases.

**Total deviations:** 0.

## Known Stubs

None.

## Threat Flags

None. All changes fall under the plan's `<threat_model>`: T-240-09 is mitigated (the hook returns no part until `hasVerdict`, and the stage-0 cases render no overlay before the verdict lands); T-240-10 and T-240-11 are transfer/accept as planned.

## Issues Encountered

None.

## Self-Check: PASSED

- FOUND: frontend/src/lib/trainBotCopy.ts, frontend/src/hooks/useTrainWalkthrough.ts, frontend/src/hooks/useTrainOnboarding.ts, frontend/src/types/train.ts, frontend/src/components/train/TrainStartScreen.tsx
- FOUND commits: 8e5228e3a, 378c59161 (ancestors of HEAD)
