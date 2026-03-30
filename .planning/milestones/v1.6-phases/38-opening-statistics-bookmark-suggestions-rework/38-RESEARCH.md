# Phase 38: Opening Statistics & Bookmark Suggestions Rework - Research

**Researched:** 2026-03-29
**Domain:** React/TypeScript frontend UI rework — Opening Statistics layout, bookmark suggestion logic, bookmark card redesign. No backend schema changes.
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Section Reordering**
- Reorder the Opening Statistics sections to:
  1. Results by Opening
  2. Win Rate Over Time
  3. Most Played Openings as White (renamed from "White: Most Played Openings", with white color circle)
  4. Most Played Openings as Black (renamed from "Black: Most Played Openings", with black color circle)

**Default Chart Data (No Bookmarks)**
- If the user has NO position bookmarks, use the top 3 white and top 3 black most-played openings as data for "Results by Opening" and "Win Rate Over Time" charts
- Each opening uses its corresponding "Played as" filter (white openings use played-as-white, black openings use played-as-black) with "Piece filter: Both" and all default "more filters" settings
- Since most-played openings data is already fetched, do NOT create extra API requests — reuse the existing fetched data
- Most Played Openings data must be fetched BEFORE rendering "Results by Opening" and "Win Rate Over Time" charts (since those charts depend on it when no bookmarks exist)
- If the user has at least one position bookmark, use ONLY bookmarks for "Results by Opening" and "Win Rate Over Time" charts

**Bookmark Suggestions Rework**
- Fetch top 10 most-played openings for white and black for bookmark suggestions
- Suggest only the top 5 for each color
- If a most-played opening is already bookmarked, skip it and suggest the next one from the list
- If all 10 most-played positions (for a color) are already bookmarked, display a message suggesting the user create custom position bookmarks on the board and experiment with the Piece filter
- Remove ALL obsolete bookmark suggestion code

**Bookmark Card: Chart Enable Toggle**
- Add a toggle to each bookmark card to enable/disable including that bookmark in "Results by Opening" and "Win Rate Over Time" charts
- Default: enabled

**Bookmark Card Layout Redesign**
- Make the minimap slightly bigger
- Move load and delete buttons to a new row below the Piece filter (gains horizontal space)
- New button row layout: chart-enable toggle on left, load button in middle, delete button on right

**Position Bookmarks Popover**
- Update the explanation text in the Position Bookmarks popover
- Add explanation of the Piece filter (not what it does functionally, just that its state can be updated here)
- Add explanation of the chart-enable toggle

### Claude's Discretion
- How to implement the chart-enable toggle state (localStorage, API field, or bookmark model extension)
- Exact sizing of the bigger minimap
- Transition/animation details for toggle
- Loading state handling while most-played openings fetch is in progress

### Deferred Ideas (OUT OF SCOPE)
None — requirements cover phase scope
</user_constraints>

---

## Summary

Phase 38 is a frontend-only rework of the Opening Statistics tab and bookmark system. The key changes are:

1. **Section reordering**: Move "Results by Opening" and "Win Rate Over Time" to the top of the Statistics tab, and rename the Most Played Openings sections.
2. **Default chart data**: When no bookmarks exist, derive synthetic bookmark-like data from the top 3 most-played openings per color and feed it into the existing chart components.
3. **Bookmark suggestions rework**: Replace the existing Zobrist-hash-based suggestion backend with a purely frontend logic that filters `mostPlayedData` against the current bookmarks list.
4. **Chart-enable toggle on bookmark cards**: A per-bookmark toggle that controls whether the bookmark is included in "Results by Opening" and "Win Rate Over Time". State must be persisted across sessions.

The most architecturally interesting decision is the chart-enable toggle storage. The most natural implementation that preserves the existing pattern is **localStorage** (purely frontend, no backend schema migration, no new API endpoint). Alternatively, adding a `chart_enabled` boolean column to the `position_bookmarks` DB table and API is robust but requires a migration. Given the scope, localStorage is the right call for this phase.

**Primary recommendation:** Implement everything in the frontend. Use localStorage for chart-enable toggle state. Reuse `mostPlayedData` already fetched in `Openings.tsx` for both the default chart logic and the new SuggestionsModal — no new API calls needed.

---

## Standard Stack

