# Phase 107: Games Subtab Frontend — Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 15 (new/modified)
**Analogs found:** 15 / 15

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/pages/library/GamesTab.tsx` | page/component | request-response | `frontend/src/pages/Endgames.tsx` (sidebar+drawer pattern) | role-match |
| `frontend/src/components/results/LibraryGameCard.tsx` | component | request-response | `frontend/src/components/results/GameCard.tsx` | exact |
| `frontend/src/components/results/LibraryGameCardList.tsx` | component | request-response | `frontend/src/components/results/GameCardList.tsx` | exact |
| `frontend/src/components/filters/LibraryFilterPanel.tsx` | component | request-response | `frontend/src/components/filters/FilterPanel.tsx` | exact |
| `frontend/src/components/library/SeverityBadge.tsx` | component | request-response | `frontend/src/components/results/GameCard.tsx` (resultIndicator chip) | role-match |
| `frontend/src/components/library/TagChip.tsx` | component | request-response | `frontend/src/components/results/GameCard.tsx` (resultIndicator chip) | role-match |
| `frontend/src/components/library/NoAnalysisState.tsx` | component | request-response | `frontend/src/components/results/GameCard.tsx` (openingLine) | partial |
| `frontend/src/components/library/FlawStatsPanel.tsx` | component | request-response | `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` (panel shell) | role-match |
| `frontend/src/components/library/FlawStatsBand.tsx` | component | request-response | `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` | role-match |
| `frontend/src/components/library/FlawTrendChart.tsx` | component | request-response | `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` | exact |
| `frontend/src/components/library/FlawTagDistribution.tsx` | component | request-response | `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` | role-match |
| `frontend/src/components/results/GameCardList.tsx` (MODIFIED) | component | request-response | itself — extract `getPaginationItems` + pagination controls | self |
| `frontend/src/pages/library/LibraryPage.tsx` (MODIFIED) | page | request-response | itself — add third TabsTrigger, update redirect | self |
| `frontend/src/lib/theme.ts` (MODIFIED) | config | — | itself — add color constants after existing semantic-color blocks | self |
| `app/schemas/library.py` (MODIFIED) | model/schema | CRUD | `app/schemas/library.py` lines 97–105 (`result_changing_rate` field) | self |
| `app/services/library_service.py` (MODIFIED) | service | CRUD | `app/services/library_service.py` lines 325–356 (`_compute_tag_distribution`) | self |
| `tests/services/test_library_service.py` (MODIFIED) | test | CRUD | itself — `TestFlawStats` class, lines 436–609 | self |

---

## Pattern Assignments

### `frontend/src/pages/library/GamesTab.tsx` (page, request-response)

**Analog:** `frontend/src/pages/Endgames.tsx`

This is the Games subtab root. It mirrors Endgames' desktop-sidebar + mobile-Drawer pattern exactly.

**Imports pattern** (Endgames.tsx lines 1–44):
```typescript
import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useQuery } from '@tanstack/react-query';
import type { FilterState } from '@/components/filters/FilterPanel';
```

**Filter state wiring** (Endgames.tsx lines 190–230 — pending vs applied, modified-dot):
```typescript
const [appliedFilters, setAppliedFilters] = useFilterStore();
const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);
useEffect(() => { setPendingFilters(appliedFilters); }, [appliedFilters]);
const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

const isModified = useMemo(
  () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
  [appliedFilters],
);
// ...modifiedDotNode JSX (lines 259–270)
```

Note for GamesTab: `severityFilter: ('blunder' | 'mistake')[]` lives as additional local state in GamesTab, NOT inside FilterState. It is passed directly to both queries.

**Mobile drawer handler** (Endgames.tsx lines 320–330):
```typescript
const handleMobileFiltersOpenChange = useCallback((open: boolean) => {
  if (!open && mobileFiltersOpen) {
    setAppliedFilters(pendingFilters);
    setGamesOffset(0);
  }
  if (open && !mobileFiltersOpen) {
    setPendingFilters(appliedFilters);
  }
  setMobileFiltersOpen(open);
}, [mobileFiltersOpen, pendingFilters, appliedFilters, setAppliedFilters]);
```

**Mobile Drawer JSX** (Endgames.tsx lines 931–951):
```tsx
<Drawer open={mobileFiltersOpen} onOpenChange={handleMobileFiltersOpenChange} direction="right">
  <DrawerContent className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]" data-testid="drawer-filter-sidebar">
    <DrawerHeader className="flex flex-row items-center justify-between">
      <DrawerTitle>Filters</DrawerTitle>
      <DrawerClose asChild>
        <Button variant="ghost" size="icon" aria-label="Close filters"><X /></Button>
      </DrawerClose>
    </DrawerHeader>
    {/* LibraryFilterPanel goes here */}
  </DrawerContent>
