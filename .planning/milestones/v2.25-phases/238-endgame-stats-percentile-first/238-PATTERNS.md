# Phase 238: Endgame Stats Percentile-First Redesign - Pattern Map

**Mapped:** 2026-10-11
**Files analyzed:** 24 (new + modified; retirements listed separately)
**Analogs found:** 22 / 24

All analog paths below are git-tracked source (verified with `git ls-files`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/canonical_slice_sql.py` (+ `ranked_games_sql(tc)`, new fn only) | utility (SQL text builder) | transform | same file: `selected_users_cte` (195-228), `_recent_capped_per_tc_cte` (284-316) | exact |
| `app/repositories/query_utils.py` (+ `game_ids` kw param) | utility | CRUD (read filter) | same file `apply_game_filters` (152-182) kw-only params e.g. `native_games_bypass_opponent_and_rated` | exact |
| `app/repositories/endgame_repository.py` (thread `game_ids`, push into inner `GamePosition` subqueries) | repository | CRUD read | same file 206-225, 363-382, 822-840 (ANY-array form comment) | exact |
| `app/repositories/endgame_ranked_repository.py` (or fn in endgame_repository) | repository | CRUD read (raw `text()`) | `app/services/user_benchmark_percentiles_service.py::_compute_metric_for_user_per_tc` (250-280) executing canonical text with `user_id` bindparam | role-match |
| `app/services/endgame_ranked_service.py` (NEW) | service | batch/transform | `app/services/endgame_service.py::get_endgame_overview` orchestration + `user_benchmark_percentiles_service.py` | role-match |
| `app/schemas/endgames.py` (+ `RankedMetricOut`, `RankedTcStats`, `EndgameRankedStatsResponse`; − aggregated fields) | model (Pydantic) | request-response | same file existing response models | exact |
| `app/routers/endgames.py` (+ `GET /ranked-stats`, `GET /stats`; later − `/overview`) | route | request-response | same file `get_endgame_overview` (27-65) | exact |
| `app/services/insights_service.py` (`compute_findings(session, user_id)`) | service | transform | same file `compute_findings` (137-183) | exact (rewrite) |
| `app/routers/insights.py` (drop filter params + `_validate_full_history_filters`) | route | request-response | same file `get_endgame_insights` (106-186) | exact (simplify) |
| `app/services/insights_llm.py` (`_PROMPT_VERSION = "endgame_v48"`) + `app/prompts/endgame_insights.md` | config/prompt | — | same file line 88 (v47 comment style) | exact |
| `tests/services/test_canonical_slice_sql.py` (golden hash + ranked_games tests) | test | — | same file (byte baseline ~line 946) | exact |
| `tests/services/test_endgame_ranked_parity.py` (NEW, DB) | test | — | `tests/services/test_user_benchmark_percentiles_service_real_data.py` (`_seed_canonical_slice_user` ~line 160) | exact |
| `tests/services/test_endgame_ranked_service.py` (NEW, status matrix) | test | — | `tests/services/test_user_benchmark_percentiles_service_real_data.py` | role-match |
| `tests/test_endgames_router.py`, `tests/test_insights_router.py`, `tests/services/test_insights_*.py` | test | — | existing files (rewrite) | exact |
| `frontend/src/hooks/useEndgameRankedStats.ts` (or inside `useEndgames.ts`) | hook | request-response | `frontend/src/hooks/useEndgames.ts::useEndgameOverview` | exact |
| `frontend/src/hooks/useEndgameStatsTc.ts` (store + localStorage) | store/hook | event-driven | `frontend/src/lib/engineSettings.ts` (useSyncExternalStore + try/catch localStorage), `frontend/src/hooks/useFlawFilterStore.ts` | exact |
| `PercentileBar.tsx` (NEW) | component | — | `frontend/src/components/charts/PercentileChip.tsx` (clamp + color logic) / `MiniBulletChart.tsx` (bar drawing) | role-match |
| `RankedMetricPopover.tsx` (NEW, merges MetricStatPopover + PercentileChip copy) | component | — | `frontend/src/components/popovers/MetricStatPopover.tsx` (shell) + `PercentileChip.tsx` (disclosure copy 193-262) | exact |
| `TcSwitch.tsx` (NEW) | component | event-driven | Radix `Tabs` usage in `frontend/src/pages/Endgames.tsx` (TabsList variant="brand") | role-match |
| `ComparedToPeersCard.tsx` (NEW dot plot) | component | — | none (sketch 009) | no analog |
| Overall per-TC cards / Metrics cards / Time Pressure / Type table (rework of `frontend/src/components/charts/Endgame*`) | component | — | existing `EndgameMetricsByTcSection.tsx`, `EndgameMetricsByTcCard.tsx`, `EndgameTypeBreakdownSection.tsx`, `ScoreGapByTimePressureChart.tsx`, `EndgameClockDiffOverTimeChart.tsx` | exact (rework) |
| `EndgameStatsTab.tsx` (extract) + `frontend/src/pages/Endgames.tsx` (hide filter UI on stats) | page/component | — | `Endgames.tsx` 918-1010 (SidebarLayout panels + mobile Filters button) | exact |
| `frontend/src/hooks/useEndgameInsights.ts` (no filters) | hook | request-response | same file | exact (simplify) |
| `frontend/src/lib/analytics.ts` (+ `OPTION_TARGETS` entry `endgame-stats-tc`) | config | — | same file line 440 | exact |

## Pattern Assignments

### `app/services/canonical_slice_sql.py` — new `ranked_games_sql(tc)` (utility, transform)

**Analog:** same file. Compose, never edit existing builders (D-07 byte identity).

`selected_users_cte` single_user branch (lines 225-228):
```python
    # single_user: scalar bindparam; pools across all TCs (D-5). The explicit
    # CAST() form is load-bearing — see 94.1 Plan 09 — SQLAlchemy's text()
    # tokeniser silently drops `:user_id::int` ...
    return "selected_users AS (SELECT CAST(:user_id AS int) AS user_id)"
```
`_recent_capped_per_tc_cte` (lines 284-316): emits `recent_capped AS (SELECT g.id, g.user_id, g.user_color, g.result, g.played_at FROM (... row_number() OVER (PARTITION BY g.user_id ORDER BY g.played_at DESC) ... AND g.time_control_bucket = '{tc}') g WHERE g.rn <= {RECENT_GAMES_PER_TC_CAP})`. `tc` f-string is safe only because it is `TimeControlBucket` Literal (docstring point 1). Copy that docstring justification into the new function. New function shape is in RESEARCH Pattern 1; confirm `platform`, `time_control_str`, `evals_completed_at` against `app/models/game.py`. Anchor-floor count must exclude chess.com Daily (`g.time_control_str LIKE '1/%'`, ~line 1259).

### `app/repositories/query_utils.py` — `game_ids` keyword (utility)

**Analog:** `apply_game_filters` signature lines 152-182. Add after the existing keyword-only block, with the same commented-default style:
```python
    *,
    # SEED-163 2b: keyword-only, default-False so every existing caller keeps
    # today's behavior unchanged; ...
    native_games_bypass_opponent_and_rated: bool = False,
    ...
    has_great: bool | None = None,
) -> Any:
```
→ add `game_ids: Sequence[int] | None = None` with a Phase 238 comment; `None` = unchanged behavior. Use bound array (`Game.id == any_(...)`) per the planner-hang comment at `endgame_repository.py:822-826` (avoid `IN (subquery)`).

### `app/repositories/endgame_ranked_repository.py` (repository, raw text)

**Analog:** `app/services/user_benchmark_percentiles_service.py::_compute_metric_for_user_per_tc` (250-280), returns `tuple[float, int] | None`, runs canonical text with `text(sql).bindparams(user_id=user_id)`. Persisted reads use `app/repositories/user_benchmark_percentiles_repository.py::fetch_for_user` (158-200):
```python
async def fetch_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]:
    """... V4 Information Disclosure mitigation: Caller MUST pass the authenticated
    user's ID ... never accept ``user_id`` as a query parameter from the client."""
    result = await session.execute(select(...).where(UserBenchmarkPercentile.user_id == user_id))
    out: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {}
    for row in rows:
        out.setdefault(row.metric, {})[row.time_control_bucket] = PercentileRow(...)
