---
phase: 168-headless-calibration-harness-spike-gated
plan: 02
subsystem: testing
tags: [nodejs, esm, stockfish, maia, onnxruntime-web, wasm, uci, benchmark, chess]

requires:
  - phase: 168-01
    provides: node-engine-providers.mjs, calibration-providers.mjs (Node EngineProviders), calibration-anchors.mjs, calibration-openings.mjs, CAL-02 parity gate
provides:
  - Bot-vs-anchor game loop driving the LIVE selectBotMove via the @/ alias hook (CAL-02 wiring, deps.search omitted → real mctsSearch)
  - Three D-10 termination cutoffs (chess.js terminal / sustained Stockfish-eval adjudication / hard ply cap) at a FIXED D-11 search budget, all named constants
  - CAL-03 throughput spike (moves/sec + projected full-grid wall-clock + WASM-vs-fallback recommendation)
  - Seeded determinism check (same --seed → byte-identical blend=1 game)
  - D-03 go/no-go decision: full grid infeasible on single-Stockfish WASM path → adopt multi-process Stockfish pool + reduced first grid (feeds Plan 03 re-scope)
affects: [168-03, calibration, bot-play]

tech-stack:
  added: []
  patterns:
    - "Game loop calls live selectBotMove with deps.search omitted so it defaults to real mctsSearch (identical wiring to the app; harness never branches on blend — CAL-02)"
    - "Single shared Stockfish process resets setoption state before every go (grade/anchor/adjudication); SearchBudget.concurrency fixed at 1"
    - "ucinewgame + readyok sync at the start of every playGame() to clear the transposition table between games (determinism)"

key-files:
  created:
    - scripts/lib/calibration-determinism.check.mjs
  modified:
    - scripts/calibration-harness.mjs

key-decisions:
  - "D-03 spike outcome: the full default grid (~59 days on the single-Stockfish WASM path) is INFEASIBLE — grade() serialization inside mctsSearch (not Maia/ONNX) is the bottleneck, so onnxruntime-node would not help. Human go/no-go chose: add a multi-process Stockfish pool first, then run a reduced grid (re-scopes Plan 03)."
  - "Tasks 1 and 2 combined into one commit (e4516272) — the game loop and spike instrumentation interleave in the same functions of a new file."

patterns-established:
  - "CAL-02 no-reimplementation wiring extends to the game loop: bot moves come only from live selectBotMove"
  - "Shared-engine state hygiene: setoption reset before every go, ucinewgame between games"

requirements-completed: [CAL-03, CAL-02]

coverage:
  - id: D1
    description: "Bot-vs-anchor game loop plays ply-by-ply via live selectBotMove, ending on a real terminal / eval-adjudication / ply-cap condition at a fixed budget"
    requirement: CAL-02
    verification:
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs --elo 1500 --blends 0 --anchors sf0 --games-per-cell 1 --seed 1 → result=loss reason=adjudicated_eval plies=40"
        status: pass
    human_judgment: false
  - id: D2
    description: "Seeded determinism: same --seed reproduces a byte-identical blend=1 game"
    requirement: CAL-02
    verification:
      - kind: integration
        ref: "node scripts/lib/calibration-determinism.check.mjs → PASS (identical 27-ply blend=1 game)"
        status: pass
    human_judgment: false
  - id: D3
    description: "CAL-03 throughput spike reports moves/sec + projected full-grid wall-clock + go/no-go recommendation for the most-expensive cell"
    requirement: CAL-03
    verification:
      - kind: manual_procedural
        ref: "spike run + controlled real-engine probes: blend=1 ≈ 173s/move, ~59-day full grid; human go/no-go answered"
        status: pass
    human_judgment: true
    rationale: "The spike is a human go/no-go decision point (D-03) — the throughput number reshapes Plan 03's scope; a human chose the fallback path."

duration: ~39min
completed: 2026-07-11
status: complete
---

