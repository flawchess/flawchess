# Phase 92: Custom date range filter — Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 30 new/modified (matches RESEARCH.md exhaustive audit)
**Analogs found:** 28 / 30 (calendar.tsx and CustomRangeDrawer.tsx have no in-repo analog — see §No Analog Found)

This document points every new/changed file at the closest existing analog in the FlawChess codebase and quotes the exact lines to copy from. Where the analog IS the file being edited (e.g. modifying FilterPanel.tsx — analog IS FilterPanel.tsx itself at the recency block), the row points to the specific line range.

---

## File Classification

### Frontend — New files

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `frontend/src/components/ui/calendar.tsx` | ui-primitive | event-driven | (none — shadcn registry install) | none — see §No Analog Found |
| `frontend/src/components/filters/CustomRangePopover.tsx` | component (desktop) | event-driven | `frontend/src/components/ui/info-popover.tsx` (Popover wrapping) + `frontend/src/components/filters/OpponentStrengthFilter.tsx` (filter sub-component shape) | role-match |
| `frontend/src/components/filters/CustomRangeDrawer.tsx` | component (mobile) | event-driven | `frontend/src/components/ui/drawer.tsx` (Drawer primitives) — nested usage has no in-repo precedent | partial — see §No Analog Found |
| `frontend/src/lib/recency.ts` | utility | pure transform | `frontend/src/lib/opponentStrength.ts` (preset↔range conversions with named-export utility shape) | exact |
| `frontend/src/lib/__tests__/recency.test.ts` | test | unit | `frontend/src/lib/__tests__/opponentStrength.test.ts` (parallel test file) | exact |

### Frontend — Modified files

