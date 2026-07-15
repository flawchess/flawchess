---
phase: 169-clocked-board-game-loop-usebotgame
plan: 02
subsystem: game-logic
tags: [chess.js, pgn, bot-play, draw-gate, end-conditions]

requires:
  - phase: 167
    provides: normalize_flawchess_game backend PGN validator (STORE-02 [%clk] gate, Termination/Result closed vocabulary)
  - phase: 168.5
    provides: locked pacing/D-01..D-04 decisions this plan encodes as named constants
provides:
  - botGameEnd.ts — chess.js end-condition detection (checkmate/stalemate/threefold/fifty-move/insufficient-material) + UI-SPEC result-copy mapping
  - botDrawGate.ts — D-04 draw-offer-throttle counter + D-01 bot draw-accept eval+endgame gate, as two independent pure functions
  - botGamePgn.ts — [%clk]/[Termination]/[Result]/[TimeControl] PGN builder proven acceptable by the backend
affects: [169-04-usebotgame-hook, 169-06-game-result-dialog]

tech-stack:
  added: []
  patterns:
    - "Pure, React-free lib modules with co-located __tests__ (mirrors analysisUrl.ts / chessClock.ts extraction rationale)"
    - "Two independent state pieces instead of one collapsed boolean (draw throttle vs draw accept-gate, RESEARCH Pitfall 5)"

key-files:
  created:
    - frontend/src/lib/botGameEnd.ts
    - frontend/src/lib/botDrawGate.ts
    - frontend/src/lib/botGamePgn.ts
    - frontend/src/lib/__tests__/botGameEnd.test.ts
    - frontend/src/lib/__tests__/botDrawGate.test.ts
    - frontend/src/lib/__tests__/botGamePgn.test.ts
    - tests/test_bot_pgn_clk_roundtrip.py
  modified: []

key-decisions:
  - "Reused MoverColor ('white' | 'black') from @/lib/liveFlaw for winner/userColor rather than declaring a new duplicate type"
  - "finalizeBotPgn also sets a [TimeControl] header from tcStr for PGN completeness/fidelity, even though the backend receives tc_str as a separate caller-supplied param (not parsed from the PGN header)"
  - "Backend round-trip test placed at tests/test_bot_pgn_clk_roundtrip.py (top-level, per plan spec) rather than tests/services/, mirroring the existing pure-unit-test pattern in tests/services/test_normalization.py (no DB required)"
  - "Reverted requirements.mark-complete's PLAY-06/07/09 checkbox flip: all three are shared across Plans 02/04 (frontmatter; PLAY-07 also Plan 05, PLAY-09 also Plan 06) — this plan delivers only the pure board-detection/draw-gate/PGN-builder logic, not flag-on-time detection, resign/draw UI wiring, or the result screen itself. Left [ ] Pending in REQUIREMENTS.md with a partial-delivery note; Plan 04 (useBotGame) and Plans 05/06 actually close them."

patterns-established:
  - "PGN-building modules (botGamePgn.ts) exclusively use chess.js setComment/setHeader/pgn() — never hand-template PGN text"
  - "Board-draw sub-reasons (stalemate/threefold/fifty-move/insufficient-material) all collapse to the single backend 'draw' Termination header; client-side copy keeps the specific reason"

requirements-completed: []  # PLAY-06/07/09 are shared across Plans 02/04 (frontmatter; PLAY-07 also Plan 05, PLAY-09 also Plan 06); this plan delivers only the pure logic modules. Left [ ] Pending in REQUIREMENTS.md with a partial-delivery note — Plan 04 (useBotGame) and Plans 05/06 actually close them.

coverage:
  - id: D1
    description: "detectEndCondition detects all five board end conditions via chess.js methods with correct checkmate winner derivation"
    requirement: "PLAY-06"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameEnd.test.ts#detectEndCondition"
        status: pass
    human_judgment: false
  - id: D2
    description: "resultCopy maps every outcome to the verbatim UI-SPEC Copywriting Contract string from the user's POV"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameEnd.test.ts#resultCopy"
        status: pass
    human_judgment: false
  - id: D3
    description: "canOfferDraw (D-04 throttle) and wouldBotAcceptDraw (D-01 eval+endgame AND-gate) are two independent, separately testable exports"
    requirement: "PLAY-07"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botDrawGate.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exported PGN carries both-color [%clk h:mm:ss] comments and a backend-valid Termination/Result header pair"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGamePgn.test.ts#annotateClock + finalizeBotPgn"
        status: pass
    human_judgment: false
  - id: D5
    description: "A Phase-169-shaped PGN is accepted end-to-end by the frozen backend normalize_flawchess_game validator (STORE-02 both-color [%clk] gate)"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "tests/test_bot_pgn_clk_roundtrip.py#TestBotPgnClkRoundtrip::test_phase_169_shaped_pgn_normalizes"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 02: botGameEnd/botDrawGate/botGamePgn Summary

**Three pure, React-free game-logic modules — chess.js end-condition detection with UI-SPEC result copy, an independent draw-throttle/draw-accept-gate pair, and a backend-validated `[%clk]`/`[Termination]`/`[Result]` PGN builder — all proven by unit tests plus a real python-chess round-trip.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-12T19:14:17Z
- **Completed:** 2026-07-12T19:23:47Z
- **Tasks:** 3
- **Files modified:** 7 (6 frontend + 1 backend, all new)

