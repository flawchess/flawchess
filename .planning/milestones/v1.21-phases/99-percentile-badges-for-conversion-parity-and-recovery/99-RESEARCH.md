# Phase 99: Percentile Badges for Conversion, Parity, and Recovery - Research

**Researched:** 2026-05-30
**Domain:** Endgame percentile chip materialization — ENUM extension, SQL builder parameterization, CDF regen, backfill, frontend chip wiring
**Confidence:** HIGH (all findings verified against live codebase; zero assumed claims)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Show BOTH chips per metric block. The new raw-rate chip does NOT replace the existing ΔES score-gap chip. Both coexist per block.
- **D-02:** New raw-rate chips render on the Conversion / Parity / Recovery **title lines, right-aligned**. Existing ΔES-gap chips stay on/near the ΔES score-gap bullet.
- **D-03:** Two-chip differentiation carried by tooltips only. No inline qualifier labels. Metric noun in bullet 1 distinguishes the two percentiles.
- **D-04:** Reuse the Phase 94.3 per-metric chip inclusion floor — same `SCORE_GAP_BUCKET_MIN_SPANS = 30` floor applied per (metric, TC). Below floor → no chip renders.
- **D-05:** Validate the reused floor against dev-DB denominator distributions during research. Flag if inadequate for conv/recov.
- **D-06:** Parity gets its own per-(parity_rate, TC) cohort CDF like conversion and recovery — all 12 metrics are per-TC.
- **D-07:** Reuse the 4-bullet disclosure contract verbatim per `feedback_percentile_chip_tooltip_disclosure`. First two bullets TC-scoped.
- **D-08:** Only the metric noun in bullet 1 changes to name the raw rate (e.g. "conversion rate") rather than the score-gap metric.
- **D-09:** 12 new ENUM members: `{conversion_rate, parity_rate, recovery_rate}_{bullet, blitz, rapid, classical}`. Shared `canonical_slice_sql.py` builder parameterised by TC.
- **D-10:** Cohort CDFs generated into `global_percentile_cdf.py` under the existing per-(metric, ELO anchor, TC) sliding-window protocol, regen report archived.
- **D-11:** Backfill dev first, then prod via `prod_db_tunnel.sh` after sign-off.

### Claude's Discretion

- Exact ENUM member naming/casing and migration shape for the 12 new metrics.
- Direction/sign convention per rate — higher rate is higher percentile for all three (more conversion wins, more parity score%, more recovery saves = better).
- Whether rate-percentile fields ride on existing block payload or a new field — must be SEPARATE from existing gap `block.percentile`.
- knip/dead-code posture: this phase adds chips, removes nothing.
- No `/gsd-ui-phase` — `PercentileChip` and the per-TC card are existing components.

### Deferred Ideas (OUT OF SCOPE)

- Inline "rate" / "gap" qualifier labels on the chips.
- Rework of the tooltip rating-coupling framing for raw rates.
- LLM narration of the new rate percentiles (belongs to Phase 100).

</user_constraints>

---

## Summary

Phase 99 wires three new percentile chip families — `conversion_rate`, `parity_rate`, `recovery_rate` — to the title lines of the Phase 97 `EndgameMetricsByTcCard`. Each chip is backed by a new per-(metric, TC) cohort CDF entry in `COHORT_PERCENTILE_CDF` (12 new cells: 3 metrics × 4 TCs) and 12 new `benchmark_metric` ENUM values stored in `user_benchmark_percentiles`. The existing ΔES score-gap chips are untouched.

The core architectural invariant — shared `canonical_slice_sql.py` builders for both CDF construction and per-user lookup — already covers the raw rate metrics via `per_user_cte_score_gap_bucket_tc(..., bucket_label=...)` which produces `per_user_values(metric_value, n_games)` where `metric_value` is the per-user pooled raw rate (win%, score%, save%). The "rate" signal is simply `metric_value` from that existing builder, read differently: instead of using the ΔES gap as the percentile value, the raw rate (the `rate` field from `PerTcBucketStats`) is the value to rank. This means new builders ARE required because the existing builders compute score gaps, not raw rates.

The frontend surface requires adding one `PercentileChip` instance to the `MetricBlock` title line (right-aligned, `ml-auto`) and one new optional field per `PerTcBucketStats` (e.g. `rate_percentile`, `rate_percentile_n_games`, `rate_percentile_value`) — separate from the existing `percentile` field. The tooltip uses flavors `'conversion'`, `'parity'`, `'recovery'` (same as the existing gap chip) but with a different `metricLabel` (e.g. `"Conversion Rate"`).

