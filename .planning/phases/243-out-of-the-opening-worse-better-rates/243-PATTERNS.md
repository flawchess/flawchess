# Phase 243: Out of the Opening Worse/Better Rates - Pattern Map

**Mapped:** 2026-10-31
**Files analyzed:** 22 (new + modified)
**Analogs found:** 21 / 22

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/opening_insights_constants.py` (mod) | config | n/a | same file (`OPENING_INSIGHTS_CI_Z_95`, `EVAL_BASELINE_PAWNS_*` at :64, :85-86) | exact |
| `app/services/canonical_slice_sql.py` (mod: `per_user_cte_opening_out_counts`, `per_user_cte_opening_out_rate`, `OPENING_OUT_MIN_GAMES_PER_COLOR`) | utility (SQL builder) | batch/transform | `per_user_cte_parity_rate_tc` (:931-1007) | exact |
| `app/services/global_percentile_cdf.py` (mod: `CdfMetricId`) | config/type | n/a | same Literal (:83-97) | exact |
| `app/models/user_benchmark_percentile.py` (mod: `color` PK col, metric type) | model | CRUD | same file (:60-145) | exact |
| `app/models/benchmark_cohort_cdf.py` (mod if ENUM→TEXT folded) | model | CRUD | `user_benchmark_percentile.py` metric column | exact |
| `alembic/versions/<date>_<rev>_opening_out_rates_metric_and_color.py` (new) | migration | n/a | `20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py` | exact (ENUM path) / role-match (TEXT+CHECK path) |
| `app/repositories/user_benchmark_percentiles_repository.py` (mod) | repository | CRUD | same file `upsert_percentile` (:58-120), `fetch_for_user` (:151) | exact |
| `app/repositories/opening_out_repository.py` (new, optional) | repository | request-response | `user_benchmark_percentiles_service._compute_metric_for_user_per_tc` (:233-262) | role-match |
| `app/services/user_benchmark_percentiles_service.py` (mod: `STAGE_B_OPENING_FAMILIES`, colour-aware cell helper) | service | batch/event-driven | same file `_compute_and_upsert_cell` (:409-457), `compute_stage_b` (:510-) | exact |
| `app/services/opening_out_stats_service.py` (new) | service | request-response | `app/services/endgame_ranked_service.py` (`RankedInputs`, `fetch_ranked_inputs`, `_fetch_rate_cohort_medians`, `_rank_status`, `_rate_significant`) | exact |
| `app/schemas/openings.py` or `app/schemas/opening_out.py` (new models) | schema | request-response | `app/schemas/endgames.py::RankedMetricOut` (:429-458), `RankStatus` (:426) | exact |
| `app/routers/openings.py` (mod: `GET /out-of-opening-stats`) | route | request-response | `app/routers/endgames.py::get_endgame_ranked_stats` (:30-51) | exact |
| `scripts/gen_global_percentile_cdf.py` (mod: colour row, tie-break, `--metrics`, merge) | script | batch | same file (:245-, :307-354, :363-367, :440-470, :807-843) | exact |
| `app/data/cohort_cdf.tsv` (regen, merged) | data | file-I/O | `_write_seed_tsv` + `tests/scripts/test_cohort_cdf_seed_artifact.py::_load_cells_from_tsv` (:58-) | exact |
| `tests/scripts/fixtures/global_percentile_cdf/opening_{worse,better}_rate__{tc}.sql` (8 new) | test fixture | n/a | existing 44 golden fixtures in same dir | exact |
| `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` (mod) / new opening parity DB test | test | n/a | same file (:101-150) + `tests/services/test_endgame_ranked_parity.py` (:456) | exact |
| `tests/integration/test_alembic_migrations.py` (mod `_PK_COLUMNS`, columns) | test | n/a | same file (:37-44, :83) | exact |
| `frontend/src/types/openingOut.ts` (new) | type | n/a | `frontend/src/types/endgames.ts` (`RankStatus`, `RankedMetricOut`) | role-match |
| `frontend/src/api/client.ts` (mod) + `frontend/src/hooks/useOutOfOpeningStats.ts` (new) | hook | request-response | `endgameApi.getRankedStats` (client.ts:270-272), `useEndgameRankedStats` (useEndgames.ts:48-62) | exact |
| `frontend/src/components/openings/stats/OutOfOpeningSection.tsx` (+ Row) (new) | component | request-response | `components/endgames/stats/RankedMetricRow.tsx` | exact (do not reuse as-is) |
| `frontend/src/components/openings/stats/OutOfOpeningPopover.tsx` (new) | component | n/a | `components/endgames/stats/RankedMetricPopover.tsx` | exact (do not reuse as-is) |
| `frontend/src/pages/openings/StatsTab.tsx` (mod) + `App.tsx` / `pages/Import.tsx` invalidation (mod) | page | n/a | same file (:70-90); App.tsx:1028, Import.tsx:208,405 | exact |
| per-eval-source report-only check | script/test | batch | none | no analog |

---

## Pattern Assignments

### `app/services/canonical_slice_sql.py` (SQL builder, batch)

**Analog:** `per_user_cte_parity_rate_tc` (lines 931-1007). Copy its signature, `_ = source` line, use of `_recent_capped_per_tc_cte`, the sub-800 filter, and the colour-sign CASE idiom.

Signature + source parity (lines 931-950):
```python
def per_user_cte_parity_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    ...
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
```

Colour-sign + eval classification idiom (lines 961-978), adapt to baseline-centred cp and `±OPENING_OUT_THRESHOLD_CP`:
```sql
      WHEN s.entry_eval_mate IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion' ELSE 'recovery' END
      WHEN s.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100 ...
