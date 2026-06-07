---
phase: 109
slug: per-card-expected-score-eval-chart-games-subtab
status: draft
shadcn_initialized: true
preset: radix-nova / neutral / cssVariables
created: 2026-06-07
amended: 2026-06-07
---

# Phase 109 — UI Design Contract

> Per-Card Expected-Score Eval Chart (Games subtab). Visual and interaction
> contract for the recharts area chart embedded in LibraryGameCard and the
> three-column card restructuring.

---

## Amendment Note (2026-06-07) — D-07/D-08/D-09 Dual-Marker Reconciliation

The original UI-SPEC (created 2026-06-07) specified user-only filled flaw dots.
Following an owner-directed scope expansion (captured in `109-CONTEXT.md` §"SCOPE
EXPANSION"), the flaw-dot contract is amended to cover **both players**:

- **D-07:** Player flaws render as **filled** circles; opponent flaws render as
  **hollow** (stroke-only) circles. Color = severity for both. 6 dot styles total
  (3 severities × player/opponent).
- **D-08:** Tooltip severity line is qualified: "You · Blunder" / "Opponent · Mistake"
  (text-only, since the filled/hollow style isn't visible in a tooltip).
- **D-09:** Density tuning during visual UAT — inaccuracy dots use a smaller radius
  (r=2) than B/M (r=2.5); hollow strokes are thin (strokeWidth=1.5). All flaws for
  both players are shown; no data is dropped.

The `FlawMarker` type gains an `is_user: boolean` discriminator (see Component Contract
section). The Scatter-based approach is replaced by a custom `dot` render prop on a Line
overlay (see Flaw Dots section). All other sections (layout, gradient, dims, ARIA) are
unchanged.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (components.json detected) |
| Preset | radix-nova, baseColor: neutral, cssVariables: true |
| Component library | Radix UI (via shadcn) |
| Icon library | lucide-react |
| Font | Nunito Sans (--font-sans; declared in index.css @theme inline) |

---

## Spacing Scale

Standard 4-point grid. No exceptions for this phase.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, flaw-dot radius |
| sm | 8px | Chart internal padding, gap between chart columns |
| md | 16px | Card horizontal padding (px-4), chart area margins |
| lg | 24px | Section spacing |
| xl | 32px | — |
| 2xl | 48px | — |
| 3xl | 64px | — |

Exceptions: none. The existing card uses `px-4 py-3` (16px / 12px) — preserved.

---

## Typography

Inherits from existing LibraryGameCard and FlawTrendChart patterns.
Two weights only (CLAUDE.md rule). Font-size floor: `text-sm` (14px) for all
body copy; tooltip popovers may use `text-xs` (12px) per CLAUDE.md exception.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body / metadata | 14px (text-sm) | 400 (regular) | 1.5 |
| Badge / label | 14px (text-sm) | 700 (bold) | 1.2 |
| Tooltip body | 12px (text-xs) | 400 (regular) | 1.5 |
| Tooltip label | 12px (text-xs) | 700 (bold) | 1.2 |

Chart axis ticks follow the existing FlawTrendChart pattern: `fontSize: 12`
(recharts SVG attribute, not a Tailwind class). No new size values introduced.

---

## Color

All chart colors sourced from `frontend/src/lib/theme.ts`. No hex literals
or oklch strings may appear in the new component — they must be imported
constants.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `var(--charcoal)` (#161412) | Card body, chart background (charcoal-texture class) |
| Secondary (30%) | `var(--background)` / `var(--card)` (dark mode: oklch 0.205) | Tooltip popup surface, sidebar, nav |
| Accent (10%) | `oklch(0.82 0 0)` (EVAL_CHART_LINE) | ES line stroke |
| Destructive | `var(--destructive)` | — not applicable in this phase |

### Chart-Specific Color Contract

These constants are already declared in `theme.ts` and must be imported, not duplicated:

| Constant | Value | Usage in chart |
|----------|-------|----------------|
| `SEV_BLUNDER` | `oklch(0.58 0.19 25)` | Blunder flaw dots on chart line |
| `SEV_MISTAKE` | `oklch(0.70 0.16 55)` | Mistake flaw dots on chart line |
| `SEV_INACCURACY` | `oklch(0.82 0.13 95)` | Inaccuracy flaw dots on chart line |

### New theme.ts Constants (must be added before implementation)

The following constants do not yet exist in `theme.ts` and must be added there
(never hard-coded in the component):

| Constant Name | Value | Rationale |
|---------------|-------|-----------|
| `EVAL_CHART_AREA_WHITE_AHEAD` | `oklch(0.70 0 0 / 0.35)` | Light grey fill, White advantage region (ES > 0.5); mid-lightness achromatic so it reads neutral and doesn't compete with the flaw-dot hues |
| `EVAL_CHART_AREA_BLACK_AHEAD` | `oklch(0.28 0 0 / 0.45)` | Dark grey fill, Black advantage region (ES < 0.5); deeper dark so the two regions are clearly distinct on the charcoal surface |
| `EVAL_CHART_LINE` | `oklch(0.82 0 0)` | ES line stroke; high-lightness achromatic, reads clearly against charcoal without competing with severity hues |
| `EVAL_CHART_MIDLINE` | `oklch(0.55 0 0)` | 50% reference dashed line; mid-grey, clearly subordinate to the main line |
| `EVAL_CHART_PHASE_LINE` | `oklch(0.55 0 0 / 0.60)` | Vertical phase-transition lines; same hue as midline but with alpha to read as structural guides |

Accent reserved for: flaw dots only (blunder/mistake/inaccuracy severity colors from `theme.ts`). The ES line itself is achromatic.

---

## Layout Contract

### Desktop Three-Column Restructuring

The current `LibraryGameCard` desktop body (`hidden sm:flex gap-3 items-start`)
has two effective columns: [mini-board fixed] [info flex-1] [flaw col flex:0 0 auto].

Phase 109 restructures analyzed-game cards into **three equal thirds** using
CSS grid:

```
desktop body: grid grid-cols-3 gap-3 items-start
  Col 1: mini-board + game info (board fixed-size, info flex-col below or beside)
  Col 2: EvalChart (new middle column, full width of its cell)
  Col 3: severity badges + tag chips (existing flaw content)
```

Concrete Tailwind classes for the desktop body container:
`hidden sm:grid sm:grid-cols-3 sm:gap-3 sm:items-start`

Column widths are equal thirds (`col-span-1` each). No column may have a
fixed-pixel width; the grid enforces equality.

For **unanalyzed** cards (`analysis_state === 'no_engine_analysis'`): the
three-column grid still applies on desktop. Col 2 renders the `NoAnalysisState`
pill (existing component, unchanged) instead of the chart. Col 3 is empty
(zero-height, no content). This avoids a layout shift between analyzed and
unanalyzed cards in the same list.

### Mobile Layout

Mobile (`sm:hidden`) stacks the same three blocks in order:

1. Board + game info row (existing pattern, unchanged)
2. Eval chart (full width) — only for analyzed games; hidden for unanalyzed
3. Severity badges + tag chips (existing flaw block) — only for analyzed games;
   `NoAnalysisState` pill for unanalyzed

```
mobile body: flex flex-col gap-2
  Block 1: flex gap-3 items-start (board left, info right — existing)
  Block 2: <EvalChart /> (full-width, analyzed only)
  Block 3: flex flex-col gap-2 (flaw content — existing)
```

### Chart Dimensions

| Context | Height |
|---------|--------|
| Desktop (col 2 of card grid) | 96px (`h-24`) |
| Mobile (full-width block) | 80px (`h-20`) |

These are deliberately compact — sparkline-level information density, not a
full analytics chart. No Y-axis labels, no X-axis ticks (use margins only).

---

## Component Contract: EvalChart

New component: `frontend/src/components/library/EvalChart.tsx`

### Props

```typescript
interface EvalChartProps {
  gameId: number;
  evalSeries: EvalPoint[];        // per-ply series from GameFlawCard.eval_series
  flawMarkers: FlawMarker[];      // user's flaws, from GameFlawCard.flaw_markers
  phaseTransitions: PhaseTransitions; // ply indices for phase boundaries
  userColor: 'white' | 'black';  // for tooltip sign convention display
}

interface EvalPoint {
  ply: number;
  es: number | null;              // null = missing eval (line-gap)
  eval_cp: number | null;         // raw cp for tooltip display
  eval_mate: number | null;       // mate-in-N for tooltip (signed, white-perspective)
}

interface FlawMarker {
  ply: number;
  severity: 'blunder' | 'mistake' | 'inaccuracy';
  tags: string[];                 // flaw tags for tooltip (empty for inaccuracies — D-03)
  is_user: boolean;               // true = filled dot (player); false = hollow dot (opponent) — D-07
}

interface PhaseTransitions {
  middlegame_ply: number | null;  // null = phase never reached
  endgame_ply: number | null;     // null = phase never reached
}
```

These types extend `GameFlawCard` in `frontend/src/types/library.ts`. The
backend plan must add `eval_series`, `flaw_markers`, and `phase_transitions`
fields to the `GameFlawCard` response.

### Recharts Architecture

Use `ComposedChart` (recharts) inside `ChartContainer` — not bare `AreaChart` —
so that the invisible `<Line dot={...}>` flaw-dot overlay can be composed alongside
the `<Area>`. Follow the established `FlawTrendChart`/`EndgameClockDiffOverTimeChart`
pattern:

- `isAnimationActive={false}` on all data series — mandatory on charcoal surface
- No `CartesianGrid` — charcoal texture is the grid signal
- No X-axis ticks, no Y-axis (both hidden) — compact sparkline mode
- `ChartContainer config={{}} className="w-full h-24"` (desktop) / `h-20` (mobile)
- Chart margin: `{ top: 4, right: 4, left: 4, bottom: 4 }` — minimal bleed

### Area Fill Strategy (Two-Region Shading)

The ES chart requires two fill colors: light grey when White is ahead (ES > 0.5),
dark grey when Black is ahead (ES < 0.5). Use a **vertical linearGradient with
a hard stop at the 50% value converted to a percentage of the Y-axis domain**.

Since the Y-axis domain is fixed [0, 1] and the midline is at 0.5, the midpoint
is always at 50% of chart height. Implement as:

```
<defs>
  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
    {/* Top half: White-ahead region (y=0 at top, y=0.5 in the middle) */}
    <stop offset="0%"   stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    {/* Hard color switch at the midline */}
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
    <stop offset="100%" stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
  </linearGradient>
</defs>
<Area
  type="monotone"
  dataKey="es"
  stroke={EVAL_CHART_LINE}
  strokeWidth={1.5}
  fill={`url(#${gradientId})`}
  fillOpacity={1}
  isAnimationActive={false}
  connectNulls={false}
/>
```

The Area fills the region between the ES line and the bottom of the chart (y=0).
This means:
- When ES > 0.5: the filled area between the line and 0 spans across the midline;
  the top portion (above 0.5) is light grey, the bottom portion (below 0.5) is dark grey.
- The visual distinction comes from the gradient color split, not from two separate Area elements.

**Note on missing-eval plies:** `connectNulls={false}` produces a line gap at
null entries. This is the correct behavior — broken lines signal genuine data
absence, not interpolation. At the ≥90% coverage gate, gaps should be rare
(≤10% of plies). This is the OPEN UI decision resolved here: break the line,
do not connect across nulls.

### Midline Reference Line

```
<ReferenceLine
  y={0.5}
  stroke={EVAL_CHART_MIDLINE}
  strokeWidth={1}
  strokeDasharray="2 2"
  ifOverflow="hidden"
/>
```

### Phase-Transition Vertical Lines

At most two `<ReferenceLine>` elements (middlegame + endgame). A transition
that never occurs draws no line. The opening boundary (ply 0) is implicit and
does **not** get a line — the chart starts at ply 0 by definition (D-06 confirmed).
A line at the leftmost pixel is invisible and redundant; never add one for ply 0.

```
{phaseTransitions.middlegame_ply !== null && (
  <ReferenceLine
    x={phaseTransitions.middlegame_ply}
    stroke={EVAL_CHART_PHASE_LINE}
    strokeWidth={1}
    strokeDasharray="3 2"
  />
)}
{phaseTransitions.endgame_ply !== null && (
  <ReferenceLine
    x={phaseTransitions.endgame_ply}
    stroke={EVAL_CHART_PHASE_LINE}
    strokeWidth={1}
    strokeDasharray="3 2"
  />
)}
```

### Flaw Dots (Both Players — Amended 2026-06-07 per D-07/D-08/D-09)

Render flaw markers for **both players** using a custom `dot` render prop on an
invisible `<Line>` overlay inside `ComposedChart`. This replaces the previously
specified `<Scatter>` approach — recharts 3.8.1 Scatter uses area-based `size`,
not radius `r`, making pixel-precise sizing unreliable. The `<Line dot={...}>` pattern
is the established project pattern (see `EndgameClockDiffOverTimeChart.tsx`).

**Dot styles — 6 total (3 severities × player/opponent):**

| Marker | fill | stroke | strokeWidth | Radius |
|--------|------|--------|-------------|--------|
| Player blunder | `SEV_BLUNDER` | — | — | 2.5 |
| Player mistake | `SEV_MISTAKE` | — | — | 2.5 |
| Player inaccuracy | `SEV_INACCURACY` | — | — | 2 |
| Opponent blunder | `"none"` | `SEV_BLUNDER` | 1.5 | 2.5 |
| Opponent mistake | `"none"` | `SEV_MISTAKE` | 1.5 | 2.5 |
| Opponent inaccuracy | `"none"` | `SEV_INACCURACY` | 1.5 | 2 |

- **Filled circle** (`fill = severity color`): when `marker.is_user === true` (player's move)
- **Hollow circle** (`fill="none"`, `stroke = severity color`, `strokeWidth=1.5`):
  when `marker.is_user === false` (opponent's move). Use `fill="none"` explicitly —
  do NOT omit the fill attribute (SVG default is black, not transparent).

Build a ply-keyed `Map` from `flawMarkers` before rendering for O(1) lookup inside
the dot render prop. Return an empty `<g key="...">` (not `null`) for plies without
a marker (avoids React key warnings — recharts 3.8.1 Pitfall 7).

```tsx
// Inside ComposedChart — invisible line overlay for flaw dot rendering
<Line
  type="monotone"
  dataKey="es"
  stroke="none"
  dot={customDotRenderer}
  activeDot={false}
  connectNulls={false}
  isAnimationActive={false}
/>
```

**Density tuning (D-09):** The compact 80–96px sparkline can get dense with both players'
inaccuracies. Inaccuracy dots are intentionally smaller (r=2) than B/M (r=2.5) and hollow
strokes are thin (strokeWidth=1.5). Executor tunes further during visual UAT if needed.

### Tooltip Contract (Amended 2026-06-07 per D-08)

Use `<ChartTooltip>` with a custom `content` render prop. Trigger on hover/tap.

**Tooltip layout (text-xs throughout — opt-in popover surface exception):**

```
┌────────────────────────────────────────┐
│ Ply 24                          [bold] │
│ +1.23 pawns (White ahead)       [body] │  ← eval_cp display
│ OR: Mate in 3 (White)                  │  ← when eval_mate present
│                                        │
│ You · Blunder                   [red]  │  ← player flaw (is_user=true)
│   tag1, tag2                  [muted]  │  ← B/M only; inaccuracy shows no tags
│ OR: Opponent · Mistake          [org]  │  ← opponent flaw (is_user=false)
└────────────────────────────────────────┘
```

Tooltip copy rules:
- Eval display: `eval_cp / 100` as `+X.XX pawns` (positive = White ahead) or
  `-X.XX pawns` (negative = Black ahead). Always white-perspective, always
  signed. Round to 2 decimal places.
- When `eval_mate !== null`: show `Mate in {Math.abs(eval_mate)} ({side})` where
  side is "White" if `eval_mate > 0`, "Black" if `eval_mate < 0`. Never show
  eval_cp when eval_mate is present.
- When the ply has a flaw marker (either player): show the severity line qualified
  with player identity — **"You · {Severity}"** when `marker.is_user === true`,
  **"Opponent · {Severity}"** when `marker.is_user === false`. Colored by severity
  (`SEV_BLUNDER` / `SEV_MISTAKE` / `SEV_INACCURACY`).
- For **B/M markers** (either player): append comma-joined tag list in
  `text-muted-foreground` below the severity line when tags are non-empty (D-03).
- For **inaccuracy markers** (either player): show severity + eval only. **No tags**
  — inaccuracy markers always have empty `tags: []` from the backend (D-03).
- Tooltip container: `rounded-lg border border-border/50 bg-background px-3 py-2
  text-xs shadow-xl space-y-1` (matches existing chart tooltip pattern in project).

### data-testid / ARIA Contract

| Element | data-testid | ARIA |
|---------|-------------|------|
| Chart container div | `eval-chart-{gameId}` | `aria-label="Expected score chart for game {gameId}"` |
| Phase middlegame ReferenceLine | — | `aria-hidden="true"` (decorative) |
| Phase endgame ReferenceLine | — | `aria-hidden="true"` (decorative) |
| Midline ReferenceLine | — | `aria-hidden="true"` (decorative) |

The chart itself is a `<div role="img" aria-label="...">` wrapper (via
`ChartContainer`) — no further interactive ARIA needed on the SVG internals.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| No-chart state (unanalyzed card, col 2) | Existing `NoAnalysisState` component — "No engine analysis" — unchanged |
| Tooltip ply label | `Ply {N}` |
| Tooltip eval (cp) | `+{X.XX} pawns` / `-{X.XX} pawns` |
| Tooltip eval (mate, White) | `Mate in {N} (White)` |
| Tooltip eval (mate, Black) | `Mate in {N} (Black)` |
| Tooltip flaw severity label | `Blunder` / `Mistake` / `Inaccuracy` |
| Chart ARIA label | `Expected score chart for game {gameId}` |
| Empty eval series (no plies) | Chart not rendered; `NoAnalysisState` pill covers the column |

No primary CTA in this phase (no user action triggers; the chart is display-only).
No destructive actions in this phase.

---

## Backend Payload Contract (inline in GameFlawCard)

The following fields are added to `GameFlawCard` (no new endpoint, no migration).
The TypeScript types in `library.ts` must be extended to match.

```typescript
// Added to GameFlawCard (existing type in frontend/src/types/library.ts)
eval_series: EvalPoint[] | null;        // null for unanalyzed games
flaw_markers: FlawMarker[] | null;      // null for unanalyzed games
phase_transitions: PhaseTransitions | null; // null for unanalyzed games
```

Where `EvalPoint`, `FlawMarker`, and `PhaseTransitions` are the types defined
in the Component Contract section above.

The backend delivers the ES series **from White's perspective** (sign convention:
positive ES = White ahead). The frontend renders it as-is (no sign flip). The
tooltip display labels the perspective explicitly ("White ahead" / "Black ahead").

---

## Interaction States

| State | Visual |
|-------|--------|
| Analyzed game, hover/tap on chart | Tooltip appears per ChartTooltip pattern; active dot enlarges (recharts default `activeDot` behavior) |
| Analyzed game, hover/tap on flaw dot | Tooltip shows eval + flaw severity + tags |
| Analyzed game, no hover | Chart renders with static area fill, flaw dots, phase lines |
| Unanalyzed game, col 2 | NoAnalysisState pill centered in col 2 |
| Missing eval ply (null) | Line breaks (connectNulls=false); no fill segment; gap is silent |
| Empty eval_series (all null or []) | Column renders NoAnalysisState pill (same as unanalyzed) |
| Mobile | Same three blocks stacked; chart is full-width at h-20 |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | ChartContainer, ChartTooltip (existing imports) | not required |

No third-party registries declared. All chart primitives are recharts (already
a project dependency used in FlawTrendChart, EndgameScoreOverTimeChart, etc.).

---

## Pre-Population Sources

| Source | Decisions Pre-Populated |
|--------|------------------------|
| ROADMAP.md Phase 109 spec | Chart type (AreaChart), three-equal-thirds layout, flaw dot colors, phase lines, tooltip contract, midline at 50%, white-perspective, missing-eval gap handling (OPEN — resolved to break line) |
| REQUIREMENTS.md LIBG-10 | All success criteria above map 1:1 to contract sections |
| `frontend/src/lib/theme.ts` (read) | SEV_BLUNDER/MISTAKE/INACCURACY values, no-new-color rule, all chart colors from theme |
| `frontend/src/components/results/LibraryGameCard.tsx` (read) | Existing two-column layout confirmed; three-column grid migration specified |
| `frontend/src/components/library/FlawTrendChart.tsx` (read) | Recharts pattern: isAnimationActive=false, ChartContainer, custom ChartTooltip, no CartesianGrid |
| `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` (read) | ReferenceLine pattern, ComposedChart with Area + Line, connectNulls=false |
| `frontend/src/index.css` (read) | charcoal-texture class, font (Nunito Sans), CSS variable names |
| `frontend/components.json` (read) | shadcn radix-nova preset, lucide icons confirmed |
| User input | none required — all contract fields answered by upstream artifacts or codebase inspection |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
