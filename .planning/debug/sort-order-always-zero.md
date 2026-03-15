---
status: diagnosed
trigger: "new position bookmarks are all created with sort_order=0 instead of distinct incremented values"
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: create_bookmark hardcodes sort_order=0 without querying max existing sort_order
test: read create_bookmark function
expecting: no logic to compute next sort_order
next_action: return diagnosis

## Symptoms

expected: Each new bookmark gets a distinct, incrementing sort_order so card order is stable
actual: All new bookmarks get sort_order=0, causing reordering when piece filter changes
errors: none (functional bug, not crash)
reproduction: Create multiple bookmarks (single or bulk via suggestions), inspect DB sort_order values
started: Since initial implementation

## Eliminated

(none needed - root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-15T00:00:00Z
  checked: app/repositories/position_bookmark_repository.py line 57
  found: create_bookmark() hardcodes `sort_order=0` with no logic to compute next value
  implication: Every bookmark created gets sort_order=0 regardless of existing bookmarks

- timestamp: 2026-03-15T00:00:00Z
  checked: app/routers/position_bookmarks.py POST endpoint (line 150-158)
  found: Router calls create_bookmark directly, no sort_order computation at router level either
  implication: Neither layer computes the next sort_order

- timestamp: 2026-03-15T00:00:00Z
  checked: app/schemas/position_bookmarks.py PositionBookmarkCreate schema
  found: Schema has no sort_order field - it is not accepted from the client
  implication: sort_order must be computed server-side, but no code does this

- timestamp: 2026-03-15T00:00:00Z
  checked: reorder_bookmarks function (line 103-128)
  found: reorder_bookmarks correctly assigns sort_order 0..N-1, confirming drag-reorder works
  implication: The reorder path works; only the creation path is broken

- timestamp: 2026-03-15T00:00:00Z
  checked: SuggestionsModal.tsx handleSave (line 92-126)
  found: Bulk save calls positionBookmarksApi.create() sequentially in a loop, no reorder call after
  implication: Each bulk-saved bookmark also gets sort_order=0; no post-save reorder fixes it

## Resolution

root_cause: `create_bookmark()` in position_bookmark_repository.py (line 57) hardcodes `sort_order=0`. It should query `SELECT MAX(sort_order) FROM position_bookmarks WHERE user_id = :uid` and set `sort_order = max_value + 1` (or 0 if no bookmarks exist). Neither the repository, router, nor frontend computes the next sort_order value.
fix: (not applied - diagnosis only)
verification: (not applied - diagnosis only)
files_changed: []
