# Phase 15: Chart Consolidation and Polish - Research

**Researched:** 2026-03-17
**Domain:** Frontend React/TypeScript chart layout, navigation restructuring, platform filtering, time-series aggregation consistency
**Confidence:** HIGH

## Summary

Phase 15 is a pure frontend refactor with one small backend change. The goal is to collapse the separate Rating page into the Global Stats page, add a platform filter to the combined Global Stats page, enforce consistent time-bucket aggregation across the WinRateChart and RatingChart, and add section titles to the Statistics sub-tab in Openings.

All the affected components are well-understood: `RatingPage`, `GlobalStatsPage`, `RatingChart`, `GlobalStatsCharts`, `WinRateChart`, and the `WinRateChart`/`WDLBarChart` blocks in `OpeningsPage`. No new libraries are needed. The backend stats endpoints already accept `recency` query param and already filter by platform at the repository level — the only backend change is adding an optional `platform` query param to `GET /stats/global` and `GET /stats/rating-history`.

The WinRateChart currently uses monthly buckets (YYYY-MM strings). The RatingChart uses per-game data points with a computed x-axis in millisecond timestamps. "Consistent aggregation time buckets" means making the RatingChart adopt a monthly bucket strategy comparable to WinRateChart — aggregating to the last-in-month rating per time control per platform rather than plotting every individual game. This avoids visual noise and aligns time-axis labeling across all time-series charts.

**Primary recommendation:** Tackle this as two plans — (1) backend platform-filter param + frontend Global Stats + Rating merge, and (2) RatingChart monthly bucketing + Openings Statistics titles.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHRT-01 | Rating tab removed from nav; rating charts appear above Results by Time Control on Global Stats page | Nav array in App.tsx has 4 items; Rating route must be removed; GlobalStatsPage restructured |
| CHRT-02 | Platform filter (chess.com / lichess) added to Global Stats page | Backend needs `platform` param; frontend adds platform toggle matching FilterPanel style |
| CHRT-03 | Rating charts show one chart per platform; each chart shows per-time-control lines | Already implemented in RatingChart; reuse as-is or merge into single chart with platform split |
| CHRT-04 | Consistent monthly aggregation across all time-series charts (RatingChart uses monthly buckets like WinRateChart) | RatingChart currently per-game; needs monthly bucketing in frontend or backend |
| CHRT-05 | Chart titles added to Statistics sub-tab of Openings tab (WDLBarChart and WinRateChart) | statisticsContent in Openings.tsx has no headings; add `<h2>` above each chart |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React + TypeScript | 19 / project lock | UI components | Existing project stack |
| Recharts (via shadcn/ui chart.tsx) | project lock | All charts in project | `ChartContainer`, `LineChart`, `BarChart` wrappers already used |
| TanStack Query | project lock | Data fetching / caching | `useQuery` with queryKey invalidation already used for stats |
| Tailwind CSS | project lock | Layout and styling | All existing pages use Tailwind classes |
| FastAPI + Pydantic v2 | 0.115.x / v2 | Backend endpoint changes | Existing router/schema pattern |
| SQLAlchemy 2.x async | project lock | Repository query updates | Existing repository pattern |

### No New Dependencies Needed
All tooling is already installed. No npm installs, no new Python packages.

## Architecture Patterns

### Current Nav Structure (App.tsx lines 44-49)
```typescript
const NAV_ITEMS = [
  { to: '/import', label: 'Import' },
  { to: '/openings', label: 'Openings' },
  { to: '/rating', label: 'Rating' },       // REMOVE
  { to: '/global-stats', label: 'Global Stats' },
] as const;
```
After phase: remove `{ to: '/rating', label: 'Rating' }`. Route `/rating` should redirect to `/global-stats` to avoid broken bookmarks.

### Current Routing (App.tsx lines 154-155)
```typescript
<Route path="/rating" element={<RatingPage />} />
<Route path="/global-stats" element={<GlobalStatsPage />} />
```
After phase: remove `RatingPage` route (or replace with `<Navigate to="/global-stats" replace />`).

### Current GlobalStatsPage — Two Filters Today
`GlobalStatsPage` has only a `recency` Select. After phase it needs `recency` + `platform` toggle (chess.com / lichess / both). The platform toggle should match the style used in `FilterPanel` (pill buttons with `border-primary bg-primary` when active).

