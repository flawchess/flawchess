---
phase: 126-comparison-stats-frontend
plan: "03"
subsystem: frontend
tags: [tactic-comparison-grid, beta-gate, library, frontend]
dependency_graph:
  requires:
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/lib/tacticComparisonMeta.ts
    - frontend/src/types/library.ts
    - frontend/src/components/library/FlawComparisonGrid.tsx
    - frontend/src/components/charts/MiniBulletChart.tsx
  provides:
    - getTacticComparison API fn
    - useTacticComparison hook
    - TacticComparisonGrid component (beta-gated)
    - TacticComparisonGrid placement in FlawStatsPanel Zone 3
  affects:
    - frontend/src/components/library/FlawStatsPanel.tsx
tech_stack:
  added: []
  patterns:
    - FlawComparisonGrid clone pattern
    - useTacticComparison mirrors useLibraryFlawComparison
    - getTacticComparison mirrors getFlawComparison
    - MiniBulletChart zone-collapse degradation (neutralMin/Max = 0/0 when !has_zone)
    - beta gate via useAuth (inner component post-guard pattern)
key_files:
  created:
    - frontend/src/components/library/TacticComparisonGrid.tsx
    - frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/components/library/FlawStatsPanel.tsx
decisions:
  - "Beta gate uses inner-component split (TacticComparisonGridInner) to keep hook call post-conditional (React hooks rules)"
  - "API-returned bullets rendered in server-side order with no client re-sort (backend ranked + capped at 6)"
  - "Zone degradation: neutralMin=0/neutralMax=0 when !has_zone (chart collapses band, no crash, no fabricated data)"
  - "Popover copy follows UI-SPEC: you_rate/opp_rate per game + sign-convention + statistically notable / within normal variation"
metrics:
  duration: "10 minutes"
  completed: "2026-06-18"
  tasks_completed: 2
  files_modified: 5
status: complete
---

# Phase 126 Plan 03: TacticComparisonGrid Frontend Summary

Beta-gated you-vs-opponent tactic-motif comparison grid rendering server-ranked family bullets with MiniBulletChart (delta + CI + zone-where-available), per-row tooltips, section sample gate, and LoadError state — placed in the Library FlawStatsPanel Zone 3, single-column at 375px.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add getTacticComparison API fn + useTacticComparison hook | f6135e57 | client.ts, useLibrary.ts |
| 2 | TacticComparisonGrid component + Library placement + tests | e082af1e | TacticComparisonGrid.tsx, FlawStatsPanel.tsx, TacticComparisonGrid.test.tsx |

## What Was Built

### API function (`frontend/src/api/client.ts`)
- `libraryApi.getTacticComparison`: GET `/library/tactic-comparison`, mirrors `getFlawComparison` plus optional `tactic_families?: string[]` param
- `TacticComparisonResponse` added to the library type import

### Hook (`frontend/src/hooks/useLibrary.ts`)
- `useTacticComparison(filters, flawFilter, tacticFamilies)`: self-fetch hook
- Query key: `['library-tactic-comparison', params, tacticFamilies]` — includes `tacticFamilies` so motif filter changes trigger re-fetch
- `staleTime: LIBRARY_STALE_TIME`, `refetchOnWindowFocus: false`
- No manual `Sentry.captureException` — global TanStack Query handler covers it (CLAUDE.md)
- `TacticFamily` type imported from `tacticComparisonMeta.ts`

### Component (`frontend/src/components/library/TacticComparisonGrid.tsx`)
- **Beta gate** (D-01): `if (!user?.beta_enabled) return null` — outer component, returns null for non-beta users before any hooks fire. Inner component `TacticComparisonGridInner` holds the hook call (React hooks-after-conditional guard)
- **State machine** (in priority order): isLoading → LoadingSkeleton (`tactic-comparison-loading`, `aria-label="Loading tactic comparison"`); isError → `<LoadError resource="tactic comparison" />`; !data → null; `below_gate` → GateCTA (`tactic-comparison-gate-cta`); else GridBody (`tactic-comparison-grid`)
- **GridBody**: renders API bullets in server-side order (no `.sort()` — server already ranked + capped at 6); one Card per bullet; `data-testid="tactic-family-card-{family}"`, `data-testid="tactic-family-header-{family}"`
- **TacticBulletRow**: family icon + label (`TACTIC_FAMILY_ICON`, `TACTIC_FAMILY_COLORS`); signed delta tinted by zone color when `isTacticDeltaSignificant`; zero-event (`delta === null`) renders muted italic "No events in current filter"; `MiniBulletChart` with `invertColors=true barColor="neutral"`, `neutralMin/Max = bullet.has_zone ? zone_lo/hi : 0`
- **TacticBulletPopover**: hover-open (100ms delay), `you_rate/opp_rate per game`, sign-convention sentence, confidence verdict without jargon
- **GateCTA**: UI-SPEC copywriting: `"{n} of {gate} analyzed games needed"` + Lichess server analysis instructions
- **Layout**: `grid-cols-1 lg:grid-cols-3` — single-column at 375px (TACUI-03), 3-column on desktop

