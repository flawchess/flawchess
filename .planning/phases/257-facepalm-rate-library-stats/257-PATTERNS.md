# Phase 257: Facepalm Rate in the Library Stats - Pattern Map

**Mapped:** 2026-11-20
**Files analyzed:** 27 (5 backend app, 5 backend tests, 17 frontend)
**Analogs found:** 27 / 27 (every new file has an in-repo analog; RESEARCH.md Patterns 1-6 already verified line refs)

All analog paths below are git-tracked source (checked with `git ls-files`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/blunder_check_rules.py` (+`FACEPALM_STATS_MIN`) | config | constant | `FACEPALM_SCORE_MIN` same file :55-60 | exact |
| `app/services/facepalm_score.py` (+type twin) | utility | transform (Python + SQL twin) | `facepalm_score` :405 / `facepalm_score_sql` :560 / `facepalm_expr` :589 | exact |
| `app/schemas/library.py` (type fields, share fields, `FacepalmBullet`, `facepalm_bullets`) | model | request-response | `FlawBullet` :327, `TempoPhaseCell` :375, `FlawTrendPoint` :281 | exact |
| `app/repositories/library_repository.py` `query_flaws` / `fetch_page_facepalm_scores` | repository | CRUD read | itself :1192-1281, :1372-1404 | exact |
| `app/repositories/library_repository.py` `fetch_facepalm_share_counts` (new) | repository | batch aggregate | `fetch_page_facepalm_scores` :1372 + `_filtered_games_base` :1611 | role-match |
| `app/repositories/library_repository.py` `fetch_facepalm_comparison` + anchor helper (new) | repository | batch aggregate | `fetch_flaw_comparison` :1997 (anchor :2028-2067) | exact |
| `app/services/library_service.py` (`_compute_flaw_trend` share, `_build_facepalm_bullet`, wiring) | service | transform | `_compute_flaw_trend` :1126, `_paired_series` :1483, `_build_tempo_phase_cell` :1538 | exact |
| `tests/facepalm_seed.py` (`facepalm_type=` option) | test helper | seed | `facepalm_fact_columns` :88, `seed_flaw_rows` :126 | exact |
| `tests/services/test_facepalm_score.py` (type parity) | test | DB parity | `_grid` :281, `_sql_scores` :300, `test_expr_matches_python_twin_over_stored_facts` :1050 | exact |
| `tests/services/test_flaw_comparison.py` (facepalm rows) | test | DB | field-parity test :865-868 | exact |
| `tests/services/test_library_service.py`, `tests/test_library_repository.py`, `tests/services/test_eval_chart_service.py` | test | DB/unit | existing facepalm tests (RESEARCH Pattern 2 list) | exact |
| `frontend/src/types/library.ts` | model | mirror | `FlawMarker.facepalm_score` :183, `FlawListItem.facepalm_score` :297 | exact |
| `frontend/src/lib/facepalm.ts` | utility | lookup | `PRESET_RANGES` / `PRESET_LABELS` same file :56-71 | exact |
| `frontend/src/lib/theme.ts` | config | constants | `TAC_MISSED*` :265-267, `TAC_ALLOWED*` :272-274; delete `FACEPALM_CHIP*` :195-196 | exact |
| `frontend/src/lib/gapBar.ts` (`noVerdict`) | utility | transform | `effectiveVerdict` :113-122 | exact |
| `frontend/src/lib/flawComparisonMeta.ts` (`FACEPALM_GAP_META`) | config | lookup | `FLAW_GAP_META` same file | exact |
| `frontend/src/components/library/FacepalmChip.tsx` | component | render | itself (34 lines) | exact |
| `frontend/src/components/analysis/FacepalmMoveChip.tsx` | component | render | `FacepalmChip.tsx` | exact |
| `frontend/src/components/library/FacepalmExplanation.tsx`, `FacepalmBadgePopover.tsx` | component | render | themselves | exact |
| `frontend/src/components/library/EvalChart.tsx` (tooltip line :1192-1201) | component | render | tactic `missed:`/`allowed:` lines :1210-1216 | exact |
| `frontend/src/components/analysis/VariationTree.tsx` :131, `hooks/analysis/useAnalysisGemMarkers.ts` :352, `FlawCard.tsx` :359 | component/hook | prop plumbing | themselves | exact |
| `frontend/src/components/library/FacepalmShareChart.tsx` (new) | component | chart | `FlawTrendChart.tsx` (201 lines) | exact |
| `frontend/src/components/library/stats/FacepalmCard.tsx` (new) | component | render | `stats/ContextTagCards.tsx` (`ContextTagRow` + `ContextTagCard`) | exact |
| `frontend/src/components/library/stats/GapPopover.tsx` | component | render | itself (:40-53 props, :98 "Fewer is better.") | exact |
| `frontend/src/components/library/stats/LibraryStatsSections.tsx` | component | composition | `FlawTimeline` :75-81, `VsOpponentsSection` :255-275 | exact |
| `frontend/.../stats/__tests__/flawStatsFixtures.ts` + new `FacepalmShareChart.test.tsx`, `FacepalmCard.test.tsx` | test | fixtures | existing `__tests__` in same dirs | exact |

## Pattern Assignments

### `app/services/blunder_check_rules.py` (config)
Add `FACEPALM_STATS_MIN: float = 0.7` directly after `FACEPALM_SCORE_MIN: float = 0.5` (line 60), with a decision comment in the style of the block at lines 55-59 ("# 257 D-01: ..."). Pin by test: `FACEPALM_STATS_MIN == 70 / 100.0` (matches `_FACEPALM_PCT_SCALE` at `library_repository.py:90`).

### `app/services/facepalm_score.py` (utility, Python+SQL twin)
**Analog:** `facepalm_expr` lines 589-613 (column map to copy verbatim for `facepalm_type_expr`):
```python
def facepalm_expr(lam: float, model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[float]:
    return facepalm_score_sql(
        FacepalmColumns(
            played_prob=GameFlaw.maia_played_prob,
            reply_spread=GameFlaw.maia_reply_spread,
            played_material=GameFlaw.played_line_material,
            mate_ply=GameFlaw.line_mate_ply,
            best_material=GameFlaw.best_line_material,
            best_mate_ply=GameFlaw.best_line_mate_ply,
            best_prob=GameFlaw.maia_best_prob,
            pre_spread=GameFlaw.maia_pre_spread,
        ),
        lam=lam,
        model=model,
    )
```
Inputs to reuse: `material_loss` :278, `material_missed` :304 (Python), `_loss_sql` :448, `_missed_sql` :470 (SQL). Add `FacepalmType = Literal["missed_win", "allowed_loss"]`, `facepalm_type_of`, `facepalm_type`, `facepalm_type_sql`, `facepalm_type_expr` per the skeleton in RESEARCH Pattern 1 (lambda-free; do not route through `_missed_weight`).

### `app/schemas/library.py` (model)
- `FlawMarker` line 99 and `FlawListItem` line 246: add `facepalm_type: FacepalmType | None = None` beside `facepalm_score: float | None = None` (keep the "ranking, not a probability" comment style at :97).
- `FlawTrendPoint` :281-296: append `facepalm_share: float | None`, `facepalm_in_window: int`, `scored_blunders_in_window: int`; extend the docstring (note they come from `game_flaws`, not the oracle columns).
- `FacepalmBullet`: copy `FlawBullet` (:327-367) field-for-field, `tag: FacepalmMetric`, `has_zone: bool = False`. Field-parity test like `tests/services/test_flaw_comparison.py:865-868`:
```python
assert set(TempoPhaseCell.model_fields) - {"tempo", "phase"} == set(FlawBullet.model_fields) - {...}
```
- `FlawComparisonTc` :403: add `facepalm_bullets: list[FacepalmBullet]` and a docstring line like the `tempo_phase_cells` one ("always 3 ... computed also below the gate"). Do NOT touch `FlawDeltaMetric`.

### `app/repositories/library_repository.py` — existing readers
**`fetch_page_facepalm_scores`** (:1372-1404), current core:
```python
score = facepalm_expr(FACEPALM_LIBRARY_LAMBDA)
stmt = (
    select(GameFlaw.game_id, GameFlaw.ply, score)
    .join(Game, Game.id == GameFlaw.game_id)
    .where(
        GameFlaw.user_id == user_id,
        GameFlaw.game_id.in_(game_ids),
        player_only_gate(GameFlaw.ply, Game.user_color),  # owner side only
        score.isnot(None),
    )
)
result: dict[int, dict[int, float]] = {}
for game_id, ply, value in (await session.execute(stmt)).all():
    result.setdefault(game_id, {})[ply] = float(value)
```
Change: add `facepalm_type_expr().label("ftype")` (never label `t`), return `dict[int, dict[int, FacepalmChipValue]]` (NamedTuple score/type). Keep the owner gate and docstring IDOR note.
**`query_flaws`**: `facepalm_chip = facepalm_expr(...)` at :1192, added at :1281 `base_stmt.add_columns(facepalm_chip.label("facepalm_chip"))`. Add the type column on the paged statement only; in the item builder null the type when the score is None (Pitfall 1).

### `app/repositories/library_repository.py` — `fetch_facepalm_comparison` + shared anchor (new)
**Analog:** `fetch_flaw_comparison` :1997, anchor block :2028-2067 — extract into a helper (e.g. `_flaw_comparison_anchor(user_id, **filters) -> Subquery`) used by both:
```python
base_filtered_subq = _filtered_games_base(user_id, time_control=..., platform=..., rated=...,
    opponent_type=..., from_date=..., to_date=..., flaw_severity=..., opponent_gap_min=...,
    opponent_gap_max=..., color=color).subquery("filtered_fc")
anchor_subq = (
    select(
        Game.id.label("game_id"), Game.user_color, Game.time_control_bucket.label("tc"),
        case((Game.user_color == "white", func.ceil(Game.ply_count / 2.0)),
             else_=func.floor(Game.ply_count / 2.0)).label("user_moves"),
    )
    .where(Game.user_id == user_id, Game.id.in_(select(base_filtered_subq.c.id)),
           Game.id.in_(select(analyzed_game_ids_subq.c.game_id)),
           Game.ply_count.isnot(None), Game.ply_count > 0,
           Game.time_control_bucket.isnot(None))
    .subquery("anchor")
)
```
Inner scan: the fenced subquery in RESEARCH "Code Examples" (`.offset(0)` with the fence comment), six `func.count(scored.c.ply).filter(...)` columns using `is_opponent_expr(scored.c.ply, anchor.c.user_color)` and `FACEPALM_STATS_MIN`. Blunder filter: `GameFlaw.severity == _SEVERITY_INT["blunder"]` (`game_flaws_repository.py:30`).

### `fetch_facepalm_share_counts` (new) + `fetch_flaw_trend_rows` (:1530)
Same filters as `fetch_flaw_trend_rows`; user side via `player_only_gate` (as in `fetch_page_facepalm_scores`), fenced score subquery, `GROUP BY game_id` returning `{game_id: (scored, facepalm)}`. `fetch_flaw_trend_rows` adds `Game.id` to SELECT and as ORDER BY tie-breaker.

### `app/services/library_service.py` (service)
**Share in the window walk** — analog `_compute_flaw_trend` :1126-1175:
```python
for row in rows:
    moves = _user_moves_from_ply_count(row.user_color, int(row.ply_count))
    if moves <= 0:
        continue
    b_rates.append(int(row.blunders or 0) / moves * _PER_100)
    ...
    window_b = b_rates[-FLAW_TREND_WINDOW:]
    n = len(window_b)
    if n < MIN_GAMES_FOR_TIMELINE:
        continue
    monday = datetime.date.fromisocalendar(iso.year, iso.week, 1)
    point_by_week[week_key] = FlawTrendPoint(date=monday.isoformat(), ..., games_in_window=n,
        per_week_games=per_week_games[week_key])
```
Add a `share_by_game: Mapping[int, tuple[int, int]]` param, append `scored`/`facepalm` lists alongside `b_rates`, emit `facepalm_share = fp_w / scored_w if scored_w >= FACEPALM_SHARE_MIN_SCORED else None`. Thread through `_compute_flaw_trend_by_tc` :1178 and `get_flaw_stats` :1203 (inside its existing try/Sentry block). Watch nesting depth <= 4; extract a `_window_share(...)` helper if needed. New constant `FACEPALM_SHARE_MIN_SCORED = 50` next to `FLAW_TREND_WINDOW` :1110.

**Facepalm bullets** — reuse `_paired_series` :1483 unchanged; model `_build_facepalm_bullet` on `_build_tempo_phase_cell` :1538-1588 with the band branch removed (`zone_lo=zone_hi=0.0`, `has_zone=False`):
```python
if series.player_total == 0 and series.opp_total == 0:
    return TempoPhaseCell(..., delta=None, ci_low=None, ci_high=None, player_rate=None,
        opp_rate=None, p_value=None, player_events=0, opp_events=0, zone_lo=zone_lo,
        zone_hi=zone_hi, has_zone=has_zone, significant=False)
mean, p_value, ci_low, ci_high, significant = _paired_gap_test(series.deltas)
n_games = len(series.player_rates)
return TempoPhaseCell(..., delta=mean, player_rate=sum(series.player_rates) / n_games if n_games else 0.0, ...)
```
Loop shape: copy `_compute_bullets` (just after `_paired_series`) iterating a `FACEPALM_METRICS` tuple with `f"player_{tag}"` / `f"opp_{tag}"`. Wire in `get_flaw_comparison` :1610 (bucket by `_bucket_rows_by_tc`, set on each `FlawComparisonTc`, sequential awaits, no gather). `_build_eval_series` :400-402 and `_build_card` :589 follow the new value type (keep the WR-01 blunder-gate comment).

### Backend tests
- Type parity: copy `_grid` :281 / `_sql_scores` :300 / stored-facts test :1050 in `tests/services/test_facepalm_score.py`, swapping in `facepalm_type_sql`; string equality.
- Seeds: add `facepalm_type=` to `facepalm_fact_columns` (`tests/facepalm_seed.py:88`).
- Update value-shape pins listed in RESEARCH Pattern 2 (`test_eval_chart_service.py:307,320`, `test_library_repository.py:2911-2990`, `test_library_router.py:1538`).

### `frontend/src/lib/theme.ts` + `lib/facepalm.ts`
Delete `FACEPALM_CHIP` / `FACEPALM_CHIP_BG` (:195-196, knip). Reuse `TAC_MISSED`/`TAC_MISSED_BG`/`TAC_MISSED_BORDER` (:265-267) and `TAC_ALLOWED*` (:272-274); add a share-line constant. In `facepalm.ts`, export `FACEPALM_HIGH_CUTOFF` (:33, now private) and add `FACEPALM_TYPE_STYLE: Record<FacepalmType, {color,bg,border}>` + `FACEPALM_TYPE_LABEL`, in the `Record<FacepalmPreset, ...>` style of `PRESET_RANGES` :56 / `PRESET_LABELS` :64.

### `FacepalmChip.tsx` / `FacepalmMoveChip.tsx`
Current chip (full file, 34 lines) styles from the neutral constants:
```tsx
<FacepalmBadgePopover testId={`facepalm-badge-${gameId}-${ply}`} score={score}>
  <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold ..."
    style={{ color: FACEPALM_CHIP, backgroundColor: FACEPALM_CHIP_BG, borderColor: FACEPALM_CHIP }}>
    <TreePalm className="h-3 w-3" aria-hidden="true" />
    <span>Facepalm</span>
    <span className="tabular-nums">{toFacepalmPct(score)}%</span>
```
Add required `type: FacepalmType`, read `FACEPALM_TYPE_STYLE[type]`, pass `type` to `FacepalmBadgePopover` -> `FacepalmExplanation` (new type line, aria-label includes type). Border choice mirrors `TacticMotifChip.tsx:196-205`.

### `gapBar.ts` (`noVerdict`)
`effectiveVerdict` :113-122 today colours zoneless significant cells:
```ts
if (!cell.hasZone && cell.delta !== null) {
  if (!cell.significant) return null;
  return cell.delta < 0 ? 'better' : 'worse';
}
```
Add `noVerdict?: boolean` to `GapCell` (:55 area) and an early `if (cell.noVerdict) return null;`. Set it where facepalm bullets become cells (`flawBulletToGapCell` in `flawComparisonMeta.ts`).

### `GapPopover.tsx`
Props :40-53 already have an override precedent (`zonelessSignificantCopy`). Add analogous optional props (e.g. `omitFewerIsBetter`, `rangeNote`) to change line :98:
```tsx
<strong>{label}:</strong> {definition.replace(/\.$/, '')}. Fewer is better.
```

### `stats/FacepalmCard.tsx` (new)
**Analog:** `ContextTagCards.tsx` `ContextTagRow` + `ContextTagCard`:
```tsx
<GapRow label={meta.label} hint={meta.hint} cell={cell} testId={`context-row-${segment}`}
  popover={cell.delta === null ? undefined : (
    <GapPopover testId={`gap-popover-${segment}-tc-${tcStats.tc}`} label={meta.label}
      definition={meta.definition} unit="per 100 moves" noun={meta.noun}
      basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)} cell={cell} />)} />
