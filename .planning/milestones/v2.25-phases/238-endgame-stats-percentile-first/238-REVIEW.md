---
phase: 238-endgame-stats-percentile-first
reviewed: 2026-10-11T00:00:00Z
depth: standard
files_reviewed: 87
files_reviewed_list:
  - app/prompts/endgame_insights.md
  - app/repositories/endgame_ranked_repository.py
  - app/repositories/endgame_repository.py
  - app/repositories/query_utils.py
  - app/routers/endgames.py
  - app/routers/insights.py
  - app/schemas/endgames.py
  - app/schemas/insights.py
  - app/schemas/llm_log.py
  - app/services/canonical_slice_sql.py
  - app/services/endgame_ranked_service.py
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_llm.py
  - app/services/insights_service.py
  - app/services/user_benchmark_percentiles_service.py
  - CHANGELOG.md
  - scripts/gen_endgame_zones_ts.py
  - tests/prompts/test_endgame_insights_prompt.py
  - tests/repositories/test_query_utils.py
  - tests/routers/test_insights_openings.py
  - tests/schemas/test_endgames_schema.py
  - tests/services/golden/insights_user_prompt.txt
  - tests/services/ranked_payload_fixtures.py
  - tests/services/test_canonical_slice_sql.py
  - tests/services/test_endgame_ranked_parity.py
  - tests/services/test_endgame_ranked_service.py
  - tests/services/test_endgame_zones.py
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service.py
  - tests/services/test_insights_service_series.py
  - tests/services/test_time_pressure_service.py
  - tests/test_aggregation_sanity.py
  - tests/test_endgame_repository.py
  - tests/test_endgame_service.py
  - tests/test_endgames_router.py
  - tests/test_insights_llm_thinking.py
  - tests/test_insights_router.py
  - tests/test_insights_schema.py
  - tests/test_integration_routers.py
  - frontend/src/api/client.ts
  - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/ScoreGapByTimePressureChart.tsx
  - frontend/src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx
  - frontend/src/components/endgames/EndgameStatsTab.test.tsx
  - frontend/src/components/endgames/EndgameStatsTab.tsx
  - frontend/src/components/endgames/stats/ComparedToPeersCard.test.tsx
  - frontend/src/components/endgames/stats/ComparedToPeersCard.tsx
  - frontend/src/components/endgames/stats/MetricsCard.test.tsx
  - frontend/src/components/endgames/stats/MetricsCard.tsx
  - frontend/src/components/endgames/stats/MetricsSection.tsx
  - frontend/src/components/endgames/stats/OverallSection.tsx
  - frontend/src/components/endgames/stats/PercentileBar.test.tsx
  - frontend/src/components/endgames/stats/PercentileBar.tsx
  - frontend/src/components/endgames/stats/rankedFixtures.ts
  - frontend/src/components/endgames/stats/RankedMetricPopover.test.tsx
  - frontend/src/components/endgames/stats/RankedMetricPopover.tsx
  - frontend/src/components/endgames/stats/RankedMetricRow.tsx
  - frontend/src/components/endgames/stats/rankedMetrics.ts
  - frontend/src/components/endgames/stats/TcSwitch.tsx
  - frontend/src/components/endgames/stats/TimePressureSection.test.tsx
  - frontend/src/components/endgames/stats/TimePressureSection.tsx
  - frontend/src/components/endgames/stats/TypeTable.test.tsx
  - frontend/src/components/endgames/stats/TypeTable.tsx
  - frontend/src/components/endgames/useEndgameInsightsState.ts
  - frontend/src/components/insights/EndgameInsightsBubble.tsx
  - frontend/src/components/layout/SidebarLayout.tsx
  - frontend/src/components/popovers/FlawBulletPopover.tsx
  - frontend/src/generated/endgameZones.ts
  - frontend/src/hooks/__tests__/useEndgameInsights.test.tsx
  - frontend/src/hooks/__tests__/useEndgameStatsTc.test.ts
  - frontend/src/hooks/__tests__/useEndgameStats.test.tsx
  - frontend/src/hooks/useEndgameInsights.ts
  - frontend/src/hooks/useEndgameStatsTc.ts
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/endgameMetrics.ts
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/lib/pressureBulletConfig.ts
  - frontend/src/lib/__tests__/sounds.test.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
  - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
  - frontend/src/types/endgames.ts
