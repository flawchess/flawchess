# Phase 49: Openings Desktop Sidebar - Research

**Researched:** 2026-04-09
**Domain:** React layout restructuring — collapsible sidebar, overlay vs push, Tailwind responsive design
**Confidence:** HIGH

## Summary

Phase 49 replaces the current 2-column desktop layout (`350px sidebar | 1fr tabs`) with a collapsed icon strip (48px) plus an optionally open panel (280px). The board, BoardControls, opening name, and MoveList move from the current `sidebar` variable into the main content area. The new sidebar hosts only Filters and Bookmarks panels.

All required components (FilterPanel, PositionBookmarkList, Button, Tooltip, Lucide icons) are already installed. No new npm packages or shadcn additions are needed. The primary work is restructuring Openings.tsx's desktop layout branch (`hidden md:grid` at line 903) and introducing a sidebar state machine (`null | 'filters' | 'bookmarks'`). The UI-SPEC.md (49-UI-SPEC.md) provides a complete, approved visual and interaction contract — the planner should treat it as a locked specification.

The single technical risk is the overlay vs push behavior at the `xl` (1280px) breakpoint. Below xl the open panel must be positioned absolutely so it does not push/overflow the layout; above xl it participates in a 3-column grid. The UI-SPEC prescribes specific dimension values (strip: 48px, panel: 280px, breakpoint: 1280px) that make this straightforward.

**Primary recommendation:** Implement as a single-file edit to `frontend/src/pages/Openings.tsx`, restructuring only the `hidden md:grid` desktop section and adding sidebar strip + panel JSX. All child components, hooks, and filter state remain unchanged.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The current 2-column desktop layout (`[350px sidebar] | [1fr tabs]`) is replaced. The board and its associated controls (board controls, opening name, move list) move from the sidebar into the main content area.
- **D-02:** A collapsed sidebar strip lives on the left edge of the Openings page, showing filter and bookmark icons. This strip is always visible on desktop.
- **D-03:** Clicking a filter or bookmark icon in the collapsed strip opens the respective panel directly — no intermediate state.
- **D-04:** Only one panel (Filters or Bookmarks) is visible at a time. Clicking the other icon switches panels without requiring a double-click (close then open).
- **D-05:** Filter changes apply live while the sidebar panel is open — no deferred apply button on desktop. This matches the current desktop behavior where filters update immediately.
- **D-06:** On smaller desktop screens (where a 3-column push layout would cause overflow), the open sidebar overlays the chessboard rather than pushing it.
- **D-07:** On larger desktop screens where space permits, the sidebar pushes the board content right without overflow.

### Claude's Discretion
- Collapsed strip width, icon sizing, and tooltip labels
- Animation style for sidebar open/close (slide vs instant)
- Exact breakpoint for overlay vs push transition
- Whether clicking outside the open panel closes it
- How to reorganize the main content area (board + tabs layout)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DESK-01 | User sees a collapsible sidebar on the left of the Openings page with filter and bookmark icons visible in collapsed state | Collapsed strip: 48px wide, `bg-sidebar-bg`, two icon buttons — confirmed in UI-SPEC and existing Openings.tsx icon imports |
| DESK-02 | User can open the sidebar directly to Filters or Bookmarks by clicking the respective icon in the collapsed strip | Single-click open: `setSidebarOpen('filters')` / `setSidebarOpen('bookmarks')` — no intermediate state |
| DESK-03 | Only one panel (Filters or Bookmarks) is shown at a time in the sidebar; clicking the other icon switches panels | State machine: `sidebarOpen: null | 'filters' | 'bookmarks'` — click same icon toggles null, click other switches directly |
| DESK-04 | Filter changes apply live while the sidebar is open (no deferred apply on desktop) | FilterPanel renders directly against `useFilterStore` filters (no local copy) — same as current desktop tab |
| DESK-05 | Sidebar overlays the chessboard on smaller desktop screens where a 3-column push layout would be too tight | Below `xl` (1280px): panel `position: absolute, left: 48px, z-40`; at `xl+`: in-flow 3-column grid |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19 (project-pinned) | Component rendering | Project standard |
| TypeScript | project-pinned | Type safety | Project standard |
| Tailwind CSS | project-pinned | Utility-first styling, responsive breakpoints | Project standard |
| Lucide React | project-pinned | SlidersHorizontal, BookMarked icons | Already imported in Openings.tsx |

