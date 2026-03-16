---
phase: 13-frontend-move-explorer-component
verified: 2026-03-16T22:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 13: Frontend Move Explorer Component — Verification Report

**Phase Goal:** Build the MoveExplorer React component — a 3-column table showing next moves from the current board position with WDL bars, transposition indicators, and frequency arrows on the board.
**Verified:** 2026-03-16T22:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                      | Status     | Evidence                                                                                     |
|----|--------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | NextMovesRequest, NextMoveEntry, NextMovesResponse types exist and mirror backend schemas  | VERIFIED   | All three interfaces present in `frontend/src/types/api.ts` lines 92–120, matching backend Pydantic schemas exactly |
| 2  | useNextMoves hook auto-fetches POST /analysis/next-moves on hash or filter change          | VERIFIED   | `useNextMoves.ts` calls `apiClient.post('/analysis/next-moves', ...)`, queryKey includes hash string + filter object; no `enabled` gate |
| 3  | WDL color constants are exported from WDLBar.tsx for reuse                                 | VERIFIED   | Lines 4–6 of `WDLBar.tsx`: `export const WDL_WIN`, `export const WDL_DRAW`, `export const WDL_LOSS` |
| 4  | ChessBoard accepts an arrows prop and renders arrows with clearArrowsOnPositionChange disabled | VERIFIED | `ChessBoard.tsx` lines 17, 111–112: `arrows?: BoardArrow[]` prop, `arrows: arrows` and `clearArrowsOnPositionChange: false` in options |
| 5  | shadcn tooltip component is installed and available                                        | VERIFIED   | `frontend/src/components/ui/tooltip.tsx` exports `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider` |
| 6  | Move Explorer table shows 3 columns: Move, Games, Results with mini WDL bar               | VERIFIED   | `MoveExplorer.tsx` table has 3 `<th>` (Move, Games, Results), each row renders mini WDL bar via `WDL_WIN/WDL_DRAW/WDL_LOSS` colored divs |
| 7  | Rows are ordered by game_count descending (most-played first)                              | VERIFIED   | Frontend renders API response order; hook sends no `sort_by` param so backend default `"frequency"` applies; backend route confirmed at `POST /analysis/next-moves` |
| 8  | Clicking a move row advances the board to resulting position and explorer refreshes        | VERIFIED   | `handleRowClick` resolves SAN to from/to via chess.js `useMemo` moveMap, calls `onMoveClick(from, to)` → `chess.makeMove`; hash change triggers `useNextMoves` re-fetch via queryKey |
| 9  | Transposition icon appears when transposition_count > game_count with hover tooltip        | VERIFIED   | Lines 94–107: condition `entry.transposition_count > entry.game_count` renders `ArrowLeftRight` icon wrapped in `TooltipProvider/Tooltip`; tooltip text "via other move orders" present at line 103 |
| 10 | Board displays blue arrows for all next moves with opacity proportional to frequency       | VERIFIED   | `Dashboard.tsx` lines 69–101: `boardArrows` useMemo computes `#1d6ab1${alpha}` color with `MIN_OPACITY + (1 - MIN_OPACITY) * (count / maxCount)` formula; passed as `arrows={boardArrows}` to ChessBoard |
| 11 | Explorer shows empty state when no moves available for current position                    | VERIFIED   | `MoveExplorer.tsx` lines 60–66: `moves.length === 0` renders `data-testid="move-explorer-empty"` with "No moves found" heading |
| 12 | Explorer is always visible (not gated by positionFilterActive)                             | VERIFIED   | `Dashboard.tsx` lines 495–502: `<MoveExplorer .../>` rendered unconditionally before the `positionFilterActive` conditional block; grep confirms no gating |

