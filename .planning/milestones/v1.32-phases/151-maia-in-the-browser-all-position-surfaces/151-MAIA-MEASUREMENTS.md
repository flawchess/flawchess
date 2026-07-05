# 151-MAIA-MEASUREMENTS — MAIA-06 size + latency, VALID-01 calibration sign-off

**Phase:** 151-maia-in-the-browser-all-position-surfaces
**Plan:** 06 (Task 4, blocking-human quality gate — D-10 measure-and-judge)
**Recorded:** 2026-07-05
**Verdict:** APPROVED (human sign-off — see §3)

---

## 1. Download / bundle size (MAIA-06)

Static artifact sizes measured directly from the vendored files in
`frontend/public/maia/` (on-disk bytes → binary MB). These are exact, not estimates.
Over-the-wire transfer size will differ if the server applies gzip/brotli to the
`.wasm`/`.onnx` (measure the `Content-Length` in devtools Network for the true
transfer figure).

| Artifact | Path | On-disk size |
|----------|------|--------------|
| Maia-3 model (smallest, D-09) | `maia3_simplified.onnx` | 45,683,686 B (~43.6 MiB / ~45.7 MB) |
| WASM-only runtime binary | `ort-wasm-simd-threaded.wasm` | 13,479,978 B (~12.9 MiB / ~13.5 MB) |
| WebGPU (Asyncify) runtime binary | `ort-wasm-simd-threaded.asyncify.wasm` | 24,254,953 B (~23.1 MiB / ~24.3 MB) |
| ort WASM API bundle | `ort.wasm.min.js` | 50,139 B (~49 KiB) |
| ort WebGPU API bundle | `ort.webgpu.min.js` | 67,237 B (~66 KiB) |
| ort WASM glue (.mjs) | `ort-wasm-simd-threaded.mjs` | 24,180 B (~24 KiB) |
| ort Asyncify glue (.mjs) | `ort-wasm-simd-threaded.asyncify.mjs` | 47,507 B (~46 KiB) |
| Maia worker | `maia-worker.js` | 9,236 B (~9 KiB) |

**Effective first-load download by backend path** (model + the ONE runtime binary that
path uses + its JS glue; the two runtime binaries are never both downloaded — see
151-04 decision "two separate ort API bundles"):

- **WASM path (mobile Safari / no-WebGPU):** ~45.7 MB model + ~13.5 MB WASM binary + ~0.07 MB JS ≈ **~59 MB**
- **WebGPU path (desktop w/ WebGPU):** ~45.7 MB model + ~24.3 MB Asyncify binary + ~0.11 MB JS ≈ **~70 MB**

The model is the dominant term either way. D-10 note: no model-size upgrade was
triggered (calibration passed — §3), so the 23M/79M larger variants (~90 MB / ~320 MB
fp32) were NOT adopted; the ~45.7 MB `maia3_simplified.onnx` stays.

---

## 2. Cold-load + per-position latency (MAIA-06)

Live device-side timings. These require an actual browser session per device/backend
and are NOT derivable from the repo. The human ran the live calibration pass (§3) but
did not record numeric timings; the rows below are left explicitly UNMEASURED rather
than fabricated. Fill from devtools Performance / `performance.now()` around the worker
`init`→`ready` and `analyze`→`result` round-trips when a numeric MAIA-06 latency
budget is needed.

Legend: **cold-load** = time from worker `init` to the first `ready` (ONNX session
created, first inference warm); **per-position (single)** = one FEN's `analyze`→`result`
for the batched ELO-ladder run the worker already does; **per-position (ELO-sweep)** =
same, noting the worker computes the whole ladder in ONE `session.run`, so the
"ELO-sweep" cost is not an added round-trip — changing the ELO selector re-derives from
the already-cached curve with no new inference (151-04 design).

| Device | Backend | Cold-load | Per-position (single) | Per-position (ELO-sweep) |
|--------|---------|-----------|-----------------------|--------------------------|
| Desktop | WebGPU | NOT YET MEASURED | NOT YET MEASURED | (no extra call — cached curve; selector change is derive-only) |
| Desktop | WASM (fallback) | NOT YET MEASURED | NOT YET MEASURED | (no extra call — cached curve) |
| Phone | WASM | NOT YET MEASURED | NOT YET MEASURED | (no extra call — cached curve) |
| Phone | WebGPU (if avail.) | NOT YET MEASURED | NOT YET MEASURED | (no extra call — cached curve) |

**Qualitative human observation (from the §3 live pass):** per-position recompute on
board navigation felt responsive on desktop with no visible stall; the bar + chart
update live per move without a server round-trip (SURF-05 confirmed observationally).
No numeric budget was set for this phase (D-10: the ephemeral in-browser surface IS the
quality gate, not a latency threshold) — record real numbers here if/when a MAIA-06
latency budget is introduced.

---

## 3. VALID-01 calibration + move-label sanity check (human sign-off)

**Verdict: APPROVED** (human, 2026-07-05).

The human performed the live calibration eyeball and the explicit policy-vocab
move-label sanity check requested in the checkpoint:

- **Bar direction / WDL sign (Assumption A5, T-151-14):** the Maia expected-score bar
  (LEFT) moves in a plausible human direction relative to the Stockfish bar (RIGHT); no
  flipped-bar tell observed.
- **Chart calibration (Q-014/Q-015):** per-move probability curves across the ELO
  ladder read sane (moves shift with rating in the expected direction) at multiple
  ELO-selector settings.
- **Move-label sanity (151-04 open policy-vocab risk):** the moves shown in the
  Moves-by-Rating chart and associated with the expected-score bar correspond to
  SENSIBLE, correct SANs for the position — probabilities are NOT attached to wrong
  moves. This is the specific failure mode a scrambled 4352-vocab index would produce
  (right chart shape, wrong labels); the human confirmed labels are correct, so the
  best-effort vocab-index reconstruction from 151-04 is validated against live
  inference for the positions checked.

**D-10 model-size decision:** calibration is acceptable → **NO upgrade** to the larger
23M/79M model. The smallest `maia3_simplified.onnx` (D-09) ships as-is.

---

## 4. Isolation / regression guard (T-151-13)

`window.crossOriginIsolated === false` must hold (no COOP/COEP headers were added — the
Maia worker runs single-thread WASM / WebGPU without cross-origin isolation, preserving
OAuth + iOS behavior). Confirmed by inspection: this plan added no header edits, and
the worker forces `numThreads = 1` (151-04). Human live pass reported no
unsupported-op console errors during calibration. If a devtools console check of
`window.crossOriginIsolated` is desired as a belt-and-suspenders record, run it on the
live `/analysis` page — expected value: `false`.
