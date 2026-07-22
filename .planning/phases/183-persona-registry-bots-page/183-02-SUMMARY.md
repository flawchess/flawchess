---
phase: 183-persona-registry-bots-page
plan: 02
subsystem: bot-engine
tags: [chess.js, vitest, bot-personas, draw-offer, tdd]

# Dependency graph
requires:
  - phase: 182-style-levers
    provides: "BotStyleParams.contempt knob, wouldBotAcceptDraw/wouldBotResign shape, botDrawGate.ts module"
provides:
  - "wouldBotOfferDraw(rootPracticalScore, chess, contempt, movesSinceOwnOffer) — pure predicate for whether a styled bot would OFFER a draw right now"
  - "BOT_DRAW_OFFER_SCORE_BAND / BOT_DRAW_OFFER_MIN_FULLMOVE / BOT_DRAW_OFFER_COOLDOWN_MOVES tuning constants"
affects: [183-03-wiring-useBotGame, 183-05-draw-offer-banner]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New draw-gate predicates mirror wouldBotResign's exact shape: pure function, null-sentinel refused first and unconditionally, no internal state, caller-owned cooldown/hysteresis counter"

key-files:
  created: []
  modified:
    - frontend/src/lib/botDrawGate.ts
    - frontend/src/lib/__tests__/botDrawGate.test.ts

key-decisions:
  - "Reused the existing contempt knob (drawValue = 0.5 + contempt) instead of adding a new BotStyleParams field, per RESEARCH.md A4's resolution — keeps the 4 shipped Phase-182 style bundles byte-unchanged"
  - "BOT_DRAW_OFFER_MIN_FULLMOVE=30 chosen independently of RESIGN_MIN_FULLMOVE=20 and DRAW_ACCEPT_MIN_FULLMOVE=40 (Pitfall 7) — offering is a bot-initiated declarative action, so its floor sits between the resign floor and the accept fallback"
  - "BOT_DRAW_OFFER_SCORE_BAND=0.05 matches DRAW_ACCEPT_SCORE_BAND's width for now (no signal yet that offer/accept need different tolerances); BOT_DRAW_OFFER_COOLDOWN_MOVES=6 is a new, separate counter from the user-facing DRAW_OFFER_COOLDOWN_MOVES=5 button throttle"

patterns-established:
  - "Bot-initiated (offer) vs user-initiated (accept) draw policy predicates live side-by-side in botDrawGate.ts with independently-tuned constants, never sharing a threshold without an explicit documented rationale"

requirements-completed: [PERS-02]

coverage:
  - id: D1
    description: "wouldBotOfferDraw is a pure, null-sentinel-disciplined predicate that returns false unconditionally when rootPracticalScore is null"
    requirement: PERS-02
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw > returns false for the not-yet-evaluated null sentinel, checked before every other argument"
        status: pass
    human_judgment: false
  - id: D2
    description: "With a real score, returns true only when score is within band of contempt-shifted draw target AND past the fullmove floor AND cooldown elapsed"
    requirement: PERS-02
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw > offers a dead-equal score once past the fullmove floor with cooldown elapsed"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw > does not offer when movesSinceOwnOffer is below the cooldown, even with a qualifying score"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw > does not offer in an early, still-developing position even with a dead-equal score"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw > does not offer a clearly-winning score, even past the floor with cooldown elapsed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Contempt shifts the offer target only (never the band width) — positive contempt (Grinder) offers rarely, negative contempt (Wall) offers readily, for free from the existing contempt knob"
    requirement: PERS-02
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw contempt shifts the offer target > positive contempt (Grinder-like) refuses a dead-equal score a neutral bot would offer"
        status: pass
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts#wouldBotOfferDraw contempt shifts the offer target > negative contempt (Wall-like) offers a mildly-worse position a neutral bot would refuse"
        status: pass
    human_judgment: false
  - id: D4
    description: "wouldBotOfferDraw is a NEW opt-in export; canOfferDraw/wouldBotAcceptDraw/wouldBotResign and the 4 Phase-182 style bundles are byte-unchanged"
    requirement: PERS-02
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botDrawGate.test.ts (all 18 pre-existing cases pass unchanged)"
        status: pass
      - kind: other
        ref: "git diff --stat confirms botStyle.ts / botStyleBundles.ts are not in this plan's diff"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-22
status: complete
---

# Phase 183 Plan 02: Bot Outgoing Draw-Offer Predicate Summary

