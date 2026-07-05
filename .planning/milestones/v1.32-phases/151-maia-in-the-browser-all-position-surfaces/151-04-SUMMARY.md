---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 04
subsystem: frontend / ml-inference
tags: [maia, onnxruntime-web, web-worker, react-hook, webgpu, wasm]

requires:
  - phase: 151-01
    provides: "151-MAIA-CONTRACT.md confirmed tensor I/O (tokens[B,64,12], elo_self/elo_oppo raw scalars, logits_move flat [B,4352], logits_value [B,3] order [L,D,W], batch dim usable, ELO ladder 1100-2000 step 100), vendored maia3_simplified.onnx + baseline WASM runtime"
provides:
  - "frontend/src/lib/maiaEncoding.ts — encodeBoard, squareIndex, maskAndSoftmax, expectedScore, softmaxWdl, eloToInput, MAIA_ELO_LADDER, POLICY_VOCAB_SIZE (original MIT glue, MAIA-03)"
  - "frontend/public/maia/maia-worker.js — classic Web Worker running onnxruntime-web with WebGPU-preferred/single-thread-WASM-fallback EP selection (MAIA-02, MAIA-06)"
  - "frontend/src/hooks/useMaiaEngine.ts — UseMaiaEngineState hook, structural sibling of useStockfishEngine (MAIA-04/05, SURF-05)"
  - "Vendored ort.wasm.min.js, ort.webgpu.min.js, ort-wasm-simd-threaded.asyncify.{mjs,wasm} onnxruntime-web runtime bundles"
affects:
  - 151-05 (Maia eval bar + ELO selector — consumes wdl/expectedScoreAtSelectedElo)
  - 151-06 (Moves-by-Rating chart + VALID-01 real-ONNX cross-check — consumes perElo)

tech-stack:
  added: []
  patterns:
    - "Classic (non-module) Worker replicating pure encoding functions from the TS glue module, since a static public/ JS file cannot import a TS ES module (mirrors the Stockfish public/engine/ precedent)"
    - "Worker returns RAW policy/WDL logits only; masking/softmax/expectedScore stay single-sourced in maiaEncoding.ts, applied by the hook"
    - "Full ELO-ladder curve computed in ONE batched session.run per FEN; selectedElo only picks the nearest already-computed rung (no re-inference on ELO-selector change)"

key-files:
  created:
    - frontend/src/lib/maiaEncoding.ts
    - frontend/src/lib/__tests__/maiaEncoding.test.ts
    - frontend/public/maia/maia-worker.js
    - frontend/public/maia/ort.wasm.min.js
    - frontend/public/maia/ort.webgpu.min.js
    - frontend/public/maia/ort-wasm-simd-threaded.asyncify.mjs
    - frontend/public/maia/ort-wasm-simd-threaded.asyncify.wasm
    - frontend/src/hooks/useMaiaEngine.ts
    - frontend/src/hooks/__tests__/useMaiaEngine.test.ts
  modified:
    - frontend/public/maia/README.md

decisions:
  - "Reconstructed the confirmed 4352-entry policy vocab as base(from*64+to, 4096, queen promotion implicit) + underpromotion lane keyed by (to, promo-piece) x4 lanes (256) = 4352 exactly; this is a best-effort deterministic scheme, NOT verified against CSSLab's literal index order — flagged as an open risk to close in Plan 06's VALID-01 real-ONNX cross-check"
  - "Corrected 151-MAIA-CONTRACT.md's WebGPU runtime-file assumption: the vendored v1.27.0 ort.webgpu.min.js bundle actually requires the Asyncify wasm pair (ort-wasm-simd-threaded.asyncify.{mjs,wasm}), not the JSEP pair the contract's 'Runtime facts' section named — verified by grepping the real bundle, not guessed"
  - "Worker uses TWO separate ort API bundles (ort.wasm.min.js for the WASM-only fallback, ort.webgpu.min.js for the WebGPU-preferred path) instead of one universal bundle, so WASM-only/mobile users only ever download the smaller ~13.5MB baseline wasm, not the ~24MB webgpu-capable asyncify wasm"
  - "elo_self == elo_oppo == ladder rung for every batched inference (symmetric-strength sweep), matching the exact methodology 151-01 used to validate the ELO ladder behaviorally"
  - "wdl / expectedScoreAtSelectedElo both derive from the SAME ladder rung nearest selectedElo (not independent sources) — consistent with expectedScore being literally derived from wdl"
  - "Kept onnxruntime-web in knip.json's ignoreDependencies (did NOT drop it as the dependency-context note anticipated): knip's project glob is src/**/*.{ts,tsx} and the worker consumes onnxruntime-web via importScripts() in a plain public/ JS file, which knip cannot see regardless of whether the import is 'real' — this differs from the Stockfish precedent only because that package has a TS-visible integration-test import; Plan 04 has no equivalent (real-ONNX integration is deferred to Plan 06 VALID-01)"

