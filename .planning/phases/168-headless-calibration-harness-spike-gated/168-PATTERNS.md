# Phase 168: Headless Calibration Harness (spike-gated) - Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 8 (new/refactored) + 1 conceptual grid-loop file
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/calibration-harness.mjs` | controller / orchestrator (CLI entrypoint) | batch (grid sweep → TSV) | `scripts/gem-elo-calibration.mjs` (`main()`, CLI parsing, TSV writer) | role-match (same shape, different inner loop: game-vs-game not position-grading) |
| `scripts/lib/node-engine-providers.mjs` | service (engine bring-up, refactored OUT of gem-elo) | request-response (UCI/ONNX process I/O) | `scripts/gem-elo-calibration.mjs` lines 375-507 (`createMaiaSession`, `StockfishUciEngine`, `spawnStockfish`, `resolveFrontendModule`) | exact (mechanical extraction, behavior-preserving) |
| `scripts/lib/calibration-providers.mjs` (Node `EngineProviders` adapter: `nodePolicy`/`nodeGrade`) | service (adapter) | request-response (UCI-keyed policy/grade) | **PRIMARY:** `frontend/src/lib/engine/workerPool.ts` `sendGo`/`handleLine` (lines 210-219, 233-267) for `grade()`; `frontend/src/lib/engine/maiaQueue.ts` for `policy()` shape. **NOT** gem-elo's `gradePosition` (SAN-keyed, all-legal-moves — wrong contract, Pitfall 1) | exact for `grade()` contract; role-match for `policy()` |
| `scripts/lib/calibration-anchors.mjs` (raw-Maia argmax + Stockfish-skill move choosers) | service (anchor movers) | request-response | New composition of `calibration-providers.mjs`'s `nodePolicy` + `node-engine-providers.mjs`'s `StockfishUciEngine`; no direct analog (first anchor-mover code in repo) | no analog (novel, but built from analog primitives) |
| `scripts/lib/calibration-openings.mjs` (curated opening FEN list) | config (static data module) | — | No analog — `temp/brilliants_no_stalemates.csv` is wrong semantics (tactical, not opening theory); build fresh per Open Question 1 | no analog |
| `scripts/calibration-harness.mjs` game loop (bot-vs-anchor single game) | controller (event-driven state machine) | event-driven (ply-by-ply until terminal/adjudicated) | No direct analog in `scripts/`; mirrors `frontend/src/lib/engine/treeCommon.ts`'s `terminalValue` (chess.js terminal checks) + `selectBotMove.ts`'s call contract | partial (compose gem-elo's loop skeleton + treeCommon's terminal checks) |
| `scripts/lib/calibration-elo.mjs` (`invertAnchorElo`/`combineAnchorEstimates`) | utility (pure math) | transform | `frontend/src/lib/scoreConfidence.ts` (`wilsonBounds`) reused directly; no existing Elo-inversion analog — new pure-function module | no analog for the math itself, but `wilsonBounds` import is exact reuse |
| `scripts/lib/calibration-parity.check.mjs` | test (parity assertion) | request-response (assert-and-exit) | `scripts/lib/gem-parity.check.mjs` (full file, 128 lines) | exact |
| `scripts/lib/frontend-alias-hook.mjs` | config (module resolution hook) | — | **UNCHANGED — reused verbatim**, do not modify | exact (verbatim reuse, not a new file) |

## Pattern Assignments

### `scripts/calibration-harness.mjs` (controller, batch orchestration)

**Analog:** `scripts/gem-elo-calibration.mjs`

**Header / doc-comment + imports pattern** (lines 1-57):
```javascript
#!/usr/bin/env node
/**
 * gem-elo-calibration.mjs — headless gem-move ELO calibration harness ...
 * Zero reimplementation drift (D-03): every gem/eval/encoding function below
 * is IMPORTED from the live frontend source via the `@/` alias resolve hook ...
 */
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

