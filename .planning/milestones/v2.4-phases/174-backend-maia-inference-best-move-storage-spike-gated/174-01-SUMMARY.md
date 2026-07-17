---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 01
subsystem: testing
tags: [onnxruntime, maia, numpy, python-chess, parity-gate, spike, encoding, softmax]

# Dependency graph
requires:
  - phase: 151-maia-in-the-browser-all-position-surfaces
    provides: The confirmed Maia-3 ONNX tensor contract (12-plane order, mirror-on-black, vocab 4352, raw ELO floats) + frontend/src/lib/maiaEncoding.ts, the port target.
  - phase: 168-headless-calibration-harness-spike-gated
    provides: scripts/lib/node-engine-providers.mjs (createMaiaSession over onnxruntime-web) + frontend-alias-hook.mjs — the independent client-equivalent reference used to capture the fixture corpus.
provides:
  - app/services/maia_encoding.py — pure stdlib+python-chess Python port of the client's Maia-3 board->tensor encoding (encode_board, mask_and_softmax, elo_to_input, clamp_to_ladder_bounds).
  - scripts/maia_parity_spike.py — the committed D-02 parity gate (tier-stability + empirical epsilon) with PARITY_EPSILON=0.010.
  - tests/fixtures/maia_parity/corpus.json — 11-ply fixture corpus (4 great, 4 gem, 3 neither) with client-equivalent expected maia_prob + provenance.
  - Isolated uv dependency group `maia-inference` (onnxruntime==1.20.1 + numpy), kept out of [project.dependencies].
affects: [174-02, 174-03, 174-04, 174-05, backend-maia-inference, gem-great-classification]

# Tech tracking
tech-stack:
  added:
    - "onnxruntime==1.20.1 (isolated maia-inference uv group; >=1.22 segfaults the vendored model)"
    - "numpy (same isolated group)"
  patterns:
    - "Non-circular parity gate: expected values captured from an INDEPENDENT client path (onnxruntime-web WASM + the live TS encoding) vs the Python port under test (onnxruntime CPU)."
    - "Isolated uv dependency group + numpy-free service module so the encoding unit tests run in the default no-group backend suite while onnxruntime/numpy stay opt-in."
    - "Empirically-derived epsilon: measure real per-ply drift, set the tolerance from it with headroom below the tightest tier-edge margin — never leave a research placeholder."

key-files:
  created:
    - app/services/maia_encoding.py
    - scripts/maia_parity_spike.py
    - scripts/maia_reference_capture.mjs
    - tests/services/test_maia_encoding.py
    - tests/services/test_maia_parity.py
    - tests/fixtures/maia_parity/corpus.json
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "PARITY_EPSILON=0.010, derived from a measured max per-ply drift of 0.003844 (~2.6x headroom, an order of magnitude below the 0.033 tightest tier-edge margin) — tightens the ~0.02 research placeholder."
  - "Fixture corpus expected values captured via onnxruntime-web WASM + the live frontend maiaEncoding.ts (client-equivalent, independent of the Python port) so the gate is a genuine cross-check, not a self-comparison."
  - "Encoding module made pure stdlib + python-chess (no numpy): numpy stays isolated in the maia-inference group AND the encoding unit tests run in the default no-group suite (both must-haves satisfied)."
  - "mask_and_softmax keyed by UCI (backend move currency) rather than the client's SAN — identical probability values, direct played_uci lookup."

patterns-established:
  - "Client-equivalent reference capture (scripts/maia_reference_capture.mjs): drive the vendored ONNX model through onnxruntime-web + the real TS encoding to produce ground-truth fixtures for a backend port."
  - "Committed parity spike as a standing regression guard against onnxruntime/model bumps (Pitfall 2), not a throwaway artifact."

requirements-completed: [GEMS-04]

