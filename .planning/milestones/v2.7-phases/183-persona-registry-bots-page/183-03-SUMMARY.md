---
phase: 183-persona-registry-bots-page
plan: 03
subsystem: bot-engine
tags: [react-hooks, typescript, chess.js, bot-personas, draw-offer, localstorage]

# Dependency graph
requires:
  - phase: 183-01
    provides: "PersonaId type (personaRegistry.ts) — the id union threaded through BotGameSettings.personaId"
  - phase: 183-02
    provides: "wouldBotOfferDraw(rootPracticalScore, chess, contempt, movesSinceOwnOffer) pure predicate + BOT_DRAW_OFFER_* constants (botDrawGate.ts)"
provides:
  - "BotGameSettings.personaId?: PersonaId — optional, additive, undefined for Custom mode (PERS-04)"
  - "Snapshot round-trip proof: a pre-183 personaId-less snapshot still validates at CURRENT_SNAPSHOT_VERSION === 1"
  - "botDrawOffer / acceptBotDraw / declineBotDraw on UseBotGameState — the bot's outgoing draw-offer UI contract"
  - "resolveBotDrawOfferUpdate — pure helper deciding raise-offer + cooldown-counter update, wired at the existing pool.grade().then() seam"
affects: [183-04, 183-05, 184-persona-calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New optional settings fields mirror style?'s doc-comment + undefined-is-Custom-mode contract verbatim (personaId now follows style)"
    - "Bot-owned per-game counters/latches (movesSinceOwnOfferRef, botDrawOfferRef) mirror consecutiveLowScoreTurnsRef/outcomeRef's caller-owned, ref-mutated-in-the-async-callback discipline — never React state read inside the stale-closure-prone pool.grade().then() continuation"
    - "Dense grade-callback logic branches extracted into pure top-level helper functions (resolveBotDrawOfferUpdate) rather than inlined, per CLAUDE.md nesting/logic-LOC limits"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/lib/__tests__/botGameSnapshot.test.ts

key-decisions:
  - "botDrawOffer modeled as a plain boolean (not an object) — sufficient for the Plan 05 banner to render (game state like moveHistory/liveGamePly is already available from the same hook); avoided an unused-field object per YAGNI"
  - "Auto-expire wired inside commitMove (shared by both attemptMove and runBotTurn) gated on mover === settings.userColor, rather than a separate effect — commitMove is the single seam every user move passes through, and the mover-color gate means a bot's own commit (which can raise a NEW offer moments later via the async grade callback) never clears the flag it is about to set"
  - "resolveBotDrawOfferUpdate extracted as a pure top-level function (score/chess/style/counter/flags in, {raiseOffer, nextMovesSinceOwnOffer} out) rather than inlined in the grade callback — keeps the already-dense pool.grade().then() body at its pre-existing nesting depth despite adding a second style-gated decision beside wouldBotResign"
  - "outcomeRef.current !== null (not a separate `resigns` check) gates 'game already over' in resolveBotDrawOfferUpdate — finalizeGame is synchronous, so a resignation this same turn is already reflected in outcomeRef by the time the offer check runs, with no extra flag needed"

patterns-established:
  - "A styled-bot behavior that must run at the existing single-grade seam (CR-02 discipline) is added as a sibling block inside the same `if (settings.style)` guard, never a second `.then()` or a second `pool.grade()` call"

requirements-completed: [PERS-02, PERS-04]

coverage:
  - id: D1
    description: "BotGameSettings gains an optional personaId?: PersonaId field; a Custom-mode game never sets it (undefined by construction), mirroring style?'s D-03 optional-everywhere contract"
    requirement: "PERS-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#personaId (Phase 183, PERS-02/PERS-04) > a Custom-mode settings object (no personaId, no style) still round-trips unchanged"
        status: pass
      - kind: other
        ref: "npx tsc -b (zero errors) — PersonaId imported from @/lib/personas/personaRegistry, no circular import (personaRegistry.ts does not import from useBotGame.ts)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A pre-183 snapshot lacking personaId round-trips through readSnapshot/isValidSnapshotShape to settings.personaId === undefined, with CURRENT_SNAPSHOT_VERSION unchanged at 1"
    requirement: "PERS-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#personaId (Phase 183, PERS-02/PERS-04) > a pre-183 snapshot object with no personaId key still validates at version 1 and reads back with settings.personaId === undefined"
        status: pass
      - kind: other
        ref: "git diff confirms CURRENT_SNAPSHOT_VERSION / isValidSettingsShape / isValidSnapshotShape are untouched in botGameSnapshot.ts (no diff to that file this plan)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A personaId round-trips intact through writeSnapshot/readSnapshot when present"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botGameSnapshot.test.ts#personaId (Phase 183, PERS-02/PERS-04) > a settings.personaId round-trips intact through writeSnapshot/readSnapshot"
        status: pass
    human_judgment: false
  - id: D4
    description: "The bot's outgoing draw-offer is computed inside the SAME post-move pool.grade().then() callback as wouldBotResign, under the same settings.style gate and the same controller.signal.aborted staleness guard — no second pool.grade() call site"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts (all 72 pre-existing tests pass unchanged — no resign/accept-draw regression)"
        status: pass
      - kind: other
        ref: "grep -n '\\.grade(fen' frontend/src/hooks/useBotGame.ts — exactly one real call site (line 1446), unchanged from pre-plan; the resolveBotDrawOfferUpdate call sits as a sibling block inside the same if (settings.style) guard, after the existing wouldBotResign block, inside the same controller.signal.aborted-guarded .then()"
        status: pass
    human_judgment: false
  - id: D5
    description: "The hook exposes bot-draw-offer state plus acceptBotDraw (ends the game as an agreed draw) and declineBotDraw (dismiss + reset the own-offer cooldown); a bot offer auto-clears on the user's next move"
    requirement: "PERS-02"
    verification:
      - kind: other
        ref: "Source review: botDrawOffer/acceptBotDraw/declineBotDraw added to UseBotGameState and the hook's return object; acceptBotDraw guards on outcomeRef.current before finalizeGame({reason:'draw', drawReason:'agreement'}); auto-expire wired in commitMove gated on mover === settings.userColor"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts (existing suite green — tsc -b confirms the new exports typecheck against UseBotGameState's shape)"
        status: pass
    human_judgment: true
    rationale: "No new dedicated unit tests were added for the offer-raise/accept/decline/auto-expire behavior itself (out of this plan's files_modified scope — Plan 05 wires the UI banner that will exercise this end to end); source-review + the unchanged pre-existing suite are the coverage this plan produced. Flagging for a human/verifier pass to confirm the behavior once Plan 05's banner makes it observable in the UI."
  - id: D6
    description: "A fresh game (newGame) resets the bot-offer state and the own-offer cooldown counter — no leak across games"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts (existing newGame-reset test coverage passes; botDrawOfferRef/movesSinceOwnOfferRef reset lines added alongside consecutiveLowScoreTurnsRef's pre-existing reset, same call site pattern)"
        status: pass
    human_judgment: false

# Metrics
duration: 11min
completed: 2026-07-22
status: complete
---

# Phase 183 Plan 03: Thread Persona Identity + Bot Outgoing Draw-Offer into useBotGame Summary

**Added optional `BotGameSettings.personaId` (version-safe snapshot round-trip proven) and wired Plan 02's `wouldBotOfferDraw` predicate into the existing post-move grade callback with `botDrawOffer`/`acceptBotDraw`/`declineBotDraw` state, no second `pool.grade()` call site.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-07-22T09:19:40Z
- **Completed:** 2026-07-22T09:29:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `BotGameSettings.personaId?: PersonaId` — additive optional field, doc-commented to mirror `style?`'s exact optional-everywhere/Custom-mode contract; only the id string is carried, never the full `Persona` object, and it is never derived from `settings.style` via reverse lookup (6 personas share one style bundle by reference).
- Proved via 3 new tests that `botGameSnapshot.ts`'s validators (`isValidSettingsShape`/`isValidSnapshotShape`) needed zero changes — they only assert pre-existing required fields, so the additive field flows through automatically, `CURRENT_SNAPSHOT_VERSION` stays at `1`, and a pre-183 personaId-less snapshot object still validates and reads back with `settings.personaId === undefined`.
- Wired `wouldBotOfferDraw` (Plan 02) into `runBotTurn`'s existing `pool.grade(fen, [uci]).then(...)` callback, as a sibling block immediately after the existing `wouldBotResign` check, inside the same `if (settings.style)` gate and the same `controller.signal.aborted` staleness guard — confirmed exactly one real `.grade(fen` call site remains in the file (line 1446), unchanged from pre-plan.
- `resolveBotDrawOfferUpdate` — a new pure top-level helper (mirroring `buildBotMoveDeps`'s extraction precedent) computing whether to raise a fresh offer and the resulting `movesSinceOwnOfferRef` update, keeping the already-dense grade callback at its pre-existing nesting depth.
- `botDrawOffer` state + `botDrawOfferRef` (an `outcomeRef`-style stale-closure-safe latch, since the async grade continuation can resolve after other state changes) + `movesSinceOwnOfferRef` (caller-owned cooldown counter, mirrors `consecutiveLowScoreTurnsRef`'s discipline exactly).
- `acceptBotDraw()` (guards on `outcomeRef.current`, then `finalizeGame({reason:'draw', drawReason:'agreement'})`) and `declineBotDraw()` (clears the pending flag; the cooldown already restarted when the offer was raised) added to `UseBotGameState`.
- Auto-expire wired at the `commitMove` seam (shared by `attemptMove` and `runBotTurn`), gated on `mover === settings.userColor` — a bot's own move commit never clears a flag it may be about to set moments later via the async grade callback.
- `botDrawOfferRef`/`botDrawOffer` state and `movesSinceOwnOfferRef` reset in `newGame()`, placed immediately after `consecutiveLowScoreTurnsRef`'s existing reset — no leak across games.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add BotGameSettings.personaId? and verify snapshot round-trip** - `7eaa8575` (feat)
2. **Task 2: Wire wouldBotOfferDraw + bot-offer state into the grade callback** - `bac059a7` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `frontend/src/hooks/useBotGame.ts` - `BotGameSettings.personaId?`, `resolveBotDrawOfferUpdate` helper, `botDrawOffer`/`acceptBotDraw`/`declineBotDraw` on `UseBotGameState`, wiring at the grade callback + `commitMove` auto-expire + `newGame()` reset
- `frontend/src/lib/__tests__/botGameSnapshot.test.ts` - 3 new tests: personaId round-trip, pre-183 backward-compat (version unchanged at 1), Custom-mode round-trip

## Decisions Made

- **`botDrawOffer` as a plain boolean, not an object:** the plan allowed either ("a small object/flag"). A boolean is sufficient — the Plan 05 banner already has access to every other piece of game state (moveHistory, activeColor, etc.) from the same hook, so a richer "live-offer state" object would carry no information the banner couldn't get elsewhere. Avoided an unused-field object per YAGNI.
- **Auto-expire lives in `commitMove`, not a separate effect:** `commitMove` is the single seam both `attemptMove` (user moves) and `runBotTurn` (bot moves) pass through, so gating on `mover === settings.userColor` there is simpler and more directly tied to "the user's next move" than a parallel effect watching `moveHistory`.
- **`outcomeRef.current !== null` (not a separate `resigns` boolean) gates "game already over" in `resolveBotDrawOfferUpdate`:** `finalizeGame` is synchronous, so if the resign branch just ran, `outcomeRef.current` is already set by the time the offer check executes in the same callback — no need to thread `resigns` through as a second flag.
- **`resolveBotDrawOfferUpdate` extracted as a pure top-level function:** the grade callback was already flagged in the plan itself as "already dense (CLAUDE.md nesting/logic-LOC limits)" — extracting keeps the new draw-offer decision as a single readable call rather than inline branching that would deepen the existing `.then() -> if(grade) -> if(settings.style)` nesting.

## Deviations from Plan

**1. [Rule 1 - Bug/inconsistency] Test file path in plan's `<verify>` block did not match the actual file on disk**
- **Found during:** Task 2 verification
- **Issue:** The plan's `<verify>` command referenced `src/hooks/__tests__/useBotGame.test.tsx`; the actual file is `src/hooks/__tests__/useBotGame.test.ts` (no `.tsx` — the hook test file has no JSX).
- **Fix:** Ran the correct `.ts` path; all 72 existing tests pass unchanged.
- **Files modified:** None (test-invocation path only, not a source change).
- **Verification:** `npm test -- --run src/hooks/__tests__/useBotGame.test.ts` — 72/72 pass.

None of the code changes themselves deviated from the plan's explicit `<action>` instructions — both tasks were implemented as specified.

---

**Total deviations:** 1 (test-file-path correction only, no source-code deviation)
**Impact on plan:** Zero impact on scope or behavior — purely a verification-command correction.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `BotGameSettings.personaId`, `botDrawOffer`, `acceptBotDraw`, `declineBotDraw` are all live on `UseBotGameState`, ready for Plan 04 (PersonaGrid/PersonaCard/setup wiring — consumes `personaId` to look up `PERSONA_REGISTRY`/`personaForId`) and Plan 05 (the draw-offer banner — consumes `botDrawOffer`/`acceptBotDraw`/`declineBotDraw` directly).
- No blockers. `botGameSnapshot.ts`'s validators, `CURRENT_SNAPSHOT_VERSION`, and `botDrawGate.ts` are all confirmed untouched by this plan's diff — Plan 04/05 start from an unmodified snapshot contract and draw-gate module.
- **Known gap flagged in coverage D5:** no dedicated unit tests exercise the raise/accept/decline/auto-expire sequence end-to-end (the existing 72-test suite covers resign/accept-draw regression only, since it predates this plan's new behavior and this plan's `files_modified` scope was `useBotGame.ts` + `botGameSnapshot.test.ts`, not a new `useBotGame.test.ts` block). Recommend a verifier/UAT pass once Plan 05's banner makes the behavior observable, or a follow-up test addition if this needs deterministic pre-UAT proof.

---
*Phase: 183-persona-registry-bots-page*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useBotGame.ts
- FOUND: frontend/src/lib/__tests__/botGameSnapshot.test.ts
- FOUND: commit 7eaa8575 (feat: Task 1 — personaId + snapshot round-trip)
- FOUND: commit bac059a7 (feat: Task 2 — wouldBotOfferDraw wiring)
