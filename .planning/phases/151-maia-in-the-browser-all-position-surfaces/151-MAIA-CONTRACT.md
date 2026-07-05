# 151-MAIA-CONTRACT — Confirmed `maia3_simplified.onnx` tensor contract

**Status:** CONFIRMED against a real load + inference (Plan 151-01, Task 3).
**Model:** `frontend/public/maia/maia3_simplified.onnx` — SHA-256 `405bf76c15727dad8728b352c06a8f3c1b80fb2760e8d666b32485c63d75b856`, 45,683,686 bytes, from https://maiachess.com/maia3/maia3_simplified.onnx (2026-07-05).
**Evidence:** `node scripts/inspect_maia_onnx.mjs` (onnxruntime-web WASM EP, `numThreads=1`) + a batched ELO-sweep probe. Loads + runs with **no unsupported-op error** (MAIA-06 satisfied on the WASM/CPU path — the exact runtime the browser worker ships).

> Wave 2+ (glue math, worker, chart, bar) builds against THIS file, not the Chessformer paper's training-time architecture (RESEARCH Pitfall 3).

---

## TL;DR for Wave 2 encoding glue

- **Policy layout: FLAT 4352-length move-index vector** (NOT a 64×64 from→to matrix, NOT flat 4096). Index moves through a fixed `from+to+promotion` → index vocabulary of size 4352.
- **WDL logit order: `[Loss, Draw, Win]`** (index 0 = Loss, 1 = Draw, 2 = Win). This is the A5 permutation — it is **not** W/D/L.
- **ELO is fed as two raw continuous float scalars** (`elo_self`, `elo_oppo`), side-to-move-relative — NOT `white_elo`/`black_elo`, NOT precomputed embedding vectors, NOT category indices. Assumption A1 = CONFIRMED (embedding is inside the graph).
- **Board tokens are 12 planes only, single position (n = 0 history)** — "simplified" drops history. No parent-FEN walk needed.
- **Batch dimension is real** — a whole ELO ladder is ONE `session.run` call (Open Question 1 = YES).

---

## Declared I/O (from `session.inputMetadata` / `outputMetadata`)

### Inputs

| Name | Type | Declared shape | Meaning |
|------|------|----------------|---------|
| `tokens` | float32 | `[unk__0, 64, 12]` | Board planes. Batch dim `unk__0`; 64 squares; 12 one-hot piece planes per square. |
| `elo_self` | float32 | `[batch_size]` | Raw ELO of the side to move (continuous scalar, e.g. `1500.0`). |
| `elo_oppo` | float32 | `[batch_size]` | Raw ELO of the opponent (continuous scalar). |

### Outputs

| Name | Type | Declared shape | Meaning |
|------|------|----------------|---------|
| `logits_move` | float32 | `[batch_size, 4352]` | Policy logits over the fixed 4352-move vocabulary (mask to legal, then softmax). |
| `logits_value` | float32 | `[batch_size, 3]` | WDL value logits in order **[Loss, Draw, Win]**. |

Start-position inference (batch 1, elo_self=elo_oppo=1500) returned `logits_move` dims `[1,4352]` and `logits_value` dims `[1,3]`, confirming the declared shapes resolve at runtime.

---

## (a) Board-plane input encoding

- **Shape `[B, 64, 12]`**, square-major: for square `s` (0..63), a 12-dim one-hot occupancy vector.
- **Square index** `s = row*8 + file`, `row = 7 - rank` from the FEN piece-placement field (a1 = 0 … h8 = 63).
- **12-plane order:** white `P, N, B, R, Q, K` (0–5), black `p, n, b, r, q, k` (6–11).
- **Side-to-move POV:** the board is presented from the mover's perspective — **if it is Black to move, mirror the FEN first** (flip ranks + swap piece colors) so the model always sees "self" as White. (Confirmed via the CSSLab reference: `preprocessMaia3` mirrors on black-to-move.)
- **History n = 0** — only the current position; the "simplified" export carries no history planes. No side-to-move / castling / en-passant channels in the Maia-3 token tensor (that 18-channel form is the older Maia-2 path — do NOT use it here).

## (b) How ELO is fed

- **Two raw float scalars**, `elo_self` and `elo_oppo`, each shape `[B]`. Pass the actual rating value (e.g. `1500.0`) — the model does continuous interpolation internally (no category bucketing, no caller-side embedding). Assumption A1 CONFIRMED.
- They are **side-relative** (self = mover, oppo = opponent), not color-keyed. After the black-to-move mirror, `elo_self` is the side that just became "White" in the mirrored board.

## (c) Confirmed ELO range + ladder granularity (D-08)

