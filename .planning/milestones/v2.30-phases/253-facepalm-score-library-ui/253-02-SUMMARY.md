---
phase: 253-facepalm-score-library-ui
plan: 02
subsystem: frontend
tags: [library, filters, facepalm, umami]
requires:
  - phase: 253-01
    provides: "GET /library/flaws and /library/games accept min_facepalm_pct / max_facepalm_pct (inclusive floored percents), coded against the plan's API contract"
provides:
  - "Facepalm range filter (All/Low/Mid/High + two-handle slider) in the Library Tags panel on both tabs"
  - "lib/facepalm.ts domain module and facepalmToQueryParams"
  - "optional hint prop on PresetRangeFilter"
affects: [library-games, library-flaws, flaw-filter-store]
tech-stack:
  added: []
  patterns: ["PresetRangeFilter wrapper cloned from TacticDepthFilter", "param omitted at default so request and query key are unchanged"]
key-files:
  created:
    - frontend/src/lib/facepalm.ts
    - frontend/src/lib/__tests__/facepalm.test.ts
    - frontend/src/components/filters/FacepalmFilter.tsx
  modified:
    - frontend/src/components/filters/PresetRangeFilter.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/__tests__/useLibraryGames.test.tsx
    - frontend/src/api/client.ts
    - frontend/src/api/__tests__/client.test.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/pages/library/GamesTab.tsx
key-decisions:
  - "Facepalm params are omitted at All (unlike the always-sent depth bounds), so the common request and react-query key do not change (D-04)"
  - "FacepalmFilter is gated in FlawFilterControl on the onFacepalmChange handler (like Gem/Great), not on showTacticFilter"
  - "A custom range counts as an active summary (activePreset !== 'all')"
requirements-completed: [D-01, D-03, D-04, D-06, D-08, D-09, D-10, D-11, D-12, D-13, D-19]
duration: 25 min
completed: 2026-11-14
status: complete
commits: 3
plan_head_before: 4b40f81e6421fe6bf53cec7d4572c204aac15fe0
plan_head_after: 8615dd7b5
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
---

# Phase 253 Plan 02: Facepalm range filter Summary

Facepalm filter in the Library Tags panel on both tabs: four preset chips plus a two-handle slider in steps of 5, sending inclusive floored percents (Low 0-29, Mid 30-69, High 70-100, custom upper handle + 4) only when narrowed, with a "Mistakes are excluded" hint and Umami tracking.

## Accomplishments

- `lib/facepalm.ts`: constants (30/70 cutoffs are plain UI constants), presets, `derivePreset`, `sliderToRange`, `displayUpper`, `isFacepalmNarrowed`, `formatFacepalmSummary`, `facepalmToQueryParams` (returns `{}` at All).
- `FacepalmFilter` over `PresetRangeFilter` with the owner-approved info copy verbatim; `PresetRangeFilter` gained an optional `hint` (other callers unchanged).
- Store fields `facepalmMin/Max` with `??`-guarded dot clause (lights only when narrowed).
- `getGames`/`getFlaws` forward `min_facepalm_pct`/`max_facepalm_pct` (min of 0 included); both hooks put the param in the query key.
- Section placed directly under Flaws and above Best Moves / Tactic Depth, on desktop panel and mobile drawer of both tabs; severity toggles untouched (D-11).
- Umami: `facepalm` filter-change target; preset change sends the preset key, slider commit one debounced event with preset or `custom`; bounds never sent.

## Verification

- `npx vitest run` on the five touched test files: 139 passed.
- `npm run lint`, `npm run build` (tsc -b), `npm run knip`: all exit 0 (knip prints only two pre-existing configuration hints).
- Banned-wording grep (avoidable / chance you / provisional) over filters dir and facepalm.ts: no match.
- Acceptance greps: `onFacepalmChange=` 2 in each tab; `min_facepalm_pct` 4 in client.ts.
- HUMAN-UAT (not blocking, not run): visual position in the desktop panel and mobile drawer on both tabs.

## Deviations from Plan

**1. [Process] Tasks 1-3 committed as three grouped commits, not strictly per task, and TDD RED/GREEN not split.**
- The tracer files, the Task 3 hint/tracking/analytics pieces and the shared client/useLibrary edits (one edit serves getFlaws and getGames) landed together, so commit 1 covers Task 1 plus the non-test parts of Task 3, commit 2 the Games tab, commit 3 the panel tests. Tests were written alongside the implementation rather than as separate RED commits. All behaviors have passing tests.

**2. [Rule 1 - Test validity] Query-key test uses a shared QueryClient.**
- `makeWrapper()` builds a new QueryClient on every render, which would refetch on `rerender` regardless of the key and make the "range changes the query key" test vacuous. The test uses one shared client instead.

**Total deviations:** 2 (1 process, 1 test-validity). **Impact:** none on behavior.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- Files exist: facepalm.ts, facepalm.test.ts, FacepalmFilter.tsx.
- Commits 73898d84c, 05e4586a1, 8615dd7b5 are on the branch.
