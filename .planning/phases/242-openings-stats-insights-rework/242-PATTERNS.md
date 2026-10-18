# Phase 242: Openings Stats + Insights Rework - Pattern Map

**Mapped:** 2026-10-17
**Files analyzed:** 34 (new + modified + deleted)
**Analogs found:** 31 / 34

RESEARCH.md already holds exhaustive file:line references (Patterns B1-B6, F1-F7). This map assigns each file
an analog and quotes the load-bearing excerpts; it does not repeat the research tables.

## File Classification

| File | Action | Role | Data Flow | Closest Analog | Match |
|------|--------|------|-----------|----------------|-------|
| `app/services/opening_eval.py` | new | utility/service | transform | `app/services/stats_service.py:424-439` (inline finalizer) | exact |
| `app/services/repertoire_recency.py` | new | service | request-response | `app/routers/train.py:65` (NowUtc) + research B2 SQL | role-match |
| `app/repositories/stats_repository.py` | modify (`query_nth_recent_played_at`, fingerprint + `ply_count` in WDL/top queries) | repository | CRUD read | same file `query_position_wdl_batch` (:457-474), `query_top_openings_sql_wdl` (:378) | exact |
| `app/services/stats_service.py` | modify (reorder, dedupe, split, constants) | service | batch/transform | itself :280-387 | exact |
| `app/services/openings_service.py` | modify (centring :186-201, weekly series :283-345) | service | transform | `app/services/endgame_service.py:1222-1254` | exact |
| `app/services/opening_insights_service.py` | modify (partition after `_rank_section`, centring :394-422) | service | batch | itself `_build_sections` :839-965 | exact |
| `app/services/opening_insights_constants.py` | modify (caps, comments) | config | - | itself :52-86 | exact |
| `app/services/eval_confidence.py` | modify (docstrings only) | utility | - | itself | exact |
| `app/schemas/stats.py`, `schemas/openings.py`, `schemas/opening_insights.py` | modify (99% CI, score p/CI, `is_current`, cutoffs, `per_week_games`, not_clear lists) | model | - | `schemas/stats.py:66-71` existing eval fields | exact |
| `app/routers/stats.py`, `app/routers/insights.py` | modify (add `now_utc`) | route | request-response | `app/routers/train.py:62-65` | exact |
| `tests/services/test_opening_eval.py`, `test_repertoire_recency.py`, updates to `test_stats_service.py`, `test_opening_insights_service.py`, `test_openings_service.py` | new/modify | test | - | existing `tests/services/test_opening_insights_service.py` | role-match |
| `frontend/src/pages/Openings.tsx` | modify (drop insights tab, redirect) | page | - | itself :69-104, :572-574 | exact |
| `frontend/src/types/openingsTab.ts` (or export in Openings) | new (`OpeningsTab` union) | type | - | union at `hooks/useTabReset.ts:16` | exact |
| `hooks/useDeepLinkHighlight.ts`, `useTabReset.ts`, `useOpeningsHandlers.ts`, `OpeningsMobileBoardPanel.tsx`, `lib/openingsBoardLayout.ts` | modify (union, comments) | hook | - | - | exact |
| `frontend/src/components/openings/stats/OpeningColorSwitch.tsx` | new | component | event-driven | `components/stats/TcSwitch.tsx:31-70` | exact |
| `frontend/src/pages/openings/StatsTab.tsx` | rewrite | page/component | request-response | `components/library/stats/LibraryStatsSections.tsx` + `StickyTcBar` | role-match |
| `frontend/src/lib/openingVerdict.ts` (+ test) | new | utility | transform | `lib/gapBar.ts:73-180` | role-match |
| `frontend/src/components/openings/stats/VerdictBar.tsx` (shared Score/Eval bar; also used by Moves/Games D-17) | new | component | - | `components/library/stats/GapBar.tsx:77-152` | role-match (direction differs) |
| `frontend/src/components/openings/stats/VerdictPopover.tsx` | new | component | - | `components/library/stats/GapPopover.tsx:80-125` | role-match |
| `frontend/src/components/openings/stats/RepertoireTable.tsx` (+ row, + test) | new | component | - | `components/endgames/stats/TypeTable.tsx` (`RangeCell` :110-160) | exact |
| `frontend/src/hooks/useRepertoireRows.ts` | new | hook | transform | bookmark-row building in `pages/openings/StatsTab.tsx:56-91` | role-match |
| `frontend/src/hooks/useOpeningRowTimeSeries.ts` | new | hook | request-response | `hooks/useOpeningsChartData.ts:158-176` | exact |
| `frontend/src/components/openings/stats/FindingCards.tsx` / `NotClearYetList.tsx` | new | component | - | `components/insights/OpeningFindingCard.tsx`, `OpeningInsightsBlock.tsx:95-103,254,271` (to be deleted after copying) | exact |
| `frontend/src/components/charts/ScoreChart.tsx` | rewrite (single series + volume) | component | - | `EndgameScoreOverTimeChart.tsx:121-124,170-291` | exact |
| `frontend/src/components/charts/PositionResultsPanel.tsx` | modify (opening-end uses VerdictBar, D-17) | component | - | itself :225-250 (endgame branch kept) | exact |
| `frontend/src/components/charts/EvalConfidenceTooltip.tsx` / `EvalConfidencePopover` | modify (opening-end copy) | component | - | itself | exact |
| `frontend/src/lib/analytics.ts` | modify (targets) | config | - | `PANEL_TARGETS` :362-376, `OPTION_TARGETS` :434-445 | exact |
| `frontend/src/hooks/usePositionBookmarks.ts` | modify (invalidate `mostPlayedOpenings`) | hook | - | itself :12-52 | exact |
| `frontend/src/hooks/useOpeningsChartData.ts`, `PositionBookmarkCard.tsx`, `Openings.tsx:7-9` | modify (D-16: remove include/exclude toggle + `bookmark-chart-enabled-<id>` localStorage) | hook/component | - | - | n/a (deletion) |
| `types/stats.ts`, `types/openings.ts`, `types/insights.ts`, `types/position_bookmarks.ts` | modify (TS mirrors) | type | - | backend schemas | exact |
| Deletions: `InsightsTab.tsx`, `OpeningInsightsBlock(.test).tsx`, `OpeningFindingCard(.test).tsx`, `OpeningStatsSection.tsx`, `OpeningStatsCard(.test).tsx`, `lib/scoreConfidence.ts` (if unused) | delete | - | - | knip (Pitfall 10) | n/a |
| `CHANGELOG.md` | modify | docs | - | `[Unreleased]` | exact |

