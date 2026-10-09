---
phase: 235-train-grading-server-answer-key
plan: 04
subsystem: ui
tags: [react, typescript, stockfish-wasm, train, grading, recheck, vitest]

requires:
  - phase: 235-train-grading-server-answer-key (plan 02)
    provides: "key-anchored grading hook: GradingAnchor, searchAfterMove, terminalSearchResult, key/legacy anchor"
  - phase: 235-train-grading-server-answer-key (plan 03)
    provides: "server SolveRecheck schema, SolveRequest.recheck, SolveResponse.disagreement"
provides:
  - "frontend/src/lib/trainRecheck.ts: pure shouldRecheck / recheckOutcome / buildRecheckPayload"
  - "useTrainGradingEngine.recheckMove: sequential 3 s + 3 s after-key / after-played re-check with raised node cap and its own timeout, never rejects"
  - "TRAIN_RECHECK_MOVETIME_MS / TRAIN_RECHECK_MAX_NODES / TRAIN_RECHECK_TIMEOUT_MS, per-dispatch maxNodes, RawSearchResult.depth, GradingAnchor.depth / unclamped"
  - "TrainSolveScreen gradeAndSolve: grade -> shouldRecheck -> recheckMove -> POST with recheck"
  - "TS wire types RecheckOutcome, SolveRecheck, SolveRequest.recheck?, SolveResponse.disagreement?"
  - "GatedRecheckWorker test helper (reused by plan 05's wait-copy test)"
affects: [235-05]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Per-dispatch node cap travelling with the queued dispatch (same shape as width/movetime)"
    - "Never-rejecting settle-once race that swaps shared state only in its success branch"
    - "Pure trigger/payload module taking camelCase parameters so the snake_case TrainPuzzle fields stay in one component (D-05)"

key-files:
  created:
    - frontend/src/lib/trainRecheck.ts
    - frontend/src/lib/__tests__/trainRecheck.test.ts
  modified:
    - frontend/src/types/train.ts
    - frontend/src/hooks/useTrainGradingEngine.ts
    - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx

key-decisions:
  - "recheckMoveInner returns the grade/record AND the 3 s anchor; only recheckMove's race success branch installs the anchor, so a re-check that lost the race never changes the reveal"
  - "A generation change during the two re-check searches resolves null (superseded puzzle) before any anchor swap"
  - "Resolved re-check: played line is clamped to the 3 s key line (a no-op unless the played reading exceeds it, which cannot happen for a non-good tier); the 3 s key line still becomes the anchor so the game line clamps to it"
  - "TRAIN_RECHECK_NODE_HEADROOM stays module-local; TRAIN_RECHECK_MOVETIME_MS / MAX_NODES / TIMEOUT_MS exported (the tests import them)"

requirements-completed: [D-10, D-11, D-13, D-16, D-17, D-19, D-20]

coverage:
  - id: D1
    description: "A sharp keyed puzzle's off-key, off-runner-up move that the 1.5 s grade rates good is re-checked (key then played, 3 s each, 8M node cap) before the POST, and the POST carries the full record"
    requirement: "D-10, D-11, D-17, D-19"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#sharp keyed puzzle: an off-key good move is re-checked and the POST carries the record (Phase 235 D-10/D-11/D-17)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#(a) posts exactly two re-check dispatches, the after-key position first ..."
        status: pass
    human_judgment: false
  - id: D2
    description: "Trigger rules: soft, herring, null type/key, played == key, played == runner-up, inaccuracy and wrong never re-check; the sharp runner-up posts no recheck"
    requirement: "D-10, D-19"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRecheck.test.ts#shouldRecheck (D-10, D-19)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#playing the sharp runner-up posts no recheck (D-19)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a soft keyed puzzle posts no recheck (D-10)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Outcome and record: confirmed iff the 3 s tier is good; payload carries the 1.5 s ES/depth pair and the 3 s pair mapped to the snake_case wire keys (null depth -> 0)"
    requirement: "D-13, D-17"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#(b) confirmed ... / (c) resolved ..."
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRecheck.test.ts#buildRecheckPayload (D-17)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A stalled or failed re-check keeps the 1.5 s grade and posts no recheck; a late answer never swaps the anchor; recheckMove never rejects"
    requirement: "D-20"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a stalled re-check falls back to the 1.5 s grade and posts no recheck (D-20)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#(d) a stalled re-check resolves null after TRAIN_RECHECK_TIMEOUT_MS ..."
        status: pass
    human_judgment: false
  - id: D5
    description: "A retried solve re-sends the identical frozen payload (recheck included) and never re-runs the re-check"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a retried solve re-sends the identical payload, recheck included, and never re-runs the re-check (D-17)"
        status: pass
    human_judgment: false
  - id: D6
    description: "After a confirmed re-check the game line is unclamped (honest phone eval); after a resolved one it stays clamped to the 3 s key line"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#(f) after a confirmed re-check ... / (f) after a resolved re-check ..."
        status: pass
    human_judgment: false
  - id: D7
    description: "Ordinary anchor, grade and game-move searches keep the 2M cap; the raised cap survives the stop-queue drain"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts#(g) ... / (h) ..."
        status: pass
    human_judgment: false
  - id: D8
    description: "D-05: the key, type and runner-up are named only in TrainSolveScreen.tsx (dotted puzzle. reads), TrainReveal.tsx and types/train.ts"
    requirement: "D-05"
    verification:
      - kind: other
        ref: "D-05 gate A and gate B greps from the plan (gate A prints the three files, gate B prints nothing)"
        status: pass
    human_judgment: false
  - id: D9
    description: "The re-check behaves in a live browser against a server that sends the key (3 s + 3 s wait, record in drill_solves.recheck)"
    verification: []
    human_judgment: true
    rationale: "Browser UAT is plan 05's, which runs with every phase plan applied (wait copy and D-15 line land there)"

