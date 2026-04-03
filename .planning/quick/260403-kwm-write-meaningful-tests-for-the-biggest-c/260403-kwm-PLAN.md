---
phase: quick
plan: 260403-kwm
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_bookmarks_router.py
  - tests/test_stats_service.py
  - tests/test_openings_time_series.py
autonomous: true
must_haves:
  truths:
    - "Position bookmarks CRUD cycle works end-to-end through the router layer"
    - "Stats service correctly computes WDL categories from SQL rows"
    - "Stats service rating history filters by platform correctly"
    - "Openings time series rolling window produces correct win rates"
    - "Openings time series recency filter trims output correctly"
  artifacts:
    - path: "tests/test_bookmarks_router.py"
      provides: "Router-level CRUD + suggestions + match-side tests for position bookmarks"
    - path: "tests/test_stats_service.py"
      provides: "Service-level tests for rating history, global stats, most-played openings"
    - path: "tests/test_openings_time_series.py"
      provides: "Service-level tests for get_time_series rolling window logic"
---

<objective>
Write meaningful tests for the three biggest coverage gaps: position bookmarks router (35%), stats service (59%), and openings time series (untested).

Purpose: Close coverage gaps with tests that verify real business logic — WDL computation correctness, rolling window math, CRUD lifecycle through HTTP, platform filtering — not just "returns 200" smoke tests.

Output: Three new test files covering the router and service layers with seeded data.
</objective>

<execution_context>
@.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@tests/conftest.py
@tests/test_imports_router.py (router test pattern: httpx AsyncClient + auth_headers fixture)
@tests/test_bookmark_repository.py (seed helpers: _seed_game_with_positions, _make_create)
@tests/test_openings_service.py (service test pattern: _seed_game + _seed_game_with_positions)
@tests/test_stats_router.py (existing stats router tests — surface-level only)
@app/routers/position_bookmarks.py
@app/services/stats_service.py
@app/services/openings_service.py (get_time_series, ROLLING_WINDOW_SIZE)
@app/schemas/position_bookmarks.py
@app/schemas/stats.py
@app/schemas/openings.py (TimeSeriesRequest, TimeSeriesBookmarkParam, TimeSeriesPoint)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Position bookmarks router tests — full CRUD + suggestions + match-side</name>
  <files>tests/test_bookmarks_router.py</files>
  <action>
Create `tests/test_bookmarks_router.py` with HTTP-level integration tests using the established pattern (httpx.AsyncClient + ASGITransport + auth_headers fixture). The repository layer is already well-tested in test_bookmark_repository.py — these tests verify the HTTP contract.

Test classes and cases:

**TestBookmarkCRUD** — Full lifecycle through HTTP:
- `test_create_returns_201_with_bookmark`: POST /api/position-bookmarks with valid body (label, target_hash as string "1234567890", fen after 1.e4, moves ["e4"], color "white", match_side "full"). Assert 201 + response has id, label, target_hash (string), fen, moves (list), color, match_side, sort_order.
- `test_list_returns_created_bookmarks`: Create 2 bookmarks, GET /api/position-bookmarks. Assert 200 + both present in response list.
- `test_update_label`: Create bookmark, PUT /api/position-bookmarks/{id} with {"label": "Updated"}. Assert 200 + label changed, other fields unchanged.
- `test_delete_returns_204`: Create bookmark, DELETE /api/position-bookmarks/{id}. Assert 204. GET list confirms removal.
- `test_delete_nonexistent_returns_404`: DELETE /api/position-bookmarks/999999. Assert 404.
- `test_update_nonexistent_returns_404`: PUT /api/position-bookmarks/999999 with {"label": "X"}. Assert 404.

**TestBookmarkReorder** — Drag-reorder via HTTP:
- `test_reorder_assigns_new_sort_order`: Create 3 bookmarks, PUT /api/position-bookmarks/reorder with ids in reversed order. Assert 200 + sort_order values match new order (0, 1, 2 in reversed sequence).

**TestBookmarkMatchSide** — match_side PATCH:
- `test_update_match_side_mine`: Create bookmark with match_side "both", PATCH /api/position-bookmarks/{id}/match-side with {"match_side": "mine"}. Assert 200 + match_side updated + target_hash changed (different from original).
- `test_update_match_side_nonexistent_returns_404`: PATCH /api/position-bookmarks/999999/match-side. Assert 404.

**TestBookmarkAuth** — Auth gates:
- `test_list_requires_auth`: GET /api/position-bookmarks without headers. Assert 401.
- `test_create_requires_auth`: POST /api/position-bookmarks without headers. Assert 401.

