# Phase 226: Browser Engine Throughput (underfill re-land + root grade split) - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 27 new/modified
**Analogs found:** 26 / 27 (all analog paths verified with `git ls-files`)

Commit order this map assumes (RESEARCH Pattern 9): **T** (tooling) → step-0 runs → design-inputs → **A0** (accept rule + verdict constants) → **A2** → **A21** → **A21S**. The "Commit" column says where each file lands.

## File Classification

| New/Modified File | Commit | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|---|
| `frontend/src/lib/engine/mctsSearch.ts` (underfill) | A2 | engine core | batch rounds | cherry-pick `d428a0194 82b910bb2 a9d5113ef` | exact (byte-reuse) |
| `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` | A2 | test | batch | same cherry-picks | exact |
| `mctsSearch.ts`, `types.ts`, `botBudget.ts`, `__tests__/mctsSearch.test.ts`, `frontend/src/hooks/useFlawChessEngine.test.tsx` (root guard) | A21 | engine core / config / test | request-response | cherry-pick `4a13b2f3a 27beff12f` | exact |
| `frontend/src/lib/engine/mctsSearch.ts` (one `gradeRoot` routing line, D-18) | A21S | engine core | request-response | `mctsSearch.ts:477-483` (`gradeWithDepth` call) | exact |
| `frontend/src/lib/engine/types.ts` (`EngineProviders.gradeRoot?`) | A21S | type contract | - | `types.ts:26-47` (optional `signal` precedent) | exact |
| `frontend/src/lib/engine/rootSplit.ts` (NEW) | A21S | utility (pure) | transform | `select.ts:44` `truncateAndRenormalize` (pure helper module style) | role-match |
| `frontend/src/lib/engine/workerPoolDispatch.ts` (`gradeRoot`) | A21S | service (pool) | request-response fan-out | `workerPoolDispatch.ts:161-274` `grade()` + `:72-80` `dispatchNext` | exact |
| `frontend/src/lib/engine/workerPoolState.ts` (`QueuedGradeRequest` write flag) | A21S | model | - | same file's `QueuedGradeRequest` | exact |
| `frontend/src/lib/engine/workerPool.ts` (interface + facade) | A21S | service facade | - | `workerPool.ts:122-145` `grade` member | exact |
| `frontend/src/lib/engine/__tests__/rootSplit.test.ts` (NEW) | A21S | test | transform | `__tests__/mctsSearch.roundFill.test.ts` header/fixture style | role-match |
| `frontend/src/lib/engine/__tests__/workerPool.test.ts` ("root split" block) | A21S | test | request-response | same file, `describe('createWorkerPool: grade() dispatch')` :365 + grade-cache block :1229 | exact |
| `frontend/src/hooks/useFlawChessEngine.ts`, `useBotGameEngineDispatch.ts` | A21S | hook wiring | - | `useFlawChessEngine.ts:381`, `useBotGameEngineDispatch.ts:90-97` | exact |
| `scripts/lib/stockfish-pool.mjs` (`freeCount`, `gradeRoot`) | T | harness service | fan-out | same file `grade`/`withEngine` :224-300 | exact |
| `scripts/lib/calibration-providers.mjs` (`nodeGrade {clearHash}`, `makeNodeProviders gradeRootFn`) | T | harness provider | request-response | same file :356-465 | exact |
| `scripts/lib/calibration-determinism.check.mjs` (`--no-clear-hash` arm, D-03) | T | check script | batch | same file :147-237 | exact |
| `scripts/calibration-harness.mjs` (`setupHarnessEngines` gradeRoot) | T | harness | - | same file :374-383 | exact |
| `scripts/engine-dispatch-stop-rule.mjs` (`--pool-size`, `createGradePool.gradeRoot`) | T | measurement CLI | batch | same file :190-245, :282-336, :405+ | exact |
| `scripts/engine-grading-depth-ab.mjs` (`--pool-size`, `--self-test`, split closure) | T | measurement CLI | batch | `engine-dispatch-stop-rule.mjs` self-test :405-450 | role-match |
| `scripts/engine-move-quality.mjs` (`--pool-size`, gradeRoot wiring, 226 fixture case) | T | measurement CLI | batch | same file :120-330 | exact |
| `scripts/engine-search-trace.mjs` (NEW, D-13) | T | measurement CLI | event-driven (wrapped providers) | `engine-dispatch-stop-rule.mjs` (argparse/self-test/`createGradePool`) + roundFill test's round-counting trick | role-match |
| `scripts/build-move-quality-fixture.mjs` (NEW, D-14) | T | generator CLI | file-I/O | `engine-move-quality.mjs` `loadFixtureRows`/`validateFixtureIntegrity` :188-230 | role-match |
| `fixtures/engine/move-quality-226.tsv` (NEW) | T | fixture | - | `fixtures/engine/maia-blindness.tsv` | exact |
| `bin/preset-supervisor.sh` (`PRESET_SUPERVISOR_SEED`) | T | ops script | - | same file's `PRESET_SUPERVISOR_GAMES`/`_ANCHORS` env hooks :24-29, :80-84 | exact |
| `scripts/engine_throughput_226_verdict.py` (NEW) | A0 | verdict CLI | batch | `scripts/engine_search_fixes_verdict.py` | exact |
| `tests/scripts/test_engine_throughput_226_verdict.py` (NEW) | A0 | test | batch | `tests/scripts/test_engine_search_fixes_verdict.py` | exact |
| `reports/engine-throughput-226/accept-rule.md` (+ `design-inputs.md`, `report.md`, `verdict.json`) | A0 / later | doc contract | - | `reports/engine-search-fixes-225/accept-rule.md` | exact |
| Conditional refit (D-11/D-20): `reports/data/bot-curves-internal-scale.json`, `bot-strength-lookup.json`, `persona-calibration.json`, `frontend/src/generated/botStrengthCurves.ts`, `personaCalibration.ts` | post-verdict | generated | batch | chain `bin/run_bot_curves_sweep.sh` → `scripts/calibration_anchor_fit.py` → `scripts/gen_bot_strength_curves.py`; `bin/run_persona_calibration_sweep.sh` → `scripts/calibration_persona_fit.py` → `scripts/gen_persona_calibration.py` | exact (run, don't edit) |
| `docs/flawchess-engine-explained-2026-07-06.md`, `CHANGELOG.md` | final | docs | - | existing files | - |

Step-0 throwaway scripts `.planning/research/perf-profiling-2026-09-28/profile_search.mjs` and `split_root.mjs` are tracked and may be extended in place (RESEARCH Pattern 2/10); they are not gate instruments.

## Pattern Assignments

### A2 / A21 cherry-picks (no new pattern needed)

- A2: `git cherry-pick d428a0194 82b910bb2 a9d5113ef` (failing round-fill test → block-and-restart `selectPath` fix → c=2 determinism + fully-blocked tests + module-header update). Diffstat: `mctsSearch.ts` +82/-20, `mctsSearch.roundFill.test.ts` +162 then +105.
- A21: `git cherry-pick 4a13b2f3a 27beff12f` (`botBudget.ts` +21 `ROOT_GUARD_BOOST_ALLOWANCE`, `types.ts` +10, `mctsSearch.ts` +75/-40, `mctsSearch.test.ts` +147, then closed-top guard test + `useFlawChessEngine.test.tsx` well-formedness).
- RESEARCH verified all five apply cleanly to current HEAD; `mctsSearch.ts` unchanged since 225-A0 (`1b5313b96`).
- Commit-message pattern to copy for the mutation-check record (from `a9d5113ef`): "Mutation check (D-08, project mutation-test rule) performed and reverted, not committed: temporarily restored ... Both round-fill tests failed as expected ... Fix restored and reconfirmed green before this commit."
- Any D-13 fix must stay inside `mctsSearch.ts` (A0→A2 content assertion).

---

### `frontend/src/lib/engine/mctsSearch.ts` (A21S routing line, D-18)

**Analog:** the existing grade call, `mctsSearch.ts:471-483`:
```typescript
  // Phase 195 LADDER-02: the grading rung is resolved HERE, not inside
  // WorkerPool, because `leaf.depth` — the tree depth-from-root — is only
  // known inside the search orchestrator.
  const gradeWithDepth = providers.grade as GradeWithLadderDepth;
  const grades = await gradeWithDepth(
    leaf.fen,
    candidateUcis,
    signal,
    gradingDepthForTreeDepth(leaf.depth),
  );
```
Change only the provider selection: `const gradeFn = (leaf.isRoot && providers.gradeRoot) ? providers.gradeRoot : providers.grade;` then cast as `GradeWithLadderDepth`. Keep the 8XN-7 block (`:506`, `if (grades.size === 0 && !signal.aborted && !leaf.isRoot)`) untouched: root exemption means an empty split grade degrades exactly like a failed single-call root grade. Nothing else in the file changes (round barrier, apply order).

### `frontend/src/lib/engine/types.ts` (A21S)

**Analog:** `types.ts:38-46`, the optional-member precedent:
```typescript
  /**
   * ... `signal` (Phase 194 ABORT-01/03) is OPTIONAL so a
   * two-argument implementation/call site stays structurally assignable to
   * this interface — widening it to required would break every existing
   * fabricated-in-tests provider and the Node calibration providers outside
   * the frontend `tsc` project (ABORT-03).
   */
  grade(fen: string, candidateUcis: string[], signal?: AbortSignal): Promise<Map<string, MoveGrade>>;
```
Add `gradeRoot?(...)` with the same signature and a doc comment in this style (optional so every test fake and `fallbackExpectimax` stays byte-identical). Run `npm run build` (tsc) and `npm run knip`.

### `frontend/src/lib/engine/workerPoolDispatch.ts` (A21S `gradeRoot`)

**Analog:** `grade()` in the same file (`:161-274`) and `dispatchNext` (`:72-80`).

Idle-slot predicate to reuse (`:72-80`):
```typescript
export function dispatchNext(state: PoolState, ops: PoolOps): void {
  for (const slot of state.slots) {
    if (state.pending.length === 0) return;
    if (slot.state !== 'idle' || !slot.isReady || slot.current !== null) continue;
    const req = dequeueHighestPriority(state.pending);
    if (!req) return;
    sendGo(state, ops, slot, req);
  }
}
```
Guard prologue to copy verbatim into `gradeRoot` (`:170-213`): empty candidates → `new Map()` (WR-05); `signal?.aborted` → `new Map()` (WR-01); full-set `state.gradeCache.read(fen, candidateUcis, resolvedGradingDepth)` hit → return; `ops.ensureSpawned()`; `slots.length === 0 && !spawnInFlight` and `noLiveSlotRemains(state)` → empty. Then k = idle-and-ready count (plus `!slot.dead`, and only if `state.pending.length === 0`), capped by candidates and `ROOT_SPLIT_MAX_SHARDS`; `k <= 1` → `return grade(state, ops, fen, candidateUcis, signal, gradingDepth)`.

Listener-leak-safe settle wrapper to reuse per sub-request (`:214-265`, Pitfall 4 / WR-02):
```typescript
    let onAbort: (() => void) | null = null;
    const settle = (grades: Map<string, MoveGrade>): void => {
      if (onAbort && signal) signal.removeEventListener('abort', onAbort);
      onAbort = null;
      resolve(grades);
    };
```
and the in-flight abort branch (`:252-262`: `ops.armStopWatchdog(slot); slot.worker.postMessage('stop'); slot.stopPending = true; slot.state = 'stopping'; settle(new Map());`).

Cache write rule (`:146-155`). The single write site is currently the `bestmove` branch:
```typescript
      // This `bestmove` branch is the ONLY caller of gradeCache.write — the
      // abort path, stopAll, terminate, and onerror all settle without
      // writing, which is precisely what keeps a partial grade out of the
      // cache. Do not "helpfully" add a write to one of those settle paths.
      state.gradeCache.write(req.fen, req.gradingDepth, slot.accumulator);
      req.resolve(slot.accumulator);
```
Sub-requests must skip this write (new `writeCache: false` flag on `QueuedGradeRequest`, `workerPoolState.ts`) and carry a "completed via bestmove" marker; the group's all-complete path does the one merged `gradeCache.write`, and this comment must be updated to name that second, success-only site. Any shard not completed → stop siblings, resolve empty (L-2), never a partial Map.

### `frontend/src/lib/engine/workerPool.ts` (A21S)

**Analog:** the `grade` member of `WorkerPool` (`:122-145`) and the `grade as dispatchGrade` import alias at `:80`. Add `gradeRoot` the same way (import `gradeRoot as dispatchGradeRoot`, facade forwards `state, ops`).

### `frontend/src/lib/engine/rootSplit.ts` (NEW, A21S)

**Analog (style):** `select.ts:44` `export function truncateAndRenormalize(policy): Map<string, number>` (pure, typed, no I/O). Exports: `ROOT_SPLIT_MAX_SHARDS` (named constant, no magic number), `partitionCandidates(cands, k)` round-robin `i % k` (as `split_root.mjs` does), `mergeShardGrades(cands, shards)` in original candidate order. Every export must be imported (knip): pool + harness lazy import.

### `frontend/src/lib/engine/__tests__/workerPool.test.ts` (A21S "root split" block)

**Analog:** same file. MockWorker + init driver (`:123-185`):
```typescript
/** Drive one mock worker through the full UCI init sequence (uciok -> Hash -> isready -> readyok). */
function driveInit(worker: MockWorker): void {
  worker.simulateMessage('uciok');
  worker.simulateMessage('readyok');
}
```
Describe setup + a grade-drive test (`:365-395`):
```typescript
describe('createWorkerPool: grade() dispatch', () => {
  beforeEach(() => {
    stubDesktopSizing(6); // computePoolSize() -> 4 slots
    stubWorkerCtor();
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('grade() resolves a Map keyed by pv[0] (UCI), white-POV normalized', async () => {
    const pool = createWorkerPool();
    const gradePromise = pool.grade(TEST_FEN, ['e7e5', 'c7c5']);
    const worker = createdWorkers[0]!;
    driveInit(worker);
    worker.simulateMessage('info depth 10 multipv 1 score cp 50 nodes 1000 pv e7e5');
    worker.simulateMessage('info depth 10 multipv 2 score cp 30 nodes 1000 pv c7c5');
    worker.simulateMessage('bestmove e7e5');
    ...
```
Cases (RESEARCH Wave 0): disjoint cover of candidates across `go ... searchmoves` lines of k workers; exactly one cache write (second `grade(fen,[uci])` subset hit, no partial entry after abort); one shard aborted/watchdog/slot death → whole result empty and siblings get `stop`; one slot busy → k = 3; pending non-empty → falls back to single grade; `stubDesktopSizing` with 2-slot sizing → k = 2. Use the grade-cache block (`:1229`) for cache assertions and the watchdog block (`:622`) for death paths. Mutation-check each by reverting (memory rule).

### `frontend/src/lib/engine/__tests__/rootSplit.test.ts` (NEW) and `mctsSearch.test.ts` "gradeRoot" routing

**Analog:** `mctsSearch.roundFill.test.ts` (from `d428a0194`): module doc comment naming decision IDs + mutation check, named fixture constants, then `import { describe, it, expect } from 'vitest'; import type { EngineProviders, ... } from '../types';`. Routing test: a fake provider with a `gradeRoot` spy asserts one call per search, root FEN only, and a provider without `gradeRoot` yields `toEqual` snapshots vs the current behavior.

### Hooks (A21S)

`frontend/src/hooks/useBotGameEngineDispatch.ts:90-97`:
```typescript
function buildBotMoveDeps(deadlineMs: number, queue: MaiaQueue, pool: WorkerPool): BotMoveDeps {
  return {
    policy: queue.policy,
    grade: pool.grade,
    ...
```
and `useFlawChessEngine.ts:381` `const providers: EngineProviders = { policy: queue.policy, grade: pool.grade };` Add `gradeRoot: pool.gradeRoot` beside `grade`. Check `BotMoveDeps` type accepts it.

---

### `scripts/lib/stockfish-pool.mjs` (T)

**Analog:** the `grade` closure and `withEngine` in the same file (`:224-300`):
```javascript
    grade: (fen, candidateUcis, signal, gradingDepth) =>
      withEngine(pool, (engine) => nodeGrade(engine, fen, candidateUcis, gradingDepth)),
```
`gradeRoot` = k from `freeCount()` (count `pool.busy` false over `pool.engines`), `Promise.all(shards.map(s => withEngine(pool, e => nodeGrade(e, fen, s, depth))))`, merge via `await import('@/lib/engine/rootSplit')` inside the body (module absent until A21S). Keep the long "BUG FIX (Phase 195, T-195-09)" style doc comment convention: declare all four params. Add the tripwire when `freeCount() !== size`. Pool option `clearHash` pinned on the pool object like `hashMb` (`:249-278`) so respawns match.

### `scripts/lib/calibration-providers.mjs` (T)

**Analog:** `nodeGrade` (`:418-465`) and `makeNodeProviders` (`:356-364`):
```javascript
export function makeNodeProviders(session, ort, gradeFn, options = {}) {
  const { maiaFifo = false } = options;
  return {
    policy: maiaFifo ? ... : ...,
    grade: gradeFn,
  };
}
```
Add `gradeRootFn` via `options` (only set the key when defined). In `nodeGrade`, the line to gate is `stockfish.send('setoption name Clear Hash');` (`:447`); add a 5th param `{ clearHash = true } = {}` and update the D-10 comment. Do not touch `evalPositionCpWithBest` (`:486`), adjudication keeps Clear Hash.

### `scripts/lib/calibration-determinism.check.mjs` (T, D-03)

**Analog:** same file, determinism block `:147-237`: named constants (`DETERMINISM_SEED = 42`, `DETERMINISM_STOCKFISH_PROCS = 2`), `setupHarnessEngines({ stockfishProcs })`, two `playGame` runs from `mulberry32(DETERMINISM_SEED)`, `assert.deepEqual(result2.moveUcis, result1.moveUcis, ...)`, `console.log('PASS: ...')`, `finally { pool.quitAll(); }`, `process.exit(0)`. The warm arm adds a grading-only pool with `clearHash: false` (adjudication/anchors on the other pool), asserts structure only (send spy: zero `Clear Hash` on grading pool), and reports divergence (first divergent ply, mean |Δes| re-graded at depth ≥ 18). Existing Clear-Hash assertion stays.

### `scripts/calibration-harness.mjs` (T)

**Analog:** `setupHarnessEngines` `:374-383`: `const pool = await createStockfishPool({ size: stockfishProcs }); ... makeNodeProviders(maiaCtx.session, maiaCtx.ort, pool.grade);` → pass `{ gradeRootFn: pool.gradeRoot }`. Check `selectBotMoveOnce` forwards `providers` unchanged.

### `scripts/engine-dispatch-stop-rule.mjs`, `engine-grading-depth-ab.mjs`, `engine-move-quality.mjs` (T)

**Flag parsing analog** (`engine-dispatch-stop-rule.mjs:210-218`):
```javascript
      case 'nodes': args.nodes = parsePositiveIntFlag(value, key); i++; break;
      case 'procs': args.procs = parsePositiveIntFlag(value, key); i++; break;
```
Add `case 'pool-size'` with default `null` → resolved to `args.procs` after the loop; keep `concurrency: args.procs` (depth-ab `:555, :613`) and feed `poolSize` into `createGradePool`/`createStockfishPool`. Document in the header usage block (`:50-85`).

**Grade pool analog** (`engine-dispatch-stop-rule.mjs:318-336`):
```javascript
export async function createGradePool(size) {
  const pool = await createStockfishPool({ size, hashMb: WORKER_HASH_MB });
  const grade = async (fen, candidateUcis, signal, depth) => {
    if (candidateUcis.length === 0) return new Map(); // mirror workerPool.ts WR-05
    return pool.run((engine) => runOneGo(engine, depth ?? GRADING_ROOT_DEPTH, fen, candidateUcis));
  };
  return { grade, resetAll: () => pool.newGameAll(), quitAll: () => pool.quitAll() };
}
```
Add `gradeRoot` beside `grade` using `pool.run` per shard over `runOneGo` (warm hash, must mirror `sendGo`), and return it.

**Self-test analog** (`engine-dispatch-stop-rule.mjs:405-450`): `runSelfTest()` with a `check(cond, label)` closure printing `SELF-TEST ok:` / `SELF-TEST FAILED:`, try/catch per `parseArgs` case asserting on message text. Use this for depth-ab's new `--self-test` and new `--pool-size` cases. Move quality's self-test (`engine-move-quality.mjs:295-345`) keeps `defaultRows.length === 12` and adds a `--fixture fixtures/engine/move-quality-226.tsv` integrity case (`loadFixtureRows` + `validateFixtureIntegrity`).

### `scripts/engine-search-trace.mjs` (NEW, T, D-13)

**Analogs:** CLI skeleton, `parseArgs`, `runSelfTest`, `createGradePool` import from `engine-dispatch-stop-rule.mjs`; round-id rule from `mctsSearch.roundFill.test.ts` header ("the run length of consecutive `policy()` calls between `onSnapshot` events is exactly one round's dispatch size"). Run with `node --import ./scripts/lib/frontend-alias-hook.mjs` from detached arm worktrees (alias hook resolves `@/` relative to itself).

### `scripts/build-move-quality-fixture.mjs` (NEW, T, D-14) + `fixtures/engine/move-quality-226.tsv`

**Analogs:** row shape and header comment block of `fixtures/engine/maia-blindness.tsv` (`# ...` purpose lines, then `id fen correct_move eval_gap_cp note source`); reader/validator `engine-move-quality.mjs:188-230` (`loadFixtureRows`, `validateFixtureIntegrity`) so the output is read unchanged. Source corpus `fixtures/tagger/detector_fixture_test.csv` (`PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating`). Order by SHA-1 of `PuzzleId` (never `hash()`), d20 MultiPV 2 via `createStockfishPool(...).run(fn)` (the "escape hatch" doc at `stockfish-pool.mjs:~310`), named constants `MIN_GAP_CP`, band quotas.

### `bin/preset-supervisor.sh` (T, D-19)

**Analog:** same file's env overrides (`:24-29`):
```bash
DIR="${PRESET_SUPERVISOR_DIR:-reports/data/sweep-${NAME}}"
GAMES_PER_CELL="${PRESET_SUPERVISOR_GAMES:-24}"
ANCHORS="${PRESET_SUPERVISOR_ANCHORS:-}"
```
Add `SEED="${PRESET_SUPERVISOR_SEED:-1}"` and replace the hard-coded `--seed 1` in `launch()` (`:80-84`):
```bash
  nohup node --import "$HOOK" "$HARNESS" \
    --blends "$BLEND" --elo "$ELO" \
    --games-per-cell "$GAMES_PER_CELL" --stockfish-procs 4 \
    --seed 1 --out-dir "$DIR" \
```
It must flow through `launch()` (single path for cold start and every resume), same rationale as the anchors comment above it.

---

### `scripts/engine_throughput_226_verdict.py` (NEW, A0)

**Analog:** `scripts/engine_search_fixes_verdict.py` (990 lines). Leave the 225 script read-only; import its generic readers.

Module docstring pattern (`:1-41`): "The machine-readable twin of `reports/.../accept-rule.md`: every threshold constant below carries the exact number from that document and is NOT reachable from any CLI flag, environment variable, or config file", stdlib-only, Sentry-exempt note, Usage with subcommands (`gates`, `reruns`, `branch`, `cells-to-json`).

Imports (`:43-61`):
```python
from __future__ import annotations
import argparse, csv, json, statistics, sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict

import calibration_anchor_fit as anchor_fit
from calibration_parity_verdict import (CellKey, CellStats, ParityVerdictResult, Verdict, fit_new_cells)
```
Add `from engine_search_fixes_verdict import read_single_tsv, _ladder_rows, cells_to_payload` (and `evaluate_throughput` if the shape fits).

Frozen-constants block (`:65-99`): banner comment, one `#:` doc line per constant (`THROUGHPUT_BUDGETS`, `EXPECTED_MQ_POSITIONS`, `MQ_REGRESSION_MARGIN = 0.05`, `DEFAULT_DATA_DIR`, `EXIT_INCOMPLETE = 2`). 226 adds: arm `Literal["a0a","a0b","a2","a21","a21s"]`, `GAMES_PER_CELL`, powered thresholds (±85 Maia / ±50 SF), z-based shape guard (1.96), MQ allowance floor `max(1, d0)`, split grade-content bound and stop-rule wall ceiling (values from design-inputs).

Validation style (`:309-331`): raise `ValueError` on runner/twin disagreement and on row-count mismatch, never silently trust:
```python
def _mq_rows_by_id(rows, label):
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != EXPECTED_MQ_POSITIONS:
        raise ValueError(f"evaluate_move_quality: expected {EXPECTED_MQ_POSITIONS} rows for {label}, got {len(by_id)}")
```
TypedDict results (`:129-200`), `required_reruns` (`:406`), incomplete → `EXIT_INCOMPLETE`. Pooling trap: pre-sum A0a+A0b by (cell, anchor) before `fit_new_cells` (`calibration_anchor_fit.py:565` overwrites).

### `tests/scripts/test_engine_throughput_226_verdict.py` (NEW, A0)

**Analog:** `tests/scripts/test_engine_search_fixes_verdict.py` `:1-60`: docstring, `sys.path` bootstrap, drive only through `main(argv)` with a synthetic per-arm layout under `tmp_path`, assert on exit code and written verdict JSON:
```python
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from scripts.engine_search_fixes_verdict import (EXIT_INCOMPLETE, MQ_REGRESSION_MARGIN, main)
POSITIONS_16 = [f"p{i:02d}" for i in range(16)]
MQ_IDS_12 = [f"mq{i:02d}" for i in range(12)]
THROUGHPUT_HEADER = ("position","depth","wall_ms","grade_cpu_ms","nodes_evaluated","maia_peak_inflight","maia_fifo")
MQ_HEADER = ("id", "delta_bot", "verdict_bot", "delta_analysis", "verdict_analysis")
```
Replace `MQ_IDS_12` with the new fixture count. Must pass `uv run ty check ... tests/ scripts/`.

### `reports/engine-throughput-226/accept-rule.md` (A0)

**Analog:** `reports/engine-search-fixes-225/accept-rule.md`. Opening paragraph pattern: "**Committed:** <date>, before any gate run ... a decision contract, not a narrative ... any deviation is a separate dated override document, in the shape of `reports/grading-ladder/override-2026-07-31.md`, never an edit to this file." Section skeleton: `## 1. Arms` (+ `### Content assertions`, `### Worktree procedure`), `## 2. Recorded design inputs`, `## 3. Run parameters` (exact command lines per arm, `### Data layout`, `### Sequencing`), `## 4. Criteria, in evaluation order`, `## 5. Report-only`, `## 6. Item decisions`, `## 7. What must not happen`. 226 changes: arms A0a/A0b (seed 2)/A2/A21/A21S, powered N=50 per (cell, anchor), z-based shape guard, paired MQ rule, D-11 refit branch instead of 225's never-refit. Secondary template: `reports/continuous-dispatch/accept-rule.md`.

## Shared Patterns

### Determinism and abort (engine)
Source: `mctsSearch.ts:484-515` (8XN-7 root exemption) and `workerPoolDispatch.ts:161-274`. Apply to all A21S code: never resolve a partial Map; aborted/failed → `new Map()`; one listener per group, detached on settle.

### Harness provider signature
Source: `stockfish-pool.mjs` `grade` doc (T-195-09). Every harness `grade`/`gradeRoot` declares `(fen, candidateUcis, signal, gradingDepth)`; an undeclared 4th param silently drops the ladder depth.

### Self-test convention for `.mjs` tools
Source: `engine-dispatch-stop-rule.mjs:405-450`, `engine-move-quality.mjs:295-345`. `check(cond, label)`, no engines spawned, exit non-zero on any failure, `--help`/`--self-test` bypass required flags.

### Frozen-constants twin
Source: `engine_search_fixes_verdict.py:65-99` + accept-rule §intro. Constants fixed in the A0 commit together with the doc; never CLI-reachable.

### Stacked arms + content assertions
Source: `reports/engine-search-fixes-225/accept-rule.md` §1 "Content assertions" and "Worktree procedure". Allowed-path lists per arm pair are in RESEARCH Pattern 9.

### Mutation checks
Source: commit messages `a9d5113ef`, `27beff12f`. Revert the fix, confirm the new test fails, restore, record in SUMMARY.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (fan-out/merge logic inside `workerPoolDispatch.gradeRoot`) | service | fan-out with group abort | No existing multi-request group settle in the pool; compose from `grade()`'s settle wrapper + `dispatchNext` predicate per RESEARCH Pattern 1 and Code Examples |

## Metadata

**Analog search scope:** `frontend/src/lib/engine/`, `frontend/src/hooks/`, `scripts/`, `scripts/lib/`, `tests/scripts/`, `bin/`, `reports/engine-search-fixes-225/`, `fixtures/engine/`, Phase 225 commits
**Files scanned:** ~25
**Pattern extraction date:** 2026-09-28
