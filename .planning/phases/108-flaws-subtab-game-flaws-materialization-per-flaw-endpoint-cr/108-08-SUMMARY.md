---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "08"
subsystem: frontend
tags: [flaws, filter, navigation, deep-link, shared-store, D-01, D-04, D-05]
dependency_graph:
  requires:
    - phase: 108-07
      provides: "useFlawFilterStore + FlawFilterControl + FlawsTab (filter rendered inline)"
  provides:
    - "LibraryFilterPanel: hosts FlawFilterControl above metadata filters (D-01 boolean toggle removed)"
    - "GamesTab: shared useFlawFilterStore state (D-04, replaces local severityFilter)"
    - "TagChip: navigation <button> deep-linking to /library/flaws?tag={TAG} (no game_id, D-05)"
    - "useLibraryGames + useLibraryFlawStats: accept FlawFilterState (severity+tags) instead of severity[]"
  affects:
    - "Phase 109+ — both Games and Flaws tabs now share a single flaw-filter control via LibraryFilterPanel"
tech_stack:
  added: []
  patterns:
    - "LibraryFilterPanel as the canonical host for FlawFilterControl across both tabs (single source)"
    - "FlawFilterState propagated from useFlawFilterStore to LibraryFilterPanel as flawFilter/onFlawFilterChange/onClearFlawFilter props"
    - "TagChip: useNavigate for navigation; data-testid stable, aria-label updated for navigable state"
key-files:
  created:
    - frontend/src/components/library/__tests__/TagChip.test.tsx
    - frontend/src/pages/library/__tests__/GamesTab.test.tsx
  modified:
    - frontend/src/components/filters/LibraryFilterPanel.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/lib/tagDefinitions.ts
key-decisions:
  - "LibraryFilterPanel now hosts FlawFilterControl for both Games and Flaws tabs (panel-hosted pattern); FlawsTab no longer renders FlawFilterControl inline"
  - "useLibraryGames + useLibraryFlawStats accept full FlawFilterState (not just severity) so tags also filter the Games query"
  - "TAG_DEFINITIONS removed (TagChip popover gone); flawThresholds.ts deleted as now-unused file"
requirements-completed: [D-01, D-04, D-05]
duration: 12min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 2
files_modified: 8
---

# Phase 108 Plan 08: Games Tab Reconciliation — FlawFilterControl in Panel, Shared Store, TagChip Nav Summary

**LibraryFilterPanel now hosts FlawFilterControl for both Games and Flaws tabs (D-01 boolean toggle removed); GamesTab migrated from local severityFilter to useFlawFilterStore (D-04); TagChip converted from display-only Radix popover to navigation button deep-linking to /library/flaws?tag={TAG} (D-05); 20 new vitest tests**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-06T19:08:00Z
- **Completed:** 2026-06-06T19:21:00Z
- **Tasks:** 3
- **Files created:** 2
- **Files modified:** 8

## Accomplishments

- **Task 1 (D-01):** Replaced the boolean `('blunder'|'mistake')[]` severity toggle in `LibraryFilterPanel` with `FlawFilterControl`. Panel now accepts `flawFilter: FlawFilterState`, `onFlawFilterChange`, and `onClearFlawFilter` props. `FlawFilterControl` renders above the metadata `FilterPanel`. `FlawsTab` migrated from inline `FlawFilterControl` renders (desktop sidebar + mobile drawer) to passing `flawFilter` props through `LibraryFilterPanel` — both tabs now share the panel-hosted control as the single source of truth. "Reset Filters" button now resets game-metadata only (not flaw filter, which has its own "Clear flaw filter" affordance).

- **Task 2 (D-04):** Replaced GamesTab's local `const [severityFilter, setSeverityFilter] = useState([])` with `const [flawFilter, setFlawFilter] = useFlawFilterStore()`. `handleFlawFilterChange` writes to the store and resets page offset; `handleClearFlawFilter` resets to `DEFAULT_FLAW_FILTER`. Games tab does NOT URL-sync (D-04 precedent). Updated `useLibraryGames` and `useLibraryFlawStats` signatures to accept full `FlawFilterState` instead of `severity[]`; `buildLibraryParams` already accepted `tags` as an optional 3rd arg so the extension was additive. `GlobalStats.tsx` updated to pass `DEFAULT_FLAW_FILTER` to `useLibraryFlawStats`.

