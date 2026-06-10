---
slug: evalchart-hover-miniboard-position
phase: 109 (feedback)
created: 2026-06-07
---

# Quick Task: EvalChart hover → live miniboard position + flaw dot

Feedback for Phase 109, Library → Games cards (`LibraryGameCard` + `EvalChart` + `MiniBoard`).

## Requirements

1. **Undo crosshair snap.** Revert the recent change (c077c929) that snapped the
   vertical crosshair to the nearest mistake/blunder. The crosshair must follow
   the exact hovered ply. Unsnap the tooltip too (it snapped in the same commit) —
   leaving it snapped while the crosshair/board track the exact ply is incoherent.
2. **Bigger miniboard.** Bump `DESKTOP_BOARD_SIZE` / `MOBILE_BOARD_SIZE`.
3. **Live position on hover.** Moving the cursor over the eval chart updates the
   card's miniboard to the position marked by the crosshair ply. At rest (no
   hover) the board shows `result_fen` as today.
4. **Flaw dot on the moved piece.** If the hovered ply's move is a mistake or
   blunder, draw an orange (mistake) / red (blunder) dot on the top-right corner
   of the square of the piece that moved.

## Key data facts (grounding the design)

- `game_positions` stores no per-ply FEN, only Zobrist hashes + `move_san`
  (the move played FROM that ply). The full PGN lives on `games.pgn`.
- `zobrist.py` (`process_game_pgn`): `eval_cp` at ply P is the eval of the
  position **AFTER** the move at ply P (`move_san`). Therefore `es[ply P]` in the
  chart already corresponds to the position reached by playing move P, and the
  chart flaw dot at ply P sits at the post-blunder eval.
- ⇒ Crosshair ply P maps to the position after playing moves[0..P], with the
  moved piece (`moves[P].to`) at its destination. This is consistent with both
  "show the position at the crosshair" and "dot the piece that moved".

## Approach

**Backend** (`app/schemas/library.py`, `app/services/library_service.py`)
- Add `moves: list[str] | None = None` to `GameFlawCard` — the SAN mainline,
  cheap to build from already-loaded `positions` (`[p.move_san for p in positions
  if p.move_san is not None]`). Populated only for analyzed games with positions.

**Frontend types** (`frontend/src/types/library.ts`)
- Add `moves: string[] | null` to `GameFlawCard`.

**`EvalChart.tsx`**
- Remove `snappedPly` / `nearestMistakeOrBlunder`. Crosshair `ReferenceLine`
  uses the exact `hoverPly`.
- Add prop `onHoverPlyChange?: (ply: number | null) => void`; call it from
  `handleMouseMove` / `handleMouseLeave`.
- Add prop `moves: string[]` so the tooltip can label any ply.
- Tooltip: key off the exact hovered ply (`markerMap.get(point.ply)`); show
  move + eval for every ply, plus glyph/severity/tags when that ply is M/B.

**`LibraryGameCard.tsx`**
- Lift `hoverPly` state. Memoize a per-ply reconstruction from `game.moves` via
  chess.js: `perPly[i] = { fen after moves[0..i], to: moves[i].to }`.
- Build a ply→severity map for M/B markers.
- Compute board fen = `perPly[clamp(hoverPly)].fen ?? result_fen`, and a
  `cornerDot = { square: perPly[ply].to, color: sev }` when the hovered ply is M/B.
- Pass fen + cornerDot to `LazyMiniBoard` (mobile + desktop), and
  `onHoverPlyChange` + `moves` to `EvalChart` (mobile + desktop).

**`MiniBoard.tsx` / `LazyMiniBoard.tsx`**
- Add optional `cornerDot?: { square: string; color: string }`. Render an SVG dot
  at the top-right corner of that square (reuse `squareToCoords`). Thread through
  `LazyMiniBoard`.

## Verification

- `cd frontend && npm run lint && npm test -- --run`
- `uv run ruff format/check`, `uv run ty check app/ tests/`, `uv run pytest -n auto`
  for the schema change (library service/router tests).
- Manual: hover the eval chart, confirm board scrubs through positions, crosshair
  tracks the cursor, and M/B plies draw the corner dot on the moved piece.