### Core (all already in the project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19 | UI framework | Project standard |
| TypeScript | 5.x | Type safety | Project standard |
| TanStack Query | 5.x | Server state | Already used for `useMostPlayedOpenings`, `usePositionBookmarks` |
| Tailwind CSS | 3.x | Styling | Project standard |
| lucide-react | — | Icon set | Already used (Upload, Trash2, Sparkles, ChevronUp, etc.) |
| @dnd-kit/sortable | — | Drag-to-reorder | Already used in PositionBookmarkList |

**Installation:** No new packages needed — this phase uses only what is already installed.

---

## Architecture Patterns

### Existing statisticsContent Structure (current)

```
statisticsContent (in Openings.tsx, lines 523-652):
  1. White: Most Played Openings  (mostPlayedData.white)
  2. Black: Most Played Openings  (mostPlayedData.black)
  3. [empty state OR bookmarks charts]
     - Results by Opening          (tsData + bookmarks)
     - Win Rate Over Time          (tsData + bookmarks)
```

### Target statisticsContent Structure (Phase 38)

```
statisticsContent:
  1. Results by Opening            (bookmarks OR top-3 derived from mostPlayedData)
  2. Win Rate Over Time            (bookmarks OR top-3 derived from mostPlayedData)
  3. Most Played Openings as White (renamed, mostPlayedData.white)
  4. Most Played Openings as Black (renamed, mostPlayedData.black)
```

### Pattern 1: Default Chart Data from Most-Played Openings

The `OpeningWDL` type (from `frontend/src/types/stats.ts`) already has all fields needed to
build a "synthetic bookmark" for the charts: `fen`, `opening_name`, `opening_eco`, WDL stats.

The challenge is that `ResultsByOpening` and `WinRateChart` consume data keyed by `bookmark_id`.
The clean approach is to derive a synthetic `PositionBookmark`-shaped array from `mostPlayedData`
when `bookmarks.length === 0`, then feed it to the same chart rendering code.

**Synthetic bookmark derivation** (when no bookmarks exist):
```typescript
// Top 3 white + top 3 black from mostPlayedData
const DEFAULT_CHART_LIMIT = 3;

const defaultChartBookmarks: PositionBookmarkResponse[] = useMemo(() => {
  if (bookmarks.length > 0 || !mostPlayedData) return [];
  const white = mostPlayedData.white.slice(0, DEFAULT_CHART_LIMIT).map((o, i) => ({
    id: -(i + 1),                    // negative ID to avoid collision with real bookmarks
    label: o.label,
    target_hash: '0',                // not used for chart lookup
    fen: o.fen,
    moves: [],
    color: 'white' as const,
    match_side: 'both' as const,
    is_flipped: false,
    sort_order: i,
    chart_enabled: true,
  }));
  const black = mostPlayedData.black.slice(0, DEFAULT_CHART_LIMIT).map((o, i) => ({
    id: -(DEFAULT_CHART_LIMIT + i + 1),
    label: o.label,
    target_hash: '0',
    fen: o.fen,
    moves: [],
    color: 'black' as const,
    match_side: 'both' as const,
    is_flipped: false,
    sort_order: DEFAULT_CHART_LIMIT + i,
    chart_enabled: true,
  }));
  return [...white, ...black];
}, [bookmarks, mostPlayedData]);
```

However: `WinRateChart` needs a `BookmarkTimeSeries[]` response from the time-series API, which
requires real bookmark IDs sent to the backend. Synthetic bookmarks (with negative IDs) cannot
be fetched from the time-series endpoint.

**Key insight on WinRateChart with default data**: The time-series endpoint (`/api/analysis/time-series`)
receives `target_hash` and `match_side` per bookmark — not the ID. The backend joins on `target_hash`,
not on `bookmark_id`. So synthetic bookmarks CAN be sent to the time-series API as long as we construct
a valid `TimeSeriesRequest` using the real Zobrist hashes from the opening FEN.

The FEN is available in `OpeningWDL.fen` (from the `openings_dedup` view, which stores the position FEN).
The Zobrist hash must be computed from FEN. Since the frontend doesn't compute Zobrist hashes, we need
a different approach:

**Recommended approach for WinRateChart default data:**
- Compute `target_hash` client-side using the `fen` from `OpeningWDL`. The Zobrist hash computation
  is in `app/services/zobrist.py` on the backend. There is no existing frontend Zobrist utility.
- **Alternative (simpler)**: Add a `full_hash` field to `OpeningWDL` in the backend response so the
  frontend can use it directly. This avoids reimplementing Zobrist in TypeScript.
- **Even simpler alternative**: Use the existing `/api/analysis/time-series` endpoint by passing
  synthetic bookmark entries with `target_hash` derived from the backend-provided `OpeningWDL.fen`
  ... but this requires the hash.

**Recommended resolution**: Add `full_hash` (as a string) to `OpeningWDL` schema and the
`query_top_openings_sql_wdl` SQL query. The `fen` is already available in `openings_dedup`;
the full hash can be computed server-side via `compute_hashes(chess.Board(fen))[2]`.

Wait — re-reading the requirements: *"Since most-played openings data is already fetched, do NOT
create extra API requests — reuse the existing fetched data."* This constraint applies to NOT making
additional API calls to fetch the data. It does not prevent adding a `full_hash` field to the
existing response. A backend schema change to add `full_hash` to `OpeningWDL` response is minimal
and aligns with "reuse existing fetched data."

**Recommended for WinRateChart default data**: Add `full_hash: string` to `OpeningWDL` backend
schema and compute it server-side. Frontend derives `TimeSeriesRequest` from `mostPlayedData`
using the included hashes. No extra API calls.

### Pattern 2: Chart-Enable Toggle — localStorage Implementation

Since the bookmark model has no `chart_enabled` column, and the CONTEXT.md leaves the
implementation to Claude's discretion, localStorage is the cleanest approach for this phase:

```typescript
// Key: `bookmark-chart-enabled-${bookmark.id}`
// Value: "true" | "false" (default: "true" — enabled by default)

function getChartEnabled(bookmarkId: number): boolean {
  const stored = localStorage.getItem(`bookmark-chart-enabled-${bookmarkId}`);
  return stored === null ? true : stored === 'true';
}

function setChartEnabled(bookmarkId: number, enabled: boolean): void {
  localStorage.setItem(`bookmark-chart-enabled-${bookmarkId}`, String(enabled));
}
```

A custom hook `useBookmarkChartEnabled(bookmarkId)` returning `[enabled, setEnabled]` makes
this testable and reusable.

**Why localStorage over DB field:**
- No backend migration, no new API endpoint, no schema change
- Correct behavior: toggle state is per-browser (not shared across devices), which is fine for
  a display preference
- Consistent with how similar display preferences are handled in most React apps
- Drawback: state is lost when clearing localStorage or using a different browser — acceptable
  for a display toggle

**Filtering in the parent component**: `Openings.tsx` filters `bookmarks` through chart-enabled
state before constructing `timeSeriesRequest` and the "Results by Opening" rows:

```typescript
const chartEnabledMap = useMemo(() => {
  const map: Record<number, boolean> = {};
  for (const b of bookmarks) {
    map[b.id] = getChartEnabled(b.id);
  }
  return map;
}, [bookmarks]);

const chartBookmarks = useMemo(
  () => bookmarks.filter(b => chartEnabledMap[b.id] !== false),
  [bookmarks, chartEnabledMap]
);
```

Then `timeSeriesRequest` uses `chartBookmarks` instead of `bookmarks`.

### Pattern 3: Bookmark Suggestions Rework

The existing `SuggestionsModal` calls `/api/position-bookmarks/suggestions` which runs the
complex Zobrist-hash-based suggestion logic in the backend. The new approach replaces the
backend call entirely with client-side filtering of `mostPlayedData`.

**New flow:**
1. Parent (`Openings.tsx`) passes `mostPlayedData` and `bookmarks` to `SuggestionsModal`
2. `SuggestionsModal` filters `mostPlayedData.white/black` against existing bookmarks
3. No call to `/api/position-bookmarks/suggestions`

**Deduplication**: Matching against existing bookmarks requires comparing the position.
`OpeningWDL` has `fen` — bookmarks also have `fen`. An exact FEN string match is the simplest
deduplication. However, bookmark's `target_hash` is more reliable (handles different FEN
representations of the same position). Since `OpeningWDL.fen` comes from `openings_dedup` and
matches the FEN stored in the bookmark when using the same opening, FEN comparison is sufficient.

