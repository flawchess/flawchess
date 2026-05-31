# Phase 99: Percentile Badges for Conversion, Parity, and Recovery - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/canonical_slice_sql.py` | service | CRUD / batch | `app/services/canonical_slice_sql.py` `per_user_cte_score_gap_bucket_tc` | exact |
| `app/models/user_benchmark_percentile.py` | model | CRUD | same file (existing 8-value SAEnum) | exact |
| `alembic/versions/YYYYMMDD_extend_benchmark_metric_for_rate_percentiles.py` | migration | batch | `alembic/versions/20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py` | exact |
| `app/services/global_percentile_cdf.py` | service | batch / transform | same file (`CdfMetricId` Literal + `COHORT_PERCENTILE_CDF` sentinels) | exact |
| `scripts/gen_global_percentile_cdf.py` | utility | batch | same file (`IN_SCOPE_METRICS` + `_per_user_cte_for_metric_and_tc` dispatch) | exact |
| `app/services/user_benchmark_percentiles_service.py` | service | batch | same file (`STAGE_B_METRIC_FAMILIES` + `_per_user_cte_for_family_and_tc` dispatch) | exact |
| `scripts/backfill_user_percentiles.py` | utility | batch | same file (`_ALL_METRICS` dynamic derivation) | exact |
| `app/schemas/endgames.py` | model | request-response | same file (`PerTcBucketStats`, existing `percentile_n_games`/`percentile_value` field pair) | exact |
| `app/services/endgame_service.py` | service | request-response | same file (`_build_per_tc_bucket_stats`, `_compute_per_tc_metric_cards` lookup block) | exact |
| `frontend/src/types/endgames.ts` | model | request-response | same file (`PerTcBucketStats` interface, `percentile_n_games` field pattern) | exact |
| `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` | component | request-response | `frontend/src/components/charts/EndgameTimePressureCard.tsx` `ClockGapHeaderRow` chip placement | exact |

---

## Pattern Assignments

---

### `app/services/canonical_slice_sql.py` (service, batch) — ADD 3 new builders

**Analog:** `app/services/canonical_slice_sql.py` lines 726–836 (`per_user_cte_score_gap_bucket_tc`)

**Existing constants pattern** (lines 119–138): the new `MINIMUM_RATE_BUCKET_SPANS` constant belongs here, declared as a named module-level constant alongside existing per-metric floors.

```python
# app/services/canonical_slice_sql.py lines 119-123 (existing pattern)
SCORE_GAP_MIN_ENDGAME_N: int = 30
SCORE_GAP_MIN_NON_ENDGAME_N: int = 30
ACHIEVABLE_MIN_GAMES: int = 30
SCORE_GAP_BUCKET_MIN_SPANS: int = 30
# Phase 99: ADD after line 123
MINIMUM_RATE_BUCKET_SPANS: int = 30  # same value; same floor contract, separate named constant
```

**Builder signature pattern** (lines 726–751): the new rate builders mirror the exact function signature, docstring shape, and `_ = source` idiom.

```python
# app/services/canonical_slice_sql.py lines 726-751 (analog to copy)
def per_user_cte_score_gap_bucket_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
    bucket_label: Literal["conversion", "parity", "recovery"],
) -> str:
    """Per-TC pooled per_user_values(user_id, metric_value, n_games) for ..."""
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT
    gp.game_id, gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
```

**Critical structural diff vs analog:** The rate builders do NOT need `spans_with_next` with `lead()` (lines 764–768 of the analog). Rate is measured from game outcome, not ΔES delta. Stop after `spans`; go directly to `bucket_rows` classifying by entry eval, then compute wins/saves/score from `g.result`. The `per_user_values` CTE MUST project `(user_id, metric_value, n_games)` — the `user_id` column is mandatory per Phase 94.4 Pitfall 1 (verified: all existing builders include it, see line 829 comment).

**per_user_values projection pattern** (lines 828–836):

```python
# lines 828-836 (pattern to adapt)
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    mean_gap AS metric_value,
    span_n AS n_games
  FROM per_user_bucket
  WHERE bucket = '{bucket_label}'
)
```

