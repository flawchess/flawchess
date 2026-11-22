---
phase: 260-facepalm-first-class-move-quality
plan: 02
subsystem: ui
tags: [react, typescript, move-stats, facepalm, vitest]

requires:
  - phase: 257-facepalm-library-stats
    provides: isFacepalmBlunder, FACEPALM_HIGH_CUTOFF, FacepalmBlunderIcon
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-01: opponent markers carry facepalm_score (D-24)"
provides:
  - "flawMoveCategory, FlawMoveCategory and MOVE_STAT_CATEGORY_ORDER in lib/moveStatsCounts.ts (the one display-split classifier, D-07)"
  - "8-row MoveStats table, 7-cell mobile compact row, Facepalm popover entry (D-01, D-05, D-06)"
  - "Blunder and Facepalm cycle maps on LibraryGameCard and AnalysisTagsPanel (D-04, D-19)"
  - "lib/gameCardGeometry.ts: desktop board size and eval chart height derived from the table (D-15, D-16, D-25)"
affects: [260-04, 260-05]

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-15, D-16, D-19, D-25]

actuals:
  tokens: 11000
  tasks: 3
  commits: 3
plan_head_before: e7c8842b68b703b73ba2b5959d2297cef3928e40
plan_head_after: 89e99215d4c812f6e60b89738ae32d3b1d822314

tech-stack:
  added: []
  patterns:
    - "One display classifier (flawMoveCategory) read by the table and its cycle maps; Lichess-meaning surfaces keep FlawSeverity"
    - "Layout sizes derived from named constants and the category count, with a test pinning the literal Tailwind class to the number"

key-files:
  created:
    - frontend/src/lib/gameCardGeometry.ts
    - frontend/src/lib/__tests__/gameCardGeometry.test.ts
  modified:
    - frontend/src/lib/moveStatsCounts.ts
    - frontend/src/lib/__tests__/moveStatsCounts.test.ts
    - frontend/src/components/library/MoveStats.tsx
    - frontend/src/components/library/__tests__/MoveStats.test.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx

key-decisions:
  - "MoveQuality and MoveQualityIcon stay unchanged; MoveStats renders the Facepalm icon through a local MoveStatIcon (Pitfall 6)"
  - "Desktop board is 248px (247px table rounded up to whole-pixel squares); the eval chart takes the extra 23px (h-[127px]) and the tags card keeps 97px"
  - "Facepalm popover definition reads FACEPALM_HIGH_CUTOFF in a template string, no literal cut"

coverage:
  - id: D1
    description: "A facepalm blunder counts in the Facepalm row and not in Blunder; an unscored blunder stays in Blunder; Blunder plus Facepalm equals the blunder markers per side"
    requirement: "D-02, D-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/moveStatsCounts.test.ts#flawMoveCategory"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/moveStatsCounts.test.ts#severityCountsBySide facepalm split"
        status: pass
    human_judgment: false
  - id: D2
    description: "MoveStats renders 8 rows with Facepalm last, and the Library card and /analysis cells cycle only their own plies"
    requirement: "D-01, D-04, D-19"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx#LibraryGameCard Facepalm row split and cycling"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx#AnalysisTagsPanel Facepalm split and cycling"
        status: pass
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx#MoveStats all 8 rows always render"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mobile compact row shows gem, great, best, mistake, blunder, facepalm plus the chevron; popover lists Facepalm from the cut constant and the Lichess sum sentence"
    requirement: "D-05, D-06"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx#MoveStats mobile compact row"
        status: pass
      - kind: unit
        ref: "frontend/src/components/library/__tests__/MoveStats.test.tsx#MoveStats accuracy info popover"
        status: pass
    human_judgment: false
  - id: D4
    description: "Desktop miniboard and eval chart sizes derive from the table height; mobile chart stays h-[114px]"
    requirement: "D-15, D-16, D-25"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/gameCardGeometry.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx#LibraryGameCard eval chart heights"
        status: pass
    human_judgment: true
    rationale: "jsdom cannot measure layout: the board bottom and the table card bottom being level within 1px must be read in a real browser at lg (plan Task 3 human-check, left to the orchestrator)"

duration: 20min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 02: Facepalm row in the move quality table Summary

**The move quality table splits Blunder and Facepalm through one classifier (`flawMoveCategory`), cycles each on both card surfaces, and the desktop board and eval chart are sized from the 8-row table.**

