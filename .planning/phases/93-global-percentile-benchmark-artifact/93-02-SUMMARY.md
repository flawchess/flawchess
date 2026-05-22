---
phase: 93-global-percentile-benchmark-artifact
plan: 02
status: complete
completed: 2026-05-22
---

# Plan 93-02 Summary

Mechanized the global empirical-CDF artifact end-to-end: typed Python registry + helper, manual recalibration script (`backfill_eval.py`-style safety guard), 11 unit tests, and the initial markdown report. Tasks 1+2 executed by gsd-executor; Task 3 (HUMAN-UAT) executed inline by the orchestrator against the live benchmark DB after operator authorization at the checkpoint.

## What shipped

| File | Role |
|------|------|
| `app/services/global_percentile_cdf.py` | Typed `GLOBAL_PERCENTILE_CDF: Mapping[CdfMetricId, CdfTable]` registry + `interpolate_percentile(metric_id, value)` helper. Python-only (D-01), sibling of `endgame_zones.py` (D-04). Pure module — no DB/I/O at import. |
| `scripts/gen_global_percentile_cdf.py` | Manual recalibration script. `--db benchmark` only; safety guard refuses unless URL contains `flawchess_benchmark` AND `:5433` (mirrors `scripts/backfill_eval.py` D-01 pattern). |
| `tests/services/test_global_percentile_cdf.py` | 11 unit tests covering structural invariants (4 keys, 99 p1..p99 breakpoints, monotone non-decreasing, snapshot month, n_users floor) and `interpolate_percentile` behavior (clamps, linear interpolation, NaN → None, unknown metric → None). |
| `reports/global-percentile-cdf-latest.md` | Initial report with per-metric breakpoint tables (99 rows each) + per-rating-bucket sanity check (5 buckets × n_users/median/skew/kurt). |

## CdfTable shape (final)

```python
@dataclass(frozen=True)
class CdfTable:
    breakpoints: tuple[float, ...]   # length 99, monotone non-decreasing, 0-1 score-gap units
    n_users: int                     # per-metric cohort size from the benchmark snapshot
    snapshot_month: str = BENCHMARK_DB_SNAPSHOT_MONTH  # "2026-03"
```

## Generator script constants

`INCLUSION_FLOOR_SCORE_GAP_EG=30`, `INCLUSION_FLOOR_SCORE_GAP_NON_EG=30`, `INCLUSION_FLOOR_ACHIEVABLE=20`, `INCLUSION_FLOOR_SECTION2_PER_BUCKET=20`, `BREAKPOINTS=tuple(i/100 for i in range(1, 100))`, `SPARSE_CELL_ELO=2400`, `SPARSE_CELL_TC="classical"`, `EQUAL_FOOTING_TOL=100`, `OUTPUT_MODULE_PATH`, `OUTPUT_REPORT_PATH`, `BENCHMARK_DB_NAME_TOKEN="flawchess_benchmark"`, `BENCHMARK_DB_PORT_TOKEN=":5433"`.

## Live UAT results (2026-05-22)

Real run against the benchmark DB (port 5433, snapshot 2026-03).

### Per-metric breakpoint range (p1 / p50 / p99)

| metric | n_users | p1 | p50 | p99 |
|---|---:|---:|---:|---:|
| `score_gap` | 2003 | −0.3149 | −0.0116 | +0.2917 |
| `achievable_score_gap` | 2299 | −0.2182 | +0.0060 | +0.2082 |
| `section2_score_gap_conv` | 2060 | −0.3461 | −0.0500 | +0.1053 |
| `section2_score_gap_parity` | 1804 | −0.1697 | +0.0035 | +0.1665 |

All four metrics show monotonically non-decreasing breakpoints across all 99 indices (enforced by Test 5).

### Sanity check vs 2026-05-22 pre-flight (`reports/benchmarks-gap-metrics-percentile-candidacy.md`)

For `section2_score_gap_conv` (conversion ΔES) the pre-flight expected ~−0.95 skew and ~+1.42 excess kurtosis. Per-bucket numbers from the regenerated report bracket those values:

| rating bucket | n_users | median | skew | excess kurt |
|---|---:|---:|---:|---:|
| 800 | 336 | −10.9pp | −1.0777 | +1.2445 |
| 1200 | 494 | −6.5pp | −1.0485 | +1.6716 |
| 1600 | 514 | −4.1pp | −0.8603 | +0.7136 |
| 2000 | 435 | −1.5pp | −0.9337 | +0.9416 |
| 2400 | 281 | −1.3pp | −0.3811 | +0.3628 |

Sign correct (left-skewed conversion); magnitude consistent with pre-flight; the 2400 bucket shows expected attenuation. No order-of-magnitude or sign drift.

### Conv p50 = −0.05 inside existing ZoneSpec band `(-0.11, 0.00)`

Confirms continuity with the ZoneSpec rebuild from Phase 88.3. The percentile artifact and the zone artifact agree on cohort-typical conversion shape.

## Idempotency

| target | result |
|---|---|
| `app/services/global_percentile_cdf.py` | **byte-identical** on re-run (`diff` empty) |
| `reports/global-percentile-cdf-latest.md` | differs only in `Snapshot taken` ISO timestamp; the rotation rule fires on re-run as designed |

The committed Python source (which Phase 94 imports) is fully deterministic. Report timestamp variance is by design — each re-run rotates the prior latest to a date-stamped archive (D-07).

## Gates

| gate | result |
|---|---|
| `uv run ruff format app/ tests/ scripts/` | 3 files unchanged |
| `uv run ruff check ...` | All checks passed |
| `uv run ty check ...` | All checks passed |
| `uv run pytest tests/services/test_global_percentile_cdf.py -x` | 11/11 pass |
| `uv run pytest -x` (full suite, 1629 tests) | 1629 passed, 6 skipped |

## D-* compliance

- **D-01 (Python-only, no TS mirror)**: `scripts/gen_endgame_zones_ts.py` and `frontend/src/generated/endgameZones.ts` untouched.
- **D-03 (no new MetricId)**: `CdfMetricId` is a narrower `Literal` over 4 existing `MetricId` values; no new IDs introduced.
- **D-04 (sibling not graft)**: module sits next to `endgame_zones.py`, mirrors its typed-`Mapping` + frozen-dataclass + purity pattern.
- **D-07 (rotation rule)**: confirmed on the idempotency re-run — `reports/global-percentile-cdf-latest.md` rotated cleanly.

## Plan deviation flagged

The plan's `<interfaces>` block names `from app.schemas.endgames import MetricId`, but `MetricId` is canonically defined in `app/services/endgame_zones.py` (the schemas module re-exports it via `app/schemas/insights.py`). The executor imported from the canonical definition site (`app.services.endgame_zones`). Functionally equivalent (same `Literal`); documentation drift in the plan, not a behavioral deviation.

## Phase 94 hand-off

```python
from app.services.global_percentile_cdf import (
    GLOBAL_PERCENTILE_CDF,
    interpolate_percentile,
    CdfTable,
    BENCHMARK_DB_SNAPSHOT_MONTH,
    BREAKPOINT_LABELS,
)
```

`interpolate_percentile(metric_id, value) -> float | None` is the per-request public API. Returns `None` for unknown metrics or NaN values; clamps to 0.0 / 100.0 at the p1 / p99 edges.
