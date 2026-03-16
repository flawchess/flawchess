# Phase 14: UI Restructuring - Research

**Researched:** 2026-03-17
**Domain:** React Router v6 nested routes, shadcn Tabs, TanStack Query auto-fetch, React state lifting
**Confidence:** HIGH

## Summary

This phase is a pure frontend restructuring with no backend changes. The work decomposes the existing `Dashboard.tsx` (650 lines, does everything) into a tabbed `OpeningsPage` at `/openings/*` (three sub-tabs: Move Explorer, Games, Statistics) and a new `ImportPage` at `/import`. The current `Openings.tsx` (Statistics-only page) is replaced by the Statistics sub-tab. The Dashboard page is deleted entirely.

All the reusable leaf components (`MoveExplorer`, `FilterPanel`, `WDLBar`, `GameCardList`, `WDLBarChart`, `WinRateChart`, `ChessBoard`, `MoveList`, `BoardControls`, `PositionBookmarkList`) work unchanged. The primary engineering work is: (1) lifting unified filter state to the new `OpeningsPage` parent, (2) wiring URL-based tab routing with React Router `useNavigate`/`useLocation`, (3) converting the Games tab from mutation-driven (Filter button) to auto-fetch `useQuery`, (4) converting the Statistics tab from mutation-driven (Analyze button) to auto-fetch `useQuery`, and (5) extracting the import form from its `Dialog` wrapper into a full-page layout.

**Primary recommendation:** Use the shadcn `Tabs` component (already installed) driven by React Router, with unified `FilterState` lifted to `OpeningsPage`, and `useQuery` for all three sub-tabs. Lift `ImportProgress` + job state to `App.tsx` for global toast coverage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Openings page sidebar:**
- Board, played-as toggle, piece filter, and bookmark button are always visible — NOT inside a collapsible. Remove the "Position filter" collapsible wrapper, show content directly.
- Position bookmarks section stays as a collapsible
- More filters section stays as a collapsible
- Unified filter state: merge Dashboard's `FilterState` and Openings' `StatsFilters` into one shared state lifted to OpeningsPage parent

**Sub-tab structure:**
- Three sub-tabs: Move Explorer, Games, Statistics
- Tab bar positioned at the top of the right column (content area)
- URL-based routing: `/openings/explorer`, `/openings/games`, `/openings/statistics`
- `/openings` defaults to `/openings/explorer`
- Tabs are bookmarkable and work with browser back/forward

**Auto-fetch behavior:**
- ALL sub-tabs auto-fetch when position or filters change — no Filter/Analyze button anywhere
- Move Explorer: auto-fetches next moves on position/filter change (existing behavior)
- Games: auto-fetches game list on position/filter change (replaces manual Filter button)
- Statistics: auto-fetches bookmark time series on bookmark/filter change (replaces Analyze button)
- Remove the Filter button and Analyze button entirely

**Games tab:**
- Shows all games by default when no position filter is active (no positionFilterActive gating)
- W/D/L bar appears above game cards (same as current Dashboard behavior)
- Pagination resets to page 1 on tab switch (offset not preserved across tabs)
- GameCardList with existing game cards, pagination, matched count

**Statistics tab:**
- WDL bar chart and Win Rate Over Time chart (current Openings page content)
- Auto-fetches when bookmarks or filters change
- No separate Analyze button

**Import page:**
- Dedicated page at `/import` replacing the import modal
- Same controls as ImportModal but laid out as a full page (expanded, not in a dialog)
- Username management, platform select, import trigger — all inline
- Delete All Games button moves here (from Dashboard header)
- Import progress shown inline on the page (not just toasts)
- Toast notification fires globally when import completes and user is on another page
- Cache invalidation on import complete: `['games']`, `['gameCount']`, `['userProfile']`

**Navigation:**
- Nav order: Import | Openings | Rating | Global Stats
- Routes: `/import`, `/openings/*`, `/rating`, `/global-stats`
- `/` redirects to `/openings`
- DashboardPage.tsx deleted entirely (no redirect component)
- All existing routes resolve correctly with no broken links