</Drawer>
```

**Modified-dot node** (Endgames.tsx lines 259–270):
```tsx
const modifiedDotNode = isModified ? (
  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-modified-dot" aria-hidden="true">
    {isPulsing && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />}
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
  </span>
) : undefined;
```

**Mobile filters button** (pattern from Endgames.tsx ~line 913):
```tsx
<Button variant="brand-outline" aria-label="Open filters" data-testid="btn-filters">
  <SlidersHorizontal className="h-4 w-4" />
  Filters
  {modifiedDotNode && <span className="relative">{modifiedDotNode}</span>}
</Button>
```

**TanStack Query hooks** (analog: `frontend/src/hooks/useEndgames.ts`):
```typescript
// Copy useEndgameGames pattern for useLibraryGames and useLibraryFlawStats.
// Key structure: ['library-games', params, severityFilter, offset]
//               ['library-flaw-stats', params, severityFilter]
return useQuery({
  queryKey: ['library-games', params, severityFilter, offset],
  queryFn: () => libraryApi.getGames({ ...params, severity: severityFilter, offset, limit }),
  staleTime: LIBRARY_STALE_TIME,
  refetchOnWindowFocus: false,
});
```

---

### `frontend/src/components/results/LibraryGameCard.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCard.tsx`

LibraryGameCard borrows GameCard's layout structure but adds a full-width header, 3-column desktop body, and a flaw column. Do NOT refactor GameCard — this is a separate component (D-05).

**Imports pattern** (GameCard.tsx lines 1–9):
```typescript
import { BookOpen, Calendar, Clock, Equal, ExternalLink, Hash, Minus, Plus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WDL_BORDER_DRAW, WDL_BORDER_LOSS, WDL_BORDER_WIN } from '@/lib/theme';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import type { GameRecord, UserResult } from '@/types/api';
```

**WDL border pattern** (GameCard.tsx lines 17–27):
```typescript
const BORDER_COLORS: Record<UserResult, string> = {
  win: WDL_BORDER_WIN,
  draw: WDL_BORDER_DRAW,
  loss: WDL_BORDER_LOSS,
};
```

**Card root with WDL left border** (GameCard.tsx lines 192–196):
```tsx
<div
  data-testid={`game-card-${game.game_id}`}
  className="charcoal-texture border border-border/20 border-l-4 rounded px-4 py-3"
  style={{ borderLeftColor: BORDER_COLORS[game.user_result] }}
