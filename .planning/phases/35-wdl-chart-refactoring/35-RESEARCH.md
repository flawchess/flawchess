# Phase 35: WDL Chart Refactoring - Research

**Researched:** 2026-03-28
**Domain:** React component refactoring — shared WDL chart component
**Confidence:** HIGH

## Summary

The codebase contains four distinct WDL bar implementations with different visual styles, data shapes, and feature sets. The goal is to collapse all of them (except the move list) into a single shared component that matches the endgame-style custom bar (the reference implementation). The Recharts-based implementations in `GlobalStatsCharts.tsx` and `WDLBarChart.tsx` are the primary targets — they use Recharts horizontal bar charts instead of the custom flex-div approach, are visually inconsistent (no glass overlay, inconsistent corners), and carry unnecessary charting library weight for what is fundamentally a simple stacked percentage bar.

The `WDLBar` component in `results/WDLBar.tsx` is the simplest form and is already close to the endgame reference. The `EndgameWDLChart` adds a title, per-row game count link, game count bar, and an inline category select interaction — these features need to be distilled into optional props on the new shared component.

**Primary recommendation:** Build a new `WDLChartRow` component (or rename/evolve `WDLBar`) that renders: optional title with InfoPopover, stacked WDL bar with glass overlay, optional game count bar, WDL legend text, and an optional games link. Eliminate `WDLBarChart` (Recharts horizontal bar chart used only in Openings Compare tab) and `WDLCategoryChart` inside `GlobalStatsCharts` entirely.

## Inventory of WDL Chart Implementations

This is the critical pre-planning survey. All implementations listed below must be accounted for in the plan.

### 1. `WDLBar` — `frontend/src/components/results/WDLBar.tsx`

**Used in:**
- `Dashboard.tsx` — shown after running a position filter (`<WDLBar stats={analysisResult.stats} />`)
- `Openings.tsx` — shown in the Explorer tab (position stats bar) and Games tab (analysis stats bar)

**Features:**
- Stacked flex-div bar with glass overlay (WDL_WIN/DRAW/LOSS + GLASS_OVERLAY from theme.ts)
- Height: `h-6`
- WDL legend text row: `W: {n} ({pct}%)` etc.
- No title, no game count bar, no games link

**Data shape:** `WDLStats` from `types/api.ts` — `{ wins, draws, losses, total, win_pct, draw_pct, loss_pct }`

**Visual status:** Already matches the reference. Minor: uses `toFixed(0)` for pct, not `Math.round()`.

---

### 2. `EndgameWDLChart` — `frontend/src/components/charts/EndgameWDLChart.tsx`

**Used in:**
- `Endgames.tsx` — "Results by Endgame Type" section

**Features:**
- Title "Results by Endgame Type" with InfoPopover
- Per-category rows: label, per-type InfoPopover, game count with "(low)" warning, ExternalLink to `/endgames/games`
- Stacked WDL bar with glass overlay, height `h-5`, dimmed when < MIN_GAMES_FOR_RELIABLE_STATS
- Grey-outlined game count bar (proportional to max category total)
- WDL legend text row with game counts (`Math.round(pct)%`)
- Specialized: `onCategorySelect` callback for the games link, endgame-specific `ENDGAME_TYPE_DESCRIPTIONS`

**Data shape:** `EndgameCategoryStats[]` from `types/endgames.ts`

**Visual status:** This IS the reference implementation. Other charts must match it.

---

### 3. `WDLCategoryChart` (internal) — inside `frontend/src/components/stats/GlobalStatsCharts.tsx`

**Used in:**
- `GlobalStats.tsx` — "Results by Time Control" and "Results by Color" charts

**Features:**
- Title with InfoPopover
- Recharts horizontal stacked bar chart (BarChart from recharts)
- No glass overlay, no game count bar
- Tooltip on hover, ChartLegend
- One bar per category (bullet/blitz/rapid/classical or white/black)

**Data shape:** `WDLByCategory[]` from `types/stats.ts` — same fields as `WDLStats` plus `label`

**Visual status:** Recharts implementation — inconsistent with reference. No glass overlay, bar height driven by Recharts layout. Must be replaced.

---

### 4. `WDLBarChart` — `frontend/src/components/charts/WDLBarChart.tsx`

**Used in:**
- `Openings.tsx` — Statistics tab ("Results by Opening")

**Features:**
- Recharts horizontal stacked bar chart
- Title "Results by Opening" with InfoPopover
- Per-bookmark row with label (color prefix "● "/"○ ") + game count outline bar
- Tooltip with full W/D/L breakdown
- No glass overlay, sorted by total descending

**Data shape:** `PositionBookmarkResponse[]` + `Record<number, WDLStats>` map

