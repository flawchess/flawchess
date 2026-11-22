---
phase: 260-facepalm-first-class-move-quality
plan: 06
subsystem: ui
tags: [react, typescript, move-stats, filter-ring, severity-badge, vitest]

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-02: 8-row MoveStats with the Facepalm row and compact row"
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-05: lib/flawSeverityFilter.ts (isSeverityNarrowed), three-tag Flaws filter"
provides:
  - "LibraryGameCard outlinedCellRefs: user-side refs for each narrowing Flaws tag plus has gem / has great (D-20, D-28)"
  - "MoveStats outlinedRefs prop ringing table count cells and mobile compact cells"
  - "SeverityBadge own-tag ring rule: Facepalm for the ??? badge, else its severity, only when the selection narrows (D-27)"
affects: [260-07]

requirements-completed: [D-20, D-27, D-28]

actuals:
  tokens: 6900
  tasks: 2
  commits: 2
plan_head_before: 58bd0ee663de58a971761c18ec39ad3c470dfce3
plan_head_after: df7276c3fc3d85de69159b6a45f0c753832cd71b

tech-stack:
  added: []
  patterns:
    - "Filter-ring state is derived from lib/flawSeverityFilter.ts (never mocked), so store-mocking tests need no importActual"
    - "Rings are built for userColor only; opponent cells and /analysis never ring"

key-files:
  created: []
  modified:
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
    - frontend/src/components/results/__tests__/LibraryGameCardPastedBadge.test.tsx
    - frontend/src/components/library/MoveStats.tsx
    - frontend/src/components/library/__tests__/MoveStats.test.tsx
    - frontend/src/components/library/SeverityBadge.tsx
    - frontend/src/components/library/__tests__/SeverityBadge.test.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx

key-decisions:
  - "has gem / has great read with a false fallback in LibraryGameCard so partial store mocks stay at the default filter"
  - "The SeverityBadge own tag keys on the facepalm prop alone, independent of showIcon"

coverage:
  - id: D1
    description: "Each selected Flaws tag rings its own user-side cell in the table and the mobile compact row; several tags ring several cells; none or all three ring nothing; never an opponent cell"
    requirement: "D-20"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx#LibraryGameCard MoveStats filter ring marks each selected tag (D-20, D-28)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx#MoveStats - outlinedRefs filter ring (D-20, D-28)"
        status: pass
    human_judgment: false
  - id: D2
    description: "has gem / has great ring the user Gem / Great cell independently of the Flaws tags and of each other; AnalysisTagsPanel (no outlinedRefs) rings nothing"
    requirement: "D-28"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx#LibraryGameCard MoveStats filter ring marks each selected tag (D-20, D-28)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "SeverityBadge rings when its own tag (Facepalm for ???, else severity) is part of a narrowing selection; never for inaccuracy, Train card or nothing/all selected"
    requirement: "D-27"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/SeverityBadge.test.tsx#SeverityBadge active-filter ring"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 06: Filter ring marks every selected tag Summary

**The Library card rings the user's own cell for each selected Flaws tag (Facepalm, Blunder, Mistake) and for has gem / has great, in the table and the mobile compact row, and the SeverityBadge ring follows the badge's own tag.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-22T14:16Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- `LibraryGameCard` builds `outlinedCellRefs` (replacing the single `outlinedCellRef`): one user-side ref per selected Flaws tag when `isSeverityNarrowed`, plus a Gem ref for has gem and a Great ref for has great, independent of each other and of the Flaws tags. Empty without a user color. Passed as `outlinedRefs` to both MoveStats sites.
- `MoveStats` takes `outlinedRefs` (default a stable empty list); a cell is ringed when any ref matches, in the table count buttons and now also in the compact-row buttons. `AnalysisTagsPanel` passes nothing, so /analysis never rings.
- `SeverityBadge` computes its own tag (`facepalm` for a blunder badge with the `facepalm` prop, else blunder / mistake, none for inaccuracy) and rings only when that tag is selected and `isSeverityNarrowed` holds. `showActiveFilterRing={false}` (Train card) still never rings.
- Tests: LibraryGameCard (9 ring cases plus the compact-cell case), MoveStats (outlinedRefs rings table and compact, none without refs), SeverityBadge (D-27 cases). The FlawCard, PastedBadge and SeverityBadge store mocks now use `severity: []` as the default filter.

## Task Commits

1. **Task 1: Tracer, selected tag rings its own user-side cell** - `8eca4c467` (feat)
2. **Task 2: SeverityBadge ring follows the badge's own tag** - `df7276c3f` (feat)

## Verification

- Tracer `<verify>`: vitest on LibraryGameCard, PastedBadge, MoveStats, AnalysisTagsPanel, Analysis (185 passed) and `npm run build` (exit 0), re-run after the commit; expansion proceeded.
- Mutation check: removing the compact-row ring made two new tests fail (MoveStats and LibraryGameCard compact cases); restored.
- Plan verification: `npm run lint` (0), `npm run build` (0), `npm test -- --run` (381 files, 6777 tests passed), `npm run knip` (0).
- Task 2 targeted vitest (SeverityBadge, FlawCard, TrainPuzzleCard, TagChip): 116 passed.
- All acceptance-criteria greps pass (removed shortcuts count 0, `outlinedRefs={outlinedCellRefs}` twice, `isSeverityNarrowed` imported from `@/lib/flawSeverityFilter`, only the hook imported from the store module in SeverityBadge).

## Deviations from Plan

None - plan executed exactly as written. (During the mutation check, a `git checkout` of MoveStats.tsx briefly dropped my uncommitted edits; they were restored from a backup copy before any commit, no effect on the result.)

## Known Stubs

None.

## Threat Flags

None. T-260-16 mitigated: rings are built for `userColor` only and tests assert no opponent cell ringed.

## Unverified

- Visual ring appearance on the compact mobile row in a real browser (jsdom checks the class only).

## Self-Check: PASSED

- Commits `8eca4c467` and `df7276c3f` are ancestors of HEAD.
- Modified files all exist on disk.
