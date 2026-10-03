---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 04
subsystem: infra
tags: [stockfish, node-tooling, mobile-pool, root-split, determinism]

# Dependency graph
requires:
  - phase: 226-01
    provides: "splitAcrossFreeEngines fan-out helper + dormant gradeRoot on scripts/lib/stockfish-pool.mjs, and gradeRootFn forwarding in calibration-providers.mjs's makeNodeProviders"
provides:
  - "--pool-size N on engine-grading-depth-ab.mjs, engine-dispatch-stop-rule.mjs, engine-move-quality.mjs (default = --procs), decoupling Stockfish process count from SearchBudget.concurrency (D-04)"
  - "Dormant gradeRoot wiring (via splitAcrossFreeEngines) on all three gate tools, ready for arm A21S to route to without further tooling change (D-18)"
  - "pool_size / root_split_calls columns on every gate TSV; depth-ab additionally records root_split_splits / root_split_premise_violations (D-08)"
  - "engine-grading-depth-ab.mjs --self-test, plus exported BUILTIN_POSITIONS / resolvePositions / parseArgs for reuse by Plan 226-06's content instrument"
  - "engine-move-quality.mjs --self-test --fixture PATH validates a non-default fixture's integrity (D-14 prerequisite)"
affects: [226-06, 226-07, 226-10, 226-12, 227-continuous-dispatch]

# Actuals (#2632)
actuals:
  tokens: 8744
  tasks: 2
  commits: 2
  plan_head_before: af18b25c15592f79bbfc6681dba736fef1652e47
  plan_head_after: 4b1a2c313fa0a6270236769860f6b0593ce9732f

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "--pool-size N (default = --procs) decouples the Stockfish PROCESS pool size from SearchBudget.concurrency in every gate tool, so a mobile-shaped run (concurrency 4 over a 2-worker pool) is measurable without touching the search-concurrency knob"
    - "gradeRootAtDepth/gradeRootAtLadder (depth-ab) and gradeRoot (stop-rule/move-quality via createGradePool) all wrap Plan 226-01's splitAcrossFreeEngines with the pool's own freeCount and a per-pass/per-pool rootSplit stats accumulator -- dormant until mctsSearch routes to providers.gradeRoot at arm A21S"
    - "Per-call/per-row root_split_calls is a DELTA of rootSplitStats().calls taken before/after each mctsSearch invocation, not a running total -- lets a mixed-position TSV attribute a split to the exact row it happened in"

key-files:
  created: []
  modified:
    - scripts/engine-grading-depth-ab.mjs
    - scripts/engine-dispatch-stop-rule.mjs
    - scripts/engine-move-quality.mjs

key-decisions:
  - "gradeRootAtDepth/gradeRootAtLadder declare all four EngineProviders.gradeRoot parameters (fen, candidateUcis, signal, depth) even where the fixed-depth variant never reads depth itself -- matches the harness provider-signature convention (RESEARCH) so a future 4th-arg caller can never be silently truncated by parameter position"
  - "root_split_calls is reported as a delta of the pool's rootSplitStats().calls counter, computed before/after each row's mctsSearch call, rather than exposing the running total directly -- keeps the column meaningful in a multi-position/multi-row TSV"
  - "engine-move-quality.mjs's runSelfTest now takes an optional fixturePath parameter (default DEFAULT_FIXTURE); the non-default-fixture integrity check and 'fixture rows=<n>' print only fire when the resolved path differs from the resolved default, so the unchanged 12-row default-fixture check always still runs unconditionally"

patterns-established:
  - "Pool-size vs concurrency decoupling: any future gate tool wiring a Stockfish pool should expose --pool-size (default --procs) rather than reusing --procs for both roles"

requirements-completed: []