**TestBookmarkSuggestions** — Suggestions endpoint:
- `test_suggestions_returns_200_empty_for_new_user`: GET /api/position-bookmarks/suggestions. Assert 200 + suggestions is empty list (new user has no games).
- `test_suggestions_structure`: Assert response has `suggestions` key with list value.

Use module-scoped auth_headers fixture (register + login once). For bookmark creation, use this standard body:
```python
{"label": "Test", "target_hash": "1234567890", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", "moves": ["e4"], "color": "white", "match_side": "full"}
```

Note: target_hash is sent as string (JavaScript BigInt compat) — the schema coerces it.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_bookmarks_router.py -x -v</automated>
  </verify>
  <done>All bookmark router tests pass. CRUD lifecycle (create -> list -> update -> delete), reorder, match-side update, auth gates, and suggestions endpoint are covered at the HTTP layer.</done>
</task>

<task type="auto">
  <name>Task 2: Stats service tests — _rows_to_wdl_categories, get_rating_history, get_global_stats, get_most_played_openings</name>
  <files>tests/test_stats_service.py</files>
  <action>
Create `tests/test_stats_service.py` with service-level integration tests. Use db_session fixture + _seed_game helper (same pattern as test_openings_service.py). The stats_router tests only check HTTP shape — these verify business logic with seeded data.

Test classes and cases:

**TestRowsToWdlCategories** — Pure function, no DB needed:
- `test_basic_conversion`: Create mock Row-like objects (use namedtuple or SimpleNamespace with index support) for 2 categories: ("blitz", 10, 6, 2, 2) and ("rapid", 5, 3, 1, 1). Call `_rows_to_wdl_categories(rows, label_fn=lambda k: k.title(), label_order=["blitz", "rapid"])`. Assert result has 2 WDLByCategory entries with correct win_pct (60.0 for blitz), draw_pct, loss_pct, label ("Blitz", "Rapid").
- `test_missing_category_skipped`: Provide rows for only "blitz" but label_order includes ["blitz", "rapid", "classical"]. Assert result has 1 entry (only blitz).
- `test_zero_total_yields_zero_pcts`: Row ("bullet", 0, 0, 0, 0) — assert all percentages are 0.0.
- `test_preserves_label_order`: Rows for rapid and blitz (out of order). label_order=["bullet", "blitz", "rapid"]. Assert result order is [Blitz, Rapid] (bullet skipped, order preserved).

For mock rows, use this approach to match SQLAlchemy Row index access:
```python
from collections import namedtuple
MockRow = namedtuple("MockRow", ["key", "total", "wins", "draws", "losses"])
```
Then wrap in a list and access by index `row[0]`, `row[1]`, etc.

**TestGetRatingHistory** — DB integration:
- `test_both_platforms`: Seed 2 chess.com games and 1 lichess game (different platforms, with white_rating/black_rating set). Call `get_rating_history(session, user_id, recency=None)`. Assert chess_com has data points and lichess has data points.
- `test_platform_filter_chess_com`: Call with `platform="chess.com"`. Assert chess_com is populated, lichess is empty list.
- `test_platform_filter_lichess`: Call with `platform="lichess"`. Assert lichess is populated, chess_com is empty list.

For seeding games with ratings, extend _seed_game to set `white_rating` and `black_rating` on the Game model.

**TestGetGlobalStats** — DB integration:
- `test_returns_wdl_by_time_control_and_color`: Seed 3 blitz games (1 win, 1 draw, 1 loss as white) + 2 rapid games (2 wins as black). Call `get_global_stats(session, user_id, recency=None)`. Assert by_time_control has entries for blitz and rapid with correct counts. Assert by_color has white (1W/1D/1L) and black (2W/0D/0L).

**TestGetMostPlayedOpenings** — DB integration:
- `test_returns_openings_with_wdl`: Seed 3 white games with opening_eco="B20" and opening_name="Sicilian Defense" (2 wins, 1 loss), plus matching game_positions with the same full_hash pointing to a valid openings_dedup entry. Call `get_most_played_openings(session, user_id)`. Assert white list is non-empty and first entry has correct eco, name, wins/losses counts.
- NOTE: This test depends on the openings_dedup view existing. If no openings_dedup rows match, the result will be empty — that's acceptable. Add a comment explaining this dependency. If the view is empty, just assert the response structure is valid (white and black are lists).

Use a dedicated user_id per test class (e.g., 800-series) to avoid cross-test pollution. Add `ensure_test_user` calls in the autouse fixture.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_stats_service.py -x -v</automated>
  </verify>
  <done>Stats service tests pass. _rows_to_wdl_categories is tested as a pure function with edge cases. get_rating_history platform filtering verified with seeded data. get_global_stats WDL aggregation verified.</done>
</task>