**Visual status:** Recharts implementation — inconsistent with reference. Must be replaced with custom rows like EndgameWDLChart.

---

### 5. `WDLRow` (internal) — inside `frontend/src/components/charts/EndgamePerformanceSection.tsx`

**Used in:**
- `Endgames.tsx` — "Endgame Performance" section (two rows: "Endgame games" / "Non-endgame games")

**Features:**
- Label + game count (right-aligned)
- Stacked WDL bar with glass overlay, height `h-5`
- WDL legend text row (`Math.round(pct)%`)
- No title, no games link, no game count bar

**Data shape:** `EndgameWDLSummary` — same fields as `WDLStats`

**Visual status:** Already matches reference visually but is a private component inside `EndgamePerformanceSection`. The planner must decide whether to extract it to the shared component.

---

### The Move List (EXCLUDED)

Per the phase objective, the moves list in the Moves tab (`MoveExplorer.tsx`) uses per-row WDL mini-bars that are NOT to be refactored. These are a different UX pattern (inline per-move rows with different dimensions) and are explicitly excluded from scope.

## Architecture Patterns

### Reference Implementation Pattern (EndgameWDLChart row)

```
┌─────────────────────────────────────────────────┐
│  [Label]  [InfoPopover?]          [N games] [🔗] │  ← header row (optional link)
│  ██████████████████▓▓▓░░░░░░░░░░░░░░░░░░░░░░    │  ← stacked WDL bar (h-5, glass)
│  ▭▭▭▭▭▭▭▭▭▭▭                                    │  ← grey-outline game count bar (optional)
│  W: 45 (45%)   D: 20 (20%)   L: 35 (35%)       │  ← WDL legend text row
└─────────────────────────────────────────────────┘
```

### Proposed Shared Component Interface

The shared component must cover all use cases via optional props:

```typescript
// Canonical WDL data shape — subset of WDLStats; EndgameWDLSummary; WDLByCategory all satisfy this
interface WDLRowData {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

interface WDLChartRowProps {
  // Core data
  data: WDLRowData;

  // Label / title area (optional — WDLBar usage has no title)
  label?: string;
  infoPopover?: React.ReactNode;

  // Games link (optional — EndgameWDLChart and WDLBarChart have links)
  gamesLink?: string;            // href for Link
  onGamesLinkClick?: () => void; // side-effect (e.g. category select)
  gamesLinkTestId?: string;

  // Game count bar (optional — only EndgameWDLChart and WDLBarChart show it)
  maxTotal?: number;             // present = show bar, absent = no bar

  // Low sample size dimming
  minGamesForReliable?: number;  // defaults to MIN_GAMES_FOR_RELIABLE_STATS from theme

  // Visual size
  barHeight?: 'h-5' | 'h-6';    // default h-5 to match reference

  // data-testid prefix
  testId?: string;
}
```

**Top-level chart wrapper** (optional, for "Results by X" sections with a heading):

```typescript
interface WDLChartProps {
  title: string;
  infoPopover?: React.ReactNode;
  rows: Array<WDLChartRowProps>;
  testId?: string;
}
```

OR the planner may keep the title rendering in the parent component and compose `WDLChartRow` directly — this is fine since `EndgameWDLChart` already does its own title rendering.

### File Location

New file: `frontend/src/components/charts/WDLChartRow.tsx`

The existing `WDLBar` (used in Dashboard/Openings as a simple single-bar without title) can either:
- **Option A:** Be reimplemented as a thin wrapper over `WDLChartRow`
- **Option B:** Be left as-is since it's already visually correct and used differently (no title/link/count bar)

Option A keeps a single code path. Option B avoids changing working code. Either is valid — Claude's discretion.

### Migration Map

| Current | Replace with | Notes |
|---------|-------------|-------|
| `WDLCategoryChart` in `GlobalStatsCharts.tsx` | Custom rows via shared component | Remove Recharts BarChart. One row per category (bullet/blitz/rapid/classical/white/black). Add game count bar. |
| `WDLBarChart.tsx` | Custom rows via shared component | Remove Recharts BarChart. One row per bookmark. Keep color prefix in label. Add games link to `/openings/games`. Keep game count bar. |
| `WDLRow` in `EndgamePerformanceSection.tsx` | Shared component | Extract private WDLRow to shared. Two rows, no game count bar, no link. |
| `WDLBar.tsx` | Keep or wrap shared component | Already correct visually. Used without title/link. |
| `EndgameWDLChart.tsx` | Refactor to use shared row | Keep outer structure, endgame-specific popovers, and `onCategorySelect` logic. Replace inner bar rendering. |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Low sample size dimming | Custom opacity logic per-component | `UNRELIABLE_OPACITY` + `MIN_GAMES_FOR_RELIABLE_STATS` from `theme.ts` | Already defined — use consistently |
| Glass overlay | Per-component linear-gradient string | `GLASS_OVERLAY` from `theme.ts` | Centralized, consistent |
| WDL colors | Per-component color strings | `WDL_WIN`, `WDL_DRAW`, `WDL_LOSS` from `theme.ts` | Single source of truth per CLAUDE.md requirement |
| Game count bar border color | Inline string | `oklch(0.6 0 0)` — already the established value in EndgameWDLChart | Match the reference |