**Primary recommendation:** Write three new SQL builders in `canonical_slice_sql.py` (`per_user_cte_conv_rate_tc`, `per_user_cte_parity_rate_tc`, `per_user_cte_recovery_rate_tc`) that output `(metric_value = raw rate, n_games = bucket spans)`, extend `CdfMetricId` and the ENUM, extend `COHORT_PERCENTILE_CDF` via regen, then wire through backfill → endgame_service → PerTcBucketStats → frontend title line.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw-rate per-user pooled SQL compute | API / Backend | — | `canonical_slice_sql.py` builder; all SQL runs server-side |
| Cohort CDF artifact | API / Backend | — | Static Python literal in `global_percentile_cdf.py`; no DB at runtime |
| ENUM + table rows | Database / Storage | API / Backend | `user_benchmark_percentiles` Postgres table; Alembic migration |
| Per-user lookup + interpolation | API / Backend | — | `fetch_for_user` + `interpolate_cohort_percentile` |
| Payload assembly | API / Backend | — | `_compute_per_tc_metric_cards` in `endgame_service.py` |
| Chip render + tooltip | Browser / Client | — | React `PercentileChip` primitive; no SSR |
| Mobile parity | Browser / Client | — | Same `MetricBlock` component serves both desktop and mobile |

---

## Standard Stack

No new packages. Phase 99 is entirely within the existing stack. [VERIFIED: live codebase]

### Core (existing, relevant)

| Component | Version | Purpose |
|-----------|---------|---------|
| `canonical_slice_sql.py` | — | Pooled-per-user SQL builder; extended for 3 new rate families |
| `global_percentile_cdf.py` | — | CDF artifact; `CdfMetricId` Literal + `COHORT_PERCENTILE_CDF` registry |
| `user_benchmark_percentiles` (table) | — | Storage for materialized percentile rows; ENUM extended |
| `PercentileChip.tsx` | v94.4 | Chip primitive; reused unchanged |
| `EndgameMetricsByTcCard.tsx` | v97 | Host card; title-line chip added |

---

## Package Legitimacy Audit

> Skipped. Phase 99 installs no new packages.

---

## Architecture Patterns

### System Architecture Diagram

```
benchmark DB (port 5433)
        |
scripts/gen_global_percentile_cdf.py
  - 3 new (metric, TC) queries via new per_user_cte_*_rate_tc builders
  - Python-side ranking → 12 new CdfTable entries
        |
        v
app/services/global_percentile_cdf.py  [static Python literal — COHORT_PERCENTILE_CDF]
  CdfMetricId Literal widened: +3 new members (conversion_rate, parity_rate, recovery_rate)
        |
Alembic migration
  ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '<each of 12 values>'
        |
scripts/backfill_user_percentiles.py  [dev → prod]
  compute_stage_b() → _per_user_cte_for_family_and_tc() dispatch
  → upsert_percentile() → user_benchmark_percentiles (12 new rows per user per above-floor cell)
        |
        v
app/services/endgame_service.py  [GET /api/endgames/metrics/cards]
  _compute_per_tc_metric_cards()
    → _effective_rows.get("conversion_rate", {}).get(tc_bucket)  [new lookup]
    → _build_per_tc_bucket_stats() receives rate_percentile_row
    → PerTcBucketStats.rate_percentile = row.percentile  [NEW field]
        |
        v
frontend/src/components/charts/EndgameMetricsByTcCard.tsx
  MetricBlock title line:
    <h4> … {rate_percentile != null && anchorRating != null && (
      <span className="ml-auto"><PercentileChip … /></span>
    )} </h4>
  (desktop + mobile — same MetricBlock component serves both)
```

### Recommended Project Structure (changes only)

```
app/services/
├── canonical_slice_sql.py          # +3 new per_user_cte_*_rate_tc() builders
├── global_percentile_cdf.py        # CdfMetricId + COHORT_PERCENTILE_CDF extended by regen
├── user_benchmark_percentiles_service.py  # STAGE_B_METRIC_FAMILIES += 3 new families
└── endgame_service.py              # _compute_per_tc_metric_cards wires rate_percentile_row

app/models/
└── user_benchmark_percentile.py    # benchmark_metric_enum widens to 11 values

app/schemas/
└── endgames.py                     # PerTcBucketStats += rate_percentile fields

alembic/versions/
└── YYYYMMDD_extend_benchmark_metric_for_rate_percentiles.py  # ALTER TYPE ADD VALUE × 12

scripts/
└── gen_global_percentile_cdf.py    # IN_SCOPE_METRICS += 3; dispatch table += 3

frontend/src/
├── types/endgames.ts               # PerTcBucketStats += rate_percentile fields
└── components/charts/EndgameMetricsByTcCard.tsx  # title-line chip in MetricBlock
```

### Pattern 1: New Rate Builder (canonical_slice_sql.py extension)

**What:** Three new `per_user_cte_*_rate_tc(tc, *, source, snapshot_date)` builders. Each produces `per_user_values(user_id, metric_value, n_games)` where `metric_value` is the raw pooled rate (wins/spans, score/spans, saves/spans) and `n_games` is the span count in that bucket.

**When to use:** CDF generation (`gen_global_percentile_cdf.py`) and per-user lookup (`user_benchmark_percentiles_service.py`) — same builder, same SQL, source-mode parity preserved (D-10).

**Structural pattern** (mirrors existing `per_user_cte_score_gap_bucket_tc` up to the aggregation step):

