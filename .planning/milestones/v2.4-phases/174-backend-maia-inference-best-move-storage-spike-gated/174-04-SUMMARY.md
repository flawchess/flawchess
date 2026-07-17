---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 04
subsystem: backend
tags: [maia, onnxruntime, lifespan, inference, gem-great, classification, elo-normalization, pure-logic, tdd]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    plan: 01
    provides: app/services/maia_encoding.py (encode_board, elo_to_input, mask_and_softmax, clamp_to_ladder_bounds, NUM_SQUARES/PLANES_PER_SQUARE) + the isolated maia-inference uv group (onnxruntime==1.20.1 + numpy).
provides:
  - app/services/maia_engine.py — process-wide Maia ONNX session lifecycle (start_maia/stop_maia, D-03a ImportError no-op guard, SHA-256 model-pin cross-check) + score_move(fen, elo, played_uci) inference.
  - app/services/best_move_candidates.py — pinned_elo_for_mover (GEMS-05, clamp to [600,2600]), passes_inaccuracy_gate (GEMS-02, D-05a), classify_best_move (GEMS-07, pure constants) + GEM_MAIA_MAX_PROB/GREAT_MAIA_MAX_PROB, mover_color_for_ply.
  - app/main.py lifespan wired with start_maia (after start_engine) / stop_maia (finally, after stop_engine).