```
Copy the keyword-only `*, user_id: int`, V4 docstring line, and nested-dict-keyed-by-Literal return shape.

### `app/services/endgame_ranked_service.py` (NEW service)

**Analogs:** `endgame_service.get_endgame_overview` for sequential awaits on one session (never `asyncio.gather`); `endgame_service._accumulate_endgame_rows(...)["gaps_by_bucket"]` for the ΔES gaps on entry_rows; `score_confidence.py` helpers for CI/p; `eval_utils.eval_cp_to_expected_score` / `eval_mate_to_expected_score` (65-115). Canonical definitions to mirror: RESEARCH Pattern 3 table (CTE line refs in `canonical_slice_sql.py` 391-1049). Status helper shape: RESEARCH "Rank-status helper". Keep nesting ≤4; pure per-TC builders (`_fetch` / `_compute` / `_rank` seams). Do NOT add to `endgame_service.py` (3817 lines).

### `app/routers/endgames.py` — `GET /ranked-stats`, `GET /stats`

**Analog:** lines 24-65:
```python
router = APIRouter(prefix="/endgames", tags=["endgames"])

@router.get("/overview", response_model=EndgameOverviewResponse)
async def get_endgame_overview(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    ...
) -> EndgameOverviewResponse:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await endgame_service.get_endgame_overview(session, user_id=user.id, ...)
```
`/ranked-stats`: same two deps, no Query params, `return await endgame_ranked_service.get_ranked_stats(session, user_id=user.id)`; comment the SQL `NOW()` vs `dev_now_utc` exception (Pitfall 11). `/stats`: copy the filter params + 422 check verbatim, call existing `get_endgame_stats`. Update module docstring endpoint list.

### `app/routers/insights.py` — drop filters (D-04)

**Analog:** `get_endgame_insights` 106-186. Keep the try/except → `JSONResponse(status_code=502, content=InsightsErrorResponse(error=...).model_dump())` blocks unchanged; delete Query params, `derive_preset`/custom-400 block, `FilterContext` build and `_validate_full_history_filters` (def at line 54). Same for `/endgame/cached` (188+).

### `app/services/insights_llm.py`

**Analog:** line 88 — bump with an explanatory inline comment in the same style:
```python
_PROMPT_VERSION = "endgame_v47"  # v47 (FLAWCHESS-AG, cache-flush only ...): ... Bumping the version is the only lever that invalidates them.
```
→ `"endgame_v48"  # v48 (Phase 238): findings from ranked sample, filter-independent ...`. Golden regen in `tests/services/test_insights_llm.py` (~874-887) must be stated as deliberate.

