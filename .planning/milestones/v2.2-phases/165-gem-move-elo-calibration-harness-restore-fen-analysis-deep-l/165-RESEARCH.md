# Phase 165: Gem-move ELO calibration harness + restore `?fen=` deep-link — Research

**Researched:** 2026-07-11
**Domain:** Headless Node engine harness (onnxruntime-web Maia + Stockfish WASM UCI) reusing frontend TS; React Router deep-link
**Confidence:** HIGH (all findings are from live codebase reads; no external-package guesswork)

## Summary

Every hard technical question in this phase is answerable from code already in the repo. The Maia-in-Node precedent (`scripts/inspect_maia_onnx.mjs`) already loads `maia3_simplified.onnx` under onnxruntime-web WASM and runs a real inference with the exact `{tokens, elo_self, elo_oppo}` feed the browser worker uses; the harness just needs to (a) feed the tensor from the *imported* `encodeBoard`, (b) batch the 6 rungs the same way `public/maia/maia-worker.js` does, and (c) `maskAndSoftmax` (imported) the sliced per-rung policy. The Stockfish grading contract is fully documented in `useStockfishGradingEngine.ts` (movetime-only, MultiPV, `searchmoves` MUST be the last go-clause, key by `pv[0]`); `parseInfoLine` in `uciParser.ts` is a pure, importable parser. The gem logic (`classifyGem`, `summarizeForGem`, `evalToExpectedScore`, `MISTAKE_DROP`) is pure and worker-free.

The single real risk is **consuming the frontend TS from a Node script with zero drift**. `tsx` and `esbuild` are NOT installed, and Vite 8 here is rolldown-based (no bundled esbuild). But Node is **v24.14.0**, where TypeScript type-stripping is on by default, and the four needed modules are fully type-erasable. So the recommended primary path is **native Node type-stripping + a ~25-line `@/`-alias resolve hook** (zero new deps, imports live source), with an **esbuild devDep bundle** as the robust fallback.

**Primary recommendation:** Build one committed `scripts/gem-elo-calibration.mjs` that (1) two-pass stream-samples the 2.2 GB CSV stratified by `score`, (2) imports the real `gemMove`/`liveFlaw`/`maiaEncoding`/`uciParser` modules via a Node alias resolve-hook, (3) runs Maia directly through an in-process onnxruntime-web session (batched 6 rungs) and Stockfish via a spawned `.cjs` UCI child process, and (4) emits a TSV + summary to `reports/data/`. Restore `?fen=` as an additive param whose only new *runtime* dependency is `loadMainLine([], fen)` — which already seeds a free-play root at an arbitrary FEN.

---

<user_constraints>
## User Constraints (from CONTEXT.md / SEED-094)

### Locked Decisions
- **D-01 Harness location & permanence:** committed reusable `scripts/*.mjs` alongside `inspect_maia_onnx.mjs`; parameterized `--n` (default 3000), configurable rungs/paths.
- **D-02 TSV output:** `reports/data/` (e.g. `reports/data/gem-elo-calibration-<timestamp>.tsv`), plus a sibling summary TSV.
- **D-03 Engine reuse — ZERO reimplementation drift:** Maia via onnxruntime-web WASM in Node; reuse `maiaEncoding.ts` encoding + `maskAndSoftmax`; Stockfish vendored WASM over UCI; import the **actual** `classifyGem`/`summarizeForGem`/`evalToExpectedScore`/`MISTAKE_DROP`.
- **C2 is ELO-independent** (Stockfish eval); only C1 (Maia prob) varies per rung → per position: 1 Stockfish grade + 6 Maia forward passes.
- **Record RAW probs**, not just the gem-at-0.1 boolean.
- **D-04 Sampling:** stratified across the `score` (brilliancy) range; source `temp/brilliants_no_stalemates.csv` (~22.4M rows, `fen,san,site,pieces,score`, full FENs).
- **D-05 TSV schema:** `fen, san, score, site, c2_pass, best_es, second_best_es, maia_p_600…maia_p_2600, gem_600…gem_2600, analysis_url` + summary block (drop-off curve + per-rung raw-prob percentiles).
- **D-06 `?fen=`:** **additive**, not a revert; `encodeURIComponent` the FEN; decode on load; seed board at FEN as free-play root; add build/parse unit tests mirroring `?line=`.
- **Rungs:** `{600, 1000, 1400, 1800, 2200, 2600}` (all valid on the 600–2600 step-100 Maia ladder).

