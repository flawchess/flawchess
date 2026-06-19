---
phase: 126-comparison-stats-frontend
plan: "02"
subsystem: frontend
tags: [tactic-chip, tactic-filter, theme-constants, library, beta-gate, frontend]
dependency_graph:
  requires: [frontend/src/lib/theme.ts, frontend/src/types/library.ts, frontend/src/components/library/TagChip.tsx, frontend/src/components/filters/FilterPanel.tsx]
  provides: [TAC_* theme constants, tacticComparisonMeta, tacticMotifDefinitions, TacticMotifChip, tactic filter in FilterPanel, TacticBullet/TacticComparisonResponse types]
  affects: [plan 126-03 (TacticComparisonGrid consumes tacticComparisonMeta + TacticComparisonResponse), FlawCard, LibraryGameCard, FilterPanel]
tech_stack:
  added: []
  patterns: [TagChip clone pattern, flawComparisonMeta clone pattern, toggleTimeControl filter pattern, beta-gate via useAuth]
key_files:
  created:
    - frontend/src/lib/tacticComparisonMeta.ts
    - frontend/src/lib/tacticMotifDefinitions.ts
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/types/library.ts
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/filters/LibraryFilterPanel.tsx
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
decisions:
  - "TacticMotifChip is purely informational (no filter-ring, no onHover/onActivate) per D-10"
  - "LibraryGameCard collects unique tactic motifs from flaw_markers (user side only) and renders one chip per distinct motif"
  - "FilterPanel uses native button elements with family-color inline styles instead of ToggleGroupItem to avoid ToggleGroup value management complexity"
  - "tacticMotif added to LIBRARY_GAMES_FILTERS in LibraryFilterPanel so the filter shows in the Flaws tab"
  - "tactic_families threaded into buildLibraryParams — null or empty means no filter (backend convention)"
  - "3 knip warnings (isTacticDeltaSignificant, tacticDeltaZoneColor, TacticComparisonResponse) are intentional: consumed by Plan 126-03 TacticComparisonGrid"
metrics:
  duration: "28 minutes"
  completed: "2026-06-18"
  tasks_completed: 3
  files_modified: 8
status: complete
---

# Phase 126 Plan 02: Tactic Chip + Filter Frontend Summary

Theme constants, shared family taxonomy, per-motif definitions, TacticMotifChip component on both flaw surfaces, and beta-gated tactic motif multi-select filter in FilterPanel.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TAC_* theme constants + tacticComparisonMeta + tacticMotifDefinitions + frontend types | feb5c64f | theme.ts, tacticComparisonMeta.ts, tacticMotifDefinitions.ts, library.ts |
| 2 | TacticMotifChip component + render on FlawCard and LibraryGameCard (beta-gated, D-10) | 57040e30 | TacticMotifChip.tsx, FlawCard.tsx, LibraryGameCard.tsx, TacticMotifChip.test.tsx |
| 3 | Beta-gated Tactic-motif multi-select filter in FilterPanel (desktop + mobile drawer) | 6cceb5b7 | FilterPanel.tsx, LibraryFilterPanel.tsx, useLibrary.ts, FlawCard.test.tsx |

## What Was Built

### Theme constants (`frontend/src/lib/theme.ts`)
Six `TAC_*` / `TAC_*_BG` color constant pairs appended after the existing `FAM_*` block:
- `TAC_FORK` / `TAC_FORK_BG` (hue 40, orange)
- `TAC_PIN_SKEWER` / `TAC_PIN_SKEWER_BG` (hue 240, indigo)
- `TAC_DISCOVERY` / `TAC_DISCOVERY_BG` (hue 130, lime)
- `TAC_MATE` / `TAC_MATE_BG` (hue 10, crimson)
- `TAC_HANGING` / `TAC_HANGING_BG` (hue 80, gold)
- `TAC_COMBINATIONS` / `TAC_COMBINATIONS_BG` (hue 300, fuchsia)

Hues chosen per UI-SPEC to avoid collision with WDL semantic hues (25/145/260) and existing flaw-family hues (55/170/200/290/330/350).

### Shared family taxonomy (`frontend/src/lib/tacticComparisonMeta.ts`)
- `TacticFamily` type (6 family keys)
- `TACTIC_FAMILY_COLORS` Record wired to TAC_* constants
- `TACTIC_FAMILY_ICON` Record (GitFork/Minus/Zap/Crown/AlertTriangle/Swords)
- `TACTIC_COMPARISON_FAMILIES` array with all 24 motif strings in the correct families (matches backend `FAMILY_TO_MOTIF_INTS`)
- `TACTIC_FAMILY_FOR_MOTIF` derived lookup Record (motif string → family key)
- `isTacticDeltaSignificant` + `tacticDeltaZoneColor` stat helpers for Plan 03

### Per-motif definitions (`frontend/src/lib/tacticMotifDefinitions.ts`)
`TACTIC_MOTIF_DEFINITIONS` Record with one-sentence plain-English definition for all 24 TacticMotif strings. Keys match backend Literal strings exactly.

### Frontend type additions (`frontend/src/types/library.ts`)
- `FlawListItem` and `FlawMarker`: added `tactic_motif: string | null` and `tactic_confidence: number | null`
- `TacticBullet` interface (mirrors backend schema)
- `TacticComparisonResponse` interface