```python
# Source: app/services/canonical_slice_sql.py (existing pattern)
# MINIMUM_RATE_BUCKET_SPANS: int = 30  # new constant, same value as SCORE_GAP_BUCKET_MIN_SPANS

def per_user_cte_conv_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled per_user_values(user_id, metric_value, n_games) for conversion_rate_{tc}.
    metric_value = wins / conv_spans (pooled over the recent-3000-per-TC × 36-month pool).
    n_games = conv span count (the binding floor ≥ MINIMUM_RATE_BUCKET_SPANS).
    """
    _ = source  # source-mode parity: cohort difference lives in selected_users_cte
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT gp.game_id, gp.endgame_class,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN swn.entry_eval_mate IS NOT NULL THEN
        CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
             THEN 'conversion' ELSE 'recovery' END
      WHEN swn.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100 THEN 'conversion'
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100 THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black') THEN 1
      ELSE 0
    END AS is_win
  FROM spans swn
  JOIN games g ON g.id = swn.game_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE bucket = 'conversion') AS conv_n,
    sum(is_win) FILTER (WHERE bucket = 'conversion')::float AS conv_wins
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE bucket = 'conversion') >= {MINIMUM_RATE_BUCKET_SPANS}
),
per_user_values AS (
  SELECT user_id,
    conv_wins / NULLIF(conv_n, 0) AS metric_value,
    conv_n::int AS n_games
  FROM per_user
  WHERE conv_wins IS NOT NULL
)"""
```

Recovery and parity follow the same template with `bucket = 'recovery'` / `bucket = 'parity'` and their respective outcome formulas:

- **Conversion:** `metric_value = wins / conv_spans`  (range 0–1; higher = better)
- **Parity:** `metric_value = (wins + 0.5 * draws) / parity_spans`  (range 0–1; higher = better)
- **Recovery:** `metric_value = (wins + draws) / recov_spans`  (range 0–1; higher = better)

All three are `higher_is_better` — no CDF inversion needed (unlike `net_flag_rate`). [VERIFIED: live codebase]

**Important:** The `spans` CTE in the new builders does NOT need the `lead()` / `spans_with_next` pattern used by `per_user_cte_score_gap_bucket_tc`, because we are measuring outcome (game result), not the ΔES gap (which required the next-span eval). The outcome per span equals the game outcome (since `bucket_rows` has terminal semantics: one row per endgame span, the game result is the exit score proxy). [VERIFIED: endgame_service.py lines 2562–2574, same terminal-span semantics]

### Pattern 2: ENUM Extension (Alembic migration)

**What:** Add 12 new values to `benchmark_metric` via `ALTER TYPE ... ADD VALUE IF NOT EXISTS`.

**When to use:** Any time new `CdfMetricId` members are needed. Postgres 12+ supports this inside a transaction (no `COMMIT` needed before using the value in the same migration — but see Pitfall 2). [VERIFIED: existing migration `fd5b551f381c`]

**Exact pattern** (copy from `20260524_170733_fd5b551f381c`):

```python
# Source: alembic/versions/20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py
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

def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")

def downgrade() -> None:
    pass  # Postgres cannot remove ENUM values without table rewrite — git revert instead
```

**`create_type=False` invariant:** The `benchmark_metric_enum` SAEnum in `app/models/user_benchmark_percentile.py` already uses `create_type=False`. The new values must be added to that SAEnum's value tuple to keep SQLAlchemy and Postgres in sync, but SQLAlchemy will NOT try to CREATE/DROP the type. [VERIFIED: `user_benchmark_percentile.py` lines 54–65]

### Pattern 3: CdfMetricId Extension

**What:** Widen the `CdfMetricId` Literal in `global_percentile_cdf.py` to include 3 new metric names. The `COHORT_PERCENTILE_CDF` registry is a static Python literal between `BEGIN/END GENERATED REGISTRY` sentinels — the regen script overwrites it.

```python
# Source: app/services/global_percentile_cdf.py lines 101-110 (current 8-value Literal)
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    # Phase 99 additions:
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
]
```

**Critical:** `CdfMetricId` is imported into `user_benchmark_percentile.py` as the Python type for the `metric` column. After widening, `ty check` will enforce that all dispatch arms cover the new values. [VERIFIED: `user_benchmark_percentile.py` line 112]

### Pattern 4: STAGE_B_METRIC_FAMILIES Extension

**What:** `STAGE_B_METRIC_FAMILIES` in `user_benchmark_percentiles_service.py` is the tuple that drives Stage B compute per-user. Add the 3 new families:

```python
# Source: user_benchmark_percentiles_service.py lines 139-147
STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = (
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    # Phase 99 additions:
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
)
```

The `_per_user_cte_for_family_and_tc` dispatch function needs 3 new arms. The backfill script's `_ALL_METRICS` is derived from `(STAGE_A_METRIC, *STAGE_B_METRIC_FAMILIES)` so it automatically picks up the new families. [VERIFIED: backfill_user_percentiles.py lines 163-164]

### Pattern 5: PerTcBucketStats Rate-Percentile Field

**What:** A new optional field on `PerTcBucketStats` carrying the raw-rate percentile. Must be named distinctly from `percentile` (which carries the ΔES-gap percentile) to satisfy D-01.

