---
phase: 237-train-reveal-chips-move-tree
plan: 11
subsystem: ui
tags: [train, uat, browser, changelog, gate]
status: complete

requires:
  - phase: 237-10 (tour rewrite)
    provides: "six-step tour, tourBubble slot, phone tour scroll"
provides:
  - "Agent browser UAT evidence for 390x844 / 375x667 / 768x1024 / 1280x800 and the tour (D-11)"
  - "CHANGELOG [Unreleased] Changed bullet + operator note"
  - "Tour phone scroll keeps the bubble readable (UAT fix)"
affects: []

key-files:
  created: []
  modified:
    - CHANGELOG.md
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/hooks/useTreeMoveGrading.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx

key-decisions:
  - "No constant tuning: TRAIN_MOVE_TREE_HEIGHT_CLASS (h-16) and the TRAIN_FOCUS_* opacities (0.92/0.22 arrows, 1/0.32 badges) passed as shipped"
  - "Tour phone scroll: the bubble always stops just under the pinned block (was: target-first fallback that hid the bubble behind the sticky board)"

requirements-completed: [D-11]

duration: ~75min
completed: 2026-10-09
---

# Phase 237 Plan 11: Browser UAT, CHANGELOG, pre-merge gate

Run inline by the orchestrator (subagents cannot reach claude-in-chrome). Dev stack: the already-running uvicorn `--reload` :8000 + Vite :5173 from this checkout; dev user 28 via the saved dev JWT; phone/desktop sizes via a same-origin iframe of the exact size (memory: browser UAT techniques).

## Hidden-tab artifacts (not defects)

