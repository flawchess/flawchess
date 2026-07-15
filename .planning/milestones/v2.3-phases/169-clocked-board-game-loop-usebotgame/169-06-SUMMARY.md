---
phase: 169-clocked-board-game-loop-usebotgame
plan: 06
subsystem: frontend-ui
tags: [react, react-router, radix-dialog, chess-clock, lazy-route]

requires:
  - phase: 169 (plan 02)
    provides: "botGameEnd.ts (resultCopy(outcome, userColor) + BotGameOutcome) — the dialog/strip title text comes from here verbatim, never re-derived"
  - phase: 169 (plan 04)
    provides: "useBotGame(settings) full state+callback contract (position, moveHistory, liveGamePly, viewedPly, clocks, outcome, attemptMove, viewPly, returnToLive, resign, offerDraw, newGame)"
  - phase: 169 (plan 05)
    provides: "ClockDisplay, MoveListPanel, GameControls presentational components + CLOCK_LOW_TIME_URGENT theme constant"
provides:
  - "GameResultDialog — dismissible WDL-colored-title result dialog with New game (default) + Analyze this game (brand-outline) actions"
  - "GameResultStrip — persistent post-dismiss result bar replacing the in-game controls area, same actions as compact buttons"
  - "Bots.tsx — the assembled /bots page: ChessBoard + dual ClockDisplay + MoveListPanel + GameControls + result surfaces, behind a hardcoded-settings D-14 stub"
  - "The real /bots route, lazy-loaded in App.tsx, unlinked from nav"
affects: [170-localstorage-resume, 171-bots-page-setup-and-store]

tech-stack:
  added: []
  patterns:
    - "GameResultStrip REPLACES GameControls in the panel (not rendered alongside it) once the dialog is dismissed, per the UI-SPEC's 'replacing the normal in-game controls area' wording — GamePanel's showResultStrip ternary picks exactly one of the two, never both"
    - "Bots.tsx renders a SINGLE mounted tree (isDesktop boolean via matchMedia, mirroring Analysis.tsx's useIsMobile precedent) rather than two CSS-hidden trees, because ClockDisplay/MoveListPanel/GameControls carry fixed (non-parameterizable) data-testids that would collide if both mobile and desktop copies existed in the DOM simultaneously"
    - "renderMobileLayout/renderDesktopLayout are plain module-scope functions taking pre-built ReactElement values (botClock/userClock/board/panel) — no hooks inside them — keeping BotsPage's own JSX under the CLAUDE.md nesting/LOC guidance without needing a context object to thread state"

key-files:
  created:
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/GameResultStrip.tsx
    - frontend/src/pages/Bots.tsx
  modified:
    - frontend/src/App.tsx
    - .planning/REQUIREMENTS.md

key-decisions:
  - "GameControls' drawCooldownActive prop is always passed false, with canOfferDraw={game.canOfferDraw} carrying the full D-04 cooldown gate — useBotGame exposes only one combined accept-gate signal (canOfferDrawGate(movesSinceLastDecline)), so there is no separate general-gate signal at the page level distinct from the cooldown; GameControls' own drawOfferDisabled = !canOfferDraw || drawCooldownActive collapses correctly to !canOfferDraw either way, this mapping just avoids a confusing double negation"
  - "D-14 stub settings: botElo 1500, blend 0.5, a lichess 5+3 blitz preset (baseSeconds 300 / incrementSeconds 3), userColor 'white' — the game starts immediately on route load (useBotGame has no idle state), so no explicit 'Start game' button was added; Phase 171 replaces this whole constant with the real setup screen"
  - "unlockAudio() is called from Bots.tsx's own onPointerDown handler on the page container (guarded by a ref so it only fires once), in addition to useBotGame's existing internal call from attemptMove — belt-and-suspenders so audio unlocks even if the user interacts with GameControls (mute/resign/draw) before ever touching the board"
  - "/bots is wrapped in its own inline <Suspense> at the route element (App.tsx has no top-level Suspense boundary around <AppRoutes/>, and AnalysisRoute's Suspense wrapper only exists because it also needs to read the ?line= search param to key the page — /bots needs no such param-driven remount, so a bare inline Suspense is sufficient and simpler)"
  - "PLAY-09's REQUIREMENTS.md traceability row is updated from 'Partial ... the result screen itself lands in Plan 06' to 'Complete' — this plan is the one the earlier partial note pointed to; requirements.mark-complete reported the checkbox already checked (no-op), so the traceability table's free-text status column was updated manually since the tool does not rewrite custom prose notes"