If `full_hash` is added to `OpeningWDL` (per Pattern 1 recommendation), hash comparison is
more robust. The SuggestionsModal can compare `opening.full_hash` against bookmark `target_hash`
values where `match_side === 'both'`.

**Fallback message** when all 10 most-played are already bookmarked:
> "All your most-played openings are already bookmarked. Try creating custom bookmarks on the board and experimenting with the Piece filter."

**Props for new SuggestionsModal:**
```typescript
interface SuggestionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mostPlayedData: MostPlayedOpeningsResponse | undefined;
  bookmarks: PositionBookmarkResponse[];
}
```

**Saving**: When saving a selected suggestion, create a bookmark via the existing
`positionBookmarksApi.create()` call. The `target_hash` for a "Both" bookmark is the
`full_hash` of the opening's position (must come from `OpeningWDL.full_hash`).

### Pattern 4: Bookmark Card Layout Redesign

Current layout (3-column flex):
```
[drag handle] [mini-board 60px] [label + piece filter toggle] [load btn / delete btn (stacked)]
```

New layout (2-row within card):
```
Row 1: [drag handle] [mini-board ~72px] [label + piece filter toggle]
Row 2 (button row below piece filter, spanning label column):
        [chart-enable toggle | LEFT] [load btn | CENTER] [delete btn | RIGHT]
```

Mini-board size: increase from `size={60}` to `size={72}` (20% larger, still compact).

The chart-enable toggle uses a Shadcn/ui `Switch` component (already in project for other uses,
or use a `Button` with active styling). Prefer `Switch` for semantic correctness of an
enable/disable toggle.

### Anti-Patterns to Avoid

- **Calling the suggestions API**: The new SuggestionsModal must NOT call
  `/api/position-bookmarks/suggestions`. Remove `usePositionSuggestions` hook usage entirely.
- **Creating a new `useMostPlayedOpenings` call in SuggestionsModal**: Pass `mostPlayedData`
  as a prop from the parent — it is already fetched there. Do not duplicate the fetch.
- **Blocking chart render waiting for time-series when using default data**: When
  `bookmarks.length === 0`, we still need a `TimeSeriesRequest` built from the synthetic entries.
  The render should show a loading state while this is in progress, not skip the charts.
- **Hardcoding color values in new UI elements**: All toggle colors (active/inactive states)
  that have semantic meaning must be routed through `theme.ts` per CLAUDE.md.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toggle on/off UI | Custom styled div | Shadcn `Switch` component | Accessible, keyboard-navigable, consistent with design system |
| Drag sorting | Custom drag impl | @dnd-kit (already in use) | Already wired in PositionBookmarkList |
| Persistent toggle state | Session state (lost on refresh) | localStorage | Survives page reload; appropriate for display preferences |
| Opening hash computation in frontend | Reimplementing Zobrist in TypeScript | Add `full_hash` to `OpeningWDL` backend response | Single source of truth; avoids hash sync bugs |

---

## Common Pitfalls

### Pitfall 1: WinRateChart with Default Data — Missing `full_hash`

**What goes wrong:** `OpeningWDL` has `fen` but not `full_hash`. Building a `TimeSeriesRequest`
for default chart data requires a Zobrist hash, which isn't available in the frontend.
**Why it happens:** The existing `MostPlayedOpeningsResponse` was designed for display only
(showing WDL stats), not for feeding the time-series endpoint.
**How to avoid:** Add `full_hash: str` to `OpeningWDL` Pydantic schema and compute it server-side
using `compute_hashes(chess.Board(fen))[2]` in `stats_service.py`.
**Warning signs:** If you try to implement default WinRateChart data without a hash, you'll find
there's no way to build the `target_hash` field for the `TimeSeriesRequest`.

### Pitfall 2: Chart-Enable Toggle — Stale State After Bookmark Delete

**What goes wrong:** When a bookmark is deleted, its localStorage key remains. If a new bookmark
is later created that gets the same ID (PostgreSQL sequences do not reuse IDs in practice, but the
risk exists), the old toggle state could be applied incorrectly.
**Why it happens:** localStorage keys are keyed by bookmark ID (`bookmark-chart-enabled-${id}`).
**How to avoid:** On bookmark delete, call `localStorage.removeItem('bookmark-chart-enabled-${id}')`.
The `useDeletePositionBookmark` mutation's `onMutate` or `onSuccess` is the right place.