coverage:
  - id: D1
    description: "engine-grading-depth-ab.mjs accepts --pool-size N (default = --procs), --self-test with no engines spawned, and exports BUILTIN_POSITIONS/resolvePositions/parseArgs"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs --self-test"
        status: pass
    human_judgment: false
  - id: D2
    description: "depth-ab one-position --pool-size 2 smoke writes TSV rows with pool_size=2 and root_split_calls=0 (split dormant before A21S), plus root_split_splits/root_split_premise_violations columns"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs --nodes 8 --depths 14 --ladder --procs 4 --pool-size 2 --fens <one.fens> --out-dir <tmp> (TSV verified via python csv.DictReader)"
        status: pass
    human_judgment: false
  - id: D3
    description: "engine-dispatch-stop-rule.mjs and engine-move-quality.mjs both accept --pool-size N; createGradePool returns gradeRoot()/rootSplitStats(); both self-tests pass including new pool-size default/explicit/invalid cases"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test && node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test"
        status: pass
    human_judgment: false
  - id: D4
    description: "engine-move-quality.mjs --self-test --fixture PATH exits 0 and both tools' source contains gradeRootFn wiring"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test --fixture fixtures/engine/maia-blindness.tsv && grep -q gradeRootFn scripts/engine-move-quality.mjs && grep -q gradeRootFn scripts/engine-dispatch-stop-rule.mjs"
        status: pass
    human_judgment: false
  - id: D5
    description: "concurrency: args.procs unchanged in engine-move-quality.mjs; no frontend/src file changed by this plan"
    verification:
      - kind: other
        ref: "grep -n \"concurrency: args.procs\" scripts/engine-move-quality.mjs; git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src (empty)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 04: Gate Tool Mobile-Pool & Dormant Root-Split Wiring Summary

**`--pool-size N` (decoupled from `--procs`) plus a dormant `gradeRoot` fan-out landed on all three engine gate tools (depth-ab, stop-rule, move-quality), with `pool_size`/`root_split_calls` provenance columns on every TSV — zero frontend/src changes.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-28T07:51:00Z
- **Completed:** 2026-09-28T08:16:11Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `engine-grading-depth-ab.mjs` gained `--pool-size N` (default = `--procs`), a no-engine `--self-test` (unknown-flag, pool-size default/explicit/invalid, `--openings` resolution, `makeGradeStats().rootSplit` zero-state), and exported `BUILTIN_POSITIONS`/`resolvePositions` for Plan 226-06's content instrument to reuse directly.
- `createDepthPool` gained `gradeRootAtDepth`/`gradeRootAtLadder` closures wrapping `splitAcrossFreeEngines` (Plan 226-01) over the pool's own `freeCount` and each pass's `stats.rootSplit` accumulator — wired into both the flat and ladder `makeNodeProviders(..., { gradeRootFn })` calls, dormant until `mctsSearch` routes a root grade to `providers.gradeRoot` at arm A21S.
- `engine-dispatch-stop-rule.mjs`'s `createGradePool(size)` now also returns `gradeRoot(fen, candidateUcis, signal, depth)` (WR-05 empty-candidates guard first, then `splitAcrossFreeEngines`) and `rootSplitStats()`; the main loop sizes the pool by `--pool-size`, keeps `concurrency: args.procs`, and appends `pool_size` + per-position `root_split_calls` delta columns to its TSV.
- `engine-move-quality.mjs` gained the same `--pool-size` flag, wired `{ gradeRootFn: pool.gradeRoot }` into its providers, and appended `pool_size`/per-row `root_split_calls` columns. Its `runSelfTest` now accepts an optional fixture path: when `--fixture` differs from the default, it loads and validates that fixture too (printing `fixture rows=<n>`), while the unchanged 12-row default-fixture check still always runs.
- Both `engine-dispatch-stop-rule.mjs` and `engine-move-quality.mjs` self-tests extended with `--pool-size` default/explicit/invalid cases.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end mobile-pool throughput slice — depth-ab `--pool-size 2` to a TSV row** - `b82e87078` (feat)
2. **Task 2: `--pool-size` and dormant gradeRoot in the stop-rule and move-quality tools** - `4b1a2c313` (feat)

**Plan metadata:** (pending — final metadata commit follows this SUMMARY)

## Files Created/Modified