**Added `wouldBotOfferDraw` — the pure predicate mirroring `wouldBotResign`'s shape that decides whether a styled bot would offer a draw, reusing the existing `contempt` knob instead of a new BotStyleParams field**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-22T11:15:00Z
- **Completed:** 2026-07-22T11:30:00Z
- **Tasks:** 1 (TDD feature: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- `wouldBotOfferDraw(rootPracticalScore, chess, contempt, movesSinceOwnOffer)` exported from `botDrawGate.ts`: null-sentinel refused first and unconditionally, pure with no internal state, three qualifying conditions (score band, fullmove floor, cooldown) all required.
- Three new tuning constants: `BOT_DRAW_OFFER_SCORE_BAND` (0.05), `BOT_DRAW_OFFER_MIN_FULLMOVE` (30, independently chosen from resign/accept floors per Pitfall 7), `BOT_DRAW_OFFER_COOLDOWN_MOVES` (6, a bot-own-move counter separate from the user-facing button throttle).
- 8 new unit tests covering the null sentinel, band match/mismatch, fullmove floor, cooldown, both contempt-shift directions (Grinder-like positive, Wall-like negative), and idempotence — all 26 tests in `botDrawGate.test.ts` (18 pre-existing + 8 new) pass.
- Confirmed via `git diff --stat` that `botStyle.ts`/`botStyleBundles.ts` are untouched — no new `BotStyleParams` field, the 4 shipped Phase-182 bundles stay byte-unchanged.

## Task Commits

TDD gate sequence for the single feature (per plan `type: tdd`):

1. **RED** - `f823c35e` (test): added 8 failing test cases importing the not-yet-existing `wouldBotOfferDraw`/constants; confirmed failure (Invalid FEN from an undefined `BOT_DRAW_OFFER_MIN_FULLMOVE` template interpolation — 8 failed, 18 pre-existing passed).
2. **GREEN** - `c5349800` (feat): implemented `wouldBotOfferDraw` + 3 constants in `botDrawGate.ts`; all 26 tests pass.

No REFACTOR commit — the implementation was clean on first pass (mirrors `wouldBotResign` structurally, no duplication to extract).

## Files Created/Modified
- `frontend/src/lib/botDrawGate.ts` - Added `wouldBotOfferDraw` + `BOT_DRAW_OFFER_SCORE_BAND`/`BOT_DRAW_OFFER_MIN_FULLMOVE`/`BOT_DRAW_OFFER_COOLDOWN_MOVES`
- `frontend/src/lib/__tests__/botDrawGate.test.ts` - Added `describe('wouldBotOfferDraw ...')` block with 8 new test cases

## Decisions Made
- Reused `contempt` (A4 resolution) rather than adding a new `BotStyleParams` offer-threshold field — per-style offer behavior derives for free from the existing knob, no re-tuning of the 4 shipped bundles.
- `BOT_DRAW_OFFER_MIN_FULLMOVE=30` sits between `RESIGN_MIN_FULLMOVE=20` and `DRAW_ACCEPT_MIN_FULLMOVE=40`: offering is bot-initiated and declarative (stronger commitment than tolerating a loss, but not requiring the accept gate's full endgame-adjacent floor).
- `BOT_DRAW_OFFER_COOLDOWN_MOVES=6` is a distinct counter from the pre-existing `DRAW_OFFER_COOLDOWN_MOVES=5` (which throttles the user-facing button) — different lifecycles, kept independently testable per the module's existing D-04 design philosophy.

## Deviations from Plan

None — plan executed exactly as written. The plan's own `<implementation>` section fully specified the function signature, constants, and body logic; no ambiguity required a judgment call beyond picking the three constants' exact numeric values (which the plan explicitly delegated to this task, flagging them `[ASSUMED] hand-tuned; retune in place`, consistent with the file's existing convention).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `wouldBotOfferDraw` is ready for Plan 03 to wire into `useBotGame.ts`'s existing `pool.grade(...).then(...)` callback (same call site as `wouldBotResign`), with a new caller-owned `movesSinceOwnOffer` ref alongside the existing per-game latches.
- No blockers. `botStyle.ts`/`botStyleBundles.ts` confirmed untouched, so Plan 03's wiring work starts from a clean, unmodified `BotStyleParams` shape.

---
*Phase: 183-persona-registry-bots-page*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: frontend/src/lib/botDrawGate.ts
- FOUND: frontend/src/lib/__tests__/botDrawGate.test.ts
- FOUND: wouldBotOfferDraw export in botDrawGate.ts
- FOUND: commit f823c35e (test: RED)
- FOUND: commit c5349800 (feat: GREEN)
- FOUND: commit 33d8dbff (docs: summary)
