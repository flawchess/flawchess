---
id: 260512-ogh
type: quick
status: in-progress
created: 2026-05-12
branch: simplify-opening-insights
---

# Quick Task: Fix MIN/MIN sample-pair transposition bug in opening_insights flat query

## Context

PR #90 (simplify-opening-insights) refactors `query_opening_transitions` from a CTE+window-function shape to a flat `SELECT … GROUP BY … HAVING`. The new query emits two independent aggregates as a "sample pointer" for downstream prefix lookup:

```python
func.min(GamePosition.game_id).label("sample_game_id"),
func.min(GamePosition.ply).label("sample_ply"),
```

The PR comment claims "all games with the same (entry_hash, move_san) share the same prefix path" — that is **wrong**. The same `entry_hash` (a Zobrist hash of a position) can be reached at different plies in different games via transposition (e.g. `1.e4 c5 2.Nf3` vs `1.Nf3 c5 2.e4`).

When that happens, `MIN(game_id)` and `MIN(ply)` are independent aggregates and de-correlate:
- Game 5 reaches position H at ply 8
- Game 10 reaches position H at ply 6
- `sample_game_id=5, sample_ply=6` — but game 5 at ply 6 is **not** the entry position
- `query_transition_prefixes` returns game 5's first 6 moves
- `_wrap_transition_row` replays that wrong prefix → either silent corruption of `resulting_full_hash` (if `move_san` is coincidentally legal) or a false "custom-FEN drop" Sentry capture.

## Fix

Replace the two independent aggregates with a single paired aggregate so the sample `(ply, game_id)` always comes from one real row in the group:

```python
func.min(pg_array([GamePosition.ply, GamePosition.game_id])).label("sample_pair")
```

`min(ARRAY[ply, game_id])` is lexicographic over the array, so the minimum array IS one of the input arrays (i.e. belongs to a real row). Unpacked in the service layer as `sample_ply, sample_game_id = row.sample_pair`.

This compiles to `min(ARRAY[…])` — the `ARRAY[…]` constructor is distinct from `ARRAY_AGG(…)`, so the structural guardrail test (which forbids `ARRAY_AGG`) still passes.

## Acceptance

- [x] `query_opening_transitions` emits a single `sample_pair` instead of two independent `MIN` aggregates.
- [x] Service layer unpacks `(ply, game_id)` from `sample_pair`.
- [x] New regression test: same user, two games that reach the same entry position at different plies via transposition; assert the sample pair maps to a prefix whose replay reproduces the entry position (no false drop, no wrong `resulting_full_hash`).
- [x] Existing tests still pass.
- [x] ruff + ty clean.
- [x] Branch pushed to `origin/simplify-opening-insights`.

## Out of scope

- Performance of the new shape on prod (still confined to the post-merge EXPLAIN ANALYZE checklist item in the PR description).
- `STARTING_POSITION_HASH` cleanup.
- Refactoring `query_transition_prefixes` itself (signature unchanged).
