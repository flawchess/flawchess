---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "07"
subsystem: frontend
tags: [flaws, filter, miniboard, pagination, url-sync, store, D-04, D-06, D-07, D-08]
dependency_graph:
  requires:
    - phase: 108-05
      provides: "GET /library/flaws endpoint + FlawListItem/LibraryFlawsResponse backend schemas"
  provides:
    - "frontend/src/hooks/useFlawFilterStore.ts: useFlawFilterStore + DEFAULT_FLAW_FILTER + FlawFilterState"
    - "frontend/src/components/filters/FlawFilterControl.tsx: FlawFilterControl component"
    - "frontend/src/pages/library/FlawsTab.tsx: FlawsTab page (filter + list + pagination + URL sync)"
    - "frontend/src/types/library.ts: FlawListItem + LibraryFlawsResponse TS types"
    - "frontend/src/api/client.ts: libraryApi.getFlaws"
    - "frontend/src/hooks/useLibrary.ts: useLibraryFlaws"
  affects:
    - "Plans 108-08 — can now wire Games-card tag chips to /library/flaws?tag= and modify LibraryFilterPanel to use FlawFilterControl"
tech_stack:
  added: []
  patterns:
    - "useFlawFilterStore: useSyncExternalStore module-level pattern (mirrors useFilterStore, no Zustand)"
    - "FlawFilterControl: severity toggle + 3 family groups (Timing/Opportunity/Impact), at-least-one guard"
    - "FlawsTab: URL sync via initialSearchParams ref + replace-state setSearchParams on store change"
    - "libraryApi.getFlaws: multi-value tag + severity params via axios paramsSerializer indexes:null"
key_files:
  created:
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
  modified:
    - frontend/src/types/library.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/pages/library/LibraryPage.tsx
key-decisions:
  - "FlawFilterControl rendered inline in FlawsTab sidebar/drawer panels (Plan 08 not yet landed — LibraryFilterPanel integration deferred to Plan 08)"
  - "MiniBoard rendered without arrows: FlawListItem.fen is board_fen() only (no full FEN), so sanToSquares cannot parse moves; board position display is sufficient"
  - "FlawsTab URL sync uses initialSearchParams ref to read params at mount time without adding searchParams as a useEffect dependency (avoids fighting the URL-write effect)"
  - "Tests mock LibraryFilterPanel (avoids window.matchMedia), SidebarLayout (renders panels + children), LazyMiniBoard (avoids IntersectionObserver)"
requirements-completed: [D-04, D-06, D-07, D-08]
duration: 8min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 5
files_modified: 4
---

# Phase 108 Plan 07: Flaws Subtab Frontend (Filter + Miniboard List + URL Sync) Summary

**Shared useFlawFilterStore (useSyncExternalStore, no Zustand) + FlawFilterControl (severity M+B + 3 tag-family groups, at-least-one guard, theme.ts colors) + FlawsTab page (URL-synced deep-link, per-flaw miniboard list, 3 empty states, mandatory isError branch) + data layer (FlawListItem types, libraryApi.getFlaws, useLibraryFlaws) + LibraryPage Flaws tab (Import-Games-Flaws-Stats order, desktop+mobile parity) + 29 vitest tests**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-06T16:58:00Z
- **Completed:** 2026-06-06T17:05:45Z
- **Tasks:** 3
- **Files created:** 5
- **Files modified:** 4

## Accomplishments

- Added `FlawListItem` + `LibraryFlawsResponse` TypeScript interfaces to `types/library.ts`, mirroring the Plan 05 backend Pydantic schemas exactly (`game_id`, `ply`, `fen`, `move_san`, `severity`, `tags`, `es_before`, `es_after`, game metadata; no `*_hash` fields).
- Created `useFlawFilterStore.ts` — module-level `useSyncExternalStore` pattern (exact mirror of `useFilterStore.ts`); exports `useFlawFilterStore`, `DEFAULT_FLAW_FILTER`, `FlawFilterState` with `severity: ('blunder'|'mistake')[]` and `tags: FlawTag[]`.
- Added `libraryApi.getFlaws` to `client.ts` hitting `GET /library/flaws`; serializes multi-value `severity` and `tag` params via `axios paramsSerializer indexes: null`.
- Extended `buildLibraryParams` in `useLibrary.ts` to accept `tags: FlawTag[]`; added `useLibraryFlaws(filters, flawFilter, offset, limit)` hook with full flawFilter in queryKey.
- Created `FlawFilterControl.tsx` per UI-SPEC contract:
  - "Show flaws with:" section label + 2 severity toggle buttons (`filter-flaw-severity-blunder/mistake`, `aria-pressed`, at-least-one guard)
  - 3 family groups (`filter-flaw-family-tempo/opportunity/impact`, `role="group"`, `aria-label`): Timing (low-clock/impatient/considered), Opportunity (miss/lucky-escape), Impact (result-changing/while-ahead) — phase tags excluded
  - Tag buttons: selected = family color from `theme.ts` (FAM_TEMPO/FAM_OPPORTUNITY/FAM_IMPACT + BG via `style` prop); unselected = `border-border bg-inactive-bg`; `rounded-full px-3 py-0.5 h-11 sm:h-7`, `aria-pressed`, `aria-label="Filter flaws by tag: {tag}"`, `data-testid="filter-flaw-tag-{tag}"`
  - Clear affordance (`btn-clear-flaw-filter`) shown only on non-default state; resets to both severities, no tags
