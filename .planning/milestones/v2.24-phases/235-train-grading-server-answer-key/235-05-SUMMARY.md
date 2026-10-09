---
phase: 235-train-grading-server-answer-key
plan: 05
subsystem: ui
tags: [react, typescript, train, copy, recheck, vitest, changelog]

requires:
  - phase: 235-train-grading-server-answer-key (plan 03)
    provides: "SolveResponse.disagreement set by the server for a credited disagreement"
  - phase: 235-train-grading-server-answer-key (plan 04)
    provides: "runRecheck / recheckMove in TrainSolveScreen.gradeAndSolve, GatedRecheckWorker, TRAIN_RECHECK_TIMEOUT_MS"
provides:
  - "guessFeedbackProse D-15 first guard: '<key SAN> is the engine's first choice, but your move holds up too.' for both guesses"
  - "TrainReveal wiring: verdict.disagreement ?? false and the key SAN from gradeResult.bestMoveUci"
  - "RECHECK_COPY 'Taking a closer look…' and the grading bubble state { kind: 'grading'; recheck: boolean }"
  - "TrainSolveScreen isRechecking state around the recheckMove await and the train-recheck-indicator bubble"
  - "CHANGELOG [Unreleased] -> Fixed bullet and a green phase-wide pre-merge gate"
affects: []

actuals:
  tokens: 9000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Wait-state flag carried on an existing discriminated-union member (grading + recheck) instead of a new bubble kind"
    - "State flag set immediately before a single await and cleared in its finally, so a null result or throw cannot leave it on"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainGuessLabels.ts
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/trainBubbleState.ts
    - frontend/src/components/train/__tests__/trainBubbleState.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - CHANGELOG.md

key-decisions:
  - "D-15 line reads the server's disagreement flag only (never the phone's outcome), so a claim the server refused shows the standard copy (T-235-07)"
  - "isRechecking is set/cleared inside plan 04's runRecheck helper around the single recheckMove await (try/finally), so the trigger, POST body and grade replacement are untouched"
  - "verdictClause is untouched: the bubble's 'Right call, right move' already agrees with a credited disagreement (plan 03 credits either guess)"

requirements-completed: [D-12, D-15, D-20]

coverage:
  - id: D1
    description: "A server-credited disagreement renders the D-15 line naming the key SAN on the reveal guess card for either guess; the six locked strings are unchanged"
    requirement: "D-15"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#a confirmed disagreement names the key for both guesses, whatever the other inputs (D-15)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#a server-confirmed disagreement renders the D-15 line naming the key SAN on the guess card (D-15)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#a verdict without the disagreement field keeps the old copy even when a key is known (D-15)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The bubble reads 'Taking a closer look…' while the re-check runs and the verdict replaces it afterwards"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#the bubble reads \"Taking a closer look…\" while the re-check runs, then the verdict replaces it (D-12)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/trainBubbleState.test.ts#grading state carries recheck: true while the disagreement re-check runs (D-12)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A stalled re-check never leaves the wait copy on screen: after the timeout the indicator is gone and the verdict renders from the 1.5 s grade"
    requirement: "D-20"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a stalled re-check falls back to the 1.5 s grade and posts no recheck (D-20)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-05: with every phase plan applied the key, type and runner-up are named only in TrainSolveScreen (dotted puzzle. reads), TrainReveal and types/train.ts"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "D-05 gate A (prints the three files) and gate B (prints nothing) from the plan, run after Task 2"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full CLAUDE.md pre-merge gate green on both stacks with plans 01-05 applied"
    verification:
      - kind: other
        ref: "ruff format/check, ty, check_function_size, pytest -n auto -x (5352 passed), npm lint/build/test/knip (313 files, 5230 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The re-check wait copy, D-15 line and no pre-attempt key leak behave in a live browser against the dev server"
    verification: []
    human_judgment: true
    rationale: "Browser UAT legs 1-5 from the plan <verification> are pending for /gsd-verify-work (orchestrator runs them)"

duration: 30min
completed: 2026-10-07
status: complete
plan_head_before: 11a352270aa5b53ac100ffc7c119e07483cd0682
plan_head_after: 7ae548f68dc045b3b5dee60a337c8862ca08ff28
commits: 3
---

# Phase 235 Plan 05: Disagreement Copy, Wait State and Phase Gate Summary

**A server-confirmed disagreement now reads "d4 is the engine's first choice, but your move holds up too." on the guess card for either guess, the bubble says "Taking a closer look…" for exactly as long as the re-check runs, and the phase-wide pre-merge gate is green on both stacks.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 (1 tracer, 1 auto/tdd, 1 auto)
- **Files modified:** 9 (0 created)

## Accomplishments

- `guessFeedbackProse(guess, correctGuess, fromOwnBlunder, moveTier, disagreement, keySan)`: new first guard returns the D-15 line when `disagreement && keySan !== null`; the six locked strings are verbatim and the docstring gained note 4. `TrainReveal` passes `verdict.disagreement ?? false` and the key SAN (`gradeResult.bestMoveUci` on the keyed path IS the server key).
- `RECHECK_COPY = 'Taking a closer look…'`; the grading bubble member is `{ kind: 'grading'; recheck: boolean }` fed by `ResolveBubbleStateInput.isRechecking`; `TrainSolveScreen` sets `isRechecking` only around the `recheckMove` await inside `runRecheck` (cleared in `finally`, reset per puzzle) and renders `train-recheck-indicator` instead of `train-grading-indicator` while it is true.
- CHANGELOG `[Unreleased]` -> Fixed bullet; full pre-merge gate run once with plans 01-05 applied.