>
```

**Platform icon + external link** (GameCard.tsx lines 84–102):
```tsx
const platformIconAndLink = (
  <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
    <PlatformIcon platform={game.platform} className="h-4 w-4" />
    {game.platform_url ? (
      <Tooltip content="Open game on platform">
        <a
          href={game.platform_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label="Open game on platform"
          data-testid={`game-card-link-${game.game_id}`}
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </Tooltip>
    ) : null}
  </span>
);
```

**Mobile layout** (GameCard.tsx lines 198–213):
```tsx
<div className="flex flex-col gap-2 sm:hidden">
  {mobileIdentifier}
  <div className="flex gap-3 items-start">
    {game.result_fen && (
      <LazyMiniBoard fen={game.result_fen} flipped={game.user_color === 'black'} size={MOBILE_BOARD_SIZE} />
    )}
    <div className="flex-1 min-w-0 flex flex-col gap-1">
      {openingLine}
      {mobileMetadata}
    </div>
  </div>
</div>
```

**Desktop layout** (GameCard.tsx lines 215–229):
```tsx
<div className="hidden sm:flex gap-3 items-center">
  {game.result_fen && (
    <LazyMiniBoard fen={game.result_fen} flipped={game.user_color === 'black'} size={DESKTOP_BOARD_SIZE} />
  )}
  <div className="min-w-0 flex-1 flex flex-col gap-2">
    {desktopIdentifier}
    {openingLine}
    {desktopMetadata}
  </div>
</div>
```

For LibraryGameCard, the desktop layout adds a third column (flaw column) after the info column:
```tsx
<div className="hidden sm:flex gap-3 items-start">
  {/* col 1: LazyMiniBoard */}
  {/* col 2: info (flex-1) */}
  {/* col 3: flaw column (flex: 0 0 auto, dashed left border) */}
  <div className="pl-4 border-l border-dashed border-border flex flex-col gap-2">
    {/* SeverityBadge row or NoAnalysisState */}
    {/* TagChip row */}
  </div>
</div>
```

**formatDate / formatTimeControl helpers** (GameCard.tsx lines 29–61): Copy verbatim — same display requirements.

---

### `frontend/src/components/results/LibraryGameCardList.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCardList.tsx`

**D-04: Extract `getPaginationItems` + pagination controls.** The planner must decide whether this becomes a `Pagination` component or `usePagination` hook. The cleanest fit is a `Pagination` component that accepts `{ currentPage, totalPages, onPageChange }` and renders the prev/numbered/next row — GameCardList and LibraryGameCardList both import it.

**`getPaginationItems` logic to extract** (GameCardList.tsx lines 28–59):
```typescript
type PaginationItem = number | 'ellipsis-start' | 'ellipsis-end';

function getPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const items: PaginationItem[] = [];
  items.push(1);
  const windowStart = Math.max(2, currentPage - 2);
  const windowEnd = Math.min(totalPages - 1, currentPage + 2);
  if (windowStart > 2) items.push('ellipsis-start');
  for (let p = windowStart; p <= windowEnd; p++) items.push(p);
  if (windowEnd < totalPages - 1) items.push('ellipsis-end');
  items.push(totalPages);
  return items;
}
```

**Pagination controls to extract** (GameCardList.tsx lines 113–164): The entire `{totalPages > 1 && <div ...>prev/items/next</div>}` block. After extraction, `GameCardList` and `LibraryGameCardList` both call:
```tsx
<Pagination
  currentPage={currentPage}
  totalPages={totalPages}
  onPageChange={handlePageChange}
/>
```

**LibraryGameCardList scroll target** (analogous to GameCardList.tsx lines 76–80):
```typescript
const handlePageChange = (newOffset: number) => {
  onPageChange(newOffset);
  document
    .querySelector('[data-testid="library-game-card-list"]')
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};
```

**Match count row** (GameCardList.tsx lines 87–98): LibraryGameCardList uses a simplified version:
```tsx
<p className="text-sm text-muted-foreground">
  {matchedCount} of {total} games
