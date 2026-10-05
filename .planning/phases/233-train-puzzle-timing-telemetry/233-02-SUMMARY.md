---
phase: 233-train-puzzle-timing-telemetry
plan: 02
subsystem: ui
tags: [react, typescript, telemetry, visibility-api, vitest]

requires:
  - phase: 233-train-puzzle-timing-telemetry
    provides: "plan 01 server contract: SolveRequest.telemetry (SolveTelemetry), clamped and merged into drill_solves.telemetry"
provides:
  - "Client think-time telemetry on the real solve POST body: v, client, guess_ms, move_ms, think_hidden_ms, resumed"
  - "Pure visible-only stopwatch (lib/visibleStopwatch.ts) with injected clock"
  - "lib/deviceClass.ts: isMobileUserAgent (extracted from useInstallPrompt) + telemetryClient"
  - "lib/trainTelemetry.ts: mirrored TELEMETRY_SCHEMA_VERSION / TELEMETRY_DURATION_CAP_MS, clamp, solve-patch builder, sessionStorage resume marker"
  - "useTrainPuzzleTelemetry hook (think part) and Python/TS cap parity test"
affects: [233-03, 233-04, 233-05]

actuals:
  tokens: 9500
  tasks: 2
  commits: 2
plan_head_before: 2ee6ff68bcaf44889c96fd397f226397d9a4b8f3
plan_head_after: 611183b995dbc352e8e5ca35bd0a3f5f6beba479

tech-stack:
  added: []
  patterns:
    - "Ref-only per-puzzle hook that resets on a (session, position) key change so StrictMode double effects cannot restart the timer or read their own resume marker"
    - "Pure stopwatch with idempotent visibility transitions; start-while-hidden opens a hidden span"
    - "TS constants as plain integer literals regex-extracted by a Python parity test"

key-files:
  created:
    - frontend/src/lib/trainTelemetry.ts
    - frontend/src/lib/visibleStopwatch.ts
    - frontend/src/lib/deviceClass.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/lib/__tests__/visibleStopwatch.test.ts
    - frontend/src/lib/__tests__/deviceClass.test.ts
    - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
    - tests/schemas/test_train_telemetry_parity.py
  modified:
    - frontend/src/types/train.ts
    - frontend/src/hooks/useInstallPrompt.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx

key-decisions:
  - "Think timer starts at engine isReady, not at mount, so 'Loading engine…' time never lands in guess_ms (Pitfall 8)"
  - "Restored reveal prefers restoredSolve.sessionId over trainSession.session (Pitfall 6); a restored reveal starts no timer and writes no resume marker"
  - "Resume marker is a single sessionStorage entry holding the latest (session:position); a fresh hook instance finding its own key reports resumed: true"
  - "Counter caps are not declared on the TS side in this plan (unused exports fail knip); plan 04 appends them to the parity tuple"

patterns-established:
  - "Frozen telemetry snapshot at move time so solve retries resend the identical object (existing retry-body test is the regression guard)"

requirements-completed: [D-02, D-04, D-05, D-09]

coverage:
  - id: C1
    description: "A guess and a graded move put v, client, guess_ms, move_ms, think_hidden_ms, resumed on the real solve POST body"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: the solve POST carries v, client, guess_ms, move_ms, think_hidden_ms and resumed"
        status: pass
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a forced solve-POST failure blocks Next ... retry re-submits the identical payload"
        status: pass
    human_judgment: false
  - id: C2
    description: "Only visible time counts: hidden span excluded and stored as think_hidden_ms, hidden mount starts paused, duplicate hidden is a no-op, durations capped at 30 min"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#think: *"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/visibleStopwatch.test.ts"
        status: pass
    human_judgment: false
  - id: C3
    description: "client is mobile for Android/iPhone/iPad/iPod UAs and desktop otherwise, via the extracted regex; install prompt unchanged"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/deviceClass.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useInstallPrompt.test.ts"
        status: pass
    human_judgment: false
  - id: C4
    description: "Remount of an unsolved puzzle sends resumed: true; first mount including StrictMode sends false"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: a remount of the same unsolved puzzle sends resumed: true"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#think: a first mount under React StrictMode is not resumed"
        status: pass
    human_judgment: false
  - id: C5
    description: "TS telemetry caps cannot drift from app/schemas/train.py"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/schemas/test_train_telemetry_parity.py"
        status: pass
    human_judgment: false
  - id: C6
    description: "No client scoring code reads telemetry (trainScore.ts untouched)"
    requirement: "D-05"
    verification:
      - kind: command
        ref: "git diff --stat -- frontend/src/lib/trainScore.ts (empty)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-05
status: complete
---

# Phase 233 Plan 02: Client think-time telemetry Summary

**Visible-only, 30-minute-capped, resume-aware `guess_ms`/`move_ms`/`think_hidden_ms` plus `client` and `resumed`, measured by a ref-only hook and frozen into the real solve POST body.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-10-05
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files:** 12 (8 created, 4 modified)

## Accomplishments

- Tracer (Task 1): `useTrainPuzzleTelemetry` is called once in `TrainSolveScreen`; `handleGuess`/`handleIntroGuess` stamp the guess mark, the graded branch of `handlePieceDrop` freezes the snapshot right before `gradeAndSolve`, and `trainSession.solvePuzzle` carries `telemetry: puzzleTelemetry.solveTelemetry()`. The pre-existing retry test (`retryBody toEqual firstAttemptBody`) still passes, proving the snapshot is frozen.
- `isMobileUserAgent()` extracted to `lib/deviceClass.ts` with the exact regex and its D-06 comment; `useInstallPrompt` now calls it (its test suite passes unchanged). `Android|iPhone|iPad|iPod` appears in non-test source only in `deviceClass.ts`.
- `lib/visibleStopwatch.ts` is a pure accumulator (`startStopwatch`/`applyVisibility`/`readStopwatch`) with an injected clock, idempotent transitions and start-while-hidden support.
- Task 2: 6 stopwatch tests, 4 device-class tests, 11 hook tests ("think: ...") and the Python/TS parity test pin the edge cases.

## Mutation proofs

- Parity: changing `TELEMETRY_DURATION_CAP_MS` in `trainTelemetry.ts` to 1800001 made `test_telemetry_constant_matches_frontend[TELEMETRY_DURATION_CAP_MS-1800000]` FAIL; reverted, green again.
- Visibility: forcing `applyVisibility` to always return the stopwatch unchanged failed 4 tests (3 hook, 1 stopwatch: hidden span, duplicate hidden, hidden mount); reverted, 17/17 green.

## Task Commits

1. **Task 1 (tracer): think-time telemetry on the solve POST** - `e210eaf78` (feat)
2. **Task 2: unit tests and cap parity** - `611183b99` (test)

## Deviations from Plan

None - plan executed exactly as written. Plan 04 still needs to append the three counter caps to both `trainTelemetry.ts` and `_MIRRORED_CONSTANTS`.

## Known Stubs

None.

## Threat Flags

None beyond the plan's `<threat_model>`: only the two-value `client` class leaves the device (T-233-09); no new network surface this plan.

## Self-Check: PASSED

- Created files present (4 libs/hook, 3 frontend test files, parity test); commits `e210eaf78`, `611183b99` exist; `commits:` measured from the plan ledger (2).
- Verification: TrainSolveScreen + stopwatch + deviceClass + hook + useInstallPrompt vitest green (102 + 36), parity pytest green, `npm run lint`, `npm run build`, `npm run knip`, `ruff check .`, `ty check app/ tests/ scripts/` all exit 0; `trainScore.ts` diff empty.
