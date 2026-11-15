---
phase: quick-261115-ntq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/stats_repository.py
  - app/repositories/openings_repository.py
  - app/services/openings_service.py
  - app/schemas/openings.py
  - tests/test_openings_time_series.py
  - tests/test_openings_repository.py
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/pages/openings/useOpeningRowTimeSeries.ts
  - frontend/src/components/openings/stats/RepertoireCard.tsx
  - frontend/src/components/openings/__tests__/RepertoireList.test.tsx
  - frontend/src/components/charts/ScoreChart.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/components/charts/__tests__/ScoreChart.test.tsx
  - CHANGELOG.md
autonomous: true
requirements: [SEED-261115-sgs]

estimate:
  tokens: 110000
  raw_tokens: 110000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Opening the Score over time chart on any repertoire card (most-played or bookmark) fetches that one opening's series on demand with the eval-expected series; the Stats page's up-front bookmark request never runs the middlegame-entry eval join (owner constraint OC-1, branch (b) selected by measurement)"
    - "The chart's primary line is the expected score from opening eval: per game, the middlegame-entry eval (first phase=1 row, user perspective, mate handled) converted to expected score, then averaged over the trailing up-to-100-game window; never the converted mean eval (SEED-LD-1)"
    - "Games without a middlegame-entry eval are skipped in the expected average but kept in the actual score, and the tooltip shows the eval game count (SEED-LD-4)"
    - "Points are still emitted once the window holds 10 games (MIN_GAMES_FOR_TIMELINE); no 100-game floor (SEED-LD-1)"
    - "Actual score is drawn as a fainter secondary line on the same axis; the dashed reference line sits at the colour baseline (about 52.3% White, 47.7% Black) and the typical band is gone (SEED-LD-2)"
    - "The legend names the lines 'Expected score from opening eval' and 'Actual score', the chart title stays 'Score over time', and one popover sentence explains the level gap; copy says eval, never pawns (SEED-LD-3, SEED-LD-5)"
    - "The card's shared score verdict fields (score, confidence, p-value, CI) stay on actual score"
  artifacts:
    - path: app/repositories/stats_repository.py
      provides: "middlegame_entry_subquery(game_ids) — the single definition of the per-game middlegame-entry row, used by the opening eval batch and the timeline"
    - path: app/repositories/openings_repository.py
      provides: "query_time_series(..., include_mg_entry_eval) returning (played_at, result, user_color, eval_cp, eval_mate); _build_time_series_stmt for EXPLAIN"
    - path: app/services/openings_service.py
      provides: "ROLLING_WINDOW_SIZE = 100, per-game expected score, rolling expected series, expected_score_baseline"
    - path: app/schemas/openings.py
      provides: "TimeSeriesRequest.include_expected_score, TimeSeriesPoint.expected_score / eval_game_count, BookmarkTimeSeries.expected_score_baseline"
    - path: frontend/src/pages/openings/useOpeningRowTimeSeries.ts
      provides: "per-opening on-demand series request for bookmark and most-played rows, with include_expected_score true"
    - path: frontend/src/components/charts/ScoreChart.tsx
      provides: "two-line chart, baseline reference line, legend, tooltip, info popover"
  key_links:
    - from: app/repositories/openings_repository.py
      to: app/repositories/stats_repository.py
      via: "middlegame_entry_subquery (same DISTINCT ON phase=1 row as the avg-eval pillar)"
      pattern: "middlegame_entry_subquery"
    - from: app/services/openings_service.py
      to: app/services/eval_utils.py
      via: "eval_cp_to_expected_score / eval_mate_to_expected_score per game"
      pattern: "eval_mate_to_expected_score"
    - from: frontend/src/pages/openings/useOpeningRowTimeSeries.ts
      to: "POST /openings/time-series"
      via: "include_expected_score: true on the per-opening request"
      pattern: "include_expected_score: true"
    - from: frontend/src/components/charts/ScoreChart.tsx
      to: app/schemas/openings.py
      via: "series.expected_score_baseline drives the reference line"
      pattern: "expected_score_baseline"