### Claude's Discretion
- Exact tab component implementation (shadcn Tabs, custom, or react-router-based)
- Debounce strategy for auto-fetch on rapid filter/position changes
- Mobile responsive layout for the tabbed Openings page
- Import page layout details (spacing, grouping of controls)
- Loading/skeleton states for each sub-tab during auto-fetch
- How to handle the transition from ImportModal to ImportPage (component refactoring approach)

### Deferred Ideas (OUT OF SCOPE)
- GamesTab pagination offset survival across tab switches — decided to reset to page 1 (simpler)
- MEXP-08: Move sorting options (by win rate, alphabetical) — future requirement
- MEXP-09: Show resulting position FEN/thumbnail on move hover — future requirement
- Phase 15: Consolidation — code cleanup, endpoint renaming, CLAUDE.md/README updates
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UIRS-01 | Openings tab has three sub-tabs: Move Explorer, Games, Statistics — with shared filter sidebar (board, position bookmarks, more filters) | shadcn Tabs (already installed), React Router nested routes, unified FilterState lifted to OpeningsPage parent |
| UIRS-02 | Filter state persists when switching between sub-tabs (no reset on tab change) | State lifting pattern: FilterState and chess position in OpeningsPage parent, never inside sub-tab components |
| UIRS-03 | Dedicated Import page replaces the import modal, showing import controls, username management, and sync functionality | Extract ImportModal form content from Dialog wrapper into ImportPage; lift ImportProgress to App.tsx |
| UIRS-04 | Navigation updated: Import, Openings, Rating, Global Stats | Update NAV_ITEMS in App.tsx; update routes; `/` redirects to `/openings`; delete DashboardPage |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-router-dom | Already installed (v6) | Nested routes for `/openings/*`, URL-based tab state | Project standard; `useNavigate` + `useLocation` for tab routing |
| @tanstack/react-query | Already installed | Auto-fetch queries for all three sub-tabs | Project standard; replaces mutations with `useQuery` |
| shadcn Tabs | Already installed | Sub-tab component | Pre-installed per UI-SPEC; Radix `TabsList`/`TabsTrigger`/`TabsContent` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | Already installed | Global toast notifications when import completes | Lift ImportProgress to App level for cross-page toasts |
| lucide-react | Already installed | Icons in sidebar and Import page | Replace Download/Trash2 icons that currently live in Dashboard header |

No new packages need to be installed. All required libraries are already in the project.

**Installation:** None required.

## Architecture Patterns

### Recommended Project Structure

```
src/
├── pages/
│   ├── Dashboard.tsx        # DELETE (decomposed into below)
│   ├── Openings.tsx         # REPLACE with new tabbed OpeningsPage
│   ├── Import.tsx           # NEW — dedicated import page
│   ├── Rating.tsx           # unchanged
│   └── GlobalStats.tsx      # unchanged
├── hooks/
│   └── useAnalysis.ts       # EXTEND: add usePositionAnalysisQuery for auto-fetch Games tab
└── App.tsx                  # UPDATE: routes, nav, lift ImportProgress state
```

### Pattern 1: URL-Based Tab Routing with shadcn Tabs

**What:** shadcn `Tabs` `value` prop controlled by the URL path segment. Tab clicks call `navigate()`. Browser back/forward naturally navigate between tabs.

**When to use:** Tab state that must survive page reload and be bookmarkable.

**How it works:**
- `OpeningsPage` renders at `/openings/*` via a nested route
- Inner `Routes` (or `Navigate`) handle `/openings` → `/openings/explorer` redirect
- `useLocation().pathname` extracts the active tab segment
- `TabsTrigger` `onClick` calls `navigate('/openings/explorer')` etc.

