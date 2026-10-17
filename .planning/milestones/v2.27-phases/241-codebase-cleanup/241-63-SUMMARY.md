---
phase: 241-codebase-cleanup
plan: 63
subsystem: frontend
tags: [naming, refactor, position-bookmarks, import, navigation]
requires: [241-02, 241-03, 241-04, 241-41, 241-44, 241-45, 241-50, 241-51]
provides:
  - hasNoSuggestions, saveButtonLabel (SuggestionsModal.tsx)
  - skipBlurSaveRef (PositionBookmarkCard.tsx)
  - BookmarkMiniBoard, BookmarkMiniBoardProps (position-bookmarks/BookmarkMiniBoard.tsx)
  - importedGameCount (LibraryPage.tsx, App.tsx)
  - ACTIVE_IMPORT_REFRESH_INTERVAL_MS (Import.tsx)
key-files:
  modified:
    - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
    - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
    - frontend/src/pages/library/LibraryPage.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/pages/Import.tsx
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-63.tsv
  renamed:
    - frontend/src/components/position-bookmarks/MiniBoard.tsx -> BookmarkMiniBoard.tsx
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: d3e8278512bf2971335dcef44b0ab0d86eca460e
actuals:
  tokens: 3000
  tasks: 3
  commits: 6
---

# Phase 241 Plan 63: Bookmark, imported-game-count and import-interval renames Summary

Six INVENTORY section 5 renames applied as printed, one `refactor(naming)` commit each, with scoped rows in `rename-maps/241-63.tsv`. Renames only, no behavior change.

## Renames

| # | Old -> New | Commit | Files |
|---|-----------|--------|-------|
| a | `allSuggestions` -> `hasNoSuggestions` | 38c9f157b | SuggestionsModal.tsx |
| b | `savingLabel` -> `saveButtonLabel` | 95235494e | SuggestionsModal.tsx |
| c | `isDirtyRef` -> `skipBlurSaveRef` | b3d64aea4 | PositionBookmarkCard.tsx |
| d | position-bookmarks `MiniBoard` -> `BookmarkMiniBoard` (file, component, `BookmarkMiniBoardProps`, imports, test `vi.mock` path and factory key) | 17a979fe3 | BookmarkMiniBoard.tsx (git mv), SuggestionsModal.tsx, PositionBookmarkCard.tsx, PositionBookmarkCard.tracking.test.tsx |
| e | `totalGames` -> `importedGameCount` (D-09, one commit) | 05cba4049 | LibraryPage.tsx, App.tsx (both sum expressions), App.test.tsx comment |
| f | `GAME_COUNT_REFRESH_INTERVAL_MS` -> `ACTIVE_IMPORT_REFRESH_INTERVAL_MS` | d3e827851 | Import.tsx |

Untouched by design: `components/board/MiniBoard.tsx`, testid `mini-board`, `GamesTab.tsx` / `FlawsTab.tsx` / other `totalGames` (different quantities).

## Verification

- `tsc -b` / `npm run build`, `npm run lint`, `npm run knip` clean (knip prints only two pre-existing configuration hints).
- Tests: position-bookmarks + board (73 passed), App.test + pages/library (103 passed), all pages (271 passed), `source_scan_tests.sh` (131 passed, includes Import source-reading tests).
- `cleanup.py absent --map rename-maps/241-63.tsv`: 0 hits. `cleanup.py diff --plan 241-63` per task: only canonicalized names differ.
- Baseline gates run on the untouched tree in the fresh worktree (`npm ci`, `uv sync --group maia-inference`) were green.

## Deviations from Plan

None - plan executed exactly as written. The `MiniBoardProps` token needed its own rename-map row (the rule matcher is whole-word), added alongside the `MiniBoard` row.

## Threat model

T-241-88 (nav gating): App.tsx diff is name-only; the expression `chess_com_game_count + lichess_game_count` and `importedGameCount > 0 && tier1` are unchanged; App tests pass. T-241-89: rows are canon-scoped to position-bookmarks/; board tests pass.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: frontend/src/components/position-bookmarks/BookmarkMiniBoard.tsx
- FOUND: .planning/phases/241-codebase-cleanup/rename-maps/241-63.tsv
- FOUND commits: 38c9f157b, 95235494e, b3d64aea4, 17a979fe3, 05cba4049, d3e827851