- The graph accepts a **continuous** scalar; there is no hard-coded enum, so nothing in the model file caps the range.
- **Behavioral confirmation:** sweeping the start position across ELO {1100, 1500, 1900, 2000} (same value for self+oppo) produced a **monotonically rising draw probability** (D: 0.023 → 0.026 → 0.037 → 0.042) — the expected human pattern (stronger players draw more), proving the ELO input is live and meaningful across that span.
- **Recommended ladder for the UI:** **1100–2000 in 100-ELO steps** (10 rungs), matching maiachess.com's own range. This is the maia-3 training/deployment sweet spot; values far outside were not trained and should not be offered. Treat 1100–2000 as the surfaced range; a single batched call covers all 10 rungs (see (f)).
- CONFIRM-AT-RUNTIME (minor): exact behavior below ~1100 / above ~2000 is untested here and out of the surfaced range — no need to probe unless the UI later exposes extremes.

## (d) Policy output layout + move mapping

- **`logits_move` is a flat `[B, 4352]` vector** — one logit per entry in a fixed move vocabulary. NOT a 64×64 matrix; NOT 4096.
- **Move → index:** key each legal move as the string `from + to + promotion` (e.g. `e2e4`, `e7e8q`) and look it up in Maia-3's move dictionary (CSSLab ships `all_moves_maia3.json` / `..._reversed.json`, 4352 entries). Wave 2 must ship **our own** vocabulary/index table (regenerate or derive it — do NOT copy CSSLab's AGPL JS; the JSON data mapping itself is a lookup table we can reconstruct).
- **Promotions** are distinct vocabulary entries (`...q/r/b/n`). **Castling** is encoded as the normal king two-square move (`e1g1` etc.); **en passant** as the normal pawn capture move. No separate special-move planes.
- **Usage:** build a legal-move mask (1.0 at each legal move's index, 0 elsewhere), apply to `logits_move`, softmax over the masked entries → per-move probability. (Wave 2 MIT glue — MAIA-03.)
- **Mirror caveat:** because the board is mirrored on black-to-move, the returned move indices are in the mirrored frame — Wave 2 must un-mirror move squares back to real board coordinates for display.

## (e) WDL output + confirmed logit order

- **`logits_value` is `[B, 3]` in order `[Loss, Draw, Win]`** (index 0 = Loss, 1 = Draw, 2 = Win). Assumption A5 = CONFIRMED as the L/D/W permutation.
- **Confirmation:** at the start position (equal ELO), softmax gives W (idx 2) = 0.507 > L (idx 0) = 0.467 — a slight edge to the side to move (White), which is correct; the opposite order would wrongly favor Black. Independently, the idx-1 value is the one that rises with ELO (draw rate), which only makes sense as Draw.
- **Expected score / win-prob glue:** these are logits — softmax first, then e.g. `E = P(Win) + 0.5·P(Draw)`. The value head is side-to-move-relative (after any mirror), so map back to White/Black for display.

## (f) Batch dimension (Open Question 1)

- **CONFIRMED usable.** A single `session.run` with `tokens[B,64,12]`, `elo_self[B]`, `elo_oppo[B]` returned `logits_value` dims `[4,3]` and `logits_move` `[4,4352]` for B = 4.
- **Implication for the per-ELO chart:** run the whole 10-rung ELO ladder for a fixed position as **one batched inference** (repeat the same 64×12 board B times, vary `elo_self`/`elo_oppo`), rather than N sequential calls. Big latency win for the "moves by rating" curve.

---

## Runtime facts (for the Wave 2 worker)

- Load with `onnxruntime-web`, `ort.env.wasm.numThreads = 1` (no COOP/COEP — Phase 136 D-3, CI-guarded). WASM-CPU baseline vendored as `public/maia/ort-wasm-simd-threaded.{mjs,wasm}`.
- **WebGPU (D-09 "prefer when available"):** requires the JSEP runtime build (`ort-wasm-simd-threaded.jsep.{mjs,wasm}`), NOT the base pair vendored here. Vendor the `.jsep` variant in the worker plan if WebGPU is enabled, and cross-check WebGPU vs WASM numeric parity (RESEARCH Pitfall 4 — GAB/attention-policy op coverage on the WebGPU EP is unverified). This plan proves only the WASM/CPU path.
- Model + ort `.wasm` are excluded from the PWA precache (`vite.config.ts` `globIgnores` `**/*.onnx` + `**/*.wasm`); lazy-load the model only when the analysis surface opens.

## Provenance / license posture

- Model vendored **unmodified** (SHA-256 pinned) — AGPL-3.0 CSSLab artifact, data asset only. No CSSLab source code copied; the inspection script's encoder is original MIT code informed by the confirmed shapes. Attribution surface (LIC-02) is a later-plan deliverable.
