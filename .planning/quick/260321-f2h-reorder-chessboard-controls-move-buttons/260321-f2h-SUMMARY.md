---
phase: quick
plan: 260321-f2h
subsystem: frontend
tags: [ui, mobile, board-controls, layout]
dependency_graph:
  requires: []
  provides: [reordered-board-controls-layout, board-controls-info-slot]
  affects: [openings-page-desktop, openings-page-mobile]
tech_stack:
  added: []
  patterns: [slot-prop-pattern, sticky-mobile-controls]
key_files:
  created: []
  modified:
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "Used infoSlot prop pattern (React.ReactNode) rather than a specific InfoPopover prop — keeps BoardControls decoupled from InfoPopover implementation"
  - "hover:bg-accent on buttons inside bg-muted container — accent is slightly darker than muted, providing visible hover feedback without fighting the parent background"
  - "Mobile BoardControls moved inside the sticky div — keeps move buttons always visible alongside the board when scrolling"
metrics:
  duration: "~10 min"
  completed: "2026-03-21"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick Plan 260321-f2h: Reorder Chessboard Controls -- Move Buttons Below Board Summary

**One-liner:** Moved board controls directly below the chessboard (before opening name) on both desktop and mobile, integrated the chessboard info popover into the controls row with a bg-muted background and evenly spaced buttons.

## What Was Built

- `BoardControls` gains an optional `infoSlot` prop (`React.ReactNode`) rendered on the far right of the row.
- The outer container now uses `flex items-center rounded-lg bg-muted` for a persistent grey background matching the ToggleGroup active/hover state.
- The 4 move buttons are wrapped in `flex flex-1 items-center justify-evenly` so they spread evenly across available width.
- Button hover changed from the invisible `hover:bg-muted` (same as parent) to `hover:bg-accent` for visible feedback.
- **Desktop sidebar**: `BoardControls` moved directly after `ChessBoard`, chessboard `InfoPopover` passed as `infoSlot`. Opening name row no longer contains the info icon.
- **Mobile layout**: `BoardControls` moved inside the sticky `div` (alongside `ChessBoard`) so move buttons are always visible when scrolling. Mobile chessboard `InfoPopover` (`testId="chessboard-info-mobile"`) passed as `infoSlot`. Mobile opening name row no longer contains the info icon.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npm run build` passes with no type errors.
- Pre-existing lint errors in `dev-dist/workbox-*.js`, `App.tsx`, `SuggestionsModal.tsx`, and shadcn UI files are out of scope and were not introduced by these changes.

## Self-Check: PASSED

- `frontend/src/components/board/BoardControls.tsx` — modified, committed 8751e15
- `frontend/src/pages/Openings.tsx` — modified, committed ab02e1f
