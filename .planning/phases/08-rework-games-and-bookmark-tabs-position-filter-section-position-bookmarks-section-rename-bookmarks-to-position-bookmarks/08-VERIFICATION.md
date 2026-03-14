---
phase: 08-rework-games-and-bookmark-tabs
verified: 2026-03-14T00:00:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
human_verification:
  - test: "Verify collapsible sections open/close visually"
    expected: "Position filter starts open, Position bookmarks and More filters start collapsed. Clicking headers toggles them."
    why_human: "CSS/animation behavior cannot be verified statically."
  - test: "Verify drag-and-drop bookmark reordering"
    expected: "Dragging a bookmark card reorders it and the new order persists after page reload."
    why_human: "Interactive DnD behavior requires a browser."
  - test: "Verify Bookmark Load replays moves in-place"
    expected: "Clicking Load on a bookmark card updates the board to the bookmarked position without any page navigation."
    why_human: "Runtime board state and navigation behavior cannot be verified statically."
---

# Phase 8: Rework Games and Bookmark Tabs — Verification Report

**Phase Goal:** Rework Games and Bookmark tabs — rename bookmarks to position bookmarks, restructure Dashboard with collapsible position filter / position bookmarks / more filters sections, simplify bookmark cards, remove standalone Bookmarks page.
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DB table is `position_bookmarks`, all CRUD at `/position-bookmarks` paths | VERIFIED | `app/models/position_bookmark.py` has `__tablename__ = "position_bookmarks"`; router declares GET/POST/PUT/DELETE at `/position-bookmarks` paths; migration `7eb7ce83cdb9` uses `op.rename_table` |
| 2 | Alembic migration is zero-data-loss (rename, not drop+create) | VERIFIED | Migration uses `op.rename_table('bookmarks', 'position_bookmarks')` + `ALTER INDEX ... RENAME TO`; downgrade reverses in correct order |
| 3 | All old backend bookmark files are deleted; no stale imports remain | VERIFIED | `bookmark.py`, `bookmark_repository.py`, `bookmarks.py` (schemas + router) all gone; `grep` for `from app.models.bookmark` / `from app.schemas.bookmarks` / `from app.repositories.bookmark_repository` returns nothing |
| 4 | Frontend types, hooks, API client all reference `position-bookmarks` | VERIFIED | `position_bookmarks.ts` exports `PositionBookmarkResponse/Create/Update/ReorderRequest`; `usePositionBookmarks.ts` uses `['position-bookmarks']` query key; `positionBookmarksApi` in `client.ts` calls `/position-bookmarks` paths; old `bookmarks.ts`, `useBookmarks.ts` deleted |
| 5 | PositionBookmarkCard has no MiniBoard and no WDL bar | VERIFIED | No imports for `MiniBoard`, `WDLBar`, `useNavigate` in `PositionBookmarkCard.tsx`; card renders drag handle + editable label + Load button + Delete button only |
| 6 | PositionBookmarkList accepts `onLoad` callback instead of `wdlStatsMap` | VERIFIED | `PositionBookmarkList` props: `{ bookmarks, onReorder, onLoad }`; no `wdlStatsMap` prop present |
| 7 | WinRateChart and WDLBarChart live in `components/charts/` | VERIFIED | Both files confirmed at `frontend/src/components/charts/WinRateChart.tsx` and `WDLBarChart.tsx`; old `components/bookmarks/` directory is gone |
| 8 | Dashboard left column has three collapsible sections with correct defaults | VERIFIED | `positionFilterOpen` initialized `true`, `positionBookmarksOpen` and `moreFiltersOpen` initialized `false`; three `<Collapsible>` blocks with `data-testid` `section-position-filter`, `section-position-bookmarks`, `section-more-filters` |
| 9 | "Bookmark this position" button is inside the Position filter section | VERIFIED | `btn-bookmark` button with text "Bookmark this position" appears at Dashboard.tsx lines 299–307, inside the first `<CollapsibleContent>` (Position filter section, lines 225–311) |
| 10 | Filter and Import buttons are always visible below all three collapsibles | VERIFIED | Always-visible button row at Dashboard.tsx lines 364–379, outside all three `<Collapsible>` blocks |
| 11 | Loading a bookmark calls `chess.loadMoves()` in-place | VERIFIED | `handleLoadBookmark` at Dashboard.tsx line 166–170 calls `chess.loadMoves(bkm.moves)`, sets `boardFlipped`, and updates filters; wired to `PositionBookmarkList` via `onLoad={handleLoadBookmark}` at line 336 |
| 12 | Navigation has 4 tabs (Games, Openings, Rating, Global Stats); Bookmarks page and `/bookmarks` route removed | VERIFIED | `NAV_ITEMS` in `App.tsx` has exactly 4 entries; no Bookmarks import, no `/bookmarks` route; `Bookmarks.tsx` deleted from `frontend/src/pages/` |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/7eb7ce83cdb9_rename_bookmarks_to_position_bookmarks.py` | Table rename migration | VERIFIED | Uses `op.rename_table` + `ALTER INDEX ... RENAME TO`; downgrade reverses correctly |
| `app/models/position_bookmark.py` | PositionBookmark ORM model | VERIFIED | `class PositionBookmark(Base)` with `__tablename__ = "position_bookmarks"` |
| `app/repositories/position_bookmark_repository.py` | PositionBookmark repository | VERIFIED | Full CRUD + reorder functions; `PositionBookmarkRepository` alias present |
| `app/schemas/position_bookmarks.py` | Pydantic schemas | VERIFIED | Exports `PositionBookmarkCreate`, `PositionBookmarkUpdate`, `PositionBookmarkResponse`, `PositionBookmarkReorderRequest` |
| `app/routers/position_bookmarks.py` | Position bookmarks router | VERIFIED | All paths use `/position-bookmarks`; `reorder` route defined before `/{bookmark_id}` |
| `frontend/src/types/position_bookmarks.ts` | Renamed TS types | VERIFIED | Exports `PositionBookmarkResponse`, `PositionBookmarkCreate`, `PositionBookmarkUpdate` |
| `frontend/src/hooks/usePositionBookmarks.ts` | Renamed hooks | VERIFIED | Exports `usePositionBookmarks`, `useCreatePositionBookmark`, `useDeletePositionBookmark`, `useReorderPositionBookmarks`, `useTimeSeries` |
| `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` | Simplified bookmark card | VERIFIED | No MiniBoard, no WDL bar; drag handle + editable label + Load + Delete |
| `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` | DnD list with onLoad | VERIFIED | Props include `onLoad`; no `wdlStatsMap` |
| `frontend/src/components/charts/WinRateChart.tsx` | Relocated chart component | VERIFIED | Present in `components/charts/`; uses `PositionBookmarkResponse` from `@/types/position_bookmarks` |
| `frontend/src/components/charts/WDLBarChart.tsx` | Relocated chart component | VERIFIED | Present in `components/charts/`; uses `PositionBookmarkResponse` from `@/types/position_bookmarks` |
| `frontend/src/pages/Dashboard.tsx` | Restructured three-section layout | VERIFIED | Three `<Collapsible>` sections; `handleLoadBookmark` wired; always-visible buttons below |
| `frontend/src/App.tsx` | Updated routes and nav (4 tabs) | VERIFIED | 4 `NAV_ITEMS`; no Bookmarks route; no Bookmarks import |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/main.py` | `app/routers/position_bookmarks.py` | `include_router` | WIRED | `from app.routers import analysis, position_bookmarks, imports, auth` + `app.include_router(position_bookmarks.router)` |
| `app/routers/position_bookmarks.py` | `app/repositories/position_bookmark_repository.py` | repository import | WIRED | `from app.repositories import position_bookmark_repository` used in all route handlers |
| `frontend/src/api/client.ts` | `/position-bookmarks` | API path strings | WIRED | All five operations (list, create, updateLabel, remove, reorder) call `/position-bookmarks` paths |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/charts/WinRateChart.tsx` | import | WIRED | `import { WinRateChart } from '@/components/charts/WinRateChart'`; rendered in JSX |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/charts/WDLBarChart.tsx` | import | WIRED | `import { WDLBarChart } from '@/components/charts/WDLBarChart'`; rendered in JSX |
| `frontend/src/pages/Openings.tsx` | `frontend/src/hooks/usePositionBookmarks.ts` | import | WIRED | `import { usePositionBookmarks, useTimeSeries } from '@/hooks/usePositionBookmarks'` |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` | import + render | WIRED | `import { PositionBookmarkList }` + rendered inside Position bookmarks collapsible with `onLoad={handleLoadBookmark}` |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/hooks/usePositionBookmarks.ts` | import | WIRED | `usePositionBookmarks`, `useCreatePositionBookmark`, `useReorderPositionBookmarks` all imported and used |
| `frontend/src/pages/Dashboard.tsx` | `chess.loadMoves` | `handleLoadBookmark` callback | WIRED | `handleLoadBookmark` calls `chess.loadMoves(bkm.moves)` then sets `boardFlipped` and `filters` |
| `frontend/vite.config.ts` | backend at `localhost:8000` | proxy entry `/position-bookmarks` | WIRED | Proxy entry `'/position-bookmarks': 'http://localhost:8000'` present; old `/bookmarks` entry gone |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REWORK-01 | 08-01, 08-02 | Rename bookmarks to position_bookmarks across DB, backend, frontend | SATISFIED | Migration, model, schemas, router, types, hooks, API client all renamed; old files deleted; no stale references |
| REWORK-02 | 08-03 | Dashboard left column: three collapsible sections (Position filter open, Position bookmarks collapsed, More filters collapsed) with always-visible Filter + Import buttons | SATISFIED | Three `<Collapsible>` with correct defaults; always-visible button row outside all collapsibles |
| REWORK-03 | 08-03 | Remove dedicated Bookmarks page and navigation tab (5 to 4 tabs) | SATISFIED | `Bookmarks.tsx` deleted; `NAV_ITEMS` has 4 entries; no `/bookmarks` route in `App.tsx` |
| REWORK-04 | 08-02 | Remove WDL bars and WinRateChart from bookmark cards; relocate charts to `components/charts/` | SATISFIED | `PositionBookmarkCard` has no MiniBoard/WDL; `WinRateChart` and `WDLBarChart` in `components/charts/` |
| REWORK-05 | 08-03 | Move "Bookmark this position" button into Position filter collapsible section | SATISFIED | Button at lines 299–307 in Dashboard.tsx, inside Position filter `<CollapsibleContent>` |

