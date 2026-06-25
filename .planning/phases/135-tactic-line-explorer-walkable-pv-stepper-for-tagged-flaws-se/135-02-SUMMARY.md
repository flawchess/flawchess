---
phase: 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
plan: "02"
subsystem: frontend
tags: [tactic-explorer, chess-hook, react, typescript, vitest, tdd]
status: complete

dependency_graph:
  requires:
    - 135-01-SUMMARY.md (backend tactic-lines endpoint + TacticLinesResponse schema)
  provides:
    - useTacticLine hook (PV stepper for TacticLineExplorer composition in Plan 03)
    - BoardArrow depth-label support in ChessBoard (id prop + label/labelColor)
  affects:
    - frontend/src/components/board/ChessBoard.tsx (backward-compatible extension)
    - Plan 03 (TacticLineExplorer composes both primitives)

tech_stack:
  added: []
  patterns:
    - TDD (RED/GREEN cycle for useTacticLine)
    - Ref-based stale-closure avoidance (historyRef + currentPlyRef synced via unconditional useEffect)
    - SVG depth-badge overlay mirroring MiniBoard.tsx geometry

key_files:
  created:
    - frontend/src/hooks/useTacticLine.ts
    - frontend/src/hooks/__tests__/useTacticLine.test.tsx
  modified:
    - frontend/src/components/board/ChessBoard.tsx

decisions:
  - TacticDepthOrientation ('missed' | 'allowed') used instead of the broader TacticOrientation which includes 'either'; toDisplayDepthForOrientation cannot handle 'either'
  - Ref sync via unconditional useEffect (not render-phase assignment) to satisfy react-hooks/refs lint rule
  - BoardArrow interface exported (was previously unexported) so Plan 03 can import the type
  - Depth-badge constants re-declared in ChessBoard.tsx matching MiniBoard.tsx values (not imported) to keep files independent; comment notes to keep in sync

metrics:
  duration: "~29 minutes"
  completed: "2026-06-24"
  tasks_completed: 2
  files_changed: 3
---

# Phase 135 Plan 02: Frontend Primitives Summary

useTacticLine hook (PV stepper from custom root FEN with floored depth counter, payoff flag, orientation reset, container-scoped keyboard) and ChessBoard optional id prop + arrow depth-label badges.

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | useTacticLine hook + vitest spec (TDD) | Done | b080648e, 9b5adb51 |
| 2 | ChessBoard optional id prop + arrow depth labels | Done | c73d4e65 |

## What Was Built

### Task 1: useTacticLine hook

New `frontend/src/hooks/useTacticLine.ts` — a PV stepper hook cloned from `useChessGame.ts` with these divergences:
- Starts from `rootFen` (decision position) instead of the chess starting position.
- Accepts `UseTacticLineOptions { moves, rootFen, tacticDepthRaw, orientation }`.
- Depth counter: `Math.max(0, toDisplayDepthForOrientation(tacticDepthRaw, orientation) - currentPly)` — floors at 0, never negative (Pitfall 1 guard).
- `isPayoff = currentPly > tacticDepthRaw` — true once past the punchline move.
- Orientation change resets to ply 0 via `useEffect([moves, rootFen, orientation])`.
- `containerRef` for container-scoped Arrow key navigation (not window-scoped).
- Completely omits: sessionStorage, Zobrist hashing, opening lookup, free-play makeMove, MAX_EXPLORER_PLY.

Vitest spec `frontend/src/hooks/__tests__/useTacticLine.test.tsx` covers 10 behaviors:
1. Initial state (currentPly=0, position==rootFen, lastMove==null)
2. goForward advances ply and sets lastMove
3. goForward at end is a no-op (canGoForward false)
4. goBack retreats; goBack at ply 0 is a no-op
5. goToMove(2) jumps directly
6. displayDepth decrements per ply, floors at 0
7. isPayoff is false at/before punchline, true after
8. reset() returns to ply 0 and rootFen
9. Handles null moves gracefully (empty line)
10. displayDepth never negative on short-PV edge case