```
Sub-800 + join-games for termination/result (lines 984-987):
```sql
  FROM spans s
  JOIN games g ON g.id = s.game_id
  WHERE (...) AND {ueag} >= {_SUB_800_FLOOR}
```
Final CTE shape (lines 997-1006): `per_user_values(user_id, metric_value, n_games)`; the new builder adds `user_color` and floors via `WHERE n_games >= {OPENING_OUT_MIN_GAMES_PER_COLOR}` (constant interpolated, defined next to `MEDIAN_ANCHOR_MIN_GAMES` at :137).

**Do not edit** `_recent_capped_per_tc_cte` (:270-302); it projects only `g.id, g.user_id, g.user_color, g.result, g.played_at` and 44 golden fixtures pin its text. Join `games g ON g.id = rc.id` for `termination`. Add `gp.user_id = rc.user_id` in the position join (PK index scan, RESEARCH Pattern 1). Must not introduce a CTE named `recent_capped_no_daily` (anchor-rename hack in the CDF script).

---

### `app/services/user_benchmark_percentiles_service.py` (service, batch)

**Analog:** same file.

Separate family tuple (copy shape of lines 136-147, but NEW tuple, never extend `STAGE_B_METRIC_FAMILIES` — pinned by `test_endgame_ranked_parity.py:78,455,562` and `test_user_benchmark_percentiles_service.py:85`):
```python
STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = ( "achievable_score_gap", ..., "recovery_rate", )
```

Per-user SQL composition (lines 251-262); the new colour-aware fetch drops `LIMIT 1` and returns `dict[Color, tuple[float, int]]`:
```python
    su_cte = selected_users_cte(source="single_user")
    pooled_cte = _per_user_cte_for_family_and_tc(family, tc)
    sql = (
        f"WITH {su_cte},\n{pooled_cte}\n"
        f"SELECT metric_value::float AS value, n_games::int AS n_games\n"
        f"FROM per_user_values\n"
        f"LIMIT 1"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
```

Per-cell compute + upsert + Sentry isolation (lines 409-457) — copy into a colour-aware sibling:
```python
    try:
        result = await _compute_metric_for_user_per_tc(session, user_id, metric, tc)
        if result is None:
            return
        value, n_games = result
        table = cohort.get((metric, round_anchor_to_grid(anchor.anchor_rating), tc))
        percentile: float | None = interpolate_cohort_percentile(value, table)
        await upsert_percentile(session, user_id=user_id, metric=metric, time_control_bucket=tc,
            value=value, n_games=n_games, percentile=percentile, cdf_snapshot=datetime.now(UTC).date())
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": stage_label, "metric": metric, "tc": tc})
        sentry_sdk.capture_exception(exc)
```

Loop placement in `compute_stage_b` (lines ~560-575): add a second `itertools.product(STAGE_B_OPENING_FAMILIES, anchors.items())` loop after the endgame loop, before `await session.commit()`, reusing `cohort_b` (`load_cohort_cells` already returns all metrics). Keep depth <= 4 (the product idiom exists for this reason). Update the docstring "Stage A / Stage B race" note to the 4-column PK.

---

### `app/repositories/user_benchmark_percentiles_repository.py` (repository, CRUD)

**Analog:** same file `upsert_percentile` (lines 58-120). Add `color: PercentileColor = "all"` kwarg; widen `index_elements`:
```python
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "metric", "time_control_bucket"],
        set_={ "value": stmt.excluded.value, "n_games": stmt.excluded.n_games,
               "percentile": stmt.excluded.percentile, "cdf_snapshot": stmt.excluded.cdf_snapshot,
               "computed_at": func.now() },
    )