All 5 REWORK requirements satisfied. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/Dashboard.tsx` | 482 | `placeholder="Bookmark label"` | Info | HTML input placeholder attribute — not a code stub; this is correct usage in the bookmark label dialog |

No blocking or warning anti-patterns found. The `placeholder` attribute is legitimate HTML — not a code placeholder.

### Human Verification Required

#### 1. Collapsible section visual behavior

**Test:** Open the Games page. Verify Position filter is expanded by default, Position bookmarks and More filters are collapsed by default. Click each section header to toggle them.
**Expected:** Each section toggles smoothly. Chevron icons change direction. Board + controls visible in Position filter. BookmarkList (or empty state) visible in Position bookmarks. Secondary filter controls visible in More filters.
**Why human:** CSS transitions and Radix UI collapsible animations cannot be verified statically.

#### 2. Drag-and-drop bookmark reordering

**Test:** Create at least 2 position bookmarks on the Games page. Expand Position bookmarks. Drag a card to a new position using the drag handle.
**Expected:** Card reorders immediately (optimistic update). After release, new order persists. Page reload shows the same order.
**Why human:** Interactive DnD with @dnd-kit requires a browser.

#### 3. In-place bookmark Load

**Test:** Create a bookmark with some moves played. Navigate to the starting position (reset). Expand Position bookmarks. Click Load on a bookmark.
**Expected:** Board updates to the bookmarked position in-place; no page navigation occurs; move list updates; Played as and Match side filters update to the bookmarked values.
**Why human:** Runtime board state and navigation behavior cannot be verified statically.

### Gaps Summary

No gaps found. All 12 observable truths are verified, all 5 REWORK requirements are satisfied, all key links are wired, and no blocking anti-patterns were detected.

The three items flagged for human verification are standard interactive UI behaviors (animations, DnD, board state) that cannot be checked statically. Automated checks passed fully.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
