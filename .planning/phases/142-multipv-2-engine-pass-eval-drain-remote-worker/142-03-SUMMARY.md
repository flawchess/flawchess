---
phase: 142-multipv-2-engine-pass-eval-drain-remote-worker
plan: "03"
subsystem: eval_remote
tags: [multipv, pv-blobs, remote-worker, jsonb, backward-compat]
status: complete

dependency_graph:
  requires:
    - plans/142-01 (evaluate_nodes_multipv2 7-tuple primitive)
    - plans/142-02 (_build_flaw_multipv2_blobs / _run_multipv2_pass helpers)
  provides:
    - app/schemas/eval_remote.py::SubmitEval.second_cp / .second_mate / .second_uci
    - app/routers/eval_remote.py::_apply_submit second_best_map + blob assembly
    - scripts/remote_eval_worker.py::_eval_positions upgraded to evaluate_nodes_multipv2
    - SC3: remote-worker SubmitRequest additive extension, backward-compatible
  affects:
    - plans/142-04 (validation tool reads allowed_pv_lines / missed_pv_lines)
    - Phase 143 (forcing_line_gate reads PvNode blobs from game_flaws)
    - Phase 145 (backfills NULL blobs from old workers)

tech_stack:
  added: []
  patterns:
    - Additive Pydantic schema extension (second_cp/second_mate/second_uci = None defaults)
    - D-04 guard: skip blob assembly when second_best_map empty (old worker gap → NULL)
    - Parallel second_best_map alongside engine_result_map (D-03 inline, not parallel list)
    - _build_flaw_multipv2_blobs called before write session (CLAUDE.md session discipline)
    - _run_multipv2_pass called after _classify_and_fill_oracle inside write session (atomic)

key_files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/routers/eval_remote.py
    - scripts/remote_eval_worker.py
    - tests/test_eval_worker_endpoints.py

decisions:
  - "D-03: inline optional second_cp/second_mate/second_uci on SubmitEval (not parallel list)"
  - "D-04 guard: second_best_map empty → blob_map = {} → _run_multipv2_pass no-op → blobs NULL"
  - "dedup_map={} for remote path (no cross-user dedup; worker evaluated all positions)"
  - "second_uci wire type str|None; None maps to su='' sentinel during blob assembly"

metrics:
  duration_seconds: 3600
  completed_date: "2026-06-29"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 4
---

# Phase 142 Plan 03: Remote Worker Contract + SubmitEval MPV-02 Extension Summary

Extend the remote-worker contract additively so MultiPV=2 second-best flows from upgraded
workers into the JSONB blobs, while un-upgraded workers keep processing full-ply jobs
without error. Three changes: (1) inline optional fields on SubmitEval; (2) thread a
parallel second_best_map through _apply_submit and reuse Plan 02 helpers; (3) upgrade
worker _eval_positions to evaluate_nodes_multipv2 and emit second-best keys.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend SubmitEval with optional second-best fields | 0948dcd2 | app/schemas/eval_remote.py |
| 2 | Thread second_best_map through _apply_submit + reuse Plan 02 assembly/write | 53fde40e | app/routers/eval_remote.py |
| 3 | Upgrade worker _eval_positions + D-04 guard + backward-compat tests | 7414d2be | scripts/remote_eval_worker.py, tests/test_eval_worker_endpoints.py, app/routers/eval_remote.py |

## What Was Built

**Task 1: SubmitEval schema extension**

- Added `second_cp: int | None = None`, `second_mate: int | None = None`, `second_uci: str | None = None` to `SubmitEval` (after `pv`)
- Phase 142 MPV-02 / D-03 comment referencing backward-compat semantics
- `SubmitRequest` structure unchanged (D-03 rejects parallel multipv2_evals list)
- Wire type for `second_uci` is `str | None` — a worker may legitimately send None for single-legal-move plies; server maps None → su="" sentinel during blob assembly (Pitfall 3)

**Task 2: _apply_submit threading**