requirements-completed: [PLAY-09]

coverage:
  - id: D1
    description: "On game end a dismissible result dialog shows the outcome+reason (colored win/loss/draw title from resultCopy) with 'New game' (default, primary) and 'Analyze this game' (brand-outline, secondary) actions; dismissing reveals the final board and a persistent GameResultStrip keeps both actions reachable, replacing the in-game controls area"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "npx tsc -b && npm run lint (frontend/src/components/bots/GameResultDialog.tsx, GameResultStrip.tsx)"
        status: pass
    human_judgment: true
    rationale: "No component test exists for GameResultDialog/GameResultStrip in this plan (presentational-only, wired to already-tested resultCopy/theme tokens) — grep-verified structural correctness (resultCopy import, WDL token usage, Button variants, testids, no text-xs) via the task's own acceptance criteria, all passing. The actual dismiss/reveal interaction, WDL title coloring on a real dialog render, and strip-replaces-controls behavior need a human/real-device check at end-of-phase UAT."
  - id: D2
    description: "'Analyze this game' deep-links to /analysis with the game's move line via buildAnalysisLineUrl; 'New game' restarts the hardcoded-settings game via useBotGame.newGame()"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "npx tsc -b (frontend/src/pages/Bots.tsx) — grep confirms buildAnalysisLineUrl(game.moveHistory) call site and game.newGame wiring on both dialog and strip"
        status: pass
    human_judgment: true
    rationale: "No test exercises the actual navigate() call or a real /analysis?line= round-trip in a browser — buildAnalysisLineUrl itself is already unit-tested elsewhere; this plan only wires it. Confirmed via a dev-server fetch that /bots serves 200 (SPA shell); the full click-through-to-/analysis flow needs a human/real-device check at end-of-phase UAT."
  - id: D3
    description: "The game ships on a real lazy-loaded /bots route, unlinked from nav, behind a minimal hardcoded-settings start stub"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b && npm run build (produces a separate Bots-*.js lazy chunk); grep confirms no nav-* testid or Link referencing /bots was added"
        status: pass
      - kind: integration
        ref: "node -e fetch('http://localhost:5174/bots') returned 200 against a temporary local dev server"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bots.tsx wires useBotGame + ClockDisplay/MoveListPanel/GameControls + result components + ChessBoard, gating board input on turn+live, with a responsive single-mounted-tree layout (bot clock above/user below board on mobile, side column on desktop)"
    requirement: "PLAY-09"
    verification:
      - kind: unit
        ref: "npx tsc -b && npm run lint (frontend/src/pages/Bots.tsx); grep confirms onPieceDrop={game.attemptMove} and data-testid=\"bots-page\""
        status: pass
    human_judgment: true
    rationale: "Board-input gating off the live position is structural (attemptMove itself returns false — no page-level gating code needed) and covered by Plan 04's own useBotGame.test.ts turn-gate suite; the actual playable end-to-end game flow (drag/click a move, watch the bot respond, clocks tick, game ends, dialog/strip appear) has not been exercised in a real browser this plan — appropriate for end-of-phase human-verify UAT."

duration: 22min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 06: Game-End Result UI + Bots Page Assembly Summary

**GameResultDialog/GameResultStrip (WDL-colored result screen with New game + Analyze deep-link) plus the assembled Bots.tsx page wiring useBotGame to ChessBoard, dual ClockDisplay, MoveListPanel, and GameControls behind a lazy, nav-unlinked `/bots` route.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-12T20:09:20Z
- **Completed:** 2026-07-12T20:31:00Z
- **Tasks:** 3
- **Files modified:** 4 (3 new, 1 modified) plus a REQUIREMENTS.md traceability update

