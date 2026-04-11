---
phase: 260411-fcs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/GlobalStats.tsx
autonomous: true
requirements:
  - QUICK-260411-fcs
user_setup: []

must_haves:
  truths:
    - "A full-width 'Reset Filters' button is rendered at the bottom of the FilterPanel on all pages (Openings desktop sidebar + mobile drawer, Endgames desktop sidebar + mobile drawer, GlobalStats desktop sidebar + mobile drawer)"
    - "Clicking 'Reset Filters' restores ONLY the filter fields that the panel renders (per visibleFilters) to their DEFAULT_FILTERS values. Fields outside the panel (e.g. color/matchSide on Endgames, color/matchSide on Openings when Reset is clicked inside FilterPanel, everything-but-platform+recency on GlobalStats) are untouched. This prevents cross-page side effects via the shared filter store."
    - "Below the Reset Filters button, a small muted helper line 'Filter changes apply on closing the filters panel' is visible ONLY in FilterPanel instances that use deferred apply (both Endgames desktop sidebar and Endgames mobile drawer, AND the Openings mobile drawer — since that drawer also commits on close)"
    - "The helper line is NOT visible in Openings desktop sidebar, GlobalStats desktop sidebar, or GlobalStats mobile drawer (all immediate-apply)"
    - "The sidebar strip filter button on Openings desktop shows a small 'modified' dot whenever the applied filter store differs from DEFAULT_FILTERS"
    - "The sidebar strip filter button on Endgames desktop shows the same modified dot when appliedFilters (not pendingFilters) differs from DEFAULT_FILTERS"
    - "The sidebar strip filter button on GlobalStats desktop shows the modified dot when the visible subset of filters (platform, recency) differs from defaults — other filter fields are irrelevant on that page"
    - "The mobile filter trigger button (btn-open-filter-drawer on Endgames and GlobalStats, btn-open-filter-sidebar on Openings) shows the same modified dot under the same conditions as its desktop counterpart"
    - "On Endgames, when the desktop sidebar panel or mobile drawer closes AND pendingFilters differs from appliedFilters at close time, the modified indicator pulses once (animation visible for ~900-1200ms) as feedback that a new query is firing"
    - "On Openings mobile drawer, when the drawer closes AND localFilters differs from filters at close time, the indicator pulses once (same behavior — drawer also defers apply)"
    - "On Openings desktop and GlobalStats (desktop + mobile), no one-shot pulse fires — the indicator simply tracks the live applied state since filter changes apply immediately"
    - "The modified indicator does not conflict with the existing 'filters hint' ping animation on Openings (which is a one-time onboarding hint, dismissed via localStorage). When both conditions are true, the onboarding hint takes visual precedence — once dismissed, the modified indicator appears normally"
    - "All new interactive elements have kebab-case, component-prefixed data-testid attributes"
    - "All colors for the Reset button and modified dot come from existing Tailwind theme tokens (border-border, text-muted-foreground, bg-toggle-active, etc.) or new constants added to frontend/src/lib/theme.ts — no hardcoded hex/oklch values in components"
    - "npm run lint, npm run knip, npm run test, and tsc --noEmit (via npm run build) all pass with zero errors"
  artifacts:
    - path: "frontend/src/components/filters/FilterPanel.tsx"
      provides: "Reset button (panel-scoped default), deferred-apply helper text, areFiltersEqual helper exported, showDeferredApplyHint + onReset props on FilterPanel"
      contains: "areFiltersEqual"
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "Deferred-apply wiring: passes showDeferredApplyHint={true} to FilterPanel in both sidebar and drawer (no onReset override — uses FilterPanel's panel-scoped default); one-shot pulse effect on panel/drawer close when pending ≠ applied; modified dot on sidebar strip filter button and mobile btn-open-filter-drawer"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Desktop sidebar: showDeferredApplyHint={false} (immediate apply), no onReset override (panel-scoped default preserves Played-as/Piece filter controls outside the panel), modified dot on sidebar strip filter button. Mobile drawer: showDeferredApplyHint={true} (drawer commits on close), no onReset override, modified dot on btn-open-filter-sidebar, one-shot pulse on drawer close when localFilters ≠ filters at close time"
    - path: "frontend/src/pages/GlobalStats.tsx"
      provides: "Desktop sidebar + mobile drawer: showDeferredApplyHint={false} (immediate apply), no onReset override (panel-scoped default naturally resets only platform+recency), modified dot on filter triggers driven by areFiltersEqual restricted to platform + recency"
  key_links:
    - from: "frontend/src/components/filters/FilterPanel.tsx"
      to: "frontend/src/pages/Endgames.tsx"
      via: "FilterPanel props (showDeferredApplyHint) and exported areFiltersEqual helper; panel-scoped reset via default onReset behavior"
      pattern: "FilterPanel.*showDeferredApplyHint"
    - from: "frontend/src/pages/Endgames.tsx"
      to: "sidebar strip notification dot"
      via: "SidebarPanelConfig.notificationDot prop + useEffect watching appliedFilters for pulse trigger"
      pattern: "notificationDot.*appliedFilters"
    - from: "frontend/src/pages/Openings.tsx"
      to: "SidebarLayout panel config"
      via: "notificationDot prop composition — existing onboarding hint OR new modified-dot"
      pattern: "notificationDot.*(showFiltersHint|modified)"
---

<objective>
Add a "Reset Filters" full-width button to the shared FilterPanel, a deferred-apply hint text
below it (only visible on panels that commit on close), and a "modified" indicator dot on the
sidebar/mobile filter trigger button that pulses once when a deferred commit actually fires.

