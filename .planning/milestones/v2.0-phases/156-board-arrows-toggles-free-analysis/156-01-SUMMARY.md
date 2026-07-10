---
phase: 156-board-arrows-toggles-free-analysis
plan: 01
subsystem: frontend-analysis-board
tags: [board-arrows, flawchess-engine, stockfish, free-analysis, theme]
requires: []
provides:
  - FLAWCHESS_ENGINE_ARROW
  - BoardArrow.layerKey
  - engineArrows (Analysis.tsx)
affects:
  - frontend/src/pages/Analysis.tsx (free-analysis board arrow layer)
  - frontend/src/components/board/ChessBoard.tsx (BoardArrow contract)
  - frontend/src/components/board/arrowGeometry.ts (dedupe key contract)
tech-stack:
  added: []
  patterns:
    - "layerKey dedupe-bypass mirrors the existing onTop `-top` suffix escape in arrowMoveKey"
key-files:
  created: []
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/arrowGeometry.ts
    - frontend/src/components/board/__tests__/dedupeArrowsByMove.test.ts
    - frontend/src/pages/Analysis.tsx
decisions: []
metrics:
  duration: ~15min
  completed: 2026-07-06
status: complete
---

# Phase 156 Plan 01: Board Arrows + Toggles (Free Analysis) Summary

Rendered the two live engines' top moves as distinct, concentric board arrows on the free-analysis `/analysis` board: an amber FlawChess Engine arrow (practical move) and the existing blue Stockfish arrow (objective move), both independently toggleable via the Phase 155 card switches and refining live.

## What Was Built

**Task 1 (TDD — RED/GREEN):**
- `FLAWCHESS_ENGINE_ARROW` — new amber/gold (`oklch(0.78 0.15 85)`) board-arrow token in `theme.ts`, distinct from the card's brown `FLAWCHESS_ENGINE_ACCENT` (D-04).
- `BoardArrow.layerKey?: string` — new optional field on the `BoardArrow` interface in `ChessBoard.tsx`.
- `arrowMoveKey` in `arrowGeometry.ts` now folds `layerKey` into the dedupe key after the existing `-top` suffix, so two arrows on the same from→to with distinct `layerKey`s both survive `dedupeArrowsByMove` (D-06) while arrows with no `layerKey` still collapse as before (regression-safe).
- Two new unit cases added to `dedupeArrowsByMove.test.ts` (RED confirmed failing before the implementation, GREEN after).

**Task 2:**
- New named constants in `Analysis.tsx`: `ARROW_COUNT = 1` (top-1-per-engine, D-02, future-configurable per D-03), `FLAWCHESS_ENGINE_ARROW_WIDTH = 0.80`, `STOCKFISH_ENGINE_ARROW_WIDTH = 0.50`.
- New `engineArrows` `useMemo<BoardArrow[]>` building the FC arrow (from `flawChessEngine.rankedLines[i].rootMove`, gated on `flawChessEnabled`) and the SF arrow (from `engine.pvLines[i].moves[0]`, gated on `engineEnabled`), each converted via the existing `uciToSquares` helper and tagged with a distinct `layerKey` (`fc-i` / `sf-i`). All array indexing is `?? null`-guarded (`noUncheckedIndexedAccess`).
- Spliced into `baseArrows` only on the free-analysis (`!isGameMode`) path: `qualityHoverArrows ?? (isGameMode ? (pvSidelineArrows ?? gameOverlay.boardArrows) : (engineArrows.length > 0 ? engineArrows : undefined))`. Game-mode arrows and the existing `nextMoveArrow` (thin white, `onTop`) are untouched.
- Draw order (FC widest at bottom, SF medium in the middle, white thinnest on top) comes entirely from `ChessBoard`'s existing width-sort + `onTop` logic — no array reordering needed.
- Mobile parity is automatic: `boardArrows` feeds the single shared `boardRow` JSX block rendered by both the mobile (L1589) and desktop (L1732) trees.

## Deviations from Plan

None — plan executed exactly as written. Constants, memo shape, splice point, and gating all match the plan's `<action>` blocks verbatim.

## Verification

- `cd frontend && npx tsc -b` — zero type errors.
- `cd frontend && npm run lint` — zero errors (3 pre-existing warnings in `coverage/*.js`, unrelated).
- `cd frontend && npm test -- --run` — 127 test files, 1527 tests, all passing (includes the two new `dedupeArrowsByMove` cases).
- `grep -rn "best move" frontend/src/pages/Analysis.tsx` — no matches; no new unqualified "best move" copy introduced (ARROW-04/D-07).
- Manual/UAT (not gating, per plan): visual concentric-arrow rendering and independent-toggle behavior on the live board are left for user verification.

## Requirements Closed

- ARROW-01: amber FlawChess Engine arrow renders from `rankedLines[0].rootMove` and refines live via the `engineArrows` memo's dependency array.
- ARROW-02: FC and SF arrows independently toggle via the existing `flawChessEnabled` / `engineEnabled` switches — each arrow's loop is separately gated.
- ARROW-03: SF arrow reuses the existing `BEST_MOVE_ARROW` pattern (same color/helper as `useGameOverlay`'s Stockfish arrow); no dedicated Maia arrow layer added.
- ARROW-04: no new "best move" unqualified copy; `FLAWCHESS_ENGINE_ARROW` and `BEST_MOVE_ARROW` render as two distinct colored arrows rather than a merged "best" concept.

## Known Stubs

None. Both arrows are wired to live engine data with no placeholder/mock values.

## Threat Flags

None — this phase adds no network calls, endpoints, auth surface, or persistence; it renders SVG arrows from engine output already in browser memory (per the plan's threat model, T-156-01, accepted).

## Self-Check: PASSED

- `frontend/src/lib/theme.ts` — FOUND, contains `FLAWCHESS_ENGINE_ARROW`.
- `frontend/src/components/board/ChessBoard.tsx` — FOUND, `BoardArrow.layerKey` present.
- `frontend/src/components/board/arrowGeometry.ts` — FOUND, `arrowMoveKey` folds `layerKey`.
- `frontend/src/components/board/__tests__/dedupeArrowsByMove.test.ts` — FOUND, 7 tests (5 original + 2 new), all passing.
- `frontend/src/pages/Analysis.tsx` — FOUND, `engineArrows` memo + constants + splice present.
- Commit `752947aa` (test RED) — FOUND in `git log`.
- Commit `3e9d5067` (feat GREEN Task 1) — FOUND in `git log`.
- Commit `5884a611` (feat Task 2) — FOUND in `git log`.
