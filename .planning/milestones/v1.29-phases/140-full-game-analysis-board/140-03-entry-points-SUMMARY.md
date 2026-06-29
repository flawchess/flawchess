---
phase: 140-full-game-analysis-board
plan: 03
subsystem: ui
tags: [react, typescript, chess, analysis-board, flaw-card, library-game-card]

# Dependency graph
requires:
  - 140-01 (buildGameAnalysisUrl in analysisUrl.ts)
  - 140-02 (Analysis.tsx game mode live, ready to receive game_id+ply links)
provides:
  - LibraryGameCard unified Search-icon Analyze button (analyzed games only, desktop + mobile)
  - FlawCard unified Analyze button; Game modal path deleted entirely
affects:
  - Users navigating from game cards or flaw cards to the full-game analysis board

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Button asChild + Link for SPA-navigable buttons (middle-click / cmd-click safe)
    - isAnalyzed gate for Analyze button visibility (D-06 analyzed-only rule)
    - buildGameAnalysisUrl(game_id, hoverPly ?? lastEvalPly ?? 0) URL pattern in game cards
    - buildGameAnalysisUrl(flaw.game_id, flaw.ply) URL pattern in flaw cards

key-files:
  modified:
    - frontend/src/components/results/LibraryGameCard.tsx (unified Analyze button, desktop + mobile)
    - frontend/src/components/library/FlawCard.tsx (unified Analyze button, Game modal deleted)
    - frontend/src/components/library/__tests__/FlawCard.test.tsx (tests updated for 140-03)

key-decisions:
  - "D-06/D-08: isAnalyzed gate on LibraryGameCard Analyze button (analyzed-only, Search icon not Activity)"
  - "D-09: FlawCard Game modal path deleted entirely (Dialog/Drawer/useLibraryGame/LibraryGameCard inline)"
  - "Mobile parity: both renderDesktopExploreButton AND md:hidden mobile row updated in LibraryGameCard"
  - "FlawCard buttonRow simplified to single Analyze button (no isTagged gate — always shown)"

patterns-established:
  - "Single Analyze button gated on isAnalyzed replaces Explore + Analyze-position pair"
  - "buildGameAnalysisUrl(game_id, hoverPly ?? lastEvalPly ?? 0) carries slider context to analysis page"

requirements-completed: [SC-1, SC-2, SC-5, D-4]

# Metrics
duration: 15min
completed: 2026-06-27
status: complete
---

# Phase 140 Plan 03: Entry Points Summary

**Collapsed the two card entry points into a single Analyze button each — LibraryGameCard replaces Explore + Analyze-position with one Search-icon Analyze button (analyzed games only, desktop + mobile); FlawCard replaces Explore + Game with one Analyze button and deletes the entire Game modal path.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-06-27
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

### Task 1: LibraryGameCard — Unified Analyze Button

- Removed `Activity` icon import; removed `FlawMarker` type import
- Added `buildGameAnalysisUrl` import from `@/lib/analysisUrl`
- Removed dead variables: `flawMarkerByPly`, `selectedFlaw`, `isTaggedFlaw`, `exploreOri`
- `renderDesktopExploreButton()`: replaced Explore + Analyze-position pair (90+ lines) with a single Analyze button gated on `isAnalyzed`, `variant="brand-outline"`, `data-testid="btn-library-game-analyze"`, `aria-label="Analyze game"`, Search icon, URL via `buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0)`
- Mobile `md:hidden` row: same single Analyze button replacing the 65-line Explore + Analyze-position block
- Existing LibraryGameCard tests (9 tests) all pass — none referenced the removed testids

### Task 2: FlawCard — Unified Analyze Button + Full Game Modal Deletion

