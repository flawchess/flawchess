# Phase 39: Mobile Opening Explorer Sidebars for Filters and Bookmarks - Research

**Researched:** 2026-03-30
**Domain:** React/TypeScript frontend — Vaul drawer, mobile layout, deferred state management
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Board Action Bar Compacting**
- D-01: Reduce all mobile board action buttons from `h-11 w-11` to `h-9 w-9` on mobile
- D-02: Sidebar trigger buttons placed **below and outside** BoardControls, not inside it
- D-03: Sidebar trigger buttons are visually distinct via style alone — no divider line

**Sidebar Component**
- D-04: Use existing Vaul-based Drawer component with `direction="right"` for both sidebars
- D-05: Both sidebars slide from right; only one open at a time
- D-06: DrawerHeader + DrawerTitle ("Filters" or "Position Bookmarks"), full-width, unconstrained scroll

**Sidebar Trigger & Layout**
- D-07: Remove existing mobile collapsibles (More Filters + Position Bookmarks) entirely
- D-08: Quick filters (Played as, Piece filter) also move into the filter sidebar
- D-09: Trigger buttons show active state (brand-brown bg or filled icon) when sidebar is open

**Filter Deferred Apply**
- D-10: Mobile filter sidebar uses deferred apply: clone filters on open, commit on close
- D-11: Desktop sidebar keeps immediate apply (unchanged)
- D-12: No explicit "Apply" button — closing IS the apply action

**Bookmark Sidebar Behavior**
- D-13: Loading a bookmark closes the sidebar and applies position to board
- D-14: All existing bookmark functionality remains inside sidebar (save, suggest, drag reorder, chart toggle, label edit, delete)

### Claude's Discretion
- Exact reduced button size (h-9 vs h-8) — UI spec resolves this to `h-9 w-9`
- Icon choices for filter and bookmark trigger buttons — UI spec: SlidersHorizontal + BookMarked
- Exact highlight style for active trigger buttons — UI spec: PRIMARY_BUTTON_CLASS (brand-brown)
- Whether to add swipe-to-dismiss — Vaul supports natively, leave enabled
- Transition duration and easing — Vaul default (~300ms ease)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 39 is a pure frontend refactor of the mobile layout in `Openings.tsx`. The goal is to replace two `<Collapsible>` sections (More Filters and Position Bookmarks) and the inline quick-filter block with two Vaul-based right-side drawers triggered by a full-width button row placed below the `BoardControls` component. Desktop layout is untouched.

The existing Drawer component (`components/ui/drawer.tsx`) already supports `direction="right"` — no new component installation is required. The `FilterPanel` and `PositionBookmarkList`/`PositionBookmarkCard` components are dropped directly into the drawer content without modification. The only new behavioral logic is the deferred filter apply pattern for the filter sidebar: local filter state is cloned on open and committed to real state on close.

**Primary recommendation:** Write a self-contained `MobileFilterSidebar` component and a `MobileBookmarkSidebar` component, each accepting the props they need from `Openings.tsx`, to keep the already-large `Openings.tsx` readable. However, inline implementations inside the mobile layout block are also acceptable — the phase is scoped to a single page.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vaul | ^1.1.2 | Drawer primitive (slide-in panels) | Already installed; Drawer component wraps it |
| lucide-react | ^0.577.0 | Icons (SlidersHorizontal, BookMarked) | Project-standard icon library |
| React | 19 | Component state and event handling | Project stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @dnd-kit/core + sortable | ^10.0.0 | Drag-and-drop bookmark reorder | Already used by PositionBookmarkList — no change needed |

**No new dependencies needed for this phase.** All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure

No new files are strictly required. The implementation fits cleanly into existing files:

```
frontend/src/
├── pages/
│   └── Openings.tsx               # Mobile section refactored (lines 785-981)
├── components/
│   └── board/
│       └── BoardControls.tsx      # Button size class change only
```

Optionally extract into sub-components if Openings.tsx grows too large:
```
frontend/src/components/
├── mobile/
│   ├── MobileFilterSidebar.tsx    # Optional extraction
│   └── MobileBookmarkSidebar.tsx  # Optional extraction
```

### Pattern 1: Vaul Right-Direction Drawer

The existing `DrawerContent` in `drawer.tsx` already handles `direction="right"` via Vaul's data attribute selectors:

