---
phase: 129-tactic-filter-ui
plan: "02"
subsystem: frontend
tags: [tactic-filter, orientation, depth, filter-ui, tdd, frontend]
status: complete

dependency_graph:
  requires:
    - TacticOrientation 3-value Literal (plan 01)
    - TacticBullet.orientation schema field (plan 01)
    - max_tactic_depth half-move unit (plan 01)
  provides:
    - TacticOrientation type + TacticBullet.orientation in types/library.ts (wave-2 shared-type boundary locked)
    - tacticDepth.ts with full-move/half-ply conversion layer (D-03)
    - FlawFilterState.tacticOrientation/tacticDepthPreset/tacticDepthMax fields
    - TacticDepthFilter component (single-handle slider, 3 presets, Intermediate default)
    - Orientation ToggleGroup (Either/Missed/Allowed) in FlawFilterControl
    - TacticMotifChip orientation prop (missed:/allowed: prefix in label/aria/testid)
    - FlawCard D-11 dual-chip matrix (Either=both, Missed=missed-only, Allowed=allowed-only)
    - Query threading: tactic_orientation + max_tactic_depth in useLibraryFlaws key
  affects:
    - frontend/src/types/library.ts
    - frontend/src/lib/tacticDepth.ts
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/components/filters/TacticDepthFilter.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/library/FlawCard.tsx

tech_stack:
  added: []
  patterns:
    - Single-handle slider pattern (clone of OpponentStrengthFilter, collapsed to one bound)
    - full-move/half-ply unit split bridged by sliderToMax/maxToSlider (D-03 locked contract)
    - ToggleGroup deselect guard (if (!v) return; — cloned from "Played as" FilterPanel:265-286)
    - Orientation-prefixed chip label/aria/testid (visibleLabel/ariaLabel/testId derived from optional prop)
    - D-11 dual-chip matrix: tacticOrientation !== 'allowed' for missed, !== 'missed' for allowed

key_files:
  created:
    - frontend/src/lib/tacticDepth.ts
    - frontend/src/lib/__tests__/tacticDepth.test.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/components/filters/TacticDepthFilter.tsx
  modified:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx

decisions:
  - "TacticDepthValue shape: { preset: TacticDepthPreset; maxMoves: number | null } where maxMoves is in HALF-PLIES (D-03 locked)"
  - "FlawCard accepts tacticOrientation prop (default 'either') threaded from FlawsTab via flawFilter.tacticOrientation"
  - "Slider domain: full moves 1..5; API value: half-plies; sliderToMax(*2)/maxToSlider(/2) bridge"
  - "isFlawFilterNonDefault treats Either+Intermediate as default; depth filter always-on never lights dot at defaults (D-02)"
  - "No Popover in TacticMotifChip (D-12 prohibition enforced); orientation prefix is text only"
  - "ResizeObserver stub required in jsdom tests that render ToggleGroup (Radix UI uses-size hook)"

metrics:
  duration_minutes: 17
  completed_date: "2026-06-20"
  tasks_completed: 4
  tasks_total: 4
  files_modified: 12
---

# Phase 129 Plan 02: Tactic Filter UI (Frontend) Summary

Wired the Flaws-tab filter UI with the depth (difficulty) control, Either/Missed/Allowed toggle, store fields, TanStack query threading, and dual-chip rendering. Locked the `TacticBullet.orientation` schema field into `types/library.ts` (shared-type boundary).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for tacticDepth + store fields | 07376d21 | tacticDepth.test.ts, useFlawFilterStore.test.ts |
| 1 GREEN | Shared types + tacticDepth lib + store fields + query threading | 07376d21 | types/library.ts, tacticDepth.ts, useFlawFilterStore.ts, client.ts, useLibrary.ts, FlawsTab.tsx |
| 2 | TacticDepthFilter + orientation toggle + FlawsTab wiring | 457585e2 | TacticDepthFilter.tsx, FlawFilterControl.tsx, FlawsTab.tsx |
| 3 RED | Failing chip/card orientation tests | 26baa480 | TacticMotifChip.test.tsx, FlawCard.test.tsx |
| 3 GREEN | Orientation-prefixed chips + D-11 dual-chip on FlawCard | 26baa480 | TacticMotifChip.tsx, FlawCard.tsx, FlawsTab.tsx |
| 4 | Full frontend gate (lint + vitest + tsc -b) + pre-existing test fixes | 2f1b9813 | FlawFilterControl.test.tsx, FlawsTab.test.tsx |

