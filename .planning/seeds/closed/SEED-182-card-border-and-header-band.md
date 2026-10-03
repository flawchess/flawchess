---
id: SEED-182
status: dormant
planted: 2026-10-02
planted_during: no open milestone (after v2.19), during Phase 227 (SEED-171); standalone /gsd-explore session on the dark theme
trigger_when: next frontend polish / UI quick task, or any phase touching card styling; small enough for /gsd-quick
scope: small (CSS tokens + card.tsx + call-site audit; frontend-only, no backend, no migration)
---

# SEED-182: Card border + lighter header band on every `.charcoal-texture` surface

## Why This Matters
The dark theme is hard to read on a phone in sunlight: cards are barely distinguishable from the
page. Page bg `oklch(0.145)` ≈ `#0a0a0a` vs card `--charcoal #161412` is a ~1.08:1 fill contrast,
cards have no border, and the CardHeader band (`bg-black/20`) is *darker* than the card body, so it
reads as a hole cut into the card instead of a raised surface.
The owner wants to keep today's darkness and all existing containers. Sketch 007 (winner **S2**) showed
that a hairline border plus a lighter header band restores the card edge, including under simulated glare.

## The change (sketch 007 S2)
1. **CardHeader band** `bg-black/20` → `white/3.5%` (`frontend/src/components/ui/card.tsx`).
2. **1px border, white/8%** (`border-border/80`, since `--border` is white/10%) on **every
   `.charcoal-texture` surface** (owner decision 2026-10-02: not Card-only), via `.charcoal-texture`
   in `frontend/src/index.css`.
3. **In-card separators** (CardHeader `border-b border-border/40`, `divide-border/40`) raised to the
   same white/8% so the border and separators match.

Unchanged: page bg, `--charcoal`, noise texture, brand brown. Lifted-surface variants (A: black page
with `#26221f` cards; B: `#161412` page with `#2b2724` cards + shadow) were rejected.

## Gotchas
- **Real `border`, not an inset `box-shadow`.** Children with a background (the header band) paint
  over an inset shadow and hide the edge. Sketch round 2 hit exactly this.
- **Call sites that already set borders:** `Card accentColor` (`border-l-4` spine, must keep winning
  over the 1px left border), `PersonaCard` `.persona-accent-frame` (own accent border + glow),
  Endgames/insights accordion items passing `border-none` (decide: drop `border-none` or keep it on purpose),
  `SidebarLayout` (`border-r border-border`).
- **Layout shift:** +1px each side; check tight grids (Bots persona 4-col grid, BoardControls, brand TabsList `p-[3px]`).
- Border color is white-alpha, so it composites against the card fill; verify it is visible on `--sidebar-bg`/`--charcoal-hover` surfaces too.

## Breadcrumbs
- Sketch: `.planning/sketches/007-dark-surface-elevation/` (README "Decision" section; MANIFEST row 007)
- `frontend/src/index.css`: `.dark` tokens, `--charcoal`, `.charcoal-texture` (+ `::before` noise)
- `frontend/src/components/ui/card.tsx`: `Card`, `CardHeader`
- `.charcoal-texture` surfaces outside `<Card>`: `ui/tabs.tsx` (brand variant), `layout/SidebarLayout.tsx`,
  `bots/PersonaCard.tsx`, `board/BoardControls.tsx`, `analysis/AnalysisTabs.tsx`, `analysis/AnalysisTagsPanel.tsx`,
  `library/MoveStats.tsx`, `library/TacticComparisonGrid.tsx`, `results/LibraryGameCard.tsx`,
  `charts/Endgame{OverallPerformanceSection,TypeTcCard,MetricsByTcCard,TimePressureCard}.tsx`,
  `insights/EndgameInsightsBlock.tsx`, `pages/Endgames.tsx`, `pages/openings/{StatsTab,ExplorerTab}.tsx`,
  `pages/Admin.tsx`, `admin/*`
- Baseline + glare screenshots: `temp/theme-explore/` (local, gitignored)

## Verification
Browser UAT at 390px on Endgames, Openings Stats, Library, Bots, Analysis: card edges visible, no
doubled borders on accent-spine/persona cards, no layout jumps. Run `npm run lint && npm run build && npm test`.