</p>
```

---

### `frontend/src/components/filters/LibraryFilterPanel.tsx` (component, request-response)

**Analog:** `frontend/src/components/filters/FilterPanel.tsx`

LibraryFilterPanel composes the existing `FilterPanel` with `visibleFilters` prop and prepends the new severity-filter section above it.

**FilterPanel props pattern** (FilterPanel.tsx lines 134–143):
```typescript
interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  visibleFilters?: FilterField[];
  showDeferredApplyHint?: boolean;
}
```

**visibleFilters for the Games surface** (omit `matchSide` and rely on FilterPanel's `visibleFilters` prop to omit color):
```typescript
// Games surface: all filters except matchSide/color
const LIBRARY_GAMES_FILTERS: FilterField[] = ['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency'];
```

**Severity filter toggle pattern** (new, analogous to TimeControl ToggleGroup in FilterPanel.tsx lines 147–153):
```tsx
<div className="flex flex-col gap-2">
  <p className="text-sm text-muted-foreground">Show games with:</p>
  <div className="flex gap-2">
    <button
      className={cn('h-11 sm:h-7 px-3 rounded border text-sm font-bold', severityFilter.includes('blunder') ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground' : 'border-border bg-inactive-bg text-muted-foreground')}
      aria-pressed={severityFilter.includes('blunder')}
      data-testid="filter-severity-blunder"
      onClick={() => toggleSeverity('blunder')}
    >
      Blunders
    </button>
    <button
      className={cn('h-11 sm:h-7 px-3 rounded border text-sm font-bold', severityFilter.includes('mistake') ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground' : 'border-border bg-inactive-bg text-muted-foreground')}
      aria-pressed={severityFilter.includes('mistake')}
      data-testid="filter-severity-mistake"
      onClick={() => toggleSeverity('mistake')}
    >
      Mistakes
    </button>
  </div>
</div>
```

**`FILTER_DOT_FIELDS` usage** (FilterPanel.tsx lines 76–85): The mobile filter-modified dot checks `FILTER_DOT_FIELDS` from shared FilterState PLUS `severityFilter.length > 0`:
```typescript
const isModified = useMemo(
  () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS) || severityFilter.length > 0,
  [appliedFilters, severityFilter],
);
```

---

### `frontend/src/components/library/SeverityBadge.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCard.tsx` — `resultIndicator` chip (lines 71–82)

The existing result indicator is a small pill with icon + color classes. SeverityBadge follows the same shape but uses severity colors from theme.ts.

**Result indicator pattern** (GameCard.tsx lines 71–82):
```tsx
const resultIndicator = (
  <span
    className={cn(
      'inline-flex items-center justify-center rounded border h-3.5 w-3.5 shrink-0',
      RESULT_CLASSES[game.user_result],
    )}
    aria-label={game.user_result}
  >
    <ResultIcon className="h-2.5 w-2.5" strokeWidth={3} />
  </span>
);
```

**SeverityBadge shape** (new, adapts the inline chip pattern to a count pill):
```tsx
interface SeverityBadgeProps {
  severity: 'blunder' | 'mistake' | 'inaccuracy';
  count: number;
  gameId: number;
}

// Colors imported from theme.ts: SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY
// Background = color at 14% alpha, border = color at 30% alpha
export function SeverityBadge({ severity, count, gameId }: SeverityBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap"
      style={{
        color: SEV_COLORS[severity],
        backgroundColor: SEV_BG_COLORS[severity],
        borderColor: SEV_BORDER_COLORS[severity],
      }}
      aria-label={`${count} ${severity}s`}
      data-testid={`severity-${severity}-${gameId}`}
    >
      <span className="text-base font-bold">{count}</span>
      <span className="text-sm font-bold">{SEVERITY_LABELS[severity]}</span>
    </span>
  );
}
```

---

### `frontend/src/components/library/TagChip.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCard.tsx` (chip inline pattern)

TagChip renders a family-colored display-only chip. Colors from theme.ts (`FAM_TEMPO`, `FAM_OPPORTUNITY`, `FAM_IMPACT`).

```tsx
interface TagChipProps {
  tag: FlawTag;
  gameId: number;
}

export function TagChip({ tag, gameId }: TagChipProps) {
  const { color, bg } = TAG_FAMILY_COLORS[getTagFamily(tag)];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 cursor-pointer text-sm font-bold hover:brightness-115 hover:-translate-y-px transition-all"
      style={{ color, backgroundColor: bg, borderColor: color }}
      aria-label={`Tag: ${tag} (not yet linked)`}
      data-testid={`chip-${tag}-${gameId}`}
    >
      <TagIcon tag={tag} className="h-3 w-3" />
      {tag}
    </span>
  );
}
```

---

### `frontend/src/components/library/NoAnalysisState.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCard.tsx` — `openingLine` pill (lines 136–143)

Simple dashed pill, no logic. Per UI-SPEC:
```tsx
export function NoAnalysisState({ gameId }: { gameId: number }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-dashed px-3 py-1 text-sm font-bold text-muted-foreground bg-white/5"
      aria-label="No engine analysis available for this game"
      data-testid={`no-analysis-${gameId}`}
    >
      <span className="h-2 w-2 rounded-full border border-muted-foreground" />
      No engine analysis
    </span>
  );
}
```

---

### `frontend/src/components/library/FlawStatsPanel.tsx` (component, request-response)

**Analog:** `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` (panel shell + header pattern, lines 144–170)

Panel shell pattern:
```tsx
<section
  className="border border-border rounded-lg p-4"
  style={{ background: 'var(--color-surface)' }}
  aria-label="Flaw statistics"
  data-testid="flaw-stats-panel"
