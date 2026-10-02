---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 01
subsystem: infra
tags: [stockfish, calibration-harness, node-tooling, determinism, root-split]

# Dependency graph
requires: []
provides:
  - "D-03 no-Clear-Hash warm-hash determinism arm in calibration-determinism.check.mjs, reporting the shipped-config noise floor Phase 227's D-06 and this phase's own D-16 need"
  - "Dormant D-18 gradeRoot fan-out on every calibration-harness grading pool (stockfish-pool.mjs), forwarded through calibration-providers.mjs and calibration-harness.mjs's selectBotMove deps, ready for arm A21S to route to without any further tooling change"
  - "D-08 harness tripwire (rootSplitStats().premiseViolations) proving round-1 sees the whole pool idle"
  - "D-19 PRESET_SUPERVISOR_SEED hook in bin/preset-supervisor.sh, so A0b can run on seed 2"
affects: [227-continuous-dispatch, 226-04, 226-10, 226-12]

# Actuals (#2632)
actuals:
  tokens: 14934
  tasks: 2
  commits: 2
  plan_head_before: 75a9cf50a49744e6d6e9a2e3ed2e3295a2a09b45
  plan_head_after: da07d7178face8c2e70369d7ecbb98289796b6a5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sendObserver-wrapped engine.send() for structural Clear-Hash send spies (never re-parsing engine stdout)"
    - "gradeRoot: dormant optional EngineProviders member wired through every layer (pool -> providers -> harness deps) before the engine ever routes to it, so a later plan's activation touches zero tooling"
    - "splitAcrossFreeEngines: pool-agnostic fan-out helper (freeCount/size/stats/runShard injected) reusable by any harness pool shape, not just stockfish-pool.mjs's own"

key-files:
  created:
    - scripts/lib/stockfish-pool.check.mjs
  modified:
    - scripts/lib/calibration-providers.mjs
    - scripts/lib/stockfish-pool.mjs
    - scripts/lib/calibration-determinism.check.mjs
    - scripts/calibration-harness.mjs
    - bin/preset-supervisor.sh

key-decisions:
  - "ROOT_SPLIT_ABSENT_MESSAGE / ROOT_SPLIT_MODULE_SPECIFIER exported as constants from stockfish-pool.mjs so the check script and the pool never hand-type the same string twice"
  - "Warm arm's adjudication/anchor pool stays a separate Clear-Hash pool (from setupHarnessEngines) — playTwoMoverGame's per-game pool.newGameAll() call never touches the two grading-only pools under measurement"
  - "Warm arm run 2 always applies run 1's recorded move to advance (never its own pick), so both runs see identical positions and any divergence is attributable purely to warm-table scheduling, not to a rng/position drift"

requirements-completed: []

coverage:
  - id: D1
    description: "D-03 no-Clear-Hash warm-hash arm added to calibration-determinism.check.mjs, reporting per-ply divergence and shipped noise floor"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs --no-clear-hash --games 1 --out-dir <tmpdir>"
        status: pass
    human_judgment: false
  - id: D2
    description: "Existing Clear-Hash bit-identity assertions (D-09, STYLE-03/STYLE-05) unchanged and still run by default"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dormant gradeRoot on stockfish-pool.mjs, calibration-providers.mjs, calibration-harness.mjs; k<=1/single-candidate never imports rootSplit"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs"
        status: pass
    human_judgment: false
  - id: D4
    description: "--root-split section exits 3 with 'rootSplit module absent (pre-A21S arm)' before Plan 226-10 lands the module"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs --root-split"
        status: pass
    human_judgment: false
  - id: D5
    description: "bin/preset-supervisor.sh PRESET_SUPERVISOR_SEED hook flows through launch()"
    verification:
      - kind: other
        ref: "bash -n bin/preset-supervisor.sh; grep PRESET_SUPERVISOR_SEED:-1; grep -- --seed \"\\$SEED\""
        status: pass
    human_judgment: false
  - id: D6
    description: "No file under frontend/src changes in this plan"
    verification:
      - kind: other
        ref: "git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src (empty)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 01: Harness Root-Split Plumbing & D-03 Warm-Hash Arm Summary