**Adaptation for rate builders:** Three separate functions (not a shared `bucket_label` parameter) because the aggregation formulas differ per metric:
- `per_user_cte_conv_rate_tc`: `metric_value = conv_wins / NULLIF(conv_n, 0)`, `n_games = conv_n`, `HAVING count(*) FILTER (WHERE is_conversion) >= {MINIMUM_RATE_BUCKET_SPANS}`
- `per_user_cte_parity_rate_tc`: `metric_value = (parity_wins + 0.5 * parity_draws) / NULLIF(parity_n, 0)`, `n_games = parity_n`
- `per_user_cte_recovery_rate_tc`: `metric_value = (recov_wins + recov_draws) / NULLIF(recov_n, 0)`, `n_games = recov_n`

All three range 0–1, all `higher_is_better` — no CDF inversion needed.

---

### `app/models/user_benchmark_percentile.py` (model, CRUD) — EXTEND SAEnum

**Analog:** same file, lines 54–65 (`benchmark_metric_enum` declaration)

```python
# app/models/user_benchmark_percentile.py lines 54-65 (full analog)
benchmark_metric_enum = SAEnum(
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    name="benchmark_metric",
    create_type=False,
)
```

**Adaptation:** Append the 12 new string values inside the same `SAEnum(...)` call. Order must mirror the migration's `_NEW_VALUES` tuple exactly (Pitfall 3 — SQLAlchemy validates writes against these values). `create_type=False` stays unchanged. The docstring on lines 1–31 must be updated to reference Phase 99 and the new count (8 → 11 values, per metric family).

```python
# After adaptation (append these 12 values before name="benchmark_metric"):
    "conversion_rate",   # Phase 99 — raw rate families (TC carried by PK column)
    "parity_rate",
    "recovery_rate",
```

Note: `CdfMetricId` is imported at line 44 and used at line 112 (`metric: Mapped[CdfMetricId]`). After widening `CdfMetricId` in `global_percentile_cdf.py`, `ty check` enforces the ORM column accepts the new values — no additional change needed here beyond the SAEnum string values.

---

### `alembic/versions/YYYYMMDD_extend_benchmark_metric_for_rate_percentiles.py` (migration) — NEW FILE

**Analog:** `alembic/versions/20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py` (full file, 93 lines)

```python
# Full analog — copy this structure verbatim, adapt values
_NEW_VALUES: tuple[str, ...] = (
    "time_pressure_score_gap_bullet",   # ← replace with rate metric values
    ...
)

def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")

def downgrade() -> None:
    pass  # Postgres cannot remove ENUM values — git revert instead
```

**Adaptation:** Replace `_NEW_VALUES` with the 12 rate metric ENUM values in this exact order (mirrors `CdfMetricId` family grouping, then TC sweep):

```python
_NEW_VALUES: tuple[str, ...] = (
    "conversion_rate_bullet",
    "conversion_rate_blitz",
    "conversion_rate_rapid",
    "conversion_rate_classical",
    "parity_rate_bullet",
    "parity_rate_blitz",
    "parity_rate_rapid",
    "parity_rate_classical",
    "recovery_rate_bullet",
    "recovery_rate_blitz",
    "recovery_rate_rapid",
    "recovery_rate_classical",
)
```

Set `down_revision = "c70f5d94b243"` (the current head migration as of 2026-05-30). Generate a new revision ID and timestamp for the filename. The `upgrade()` and `downgrade()` bodies are copied verbatim — no adaptation beyond the `_NEW_VALUES` tuple and metadata fields.

---

### `app/services/global_percentile_cdf.py` (service, batch) — EXTEND `CdfMetricId`

**Analog:** same file, lines 101–110 (`CdfMetricId` Literal declaration)

```python
# app/services/global_percentile_cdf.py lines 101-110 (full analog)
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
]
```

**Adaptation:** Append 3 new values (note: 3 families, NOT 12 — TC is an outer key on the registry, not a suffix on the metric name per the State of the Art table):

```python
# Append inside the same Literal[...] block:
    "conversion_rate",   # Phase 99
    "parity_rate",
    "recovery_rate",
```

The `COHORT_PERCENTILE_CDF` registry between `# --- BEGIN GENERATED REGISTRY ---` and `# --- END GENERATED REGISTRY ---` sentinels is overwritten by `scripts/gen_global_percentile_cdf.py --target benchmark`. Do not hand-edit the registry block. Update `CdfMetricId` first, then regen.

