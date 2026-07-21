---
quick_id: 260721-sgb
slug: dispose-maia-ort-tensors-in-maia-worker-
date: 2026-07-21
status: complete
---

# Quick Task 260721-sgb: Dispose Maia ORT tensors in maia-worker.js (SEED-113 app half) — SUMMARY

## What changed

`frontend/public/maia/maia-worker.js`, `analyze()` (~L186-217):

1. Wrapped `session.run(feeds)` and the downstream slicing in `try`/`finally`, with
   `outputs` hoisted to a `let` outside the `try` so the `finally` block can see it.

2. In `finally`, disposed every input feed (`tokens`, `elo_self`, `elo_oppo`) and every
   output tensor via optional-chained `t.dispose?.()`. Optional-chaining keeps this safe
   across ORT backends/versions that don't expose `dispose()` (WebGPU tensors, older
   builds).

3. Guarded the output loop with `if (outputs)` — `outputs` stays `undefined` when
   `session.run()` rejects, so the rejection path disposes inputs only and doesn't mask
   the original error with a TypeError.

4. Added a bug-fix comment at the disposal site (CLAUDE.md rule) naming SEED-113, the
   wasm-linear-heap mechanism, and the observed symptom in the harness half. Added a
   second short comment above the `.slice()` calls recording why disposing in `finally`
   cannot invalidate the returned buffers (`TypedArray.slice()` copies out of wasm
   memory before the `finally` runs).

This is the app half of SEED-113. The harness half
(`scripts/lib/calibration-providers.mjs` `nodePolicy`) was fixed earlier the same day and
is the reference implementation.

## Verification

- `npm run lint` → 0 errors (3 warnings, all in generated `coverage/`, pre-existing).
- `npm test -- --run` → 172 files, 2313 tests pass (no regression in `maiaQueue` /
  `useMaiaEngine` suites).
- `npx tsc -b` / `npm run knip` not applicable: the file lives in `frontend/public/` and
  is shipped as a raw asset, so it is outside the TS project graph and knip's module
  graph. ESLint does lint it (`eslint .`), which is the gate that applies.
- Runtime confirmation on both execution providers (WebGPU desktop + wasm fallback) is
  HUMAN-UAT and not performed here. Risk is low: the code path is provider-agnostic and
  every `dispose()` call is optional-chained.

## Flagged: no regression test

Reverting this fix would not fail any test — the leak is a wasm-heap growth property of a
long-running session, not an observable output. A faithful guard would need a fake `ort`
whose tensors count `dispose()` calls, plus a worker-level harness; `maia-worker.js` is a
plain public asset with no test seam today (it is loaded by URL, not imported). Not worth
building for a 5-line `finally`. The equivalent harness-half fix is likewise unguarded.
