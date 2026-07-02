---
phase: 145-corpus-backfill-rollout
plan: "01"
subsystem: tactic-gate
tags: [forcing-line-gate, sentinel, backfill, migration, tdd]
dependency_graph:
  requires: []
  provides: [D-06-sentinel-tolerance, SHIP-02-live-gate-fix, ix_game_flaws_blob_backfill]
  affects: [flaws_service, eval_remote, game_flaws]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, partial-index-migration, monkeypatch-spy]
key_files:
  created:
    - alembic/versions/20260630_220000_c3f5d1e8a092_ix_game_flaws_blob_backfill.py
  modified:
    - app/services/flaws_service.py
    - app/routers/eval_remote.py
    - tests/services/test_flaws_service.py
    - tests/test_eval_worker_endpoints.py
decisions:
  - "D-06: empty list [] in _classify_tactic_gated is now the un-fillable sentinel — gate skipped, raw kernel result returned (supersedes Phase-143 Pitfall-2)"
  - "SHIP-02: blob_map if blob_map else None degrades empty dict (old worker) to None → gate skipped → backward-compat preserved"
  - "Partial index uses game_id column (not flaw_id) so the lottery can read game_id directly from the index without a heap fetch"
metrics:
  duration: "7 minutes"
  completed: 2026-06-30
  tasks_completed: 3
  files_modified: 4
  files_created: 1
status: complete
---

# Phase 145 Plan 01: Corpus Backfill Rollout — Prerequisites Summary

## One-liner

Three load-bearing correctness fixes: D-06 sentinel tolerance in `_classify_tactic_gated`, SHIP-02 blob_map threading in `_apply_submit`, and `ix_game_flaws_blob_backfill` partial index for the Plan-02 lottery.

## What Was Built

### Task 1: D-06 sentinel tolerance in `_classify_tactic_gated`

**Problem:** The gate guard was `pv_blob is not None`, which meant an empty list `[]` entered the gate and was rejected by the one-mover discard (0 solver nodes < required). This would incorrectly strip tactic tags from flaws whose PV blob could not be assembled (the D-06 sentinel case), making it unsafe to write sentinels to the corpus before fixing the gate.

**Fix:** Changed the gate guard in `_classify_tactic_gated` to `pv_blob is not None and len(pv_blob) > 0`. The empty list is now the D-06 un-fillable sentinel — gate is skipped, raw kernel result returned. `apply_forcing_line_filter` itself remains unchanged (correctly rejects `[]` when called directly; the skip is upstream of that call).

**Docstring:** Updated to document the D-06 semantic, explicitly superseding the Phase-143 Pitfall-2 wording.

**TDD:** RED (renamed and inverted `test_suppression_when_blob_is_empty_list` → `test_sentinel_empty_blob_skips_gate_returns_kernel_result`), then GREEN.

### Task 2: Fix the live `_apply_submit` gate gap (SHIP-02)

**Problem:** In `_apply_submit` (eval_remote.py), `_classify_and_fill_oracle` was called without passing `blob_map`. Blobs were assembled and written via `_run_multipv2_pass`, but the tactic classification ran ungated — new remote-worker games received unfiltered tags even when second-best data was available.

**Fix:** Changed the call to `await _classify_and_fill_oracle(write_session, game_id, engine_result_map, blob_map if blob_map else None)`. The `blob_map if blob_map else None` expression degrades an empty dict (old-worker, no second-best) to `None`, preserving the gate-skipped backward-compatible path.

**TDD:** RED (spy test captures `flaw_pv_blobs` kwarg — fails when `None` is returned for a new-worker submit), then GREEN.

### Task 3: Partial index for the tier-4 backfill predicate

**Created:** `alembic/versions/20260630_220000_c3f5d1e8a092_ix_game_flaws_blob_backfill.py`

Creates `ix_game_flaws_blob_backfill` on `game_flaws (game_id) WHERE allowed_pv_lines IS NULL`. Backs the Plan-02 tier-4 lottery predicate so it does not seq-scan ~3.18M game_flaws rows on every remote-worker idle poll. Non-concurrent (inside transaction), mirroring the existing pattern. Shrinks to near-empty as backfill writes blobs/sentinels. Single head confirmed.

## Verification Results

- `uv run pytest tests/services/test_flaws_service.py tests/test_eval_worker_endpoints.py -x`: **180 passed**
- `uv run alembic upgrade head && downgrade -1 && upgrade head && heads`: round-trips clean, single head `c3f5d1e8a092`
- `uv run ruff check` touched files: **All checks passed**
- `uv run ty check` touched files: **All checks passed**

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all changes are complete implementations with no placeholder behavior.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries beyond the DDL-only migration documented in the plan's threat register (T-145-02, accepted).

## Self-Check

Verified commits exist and files are present.
