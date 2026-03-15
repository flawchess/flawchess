---
phase: quick-25
plan: 01
subsystem: position-bookmarks
tags: [ui, simplification, frontend, backend]
key-files:
  modified:
    - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
    - frontend/src/types/position_bookmarks.ts
    - app/routers/position_bookmarks.py
    - app/schemas/position_bookmarks.py
decisions:
  - "Removed suggested_match_side from PositionSuggestion schema entirely — frontend no longer consumes it, removing it from the API contract is cleaner than keeping dead schema fields"
  - "Added refetchQueries after invalidateQueries to guarantee bookmark list updates immediately when modal closes"
metrics:
  duration: 5min
  completed: 2026-03-15
---

# Quick Task 25: Remove Piece Filter from Suggestion Modal Summary

**One-liner:** Removed Mine/Both piece filter toggle from suggestion modal — all saved suggestions now use match_side 'both' and full_hash as target_hash.

## What Was Done

Simplified the bookmark suggestion modal by removing the per-suggestion Pieces filter (Mine/Both toggle). Users can still change match_side on a saved bookmark card. Also fixed a bookmark list refresh bug where the list did not update immediately after saving suggestions.

## Changes

### SuggestionsModal.tsx
- Removed `MatchSideChoice` type alias
- Removed `matchSideChoices` state and `handleMatchSideChange` function
- Removed `resolveHash` function (was used to pick white/black/full hash based on match_side choice)
- Removed the "Pieces:" row with the ToggleGroup from each suggestion card
- Hardcoded `match_side: 'both'` and `target_hash: suggestion.full_hash` in `handleSave`
- Removed unused imports: `ToggleGroup`, `ToggleGroupItem`, `resolveMatchSide`
- Added `await qc.refetchQueries({ queryKey: ['position-bookmarks'] })` after `invalidateQueries` to ensure bookmark list updates immediately

### frontend/src/types/position_bookmarks.ts
- Removed `suggested_match_side: 'mine' | 'both'` from `PositionSuggestion` interface

### app/schemas/position_bookmarks.py
- Removed `suggested_match_side: str` field from `PositionSuggestion` schema

### app/routers/position_bookmarks.py
- Removed the `suggest_match_side()` repository call (lines 113-123)
- Removed `suggested_match_side` from `PositionSuggestion` constructor call

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 4 files modified as specified
- TypeScript compiles without errors (`npx tsc --noEmit`)
- Python linting passes (`uv run ruff check`)
- Commit 951d5e3 exists
