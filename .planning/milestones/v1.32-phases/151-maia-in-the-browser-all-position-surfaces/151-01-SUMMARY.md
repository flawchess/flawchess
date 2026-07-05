---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 01
subsystem: frontend / ml-inference
tags: [maia, onnx, onnxruntime-web, tensor-contract, pwa, vendoring]
status: complete
requires: []
provides:
  - "frontend/public/maia/maia3_simplified.onnx (pinned, sha256 405bf76c…)"
  - "frontend/public/maia/ort-wasm-simd-threaded.{mjs,wasm} (onnxruntime-web WASM runtime)"
  - "onnxruntime-web@1.27.0 dependency (Wave 2 worker consumes)"
  - "151-MAIA-CONTRACT.md (confirmed tensor I/O — consumed by Plans 04/05/06)"
  - "scripts/inspect_maia_onnx.mjs (contract inspection dev tool)"
affects:
  - frontend/vite.config.ts
  - frontend/knip.json
tech-stack:
  added: ["onnxruntime-web@1.27.0 (MIT)"]
  removed: ["onnxruntime-node (redundant — native addon SIGSEGVs on this platform)"]
  patterns: ["vendored runtime data asset (public/maia/, mirrors public/engine/ Stockfish precedent)"]
key-files:
  created:
    - frontend/public/maia/maia3_simplified.onnx
    - frontend/public/maia/ort-wasm-simd-threaded.mjs
    - frontend/public/maia/ort-wasm-simd-threaded.wasm
    - frontend/public/maia/README.md
    - scripts/inspect_maia_onnx.mjs
    - .planning/phases/151-maia-in-the-browser-all-position-surfaces/151-MAIA-CONTRACT.md
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/vite.config.ts
    - frontend/knip.json
decisions:
  - "Model sourced from https://maiachess.com/maia3/maia3_simplified.onnx (the reference client's own default asset path); committed unmodified, SHA-256 pinned"
  - "Inspection uses onnxruntime-web WASM (not onnxruntime-node) — same EP the browser worker ships; native onnxruntime-node addon SIGSEGVs on Linux/Node 24 here"
  - "Confirmed ELO ladder 1100–2000 ×100 for D-08 (behaviorally validated via ELO-monotonic draw rate)"
metrics:
  duration: ~16min (post-checkpoint execution)
  completed: 2026-07-05
  tasks: 3 (1 human-verify checkpoint + 2 auto)
  files: 10
---

# Phase 151 Plan 01: Maia-3 ONNX Contract De-risk Summary

Vendored the unmodified, version-pinned `maia3_simplified.onnx` (43.6 MB, SHA-256 `405bf76c…`) plus the onnxruntime-web WASM runtime under `frontend/public/maia/`, then confirmed its exact tensor contract hands-on against a real load + inference — unblocking every shape-dependent Wave 2+ plan.

## What shipped

- **Model + runtime vendored** (`public/maia/`), served verbatim (no bundler processing), excluded from the PWA precache. `onnxruntime-web@1.27.0` (MIT) installed and pinned exact.
- **`scripts/inspect_maia_onnx.mjs`** — loads the model via onnxruntime-web WASM (`numThreads=1`), prints declared I/O, runs a start-position inference. No unsupported-op error → MAIA-06 satisfied on the WASM/CPU path.
- **`151-MAIA-CONTRACT.md`** — the confirmed contract Wave 2 reads.

## Confirmed tensor contract (the load-bearing facts)

| Item | Confirmed value |
|------|-----------------|
| Inputs | `tokens[B,64,12]` float32; `elo_self[B]`, `elo_oppo[B]` **raw continuous float scalars** (A1 ✓) |
| Board encoding | 12 one-hot piece planes/square (W `PNBRQK`, B `pnbrqk`), square = `row*8+file`, **n=0 history**, mirror on black-to-move |
| Policy output | `logits_move` **flat `[B,4352]`** — NOT 64×64, NOT 4096; move key = `from+to+promotion` → 4352-vocab index |
| WDL output | `logits_value` `[B,3]` order **`[Loss, Draw, Win]`** (A5 permutation ✓) |
| ELO range (D-08) | **1100–2000 ×100** (10 rungs); draw-rate rose monotonically 0.023→0.042 across the sweep |
| Batch dim (OQ1) | **Usable** — full ELO ladder is one `session.run` (returned `[4,3]`/`[4,4352]` for B=4) |

