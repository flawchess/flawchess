---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 06
subsystem: frontend-dev-tooling
tags: [dev-page, maia, webgpu, wasm, stockfish-pool, bench, engine-bench-227]

requires:
  - phase: 227-02
    provides: "DispatchMode type, SearchBudget.dispatchMode, FIFO app Stockfish queue"
  - phase: 227-03
    provides: "engine-bench-227/v1 contract read by engine_dispatch_227_verdict.py webgpu"
provides:
  - "DEV-gated lazy route /dev/engine-bench (outside the auth wrappers), absent from production builds"
  - "Maia batch-1 latency per backend (wasm with reported thread count, WebGPU when the adapter supports it), idle and Stockfish-saturated"
  - "Bot-move wall legs: round-only and interleaved round/continuous, rotated order, every row carrying the in-page observed dispatch mode"
  - "engine-bench-227/v1 JSON export (copy button) in the shape the verdict twin reads"
affects: [227-08, 227-10, 227-13]

plan_head_before: cb82bf558f50333e574f9f646ae446f08257f3a1
plan_head_after: 69c14eb365f78aadfdb1f04253bdd9ccd6401ce7

actuals:
  tokens: 13900
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Compile-time DEV gate on the lazy() call itself (conditional, not top-level lazy), proven by a positive-control dev build"
    - "Dedicated bench workers/pools built from shipped modules; no shipped engine module edited"

key-files:
  created:
    - frontend/src/dev/engineBench/EngineBenchPage.tsx
    - frontend/src/dev/engineBench/maiaLatencyBench.ts
    - frontend/src/dev/engineBench/botMoveBench.ts
    - frontend/src/dev/engineBench/benchReport.ts
    - frontend/src/dev/engineBench/benchPositions.ts
    - frontend/src/dev/engineBench/__tests__/benchReport.test.ts
    - frontend/src/dev/engineBench/__tests__/botMoveBench.test.ts
    - frontend/src/dev/engineBench/__tests__/EngineBenchPage.test.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "BENCH_POSITIONS lives in benchPositions.ts (shared by the Maia and bot-move legs) instead of botMoveBench.ts, so Task 1 can ship without the Task 2 module"
  - "Plan-listed constants (MAIA_BENCH_WARMUP/SAMPLES/ELO, BUSY_GRADE_DEPTH) are module-private, not exported: knip fails CI on exports nothing imports"
  - "Maia-only runs export leg 'round' with an empty botMove list; the twin's round-leg reader accepts that, and the judged continuous-leg file needs leg 'interleaved'"

requirements-completed: []

coverage:
  - id: D1
    description: "Dev page measures Maia batch-1 latency per backend, idle and Stockfish-saturated, and exports engine-bench-227/v1 JSON"
    verification:
      - kind: unit
        ref: "frontend/src/dev/engineBench/__tests__/benchReport.test.ts"
        status: pass
    human_judgment: true
    rationale: "The measurement itself needs a real browser; none was available to this agent. Plan 227-08 (local wasm) and the owner (WebGPU) run it."
  - id: D2
    description: "Page refuses to run (red banner, disabled buttons) unless isSecureContext && crossOriginIsolated"
    verification:
      - kind: unit
        ref: "frontend/src/dev/engineBench/__tests__/EngineBenchPage.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Route and page are absent from the production bundle"
    verification:
      - kind: other
        ref: "cd frontend && npm run build && ! grep -rq 'engine-bench-227' frontend/dist (positive control: NODE_ENV=development vite build contains the marker and an EngineBenchPage chunk)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every bot-move row records the dispatch mode observed by an in-page probe"
    verification:
      - kind: unit
        ref: "frontend/src/dev/engineBench/__tests__/botMoveBench.test.ts"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 06: Dev engine-bench page Summary

**A DEV-only `/dev/engine-bench` page that measures Maia batch-1 latency per backend (idle and with the Stockfish pool saturated) and bot-move wall time round vs continuous (interleaved, rotated, each row labelled with the dispatch mode an in-page probe observed), exporting one `engine-bench-227/v1` JSON for the verdict twin.**

## Accomplishments

- **Route and gate.** `App.tsx`: `const EngineBenchPage = import.meta.env.DEV ? lazy(() => import('./dev/engineBench/EngineBenchPage')) : null;` and a `/dev/engine-bench` route rendered only when non-null, beside the public routes (outside `ProtectedLayout`). No shipped module imports `frontend/src/dev`.
- **Maia leg** (`maiaLatencyBench.ts`). One dedicated `Worker(ENGINE_PATH)` per backend with the same `init` message `maiaWorkerHost.spawn()` posts (wasm runtime from `fetchWasmOnlyOrtRuntime()`, WebGPU from `ensureOrtRuntime()` only when the shipped probe picks webgpu). Records `backend` and `numThreads` from `ready`; a device without WebGPU, a worker that falls back or fails init yields rows with `available: false` and a reason. 5 warm-up + 30 timed single-ELO (1500) analyzes cycling the bench FENs, median and nearest-rank p90. `sf-busy` keeps a `computePoolSize()`-slot `createWorkerPool()` saturated with depth-14 grades on a stream of distinct FENs (grade cache keys on fen|depth). A failed busy run keeps the idle row. Every worker and pool is terminated.
- **Bot-move legs** (`botMoveBench.ts`). `runBotMoveLeg(modes, rounds)`: per round the modes rotate by `round - 1`; per (round, mode) a fresh pool + Maia queue wired as `useBotGameEngineDispatch` wires the bot (policy, grade, gradeRoot), an untimed warm-up search, then one timed `mctsSearch` per position with `FLAWCHESS_BOT_*` budget, `clearMaiaPolicyCache()` first. `probeDispatchModeInPage` is the browser twin of `scripts/lib/dispatch-mode.mjs` (deferred mock grades around the real `mctsSearch`, concurrency 2, a grade call beyond `1 + 2` after one child settles means continuous). Each row stores `modeObserved` and the queue's reported `backend`. The interleaved button probes continuous first and refuses with "continuous dispatch is not implemented in this build" when the page observes round.
- **Export** (`benchReport.ts`). `buildBenchReport`, `summarizeBotMoveRatios` (per-round sum continuous / sum round, median, excluded-round count), `summarizeLatencySamples`, `ENGINE_BENCH_SCHEMA = 'engine-bench-227/v1'`.
- **Refusal.** Red `engine-bench-refusal` banner and disabled run buttons unless `isSecureContext && crossOriginIsolated`.