[VERIFIED: codebase grep] All packages already installed — no additions needed.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn Button | installed | Icon buttons for strip | ghost + brand-outline variants |
| shadcn Tooltip | installed | "Filters" / "Bookmarks" labels on strip icons | Always on icon-only buttons per CLAUDE.md |

**Installation:** None required. All packages are already present.

---

## Architecture Patterns

### Recommended Project Structure

No new files or directories. All changes are confined to:
```
frontend/src/pages/Openings.tsx   # Desktop layout section only (lines 900-932)
```

The `sidebar` variable (lines 427-629) is decomposed: board content extracted to desktop main area, filter/bookmark tabs replaced by the new strip+panel system.

### Pattern 1: Sidebar State Machine

**What:** Replace `sidebarTab: string` with `sidebarOpen: null | 'filters' | 'bookmarks'`. The `null` state means collapsed (panel not visible). The panel renders based on this value.

**When to use:** Always — this is the required interaction model per D-03/D-04.

```typescript
// State declaration (replaces or extends sidebarTab at line 95)
const [sidebarOpen, setSidebarOpen] = useState<null | 'filters' | 'bookmarks'>(null);

// Toggle / switch handler
const handleStripIconClick = useCallback((panel: 'filters' | 'bookmarks') => {
  setSidebarOpen(prev => prev === panel ? null : panel);
}, []);
```

[VERIFIED: codebase read] The existing `sidebarTab` state at line 95 can be replaced entirely — it is only used in the current desktop sidebar tabs, not in mobile code.

### Pattern 2: Overlay vs Push Layout

**What:** The desktop layout changes based on `xl` breakpoint:
- Below xl: `48px strip` + `absolute panel` + `full-width content`
- At xl+: `48px strip` + `280px panel (in-flow)` + `1fr content`

**When to use:** Required per D-06/D-07 and confirmed in UI-SPEC.

```tsx
{/* Desktop container: strip + optional panel + content */}
<div className="hidden md:flex md:flex-row md:min-h-0 md:flex-1 md:relative">

  {/* Collapsed strip — always visible */}
  <div
    className="flex flex-col items-center py-2 gap-1 bg-sidebar-bg charcoal-texture border-r border-border"
    style={{ width: '48px', flexShrink: 0 }}
    data-testid="sidebar-strip"
  >
    {/* strip icon buttons */}
  </div>

  {/* Panel — absolute below xl, in-flow at xl+ */}
  {sidebarOpen && (
    <>
      {/* xl+: in-flow panel that pushes content */}
      <div
        className="hidden xl:flex flex-col bg-sidebar-bg charcoal-texture border-r border-border overflow-y-auto"
        style={{ width: '280px', flexShrink: 0 }}
        data-testid="sidebar-panel"
      >
        {/* panel content */}
      </div>
      {/* below xl: absolute overlay panel */}
      <div
        className="xl:hidden absolute top-0 bottom-0 bg-sidebar-bg charcoal-texture border-r border-border overflow-y-auto z-40"
        style={{ left: '48px', width: '280px' }}
        data-testid="sidebar-panel"
      >
        {/* same panel content */}
      </div>
    </>
  )}

  {/* Main content area */}
  <div className="flex-1 min-w-0">
    {/* board + tabs */}
  </div>
</div>
```

**Alternative approach:** Use a single panel div and toggle `position` via conditional classes. The two-panel approach above duplicates the panel JSX but avoids runtime style toggling. A simpler single-panel approach is acceptable if the executor prefers it — extract the content to a variable to avoid duplication.

