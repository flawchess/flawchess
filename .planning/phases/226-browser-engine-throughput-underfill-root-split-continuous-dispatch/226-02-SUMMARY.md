---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 02
subsystem: engine
tags: [stockfish, mctssearch, node-harness, tooling, profiling, move-quality]

# Dependency graph
requires: []
provides:
  - "scripts/engine-search-trace.mjs — D-13 cBFTV diagnosis tool: per-round expansion/snapshot TSVs from the live mctsSearch, with mechanical bug-signature detection (round-over-concurrency, duplicate-expansion)"
  - "scripts/build-move-quality-fixture.mjs — D-14 widened move-quality fixture builder with a pre-registered, SHA-1-ordered selection rule and a --check verifier"
  - "profile_search.mjs D-17 grade-CPU histogram (root vs non-root x grading depth x candidate-count bucket) and the non_root_gt8_share decision line"
affects: [226-04, 226-05, 226-07]

# Actuals (#2632)
actuals:
  tokens: 15221
  tasks: 3
  commits: 3
plan_head_before: 75a9cf50a49744e6d6e9a2e3ed2e3295a2a09b45
plan_head_after: 9a56e9b348d1be6ce45287b1ca245e8764672fd5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Round-id tracking via a shared mutable counter incremented at the first policy() call after any onSnapshot (mirrors mctsSearch.roundFill.test.ts's own rule) — zero production instrumentation needed"
    - "Edge map (childFen -> {parentFen, uci}) built synchronously at each grade() call's entry, enabling root-to-leaf path reconstruction and duplicate-expansion detection without touching mctsSearch.ts"
    - "SHA-1-ordered, batch-parallel-but-order-decided selection: evaluate a band's candidates in bounded parallel batches for throughput, but walk each batch's results in SHA-1 order and stop at quota — deterministic regardless of engine completion order"
    - "MultiPV rank-keyed (not move-keyed) grade collection for ground-truth evaluation — keying by move would leave stale lower-depth entries for moves that drop out of the top-2 as the search deepens"

key-files:
  created:
    - scripts/engine-search-trace.mjs
    - scripts/build-move-quality-fixture.mjs
  modified:
    - .planning/research/perf-profiling-2026-09-28/profile_search.mjs
    - .planning/research/perf-profiling-2026-09-28/README.md

key-decisions:
  - "No production instrumentation added to mctsSearch.ts or any frontend/src file — the trace tool observes round boundaries purely from the policy()/onSnapshot call sequence, per the plan's own D-12 prohibition"
  - "Ground-truth engine evaluation in build-move-quality-fixture.mjs collects grades by MultiPV rank, not move UCI, to avoid stale cross-depth artifacts in the top-2 (a defect the plan's runOneGo-style move-keyed pattern would have carried over silently)"
  - "profile_search.mjs's existing per-position and TOTAL console output lines are byte-unchanged; only the shared accumulator object literals gained a histogram field, so the 2026-09-28 baseline numbers stay comparable"

requirements-completed: []

coverage:
  - id: D1
    description: "engine-search-trace.mjs traces the live mctsSearch on a fixture position and writes per-round expansion + snapshot TSVs, flagging TRACE-ANOMALY lines for the two D-08 bug signatures"
    requirement: null
    verification:
      - kind: unit
        ref: "scripts/engine-search-trace.mjs --self-test"
        status: pass
      - kind: integration
        ref: "node scripts/engine-search-trace.mjs --ids cBFTV --label smoke --out-dir <tmp> (real mctsSearch + real Stockfish/Maia)"
        status: pass
    human_judgment: false
  - id: D2
    description: "build-move-quality-fixture.mjs builds the widened fixture by a rule fixed in named constants, and --check re-verifies a fixture against the gate's own reader"
    requirement: null
    verification:
      - kind: unit
        ref: "scripts/build-move-quality-fixture.mjs --self-test"
        status: pass
      - kind: integration
        ref: "node scripts/build-move-quality-fixture.mjs --depth 10 --per-band 1 --out <tmp> && node scripts/build-move-quality-fixture.mjs --check <tmp> --min-rows 18"
        status: pass
    human_judgment: false
  - id: D3
    description: "profile_search.mjs records a root vs non-root x grading-depth x candidate-bucket grade-ms histogram and prints the D17 non_root_gt8_share decision line, plus optional JSON output"
    requirement: null
    verification:
      - kind: integration
        ref: "node profile_search.mjs 8 4 4 0 <tmp.json> | grep D17 line; python3 assert JSON histogram+totals present"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 02: Step-0 Diagnostic and Fixture Tooling Summary

**Built the D-13 cBFTV search tracer, the D-14 widened move-quality fixture builder, and the D-17 grade-CPU histogram in profile_search.mjs — the three step-0 instruments that are not gate tools, all proven against the live engine on the current (pre-underfill-fix) checkout.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `scripts/engine-search-trace.mjs`: wraps the real `mctsSearch`'s `policy`/`grade`/`gradeRoot` providers via `makeTracingProviders`, tracking round boundaries with zero production instrumentation (round increments at the first `policy()` call after any `onSnapshot`, exactly mirroring `mctsSearch.roundFill.test.ts`'s documented rule). Writes per-round expansion and snapshot TSVs and prints `TRACE-ANOMALY` lines for the two D-08 bug signatures (`round-over-concurrency`, `duplicate-expansion`). The cBFTV smoke run on the current, pre-underfill-fix checkout confirms the A0 baseline plays `e4c6` — matching `reports/engine-search-fixes-225/report.md`'s finding — so the tool is ready to diff against the A2 candidate once that arm is cherry-picked (Plan 226-04+).
- `scripts/build-move-quality-fixture.mjs`: builds the widened move-quality fixture from `fixtures/tagger/detector_fixture_test.csv`, selecting by a rule fixed in named constants (`PER_BAND_QUOTA=8`, `MIN_GAP_CP=150`, `GROUND_TRUTH_DEPTH=20`, SHA-1-of-PuzzleId ordering) and restated in the output file's own header comment. `--check` reuses `engine-move-quality.mjs`'s own `loadFixtureRows`/`validateFixtureIntegrity` so a generated fixture is read by the gate unchanged. The smoke run (`--depth 10 --per-band 1`) produced 18 rows (12 base + 1 per band × 6 bands) and passed `--check --min-rows 18`; no full-size `fixtures/engine/move-quality-226.tsv` was generated or committed — that d20/8-per-band run is orchestrator work for Plan 226-07.
- `profile_search.mjs` (research script, not a gate tool): extended the grade wrapper with an `is_root × grading_depth × candidate-count-bucket` histogram, printed as aligned rows after the existing `TOTAL` line plus one `D17 non_root_gt8_share=<x.xxx>` decision line, and an optional 6th positional `outJson` argument writing the full histogram + per-position stats + totals as JSON. The existing per-position and `TOTAL` console lines are byte-unchanged, so the 2026-09-28 baseline numbers stay comparable for step-0 re-measurement.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end search trace — wrapped providers to per-round TSVs on cBFTV** - `df86c86dd` (feat)
2. **Task 2: Widened move-quality fixture builder with a pre-committed selection rule** - `22321485e` (feat)
3. **Task 3: D-17 grade-CPU histogram in profile_search.mjs** - `9a56e9b34` (feat)

