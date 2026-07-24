---
phase: 182-style-levers
plan: 02
subsystem: engine
tags: [chess-engine, bot-play, draw-policy, resign-policy, typescript, vitest]

# Dependency graph
requires:
  - phase: 169-play-07-clocked-board
    provides: "botDrawGate.ts with wouldBotAcceptDraw (D-01) and canOfferDraw (D-04), the never-offer/never-resign Phase 169 D-02/D-03 baseline"
provides:
  - "wouldBotAcceptDraw gains an optional signed contempt param (D-09) shifting the accept target off dead-center 0.5, band width unchanged, byte-identical when omitted/0"
  - "wouldBotResign: a new pure, sentinel-first, hysteresis-gated resign predicate (D-07/D-08)"
  - "RESIGN_MIN_FULLMOVE and RESIGN_HYSTERESIS_TURNS named tunable constants"
  - "module header records D-07 (Phase 182) supersedes Phase 169 D-02/D-03 for STYLED bots only"
affects: [182-07-wire-style-levers-into-useBotGame, 183-persona-registry-bots-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sentinel-first pure predicate: null rootPracticalScore refuses before any other argument is inspected, matching wouldBotAcceptDraw's existing discipline"
    - "Signed contempt knob shifts a decision's target value (0.5 - contempt), never the tolerance band width around it"
    - "Hysteresis counters stay caller-owned (a ref in useBotGame.ts); the pure predicate in botDrawGate.ts carries no state"

key-files:
  created: []
  modified:
    - frontend/src/lib/botDrawGate.ts
    - frontend/src/lib/__tests__/botDrawGate.test.ts

key-decisions:
  - "RESIGN_MIN_FULLMOVE set to 20 ([ASSUMED], hand-tuned) — later than DRAW_ACCEPT_MIN_FULLMOVE's 40 is not required since resignation only needs a settled-enough position, not the same conservative bar as offering a draw"
  - "RESIGN_HYSTERESIS_TURNS set to 4 ([ASSUMED], hand-tuned default) as the shared floor when a style doesn't override it; actual per-style thresholds are style params supplied by Plan 07's wiring, not hardcoded here"
  - "wouldBotResign takes 5 positional args (score, threshold, consecutiveLowTurns, hysteresisFloor, chess) mirroring wouldBotAcceptDraw's parameter-list style rather than an options object, keeping both draw-gate functions structurally consistent"

patterns-established:
  - "Contempt-style signed shift: drawValue = 0.5 - contempt as the general shape for future style knobs that move a decision target without touching its tolerance band"

requirements-completed: [STYLE-02]

coverage:
  - id: D1
    description: "wouldBotAcceptDraw gains an optional contempt param (D-09); contempt omitted/0 is byte-identical to pre-182 behavior; positive contempt refuses a level position, negative contempt accepts a mildly-worse position; null sentinel still refused regardless of contempt"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botDrawGate.test.ts#wouldBotAcceptDraw > contempt (D-09, Phase 182)"
        status: pass
    human_judgment: false
  - id: D2
    description: "wouldBotResign: new pure predicate — null sentinel refuses first/unconditionally; true only when score <= threshold AND consecutiveLowTurns >= hysteresisFloor AND past RESIGN_MIN_FULLMOVE; below-floor and early-game cases refuse; idempotent"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botDrawGate.test.ts#wouldBotResign (D-07/D-08, Phase 182)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-21
status: complete
---

# Phase 182 Plan 02: Draw Contempt & Resign Predicate Summary

**Extended `botDrawGate.ts` with a signed contempt knob on `wouldBotAcceptDraw` (D-09) and a new pure, sentinel-first, hysteresis-gated `wouldBotResign` predicate (D-07/D-08) — policy-only, wiring deferred to Plan 07.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-21T23:05:00Z (approx)
- **Completed:** 2026-07-21T23:20:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `wouldBotAcceptDraw` accepts a trailing optional `contempt = 0` parameter; the accept target is now `0.5 - contempt`, band width (`DRAW_ACCEPT_SCORE_BAND`) unchanged; contempt omitted/0 is byte-identical to the pre-182 function for every existing 2-arg caller.
- New pure `wouldBotResign(rootPracticalScore, resignThreshold, consecutiveLowTurns, hysteresisFloor, chess)` predicate: refuses immediately and unconditionally on the `null` sentinel (Human-rung / in-book bots never resign, D-08); otherwise resigns only when the score is at/below threshold, the hysteresis floor is met, and the game is past `RESIGN_MIN_FULLMOVE`.
- New named, doc-commented constants `RESIGN_MIN_FULLMOVE` (20) and `RESIGN_HYSTERESIS_TURNS` (4), mirroring the existing `DRAW_ACCEPT_MIN_FULLMOVE` convention.
- Module doc-header updated to record that D-07 (Phase 182) supersedes Phase 169's D-02/D-03 never-offer/never-resign rule for STYLED bots only — unstyled bots keep the old behavior by construction (every new parameter defaults to the old no-op value).
- Test suite extended from 6 to 18 passing tests covering contempt shift, resign sentinel/hysteresis/early-game/threshold cases, and idempotency.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add contempt to wouldBotAcceptDraw + update the supersession header** - `a9cacbb8` (feat)
2. **Task 2: Add the pure wouldBotResign predicate + named resign constants** - `1a0fe5e4` (feat)

_TDD tasks structured as behavior-first implementation + test extension per commit (existing test file grown incrementally, not a strict separate RED/GREEN pair)._

## Files Created/Modified
- `frontend/src/lib/botDrawGate.ts` - added `contempt` param + D-09 doc, `RESIGN_MIN_FULLMOVE`/`RESIGN_HYSTERESIS_TURNS` constants, new `wouldBotResign` predicate, D-07 supersession note in the module header
- `frontend/src/lib/__tests__/botDrawGate.test.ts` - added contempt regression/shift/null-sentinel cases and a full `wouldBotResign` test block (sentinel, below-floor, at-floor-past-min-move, early-game, above-threshold, idempotency)

## Decisions Made
- `RESIGN_MIN_FULLMOVE = 20` — deliberately earlier than `DRAW_ACCEPT_MIN_FULLMOVE`'s 40; resigning doesn't need the same conservative "wait for genuine endgame" bar that offering a draw does, just enough moves for the position to have settled past the opening.
- `RESIGN_HYSTERESIS_TURNS = 4` as the shared default; per-style overrides are Plan 07's job (style params supplied by the caller), not hardcoded per-style values in this module.
- `wouldBotResign` kept as 5 positional args, not an options object, to stay structurally consistent with `wouldBotAcceptDraw`'s existing calling convention in this same module.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `wouldBotAcceptDraw`'s contempt param and `wouldBotResign` are ready for Plan 07 to wire into `useBotGame.ts`: the plan's own Pitfall 3 guidance (hysteresis counter as a per-game ref, reset in `newGame()`, incremented alongside `lastRootPracticalScoreRef`) is unchanged and unblocked by this plan.
- No blockers. `npx vitest run src/lib/__tests__/botDrawGate.test.ts` (18/18 pass) and `npx tsc -b` (zero errors) both green; `grep -nE "^(let|var) " frontend/src/lib/botDrawGate.ts` finds no module-level mutable state (prohibition satisfied).

---
*Phase: 182-style-levers*
*Completed: 2026-07-21*

## Self-Check: PASSED

All claimed files and commits verified present on disk / in git history.
