---
status: diagnosed
phase: 10-auto-generate-position-bookmarks-from-most-played-openings
source: 10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md
started: 2026-03-15T12:00:00Z
updated: 2026-03-15T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Suggest Bookmarks Button Visible
expected: On the Dashboard, the Position Bookmarks section shows a "Suggest bookmarks" button with a Sparkles icon in the header. This button is visible even when no bookmarks exist yet.
result: pass

### 2. Suggestions Modal Opens with Position Previews
expected: Clicking the "Suggest bookmarks" button opens a modal dialog. The modal shows positions grouped into White and Black sections. Each suggestion displays a mini chess board preview (~80px), the opening name/ECO code, and a game count badge.
result: issue
reported: "This works, but the suggested bookmarks are almost all already in my bookmark list. Only new positions should be suggested. Use the target_hash to exclude positions which are already included"
severity: major

### 3. Suggestion Match Side Toggles
expected: Each suggestion in the modal has a Mine/Both toggle. The toggle allows switching between "Mine" (match only your pieces) and "Both" (match full position). The default is pre-selected based on a heuristic from the backend.
result: issue
reported: "I noticed the heuristic pieces filter (match_side) is always mine. In many cases, Both would make more sense. We need to check the heuristic. Let's include position which occur at 2 plays minimum"
severity: major

### 4. Bulk Save Suggestions as Bookmarks
expected: Each suggestion has a checkbox for selection. After selecting one or more suggestions, clicking Save creates position bookmarks for the selected suggestions. A progress indicator shows "Saving N of M..." during the save. After saving, the modal closes and the new bookmarks appear in the Position Bookmarks list.
result: pass

### 5. Bookmark Card Shows Mini Board
expected: Each position bookmark card displays a small (~60px) chess board thumbnail showing the bookmarked position. The board respects the is_flipped orientation. On very narrow screens (mobile), the mini board is hidden to save space.
result: issue
reported: "Don't shorten the Opponent option to Opp"
severity: cosmetic

### 6. Bookmark Card Inline Piece Filter Toggle
expected: Each bookmark card has an inline Mine/Opp/Both toggle group for the match_side (piece filter). Changing the toggle updates the match_side via the backend. While updating, the mini board shows subtle opacity feedback. The toggle prevents clearing the selection (re-clicking the active value does nothing).
result: issue
reported: "When I change the piece filter, the card order changes. In the DB, I see sort_order 0 for all cards. When new bookmarks are created, the sort order should be increased and have a distinct value. I noticed that when I drag one bookmark to a different sort order, all sort_order values are set to distinct values in the DB at once."
severity: major

### 7. Suggestions Deduplicate Existing Bookmarks
expected: When opening the suggestions modal, positions that are already saved as bookmarks are excluded from the suggestions list. If all top positions are already bookmarked, the corresponding color section shows an appropriate empty state or fewer suggestions.
result: issue
reported: "The deduplication doesn't work, I see a lot of bookmarks with duplicate hashes. Always suggest 10 new positions with new and unique hashes, which have not been bookmarked yet."
severity: major

## Summary

total: 7
passed: 2
issues: 5
pending: 0
skipped: 0

## Gaps

- truth: "Suggestions should exclude positions already bookmarked"
  status: failed
  reason: "User reported: This works, but the suggested bookmarks are almost all already in my bookmark list. Only new positions should be suggested. Use the target_hash to exclude positions which are already included"
  severity: major
  test: 2
  root_cause: "get_existing_full_hashes() recomputes full_hash from FEN via compute_hashes(), ignoring bookmark's actual target_hash column. For match_side=mine bookmarks, target_hash is white_hash/black_hash (not full_hash), so the exclusion set misses them entirely."
  artifacts:
    - path: "app/repositories/position_bookmark_repository.py"
      issue: "get_existing_full_hashes() uses wrong hash source for exclusion"
    - path: "app/routers/position_bookmarks.py"
      issue: "get_suggestions() passes wrong exclusion set"
  missing:
    - "Read target_hash directly from bookmarks instead of recomputing full_hash from FEN"
  debug_session: ".planning/debug/suggestions-dedup-and-duplicates.md"

- truth: "Match side heuristic should suggest Both when appropriate, not always Mine"
  status: failed
  reason: "User reported: I noticed the heuristic pieces filter (match_side) is always mine. In many cases, Both would make more sense. We need to check the heuristic. Let's include position which occur at 2 plays minimum"
  severity: major
  test: 3
  root_cause: "suggest_match_side ratio (distinct_full_hashes / distinct_games) is structurally ~1.0 for opening positions, making the 1.5 threshold unreachable. Each game contributes ~1 distinct full_hash per white_hash at a given ply, so ratio stays near 1.0."
  artifacts:
    - path: "app/repositories/position_bookmark_repository.py"
      issue: "suggest_match_side ratio calculation is structurally flawed; threshold 1.5 unreachable"
  missing:
    - "Compare game count at two granularities: my-hash-only vs full-hash. If my_hash_count / full_hash_count > 2.0, suggest mine; otherwise suggest both"
    - "Add minimum 2 plays filter to get_top_positions_for_color"
  debug_session: ".planning/debug/match-side-always-mine.md"

- truth: "Opponent label should not be shortened to Opp"
  status: failed
  reason: "User reported: Don't shorten the Opponent option to Opp"
  severity: cosmetic
  test: 5
  root_cause: "PositionBookmarkCard.tsx line 151 uses 'Opp' as ToggleGroupItem text instead of 'Opponent'"
  artifacts:
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx"
      issue: "Line 151: 'Opp' should be 'Opponent'"
  missing:
    - "Change text from 'Opp' to 'Opponent'"
  debug_session: ""

- truth: "Bookmark sort_order should have distinct values on creation"
  status: failed
  reason: "User reported: When I change the piece filter, the card order changes. In the DB, I see sort_order 0 for all cards. When new bookmarks are created, the sort order should be increased and have a distinct value."
  severity: major
  test: 6
  root_cause: "create_bookmark() in position_bookmark_repository.py line 57 hardcodes sort_order=0 for every new bookmark. No logic exists to compute MAX(sort_order)+1."
  artifacts:
    - path: "app/repositories/position_bookmark_repository.py"
      issue: "Line 57: hardcoded sort_order=0 in create_bookmark()"
  missing:
    - "Query MAX(sort_order)+1 for user's bookmarks before creating new bookmark"
  debug_session: ".planning/debug/sort-order-always-zero.md"

- truth: "Suggestions should always return 10 new unique positions not already bookmarked"
  status: failed
  reason: "User reported: The deduplication doesn't work, I see a lot of bookmarks with duplicate hashes. Always suggest 10 new positions with new and unique hashes, which have not been bookmarked yet."
  severity: major
  test: 7
  root_cause: "get_top_positions_for_color() groups by (white_hash, black_hash, full_hash). Same white_hash can appear with different black_hash values. When match_side=mine, all produce same target_hash. No post-grouping deduplication by target hash."
  artifacts:
    - path: "app/repositories/position_bookmark_repository.py"
      issue: "get_top_positions_for_color() lacks deduplication by target hash"
  missing:
    - "Deduplicate results by the hash that will become target_hash for the given color/match_side"
    - "Always return exactly 10 unique suggestions (over-fetch and filter)"
  debug_session: ".planning/debug/suggestions-dedup-and-duplicates.md"