### Pattern 3: Outside-Click to Close

**What:** Click anywhere outside the open panel closes it. Required per UI-SPEC.

```typescript
// Via a transparent backdrop div rendered behind the panel
{sidebarOpen && (
  <div
    className="xl:hidden fixed inset-0 z-30"
    onClick={() => setSidebarOpen(null)}
    aria-hidden="true"
  />
)}
```

**Note:** The backdrop should only render below xl (overlay mode) since above xl the panel is in-flow and outside-click closing is less critical but can still be implemented via `useEffect` with `mousedown` listener.

[ASSUMED] The backdrop z-index (z-30 backdrop, z-40 panel) keeps the panel above the backdrop. Verify z-index stack doesn't conflict with other z-indexed elements in Openings.tsx (sticky mobile top bar uses `z-20` at line 938 — desktop-only changes don't affect this).

### Pattern 4: Notification Dots on Strip Icons

**What:** The existing pulsing notification dots (filters hint, bookmark empty-state hint) must be preserved on the new strip icon buttons.

**When to use:** Same conditions as current implementation:
- Filters dot: `bookmarks.length > 0 && !filtersHintDismissed`
- Bookmarks dot: `bookmarks.length === 0 && hasGames`

[VERIFIED: codebase read] The `filtersHintDismissed` state and `bookmarks`/`hasGames` variables are already available in scope. The dot JSX pattern (pulsing bg-red-500 span) is at lines 492-498 and 504-510 — reuse verbatim.

### Pattern 5: Main Content Area Board Layout

**What:** Board, BoardControls, opening name, and MoveList move from the `sidebar` variable into the desktop main content area. They stack above the existing Tabs (Moves/Games/Stats).

```tsx
{/* Desktop main content area */}
<div className="flex-1 min-w-0">
  {/* Board section — board + controls + opening name + move list */}
  <div className="flex flex-col gap-2 mb-6">
    <ChessBoard ... />
    <BoardControls ... />
    <div className="opening-name ...">...</div>
    <MoveList ... />
  </div>

  {/* Tabs: Moves / Games / Stats */}
  <Tabs value={activeTab} ...>
    ...
  </Tabs>
</div>
```

[VERIFIED: codebase read] The board section JSX (lines 430-481) and the tabs section (lines 906-932) exist separately — they only need to be combined under one container.

### Anti-Patterns to Avoid

- **Duplicating filter state for the desktop panel:** The desktop panel must use `filters`/`setFilters` from `useFilterStore` directly, NOT a `localFilters` copy. The `localFilters` pattern is mobile-only (deferred apply). See lines 105, 1126 in Openings.tsx.
- **Removing `sidebarTab` before verifying it has no other consumers:** Grep confirms `sidebarTab` is only used in the desktop sidebar tabs (lines 95, 486, 504) — safe to replace.
- **Rendering notification dots in both mobile and desktop simultaneously:** The current mobile dots use `-mobile` suffix testids. The desktop strip dots should use the base testids (`filters-notification-dot`, `bookmarks-notification-dot`) per UI-SPEC. Ensure these don't collide with mobile dot testids (mobile uses `filters-notification-dot-mobile`).
- **Applying desktop layout changes to mobile section:** Per CLAUDE.md, always check both sections. Mobile layout is `md:hidden` and entirely separate — it must not be changed in this phase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Outside-click detection | Custom global event listener in component body | Transparent backdrop div or `useEffect` with `mousedown` on `document` | Backdrop div is simpler, idiomatic React, and already used in Radix modals |
| Slide animation | CSS `transform: translateX()` | Tailwind `transition-[width,opacity]` on the panel container | Width transition is simpler and doesn't require absolute positioning tricks |
| Overlay z-index management | Custom z-index constants | Tailwind z-30/z-40 | Sufficient for this single overlay use case |

**Key insight:** This is a layout restructuring, not a new feature. Leverage the existing component props and state — the only new logic is the `sidebarOpen` state machine and the layout grid change.

---

## Common Pitfalls

