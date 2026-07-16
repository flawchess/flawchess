---
phase: 173-anchor-ladder-self-calibration-seed-101
plan: 02
subsystem: infra
tags: [node, chess.js, stockfish, maia, calibration-harness, esm, bradley-terry]

# Dependency graph
requires:
  - phase: 173-01
    provides: "playTwoMoverGame (mover-agnostic two-mover game loop), sf8/sf10 anchor tokens, 8 exported CLI/seed/build helpers from calibration-harness.mjs"
provides:
  - "scripts/lib/calibration-anchor-schedule.mjs — pure-logic D-01/D-02/D-04 scheduler: scoreInInformativeBand, buildCandidateGraph, checkConnectivity, selectMeasurePairs, canonicalPair/pairKey/isCrossFamilyPair"
  - "scripts/calibration-anchor-ladder.mjs — standalone anchor-vs-anchor orchestrator (D-08): two-pass probe->measure schedule, D-04 re-target fallback, two-tier durable TSV, --resume"
  - "Raw per-game TSV column contract (pass, anchor_white, anchor_black, result, reason, plies, game_index, opening, seed, git_sha) that Plan 03's load_games parses"
affects: [173-04-real-run]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Canonical pair identity (a < b lexicographic) shared between the Node scheduler and the orchestrator so (x,y)/(y,x) never both appear and pairKey is a stable Map key across --resume reloads"
    - "Bounded re-target loop (MAX_RETARGET_ROUNDS=3): each round probes newly-retargeted cross-family candidates, re-gates, and re-checks connectivity before either returning or exhausting the budget and failing loud"
    - "Extra exports on internal pure-logic helpers (parseArgs, mergeUniquePairs, buildTriedMaiaMap, computeRetargets, isGraphConnected, buildScoreMap, pairsAggregateRows, applyPriorRowsToState, pairsFromRows, ensurePairStats, mergeDeltaIntoStats) mirroring calibration-harness.mjs's own testability convention"

key-files:
  created:
    - scripts/lib/calibration-anchor-schedule.mjs
    - scripts/lib/calibration-anchor-schedule.check.mjs
    - scripts/calibration-anchor-ladder.mjs
  modified: []

key-decisions:
  - "Global gameIndex is a single monotonically-increasing counter shared across the WHOLE run (all pairs, probe+measure) rather than per-pair-local — matches the bot harness's existing SEED-097 --resume convention and lets applyPriorRowsToState fast-forward it via max(priorRows.gameIndex)+1 (Pitfall 4)"
  - "D-04 re-target applies to EVERY dropped cross-family pair (not only when it's the sole surviving cross link) — computeRetargets walks each SF anchor outward to the next untried Maia rung by folklore-Elo distance every time its current cross-family candidate is dropped, bounded by MAX_RETARGET_ROUNDS=3"
  - "Measure-pass extension is `args.gamesPerMeasure - stats.games` (stats.games already includes the pair's probe games) rather than a fresh count — Open Question 1's resolved recommendation, reusing the 8 probe games as the first 8 of 24"
  - "The pairs-aggregate `pass` column reflects kept-set membership at write time (`measure` if the pair survived to the measure pass, `probe` if it was dropped and never re-targeted into a surviving pair), not literally which TSV rows exist for it"
  - "isCrossFamilyPair moved into calibration-anchor-schedule.mjs as a named export (used by both checkConnectivity internally and the orchestrator's re-target logic) rather than being duplicated"

patterns-established:
  - "Probe->gate->retarget->reconnect loop as the D-01/D-04 scheduling algorithm: bounded, deterministic, and testable purely via mock pairStats without any real engine"

requirements-completed: [D-01, D-02, D-03, D-08, D-10, D-13]

