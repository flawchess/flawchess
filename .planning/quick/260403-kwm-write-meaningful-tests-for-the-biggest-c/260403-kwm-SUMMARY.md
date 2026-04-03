---
phase: quick
plan: 260403-kwm
subsystem: tests
tags: [testing, bookmarks, stats, openings, time-series, rolling-window]
dependency_graph:
  requires: []
  provides: [test-coverage-bookmarks-router, test-coverage-stats-service, test-coverage-openings-time-series]
  affects: [CI test suite]
tech_stack:
  added: []
  patterns: [httpx ASGITransport router testing, namedtuple mock rows for pure functions, seeded DB integration tests]
key_files:
  created:
    - tests/test_bookmarks_router.py
    - tests/test_stats_service.py
    - tests/test_openings_time_series.py
  modified: []
decisions:
  - "namedtuple MockRow for _rows_to_wdl_categories — SQLAlchemy Row index access is emulated by namedtuple.__getitem__"
  - "Literal types in _make_request() helper — ty rejects str where Literal is expected; used Literal annotations directly instead of type: ignore"
  - "TestGetMostPlayedOpenings structure-only — openings_dedup is a DB-managed view, seeding games with matching eco/name/ply is complex; structure validation captures the useful invariant without brittle data coupling"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-03"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 0
---

# Quick Task 260403-kwm: Meaningful Tests for Biggest Coverage Gaps Summary

Write meaningful tests for the three biggest coverage gaps: position bookmarks router (35%), stats service (59%), and openings time series (untested). 34 new tests across 3 files targeting real business logic — WDL computation correctness, rolling window math, CRUD lifecycle through HTTP, platform filtering.

## Tasks Completed

| Task | Name | Commit | Tests Added |
|------|------|--------|-------------|
| 1 | Position bookmarks router — CRUD + suggestions + match-side | 0a34db3 | 13 |
| 2 | Stats service — _rows_to_wdl_categories + rating history + global stats | 3d6f12b | 12 |
| 3 | Openings time series — rolling window + recency filtering + multi-bookmark | fb184f1 | 9 |

**Total: 34 new tests, all passing.**

## What Was Tested

### tests/test_bookmarks_router.py (13 tests)

**TestBookmarkCRUD:** Full HTTP lifecycle — create (201 with shape validation including target_hash as string), list (both bookmarks present), update label (other fields unchanged), delete (204 + list confirms removal), delete nonexistent (404), update nonexistent (404).

**TestBookmarkReorder:** Create 3 bookmarks, PUT /reorder with reversed order, assert sort_order 0/1/2 mapped to b3/b1/b2.

**TestBookmarkMatchSide:** PATCH /match-side to "mine" changes `match_side` field and recomputes `target_hash` (white_hash vs full_hash). 404 for nonexistent ID.

**TestBookmarkAuth:** Unauthenticated GET and POST return 401.

**TestBookmarkSuggestions:** New user gets empty suggestions list; response has `suggestions` key with list value.

### tests/test_stats_service.py (12 tests)

**TestRowsToWdlCategories (pure function, no DB):**
- Basic conversion: blitz 6/2/2/10 → win_pct=60.0, labels applied via label_fn
- Missing category: blitz-only rows with [blitz, rapid, classical] label_order → 1 entry
- Zero total: row with 0 total produces 0.0 percentages without division by zero
- Label order preserved: rapid/blitz rows with [bullet, blitz, rapid] label_order → [Blitz, Rapid]

**TestGetRatingHistory (DB integration):** Seeded 2 chess.com + 1 lichess game. Both platforms populated when no filter; chess.com filter yields empty lichess; lichess filter yields empty chess_com. Data point fields validated.

**TestGetGlobalStats (DB integration):** 3 blitz as white (1W/1D/1L) + 2 rapid as black (2W) — blitz total=3 with 1/1/1 WDL, rapid total=2 with 2W. by_color split: White 1/1/1, Black 2/0/0. Win percentage rounding: 2/3 = 66.7%.

**TestGetMostPlayedOpenings:** Structure validation — white/black are lists; if entries present, all required fields exist.

### tests/test_openings_time_series.py (9 tests)

**TestRollingWindow:**
- Single win: 1 data point, win_rate=1.0, game_count=1, window_size=ROLLING_WINDOW_SIZE
- Single loss: win_rate=0.0
- Two games same day: data_by_date keeps last snapshot → 1 data point with win_rate=0.5, game_count=2
- Multi-day sequence: 5 games across 5 days (3W then 2L) → first point=1.0, final point=0.6 (3/5)
- Empty position: empty data, total_games=0

**TestRecencyFilter:**
- Recency trims output: 1 old game (60 days) + 2 recent (today) with recency=month → only today's points in output, total_games=2 (recomputed from filtered period)
- Rolling window uses full history: 3 old wins + 1 recent loss with recency=month → today's datapoint has game_count=4 and win_rate=0.75 (trailing window includes pre-filter games)

**TestMultipleBookmarks:**
- Two hashes yield two BookmarkTimeSeries with correct bookmark_ids and independent WDL counts
- Empty + populated bookmark pair: both series returned, empty has 0 games

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Literal types in _make_request() helper**
- **Found during:** Task 3 — `uv run ty check` after writing the file
- **Issue:** `_make_request()` helper used `str` for `match_side`, `color`, and `recency` parameters. ty rejects `str` where `Literal[...]` is required and doesn't honor `# type: ignore[arg-type]` (mypy syntax).
- **Fix:** Changed parameter types to `Literal["white", "black", "full"]`, `Literal["white", "black"]`, and `Literal["week", "month", ...]` respectively. Removed incorrect `# ty: ignore` comments.
- **Files modified:** tests/test_openings_time_series.py
- **Commit:** fb184f1 (same task commit)

## Verification

```
uv run pytest tests/test_bookmarks_router.py tests/test_stats_service.py tests/test_openings_time_series.py -x -v
# 34 passed

uv run pytest -x
# 524 passed

uv run ty check app/ tests/
# All checks passed!
```

## Self-Check: PASSED

- tests/test_bookmarks_router.py: FOUND
- tests/test_stats_service.py: FOUND
- tests/test_openings_time_series.py: FOUND
- Commits 0a34db3, 3d6f12b, fb184f1: FOUND in git log
- 524 total tests pass (no regressions)
- ty check passes with zero errors