## Pattern Assignments

### `app/services/opening_eval.py` (new, transform)

**Analog:** `app/services/stats_service.py:415-439` (copy shape, then replace the call site and 3 siblings: `stats_service.py:502-514`, `openings_service.py:186-201`, `opening_insights_service.py:394-422`). Do NOT touch `endgame_service.py:747`.

```python
avg_eval_pawns: float | None = None
eval_ci_low_pawns: float | None = None
eval_ci_high_pawns: float | None = None
eval_n = 0
eval_p_value: float | None = None
eval_confidence: Literal["low", "medium", "high"] = "low"

if pe is not None and pe.eval_n_mg > 0:
    # H0: mean == 0 cp ...   <- comment to rewrite: H0 = colour baseline
    confidence_mg, p_value_mg, mean_cp_mg, ci_half_mg = compute_eval_confidence_bucket(
        pe.eval_sum_mg, pe.eval_sumsq_mg, pe.eval_n_mg,
    )                       # new: baseline_cp=resolve_eval_baseline_pawns(color) * CENTIPAWNS_PER_PAWN
    avg_eval_pawns = mean_cp_mg / 100.0  # raw, uncentred
    if pe.eval_n_mg >= 2:
        eval_ci_low_pawns = (mean_cp_mg - ci_half_mg) / 100.0
        eval_ci_high_pawns = (mean_cp_mg + ci_half_mg) / 100.0
```
Return a TypedDict (CLAUDE.md: TypedDict for internal structures) adding `eval_ci99_low/high_pawns` via
`ci99_half = ci_half * VERDICT_CI_Z_99 / OPENING_INSIGHTS_CI_Z_95` (`score_confidence.py:69`). Baselines:
`EVAL_BASELINE_PAWNS_WHITE/BLACK` (`opening_insights_constants.py:85-86`); `None` colour resolves to white.

### `app/services/repertoire_recency.py` + `stats_repository.query_nth_recent_played_at`

Use the RESEARCH "Cutoff (backend)" code example verbatim (select `Game.played_at` + `apply_game_filters(..., color=color)` + `.order_by(Game.played_at.desc()).offset(CURRENT_REPERTOIRE_RECENT_GAMES - 1).limit(1)`). Repository holds the SQL; the service does `min(nth, now_utc - timedelta(days=CURRENT_REPERTOIRE_MIN_DAYS))`, `None` when fewer than 200 games. `is_current(last, cutoff) = cutoff is None or last is None or last >= cutoff`.