| File | Role | Data Flow | Analog (this phase's pattern source) | Notes |
|------|------|-----------|--------------------------------------|-------|
| `frontend/src/components/filters/FilterPanel.tsx` | component | event-driven | Self — extend lines 173-195 (Recency Select block) | Add 9th SelectItem + Popover/Drawer wiring |
| `frontend/src/hooks/useFilterStore.ts` | store | request-response | Self — module-level useSyncExternalStore at lines 1-37 | Add `customRange` field; no shape change to the store mechanism |
| `frontend/src/hooks/useStats.ts` (4 hooks) | hook | request-response | Self — `useRatingHistory` lines 8-21 is the canonical recency-consuming hook | Replicate migration across `useGlobalStats`, `useMostPlayedOpenings`, `useBookmarkPhaseEntryMetrics` |
| `frontend/src/hooks/useOpenings.ts` | hook | request-response | Self — full file (33 LOC) | Drop `recency`, spread `dateRangeToWireParams(...)` |
| `frontend/src/hooks/useNextMoves.ts` | hook | request-response | Self — full file (39 LOC) | Same migration as useOpenings |
| `frontend/src/hooks/useEndgames.ts` | hook | request-response | `useOpenings.ts` (same migration shape) | Apply identical pattern |
| `frontend/src/hooks/useEndgameInsights.ts` | hook | request-response | `useOpenings.ts` | Apply identical pattern |
| `frontend/src/hooks/useOpeningInsights.ts` | hook | request-response | `useStats.ts::useRatingHistory` (uses `normalizedRecency` derived value) | Replace `normalizedRecency` slot with date wire params |
| `frontend/src/api/client.ts` | api-builder | request-response | Self — `buildFilterParams` lines 75-97 | Replace `recency` branch with `from_date`/`to_date` |
| `frontend/src/types/api.ts` | type | n/a | Self — line 38 | Rename `Recency` → `RecencyPreset`, drop API mention in comment |
| `frontend/src/types/position_bookmarks.ts` | type | n/a | Self — line 52 | **REMOVE** `recency` field (D-19) |
| `frontend/src/types/stats.ts` | type | n/a | Self — `BookmarkPhaseEntryRequest.recency` at line 96 | Replace with `from_date`/`to_date` strings |
| `frontend/src/pages/{Openings,Endgames,GlobalStats,Home}.tsx` | page | event-driven | Self — `Openings.tsx:289` / `GlobalStats.tsx:17-28` | Drop `recency` from query inputs; keep "recency" as user-facing label text |
| `frontend/src/components/insights/{Opening,Endgame}InsightsBlock.tsx` | component | request-response | Self — existing modified-filter detector | Compare `customRange` alongside `recency` against DEFAULT_FILTERS |

### Backend — New helpers / changes

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `tests/test_query_utils.py` (NEW) | test | unit | `tests/test_openings_repository.py` (existing repository tests calling `apply_game_filters` indirectly) | role-match |

### Backend — Modified files

| File | Role | Data Flow | Analog (pattern source) | Notes |
|------|------|-----------|-------------------------|-------|
| `app/repositories/query_utils.py` | repository-helper | SQL-builder | Self — `apply_game_filters` lines 12-77 | Replace `recency_cutoff` slot with `from_date`/`to_date` |
| `app/schemas/openings.py` | schema | wire | Self — `OpeningsRequest` lines 9-49 (existing `recency` Literal + `field_validator`) + `app/schemas/insights.py:357-371` (`@model_validator(mode="after")` examples) | 2 schemas migrate, 1 (`TimeSeriesRequest`) drops the field |
| `app/schemas/insights.py` | schema | wire | Self — `FilterContext` lines 133-147 + own `model_validator` lines 357-371 | Switch `recency` Literal to two date fields |
| `app/schemas/stats.py` | schema | wire | `app/schemas/openings.py::OpeningsRequest` (full pattern) | `BookmarkPhaseEntryRequest` looser-typed `recency: str \| None` → typed dates |
| `app/schemas/opening_insights.py` | schema | wire | `app/schemas/openings.py::OpeningsRequest` | Same Literal → dates swap |
| `app/routers/stats.py` | router | request-response | Self — `get_rating_history` lines 23-45 | Replace `recency: str \| None = Query(...)` with two `date.date \| None` Query params + inline 422 |
| `app/routers/endgames.py` | router | request-response | `app/routers/stats.py::get_rating_history` | Same pattern |
| `app/routers/insights.py` | router | request-response | Self — lines 54-88 (`_validate_full_history_filters` gate) | Update blocking-list message to "Clear Custom date range filter" |
| `app/services/openings_service.py` | service | orchestration | Self — `recency_cutoff` helper lines 137-145 (DELETE) + `RECENCY_DELTAS` dict lines 56-64 (DELETE) | Refactor-on-sight: dead code after FE owns conversion |
| `app/services/{stats,endgame,opening_insights}_service.py` | service | orchestration | `openings_service.py` (parameter rename pattern) | Mechanical signature change `recency_cutoff=` → `from_date=, to_date=` |
| `app/services/insights_service.py` | service | orchestration | Self — lines 152-165 (two-window structure) | Switch internal windows: `recency="3months"` → `from_date=today-90d, to_date=None` |
| `app/repositories/{openings,endgame,stats}_repository.py` | repository | SQL | Self — every callsite of `apply_game_filters` | Mechanical signature change |

---

## Pattern Assignments

### `frontend/src/lib/recency.ts` (utility, pure transform)

**Analog:** `frontend/src/lib/opponentStrength.ts`

**Why this analog:** Same role (pure utility in `lib/` exporting named functions that convert between UI preset names and a richer richer type), same call surface (named exports, no React, no side effects), same testing convention (`__tests__/opponentStrength.test.ts` sibling file).

**Module shape pattern** (`opponentStrength.ts:1-25`):
```typescript
import type { OpponentStrengthPreset, OpponentStrengthRange } from '@/types/api';

// Constants block at the top — domain limits as named exports.
export const SLIDER_MIN = -200;
export const SLIDER_MAX = 200;
export const SLIDER_STEP = 50;

export const PRESET_THRESHOLD = 100;
export const STRONG_WEAK_THRESHOLD = 50;

export const ANY_RANGE: OpponentStrengthRange = { min: null, max: null };

export const PRESET_RANGES: Record<OpponentStrengthPreset, OpponentStrengthRange> = {
  any: ANY_RANGE,
  stronger: { min: STRONG_WEAK_THRESHOLD, max: null },
  similar: { min: -PRESET_THRESHOLD, max: PRESET_THRESHOLD },
  weaker: { min: null, max: -STRONG_WEAK_THRESHOLD },
};
```

**Preset → range conversion pattern** (`opponentStrength.ts:48-51`):
```typescript
/** Inverse of derivePreset — preset name → range. */
export function presetToRange(preset: OpponentStrengthPreset): OpponentStrengthRange {
  return PRESET_RANGES[preset];
}
```

**Wire-param builder pattern** (`opponentStrength.ts:106-113`) — this is the model for `dateRangeToWireParams`:
```typescript
/**
 * Build the API query params for the opponent-gap filter. Returns an empty
 * object when both bounds are null so unbounded filters don't appear in the
 * query string at all.
 */
export function rangeToQueryParams(
  range: OpponentStrengthRange,
): { opponent_gap_min?: number; opponent_gap_max?: number } {
  const params: { opponent_gap_min?: number; opponent_gap_max?: number } = {};
  if (range.min !== null) params.opponent_gap_min = range.min;
  if (range.max !== null) params.opponent_gap_max = range.max;
  return params;
}
```

**Apply to recency.ts:** Export `presetToDates(preset, now?)`, `dateToWire(d)`, `dateRangeToWireParams(range)` named functions with the same shape. The reference implementation in RESEARCH.md §Code Examples lines 808-866 is correct and copy-pastable; the only project-style additions are JSDoc above each export and named const for the cache size if a bounded LRU is added (not in v1).

**JSDoc preamble pattern** (`relativeDate.ts:1-10`) — when a util has non-obvious memoization or threshold logic, lead with a multi-line block:
```typescript
/**
 * Relative-date formatter for the WDL confidence tooltip "Last played: ..." line.
 *
 * Converts an ISO 8601 timestamp into short human prose ("Just now", ...).
 *
 * Quick task 260508-r61.
 */
```
Recency.ts should open with a similar block citing Phase 92 and explaining the `(preset, today-string)` memoization rationale.

**No magic numbers rule** — the day/week/month conversion constants must be extracted as named consts. `relativeDate.ts:14-30` is the established pattern:
```typescript
const JUST_NOW_THRESHOLD_SECONDS = 30;
const SECONDS_IN_MINUTE = 60;
// ...
```
For `recency.ts` the source presets ARE the named constants (`'week'`, `'3months'`, etc.); the literal `90` days for `_subForPreset('3months')` is handled by `date-fns` `subMonths(now, 3)` which IS the named-constant form. No new magic numbers.

---

### `frontend/src/lib/__tests__/recency.test.ts` (test, unit)

**Analog:** `frontend/src/lib/__tests__/opponentStrength.test.ts`

**Why:** Parallel structure — every public function in `recency.ts` gets a `describe` block; vitest is already configured; the test file location convention (`__tests__/` sibling) is project-wide.

**Test coverage to mirror:**
- `presetToDates('week')` returns `{from: startOfDay(now-1w), to: endOfDay(now)}`
- `presetToDates('all')` returns `{}`
- `presetToDates(null)` returns `{}`
- Cache stability: two calls within the same calendar day return the same object reference (`===`)
- Cache invalidation: calling across a different `now` date string returns a fresh object
- `dateToWire(undefined)` returns `undefined`
- `dateToWire(new Date(2026, 2, 1))` returns `'2026-03-01'` (no timezone leak)

---

### `frontend/src/components/filters/CustomRangePopover.tsx` (component, event-driven, desktop)

**Analog:** `frontend/src/components/ui/info-popover.tsx` for the Radix Popover wrapping; `frontend/src/components/filters/OpponentStrengthFilter.tsx` for the "filter sub-component receiving `value`/`onChange` props" shape.

**Why this analog:** info-popover demonstrates the project's wrapping of `radix-ui` Popover primitives directly (without the `@/components/ui/popover` wrapper) when fine control over portal/animation is needed. The `frontend/src/components/ui/popover.tsx` wrapper IS suitable here — it already re-exports `PopoverAnchor` at lines 40-44 which is the key primitive for D-03's "anchor a Popover to the Select trigger" pattern.

**Popover wrapper imports pattern** (`info-popover.tsx:1-4`):
```typescript
import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { HelpCircle } from "lucide-react"
import { cn } from "@/lib/utils"
```

For CustomRangePopover, prefer the higher-level wrapper at `@/components/ui/popover` (already exports `Popover`, `PopoverAnchor`, `PopoverContent`):
```typescript
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover';
```

**PopoverAnchor + Select anchor pattern** — the project has NO existing example of a Popover anchored to a Select trigger; the closest hint is `popover.tsx:40-44` which exports `PopoverAnchor` for exactly this purpose:
```typescript
function PopoverAnchor({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Anchor>) {
  return <PopoverPrimitive.Anchor data-slot="popover-anchor" {...props} />
}
```
The composition sketch in RESEARCH.md §Pattern 1 (lines 286-318) is the authoritative recipe; copy it verbatim including the `queueMicrotask(() => setPopoverOpen(true))` deferral for the Pitfall 6 focus race.

**Popover content styling** — copy the className from `popover.tsx:31` (the wrapper's default):
```typescript
"z-50 flex w-72 origin-(--radix-popover-content-transform-origin) flex-col gap-2.5 rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-hidden"
```
The `w-72` (288px) is the default Popover width. Single-month Calendar fits in `w-72`; two-month does not (RESEARCH.md Open Question 1 recommends single-month).

**Filter sub-component prop shape** (`FilterPanel.tsx:255-261` showing how `OpponentStrengthFilter` is invoked):
```typescript
{show('opponentStrength') && (
  <OpponentStrengthFilter
    value={filters.opponentStrength}
    onChange={(opponentStrength) => update({ opponentStrength })}
  />
)}
```
Apply identical shape: `<CustomRangePopover value={filters.customRange} onChange={(customRange) => update({ customRange, recency: 'custom' })} anchorRef={triggerRef} open={popoverOpen} onOpenChange={setPopoverOpen} />`.

**Required testids (CLAUDE.md):**
- `data-testid="custom-range-popover"` on the content surface
- `data-testid="filter-recency-custom"` on the 9th SelectItem
- `data-testid="custom-range-calendar"` on the Calendar element
- Calendar day buttons: wrap with `data-testid={`calendar-day-${format(day, 'yyyy-MM-dd')}`}` (RESEARCH.md line 1093)

**text-sm floor:** All text inside CustomRangePopover must be `text-sm` or larger. The `popover.tsx:31` className already sets `text-sm` as the container default, so children inherit. Do not add `text-xs` (the existing FilterPanel "Recency" header at line 175 is grandfathered; do not propagate).

---

### `frontend/src/components/filters/CustomRangeDrawer.tsx` (component, event-driven, mobile)

**Analog (partial):** `frontend/src/components/ui/drawer.tsx` for the Drawer primitive shape; no existing in-repo nested-drawer usage.

**Why partial:** The project's `frontend/src/components/ui/drawer.tsx` does NOT re-export `Drawer.NestedRoot` from vaul. Per RESEARCH.md §Pattern 2 (line 349), the planner must either:
1. Add a `DrawerNested` export to the wrapper, OR
2. Import `NestedRoot` directly from `vaul` in CustomRangeDrawer.tsx.

**Drawer wrapper shape** (`drawer.tsx:1-10`) — the existing `Drawer` re-export pattern that the planner mirrors when adding `DrawerNested`:
```typescript
import * as React from "react"
import { Drawer as DrawerPrimitive } from "vaul"

import { cn } from "@/lib/utils"

function Drawer({
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Root>) {
  return <DrawerPrimitive.Root data-slot="drawer" {...props} />
}
```

**DrawerNested to add (recommended Option 1)** — append to `drawer.tsx` between `Drawer` and `DrawerPortal`:
```typescript
function DrawerNested({
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.NestedRoot>) {
  return <DrawerPrimitive.NestedRoot data-slot="drawer-nested" {...props} />
}
```
And add `DrawerNested` to the bottom `export { ... }` block (`drawer.tsx:92-98`).

**DrawerContent styling** — copy from `drawer.tsx:40-61`. The bottom-direction styling (`data-[vaul-drawer-direction=bottom]:bottom-0`, `max-h-[80vh]`, `rounded-t-xl`) is already set up; the nested drawer reuses `DrawerContent` unchanged.

**Apply CTA button pattern** — copy from `FilterPanel.tsx:316-327` (the Reset button):
```typescript
<Button
  type="button"
  variant="brand-outline"
  size="lg"
  className="w-full min-h-11 sm:min-h-0"
  data-testid="btn-reset-filters"
  onClick={...}
>
  Reset Filters
</Button>
```
For the Apply CTA, swap `variant="brand-outline"` → `variant="default"` (primary action per CLAUDE.md §Frontend — Primary vs secondary buttons), `data-testid="btn-apply-custom-range"`, label `Apply`, and disable when `!range?.from` (D-15 frontend prevention).

**Backdrop dismiss = Cancel (D-08):** No special code needed — vaul `Drawer.NestedRoot`'s default `onOpenChange={setOpen(false)}` triggered by backdrop click does NOT commit the range. Only the Apply onClick handler should call `onChange({ customRange: range, recency: 'custom' })`.

**Required testids:**
- `data-testid="drawer-custom-range"` on the DrawerContent
- `data-testid="btn-apply-custom-range"` on the Apply button

---

### `frontend/src/components/ui/calendar.tsx` (ui-primitive, NEW from shadcn registry)

**Analog:** None — file is written by `npx shadcn@latest add calendar`.

**Pattern notes:**
- Source: shadcn registry JSON at https://ui.shadcn.com/r/styles/new-york-v4/calendar.json (verified in RESEARCH.md line 1031)
- Install command: `cd frontend && npx shadcn@latest add calendar`
- File path written: `frontend/src/components/ui/calendar.tsx`
- Transitive deps auto-added: `react-day-picker@10.0.1`, `date-fns@4.2.1`
- The registry-emitted file uses the same `cn(...)` + `data-slot` conventions already used by `popover.tsx` and `drawer.tsx`, so no patches needed.
- **Post-install:** verify the registry's `range_start` / `range_middle` / `range_end` className slots use existing theme tokens (`bg-primary`, `bg-accent`) and not raw hex. If the registry version uses raw hex, swap to theme tokens per CLAUDE.md §Frontend — Theme constants.
- **Day-cell `data-testid`:** The registry-emitted file does NOT add `data-testid` per CLAUDE.md §Browser Automation Rules. Add a wrapper or patch the day-button render so each day cell gets `data-testid={`calendar-day-${format(day.date, 'yyyy-MM-dd')}`}`. RESEARCH.md line 1093 calls this out explicitly.

---

### `frontend/src/components/filters/FilterPanel.tsx` (component, event-driven)

**Analog:** Self — the existing recency Select block at lines 173-195 is the exact extension surface.

**Existing pattern to extend** (lines 173-195):
```typescript
{/* Recency */}
{show('recency') && (
  <div>
    <p className="mb-1 text-xs text-muted-foreground">Recency</p>
    <Select
      value={filters.recency ?? 'all'}
      onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
    >
      <SelectTrigger size="sm" data-testid="filter-recency" className="min-h-11 sm:min-h-0 w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All time</SelectItem>
        <SelectItem value="week">Past week</SelectItem>
        <SelectItem value="month">Past month</SelectItem>
        <SelectItem value="3months">3 months</SelectItem>
        <SelectItem value="6months">6 months</SelectItem>
        <SelectItem value="year">1 year</SelectItem>
        <SelectItem value="3years">3 years</SelectItem>
        <SelectItem value="5years">5 years</SelectItem>
      </SelectContent>
    </Select>
  </div>
)}
```

**Changes:**
1. Add 9th `<SelectItem value="custom" data-testid="filter-recency-custom">Custom range…</SelectItem>` at the bottom.
2. Track a `popoverOpen` state and a `triggerRef`.
3. Wrap the Select in `<Popover open={popoverOpen} onOpenChange={setPopoverOpen}><PopoverAnchor asChild>...</PopoverAnchor><PopoverContent>...</PopoverContent></Popover>` (RESEARCH.md §Pattern 1).
4. When `onValueChange === 'custom'`, defer `setPopoverOpen(true)` via `queueMicrotask` (RESEARCH.md §Pitfall 6).
5. Replace `<SelectValue />` with a custom trigger label resolver that reads `filters.customRange` and renders `format(from, 'MMM d, yyyy') + ' – ' + format(to, 'MMM d, yyyy')` when both bounds set, or `'From <date>'` / `'Until <date>'` when only one (RESEARCH.md Open Question 2 recommends symmetric "From X" / "Until Y").
6. Branch desktop vs mobile via the existing `useBreakpoint` (or whatever FilterPanel currently uses for the mobile drawer split — verify in the page-level wrapper since FilterPanel itself does not currently split).

**existing label note (text-xs):** Line 175's `<p className="mb-1 text-xs text-muted-foreground">Recency</p>` is grandfathered. Do NOT change it (CONTEXT.md notes pre-rule) and do NOT propagate `text-xs` into new Calendar/popover/drawer UI.

**FilterState shape update** — extend lines 17-30:
```typescript
export interface FilterState {
  // ... existing fields
  recency: RecencyPreset | 'custom' | null;          // 'custom' = look at customRange
  customRange: { from?: Date; to?: Date } | null;    // null = no custom range
}
```
And DEFAULT_FILTERS (lines 33-42): `recency: null, customRange: null`.

**`FILTER_DOT_FIELDS` extension** (lines 51-59): add `'customRange'` so the modified-dot lights when a custom range is set.

**`areFiltersEqual` extension** (lines 70-97): add a structural-compare branch for `customRange` similar to the existing `opponentStrength` case at lines 88-93:
```typescript
if (key === 'customRange') {
  const ar = av as FilterState['customRange'];
  const br = bv as FilterState['customRange'];
  if (ar === null && br === null) continue;
  if (ar === null || br === null) return false;
  if (ar.from?.getTime() === br.from?.getTime() && ar.to?.getTime() === br.to?.getTime()) continue;
  return false;
}
```

---

### `frontend/src/hooks/useFilterStore.ts` (store, request-response)

**Analog:** Self — full file (37 LOC).

**Why:** The store mechanism (module-level state + `useSyncExternalStore`) is correct and unchanged. Only the *value shape* changes via `DEFAULT_FILTERS` (imported from FilterPanel). No edits to this file are likely needed — verify after the FilterPanel `DEFAULT_FILTERS` extension lands.

**Existing pattern** (lines 1-7):
```typescript
import { useSyncExternalStore, useCallback } from 'react';
import { DEFAULT_FILTERS, type FilterState } from '@/components/filters/FilterPanel';

let currentFilters: FilterState = { ...DEFAULT_FILTERS };
const listeners = new Set<() => void>();
```

---

### `frontend/src/hooks/useStats.ts` (4 hooks: useRatingHistory, useGlobalStats, useMostPlayedOpenings, useBookmarkPhaseEntryMetrics)

**Analog:** Self — `useRatingHistory` lines 8-21 is the canonical recency-consuming hook.

**Existing pattern** (lines 8-21):
```typescript
export function useRatingHistory(
  recency: Recency | null,
  platforms: Platform[] | null,
  opponentType: OpponentType,
  opponentStrength: OpponentStrengthRange,
) {
  const normalizedRecency = recency === 'all' ? null : recency;
  const platform = platforms && platforms.length === 1 ? platforms[0]! : null;
  return useQuery({
    queryKey: ['ratingHistory', normalizedRecency, platform, opponentType, opponentStrength.min, opponentStrength.max],
    queryFn: () => statsApi.getRatingHistory(normalizedRecency, platform, opponentType, opponentStrength),
  });
}
```

**Target pattern (apply to all 4 hooks):**
```typescript
export function useRatingHistory(
  filters: FilterState,            // or accept individual fields; consistent with current call sites
  // ... unchanged params
) {
  const dateParams = useDateRangeWireParams(filters); // new shared helper from recency.ts
  return useQuery({
    queryKey: ['ratingHistory', dateParams.from_date ?? null, dateParams.to_date ?? null, platform, ...],
    queryFn: () => statsApi.getRatingHistory(dateParams, platform, ...),
  });
}
```

**The `normalizedRecency` slot** in the query key (line 18, 33, 54, 87) becomes two slots `from_date` and `to_date`. RESEARCH.md §TanStack Query Key Audit recommends one of:
- Two slots `dateParams.from_date ?? null, dateParams.to_date ?? null`
- Single derived string `'${from_date ?? ''}|${to_date ?? ''}'`

Prefer two slots for searchability in React Query DevTools.

**`useBookmarkPhaseEntryMetrics` is the 7th hook (Pitfall 4)** — lines 66-107. Apply the same migration; this hook is NOT in CONTEXT.md D-13's list of six but breaks silently otherwise. RESEARCH.md §Pitfall 4 line 774-782 flags this explicitly.

---

### `frontend/src/hooks/useOpenings.ts`, `useNextMoves.ts`, `useEndgames.ts`, `useEndgameInsights.ts`, `useOpeningInsights.ts`

**Analog:** Each is the analog for the others — five hooks with the same shape (spread `filters` into a request body and query key).

**`useOpenings.ts` (full file, 33 LOC)** is the cleanest reference:
```typescript
export function useOpeningsPositionQuery(params: {
  targetHash: string;
  filters: FilterState;
  offset: number;
  limit: number;
}) {
  return useQuery<OpeningsResponse>({
    queryKey: ['openingsPosition', params.targetHash, params.filters, params.offset, params.limit],
    queryFn: async () => {
      const response = await apiClient.post<OpeningsResponse>('/openings/positions', {
        target_hash: params.targetHash,
        match_side: resolveMatchSide(params.filters.matchSide, params.filters.color),
        time_control: params.filters.timeControls,
        platform: params.filters.platforms,
        rated: params.filters.rated,
        opponent_type: params.filters.opponentType,
        ...rangeToQueryParams(params.filters.opponentStrength),
        recency: params.filters.recency,          // ← REPLACE
        color: params.filters.color,
        offset: params.offset,
        limit: params.limit,
      });
      return response.data;
    },
  });
}
```

**Target:**
```typescript
// At top of file:
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';

// In queryFn body, replace the `recency: params.filters.recency,` line with:
...dateRangeToWireParams(resolveDateRange(params.filters)),
// → spreads { from_date?: 'YYYY-MM-DD'; to_date?: 'YYYY-MM-DD' }
```
Where `resolveDateRange(filters)` returns `presetToDates(filters.recency)` for preset values, OR `filters.customRange` for `recency === 'custom'`. This single helper handles both branches uniformly.

**Query key — note on `params.filters`**: line 15 currently passes the entire `filters` object as a single query-key slot. Because TanStack Query keys are deep-compared, the new `customRange: { from?: Date; to?: Date }` field's Date objects will compare by identity. The memoization in `presetToDates` keeps these stable within a calendar day; for the custom path, the planner needs to ensure `filters.customRange` is also a stable object reference (e.g. from a `useMemo` in the FilterPanel, or normalized on `update()`).

---

### `frontend/src/api/client.ts` (api-builder, request-response)

**Analog:** Self — `buildFilterParams` lines 75-97.

**Existing pattern** (lines 75-97):
```typescript
export function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  recency?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  opponent_strength?: OpponentStrengthRange;
  window?: number;
}): Record<string, string | string[] | number | boolean> {
  const result: Record<string, string | string[] | number | boolean> = {};
  if (params.time_control) result.time_control = params.time_control;
  if (params.platform) result.platform = params.platform;
  if (params.recency && params.recency !== 'all') result.recency = params.recency;
  if (params.rated !== null && params.rated !== undefined) result.rated = params.rated;
  // ...
}
```

**Target — replace lines 78, 87:**
```typescript
export function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  from_date?: string | null;     // NEW (replaces recency)
  to_date?: string | null;       // NEW
  rated?: boolean | null;
  // ... unchanged
}): Record<string, string | string[] | number | boolean> {
  const result: Record<string, string | string[] | number | boolean> = {};
  if (params.time_control) result.time_control = params.time_control;
  if (params.platform) result.platform = params.platform;
  if (params.from_date) result.from_date = params.from_date;   // NEW
  if (params.to_date) result.to_date = params.to_date;         // NEW
  // ... unchanged
}
```

And update the `statsApi.getRatingHistory`/`getGlobalStats`/`getMostPlayedOpenings` and `endgameApi.getOverview`/`getGames` signatures (lines 126-208) to accept `from_date` / `to_date` strings instead of `recency: string | null`.

---

### `frontend/src/types/api.ts` (type)

**Analog:** Self — line 38.

**Existing line:**
```typescript
export type Recency = 'week' | 'month' | '3months' | '6months' | 'year' | '3years' | '5years' | 'all';
```

**Target:**
```typescript
/** UI-only preset, not sent to the API. The wire shape uses from_date/to_date instead. */
export type RecencyPreset = 'week' | 'month' | '3months' | '6months' | 'year' | '3years' | '5years' | 'all';
```

**All 21 files importing `Recency`** — see RESEARCH.md §Recency Call-Site Audit lines 496-545 — must update the import. Most use it as a type-only import; mechanical find/replace `Recency` → `RecencyPreset` covers them. Watch for `useFilterStore.ts` which transitively re-exposes the type via `FilterState`.

---

### `frontend/src/types/position_bookmarks.ts` (type)

**Analog:** Self — line 52.

**REMOVE** (D-19):
```typescript
recency?: 'week' | 'month' | '3months' | '6months' | 'year' | '3years' | '5years' | 'all' | null;
```
And update the comment at line 72 referencing "recency window" → "filter window" or remove if no longer accurate.

---

### `app/repositories/query_utils.py` (repository-helper, SQL-builder)

**Analog:** Self — lines 12-77.

**Existing signature + recency branch** (lines 12-58):
```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,   # ← REPLACE
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
    # ... unchanged filters ...
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    # ... unchanged opponent_gap logic ...
```

**Target — RESEARCH.md §Code Examples lines 880-917:**
```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,       # ← NEW (replaces recency_cutoff)
    to_date: datetime.date | None,         # ← NEW
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
    # ... unchanged filters ...
    # NOTE: Postgres implicitly casts DATE to TIMESTAMPTZ at UTC midnight. A
    # local-day-bounded filter on the FE side leaks up to 24h of boundary
    # games to the result set. Accepted trade-off (Phase 92 §Pitfall 2).
    if from_date is not None:
        stmt = stmt.where(Game.played_at >= from_date)
    if to_date is not None:
        # +1 day to make the upper bound inclusive of the user's selected end date.
        stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    # ... unchanged opponent_gap logic ...
```

**Signature shape decision (RESEARCH.md line 446):** keep both `from_date` and `to_date` as positional in the same slot (replace 1 → 2 positional). All callers update to pass two args. Alternative: keyword-only via `*,` separator — larger churn but safer long-term. Planner picks.

**Optional SQL predicates pattern** — the existing function already demonstrates the "conditionally append `where()`" pattern across all 5 filter blocks (`time_control`, `platform`, `rated`, `opponent_type`, `color`, `opponent_gap_*`). The new date branches mirror this structure exactly: `if param is not None: stmt = stmt.where(...)`.

---

### `app/schemas/openings.py`, `insights.py`, `stats.py`, `opening_insights.py` (schema, wire)

**Analog:** `app/schemas/openings.py::OpeningsRequest` lines 9-49 is the canonical request schema in the project. The `@field_validator` pattern at lines 14-30 (used for `target_hash` BigInt coercion) plus the `@model_validator(mode="after")` pattern at `app/schemas/insights.py:357-371` are the project-idiomatic surfaces for date params.

**Existing `recency` field** (`openings.py:39-41`):
```python
recency: (
    Literal["week", "month", "3months", "6months", "year", "3years", "5years", "all"] | None
) = None
```

**Target** — RESEARCH.md §Code Examples lines 922-954:
```python
import datetime
from pydantic import BaseModel, model_validator

class OpeningsRequest(BaseModel):
    # ... existing fields ...
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    # ... rest unchanged ...

    @model_validator(mode="after")
    def _check_date_range(self) -> "OpeningsRequest":
        if (self.from_date is not None and self.to_date is not None
                and self.from_date > self.to_date):
            raise ValueError("from_date must be <= to_date")
        return self
```

**`@model_validator(mode="after")` reference** (`insights.py:357-371`):
```python
@model_validator(mode="after")
def unique_section_ids(self) -> "EndgameInsightsReport":
    ids = [s.section_id for s in self.sections]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate section_id")
    return self

@model_validator(mode="after")
def recommendations_length(self) -> "EndgameInsightsReport":
    for rec in self.recommendations:
        if not rec.strip():
            raise ValueError("recommendation must not be empty")
        if len(rec) > 200:
            raise ValueError("recommendation exceeds 200 chars")
    return self
```
Pydantic v2 `ValueError` raised from `@model_validator` surfaces as FastAPI 422 (RESEARCH.md §Validation Pattern). No additional router-level check needed for body-shape endpoints.

**Per-schema actions:**
| Schema | Action |
|--------|--------|
| `app/schemas/openings.py::OpeningsRequest` (line 39) | Replace `recency` Literal with `from_date`/`to_date` + `@model_validator` |
| `app/schemas/openings.py::TimeSeriesRequest` (line 153) | **REMOVE** `recency` field entirely (D-19) — no replacement |
| `app/schemas/openings.py::NextMovesRequest` (line 215) | Replace `recency` Literal with `from_date`/`to_date` + `@model_validator` |
| `app/schemas/insights.py::FilterContext` (line 133) | Replace `recency: Literal["all_time", ...] = "all_time"` with `from_date`/`to_date` (default None) |
| `app/schemas/stats.py::BookmarkPhaseEntryRequest` (line 133) | Replace `recency: str \| None` with typed `from_date`/`to_date` |
| `app/schemas/opening_insights.py::OpeningInsightsRequest` (line 29) | Replace `recency` Literal with `from_date`/`to_date` + `@model_validator` |

---

### `app/routers/stats.py`, `endgames.py`, `insights.py` (router, request-response)

**Analog:** `app/routers/stats.py::get_rating_history` lines 23-45 is the canonical Query-param recency consumer.

**Existing pattern** (`stats.py:23-45`):
```python
@router.get("/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    recency: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> RatingHistoryResponse:
    return await stats_service.get_rating_history(
        session,
        user.id,
        recency,
        platform,
        # ...
    )
```

**Target — RESEARCH.md §Validation Pattern lines 687-695:**
```python
@router.get("/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    platform: str | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> RatingHistoryResponse:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await stats_service.get_rating_history(
        session,
        user.id,
        from_date,
        to_date,
        platform,
        # ...
    )
```

**FastAPI auto-coerces `Query()` of type `datetime.date | None`** from ISO `YYYY-MM-DD` strings — no manual parsing needed. Malformed input returns 422 automatically (Pydantic's date parser).

**Inline 422 vs shared dependency:** RESEARCH.md line 697 recommends inline checks across 3 endpoints; defining a `DateRangeQuery` dependency is over-engineering for this scope.

---

### `app/routers/insights.py::_validate_full_history_filters` (router gate)

**Analog:** Self — lines 54-88.

**Existing gate logic** (lines 67-75):
```python
blocking: list[str] = []
if filters.recency != "all_time":
    blocking.append("Switch Recency to All time")
if filters.time_controls:
    blocking.append("Remove Time control filter")
if filters.platforms:
    blocking.append("Remove Platform filter")
if filters.rated_only:
    blocking.append("Remove Rated filter")
```

**Target** (RESEARCH.md §Pitfall 3 lines 765-768):
```python
blocking: list[str] = []
if filters.from_date is not None or filters.to_date is not None:
    blocking.append("Clear Custom date range filter")
if filters.time_controls:
    blocking.append("Remove Time control filter")
# ... unchanged ...
```

---

### `app/services/openings_service.py` (service, dead-code removal)

**Analog:** Self — `RECENCY_DELTAS` dict at lines 55-64 and `recency_cutoff()` helper at lines 137-145.

**Dead code to DELETE** (CLAUDE.md "Refactor bloated code on sight" applies — these become unused after FE owns the conversion):

```python
# Lines 55-64 — DELETE
RECENCY_DELTAS: dict[str, datetime.timedelta] = {
    "week": datetime.timedelta(days=7),
    "month": datetime.timedelta(days=30),
    "3months": datetime.timedelta(days=90),
    "6months": datetime.timedelta(days=180),
    "year": datetime.timedelta(days=365),
    "3years": datetime.timedelta(days=365 * 3),
    "5years": datetime.timedelta(days=365 * 5),
}

# Lines 137-145 — DELETE
def recency_cutoff(recency: str | None) -> datetime.datetime | None:
    """Return a UTC datetime cutoff for the given recency filter, or None."""
    if recency is None or recency == "all":
        return None
    delta = RECENCY_DELTAS[recency]
    return datetime.datetime.now(tz=datetime.timezone.utc) - delta
```

**Every callsite** (RESEARCH.md lines 562-568 enumerates) that imports `recency_cutoff` from `openings_service` must drop the import. Pattern: `cutoff = recency_cutoff(request.recency)` → just pass `from_date=request.from_date, to_date=request.to_date` straight to the repository.

---

### `app/services/insights_service.py` (service, internal LLM windows)

**Analog:** Self — lines 152-165 (two-window structure).

**Existing pattern** (lines 150-165, paraphrased per RESEARCH.md):
```python
# all_time window
recency=None,
# ...
# last_3mo window
recency="3months",
```

**Target** (RESEARCH.md lines 467-473, Open Question 4 line 1076):
```python
# all_time window
from_date=None,
to_date=None,
# ...
# last_3mo window — replicate existing recency_cutoff("3months") semantics exactly
from_date=datetime.date.today() - datetime.timedelta(days=90),
to_date=None,
```

**Key detail (Open Question 4):** Use `to_date=None`, NOT `to_date=datetime.date.today()`. The existing `recency_cutoff("3months")` returns only a from-side cutoff; preserving exact semantics avoids unintended LLM cache-key drift.

---

### `app/services/{stats,endgame,opening_insights}_service.py` (service, parameter rename)

**Analog:** `app/services/openings_service.py` — every callsite of `apply_game_filters(...)` passing `recency_cutoff=cutoff`.

**Mechanical change pattern:** Find every call to `apply_game_filters(stmt, ..., recency_cutoff=...)` and replace the `recency_cutoff` kwarg with `from_date=..., to_date=...`. Two changes per call site.

**Per-service touch counts** (RESEARCH.md lines 564-572):
- `stats_service.py`: ~22 callsites
- `endgame_service.py`: ~22 callsites
- `opening_insights_service.py`: ~6 callsites

---

### `app/repositories/{openings,endgame,stats}_repository.py` (repository, parameter rename)

**Analog:** Self — every existing function signature accepting `recency_cutoff: datetime.datetime | None`.

**Mechanical change:** signature accepts `from_date: datetime.date | None, to_date: datetime.date | None`; pass through to `apply_game_filters`. RESEARCH.md lines 570-575 enumerates ~80 distinct line refs across the three files.

---

### `tests/test_query_utils.py` (test, NEW)

**Analog:** `tests/test_openings_repository.py` (existing test file calling `apply_game_filters` indirectly via repository functions).

**Why:** No direct unit tests of `apply_game_filters` exist (RESEARCH.md line 1004). This phase adds the missing direct unit-test surface. The repository-level tests will continue to test the integration path.

**Tests to add** (RESEARCH.md §Phase Requirements → Test Map lines 985-989):
- `test_apply_game_filters_date_range` — both bounds set produces correct SQL window
- `test_apply_game_filters_no_date_filter` — both omitted = no date predicate
- `test_apply_game_filters_from_only` — from_date only = `played_at >= from_date`, no upper bound
- `test_apply_game_filters_to_only` — to_date only = `played_at < to_date + 1 day`, no lower bound

---

## Shared Patterns

### Authentication
**Source:** `app/users.py::current_active_user`
**Apply to:** All router endpoints (already applied — no change for this phase)

No new auth surface. Existing `Annotated[User, Depends(current_active_user)]` dependency on every router endpoint is unaffected.

### Pydantic 422 validation
**Source:** `app/schemas/insights.py:357-371` (`@model_validator(mode="after")`)
**Apply to:** Every Pydantic request schema that gains `from_date`/`to_date` fields (`OpeningsRequest`, `NextMovesRequest`, `OpeningInsightsRequest`, `BookmarkPhaseEntryRequest`, `FilterContext`)

```python
@model_validator(mode="after")
def _check_date_range(self) -> "OpeningsRequest":
    if (self.from_date is not None and self.to_date is not None
            and self.from_date > self.to_date):
        raise ValueError("from_date must be <= to_date")
    return self
```

**Source for Query-param validation:** RESEARCH.md §Validation Pattern lines 687-695
**Apply to:** Every router endpoint with `from_date`/`to_date` as `Query()` params (`stats.py`, `endgames.py`, `insights.py`)

```python
if from_date is not None and to_date is not None and from_date > to_date:
    raise HTTPException(status_code=422, detail="from_date must be <= to_date")
```

### Date wire format
**Source:** new `frontend/src/lib/recency.ts::dateToWire`
**Apply to:** Every hook constructing a request body (`useOpenings`, `useNextMoves`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`, all 4 hooks in `useStats.ts`)

ISO `YYYY-MM-DD` strings only (no time component, no UTC suffix). Backend FastAPI coerces to `datetime.date`. RESEARCH.md §Anti-Patterns line 385 warns against ISO datetime strings.

### TanStack Query key shape
**Source:** `frontend/src/hooks/useStats.ts::useRatingHistory` line 18
**Apply to:** Every recency-consuming hook

Replace the single `normalizedRecency` slot with two slots `from_date ?? null, to_date ?? null`. Cache stability is preserved by `presetToDates` memoization on `(preset, today-YYYY-MM-DD)`.

### `data-testid` naming convention
**Source:** `FilterPanel.tsx` existing testids (`filter-time-control-bullet`, `filter-platform-chess-com`, `filter-recency`, `filter-opponent-human`)
**Apply to:** All new Custom Range UI

Proposed names:
- `filter-recency-custom` — the 9th SelectItem
- `custom-range-popover` — desktop Popover content
- `drawer-custom-range` — mobile DrawerContent
- `custom-range-calendar` — Calendar element (both desktop and mobile)
- `calendar-day-${YYYY-MM-DD}` — individual day buttons (wrapping the shadcn-emitted Day component)
- `btn-apply-custom-range` — mobile Apply CTA
- `btn-clear-custom-range` — optional "Clear" button inside popover/drawer if planner adds one

### `text-sm` minimum
**Source:** CLAUDE.md §Frontend; existing exception at `FilterPanel.tsx:175` (grandfathered)
**Apply to:** All text inside Calendar, CustomRangePopover, CustomRangeDrawer, and the Select trigger label

The existing `popover.tsx:31` className already sets `text-sm` on the container default. The existing `drawer.tsx:50` className sets `text-sm` on DrawerContent. Children inherit. Do NOT add `text-xs` anywhere in new UI text. The shadcn-emitted Calendar typically uses default font-size; verify after install that day-cell text is `text-sm` or larger (or override via className prop).

### Theme constants
**Source:** `frontend/src/lib/theme.ts` (per CLAUDE.md §Frontend)
**Apply to:** Calendar range-highlight colors

If the shadcn-emitted `calendar.tsx` uses raw hex for `range_start` / `range_middle` / `range_end`, replace with theme tokens. Likely the registry version already uses `bg-primary` / `bg-accent` which inherit from the project's Tailwind config — verify after install.

### Mobile-first parity
**Source:** CLAUDE.md §Frontend — "Always apply changes to mobile too"
**Apply to:** The two-renderer split (CustomRangePopover desktop / CustomRangeDrawer mobile) IS the mobile parity for this phase — both surfaces render the same logical feature (a Calendar in range mode) with parity on testids, value contract, and trigger-label rendering.

---

## No Analog Found

Files with no close in-repo match. Planner should rely on RESEARCH.md and external sources.

| File | Role | Reason | Fallback |
|------|------|--------|----------|
| `frontend/src/components/ui/calendar.tsx` | ui-primitive | New shadcn registry file; no existing date-picker UI in the codebase | Run `npx shadcn@latest add calendar` (RESEARCH.md §Standard Stack lines 130-135); verify range-mode className slots use theme tokens; patch day cells to add `data-testid={`calendar-day-${...}`}` per CLAUDE.md §Browser Automation Rules |
| `frontend/src/components/filters/CustomRangeDrawer.tsx` | component (mobile, nested-drawer pattern) | `Drawer.NestedRoot` from vaul has no in-repo precedent — `frontend/src/components/ui/drawer.tsx` does not re-export it | RESEARCH.md §Pattern 2 lines 322-349 documents the vaul API and the `DrawerNested` wrapper to add. Compose with existing `DrawerContent`/`DrawerOverlay` which already support `data-[vaul-drawer-direction=bottom]` styling |

---

## Metadata

**Analog search scope:**
- `frontend/src/components/` (filter components, UI primitives, popovers)
- `frontend/src/lib/` (utility module conventions)
- `frontend/src/hooks/` (TanStack Query hook shape)
- `frontend/src/types/` (type-only exports)
- `app/schemas/` (Pydantic v2 patterns: `field_validator`, `model_validator`)
- `app/routers/` (FastAPI Query params, validation patterns)
- `app/repositories/` (SQL builder helper)
- `app/services/` (service-layer signatures)

**Files scanned:** 18 read in full, 5 grep'd for cross-reference, ~30 enumerated via Bash grep

**Key patterns identified:**
- All `lib/` utilities follow named-export + sibling `__tests__/*.test.ts` convention; `opponentStrength.ts` is the closest in spirit to the new `recency.ts`
- All Pydantic v2 schemas use `BaseModel` + `Annotated[..., Field(...)]` for constraint params + `@field_validator(mode="before")` for type coercion + `@model_validator(mode="after")` for cross-field invariants
- All FastAPI routers use `APIRouter(prefix=..., tags=[...])` with relative paths in decorators and inline `HTTPException(status_code=422, ...)` for cross-field invariants on Query-param endpoints
- `apply_game_filters` is the SINGLE source of truth for game filtering per CLAUDE.md §Shared Query Filters — every change to filter shape lands here once
- `text-sm` floor is enforced by Tailwind defaults in `popover.tsx:31` and `drawer.tsx:50`; the FilterPanel's `text-xs` Recency header at line 175 is the documented grandfathered exception

**Pattern extraction date:** 2026-05-21