duration: 25min
completed: 2026-10-07
status: complete
plan_head_before: c4a82c1ec0ca8d1b6c25b92703b007ad45bbfeae
plan_head_after: 106a2f144f69ed65936fd3491b74be26107b4ff0
commits: 2
---

# Phase 235 Plan 04: Phone Disagreement Re-check Summary

**A sharp off-key move the 1.5 s phone grade rates good is re-searched at 3 s (key, then played) with an 8M node cap before the solve POST; the deeper verdict replaces the grade, every completed re-check rides the POST as the `recheck` record, and a stall or error silently keeps the 1.5 s grade.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-10-07T18:55:00Z
- **Completed:** 2026-10-07T19:19:00Z
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 7 (2 created)

## Accomplishments

- `trainRecheck.ts` (pure): `shouldRecheck` (sharp + key + off-key + off-runner-up + good), `recheckOutcome` (confirmed iff good), `buildRecheckPayload` (snake_case wire record, `v: 1`, null depth to 0).
- Hook: `maxNodes` travels with every dispatch (QueuedDispatch, readyok drain, stop-queue drain); `RawSearchResult.depth`, `GradingAnchor.depth`; `lastPlayedSearchRef` records the 1.5 s played reading; `recheckMove` runs the two 3 s searches sequentially under `TRAIN_RECHECK_MAX_NODES` (8,000,000) and `TRAIN_RECHECK_TIMEOUT_MS` (12 s), never rejects, and swaps the anchor (3 s key line, `unclamped` when confirmed) only if it won the race.
- `startGameMoveSearch` skips the key clamp when `anchor.unclamped` (D-16).
- `TrainSolveScreen.gradeAndSolve`: grade, then `runRecheck` helper (dotted `puzzle.` reads only), replaces grade and adds `recheck` to the frozen POST body.
- Wire types: `RecheckOutcome`, `SolveRecheck`, `SolveRequest.recheck?`, `SolveResponse.disagreement?`.

## Task Commits

1. **Task 1 (tracer): re-check a sharp off-key good move at 3 s + 3 s and post the record** - `c55e69063` (feat)
2. **Task 2: timeout fallback, honest game line, unit coverage** - `106a2f144` (feat)

Tracer gate (`end-of-phase`, automated-only verify): the Task 1 `<verify>` set (three vitest suites, `npm run lint`, `npm run build`) was re-run green before expansion. Tracer verified end-to-end, then expanded.

## Mutation Proofs (each applied, observed red, reverted; suites green afterwards)

| Mutation | Red result |
| --- | --- |
| a. `shouldRecheck` ignores the runner-up | `trainRecheck.test.ts#never fires for played == runner-up` and `TrainSolveScreen.test.tsx#playing the sharp runner-up posts no recheck (D-19)` RED |
| b. `gradeAndSolve` posts a `buildRecheckPayload` record built from the 1.5 s grade when `recheckMove` resolved null | `a stalled re-check falls back to the 1.5 s grade and posts no recheck (D-20)` RED, plus the runner-up and soft screen tests (they also assert no `recheck` key) |
| c. `startGameMoveSearch` clamps even when `anchor.unclamped` | hook case `(f) after a confirmed re-check, startGameMoveSearch ... unclamped eval` RED |

## Files Created/Modified