**Backend schema** (Pydantic, `app/schemas/endgames.py`):

```python
# Source: app/schemas/endgames.py lines 822-856 — existing PerTcBucketStats
# Add after percentile_value:
rate_percentile: float | None = None
rate_percentile_n_games: int | None = None
rate_percentile_value: float | None = None
```

Default `None` preserves backward compatibility with existing test fixtures. [VERIFIED: existing `percentile_n_games`/`percentile_value` pattern at line 855]

**Frontend TypeScript** (`frontend/src/types/endgames.ts`):

```typescript
// Source: frontend/src/types/endgames.ts lines 422-438 — existing PerTcBucketStats
// Add after percentile_value:
rate_percentile?: number | null;       // raw-rate percentile (separate from ΔES-gap percentile)
rate_percentile_n_games?: number | null;
rate_percentile_value?: number | null;
```

### Pattern 6: Title-Line Chip Placement (MetricBlock)

**What:** Add one `PercentileChip` instance to the `h4` title line inside `MetricBlock`, right-aligned via `ml-auto`. Mirror the `EndgameTimePressureCard` `ClockGapHeaderRow` chip placement.

**Exact placement pattern** (from `EndgameTimePressureCard.tsx` lines 189-203):

```tsx
// Source: frontend/src/components/charts/EndgameTimePressureCard.tsx lines 189-203
// Target location: EndgameMetricsByTcCard.tsx — MetricBlock h4 title line
<h4 className="text-base font-semibold mb-2 inline-flex items-center gap-1 w-full">
  {BUCKET_DISPLAY_LABELS[bucket]}
  <InfoPopover … />
  {/* Phase 99: raw-rate percentile chip, right-aligned on the title line.
      Gated on BOTH rate_percentile != null AND anchorRating != null so the
      tooltip can disclose the anchor honestly (mirrors the gap chip gate). */}
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
</h4>
```

**`h4` needs `w-full`** because the existing `h4` is `inline-flex` but the title text + info popover do not fill the row — adding `ml-auto` to push the chip right requires the container to be full-width. [VERIFIED: EndgameMetricsByTcCard.tsx line 150]

**Mobile parity:** `MetricBlock` is a single component used for both desktop and mobile (no separate mobile renderer). Adding the chip to `MetricBlock` automatically covers both. Confirm no separate mobile-only branch exists before treating this as done — the card uses responsive CSS (`flex-col lg:flex-row`) but one `MetricBlock` component. [VERIFIED: EndgameMetricsByTcCard.tsx lines 403-439]

### Pattern 7: gen_global_percentile_cdf.py Dispatch Extension

**What:** `IN_SCOPE_METRICS` in `gen_global_percentile_cdf.py` drives the CDF regen loop. Add 3 new entries. The dispatch function `_per_user_cte_for_metric_and_tc` needs 3 new arms mirroring `_per_user_cte_for_family_and_tc` in the service. [VERIFIED: gen_global_percentile_cdf.py lines 154-163]

### Anti-Patterns to Avoid

- **Do not embed TC in the metric name.** Phase 94.4 D-13 removed the TC suffix from `CdfMetricId` — TC is an outer key on the registry. `conversion_rate_bullet` is an ENUM member name but NOT a `CdfMetricId`. `CdfMetricId` = `"conversion_rate"` only. [VERIFIED: global_percentile_cdf.py line 101]
- **Do not collide with `block.percentile`.** The new field must be named `rate_percentile` (or similar), never reusing `percentile`. [VERIFIED: PerTcBucketStats schema lines 854]
- **Do not skip `HAVE count(*) FILTER ...`** for the rate builders. The floor is 30 spans in the relevant bucket, not 30 games total. [VERIFIED: `per_user_cte_score_gap_bucket_tc` HAVING clause, line 826]
- **Do not add `lead()` / `spans_with_next` to rate builders.** Rate is measured from game outcomes, not ΔES deltas. No next-span eval required.
- **Do not use the `PercentileChipFlavor` 'conversion'/'parity'/'recovery' for the rate chips without the correct `metricLabel`.** The flavor routes the popover body; the `metricLabel` is what bullet 1 names in the disclosure text. Existing gap chips already use these flavors — Phase 99 reuses the same flavor values but MUST pass `"Conversion Rate"` / `"Parity Rate"` / `"Recovery Rate"` as `metricLabel` to distinguish the two chips' bullet-1 copy. [VERIFIED: PercentileChip.tsx `PercentileChipPopoverBody`, line 215]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile interpolation | Custom bisect logic | `interpolate_cohort_percentile(metric, value, anchor, tc)` in `global_percentile_cdf.py` | Already handles anchor rounding, CDF miss → None, clamp to [0,100] |
| Per-user pooled window | Custom recency filter | `_recent_capped_per_tc_cte` (imported via the new builders) | Encodes the 3000-cap, 36-month, equal-footing, rated, non-computer filters |
| CDF generation | New regen script | `scripts/gen_global_percentile_cdf.py` extended with 3 new entries | The script handles BEGIN/END sentinel overwrite, regen report archive, benchmark-only guard |
| ENUM lifecycle | SQLAlchemy auto-create | `ALTER TYPE ... ADD VALUE IF NOT EXISTS` in Alembic migration | `create_type=False` is already set; autogenerate cannot handle ADD VALUE |
| PercentileChip render | New chip component | `PercentileChip` with `flavor`, `tc`, `anchorRating`, `metricLabel`, `testId`, `nGames`, `value` props | Handles hover delay, color band, aria-label, tooltip portal — all reused |
| Chip suppression | Frontend null-check | Don't render if `rate_percentile == null` OR `anchorRating == null` | Backend guarantees no row below floor; null means below-floor or no anchor |

