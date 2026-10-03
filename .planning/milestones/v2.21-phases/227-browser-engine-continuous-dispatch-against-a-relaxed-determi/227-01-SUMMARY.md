---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 01
subsystem: engine-harness
tags: [node, worker_threads, onnxruntime-web, stockfish, abort-signal, calibration-harness]

requires: []
provides:
  - "createMaiaSession({ backend, offThread = true }): wasm Maia runs in a worker_threads worker behind an unchanged { ort, session } surface"
  - "Node Stockfish pool abort semantics (grade / gradeRoot / run) mirroring the browser WorkerPool, plus whenIdle() and queuedCount()"
  - "maia-worker-thread.check.mjs and an abort section in stockfish-pool.check.mjs, each with discriminating negative controls"
affects: [227-02, 227-03, 227-08, continuous-dispatch gate scripts]

plan_head_before: 5747916856992a7422efac837c2ae69948edd1b3
plan_head_after: 4be3c432ef33c4ddcb4ec9e0eba62baab00beac0

actuals:
  tokens: 12400
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Worker-thread proxy session: same run(feeds) contract, transferred buffers, ref/unref tied to in-flight requests"
    - "Abort-aware pool acquire: queued waiter entry exposed so an abort can pull it; engine freed only after bestmove"

key-files:
  created:
    - scripts/lib/maia-worker-thread.mjs
    - scripts/lib/maia-worker-thread.check.mjs
  modified:
    - scripts/lib/node-engine-providers.mjs
    - scripts/lib/stockfish-pool.mjs
    - scripts/lib/stockfish-pool.check.mjs
    - scripts/lib/maia-instrumentation.check.mjs

key-decisions:
  - "Worker death ends the process with MAIA_WORKER_DIED_EXIT_CODE (70) instead of degrading into empty policies, so bin/preset-supervisor.sh resumes a sweep exactly as it does for a main-thread crash"
  - "Worker spawned with execArgv: [] (the worker imports no frontend TS; inheriting --input-type=module -e breaks it outright)"
  - "Pool whenIdle also waits for in-flight dead-engine respawns (pool.respawning), so it never reports idle mid-heal"

requirements-completed: []

coverage:
  - id: D1
    description: "Harness Maia runs in a worker thread with byte-identical output, timers keep running through a FIFO burst, worker death exits with a dedicated code, and the process exits on its own"
    verification:
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/maia-worker-thread.check.mjs"
        status: pass
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/maia-instrumentation.check.mjs [--real-session]"
        status: pass
    human_judgment: false
  - id: D2
    description: "Node Stockfish pool honors the grade signal like the browser pool (pre-aborted, queued, in-flight stop, listener hygiene, gradeRoot never partial) and can be quiesced via whenIdle()"
    verification:
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs [--root-split]"
        status: pass
      - kind: integration
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool-death-check.mjs"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 01: Harness Maia off the event loop and abort-aware Node Stockfish pool Summary

**Harness Maia now runs in a `worker_threads` worker (byte-identical logits, timers keep firing through a FIFO burst), and the Node Stockfish pool cancels stale grades like the browser pool and exposes `whenIdle()`.**

## Performance

- **Duration:** about 50 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 2 created, 4 modified, none under `frontend/src`

## Accomplishments

