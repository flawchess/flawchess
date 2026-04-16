---
quick_id: 260416-vcx
type: execute
autonomous: true
files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameTimelineChart.tsx
  - tests/test_endgame_service.py
---

<objective>
Replace the per-type rolling-window series in the "Win Rate by Endgame Type" chart with weekly buckets (average win rate per ISO week, Monday-dated) to cut backend compute. The overall endgame-vs-non-endgame series is unchanged.

Purpose: the per-type chart currently runs a rolling window over every game, producing one point per game date and heavy aggregation work. Weekly buckets reduce output volume dramatically while preserving trend readability. Per-game binary outcomes make MEAN the correct aggregator (median is degenerate); orchestrator locked AVERAGE.

Output: backend service + schema update, frontend chart tooltip/popover/type update, unit tests for the new weekly aggregator.
</objective>

<context>
@CLAUDE.md
@app/schemas/endgames.py
@app/services/endgame_service.py
@frontend/src/types/endgames.ts
@frontend/src/components/charts/EndgameTimelineChart.tsx
@tests/test_endgame_service.py

<interfaces>
<!-- Key existing contracts the executor needs. Do NOT re-explore. -->

From app/schemas/endgames.py (current):
```python
class EndgameTimelinePoint(BaseModel):
    """Single data point in a per-type rolling-window time series."""
    date: str            # ISO date string "YYYY-MM-DD"
    win_rate: float      # 0.0-1.0
    game_count: int
    window_size: int     # <-- REMOVE in this change

class EndgameOverallPoint(BaseModel):
    # unchanged — overall series keeps rolling-window semantics
    date: str
    endgame_win_rate: float | None
    non_endgame_win_rate: float | None
    endgame_game_count: int
    non_endgame_game_count: int
    window_size: int

class EndgameTimelineResponse(BaseModel):
    overall: list[EndgameOverallPoint]
    per_type: dict[str, list[EndgameTimelinePoint]]   # <-- semantics change: weekly, not rolling
    window: int          # still used by overall series
```

From app/services/endgame_service.py (current):
```python
from app.services.openings_service import MIN_GAMES_FOR_TIMELINE, derive_user_result, recency_cutoff

def _compute_rolling_series(rows: list[Row[Any]], window: int) -> list[dict]:
    """Used for BOTH overall (keep) and per_type (replace with weekly)."""

async def get_endgame_timeline(..., window: int = 50, ...) -> EndgameTimelineResponse:
    # ...
    per_type: dict[str, list[EndgameTimelinePoint]] = {}
    for class_int, rows in per_type_rows.items():
        class_name = _INT_TO_CLASS[class_int]
        series = _compute_rolling_series(rows, window)    # <-- REPLACE with weekly helper for per_type
        per_type[class_name] = [
            EndgameTimelinePoint(
                date=pt["date"],
                win_rate=pt["win_rate"],
                game_count=pt["game_count"],
                window_size=pt["window_size"],            # <-- drop this field
            )
            for pt in series
            if not cutoff_str or pt["date"] >= cutoff_str
        ]
```

Row shape for per_type_rows (from query_endgame_timeline_rows): list of (played_at: datetime, result: str, user_color: str), ordered by played_at ASC.

`derive_user_result(result, user_color)` returns `Literal["win", "draw", "loss"]`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — add weekly aggregator, update per_type path, update schema</name>
  <files>
    app/schemas/endgames.py,
    app/services/endgame_service.py
  </files>
  <action>
**1. `app/schemas/endgames.py`:**
- In `EndgameTimelinePoint`: remove the `window_size: int` field. Update docstring to:
  `"""Single data point in the per-type weekly win-rate time series.

  Represents the average win rate (wins / games) for one endgame type over one
  ISO week. `date` is the Monday of that week as `YYYY-MM-DD`. A point is only
  emitted for weeks with at least MIN_GAMES_PER_WEEK games (see endgame_service)."""`
- Leave `EndgameOverallPoint`, `EndgameTimelineResponse`, and the `window: int` field unchanged (the overall series still uses rolling windows). Update the `EndgameTimelineResponse` docstring line for `per_type` to: `per_type: per-endgame-class weekly win-rate series (keys are EndgameClass strings).`