---

### `scripts/gen_global_percentile_cdf.py` (utility, batch) — EXTEND `IN_SCOPE_METRICS` + dispatch

**Analog:** same file, lines 154–163 (`IN_SCOPE_METRICS`) and lines 258–306 (`_per_user_cte_for_metric_and_tc` dispatch)

```python
# scripts/gen_global_percentile_cdf.py lines 154-163 (full analog)
IN_SCOPE_METRICS: Final[tuple[CdfMetricId, ...]] = (
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)
```

**Adaptation for `IN_SCOPE_METRICS`:** Append `"conversion_rate"`, `"parity_rate"`, `"recovery_rate"` at the end of the tuple.

```python
# scripts/gen_global_percentile_cdf.py lines 286-306 (dispatch analog)
if metric == "score_gap_conv":
    return per_user_cte_score_gap_bucket_tc(
        tc, source="benchmark", snapshot_date=snapshot_date, bucket_label="conversion"
    )
...
if metric == "net_flag_rate":
    return per_user_cte_net_flag_rate(tc, source="benchmark", snapshot_date=snapshot_date)
raise ValueError(f"Unknown metric: {metric!r}")
```

**Adaptation for dispatch:** Add 3 new `if` arms before the `raise ValueError`:

```python
if metric == "conversion_rate":
    return per_user_cte_conv_rate_tc(tc, source="benchmark", snapshot_date=snapshot_date)
if metric == "parity_rate":
    return per_user_cte_parity_rate_tc(tc, source="benchmark", snapshot_date=snapshot_date)
if metric == "recovery_rate":
    return per_user_cte_recovery_rate_tc(tc, source="benchmark", snapshot_date=snapshot_date)
```

Also extend the `_METRIC_SECTION_LABELS` dict (around line 586) with entries for the 3 new families (used in the regen report).

---

### `app/services/user_benchmark_percentiles_service.py` (service, batch) — EXTEND `STAGE_B_METRIC_FAMILIES` + dispatch

**Analog:** same file, lines 139–147 (`STAGE_B_METRIC_FAMILIES`) and lines 155–191 (`_per_user_cte_for_family_and_tc` dispatch)

```python
# app/services/user_benchmark_percentiles_service.py lines 139-147 (full analog)
STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = (
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)
```

**Adaptation for `STAGE_B_METRIC_FAMILIES`:** Append 3 new families:

```python
    "conversion_rate",   # Phase 99
    "parity_rate",
    "recovery_rate",
```

**Dispatch analog** (lines 155–191):

```python
# lines 183-191 (last arms + raise, copy pattern)
if family == "time_pressure_score_gap":
    return per_user_cte_time_pressure_score_gap(tc, source="single_user", snapshot_date=None)
if family == "clock_gap":
    return per_user_cte_clock_gap(tc, source="single_user", snapshot_date=None)
if family == "net_flag_rate":
    return per_user_cte_net_flag_rate(tc, source="single_user", snapshot_date=None)
raise ValueError(f"Unknown CdfMetricId for per-TC dispatch: {family!r}")
```

**Adaptation:** Add 3 arms before the `raise`:

```python
if family == "conversion_rate":
    return per_user_cte_conv_rate_tc(tc, source="single_user", snapshot_date=None)
if family == "parity_rate":
    return per_user_cte_parity_rate_tc(tc, source="single_user", snapshot_date=None)
if family == "recovery_rate":
    return per_user_cte_recovery_rate_tc(tc, source="single_user", snapshot_date=None)
```

Also update the import block at the top of the file to include the 3 new builders from `canonical_slice_sql`.

---

### `scripts/backfill_user_percentiles.py` (utility, batch) — NO CHANGES NEEDED TO `_ALL_METRICS`

**Analog:** same file, lines 159–163

```python
# scripts/backfill_user_percentiles.py lines 159-163 (full analog)
_ALL_METRICS: tuple[CdfMetricId, ...] = (STAGE_A_METRIC, *STAGE_B_METRIC_FAMILIES)
```

