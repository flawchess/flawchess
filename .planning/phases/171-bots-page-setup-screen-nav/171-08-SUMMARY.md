---
phase: 171-bots-page-setup-screen-nav
plan: 08
subsystem: ui
tags: [react, react-router, analysis-board, bot-play, url-contract]

# Dependency graph
requires:
  - phase: 165
    provides: "?fen= additive analysis deep-link precedence (game_id > fen > line) and the parseAnalysisFenParam degrade-not-throw guard this plan's parseAnalysisOrientationParam mirrors"
  - phase: 169
    provides: "Bots.tsx handleAnalyze CTA and Bots.test.tsx harness (useBotGame mock, setup-screen flow) this plan extends"
provides:
  - "Optional orientation arg on buildAnalysisLineUrl, emitted as &orientation=white|black"
  - "parseAnalysisOrientationParam strict lowercase allowlist guard"
  - "Single autoOrientation value/effect on Analysis.tsx driving board flip for both game mode and free play"
  - "Bots.tsx handleAnalyze wired to pass settings.userColor through to the URL"
affects: [analysis, bots]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "URL query param as the state-transport for free-play page orientation (no store/context needed), following the existing ?line=/?fen= precedent in analysisUrl.ts"
    - "Single derived autoOrientation value collapsing two per-mode sources into one effect, rather than two competing useEffects"

key-files:
  created: []
  modified:
    - frontend/src/lib/analysisUrl.ts
    - frontend/src/lib/analysisUrl.test.ts
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "buildAnalysisLineUrl's orientation arg is optional (2nd param) so the existing Openings.tsx:570 caller compiles unchanged with zero edits"
  - "No new exported type alias for the orientation union — inline 'white' | 'black' keeps knip's dead-export surface at zero"
  - "Square-order assertion pinned empirically (unflipped: a8 precedes a1 in DOM order per react-chessboard v5's own squareRenderer), not assumed — used the orientation-independent a1BeforeA8 relative-position check"
  - "Mutation-tested both wiring points by reverting them one at a time and confirming the specific tests (not the whole suite) go red, per the project's mutation-test-gap-closure convention"

patterns-established: []

requirements-completed: [PLAY-10]

