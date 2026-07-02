---
phase: 142-multipv-2-engine-pass-eval-drain-remote-worker
plan: "01"
subsystem: engine
tags: [engine, multipv, unit-tests, tdd]
status: complete

dependency_graph:
  requires: []
  provides:
    - app/services/engine.py::EnginePool._analyse_multipv2
    - app/services/engine.py::EnginePool.evaluate_nodes_multipv2
    - app/services/engine.py::evaluate_nodes_multipv2
  affects:
    - plans/142-02 (eval drain consumes evaluate_nodes_multipv2)
    - plans/142-03 (remote worker pool method)
    - plans/142-04 (validation tool)

tech_stack:
  added: []
  patterns:
    - EnginePool method sibling pattern (_analyse_with_pv analog)
    - 7-tuple return with str (not str | None) second_uci sentinel
    - Module-level wrapper over _pool

key_files:
  created: []
  modified:
    - app/services/engine.py
    - tests/services/test_engine.py

decisions:
  - "D-02: New _analyse_multipv2 method required — list[InfoDict] return type cannot reuse scalar _analyse_with_pv"
  - "D-06: Reuse _NODES_BUDGET=1_000_000 and _NODES_TIMEOUT_S=5.0 unchanged for multipv=2"
  - "Pitfall 3: second_uci is str (never None) — empty string '' is the PvNode.su sentinel for single-legal-move positions"
  - "Return (None,)*7 when pool not started or engine failure — second_uci=None only in that case"

metrics:
  duration_seconds: 301
  completed_date: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 142 Plan 01: _analyse_multipv2 + evaluate_nodes_multipv2 Engine Primitive Summary

New `EnginePool._analyse_multipv2` method + `evaluate_nodes_multipv2` (method + module-level wrapper) for multipv=2 per-ply second-best extraction, guarded for single-legal-move positions, tested with 5 unit tests (no real engine).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD failing test stub | 6825db9f | tests/services/test_engine.py |
| 1 (GREEN) | _analyse_multipv2 + evaluate_nodes_multipv2 | 2b2750a7 | app/services/engine.py |
| 2 | TestEvaluateNodesMultipv2 full unit tests | 4b06e743 | tests/services/test_engine.py |

## What Was Built

**`EnginePool._analyse_multipv2(board, limit, timeout) -> list[chess.engine.InfoDict] | None`**

Sibling of `_analyse_with_pv` (engine.py:568). Copies the worker-acquisition / restart / finally-release structure verbatim; changes the inner call to `protocol.analyse(board, limit, multipv=2)` and the return annotation to `list[chess.engine.InfoDict] | None`. Same except-tuple (TimeoutError, EngineError, EngineTerminatedError) → `_restart_worker(idx)` → return None.

**`EnginePool.evaluate_nodes_multipv2(board) -> tuple[int|None, ...]*7`**

Returns `(eval_cp, eval_mate, best_move, pv_string, second_cp, second_mate, second_uci)`. Calls `_analyse_multipv2` with `_NODES_BUDGET` / `_NODES_TIMEOUT_S`. Guards `len(info_list) > 1`: when False (single-legal-move), sets `second_cp=second_mate=None, second_uci=""` (str sentinel, never None — Pitfall 3). Returns `(None,)*7` on engine failure.

**Module-level `evaluate_nodes_multipv2` wrapper**

After existing `evaluate_nodes_with_pv` (engine.py:289). Returns `(None,)*7` when `_pool is None`, else delegates to `_pool.evaluate_nodes_multipv2(board)`.

**`TestEvaluateNodesMultipv2` (5 tests, mock-protocol only)**

- `test_pool_not_started_returns_7_none`: module-level wrapper with `_pool=None` → `(None,)*7`
- `test_engine_not_started_returns_7_none`: EnginePool with `_started=False` → `(None,)*7`
- `test_two_line_extraction`: two-line result extracts best from index 0, second from index 1 (Pitfall 1 guard)
- `test_single_legal_move_sets_second_sentinel`: len==1 result → `second_uci=""` (str, not None)
- `test_mate_line_best_and_second_extracted`: line 0 mate score with line 1 cp — both extracted correctly

## Acceptance Criteria Verified

- `grep -n "def _analyse_multipv2" app/services/engine.py` → line 568, return `list[chess.engine.InfoDict] | None` ✓
- `grep -n "multipv=2" app/services/engine.py` → new call only at line 594; existing `_analyse_with_pv` unchanged ✓
- `grep -c "def evaluate_nodes_multipv2" app/services/engine.py` → 2 (method + module wrapper) ✓
- `uv run ty check app/services/engine.py` → exits 0 ✓
- `uv run pytest tests/services/test_engine.py::TestEvaluateNodesMultipv2 -x` → 5 tests pass ✓
- `uv run ty check app/ tests/` → zero errors ✓
- `uv run pytest tests/services/test_engine.py -x` → 12 tests pass ✓

## Deviations from Plan

None — plan executed exactly as written.

The plan's action section showed `str|None` as the return type for `second_uci` in the tuple, which appeared to conflict with Pitfall 3 ("never None"). This is not a real conflict: the `(None,)*7` engine-failure return legitimately produces `second_uci=None` (pool not started / engine failed), while `second_uci=""` (str) covers the single-legal-move case where the engine DID run. The return type `str | None` is correct at the function boundary.

## Threat Model Verification

| Threat | Mitigation | Verified |
|--------|-----------|---------|
| T-142-01-01: DoS via hung engine | `_NODES_TIMEOUT_S` + `_restart_worker(idx)` on TimeoutError (copied from `_analyse_with_pv`) | ✓ |
| T-142-01-02: IndexError on `info_list[1]["pv"]` | `len(info_list) > 1` guard + `if second_pv else ""` walrus | ✓ |

## Self-Check: PASSED

- app/services/engine.py: FOUND
- tests/services/test_engine.py: FOUND
- SUMMARY.md: FOUND
- Commit 6825db9f (RED): FOUND
- Commit 2b2750a7 (GREEN): FOUND
- Commit 4b06e743 (tests): FOUND