findings:
  critical: 0
  warning: 5
  info: 9
  total: 14
status: issues_found
---
# Phase 238: Code Review Report

Merged from two parallel standard-depth reviewers (87-file scope split by stack). Finding IDs carry a BE-/FE- prefix for the backend and frontend halves.


# Backend

**Reviewed:** 2026-10-11
**Depth:** standard
**Files Reviewed:** 40
**Status:** issues_found

## Summary

The backend half of the percentile-first redesign is in good shape on the points the brief flagged as risky. I traced each one against the source:

- **User scoping and SQL binding.** `user_id` comes only from `current_active_user`. It reaches the ranked SQL through `CAST(:user_id AS int)` plus `.bindparams()`. Every `game_ids` restriction is a single bound `int[]` (`= ANY(:ids)`) and is always combined with `GamePosition.user_id == user_id` / `Game.user_id == user_id`. There is no cross-user leakage path and no injection surface. The `tc` f-string in `ranked_games_sql` is closed by the `TimeControlBucket` Literal at its only call site.
- **CTE mirroring.** I compared the Python helpers with the Stage A/B CTEs line by line, and they match. This covers the NULL-eval exclusion, the sub-800 floor on the rates and bucket gaps (and its absence on score_gap and achievable), the mate-before-cp bucket classification, the `|cp| < 2000` d_i gate, the net-flag denominator and the entry-clock extraction.
- **`since` trimming.** `_restrict_to_since` filters games and every row family consistently, drops persisted percentiles, and keeps the full rows for timeline pre-fill. The timelines trim emitted points by cutoff.
- **Insights cache key.** The key is `(user_id, prompt_version, model, "any")`, and the prompt version was bumped to v48, so old rows cannot be served. The router no longer accepts filters, and extra query params are ignored.
- **Retirement.** There are no live references to the retired overview endpoint, `FilterContext`, or the time-pressure card types. The only leftovers are stale comments and docstrings (see BE-IN-02).
- **Sentry and error messages.** The new except block (`compute_findings`) calls `set_context` and `capture_exception` and embeds no variables in the message.

I found no BLOCKER-level defects. The two warnings are both in the insights prompt assembly. They are behavior regressions caused by the move to per-time-control findings, not by the ranked service itself.

## Warnings

### BE-WR-01: Time-pressure aggregate lines narrate ungated, below-floor values

**File:** `app/services/insights_llm.py:933-978` (cause: `app/services/endgame_ranked_service.py:613-643`, `818-846`)
**Issue:** `_time_pressure_aggregate_lines` falls back to `tc_stats.metrics[<metric>].value` whenever no percentile record exists. `RankedMetricOut.value` is deliberately not gated by the floor: `_metric_out` copies `core.value` regardless of `status`. `_time_pressure_score_gap_metric` returns a value as soon as each side has at least one pressured game, so n=1 or n=2 per side gives a value.

The prompt then carries `- Time-Pressure Score Gap ...: value=+40% (no peer percentile yet)` built from a handful of games, with no `quality=` tag to tell the LLM it is thin. Before this phase the Time-Pressure Score Gap fallback read `card.time_pressure_score_gap_value`, which was sourced from the persisted `PercentileRow.value`. That row only exists once the dual >=30 floor is met, so the old fallback was implicitly floor-gated. The other two aggregate lines (Clock Gap, Net Flag Rate) were already ungated before this phase, but they share the new code path and have the same exposure now that their `status` is available.

**Fix:** Skip the value fallback unless the cell cleared its floor. For example, pass the whole `RankedMetricOut` and use:

```python
ranked_metric = tc_stats.metrics.get(metric_key)
fallback = (
    ranked_metric.value
    if ranked_metric is not None and ranked_metric.status in ("unranked", "ranked")
    else None
)
line = _aggregate_value_or_pctl(label, percentiles.get(f"{metric_key}:{tc}"), fallback)
```

A `below_floor` or `pending` cell then renders no line, matching the old TPSG behavior. Add a test with 2 pressured games per side asserting no `Time-Pressure Score Gap` line.

### BE-WR-02: Series filters (C2 / C5 / stale-live-twin) key on (metric, subsection_id) and ignore the new time_control dimension of `score_timeline`

