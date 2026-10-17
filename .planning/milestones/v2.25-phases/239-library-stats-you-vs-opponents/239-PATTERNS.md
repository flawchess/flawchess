# Phase 239: Library Stats You-vs-Opponents Redesign - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 22 (new + modified)
**Analogs found:** 21 / 22

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/benchmarks/chapter5.py` (mod) | offline script | batch | itself (`_per_user_cte` 126+, `_FLAW_DELTA_METRICS` 58-76) | exact (extend) |
| `.claude/skills/benchmarks/SKILL.md` §5 (mod) | doc | n/a | itself §5 | exact |
| `tests/scripts/benchmarks/test_chapter5_diff.py` (mod) | test (on-demand gate) | batch | itself | exact |
| `app/services/flaw_delta_zones.py` (mod) | config/registry | transform | itself (lines 1-60) | exact |
| `app/services/tactic_delta_zones.py` (NEW) | config/registry | transform | `app/services/flaw_delta_zones.py` | exact |
| `app/schemas/library.py` (mod) | model (Pydantic) | request-response | `app/schemas/endgames.py` `RankedTcStats` / `EndgameRankedStatsResponse` (519-557) | exact |
| `app/repositories/library_repository.py` (mod) | repository | CRUD (read) | itself `fetch_flaw_comparison` (~2014), `fetch_tactic_comparison` (~2300), `count_filtered_and_analyzed` (~1880) | exact |
| `app/services/library_service.py` (mod) | service | request-response | itself `_compute_bullets`/`get_flaw_comparison` (1539-1700) + `endgame_ranked_service.build_ranked_stats` (~915-935) | exact |
| `app/routers/library.py` (mod, signatures mostly unchanged) | router | request-response | itself (218-262) | exact |
| `tests/services/test_flaw_comparison.py`, `tests/services/test_tactic_comparison_service.py` (mod) | test | request-response | themselves + `tests/services/test_endgame_ranked_service.py` | exact |
| `tests/routers/test_library_tactic_comparison.py` (+ flaw-comparison router test) | test | request-response | itself | exact |
| `frontend/src/lib/gapBar.ts` (NEW) | utility | transform | `frontend/src/components/endgames/stats/rankedMetrics.ts` + sketch `index.html:223-226,362-380` | role-match |
| `frontend/src/components/library/stats/GapBar.tsx` (NEW) | component | transform | `components/endgames/stats/PercentileBar.tsx` | exact |
| shared popover shell (NEW, e.g. `components/ui/metric-info-popover.tsx`) | component | event-driven | `components/endgames/stats/RankedMetricPopover.tsx` 118-183 | exact (extract) |
| `components/library/stats/GapPopover.tsx` (NEW) | component | event-driven | `RankedMetricPopover.tsx` | exact |
| `components/library/stats/GapRow.tsx` (NEW) | component | transform | `components/endgames/stats/RankedMetricRow.tsx` | exact |
| `frontend/src/hooks/tcSelectionStore.ts` (NEW) + `useLibraryStatsTc.ts` (NEW) + `useEndgameStatsTc.ts` (mod → wrapper) | hook/store | event-driven | `frontend/src/hooks/useEndgameStatsTc.ts` | exact |
| `components/endgames/stats/TcSwitch.tsx` (mod → presentational) | component | event-driven | itself | exact |
| `FlawTiles`, `WhatStandsOut`, `ContextTagCards`, `TacticTables` (NEW, `components/library/stats/`) | component | transform | `FlawStatsBand.tsx`, `FlawComparisonGrid.tsx`, `TacticComparisonGrid.tsx` (being replaced), `EndgameStatsTab.tsx` SectionInsightSlot | role-match |
| `components/insights/ShellyQuote.tsx` (mod: export `EXPAND_HINT`) | component | n/a | itself line 7, 47-50 | exact |
| `frontend/src/hooks/useLibrary.ts`, `types/library.ts`, `lib/analytics.ts` (mod) | hook/types/config | request-response | themselves (`useLibraryFlawComparison` 204-215) | exact |
| `WhatStandsOut` ranking logic | utility | transform | none in codebase (sketch `renderHighlights` only) | no analog |

All analog paths verified git-tracked (`git ls-files`).

## Pattern Assignments

### `app/services/tactic_delta_zones.py` (NEW) and `app/services/flaw_delta_zones.py` (mod)

**Analog:** `app/services/flaw_delta_zones.py` (60 lines)

Module docstring + frozen dataclass + `Mapping` registry (lines 1-38):
```python
"""Flaw-delta zone registry: authoritative backend source for per-bullet zone constants.

Backend is the single source of truth per Phase 115 D-07. The endpoint embeds
zone_lo / zone_hi / domain in every FlawBullet response ...
This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""
from collections.abc import Mapping
from dataclasses import dataclass

@dataclass(frozen=True)
class FlawDeltaZoneSpec:
    zone_lo: float
    zone_hi: float
    domain: float

FLAW_DELTA_ZONES: Mapping[str, FlawDeltaZoneSpec] = {
    "mistake": FlawDeltaZoneSpec(zone_lo=-0.23, zone_hi=+0.20, domain=1.0),
    "blunder": FlawDeltaZoneSpec(zone_lo=-0.31, zone_hi=+0.25, domain=1.4),
    ...
```
Changes: drop `domain`; drop `flaw_rate` (line 40), `hasty_miss`/`low_clock_miss` (58-59); key by `Literal` metric; add `ZONE_TC_FOR` stopgap mapping (blitz/bullet → rapid, documented in docstring per D-09); values per zone-TC (RESEARCH Pattern 3 shape). Keep the 0.01 grid comment (24-26). Import `TimeControlBucket` from `app/schemas/normalization.py:19`. Tactic registry: same module shape, `Mapping[tuple[TacticFamily, Literal["missed","allowed"]], Mapping[ZoneTc, ZoneBand] | None]`, `None` = `has_zone=False`, units per 100 games.

---

### `app/schemas/library.py` (mod)

**Analog for per-TC wrapper:** `app/schemas/endgames.py` lines 519-557
```python
class RankedTcStats(BaseModel):
    """Everything the Stats tab shows for one time control, ..."""
    tc: TimeControlBucket
    ranked_games: int
    ...

class EndgameRankedStatsResponse(BaseModel):
    """GET /api/endgames/ranked-stats.

    tcs lists only time controls with at least one ranked-sample game, ordered
    bullet, blitz, rapid, classical (D-14). ..."""
    tcs: list[RankedTcStats]
```
**Existing bullets to modify:** `FlawBullet` (library.py 365-389: `tag: str` → Literal; remove `domain`; add `low_sample: bool`), `FlawComparisonResponse` (392-406 → `tcs: list[FlawComparisonTc]` + `analyzed_gate`), `TacticBullet` (414-438: `family: str` → `TacticFamily` Literal, comments change to per-100-games, add `low_sample`), `TacticComparisonResponse` (441-460: drop top-6 docstring contract). Add `FlawTrendTc` + `trend_by_tc` on `FlawStatsResponse` (346). Keep inline-comment-per-field style.

---

### `app/services/library_service.py` (mod)

**Analog:** itself, `_compute_bullets` (1539-1617) and `get_flaw_comparison` (1620-1700).

Per-game accumulation pattern to keep (1557-1571):
```python
for row in rows:
    user_moves = int(row.user_moves) if row.user_moves else 0
    if user_moves <= 0:
        continue
    for tag in tags:
        player_count = int(getattr(row, f"player_{tag}", 0) or 0)
        opp_count = int(getattr(row, f"opp_{tag}", 0) or 0)
        ...
        deltas_by_tag[tag].append(player_rate - opp_rate)
```
Stats: reuse `_compute_mean_ci` (1496) and `_two_sided_p` (1519) unchanged. Add `low_sample = p_total + o_total < LOW_SAMPLE_MIN_FLAWS` (new constant `LOW_SAMPLE_MIN_FLAWS: int = 40` near `FLAW_COMPARISON_GATE` at 1493). Note depth: the existing nested loop is already at depth 3; per-TC bucketing must be a separate helper (`_bucket_rows_by_tc`) to stay ≤4.

Error handling to keep (1696-1700):
```python
except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
    sentry_sdk.set_context("flaw_comparison", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise
```
Remove the pooled early-return (1674-1680); replace with per-TC `below_gate`.

**Per-TC assembly analog:** `app/services/endgame_ranked_service.py`
```python
RANKED_TC_ORDER: Final[tuple[TimeControlBucket, ...]] = ("bullet", "blitz", "rapid", "classical")  # line 105
...
tcs = [
    _build_tc_stats(tc, inputs.games_by_tc[tc], inputs, full, since)
    for tc in RANKED_TC_ORDER
    if inputs.games_by_tc.get(tc)
]
return EndgameRankedStatsResponse(tcs=tcs)   # ~925-929
```
Sequential queries rule from the docstring at 178-183 ("never asyncio.gather on a session"). Library: one per-game query with `Game.time_control_bucket.label("tc")`, bucket in Python, skip NULL buckets, emit only TCs with analyzed_n ≥ 1.

Tactic: `_compute_tactic_bullets` (1718) multiply per-game counts by `PER_100_GAMES = 100`; delete `_sort_key` / top-6 (1801-1815, 1924-1958), emit fixed `FAMILY_TO_MOTIF_INTS` order, missed then allowed; zones from `tactic_delta_zones`.

---

### `app/repositories/library_repository.py` (mod)

**Analog:** itself. Add `Game.time_control_bucket.label("tc")` to anchor subqueries + `group_by` in `fetch_flaw_comparison` (~2014) and `fetch_tactic_comparison` (~2300); remove flaw_rate columns (~2085-2097) and combo columns (~2258-2288). Keep the tactic join gate (2400-2406):
```python
.outerjoin(GameFlaw, (GameFlaw.game_id == anchor_subq.c.game_id) & (GameFlaw.user_id == user_id)
           & motif_col.isnot(None) & (conf_col >= tactic_confidence_min))
```
New count-by-TC uses `_filtered_games_base(...)` ∩ `_analyzed_game_ids_subquery(user_id)` (filters via `apply_game_filters`, never duplicated). `fetch_flaw_trend_rows` gains the TC column for `trend_by_tc`.

---

### `app/routers/library.py` (mod)

**Analog:** itself, lines 218-259 (`/flaw-comparison`). Pattern: `Annotated[...Depends]` session/user, Query params, date guard → 422, delegate to service with `user_id=user.id` (IDOR comment). Only docstrings change ("15-bullet" → per-TC); keep params so sidebar filters still apply (D-01).

---

### `scripts/benchmarks/chapter5.py` (mod)

**Analog:** itself. Metric tuple at 58-76:
```python
_FLAW_DELTA_METRICS: tuple[tuple[str, str], ...] = (
    ("flaw_rate", "delta_flaw_rate"),   # remove
    ("low_clock", "delta_low_clock"),
    ...
    ("hasty_miss", "delta_hasty_miss"),        # remove
    ("low_clock_miss", "delta_low_clock_miss"),# remove
    ("mistake", "delta_mistake"),
    ("blunder", "delta_blunder"),
)
```
Constants style (39-50): `FLAW_DELTA_MIN_GAMES: int = 20`, `_CELL_CONTRIBUTOR_FLOOR: int = 30`. Add `FULL_ANALYSIS_TRANCHES = ("classical", "rapid")` and one `_base_games_cte()` helper used by both `_per_user_cte()` (126) and `_compute_viability()` (RESEARCH Pattern 1 has the exact SQL). Import `FAMILY_TO_MOTIF_INTS` from `app.repositories.library_repository` and `MIN_TACTIC_CHIP_CONFIDENCE` from `app.services.library_service` (do not copy ints). `TypedDict` result types (`MetricBlock` 78, `ViabilityRow` 85, `Chapter5Values` 95) extended for tactic rows. Report: `render()` (463) / `_metric_section` (515) / `_render_viability` (538); tactics as one compact table; new unit `"per100g"` in `scripts/benchmarks/render.py:72-75`. Update `SECTION` string (35).

---

### `frontend/src/components/library/stats/GapBar.tsx` (NEW)

**Analog:** `frontend/src/components/endgames/stats/PercentileBar.tsx`

Imports (1-15): `cn`, theme `PERCENTILE_TRACK`, `PERCENTILE_TYPICAL_BAND`, `PERCENTILE_MEDIAN_TICK`; dot colours from `rankedMetrics.percentileBandColor` palette (`ZONE_DANGER`/`GAUGE_NEUTRAL`/`ZONE_SUCCESS`).

Gate slot (17-65): copy `RankStatusLine` shape for "Not enough analyzed games yet (12 of 20)":
```tsx
case 'below_floor':
  return `Not enough games to rank yet (${floorN} of ${floorRequired})`;
...
<p className={cn('text-sm text-muted-foreground', className)} data-testid={testId}>{text}</p>
```
Track/band/tick/dot markup (106-131), with band `left`/`width` from `gapPosition(hi)`..`gapPosition(lo)` and the tick at 50%:
```tsx
<div className="relative h-2.5 flex-1 rounded-full" style={{ backgroundColor: PERCENTILE_TRACK }} data-testid={`${testId}-track`}>
  <div className="absolute inset-y-0 rounded-sm" style={{ left: ..., width: ..., backgroundColor: PERCENTILE_TYPICAL_BAND }} data-testid={`${testId}-band`} />
  <div className="absolute -inset-y-[3px] w-px" style={{ left: '50%', backgroundColor: PERCENTILE_MEDIAN_TICK }} data-testid={`${testId}-median`} />
  <div className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background" style={{ left: `${pos}%`, backgroundColor: color }} data-testid={`${testId}-dot`} />
</div>
<span className="min-w-11 text-right text-sm font-semibold tabular-nums" style={{ color }} data-testid={`${testId}-number`}>...</span>
```
Differences: no band when `has_zone=false`; number span shows `gapWords` (white when typical, green/red otherwise; dot blue for typical, D-00b); faded row for `low_sample`.

**Test analog:** `frontend/src/components/endgames/stats/PercentileBar.test.tsx` (jsdom header, `normalized()` colour helper lines 11-15, `it.each` colour cases).

---

### `frontend/src/lib/gapBar.ts` (NEW)

**Analog:** sketch math (RESEARCH Pattern 5, verbatim) + `rankedMetrics.ts` style (named exported constants and pure fns). Add guards for `hi - lo === 0` and `s === 0`. Pure-function vitest file alongside (`gapBar.test.ts`).

---

### Shared popover shell + `GapPopover.tsx` (NEW)

**Analog:** `frontend/src/components/endgames/stats/RankedMetricPopover.tsx` 118-183. Extract everything except the body into a generic `children`-taking shell; `RankedMetricPopover` then wraps it.
```tsx
const HOVER_OPEN_DELAY_MS = 100;
const [open, setOpen] = useTrackedPopoverOpen(testId);
const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
React.useEffect(() => () => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }, []);
...
<PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
  <PopoverPrimitive.Trigger asChild>
    <span role="button" tabIndex={0} aria-label={`About ${label}`} data-testid={testId}
      className="inline-flex cursor-pointer items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <Search className="h-4 w-4" />
    </span>
  </PopoverPrimitive.Trigger>
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content side="top" sideOffset={4} ... data-testid={`${testId}-popover`}
      className={cn('z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background', ...animations)}>
      {children}
```
Body footer pattern: `FOOTER_SEPARATOR = ' · '` (line 30), `formatCiBound`, `formatPValue` from `rankedMetrics.ts`. TestId: `gap-popover-{tag-kebab}-tc-{tc}` (TC segment collapses in analytics). **Test analog:** `RankedMetricPopover.test.tsx`.

---

### `GapRow.tsx` (NEW)

**Analog:** `RankedMetricRow.tsx` (51 lines) — label + Search trigger on the left, value right, bar below:
```tsx
<div className="flex flex-col gap-1" data-testid={testId}>
  <div className="flex items-center justify-between gap-2">
    <span className="flex items-center gap-1.5">
      <span className="font-semibold">{label}</span>
      <RankedMetricPopover ... testId={`ranked-metric-${metricSlug(metric.metric)}-tc-${tcStats.tc}`} />
    </span>
    ...
  </div>
  <PercentileBar ... testId={`${testId}-bar`} />
</div>
```
Add the one-line hint under the label (D-00f).

---

### `tcSelectionStore.ts` / `useLibraryStatsTc.ts` (NEW), `useEndgameStatsTc.ts` (mod)

**Analog:** `frontend/src/hooks/useEndgameStatsTc.ts` (121 lines). Lift into a factory parameterised by `storageKey` + `pickDefault`; module state = `chosenTc` (undefined/null/tc), `pinnedDefaultTc`, `listeners`. Keep:
- validated, try/catch storage read (37-45) and write (63-73)
- `useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)` (111)
- pin-after-render `useEffect` (114-118, FE-IN-05)
- `TC_ORDER` (25) tie-break
D-04 picker = copy `pickDefaultTc` (87-102) with `analyzed_n >= analyzed_gate` replacing anchor floor and `analyzed_n` replacing `ranked_games`. Key `'library_stats_tc'`. `useEndgameStatsTc` becomes a thin wrapper keeping its exports (`ENDGAME_STATS_TC_STORAGE_KEY`, `pickDefaultTc`).

**Test analog:** `frontend/src/hooks/__tests__/useEndgameStatsTc.test.ts` — `vi.resetModules()` + dynamic `await import(...)` in `beforeEach` (module state), `localStorage.clear()`, `pickDefaultTc` describe cases (most games, faster tie-break, above-floor preference, fallback). Note memory: hoist `await import` to `beforeEach`/`beforeAll`, never inside the test body.

---

### `TcSwitch.tsx` (mod → presentational)

**Analog:** itself (57 lines). Replace internal `useEndgameStatsTc(tcs)` + hardcoded `target: 'endgame-stats-tc'` (21, 26) with props `tcs: readonly TimeControlBucket[]`, `selected`, `onSelect`; callers do the `trackFeature('option-change', { target: 'library-stats-tc', value: tc })` (register in `lib/analytics.ts` `OPTION_TARGETS` ~449/486). Keep button markup 39-52 and testids `tc-switch-${sectionId}-${tc}`.

---

### Advanced tactics accordion + `ShellyQuote` `EXPAND_HINT`

**Analog:** `EndgameStatsTab.tsx` `SectionInsightSlot` (227-290):
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="insight" data-testid={...} className="charcoal-texture rounded-md overflow-hidden">
    <AccordionTrigger data-testid={`...-trigger`} band>{header}</AccordionTrigger>
    <AccordionContent className="p-4">...</AccordionContent>
```
Hint markup from `ShellyQuote.tsx` 47-50 (export the constant at line 7):
```tsx
<span className="text-xs font-normal text-muted-foreground group-aria-expanded/accordion-trigger:hidden">
  {EXPAND_HINT}
</span>
```
Track open with `useTrackedOpen`. Non-collapsible card header band: `<div className="w-full flex items-center gap-2 px-4 py-3 bg-card-band">` (same file). h2: `className="font-brand text-lg font-semibold text-foreground"` (`MetricsSection.tsx:34`).

---

### `frontend/src/hooks/useLibrary.ts` (mod)

**Analog:** itself 204-215:
```ts
export function useLibraryFlawComparison(filters: FilterState, flawFilter: FlawFilterState) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaw-comparison', params],
    queryFn: () => libraryApi.getFlawComparison(params),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```
Query keys must NOT include the selected TC (switch is client-only). `useTacticComparison` (228-245) loses the `tacticFamilies` dimension if the family filter is dropped (planner decides).

---

### Backend tests

- `tests/services/test_flaw_comparison.py`: update `_EXPECTED_TAGS` (35-50, drop flaw_rate + combos → 12), replace `test_registry_has_15_metrics`/`test_combos`, add per-TC bucketing, `below_gate` per TC, `low_sample` boundary (39 vs 40). Imports pattern (16-28): `from app.services.library_service import FLAW_COMPARISON_GATE, _compute_mean_ci, get_flaw_comparison`.
- `tests/services/test_tactic_comparison_service.py`: replace top-6 tests with fixed-order test, assert unit (1-vs-0 game → `you_rate == 100.0`), registry `has_zone`.
- Router: `tests/routers/test_library_tactic_comparison.py` (`_register_and_login` helper, `httpx.ASGITransport(app=app)`, 200/401/422 cases) — mirror for `/flaw-comparison` shape `tcs[]`.
- Per-TC shape assertions: `tests/services/test_endgame_ranked_service.py`.
- Memory: non-guest `Game` inserts need finally-cleanup (lottery isolation).

## Shared Patterns

### Sentry in services
**Source:** `app/services/library_service.py` 1696-1700. Apply to every modified service entry point; context via `set_context`, no variables in messages.

### Filter application
**Source:** `_filtered_games_base` → `apply_game_filters` in `library_repository.py`. All new count/row queries go through it (D-01).

### TC ordering
**Source:** `RANKED_TC_ORDER` (`endgame_ranked_service.py:105`) / `TC_ORDER` (`useEndgameStatsTc.ts:25`): bullet, blitz, rapid, classical.

### Popover tracking + testIds
**Source:** `useTrackedPopoverOpen(testId)` (`RankedMetricPopover.tsx:123`); testIds with `-tc-{tc}` segment, never free values (frontend/CLAUDE.md).

### Below-gate slot copy
**Source:** `PercentileBar.tsx` `rankStatusText` 21-36, `text-sm text-muted-foreground`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| "What stands out" ranking (`WhatStandsOut.tsx` / helper in `gapBar.ts`) | utility | transform | Only exists in sketch `renderHighlights` (`.planning/sketches/010-library-stats-you-vs-opponents/index.html`); use RESEARCH Pattern 8 |

## Metadata

**Analog search scope:** app/services, app/schemas, app/routers, app/repositories, scripts/benchmarks, tests/services, tests/routers, frontend/src/components/endgames/stats, frontend/src/hooks, frontend/src/components/insights
**Files scanned:** ~25
**Pattern extraction date:** 2026-10-12
