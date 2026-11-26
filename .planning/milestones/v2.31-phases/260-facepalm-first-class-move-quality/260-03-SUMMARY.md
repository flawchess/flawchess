---
phase: 260-facepalm-first-class-move-quality
plan: 03
subsystem: ui
tags: [react, typescript, filters, facepalm, knip, vitest]

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-02: Blunder and Facepalm split into their own move quality rows (the facepalm dimension becomes a cut)"
provides:
  - "Library Games and Flaws Tags panels (desktop and mobile drawer) without the Facepalm Score range filter"
  - "Flaw filter state, query keys and library requests free of facepalm range fields; stale objects carrying them load as the default filter"
  - "lib/facepalm.ts reduced to score units, FACEPALM_HIGH_CUTOFF, copy constants and the type tint"
affects: [260-04, 260-05, 260-07]

requirements-completed: [D-10, D-11, D-14, D-21]

actuals:
  tokens: 8000
  tasks: 3
  commits: 3
plan_head_before: 25c6c3086ee4f9f215d3fb98dc9671e3040e058c
plan_head_after: e1bb647cdce27e912566ca18f4589f04ede63395

tech-stack:
  added: []
  patterns:
    - "Removed fields are never inspected: stale in-memory state with extra keys is ignored, and tests prove it via casts through unknown"

key-files:
  created: []
  modified:
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/__tests__/useLibraryGames.test.tsx
    - frontend/src/api/client.ts
    - frontend/src/api/__tests__/client.test.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/facepalm.ts
    - frontend/src/lib/__tests__/facepalm.test.ts
  deleted:
    - frontend/src/components/filters/FacepalmFilter.tsx

key-decisions:
  - "FACEPALM_HIGH_CUTOFF and its doc comment (lines owned by plan 259-12) left byte-identical; its wording about presets is fixed by plan 07"
  - "isFlawFilterNonDefault ignores stray range fields entirely rather than reading them defensively"

coverage:
  - id: D1
    description: "No Facepalm Score control, divider or summary renders in FlawFilterControl, on either tab or in the mobile drawer"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx#Facepalm range filter removal (D-10)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Store, query keys and requests carry no facepalm range; a stale filter object with range fields is the default filter and sends nothing"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawFilterStore.test.ts#removed facepalm range fields"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useLibraryGames.test.tsx#useLibraryGames sends no facepalm range params"
        status: pass
      - kind: unit
        ref: "frontend/src/api/__tests__/client.test.ts#no facepalm range params"
        status: pass
    human_judgment: false
  - id: D3
    description: "lib/facepalm.ts keeps score units, the cut, copy and type tint; the facepalm analytics target is removed; knip clean"
    requirement: "D-11, D-14, D-21"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/facepalm.test.ts"
        status: pass
      - kind: command
        ref: "cd frontend && npm run knip"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 03: Remove the Facepalm Score range filter Summary

**The Facepalm Score slider, presets, store fields, request params and analytics target are gone from the frontend; lib/facepalm.ts keeps only units, the untouched cut, copy and the type tint.**

## Performance

- **Duration:** about 5 min
- **Tasks:** 3 (1 tracer, 2 TDD auto)
- **Files:** 13 modified, 1 deleted

## Accomplishments

- `FacepalmFilter.tsx` deleted; `FlawFilterControl` lost the `facepalm` / `onFacepalmChange` props, the render block and `filter-facepalm-divider`; both tabs dropped the props at their desktop and mobile-drawer sites.
- `facepalmMin` / `facepalmMax` left `FlawFilterState`, `DEFAULT_FLAW_FILTER` and `isFlawFilterNonDefault`; `useLibraryGames` / `useLibraryFlaws` lost `facepalmParam` (query keys and requests); `libraryApi.getGames` / `getFlaws` lost `min_facepalm_pct` / `max_facepalm_pct`.
- `lib/facepalm.ts`: removed `FACEPALM_STEP`, `FACEPALM_MID_CUTOFF`, the preset / range / summary / query helpers and types; the `FACEPALM_HIGH_CUTOFF` declaration and its doc comment are unchanged. The `'facepalm'` filter-change target left `analytics.ts` with its only caller.
- Tests: stale objects carrying range fields are the default filter and send no facepalm parameter; `FlawFilterControl` renders no `filter-facepalm*` testid.

## Task Commits

1. **Task 1: Tracer, control gone from both Tags panels** - `c434230b9` (feat)
2. **Task 2: Range leaves store, query keys and requests** - `8009d4db3` (feat)
3. **Task 3: lib/facepalm.ts and analytics trimmed; knip clean** - `e1bb647cd` (feat)

## Deviations from Plan

None - plan executed exactly as written. The tracer gate was satisfied by re-running its `<verify>` (vitest on the three touched files and `npm run build`), both green, before the expansion tasks.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-260-08 and T-260-09 mitigated as planned (stray-fields tests; only the target whose caller was deleted was removed, FILTER_TARGETS kebab-case test green).

## Verification

- `npm run lint`, `npm run build` (tsc -b + vite) and `npm run knip`: all exit 0 (knip prints only two pre-existing configuration hints).
- Full frontend suite `npm test -- --run`: 6725 tests passed.
- Acceptance greps: all removed-symbol counts 0; `export const FACEPALM_HIGH_CUTOFF = ` count 1; the 259-12-owned doc-comment line present (1); `target: 'facepalm'` and `FacepalmPreset` in analytics.ts 0.
- Not verified: no browser check of the Tags panel layout after the divider removal (the Flaws group now flows straight into Tactic Depth, as the plan specifies).

## Next Phase Readiness

Backend parameters `min_facepalm_pct` / `max_facepalm_pct` stay until plan 07 (D-13); the frontend no longer sends them. Plan 07 must reword the `FACEPALM_HIGH_CUTOFF` doc comment (it still mentions the old presets) after 259-12 has merged.

## Self-Check: PASSED

`FacepalmFilter.tsx` absent; commits c434230b9, 8009d4db3 and e1bb647cd are ancestors of HEAD.