Purpose: Three usability gaps surfaced in user testing:
1. No quick way to clear all filters back to defaults
2. Users don't realise the Endgames panel defers apply until close (Openings applies live), and nothing tells them
3. When the panel is closed, there's no visual reminder that the current query is non-default

Output: Updated FilterPanel with Reset + hint, and updated Endgames/Openings/GlobalStats pages
that wire the modified-dot + (Endgames + Openings-mobile only) one-shot pulse on commit.

IMPORTANT: Reset is panel-scoped everywhere. The default `onReset` behavior in FilterPanel
only resets fields listed in `visibleFilters`, preserving everything else. No page overrides
onReset — the default is correct for all consumers. This prevents cross-page side effects via
the shared filter store (e.g. Endgames Reset must not clobber Openings' color/matchSide, and
Openings desktop Reset inside FilterPanel must not clobber the Played-as/Piece filter controls
that live OUTSIDE the FilterPanel component).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/hooks/useFilterStore.ts
@frontend/src/components/layout/SidebarLayout.tsx
@frontend/src/pages/Endgames.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/pages/GlobalStats.tsx
@frontend/src/lib/theme.ts
@frontend/src/components/ui/button.tsx

<interfaces>
<!-- Extracted from the codebase — executor should use these directly, no scouting needed. -->

From frontend/src/components/filters/FilterPanel.tsx (current, BEFORE changes):
```typescript
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null;      // null = all
  platforms: Platform[] | null;            // null = all
  rated: boolean | null;                   // null = all
  opponentType: OpponentType;              // default 'human'
  opponentStrength: OpponentStrength;      // default 'any'
  recency: Recency | null;                 // null = all time
  color: Color;
}

export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'both',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: 'any',
  recency: null,
  color: 'white',
};

type FilterField = 'timeControl' | 'platform' | 'rated' | 'opponent' | 'opponentStrength' | 'recency';

interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  visibleFilters?: FilterField[];
}

const ALL_FILTERS: FilterField[] = ['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency'];
```

From frontend/src/hooks/useFilterStore.ts:
```typescript
// Module-level shared store; survives page navigations.
export function useFilterStore(): readonly [FilterState, (next: FilterUpdater) => void];
// Initial state = DEFAULT_FILTERS
```

From frontend/src/components/layout/SidebarLayout.tsx:
```typescript
export interface SidebarPanelConfig {
  id: string;
  label: string;
  icon: ReactNode;
  content: ReactNode;
  headerExtra?: ReactNode;
  notificationDot?: ReactNode;  // already rendered inside the strip button — reuse this
}
```

From frontend/src/pages/Endgames.tsx (deferred-apply state machine — do NOT refactor):
```typescript
const [appliedFilters, setAppliedFilters] = useFilterStore();
const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

// handleSidebarOpenChange commits pendingFilters -> appliedFilters when panel closes.
// handleMobileFiltersOpenChange commits pendingFilters -> appliedFilters when drawer closes.
// Both then call setGamesOffset(0).
```

From frontend/src/pages/Openings.tsx:
```typescript
const [filters, setFilters] = useFilterStore();
const [localFilters, setLocalFilters] = useState<FilterState>(filters); // MOBILE DRAWER ONLY
// Desktop uses filters + handleFiltersChange directly (live apply).
// Mobile drawer uses localFilters + commits via handleFilterSidebarOpenChange on close.
// Played-as / Piece filter ToggleGroups live OUTSIDE FilterPanel — Reset inside the panel must not reach them.
```

From frontend/src/pages/GlobalStats.tsx:
```typescript
// Uses filters directly everywhere — immediate apply, no localFilters, no pendingFilters.
// visibleFilters={['platform', 'recency']} — only those two matter for the dot.
```

From frontend/src/components/ui/button.tsx — available variants:
`default | outline | brand-outline | secondary | ghost | destructive | link`
Sizes: `default | xs | sm | lg | icon | icon-xs | icon-sm | icon-lg`
</interfaces>

<existing_patterns>
<!-- Patterns already in the codebase — executor should copy these exactly. -->

EXISTING sidebar notification dot pattern (Openings.tsx for onboarding hints — REUSE this markup):
```tsx
notificationDot: showFiltersHint ? (
  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-notification-dot">
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
) : undefined,
```
Note: `bg-red-500` is used for the existing onboarding hint. For the "modified filters" dot,
use a DIFFERENT semantic color (see theme.ts additions below) to avoid visually colliding
with the onboarding hint and to signal "info, not warning".
</existing_patterns>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Extend FilterPanel with Reset button, deferred-apply hint, areFiltersEqual helper, and theme tokens for the modified-dot</name>
  <files>
    frontend/src/components/filters/FilterPanel.tsx
    frontend/src/lib/theme.ts
  </files>
  <action>
## 1a. Add theme tokens in `frontend/src/lib/theme.ts`

Append new constants at the bottom of theme.ts (keep existing content untouched):

```typescript
// Modified-filter indicator dot — signals "current query uses non-default filters".
// Uses brand brown to differentiate from the existing red onboarding-hint dot.
// Tailwind classes (referenced in components): bg-brand-brown, text-brand-brown.
// The raw oklch is here for any JS-side usage (currently none).
export const FILTER_MODIFIED_DOT = 'oklch(0.55 0.08 55)'; // brand brown mid
```