**Example:**
```typescript
// In OpeningsPage
import { useNavigate, useLocation, Routes, Route, Navigate } from 'react-router-dom';

const location = useLocation();
const navigate = useNavigate();

// Derive active tab from URL
const activeTab = location.pathname.includes('/games')
  ? 'games'
  : location.pathname.includes('/statistics')
    ? 'statistics'
    : 'explorer';

// Tab trigger connects to router
<Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)}>
  <TabsList data-testid="openings-tabs">
    <TabsTrigger value="explorer" data-testid="tab-move-explorer">Move Explorer</TabsTrigger>
    <TabsTrigger value="games" data-testid="tab-games">Games</TabsTrigger>
    <TabsTrigger value="statistics" data-testid="tab-statistics">Statistics</TabsTrigger>
  </TabsList>
  <TabsContent value="explorer">...</TabsContent>
  <TabsContent value="games">...</TabsContent>
  <TabsContent value="statistics">...</TabsContent>
</Tabs>
```

**App.tsx route setup:**
```typescript
<Route path="/openings/*" element={<OpeningsPage />} />
// Inside OpeningsPage, handle sub-routes:
// /openings → redirect to /openings/explorer
// /openings/explorer, /openings/games, /openings/statistics → tab content
```

**Active nav detection for `/openings/*`:** Use `location.pathname.startsWith('/openings')` instead of exact equality in `NavHeader`.

### Pattern 2: Unified FilterState — Merge Two Filter Types

**What:** The current codebase has two separate filter type systems. `FilterState` (Dashboard) has `matchSide` and `color` on top of the common fields. `StatsFilters` (Openings) has the same common fields without `matchSide`/`color`. After merging, one `FilterState` covers all three sub-tabs.

**Existing `FilterState` in `FilterPanel.tsx` already includes all needed fields:**
```typescript
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  recency: Recency | null;
  color: Color;
}
```

**Action:** `OpeningsPage` uses `FilterState` directly (not `StatsFilters`). The Statistics sub-tab constructs its `TimeSeriesRequest` from this unified state — replacing the `StatsFilters` approach in `Openings.tsx`. The old `StatsFilters` interface is deleted.

### Pattern 3: Auto-Fetch Games Tab via useQuery (Replaces Mutation)

**What:** The current Games view in Dashboard uses `useAnalysis` (a `useMutation`) triggered by a Filter button. The new Games tab must auto-fetch on position/filter changes using `useQuery`.

**Current `useGamesQuery` in `useAnalysis.ts`** fetches unfiltered games (no hash). It needs to be extended or replaced with a query that accepts the full filter set including position hash.

**New hook pattern:**
```typescript
// useAnalysis.ts — extend with auto-fetch position query
export function usePositionAnalysisQuery(params: {
  targetHash: string;
  filters: FilterState;
  offset: number;
  limit: number;
}) {
  return useQuery<AnalysisResponse>({
    queryKey: ['games', params.targetHash, params.filters, params.offset, params.limit],
    queryFn: async () => {
      const response = await apiClient.post<AnalysisResponse>('/analysis/positions', {
        target_hash: params.targetHash,
        match_side: resolveMatchSide(params.filters.matchSide, params.filters.color),
        time_control: params.filters.timeControls,
        platform: params.filters.platforms,
        rated: params.filters.rated,
        opponent_type: params.filters.opponentType,
        recency: params.filters.recency,
        color: params.filters.color,
        offset: params.offset,
        limit: params.limit,
      });
      return response.data;
    },
  });
}
```

**Key insight:** At starting position (no moves played), `targetHash` is the full hash of the initial board. The backend returns all games since no position filter is restrictive at the root. This removes the `positionFilterActive` gating concept entirely — the Games tab always shows results.

**Debounce:** 300ms debounce on filter state changes prevents query spam from rapid toggle clicks. Use a debounced version of the filter state for query keys only (not for the UI which reflects changes immediately).

### Pattern 4: Auto-Fetch Statistics Tab via useQuery

