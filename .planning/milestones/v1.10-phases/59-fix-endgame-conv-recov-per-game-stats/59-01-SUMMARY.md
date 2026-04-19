---
phase: 59-fix-endgame-conv-recov-per-game-stats
plan: 01
subsystem: endgame-analytics
tags: [backend, endgame, tests, bugfix]
dependency_graph:
  requires:
    - app/services/endgame_service.py::_compute_score_gap_material (Phase 53)
    - app/schemas/endgames.py::ScoreGapMaterialResponse (Phase 53)
  provides:
    - "Invariant: sum(material_rows[i].games) == endgame_wdl.total"
    - "Deterministic group-then-pick dedupe with conversion-over-recovery tiebreak"
    - "NULL imbalance rows bucketed as 'even' instead of dropped"
  affects:
    - "GET /api/endgames/performance — material_rows.games counts now sum to endgame_wdl.total"
tech-stack:
  added: []
  patterns:
    - "Group-then-pick per-game span selection with explicit priority passes"
key-files:
  created: []
  modified:
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
decisions:
  - "NULL imbalance → 'even' bucket (Phase 59 Decision 1)"
  - "Conversion-over-recovery tiebreak when both spans qualify (Phase 59 Decision 2)"
  - "Even-fallback selection picks lowest endgame_class_int for determinism"
  - "Inherit TestScoreGapMaterialInvariant from TestScoreGapMaterial to reuse _make_wdl helpers (minimal duplication)"
metrics:
  duration: ~12 minutes
  completed: 2026-04-13
  tasks: 2
  files: 2
  commits: 2
---

# Phase 59 Plan 01: Fix per-game bucket invariant in score-gap material breakdown — Summary

Replace the per-row "first-seen + skip NULL" loop in `_compute_score_gap_material` with a group-then-pick algorithm that routes every endgame game into exactly one of conversion/even/recovery, restoring the invariant `sum(material_rows.games) == endgame_wdl.total` for any filter combination.

## What Changed

### `app/services/endgame_service.py`

Rewrote the dedupe + bucketing loop inside `_compute_score_gap_material` (lines ~531-595 in the new layout):

1. Build `rows_by_game: dict[int, list[Sequence[Any]]]` from `entry_rows` (one bucket per game_id).
2. For each game, run three priority passes:
   - Pass 1: any row with both `imb >= +threshold` and `imb_after >= +threshold` → bucket as `conversion`.
   - Pass 2 (only if no conversion match): any row with both `imb <= -threshold` and `imb_after <= -threshold` → bucket as `recovery`.
   - Pass 3 (fallback): pick the row with the lowest `endgame_class_int` for deterministic output → bucket as `even`.
3. NULL `user_material_imbalance` and NULL `user_material_imbalance_after` cannot satisfy passes 1 or 2 — they fall through to pass 3 and the game is bucketed as `even` (vs. previously dropped).
4. `seen_game_ids: set[int]` removed (no longer needed; iteration is over `rows_by_game.items()`).

The conversion-over-recovery tiebreak rationale ("reaching a winning position is the earlier causal event") is documented inline at the top of the new loop.

### `tests/test_endgame_service.py`

- Renamed `test_score_gap_material_none_imbalance_excluded` → `test_score_gap_material_none_imbalance_bucketed_as_even` and inverted its assertion (NULL row now lands in `material_rows[1]` with `games == 1`).
- Added new `class TestScoreGapMaterialInvariant(TestScoreGapMaterial)` with 8 invariant-focused tests:
  1. `test_invariant_single_span_each_bucket`
  2. `test_invariant_multi_span_conversion_over_recovery`
  3. `test_invariant_multi_span_null_then_qualifying`
  4. `test_invariant_null_imbalance_lands_in_even`
  5. `test_invariant_null_after_lands_in_even`
  6. `test_invariant_empty_input_no_divide_by_zero`
  7. `test_invariant_mixed_10_games`
  8. `test_invariant_deterministic_ordering`

Inheritance reuses `_make_wdl`/`_make_wdl_pct` helpers from the parent class without duplication.

## Verification

- `uv run ty check app/ tests/` → All checks passed (0 errors).
- `uv run pytest tests/test_endgame_service.py::TestScoreGapMaterial tests/test_endgame_service.py::TestScoreGapMaterialInvariant -v` → 42 passed (17 in parent class, 17 inherited + 8 new in subclass; 0 failed).
- `grep -n "seen_game_ids" app/services/endgame_service.py` → 0 matches in `_compute_score_gap_material` body (variable removed).
- `grep -n "if user_material_imbalance is None:" app/services/endgame_service.py` → 0 matches (NULL-skip removed).
- `grep -in "Conversion-over-recovery" app/services/endgame_service.py` → 1 match (line 542, documentation comment).
- `grep -n "rows_by_game" app/services/endgame_service.py` → 3 matches (declaration + assignment + iteration).
- `grep -cn "test_invariant_" tests/test_endgame_service.py` → 8 (one per new invariant test).

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite `_compute_score_gap_material` with group-then-pick dedupe | `981c33b` | `app/services/endgame_service.py` |
| 2 | Update existing test + add `TestScoreGapMaterialInvariant` (8 tests) | `2e12c0c` | `tests/test_endgame_service.py` |

## Deviations from Plan

None — plan executed exactly as written. The acceptance-criteria grep for `conversion-over-recovery` was case-sensitive in the plan but the inline doc comment uses the capitalized "Conversion-over-recovery" at the start of a sentence; verified with case-insensitive grep, semantically equivalent.

## Authentication Gates

None.

## Known Stubs

None.

## Out-of-Scope Discoveries

`uv run ruff check app/services/endgame_service.py` reports 2 pre-existing errors at lines 867-869 (unused locals `time_control_seconds` and `termination` in an unrelated function). Confirmed pre-existing via baseline `git stash` check before any edits. Left untouched per scope rule (out of scope for this plan; will be picked up by Plan 59-02 or 59-03 if those touch surrounding code).

## Self-Check: PASSED

- `app/services/endgame_service.py` — present (modified, 2 commits include it)
- `tests/test_endgame_service.py` — present (modified)
- Commit `981c33b` — found in `git log`
- Commit `2e12c0c` — found in `git log`
- All 42 targeted tests pass
- `ty` clean
