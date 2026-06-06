---
phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
plan: "04"
subsystem: frontend-library-primitives
tags: [library, severity-badge, tag-chip, no-analysis-state, filter-panel, display-only]
dependency_graph:
  requires: [107-02]
  provides: [SeverityBadge, TagChip, NoAnalysisState, LibraryFilterPanel]
  affects:
    - frontend/src/components/library/SeverityBadge.tsx
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/library/NoAnalysisState.tsx
    - frontend/src/components/filters/LibraryFilterPanel.tsx
    - frontend/src/components/filters/FilterPanel.tsx
tech_stack:
  added: []
  patterns: [alpha-composite-colors-from-theme, getTagFamily-switch, tag-family-colors-map, hideReset-prop-pattern]
key_files:
  created:
    - frontend/src/components/library/SeverityBadge.tsx
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/library/NoAnalysisState.tsx
    - frontend/src/components/filters/LibraryFilterPanel.tsx
  modified:
    - frontend/src/components/filters/FilterPanel.tsx
decisions:
  - "SeverityBadge bg/border colors derived as oklch alpha composites of SEV_* theme constants (no new hue values)"
  - "TagChip display-only per D-07: cursor-pointer + brightness/translate hover, zero navigation, zero toast"
  - "FilterPanel gains hideReset prop so LibraryFilterPanel can own the Reset button and clear both FilterState and severityFilter atomically"
  - "LibraryFilterPanel severity filter stays out of FilterState; passed as separate prop per UI-SPEC"
metrics:
  duration: "900s"
  completed_date: "2026-06-06"
  tasks_completed: 3
  files_changed: 5
---

# Phase 107 Plan 04: Leaf Primitives (SeverityBadge + TagChip + NoAnalysisState + LibraryFilterPanel) Summary

Four independent leaf primitives consumed by LibraryGameCard (Plan 06) and GamesTab: colored severity count badges, a family-colored display-only tag chip with honest ARIA, a dashed no-analysis pill, and a filter panel that composes FilterPanel with a separate boolean severity toggle.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SeverityBadge + NoAnalysisState primitives | ccc69de6 | frontend/src/components/library/SeverityBadge.tsx, NoAnalysisState.tsx |
| 2 | TagChip (family-colored, display-only, D-07) | f9d37ade | frontend/src/components/library/TagChip.tsx |
| 3 | LibraryFilterPanel (FilterPanel composition + severity filter) | 1f322669 | frontend/src/components/filters/LibraryFilterPanel.tsx |
| 3 (fix) | Suppress FilterPanel's own Reset when LibraryFilterPanel owns it | 8a8c7e98 | frontend/src/components/filters/FilterPanel.tsx, LibraryFilterPanel.tsx |

## What Was Built

### frontend/src/components/library/SeverityBadge.tsx (CREATED)

Renders a nowrap count pill for one severity level (blunder / mistake / inaccuracy). Count in `text-base font-bold`, full label (`Blunders` / `Mistakes` / `Inacc.`) in `text-sm font-bold`. Colors sourced from theme.ts `SEV_*` constants; background = oklch at 14% alpha, border = oklch at 30% alpha — derived inline as alpha composites of the exact same OKLCH values (no new color literals). `aria-label="{count} {severity}s"`, `data-testid="severity-{severity}-{gameId}"`.

### frontend/src/components/library/NoAnalysisState.tsx (CREATED)

Single dashed pill per UI-SPEC §'"No engine analysis" state'. Renders `border border-dashed rounded-full px-3 py-1 text-sm font-bold text-muted-foreground bg-white/5` with a small `h-2 w-2 rounded-full border` circle glyph and the copy "No engine analysis". Never shows counts — replaces the entire severity row + chips block. `aria-label="No engine analysis available for this game"`, `data-testid="no-analysis-{gameId}"`.

### frontend/src/components/library/TagChip.tsx (CREATED)