WDL order proven two ways: at the start position W(idx2)=0.507 > L(idx0)=0.467 (correct slight edge to mover; the opposite order would wrongly favor Black), and idx-1 is the value that rises with ELO (draw rate).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] onnxruntime-node native addon SIGSEGVs → switched inspection to onnxruntime-web WASM**
- **Found during:** Task 3.
- **Issue:** `onnxruntime-node@1.27.0`'s native addon segfaults (SIGSEGV, exit 139) on `InferenceSession.create` on this Linux / Node 24 box, both via the script and a minimal repro. The plan specified onnxruntime-node for the Node inspection path.
- **Fix:** Rewrote `scripts/inspect_maia_onnx.mjs` to load the model with **onnxruntime-web's WASM execution provider** under Node (`numThreads=1`). This is a strictly better MAIA-06 proof — it exercises the exact runtime the browser worker will ship, not a native addon that never runs in production. Removed the now-redundant, unusable `onnxruntime-node` devDependency (also avoids an unused-devDependency knip failure and trims supply-chain surface). The human-approved onnxruntime-web install is unaffected.
- **Files:** scripts/inspect_maia_onnx.mjs, frontend/package.json, frontend/package-lock.json
- **Commit:** 91689787

**2. [Rule 3 - Blocking] knip flagged onnxruntime-web as an unused dependency**
- **Found during:** Task 3 (tree-hygiene check after install).
- **Issue:** `npm run knip` (CI gate per CLAUDE.md) exited 1 because `onnxruntime-web` is installed in Wave 1 (this plan) but its consumer is the Wave 2 worker — knip sees no importer in `frontend/src` yet.
- **Fix:** Added `onnxruntime-web` to `knip.json` `ignoreDependencies`. It is an intentional install-ahead-of-consumer, exactly as the phase sequences (Wave 1 vendors runtime, Wave 2 imports it). The Wave 2 worker plan should drop this ignore once it adds the import.
- **Files:** frontend/knip.json
- **Commit:** 91689787

## Checkpoint (Task 1) — resolved

`checkpoint:human-verify gate="blocking-human"` package-legitimacy gate for `onnxruntime-web`/`onnxruntime-node` ([SUS] false-positive, Phase 136 stockfish pattern). Human verified provenance (Microsoft, MIT, no postinstall, v1.27.0) and replied **"approved"** before any `npm install` ran. Documented as normal flow, not a deviation.

## Verification

- `npm run build` green; `dist/sw.js` free of `.onnx` / `ort-wasm*.wasm` precache entries (automated guard PASS).
- `node scripts/inspect_maia_onnx.mjs` runs to completion, no unsupported-op error.
- `151-MAIA-CONTRACT.md` records concrete answers for all six items (a)–(f).
- `npm run knip` PASS, `npm run lint` PASS, no COOP/COEP headers added (CI guard intact).

## Notes for Wave 2

- **WebGPU (D-09):** needs the JSEP runtime build (`ort-wasm-simd-threaded.jsep.{mjs,wasm}`), NOT the base WASM pair vendored here — vendor it in the worker plan if WebGPU is enabled, and cross-check WebGPU↔WASM numeric parity (RESEARCH Pitfall 4).
- **Move vocabulary:** Wave 2 needs its OWN 4352-entry `from+to+promotion`→index table (reconstruct — do not copy CSSLab's AGPL JS).
- **Mirror un-mapping:** because the board mirrors on black-to-move, returned move indices + the value head are in the mover's frame — un-mirror for display.

## Self-Check: PASSED
All 6 created files exist on disk; both task commits (4e45e2a4, 91689787) present in git log. Model is git-tracked (not LFS, mirrors the committed Stockfish .wasm precedent).
