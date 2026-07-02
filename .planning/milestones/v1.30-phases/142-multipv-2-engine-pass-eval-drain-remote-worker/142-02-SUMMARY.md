---
phase: 142-multipv-2-engine-pass-eval-drain-remote-worker
plan: "02"
subsystem: eval_drain
tags: [multipv, pv-blobs, drain, engine, jsonb, tdd]
status: complete

dependency_graph:
  requires:
    - plans/142-01 (evaluate_nodes_multipv2 7-tuple primitive)
  provides:
    - app/services/eval_drain.py::_fill_engine_game_flaw_second_best
    - app/services/eval_drain.py::_walk_pv_boards
    - app/services/eval_drain.py::_build_line_blobs
    - app/services/eval_drain.py::_build_flaw_multipv2_blobs
    - app/services/eval_drain.py::_batch_update_flaw_pv_lines
    - app/services/eval_drain.py::_run_multipv2_pass
    - game_flaws.allowed_pv_lines / missed_pv_lines populated per drain tick
  affects:
    - plans/142-03 (remote worker pool method — same evaluate_nodes_multipv2 7-tuple)
    - plans/142-04 (validation tool reads allowed_pv_lines / missed_pv_lines)
    - Phase 143 (forcing_line_gate reads PvNode blobs from game_flaws)

tech_stack:
  added: []
  patterns:
    - 7-tuple gather (parallel second_best_map alongside 4-tuple engine_result_map)
    - Option B PV-walk: server walks each flaw PV locally; only node-0 second-best from worker
    - JSONB batch UPDATE with CAST(:param AS jsonb) (asyncpg compatibility)
    - Session discipline: _build_flaw_multipv2_blobs opens own read session + gathers before write session
    - D-05 recovery: mirrors SEED-056 _fill_engine_game_flaw_pvs pattern

key_files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py

decisions:
  - "D-01: whole-game per-ply pass switched to evaluate_nodes_multipv2 (multipv=2)"
  - "D-02 (parallel maps): engine_result_map kept as 4-tuple (no blast radius on _apply_full_eval_results); second_best_map carries 3-tuple (second_cp, second_mate, second_uci) separately"
  - "D-05 (recovery): _fill_engine_game_flaw_second_best mirrors SEED-056; runs between Step-3b and Step-3d"
  - "Pitfall 3 confirmed: su='' (str, not None) in PvNode; engine failure yields su=None only in (None,)*7 which is filtered by second_best_map condition"
  - "Pitfall 5: _run_multipv2_pass wired inside same write session as _classify_and_fill_oracle"
  - "_fill_engine_game_flaw_pvs also switched to evaluate_nodes_multipv2 (prevents SEED-056 test from patching dead evaluate_nodes_with_pv)"

metrics:
  duration_seconds: 5400
  completed_date: "2026-06-29"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 142 Plan 02: Wire MultiPV=2 Into Eval Drain Summary

Switch the whole-game per-ply eval pass to multipv=2, build a parallel second_best_map, add D-05 recovery for dedup-transplanted flaw plies, Option B PV-walk blob assembly, JSONB batch write, and drain integration test proving non-NULL blobs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Switch Step 3 to multipv2 + second_best_map + D-05 recovery | 74c5c6e4 | app/services/eval_drain.py |
| 2 | _build_flaw_multipv2_blobs + _batch_update_flaw_pv_lines + _run_multipv2_pass | 72c8ecde | app/services/eval_drain.py |
| 3 | Drain integration test for multipv2 blobs | 52df5200 | tests/services/test_full_eval_drain.py, app/services/eval_drain.py |

## What Was Built

**Task 1: Step 3 + second_best_map + D-05 recovery**

- Switched `asyncio.gather` in Step 3 from `evaluate_nodes_with_pv` to `evaluate_nodes_multipv2`; type annotation updated to 7-tuple
- WR-05 circuit breaker unpacks all 7 fields
- `second_best_map: dict[int, tuple[int|None, int|None, str|None]]` built in parallel with `engine_result_map` (4-tuple stays unchanged — zero blast radius on `_apply_full_eval_results` / `_classify_and_fill_oracle`)
- `_fill_engine_game_flaw_second_best` (D-05 recovery): mirrors `_fill_engine_game_flaw_pvs` (SEED-056); no-op for lichess games / no dedup; uses `_missing_flaw_pv_targets` to find the same flaw plies as the PV-recovery pass; calls `evaluate_nodes_multipv2` for the missing plies; merges `res[4:7]` into `second_best_map`
- Added `import json` and `from app.services.forcing_line_gate import PvNode`
- Also switched `_fill_engine_game_flaw_pvs` gather to `evaluate_nodes_multipv2` (slices `res[0:4]` for `engine_result_map` compatibility)

