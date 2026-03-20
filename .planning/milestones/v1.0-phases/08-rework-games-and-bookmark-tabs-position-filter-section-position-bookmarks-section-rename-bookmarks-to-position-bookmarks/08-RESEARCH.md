# Phase 8: Rework Games and Bookmark Tabs - Research

**Researched:** 2026-03-14
**Domain:** React/TypeScript UI restructuring + Alembic DB rename + full-stack rename refactor
**Confidence:** HIGH

## Summary

Phase 8 is a structural refactor with three distinct workstreams: (1) a full-stack rename of `bookmarks` → `position_bookmarks` across DB, backend, and frontend; (2) a UI restructuring of the Dashboard left column into three top-level collapsible sections; and (3) removal of the dedicated Bookmarks page and WDL chart components. There is no new feature logic — all existing hooks, CRUD operations, and drag-and-drop patterns are preserved and relocated.

The rename workstream touches 8 backend files, 4 frontend files, 1 Alembic migration, and all API paths. The UI workstream restructures Dashboard.tsx and FilterPanel.tsx substantially but reuses the existing shadcn/ui `Collapsible` primitive throughout. The most important risk is the `BookmarkCard.handleLoad` function: it currently navigates to `/` via React Router state injection, but since the Position bookmarks section will now be on the same page as the board, the Load action must instead call chess state mutations directly.

The Openings page currently imports and renders `WinRateChart` from `components/bookmarks/WinRateChart.tsx` and uses `useBookmarks` / `useTimeSeries` hooks — these references must be updated (rename hooks/types) but the Openings page's WinRateChart and WDLBarChart components are kept (they are on Openings, not Bookmarks). The WinRateChart component file and WDLBarChart file currently live in `components/bookmarks/` — they should move to a neutral location (e.g., `components/charts/`) since the Bookmarks folder is being renamed.

**Primary recommendation:** Execute the rename first (backend then frontend) as a single atomic pass, then do the UI restructure as a separate pass. This keeps diffs reviewable and avoids mixing concerns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Left column layout — three collapsible sections
- **Position filter** (open by default): Contains chessboard, opening name display, move list, board controls (back/forward/reset/flip), Played as / Match side toggle groups, and "Bookmark this position" button
- **Position bookmarks** (collapsed by default): Contains the BookmarkList with drag-and-drop reordering. Bookmark cards show only: drag handle, editable label, Load button, Delete button. No WDL bars, no WDL charts, no WinRateChart
- **More filters** (collapsed by default): Time control, Platform, Rated, Opponent, Recency — unchanged from current implementation
- **Filter + Import buttons**: Always visible below all three collapsible sections (not inside any collapsible)
- All three collapsibles are siblings at the same nesting level — no nested collapsibles

#### Bookmarks tab removal
- Remove the `/bookmarks` route and `BookmarksPage` component
- Remove "Bookmarks" from the `NAV_ITEMS` array (5 tabs → 4 tabs: Games, Openings, Rating, Global Stats)
- All bookmark functionality now lives inside the "Position bookmarks" collapsible section on the Games page

#### WDL removal from bookmarks
- Remove WDL bars from individual bookmark cards
- Remove WinRateChart (time-series line chart) entirely — it was on the old Bookmarks/Openings page
- No stats displayed on bookmark cards at all — they are lightweight position references

#### Bookmark button
- Moved from the action buttons row into the "Position filter" collapsible section
- Renamed from "Bookmark" to "Bookmark this position"
- Still opens the existing label dialog before saving

