---
phase: quick
plan: 260330-qj0
subsystem: frontend
tags: [homepage, acknowledgements, credits, ui]
dependency_graph:
  requires: []
  provides: [acknowledgements-section]
  affects: [Home.tsx]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - frontend/src/pages/Home.tsx
decisions: []
metrics:
  duration: "~5 minutes"
  completed_date: "2026-03-30"
  tasks_completed: 1
  files_changed: 1
---

# Phase quick Plan 260330-qj0: Create Acknowledgements Section on Homepage Summary

**One-liner:** Added Acknowledgements section to homepage below FAQ, crediting Lichess, Chess.com, OpeningTree.com, python-chess, FastAPI, chess.js, react-chessboard, and Recharts with styled external links.

## What Was Built

A new `<section data-testid="acknowledgements-section">` was inserted in `HomePageContent` between the FAQ section (`id="faq"`) and the Footer CTA section (`data-testid="footer-cta"`). The section contains:

- A brief intro paragraph: "FlawChess is built with and inspired by these projects:"
- An unordered list (`list-disc pl-5 space-y-1.5`) with 8 entries grouped as platforms, backend libraries, and frontend libraries
- All links use `target="_blank" rel="noopener noreferrer"` and `className="text-primary underline-offset-4 hover:underline"` to match FAQ link styling
- No id attribute and no header navigation link for this section

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Acknowledgements section to homepage | 09f4b0d | frontend/src/pages/Home.tsx |

## Verification

- `npm run build` completed without errors
- Acknowledgements section positioned below FAQ, above Footer CTA
- All 8 projects linked: Lichess, Chess.com, OpeningTree.com, python-chess, FastAPI, chess.js, react-chessboard, Recharts
- No header navigation link added

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- frontend/src/pages/Home.tsx: FOUND (modified)
- Commit 09f4b0d: FOUND
