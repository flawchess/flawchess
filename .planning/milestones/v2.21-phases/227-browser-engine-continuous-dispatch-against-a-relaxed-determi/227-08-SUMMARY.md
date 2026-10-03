---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 08
subsystem: testing
tags: [engine, tripwire, determinism, webgpu, bench, orchestrator]

requires:
  - phase: 227-01
    provides: "worker-thread Maia (the cause of the warm-hash tripwire drift), abort-aware pool"
  - phase: 227-04
    provides: "MQ gate --dispatch-mode/--repeats/--maia-fifo/--hash"
  - phase: 227-06
    provides: "dev bench page /dev/engine-bench"
provides:
  - "D-18 tripwire evidence: clear-hash worker vs main-thread parity PASS (0/60 x 2 stop modes)"
  - "Report-only warm-hash similarity vs 226 a21s"
  - "--maia-main-thread parity flag on scripts/engine-move-quality.mjs (stamped maia_thread)"
  - "Local wasm round leg and owner WebGPU round leg (engine-bench-227/v1)"
affects: [227-09, 227-11, 227-12]

plan_head_before: d07a6d0df582a596f65c35992a5a5165b2d501f8
plan_head_after: 16d70285e

actuals:
  tasks: 3
  commits: 4

key-files:
  created:
    - reports/data/continuous-dispatch-227/tripwire/mq-off/ (warm hash, report-only vs a21s)
    - reports/data/continuous-dispatch-227/tripwire/mq-on/ (warm hash, report-only vs a21s)
    - reports/data/continuous-dispatch-227/tripwire/parity-clear/{worker,main}/mq-{off,on}/ (judged parity)
    - reports/data/continuous-dispatch-227/webgpu/local-wasm-round-leg.json
    - reports/data/continuous-dispatch-227/webgpu/round-leg.json
    - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-08-TRIPWIRE-DEBUG.md
  modified:
    - scripts/engine-move-quality.mjs

key-decisions:
  - "Owner (2026-10-02): bit-identical round-mode results are not required with concurrent (off-thread) Maia inference; very similar is good enough"
  - "D-18 is judged as exact parity at --hash clear (worker vs --maia-main-thread), where timing cannot reach content; warm-hash vs a21s is report-only"
  - "Tooling commit T = cef88fd87 (adds --maia-main-thread; no other code change)"

requirements-completed: []
---

# 227-08 Summary: round-mode tripwire, local wasm leg, owner WebGPU leg

## Task 1: tooling tripwire (D-18)

**Fast checks at d07a6d0df (all exit codes as required):** stockfish-pool.check 0, `--root-split` 0,
maia-worker-thread.check 0, dispatch-mode.check 0, `--mode continuous` 3, calibration-ledger-schema.check 0,
calibration-determinism.check 0 (74 s), interleave `--dry-run` 0.

**First tripwire (as planned, `--maia-fifo --hash warm`) FAILED vs 226 a21s:** stop-off 2/60 rows (cBFTV, Mhfvi
picks), stop-on 5/60 (cBFTV pick; GZOoY, W7T4K, mWhzd, zskVk node counts). Run time 331 s (off), 110 s (on).

**Debug** (full record in `227-08-TRIPWIRE-DEBUG.md`): the pre-phase tooling still reproduces a21s exactly; Maia on
the main thread reproduces a21s exactly; signal forwarding and `--maia-fifo` are not causes; at `--hash clear` the
worker and main-thread sessions are identical and repeatable. Cause: off-thread Maia (227-01, D-18) lets grades
complete while Maia infers, so pool engine assignment and each engine's warm-hash history depend on timing. The
browser has the same property. Not a tooling content bug.

**Resolution (owner-approved: very similar is good enough):**
- Judged: `--hash clear`, worker vs `--maia-main-thread`, 60 rows, both stop modes: **TRIPWIRE PASS, 0 diffs**
  (twin `tripwire --mq-dir .../parity-clear/worker --baseline-dir .../parity-clear/main`). T = cef88fd87.
- Report-only, warm hash vs a21s:

| Mode | picks changed | pass | mean es_bot | mean nodes |
|---|---|---|---|---|
| stop-off a21s / 227 | 0 / 2 of 60 | 49 / 48 | 0.8079 / 0.7995 | 50 / 50 |
| stop-on a21s / 227 | 0 / 1 of 60 | 50 / 49 | 0.8196 / 0.8101 | 9.28 / 10.07 |

## Task 2: local wasm round leg (tool validation)

Chrome 154 / Linux, 16 threads, pool 4, no WebGPU adapter with shader-f16 (WebGPU rows `available: false`).
Secure context and cross-origin isolation true, no refusal banner, no page console errors. Interleaved button refused
with "continuous dispatch is not implemented in this build" and left the JSON unchanged.

## Task 3: owner WebGPU round leg

Edge 154 / Windows, 32 threads, pool 4, shader-f16 true. Served over the tailnet (`tailscale serve` to this box's
Vite dev server; the page runs entirely in the owner's browser).

| Machine | Backend | idle median / p90 (ms) | SF-busy median / p90 (ms) |
|---|---|---|---|
| Windows (owner) | webgpu | 17.8 / 28.2 | 23.2 / 25.9 |
| Windows (owner) | wasm (4 threads) | 46.2 / 46.6 | 32.0 / 40.6 |
| Linux (this box) | wasm (4 threads) | 35.7 / 37.7 | 39.2 / 43.4 |

P(webgpu) is about 18-23 ms, close to Phase 198's X-2 prior (P around 15 ms), slightly higher.

Round-mode bot-move wall, median over 3 rounds (ms):

| Position | Linux wasm | Windows webgpu |
|---|---|---|
| italian | 1733 | 1361 |
| middlegame | 6363 | 4882 |
| sharp | 2664 | 1958 |
| endgame | 1066 | 716 |
| C50 | 1457 | 2114 |
| C60 | 2644 | 2114 |

## Deviations

1. **Tripwire criterion changed (owner decision).** The plan required warm-hash identity with 226 a21s; that is
   unreachable with off-thread Maia (timing-dependent warm-hash history). Judged parity now runs at `--hash clear`
   against the new `--maia-main-thread` reference. Committed as `fix(227-08)` (cef88fd87).
2. **Owner leg served over Tailscale** instead of a local checkout or SSH tunnel.

## Required follow-up for 227-09 (accept rule)

`_check_round_determinism` in `scripts/engine_dispatch_227_verdict.py` raises INVALID on ANY round-repeat
disagreement ("226: 0 of 60"). Under warm hash with worker Maia, round repeats will disagree on some positions
(227-04 measured cBFTV flipping in about 8-11% of repeats), so the judged MQ cells would always be INVALID.
227-09 must replace that rule (report the round-repeat disagreement rate instead of failing, or judge MQ at
`--hash clear`) and update the twin's tripwire docstring ("bit-identical to A21S") to point at the clear-hash parity
check. No continuous-mode data exists.

## Self-Check: PASSED
- Twin prints TRIPWIRE PASS on the committed parity data; tripwire TSVs are in git.
- LOCAL-LEG OK and OWNER-LEG OK validators pass; both JSONs are committed.