import {
  encodeBoard, maskAndSoftmax, eloToInput, MAIA_ELO_LADDER,
  NUM_SQUARES, PLANES_PER_SQUARE, POLICY_VOCAB_SIZE,
} from '@/lib/maiaEncoding';
import { parseInfoLine } from '@/hooks/uciParser';
```
For the new harness, add: `import { selectBotMove } from '@/lib/engine/selectBotMove';`, `import { mulberry32, fallbackMove } from '@/lib/engine/botSampling';`, `import { wilsonBounds } from '@/lib/scoreConfidence';`, and a `chess.js` `Chess` constructor import for terminal-state checks.

**CLI flag validation pattern** (lines 93-190, `requireFlagValue`/`parsePositiveIntFlag`/`parseArgs`/`validateRungs`):
```javascript
/** Returns the flag's value, or throws if it's missing (absent or itself a --flag). */
function requireFlagValue(value, key) {
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`Missing value for ${key}`);
  }
  return value;
}
```
Mirror this exactly for `--elo`, `--blends`, `--anchors`, `--games-per-cell`, `--seed`, `--out-dir` — WR-02's "every flag that consumes a value MUST validate it" discipline directly transfers (Security Domain V5 in RESEARCH.md).

**`validateRungs`** (line 178) — reuse verbatim (imported, not re-derived) to validate bot ELO rungs against `MAIA_ELO_LADDER` per D-08.

**Durable TSV writer pattern** (lines 566-627, `buildTimestamp`/`tsvColumns`/`tsvRowLine`/`openTsvWriter`):
```javascript
function openTsvWriter(filePath, rungs) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const stream = fs.createWriteStream(filePath, { encoding: 'utf8' });
  stream.write(`${tsvColumns(rungs).join('\t')}\n`);
  return {
    writeRow(row) { stream.write(`${tsvRowLine(row, rungs)}\n`); },
    close() { return new Promise((resolve, reject) => { stream.end((err) => (err ? reject(err) : resolve())); }); },
  };
}
```
Adapt `tsvColumns`/`tsvRowLine` to the new row shape per D-04 (bot-cell × anchor: games, W/D/L, score, color split, seed/budget/git-SHA/grid-params metadata). Keep the header-write-immediately + per-row-append durability discipline (WR-01) unchanged — this is D-06's explicit requirement.

**`emitSummary` pattern** (lines 635-674) — adapt for the D-05 advisory per-cell Elo estimate sibling TSV (`-summary.tsv`), same `fs.writeFileSync`-once-at-end shape (summary is small/derived, not per-row-durable like the main TSV).

**Main orchestration loop shape** (lines 712+, `main()`) — mirror the setup order: `parseArgs` → `validateRungs` → `createMaiaSession` (once) → `spawnStockfish` (once) → `openTsvWriter` → sweep loop → `emitSummary`. Replace the per-position `gradeSampledPosition` inner function (lines 682-710) with a per-game inner function that runs the bot-vs-anchor move loop.

---

### `scripts/lib/node-engine-providers.mjs` (service, refactored engine bring-up)

**Analog:** `scripts/gem-elo-calibration.mjs` lines 375-507 — extract these functions UNCHANGED into the new shared lib module, then re-import them back into `gem-elo-calibration.mjs` (mechanical, behavior-preserving refactor per RESEARCH.md's explicit recommendation):

**`resolveFrontendModule`** (lines 375-379):
```javascript
async function resolveFrontendModule(packageName) {
  const requireFromFrontend = createRequire(path.join(FRONTEND_DIR, 'package.json'));
  const resolved = requireFromFrontend.resolve(packageName);
  return import(pathToFileURL(resolved).href);
}
```

**`createMaiaSession`** (lines 383-390):
```javascript
async function createMaiaSession() {
  const ort = (await resolveFrontendModule('onnxruntime-web')).default;
  ort.env.wasm.numThreads = 1;
  const modelPath = path.resolve(FRONTEND_DIR, 'public/maia/maia3_simplified.onnx');
  const modelBytes = fs.readFileSync(modelPath);
  const session = await ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] });
  return { ort, session };
}
```

**`StockfishUciEngine` class** (lines 420-484) — `send`/`onLine`/`waitFor`/`init`/`stopAndSync`/`terminate`. `stopAndSync` (lines 467-478) is the WR-01 recovery pattern needed here too (a timed-out `go` must be stopped+synced before the next `position`/`go`, or Pitfall 2's option-state-leak risk compounds with a still-searching engine).

**`spawnStockfish`** (lines 486-507) — the `.cjs`/`.wasm` basename-copy trick (Pitfall 5 in RESEARCH.md: copy to `os.tmpdir()` as `.cjs`, rename `.wasm` to the SAME basename, `spawn('node', [cjsPath])`). Copy verbatim; re-verify with a `uci`/`isready` smoke round-trip immediately after the refactor.

**Import/export the same constants**: `STOCKFISH_INIT_TIMEOUT_MS = 30_000` (line 76) — reuse as-is.

---

### `scripts/lib/calibration-providers.mjs` (`nodePolicy`/`nodeGrade` — the `EngineProviders` adapter)

**`nodeGrade` analog — NOT gem-elo's `gradePosition`.** Use `frontend/src/lib/engine/workerPool.ts`'s `sendGo`/`handleLine`:

**`sendGo` pattern** (workerPool.ts lines 210-219):
```typescript
function sendGo(slot: PoolWorkerSlot, req: QueuedGradeRequest): void {
  slot.current = req;
  slot.accumulator = new Map();
  slot.worker.postMessage(`setoption name MultiPV value ${req.candidateUcis.length}`);
  slot.worker.postMessage(`position fen ${req.fen}`);
  slot.worker.postMessage(
    `go depth ${GRADING_TARGET_DEPTH} searchmoves ${req.candidateUcis.join(' ')} movetime ${GRADING_MOVETIME_SAFETY_CAP_MS}`,
  );
  slot.state = 'thinking';
}
```
Translate `worker.postMessage(cmd)` → `stockfish.send(cmd)` (the Node UCI wrapper's `send`).

**`handleLine` info-line parsing pattern** (workerPool.ts lines 249-267) — key by `parsed.pv[0]` (UCI), NEVER by the `multipv` rank field (SC5 landmine, confirmed twice in this codebase):
```typescript
if (line.startsWith('info ')) {
  if (slot.state !== 'thinking' || slot.stopPending || slot.current === null) return;
  const parsed = parseInfoLine(line);
  if (parsed === null || parsed.bound !== 'exact') return;
  const uci = parsed.pv[0];
  if (uci === undefined) return;
  const whitePovSign = sideToMove(slot.current.fen) === 'b' ? -1 : 1;
  const toWhitePov = (v) => (v === null ? null : v * whitePovSign);
  slot.accumulator.set(uci, {
    evalCp: toWhitePov(parsed.scoreCp),
    evalMate: toWhitePov(parsed.scoreMate),
    depth: parsed.depth,
  });
}
```
Constants to reuse verbatim from `workerPool.ts` (lines 36, 39): `GRADING_TARGET_DEPTH = 14`, `GRADING_MOVETIME_SAFETY_CAP_MS = 2500`.

**Pitfall 2 discipline (option-state reset)** — every `nodeGrade` call must reset Stockfish to full strength first (no analog needed, this is new per Pitfall 2):
```javascript
stockfish.send('setoption name Skill Level value 20');
stockfish.send('setoption name UCI_LimitStrength value false');
```

**`nodePolicy` analog** — adapt `maiaProbsForPosition` (gem-elo lines 393-415) from its multi-rung-batched SAN-keyed shape down to a single-rung, UCI-keyed shape (per `EngineProviders.policy(fen, elo, side)` in `frontend/src/lib/engine/types.ts`). The SAN→UCI conversion step is new (no analog): use `sanToUci` from wherever the frontend exposes it (check `@/lib/sanToSquares` or equivalent), converting each `maskAndSoftmax` key.

**`fallbackMove`** — import `frontend/src/lib/engine/botSampling.ts`'s exported `fallbackMove(fen, rng)` (line 145) rather than hand-rolling a "pick any legal move" fallback.

---

### `scripts/lib/calibration-anchors.mjs` (anchor move-choosers)

**No direct existing-file analog** (first anchor-mover code in the repo) — compose from `calibration-providers.mjs`'s `nodePolicy` (argmax instead of sample) and `node-engine-providers.mjs`'s `StockfishUciEngine` (skill-level `go`). Pattern from RESEARCH.md (already verified against real UCI option names in the vendored binary):
```javascript
async function stockfishSkillMove(fen, skillLevel) {
  stockfish.send(`setoption name Skill Level value ${skillLevel}`);
  stockfish.send('setoption name UCI_LimitStrength value false');
  stockfish.send(`position fen ${fen}`);
  stockfish.send(`go movetime ${ANCHOR_MOVETIME_MS}`);
  const line = await stockfish.waitFor((l) => l.startsWith('bestmove'), ANCHOR_MOVETIME_MS + SLACK_MS);
  return parseBestmove(line); // import from @/hooks/uciParser, do not reimplement
}
```

---

### `scripts/lib/calibration-openings.mjs` (opening book, static config)

**No analog** — `temp/brilliants_no_stalemates.csv` (used by `sampleStratified`, gem-elo lines 279-373) is the wrong semantic source (tactical brilliancy positions, not opening theory). Build a fresh hand-curated `~20-30`-entry array (name/ECO + FEN) per RESEARCH.md Open Question 1's recommendation. Follow the "confirmed facts, not copied source" documentation discipline used in `frontend/src/lib/maiaEncoding.ts`'s header comment (cite that this is standard public opening theory, not a licensed database).

---

### `scripts/lib/calibration-parity.check.mjs` (test, parity assertion)

**Analog:** `scripts/lib/gem-parity.check.mjs` (full file — mirror its exact structure)

**Doc-comment + import + assert pattern** (lines 1-32):
```javascript
#!/usr/bin/env node
/**
 * ... imports the REAL fn THROUGH the `@/` alias resolve hook — never
 * re-derived (D-03 zero-drift). Asserts the imported pipeline reproduces
 * hand-derived booleans for a fixed fixture ...
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/<name>.check.mjs
 */