### Task 2: ChessBoard optional id prop + arrow depth labels

Modified `frontend/src/components/board/ChessBoard.tsx`:
- `BoardArrow` interface now exported and has optional `label?: string` and `labelColor?: string` fields.
- `ChessBoardProps` has optional `id?: string` (default preserved via `id ?? 'chessboard'` fallback at `react-chessboard` board-id site).
- `ArrowOverlay` renders SVG `<text>` depth-badge on the arrow's target square when `label` is set — mirrors MiniBoard.tsx geometry (`DEPTH_LABEL_FONT=0.55`, `DEPTH_LABEL_CORNER_INSET=0.08`, `DEPTH_LABEL_OUTLINE=0.09`, text anchored to top-right corner).
- All existing callers unchanged (no required prop additions).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TacticOrientation type too broad for useTacticLine**
- **Found during:** tsc -b after Task 2
- **Issue:** `UseTacticLineOptions.orientation` was typed as `TacticOrientation` (includes `'either'`) but `toDisplayDepthForOrientation` only accepts `TacticDepthOrientation` (`'missed' | 'allowed'`). TypeScript error TS2345.
- **Fix:** Changed type to `TacticDepthOrientation` from `@/lib/tacticDepth`. The hook is only ever called with `'missed'` or `'allowed'` (never `'either'`).
- **Files modified:** `frontend/src/hooks/useTacticLine.ts`
- **Commit:** 9b5adb51

**2. [Rule 2 - Missing functionality] Ref-sync approach changed**
- **Found during:** Lint run on useTacticLine.ts
- **Issue:** `react-hooks/refs` lint rule (react-hooks v7.1.1) flags ref value updates during render. The original ref-sync approach (`historyRef.current = history` in render body) triggered 2 lint errors.
- **Fix:** Moved ref sync to an unconditional `useEffect(() => { historyRef.current = ...; currentPlyRef.current = ...; })` (no deps array = runs after every render). This is the React-recommended pattern. The `eslint-disable-next-line` approach was tried first but produced "unused directive" warnings (the rule was not triggered after the move-to-effect refactor).
- **Files modified:** `frontend/src/hooks/useTacticLine.ts`
- **Commit:** 9b5adb51

**3. [Rule 2 - Missing export] BoardArrow interface exported**
- **Found during:** Implementation of Task 2
- **Issue:** `BoardArrow` was a non-exported local interface in `ChessBoard.tsx`. Plan 03 (TacticLineExplorer) will need to import it.
- **Fix:** Added `export` keyword to the `BoardArrow` interface.
- **Files modified:** `frontend/src/components/board/ChessBoard.tsx`
- **Commit:** c73d4e65

## Verification

```
cd frontend && npm test -- --run useTacticLine → 10/10 tests pass
cd frontend && npm run lint                     → 0 errors (3 warnings from coverage/ files, not our code)
cd frontend && npx tsc -b                       → clean (0 errors)
```

## Known Stubs

None — useTacticLine and ChessBoard changes are complete, self-contained primitives with no placeholder values flowing to UI rendering.

## Threat Flags

None — client-only primitives, no new network or trust boundaries.

## Self-Check

### Files exist

- [x] `frontend/src/hooks/useTacticLine.ts` — exists
- [x] `frontend/src/hooks/__tests__/useTacticLine.test.tsx` — exists
- [x] `frontend/src/components/board/ChessBoard.tsx` — modified (exists)

### Commits exist

- [x] b080648e — feat(135-02): useTacticLine hook + vitest spec (TDD green)
- [x] 9b5adb51 — fix(135-02): use TacticDepthOrientation in useTacticLine (not TacticOrientation)
- [x] c73d4e65 — feat(135-02): ChessBoard optional id prop + arrow depth-label badges

## Self-Check: PASSED