# Phase 168 Plan 02: Bot-vs-Anchor Game Loop + CAL-03 Throughput Spike Summary

**Faithful bot-vs-anchor game loop on the live `selectBotMove` with three D-10 cutoffs at a fixed budget, plus the CAL-03 spike that measured the full-Stockfish cell at ~173s/move (~59-day full grid) and gated Plan 03 to a Stockfish-pool + reduced-grid fallback.**

## Performance

- **Duration:** ~39 min (code); spike measurement wall-clock-bound
- **Completed:** 2026-07-11
- **Tasks:** 2 auto + 1 human-verify gate (resolved)
- **Files modified:** 2

## Accomplishments
- Bot-vs-anchor game loop in `scripts/calibration-harness.mjs` driving the LIVE `selectBotMove` (via `@/`), `deps.search` omitted → real `mctsSearch`, `concurrency=1`, shared Stockfish resetting `setoption` before every `go`.
- Three D-10 termination cutoffs (chess.js terminal family / sustained Stockfish-eval adjudication ≥600cp over 4 plies / 120-ply cap) at fixed D-11 budget (`maxNodes=400`, `maxPlies=8`), all named constants.
- CAL-03 throughput spike + determinism check (`calibration-determinism.check.mjs`), proven seed-reproducible after a real transposition-table-leak bug fix.
- **D-03 go/no-go resolved by the human:** full grid infeasible on the current path → adopt multi-process Stockfish pool first, then a reduced grid (re-scopes Plan 03).

## Task Commits

1. **Tasks 1 & 2: Game loop + CAL-03 spike + determinism check** - `e4516272` (feat) — combined; new file, interleaved functions.

## Files Created/Modified
- `scripts/calibration-harness.mjs` - `playGame(...)`, `main()` CLI, D-10 cutoffs, D-11 budget constants, spike instrumentation.
- `scripts/lib/calibration-determinism.check.mjs` - same-seed byte-identity assertion.

## Decisions Made
- **Spike bottleneck attribution:** `grade()` serialization inside `mctsSearch`'s node expansion under a single WASM Stockfish process (`SEARCH_CONCURRENCY=1`) dominates cost (~0.44s/call). NOT Maia/ONNX — so `onnxruntime-node` (D-02's anticipated fallback) would not help.
- **Fallback adopted (human go/no-go):** multi-process Stockfish pool (mirroring `workerPool.ts` slot-queue) + reduced first-grid scope. Passed to Plan 03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Correctness] Transposition table leaked across games broke determinism**
- **Found during:** Task 2 (determinism check)
- **Issue:** The shared Stockfish process's TT was never cleared between games, so two replays of the identical seeded `blend=1` game diverged after ply 2 (game 2's early search hit stale TT entries from game 1).
- **Fix:** Send `ucinewgame` + sync on `readyok` at the start of every `playGame()`.
- **Files modified:** `scripts/calibration-harness.mjs`
- **Verification:** determinism check now passes (identical 27-ply blend=1 game).
- **Committed in:** `e4516272`

---

**Total deviations:** 1 auto-fixed (1 correctness)
**Impact on plan:** Fix was necessary for the D-09 determinism guarantee. No scope creep.

## Issues Encountered
- The literal most-expensive-cell run (`--elo 1900 --blends 1 --anchors sf5 --games-per-cell 4`) would take hours, so throughput was cross-checked via controlled real-engine probes (varying `maxNodes`) plus one confirmed real ply-1 measurement (173.11s), which agreed within 2%.

## Next Phase Readiness
- Plan 03 is **re-scoped by the go/no-go decision:** add a multi-process Stockfish pool (parallelize `grade()`), re-measure throughput, set reduced-grid CLI defaults that fit a bounded wall-clock, then emit the durable raw W/D/L matrix TSV + advisory ELO summary. A full-resolution grid remains a later CLI re-run (not a code change).

---
*Phase: 168-headless-calibration-harness-spike-gated*
*Completed: 2026-07-11*
