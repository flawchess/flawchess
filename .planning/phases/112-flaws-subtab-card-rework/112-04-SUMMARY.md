---
phase: 112-flaws-subtab-card-rework
plan: "04"
subsystem: library/flaws
tags: [frontend, hook, modal, grid, tdd, dialog]
dependency_graph:
  requires:
    - "112-02 (GET /api/library/games/{game_id} backend endpoint)"
    - "112-03 (FlawCard component with View-game placeholder)"
  provides:
    - "libraryApi.getGame(gameId) in client.ts -> GET /library/games/{gameId}"
    - "useLibraryGame(gameId: number | null) hook — enabled when non-null"
    - "View-game Button + Dialog modal in FlawCard (flaw-game-modal testid)"
    - "FlawsTab: responsive grid (grid-cols-1 lg:grid-cols-2, flaw-grid testid)"
    - "FlawRow + MINI_BOARD_SIZE removed from FlawsTab"
    - "CHANGELOG [Unreleased] Phase 112 bullet"
  affects:
    - "frontend/src/api/client.ts"
    - "frontend/src/hooks/useLibrary.ts"
    - "frontend/src/components/library/FlawCard.tsx"
    - "frontend/src/pages/library/FlawsTab.tsx"
    - "frontend/src/components/library/__tests__/FlawCard.test.tsx"
    - "frontend/src/pages/library/__tests__/FlawsTab.test.tsx"
    - "frontend/src/hooks/__tests__/useLibraryGame.test.tsx"
    - "CHANGELOG.md"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN flow for API hook + modal tests"
    - "useQuery enabled: gameId !== null pattern for lazy modal fetch"
    - "Dialog sm:max-w-4xl overflow-y-auto max-h-[90vh] for full-game modal"
    - "isLoading/isError/data ternary branches (CLAUDE.md mandatory isError)"
    - "grid grid-cols-1 lg:grid-cols-2 gap-4 responsive layout"
key_files:
  created:
    - frontend/src/hooks/__tests__/useLibraryGame.test.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - CHANGELOG.md
decisions:
  - "useLibraryGame fetches only when modal opens (enabled: gameId !== null); closes reset selectedGameId to null"
  - "Dialog uses sm:max-w-4xl per UI-SPEC; sr-only DialogTitle satisfies Radix a11y requirement"
  - "FlawsTab tests updated: useLibraryGame added to useLibrary mock; TagLegend stub added; testid updated from flaw-card-link-* to flaw-card-platform-link-*"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-09"
  tasks_completed: 3
  files_changed: 8
---

# Phase 112 Plan 04: View-game modal + FlawCard grid Summary

Wired `libraryApi.getGame` + `useLibraryGame`, added the "View game" button and full-game Dialog modal to `FlawCard`, swapped `FlawsTab`'s `flex-col` list for a `grid grid-cols-1 lg:grid-cols-2 gap-4` grid, deleted `FlawRow` and `MINI_BOARD_SIZE`, and added the CHANGELOG entry. Closes SC-1 (grid), SC-7 (View-game modal), SC-8 (a11y/mobile).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for useLibraryGame hook | 49b1df29 | hooks/__tests__/useLibraryGame.test.tsx |
| 1 GREEN | libraryApi.getGame + useLibraryGame hook | 03794fbb | api/client.ts, hooks/useLibrary.ts |
| 2 RED | Failing tests for FlawCard View-game modal | 458195c2 | FlawCard.test.tsx |
| 2 GREEN | View-game Button + Dialog modal in FlawCard | 59eb3c35 | FlawCard.tsx, FlawCard.test.tsx |
| 3 | Replace FlawsTab list with FlawCard grid + CHANGELOG | 7e3bdd7a | FlawsTab.tsx, FlawsTab.test.tsx, CHANGELOG.md |

## Key Changes

### libraryApi.getGame (frontend/src/api/client.ts)
- Added `getGame: (gameId: number) => apiClient.get<GameFlawCard>('/library/games/${gameId}').then(r => r.data)` to the `libraryApi` object
- Added `GameFlawCard` to the import from `@/types/library`

### useLibraryGame (frontend/src/hooks/useLibrary.ts)
- Added `export function useLibraryGame(gameId: number | null)` with `queryKey: ['library-game', gameId]`, `enabled: gameId !== null`, `staleTime: LIBRARY_STALE_TIME`, `refetchOnWindowFocus: false`
- Fetch fires on first modal open per `gameId`; TanStack Query caches per query key

### FlawCard.tsx (frontend/src/components/library/FlawCard.tsx)
- Added `useState(false)` for `open` + `useLibraryGame(open ? flaw.game_id : null)` at the top
- Added "View game" `Button` (variant="default", size="sm", self-start) with `BookOpen` icon, `data-testid="flaw-card-view-game-{game_id}-{ply}"`, `aria-label="View full game for {whiteName} vs {blackName}"`
- Added `Dialog` with `open={open}`, `onOpenChange={(v) => !v && setOpen(false)}`
- `DialogContent` carries `className="sm:max-w-4xl overflow-y-auto max-h-[90vh]"`, `data-testid="flaw-game-modal"`, `aria-label="View full game"`
- `DialogTitle` with `className="sr-only"` satisfies Radix a11y screen-reader requirement
- Three modal states: `isLoading` spinner (Loader2 in p-8 wrapper), `isError` LoadError, `data` LibraryGameCard
- T-112-08: `isError` never falls through to empty/success (CLAUDE.md mandatory branch)