- Removed imports: `useEffect`, `useState` (react); `Swords`, `Loader2`, `X` (lucide); `Dialog`, `DialogContent`, `DialogTitle`; `Drawer`, `DrawerContent`, `DrawerHeader`, `DrawerTitle`, `DrawerClose`; `LoadError`; `LibraryGameCard`; `useLibraryGame`; `useFlawFilterStore`
- Deleted local `MOBILE_BREAKPOINT_PX` constant and `useIsMobile()` helper (lines 59-78)
- Deleted component-body vars: `open` useState, `isMobile`, `isTagged`, `ori`, `flawFilter`, `useLibraryGame` call
- Deleted JSX: `gameBody`, `gameCloseLabel`, `gameView` variables + `{gameView}` return reference
- `buttonRow`: replaced Explore + Game pair with single Analyze button: `variant="brand-outline"`, `flex-1`, `data-testid="btn-flaw-analyze"`, `aria-label="Analyze game"`, Search icon, `buildGameAnalysisUrl(flaw.game_id, flaw.ply)`
- FlawCard.test.tsx: removed `useLibraryGame` mock, `GameFlawCard` type import, `MOCK_GAME`, `beforeEach` mock setup, `fireEvent`/`waitFor` imports, "View game" modal tests, "Explore + Game" button row tests; added 4 new Phase 140-03 Analyze button tests

## Task Commits

1. **Task 1: LibraryGameCard unified Analyze button (desktop + mobile)** - `5a291f58` (feat)
2. **Task 2: FlawCard unified Analyze button + Game modal deletion + phase gate** - `c99b2a6c` (feat)

## Files Modified

- `frontend/src/components/results/LibraryGameCard.tsx` — removed 155 lines, added 30 (net -125): Explore/Analyze-position pair gone, unified Analyze button in renderDesktopExploreButton and mobile row
- `frontend/src/components/library/FlawCard.tsx` — removed 334 lines, added 39 (net -295): Game modal path + Explore button deleted, unified Analyze button
- `frontend/src/components/library/__tests__/FlawCard.test.tsx` — removed 125 lines, added 39: old modal/explore tests replaced with 4 Analyze-button assertions

## Decisions Made

- **D-06/D-08 applied:** LibraryGameCard Analyze button gated on `isAnalyzed` (not always-enabled as UI-SPEC originally said); icon is Search (not Activity); no free-play fallback for un-analyzed games. NoAnalysisState.tsx left untouched (D-07).
- **D-09 fully applied:** FlawCard Game modal deleted. `useLibraryGame`, Dialog/Drawer, LibraryGameCard inline, `open` state, `useIsMobile` — all gone. `grep -c "useLibraryGame" FlawCard.tsx` returns 0.
- **Mobile parity:** Both desktop (`renderDesktopExploreButton`) and mobile (`md:hidden` row) updated in LibraryGameCard per CLAUDE.md mobile-parity rule.
- **FlawCard Analyze always shows:** unlike LibraryGameCard (isAnalyzed gate), FlawCard always shows the Analyze button — flaw cards only exist when a game has been analyzed (the flaw was detected by the analysis pipeline).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced.
T-140-03b (dead code from deleted Game modal): knip + tsc gate passed with zero issues — all deleted imports removed cleanly.
T-140-03a (URL tampering): `buildGameAnalysisUrl` inputs are numeric fields from typed props; Analysis.tsx (140-02) guards ply/game_id with NaN + bounds checks on receipt.

## Self-Check

- [x] `frontend/src/components/results/LibraryGameCard.tsx` contains `btn-library-game-analyze` (2 occurrences: desktop + mobile)
- [x] `frontend/src/components/library/FlawCard.tsx` contains `btn-flaw-analyze`
- [x] `grep -c "useLibraryGame" FlawCard.tsx` returns 0
- [x] `grep -c "Activity" LibraryGameCard.tsx` returns 0
- [x] `grep -c "game-card-btn-explore" LibraryGameCard.tsx` returns 0
- [x] `grep -c "game-card-btn-analyze-position" LibraryGameCard.tsx` returns 0
- [x] Commits exist: 5a291f58, c99b2a6c
- [x] `npx tsc -b` — zero errors
- [x] `npm run lint` — 0 errors (3 pre-existing coverage warnings)
- [x] `npm test -- --run` — 103 files, 1206 tests all pass
- [x] `npm run knip` — clean (no dead exports, no unused dependencies)

## Self-Check: PASSED