- **Task 1 (tracer): Maia off the event loop.** `createMaiaSession({ offThread = true })` spawns `scripts/lib/maia-worker-thread.mjs` and returns a proxy session with `inputNames`, `outputNames`, `run(feeds)`, `close()` and a non-enumerable `_worker`. `runMaia` in `calibration-providers.mjs` is unchanged (`result.logits_move.data.slice(...)` and `t.dispose?.()` work against the proxy's `{ type, data, dims, dispose() {} }` outputs). `offThread: false` is the old main-thread session; `backend: 'native'` untouched.
- **Task 2 (TDD): abort-aware pool.** `withEngine(pool, fn, signal, abortValue)`; `grade`, `gradeRoot`, `run(fn, signal, abortValue)` honor the signal; `whenIdle()`; "Phase 227 N-2" fix-site comment on `grade`.

### Measured values (Task 1 acceptance)

| Session | Max event-loop lag over the 4-request FIFO burst | Timer ticks (10 ms) | Burst wall |
|---|---|---|---|
| worker thread (default) | 6.3 to 15.4 ms across runs, bound is 30 ms | 35 | about 370 to 383 ms |
| main thread (`offThread: false`, negative control) | 354.8 to 363 ms | 0 | about 364 to 374 ms |

Parity: 14/14 (FEN, ELO) pairs byte-identical for both heads (7 FENs x ELOs 1100 and 1900). Worker-death child exits with status 70. The check script exits on its own (about 6 s) without `close()`.

## Mutation checks (as the plan requires)

| Mutation | Result |
|---|---|
| Task 1: `createMaiaSession` default returns the main-thread session | (b) worker-session lag FAIL (363 ms, 0 ticks), (c) FAIL (`_worker` undefined, child status 1) |
| Task 1: remove `process.exit(MAIA_WORKER_DIED_EXIT_CODE)` from the death handler | (c) FAIL (child status 0 instead of 70) |
| Task 2 (a): remove the `stop` send on in-flight abort | (i) "abort sends stop" FAIL, (i) `whenIdle` bound FAIL (timedOut), (k) `whenIdle` FAIL |
| Task 2 (b): remove the waiter-list removal | (h) "aborted request left the waiter list" FAIL (queuedCount 1) |
| Task 2 (c): drop the listener removal in `settle` | (j) listener hygiene FAIL (20 listeners left) |

Every mutation was reverted (`grep MUT` finds nothing) and the full checks re-run green.

## TDD Gate Compliance

- RED: `47ec0760b test(227-01)`. Against the unmodified pool the abort section failed on assertions, not crashes: (g) non-empty Map for an aborted grade (got size 4) and a `go` sent, (h) queued request not cancelled, (i) aborted in-flight grade did not settle within 500 ms (timedOut=true), no `stop` sent, `whenIdle` bound missed. Case (j) passed at RED by construction (the old pool never attaches a listener), so it only guards the new code (proved by mutation c). The `gsd_run check tdd-red-evidence` record was not produced: the `gsd_run` shell function is not available in this subagent environment.
- GREEN: `4be3c432e feat(227-01)`. 26 PASS, 0 FAIL in the default run; 4 PASS in `--root-split`; `stockfish-pool-death-check.mjs` ALL PASS.
- REFACTOR: none.

## Task Commits

1. **Task 1 (tracer):** `b23c593f3` feat(227-01): run harness Maia in a worker thread off the event loop
2. **Task 2 RED:** `47ec0760b` test(227-01): add failing abort section for the Node Stockfish pool
3. **Task 2 GREEN:** `4be3c432e` feat(227-01): Node Stockfish pool honors abort and exposes whenIdle

Tracer gate: auto-mode not required; `<verify>` re-run end to end after the commit and passed ("Tracer verified end-to-end, expanding").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] maia-instrumentation.check.mjs was broken at the plan base**
- **Found during:** Task 1, step 4 (baseline run before any change)
- **Issue:** its stub Maia session returns only `logits_move`, but `runMaia` has read `logits_value` since SEED-145, so the default run threw `Cannot read properties of undefined (reading 'data')`. The plan's verify requires this check to pass.
- **Fix:** the stub now also returns a 3-float `logits_value`. No production code touched.
- **Files modified:** scripts/lib/maia-instrumentation.check.mjs
- **Commit:** b23c593f3

**2. [Rule 1 - Bug] `monitorEventLoopDelay` cannot serve as the negative-control instrument**
- **Found during:** Task 1, first check run
- **Issue:** the plan specified `monitorEventLoopDelay({ resolution: 1 })`. Over a main-thread burst in which the 10 ms timer fired zero times in about 370 ms, the histogram reported a 1.1 ms max, so the negative control could not fail as intended.
- **Fix:** lag is measured with a self-timed 10 ms interval (max gap between ticks minus the period), after letting one tick through post-burst. Reads 355 to 363 ms on the main thread, 6 to 15 ms on the worker.
- **Files modified:** scripts/lib/maia-worker-thread.check.mjs
- **Commit:** b23c593f3