### TacticMotifChip (`frontend/src/components/library/TacticMotifChip.tsx`)
Cloned from `TagChip.tsx`, purely informational (D-10):
- Props: `motif: string`, `flawId: number`
- Resolves family via `TACTIC_FAMILY_FOR_MOTIF`, colors via `TACTIC_FAMILY_COLORS`, icon via `TACTIC_FAMILY_ICON`
- `data-testid="chip-tactic-{motif}-{flawId}"`, `aria-label="Tactic: {motif} — {definition}"`
- Hover/tap definition popover: side=top desktop, side=bottom mobile
- Returns null for unknown motif strings (defensive)

### Chip render sites (both beta-gated via `user?.beta_enabled`)
- `FlawCard.tsx`: chip rendered after the TagChip/TagLegend block, gated by `user?.beta_enabled && flaw.tactic_motif != null`
- `LibraryGameCard.tsx`: collects unique non-null tactic motifs from `game.flaw_markers` (user side), renders one chip per distinct motif, gated by `user?.beta_enabled && tacticMotifs.length > 0`

### FilterPanel tactic filter (`frontend/src/components/filters/FilterPanel.tsx`)
- `tacticFamilies: TacticFamily[] | null` field on `FilterState` (null = all families = no filter)
- `'tacticMotif'` added to `FilterField` union and `ALL_FILTERS`
- `toggleTacticFamily` / `isTacticFamilyActive` helpers mirror `toggleTimeControl` pattern
- Beta-gated section after existing filters, iterates `TACTIC_COMPARISON_FAMILIES`, family-colored buttons with `data-testid="filter-tactic-motif"` and per-family `data-testid="filter-tactic-motif-{family}"`
- `'tacticMotif'` added to `LIBRARY_GAMES_FILTERS` in `LibraryFilterPanel.tsx`
- `tactic_families` threaded into `buildLibraryParams` in `useLibrary.ts`

### Tests
17 tests in `TacticMotifChip.test.tsx` covering: motif text render, family color, testid stability, aria-label, role/tabIndex, keyboard, unknown motif null return, popover wiring.

## Verification Results

```
cd frontend && npm run lint && npx tsc --noEmit
# No errors

npm test -- --run TacticMotifChip
# 17 passed

npm test -- --run
# 968 passed (85 test files)

npm run knip
# 3 intentional warnings: isTacticDeltaSignificant, tacticDeltaZoneColor, TacticComparisonResponse
# — consumed by Plan 126-03 TacticComparisonGrid (next plan)
```

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] FlawCard.test.tsx missing useAuth mock**
- **Found during:** Task 3 (test run after adding `useAuth` to FlawCard)
- **Issue:** The existing `FlawCard.test.tsx` rendered without an `AuthProvider`, causing all 18 tests to fail with "useAuth must be used within an AuthProvider"
- **Fix:** Added `vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ user: null }) }))` to the test file
- **Files modified:** `frontend/src/components/library/__tests__/FlawCard.test.tsx`
- **Commit:** 6cceb5b7

**2. [Rule 1 - Deviation] LibraryGameCard: TacticMotifChip from flaw_markers, not chip field**
- **Found during:** Task 2 (reading LibraryGameCard structure)
- **Issue:** `LibraryGameCard` uses `game.chips: FlawTag[]` (aggregated) for the tag chip row, but tactic motifs are per-flaw (on `flaw_markers`). Rendering from `chips` would require a `chips` API change.
- **Fix:** Collect unique tactic motifs from `game.flaw_markers` (user-side flaws only) and render one `TacticMotifChip` per distinct motif. This is functionally equivalent — one chip per motif pattern found in the game.
- **Files modified:** `frontend/src/components/results/LibraryGameCard.tsx`

### Intentional knip warnings (3)

`isTacticDeltaSignificant`, `tacticDeltaZoneColor`, and `TacticComparisonResponse` are exported from this plan but consumed by Plan 126-03 `TacticComparisonGrid` (the comparison grid component). They are not dead exports — they are forward-consumed by the next plan. knip cannot detect cross-plan usage at plan-02 verification time.

## Known Stubs

None. All chip and filter functionality is fully wired:
- Chip colors come from TACTIC_FAMILY_COLORS (theme.ts constants, not stubs)
- Filter toggles update FilterState and thread to the backend via tactic_families param
- Definitions in TACTIC_MOTIF_DEFINITIONS are substantive (not "coming soon" or placeholder)
- `has_zone=False` on `TacticBullet` is intentional per Context §Deferred (no tactic benchmark pipeline this phase)

## Threat Flags

None. All STRIDE threats from the plan's threat register are addressed:
- T-126-05 (beta gate): `user?.beta_enabled` guards all three tactic render sites (chip on FlawCard, chip on LibraryGameCard, filter section in FilterPanel)
- T-126-06 (family key injection): family keys come from `TACTIC_COMPARISON_FAMILIES` enum; backend maps unknown keys to no-op
- T-126-07 (XSS): definitions are static constants; motif strings from typed backend enum; rendered as React text nodes (auto-escaped)
- T-126-SC (npm): no new packages added

## Self-Check: PASSED
