---
phase: 10-auto-generate-position-bookmarks-from-most-played-openings
verified: 2026-03-15T13:00:00Z
status: human_needed
score: 14/14 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 9/9
  gaps_closed:
    - "Suggestions exclude already-bookmarked positions using target_hash (not recomputed full_hash)"
    - "Suggestions return unique positions with no duplicate target hashes (grouped by color-specific hash)"
    - "Match side heuristic suggests Both when opponent play is consistent, Mine when opponent varies"
    - "New bookmarks get sort_order = MAX(existing) + 1 instead of hardcoded 0"
    - "Opponent toggle label reads Opponent not Opp"
  gaps_remaining: []
  regressions: []
gaps: []
human_verification:
  - test: "Open suggestions modal and verify mini board thumbnails render correctly"
    expected: "Each suggestion card shows a correctly-oriented mini chess board at 80px, opening name, game count badge, and Mine/Both toggle defaulting to heuristic suggestion"
    why_human: "react-chessboard rendering and visual correctness cannot be verified programmatically"
  - test: "Verify suggestions no longer include already-bookmarked positions after gap closure"
    expected: "Modal shows only positions not yet bookmarked; no suggestion matches an existing bookmark card"
    why_human: "Requires live data: user must have bookmarks and observe that suggestions exclude them"
  - test: "Verify match side heuristic produces Both for consistent openings"
    expected: "Some suggestions show Both as the pre-selected toggle; not all suggestions default to Mine"
    why_human: "Heuristic correctness depends on actual game data distribution in the user's account"
  - test: "Create multiple bookmarks via bulk save and verify stable sort order"
    expected: "Newly saved bookmarks appear at the bottom of the list in the order they were saved; reloading the page preserves the order"
    why_human: "sort_order correctness under concurrent bulk-save requires live browser observation"
  - test: "Click Mine/Opp/Both toggle on a bookmark card and verify target_hash updates"
    expected: "Backend PATCH called; card shows updated match_side; analysis results change accordingly; Opponent label reads Opponent not Opp"
    why_human: "Mutation side-effect and target_hash recomputation correctness requires live integration test"
---

# Phase 10: Auto-generate Position Bookmarks Verification Report