## What Was Built

### Task 1: Shared Types + tacticDepth Lib + Store Fields + Query Threading

**`types/library.ts`**: Added `TacticOrientation = 'either' | 'missed' | 'allowed'` type and `orientation: 'missed' | 'allowed'` field to `TacticBullet` — the shared-type boundary mirror of plan 01's schema.

**`lib/tacticDepth.ts`** (NEW): Companion library with named constants and conversion functions. D-03 locked contract: slider domain is FULL MOVES (1..5); API value is HALF-PLIES. `sliderToMax` multiplies by `HALF_PLIES_PER_MOVE=2`; `maxToSlider` divides (Math.ceil). `sliderToMax(DEPTH_SLIDER_MAX_MOVES)=null` = Advanced/no cap. Named constants: `DEPTH_PRESET_BEGINNER_MAX=2`, `DEPTH_PRESET_INTERMEDIATE_MAX=6`, `DEPTH_PRESET_ADVANCED_MAX=null`, `DEPTH_SLIDER_MIN_MOVES=1`, `DEPTH_SLIDER_MAX_MOVES=5`, `DEPTH_SLIDER_STEP=1`, `HALF_PLIES_PER_MOVE=2`, `DEPTH_DEFAULT_PRESET='intermediate'`. Functions: `derivePreset`, `presetToMax`, `sliderToMax`, `maxToSlider`, `formatDepthSummary` (full-moves strings), `depthToQueryParam` (half-ply passthrough).

**`hooks/useFlawFilterStore.ts`**: Added `tacticOrientation: TacticOrientation`, `tacticDepthPreset: TacticDepthPreset`, `tacticDepthMax: number | null` to `FlawFilterState` and `DEFAULT_FLAW_FILTER`. `isFlawFilterNonDefault` updated: returns false at Either+Intermediate defaults (D-02 — depth always-on never lights dot at default); returns true when orientation !== 'either' OR depthPreset !== 'intermediate'.

**`api/client.ts`**: Added `tactic_orientation` and `max_tactic_depth` params to `getFlaws`. Orientation omitted when 'either'; depth omitted when null.

**`hooks/useLibrary.ts`**: Added `depthToQueryParam` import and threaded `tacticOrientation` + `depthParam` into `useLibraryFlaws` query key and function call (changing either triggers refetch — pitfall 4 prevention).

### Task 2: TacticDepthFilter + Orientation Toggle + FlawsTab Wiring

**`TacticDepthFilter.tsx`** (NEW): Single-handle slider in FULL MOVES (1..5). Preset chips grid (`grid grid-cols-3`) for Beginner/Intermediate/Advanced with `aria-pressed`. Slider onValueChange maps through `sliderToMax` to half-ply API value. Summary text goes `text-toggle-active` when preset is not Intermediate (D-02). InfoPopover body includes mate-exempt sentence (D-04). All data-testids per UI-SPEC.

**`FlawFilterControl.tsx`**: Added `orientation`, `onOrientationChange`, `tacticDepth`, `onTacticDepthChange` props. New sections inserted ABOVE Tactic Motif when `showTacticFilter`: (1) Orientation ToggleGroup cloned from FilterPanel "Played as" with deselect guard `if (!v) return;`; (2) `<TacticDepthFilter>`. Both sections render in mobile drawer automatically (drawer renders `FlawFilterControl`).

**`FlawsTab.tsx`**: Threaded new store fields through pending/applied filter pattern. Both desktop and mobile `FlawFilterControl` instances receive `orientation`/`onOrientationChange`/`tacticDepth`/`onTacticDepthChange`. `FlawCard` receives `tacticOrientation={flawFilter.tacticOrientation}`.

### Task 3: Orientation-Prefixed Chips + Dual-Chip Rendering

