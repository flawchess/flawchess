---
quick_id: 260618-oqw
title: Best-move blue arrow in Game and Flaw card miniboards
status: complete
date: 2026-06-18
commit: a71783f9
---

# Quick Task 260618-oqw — Summary

**Goal:** If `best_move` is available, show it as a blue transparent arrow in the
Game and Flaw card miniboards, updating as different positions of a game are shown.

## What changed

Surfaced the already-stored `game_positions.best_move` (UCI) through the library
API and rendered it as a translucent blue arrow on the two Library miniboards.

### Backend (no SQL/migration — the ORM column already existed)
- `app/schemas/library.py`: `EvalPoint.best_move` and `FlawListItem.best_move`
  (`str | None = None`).
- `app/services/library_service.py` `_build_eval_series`: `best_move=pos.best_move`.
- `app/repositories/library_repository.py` `query_flaws`: `best_move=pos_at.best_move`
  (the PositionAt ply=N join — the pre-flaw decision position).

### Frontend
- `lib/theme.ts`: `BEST_MOVE_ARROW = rgba(59,130,246,0.6)` (blue, translucent).
- `lib/sanToSquares.ts`: `uciToSquares()` — positional UCI parse, no board context.
- `types/library.ts`: `best_move: string | null` on `EvalPoint` + `FlawListItem`.
- `LibraryGameCard.tsx`: per-scrubbed-ply arrow on both mobile + desktop miniboards.
  It shows the move that SHOULD have been played to reach the scrubbed position
  (pairs with the yellow last-move highlight: "what I played vs what was best"),
  NOT the opponent's best reply. The scrubbed board `perPly[activePly]` is game-ply
  `activePly+1`; the move that reached it was played from game-ply `activePly`, so the
  arrow is `eval_series[ply == activePly].best_move`. No arrow at rest.
- `FlawCard.tsx`: arrow at the pre-flaw decision point (`flaw.best_move`) beside the
  red flaw-move arrow; skipped if it coincides with the played move.

"If available" gate: `best_move` is NULL for lichess-eval-only games (no PV
captured) and the final position → no arrow.

## Scope note
"Game card" = `LibraryGameCard` (the position-scrubbing card). The static
`results/GameCard.tsx` shows only `result_fen` with no eval/best_move payload and
no scrubbing, so it was out of scope.

## Tests
- Backend: `_build_eval_series` best_move passthrough; `query_flaws` schema test
  asserts `best_move` from the ply=N join. Extended `_seed_position` /`_make_pos`.
- Frontend: 2 new `FlawCard` tests (blue arrow present when UCI set; absent when null).

## Verification
- Backend: `ruff format`/`check`, `ty` (0 errors), `pytest -n auto` → 2792 passed, 15 skipped.
- Frontend: `tsc -b` clean, `eslint` clean, `vitest` → 985 passed (86 files), `knip` clean.

**Commit:** `a71783f9` (feature, atomic). Docs committed separately.
