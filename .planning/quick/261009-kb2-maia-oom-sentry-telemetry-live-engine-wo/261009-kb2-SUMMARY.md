---
quick_id: 261009-kb2
status: complete
seed: SEED-195
commit: 72d164b08
---

# Quick 261009-kb2 summary: Maia OOM Sentry telemetry

SEED-195 step 1. This is telemetry only; engine behavior is unchanged.

## What changed

- `frontend/src/lib/engine/liveEngineWorkers.ts` (new): counts Stockfish Workers per role
  (`pool`, `single`, `grading`, `train-grading`). `trackStockfishWorker()` increments the count and
  wraps the instance's `terminate()` so the count drops exactly once.
- `createStockfishWorker(sharedUrl, role)`: the role is now required and every real Worker is
  tracked. All four callers pass their role.
- `maiaWorkerHost.ts`: records each worker's `MaiaSpawnPath` in `constructWorker` (`webgpu`,
  `auto-wasm`, `webgpu-failed-wasm`, `ios-wasm`) and passes it to the failure capture.
- `captureMaiaWorkerError`: adds the tag `maia_spawn_path` (defaults to `unknown`) and the context
  `engine_workers`. The error message and classification are unchanged, so Sentry grouping is
  unaffected.

## Verification

- New `liveEngineWorkers.test.ts` (4 cases), 2 new `maiaWorkerErrors` cases, and 1 new
  `maiaWorkerHost` case that checks both the `auto-wasm` and the `webgpu-failed-wasm` OOM paths.
- Mutation check: mislabeling the respawn path as `auto-wasm` failed the host test. Reverted.
- Frontend gate: lint, build (`tsc -b`), 5440/5440 tests, knip all clean.

## Follow-up

The data only arrives after the next deploy. Step 2 (pool-shrink retry) waits on the
`engine_workers` counts from real Mac Safari OOM events. See the SEED-195 Status section.
