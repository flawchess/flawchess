---
quick_id: 260709-k9r
title: Fix FlawChess Engine card mate eval and stale Stockfish prompt on forced-mate lines
date: 2026-07-09
status: complete
---

# Summary — 260709-k9r

Fixed both forced-mate rendering bugs on the FlawChess Engine card, which shared
one root cause: `RankedLine`/the search node kept only `objectiveEvalCp` and
dropped `MoveGrade.evalMate`, so a mate leaf (`{evalCp: null, evalMate: -4}`)
surfaced as `null`.

## Changes

- **Data contract** (`lib/engine/types.ts`, `treeCommon.ts`): added
  `objectiveEvalMate` to `RankedLine` + `ModalPlyStat`; carried it on the tree
  node and through `buildModalPath` / `buildRankedLines`.
- **Both search runners** (`mctsSearch.ts`, `fallbackExpectimax.ts`): pass
  `grade?.evalMate ?? null` symmetrically (child + root nodes).
- **Display** (`FlawChessEngineLines.tsx`): objective badge + chip-preview eval now
  `formatScore(objectiveEvalCp, objectiveEvalMate)` → `#-4` instead of `…`. The gold
  **practical** badge, a probability that saturates to a useless `-10.0` cap on a
  forced mate, also borrows the objective mate distance → `#-N` (follow-up per user
  request: option A — both badges show the mate).
- **Terminal positions** (`FlawChessEngineLines.tsx` + `Analysis.tsx`): a
  checkmated/drawn root has no legal moves, so the engine ranks nothing and the
  card previously sat blank with a misleading "Turn on Stockfish to compare picks."
  prompt. The card now renders a single terminal row — a gold `#0` badge for
  checkmate, `½–½` for a draw — driven by the existing `terminalPositionEval`, and
  the agreement verdict is hidden in a terminal position (nothing to compare).
- **Verdict** (`lib/flawChessVerdict.ts`): bails only when BOTH cp and mate are
  null; sets `flawChessMove.evalMate`; feeds mate into `evalToExpectedScore`;
  nulls the cp gap when the FC side is a mate.
- **Reconciliation** (`pages/Analysis.tsx`): `reconciledRankedLines` pulls both
  `evalCp` and `evalMate` from the same resolved lookup grade.
- **Tests**: added verdict mate-classification cases + a card `#-4` render test;
  threaded `objectiveEvalMate` through fixtures in 4 test files.

No search-logic/ranking behavior changed — the practical value/backup already
handled mate via `terminalValue`/`leafExpectedScore`. This only surfaces the
objective mate Stockfish already computes.

## Verification

- `npx tsc -b` clean; `npm run lint` (only pre-existing `coverage/` warnings);
  `npm test` → 1638 passed.
- Chrome plugin at `/analysis?game_id=687512&ply=63`: card badge shows `#-4`;
  verdict reads "FlawChess and Stockfish agree on Qxc1 — objectively #-4, and the
  practical pick too." Both bugs confirmed fixed against the live app.

## Files touched

- frontend/src/lib/engine/types.ts
- frontend/src/lib/engine/treeCommon.ts
- frontend/src/lib/engine/mctsSearch.ts
- frontend/src/lib/engine/fallbackExpectimax.ts
- frontend/src/components/analysis/FlawChessEngineLines.tsx
- frontend/src/lib/flawChessVerdict.ts
- frontend/src/pages/Analysis.tsx
- frontend/src/lib/flawChessVerdict.test.ts
- frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx
- frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx
- frontend/src/pages/__tests__/Analysis.test.tsx
- frontend/src/hooks/__tests__/useFlawChessEngine.test.ts
