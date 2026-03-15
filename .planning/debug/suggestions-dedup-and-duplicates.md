---
status: diagnosed
trigger: "Suggestions modal shows already-bookmarked positions (Test 2) and contains duplicate hashes (Test 7)"
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: Two root causes identified - see Resolution
test: n/a
expecting: n/a
next_action: return diagnosis

## Symptoms

expected: Suggestions should exclude already-bookmarked positions using target_hash and return unique hashes
actual: (1) Already-bookmarked positions appear in suggestions. (2) Duplicate hashes in suggestion results.
errors: Test 2 and Test 7 failures
reproduction: Run suggestion query with existing bookmarks that have match_side != "both"
started: Current implementation

## Eliminated

(none needed - root causes identified on first analysis)

## Evidence

- timestamp: 2026-03-15
  checked: get_existing_full_hashes() implementation (lines 131-151 of position_bookmark_repository.py)
  found: Function recomputes full_hash from FEN via compute_hashes() instead of reading target_hash directly from the bookmark. This means exclusion always uses full_hash regardless of the bookmark's match_side.
  implication: When a bookmark has match_side="mine", its target_hash is white_hash or black_hash (not full_hash). The exclusion set contains full_hash (recomputed), but the suggestion query groups by (white_hash, black_hash, full_hash) and filters on full_hash. The full_hash will match if a bookmark was created with match_side="both", but the real problem is conceptual mismatch -- see root cause.

- timestamp: 2026-03-15
  checked: get_top_positions_for_color() implementation (lines 154-202)
  found: Groups by (white_hash, black_hash, full_hash) and post-filters on full_hash. No deduplication by any single hash column -- if the same white_hash appears with different full_hashes, they are treated as separate rows.
  implication: Issue 2 (duplicate hashes) stems from this grouping. Multiple rows can share the same white_hash or black_hash but differ in full_hash, producing "duplicates" from the perspective of the match_side hash.

- timestamp: 2026-03-15
  checked: How target_hash is determined (update_match_side lines 239-270, PositionBookmarkCreate schema)
  found: target_hash depends on match_side and color. "mine" -> white_hash (for white) or black_hash (for black). "both" -> full_hash. "opponent" -> opposite side hash.
  implication: The exclusion mechanism must use target_hash directly, not recompute full_hash.

- timestamp: 2026-03-15
  checked: Suggestion endpoint in router (lines 37-137 of position_bookmarks.py)
  found: Calls get_existing_full_hashes() which returns full_hashes, then passes them to get_top_positions_for_color() as exclude_full_hashes. The exclusion always operates on full_hash column regardless of bookmark match_side.
  implication: A bookmark with match_side="mine" and target_hash=white_hash will NOT be excluded because exclusion checks full_hash, not the hash that was actually bookmarked.

## Resolution

root_cause: |
  **Issue 1 (already-bookmarked positions not excluded):**
  `get_existing_full_hashes()` recomputes full_hash from FEN via `compute_hashes()` instead of reading the bookmark's `target_hash` column directly. This means the exclusion set always contains full_hashes. However, when a bookmark was created with match_side="mine", its target_hash is a white_hash or black_hash -- not a full_hash. The recomputed full_hash happens to work for "both" bookmarks but fails for "mine" or "opponent" bookmarks because the exclusion compares the wrong hash type.

  More fundamentally: the exclusion in `get_top_positions_for_color()` filters on `row.full_hash in exclude_full_hashes` (line 196). Even if `get_existing_full_hashes()` returned target_hashes, the comparison would still be against full_hash column. The fix needs to use target_hash from bookmarks AND compare against the appropriate hash column (not always full_hash).

  **Issue 2 (duplicate hashes in suggestions):**
  `get_top_positions_for_color()` groups by `(white_hash, black_hash, full_hash)` -- a 3-column composite group. The same white_hash can appear in multiple rows if paired with different black_hashes (different opponent responses). From the user's perspective these are "duplicate" positions when match_side="mine" because they share the same target_hash (white_hash for white). The function has no deduplication by the hash that will become the bookmark's target_hash. It returns multiple entries that would all produce the same bookmark.

fix: (not applied - diagnosis only)
verification: (not applied - diagnosis only)
files_changed: []
