---
phase: 71-frontend-stats-subtab-openinginsightsblock
plan: "04"
subsystem: frontend
tags: [react, component, tdd, opening-insights, vitest]
dependency_graph:
  requires:
    - frontend/src/components/board/LazyMiniBoard.tsx (Plan 02)
    - frontend/src/lib/openingInsights.ts (Plan 03)
    - frontend/src/types/insights.ts (Plan 03)
  provides:
    - frontend/src/components/insights/OpeningFindingCard.tsx
  affects:
    - Plan 05 (OpeningInsightsBlock will consume OpeningFindingCard)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN cycle with vitest + @testing-library/react
    - Dual mobile/desktop layout mirroring GameCard.tsx (sm:hidden / hidden sm:flex)
    - Inline style borderLeftColor for severity accent (not Tailwind class — dynamic hex value)
key_files:
  created:
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
  modified: []
decisions:
  - "IntersectionObserver stubbed in test with vi.stubGlobal per GameCard.test.tsx pattern — LazyMiniBoard uses IntersectionObserver which is absent in jsdom"
  - "react-chessboard mocked in test environment to avoid SVG/canvas rendering failures"
  - "Rate percent colored with borderLeftColor for visual consistency — tests do not assert on this color so choice is safe per plan note"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 71 Plan 04: OpeningFindingCard Component Summary

**One-liner:** Severity-accented clickable finding card with dual mobile/desktop layout, D-06 prose template, and LazyMiniBoard thumbnail, built TDD against 11 vitest tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write OpeningFindingCard tests (TDD red phase) | 002669f | frontend/src/components/insights/OpeningFindingCard.test.tsx |
| 2 (GREEN) | Implement OpeningFindingCard component (TDD green phase) | 150e6fa | frontend/src/components/insights/OpeningFindingCard.tsx + test updates |

## What Was Built

### Component (`OpeningFindingCard.tsx`)

- Single `<a href="/openings/explorer">` element — the entire card is the touch target (D-22), no nested interactive elements
- `onClick` calls `e.preventDefault()` then `onFindingClick(finding)` for client-side React Router navigation
- `style={{ borderLeftColor: getSeverityBorderColor(classification, severity) }}` maps the four severity combinations to DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN from `arrowColor.ts`
- Mobile branch (`sm:hidden`): header line full-width on top, `LazyMiniBoard` (105px) + prose row below
- Desktop branch (`hidden sm:flex`): `LazyMiniBoard` (100px) on left, header + prose stacked right
- `LazyMiniBoard` receives `fen={finding.entry_fen}` and `flipped={finding.color === 'black'}`
- Header: `display_name` (italic muted for `<unnamed line>` sentinel) + `(ECO)` muted + `ExternalLink` icon right-aligned
- Prose: `"You {lose|win} {rate}% as {White|Black} after {trimmedSequence} (n={n_games})"` (D-06)
- Rate: `Math.round(loss_rate * 100)` for weakness, `Math.round(win_rate * 100)` for strength
- `data-testid="opening-finding-card-{idx}"` and `aria-label="Open {display_name} ({candidate_move_san}) in Move Explorer"` per D-15

### Tests (`OpeningFindingCard.test.tsx`)

11 test cases covering:
- Weakness prose (lose/rate/color/n_games)
- Strength prose (win/rate/color/n_games)
- 4 severity border color combinations (DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN)
- Click handler invocation with finding payload
- Header display_name + ECO rendering
- `<unnamed line>` sentinel italic rendering
- aria-label exact format
- Trimmed SAN sequence in prose (D-05)

Test file updated with `IntersectionObserver` stub and `react-chessboard` mock (following `GameCard.test.tsx` pattern) to allow jsdom rendering of `LazyMiniBoard`.

## Deviations from Plan

### [Rule 2 - Missing Critical] Added IntersectionObserver stub and react-chessboard mock to test file

- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** `LazyMiniBoard` uses `IntersectionObserver` which is not available in jsdom. `react-chessboard` fails to render in test environment without a mock.
- **Fix:** Added `vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)` and `vi.mock('react-chessboard', ...)` at the top of the test file, following the identical pattern already established in `GameCard.test.tsx`.
- **Files modified:** `frontend/src/components/insights/OpeningFindingCard.test.tsx`
- **Commit:** 150e6fa

## TDD Gate Compliance

- RED gate: `test(71-04): add failing tests for OpeningFindingCard component` (002669f) — tests failed with module-not-found error since component did not exist
- GREEN gate: `feat(71-04): implement OpeningFindingCard component` (150e6fa) — all 11 tests pass

## Known Stubs

None — `OpeningFindingCard` receives fully-populated `OpeningInsightFinding` props. No placeholder data in the component itself. Plan 05 will wire live data from `useOpeningInsights`.

## Knip Note

`OpeningFindingCard` export is not yet consumed by production code. It is imported by its companion test file, which keeps knip passing. Plan 05 (`OpeningInsightsBlock`) will consume it in the next wave.

## Threat Flags

None — this is a pure presentational frontend component with no network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- [x] `frontend/src/components/insights/OpeningFindingCard.tsx` exists: FOUND
- [x] `frontend/src/components/insights/OpeningFindingCard.test.tsx` exists: FOUND
- [x] Commit 002669f exists (RED): FOUND
- [x] Commit 150e6fa exists (GREEN): FOUND
- [x] All 138 frontend tests pass
- [x] `npm run lint` passes
- [x] `npm run knip` passes
- [x] `npx tsc --noEmit` produces no errors