### `tests/services/test_endgame_ranked_parity.py` (NEW)

**Analog:** `tests/services/test_user_benchmark_percentiles_service_real_data.py` (`_seed_canonical_slice_user` ~160), oracle = `_compute_metric_for_user_per_tc(session, user_id, family, tc)` (`user_benchmark_percentiles_service.py:250`). Shape in RESEARCH "Parity test". Per memory: every non-guest Game insert needs finally-cleanup (lottery isolation).

### `frontend/src/hooks/useEndgameRankedStats.ts` (hook)

**Analog:** `frontend/src/hooks/useEndgames.ts` 20-45:
```ts
const ENDGAME_STALE_TIME = 5 * 60 * 1000;
export function useEndgameOverview(filters: FilterState, options: { window?: number; enabled?: boolean } = {}) {
  ...
  return useQuery({
    queryKey: ['endgameOverview', params, window],
    queryFn: () => endgameApi.getOverview({ ...params, window }),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
    // Quick 260529-015: gate the fetch on Tier-2 readiness ...
    enabled,
  });
}
```
Use queryKey `['endgameOverview', 'ranked']` so invalidations in `App.tsx:1052` / `Import.tsx:209,413` still match; keep `enabled: tier2` gating. No filters argument (D-01).

### `frontend/src/hooks/useEndgameStatsTc.ts` (store, localStorage)

**Analog:** `frontend/src/lib/engineSettings.ts` (module store via `useSyncExternalStore`, listener Set, flat key). Read/write with try/catch and validation (lines 114-123, 152-157):
```ts
function readCount(id: CountSettingId): number {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEYS[id]);
    if (raw === null || raw.trim() === '') return defaultFor(id);
    ...
  } catch {
    return defaultFor(id);
  }
}
export function setCountSetting(id, value): void {
  if (!Number.isInteger(value) || !isValidForSetting(id, value)) return;
  try { localStorage.setItem(SETTINGS_STORAGE_KEYS[id], String(value)); } catch { ... }
}
```
Validate stored value against the `TimeControlBucket` union; fall back to D-12 default derived from payload. Named constant for the storage key. `trackFeature('option-change', { target: 'endgame-stats-tc', ... })` only in the click handler, never in restore/fallback effects.

### `RankedMetricPopover.tsx` (component)

**Shell analog:** `frontend/src/components/popovers/MetricStatPopover.tsx` (whole file, ~100 lines): `HOVER_OPEN_DELAY_MS = 100`, `useTrackedPopoverOpen(testId)`, `PopoverPrimitive.Root/Trigger asChild <span role="button" tabIndex={0} data-testid={testId}>`, `Portal` + `Content side="top" sideOffset={4}` with `text-xs` body classes (documented exception to text-sm), hover enter/leave clearTimeout handling. Copy verbatim, replace `<MetricStatTooltip>` body.

**Copy analog:** `frontend/src/components/charts/PercentileChip.tsx` 193-262 — percentile statement ("Your <em>recent</em> {metricLabel} is {phrasing} of similarly-rated players"), clamp `Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(percentile)))` (line 200), recent-games basis ("Based on {nGames} of your recent {tc} games over the last 36 months, vs opponents ..." line 239), `COPY_FILTER_INDEPENDENCE` (line 75), anchor-composition branches. Drop the aggregated path (251-262). Footer: n / CI / p greyed below a separator. No flame icons.

