---
title: A blend=0 bot has an honest, flaggable clock but NO pacing mechanism — the D-16 think deadline is thrown away
trigger_condition: BLOCKS Phase 171 (Bots Page + Setup Screen) — must be resolved before `blend` is surfaced as a user-facing slider. Read this at Phase 171 discuss/plan.
planted_date: 2026-07-13
source: 169-REVIEW.md WR-02 (code review after Phase 169 plan-10 gap closure)
---

# SEED-100: `blend <= 0` bot is clock-managed in name only

**Files:** `frontend/src/hooks/useBotGame.ts` (`buildBotMoveDeps`, ~:205-212, :709-710);
`frontend/src/lib/engine/selectBotMove.ts` (~:112-118)

## The problem

Phase 169 (D-16) gives the bot a per-move think deadline derived from its remaining clock, injected
into `selectBotMove` through the `deps.search` seam via `createDeadlineSearch`. That is what makes
the bot speed up in time trouble instead of flagging.

But `selectBotMove`'s full-human regime **returns before `deps.search` is ever consulted**:

```ts
if (blend <= 0) {
  const rawPolicy = await deps.policy(fen, settings.elo, side);   // no deps.search call
  const sampled = samplePolicy(rawPolicy, deps.rng);
  return sampled ?? fallbackMove(fen, deps.rng);
}
const search = deps.search ?? mctsSearch;   // only reached for blend > 0
```

So at `blend = 0` the bot has an **honest, flaggable clock and no pacing mechanism whatsoever**.
`computeThinkDeadlineMs` is computed, passed into `createDeadlineSearch`, and thrown away.

Phase 169's amended SC1 pairs "the bot CAN lose on time" with "it manages its own clock via a
per-move think deadline". At `blend = 0` the first half ships and the second half does not.

## Why this is a Phase 171 blocker, not a hypothetical

`BotGameSettings.blend` is a **public field of the hook's contract**, and **Phase 171 surfaces it as
a user-facing slider**. The only reason this does not bite today is that `Bots.tsx` hardcodes
`blend: 0.5`. The moment a user can drag that slider to 0, they get a bot that can lose on time with
nothing managing its clock.

Also note: the D-16 header comment in `chessClock.ts` (~:36-39) asserts that `deadlineSearch.ts`
"enforces [the deadline] from OUTSIDE the frozen search core." That claim is **only true for
`blend > 0`** and should be corrected either way.

## Fix (pick one at Phase 171 planning)

**(a) Enforce the deadline outside `selectBotMove`.** Race the whole `selectBotMove(...)` call
against a `deadlineMs` timer that aborts the outer controller. This makes the deadline regime-
independent and matches what the D-16 comment already claims. Preferred if the blend slider ships.

**(b) Document the exemption and pin it.** Explicitly note on `BotGameSettings.blend` and in
chessClock.ts's D-16 header that the deadline applies only to `blend > 0`, and add a test that pins
the behavior — so Phase 171 does not ship a `blend = 0` bot believing it is clock-managed. Only
acceptable if the slider's range excludes 0, or if a pure-policy bot is fast enough that pacing is
moot (needs measurement, not assumption).

## Verification note

Prove whichever fix by **mutation** — revert it and confirm a test fails. Phase 169 burned three
rounds on invariants that passed greps while being false at runtime; do not accept symbol presence
as evidence here.