```typescript
// Source: frontend/src/components/ui/drawer.tsx (verified)
// direction="right" triggers these CSS rules automatically:
// data-[vaul-drawer-direction=right]:inset-y-0
// data-[vaul-drawer-direction=right]:right-0
// data-[vaul-drawer-direction=right]:w-3/4
// data-[vaul-drawer-direction=right]:rounded-l-xl
// data-[vaul-drawer-direction=right]:border-l
// data-[vaul-drawer-direction=right]:sm:max-w-sm

<Drawer open={filterSidebarOpen} onOpenChange={handleFilterSidebarClose} direction="right">
  <DrawerContent data-testid="drawer-filter-sidebar">
    <DrawerHeader>
      <DrawerTitle>Filters</DrawerTitle>
      <DrawerClose asChild>
        <Button variant="ghost" size="icon" aria-label="Close filters" data-testid="btn-close-filter-sidebar">
          <X className="h-4 w-4" />
        </Button>
      </DrawerClose>
    </DrawerHeader>
    <div className="overflow-y-auto flex-1 p-4">
      {/* Played as + Piece filter + FilterPanel */}
    </div>
  </DrawerContent>
</Drawer>
```

### Pattern 2: Deferred Filter Apply

The key behavioral pattern. Local state is a shallow clone of `FilterState`. Mutations during sidebar interaction affect only `localFilters`. On any close (overlay tap, swipe, X button), `handleFiltersChange(localFilters)` fires before `filterSidebarOpen` goes false.

```typescript
// Controlled via onOpenChange — fires on ALL close triggers (overlay, swipe, X, Escape)
const handleFilterSidebarOpenChange = (open: boolean) => {
  if (!open) {
    // Commit deferred filters before closing
    handleFiltersChange(localFilters);
  }
  setFilterSidebarOpen(open);
};

// On open: clone current filters
const openFilterSidebar = () => {
  setLocalFilters({ ...filters });
  setFilterSidebarOpen(true);
};
```

**Critical:** The `color` and `matchSide` fields that were previously handled by inline ToggleGroups (lines 840-890 of Openings.tsx) must be included in `localFilters` — they are fields on `FilterState`. `FilterPanel` receives `visibleFilters` prop; the `color` and `matchSide` fields are handled outside `FilterPanel` since that component does not render them. The mobile filter sidebar must render these two controls manually (same JSX as the removed quick-filter block) and connect them to `localFilters` instead of `filters`.

### Pattern 3: Bookmark Load Closes Sidebar

The `handleLoadBookmark` callback needs to close the sidebar. Two options:

**Option A:** Pass a `onClose` callback to the bookmark sidebar alongside `onLoad`:
```typescript
// Inside sidebar, wrap onLoad to close first
const handleLoad = (bkm: PositionBookmarkResponse) => {
  onLoad(bkm);
  setBookmarkSidebarOpen(false);
};
```

**Option B (simpler):** Manage `bookmarkSidebarOpen` state in `Openings.tsx` and pass a combined handler.

Either approach is fine. Option A keeps the sidebar self-contained.

### Pattern 4: Sidebar Trigger Button Row

The trigger row is rendered inside the `md:hidden` sticky board container, below the existing `BoardControls` + `InfoPopover` layout:

```typescript
// Source: UI-SPEC.md (verified)
// Below the flex row containing board + BoardControls:
<div className="flex gap-2 w-full" aria-label="Open filters" >
  <Button
    variant={filterSidebarOpen ? undefined : 'ghost'}
    className={`flex-1 h-11 ${filterSidebarOpen ? PRIMARY_BUTTON_CLASS : 'hover:bg-accent'}`}
    onClick={openFilterSidebar}
    data-testid="btn-open-filter-sidebar"
    aria-label="Open filters"
  >
    <SlidersHorizontal className="h-4 w-4" />
    Filters
  </Button>
  <Button
    variant={bookmarkSidebarOpen ? undefined : 'ghost'}
    className={`flex-1 h-11 ${bookmarkSidebarOpen ? PRIMARY_BUTTON_CLASS : 'hover:bg-accent'}`}
    onClick={openBookmarkSidebar}
    data-testid="btn-open-bookmark-sidebar"
    aria-label="Open bookmarks"
  >
    <BookMarked className="h-4 w-4" />
    Bookmarks
  </Button>
</div>
```

### Anti-Patterns to Avoid