The MCP tab reports `visibilityState: hidden`, which (a) pauses Stockfish by design (D-04 tab-hide pause), (b) stops `requestAnimationFrame` (board piece animation and the tour's scroll tween stall), and (c) never dispatches `matchMedia` change events on an iframe resize. Worked around by overriding the iframe document's `visibilityState`, shimming `requestAnimationFrame` onto `setTimeout`, and reloading the iframe at each size instead of resizing a mounted page.

## Task 1: 390x844 reveal flow

| # | Item | Result | Evidence |
|---|------|--------|----------|
| 1 | First view fits, no scroll | PASS | `scrollHeight=844 innerHeight=844` on two puzzles (2 chips; 3 chips + game footer). Strip y384-432, chips 449-517, list 533-597, footer 613-661, bottom bar 787-844 |
| 2 | Bottom bar ⏮ ‹ › ⇅ + Analyze + Next in one row, main nav gone | PASS | `mobile-board-controls-bar` buttons: board-btn-reset/back/forward/flip, btn-train-analyze, btn-train-next; no `mobile-nav-*` during the reveal |
| 3 | You focused; others dimmed; Best tap lights Best, board stays | PASS | You: a6 arrow opacity 0.92, best + also-fine arrows 0.22, You badge 1, others 0.32. Best tap: best arrow 0.92, e3 badge 1, board signature unchanged |
| 4 | List tap steps the board, no page jump | PASS | tap `variation-node-1` changed the board, `scrollY=0`, `scrollHeight` still 844 |
| 5 | Fork: sideline with x, Stockfish row (2 lines), grading mark | PASS | list `a6 18. Bf3 ( h6 ) Ne3 ...`, `btn-delete-line-*`; SF row expanded shows `+5.5 1. Bxd5 ...` and `+4.3 1. Nc3 ...`; board badge "?!" on h6 (eval +3.66 -> +5.57). The move list draws no inaccuracy glyph by design (D-03, same as Analysis) |
| 6 | ⏮ back to the puzzle position keeping the sideline; x removes it | PASS | after rewind a7 pawn back, list still contains `( h6 )`; after x the list has no sideline and 0 delete buttons |
| 7 | Strip expands (verdict, Your call, prose, Also fine) and collapses | PASS | details text "Close. Right call +1, wrong move +0 ... Your call: several good moves +1 ... Also fine, e.g. f5, e4"; collapse restores `scrollHeight=844` |
| 8 | Next advances, normal nav back, next strip collapsed (D-08) | PASS | after Next: `mobile-nav-*` present, guess prompt for 4 of 9; next reveal `aria-expanded=false` |

Screenshots: `temp/puzzle-reveal-ux/after/390-first-view-top.jpg`, `390-first-view-bottom-3chips.jpg` (host capture shows the top/bottom halves of the 390x844 iframe).

## Task 2: other sizes and the tour

| Leg | Result | Evidence |
|-----|--------|----------|
| 375x667 | PASS | reveal renders, `scrollHeight=749` (scroll allowed), fixed bar at 610-667 |
| 768x1024 | PASS | no fixed bar (`mobile-board-controls-bar` hidden); in-flow `train-reveal-action-bar` y439-487 under the board; strip, chips, list, footer below; `scrollHeight=1024` |
| 1280x800 | PASS | fresh mount: board + eval bar left, action bar y628-676 with the "← → Home" hint; verdict bubble y111-315, chips, list, footer in the right column; `scrollHeight=800`. Keyboard: → enters `a6`, → `14. Qe2+`, ← back, Home to ROOT with the board back on the puzzle position (read after the animation settles) |
| Tour 390x844 | PASS (after fix) | six steps in order; strip expand, chip tap, list tap and fork each advanced their step; rings on strip, chips, list, board row, chips + list, and the FIXED bottom bar (`train-reveal-action-bar` inside `mobile-board-controls-bar`, y787); "Got it" ends the tour, stamps `reveal_walkthrough_seen_at`, view back to `844/844` |
| Tour 1280x800 | PASS | tour bubble y111-238 above the verdict bubble y254-498 in the right column; all six rings land; no scroll; "Got it" ends it and stamps |
| Tour 375x667 | PASS with a note | bubble readable on every step (top 363 > pinned bottom 351); see the trade-off below |
| Real-phone tap leg | PENDING (owner) | thumb reach, iOS Safari bottom bar + safe area |

## Deviations

1. **[Rule 1 - Bug] Tour bubble slid behind the sticky board (fixed, 1a997e563).** At 390x844, after the result step's own action (tapping the strip expands its feedback), the chips no longer fit under the bubble, so plan 10's target-first fallback scrolled the chips under the pinned block and pushed the bubble to y -19..223, behind the sticky board (y 0..366): the step copy and the lines step's only Next button were unreadable/unreachable. `computeTourScrollDelta` now always anchors the bubble just under the pinned block (target-first only without a bubble); `WALKTHROUGH_BOTTOM_BAR_RESERVE_PX` removed. Regression test re-asserted ("the bubble still stops just under the pinned block (never behind it)"); reverting the hook turns it red (mutation-checked).
2. **Comment fix** in `useTreeMoveGrading.ts`: it claimed the move list shows an inaccuracy glyph; the shared list omits it by design (D-03).

## Owner judgment (pending)

- **Tour targets below the fold on small phones.** With the bubble kept readable, the ringed chips/list sit a short scroll below the fixed bar on steps 1, 2 and 4 when the strip's feedback is expanded (390x844) and always at 375x667. Options if this reads badly on a device: collapse the strip's feedback when the tour leaves the result step, or render the tour bubble next to its target instead of above the strip.
- Dim levels 0.22 / 0.32, list height h-16 and bar density look right in the DOM measurements; confirm on a real phone.

## Gate

- CHANGELOG-OK (both bullets under `### Changed`, no em-dashes) - 2ca003a25.
- Backend: ruff format --check (523 files), ruff check, ty (app/tests/scripts and analysis), nesting gate (1164 functions, no breaches), `pytest -n auto -x` 5448 passed / 19 skipped, serial train run 169 passed.
- Frontend (after the fix): lint clean, `npm run build` exit 0, vitest 320 files / 5421 tests passed, knip clean.

## Dev data touched

Dev DB only: user 28's `reveal_walkthrough_seen_at` reset to NULL four times for the tour legs (stamped again by "Got it"); puzzles 3-9 of the dev session were solved during UAT.

## Self-Check: PASSED
