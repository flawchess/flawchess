# Phase 34: Theme Improvements - Research

**Researched:** 2026-03-28
**Domain:** React/TypeScript frontend — Tailwind v4 CSS variables, SVG noise textures, Recharts bar styling, shadcn/Radix Tabs
**Confidence:** HIGH

## Summary

This phase is entirely frontend UI work with no backend changes. All four technical research areas (SVG noise texture, Tailwind v4 CSS variables, Recharts stacked bar rounding, shadcn tabs active state) are well-understood from official docs and code inspection. The existing codebase is well-structured for these changes — `@theme inline` is already in place, `tabs.tsx` uses CVA variants, and `theme.ts` is the established JS export hub.

One important constraint: the project uses Recharts 2.15.4. The `BarStack` component (which cleanly rounds only outer stack corners) is a Recharts 3.x feature and is NOT available. Rounding outer corners of stacked WDL bars in `WDLBarChart.tsx` requires a custom shape or Cell-based conditional radius workaround in 2.x.

**Primary recommendation:** Add `--color-brand-brown` and `--color-charcoal` to the `@theme inline` block in `index.css`, implement noise texture as a CSS custom property with a `::before` pseudo-element pattern, and use a new `brand` variant in `tabs.tsx` for the active subtab style.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Container Styling**
- D-01: Charcoal background with SVG feTurbulence noise texture applied to specific content sections — NOT full-page panels
- D-02: Implementation via CSS variable + Tailwind utility class (e.g. `bg-charcoal`) — not a wrapper component
- D-03: Charcoal containers apply to: endgame statistics sections, endgame concept accordion, game cards, bookmark cards, subtab navigation bar, import page cards/containers
- D-04: Sidebar filter panel does NOT get a card container — uses flat background `#171513` (dark brown), distinct from main content background

**Filter Button Layout**
- D-05: Filter buttons should be spaced horizontally across the full sidebar width — Claude's discretion on whether to use equal-width grid or flex-grow
- D-06: Keep the two existing filter patterns separate (raw buttons for Time Control/Platform, ToggleGroup for Rated/Opponent) — just fix the spacing, don't unify

**Chart Consistency**
- D-07: All WDL charts use rounded corners — apply rounded corners to Recharts `WDLBarChart` bars to match custom `WDLBar` and `EndgameWDLChart` components
- D-08: Glass overlay stays on custom WDL bars only — do NOT add glass effect to Recharts bars. Just match corners and theme colors.

