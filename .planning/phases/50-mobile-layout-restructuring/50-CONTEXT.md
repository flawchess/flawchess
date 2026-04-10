# Phase 50: Mobile Layout Restructuring - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the Openings page mobile layout so the Moves/Games/Stats subtabs, the color toggle, the filter drawer trigger, and the bookmark drawer trigger all live in a single horizontal row below the collapsible board, outside the collapse animation. The vertical board-action column shrinks to five buttons that grow taller to fill the freed vertical space. The sticky wrapper gets a translucent blurred background mirroring the desktop sidebar panel look. Endgames mobile receives a small visual-alignment pass only — no structural change. No backend, no new features, no change to desktop layout.

Scope: Openings mobile layout (`md:hidden` branch of `frontend/src/pages/Openings.tsx`) plus a minor visual-alignment touch on Endgames mobile (`md:hidden` branch of `frontend/src/pages/Endgames.tsx`). Desktop layouts are untouched. No changes to filter/bookmark drawer internals, vaul drawer component, or data flow.

</domain>

<decisions>
## Implementation Decisions

### Unified Control Row (the core move)
- **D-01:** On mobile, a single horizontal row holds the Moves/Games/Stats subtab list, the color toggle button, the bookmark drawer trigger, and the filter drawer trigger. These four items are removed from the vertical board-action column where the color toggle, filter button, and bookmark button currently live.
- **D-02:** Left-to-right order in the row is: **Tabs | Color toggle | Bookmark | Filter**. The tabs take the remaining flex space; the three action buttons are fixed-width icon buttons on the right side near the user's thumb.
- **D-03:** The row lives **inside** the sticky top wrapper but **outside** the `grid-rows` collapse animation that hides the board. Result: when the user collapses the board with the handle, the unified row remains visible and usable. This is the main ergonomic win over the current layout, where collapsing the board also hides the color toggle, filter button, and bookmark button.
- **D-04:** The subtab list uses a normal flex `TabsList` — **no** horizontal scrolling, **no** swipe-to-paginate, **no** carousel. With three tabs at `text-xs` the row fits comfortably at 375px viewport. The decision to reopen this is deferred to whenever an Insights subtab is actually added.
- **D-05:** **Swipe-to-navigate between tabs remains out of scope** (reaffirmed from PROJECT.md "Out of Scope" list). Horizontal swipe on content would collide with chess piece dragging on the Moves subtab.

### Vertical Board-Action Column
- **D-06:** The vertical column to the right of the board shrinks from 8 items to 5: back, forward, reset, flip, and the info popover. The color toggle, filter button, and bookmark button are gone (moved to the unified row per D-01).
- **D-07:** The 5 remaining buttons grow **taller** (more vertical gap / larger touch targets) to fill the freed vertical space. The column stays the same **width** — the board itself keeps its current horizontal footprint. Enlarging the column width would shrink the board on 375px screens where it is already tight.

### Sticky Wrapper Background
- **D-08:** The sticky top wrapper background changes from the current opaque `bg-background` plus hard shadow to `bg-background/80 backdrop-blur-md` — the exact same translucent-blur pattern used by the desktop sidebar panel (`frontend/src/components/layout/SidebarLayout.tsx:112`). This is not charcoal-texture; it is true backdrop-blur. The project already pays this cost on desktop with acceptable performance.
- **D-09:** The current heavy shadow `shadow-[0_6px_20px_rgba(0,0,0,0.8)]` needs to be softened or removed — a hard shadow under a glass surface looks wrong. Exact tuning is Claude's discretion. The sticky wrapper must still be visually separable from content scrolling below it.
- **D-10:** When the board is visible, visual change is minimal because the react-chessboard squares are opaque. The translucent-blur effect is mostly visible around the board padding, behind the unified row, and around the collapse handle. When the board is collapsed, the remaining strip (unified row + handle) becomes a glassy blurred surface with scroll content faintly visible through it.

### Board Collapse Handle
- **D-11:** The collapse handle stays at the **bottom** of the sticky region (below the unified row), which preserves current muscle memory.
- **D-12:** The handle becomes **taller** than its current sliver. Today it is hard to tap — the user flagged this as a real touch-target problem. Exact height is Claude's discretion, but it must comfortably meet the 44px minimum touch target guideline used elsewhere in the app.

