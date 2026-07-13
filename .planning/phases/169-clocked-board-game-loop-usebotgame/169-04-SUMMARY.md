---
phase: 169-clocked-board-game-loop-usebotgame
plan: 04
subsystem: frontend-hooks
tags: [react-hooks, chess.js, bot-play, wall-clock-timing, fischer-increment, sentry, vitest]

requires:
  - phase: 169 (plan 01)
    provides: "chessClock.ts pure timing/pacing primitives (increment, wall-clock delta, pause anchor-shift, D-05 synthetic-debit reconciliation, reveal delay, low-time detection)"
  - phase: 169 (plan 02)
    provides: "botGameEnd.ts (end-condition detection + result copy), botDrawGate.ts (D-04 throttle + D-01 accept-gate), botGamePgn.ts ([%clk]/Termination/Result PGN builder)"
  - phase: 169 (plan 03)
    provides: "sounds.ts audio module (playSound/useMuted/setMuted/unlockAudio) over vendored AGPLv3+ lila sfx clips"
  - phase: 166
    provides: "selectBotMove(fen, settings, deps, signal) frozen move-selection entry, AbortSignal cancellation contract"
  - phase: 168.5
    provides: "botBudget.ts shipped FLAWCHESS_BOT_* search-budget constants (locked from real measurement)"
provides:
  - "useBotGame(settings) — the orchestrating game-loop hook: turn-gated moves + Fischer increment, wall-clock dual clocks with hidden-tab pause + flag-on-time, 168.5 D-05 bot pacing (Promise.all reveal-delay + search, never-flag reconciled debit), all board end conditions, resign/draw per D-01..D-04, event sounds, and a serializable finished PGN"
  - "useBotGame.test.ts — 11 passing tests covering turn-gate/pacing/end-conditions/resign-draw/pgn-export with mocked selectBotMove/providers/sounds and fake-timer-driven time"
affects: [169-05-clockdisplay-and-game-controls-ui, 169-06-game-result-dialog, 170-localstorage-resume, 171-bots-page-setup-and-store]

tech-stack:
  added: []
  patterns:
    - "Bot-turn dispatch called imperatively from an effect keyed on activeColor (not a debounced-FEN-triggered effect like useFlawChessEngine) — selectBotMove runs exactly once per bot turn, harness-style"
    - "viewedPly/liveGamePly as two independent numbers (never overloading one ply pointer) for view-only scroll-back during play"
    - "movesSinceLastDecline (D-04 cooldown) and wouldBotAcceptDraw's near-equal+endgame gate (D-01) kept as two fully independent pieces of state/logic, resolved via a drawOfferPending effect rather than collapsed into one synchronous decision"

key-files:
  created:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts
  modified: []

key-decisions:
  - "D-01's 'reuse the grading provider it already has' implemented as a best-effort, non-blocking pool.grade(rootFen, [botUci]) call fired after each bot move commits, converting the result via evalToExpectedScore(evalCp, evalMate, botColor) into lastRootPracticalScoreRef — selectBotMove itself exposes no snapshot/practicalScore, only the resolved UCI, so this was the only available reuse path; defaults to a neutral 0.5 before any bot move resolves, which correctly falls through to the endgame gate (queens-off/moveNumber) rather than ever masking it"
  - "drawOfferPending is real observable state (not collapsed into offerDraw()'s synchronous call): offerDraw() sets it true (subject to the D-04 button-level throttle), a separate effect resolves the wouldBotAcceptDraw decision and sets it back to false — gives a genuine two-render pending window even though the underlying decision is computed synchronously from a cached score"
  - "commitMove(move, mover, debitMs) is one shared function for BOTH the user move path (debitMs = raw wall-clock elapsed) and the bot move path (debitMs = reconcileBotDebitMs's max(real,synthetic) never-flag value) — the caller decides which debit to apply, avoiding duplicated clock/history/end-detection/sound logic across the two paths"
  - "Task 1's BOT_SEARCH_BUDGET constant (assembled from botBudget.ts's FLAWCHESS_BOT_* values) is threaded through the runBotTurnRef seam as a call argument (not just imported-and-unused) so the Task-1-only commit compiled cleanly under noUnusedLocals while still landing the Pitfall-6-safe direct botBudget import at the correct task boundary"
  - "Turn-anchor ref (turnStartedAtRef) is initialized to a 0 placeholder and set to the real Date.now() by a mount effect, not by the useRef initializer itself — eslint's react-hooks/purity rule forbids calling an impure function (Date.now()) during render; the effect is declared before the clock-tick effect so it runs first within the same commit"
  - "end-conditions test coverage is checkmate (Fool's mate, verifies winner derivation) + threefold repetition + flag-on-time, not all five board conditions — stalemate/fifty-move/insufficient-material detection is already exhaustively fixture-tested against chess.js directly in botGameEnd.test.ts (Plan 02); useBotGame's own suite only needs to prove the single detectEndCondition call site wires outcomes through to state correctly, which the decisive + non-decisive cases already demonstrate"

