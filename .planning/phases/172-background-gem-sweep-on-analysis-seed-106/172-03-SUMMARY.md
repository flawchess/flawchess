---
phase: 172-background-gem-sweep-on-analysis-seed-106
plan: 03
subsystem: ui
tags: [react, typescript, theme, svg, analysis-board, gem-sweep]

# Dependency graph
requires:
  - phase: 163 (SEED-092)
    provides: "GEM_GLYPH / GemIcon precedent (one-record-two-consumers glyph shape), resolveMarkerIcon severity > gem precedence, SquareMarker.gem badge geometry"
provides:
  - "BOOK_MARKER_COLOR theme token (lowest-chroma corner-marker hue)"
  - "BOOK_GLYPH one-record-two-consumers glyph spec"
  - "BookIcon component (mirrors GemIcon, BookOpen glyph, 'Opening theory' title)"
  - "FlawMarkerEntry.book field + resolveMarkerIcon severity > gem > book precedence in VariationTree"
  - "SquareMarker.book field + book badge branch in boardMarkers (board corner marker)"
affects: [172-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "book marker glyph follows the exact 'one record, two consumers' shape as gem (bookGlyph.ts -> BookIcon.tsx + boardMarkers.tsx book branch)"
    - "severity > gem > book precedence implemented differently per surface: VariationTree.resolveMarkerIcon is real runtime branching; boardMarkers.SquareMarker relies on construction-time mutual exclusivity (no runtime assertion)"

key-files:
  created:
    - frontend/src/lib/bookGlyph.ts
    - frontend/src/components/icons/BookIcon.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
    - frontend/src/components/board/boardMarkers.tsx
    - frontend/src/components/board/__tests__/boardMarkers.test.tsx

key-decisions:
  - "BOOK_MARKER_COLOR = oklch(0.60 0.04 250) added verbatim per UI-SPEC — no deviation"
  - "MoveListMarker required NO new branch — book falls through the existing plain-icon path severity already uses, confirmed by grep (single resolveMarkerIcon call site, used by both desktop and mobile render paths)"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "BOOK_MARKER_COLOR theme token + BOOK_GLYPH + BookIcon component exist, matching the gem precedent exactly (one record, two consumers, no data-testid, 'Opening theory' accessible title)"
    verification:
      - kind: unit
        ref: "tsc -b --noEmit + npm run lint (theme.ts/bookGlyph.ts/BookIcon.tsx compile clean, no raw color literal in bookGlyph.ts)"
        status: pass
    human_judgment: false
  - id: D2
    description: "VariationTree move-list marker implements severity > gem > book precedence (resolveMarkerIcon book clause is last; severity always wins over book)"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(16) book-only entry renders BookIcon"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(17) severity + book: severity wins, book icon does not render (D-08)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(18) gem + book: gem icon renders, not book"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(19) no severity, gem, or book renders nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "Board corner marker (boardMarkers.tsx) renders the book badge, inserted after the gem branch and before the severity fallback, reusing existing geometry constants verbatim"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx#renders the muted book badge with a BookOpen glyph for a book marker"
        status: pass
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx#still renders the gem badge when both gem and book could apply (ordering regression)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 172 Plan 03: Book Marker Display Layer (D-08) Summary

**New `BOOK_MARKER_COLOR` theme token, `BOOK_GLYPH`/`BookIcon` one-record-two-consumers pair, and `severity > gem > book` precedence wired into both `VariationTree.resolveMarkerIcon` and `boardMarkers.SquareMarkerBadge`.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 (Task 2 and Task 3 followed TDD RED → GREEN)
- **Files modified:** 7 (2 new, 5 modified)

## Accomplishments
- `BOOK_MARKER_COLOR = 'oklch(0.60 0.04 250)'` added to `theme.ts`, grouped with the other corner-marker identity colors — lowest chroma of any corner-marker hue per the UI-SPEC contract.
- `bookGlyph.ts` + `BookIcon.tsx` created as verbatim structural copies of the gem precedent (`gemGlyph.ts` + `GemIcon.tsx`): `BookOpen` glyph, `<title>Opening theory</title>`, no `data-testid`, no popover.
- `VariationTree.tsx`'s `resolveMarkerIcon` extended with the book clause as the LAST branch (after severity and gem), returning `isBook: true`. `FlawMarkerEntry.book?: boolean` added, doc-commented per the file's existing style. `MoveListMarker` needed no new branch — confirmed via grep that it's the single call site for all 4 render locations (mobile chip trailing, mobile mainline trailing, desktop) — book falls through the same plain-icon path severity already uses.
- `boardMarkers.tsx`'s `SquareMarker` gained `book?: boolean` and `SquareMarkerBadge` a third branch (after `marker.gem`, before the severity fallback), reusing `MARKER_STROKE`/`GEM_ICON_DIAMETER_RATIO`/`r`/`cx`/`cy` geometry verbatim — no new geometry constant introduced.

## Task Commits

Each task was committed atomically:

1. **Task 1: `BOOK_MARKER_COLOR` + `bookGlyph.ts` + `BookIcon.tsx`** - `ec52b6c8` (feat)
2. **Task 2: `severity > gem > book` in the `VariationTree` move-list marker** - TDD: `ecf441a2` (test, RED) → `43e135e5` (feat, GREEN)
3. **Task 3: The board corner book marker** - TDD: `09d25562` (test, RED) → `c688f3b2` (feat, GREEN)

**Plan metadata:** (this commit, following)

## Files Created/Modified
- `frontend/src/lib/theme.ts` - added `BOOK_MARKER_COLOR` export
- `frontend/src/lib/bookGlyph.ts` (new) - `BOOK_GLYPH` one-record-two-consumers spec
- `frontend/src/components/icons/BookIcon.tsx` (new) - white `BookOpen` on muted slate-blue dot, `<title>Opening theory</title>`
- `frontend/src/components/analysis/VariationTree.tsx` - `resolveMarkerIcon` book clause + `FlawMarkerEntry.book`
- `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` - 4 new cases: book-only, severity+book, gem+book, no-marker
- `frontend/src/components/board/boardMarkers.tsx` - `SquareMarker.book` + `SquareMarkerBadge` book branch
- `frontend/src/components/board/__tests__/boardMarkers.test.tsx` - book badge render case + gem-precedence regression case

## Decisions Made
- No deviations from the plan's exact wiring — `resolveMarkerIcon` and `SquareMarkerBadge` match the plan's stated shape verbatim.
- Confirmed (per plan's explicit instruction) that `MoveListMarker` needed no new branch: grepped `resolveMarkerIcon`/icon-render call sites in `VariationTree.tsx` and found exactly one call site inside `MoveListMarker`, which is itself called from 4 render locations covering both the desktop (`renderMoveButton`) and mobile (`siblingBlockToChips`, `MobileTree`) paths. Mobile parity confirmed structurally, not just by inspection.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Mobile Parity Check (per plan's `<verification>` section)

`VariationTree.tsx` render paths checked: desktop list (`DesktopTree` → `renderMoveButton` → `MoveListMarker`) and mobile list (`MobileTree` → `siblingBlockToChips` → `MoveListMarker`). Both route through the single `MoveListMarker` component, which itself calls the single `resolveMarkerIcon` function — one precedence-chain implementation covers both surfaces.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both marker surfaces (`VariationTree` move list, board corner marker) can now render the book badge with correct `severity > gem > book` precedence. No caller currently SETS `book: true` on either — plan 05 wires the actual `opening_ply_count`-derived boolean at the `Analysis.tsx` call site (`moveListMarkers` for the move list, `boardSquareMarkers` for the board), per this plan's frontmatter `key_links` note.
- No blockers.

---
*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 7 key files verified present on disk; all 6 commits (ec52b6c8, ecf441a2, 43e135e5, 09d25562, c688f3b2, 3cc95141) verified in git log.