### Pitfall 1: Panel Duplication for Overlay vs Push

**What goes wrong:** To handle two distinct layout behaviors (absolute overlay vs in-flow push), the executor renders the panel content twice (once for each mode, toggled via `hidden`/`xl:block`). This creates duplicate `data-testid` attributes, which breaks browser automation and violates the testid contract.

**Why it happens:** The simplest approach to handle both CSS contexts is to render the same JSX twice.

**How to avoid:** Extract the panel content to a variable or component, then render it in both structural locations using the same variable. Or use a single panel div with conditional inline `style` that toggles `position` at runtime using a resize observer or JS-based breakpoint hook. The simplest correct approach: render one panel div and switch between `absolute` and `relative`/in-flow positioning via a conditional `className` driven by a JS `isXl` state.

**Warning signs:** `data-testid="sidebar-panel"` appearing twice in the rendered DOM.

### Pitfall 2: `sidebarTab` State Not Fully Replaced

**What goes wrong:** The `sidebarTab` state (line 95) is retained alongside the new `sidebarOpen` state, causing stale state to accumulate.

**Why it happens:** Executor replaces the tabs UI but forgets to remove the `sidebarTab` state and `setSidebarTab` references.

**How to avoid:** Grep for `sidebarTab` before marking complete — the state declaration at line 95, the `<Tabs value={sidebarTab}` at line 486, and `<TabsTrigger ... setSidebarTab>` at lines 500/512 must all be removed or replaced.

**Warning signs:** TypeScript unused variable warnings, or `sidebarTab` still in component state after refactor.

### Pitfall 3: Board Layout Breaking on md Without xl Content Area Width

**What goes wrong:** The main content area (now `flex-1`) renders the board at full width on md (768px) and wider. At xl+ when the panel is open, `1fr` of remaining space after `48px + 280px = 328px` is enough. But at md-xl, if the panel is open in absolute mode, the board may still jump/reflow unexpectedly.

**Why it happens:** The absolute-positioned panel overlays the board but can cause misalignment if the board container uses a grid that doesn't account for the strip width.

**How to avoid:** The outer desktop container should be `flex flex-row` rather than `grid`, with the strip as a fixed-width flex child and the content area as `flex-1`. This ensures the board always fills the space left by the strip regardless of panel state.

### Pitfall 4: knip Detecting Removed `sidebarTab` as Dead Export

**What goes wrong:** If `setSidebarTab` or `sidebarTab` is removed from the component but the state is still referenced in a type or export, knip flags it in CI.

**Why it happens:** The current code doesn't export these state values, but any residual references to `sidebarTab` will be caught by TypeScript as unused variables.

**How to avoid:** Run `npm run lint` (which includes knip per CLAUDE.md) after the refactor before committing.

---

## Code Examples

### Strip Icon Button with Notification Dot (Verified Pattern)

```tsx
// Source: Openings.tsx lines 990-1010 (mobile button) + UI-SPEC.md strip contract
<Tooltip content="Filters" side="right">
  <Button
    variant={sidebarOpen === 'filters' ? 'brand-outline' : 'ghost'}
    size="icon"
    className="relative"
    onClick={() => handleStripIconClick('filters')}
    aria-label={sidebarOpen === 'filters' ? 'Close filters' : 'Open filters'}
    data-testid="sidebar-strip-btn-filters"
  >
    <SlidersHorizontal className="h-5 w-5" />
    {bookmarks.length > 0 && !filtersHintDismissed && (
      <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-notification-dot">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
      </span>
    )}
  </Button>
</Tooltip>
```

### Desktop Filter Panel (Live Updates — No Local State)

```tsx
// Source: Openings.tsx lines 515-574 (current desktop tab filters content)
// Key: uses `filters` and `handleFiltersChange` directly — NOT localFilters
<div className="p-4 space-y-3">
  {/* Played as + Piece filter row */}
  <div className="flex flex-wrap gap-x-4 gap-y-3">
    {/* ... color toggle, matchSide toggle — same as current desktop sidebar */}
  </div>
  <div className="border-t border-border/20" />
  <FilterPanel filters={filters} onChange={handleFiltersChange} />
</div>
```

