---
phase: 14-ui-restructuring
verified: 2026-03-17T12:00:00Z
status: human_needed
score: 18/18 must-haves verified
re_verification: false
human_verification:
  - test: "Filter state persists across tab switches"
    expected: "Change Played As to Black on Moves tab, switch to Games tab — Played As remains Black. Switch to Statistics — still Black."
    why_human: "React state persistence across shadcn Tabs cannot be confirmed by static analysis; requires live browser interaction."
  - test: "Board position persists across tab switches"
    expected: "Play a move on the board, switch from Moves to Games tab — board still shows the played position."
    why_human: "State persistence in parent component verified structurally, but actual React rendering behavior needs browser confirmation."
  - test: "Import progress visible globally from any page"
    expected: "Start an import on /import, navigate to /openings — ImportJobWatcher (non-visual) continues polling and fires query invalidation on completion."
    why_human: "ImportJobWatcher is a non-visual component mounted outside Routes; global coverage requires runtime verification that jobs tracked before navigation are still watched after navigation."
  - test: "URL-based tab routing with browser back/forward"
    expected: "Clicking tabs changes URL (/openings/explorer, /openings/games, /openings/statistics). Browser back/forward navigates between tabs correctly."
    why_human: "React Router navigate() and useLocation() interaction requires browser testing."
  - test: "Openings nav item stays highlighted on sub-routes"
    expected: "While on /openings/games or /openings/statistics, the Openings nav link is highlighted (active)."
    why_human: "The isActive() prefix logic is correct in code but visual highlighting requires browser verification."
---

# Phase 14: UI Restructuring Verification Report