### Platform Filter UI Pattern (from FilterPanel.tsx)
```tsx
// Exact pattern already used for time control and platform in FilterPanel
<button
  key={p}
  onClick={() => togglePlatform(p)}
  data-testid={`filter-platform-${p === 'chess.com' ? 'chess-com' : p}`}
  aria-label={`${PLATFORM_LABELS[p]} platform`}
  aria-pressed={isPlatformActive(p)}
  className={cn(
    'rounded border px-2 py-0.5 text-xs transition-colors',
    isPlatformActive(p)
      ? 'border-primary bg-primary text-primary-foreground'
      : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground',
  )}
>
  {PLATFORM_LABELS[p]}
</button>
```
Use this identical pattern directly in `GlobalStatsPage` (inline, no FilterPanel needed since it's simpler).

### Backend Platform Filter Addition
Both stats endpoints today take only `recency: str | None`. Add `platform: str | None` to both:

**Router change** (`app/routers/stats.py`):
```python
@router.get("/stats/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    session: ...,
    user: ...,
    recency: str | None = Query(default=None),
    platform: str | None = Query(default=None),  # ADD: "chess.com" | "lichess" | None (all)
) -> RatingHistoryResponse:
```

**Service change** (`app/services/stats_service.py`):
When `platform` is `"chess.com"`, only query chess.com. When `"lichess"`, only query lichess. When `None`, query both (current behavior).

**Repository** — `query_rating_history` already accepts `platform: str` per call. No repository changes needed.

**Schema** — `RatingHistoryResponse` already has `chess_com` and `lichess` lists. When platform filter is set, one list is empty. No schema changes needed.

For `GET /stats/global`, add `platform: str | None` and filter `query_results_by_time_control` / `query_results_by_color` by platform. This requires adding `AND Game.platform = :platform` conditionally to the repository queries.

### Monthly Bucketing for RatingChart

**Current behavior:** `RatingChart` receives raw `RatingDataPoint[]` (one entry per game) and plots every game as an x-axis point. The x-axis is a computed timestamp axis.

**Target behavior:** Bucket to monthly — take the last rating reading per `(month, time_control_bucket)` combination before rendering. This matches WinRateChart's `YYYY-MM` monthly bucket approach.

Two implementation approaches:
1. **Frontend-only (preferred):** Transform `RatingDataPoint[]` to monthly buckets inside `RatingChart` using a `useMemo`. No backend changes. Simpler.
2. **Backend:** Add monthly aggregation to `query_rating_history`. More complex, not needed.

**Frontend transform logic:**
```typescript
// Group by month+tc, keep last rating per group
const monthlyData = useMemo(() => {
  const map = new Map<string, Record<string, number>>();
  for (const pt of data) {
    const month = pt.date.slice(0, 7); // "2024-03"
    const row = map.get(month) ?? { month };
    // Last-in-month wins (data is sorted by played_at)
    row[pt.time_control_bucket] = pt.rating;
    map.set(month, row);
  }
  return Array.from(map.values()).sort((a, b) =>
    (a.month as string).localeCompare(b.month as string)
  );
}, [data]);
```
After bucketing, the x-axis becomes a `dataKey="month"` string axis formatted with `formatMonth` (same helper as WinRateChart). Remove the complex `computeXTicks` / millisecond timestamp logic from `RatingChart` — replace with simple `XAxis dataKey="month" tickFormatter={formatMonth}`.

### Openings Statistics Sub-Tab Chart Titles

`statisticsContent` in `Openings.tsx` currently renders:
```tsx
<>
  <WDLBarChart bookmarks={bookmarks} wdlStatsMap={wdlStatsMap} />
  <WinRateChart bookmarks={bookmarks} series={tsData.series} />
</>
```
Add `<h2>` headings above each chart, consistent with the style used in `GlobalStatsCharts` (`text-lg font-medium mb-3`):
```tsx
<>
  <div>
    <h2 className="text-lg font-medium mb-3">Results by Opening</h2>
    <WDLBarChart bookmarks={bookmarks} wdlStatsMap={wdlStatsMap} />
  </div>
  <div>
    <h2 className="text-lg font-medium mb-3">Win Rate Over Time</h2>
    <WinRateChart bookmarks={bookmarks} series={tsData.series} />
  </div>
</>
```

### Global Stats Page Merged Layout

After merging Rating into Global Stats, the section order on `GlobalStatsPage` should be:

1. Page title: "Global Stats"
2. Filters row: recency Select + platform toggle (horizontal, same row or stacked depending on space)
3. Rating section: `<h2>Chess.com Rating</h2>` + `<RatingChart>` (hidden if platform=lichess)
4. Rating section: `<h2>Lichess Rating</h2>` + `<RatingChart>` (hidden if platform=chess.com)
5. Results by Time Control: `<WDLCategoryChart>`
6. Results by Color: `<WDLCategoryChart>`

Rating charts appear ABOVE Results by Time Control per the phase description.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-series x-axis formatting | Custom date formatter | Reuse `formatMonth` from WinRateChart | Already handles YYYY-MM → "Mar '24" |
| Platform pill filter | New component | Copy pattern from FilterPanel inline | Identical HTML/CSS already exists |
| Monthly bucketing | New API endpoint | Frontend useMemo transform | Simpler, no backend changes needed |
| Chart section headings | New styled component | `<h2 className="text-lg font-medium mb-3">` | Exact pattern in GlobalStatsCharts.tsx |

## Common Pitfalls

### Pitfall 1: Empty RatingChart when platform filter excludes a platform
**What goes wrong:** When platform="lichess", `ratingData?.chess_com` will be `[]`. The `RatingChart` renders an empty state "No Chess.com games imported." — misleading when the user explicitly filtered it out.
**How to avoid:** Conditionally render the entire section (`<section>` + `<h2>` + `<RatingChart>`) only if the platform filter includes that platform. When `platforms` is null (all) or includes "chess.com", show chess.com section; same for lichess.

### Pitfall 2: `computeXTicks` removal breaks existing tick logic
**What goes wrong:** `RatingChart` has a complex `computeXTicks` function (daily/weekly/monthly adaptive ticks). Removing it to switch to monthly bucketing is safe only if all call sites use the new monthly format.
**How to avoid:** After the monthly-bucket transform, the x-axis is categorical string data (YYYY-MM). Use `XAxis dataKey="month"` with `tickFormatter={formatMonth}` and no custom ticks — Recharts handles sparse categorical axes correctly.

### Pitfall 3: Route `/rating` becomes a 404
**What goes wrong:** Removing the `/rating` route without a redirect leaves any bookmarked URLs broken.
**How to avoid:** Replace `<Route path="/rating" element={<RatingPage />} />` with `<Route path="/rating" element={<Navigate to="/global-stats" replace />} />` in `App.tsx`. Keep `RatingPage` file until the route is confirmed removed or delete it if it's fully subsumed.

### Pitfall 4: Platform filter state naming collision with FilterPanel
**What goes wrong:** `GlobalStatsPage` uses a local `platforms` state; `FilterPanel` also has `platforms`. If someone tries to reuse `FilterPanel` here, its opaque toggle logic (null = all, array = subset) is designed for the Openings sidebar context and would add unnecessary complexity.
**How to avoid:** Manage platform selection directly in `GlobalStatsPage` as a simple `Platform | null` state (null = both). Do not embed `FilterPanel`.

### Pitfall 5: Monthly bucketing loses intra-month rating progression
**What goes wrong:** If a user plays 50 games in March and their rating swings 200 points, the monthly bucket shows only the last game — masking the journey.
**How to avoid:** This is the accepted tradeoff for visual clarity (per phase description: "consistent aggregation"). The last-in-month approach matches standard rating history chart behavior on chess.com and lichess. No special handling needed.

### Pitfall 6: Stats API recency + platform params combine incorrectly
**What goes wrong:** The backend might ignore platform when recency is null or vice versa.
**How to avoid:** Apply both filters independently with separate `.where()` clauses in the repository. Verify in tests.

### Pitfall 7: data-testid coverage on new elements
**What goes wrong:** New platform filter buttons and chart sections get no `data-testid` attributes, breaking browser automation.
**How to avoid:** Every new interactive element (platform filter buttons) needs `data-testid="filter-platform-chess-com"` and `data-testid="filter-platform-lichess"`. New rating section containers need `data-testid="rating-section-chess-com"` and `data-testid="rating-section-lichess"`.

## Code Examples

### Monthly Bucket Transform for RatingChart
```typescript
// Source: WinRateChart.tsx pattern adapted for rating data
const monthlyChartData = useMemo(() => {
  if (data.length === 0) return [];
  // data is sorted by played_at (backend guarantees chronological order)
  const map = new Map<string, Record<string, string | number>>();
  for (const pt of data) {
    const month = pt.date.slice(0, 7); // "YYYY-MM"
    const row = map.get(month) ?? { month };
    row[pt.time_control_bucket] = pt.rating; // last game in month wins
    map.set(month, row);
  }
  return Array.from(map.values());
  // Already sorted because source data is sorted by played_at
}, [data]);
```

### formatMonth helper (reuse from WinRateChart)
```typescript
// Source: WinRateChart.tsx line 26-31
const formatMonth = (m: string) => {
  const [year, month] = m.split('-');
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-US', {
    month: 'short',
    year: '2-digit',
  });
};
```

### Platform filter state in GlobalStatsPage
```typescript
// Simple: null = both platforms, string = one platform
const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[] | null>(null);

// Pass to hook:
const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(recency, selectedPlatforms);
const { data: globalStats, isLoading: statsLoading } = useGlobalStats(recency, selectedPlatforms);
```

### Updated useStats hooks signature
```typescript
// hooks/useStats.ts
export function useRatingHistory(recency: Recency | null, platforms: Platform[] | null) {
  return useQuery({
    queryKey: ['ratingHistory', recency, platforms],
    queryFn: () => statsApi.getRatingHistory(recency, platforms),
  });
}

export function useGlobalStats(recency: Recency | null, platforms: Platform[] | null) {
  return useQuery({
    queryKey: ['globalStats', recency, platforms],
    queryFn: () => statsApi.getGlobalStats(recency, platforms),
  });
}
```

### Backend repository — platform filter addition
```python
# stats_repository.py — query_results_by_time_control with optional platform
async def query_results_by_time_control(
    session: AsyncSession,
    user_id: int,
    recency_cutoff: datetime.datetime | None,
    platform: str | None = None,            # ADD
) -> list[tuple]:
    stmt = (
        select(Game.time_control_bucket, Game.result, Game.user_color)
        .where(Game.user_id == user_id, Game.time_control_bucket.is_not(None))
    )
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    if platform is not None:                # ADD
        stmt = stmt.where(Game.platform == platform)
    result = await session.execute(stmt)
    return list(result.fetchall())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-game x-axis in RatingChart | Monthly bucket (after this phase) | Phase 15 | Consistent with WinRateChart; less visual noise |
| Separate Rating nav tab | Merged into Global Stats | Phase 15 | Cleaner nav: 3 items (Import, Openings, Global Stats) |
| No platform filter on global stats | Platform toggle (chess.com/lichess) | Phase 15 | Multi-platform users can isolate data |

## Open Questions

1. **Platform filter: null=both or explicit array?**
   - What we know: FilterPanel uses `Platform[] | null` (null = all). `statsApi` calls pass platform as a single string today.
   - What's unclear: Whether the API should accept a single platform string or a comma-separated list.
   - Recommendation: Use a single `platform: str | None` query param at the API level (simpler; global stats page never needs both-except-one). The frontend maps `Platform[] | null` to a single param by taking the first element when the array has one entry, or `None` when both are selected.

2. **Merge both rating charts into one chart?**
   - What we know: Currently two separate `RatingChart` components — one for chess.com, one for lichess. Both use bullet/blitz/rapid/classical lines.
   - What's unclear: Phase description says "rating charts above Results by Time Control" (plural), implying two charts remain.
   - Recommendation: Keep as two separate charts with section headings. Merging 8 lines (4 TCs × 2 platforms) into one chart would be unreadable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHRT-01 | Rating tab removed from nav | manual smoke | visual inspection | N/A |
| CHRT-02 | Platform filter on Global Stats — backend filters correctly | unit/integration | `uv run pytest tests/test_stats_repository.py -x` | ✅ extend existing |
| CHRT-02 | Platform filter — router accepts param | integration | `uv run pytest tests/test_stats_router.py -x` | ✅ extend existing |
| CHRT-03 | Rating charts show per-time-control lines | manual smoke | visual inspection | N/A |
| CHRT-04 | Monthly bucketing produces correct month keys | unit | `uv run pytest tests/test_stats_service.py -x` | ❌ Wave 0 (new test) |
| CHRT-05 | Statistics sub-tab has chart titles | manual smoke | visual inspection | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_stats_service.py` — extend or create to cover platform filter in `get_global_stats` and `get_rating_history`

## Sources

### Primary (HIGH confidence)
- Direct code read of `frontend/src/pages/Rating.tsx` — full component source
- Direct code read of `frontend/src/pages/GlobalStats.tsx` — full component source
- Direct code read of `frontend/src/components/stats/RatingChart.tsx` — full chart with computeXTicks
- Direct code read of `frontend/src/components/stats/GlobalStatsCharts.tsx` — WDL category chart
- Direct code read of `frontend/src/components/charts/WinRateChart.tsx` — monthly bucket approach
- Direct code read of `frontend/src/App.tsx` — nav items and route definitions
- Direct code read of `frontend/src/pages/Openings.tsx` — statisticsContent block
- Direct code read of `app/routers/stats.py` — current endpoint signatures
- Direct code read of `app/repositories/stats_repository.py` — current query functions
- Direct code read of `app/services/stats_service.py` — aggregation logic
- Direct code read of `app/schemas/stats.py` — Pydantic response models
- Direct code read of `frontend/src/hooks/useStats.ts` — query hooks
- Direct code read of `frontend/src/api/client.ts` — statsApi methods
- Direct code read of `frontend/src/components/filters/FilterPanel.tsx` — platform filter pill pattern

### Secondary (MEDIUM confidence)
- None needed — all claims come from direct code inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture: HIGH — all patterns come from existing code in the same file tree
- Pitfalls: HIGH — derived from specific code-level observations (route removal, empty state messaging, etc.)

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable frontend project; no fast-moving dependencies)