### Endgames Mobile (EGAM-01)
- **D-13:** Endgames mobile structure is NOT restructured. It already has subtabs + filter button in a sticky top row and has no board, no color toggle, and no bookmarks — none of the Openings restructuring motivation applies.
- **D-14:** Endgames mobile receives a **visual-alignment pass only**: apply the same `bg-background/80 backdrop-blur-md` to its sticky top row so it reads as a sibling to the new Openings mobile pattern, and match row height and gap sizing to the new Openings unified row so the two pages feel visually consistent. No structural changes, no new buttons, no layout rework.

### Out of Phase 50 Scope (explicitly)
- **D-15:** No changes to the filter panel content or the bookmark panel content — only the trigger button positions move.
- **D-16:** No changes to the mobile vaul drawers themselves (right-side sheets for filters/bookmarks).
- **D-17:** No changes to the global mobile bottom nav (`MobileBottomBar` in `frontend/src/App.tsx`).
- **D-18:** No changes to desktop layouts for either Openings or Endgames.
- **D-19:** No changes to the Games subtab content layout inside Openings — only the tab list location changes, not what the tabs render.

### Claude's Discretion
- Exact heights of the unified row, the enlarged board-action buttons, and the collapse handle (subject to 44px touch target minimum)
- Exact gap sizing inside the unified row
- Whether to keep a subtle shadow or drop it entirely when moving to backdrop-blur
- Whether the notification dots on filter and bookmark icons stay exactly as they render today or need visual adjustment in the new row position
- How the sticky wrapper's `z-index` interacts with the filter and bookmark drawers (current `z-20` may or may not need to change)
- Whether the info popover stays in the vertical column or moves into the unified row (if keeping 5 items in the column feels unbalanced after the enlargement, Claude may move `info` into the unified row as a 5th item)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` — MMOB-01 and EGAM-01 definitions; Out of Scope list (swipe-to-navigate between tabs)
- `.planning/ROADMAP.md` — Phase 50 goal and three success criteria
- `.planning/PROJECT.md` — "Out of Scope" list reaffirms swipe-to-navigate ruling; current milestone description

### Phase 49 Prior Work
- `.planning/phases/49-openings-desktop-sidebar/49-CONTEXT.md` — Phase 49 scoped itself to desktop only and explicitly deferred mobile to Phase 50. No mobile decisions were locked in Phase 49.
- `.planning/phases/49-openings-desktop-sidebar/49-01-SUMMARY.md` — Phase 49 introduced the shared `SidebarLayout` component on desktop. Phase 50 does not reuse this component on mobile but references its visual pattern (translucent blur) as the style target.

### Existing Code — Primary Change Targets
- `frontend/src/pages/Openings.tsx` — Main change target. Mobile branch at `md:hidden` (around line 913). Current structure: sticky top wrapper (line 916) containing collapsible grid (line 918) holding board + 8-item vertical controls column (lines 920–1012), then `TabsList` subtabs (line 1015), then collapse handle button (line 1027). `boardCollapsed` state, `filters.color` state, filter/bookmark drawer open handlers, and notification dot conditions already exist — Phase 50 rewires placement, not logic.
- `frontend/src/pages/Endgames.tsx` — Visual-alignment target only. Mobile branch at `md:hidden` (line 347). Current sticky top row (line 350) already holds `TabsList` + filter button. Apply backdrop-blur and match row height/gaps to the new Openings pattern.

### Existing Code — Visual Reference
- `frontend/src/components/layout/SidebarLayout.tsx:112` — Desktop sidebar panel className is the authoritative visual reference: `bg-background/80 backdrop-blur-md border border-border rounded-r-md`. Mobile sticky wrapper background should use the same `bg-background/80 backdrop-blur-md` combo.

### Existing Code — Do Not Modify
- `frontend/src/App.tsx` — `MobileBottomBar` (line 179), `BOTTOM_NAV_ITEMS` (line 55), `MobileHeader` (line 143). Global mobile chrome. Out of scope for Phase 50.
- `frontend/src/components/filters/FilterPanel.tsx` — Filter panel content. Only the trigger location moves.
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` — Bookmark list content. Only the trigger location moves.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing Tabs component** (`@/components/ui/tabs`): Used in both mobile branches today. No new component needed — the unified row just hosts a `TabsList` plus three icon buttons inside a flex container.
- **Existing filter/bookmark icon buttons** in the current vertical column (Openings.tsx lines 968–1009): JSX and handlers can be lifted wholesale into the new unified row. State, aria-labels, notification dots, tooltips, `data-testid` attributes all carry over.
- **Existing color toggle button** (Openings.tsx lines 951–967): Same — lift into the unified row unchanged.
- **Existing `bg-background/80 backdrop-blur-md` pattern** in `SidebarLayout.tsx:112`: Proven working on desktop, can be applied verbatim to the mobile sticky wrapper.