**Dormant `gradeRoot` fan-out threaded through every calibration-harness grading pool plus a new no-Clear-Hash determinism arm reporting the shipped-warm-hash noise floor — zero frontend/src changes.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-28T07:20:00Z
- **Completed:** 2026-09-28T08:05:00Z
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `calibration-providers.mjs`'s `nodeGrade` gained a `{ clearHash = true }` option; `calibration-determinism.check.mjs` gained a `--no-clear-hash --games N --out-dir DIR` warm arm proving zero `Clear Hash` reaches a grading-only pool and reporting per-ply divergence (mean/max |Δes| re-graded at depth 18) between two independently-warmed pools replaying the same seeded game — this is the shipped-configuration noise floor Phase 227's D-06 tolerance anchors to.
- `stockfish-pool.mjs` gained `freeCount()`, `gradeRoot(fen, candidateUcis, signal, gradingDepth)`, `rootSplitStats()`, and the exported `splitAcrossFreeEngines` fan-out helper — dormant until an A21S engine actually routes a root grade to it (`k <= 1` or a single candidate always takes the plain `grade` path and never imports the not-yet-built `@/lib/engine/rootSplit`).
- `calibration-providers.mjs`'s `makeNodeProviders` and `calibration-harness.mjs`'s `setupHarnessEngines`/`selectBotMoveOnce` forward `gradeRoot` end to end (conditional spread, never a literal `undefined` key), and log a `root-split: calls=.. splits=.. premise_violations=..` line at the end of every run.
- New `scripts/lib/stockfish-pool.check.mjs`: real-engine fast check covering Clear-Hash send discipline, `freeCount()`, dormant `gradeRoot` parity with `grade`, and a `--root-split` section that exits 3 with the exact absent-module message before Plan 226-10 lands `rootSplit.ts`.
- `bin/preset-supervisor.sh` gained `PRESET_SUPERVISOR_SEED` (default 1), threaded through `launch()` for both cold start and crash-resume, enabling D-19's A0b-on-seed-2 run.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end D-03 warm-hash arm — nodeGrade option to a divergence report** - `3f95641d3` (feat)
2. **Task 2: Dormant harness gradeRoot, harness forwarding, tripwire, and the supervisor seed hook** - `da07d7178` (feat)

_Note: a follow-up fix inside Task 2's own commit (the ENOENT vs ERR_MODULE_NOT_FOUND catch) was folded into the Task 2 commit before it landed — see Deviations below._

## Files Created/Modified

- `scripts/lib/calibration-providers.mjs` - `nodeGrade` gains `{ clearHash }`; `makeNodeProviders` gains `gradeRootFn`
- `scripts/lib/stockfish-pool.mjs` - `clearHash`/`sendObserver` pool options, `freeCount()`, `splitAcrossFreeEngines`, `gradeRoot`, `rootSplitStats()`
- `scripts/lib/stockfish-pool.check.mjs` (new) - real-engine fast check, default section (a)-(f) + `--root-split` section
- `scripts/lib/calibration-determinism.check.mjs` - `--no-clear-hash`/`--games`/`--out-dir` flags; warm arm
- `scripts/calibration-harness.mjs` - `gradeRootFn` forwarding, conditional `gradeRoot` deps spread, end-of-run root-split log line
- `bin/preset-supervisor.sh` - `PRESET_SUPERVISOR_SEED` hook

## Decisions Made