- `frontend/src/lib/trainRecheck.ts` - pure trigger, outcome and payload builder
- `frontend/src/lib/__tests__/trainRecheck.test.ts` - trigger matrix, outcome, payload mapping
- `frontend/src/types/train.ts` - `RecheckOutcome`, `SolveRecheck`, `SolveRequest.recheck?`, `SolveResponse.disagreement?`
- `frontend/src/hooks/useTrainGradingEngine.ts` - re-check constants, per-dispatch node cap, depth capture, `recheckMove`, `anchor.unclamped`
- `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts` - describe "disagreement re-check (Phase 235 D-11/D-13/D-16/D-20)", cases (a)-(h)
- `frontend/src/components/train/TrainSolveScreen.tsx` - `runRecheck`, re-check in `gradeAndSolve`, POST `recheck`
- `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx` - tracer, runner-up, soft, D-20 stall, retry tests; `GatedRecheckWorker`; `drop-c2c4` mock button

## Decisions Made

- The anchor swap lives in `recheckMove`'s race success branch (not in the inner worker), so the timeout path cannot change the reveal and a late answer after a timeout is ignored.
- Resolved outcome clamps the played line to the 3 s key line per the plan; that clamp is observably a no-op for a non-good tier (a resolved played reading cannot exceed the key), so the case-(c) assertion checks "not above the key line" and the clamp's visible effect is proven through the game line in case (f).
- Extra tests beyond the behavior block: retry re-sends the identical payload and never re-runs the re-check (D-17), and the raised node cap survives the stop-queue drain (case h).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, test tooling] D-20 screen test cannot use RTL `waitFor` while `setTimeout` is faked**
- **Found during:** Task 2
- **Issue:** RTL's `waitFor` ends with a drain step that waits on a (faked) `setTimeout`; without a `jest` global it never advances, so the test hung until the 20 s test timeout.
- **Fix:** Fake only `setTimeout`/`clearTimeout`, and only after `renderScreen`; drive the flow with `act` + `vi.advanceTimersByTimeAsync(0)` (the FakeWorker answers in microtasks) and assert synchronously.
- **Files modified:** frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
- **Committed in:** 106a2f144

**2. [Process] TDD red-first order not followed for the re-check logic**
- Task 2 is marked `tdd="true"`, but the tracer (Task 1) already shipped the re-check path, and Task 2's behavior tests were written against code that mostly existed. The red evidence was replaced by the three mutation proofs above (each test demonstrably bites). No separate `test(...)` commit exists for Task 2, so a TDD gate audit would flag a missing RED commit; plan type is `execute`, not `tdd`, so no gate is enforced.

**Total deviations:** 1 auto-fixed (test tooling), 1 process note. **Impact:** none on behavior or scope.

## Issues Encountered

- Worktree guard refused compound shell commands (cd + git, heredocs); handled by splitting into plain commands and writing scratch files with the Write tool.

## Known Stubs

None.

## Threat Flags

None. T-235-12 (server revalidates the claim), T-235-13 (own timeout, never rejects, anchor untouched on timeout; GatedRecheckWorker test plus mutation b) and T-235-15 (D-05 gates A and B) are covered as planned. No new network surface (the existing solve POST gains an optional field).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05 can add the `isRechecking` state and "Taking a closer look…" copy around the `runRecheck` await in `gradeAndSolve`, reuse `GatedRecheckWorker` (holds `go movetime 3000 ...` until `release()` or `stop`), and read `verdict.disagreement ?? false` for the D-15 line.
- Between plans 04 and 05 the bubble keeps "Checking your move…" for the whole grade-plus-re-check wait (up to ~6 s extra on the rare sharp disagreement path); both plans ship together.
- Verification run: targeted four suites 176 tests pass; full `npm test -- --run` 313 files / 5223 tests pass; `npm run lint`, `npm run build`, `npm run knip` exit 0.

## Self-Check: PASSED

- Created files exist: `frontend/src/lib/trainRecheck.ts`, `frontend/src/lib/__tests__/trainRecheck.test.ts`.
- Commits `c55e69063` and `106a2f144` are ancestors of HEAD; `git rev-list --count c4a82c1ec..HEAD` = 2 before this SUMMARY.
- Acceptance greps: `export function shouldRecheck|recheckOutcome|buildRecheckPayload` match; `TRAIN_RECHECK_MOVETIME_MS = 3000`, `TRAIN_RECHECK_TIMEOUT_MS = 12000`, ``nodes ${maxNodes}`` match; `recheckMove(` / `shouldRecheck(` match in TrainSolveScreen.tsx; `anchor.unclamped` matches and `TRAIN_RECHECK_TIMEOUT_MS` count is 3; `class GatedRecheckWorker` matches; D-05 gate A prints exactly TrainReveal.tsx, TrainSolveScreen.tsx, types/train.ts and gate B prints nothing.

---
*Phase: 235-train-grading-server-answer-key*
*Completed: 2026-10-07*