requirements-completed: [MAIA-02, MAIA-03, MAIA-04, MAIA-05, MAIA-06, SURF-05]

coverage:
  - id: D1
    description: "maiaEncoding.ts: board->tensor encoding (mirrors black-to-move), legal-move masking + numerically-stable softmax, expectedScore, softmaxWdl, MAIA_ELO_LADDER"
    requirement: "MAIA-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/maiaEncoding.test.ts (15 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "maia-worker.js: classic Worker, WebGPU feature-detect + try/catch fallback to single-thread WASM, numThreads never >1, batched ELO-ladder inference, returns raw policy/WDL + backend"
    requirement: "MAIA-02, MAIA-06"
    verification:
      - kind: unit
        ref: "node -e regex gate (numThreads=1 forced, never >1, webgpu+requestAdapter present) — see plan Task 2 <verify>"
        status: pass
      - kind: other
        ref: "npm run build (dist/sw.js precache manifest contains no .onnx/.wasm entries)"
        status: pass
    human_judgment: true
    rationale: "Real WebGPU/WASM numeric parity and no-unsupported-op confirmation on an actual GPU requires a live browser session — deferred to Plan 06 VALID-01, documented not silently skipped."
  - id: D3
    description: "useMaiaEngine.ts hook: mount-only Worker lifecycle, adaptive debounce, stale-result guard, tab-hide pause, ephemeral FIFO cache, returns {perElo, expectedScoreAtSelectedElo, wdl, isReady, isAnalyzing}"
    requirement: "MAIA-04, MAIA-05, SURF-05"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEngine.test.ts (10 tests: idle/enabled, debounce, coalesce, stale discard, cache hit, tab-hide pause, unmount, nearest-ELO WDL)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-07-05
status: complete
---

# Phase 151 Plan 04: Maia ML Core (encoding + worker + hook) Summary

**Client-side Maia-3 ONNX inference core: board->tensor MIT glue, a WebGPU/WASM-fallback Web Worker, and a `useMaiaEngine` hook producing the full per-ELO move curve + WDL live per FEN, with zero server round-trip.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-05
- **Tasks:** 3 (all auto)
- **Files modified:** 10 (2 new source modules + 2 test files + 1 worker + 4 vendored runtime bundles + 1 README update)

## Accomplishments

- `maiaEncoding.ts`: original MIT board-encoding/masking/softmax glue against the CONFIRMED `151-MAIA-CONTRACT.md` tensor contract (flat 4352 policy vocab, `[Loss,Draw,Win]` WDL order, 1100-2000 ELO ladder, black-to-move mirroring) — 15 passing unit tests, zero real-ONNX dependency needed for correctness of the pure math.
- `maia-worker.js`: a classic Web Worker mirroring the Stockfish `public/engine/` precedent, feature-detecting WebGPU and falling back to forced single-thread WASM on any failure, batching the whole ELO ladder into one `session.run`, returning raw policy/WDL logits + the active backend.
- `useMaiaEngine.ts`: a structural sibling of `useStockfishEngine` — same lifecycle shape (mount-only Worker effect, adaptive debounce, stale-result guard, tab-hide pause), new request/response protocol, ephemeral FIFO cache, deriving `wdl`/`expectedScoreAtSelectedElo` from the ladder rung nearest the caller's `selectedElo` without re-inference.

## Task Commits

1. **Task 1: maiaEncoding.ts** - `fa336795` (feat)
2. **Task 2: maia-worker.js** - `42e847ca` (feat)
3. **Task 3: useMaiaEngine.ts + softmaxWdl** - `79155d38` (feat)

_No plan-metadata-only commit yet — this SUMMARY + STATE/ROADMAP updates are the final commit for this plan._

## Files Created/Modified