coverage:
  - id: D1
    description: "Python port of the Maia-3 12-plane encoding (mirror-on-black, vocab 4352 mask+softmax, ELO clamp [600,2600]) reproduces the client contract."
    requirement: "GEMS-04"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_encoding.py (18 tests: plane order, square index a1/h8, mirror-on-black, one-hot tensor, softmax sum=1 / illegal excluded, clamp bounds)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-02 parity gate: every fixture ply tier-matches the client-equivalent reference within PARITY_EPSILON (the spike-gate for the whole phase)."
    requirement: "GEMS-04"
    verification:
      - kind: integration
        ref: "scripts/maia_parity_spike.py (exit 0; 11/11 plies tier-match, max drift 0.003844 <= PARITY_EPSILON 0.010)"
        status: pass
      - kind: integration
        ref: "tests/services/test_maia_parity.py (11 parametrized plies, importorskip numpy+onnxruntime)"
        status: pass
    human_judgment: false
  - id: D3
    description: "onnxruntime==1.20.1 + numpy isolated in a NEW uv group, absent from [project.dependencies] (GEMS-06 worker-image leanness precondition)."
    requirement: "GEMS-04"
    verification:
      - kind: other
        ref: "grep: onnxruntime absent from [project.dependencies], present as ==1.20.1 in [dependency-groups].maia-inference"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 01: Maia Parity Spike Gate Summary

**Python port of the client's Maia-3 board->tensor encoding + a non-circular D-02 parity gate that PASSES (11/11 fixture plies tier-match within an empirically-derived PARITY_EPSILON=0.010, max drift 0.003844) — the phase is cleared to proceed to Wave 2.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-07-16T12:27:07Z
- **Completed:** 2026-07-16T12:41:22Z
- **Tasks:** 2
- **Files modified:** 8 (6 created, 2 modified)

## GATE RESULT (D-02)

**PASSED.** `scripts/maia_parity_spike.py` exits 0. Every one of the 11 fixture plies lands in the SAME gem/great/neither tier on both the Python port (onnxruntime CPU) and the client-equivalent reference (onnxruntime-web WASM), and every raw `maia_prob` is within PARITY_EPSILON.

- **Empirical epsilon:** `PARITY_EPSILON = 0.010`, derived from a **measured max per-ply drift of 0.003844** (on the busy Rxd1 @2600 middlegame position; simpler positions drift 0.0000–0.0003). This gives ~2.6x headroom over the measured drift while sitting an order of magnitude below the tightest tier-edge margin in the corpus (0.033, Nf3 @1500), so a real tier flip can never hide inside the band. Tightens the ~0.02 research placeholder to the real CPU-vs-WASM drift.
- **Non-circularity:** expected values were captured from the TS encoding + onnxruntime-web WASM path, INDEPENDENT of the Python port under test. The 2600-ELO Qxh2+/Rxd1 anchor reproduces the independently UI-captured note values (UI 0.4524/0.4184; here 0.4494/0.4222) within WebGPU-vs-WASM drift.

## Accomplishments
- Ported the client's Maia-3 encoding to `app/services/maia_encoding.py` (pure stdlib + python-chess): 12-plane mirror-on-black `encode_board`, vocab-4352 legal-move-masked `mask_and_softmax` (keyed by UCI), `elo_to_input`, `clamp_to_ladder_bounds` to [600,2600]. 18 unit tests, all green, runnable without onnxruntime/numpy.
- Built the D-02 parity gate `scripts/maia_parity_spike.py` (SHA-256-verified model load, tier + epsilon assertions, exits 0 iff all pass) and its pytest wrapper.
- Captured an 11-ply fixture corpus spanning all three tiers via a new client-equivalent reference generator (`scripts/maia_reference_capture.mjs`) using onnxruntime-web + the live TS encoding.
- Isolated `onnxruntime==1.20.1` + `numpy` in a new `maia-inference` uv group, kept out of `[project.dependencies]` so the lean worker image excludes them (GEMS-06).

## Task Commits

1. **Task 1 (RED): failing encoding unit tests** - `9f12dc46` (test)
2. **Task 1 (GREEN): encoding port + isolated uv group** - `8dd2dee6` (feat)
3. **Task 1/2 (deviation fix): numpy-free encoding module** - `4152dcad` (fix)
4. **Task 2: parity spike gate + corpus + reference capture** - `999ea67b` (feat)