**Subtab Highlighting**
- D-09: Active subtab gets brand brown (#8B5E3C) as background fill with white text — bold, clear active state
- D-10: Subtab navigation bar itself uses charcoal background (per D-03)

**Navigation Header**
- D-11: Active main navigation tab highlighted with a lighter background spanning the full header height
- D-12: Remove the white border from the header
- D-13: Logo and "FlawChess" text both link to the homepage

**Collapsible Sections**
- D-14: All collapsible sections (Dashboard, Openings, Endgames) use charcoal background consistently — no more divergent styling between pages
- D-15: The entire collapsible (header + expanded content) is one charcoal container with its own padding — not just the header getting charcoal

**CSS Variable Migration**
- D-16: Migrate brand brown from `PRIMARY_BUTTON_CLASS` hardcoded hex in theme.ts to a CSS variable in index.css's `@theme inline` block — enables Tailwind utility usage (`bg-brand` etc.) without hardcoded brackets
- D-17: WDL and gauge colors remain in theme.ts as JS constants (oklch values used in inline styles) — no need to migrate these to CSS variables

### Claude's Discretion
- Filter button layout approach (grid vs flex-grow) — pick what looks best given button counts per group
- WDL bar height normalization (h-5 vs h-6) — unify if it improves consistency
- Exact charcoal color value — pick something that works with the noise texture and contrasts with the `#171513` sidebar

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| THEME-01 | User sees all visual constants (container colors, spacing, chart styles) centralized in theme.ts and CSS variables | D-16/D-17: brand brown migrated to CSS variable; WDL/gauge stays in theme.ts JS constants |
| THEME-02 | User sees content containers with charcoal background and subtle SVG feTurbulence noise texture | SVG data URI pattern + Tailwind utility class via `@theme inline` |
| THEME-03 | User sees filter buttons in sidebar spaced horizontally across full available width | `flex-1` on raw buttons; `w-full` on ToggleGroup components |
| THEME-04 | User sees consistent WDL chart styling (unified corners and rendering) across all chart types | Recharts 2.x Cell-based radius workaround for outer corners only |
| THEME-05 | User sees clear visual highlighting on the active subtab | New `brand` variant in `tabs.tsx` using `data-active:bg-[--color-brand-brown]` |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Tailwind CSS | 4.2.x | Utility-first CSS — `@theme inline` for brand variables | Already configured in `index.css` |
| class-variance-authority (cva) | already installed | Variant-based class composition for shadcn | Already used in `tabs.tsx` |
| Recharts | 2.15.4 | Stacked bar charts in `WDLBarChart.tsx` | No upgrade needed — workaround for stacked radius |

**No new packages required.** All changes are CSS, component modification, and Tailwind configuration only.

---

## Architecture Patterns

### Pattern 1: Tailwind v4 CSS Variable Registration

**What:** In Tailwind v4, the `@theme inline` block in `index.css` registers CSS variables as Tailwind utility classes. Variables prefixed with `--color-` become `bg-*`, `text-*`, `border-*` utilities.

**`@theme inline` vs `@theme`:** Use `@theme inline` (already in use) when variables reference other CSS variables (i.e., `var(--something)` indirection). The `inline` keyword ensures the utility class emits `color: var(--color-brand-brown)` rather than double-indirecting. This matters for referencing `:root` / `.dark` theme vars.

**How to add brand brown and charcoal:**

Step 1 — Define CSS custom properties in `:root` (and optionally `.dark`):
```css
/* in :root block */
--brand-brown: #8B5E3C;
--brand-brown-hover: #6B4226;
--charcoal: #2A2520;  /* to be chosen — must contrast with #171513 sidebar */
```

Step 2 — Register in `@theme inline` block:
```css
@theme inline {
  /* existing entries ... */
  --color-brand-brown: var(--brand-brown);
  --color-brand-brown-hover: var(--brand-brown-hover);
  --color-charcoal: var(--charcoal);
}
```

This creates `bg-brand-brown`, `hover:bg-brand-brown-hover`, `text-brand-brown`, `bg-charcoal`, etc. as standard Tailwind utilities.

**After migration**, `PRIMARY_BUTTON_CLASS` in `theme.ts` becomes:
```typescript
export const PRIMARY_BUTTON_CLASS = 'bg-brand-brown hover:bg-brand-brown-hover text-white';
```
No more hardcoded hex in brackets.

**Confidence:** HIGH — verified against official Tailwind v4 docs and confirmed with the existing `index.css` pattern (e.g., `--color-sidebar: var(--sidebar)` already follows this exact pattern).

---

### Pattern 2: SVG feTurbulence Noise Texture

**What:** A lightweight repeating noise texture using an SVG `feFurbulence` filter embedded as a CSS `background-image` data URI. Applied via a `::before` pseudo-element layered on top of a solid charcoal background color.

**Why pseudo-element:** The texture must overlay the background without obscuring content. Using `::before` with `pointer-events: none` and `position: absolute` achieves this. The container must have `position: relative` and `overflow: hidden`.

**SVG data URI pattern (verified from official MDN + ibelick.com):**
```css
.bg-charcoal-texture {
  position: relative;
  overflow: hidden;
  background-color: var(--charcoal);
}
.bg-charcoal-texture::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 200px;
  opacity: 0.06;  /* subtle — adjust to taste */
}
```

**Key SVG parameters:**
- `type='fractalNoise'` — smooth cloud-like grain (not turbulence which creates ripple lines)
- `baseFrequency='0.65'` — controls grain density; higher = finer grain
- `numOctaves='3'` — detail level; 3 is a good balance
- `stitchTiles='stitch'` — ensures the tile seams are invisible when repeating
- `opacity: 0.06` — very subtle; charcoal is dark, strong noise would look dirty

**Defining as a CSS utility class for Tailwind v4:**
Since Tailwind v4 doesn't have a simple way to add pseudo-element utilities via `@theme`, this should be defined as a plain CSS class in `@layer components` in `index.css`:

```css
@layer components {
  .charcoal-texture {
    position: relative;
    overflow: hidden;
    background-color: var(--charcoal);
  }
  .charcoal-texture::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: url("data:image/svg+xml,...");
    background-repeat: repeat;
    background-size: 200px;
    opacity: 0.06;
  }
}
```

Usage: `<div className="charcoal-texture rounded-md p-4">` with `bg-charcoal` as a composable fallback where the pseudo-element isn't needed.

**Confidence:** HIGH — SVG feTurbulence is a well-documented browser feature (MDN); CSS data URI embedding is standard; pseudo-element overlay pattern is widely used.

---

### Pattern 3: Filter Button Full-Width Layout

**What:** Time Control (4 buttons: Bullet, Blitz, Rapid, Classical) and Platform (2 buttons: Chess.com, Lichess) groups should span the full sidebar width.

**Current state:** `FilterPanel.tsx` uses `<div className="flex flex-wrap gap-1">` with unsized buttons. Buttons are content-width, leaving unused space.

**Recommended approach (Claude's discretion — D-05):**

For Time Control (4 buttons, equal labels): use `grid grid-cols-4` — each button gets exactly 25% width regardless of label length.
```jsx
<div className="grid grid-cols-4 gap-1">
  {TIME_CONTROLS.map((tc) => (
    <button key={tc} className={cn('rounded border h-11 sm:h-7 text-xs ...', ...)} />
  ))}
</div>
```

For Platform (2 buttons): use `grid grid-cols-2` — equal halves.

For ToggleGroup components (Rated, Opponent): ToggleGroup has `w-fit` by default. Pass `className="w-full"` to the ToggleGroup and `className="flex-1"` to each ToggleGroupItem:
```jsx
<ToggleGroup className="w-full" ...>
  <ToggleGroupItem className="flex-1" ...>All</ToggleGroupItem>
  ...
</ToggleGroup>
```

**Confidence:** HIGH — verified by reading the ToggleGroup source (`w-fit` default confirmed at line 44 of `toggle-group.tsx`).

---

### Pattern 4: Recharts Stacked Bar Corner Rounding (2.15.4)

**What:** `WDLBarChart.tsx` renders three stacked `Bar` components (`win_pct`, `draw_pct`, `loss_pct`) with `stackId="wdl"`. Currently all have `radius={[0,0,0,0]}` (no rounding). Goal is outer corner rounding: bottom-left/bottom-right on the bottom bar, top-left/top-right on the top bar.

**Key constraint:** `BarStack` component (the clean solution) was introduced in Recharts 3.x. The project uses 2.15.4 — BarStack does NOT exist.

**Radius prop format in 2.x:** `radius?: number | [topLeft, topRight, bottomRight, bottomLeft]`

**Problem with naive approach:** Applying `radius={[4,4,0,0]}` on the top bar AND `radius={[0,0,4,4]}` on the bottom bar works for rows where all three segments exist. But when `win_pct=0` or `loss_pct=0`, the "outermost" bar shifts. Applying radius to a bar that doesn't render causes no visual problem — Recharts skips zero-value bars — but a middle bar could end up as the actual outermost when flanking bars are zero.

**For a WDL chart (win/draw/loss always has values unless total=0):** The `WDLBarChart` already filters out bookmarks with `total === 0` before rendering. Since we're dealing with meaningful percentages, all three bars will typically be present. However, draws at exactly 0% are possible (e.g., bulletins rarely draw).

**Practical approach for 2.15.4:**

Option A — Static outer-only radius (simple, good enough for typical WDL distributions):
```jsx
<Bar xAxisId="pct" dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)" radius={[4,4,0,0]} />
<Bar xAxisId="pct" dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" />
<Bar xAxisId="pct" dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)" radius={[0,0,4,4]} />
```
Trade-off: if `win_pct=0`, the draw bar becomes the topmost but won't have radius. Acceptable for this use case since full zeroes are filtered out.

Option B — Cell-based conditional radius per row (robust):
```jsx
<Bar dataKey="win_pct" ...>
  {data.map((entry) => (
    <Cell key={entry.label} radius={entry.win_pct > 0 && entry.loss_pct === 0 && entry.draw_pct === 0 ? [4,4,4,4] : entry.win_pct > 0 ? [4,4,0,0] : [0,0,0,0]} />
  ))}
</Bar>
```
Trade-off: verbose, but handles edge cases correctly.

**Recommendation:** Start with Option A (static radius on top and bottom bars) since WDL values are always present in filtered data. Add a comment noting the limitation. This matches the rounding behavior of `WDLBar.tsx` (which uses `overflow-hidden rounded` on the container div — no per-segment control needed) and `EndgameWDLChart.tsx` (same container approach, `h-5 w-full overflow-hidden rounded`).

**Insight on h-5 vs h-6 normalization (D-05, discretion):** `WDLBar.tsx` uses `h-6`, `EndgameWDLChart.tsx` uses `h-5`. Unifying to `h-6` would give the bars a bit more presence. Recharts bars have their height determined by the chart layout, not these CSS classes. The `h-5`/`h-6` inconsistency only affects the custom bar components.

**Confidence:** MEDIUM — based on Recharts 2.x GitHub issues (#1888, #3887) and reading the installed type definitions. BarStack absence confirmed by direct filesystem check.

---

### Pattern 5: Charcoal Color Selection

**Recommended charcoal value:** `#2A2520`

- Sidebar (`#171513`): very dark brown-black
- Background (`oklch(0.145 0 0)` in `.dark`): near-black neutral ≈ `#1a1a1a`
- Charcoal at `#2A2520` sits between these — darker than standard card (`oklch(0.205 0 0)` ≈ `#2d2d2d`) but lighter than sidebar, with a warm brown undertone that complements the brand brown theme.

If `#2A2520` lacks sufficient contrast from page background, try `#252018` (slightly warmer) or `#2C2822` (slightly lighter).

**Confidence:** LOW (aesthetic judgment) — exact value is Claude's discretion per D-05 and should be validated visually.

---

### Pattern 6: shadcn Tabs Active State — Brand Variant

**What:** Add a `brand` variant to `TabsList` and corresponding active state override in `TabsTrigger` so `data-active` sets brand brown background + white text.

**Existing active state selector:** The current `tabs.tsx` uses `data-active:bg-background` for the `default` variant. The component uses custom `data-active` (not Radix's `data-state="active"`) — this is confirmed by reading the code.

**Approach:** Add a `brand` variant to `tabsListVariants` and override the trigger's active state using group-based variant targeting:

In `tabsListVariants` CVA:
```typescript
variants: {
  variant: {
    default: "bg-muted",
    line: "gap-1 bg-transparent",
    brand: "bg-charcoal gap-0",  // charcoal background for the tab bar
  },
}
```

In `TabsTrigger`, add a new line to the `cn(...)` call:
```typescript
"group-data-[variant=brand]/tabs-list:data-active:bg-brand-brown group-data-[variant=brand]/tabs-list:data-active:text-white group-data-[variant=brand]/tabs-list:data-active:border-transparent",
```

This follows the exact same pattern already used in the component:
```typescript
"group-data-[variant=default]/tabs-list:data-active:shadow-sm"
"group-data-[variant=line]/tabs-list:data-active:shadow-none"
```

Usage at call sites:
```jsx
<TabsList variant="brand" className="w-full">
  <TabsTrigger value="statistics">Statistics</TabsTrigger>
  <TabsTrigger value="games">Games</TabsTrigger>
</TabsList>
```

**Confidence:** HIGH — pattern is directly confirmed by reading the existing `tabs.tsx` implementation. The group-based variant targeting is already established in the component.

---

### Pattern 7: Collapsible Unified Container

**What:** Wrap the entire `<Collapsible>` (trigger + content) in a `<div className="charcoal-texture rounded-md">` container so the charcoal background applies to both header and expanded content as one unit.

**Current state:** Collapsible triggers have `bg-muted/50` (Openings) or no background (Dashboard). Content is unstyled.

**Target structure:**
```jsx
<div className="charcoal-texture rounded-md p-2">
  <Collapsible open={open} onOpenChange={setOpen}>
    <CollapsibleTrigger asChild>
      <Button variant="ghost" size="sm" className="w-full justify-between text-sm font-medium">
        Section title
        {open ? <ChevronUp /> : <ChevronDown />}
      </Button>
    </CollapsibleTrigger>
    <CollapsibleContent>
      <div className="pt-2">
        {/* content */}
      </div>
    </CollapsibleContent>
  </Collapsible>
</div>
```

The trigger button should use `variant="ghost"` without its own background — the container provides the charcoal. Remove `bg-muted/50`, `border border-border/40` from trigger buttons.

**Confidence:** HIGH — straightforward structural change confirmed by reading page code.

---

### Pattern 8: Navigation Header Changes

**Active tab highlight (D-11):**

Current: `border-b-2 border-primary rounded-none font-medium` — only an underline indicator.
Target: lighter background spanning full header height.

The `NavHeader` header has `py-1` on the inner div, making the header height determined by the button content. To span full height, use `h-full self-stretch` on the Button plus a background:

```jsx
className={
  isActive(to, location.pathname)
    ? 'self-stretch rounded-none font-medium bg-white/10'  // subtle light tint
    : 'self-stretch rounded-none text-muted-foreground'
}
```

`bg-white/10` over a dark background creates a subtle highlight without being garish. The `border-b-2` underline can be removed (replaced by full-height highlight).

**Remove header border (D-12):** Remove `border-b border-border` from the `<header>` element in `NavHeader()` and `MobileHeader()` in `App.tsx`.

**Logo links to homepage (D-13):** In `NavHeader()`, wrap `<img>` + `<span>FlawChess</span>` in a `<Link to="/">`. Currently neither is a link in the nav header. In `MobileHeader()`, wrap the brand span in a `<Link to="/">`.

**Confidence:** HIGH — confirmed by reading `App.tsx` NavHeader and MobileHeader implementations.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Noise texture image | PNG/WebP asset file | SVG feTurbulence data URI | No extra HTTP request, scales infinitely, ~500 bytes |
| Brand color variants | New component with hardcoded colors | CSS variable + `@theme inline` registration | Enables Tailwind utilities everywhere, single source of truth |
| Tab active state logic | JS-based class toggling | CVA variant + `data-active` CSS selector | Already how the component works |
| Stacked bar rounding | Custom SVG path renderer | `radius` prop on outermost Bar components | Recharts handles SVG path; only needs outer bars targeted |

---

## Common Pitfalls

### Pitfall 1: Noise Texture Covering Content
**What goes wrong:** Container has `position: static` (default) — the `::before` pseudo-element with `position: absolute` escapes the container.
**Why it happens:** `position: absolute` is relative to the nearest positioned ancestor.
**How to avoid:** The `.charcoal-texture` CSS class must include `position: relative`. The container also needs `overflow: hidden` to clip the texture at border-radius.
**Warning signs:** Noise texture bleeds outside rounded corners, or content underneath adjacent elements gets covered.

### Pitfall 2: Recharts Bar Radius Visual Artifacts in Stacked Mode
**What goes wrong:** Applying `radius` to a middle bar (e.g., `draw_pct`) creates a gap between segments where the rounded corners pull away from adjacent bars.
**Why it happens:** Recharts applies the radius to the individual SVG rectangle, not just the outer edges of the stack.
**How to avoid:** Only apply radius to the first bar (bottom corners) and last bar (top corners). Leave middle bars with `radius={0}` or no radius prop.
**Warning signs:** White/background-colored gaps visible between WDL segments in the chart.

### Pitfall 3: Tailwind v4 @theme inline — Dark Mode Variables
**What goes wrong:** Adding `--color-charcoal: #2A2520` directly to `@theme inline` hardcodes the value and bypasses dark mode switching.
**Why it happens:** The project's existing pattern defines values in `:root` / `.dark` blocks and references them via `var()` in `@theme inline`. Bypassing this pattern breaks dark mode (though the app is dark-only, it's still good practice).
**How to avoid:** Define the raw color values in `:root` (or `.dark`), then reference via `var(--charcoal)` in `@theme inline`. Follow the existing `--color-sidebar: var(--sidebar)` pattern exactly.

### Pitfall 4: ToggleGroup Items Not Filling Width
**What goes wrong:** Adding `className="w-full"` to `ToggleGroup` but items don't expand.
**Why it happens:** ToggleGroupItem has `shrink-0` by default (see `toggle-group.tsx` line 75). Items need explicit `flex-1` to grow.
**How to avoid:** Pass `className="flex-1"` on each `ToggleGroupItem`.

### Pitfall 5: Mobile-only vs Desktop-only Sidebar — D-06 Filter Layout
**What goes wrong:** Fixing the desktop sidebar filter layout but missing the mobile collapsible `FilterPanel` instance.
**Why it happens:** `FilterPanel` is rendered twice per page — once in the desktop sidebar column, once in the mobile `<Collapsible>`. Both call the same component, so changes to `FilterPanel.tsx` propagate to both.
**How to avoid:** Changes to `FilterPanel.tsx` automatically fix both layouts. No separate mobile/desktop handling needed.

### Pitfall 6: Tabs Component data-active vs data-state
**What goes wrong:** Using `data-[state=active]` Tailwind selector instead of `data-active`.
**Why it happens:** Radix UI primitives normally expose `data-state="active"`, but the project's `tabs.tsx` is a customized shadcn build that uses `data-active` boolean attribute instead. Confirmed by reading the actual component source.
**How to avoid:** Use `data-active:` prefix in Tailwind classes (already established in tabs.tsx). Do NOT use `data-[state=active]:`.

---

## Code Examples

### Adding CSS Variables to index.css (THEME-01, D-16)

```css
/* Source: verified from existing index.css pattern */
:root {
    /* existing vars ... */

    /* Brand colors */
    --brand-brown: #8B5E3C;
    --brand-brown-hover: #6B4226;

    /* Container colors */
    --charcoal: #2A2520;
    --sidebar-bg: #171513;
}

@theme inline {
    /* existing entries ... */

    /* Brand and container utilities */
    --color-brand-brown: var(--brand-brown);
    --color-brand-brown-hover: var(--brand-brown-hover);
    --color-charcoal: var(--charcoal);
}
```

After this, `PRIMARY_BUTTON_CLASS` in `theme.ts` becomes:
```typescript
export const PRIMARY_BUTTON_CLASS = 'bg-brand-brown hover:bg-brand-brown-hover text-white';
```

### Noise Texture CSS Class (THEME-02)

```css
/* Source: ibelick.com pattern + MDN feTurbulence */
/* Place in @layer components in index.css */
@layer components {
  .charcoal-texture {
    position: relative;
    overflow: hidden;
    background-color: var(--charcoal);
  }
  .charcoal-texture::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C%2Fsvg%3E");
    background-repeat: repeat;
    background-size: 200px;
    opacity: 0.06;
  }
}
```

Children of `.charcoal-texture` that should appear above the pseudo-element must have `position: relative; z-index: 1` if they stack incorrectly. In most cases, flow content sits above `::before` naturally.

### Filter Buttons Full Width (THEME-03)

Raw button groups — change `flex flex-wrap gap-1` to `grid`:
```jsx
/* Time Control: 4 equal columns */
<div className="grid grid-cols-4 gap-1">
  {TIME_CONTROLS.map((tc) => (
    <button key={tc} className={cn('rounded border h-11 sm:h-7 text-xs transition-colors', ...)} />
  ))}
</div>

/* Platform: 2 equal columns */
<div className="grid grid-cols-2 gap-1">
  {PLATFORMS.map((p) => (
    <button ... />
  ))}
</div>
```

ToggleGroup components — add `className="w-full"` to ToggleGroup and `className="flex-1"` to each ToggleGroupItem:
```jsx
<ToggleGroup type="single" variant="outline" size="sm" className="w-full" ...>
  <ToggleGroupItem value="all" className="flex-1" ...>All</ToggleGroupItem>
  <ToggleGroupItem value="rated" className="flex-1" ...>Rated</ToggleGroupItem>
  <ToggleGroupItem value="casual" className="flex-1" ...>Casual</ToggleGroupItem>
</ToggleGroup>
```

### Recharts Stacked Bar Rounding (THEME-04)

```jsx
/* Source: Recharts 2.x Bar radius prop + GitHub issue #1888 */
/* Apply radius only to outermost bars in the stack */
<Bar xAxisId="pct" dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)"
     radius={[4, 4, 0, 0]} />   {/* top-left, top-right, bottom-right, bottom-left */}
<Bar xAxisId="pct" dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" />
<Bar xAxisId="pct" dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)"
     radius={[0, 0, 4, 4]} />
```

Note: `radius={[4,4,0,0]}` on `win_pct` (topmost in Recharts stacking order — last rendered = topmost visual) and `radius={[0,0,4,4]}` on `loss_pct` (bottom). The stacking order in Recharts follows declaration order: `win_pct` is first declared so it renders at the bottom, `loss_pct` is last so it renders at the top. **Verify the actual visual stacking order** during implementation — adjust radius placement if needed.

### Tabs Brand Variant (THEME-05)

In `tabs.tsx`, add `brand` to CVA variants:
```typescript
const tabsListVariants = cva(
  "group/tabs-list inline-flex w-fit items-center justify-center rounded-lg ...",
  {
    variants: {
      variant: {
        default: "bg-muted",
        line: "gap-1 bg-transparent",
        brand: "bg-charcoal gap-0",   // charcoal background for the tab bar
      },
    },
    defaultVariants: { variant: "default" },
  }
)
```

In `TabsTrigger`, add brand active state styling:
```typescript
"group-data-[variant=brand]/tabs-list:data-active:bg-brand-brown",
"group-data-[variant=brand]/tabs-list:data-active:text-white",
"group-data-[variant=brand]/tabs-list:data-active:border-transparent",
"group-data-[variant=brand]/tabs-list:data-active:shadow-none",
```

Usage:
```jsx
<TabsList variant="brand" className="w-full" data-testid="endgames-tabs">
  <TabsTrigger value="statistics" className="flex-1" ...>Statistics</TabsTrigger>
  <TabsTrigger value="games" className="flex-1" ...>Games</TabsTrigger>
</TabsList>
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Tailwind 3: `tailwind.config.js` theme extension | Tailwind v4: `@theme inline` in CSS | Project already on v4 |
| Recharts BarStack for stacked rounding | Cell-based conditional radius (2.x) | BarStack requires Recharts 3.x |
| Hardcoded hex in Tailwind brackets `bg-[#8B5E3C]` | CSS variable → `@theme inline` → `bg-brand-brown` | Enabled by D-16 |

---

## Environment Availability

Step 2.6: SKIPPED — this phase is frontend-only code/CSS changes with no new external tool dependencies.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.x |
| Config file | `vite.config.ts` (vitest config embedded in vite config) |
| Quick run command | `npm test` (from `frontend/`) |
| Full suite command | `npm test` (from `frontend/`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| THEME-01 | Brand brown CSS variable defined in index.css and `PRIMARY_BUTTON_CLASS` uses `bg-brand-brown` | manual-only | — inspect `theme.ts` and `index.css` | N/A |
| THEME-02 | Charcoal containers with noise texture visible on target pages | manual-only | — visual inspection required | N/A |
| THEME-03 | Filter buttons span full sidebar width | manual-only | — visual inspection required | N/A |
| THEME-04 | WDL bar chart corners rounded in `WDLBarChart.tsx` | manual-only | — visual inspection required | N/A |
| THEME-05 | Active subtab has brand brown fill with white text | manual-only | — visual inspection required | N/A |

All THEME requirements are purely visual and require manual browser inspection. The existing `arrowColor.test.ts` confirms Vitest is configured and working.

### Sampling Rate
- **Per task commit:** `npm test` — verify no existing tests regressed
- **Per wave merge:** `npm test` + visual browser check of affected pages
- **Phase gate:** All existing tests green + manual visual review of Openings, Endgames, Dashboard, Import pages

### Wave 0 Gaps
None — no new test files needed for this phase. All requirements are visual and manual-only. The existing test passes as a regression gate.

---

## Open Questions

1. **Recharts stacking order: which bar is visually topmost?**
   - What we know: In Recharts stacked horizontal bars, rendering order follows JSX declaration order, but the visual stacking (which value appears on which side) depends on the layout.
   - What's unclear: For `layout="vertical"` stacked bars with `win_pct`, `draw_pct`, `loss_pct`, the first-declared bar may be leftmost (since WDL is horizontal here, effectively left = bottom, right = top). Needs visual verification during implementation.
   - Recommendation: During implementation, temporarily set distinctive colors and confirm which bar is leftmost. Apply `radius={[0,0,4,4]}` to the leftmost (left edge = bottom-left/bottom-right corners visually) and `radius={[4,4,0,0]}` to the rightmost.

2. **Charcoal opacity under noise texture — legibility of text/content**
   - What we know: Charcoal at `#2A2520` with opacity 0.06 noise is the starting point.
   - What's unclear: Whether content inside charcoal containers (e.g., bookmark card text, game card metadata) retains sufficient contrast.
   - Recommendation: Start at opacity 0.06 and adjust. If content looks washed out, reduce to 0.04.

---

## Sources

### Primary (HIGH confidence)
- Tailwind CSS official docs (tailwindcss.com/docs/theme) — `@theme inline` CSS variable syntax verified
- MDN Web Docs (developer.mozilla.org/SVG/Reference/Element/feTurbulence) — feTurbulence attributes
- Project source code (`index.css`, `tabs.tsx`, `toggle-group.tsx`, `WDLBarChart.tsx`, `App.tsx`) — direct inspection

### Secondary (MEDIUM confidence)
- ibelick.com/blog/create-grainy-backgrounds-with-css — CSS data URI noise texture pattern (verified consistent with MDN)
- Recharts GitHub issue #1888 (recharts/recharts) — stacked bar radius behavior in 2.x confirmed
- Recharts GitHub issue #3887 — BarStack confirmed as 3.x-only feature

### Tertiary (LOW confidence)
- recharts.github.io/en-US/guide/roundedBars/ — references BarStack but this applies to 3.x only; confirmed mismatch with installed 2.15.4

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on This Phase |
|-----------|---------------------|
| Theme constants in `theme.ts` — all theme-relevant color constants must be defined in `theme.ts` and imported from there | `PRIMARY_BUTTON_CLASS` update stays in `theme.ts` after migrating from hardcoded hex. WDL/gauge constants stay in `theme.ts` (D-17). |
| Never hard-code color values with semantic meaning directly in components | Use `bg-brand-brown` utility, not `bg-[#8B5E3C]` in components |
| `data-testid` on every interactive element | Any new/modified interactive elements need `data-testid`. The phase adds no new interactive elements — only visual styling changes. |
| Mobile-friendly: apply changes to both desktop and mobile variants | `FilterPanel.tsx` is shared (single component used in both desktop sidebar and mobile collapsible) — one change covers both. Nav header has both `NavHeader` (desktop) and `MobileHeader` — both need border removal and logo link. |
| Always check mobile variants | Dashboard collapsibles appear in mobile view too — verify charcoal texture looks correct on narrow screens. |
| No dark/light mode toggle — dark theme is only mode | Only `.dark` block matters; `:root` light values exist in `index.css` but are never activated. Safe to define new variables in `:root` only since `.dark` overrides all background values anyway. |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed, no new dependencies
- Architecture: HIGH — patterns verified by reading actual source files and official docs
- Pitfalls: HIGH — specific to the actual code patterns observed in the codebase
- Recharts radius workaround: MEDIUM — behavior confirmed via GitHub issues, visual validation still needed at implementation time

**Research date:** 2026-03-28
**Valid until:** 2026-09-01 (CSS/component patterns are stable; Tailwind v4 API unlikely to change significantly)
