---
phase: 182-style-levers
plan: "07"
subsystem: frontend-engine
tags: [flawchess-engine, bot-style, style-levers, useBotGame, resign, contempt, opening-book]

# Dependency graph
requires:
  - phase: 182-02
    provides: "wouldBotAcceptDraw contempt param + wouldBotResign predicate + RESIGN_MIN_FULLMOVE (botDrawGate.ts)"
  - phase: 182-05
    provides: "BOT_STYLE_BUNDLES — the 4 named style-to-BotStyleParams bundles (botStyleBundles.ts)"
  - phase: 182-06
    provides: "BotSettings.style?: BotStyleParams + selectBotMove.ts's blend<=0/search regime hooks"
provides:
  - "BotGameSettings.style?: BotStyleParams — the optional bot-only style layer useBotGame accepts"
  - "resolveBookMove threads style through styleNameFor()->styleLinesFor()->styleBookWeighting(), falling back to the default maiaPolicyWeighting"
  - "settings.style also reaches selectBotMove's search call, so STYLE-03/04's prior-reweighting/score-shaping hooks (Plan 06) are live in real play, not just tests"
  - "Draw-accept effect threads settings.style?.contempt ?? 0 into wouldBotAcceptDraw"
  - "consecutiveLowScoreTurnsRef per-game hysteresis ref + wouldBotResign check inside the pool.grade().then() callback, dispatching finalizeGame({reason:'resignation'})"
