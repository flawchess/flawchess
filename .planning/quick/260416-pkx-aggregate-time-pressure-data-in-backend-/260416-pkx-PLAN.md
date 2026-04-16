---
quick_id: 260416-pkx
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
autonomous: true

must_haves:
  truths:
    - "Backend `/api/endgames/overview` returns a single pre-aggregated user_series + opp_series for the Time Pressure chart (no per-time-control rows)"
    - "Frontend no longer contains an `aggregateSeries` helper (knip-clean)"
    - "Frontend no longer references `TimePressureChartRow` anywhere (knip-clean)"
    - "Aggregation math matches the current frontend exactly: weighted average by game_count, score=null when game_count==0"
    - "MIN_GAMES_FOR_RELIABLE_STATS threshold still applied at the frontend render layer (not backend)"
    - "New backend test asserts sum(game_count) across all user buckets equals sum across all opp buckets, using realistic multi-time-control fixture data"
    - "uv run ty check app/ tests/ passes with zero errors; uv run pytest passes; npm run build + npm run lint succeed"
  artifacts:
    - path: "app/schemas/endgames.py"
      provides: "Updated TimePressureChartResponse (flattened user_series/opp_series); TimePressureChartRow removed"
    - path: "app/services/endgame_service.py"
      provides: "Rewritten _compute_time_pressure_chart producing a single pooled response"
    - path: "tests/test_endgame_service.py"
      provides: "Updated TestComputeTimePressureChart suite + new user/opp game_count parity test"
    - path: "frontend/src/types/endgames.ts"
      provides: "Mirror of new backend shape; TimePressureChartRow removed"
    - path: "frontend/src/components/charts/EndgameTimePressureSection.tsx"
      provides: "Chart consumes pre-aggregated series directly; aggregateSeries deleted"
  key_links:
    - from: "app/services/endgame_service.py::_compute_time_pressure_chart"
      to: "app/schemas/endgames.py::TimePressureChartResponse"
      via: "function return type"
    - from: "frontend/src/components/charts/EndgameTimePressureSection.tsx::buildChartData"
      to: "backend TimePressureChartResponse shape"
      via: "data prop (no intermediate aggregation)"
---

<objective>
Move the weighted-average aggregation of Time Pressure vs Performance chart data from the frontend into the backend. The backend returns a single pooled `user_series` + `opp_series` (10 buckets each), removing per-time-control rows entirely. The frontend drops its `aggregateSeries()` helper and consumes the backend payload directly. A new pytest test asserts that total user game_count equals total opponent game_count across all buckets (same-game symmetry invariant).

Purpose: Reduce frontend logic surface area, keep aggregation close to the data, simplify the response shape. The per-time-control rows are no longer consumed by anything and get deleted (not kept as dead fields).

Output: Updated Pydantic schema, rewritten service function, updated + new tests, smaller frontend component, knip-clean type exports.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/schemas/endgames.py
@app/services/endgame_service.py
@app/repositories/endgame_repository.py
@tests/test_endgame_service.py
@frontend/src/types/endgames.ts
@frontend/src/components/charts/EndgameTimePressureSection.tsx
@frontend/src/pages/Endgames.tsx

<interfaces>
Current backend contract (to be CHANGED):

```python
# app/schemas/endgames.py
class TimePressureBucketPoint(BaseModel):
    bucket_index: int          # 0..9
    bucket_label: str          # "0-10%" .. "90-100%"
    score: float | None        # None when game_count == 0
    game_count: int

class TimePressureChartRow(BaseModel):  # <-- WILL BE REMOVED
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str
    total_endgame_games: int
    user_series: list[TimePressureBucketPoint]
    opp_series: list[TimePressureBucketPoint]

class TimePressureChartResponse(BaseModel):  # <-- WILL BE RESHAPED
    rows: list[TimePressureChartRow]
```

Target backend contract (flattened, single pooled series):

