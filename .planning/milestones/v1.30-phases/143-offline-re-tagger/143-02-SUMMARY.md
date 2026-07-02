---
phase: 143-offline-re-tagger
plan: "02"
subsystem: backend
tags: [gate, live-drain, classify-path, single-path, sc4, d02, forcing-line]
dependency_graph:
  requires: [143-01, 141-forcing-line-gate, 142-multipv-engine-pass]
  provides: [single-classify-path, gated-live-drain, flaw-pv-blobs-threaded]
  affects:
    - app/services/flaws_service.py
    - app/services/eval_drain.py
    - tests/services/test_flaws_service.py
tech_stack:
  added: []
  patterns: [thin-wrapper, optional-param-threading, tdd-red-green, in-memory-blob-forwarding]
key_files:
  modified:
    - app/services/flaws_service.py
    - app/services/eval_drain.py
    - tests/services/test_flaws_service.py
decisions:
  - "D-02 implemented: _classify_tactic_gated routes both allowed/missed passes through the forcing-line gate"
  - "Gate condition is pv_blob is not None (not truthiness) — empty list passes through gate and is rejected by one-mover discard (Pitfall 2)"
  - "flaw_pv_blobs threaded from _full_drain_tick into _classify_and_fill_oracle -> classify_game_flaws -> _build_flaw_record at classify time (before _run_multipv2_pass writes blobs to DB)"
  - "pre_flaw_eval_cp sourced from positions[n].eval_cp for both orientations (A1 assumption: low residual risk for missed pass per RESEARCH.md)"
  - "flaw_pv_blobs param defaults to None on all signatures — preserves gate-free backward compat for pre-Phase-142 callers"
metrics:
  duration: "~20min"
  completed: "2026-06-30"
  tasks: 2
  files: 3
status: complete
---

# Phase 143 Plan 02: Live Gate Wiring — Single Classify Path Summary

Wire the forcing-line gate into the live tactic classify path (D-02) via a thin `_classify_tactic_gated` wrapper and thread the in-memory MultiPV-2 blobs from the eval drain into that wrapper at classify time.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add `_classify_tactic_gated` wrapper and route `_build_flaw_record` through it | 932073b0 | app/services/flaws_service.py, tests/services/test_flaws_service.py |
| 2 | Thread in-memory `flaw_pv_blobs` into the live classify call | 4fa0b316 | app/services/eval_drain.py |

## What Was Built

### Task 1 — `_classify_tactic_gated` + `_solver_color_for` (D-02, SC4)

**`_solver_color_for(n, orientation)`** maps ply parity + orientation to the tactic-delivering side's color, matching the `board_before.turn` convention at `flaws_service.py` line 444-446:
- Even ply (white mover), "allowed" → "black" (refuter = opponent)
- Odd ply (black mover), "allowed" → "white"
- Even ply (white mover), "missed" → "white" (flaw-maker = mover)
- Odd ply (black mover), "missed" → "black"

**`_classify_tactic_gated(n, fen_map, positions, orientation, pv_blob, pre_flaw_eval_cp, pv_by_ply=None, margin=ONLY_MOVE_WIN_PROB_MARGIN)`** is the single classify path (SC4 no-drift):
- Calls `_detect_tactic_for_flaw` to run tactic detection
- If a motif was detected AND `pv_blob is not None` AND `pre_flaw_eval_cp is not None`: applies `apply_forcing_line_filter`
- If the line is non-forcing: returns `(None, None, None, None)` (motif suppressed)
- Gate skip for `None` blob: pre-Phase-142 rows return the raw kernel result (backward compat)
- Gate condition is `pv_blob is not None` (NOT `if pv_blob`): empty list `[]` is a valid blob that runs through the gate and is rejected by the one-mover discard

**`_build_flaw_record`** updated:
- New optional `flaw_pv_blobs: dict[int, tuple[list[PvNode], list[PvNode]]] | None = None` param
- Extracts `allowed_pv_blob`, `missed_pv_blob` via `flaw_pv_blobs.get(n)` (None when ply absent → gate skips)
- Sources `pre_flaw_eval_cp = positions[n].eval_cp` for both orientations (A1 assumption)
- Routes both passes through `_classify_tactic_gated` instead of `_detect_tactic_for_flaw` directly

**`classify_game_flaws`** updated:
- New optional `flaw_pv_blobs` param (same type, default None)
- Passes it through to `_build_flaw_record`
- All existing callers unaffected (default None → gate-free behavior)

**Unit tests added** (TDD: RED commit then GREEN commit together):
- `TestSolverColorFor`: 4 parity cases (even/odd × allowed/missed)
- `TestClassifyTacticGated`: gate-skip on None blob, suppress on empty blob (Pitfall 2 guard), suppress on small-margin nodes, pass-through on forced 3-node line

### Task 2 — Thread `flaw_pv_blobs` into live drain (D-02, SC4)

**`_classify_and_fill_oracle`** updated:
- New optional `flaw_pv_blobs: dict[int, tuple[list[PvNode], list[PvNode]]] | None = None` param
- Passes it to `classify_game_flaws` at classify time
- Docstring updated with Pitfall 4 warning: blobs are NOT yet in the DB when classify runs

**`_full_drain_tick` call site** updated:
- Passes the in-memory `flaw_pv_blobs` (built by `_build_flaw_multipv2_blobs` in Step 3d) into `_classify_and_fill_oracle`
- Ordering preserved: `_classify_and_fill_oracle` still runs BEFORE `_run_multipv2_pass` writes blobs to DB

No DB read of blobs occurs at classify time. The in-memory dict is the source.

## Verification Results

```
uv run ty check app/ tests/          → All checks passed!
uv run pytest tests/services/test_flaws_service.py tests/services/test_full_eval_drain.py tests/services/test_eval_drain.py -q  → 193 passed
uv run pytest -n auto -x -q          → 2983 passed, 18 skipped
```

## Deviations from Plan

None — plan executed exactly as written.

**TDD compliance:** Tests were written first (RED phase, ImportError confirmed) before the production code (GREEN phase).

## SC4 Status

Partial SC4 achieved (as specified): the live drain classifies tactics through `_classify_tactic_gated`, the single classify path. The re-tagger (Plan 03) will also call this same wrapper, guaranteeing no drift. The DB-level idempotency proof lands in Plan 03.

## Known Stubs

None — this plan modifies pure-backend classify logic only; no UI or data rendering stubs.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The `flaw_pv_blobs` threaded from `_full_drain_tick` is an in-memory dict (own data, not external input). Malformed/partial JSONB nodes are handled by the existing conservative guards in `is_solver_node_forced` / `_resolve_mate_priority` (T-143-02 mitigated as designed).

## Self-Check: PASSED

- FOUND: 143-02-SUMMARY.md
- FOUND: commit 932073b0 (Task 1 — feat: _classify_tactic_gated wrapper)
- FOUND: commit 4fa0b316 (Task 2 — feat: eval_drain threading)
- FOUND: app/services/flaws_service.py (modified — _solver_color_for, _classify_tactic_gated, _build_flaw_record, classify_game_flaws)
- FOUND: app/services/eval_drain.py (modified — _classify_and_fill_oracle, _full_drain_tick call)
- FOUND: tests/services/test_flaws_service.py (modified — TestSolverColorFor, TestClassifyTacticGated)