**2. `app/services/endgame_service.py`:**

Add a module-level constant near the top of the file (after `_MATERIAL_ADVANTAGE_THRESHOLD` or near `MIN_GAMES_FOR_CLOCK_STATS`):
```python
# Minimum games per ISO week to emit a point in the per-type weekly timeline.
# Lower than MIN_GAMES_FOR_TIMELINE (10) because weekly buckets are naturally
# smaller than rolling windows. Three games is enough for a meaningful average
# while still suppressing noise from single-game weeks.
MIN_GAMES_PER_WEEK = 3
```

Add a new helper alongside `_compute_rolling_series` (do NOT modify `_compute_rolling_series` — still used by overall):
```python
def _compute_weekly_series(
    rows: list[Row[Any]],
    min_games: int,
) -> list[dict]:
    """Compute a per-ISO-week average win-rate series from chronological game rows.

    Groups games by ISO week (Monday start, via `played_at.isocalendar()`).
    Emits one point per week where `games >= min_games`, dated to that week's
    Monday in `YYYY-MM-DD` form. Win rate = wins / games in the week.

    Args:
        rows: list of (played_at, result, user_color), ordered by played_at ASC
            (order doesn't affect correctness — week is derived from played_at).
        min_games: drop weeks with fewer than this many games.

    Returns:
        list of dicts with keys: date, win_rate, game_count.
        Sorted chronologically by date.
    """
    # Accumulate per (iso_year, iso_week): [wins, games, monday_date_str]
    # Using defaultdict keyed by (year, week) avoids recomputing Monday each game.
    buckets: dict[tuple[int, int], dict[str, Any]] = {}
    for played_at, result, user_color in rows:
        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        key = (iso_year, iso_week)
        if key not in buckets:
            # Monday of this ISO week = played_at shifted back (iso_weekday - 1) days.
            monday = (played_at - timedelta(days=iso_weekday - 1)).date()
            buckets[key] = {"wins": 0, "games": 0, "date": monday.isoformat()}
        outcome = derive_user_result(result, user_color)
        buckets[key]["games"] += 1
        if outcome == "win":
            buckets[key]["wins"] += 1

    out: list[dict] = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        games = b["games"]
        if games < min_games:
            continue
        out.append({
            "date": b["date"],
            "win_rate": round(b["wins"] / games, 4),
            "game_count": games,
        })
    return out
```

Add `from datetime import timedelta` to imports if not already present (check `datetime` is imported via stdlib — add alongside existing imports).

In `get_endgame_timeline`, replace the per-type loop body:
```python
per_type: dict[str, list[EndgameTimelinePoint]] = {}
for class_int, rows in per_type_rows.items():
    class_name = _INT_TO_CLASS[class_int]
    series = _compute_weekly_series(rows, MIN_GAMES_PER_WEEK)
    per_type[class_name] = [
        EndgameTimelinePoint(
            date=pt["date"],
            win_rate=pt["win_rate"],
            game_count=pt["game_count"],
        )
        for pt in series
        if not cutoff_str or pt["date"] >= cutoff_str
    ]
```

Leave everything else in `get_endgame_timeline` alone — the overall series still calls `_compute_rolling_series(endgame_rows, window)` and `_compute_rolling_series(non_endgame_rows, window)` with unchanged logic. The `window` parameter is still accepted, still forwarded to overall, and is silently not used for per_type (per orchestrator decision).

**Constants / conventions:**
- `MIN_GAMES_PER_WEEK = 3` is a named module constant (no magic number).
- All new functions carry full type annotations.
- Use `played_at.isocalendar()` (datetime method) — it returns a named tuple `(year, week, weekday)` where Monday=1, Sunday=7. `played_at - timedelta(days=iso_weekday - 1)` gives the Monday of that week.