affects: ["183-persona-registry"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reverse-name-lookup bridge: BotGameSettings.style is the bare numeric BotStyleParams (matching selectBotMove's shape so the SAME object threads unchanged into search); styleNameFor() resolves it back to its Style key by reference-equality against BOT_STYLE_BUNDLES only where a NAME is needed (the book's styleLinesFor lookup) — no name ever reaches engine-layer transforms (D-01)."
    - "Ref-latch hysteresis mutated only inside the existing best-effort pool.grade().then() callback, gated on settings.style, reset in newGame() — mirrors lastRootPracticalScoreRef/hasLeftBookRef exactly (Pitfall 3)."

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts

key-decisions:
  - "BotGameSettings.style is typed as the bare BotStyleParams (not a {name, params} wrapper) so the identical object threads unchanged into selectBotMove's own style-gated regime hooks (Plan 06). Since BotStyleParams carries no style name (D-01: engine code stays numeric-only) but styleOpeningLines.ts's curated book lines are keyed by Style name, resolveBookMove needs a one-hop bridge: a new module-scope styleNameFor() helper reverse-resolves the params object back to its Style key by reference equality against BOT_STYLE_BUNDLES. A style not sourced from a bundle (a future Custom-mode literal, PERS-04, out of scope) resolves to undefined and silently falls back to the default maiaPolicyWeighting — never a crash."
  - "Also threaded settings.style into the selectBotMove() call at the runBotTurn search call site (not explicitly listed among this plan's 3 named seams, but flagged by 182-06-SUMMARY.md's key-decisions as the missing wire needed for STYLE-03/04 to ever fire in live play, not just unit tests/the calibration harness). Applied under deviation Rule 2 (missing critical functionality) — without it, Plan 06's fully-implemented and tested prior-reweighting/score-shaping hooks would be permanently dead code in production. Byte-identical when settings.style is undefined (D-03)."
  - "Resign hysteresis increment/reset reads ONLY the FRESH score computed in the same pool.grade().then() callback (never a stale prior-turn value from lastRootPracticalScoreRef) — satisfies Task 3's must-have that the counter increments/resets off a fresh grade, and keeps the book-ply null-sentinel invariant intact (the whole block is unreachable when fromBook is true, since the callback is never even scheduled for a book move)."

patterns-established:
  - "A bare numeric style-params object threaded through both the game-loop orchestrator (useBotGame.ts) and the engine orchestrator (selectBotMove.ts) unchanged; any seam needing the style's NAME (not its knobs) does a one-hop reverse lookup against the canonical bundle map, kept local to the orchestrator that needs it."

requirements-completed: [STYLE-01, STYLE-02]

coverage:
  - id: D1
    description: "BotGameSettings gains an optional style?: BotStyleParams field; undefined runs the exact current code path (default book, Phase 169 draw gate, never resigns)"
    requirement: "STYLE-05"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts — full 71-test file green under DEFAULT_SETTINGS (no style), including the new 'never resigns for an unstyled game' test"
        status: pass
    human_judgment: false
  - id: D2
    description: "resolveBookMove passes a styleBookWeighting(styleLinesFor(styleName, side), history, bookBoost) closure when style resolves to a known bundle; falls back to the default maiaPolicyWeighting otherwise (D-03 byte-identical for undefined/unrecognized style)"
    requirement: "STYLE-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#book (existing describe block, unchanged and green) + tsc -b source assertion at the resolveBookMove call site"
        status: pass
    human_judgment: false
  - id: D3
    description: "Draw-accept effect threads settings.style?.contempt ?? 0 into wouldBotAcceptDraw; undefined style keeps the exact pre-182 0.5 accept target"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#resign-draw — 'a queens-off position satisfying wouldBotAcceptDraw yields a draw-by-agreement outcome' (unchanged, green under DEFAULT_SETTINGS / contempt 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "consecutiveLowScoreTurnsRef hysteresis counter increments only on a fresh at/below-threshold grade and resets on an above-threshold one; declared beside the other per-game ref latches and reset in newGame()"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#styled resign wiring (STYLE-02) — 'increments the hysteresis counter only on a fresh at/below-threshold grade, and resets on an above-threshold grade'"
        status: pass
    human_judgment: false
  - id: D5
    description: "wouldBotResign fires inside the settings.style guard; when true, finalizeGame({reason:'resignation', winner: settings.userColor}) ends the game exactly once the hysteresis floor is reached past RESIGN_MIN_FULLMOVE, and stays stable afterward"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#styled resign wiring (STYLE-02) — 'fires finalizeGame with reason:resignation exactly once the counter reaches hysteresisFloor past RESIGN_MIN_FULLMOVE'"
        status: pass
    human_judgment: false
  - id: D6
    description: "An unstyled game (DEFAULT_SETTINGS) never reaches the resign branch under the identical low-score grade sequence that resigns a styled bot"
    requirement: "STYLE-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#styled resign wiring (STYLE-02) — 'never resigns for an unstyled game (DEFAULT_SETTINGS) under the same low-score grade sequence'"
        status: pass
    human_judgment: false

# Metrics
duration: 55min
completed: 2026-07-22
status: complete
---

# Phase 182 Plan 07: Wire Style Layer into useBotGame Summary

**Threads the optional `BotGameSettings.style?: BotStyleParams` through three game-loop seams — style-aware opening-book weighting, contempt-shifted draw acceptance, and a per-game resign-hysteresis ref — while also wiring the same object into `selectBotMove`'s search call so Plan 06's prior-reweighting/score-shaping hooks fire in live bot play, not just unit tests.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified:** 2 (`useBotGame.ts`, `useBotGame.test.ts`)

## Accomplishments
- `BotGameSettings.style?: BotStyleParams` — undefined runs today's exact code path everywhere (D-03).
- `resolveBookMove` composes `styleBookWeighting(styleLinesFor(styleName, side), moveHistorySan, style.bookBoost)` over the default `maiaPolicyWeighting` when a style resolves to a known bundle; falls through to the default otherwise.
- `settings.style` also reaches `selectBotMove`'s `{ elo, blend, budget, style }` search call, completing STYLE-03/04's live-play wiring that Plan 06 built and tested but explicitly deferred activating.
- Draw-accept effect threads `settings.style?.contempt ?? 0` into `wouldBotAcceptDraw`.
- New `consecutiveLowScoreTurnsRef` per-game ref-latch (mirrors `lastRootPracticalScoreRef`/`hasLeftBookRef`), incremented/reset only from a fresh grade inside the existing `pool.grade().then()` callback, reset in `newGame()`.
- `wouldBotResign` check dispatches `finalizeGame({reason:'resignation', winner: settings.userColor})` when the hysteresis floor is reached past `RESIGN_MIN_FULLMOVE`, gated entirely on `settings.style`.
- New `describe('styled resign wiring (STYLE-02)')` block (3 tests) proving the HOOK wiring end to end via a real 44-ply generated chess sequence, plus a manual revert-proof performed during authoring (both the reset branch and the `settings.style` guard were temporarily removed and confirmed to turn the relevant test red, then restored).

## Task Commits

Each task was committed atomically:

1. **Task 1: BotGameSettings.style + style-aware book weighting in resolveBookMove** - `981985c7` (feat)
2. **Task 2: Contempt in draw-accept + resign hysteresis ref + resign check** - `08a972fc` (feat)
3. **Task 3: useBotGame-level behavioral test for the styled-resign wiring** - `701db94e` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/hooks/useBotGame.ts` - `BotGameSettings.style?`, `styleNameFor()` bridge helper, style-aware `resolveBookMove`, `style` threaded into the `selectBotMove` search call, contempt-threaded draw accept, `consecutiveLowScoreTurnsRef` + resign check
- `frontend/src/hooks/__tests__/useBotGame.test.ts` - new `styled resign wiring (STYLE-02)` describe block (3 tests) + `BotStyleParams` type import

## Decisions Made
See `key-decisions` in frontmatter — the `styleNameFor()` reverse-lookup bridge, threading `style` into the `selectBotMove` search call (deviation), and the fresh-grade-only hysteresis update.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Threaded `settings.style` into the `selectBotMove()` search call in `runBotTurn`**
- **Found during:** Task 1 (resolveBookMove wiring)
- **Issue:** The plan's 3 named seams (book, contempt, resign) did not include passing `settings.style` to the `selectBotMove()` call itself. But `182-06-SUMMARY.md`'s own key-decisions explicitly flagged this exact gap: "STYLE-03 left Pending... only exists once Plan 07 threads a resolved BotStyleParams from BotGameSettings.style into selectBotMove's settings.style at the actual play-loop call site." Without this one-line addition, Plan 06's fully-built and unit-tested prior-reweighting (STYLE-03) and score-shaping (STYLE-04) hooks would never fire in a real bot game — only in `selectBotMove.test.ts` and the calibration harness.
- **Fix:** Added `style: settings.style` to the `{ elo, blend, budget }` config object at the search call site. Byte-identical when `settings.style` is undefined (the field is optional).
- **Files modified:** `frontend/src/hooks/useBotGame.ts`
- **Verification:** `tsc -b` zero errors; full 71-test `useBotGame.test.ts` suite green under `DEFAULT_SETTINGS` (no style) — undefined-style behavior provably unchanged.
- **Committed in:** `981985c7` (Task 1 commit)

**2. [Rule 2 - Missing Critical] `styleNameFor()` reverse-lookup bridge for the book seam**
- **Found during:** Task 1 (resolveBookMove wiring)
- **Issue:** The plan's must-haves state `BotGameSettings.style?: BotStyleParams` (bare numeric knobs, no style name — matching `selectBotMove.ts`'s `BotSettings.style` shape from Plan 06) and separately instruct calling `styleBookWeighting(styleLinesFor(style, side), ...)`. But `styleLinesFor`'s signature requires a `Style` NAME key ('Attacker'/'Trickster'/'Grinder'/'Wall'), which `BotStyleParams` does not carry (D-01: engine code stays numeric-only, no style names) — the two requirements are structurally incompatible without a bridge.
- **Fix:** Added a module-scope `styleNameFor(style: BotStyleParams): Style | undefined` helper in `useBotGame.ts` that reverse-resolves a params object to its key by reference equality against `BOT_STYLE_BUNDLES` (the 4 canonical singleton bundles every real caller supplies, per D-02). No match (undefined style, or a future non-bundle `BotStyleParams`) falls back to the default `maiaPolicyWeighting` — a safe, silent degrade.
- **Files modified:** `frontend/src/hooks/useBotGame.ts`
- **Verification:** `tsc -b` zero errors; existing `describe('book')` tests (unchanged, still exercising the unstyled default path) stay green.
- **Committed in:** `981985c7` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 - missing critical functionality)
**Impact on plan:** Both closures were necessary to make the plan's stated seams actually functional/reachable in live play; neither changes scope beyond what the plan's own objective and the prior plan's SUMMARY already called for. No scope creep.

## Issues Encountered
- The Task 3 test's hand-transcribed 22-round move sequence initially had one round wrong (`b1c3` instead of `c3b1` at round 16), causing an illegal-move-adjacent silent divergence that made the resign test fail one round early. Caught by generating and verifying the sequence programmatically via a direct chess.js run before finalizing the test, then fixing the one transcription error.
- Per-task commits required temporarily reverting and reapplying Task 2's hunks (the two tasks touch closely interleaved regions of the same file) to keep each task's commit self-contained and independently verifiable, per the executor's atomic-commit protocol.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 182's three STYLE-01/02/03/04/05 engine-layer levers (opening book, draw contempt/resign, prior reweighting, score shaping) are now fully wired end to end into live bot play via `BotGameSettings.style` — nothing left dangling for Phase 183 to re-wire at the game-loop level.
- Phase 183 (Persona Registry & Bots Page) can set `BotGameSettings.style` directly from `BOT_STYLE_BUNDLES[personaStyle]` (or a future Custom-mode `BotStyleParams` literal) and every lever this phase built activates automatically.
- No blockers.

---
*Phase: 182-style-levers*
*Completed: 2026-07-22*

## Self-Check: PASSED
- FOUND: `.planning/phases/182-style-levers/182-07-SUMMARY.md`
- FOUND: commit `981985c7` (Task 1)
- FOUND: commit `08a972fc` (Task 2)
- FOUND: commit `701db94e` (Task 3)