---

<objective>
Implement SEED-261115-sgs: on the per-opening "Score over time" chart (Openings stats page, expanded repertoire card), the eval-expected score over a rolling 100-game window becomes the primary line and the actual score becomes a fainter secondary line on the same axis. Honour the seed's five locked owner decisions (cited below as SEED-LD-1..5) and the owner's loading constraint OC-1. Scope is exactly the seed's: no other refactors.

Purpose: the rolling-50 actual-score line is mostly chance (about 95% noise in the benchmark population). The eval-expected line has similar real drift but about 2.5x less noise, so it answers "is this opening holding up" far better.

Output: an opt-in eval-expected series on POST /openings/time-series, on-demand per-opening chart loading for every repertoire card, and a two-line ScoreChart with a colour-baseline reference line, legend, tooltip and info popover.

## How the timeline loads today (live observation, 2026-11-15)

- Most-played rows (the bulk of the cards) are already on demand: `useOpeningRowTimeSeries` sends a one-opening POST /openings/time-series only when the card's chart is opened (the ScoreOverTime block mounts on open).
- Bookmark rows are front-loaded: `useOpeningsChartData` sends one table-wide POST /openings/time-series with every bookmark on page load. That series also feeds the bookmark card's totals, score verdict fields, `is_current` and `last_played_at` (`useRepertoireRows.bookmarkRow`), so the table-wide request itself must stay. Today the bookmark card's chart reuses those front-loaded points.

## Front-load vs on-demand decision (OC-1), measured at planning time