#### Rename scope: bookmarks → position_bookmarks
- **DB table**: `bookmarks` → `position_bookmarks` (Alembic migration with `op.rename_table`)
- **Backend model**: `Bookmark` → `PositionBookmark`, `__tablename__ = "position_bookmarks"`
- **Backend files**: `bookmark_repository.py` → `position_bookmark_repository.py`, `bookmarks.py` (schemas) → `position_bookmarks.py`, `bookmarks.py` (router) → `position_bookmarks.py`
- **Backend schemas**: `BookmarkCreate` → `PositionBookmarkCreate`, `BookmarkUpdate` → `PositionBookmarkUpdate`, `BookmarkResponse` → `PositionBookmarkResponse`, etc.
- **API endpoint paths**: `/bookmarks` → `/position-bookmarks` (hyphenated in URL)
- **Frontend types**: `bookmarks.ts` → `position_bookmarks.ts`, `BookmarkResponse` → `PositionBookmarkResponse`
- **Frontend hooks**: `useBookmarks.ts` → `usePositionBookmarks.ts`, hook names updated accordingly
- **Frontend components**: `components/bookmarks/` → `components/position-bookmarks/`, component names prefixed with `PositionBookmark`
- **API client paths**: all `/bookmarks` calls updated to `/position-bookmarks`

### Claude's Discretion
- Exact styling of collapsible section headers (chevron icons, font size, spacing)
- How to handle the "Load" bookmark action now that bookmarks are on the same page as the board (no navigation needed — can just replay moves in-place)
- Empty state text for the Position bookmarks section when no bookmarks exist
- Whether the Openings page needs updates after WinRateChart removal (it may share the chart)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core (already in project — no new installations)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| shadcn/ui Collapsible | via radix-ui | Collapsible sections | Already used in FilterPanel |
| @dnd-kit/core + sortable | existing | Drag-and-drop bookmark reorder | Already used in BookmarkList |
| TanStack Query | existing | Server state (bookmarks) | Query key rename: `'bookmarks'` → `'position-bookmarks'` |
| Alembic | existing | DB migration (rename table) | `op.rename_table` + index rename |
| react-router-dom | existing | Remove /bookmarks route | No version change |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended File Structure After Phase 8

**Backend:**
```
app/
├── models/
│   └── position_bookmark.py          # renamed from bookmark.py
├── repositories/
│   └── position_bookmark_repository.py  # renamed from bookmark_repository.py
├── routers/
│   └── position_bookmarks.py         # renamed from bookmarks.py
├── schemas/
│   └── position_bookmarks.py         # renamed from bookmarks.py
alembic/versions/
└── XXXX_rename_bookmarks_to_position_bookmarks.py
```

**Frontend:**
```
src/
├── components/
│   ├── position-bookmarks/           # renamed from bookmarks/
│   │   ├── PositionBookmarkList.tsx  # renamed, simplified props (no wdlStatsMap)
│   │   └── PositionBookmarkCard.tsx  # renamed, no WDL bar, no MiniBoard, Load in-place
│   └── charts/                       # NEW: moved from bookmarks/
│       ├── WinRateChart.tsx          # moved (still used by Openings page)
│       └── WDLBarChart.tsx           # moved (still used by Openings page)
├── hooks/
│   └── usePositionBookmarks.ts       # renamed from useBookmarks.ts
├── types/
│   └── position_bookmarks.ts         # renamed from bookmarks.ts
├── pages/
│   ├── Dashboard.tsx                 # major restructure
│   └── Bookmarks.tsx                 # DELETED
├── api/
│   └── client.ts                     # bookmarksApi → positionBookmarksApi, paths updated
└── App.tsx                           # remove /bookmarks route and NAV_ITEMS entry
```

### Pattern 1: Alembic Table Rename
**What:** Use `op.rename_table` + `op.rename_constraint` / index rename for clean reversible migration.
**When to use:** Renaming an existing table without changing schema.

```python
# Source: Alembic docs
def upgrade() -> None:
    op.rename_table('bookmarks', 'position_bookmarks')
    # Rename the user_id index (Alembic-generated name)
    op.execute('ALTER INDEX ix_bookmarks_user_id RENAME TO ix_position_bookmarks_user_id')

def downgrade() -> None:
    op.execute('ALTER INDEX ix_position_bookmarks_user_id RENAME TO ix_bookmarks_user_id')
    op.rename_table('position_bookmarks', 'bookmarks')
```

The index was created as `ix_bookmarks_user_id` (confirmed in migration `00e469a985ef`). PostgreSQL `ALTER INDEX ... RENAME TO` is the correct syntax.

