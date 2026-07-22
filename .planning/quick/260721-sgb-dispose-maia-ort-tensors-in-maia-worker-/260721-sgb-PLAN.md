---
task: Dispose Maia ORT tensors in maia-worker.js (SEED-113 app half)
quick_id: 260721-sgb
date: 2026-07-21
mode: quick (inline — single-file mechanical fix)
---

# Dispose Maia ORT tensors (wasm heap leak) — app-worker half

## Problem

`frontend/public/maia/maia-worker.js` `analyze()` allocates three input `ort.Tensor`s
(`tokens`, `elo_self`, `elo_oppo`) per call and receives output tensors from
`session.run()`. onnxruntime-web keeps those buffers in the **wasm linear heap** and only
frees them on `.dispose()`. Nothing disposes anything, so the heap grows per inference
until it throws `RuntimeError: memory access out of bounds`.

This is the app half of SEED-113. The harness half (`scripts/lib/calibration-providers.mjs`
`nodePolicy`) was fixed 2026-07-21 and is the reference implementation.

## Scope

Single file: `frontend/public/maia/maia-worker.js`, function `analyze()` (~L173-203).

## Task

1. Wrap `session.run(feeds)` and the downstream slicing in `try`/`finally`.
2. In `finally`, dispose every input feed and every output tensor with optional-chained
   `dispose?.()` (backend-safe: WebGPU tensors / older ORT builds may not expose it).
3. Guard the output loop — `outputs` is `undefined` if `session.run()` rejects.
4. Add a bug-fix comment at the site (CLAUDE.md rule) naming SEED-113 and the symptom.

Safety: the returned `rawPolicyByElo` / `wdlByElo` already use `TypedArray.slice()`, which
copies out of wasm memory, so disposing after they are built cannot invalidate the return
value. Disposing inputs after `run()` resolves is safe — they are already consumed.

## Verification

- `npm run lint` (frontend) — worker file is linted.
- `npm test -- --run` — no regression in maiaQueue / useMaiaEngine suites.
- Runtime check on both execution providers is HUMAN-UAT (WebGPU desktop + wasm fallback);
  the code path is provider-agnostic and `dispose?.()` is optional-chained, so no
  provider-specific risk is introduced.

## Out of scope

- Instrumenting `performance.memory` / wasm heap size across a long bot session (the seed
  lists it as "ideally"; it needs a live long-running session, not code).
- Retiring `bin/preset-supervisor.sh` (belongs to the already-shipped harness half).
