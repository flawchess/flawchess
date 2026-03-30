---
phase: 38-opening-statistics-bookmark-suggestions-rework
verified: 2026-03-29T11:00:00Z
status: human_needed
score: 6/6 must-haves verified
human_verification:
  - test: "Open Statistics tab without bookmarks — verify charts show most-played openings data"
    expected: "Results by Opening and Win Rate Over Time show up to 3 white + 3 black most-played openings with real WDL data, no empty state"
    why_human: "Requires a logged-in user with game imports; chart rendering not testable statically"
  - test: "Open Position Bookmarks > Suggest — verify suggestions come from most-played openings without any backend loading delay"
    expected: "Modal populates immediately from already-fetched mostPlayedData; already-bookmarked positions are absent"
    why_human: "Network timing and suggestion filtering require visual inspection"
  - test: "Toggle chart-enable off on a bookmark, reload page — verify toggle state persists and chart excludes that bookmark"
    expected: "Toggled-off bookmark disappears from Results by Opening and Win Rate Over Time after page reload"
    why_human: "localStorage persistence and chart re-render require browser interaction"
  - test: "Delete a bookmark that had chart-enable toggled off, re-create it — verify toggle defaults to enabled"
    expected: "Newly created bookmark appears in charts (toggle defaults on)"
    why_human: "localStorage cleanup on delete requires end-to-end browser flow"
  - test: "Verify bookmark card layout on mobile viewport"
    expected: "72-84px minimap visible, button row (toggle/load/delete) below piece filter, no overflow"
    why_human: "Responsive layout correctness requires visual inspection at small viewport"
---

# Phase 38: Opening Statistics & Bookmark Suggestions Rework — Verification Report

**Phase Goal:** Reorder Opening Statistics sections, use top most-played openings as default chart data when no bookmarks exist, rework bookmark suggestion system using most-played openings data, add chart-enable toggle to bookmarks, redesign bookmark card layout

**Verified:** 2026-03-29T11:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OpeningWDL backend response includes full_hash field | VERIFIED | `app/schemas/stats.py` line 49: `full_hash: str`; DB query at `stats_repository.py` line 220 selects `full_hash`; service at `stats_service.py` line 259 passes `full_hash=str(full_hash)` |
| 2 | Statistics tab shows Results by Opening first, then Win Rate Over Time, then Most Played White, then Most Played Black | VERIFIED | `Openings.tsx` lines 623-729: `statisticsContent` renders in exact order: Results by Opening (623), Win Rate Over Time (691), Most Played as White (697), Most Played as Black (717) |
| 3 | When user has no bookmarks, charts show data from top 3 most-played openings per color | VERIFIED | `Openings.tsx` lines 188-218: `defaultChartEntries` slices `mostPlayedData.white/black` to `DEFAULT_CHART_LIMIT=3`; `chartBookmarks` uses `defaultChartEntries` when `bookmarks.length === 0` |
| 4 | When user has bookmarks, charts use only bookmark data filtered by chart-enable toggle | VERIFIED | `Openings.tsx` line 216-218: `chartBookmarks = bookmarks.filter(b => chartEnabledMap[b.id] !== false)` when bookmarks exist |
| 5 | Bookmark suggestions derive from most-played openings, skip already-bookmarked positions, show fallback | VERIFIED | `SuggestionsModal.tsx` lines 40-63: derives from `mostPlayedData` prop, filters by `full_hash` vs `target_hash`, fallback message at line 191 |
| 6 | Each bookmark card has chart-enable toggle persisted in localStorage | VERIFIED | `PositionBookmarkCard.tsx` lines 36-37, 206-212: props `chartEnabled`/`onChartEnabledChange`; `data-testid="bookmark-chart-toggle-{id}"`; `Openings.tsx` lines 4-8: `getChartEnabled`/`setChartEnabledStorage` localStorage helpers; `usePositionBookmarks.ts` line 42: `localStorage.removeItem` on delete |
| 7 | Bookmark card layout has bigger minimap and button row below piece filter | VERIFIED | `PositionBookmarkCard.tsx` line 128: `size={84}` (up from 60px, exceeds 72px spec); button row at lines 204-232 with chart toggle (left), load (middle), delete (right) in `flex items-center justify-between` |
| 8 | Position Bookmarks popover explains Piece filter and chart-enable toggle | VERIFIED | `Openings.tsx` desktop popover (lines 468-473) and mobile popover (lines 931-940) both contain "Piece filter" and "chart toggle" explanations |
| 9 | Dead suggestion code removed (usePositionSuggestions, getSuggestions, PositionSuggestion, SuggestionsResponse) | VERIFIED | `grep` found zero occurrences in `usePositionBookmarks.ts`, `client.ts`, and `position_bookmarks.ts` |