**Score:** 12/12 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact                                            | Expected                                        | Status     | Details                                                                |
|-----------------------------------------------------|-------------------------------------------------|------------|------------------------------------------------------------------------|
| `frontend/src/types/api.ts`                         | NextMovesRequest, NextMoveEntry, NextMovesResponse types | VERIFIED | All three interfaces present, lines 92–120; `NextMoveEntry` includes `transposition_count: number` |
| `frontend/src/hooks/useNextMoves.ts`                | TanStack useQuery hook for next-moves endpoint  | VERIFIED   | 34 lines, exports `useNextMoves`, uses `useQuery<NextMovesResponse>`, calls `apiClient.post` |
| `frontend/src/components/results/WDLBar.tsx`        | Exported WDL color constants                    | VERIFIED   | `export const WDL_WIN`, `WDL_DRAW`, `WDL_LOSS` at lines 4–6          |
| `frontend/src/components/board/ChessBoard.tsx`      | ChessBoard with arrows prop support             | VERIFIED   | `BoardArrow` interface, `arrows?: BoardArrow[]` prop, `clearArrowsOnPositionChange: false` |
| `frontend/src/components/ui/tooltip.tsx`            | shadcn Tooltip component                        | VERIFIED   | Exports `Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger` |

### Plan 02 Artifacts

| Artifact                                                  | Expected                                               | Status     | Details                                            |
|-----------------------------------------------------------|--------------------------------------------------------|------------|----------------------------------------------------|
| `frontend/src/components/move-explorer/MoveExplorer.tsx`  | Move Explorer table with mini WDL bars, transposition icons | VERIFIED | 138 lines (above 80-line minimum); all required data-testid attributes present |
| `frontend/src/pages/Dashboard.tsx`                        | Dashboard integration with MoveExplorer and board arrows | VERIFIED  | Imports `MoveExplorer`, calls `useNextMoves`, computes `boardArrows`, passes `arrows={boardArrows}` to ChessBoard |

---

## Key Link Verification

### Plan 01 Key Links

| From                        | To                              | Via                       | Status     | Details                                                     |
|-----------------------------|---------------------------------|---------------------------|------------|-------------------------------------------------------------|
| `useNextMoves.ts`           | `/analysis/next-moves`          | `apiClient.post`          | WIRED      | Line 22: `await apiClient.post<NextMovesResponse>('/analysis/next-moves', ...)` |
| `useNextMoves.ts`           | `frontend/src/types/api.ts`     | `import NextMovesResponse` | WIRED     | Line 3: `import type { NextMovesResponse } from '@/types/api'` |

### Plan 02 Key Links

| From                  | To                              | Via                        | Status   | Details                                                   |
|-----------------------|---------------------------------|----------------------------|----------|-----------------------------------------------------------|
| `Dashboard.tsx`       | `useNextMoves.ts`               | `useNextMoves` hook call   | WIRED    | Line 19 import + line 65: `const nextMoves = useNextMoves(chess.hashes.fullHash, filters)` |
| `Dashboard.tsx`       | `MoveExplorer.tsx`              | `<MoveExplorer` render     | WIRED    | Line 27 import + lines 495–502: `<MoveExplorer moves={...} .../>` |
| `Dashboard.tsx`       | `ChessBoard.tsx`                | `arrows=` prop             | WIRED    | Line 324: `arrows={boardArrows}` on `<ChessBoard>` element |
| `MoveExplorer.tsx`    | `WDLBar.tsx`                    | WDL color constants import | WIRED    | Line 4: `import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar'` |

---

## Requirements Coverage

| Requirement | Source Plan | Description                                                                                                    | Status       | Evidence                                                                                     |
|-------------|-------------|----------------------------------------------------------------------------------------------------------------|--------------|----------------------------------------------------------------------------------------------|
| MEXP-06     | 13-01, 13-02 | Move Explorer tab displays a 3-column table (Move, Games, Results) with a W/D/L stacked bar in the Results column | SATISFIED  | `MoveExplorer.tsx`: 3-column table with `<th>` headers Move/Games/Results; mini WDL bar via inline divs using `WDL_WIN/WDL_DRAW/WDL_LOSS` colors |
| MEXP-07     | 13-02        | Clicking a move row advances the board to the resulting position and refreshes the explorer with the new position's next moves | SATISFIED | `handleRowClick` → `onMoveClick(from, to)` → `chess.makeMove`; hash change invalidates `useNextMoves` queryKey and triggers refetch |
| MEXP-11     | 13-02        | Move Explorer shows a transposition warning icon with hover tooltip when the resulting position has been reached through other move orders | SATISFIED | Condition `transposition_count > game_count` renders `ArrowLeftRight` in `TooltipTrigger`; `TooltipContent` shows "via other move orders" text |
| MEXP-12     | 13-01, 13-02 | Chessboard displays transparent arrows for all next moves from the current position, with opacity proportional to move frequency | SATISFIED | `boardArrows` useMemo in Dashboard: `#1d6ab1` + hex alpha via `MIN_OPACITY + (1 - MIN_OPACITY) * (count / maxCount)`; passed to `<ChessBoard arrows={boardArrows}>` with `clearArrowsOnPositionChange: false` |