### FlawsTab.tsx (frontend/src/pages/library/FlawsTab.tsx)
- Replaced `<div className="flex flex-col gap-3">` + `FlawRow` map with `<div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="flaw-grid">` + `FlawCard` map
- Deleted `FlawRow` function (was ~95 LOC)
- Deleted `MINI_BOARD_SIZE = 80` constant
- Removed now-unused imports: `LazyMiniBoard`, `SeverityBadge`, `TagChip`, `sanToSquares`, `flawPlyUrl`, `supportsPlyDeepLink`, `ExternalLink`, `PlatformIcon`, `FlawListItem`, `SEV_BLUNDER`, `Tooltip`
- Added `FlawCard` import from `@/components/library/FlawCard`
- Existing loading/isError/empty-state scaffolding untouched

## TDD Gate Compliance

- RED commit (Task 1): `49b1df29` — `test(112-04): add failing tests for useLibraryGame hook (RED)`
- GREEN commit (Task 1): `03794fbb` — `feat(112-04): add libraryApi.getGame + useLibraryGame hook (GREEN)`
- RED commit (Task 2): `458195c2` — `test(112-04): add failing tests for FlawCard View-game modal (RED)`
- GREEN commit (Task 2): `59eb3c35` — `feat(112-04): add View-game button + Dialog modal to FlawCard (GREEN)`
- Task 3 (no TDD): `7e3bdd7a` — `feat(112-04): replace FlawsTab list with FlawCard grid; remove FlawRow; CHANGELOG`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] endgameApi got getGame before libraryApi**
- **Found during:** Task 1 GREEN implementation of libraryApi.getGame
- **Issue:** `replace_all: true` on `.then(r => r.data),\n};` matched the endgameApi closing line as well as the libraryApi closing line, inserting `getGame` into both.
- **Fix:** Removed the duplicate `getGame` from `endgameApi`; the final `getGame` lands correctly inside `libraryApi`.
- **Files modified:** `frontend/src/api/client.ts`
- **Commit:** 03794fbb

**2. [Rule 1 - Bug] FlawCard tests missing default useLibraryGame mock**
- **Found during:** Task 2 GREEN (FlawCard now calls useLibraryGame but existing tests didn't set it up)
- **Issue:** Pre-existing FlawCard tests (CardHeader, move notation, miniboard, testid) failed with `TypeError: Cannot destructure property 'data' of 'useLibraryGame(...)' as it is undefined` after the new hook call was added.
- **Fix:** Added `beforeEach` with a default mock return `{isLoading: false, isError: false, data: undefined}` in FlawCard.test.tsx; added `beforeEach` to the vitest import.
- **Files modified:** `FlawCard.test.tsx`
- **Commit:** 59eb3c35

**3. [Rule 1 - Bug] FlawsTab tests missing useLibraryGame + TagLegend mocks**
- **Found during:** Task 3 (FlawsTab now renders FlawCard which calls useLibraryGame and TagLegend)
- **Issue 1:** FlawsTab tests failed with `Cannot destructure 'data' of useLibraryGame(...)` because the useLibrary mock didn't include `useLibraryGame`.
- **Fix 1:** Added `useLibraryGame: () => ({ data: undefined, isLoading: false, isError: false })` to the mock.
- **Issue 2:** `No "TagLegend" export is defined on the "@/components/library/TagChip" mock` — the TagChip mock only exported `TagChip`.
- **Fix 2:** Added `TagLegend: () => null` to the TagChip mock.
- **Files modified:** `FlawsTab.test.tsx`
- **Commit:** 7e3bdd7a

**4. [Rule 1 - Bug] FlawsTab test used old FlawRow testid pattern**
- **Found during:** Task 3 test run
- **Issue:** Test looked for `data-testid="flaw-card-link-1-24"` (the old FlawRow pattern) but FlawCard uses `flaw-card-platform-link-{id}-{ply}`.
- **Fix:** Updated test to use `flaw-card-platform-link-1-24` and `flaw-card-platform-link-2-32`.
- **Files modified:** `FlawsTab.test.tsx`
- **Commit:** 7e3bdd7a

## Known Stubs

None. The View-game modal fetches live data via `useLibraryGame` → `GET /api/library/games/{game_id}`. The FlawCard grid renders real `FlawListItem` data. No placeholder content in production paths.

## Threat Flags

No new threat surfaces beyond the plan's threat register:
- T-112-01 (IDOR): client passes `flaw.game_id` from the user's own flaw list; server IDOR guard (plan 112-02) enforces ownership at `GET /library/games/{game_id}`.
- T-112-08 (fetch failure): `isError` → `LoadError` (no fall-through); captured by global `QueryCache.onError` (no duplicate Sentry call needed per CLAUDE.md).

## Self-Check: PASSED

- [x] `frontend/src/api/client.ts` contains `getGame` only inside `libraryApi` (grep confirms 1 occurrence at line ~293)
- [x] `frontend/src/hooks/useLibrary.ts` exports `useLibraryGame` with `enabled: gameId !== null`
- [x] `frontend/src/components/library/FlawCard.tsx` contains `flaw-game-modal` testid and `flaw-card-view-game-` button
- [x] `frontend/src/pages/library/FlawsTab.tsx` contains `flaw-grid` testid; `grep FlawRow MINI_BOARD_SIZE` returns nothing
- [x] `CHANGELOG.md` contains "Flaws" bullet under [Unreleased] Changed
- [x] 878/878 frontend tests pass; lint clean
- [x] Commits 49b1df29, 03794fbb, 458195c2, 59eb3c35, 7e3bdd7a present in git log
