---
phase: 172-background-gem-sweep-on-analysis-seed-106
plan: 02
subsystem: analysis
tags: [gem-sweep, maia, chess-analysis, react, typescript, scheduler]

# Dependency graph
requires:
  - phase: 172-01
    provides: "opening_ply_count on GameFlawCard (backend + frontend types)"
provides:
  - "GEM_MAIA_MAX_PROB raised 0.1 -> 0.2 (D-07)"
  - "deriveRawDefault / clampToLadderBounds exported from useMaiaEloDefault.ts (D-01)"
  - "gemSweep.ts: selectSweepCandidates (D-04 free prefilter) + nextSweepDispatch (D-05 yield-to-cursor scheduler decision)"
affects: [172-04, 172-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure, worker-free scheduler decision function (nextSweepDispatch) — proves the yield-to-cursor invariant without mocking React/Workers"
    - "SAN-vs-UCI conversion before comparison (sanToUci) as the mandatory idiom for matching played moves against EvalPoint.best_move"

key-files:
  created:
    - frontend/src/lib/gemSweep.ts
    - frontend/src/lib/__tests__/gemSweep.test.ts
  modified:
    - frontend/src/lib/gemMove.ts
    - frontend/src/lib/__tests__/gemMove.test.ts
    - frontend/src/hooks/useMaiaEloDefault.ts
    - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts

key-decisions:
  - "GEM_MAIA_MAX_PROB set to exactly 0.2 per D-07, with the doc-comment recording the Phase 165 TSV ratios (not absolute frequencies) as the calibration basis"
  - "selectSweepCandidates uses strict best_move equality (no es-loss band) — fails safe on backend/live-engine disagreement, per D-04"
  - "nextSweepDispatch checks liveBusy FIRST, before any candidate lookup, making the yield-to-cursor guard structurally unbypassable rather than merely tested"

requirements-completed: []

coverage:
  - id: D1
    description: "GEM_MAIA_MAX_PROB raised to 0.2; a 0.15-probability move with passing C2 now classifies as a gem"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/gemMove.test.ts#D-07 (Phase 172): a maiaProbability of 0.15 with a passing C2 now classifies as a gem"
        status: pass
    human_judgment: false
  - id: D2
    description: "deriveRawDefault/clampToLadderBounds exported and proven structurally independent of the Elo slider for a fixed mover"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts#D-01 regression: setSelectedElo does NOT perturb deriveRawDefault for a fixed mover"
        status: pass
    human_judgment: false
  - id: D3
    description: "selectSweepCandidates free prefilter — SAN-vs-UCI conversion, book-ply gate, strict best_move equality, ascending-order output"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/gemSweep.test.ts#selectSweepCandidates (all 7 cases)"
        status: pass
    human_judgment: false
  - id: D4
    description: "nextSweepDispatch yield-to-cursor scheduler decision, proven red-then-green by manually deleting and restoring the liveBusy guard"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/gemSweep.test.ts#nextSweepDispatch LOAD-BEARING (D-05 yield-to-cursor invariant) case"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-07-14
status: complete
---

# Phase 172 Plan 02: Background Gem Sweep Primitives Summary

**Raised `GEM_MAIA_MAX_PROB` to 0.2 (D-07), exported the mover-pinned rating helpers from `useMaiaEloDefault.ts` (D-01), and shipped `gemSweep.ts` — a pure, worker-free free-prefilter (D-04) and yield-to-cursor scheduler decision (D-05) with a manually-recorded red-then-green revert proof.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-14
- **Tasks:** 3
- **Files modified:** 6 (2 new, 4 modified)

## Accomplishments

- `GEM_MAIA_MAX_PROB` raised from 0.1 to 0.2, doc-comment records the Phase 165 calibration TSV ratios (x1.35 at Maia-600, ~1.8x at 2200-2600, Elo skew narrows 3.8x -> 2.9x), stale `toBe(0.1)` pin test updated to `0.2` in the same commit, plus a new behavioral proof case (0.15 probability + passing C2 now classifies as a gem).
- `deriveRawDefault` and `clampToLadderBounds` promoted from module-private to exported in `useMaiaEloDefault.ts`, with a new direct-call test `describe` block proving: per-mover rung derivation (white vs black differ from the same `gameData`), null-when-not-loaded, ladder clamping without step-snapping, and — the load-bearing D-01 regression case — that `setSelectedElo` never perturbs `deriveRawDefault`'s result for a fixed mover.
- New `frontend/src/lib/gemSweep.ts`: `selectSweepCandidates` (D-04 free prefilter, converts played SAN to UCI via `sanToUci` before comparing to `EvalPoint.best_move`, gates on `openingPlyCount`, strict equality fails safe) and `nextSweepDispatch` (D-05 pure scheduler decision — `liveBusy` checked before any candidate lookup, single in-flight candidate, `idle`/`done`/`dispatch` outcomes). Zero React/Worker imports. 16 new unit tests in `gemSweep.test.ts`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Raise `GEM_MAIA_MAX_PROB` to 0.2 (D-07)** - `6640b7dd` (feat)
2. **Task 2: Export the rating-pin helpers (D-01)** - `cb95433d` (feat)
3. **Task 3: `gemSweep.ts` — free prefilter (D-04) + yield-to-cursor scheduler decision (D-05)** - `63820b67` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/lib/gemSweep.ts` - new pure module: `SweepCandidate`, `selectSweepCandidates`, `SweepDispatchInput`/`SweepDispatch`, `nextSweepDispatch`
- `frontend/src/lib/__tests__/gemSweep.test.ts` - 16 new unit tests (Wave 0 gap from VALIDATION.md)
- `frontend/src/lib/gemMove.ts` - `GEM_MAIA_MAX_PROB` 0.1 -> 0.2, doc-comment updated with calibration rationale
- `frontend/src/lib/__tests__/gemMove.test.ts` - stale 0.1 pin updated to 0.2, new 0.15-probability behavioral case added
- `frontend/src/hooks/useMaiaEloDefault.ts` - `deriveRawDefault`/`clampToLadderBounds` exported (no other behavior change)
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` - new direct-call `describe` block (5 cases) covering the D-01 contract

## Decisions Made

- `GEM_MAIA_MAX_PROB` set to exactly 0.2, with the caveat about the Phase 165 TSV's enriched sample (ratios transfer, absolute frequencies do not) recorded in the doc-comment for future readers.
- Export-in-place (minimal diff) chosen over extracting `deriveRawDefault`/`clampToLadderBounds` to a shared module — matches the plan's stated minimal-diff preference and PATTERNS.md's analog.
- `selectSweepCandidates` uses strict `best_move` equality rather than an es-loss band, per D-04's explicit fail-safe design: losing a rare gem on backend/live-engine disagreement is preferable to inventing one.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Revert-Proof Evidence (D-05 yield-to-cursor invariant)

Per the plan's acceptance criteria, the `liveBusy` guard in `nextSweepDispatch` was manually deleted, the test suite was run to confirm RED, then the guard was restored and the suite re-run to confirm GREEN. Grep/symbol-presence was NOT used as evidence — this is the actual revert-and-fail-red proof.

**RED (guard removed — `if (liveBusy) return { kind: 'idle' };` commented out):**

```
 ❯ src/lib/__tests__/gemSweep.test.ts (16 tests | 1 failed) 28ms
     × LOAD-BEARING (D-05 yield-to-cursor invariant): returns idle when liveBusy is true, even with unresolved candidates present and nothing in flight — deleting the liveBusy guard MUST turn this test red 10ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/lib/__tests__/gemSweep.test.ts > nextSweepDispatch > LOAD-BEARING (D-05 yield-to-cursor invariant): returns idle when liveBusy is true, even with unresolved candidates present and nothing in flight — deleting the liveBusy guard MUST turn this test red
AssertionError: expected { kind: 'dispatch', …(1) } to deeply equal { kind: 'idle' }

- Expected
+ Received

  {
-   "kind": "idle",
+   "candidate": {
+     "parentFen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
+     "playedSan": "Nf3",
+     "plyIndex": 4,
+   },
+   "kind": "dispatch",
  }

 Test Files  1 failed (1)
      Tests  1 failed | 15 passed (16)
```

**GREEN (guard restored):**

```
 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 Test Files  1 passed (1)
      Tests  16 passed (16)
   Duration  241ms
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `GEM_MAIA_MAX_PROB`, the exported rating-pin helpers, and `gemSweep.ts`'s two pure primitives are all committed and unit-tested — ready for plan 04 (the `useGemSweep` orchestration hook) and plan 05 (wiring into `Analysis.tsx`) to consume directly.
- Full plan-level verification passed: `npm test -- --run src/lib/__tests__/gemSweep.test.ts src/lib/__tests__/gemMove.test.ts src/hooks/__tests__/useMaiaEloDefault.test.ts` (57 tests, all green), `npx tsc -b --noEmit` (zero errors), `npm run lint` (clean, only pre-existing `coverage/` directory warnings unrelated to this plan), `npm run knip` (clean).
- No blockers. Note for plan 04/05: `nextSweepDispatch` and `selectSweepCandidates` are intentionally consumer-agnostic — plan 04's hook must supply `fenAtPly`, `resolvedPlyIndices`, `liveBusy`, and `tabHidden` from real state, none of which exist yet.

---
*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 7 claimed files found on disk; all 4 commit hashes (6640b7dd, cb95433d, 63820b67, 8bc4dd1b) found in git log.