```python
class TimePressureBucketPoint(BaseModel):   # unchanged
    bucket_index: int
    bucket_label: str
    score: float | None
    game_count: int

class TimePressureChartResponse(BaseModel):
    user_series: list[TimePressureBucketPoint]  # 10 points, pooled across time controls
    opp_series: list[TimePressureBucketPoint]   # 10 points, pooled across time controls
    total_endgame_games: int                    # sum of per-TC totals (after MIN_GAMES filter)
```

Notes on contract:
- `TimePressureChartRow` is DELETED from both backend and frontend types.
- The per-time-control filter (`MIN_GAMES_FOR_CLOCK_STATS`) still applies when deciding whether each TC's data contributes. Games under TCs below threshold are EXCLUDED from the pooled totals (same behaviour as today — frontend currently only sees rows that passed the filter).
- `total_endgame_games` is retained for "empty state" detection in the frontend (currently `timePressureChartData.rows.length > 0`).

Frontend consumer (currently in EndgameTimePressureSection.tsx, to be trimmed):

```typescript
// DELETE aggregateSeries() and its call site in buildChartData.
// buildChartData now maps data.user_series + data.opp_series directly into ChartDataPoint[].
// Keep MIN_GAMES_FOR_RELIABLE_STATS gate at render time (unchanged).
```

Consumer in Endgames.tsx (line 214):

```typescript
const showTimePressureChart = !!(timePressureChartData && timePressureChartData.rows.length > 0);
// CHANGE: replace with a field that exists on the new shape, e.g. total_endgame_games > 0
```