**What:** The current `Openings.tsx` uses `useTimeSeries` with a manually-triggered `activeRequest` state (set by "Analyze" button). The new Statistics tab must auto-fetch when bookmarks or filters change.

**Pattern:** Drive `useTimeSeries` directly from current bookmarks + filters, no intermediate `activeRequest` state:
```typescript
// In StatisticsTab (or OpeningsPage parent)
const { data: bookmarks = [] } = usePositionBookmarks();
// Build request inline:
const timeSeriesRequest: TimeSeriesRequest | null = bookmarks.length > 0 ? {
  bookmarks: bookmarks.map((b) => ({
    bookmark_id: b.id,
    target_hash: b.target_hash,
    match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
    color: b.color,
  })),
  time_control: filters.timeControls,
  platform: filters.platforms,
  rated: filters.rated,
  opponent_type: filters.opponentType,
  recency: filters.recency === 'all' ? null : filters.recency,
} : null;
const { data: tsData, isFetching } = useTimeSeries(timeSeriesRequest);
```

`useTimeSeries` already uses `useQuery` with `enabled: !!req && req.bookmarks.length > 0` — the auto-fetch behavior comes for free by removing the manual trigger.

### Pattern 5: Lifting ImportProgress to App Level

**What:** When user navigates away from `/import` while a job runs, the toast must still fire. This requires `activeJobIds` state and `ImportProgress` to live above the page router.

**Current pattern in Dashboard:** `activeJobIds` + `handleJobDone` local to `DashboardPage`.

**New pattern — lift to App.tsx:**
```typescript
// App.tsx
function AppRoutes() {
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const handleImportStarted = useCallback((jobId: string) => {
    setActiveJobIds((ids) => [...ids, jobId]);
  }, []);

  const handleJobDone = useCallback((jobId: string) => {
    setActiveJobIds((ids) => ids.filter((id) => id !== jobId));
    queryClient.invalidateQueries({ queryKey: ['games'] });
    queryClient.invalidateQueries({ queryKey: ['gameCount'] });
    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
  }, [queryClient]);

  return (
    <>
      <Routes>
        ...
        <Route path="/import" element={<ImportPage onImportStarted={handleImportStarted} />} />
        ...
      </Routes>
      {/* Global — fires toasts from any page */}
      <ImportProgress jobIds={activeJobIds} onJobDone={handleJobDone} />
    </>
  );
}
```

**ImportPage** receives `onImportStarted` as a prop (same pattern as `ImportModal` currently receives).

**Inline progress on ImportPage:** `ImportProgress` rendered at App level handles the global toasts. On ImportPage itself, a separate inline view of running jobs can be shown by passing the same `activeJobIds` down as a prop, or the ImportPage can show job state via a local display (simpler: just link to the same activeJobIds via prop drilling or context).

**Simpler alternative:** Pass `activeJobIds` as a prop to `ImportPage` so it can render its own inline view, while App also renders the global `ImportProgress`. This is the lowest-complexity approach.

### Pattern 6: Delete All Games Moves to ImportPage

**What:** The delete functionality currently lives in `DashboardPage` (button in header + confirmation dialog). It moves to `ImportPage` in a "Data Management" section.

**Action needed:** Move `handleDeleteAllGames` logic, `deleteDialogOpen` state, and the confirmation dialog from `Dashboard.tsx` to `Import.tsx`. The `ImportPage` calls `queryClient.invalidateQueries` for `['games']` and `['gameCount']` after deletion — already established pattern.

### Anti-Patterns to Avoid

