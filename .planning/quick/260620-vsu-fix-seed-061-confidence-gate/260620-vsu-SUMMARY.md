---
quick_id: 260620-vsu
slug: fix-seed-061-confidence-gate
description: "Fix SEED-061 — Games-tab tactic filter omits the chip-confidence gate"
status: complete
date: 2026-06-20
commit: aa529fda
---

# Quick Task 260620-vsu — SUMMARY

## What changed

Added `& (conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN)` to each orientation branch of
the Games-tab tactic-family EXISTS in `apply_game_filters`
(`app/repositories/query_utils.py`), and imported `_TACTIC_CHIP_CONFIDENCE_MIN` from
`library_repository`. The Games filter now matches only tactics that would actually
render a chip (confidence >= 70), aligning it with `build_flaw_filter_clauses`
(Flaws list) and the chip-display threshold.

## Decision (user)

Asked the user because the same EXISTS had a deliberate Phase 129 test
(`test_no_confidence_gate_in_exists_site`) and a "Pitfall 3" comment preserving the
no-gate behavior. The user chose **Add the gate (align)**. The asymmetry was
incidental, not principled (Pitfall 3 itself said "keep intentional OR fix
deliberately"), and code review WR-02 flagged it for explicit decision.

## Tests

- Reversed the unit test → `test_confidence_gate_present_in_exists_site`
  (`tests/test_query_utils.py`): asserts `tactic_confidence` IS in the compiled SQL
  for all three orientations.
- Added behavioral test `test_tactic_filter_excludes_below_confidence_tactic`
  (`tests/test_library_repository.py`): a fork at the threshold matches; a fork one
  point below is excluded.
- Updated two stale "no confidence gate" docstrings.

## Verification

- `uv run ty check app/repositories/query_utils.py` → clean.
- `uv run pytest tests/test_library_repository.py tests/test_query_utils.py tests/routers/test_library_tactic_comparison.py tests/services/test_tactic_comparison_service.py -n auto` → 75 passed (also ran flaw_predicate + library_router earlier, green).

## Notes

- Builds on SEED-060's player gate (same EXISTS, prior commit 5eff5f56).
- SEED-062 (comparison orientation basis) remains open — next.
- SEED-061 seed moved to `.planning/seeds/closed/`.

## Commit

- `aa529fda` fix(library): gate Games-tab tactic filter on chip confidence (SEED-061)