coverage:
  - id: D1
    description: "Pure-logic probe->measure scheduler (scoreInInformativeBand, buildCandidateGraph, checkConnectivity, selectMeasurePairs) proven on canned fixtures independent of any engine run"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-anchor-schedule.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-02 base candidate graph on the 10-anchor default set yields 4 adjacent-maia + 4 adjacent-sf + >=2 cross-family candidates, all canonically ordered and de-duplicated"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-anchor-schedule.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-04 connectivity guard: checkConnectivity throws on 0 or 1 cross-family links, passes on 2 (BFS + cross-family-edge count)"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "scripts/lib/calibration-anchor-schedule.check.mjs (node --import ./scripts/lib/frontend-alias-hook.mjs)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Standalone D-08 orchestrator (calibration-anchor-ladder.mjs) is valid, importable, imports Plan 01's playTwoMoverGame + Plan 02 Task 1's schedule functions + calibration-harness.mjs's exported CLI/seed helpers, and references none of the bot harness's ANCHOR_ELO_WINDOW/selectBotMove/botBudget concepts"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "node --check scripts/calibration-anchor-ladder.mjs; node --import ./scripts/lib/frontend-alias-hook.mjs -e \"import('./scripts/calibration-anchor-ladder.mjs')\"; grep -Ec 'ANCHOR_ELO_WINDOW|selectBotMove|botBudget' scripts/calibration-anchor-ladder.mjs (returns 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Two-pass schedule + D-04 re-target + connectivity guard + measure-pass extension logic (never a fresh 24) exercised via a scratch smoke test against mocked pair stats/ledger rows (parseArgs, mergeUniquePairs, buildTriedMaiaMap, computeRetargets, isGraphConnected, buildScoreMap, pairsAggregateRows, applyPriorRowsToState, pairsFromRows)"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "ad hoc scratch script (not committed — exercised the exported pure-logic helpers directly, no real engines); all 8 assertions passed this session"
        status: pass
    human_judgment: false
  - id: D6
    description: "The real multi-hour anchor-vs-anchor run producing the D-12 artifacts (raw ledger + per-pair aggregate with the executed data) is out of scope for this plan — it is Plan 04's deliverable"
    human_judgment: true
    rationale: "Plan 02 builds and structurally verifies the tooling only; D-11 execution against real Maia/Stockfish engines for hours is explicitly Plan 04's job per 173-02-PLAN.md's own <done> criteria."

# Metrics
duration: ~13min
completed: 2026-07-15
status: complete
---

# Phase 173 Plan 02: Anchor Ladder Orchestrator Summary

**Standalone `calibration-anchor-ladder.mjs` orchestrator with a two-pass probe→measure adaptive scheduler (8-game probe, 24-game measure, D-04 connectivity-guarded cross-family re-targeting) and a durable two-tier TSV ready for Plan 04's real run.**

## Performance