- `scripts/engine-grading-depth-ab.mjs` — `--pool-size`, `--self-test`, `gradeRootAtDepth`/`gradeRootAtLadder`, 4 new trailing TSV columns, exported `BUILTIN_POSITIONS`/`resolvePositions`
- `scripts/engine-dispatch-stop-rule.mjs` — `--pool-size`, `createGradePool` gains `gradeRoot`/`rootSplitStats()`, 2 new trailing TSV columns, extended self-test
- `scripts/engine-move-quality.mjs` — `--pool-size`, `gradeRootFn` wiring, 2 new trailing TSV columns, self-test accepts `--fixture` path for non-default integrity validation

## Decisions Made

- `gradeRootAtDepth`/`gradeRootAtLadder` declare all four `EngineProviders.gradeRoot` parameters even where the fixed-depth variant never reads `depth` itself, matching the harness provider-signature convention so a future 4th-argument caller can never be silently truncated by parameter position.
- `root_split_calls` is reported as a delta of `rootSplitStats().calls` taken immediately before/after each row's `mctsSearch` call (not the running total), so the column stays meaningful across a multi-position or multi-row TSV.
- `engine-move-quality.mjs`'s `runSelfTest` takes an optional `fixturePath` parameter (default `DEFAULT_FIXTURE`); the extra non-default-fixture check and `fixture rows=<n>` print fire only when the resolved path differs from the resolved default, so the required unchanged 12-row default check always still runs unconditionally.

## Deviations from Plan

None — plan executed exactly as written. All three tools' verification commands (self-tests, the depth-ab pool-2 smoke, the `--self-test --fixture` command, both `gradeRootFn` grep checks, the `concurrency: args.procs` grep check, and the empty `frontend/src` diff) passed on first attempt with no fix-up needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three gate tools (`engine-grading-depth-ab.mjs`, `engine-dispatch-stop-rule.mjs`, `engine-move-quality.mjs`) can now measure the mobile pool-of-2 configuration (bot budget at concurrency 4, analysis budget at concurrency 2) independently of search concurrency, satisfying D-04's gating mobile measurement requirement.
- Every gate tool's `gradeRoot` is dormant and provenance-tracked (`pool_size`, `root_split_calls`, and for depth-ab also `root_split_splits`/`root_split_premise_violations`) — a future arm A21S run through these same tools will show a nonzero `root_split_calls` the instant `mctsSearch.ts` routes a root grade to `providers.gradeRoot` (Plan 226-10), with no further tooling change required.
- `engine-grading-depth-ab.mjs`'s exported `BUILTIN_POSITIONS`/`resolvePositions`/`parseArgs` are ready for Plan 226-06's content instrument to import directly.
- No blockers. `frontend/node_modules` was absent in this fresh worktree and required `npm ci` before any `@/`-aliased script could run (memory note: fresh-worktree gate needs `npm ci` per worktree) — done, not carried forward as a blocker.

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `scripts/engine-grading-depth-ab.mjs`
- FOUND: `scripts/engine-dispatch-stop-rule.mjs`
- FOUND: `scripts/engine-move-quality.mjs`
- FOUND: `.planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-04-SUMMARY.md`
- FOUND: commit `b82e87078` (Task 1)
- FOUND: commit `4b1a2c313` (Task 2)
- Re-ran plan-level `<verification>`: `engine-grading-depth-ab.mjs --self-test` (6/6 checks pass), `engine-dispatch-stop-rule.mjs --self-test` (18/18 checks pass), `engine-move-quality.mjs --self-test` (11/11 checks pass); depth-ab `--pool-size 2` one-position smoke writes a TSV with `pool_size=2` and `root_split_calls=0` on both rows (verified via `csv.DictReader`); `engine-move-quality.mjs --self-test --fixture fixtures/engine/maia-blindness.tsv` exits 0; `grep -q gradeRootFn` matches in both `engine-move-quality.mjs` and `engine-dispatch-stop-rule.mjs`; `grep -n "concurrency: args.procs" scripts/engine-move-quality.mjs` still matches; `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` is empty.
