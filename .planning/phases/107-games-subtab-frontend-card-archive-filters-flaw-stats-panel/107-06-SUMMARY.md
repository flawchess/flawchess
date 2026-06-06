---
phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
plan: "06"
subsystem: frontend-library-card
tags: [library, game-card, pagination, severity-badge, tag-chip, no-analysis-state]
dependency_graph:
  requires:
    - phase: 107-02
      provides: "library types (GameFlawCard, FlawTag, AnalysisState, SeverityCountsData)"
    - phase: 107-03
      provides: "shared Pagination component"
    - phase: 107-04
      provides: "SeverityBadge, TagChip, NoAnalysisState primitives"
  provides:
    - LibraryGameCard (full-width header + 3-column desktop body + flaw column / no-analysis state)
    - LibraryGameCardList (paginated list with matched-count row)
  affects:
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/LibraryGameCardList.tsx
tech-stack:
  added: []
  patterns:
    - standalone-card-per-D05 (new card component does not extend GameCard)
    - analysis_state-discriminated-render (analyzed vs no_engine_analysis branch)
    - library-scroll-target-distinct (scrolls library-game-card-list not game-card-list)
key-files:
  created:
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/LibraryGameCardList.tsx
  modified: []
key-decisions:
  - "LibraryGameCard is a standalone component (D-05): formatDate/formatTimeControl copied verbatim from GameCard, not refactored as shared helpers"
  - "flawContent branches on analysis_state only: analyzed renders SeverityBadge + TagChip; no_engine_analysis renders NoAnalysisState — severity_counts never read when null"
  - "flaw column uses flex: 0 0 auto so the nowrap SeverityBadge row dictates the column width"
  - "LibraryGameCardList scroll target is [data-testid=library-game-card-list] not game-card-list (separate from GameCardList per UI-SPEC)"
requirements-completed: [LIBG-01]
duration: 4min
completed: "2026-06-06"
---

# Phase 107 Plan 06: LibraryGameCard + LibraryGameCardList Summary

**Analyzed game card with 3-column desktop body + flaw column (SeverityBadge/TagChip or NoAnalysisState), plus paginated LibraryGameCardList with library-specific scroll target**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-05T22:26:12Z
- **Completed:** 2026-06-05T22:29:38Z
- **Tasks:** 2
- **Files modified:** 2 (created)

## Accomplishments

- `LibraryGameCard` standalone per D-05: full-width header (desktop single-line bold, mobile two-line 400-weight), 3-column desktop body (board / info / dashed flaw column), mobile flaw block; analyzed branch renders nowrap SeverityBadge row + flex-wrap TagChip row; `no_engine_analysis` branch renders NoAnalysisState pill and never reads null `severity_counts`
- `LibraryGameCardList` wraps cards in a `<section aria-label="Game results" data-testid="library-game-card-list">` with a matched-count row ("{matchedCount} of {total} games"), shared Pagination, and a scroll target distinct from `GameCardList`
- All threat mitigations active: `platform_url` rendered with `rel="noopener noreferrer"` (T-107-10), text rendered as React children (T-107-09 auto-escaped), `no_engine_analysis` branch never reads null `severity_counts` (T-107-11)
- `npx tsc --noEmit`, `npm run lint`, `npm test -- --run` all pass (744 tests)

## Task Commits

1. **Task 1: LibraryGameCard** - `965853b5` (feat)
2. **Task 2: LibraryGameCardList** - `214c80ed` (feat)

## Files Created/Modified

- `frontend/src/components/results/LibraryGameCard.tsx` — Analyzed game card: full-width header, 3-col desktop body, mobile flaw block, analysis_state branch
- `frontend/src/components/results/LibraryGameCardList.tsx` — Paginated library card list with matched-count row and library scroll target

## Decisions Made

- `LibraryGameCard` is standalone per D-05: `formatDate` / `formatTimeControl` copied verbatim from `GameCard.tsx` (not a shared import or refactor). GameCard.tsx is untouched.
- `flawContent` is derived once and shared between the desktop flaw column and the mobile flaw block — both renderers render the same JSX node, eliminating duplication.
- `flaw column` uses `style={{ flex: '0 0 auto' }}` so its width is dictated by the nowrap SeverityBadge row per UI-SPEC.
- `severity_counts` is narrowed before any index access (`const counts = game.severity_counts; const count = counts !== null ? (counts[sev] ?? 0) : 0`) — honors `noUncheckedIndexedAccess`.
- `PAGE_SIZE = 20` named constant in `LibraryGameCardList` (no magic number per CLAUDE.md).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both components are complete implementations. The `chips.length > 0` guard ensures an empty chip row is not rendered, but this is correct behavior (not a stub) — an analyzed game can legitimately have no chips.

## Threat Flags

None. Both components use React-escaped text rendering and no new endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/results/LibraryGameCard.tsx` — exists
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/results/LibraryGameCardList.tsx` — exists
- Commit 965853b5 — Task 1 (LibraryGameCard)
- Commit 214c80ed — Task 2 (LibraryGameCardList)
- `npx tsc --noEmit` — 0 errors
- `npm run lint` — 0 issues
- `npm test -- --run` — 744 tests passed
