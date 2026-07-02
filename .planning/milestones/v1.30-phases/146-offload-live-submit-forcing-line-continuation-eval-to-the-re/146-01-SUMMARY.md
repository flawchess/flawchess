---
phase: 146-offload-live-submit-forcing-line-continuation-eval-to-the-re
plan: "01"
subsystem: eval-pipeline
tags:
  - eval-remote
  - tier-4
  - flaw-blobs
  - performance
  - d-03
  - d-01
dependency_graph:
  requires:
    - "Phase 145 tier-4 server endpoints (_claim_tier4_blob, /flaw-blob-lease, /flaw-blob-submit)"
    - "Phase 142 _apply_submit write path (reused unchanged)"
  provides:
    - "Live /submit takes the empty-blob_map path unconditionally (D-03)"
    - "TIER4_RECENCY_WINDOW constant + recency-CTE for _claim_tier4_blob (D-01)"
  affects:
    - "app/routers/eval_remote.py (_apply_submit)"
    - "app/schemas/eval_remote.py (SubmitEval)"
    - "app/services/eval_queue_service.py (_claim_tier4_blob)"
tech_stack:
  added: []
  patterns:
    - "sa.text bound-param convention for recency CTE (:recency_window in params dict)"
    - "PvNode imported from forcing_line_gate for blob_map type annotation"
key_files:
  created:
    - tests/test_eval_queue_service.py
  modified:
    - app/routers/eval_remote.py
    - app/schemas/eval_remote.py
    - app/services/eval_queue_service.py
    - tests/test_eval_worker_endpoints.py
decisions:
  - "blob_map={} unconditional in _apply_submit — empty-blob branch made the default live path"
  - "PvNode imported from forcing_line_gate for explicit type annotation"
  - "Recency CTE queries games directly (not game_flaws) to avoid duplicate rows per game"
  - "TIER4_RECENCY_WINDOW=50 placed near RECENCY_HALF_LIFE_DAYS/WEIGHT_FLOOR constants"
  - "Existing Phase 142 MPV-02 tests updated to reflect new behavior (blobs always NULL)"
metrics:
  duration: "~80 minutes"
  completed: "2026-07-01"
  tasks_completed: 2
  files_modified: 5
status: complete
---

# Phase 146 Plan 01: Offload live-submit blob assembly, recency-order tier-4 drain — Summary

**One-liner:** Unconditional `blob_map={}` in `_apply_submit` (no server Stockfish on live submit path) plus recency-windowed CTE in `_claim_tier4_blob` to drain freshly-analyzed games promptly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Force blob_map={} in _apply_submit and drop second-best from SubmitEval (D-03) | ab47e283 | app/routers/eval_remote.py, app/schemas/eval_remote.py, tests/test_eval_worker_endpoints.py |
| 2 | Recency-order _claim_tier4_blob so fresh games drain first (D-01) | 38db8a81 | app/services/eval_queue_service.py, tests/test_eval_queue_service.py |

## What Was Built

### Task 1: D-03 — Unconditional blob_map={} in _apply_submit

**app/schemas/eval_remote.py:**
- Removed `second_cp`, `second_mate`, `second_uci` fields from `SubmitEval` (the Phase-142 MPV-02 per-ply second-best fields). These fields fed only the removed `_build_flaw_multipv2_blobs` call.
- Pydantic v2 default (`extra` not set to `'forbid'`) silently ignores unknown fields on `SubmitEval` and `SubmitRequest` — old workers that still send `second_*` receive no 422 (backward-compat narrowing).

**app/routers/eval_remote.py:**
- Replaced the Phase-142 `second_best_map` dict-comprehension build + conditional `_build_flaw_multipv2_blobs` call (lines 256-276 previously) with the single unconditional assignment `blob_map: dict[int, tuple[list[PvNode], list[PvNode]]] = {}`.
- Removed the now-dead `_run_multipv2_pass(write_session, game_id, blob_map)` call (was a no-op on empty dict; removed for clarity per RESEARCH Open Question 2).
- Removed both imports (`_build_flaw_multipv2_blobs`, `_run_multipv2_pass`) from the eval_drain import block.
- Added `PvNode` import from `app.services.forcing_line_gate` for the explicit type annotation.
- Updated comment at `_classify_and_fill_oracle` call site to reflect Phase 146 state.

The existing write path is untouched: `_apply_full_eval_results`, `_classify_and_fill_oracle(..., None)` (raw classify, gate skipped), `_mark_full_evals_completed`, `_mark_full_pv_completed` — both completion markers still stamped on Path A/C.