Aggregation formula (MUST match exactly — current frontend):
```
scoreSum += pt.score * pt.game_count  // only when pt.score !== null
scoredCount += pt.game_count          // only when pt.score !== null
countSum += pt.game_count             // always (tracks total games in bucket)
score = scoredCount > 0 ? scoreSum / scoredCount : null
game_count = countSum
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reshape backend schema + service + tests (pooled user/opp series)</name>
  <files>
    app/schemas/endgames.py,
    app/services/endgame_service.py,
    tests/test_endgame_service.py
  </files>
  <behavior>
    - `TimePressureChartResponse` exposes `user_series: list[TimePressureBucketPoint]` (len=10), `opp_series: list[TimePressureBucketPoint]` (len=10), and `total_endgame_games: int` — no `rows` field, no `TimePressureChartRow` class.
    - `_compute_time_pressure_chart` pools games across ALL time controls that pass `MIN_GAMES_FOR_CLOCK_STATS` into a single pair of 10-bucket series. It still iterates per-time-control internally to apply that threshold (same filter as today), then merges the kept TCs by summing `score_sum` and `game_count` per bucket.
    - Per bucket: `score = score_sum / game_count` if `game_count > 0` else `None` (weighted average, identical to the frontend formula being replaced).
    - `total_endgame_games` = sum of per-TC `total_games` for TCs that passed the threshold.
    - Bucket labels remain `"0-10%"` .. `"90-100%"`; `bucket_index` remains 0..9.
    - Existing `TestComputeTimePressureChart` tests updated to the new shape:
      - `result.rows` references → `result.user_series` / `result.opp_series` / `result.total_endgame_games`.
      - Tests that previously asserted two rows (bullet + rapid) now assert a single pooled pair whose bucket game_counts sum to the combined input.
      - Tests that checked `len(result.rows) == 0` now check `result.total_endgame_games == 0` AND that every point has `game_count == 0` / `score is None`.
    - New test `test_user_and_opp_game_count_totals_are_equal` in `TestComputeTimePressureChart`:
      - Builds `_make_clock_row` fixtures across MULTIPLE time controls (at least bullet and rapid, each with ≥10 qualifying games — use mixed W/D/L, mixed clock positions across buckets).
      - Calls `_compute_time_pressure_chart(rows)`.
      - Asserts `sum(p.game_count for p in result.user_series) == sum(p.game_count for p in result.opp_series)`.
      - Rationale comment: every played endgame contributes exactly one data point for the user AND one for the opponent — totals must match.
    - All other existing endgame tests remain green (no changes to semantics outside this function).
  </behavior>
  <action>
    1. In `app/schemas/endgames.py`:
       - Delete the `TimePressureChartRow` class.
       - Rewrite `TimePressureChartResponse` to `{ user_series: list[TimePressureBucketPoint], opp_series: list[TimePressureBucketPoint], total_endgame_games: int }`. Update the docstring to reflect the pooled shape.

    2. In `app/services/endgame_service.py`:
       - Remove the `TimePressureChartRow` import.
       - Rewrite `_compute_time_pressure_chart(clock_rows)` so it:
         a. Builds per-TC accumulators identical to today (`tc_user_buckets`, `tc_opp_buckets`, `tc_game_count`) — this preserves the `MIN_GAMES_FOR_CLOCK_STATS` threshold gate per TC.
         b. After the per-row loop, iterates `_TIME_CONTROL_ORDER`, skipping any TC with `tc_game_count[tc] < MIN_GAMES_FOR_CLOCK_STATS`.
         c. For each kept TC, accumulates into POOLED `user_buckets: list[list[float]]` / `opp_buckets: list[list[float]]` (len=10, `[score_sum, game_count]` per bucket) by adding each TC's sums element-wise. Also accumulates `total_endgame_games`.
         d. Builds pooled `user_series` / `opp_series` via the existing `_build_bucket_series` helper (it already produces `None` when `count == 0` — match the current formula exactly).
         e. Returns `TimePressureChartResponse(user_series=..., opp_series=..., total_endgame_games=...)`.
       - Do NOT change `_build_bucket_series` — it already implements the same weighted-average math (score_sum / count).
       - Do NOT change `query_clock_stats_rows` or `_compute_clock_pressure` (clock pressure table is unchanged).

    3. In `tests/test_endgame_service.py`:
       - Update every assertion in `TestComputeTimePressureChart` and `TestTimePressureChartPerGameDenominator` that references `result.rows[i].user_series` / `result.rows[i].opp_series` / `result.rows[i].total_endgame_games` / `result.rows[i].time_control` / `result.rows` → use `result.user_series` / `result.opp_series` / `result.total_endgame_games` directly. For the multi-TC test (`test_multiple_time_controls_separate_rows`), rename + rewrite to assert pooled behaviour: `sum(user_series game_counts) == 20`, both TCs' bucket counts accumulate into the same pair of series.
       - Update `test_empty_clock_rows_returns_empty_response`: `result.user_series` still has 10 points (all `score=None, game_count=0`), `result.opp_series` same, `result.total_endgame_games == 0`.
       - Update `test_time_control_below_min_games_excluded`: now assert `result.total_endgame_games == 0` and all bucket game_counts are 0 (since the only TC was excluded).
       - Add new test method `test_user_and_opp_game_count_totals_are_equal` inside `TestComputeTimePressureChart`:
         ```python
         def test_user_and_opp_game_count_totals_are_equal(self):
             """Same-game symmetry: every endgame contributes one user point AND one opp point,
             so summed game_counts across the user series and opp series must be equal."""
             rows: list[tuple] = []
             # Bullet: 10 games, varied clocks and results → user/opp land in different buckets
             for i in range(10):
                 rows.append(
                     _make_clock_row(i + 1, "bullet", 60, "checkmate",
                                     ["1-0", "0-1", "1/2-1/2"][i % 3],
                                     "white" if i % 2 == 0 else "black",
                                     [0, 1], [float(10 + i * 4), float(5 + i * 3)])
                 )
             # Rapid: 12 games, different clock distribution
             for i in range(12):
                 rows.append(
                     _make_clock_row(100 + i, "rapid", 600, "checkmate",
                                     ["1-0", "0-1", "1/2-1/2"][i % 3],
                                     "white" if i % 2 == 0 else "black",
                                     [0, 1], [float(100 + i * 40), float(80 + i * 35)])
                 )
             result = _compute_time_pressure_chart(rows)
             total_user = sum(p.game_count for p in result.user_series)
             total_opp = sum(p.game_count for p in result.opp_series)
             assert total_user == total_opp
             # Sanity: both totals match the number of games that contributed (those with
             # both clocks present and within the 2x clamp) — here all 22 games qualify.
             assert total_user == 22
         ```
       - Keep the existing `_build_bucket_series` unit tests as-is (helper unchanged).

    4. Run `uv run ruff check app/ tests/`, `uv run ruff format app/ tests/`, `uv run ty check app/ tests/`, and `uv run pytest tests/test_endgame_service.py -x` — fix any issues. Full suite is run in Task 3.
  </action>
  <verify>
    <automated>uv run ruff check app/ tests/ &amp;&amp; uv run ty check app/ tests/ &amp;&amp; uv run pytest tests/test_endgame_service.py -x</automated>
  </verify>
  <done>
    TimePressureChartRow deleted from schemas; TimePressureChartResponse has user_series/opp_series/total_endgame_games; _compute_time_pressure_chart returns pooled series; all existing endgame tests pass; new game_count-equality test passes; ty/ruff clean.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Update frontend types + delete aggregateSeries in EndgameTimePressureSection</name>
  <files>
    frontend/src/types/endgames.ts,
    frontend/src/components/charts/EndgameTimePressureSection.tsx,
    frontend/src/pages/Endgames.tsx
  </files>
  <action>
    1. In `frontend/src/types/endgames.ts`:
       - Delete the `TimePressureChartRow` interface entirely.
       - Rewrite `TimePressureChartResponse` to:
         ```typescript
         export interface TimePressureChartResponse {
           user_series: TimePressureBucketPoint[];  // 10 points, pre-aggregated across time controls
           opp_series: TimePressureBucketPoint[];   // 10 points, pre-aggregated across time controls
           total_endgame_games: number;
         }
         ```
       - Keep `TimePressureBucketPoint` unchanged (still exported — it's imported by the chart component).

    2. In `frontend/src/components/charts/EndgameTimePressureSection.tsx`:
       - Delete the `aggregateSeries` function entirely (lines ~51-82 in current file).
       - Rewrite `buildChartData(data: TimePressureChartResponse)` to map `data.user_series` and `data.opp_series` directly — zero-index alignment of the two 10-element arrays. The MIN_GAMES_FOR_RELIABLE_STATS gate stays here (pre-existing boundary — frontend still decides what to render vs null). Shape:
         ```typescript
         function buildChartData(data: TimePressureChartResponse): ChartDataPoint[] {
           return data.user_series.map((userPt, i) => {
             const oppPt = data.opp_series[i];
             const bucket_center = i * BUCKET_WIDTH + BUCKET_WIDTH / 2;
             const myCount = userPt.game_count;
             const oppCount = oppPt?.game_count ?? 0;
             return {
               bucket_center,
               bucket_label: userPt.bucket_label,
               my_score: myCount >= MIN_GAMES_FOR_RELIABLE_STATS ? userPt.score ?? null : null,
               opp_score: oppCount >= MIN_GAMES_FOR_RELIABLE_STATS ? (oppPt?.score ?? null) : null,
               my_game_count: myCount,
               opp_game_count: oppCount,
             };
           });
         }
         ```
       - Update the empty-guard: replace `if (data.rows.length === 0) return null;` with `if (data.total_endgame_games === 0) return null;`.
       - Remove the `TimePressureBucketPoint` import if it's no longer used in this file (only keep if buildChartData still references it). After the rewrite it is NOT referenced in type positions here — remove the import. The type remains exported from `types/endgames.ts` for the response schema itself.

    3. In `frontend/src/pages/Endgames.tsx` (line 214):
       - Change `const showTimePressureChart = !!(timePressureChartData && timePressureChartData.rows.length > 0);`
         to   `const showTimePressureChart = !!(timePressureChartData && timePressureChartData.total_endgame_games > 0);`

    4. Run `npm run lint`, `npm run build`, and `npm test` (from the `frontend/` directory). Address any errors. `npm run build` runs knip in CI — knip will flag `aggregateSeries` (deleted, good) and `TimePressureChartRow` (deleted, good), so the build must be clean.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run lint &amp;&amp; npm run build</automated>
  </verify>
  <done>
    aggregateSeries removed; TimePressureChartRow removed from types; buildChartData consumes data.user_series / data.opp_series directly; empty-state check uses total_endgame_games; npm run lint + npm run build pass (knip clean); npm test green.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Full-stack verification (ty + full pytest + frontend build)</name>
  <files></files>
  <action>
    Run the full verification battery to confirm nothing else broke:
    1. `uv run ruff check .`
    2. `uv run ty check app/ tests/` — zero errors required (CLAUDE.md rule).
    3. `uv run pytest` — full suite must pass (not just the endgame tests; the schema change could ripple into anything importing TimePressureChartRow).
    4. `cd frontend && npm run lint && npm run build` — knip must be clean (CI gate).
    5. Search the entire repo for any lingering references to the deleted symbols:
       - `grep -rn "TimePressureChartRow" app/ tests/ frontend/src/` — should return zero hits.
       - `grep -rn "aggregateSeries" frontend/src/` — should return zero hits.
       - `grep -rn "time_pressure_chart.*\.rows" app/ tests/ frontend/src/` — should return zero hits.
    6. If any of the above commands fail or return hits, fix the offending file and re-run. Do NOT leave dead references.
  </action>
  <verify>
    <automated>uv run ruff check . &amp;&amp; uv run ty check app/ tests/ &amp;&amp; uv run pytest &amp;&amp; cd frontend &amp;&amp; npm run lint &amp;&amp; npm run build</automated>
  </verify>
  <done>
    All linters/type checkers/tests pass on both stacks. No residual references to TimePressureChartRow, aggregateSeries, or `.time_pressure_chart.rows` anywhere in the repo.
  </done>
</task>

</tasks>

<verification>
- `uv run ty check app/ tests/` reports zero errors.
- `uv run pytest` passes (full suite, not just endgame tests).
- `cd frontend && npm run build` succeeds — this runs knip, which would flag leftover dead exports (`TimePressureChartRow`, `aggregateSeries`) if present.
- New backend test `test_user_and_opp_game_count_totals_are_equal` passes and exercises multiple time controls.
- Manual sanity check: open the Endgames page locally (`bin/run_local.sh`) and confirm the Time Pressure chart renders identically to main — same bucket shape, same line positions, same tooltip values. No regression in how MIN_GAMES_FOR_RELIABLE_STATS suppresses low-sample buckets.
</verification>

<success_criteria>
- Backend returns a flattened `TimePressureChartResponse` with `user_series`, `opp_series`, `total_endgame_games` — no per-time-control rows.
- Frontend has no `aggregateSeries` function and no `TimePressureChartRow` type.
- Weighted-average formula in the new backend pooled aggregation produces values identical to the current frontend computation for equivalent inputs.
- `MIN_GAMES_FOR_RELIABLE_STATS` threshold still enforced at the frontend render layer — moved nothing there, changed nothing there.
- New test proves the same-game symmetry invariant (sum user_series.game_count == sum opp_series.game_count).
- ty, ruff, pytest, knip, npm run lint, npm run build all green.
</success_criteria>

<output>
After completion, create `.planning/quick/260416-pkx-aggregate-time-pressure-data-in-backend-/260416-pkx-SUMMARY.md` documenting:
- Before/after shape of TimePressureChartResponse
- What was deleted on the frontend (aggregateSeries, TimePressureChartRow interface)
- Where the MIN_GAMES_FOR_RELIABLE_STATS boundary now lives (still frontend) and why
- Result of the new game_count parity test
</output>
