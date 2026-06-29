---
phase: 140
slug: full-game-analysis-board
status: draft
shadcn_initialized: true
preset: radix-nova / neutral
created: 2026-06-27
---

# Phase 140 — UI Design Contract

> Visual and interaction contract for the Full-Game Analysis Board refinement.
> Refines the existing v1.29 `/analysis` board (Phases 136–139, already shipped).
> This is NOT a greenfield UI — all tokens, component variants, and semantic colors
> must be drawn from the existing FlawChess design system.

Source decisions: `.planning/notes/analysis-board-fullgame-refinement.md` (all
"Locked decisions" sections are treated as already-decided in this contract and are NOT
re-asked). Source file scanned: `frontend/src/lib/theme.ts`, `components.json`,
`frontend/src/components/ui/button.tsx`, all referenced analysis components.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Style | radix-nova |
| Base color | neutral |
| Preset | not applicable (pre-existing project) |
| Component library | Radix UI (via shadcn) |
| Icon library | Lucide (`lucide-react`) |
| Font | CSS variable `--font-sans` (system sans, neutral base) |
| Mono font | CSS variable `--font-mono` — used for SAN notation in move list |

All semantic colors are defined in `frontend/src/lib/theme.ts`. Never hard-code
color hex or oklch literals inside components — always import from `theme.ts`.

---

## Spacing Scale

