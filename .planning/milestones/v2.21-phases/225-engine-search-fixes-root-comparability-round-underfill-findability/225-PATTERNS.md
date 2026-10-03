# Phase 225: Engine Search Fixes - Pattern Map

**Mapped:** 2026-09-27
**Files analyzed:** 17 (from RESEARCH.md "Recommended file touch list")
**Analogs found:** 16 / 17 (converter script is conditional, no analog needed unless the fail branch fires)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/engine-move-quality.mjs` (new) | utility (measurement CLI) | batch | `git show b1764a83^:scripts/engine-wdl-leaf-quality.mjs` + `scripts/engine-dispatch-stop-rule.mjs` | exact |
| `scripts/engine-dispatch-stop-rule.mjs` (flags `--no-stop-rule`, `--root-trace`, `--guard-window`) | utility | batch | itself, `parseArgs` switch 151-209, `runSelfTest` 307+ | exact |
| `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` (new) | test | request-response (fake providers) | `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` | exact |
| `frontend/src/lib/engine/mctsSearch.ts` | service (search) | event-driven rounds | itself: `isClosed`/`propagateClosure`/`isPending` | exact |
| `frontend/src/lib/engine/types.ts` | model | n/a | `BotStopRule` 57-66 | exact |
| `frontend/src/lib/engine/botBudget.ts` | config | n/a | `FLAWCHESS_BOT_STOP_RULE` | exact |
| `frontend/src/lib/engine/findability.ts`, `treeCommon.ts` | utility | transform | themselves | exact |
| `__tests__/mctsSearch.test.ts`, `findability.test.ts`, `fallbackExpectimax.test.ts`, `selectBotMove.test.ts`, `frontend/src/hooks/useFlawChessEngine.test.tsx` | test | - | themselves | exact |
| `reports/engine-search-fixes-225/accept-rule.md` | doc (decision contract) | - | `reports/bot-parity-199/accept-rule.md`, `reports/continuous-dispatch/accept-rule.md` | exact |
| `reports/engine-search-fixes-225/d02-allowance.md`, `report.md` | doc | - | `reports/bot-parity-199/report.md`, `reports/continuous-dispatch/report.md` | role-match |
| machine-readable twin of accept rule | utility | transform | `scripts/calibration_parity_verdict.py` (named in bot-parity-199/accept-rule.md header as its twin, "five constants carry these exact numbers") | role-match |
| `docs/flawchess-engine-explained-2026-07-06.md`, `CHANGELOG.md` | doc | - | themselves | exact |
| `scripts/<converter>` (conditional) | utility | transform | none | no analog |

## Pattern Assignments

### `scripts/engine-move-quality.mjs` (new, batch CLI)

**Primary analog:** `git show b1764a83^:scripts/engine-wdl-leaf-quality.mjs` (deleted script; the maia-blindness runner). **Arg/self-test shape:** `scripts/engine-dispatch-stop-rule.mjs`.

**Header docblock + usage** (wdl-leaf-quality 1-50): shebang `#!/usr/bin/env node`, a `/** ... */` docblock stating which accept rule it implements, and a `Usage:` block invoked as
```
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-wdl-leaf-quality.mjs \
  [--fixture fixtures/engine/maia-blindness.tsv] [--fens path/to/fens.txt] ...
```
`--help` prints this docblock (dispatch-stop-rule 378-380: `fs.readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0]`).

**Imports** (wdl-leaf-quality 55-65): reuse, never duplicate, engine bring-up:
```js
import { spawnStockfish, createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { makeNodeProviders, nodeGrade, resetMaiaRunMemo, maiaInferenceStats } from './lib/calibration-providers.mjs';
import { mctsSearch } from '@/lib/engine/mctsSearch';
import { evalToExpectedScore } from '@/lib/liveFlaw';
```
Import `FLAWCHESS_BOT_STOP_RULE` / `FLAWCHESS_BOT_MAX_NODES` from `@/lib/engine/botBudget` for defaults (as dispatch-stop-rule `parseArgs` defaults at 152-165 do). Toggle stop rule via a `--no-stop-rule` boolean (like `case 'maia-fifo': args.maiaFifo = true; break;` at dispatch-stop-rule ~182).

**parseArgs** (dispatch-stop-rule 136-209): `requireFlagValue` / `parsePositiveIntFlag` helpers, `args` defaults object, `--help`/`--self-test` handled before the `switch`, `default: throw new Error(\`Unknown flag --${key}\`)`. Export `parseArgs`.

**Fixture loader** (wdl-leaf-quality 168-199, `loadFixtureRows`): `#` preamble filtered, header row, tab split, per-row field-count error. Fixture is `fixtures/engine/maia-blindness.tsv` (exists, tracked). Follow with chess.js legality precondition before spawning engines (`validateFixtureIntegrity`, ~201).

**Grading the pick** (wdl-leaf-quality ~346-356, `gradeChosenMoves`): `nodeGrade(engine, fen, dedupedUcis, gradeDepth)`, mover from `fen.split(' ')[1]`, score via `evalToExpectedScore(grade.evalCp, grade.evalMate, mover)`. Phase 225 scores the bot's `argmaxLine` pick (D-13); `rankedLines[0]` report-only.