- **Storing tab state in React state:** Tab identity belongs in the URL. `useState('explorer')` for the active tab will lose the value on navigation and break back/forward.
- **Passing `onImportStarted` through multiple layers:** Keep it at App level — don't thread it through OpeningsPage just in case.
- **Debouncing inside the hook:** Debounce the filter state variable in the parent component, pass the debounced value to the hook. Don't debounce inside the hook itself.
- **Keeping positionFilterActive gating:** The new Games tab always shows results; remove the boolean flag entirely.
- **useEffect to auto-trigger:** The current Openings.tsx uses a render-time side-effect (`setActiveRequest` called during render with `!autoAnalyzed` guard) to auto-analyze. Replace with direct `useQuery` — no manual triggering needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab UI with active indicator | Custom div-based tabs | shadcn `Tabs` (already installed) | Handles keyboard nav, ARIA, active styling |
| URL-derived tab state | Custom URL parser | `useLocation().pathname` + string matching | Router already tracks location |
| Debounce | Custom timer logic | `useMemo` + `useDebounce` (or inline `useEffect` + `useRef`) | ~5 lines; no library needed for this case |
| Query caching | Manual fetch + local state | TanStack Query `useQuery` | Deduplication, background refetch, stale time |

**Key insight:** The filter state merging is the most subtle engineering task. The old `StatsFilters` in `Openings.tsx` duplicates fields that already exist in `FilterState`. Do not create a third type — use `FilterState` from `FilterPanel.tsx` as the single source of truth.

## Common Pitfalls

### Pitfall 1: NavHeader Active State Breaks on Sub-Routes

**What goes wrong:** Current `NavHeader` uses `location.pathname === to` for exact match. This means the Openings nav item won't be highlighted when on `/openings/games` or `/openings/statistics`.

**Why it happens:** NavHeader uses strict equality `===` not `startsWith`.

**How to avoid:** Change the Openings nav item active detection:
```typescript
const isActive = (to: string) =>
  to === '/openings'
    ? location.pathname.startsWith('/openings')
    : location.pathname === to;
```

**Warning signs:** Openings nav item appears inactive while on a sub-tab.

### Pitfall 2: React Router Nested Routes Need `/*` on Parent

**What goes wrong:** If `App.tsx` registers `/openings` (no wildcard), React Router won't match `/openings/explorer` and the tab content won't render.

**How to avoid:** Register parent route as `/openings/*`:
```typescript
<Route path="/openings/*" element={<OpeningsPage />} />
```

**Warning signs:** Sub-tab URLs show blank page or redirect to catch-all.

### Pitfall 3: Tab Rerenders Reset Sub-Tab Component State

**What goes wrong:** If sub-tab components are conditionally rendered (unmounted when inactive), any local state inside them resets on tab switch. Pagination offset inside GamesTab would reset.

**How to avoid:** shadcn `TabsContent` renders content even when inactive (hidden via CSS `display:none`, not unmounted). Do NOT add `{activeTab === 'games' && <GamesTab />}` conditionals — use `TabsContent` as designed. Pagination offset managed in parent is safe because it's outside the TabsContent.

**Warning signs:** Filter state seems to reset on tab switch despite being in the parent.

### Pitfall 4: Filter State Object Identity Causes Infinite Query Loops

**What goes wrong:** If `filters` is rebuilt on every render (e.g., `const filters = { ...defaultFilters, ...overrides }` at render time), TanStack Query sees a new object reference every render and refetches continuously.

**Why it happens:** Query key includes the filters object; new object = new cache key = refetch.

**How to avoid:** Filter state must be a stable `useState` value. Only change it via `setFilters`. The query key `[..., filters]` compares by JSON serialization under the hood in TanStack Query v5 — stable as long as the object content doesn't change.

**Warning signs:** Network tab shows continuous requests firing.

### Pitfall 5: Debounce Needed for Auto-Fetch on Filter Changes

**What goes wrong:** Without debouncing, clicking Bullet + Blitz + Rapid time control filters in rapid succession triggers 3 separate API calls.

**How to avoid:** Use a 300ms debounce on the filter state that drives query keys:
```typescript
const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
const debouncedFilters = useDebounce(filters, 300); // simple hook ~5 lines
// Pass debouncedFilters to sub-tab hooks, not raw filters
```

The UI updates immediately (using raw `filters`); queries only fire after the user pauses.