requirements-completed: [PLAY-03, PLAY-04, PLAY-05, PLAY-06, PLAY-07, PLAY-08, PLAY-09]

coverage:
  - id: D1
    description: "attemptMove turn-gates moves (rejects off-turn and off-live-position attempts), auto-promotes to queen, and applies the Fischer increment on a legal move"
    requirement: "PLAY-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#turn-gate"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dual wall-clock clocks recomputed from computeElapsedMs (never accumulated ticks), hidden-tab pause shifts the turn anchor, flag-on-time ends the game"
    requirement: "PLAY-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#end-conditions > ends the game with a timeout when the active side's clock reaches zero"
        status: pass
    human_judgment: true
    rationale: "The visibility-pause anchor-shift itself (shiftAnchorForPause) is unit-tested against chessClock.ts directly in Plan 01; useBotGame's own visibilitychange listener wiring has no jsdom-simulable document.visibilityState toggle test in this suite — real-device/browser verification is appropriate at end-of-phase UAT."
  - id: D3
    description: "Bot paces via Promise.all(selectBotMove, reveal-delay) — never a race — with isBotThinking derived from the real in-flight promise, and a max(real,synthetic) never-flag debit on resolve"
    requirement: "PLAY-05"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#pacing"
        status: pass
    human_judgment: false
  - id: D4
    description: "All board-derived end conditions (checkmate w/ correct winner, stalemate, threefold, fifty-move, insufficient material) plus flag-on-time propagate to state via detectEndCondition + the loop's own clock check"
    requirement: "PLAY-06"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#end-conditions"
        status: pass
    human_judgment: true
    rationale: "Only checkmate + threefold + flag-on-time are exercised end-to-end in this suite (stalemate/fifty-move/insufficient-material are exhaustively fixture-tested against chess.js directly in Plan 02's botGameEnd.test.ts) — a human reviewer should confirm this scope decision is acceptable, or a follow-up can add the remaining three scripted sequences."
  - id: D5
    description: "resign()/offerDraw() implement D-01 (bot accept-gate) and D-04 (cooldown throttle + confirmed resign); the bot never resigns or offers a draw itself"
    requirement: "PLAY-07"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resign-draw"
        status: pass
    human_judgment: false
  - id: D6
    description: "Event sounds (move/capture/check/game-end/low-time/draw-declined) fire on the right transitions honoring mute, with unlockAudio() called from the first user gesture"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resign-draw > offerDraw() is blocked by the D-04 cooldown immediately after a decline"
        status: pass
    human_judgment: true
    rationale: "Only the draw-declined sound event is asserted directly in this suite (via a mocked playSound spy); move/capture/check/game-end/low-time dispatch sites are implemented per the plan's behavior spec but not independently asserted per-event here — the underlying sounds.ts asset dispatch is exhaustively unit-tested in Plan 03; a human/real-device check (Pitfall 4's iOS unlock) is appropriate at end-of-phase UAT."
  - id: D7
    description: "On game end, state.pgn is a serializable finished PGN with both-color [%clk h:mm:ss] annotations and the correct [Termination]/[Result] headers"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#pgn-export"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 04: useBotGame Game-Loop Hook Summary

**`useBotGame(settings)` — the full clocked bot-game orchestrator composing chess.js, the frozen `selectBotMove` engine core, and the plan-01/02/03 pure modules into turn-gated moves, wall-clock dual clocks, 168.5 never-flag bot pacing, all end conditions, D-01..D-04 resign/draw, event sounds, and a backend-valid finished PGN.**