**Self-test** (dispatch-stop-rule 301-370): `runSelfTest()` with local `check(cond, label)` printing `SELF-TEST ok:` / `SELF-TEST FAILED:`, exercising parseArgs only (unknown flag throws, required-flag checks, tmp fens file via `os.tmpdir()`). `main()` returns exit code:
```js
if (args.selfTest) {
  const passed = runSelfTest();
  console.log(passed ? '\nSelf-test: ALL CHECKS PASSED' : '\nSelf-test: FAILURES ABOVE');
  return passed ? 0 : 1;
}
```
**Entrypoint guard** (dispatch-stop-rule 460-463):
```js
if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const code = await main();
  process.exit(code);
}
```
Output: TSV via `fs.writeFileSync(outPath, \`${tsv}\n\`)` into `--out-dir` (dispatch-stop-rule ~452). Call `pool.quitAll()` before return.

### `scripts/engine-dispatch-stop-rule.mjs` (modify)
Add `case 'no-stop-rule'` (boolean, no `i++`), `case 'root-trace'` (boolean), `case 'guard-window'` (`parsePositiveIntFlag` or a float parse with same error style) to the switch at 175-199; extend `runSelfTest` with one check per new flag. This commit is A0 (Pitfall 3), engine code untouched.

### `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` (new)
**Analog:** `mctsSearch.test.ts`.
- Imports (50-57): `vitest`, `chess.js`, `../mctsSearch`, types `EngineProviders, SearchBudget, MoveGrade` from `../types`.
- Fake providers (136-165): `makeFixedPolicy(byFen, calls?)` returns `byFen[fen] ?? uniformPolicyFromLegalMoves(fen)`; `makeFixedGrade(byFen, calls?)` defaults to `{ evalCp: 0, evalMate: null, depth: 10 }` and records `candidateUcis`. These are file-local; copy them (or the planner may extract to a shared helper, but not required).
- Test shape (168-176):
```ts
const budget: SearchBudget = { maxNodes: 1, elo: NEUTRAL_BUDGET_ELO, maxPlies: 4, concurrency: 1 };
const providers: EngineProviders = { policy: makeFixedPolicy({...}), grade: makeFixedGrade({...}) };
const snapshot = await mctsSearch(FEN, budget, providers, () => {}, freshSignal());
```
For D-08 round-fill: set `concurrency: 4`, record `calls` on the grade/policy fake and assert per-round dispatch count equals `concurrency` (use a deferred/gated fake grade to observe round boundaries). Put it in a `describe('mctsSearch — D-08 round fill', ...)`, matching `describe('mctsSearch — <ID> <topic>')` naming.

### `frontend/src/lib/engine/mctsSearch.ts` (per-round block flag + guard)
**Flag analog:** `EngineNode.isPending` (97) / `isClosed` (107), initialized `false` in both node factories (122/125, 162/165). Add `isBlocked: boolean` beside them, initialized `false` in both factories.

**Filter site** (310-311):
```ts
if (!child.isPending && !child.isClosed) candidates.push(child);
...
if (candidates.length === 0) return null;
```
becomes the block-and-restart per RESEARCH Pattern 1 (non-root: set `isBlocked`, push onto round-owned `blocked`, restart at root; root: return null). `selectPath(root, maxPlies)` signature at 287 gains `blocked: EngineNode[]`.

**Termination-comment analog** (fill loop 545-548, `propagateClosure` 263-277 "each node closes at most once"): mirror it for "each node blocks at most once per round". Clear flags after the fill loop (~after 592, before `Promise.all`).

**Guard analog** (`rootChildValueExtremes` 198-221, `stopRuleSatisfied` 245-260): extend `entries` to `{ uci, value, settled: child.visits >= 1 || child.isClosed }`; keep stability update lines unconditional; clear-winner disjunct gains `&& !hasUnsettledInWindow` with window `rule.marginThreshold + rule.<allowance>`.

### `frontend/src/lib/engine/types.ts` (`BotStopRule` 57-66)
Add a required field with the same one-line `/** D-xx: ... */` doc per field. Required (not optional) so omitting it is a `tsc -b` error.

## Shared Patterns

### Accept-rule decision contract
**Source:** `reports/bot-parity-199/accept-rule.md` 1-10, `reports/continuous-dispatch/accept-rule.md` 1-16.
**Apply to:** `reports/engine-search-fixes-225/accept-rule.md`.
- Title `# <topic> — accept rule`, then `**Committed:** <date>, before any <run> has run.`
- States it discharges named CONTEXT decisions; "a decision contract, not a narrative"; thresholds fixed in advance; not editable once data exists; deviations go in a separate dated override doc (shape: `reports/grading-ladder/override-2026-07-31.md`).
- Names its machine-readable twin and that the twin's constants carry the exact numbers (bot-parity-199 lines 7-9 -> `scripts/calibration_parity_verdict.py`).
- Numbered `## 1. Run parameters` section with pinned, executable commands; criteria "in evaluation order". Record A0/A2/A21 SHAs (A2/A21 filled in report).

### Script engine bring-up
Always via `scripts/lib/node-engine-providers.mjs` + `scripts/lib/calibration-providers.mjs`; run with `--import ./scripts/lib/frontend-alias-hook.mjs` so `@/` resolves.

### Long runs
Per memory notes: harness runs go from the orchestrator (setsid nohup + Monitor), not backgrounded inside an executor.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `scripts/<converter>` (A0 cells -> `{"cells":[...]}` for `--old-json`) | utility | transform | Conditional on the fail branch; follow parseArgs/self-test shape above if built |

## Metadata
**Analog search scope:** `scripts/`, `frontend/src/lib/engine/`, `reports/`, git history (b1764a83^)
**Pattern extraction date:** 2026-09-27