**Import note:** `timedelta` needs to be imported from `datetime`. The file currently does not import `datetime` — add `from datetime import timedelta` at the top near other stdlib imports (after `import statistics`).
  </action>
  <verify>
    <automated>uv run ruff format app/schemas/endgames.py app/services/endgame_service.py &amp;&amp; uv run ruff check app/schemas/endgames.py app/services/endgame_service.py &amp;&amp; uv run ty check app/schemas/endgames.py app/services/endgame_service.py</automated>
  </verify>
  <done>
    - `EndgameTimelinePoint` no longer has `window_size` field.
    - `_compute_weekly_series` exists with docstring, type annotations, correct ISO-week Monday bucketing.
    - `MIN_GAMES_PER_WEEK = 3` module constant defined.
    - `get_endgame_timeline` per-type loop calls `_compute_weekly_series(rows, MIN_GAMES_PER_WEEK)` and omits `window_size` from `EndgameTimelinePoint(...)`.
    - `_compute_rolling_series` untouched; overall series still uses it.
    - ruff format/check passes; ty check passes with zero new errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Backend tests — add weekly-series unit tests, update per_type assertions</name>
  <files>tests/test_endgame_service.py</files>
  <action>
**1. Add a new test class** for `_compute_weekly_series` alongside the existing `TestComputeRollingSeries` (around line 397-475). Import the new symbol: add `_compute_weekly_series, MIN_GAMES_PER_WEEK` to the existing import block that already imports `_compute_rolling_series` (around line 25-35).

Add this test class (adapt fixtures to match the existing style — plain `(played_at, result, user_color)` tuples are accepted by the helper):

```python
class TestComputeWeeklySeries:
    """Unit tests for _compute_weekly_series helper (per-type weekly timeline)."""

    def test_empty_rows_returns_empty(self):
        assert _compute_weekly_series([], min_games=MIN_GAMES_PER_WEEK) == []

    def test_single_week_meeting_min_games_emits_one_point(self):
        # Monday 2026-04-13 through Sunday 2026-04-19 is one ISO week.
        # 3 games on Mon/Wed/Fri — all same week, all wins.
        rows = [
            (datetime(2026, 4, 13), "1-0", "white"),  # win
            (datetime(2026, 4, 15), "1-0", "white"),  # win
            (datetime(2026, 4, 17), "0-1", "black"),  # win (black wins)
        ]
        result = _compute_weekly_series(rows, min_games=3)
        assert len(result) == 1
        assert result[0]["date"] == "2026-04-13"  # Monday of that ISO week
        assert result[0]["game_count"] == 3
        assert result[0]["win_rate"] == 1.0

    def test_week_below_min_games_dropped(self):
        # 2 games in a week, min_games=3 -> no output.
        rows = [
            (datetime(2026, 4, 13), "1-0", "white"),
            (datetime(2026, 4, 14), "0-1", "white"),  # loss
        ]
        assert _compute_weekly_series(rows, min_games=3) == []

    def test_multi_week_chronological_monday_dates(self):
        # Week 1 (Mon 2026-04-06 - Sun 2026-04-12): 3 wins
        # Week 2 (Mon 2026-04-13 - Sun 2026-04-19): 3 losses
        # Week 3 (Mon 2026-04-20 - Sun 2026-04-26): 3 draws
        rows = [
            (datetime(2026, 4, 6), "1-0", "white"),
            (datetime(2026, 4, 8), "1-0", "white"),
            (datetime(2026, 4, 12), "1-0", "white"),   # Sunday still week 1
            (datetime(2026, 4, 13), "0-1", "white"),   # loss
            (datetime(2026, 4, 15), "0-1", "white"),
            (datetime(2026, 4, 17), "0-1", "white"),
            (datetime(2026, 4, 20), "1/2-1/2", "white"),  # draw
            (datetime(2026, 4, 22), "1/2-1/2", "white"),
            (datetime(2026, 4, 24), "1/2-1/2", "white"),
        ]
        result = _compute_weekly_series(rows, min_games=3)
        assert [pt["date"] for pt in result] == ["2026-04-06", "2026-04-13", "2026-04-20"]
        assert result[0]["win_rate"] == 1.0
        assert result[1]["win_rate"] == 0.0
        assert result[2]["win_rate"] == 0.0
        assert all(pt["game_count"] == 3 for pt in result)

    def test_win_rate_is_average_of_wins_over_games(self):
        # Week with 4 games: 1 win, 2 draws, 1 loss -> win_rate = 0.25
        rows = [
            (datetime(2026, 4, 13), "1-0", "white"),       # win
            (datetime(2026, 4, 14), "1/2-1/2", "white"),   # draw
            (datetime(2026, 4, 15), "1/2-1/2", "white"),   # draw
            (datetime(2026, 4, 16), "0-1", "white"),       # loss
        ]
        result = _compute_weekly_series(rows, min_games=3)
        assert len(result) == 1
        assert result[0]["win_rate"] == 0.25
        assert result[0]["game_count"] == 4
```

