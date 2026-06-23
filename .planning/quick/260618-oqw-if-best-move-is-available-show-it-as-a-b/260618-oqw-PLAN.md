---
quick_id: 260618-oqw
title: Best-move blue arrow in Game and Flaw card miniboards
status: in-progress
date: 2026-06-18
---

# Quick Task 260618-oqw

**Description:** If `best_move` is available, show it as a blue transparent arrow in the Game and Flaw card miniboards. It should update when showing different positions of a game in the game card.

## Scope decision

"Game card" = `LibraryGameCard` (Library → Games subtab), the only game card that
scrubs through positions (via eval-chart hover) and carries per-ply eval data. The
static `results/GameCard.tsx` shows only `result_fen` with no eval/best_move payload,
so it is out of scope. "Flaw card" = `FlawCard` (Library → Flaws subtab).

## Data semantics (verified against zobrist.py / game_position.py)

- `game_positions.best_move` (UCI, e.g. `e2e4` / `e7e8q`) is a property of the
  **pre-move position** at that ply — the engine's best move FROM that board. NULL
  for lichess-eval-only games (no PV) → "if available" gate.
- `LibraryGameCard`: scrubbed board `perPly[activePly]` is the position at game-ply
  `activePly+1`. Best move FROM the displayed board = `eval_series[ply==activePly+1].best_move`.
- `FlawCard`: `flaw.fen` is the pre-flaw decision point at ply N; best move from it =
  `PositionAt(ply=N).best_move` = `flaw.best_move`.

## Tasks

1. **Backend schemas** (`app/schemas/library.py`): add `best_move: str | None = None`
   to `EvalPoint` and `FlawListItem`.
2. **Backend populate**:
   - `app/services/library_service.py` `_build_eval_series`: `best_move=pos.best_move`.
   - `app/repositories/library_repository.py` `query_flaws`: `best_move=pos_at.best_move if pos_at else None`.
3. **Frontend types** (`frontend/src/types/library.ts`): add `best_move: string | null`
   to `EvalPoint` and `FlawListItem`.
4. **Frontend rendering**:
   - `theme.ts`: add `BEST_MOVE_ARROW` (blue, transparent).
   - `sanToSquares.ts`: add `uciToSquares(uci)` helper (slice from/to).
   - `LibraryGameCard.tsx`: per-scrubbed-ply best-move arrow (mobile + desktop boards).
   - `FlawCard.tsx`: best-move arrow alongside the flaw-move arrow.
5. **Tests**: update `FlawCard.test.tsx` `makeFlaw` fixture + `useLibraryGame.test.tsx`
   fixture for the new required TS field; add coverage for the best-move arrow.

## Verify

- `uv run ruff format/check`, `uv run ty check app/ tests/`, `uv run pytest -n auto`
- `frontend`: `npx tsc -b`, `npm run lint`, `npm test -- --run`, `npm run knip`
