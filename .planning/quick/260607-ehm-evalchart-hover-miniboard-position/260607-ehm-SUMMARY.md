---
slug: evalchart-hover-miniboard-position
phase: 109 (feedback)
status: complete
date: 2026-06-07
commit: 9cd63886
---

# Summary: EvalChart hover → live miniboard position + flaw dot

Phase 109 feedback for the Library → Games cards. Hovering the eval chart now
drives the card's miniboard, and the snap-to-nearest-flaw behavior is gone.

## What changed

1. **Unsnapped crosshair + tooltip** (`EvalChart.tsx`). The vertical crosshair
   follows the exact hovered ply. Removed `nearestMistakeOrBlunder`. The tooltip
   also tracks the exact ply now (it snapped in the same commit, c077c929):
   shows `{move} · {eval}` for any ply, plus the You/Opponent glyph + severity +
   tags when the hovered ply is itself a mistake/blunder.
2. **Bigger miniboard** (`LibraryGameCard.tsx`): desktop 100→132, mobile 105→130.
3. **Live position on hover**: `hoverPly` lifted into `LibraryGameCard`; a new
   `onHoverPlyChange` callback on `EvalChart` reports the ply. The card replays
   the SAN mainline once (chess.js, memoized) into per-ply `{fen, to}` entries and
   swaps the board FEN to the hovered ply. At rest the board shows `result_fen`.
4. **Flaw corner dot** (`MiniBoard.tsx` new `cornerDot` prop, threaded through
   `LazyMiniBoard`): orange (mistake) / red (blunder) SVG dot on the top-right
   corner of the moved piece's destination square when the hovered ply is M/B.

## Why the ply→position mapping is correct

`game_positions` stores no per-ply FEN (only Zobrist hashes + `move_san`). The
full PGN is on `games.pgn`, but the SAN mainline is cheaper, so the backend now
returns `GameFlawCard.moves` (built from already-loaded positions — no extra
query). Crucially, `zobrist.py` stores `eval_cp` at ply P as the eval of the
position **after** the move at ply P. So `eval_series[P].es` already corresponds
to the position reached by playing `moves[0..P]`, the chart flaw dot sits at the
post-blunder eval, and the moved piece (`moves[P].to`) is on that board — the dot
lands on the right piece with no off-by-one.

## Scope note (flag for review)

The tooltip now appears on **every** hovered ply (move + eval), not only on flaw
plies as before the unsnap. This pairs naturally with the new scrubbing, but if
it feels noisy it's a one-line gate on `marker` presence in `buildTooltipContent`.

## Verification

- Backend: `ruff format/check` clean, `ty` clean, full suite `2431 passed` (one
  unrelated flake — guest-account IP rate-limit — passes in isolation).
  `TestEvalSeriesPayload` extended: asserts `moves` aligns with `eval_series`
  (analyzed) and is null (unanalyzed); fixture now seeds `move_san`.
- Frontend: `lint` clean, `tsc` clean, `knip` clean, `825 passed`.
- **HUMAN-UAT (manual)**: hover the eval chart on an analyzed Games card — board
  scrubs through positions, crosshair tracks the cursor exactly, and M/B plies
  draw the orange/red dot on the moved piece. Check both desktop and mobile.

commit: 9cd63886