Ensure `from datetime import datetime` is imported at the top of the test file if not already.

**2. Update per_type assertions** in existing `TestGetEndgameTimeline` class (around lines 565-750):
- Any assertion that reads `.window_size` on a per_type point must be removed. The `EndgameTimelinePoint` no longer carries that field.
- Any assertion that expects rolling-window semantics on per_type (e.g. "point emitted per game date" or "game_count equals rolling window total") must be reworked to weekly semantics: points land on Mondays, game_count is that week's total.
- The specific test `test_per_type_keys_are_endgame_class_strings` (line ~702): its rook fixture is likely a single row producing one rolling point. With weekly aggregation this would need 3 games in one ISO week to emit a point. Adjust the fixture to 3 rows in the same ISO week (e.g. Mon/Wed/Fri of 2026-04-13 week, all wins), then assert `result.per_type["rook"][0].win_rate == 1.0` and `result.per_type["rook"][0].date == "2026-04-13"`.
- The tests that mock `query_endgame_timeline_rows` with `([], [], {1: [], 2: [], ...})` (empty per_type) still work unchanged — empty rows produce empty weekly series.
- Tests that check the OVERALL series (endgame_rows / non_endgame_rows going through `_compute_rolling_series`) must stay unchanged. Only per_type assertions shift.

Do NOT change `TestComputeRollingSeries` (lines ~397-475) — that helper is still used for the overall series.

**3. `tests/test_aggregation_sanity.py`:** `TestRollingWindowBoundaries` (line 213) tests `MIN_GAMES_FOR_TIMELINE=10` semantics. Read it first to determine whether it exercises the overall or per_type path. If its assertions go through the overall series (endgame_rows / non_endgame_rows), no change. If it asserts on per_type with rolling-window game_count behavior, either (a) scope it to overall-only by filtering `result.overall`, or (b) split into one overall test + one new weekly test that respects `MIN_GAMES_PER_WEEK=3`. Document the choice in a brief comment on the test.

**4. `tests/test_endgame_repository.py`:** the repository layer itself is unchanged, but grep for `window_size` assertions — if any check `window_size` on per_type response rows, remove those asserts (the field is gone from the schema). Repository row-shape assertions stand.

**Scope guard:** do NOT introduce broader test refactors. Minimal edits to keep the existing suite green under the new semantics.
  </action>
  <verify>
    <automated>uv run pytest tests/test_endgame_service.py tests/test_aggregation_sanity.py tests/test_endgame_repository.py -x</automated>
  </verify>
  <done>
    - `TestComputeWeeklySeries` class added with the four unit tests listed.
    - Existing per_type assertions in `TestGetEndgameTimeline` updated to weekly semantics; `window_size` reads removed.
    - Overall-series tests untouched and still passing.
    - `test_endgame_repository.py` passes (any `window_size` assertions on per_type rows removed).
    - `test_aggregation_sanity.py::TestRollingWindowBoundaries` passes — scoped to overall or split into overall+weekly as needed.
    - `uv run pytest tests/test_endgame_service.py tests/test_aggregation_sanity.py tests/test_endgame_repository.py -x` is green.
  </done>
</task>

<task type="auto">
  <name>Task 3: Frontend — update types, chart tooltip, popover text</name>
  <files>
    frontend/src/types/endgames.ts,
    frontend/src/components/charts/EndgameTimelineChart.tsx
  </files>
  <action>