### Claude's Discretion
- Stockfish grading depth/MultiPV budget (verify against the frontend's real grading config — done below, §3).

### Deferred Ideas (OUT OF SCOPE)
- The actual ELO-scaled iso-rarity ceiling in `gemMove.ts` (D-08 proper). **Do NOT modify `GEM_MAIA_MAX_PROB`.**
- Matched control set of ordinary best-moves.
</user_constraints>

---

## Q1 — onnxruntime-web in headless Node for Maia

**Evidence:** `scripts/inspect_maia_onnx.mjs` (read in full).

| Fact | Detail | Source |
|------|--------|--------|
| Model file | `frontend/public/maia/maia3_simplified.onnx` (45 MB, confirmed present) | `inspect_maia_onnx.mjs:29`; `ls public/maia/` |
| Runtime import | `onnxruntime-web` resolved from **`frontend/node_modules`** via `createRequire(path.join(FRONTEND_DIR,'package.json'))` then dynamic `import(pathToFileURL(...).href)` → `.default` | `inspect_maia_onnx.mjs:34-36` |
| Threading flag | `ort.env.wasm.numThreads = 1` (no COOP/COEP → no SharedArrayBuffer; matches worker) | `inspect_maia_onnx.mjs:40`; worker `initSession` |
| Session create | `ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] })` — takes **model bytes** (`fs.readFileSync`), not a path, in Node | `inspect_maia_onnx.mjs:86-89` |
| Input names | `tokens`, `elo_self`, `elo_oppo` | `inspect_maia_onnx.mjs:115-119` |
| Input tensors | `tokens: float32 [batch, 64, 12]`; `elo_self: float32 [batch]`; `elo_oppo: float32 [batch]` | `inspect_maia_onnx.mjs:116-118` |
| Output names | `logits_move` (policy, length 4352/item), `logits_value` (WDL logits, length 3/item, order **[Loss, Draw, Win]**) | `inspect_maia_onnx.mjs:129,142-146` |
| Native EP note | `onnxruntime-node` **SIGSEGVs** on session-create on this box → WASM is the sanctioned path | `inspect_maia_onnx.mjs:13-18` header |

**What the model expects (per forward pass):** a `[B,64,12]` one-hot piece-occupancy tensor (12 planes: white PNBRQK 0–5, black pnbrqk 6–11; square-major, board mirrored to mover-POV when Black is to move) plus two `[B]` raw-float ELO scalars.

**Recommendation:** the harness loads the session **once** (reuse across all 3000 positions), copying the `inspect_maia_onnx.mjs` resolve/create/`numThreads=1` recipe verbatim, but replaces the script's own local `boardToMaia3Tokens` with the **imported** `encodeBoard` from `maiaEncoding.ts` (see Q2) so the encoding is single-sourced.

---

## Q2 — Reuse the frontend Maia board→tensor encoding

**Evidence:** `frontend/src/lib/maiaEncoding.ts`, `frontend/public/maia/maia-worker.js`, `frontend/src/hooks/useMaiaEngine.ts`, `frontend/src/lib/engine/maiaQueue.ts`.

### The importable pure functions (all in `maiaEncoding.ts`, chess.js is the only runtime import)

| Export | Signature | Role | Line |
|--------|-----------|------|------|
| `encodeBoard(fen, historyFens?)` | `(string, string[]?) → Float32Array` (flat 64×12, **no batch dim**; mirrors on Black-to-move; `historyFens` ignored, n=0 contract) | board→tensor | `maiaEncoding.ts:177-188` |
| `eloToInput(elo)` | `(number) → number` (identity — raw float scalar fed directly) | ELO input | `maiaEncoding.ts:200-202` |
| `maskAndSoftmax(policy, fen)` | `(Float32Array, string) → Record<san, number>` — masks flat policy to chess.js legal moves, numerically-stable softmax, **SAN-keyed** | legal-move masking → per-move prob | `maiaEncoding.ts:234-255` |
| `MAIA_ELO_LADDER` | `readonly number[]` = **600..2600 step 100 (21 rungs)** — confirms the rung ladder | rung ladder | `maiaEncoding.ts:56-59` (MIN 600 `:40`, MAX 2600 `:46`, STEP 100 `:49`) |
| `softmaxWdl(logits)` | `(ArrayLike<number>) → {win,draw,loss}` | WDL (not needed for gem; available) | `maiaEncoding.ts:278-291` |
| `NUM_SQUARES` / `PLANES_PER_SQUARE` / `POLICY_VOCAB_SIZE` | `64` / `12` / `4352` consts | tensor shapes / slicing | `maiaEncoding.ts:20,23,64` |

### How the ELO rung is encoded (per-ELO conditioning) — the batching pattern to copy

`maia-worker.js` `analyze(fen, eloInputs)` (`public/maia/maia-worker.js:170-207`) is the exact template:
- Encode the board **once**; repeat the same `[64×12]` tokens `B` times into a `[B,64,12]` buffer (`tokens.set(boardTokens, b*768)`).
- `elo_self === elo_oppo === eloInputs[b]` per batch item — **symmetric strength** ("how would a player rated X play"), the config Plan 151-01 validated. (worker comment `:167-169`.)
- One `session.run` → `logits_move.data` (flat `[B*4352]`), `logits_value.data` (flat `[B*3]`).
- Slice per rung: `policy_i = policyFlat.slice(i*4352, (i+1)*4352)`; then `maskAndSoftmax(policy_i, fen)` (this is what `useMaiaEngine.ts:102-105` does per rung).

`useMaiaEngine.ts:191` calls analyze with `eloInputs: MAIA_ELO_LADDER` (all 21 rungs). **The harness passes only the 6 phase rungs** `[600,1000,1400,1800,2200,2600]` as the batch — a strict subset of the ladder, same code path, no new logic.

### Which functions the harness IMPORTS vs RE-INVOKES

- **Import (single-source):** `encodeBoard`, `maskAndSoftmax`, `eloToInput`, the shape consts, and (optionally) `MAIA_ELO_LADDER` for validating the 6 rungs are ladder members.
- **Re-invoke in the harness (Node-side glue, NOT reimplementing math):** the batch-stacking loop and `session.run` — this is I/O plumbing, identical to `analyze()` in the worker. The worker itself is a **classic Web Worker** (`importScripts`, `self.postMessage`) and **cannot be reused in Node**; the harness talks to onnxruntime-web directly (Q1). This is not drift — the only *math* (encoding, masking) is imported.

**Finding the played move's probability:** `maskAndSoftmax` returns a `Record` keyed by chess.js's own SAN. The CSV `san` (e.g. `Nf5`, `Qxc5`) must be **canonicalized through chess.js** before lookup — do `new Chess(fen).move(csvSan).san` and index the record by that, so `+`/`#`/`=Q` suffix differences between the CSV and chess.js can't cause a silent miss (see Landmines).

---

## Q3 — Headless Stockfish WASM over UCI in Node

**Evidence:** `frontend/src/hooks/useStockfishGradingEngine.ts`, `frontend/src/hooks/uciParser.ts`, memory `project_headless_stockfish_wasm_verification`, `ls frontend/public/engine/`.

### Vendored binary + driving pattern
- Files: `frontend/public/engine/stockfish-18-lite-single.{js,wasm}` (confirmed present; `.js` 21 KB Emscripten glue, `.wasm` 7.3 MB).
- Proven headless pattern (memory note): **copy the `.js` to a non-ESM `.cjs`** in a scratch dir; when run under Node it **auto-starts a UCI CLI reading stdin / writing stdout**. Drive it as a spawned child process (`child_process.spawn('node',[stockfishCjsPath])`), write UCI commands to `stdin`, read newline-delimited UCI from `stdout`.
- Load-bearing caveats (confirmed on the real binary, `useStockfishGradingEngine.ts:14-25`, `256-267`):
  1. **Key grades by `pv[0]` (the move), NEVER by the `multipv` index** — multipv is an eval rank that reorders as depth climbs.
  2. Illegal `searchmoves` entries are **silently dropped**.
  3. **`searchmoves` MUST be the LAST clause of the `go` command** on this WASM build — anything after it (e.g. `movetime`) is swallowed into the move list. (`useStockfishGradingEngine.ts:257-267`.)

### Frontend's real grading config (cross-check per D-03 discretion note)
`useStockfishGradingEngine.ts`:
- Termination: **`movetime` only, no depth cap** — `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` (`:52`), measured (Phase 158) to reach depth parity with the free run for a 6–8-move candidate union.
- `MultiPV` set **per search to the candidate count** (`setoption name MultiPV value ${candidateUcis.length}`, `:255`).
- Restricted with `searchmoves` to the **candidate union** (Maia mass set ∪ free-run best ∪ played), NOT all legal moves — because the UI only displays that union.
- Command order: `setoption MultiPV` → `position fen …` → `go movetime 4000 searchmoves <ucis>` (`:255-267`).

### Concrete UCI sequence to grade ONE position in the harness
```
uci
isready                     # gate on 'uciok' then 'readyok'
ucinewgame                  # (optional, clears hash between positions)
setoption name MultiPV value <K>
position fen <FULL_FEN>
go movetime <MS> searchmoves <uci1> <uci2> ...   # searchmoves LAST
# stream 'info ... multipv K ... score cp|mate ... pv <move> ...' → parseInfoLine
# terminate on 'bestmove <uci>'
```
Parse each `info` line with the **imported** `parseInfoLine` (`uciParser.ts:60-133`, pure, returns `{depth, multipv, scoreCp, scoreMate, bound, pv}`) and **ignore non-`exact` bounds** (`bound !== 'exact'` — jitter guard, `uciParser.ts:33`). Convert `pv[0]` UCI → SAN with chess.js (mirror `sanFromUci`, `useStockfishGradingEngine.ts:105-119`); normalize the mover-POV cp/mate to **white-POV** (`* (side==='b'?-1:1)`, `:357-359`) because `evalToExpectedScore` expects white-POV.

### Budget recommendation for C2 over 3000 positions (Claude's discretion)
The frontend grades a *display union*, but C2 for the harness needs the **true best vs runner-up over all legal moves** (a brilliant move's whole point is being uniquely best). So:
- **Grade all legal root moves:** `MultiPV = min(legalMoveCount, 32)`, `go movetime` with **no `searchmoves`** (rank every root move). This yields `best_es` (rank-1) and `second_best_es` (rank-2) directly, and lets `summarizeForGem` compute `playedIsBest` honestly.
- **Movetime:** recommend **2500–3000 ms** (below the frontend's 4000 ms, which was tuned for a *tiny* MultiPV; a full-legal MultiPV dilutes depth, but C2 is a coarse ≥`MISTAKE_DROP`=0.10-ES gap test, not a fine eval). At 3000 ms × 3000 positions ≈ **~2.5 h** wall clock (+ Maia, which is fast). Acceptable for a one-shot offline tool; `--n 5` validates first.
- **This diverges from the frontend's union-restricted C2** — flagged in Landmines. It is *more* correct for calibration and still imports `summarizeForGem`/`classifyGem` verbatim; only the candidate **set** differs (inherent to an offline harness with no Maia-union UI).
- Make `movetime` and the MultiPV cap `--`-overridable so the planner/user can trade fidelity for speed.

---

## Q4 — Gem logic single-source import

**Evidence:** `frontend/src/lib/gemMove.ts`, `frontend/src/lib/liveFlaw.ts`, `frontend/src/generated/flawThresholds.ts`.

| Function | Signature | Home | Line |
|----------|-----------|------|------|
| `classifyGem` | `({maiaProbability: number\|null, playedIsBest: boolean, bestEs: number\|null, secondBestEs: number\|null}) → boolean` | `gemMove.ts` | `:32-46` |
| `summarizeForGem` | `(Map<san,{evalCp,evalMate}>, mover: 'white'\|'black') → {bestSan, bestEs, secondBestEs}` (skips null/null entries; single graded → `secondBestEs:null`) | `gemMove.ts` | `:62-92` |
| `evalToExpectedScore` | `(evalCp: number\|null, evalMate: number\|null, mover) → number` in (0,1); mate→±1000cp then Lichess sigmoid; null→0.5 | **`liveFlaw.ts`** (NOT `moveQuality.ts`) | `liveFlaw.ts:88-103` |
| `GemGrade` | `{evalCp: number\|null; evalMate: number\|null}` | `gemMove.ts` | `:49-52` |
| `MISTAKE_DROP` | `0.1` (generated) | `flawThresholds.ts` | `:17` |
| `GEM_MAIA_MAX_PROB` | `0.1` — **DO NOT MODIFY** | `gemMove.ts` | `:25` |

> **Correction to the CONTEXT canonical-refs list:** `evalToExpectedScore` lives in `liveFlaw.ts`, not `moveQuality.ts`. `gemMove.ts:18` and `moveQuality.ts:25` both *import* it from `@/lib/liveFlaw`. The harness needs `gemMove.ts` + `liveFlaw.ts` + `flawThresholds.ts` — **`moveQuality.ts` is NOT required** (its `classifyMoveQuality`/bucket helpers are UI-only, and it type-imports `@/hooks/useMaiaEngine`).

### How they compose (the harness's per-position gem decision)
1. Build `Map<san, GemGrade>` from Stockfish grades (white-POV `evalCp`/`evalMate` per graded SAN).
2. `const {bestSan, bestEs, secondBestEs} = summarizeForGem(gradeMap, mover)` where `mover = sideToMoveFromFen(fen)` (`liveFlaw.ts:32-34`).
3. `c2_pass = playedIsBest && bestEs!==null && secondBestEs!==null && (bestEs - secondBestEs >= MISTAKE_DROP)` — this is exactly the C2 tail of `classifyGem`.
4. `playedIsBest = (bestSan === playedCanonicalSan)`.
5. For each rung: `gem_<rung> = classifyGem({maiaProbability: probAtRung, playedIsBest, bestEs, secondBestEs})`.

**C2 is ELO-independent — confirmed:** `classifyGem` (`:43-45`) only uses `maiaProbability` for the C1 gate (`maiaProbability > GEM_MAIA_MAX_PROB`); `playedIsBest`/`bestEs`/`secondBestEs` carry no ELO. So `c2_pass`, `best_es`, `second_best_es` are computed **once** per position; only `maiaProbability` varies per rung. This matches SEED-094's "1 Stockfish grade + 6 Maia forward passes".

**Store RAW probs (D-05):** the TSV's `maia_p_<rung>` columns are the raw `probAtRung` (the played move's masked-softmax prob); `gem_<rung>` is the derived `classifyGem(...)` boolean at the flat 0.1 ceiling.

---

## Q5 — Consuming frontend TypeScript from a Node `.mjs` (KEY RISK)

**Environment facts (verified):**
- Node **v24.14.0** (`node --version`) → TypeScript **type-stripping is unflagged/default-on** for `.ts` imports.
- **No `tsx`, no `esbuild`** resolvable from `frontend/` (`createRequire` probe: both "no"); **`chess.js` IS** ("yes").
- **Vite 8.0.16 is rolldown-based** (`vite` deps: `rolldown 1.0.3`, no esbuild) → cannot piggyback esbuild off vite.
- No root `package.json`; empty root `node_modules`. `frontend/knip.json` scans only `src/**` and already uses `ignoreDependencies` (e.g. `onnxruntime-web`, used by the un-scanned public/ worker).
- The `@/` alias = `frontend/src/*` (`frontend/vite.config.ts:134-137`, `tsconfig.json:13-14`). Node does **not** read tsconfig paths.

### Purity trace of the modules the harness imports
| Module | Runtime imports | DOM/Worker/`import.meta`? | Erasable TS only? |
|--------|-----------------|---------------------------|-------------------|
| `maiaEncoding.ts` | `chess.js` (bare) | none | yes (consts, `as const`, fns, interfaces) |
| `gemMove.ts` | `@/lib/liveFlaw`, `@/generated/flawThresholds` | none | yes |
| `liveFlaw.ts` | `chess.js`, `@/generated/flawThresholds`, `@/types/library` (**`import type`**, erased) | none | yes |
| `flawThresholds.ts` | none | none | yes (plain consts) |
| `uciParser.ts` | none | none | yes |

**All five are pure and fully type-erasable** (no enums, no `namespace`, no parameter properties, no `import =`). The only non-native need is `@/` alias resolution; `chess.js` resolves natively from `frontend/node_modules` because the `.ts` files physically live in `frontend/src`.

### Recommended: **Option D — native type-stripping + a tiny `@/` resolve hook** (primary)
- Add `scripts/lib/frontend-alias-hook.mjs` (~25 lines) registering a `resolve` hook that rewrites specifiers starting with `@/` → `pathToFileURL(frontendSrc + rest + '.ts')`, delegating everything else to `nextResolve`.
- Run: `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/gem-elo-calibration.mjs`; inside, `await import(<abs>/frontend/src/lib/gemMove.ts)` etc.
- **Pros:** zero new deps, zero `package.json`/knip changes, imports the **live source** (true zero-drift — a later edit to `gemMove.ts` is picked up next run). **Cons:** relies on Node's (stable-in-24) type-stripping; emits a cosmetic `ExperimentalWarning` (suppress with `--disable-warning=ExperimentalWarning` if desired).

### Fallback: **Option B — esbuild one-shot bundle**
- Add `esbuild` to `frontend/package.json` devDeps + one line in `frontend/knip.json` `ignoreDependencies` (exact precedent: `onnxruntime-web` is ignored there for the same "used outside src/" reason). Resolve it from `frontend/node_modules` via `createRequire` (same trick as `inspect_maia_onnx.mjs:34`).
- `esbuild.build({ stdin:{contents:"export * from '@/lib/gemMove'; export * from '@/lib/liveFlaw'; export * from '@/lib/maiaEncoding'; export * from '@/hooks/uciParser'", resolveDir:frontendSrc, loader:'ts'}, bundle:true, format:'esm', platform:'node', alias:{'@':frontendSrc}, write:false })` → write to a temp `.mjs` → dynamic `import()`.
- **Pros:** battle-tested, no experimental reliance, single output. **Cons:** one devDep + one knip-ignore line; bundles a snapshot (re-run each harness invocation to stay zero-drift).

Options (c) "compiled output" and Node's own without-hook are non-viable: Vite emits hashed bundles (no stable per-module path), and bare Node can't resolve `@/`.

> **`uciParser.ts` is at `frontend/src/hooks/uciParser.ts`** (not `lib/`) — import path `@/hooks/uciParser`.

---

## Q6 — `?fen=` deep-link restoration (additive)

**Evidence:** `frontend/src/lib/analysisUrl.ts`, `frontend/src/lib/analysisUrl.test.ts`, `frontend/src/pages/Analysis.tsx`, `frontend/src/hooks/useAnalysisBoard.ts`.

### Current state
- `analysisUrl.ts` header (`:8-14`) documents that `?fen=` was **replaced** by `?line=` (comma-separated UCI, URL-safe, replayable to move 1). Existing exports: `buildAnalysisLineUrl`, `parseAnalysisLineParam`, `buildGameAnalysisUrl`.
- `Analysis.tsx` reads `line` (`:430-431`), `game_id`/`ply` (`:435-444`); precedence today: **game mode (`game_id`) vs free-play (`line`)**, mutually exclusive via `isGameMode` (`:448`) and the shared `hasLoadedMainLine` guard.
- Seeding is via **effects calling `loadMainLine`**: game mode `loadMainLine(gameData.moves, STARTING_FEN)` (`:660`); free play `loadMainLine(lineSans, STARTING_FEN)` (`:671`).

### The load path for an arbitrary FEN already exists — no new hook method needed
`useAnalysisBoard.loadMainLine(sans, newRootFen)` (`useAnalysisBoard.ts:297-324`): with **empty `sans`**, `newMainLine=[]`, `currentNodeId=null`, `rootFen=newRootFen`. `getPosition` returns `rootFen` when `currentNodeId===null` (`:126-130`). So **`loadMainLine([], fen)` seeds the board at `fen` as a free-play root** — the user can make moves from it (they fork children off the root). No `loadPositionFromFen`-style method needs adding.

### Recommended implementation
**`analysisUrl.ts` — add two exports (mirror the line helpers):**
```ts
const FEN_PARAM = 'fen';
// build: encodeURIComponent handles the FEN's spaces and '/'
export function buildAnalysisFenUrl(fen: string): string {
  return `${ANALYSIS_PATH}?${FEN_PARAM}=${encodeURIComponent(fen)}`;
}
// parse: decode + validate via chess.js; invalid → null (defensive, like parseAnalysisLineParam)
export function parseAnalysisFenParam(fenParam: string | null): string | null {
  if (!fenParam) return null;
  const fen = decodeURIComponent(fenParam);
  try { new Chess(fen); return fen; } catch { return null; }
}
```
(`Chess` is already imported in `analysisUrl.ts:16`.)

**`Analysis.tsx`:**
- `const fenParam = searchParams.get('fen');`
- `const rootFenSeed = useMemo(() => parseAnalysisFenParam(fenParam), [fenParam]);`
- New effect mirroring the line effect (`:668-673`):
  ```ts
  useEffect(() => {
    if (isGameMode || rootFenSeed === null || hasLoadedMainLine.current) return;
    hasLoadedMainLine.current = true;
    loadMainLine([], rootFenSeed);
  }, [rootFenSeed, isGameMode]);
  ```
- **Precedence:** `game_id` > `fen` > `line`. Enforce by adding `&& rootFenSeed === null` to the existing line-effect guard (`:669`) so `?fen=` wins when both are present (they address different use cases; the harness only ever emits `?fen=`). `fenToRootPly` (`Analysis.tsx:283-291`) already derives correct move numbering from an arbitrary FEN's `fullmove`/side fields, so the variation tree / engine labels are correct at a mid-game root.

**Tests (`analysisUrl.test.ts`, mirror existing structure):**
- `buildAnalysisFenUrl` encodes spaces (`%20`) and `/` (`%2F`); `parseAnalysisFenParam` round-trips `build→parse`; returns `null` for `null`/empty/garbage; a mid-game full FEN with counters round-trips.

**knip:** the test file importing both new exports + `Analysis.tsx` importing `parseAnalysisFenParam` satisfies knip (test imports count as usage — the existing `buildAnalysisLineUrl` etc. are only "used" the same way and aren't flagged). The harness may import `buildAnalysisFenUrl` (via Q5) for single-source URL format, or inline the trivial `https://flawchess.com/analysis?fen=${encodeURIComponent(fen)}` for the absolute `analysis_url` column.

---

## Q7 — CSV sampling (2.2 GB / 22.4M rows, stratified by `score`)

**Evidence:** `ls -la temp/brilliants_no_stalemates.csv` → 2,209,595,857 bytes; `wc -l` → 22,418,058 rows; `head -3`:
```
fen,san,site,pieces,score
3r2k1/p5pp/1p1Np1q1/2pRP3/5P2/P3n1PP/1PP3Q1/3R3K w - - 1 28,Nf5,https://lichess.org/fdqudly3,d1 g2 d5 f5,46.47
```
- **FENs are full FENs** (piece-placement + `w`/`b` + castling + ep + halfmove + **fullmove**, e.g. `… w - - 1 28`) → correct side-to-move for both engines. ✓ (confirms SEED-094 open question).
- **No field contains a comma:** FEN/SAN/site have none; `pieces` is **space-separated** (`d1 g2 d5 f5`); `score` is a decimal. So `line.split(',')` yields **exactly 5 fields** — a naive split is safe (assert `length===5`, skip the header row).

### Recommended: two-pass streaming (memory O(sample), never loads the file)
Use `fs.createReadStream` + `readline` (line-by-line; never `readFileSync`).
- **Pass 1** — stream once, track `score` **min/max** and a coarse histogram (e.g. 100 fixed bins once min/max stabilize, or a running list of counts by rounded score) to derive **equal-count strata edges** (score is unknown-range/skewed; the head shows ~46, but don't assume).
- **Pass 2** — stream again; assign each row to one of **S strata** (recommend S = 10–20 by quantile edges from pass 1); **reservoir-sample `ceil(n/S)` rows per stratum** via Algorithm R. Total held rows ≈ `n` (3000 → trivial memory).
- Seed a deterministic PRNG (e.g. mulberry32) via `--seed` so a given `(--n, --seed)` reproduces the same sample (valuable for `--n 5` smoke runs and re-runs).

**Why two-pass, not one-pass:** the score range/skew is unknown a priori, so fixed one-pass bucket edges would mis-stratify. Two sequential streams over 2.2 GB are cheap (a few minutes each, I/O-bound) and guarantee coverage across the brilliancy range per D-04.

**Robustness:** wrap per-row FEN parse in try/catch (skip malformed rows), and skip rows whose CSV `san` fails to canonicalize via `new Chess(fen).move(san)` (defensive; counts logged in the summary).

---

## Recommended Harness Architecture

```
CSV (2.2GB, gitignored)
   │  two-pass stream, stratified reservoir by `score` (--n, --seed)
   ▼
~3000 sampled rows {fen, san, site, score}
   │
   ├──► Stockfish child process (.cjs, UCI over stdin/stdout)      [once/position]
   │        setoption MultiPV=min(legal,32); position fen; go movetime ~3000
   │        parseInfoLine (imported) → white-POV gradeMap<san,GemGrade>
   │        summarizeForGem (imported) → {bestSan,bestEs,secondBestEs}
   │        playedIsBest = bestSan===canonSan ; c2_pass = C2 tail of classifyGem
   │
   ├──► onnxruntime-web session (in-process, loaded once)          [6 rungs/position]
   │        encodeBoard (imported) → tokens; batch×6 {elo_self=elo_oppo=rung}
   │        session.run → slice logits_move per rung
   │        maskAndSoftmax (imported) → probs[canonSan] = maia_p_<rung>
   │
   ▼
   classifyGem (imported) per rung → gem_<rung>
   ▼
reports/data/gem-elo-calibration-<ts>.tsv   (+  …-summary.tsv)
   analysis_url = https://flawchess.com/analysis?fen=<encodeURIComponent(fen)>
```
Engines are initialized **once** and reused across all positions (session create + Stockfish spawn are the expensive steps). Frontend TS imported via the Q5 alias hook.

## Standard Stack (all already vendored / installed in `frontend/`)

| Dependency | Version | Purpose | Source of truth |
|------------|---------|---------|-----------------|
| `onnxruntime-web` | (frontend dep) | Maia WASM inference in Node | `frontend/package.json`; resolve via `createRequire` |
| `chess.js` | 5.x (frontend dep) | legal moves / SAN↔UCI / FEN validation | imported transitively + directly |
| vendored Stockfish 18 lite | `public/engine/stockfish-18-lite-single.{js,wasm}` | C2 grading | copy `.js`→`.cjs`, spawn |
| `maia3_simplified.onnx` | `public/maia/` (45 MB) | Maia-3 model | `inspect_maia_onnx.mjs:29` |
| Node | **v24.14.0** | type-stripping runtime | `node --version` |
| `esbuild` | (only if Option B) | TS bundle fallback | add to frontend devDeps + knip ignore |

## Package Legitimacy Audit

No new **runtime/external** package is required for the primary path (Option D). The only *potential* new dep is the Option-B fallback:

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| `esbuild` | npm | OK (ubiquitous, MIT, ~40M/wk) | **Only if Option B is chosen**; add to `frontend` devDeps + `knip.json` `ignoreDependencies`. `[ASSUMED]` — not verified against registry this session; planner should `npm view esbuild version` before adding. |

Primary recommendation (Option D) adds **zero** packages.

## Validation Architecture

**Test framework:** Vitest (`frontend/package.json` `"test": "vitest run"`; jsdom devDep; `@/` alias inherited from `vite.config.ts`). No backend/pytest involvement — this phase is Node + frontend TS only.

| Req | Behavior | Test type | Command | Exists? |
|-----|----------|-----------|---------|---------|
| `?fen=` build | `buildAnalysisFenUrl` encodes spaces/`/` | unit (vitest) | `cd frontend && npx vitest run src/lib/analysisUrl.test.ts` | ❌ Wave 0 (extend existing file) |
| `?fen=` parse | `parseAnalysisFenParam` decodes, validates, `null` on garbage, round-trips build→parse | unit | same | ❌ Wave 0 |
| `?fen=` precedence | game_id > fen > line seeding | (optional) component/manual | — | manual UAT |
| Gem-logic import parity | imported `classifyGem`/`summarizeForGem` produce the expected C2/gem booleans for a hand-computed fixture position | unit (Node/vitest) | small fixture test | ❌ Wave 0 |
| Harness smoke | `--n 5` runs end-to-end, emits a well-formed TSV + summary, no crash | integration (manual) | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/gem-elo-calibration.mjs --n 5` | ❌ Wave 0 |

- **Sampling rate:** unit tests are sub-second; the harness itself is an offline one-shot — validate correctness at `--n 5` before any full `--n 3000` (~2.5 h) soak.
- **Round-trip is the cheap high-value test:** `parseAnalysisFenParam(new URLSearchParams(buildAnalysisFenUrl(fen).split('?')[1]).get('fen'))` === `fen` for a mid-game full FEN.
- **Gem parity is definitional** (same imported module the app uses) — the meaningful assertion is a fixture where you hand-derive `best_es`/`second_best_es`/`c2_pass` from known evals and confirm the harness pipeline agrees, catching wiring bugs (white-POV sign, SAN canonicalization).
- **Zero-drift guard (nice-to-have):** a test asserting the harness's imported `MISTAKE_DROP`/`GEM_MAIA_MAX_PROB` equal the frontend constants (they must, since it's the same module) — cheap tripwire if someone later swaps to a copied constant.

## Landmines / Open Risks

1. **SAN canonicalization mismatch (HIGH impact, easy fix).** `maskAndSoftmax` and the Stockfish `gradeMap` are keyed by **chess.js SAN**; the CSV `san` may differ in `+`/`#`/`=Q` decoration. Always canonicalize the CSV move via `new Chess(fen).move(csvSan).san` and index everything by that. Skip (and count) rows where the CSV move is illegal for the FEN.
2. **`searchmoves` must be the LAST go-clause** (`useStockfishGradingEngine.ts:257-267`) — if the harness appends `movetime` after `searchmoves`, the movetime is silently swallowed and the search only ends on depth/`bestmove`. For the recommended full-legal grading we use **no `searchmoves`**, sidestepping this — but if the planner opts for a candidate-restricted C2, honor the ordering.
3. **C2 candidate-set divergence from the frontend (MEDIUM, by design).** The frontend computes best/2nd-best over its *display union*; the harness grades **all legal moves**. This is intentional and more correct for calibration, but it means the harness's `c2_pass` can differ from what the live gem overlay would show for the same position. Document this in the harness header. The *logic* (`summarizeForGem`/`classifyGem`) is still imported verbatim — only the candidate set differs.
4. **Maia policy vocab index is UNVERIFIED against the real model's order** (`maiaEncoding.ts:78-87`, VALID-01 open risk). Because the harness reuses the **same `maskAndSoftmax`**, any bias is identical to what production's gem detector sees — so for calibrating *this* detector it is self-consistent. Do NOT treat the raw probs as ground-truth Maia probabilities in an absolute sense; treat them as "what FlawChess's Maia path reports," which is exactly what D-08 will recalibrate against.
5. **Node type-stripping is experimental-flagged** (cosmetic warning) and requires all imported TS to be erasable — verified true for the five modules today, but a future edit adding an `enum`/`namespace` to `liveFlaw.ts`/`gemMove.ts` would break Option D. The gem-parity test is the tripwire; Option B (esbuild) is immune.
6. **`moveQuality.ts` is a red herring** in the CONTEXT refs — importing it drags a `type` import of `@/hooks/useMaiaEngine` (harmless, erased) but it is not needed. Import from `liveFlaw.ts` for `evalToExpectedScore`.
7. **WebGPU path is browser-only.** In Node there is no `navigator.gpu`; the harness must force the **`wasm`** EP directly (as `inspect_maia_onnx.mjs` does) — do not copy the worker's WebGPU-probe branch.
8. **`?fen=`/`?line=` double-seed race.** Both seeding effects share `hasLoadedMainLine`; without an explicit `rootFenSeed === null` guard on the line effect, effect ordering decides the winner. Add the guard (§Q6) to make precedence deterministic.
9. **CSV field-count assumption.** Verified no field carries a comma today; still assert `split(',').length === 5` per row and skip/count violations, in case a future dump changes the `pieces` delimiter.

## Sources

### Primary (HIGH confidence — live codebase reads)
- `scripts/inspect_maia_onnx.mjs` — onnxruntime-web-in-Node contract (Q1)
- `frontend/src/lib/maiaEncoding.ts` — encoding, `maskAndSoftmax`, ladder (Q2)
- `frontend/public/maia/maia-worker.js` — batched multi-ELO `analyze` (Q2)
- `frontend/src/hooks/useMaiaEngine.ts`, `frontend/src/lib/engine/maiaQueue.ts` — per-rung usage (Q2)
- `frontend/src/hooks/useStockfishGradingEngine.ts` + `uciParser.ts` — Stockfish grading contract (Q3)
- `frontend/src/lib/gemMove.ts`, `liveFlaw.ts`, `generated/flawThresholds.ts` — gem logic (Q4)
- `frontend/src/lib/analysisUrl.ts` + `.test.ts`, `pages/Analysis.tsx`, `hooks/useAnalysisBoard.ts` — deep-link (Q6)
- `frontend/vite.config.ts`, `tsconfig.json`, `frontend/knip.json`, `frontend/package.json` — build/import config (Q5)
- `temp/brilliants_no_stalemates.csv` head/`wc`/size — sampling (Q7)
- memory `project_headless_stockfish_wasm_verification` — `.cjs` UCI driving (Q3)

### Environment probes (HIGH)
- `node --version` → v24.14.0; `createRequire` resolvability of `tsx`/`esbuild`/`chess.js`; `vite` deps (rolldown).

## Metadata

**Confidence breakdown:**
- Engine reuse (Maia + Stockfish): HIGH — exact code paths and a working Node precedent exist.
- Gem-logic import: HIGH — pure modules, signatures read directly.
- TS-consumption strategy: HIGH on the *mechanism*, MEDIUM on Option D vs B choice (both work; Option D leans on experimental type-stripping — flagged).
- `?fen=` restore: HIGH — load path (`loadMainLine([], fen)`) already exists.
- CSV sampling: HIGH — format and size verified.

**Research date:** 2026-07-11
**Valid until:** ~30 days (stable internal code; re-verify if `gemMove.ts`/`useStockfishGradingEngine.ts`/`maiaEncoding.ts` change).

## RESEARCH COMPLETE