### `PercentileBar.tsx` (component)

**Analog:** `PercentileChip.tsx` clamp logic + `MiniBulletChart.tsx` (kept; Openings uses it) for bar drawing. Named constants `PERCENTILE_TYPICAL_LOW = 25`, `PERCENTILE_TYPICAL_HIGH = 75`; colors from `lib/theme.ts`. Below-floor / pending / unranked slot variants (D-09/D-11 copy in CONTEXT specifics).

### Section components (rework of `frontend/src/components/charts/Endgame*`)

**Analog:** `EndgameMetricsByTcSection.tsx` (124 lines): currently `useState<string[]>` expandedTcs accordion with `trackFeature('panel-open', { target: 'endgame-metrics-tc' })` (lines 69-85) and testids `endgame-metrics-tc-section`, `-empty` (92-101). Replace the accordion with `<TcSwitch>` bound to the shared store; keep section testids and empty branch. Leave old `PANEL_TARGETS` entries in analytics (do not rename).

### `frontend/src/pages/Endgames.tsx` — hide filter UI on Stats (D-02) + extract `EndgameStatsTab`

**Analog:** same file. Desktop `SidebarLayout panels={[{ id: 'filters', ... }]} activePanel={sidebarOpen} onActivePanelChange={handleSidebarOpenChange}` (920-952): pass `panels={activeTab === 'stats' ? [] : [...]}` and `setSidebarOpen(null)` on tab change to stats. Mobile sticky Filters `<Button data-testid="btn-open-filter-drawer">` (996-1010): render only on games tab; close drawer on switch. `useEndgameOverview(appliedFilters, { enabled: tier2 })` (357) moves to Games tab `/stats` hook; `toInsightsFilters` (41, 222) removed. Never call `setAppliedFilters` on hide. Page is at the eslint complexity baseline (54-61, 77-85): extract, don't add branches.

## Shared Patterns

### Auth / user scoping
**Source:** `app/routers/endgames.py` 29-30 — `user: Annotated[User, Depends(current_active_user)]`; `user_id` only from auth (V4 docstring in `fetch_for_user`). SQL `user_id` only via `CAST(:user_id AS int)` bindparam.

### Sequential DB access
**Source:** router docstring 44-48 ("All internal queries execute sequentially on one AsyncSession (no asyncio.gather)"). Applies to ranked service and insights.

### Error handling (insights)
**Source:** `app/routers/insights.py` 170-185 — `InsightsValidationFailure` / `InsightsProviderError` → 502 `InsightsErrorResponse`. Services: `sentry_sdk.capture_exception` + `set_context`, no variables in messages.

### Popover shell + analytics
**Source:** `MetricStatPopover.tsx` + `useTrackedPopoverOpen`; `OPTION_TARGETS` in `frontend/src/lib/analytics.ts:440` (append, never rename).

### Literal types
`TimeControlBucket`, `CdfMetricId` already exist (used in `fetch_for_user` signature); new `RankStatus = Literal["ranked", "below_floor", "unranked", "pending"]`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `ComparedToPeersCard.tsx` | component | — | Dot-plot card is new; use sketch `.planning/sketches/009-endgame-stats-percentile-first/index.html` |
| Type breakdown table (replacing `EndgameTypeCard`/`EndgameTypeTcCard`) | component | — | No table-with-typical-range in codebase; use sketch + `PER_CLASS_TC_GAUGE_ZONES` from `frontend/src/generated/endgameZones.ts` |

## Retirement (Plan 04, no analog needed)
`/endgames/overview` + `get_endgame_overview`, `_aggregate_per_tc_percentile` (`endgame_service.py:1509`), `_build_per_tc_breakdown`, `_per_tc_game_counts`, aggregated schema fields, `EndgameGauge`, `PercentileChip`, `MetricStatPopover`, `MetricStatTooltip`, `AchievableScorePopover`, `EndgameTypeCard`, `EndgameTypeTcCard`, `EndgameOverallScoreGapRow`, `frontend/src/lib/insightsFilters.ts`. Keep `MiniBulletChart`. Update comments in `FlawBulletPopover.tsx` / `PersonaEloDisclosurePopover.tsx` referencing MetricStatPopover.

## Metadata
**Analog search scope:** `app/routers`, `app/services`, `app/repositories`, `frontend/src/hooks`, `frontend/src/lib`, `frontend/src/components/{charts,popovers}`, `frontend/src/pages`, `tests/services`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-11