## Task Commits

1. **Task 1 (tracer): D-15 guess card line** - `2f2db4c87` (feat)
2. **Task 2: "Taking a closer look…" while the re-check runs** - `9d08cdde5` (feat)
3. **Task 3: CHANGELOG bullet and phase gate** - `7ae548f68` (docs)

Tracer gate (end-of-phase, automated-only verify): the Task 1 verify set (TrainReveal suite, `npm run lint`, `npm run build`) was green before expansion. Tracer verified end-to-end, then expanded.

## Mutation Proofs (each applied, observed red, reverted)

| Mutation | Red result |
| --- | --- |
| Task 1: D-15 guard disabled (`if (false && disagreement && keySan !== null)`) | `a confirmed disagreement names the key for both guesses ...` and `a server-confirmed disagreement renders the D-15 line ...` RED (2 failed) |
| Task 2: `resolveBubbleState` always returns `recheck: false` | `trainBubbleState#grading state carries recheck: true ...`, `TrainSolveScreen#the bubble reads "Taking a closer look…" ...` and the extended `a stalled re-check ... (D-20)` RED (3 failed) |

Suites were green after each revert.

## Gate Results

- Task 1 acceptance: D-15 sentence count in `trainGuessLabels.ts` is 1; each of the six locked strings still appears exactly once; `verdict.disagreement ?? false` matches in `TrainReveal.tsx`.
- Task 2 acceptance: `RECHECK_COPY = 'Taking a closer look…'`, `data-testid="train-recheck-indicator"` and `setIsRechecking(true)` all match. D-05 gate A prints exactly `TrainReveal.tsx`, `TrainSolveScreen.tsx`, `types/train.ts`; gate B prints nothing.
- Backend: `ruff format` (522 files unchanged), `ruff check . --fix`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4` (1158 functions, no breaches), `pytest -n auto -x`: 5352 passed, 19 skipped.
- Frontend: `npm run lint`, `npm run build`, `npm test -- --run` (313 files, 5230 tests), `npm run knip` all exit 0.
- No formatter or lint fixups were needed, so there is no `style(235-05)` commit.

## Deviations from Plan

None - plan executed exactly as written.

The plan allowed the `isRechecking` set/clear to live "in plan 04's helper or inline"; it went into `runRecheck` (the single `recheckMove` await), which is also where the plan's wording points.

## Issues Encountered

- `uv run --project analysis --with ty ty check analysis/` exits 1 on one pre-existing diagnostic, a `deprecated` warning on `@contextmanager` at `analysis/db.py:92` (likely a newer ty release flagging it; the analysis venv resolves `ty` fresh with `--with ty`). The file is untouched by phase 235, so per the scope boundary it was not fixed. Logged here for a follow-up: change the return annotation to `Generator[...]` in `analysis/db.py`.
- The worktree guard refuses compound shell commands (`cd` + git, `$(...)` around git); handled by splitting into plain commands.

## Known Stubs

None.

## Threat Flags

None. T-235-14 (key SAN rendered only post-attempt; D-05 gates A and B pass with every plan applied) and T-235-16 (indicator bounded by the `finally`, per-puzzle reset, verdict precedence and plan 04's timeout; the extended D-20 test asserts it is gone) are covered as planned. No new network surface.

## Pending Browser UAT (for /gsd-verify-work, from the plan `<verification>`)

1. Start a Train session for a dev user; `POST /api/train/sessions` puzzles carry `key_move_uci`, `puzzle_type`, `runner_up_uci`; nothing on the guess screen shows them.
2. Play an SR puzzle: the reveal's best arrow and BEST MOVE box name the key from the payload; on another puzzle, playing the key opens the verdict without the "Checking your move…" indicator.
3. Force a disagreement on the dev DB (sharp blob, `su` a legal move, key kept in `game_positions.best_move`); guess "several", play a third legal move the phone rates close to the key. Expect "Taking a closer look…" for about 6 s, then the D-15 line with the key SAN (both guesses credited) or the normal copy; `drill_solves.recheck` holds the record with `accepted` matching.
4. Play the forced puzzle's `su`: no "Taking a closer look…", the server grades it, `recheck` stays NULL.
5. Optional, device-dependent: user-28 repro numbers via `temp/phase235/probe_budget.mjs` or `frontend/scripts/measure-train-movetime.mjs`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All five phase 235 plans have summaries. Ready for the orchestrator's merge, phase verification and the browser UAT above.

## Self-Check: PASSED

- Modified files exist; commits `2f2db4c87`, `9d08cdde5`, `7ae548f68` are ancestors of HEAD (`git rev-list --count 11a352270..HEAD` = 3 before this SUMMARY).

---
*Phase: 235-train-grading-server-answer-key*
*Completed: 2026-10-07*