### Pitfall 3: `usePositionSuggestions` Hook — Dead Code Risk

**What goes wrong:** The old `usePositionSuggestions` hook in `usePositionBookmarks.ts` and the
`getSuggestions` API call in `client.ts` become dead code after the rework. Leaving them creates
confusion and the backend endpoint stays alive.
**Why it happens:** Partial refactors that change the call site but not the definitions.
**How to avoid:** Remove `usePositionSuggestions` from `usePositionBookmarks.ts`, remove
`getSuggestions` from `client.ts`, remove `PositionSuggestion`/`SuggestionsResponse` from
`types/position_bookmarks.ts`, and delete or simplify the backend `/position-bookmarks/suggestions`
endpoint (or leave the backend endpoint in place since removing it is not required, but remove all
frontend dead code).

### Pitfall 4: Section Reorder — Mobile Layout Duplication

**What goes wrong:** `Openings.tsx` has both a desktop and mobile layout. The `statisticsContent`
variable is shared — but if the Statistics tab ever has mobile-specific markup, it must be updated
in both places.
**Why it happens:** CLAUDE.md requires checking both desktop and mobile variants.
**How to avoid:** Verify that `statisticsContent` is shared between both layouts (it is, as a
single `const statisticsContent = ...` used in both `<TabsContent value="compare">` blocks).
A single reorder edit covers both layouts in this case.

### Pitfall 5: Default Chart Data — Loading State Race Condition

**What goes wrong:** `mostPlayedData` is loaded asynchronously. If `bookmarks.length === 0` and
`mostPlayedData` is still `undefined` (loading), the charts must not render in a broken state.
**Why it happens:** The dependency chain: charts depend on mostPlayedData when no bookmarks exist,
but mostPlayedData fetches in parallel with the page load.
**How to avoid:** Show a loading skeleton / spinner for the charts while `mostPlayedData` is
`undefined` AND `bookmarks.length === 0`. Once `mostPlayedData` arrives, render the charts.

### Pitfall 6: Bookmark Suggestion Matching — FEN vs Hash