IMPORTANT: `bg-brand-brown` / `text-brand-brown` are already defined Tailwind tokens in the project (used by the onboarding hint HelpCircle icon: `text-brand-brown/70`, and by `brand-outline` button variant: `border-brand-brown-light/50`). Verify by grepping `brand-brown` — if the `bg-brand-brown` variant does not exist as-is, use `bg-brand-brown-light` instead. Do NOT hardcode hex colors.

If NEITHER `bg-brand-brown` nor `bg-brand-brown-light` exists as a Tailwind class, fall back to `bg-toggle-active` (also already used elsewhere for semantic "active/modified" UI state in this codebase — see the mobile filter button). Pick whichever concrete Tailwind utility is already registered. Comment the choice in code: `// modified-filters dot — uses <token> (see theme.ts FILTER_MODIFIED_DOT)`.

## 1b. Export `areFiltersEqual` helper from `FilterPanel.tsx`

Add after `DEFAULT_FILTERS`:

```typescript
/**
 * Compare two FilterState values for equality, treating array fields (timeControls, platforms)
 * as set-equal regardless of order. Used to detect "filters are modified from defaults" for
 * the sidebar modified-indicator dot.
 *
 * If `fields` is provided, only those FilterState keys are compared — used by GlobalStats
 * which only exposes platform + recency (other fields must be ignored even if non-default).
 */
// eslint-disable-next-line react-refresh/only-export-components
export function areFiltersEqual(
  a: FilterState,
  b: FilterState,
  fields?: ReadonlyArray<keyof FilterState>,
): boolean {
  const keys = fields ?? (Object.keys(a) as (keyof FilterState)[]);
  for (const key of keys) {
    const av = a[key];
    const bv = b[key];
    if (av === bv) continue;
    // Both null already handled by === above; handle array set-equality
    if (Array.isArray(av) && Array.isArray(bv)) {
      if (av.length !== bv.length) return false;
      const setB = new Set<string>(bv as readonly string[]);
      if (!(av as readonly string[]).every((v) => setB.has(v))) return false;
      continue;
    }
    return false;
  }
  return true;
}
```

Notes:
- `timeControls` and `platforms` are `T[] | null`, so after the `===` short-circuit only (array, array) pairs remain for those fields. Do NOT cross-compare array vs null — that's already `!==`.
- The `// eslint-disable-next-line react-refresh/only-export-components` is required because this file is a component file that also exports non-component values (same pattern already used for `DEFAULT_FILTERS`).
- `noUncheckedIndexedAccess`: iterating `keys` is fine because `a[key]` is narrowed by the union type; no index-access warnings.

## 1c. Extend `FilterPanelProps`

```typescript
interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  visibleFilters?: FilterField[];
  /** When true, shows a muted helper line below the Reset button explaining deferred apply. */
  showDeferredApplyHint?: boolean;
  /**
   * Called when the user clicks the Reset Filters button. If omitted, Reset applies
   * DEFAULT_FILTERS via onChange RESTRICTED to the visibleFilters subset — i.e. panel-scoped.
   * This is the correct behavior for every current consumer; no page should override this.
   * The prop exists only as an escape hatch for hypothetical future consumers that need
   * to do additional work on reset (e.g. reset gamesOffset alongside the filter reset).
   */
  onReset?: () => void;
}
```

Signature:
```typescript
export function FilterPanel({
  filters,
  onChange,
  visibleFilters = ALL_FILTERS,
  showDeferredApplyHint = false,
  onReset,
}: FilterPanelProps) {
```

## 1d. Add the Reset button + hint text below all existing filter sections

Inside the existing root `<div className="space-y-3">`, AFTER the final filter section (Rated), add:

```tsx
{/* Reset Filters — full panel width, below the last filter row.
    PANEL-SCOPED by default: only resets fields listed in `visibleFilters`, preserving
    everything else in the shared filter store. This prevents cross-page side effects —
    e.g. Endgames Reset must not clobber Openings' color/matchSide, and clicking Reset
    inside the Openings desktop FilterPanel must not reach the Played-as/Piece filter
    ToggleGroups that live OUTSIDE FilterPanel. */}
<div className="pt-2 border-t border-border/40">
  <Button
    type="button"
    variant="outline"
    size="sm"
    className="w-full min-h-11 sm:min-h-0"
    data-testid="btn-reset-filters"
    onClick={() => {
      if (onReset) {
        onReset();
        return;
      }
      // Default behavior: reset only the visible subset, preserve hidden fields.
      // This is panel-scoped and correct for EVERY current consumer.
      const patch: Partial<FilterState> = {};
      for (const field of visibleFilters) {
        // Map FilterField -> FilterState key. Most are 1:1 except 'timeControl' -> 'timeControls'.
        if (field === 'timeControl') patch.timeControls = DEFAULT_FILTERS.timeControls;
        else if (field === 'platform') patch.platforms = DEFAULT_FILTERS.platforms;
        else if (field === 'rated') patch.rated = DEFAULT_FILTERS.rated;
        else if (field === 'opponent') patch.opponentType = DEFAULT_FILTERS.opponentType;
        else if (field === 'opponentStrength') patch.opponentStrength = DEFAULT_FILTERS.opponentStrength;
        else if (field === 'recency') patch.recency = DEFAULT_FILTERS.recency;
      }
      onChange({ ...filters, ...patch });
    }}
  >
    Reset Filters
  </Button>
  {showDeferredApplyHint && (
    <p
      className="mt-2 text-[11px] leading-tight text-muted-foreground"
      data-testid="filter-deferred-apply-hint"
    >
      Filter changes apply on closing the filters panel.
    </p>
  )}
</div>
```