**tests/test_eval_worker_endpoints.py:**
- Added three RED tests (committed before code change): `test_submit_eval_schema_phase146_no_second_best_fields`, `test_submit_phase146_build_blob_not_called`, `test_submit_phase146_blobs_null_both_markers_stamped`.
- Updated Phase 142 tests to match new behavior:
  - `test_submit_eval_accepts_second_best_fields` → updated to assert `second_cp` is NOT an attribute, and extra keys in JSON are silently ignored.
  - `TestMultipv2BlobsRemote.test_submit_with_second_best_populates_blobs` → renamed `test_submit_with_second_best_leaves_blobs_null`; asserts blobs always NULL even with second_best in payload.
  - `TestMultipv2BlobsRemote.test_apply_submit_passes_blob_map_to_classify` → renamed `test_apply_submit_passes_none_to_classify`; asserts spy always receives `flaw_pv_blobs=None`.

### Task 2: D-01 — Recency-ordered _claim_tier4_blob

**app/services/eval_queue_service.py:**
- Added `TIER4_RECENCY_WINDOW: int = 50` constant in the module-level constants block, after `WEIGHT_FLOOR`.
- Replaced the old `ORDER BY random() LIMIT 1` query over the entire `allowed_pv_lines IS NULL` backlog with a recency CTE:
  ```sql
  WITH recent AS (
      SELECT g.id AS game_id, g.user_id, g.full_evals_completed_at
      FROM games g
      JOIN users u ON u.id = g.user_id
      WHERE EXISTS (SELECT 1 FROM game_flaws gf WHERE gf.game_id = g.id AND gf.allowed_pv_lines IS NULL)
        AND g.full_evals_completed_at IS NOT NULL
        AND u.is_guest = false
      ORDER BY g.full_evals_completed_at DESC
      LIMIT :recency_window
  )
  SELECT game_id, user_id FROM recent ORDER BY random() LIMIT 1
  ```
- `:recency_window` is bound via the params dict (`{"recency_window": TIER4_RECENCY_WINDOW}`), never f-string-interpolated (security convention).
- CTE queries `games` directly (not `game_flaws`) to avoid duplicate rows per game (RESEARCH Pitfall 4).
- Updated docstring to describe the recency behavior and security note.

**tests/test_eval_queue_service.py** (new file):
- Created with session-scoped `tier4_session_maker` and `tier4_test_user` fixtures.
- `test_claim_tier4_blob_recency_favors_fresh_game`: monkeypatches `TIER4_RECENCY_WINDOW=1`, inserts two games (1 min ago vs 1 hour ago), asserts all 20 draws pick the fresh game (window=1 means only the most-recent game enters the pool). Every insert wrapped in a `finally`-cleanup for eval-lottery isolation.

## Verification

```
uv run pytest -n auto tests/test_eval_worker_endpoints.py tests/test_eval_queue_service.py
# → 69 passed

grep -n "_build_flaw_multipv2_blobs\|_run_multipv2_pass" app/routers/eval_remote.py | grep -v '^\s*#' | wc -l
# → 0

grep -n "recency_window" app/services/eval_queue_service.py | grep -v 'f"' | grep -c ":recency_window"
# → 3 (≥1 bound-param usages)

uv run ty check app/ tests/   # → 0 errors
uv run ruff check app/ tests/ # → All checks passed!
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_submit_phase146_build_blob_not_called — patch location**

- **Found during:** Task 1 GREEN phase
- **Issue:** Monkeypatched `app.routers.eval_remote._build_flaw_multipv2_blobs` but Phase 146 removed that import — `AttributeError` raised from monkeypatch itself, not from the submit endpoint.
- **Fix:** Changed patch target to `app.services.eval_drain._build_flaw_multipv2_blobs` (the definition site). Since eval_remote no longer imports the function, patching the definition is the correct approach.
- **Files modified:** tests/test_eval_worker_endpoints.py
- **Commit:** ab47e283

**2. [Rule 2 - Auto-add] Stale SHIP-02 comment updated**

- **Found during:** Task 1 GREEN phase
- **Issue:** Comment at `_classify_and_fill_oracle` call site still referenced the Phase-142 `_run_multipv2_pass` fix (SHIP-02), which is no longer accurate after Phase 146 makes `blob_map={}` unconditional.
- **Fix:** Updated comment to describe Phase 146 D-03 behavior (gate always skipped, blobs deferred to tier-4 drain).
- **Files modified:** app/routers/eval_remote.py
- **Commit:** ab47e283

## Known Stubs

None. All changes are complete functional implementations with no placeholders.

## Threat Flags

No new threat surface introduced. The `:recency_window` bound-param convention follows the existing eval_queue_service security pattern. `SubmitEval` schema narrowing is backward-compatible (no `extra='forbid'`).

## Self-Check: PASSED
