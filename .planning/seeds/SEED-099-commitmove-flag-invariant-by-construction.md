---
title: Enforce the "bot can lose on time" invariant by construction, not by comment (useBotGame commitMove)
trigger_condition: Next time useBotGame.ts's clock/commit path is touched — or immediately, as a /gsd-quick. Surfaces at next /gsd-new-milestone scoping.
planted_date: 2026-07-13
source: 169-REVIEW.md WR-01 (code review after Phase 169 plan-10 gap closure)
---

# SEED-099: `commitMove`'s flag invariant is enforced by prose, not by code

**File:** `frontend/src/hooks/useBotGame.ts` (`commitMove`, ~:400-418)

## The problem

Phase 169's amended SC1 says the bot **can lose on time, like a human** (D-15/D-16/D-18). That
invariant currently rests on an 11-line *comment* on `commitMove`:

> "Callers MUST call `flagIfOutOfTime` before applying a move; do not reintroduce a floor here."

`commitMove` does nothing to enforce it. A future call site that forgets produces a **negative**
`clockBaseRef[mover]`, which `applyIncrementMs`'s `Math.max(0, …)` then silently converts straight
back into the never-flag behavior D-15 deleted — topping the flagged mover back up to exactly the
Fischer increment. No error, no failing test, no type error, no lint warning.

## Why this is worth a seed and not a shrug

**This exact invariant has already regressed twice**, and Phase 169 burned three gap-closure rounds
(plans 08, 09, 10) plus a post-review orchestrator fix on it:

- Plans 08/09 deleted the never-flag clamp from `chessClock.ts` — but an unlabelled duplicate of it
  survived in `useBotGame.ts`'s `commitMove`. Grep for the symbol: clean. Invariant: false.
- The related CR-01 (hidden-tab) fix had the same shape — all consumers correctly routed through one
  helper, but the helper's *input* was never seeded at mount.

Prose is not a mechanism. The invariant currently has exactly two guards (`attemptMove` and
`runBotTurn` both call `flagIfOutOfTime` before `chess.move()`), and the only thing keeping a third
caller from breaking it is that a future reader notices the comment.

## Fix (two options, either is cheap)

**(a) Make it structural — `commitMove` owns the question.** Fold the flag test in, so `commitMove`
answers "can this move be applied at all?" and returns `false` when the mover has flagged. Callers
then cannot skip it, because there is nothing to skip.

**(b) Fail loudly in dev.** Cheaper, weaker:

```ts
const remainingBeforeIncrement = clockBaseRef.current[mover] - debitMs;
if (import.meta.env.DEV && remainingBeforeIncrement <= 0) {
  throw new Error('commitMove reached with an overrun debit — caller skipped flagIfOutOfTime');
}
```

Option (a) is preferred: it removes the precondition rather than policing it.

## Verification note

Whatever the fix, prove it by **mutation**: revert it and confirm specific tests fail. The existing
regression tests (`useBotGame.test.ts`, the two commit-path flag tests) use `vi.setSystemTime()` with
no timer advance, so the 100 ms tick provably cannot be the detector — preserve that property.
