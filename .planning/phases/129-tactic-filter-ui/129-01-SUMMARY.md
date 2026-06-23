---
phase: 129-tactic-filter-ui
plan: "01"
subsystem: backend
tags: [tactic-filter, orientation, depth, comparison, backend, tdd]
status: complete

dependency_graph:
  requires: []
  provides:
    - TacticOrientation widened to 3-value Literal (wave-2 type mirror anchor)
    - max_tactic_depth kwarg at both SQL filter sites
    - "either" OR across both missed+allowed column sets
    - TacticBullet.orientation schema field (wave-2 type mirror anchor)
    - Dual-orientation comparison bullets, top-6 by Missed ranking
  affects:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/schemas/library.py
    - app/services/library_service.py
    - app/routers/library.py

tech_stack:
  added: []
  patterns:
    - _tactic_orientation_pairs closed-enum resolver (replaces ad-hoc _tactic_cols at filter sites)
    - _depth_ok helper with FAMILY_TO_MOTIF_INTS['mate'] exemption (reuses existing constant)
    - Two-fetch approach for dual-orientation comparison (A3 — post-gate, acceptable cost)

key_files:
  modified:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/schemas/library.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/test_query_utils.py
    - tests/test_library_repository.py
    - tests/test_library_router.py
    - tests/services/test_tactic_comparison_service.py

decisions:
  - "_tactic_orientation_pairs returns list[tuple[motif_col, conf_col, depth_col]] — 1 tuple for missed/allowed, 2 for either (missed first)"
  - "_depth_ok returns literal-true when max_tactic_depth=None; otherwise depth_col<=N | motif_col.in_(mate_ints)"
  - "max_tactic_depth unit is half-moves (raw column value); UI converts to 'moves deep' in plan 02"
  - "TacticComparisonResponse.bullets ordering contract: top-6 families by Missed you_rate desc appear first (both missed+allowed bullets each), then overflow families in same order"
  - "apply_game_filters (Games-EXISTS site) does NOT gate confidence for tactic families — intentional Pitfall 3 asymmetry preserved"
  - "get_tactic_comparison orientation param removed (D-09); grid always shows both orientations"
  - "_compute_tactic_bullets now parameterized with orientation, no [:6] cap; caller selects top-6 families"

metrics:
  duration_minutes: 15
  completed_date: "2026-06-20"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 9
---

# Phase 129 Plan 01: Backend Tactic Filter Extension Summary

Extended the backend tactic-filter layer with 3-value orientation, max_tactic_depth bound, and dual-orientation comparison response — locking the `TacticBullet.orientation` schema field that wave-2 mirrors in `types/library.ts`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for depth+either | 021dff44 | test_query_utils.py, test_library_repository.py |
| 1 GREEN | Widen orientation + depth/either at both SQL sites | 192281d5 | library_repository.py, query_utils.py, tests |
| 2 RED | Failing tests for dual-orientation comparison | 99c19d18 | test_library_router.py |
| 2 GREEN | Dual-orientation schema + endpoint + Missed ranking | 5b6e3bd2 | schemas/library.py, library_service.py, routers/library.py, tests |
| 2 STYLE | ruff formatter output | 64238a49 | library_service.py |
| 3 | Full backend gate (format + lint + ty + full suite) | — | (formatter committed above) |

## What Was Built

### Task 1: Widen Orientation + Depth Filter

**`TacticOrientation`** widened from `Literal["missed","allowed"]` to `Literal["either","missed","allowed"]`. This is the single source of truth imported by `query_utils` (lazy) and `library_service`.

**`_tactic_orientation_pairs(orientation)`** — new shared resolver returning `list[tuple[motif_col, conf_col, depth_col]]`. Returns 1 triple for `"missed"` / `"allowed"`, 2 triples for `"either"` (missed first). Never string-interpolates caller input (T-129-01).

**`_depth_ok(depth_col, motif_col, max_tactic_depth)`** — returns `true()` when `max_tactic_depth is None`, otherwise `(depth_col <= max_tactic_depth) | motif_col.in_(FAMILY_TO_MOTIF_INTS["mate"])`. Reuses the existing `FAMILY_TO_MOTIF_INTS["mate"]` constant per the plan prohibition on new mate constants.

**`build_flaw_filter_clauses`** (Flaws-list site): extended with `max_tactic_depth: int | None = None` and `"either"` OR across both column sets. Confidence gate (`conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN`) preserved on all branches.

