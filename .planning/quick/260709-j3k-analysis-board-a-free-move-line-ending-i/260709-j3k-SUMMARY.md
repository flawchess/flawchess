---
quick_id: 260709-j3k
status: complete
date: 2026-07-09
commit: ce8d19b5
---

# Quick Task 260709-j3k — Summary

## What changed

Fixed the `/analysis` board so a free (sideline / free-play) move that delivers
**checkmate** is no longer graded a blunder, and the Stockfish eval bar fills to the
winner (0% / 100%) instead of snapping back to the ~50% midpoint.

## Root cause

A checkmated position reports an ambiguous `mate 0` (or no score) from the live
Stockfish worker. Two consumers misread it:

- `EvalBar.computeWhiteFraction` maps `evalMate === 0` to the 0.5 midpoint.
- `evalToExpectedScore` maps `evalMate === 0` to "no mate" → 0.5 expected score, so
  `useLiveMoveFlaw` saw the mover's score drop from ~1.0 (winning parent) to 0.5
  (child) and tagged the mating move a **blunder**.

## Fix

Added a pure helper `terminalPositionEval(fen)` in `frontend/src/lib/liveFlaw.ts`
that derives the eval from the rules via chess.js:

- checkmate → decisive white-POV mate for the winner (`{ cp: null, mate: ±1 }`,
  sign keyed to the mated side to move),
- draw / stalemate → dead-equal (`{ cp: 0, mate: null }`),
- in-progress / malformed FEN → `null`.

`Analysis.tsx` computes `terminalEval = terminalPositionEval(position)` and prefers it
over the live engine eval for both:
- the right (Stockfish) eval bar — with a synthetic depth (`TERMINAL_EVAL_DEPTH = 99`)
  so EvalBar's mate-display gate fires and the bar fills to the winner;
- `useLiveMoveFlaw`'s child eval — the mating move now reads clean (green last-move
  squares), while a genuine stalemate-when-winning still correctly flags (its cp-0
  child still drops the mover's expected score).

## Files

- `frontend/src/lib/liveFlaw.ts` — new `terminalPositionEval` export + `TERMINAL_MATE`.
- `frontend/src/pages/Analysis.tsx` — `terminalEval` memo, wired into the live-flaw
  child eval and the right eval bar; `TERMINAL_EVAL_DEPTH` constant.
- `frontend/src/lib/__tests__/terminalPositionEval.test.ts` — new (5 cases: white/black
  mate sign, stalemate, in-progress, malformed FEN).

## Verification

- `npm test -- --run` → 135 files, 1636 tests pass (incl. new terminalPositionEval + existing Analysis suite).
- `npx tsc -b` clean, `npm run lint` clean (only pre-existing `coverage/` warnings), `npm run knip` clean.

## Notes / out of scope

- The EvalBar text label reads `M1` / `-M1` for a delivered mate (it's technically
  mate-in-0); the bar *direction* is the requirement and is correct. Cosmetic label
  polish left out of scope.
- Backend `eval_series` / game main-line checkmate already carries a decisive eval
  from the backend, so this change targets the live/free path.