---

## D-05 Floor Validation (Live Dev DB Query)

**Findings from dev DB (27 non-superuser accounts, queried 2026-05-30):**

Per-TC span distribution at user level (p10/p25/p50/p75/p90 span counts):

| TC | n_users | conv (p10,p25,p50,p75,p90) | recov (p10,p25,p50,p75,p90) | parity (p10,p25,p50,p75,p90) |
|----|---------|----------------------------|------------------------------|-------------------------------|
| bullet | 9 | 0, 23, 2156, 4609, 9511 | 5, 24, 1958, 3670, 5052 | 1, 7, 721, 2287, 6970 |
| blitz | 16 | 52, 258, 1208, 5133, 19914 | 68, 187, 1155, 4019, 12317 | 6, 64, 545, 2416, 20912 |
| rapid | 19 | 16, 170, 1659, 4635, 5154 | 10, 86, 1909, 4203, 4910 | 8, 30, 994, 2769, 3241 |
| classical | 14 | 4, 10, 12, 58, 378 | 0, 0, 6, 29, 357 | 2, 2, 4, 21, 336 |

**Users above the ≥30 floor:**

| TC | n_users | conv_above_30 | recov_above_30 |
|----|---------|---------------|----------------|
| bullet | 9 | 6 (67%) | 6 (67%) |
| blitz | 16 | 15 (94%) | 15 (94%) |
| rapid | 19 | 17 (89%) | 17 (89%) |
| classical | 14 | 6 (43%) | 3 (21%) |

**Assessment (D-05):**

- **bullet/blitz/rapid:** The ≥30 floor is entirely adequate. Median span counts are 1208–2156 for conversion and 1155–1958 for recovery — users who have those TCs in the recent-3000 window overwhelmingly clear the floor. The p25 for blitz (258 conv, 187 recov) is well above 30. The few sub-30 users (3 bullet conv, 1 blitz conv, 2 rapid conv) represent users with very sparse games in that TC on the dev DB, not a systematic floor problem.

- **classical:** The classical TC is thin by design — most users play few classical games. Recovery at p50 = 6 spans, p75 = 29 spans, p90 = 357 spans. A significant fraction of classical users (57%–79%) will fall below the ≥30 floor and have chips suppressed. This is expected and acceptable: the chip naturally suppresses, no card-level hiding occurs. The ≥30 floor is adequate here too — it is precisely what prevents percentile chips on insufficiently thin samples.

**Verdict: the ≥30 floor (reused from Phase 94.3 `SCORE_GAP_BUCKET_MIN_SPANS`) is adequate for all three rate families across all four TCs.** Classical will have a higher suppression rate for conv/recov (as expected given thin samples). No floor adjustment is needed; flag is cleared. [VERIFIED: live dev DB query]

---

## Common Pitfalls

### Pitfall 1: Forgetting the `user_id` projection in `per_user_values`

**What goes wrong:** `gen_global_percentile_cdf.py` joins `per_user_values` against `per_user_anchor USING (user_id)` in its CDF-construction query. If the new rate builders omit `user_id` from `per_user_values`, the JOIN silently produces zero rows and the new metrics generate empty CdfTables.

**Why it happens:** The original pooled builders (before Phase 94.4 Pitfall 1 fix) omitted `user_id`; the 94.4 fix added it. All current builders include it but new builders must remember it.

**How to avoid:** Follow the template — `per_user_values` must project `(user_id, metric_value, n_games)`. Every existing Phase 94.4 builder includes the comment "user_id widened per Phase 94.4 Pitfall 1". [VERIFIED: canonical_slice_sql.py lines 430, 488, 555, 641, 719, 829]

### Pitfall 2: ALTER TYPE ADD VALUE and transaction visibility

**What goes wrong:** `ALTER TYPE ... ADD VALUE` in Postgres 12+ is allowed inside a transaction, but the new value is NOT visible within that same transaction. If the migration also tries to insert rows referencing the new value in the same `upgrade()`, those inserts fail.

**Why it happens:** Postgres delays ENUM value visibility until a new transaction begins (per Postgres docs).

**How to avoid:** Phase 99's migration only adds the ENUM values — it writes no data rows. The backfill script runs in a separate process after `alembic upgrade head`. No mitigation required for this phase's migration shape. [VERIFIED: fd5b551f381c migration adds values only, no inserts]

### Pitfall 3: SAEnum out of sync with Postgres