- **Task 3 (D-05):** Converted `TagChip` from Radix `PopoverPrimitive.Root/Trigger` (display-only) to a semantic `<button type="button">` calling `useNavigate('/library/flaws?tag=${tag}')`. `data-testid="chip-{tag}-{gameId}"` unchanged. `aria-label` updated to `"Filter flaws by tag: {tag}"`. Removed the popover definition body and `TAG_DEFINITIONS` export. `flawThresholds.ts` (no longer consumed after removing `TAG_DEFINITIONS`) was deleted. `tagDefinitions.ts` updated to remove the threshold imports and `TAG_DEFINITIONS` export; `TAG_LABELS` retained for `FlawFilterControl`.

- **Tests:** 7 GamesTab tests (shared store, flawFilter passed to query, no URL sync, isError) + 13 TagChip tests (navigation D-05, ARIA, semantic HTML, data-testid, styling). Updated FlawsTab test's LibraryFilterPanel stub to render FlawFilterControl via props so existing clear-button and flaw-filter-control tests still work.

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Swap severity toggle for FlawFilterControl in LibraryFilterPanel (D-01) | 3907fc18 | LibraryFilterPanel.tsx, FlawsTab.tsx, FlawsTab.test.tsx |
| 2 | Migrate GamesTab to useFlawFilterStore; update useLibraryGames/FlawStats (D-04) | bfa5c5aa | GamesTab.tsx, useLibrary.ts, GlobalStats.tsx, GamesTab.test.tsx |
| 3 | TagChip → navigation deep-link to /library/flaws?tag={TAG} (D-05) | 3394288d | TagChip.tsx, tagDefinitions.ts, TagChip.test.tsx, flawThresholds.ts (deleted) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Updated useLibraryGames + useLibraryFlawStats to accept FlawFilterState (not just severity)**
- **Found during:** Task 2 implementation
- **Issue:** Plan specified "Games query passes both severity and tags" but the existing hook signatures only accepted `severity: ('blunder'|'mistake')[]`. The `buildLibraryParams` function already supported `tags` as the optional 3rd argument (from Plan 07's extension for `useLibraryFlaws`), so updating the public hook signatures to accept `FlawFilterState` was the consistent extension.
- **Fix:** Updated `useLibraryGames` and `useLibraryFlawStats` to take `FlawFilterState` instead of bare severity array. `GlobalStats.tsx` updated to pass `DEFAULT_FLAW_FILTER`.
- **Files modified:** `frontend/src/hooks/useLibrary.ts`, `frontend/src/pages/GlobalStats.tsx`
- **Commit:** bfa5c5aa

**2. [Rule 1 - Bug] Removed dead TAG_DEFINITIONS export and deleted unused flawThresholds.ts**
- **Found during:** Task 3 (knip gate after TagChip conversion)
- **Issue:** After replacing the Radix popover with a navigation button, `TAG_DEFINITIONS` (the definition text displayed in the popover) became unused. `flawThresholds.ts` was only consumed to build `TAG_DEFINITIONS` sentences, so it became an unused file.
- **Fix:** Removed `TAG_DEFINITIONS` export and all its threshold imports from `tagDefinitions.ts`. Deleted `flawThresholds.ts`. Knip gate passes after cleanup.
- **Files modified/deleted:** `frontend/src/lib/tagDefinitions.ts` (modified), `frontend/src/lib/flawThresholds.ts` (deleted)
- **Commit:** 3394288d

## Known Stubs

None — all outputs are fully functional. `LibraryFilterPanel` hosts the real `FlawFilterControl`, `GamesTab` uses the shared store, and `TagChip` navigates to the real Flaws tab route.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-108-18 (mitigated) | frontend/src/components/library/TagChip.tsx | tag value flows into client-side navigate URL; downstream API (Plan 05) validates tag as FlawTag Literal (422 on invalid). No auth decision made client-side. |
| T-108-19 (mitigated) | frontend/src/components/library/TagChip.tsx | D-05 drops game_id from chip deep-link — URL contains only tag, no game identifier. |

## Verification

```
cd frontend && npm run lint   → 0 errors
cd frontend && npm test -- --run → 805 passed (69 test files)
cd frontend && npx tsc --noEmit → All checks passed
cd frontend && npm run knip    → 0 issues
```

## Self-Check: PASSED
