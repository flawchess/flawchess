---
quick_id: 260512-6zn
slug: simplify-opening-insights
status: complete
branch: simplify-opening-insights
date: 2026-05-12
---

# Quick Task 260512-6zn: simplify-opening-insights — Summary

## Outcome

Refactored `query_opening_transitions` from a multi-layered CTE/window/subquery composition into a flat `SELECT … GROUP BY … HAVING`. Moved `entry_san_sequence` resolution and `resulting_full_hash` derivation out of SQL into the Python service layer. Eliminates the structural complexity that caused the planner-misestimate cascade fixed in `.planning/debug/opening-insights-timeout-u84.md` (Alembic migration `e925558020b9` stays as belt-and-suspenders).

## Commits

| SHA | Message |
|---|---|
| `3a8a5748` | refactor(openings): flatten query_opening_transitions, add query_transition_prefixes helper |
| `91fc1915` | refactor(opening-insights): derive entry_san_sequence + resulting_full_hash in Python service layer |
| `101bc377` | test(opening-insights): cover flat query shape, prefix helper, and custom-FEN drop path |
| `2378e4c4` | chore: merge quick task worktree |

## Verification

- `uv run ruff check app/ tests/` — passed
- `uv run ty check app/ tests/` — passed
- `uv run pytest` — 1385 passed, 6 skipped
- Targeted: `tests/repositories/test_opening_insights_repository.py` + `tests/services/test_opening_insights_service.py` — 62 passed

## Key changes

- `app/repositories/openings_repository.py`
  - `query_opening_transitions`: flat aggregation. No CTE, no `LEAD()`, no `array_agg() OVER`, no standard-start subquery. Return Row shape changed: drops `entry_san_sequence` + `resulting_full_hash`, adds `sample_game_id` + `sample_ply` for downstream prefix lookup.
  - New `query_transition_prefixes(session, user_id, samples)`: batch-resolves the SAN prefix path for surviving findings via one `WHERE user_id=? AND game_id = ANY(...) AND ply < ?` query.
- `app/services/opening_insights_service.py`
  - New `_TransitionRow` dataclass + `_signed_full_hash` helper + `_wrap_transition_row` that replays the prefix via `_replay_san_sequence`, pushes the candidate `move_san`, and derives `resulting_full_hash` deterministically.
  - Replay wrapped in `try/except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError, AssertionError)` with `sentry_sdk.capture_exception(tag=source="opening_insights")` and finding dropped — handles the ~0.05% custom-FEN survivors (chess.com thematic tournaments and custom-position "Let's Play!" games) without crashing.
- Tests: new structural guardrail (compiled SQL must not contain `WITH `, `LEAD(`, `array_agg`) + prefix-helper coverage + custom-FEN drop-path assertion.

## Misattribution corrected

The old comment claimed the standard-start filter protected against "chess.com themed events / puzzles". Verified against prod data: the 176 affected ply-0 rows (out of 344,013) come from chess.com **thematic tournament games** (Benko Gambit round 1, etc.) and **custom-position "Let's Play!" games** — rated, real opponents, `rules: chess`. They pass the variant filter at import because they are standard rules from a custom FEN. Comment corrected accordingly.

## Out of scope (deliberate)

- `ix_gp_user_game_ply` partial index — kept as-is. Could be slimmed in a follow-up after observing the new plan on prod.
- Extended-statistics migration `e925558020b9` — kept as belt-and-suspenders. Negligible cost.
- `STARTING_POSITION_HASH` constant — kept (still used as a sanity reference). Comment notes it is no longer load-bearing in the query.

## Next steps

- Push `simplify-opening-insights` branch and open a PR for review.
- Verify on prod via tunneled EXPLAIN ANALYZE after deploy — expect identical or better plan vs the post-stats baseline (36ms for user 84).
