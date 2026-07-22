---
title: Dispose Maia ORT tensors to fix onnxruntime-web wasm heap leak (nodePolicy + maia-worker.js)
trigger_condition: Anytime — small, self-contained engine-infra bug fix. The harness half is being applied now (2026-07-21) alongside this seed; the app-worker half is the remaining scoped work this seed tracks. Prioritize the worker half if bot-play memory issues are ever reported on wasm-only / low-memory mobile.
planted_date: 2026-07-21
source: Phase 180 bot-curves sweep (2026-07-19/21). Both blend>0 presets crashed every ~8.5-9h with onnxruntime-web "memory access out of bounds" in Maia inference; root-caused to undisposed ort.Tensors. See memory project_calibration_harness_wasm_oob_crash.
---

# SEED-113: Dispose Maia ORT tensors (wasm heap leak)

Every Maia policy inference allocates input `ort.Tensor`s (`tokens`, `elo_self`, `elo_oppo`) and
receives output tensors from `session.run()`. onnxruntime-web keeps those buffers in the **wasm
linear heap** and requires `.dispose()` to free them. Neither inference path disposes anything, so
the heap grows a few buffers per call until it hits its bound and throws
`RuntimeError: memory access out of bounds` mid-run. Confirmed onnxruntime-web 1.27.0 has
`Tensor.prototype.dispose` (a real function), so disposal actually frees the buffer.

## Two call sites (same bug, separate code)

| Site | File | Status |
|---|---|---|
| Calibration harness | `scripts/lib/calibration-providers.mjs` `nodePolicy` (~L116-135) | **FIXED 2026-07-21** (this seed's harness half) — retires `bin/preset-supervisor.sh` for future long sweeps |
| Production app | `frontend/public/maia/maia-worker.js` (tensors L184-186, `session.run` L189) | **OPEN** — the remaining work this seed tracks |

## Fix

Wrap the `session.run()` in try/finally; after copying `logits_move.data` out (`.slice()` = defensive
copy), dispose the input feeds and every output tensor: `for (const t of Object.values(feeds)) t.dispose?.()`
and the same over `Object.values(result)`. Optional-chain `dispose?.()` to stay backend-safe (WebGPU
tensors / older versions). Disposing inputs after `run()` resolves is safe — they're already consumed.

## Production risk (why the app half is not urgent)

Real exposure sits far below the crash threshold (~270k policy inferences on the Node wasm heap):
one Deep game ≈ 1.5-3k inferences, Human ≈ 30-60, session is per-tab and resets on reload, and the
app tries **WebGPU first** (`maia-worker.js:142`), falling to wasm only on Safari/old/mobile. A user
would need ~100+ Deep games in one uninterrupted wasm-only tab to approach it. Residual real risk is a
marathon session on a memory-constrained mobile — low probability, cheap fix, benefits exactly those
users.

## Verification for the app half

Apply the disposal, then confirm no regression on both execution providers (WebGPU desktop + wasm
fallback), and ideally instrument `performance.memory` / wasm heap size across a long bot session to
confirm it stays flat. The harness half is verified by running a multi-hour blend>0 sweep and
confirming zero wasm-OOB crashes (previously ~1 per 8.5-9h) — which also lets `preset-supervisor.sh`
be retired.