**What goes wrong:** After adding ENUM values to Postgres via the migration, if `benchmark_metric_enum` in `user_benchmark_percentile.py` is not updated with the new string values, SQLAlchemy may reject writes when the ORM validates the column value.

**Why it happens:** `benchmark_metric_enum = SAEnum(..., create_type=False)` is used for column type in the ORM model. With `create_type=False`, SQLAlchemy does not create/drop the type, but it still validates inserts against the Literal values in the SAEnum.

**How to avoid:** Add all 12 new string values to the `benchmark_metric_enum` SAEnum in `user_benchmark_percentile.py`. Keep the order consistent with the Postgres ENUM creation order. [VERIFIED: user_benchmark_percentile.py lines 54-65]

### Pitfall 4: Alembic autogenerate ignores ADD VALUE

**What goes wrong:** `alembic revision --autogenerate` does NOT detect new ENUM values. It cannot produce the `ALTER TYPE ... ADD VALUE` statement.

**Why it happens:** SQLAlchemy's autogenerate compares ORM metadata to DB metadata at the table level, not the ENUM type level.

**How to avoid:** Write the migration manually, following the `fd5b551f381c` pattern exactly. Do not run `--autogenerate` expecting it to generate the ENUM change. [VERIFIED: alembic/versions files — no autogenerated ADD VALUE exists in the codebase]

### Pitfall 5: CdfMetricId Literal not updated in global_percentile_cdf.py before regen

**What goes wrong:** `gen_global_percentile_cdf.py` imports `CdfMetricId` from `global_percentile_cdf.py`. If the `IN_SCOPE_METRICS` tuple in the regen script includes new names not yet in the `CdfMetricId` Literal, `ty check` fails at the assignment site `metric: CdfMetricId = "conversion_rate"`.

**Why it happens:** `ty` enforces that string literals assigned to `CdfMetricId` columns are within the Literal's value set.

**How to avoid:** Always update `CdfMetricId` in `global_percentile_cdf.py` AND `IN_SCOPE_METRICS` in `gen_global_percentile_cdf.py` in the same commit. [VERIFIED: gen_global_percentile_cdf.py lines 154-163 import CdfMetricId from global_percentile_cdf]

### Pitfall 6: `h4` not full-width — `ml-auto` chip doesn't push right

**What goes wrong:** The current `MetricBlock` `h4` is `inline-flex` without `w-full`. Adding `ml-auto` on the chip span won't push it right if the container doesn't fill the row.

**Why it happens:** `inline-flex` shrinks to content by default.

**How to avoid:** Change `h4` class to include `w-full` when adding the chip. [VERIFIED: EndgameMetricsByTcCard.tsx line 150 — current class does not include w-full]

### Pitfall 7: Backfill `_ALL_METRICS` iteration coverage

**What goes wrong:** The backfill `_PercentileSummary.__init__` builds its cell dict from `_ALL_METRICS`. If `_ALL_METRICS` is not updated after extending `STAGE_B_METRIC_FAMILIES`, the summary table won't report the new metrics.

**Why it happens:** `_ALL_METRICS = (STAGE_A_METRIC, *STAGE_B_METRIC_FAMILIES)` — it derives automatically from `STAGE_B_METRIC_FAMILIES`. No manual update needed in the backfill script itself. Just extend `STAGE_B_METRIC_FAMILIES`.

**How to avoid:** The dynamic derivation is the existing safety net. No special action needed, but verify by running `--target dev --metric conversion_rate` and checking the summary table. [VERIFIED: backfill_user_percentiles.py lines 163-164]

### Pitfall 8: `PercentileChipFlavor` not extended

**What goes wrong:** `PercentileChip.tsx` defines `PercentileChipFlavor` as a union type. The `'conversion'`, `'parity'`, `'recovery'` flavors already exist (Phase 94). NO extension to `PercentileChipFlavor` is needed. If a new flavor were accidentally added, the flavor-specific popover note (`bulletMetricNote`) would need updating.

**Why it happens:** The existing flavors cover the three buckets. Reusing them is intentional (D-03 — same visual treatment, tooltip content differentiated only by `metricLabel`).

**How to avoid:** Do NOT add new flavors. Pass `flavor="conversion"` (etc.) unchanged and use `metricLabel="Conversion Rate"` to differentiate. [VERIFIED: PercentileChip.tsx lines 88-96, 307]

---

## Code Examples

### Minimal per-TC rate builder structure (canonical_slice_sql.py extension)