**What goes wrong:** Matching opening suggestions against existing bookmarks by FEN string may fail
if the FEN in `OpeningWDL` differs from the FEN stored in the bookmark (e.g., en passant square
or castling rights differ, though `board_fen()` vs `fen()` distinctions were already handled
at import time via `compute_hashes`).
**Why it happens:** `openings_dedup.fen` comes from the openings reference table (seeded from TSV,
computed via python-chess's `board.fen()` which includes castling/en passant). Bookmark `fen` is
stored from the board at bookmark creation time (also full FEN). For opening positions these should
match, but subtle differences are possible.
**How to avoid:** If `full_hash` is added to `OpeningWDL`, use hash comparison instead of FEN
string comparison for deduplication in SuggestionsModal. This is more robust and is already the
reason we recommend adding `full_hash`.

---

## Code Examples

### Verified: Existing OpeningWDL response structure
```typescript
// Source: frontend/src/types/stats.ts
export interface OpeningWDL {
  opening_eco: string;
  opening_name: string;
  label: string;
  pgn: string;
  fen: string;
  wins: number; draws: number; losses: number; total: number;
  win_pct: number; draw_pct: number; loss_pct: number;
}
```

Field `full_hash` does not exist yet — must be added in `app/schemas/stats.py` and
`app/services/stats_service.py`.

### Verified: Existing timeSeriesRequest construction (Openings.tsx lines 152-168)
```typescript
const timeSeriesRequest: TimeSeriesRequest | null = useMemo(() => {
  if (bookmarks.length === 0) return null;
  return {
    bookmarks: bookmarks.map((b) => ({
      bookmark_id: b.id,
      target_hash: b.target_hash,
      match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
      color: b.color,
    })),
    // ...filters
  };
}, [bookmarks, debouncedFilters]);
```

For default chart data (no bookmarks), a parallel request is built from `mostPlayedData` slices
using `full_hash` from `OpeningWDL`. The `bookmark_id` field in `TimeSeriesBookmarkParam` is a
frontend label used to match series back to display labels — synthetic negative IDs work fine here
since the backend only uses `target_hash` and `match_side` for the query.

### Verified: Backend stats_service rows_to_openings (stats_service.py line 213)
```python
# Currently does NOT include full_hash — must be added
for eco, name, pgn, fen, total, wins, draws, losses in rows:
    # Add full_hash computation:
    import chess as chess_lib
    from app.services.zobrist import compute_hashes
    board = chess_lib.Board(fen)
    _, _, full_hash = compute_hashes(board)
```

And the SQL query in `stats_repository.py` does not need to change — `full_hash` is computed
from the `fen` field that's already returned.

### Verified: Bookmark card current DOM structure (PositionBookmarkCard.tsx lines 76-198)
Current: `[drag handle] [mini-board 60px] [flex-col: label + piece-filter] [flex-col: load + delete]`

New target:
```tsx
<div className="flex items-start gap-2 ...">
  <span {...listeners}>☰</span>           {/* drag handle */}
  <MiniBoard size={72} ... />              {/* larger minimap */}
  <div className="flex-1 flex flex-col gap-1">
    {/* label row */}
    {/* piece filter toggle */}
    {/* NEW: button row */}
    <div className="flex items-center justify-between">
      <Switch checked={chartEnabled} onCheckedChange={setChartEnabled}
              aria-label="Include in charts" data-testid={`bookmark-chart-toggle-${id}`} />
      <Button onClick={handleLoad} ...>Load</Button>
      <Button onClick={handleDelete} ...>Delete</Button>
    </div>
  </div>
</div>
```

---

## Backend Changes Required

This phase was stated as "No backend schema changes expected" in CONTEXT.md. However, research
reveals one minimal backend addition is needed:

**`full_hash` field on `OpeningWDL`**: Required to enable the SuggestionsModal to save bookmarks
with correct `target_hash`, and to enable WinRateChart default data without a new API call.

| Change | File | Impact |
|--------|------|--------|
| Add `full_hash: str` to `OpeningWDL` Pydantic schema | `app/schemas/stats.py` | Non-breaking (additive) |
| Compute and include `full_hash` in `rows_to_openings()` | `app/services/stats_service.py` | Non-breaking |
| Add `full_hash: string` to `OpeningWDL` TypeScript interface | `frontend/src/types/stats.ts` | Non-breaking |

No DB migration needed. No new endpoints. No schema changes to `position_bookmarks` table.

---

## Validation Architecture

nyquist_validation is enabled per config.json.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), Vitest (frontend) |
| Config file | `pyproject.toml` (backend), `vite.config.ts` (frontend) |
| Quick run command | `uv run pytest tests/test_bookmark_repository.py tests/test_stats_router.py -x` |
| Full suite command | `uv run pytest && npm test` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `full_hash` included in MostPlayedOpenings response | integration | `uv run pytest tests/test_stats_router.py -x -k most_played` | Exists (test_stats_router.py) |
| Default chart bookmarks derived from mostPlayedData when no bookmarks | unit/manual | Manual verification in browser | N/A (UI logic) |
| Suggestion filtering skips already-bookmarked openings | unit | Frontend test or manual | N/A (no frontend unit test yet) |
| Chart-enable toggle persists across page reload | manual | Manual browser verification | N/A |
| Bookmark card layout: buttons in new row | visual | Browser + screenshot | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_stats_router.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- No new test files required — the single backend change (`full_hash` in response) is covered by
  the existing `test_stats_router.py` (add one assertion for the new field).

---

## Environment Availability

Step 2.6: SKIPPED — this phase is primarily frontend code changes with one minimal backend schema
addition. No new external tools, CLIs, or services are required beyond the existing stack.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — all source file reads above

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions (Phase 38, gathered 2026-03-29)
- STATE.md accumulated decisions for Phases 36-37

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing; no new dependencies
- Architecture: HIGH — codebase thoroughly read; patterns are clear
- Pitfalls: HIGH — identified from direct code analysis, not speculation
- Backend `full_hash` addition: HIGH — straightforward addition to existing service

**Research date:** 2026-03-29
**Valid until:** Indefinite for stable internal codebase; refresh if Phase 37 implementation
details change before this phase executes.