**1. `frontend/src/types/endgames.ts`:**
- In `EndgameTimelinePoint` (lines 64-69): remove the `window_size: number;` field. Add a brief JSDoc:
  ```ts
  /** Single data point in the per-type weekly win-rate time series.
   *  `date` is the Monday of an ISO week (YYYY-MM-DD). `win_rate` is wins / games
   *  in that week. Only weeks with at least 3 games are emitted. */
  export interface EndgameTimelinePoint {
    date: string;
    win_rate: number;
    game_count: number;
  }
  ```
- Leave `EndgameOverallPoint` (still has `window_size`) and `EndgameTimelineResponse` unchanged.

**2. `frontend/src/components/charts/EndgameTimelineChart.tsx`:**

At line ~84, inside the `allTypeDates.map` builder, remove the `window_size` assignment:
```ts
// BEFORE
if (found) {
  point[key] = found.win_rate;
  point[`${key}_game_count`] = found.game_count;
  point[`${key}_window_size`] = found.window_size;   // <-- REMOVE
}

// AFTER
if (found) {
  point[key] = found.win_rate;
  point[`${key}_game_count`] = found.game_count;
}
```

At line ~113, update the `InfoPopover` body:
```tsx
<InfoPopover ariaLabel="Win Rate by Endgame Type info" testId="timeline-per-type-info" side="top">
  Win rate per week for each endgame type. Only weeks with at least 3 games are shown. Click legend items to toggle individual series.
</InfoPopover>
```

At line ~150, update the tooltip game-count suffix:
```tsx
// BEFORE
<span className="text-muted-foreground ml-1">(past {gameCount} games)</span>

// AFTER
<span className="text-muted-foreground ml-1">({gameCount} games this week)</span>
```

Leave `connectNulls={true}`, the legend-toggle behavior, the Y-axis ticks, the X-axis formatter, and every other aspect of the component untouched. No layout change; change is tooltip string + popover copy + dropping the `_window_size` field from the merged data row.

Keep the small paragraph at line ~117-119 ("Win rate trend over time, per endgame type.") as-is — still accurate.

**Conventions honored:**
- No magic numbers — the "3 games" threshold in copy matches the backend constant; no numeric constant on the frontend side (pure user-facing string).
- Mobile: no layout change, works as-is.
- `data-testid` attributes untouched.
- No em-dashes introduced in user-facing copy.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run build</automated>
  </verify>
  <done>
    - `EndgameTimelinePoint` on the frontend no longer has `window_size`.
    - Chart component no longer reads `found.window_size` nor writes `point[`${key}_window_size`]`.
    - Tooltip reads `({N} games this week)`.
    - Info popover text updated to weekly + 3-game threshold + "Click legend items..." sentence preserved.
    - `npm run build` passes (TypeScript compile succeeds under `noUncheckedIndexedAccess`).
  </done>
</task>

</tasks>

<verification>
- `uv run ruff format .` and `uv run ruff check .` pass.
- `uv run ty check app/ tests/` passes.
- `uv run pytest` passes (full suite, not just the three touched files).
- `cd frontend && npm run build` and `cd frontend && npm run lint` pass.
- Manual smoke (human optional): load the Endgames tab, confirm "Win Rate by Endgame Type" chart renders with one data point per week (roughly — depending on import density), tooltip reads "(N games this week)", popover reads the new copy.
</verification>

<success_criteria>
- Per-type series in `data.per_type` carries weekly-aggregated points with one entry per ISO week meeting `MIN_GAMES_PER_WEEK = 3`; each `date` is the Monday of that week.
- `EndgameTimelinePoint` no longer has `window_size` on either backend or frontend.
- The overall endgame-vs-non-endgame chart (`data.overall`) is unchanged in behavior, schema, and computation.
- All backend and frontend type checks, lint, and tests green.
- Frontend chart renders with updated tooltip and popover copy.
</success_criteria>

<output>
After completion, create `.planning/quick/260416-vcx-use-weekly-datapoints-with-median-win-ra/260416-vcx-SUMMARY.md` using the standard quick-task summary template.
</output>