## Common Pitfalls

### Pitfall 1: WDLBarChart Interactivity Loss
**What goes wrong:** `WDLBarChart` uses Recharts tooltips for exact game counts on hover. The custom row pattern shows counts inline. Removing Recharts removes the tooltip.
**Why it happens:** Recharts hover is the only mechanism for showing W/D/L counts in the bar chart.
**How to avoid:** Show W/D/L counts as static text below the bar (like EndgameWDLChart), not just on hover. This is the reference pattern and is more accessible.
**Warning signs:** If the plan keeps Recharts tooltip for WDLBarChart, it's not fully migrated.

### Pitfall 2: WDLByCategory Missing pct Fields
**What goes wrong:** The Recharts GlobalStatsCharts reads `win_pct`, `draw_pct`, `loss_pct` from `WDLByCategory`. The custom bar needs these — verify they exist.
**Why it happens:** Type inspection required.
**How to avoid:** `WDLByCategory` in `types/stats.ts` already includes `win_pct`, `draw_pct`, `loss_pct`. No backend change needed. Confidence: HIGH (verified from source).

### Pitfall 3: WDLBarChart Sort Order
**What goes wrong:** `WDLBarChart` sorts bookmarks by `total` descending. In the custom row implementation, sort order must be explicitly applied before rendering rows.
**How to avoid:** Sort the rows array before passing to the component, same as the current `.sort((a, b) => b.total - a.total)` in WDLBarChart.

### Pitfall 4: Color Prefix Labels in WDLBarChart
**What goes wrong:** WDLBarChart prepends "● " or "○ " to bookmark labels based on color (white/black). This label manipulation is bookmark-specific and should stay in the Openings page, not leak into the shared component.
**How to avoid:** Compute the display label in `Openings.tsx` before passing to the shared component rows.

### Pitfall 5: Removing Recharts Leaves Dead chartConfig Constants
**What goes wrong:** `chartConfig` objects in `GlobalStatsCharts.tsx` and `WDLBarChart.tsx` reference `WDL_WIN`/`WDL_DRAW`/`WDL_LOSS`. When Recharts is removed, these constants may still be imported but unused.
**How to avoid:** Delete the `chartConfig` object and verify the import of `ChartContainer`, `ChartTooltip`, `ChartLegend`, `ChartLegendContent`, `BarChart`, `Bar`, `XAxis`, `YAxis`, `CartesianGrid` are all removed.

### Pitfall 6: WDLBar Height Inconsistency
**What goes wrong:** `WDLBar` uses `h-6`, `EndgameWDLChart` rows use `h-5`. Migrating to a shared component requires picking one canonical height.
**How to avoid:** Use `h-5` as the default (matches the reference implementation). `WDLBar` can pass `barHeight="h-6"` if the current height matters — or just standardize on `h-5`.

### Pitfall 7: `EndgameWDLChart` Has Endgame-Specific Logic
**What goes wrong:** `EndgameWDLChart` has `ENDGAME_TYPE_DESCRIPTIONS`, a `CLASS_TO_SLUG` map, and an `onCategorySelect` callback — these are endgame-specific and cannot move into the shared component.
**How to avoid:** The shared component handles only the visual row. `EndgameWDLChart` remains as an endgame-specific wrapper that provides the per-type InfoPopover content and `onCategorySelect` binding.

## Code Examples

### Reference: EndgameCategoryRow inner bar (the pattern to replicate)

