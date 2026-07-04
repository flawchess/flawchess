---
spike: 004
name: maia3-onnx-browser-feasibility
type: standard
validates: "Given the Maia-3 checkpoint, when exported to ONNX and run via onnxruntime-web, then the browser can produce the full per-ELO policy over legal moves + WDL for a position at acceptable model-download size and inference latency"
verdict: VALIDATED
related: []
tags: [maia, onnx, browser, onnxruntime-web, seed-081]
---

# Spike 004: Maia-3 in the browser (ONNX + onnxruntime-web)

## What This Validates

Given the Maia-3 model, when run client-side via ONNX Runtime Web, then the browser can
produce the per-ELO move-probability distribution + WDL we need for the analysis-board feature
(SEED-081) — **without any server inference**.

> **Method note:** per the spike-scope decision this is a **research-grounded feasibility
> verdict**, not a hands-on export/run in this sandbox. The remaining hands-on items (measure
> real size/latency, confirm tensor I/O) are listed under "What still needs a hands-on pass."

## Research

Docs / sources checked:
- `CSSLab/maia-platform-frontend` (the maiachess.com frontend) — README + architecture.
- `CSSLab/maia3` repo README + HF model cards (`UofTCSSLab/Maia3-23M`/`-79M`).
- Chessformer paper (arXiv 2605.19091) — architecture + heads.
- onnxruntime-web docs; `hunterchen7/play-lc0` (independent lc0-in-browser via ORT Web).

### The decisive finding

**maiachess.com runs Maia in the user's browser, client-side, via `onnxruntime-web`.** Their
`MaiaEngineContext` React provider "handles the download, initialization, and execution of the
various Maia models" as **ONNX** files, executed in WASM (CPU) or WebGPU. They run **Stockfish
*and* Maia entirely in-browser** — the exact architecture SEED-081 wants is the model authors'
own reference implementation, not a bet.

**A Maia-3-specific ONNX artifact exists publicly:** `maia3_simplified.onnx` (from
maiachess.com). So we are not blocked on exporting Chessformer→ONNX ourselves — a working
export already ships. (The HF cards distribute PyTorch `.pt`; the ONNX is the platform's
converted artifact.)

### Architecture fit (why ONNX export is clean)

Chessformer (Maia-3) is an **encoder-only transformer**: board squares as tokens + Geometric
Attention Bias (GAB, a dynamic positional bias) + two heads:
- **Policy head** — self-attention "from-to": query=from-square, key=to-square, scaled
  dot-product → a 64×64 move-logit matrix (mask to legal moves, softmax).
- **Value head** — mean-pool → LayerNorm → Linear(128) → ReLU → Linear(3) → **WDL** logits.

These are standard transformer ops ORT Web supports; the existence of `maia3_simplified.onnx`
proves the whole graph (incl. GAB + the attention policy head) exports and runs.

### Rating conditioning = exactly our chart

Maia-3 is **rating-conditioned** (continuous ELO input), reaching 57.1% move-match with <¼ the
params of prior SOTA. maiachess.com/analysis already renders the per-rating "Moves by Rating"
curve the user screenshotted — evidence the *full-ELO-ladder* output is obtainable client-side.
For our chart we run inference across a sweep of ELO inputs (or a single call if the graph
accepts a rating vector) and read the policy row per candidate move.

### Model size (download cost — the main client-side tax)

Params → rough fp32 on-disk: **5M ≈ 20 MB, 23M ≈ 90 MB, 79M ≈ 320 MB**; int8/quantized
roughly ¼ of that. `maia3_simplified.onnx` size is TBD (hands-on) but "simplified" suggests a
deployment-optimized graph. **Recommendation: start with the smallest Maia-3 ONNX**, lazy-load
it only when the analysis board opens (never in the initial bundle), cache in the browser.

## Competing approaches

| Approach | Tool | Pros | Cons | Status |
|----------|------|------|------|--------|
| Client-side (chosen) | onnxruntime-web (WASM/WebGPU) | authors' reference impl; zero server load; offline; private | model download; AGPL-in-MIT-bundle (→ spike 005); ELO-sweep cost | **Chosen** |
| Server-side sync endpoint | PyTorch on backend | runs `.pt` as-is; clean AGPL arm's-length | worker/backend CPU+RAM (OOM history); round-trip; **not** the pull-based worker fleet | Fallback |

**Chosen:** client-side — it's the proven reference path and matches the existing client-side
Stockfish precedent (`stockfish@18.0.8` already a frontend dep). Server-side stays the fallback
if spike 005 (license) blocks bundling.

## What still needs a hands-on pass (before/early in the build)

1. **Obtain `maia3_simplified.onnx`** (locate in maia-platform-frontend / its CDN) and confirm
   its exact **input encoding** (board planes + how ELO is fed) and **output tensor layout**
   (policy 64×64 vs flat; WDL order).
2. **Measure**: file size (download), and **per-position latency** in WASM vs WebGPU on a
   mid-range laptop and a phone (PWA is mobile-first) — and the cost of an ELO **sweep** (N
   inferences for the curve) vs a single batched call.
3. Confirm **onnxruntime-web** loads it with no unsupported-op errors (expected fine — the ONNX
   already exists).
4. License clearance for shipping the AGPL ONNX in an MIT frontend → **spike 005**.

## Results

**VERDICT: VALIDATED (feasibility).** Client-side Maia-3 in the browser is the model authors'
own shipped architecture (maiachess.com via onnxruntime-web), a Maia-3 ONNX (`maia3_simplified.onnx`)
already exists publicly, the transformer graph demonstrably exports/runs, the model is
rating-conditioned to produce exactly our per-ELO curve, and we already ship a client-side WASM
engine (Stockfish) so the pattern is established here. No technical blocker found.

**Caveats (why not "VALIDATED, done"):** the download-size and latency numbers — the real
client-side tax — are unmeasured, and the ONNX tensor I/O contract is unconfirmed. These are
"measure and wire up," not "does it work." The one genuine gating risk is legal, not technical
(spike 005).

**Surprise:** we assumed we might have to export Chessformer→ONNX ourselves; instead a
deployment ONNX already ships. That removes the biggest technical unknown.
