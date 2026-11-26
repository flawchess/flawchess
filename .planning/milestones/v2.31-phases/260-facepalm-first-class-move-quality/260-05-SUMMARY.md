---
phase: 260-facepalm-first-class-move-quality
plan: 05
subsystem: ui
tags: [react, typescript, filters, facepalm, vitest]

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-01: backend severity=facepalm|blunder|mistake contract; 260-03: range filter removed from the store and requests"
provides:
  - "FlawSeverityFilter type (facepalm | blunder | mistake) threaded through the store, FlawFilterControl, useLibrary, client and analytics"
  - "lib/flawSeverityFilter.ts: FLAW_SEVERITY_FILTER_VALUES, isSeverityNarrowed, parseSeverityFilterParams (outside the mocked store module)"
  - "Flaws row of the Tags panel with three singular OR tags in the order Facepalm, Blunder, Mistake; Facepalm uses the ??? icon and SEV_FACEPALM / SEV_FACEPALM_BG"
  - "None or all three selected is not narrowing: no filter dot, no Games-tab severity, no Flaws-tab URL param"
affects: [260-06, 260-07]

requirements-completed: [D-08, D-09]

actuals:
  tokens: 10700
  tasks: 2
  commits: 2
plan_head_before: 9c3fd28cb6590370f9e264451fa2eb89cf2557ca
plan_head_after: 09ba28726515c072e120f8044cf86e44fc778d29

tech-stack:
  added: []
  patterns:
    - "Selection helpers live in a pure lib module, not the store module, because many component tests stub the store with a factory exporting only the hook"

key-files:
  created:
    - frontend/src/lib/flawSeverityFilter.ts
  modified:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/hooks/__tests__/useLibraryGames.test.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/api/client.ts
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - frontend/src/pages/library/__tests__/GamesTab.test.tsx

key-decisions:
  - "useLibraryGames gates severity on isSeverityNarrowed in addition to isFlawFilterNonDefault, so all three tags plus a narrowing tag family still sends no severity (the backend severity EXISTS would otherwise drop unanalyzed games)"
  - "FlawsTab and GamesTab test fixtures that used blunder+mistake as the default moved to the empty default, since blunder+mistake now narrows (it excludes facepalms)"
  - "No explanation line in the Flaws filter panel (popover-copy minimalism)"

coverage:
  - id: D1
    description: "The Flaws row shows Facepalm, Blunder, Mistake in that order with singular labels and the ??? icon on Facepalm; tags combine with OR; clicking Facepalm tracks filter-change severity=facepalm"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx#severity buttons"
        status: pass
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx#filter-change tracking"
        status: pass
    human_judgment: false
  - id: D2
    description: "Selecting Facepalm requests severity=facepalm on the Games and Flaws tabs; two tags request both; all three send nothing on the Games tab"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useLibraryGames.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "One or two tags narrow (filter dot), none or all three do not; the Flaws-tab URL round-trips only facepalm/blunder/mistake and writes no severity for none or all three"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawFilterStore.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/library/__tests__/FlawsTab.test.tsx#URL sync"
        status: pass
    human_judgment: false
  - id: D4
    description: "The selected Facepalm pill reads as dark red next to the Blunder and Mistake pills on desktop and the mobile drawer"
    requirement: "D-08"
    verification: []
    human_judgment: true
    rationale: "Pill colour legibility is visual; jsdom cannot judge it."

duration: 10min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 05: Flaws filter with Facepalm, Blunder and Mistake tags Summary

**The Flaws filter now offers Facepalm, Blunder and Mistake as three singular OR tags (`FlawSeverityFilter`), and "all three selected" replaces "both selected" as the non-narrowing case for the filter dot, the Games-tab request and the Flaws-tab URL, whose `?severity=` reader now drops unknown values.**

## Accomplishments

- Tracer: `FlawSeverityFilter` mirrors the backend Literal and flows through `useFlawFilterStore`, `FlawFilterControl`, `buildLibraryParams`, the five `client.ts` request fields and the `severity` analytics target. The Facepalm pill uses `FacepalmBlunderIcon`, `SEV_FACEPALM` and the new `SEV_FACEPALM_BG`.
- `lib/flawSeverityFilter.ts` holds `FLAW_SEVERITY_FILTER_VALUES`, `isSeverityNarrowed` and `parseSeverityFilterParams`, outside the store module that tests stub.
- `isFlawFilterNonDefault` uses `isSeverityNarrowed`; `blunder + mistake` now narrows because it excludes facepalms.
- `FlawsTab` reads `?severity=` through `parseSeverityFilterParams` (T-260-11) and writes it only when the selection narrows.

## Task Commits

1. Task 1 (tracer): `aeb40fb6e` feat(260-05): Flaws filter offers Facepalm, Blunder and Mistake as three OR tags
2. Task 2: `09ba28726` feat(260-05): all three flaw tags selected is not a narrowing filter

## Verification

- `npm run lint`, `npm run build`, `npm run knip` exit 0 (knip prints two pre-existing configuration hints, no issues).
- `npm test -- --run`: 381 files, 6760 tests passed.
- All task acceptance criteria re-run and pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Games-tab severity gate**
- **Found during:** Task 1
- **Issue:** `useLibraryGames` sent `flawFilter.severity` whenever any part of the filter narrowed. With all three tags selected plus a tag family, it would have sent `severity=facepalm&blunder&mistake`, contradicting "all three selected sends nothing on the Games tab" (D-08) and re-triggering the unanalyzed-games exclusion the gate exists to prevent.
- **Fix:** severity is sent only when `isFiltering && isSeverityNarrowed(severity)`; test added.
- **Files modified:** `frontend/src/hooks/useLibrary.ts`, `frontend/src/hooks/__tests__/useLibraryGames.test.tsx`
- **Commit:** aeb40fb6e

**2. [Rule 3 - Test fixtures] Fixtures relying on "both = default"**
- **Found during:** Task 2
- **Issue:** FlawsTab and GamesTab tests used `['blunder', 'mistake']` as the default flaw state, which now narrows.
- **Fix:** fixtures use the empty default; FlawsTab gained a `SearchProbe` so URL-writer tests can read the router search string.
- **Commit:** 09ba28726

No type-only touches were needed in GamesTab or LibraryFilterPanel; `npm run build` passed without them.

**Total deviations:** 2 auto-fixed. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-260-11 (URL tampering) mitigated by `parseSeverityFilterParams`; T-260-12 holds, the analytics value is the enumerated `FlawSeverityFilter` literal.

## Unverified

- Pill colour legibility on desktop and the mobile drawer (D4) is a visual check left to the owner.
- The backend answer to `severity=blunder` (non-facepalm blunders) is plan 01; this plan's tests check the request only.

## Self-Check: PASSED

- `frontend/src/lib/flawSeverityFilter.ts` exists; commits `aeb40fb6e` and `09ba28726` are ancestors of HEAD.