**Phase Goal:** Let users auto-generate position bookmarks from their most-played opening positions, with a suggestion modal showing mini board previews and bulk save, and enhance existing bookmark cards with mini board thumbnails and inline piece filter controls.
**Verified:** 2026-03-15T13:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 10-04 fixed 5 UAT issues)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /position-bookmarks/suggestions returns top 5 white + top 5 black positions by frequency in ply range 6-14 | VERIFIED | Router lines 48-50: `PLY_MIN=6, PLY_MAX=14, LIMIT_PER_COLOR=5`; loops over `("white","black")` calling `get_top_positions_for_color` |
| 2 | Suggestions exclude positions already bookmarked (deduplication by target_hash) | VERIFIED | `get_existing_target_hashes` reads `target_hash` column directly (line 147); router passes result as `exclude_target_hashes`; `test_get_top_positions_excludes_hashes` passes |
| 3 | Suggestions return unique positions with no duplicate target hashes | VERIFIED | `get_top_positions_for_color` groups by color-specific hash only (line 181); opponent variations merge under one entry; `test_get_top_positions_deduplicates_by_color_hash` passes |
| 4 | Positions with fewer than 2 games are excluded from suggestions | VERIFIED | `.having(func.count(...) >= 2)` at line 191; `test_get_top_positions_minimum_two_games` passes |
| 5 | Match side heuristic suggests Both when opponent play is consistent, Mine when opponent varies | VERIFIED | `suggest_match_side` uses two-granularity comparison: `my_hash_count > 2 * full_hash_count` (line 272); `test_suggest_match_side_both_when_consistent` and `test_suggest_match_side_mine_when_opponent_varies` both pass |
| 6 | Each suggestion includes FEN, SAN moves, opening name/ECO, game count, and piece filter heuristic | VERIFIED | Router reconstructs FEN+SAN via python-chess PGN replay, calls `find_opening`, includes all in `PositionSuggestion` response schema |
| 7 | PATCH /position-bookmarks/{id}/match-side recomputes target_hash from stored FEN and new match_side | VERIFIED | `update_match_side` in repository parses FEN with `chess.Board`, calls `compute_hashes`, resolves target_hash by match_side+color; 3 tests pass |
| 8 | New bookmarks get incrementing sort_order values, not all zero | VERIFIED | `create_bookmark` queries `COALESCE(MAX(sort_order), -1) + 1` at lines 52-55; no hardcoded 0 |
| 9 | User can open a suggestions modal from the Position bookmarks section | VERIFIED | `PositionBookmarkList.tsx` has `btn-suggest-bookmarks` button wired to `setSuggestionsOpen(true)`; `SuggestionsModal` rendered |
| 10 | Modal shows up to 10 suggestions with mini board previews, game counts, opening names, and suggested piece filter | VERIFIED | `SuggestionsModal.tsx`: renders white/black sections with `MiniBoard`, `Badge` for game count, opening label, `ToggleGroup` Mine/Both per suggestion |
| 11 | Each bookmark card shows a mini board thumbnail (~60-80px) of its position | VERIFIED | `PositionBookmarkCard.tsx` line 98: `<MiniBoard fen={bookmark.fen} flipped={bookmark.is_flipped} size={60} />`; hidden on mobile via `hidden sm:block` |
| 12 | Each bookmark card has an inline piece filter control that calls backend on change | VERIFIED | `ToggleGroup` Mine/Opponent/Both bound to `bookmark.match_side` at lines 127-161; `handleMatchSideChange` calls `updateMatchSide.mutate` |
| 13 | Opponent toggle label reads "Opponent" not "Opp" | VERIFIED | `PositionBookmarkCard.tsx` line 151: `Opponent` text confirmed in ToggleGroupItem |
| 14 | All 19 backend tests pass | VERIFIED | `uv run pytest tests/test_bookmark_repository.py` — 19/19 passed; no failures |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/repositories/position_bookmark_repository.py` | `get_existing_target_hashes, get_top_positions_for_color, suggest_match_side, create_bookmark, update_match_side` | VERIFIED | All five functions present and substantive; gap-closure fixes applied: target_hash dedup, color-hash grouping, two-granularity heuristic, MAX+1 sort_order |
| `app/routers/position_bookmarks.py` | `GET /position-bookmarks/suggestions, PATCH /position-bookmarks/{id}/match-side` | VERIFIED | Both endpoints implemented; route ordering correct; uses `get_existing_target_hashes` and passes `full_hash + ply params` to heuristic |
| `tests/test_bookmark_repository.py` | 19 tests covering suggestions, heuristic, match_side update, CRUD, reorder, isolation | VERIFIED | 19/19 pass; includes 2 new tests from gap closure: `test_get_top_positions_minimum_two_games`, `test_get_top_positions_deduplicates_by_color_hash` |
| `frontend/src/components/position-bookmarks/MiniBoard.tsx` | Reusable read-only mini chess board thumbnail | VERIFIED | Component exists; `pointer-events-none`, `allowDragging: false`, `data-testid="mini-board"` |
| `frontend/src/components/position-bookmarks/SuggestionsModal.tsx` | Modal dialog with mini boards, per-suggestion toggles, bulk save | VERIFIED | Substantive component; Dialog with loading/empty states, white/black sections, per-suggestion checkbox+toggle, bulk save with progress |
| `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` | Enhanced card with MiniBoard, inline piece filter ToggleGroup, Opponent label | VERIFIED | MiniBoard at line 98; ToggleGroup Mine/Opponent/Both at lines 127-161; "Opponent" text confirmed at line 151 |
| `frontend/src/types/position_bookmarks.ts` | `PositionSuggestion, SuggestionsResponse, MatchSideUpdateRequest` types | VERIFIED | All three interfaces defined |
| `frontend/src/hooks/usePositionBookmarks.ts` | `usePositionSuggestions, useUpdateMatchSide` hooks | VERIFIED | Both hooks present and wired |
| `frontend/src/api/client.ts` | `positionBookmarksApi.getSuggestions, positionBookmarksApi.updateMatchSide` | VERIFIED | Both methods present with correct endpoints |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/position_bookmarks.py` | `get_existing_target_hashes` | reads target_hash directly | WIRED | Line 53: `get_existing_target_hashes(session, user.id)` |
| `app/routers/position_bookmarks.py` | `get_top_positions_for_color` | passes `exclude_target_hashes` | WIRED | Line 60-68: called with `exclude_target_hashes=existing_target_hashes` |
| `app/routers/position_bookmarks.py` | `suggest_match_side` | passes `full_hash, ply_min, ply_max` | WIRED | Lines 114-123: all new params passed correctly |
| `app/repositories/position_bookmark_repository.py:create_bookmark` | `PositionBookmark.sort_order` | `COALESCE(MAX(sort_order), -1) + 1` | WIRED | Lines 52-55: MAX+1 logic before bookmark creation |
| `PositionBookmarkCard.tsx` | `useUpdateMatchSide` | `handleMatchSideChange` mutation | WIRED | Line 72: `.mutate()` on ToggleGroup value change |
| `frontend/src/api/client.ts` | `PATCH /position-bookmarks/{id}/match-side` | `apiClient.patch` | WIRED | Confirmed from initial verification; TypeScript compiles clean |

