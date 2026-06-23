---
phase: quick-260622-fdh
plan: "01"
status: complete
completed: "2026-06-22"
tags: [frontend, library, layout, ui]
key-files:
  modified:
    - frontend/src/components/results/LibraryGameCard.tsx
decisions:
  - Reused existing fragment definitions (severityBadges, chipsBlock) unchanged; only relocated their render site in the desktop body
  - Kept heightClass="h-[116px]" on the desktop EvalChart (same as before; three right-column rows sum to ~200px)
  - Used sm:flex sm:items-center pattern for the desktop header span (was sm:block) to allow inline date label without breaking truncation
metrics:
  duration: "~15 min"
---

# Quick 260622-fdh: Redesign LibraryGameCard Desktop Layout Summary

**One-liner:** Desktop LibraryGameCard redesigned as board-only left column (200px) plus right column stacking metadata strip, eval chart, and tactic chips; game date moved to header.

## What Was Done

### Task 1: Date in desktop header + desktopMetaStrip fragment

- Desktop header span changed from `sm:block` to `sm:flex sm:items-center` so the matchup text truncates on the left and the formatted date sits as a muted trailing label (`shrink-0 text-muted-foreground`).
- Mobile header (`flex sm:hidden`) untouched.
- New `desktopMetaStrip` fragment added (desktop-only): one flex row rendering `<BookOpen> opening · TC · moves · result` at `text-sm`, with the opening name as the only truncating element. Does not touch the shared `metadata`, `openingLine`, or mobile body.

### Task 2: Desktop body rebuilt as two-column layout

- `DESKTOP_BOARD_SIZE` bumped from `132` to `200`.
- Desktop body (`hidden sm:flex`) rewritten as `sm:flex sm:gap-3 sm:items-stretch`:
  - **LEFT column** (`shrink-0`): `LazyMiniBoard` only at 200px.
  - **RIGHT column** (`flex-1 min-w-0 flex flex-col gap-2`), three stacked rows:
    1. `desktopMetaStrip`
    2. Eval chart + severity badges (same pairing as before, same testids)
    3. Tactic chips (`chipsBlock`, analyzed + truthy only, in `flaw-controls-*` wrapper)
- Dropped the `md:grid md:grid-cols-3` alignment trick (chips now live in the right column, not a full-width row beneath).
- Shared fragment definitions (`severityBadges`, `chipsBlock`, `flawContent`, `metadata`, `openingLine`) unchanged.
- Mobile body (`sm:hidden`) byte-for-byte unchanged.

### Task 3: Full frontend gate

All three gates passed:
- `npx tsc -b` — clean (0 errors)
- `npm run lint` — 0 errors, 3 pre-existing warnings in coverage/ (not our code)
- `npm test -- --run` — 1083/1083 tests passed

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 7d3a3a62 | feat(library): redesign LibraryGameCard desktop layout as board-left / stacked-right |

## Self-Check: PASSED

- [x] `frontend/src/components/results/LibraryGameCard.tsx` modified (1 file changed, 65 insertions, 53 deletions)
- [x] Commit 7d3a3a62 exists on branch `gsd/phase-130-tactic-tag-improvements-and-fixes`
- [x] `DESKTOP_BOARD_SIZE = 200` in the file
- [x] `desktopMetaStrip` fragment defined and used in desktop body only
- [x] Mobile body (`sm:hidden` div at ~line 894) unchanged per git diff
- [x] All shared fragment definitions unchanged per git diff
- [x] All existing `data-testid`s preserved (`flaw-controls-*`, `card-col2-*`, `eval-chart-*`, `library-game-card-*`)
