---
slug: gem-great-divergence-guard-lichess-eval
status: complete
completed: 2026-07-17
---

# Summary

Added a query-time guard that suppresses gem/great badges on lichess-eval games
when our own best-move engine's eval is materially more optimistic than the
imported lichess post-move eval for the same resulting position.

## Root cause (recap)

For a lichess-eval game, `game_positions.eval_cp` preserves lichess's imported
`%eval`, while `game_best_moves.best_cp` / `best_move` come from our Stockfish
(1M nodes). When our shallow search overrated a sharp line it could pick a best
move + eval both engines-of-record (lichess, live board) disagree with, yielding
a spurious badge. Verified on game 640125, 55.Qc6+ (our −0.82 vs lichess −2.46).

## Change

- **`app/services/best_move_candidates.py`**: new `BEST_MOVE_DIVERGENCE_MAX_ES =
  0.10` constant; `classify_best_move` and its SQL twin `best_move_tier_sql` gain
  optional post-move-eval + `is_lichess_eval` params and drop a would-be
  gem/great when (mover-POV) `best_es − post_move_es > 0.10`. Directional
  (optimistic only), scoped to lichess-eval games, fails open on missing eval.
- **`app/services/library_service.py`** (board): passes `pos.eval_cp/eval_mate`
  and `game.lichess_evals_at is not None` (both already in scope).
- **`app/repositories/library_repository.py`** (Library filter): LEFT-joins the
  candidate ply's `game_positions` row into the `best_move_exists_from_table`
  EXISTS so the SQL guard mirrors the board (D-03b). LEFT join → fail-open.
- **Tests**: 8 Python guard cases (incl. the 640125 shape + black-mover POV), a
  parametrized SQL-twin guard-agreement test, and 2 end-to-end repository tests
  (guard fires for a divergent lichess gem; no-op for engine games).
- **CHANGELOG**: `[Unreleased] > Fixed` bullet.

## Design decisions

1. **Query-time, not write-time** — retroactive (fixes existing badges with zero
   re-analysis), matching the module's "a retune reclassifies the corpus for
   free" philosophy.
2. **Scoped to lichess-eval games** — engine games feed both surfaces from one
   engine, so the guard would be noise there.
3. **Directional, expected-score space, threshold 0.10** — a "mistake's worth" of
   optimism. Retunable via one constant (zero re-analysis).

## Verification

- `uv run ty check app/ tests/` — clean.
- `uv run pytest -n auto` — 3439 passed, 18 skipped.
- Guard-firing tests fail-open on any broken link (join/flag/col), so their
  passing proves the whole chain suppresses the divergent case.

## Follow-up (not done)

- The threshold 0.10 was picked by reasoning, not a DB-wide sweep. A quick query
  of how many existing lichess-eval gem/great badges the guard now flips would
  confirm it's neither too aggressive nor too lax (offered to the user).
- Frontend live-fallback path (`gemMove.ts`) is unchanged — it recomputes on the
  live board and has no imported lichess eval to compare against, so it's out of
  scope for this guard.