## Accomplishments
- `GameResultDialog.tsx` — a dismissible `Dialog` shown on game end, title = `resultCopy(outcome, userColor)` (never re-derived) colored by the matching `WDL_WIN`/`WDL_LOSS`/`WDL_DRAW` token as text color only, no body prose beyond the title. Actions: "Analyze this game" (`brand-outline`, left) and "New game" (`default`, right — primary on the right per the existing dialog action-row convention). Dismissible via the existing `Dialog`'s X/outside-click, revealing the final board underneath.
- `GameResultStrip.tsx` — a thin `--secondary`-background inline bar with the same `resultCopy` text at Body size and the same two actions as compact buttons, rendered by `Bots.tsx`'s `GamePanel` in place of `GameControls` once the dialog is dismissed (per the UI-SPEC's "replacing the normal in-game controls area" wording), persisting until "New game" is clicked.
- `Bots.tsx` — the assembled `/bots` page (default export). D-14 stub: a hardcoded `BotGameSettings` (botElo 1500, blend 0.5, a lichess 5+3 blitz preset, userColor white) fed directly into `useBotGame`, which starts the game immediately on route load. Renders `ChessBoard` (position/onPieceDrop wired to the hook's viewed FEN/`attemptMove`, flipped when userColor is black), two `ClockDisplay` instances (bot/user, remaining-ms/active/thinking derived from the hook state), `MoveListPanel` (liveGamePly/viewedPly/viewPly/returnToLive), and `GameControls`/`GameResultStrip` via a shared `GamePanel` helper. A single mounted tree (`useIsDesktop` matchMedia hook, mirroring `Analysis.tsx`'s `useIsMobile` precedent) switches between a mobile layout (bot clock above the board, user clock below) and a desktop layout (board + fixed-width side column) without ever double-mounting components that carry fixed `data-testid`s.
- `unlockAudio()` fires from the page's own first-pointer-gesture handler (in addition to `useBotGame`'s existing per-move unlock), and the Analyze CTA calls `navigate(buildAnalysisLineUrl(game.moveHistory))` (D-12).
- `App.tsx` gains a `BotsPage = lazy(() => import('./pages/Bots'))` import and a `<Route path="/bots">` wrapped in its own inline `<Suspense>`, matching `/analysis`'s guest-friendly access posture (not wrapped in `ImportRequiredRoute` or `SuperuserRoute`) and left entirely unlinked from nav (D-14) — verified via `npm run build` producing a separate `Bots-*.js` lazy chunk and a temporary dev-server fetch confirming `/bots` serves 200.

## Task Commits

Each task was committed atomically:

1. **Task 1: GameResultDialog + GameResultStrip (D-11, D-12, PLAY-09)** - `5708cea6` (feat)
2. **Task 2: Bots.tsx page — assemble board + clocks + move list + controls + result surfaces behind the D-14 stub** - `e01f3284` (feat)
3. **Task 3: Register the lazy /bots route in App.tsx, unlinked from nav (D-14)** - `d8c57187` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/components/bots/GameResultDialog.tsx` - dismissible game-end result dialog
- `frontend/src/components/bots/GameResultStrip.tsx` - persistent post-dismiss result strip
- `frontend/src/pages/Bots.tsx` - the assembled /bots page
- `frontend/src/App.tsx` - lazy `BotsPage` import + `/bots` route registration
- `.planning/REQUIREMENTS.md` - PLAY-09 traceability row updated to Complete

## Decisions Made
- `GameControls`'s `drawCooldownActive` is always passed `false`, with `canOfferDraw={game.canOfferDraw}` alone carrying the full D-04 cooldown gate — `useBotGame` exposes only one combined accept-gate signal, so there's no separate general-gate distinct from the cooldown at the page level.
- D-14 stub settings (botElo 1500, blend 0.5, lichess 5+3, userColor white) start the game immediately on route load — no "Start game" button, since `useBotGame` has no idle/not-yet-started state to gate on.
- `unlockAudio()` is called redundantly from both `Bots.tsx`'s own first-pointer-gesture handler and `useBotGame`'s internal per-move call — belt-and-suspenders so audio unlocks even from a GameControls interaction before the first board move.
- `/bots` gets its own inline `<Suspense>` at the route element rather than reusing `AnalysisRoute`'s wrapper pattern — that wrapper's only extra job is reading the `?line=` search param to key `AnalysisPage`, which `/bots` doesn't need.
- PLAY-09's REQUIREMENTS.md traceability row updated from "Partial ... lands in Plan 06" to "Complete" — `requirements mark-complete` reported the checkbox already set (no-op), so the free-text status column needed a manual edit since the tool doesn't rewrite custom prose.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' acceptance criteria passed on the first implementation without needing Rule 1-3 auto-fixes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The phase's full playable loop is now assembled end-to-end on `/bots`: `useBotGame` (Plan 04) → `ClockDisplay`/`MoveListPanel`/`GameControls` (Plan 05) → result surfaces + page assembly (this plan). Phase 170 (localStorage resume) and Phase 171 (setup screen/store-on-finish) can build directly on `Bots.tsx`'s structure — `BOT_GAME_SETTINGS` is the exact seam Phase 171 replaces with the real setup screen's chosen settings.
- Full frontend suite (`npm test -- --run`) is green: 148 test files, 1872 tests passed, no regressions from this plan's changes.
- `cd frontend && npx tsc -b && npm run lint && npm run build` all succeed; the `/bots` route builds a separate lazy chunk (`Bots-*.js`, ~16.5 kB) and was confirmed reachable (200) via a temporary local dev server.
- Coverage gaps flagged in this SUMMARY's `coverage:` block (`human_judgment: true` on D1/D2/D4) are the expected shape for a UI-assembly plan with no browser-automation tooling available in this session — the real playable end-to-end flow (drag/click moves, bot responses, clock ticking, dialog→strip transition, Analyze click-through to `/analysis`) needs a human/real-device check at end-of-phase UAT, per this project's `human_verify_mode = end-of-phase` default (no `checkpoint:human-verify` tasks exist in this plan).
- This plan closes out Phase 169's Wave 4 (final plan of 6/7 per ROADMAP wave numbering, but plan 06 of the phase's 7 plans overall). Confirm remaining plans in `.planning/phases/169-clocked-board-game-loop-usebotgame/` before declaring the phase complete.

## Self-Check: PASSED

- `[ -f frontend/src/components/bots/GameResultDialog.tsx ]` → FOUND
- `[ -f frontend/src/components/bots/GameResultStrip.tsx ]` → FOUND
- `[ -f frontend/src/pages/Bots.tsx ]` → FOUND
- `[ -f frontend/src/App.tsx ]` → FOUND (modified)
- `git log --oneline --all | grep -E "5708cea6|e01f3284|d8c57187"` → all three commits FOUND
- Acceptance criteria re-verified for all three tasks (grep checks for `resultCopy` import, `WDL_WIN`/`WDL_LOSS`/`WDL_DRAW`, `variant="default"`/`variant="brand-outline"`, `result-dialog`/`result-strip`/`btn-new-game`/`btn-analyze-game` testids, no `text-xs`, `BOT_GAME_SETTINGS` with `baseSeconds`/`incrementSeconds`, `onPieceDrop={game.attemptMove}`, `buildAnalysisLineUrl`, `unlockAudio`, `data-testid="bots-page"`, `import('./pages/Bots')`, `path="/bots"`, no `nav-` testid referencing `/bots`) — all PASS.
- Plan-level verification re-run: `cd frontend && npx tsc -b` clean; `npm run lint` clean (only pre-existing unrelated `coverage/` generated-file warnings); `npm run build` succeeds with a separate `Bots-*.js` lazy chunk; `npm test -- --run` → 148 files / 1872 tests passed.
- `git diff --name-only` across all three task commits shows only `frontend/src/components/bots/GameResultDialog.tsx`, `frontend/src/components/bots/GameResultStrip.tsx`, `frontend/src/pages/Bots.tsx`, `frontend/src/App.tsx` — no frozen engine file touched.

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*
