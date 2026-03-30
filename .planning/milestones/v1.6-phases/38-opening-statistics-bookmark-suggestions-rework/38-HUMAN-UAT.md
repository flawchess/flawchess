---
status: partial
phase: 38-opening-statistics-bookmark-suggestions-rework
source: [38-VERIFICATION.md]
started: 2026-03-29T12:30:00Z
updated: 2026-03-29T12:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Default charts without bookmarks
expected: 3 white + 3 black most-played openings populate Results by Opening and Win Rate Over Time charts
result: [pending]

### 2. Suggestions from most-played
expected: No backend delay when opening suggestions; already-bookmarked positions absent from list
result: [pending]

### 3. Toggle persistence
expected: Chart-enable toggle state persists in localStorage across page reload
result: [pending]

### 4. Delete cleanup
expected: Re-created bookmark defaults to chart-enabled after deleting and re-creating
result: [pending]

### 5. Mobile card layout
expected: Minimap + button row (toggle, load, delete) render correctly at small viewport
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
