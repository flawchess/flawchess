---
phase: 55-time-pressure-performance-chart
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
  - frontend/src/lib/theme.ts
  - tests/test_endgame_service.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the time-pressure performance chart implementation spanning backend service, frontend components, and schemas. The phase introduces a new time-pressure vs performance visualization comparing user's score against opponent's score across 10 time-remaining buckets, tabbed by time control. The architecture is sound with proper state management and component composition. However, **one critical type safety issue** was found in the frontend component that violates the project's `noUncheckedIndexedAccess` TypeScript setting, along with minor concerns about error handling and consistency.

## Critical Issues

### CR-01: Unsafe Array Index Access in buildChartData

**File:** `frontend/src/components/charts/EndgameTimePressureSection.tsx:31`

**Issue:** The `buildChartData` function iterates over `row.user_series` and accesses `row.opp_series[i]` without bounds checking. While the code uses optional chaining `oppPt?.score` on line 35 to handle the potential undefined value, this doesn't address the root safety issue: the index access itself is unchecked. Per CLAUDE.md, `noUncheckedIndexedAccess` is enabled in the TypeScript configuration, which means every array index access that returns `T | undefined` must be explicitly narrowed before use. The code creates a false sense of safety by using optional chaining on the result, but the real issue is the unchecked index access at the assignment.

The backend schema documents that both `user_series` and `opp_series` have exactly 10 elements (`// always 10 elements`), but TypeScript's type system doesn't encode this invariant. If the backend ever returns mismatched array lengths or if the contract is violated, this will silently produce undefined values rather than failing loudly.

**Fix:**
```typescript
function buildChartData(row: TimePressureChartRow): ChartDataPoint[] {
  return row.user_series.map((userPt, i) => {
    const oppPt = row.opp_series[i]; // oppPt is now TimePressureBucketPoint | undefined
    if (oppPt === undefined) {
      // Handle the case where opp_series is shorter than user_series
      throw new Error(`opp_series missing data at index ${i}`);
    }
    return {
      bucket_label: userPt.bucket_label,
      my_score: userPt.score ?? undefined,
      opp_score: oppPt.score ?? undefined,
      my_game_count: userPt.game_count,
      opp_game_count: oppPt.game_count ?? 0,
    };
  });
}
```

Alternatively, if the invariant is guaranteed by the backend, add an assertion:
```typescript
function buildChartData(row: TimePressureChartRow): ChartDataPoint[] {
  return row.user_series.map((userPt, i) => {
    const oppPt = row.opp_series[i]!; // non-null assertion: always 10 elements per schema
    return {
      bucket_label: userPt.bucket_label,
      my_score: userPt.score ?? undefined,
      opp_score: oppPt.score ?? undefined,
      my_game_count: userPt.game_count,
      opp_game_count: oppPt.game_count,
    };
  });
}
```

## Warnings

### WR-01: Missing Error Handling in useQuery in Endgames.tsx

**File:** `frontend/src/pages/Endgames.tsx:285-290`

**Issue:** The `timePressureChartData` is rendered on line 285-290 without an explicit `isError` check. Per CLAUDE.md frontend error handling rules, every `useQuery` result rendered in a data-loading ternary chain must include an `isError` branch. The current code handles `overviewError` broadly at line 291, but if specifically the time-pressure chart query fails while other overview data loads, the UI may show partial data without clearly indicating the failure for this section. Additionally, line 285 uses the guard `timePressureChartData && timePressureChartData.rows.length > 0`, which succeeds even when the data is stale from a previous successful request, potentially showing outdated time-pressure stats if the refetch fails.

**Fix:**
```typescript
{timePressureChartData && timePressureChartData.rows.length > 0 && !overviewError ? (
  <div className="charcoal-texture rounded-md p-4">
    <EndgameTimePressureSection data={timePressureChartData} />
  </div>
) : overviewError ? (
  <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
    <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
    <p className="text-sm text-muted-foreground">
      Something went wrong. Please try again in a moment.
    </p>
  </div>
) : null}
```

### WR-02: Score Mapping Off-by-One in Time Pressure Chart Calculation

**File:** `app/services/endgame_service.py:869`

**Issue:** The `user_score` mapping at line 869 assigns `"loss": 0.0` directly, but doesn't handle the case where `derive_user_result` returns something other than "win", "draw", or "loss". If the function ever returns an unexpected value (due to a bug in `derive_user_result` or data corruption), this will raise a KeyError rather than failing gracefully. While the function is tested and reliable, defensive programming would catch such edge cases early.

Additionally, on line 874, the opponent score is computed as `1.0 - user_score`, which is mathematically correct for win/loss/draw but creates an implicit coupling: if the user_score mapping ever changes, the opponent calculation may become incorrect. For example, if a new result type is added, the mapping must be updated in both places.

**Fix:**
```typescript
def _compute_time_pressure_chart(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> TimePressureChartResponse:
    # ... existing code ...
    for row in clock_rows:
        # ... existing code ...
        
        user_result = derive_user_result(result, user_color)
        user_score = {"win": 1.0, "draw": 0.5, "loss": 0.0}.get(user_result, 0.0)  # Safe default
        
        # Accumulate: initialise defaultdict entry if needed, then update
        tc_user_buckets[tc][user_bucket][0] += user_score
        tc_user_buckets[tc][user_bucket][1] += 1
        # Opponent score is always the complement in W/D/L
        opp_score = 1.0 - user_score
        tc_opp_buckets[tc][opp_bucket][0] += opp_score
        tc_opp_buckets[tc][opp_bucket][1] += 1
```

## Info

### IN-01: Theme Constants Correctly Imported in EndgameTimePressureSection

**File:** `frontend/src/components/charts/EndgameTimePressureSection.tsx:13`

**Issue:** Minor observation (not a bug). The component imports theme constants `MY_SCORE_COLOR` and `OPP_SCORE_COLOR` from `@/lib/theme`, which is correct per CLAUDE.md guidelines ("all theme-relevant color constants must be defined in `frontend/src/lib/theme.ts` and imported from there"). However, the constants are also used inline in the Recharts `Line` component's `stroke` attribute as CSS variables (`stroke="var(--color-my_score)"`), which assumes Recharts' `ChartContainer` sets up these CSS variables. This creates an implicit dependency: if the CSS variable names ever change, the code won't break, but the colors will be wrong silently.

**Suggestion:** Consider a comment documenting the CSS variable naming convention:
```typescript
// NOTE: MY_SCORE_COLOR and OPP_SCORE_COLOR are used in the chartConfig above.
// The Line components reference these via CSS variables (e.g., var(--color-my_score))
// which are injected by Recharts' ChartContainer. Ensure the CSS variable names
// match the chartConfig keys exactly.
```

### IN-02: MIN_GAMES_FOR_CLOCK_STATS Constant Defined in Both Schema and Service

**File:** `app/schemas/endgames.py:249` vs `app/services/endgame_service.py:616`

**Issue:** The constant `MIN_GAMES_FOR_CLOCK_STATS = 10` is defined in both locations (schema docstring and service module). The service value is the authoritative one used in computation, but the schema's docstring mentions it for documentation. This is not incorrect, but creates a maintenance risk: if the threshold changes, both locations must be updated. The threshold is already imported into the service from the query utils (implicit dependency on `query_clock_stats_rows`), so there's no functional issue.

**Suggestion:** Consider defining this constant in a shared location (e.g., `app/config/constants.py`) or in the schema module as an exported constant, so the service imports it rather than redefining it locally. This ensures a single source of truth.

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