## Performance

- **Duration:** about 20 min
- **Completed:** 2026-11-22T13:46Z
- **Tasks:** 3
- **Files modified:** 10 (2 new)

## Accomplishments

- `flawMoveCategory` returns 'facepalm' exactly for a blunder whose score reaches `FACEPALM_HIGH_CUTOFF`, else the severity; `severityCountsBySide` counts disjointly, so Blunder plus Facepalm equals the Lichess blunder count. `MOVE_STAT_CATEGORY_ORDER` puts Facepalm last.
- `MoveStats` has 8 rows, a 7-cell compact row (`grid-cols-7`: gem, great, best, mistake, blunder, facepalm, chevron), a Facepalm popover definition built from `FACEPALM_HIGH_CUTOFF`, and the sentence "Blunders and facepalms together make up Lichess's blunder count." The Blunder definition is unchanged.
- `LibraryGameCard` and `AnalysisTagsPanel` feed `flawMoveCategory(fm)` into their cycle maps; `facepalmPlies` on the card uses the same classifier, so no second inline copy of the cut test remains.
- `lib/gameCardGeometry.ts` derives the table height (247px), the board size (248px, whole-pixel squares) and the desktop eval chart height (127px, tags card kept at 97px). Mobile sizing is untouched.

## Task Commits

1. **Task 1: Tracer, Facepalm row and cycling on the Library card** - `2e4754745` (feat). Also carries the compact-row and popover code of MoveStats.tsx (same file, see deviations).
2. **Task 2: Analysis panel, compact row and popover tests** - `5b902d9a0` (feat)
3. **Task 3: Geometry derived from the table** - `89e99215d` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Ordering] Compact row and popover implemented in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** Task 2's MoveStats changes (COMPACT_CATEGORY_ORDER, grid-cols-7) and Task 1's changes sit in the same file and the same pass; splitting them would have needed an intermediate state with a broken 8-cell compact row.
- **Fix:** Task 1's commit contains the MoveStats.tsx work for both; Task 2's commit holds the AnalysisTagsPanel change, the compact-row and popover tests, and comments. All Task 2 acceptance criteria hold.
- **Commit:** 2e4754745

**2. [Rule 1 - Test bug] Compact-cell count assertion read icon glyph text**
- **Found during:** Task 2
- **Issue:** `textContent` of a compact cell includes the SVG glyph text ("1??"), so `toBe('1')` failed.
- **Fix:** the test reads the first span (the count).
- **Files modified:** frontend/src/components/library/__tests__/MoveStats.test.tsx
- **Commit:** 5b902d9a0

**Total deviations:** 1 ordering note, 1 test fix. **Impact:** none on scope or behavior.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary; T-260-06 and T-260-07 accepted as planned.

## Verification

- `npx vitest run src/lib src/components/library src/components/results src/components/analysis`: 181 files, 3474 tests passed.
- `npm run lint` (whole tree, run in the Task 2 gate) and a re-run of eslint over the touched directories after the last edits: clean. `npm run build`: passes after every task. `npm run knip`: no issues (two pre-existing configuration hints only).
- All Task 1, 2 and 3 acceptance greps return their expected values, including the guard mutations (MoveQuality / MoveQualityIcon free of 'facepalm', Lichess-meaning surfaces free of `flawMoveCategory`, mobile `h-[114px]` kept, Blunder definition unchanged).
- Not run: the Task 3 browser measurement (board bottom vs table card bottom within 1px at lg, eval chart taller, tags card roughly 97px). The pixel constants come from the class arithmetic in the research; if a row measures 25px, change `MOVE_STATS_ROW_PX` only and re-run `gameCardGeometry.test.ts` (the literal `DESKTOP_EVAL_CHART_HEIGHT_CLASS` must then be updated with it).

## Next Phase Readiness

Plans 260-04 (eval chart) can import `flawMoveCategory`; 260-05 can use the Facepalm cells and the `severity=facepalm` filter from 260-01. Frontend plans continue one at a time.

## Self-Check: PASSED

Created files exist (`frontend/src/lib/gameCardGeometry.ts`, `frontend/src/lib/__tests__/gameCardGeometry.test.ts`); commits 2e4754745, 5b902d9a0 and 89e99215d are ancestors of HEAD.