### Sidebar State Machine

```typescript
// Source: pattern derived from existing sidebarTab (line 95) + D-03/D-04 requirements
type SidebarPanel = 'filters' | 'bookmarks';
const [sidebarOpen, setSidebarOpen] = useState<SidebarPanel | null>(null);

const handleStripIconClick = useCallback((panel: SidebarPanel) => {
  setSidebarOpen(prev => prev === panel ? null : panel);
}, []);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Always-visible sidebar tabs (350px) | Collapsed strip (48px) + panel-on-demand (280px) | Phase 49 | Recovers ~270px horizontal space on smaller desktops; reduces visual noise |
| `sidebarTab: string` tracking active tab | `sidebarOpen: null | 'filters' | 'bookmarks'` | Phase 49 | Panel state includes open/closed, not just which tab |

**Deprecated/outdated after this phase:**
- `sidebar` JSX variable (lines 427-629): decomposed — board content moved to main area, filter/bookmark tabs replaced by new panel system
- `sidebarTab` state (line 95): replaced by `sidebarOpen`
- `md:grid md:grid-cols-[350px_1fr]` layout (line 903): replaced by flex-row with strip + optional panel

---

## Existing Code Touchpoints

| File | Lines | What Changes |
|------|-------|--------------|
| `frontend/src/pages/Openings.tsx` | 95 | Replace `sidebarTab` with `sidebarOpen: null \| 'filters' \| 'bookmarks'` |
| `frontend/src/pages/Openings.tsx` | 427-629 | Remove `sidebar` variable; distribute board JSX to main area, filter/bookmark JSX to panel |
| `frontend/src/pages/Openings.tsx` | 900-932 | Replace `hidden md:grid md:grid-cols-[350px_1fr]` with `hidden md:flex` strip+panel+content layout |
| `frontend/src/pages/Openings.tsx` | 486-627 | Remove the `<Tabs value={sidebarTab}>` block entirely (filter+bookmark tabs in old sidebar) |

Mobile section (lines 934-1273): **no changes** — desktop-only phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sidebarTab` has no consumers outside the desktop sidebar tabs section | Architecture Patterns | If used elsewhere, removal causes compile error |
| A2 | z-index z-30 (backdrop) / z-40 (panel) doesn't conflict with other stacked elements in desktop view | Common Pitfalls | Visual layering issue (panel hidden behind another element) |
| A3 | The `filtersHintDismissed` dismissal logic (clicking into filters dismisses the dot) still works after the state rename | Code Examples | Hint dot never dismisses, UX regression |

Note: A1 was partially verified by reading Openings.tsx — `sidebarTab` only appears in the desktop sidebar section (lines 95, 486, 500, 512). HIGH confidence it has no other consumers.

---

## Open Questions

1. **Single panel div vs two panel divs for overlay/push**
   - What we know: Two divs duplicates content but is CSS-only; one div requires JS resize tracking
   - What's unclear: Whether the executor prefers CSS-only or JS-driven approach
   - Recommendation: Use a single panel div. Track `isXlOrAbove` via a simple `useState` + `useEffect(window.matchMedia('(min-width: 1280px)'))` hook. This avoids duplicated testids and is unambiguous.

2. **Dismiss behavior for filtersHintDismissed after refactor**
   - What we know: Currently dismissed when the user clicks the filters tab (`setSidebarTab` triggers it — search `filtersHintDismissed`)
   - What's unclear: The exact line where dismissal is triggered — needs verification during implementation
   - Recommendation: Grep for `setFiltersHintDismissed` before implementing; ensure it fires when the filters panel opens.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is frontend layout restructuring only. No external dependencies, CLI tools, or services beyond the existing project stack.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.1 |