`_ALL_METRICS` is dynamically derived from `STAGE_B_METRIC_FAMILIES`. Extending `STAGE_B_METRIC_FAMILIES` in `user_benchmark_percentiles_service.py` automatically propagates to `_ALL_METRICS` here. No direct edit is required to the backfill script.

The `--metric` argparse choices list (around line 68 in the module docstring examples) and the comment on line 159 should be updated to reflect 11 valid metric values. The `_PercentileSummary.__init__` cell dict (line 396) also derives from `_ALL_METRICS` automatically.

---

### `app/schemas/endgames.py` (model, request-response) — EXTEND `PerTcBucketStats`

**Analog:** same file, lines 822–856 (`PerTcBucketStats` Pydantic model)

```python
# app/schemas/endgames.py lines 854-856 (exact analog — the existing gap chip field pair)
percentile: float | None
percentile_n_games: int | None = None
percentile_value: float | None = None
```

**Adaptation:** Append 3 new optional fields immediately after `percentile_value` (line 856). They default `None` to preserve backward compatibility with all existing test fixtures:

```python
# Phase 99 — raw-rate percentile (SEPARATE from ΔES-gap percentile per D-01)
rate_percentile: float | None = None
rate_percentile_n_games: int | None = None
rate_percentile_value: float | None = None
```

Also update the class docstring (lines 823–842) to document the 3 new fields, following the same pattern as the existing `percentile_n_games`/`percentile_value` documentation at lines 836–841.

---

### `app/services/endgame_service.py` (service, request-response) — EXTEND `_build_per_tc_bucket_stats` + lookup block

**Analog A:** same file, lines 2657–2678 (per-TC lookup block in `_compute_per_tc_metric_cards`)

```python
# app/services/endgame_service.py lines 2657-2678 (full analog — 3-row lookup pattern)
conv_row = _effective_rows.get("score_gap_conv", {}).get(tc_bucket)
parity_row = _effective_rows.get("score_gap_parity", {}).get(tc_bucket)
recov_row = _effective_rows.get("recovery_score_gap", {}).get(tc_bucket)

conversion_stats = _build_per_tc_bucket_stats(
    acc,
    "conversion",
    acc.gaps_conv,
    conv_row,
)
parity_stats = _build_per_tc_bucket_stats(
    acc,
    "parity",
    acc.gaps_parity,
    parity_row,
)
recovery_stats = _build_per_tc_bucket_stats(
    acc,
    "recovery",
    acc.gaps_recov,
    recov_row,
)
```

**Adaptation:** Add 3 new rate lookups after line 2659. Pass `rate_percentile_row` as a new positional argument (with default `None`) to each `_build_per_tc_bucket_stats` call:

```python
# ADD after existing conv/parity/recov_row lookups
conv_rate_row   = _effective_rows.get("conversion_rate", {}).get(tc_bucket)
parity_rate_row = _effective_rows.get("parity_rate",    {}).get(tc_bucket)
recov_rate_row  = _effective_rows.get("recovery_rate",  {}).get(tc_bucket)
```

Then update each `_build_per_tc_bucket_stats` call to pass the rate row:

```python
conversion_stats = _build_per_tc_bucket_stats(acc, "conversion", acc.gaps_conv, conv_row, conv_rate_row)
```

**Analog B:** same file, lines 2478–2550 (`_build_per_tc_bucket_stats` function)

```python
# app/services/endgame_service.py lines 2478-2483 + 2547-2550 (signature + return, analog)
def _build_per_tc_bucket_stats(
    acc: "_MetricTcAccumulator",
    bucket: MaterialBucket,
    gaps: list[float],
    percentile_row: PercentileRow | None,
) -> PerTcBucketStats:
    ...
    return PerTcBucketStats(
        ...
        percentile=percentile_row.percentile if percentile_row is not None else None,
        percentile_n_games=percentile_row.n_games if percentile_row is not None else None,
        percentile_value=percentile_row.value if percentile_row is not None else None,
    )
```

**Adaptation:** Add `rate_percentile_row: PercentileRow | None = None` as a 5th parameter and wire 3 new return fields:

```python
def _build_per_tc_bucket_stats(
    acc: "_MetricTcAccumulator",
    bucket: MaterialBucket,
    gaps: list[float],
    percentile_row: PercentileRow | None,
    rate_percentile_row: PercentileRow | None = None,  # Phase 99 — raw rate percentile
) -> PerTcBucketStats:
    ...
    return PerTcBucketStats(
        ...
        percentile=percentile_row.percentile if percentile_row is not None else None,
        percentile_n_games=percentile_row.n_games if percentile_row is not None else None,
        percentile_value=percentile_row.value if percentile_row is not None else None,
        rate_percentile=rate_percentile_row.percentile if rate_percentile_row is not None else None,
        rate_percentile_n_games=rate_percentile_row.n_games if rate_percentile_row is not None else None,
        rate_percentile_value=rate_percentile_row.value if rate_percentile_row is not None else None,
    )
```

---

### `frontend/src/types/endgames.ts` (model, request-response) — EXTEND `PerTcBucketStats`

**Analog:** same file, lines 422–439 (`PerTcBucketStats` interface)

```typescript
// frontend/src/types/endgames.ts lines 433-438 (exact analog — existing gap chip fields)
percentile: number | null;       // per-TC DeltaES-gap percentile
// Chip-cohort n_games + value from the same PercentileRow as `percentile`.
// ... (comment)
percentile_n_games?: number | null;
percentile_value?: number | null;
```

**Adaptation:** Append 3 new optional fields after `percentile_value` (line 438):

```typescript
// Phase 99 — raw-rate percentile (SEPARATE from ΔES-gap `percentile` per D-01)
rate_percentile?: number | null;
rate_percentile_n_games?: number | null;
rate_percentile_value?: number | null;
```

---

### `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` (component, request-response) — ADD title-line chip to `MetricBlock`

**Analog A (chip placement):** `frontend/src/components/charts/EndgameTimePressureCard.tsx` lines 182–203 (`ClockGapHeaderRow` chip slot)

```tsx
// EndgameTimePressureCard.tsx lines 182-203 (title-line right-aligned chip — exact analog)
{/* Phase 94.4 Plan 07: Clock Gap percentile chip, right-aligned.
    `ml-auto` pushes the chip to the row's right edge. Gated on
    `!= null` to honor the backend inclusion-floor contract — a null
    percentile suppresses the chip silently. Also gated on
    `ratingAnchor !== undefined` because bullet 4 of the popover MUST
    disclose the anchor; without it we cannot honestly render the tooltip. */}
{card.clock_gap_percentile != null && ratingAnchor !== undefined && (
  <span className="ml-auto inline-flex">
    <PercentileChip
      percentile={card.clock_gap_percentile}
      flavor="clock-gap"
      tc={card.tc}
      anchorRating={ratingAnchor.anchor_rating}
      metricLabel="Clock Gap"
      testId={`time-pressure-card-${card.tc}-clock-gap-chip`}
      nGames={card.clock_gap_n_games}
      value={card.clock_gap_value}
    />
  </span>
)}
```

**Analog B (existing gap chip in same file):** `EndgameMetricsByTcCard.tsx` lines 216–234 (the ΔES-gap chip wiring inside `chipSlot` — pattern for null-gating and prop threading).

**Analog C (h4 gap — Pitfall 6):** `EndgameMetricsByTcCard.tsx` line 150 (current h4 class lacks `w-full`):

```tsx
// EndgameMetricsByTcCard.tsx line 150 (CURRENT — missing w-full)
<h4 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
```

**Adaptation — three changes to `MetricBlock`:**

1. Add `w-full` to the `h4` class at line 150 (required for `ml-auto` to push chip right):

```tsx
// CHANGE line 150 to:
<h4 className="text-base font-semibold mb-2 inline-flex items-center gap-1 w-full">
```

2. After the closing `</InfoPopover>` (line 158), add the rate chip slot inside the `h4`:

```tsx
{block.rate_percentile != null && anchorRating != null && (
  <span className="ml-auto inline-flex">
    <PercentileChip
      percentile={block.rate_percentile}
      flavor={
        bucket === 'conversion' ? 'conversion'
        : bucket === 'parity' ? 'parity'
        : 'recovery'
      }
      tc={tc}
      anchorRating={anchorRating}
      metricLabel={
        bucket === 'conversion' ? 'Conversion Rate'
        : bucket === 'parity' ? 'Parity Rate'
        : 'Recovery Rate'
      }
      testId={`${testId}-rate-percentile-chip`}
      nGames={block.rate_percentile_n_games}
      value={block.rate_percentile_value}
    />
  </span>
)}
```

