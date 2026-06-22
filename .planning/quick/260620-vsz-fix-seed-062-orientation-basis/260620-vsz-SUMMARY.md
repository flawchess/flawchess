---
quick_id: 260620-vsz
slug: fix-seed-062-orientation-basis
description: "Fix SEED-062 — tactic-comparison family narrowing inherits orientation=allowed"
status: complete
date: 2026-06-20
commit: 5932206f
---

# Quick Task 260620-vsz — SUMMARY

## What changed

The tactic-comparison endpoint (`get_tactic_comparison`) now narrows its game
population on `orientation="either"` instead of inheriting `apply_game_filters`'
`"allowed"` default. The grid renders both missed and allowed bullets, so the
population must include games with a family-X tactic in either column — otherwise a
game whose only fork was missed-only was silently dropped, biasing the Missed
bullets and the `analyzed_n` gate denominator.

Plumbing:
- `_filtered_games_base` (library_repository.py): new `tactic_orientation` param
  threaded into `apply_game_filters(orientation=...)`.
- `count_filtered_and_analyzed`: new `tactic_filter_orientation` param → base.
- `fetch_tactic_comparison`: new `tactic_filter_orientation` param → base, kept
  distinct from the existing `orientation` (which selects the COUNT column set).
- `get_tactic_comparison` (library_service.py): adds `tactic_filter_orientation="either"`
  to `_filter_kwargs`, so it flows to the gate and both fetches in one place.

Defaults stay `"allowed"`, so the other `count_filtered_and_analyzed` callers (flaw
comparison, coverage badge — none pass tactic_families) are byte-for-byte unchanged.

## Test

Added `TestAnalyzedDenominator::test_tactic_filter_orientation_either_includes_missed_only_game`
(`tests/test_library_repository.py`): seeds an analyzed game with a MISSED-only fork
and asserts the gate count is 0 under `"allowed"` but 1 under `"either"` — proving
the basis is threaded and the missed-only game joins the population. Self-validating
(both branches asserted in one run).

## Verification

- `uv run ty check app/repositories/library_repository.py app/services/library_service.py` → clean.
- `uv run ruff format/check` on touched files → clean.
- `uv run pytest tests/test_library_repository.py tests/services/test_tactic_comparison_service.py tests/routers/test_library_tactic_comparison.py tests/services/test_library_service.py tests/test_query_utils.py -n auto` → 102 passed.

## Notes

- Interacts cleanly with SEED-060 (player gate) and SEED-061 (confidence gate): the
  "either" base filter now also player-scopes and confidence-gates the population,
  which is correct for a you-vs-opponent grid keyed on the user's own tactics.
- SEED-062 seed moved to `.planning/seeds/closed/`.

## Commit

- `5932206f` fix(library): tactic-comparison narrows population on 'either' (SEED-062)