**File:** `app/services/insights_llm.py:2080-2108`, `2280-2306`, `2309-2331`, `2465-2467` (feeding `app/services/insights_service.py:655-802`)
**Issue:** Phase 238 made `score_timeline` per time control: each TC emits its own three findings with `dimension={"time_control": tc}`. The three series-filter sets are all keyed on `(f.metric, f.subsection_id)`. That pair is now shared by up to four TCs, so one TC's series state decides the rendering of every other TC's series. This is the coarse-key problem the "Fix A" comment at line 2286 already fixed for a single pair; the endgame_elo combos only avoided it by being rarer.

- **C5 / Fix A regression.** `all_time_series_pairs` gets the pair as soon as ANY TC retains an all_time series. For a TC whose whole history is inside the last 90 days (for example a newly started rapid), its all_time series is C2-trimmed to empty. Its `last_3mo` series is then still suppressed by C5 because blitz registered the pair. The LLM gets `[summary ... time_control=rapid]` lines with `buckets=` and no `[series ...]` block, which is exactly the failure Fix A was written to prevent.
- **Stale-live-twin.** `live_series_metrics` holds the pair as soon as any TC is live. A TC whose last bucket is more than 183 days behind the newest bucket (for example classical, not played for 7 months) has its series dropped entirely because a "live twin" exists. The twins here are different time controls, not the same combo, so the dropped history is real information.
- **C2 over-trim.** `last_3mo_pairs` is true when any TC has a last_3mo finding, so every TC's all_time series loses its last 90 days, including a TC with no last_3mo series to cover them. This is harmless only because such a TC has no games in that period.

**Fix:** Key the three sets on the full group identity, `(f.metric, f.subsection_id, _dim_key_for_finding(f))`, in `_compute_all_time_series_pairs`, `_compute_stale_markers_and_live_metrics`, `last_3mo_pairs`, `_retained_series_for_summary`, `_apply_c5_filter` and `_apply_c2_filter`'s caller. For `endgame_elo_timeline` this also fixes the same latent issue between combos. Add a regression test with two TCs where one has history older than 90 days and the other does not.

## Info

### BE-IN-01: Dead retirement leftovers in schemas and service

**File:** `app/schemas/endgames.py:185-190, 286-308`; `app/services/endgame_service.py:1305-1340, 1505-1513, 1595-1686`
**Issue:**
- `EndgameStatsResponse.categories_by_tc` is never populated any more. `get_endgame_stats` does not set it, and it was previously filled from `_aggregate_endgame_stats_by_tc`. It is always `null` on the wire. `frontend/src/types/endgames.ts:73` still declares it and the docstring still says it is back-compat.
- `ClockStatsRow` has zero references in `app/`, `scripts/` and `tests/`.
- `_iterate_clock_rows` still builds `tc_clock_diffs` and the `_ClockAggregate` sums (`_bump_timeout_counts`, five summed fields). The only caller outside tests, `endgame_ranked_service._time_pressure_out`, discards both (`tc_total, _, user_wdl, opp_wdl, _, shared`). The TimePressureTcCard these were built for is gone, so this is wasted per-row work and a six-tuple return where three members are used.

**Fix:** Drop `categories_by_tc` (and the frontend type), delete `ClockStatsRow`, and shrink `_iterate_clock_rows` to return `(tc_total, user_wdl, opp_wdl, shared)`. Delete `_ClockAggregate` and `_bump_timeout_counts` along with it, and update `tests/services/test_time_pressure_service.py` accordingly.

### BE-IN-02: Stale comments and docstrings referencing retired components and plan numbers

**File:** `app/schemas/endgames.py:545, 559-560`; `app/services/endgame_service.py:1310, 1569`; `app/services/canonical_slice_sql.py:553`; `app/schemas/endgames.py:211, 230, 343`; `app/repositories/endgame_repository.py:772`
**Issue:** `RankedTimePressureOut` ("Plan 238-02 fills it") and `RankedTcStats` ("filled by Plan 238-02") describe a plan sequence that has finished. The fields are fully populated now, so those docstrings are misleading. Several docstrings still cite `TimePressureTcCard`, `EndgamePerformanceResponse`, `ScoreGapMaterialResponse` and `endgame_service.py lines 1941-1956`, none of which exist.
**Fix:** Reword to describe the current behavior and remove the line-number citations.

