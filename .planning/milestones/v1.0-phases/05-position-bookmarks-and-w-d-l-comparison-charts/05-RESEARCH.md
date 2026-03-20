# Phase 5: Position Bookmarks and W/D/L Comparison Charts - Research

**Researched:** 2026-03-13
**Domain:** Full-stack feature: PostgreSQL bookmarks table, FastAPI CRUD + time-series endpoints, React drag-and-drop sortable list, Recharts line chart
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Navigation and routing**
- New `/bookmarks` route — separate page, not tabs or a panel on the existing dashboard
- Header gets two nav tabs: **Analysis** (existing /) and **Bookmarks** (/bookmarks)
- Existing dashboard layout unchanged

**Adding bookmarks**
- **Bookmark button** (`★ Bookmark`) sits next to the Analyze button in the left column of the Analysis page
- Clicking it saves the current position (moves + filters + hash + FEN + opening label if known)
- Works independently of whether analysis has been run

**Loading a bookmark to edit**
- On the /bookmarks page, each bookmark has a **[Load]** button
- Clicking navigates to `/` with the board pre-populated from the bookmark (moves replayed, filters restored, bookmark ID tracked for overwrite)
- After editing, user clicks **Save** (overwrite in place — not save-as-new)

**/bookmarks page layout (desktop)**
- Full-width stacked layout: bookmark list on top, win rate line chart below
- Each bookmark row: drag handle (☰), label (editable), [Load] [✕] actions, WDL bar underneath
- [+ Add bookmark] button below the list (alternative to adding from dashboard)
- Mobile: same vertical stack, drag-and-drop supported

**Bookmark storage**
- **Backend database** (new `bookmarks` table in PostgreSQL)
- Persists across devices and browser clears
- Stored fields per bookmark: `moves` (SAN array), `color` (played-as filter), `match_side`, `label`, `target_hash` (BIGINT Zobrist), `fen` (position FEN for potential thumbnail use), `sort_order` (integer for drag reorder)
- No cap on number of bookmarks per user

**Bookmark editing rules**
- Saving an edited bookmark **overwrites in place** — original is replaced
- Label is editable inline on the /bookmarks page (no separate edit modal needed)

**WDL bars on bookmarks page**
- **Reuse existing `WDLBar` component** — same look as analysis results, rendered under each bookmark row
- Stats fetched from backend when /bookmarks page loads

**Chart library**
- **Recharts** — React-native, TypeScript-friendly, fits shadcn/ui ecosystem
- shadcn/ui provides Recharts chart wrappers (consistent styling)

**Win rate over time line chart**
- **One line per bookmark** showing monthly win rate
- Win rate = wins / (wins + draws + losses) per month
- **Monthly buckets** — each data point is one calendar month
- **Skip months with 0 games** — gap in the line (no interpolation)
- **All-time by default** — full historical range shown
- Data fetched from new backend endpoint: `GET /analysis/time-series` (accepts bookmark params)

### Claude's Discretion
- Exact drag-and-drop library (react-beautiful-dnd or @dnd-kit — pick what fits React 19 best)
- Inline label editing UX (click to edit, blur to save, or pencil icon)
- Loading skeleton / empty state design for bookmarks page
- Color coding of lines in the win rate chart per bookmark (use distinct hues)
- Whether the [+ Add bookmark] on the /bookmarks page opens a modal or navigates to / with a special "add bookmark" mode

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 5 adds two interlocking features: a bookmark system (backend CRUD + frontend list with drag-and-drop reordering) and a win-rate-over-time line chart comparing all saved positions. The backend adds a `bookmarks` table, three new REST endpoints (CRUD and time-series), and a new `bookmark_repository`. The frontend adds a `/bookmarks` route, a `BookmarksPage`, and nav tabs in the header.

