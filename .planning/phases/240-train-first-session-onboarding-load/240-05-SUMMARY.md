---
phase: 240-train-first-session-onboarding-load
plan: 05
subsystem: ui
tags: [react, typescript, train, onboarding, intro, score-bubble, vitest]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "three-part reveal tour and the settings fixture on reveal_tour_stage (plans 03-04)"
provides:
  - "Two-bubble puzzle-1 intro for every audience and warm-up sessions (IntroStep 0 | 1, INTRO_STEP_COUNT = 2)"
  - "Score bubble per the D-19 sheet: PRACTICE_RATIONALE in line 1 of the first completed session in the regular, perfect and warm-up branches; later sessions read 'See you tomorrow.'"
  - "No returning-counts sentence in any session; ScoreBubbleInput without outcomes/session_date/expires_on"
  - "sr_explained stamped whenever the first-completed variant renders, in any branch (D-21)"
affects: [240-06, 240-07, train-frontend]

requirements-completed: [D-01, D-02, D-16, D-17, D-18, D-19, D-21]

actuals:
  tokens: 33000
  tasks: 2
  commits: 2
plan_head_before: 503e3314031a71277fa554189cde7461de70d0c7
plan_head_after: 18413d87f7f8ec76d4b69ac0851701c2761728f6

tech-stack:
  added: []
  patterns:
    - "Fixed-size copy sequence as an exported constant (INTRO_STEP_COUNT) instead of a count function that varied with flags"
    - "Matrix tests built with flatMap so exhaustive combinations stay within the max-depth 4 lint gate"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/trainBubbleState.ts
    - frontend/src/components/train/TrainBotStepper.tsx
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/pages/Train.tsx
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/trainBubbleState.test.ts
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx

key-decisions:
  - "PRACTICE_RATIONALE stays module-private (tests assert the literal string, knip clean)"
  - "D-21 stamp gate is `bubbleCopy !== null && firstExplanation`; the existing latch keeps the copy stable across the stamp's cache write-back"
  - "The warm-up `no_games` early return is kept: a registered zero-game first session still gets a single line 1 (now with the rationale)"

status: complete
duration: 12min
completed: 2026-10-15
---

# Phase 240 Plan 05: Two-bubble intro and the reworked score bubble Summary

**Puzzle 1 now reaches the guess buttons after one Next (welcome, then "Decide first, then play. Your turn. ..."), and the first completed session's score bubble explains why practice matters in line 1 in every branch, with no return counts on any session.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-10-15
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Intro: `IntroStep = 0 | 1`, exported `INTRO_STEP_COUNT = 2`, `introSteps(sideToMove, audience)` and `introCopy(step, sideToMove, audience)` (the warm-up flag is gone). The question, vocabulary, practice and warm-up intro steps are deleted. The four audience welcomes are unchanged. `WARMUP_TAIL_COPY`, `WARMUP_SCORE_CLAUSE` and the `returnPhrase` verdict tails are untouched (D-02: a warm-up first session learns that from the puzzle-1 verdict tail).
- `TrainSolveScreen`: `BubbleBodyDeps` and `resolveBubblePersona` drop `isWarmup`; `handleIntroNext` clamps at `INTRO_STEP_COUNT - 1`; the `isWarmup` const stays for TrainReveal.
- Score bubble: `scoreBubbleCopy` takes `missedCount, isFirstCompletedSession, isWarmup, reminderAsk, band, audience` only. Branches: regular first = opener + rationale / habit line + ask; regular later = opener + "See you tomorrow."; perfect first = "Nothing got away today." + rationale / habit line + ask; perfect later = unchanged lead + ask or understanding tip; warm-up first = opener + rationale + "Those were warm-ups." + audience clause; warm-up later unchanged. `returningCountsSentence` and `ScoreBubbleOutcome` removed.
- `TrainScoreScreen`: `sessionDate`/`expiresOn` props removed (and from `pages/Train.tsx`); stamp gate is `showsFirstSessionCopy`, so an all-warm-up guest no longer sees the rationale every session. Accepted side effect (owner, D-21): a first warm-up session means the later "Reminders build the habit" line is never shown.
- Tests rewritten with exact strings: intro describes (all four audiences x both sides), score-bubble describes plus a 384-combination matrix for at-most-2-lines and no returning text, and TrainScoreScreen cases flipped to "stamps exactly once".

## Task Commits

1. **Task 1: Two-bubble intro end to end (tracer)** - `b21227e1a` (feat)
2. **Task 2: Score bubble rationale, no counts, stamp in any branch** - `18413d87f` (feat)

## Verification

- `npm test -- --run`: 332 files, 5638 tests passed. `npm run build` (tsc -b + vite): no TS errors. `npm run lint`: clean. `npm run knip`: exit 0 (two pre-existing `knip.json` configuration hints, unrelated).
- Acceptance greps: `IntroStep = 0 | 1` and `INTRO_STEP_COUNT = 2` present; no `INTRO_QUESTION|INTRO_VOCABULARY|INTRO_PRACTICE|INTRO_WARMUP_COPY|introStepCount|returningCountsSentence|ScoreBubbleOutcome|Nothing else is coming back` anywhere in `frontend/src`; no `sessionDate|expiresOn|missedCount > 0` in TrainScoreScreen.tsx; `showsFirstSessionCopy` present.
- Mutation check: restoring the old stamp gate (`!isWarmup && missedCount > 0`) fails the warm-up and perfect "stamps exactly once" cases (2 failed, 38 passed); restored and green.
- Tracer gate: the Task 1 intro tests (`-t` filters equivalent: whole TrainSolveScreen file 183 passed) and build passed before expansion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan expectation] "No 'come back' text in any branch" collides with the unchanged guest sign-up ask**
- **Found during:** Task 2 matrix test
- **Issue:** `GUEST_SIGNUP_ASK_SCORE` (kept verbatim by D-19, warm-up line 2 for guests) reads "your own blunders come back instead of warm-ups". It is not a returning-counts sentence, but it matches the broad regex.
- **Fix:** the matrix test exempts that one fixed line; every other line is still checked. No production copy changed.
- **Files modified:** frontend/src/lib/__tests__/trainBotCopy.test.ts
- **Commit:** 18413d87f

**2. [Rule 1 - Test bug] Unmount-mid-stepper case clicked Next twice**
- **Found during:** Task 1
- **Issue:** with two steps the second click has no Next button to find. Fixed to one click and renamed to "on the closing step".
- **Commit:** b21227e1a

**Total deviations:** 2 auto-fixed (test-side only). **Impact:** none on scope or shipped copy.

## Known Stubs

None.

## Threat Flags

None. T-240-12 mitigated (copy is built only from constants; the "no position number, game id or ply" case stays green); T-240-13 accepted as planned.

## Issues Encountered

None. Pending for the orchestrator (end of phase): the 375x667 / 390x844 / desktop above-the-fold human check on the worst case line 1 (guest with games, red band, first session, 230 characters). The TrainStepper `nextTestId` docstring still mentions the old walkthrough caller; left as is (out of this plan's scope).

## Self-Check: PASSED

- FOUND: all 10 modified files; FOUND commits `b21227e1a`, `18413d87f` (ancestors of HEAD); all `<acceptance_criteria>` greps and the frontend chain re-run green.