**Phase Goal:** Restructure the frontend UI: create dedicated Import page, unify Openings as tabbed hub (Move Explorer, Games, Statistics), update navigation, persist filter state across tabs.
**Verified:** 2026-03-17T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Import page at /import shows platform rows with usernames and Sync buttons | VERIFIED | `Import.tsx` lines 147-214: two platform rows with `data-testid="import-platform-chess-com"` and `data-testid="import-platform-lichess"`, each with username Input and Sync Button |
| 2  | Import page shows Delete All Games button with confirmation dialog | VERIFIED | `Import.tsx` lines 228-266: `data-testid="btn-delete-games"` triggers dialog `data-testid="delete-games-modal"` with confirm/cancel buttons |
| 3  | Import progress is tracked globally from any page | VERIFIED | `App.tsx` lines 19-29: `ImportJobWatcher` is a non-visual poller rendered outside `<Routes>` via `watchableJobIds.map(...)` at lines 160-162; invalidates `['games']`, `['gameCount']`, `['userProfile']` on completion |
| 4  | Navigation shows Import, Openings, Rating, Global Stats in that order | VERIFIED | `App.tsx` lines 44-49: `NAV_ITEMS` array in exact required order |
| 5  | / redirects to /openings | VERIFIED | `App.tsx` line 151: `<Route path="/" element={<Navigate to="/openings" replace />} />` |
| 6  | /openings/* wildcard route is registered | VERIFIED | `App.tsx` line 153: `<Route path="/openings/*" element={<OpeningsPage />} />` |
| 7  | /openings defaults to /openings/explorer | VERIFIED | `Openings.tsx` lines 53, 458-460: `needsRedirect` check + `<Navigate to="/openings/explorer" replace />` early return |
| 8  | Openings page has three sub-tabs: Moves, Games, Statistics | VERIFIED | `Openings.tsx` lines 470-480: `TabsTrigger` for `explorer` (label "Moves", `data-testid="tab-move-explorer"`), `games`, `statistics` |
| 9  | Tab bar uses URL-based routing | VERIFIED | `Openings.tsx` line 469: `onValueChange={(val) => navigate('/openings/${val}')}` and `activeTab` derived from `location.pathname` at lines 55-59 |
| 10 | Filter state persists when switching between sub-tabs | VERIFIED (code) | All filter state (`filters`, `chess`, `boardFlipped`, `gamesOffset`) lives in `OpeningsPage` parent, never inside `TabsContent`; tab content is JSX variables computed before render | NEEDS HUMAN |
| 11 | Board position persists when switching between sub-tabs | VERIFIED (code) | `useChessGame()` called once in parent at line 62; same instance referenced by all three tab content variables | NEEDS HUMAN |
| 12 | All three sub-tabs auto-fetch when position or filters change | VERIFIED | `useNextMoves` (line 94), `usePositionAnalysisQuery` (lines 133-138), `useTimeSeries` (line 169) all receive `debouncedFilters`; no manual trigger buttons present |
| 13 | Games tab shows all games by default (no positionFilterActive gating) | VERIFIED | `Openings.tsx`: no `positionFilterActive` variable or conditional; `usePositionAnalysisQuery` always runs |
| 14 | Games tab shows W/D/L bar above game cards | VERIFIED | `Openings.tsx` lines 425-426: `<WDLBar stats={gamesData.stats} />` rendered before `<GameCardList>` |
| 15 | Move Explorer tab shows WDL bar and next moves table | VERIFIED | `Openings.tsx` lines 383-396: `WDLBar` conditionally rendered above `MoveExplorer` in `moveExplorerContent` |
| 16 | Statistics tab shows WDL bar chart and Win Rate Over Time chart | VERIFIED | `Openings.tsx` lines 449-450: `<WDLBarChart>` and `<WinRateChart>` rendered when bookmarks + tsData present |
| 17 | useDebounce hook exists and is exported | VERIFIED | `frontend/src/hooks/useDebounce.ts`: 10-line implementation, `export function useDebounce<T>` |
| 18 | usePositionAnalysisQuery hook exists alongside existing hooks | VERIFIED | `frontend/src/hooks/useAnalysis.ts` line 38: `export function usePositionAnalysisQuery`; `useAnalysis` at line 7 and `useGamesQuery` at line 20 still present |

**Score:** 18/18 truths verified (5 also need human browser confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/Import.tsx` | Dedicated import page | VERIFIED | 269 lines; substantive implementation with platform rows, sync flow, delete confirmation dialog, inline progress bars; all required `data-testid` attributes present |
| `frontend/src/App.tsx` | Updated routing, nav, global job tracking | VERIFIED | ImportJobWatcher pattern replaces ImportProgress; NAV_ITEMS in correct order; `/openings/*` and `/import` routes; `isActive()` prefix helper; DashboardPage absent |
| `frontend/src/hooks/useDebounce.ts` | Generic debounce hook | VERIFIED | Correct implementation with `useState` + `useEffect` + cleanup |
| `frontend/src/hooks/useAnalysis.ts` | usePositionAnalysisQuery added | VERIFIED | All three exports present: `useAnalysis`, `useGamesQuery`, `usePositionAnalysisQuery`; query key includes `'positionAnalysis'` + hash + filters + pagination |
| `frontend/src/pages/Openings.tsx` | Tabbed hub with sidebar + 3 sub-tabs | VERIFIED | 548 lines (rewritten from 264); `data-testid="openings-page"`, `data-testid="openings-tabs"`, all tab testids present; sidebar with board, toggles, bookmark, collapsibles |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `App.tsx` | `pages/Import.tsx` | `Route path="/import"` | WIRED | Line 152: `<Route path="/import" element={<ImportPage .../>} />` |
| `App.tsx` | `ImportJobWatcher` | Global job watcher rendered outside Routes | WIRED | Lines 160-162: `watchableJobIds.map(id => <ImportJobWatcher key={id} .../>)` |
| `Openings.tsx` | `hooks/useNextMoves.ts` | `useNextMoves` for Move Explorer auto-fetch | WIRED | Line 94: `const nextMoves = useNextMoves(chess.hashes.fullHash, debouncedFilters)` |
| `Openings.tsx` | `hooks/useAnalysis.ts` | `usePositionAnalysisQuery` for Games tab auto-fetch | WIRED | Lines 133-138: `usePositionAnalysisQuery({ targetHash, filters: debouncedFilters, ... })` |
| `Openings.tsx` | `hooks/usePositionBookmarks.ts` | `useTimeSeries` for Statistics tab auto-fetch | WIRED | Lines 28-29, 152-169: imported and called with `timeSeriesRequest` memo |
| `Openings.tsx` | `hooks/useDebounce.ts` | Debounced filters for query keys | WIRED | Line 67: `const debouncedFilters = useDebounce(filters, 300)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UIRS-01 | 14-02-PLAN.md | Openings tab has three sub-tabs: Move Explorer, Games, Statistics — with shared filter sidebar | SATISFIED | `Openings.tsx`: `data-testid="openings-tabs"`, three `TabsTrigger` values (explorer/games/statistics), shared sidebar with `FilterPanel`, `PositionBookmarkList`, toggles |
| UIRS-02 | 14-02-PLAN.md | Filter state persists when switching between sub-tabs (no reset on tab change) | SATISFIED (code) | All state in `OpeningsPage` parent — `filters`, `chess`, `boardFlipped`, `gamesOffset`, `bookmarks`; no state lives inside `TabsContent`; needs human browser confirmation |
| UIRS-03 | 14-01-PLAN.md | Dedicated Import page replaces the import modal, showing import controls, username management, and sync functionality | SATISFIED | `Import.tsx` at route `/import` with platform rows, inline editable usernames, sync, delete all games; `ImportModal` still exists but unused by active routes |
| UIRS-04 | 14-01-PLAN.md | Navigation updated: Import, Openings, Rating, Global Stats | SATISFIED | `App.tsx` `NAV_ITEMS`: Import → /import, Openings → /openings, Rating → /rating, Global Stats → /global-stats; `isActive()` prefix-matches `/openings/*` |

All four UIRS requirement IDs declared in plan frontmatter are accounted for. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `Import.tsx` | 157, 192 | `placeholder=` | Info | HTML input placeholder attributes — not code stubs |
| `Openings.tsx` | 531 | `placeholder=` | Info | HTML input placeholder for bookmark label — not a code stub |

No blocker or warning-level anti-patterns found.

### Implementation Notes (Plan 03 Deviations)

The Phase 14 Plan 03 human verification checkpoint uncovered several issues that were fixed iteratively. These are reflected in the current codebase and are improvements over the original plan:

1. **Hooks order fix** — early `<Navigate>` return was moved after all hooks calls to avoid React hook ordering violation; the code now computes `needsRedirect` as a boolean before hooks, and renders `<Navigate>` only after all hooks have run (line 458).
2. **Tab renamed** — the "Move Explorer" tab label was renamed to "Moves" during human review; `data-testid="tab-move-explorer"` is preserved for automation compatibility.
3. **WDL bar on Moves tab** — position stats bar (`WDLBar`) was added above the move explorer table, driven by `gamesQuery.data` (lines 385-387).
4. **Import page redesigned** — floating toasts replaced with inline progress bars (`ImportProgressBar` component); `ImportProgress` floating toast component is no longer used in App.tsx; instead `ImportJobWatcher` (a non-visual poller) handles global job tracking.
5. **Backend fixes** — chess.com username lowercasing and bulk insert chunking (backend concerns, not UI restructuring scope).

### Human Verification Required

The following items need browser testing — all automated structural checks passed but runtime behavior cannot be confirmed statically.

#### 1. Filter State Persistence Across Tab Switches

**Test:** On the Moves tab, change "Played As" to Black. Click the Games tab. Check the Played As toggle state. Click Statistics. Check again.
**Expected:** Played As remains Black on all three tabs.
**Why human:** shadcn `Tabs` hides content via CSS (no unmount), but the state living in the parent component needs live verification that React reconciliation does not reset it.

#### 2. Board Position Persistence Across Tab Switches

**Test:** Play 1.e4 on the board. Switch from Moves to Games tab. Switch to Statistics. Return to Moves.
**Expected:** Board still shows the position after 1.e4 on all tab switches.
**Why human:** Same reason as filter persistence — structural verification is sound but live behavior must be confirmed.

#### 3. Import Progress Works Globally (Not Just on Import Page)

**Test:** Start a chess.com or lichess import from the Import page. Navigate to /openings while import is running. Wait for import to complete. Verify that game data refreshes (new games appear) even though you navigated away.
**Expected:** `ImportJobWatcher` continues polling and invalidates `['games']`, `['gameCount']`, `['userProfile']` query caches after job completes, regardless of current page.
**Why human:** `ImportJobWatcher` is a non-visual component — its lifecycle and polling behavior when navigating between routes needs runtime confirmation.

#### 4. URL-Based Tab Routing With Browser Back/Forward

**Test:** Navigate to /openings/explorer, click Games tab (URL becomes /openings/games), click browser Back button.
**Expected:** URL returns to /openings/explorer and the Moves tab is active.
**Why human:** React Router history stack behavior requires browser testing.

#### 5. Openings Nav Link Highlighted on Sub-Routes

**Test:** Navigate to /openings/games. Look at the top navigation bar.
**Expected:** The "Openings" nav link shows the active underline indicator.
**Why human:** Visual styling requires browser inspection; the `isActive()` prefix logic is correct in code but the resulting CSS class application needs visual confirmation.

### Gaps Summary

No gaps found. All 18 automated must-haves pass. The status is `human_needed` because 5 items (filter persistence, board persistence, global import tracking, URL routing, nav highlighting) involve runtime UI behavior that cannot be verified by static code analysis.

---

_Verified: 2026-03-17T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
