---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 04
subsystem: engine-harness
tags: [node, gate-scripts, dispatch-mode, move-quality, throughput, abort-signal, event-loop-lag]

requires:
  - phase: 227-01
    provides: "abort-aware Node Stockfish pool (run(fn, signal, abortValue), whenIdle) and worker-thread Maia"
  - phase: 227-02
    provides: "scripts/lib/dispatch-mode.mjs (parseDispatchModeFlag, defaultDispatchMode, assertDispatchModeLive) and FLAWCHESS_DISPATCH_MODE"
  - phase: 227-03
    provides: "verdict twin column contract (dispatch_mode, repeat, hash_mode, maia_fifo, grade_cpu_ms)"
provides:
  - "All four gate scripts take --dispatch-mode round|continuous (default = app constant), probe it live before any engine starts (exit 3 for continuous until Plan 227-10) and stamp it into every TSV"
  - "engine-move-quality.mjs: --repeats N, --maia-fifo, --hash warm|clear, in-process judge memo, quiesced+reset pool per (row, repeat)"
  - "createGradePool(size, { clearHash }) with abort-forwarding grade/gradeRoot, whenIdle() and gradeCpuMs()"
  - "engine-dispatch-stop-rule.mjs: grade_cpu_ms, loop_lag_max_ms, root_split_premise_violations columns; startLoopLagProbe()"
  - "engine-grading-depth-ab.mjs: --ladder-only, abort-forwarding wrappers, dispatch_mode and loop_lag_max_ms columns"
affects: [227-05, 227-07, 227-08, 227-11, 227-12]

plan_head_before: cb82bf558f50333e574f9f646ae446f08257f3a1
plan_head_after: d836b2059fe4cabb880671b34ede4505fd26127e

actuals:
  tokens: 17500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Mode flags are code-path switches proven by assertDispatchModeLive before any engine bring-up"
    - "New TSV columns are appended at the END so 226 readers and the 227 tripwire parse old and new files"
    - "Pool quiescence (await pool.whenIdle()) before every timed position/pass"
    - "Event-loop lag read after a settle wait (the histogram records a stall only after it ends)"

key-files:
  created: []
  modified:
    - scripts/engine-move-quality.mjs
    - scripts/engine-dispatch-stop-rule.mjs
    - scripts/engine-grading-depth-ab.mjs
    - scripts/engine-search-trace.mjs

key-decisions:
  - "Judge memo is keyed on the full nodeGrade call content (fen|pick|correct|depth), not per uci, because MultiPV set size can change a grade; a hit is then exactly content-identical (nodeGrade clears hash per call)"
  - "loop_lag_max_ms uses monitorEventLoopDelay as the plan says, but reads it after a 20 ms settle wait and subtracts the 10 ms sampling period (naive read-after-search missed a 300 ms stall: read 10 ms)"
  - "Pool-level grade_cpu_ms is the engine-go elapsed of settled grades (never queue wait, retried attempts not double counted), the same definition as depth-ab's makeGradeStats"

requirements-completed: []

coverage:
  - id: D1
    description: "MQ gate selects the dispatch mode in one checkout with repeats, FIFO Maia and warm/clear hash, probes the mode live (exit 3 for continuous) and stamps dispatch_mode/repeat/hash_mode/maia_fifo"
    verification:
      - kind: command
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test"
        status: pass
      - kind: command
        ref: "engine-move-quality.mjs --arm smoke --stop-rule on --dispatch-mode round --repeats 2 --maia-fifo (12-row fixture): 24 rows, columns present, repeats 1 and 2, mode round"
        status: pass
      - kind: command
        ref: "engine-move-quality.mjs --dispatch-mode continuous exits 3"
        status: pass
    human_judgment: false
  - id: D2
    description: "Round-mode MQ repeats agree on bot_move for every fixture id (the plan's smoke assertion)"
    verification:
      - kind: command
        ref: "same smoke: PASSED on the first run, FAILED on a later run because cBFTV flips between e4c6 and e2g4 (see Issues Encountered)"
        status: fail
    human_judgment: true
    rationale: "cBFTV flips in round mode about 9 to 11 percent of in-process repeats regardless of this plan's changes; whether the twin's hard round-determinism invalidation is the right rule is a Plan 227-08/09 decision"
  - id: D3
    description: "Stop-rule, depth-ab (ladder-only) and search-trace measure the selected mode on quiesced pools with report-only CPU and loop-lag columns"
    verification:
      - kind: command
        ref: "all three --self-test pass; stop-rule smoke STOP-SMOKE OK 5 rows; ladder-only smoke LADDER-SMOKE OK 5 rows; search-trace round smoke writes dispatch_mode column"
        status: pass
      - kind: command
        ref: "stop-rule, depth-ab, search-trace each exit 3 with --dispatch-mode continuous"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 04: Gate scripts as one-checkout, two-arm instruments Summary