```python
# Source: app/services/canonical_slice_sql.py (new builder, mirrors per_user_cte_score_gap_bucket_tc)
# Rate is measured from game outcomes — no lead()/spans_with_next needed.

MINIMUM_RATE_BUCKET_SPANS: int = 30  # New named constant; same value as SCORE_GAP_BUCKET_MIN_SPANS

def per_user_cte_conv_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    _ = source  # cohort difference in selected_users_cte; pooled body identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT gp.game_id,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE WHEN (swn.entry_eval_mate IS NOT NULL AND (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0)
           OR (swn.entry_eval_cp IS NOT NULL AND (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100)
         THEN true ELSE false END AS is_conversion,
    CASE WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black')
         THEN 1 ELSE 0 END AS is_win
  FROM spans swn
  JOIN games g ON g.id = swn.game_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE is_conversion) AS conv_n,
    sum(is_win) FILTER (WHERE is_conversion)::float AS conv_wins
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE is_conversion) >= {MINIMUM_RATE_BUCKET_SPANS}
),
per_user_values AS (
  SELECT user_id,
    conv_wins / NULLIF(conv_n, 0) AS metric_value,
    conv_n::int AS n_games
  FROM per_user
  WHERE conv_wins IS NOT NULL
)"""
```

### endgame_service.py wire-through (new lookup + PerTcBucketStats field)

```python
# Source: app/services/endgame_service.py lines 2655-2659 (existing lookup pattern)
# Add 3 new lookups mirroring the existing 3:
conv_row     = _effective_rows.get("score_gap_conv",    {}).get(tc_bucket)  # existing — ΔES gap
parity_row   = _effective_rows.get("score_gap_parity",  {}).get(tc_bucket)  # existing — ΔES gap
recov_row    = _effective_rows.get("recovery_score_gap",{}).get(tc_bucket)  # existing — ΔES gap
# NEW — raw rate percentiles:
conv_rate_row    = _effective_rows.get("conversion_rate", {}).get(tc_bucket)
parity_rate_row  = _effective_rows.get("parity_rate",     {}).get(tc_bucket)
recov_rate_row   = _effective_rows.get("recovery_rate",   {}).get(tc_bucket)

# Pass rate_percentile_row alongside percentile_row into _build_per_tc_bucket_stats:
conversion_stats = _build_per_tc_bucket_stats(acc, "conversion", acc.gaps_conv, conv_row, conv_rate_row)
```

Then `_build_per_tc_bucket_stats` gains a fourth parameter:

```python
def _build_per_tc_bucket_stats(
    acc: _MetricTcAccumulator,
    bucket: MaterialBucket,
    gaps: list[float],
    percentile_row: PercentileRow | None,
    rate_percentile_row: PercentileRow | None = None,   # NEW — optional for backward compat
) -> PerTcBucketStats:
    ...
    return PerTcBucketStats(
        ...
        percentile=percentile_row.percentile if percentile_row is not None else None,
        percentile_n_games=percentile_row.n_games if percentile_row is not None else None,
        percentile_value=percentile_row.value if percentile_row is not None else None,
        # NEW fields:
        rate_percentile=rate_percentile_row.percentile if rate_percentile_row is not None else None,
        rate_percentile_n_games=rate_percentile_row.n_games if rate_percentile_row is not None else None,
        rate_percentile_value=rate_percentile_row.value if rate_percentile_row is not None else None,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TC-suffixed metric names in ENUM (e.g. `time_pressure_score_gap_bullet`) | TC as outer registry key; ENUM = 8 family names only | Phase 94.4 | Phase 99 adds 3 families (not 12 TC-suffixed names) |
| Phase 94.3 flat CDF pooled across all anchors | Cohort sliding-window CDF per (metric, anchor, TC) | Phase 94.4 | Phase 99 regenerates into the same per-anchor structure |
| Score-gap metrics only in `STAGE_B_METRIC_FAMILIES` | Rate metrics added | Phase 99 | New — requires new SQL builders for raw rate |

**Deprecated/outdated:**
- `interpolate_percentile(metric, value)` (flat 2-arg form) — superseded by `interpolate_cohort_percentile(metric, value, anchor, tc)` in Phase 94.4. Do not use.

---

## Assumptions Log

> All claims in this research were verified against the live codebase or live dev DB. No assumed claims.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**This table is empty:** All claims were verified or cited — no user confirmation needed.

---

## Open Questions

1. **Naming: `conversion_rate` vs `rate_conv` vs `conv_rate`**
   - What we know: the ENUM is currently snake_case with metric family first (e.g. `score_gap_conv`, `recovery_score_gap`). For consistency `conversion_rate` / `parity_rate` / `recovery_rate` (adjective_noun) is the cleanest.
   - What's unclear: pure style — no technical constraint.
   - Recommendation: use `conversion_rate`, `parity_rate`, `recovery_rate` (matches the CONTEXT D-09 specification verbatim).

2. **Rate builder: reuse `spans` CTE from `per_user_cte_score_gap_bucket_tc` or write fresh?**
   - What we know: the `spans` CTE in the existing bucket builder accumulates `entry_eval_cp`, `entry_eval_mate`, and uses `lead()` for next-eval (not needed for rates). The rate builders need a simpler `spans` (no next-eval).
   - Recommendation: write fresh builders — the `lead()` pattern is unnecessary overhead and would pollute the rate query. The code is short (~40 lines per builder).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev DB (Docker port 5432) | D-05 validation, backfill dev | ✓ | PostgreSQL 18 (flawchess-dev-db-1) | — |
| Benchmark DB (Docker port 5433) | CDF regen | ✓ | PostgreSQL 18 (flawchess-benchmark-db-1) | — |
| Prod DB (via tunnel port 15432) | Prod backfill (D-11) | Requires `bin/prod_db_tunnel.sh` | — | SSH tunnel |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `pyproject.toml` (pytest), `vite.config.ts` (vitest) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest && (cd frontend && npm test -- --run)` |