...
<Card data-testid={testId}>
  <CardHeader>{card.title}<small className="text-sm font-normal text-muted-foreground">{...}</small></CardHeader>
  <CardBody className="space-y-4">...</CardBody>
</Card>
```
Omit the `GAP_AXIS_LABELS` caption (D-16). Mount in the `ContextTagCards` grid after `CONTEXT_TAG_CARDS.slice(CARDS_PER_ROW)` (e.g. a `trailing?: ReactNode` prop mirroring `afterFirstRow`), driven from `VsOpponentsSection` (`LibraryStatsSections.tsx:255-275`).

### `FacepalmShareChart.tsx` (new)
**Analog:** `FlawTrendChart.tsx` — imports :1-15 (`ComposedChart`, `Bar`, `Line`, `ChartContainer`, `ChartTooltipBox`, `inactivityGapReferenceLines`, `VOLUME_BAR_COLOR`, `createDateTickFormatter`), testids `flaw-trend-chart` :78 / `flaw-trend-composed-chart` :93 / `flaw-trend-volume-bars` :146, hidden bars axis `<YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />` :107, `inactivityGapReferenceLines({ dates: allDates, yAxisId: 'rate' })` :139, caption `last {windowSize} games · rolling window` :167. Drop the legend/toggle state (single series, no trackFeature toggle). Mount under `<FlawTrendChart .../>` in `FlawTimeline` (`LibraryStatsSections.tsx:75-81`) reusing its loading/error branches.

## Shared Patterns

- **Score evaluated once per row:** fenced subquery `.offset(0)` (RESEARCH Code Examples); bind `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` once per statement. Applies to both new repository functions.
- **User scoping / D-06:** `GameFlaw.user_id == user_id` + `Game.user_id == user_id`; `player_only_gate(GameFlaw.ply, Game.user_color)` for owner-only readers (`library_repository.py:1397`). Don't touch drill/filter gates.
- **Filtering:** only via `_filtered_games_base` (:1611) / the extracted anchor.
- **Paired normalisation:** `_paired_series` (library_service.py:1483) is the single denominator owner.
- **Null type with null score:** in every builder (`facepalm_type=ftype if score is not None else None`).
- **Sentry:** new calls go inside the existing try blocks of `get_flaw_stats` / `get_flaw_comparison`.
- **Frontend:** colours only from `theme.ts`; every interactive element `data-testid`; popover testids `gap-popover-{segment}-tc-{tc}` auto-tracked; update `stats/__tests__/flawStatsFixtures.ts` for new required fields (tsc -b compiles it).

## No Analog Found

None. The only design without a direct precedent is the `noVerdict` neutral-cell switch, which is a small extension of `effectiveVerdict`.

## Metadata

**Analog search scope:** `app/services`, `app/repositories`, `app/schemas`, `tests/`, `frontend/src/{lib,components/library,components/analysis}`
**Files scanned:** ~15 (targeted reads; line refs from RESEARCH.md re-verified by grep)
**Pattern extraction date:** 2026-11-20