<task type="auto">
  <name>Task 3: Openings time series tests — rolling window correctness and recency filtering</name>
  <files>tests/test_openings_time_series.py</files>
  <action>
Create `tests/test_openings_time_series.py` with service-level integration tests for `get_time_series`. This is the biggest untested logic gap — the rolling window computation in lines 194-275 of openings_service.py.

Use db_session fixture + _seed_game_with_positions helper (same pattern as test_openings_service.py). The key insight: seeded games need full_hash on position rows so query_time_series can match them.

Test classes and cases:

**TestRollingWindow** — Core rolling window math:
- `test_single_game_win_rate_is_100_or_0`: Seed 1 game (win as white) with a GamePosition at ply 1 matching the target full_hash. Create TimeSeriesRequest with one bookmark (bookmark_id=1, target_hash=<full_hash>, match_side="full", color="white"). Call `get_time_series(session, user_id, request)`. Assert series has 1 BookmarkTimeSeries, data has 1 point with win_rate=1.0, game_count=1, window_size=ROLLING_WINDOW_SIZE. Assert total_wins=1, total_games=1.
- `test_two_games_same_day_keeps_last`: Seed 2 games (1 win, 1 loss) on the same day with same full_hash. Assert data has 1 point (same date collapsed), win_rate reflects both games in window (0.5 for 1W+1L). Assert total_games=2.
- `test_win_rate_across_multiple_days`: Seed 5 games across 5 different days with same full_hash: 3 wins then 2 losses (chronologically). Assert data has 5 points. Final point win_rate = 3/5 = 0.6. First point = 1.0 (first game was a win).
- `test_empty_position_returns_empty_series`: Request with a hash matching no games. Assert series has 1 BookmarkTimeSeries with empty data, total_games=0.

**TestRecencyFilter** — Recency trimming:
- `test_recency_filter_trims_old_data`: Seed 3 games: 1 from 60 days ago, 2 from today. Use recency="month" (30 days). Assert data points only include dates from the last 30 days (should have points for today's 2 games only). Assert total_wins + total_draws + total_losses = count of games within recency window only.
- `test_rolling_window_uses_full_history_even_with_recency`: Seed 10 games: 8 old (>30 days) + 2 recent. Use recency="month". The rolling window for the recent games should still include the old games in its trailing window (computed over full history). Assert data points exist only for recent dates, but game_count may be > 2 (window includes pre-filter games).

**TestMultipleBookmarks** — Multi-bookmark request:
- `test_two_bookmarks_return_two_series`: Seed games for 2 different full_hashes. Create TimeSeriesRequest with 2 bookmarks. Assert response has 2 BookmarkTimeSeries, each with the correct bookmark_id.

Use user_id in 900-series range. For dates, use `datetime.datetime(2026, 3, 1, tz=datetime.timezone.utc)` etc. to ensure deterministic ordering.

Important implementation detail: `query_time_series` matches on `hash_column` (from match_side) and joins to Game on user_color (from the `color` param on the bookmark). The seed helper must set the correct `user_color` on the Game and the correct hash values on GamePosition.

TimeSeriesRequest/TimeSeriesBookmarkParam import paths:
```python
from app.schemas.openings import TimeSeriesRequest, TimeSeriesBookmarkParam
from app.services.openings_service import get_time_series, ROLLING_WINDOW_SIZE
```
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_openings_time_series.py -x -v</automated>
  </verify>
  <done>Openings time series tests pass. Rolling window produces correct win rates for single game, multiple games, and multi-day sequences. Recency filter trims output while preserving full-history rolling windows. Multi-bookmark request returns separate series.</done>
</task>

</tasks>

<verification>
All three test files pass independently:
```bash
uv run pytest tests/test_bookmarks_router.py tests/test_stats_service.py tests/test_openings_time_series.py -x -v
```

Full test suite still passes (no regressions):
```bash
uv run pytest -x
```

Type check passes:
```bash
uv run ty check app/ tests/
```
</verification>

<success_criteria>
- tests/test_bookmarks_router.py: 12+ router-level tests covering CRUD lifecycle, reorder, match-side, auth, and suggestions
- tests/test_stats_service.py: 8+ tests covering _rows_to_wdl_categories pure function + get_rating_history/get_global_stats with seeded data
- tests/test_openings_time_series.py: 7+ tests covering rolling window math, recency filtering, and multi-bookmark support
- All tests verify business logic correctness (WDL counts, percentages, window sizes), not just HTTP status codes
- Full test suite passes with zero failures
</success_criteria>

<output>
After completion, write summary to: .planning/quick/260403-kwm-write-meaningful-tests-for-the-biggest-c/260403-kwm-SUMMARY.md
</output>