Import `Button` from `@/components/ui/button` at the top of FilterPanel.tsx (add to the existing import block).

## 1e. Scope boundary reminders

- The Reset button lives INSIDE FilterPanel (root `<div className="space-y-3">`), so it renders automatically in every consumer: Openings desktop (wrapped by extra piece-filter markup in desktopFilterPanelContent), Openings mobile drawer, Endgames desktop sidebar, Endgames mobile drawer, GlobalStats desktop sidebar, GlobalStats mobile drawer.
- DO NOT touch the Openings desktop "Piece filter" / "Played as" ToggleGroups — those live OUTSIDE FilterPanel in `desktopFilterPanelContent` and `Openings.tsx` drawer markup. The panel-scoped default reset already leaves them alone.
- Do NOT change the `DEFAULT_FILTERS` constant.
- Do NOT add tests in this task (covered by overall success criteria: lint/knip/tsc/build pass).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm run knip</automated>
  </verify>
  <done>
- `areFiltersEqual` is exported from FilterPanel.tsx and handles null/array/scalar cases correctly
- FilterPanel renders a Reset button + conditional hint text at the bottom
- Reset button uses existing theme-driven Button variant ("outline"), no hardcoded colors
- Reset button default `onClick` is panel-scoped: resets only fields in `visibleFilters`, preserves all other filter store fields
- `showDeferredApplyHint` and `onReset` props added, both optional with sensible defaults
- theme.ts has the new `FILTER_MODIFIED_DOT` constant
- `npm run lint`, `tsc --noEmit`, and `npm run knip` all pass
- No knip warnings about unused exports (`areFiltersEqual` will be imported in Tasks 2 & 3)
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Wire Endgames page — modified dot with one-shot pulse on commit + deferred-apply hint (panel-scoped Reset via FilterPanel default)</name>
  <files>
    frontend/src/pages/Endgames.tsx
  </files>
  <action>
## 2a. Import additions

```typescript
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual } from '@/components/filters/FilterPanel';
import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
```

(Append `useMemo` and `useRef` to the existing React imports; append `DEFAULT_FILTERS, areFiltersEqual` to the existing FilterPanel import.)

Note: `DEFAULT_FILTERS` is imported for the `areFiltersEqual` comparison in the modified-dot logic (2b), NOT for a reset override. Reset is handled by FilterPanel's panel-scoped default.

## 2b. Add pulse state + modified computation

Add inside `EndgamesPage` component, near the other useState hooks (after `sidebarOpen`):

```typescript
// ── Modified-filters indicator state ────────────────────────────────────────
// The dot reflects APPLIED filters (what the backend is filtering by), not pending.
// When appliedFilters changes away from defaults via a commit, pulse once.
const isModified = useMemo(
  () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS),
  [appliedFilters],
);
const [isPulsing, setIsPulsing] = useState(false);
const pulseTimeoutRef = useRef<number | null>(null);
const prevAppliedRef = useRef(appliedFilters);

useEffect(() => {
  // Pulse once whenever appliedFilters transitions to a new value (i.e. a commit fired).
  // Skip the initial mount and skip no-op updates.
  if (prevAppliedRef.current !== appliedFilters) {
    prevAppliedRef.current = appliedFilters;
    // Only pulse if the new state is "modified" — pulsing on "reset to defaults" is also
    // useful feedback, so don't gate on isModified. Just pulse on any real commit.
    setIsPulsing(true);
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current);
    }
    pulseTimeoutRef.current = window.setTimeout(() => {
      setIsPulsing(false);
      pulseTimeoutRef.current = null;
    }, 1000); // ~1s pulse duration
  }
  return () => {
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current);
      pulseTimeoutRef.current = null;
    }
  };
}, [appliedFilters]);
```

Note on the effect: on initial mount `prevAppliedRef.current === appliedFilters` (both equal to the useFilterStore initial snapshot), so no pulse fires on page load. Subsequent changes to `appliedFilters` (via `setAppliedFilters(pendingFilters)` in `handleSidebarOpenChange` or `handleMobileFiltersOpenChange`) will trigger the pulse. Comment this in code.

## 2c. Build the notification dot markup

Add a helper const BEFORE the sidebar config:

```tsx
const modifiedDotNode = isModified ? (
  <span
    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
    data-testid="filters-modified-dot"
    aria-hidden="true"
  >
    {isPulsing && (
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
    )}
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
  </span>
) : undefined;
```

If `bg-brand-brown` is not a registered Tailwind class in the codebase, fall back to `bg-brand-brown-light`, then to `bg-toggle-active`, matching whichever Task 1 used. Pick ONE and be consistent across tasks.

## 2d. Pass `notificationDot` + `showDeferredApplyHint` into the SidebarLayout `panels` config for the filters panel

Replace:
```tsx
{
  id: 'filters',
  label: 'Filters',
  icon: <SlidersHorizontal className="h-5 w-5" />,
  content: (
    <div className="p-3">
      <FilterPanel filters={pendingFilters} onChange={setPendingFilters} />
    </div>
  ),
},
```

With:
```tsx
{
  id: 'filters',
  label: 'Filters',
  icon: <SlidersHorizontal className="h-5 w-5" />,
  notificationDot: modifiedDotNode,
  content: (
    <div className="p-3">
      <FilterPanel
        filters={pendingFilters}
        onChange={setPendingFilters}
        showDeferredApplyHint
      />
    </div>
  ),
},
```

