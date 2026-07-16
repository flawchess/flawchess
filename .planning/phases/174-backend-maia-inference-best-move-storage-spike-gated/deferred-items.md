# Phase 174 — Deferred Items

Out-of-scope discoveries logged during plan execution (not fixed in-plan per the
executor SCOPE BOUNDARY). These must be resolved before the phase's pre-merge gate
(`uv run ty check app/ tests/` with zero errors).

## D-174-DEFER-01: whole-tree ty errors in Plan-04's test_best_move_candidates.py — RESOLVED

- **Resolved:** commit `0c8d9201` (post-Wave-3, by execute-phase orchestrator). Typed the
  shared margin kwargs as `_MarginKwargs` / `_ClassifyKwargs` TypedDicts so the `**` splat
  carries the `mover_color` `Literal`. `uv run ty check app/ tests/` → "All checks passed!";
  21/21 tests still green.
- **Found during:** Plan 05 execution (whole-tree `uv run ty check app/ tests/`).
- **Symptom:** 48 `error[invalid-argument-type]: Argument to function classify_best_move is incorrect`
  in `tests/services/test_best_move_candidates.py`. Reproduces with
  `uv run ty check tests/services/test_best_move_candidates.py` alone.
- **Root cause:** the test passes tuple/`None` literals into `classify_best_move`
  whose narrow inferred types don't match the parameter's `int | None` unions
  (dict/tuple invariance) — the same class of issue fixed in Plan 05's own
  `test_eval_apply.py` via explicit type aliases.
- **Why deferred:** Plan-04 file, not touched by Plan 05; out of Plan-05 scope.
  Plan 05's own files (`eval_apply.py`, `eval_drain.py`, `eval_remote.py`,
  `test_eval_apply.py`, `measure_maia_rss.py`) are ty-clean.
- **Fix (trivial):** annotate the affected call-argument literals in
  `test_best_move_candidates.py` with the expected `int | None` types (mirror the
  `_EngineResultMap` / explicit-annotation pattern used in `test_eval_apply.py`).