### Routers `stats.py:87`, `insights.py:107`

**Analog:** `app/routers/train.py:62-65`
```python
#: The current UTC instant, dev-clock-shiftable. Real clock outside development.
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]
```
Add `now_utc: NowUtc` and pass to the service. Routers stay thin.

### `stats_service.py` most-played reorder

Analog is the function itself (:280-387). Pipeline per colour, sequential awaits (test `test_no_asyncio_gather_in_stats_service`): top query (limit `MOST_PLAYED_FETCH_LIMIT = 60`) → `query_position_wdl_batch` (+ `func.sum(func.distinct(Game.id))` fingerprint) → dedupe by `(total, id_sum)` keep deeper `ply_count` → drop bookmark twins (replay moves like `position_bookmark_repository.py:277-321`, `compute_hashes(board)[2]`) → split `is_current` → cap 10/10 → phase-entry batch on survivors → `finalize_opening_eval`. Switch `row[5]` index access to `row.full_hash` (Pitfall 5). Score p/99% CI: `compute_confidence_bucket` + `wilson_bounds(p, n, z=VERDICT_CI_Z_99)` (`score_confidence.py:82, 354`); reuse the same for bookmark time series (D-18).

### `openings_service._build_bookmark_time_series` weekly (B6)

**Analog:** `app/services/endgame_service.py:1222-1254`
```python
iso_year, iso_week, iso_weekday = played_at.isocalendar()
per_week_total[(iso_year, iso_week)] = per_week_total.get((iso_year, iso_week), 0) + 1
...
monday = (played_at - timedelta(days=iso_weekday - 1)).date()
data_by_week[(iso_year, iso_week)] = {
    "date": monday.isoformat(),
    ...
    "per_week_total_games": per_week_total[(iso_year, iso_week)],
```
Keep last rolling value per week (`ROLLING_WINDOW_SIZE = 50`, `MIN_GAMES_FOR_TIMELINE = 10`), add `per_week_games`.

### `opening_insights_service._build_sections` partition (B5)

After `_rank_section`: `high` (confidence == "high", current-first stable sort, cap `FINDINGS_CARD_CAP = 5`), `medium` (count BEFORE cap, sort `(not is_current, p_value)`, cap `FINDINGS_NOT_CLEAR_CAP = 10`), drop low, then eval enrichment on survivors only (Pitfall 8). Replace `WEAKNESS_CAP_PER_COLOR`/`STRENGTH_CAP_PER_COLOR` (also imported by `tests/services/test_opening_insights_service.py:30-31`).

---

### `OpeningColorSwitch.tsx` (new)

**Analog:** `frontend/src/components/stats/TcSwitch.tsx:31-70`
```tsx
const handleClick = (tc: TimeControlBucket): void => {
  if (tc === selected) return;
  onSelect(tc);
  trackFeature('option-change', { target: trackTarget, value: tc });
};
return (
  <div role="group" aria-label="Time control" className="inline-flex gap-1" data-testid={`tc-switch-${idPrefix}`}>
    {tcs.map((tc) => {
      const isSelected = tc === selected;
      return (
        <Button key={tc} type="button" variant={isSelected ? 'default' : 'brand-outline'}
          aria-pressed={isSelected} className="min-h-11 gap-1 px-2 sm:min-h-0 sm:gap-1.5 sm:px-2.5"
          onClick={() => handleClick(tc)} data-testid={`tc-switch-${idPrefix}-${tc}`}>
```
Target `{ target: 'opening-stats-color'; value: 'white' | 'black' }` in `OptionChangeProps`. Host in `StickyTcBar`; on mobile place it in the existing sticky Filters row (`Openings.tsx:774-788`), not a second `top-0` row.

### `VerdictBar.tsx` (new; repertoire Score/Eval cells, finding cards, expanded row, AND Moves/Games per D-17)