```tsx
// Source: frontend/src/components/charts/EndgameWDLChart.tsx
<div
  className={cn('flex h-5 w-full overflow-hidden rounded mb-0')}
  style={cat.total < MIN_GAMES_FOR_RELIABLE_STATS ? { opacity: UNRELIABLE_OPACITY } : undefined}
>
  {cat.win_pct > 0 && (
    <div
      className="transition-all"
      style={{ width: `${cat.win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
    />
  )}
  {cat.draw_pct > 0 && (
    <div
      className="transition-all"
      style={{ width: `${cat.draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }}
    />
  )}
  {cat.loss_pct > 0 && (
    <div
      className="transition-all"
      style={{ width: `${cat.loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }}
    />
  )}
</div>
```

### Reference: Game count bar

```tsx
// Source: frontend/src/components/charts/EndgameWDLChart.tsx
<div className="h-2 mt-0.5 mb-1">
  <div
    className="h-full rounded-sm"
    style={{
      width: `${(cat.total / maxTotal) * 100}%`,
      border: '1px solid oklch(0.6 0 0)',
      backgroundColor: 'transparent',
    }}
  />
</div>
```

### Reference: WDL legend text row

```tsx
// Source: frontend/src/components/charts/EndgameWDLChart.tsx
<div
  className="flex justify-center gap-3 text-sm"
  style={cat.total < MIN_GAMES_FOR_RELIABLE_STATS ? { opacity: UNRELIABLE_OPACITY } : undefined}
>
  <span style={{ color: WDL_WIN }}>W: {cat.wins} ({Math.round(cat.win_pct)}%)</span>
  <span style={{ color: WDL_DRAW }}>D: {cat.draws} ({Math.round(cat.draw_pct)}%)</span>
  <span style={{ color: WDL_LOSS }}>L: {cat.losses} ({Math.round(cat.loss_pct)}%)</span>
</div>
```

## Cleanup Checklist

After refactoring, the following should be removed or have no remaining callers:

- `WDLBarChart.tsx` — delete the file (only used in Openings.tsx Statistics tab; replaced)
- Internal `WDLCategoryChart` function inside `GlobalStatsCharts.tsx` — replaced with shared component rows
- Internal `WDLRow` function inside `EndgamePerformanceSection.tsx` — replaced with shared component
- Recharts `BarChart`/`Bar`/`XAxis`/`YAxis`/`CartesianGrid` imports in `GlobalStatsCharts.tsx` and `WDLBarChart.tsx` (once deleted)
- `ChartContainer`/`ChartTooltip`/`ChartLegend`/`ChartLegendContent` imports from `components/ui/chart` in the same files
- `chartConfig` constant in `GlobalStatsCharts.tsx` (Recharts config object)
- Any `WDL_WIN`/`WDL_DRAW`/`WDL_LOSS` imports that become redundant in files where they were only used for the Recharts `chartConfig`

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — this is a pure frontend component refactor)

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.x |
| Config file | `frontend/vite.config.ts` (vitest inline config) or `frontend/vitest.config.ts` |
| Quick run command | `npm test` (from `frontend/`) |
| Full suite command | `npm test` (same — only unit tests exist) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| (SC-1) | Shared WDL chart component exists and renders | unit | `npm test` | ❌ Wave 0 |
| (SC-2) | All WDL chart locations use shared component | manual visual check | — | manual-only |
| (SC-3) | No unused WDL-related constants or Recharts code | lint/build | `npm run lint && npm run build` | ✅ existing |
| (SC-4) | Visual appearance matches endgame type reference | manual visual check | — | manual-only |

**Note:** SC-2 and SC-4 are visual/structural checks. Automated unit tests can cover the shared component's rendering logic (bar segments, glass overlay, optional game count bar) but cannot fully automate visual comparison. Build + lint verification catches dead imports automatically.

### Sampling Rate
- **Per task commit:** `npm run lint && npm run build`
- **Per wave merge:** `npm test && npm run build`
- **Phase gate:** Full suite green + manual visual comparison with endgame charts before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/components/charts/WDLChartRow.test.tsx` — covers shared component rendering (bar segments present/absent, opacity dimming for low sample size, game count bar presence). Needs Vitest + React Testing Library or a simple DOM render test.

Note: No `@testing-library/react` is installed currently. The existing test (`arrowColor.test.ts`) is a pure logic test requiring no DOM. The planner must decide whether to:
1. Add `@testing-library/react` for component tests, OR
2. Keep the test as a pure logic/export test (verify constants and function signatures), OR
3. Accept manual verification for the visual component and use build/lint as the automated gate.

Given project precedent (only one existing test, which is pure logic), the planner should probably use build + lint as the primary automation gate and add a smoke test if practical.

## Sources

### Primary (HIGH confidence)
- Direct source file reading: all files verified from repository at 2026-03-28

### Secondary (MEDIUM confidence)
- N/A — this is entirely internal codebase analysis; no external library research needed

## Metadata

**Confidence breakdown:**
- Inventory of WDL chart implementations: HIGH — all files read directly
- Proposed component interface: HIGH — derived from existing code patterns
- Migration complexity: HIGH — no backend changes, pure frontend restructuring
- Pitfalls: HIGH — derived from direct code inspection

**Research date:** 2026-03-28
**Valid until:** 30 days (stable codebase, no external dependency changes)