**`TacticMotifChip.tsx`**: Added optional `orientation?: 'missed' | 'allowed'` prop. When set: `visibleLabel = "${orientation}: ${motif}"`; `ariaLabel = "Tactic: ${orientation} ${motif} — ${definition}"` (space in aria, colon in label per UI-SPEC); `testId = "chip-tactic-${orientation}-${motif}-${flawId}"`. When unset: unchanged output. No Popover import (D-12 prohibition).

**`FlawCard.tsx`** (Flaws-tab list-row card only): Added `tacticOrientation: TacticOrientation` prop (default 'either'). D-11 dual-chip matrix: `tacticOrientation !== 'allowed'` gates missed chip; `tacticOrientation !== 'missed'` gates allowed chip. TagLegend receives filtered motif list matching rendered chips. `LibraryGameCard.tsx` and `EvalChart.tsx` NOT modified (out of scope per RESEARCH Open Questions RESOLVED §3).

### TacticDepthValue Shape (for plan 03 checker)

```typescript
interface TacticDepthValue {
  preset: TacticDepthPreset;  // 'beginner' | 'intermediate' | 'advanced'
  maxMoves: number | null;    // HALF-PLIES (API value); null = Advanced/no cap
}
```

FlawCard's `flawFilter`/orientation prop: `tacticOrientation: TacticOrientation` threaded from `FlawsTab` via `flawFilter.tacticOrientation`. The `TacticComparisonGrid` (plan 03) does NOT receive this prop — it shows both orientations regardless (D-09).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ResizeObserver undefined in pre-existing test suite**
- Found during: Task 4 full gate
- Issue: Adding `ToggleGroup` (Radix UI) to `FlawFilterControl` caused `FlawFilterControl.test.tsx` and `FlawsTab.test.tsx` to fail with `ReferenceError: ResizeObserver is not defined` — Radix's `@radix-ui/react-use-size` hook calls `ResizeObserver` which jsdom doesn't provide.
- Fix: Added `beforeAll` stub in both test files: `window.ResizeObserver = class ResizeObserver { observe = vi.fn(); unobserve = vi.fn(); disconnect = vi.fn(); }`.
- Files modified: `FlawFilterControl.test.tsx`, `FlawsTab.test.tsx`
- Commit: 2f1b9813

**2. [Rule 1 - Bug] FlawsTab test mockStoreState missing Phase 129 fields**
- Found during: Task 4 full gate
- Issue: Two tests overrode `mockStoreState` with a partial object (`{ severity, tags }`) missing `tacticOrientation`/`tacticDepthPreset`/`tacticDepthMax`. FlawsTab now accesses these fields; accessing `undefined.tacticOrientation` caused render failures.
- Fix: Updated both inline overrides to include all Phase 129 fields with defaults.
- Files modified: `FlawsTab.test.tsx`
- Commit: 2f1b9813

**3. [Rule 2 - Missing critical functionality] makeFlaw factory missing tactic motif fields**
- Found during: Task 3 tests
- Issue: `FlawCard.test.tsx`'s `makeFlaw` factory didn't include `allowed_tactic_motif`, `missed_tactic_motif` or confidence fields, making them implicitly undefined rather than null — confusing the chip rendering tests.
- Fix: Added null defaults for all four tactic motif fields to the factory.
- Files modified: `FlawCard.test.tsx`
- Commit: 26baa480

## Verification Results

- `npm run lint`: clean (knip zero issues — all new exports imported)
- `npm test -- --run`: 1063 passed, 0 failed across 88 test files
- `npx tsc -b`: zero errors (shared-type boundary confirmed)

## Known Stubs

None — all new controls wire to real store state + query key. The depth filter defaults to Intermediate (always-on per D-02); orientation defaults to Either.

## Threat Mitigations Verified

| T-ID | Status |
|------|--------|
| T-129-05 (beta gate bypass) | Accept — `useUserProfile().data.beta_enabled` gate preserved (not useAuth().user) |
| T-129-06 (client-crafted depth/orientation) | Mitigated — `depthToQueryParam` passes half-ply value through; server-side validation in plan 01 |
| T-129-07 (flaw chip rendering) | Accept — player-only flaws, card renders user's own motifs |
| T-129-SC (npm installs) | Mitigated — no new dependencies; all primitives from Phase 126 |

## Self-Check: PASSED