### Pattern 2: Three-Section Collapsible Left Column in Dashboard.tsx

**What:** Replace the flat left-column layout with three sibling `<Collapsible>` sections.
**When to use:** This is the target layout for Dashboard.tsx after the restructure.

```tsx
// shadcn/ui Collapsible — already imported in FilterPanel.tsx
// Pattern matches existing "More filters" usage in FilterPanel

const [positionFilterOpen, setPositionFilterOpen] = useState(true);   // open by default
const [bookmarksOpen, setBookmarksOpen] = useState(false);             // collapsed by default
const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);         // collapsed by default

// Section header button pattern (match existing FilterPanel style):
<Collapsible open={positionFilterOpen} onOpenChange={setPositionFilterOpen}>
  <CollapsibleTrigger asChild>
    <Button
      variant="ghost"
      size="sm"
      className="w-full justify-between px-2 text-sm font-medium"
      data-testid="section-position-filter"
    >
      Position filter
      {positionFilterOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
    </Button>
  </CollapsibleTrigger>
  <CollapsibleContent>
    {/* board, opening name, move list, board controls, played-as/match-side toggles, bookmark button */}
  </CollapsibleContent>
</Collapsible>
```

### Pattern 3: BookmarkCard "Load" In-Place (no navigation)

**What:** Since Position bookmarks is on the same page as the board, Load should replay moves in-place rather than navigate via router state.
**Current code:** `handleLoad` calls `navigate('/', { state: { bookmark: ... } })` — irrelevant when already on `/`.

The Dashboard's chess state and filter setters must be passed down to `PositionBookmarkCard` as callback props:

```tsx
// In Dashboard.tsx — pass callback to PositionBookmarkList
const handleLoadBookmark = useCallback((bkm: PositionBookmarkResponse) => {
  chess.loadMoves(bkm.moves);
  setBoardFlipped(bkm.is_flipped ?? false);
  setFilters(prev => ({
    ...prev,
    color: bkm.color ?? null,
    matchSide: bkm.match_side,
  }));
}, [chess]);

// PositionBookmarkList passes onLoad down to each card
// PositionBookmarkCard calls onLoad(bookmark) instead of navigate()
```

This replaces the old `useEffect` mount-side hydration that read `location.state` — that effect can be removed from Dashboard entirely.

### Pattern 4: Rename queryKey in TanStack Query

**What:** The `useBookmarks` hook uses `queryKey: ['bookmarks']`. After rename to `usePositionBookmarks`, the key should change to `['position-bookmarks']`.
**Impact:** All `qc.invalidateQueries({ queryKey: ['bookmarks'] })` calls in mutations must also update to `['position-bookmarks']`.

```typescript
// In usePositionBookmarks.ts
export function usePositionBookmarks() {
  return useQuery({
    queryKey: ['position-bookmarks'],
    queryFn: positionBookmarksApi.list,
  });
}
// All mutations: onSuccess: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] })
```

### Pattern 5: WDLBarChart and WinRateChart relocation