coverage:
  - id: D1
    description: "buildAnalysisLineUrl accepts an optional orientation arg, emitted as &orientation=white|black (or the sole ?orientation= param on an empty move list); parseAnalysisOrientationParam is a strict lowercase allowlist that never throws"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/lib/analysisUrl.test.ts#buildAnalysisLineUrl / parseAnalysisOrientationParam"
        status: pass
    human_judgment: false
  - id: D2
    description: "Analysis.tsx collapses the isGameMode-only flip effect into one autoOrientation value/effect: game mode still sources from gameData.user_color, free play now sources from ?orientation=. hasAutoFlipped guard retained so a manual flip still wins. A ?line= URL with no orientation param stays white (no Openings regression); a malformed value degrades to white without throwing."
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Board auto-orientation (171 UAT gap 1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "THE JOINING LINE (B-1): Bots.tsx handleAnalyze passes settings.userColor into buildAnalysisLineUrl, so clicking the Analyze CTA on a finished bot game navigates to a URL carrying orientation=<played colour> and the move-list line param. Mutation-verified: deleting the 2nd arg turns the dedicated Bots.test.tsx tests red (confirmed then reverted, not committed)."
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Analyze CTA carries the played colour (171 UAT gap 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Analyze CTA remains a pure client-side deep-link with no dependency on the store POST having landed (D-20/D-21 unchanged) — GameResultDialog's V-17 pin ('Analyze this game' still fires onAnalyze when storeSucceeded is true — not re-pointed at the stored game) stays green untouched."
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 08: Bot-game analysis board auto-orientation Summary

**Free-play `/analysis` URLs gained an optional `?orientation=white|black` param, wired end-to-end from the bot Analyze CTA so a finished game played as Black opens the board flipped instead of white-side-up.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-14T16:52:12+02:00
- **Completed:** 2026-07-14T16:59:16+02:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `buildAnalysisLineUrl` takes an optional `orientation` 2nd arg, emitted explicitly (never elided) alongside or instead of `?line=`
- `parseAnalysisOrientationParam` is a strict lowercase allowlist that degrades any malformed/garbage/mixed-case value to `null` and never throws
- `Analysis.tsx`'s two competing per-mode orientation sources (game mode's `gameData.user_color`, free play's previously-nonexistent input) are collapsed into a single `autoOrientation` value driving the one existing flip effect — the `hasAutoFlipped` manual-flip guard is untouched
- `Bots.tsx`'s `handleAnalyze` now passes `settings.userColor` through, closing the actual gap (171 UAT gap 1, test 2)
- B-1 coverage added: `Bots.test.tsx` clicks the real `btn-analyze-game` CTA on a finished bot game and asserts the navigated URL — the one test in the whole plan set that can catch a future regression of the joining line itself

## Task Commits

Each task was committed atomically (TDD RED → GREEN per task):

1. **Task 1: Add orientation to the /analysis URL contract**
   - `0387f6f9` test(171-08): add failing tests for orientation URL param
   - `35d32764` feat(171-08): add orientation param to /analysis URL contract
2. **Task 2: Wire the bot game's colour through to a single Analysis auto-orientation effect**
   - `4982e460` test(171-08): add failing tests for bot-game analyze orientation flip
   - `7d76602c` feat(171-08): flip analysis board to the played colour for bot games

_Note: both tasks are TDD — test commit written and confirmed red before the implementation commit._

## Files Created/Modified
- `frontend/src/lib/analysisUrl.ts` — `ORIENTATION_PARAM`, optional 2nd arg on `buildAnalysisLineUrl`, `parseAnalysisOrientationParam`
- `frontend/src/lib/analysisUrl.test.ts` — 5 build cases + 8 parse cases for the new param
- `frontend/src/pages/Analysis.tsx` — `?orientation=` param read, single `autoOrientation` value/effect replacing the `isGameMode`-only flip effect
- `frontend/src/pages/Bots.tsx` — `handleAnalyze` passes `settings.userColor`
- `frontend/src/pages/__tests__/Analysis.test.tsx` — `describe('Board auto-orientation (171 UAT gap 1)')`, 5 tests
- `frontend/src/pages/__tests__/Bots.test.tsx` — mock harness extended (settable `fakeGame.moveHistory`, `useNavigate` spy) + `describe('Analyze CTA carries the played colour (171 UAT gap 1)')`, 2 tests (B-1)

## Decisions Made
- Optional 2nd param (not a new function) keeps `Openings.tsx:570`'s existing 1-arg call compiling unchanged
- No new exported orientation type alias — inline `'white' | 'black'` keeps knip's dead-export surface at zero, and `settings.userColor` (`MoverColor`) passes with no cast
- Square-order assertion for the flip tests was pinned empirically (a throwaway dump confirmed react-chessboard v5 renders `square-a8` before `square-a1` in the unflipped/white-oriented default), not assumed — the final assertion uses the orientation-independent `compareDocumentPosition` relative check

## Deviations from Plan

None — plan executed exactly as written, including both required mutation checks (Bots.tsx 2nd-arg deletion, Analysis.tsx `autoOrientation` reversion), each confirmed red then restored before committing.

## Issues Encountered

Vitest's default console interception swallowed `console.log` output during the empirical square-order probe; switched to writing the dump to a scratch JSON file via `node:fs`, read it back, then deleted the temporary probe test before writing the final assertions.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Gap 1 of the 171 UAT (major, test 2) is closed. Two more gap-closure plans (171-09, 171-10) remain from the UAT diagnosis session per `.planning/phases/171-bots-page-setup-screen-nav/171-UAT.md`.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 7 claimed files found on disk. All 5 claimed commit hashes found in git log.