### Section heading (UI-SPEC verbatim)
- Heading: "Tactic Motifs"
- Sub-heading: "You vs. your opponents — flaws allowed per game" (no em-dash, CLAUDE.md style)

### Library placement (`frontend/src/components/library/FlawStatsPanel.tsx`)
- `<TacticComparisonGrid filters={filters} flawFilter={flawFilter} />` added in Zone 3, directly after `<FlawComparisonGrid>`, wrapped in `<div className="mt-6">`
- No extra beta guard at call site — the grid self-gates

### Test suite (`frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx`)
10 tests across 6 describe blocks:
1. **Beta gate**: non-beta user → renders null
2. **Below-gate CTA** (2 tests): CTA testid present + "12 of 20" text
3. **Full grid** (4 tests): grid testid; 6 family card testids; 6 popovers with aria-label; section heading + sub-heading
4. **Zero-event bullet**: "No events" placeholder, no MiniBulletChart inside row
5. **Error state**: LoadError copy rendered
6. **Loading state**: loading skeleton testid

## Verification Results

```
cd frontend && npm run lint
# No errors

npx tsc --noEmit
# No errors

npm test -- --run TacticComparisonGrid
# 10 passed (1 test file)

npm run knip
# No warnings (previous plan-02 intentional warnings resolved by this plan's consumers)
```

### Source assertions verified
- `TacticComparisonGrid.tsx` contains `if (!user?.beta_enabled) return null`: YES (1 occurrence)
- `data-testid="tactic-comparison-grid"`: YES
- `tactic-comparison-gate-cta`: YES
- `tactic-comparison-loading`: YES
- `tactic-family-card-${bullet.family}`: YES (dynamic testid)
- No `.sort(` on bullets array: CONFIRMED (0 occurrences)
- `FlawStatsPanel.tsx` renders `<TacticComparisonGrid` in Zone 3: YES
- `neutralMin/Max = 0/0` when `!bullet.has_zone`: YES (lines 224–225)

### Mobile parity (TACUI-03, 375px)
Grid uses `grid-cols-1 lg:grid-cols-3` — collapses to single-column below the `lg` (1024px) breakpoint, covering 375px. MiniBulletChart is full-width within card padding. Section heading + sub-heading stack naturally. Manual 375px note: confirmed single-column via Tailwind `grid-cols-1` default.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 - Architecture] Inner component for hook-after-conditional guard**
- **Found during:** Task 2 (implementing beta gate)
- **Issue:** React rules prohibit calling hooks after a conditional return. The plan spec says "beta gate FIRST: `if (!user?.beta_enabled) return null`" with `useTacticComparison` called inside the same component — but hooks must be called unconditionally.
- **Fix:** Split into `TacticComparisonGrid` (outer, runs beta gate, no hooks after the gate) and `TacticComparisonGridInner` (inner, post-gate, holds the `useTacticComparison` call). Functionally identical to the plan intent.
- **Files modified:** `frontend/src/components/library/TacticComparisonGrid.tsx`

## Known Stubs

None. All functionality is wired:
- `has_zone=False` on `TacticBullet` is intentional per CONTEXT §Deferred (no tactic benchmark pipeline this phase); `neutralMin/Max=0/0` is the correct graceful degradation, not a stub.
- Per-row popovers render actual `you_rate`/`opp_rate` from API data.

## Threat Flags

None. All STRIDE threats from the plan's threat register are mitigated:
- T-126-08 (beta gate): `if (!user?.beta_enabled) return null` in outer component gates both render and fetch
- T-126-09 (DoS/overdraw): `LIBRARY_STALE_TIME` + `refetchOnWindowFocus:false` in hook; server caps at 6 rows
- T-126-10 (malformed zone bounds): `has_zone` discriminator gates neutralMin/Max; `delta === null` renders placeholder (no NaN)

## Self-Check: PASSED