### Established Patterns
- **Desktop/mobile split via `md:hidden` / `hidden md:`**: Phase 50 only modifies the `md:hidden` branches. Desktop is locked by Phase 49 and must not change.
- **Sticky top wrapper with collapsible board via grid-rows trick** (Openings.tsx lines 916–1014): `grid-rows-[0fr]` vs `grid-rows-[1fr]` with `overflow-hidden` drives the smooth collapse animation. Phase 50 keeps this mechanism but moves the unified row outside the collapse grid so it stays visible when `boardCollapsed` is true.
- **Vaul drawer triggers from icon buttons**: Current pattern (button click → `setMobileFiltersOpen(true)`) stays unchanged. Only the buttons' location in the DOM moves.
- **`data-testid` conventions**: All existing testids on the moved buttons must be preserved. The new unified row itself should get a stable testid (e.g., `openings-mobile-control-row`) per the browser automation rules in CLAUDE.md.

### Integration Points
- **`boardCollapsed` state** (Openings.tsx line 108): Currently gates the grid-rows collapse on the entire sticky top content. After restructuring, this state only gates the board + vertical controls column — the unified row and the collapse handle sit outside the grid. The touch handler for the handle (`handleHandleTouchStart`/`handleHandleTouchEnd`) and the click toggle both stay.
- **Filter and bookmark drawer state** (`mobileFiltersOpen`, `setMobileFiltersOpen`, analogous bookmark state): Unchanged. Triggers relocate but wiring is identical.
- **`filters.color` toggle handler** (Openings.tsx around line 957): Unchanged. Button relocates to the unified row.
- **Notification dot conditions** on filter icon (`bookmarks.length > 0 && !filtersHintDismissed`, Openings.tsx line 978) and bookmark icon (`bookmarks.length === 0 && hasGames`, line 999): Unchanged. Dots move with their buttons.
- **Endgames sticky top row** (`Endgames.tsx` line 350): Current structure `<div className="sticky top-0 z-20 flex items-center gap-2 pb-2">` just gets a background className change and a row-height alignment to match Openings.

</code_context>

<specifics>
## Specific Ideas

- The user's motivating insight: **collapsing the board currently also hides the color toggle, filter, and bookmark buttons** because they are nested inside the same `grid-rows` collapse region as the board. This is the single biggest reason to restructure. Moving those three controls out of the collapse region is the core value delivered by Phase 50.
- The desktop sidebar panel (`SidebarLayout.tsx:112`) is the explicit visual reference for the backdrop-blur effect. Not charcoal-texture. Not just a transparent color. The exact combo is `bg-background/80 backdrop-blur-md`.
- The user flagged the current collapse handle as "hard to tap". The enlargement is a real touch-target fix, not a cosmetic tweak.
- The Insights subtab is anticipated but not yet in scope. Phase 50 does not plan for it — the decision is to handle the 4-tab space problem when and if Insights is actually being added.
- Endgames mobile is deliberately left structurally alone. The visual-alignment pass is scoped to `backdrop-blur-md` on its sticky row and height/gap matching so the two pages read as siblings.

</specifics>

<deferred>
## Deferred Ideas

- **Scrollable / swipeable / carousel subtabs** — deferred until a 4th tab (e.g., Insights) is actually being added. Phase 50 uses a plain flex `TabsList`.
- **Swipe-on-content-to-change-tab** — remains in PROJECT.md Out of Scope. Reaffirmed, not reopened.
- **Endgames mobile structural restructuring** — deferred indefinitely. Current structure is already close to what the new Openings pattern delivers; no motivation to restructure.
- **Info popover relocation** — may or may not happen in the same phase. Claude's discretion whether to lift `info` into the unified row if the 5-item vertical column feels unbalanced after the enlargement.

</deferred>

---

*Phase: 50-mobile-layout-restructuring*
*Context gathered: 2026-04-10*