The key technical decisions already made are: Recharts for charting and PostgreSQL backend storage. The research confirms both are correct choices for React 19 and the existing stack. The only remaining discretion item of substance is the drag-and-drop library: `react-beautiful-dnd` is officially deprecated and archived (repo made read-only April 2025); `@dnd-kit/core` v6.3.1 + `@dnd-kit/sortable` v10.0.0 is the correct modern choice with `react: >=16.8.0` peer dependency that works with React 19.

The time-series endpoint requires a GROUP BY DATE_TRUNC('month', played_at) SQL query — a pattern not currently in the codebase but straightforward with SQLAlchemy's `func.date_trunc`.

**Primary recommendation:** Use `@dnd-kit/core` + `@dnd-kit/sortable` for drag-and-drop. Install Recharts 2.15.4 (latest v2; explicit React 19 support, no workaround needed). Add the shadcn chart component via CLI. The CONTEXT.md specifies `GET /analysis/time-series`; implement it in the existing `analysis` router following the established router/service/repository layering.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core | 6.3.1 | Drag-and-drop context + sensors | Active, React 19 compatible (>=16.8.0), replaces deprecated react-beautiful-dnd |
| @dnd-kit/sortable | 10.0.0 | Sortable list abstraction over @dnd-kit/core | Pairs with core; provides `useSortable`, `SortableContext`, `arrayMove` |
| recharts | 2.15.4 | Charting (line chart) | Decision-locked; React 19 explicit support in peerDeps |
| shadcn chart | (copy-paste) | ChartContainer / ChartTooltip wrappers | Decision-locked; consistent dark-mode styling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @dnd-kit/utilities | ^3.2.2 | CSS transform helpers (CSS.Transform.toString) | Required for drag visual feedback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @dnd-kit/core | react-beautiful-dnd | react-beautiful-dnd is archived/deprecated (April 2025), no React 19 support |
| recharts 2.x | recharts 3.x | v3 is newest but shadcn chart component has known v3 API incompatibilities (issue #7669); v2.15.4 supports React 19 and works with shadcn chart out of the box |
| recharts 2.x | Nivo, Visx | No shadcn integration, more complex setup, decision already locked |

**Installation:**
```bash
# Frontend
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities recharts
npx shadcn@latest add chart
```

---

## Architecture Patterns

### Recommended Project Structure

**Backend additions:**
```
app/
├── models/
│   └── bookmark.py          # Bookmark SQLAlchemy model
├── repositories/
│   └── bookmark_repository.py  # CRUD + ordering operations
├── routers/
│   └── bookmarks.py         # GET/POST/PUT/DELETE /bookmarks endpoints
├── schemas/
│   └── bookmarks.py         # Pydantic v2 request/response schemas
└── services/
    └── bookmark_service.py  # Business logic (optional thin layer)
    # analysis_service.py gets new time_series function
    # analysis_repository.py gets new query_time_series function
```

**Frontend additions:**
```
frontend/src/
├── pages/
│   └── Bookmarks.tsx        # BookmarksPage component
├── components/
│   └── bookmarks/
│       ├── BookmarkList.tsx         # Sortable list with @dnd-kit
│       ├── BookmarkRow.tsx          # Single row: handle, label, WDL, actions
│       └── WinRateChart.tsx         # Recharts multi-line chart
├── hooks/
│   └── useBookmarks.ts      # TanStack Query hooks for bookmark CRUD
└── api/
    └── api.ts               # Add bookmark + time-series API calls
```

### Pattern 1: SQLAlchemy Bookmark Model
**What:** New `bookmarks` table following Base class conventions (BIGINT primary key via type_annotation_map, DateTime timezone-aware)
**When to use:** Backend data layer

```python
# Source: established project pattern (app/models/game.py)
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    target_hash: Mapped[int] = mapped_column(nullable=False)  # BIGINT via type_annotation_map
    fen: Mapped[str] = mapped_column(String(200), nullable=False)
    moves: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded SAN array
    color: Mapped[str | None] = mapped_column(String(10))     # "white"|"black"|None
    match_side: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
```

**Note on `moves` storage:** Store as JSON string (`json.dumps(sans_list)`) — avoids a separate junction table, and the array is small (rarely >30 elements).

### Pattern 2: Time-Series Repository Query
**What:** GROUP BY calendar month to get monthly W/D/L counts per bookmark's hash
**When to use:** `GET /analysis/time-series` endpoint

```python
# Source: SQLAlchemy 2.x async pattern + PostgreSQL DATE_TRUNC
from sqlalchemy import func, select, extract
from app.models.game import Game
from app.models.game_position import GamePosition

async def query_time_series(
    session: AsyncSession,
    user_id: int,
    hash_column,
    target_hash: int,
    color: str | None,
) -> list[tuple]:
    """Return (year, month, result, user_color) tuples for monthly bucketing."""
    stmt = (
        select(
            func.date_trunc("month", Game.played_at).label("month"),
            Game.result,
            Game.user_color,
        )
        .join(GamePosition, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
        )
        .distinct(Game.id)
    )
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    stmt = stmt.where(Game.played_at.isnot(None))
    rows = await session.execute(stmt)
    return list(rows.all())
```

The service layer then groups the raw rows into monthly buckets and computes win_rate = wins / total.

### Pattern 3: @dnd-kit Sortable List
**What:** Drag-and-drop reorder using `SortableContext` + `useSortable` hook
**When to use:** BookmarkList.tsx

```typescript
// Source: https://docs.dndkit.com/presets/sortable
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors
} from '@dnd-kit/core';
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function BookmarkList({ bookmarks, onReorder }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = bookmarks.findIndex(b => b.id === active.id);
      const newIndex = bookmarks.findIndex(b => b.id === over.id);
      onReorder(arrayMove(bookmarks, oldIndex, newIndex));
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={bookmarks.map(b => b.id)} strategy={verticalListSortingStrategy}>
        {bookmarks.map(b => <SortableBookmarkRow key={b.id} bookmark={b} />)}
      </SortableContext>
    </DndContext>
  );
}

function SortableBookmarkRow({ bookmark }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: bookmark.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <span {...listeners}>☰</span>  {/* drag handle */}
      {/* rest of row */}
    </div>
  );
}
```

### Pattern 4: Recharts Multi-Line Chart with shadcn Wrapper
**What:** One line per bookmark, monthly win rate on Y axis, month label on X axis
**When to use:** WinRateChart.tsx

```typescript
// Source: https://ui.shadcn.com/docs/components/chart
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';

// chartConfig: one entry per bookmark with a distinct color
const chartConfig = {
  bookmark_1: { label: 'e4 e5 Nf3', color: 'hsl(var(--chart-1))' },
  bookmark_2: { label: 'Sicilian', color: 'hsl(var(--chart-2))' },
};

// data: array of month objects with win_rate per bookmark key
// [{ month: '2025-01', bookmark_1: 0.55, bookmark_2: 0.40 }, ...]
// Months with no games for a bookmark have undefined (not 0) → gap in line

<ChartContainer config={chartConfig} className="w-full">
  <LineChart data={data}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="month" />
    <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
    <ChartTooltip content={<ChartTooltipContent />} />
    {bookmarks.map(b => (
      <Line
        key={b.id}
        dataKey={`bookmark_${b.id}`}
        stroke={`var(--color-bookmark_${b.id})`}
        dot={false}
        connectNulls={false}  // gaps for months with no games
      />
    ))}
  </LineChart>
</ChartContainer>
```

**shadcn chart install command:**
```bash
npx shadcn@latest add chart
```
This creates `frontend/src/components/ui/chart.tsx`.

### Pattern 5: Bookmark Loading via URL State
**What:** Navigating from /bookmarks [Load] to / with pre-populated state
**When to use:** BookmarkRow.tsx [Load] button + DashboardPage initialization

The cleanest pattern for this project is to pass bookmark data via React Router `state` (not query params) since the data is structured:

```typescript
// In BookmarkRow.tsx
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
const handleLoad = () => {
  navigate('/', {
    state: {
      bookmark: {
        id: bookmark.id,
        moves: bookmark.moves,      // string[]
        color: bookmark.color,      // 'white' | 'black' | null
        matchSide: bookmark.match_side,
      }
    }
  });
};
```

```typescript
// In DashboardPage.tsx — read location state on mount
import { useLocation } from 'react-router-dom';

const location = useLocation();
const loadedBookmark = location.state?.bookmark ?? null;

useEffect(() => {
  if (loadedBookmark) {
    chess.loadMoves(loadedBookmark.moves);  // new hook method needed
    setFilters(prev => ({
      ...prev,
      color: loadedBookmark.color,
      matchSide: loadedBookmark.matchSide,
    }));
    setActiveBookmarkId(loadedBookmark.id);  // track for overwrite-save
  }
}, []);  // only on mount
```

### Pattern 6: useChessGame loadMoves Extension
**What:** New `loadMoves(sans: string[])` method on the hook
**When to use:** Restoring board state from a bookmark

The `replayTo` internal helper already does this. The new method is just a thin wrapper:

```typescript
const loadMoves = useCallback((sans: string[]) => {
  setMoveHistory(sans);
  replayTo(sans, sans.length);
}, [replayTo]);
```

Add `loadMoves` to `ChessGameState` interface and return it from the hook.

### Pattern 7: Bookmark CRUD API Endpoints
**What:** Standard RESTful endpoints following existing router conventions
**When to use:** New `app/routers/bookmarks.py`

```
GET    /bookmarks               → list all for user, ordered by sort_order
POST   /bookmarks               → create new bookmark
PUT    /bookmarks/{id}          → update label and/or sort_order
DELETE /bookmarks/{id}          → delete bookmark
GET    /analysis/time-series    → monthly win rate for a set of bookmark hashes
```

The time-series endpoint belongs in the `analysis` router (same tag, same concept as `/analysis/positions`) and accepts a list of bookmark params.

### Anti-Patterns to Avoid

- **Storing `moves` as a PostgreSQL ARRAY**: Adds complexity for minimal gain. JSON string via `json.dumps`/`json.loads` in Python is simpler and equally fast for small arrays.
- **Fetching time-series data per-bookmark sequentially**: Batch all bookmarks in a single query with `WHERE (hash_column, user_id) IN (...)` or run parallel queries. Never N+1.
- **Blocking route navigation with async state init**: Load the dashboard immediately, then hydrate from `location.state` in a `useEffect`. Don't wait for board state before rendering.
- **`connectNulls={true}` on Recharts Line**: The decision is to show gaps for months with 0 games. `connectNulls` defaults to false — do not override it.
- **Using CSS `display:none` for the drag handle on mobile**: @dnd-kit's `PointerSensor` works on touch events natively. The drag handle should always render.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop reordering | Custom mouse/touch event tracking | @dnd-kit/sortable | Handles keyboard accessibility, touch, pointer cancellation, focus management, ARIA |
| Sortable list item IDs | String-based item tracking | `arrayMove` from @dnd-kit/sortable | Handles index mutation correctly during live drag |
| Chart color cycling | Custom hsl rotation logic | shadcn `--chart-1` through `--chart-5` CSS variables | Already defined in Nova/Radix theme, respects dark mode |
| Month label formatting | String manipulation | `new Date(monthStr).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })` | Standard JS Date API |
| Optimistic reorder UI | Complex rollback logic | TanStack Query `onMutate`/`onError`/`onSettled` pattern | Built-in optimistic update support |

**Key insight:** The drag-and-drop and charting problems look deceptively simple but have many edge cases (accessibility, touch, keyboard, data gaps). Both have well-maintained libraries that cover these.

---

## Common Pitfalls

### Pitfall 1: BIGINT precision in JSON for target_hash
**What goes wrong:** `target_hash` is a 64-bit Zobrist hash. If returned as a JSON number, JavaScript loses precision for values > 2^53.
**Why it happens:** JSON numbers are IEEE-754 doubles.
**How to avoid:** The existing `coerce_target_hash` validator in `AnalysisRequest` already handles string→int on input. For bookmarks API responses, return `target_hash` as a string (add `@field_serializer` or use `json_encoders`) OR handle it client-side as a string field in the TypeScript type (matching existing `AnalysisRequest.target_hash: string`).
**Warning signs:** Incorrect analysis results when loading a bookmark — hash appears correct as a decimal string but differs numerically.

### Pitfall 2: DATE_TRUNC returns timezone-aware datetime in PostgreSQL
**What goes wrong:** `func.date_trunc("month", Game.played_at)` returns a `datetime` with timezone. Grouping may produce unexpected results if played_at is stored in UTC but displayed in local time.
**Why it happens:** `played_at` is stored as `DateTime(timezone=True)` (confirmed in `base.py`).
**How to avoid:** All dates are UTC — treat the truncated month as UTC label (`"2025-01"` format). Serialize as `month.strftime("%Y-%m")` in the service layer.
**Warning signs:** Chart showing 13 months in a year, or off-by-one month boundaries.

### Pitfall 3: @dnd-kit/sortable requires stable string/number IDs
**What goes wrong:** Using array indices as drag IDs causes incorrect reorder behavior.
**Why it happens:** `arrayMove` and collision detection rely on stable item identity, not position.
**How to avoid:** Use `bookmark.id` (integer PK) as the `id` prop for each `SortableContext` item. Pass `items={bookmarks.map(b => b.id)}`.
**Warning signs:** Bookmarks teleport to wrong positions after drag.

### Pitfall 4: sort_order gaps after delete
**What goes wrong:** After deleting a bookmark, sort_order has gaps (e.g. 0, 2, 4). After reorder, a PATCH sends the new array order, and the backend must re-number sort_order from 0.
**Why it happens:** sort_order is an explicit integer, not derived from position.
**How to avoid:** On every reorder PATCH, send the full ordered list of IDs and re-assign sort_order 0..N in the repository. Don't try to increment/decrement individual rows.
**Warning signs:** Bookmark order changes unexpectedly after a delete followed by a new import.

### Pitfall 5: Recharts `connectNulls` and undefined vs null
**What goes wrong:** Recharts treats `null` as a gap and `undefined` as a gap, but `0` as a data point. If months with no games accidentally get `win_rate: 0` instead of `undefined`, lines won't gap.
**Why it happens:** Python→JSON serialization of absent months.
**How to avoid:** Build the monthly data structure in the service explicitly: only include months that have at least one game. The frontend merges all bookmarks' month arrays and uses `undefined` for a bookmark's missing months.
**Warning signs:** Line drops to 0% for months with no games instead of showing a gap.

### Pitfall 6: Inline label edit blur race condition
**What goes wrong:** User clicks [Load] or [✕] while a label input is focused — the blur fires the save API call, then the navigation fires, causing a spurious mutation.
**Why it happens:** `onBlur` fires before `onClick` completes.
**How to avoid:** Use `onMouseDown` + `event.preventDefault()` on action buttons to prevent blur from firing, or track a `pendingNavigation` state that cancels the save mutation.
**Warning signs:** Extra PATCH requests in network tab when clicking [Load] after editing a label.

---

## Code Examples

### Alembic Migration Pattern for Bookmark Table
```python
# Source: established project pattern (alembic/versions/)
# uv run alembic revision --autogenerate -m "add bookmarks table"
# The generated migration will use op.create_table() with BIGINT columns
# (Base.type_annotation_map maps int → BIGINT automatically)
```

### Backend: Bookmark Schema
```python
# Source: established project pattern (app/schemas/analysis.py)
from pydantic import BaseModel

class BookmarkCreate(BaseModel):
    label: str
    target_hash: int
    fen: str
    moves: list[str]         # SAN array — serialized to JSON string in model
    color: str | None = None
    match_side: str = "full"

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

class BookmarkResponse(BaseModel):
    id: int
    label: str
    target_hash: str         # Return as string to avoid JS precision loss
    fen: str
    moves: list[str]
    color: str | None
    match_side: str
    sort_order: int

    @field_serializer("target_hash")
    def serialize_hash(self, v: int) -> str:
        return str(v)

    model_config = ConfigDict(from_attributes=True)
```

### Backend: Time-Series Response Shape
```python
# Source: CONTEXT.md specifics section
# Each bookmark gets a list of monthly data points
class TimeSeriesPoint(BaseModel):
    month: str          # "2025-01"
    win_rate: float     # wins / (wins + draws + losses)
    game_count: int

class BookmarkTimeSeries(BaseModel):
    bookmark_id: int
    data: list[TimeSeriesPoint]

class TimeSeriesResponse(BaseModel):
    series: list[BookmarkTimeSeries]
```

### Frontend: TanStack Query bookmark hooks
```typescript
// Source: established project pattern (hooks/useAnalysis.ts)
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useBookmarks() {
  return useQuery({
    queryKey: ['bookmarks'],
    queryFn: () => apiClient.get<BookmarkResponse[]>('/bookmarks').then(r => r.data),
  });
}

export function useCreateBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BookmarkCreate) =>
      apiClient.post<BookmarkResponse>('/bookmarks', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}

export function useReorderBookmarks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderedIds: number[]) =>
      apiClient.put('/bookmarks/reorder', { ids: orderedIds }).then(r => r.data),
    onMutate: async (orderedIds) => {
      await qc.cancelQueries({ queryKey: ['bookmarks'] });
      const prev = qc.getQueryData<BookmarkResponse[]>(['bookmarks']);
      // optimistic update: reorder locally
      qc.setQueryData(['bookmarks'], (old: BookmarkResponse[]) =>
        orderedIds.map(id => old.find(b => b.id === id)!).filter(Boolean)
      );
      return { prev };
    },
    onError: (_, __, ctx) => qc.setQueryData(['bookmarks'], ctx?.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-beautiful-dnd | @dnd-kit/sortable | 2025 (rbd archived) | Must use @dnd-kit; rbd peer deps reject React 19 |
| recharts v2 (shadcn default) | recharts v2.15.4+ | 2024 | v2.15.4 added React 19 peer dep; use v2, NOT v3 yet with shadcn |
| shadcn chart requires recharts v2 | shadcn chart partially broken with recharts v3 | 2025 (issue open) | Stick to recharts 2.x; v3 API changes broke shadcn ChartTooltipContent |

**Deprecated/outdated:**
- `react-beautiful-dnd`: Archived April 2025, no React 19 support. Do not use.
- `recharts@3.x` with shadcn chart: shadcn issue #7669 tracks incompatibility; community workaround exists but adds maintenance burden. Avoid until officially resolved.

---

## Open Questions

1. **[+ Add bookmark] on /bookmarks page — modal or navigation?**
   - What we know: CONTEXT.md marks this as Claude's Discretion
   - What's unclear: Neither option is specified; both require slightly different implementation
   - Recommendation: Navigate to `/` with `location.state = { mode: 'add-bookmark' }` — reuses all existing Dashboard infrastructure, avoids a separate bookmark creation form, and keeps the board visible for position verification before saving. Simpler than a modal that must replicate board state.

2. **Reorder endpoint: PATCH per item or single PUT with ordered IDs?**
   - What we know: CONTEXT.md says sort_order is stored as integer; no endpoint shape specified
   - What's unclear: Whether to PATCH individual sort_orders or send one bulk reorder
   - Recommendation: `PUT /bookmarks/reorder` with `{ ids: number[] }` — atomically reassigns sort_order 0..N-1, avoids race conditions, single DB transaction.

3. **Time-series endpoint: per-bookmark calls or single batched endpoint?**
   - What we know: CONTEXT.md says `GET /analysis/time-series` accepts bookmark params; shape shows single-bookmark response
   - What's unclear: Whether it handles multiple bookmarks in one call
   - Recommendation: Accept a list of bookmark params in one request body (POST `/analysis/time-series` with list), return `BookmarkTimeSeries[]`. Avoids N+1 HTTP calls when the page loads with many bookmarks.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/test_bookmark_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKM-01 | Bookmark CRUD (create/read/update/delete) | integration | `uv run pytest tests/test_bookmark_repository.py::TestCRUD -x` | Wave 0 |
| BKM-02 | sort_order reorder assigns 0..N-1 | integration | `uv run pytest tests/test_bookmark_repository.py::TestReorder -x` | Wave 0 |
| BKM-03 | Time-series returns correct monthly buckets | integration | `uv run pytest tests/test_analysis_repository.py::TestTimeSeries -x` | Wave 0 |
| BKM-04 | Time-series skips months with 0 games (no zero entries) | integration | `uv run pytest tests/test_analysis_repository.py::TestTimeSeries::test_gap_months -x` | Wave 0 |
| BKM-05 | Bookmark is user-scoped (user A cannot read user B's bookmarks) | integration | `uv run pytest tests/test_bookmark_repository.py::TestIsolation -x` | Wave 0 |

*Note: No formal REQUIREMENTS.md IDs were provided for this phase. IDs above are provisional for test traceability.*

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_bookmark_repository.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bookmark_repository.py` — covers BKM-01, BKM-02, BKM-05
- [ ] `tests/test_analysis_repository.py` — append `TestTimeSeries` class for BKM-03, BKM-04
- [ ] Alembic migration for `bookmarks` table (needed before any repository test can run)

---

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection: `app/models/`, `app/routers/`, `app/repositories/`, `app/services/`, `frontend/src/` — existing patterns verified
- `npm info @dnd-kit/core` + `npm info @dnd-kit/sortable` — peerDeps and versions confirmed locally
- `npm info recharts@2.15.4 peerDependencies` — React 19 explicit support confirmed locally

### Secondary (MEDIUM confidence)
- [shadcn/ui Chart docs](https://ui.shadcn.com/docs/components/chart) — installation command, ChartContainer API, multi-line example verified
- [shadcn/ui React 19 guide](https://ui.shadcn.com/docs/react-19) — recharts react-is override requirement (for recharts v2 this is NOT needed per npm peerDeps; relevant only if using v3)
- [shadcn/ui recharts v3 issue #7669](https://github.com/shadcn-ui/ui/issues/7669) — confirms shadcn chart is not yet officially v3 compatible; use v2

### Tertiary (LOW confidence)
- WebSearch: react-beautiful-dnd deprecation — confirmed by multiple sources including GitHub archive notice (April 2025); MEDIUM confidence
- WebSearch: @dnd-kit/react 0.x beta status — treat as informational; do not use beta package in this phase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via npm CLI on local machine; peerDep compatibility verified
- Architecture: HIGH — all patterns follow existing codebase conventions directly (router/service/repository, SQLAlchemy Base, TanStack Query, FilterState)
- Pitfalls: HIGH — BIGINT precision issue is a documented existing pattern in codebase; others derived from library documentation and codebase inspection
- Time-series SQL: MEDIUM — `func.date_trunc` is standard SQLAlchemy/PostgreSQL; not yet used in codebase but well-established

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (stable libraries; recharts v3 shadcn compat may resolve sooner)
