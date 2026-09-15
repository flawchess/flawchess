---
quick_id: 260915-sht
slug: fix-train-verdict-return-tail-red-herrin
date: 2026-09-15
status: complete
commit: 2b77f0009
---

# Summary: Train verdict tail no longer calls a regular-session herring a warm-up

## What changed

- `frontend/src/lib/trainBotCopy.ts`: `ReturnPhraseInput.is_warmup` added.
  `returnPhrase` returns `WARMUP_TAIL` for herring/filler sources only when
  `is_warmup === true`; otherwise `HERRING_TAIL` ("That one was a red
  herring, so it won't come back.") or `FILLER_TAIL` ("That one was a filler
  position, so it won't come back."). An absent flag (pre-fix cached reveal)
  degrades to the neutral line, never the warm-up claim.
- `frontend/src/components/train/TrainSolveScreen.tsx`: `deps.isWarmup`
  (already computed from `trainSession.session?.is_warmup` for the intro
  stepper) is threaded through `renderVerdictBubbleBody` into `returnPhrase`.
- `CHANGELOG.md`: Fixed bullet under `[Unreleased]`.

## Tests

- `trainBotCopy.test.ts`: warm-up branch for both sources, regular-session
  branch for both sources (no "warm-up", no "own positions"), per-source
  wording, absent-flag fallback.
- `TrainSolveScreen.test.tsx`: `it.each` over `is_warmup` true/false with a
  `red_herring` solve response, asserting the rendered verdict line mentions
  "warm-up" iff the session is a warm-up (proves the flag is threaded, not
  just accepted).
- Mutation check: with the fix stashed and tests kept, 5 tests fail.
- Gate: `npm run lint`, `npx tsc -b`, full vitest (264 files / 4190 tests) green.

## Not done / follow-ups

- Phase 222 D-16 prose in `222-CONTEXT.md` still groups herrings under
  "warm-up"; left as historical record, the code comment at the fix site
  explains the correction.