>
  {/* Header row: title + toggle + denominator */}
  <div className="flex items-center gap-3">
    <h2 className="text-lg font-bold font-brand">Flaw-Stats</h2>
    {/* NormToggle component */}
    {/* DenominatorPill component */}
  </div>
  {/* Zone 1: FlawStatsBand */}
  {/* Zone 2: FlawTrendChart */}
  {/* Zone 3: FlawTagDistribution */}
</section>
```

The `isError` branch must show: `"Failed to load flaw statistics. Something went wrong. Please try again in a moment."` (CLAUDE.md rule).

---

### `frontend/src/components/library/FlawTrendChart.tsx` (component, request-response)

**Analog:** `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` — full file

**Recharts pattern** (EndgameScoreOverTimeChart.tsx lines 182–311):
```tsx
import { Area, AreaChart, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { SEV_BLUNDER } from '@/lib/theme';

// Use AreaChart (single series) per UI-SPEC.
// Area fill: SEV_BLUNDER at 32% opacity with gradient fading to 0 (use <defs>/<linearGradient>).
// Line stroke: SEV_BLUNDER / stroke-width 2.5.
// Dots: dot={{ r: 3, fill: SEV_BLUNDER }}.
// No CartesianGrid (no grid lines on charcoal).
// X-axis tickFormatter: date strings.
// Empty state: when trend.length < 2, render text fallback inside the container.

<ChartContainer config={{}} className="w-full h-48" data-testid="flaw-trend-chart">
  <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}>
    <defs>
      <linearGradient id="blunderGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={SEV_BLUNDER} stopOpacity={0.32} />
        <stop offset="100%" stopColor={SEV_BLUNDER} stopOpacity={0} />
      </linearGradient>
    </defs>
    <XAxis dataKey="date" tickFormatter={...} tick={{ fill: 'var(--color-text-muted)' }} />
    <YAxis hide />
    <ChartTooltip ... />
    <Area
      type="monotone"
      dataKey="rate"
      stroke={SEV_BLUNDER}
      strokeWidth={2.5}
      fill="url(#blunderGradient)"
      dot={{ r: 3, fill: SEV_BLUNDER }}
      isAnimationActive={false}
    />
  </AreaChart>
</ChartContainer>
```

Container wrapper (per UI-SPEC): `background: var(--color-charcoal)` / `border: 1px solid var(--color-border)` / `border-radius: var(--radius-md)` / `padding: 16px` / `margin-top: 16px`.

---

### `frontend/src/components/library/FlawStatsBand.tsx` (component, request-response)

**Analog:** Endgames stat-band cells pattern (inline cells in Endgames.tsx)

Four flex cells. Each cell per UI-SPEC:
```tsx
<div
  className="flex-1 min-w-[120px] rounded border border-border p-3"
  style={{ background: '#161412' }}  // var(--color-charcoal)
  data-testid={`stat-cell-${cellKey}`}
>
  <p className="text-2xl font-bold" style={{ color: cellColor }}>{displayValue}</p>
  <p className="text-sm font-bold uppercase text-muted-foreground">{label}</p>