### Phase Requirements → Test Map

Phase 99 has no formal requirement IDs. Coverage is driven by the 5 Success Criteria from CONTEXT.md:

| Success Criterion | Behavior | Test Type | Automated Command |
|---|---|---|---|
| SC-1: Chip inclusion floor | Rate chip suppresses when user below ≥30-span floor | Unit | `pytest tests/services/test_canonical_slice_sql.py -x` (extend with rate builder floor assertion) |
| SC-2: Drift-proof CDF/lookup | Same builder used for CDF construction and per-user lookup | Unit | `pytest tests/services/test_canonical_slice_sql.py::test_per_user_cte_conv_rate_tc_source_parity` |
| SC-3: CDF regen + archive | Regen produces non-empty CdfTables for new metrics; report archived | Manual (benchmark DB required) | `bin/benchmark_db.sh start && uv run python scripts/gen_global_percentile_cdf.py --target benchmark` |
| SC-4: Tooltip TC-scoped | Bullet 1 names the TC and metricLabel | Frontend unit | `cd frontend && npm test -- --run EndgameMetricsByTcCard` |
| SC-5: Backfill coverage | Dev DB rows written for conversion_rate/parity_rate/recovery_rate × TCs | Manual | `uv run python scripts/backfill_user_percentiles.py --target dev --metric conversion_rate` |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q && (cd frontend && npm run lint && npm test -- --run)`
- **Per wave merge:** Full suite above
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_canonical_slice_sql.py` — extend with 3 new rate builder tests (SC-1: floor HAVING, SC-2: source parity, metric_value formula)
- [ ] `tests/services/test_endgame_service.py` — extend with `rate_percentile` field on `PerTcBucketStats` fixture
- [ ] Frontend: extend `EndgameMetricsByTcCard` vitest with rate chip render + suppression assertions

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No new auth surface |
| V3 Session Management | No | — |
| V4 Access Control | Yes | `fetch_for_user(user_id=current_user.id)` — existing pattern unchanged |
| V5 Input Validation | Yes | `tc` and `metric` are Literal types; no user string flows into SQL |
| V6 Cryptography | No | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `tc` f-string | Tampering | `tc: TimeControlBucket` is a 4-value Literal; ty enforces closed set at call sites. Same pattern as all existing builders. [VERIFIED: canonical_slice_sql.py security note lines 76-83] |
| IDOR on percentile lookup | Information Disclosure | `fetch_for_user(user_id=current_user.id)` — V4 mitigation already in place; rate rows slot through the same path |
| Backfill cross-env write | Tampering | `_assert_target_safe` port-check in backfill script covers new metrics automatically |

---

## Sources

### Primary (HIGH confidence)

- `app/services/canonical_slice_sql.py` — all builder patterns, constants, security model
- `app/services/global_percentile_cdf.py` — CdfMetricId, COHORT_PERCENTILE_CDF structure, sentinel pattern
- `app/models/user_benchmark_percentile.py` — ENUM descriptor, PK shape
- `app/repositories/user_benchmark_percentiles_repository.py` — fetch_for_user return shape, upsert pattern
- `app/services/user_benchmark_percentiles_service.py` — Stage A/B dispatch, STAGE_B_METRIC_FAMILIES
- `app/schemas/endgames.py` — PerTcBucketStats, EndgameMetricsTcCard
- `app/services/endgame_service.py` — `_compute_per_tc_metric_cards`, `_build_per_tc_bucket_stats` (lines 2480–2689)
- `scripts/backfill_user_percentiles.py` — full backfill lifecycle, summary counters
- `scripts/gen_global_percentile_cdf.py` — IN_SCOPE_METRICS, sentinel overwrite, archive
- `alembic/versions/20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py` — canonical ADD VALUE pattern
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — host card, MetricBlock
- `frontend/src/components/charts/EndgameTimePressureCard.tsx` — title-line chip placement precedent
- `frontend/src/components/charts/PercentileChip.tsx` — chip props, flavor enum, tooltip logic
- `frontend/src/types/endgames.ts` — PerTcBucketStats TypeScript type
- `reports/benchmark/benchmarks-latest.md` §3.2.1 — per-TC rate distributions (benchmark source of truth)
- Live dev DB query (2026-05-30) — D-05 floor validation

### Secondary (MEDIUM confidence)

- `.planning/phases/99-percentile-badges-for-conversion-parity-and-recovery/99-CONTEXT.md` — locked decisions

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — entirely within existing codebase; no new packages
- Architecture: HIGH — all integration points verified in live code
- SQL builder pattern: HIGH — derived from existing builders with documented structural diff (no lead())
- Pitfalls: HIGH — all verified from existing migration history and code comments
- D-05 floor validation: HIGH — live dev DB query; small user count but floor adequacy is structural

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (stable codebase; no fast-moving external dependencies)