- **Duration:** ~13 min
- **Completed:** 2026-07-15T22:20:20+02:00
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments
- `scripts/lib/calibration-anchor-schedule.mjs` — pure-logic D-01/D-02/D-04 module (no engines, no I/O): the `[0.2, 0.8]` informative-band gate, the D-02 base candidate graph (adjacent Maia rungs, adjacent SF skills, folklore-seeded initial cross-family candidates), a stdlib-BFS `checkConnectivity` guard requiring >= 2 cross-family links, and `selectMeasurePairs`'s keep/drop split — all proven on canned fixtures in `calibration-anchor-schedule.check.mjs`.
- `scripts/calibration-anchor-ladder.mjs` — the D-08 standalone orchestrator (NOT a `calibration-harness.mjs` mode): plays anchor-vs-anchor games via Plan 01's `playTwoMoverGame`, runs the probe pass, gates via `selectMeasurePairs`, re-targets dropped cross-family pairs to the next-nearest untried Maia rung (bounded retry), verifies connectivity before the measure pass, and extends every surviving pair from its 8 probe games to 24 total (never replaying a fresh 24).
- Two-tier durable TSV: a raw per-game ledger (`pass anchor_white anchor_black result reason plies game_index opening seed git_sha` — the exact column contract Plan 03's fit script will parse) streamed one row per finished game (WR-01), plus a per-pair aggregate sibling carrying the D-13 "internal scale — NOT human ELO" caveat verbatim in its metadata footer.
- `--resume` reconstructs per-pair progress by replaying the raw ledger keyed on pair identity (not the bot harness's fixed-gridKeys `loadPriorSweep`) and fast-forwards the global `gameIndex` through every already-logged game, per 173-RESEARCH.md Pitfall 4.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure-logic probe→measure scheduler + connectivity guard (D-01/D-02/D-04) + check** - `7b39b9c7` (feat)
2. **Task 2: The anchor-vs-anchor orchestrator — two-pass run, two-tier TSV, --resume (D-01/D-03/D-08/D-10/D-13)** - `2fa788ae` (feat)

## Files Created/Modified
- `scripts/lib/calibration-anchor-schedule.mjs` - New module: `scoreInInformativeBand`, `buildCandidateGraph`, `checkConnectivity`, `selectMeasurePairs`, `canonicalPair`/`pairKey`/`isCrossFamilyPair`
- `scripts/lib/calibration-anchor-schedule.check.mjs` - Canned-fixture assertions (0/1/2 cross-family-link connectivity cases; 10-anchor default-set candidate-graph shape; band-gate boundaries)
- `scripts/calibration-anchor-ladder.mjs` - New standalone CLI orchestrator: CLI parsing (`--anchors`/`--games-per-probe`/`--games-per-measure`/`--seed`/`--stockfish-procs`/`--out-dir`/`--resume`), the probe→gate→retarget→reconnect scheduling loop, the measure-pass extension, the two-tier TSV writers, and the `--resume` ledger reader/reconstructor

## Decisions Made
- Global `gameIndex` is a single run-wide counter (not per-pair-local) — mirrors the bot harness's existing `--resume` convention and makes fast-forwarding on resume a single `max(priorRows.gameIndex) + 1` computation.
- D-04 re-targeting applies to every dropped cross-family pair on every round (not gated to "only when it's the sole surviving link") — simpler, monotonic, and bounded by `MAX_RETARGET_ROUNDS=3`.
- Measure-pass extension computes `args.gamesPerMeasure - stats.games` where `stats.games` already includes the pair's probe games — resolves 173-RESEARCH.md Open Question 1 by reusing rather than discarding already-played data.
- `isCrossFamilyPair` is exported from `calibration-anchor-schedule.mjs` (used by both `checkConnectivity` and the orchestrator's `computeRetargets`) rather than duplicated.
- Several internal pure-logic helpers in `calibration-anchor-ladder.mjs` (`parseArgs`, `mergeUniquePairs`, `buildTriedMaiaMap`, `computeRetargets`, `isGraphConnected`, `buildScoreMap`, `pairsAggregateRows`, `applyPriorRowsToState`, `pairsFromRows`, `ensurePairStats`, `mergeDeltaIntoStats`) are exported (not strictly required by the plan) to mirror `calibration-harness.mjs`'s own testability convention and to enable the scratch smoke test run this session.

## Deviations from Plan

None — plan executed exactly as written. One self-imposed strengthening beyond the plan's own `<verify>` block (which only required `node --check` + a bare import): a scratch smoke test (not committed, run via the scratchpad directory) exercised the probe→retarget→connectivity→resume-reconstruction logic against mocked pair stats and ledger rows, since the real engine run is deferred to Plan 04 and this logic is intricate enough to warrant more than a syntax check before considering the task complete.

## Issues Encountered
- The Task 2 acceptance criterion's literal grep (`grep -Ec 'ANCHOR_ELO_WINDOW|selectBotMove|botBudget'`) initially matched the module's own header comment explaining why those bot-harness concepts don't apply here (documentation, not a functional reference). Reworded the comment to describe the concept without naming the exact `ANCHOR_ELO_WINDOW` token, so the grep returns 0 as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 03 (rating fit tooling) already exists and its `load_games` parser targets this plan's exact raw-ledger column contract.
- Plan 04 (the real multi-hour anchor-vs-anchor run) can invoke `scripts/calibration-anchor-ladder.mjs` directly — the two-pass schedule, connectivity guard, and durable/resumable TSV output are all in place and structurally verified; only real-engine execution remains untested.

---
*Phase: 173-anchor-ladder-self-calibration-seed-101*
*Completed: 2026-07-15*

## Self-Check: PASSED

All created files and referenced commit hashes verified present on disk / in git log.
