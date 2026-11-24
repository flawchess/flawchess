---
phase: 263-foreign-blunder-fillers
plan: 02
subsystem: ui
tags: [react, typescript, train, copy, vitest, tdd]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: plan 01 backend (DrillSource.FOREIGN_BLUNDER, DrillSourceWire "foreign_blunder")
provides:
  - FOREIGN_TAIL on every foreign puzzle, returnPhrase with no session input
  - INTRO_NO_OWN_PUZZLES_WELCOME_COPY and introSteps/introCopy(noOwnPuzzles)
  - NO_OWN_DUE_TODAY_COPY rendered as train-landing-no-own-due on the start screen
  - no-own score bubble (NO_OWN_PUZZLES_NOTE_FIRST/LATER, reminder ask, clause) and the new GUEST_SIGNUP_ASK_SCORE
  - TrainSessionResponse.own_puzzle_count and 'foreign_blunder' in every source union
affects: [263-09, 263-03, 263-04, 263-05, 263-06, 263-07, 263-08, 263-10]

plan_head_before: 40c8ad1eab824b49f1a4d3111e39835925895a76
plan_head_after: 4cdd966fb859cb0c2fe7ccaf655e8ab5fe84be7e

actuals:
  tokens: 11900
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "The client reads own_puzzle_count only as === 0; no partial-count copy"
    - "Return tail is per puzzle (source), never a session property"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/types/train.ts
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainVerdictDetails.tsx
    - frontend/src/pages/Train.tsx
    - frontend/src/pages/Welcome.tsx

key-decisions:
  - "D-13 'established user' = hasGames AND progress.modes.puzzles.first_session_done === true (assumption, owner review)"
  - "The D-12 no-own welcome is 155 chars, over STEPPER_COPY_MAX_CHARS (145); the copy test holds it to seven 24px lines (168) instead and the constant is untouched"
  - "own_puzzle_count is read only as === 0; a server that omits the field (until 263-09) shows the own-games copy"

requirements-completed: [D-04, D-11, D-12, D-13]

coverage:
  - id: D1
    description: "Every foreign puzzle shows the neutral return-tail line after solving, herring tail unchanged, legacy sharp_filler shows none"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#returnPhrase (truth table)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a $source verdict in a session with own_puzzle_count"
        status: pass
    human_judgment: false
  - id: D2
    description: "A session with no own puzzles opens the intro with the owner's welcome; otherwise the own-games welcome stays"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#introCopy / introSteps (two bubbles)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a session with no own puzzles is also exactly two bubbles"
        status: pass
    human_judgment: true
    rationale: "The 155-char welcome exceeds the calibrated 145-char phone budget; it needs a 375x667 device measurement"
  - id: D3
    description: "An established user on the exhausted day reads the start-screen sentence with no session name"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx#the exhausted-day sentence (D-13)"
        status: pass
    human_judgment: true
    rationale: "'Established user' is an assumption and the sentence wording is an owner review item"
  - id: D4
    description: "Client contract carries own_puzzle_count; no Train file keeps a warm-up branch, prop, identifier or word"
    requirement: "D-04"
    verification:
      - kind: other
        ref: "git grep -n -i -e warm-up -e warmup over the plan's Train scope exits 1 (no match); npm run build exits 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Score screen for a no-own session uses the proposed copy; guest sign-up ask no longer mentions warm-ups"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#scoreBubbleCopy"
        status: pass
    human_judgment: true
    rationale: "Proposed wording is an owner review item (orchestrator ruling 5)"

duration: 20min
completed: 2026-11-23
status: complete
---

# Phase 263 Plan 02: Client Copy and Contract for the Foreign Blunder Fillers Summary

**The Train client drops the warm-up concept: `own_puzzle_count` replaces the retired session flag, every foreign puzzle gets a neutral per-puzzle tail, and the intro, start screen and score screen speak truthfully about a session with no own puzzles.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 3 of 3
- **Files modified:** 23 (no new files)

## Accomplishments