**Analog:** `components/library/stats/GapBar.tsx:77-152`. Copy the track markup:
```tsx
<div className={cn('relative h-2.5 rounded-full', classes.track)}
  style={{ backgroundColor: PERCENTILE_TRACK }} role="img" aria-label={ariaLabel}
  data-testid={`${testId}-track`}>
  {band && (<div className="absolute inset-y-0 rounded-sm"
     style={{ left: `${band.leftPct}%`, width: `${band.widthPct}%`, backgroundColor: PERCENTILE_TYPICAL_BAND }}
     data-testid={`${testId}-band`} />)}
  <div className="absolute -inset-y-[3px] w-px"
     style={{ left: `${GAP_CENTRE}%`, backgroundColor: PERCENTILE_MEDIAN_TICK }} data-testid={`${testId}-zero`} />
  <div className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background"
     style={{ left: `${cellPosition(cell)}%`, backgroundColor: color }} data-testid={`${testId}-dot`} />
</div>
```
Differences: higher is better; centre = 50% (score) or colour baseline (eval) with a faint absolute 0 tick for eval; wording is the value ("54%", "+0.41" without "pawns"), not "fewer/more flaws". Value text coloured only when the verdict is hi/lo (GapBar's `colored` rule).

### `lib/openingVerdict.ts` (new, pure + unit test)

**Analog:** `lib/gapBar.ts`. Reuse `gapPosition(delta, zoneLo, zoneHi)` (:73-92, positive right), `bandRange` (:143-149) and `gapVerdictColor` (:176-180, `better→ZONE_SUCCESS`, `worse→ZONE_DANGER`, else `GAUGE_NEUTRAL`). Do NOT reuse `gapVerdict` (:95-99, "lower is better"). Verdict: neutral when `n < REPERTOIRE_MIN_GAMES_FOR_VERDICT (20)` or `|v| <= band` or confidence !== 'high'. Bands: `SCORE_BULLET_NEUTRAL_MAX = 0.05` (`lib/scoreBulletConfig.ts:15-16`), `EVAL_NEUTRAL_MAX_PAWNS = 0.30` (`lib/openingStatsZones.ts:28`). Fade `UNRELIABLE_OPACITY` (`theme.ts:358`).

### `VerdictPopover.tsx` (new)

**Analog:** `components/library/stats/GapPopover.tsx:80-125`
```tsx
<MetricInfoPopover testId={props.testId} ariaLabel={`About ${props.label}`}>
  ...
  <hr className="border-background/25" />
  <p className="italic text-background/60" data-testid={`${testId}-footer`}>
    {footerText(cell, noun)}   // "99% CI ... · p = ... · vs 50% / vs baseline · n games"
  </p>
```
Footer builder mirrors GapPopover `footerText` (:~70-82, `formatPValue`, `FOOTER_SEPARATOR`). testIds like `repertoire-row-{index}-score-info`, never SAN/name/FEN (Umami).

### `RepertoireTable.tsx` (new)

**Analog:** `components/endgames/stats/TypeTable.tsx` `RangeCell` (:110-160)
```tsx
<td className="max-md:min-w-0 md:text-right md:align-middle">
  <span className="block text-sm text-muted-foreground md:hidden" data-testid={`${testId}-caption`}>{caption}</span>
  <span className="flex flex-col gap-1 md:items-end">
    <span className="font-semibold tabular-nums" style={valueColor ? { color: valueColor } : undefined}
      data-testid={`${testId}-value`}>{value === null ? NO_VALUE : format(value)}</span>
    <span className="relative block h-2 w-full rounded-sm md:w-24"
      style={{ backgroundColor: PERCENTILE_TRACK }} aria-hidden="true">
```
Results column: `MiniWDLBar` (same file). Opening cell: `LazyMiniBoard` 44px, `opening_name` (never `label`/ECO), move line. Games cell: `formatRelativeDate`. Keys by `full_hash`/bookmark id + index. Eval cell keeps `useReadiness().tier2` / `EvalCpuPlaceholder`. Sticky `thead th` under the switch; no `overflow-hidden` ancestors (Pitfall 6). "Played before (n)" collapsed group (`panel-open` target, reuse `opening-stats-more`). Row expand: `panel-open` `opening-row-expand`.

### `PositionResultsPanel.tsx` (D-17)

Current eval display (:229-243) to keep byte-identical for `endgame-entry`:
```tsx
<MiniBulletChart value={stats.avg_eval_pawns as number}
  ciLow={stats.eval_ci_low_pawns ?? undefined} ciHigh={stats.eval_ci_high_pawns ?? undefined}
  tickPawns={isEndgameEntryEval ? undefined : resolvedEvalBaselinePawns}
  neutralMin={EVAL_NEUTRAL_MIN_PAWNS} neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
  domain={EVAL_BULLET_DOMAIN_PAWNS} barColor="neutral" ariaLabel={evalAriaLabel} />
```
Branch: `evalContext === 'opening-end'` renders `VerdictBar` (eval mode, baseline centre, ±0.30, 99% from `eval_confidence === 'high'`) + `VerdictPopover` with stats footer (uses new `eval_ci99_*` on `WDLStats`); else the block above unchanged. Watch `Endgames.*.test.tsx` for diffs (Pitfall 1). Knip may then flag `EVAL_BULLET_DOMAIN_PAWNS`/`evalZoneColor` only if endgame stops using them (it does not).

### `ScoreChart.tsx` rewrite

**Analog:** `components/charts/EndgameScoreOverTimeChart.tsx:121-124, 170-291`: `ComposedChart`, `<Bar yAxisId="bars" fill={VOLUME_BAR_COLOR} />`, hidden right axis `domain={[0, barMax * 5]}`, `inactivityGapReferenceLines({ dates, yAxisId: 'value' })` (:248). New props `{ series: BookmarkTimeSeries; showVolume?: boolean }`; delete legend/hide toggles/multi-bookmark header.

### Finding cards / Not clear yet

Copy from `components/insights/OpeningFindingCard.tsx` and `OpeningInsightsBlock.tsx` before deleting them: `isLoading`/`isError`+retry branches (:95-103), grid `grid-cols-1 lg:grid-cols-2` (:254), "more" emitter `trackFeature('panel-open', { target: 'opening-insights-more' })` (:271, reuse for phone "Show more", D-08). Helpers kept: `formatCandidateMove`, `sanToSquares`, `handleOpenFinding`/`handleOpenFindingGames` (`useOpeningsHandlers.ts:194-225`). Card cap 2 on phone (`INITIAL_VISIBLE_PHONE = 2`); new target `opening-findings-unclear`.

### `Openings.tsx` redirect (D-15)
```tsx
const needsLegacyRedirect = location.pathname.endsWith('/statistics')
  || location.pathname.endsWith('/compare')
  || location.pathname.endsWith('/insights');
```
Remove triggers `tab-insights`/`tab-insights-mobile`, `TabsContent value="insights"`, `insightsTabEl`, `Lightbulb` import, `activeTab === 'insights'` in the mobile Filters row (:774) and `openingsBoardLayout.ts:17`.

### D-16 toggle removal
Remove `bookmark-chart-enabled-<id>` localStorage helpers (`Openings.tsx:7-9`, `useOpeningsChartData.ts:25-28`), `chartBookmarks` filtering (:121-124), the toggle button in `PositionBookmarkCard.tsx:~193`, and the `toggle` target `'bookmark-chart'` (`analytics.ts:352`) once no emitter remains (knip). Optionally clear stale keys once on load.

## Shared Patterns

- **Dev clock:** `NowUtc` alias, `app/routers/train.py:65`. Apply to stats + insights routers.
- **Filters:** `apply_game_filters()` `app/repositories/query_utils.py:169` (takes `color`). Cutoff query only.
- **Sequential awaits on one AsyncSession**, no gather (stats_service test enforces).
- **Score stats:** `compute_confidence_bucket` + `wilson_bounds(z=VERDICT_CI_Z_99)` (`app/services/score_confidence.py:69,82,354`) for rows and bookmark series.
- **Verdict visuals:** theme `PERCENTILE_TRACK/TYPICAL_BAND/MEDIAN_TICK` (`lib/theme.ts:313-315`), `gapVerdictColor`, popover footer `italic text-background/60` after `hr`.
- **Umami:** `trackFeature` only on user clicks that change state (TcSwitch `if (tc === selected) return`); register targets in `lib/analytics.ts`; never rename existing targets.
- **Query error branches:** every `useQuery` consumer renders "Failed to load ..." on `isError`.
- **Cache invalidation:** bookmark create/delete invalidate `['mostPlayedOpenings']` in `usePositionBookmarks.ts:12-52`.
- **Verify:** `npm run build` (tsc) + `npm run knip` in every frontend plan (Pitfalls 9, 10).

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| Bookmark-twin drop in `stats_service.py` | service step | no cross-endpoint dedupe exists; use replay pattern from `position_bookmark_repository.py:277-321` |
| Game-set fingerprint (`sum(distinct id)`) | repository | new technique; research B4 evidence |
| `useOpeningRowTimeSeries` lazy per-row series for most-played rows | hook | request keyed by `bookmark_id`; pass `bookmark_id: 0` + `target_hash` per research B6 |

## Metadata

**Analog search scope:** `app/services`, `app/routers`, `app/repositories`, `frontend/src/components/{library,endgames}/stats`, `components/stats`, `components/charts`, `lib/gapBar.ts`
**Files scanned:** ~15 directly, rest from RESEARCH.md verified references
**Pattern extraction date:** 2026-10-17
