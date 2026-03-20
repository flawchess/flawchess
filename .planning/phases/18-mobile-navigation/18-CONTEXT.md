# Phase 18: Mobile Navigation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Users on mobile viewports (<640px) navigate the full app through a bottom navigation bar with direct page buttons and a "More" drawer. Desktop navigation remains unchanged. Safe-area insets prevent content from overlapping notch/Dynamic Island on iPhones in standalone PWA mode.

</domain>

<decisions>
## Implementation Decisions

### Navigation pattern
- Bottom navigation bar (not hamburger-only) — matches chess.com/lichess mobile pattern
- 3 direct tab buttons: Import, Openings, Global Stats (icon + label below)
- 4th button: "More" (hamburger icon + "More" label) — opens bottom sheet drawer
- Bottom bar visible only for authenticated users — login page has no nav
- Active route highlighted in bottom bar

### Bottom sheet drawer (More)
- Slide-up half-sheet from bottom when "More" is tapped
- Content: username/email at top, all nav links (for discoverability), separator, Logout button
- Tapping any nav link closes the sheet and navigates
- Dimmed backdrop behind sheet; tap backdrop to dismiss

### Context-sensitive bottom bar (experimental)
- On the Openings page, consider replacing bottom bar nav buttons with chessboard controls (reset, previous move, next move, flip board)
- This is experimental — implement the standard bottom bar first, then experiment with contextual actions
- If contextual controls are used, the "More" button should remain for navigation access

### Mobile header
- On mobile (<640px): simplified header with "Chessalytics" brand left-aligned + current page title
- Page title shows top-level name only (e.g., "Openings" not "Openings > Moves")
- Desktop header (≥640px): unchanged horizontal nav bar with all links

### Breakpoint
- 640px (Tailwind `sm`) — below this gets mobile layout (bottom bar + simplified header), above gets desktop layout (horizontal nav in header)
- Matches Phase 18 success criteria specification

### Safe-area insets
- `viewport-fit=cover` already set in index.html (Phase 17)
- Apply `env(safe-area-inset-*)` CSS for header top padding and bottom bar bottom padding
- Prevents overlap with notch/Dynamic Island on iPhones in standalone PWA mode

### Claude's Discretion
- Bottom bar animation style and transition timing
- Exact icons for each bottom bar tab (Lucide icon choices)
- Bottom sheet implementation approach (shadcn Sheet vs custom)
- Safe-area inset CSS implementation details
- Whether to use shadcn Drawer component or custom bottom sheet

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Navigation structure
- `.planning/REQUIREMENTS.md` — NAV-01, NAV-02, NAV-03 requirements (hamburger drawer, active route, safe-area)
- `.planning/ROADMAP.md` §Phase 18 — Success criteria (640px breakpoint, hamburger visibility, drawer links, safe-area)

### Prior phase context
- `.planning/phases/17-pwa-foundation-dev-workflow/17-CONTEXT.md` — PWA decisions (viewport-fit=cover, dark theme, standalone mode)

### Current navigation code
- `frontend/src/App.tsx` — `NavHeader` component (lines 39-77), `NAV_ITEMS` array, `ProtectedLayout` wrapper

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NavHeader` component in `App.tsx`: Has `NAV_ITEMS` array and `isActive()` route matching logic — reuse for bottom bar
- shadcn/ui `Button` with `ghost` variant: Currently used for nav links — reuse in bottom bar tabs
- `useAuth` hook: Provides `logout` function and `token` for conditional rendering
- shadcn/ui component library: Has Dialog, but no Sheet/Drawer yet — may need to add

### Established Patterns
- Tailwind CSS for all styling — use Tailwind responsive prefixes (`sm:hidden`, `hidden sm:flex`)
- shadcn/ui for component primitives — prefer shadcn components over custom implementations
- `data-testid` on all interactive elements (CLAUDE.md requirement)
- React Router `useLocation` for active route detection

### Integration Points
- `App.tsx` `ProtectedLayout` — currently renders `NavHeader` + `Outlet`; needs to render bottom bar on mobile
- `App.tsx` `NavHeader` — needs responsive hiding on mobile, simplified mobile header variant
- `index.html` — `viewport-fit=cover` already set, ready for safe-area CSS

</code_context>

<specifics>
## Specific Ideas

- Bottom bar should feel like chess.com/lichess Android apps — icon + label below each button, thumb-reachable
- Context-sensitive bottom bar on Openings page: swap nav buttons for board controls (reset, prev, next, flip) — experimental, try after base implementation works
- "More" button always stays in bottom-right position for consistency

</specifics>

<deferred>
## Deferred Ideas

- Context-sensitive board controls in bottom bar (Openings page) — experiment during or after Phase 18 base implementation
- UX-F01 from REQUIREMENTS.md is now superseded — bottom bar is being implemented in Phase 18 instead of deferred

</deferred>

---

*Phase: 18-mobile-navigation*
*Context gathered: 2026-03-20*