- `trainBotCopy.ts`: `FOREIGN_TAIL` replaces the filler tail and `returnPhrase` takes no session flag (herring tail in every session, legacy `sharp_filler` shows none, SR rules byte-identical). `introSteps`/`introCopy` take `noOwnPuzzles` and pick the D-12 welcome. `NO_OWN_DUE_TODAY_COPY` exported for D-13. Score bubble keys on `noOwnPuzzles` with the first/later notes for every audience, and `GUEST_SIGNUP_ASK_SCORE` now reads "Sign up free and your own blunders become your puzzles. ..."
- `types/train.ts`: `TrainSessionResponse.own_puzzle_count: number`; `'foreign_blunder'` added to `SolvedResult`, `SolveResponse` and `PuzzleRevealResponse` source unions, `'sharp_filler'` kept for cached verdicts.
- `TrainStartScreen.tsx`: the `'warmup'` landing kind and `resume.isWarmup` are gone; `showNoOwnDue` renders `<p data-testid="train-landing-no-own-due">` in the host bubble (fresh and resume states, also kept visible on phones).
- `TrainScoreScreen`, `Train.tsx`, `TrainSolveScreen`, `TrainReveal`, `TrainVerdictDetails`, the admin demo, `Welcome.tsx` (`DELTA_2` reworded), and comments in `App.tsx`/`ImportAskActions.tsx` updated; every Train fixture carries `own_puzzle_count`.

## Task Commits

1. Task 1: copy library - `9e1db9931`
2. Task 2: contract, start screen, score screen - `e68e7642d`
3. Task 3: solve screen, reveal, verdict details, fixtures, gate - `4cdd966fb`

## Verification (observed)

- `npm run lint`: exit 0
- `npm run build` (tsc -b + vite): exit 0, no `error TS`
- `npm test -- --run`: 382 files, 6859 tests passed
- `npm run knip`: exit 0 (two configuration hints, no unused exports or files)
- Scoped D-04 `git grep -n -i -e warm-up -e warmup` over the plan's Train scope: no match
- `grep -c "own_puzzle_count === 0" TrainSolveScreen.tsx`: 1

## Decisions Made

- D-13 "established user" is `hasGames` plus `modes.puzzles.first_session_done === true`, strict so a pending progress query never flashes the sentence (assumption for owner review).
- The owner's D-12 welcome is 155 characters, over `STEPPER_COPY_MAX_CHARS` (145). The constant is untouched; the copy test holds that one welcome to a seven-line bound (7 x 24 = 168) and flags the missing 375x667 device measurement.
- Task commits are single test+implementation commits per task (no separate RED commit), since the tasks rewrite existing suites rather than add new behavior over unchanged ones.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Matrix test forbade the new "nothing comes back yet" note**
- **Found during:** Task 1
- **Issue:** The existing "no returning text" matrix regex matches `comes back`, which is inside the plan-mandated `NO_OWN_PUZZLES_NOTE_LATER`.
- **Fix:** The matrix strips that one sentence before checking; it still forbids every other returning-count text.
- **Files modified:** frontend/src/lib/__tests__/trainBotCopy.test.ts
- **Commit:** 9e1db9931

**2. [Rule 3 - Blocking] Phone copy budget vs the owner's welcome wording**
- **Found during:** Task 1
- **Issue:** The D-12 welcome (155 chars) fails the 145-char intro budget test.
- **Fix:** See Decisions Made; wording kept verbatim.
- **Files modified:** frontend/src/lib/__tests__/trainBotCopy.test.ts
- **Commit:** 9e1db9931

**Total deviations:** 2 auto-fixed. **Impact:** none on behavior; one open measurement (below).

## Issues Encountered

None. The server does not send `own_puzzle_count` yet (263-09), so against the current backend `own_puzzle_count === 0` is false and the own-games copy shows, as the plan specifies.

## Known Stubs

None.

## Threat Flags

None. T-263-06 and T-263-07 mitigations are implemented: foreign copy names no person and nothing marks a puzzle pre-attempt; the D-13 sentence is gated on `=== 0` and `first_session_done === true`.

## Open Items for the Owner

- Device-check the D-12 welcome at 375x667 (155 chars, budget calibrated at 145).
- Review the proposed wording: score-screen notes, new guest sign-up line, `DELTA_2`, and the "established user" definition for D-13.

## Next Phase Readiness

Ready for the remaining wave plans. 263-09 must send `own_puzzle_count` for the client branches to activate.

## Self-Check: PASSED

- Commits `9e1db9931`, `e68e7642d`, `4cdd966fb` are ancestors of HEAD.
- Modified files exist and the full frontend gate was green at `4cdd966fb`.