No orphaned requirements found — all four requirement IDs (MEXP-06, MEXP-07, MEXP-11, MEXP-12) are claimed and implemented.

---

## Anti-Patterns Found

No anti-patterns detected in modified files.

| File                                | Pattern Checked                     | Result  |
|-------------------------------------|-------------------------------------|---------|
| `MoveExplorer.tsx`                  | TODO/FIXME/placeholder comments     | Clean   |
| `MoveExplorer.tsx`                  | Empty implementations               | Clean   |
| `Dashboard.tsx`                     | TODO/FIXME/placeholder comments     | Clean   |
| `Dashboard.tsx`                     | match_side in next-moves request    | Clean (not present) |
| `useNextMoves.ts`                   | match_side/matchSide/offset/limit   | Clean (none present) |
| `ChessBoard.tsx`                    | clearArrowsOnPositionChange missing | Clean (set to false) |

---

## Human Verification Required

The following behaviors require browser testing and cannot be verified programmatically:

### 1. MEXP-07 — Click-to-navigate move rows

**Test:** Load the dashboard with imported games. Click a move row (e.g., "e4") in the Move Explorer.
**Expected:** The board advances to show that move played. The Move Explorer table refreshes with the next position's moves automatically.
**Why human:** React state updates and real API fetch on hash change require a running browser environment.

### 2. MEXP-11 — Transposition indicator visibility

**Test:** Navigate to a position known to be reachable via multiple move orders. Look for the ArrowLeftRight icon next to the game count in a move row. Hover over it.
**Expected:** Tooltip appears reading "Position reached in X total games (Y via other move orders)".
**Why human:** Transposition data depends on actual imported game database; tooltip render requires mouse interaction.

### 3. MEXP-12 — Arrow opacity proportional to frequency

**Test:** Verify the board shows blue arrows for all next moves. Compare arrows for moves with very different game counts.
**Expected:** Most-played move has the darkest arrow; less-played moves have lighter arrows. Hovering a move row should highlight its arrow (darker `#0a3d6b` color is implemented for hovered move).
**Why human:** Visual opacity comparison requires human judgment; hover state requires mouse interaction.

### 4. Empty state messaging

**Test:** Navigate to a deep position with no recorded games.
**Expected:** "No moves found" message appears in the Move Explorer panel.
**Why human:** Requires games data (or lack thereof) in the actual database.

---

## TypeScript Compilation

`npx tsc --noEmit` exits 0 — no type errors across the entire frontend codebase.

---

## Summary

Phase 13 goal is fully achieved. All five Plan 01 building blocks (types, hook, WDL color exports, ChessBoard arrows prop, shadcn tooltip) exist and are substantive and wired. The Plan 02 MoveExplorer component (138 lines) renders the 3-column table with mini WDL bars, transposition indicators with tooltips, loading/error/empty states, keyboard navigation, and 44px touch targets per CLAUDE.md requirements. Dashboard integration is complete: `useNextMoves` is called unconditionally, `boardArrows` are computed with frequency-proportional opacity, and `<MoveExplorer>` is placed before the `positionFilterActive` block (always visible). All four requirement IDs (MEXP-06, MEXP-07, MEXP-11, MEXP-12) are satisfied.

Four items require human browser verification (visual appearance, real data interaction, hover tooltips) but no blocking gaps were found in the static analysis.

---

_Verified: 2026-03-16T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