- `frontend/src/lib/maiaEncoding.ts` - board->tensor, legal-move mask+softmax, expectedScore, softmaxWdl, eloToInput, MAIA_ELO_LADDER
- `frontend/src/lib/__tests__/maiaEncoding.test.ts` - 15 unit tests
- `frontend/public/maia/maia-worker.js` - classic Worker, EP selection, batched ELO-ladder inference
- `frontend/public/maia/ort.wasm.min.js`, `ort.webgpu.min.js`, `ort-wasm-simd-threaded.asyncify.{mjs,wasm}` - vendored onnxruntime-web runtime bundles (v1.27.0, MIT)
- `frontend/public/maia/README.md` - documents both runtime paths + the JSEP->Asyncify filename correction
- `frontend/src/hooks/useMaiaEngine.ts` - the hook; `UseMaiaEngineState`/`MoveCurvePoint` types
- `frontend/src/hooks/__tests__/useMaiaEngine.test.ts` - 10 mock-worker tests

## Final `UseMaiaEngineState` shape (for Plans 05/06)

```typescript
interface MoveCurvePoint {
  elo: number;
  moveProbabilities: Record<string, number>; // SAN -> probability, sums to 1.0
}

interface UseMaiaEngineState {
  perElo: MoveCurvePoint[];               // one entry per MAIA_ELO_LADDER rung (10 rungs, 1100..2000 step 100); [] until first result
  expectedScoreAtSelectedElo: number | null; // W + 0.5*D at the ladder rung nearest `selectedElo`; null until ready
  wdl: WdlVector | null;                  // { win, draw, loss } at that SAME nearest rung — feeds Phase 152
  isReady: boolean;                       // Worker's ONNX session created
  isAnalyzing: boolean;                   // non-cached inference in flight for the current FEN
}

// Hook signature:
useMaiaEngine({ fen, enabled, selectedElo }: {
  fen: string | null;
  enabled: boolean;
  selectedElo: number;
}): UseMaiaEngineState
```

`wdl` and `expectedScoreAtSelectedElo` are always derived from the SAME ELO rung (nearest to `selectedElo`) — changing `selectedElo` alone re-derives both via `useMemo`, no new worker call, since the full 10-rung curve is already cached per FEN.

## Decisions Made

- Reconstructed the confirmed 4352-entry policy vocab as base `from*64+to` (4096, queen promotion implicit) + an underpromotion lane keyed by `(to, promo-piece)` x4 lanes (256) = 4352 exactly. This is a deterministic, internally-consistent, **best-effort** scheme — NOT verified against CSSLab's literal `all_moves_maia3.json` index order (which we deliberately did not copy, per MAIA-03/AGPL hygiene). See "Known Limitations" below.
- Corrected `151-MAIA-CONTRACT.md`'s WebGPU runtime-file assumption: the vendored v1.27.0 `ort.webgpu.min.js` bundle requires the **Asyncify** wasm pair, not the JSEP pair the contract's "Runtime facts" section named (written before this worker existed). Verified by grepping the actual bundle source for the literal filename it requests — documented in `public/maia/README.md`.
- Used two separate onnxruntime-web API bundles (`ort.wasm.min.js` for the WASM-only path, `ort.webgpu.min.js` for the WebGPU-preferred path) so mobile/WASM-only users only ever download the smaller ~13.5MB baseline WASM binary, not the ~24MB WebGPU-capable Asyncify binary.
- `elo_self == elo_oppo == ladder rung` for every batched inference call (symmetric-strength sweep), matching 151-01's own ELO-ladder validation methodology exactly.
- Worker returns RAW policy/WDL logits only (no masking/softmax in the worker) so `maskAndSoftmax`/`expectedScore`/`softmaxWdl` stay single-sourced in `maiaEncoding.ts`, applied by the hook — avoids a second, divergence-prone implementation of that math inside the plain-JS worker.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `softmaxWdl` to maiaEncoding.ts**
- **Found during:** Task 3 (useMaiaEngine hook)
- **Issue:** The worker returns raw `[Loss,Draw,Win]` WDL logits (per CONTRACT §e); `expectedScore()` expects an already-normalized `{win,draw,loss}` fraction. Nothing in Task 1's named exports converted between them, so the hook could not correctly consume the confirmed WDL contract.
- **Fix:** Added `softmaxWdl(logits): WdlVector` to `maiaEncoding.ts` — numerically-stable softmax over the confirmed `[L,D,W]` index order, mirroring `maskAndSoftmax`'s technique. Added 2 unit tests.
- **Files modified:** frontend/src/lib/maiaEncoding.ts, frontend/src/lib/__tests__/maiaEncoding.test.ts
- **Committed in:** 79155d38 (Task 3 commit)