### Pitfall 6: ImportProgress Loses Jobs on Navigation (if not lifted)

**What goes wrong:** If `activeJobIds` lives in `ImportPage`, navigating away from `/import` unmounts the page, destroying the state and stopping polling.

**How to avoid:** `activeJobIds` + `ImportProgress` must live in `App.tsx` (above the router outlet). The `ImportPage` only receives `onImportStarted` as a prop.

## Code Examples

Verified patterns from existing codebase:

### shadcn Tabs — Already Installed, Standard Usage
```typescript
// Source: shadcn tabs component already installed at frontend/src/components/ui/tabs.tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

<Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)}>
  <TabsList className="w-full" data-testid="openings-tabs">
    <TabsTrigger value="explorer" data-testid="tab-move-explorer">Move Explorer</TabsTrigger>
    <TabsTrigger value="games" data-testid="tab-games">Games</TabsTrigger>
    <TabsTrigger value="statistics" data-testid="tab-statistics">Statistics</TabsTrigger>
  </TabsList>
  <TabsContent value="explorer">
    <MoveExplorer ... />
  </TabsContent>
  <TabsContent value="games">
    ...
  </TabsContent>
  <TabsContent value="statistics">
    ...
  </TabsContent>
</Tabs>
```

### Route Setup in App.tsx
```typescript
// Source: existing App.tsx pattern — extend for nested routes
<Route element={<ProtectedLayout />}>
  <Route path="/" element={<Navigate to="/openings" replace />} />
  <Route path="/import" element={<ImportPage onImportStarted={handleImportStarted} />} />
  <Route path="/openings/*" element={<OpeningsPage />} />
  <Route path="/rating" element={<RatingPage />} />
  <Route path="/global-stats" element={<GlobalStatsPage />} />
</Route>
<Route path="*" element={<Navigate to="/openings" replace />} />
```

### useDebounce (inline — no library needed)
```typescript
// ~7 lines, inline in OpeningsPage or extracted to src/hooks/useDebounce.ts
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

### TimeSeriesRequest Construction Without Manual Trigger
```typescript
// Source: existing useTimeSeries in usePositionBookmarks.ts
// No activeRequest intermediate state — build inline
const timeSeriesRequest: TimeSeriesRequest | null = useMemo(() => {
  if (bookmarks.length === 0) return null;
  return {
    bookmarks: bookmarks.map((b) => ({
      bookmark_id: b.id,
      target_hash: b.target_hash,
      match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
      color: b.color,
    })),
    time_control: debouncedFilters.timeControls,
    platform: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponent_type: debouncedFilters.opponentType,
    recency: debouncedFilters.recency === 'all' ? null : debouncedFilters.recency,
  };
}, [bookmarks, debouncedFilters]);
const { data: tsData, isFetching } = useTimeSeries(timeSeriesRequest);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mutation + button for Games | Auto-fetch `useQuery` | Phase 14 | Removes Filter button; UX improvement |
| Manual Analyze trigger for Statistics | Auto-fetch via `useTimeSeries` driven by state | Phase 14 | Removes Analyze button |
| Import in Dialog | Import as dedicated page | Phase 14 | Delete All Games moves here too |
| Dashboard as hub | OpeningsPage as tabbed hub | Phase 14 | Dashboard.tsx deleted entirely |

**Deprecated/outdated after this phase:**
- `DashboardPage` (`Dashboard.tsx`): deleted
- `StatsFilters` interface in `Openings.tsx`: deleted (replaced by unified `FilterState`)
- `positionFilterActive` boolean gate: deleted
- `analysisResult` local state in Dashboard: deleted (replaced by `useQuery`)
- `handleAnalyze` / `handlePageChange` mutation callbacks: deleted

## Open Questions