### BE-IN-03: Bare `str` for fixed sets in the new ranked path

**File:** `app/repositories/endgame_ranked_repository.py:31`; `app/services/endgame_ranked_service.py:144, 263`; `app/services/endgame_ranked_service.py:112`
**Issue:** The CLAUDE.md rule says never to use bare `str` for a fixed set. `RankedGameRow.platform` can only be `"chess.com"` or `"lichess"`. `_sign(user_color: str)` takes `"white"` or `"black"`. `_RowQueryKwargs.opponent_type` takes a fixed set. `_OUTCOME_SCORE` is `dict[str, float]` but is keyed by the `derive_user_result` Literal. `_achievable_expected` already needs a `cast(Literal["white","black"], ...)` because `user_color` was left as `str`.
**Fix:** Use `Literal["chess.com", "lichess"]` for `platform` and `Literal["white", "black"]` for `user_color`. Type `_OUTCOME_SCORE` as `dict[Literal["win","draw","loss"], float]`. That removes the `cast`.

### BE-IN-04: `endgame_ranked_service` imports private helpers from `endgame_service`

**File:** `app/services/endgame_ranked_service.py:80-94`
**Issue:** The ranked service reaches into eight underscore-prefixed names of `endgame_service` (`_aggregate_endgame_stats_by_tc`, `_build_quintile_bullets`, `_compute_clock_diff_timeline`, `_compute_score_gap_timeline`, `_compute_span_gap`, `_extract_entry_clocks`, `_iterate_clock_rows`, `_build_wdl_summary`). The service is now the main consumer of these helpers, so the "private" prefix no longer describes who depends on them. A rename in `endgame_service` silently breaks the new service. `build_endgame_elo_combos` was extracted as a public function in this phase, which is the right pattern.
**Fix:** Drop the underscore on the helpers that are now shared across modules, or move them into a small `endgame_metrics` module that both services import.

---

_Reviewed: 2026-10-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_



# Frontend

**Reviewed:** 2026-10-11
**Depth:** standard
**Files Reviewed:** 46
**Status:** issues_found

## Summary

The frontend half of the redesign is mostly sound. I checked the following and found no defect:

- TC restore and default logic in `useEndgameStatsTc`. A stored TC missing from the payload falls back to the D-12 default. The store holds only user choices, so restore and fallback write nothing and fire no analytics.
- Analytics. `trackFeature` fires only from the `TcSwitch` click handler, `jumpToSection`, and the tracked popover setter. Nothing fires on mount or from an effect.
- `isError` handling on the ranked query chain in `EndgameStatsTab`.
- Theme tokens. There are no raw colors and no `text-xs` outside the Radix popover exception.
- The G-1 double-mount fix. `findRenderedSection` is the only code that looks sections up by id. The other fixed ids are `aria-labelledby` targets (see FE-IN-02), and the chart gradient ids are `useId`-based.

The real defects are in the insights state, which moved from the page into the tab component. Its lifetime is now shorter than the cache that backs it (FE-WR-01, FE-WR-02). There is also a label inconsistency in the percentile bar (FE-WR-03).

## Warnings

### FE-WR-01: Generated insights report vanishes when the user leaves and re-enters the Stats tab

**File:** `frontend/src/components/endgames/useEndgameInsightsState.ts:21-42` (with `frontend/src/hooks/useEndgameInsights.ts:18-25`)
**Issue:** The state that holds the latest Generate result (`generatedInsights`) now lives in `EndgameStatsTab`, not in `EndgamesPage` as before.

- The tab sits inside Radix `TabsContent`, which unmounts inactive tabs. A Stats -> Games -> Stats round trip also remounts it through the `SidebarLayout` tree change (see FE-IN-03).
- On remount, `generatedInsights` is back to `null`. The report falls back to `cachedInsights.data`, which is the `['endgame-insights','cached']` query.
- Nothing writes the Generate result into that query. `useEndgameInsights` has no `onSuccess` and does no `setQueryData` or invalidate.
- The cached query has `staleTime` of 5 minutes, so remounting does not refetch. The user gets the pre-Generate value, usually `null` (404) or an older report.

The result is that a report the user just paid LLM budget and rate limit for disappears. Shelly's "Generate" bubble comes back, and clicking it again regenerates.

