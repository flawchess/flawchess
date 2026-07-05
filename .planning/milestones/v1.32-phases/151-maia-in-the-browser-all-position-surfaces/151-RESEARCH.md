# Phase 151: Maia in the Browser + All-Position Surfaces - Research

**Researched:** 2026-07-05
**Domain:** Client-side ML inference (onnxruntime-web + Web Worker) integrated into an existing React/Vite analysis board; AGPL relicensing mechanics; Recharts multi-line chart
**Confidence:** MEDIUM (architecture/patterns HIGH — extends proven Phase 136–140 precedent; exact `maia3_simplified.onnx` tensor I/O contract MEDIUM/LOW — genuinely requires the phase's own hands-on pass, per D-08/MAIA-01/MAIA-06)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Layout & placement (Area 1)**
- **D-01:** Desktop is a **3-column layout**: **left column = "Moves by Rating" chart** (~340–380px) | **center = Maia eval bar + board + Stockfish eval bar** | **right column = engine card + variation tree + board controls** (current right panel). Maia bar hugs the board's LEFT edge (SURF-04); Stockfish bar stays RIGHT.
- **D-02:** Left-column chart is narrower than a below-board one — fewer ELO x-axis ticks accepted. Keep legible at ~360px (compact axis; top-N cap already limits line count).
- **D-03:** Mobile adds a **4th tab**; order **Moves | Eval | Human | Tags**. "Human" tab holds the Moves-by-Rating chart (full width when selected). Board + both eval bars stay always-visible above the tab strip.
  - **Open detail for planning:** free play currently has **no** mobile tab strip (only the move list — confirmed by direct code read of `Analysis.tsx`, the `isGameMode && evalChartReady` gate). The Human chart must still appear in free play — planner decides: below the board, or a minimal Moves | Human tab pair in free play. Keep consistent with the tabbed game-mode surface.

**Maia eval bar rendering (Area 2)**
- **D-04:** LEFT Maia bar renders a **single expected-score fill** — collapse WDL to `E = W + 0.5·D` (0..1), one vertical fill, a clean mirror of the Stockfish cp bar. Not a 3-segment W/D/L stack.
- **D-05:** White-POV, flips with board orientation exactly like `EvalBar`'s `flipped` prop. Full WDL vector still computed (feeds the chart / Phase 152) but the *bar* shows only expected score.

**ELO conditioning + "you are here" (Area 3)**
- **D-06:** Interactive **ELO selector** drives the "you are here" reference line, available across modes.
- **D-07:** Selector defaults: game mode → user's color **rating-at-game-time** (`games.white_rating`/`games.black_rating`, never frozen snapshot); free play → user's **current platform rating** (from `useUserProfile()`), else **1500** midpoint fallback. Selector lets the user move off default.
- **D-08 (Claude's discretion / research):** ELO ladder range + granularity provisional **~1100–2000, ~100-ELO steps** (matching maiachess.com) — **confirm against the actual `maia3_simplified.onnx` ELO input contract during the hands-on pass**; do not hard-code a range the model wasn't trained on.

**Model size + execution backend (Area 4)**
- **D-09:** Start with **`maia3_simplified.onnx`** / smallest Maia-3; **WASM baseline** (mobile Safari), feature-detect + prefer **WebGPU** when available.
- **D-10:** Upgrade to a larger model (23M/79M) **ONLY if** the VALID-01 live-eyeball gate shows poor calibration. VALID-01 is measure-and-judge, **not** a hard ship-block for the chart/bar. Download-size + per-position latency (desktop + phone; single call vs ELO sweep; WASM vs WebGPU) measured **during the phase** (MAIA-06), not guessed here.

### Claude's Discretion

- Chart color mapping for candidate-move lines (reuse `theme.ts`; played + best emphasized) — spike 006 already prototyped the shape; production port to Recharts is mechanical.
- Worker hook shape (mirror `useStockfishEngine` — lifecycle, tab-hide pause, adaptive debounce, stale-guard), ephemeral session cache scope/size (board-session only, no persistence — MAIA-05).
- Attribution notice placement (visible surface citing CSSLab repo + AGPL text + model artifact + Chessformer paper — LIC-02); planner picks the surface (analysis-page info, footer, or About).

### Deferred Ideas (OUT OF SCOPE)

- **Phase 152 (next):** salience×trainability verdict banner (FLAW-01/02), Maia-WDL practical-severity reframe (FLAW-03), precision-first withhold on low-confidence buckets (FLAW-04). This phase ships chart+bar for ALL positions; flaw *interpretation* is Phase 152.
- **v2 / future persistence-gated milestone:** Pillar C aggregate weakness rollup (AGG-01/02), `game_flaws` schema + flaw-node backfill, SEED-082 human-playable-line engine. Revisit only after this phase proves Maia calibration is trustworthy.
- **3-segment W/D/L bar rendering** — offered, not chosen (D-04 picked single expected-score fill).
- Pillar C aggregate rollup, any DB write/persistence of Maia signals, `game_flaws` schema change, server-side/remote-worker Maia inference, SEED-082, Maia model fine-tuning/modification (unmodified model only — AGPL §13).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIC-01 | Relicense MIT → AGPL-3.0 | See "AGPL Relicensing Mechanics" — concrete file list identified (LICENSE, README badge/text) |
| LIC-02 | Visible Maia attribution + offer-source notice citing Chessformer paper | README already has a precedent section for the Stockfish GPL vendoring — mirror it; frontend "About"/footer notice pattern documented |
| MAIA-01 | Unmodified `maia3_simplified.onnx` obtained, version-pinned, loaded as runtime data asset; input encoding + output layout confirmed against reference client | Chessformer paper's board/ELO/policy/WDL architecture documented below; exact ONNX I/O names/shapes flagged as the phase's mandatory hands-on item (LOW confidence without inspection) |
| MAIA-02 | onnxruntime-web in a Web Worker, lazy-loaded only when analysis board opens | Worker pattern mirrors `useStockfishEngine.ts`; `React.lazy` + dynamic `import()` pattern documented |
| MAIA-03 | Own MIT glue (board→tensor, ELO input, legal-move masking, softmax) — deterministic per-legal-move distribution; no AGPL JS copied/bundled | Encoding math from the paper documented in Code Examples; masking/softmax pattern documented |
| MAIA-04 | Single forward pass or efficient ELO sweep → full per-ELO curve + WDL; ELO from rating-at-game-time | Batched-inference-across-ELO pattern documented; `games.white_rating`/`black_rating` already read in `Analysis.tsx` via `useLibraryGame` |
| MAIA-05 | Ephemeral, board-session-scoped cache only | `LIVE_EVAL_CACHE_MAX` FIFO Map pattern already in `Analysis.tsx` — reuse directly |
| MAIA-06 | Download size + per-position latency measured (desktop/mobile, WASM/WebGPU, single/sweep); no unsupported-op errors | Spike 004 size table (5M≈20MB/23M≈90MB/79M≈320MB fp32); WASM supports all ops, WebGPU a subset — op-support check is a hands-on gate |
| SURF-01 | "Moves by Rating" chart, one line per candidate move over ELO ladder | Spike 006 prototype + Recharts `EvalChart.tsx` precedent documented |
| SURF-02 | "You are here" reference line + played/best emphasis | `<ReferenceLine>` pattern from existing `EvalChart.tsx` |
| SURF-03 | Line cap: top-N-by-peak ∪ {played, best} | Cap algorithm from spike 006 (`Array.sort` by peak, `Set` union) documented verbatim |
| SURF-04 | Maia WDL bar LEFT, Stockfish bar RIGHT | `EvalBar.tsx` generalization pattern documented (add `whiteFraction` override prop) |
| SURF-05 | Live recompute on every navigation, no server round-trip | Worker message-per-FEN pattern mirrors `useStockfishEngine`'s debounced `analyze()` |
| VALID-01 | Calibration eyeballed live; size/latency measured before shippable | Validation Architecture section below; lightweight measure-and-judge (D-10), not a formal rubric |
</phase_requirements>

---

## Summary

This phase extends a proven pattern (Phase 136's `useStockfishEngine` Web Worker + WASM hook, wired into `Analysis.tsx` in Phases 137–140) to a second, structurally different engine: an ONNX transformer run via `onnxruntime-web` instead of a UCI WASM binary. The Worker lifecycle, tab-hide pause, debounce, and stale-result-guard patterns transfer almost directly. What's new is the **inference contract** (tensor in, tensor out, not UCI text) and a **hard constraint carried over from Phase 136**: FlawChess runs **no COOP/COEP headers site-wide** (CI-guarded, breaks Google OAuth + iOS Safari) — so onnxruntime-web's WASM execution provider must run with `ort.env.wasm.numThreads = 1` explicitly forced, never relying on the multi-threaded default. WebGPU is a separate, no-COOP/COEP-required execution provider and is the "prefer when available" path per D-09.

The `Chessformer` (Maia-3) architecture is now well understood from the arXiv paper (2605.19091), which this session fetched directly: **input** is 64 square-tokens, each concatenating a 12-dim one-hot piece-plane (repeated over 1+n history positions, board flipped to side-to-move POV) with two 128-dim "soft" rating embeddings (a learned weak/strong interpolation) appended to every token. **Output** is a 64×64 from→to attention matrix for the policy (promotions via an additive bias on last-rank key vectors; castling/en passant map onto normal king/pawn moves) and a WDL 3-logit value head (mean-pool → LayerNorm → Linear(128) → ReLU → Linear(3)). This is enough to write the *glue math* (masking, softmax, expected-score) with confidence, but the **exact named ONNX inputs/outputs of `maia3_simplified.onnx`** — whether ELO is fed as a raw scalar (embedding computed inside the graph, the far more likely ONNX-export convention) or as a precomputed 352-dim vector, and whether "simplified" means history is dropped (n=0) for the live-navigation use case — is unconfirmed and is precisely the phase's mandated hands-on item (MAIA-01/success-criterion-1). Do not let the planner treat the paper's architecture as license to skip that inspection step.

For the frontend surfaces: the "Moves by Rating" chart is a straightforward Recharts port of the already-prototyped spike 006 (top-N∪{played,best} cap, "you are here" `ReferenceLine`) using the exact `<LineChart>`/`<ReferenceLine>` APIs already in production in `EvalChart.tsx`. The Maia eval bar should **not** duplicate `EvalBar.tsx` — extend it with an optional `whiteFraction` override prop so both bars share one component and one flip/testid contract (D-04/D-05 explicitly call for "a clean mirror"). One real gap surfaced during this research: **`useUserProfile()`'s `UserProfile` type has no rating field at all** — D-07's free-play default ("user's current platform rating") cannot be read today; the minimal-diff fix is a read-only addition to the existing `/users/me/profile` endpoint (most-recent-game rating per platform, backed by the existing `ix_games_user_played_at` index — no migration, no new endpoint, no write).

**Primary recommendation:** Treat MAIA-01 (ONNX tensor I/O + ELO-range confirmation) as the literal first task of the first plan — everything else (worker hook, chart, bar, ELO selector) is data-shape-dependent on its answer. Build the Worker hook as a structural sibling of `useStockfishEngine.ts` (own message protocol, same lifecycle skeleton). Extend `EvalBar` rather than forking it. Extend `/users/me/profile` for the free-play rating default rather than inventing a new source.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Maia ONNX inference (policy + WDL) | Browser Worker thread | — | Mirrors Stockfish precedent; keeps main thread free; MAIA-02 locked |
| Board→tensor encoding, ELO input, legal-move masking, softmax | Frontend (Worker-adjacent glue module) | — | Our own MIT code (MAIA-03) — never copies CSSLab's AGPL JS |
| "Moves by Rating" chart rendering | Frontend (React component, Recharts) | — | Pure presentation over the worker's per-ELO curve output |
| Maia eval bar rendering | Frontend (React component, extends `EvalBar`) | — | Shares the existing Stockfish bar's visual/orientation contract |
| ELO selector + "you are here" default | Frontend (component state) | Backend (rating source) | Game mode reads existing `games.white_rating`/`black_rating`; free play needs a small backend read addition |
| Free-play current-rating default | Backend (`/users/me/profile` read extension) | Frontend (`useUserProfile`) | No schema/migration — a `SELECT ... ORDER BY played_at DESC LIMIT 1` against the existing `ix_games_user_played_at` index |
| ONNX model + onnxruntime-web WASM/WebGPU assets | CDN/Static (`public/`) | — | Vendored runtime data asset, mirrors `public/engine/` Stockfish precedent |
| Ephemeral inference cache | Frontend (in-memory Map, board-session scoped) | — | MAIA-05 — no DB, no localStorage |
| AGPL relicensing (LICENSE, README) | Repo root / docs | — | Non-code surface; no tier ownership beyond the repo itself |
| Backend | None (beyond the one read-extension above) | — | Zero DB writes, zero schema, zero migration (locked) |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `onnxruntime-web` | 1.27.0 (verify at install time) | Runs the Maia-3 ONNX graph client-side (WASM CPU EP + WebGPU EP) | MIT-licensed, maintained by Microsoft, the same runtime `maiachess.com`'s own reference client uses [CITED: spike 004 research, re-confirmed this session via WebSearch] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `recharts` | `^3.8.1` (already a frontend dep) | "Moves by Rating" chart | Already in production use for `EvalChart.tsx`; no new charting library |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `onnxruntime-web` | `transformers.js` (also wraps onnxruntime-web) | Adds an unnecessary abstraction layer over a model that isn't a standard HF pipeline task; more bundle weight for no benefit here |
| Client-side WebGPU EP | WASM-only (no WebGPU) | Simpler, but slower on desktop; D-09 explicitly wants WebGPU preferred when available |
| Vendor `.onnx` + `.wasm` directly to `public/` (Stockfish precedent) | `vite-plugin-static-copy` | Plugin automates the `node_modules → dist` copy but adds a dev dependency; Stockfish precedent (Phase 136 D-03) chose direct commit — planner should follow the same precedent for consistency unless the ONNX model needs to stay out of git (see Pitfall on binary size below) |

**Installation:**
```bash
cd frontend && npm install onnxruntime-web
```

**Version verification:**
```bash
npm view onnxruntime-web version   # 1.27.0 at research time
npm view onnxruntime-web license   # MIT
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `onnxruntime-web` | npm | v1.27.0 published 2026-06-19 (package/org exists since 2021, Microsoft-maintained) | 2,516,349/wk | github.com/Microsoft/onnxruntime | SUS (`too-new` — version-date artifact only) | Flagged — planner adds `checkpoint:human-verify` before `npm install onnxruntime-web` |

**Packages removed due to [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** `onnxruntime-web` — identical false-positive pattern to the `stockfish` package flagged in Phase 136's research (the legitimacy checker keys off the latest version's publish date, not package age). This package is Microsoft's official ONNX Runtime Web build, MIT-licensed, 2.5M weekly downloads, no postinstall script (`npm view onnxruntime-web scripts.postinstall` returned empty), maintained under the same org/repo as the widely-used `onnxruntime-node`. Planner must still gate `npm install onnxruntime-web` behind a `checkpoint:human-verify` task per protocol, but there is no substantive risk signal here beyond the version-date artifact.

*The `maia3_simplified.onnx` model artifact itself is not an npm package and is not covered by this registry-based audit — it is a runtime data asset sourced from CSSLab/maiachess.com per MAIA-01, and its provenance/version-pin is a hands-on task, not a package-legitimacy check.*

---

## Architecture Patterns

### System Architecture Diagram

```
Board position (FEN) + ELO ladder samples (from D-08 range, e.g. 1100..2000 step 100)
     |
     | (from Analysis.tsx: `position` state, same source useStockfishEngine already reads)
     v
[useMaiaEngine hook]  — mounts only when /analysis is open (React.lazy boundary, MAIA-02)
     |
     |-- on mount --> new Worker('/maia/maia-worker.js')  (classic Worker, mirrors Stockfish)
     |                 -> importScripts('/maia/ort.min.js')  (or ort.webgpu.min.js)
     |                 -> feature-detect: navigator.gpu?.requestAdapter()
     |                     -> WebGPU available: executionProviders: ['webgpu']
     |                     -> else: executionProviders: ['wasm']; ort.env.wasm.numThreads = 1
     |                 -> ort.InferenceSession.create('/maia/maia3_simplified.onnx', ...)
     |
     |-- FEN change (debounced, mirrors Layer A in useStockfishEngine) --------------------
     |   1. Encode board -> 64 square tokens x 12-dim one-hot piece planes
     |      (side-to-move-relative flip; history planes if the confirmed
     |      ONNX contract requires n>0 -- walk node.parentId chain, see Code Examples)
     |   2. Build a BATCHED input across the ELO ladder samples (one inference
     |      call, batch dim = ELO sample count) -- confirm the model accepts a
     |      batch dimension for this (MAIA-04's "efficient ELO sweep")
     |   3. session.run({ board: ..., elo: ... }) -> { policy: Float32Array[B,64,64] (or B,4096),
     |                                                  wdl: Float32Array[B,3] }
     |   4. Our own MIT glue (NOT copied from CSSLab):
     |      - mask policy logits to legal moves only (chess.js/python-chess-equivalent
     |        legal-move list for the current FEN)
     |      - softmax the masked logits -> normalized per-legal-move distribution
     |      - expected score E = W + 0.5*D per ELO sample (bar input)
     |      - per-move-per-ELO curve (chart input)
     |   5. Cache result in an ephemeral, board-session-scoped Map<FEN, MaiaResult>
     |      (MAIA-05 -- mirror the existing LIVE_EVAL_CACHE_MAX FIFO pattern in Analysis.tsx)
     |
     v
Returns: {
  perElo: { elo: number, moveProbabilities: Record<san, number> }[],  // chart input
  expectedScoreAtSelectedElo: number,  // 0..1, bar input (D-04)
  wdl: { win: number, draw: number, loss: number },  // full vector, feeds Phase 152
  isReady: boolean,
  isAnalyzing: boolean,
}
     |
     v
[MovesByRatingChart] (Recharts <LineChart>)      [MaiaEvalBar] (extends EvalBar with whiteFraction)
  - top-N-by-peak ∪ {played, best} line cap        - flipped prop shared with Stockfish EvalBar
  - <ReferenceLine x={selectedElo}> "you are here"  - whiteFraction = expectedScoreAtSelectedElo
```

### Recommended Project Structure

```
frontend/
├── public/
│   └── maia/                              # NEW — mirrors public/engine/ (Stockfish precedent)
│       ├── maia-worker.js                 # NEW — classic Worker glue (imports ort + our encoding)
│       ├── ort.min.js / ort.webgpu.min.js # NEW — vendored onnxruntime-web UMD build(s)
│       ├── ort-wasm-simd*.wasm            # NEW — vendored WASM binary(ies)
│       └── maia3_simplified.onnx          # NEW — version-pinned model artifact (MAIA-01)
├── src/
│   ├── hooks/
│   │   └── useMaiaEngine.ts               # NEW — structural sibling of useStockfishEngine.ts
│   ├── lib/
│   │   └── maiaEncoding.ts                # NEW — board→tensor, legal-move mask, softmax (MAIA-03, own MIT code)
│   └── components/analysis/
│       ├── MaiaEvalBar.tsx                # NEW — thin wrapper, OR EvalBar gets a whiteFraction prop
│       └── MovesByRatingChart.tsx         # NEW — Recharts port of spike 006
├── vite.config.ts                         # MODIFY — optimizeDeps.exclude if onnxruntime-web is imported anywhere in frontend source; globIgnores for the new .onnx/.wasm if PWA precache would otherwise grab them
README.md                                  # MODIFY — LIC-02 attribution section (mirror the existing GPLv3 Stockfish note)
LICENSE                                    # MODIFY — MIT -> AGPL-3.0 text (LIC-01)
```

### Pattern 1: Worker Hook Structural Sibling (MAIA-02, MAIA-05)

**What:** `useMaiaEngine` mirrors `useStockfishEngine.ts`'s skeleton — Worker lifecycle in a mount-only `useEffect`, `isReady`/`isAnalyzing` state, tab-hide pause via `visibilitychange`, and a debounced FEN input. The *protocol* differs (structured messages carrying `{fen, eloSamples}` in and `{perElo, wdl}` out, not UCI text lines), but the state-machine shape (idle/thinking/stopping equivalents) and the stale-result guard transfer directly.

**When to use:** This is the primary deliverable of the phase's first plan.

```typescript
// Source: frontend/src/hooks/useStockfishEngine.ts (direct structural precedent)
// The Worker lifecycle, tab-hide pause, and stale-result guard patterns are proven
// in this codebase already -- do not redesign them for Maia.

useEffect(() => {
  if (!enabled) return;
  const worker = new Worker('/maia/maia-worker.js'); // classic Worker, mirrors Stockfish
  workerRef.current = worker;
  worker.onmessage = (e) => handleMaiaMessage(e.data);
  worker.postMessage({ type: 'init', modelUrl: '/maia/maia3_simplified.onnx' });
  return () => {
    worker.postMessage({ type: 'terminate' });
    worker.terminate();
    workerRef.current = null;
  };
}, [enabled]);
```

### Pattern 2: onnxruntime-web Execution-Provider Selection (D-09, MAIA-06)

**What:** Feature-detect WebGPU; force single-thread WASM when falling back, to respect the site-wide no-COOP/COEP constraint (Phase 136 D-3, CI-guarded — see Pitfall 1).

```typescript
// Source: onnxruntime.ai docs (ep-webgpu.html, env-flags-and-session-options.html) — WebSearch this session
// Inside the Worker (maia-worker.js), before InferenceSession.create:

const gpuAdapter = await navigator.gpu?.requestAdapter().catch(() => null);
let executionProviders: string[];
if (gpuAdapter) {
  executionProviders = ['webgpu'];
} else {
  // Single-thread WASM: force numThreads=1 so onnxruntime-web never attempts
  // SharedArrayBuffer-based multi-threading, which requires COOP/COEP headers
  // this site does not and will not ship (Phase 136 D-3, CI-guarded).
  ort.env.wasm.numThreads = 1;
  executionProviders = ['wasm'];
}
const session = await ort.InferenceSession.create('/maia/maia3_simplified.onnx', {
  executionProviders,
});
```

**Pitfall this avoids:** setting `numThreads` > 1 without `crossOriginIsolated` can silently no-op or warn depending on onnxruntime-web version — explicit `numThreads = 1` removes the ambiguity entirely rather than relying on auto-fallback behavior. [CITED: onnxruntime.ai env-flags docs + microsoft/onnxruntime#19148]

### Pattern 3: Board Encoding + History Walk (MAIA-01/03 — the genuinely hard part)

**What:** Per the Chessformer paper (arXiv 2605.19091, fetched directly this session), the model's board representation is 64 square-tokens, each a 12-dim one-hot piece-occupancy plane **stacked over the current + n past positions** (default n=7; "repeat the earliest position if past positions are not available"), board **flipped to the side-to-move's perspective**. If `maia3_simplified.onnx` requires history (unconfirmed — could be n=0 for a lighter, live-navigation-friendly "simplified" build), the glue must walk the existing `nodes.get(id)?.parentId` chain already used elsewhere in `Analysis.tsx` (see `parentFen` derivation) to collect up to 7 preceding FENs.

```typescript
// Source: arXiv 2605.19091 §"Input Representation" (WebFetch this session) +
// frontend/src/pages/Analysis.tsx's existing parentId-walk pattern (parentFen derivation)

function collectHistoryFens(nodes: Map<NodeId, MoveNode>, currentNodeId: NodeId, n: number): string[] {
  const fens: string[] = [];
  let id: NodeId | null = currentNodeId;
  while (fens.length <= n) {
    const node = id !== null ? nodes.get(id) : undefined;
    if (node === undefined) {
      // Repeat the earliest available position (paper's stated padding rule)
      const earliest = fens[fens.length - 1];
      if (earliest !== undefined) fens.push(earliest);
      else break; // no positions at all — should not happen (root is always FEN)
      continue;
    }
    fens.push(node.fen);
    id = node.parentId;
  }
  return fens; // [current, current-1, ..., current-n], padded
}
```

**Confirm before implementing:** whether `maia3_simplified.onnx` actually needs n>0 history at all — a single-position (n=0) simplified export is plausible and would remove this complexity entirely (12-dim planes only, no walk needed). This is exactly why MAIA-01 is sequenced first.

### Pattern 4: Legal-Move Masking + Softmax (MAIA-03 — own MIT code, never copy CSSLab's AGPL JS)

**What:** The paper confirms the policy head outputs a raw 64×64 (from-square × to-square) attention-logit matrix with promotion handled via an additive bias on last-rank key vectors — not a softmax-normalized distribution over legal moves. Masking + softmax is explicitly **our own glue's job** (MAIA-03), using `chess.js` (already a frontend dependency) to enumerate legal moves for the current FEN.

```typescript
// Source: arXiv 2605.19091 §"Policy Head" (WebFetch this session) — architecture only;
// this implementation is original MIT code, not derived from CSSLab's source (spike 005 condition 2).

import { Chess } from 'chess.js';

function maskAndSoftmax(policyLogits: Float32Array /* [64,64] flat or similar */, fen: string): Record<string, number> {
  const chess = new Chess(fen);
  const legalMoves = chess.moves({ verbose: true }); // { from, to, promotion? }[]
  const scores = legalMoves.map((m) => policyLogits[squareIndex(m.from) * 64 + squareIndex(m.to)] ?? -Infinity);
  const max = Math.max(...scores);
  const exps = scores.map((s) => Math.exp(s - max)); // numerically stable softmax
  const sum = exps.reduce((a, b) => a + b, 0);
  const probs: Record<string, number> = {};
  legalMoves.forEach((m, i) => { probs[m.san] = (exps[i] ?? 0) / sum; });
  return probs;
}
```

### Pattern 5: EvalBar Generalization for the Maia Bar (SURF-04, D-04/D-05)

**What:** Rather than forking `EvalBar.tsx`, add an optional `whiteFraction` override so the Maia bar reuses the exact same flip/testid/styling contract the Stockfish bar already has.

```typescript
// Source: frontend/src/components/analysis/EvalBar.tsx (direct read this session)
// EvalBar currently derives whiteFraction internally from evalCp/evalMate via a sigmoid.
// Maia already produces a 0..1 probability (E = W + 0.5*D) -- no sigmoid needed.

export interface EvalBarProps {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
  /** NEW: when provided, bypasses evalCp/evalMate/depth entirely and uses this
   *  fraction directly (0..1, white's share). Used by the Maia bar (D-04). */
  whiteFraction?: number;
  flipped?: boolean;
  className?: string;
}
// computeWhiteFraction(...) becomes: if (whiteFraction !== undefined) return whiteFraction; ...(existing logic)
```

### Pattern 6: "Moves by Rating" Chart — Recharts Port of Spike 006 (SURF-01/02/03)

**What:** Spike 006's cap algorithm and chart shape port directly onto the `<LineChart>`/`<ReferenceLine>` APIs already used in `EvalChart.tsx` — no new Recharts surface needed.

```typescript
// Source: .planning/spikes/006-moves-by-rating-chart/index.html (cap algorithm, verbatim logic)
//         + frontend/src/components/library/EvalChart.tsx (Recharts API precedent, direct read this session)

const TOP_N = 6; // SURF-03 default N ≈ 6

function capMoves(moves: MoveCurve[], playedSan: string, bestSan: string): MoveCurve[] {
  const byPeak = [...moves].sort((a, b) => Math.max(...b.probs) - Math.max(...a.probs));
  const keep = new Set(byPeak.slice(0, TOP_N).map((d) => d.san));
  keep.add(playedSan);
  keep.add(bestSan); // union — SURF-03: always shown even outside top-N
  return moves.filter((d) => keep.has(d.san));
}

// JSX (mirrors EvalChart.tsx's existing <ReferenceLine> usage):
// <LineChart data={perEloRows}>
//   {shownMoves.map((m) => (
//     <Line key={m.san} dataKey={m.san} stroke={colorFor(m, played, best)}
//           strokeWidth={m.san === playedSan || m.san === bestSan ? 3 : 1.5} dot={false} />
//   ))}
//   <ReferenceLine x={selectedElo} stroke={THEME_BRAND} strokeDasharray="4 4" label="you" />
// </LineChart>
```

### Anti-Patterns to Avoid

- **Copying/bundling CSSLab's `MaiaEngineContext` JS or encoding utilities:** even for reference — that combines AGPL *source* into the MIT/AGPL-relicensed frontend and defeats the "own glue" condition (spike 005 condition 2, still relevant post-relicense for hygiene even though AGPL-in-AGPL removes the legal ambiguity).
- **Setting `ort.env.wasm.numThreads` to anything but `1` in the WASM fallback path:** reintroduces the exact SharedArrayBuffer/COOP-COEP dependency Phase 136 explicitly engineered around (CI-guarded — see Pitfall 1).
- **Forking `EvalBar.tsx` into a separate `MaiaEvalBar` component with duplicated flip/style logic:** violates D-04's "clean mirror" framing and creates two divergent bar implementations to maintain.
- **Treating the paper's architecture as a substitute for inspecting the real `maia3_simplified.onnx`:** the paper describes Chessformer generally; the "simplified" export's exact input names, shapes, and whether history is included is unconfirmed and is the phase's literal first task.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ONNX graph execution, WASM/WebGPU dispatch | Custom WASM loader / WebGPU compute pipeline | `onnxruntime-web` | Same tool the model's own authors ship client-side; huge surface to reimplement correctly |
| Legal-move enumeration for masking | Custom chess-move generator | `chess.js` (already a frontend dep) | Already vetted, used throughout the codebase (board interaction, `EngineLines`, etc.) |
| Sigmoid/eval-bar visual logic | A second bar component | Extend `EvalBar` with `whiteFraction` | One flip/orientation/testid contract instead of two to keep in sync |
| Recharts multi-line + reference-line chart shape | A hand-rolled SVG chart (like the spike) | Recharts `<LineChart>`/`<ReferenceLine>` (already proven in `EvalChart.tsx`) | Spike 006 is explicitly "hand-rolled inline SVG so it runs with zero build" — the spike's own README states production should NOT keep this approach |
| Debounce | Custom `setTimeout` wrapper | Existing `useDebounce` hook (`src/hooks/useDebounce.ts`) or the `useStockfishEngine` adaptive-debounce pattern | Already proven in this exact page |

**Key insight:** Every non-ML piece of this phase (worker lifecycle, chart, bar, debounce) has a working precedent already merged into this codebase from Phases 136–140. The only genuinely new surface is the ONNX tensor contract itself — everything else is disciplined reuse, not invention.

---

## Common Pitfalls

### Pitfall 1: Accidentally Requiring COOP/COEP (breaks Google OAuth + iOS Safari)
**What goes wrong:** onnxruntime-web's default WASM backend (since v1.19) ships a "threaded" binary and will attempt `SharedArrayBuffer`-based multi-threading whenever `crossOriginIsolated` happens to be true and `numThreads` isn't pinned — and even where it degrades gracefully, relying on implicit fallback is fragile across onnxruntime-web versions.
**Why it happens:** The library's default thread count is `min(navigator.hardwareConcurrency/2, 4)`, not `1` — the site never intentionally opts into COOP/COEP (Phase 136 D-3 locked this out permanently, CI-guarded via `.github/workflows/ci.yml`'s "No COOP/COEP header guard" step), so any implicit multi-thread attempt either no-ops or (per a documented onnxruntime-web GitHub issue) can produce console warnings/errors under the wrong version.
**How to avoid:** Explicitly set `ort.env.wasm.numThreads = 1` in every code path that doesn't use WebGPU. Never touch `vite.config.ts` or Caddy config to add COOP/COEP for this feature.
**Warning signs:** The existing CI guard (`ci.yml` line ~130) will fail the build if COOP/COEP headers appear on the page — this is a hard backstop, but don't rely on CI to catch a WASM-path regression; verify locally with `window.crossOriginIsolated === false` during manual testing.

### Pitfall 2: Free-Play ELO Default Has No Data Source Today
**What goes wrong:** D-07 assumes `useUserProfile()` already exposes a "current platform rating" — it does not. `UserProfile` (frontend/src/types/users.ts) has no rating field at all, and no backend endpoint computes one.
**Why it happens:** Every existing rating consumer in this codebase reads a *specific game's* stored `white_rating`/`black_rating` (rating-at-game-time), never a "current" aggregate — there was never a need for one before this phase.
**How to avoid:** Extend the existing `/users/me/profile` endpoint (not a new endpoint — a field addition) with a `current_rating: number | null` computed as the most recent game's rating for the platform/color, using the already-indexed `ix_games_user_played_at (user_id, played_at DESC)` — a cheap, indexed, read-only query. No migration, no schema change, no new endpoint; consistent with the phase's "zero DB writes" framing (this is a read).
**Warning signs:** If the planner instead invents a client-side-only fallback (e.g., always defaulting to 1500 even for users with strong signal), the ELO selector's default becomes meaningfully wrong for engaged users — flag this to the planner explicitly rather than silently degrading to the 1500 fallback for everyone.

### Pitfall 3: Treating the Chessformer Paper as the ONNX Export Contract
**What goes wrong:** The paper describes the *training-time* model (352-dim per-token input including precomputed rating embeddings) — but ONNX exports conventionally bake embedding lookups into the graph and expose raw scalar inputs (e.g., a `white_elo`/`black_elo` int input), not precomputed 352-dim vectors. Assuming the paper's internal representation is the literal ONNX input shape will produce a wrong tensor and a silent shape-mismatch error (or worse, a shape that happens to run but produces garbage).
**Why it happens:** Research-grounded paper analysis and hands-on ONNX inspection are two different sources of truth; this session could only do the former.
**How to avoid:** MAIA-01's hands-on step must inspect the real `session.inputNames`/`session.outputNames` (or view the graph in [netron.app](https://netron.app)) before writing any encoding glue against assumed shapes.
**Warning signs:** onnxruntime-web throws a clear shape-mismatch error at `session.run()` time if the input tensor doesn't match — this is a loud failure, not a silent one, which is reassuring but still costs a debugging cycle if the contract is guessed wrong going in.

### Pitfall 4: WebGPU Op-Support Gaps for Custom Attention (GAB)
**What goes wrong:** Chessformer's Geometric Attention Bias is a non-standard positional-bias mechanism layered onto standard scaled-dot-product attention. WASM supports all ONNX ops; WebGPU supports only a subset. If GAB or the attention-based policy head exports to an op WebGPU doesn't implement, `executionProviders: ['webgpu']` will throw at session-create time.
**Why it happens:** WebGPU EP op coverage in onnxruntime-web trails the WASM EP by design (newer, actively-developed backend).
**How to avoid:** MAIA-06's "confirm no unsupported-op errors" must be tested explicitly against WebGPU, not just WASM — feature-detection (`navigator.gpu`) only proves the *browser* supports WebGPU, not that *this specific graph* runs on it. Wrap `InferenceSession.create(..., { executionProviders: ['webgpu'] })` in a try/catch that falls back to `['wasm']` on failure, in addition to the `navigator.gpu` pre-check.
**Warning signs:** A caught exception during session creation, or (worse, per a documented onnxruntime-web GitHub issue) a session that creates successfully but produces *different numeric output* between WebGPU and WASM/CUDA for the same input — worth a manual eyeball cross-check between backends during VALID-01, not just a "does it load" check.

### Pitfall 5: Model File Size vs Git / PWA Precache
**What goes wrong:** Spike 004's size table (5M≈20MB fp32, quantized ~¼) means even the smallest model is plausibly 5–20MB — larger than the Stockfish WASM binary already committed (~7MB) but same order of magnitude. If this gets swept into the PWA's Workbox precache manifest (same `globIgnores` issue Phase 136 solved for `.wasm`), iOS Safari's ~50MB Cache API ceiling is at real risk of being exceeded when combined with the existing Stockfish assets.
**How to avoid:** Add `.onnx` (and any new `.wasm` filename pattern from onnxruntime-web, which differs from Stockfish's) to `vite.config.ts`'s `globIgnores`, mirroring the existing `**/*.wasm` entry (which won't automatically catch onnxruntime-web's differently-named WASM files unless the glob is broad enough — verify).
**Warning signs:** `npm run build` + inspect `dist/sw.js` for accidental `.onnx`/onnxruntime `.wasm` precache entries, exactly the verification step Phase 136's research documented for Stockfish.

### Pitfall 6: Spike 006's Chart Is a Throwaway, Not a Component
**What goes wrong:** Spike 006's `index.html` hand-rolls raw SVG path/circle/text manipulation with vanilla DOM APIs — a naive "port" that copies this imperative code into a React component instead of an idiomatic Recharts `<LineChart>` would violate the project's existing `EvalChart.tsx` conventions and reintroduce hover/tooltip logic Recharts already provides.
**How to avoid:** Treat the spike strictly as a **visual/behavioral spec** (cap rule, colors, marker, tooltip content) — implement with Recharts primitives from scratch, following `EvalChart.tsx`'s existing patterns (custom tooltip via `content` prop, `ReferenceLine` for the "you are here" marker), not a line-by-line SVG port.

---

## Code Examples

### Ephemeral Session Cache (MAIA-05) — Reuse the Existing FIFO Pattern

```typescript
// Source: frontend/src/pages/Analysis.tsx (direct read this session — LIVE_EVAL_CACHE_MAX pattern)
// This exact FIFO-Map-with-cap pattern already exists for the Stockfish live-eval cache;
// reuse verbatim for Maia (keyed by FEN + selected ELO, since results are ELO-dependent).

const MAIA_CACHE_MAX = 256; // mirrors LIVE_EVAL_CACHE_MAX

const [maiaResultByKey, setMaiaResultByKey] = useState<Map<string, MaiaResult>>(() => new Map());

function cacheKey(fen: string): string {
  return fen; // the per-ELO curve is computed for the WHOLE ladder in one batch, so FEN alone keys it
}

// On new result:
setMaiaResultByKey((prev) => {
  const next = new Map(prev);
  next.set(cacheKey(fen), result);
  if (next.size > MAIA_CACHE_MAX) {
    const oldest = next.keys().next().value;
    if (oldest !== undefined) next.delete(oldest);
  }
  return next;
});
```

### Expected Score Computation (D-04)

```typescript
// Source: SEED-081 design (D-04 locked) — pure arithmetic, no external reference needed
function expectedScore(wdl: { win: number; draw: number; loss: number }): number {
  // W + 0.5*D, already normalized 0..1 since W+D+L=1 after softmax on the 3 WDL logits
  return wdl.win + 0.5 * wdl.draw;
}
```

### README Attribution Section (LIC-02) — Mirror the Existing Stockfish Precedent

```markdown
<!-- Source: README.md's existing "Engine Binaries (GPLv3 License Note)" section
     (direct read this session) -- mirror its structure for Maia -->

## Maia-3 Model (AGPL-3.0 License Note)

The file `frontend/public/maia/maia3_simplified.onnx` is an unmodified model artifact from
[CSSLab/maia3](https://github.com/CSSLab/maia3) ("Chessformer", Monroe et al.), licensed under
the [GNU Affero General Public License v3 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html).
FlawChess is itself AGPL-3.0 licensed (see LICENSE) as of this release. The model is loaded
unmodified via the MIT-licensed `onnxruntime-web` runtime; no CSSLab source code is copied or
bundled — all board/ELO encoding, legal-move masking, and probability normalization is FlawChess's
own code. Citation: Monroe et al., "Chessformer: A Unified Architecture for Chess Modeling"
(arXiv:2605.19091).
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server-side/backend inference for any chess ML model | Client-side ONNX via `onnxruntime-web`, mirroring `maiachess.com`'s own architecture | Established by spike 004 (2026-07-04), consistent with this codebase's Phase 136 Stockfish precedent | Zero server load, zero new backend surface, consistent with the milestone's "zero DB writes" framing |
| Multi-threaded WASM (SharedArrayBuffer, COOP/COEP) | Single-thread WASM (`numThreads=1`) as the fallback, WebGPU preferred when available | This codebase locked multi-thread WASM out entirely in Phase 136 (D-3); onnxruntime-web's WebGPU EP (mainstream since ~2024) makes "prefer GPU, fall back to safe single-thread CPU" viable without ever needing cross-origin isolation | Avoids reopening the COOP/COEP decision that already broke OAuth once during this project's history (implied by the CI guard's comment) |
| Non-monotonic curve local-slope trainability metric | Endpoint-difference trainability metric (your-ELO vs top-ELO) | Locked in SEED-081 design session (2026-07-04), driven by the Ne4-hump/O-O-mirror example | Only relevant to Phase 152, but the chart output (full per-ELO curve) this phase produces must preserve every ELO sample so Phase 152 can compute the endpoint difference — don't collapse/discard curve data after rendering |

**Deprecated/outdated:**
- Non-threaded, non-SIMD onnxruntime-web WASM builds — removed from the published package since ~v1.19; only the SIMD-threaded artifact ships, controlled at runtime via `numThreads`.
- Treating "Apache 2.0" secondary-press claims about Maia-3's license as authoritative — confirmed wrong in prior research (`maia-3-integration.md`); the actual repo `LICENSE` is AGPL-3.0.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `maia3_simplified.onnx` exposes raw ELO scalar input(s) rather than requiring the caller to precompute the 352-dim embedding vector | Architecture Patterns, Summary | If wrong, the glue must replicate the weak/strong embedding interpolation math itself — significantly more complex, and arguably crosses from "using the model as data" into "reimplementing model internals," worth flagging as a license-posture question too |
| A2 | The "simplified" in `maia3_simplified.onnx` means no/reduced history conditioning (n=0 or small n), not just a quantization/export simplification | Pattern 3, Summary | If history IS required at full n=7, the board-encoding glue needs the parentId-walk (documented) but adds meaningful latency/complexity per-inference, worth re-measuring against MAIA-06's latency target |
| A3 | Maia-3's internal ELO scale (paper's `k`, 0–5000 interpolation range) maps roughly linearly onto real chess ratings 600–2600, matching the maiachess.com UI's displayed range | Layout & placement, D-08 | If the true scale differs, D-08's provisional 1100–2000 range (and the rating-at-game-time / current-platform-rating inputs) could map to the wrong internal `k`, producing systematically miscalibrated curves — exactly what VALID-01 exists to catch |
| A4 | onnxruntime-web's WASM EP, forced to `numThreads=1`, is fast enough for interactive per-position latency on a mid-range phone for the smallest Maia-3 model | Standard Stack, Common Pitfalls | If too slow, MAIA-06's own measurement step (not this research) is the intended place to discover this and escalate to WebGPU-only or a smaller/quantized model — consistent with D-10's escalation path |
| A5 | The WDL 3-logit order is Win/Draw/Loss (not some other permutation) | Pattern in Summary / Code Examples | A silently swapped W/L order would flip the entire practical-severity framing (Phase 152) and the bar's sign — VALID-01's live eyeball check is explicitly designed to catch exactly this class of error |

**If this table is empty:** N/A — several claims here genuinely require the phase's own hands-on pass to resolve; that is by design (MAIA-01/MAIA-06/VALID-01 exist specifically to close these gaps).

---

## Open Questions

> **All three are DELIBERATELY DEFERRED to Plan 151-01's hands-on MAIA-01 tasks — not left open.** They cannot be answered by desk research (they require loading + inspecting the real `maia3_simplified.onnx`), which is exactly why MAIA-01 is sequenced as the phase's literal first plan. Each carries a `→ RESOLVED BY` pointer to the 151-01 task that closes it.

1. **Does `maia3_simplified.onnx` accept a batched ELO dimension for one inference call, or does the full per-ELO curve require N separate `session.run()` calls?**
   - **→ RESOLVED BY: 151-01 Task 3** (tensor-contract inspection) records batch-dim support alongside policy/WDL layout in `151-MAIA-CONTRACT.md`; **151-06 Task 4** (MAIA-06) times batch=N vs N×batch=1 and picks the faster supported path.
   - What we know: Rating conditioning is architecturally per-token (embeddings appended to every square token), which is compatible with batching the same board across a batch dimension while varying only the rating embedding/input per batch item — this is the standard way to get a "curve in one call" from a batch-capable ONNX graph.
   - What's unclear: Whether the exported "simplified" graph actually declares a batch dimension in its input shape (some simplified/mobile-oriented ONNX exports fix batch=1 for a smaller/faster graph).
   - Recommendation: MAIA-06's hands-on measurement should explicitly time "1 call with batch=N" vs "N calls with batch=1" and pick whichever the graph supports/is faster — this directly determines interactive latency for the "every position, live" requirement (SURF-05).

2. **Is a hosted CDN copy of `maia3_simplified.onnx` available (avoiding vendoring a multi-MB binary into git), or must it be committed like the Stockfish precedent?**
   - **→ RESOLVED BY: 151-01 Task 2** — the plan commits a pinned, vendored copy to `frontend/public/maia/` (Stockfish precedent: reproducible, no runtime third-party fetch), which settles the question regardless of CDN availability.
   - What we know: `maiachess.com` serves the model to browsers somehow (client-side per spike 004) — likely from their own CDN/static hosting, not npm.
   - What's unclear: Whether that URL is stable/public enough to fetch-and-vendor at build time, or whether FlawChess must download-and-commit its own pinned copy (matching MAIA-01's "version-pinned" requirement, which favors committing a pinned copy regardless of CDN availability, to guarantee reproducibility).
   - Recommendation: Commit a pinned copy to `public/maia/` (git), consistent with the Stockfish precedent's "reproducible, no runtime fetch of a third-party artifact" reasoning — even if a CDN URL exists, don't depend on its long-term availability/version-stability.

3. **What is `maia3_simplified.onnx`'s actual total file size?**
   - **→ RESOLVED BY: 151-01 Task 2** — the plan records the real byte size (and SHA-256 + source URL) in `frontend/public/maia/README.md` when the artifact is vendored, before downstream work proceeds.
   - What we know: Spike 004's size table is per-parameter-count fp32 estimates (5M≈20MB), not a measurement of the actual "simplified" export, which could be quantized (~¼ size) or otherwise optimized.
   - What's unclear: The real number, which directly affects MAIA-06's model-size decision and mobile download-latency framing.
   - Recommendation: The very first hands-on step (MAIA-01) should report this number before any other work proceeds — it's a `curl -sI` / `ls -la` away once the file is located.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `npm install onnxruntime-web` | Yes | v24 (per CI/CLAUDE.md) | — |
| `onnxruntime-web` (npm) | MAIA-02/03 | Not yet installed | 1.27.0 at research time | — |
| WebGPU (browser) | D-09 preferred backend | Feature-detected at runtime, not an install-time dependency | ~82% global browser support per 2026 WebSearch estimate; Safari support is inconsistent | WASM CPU EP (always available; `numThreads=1`) |
| `chess.js` | Legal-move masking (Pattern 4) | Yes (already a frontend dep, `^1.4.0`) | current | — |
| `recharts` | Chart | Yes (already a frontend dep, `^3.8.1`) | current | — |
| Real `maia3_simplified.onnx` artifact + its exact I/O contract | MAIA-01 (blocking everything downstream) | Not verified this session (research-grounded only, no live download/inspect) | — | None — this is the phase's mandated first hands-on step, not optional |

**Missing dependencies with no fallback:**
- The confirmed ONNX tensor I/O contract (MAIA-01) — everything else in this phase is gated on it.

**Missing dependencies with fallback:**
- WebGPU unavailability → WASM single-thread fallback (D-09, already the locked design).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.7 (frontend), no backend test framework needed (no backend code changes beyond the optional profile-endpoint field) |
| Config file | none (defaults from `vite.config.ts`) |
| Quick run command | `npm test` (from `frontend/`) |
| Full suite command | `npm test` + `npm run build` (tsc + vite build catches type errors `npm test` alone misses, per CLAUDE.md) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAIA-01 | ONNX model loads with no unsupported-op errors on both WASM and WebGPU | integration/manual (real WASM/WebGPU cannot be meaningfully mocked) | `npm test -- src/hooks/__tests__/useMaiaEngine.integration.test.ts` (mirrors `useStockfishEngine.integration.test.ts` pattern — Node-side ORT if available, else browser manual check) | No — Wave 0 |
| MAIA-03 | Board→tensor + legal-move mask + softmax produces a normalized distribution summing to 1 | unit | `npm test -- src/lib/__tests__/maiaEncoding.test.ts` | No — Wave 0 |
| MAIA-04 | Full per-ELO curve computed for a known FEN; WDL value returned | unit/integration (fixture ONNX output or real model) | same file | No — Wave 0 |
| MAIA-05 | Cache is capped at `MAIA_CACHE_MAX`, board-session only (no `localStorage`/DB writes) | unit | `npm test -- src/pages/__tests__/Analysis.maiaCache.test.tsx` (or extend existing `Analysis` test coverage) | No — Wave 0 |
| SURF-01/02/03 | Chart renders correct line count (top-N ∪ {played,best}), reference line at selected ELO | unit (React Testing Library + Recharts snapshot or DOM query) | `npm test -- src/components/analysis/__tests__/MovesByRatingChart.test.tsx` | No — Wave 0 |
| SURF-04 | Maia bar renders LEFT of board, Stockfish bar RIGHT, both visible simultaneously | unit (component) + manual (visual) | `npm test -- src/components/analysis/__tests__/EvalBar.test.tsx` (extend existing if present) | Check — may not exist yet |
| VALID-01 | Manual live-eyeball calibration check across representative positions; size/latency measured | **manual-only** — explicitly not automatable (calibration judgment call, per D-10) | N/A — HUMAN-UAT | N/A |

### Sampling Rate
- **Per task commit:** `npm test` (relevant test files only)
- **Per wave merge:** `npm test` + `npm run build` + `npm run lint`
- **Phase gate:** Full pre-merge gate per CLAUDE.md (`ruff format/check`, `ty check`, `pytest -n auto` if any backend field was touched, frontend lint+test) plus the manual VALID-01 eyeball/measurement pass — this gate is explicitly NOT a green-checkmark-only gate (D-10: "measure-and-judge, not a hard ship-block").

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/maiaEncoding.test.ts` — board encoding, legal-move masking, softmax normalization unit tests (the one piece of this phase that's pure, deterministic, and fully unit-testable without a real ONNX session)
- [ ] `frontend/src/hooks/__tests__/useMaiaEngine.test.ts` — mock-worker unit tests mirroring `useStockfishEngine.test.ts`'s structure
- [ ] `frontend/src/hooks/__tests__/useMaiaEngine.integration.test.ts` — real-model integration test, IF a Node-side onnxruntime path is feasible (check `onnxruntime-node` as a dev-only test dependency, mirroring how `stockfish`'s Node entry point was used for Phase 136's integration test) — otherwise this becomes a manual/browser-only verification step, documented as such rather than silently skipped
- [ ] `frontend/src/components/analysis/__tests__/MovesByRatingChart.test.tsx`, `MaiaEvalBar.test.tsx` (or extended `EvalBar.test.tsx`) — component-level coverage for SURF-01..05

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface touched by this phase |
| V3 Session Management | No | Worker/hook is stateless per browser session |
| V4 Access Control | No | No new endpoint; the one profile-field addition reads only `request.user`'s own games (existing auth dependency already enforces this on `/users/me/profile`) |
| V5 Input Validation | Yes (limited) | FEN passed to `chess.js` for legal-move enumeration is already validated elsewhere on this page (T-138-01 FEN guard in `Analysis.tsx`); the ONNX model itself receives only derived tensors, not raw user text |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious/tampered `.onnx` model artifact (supply chain) | Tampering | Committed to git, version-pinned (MAIA-01) — same mitigation as the Stockfish WASM binary precedent; no runtime fetch of the model from a third party |
| `npm install onnxruntime-web` postinstall risk | Tampering | `npm view onnxruntime-web scripts.postinstall` returned empty this session — no postinstall script; still gate behind `checkpoint:human-verify` per the SUS legitimacy verdict |
| Accidental COOP/COEP reintroduction breaking OAuth | Elevation of Privilege (auth bypass avoidance, inverted — this is an availability/breakage risk, not an EoP path, but shares the same CI backstop) | Existing CI guard (`ci.yml`) already fails the build on any COOP/COEP header regression — no new mitigation needed, just don't defeat it |
| Worker message payload spoofing (a compromised extension or same-origin script posting fake `MessageEvent`s to the Maia worker) | Spoofing | Same trust model as the existing Stockfish worker (same-origin, no cross-origin `postMessage` target) — no new mitigation needed beyond what's already accepted for the engine worker |

---

## Sources

### Primary (HIGH confidence — project-internal)
- `.planning/phases/151-maia-in-the-browser-all-position-surfaces/151-CONTEXT.md` — locked decisions D-01..D-10, phase boundary
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` §Phase 151 — requirement IDs, success criteria
- `.planning/seeds/SEED-081-...md`, `.planning/spikes/004/005/006` — feasibility, license posture, chart prototype
- `.planning/research/maia-3-integration.md`, `.planning/research/questions.md` (Q-013..Q-016) — prior license/technical research
- `frontend/src/hooks/useStockfishEngine.ts`, `frontend/src/components/analysis/EvalBar.tsx`, `frontend/src/pages/Analysis.tsx`, `frontend/src/hooks/useUserProfile.ts`, `frontend/src/lib/theme.ts`, `frontend/src/components/library/EvalChart.tsx` — direct code reads this session
- `frontend/vite.config.ts`, `.github/workflows/ci.yml`, `.planning/milestones/v1.29-phases/136-.../136-RESEARCH.md`, `README.md` — direct reads this session (COOP/COEP guard, Stockfish vendoring precedent, GPLv3 attribution section)
- `app/models/game.py` (`ix_games_user_played_at` index), `app/routers/users.py`, `frontend/src/types/users.ts` — direct reads confirming the free-play rating gap (Pitfall 2)
- `frontend/package.json` — confirmed `recharts@^3.8.1`, `chess.js@^1.4.0`, `stockfish 18.0.8` already present; `onnxruntime-web` absent

### Secondary (MEDIUM confidence — web-verified this session)
- [arXiv 2605.19091 (Chessformer)](https://arxiv.org/html/2605.19091) — WebFetch this session; board tokenization, GAB, policy/value head architecture
- [onnxruntime.ai env-flags-and-session-options](https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html), [ep-webgpu](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html) — WebFetch this session
- [npm onnxruntime-web registry](https://www.npmjs.com/package/onnxruntime-web) — `npm view` this session (v1.27.0, MIT, no postinstall)
- [github.com/CSSLab/maia3](https://github.com/CSSLab/maia3), [csslab/maia-platform-frontend](https://github.com/csslab/maia-platform-frontend) — WebSearch/WebFetch this session (architecture confirmation; exact client-side encoding source not directly inspectable via the fetch tool)
- WebSearch results on onnxruntime-web threading/COOP-COEP behavior, WebGPU feature detection (`navigator.gpu`), onnxruntime-web + Vite bundler integration patterns

### Tertiary (LOW confidence — context only)
- General WebGPU browser-support percentage estimates (~82% global, 2026) — directional only, not load-bearing for any decision in this research
- Secondary press claims about Maia-3's license being "Apache 2.0" — explicitly flagged as WRONG in prior research; repeated here only as a contrast/warning, not as a source

---

## Metadata

**Confidence breakdown:**
- Standard stack (`onnxruntime-web`, `recharts`): HIGH — versions/licenses confirmed via `npm view`; both are established, widely-used packages
- Worker hook / chart / bar architecture patterns: HIGH — directly extend proven, merged code in this exact codebase (Phases 136–140)
- `maia3_simplified.onnx` exact tensor I/O contract: LOW — paper-grounded architecture understanding only; the model's *actual* ONNX export contract is explicitly unconfirmed and is the phase's mandated hands-on task (MAIA-01)
- AGPL relicensing mechanics: HIGH — concrete file list identified via direct repo inspection (LICENSE, README sections, absence of `license` fields in `package.json`/`pyproject.toml`)
- Free-play rating gap (Pitfall 2): HIGH — directly confirmed by reading `types/users.ts`, `app/routers/users.py`, and `app/models/game.py`'s existing index; this is a real gap the planner must address, not a guess

**Research date:** 2026-07-05
**Valid until:** 2026-07-19 (14 days — onnxruntime-web ships frequent releases; the `maia3_simplified.onnx` artifact and its hosting location could also change without notice, being a third-party research artifact rather than a versioned release)