</div>
```

The normalization toggle (`per game` / `per 100 moves`) is local state in FlawStatsPanel; it is passed to FlawStatsBand as a prop to select `rates.per_game` vs `rates.per_100_moves`.

---

### `frontend/src/components/library/FlawTagDistribution.tsx` (component, request-response)

**Analog:** `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` (bar-track pattern)

Three sub-columns (desktop grid, mobile stack). Each rate bar row:
```tsx
// 3-column label | track | value grid
<div className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
  <span className="text-sm text-muted-foreground font-bold">{label}</span>
  <div className="h-2 rounded-full" style={{ background: 'oklch(1 0 0 / 7%)' }}>
    <div
      className="h-2 rounded-full"
      style={{ width: `${rate * 100}%`, background: fillColor }}
    />
  </div>
  <span className="text-sm font-bold">{(rate * 100).toFixed(0)}%</span>
</div>
```

Stacked bar for tempo (full-width, proportional segments, `height: 14px`):
```tsx
<div className="flex h-[14px] rounded-full overflow-hidden" data-testid="tempo-stacked-bar">
  {segments.map(({ key, width, color }) => (
    <div key={key} style={{ width: `${width}%`, background: color }} />
  ))}
</div>
```

Segments: `low-clock` / `impatient` / `considered` / unmeasured remainder (`FAM_TEMPO_UNMEASURED`). Width = count / total_mb_flaws * 100. Omit unmeasured segment only when it is zero.

---

### `frontend/src/pages/library/LibraryPage.tsx` (MODIFIED)

**Analog:** itself (lines 1–124)

**Changes:**
1. Add third `TabsTrigger` value `"games"` with `BookOpen` or `Library` icon, `data-testid="tab-games"` (desktop) / `data-testid="tab-games-mobile"` (mobile).
2. Add corresponding `TabsContent value="games"` with `<GamesTab />`.
3. Update `activeTab` derivation (line 35) to detect `/games`.
4. Update default redirect (lines 28–33) from `'/library/overview'` to `'/library/games'`:

```typescript
// BEFORE (line 33):
return <Navigate to={noGames ? '/library/import' : '/library/overview'} replace />;

// AFTER:
return <Navigate to={noGames ? '/library/import' : '/library/games'} replace />;
```

**TabsTrigger addition pattern** (LibraryPage.tsx lines 53–57, copy and adapt):
```tsx
<TabsTrigger value="games" data-testid="tab-games" className="flex-1">
  <BookOpen className="mr-1.5 h-4 w-4" />
  Games
</TabsTrigger>
```

Apply to BOTH desktop Tabs block (lines 47–70) and mobile Tabs block (lines 73–119).

---

### `frontend/src/lib/theme.ts` (MODIFIED)

**Analog:** itself — existing semantic-color blocks (lines 14–25 for WDL, lines 35–38 for zones)

**Placement:** Add the new tag-family and severity blocks immediately after the `WDL_BORDER_*` constants (line 24). Add phase histogram constants in the same section.

**Pattern to follow** (theme.ts lines 14–24 — the WDL block):
```typescript
// Severity colors (B/M/I — flaw stats panel and library game cards)
export const SEV_BLUNDER = 'oklch(0.58 0.19 25)';
export const SEV_MISTAKE = 'oklch(0.70 0.16 55)';
export const SEV_INACCURACY = 'oklch(0.82 0.13 95)';

// Tag families (flaw chip color-by-family)
export const FAM_TEMPO = 'oklch(0.70 0.17 290)';
export const FAM_TEMPO_BG = 'oklch(0.70 0.17 290 / 0.15)';
export const FAM_TEMPO_LOW_CLOCK = 'oklch(0.74 0.16 290)';
export const FAM_TEMPO_IMPATIENT = 'oklch(0.62 0.15 300)';
export const FAM_TEMPO_CONSIDERED = 'oklch(0.50 0.13 305)';
export const FAM_TEMPO_UNMEASURED = 'oklch(0.40 0 0)';
export const FAM_OPPORTUNITY = 'oklch(0.72 0.12 200)';
export const FAM_OPPORTUNITY_BG = 'oklch(0.72 0.12 200 / 0.15)';
export const FAM_IMPACT = 'oklch(0.66 0.18 330)';
export const FAM_IMPACT_BG = 'oklch(0.66 0.18 330 / 0.15)';