The same stale-copy problem shows up with the double mount. The desktop and mobile copies each hold a private `generatedInsights`, so crossing the md breakpoint after Generate shows the other copy with no report.

**Fix:** Make the cached query the single source of truth:

```ts
// useEndgameInsights.ts
export function useEndgameInsights() {
  const queryClient = useQueryClient();
  return useMutation<EndgameInsightsResponse, InsightsAxiosError, void>({
    mutationFn: async () => (await apiClient.post<EndgameInsightsResponse>('/insights/endgame')).data,
    onSuccess: (data) => {
      queryClient.setQueryData(['endgame-insights', 'cached'], data);
    },
  });
}
```

With that in place, `generatedInsights` only needs to cover the window before the cache write lands, or it can be dropped.

### FE-WR-02: Import completion does not invalidate the cached insights report unless the Stats tab happens to be mounted

**File:** `frontend/src/components/endgames/useEndgameInsightsState.ts:44-63` (with `frontend/src/App.tsx:1037-1052`)
**Issue:** The only place that refetches `['endgame-insights','cached']` after an import is the `>0 -> 0` active-jobs edge effect in this hook. The hook now runs only while `EndgameStatsTab` is mounted.

- The global import-completion handler in `App.tsx` invalidates `endgameOverview` and the library keys, but not `endgame-insights`.
- If an import finishes while the user is on the Games tab, the Library, or Import, the effect never sees the edge. The cached query keeps serving the pre-import report for up to the 5-minute `staleTime`.
- On return, the new-games-invalidated report is shown as current, and the 404 the server would send for a report older than the latest import is never observed.
- The mount effect seeds `prevJobsCountRef` with the first observation, so the missed edge is never replayed.

**Fix:** Invalidate where the other endgame caches are invalidated. Once FE-WR-01 makes the query the source of truth, the per-hook edge effect and `refetchCachedInsights` can go too.

```ts
// App.tsx, next to the endgameOverview invalidation
queryClient.invalidateQueries({ queryKey: ['endgame-insights'] });
```

### FE-WR-03: Percentile ordinal is not clamped, so the bar can say "0th" or "100th" while the dot and the popover say 1% or 99%

**File:** `frontend/src/components/endgames/stats/PercentileBar.tsx:103-137` (clamp helpers in `frontend/src/components/endgames/stats/rankedMetrics.ts:17-23`, used at `frontend/src/components/endgames/stats/RankedMetricPopover.tsx:65`)
**Issue:** The backend returns tail percentiles of exactly `0.0` and `100.0`. See `_LEFT_TAIL_CLAMP` and `_RIGHT_TAIL_CLAMP` in `app/services/global_percentile_cdf.py:86-87`, for any value at or beyond the first or last breakpoint.

- `PercentileBar` clamps the dot position with `clampPercentile`, but renders the label with `formatOrdinal(percentile)` on the raw value, so the user sees "0th" or "100th".
- `RankedMetricPopover` prints `Math.round(clampPercentile(...))`, so the same cell reads "Better than 99% of ...".
- The comment on `MIN_PERCENT`/`MAX_PERCENT` states the intent: "no '0th' or '100th' percentile". The dot honours that, the number does not.
- `PercentileBar.test.tsx` covers the dot clamp (0.4 -> 1%, 100 -> 99%) but never asserts the label for those inputs.

**Fix:** Derive one displayed percentile and use it for the label, the color, and the popover:

```tsx
const shown = Math.round(clampPercentile(percentile));
const bandColor = percentileBandColor(shown);
// ...
{formatOrdinal(shown)}
```

Add a test row for 0 -> "1st" and 100 -> "99th". See FE-IN-01 for the color-boundary half of the same issue.

## Info

### FE-IN-01: Band color is computed from the unrounded percentile, so the displayed ordinal can contradict the legend

**File:** `frontend/src/components/endgames/stats/PercentileBar.tsx:103`
**Issue:** `percentileBandColor(percentile)` uses the raw value, while the label shows the rounded one. A percentile of 24.6 renders a red dot with the label "25th". The Concepts accordion says "red below the 25th percentile, blue from the 25th to the 75th". 75.4 renders "75th" in green. This only occurs at the two boundaries.
**Fix:** Pass the rounded and clamped value to `percentileBandColor` (see the FE-WR-03 snippet).

