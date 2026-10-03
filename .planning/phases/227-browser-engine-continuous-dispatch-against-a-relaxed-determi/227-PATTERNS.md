# Phase 227: Browser Engine Continuous Dispatch - Pattern Map

**Mapped:** 2026-10-02
**Files analyzed:** 24 (new + modified)
**Analogs found:** 23 / 24

All analog paths below are git-tracked source (verified via `git ls-files`). Line numbers were checked on this branch (post-226 squash `d0f5cb2ba`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/engine/mctsSearch.ts` (add continuous loop, shared apply helper) | service (search core) | event-driven / async | own round loop `mctsSearch.ts:650-748` | exact (same file) |
| `frontend/src/lib/engine/types.ts` (`DispatchMode`, `SearchBudget.dispatchMode?`) | model/type | config | `types.ts:107` `stopRule?` and `:61` `gradeRoot?` | exact |
| `frontend/src/lib/engine/botBudget.ts` (`FLAWCHESS_DISPATCH_MODE`) | config | config | `botBudget.ts:64` `FLAWCHESS_BOT_CONCURRENCY`, `FLAWCHESS_BOT_STOP_RULE` | exact |
| `frontend/src/hooks/useBotGame.ts` (`BOT_SEARCH_BUDGET` :123-128) | hook | config | itself (add one field) | exact |
| `frontend/src/hooks/useFlawChessEngine.ts` (analysis budget :365-379) | hook | config | itself | exact |
| `frontend/src/lib/engine/deadlineSearch.ts` (comment :36-44) | service | event-driven | itself; two-signal pattern at `:83-124` | exact |
| `frontend/src/lib/engine/gradingLadder.ts` (Y-14 comment :84-85) | utility | - | `workerPool.ts:274-276` (real cache key) | exact |
| `frontend/src/lib/engine/workerPoolState.ts` (D-19 FIFO tie-break, `dequeueHighestPriority` :443-468) | utility (queue) | request-response | itself + harness FIFO `scripts/lib/stockfish-pool.mjs:81,104` | exact |
| `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts` (new) | test | event-driven | `__tests__/mctsSearch.roundFill.test.ts`, `__tests__/mctsSearch.test.ts` (`withJitter`, `makeFixedPolicy`, `makeVariedGrade`) | exact |
| `frontend/src/lib/engine/__tests__/workerPool.test.ts` (FIFO test) | test | request-response | itself | exact |
| `frontend/src/dev/engineBench/EngineBenchPage.tsx` (+ helpers, new, removed at phase end) | component (dev page) | request-response | `lib/devClock.ts:26` DEV gate, `App.tsx:53-64` `lazy()` routes, `maiaWorkerHost.ts:525-540` worker init | role-match |
| `frontend/src/App.tsx` (DEV-only route) | route | - | `App.tsx:53-64` lazy imports | exact |
| `scripts/lib/stockfish-pool.mjs` (abort support, N-2) | service (Node pool) | request-response | `frontend/src/lib/engine/workerPoolDispatch.ts:280-315` | exact (mirror) |
| `scripts/engine-dispatch-stop-rule.mjs` (`createGradePool` abort, real `--dispatch-mode`, grade-time column) | script | batch | itself `:30-46`, `:327-375` | exact |
| `scripts/lib/calibration-providers.mjs` (`maiaFifo` off main thread, D-18) | service (Node provider) | event-driven | `maiaFifoProcess` `:300-335` mirroring `frontend/src/lib/engine/maiaQueue.ts` | exact |
| `scripts/lib/node-engine-providers.mjs` (Maia session into `worker_threads`, D-18) | service | request-response | `:85-98` session creation; browser `maiaWorkerHost.ts` worker protocol | role-match |
| `scripts/engine-move-quality.mjs` (`--dispatch-mode`, `--repeats`, `--maia-fifo`, `--grade-depth 20`) | script | batch | itself `:92-95`, `:462-468` | exact |
| `scripts/engine-grading-depth-ab.mjs` (`--dispatch-mode`, `--ladder-only`) | script | batch | itself `:686-690,751-755`, grade timing `:316-326` | exact |
| `scripts/calibration-harness.mjs` (budget mode + resume key) | script | batch | itself `:594-603`, resume check `:1060-1072` | exact |
| `scripts/lib/calibration-determinism.check.mjs` (pin round + parity assert) | test (check script) | batch | itself `:430-440` | exact |
| `scripts/lib/maia-fifo-yield.check.mjs` or extend `maia-instrumentation.check.mjs` (event-loop lag) | test (check script) | event-driven | `scripts/lib/stockfish-pool.check.mjs`, other `scripts/lib/*.check.mjs` | role-match |
| `scripts/engine_dispatch_227_verdict.py` (new) | utility (verdict twin) | transform | `scripts/engine_throughput_226_verdict.py` | exact |
| `tests/scripts/test_engine_dispatch_227_verdict.py` (new) | test | transform | `tests/scripts/test_engine_throughput_226_verdict.py` | exact |
| Interleave driver `scripts/engine_interleave_227.py` or `bin/engine_interleave_227.sh` (new, with machine-speed probe) | script (driver) | batch | none committed (only `reports/data/engine-throughput-226/retest-2026-10-02/driver.log`); shell style from `bin/preset-supervisor.sh` | partial |
| `reports/continuous-dispatch-227/{design,accept-rule,report}.md` | doc | - | `reports/engine-throughput-226/accept-rule.md`, `reports/continuous-dispatch/apply-order-design.md` §9b/§9d | exact |
| `CHANGELOG.md`, `docs/flawchess-engine-explained-2026-07-06.md` (if ships) | doc | - | existing `[Unreleased]` bullets | exact |

## Pattern Assignments

### `frontend/src/lib/engine/types.ts` + `botBudget.ts` (flag, "omitted = old behavior")

**Analog:** `types.ts:105-108`
```typescript
  /** Phase 159 D-06/D-07: reshapes the user's-side policy before truncation; omitted/1 = no-op. */
  policyTemperature?: number;
  /** Phase 168.5 D-05/D-06: optional bot-play early-stop rule; omitted/undefined = today's unchanged full-budget behavior. */
  stopRule?: BotStopRule;
```
Add `export type DispatchMode = 'round' | 'continuous';` and `dispatchMode?: DispatchMode;` with doc comment "Phase 227 D-13: omitted/undefined = round (byte-identical A21S)". Never `string`.

**Constant analog** `botBudget.ts:63-64`:
```typescript
/** Pinned bot-play search concurrency (D-09) — ... so app == harness determinism holds exactly. Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_CONCURRENCY = 4;
```
`export const FLAWCHESS_DISPATCH_MODE: DispatchMode = 'round';` in the implementation commit; the ship commit flips it to `'continuous'` (one line, rollback = flip back). App and harness both import it (single definition).

---

### `frontend/src/lib/engine/mctsSearch.ts` (continuous loop)

**Analog:** the round loop in the same file. Block clearing `:700-709`:
```typescript
    for (const node of blockedThisRound) node.isBlocked = false;
    blockedThisRound.length = 0;
```
Barrier + apply loop `:720-745` (the part continuous mode replaces; the apply body must be extracted into a shared helper both modes call):
```typescript
    const results = await Promise.all(
      toExpand.map(({ leaf, path }) => dispatchExpansion(leaf, path, budget, providers, rootMover, signal)),
    );

    for (const result of results) {
      if (signal.aborted) break;
      applyExpansion(result, rootMover);
      if (result.candidateMap.size === 0) continue; // degenerate close (WR-04)
      nodesEvaluated += 1;
      if (nodesEvaluated >= budget.maxNodes) budgetExhausted = true;
      if (budget.stopRule && stopRuleSatisfied(root, budget.stopRule, nodesEvaluated, stopState)) {
        earlyStop = true;
      }
      onSnapshot(buildSnapshot(root, nodesEvaluated, budgetExhausted, budget.elo[root.side], stopReason()));
      if (earlyStop) break;
    }
```
Continuous loop shape: use RESEARCH.md "Continuous loop (sketch)" and "Fill pass with per-fill block scoping" (lines 344-379, 640-667): settled queue + single-shot `wake`, inner `dispatchController` forwarded from outer `signal` with `{ once: true }` and removed in `finally`, `applied + inFlight < maxNodes` guard, discard after `signal.aborted || earlyStop`, rejection rethrown. Split along seams fill / await / drain (eslint `max-depth` 4, soft complexity 15). Do not rebuild commit-ordered apply / ring buffer (D-08).

**Two-signal analog:** `deadlineSearch.ts:83-124` (inner controller pattern). **Listener-leak lesson:** `workerPoolDispatch.ts:271-279`.

---

### `frontend/src/lib/engine/workerPoolState.ts` (D-19 FIFO tie-break)

**Analog:** itself `:443-468`:
```typescript
 * Remove and return the highest-priority pending request. Ties broken by
 * smaller `depth`, then by ascending `candidateUcis[0]` UCI string —
 * NEVER by insertion/arrival order.
 ...
      (req.priority === best.priority &&
        req.depth === best.depth &&
        (req.candidateUcis[0] ?? '') < (best.candidateUcis[0] ?? ''));
```
Change: arrival order among equal priority/depth (e.g. monotonic enqueue seq, or rely on `pending` array order since `enqueue` does `pending.push(req)` at `:440` and strict `>`/`<` keeps the earliest). Update the doc comment, add a comment explaining the bug fix (starvation at pool 2 / c 4). Verify round mode stays bit-identical under existing c=4 unit/fixture gates (D-19); state explicitly in the plan if not. Mutation-check the new FIFO test in `workerPool.test.ts`.

---

### `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts` (new)

**Analog:** `__tests__/mctsSearch.roundFill.test.ts:1-40` header style: a long doc comment naming the decision IDs and the **mutation check** to record in SUMMARY, then:
```typescript
import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { mctsSearch } from '../mctsSearch';
import type { EngineProviders, EngineSnapshot, MoveGrade, SearchBudget } from '../types';
```
Reuse `withJitter`, `makeFixedPolicy`, `makeVariedGrade` from `mctsSearch.test.ts`; use deferreds for settle-after-abort (RESEARCH lines 669-686). Test list: RESEARCH "Decision -> Test Map" lines 748-768 (c=1 identity across 7+ fixtures with different jitter, after-abort, early-stop, budget, arrival order, fill, root guard, rejection, wakeup, listener).

---

### `scripts/lib/stockfish-pool.mjs` + `createGradePool` in `engine-dispatch-stop-rule.mjs` (abort, N-2)

**Analog:** `frontend/src/lib/engine/workerPoolDispatch.ts:285-313`:
```typescript
    if (signal) {
      onAbort = () => {
        const idx = state.pending.indexOf(req);
        if (idx >= 0) {
          // Unstarted — just drop it from the queue.
          state.pending.splice(idx, 1);
          settle(new Map());
          return;
        }
        // In-flight — send stop; the eventual bestmove is discarded ...
        for (const slot of state.slots) {
          if (slot.current === req && slot.state === 'thinking') {
            ops.armStopWatchdog(slot);
            slot.worker.postMessage('stop');
            slot.stopPending = true;
            slot.state = 'stopping';
            settle(new Map());
            return;
          }
        }
      };
      signal.addEventListener('abort', onAbort, { once: true });
    }
```
Replace the stale comment at `stockfish-pool.mjs:419-421` ("`signal` is accepted but deliberately NOT acted on") with a fix-site comment. Release the engine only on `bestmove`. Scripts await pool quiescence before each position's timer. Extend `scripts/lib/stockfish-pool.check.mjs`.

---

### `scripts/lib/calibration-providers.mjs` + `node-engine-providers.mjs` (D-18 Maia in `worker_threads`)

**Analog (FIFO):** `calibration-providers.mjs:300-335` `maiaFifoProcess` (one in flight, re-entered from both settle handlers, rejection resolves `{}`). Keep that queue shape; replace the `nodePolicy(...)` call with a postMessage round-trip to a worker thread holding the session.
**Analog (session):** `node-engine-providers.mjs:94-97`:
```javascript
  const ort = (await resolveFrontendModule('onnxruntime-web')).default;
  ort.env.wasm.numThreads = 1; // matches the browser worker's no-COOP/COEP posture
  const modelBytes = fs.readFileSync(modelPath);
  const session = await ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] });
```
Move into the worker. Tripwire: round-mode MQ must be byte-identical to 226 `reports/data/engine-throughput-226/gate/a21s/mq-{off,on}` TSVs. Set `maiaFifo: true` where continuous arms run (`engine-move-quality.mjs:462`, `calibration-harness.mjs:390`, Pitfall 4).

---

### `scripts/engine-dispatch-stop-rule.mjs`, `engine-move-quality.mjs`, `engine-grading-depth-ab.mjs` (real `--dispatch-mode`)

**Analog:** stop-rule header `:36-46` currently says the flag is a LABEL only and that D-11 (198) forbids retaining round mode; that rationale is superseded by 226 D-07. Rewrite the header, pass `dispatchMode` into the budget (`engine-move-quality.mjs:463-468`, `engine-grading-depth-ab.mjs:686-690,751-755`), stamp mode into every TSV row. Add `--repeats` (MQ), `--ladder-only` (depth-ab), `--grade-depth 20` explicitly (`DEFAULT_GRADE_DEPTH = 18` at `engine-move-quality.mjs:92`).

---

### `scripts/calibration-harness.mjs` (resume key, Pitfall 10)

**Analog:** `:1065-1071`:
```javascript
    if (row.maxNodes !== FLAWCHESS_BOT_MAX_NODES || row.maxPlies !== FLAWCHESS_BOT_MAX_PLIES) {
      throw new Error(
        `--resume: prior budget (nodes=${row.maxNodes}, plies=${row.maxPlies}) differs from current ` +
          `(nodes=${FLAWCHESS_BOT_MAX_NODES}, plies=${FLAWCHESS_BOT_MAX_PLIES}) — refusing to resume`,
      );
```
Add an identical `row.dispatchMode !== <active mode>` refusal and write `dispatchMode` into ledger rows (check `calibration-ledger-schema.check.mjs`). Budget at `:594-603` gets `dispatchMode` from `FLAWCHESS_DISPATCH_MODE` with an explicit arm-override flag.

---

### `scripts/engine_dispatch_227_verdict.py` (new verdict twin)

**Analog:** `scripts/engine_throughput_226_verdict.py`. Copy:
- Module docstring (lines 1-49): "machine-readable twin of accept-rule.md", constants not reachable from CLI/env, never passes on missing data, stdlib-only, usage per subcommand.
- Imports (52-59): `from __future__ import annotations`, `argparse/json/math/sys`, `Callable, Mapping, Sequence`, `Literal, TypedDict, cast`.
- Frozen-constant block (67-110) with `#:` doc comments and `Literal` aliases:
```python
Arm = Literal["a0", "a0a", "a0b", "a2", "a21", "a21s", "a21sc"]
StopMode = Literal["off", "on"]
ThroughputConfig = Literal["t50-p4", "t400-p4", "t50-p2", "t400-p2"]
#: D-14/D-15 move-quality regression margin on the argmaxLine pick.
MQ_REGRESSION_MARGIN = 0.05
```
New constants: `DispatchArm = Literal["round", "continuous"]`, `MQ_SIGNED_MARGIN = 0.025` (k=1.5), `MQ_REPEATS = 5`, D-03 allowance formula `max(1, ceil(max_pairs |N_rs|))`, `THROUGHPUT_SHIP_GAIN = 0.15`, `THROUGHPUT_MAX_REGRESSION = 0.03`, `WEBGPU_MAX_RATIO = 1.03`, reuse `CALIBRATION_THRESHOLD_MAIA = 85.0`, `CALIBRATION_THRESHOLD_SF = 53.542812708469995`. Reuse calibration reducer by importing `engine_throughput_226_calibration as calib` and `calibration_parity_verdict` (line 61-63), do not re-implement. Exit codes `EXIT_INCOMPLETE` / `EXIT_INVALID` (round-repeat diff -> invalid).

### `tests/scripts/test_engine_dispatch_227_verdict.py`

**Analog:** `tests/scripts/test_engine_throughput_226_verdict.py:1-30`: drive only via `main(argv)`, sys.path bootstrap:
```python
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from scripts.engine_throughput_226_verdict import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_INVALID,
```
Include a test pinning frozen constants to accept-rule numbers.

---

### `frontend/src/dev/engineBench/EngineBenchPage.tsx` + `App.tsx` route (D-06)

**Gate analog:** `frontend/src/lib/devClock.ts:26`:
```typescript
/** True only in the Vite dev build — a compile-time constant, so prod tree-shakes the feature. */
export const DEV_CLOCK_ENABLED = import.meta.env.DEV;
```
**Route analog:** `App.tsx:53-64` `const BotsPage = lazy(() => import('./pages/Bots'));` -> mount as `{import.meta.env.DEV && <Route path="/dev/engine-bench" .../>}` outside auth wrappers. Worker init shape from `maiaWorkerHost.ts:525-540`; backend probe `ortRuntimeSource.ts` `probeOrtBackend`. Refuse unless `isSecureContext && crossOriginIsolated`. `data-testid` on every control, `text-sm` minimum (frontend/CLAUDE.md). Gate check: `npm run build` then grep `dist/` for a unique marker, expect 0 hits. Delete page + route at phase end; knip must stay clean.

---

### Interleave driver (new)

**Partial analog:** `bin/preset-supervisor.sh` (shell style, resume-on-crash), and the protocol recorded in `reports/data/engine-throughput-226/retest-2026-10-02/driver.log` + `reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md` (load-average gate < 2.0, rotated order, >= 3 rounds). Add `/proc/loadavg` logging and a ~15 s machine-speed probe before each step. Runs are launched inline from the orchestrator (`setsid nohup` + Monitor), never backgrounded in an executor.

---

### `reports/continuous-dispatch-227/` docs

- `accept-rule.md`: copy structure of `reports/engine-throughput-226/accept-rule.md` (frozen constants table, sequencing, invalid states). Must be committed before any continuous MQ run (Pitfall 3).
- `design.md`: disposition table per RESEARCH Q6 (X-1..X-12, Y-1..Y-14, N-1..N-4) against `reports/continuous-dispatch/apply-order-design.md` §9b/§9d; reviewer briefing claims (a)-(f).
- Overrides: separate files `override-<date>-*.md`, never rule edits.

## Shared Patterns

### "Omitted = old behavior" optional flags
**Source:** `types.ts:61` (`gradeRoot?`), `types.ts:107` (`stopRule?`). **Apply to:** `dispatchMode` in `SearchBudget`, every harness flag (`--dispatch-mode` default round, `--ladder-only`, `--repeats` default 1). Existing tests stay on round mode with zero edits.

### Cancellation via AbortSignal
**Source:** `workerPoolDispatch.ts:285-313` (drop unstarted / `stop` in-flight / settle empty Map, `{ once: true }`), `maiaQueue.ts:60-69`. **Apply to:** mctsSearch inner controller, Node SF pools. Never apply a result settled after abort (empty Map becomes `NEUTRAL_EXPECTED_SCORE`, `mctsSearch.ts:459`).

### Fix-site comments + mutation checks
**Source:** `workerPoolDispatch.ts:301-305` ("Bug fix (quick 260731-s0z, FIX-4): ..."), `mctsSearch.roundFill.test.ts:27-31` mutation-check paragraph. **Apply to:** FIFO tie-break, harness abort, Maia worker move, every continuous-mode guard; record revert-and-fail results in SUMMARY.

### Frozen pre-registration
**Source:** `scripts/engine_throughput_226_verdict.py:67-110` + `reports/engine-throughput-226/accept-rule.md`. **Apply to:** 227 accept rule and twin; constants not CLI-reachable; owner overrides as separate docs.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Committed interleave driver with machine-speed probe | script | batch | 226 driver was ad hoc and not committed; only its log exists. Use RESEARCH Q8 spec + partial shell analog above |

## Metadata

**Analog search scope:** `frontend/src/lib/engine/`, `frontend/src/lib/`, `frontend/src/App.tsx`, `scripts/`, `scripts/lib/`, `tests/scripts/`, `bin/`, `reports/engine-throughput-226/`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-02
