---
id: 260512-ogh
type: quick
status: complete
created: 2026-05-12
completed: 2026-05-12
branch: simplify-opening-insights
---

# Quick Task Summary: Fix MIN/MIN sample-pair transposition bug in opening_insights flat query

## What changed

`query_opening_transitions` (PR #90 refactor) emitted two independent aggregates as a sample pointer:

```python
func.min(GamePosition.game_id).label("sample_game_id"),
func.min(GamePosition.ply).label("sample_ply"),
```

Independent MINs de-correlate when the same `entry_hash` is reached at different plies via transposition (polyglot Zobrist ignores half-move clock, so e.g. `Nf3 Nf6 Ng1 Ng8 e4 e5` returns to the same hash as `e4 e5` at a deeper ply). The "sample" `(game_id, ply)` could refer to no real row — silently breaking the prefix replay in `_wrap_transition_row` (either a wrong `resulting_full_hash` or a false "custom-FEN drop" Sentry capture).

Fix: pair the aggregate into a single PostgreSQL `ARRAY[ply, game_id]`, then `MIN()` is lexicographic over arrays — the minimum array IS one of the input arrays, so the pair always refers to a real row in the group. Order `[ply, game_id]` keeps the shallowest reachable prefix as the sample (game_id breaks ties).

## Files touched

- `app/repositories/openings_repository.py` — replaced two `MIN()`s with `MIN(pg_array([ply, game_id]))` labeled `sample_pair`; updated docstring.
- `app/services/opening_insights_service.py` — unpack `(ply, game_id)` from `raw_row.sample_pair` in `_wrap_transition_row` and `_collect_attribution_hashes`; updated `_TransitionRow` docstring.
- `tests/repositories/test_opening_insights_repository.py`:
  - Renamed `test_query_returns_sample_game_id_and_ply` → `test_query_returns_sample_pair`; asserts on `row.sample_pair` unpacking.
  - Updated `test_query_handles_custom_fen_ply0_gracefully` to read `sample_pair`.
  - Updated structural guardrail snapshot (`test_query_compiles_to_flat_aggregation`) to mirror the real query shape.
  - **New regression test** `test_sample_pair_correlated_under_transposition`: seeds 10 deep-ply games first (smaller game_ids) and 10 shallow-ply games second (larger game_ids) at the same `entry_hash`, then asserts `sample_pair` lands in the shallow batch and the helper's prefix replay reaches the entry position. Under the broken MIN/MIN shape, `MIN(game_id)` would land in the deep batch while `MIN(ply)=2`, de-correlating and failing the assertion.
- `tests/services/test_opening_insights_service.py` — `_make_row` and the Sentry-drop test now build mock rows with `sample_pair=[ply, game_id]`.

## Validation

- `uv run ruff check app/ tests/` — clean.
- `uv run ty check app/ tests/` — clean.
- Targeted: `pytest tests/repositories/test_opening_insights_repository.py tests/services/test_opening_insights_service.py` — **63 passed**.
- Full: `uv run pytest` — **1386 passed**, 6 skipped (was 1385 — the new transposition test adds one).

## Notes

- The `ARRAY[...]` constructor is distinct from `ARRAY_AGG(...)`. The structural guardrail (which forbids `WITH `, `LEAD(`, `ARRAY_AGG`) still passes.
- No SQL plan regression expected — `min(ARRAY[a,b])` is a plain scalar aggregate, not a window function.
- The drop-path Sentry comment in `_wrap_transition_row` still refers to "custom-FEN survivor"; with this fix, false drops from transposition mismatches no longer pollute that signal.