## Accomplishments
- `botGameEnd.ts` — `detectEndCondition` wraps chess.js's `isCheckmate`/`isStalemate`/`isThreefoldRepetition`/`isDrawByFiftyMoves`/`isInsufficientMaterial` with correct checkmate-winner derivation; `resultCopy` maps every outcome to the exact UI-SPEC Copywriting Contract string from the user's POV. No bot-resign/bot-draw-offer branch exists anywhere (D-02/D-03 encoded as absence).
- `botDrawGate.ts` — `canOfferDraw` (D-04 cooldown counter) and `wouldBotAcceptDraw` (D-01 near-equal-score AND endgame-gate) kept as two fully independent exports per RESEARCH.md Pitfall 5, each unit-tested in isolation.
- `botGamePgn.ts` — `formatClockHms`/`annotateClock` produce lichess-convention `{[%clk h:mm:ss]}` comments via `chess.setComment`; `finalizeBotPgn` sets `[Result]`/`[Termination]`/`[TimeControl]` via `chess.setHeader`; `toBackendTcStr` emits base+increment seconds (`"300+3"`), never a minutes display label. A new backend pytest (`tests/test_bot_pgn_clk_roundtrip.py`) proves a Phase-169-shaped PGN is accepted by the frozen `normalize_flawchess_game` validator — resolving RESEARCH Assumption A1 (the `h:mm:ss` format parses cleanly via python-chess's `node.clock()`).

## Task Commits

Each task was committed atomically:

1. **Task 1: botGameEnd.ts — end-condition detection + result copy (PLAY-06, PLAY-09)** - `4b685a39` (feat)
2. **Task 2: botDrawGate.ts — offer throttle + bot draw-accept gate (PLAY-07)** - `bde20017` (feat)
3. **Task 3: botGamePgn.ts — [%clk]/[Termination]/[Result] builder + python-chess round-trip (PLAY-09)** - `93247696` (feat)

## Files Created/Modified
- `frontend/src/lib/botGameEnd.ts` - chess.js end-condition detection + UI-SPEC result-copy mapping
- `frontend/src/lib/__tests__/botGameEnd.test.ts` - checkmate (both directions)/stalemate/threefold/fifty-move/insufficient-material fixtures + full resultCopy branch coverage
- `frontend/src/lib/botDrawGate.ts` - D-04 throttle + D-01 accept-gate as two independent pure functions
- `frontend/src/lib/__tests__/botDrawGate.test.ts` - throttle boundary + accept-gate truth table (near-equal×queens-off/queens-on, lopsided×endgame)
- `frontend/src/lib/botGamePgn.ts` - `[%clk]`/`[Termination]`/`[Result]`/`[TimeControl]` PGN builder
- `frontend/src/lib/__tests__/botGamePgn.test.ts` - clock formatting, tc_str formatting, both-color `[%clk]` embedding, draw-reason collapse
- `tests/test_bot_pgn_clk_roundtrip.py` - backend round-trip proving `normalize_flawchess_game` accepts a Phase-169-shaped PGN

## Decisions Made
- Reused `MoverColor` (`'white' | 'black'`) from `@/lib/liveFlaw` for `winner`/`userColor` instead of declaring a duplicate type — keeps the app's single player-POV color convention.
- `finalizeBotPgn` additionally sets a `[TimeControl]` PGN header from `tcStr` for PGN fidelity/completeness (real lichess/chess.com PGNs always carry one), even though the backend receives `tc_str` as a separate service-layer parameter rather than parsing it from the PGN header — this is additive, not required by `normalize_flawchess_game`, and does not change any gate behavior.
- Placed the backend round-trip test at the top-level `tests/test_bot_pgn_clk_roundtrip.py` (as the plan specifies) rather than `tests/services/`, mirroring `tests/services/test_normalization.py`'s existing no-DB pure-unit-test pattern for `normalize_flawchess_game`.

## Deviations from Plan

None — plan executed exactly as written. All three tasks matched their `<behavior>`/`<action>` specs; all acceptance criteria (grep checks for chess.js method usage, separate exports, verbatim copy strings) passed on the first implementation without rework.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
`botGameEnd.ts`, `botDrawGate.ts`, and `botGamePgn.ts` are ready for `useBotGame` (plan 04) to compose directly: end-condition detection + result copy, the draw-throttle/accept-gate pair, and the finished-PGN builder are all pure and fully unit-tested in isolation, with no React/hook dependencies to untangle. The PGN builder's backend acceptance is proven now (not deferred to Phase 171 discovery). No blockers for the next plan in this phase.

## Self-Check: PASSED

All 7 created files confirmed present on disk; all 3 task commit hashes (`4b685a39`, `bde20017`, `93247696`) confirmed in `git log --oneline --all`; all three plan-level verification commands (frontend vitest x3, `npx tsc -b`, `npm run lint`, `uv run pytest -n auto tests/test_bot_pgn_clk_roundtrip.py`) re-run and green.

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*