**2. [Rule 1 - Bug] Corrected the WebGPU runtime-file pair (JSEP -> Asyncify)**
- **Found during:** Task 2 (maia-worker.js)
- **Issue:** `151-MAIA-CONTRACT.md`'s "Runtime facts" section (written speculatively before this worker existed) said WebGPU requires the JSEP build (`ort-wasm-simd-threaded.jsep.{mjs,wasm}`). Vendoring that pair and wiring `ort.webgpu.min.js` against it would have silently failed at runtime (or fetched a file the bundle never requests).
- **Fix:** Grepped the real vendored v1.27.0 `ort.webgpu.min.js` bundle source for the literal wasm/mjs filename string it requests — confirmed it hardcodes `ort-wasm-simd-threaded.asyncify.mjs`, not `.jsep.mjs`. Vendored the Asyncify pair instead; documented the correction in `public/maia/README.md` so the discrepancy isn't silently lost.
- **Files modified:** frontend/public/maia/ort-wasm-simd-threaded.asyncify.{mjs,wasm}, frontend/public/maia/ort.webgpu.min.js, frontend/public/maia/README.md
- **Committed in:** 42e847ca (Task 2 commit)

**3. [Rule 3 - Blocking] Vendored two additional onnxruntime-web API bundles not yet present**
- **Found during:** Task 2 (maia-worker.js)
- **Issue:** Plan 151-01 vendored only the raw WASM runtime pair (`ort-wasm-simd-threaded.{mjs,wasm}`), not the onnxruntime-web JS API layer (`ort.InferenceSession`/`ort.Tensor`/`ort.env`) itself — the worker cannot call the ONNX API without it.
- **Fix:** Vendored `ort.wasm.min.js` (WASM-only bundle, pairs with the already-vendored baseline WASM runtime) and `ort.webgpu.min.js` (WebGPU+WASM bundle, requires the new Asyncify pair — see deviation #2).
- **Files modified:** frontend/public/maia/ort.wasm.min.js, frontend/public/maia/ort.webgpu.min.js (new files)
- **Committed in:** 42e847ca (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 bug/correction, 1 blocking)
**Impact on plan:** All three were necessary for the worker to function at all or to correctly report/consume WDL; no scope creep beyond what Task 2/3's own action text already implied (vendoring runtime files, single-sourcing the math).

## Known Limitations

**Policy vocabulary index order is a best-effort reconstruction, not yet cross-validated against the real model.** `151-MAIA-CONTRACT.md` confirms the policy output is a flat `[B,4352]` vector keyed by `from+to+promotion`, but the CSSLab reference client's literal `all_moves_maia3.json` index ORDER was deliberately not copied (AGPL hygiene, MAIA-03). `maiaEncoding.ts`'s `moveVocabIndex` uses a deterministic, internally-consistent scheme (base `from*64+to` lane + a reserved `(to, promo-piece)` underpromotion lane) sized to exactly match the confirmed 4352 total, but its alignment with the REAL model's index order is unverified. **This is exactly what Plan 06's VALID-01 real-ONNX cross-check must close** — until then, `maskAndSoftmax`'s move-probability assignments should be treated as unverified against live inference (the unit tests in this plan only prove internal consistency: sums to 1, illegal moves absent, single-legal-move case — they do NOT and cannot prove the indices match the real model without a live session).

**Worker error handling is minimal.** On a worker `'error'` message, the hook only clears `isAnalyzing` — it does not surface a distinct error state to the caller (no `error` field in `UseMaiaEngineState`). Real-model error paths (unsupported-op exceptions, model-load failures) are exercised manually in Plan 06 / VALID-01 per the plan's own instruction ("document, do not silently skip"). If VALID-01 surfaces a need for a first-class error state, Plan 05/06 should add it.

## Issues Encountered

None beyond the deviations above — all resolved inline.

## User Setup Required

None - no external service configuration required. `onnxruntime-web` was already installed and human-verified in Plan 151-01 (checkpoint:human-verify already resolved); this plan only vendors additional runtime bundles from the same already-approved npm package, no new install.

## Next Phase Readiness

- `useMaiaEngine` is ready for Plan 05 (Maia eval bar + ELO selector — consumes `wdl`/`expectedScoreAtSelectedElo`) and Plan 06 (Moves-by-Rating chart — consumes `perElo`; VALID-01 real-ONNX cross-check should specifically verify the policy vocab index scheme documented under "Known Limitations").
- No blockers. The one open risk (vocab index order) is explicitly flagged, not silently assumed correct.

---
*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Completed: 2026-07-05*

## Self-Check: PASSED
All 9 created/modified source files exist on disk; all 3 task commits (fa336795, 42e847ca, 79155d38) present in git log.
