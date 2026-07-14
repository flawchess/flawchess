---
phase: 171-bots-page-setup-screen-nav
plan: 06
subsystem: ui
tags: [react, typescript, localStorage, vitest, rtl]

# Dependency graph
requires:
  - phase: 171-05
    provides: "SetupScreen component + SetupScreenProps ({ ownerKey, normalizedRating, onStart }) — the pre-game setup form"
  - phase: 171-03
    provides: "The reachable, never-locked /bots nav entry"
  - phase: 170
    provides: "ResumeGate + botGameSnapshot.ts (readSnapshot/clearSnapshot) + the D-04 snapshot-beats-setup precedence + the pending-store drain effect"
provides:
  - "BotsPage's setup/game phase switch: no snapshot -> SetupScreen; Start -> BotsGame mounted with the emitted settings; a snapshot always wins over setup (D-04 unchanged)"
  - "BotsGame.settings (required prop, no fallback) and BotsGame.onNewGame prop — the D-14 hardcoded BOT_GAME_SETTINGS stub is fully deleted"
  - "handleNewGame()/handleDiscard() both return to setup (D-11/D-13) instead of restarting a game in place"
affects: [171-07-store-on-finish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit phase state (startedSettings: BotGameSettings | null) alongside the existing boot/nonce state, rather than deriving 'show setup vs show game' from any single boolean — matches the plan's three co-existing gates (loading / resume / setup / started)"

key-files:
  created:
    - frontend/src/pages/__tests__/Bots.test.tsx
  modified:
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/SetupScreen.tsx

key-decisions:
  - "Fixed a stale BOT_GAME_SETTINGS doc-comment reference in SetupScreen.tsx (a Plan 05 leftover, not in this plan's files_modified) to satisfy this plan's own explicit whole-frontend grep gate (`grep -rc 'BOT_GAME_SETTINGS' frontend/src/` == 0) — a comment-only fix, no behavior change"
  - "handleDiscard() now also resets startedSettings to null (in addition to clearing the snapshot and bumping nonce) — belt-and-suspenders alongside the fact that startedSettings is structurally null whenever a snapshot exists, since the setup screen (the only place startedSettings gets set) is never rendered while `boot.resume !== null`"
  - "game.newGame left fully in place on the hook (untouched useBotGame.ts, verified via git diff --exit-code); a one-line comment at the useBotGame() call site in BotsGame documents that it is no longer reached from the UI (D-11) and that npm run knip is the arbiter — knip ran clean, no unused-export flag (newGame is a UseBotGameState object property, not a knip-visible module export, so it was never going to be flagged either way)"
  - "Bots.test.tsx mocks @/hooks/useBotGame with a hook that keeps its OWN React useState for outcome/live, rather than a static object — this lets a test flip outcome via a captured setter and observe BotsGame re-render exactly like the real hook would, without spawning a WorkerPool/Maia queue"

patterns-established:
  - "Controllable-fake-hook-with-internal-useState is now the established pattern for mocking a heavy stateful hook in a page-level RTL test (useBotGame here; a template for Plan 07's tests against the same mock)"

requirements-completed: [PLAY-02, PLAY-10]

coverage:
  - id: D1
    description: "With no snapshot, /bots renders SetupScreen (not a board, not an auto-started game); Start mounts BotsGame with exactly the settings chosen at setup (concrete color, seconds-based clocks) — the D-14 BOT_GAME_SETTINGS stub is deleted everywhere in the frontend"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#renders the setup screen when there is no snapshot"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#mounts the game with the settings chosen at setup"
        status: pass
      - kind: other
        ref: "grep -rc 'BOT_GAME_SETTINGS' frontend/src/ (0 matches)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A snapshot always wins over setup (170 D-04 unchanged): BotsGame mounts immediately with ResumeGate overlaid, and setup-screen is never rendered while a snapshot exists"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#snapshot beats setup — setup-screen is absent when a snapshot is present"
        status: pass
    human_judgment: false
  - id: D3
    description: "ResumeGate Discard clears ONLY the in-progress snapshot (never the pending-store queue, 170 D-05) and falls through to the setup screen, not an auto-started game"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#discard falls through to setup, clearing only the snapshot key (170 D-05)"
        status: pass
    human_judgment: false
  - id: D4
    description: "'New game' on both the result dialog (btn-new-game) and the result strip (strip-btn-new-game) returns to the setup screen — NOT an instant same-settings restart; game.newGame() is never called from either surface (D-11)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#new game returns to setup, not an instant restart (D-11)"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#new game from the result strip also returns to setup, without calling newGame"
        status: pass
    human_judgment: false
  - id: D5
    description: "A guest profile (no email / is_guest: true) reaches the same setup screen and can start a game (owner scope falls back to anon)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#guest reaches setup — no email, is_guest, Start still works"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 06: Bots Page Setup Screen + New-Game Convergence Summary

**Deleted the D-14 hardcoded `BOT_GAME_SETTINGS` stub and rewired `/bots` so `SetupScreen` is the single entry point for every new game — a fresh visit, a Discard, and both result-surface "New game" actions all converge on setup, while the resume gate's snapshot-beats-setup precedence stays untouched.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-14T14:06:06+02:00
- **Tasks:** 2 completed
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments

- `BOT_GAME_SETTINGS` deleted entirely from `Bots.tsx` (and a stale doc-comment reference in `SetupScreen.tsx` corrected) — `grep -rc 'BOT_GAME_SETTINGS' frontend/src/` returns 0 matches across the whole frontend.
- `BotsGame` now takes two new required/added props: `settings: BotGameSettings` (no fallback — a placeholder mount is a `tsc` error, not just a lint warning, structurally closing T-171-06-02) and `onNewGame: () => void`, threaded into both `GameResultDialog` and `GameResultStrip` (via `GamePanelProps`) in place of `game.newGame`.
- `BotsPage` gained an explicit `startedSettings: BotGameSettings | null` phase alongside the existing `boot`/`nonce` state. Render order: loading → `boot.resume !== null` (BotsGame + ResumeGate, unchanged D-04 precedence) → `startedSettings === null` (SetupScreen) → BotsGame with the started settings.
- `handleStart(settings)` sets `startedSettings` and bumps `nonce` for a fresh mount; `handleNewGame()` resets `startedSettings` to `null` and bumps `nonce`, unmounting `BotsGame` and returning to setup (D-11); `handleDiscard()` keeps `clearSnapshot(ownerKey)` and now also resets `startedSettings`, falling through to setup instead of auto-starting (D-13).
- The Phase 170 `useDrainPendingStore` mount effect and `useBotGame.ts` itself are both byte-for-byte untouched (`git diff --exit-code -- frontend/src/hooks/useBotGame.ts` exits 0).
- `Bots.test.tsx` — the page's first test file — mocks `@/hooks/useBotGame` wholesale with a controllable fake hook (its own internal `outcome`/`live` `useState`, so a test can flip `outcome` and observe `BotsGame` re-render without any real `WorkerPool`/Maia queue), plus `@/hooks/useUserProfile` and `@/hooks/useStoreBotGame`'s `useDrainPendingStore`. 7 RTL cases cover every behavior bullet from the plan, including the load-bearing D-11 negative assertion (`expect(fakeGame.newGame).not.toHaveBeenCalled()`) for BOTH result surfaces.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the BOT_GAME_SETTINGS stub branch with the setup screen (D-09, D-11, D-13)** - `4ccf0455` (feat)
2. **Task 2: Bots.test.tsx — pin the setup/resume/new-game convergence (V-11)** - `7ab92c74` (test)

_Note: no TDD RED/GREEN split was applied — Task 1's `<behavior>` spec was directly implementable against the already-shipped `SetupScreen`/`ResumeGate`/`useBotGame` contracts, and Task 2 wrote the full test suite green against the already-committed Task 1 code (both tasks match the plan's own `tdd="true"` framing loosely — the "RED" here is the pre-existing failing state of the old stub-wired page, proven by the new negative assertions passing only after Task 1's wiring)._

## Files Created/Modified

- `frontend/src/pages/Bots.tsx` - `BOT_GAME_SETTINGS` deleted; `BotsGameProps` gains `settings`/`onNewGame`; `GamePanelProps` gains `onNewGame`; `BotsPage` gains the `startedSettings` phase, `handleStart`/`handleNewGame`, and an updated `handleDiscard`
- `frontend/src/components/bots/SetupScreen.tsx` - One-line doc-comment fix (removed a literal `BOT_GAME_SETTINGS` reference left over from Plan 05) to satisfy this plan's whole-frontend grep gate
- `frontend/src/pages/__tests__/Bots.test.tsx` - NEW. 7 RTL tests: no-snapshot setup render, Start emits resolved settings, snapshot-beats-setup, discard preserves the pending-store key, New-game from both result surfaces (each with the D-11 negative assertion), guest reaches setup

## Decisions Made

- Fixed the stale `BOT_GAME_SETTINGS` doc-comment in `SetupScreen.tsx` (outside this plan's `files_modified` list) because the plan's own acceptance criteria explicitly greps the whole frontend, not just the two named files
- `handleDiscard()` explicitly resets `startedSettings` to `null` even though it is already structurally `null` whenever a snapshot exists (defensive, matches the plan's literal instruction)
- Kept `useBotGame`'s `newGame` export fully in place; documented at the hook's call site in `BotsGame` that it is unreached from the UI — `npm run knip` ran clean with no unused-export flag (it's an object property of the hook's return value, not a module-level export knip tracks)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/stale reference] Corrected a stale `BOT_GAME_SETTINGS` doc-comment in `SetupScreen.tsx`**
- **Found during:** Task 1 verification (the plan's own acceptance-criteria grep)
- **Issue:** `SetupScreen.tsx` (created in Plan 05, not in this plan's `files_modified`) had a doc comment literally naming `BOT_GAME_SETTINGS` as "the D-14 hardcoded stub" — this made `grep -rc 'BOT_GAME_SETTINGS' frontend/src/` return a nonzero count even after Task 1 fully deleted the real constant from `Bots.tsx`.
- **Fix:** Reworded the comment to "the D-14 hardcoded start-settings stub" — no behavior change, comment-only.
- **Files modified:** `frontend/src/components/bots/SetupScreen.tsx`
- **Verification:** `grep -rc 'BOT_GAME_SETTINGS' frontend/src/` returns 0 matches; `npx tsc -b`/`npm run lint`/`npm run knip` all still clean.
- **Committed in:** `4ccf0455` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — a stale comment reference that would have failed this plan's own explicit acceptance gate).
**Impact on plan:** No scope creep — a one-line comment correction in a file this plan's acceptance criteria already required to be grep-clean.

## Issues Encountered

None. `npx tsc -b`, `npm run lint`, `npm run knip`, and `npx vitest run src/pages/__tests__/Bots.test.tsx` all passed clean on the implementation as written; a broader `npx vitest run src/pages src/components/bots` (145 tests, 14 files) confirmed no regression in sibling Bots-page or bots-component tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`/bots` now has a single, real entry point for every new game — Plan 07 (store-on-finish + "Saved to your Library" affordance, same file) can build directly on `BotsGame`'s `settings`/`onNewGame` props and the `startedSettings` phase without any further rewiring of the setup/resume/new-game convergence. No blockers.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 4 created/modified files verified present on disk (`frontend/src/pages/Bots.tsx`, `frontend/src/pages/__tests__/Bots.test.tsx`, `frontend/src/components/bots/SetupScreen.tsx`, this SUMMARY.md); both task commits (`4ccf0455`, `7ab92c74`) verified present in git log.
