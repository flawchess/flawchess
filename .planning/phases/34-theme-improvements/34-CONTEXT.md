# Phase 34: Theme Improvements - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Centralize theme management and improve visual consistency across all pages. Covers: CSS variable migration for brand colors, charcoal container styling with noise texture, filter button spacing, WDL chart corner consistency, subtab highlighting, navigation header polish, and collapsible section styling.

</domain>

<decisions>
## Implementation Decisions

### Container Styling
- **D-01:** Charcoal background with SVG feTurbulence noise texture applied to specific content sections — NOT full-page panels
- **D-02:** Implementation via CSS variable + Tailwind utility class (e.g. `bg-charcoal`) — not a wrapper component
- **D-03:** Charcoal containers apply to: endgame statistics sections, endgame concept accordion, game cards, bookmark cards, subtab navigation bar, import page cards/containers
- **D-04:** Sidebar filter panel does NOT get a card container — uses flat background `#171513` (dark brown), distinct from main content background

### Filter Button Layout
- **D-05:** Filter buttons should be spaced horizontally across the full sidebar width — Claude's discretion on whether to use equal-width grid or flex-grow
- **D-06:** Keep the two existing filter patterns separate (raw buttons for Time Control/Platform, ToggleGroup for Rated/Opponent) — just fix the spacing, don't unify

### Chart Consistency
- **D-07:** All WDL charts use rounded corners — apply rounded corners to Recharts `WDLBarChart` bars to match custom `WDLBar` and `EndgameWDLChart` components
- **D-08:** Glass overlay stays on custom WDL bars only — do NOT add glass effect to Recharts bars. Just match corners and theme colors.

### Subtab Highlighting
- **D-09:** Active subtab gets brand brown (#8B5E3C) as background fill with white text — bold, clear active state
- **D-10:** Subtab navigation bar itself uses charcoal background (per D-03)

### Navigation Header
- **D-11:** Active main navigation tab highlighted with a lighter background spanning the full header height
- **D-12:** Remove the white border from the header
- **D-13:** Logo and "FlawChess" text both link to the homepage

### Collapsible Sections
- **D-14:** All collapsible sections (Dashboard, Openings, Endgames) use charcoal background consistently — no more divergent styling between pages
- **D-15:** The entire collapsible (header + expanded content) is one charcoal container with its own padding — not just the header getting charcoal

### CSS Variable Migration (Folded Todo)
- **D-16:** Migrate brand brown from `PRIMARY_BUTTON_CLASS` hardcoded hex in theme.ts to a CSS variable in index.css's `@theme inline` block — enables Tailwind utility usage (`bg-brand` etc.) without hardcoded brackets
- **D-17:** WDL and gauge colors remain in theme.ts as JS constants (oklch values used in inline styles) — no need to migrate these to CSS variables

### Claude's Discretion
- Filter button layout approach (grid vs flex-grow) — pick what looks best given button counts per group
- WDL bar height normalization (h-5 vs h-6) — unify if it improves consistency
- Exact charcoal color value — pick something that works with the noise texture and contrasts with the `#171513` sidebar

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme system
- `frontend/src/lib/theme.ts` — Current theme constants (WDL colors, gauge zones, board colors, PRIMARY_BUTTON_CLASS)
- `frontend/src/index.css` — Tailwind v4 `@theme inline` block, shadcn CSS variables, dark mode setup

### Components to modify
- `frontend/src/components/filters/FilterPanel.tsx` — Filter button layout (two patterns: raw buttons + ToggleGroup)
- `frontend/src/components/results/WDLBar.tsx` — Custom WDL bar (rounded, h-6, glass overlay)
- `frontend/src/components/charts/EndgameWDLChart.tsx` — Custom endgame WDL rows (rounded, h-5, glass overlay)
- `frontend/src/components/charts/WDLBarChart.tsx` — Recharts WDL bar chart (square corners, needs rounding)
- `frontend/src/components/ui/tabs.tsx` — Subtab component (needs brand brown active state)

### Pages with containers to update
- `frontend/src/pages/OpeningsPage.tsx` — Sidebar + content layout, collapsibles
- `frontend/src/pages/EndgamesPage.tsx` — Sidebar + content layout, collapsibles
- `frontend/src/pages/DashboardPage.tsx` — Collapsible sections (currently plain ghost buttons)
- `frontend/src/pages/ImportPage.tsx` — Import cards/containers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme.ts`: Already centralizes WDL/gauge colors and board square colors — extend with container/brand CSS variables
- shadcn `tabs.tsx`: Has `default` and `line` variants — can add `brand` variant or modify default
- shadcn CSS variable system in `index.css`: Well-structured `@theme inline` block ready for new variables

### Established Patterns
- Tailwind v4 with `@theme inline` in `index.css` — no tailwind.config file
- Dark mode via `.dark` class selector
- oklch color space for WDL/gauge colors (inline styles)
- shadcn component variants via `class-variance-authority` (cva)

### Integration Points
- `index.css @theme inline` block: Add brand brown, charcoal, sidebar background as CSS variables
- `theme.ts`: Keep as JS export hub but reference CSS variables where possible
- Navigation header: likely in `frontend/src/components/` layout components
- Collapsible pattern: used across Dashboard, Openings, Endgames pages with inconsistent styling

</code_context>

<specifics>
## Specific Ideas

- Charcoal texture: Use SVG feTurbulence for lightweight, repeatable grain — no image assets
- Sidebar background: specifically `#171513` (dark brown)
- Brand brown for active subtabs: `#8B5E3C` fill with white text
- Collapsibles must feel like one unified container when expanded, not header-only styling

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 34-theme-improvements*
*Context gathered: 2026-03-28*