```
`fetch_for_user` (line 151) must add `WHERE color = 'all'` so Endgames' `RankedInputs.percentile_rows: dict[CdfMetricId, dict[TC, PercentileRow]]` is unchanged; add a new `fetch_opening_out_rows(session, *, user_id)` keyed by `(metric, tc, color)` returning the same frozen `PercentileRow` dataclass (lines 37-55). Keep the keyword-only `user_id` (V4 disclosure note, module docstring lines 17-19).

---

### `app/models/user_benchmark_percentile.py` + migration

**Analog model:** lines 131-145:
```python
    metric: Mapped[CdfMetricId] = mapped_column(benchmark_metric_enum, primary_key=True)
    time_control_bucket: Mapped[TimeControlBucket] = mapped_column(
        time_control_bucket_enum, primary_key=True, nullable=False)
```
Add `color: Mapped[Literal["all","white","black"]] = mapped_column(Text, primary_key=True, nullable=False, server_default="all")` + `CheckConstraint`. If ENUM→TEXT is folded in, `metric` becomes `Text` with `CheckConstraint` generated from `typing.get_args(CdfMetricId)`; `benchmark_metric_enum` (:60-88) is deleted.

**Analog migration (ENUM fallback path):** `alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py`:
```python
_NEW_VALUES: tuple[str, ...] = ("conversion_rate", "parity_rate", "recovery_rate")

def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")
```
Pitfalls: filename must NOT contain `user_benchmark_percentile` (test globs, `test_alembic_migrations.py:37-44`); never use a newly added ENUM label in the same transaction. Update `_PK_COLUMNS` (`test_alembic_migrations.py:83`) to include `color`.

---

### `app/services/opening_out_stats_service.py` (service, request-response)

**Analog:** `app/services/endgame_ranked_service.py`.

Inputs dataclass pattern (lines 128-149): a frozen-ish dataclass of everything the pure builder needs, fetched once. Fetch function pattern (lines 188-243): sequential awaits, one per TC over `RANKED_TC_ORDER`, never `asyncio.gather`:
```python
    for tc in RANKED_TC_ORDER:
        games_by_tc[tc] = await fetch_ranked_games(session, user_id=user_id, tc=tc)
    ...
    anchors = await fetch_anchors_for_user(session, user_id=user_id)
    cohort_medians = await _fetch_rate_cohort_medians(session, anchors)
```
Cohort p50 lookup (lines 246-258) — copy for opening metrics and also pull p25/p75 for the footer band:
```python
    rounded = {tc: round_anchor_to_grid(a.anchor_rating) for tc, a in anchors.items()}
    cells = await load_cohort_cells(session, sorted(set(rounded.values())), list(rounded))
    ...
            table = cells.get((metric, anchor_elo, tc))
            if table is not None:
                medians[(metric, tc)] = table.breakpoints[_MEDIAN_BREAKPOINT_INDEX]
```
Rank status (lines 876-906): extract `_rank_status` to a public helper (e.g. `rank_status`) and call it; do not copy. Order: anchor floor → pending → own floor → ranked → unranked.

Gate: analog `_rate_significant` (lines 780-789) hardcodes 99%:
```python
    lo, hi = wilson_bounds(successes / games, games, z=VERDICT_CI_Z_99)
    return ci_excludes(_band_mid(band), lo, hi)
