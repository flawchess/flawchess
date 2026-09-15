---
quick_id: 260915-sht
slug: fix-train-verdict-return-tail-red-herrin
date: 2026-09-15
status: planned
---

# Quick task 260915-sht: Fix Train verdict return tail for herrings in regular sessions

## Problem

`returnPhrase` (`frontend/src/lib/trainBotCopy.ts`) returns the warm-up tail
("That one was a warm-up, so it won't come back. Your own positions will.") for
ANY puzzle whose `source` is `red_herring` or `sharp_filler`, regardless of
whether the session is a warm-up. Phase 222 D-16 conflated "never returns" with
"warm-up". Red herrings are a regular part of every Train session, so a user
with plenty of SR items (reported by user 28 in prod) sees a line claiming the
puzzle was a warm-up and that "your own positions will" come, while the
surrounding puzzles already are their own positions.

The session-level flag `TrainSessionResponse.is_warmup` (Phase 206 D-06/D-07,
true iff zero surviving SR items at composition) already reaches
`TrainSolveScreen` and is used for the intro stepper and score bubble, but not
the per-puzzle verdict tail.

## Tasks

1. `trainBotCopy.ts`: add `is_warmup?: boolean` to `ReturnPhraseInput`. For
   herring/filler sources return the warm-up tail only when `is_warmup` is
   true; otherwise a neutral non-return line per source ("That one was a red
   herring, so it won't come back." / "That one was a tactics puzzle, not from
   your games, so it won't come back."). Update the D-16 doc comment.
2. `TrainSolveScreen.tsx`: thread `deps.isWarmup` into
   `renderVerdictBubbleBody` and on into `returnPhrase`.
3. Tests in `frontend/src/lib/__tests__/trainBotCopy.test.ts`: pin both
   branches for both sources (warm-up session vs regular session), and pin
   that the regular-session line never mentions "warm-up" or "own positions".

## Verify

`cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__/TrainSolveScreen.test.tsx && npm run lint && npx tsc -b`
