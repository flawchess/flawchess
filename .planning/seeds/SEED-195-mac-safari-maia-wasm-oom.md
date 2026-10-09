---
id: SEED-195
status: dormant
planted: 2026-10-09
planted_during: ad-hoc Sentry triage of unresolved Maia issues (Phase 237 in flight)
trigger_when: a few Mac Safari `maia_failure:oom` events carrying the new `engine_workers` context have arrived (step 1 telemetry shipped), or any change to the Stockfish worker pool sizing
scope: small-medium (frontend only; maiaWorkerHost + workerPoolState + Sentry context)
---

# SEED-195: Maia wasm OOM on Mac Safari

## Why This Matters

Mac Safari users can't load Maia at all. Every event is a pre-ready failure at
`InferenceSession.create` with the same raw message:

```
no available backend found. ERR: [wasm] RangeError: Out of memory
```

The user lands on the EngineReadyGate "free device memory" screen and Maia never starts.

| Issue | Status | Mac Safari events | Versions |
|---|---|---|---|
| FLAWCHESS-B2 | resolved (but kept firing) | 3 (09-26, 09-27, 10-03) | Safari 26.3, 26.5.2, 26.6.1 |
| FLAWCHESS-CP | unresolved | 1 (10-07) | Safari 26.6.2 |

Four users in about two weeks, from different locations. B2 was resolved yet recurred, and Sentry
regrouped it as CP because the stack differs. All four report `hardwareConcurrency: 8`. Safari
reports a fixed value, so this tells us nothing about the device. Sources were `/analysis` and
`/bots`.

## Hypothesis (unproven)

It's the same WebKit per-process wasm memory reservation budget we hit on iOS
(see the iOS reservation-budget memory and SEED-158), with a larger ceiling on macOS. The
`maximum: 16384` (1 GB) cap in both vendored `public/maia/ort-wasm-simd-threaded*.mjs` files
already ships to Macs, so the cap alone doesn't cover it.

An 8-core Mac on /analysis runs `computePoolSize()` = 4 Stockfish pool workers, plus the grading
worker, plus Maia. Each holds its own wasm Memory, and Maia usually spawns last. Stockfish's hash is
only 8 MB per worker (`WORKER_HASH_MB`), so if the theory holds the problem is the number of wasm
memory reservations, not the bytes they hold.

The events can't confirm it: they don't record how many engine workers were alive, or whether Maia
went straight to wasm or got there via the `webgpu-unavailable` → `respawnPinnedToWasm` respawn.

## Status (2026-10-09)

- **Step 1 (telemetry) done:** quick task 261009-kb2, commit `72d164b08` on `main`. It is only
  live after the next deploy. Every Maia failure capture now carries:
  - tag `maia_spawn_path`: `webgpu` | `auto-wasm` (no adapter) | `webgpu-failed-wasm` (pinned
    after a WebGPU failure) | `ios-wasm` | `unknown`
  - context `engine_workers`: `stockfishPool`, `stockfishSingle`, `stockfishGrading`,
    `stockfishTrainGrading`, `stockfishTotal` (Stockfish workers constructed and not yet
    terminated, counted in `frontend/src/lib/engine/liveEngineWorkers.ts`)
- **Step 2 (mitigation) is waiting on that data.** Read the next Mac Safari OOM events with
  `maia_failure:oom os.name:"Mac OS X"`. A high `stockfishTotal` (4+) on every event supports
  the budget theory and the pool-shrink retry. Low or varying counts point somewhere else
  (per-tab memory, other tabs), and the pool shrink would be the wrong fix.
- The owner can test the normal load path on an office Mac (around 2026-10-12). That checks for
  regressions only; the OOM is rare enough that it probably won't reproduce there.

## Proposed Direction

1. **Telemetry first (one release, DONE, see Status):** on a Maia `oom`, add to the Sentry context the live engine
   worker count (Stockfish pool slots, grading worker, single engine) and the spawn path
   (`auto-wasm` / `webgpu→wasm respawn` / `ios`). Fold B2 into CP.
2. **Mitigation:** on a pre-ready wasm OOM, shrink the Stockfish pool to `MOBILE_POOL_SIZE` (2),
   terminating idle slots, and retry the Maia spawn once. Guard it so it can't loop, like the
   WR-01 single-thread retry. The simpler alternative is to always size the pool at 2 on desktop
   WebKit. The cost is slower Stockfish analysis for Safari users.
3. Don't bother with a single-thread retry. ORT's glue reserves the shared memory even at 1 thread.

## Validation

This can't be reproduced on the Linux dev box: there's no Safari, and WebKitGTK's wasm memory
behavior differs. It needs a real Mac running Safari 26.x on /analysis with Stockfish and the
FlawChess Engine on. Watch for new `maia_failure:oom` events from `os.name:"Mac OS X"` after the
release.

## Not In Scope

FLAWCHESS-9H ("worker load failure") was triaged in the same session and closed as expected
browser behavior. It fires as a bare Event (no ErrorEvent) and often hits every Stockfish worker at
the same instant, so the browser is refusing workers page-wide (memory pressure, or a tab in the
background). The next request or Retry respawns the worker.