### Requirements Coverage

AUTOBKM requirements are defined in ROADMAP.md Phase 10 section. All 8 are fully satisfied after gap closure:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTOBKM-01 | 10-01 | Top 5 white + top 5 black positions by frequency at ply 6-14 | SATISFIED | `get_top_positions_for_color` with `ply_min=6, ply_max=14, limit=5` per color |
| AUTOBKM-02 | 10-01, 10-04 | Suggestions exclude already-bookmarked positions | SATISFIED | `get_existing_target_hashes` reads `target_hash` directly; test passes |
| AUTOBKM-03 | 10-01, 10-04 | Piece filter heuristic suggests Mine vs Both | SATISFIED | Two-granularity `my_hash_count > 2 * full_hash_count`; two tests verify mine/both cases |
| AUTOBKM-04 | 10-01 | PATCH endpoint updates match_side and recomputes target_hash | SATISFIED | `PATCH /position-bookmarks/{id}/match-side`; FEN-based hash recomputation; 3 tests pass |
| AUTOBKM-05 | 10-02 | Suggestions modal shows mini boards, game counts, opening names, suggested piece filter | SATISFIED | `SuggestionsModal.tsx` renders all per card |
| AUTOBKM-06 | 10-02 | User can select/deselect and bulk-save suggestions | SATISFIED | Checkbox per suggestion, `handleSave` for-of loop, cache invalidation |
| AUTOBKM-07 | 10-03 | Bookmark cards show mini board thumbnails (~60-80px) | SATISFIED | `MiniBoard` at size=60, responsive via `hidden sm:block` |
| AUTOBKM-08 | 10-03, 10-04 | Bookmark cards have inline piece filter (match_side) control | SATISFIED | `ToggleGroup` Mine/Opponent/Both in card; "Opponent" label fixed; wired to `useUpdateMatchSide` |