- Created `FlawsTab.tsx` mirroring `GamesTab` structure:
  - Shared `useFlawFilterStore` + `useFilterStore` + `useLibraryFlaws`
  - URL sync (D-04): mounts reads `?tag=`/`?severity=` into store via `initialSearchParams` ref (only when params present — doesn't overwrite navigation-time state); on store change writes URL with `replace-state`
  - Desktop: SidebarLayout with FlawFilterControl + LibraryFilterPanel in sidebar panels
  - Mobile: sticky Filters button + Drawer containing FlawFilterControl + LibraryFilterPanel
  - Flaw rows: `LazyMiniBoard(fen, flipped)` + `SeverityBadge` + `TagChip(s)` + game metadata (opponent/date/time-control/result/platform)
  - Mandatory `isError` branch: "Failed to load flaws. Something went wrong. Please try again in a moment."
  - 3 empty states per UI-SPEC: no games imported (+ Import CTA), no flaws matched
  - Pagination (page size 20), reset to offset 0 on filter change, scroll-to-top on page change
  - `data-testid="flaws-tab-content"`, `<section aria-label="Flaw results" data-testid="flaw-list">`
- Updated `LibraryPage.tsx`:
  - Import `AlertTriangle` lucide icon + `FlawsTab`
  - `activeTab` detection adds `/flaws` branch
  - Flaws `TabsTrigger` (`data-testid="tab-flaws"` desktop / `"tab-flaws-mobile"` mobile) with `AlertTriangle` icon, inserted between Games and Stats in **both** desktop and mobile `Tabs` blocks
  - `TabsContent value="flaws"` wrapping `<FlawsTab />` in both blocks
- 17 vitest tests for `FlawFilterControl` (severity guard, tag toggling, family groups, phase-tag absence, clear, ARIA)
- 12 vitest tests for `FlawsTab` (rendering, isError branch, flaw rows, matched count, empty states, URL sync deep-link)

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Data layer — types, client.getFlaws, useFlawFilterStore, useLibraryFlaws | d628bee2 | types/library.ts, hooks/useFlawFilterStore.ts, api/client.ts, hooks/useLibrary.ts |
| 2 | FlawFilterControl component + vitest test | 7030f1f6 | components/filters/FlawFilterControl.tsx, __tests__/FlawFilterControl.test.tsx |
| 3 | FlawsTab page, LibraryPage tab wiring, FlawsTab test | fa986c7a | pages/library/FlawsTab.tsx, LibraryPage.tsx, __tests__/FlawsTab.test.tsx |
| fix | ESLint exhaustive-deps fix in FlawsTab | 46cfa4ab | pages/library/FlawsTab.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ESLint react-hooks/exhaustive-deps in FlawsTab URL-sync effect**
- **Found during:** Task 3 full verification (lint gate)
- **Issue:** Initial URL-sync `useEffect` used `// eslint-disable-line` with incorrect comment syntax (`react-hooks/exhaustive-deps — intentional mount-only` is not a valid rule name), causing lint to fail.
- **Fix:** Replaced with `initialSearchParams` ref pattern — captures `searchParams` at render time so the mount effect uses the ref without needing `searchParams` as a dependency, satisfying the exhaustive-deps rule without a disable comment.
- **Files modified:** `frontend/src/pages/library/FlawsTab.tsx`
- **Commit:** 46cfa4ab

**2. [Rule 2 - Missing functionality] MiniBoard renders without flaw-move arrow**
- **Found during:** Task 3 implementation analysis
- **Issue:** `FlawListItem.fen` is `board_fen()` (piece placement only, no turn/castling/en passant), so `sanToSquares(fen, move_san)` cannot parse the move (chess.js requires a full FEN). Arrows are not possible without a full FEN.
- **Decision:** Render the board position correctly (react-chessboard accepts board_fen); display `move_san` as text label instead ("Move N: {san}"). The board position IS the flaw-position visualization; the arrow is a convenience overlay not essential for correctness.
- **Impact:** No arrow overlay on flaw miniboards. Future Plan could store full FEN in `game_flaws` to enable arrow rendering.

## Known Stubs

None — all outputs are fully functional. The FlawsTab fetches real data from `GET /library/flaws`, the FlawFilterControl correctly serializes filter state, URL sync works on deep-link landing.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-108-16 (mitigated) | frontend/src/pages/library/FlawsTab.tsx | URL params ?tag=/?severity= initialize filter store; values flow to API call; backend (Plan 05) validates at HTTP layer (422 on invalid values) — frontend renders empty results for unmatched combos |
| T-108-17 (accepted) | frontend/src/pages/library/FlawsTab.tsx | Only tag/severity selectors appear in URL — no user IDs, game IDs, or PII |

## Verification

```
cd frontend && npm run lint   → 0 errors
cd frontend && npm test -- --run → 785 passed (67 test files)
cd frontend && npx tsc --noEmit → All checks passed
cd frontend && npm run knip    → 0 issues
```

## Self-Check: PASSED