**Reset semantics (CRITICAL — do not add `onReset`):**
- Do NOT pass an `onReset` override here. Use the FilterPanel default.
- The default calls `onChange(...)` (which is `setPendingFilters`) with a merged patch
  restricted to the visible subset. Endgames uses the full `ALL_FILTERS` set, so the patch
  resets every field the panel renders — exactly what the user expects.
- The reset lands in `pendingFilters`; it gets committed to `appliedFilters` on panel close
  like any other pending change, and the existing pulse `useEffect` in 2b will fire naturally.
- Fields NOT rendered by FilterPanel (notably `color` and `matchSide` — shared with Openings
  via the global filter store) are PRESERVED. This is the correct behavior: Reset on Endgames
  must not silently flip Openings' color/matchSide.

## 2e. Wire the mobile filter trigger button

In the mobile sticky row, replace:
```tsx
<Button
  variant="ghost"
  size="icon"
  className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
  onClick={() => setMobileFiltersOpen(true)}
  data-testid="btn-open-filter-drawer"
  aria-label="Open filters"
>
  <SlidersHorizontal className="h-4 w-4" />
</Button>
```

With (note added `relative` and the dot span):
```tsx
<Button
  variant="ghost"
  size="icon"
  className="relative h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
  onClick={() => setMobileFiltersOpen(true)}
  data-testid="btn-open-filter-drawer"
  aria-label="Open filters"
>
  <SlidersHorizontal className="h-4 w-4" />
  {isModified && (
    <span
      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
      data-testid="filters-modified-dot-mobile"
      aria-hidden="true"
    >
      {isPulsing && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
      )}
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
    </span>
  )}
</Button>
```

## 2f. Wire the mobile drawer FilterPanel with deferred-apply hint (NO onReset override)

Replace:
```tsx
<FilterPanel filters={pendingFilters} onChange={setPendingFilters} />
```
(inside the `<Drawer>` content)

With:
```tsx
<FilterPanel
  filters={pendingFilters}
  onChange={setPendingFilters}
  showDeferredApplyHint
/>
```

**Reset semantics:** Same as 2d — do NOT pass an `onReset` override. The FilterPanel default
calls `setPendingFilters` with a panel-scoped patch, which gets committed on drawer close.
Fields outside the panel (color/matchSide) are preserved.

## 2g. Scope boundaries

- DO NOT touch the deferred-apply state machine (`handleSidebarOpenChange`, `handleMobileFiltersOpenChange`). They already commit pending -> applied on close; the pulse useEffect reacts to that commit automatically.
- DO NOT add a separate pulse trigger on close — the `appliedFilters` change IS the trigger.
- DO NOT pulse on pending edits while the panel is open — the useEffect only fires on applied changes.
- DO NOT pass `onReset` to FilterPanel — rely on the panel-scoped default.
- If `bg-brand-brown` isn't a registered Tailwind class, pick one fallback and use it consistently in Tasks 2 and 3. Document the choice in a single-line code comment.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>
- Endgames sidebar strip filter button shows the modified dot whenever `appliedFilters !== DEFAULT_FILTERS`
- Endgames mobile `btn-open-filter-drawer` shows the same dot
- When `setAppliedFilters(pendingFilters)` fires on panel/drawer close (AND the value actually changes), the dot pulses for ~1s via a toggled `animate-ping` span
- FilterPanel in both sidebar and drawer renders the "Filter changes apply on closing the filters panel" helper
- Reset button uses FilterPanel's panel-scoped default: resets fields the Endgames panel displays (via ALL_FILTERS visibleFilters default), preserves `color` and `matchSide`; lands in `pendingFilters` and commits on next close; pulse fires on commit
- No `onReset` override is passed anywhere in Endgames.tsx
- Navigating to Openings after an Endgames Reset preserves Openings' color/matchSide
- No initial-mount pulse, no pulse on no-op commits
- Lint, tsc, build all pass
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Wire Openings + GlobalStats — modified dot, immediate-apply semantics, Openings mobile drawer pulse (panel-scoped Reset via FilterPanel default)</name>
  <files>
    frontend/src/pages/Openings.tsx
    frontend/src/pages/GlobalStats.tsx
  </files>
  <action>
## 3a. Openings.tsx — imports

Add `DEFAULT_FILTERS, areFiltersEqual` to the existing FilterPanel import:
```typescript
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual } from '@/components/filters/FilterPanel';
```

Add `useMemo, useRef, useEffect` to the existing React imports if any are missing (useEffect and useRef are likely already imported; add useMemo).

Note: `DEFAULT_FILTERS` is imported for the `areFiltersEqual` comparison in the modified-dot logic (3b), NOT for a reset override. Reset is handled by FilterPanel's panel-scoped default.

## 3b. Openings.tsx — modified state (desktop is LIVE, mobile drawer defers)

Add near other state hooks (around line 228 area):