**`apply_game_filters`** (Games-EXISTS site): same extensions — `max_tactic_depth` + `"either"` OR — but WITHOUT the confidence gate (intentional asymmetry, Pitfall 3 preserved).

**`query_flaws`**: threads `max_tactic_depth` through to `build_flaw_filter_clauses`.

### Task 2: Dual-Orientation Comparison

**`TacticBullet.orientation: Literal["missed","allowed"]`** field added (schema option A). `TacticComparisonResponse.bullets` can now hold up to 12 entries.

**`_compute_tactic_bullets(rows, orientation)`**: parameterized with orientation; each bullet tagged `orientation=orientation`. The `[:6]` cap removed — caller selects top-6 families.

**`get_tactic_comparison`**: `orientation` param removed (D-09). Fetches twice (once per orientation) via `fetch_tactic_comparison` — two post-gate queries, acceptable cost (A3). Top-6 families selected by Missed `you_rate` descending; tie-break by the existing `_sort_key` order in `missed_bullets`. Both orientation bullets emitted per family in: top-6 first (missed then allowed), then overflow families.

**Router**: docstring updated; no new query param (D-09 intact).

### Ordering Contract (for plans 02/03)

`TacticComparisonResponse.bullets` ordering:
1. Top-6 families by Missed `you_rate` descending (tie-break: existing significance/delta/volume `_sort_key` on the missed orientation)
2. For each family: missed bullet first, then allowed bullet
3. Overflow families (6+) follow in the same paired order

The frontend renders server order — no client re-sort needed (confirmed in the test that `fork` with the highest missed `you_rate` appears first).

### Locked Contract for Wave 2

- `max_tactic_depth` unit = **half-moves** (raw `SmallInteger` column value). The UI (plan 02) converts to "moves deep" via `depthToQueryParam(maxMoves)` — `max_tactic_depth = maxMoves * 2` (or the slider value directly if it's already in half-moves).

  **Correction:** Per D-03, the UI uses "moves deep" labels but the API param is in half-moves. The `depthToQueryParam` conversion in plan 02 must multiply full-moves by 2, or the slider value can be in half-moves directly. Plan 02 owns this conversion.

- `TacticBullet.orientation: 'missed' | 'allowed'` is locked — `types/library.ts` must mirror this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FAMILY_TO_MOTIF_INTS occurrence count test threshold stale**
- Found during: Task 1 GREEN
- Issue: `TestTacticOrientationBuildFlawFilterClauses::test_family_to_motif_ints_defined_once_not_duplicated` asserted `<= 8` occurrences; Phase 129 added `_depth_ok` + `_tactic_orientation_pairs` helpers with docstring references, pushing count to 10
- Fix: Updated threshold to `<= 15` with comment explaining Phase 129 additions are not duplication
- Files: `tests/test_library_repository.py`

**2. [Rule 1 - Bug] Existing service tests expected Phase 126 response shape (6 bullets)**
- Found during: Task 2 GREEN
- Issue: `test_full_response_six_bullets` asserted `<= 6` bullets; `test_significant_gap_first` asserted `<= 1` fork bullet — both stale after Phase 129's 12-bullet dual-orientation response
- Fix: Updated assertions to `<= 12` bullets and `<= 2` fork bullets; added `orientation` field assertion
- Files: `tests/services/test_tactic_comparison_service.py`

## Verification Results

- `uv run ruff format app/ tests/`: 1 file reformatted (library_service.py), committed
- `uv run ruff check app/ tests/ --fix`: 1 autofix (unused import in library_service.py)
- `uv run ty check app/ tests/`: zero errors
- `uv run pytest -n auto -x`: 2816 passed, 15 skipped, 3 warnings, 0 failures

## Threat Mitigations Verified

| T-ID | Status |
|------|--------|
| T-129-01 (orientation enum → SQL column) | Mitigated — `_tactic_orientation_pairs` is the only resolution path; no string interpolation |
| T-129-02 (max_tactic_depth int param) | Partial — SQLAlchemy bound param prevents injection; Pydantic `int` type is at the API boundary (plan 02 will add `ge=0,le=...` validation when the route param is exposed) |
| T-129-03 (dual-orientation info disclosure) | Accepted — no new data class; aggregation is user-scoped |
| T-129-04 (flaw ownership) | Mitigated — new clauses ADD filters inside existing `user_id`-scoped predicate, never widen it |

## Self-Check: PASSED