**3. [Rule 1 - Bug] Worker inherited the parent's `execArgv`**
- **Found during:** Task 1, death-section child (`--input-type=module -e`)
- **Issue:** a Node Worker inherits `process.execArgv`; with `--input-type=module -e` it fails with ERR_INPUT_TYPE_NOT_ALLOWED when loading a file URL. Any harness invoked that way would hit it.
- **Fix:** `new Worker(..., { execArgv: [] })` (the worker imports no frontend TS, so it needs no alias hook).
- **Files modified:** scripts/lib/node-engine-providers.mjs
- **Commit:** b23c593f3

**4. [Rule 2 - Missing critical] `queuedCount()` read-only pool instrument added**
- **Found during:** Task 2, designing mutation check (b)
- **Issue:** with the required "engine handed to an aborted waiter is released" guard, removing the waiter-list removal has no behavioral effect (the engine is just released straight away), so the plan's mutation (b) could not fail without a way to observe the waiter list.
- **Fix:** `queuedCount: () => pool.waiters.length` on the pool surface (same status as the existing `freeCount()`); case (h) asserts it is 1 before the abort and 0 after. Mutation (b) now fails exactly there.
- **Files modified:** scripts/lib/stockfish-pool.mjs, scripts/lib/stockfish-pool.check.mjs
- **Commit:** 4be3c432e

**5. [Rule 2 - Missing critical] gradeRoot abort case (k) and `whenIdle` respawn accounting**
- `gradeRoot` abort (L-2: never a partial merge) was specified in the action but not in the behavior list, so check case (k) was added (size-4 pool, fan-out, abort, empty Map, `whenIdle` bound).
- `whenIdle` also waits on `pool.respawning` so it never reports idle while a dead engine's replacement is still spawning. `stockfish-pool-death-check.mjs` passes unchanged.
- **Commit:** 4be3c432e

**Total deviations:** 5 auto-fixed (1 blocking, 2 bugs, 2 missing critical). **Impact:** none on scope; all inside the plan's files plus the one pre-existing check script.

### Environment notes

- `frontend/node_modules` was absent in the fresh worktree; ran `npm ci` in `frontend/` from the lockfile (no package added or changed, ORT versions untouched).
- The per-plan commit ledger and spawn-toplevel sentinel files could not be written under the shared `.git/worktrees/` path (the sandbox rejects it); `plan_head_before` above is the dispatch base SHA recorded by the orchestrator, and `commits: 3` is `git rev-list --count base..HEAD` at SUMMARY time (before the docs commit).

## Known Stubs

None.

## Threat Flags

None. T-227-01 (worker output tampering) mitigated by the byte-parity check; T-227-02 (stale search) mitigated by the abort section plus three mutations; T-227-SC: no package installed or changed.

## Verification

- `maia-worker-thread.check.mjs`: MAIA-WORKER-CHECK PASS (exit 0, process ends on its own).
- `maia-instrumentation.check.mjs` default and `--real-session`: ALL CHECKS PASSED (the real-session mode now exercises the worker proxy).
- `stockfish-pool.check.mjs` default: 26 PASS / 0 FAIL; `--root-split`: 4 PASS, exit 0.
- `stockfish-pool-death-check.mjs`: ALL PASS.
- `git diff --stat <base> HEAD` lists no file under `frontend/src` and no `scripts/lib/calibration-providers.mjs`.

## Next Phase Readiness

Gate scripts can now run Maia and Stockfish concurrently without starving either (`createMaiaSession()` default) and can `abort()` stale grades and `await pool.whenIdle()` before the next position's timer starts. Callers that build their own private pools (the depth-ab closures, `createGradePool`) are not covered by this plan.

## Self-Check: PASSED

- Created files exist: scripts/lib/maia-worker-thread.mjs, scripts/lib/maia-worker-thread.check.mjs.
- Commits exist: b23c593f3, 47ec0760b, 4be3c432e.
- Acceptance criteria re-checked: `offThread` default true present; `whenIdle` and "Phase 227 N-2" present; calibration-providers.mjs and frontend/src unchanged.