## Performance

- **Duration:** 23 min
- **Started:** 2026-07-12T19:34:56Z
- **Completed:** 2026-07-12T19:58:17Z
- **Tasks:** 3
- **Files modified:** 2 (both new)

## Accomplishments
- `useBotGame.ts` exports `BotGameSettings`, `UseBotGameState`, and the `useBotGame(settings)` hook exactly per the plan's artifact contract — `attemptMove`/`viewPly`/`returnToLive`/`resign`/`offerDraw`/`newGame` callbacks plus the full state shape (position, moveHistory, liveGamePly, viewedPly, isBotThinking, whiteClockMs, blackClockMs, activeColor, outcome, pgn, drawOfferPending, canOfferDraw).
- Turn-gated move commit (auto-queen promotion, Fischer increment) shared between the user and bot paths via one `commitMove(move, mover, debitMs)` function, with `detectEndCondition` wired at the single call site both paths funnel through.
- Wall-clock dual clocks recomputed every ~100ms from `computeElapsedMs` (never accumulated tick counts), a `visibilitychange` listener shifting the turn anchor during hidden-tab pauses, and flag-on-time as the one loop-owned end condition.
- Bot-turn dispatch mirrors `useFlawChessEngine.ts`'s provider-lifecycle pattern (mount-once `createWorkerPool`/`createMaiaQueue`, terminated on unmount) but calls `selectBotMove` imperatively per turn (not via a debounced-FEN effect), with a fresh `AbortController` every turn and `Promise.all([selectBotMove(...), reveal-delay])` — never `Promise.race` — so a long contested think genuinely shows real-time ticking, not a premature reveal.
- D-05's never-flag reconciliation (`reconcileBotDebitMs(realElapsedMs, computeSyntheticDebitMs(...), botRemainingMs)`) is applied on every bot move; D-01's draw-accept score is refreshed best-effort via a non-blocking `pool.grade` call after each bot move.
- `resign()`/`offerDraw()` implement D-01 (near-equal + endgame gate) and D-04 (cooldown throttle, resolved via a real `drawOfferPending` state transition) — the bot itself never resigns or offers a draw (D-02/D-03 hold structurally: no such code path exists on the bot's side).
- Event sounds (move/capture/check/game-end/low-time/draw-declined) fire per the D-09 spec, honoring mute via the frozen `sounds.ts` module; `unlockAudio()` fires from the first `attemptMove` call (Pitfall 4).
- On game end, `finalizeBotPgn` produces `state.pgn` with both-color `[%clk h:mm:ss]` annotations and the correct `[Termination]`/`[Result]` headers.
- 11 passing unit tests (turn-gate ×3, pacing ×1, end-conditions ×3, resign-draw ×3, pgn-export ×1) with `selectBotMove`/providers/sounds mocked and all timing driven by fake timers — stable across 3 consecutive runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: useBotGame core — state, move-commit + turn-gate, dual clocks, visibility pause, end detection** - `0efb0b7f` (feat)
2. **Task 2: useBotGame bot turn — provider bring-up, D-05 pacing, resign/draw, sounds, PGN export** - `067e6a27` (feat)
3. **Task 3: useBotGame tests — turn-gate, pacing, end-conditions, resign-draw, pgn-export** - `cfc81e83` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/hooks/useBotGame.ts` - the orchestrating game-loop hook (381 → 601 lines across the two feature commits)
- `frontend/src/hooks/__tests__/useBotGame.test.ts` - 11 unit tests covering all five required behavior tokens

## Decisions Made
- D-01's draw-accept score is refreshed via a best-effort, non-blocking `pool.grade(rootFen, [botUci])` call after each bot move (since `selectBotMove` exposes no snapshot/practicalScore, only the resolved UCI) — defaults to a neutral 0.5 that correctly falls through to the endgame gate before any bot move has resolved.
- `drawOfferPending` is genuine observable state (a real two-render pending window via a resolution effect), not collapsed into `offerDraw()`'s synchronous call, even though the underlying accept/decline decision is computed instantly from a cached score.
- `commitMove(move, mover, debitMs)` is shared by both the user and bot move paths — the caller supplies raw elapsed time or the D-05 reconciled debit; all clock/history/end-detection/sound logic lives in one place.
- `turnStartedAtRef` is initialized to a placeholder and set to the real `Date.now()` by a mount effect (declared before the clock-tick effect) rather than in the `useRef` initializer itself, to satisfy eslint's `react-hooks/purity` rule (no impure calls during render).
- `end-conditions` test coverage is checkmate + threefold + flag-on-time (not all five board conditions) — stalemate/fifty-move/insufficient-material are already exhaustively fixture-tested against chess.js directly in Plan 02's `botGameEnd.test.ts`; this suite proves the single `detectEndCondition` wiring point, which the decisive and non-decisive cases already demonstrate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `Date.now()`/ref-read-during-render eslint failures (react-hooks/purity, react-hooks/refs)**
- **Found during:** Task 1
- **Issue:** Initializing `turnStartedAtRef` with `useRef(Date.now())` and the clock-ms `useState`s with `useState(clockBaseRef.current.white)` both violate this project's strict ESLint react-hooks rules (calling an impure function, or reading a ref's value, during render).
- **Fix:** `turnStartedAtRef` now initializes to a `0` placeholder and is set to the real `Date.now()` by a dedicated mount effect declared before the clock-tick effect (guaranteeing correct ordering within the same commit); the clock `useState`s now derive their initial value directly from `settings.baseSeconds * 1000` instead of reading the ref.
- **Files modified:** frontend/src/hooks/useBotGame.ts
- **Verification:** `npx eslint src/hooks/useBotGame.ts` clean; `npx tsc -b` clean.
- **Committed in:** 0efb0b7f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** No scope change — a lint-compliance fix internal to Task 1's own implementation, required for the task's own `<verify>` gate to pass.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `useBotGame.ts`'s state + callback contract is ready for Plan 05 (dual-clock/game-controls UI) and Plan 06 (result dialog) to consume directly — every field the artifacts block specified is present and typed.
- Game state remains serializable (aside from callback identities) for Phase 170's localStorage resume work — `moveHistory`/`viewedPly`/`liveGamePly`/clock values/`outcome`/`pgn` are all plain JSON-safe values; only `chessRef` itself is a class instance, and it is fully reconstructable from `moveHistory` (SAN replay) at resume time.
- The finished PGN's shape is proven backend-acceptable by Plan 02's `tests/test_bot_pgn_clk_roundtrip.py`; Phase 171's store-on-finish POST can consume `state.pgn` unchanged.
- No frozen engine file (`useFlawChessEngine.ts`, any `lib/engine/*` file) was touched — verified via `git diff --name-only` after each task.
- Two known coverage gaps are flagged in this SUMMARY's `coverage:` block (`human_judgment: true`) for the verifier: (1) the visibility-pause hidden-tab wiring has no jsdom-simulable test in this suite (the underlying `shiftAnchorForPause` math is unit-tested in Plan 01); (2) only the `draw-declined` sound event is asserted via a spy in this suite (the other five dispatch sites are implemented per spec but not independently asserted here, and the underlying asset-dispatch logic is exhaustively tested in Plan 03). Both are reasonable candidates for the phase's end-of-phase human-verify UAT rather than blocking this plan.

## Self-Check: PASSED

- `[ -f frontend/src/hooks/useBotGame.ts ]` → FOUND
- `[ -f frontend/src/hooks/__tests__/useBotGame.test.ts ]` → FOUND
- `git log --oneline --all | grep -E "0efb0b7f|067e6a27|cfc81e83"` → all three commits FOUND
- Acceptance criteria re-verified: `cd frontend && npx tsc -b` → zero errors; `npx vitest run src/hooks/__tests__/useBotGame.test.ts` → 11/11 passed (3 consecutive runs, no flake); `grep -n "Promise.all" useBotGame.ts` present / `Promise.race` absent; `grep -n "reconcileBotDebitMs"` present; `grep -n "source: 'bot-game'"` present (×2, both catch blocks); `git diff --name-only` across all three task commits shows only `frontend/src/hooks/useBotGame.ts` and `frontend/src/hooks/__tests__/useBotGame.test.ts` — no frozen engine file touched.
- Plan-level verification re-run: `npx tsc -b` clean; `npx vitest run src/hooks/__tests__/useBotGame.test.ts` green; `npm run lint` clean (only pre-existing unrelated `coverage/` generated-file warnings).

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*