- Built parallel `second_best_map: dict[int, tuple[int|None, int|None, str|None]]` from `body.evals`, including only rows where `e.second_cp is not None or e.second_uci is not None`
- Added D-04 guard: when `second_best_map` is empty (old worker omits all second_*), `blob_map = {}` skips `_build_flaw_multipv2_blobs` entirely → blobs stay NULL
- Added `_build_flaw_multipv2_blobs` and `_run_multipv2_pass` to the eval_drain import block
- `_build_flaw_multipv2_blobs` called before write session (CPU/engine region, CLAUDE.md rule)
- `_run_multipv2_pass` called after `_classify_and_fill_oracle` inside write_session (Pitfall 5)
- `dedup_map={}` for remote path (no cross-user dedup)

**Task 3: Worker upgrade + tests**

- Switched `asyncio.gather` in `_eval_positions` from `pool.evaluate_nodes_with_pv` to `pool.evaluate_nodes_multipv2` (7-tuple)
- Added three output dict keys: `"second_cp": r[4]`, `"second_mate": r[5]`, `"second_uci": r[6]`
- `_eval_entry_positions` (depth-15 path) unchanged — carries no second-best
- Added `test_submit_eval_accepts_second_best_fields`: schema unit test for old/new/null-uci cases
- Added `TestMultipv2BlobsRemote.test_submit_with_second_best_populates_blobs`: 6-ply game with artificial blunder (win-prob 53%→7%), submit with second_cp=25/second_uci="d2d4" at ply=2 → asserts allowed_pv_lines IS NOT NULL, missed_pv_lines IS NOT NULL, node-0 s=25, su="d2d4"
- Added `TestMultipv2BlobsRemote.test_submit_without_second_best_leaves_blobs_null`: same game WITHOUT second_* fields → flaw exists, blobs stay NULL (D-04 backward-compat proof)

## Acceptance Criteria Verified

- `grep -n "second_cp\|second_mate\|second_uci" app/schemas/eval_remote.py` shows all three with `= None` defaults ✓
- `SubmitRequest` structure unchanged ✓
- `uv run ty check app/schemas/eval_remote.py` exits 0 ✓
- `grep -n "second_best_map\|_build_flaw_multipv2_blobs\|_run_multipv2_pass" app/routers/eval_remote.py` shows parallel map build + both helper calls ✓
- `_run_multipv2_pass` call inside write_session block, after `_classify_and_fill_oracle` ✓
- `_build_flaw_multipv2_blobs` called BEFORE write_session opens ✓
- D-04 guard: `if second_best_map:` skips blob assembly when empty ✓
- `uv run ty check app/routers/eval_remote.py` exits 0 ✓
- `grep -n "evaluate_nodes_multipv2\|second_cp\|second_uci" scripts/remote_eval_worker.py` shows `_eval_positions` upgraded ✓
- `_eval_entry_positions` still calls depth-15 path ✓
- Backward-compat test (no second_* → blobs NULL) passes ✓
- Populated blob test (second_* → non-NULL blobs + node-0 s/su check) passes ✓
- `uv run pytest tests/test_eval_worker_endpoints.py -x` green (42 passed) ✓
- `uv run ty check app/ tests/` exits 0 ✓

## Deviations from Plan

**1. [Rule 2 - Missing] Added D-04 guard to skip blob assembly for empty second_best_map**

- **Found during:** Task 3 analysis (backward-compat test design)
- **Issue:** Plan Task 2 action stated "_run_multipv2_pass no-ops on an empty blob_map" but the actual `_build_flaw_multipv2_blobs` produces non-empty blobs even with empty `second_best_map` (1-node blobs from pos_eval). Without the guard, old workers would populate blobs with node-0 only (no second-best data), but D-04 requires NULL blobs for old workers so Phase 145 can backfill with full multipv data.
- **Fix:** Added `if second_best_map: blob_map = await _build_flaw_multipv2_blobs(...)` else `blob_map = {}` in `_apply_submit`
- **Files modified:** `app/routers/eval_remote.py` (included in Task 3 commit)
- **Commit:** 7414d2be

## Known Stubs

None — the blobs are populated with real PvNode dicts (b/bm/s/sm/su fields). Tests use 1-node blobs (no PV strings → no continuation walk), which is sufficient to prove the write path.

## Threat Flags

None — the new fields ride the existing `require_operator_token` authenticated path (T-142-03-01 transfer). Pydantic validates str|None (T-142-03-02 mitigated). The write is in the same atomic txn as flaw rows (T-142-03-04 mitigated).

## Self-Check: PASSED