```
New local helper calls `wilson_bounds(k / n, n, z=OPENING_INSIGHTS_CI_Z_95)` and `ci_excludes(weighted_p50, lo, hi)` plus the direction guard. Do not edit the Endgames helpers. Orient display percentile (worse → 100 − raw) once, server-side, in a distinctly named field.

---

### `app/schemas/...` response models

**Analog:** `app/schemas/endgames.py` `RankStatus = Literal["ranked","below_floor","unranked","pending"]` (:426, import it, do not redefine) and `RankedMetricOut` (:429-458) field set (`value`, `n`, `floor_n`, `floor_required`, `percentile`, `status`, `ci_low`, `ci_high`, `significant`). New models: per-TC breakdown item, per-rate collapsed out, per-colour out, `OutOfOpeningStatsResponse{white, black}`. `Literal` for colour and rate.

---

### `app/routers/openings.py` (route)

**Analog:** `app/routers/endgames.py` lines 30-51:
```python
@router.get("/ranked-stats", response_model=EndgameRankedStatsResponse)
async def get_endgame_ranked_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> EndgameRankedStatsResponse:
    """... Takes NO filter parameters ...
    Dev-clock exception: the ranked window uses SQL ``NOW()`` rather than the
    ``dev_now_utc`` dependency (CLAUDE.md). ..."""
    return await endgame_ranked_service.get_ranked_stats(session, user_id=user.id)
```
Openings router already has `router = APIRouter(prefix="/openings", tags=["openings"])` (line 26); add `@router.get("/out-of-opening-stats", ...)` with relative path. Copy the dev-clock exception docstring verbatim in spirit. Update module docstring line 1 listing endpoints.

---

### `scripts/gen_global_percentile_cdf.py` (script, batch)

**Analog:** same file.
- Dispatcher `_per_user_cte_for_metric_and_tc` (:245-304): add two arms calling the new builder with `source="benchmark", snapshot_date=snapshot_date`; mirror in the service dispatcher (`user_benchmark_percentiles_service.py:185-230`).
- Query (:307-354): project `puv.user_color` in the outer SELECT for opening metrics; anchor-rename hack:
```python
    anchor_block_renamed = (
        anchor_block.replace("recent_capped AS (", "recent_capped_anchor AS (")
        .replace("recent_capped_no_daily", "recent_capped_anchor_no_daily")
        .replace("FROM recent_capped rc", "FROM recent_capped_anchor rc")
    )