**Score:** 9/9 truths verified (exceeds the 6 required must-haves across both plans)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/stats.py` | full_hash field on OpeningWDL | VERIFIED | Line 49: `full_hash: str` with comment |
| `app/services/stats_service.py` | full_hash computation in rows_to_openings | VERIFIED | Line 240: unpacked from DB row; line 259: `full_hash=str(full_hash)` in constructor. Note: pulled from DB query (not recomputed via compute_hashes), which is correct — avoids redundant hashing |
| `frontend/src/types/stats.ts` | full_hash field on OpeningWDL TS interface | VERIFIED | Line 34: `full_hash: string` |
| `frontend/src/pages/Openings.tsx` | DEFAULT_CHART_LIMIT + default chart data logic + chartEnabledMap | VERIFIED | Lines 4-8 (localStorage helpers), 63 (DEFAULT_CHART_LIMIT=3), 115-125 (chartEnabledMap), 188-218 (defaultChartEntries, chartBookmarks) |
| `frontend/src/components/position-bookmarks/SuggestionsModal.tsx` | Reworked SuggestionsModal using mostPlayedData prop | VERIFIED | Props include `mostPlayedData` and `bookmarks`; no `usePositionSuggestions` import; derives suggestions client-side |
| `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` | Chart-enable toggle + redesigned layout | VERIFIED | `data-testid="bookmark-chart-toggle-{id}"`, `size={84}` MiniBoard, button row |
| `frontend/src/hooks/usePositionBookmarks.ts` | localStorage cleanup on delete | VERIFIED | Line 42: `localStorage.removeItem` in `useDeletePositionBookmark` |
| `frontend/src/api/client.ts` | getSuggestions removed | VERIFIED | Not present |
| `frontend/src/types/position_bookmarks.ts` | PositionSuggestion/SuggestionsResponse removed | VERIFIED | Not present |
| `frontend/src/pages/Dashboard.tsx` | Chart toggle wiring (auto-fixed) | VERIFIED | Lines 4-8 (helpers), 73-81 (chartEnabledMap/handleChartEnabledChange), 456-457 (passed to PositionBookmarkList) |
| `tests/test_stats_router.py` | full_hash assertions in most_played tests | VERIFIED | Lines 307-309: asserts `full_hash` key exists, is a non-empty string |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/stats_service.py` | `app/repositories/stats_repository.py` | full_hash in DB rows | VERIFIED | Row tuple unpacked at line 240 includes full_hash from SQL query |
| `frontend/src/pages/Openings.tsx` | `frontend/src/types/stats.ts` | OpeningWDL.full_hash for synthetic bookmarks | VERIFIED | `defaultChartEntries` uses `o.full_hash` as `target_hash` at lines 193, 203 |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/position-bookmarks/SuggestionsModal.tsx` | mostPlayedData and bookmarks props | VERIFIED | Lines 1043-1048: `mostPlayedData={mostPlayedData}` and `bookmarks={bookmarks}` passed |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` | chartEnabled/onChartEnabledChange via PositionBookmarkList | VERIFIED | PositionBookmarkList passes `chartEnabled={chartEnabledMap[b.id] !== false}` and `onChartEnabledChange` at lines 67-68 |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/charts/WinRateChart.tsx` | chartBookmarks prop | VERIFIED | Line 694: `<WinRateChart bookmarks={chartBookmarks} series={tsData.series} />` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `Openings.tsx` statisticsContent | `chartBookmarks` | `bookmarks` (from `usePositionBookmarks`) or `defaultChartEntries` (from `mostPlayedData`) | Yes — `mostPlayedData` comes from `useMostPlayedOpenings` hook which calls real API endpoint | FLOWING |
| `SuggestionsModal.tsx` suggestion list | `whiteSuggestions`/`blackSuggestions` | `mostPlayedData` prop from parent | Yes — parent fetches via `useMostPlayedOpenings` | FLOWING |
| `PositionBookmarkCard.tsx` chart toggle | `chartEnabled` prop | `chartEnabledMap` → localStorage → `chartToggleVersion` state | Yes — localStorage reads real stored values; defaults to `true` for new bookmarks | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend most_played tests pass with full_hash | `uv run pytest tests/test_stats_router.py -x -k most_played` | 5 passed, 0 failed | PASS |
| Frontend TypeScript build succeeds | `npm run build` | Built in 4.62s, no errors | PASS |
| Frontend lint passes | `npm run lint` | No warnings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STAT-01 | 38-01 | Statistics tab sections in order: Results by Opening, Win Rate Over Time, Most Played White, Most Played Black | SATISFIED | `statisticsContent` renders in correct order at lines 623, 691, 697, 717 |
| STAT-02 | 38-01 | No-bookmark default: charts show top 3 most-played per color | SATISFIED | `DEFAULT_CHART_LIMIT=3`, `defaultChartEntries` slices `mostPlayedData.white/black[:3]` |
| STAT-03 | 38-02 | Bookmark suggestions from most-played data, skip bookmarked, fallback message | SATISFIED | SuggestionsModal derives client-side; filters by `full_hash`; fallback at line 191 |
| STAT-04 | 38-02 | Chart-enable toggle per bookmark, localStorage persistence, controls chart inclusion | SATISFIED | Toggle in PositionBookmarkCard; `chartEnabledMap` filters `chartBookmarks` |
| STAT-05 | 38-02 | Bigger minimap (~72px), button row (toggle/load/delete) below piece filter | SATISFIED | MiniBoard `size={84}` (exceeds ~72px target); button row confirmed |
| STAT-06 | 38-02 | Position Bookmarks popover explains Piece filter and chart-enable toggle | SATISFIED | Both desktop (line 468-473) and mobile (line 936-939) popovers updated |

No orphaned requirements — all 6 STAT-0x IDs claimed by plans and verified in code.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `Openings.tsx` | 221 | `if (chartBookmarks.length === 0) return null` in `timeSeriesRequest` useMemo | Info | Intentional guard — no time-series request when no chart data. Correct behavior. |

No stub patterns, no hardcoded empty returns that flow to user-visible output, no TODO/FIXME comments found in modified files.

### Human Verification Required

#### 1. Default chart data with no bookmarks

**Test:** Log in as a user with game imports but no bookmarks. Navigate to Openings > Statistics tab.
**Expected:** Results by Opening and Win Rate Over Time are populated with data from the top 3 most-played openings as white and top 3 as black (6 entries total). No "No bookmarks yet" empty state appears.
**Why human:** Requires authenticated user session with real game data; chart rendering cannot be verified statically.

#### 2. Bookmark suggestions from most-played data

**Test:** Open Position Bookmarks collapsible in the sidebar, click "Suggest". If you have existing bookmarks, verify those openings are absent from the suggestions list.
**Expected:** Modal populates immediately (no loading spinner from a backend call). Already-bookmarked positions are skipped. If all top 10 per color are bookmarked, fallback message appears.
**Why human:** Network timing and client-side filtering logic require runtime verification.

#### 3. Chart-enable toggle persistence

**Test:** With at least one bookmark, toggle its chart-enable switch off. Verify the bookmark disappears from Results by Opening and Win Rate Over Time. Reload the page. Verify the toggle is still off and the bookmark is still excluded from charts.
**Expected:** Toggle state survives page reload via localStorage. Charts update immediately on toggle.
**Why human:** localStorage reads, React re-render on toggle change, and chart exclusion all require browser interaction.

#### 4. localStorage cleanup on bookmark delete

**Test:** Toggle a bookmark's chart-enable off, then delete that bookmark. Re-create a bookmark at the same position. Verify the new bookmark defaults to chart-enabled (toggle is on).
**Expected:** Old localStorage key removed on delete; new bookmark starts with default-enabled state.
**Why human:** End-to-end flow spanning delete mutation, localStorage cleanup, and re-creation.

#### 5. Bookmark card layout on mobile viewport

**Test:** Resize browser to a mobile viewport (375px width). Open Position Bookmarks. Verify each card shows: larger minimap (~84px), piece filter toggle row, then button row (chart toggle on left, load in middle, delete on right).
**Expected:** All three sections visible, no horizontal overflow, buttons are tappable size.
**Why human:** Responsive layout correctness requires visual inspection.

### Gaps Summary

No automated gaps found. All 6 requirements are satisfied and all 9 observable truths are verified by code inspection. The 5 human verification items above are standard UX behaviors that cannot be confirmed without a running browser session.

**Implementation note on minimap size:** The plan specified `size={72}` and STAT-05 says "bigger minimap (~72px)". The implementation used `size={84}`, which exceeds the approximate target. This is not a gap — 84px is larger than the previous 60px and satisfies "bigger minimap".

**Implementation note on full_hash computation:** Plan 38-01 described computing `full_hash` via `chess.Board(fen)` + `compute_hashes()` in the service. The actual implementation pulls `full_hash` directly from the database query result (already stored in `game_positions.full_hash`). This is semantically equivalent and architecturally superior — it avoids redundant hashing and uses the canonical stored hash. The test assertion (`full_hash` is non-empty string) passes, confirming the field flows correctly.

---

_Verified: 2026-03-29T11:00:00Z_
_Verifier: Claude (gsd-verifier)_