```typescript
// ── Modified-filters indicator ─────────────────────────────────────────────
// Desktop: filters apply immediately, so the dot tracks `filters` directly.
// Mobile drawer: defers apply until drawer close, so the dot also tracks `filters`
// (the committed state), and we add a one-shot pulse on drawer close when
// localFilters differed from filters at close time.
const justCommittedFromDrawerRef = useRef(false);
const isFiltersModified = useMemo(
  () => !areFiltersEqual(filters, DEFAULT_FILTERS),
  [filters],
);
const [isFiltersPulsing, setIsFiltersPulsing] = useState(false);
const filtersPulseTimeoutRef = useRef<number | null>(null);
const prevFiltersRef = useRef(filters);

useEffect(() => {
  if (prevFiltersRef.current !== filters) {
    prevFiltersRef.current = filters;
    // On Openings desktop, `filters` changes live as the user toggles — pulsing on every
    // change would be noisy. Only pulse when the mobile drawer JUST closed AND committed
    // a change. We guard via `justCommittedFromDrawerRef` set inside handleFilterSidebarOpenChange.
    if (justCommittedFromDrawerRef.current) {
      justCommittedFromDrawerRef.current = false;
      setIsFiltersPulsing(true);
      if (filtersPulseTimeoutRef.current !== null) {
        window.clearTimeout(filtersPulseTimeoutRef.current);
      }
      filtersPulseTimeoutRef.current = window.setTimeout(() => {
        setIsFiltersPulsing(false);
        filtersPulseTimeoutRef.current = null;
      }, 1000);
    }
  }
  return () => {
    if (filtersPulseTimeoutRef.current !== null) {
      window.clearTimeout(filtersPulseTimeoutRef.current);
      filtersPulseTimeoutRef.current = null;
    }
  };
}, [filters]);
```

(`justCommittedFromDrawerRef` is declared BEFORE the `useEffect` that reads it.)

## 3c. Openings.tsx — set the ref when mobile drawer commits

Inside `handleFilterSidebarOpenChange` (currently around line 487), when the drawer is closing and localFilters differs from filters, set the flag BEFORE calling `handleFiltersChange(localFilters)`:

Change:
```typescript
const handleFilterSidebarOpenChange = useCallback((open: boolean) => {
  if (!open && filterSidebarOpen) {
    handleFiltersChange(localFilters);
    ...
  }
  ...
}, [filterSidebarOpen, localFilters, handleFiltersChange, ...]);
```

To:
```typescript
const handleFilterSidebarOpenChange = useCallback((open: boolean) => {
  if (!open && filterSidebarOpen) {
    // Pulse the filter indicator if the drawer commit actually changes `filters`.
    // Check BEFORE handleFiltersChange runs (which updates `filters`).
    if (!areFiltersEqual(localFilters, filters)) {
      justCommittedFromDrawerRef.current = true;
    }
    handleFiltersChange(localFilters);
    // ... existing logic below unchanged
  }
  // ... existing logic for open branch unchanged
}, [filterSidebarOpen, localFilters, handleFiltersChange, filters, /* existing deps */]);
```

Add `filters` to the dependency array if not already present.

## 3d. Openings.tsx — wire the notificationDot into SidebarLayout panels config

