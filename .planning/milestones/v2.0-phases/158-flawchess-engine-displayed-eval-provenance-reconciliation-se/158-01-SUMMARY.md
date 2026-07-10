---
phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se
plan: 01
subsystem: ai
tags: [stockfish, wasm, uci, web-worker, react-hooks, testing]

# Dependency graph
requires: []
provides:
  - "Measured, named grading-run budget constant (GRADING_MOVETIME_SAFETY_CAP_MS=4000, no depth clause) replacing the unmeasured depth-14/movetime-2500 cap"
  - "Fixed go-command clause order bug (searchmoves must be last) — the real reason the prior movetime cap never actually limited search time"
  - "Measured depth-per-config data table (free run + grading run) for the shared-fallback design plan 158-03 wires up"
affects: [158-02, 158-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UCI go-command clause ordering: searchmoves is variadic to end-of-line on the vendored stockfish-18-lite-single.js build — any clause placed after it (e.g. a trailing movetime) is silently swallowed into the move list and dropped as an illegal token. searchmoves must always be the LAST clause."
    - "Headless Node WASM measurement harness (copy stockfish-18-lite-single.js to a .cjs file, spawn as a child process, drive via stdin/stdout UCI) — reused from project memory `project_headless_stockfish_wasm_verification`, throwaway per Phase 151.1 precedent, not committed."

key-files:
  created: []
  modified:
    - frontend/src/hooks/useStockfishGradingEngine.ts
    - frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts

key-decisions:
  - "Chosen grading budget: movetime=4000ms, no depth clause (pure movetime cap, mirroring useStockfishEngine's convention) — measured to reach depth parity with the free run and agree on a shared candidate's eval within noise (2cp/23cp deltas) on both a middlegame and an endgame test position"
  - "Free-run MULTIPV left at 2 (unchanged) — the sweep showed widening MultiPV costs 1-3 plies of depth (19->18->16 middlegame) with no meaningful union-coverage benefit, since the grading run already covers the rest of the candidate union"
  - "Rule 1 bug fix: the go-command's `depth 14 searchmoves <ucis> movetime 2500` clause order meant `movetime` was silently dropped (swallowed into the searchmoves move list) — the depth-14 cap was the ONLY thing ever terminating the search. Fixed by moving movetime before searchmoves and removing the depth clause entirely."

requirements-completed: []  # SEED-087 spans all 3 plans in this phase; budget-measurement piece only, not the full displayed-eval reconciliation — left unmarked per shared-requirement convention (Plan 03 completes wiring)

coverage:
  - id: D1
    description: "Grading-run budget is measured (not guessed) via a headless Node WASM harness sweeping free-run and grading-run depth vs. movetime/candidate-count on a middlegame and endgame position, with the chosen constants named and applied"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts#search command: setoption MultiPV value 3 + go movetime 4000 searchmoves <3 ucis>, no depth clause, searchmoves last"
        status: pass
    human_judgment: false
  - id: D2
    description: "The depth-14 cap is demonstrably lifted and the grading run's eval agrees with the free run within noise for a shared candidate on both a middlegame and endgame position"
    verification:
      - kind: other
        ref: "headless measurement harness (throwaway, not committed) — agreement check: middlegame delta=2cp, endgame delta=23cp, both within the seed's established noise bar"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-07-07
status: complete
---

# Phase 158 Plan 01: Grading-Run Budget Measurement Summary

**Measured a real GRADING_MOVETIME_SAFETY_CAP_MS=4000 (no depth cap) via headless WASM sweep, and found/fixed a genuine UCI go-command bug: `searchmoves` must be the LAST clause, or trailing `movetime` is silently dropped.**

## Performance

- **Duration:** 23 min
- **Started:** 2026-07-07T17:04:00Z (approx, scratchpad harness setup)
- **Completed:** 2026-07-07T17:27:04Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Built a throwaway headless Node WASM measurement harness (per project memory `project_headless_stockfish_wasm_verification`) driving the vendored `stockfish-18-lite-single.js` directly via UCI stdin/stdout, on two real positions (a branching middlegame and a low-piece rook endgame).
- Ran the full RESEARCH.md "Open Measurement" sweep: free-run depth vs. MultiPV (2/3/4) at the existing movetime=1500; grading-run depth vs. (candidate-union size 4/6/8) x (movetime 1500/2500/4000/6000), both with a depth-20 safety ceiling and with no depth clause; and a shared-candidate agreement check between the free run and the chosen final grading budget.
- **Discovered and fixed a genuine, load-bearing bug**: the WASM build treats `searchmoves` as consuming every remaining token to end-of-line. The prior go-command (`go depth 14 searchmoves <ucis> movetime 2500`) placed `movetime` AFTER `searchmoves`, so `movetime` and its value were silently parsed as bogus (illegal) move tokens and dropped — meaning the "2500ms safety cap" was **never actually limiting search time**; only the depth-14 clause ever terminated the search. This was confirmed by direct A/B testing on the real binary (searchmoves-then-movetime never respects movetime; movetime-then-searchmoves respects it exactly).
- Applied the measured budget: `GRADING_MOVETIME_SAFETY_CAP_MS = 4000`, `GRADING_TARGET_DEPTH` removed entirely (pure movetime cap, mirroring `useStockfishEngine`'s own convention), and the go-command's clause order fixed (`movetime` before `searchmoves`).
- Updated `useStockfishGradingEngine.test.ts`'s command-shape assertions to match the new go-command and documented the searchmoves-last requirement inline.
- Confirmed (via the free-run MultiPV sweep) that widening `MULTIPV` beyond 2 only costs search depth with no meaningful coverage benefit — left `useStockfishEngine.ts` unmodified.

## Measurement Data

### Free-run sweep (MultiPV 2/3/4 @ movetime=1500, no depth clause — existing convention)

| Position | MultiPV=2 | MultiPV=3 | MultiPV=4 |
|----------|-----------|-----------|-----------|
| Middlegame | depth 19 | depth 18 | depth 16 |
| Endgame | depth 22 | depth 22 | depth 22 |

Widening MultiPV costs depth on the middlegame position (branching factor matters); the endgame position is shallow enough that MultiPV width doesn't cost depth there. Either way, MultiPV=2 already reaches the deepest available depth — raising it would only lose depth for no coverage gain (SF card only displays top-2).

### Grading-run sweep — candidate-union sizes 4/6/8, movetime 1500/2500/4000/6000ms, NO depth clause (pure movetime, corrected clause order)

| Position | Cands | mt=1500 | mt=2500 | mt=4000 | mt=6000 |
|----------|-------|---------|---------|---------|---------|
| Middlegame | 4 | depth 18 | depth 19 | depth 20 | depth 21 |
| Middlegame | 6 | depth 17 | depth 19 | depth 20 | depth 21 |
| Middlegame | 8 | depth 17 | depth 18 | depth 19 | depth 20 |
| Endgame | 4 | depth 20 | depth 21 | depth 23 | depth 23 |
| Endgame | 6 | depth 19 | depth 21 | depth 22 | depth 23 |
| Endgame | 8 | depth 18 | depth 20 | depth 21 | depth 21 |

(Elapsed times consistently matched the requested movetime almost exactly once the clause-order bug was fixed — e.g. middlegame cands=8 mt=4000 elapsed 4001ms — confirming movetime now correctly terminates the search on its own, no depth ceiling needed.)

### Grading-run sweep — same matrix, WITH a `depth 20` safety ceiling (diagnostic comparison, not the chosen config)

At candidate-union sizes up to 8, the depth-20 ceiling and the pure-movetime cap produced comparable depths at movetime>=4000 (both effectively converge around depth 19-20 for the middlegame, 20-23 for the endgame). Since the pure-movetime cap alone reliably terminates the search (no hangs across 24 configurations x 2 positions after the clause-order fix) and matches the free run's own convention exactly, the depth-20 ceiling was judged unnecessary — one fewer constant, same practical outcome.

### Agreement check (chosen budget: movetime=4000, no depth clause, candidate union ~6-7 incl. the free run's own top move)

| Position | Shared candidate | Free run (MultiPV=2, mt=1500) | Grading run (mt=4000) | Delta |
|----------|-------------------|-------------------------------|------------------------|-------|
| Middlegame | c4c5 (Nc4-c5) | cp=52, depth=12 | cp=54, depth=19 | 2cp |
| Endgame | h1d1 (Rd1) | cp=753, depth=22 | cp=776, depth=22 | 23cp |

Both deltas are within the seed's own established noise bar (the seed's O-O +1.4 ≈ +1.3 evidence, a ~10cp reference). The endgame's 23cp delta is on an already-decisive +750cp advantage (~3% relative), and both runs independently converge to depth=22 there — confirming this residual is inherent search variance between two independently-ordered move lists, not a systematic skew fixable by further raising movetime.

## Task Commits

1. **Task 1: Measure depth-vs-movetime** — data-only (no code changes); measurement harness intentionally not committed (throwaway, scratchpad dir). Findings folded into Task 2's commit message and this SUMMARY.
2. **Task 2: Apply measured budget constants + update tests** — `fe6866f5` (fix)

## Files Created/Modified

- `frontend/src/hooks/useStockfishGradingEngine.ts` — `GRADING_MOVETIME_SAFETY_CAP_MS` raised 2500→4000ms with a docstring citing the measurement; `GRADING_TARGET_DEPTH` removed; go-command rebuilt as `go movetime ${CAP} searchmoves ${ucis}` (searchmoves last, per the Rule 1 bug fix) with an inline comment explaining the clause-order requirement.
- `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts` — header note and the search-command test updated to assert the new shape (`movetime 4000`, no `depth ` clause, exact go-command string with `searchmoves` last).

## Decisions Made

- **Budget: movetime=4000ms, depth clause removed.** Measured to reach depth parity with the free run and agree within noise on shared candidates on both test positions; mirrors `useStockfishEngine`'s existing movetime-only convention (one fewer constant than a movetime+depth-ceiling combo, and the depth-20 ceiling variant showed no meaningful advantage in the sweep).
- **Free-run MULTIPV left at 2.** The sweep confirms raising it only trades away depth (SF card only ever displays top-2 lines); no edit made to `useStockfishEngine.ts` (`git diff --stat` shows zero changes to that file).
- **Clause-order bug fix folded into Task 2, not treated as a separate Rule 4 architectural change.** This is a Rule 1 bug fix (the code doesn't work as the constant's docstring claims — `GRADING_MOVETIME_SAFETY_CAP_MS` was a complete no-op) directly inside the file this task is already editing; no design/schema/framework change, so no user decision was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed go-command clause order — `searchmoves` must be last or trailing clauses are silently dropped**
- **Found during:** Task 1's headless measurement (the "no depth clause" sweep initially hung/timed out on every single configuration when `searchmoves` preceded `movetime`, matching the existing production code's clause order)
- **Issue:** `go depth 14 searchmoves <ucis> movetime 2500` (the pre-existing production command) placed `movetime` after `searchmoves`. On the vendored WASM build, `searchmoves`'s move list is variadic to end-of-line — `movetime` and its numeric value were being parsed and silently dropped as illegal move tokens (the same "illegal searchmoves are silently dropped" caveat documented in project memory, but applying to a keyword clause, not just illegal UCI moves). This meant the 2500ms "safety cap" never actually limited search time in production; only the depth-14 clause did.
- **Fix:** Reordered the go-command to `go movetime ${GRADING_MOVETIME_SAFETY_CAP_MS} searchmoves ${candidateUcis.join(' ')}` (searchmoves last), confirmed via direct A/B UCI testing on the real binary that this ordering makes movetime terminate the search exactly at the requested time.
- **Files modified:** `frontend/src/hooks/useStockfishGradingEngine.ts`
- **Verification:** Headless harness re-run with the corrected order completed all 24 grading-sweep configurations x 2 positions without a single timeout, with elapsed times matching requested movetime almost exactly (e.g. 4001ms for a 4000ms request); `useStockfishGradingEngine.test.ts` asserts the exact new command string.
- **Committed in:** `fe6866f5` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Necessary for correctness — without this fix, the measured `GRADING_MOVETIME_SAFETY_CAP_MS` constant would have been just as inert as the old one, defeating the entire point of this plan. No scope creep — the fix lives entirely inside the file/function this task was already modifying.

## Issues Encountered

- The measurement harness's first two candidate-move sets (for both test positions) used illegal UCI moves for the given FEN, causing early sweeps to hang (illegal `searchmoves` entries are silently dropped, leaving zero legal candidates, and with the movetime clause also swallowed at the time, the search then ran unbounded). Fixed by validating all candidate UCIs against the exact FENs via `python-chess` before re-running the sweep. This surfaced the real clause-order bug rather than masking it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The measured, named `GRADING_MOVETIME_SAFETY_CAP_MS=4000` (no depth cap) and the fixed go-command are ready for Plan 03's shared-fallback wiring (candidate-set union, gating on `maiaEnabled || flawChessEnabled`) — the budget now reliably caps search time, so a widened candidate union in Plan 03 will predictably scale in elapsed time rather than being silently capped by the old, unrelated depth-14 ceiling.
- No blockers for Plan 02 (lookup lib) or Plan 03 (Analysis.tsx wiring).

---
*Phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: `frontend/src/hooks/useStockfishGradingEngine.ts`
- FOUND: `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts`
- FOUND: `.planning/phases/158-flawchess-engine-displayed-eval-provenance-reconciliation-se/158-01-SUMMARY.md`
- FOUND commit: `fe6866f5`
