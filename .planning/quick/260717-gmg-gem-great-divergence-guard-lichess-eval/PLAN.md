---
slug: gem-great-divergence-guard-lichess-eval
created: 2026-07-17
---

# Guard gem/great badges against best_cp vs imported-eval divergence

## Problem

For lichess-eval games, `game_positions.eval_cp` preserves lichess's imported
`%eval` (the eval graph), while `game_best_moves.best_cp` and `best_move` come
from *our* Stockfish (1M nodes). When our shallow search overrates a sharp line,
it can pick a "best move" and eval that both disagree with the deeper lichess
eval sitting in the same row — producing a spurious gem/great badge.

Concrete case: game 640125, 55.Qc6+ (ply 108). Our `best_cp = -82` (−0.82) →
classified **great**, but lichess's preserved post-move `eval_cp = -246` (−2.46)
and the live board (≈−2.2) agree the move is much worse, and prefer Qh8+.

## Guard

Query-time (retroactive, zero re-analysis — matches GEMS-07 philosophy), scoped
to lichess-eval games only (engine games use one engine for both surfaces, so the
guard is noise there). Directional, expected-score space: suppress a would-be
gem/great when *our* best-move expected score exceeds the imported post-move
expected score (mover POV) by more than `BEST_MOVE_DIVERGENCE_MAX_ES = 0.10`.

## Changes

1. `app/services/best_move_candidates.py`
   - Add `BEST_MOVE_DIVERGENCE_MAX_ES = 0.10` constant.
   - `classify_best_move`: add `post_move_cp`, `post_move_mate`,
     `is_lichess_eval_game` params (default off); suppress → "neither" on
     optimistic divergence.
   - `best_move_tier_sql`: mirror the guard in the SQL twin (new cols +
     `is_lichess` flag) so board and Library filter stay consistent (D-03b).
2. `app/services/library_service.py`: pass `pos.eval_cp`, `pos.eval_mate`,
   `game.lichess_evals_at is not None` into `classify_best_move` (already in scope).
3. `app/repositories/library_repository.py`: join `GamePosition` into the
   `best_move_exists_from_table` EXISTS on (game_id, ply, user_id); pass the
   post-move eval cols + lichess flag to `best_move_tier_sql`.
4. Tests: unit tests for the Python guard + a SQL-twin guard-agreement test.
5. CHANGELOG bullet under [Unreleased] > Fixed.

## Verification

- Guard fires for the 640125 shape (best −0.82 vs post-move −2.46, lichess) → neither.
- Guard is a no-op when `is_lichess_eval_game=False` or divergence ≤ threshold,
  or when our eval is *pessimistic* vs the imported eval.
- SQL twin agrees with Python under the guard.
- Full backend gate green.