The existing filters panel already has a `notificationDot` for the onboarding hint (`showFiltersHint`). That onboarding hint takes precedence (it's dismissible and pedagogical). Compose both:

Replace:
```tsx
notificationDot: showFiltersHint ? (
  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-notification-dot">
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
) : undefined,
```

With:
```tsx
notificationDot: showFiltersHint ? (
  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-notification-dot">
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
) : isFiltersModified ? (
  <span
    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
    data-testid="filters-modified-dot"
    aria-hidden="true"
  >
    {isFiltersPulsing && (
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
    )}
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
  </span>
) : undefined,
```

## 3e. Openings.tsx — wire desktop FilterPanel props (NO onReset override)

In `desktopFilterPanelContent`, update the FilterPanel call:

```tsx
<FilterPanel
  filters={filters}
  onChange={handleFiltersChange}
/>
```

**Reset semantics (CRITICAL):**
- Do NOT pass `onReset`. Use the FilterPanel default.
- Rationale: the "Played as" and "Piece filter" ToggleGroups are visually OUTSIDE the
  FilterPanel in `desktopFilterPanelContent`. Reset inside the FilterPanel must NOT reach
  across and clear them. The panel-scoped default calls `handleFiltersChange(...)` with a
  patch limited to the fields FilterPanel renders (ALL_FILTERS default) — which does NOT
  include `matchSide` or `color`. Played-as / Piece filter values are preserved.
- The user can flip Played-as / Piece filter manually via their own ToggleGroup controls.
- Do NOT pass `showDeferredApplyHint` — desktop Openings is immediate-apply.

## 3f. Openings.tsx — wire mobile drawer FilterPanel props (NO onReset override)

Find the mobile drawer `<FilterPanel filters={localFilters} onChange={setLocalFilters} />` (around line 1333) and update:

```tsx
<FilterPanel
  filters={localFilters}
  onChange={setLocalFilters}
  showDeferredApplyHint
/>
```

**Reset semantics:**
- Do NOT pass `onReset`. Use the FilterPanel default.
- The drawer defers apply (commits on close), so show the hint.
- The default `onClick` calls `setLocalFilters(...)` with a panel-scoped patch. Reset lands
  in `localFilters` and commits on drawer close like any other pending change. The pulse
  useEffect (3b/3c) will fire on the resulting `handleFiltersChange(localFilters)` commit
  via `justCommittedFromDrawerRef`.
- If the mobile drawer ALSO renders Played-as / Piece filter controls outside the FilterPanel
  (mirror of desktop), they are preserved — the panel-scoped reset does not reach them.
  Verify by grepping the mobile drawer JSX for ToggleGroup / matchSide / pieceFilter usage.

## 3g. Openings.tsx — mobile filter trigger button

Find `btn-open-filter-sidebar` (around line 1239). It already has the onboarding hint dot with precedence. Compose the modified dot:

Replace:
```tsx
<SlidersHorizontal className="h-4 w-4" />
{showFiltersHint && (
  <span
    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
    data-testid="filters-notification-dot-mobile"
  >
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
)}
```

With:
```tsx
<SlidersHorizontal className="h-4 w-4" />
{showFiltersHint ? (
  <span
    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
    data-testid="filters-notification-dot-mobile"
  >
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
) : isFiltersModified ? (
  <span
    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
    data-testid="filters-modified-dot-mobile"
    aria-hidden="true"
  >
    {isFiltersPulsing && (
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
    )}
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
  </span>
) : null}
```

Note the button already has `className="... relative"` (verify — it currently says `"h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"`), so no class change needed.

## 3h. GlobalStats.tsx — imports, modified state, FilterPanel wiring (NO onReset override)

Add to imports:
```typescript
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual } from '@/components/filters/FilterPanel';
import { useState, useCallback, useMemo } from 'react';
```

Inside `GlobalStatsPage` component:

```typescript
// GlobalStats only exposes platform + recency — restrict "modified" detection to those fields.
const isGlobalStatsFiltersModified = useMemo(
  () => !areFiltersEqual(filters, DEFAULT_FILTERS, ['platforms', 'recency'] as const),
  [filters],
);
// NOTE: no pulse on GlobalStats — it's immediate-apply.
```

Update both FilterPanel instances (desktop sidebar AND mobile drawer) to:

```tsx
<FilterPanel
  filters={filters}
  onChange={handleFilterChange}
  visibleFilters={['platform', 'recency']}
/>
```

**Reset semantics (CRITICAL):**
- Do NOT pass `onReset`. Use the FilterPanel default for consistency with Openings/Endgames.
- The default already does exactly the right thing here: with `visibleFilters={['platform', 'recency']}`,
  the panel-scoped patch only touches `platforms` and `recency`. Everything else in the shared
  filter store (color, matchSide, timeControls, rated, opponent*) is preserved — so navigating
  to Openings after a GlobalStats Reset keeps Openings' state untouched.
- Rationale for removing the explicit override: one less place for drift. Relying on the default
  means the truth "Reset is panel-scoped" is enforced by FilterPanel itself, not duplicated
  per page.
- Do NOT pass `showDeferredApplyHint`.

## 3i. GlobalStats.tsx — notification dot on desktop sidebar panel

The current SidebarLayout panels config has no notificationDot. Add it:

```tsx
{
  id: 'filters',
  label: 'Filters',
  icon: <SlidersHorizontal className="h-5 w-5" />,
  notificationDot: isGlobalStatsFiltersModified ? (
    <span
      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
      data-testid="filters-modified-dot"
      aria-hidden="true"
    >
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
    </span>
  ) : undefined,
  content: ( ... ),
}
```

## 3j. GlobalStats.tsx — notification dot on mobile filter button

Find the mobile filter trigger (`btn-open-filter-drawer`, around line 194) and add the dot span INSIDE the Button, adding `relative` to the className:

```tsx
<Button
  variant="ghost"
  size="icon"
  className="relative h-11 w-11 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
  onClick={() => setMobileFiltersOpen(true)}
  data-testid="btn-open-filter-drawer"
  aria-label="Open filters"
>
  <SlidersHorizontal className="h-4 w-4" />
  {isGlobalStatsFiltersModified && (
    <span
      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
      data-testid="filters-modified-dot-mobile"
      aria-hidden="true"
    >
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
    </span>
  )}
</Button>
```

## 3k. Color token fallback reminder

If Task 2 determined that `bg-brand-brown` is not a registered Tailwind token and fell back to `bg-brand-brown-light` or `bg-toggle-active`, use the SAME token in all dot spans added in this task. Grep the project for `bg-brand-brown` to confirm existence before committing — the user explicitly requires no hardcoded colors.

## 3l. Scope boundaries

- DO NOT change Openings' immediate-apply semantics on desktop (live `handleFiltersChange`)
- DO NOT change GlobalStats' immediate-apply semantics (no pending/applied split)
- DO NOT add a pulse on Openings desktop — only on the mobile drawer commit
- DO NOT add a pulse on GlobalStats anywhere
- DO NOT touch the `showFiltersHint` / `showBookmarksHint` onboarding logic — just compose the modified dot as a fallback when the onboarding hint is not showing
- DO NOT pass `onReset` to any FilterPanel instance in this task — rely on the panel-scoped default everywhere
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm run knip && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>
- Openings desktop sidebar strip filter button shows the modified dot (only when onboarding hint is not showing) whenever `filters !== DEFAULT_FILTERS`; no pulse on live changes
- Openings mobile `btn-open-filter-sidebar` shows the same dot under the same precedence rules
- Openings mobile drawer close pulses the indicator ONCE when `localFilters !== filters` at close time
- Openings desktop Reset uses FilterPanel's panel-scoped default: resets timeControl/platform/opponent/opponentStrength/rated/recency; leaves Played-as ("matchSide") and Piece filter ("color") ToggleGroups untouched because they live outside FilterPanel
- Openings mobile drawer Reset uses the panel-scoped default: resets the drawer's FilterPanel fields in `localFilters`; commits on drawer close; Played-as / Piece filter controls (if rendered outside FilterPanel in the drawer) are preserved
- GlobalStats desktop + mobile filter triggers show the modified dot driven by platform+recency diff only (never by color/matchSide/etc. even if modified elsewhere)
- GlobalStats never shows the deferred-apply hint
- GlobalStats Reset uses FilterPanel's panel-scoped default: clears ONLY platforms + recency (via `visibleFilters={['platform', 'recency']}`), preserves color/matchSide/timeControls/rated/opponent* for other pages
- NO `onReset` override is passed to any FilterPanel instance in Openings.tsx or GlobalStats.tsx
- Cross-page check: after clicking Reset on GlobalStats, navigating to Openings preserves its color/matchSide
- Cross-page check: after clicking Reset on Endgames, navigating to Openings preserves its color/matchSide
- All `noUncheckedIndexedAccess` rules respected, no `any`, no ts-ignore
- `npm run lint`, `tsc --noEmit`, `npm run knip`, `npm run build` all pass
- `areFiltersEqual` is imported and used (no knip dead-export warning)
  </done>
</task>

</tasks>

<verification>
## Manual verification checklist (run by user via `npm run dev`)

### Openings page
1. Fresh load (dismiss onboarding hint first via normal UX if present). Confirm no modified dot on sidebar filter button.
2. Click sidebar filter -> change Recency to "Past month". Modified dot appears IMMEDIATELY on the strip button (no pulse, live apply). Close panel: still there, no pulse.
3. Click Reset Filters button inside the desktop panel. Expected: timeControl/platform/opponent/opponentStrength/rated/recency reset; 'Played as' / 'Piece filter' ToggleGroups (outside FilterPanel) remain unchanged. Modified dot updates live based on `filters !== DEFAULT_FILTERS` (should disappear if Played-as/Piece filter are at defaults, otherwise stays).
4. Mobile: open filter drawer, change Recency to "Past month", close drawer. Dot appears on btn-open-filter-sidebar AND pulses once for ~1s.
5. Open drawer again, no changes, close: no pulse (pending === applied).
6. Open drawer, click Reset Filters, see the helper text "Filter changes apply on closing the filters panel" below the Reset button, close drawer. Pulse fires (if there was a committed change); dot state matches `filters !== DEFAULT_FILTERS`.

### Endgames page
7. Fresh load. No dot.
8. Desktop: open filter panel, change Recency. Dot does NOT appear yet (pending ≠ applied, dot tracks applied). Close panel. Dot appears + pulses once.
9. Verify the "Filter changes apply on closing the filters panel" hint text is visible in the desktop panel.
10. Mobile: same test — open drawer, change filter, close. Hint visible inside drawer, dot pulses on mobile filter button after close.
11. Click Reset Filters inside Endgames panel, close panel. Expected: Endgames-visible filters reset in pendingFilters, commit on close fires the pulse, dot reflects new applied state. Then navigate to Openings and verify its color/matchSide are preserved (Endgames Reset must not clobber them).

### GlobalStats page
12. Fresh load. No dot.
13. Change Recency to "Past week". Dot appears immediately (no pulse — live apply).
14. NO "Filter changes apply on closing" helper visible in GlobalStats panel.
15. Click Reset Filters. Platforms + recency reset; dot disappears.
16. Navigate to Openings — verify its color/matchSide filter state is preserved (GlobalStats reset did NOT clobber it).

### Cross-checks
17. On Openings, if the onboarding "filters hint" ping is showing, the modified dot does NOT render simultaneously (onboarding takes precedence). Dismiss hint -> modified dot appears if filters are non-default.
18. No TypeScript errors in `npm run build`.
19. `npm run knip` passes — `areFiltersEqual` is imported and used.
20. All new data-testid values are unique and follow kebab-case conventions.
21. Panel-scoped reset consistency: grep the three page files for `onReset=` — there should be ZERO matches in Openings.tsx, Endgames.tsx, GlobalStats.tsx. The only place `onReset` appears in the codebase is as a prop definition in FilterPanel.tsx.

## Automated verification (CI-equivalent)

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm run knip && npm test && npm run build
```
</verification>

<success_criteria>
- Reset Filters button renders full-width at the bottom of FilterPanel in all 6 consumption points (Openings desktop/mobile, Endgames desktop/mobile, GlobalStats desktop/mobile)
- Reset is PANEL-SCOPED everywhere: only fields in `visibleFilters` are reset, all other shared-filter-store fields are preserved. No page passes `onReset` — the FilterPanel default is used across all 6 instances.
- Deferred-apply hint text is visible in Endgames desktop/mobile AND Openings mobile drawer; invisible everywhere else
- Modified dot tracks applied (not pending) state on all 3 pages
- Pulse-on-commit fires only on Endgames (both desktop/mobile) and Openings mobile drawer; never on Openings desktop or GlobalStats
- All new code uses theme-driven Tailwind classes; zero hardcoded color literals
- Cross-page side effects are eliminated: Reset on any page preserves the other pages' filter state for fields that page doesn't render
- `npm run lint`, `tsc --noEmit`, `npm run knip`, `npm run build`, `npm test` all pass
- Mobile parity: every desktop change has a matching mobile change
</success_criteria>

<output>
After completion, create `.planning/quick/260411-fcs-add-reset-filters-button-deferred-apply-/260411-fcs-SUMMARY.md`
with:
- List of files modified
- Snippet of the `areFiltersEqual` helper signature
- Brief note on the Tailwind color token used for the dot (`bg-brand-brown` or fallback) and why
- Confirmation that Reset is panel-scoped everywhere (no `onReset` overrides in any page)
- Confirmation of lint/tsc/knip/build results
</output>