**All four gate scripts now run either dispatch arm from one checkout behind a live probe (continuous exits 3 until Plan 227-10), with MQ repeats, app-faithful Maia, warm/clear hash, a judge memo, ladder-only throughput runs, report-only CPU and event-loop columns, and abort-aware quiesced grade pools.**

## Accomplishments

- **Task 1 (tracer): MQ arms in one checkout.** `engine-move-quality.mjs` gained `--dispatch-mode` (default `defaultDispatchMode()`, probed by `assertDispatchModeLive` after fixture validation and before any engine bring-up, exit code from the thrown error), `--repeats N`, `--maia-fifo` and `--hash warm|clear`. Every (row, repeat) runs `await pool.whenIdle()`, `await pool.resetAll()`, `resetMaiaRunMemo()`, then the search with `budget.dispatchMode`. Columns `dispatch_mode`, `repeat`, `hash_mode`, `maia_fifo` are appended at the end. `createJudgeMemo()` caches the independent judge grades, so repeat 2 of the smoke did zero judge grading (24 hits, 0 misses in one run; 23 hits, 1 miss in another, where the one miss was a flipped pick). `createGradePool(size, { clearHash })` forwards the search signal into `pool.run` and exposes `whenIdle()`.
- **Task 2: stop-rule, depth-ab, search-trace.**
  - `engine-dispatch-stop-rule.mjs`: the label-only header is rewritten (226 D-07 retains round mode behind `SearchBudget.dispatchMode`), the flag is optional and real, `whenIdle()` precedes every timer, and `grade_cpu_ms`, `loop_lag_max_ms`, `root_split_premise_violations` are appended. `LOOP_LAG_RESOLUTION_MS = 10` and `startLoopLagProbe()` are exported.
  - `engine-grading-depth-ab.mjs`: `--dispatch-mode`, `--ladder-only` (implies `--ladder`, skips all flat passes and reference comparisons), signal forwarded through `gradeAtDepth`, `gradeAtLadder` and both gradeRoot variants (shared `gradeRootWith`, aborted root grade resolves empty, never a partial merge), hash probe skipped after abort, `whenIdle()` before each pass, `dispatch_mode` and `loop_lag_max_ms` appended.
  - `engine-search-trace.mjs`: `--dispatch-mode` with probe, `whenIdle()`, budget field, `dispatch_mode` as the last column of both TSVs, and a header caveat that round ids are snapshot-delimited batches in continuous mode.

## Smoke results (real engines, round mode)

| Smoke | Result |
|---|---|
| MQ, 12-row fixture, `--repeats 2 --maia-fifo` | 24 rows; repeat 1 about 21 to 25 s, repeat 2 about 23 s (search time only); judge memo hits +12/+12 then +24/+0 |
| MQ `--hash clear --stop-rule off --nodes 12` | runs, 12 rows (Clear Hash path exercised) |
| stop-rule `--openings 1 --maia-fifo` | 5 rows, `grade_cpu_ms` 1101 to 13204, `loop_lag_max_ms` 2.2, 6.9, 7.8, 8.9, 9.6 |
| depth-ab `--nodes 20 --ladder-only --openings 1 --maia-fifo` | 5 ladder rows only, `loop_lag_max_ms` 1.5, 6.5, 7.1, 7.6, 9.7, total ladder wall 17.1 s |
| depth-ab flat+ladder (`--nodes 8 --depths 10,8 --ladder`) | flat passes, comparisons and ladder all still work |
| search-trace `--ids cBFTV --nodes 12 --dispatch-mode round` | 4 rounds (1,4,4,3), `dispatch_mode` column present |
| `--dispatch-mode continuous` on all four scripts | exit status 3 (checked once per script) |

Loop lag stayed well under the expected 30 ms (max 9.7 ms) with worker-thread Maia. No MQ pass was run on `fixtures/engine/move-quality-226.tsv` (prohibition honored).

## Task Commits

1. **Task 1 (tracer):** `ec3e7fa5d` feat(227-04): MQ gate selects dispatch mode in one checkout with repeats, FIFO Maia and hash modes
2. **Task 2:** `d836b2059` feat(227-04): stop-rule, depth-ab and search-trace measure the selected dispatch mode on quiesced pools

Tracer gate: after the Task 1 commit the verify steps were re-run (self-test, 2-repeat smoke, hash-clear smoke, continuous exit 3) and passed before expansion; the 2-repeat smoke was re-run again after Task 2 (see Issues Encountered).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan] monitorEventLoopDelay read right after the search misses the last stall**
- **Found during:** Task 2, before wiring the column (Plan 227-01 had hit the same instrument problem)
- **Issue:** a 300 ms synchronous block read 10.19 ms from the histogram immediately and 309.85 ms 50 ms later; the sample lands only after the stall ends. Also each sample includes the 10 ms sampling period itself.
- **Fix:** `startLoopLagProbe().stop()` waits `2 x LOOP_LAG_RESOLUTION_MS` before reading `max` and subtracts one period. The wait happens after `wall_ms` is taken, so it is not timed. Self-test asserts an idle loop reads under 50 ms and a 150 ms stall read immediately afterwards reads at least 100 ms.
- **Files modified:** scripts/engine-dispatch-stop-rule.mjs
- **Commit:** d836b2059