**Note on REQUIREMENTS.md:** All 8 AUTOBKM IDs are absent from the REQUIREMENTS.md traceability table. This is a documentation-only gap — the requirements are fully defined in ROADMAP.md and fully implemented. REQUIREMENTS.md was last updated after Phase 4; Phase 10 requirements were defined as provisional in the ROADMAP.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/routers/position_bookmarks.py` | 95-107 | Broad `except Exception: continue` swallows PGN parse errors silently | Info | A malformed PGN would silently skip that suggestion; acceptable for suggestion quality |
| `app/repositories/position_bookmark_repository.py` | Over-fetch logic | `over_fetch_limit = limit + len(exclude_target_hashes) + 10` — arbitrary +10 buffer | Info | If exclude set is large (>10 times limit), the over-fetch may still miss positions; unlikely in practice but not provably correct for all cases |

No blockers or warnings found. No TODO/FIXME/placeholder patterns. No stub implementations. No empty returns.

### Human Verification Required

#### 1. Mini Board Rendering in Suggestions Modal

**Test:** Log in, import some games, click "Suggest bookmarks" in the Position bookmarks section.
**Expected:** Modal opens showing white/black opening sections; each suggestion card shows a correctly-oriented chess board thumbnail at 80px, opening name, game count badge, and Mine/Both toggle defaulting to the heuristic suggestion.
**Why human:** react-chessboard rendering and visual correctness cannot be verified programmatically.

#### 2. Suggestions Exclude Existing Bookmarks (Gap Closure Validation)

**Test:** User has existing bookmarks. Click "Suggest bookmarks" and compare the suggestions list against the bookmark cards.
**Expected:** No suggestion in the modal corresponds to a position already saved as a bookmark. The deduplication uses `target_hash` comparison, not full_hash recomputation.
**Why human:** Requires live data where the user has both bookmarks and game history to verify the gap closure works in production.

#### 3. Match Side Heuristic Produces Both (Gap Closure Validation)

**Test:** Click "Suggest bookmarks" with a user account that has several hundred games in common openings.
**Expected:** Some suggestions show the Mine/Both toggle pre-set to "Both" — not all suggestions default to Mine. Positions with consistent full-position match across games should show Both.
**Why human:** Heuristic correctness depends on actual game data distribution; requires a real user account with meaningful game history.

#### 4. Stable Sort Order on Bulk Save (Gap Closure Validation)

**Test:** Open suggestions modal, select multiple suggestions, click Save. After saving, observe the order of the newly-created bookmark cards.
**Expected:** New bookmarks appear at the end of the list in save order. Reloading the page preserves the same order. Card order does not change when toggling the piece filter on any card.
**Why human:** Sort order stability under the new MAX+1 logic requires live observation; previous UAT found all cards colliding at sort_order=0 causing order to flip on filter change.

#### 5. Opponent Label and Piece Filter Toggle

**Test:** On a bookmark card, observe all three toggle items. Click Opponent, then Both, then Mine.
**Expected:** Toggle labels read "Mine", "Opponent", "Both" (not "Opp"). Each click triggers a PATCH call; the active toggle reflects the new value after mutation completes. Mini board opacity reduces to 0.6 while pending, then returns to 1.0.
**Why human:** Visual label rendering and mutation pending state require live browser observation.

### Gaps Summary

No gaps remain. All 5 UAT issues identified during testing have been fixed and verified against the actual codebase:

1. **Deduplication by target_hash** — `get_existing_target_hashes` now reads `target_hash` directly from bookmarks; old code recomputed `full_hash` from FEN, missing mine/opponent bookmarks. Fixed in commit `1f69f75`.

2. **Unique suggestions by color hash** — `get_top_positions_for_color` now groups by color-specific hash, merging all opponent variations under one entry. Old code grouped by `(white_hash, black_hash, full_hash)` allowing duplicate suggestions. Fixed in commit `1f69f75`.

3. **Two-granularity match side heuristic** — `suggest_match_side` now compares `my_hash_count` vs `full_hash_count` within the ply range. Old ratio `distinct_full/distinct_games` was structurally ~1.0, making the 1.5 threshold unreachable. Fixed in commit `1f69f75`.

4. **Incrementing sort_order** — `create_bookmark` now queries `COALESCE(MAX(sort_order), -1) + 1`. Old code hardcoded `sort_order=0`. Fixed in commit `1f69f75`.

5. **Opponent label** — `PositionBookmarkCard.tsx` ToggleGroupItem text changed from "Opp" to "Opponent". Fixed in commit `8acc41f`.

All 19 backend tests pass. TypeScript compiles clean. Ruff reports no lint errors. The phase is functionally complete; remaining items require human browser validation.

---

_Verified: 2026-03-15T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after gap closure plan 10-04_