// Phase histogram bar fills
export const PHASE_OPENING = 'oklch(0.62 0.06 70)';
export const PHASE_MIDDLEGAME = 'oklch(0.62 0.10 230)';
export const PHASE_ENDGAME = 'oklch(0.62 0.12 300)';
```

All these constants are defined exactly per UI-SPEC §Color — never hard-code these values in components.

---

### `app/schemas/library.py` (MODIFIED — D-01)

**Analog:** itself — `result_changing_rate: float` field at line 104

`TagDistribution` currently ends at line 105. Add three flat float fields immediately after `result_changing_rate`, mirroring it exactly:

```python
class TagDistribution(BaseModel):
    tempo: dict[TempoTag, int]
    result_changing_rate: float
    phase_histogram: dict[Literal["opening", "middlegame", "endgame"], int]
    # D-01: Opportunity and Impact rates (Phase 107).
    # Each = count / total M+B flaws; 0.0 when there are no M+B flaws.
    # Flat floats, consistent with result_changing_rate precedent (no nested dicts).
    miss_rate: float
    lucky_escape_rate: float
    while_ahead_rate: float
```

---

### `app/services/library_service.py` (MODIFIED — D-01)

**Analog:** itself — `_compute_tag_distribution` lines 325–356

Add three counters in the existing tag-walk loop. The loop already iterates `flaw["tags"]` for every M+B flaw.

**Current function body** (library_service.py lines 333–355):
```python
tempo: dict[TempoTag, int] = {tag: 0 for tag in _TEMPO_TAGS}
phase_histogram: dict[...] = {"opening": 0, "middlegame": 0, "endgame": 0}
total_flaws = 0
result_changing = 0
for gf in per_game:
    for flaw in gf.flaws:
        total_flaws += 1
        for tag in flaw["tags"]:
            if tag in _TEMPO_TAGS:
                tempo[tag] += 1
            elif tag in _PHASE_TAG_TO_KEY:
                phase_histogram[_PHASE_TAG_TO_KEY[tag]] += 1
            elif tag == _RESULT_CHANGING_TAG:
                result_changing += 1
rate = result_changing / total_flaws if total_flaws > 0 else 0.0
return TagDistribution(
    tempo=tempo,
    result_changing_rate=rate,
    phase_histogram=phase_histogram,
)
```

**Modified version** (add three counters + three rate fields):
```python
# D-01: add counters alongside result_changing
miss_count = 0
lucky_escape_count = 0
while_ahead_count = 0

# In the tag loop, add after the result_changing branch:
elif tag == "miss":
    miss_count += 1
elif tag == "lucky-escape":
    lucky_escape_count += 1
elif tag == "while-ahead":
    while_ahead_count += 1

# Rate computations (same pattern as result_changing_rate):
miss_rate = miss_count / total_flaws if total_flaws > 0 else 0.0
lucky_escape_rate = lucky_escape_count / total_flaws if total_flaws > 0 else 0.0
while_ahead_rate = while_ahead_count / total_flaws if total_flaws > 0 else 0.0

return TagDistribution(
    tempo=tempo,
    result_changing_rate=rate,
    phase_histogram=phase_histogram,
    miss_rate=miss_rate,
    lucky_escape_rate=lucky_escape_rate,
    while_ahead_rate=while_ahead_rate,
)
```

---

### `tests/services/test_library_service.py` (MODIFIED — D-01)

**Analog:** itself — `TestFlawStats.test_result_changing_rate_and_distribution` (lines 483–531)

Add new test methods to `TestFlawStats` using the same `_seed_db_game` / `_seed_db_pos` helpers and the existing `_make_flaw` / `_compute_tag_distribution` unit-test approach.

**Pattern to follow** (test_library_service.py lines 483–531):
```python
@pytest.mark.asyncio
async def test_miss_rate_and_lucky_escape_rate(self, db_session: object) -> None:
    """1 miss + 1 lucky-escape out of 2 M+B flaws -> rates == 0.5 each."""
    # ... seed game with flaws tagged "miss" and "lucky-escape" ...
    assert resp.tag_distribution.miss_rate == pytest.approx(0.5)
    assert resp.tag_distribution.lucky_escape_rate == pytest.approx(0.5)