| Config file | vite.config.ts (no separate vitest.config.ts detected) |
| Quick run command | `npm test` (from `frontend/` directory) |
| Full suite command | `npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DESK-01 | Strip visible, icons present on desktop | manual / e2e | n/a — browser-only layout | N/A |
| DESK-02 | Click icon opens correct panel | manual / e2e | n/a — requires DOM interaction | N/A |
| DESK-03 | Switching icons changes panel without double-click | manual / e2e | n/a — requires DOM interaction | N/A |
| DESK-04 | Filter changes apply live (no Apply button) | manual / e2e | n/a — requires API + DOM | N/A |
| DESK-05 | Overlay at <1280px, push at 1280px+ | manual / e2e | n/a — requires viewport resize | N/A |

**Rationale:** All DESK requirements are visual/interactive layout behaviors that require a real browser with a chess board and viewport control. Vitest (unit test runner) cannot test these. The existing test files (`lib/*.test.ts`, `types/api.test.ts`) cover pure logic — no component or DOM tests exist in this project.

The phase gate for correctness is manual browser verification (resize test at md vs xl breakpoints, click through filter/bookmark panel open/close/switch).

### Sampling Rate

- **Per task commit:** `npm run lint` (includes knip + TypeScript check equivalent)
- **Per wave merge:** `npm test` (run from `frontend/` directory)
- **Phase gate:** `npm run build` must succeed (catches TS errors), `npm run lint` must pass (catches knip), manual browser test at 1024px and 1440px viewport widths

### Wave 0 Gaps

None — no new test files required. This phase has no unit-testable pure logic.

---

## Security Domain

This phase is frontend layout restructuring only. No authentication, data validation, cryptography, session management, or access control changes. Security domain: NOT APPLICABLE.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on This Phase |
|-----------|----------------------|
| `data-testid` on every interactive element | Strip icon buttons need `sidebar-strip-btn-filters`, `sidebar-strip-btn-bookmarks`; panel container needs `sidebar-panel` |
| `aria-label` on icon-only buttons | Both strip icon buttons require aria-label ("Open/Close filters", "Open/Close bookmarks") |
| Theme constants in `theme.ts` | No new semantic color values introduced — using existing CSS tokens (`bg-sidebar-bg`, `charcoal-texture`) |
| `noUncheckedIndexedAccess` enabled | No new array index accesses introduced by this phase |
| Knip runs in CI | After removing `sidebarTab` and `sidebar` variable, ensure no dead exports remain |
| Always apply changes to mobile too | Mobile layout is unchanged by design — this is desktop-only. The CLAUDE.md rule applies when a change is unintentionally missing from mobile; here mobile is intentionally out of scope (per D-01, Phase 50 handles mobile) |
| No magic numbers | Strip width `48`, panel width `280`, breakpoint `1280` should be named constants |
| `ty check` must pass | No backend changes; frontend TypeScript must compile — `npm run build` confirms this |

---

## Sources

### Primary (HIGH confidence)
- `frontend/src/pages/Openings.tsx` — current layout structure, state variables, component usage verified by direct read
- `.planning/phases/49-openings-desktop-sidebar/49-UI-SPEC.md` — approved design contract with exact dimensions, breakpoints, and interaction model
- `.planning/phases/49-openings-desktop-sidebar/49-CONTEXT.md` — locked decisions D-01 through D-07
- `frontend/src/components/filters/FilterPanel.tsx` — FilterPanel props interface and rendering verified
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` — PositionBookmarkList props interface verified
- `frontend/src/index.css` — `--sidebar-bg`, `--charcoal`, `.charcoal-texture` CSS tokens verified

### Secondary (MEDIUM confidence)
- `frontend/package.json` — Vitest 4.1.1 confirmed as test runner

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in codebase
- Architecture: HIGH — existing patterns and code locations verified by direct file read
- Pitfalls: HIGH — derived from concrete code reading (duplicate testids, sidebarTab removal, board layout)
- Validation: HIGH — Vitest confirmed, coverage gap is inherent (layout = manual test)

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable codebase, no moving parts)