**What:** These components live in `components/bookmarks/` but are only used by `Openings.tsx`. After rename, they will be in `components/position-bookmarks/` — but since they have no relation to position-bookmarks CRUD, moving them to `components/charts/` is cleaner.
**Decision (Claude's Discretion):** Move to `components/charts/` and update imports in `Openings.tsx`.

### Anti-Patterns to Avoid

- **Nested collapsibles:** The three sections must be flat siblings. Do not put the "More filters" Collapsible inside another Collapsible.
- **Keeping `useEffect` mount hydration:** The old `useEffect` in Dashboard that read `location.state` for bookmark loading was only needed for cross-page navigation. Remove it entirely — the in-place `handleLoadBookmark` callback replaces it.
- **Forgetting `op.rename_table` downgrade:** The downgrade must reverse both the table rename and the index rename, in opposite order.
- **Missing router import cleanup:** `App.tsx` imports `BookmarksPage` — it must be removed together with the route.
- **Forgetting `app/main.py` router include:** `bookmarks.router` in `main.py` must be updated to reference the renamed `position_bookmarks.router`.
- **Stale query keys:** `timeSeriesApi` POST is referenced in `Openings.tsx` via `useTimeSeries` — that hook is in `useBookmarks.ts` today; after rename to `usePositionBookmarks.ts`, `Openings.tsx` must update its import path. The `useTimeSeries` hook itself can stay (it's about time series, not about CRUD) or move — consistent naming matters.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sections | Custom accordion/expand logic | shadcn/ui `Collapsible` | Already used in FilterPanel — zero new dependency |
| Drag-and-drop reorder | Custom drag logic | @dnd-kit (already in BookmarkList) | Retain existing DnD implementation unchanged |
| DB table rename | Manual data migration | `op.rename_table` (Alembic) | Atomic, reversible, PostgreSQL-correct |
| In-place board state load | New API endpoint | Direct state mutation via callback props | No server round-trip needed |

## Common Pitfalls

### Pitfall 1: Alembic autogenerate will not detect op.rename_table
**What goes wrong:** Running `alembic revision --autogenerate` after changing `__tablename__` will generate a DROP + CREATE, not a rename. This destroys data.
**Why it happens:** Autogenerate sees a missing table and a new table — it can't infer rename intent.
**How to avoid:** Write the migration manually using `op.rename_table`. Do NOT use `--autogenerate` for this migration.
**Warning signs:** Generated migration contains `op.drop_table('bookmarks')` and `op.create_table('position_bookmarks', ...)`.

### Pitfall 2: Index name not renamed alongside table
**What goes wrong:** After `op.rename_table('bookmarks', 'position_bookmarks')`, the index `ix_bookmarks_user_id` still exists with the old name. Future Alembic autogenerations may try to recreate it.
**Why it happens:** PostgreSQL renames the table but not indexes automatically.
**How to avoid:** Explicitly rename the index in the same migration using `op.execute('ALTER INDEX ix_bookmarks_user_id RENAME TO ix_position_bookmarks_user_id')`.

### Pitfall 3: FastAPI route ordering for `/position-bookmarks/reorder`
**What goes wrong:** If the `PUT /position-bookmarks/reorder` route is defined after `PUT /position-bookmarks/{bookmark_id}`, FastAPI interprets "reorder" as an integer bookmark ID.
**Why it happens:** FastAPI path parameter matching is first-match.
**How to avoid:** Keep `reorder` route definition BEFORE `{bookmark_id}` route — this constraint is already documented in the existing `bookmarks.py` router (line 46-48 comment). Preserve it during rename.

### Pitfall 4: BookmarkCard MiniBoard removal
**What goes wrong:** The simplified `PositionBookmarkCard` spec says no MiniBoard. The current card renders `<MiniBoard fen={bookmark.fen} size={100} flipped={bookmark.is_flipped} />`. Removing it also removes the need to pass `fen` and `is_flipped` to the card display — but these fields still exist on the type (they're needed for Load).
**How to avoid:** Keep `fen` and `is_flipped` in `PositionBookmarkResponse` type. Just don't render MiniBoard in the card JSX.

### Pitfall 5: Openings.tsx WinRateChart import path breaks after move
**What goes wrong:** `Openings.tsx` imports `WinRateChart` from `@/components/bookmarks/WinRateChart` and `WDLBarChart` from `@/components/bookmarks/WDLBarChart`. After rename/move, these paths are stale.
**How to avoid:** Update imports in `Openings.tsx` to match the new location (`@/components/charts/` or `@/components/position-bookmarks/`).

### Pitfall 6: `useTimeSeries` hook location after rename
**What goes wrong:** `Openings.tsx` imports `useTimeSeries` from `@/hooks/useBookmarks`. After rename to `usePositionBookmarks.ts`, this import breaks.
**How to avoid:** `Openings.tsx` must update its import to `@/hooks/usePositionBookmarks`. The `useTimeSeries` hook itself is about the analysis/time-series endpoint — it could alternatively live in `useAnalysis.ts` or stay in `usePositionBookmarks.ts`. Either is acceptable; just be consistent.

### Pitfall 7: Dashboard mount-effect leftover
**What goes wrong:** Dashboard.tsx has a `useEffect(() => { ... }, [])` that reads `location.state.bookmark` on mount to hydrate the board after navigating from `/bookmarks`. After the Bookmarks page is removed, this effect code is unreachable dead code but still executes harmlessly. However it creates confusion.
**How to avoid:** Remove the `useEffect` and `useLocation` import from Dashboard.tsx during the UI restructure.

### Pitfall 8: `data-testid` on all new interactive elements
**What goes wrong:** CLAUDE.md mandates `data-testid` on every interactive element. New collapsible triggers and the in-place Load callback button need IDs.
**How to avoid:** Apply during implementation:
- `data-testid="section-position-filter"` on Position filter CollapsibleTrigger
- `data-testid="section-position-bookmarks"` on Position bookmarks CollapsibleTrigger
- `data-testid="section-more-filters"` on More filters CollapsibleTrigger
- Retain existing `data-testid="bookmark-btn-load-{id}"` on Load buttons

## Code Examples

### Alembic rename migration
```python
# Source: Alembic documentation + existing migration pattern in project
def upgrade() -> None:
    op.rename_table('bookmarks', 'position_bookmarks')
    op.execute('ALTER INDEX ix_bookmarks_user_id RENAME TO ix_position_bookmarks_user_id')

def downgrade() -> None:
    op.execute('ALTER INDEX ix_position_bookmarks_user_id RENAME TO ix_bookmarks_user_id')
    op.rename_table('position_bookmarks', 'bookmarks')
```

### Backend model rename (position_bookmark.py)
```python
class PositionBookmark(Base):
    __tablename__ = "position_bookmarks"
    # All columns identical to current Bookmark model
```

### Backend router rename in main.py
```python
from app.routers import analysis, position_bookmarks, imports, auth

app.include_router(position_bookmarks.router)  # was: bookmarks.router
```

### Frontend API client rename
```typescript
// client.ts — rename object and update paths
export const positionBookmarksApi = {
  list: () =>
    apiClient.get<PositionBookmarkResponse[]>('/position-bookmarks').then(r => r.data),
  create: (data: PositionBookmarkCreate) =>
    apiClient.post<PositionBookmarkResponse>('/position-bookmarks', data).then(r => r.data),
  updateLabel: (id: number, data: PositionBookmarkUpdate) =>
    apiClient.put<PositionBookmarkResponse>(`/position-bookmarks/${id}`, data).then(r => r.data),
  remove: (id: number) =>
    apiClient.delete(`/position-bookmarks/${id}`),
  reorder: (req: PositionBookmarkReorderRequest) =>
    apiClient.put<PositionBookmarkResponse[]>('/position-bookmarks/reorder', req).then(r => r.data),
};
```

### PositionBookmarkCard simplified (no WDL, no MiniBoard, in-place Load)
```tsx
// No MiniBoard, no WDLBar, no useNavigate
// Load calls onLoad prop instead of navigate()
interface Props {
  bookmark: PositionBookmarkResponse;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}

export function PositionBookmarkCard({ bookmark, onLoad }: Props) {
  // drag handle, editable label (existing logic), Load button, Delete button
  // Load: onClick={() => onLoad(bookmark)}
}
```

### PositionBookmarkList simplified (no wdlStatsMap)
```tsx
interface Props {
  bookmarks: PositionBookmarkResponse[];
  onReorder: (orderedIds: number[]) => void;
  onLoad: (bookmark: PositionBookmarkResponse) => void;
}
// Pass onLoad down to each PositionBookmarkCard
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cross-page Load via router state | In-place chess.loadMoves() callback | Phase 8 | Removes useEffect hydration from Dashboard |
| Bookmarks as separate nav tab | Embedded in Dashboard left column | Phase 8 | Removes /bookmarks route |
| `bookmarks` table | `position_bookmarks` table | Phase 8 | Alembic rename migration required |
| WDL stats on bookmark cards | No stats on cards (lightweight refs) | Phase 8 | Simpler card; WDL lives only on Openings page |

**Deprecated/removed in this phase:**
- `pages/Bookmarks.tsx` — deleted entirely
- `BookmarkCard` WDL bar rendering — stripped
- `useEffect` mount hydration in Dashboard.tsx — removed
- `useTimeSeries` dependency in `BookmarksPage` — page is deleted; hook stays in usePositionBookmarks for Openings page

## Open Questions

1. **WinRateChart file location after move**
   - What we know: `WinRateChart.tsx` and `WDLBarChart.tsx` currently live in `components/bookmarks/`. The `bookmarks/` folder becomes `position-bookmarks/`. These charts are used only by Openings.tsx, not by the Position bookmarks UI.
   - What's unclear: Whether to keep them in `position-bookmarks/` or move to `components/charts/`.
   - Recommendation (Claude's Discretion): Move to `components/charts/` since they are general charting components unrelated to bookmark CRUD. Update imports in `Openings.tsx`.

2. **useTimeSeries hook placement**
   - What we know: `useTimeSeries` is currently in `useBookmarks.ts`. It calls `POST /analysis/time-series`, not a bookmarks endpoint. `Openings.tsx` uses it.
   - What's unclear: Should `useTimeSeries` live in `usePositionBookmarks.ts` (renamed file) or be moved to `useAnalysis.ts`?
   - Recommendation (Claude's Discretion): Keep in `usePositionBookmarks.ts` for this phase to minimize diff. Moving to `useAnalysis.ts` is a future cleanup item.

3. **Empty state for Position bookmarks section**
   - What we know: When no bookmarks exist, a message is needed inside the collapsed section.
   - Recommendation (Claude's Discretion): "No position bookmarks yet. Use the 'Bookmark this position' button above to save positions." — simple, actionable, consistent with existing empty state patterns.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) |
| Config file | `pyproject.toml` (inferred from project) |
| Quick run command | `uv run pytest -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

This phase has no new v1 requirements (it is a refactor/restructure). The rename must not break existing behavior:

| Area | Behavior | Test Type | Notes |
|------|----------|-----------|-------|
| DB migration | `position_bookmarks` table exists after upgrade | manual | `uv run alembic upgrade head` |
| Backend CRUD | All existing bookmark CRUD endpoints work at new `/position-bookmarks` paths | manual API test or existing pytest if any |
| Frontend | Position filter section open by default | manual browser | |
| Frontend | Position bookmarks section collapsed by default | manual browser | |
| Frontend | More filters section collapsed by default | manual browser | |
| Frontend | Load bookmark in-place replays moves on board | manual browser | |
| Frontend | Openings page still renders WinRateChart and WDLBarChart | manual browser | |
| Frontend | Nav has 4 tabs (no Bookmarks tab) | manual browser | |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (backend changes only)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + manual browser verification before `/gsd:verify-work`

### Wave 0 Gaps
- No new test files required — this is a rename/restructure with no new logic.
- Existing tests (if any target bookmark endpoints) will need path updates from `/bookmarks` to `/position-bookmarks`.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — all existing files read in full
- Alembic migration `00e469a985ef` — confirmed index name `ix_bookmarks_user_id`
- `components/ui/collapsible.tsx` — confirmed Radix-based shadcn/ui Collapsible already available
- `FilterPanel.tsx` — confirmed existing collapsible pattern with ChevronUp/ChevronDown

### Secondary (MEDIUM confidence)
- PostgreSQL `ALTER INDEX ... RENAME TO` syntax — standard SQL DDL, stable across versions
- Alembic `op.rename_table` — documented in official Alembic ops API

## Metadata

**Confidence breakdown:**
- Rename scope: HIGH — all files inspected, rename targets confirmed
- Alembic migration pattern: HIGH — confirmed index name from existing migration
- UI restructure: HIGH — existing collapsible pattern verified in FilterPanel
- Load in-place approach: HIGH — chess.loadMoves() and setBoardFlipped exist in Dashboard
- WinRateChart/WDLBarChart concern: HIGH — Openings.tsx confirmed to use both, from bookmarks/ folder

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack, no fast-moving dependencies)