## Verification

| Check | Result |
|---|---|
| `npx vitest run src/dev/engineBench` | 3 files, 12 tests passed |
| `npm run lint`, `npm run build` (tsc -b + vite), `npx knip` | clean, exit 0 |
| `src/App.test.tsx` | 61 passed (route addition did not disturb it) |
| `grep -rq "engine-bench-227" frontend/dist` after a production build | no match; no `EngineBench*` chunk in `frontend/dist/assets` |
| Positive control: `NODE_ENV=development npx vite build --mode development` into a scratch dir | marker found, `EngineBenchPage-*.js` chunk emitted (so the grep can fail) |
| Mutation: drop `&& env.crossOriginIsolated` from `contextOk` | the "not cross-origin isolated" refusal test fails; restored, 12/12 pass |

Build output directory checked: `frontend/dist`. Marker string: `engine-bench-227` (appears in the page's testid and the schema constant).

## Task Commits

1. **Task 1 (tracer):** `a5999a984` feat(227-06): dev-only engine bench page with Maia latency leg and engine-bench-227/v1 export. Tracer gate: `<verify>` re-run end to end after the commit's code was final (vitest, lint, build, knip, marker grep) and passed before expanding.
2. **Task 2:** `69c14eb36` feat(227-06): bot-move legs on the engine bench page, each row carries the observed dispatch mode.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `BENCH_POSITIONS` placed in `benchPositions.ts`, not `botMoveBench.ts`**
- **Found during:** Task 1 (the Maia leg needs the FENs, but `botMoveBench.ts` is Task 2's file)
- **Fix:** a small shared module; `botMoveBench.ts` imports it. The six positions are the stop-rule harness's four built-ins plus `OPENING_BOOK` C50 and C60.
- **Commit:** a5999a984

**2. [Rule 3 - Blocking] Plan-listed constants kept module-private**
- **Issue:** `MAIA_BENCH_WARMUP`, `MAIA_BENCH_SAMPLES`, `MAIA_BENCH_ELO`, `BUSY_GRADE_DEPTH` are listed as constants of the module; exporting them with no importer would fail `npm run knip` (CI gate). Only `BOT_BENCH_ROUNDS`, `probeDispatchModeInPage`, `runBotMoveLeg`, `runMaiaLatencyLeg` and the report builders are exported (all imported by the page or tests).
- **Commit:** a5999a984

**3. [Rule 2 - Missing critical] Page render test for the refusal rule**
- The plan's threat T-227-11 mitigation (refusal banner, disabled buttons) had no test in the plan; added `EngineBenchPage.test.tsx` (3 cases) and mutation-checked it. Also added `botMoveBench.test.ts` (the probe reads `round` against the real round loop). The probe test deliberately makes no assertion for a continuous request, so Plan 227-10 landing the continuous loop does not break it.
- **Commit:** 69c14eb36

**Total deviations:** 3, none changing scope or any shipped engine module.

## Owner instructions (WebGPU leg; also Plan 227-08's local wasm leg)

The real-browser run of both legs is Plan 227-08's job (Claude's local wasm leg) and the owner's (WebGPU). This agent had no browser, so none of the page's measurements have been executed in a real browser; only the pure logic, the refusal rule (jsdom) and the build gate were verified.

1. Get a dev server on a machine with a WebGPU adapter: either an SSH tunnel to the dev box, `ssh -L 5173:localhost:5173 <box>`, or a local checkout with `cd frontend && npm ci && npm run dev`.
2. Open `http://localhost:5173/dev/engine-bench` in Chrome. Never a LAN IP (not a secure context, so the page refuses).
3. Confirm the env panel shows `isSecureContext true`, `crossOriginIsolated true`, `adapter shader-f16 true`.
4. Click "Run Maia latency leg", then "Run round-only leg" (works now), then, once continuous dispatch exists (Plan 227-10), "Run interleaved leg".
5. After each bot-move leg click "Copy JSON" and save it: the round-only run as `reports/data/continuous-dispatch-227/webgpu/round-leg.json`, the interleaved run as `.../webgpu/continuous-leg.json` (the twin judges `leg: "interleaved"` rows on the `webgpu` backend only).

## Known Stubs

None. (`modeObserved` for a `continuous` request reads `round` until Plan 227-10 adds the loop; that is the probe working as designed, not a stub.)

## Threat Flags

None. T-227-10 mitigated (compile-time gate, marker grep, positive control; deletion left to Plan 227-13). T-227-11 mitigated (refusal banner, backend and `numThreads` recorded per row). T-227-SC: no package added (`npm ci` from the lockfile only).

## Self-Check: PASSED

- Created files exist under `frontend/src/dev/engineBench/` (8 files) and `frontend/src/App.tsx` carries `import.meta.env.DEV ? lazy`.
- Commits `a5999a984` and `69c14eb36` exist on the worktree branch.
- No edits to `maiaWorkerHost.ts`, `maiaQueue.ts`, `workerPool*.ts`, `mctsSearch.ts` or other shipped engine modules; no npm package added.