- **Using DrawerTrigger instead of controlled open state:** Using `<DrawerTrigger>` bypasses the deferred filter open callback. Use controlled `open` + `onOpenChange` on `<Drawer>`.
- **Calling `handleFiltersChange` on every toggle inside the sidebar:** Defeats deferred apply. All toggles inside the filter sidebar must call `setLocalFilters`, not `handleFiltersChange`.
- **Rendering Drawer components outside `md:hidden` block:** Both drawers and the trigger row must remain inside the `md:hidden` branch. The `sm:max-w-sm` cap in `DrawerContent` already handles wider phones, so no additional guard is needed.
- **Forgetting `color` and `matchSide` in `localFilters`:** `FilterPanel` only covers 5 of 7 `FilterState` fields (the `visibleFilters` prop excludes color/matchSide). The deferred local state must be a full `FilterState` copy, and the inline Played as / Piece filter controls must write to `localFilters`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slide-in panel with overlay + focus trap + Escape | Custom modal/panel | Vaul Drawer (already installed) | Focus trapping, swipe-to-dismiss, and overlay management are non-trivial; Vaul handles all of them |
| Swipe-to-close gesture on mobile | Touch event listener | Vaul native (threshold-based swipe) | Vaul distinguishes swipe-to-close from content scroll automatically |
| Drag-and-drop bookmark reorder in sidebar | Custom DnD | PositionBookmarkList (already uses @dnd-kit) | Already implemented and tested |

**Key insight:** This phase has zero new dependencies. Every needed primitive is either already installed or built into the existing component library.

---

## Common Pitfalls

### Pitfall 1: Deferred Filter `color` Field Not Syncing Board Flip
**What goes wrong:** When the user changes "Played as" (color) inside the filter sidebar, the board orientation (`boardFlipped`) only updates when `handleFiltersChange` fires on close. This is correct per D-10 — deferred apply includes deferred board flip.
**Why it happens:** The original code calls `setBoardFlipped(color === 'black')` in the same event handler as `setFilters`. With deferred apply, this needs to happen in `handleFiltersChange` or on close.
**How to avoid:** The `handleFiltersChange` callback (line 260-263 of Openings.tsx) only calls `setFilters`. The board flip on color change must be preserved: either in a `useEffect` on `filters.color`, or in the `handleFilterSidebarOpenChange` close handler: `setBoardFlipped(localFilters.color === 'black')`.
**Warning signs:** Board stays showing the wrong color orientation after closing the filter sidebar.

### Pitfall 2: Vaul `onOpenChange` Fires Twice on Programmatic Close
**What goes wrong:** Calling `setFilterSidebarOpen(false)` programmatically (e.g., when opening the bookmark sidebar) may trigger `onOpenChange(false)` which commits deferred filters unexpectedly.
**Why it happens:** Vaul fires `onOpenChange` for any state change.
**How to avoid:** Use a single boolean `filterSidebarOpen` controlled only via `handleFilterSidebarOpenChange`. Never set `filterSidebarOpen` to false directly from other handlers — always go through `handleFilterSidebarOpenChange(false)` which commits filters, or add a guard: only commit if `filterSidebarOpen` was actually open.
**Warning signs:** Filters reset/apply at unexpected times.

### Pitfall 3: Mutual Exclusion — Opening One Sidebar While Other Is Open
**What goes wrong:** If the user somehow triggers both sidebars simultaneously, Vaul renders two overlapping drawers.
**Why it happens:** Two independent state booleans with no guard.
**How to avoid:** In `openFilterSidebar`, check `bookmarkSidebarOpen` and close it first (no deferred commit needed for bookmarks). In `openBookmarkSidebar`, check `filterSidebarOpen` and commit+close filters first. Since the trigger buttons are the only way to open sidebars, this situation only occurs if state gets into a bad state — a defensive guard is cheap.
**Warning signs:** Two overlapping drawers visible simultaneously.

### Pitfall 4: `mobileFiltersOpen` and `positionBookmarksOpen` State Variables Left Unused
**What goes wrong:** After removing the collapsibles, these state variables become dead code but TypeScript won't error.
**Why it happens:** Simple oversight.
**How to avoid:** Delete `mobileFiltersOpen`/`setMobileFiltersOpen` and `positionBookmarksOpen`/`setPositionBookmarksOpen` from Openings.tsx state. Also remove the `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` import if no longer used elsewhere on the page.
**Warning signs:** `eslint --no-unused-vars` or TypeScript `noUnusedLocals` warnings.

### Pitfall 5: Drawer Content Scroll Conflicting with Vaul Swipe
**What goes wrong:** Vertical scroll inside the sidebar triggers Vaul's swipe-to-close, closing the sidebar while the user is scrolling content.
**Why it happens:** Vaul's default behavior on `direction="right"` uses a drag threshold — horizontal drag closes, vertical scroll is passed through.
**How to avoid:** No action needed. Vaul 1.x handles this natively for directional drawers. Do not add `modal={false}` or override touch handling. Test manually by scrolling a long filter/bookmark list without triggering close.
**Warning signs:** Sidebar closes unexpectedly during vertical content scroll.

---

## Code Examples

### Verified: Existing Drawer usage (mobile nav "More" menu)