```
- Row type `_PerUserRow(NamedTuple)` (:363-367): add `user_color` (or sibling type).
- Tie-break (:461): `sorted(in_window, key=lambda r: (abs(r.anchor_rating - anchor), r.user_id))` → add `r.user_color` (or rank distinct users, RESEARCH Pattern 3).
- CLI (:807-843): copy `parser.add_argument` style for `--metrics` (choices from `IN_SCOPE_METRICS`); merge mode promotes `_load_cells_from_tsv` from `tests/scripts/test_cohort_cdf_seed_artifact.py:58-` into the script; separate report path. Existing metric SQL must stay byte-identical.

---

### Tests

- Structural parity: `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` tests at :101 (`test_pooled_per_tc_cte_body_is_identical_across_sources`), :127, :140 — add the opening builders to its parametrised family list (`_PER_TC_METRIC_FAMILIES`, ~line 58).
- DB parity (CDF path vs user path vs on-read): `tests/services/test_endgame_ranked_parity.py:456` `test_on_read_value_matches_canonical_cte` with its `ranked_parity_user` fixture; seed edge cases (early resignation/timeout/checkmate, abandoned, draw, mate at MG entry, NULL eval MG entry, sub-800). Every non-guest Game insert needs finally-cleanup (memory: eval lottery isolation).
- Golden SQL fixtures: copy naming `{metric}__{tc}.sql` in `tests/scripts/fixtures/global_percentile_cdf/`.

---

### Frontend: `useOutOfOpeningStats.ts` + `client.ts`

**Analog:** `frontend/src/hooks/useEndgames.ts:48-62`:
```ts
export function useEndgameRankedStats(options: { enabled?: boolean } = {}) {
  const { enabled = true } = options;
  return useQuery({
    queryKey: ['endgameOverview', 'ranked'],
    queryFn: () => endgameApi.getRankedStats(),
    staleTime: ENDGAME_STALE_TIME_MS,
    refetchOnWindowFocus: false,
    enabled,
  });
}
```
`client.ts:270-272`: `getRankedStats: () => apiClient.get<EndgameRankedStatsResponse>('/endgames/ranked-stats').then(r => r.data)` → add an openings-api method for `/openings/out-of-opening-stats`. New query key under its own prefix; add `invalidateQueries` next to `App.tsx:1028` and `pages/Import.tsx:208,405`.

### Frontend: `OutOfOpeningSection.tsx` / row

**Analog:** `components/endgames/stats/RankedMetricRow.tsx` (whole file, 50 lines). Copy layout: label + popover trigger left, bold tabular value right, `PercentileBar` below with `status/percentile/floorN/floorRequired/significant/testId`; hide value when `status === 'pending'`. Do not import `RankedMetricRow` (bound to `RankedMetricOut`/`METRIC_LABELS`). Better row = lesser styling (e.g. `font-medium`/muted label). Handle `isError` with `LoadError` (`StatsTab.tsx:3`, used at ~line 108: `<LoadError resource="most-played openings" .../>`).

### Frontend: `OutOfOpeningPopover.tsx`

**Analog:** `components/endgames/stats/RankedMetricPopover.tsx`. Copy: `FOOTER_SEPARATOR`, `footerText` (change "99% CI" to "95% CI", add pooled "k of n" and peer band), `RankedDisclosures` structure (`<p className="font-semibold">` percentile statement + `COPY_CHANCE` when out of range and not significant, `<ul className="list-disc space-y-0.5 pl-4">` disclosures), body (`space-y-1.5`, `RankStatusLine` with `className="text-xs text-background"` for non-ranked, `<hr className="border-background/25" />`, `<p className="italic text-background/60" data-testid={`${testId}-footer`}>`), shell via `MetricInfoPopover testId ariaLabel`. Add: per-TC list (D-10), filter-independence line, "not FlawChess users" line, rating-dependence line. Wording: "Fewer worse games than N% of peers" / "More better games than N% of peers"; copy says "eval", never "pawns". Testid without colour segment, e.g. `out-of-opening-worse-rate`.

### Frontend: `StatsTab.tsx` host

**Analog:** same file lines 70-90. Insert the section as the FIRST child of `<div className="flex flex-col gap-6">` with heading `<h2 className={REPERTOIRE_HEADING_CLASS}>Out of the opening</h2>` (outside the card, like Bookmarked Openings) so the `StickyTcBar` overlays it; card uses `charcoal-texture rounded-md p-4`. Update the comment at :72-75 that names "Bookmarked Openings" as the first heading. Pass `color` from props.

---

## Shared Patterns

### Sentry in background compute
**Source:** `user_benchmark_percentiles_service.py:409-457` and top-level `compute_stage_b` except block. Re-raise `CancelledError`, `set_context("percentile_compute", {...})`, `capture_exception`; no variables in messages. Apply to Stage B opening loop and the new service fetch if it catches anything.

### Sequential DB access
**Source:** `endgame_ranked_service.fetch_ranked_inputs:188-243`. One session, awaits in sequence. Apply to new service.

### Shared SQL, `.bindparams(user_id=...)`
**Source:** `user_benchmark_percentiles_service.py:251-258`. Never f-string `user_id`; only Literal TCs and named constants are interpolated.

### Percentile display helpers
**Source:** `frontend/src/components/endgames/stats/rankedMetrics.ts` (`displayPercentile` :27, `PERCENTILE_TYPICAL_LOW/HIGH` :13-14, `COPY_CHANCE` :107, `formatOrdinal` :43). Do not add opening ids to frontend `CdfMetricId` / `METRIC_LABELS` (:53) / `METRIC_WHAT` (:71).

### Named constants
`OPENING_OUT_THRESHOLD_PAWNS` (+ cp mirror) in `opening_insights_constants.py`; `OPENING_OUT_MIN_GAMES_PER_COLOR` in `canonical_slice_sql.py`; z from `OPENING_INSIGHTS_CI_Z_95`; median index via `BREAKPOINT_PERCENTILES.index(50.0)` as in `endgame_ranked_service.py:242-243`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| per-eval-source check (lichess vs local full vs entry-lane) | script/test, report-only | batch | No existing report-only eval-source comparison; use `.planning/sketches/013-out-of-the-opening/analysis/fetch_sweep.py` semantics and RESEARCH §Validation Architecture |
| TEXT+CHECK conversion of `benchmark_metric` (if folded in) | migration | n/a | No prior ENUM→TEXT migration located; only ENUM ADD VALUE precedent |

## Metadata

**Analog search scope:** `app/services`, `app/repositories`, `app/routers`, `app/models`, `app/schemas`, `alembic/versions`, `scripts`, `tests/services`, `tests/scripts`, `frontend/src/{components,hooks,api,pages}`
**Files scanned:** ~20
**Pattern extraction date:** 2026-10-31