## Files Created/Modified
- `app/services/maia_encoding.py` - pure Python Maia-3 encoding port (created)
- `scripts/maia_parity_spike.py` - the committed D-02 parity gate (created)
- `scripts/maia_reference_capture.mjs` - client-equivalent fixture generator (onnxruntime-web + TS encoding) (created)
- `tests/services/test_maia_encoding.py` - 18 pure-math unit tests (created)
- `tests/services/test_maia_parity.py` - group-gated parity pytest wrapper (created)
- `tests/fixtures/maia_parity/corpus.json` - 11-ply fixture corpus + provenance (created)
- `pyproject.toml` - new isolated `maia-inference` dependency group (modified)
- `uv.lock` - onnxruntime 1.20.1 + numpy resolution (modified)

## Decisions Made
- Kept the tolerance as a real measured value (0.010 from 0.003844 drift), recorded in both the spike script and the corpus provenance — no research placeholder shipped.
- Captured fixtures from an independent client path (onnxruntime-web + TS encoding) to keep the gate a genuine cross-check.
- Keyed `mask_and_softmax` by UCI (the backend's move currency) instead of the client's SAN — same probability values, direct `played_uci` lookup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made the encoding module numpy-free**
- **Found during:** Task 2 (fixture/gate wiring, when validating the default no-group suite)
- **Issue:** The plan places `numpy` in the isolated `maia-inference` group AND requires the encoding module + its unit tests to run in the default no-group suite. But the module (and `test_maia_encoding.py`) imported numpy at module scope, so with the group unsynced the whole default backend suite failed collection with `ModuleNotFoundError: numpy` (would break CI / the pre-merge gate). The two must-haves were in direct tension as written.
- **Fix:** Reworked `app/services/maia_encoding.py` to pure stdlib + python-chess — `encode_board` returns `list[float]`, `mask_and_softmax` uses `math.exp` over an indexable `Sequence[float]`. The ONNX callers (spike + parity test) wrap the list in a numpy float32 tensor at feed time and pass `policy.tolist()`. numpy stays isolated in the group; the encoding tests now run group-free. `test_maia_parity.py` additionally `importorskip`s numpy so it skips (not errors) in the default suite.
- **Files modified:** app/services/maia_encoding.py, tests/services/test_maia_encoding.py, tests/services/test_maia_parity.py, scripts/maia_parity_spike.py
- **Verification:** default-env full-suite collection clean (3326 tests, 0 errors); `test_maia_encoding.py` 18/18 green without the group; parity module skips cleanly; ty + ruff clean.
- **Committed in:** `4152dcad` (fix) + `999ea67b` (feat)

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Necessary to keep the default backend suite/CI green while honoring both isolation must-haves. No scope creep — same public API and behavior, only the internal array type changed. The gate's math and result are unaffected.

## Issues Encountered
None beyond the numpy tension documented as a deviation above. The parity gate passed on the first real measurement; no epsilon loosening or escape-hatch was needed.

## User Setup Required
None - no external service configuration required. (Backend enablement, prod RSS measurement, and the Maia session lifecycle are later plans in this phase.)

## Next Phase Readiness
- **The spike gate is GREEN — Wave 2 (Plans 02-05) may proceed.** Per D-02 the phase does NOT pause for re-scope.
- Provides the port (`app/services/maia_encoding.py`), the isolated `maia-inference` group, and the committed regression gate (`scripts/maia_parity_spike.py`) that downstream plans build on.
- Reminder for downstream/CI: the parity gate and Maia inference only run when the `maia-inference` group is synced (`uv sync --group maia-inference`); the backend Dockerfile must add `--group maia-inference` while `Dockerfile.worker` stays lean (GEMS-06, Plan 02).

## Self-Check: PASSED

All 6 created files present on disk; all 4 task commits (9f12dc46, 8dd2dee6, 4152dcad, 999ea67b) present in git history.

---
*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Completed: 2026-07-16*