4 px grid throughout. Standard Tailwind spacing aliases (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px (p-1 / gap-1) | Icon gaps, inline chip internal padding |
| sm | 8px (p-2 / gap-2) | Compact element spacing, chip rows |
| md | 16px (p-4 / gap-4) | Default element spacing, section padding |
| lg | 24px (p-6 / gap-6) | Column-level gaps, card padding |
| xl | 32px (p-8) | Major section breaks |
| 2xl | 48px | Page-level vertical rhythm (mobile bottom padding) |
| 3xl | 64px | Reserved; not used in this phase |

Exceptions:
- Move list row min-height: 28px (`min-h-[28px]`) — carries over from Phase 137.
- Eval chart area height on analysis page: 120px (`h-[120px]`), matching approximately
  the LibraryGameCard desktop chart height. The slider row adds 16px (`h-4`) below,
  so the total eval-chart block = 136px.
- Board EvalBar gap: 8px (`gap-2`) — carries over from Phase 137.
- Variation tree Level-1 PV indent: 32px (`ml-8`). Level-2 sub-sideline indent: 64px
  (`ml-16`). These are explicit exceptions to the 4px grid (ml-8 = 32px is 4px × 8 —
  still on grid). The desktop tree's existing single-variation `ml-8` is promoted to
  the Level-1 contract; `ml-16` is the new Level-2 contract.

---

## Typography

All sizes from the Tailwind scale. Hard minimum: `text-sm` (14px) for all visible inline
text. The only exception permitted by CLAUDE.md is hover/tap-activated info tooltips
rendered as Radix Popover bodies with a HelpCircle trigger (e.g. `MetricStatPopover`).
No new exceptions in this phase.

| Role | Tailwind Class | Weight | Line Height | Usage in this phase |
|------|---------------|--------|-------------|---------------------|
| Body / label | `text-sm` (14px) | 400 (normal) | 1.5 | Engine lines, metadata, inline tag chips, slider labels, move list move number labels |
| Move SAN | `text-sm font-mono` (14px mono) | 400 | 1.4 | SAN text in both desktop and mobile variation tree |
| Inline flaw tag chip | `text-sm` (14px) | 500 (medium) | 1 | "Missed" / "Allowed" chip label in move list |
| Eval chart labels | `text-sm` (14px) | 400 | 1 | Phase-boundary annotations (carries over from EvalChart) |

Two weights in use: 400 (regular) + 500 (medium). No third weight.

---

## Color

All values are CSS-variable-based (Tailwind) or imported from `theme.ts`. No inline
hex or oklch literals in components.

| Role | Source | Value | Usage |
|------|--------|-------|-------|
| Dominant surface (60%) | CSS var | `bg-background` | Page background (charcoal) |
| Secondary surface (30%) | CSS var | `bg-card` / `bg-muted` | Cards, side panel, engine-lines area |
| Primary accent | Tailwind | `bg-brand-brown` | Primary CTA buttons (`variant="default"`) |
| Missed tactic | `theme.ts` | `TAC_MISSED` = `oklch(0.70 0.15 258)` (light blue) | Inline missed-tag chip border + text; punchline node color in tree |
| Missed tactic bg | `theme.ts` | `TAC_MISSED_BG` = `oklch(0.70 0.15 258 / 0.15)` | Inline missed-tag chip background |
| Allowed tactic | `theme.ts` | `TAC_ALLOWED` = `oklch(0.70 0.15 25)` (light red) | Inline allowed-tag chip border + text; blunder node color in tree |
| Allowed tactic bg | `theme.ts` | `TAC_ALLOWED_BG` = `oklch(0.70 0.15 25 / 0.15)` | Inline allowed-tag chip background |
| Muted text | CSS var | `text-muted-foreground` | Variation move text (Level-1 and Level-2), dimmed main-line moves after fork, move number labels |
| Active node | CSS var | `bg-primary text-primary-foreground` | Currently-selected node in move list (all levels) |
| Eval bar white-ahead | `theme.ts` | `EVAL_CHART_AREA_WHITE_AHEAD` | EvalChart and EvalBar (existing — no change) |
| Eval bar black-ahead | `theme.ts` | `EVAL_CHART_AREA_BLACK_AHEAD` | EvalChart and EvalBar (existing — no change) |
| Slider parked/dimmed | CSS var | `opacity-40` on slider `<input>` + `pointer-events-none` | Eval chart slider state when a sideline is active |
| Connector line | CSS var | `border-muted/40` | Left border on Level-1 and Level-2 indented blocks |
| Destructive | CSS var | `text-destructive` / `bg-destructive/10` | Not used in this phase (no destructive actions) |

Accent reserved for:
- `TAC_MISSED` (blue): inline missed-tag chips in move list; punchline move node text in tactic overlay; blue best-move arrow on board.
- `TAC_ALLOWED` (red): inline allowed-tag chips in move list; blunder move node text; red flaw-move arrow on board.
- `brand-brown`: primary CTA button fill only (`variant="default"`). Not used for any new button in this phase — the Analyze button is secondary (`brand-outline`).

---

## Component Inventory

New and modified components for this phase.

### New: Inline Flaw Tag Chip (inside VariationTree)

A compact pill rendered adjacent to the SAN text on flaw plies in the desktop move list.
Not a separate component file — rendered inline inside `DesktopTree.renderMoveButton()`.

Visual spec:
- Shape: `rounded-full` (pill)
- Height: fits within `min-h-[28px]` row — use `inline-flex items-center h-5 px-1.5`
- Text: `text-sm font-medium` — label is "Missed" (for TAC_MISSED) or "Allowed" (for TAC_ALLOWED)
- Colors: background = `TAC_MISSED_BG` or `TAC_ALLOWED_BG`; border = `TAC_MISSED/0.30` or `TAC_ALLOWED/0.30`; text = `TAC_MISSED` or `TAC_ALLOWED`
- Border: `border border-[TAC_MISSED/0.30]` (inline style since these are dynamic oklch values from theme.ts; the opacity-adjusted border matches the existing TacticMotifChip border pattern)
- Placement: rendered as a trailing element in the same row as the SAN button (sibling `span`, not inside the `<button>`)
- Active state (when this chip's PV is the currently-navigated sideline): add `ring-2 ring-offset-1` in the chip's accent color (same as `ACTIVE_FILTER_RING_CLASS` in theme.ts)
- ARIA: `aria-label="Missed tactic: {motifName}. Click to expand tactic line."` or `"Allowed tactic: {motifName}. Click to expand tactic line."`
- `data-testid`: `flaw-inline-tag-missed-{nodeId}` / `flaw-inline-tag-allowed-{nodeId}`
- Click behavior: fetches the PV for this flaw on-demand (via `useTacticLines`) and inserts it as a Level-1 sideline in the move tree, navigating to the fork position. Clicking again collapses (removes the PV sideline and returns to main line).
- Only one PV sideline may be expanded at a time. Clicking a second chip collapses the first.
- Mobile: inline chips are NOT shown in the horizontal mobile chip rail; tactic PVs on mobile are accessed via the TacticModeOverlay header row (existing pattern) or the chip header above the mobile tree. See Mobile Layout section.

### Modified: VariationTree — two-level nesting

The existing `DesktopTree` supports one active variation (single-level). This phase
extends it to two levels.

Level definitions:

| Level | Description | Indentation | Text color | Connector |
|-------|-------------|-------------|------------|-----------|
| 0 | Main game line | none (`ml-0`) | `text-foreground` | none |
| 1 | PV sideline (tactic PV expanded from inline chip) | `ml-8` (32px) | `text-muted-foreground` | `border-l-2 border-muted/40 pl-2` on the wrapping `<div>` |
| 2 | PV sub-sideline (user forks within a PV line) | `ml-16` (64px) | `text-muted-foreground opacity-80` | `border-l-2 border-muted/30 pl-2` on the wrapping `<div>` |

Active node (any level): `bg-primary text-primary-foreground` — same highlight regardless of level.

Main-line moves after the fork point: `text-muted-foreground` (dimmed) while a sideline
is active (same as the existing variation coloring in DesktopTree).

Desktop variation tree height: matched to the board height. The board renders at a max
width of 480px (its height equals its width since chess boards are square). At the
`lg:w-[508px]` column width the board fills ~480px. The variation tree receives
`max-h-[480px] overflow-y-auto` (matching the board). Use a CSS variable or prop to
sync heights if the board renders smaller on intermediate widths.

Row height: `min-h-[28px]` per row at all levels.

Mobile MobileTree (HorizontalMoveList):
- Level 1 PV: inline in parens after the fork move, as today: `(N. Pv1 Pv2 ...)`.
- Level 2 sub-PV: inline double parens: `((N. sub1 sub2 ...))`.
- No inline flaw-tag chips on mobile — tactic access is via TacticModeOverlay header.

### Modified: TacticModeOverlay — contextual activation

Today the overlay is shown whenever URL has `game_id + flaw_ply` params.

Phase 140 behavior: shown when EITHER of:
1. URL has `game_id + flaw_ply` params (existing tactic-entry, unchanged)
2. A flaw-tag inline chip in the move list has been clicked and its PV sideline is the
   active sideline (contextual)

Hidden when:
- User navigates back to main game line with no active PV sideline
- User collapses the active inline chip

No position change: overlay remains the first element in the right column (above
EngineLines), same as Phase 139. No visual change to the overlay itself — only the
condition that shows/hides it changes.

The `resolvedOrientation` prop maps to the clicked chip's orientation when contextually
activated (not URL-driven). The `onStoredLine` prop reflects whether the user is on
the PV sideline (true) or has forked off it into a sub-sideline (false).

### Modified: EvalChart — relocated to analysis page

The `EvalChart` component (in `frontend/src/components/library/EvalChart.tsx`) is
reused without modification on the `/analysis` page.

Placement on the analysis page:
- Desktop: directly below the board + EvalBar row, in the left column
- Mobile: below the board + EvalBar row (first item below the board stack)

Props passed from `Analysis.tsx`:
- `gameId`: from URL `game_id` param
- `evalSeries`: from the game-by-id fetch (same data `LibraryGameCard` uses)
- `flawMarkers`: from the game-by-id fetch
- `phaseTransitions`: from the game-by-id fetch
- `moves`: from the game-by-id fetch
- `heightClass`: `"h-[120px]"` (fixed, same on desktop and mobile in the analysis context)
- `initialPly`: the `ply` URL param (where the slider starts)
- `onPlyChange`: callback → `goToNode(mainLine[ply])` (syncs board + move list highlight)

The chart also stays in `LibraryGameCard` unchanged — it continues to serve as the
inline preview + ply selector that seeds the Analyze button URL.

### Eval chart slider: parked/dimmed state

When the user is on a sideline (Level-1 PV or Level-2 sub-PV):
- Slider `<input>` gets `disabled` + `opacity-40 cursor-not-allowed pointer-events-none`
- A tooltip on the slider reads: "Return to main game line to scrub"
  (`title` attribute sufficient — no Radix Tooltip needed)
- The chart's eval data remains fully visible (no opacity change on the chart area)
- The slider thumb stays at the fork ply's position on the track

When user returns to the main game line (by navigating back or clicking a main-line node):
- Slider re-enables and syncs to the current main-line ply

### Unified Analyze button

**LibraryGameCard replacement:**

Replace the two-button row (`Explore` + `Analyze position`) with a single button:
- Label: "Analyze"
- Icon: `Activity` (from lucide-react, already imported in `LibraryGameCard`)
- Variant: `brand-outline` (secondary, same as existing Explore button)
- Size: `default` (h-8)
- `data-testid`: `btn-library-game-analyze`
- `aria-label`: `"Analyze game"`
- Navigation: opens `/analysis?game_id={game.game_id}&ply={hoverPly ?? lastEvalPly ?? 0}`
  via React Router `<Link>` (same `asChild` pattern as existing Explore button)
- Disabled state: none — the Analyze button is always enabled for analyzed games
  (for un-analyzed games the button is still shown but navigates to free-play mode)
- Placement: same location as the existing Explore button (right-aligned in card header or flaw column footer, matching existing layout)

**FlawCard replacement:**

Replace the two-button row (`Explore` + `Game`) with a single button:
- Label: "Analyze"
- Icon: `Activity` (from lucide-react; add import if not already present)
- Variant: `brand-outline`
- Size: `default` (h-8)
- `data-testid`: `btn-flaw-analyze`
- `aria-label`: `"Analyze game"`
- Navigation: opens `/analysis?game_id={flaw.game_id}&ply={flaw.ply}`
  via React Router `<Link>` with `asChild` pattern
- The flaw's missed/allowed tag is visible in the move list once the game loads — no
  auto-expand, user clicks the inline chip to see the PV (locked decision)
- The `Game` modal path (Dialog/Drawer + LibraryGameCard inline) is deleted entirely:
  remove `open` state, `useLibraryGame`, Dialog, Drawer, DrawerContent, DrawerHeader,
  DrawerTitle, DrawerClose, LoadError imports

The `Explore` button on the FlawCard and the `Explore` + `Analyze position` buttons on
LibraryGameCard are removed; no other button changes.

---

## Layout Contract

The chess board is the primary visual anchor (left column on desktop, top of the stack on mobile); all other elements (eval chart, move list, engine lines, controls) are subordinate to it.

### Desktop (`lg:flex-row` breakpoint = 1024px)

Left column (existing `lg:w-[508px] shrink-0`):

```
┌─────────────────────────────────┐
│  Board (480px) │ EvalBar (20px) │  ← row: flex-row gap-2
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  EvalChart (120px) + slider     │  ← NEW: replaces where BoardControls was
└─────────────────────────────────┘
```

Right column (existing `flex-1 flex-col gap-4`):

```
┌──────────────────────────────────────────────┐
│  TacticModeOverlay (contextual — may be absent)│
├──────────────────────────────────────────────┤
│  EngineLines (or "Loading engine…" / "off")  │
├──────────────────────────────────────────────┤
│  VariationTree (max-h-[480px] overflow-y-auto)│
│  (height matched to board)                   │
├──────────────────────────────────────────────┤
│  BoardControls  ← MOVED from left column     │
└──────────────────────────────────────────────┘
```

The `BoardControls` `infoSlot` (engine toggle button) moves with the controls to the
right column bottom. The engine toggle button spec is unchanged: `variant="ghost" size="icon"`, `Cpu` icon, `aria-label="Toggle engine"`, `data-testid="btn-analysis-engine-toggle"`.

### Mobile (below `lg` breakpoint)

Stacking order (top to bottom), all full-width:

1. Board + EvalBar (`flex-row gap-2`, full width)
2. EvalChart + slider (`h-[120px]` + slider row)
3. TacticModeOverlay (when contextually active — header row + mobile SAN ladder if applicable)
4. Engine area (loading spinner / "Engine off" / EngineLines)
5. VariationTree (mobile HorizontalMoveList, `h-20`)
6. BoardControls

Bottom padding: `pb-20` (80px) on mobile to clear the fixed navigation bar (existing `pb-20 md:pb-6` pattern — unchanged).

---

## Testid Map

All interactive elements and major layout containers in this phase. Carrying forward all
existing testids without change; adding only what is new.

| Element | `data-testid` | Notes |
|---------|---------------|-------|
| Analysis page root | `analysis-page` | Existing — no change |
| Board container | `analysis-board` | Existing — no change |
| EvalBar | (existing) | Existing — no change |
| **EvalChart on analysis page** | `analysis-eval-chart` | NEW — pass via `gameId` prop or wrap |
| **Eval chart slider** | `analysis-eval-chart-slider` | NEW — set on the `<input type="range">` in EvalChart when rendered in analysis context (via prop or data-testid prop) |
| EngineLines | `analysis-engine-lines` | Existing — no change |
| VariationTree root | `analysis-variation-tree` | Existing — no change |
| VariationTree desktop | `variation-tree-desktop` | Existing — no change |
| VariationTree mobile | `variation-tree-mobile` | Existing — no change |
| Move node button | `variation-node-{nodeId}` | Existing — unchanged across all levels |
| **Level-1 PV indent block** | `variation-pv-section` | NEW — wrapping `<div>` around Level-1 indented rows |
| **Level-2 sub-PV indent block** | `variation-subpv-section` | NEW — wrapping `<div>` around Level-2 indented rows |
| **Inline missed chip** | `flaw-inline-tag-missed-{nodeId}` | NEW — chip `<button>` or `<span>` in move row |
| **Inline allowed chip** | `flaw-inline-tag-allowed-{nodeId}` | NEW — chip `<button>` or `<span>` in move row |
| TacticModeOverlay | `tactic-mode-overlay` | Existing — no change |
| Tactic missed chip | `tactic-toggle-missed` | Existing — no change |
| Tactic allowed chip | `tactic-toggle-allowed` | Existing — no change |
| Engine toggle button | `btn-analysis-engine-toggle` | Existing — moves with BoardControls |
| BoardControls | (existing inner testids) | Existing — no structural change |
| **Analyze button (game card)** | `btn-library-game-analyze` | NEW — replaces `btn-library-game-explore` + `btn-library-game-analyze-position` |
| **Analyze button (flaw card)** | `btn-flaw-analyze` | NEW — replaces `flaw-btn-explore` + `flaw-btn-game` |

ARIA label requirements for new icon-only or abbreviated elements:
- Inline missed chip: `aria-label="Missed tactic: {motifName}. Click to expand tactic line."`
- Inline allowed chip: `aria-label="Allowed tactic: {motifName}. Click to expand tactic line."`
- Analyze button: `aria-label="Analyze game"`

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Analyze button label | "Analyze" |
| Inline missed chip label | "Missed" |
| Inline allowed chip label | "Allowed" |
| Inline chip (when active/expanded) ARIA suffix | "Click to collapse tactic line." |
| Eval chart slider disabled tooltip | "Return to main game line to scrub" |
| Engine loading state | "Loading engine…" (existing — no change) |
| Engine off state | "Engine off" (existing — no change) |
| Empty move list | "No moves yet" (existing — no change) |
| No tactic line available | "Tactic line not available for this flaw." (existing — no change) |
| Variation tree empty (full game, no moves loaded) | "No moves yet" |
| Error loading game for analysis | "Failed to load game. Something went wrong. Please try again in a moment." (follow `isError` branch pattern from CLAUDE.md) |

No destructive actions in this phase (the `Game` modal is deleted silently, not with a
confirmation dialog).

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | Button, Card, Dialog (deleted), Drawer (deleted), Tooltip (existing) | not required |
| Third-party | none | not applicable |

No third-party shadcn registry components are introduced in this phase. The `components.json`
`"registries": {}` field is unchanged.

---

## Key Design Decisions Carried from Upstream

| Decision | Source | Contract Impact |
|----------|--------|----------------|
| No auto-expand PV on game load | `analysis-board-fullgame-refinement.md` | Inline chips are collapsed by default; user must click to expand |
| Slider parks at fork, not scrubs sideline | `analysis-board-fullgame-refinement.md` | Slider disabled + `opacity-40` when on any sideline |
| EvalChart stays in LibraryGameCard | `analysis-board-fullgame-refinement.md` | Reuse component — no modification to EvalChart.tsx itself |
| Game modal deleted entirely | `analysis-board-fullgame-refinement.md` | FlawCard loses Dialog/Drawer imports; no confirmation step |
| Desktop: board height = move list height | `analysis-board-fullgame-refinement.md` | VariationTree `max-h-[480px] overflow-y-auto` |
| Controls below move list (chess.com pattern) | `analysis-board-fullgame-refinement.md` | BoardControls moved to bottom of right column |
| No new backend endpoints (D-4) | REQUIREMENTS.md D-4 | Game-by-id fetch reuses existing endpoint (no schema changes) |
| text-sm minimum everywhere except info tooltips | CLAUDE.md | Inline chip text: `text-sm font-medium` |
| brand-outline = secondary button | CLAUDE.md + button.tsx | Analyze button: `variant="brand-outline"` |
| Semantic colors from theme.ts only | CLAUDE.md | TAC_MISSED/TAC_ALLOWED imported, never hard-coded |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
