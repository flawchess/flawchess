---
phase: 241-codebase-cleanup
plan: 60
subsystem: frontend
tags: [naming, refactor, frontend, hooks, lib]
requires: [241-02, 241-03, 241-04, 241-30, 241-31, 241-33, 241-35, 241-44, 241-46, 241-49, 241-51]
provides: [NEUTRAL_ARROW_COLOR, MAIA_WORKER_PATH, liveEval, followingBestSquares]
affects: [frontend/src/lib/arrowColor.ts, frontend/src/lib/engine/maiaWorkerHost.ts]
key-files:
  modified:
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/hooks/useGameOverlay.ts
    - frontend/src/lib/engine/maiaWorkerHost.ts
    - frontend/src/lib/engine/__tests__/maiaWorkerHost.test.ts
    - frontend/src/lib/engine/__tests__/maiaQueue.test.ts
    - frontend/src/lib/arrowColor.ts
    - frontend/src/lib/arrowColor.test.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/scoreBulletConfig.ts
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-60.tsv
    - .planning/phases/241-codebase-cleanup/ledgers/241-60.txt
    - .planning/phases/241-codebase-cleanup/allow/241-60.tsv
status: complete
commits: 4
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 2e377754cc225b65c158526df30b527b3428492a
actuals:
  tokens: 9000
  tasks: 2
  commits: 4
---

# Phase 241 Plan 60: lib/hook renames Summary

Four INVENTORY section 5 renames applied as printed, one `refactor(naming)` commit each, plus the two arrowColor comment rows (INV-L1298, INV-L1299) deferred here by 241-35. No behavior change.

## Renames

| Old | New | Commit | Files |
|-----|-----|--------|-------|
| `live` (outer binding only) | `liveEval` | 2b7cee066 | useTrainRevealTree.ts (passed as `live: liveEval`; useTreeMoveGrading option and callback-local `live` snapshots unchanged) |
| `blueSquares` | `followingBestSquares` | 3aa9d3805 | useGameOverlay.ts |
| `ENGINE_PATH` | `MAIA_WORKER_PATH` | ad13d4620 | maiaWorkerHost.ts, maiaWorkerHost.test.ts, maiaQueue.test.ts (incl. test titles); comments about the retired Stockfish `ENGINE_PATH` (useStockfishEngine.test.ts, workerPool.test.ts) deliberately untouched |
| `DARK_BLUE` | `NEUTRAL_ARROW_COLOR` | 2e377754c | arrowColor.ts, arrowColor.test.ts, theme.ts, scoreBulletConfig.ts, ChessBoard.tsx, ChessBoard.arrowOpacity.test.ts |

The DARK_BLUE commit also deletes the "Historically blue ... out of scope for now" deferral comment. Value `#6B7280` and `===` equality are unchanged.

## Ledger statuses (ledgers/241-60.txt)

- INV-L1298: APPLIED (arrowColor.ts "blue" to "grey" in the getArrowColor and arrowSortKey docblocks; constant name updated in the header table).
- INV-L1299: APPLIED (scoreBulletConfig.ts "neutral grey band").

## Verification

- `npm run build` (tsc -b + vite), `npm run lint`: clean.
- Targeted vitest (useTrainRevealTree 82, useGameOverlay 12, maiaWorkerHost + maiaQueue 85, arrowColor + board 86) and the frontend source-scan set (131): pass.
- `tests/services/test_opening_insights_arrow_consistency.py`: 3 passed.
- `cleanup.py absent` over rename-maps/241-60.tsv: 0 hits. `cleanup.py diff --plan 241-60`: only the allow-listed `live: liveEval` shorthand expansion remains.

## Deviations from Plan

None - plan executed as written. One environmental note: two runs of the Python source-scan tests hit `database "flawchess_test_gw0" does not exist` errors (the dev Postgres is shared by ~12 parallel executors, which race on the per-session test DB clones); a re-run passed 5/5. Not caused by this plan.

## Known Stubs

None.

## Self-Check: PASSED

All four commits (2b7cee066, 3aa9d3805, ad13d4620, 2e377754c) are ancestors of HEAD; rename-maps/241-60.tsv, ledgers/241-60.txt and allow/241-60.tsv exist.
