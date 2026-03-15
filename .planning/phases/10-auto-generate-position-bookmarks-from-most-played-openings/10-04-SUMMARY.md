---
phase: 10-auto-generate-position-bookmarks-from-most-played-openings
plan: "04"
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, react, typescript, position-bookmarks, suggestions]

# Dependency graph
requires:
  - phase: 10-auto-generate-position-bookmarks-from-most-played-openings
    provides: suggestion endpoint, get_existing_full_hashes, get_top_positions_for_color, suggest_match_side

provides:
  - get_existing_target_hashes (reads target_hash directly, no FEN recomputation)
  - get_top_positions_for_color deduplicates by color-specific hash with 2-game minimum
  - suggest_match_side two-granularity heuristic with ply constraint
  - create_bookmark increments sort_order via MAX+1
  - PositionBookmarkCard "Opponent" label

affects: [position-bookmarks, suggestions-modal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-granularity heuristic: compare my_hash_count vs full_hash_count with ply constraint to detect opponent variation"
    - "Group by color-specific hash to deduplicate suggestions by target hash"

key-files:
  created: []
  modified:
    - app/repositories/position_bookmark_repository.py
    - app/routers/position_bookmarks.py
    - tests/test_bookmark_repository.py
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx

key-decisions:
  - "get_existing_target_hashes reads target_hash column directly instead of recomputing full_hash from FEN — avoids exclusion failure for mine/opponent bookmarks"
  - "get_top_positions_for_color groups by color-specific hash (white_hash or black_hash) to merge opponent variations under a single target hash — eliminates duplicate suggestions"
  - "suggest_match_side two-granularity heuristic: if my_hash_count > 2 * full_hash_count within ply range, suggest mine (opponent varies); else suggest both"
  - "create_bookmark sort_order = COALESCE(MAX(sort_order), -1) + 1 so new bookmarks always append in stable order"
  - "Minimum 2 games filter in get_top_positions_for_color per user preference"

patterns-established:
  - "Two-granularity position heuristic: compare broad hash (color only) vs narrow hash (full position) game counts within a ply range"

requirements-completed: [AUTOBKM-02, AUTOBKM-03, AUTOBKM-08]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 10 Plan 04: Gap Closure Summary

**Fixed 5 UAT gaps: suggestion dedup by target_hash, two-granularity match_side heuristic, incremental sort_order, and "Opponent" label text**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T12:05:02Z
- **Completed:** 2026-03-15T12:10:08Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Suggestions now correctly exclude already-bookmarked positions by reading `target_hash` directly (not recomputing `full_hash` from FEN)
- Suggestions deduplicated by color-specific hash — opponent variations merge under one "my pieces" entry; minimum 2 games filter applied
- Match side heuristic replaced with two-granularity comparison (my_hash_count vs full_hash_count within ply range) — correctly suggests "both" for consistent positions
- New bookmarks get `sort_order = MAX(existing) + 1` instead of hardcoded 0 — stable card ordering on bulk save
- ToggleGroupItem "Opp" changed to "Opponent" in bookmark card

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix backend suggestion dedup, heuristic, sort_order, and grouping** - `1f69f75` (fix)
2. **Task 2: Fix Opponent label text in PositionBookmarkCard** - `8acc41f` (fix)

## Files Created/Modified
- `app/repositories/position_bookmark_repository.py` - Renamed get_existing_full_hashes to get_existing_target_hashes; rewrote get_top_positions_for_color to group by color hash; replaced suggest_match_side heuristic; fixed create_bookmark sort_order
- `app/routers/position_bookmarks.py` - Updated calls to use new function names and pass full_hash + ply params to suggest_match_side
- `tests/test_bookmark_repository.py` - Updated all tests to match new function signatures and behavior; added 2 new tests (minimum games filter, dedup by color hash)
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` - "Opp" -> "Opponent" label

## Decisions Made
- Read `target_hash` directly from bookmarks instead of recomputing from FEN — simpler and semantically correct
- Group by color-specific hash (not full composite) so opponent variations merge naturally
- Two-granularity heuristic: `my_hash_count > 2 * full_hash_count` threshold chosen because it's robust — a 2x gap clearly indicates significant opponent variation

## Deviations from Plan

**1. [Rule 1 - Bug] Updated test suite to match new function signatures**
- **Found during:** Task 1 (backend fixes)
- **Issue:** Tests referenced old `get_existing_full_hashes`, `exclude_full_hashes`, and `suggest_match_side` with old signature; existing test for `test_get_top_positions_returns_results` seeded only 1 game for Position B which would fail the new 2-game minimum filter
- **Fix:** Updated all test imports, parameter names, and test data; updated heuristic tests to match new two-granularity semantics; added 2 new tests (minimum games, deduplication by color hash)
- **Files modified:** tests/test_bookmark_repository.py
- **Verification:** All 19 tests pass
- **Committed in:** 1f69f75 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test suite update required by implementation change)
**Impact on plan:** Required to keep tests passing. No scope creep.

## Issues Encountered
None — all root causes were well-diagnosed in debug files, implementation was straightforward.

## Next Phase Readiness
- All 5 UAT gaps from phase 10 are now fixed
- Phase 10 is complete — all 4 plans done

---
*Phase: 10-auto-generate-position-bookmarks-from-most-played-openings*
*Completed: 2026-03-15*

## Self-Check: PASSED

- FOUND: app/repositories/position_bookmark_repository.py
- FOUND: app/routers/position_bookmarks.py
- FOUND: frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
- FOUND: .planning/phases/10-auto-generate-position-bookmarks-from-most-played-openings/10-04-SUMMARY.md
- FOUND: commit 1f69f75
- FOUND: commit 8acc41f