3. The `MetricBlockProps` interface (lines 86–100) needs no changes — `block: PerTcBucketStats` already flows through; the new fields are on `PerTcBucketStats`. `anchorRating: number | undefined` is already a prop.

**Mobile parity:** `MetricBlock` is a single component (no separate mobile renderer). The `EndgameMetricsByTcCard` uses responsive CSS (`flex-col lg:flex-row`) but one `MetricBlock` instance. Adding the chip to `MetricBlock` covers both desktop and mobile automatically — confirmed by lines 404–439 which show a single `<MetricBlock>` call per bucket with no mobile-specific branch.

**Tooltip differentiation (D-03):** The existing ΔES-gap chip at lines 217–234 already uses `flavor="conversion"` (etc.) with `metricLabel="${BUCKET_DISPLAY_LABELS[bucket]} Eval Score Gap"`. The new rate chip uses the SAME `flavor` values but `metricLabel="Conversion Rate"` (etc.). The `PercentileChip` popover body at `PercentileChip.tsx` line 218 weaves `metricLabel` into bullet 1's text: "Your recent Conversion Rate +X% is better than Y% of ~Z-rated players in {tc}." vs "Your recent Conversion Eval Score Gap +X% is…" — the noun alone distinguishes the two chips.

---

## Shared Patterns

### `PercentileRow` null-gating (chip suppression)
**Source:** `app/repositories/user_benchmark_percentiles_repository.py` lines 158–203 (`fetch_for_user` return shape)
**Apply to:** `endgame_service.py` lookup block, `EndgameMetricsByTcCard.tsx` render gate

Row absence = below floor (Plan 13 gap-closure). Backend: `_effective_rows.get("conversion_rate", {}).get(tc_bucket)` returns `None` when no row exists. Frontend: `block.rate_percentile != null && anchorRating != null` gates chip render. Never check a separate `isFloor` flag — absence is the signal.

### `_ = source` idiom
**Source:** `app/services/canonical_slice_sql.py` line 749 (and all other builders)
**Apply to:** All 3 new rate builders

Every pooled builder accepts `source` but does not use it in the SQL body (the cohort difference lives entirely in `selected_users_cte`). Assign `_ = source` to silence the unused-variable linter.

### `per_user_values` user_id projection (Pitfall 1)
**Source:** `app/services/canonical_slice_sql.py` line 829 comment
**Apply to:** All 3 new rate builders

`per_user_values` MUST project `(user_id, metric_value, n_games)`. The `gen_global_percentile_cdf.py` regen script JOINs `per_user_values` against `per_user_anchor USING (user_id)` — omitting `user_id` silently produces empty CdfTables.

### `create_type=False` SAEnum invariant (Pitfall 3)
**Source:** `app/models/user_benchmark_percentile.py` line 64
**Apply to:** Migration + model update

Alembic owns the ENUM lifecycle. `--autogenerate` cannot detect `ADD VALUE` (Pitfall 4). Always write the migration manually following `fd5b551f381c`. Keep SAEnum string values and Postgres ENUM values in sync.

### `inline-flex w-full` h4 for `ml-auto` chip
**Source:** `frontend/src/components/charts/EndgameTimePressureCard.tsx` (all chip-bearing header rows use `flex items-center` or `inline-flex w-full`)
**Apply to:** `EndgameMetricsByTcCard.tsx` `MetricBlock` h4 (line 150)

`inline-flex` without `w-full` shrinks to content — `ml-auto` has no effect. Adding `w-full` makes the container fill the row so the chip pushes to the right edge.

---

## No Analog Found

No files in this phase lack a codebase analog. All 9 files extend existing patterns.

---

## Metadata

**Analog search scope:** `app/services/`, `app/models/`, `app/repositories/`, `app/schemas/`, `alembic/versions/`, `scripts/`, `frontend/src/components/charts/`, `frontend/src/types/`
**Files scanned:** 14 source files read directly; 6 searched via grep
**Pattern extraction date:** 2026-05-30