**2. [Rule 2 - Missing critical] Judge memo keyed on the full call content instead of fen|uci|depth**
- **Found during:** Task 1
- **Issue:** the judge grades a (pick, correct) pair with MultiPV equal to the candidate count, so a per-uci key could mix grades produced under different MultiPV sets.
- **Fix:** key is `fen|pick|correct|depth`; a hit is then exactly the result a fresh grade would give. A self-test with a scripted engine proves hit, miss on depth, miss on pick, and that failures are not cached.
- **Commit:** ec3e7fa5d

**3. [Rule 3 - Blocking] Abort values shaped for the internal result types**
- **Found during:** Task 2
- **Issue:** the plan says `pool.run(fn, signal, new Map())`, but in the stop-rule pool `fn` resolves `{ grades, elapsedMs }` (needed for `grade_cpu_ms` without double counting retried attempts) and in depth-ab `{ grades, scratch, aborted }`, so the abort value takes the same shape. The public `grade`/`gradeRoot` still resolve a plain empty Map on abort.
- **Files modified:** scripts/engine-dispatch-stop-rule.mjs, scripts/engine-grading-depth-ab.mjs
- **Commit:** d836b2059

**Total deviations:** 3 auto-fixed (1 bug-in-plan, 1 missing critical, 1 blocking). **Impact:** none on scope; all inside the four planned files. The default MQ `--grade-depth` stays 18 (the Phase 227 gate passes `--grade-depth 20` explicitly; the plan did not ask for a default change and the tripwire compares `es_bot` only when `grade_depth` matches).

## Issues Encountered

**cBFTV flips in round mode, so the plan's smoke assertion (round repeats agree on `bot_move`) is flaky.** The 2-repeat smoke passed on the first run and failed on a later run: cBFTV picked `e4c6` (8 nodes, early-stop) in one repeat and `e2g4` (50 nodes, budget) in the other. Measured with a 1-row fixture (cBFTV only), in-process repeats, `--stop-rule on`, pool size 4:

| Variant | Flips to the minority pick |
|---|---|
| this plan's code (signal forwarded) | 14 of 130 repeats (10.8 percent) |
| same code with the signal forwarding disabled (A/B) | 9 of 120 repeats (7.5 percent) |
| plan-base scripts (process-level, 15 separate runs) | 0 of 15 (e4c6 each time) |

The rate does not depend on this plan's signal forwarding (A/B 10.8 vs 7.5 percent, not distinguishable), so it is the inherent warm-hash/timing sensitivity of that position under round dispatch (which engine of the pool receives which grade within a round varies with timing). `--maia-fifo` appeared to shift the majority pick (one 10-repeat run with FIFO gave 9 of 10 `e2g4`, the non-FIFO runs gave mostly `e4c6`; small sample), which is another timing-sensitivity symptom. **Consequence for later plans:** `engine_dispatch_227_verdict.py::_check_round_determinism` treats any round-repeat disagreement as INVALID (it cites 226's 0 of 60); with 5 repeats a genuine cBFTV-style flip would invalidate a round arm. Plan 227-08/09 should decide whether that rule needs a flip allowance or whether the round arm needs a harder determinism setting before the repeats run.

## Known Stubs

None.

## Threat Flags

None. T-227-07 (label-only mode) mitigated: `assertDispatchModeLive` runs before engine bring-up in all four scripts and `dispatch_mode` is stamped per row. T-227-08 (stale grades) mitigated: `whenIdle()` before each timer and the signal reaches the Node pools. T-227-SC: no package installed (`npm ci` from the lockfile only).

## Self-Check: PASSED

- Modified files exist: scripts/engine-move-quality.mjs, scripts/engine-dispatch-stop-rule.mjs, scripts/engine-grading-depth-ab.mjs, scripts/engine-search-trace.mjs.
- Commits exist: ec3e7fa5d, d836b2059.
- Acceptance greps: `assertDispatchModeLive` present in engine-move-quality.mjs; `grep -c "is a LABEL for the emitted row"` in the stop-rule script prints 0 and `226 D-07` matches the rewritten header; `--repeats`, `loop_lag_max_ms`, `--ladder-only`, `dispatchMode` present in their scripts.
- No file under `frontend/src` or `mctsSearch.ts` changed (`git diff --stat cb82bf558 HEAD` lists only the four scripts).