**Plan metadata:** SUMMARY commit follows this file's own write.

## Files Created/Modified

- `scripts/engine-search-trace.mjs` - D-13 cBFTV diagnosis tool: traces the live mctsSearch's policy/grade/gradeRoot calls into per-round expansion and snapshot TSVs, with mechanical anomaly detection
- `scripts/build-move-quality-fixture.mjs` - D-14 widened move-quality fixture builder with a pre-registered SHA-1-ordered selection rule and a `--check` re-verifier
- `.planning/research/perf-profiling-2026-09-28/profile_search.mjs` - added the D-17 grade-ms histogram and decision line, plus optional JSON output
- `.planning/research/perf-profiling-2026-09-28/README.md` - updated the `profile_search.mjs` table row to document the D-17 addition and the new `outJson` argument

## Decisions Made

- Ground-truth grade collection in `build-move-quality-fixture.mjs` keys by MultiPV rank (1/2), not move UCI — keying by move would let a stale lower-depth entry for a move that later drops out of the top-2 survive into the final map, corrupting the top-move/gap decision. This is a correctness improvement over the naive move-keyed pattern `runOneGo` uses elsewhere (safe there only because `runOneGo`'s MultiPV count always equals its fixed, small `candidateUcis` restriction).
- `engine-search-trace.mjs`'s `makeTracingProviders` signature stays exactly `(providers, rootFen, sink)` per the plan's own contract; the chess.js `Chess` constructor needed for child-FEN computation travels inside `sink.Chess` rather than widening the parameter list, so the caller-supplied `onSnapshot` (which shares the same round-counter state) can be wired directly into `mctsSearch` without a second wrapping layer.
- No file under `frontend/src` was touched in this plan (D-12 honored) — both new CLIs and the profiling script instrument the search purely from the outside, through the `EngineProviders` and `onSnapshot` contracts the app already exposes.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<verify>` commands (self-tests, cBFTV smoke, fixture smoke + check, profiling smoke + JSON assertion) were run verbatim from the plan and passed on the first implementation attempt after fixing one authoring bug caught by `--self-test` itself (see below).

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong SHA-1 test vector in build-move-quality-fixture.mjs's own self-test**
- **Found during:** Task 2, first self-test run
- **Issue:** The self-test asserted `sha1Hex('abc') === 'a9993e364706816aba3e25717850c26c9cd0d89'` — a transcription of the well-known NIST test vector missing its final hex digit (39 chars instead of 40). `sha1Hex` itself was correct throughout; only the test's expected constant was wrong.
- **Fix:** Corrected the expected constant to the full 40-character digest `a9993e364706816aba3e25717850c26c9cd0d89d`, verified independently via `node -e "require('crypto').createHash('sha1').update('abc').digest('hex')"`.
- **Files modified:** scripts/build-move-quality-fixture.mjs
- **Verification:** `--self-test` passes; all 19 self-test assertions green.
- **Committed in:** `22321485e` (Task 2 commit — caught and fixed before the commit was made)

---

**Total deviations:** 1 auto-fixed (1 bug, caught by the tool's own self-test before committing).
**Impact on plan:** None — a test-authoring typo caught and fixed within the same task, before any commit. No scope creep.

## Issues Encountered

None. `frontend/node_modules` was absent in this fresh worktree (`npm ci` had not yet run here); ran `npm ci` in `frontend/` to resolve `chess.js`/`onnxruntime-web`/vendored Stockfish for the self-tests and smoke runs — this is expected fresh-worktree setup (memory note: "Fresh worktree gate needs --group maia-inference"), not a plan deviation, and no `scripts/node_modules` install was needed since neither self-test spawns the native `onnxruntime-node` backend.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The D-13 trace tool is ready to run A0 vs A2 comparisons on `cBFTV` (and the other 11 maia-blindness rows as controls) once the underfill-fix arm is cherry-picked in a later plan (226-04+) — this plan only proved the tool against the current A0-equivalent checkout.
- The D-14 fixture builder is ready for its full-size run (`--depth 20 --per-band 8`, ~55 rows total) from the orchestrator in Plan 226-07, per the plan's own prohibition against running the full-depth generation here.
- The D-17 histogram is ready to run at the accept rule's `50/c4/stop-on` and `400/c4` configurations to answer whether the non-root candidate-cap arm is worth building; this plan's 8-node smoke (`non_root_gt8_share≈0.41`) is a smoke-only number, not the step-0 decision measurement.
- No blockers.

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: scripts/engine-search-trace.mjs
- FOUND: scripts/build-move-quality-fixture.mjs
- FOUND: .planning/research/perf-profiling-2026-09-28/profile_search.mjs
- FOUND: .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-02-SUMMARY.md
- FOUND commit df86c86dd (Task 1)
- FOUND commit 22321485e (Task 2)
- FOUND commit 9a56e9b34 (Task 3)
- FOUND commit 4909708f8 (SUMMARY)
- All three plan-level `<verification>` items re-confirmed: both CLIs' `--self-test` pass; the cBFTV trace smoke and the fixture smoke+check both succeed; the profiling smoke prints the `D17` line.