Decision rule: keep front-loading only if, on the heaviest dev user that has bookmarks, adding the eval series to the table-wide bookmark request adds at most 250 ms AND at most 25% to the median service time (median of 4 interleaved warm rounds, `get_time_series` over all of that user's bookmarks). Otherwise load the eval series on demand.

Planning measurement (read-only, dev DB, `get_time_series` before vs a prototype that LEFT JOINs the existing DISTINCT ON phase=1 selection; 4 interleaved rounds after one warm-up each, run twice). Service time is the endpoint's work; HTTP, auth and serialization are unchanged apart from two extra fields per point.

| User | Games | Bookmarks | Before (median) | With eval series (median) | Added |
|---|---|---|---|---|---|
| 7 (heaviest) | 67,244 | 5 (largest openings 5,620 and 5,046 games) | 1,041 ms / 871 ms | 2,846 ms / 2,183 ms | +1,805 ms (+173%) / +1,312 ms (+151%) |
| 28 | 5,295 | 10 | 1,136 ms | 1,279 ms | +143 ms (+13%) |

EXPLAIN (ANALYZE, BUFFERS), user 7, per opening: bookmark 41 (5,620 games) 433 ms (shared hit 19.6k, read 10.9k) before vs 663 ms (hit 52.3k, read 31.4k, temp 411 blocks) with the join; bookmark 48 (5,046 games) 355 ms vs 577 ms. The join reads every phase=1 row of the matched games through `ix_game_positions_game_id` and external-merge sorts about 209k rows to keep the first per game. The very first cold run of the joined query took about 3.2 s. Adding a `user_id` predicate to the phase=1 selection made it slower (1.15 to 1.3 s), so do not add one.

Verdict: user 7 fails both thresholds by a wide margin, so **branch (b), on-demand, is selected**. Only branch (b) is planned. Branch (a) (front-load the eval series with the table-wide request) is rejected by the numbers above.

Branch (b) shape: the table-wide bookmark request keeps today's query and payload cost (`include_expected_score` defaults to false, so no join). Every card's chart, bookmark and most-played alike, sends its own one-opening request with `include_expected_score: true` when the chart is opened, with the existing loading and error states. The per-opening on-demand cost for the heaviest opening is about 0.6 to 0.7 s of DB time warm.

Not adopted: a LATERAL "first phase=1 row by ply" over the primary key measured about 0.5 s total, but it would be a second definition of the middlegame-entry row. The brief requires reusing the existing selection. It stays an owner option if the on-demand latency ever bothers anyone.

## Discretion choices (documented)

- Mate handling follows endgame_service's entry-eval convention: mate takes precedence over cp and maps to exactly 0 or 1 via `eval_mate_to_expected_score`; otherwise `eval_cp_to_expected_score`. Rows with |cp| >= 2000 are kept, since the sigmoid is bounded. The avg-eval pillar trims them only because they distort a cp mean.
- The expected line uses the same 10-game floor as the actual line, but on its own eval-game count. A point whose window holds fewer than 10 games with an eval carries `expected_score: null` (a gap in the line), while the actual score point is still emitted.
- Secondary line colour: neutral grey with alpha, thinner stroke, so it reads as context next to the blue primary.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/SEED-261115-sgs-opening-chart-eval-expected-primary-line.md
@CLAUDE.md
@frontend/CLAUDE.md
@app/services/openings_service.py
@app/repositories/openings_repository.py
@app/repositories/stats_repository.py
@app/services/eval_utils.py
@app/services/opening_eval.py
@app/schemas/openings.py
@frontend/src/components/charts/ScoreChart.tsx
@frontend/src/pages/openings/useOpeningRowTimeSeries.ts
@frontend/src/components/openings/stats/RepertoireCard.tsx
@frontend/src/types/position_bookmarks.ts

Interfaces the executor needs (read at planning time):
- `query_time_series(session, user_id, hash_column, target_hash, color, time_control=None, platform=None, rated=None, opponent_type="human", opponent_gap_min=None, opponent_gap_max=None) -> list[Row[Any]]` currently selects (played_at, result, user_color), DISTINCT ON Game.id, through `apply_game_filters` with dates pinned to None, then wraps it in a subquery ordered by played_at ASC.
- In `query_opening_phase_entry_metrics_batch`, the middlegame-entry row is the `phase_entry` subquery: GamePosition.game_id / eval_cp / eval_mate WHERE phase == 1 AND game_id IN (select dedup.game_id), DISTINCT ON game_id ORDER BY game_id, ply. eval_cp and eval_mate are white-perspective.
- `eval_cp_to_expected_score(eval_cp, user_color)` and `eval_mate_to_expected_score(eval_mate, user_color)` take white-perspective input and `Literal["white", "black"]`.
- `resolve_eval_baseline_pawns(color)` in opening_eval.py returns the user-perspective baseline in pawns (+0.25 White, -0.25 Black; None means White). `CENTIPAWNS_PER_PAWN` is defined there.
- `_build_bookmark_time_series(bookmark_id, rows, from_date, to_date, cutoff)` unpacks 3-tuples. `get_time_series` loops bookmarks sequentially (no gather, CLAUDE.md).
- FE `resolveMatchSide(matchSide, color)` in `frontend/src/types/api.ts` maps both→full, mine→colour, opponent→other colour. `useTimeSeries(req)` keys on `['timeSeries', req]`. `MOST_PLAYED_ROW_SERIES_ID = 0`.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): opt-in eval-expected series end-to-end through repository, service and API schema, plus the post-change measurement</name>
  <files>app/repositories/stats_repository.py, app/repositories/openings_repository.py, app/services/openings_service.py, app/schemas/openings.py, tests/test_openings_time_series.py, tests/test_openings_repository.py</files>
  <precondition>The executor works in an isolated git worktree off main, not the main checkout (STATE.md shows Phase 254 executing there; the seed's isolation note). In a fresh worktree, run `uv sync --group maia-inference` and `npm --prefix frontend ci` first. The dev Postgres container (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`) is running.</precondition>
  <behavior>
    - include_expected_score=True: 12 white-user games through the bookmark hash, each with a phase=1 row at ply 20 (eval_cp +100) and a later phase=1 row at ply 21 (eval_cp -300). The last point's expected_score is about 0.5914 (sigmoid of LICHESS_K x 100; compute it in the test from LICHESS_K) and eval_game_count is 12. This proves the first phase=1 row by ply is used.
    - Convert-then-average: 12 games whose MG-entry evals alternate +400 and 0 give the mean of the per-game expected scores (about 0.6568), not the expected score of the mean eval (about 0.6762).
    - Black user, white-perspective eval_cp +100 gives an expected score of about 0.4086.
    - Mate: eval_mate +3 for a white user counts as 1.0, eval_mate -3 for a black user counts as 1.0, and mate wins over a present eval_cp.
    - Games without an eval (no phase=1 row, or a phase=1 row with both evals NULL) are skipped. For example, 12 eval games plus 3 without give eval_game_count 12, game_count 15, and an actual score over all 15.
    - Floor: 12 games of which 5 have an eval give an emitted point (game_count 12) with expected_score None.
    - Window is 100: 110 games give game_count == ROLLING_WINDOW_SIZE == 100 on the last point.
    - Default request (flag omitted): points carry expected_score None and eval_game_count 0 even when evals exist, so the table-wide request skips the join.
    - expected_score_baseline is about 0.5230 for a white bookmark and about 0.4770 for a black one (compute from LICHESS_K and the EVAL_BASELINE_PAWNS_* constants in the test).
    - User scoping: another user's game on the same hash with a phase=1 eval does not change eval_game_count.
  </behavior>
  <action>
Step 0, baseline (before any code change): record `git rev-parse HEAD` and re-observe the heaviest dev user that has bookmarks, read-only: games per user joined with position_bookmarks, and that user's bookmarks (id, target_hash, color, match_side). Planning observed user 7 with 5 bookmarks. Copy the planning measurement table and the OC-1 decision rule from this plan's objective into SUMMARY.md.

1. stats_repository.py: extract the existing `phase_entry` subquery of `query_opening_phase_entry_metrics_batch` into a public helper `middlegame_entry_subquery(game_ids, name="phase_entry")`. It takes a one-column Select of game ids and returns a Subquery with columns game_id, eval_cp, eval_mate. Keep the exact predicates and ordering (phase == 1, game_id IN the given select, DISTINCT ON game_id ORDER BY game_id, ply) and no user_id predicate (measured slower). Its docstring states it is the single definition of the per-game middlegame-entry row: eval is after that move, white-perspective, the same row as the avg-eval pillar. Call it from `query_opening_phase_entry_metrics_batch` so that query's SQL is unchanged; its tests must pass untouched. Do not write a second selection (brief: reuse the existing one).

2. openings_repository.py: split the statement building out of `query_time_series` into `_build_time_series_stmt(...)` (same parameters plus keyword `include_mg_entry_eval: bool = False`) so a script can compile and EXPLAIN the real statement. `query_time_series` gains the same keyword, executes the built statement and returns rows (played_at, result, user_color, eval_cp, eval_mate) ordered by played_at ASC.
   - The matched-games select adds Game.id labelled game_id and is otherwise unchanged (DISTINCT ON Game.id, ply <= MAX_EXPLORER_PLY, played_at not null, `apply_game_filters` with dates pinned to None).
   - Flag false: keep today's shape (matched select as a subquery, outer select ordered by played_at) and add two NULL columns labelled eval_cp and eval_mate (sqlalchemy `null()`), so the table-wide bookmark request gets no join and no new plan nodes.
   - Flag true: make the matched select a CTE named ts_matched. Call `middlegame_entry_subquery(select(ts_matched.c.game_id))` and LEFT OUTER JOIN it on game_id, so games without a phase=1 row keep a row with NULL evals. Order by played_at ASC.
   - Update the docstring. Filters stay solely in `apply_game_filters`; no SQL in the service.

3. schemas/openings.py:
   - `TimeSeriesRequest.include_expected_score: bool = False`, with a comment: the per-opening chart request sets it; the table-wide bookmark request leaves it false, because the join added +1.3 to +1.8 s for the heaviest dev user (OC-1).
   - `TimeSeriesPoint.expected_score: float | None = None`: mean per-game expected score over the window's games with a middlegame-entry eval; None when not requested or when fewer than MIN_GAMES_FOR_TIMELINE eval games.
   - `TimeSeriesPoint.eval_game_count: int = 0`.
   - `BookmarkTimeSeries.expected_score_baseline: float`: the colour baseline on the expected-score scale.
   - Update the window comments from 50 to ROLLING_WINDOW_SIZE wording.

4. openings_service.py:
   - Set `ROLLING_WINDOW_SIZE = 100` (SEED-LD-1); MIN_GAMES_FOR_TIMELINE stays 10.
   - Add `_game_expected_score(eval_cp, eval_mate, user_color) -> float | None`, following the mate convention in the objective. Narrow the str user_color to the Literal explicitly rather than using a ty ignore.
   - Add `_rolling_expected_score(expected_so_far) -> tuple[float | None, int]`: the last ROLLING_WINDOW_SIZE entries, drop None, return (mean or None below MIN_GAMES_FOR_TIMELINE, eval count). Convert per game, then average; never convert a mean eval (SEED-LD-1, SEED-LD-4).
   - Add `_expected_score_baseline(color) -> float`: `resolve_eval_baseline_pawns(color)` x CENTIPAWNS_PER_PAWN, rounded to cp, through `eval_cp_to_expected_score` with user_color "white". Comment that the baseline is already user-perspective, so "white" means no sign flip (SEED-LD-2).
   - `_build_bookmark_time_series` gains an `expected_score_baseline` parameter and unpacks the 5-column rows. Every game appends to a parallel expected list (warm-up included), and each point gets expected_score (rounded to 4 places like score) and eval_game_count.
   - `get_time_series` passes `include_mg_entry_eval=request.include_expected_score` and the per-bookmark baseline.
   - The shared score verdict fields stay on actual totals (seed note). Refresh the docstrings that say rolling-50.
   - Keep nesting depth <= 3.

5. Tests:
   - Add a `TestEvalExpectedSeries` class to tests/test_openings_time_series.py covering the behavior list. Extend the seed helper with keyword-only middlegame-entry eval options that insert phase=1 GamePosition rows at distinct plies (the PK is user_id, game_id, ply), and add `include_expected_score` to `_make_request`.
   - In tests/test_openings_repository.py, update the two tuple unpackings of query_time_series rows (`for month_dt, result, user_color in rows` and `_, _, user_color = rows[0]`) to the 5-column shape.
   - Write the tests first and watch them fail, then implement.

6. Post-change measurement (read-only, record everything in SUMMARY.md). Write `temp/261115-ntq/measure_timeline.py` (gitignored). It imports `app.models`, `app.models.user` and `app.models.oauth_account` first, because without them the ORM raises NoReferencedTableError on games.user_id. It uses `app.core.database.async_session_maker`, never reads .env files and ends with a rollback. For the step-0 user:
   - (i) `get_time_series` over all bookmarks, include_expected_score false vs true: one warm-up each, then 4 interleaved rounds, report the medians. The false arm is the shipped front-loaded request; the true arm reproduces the rejected branch (a).
   - (ii) the heaviest single bookmark with include_expected_score true (the on-demand chart request): 4 rounds, report the median.
   - (iii) EXPLAIN (ANALYZE, BUFFERS) on `_build_time_series_stmt` compiled with the postgresql dialect and literal_binds, for the heaviest bookmark, both flags. Record Execution Time and the top Buffers line.
   - Run with `uv run python temp/261115-ntq/measure_timeline.py`.
   - Expected: the false-arm plan contains no phase = 1 filter, and its median stays within about 25% of the planning "before" medians (871 to 1,041 ms on user 7; dev timing drifts by about 12%). The true arm re-confirms the OC-1 verdict.
   - Halt and report, without further optimising, if the on-demand single-opening median is above 1,500 ms warm or the false arm shows a phase = 1 scan.
   - Write the chosen branch (b), the planning numbers and these numbers into SUMMARY.md.
  </action>
  <verify>
    <automated>uv run pytest tests/test_openings_time_series.py tests/test_openings_repository.py tests/test_stats_repository_phase_entry.py -n auto -x && uv run ty check app/ tests/ scripts/ && uv run ruff check app/ tests/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && grep -q 'ROLLING_WINDOW_SIZE = 100' app/services/openings_service.py && uv run python temp/261115-ntq/measure_timeline.py</automated>
  </verify>
  <done>The backend returns the eval-expected series only when include_expected_score is true, with first-phase=1-row selection, mate handling, convert-then-average, eval-less games skipped, the 10-game floor per line, a 100-game window and the colour baseline, all covered by passing tests. The phase-entry batch tests pass unchanged. SUMMARY.md records the planning and post-change numbers and branch (b).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: on-demand per-opening chart loading for bookmark and most-played cards</name>
  <files>frontend/src/types/position_bookmarks.ts, frontend/src/pages/openings/useOpeningRowTimeSeries.ts, frontend/src/components/openings/stats/RepertoireCard.tsx, frontend/src/components/openings/__tests__/RepertoireList.test.tsx</files>
  <behavior>
    - A most-played row's hook request is the one-opening full-hash request (as today) plus include_expected_score true.
    - A bookmark row (row.bookmark set) now requests its own series once the hook mounts: bookmark_id = the bookmark's id, target_hash, match_side = resolveMatchSide(bookmark.match_side, row colour), color, include_expected_score true. The hook returns the series whose bookmark_id matches that id, not the front-loaded row.series.
    - Without an open chart, no card issues a per-row request (the existing "no per-row request" assertion on the bookmark card still holds; only its comment changes).
    - Loading shows the existing "Loading score chart..." line. An error shows the existing LoadError ("Failed to load the score chart") for bookmark cards too.
  </behavior>
  <action>
Per OC-1 branch (b):
- position_bookmarks.ts: add `include_expected_score?: boolean` to TimeSeriesRequest. Add `expected_score: number | null` and `eval_game_count: number` to TimeSeriesPoint, and `expected_score_baseline: number` to BookmarkTimeSeries, with comments mirroring the backend schema.
- useOpeningRowTimeSeries.ts:
  - Always build the one-opening request (remove the row.series short-circuit). With row.bookmark, use the bookmark's id, target_hash and resolveMatchSide(match_side, row.color). Without it, use MOST_PLAYED_ROW_SERIES_ID, row.fullHash and 'full' as today.
  - Spread timeSeriesFilterParams(debouncedFilters) and set include_expected_score true.
  - Return the series with the matching bookmark_id, plus isLoading and isError from the query.
  - Rewrite the docstring: every card fetches its chart series on demand, because the eval series is too costly to front-load (OC-1 numbers). Bookmark rows keep the front-loaded series for their totals and verdict fields only.
- Leave the table-wide request in useOpeningsChartData untouched: no flag, so the default false keeps the page-load cost unchanged.
- RepertoireCard.tsx: only update the ScoreOverTime doc comment to describe the two lines and on-demand loading. Its loading and error branches already satisfy frontend/CLAUDE.md (isError handled before loading or empty).
- RepertoireList.test.tsx:
  - Replace the hook test "returns a bookmark row's own series and never requests one" with one asserting the bookmark request shape. Include a match_side 'mine' bookmark resolving to the row colour.
  - Extend the most-played request expectation with include_expected_score true.
  - Add a bookmark-card test: opening the chart issues the per-row request and an error renders the chart error.
  - Add expected_score, eval_game_count and expected_score_baseline to the series fixtures, and window_size 100.
  - Write the tests first and watch them fail.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- src/components/openings/__tests__/RepertoireList.test.tsx && npm --prefix frontend run build && grep -q 'include_expected_score: true' frontend/src/pages/openings/useOpeningRowTimeSeries.ts</automated>
  </verify>
  <done>Every repertoire card's chart loads its own series on demand with the eval series, through the existing loading and error states. The page-load bookmark request is unchanged. The tests and `tsc -b` pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: two-line ScoreChart with colour-baseline reference, legend, tooltip and popover; CHANGELOG</name>
  <files>frontend/src/components/charts/ScoreChart.tsx, frontend/src/lib/theme.ts, frontend/src/components/charts/__tests__/ScoreChart.test.tsx, CHANGELOG.md</files>
  <behavior>
    - Two series lines render: expected_score (primary) and score (secondary).
    - No reference area and no "typical" watermark text render; a dashed reference line renders.
    - The legend shows "Expected score from opening eval" and "Actual score" (testids `${testId}-legend`, `${testId}-legend-expected`, `${testId}-legend-actual`).
    - The info popover trigger `${testId}-info` renders.
    - Volume bars, inactivity-gap annotations and the empty state behave as before.
  </behavior>
  <action>
- theme.ts: rename SCORE_OVER_TIME_LINE to SCORE_OVER_TIME_EXPECTED_LINE (same value; ScoreChart is its only consumer) with a comment marking it as the primary eval-expected line. Add SCORE_OVER_TIME_ACTUAL_LINE = 'oklch(0.75 0 0 / 0.55)' for the fainter secondary actual-score line.
- ScoreChart.tsx (SEED-LD-2, SEED-LD-3, SEED-LD-4, SEED-LD-5):
  - Drop the typical band: remove the band ReferenceArea, its watermark shape, the mask hook and the mask on the reference line. Remove the verdict-band import and the now-unused even-score and band constants. The watermark component and hook stay, since other charts use them.
  - Move the dashed reference line to y = series.expected_score_baseline.
  - Build the y axis from the actual scores, the non-null expected scores and the baseline.
  - Render the actual line first (dataKey score, SCORE_OVER_TIME_ACTUAL_LINE, named width constant 1.5, name "Actual score"). Render the expected line on top (dataKey expected_score, SCORE_OVER_TIME_EXPECTED_LINE, width 2, name "Expected score from opening eval"). Both have no dots and no animation. Null expected points leave a gap.
  - Tooltip body: the week line, "Expected score from opening eval: N%" with the muted count "(N games with an eval)", or the muted "not enough games with an eval" when null. Then "Actual score: N%" with "(past N games)", then the volume line as today.
  - Below the chart, add a small legend sub-component. It shows two line swatches (h-0.5 w-4, colours from theme.ts) with the two names in text-sm, plus an InfoPopover (testId `${testId}-info`, ariaLabel "Score over time info") on the same row. The popover body can use text-xs.
  - Popover copy, no em-dashes, "eval" never "pawns":
    - It defines the expected line as the expected score from the eval of the position you reach out of the opening, averaged over your last {window_size} games in this opening (take window_size from the first point; no hard-coded 100).
    - It says the dashed line is the typical value for your colour.
    - It includes the level-gap sentence (SEED-LD-3): the expected line reflects only the position reached out of the opening, so your actual score can sit above or below it.
  - The chart title stays "Score over time" (the card toggle label, unchanged).
  - Keep max-depth <= 4 and use named constants, no magic numbers.
- ScoreChart.test.tsx:
  - Update makeSeries with expected_score, eval_game_count, window_size 100 and expected_score_baseline.
  - Replace the typical-band test with the behavior list: two `.recharts-line` series, no `.recharts-reference-area`, no "typical" text, a `.recharts-reference-line`, the legend names and the info testid.
  - Write the tests first and watch them fail.
- CHANGELOG.md: under `## [Unreleased]` → `### Changed`, add one user-facing bullet. Openings: the Score over time chart on each opening card now leads with your expected score from the opening eval over your last 100 games in that opening, with your actual score as a fainter second line. The dashed line marks the typical expected score for your colour, and the chart loads when you open it. No em-dash.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- src/components/charts/__tests__/ScoreChart.test.tsx src/components/openings/__tests__/RepertoireList.test.tsx && npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend run knip && grep -q "Expected score from opening eval" frontend/src/components/charts/ScoreChart.tsx</automated>
  </verify>
  <done>The chart shows the eval-expected primary line and the fainter actual line on one axis, with a dashed colour-baseline line and no typical band. The legend, the tooltip with eval game count and the level-gap popover all render. Lint, build, knip and tests pass, and the CHANGELOG bullet is under [Unreleased].</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → POST /openings/time-series | Authenticated user sends bookmark hashes, filters and the new include_expected_score flag |
| service → game_positions | The phase=1 selection runs over game ids from the user-scoped matched set |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ntq-01 | I | openings_repository flag-true statement | medium | mitigate | middlegame_entry_subquery only sees game ids from the ts_matched CTE, which filters GamePosition.user_id == user_id; Task 1 test proves another user's eval on the same hash is not counted |
| T-ntq-02 | D | Page-load table-wide bookmark request | medium | mitigate | include_expected_score defaults to false, so the measured +1.3 to +1.8 s join never runs on page load; the per-opening request runs only on chart open; Task 1 step 6 checks the false-arm plan has no phase = 1 scan and records the on-demand cost against a 1,500 ms halt line |
| T-ntq-03 | T | include_expected_score request field | low | accept | Pydantic bool; it only toggles a read-only join over the caller's own games |
| T-ntq-SC | Tampering | npm/pip installs | high | accept | No packages are added or upgraded; `uv sync` and `npm ci` only install the locked set in a fresh worktree |
</threat_model>

<verification>
Before integrating into main (CLAUDE.md pre-merge gate, once, right before the squash-merge):
- `uv run ruff format app/ tests/ scripts/ analysis/` then `uv run ruff check . --fix`
- `uv run ty check app/ tests/ scripts/` and `uv run --project analysis --with ty ty check analysis/`
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`
- `uv run pytest -n auto -x`
- `npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend test -- --run && npm --prefix frontend run knip`
- `git status --porcelain frontend/src/generated` is empty: no generated file derives from the openings schemas, so none needs regenerating.
- If any gate step changes files, commit them with a `style(...)` or `chore(...)` prefix.
</verification>

<success_criteria>
- Opening any repertoire card's chart shows the eval-expected line over up to 100 games as the primary line, with the actual score fainter on the same axis, a dashed colour-baseline line and no typical band.
- The tooltip shows both values and the eval game count; the legend and popover copy match SEED-LD-3 and SEED-LD-5.
- The Stats page's up-front bookmark request is not heavier than before; the eval series is fetched per opening on chart open (OC-1 branch (b)).
- SUMMARY.md quotes the planning measurement, the decision rule, branch (b) and the post-change numbers.
- The CHANGELOG has the [Unreleased] bullet.
</success_criteria>

<output>
Create `.planning/quick/261115-ntq-implement-seed-261115-sgs/261115-ntq-SUMMARY.md` when done
</output>

<owner_override date="2026-11-15">
Decided by the owner during execution, after this plan was written:
- The per-game middlegame-entry eval uses the LATERAL first-phase=1-row lookup (listed above as "Not adopted"), not the sorted join. It lives next to the existing selection in `stats_repository`, with a parity test.
- Loading stays on demand as planned (front-loading was tried as a direction and reversed the same day, because most-played charts already load on open).
- Dev user 7 (67k games) is an outlier; prod allows far fewer games per user. Dev user 28 is the representative case.
See SUMMARY.md "Deviations from plan" for the measured numbers.
</owner_override>