**Task 2: Blob assembly + JSONB write**

- `_walk_pv_boards(start_board, pv_string, cap)`: pure helper; returns `list[chess.Board]` from node 0 to node k; stops on illegal UCI, malformed UCI, or cap reached; each board is an independent copy
- `_build_line_blobs(flaw_ply, line, walk, pos_eval, second_best_map, node_eval)`: assembles `list[PvNode]` for one line; node 0 from `pos_eval` + `second_best_map` (no engine call); nodes 1..N from `node_eval` batch lookup; `su='' if res[6] is None` (Pitfall 3)
- `_build_flaw_multipv2_blobs`: opens own read session (closed before gather), overlays in-memory evals (same as `_missing_flaw_pv_targets`), classifies flaws, walks PVs, runs ONE `asyncio.gather` for all continuation boards across all flaws and both lines, assembles blobs
- `_batch_update_flaw_pv_lines`: batched UPDATE with `CAST(:param AS jsonb)` (asyncpg compatibility, mirrors `_batch_update_pv_rows`); `json.dumps` serializes PvNode lists
- `_run_multipv2_pass`: thin wrapper enforcing Pitfall 5 discipline
- Step 3d wired in `_full_drain_tick` before write session opens; `_run_multipv2_pass` wired after `_classify_and_fill_oracle` inside write session

**Task 3: Test updates**

- `_patch_drain_for_tick_tests` now stubs `_build_flaw_multipv2_blobs → {}` so existing tests (finite side_effect lists) are not disrupted by Step-3d continuation calls
- Updated `_blunder_eval_sequence` and `_two_blunder_eval_sequence` from 4-tuple to 7-tuple; `second_uci=""` added throughout
- Updated `_eval_for_board` (SEED-056 test) to 7-tuple
- Replaced all 21 `evaluate_nodes_with_pv` mock patches with `evaluate_nodes_multipv2`
- Expanded all inline 4-tuples to 7-tuples (side_effect lists + return_value)
- `TestMultipv2Blobs.test_blobs_populated_after_drain_tick`: runs `_full_drain_tick` with iterator mock (main sequence falls back to `(None,)*7` for continuation calls); asserts exactly 1 flaw at ply 2, `allowed_pv_lines IS NOT NULL`, `missed_pv_lines IS NOT NULL`, each with ≥ 1 node

## Acceptance Criteria Verified

- `grep -n "evaluate_nodes_multipv2" app/services/eval_drain.py` shows Step-3 gather and D-05 recovery switched over ✓
- `uv run ty check app/services/eval_drain.py` exits 0 ✓
- `uv run pytest tests/services/test_eval_drain.py -x` passes (18 tests) ✓
- `uv run pytest tests/services/test_full_eval_drain.py -x` passes (38 tests including new blob test) ✓
- `uv run ty check app/ tests/` exits 0 ✓
- `uv run pytest tests/ -n auto -x` passes (2969 tests, 18 skipped) ✓
- `game_flaws.allowed_pv_lines IS NOT NULL` / `missed_pv_lines IS NOT NULL` after tick ✓
- Each blob has ≥1 node ✓

## Deviations from Plan

**1. [Rule 1 - Bug] Also switched _fill_engine_game_flaw_pvs to evaluate_nodes_multipv2**

- **Found during:** Task 3 test run (SEED-056 test failure)
- **Issue:** `_fill_engine_game_flaw_pvs` still called `evaluate_nodes_with_pv`; after Task 3 changed all test mocks from `evaluate_nodes_with_pv` to `evaluate_nodes_multipv2`, the SEED-056 test's mock no longer intercepted the SEED-056 recovery gather → pv stayed NULL → test failed
- **Fix:** Switched `_fill_engine_game_flaw_pvs` gather to `evaluate_nodes_multipv2`; slices `res[0:4]` when writing to `engine_result_map` to keep the 4-tuple invariant
- **Files modified:** `app/services/eval_drain.py` (committed in Task 3 commit)
- **Commit:** 52df5200

**2. [Rule 2 - Missing] Node-0 su narrowing in _build_line_blobs**

- `second_best_map` type is `dict[int, tuple[int|None, int|None, str|None]]` (third element `str|None`)
- When unpacking with `scp, smt, su_raw = second if second else (None, None, "")`, `su_raw` has type `str|None`
- Added explicit narrowing: `su: str = su_raw if su_raw is not None else ""`
- Required by ty's strict TypedDict key-type check (`PvNode.su: str`)

## Known Stubs

None — the blobs are populated with real PvNode dicts (b/bm/s/sm/su fields). Node-0 evals come from the engine; continuation nodes may be None if the engine failed for that position (su="" sentinel).

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. The JSONB write is bounded by existing game_flaws FK constraints.

## Self-Check: PASSED