1. **Games tab: starting position shows ALL games**
   - What we know: At starting position, full_hash matches every game position. The backend `/analysis/positions` with a starting-position hash will return all user games — this is the desired behavior (no positionFilterActive gating).
   - What's unclear: Whether the backend has performance implications for the starting position query (all games). Likely fine given existing indexed query pattern.
   - Recommendation: Implement as designed; no special-casing needed.

2. **`useDebounce` implementation approach**
   - What we know: No debounce utility exists in the project; a simple inline implementation is ~7 lines.
   - What's unclear: Whether the planner wants to extract it to a shared hook or keep it inline.
   - Recommendation: Create `src/hooks/useDebounce.ts` as a reusable hook — one file, trivial complexity.

3. **Inline ImportProgress on ImportPage vs global-only**
   - What we know: CONTEXT.md says progress is "shown inline on the page" and "Toast notification fires globally when import completes and user is on another page." UI-SPEC says `ImportProgress` is lifted to App level.
   - What's unclear: Whether `ImportPage` renders a second `ImportProgress` instance inline, or passes `activeJobIds` down via props.
   - Recommendation: Pass `activeJobIds` as a prop to `ImportPage`; render `ImportProgress` inline there in addition to the global one in App. The global one handles the toast-after-navigation case.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); no frontend test framework configured |
| Config file | `pyproject.toml` (backend: `asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

This phase is **frontend-only**. No backend code changes. Backend tests pass unchanged.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UIRS-01 | Three sub-tabs exist at /openings/explorer, /openings/games, /openings/statistics | manual-only | Browser: navigate to each sub-tab URL directly | N/A |
| UIRS-02 | Filter state persists across tab switches | manual-only | Browser: set filter, switch tab, verify filter unchanged | N/A |
| UIRS-03 | /import page shows import controls, no modal | manual-only | Browser: navigate to /import | N/A |
| UIRS-04 | Nav shows Import, Openings, Rating, Global Stats | manual-only | Browser: inspect nav header | N/A |

**No automated test framework is configured for the frontend.** All UIRS verification is via browser.

**Backend tests remain applicable and unchanged:**
- `uv run pytest` — full suite must stay green after any accidental backend file change

### Sampling Rate
- **Per task commit:** `uv run pytest -x -q` (backend; confirms no accidental backend regressions)
- **Per wave merge:** `uv run pytest` (full suite)
- **Phase gate:** Full backend suite green + manual browser verification of all four UIRS requirements before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all backend requirements. No frontend test files to create (no frontend test framework in the project).

## Sources

### Primary (HIGH confidence)
- Existing `frontend/src/App.tsx` — current routing structure, NavHeader active detection
- Existing `frontend/src/pages/Dashboard.tsx` — full decomposition source, state/handlers to relocate
- Existing `frontend/src/pages/Openings.tsx` — Statistics tab source, StatsFilters to eliminate
- Existing `frontend/src/components/import/ImportModal.tsx` — form controls to extract
- Existing `frontend/src/components/import/ImportProgress.tsx` — polling pattern, lift target
- Existing `frontend/src/hooks/useAnalysis.ts` — `useGamesQuery` pattern to extend
- Existing `frontend/src/hooks/useNextMoves.ts` — `useQuery` pattern for auto-fetch
- Existing `frontend/src/hooks/usePositionBookmarks.ts` — `useTimeSeries` enabled guard
- `.planning/phases/14-ui-restructuring/14-CONTEXT.md` — all locked decisions
- `.planning/phases/14-ui-restructuring/14-UI-SPEC.md` — layout, testid, routing contracts

### Secondary (MEDIUM confidence)
- React Router v6 docs — `useNavigate`, `useLocation`, nested `/*` wildcard routes
- shadcn Tabs docs — `value`/`onValueChange` controlled mode; TabsContent CSS hidden (not unmounted)
- TanStack Query v5 docs — `useQuery` stability, object query key comparison

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and used in project
- Architecture: HIGH — all patterns derived directly from existing codebase code
- Pitfalls: HIGH — derived from reading existing implementation; not theoretical

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable libraries, no version changes expected)