Family-colored display-only chip. `getTagFamily()` maps the three tempo tags to `'tempo'`, miss/lucky-escape to `'opportunity'`, and while-ahead/result-changing to `'impact'`. `TAG_FAMILY_COLORS` pulls `{ color, bg }` from theme.ts `FAM_*` and `FAM_*_BG` constants. Each tag renders with a small lucide icon (Clock / Zap / Brain / Target / Clover / TrendingDown / Swords at `h-3 w-3`) and the tag string as escaped React text (T-107-05 mitigation). Per D-07: `cursor-pointer` + `hover:brightness-110 hover:-translate-y-px` affordance, but zero `onClick`, zero toast, zero `/library/...` route reference. `aria-label="Tag: {tag} (not yet linked)"`, `data-testid="chip-{tag}-{gameId}"`.

### frontend/src/components/filters/LibraryFilterPanel.tsx (CREATED)

Composes `FilterPanel` with `visibleFilters` set to `['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']` (omits color/matchSide — Games subtab shows all colors). Above the composed panel, renders "Show games with:" label + two `<button>` toggles (Blunders / Mistakes) using the existing active/inactive toggle CSS classes (`border-toggle-active bg-toggle-active text-toggle-active-foreground` / `border-border bg-inactive-bg text-muted-foreground`), height `h-11 sm:h-7`, `aria-pressed`, `data-testid="filter-severity-blunder"` / `filter-severity-mistake"`. Below the panel, owns the Reset Filters button (`variant="brand-outline"`, `data-testid="btn-reset-filters"`) which clears both FilterState and severityFilter. Props: `severityFilter: ('blunder' | 'mistake')[]` and `onSeverityChange` separate from FilterState.

### frontend/src/components/filters/FilterPanel.tsx (MODIFIED)

Added `hideReset?: boolean` prop (default `false`). When `true`, suppresses the built-in Reset Filters button and its wrapper `<div>`. No other behavior changes. All existing callers unaffected (default `false`). This was needed so `LibraryFilterPanel` can own a single Reset that atomically clears both FilterState and severityFilter without showing a duplicate Reset button.

## Verification

- `cd frontend && npx tsc --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 issues
- `cd frontend && npm test -- --run` — 744 tests passed (63 test files)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `hideReset` prop to FilterPanel**
- **Found during:** Task 3
- **Issue:** FilterPanel always renders its own Reset Filters button. LibraryFilterPanel composing it would produce two identical Reset buttons with different behaviors (FilterPanel's resets only FilterState; LibraryFilterPanel's must also reset severityFilter).
- **Fix:** Added `hideReset?: boolean` prop to FilterPanel (default `false`; all existing callers unaffected). LibraryFilterPanel passes `hideReset` and owns the single Reset button that atomically clears both FilterState and severityFilter.
- **Files modified:** `frontend/src/components/filters/FilterPanel.tsx`, `frontend/src/components/filters/LibraryFilterPanel.tsx`
- **Commit:** 8a8c7e98

## Known Stubs

None. All four components are complete implementations matching the UI-SPEC. No placeholder text, no wired-but-empty data sources. TagChip's D-07 "not yet linked" ARIA is the intentional honest state, not a stub.

## Threat Flags

None. Display-only primitives with React-escaped text (T-107-05 mitigated). No new network endpoints, no auth paths, no schema changes at trust boundaries.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/library/SeverityBadge.tsx` — exists
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/library/TagChip.tsx` — exists
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/library/NoAnalysisState.tsx` — exists
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/filters/LibraryFilterPanel.tsx` — exists
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/filters/FilterPanel.tsx` — modified (hideReset prop)
- Commit ccc69de6 — Task 1 (SeverityBadge + NoAnalysisState)
- Commit f9d37ade — Task 2 (TagChip)
- Commit 1f322669 — Task 3 (LibraryFilterPanel)
- Commit 8a8c7e98 — Task 3 fix (hideReset)