@pytest.mark.asyncio
async def test_while_ahead_rate(self, db_session: object) -> None:
    """1 while-ahead of 2 M+B flaws -> while_ahead_rate == 0.5."""
    # ...
    assert resp.tag_distribution.while_ahead_rate == pytest.approx(0.5)

@pytest.mark.asyncio
async def test_rates_zero_when_no_mb_flaws(self, db_session: object) -> None:
    """0 M+B flaws -> all three new rates are 0.0 (no ZeroDivisionError)."""
    # Use the chess.com (no eval) game from test_empty_analyzed_set_returns_zeros pattern
    assert resp.tag_distribution.miss_rate == 0.0
    assert resp.tag_distribution.lucky_escape_rate == 0.0
    assert resp.tag_distribution.while_ahead_rate == 0.0
```

Note: the `_compute_tag_distribution` function can also be tested as a pure unit test (no DB) using `_make_flaw(["miss", ...])` — follow `TestCardChips` style (lines 234–267) for zero-overhead rate assertions.

---

## Shared Patterns

### TanStack Query hooks for library data
**Source:** `frontend/src/hooks/useEndgames.ts` (full file — 68 lines)
**Apply to:** new `useLibraryGames` and `useLibraryFlawStats` hooks (create in `frontend/src/hooks/useLibrary.ts`)

```typescript
// Copy buildEndgameParams → buildLibraryParams (same structure, drop color/matchSide)
function buildLibraryParams(filters: FilterState, severity: ('blunder' | 'mistake')[]) {
  const dateParams = dateRangeToWireParams(resolveDateRange(filters));
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    ...dateParams,
    rated: filters.rated,
    opponent_type: filters.opponentType,
    opponent_strength: filters.opponentStrength,
    severity: severity.length > 0 ? severity : undefined,
  };
}

export function useLibraryGames(filters: FilterState, severity: ('blunder'|'mistake')[], offset: number, limit: number) {
  const params = buildLibraryParams(filters, severity);
  return useQuery({
    queryKey: ['library-games', params, offset, limit],
    queryFn: () => libraryApi.getGames({ ...params, offset, limit }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

export function useLibraryFlawStats(filters: FilterState, severity: ('blunder'|'mistake')[]) {
  const params = buildLibraryParams(filters, severity);
  return useQuery({
    queryKey: ['library-flaw-stats', params],
    queryFn: () => libraryApi.getFlawStats(params),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

### isError branches (mandatory, CLAUDE.md)
**Apply to:** All `useQuery` chains in `GamesTab`, `FlawStatsPanel`

Every `useQuery` result chain must follow this pattern:
```tsx
if (isError) {
  return <p className="text-sm text-muted-foreground">Failed to load [X]. Something went wrong. Please try again in a moment.</p>;
}
```
Never let errors fall through to empty-state messages.

### FilterState and FILTER_DOT_FIELDS
**Source:** `frontend/src/components/filters/FilterPanel.tsx` lines 40–85
**Apply to:** `GamesTab`, `LibraryFilterPanel`

- `FilterState` interface is unchanged — import and use as-is.
- `FILTER_DOT_FIELDS` covers the shared filter dimensions.
- `severityFilter: ('blunder' | 'mistake')[]` is local state in `GamesTab`, passed down as a prop. It is NOT added to `FilterState`.
- The mobile filter-dot is lit when `!areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS) || severityFilter.length > 0`.

### Recharts on charcoal (no grid lines)
**Source:** `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` lines 188–211
**Apply to:** `FlawTrendChart`

- No `<CartesianGrid>` element.
- `<ChartContainer config={{}} className="w-full h-48">` wraps `<AreaChart>`.
- X-axis tick color via `tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}`.
- `isAnimationActive={false}` on all data series.

---

## No Analog Found

All files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `frontend/src/pages/`, `frontend/src/components/results/`, `frontend/src/components/filters/`, `frontend/src/components/charts/`, `frontend/src/hooks/`, `frontend/src/lib/`, `app/schemas/`, `app/services/`, `tests/services/`
**Files scanned:** ~20 source files read in full or targeted sections
**Pattern extraction date:** 2026-06-05