```typescript
// Source: frontend/src/components/ui/drawer.tsx (verified - production code)
// The Drawer component wraps vaul's DrawerPrimitive.Root and passes all props through.
// direction prop is forwarded directly to vaul.

<Drawer direction="right" open={open} onOpenChange={setOpen}>
  <DrawerContent>
    <DrawerHeader>
      <DrawerTitle>Title</DrawerTitle>
    </DrawerHeader>
    <div className="overflow-y-auto flex-1 p-4">
      {/* content */}
    </div>
  </DrawerContent>
</Drawer>
```

### Verified: FilterPanel interface

```typescript
// Source: frontend/src/components/filters/FilterPanel.tsx (verified)
interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  visibleFilters?: FilterField[]; // defaults to all 5 fields
}
// FilterField = 'timeControl' | 'platform' | 'rated' | 'opponent' | 'recency'
// NOTE: 'color' and 'matchSide' are NOT in FilterField — handled outside FilterPanel
```

### Verified: handleLoadBookmark signature

```typescript
// Source: frontend/src/pages/Openings.tsx line 326-331 (verified)
const handleLoadBookmark = useCallback((bkm: PositionBookmarkResponse) => {
  chess.loadMoves(bkm.moves);
  setBoardFlipped(bkm.is_flipped ?? false);
  setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: bkm.match_side }));
  window.scrollTo({ top: 0 });
}, [chess]);
// Must close bookmark sidebar after this call
```

### Verified: BoardControls button size (current)

```typescript
// Source: frontend/src/components/board/BoardControls.tsx (verified)
// Current: className="h-11 w-11 sm:h-8 sm:w-8 hover:bg-accent"
// Change to: className="h-9 w-9 sm:h-8 sm:w-8 hover:bg-accent"
// All 4 buttons get the same change; icon size h-4 w-4 stays unchanged
```

---

## Detailed Implementation Map

### Files to Modify

**1. `frontend/src/components/board/BoardControls.tsx`**
- Change `h-11 w-11` to `h-9 w-9` on all 4 buttons (Reset, Back, Forward, Flip)
- `sm:h-8 sm:w-8` remains unchanged
- Icon sizes (`h-4 w-4`) remain unchanged

**2. `frontend/src/pages/Openings.tsx`**

State additions:
```typescript
const [filterSidebarOpen, setFilterSidebarOpen] = useState(false);
const [bookmarkSidebarOpen, setBookmarkSidebarOpen] = useState(false);
const [localFilters, setLocalFilters] = useState<FilterState>(DEFAULT_FILTERS);
```

State removals:
- `mobileFiltersOpen` / `setMobileFiltersOpen`
- `positionBookmarksOpen` / `setPositionBookmarksOpen`

Import additions:
- `Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose` from `@/components/ui/drawer`
- `SlidersHorizontal, BookMarked, X` from `lucide-react`

Import removals (if not used elsewhere in the file):
- `Collapsible, CollapsibleTrigger, CollapsibleContent` from `@/components/ui/collapsible`
- `ChevronUp, ChevronDown` from `lucide-react` — check if still used (currently imported for collapsibles and also possibly for other things; verify before removing)

Mobile section changes (lines 785-981):
- Remove: Played as + Piece filter block (lines 840-890)
- Remove: `<div className="border-t border-border/40" />` (line 892)
- Remove: More filters collapsible (lines 894-915)
- Remove: Position bookmarks collapsible (lines 917-981)
- Add: Trigger button row below sticky board container
- Add: Filter sidebar Drawer (with all filter content including Played as + Piece filter)
- Add: Bookmark sidebar Drawer (with InfoPopover + Save + Suggest + PositionBookmarkList)

Board flip on filter close:
- In `handleFilterSidebarOpenChange(false)`: call `setBoardFlipped(localFilters.color === 'black')` before or alongside `handleFiltersChange(localFilters)`

### What Is NOT Changed

- Desktop sidebar layout (lines 339 onwards — the `sidebar` variable)
- `handleFiltersChange` callback (desktop still calls this directly)
- `FilterPanel` component
- `PositionBookmarkList` / `PositionBookmarkCard` components
- `BoardControls` props interface — only the internal button className changes

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely frontend code changes with no external service or CLI dependencies beyond the existing project stack.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.1 |
| Config file | none explicit — Vite auto-discovers via `vite.config.ts` |
| Quick run command | `cd frontend && npm test` |
| Full suite command | `cd frontend && npm test` |

### Phase Requirements → Test Map

This phase has no formal requirement IDs. The behavior maps to manual verification:

| Behavior | Test Type | Notes |
|----------|-----------|-------|
| Filter sidebar opens from trigger | Manual / smoke | Vitest has no DOM testing setup (no @testing-library) |
| Deferred filter apply on close | Manual | Requires interaction testing |
| Bookmark sidebar opens, load closes it | Manual | Requires interaction testing |
| BoardControls button size reduction | Visual | |
| Desktop layout untouched | Manual regression | |

The existing `arrowColor.test.ts` is a pure logic unit test — no DOM/component testing infrastructure exists. The existing `npm test` suite covers only `arrowColor` logic.

### Sampling Rate
- **Per task commit:** `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm test` (fast, < 5s)
- **Per wave merge:** `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build` (verifies TypeScript + bundle)
- **Phase gate:** Full build green + manual mobile verification before `/gsd:verify-work`

### Wave 0 Gaps
- No new test files required — this phase adds no pure logic functions to unit test. The deferred apply logic is tightly coupled to React state and would require `@testing-library/react` to test properly, which is not installed. Manual verification is the appropriate gate.

---

## Project Constraints (from CLAUDE.md)

- **`data-testid` on every interactive element** — all new buttons must follow `btn-{action}` naming. UI spec provides: `btn-open-filter-sidebar`, `btn-open-bookmark-sidebar`, `btn-close-filter-sidebar`, `btn-close-bookmark-sidebar`, `drawer-filter-sidebar`, `drawer-bookmark-sidebar`
- **Semantic HTML** — use `<button>` (via shadcn `Button`) for all interactive elements
- **ARIA labels on icon-only buttons** — trigger buttons have visible text so `aria-label` is supplemental; close X buttons are icon-only and MUST have `aria-label`
- **Theme constants in theme.ts** — `PRIMARY_BUTTON_CLASS` is already in `theme.ts` and must be imported from there for active button state
- **Always check mobile variants** — this phase IS the mobile variant; verify desktop layout is untouched
- **Type safety** — `localFilters` must be typed as `FilterState`, not `any`
- **No magic numbers** — button sizes (`h-9 w-9`) are presentational Tailwind classes, not numeric thresholds; acceptable as-is
- **Mobile friendly** — this phase's entire purpose is mobile UX; all changes are inside `md:hidden` block

---

## Open Questions

1. **Board flip timing with deferred apply**
   - What we know: Original code called `setBoardFlipped(color === 'black')` inline when `color` changed. Deferred apply delays `setFilters` until sidebar close.
   - What's unclear: Should board flip also be deferred (only flips after closing sidebar), or should it flip immediately as user changes "Played as" inside the sidebar?
   - Recommendation: Defer the flip along with all other filters per D-10 (mobile deferred apply). Apply `setBoardFlipped(localFilters.color === 'black')` in the close handler alongside `handleFiltersChange(localFilters)`. This is consistent — the board position doesn't change until filters commit.

2. **`ChevronUp`/`ChevronDown` removal safety**
   - What we know: These are imported for collapsible triggers being removed. Lucide-react tree-shakes unused icons so this is cosmetic.
   - What's unclear: Are ChevronUp/ChevronDown used elsewhere in Openings.tsx after the collapsibles are removed?
   - Recommendation: Search for all usages before removing the import. The executor should verify with a quick grep before removing.

---

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/ui/drawer.tsx` — Vaul Drawer component, directional support confirmed
- `frontend/src/pages/Openings.tsx` — Mobile layout (lines 785-981), filter state, handlers
- `frontend/src/components/filters/FilterPanel.tsx` — FilterState interface, visibleFilters prop
- `frontend/src/components/board/BoardControls.tsx` — Current button sizes
- `frontend/src/lib/theme.ts` — PRIMARY_BUTTON_CLASS, brand colors
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` — Props interface
- `frontend/package.json` — vaul ^1.1.2, lucide-react ^0.577.0
- `.planning/phases/39-.../39-UI-SPEC.md` — Canonical design contract for this phase
- `.planning/phases/39-.../39-CONTEXT.md` — Locked decisions

### Secondary (MEDIUM confidence)
- `frontend/src/lib/arrowColor.test.ts` — Confirms Vitest is the test framework with no DOM setup
- `frontend/vite.config.ts` — Confirms no vitest config file (auto-discovery from vite config)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in package.json and source code
- Architecture: HIGH — all patterns verified against live source files
- Pitfalls: HIGH — derived from reading actual code being modified
- Vaul direction="right" behavior: HIGH — verified in drawer.tsx CSS selectors

**Research date:** 2026-03-30
**Valid until:** 2026-06-01 (stable libraries; Vaul and Tailwind CSS 4 are unlikely to have breaking changes in this window)