affects: [174-05, backend-maia-inference, gem-great-classification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Singleton ONNX session mirroring the Stockfish start/stop lifecycle, PLUS a D-03a deferred-import guard so lean/worker images (no maia-inference group) boot without crashing."
    - "SHA-256 model-pin cross-check at session load: a backend/client byte desync DISABLES Maia (Sentry-captured) rather than serving inferences that would disagree with the live board (D-04)."
    - "Pure candidate logic (pinned ELO / inaccuracy gate / classification) that reuses the canonical sigmoid + ELO normalization + clamp + drop thresholds verbatim — no re-derivation, so backend can never drift from the frontend board."
    - "Query-time classification is a pure function of stored (maia_prob, cp margin) + module constants, so a threshold retune reclassifies the whole corpus with zero re-analysis (GEMS-07)."

key-files:
  created:
    - app/services/maia_engine.py
    - app/services/best_move_candidates.py
    - tests/services/test_maia_engine.py
    - tests/services/test_best_move_candidates.py
  modified:
    - app/main.py

key-decisions:
  - "score_move reshapes tokens to (1, NUM_SQUARES, PLANES_PER_SQUARE) to match the proven Plan-01 parity-spike feed shape exactly, and defers the numpy import (isolated group) so maia_engine.py imports cleanly in the default no-group suite."
  - "SHA-256 desync / missing model / ONNX load failure all DISABLE Maia gracefully (session stays None, Sentry-captured) instead of aborting FastAPI startup — extending the D-03a 'lean image must boot' philosophy to every load-time failure mode."
  - "pinned_elo_for_mover takes (raw_rating, platform, time_control_bucket, is_correspondence) and reproduces library_service's exact flawchess-passthrough + `?? raw` fallback shape, delegating to the shared normalize_to_lichess_blitz + clamp_to_ladder_bounds — never re-deriving normalization or clamp."
  - "classify_best_move / passes_inaccuracy_gate import INACCURACY_DROP, MISTAKE_DROP, MATE_CP_EQUIVALENT from flaws_service and eval_cp_to_expected_score from eval_utils; Option-B mate mapping (±MATE_CP_EQUIVALENT before the sigmoid), never eval_mate_to_expected_score."

requirements-completed: [GEMS-02, GEMS-03, GEMS-05, GEMS-07]

coverage:
  - id: D1
    description: "start_maia() is a no-op when onnxruntime is absent (D-03a) — a lean/worker image boots without crashing; session stays None."
    requirement: "GEMS-03"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_engine.py::test_noop_without_onnxruntime (forces ImportError via a sys.modules None sentinel, asserts start_maia returns and _session is None)"
        status: pass
    human_judgment: false
  - id: D2
    description: "start_maia is idempotent (one session), stop_maia is a safe no-op, score_move returns the played move's policy probability in [0,1] via the eager session + Plan-01 encoding."
    requirement: "GEMS-03"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_engine.py::test_start_maia_idempotent_with_session, ::test_score_move_returns_played_move_probability (group-gated; matches the client-equivalent corpus within 0.02), ::test_stop_maia_without_start_is_noop, ::test_score_move_returns_none_without_session"
        status: pass
    human_judgment: false
  - id: D3
    description: "The vendored model's SHA-256 is cross-checked at load against the pinned value (T-174-09); the pin matches the actual bytes."
    requirement: "GEMS-03"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_engine.py::test_model_sha256_pin_matches_vendored_file"
        status: pass
    human_judgment: false
  - id: D4
    description: "pinned_elo_for_mover derives the mover's lichess-blitz-equivalent rating (flawchess passthrough, `?? raw` fallback) and clamps to [600,2600] (GEMS-05, D-04)."
    requirement: "GEMS-05"
    verification:
      - kind: unit
        ref: "tests/services/test_best_move_candidates.py Group 1 (passthrough, 2700->2600, 500->600, lichess-blitz identity, None-normalized fallback, always-in-bounds sweep)"
        status: pass
    human_judgment: false
  - id: D5
    description: "passes_inaccuracy_gate returns true iff best_es - second_es >= INACCURACY_DROP via the shared sigmoid + Option-B mate mapping (GEMS-02, D-05a)."
    requirement: "GEMS-02"
    verification:
      - kind: unit
        ref: "tests/services/test_best_move_candidates.py Group 2 (pass/fail/boundary, mate-via-Option-B, black-mover sign flip, missing-eval False)"
        status: pass
    human_judgment: false
  - id: D6
    description: "classify_best_move maps stored (maia_prob, cp margin) to gem/great/neither purely from constants; the SAME inputs reclassify under retuned constants with zero re-analysis (GEMS-07)."
    requirement: "GEMS-07"
    verification:
      - kind: unit
        ref: "tests/services/test_best_move_candidates.py Group 3 + ::test_constants_only_retune_flips_classification + ::test_reuses_shared_thresholds_not_local_copies"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 04: Backend Maia Inference Lifecycle + Candidate Logic Summary

**The eager-loaded Maia ONNX session (Stockfish-mirrored start/stop, no-op when onnxruntime is absent, SHA-256 model-pin cross-check), `score_move` inference, and all pure candidate logic — pinned+clamped lichess-blitz ELO (GEMS-05), the write-time inaccuracy gate (GEMS-02), and the constants-only Gem/Great/neither classification (GEMS-07) — delivered and unit-tested in isolation (27 tests green, ty + ruff clean).**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-16
- **Tasks:** 2 (both TDD)
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- **`app/services/maia_engine.py`** — process-wide singleton ONNX session mirroring `engine.py`'s `start_engine`/`stop_engine`, with the extra D-03a guard: a deferred `import onnxruntime` inside `try/except ImportError` logs and returns a no-op so lean/worker images (no `maia-inference` group) boot without crashing. Idempotent start, safe no-op stop. At load, the vendored model's SHA-256 is cross-checked against the pinned value (`405bf76c…`); a missing file, digest desync, or ONNX init failure all disable Maia gracefully (session `None`, Sentry-captured) rather than aborting startup. `score_move(fen, elo, played_uci)` reuses the Plan-01 pure encoding (`encode_board`/`elo_to_input`/`mask_and_softmax`) + the eager session and returns the played move's policy probability, or `None` when the session/move is unavailable.
- **`app/main.py`** — lifespan wired: `await start_maia()` immediately after `await start_engine()` (Phase 174 / D-03 comment), `await stop_maia()` in the `finally` after `await stop_engine()`.
- **`app/services/best_move_candidates.py`** — three pure functions, each reusing a single-source implementation:
  - `pinned_elo_for_mover` reproduces the frontend `deriveRawDefault` (`*_lichess_blitz ?? raw`, flawchess passthrough) via the shared `normalize_to_lichess_blitz`, then `clamp_to_ladder_bounds` → always in `[600, 2600]` (GEMS-05, D-04).
  - `passes_inaccuracy_gate` converts both evals via `eval_cp_to_expected_score` (Option-B mate mapping to ±`MATE_CP_EQUIVALENT` before the sigmoid) and returns `best_es − second_es >= INACCURACY_DROP` (GEMS-02, D-05a).
  - `classify_best_move` is pure `(maia_prob, cp margin)` + module constants (`GEM_MAIA_MAX_PROB=0.20`, `GREAT_MAIA_MAX_PROB=0.50`, C2 margin via `MISTAKE_DROP`): gem / great / neither with zero re-analysis (GEMS-07).
  - plus `mover_color_for_ply` (ply-parity helper) and `GEM_MAIA_MAX_PROB`/`GREAT_MAIA_MAX_PROB` named constants.
- **27 unit tests** (6 engine + 21 candidate) green; the D-03a no-op test forces the ImportError via a `sys.modules` None sentinel (proves a lean image boots without uninstalling the package); real-session tests are `importorskip`-gated so the default no-group suite skips them; the constants-only reclassification test flips gem↔great↔neither under monkeypatched constants, proving the GEMS-07 zero-re-analysis retune.

## Gate / Prohibition Status

| Prohibition | Status | Evidence |
|---|---|---|
| A backend image WITHOUT the maia-inference group MUST NOT crash (D-03a) | ENFORCED | `test_noop_without_onnxruntime` forces ImportError, asserts `start_maia()` returns and `_session` stays `None`. |
| cp→ES sigmoid, ELO normalization, ELO clamp MUST reuse the single-source implementations (no re-derivation) | ENFORCED | imports `eval_cp_to_expected_score` (eval_utils), `normalize_to_lichess_blitz` (chesscom_to_lichess), `clamp_to_ladder_bounds` (maia_encoding); `test_reuses_shared_thresholds_not_local_copies` asserts identity with flaws_service constants. |
| classify_best_move MUST be pure (constants + stored floats only) — no DB / engine / re-inference | ENFORCED | `test_constants_only_retune_flips_classification` reclassifies fixed stored inputs under monkeypatched constants with zero re-analysis. |

## Task Commits

1. **Task 1 (RED): failing maia_engine tests** — `66c66e38` (test)
2. **Task 1 (GREEN): maia_engine lifecycle + score_move + lifespan** — `aed7f602` (feat)
3. **Task 2 (RED): failing best_move_candidates tests** — `775d18e7` (test)
4. **Task 2 (GREEN): pinned ELO + gate + classification** — `dc4c8f95` (feat)
5. **Format: ruff format on new test files** — `3033c6ee` (style)

## Files Created/Modified

- `app/services/maia_engine.py` — Maia ONNX lifecycle + score_move (created)
- `app/services/best_move_candidates.py` — pinned ELO / inaccuracy gate / classification (created)
- `app/main.py` — lifespan wired with start_maia/stop_maia (modified)
- `tests/services/test_maia_engine.py` — 6 unit tests (created)
- `tests/services/test_best_move_candidates.py` — 21 unit tests (created)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a test-construction undershoot in the inaccuracy-gate boundary probe**
- **Found during:** Task 2 (GREEN verification)
- **Issue:** `test_gate_boundary_exactly_inaccuracy_drop_passes` inverted the Lichess sigmoid and `round()`-ed the resulting cp to an int; the rounding landed the reconstructed ES gap at ~0.0495, just *below* `INACCURACY_DROP` (0.05), so the "exactly at boundary passes" probe failed its own construction sanity assert. This was a defect in the test, not the implementation (the gate correctly rejects a 0.0495 gap).
- **Fix:** Use `math.ceil` (not `round`) so the integer-cp ES gap lands at or above the threshold — an exact-boundary probe must never undershoot.
- **Files modified:** tests/services/test_best_move_candidates.py
- **Commit:** `dc4c8f95`

**Total deviations:** 1 auto-fixed (1 bug, test-only). No production-code deviations; both modules were implemented exactly as specified, reusing every shared single-source implementation.

## Threat Surface

All three plan-registered threats are mitigated as designed:
- **T-174-07 (session memory growth):** fixed-size singleton, one session per process (no per-request session). RAM measured in Plan 05 (D-03b) before prod enablement.
- **T-174-08 (extreme/malformed rating → float32):** `pinned_elo_for_mover` clamps to `[600, 2600]` before any cast.
- **T-174-09 (backend/client model desync):** SHA-256 cross-check at load; desync disables Maia (Sentry-captured), never serves divergent inferences.

No new security surface beyond the plan's threat model.

## Known Stubs

None. Every function is fully wired to its shared single-source dependency; there are no placeholder/empty-value stubs. (Plan 05 wires these into the eval-apply write pipeline — that integration is the remaining work, not a stub here.)

## User Setup Required

None. The `maia-inference` group and vendored model already exist from Plan 01. Backend enablement (Dockerfile `--group maia-inference`) and prod RSS measurement are Plan 05 concerns.

## Next Plan Readiness

- Plan 05 can now call `start_maia`/`score_move` and the three pure candidate helpers to build and persist `game_best_moves` rows in the eval-apply write session.
- Reminder: `score_move` and the real-session tests only run when the `maia-inference` group is synced; the default no-group suite skips them via `importorskip`. The backend Dockerfile must add `--group maia-inference` (Plan 02/05); `Dockerfile.worker` stays lean (GEMS-06).

## Self-Check: PASSED

All 4 created files present on disk; `app/main.py` wiring confirmed (start_maia after start_engine, stop_maia in finally); all 5 task commits (66c66e38, aed7f602, 775d18e7, dc4c8f95, 3033c6ee) present in git history. 27/27 tests green; `ty` and `ruff` clean on all touched files.

---
*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Completed: 2026-07-16*