- Reused `OPENING_BOOK[0].fen` (the harness's own committed Italian Game position) as the check script's fixed middlegame FEN rather than hand-typing a new one, and derived candidate UCIs from a real `chess.js` legal-move scan rather than hand-picking moves — removes any chance of an illegal `searchmoves` entry being silently dropped by Stockfish (memory note: illegal searchmoves are silently dropped, not rejected).
- `--root-split`'s manual round-robin comparison imports `partitionCandidates`/`mergeShardGrades`/`ROOT_SPLIT_MAX_SHARDS` from the SAME lazily-imported `rootSplit` module `gradeRoot` itself uses, rather than reimplementing round-robin partitioning by hand — guarantees the comparison can never silently drift from the real partitioning scheme once Plan 226-10 lands it.
- Warm arm's regrade (depth 18, mover-POV expected score) reuses the adjudication pool (Clear-Hash, separate from both warm grading pools) rather than spawning a third pool — "a separate Clear-Hash engine" per the plan's own wording, and this pool is already isolated from the two pools under measurement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `splitAcrossFreeEngines`'s absent-module detection missed the actual error Node throws**
- **Found during:** Task 2, verifying the `--root-split` section
- **Issue:** The plan's action text says to catch "a module-not-found error" and named the standard `ERR_MODULE_NOT_FOUND`/`MODULE_NOT_FOUND` codes. `frontend-alias-hook.mjs`'s `@/` resolve branch has no `fs.existsSync` guard (unlike its extensionless-relative branch), so it always returns a URL regardless of whether the target file exists — an absent `rootSplit.ts` therefore fails at the LOAD stage as a raw `ENOENT`, never at resolve. The original catch only matched the two standard codes, so `--root-split` crashed with an uncaught `ENOENT` instead of exiting 3 with the absent-module message.
- **Fix:** Added `err.code === 'ENOENT'` to the catch condition in `splitAcrossFreeEngines` (`stockfish-pool.mjs`), with a comment explaining why the alias hook produces this shape. Kept the original two codes for portability (a caller running without the alias hook, or a future hook fix, would surface the standard code instead).
- **Files modified:** `scripts/lib/stockfish-pool.mjs`
- **Verification:** `stockfish-pool.check.mjs --root-split` now exits 3 and prints `ROOT-SPLIT: rootSplit module absent (pre-A21S arm)`; the default section's `(d)`/`(e)` cases (which never reach this import) were unaffected and still pass.
- **Committed in:** `da07d7178` (part of the Task 2 commit — the ENOENT gap was found and fixed before that commit, never shipped broken)

---

**Total deviations:** 1 auto-fixed (1 bug fix, found and fixed before its introducing commit landed).
**Impact on plan:** Necessary for the `--root-split` section's own acceptance criterion (exit 3 with the named message) to actually hold. No scope creep — same file, same function, no new surface.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every calibration-harness grading pool now carries a dormant, tested `gradeRoot` — Plan 226-10 (the frontend `rootSplit.ts` + `mctsSearch.ts` routing line) can land without touching any file this plan touched.
- The D-03 warm arm is ready for reuse by Phase 227's D-06 accept rule (round-mode vs round-mode warm-hash noise floor) and by this phase's own D-16 root-split grade-content bound (warm-hash comparison point).
- `bin/preset-supervisor.sh`'s `PRESET_SUPERVISOR_SEED` is ready for the step-0 A0a/A0b sweep (D-09/D-19): A0a on the default seed, A0b on `PRESET_SUPERVISOR_SEED=2`.
- No blockers. `frontend/node_modules` was absent in this fresh worktree and required `npm ci` before any `@/`-aliased script could run (memory note: fresh-worktree gate needs `npm ci` per worktree) — done, not carried forward as a blocker.

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `scripts/lib/stockfish-pool.check.mjs`
- FOUND: `.planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-01-SUMMARY.md`
- FOUND: commit `3f95641d3` (Task 1)
- FOUND: commit `da07d7178` (Task 2)
- FOUND: commit `353a646e5` (SUMMARY/plan metadata)
- Re-ran plan-level `<verification>`: `stockfish-pool.check.mjs` default section green (9/9 PASS); `--root-split` exits 3 with the absent-module message; warm arm (`--no-clear-hash --games 1`) completes and reports divergence with zero Clear Hash on both grading pools; `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` is empty.
