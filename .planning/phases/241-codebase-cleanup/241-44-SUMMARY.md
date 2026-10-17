---
phase: 241-codebase-cleanup
plan: 44
subsystem: frontend
tags: [cleanup, comments, typescript, app-shell, board, move-explorer]

requires:
  - phase: 241-04
    provides: "cleanup.py TypeScript/JSX support (scan, token diff) and the FE loop"
provides:
  - "App.tsx, MoveExplorer.tsx and the board components free of planning tags and review ids"
  - "ledgers/241-44.txt: status of all 35 INVENTORY section 6 rows in these files"
affects: [241-60, 241-63]

actuals:
  tokens: 30000
  tasks: 2
  commits: 2
plan_head_before: ad89a557fee9dcef9abec37de55a826771f39416
plan_head_after: 3a5fc6138357c52fa169e9c63907758fec911bd3

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-44.txt
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/move-explorer/MoveExplorer.tsx
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/components/board/boardSize.ts
    - frontend/src/components/board/boardMarkers.tsx
    - frontend/src/components/board/PlayerBar.tsx
    - frontend/src/components/board/MiniBoard.tsx
    - frontend/src/components/board/arrowGeometry.ts
    - frontend/src/components/board/MaterialDisplay.tsx
    - frontend/src/components/board/HorizontalMoveList.tsx

key-decisions:
  - "All edits were hand-written (no codemod run): the tag shapes in these files were nearly all embedded in multi-line narration that needed rewriting, not the two safe codemod shapes"
  - "INV-L1128 kept the 'don't gate animation on ontouchstart' rule and the coarse-pointer fallback; the history (Phase 19, real-phone verification dates, react-chessboard release survey) was dropped"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 45min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 44: App, Move Explorer and Board Comment Cleanup Summary

**All planning tags, review ids (WR-07, CR-01, WR-04), quick-task ids and UAT narration are gone from the comments of App.tsx, MoveExplorer.tsx and the 9 tagged board components, with 35 inventoried rows applied and an empty non-comment token diff.**

## Accomplishments

- Task 1: App.tsx (about 60 tagged comment lines, including JSX comments) and MoveExplorer.tsx (7 lines). The `NavHeader` banner and "Exported so App.test.tsx..." comment moved directly above `export function NavHeader()`; IMPORT_EXEMPT_ROUTES gained the `/train` bullet and the WR-07 narration became the rule "don't copy this check into a surface"; the NAV_ITEMS pointer now says `IMPORT_EXEMPT_ROUTES`.
- Task 2: ChessBoard.tsx, BoardControls.tsx, boardSize.ts, boardMarkers.tsx, PlayerBar.tsx, MiniBoard.tsx, arrowGeometry.ts, MaterialDisplay.tsx, HorizontalMoveList.tsx. The ChessBoard `showAnimations` docblock is now the rule plus the coarse-pointer fallback, and the commented-out revert block is deleted. MoveList.tsx and LazyMiniBoard.tsx were scanned clean and left untouched.
- Ledger: 35 rows, 31 APPLIED, 4 MOVED (INV-L1062, L1124, L1135, L1128), 0 SKIPPED, 0 LEFT, 0 DEFERRED. Every row was re-verified against the code first (D-10); the evidence is on each ledger line.

## Task Commits

1. **Task 1: App.tsx and MoveExplorer.tsx** - `b091399ec` (`chore(comments): frontend App and MoveExplorer`)
2. **Task 2: board components** - `3a5fc6138` (`chore(comments): frontend board components`)

`commits: 2` is measured with `git rev-list --count ad89a557f..HEAD` before this SUMMARY commit.

## Verification (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-44.txt` | exit 0 (13 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-44.txt` | exit 0 (13 selected, 11 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-44.txt --ledger ledgers/241-44.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| source_scan_tests.sh python half (run serially, no `-n 4`) | 95 passed + 5 passed |
| `npm --prefix frontend test -- --run src/App.test.tsx src/components/board src/pages/__tests__/Analysis.test.tsx` | 12 files / 246 tests passed |
| `npm --prefix frontend test -- src/components/move-explorer` | 30 passed (the `bg-foreground/10!` source-count test still holds: the two code uses remain, the comment mention carries no `!`) |

Environmental: the python half of `source_scan_tests.sh` was run without `-n 4` because sibling executors share the dev Postgres.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the gates.

**2. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- App.tsx: dropped "UNLINKED from nav this phase" (the nav links `/bots`); "Growth item 16:", "Bug fix (quick 260611)" and "(Phase 62)" provenance prefixes removed (the scan regex misses the first two shapes); the `useReminderResurfaceRedirect` comment lost the `_reject_guest` 403 history but keeps why the gate stays.
- ChessBoard.tsx: the `animationDurationInMs` doc said "on touch devices animations are off entirely"; the code enables animation everywhere except vitest, so the doc now says that (same stale claim as INV-L1072). The `heightRef` docs and `BoardArrow` docs lost "exactly as today" phrasing.
- boardSize.ts: dropped the per-caller maxWidth list (Bots 400, Train 600) as unverifiable drift risk; `BOARD_EVAL_BARS_ALLOWANCE_PX`, `EVAL_SLIDER_SLACK_PX` and `DESKTOP_BOARD_SIZE_REDUCTION_PX` docs lost "Hoisted here (215 code review WR-04)" and keep the reason they are shared.
- boardMarkers.tsx: "UI-SPEC: no new geometry constant" removed (UI-SPEC is not in the scan regex).
- MiniBoard.tsx: three "(item 4/5)" pointers removed.

**Total deviations:** 1 blocking env prep, 1 group of wording fixes; none touch code, testids, Umami names, storage keys or URLs. The token diff is empty.

## Ledger notes

- INV-L1070: the primary (ChessBoard.tsx) clause is a real ledger line; the index.css clause was applied by 241-04 as a `#` line in its own ledger. No `#` lines were added to ledgers/241-44.txt.

## Issues Encountered

- zsh does not word-split `$VAR`, so a for-loop over command strings failed on the first try; rerun with explicit commands.
- `Read`-before-`Edit` constraint required switching to scripted exact-string replacements for the larger blocks; each replacement asserted a single match.

## Known Stubs

None.

## Threat Flags

None. Comment-only change; `cleanup.py diff` compared every non-comment token of App.tsx (T-241-61) and found none changed.

## Self-Check: PASSED

Files verified present: ledgers/241-44.txt and the 11 edited frontend files. Commits `b091399ec` and `3a5fc6138` are ancestors of HEAD.