### FE-IN-02: Duplicate data-testid values within a single mount; duplicate ids from the double mount reach `aria-labelledby`

**File:** `frontend/src/components/endgames/stats/ComparedToPeersCard.tsx:70`, `frontend/src/components/endgames/stats/RankedMetricRow.tsx:38`, `frontend/src/components/endgames/stats/TypeTable.tsx:263-271`
**Issue:**

1. `PeerRow` and `RankedMetricRow` build the popover trigger testid the same way, as `ranked-metric-${slug}-tc-${tc}`. The peers card and the section card both render every ranked metric, so within one mounted tab each trigger testid and its `-popover` / `-footer` variants appear twice. The sharing is deliberate (one analytics row per explanation), but it breaks the "stable testids for browser automation" intent. Selectors for these elements will match two nodes.
2. The only remaining reliance on unique ids under the double mount is `aria-labelledby="endgame-type-breakdown-heading"`. It resolves to the first copy, the desktop one, which is `display:none` on mobile. Accessible-name computation still reads hidden labelled-by content, so this works today.
   - I found no other `getElementById`, `querySelector('#...')` or fixed SVG id that depends on uniqueness. `EndgameEloTimelineSection` uses `useId`.

**Fix:** Keep the popover testid for analytics, but make the DOM testid distinct, for example by adding a surface prefix (`peer-` or `row-`). Alternatively pass a separate analytics key to `useTrackedPopoverOpen`. Prefer `aria-label` on the section over `aria-labelledby` against a duplicated id.

### FE-IN-03: Stats-tab visits still fire the Games tab's queries, and the tab switch remounts the tab content

**File:** `frontend/src/pages/Endgames.tsx:162-178` (hooks in `frontend/src/hooks/useEndgames.ts:28-46,65-84`), `frontend/src/components/layout/SidebarLayout.tsx:181-187`
**Issue:**

1. `useEndgameStats(appliedFilters, ...)` is the heavy filtered GROUP BY (the hook's own comment calls it expensive). It is now consumed only by the Games tab, but runs while the Stats tab is active. `useEndgameGames` also fires for the default `mixed` category on the Stats tab, and is not gated on `tier2`.
2. `SidebarLayout` returns a structurally different tree when `panels` is empty, so switching Stats <-> Games remounts all tab content, not only the Radix inactive-content unmount. This amplifies FE-WR-01 and also drops the Games-tab `GameCardList` state.

**Fix:** Gate both Games queries on `enabled: tier2 && activeTab === 'games'`. Keep `SidebarLayout`'s child position stable if remount cost matters, or accept it once FE-WR-01 is fixed. Note that the `matchLabel` consumer already tolerates `statsData` being undefined.

### FE-IN-04: Time Pressure section shows an empty plot with no message when a TC has no clock data

**File:** `frontend/src/components/endgames/stats/TimePressureSection.tsx:49-62` (chart in `frontend/src/components/charts/ScoreGapByTimePressureChart.tsx:248-253`)
**Issue:** The clock timeline card hides itself when `clock_diff_timeline` is empty, but the "Score vs. opponent by clock left" chart always renders. With all quintile `n === 0`, `toChartData` returns `[]` and the chart draws only the axis frame and the grey "typical" band. There is no "not enough clock data" copy, and the section gives no reason why it is blank.
**Fix:** In `TimePressureSection`, render a muted `text-sm` empty-state line instead of the chart when `tcStats.time_pressure.quintiles.every((q) => q.n === 0)`.

### FE-IN-05: Un-chosen default TC can change silently when the payload refetches

**File:** `frontend/src/hooks/useEndgameStatsTc.ts:98-99`
**Issue:** When the user has never clicked a TC, `selected` is re-derived from `pickDefaultTc(tcs)` on every render. After an import invalidates `['endgameOverview','ranked']`, a different TC can overtake the previous leader by `ranked_games`. All sections then jump to another TC without the user doing anything, possibly mid-reading. This is consistent with the "store only user choices" design, but it is a surprising state change. It also leaves the first section the user never touched in a different state than the one they last saw.
**Fix:** Accept as is (cheap to explain), or memoize the first computed default in a ref for the lifetime of the mount and recompute only when that TC leaves the payload.

---

_Reviewed: 2026-10-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