import assert from 'node:assert/strict';
import { classifyGem, summarizeForGem, GEM_MAIA_MAX_PROB } from '@/lib/gemMove';
```
For the new check: import `selectBotMove`, `mctsSearch`, `maskAndSoftmax` (per CAL-02), assert against hand-derived fixtures exactly as `gem-parity.check.mjs` does with `classifyGem`/`summarizeForGem` (lines 53-125). Exit with `process.exit(0)` and a `console.log('PASS: ...')` line (line 127-128) on success.

Fold in (per RESEARCH.md Wave 0 Gaps): the pure-math `invertAnchorElo`/`combineAnchorEstimates` assertion (canned inputs, no engines) and the seeded-determinism assertion (same `--seed` → byte-identical `blend=1` game) — either as sections of this same file or sibling `.check.mjs` files following the identical pattern.

---

### `scripts/lib/calibration-elo.mjs` (pure math: Elo inversion)

**No existing-file analog for the math itself** — new pure functions. **Reuse `wilsonBounds` directly** (`frontend/src/lib/scoreConfidence.ts`, imported via `@/` per the Don't-Hand-Roll table — "Trust the established Wilson stat method" project memory applies here):
```javascript
import { wilsonBounds } from '@/lib/scoreConfidence';

function invertAnchorElo(observedScore, anchorRating, games) {
  const epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games);
  const clamped = Math.min(1 - epsilon, Math.max(epsilon, observedScore));
  return anchorRating - 400 * Math.log10(1 / clamped - 1);
}
```

---

## Shared Patterns

### `@/` alias resolution (module loading)
**Source:** `scripts/lib/frontend-alias-hook.mjs` (verbatim, unchanged — reuse as-is)
**Apply to:** the harness invocation itself: `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs [flags]`. No new hook needed.

### No-reimplementation / zero-drift discipline (CAL-02)
**Source:** `scripts/gem-elo-calibration.mjs` header comment (lines 12-16), enforced by `scripts/lib/gem-parity.check.mjs`
**Apply to:** every function touching `selectBotMove`/`mctsSearch`/`maskAndSoftmax`/`encodeBoard`/`eloToInput`/`MAIA_ELO_LADDER`/`wilsonBounds` — import via `@/`, never re-derive. `calibration-parity.check.mjs` is the tripwire.

### CLI flag validation (WR-02)
**Source:** `scripts/gem-elo-calibration.mjs` lines 93-110 (`requireFlagValue`, `parsePositiveIntFlag`)
**Apply to:** all new flags in `calibration-harness.mjs` (`--elo`, `--blends`, `--anchors`, `--games-per-cell`, `--seed`, `--out-dir`) — every value-consuming flag must throw on missing/malformed input, never silently coerce to `NaN`/`undefined`.

### Durable per-row TSV streaming (WR-01/D-06)
**Source:** `scripts/gem-elo-calibration.mjs` lines 606-627 (`openTsvWriter`)
**Apply to:** the main results-matrix TSV — write header immediately, `writeRow` after every completed game, never buffer-then-write-at-end.

### Shared-engine option-state discipline (Pitfall 2)
**Source:** new pattern (no prior-art analog — `gem-elo-calibration.mjs` never shared one Stockfish process across roles)
**Apply to:** every call site sending `go` to the single shared Stockfish process (`nodeGrade`, `stockfishSkillMove`, adjudication eval) — explicitly `setoption` every dependency immediately before that `go`, never assume prior state.

### UCI info-line parsing / multipv-is-a-rank landmine (SC5)
**Source:** `frontend/src/lib/engine/workerPool.ts` lines 249-267; also documented in `@/hooks/uciParser`
**Apply to:** `nodeGrade`'s line handler — key results by `parsed.pv[0]`, never by the `multipv` field.

### Terminal-state detection
**Source:** `chess.js`'s `isGameOver()`/`isCheckmate()`/`isStalemate()`/`isThreefoldRepetition()`/`isInsufficientMaterial()`, as called in `frontend/src/lib/engine/treeCommon.ts`'s `terminalValue`
**Apply to:** the game loop's per-move terminal check in `calibration-harness.mjs` — call these methods directly, do not build a custom rules engine.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/lib/calibration-openings.mjs` | config | — | No existing FEN corpus in the repo has opening-theory semantics; must be hand-built (Open Question 1). |
| `scripts/lib/calibration-anchors.mjs` | service | request-response | First anchor-move-chooser code in the repo; composed from other analogs' primitives, not copied from one file. |
| Game loop's grid-sweep + adjudication logic (`calibration-harness.mjs` inner loops) | controller | event-driven | First bot-vs-anchor self-play loop in the repo; gem-elo's loop grades single static positions, not live games — only the outer sweep/TSV shell transfers. |
| `scripts/lib/calibration-elo.mjs`'s inversion math | utility | transform | No existing Elo-inversion code in the repo; only the `wilsonBounds` combination-weighting sub-step reuses an existing utility. |

## Metadata

**Analog search scope:** `scripts/`, `scripts/lib/`, `frontend/src/lib/engine/`, `frontend/src/hooks/`, `frontend/src/lib/scoreConfidence.ts`
**Files scanned:** `scripts/gem-elo-calibration.mjs` (792 lines, full read), `scripts/lib/gem-parity.check.mjs` (128 lines, full read), `scripts/lib/frontend-alias-hook.mjs` (45 lines, full read), `frontend/src/lib/engine/workerPool.ts` (463 lines, targeted reads lines 1-60, 195-275), `frontend/src/lib/engine/selectBotMove.ts` (147 lines, full read), `frontend/src/lib/engine/maiaQueue.ts`/`mctsSearch.ts`/`botSampling.ts` (function-signature grep only — sufficient for classification)
**Pattern extraction date:** 2026-07-11
