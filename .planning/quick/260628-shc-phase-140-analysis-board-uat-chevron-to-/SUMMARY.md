---
quick_id: 260628-shc
slug: phase-140-analysis-board-uat-chevron-to-
date: 2026-06-28
status: complete
---

# Summary: Phase 140 analysis-board UAT — engine-line chevron + sideline grafting

## What changed

Two UAT fixes on the `/analysis` engine lines, plus a follow-up adjustment.

1. **Chevron to expand each engine line.** Each of the two Stockfish PV lines now
   renders a `ChevronDown` button on the right when the line is longer than
   `MAX_PLIES` (5). Clicking it toggles the row between the first 5 plies and the
   full principal variation (chevron rotates 180° when expanded). State is
   per-row and persists across the engine's streaming depth updates (stable
   `lineIndex` key). The desktop engine card body changed from a fixed
   `h-[78px] overflow-y-auto` to `min-h-[78px]`, so the card grows to fit an
   expanded line instead of scrolling inside a clipped box (follow-up request).

2. **Clicking a line move grafts the whole sideline.** `EngineLines.onMoveClick`
   changed from `(from, to)` to `(uciMoves: string[])`; each chip passes the UCI
   prefix `moves.slice(0, moveIndex + 1)`. A new `useAnalysisBoard.playUciLine`
   grafts that whole prefix from the current anchor node in one `setState`
   (reusing matching children to avoid duplicate branches) and navigates to the
   last move. Previously `onMoveClick` was wired straight to `makeMove`, which
   played only the single clicked move from the shown position, skipping every
   move before it.

## Files

- `frontend/src/hooks/useAnalysisBoard.ts` — new `playUciLine`; added to return contract.
- `frontend/src/components/analysis/EngineLines.tsx` — chevron expand (ChevronDown),
  per-row expand state, restructured row (badge + flex-1 move container + right-pinned
  chevron), new `onMoveClick` signature.
- `frontend/src/pages/Analysis.tsx` — destructure `playUciLine`; pass as `onMoveClick`
  (desktop + mobile); engine CardBody `h-[78px] overflow-y-auto` → `min-h-[78px]`.
- `frontend/src/components/analysis/__tests__/EngineLines.test.tsx` — array signature,
  prefix click, chevron expand / no-chevron tests.
- `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` — `playUciLine` graft +
  child-reuse tests.
- `CHANGELOG.md` — Unreleased Changed bullet.

## Verification

- `npm run lint` — clean (3 pre-existing warnings in `coverage/` artifacts only).
- `npx tsc -b` — clean.
- `npm test -- --run` — full suite green (1222 tests; affected files 31 tests).
- Backend untouched (frontend-only change) — backend gate not applicable.
- Manual UAT (chevron interaction, card growth, sideline grafting) deferred to user.
