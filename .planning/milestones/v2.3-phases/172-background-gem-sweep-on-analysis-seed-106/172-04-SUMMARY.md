---
phase: 172-background-gem-sweep-on-analysis-seed-106
plan: 04
subsystem: analysis
tags: [gem-sweep, maia, stockfish, react, typescript, worker-scheduler]

# Dependency graph
requires:
  - phase: 172-02
    provides: "gemSweep.ts: selectSweepCandidates (D-04 free prefilter) + nextSweepDispatch (D-05 yield-to-cursor scheduler decision)"
provides:
  - "useStockfishGradingEngine: optional movetimeMs option, defaulting to the existing GRADING_MOVETIME_SAFETY_CAP_MS (live instances unaffected)"
  - "workerPool.ts: exported isLowPowerDevice(), extracted from computePoolSize()'s inline mobile heuristic"
  - "useGemSweep hook: dedicated Maia + Stockfish grading worker instances, the D-04 cascade, and the D-05 yield-to-cursor scheduler"
affects: [172-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedicated worker instances (never shared with the live path) as the structural fix for single-in-flight-slot hooks — mirrors useFlawChessEngine.ts's established precedent"
    - "requestIdleCallback with a setTimeout(cb, 1) fallback for idle-time scheduling — first use of this pattern in the repo"
    - "Two-layer liveBusy gate: nextSweepDispatch decides whether to SCHEDULE, a ref re-check inside the idle callback decides whether to COMMIT (covers the race where the cursor moves between scheduling and execution)"

key-files:
  created:
    - frontend/src/hooks/useGemSweep.ts
    - frontend/src/hooks/__tests__/useGemSweep.test.ts
  modified:
    - frontend/src/hooks/useStockfishGradingEngine.ts
    - frontend/src/lib/engine/workerPool.ts

key-decisions:
  - "Dedicated worker instances chosen over migrating onto workerPool.ts's existing (unused, unit-tested) priority queue — dispatchNext() only assigns pending work to IDLE slots and never preempts an in-flight low-priority slot, so priority alone would not satisfy 'never starve the live position' under saturation. Dedicated instances make starvation structurally impossible, at the cost of one extra Worker thread."
  - "SWEEP_GRADING_MOVETIME_MS set to 1000ms — roughly the live free-run's own MOVETIME_MS order of magnitude, deliberately smaller than the live grading path's 4000ms cap. The sweep has no deadline; C2's comparison is a large expected-score gap (MISTAKE_DROP), not a fine one, so a shallower search still resolves it correctly."
  - "Yield semantics deviate from RESEARCH.md's suggestion to abort in-flight sweep work on every cursor change: the sweep yields ONLY at the dispatch gate (never starts new work while the live path is busy) and tolerates an already-started candidate finishing, since dedicated workers mean an in-flight sweep search occupies no resource the live path needs. Aborting continuously would prevent the sweep from ever finishing against a user stepping briskly through the mainline."
  - "Two-layer liveBusy gate (scheduler-level nextSweepDispatch call + idle-callback ref re-check) rather than a single check — the re-check specifically covers the race where liveBusy flips true between an idle callback being scheduled and it actually running."

requirements-completed: []

coverage:
  - id: D1
    description: "useStockfishGradingEngine accepts an optional movetimeMs, defaulting to GRADING_MOVETIME_SAFETY_CAP_MS; searchmoves stays the last go clause; the two live instances are unaffected"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts (11 tests, all green, unmodified)"
        status: pass
    human_judgment: false
  - id: D2
    description: "workerPool.ts's isLowPowerDevice() extracted from computePoolSize()'s inline mobile heuristic — one heuristic, two consumers, behavior-preserving refactor"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts (33 tests, all green, unmodified)"
        status: pass
    human_judgment: false
  - id: D3
    description: "useGemSweep drives dedicated useMaiaEngine/useStockfishGradingEngine instances (never the live path's), running the D-04 cascade (free prefilter already done by caller -> Maia C1 -> Stockfish C2) with the D-05 yield-to-cursor scheduler"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useGemSweep.test.ts (11 tests, all green)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-05 yield-to-cursor invariant proven red-then-green at the hook layer by bypassing both the scheduler's nextSweepDispatch liveBusy input AND the idle-callback's ref re-check simultaneously"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useGemSweep.test.ts#LOAD-BEARING (D-05 yield-to-cursor invariant): with liveBusy true, the sweep's Maia instance is driven with fen: null; flipping liveBusy to false dispatches the first candidate"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-07-14
status: complete
---

# Phase 172 Plan 04: Background Gem Sweep Cascade Hook Summary

**`useGemSweep` — a background gem-resolution hook driving dedicated Maia + Stockfish worker instances through the D-04 free→cheap→expensive cascade, gated by a D-05 yield-to-cursor scheduler proven red-then-green at the hook layer.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-14
- **Tasks:** 3
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments

- `useStockfishGradingEngine` gained an optional `movetimeMs` option (default `GRADING_MOVETIME_SAFETY_CAP_MS = 4000`), mirrored into a ref so `prepareSearch`'s stable `useCallback([])` can read it without breaking the stable-capture contract the worker's bestmove/visibility handlers depend on. `searchmoves` stays the final clause of the `go` command (the WASM build's trailing-keyword-swallowing quirk). Both live instances (`Analysis.tsx`'s `grading`/`gemGrading`) are byte-for-byte unaffected.
- `workerPool.ts`'s mobile heuristic extracted into an exported `isLowPowerDevice()`, with `computePoolSize()` now calling it — one heuristic, two consumers (pool sizing and the sweep's device gate), behavior-preserving.
- New `frontend/src/hooks/useGemSweep.ts`: drives its OWN `useMaiaEngine` + `useStockfishGradingEngine` instances (never `Analysis.tsx`'s `maia`/`grading`/`gemGrading`), running the cascade one candidate at a time — Maia C1 at the candidate's caller-supplied pinned rung, then (on a C1 pass) Stockfish C2 at `SWEEP_GRADING_MOVETIME_MS = 1000`. The `nextSweepDispatch` scheduler decision (from plan 02) gates every new dispatch through a `requestIdleCallback`/`setTimeout(cb, 1)` fallback, re-checked against the latest `liveBusy`/`enabled` refs immediately before committing. Results land in `gemByPly`, a map bounded by `candidates.length` and deliberately never FIFO-capped like `Analysis.tsx`'s shared 256-entry caches.
- 11 new unit tests in `useGemSweep.test.ts`, including a genuine red-then-green revert proof of the D-05 yield invariant performed at the hook layer (see below).

## Task Commits

Each task was committed atomically:

1. **Task 1: A tunable grading movetime + a single shared low-power-device heuristic** - `ba524c00` (feat)
2. **Task 2: `useGemSweep` — dedicated workers, the D-04 cascade, the D-05 scheduler** - `adfaecca` (feat)
3. **Task 3: Hook-level contention, isolation, and cache-bound tests** - `9019ffc6` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/hooks/useGemSweep.ts` - new hook: `SweepGemDetail`, `UseGemSweepOptions`, `UseGemSweepState`, `SWEEP_GRADING_MOVETIME_MS`
- `frontend/src/hooks/__tests__/useGemSweep.test.ts` - 11 new unit tests (Wave 0 gap from 172-VALIDATION.md)
- `frontend/src/hooks/useStockfishGradingEngine.ts` - new optional `movetimeMs` option
- `frontend/src/lib/engine/workerPool.ts` - new exported `isLowPowerDevice()`

## Decisions Made

- Dedicated worker instances over `workerPool.ts`'s priority-queue migration — recorded in the plan's own objective and reaffirmed here: `dispatchNext()` only assigns to idle slots, never preempts an in-flight low-priority one, so priority alone does not satisfy "never starve the live position" under saturation.
- `SWEEP_GRADING_MOVETIME_MS = 1000` — see frontmatter `key-decisions` for the full rationale (roughly the live free-run's own movetime order of magnitude; the sweep has no deadline and C2's comparison tolerates a shallower search).
- Yield-at-dispatch-only semantics (no abort-on-cursor-change for in-flight sweep work) — documented in the hook's own header doc-comment, citing the `useFlawChessEngine.ts` precedent for the Maia tier ("a stale policy() resolution is unused and harmless") and extending the same tolerance to the sweep's Stockfish tier, since dedicated workers make an in-flight sweep search resource-free with respect to the live path.
- Two-layer `liveBusy` gate (scheduler decision + idle-callback ref re-check) — the re-check specifically covers the scheduling-to-execution race; discovered necessary during the Task 3 revert-proof exercise (see Issues Encountered).

## Deviations from Plan

None - plan executed exactly as written. (The two-layer `liveBusy` gate was already part of the Task 2 implementation as written — the plan's action text explicitly calls for "Re-check `liveBusy` and `enabled` from refs INSIDE the idle callback before setting `inFlight`" alongside the scheduler's own `nextSweepDispatch` gate, so this is not a deviation, just a design detail that shaped how the Task 3 revert-proof had to be performed.)

## Issues Encountered

While performing the Task 3 mandatory revert-proof, bypassing only the scheduler effect's `nextSweepDispatch({ liveBusy, ... })` input (hardcoding it to `false`) was NOT sufficient to turn the yield test red — the idle-callback's own re-check (`if (!liveBusyRef.current && effectiveEnabledRef.current)`) still correctly blocked the dispatch, because it reads the REAL `liveBusy` ref, independent of the bypassed scheduler input. This is a genuine defense-in-depth feature (per the plan's action text), not a test bug, but it meant the revert-proof had to bypass BOTH gates simultaneously to demonstrate what a real regression removing the invariant would look like. Resolved by bypassing both, confirming RED, then restoring both and confirming GREEN (see evidence below). The test itself was also adjusted to `await` past the idle-callback's real `setTimeout(cb, 1)` window before asserting `fen: null`, since a purely synchronous assertion right after mount would pass even with the gate removed (no timer could have fired yet).

## Revert-Proof Evidence (D-05 yield-to-cursor invariant, hook layer)

Per the plan's mandatory Task 3 instructions, the hook's `liveBusy` gate was temporarily bypassed at BOTH enforcement points — the scheduler effect's `nextSweepDispatch({ liveBusy: false /* bypass */, ... })` call and the idle-callback's `if (!liveBusyRef.current && ...)` re-check (changed to `if (effectiveEnabledRef.current)`) — the test suite was run to confirm RED, then both were restored and the suite re-run to confirm GREEN. Grep/symbol-presence was NOT used as evidence.

**RED (both `liveBusy` gates bypassed):**

```
 ❯ src/hooks/__tests__/useGemSweep.test.ts (11 tests | 1 failed) 653ms
     × LOAD-BEARING (D-05 yield-to-cursor invariant): with liveBusy true, the sweep's Maia instance is driven with fen: null; flipping liveBusy to false dispatches the first candidate 64ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/hooks/__tests__/useGemSweep.test.ts > useGemSweep > LOAD-BEARING (D-05 yield-to-cursor invariant): with liveBusy true, the sweep's Maia instance is driven with fen: null; flipping liveBusy to false dispatches the first candidate
AssertionError: expected 'fen-0' to be null

- Expected:
null

+ Received:
"fen-0"

 ❯ src/hooks/__tests__/useGemSweep.test.ts:163:33
    161|     // timer callback can fire before control returns to this line.
    162|     await new Promise((resolve) => setTimeout(resolve, 50));
    163|     expect(lastMaiaCall()?.fen).toBeNull();
       |                                 ^
    164|     expect(lastMaiaCall()?.enabled).toBe(true); // engineEnabled: cand…
    165|

 Test Files  1 failed (1)
      Tests  1 failed | 10 passed (11)
```

**GREEN (both gates restored):**

```
 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 Test Files  1 passed (1)
      Tests  11 passed (11)
   Duration  1.53s (transform 68ms, setup 0ms, import 139ms, tests 749ms, environment 512ms)
```

`git diff -- frontend/src/hooks/useGemSweep.ts` confirmed empty after restoration — no bypass code was left behind.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `useGemSweep` is committed and unit-tested, exporting `SWEEP_GRADING_MOVETIME_MS = 1000` for plan 05 and UAT to reference. `UseGemSweepOptions` intentionally has no slider/`selectedElo` field — plan 05 must supply `candidates` (plan 02's `selectSweepCandidates` output), `pinnedEloForPly` (per-mover pinned rungs, likely via the exported `deriveRawDefault`/`clampToLadderBounds`), `liveBusy` (derived from `Analysis.tsx`'s existing `needParentGemGrade`/grading-in-flight state), and `userColor`.
- `gemByPly`'s value shape (`SweepGemDetail`) mirrors `Analysis.tsx`'s private `GemDetail` type exactly, so plan 05's display merge (sweep-resolved gems ∪ the live per-node `gemByNode` resolution) should be a straight union with no field mapping needed.
- Full plan-level verification passed: `npm test -- --run src/hooks/__tests__/useGemSweep.test.ts` (11/11 green, including the recorded red-then-green revert proof), `npm test -- --run src/hooks/__tests__ src/lib/engine/__tests__` (453/453 green, no regressions), `npx tsc -b --noEmit` (zero errors), `npm run lint` (clean, only pre-existing `coverage/` directory warnings), `npm run knip` (clean).
- No blockers.

---
*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 5 claimed files found on disk; all 3 task commit hashes (ba524c00, adfaecca, 9019ffc6) found in git log.
