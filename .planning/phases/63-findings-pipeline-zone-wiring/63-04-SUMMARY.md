---
phase: 63-findings-pipeline-zone-wiring
plan: 04
subsystem: backend/services
tags: [python, pydantic, async, sqlalchemy, insights, endgame, compute-findings, hash, trend, flags]

# Dependency graph
requires:
  - "63-01 — endgame_zones.py registry + assign_zone / assign_bucketed_zone / sample_quality helpers + named thresholds"
  - "63-03 — insights.py schemas: FilterContext, SubsectionFinding, EndgameTabFindings, FlagId"
provides:
  - "app/services/insights_service.py — compute_findings(filter_context, session, user_id) -> EndgameTabFindings"
  - "Private helpers: _compute_subsection_findings, 10 per-subsection builders, _compute_trend, _compute_flags, _compute_hash, _endgame_skill_from_material_rows, _empty_finding"
  - "Deterministic findings_hash: SHA256 of canonical JSON (model_dump_json -> json.loads -> json.dumps sort_keys=True)"
  - "Four cross-section flags computed from all_time findings using endgame_zones constants"
affects:
  - "63-05 (tests): compute_findings + helpers are ready for comprehensive test coverage (zone assign, trend gating, flag computation, hash stability, empty-window paths)"
  - "Phase 65 (LLM endpoint): compute_findings is the contract consumed by prompt-assembly; field names are LOCKED (renaming after ships forces prompt revision)"
  - "Phase 67 (regression test): findings_hash stability is implementable and smoke-verified (same inputs -> same hash across runs; as_of exclusion makes it day-invariant)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sequential-await-on-same-session pattern for two-window composite: mirror of endgame_service.get_endgame_overview's internal sequential call chain"
    - "NaN-safe hash recipe: model_dump_json(exclude={...}) -> json.loads -> json.dumps(sort_keys=True, separators=(',', ':')) -> hashlib.sha256 hex digest"
    - "Dict value widening via explicit `dict[str, str]` annotation when inserting Literal-typed values (ty-invariant dict values)"
    - "D-06 sign-flip-at-call-site pattern for metrics where registry direction disagrees with raw formula semantics — preserves the raw value in the finding, flips only the assign_zone input"

key-files:
  created:
    - "app/services/insights_service.py (1036 lines)"
  modified: []

key-decisions:
  - "as_of populated via datetime.datetime.now(datetime.UTC) to match the Plan 03 schema (as_of: datetime.datetime). The plan text showed datetime.date.today().isoformat() -> str, but that produces a string which the schema rejects; honored the schema (authoritative per Plan 03 summary)."
  - "Weighted-mean rather than arithmetic mean for time_pressure_at_entry aggregations: avg_clock_diff_pct weighted by clock_games, net_timeout_rate weighted by total_endgame_games. This mirrors how ClockStatsRow defines the metrics per row."
  - "time_pressure_vs_performance emits one finding using avg_clock_diff_pct as metric with value=weighted mean of user scores across time-pressure buckets (0.0-1.0). is_headline_eligible=False until a dedicated metric lands in a follow-up phase (planner discretion per RESEARCH.md §Subsection Mapping)."
  - "Explicit `dict[str, str]` annotations at every dimension-dict literal site (bucket_dim, combo dim, endgame_class dim, conv_dim, recov_dim). Required because ty treats dict value types as invariant: without the annotation, `{'bucket': combo.platform}` infers `dict[str, Literal['chess.com', 'lichess']]` which is not assignable to `dict[str, str] | None` on SubsectionFinding.dimension."
  - "Flag-computation lookup uses only dimension=None findings (plus the full list for endgame_elo_timeline's per-combo scan). Bucketed rows in endgame_metrics are skipped from the by_key map — the endgame_skill flag reads the aggregate finding, not the per-bucket rows."

patterns-established:
  - "Every per-subsection builder returns either a single SubsectionFinding or a list — signature clarity for the caller (_compute_subsection_findings)."
  - "_empty_finding helper keeps the empty-window contract in one place: value=NaN, zone='typical', trend='n_a', sample_size=0, sample_quality='thin', is_headline_eligible=False."
  - "Sentry set_context on the compound try (covering both endgame_service calls) rather than per-call: the two awaits are effectively one operation, so the context captures whichever call raised."

requirements-completed:
  - FIND-01
  - FIND-03
  - FIND-04
  - FIND-05

# Metrics
duration: ~8min
completed: 2026-04-20
---

# Phase 63 Plan 04: compute_findings Service Summary

**Sole public entry point `compute_findings` implemented as a 1036-line pure-compute service that transforms two `EndgameOverviewResponse` composites (all_time + last_3mo) into a typed `EndgameTabFindings` with per-subsection findings, four cross-section flags, and a deterministic 64-char SHA256 `findings_hash`. Zero imports from `app.repositories`; two sequential awaits on the same AsyncSession; all thresholds come from `app.services.endgame_zones` constants.**

## Performance

- **Started:** 2026-04-20T19:26:07Z
- **Completed:** 2026-04-20T19:34:01Z
- **Duration:** ~8 min
- **Tasks:** 1 (service-only; tests land in Plan 63-05)
- **Files created:** 1 (`app/services/insights_service.py`)
- **Files modified:** 0

## Module Line Count and Surface

| Aspect               | Count / Value                                               |
| -------------------- | ----------------------------------------------------------- |
| Module lines         | 1036                                                        |
| Public functions     | 1 (`async def compute_findings`)                            |
| Private helpers      | 16                                                          |
| Imports from `app.repositories` | 0 (`grep -c "from app.repositories"` → 0)        |
| `asyncio.gather` uses           | 0 (`grep -c "asyncio.gather"` → 0)               |
| `get_endgame_overview` references | 9 (import + 2 call sites + 6 docstring mentions) |
| `recency=None` occurrences      | 2 (docstring + call site)                        |
| `recency="3months"` occurrences | 2 (docstring + call site)                        |

### Functions

```
Public:
  async def compute_findings(filter_context, session, user_id) -> EndgameTabFindings

Subsection builders (one per SubsectionId, 10 total):
  _compute_subsection_findings(response, window) -> list[SubsectionFinding]
    _finding_overall(response, window)
    _finding_score_gap_timeline(response, window)
    _findings_endgame_metrics(response, window)            # 1 skill + 9 bucket×metric
    _findings_endgame_elo_timeline(response, window)       # fan-out per (platform, tc) combo
    _findings_time_pressure_at_entry(response, window)     # 2 metrics: clock_diff + net_timeout
    _finding_clock_diff_timeline(response, window)
    _finding_time_pressure_vs_performance(response, window)
    _findings_results_by_endgame_type(response, window)    # per EndgameCategoryStats
    _findings_conversion_recovery_by_type(response, window) # per category × (conv, recov)
    _findings_type_win_rate_timeline(response, window)     # per endgame class, parent=results_by_endgame_type

Core helpers:
  _endgame_skill_from_material_rows(rows) -> float
  _compute_trend(points, min_weekly_points, min_slope_vol_ratio) -> tuple[Trend, int]
  _compute_flags(findings) -> list[FlagId]
  _compute_hash(findings) -> str
  _empty_finding(subsection_id, window, metric, parent=None, dimension=None)
```

## FIND-01 / FIND-03 / FIND-04 / FIND-05 Compliance

- **FIND-01 (service-only access):** verified by `grep -c "from app.repositories" app/services/insights_service.py` → 0. The only external data access is `from app.services.endgame_service import get_endgame_overview`. No router, no DB, no repo.
- **FIND-03 (four flags):** `_compute_flags` emits each flag deterministically from all_time findings. Thresholds reference `NEUTRAL_PCT_THRESHOLD` and `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` by name — no inline 10.0 or 100 literals at flag sites.
- **FIND-04 (trend gate):** `_compute_trend` applies BOTH the count gate (`n < TREND_MIN_WEEKLY_POINTS` → n_a) AND the ratio gate (`abs(slope)/stdev < TREND_MIN_SLOPE_VOL_RATIO` → n_a). Zero-stdev series collapse to `"stable"`. Otherwise slope sign picks `"improving"` / `"declining"`.
- **FIND-05 (stable hash):** `_compute_hash` uses the NaN-safe two-step recipe. Smoke-verified that the same findings with different `as_of` values produce the same 64-char hex digest.

## Two-Call-Not-Gather Pattern

```python
all_time_resp = await get_endgame_overview(..., recency=None, ...)
last_3mo_resp = await get_endgame_overview(..., recency="3months", ...)
```

Both awaits sit inside one `try:` block on the same `AsyncSession`. A single Sentry `set_context("insights", {"user_id": ..., "filter_context": ...})` + `capture_exception` wraps both calls — whichever raises, Sentry groups it under the same insights context.

## Net Timeout Rate Direction Resolution (D-06 / RESEARCH.md A1)

The registry declares `net_timeout_rate` with `direction="lower_is_better"` (CONTEXT.md D-06 verbatim). However, `ClockStatsRow.net_timeout_rate` formula is `(timeout_wins - timeout_losses) / total * 100` — positive when the user wins more flagging battles (good for the user).

**Resolution at the service call site, NOT the registry** (per Plan 01 A1 commitment):

```python
# D-06 resolution: the registry declares net_timeout_rate as
# `lower_is_better`, but ClockStatsRow.net_timeout_rate is
# (timeout_wins - timeout_losses) / total * 100 — positive when the user
# wins flag battles. We flip the sign before calling assign_zone so the
# zone matches the user's actual advantage under the locked
# lower_is_better semantic. Do NOT store the negated value — emit the
# original formula output in the finding so Phase 65 prompt-assembly
# sees the actual number, not its sign-flipped proxy.
net_timeout_zone_input = (
    -net_timeout_value if not math.isnan(net_timeout_value) else net_timeout_value
)
```

The finding's `value` field carries the raw formula output (unchanged); only the `assign_zone` input is sign-flipped. `grep -c "D-06 resolution"` → 1.

## Smoke-Test Results

Ran a live-Python smoke test against the helpers (not committed; Plan 05 owns formal test coverage):

| Check                                                     | Outcome                         |
| --------------------------------------------------------- | ------------------------------- |
| `_compute_trend([1.0]*10)` (count gate)                   | `("n_a", 10)` ✓                 |
| `_compute_trend([0.5]*25)` (zero-stdev stable)            | `("stable", 25)` ✓              |
| `_compute_trend(rising [0..24])` (slope 1 vs stdev 7.36)  | `("n_a", 25)` ✓ — ratio 0.14 < 0.5 gate by design |
| `_endgame_skill_from_material_rows([])`                   | `nan` ✓                         |
| `_endgame_skill_from_material_rows([conv 1.0, parity 0.5, recov 0.4])` | `0.6333...` ✓          |
| `_empty_finding(...)` zone / NaN / thin                   | all correct ✓                   |
| `_compute_flags([clock_diff=15])`                         | `["clock_entry_advantage"]` ✓   |
| `_compute_flags([clock_diff=5])`                          | `["no_clock_entry_advantage"]` ✓|
| `_compute_hash(ft)` length / hex                          | 64 lowercase hex chars ✓        |
| `_compute_hash` stable across different `as_of` values    | identical hash ✓                |
| `json.loads(ft.model_dump_json())` NaN round-trip         | `value: null` ✓ (no JSONDecodeError) |

## Verification

- `uv run ty check app/ tests/` → **All checks passed!** (project-wide, no regressions)
- `uv run ruff check .` → **All checks passed!** (project-wide)
- `uv run python -c "from app.services.insights_service import compute_findings"` → exits 0 (clean import)
- `uv run pytest tests/services/test_endgame_zones.py tests/test_insights_schema.py -x` → 49 passed (no regressions in Plan 01 / Plan 03 tests)

## Decisions Made

- **`as_of` uses `datetime.datetime.now(datetime.UTC)` (not `.isoformat()`).** Plan 03 (the authoritative schema) declares `as_of: datetime.datetime`; passing an ISO string would fail Pydantic validation. Plan 04's action text showed `datetime.date.today().isoformat()` — I honored the Plan 03 schema contract over the Plan 04 sample snippet (Plan 03 is the schema owner). The JSON wire shape is identical (ISO-8601 string emitted by Pydantic) because Phase 65 prompt-assembly never touches `as_of` (it is excluded from the hash anyway).
- **Weighted means for time_pressure_at_entry aggregations.** `avg_clock_diff_pct` aggregated from `ClockStatsRow` is the game-weighted mean `(user_avg_pct - opp_avg_pct)` across rows, weighted by `clock_games`. `net_timeout_rate` is the game-weighted mean across rows, weighted by `total_endgame_games` (its natural denominator per row). Rows missing clock data (`user_avg_pct is None`) are excluded from the clock_diff mean; rows with `total_endgame_games == 0` are excluded from net_timeout aggregation.
- **`time_pressure_vs_performance` emits a conservative placeholder finding.** Metric reuses `avg_clock_diff_pct` (registry keeps the `MetricId` namespace finite), value is the game-weighted mean user score across buckets (0.0-1.0). Always `is_headline_eligible=False` until a dedicated slope metric is added (planner discretion per RESEARCH.md §Subsection Mapping). This keeps the finding visible for Phase 65 sample-size gating without elevating it to a headline.
- **Explicit `dict[str, str]` annotations at every dimension-dict literal.** ty treats `dict[K, V]` value types as invariant; `{"bucket": row.bucket}` where `row.bucket: MaterialBucket` infers `dict[str, Literal["conversion", "parity", "recovery"]]` which is not assignable to `SubsectionFinding.dimension: dict[str, str] | None`. Annotating the local with `dict[str, str]` widens the value type at the dict literal. Applied to all five dimension-dict sites (bucket_dim, combo dim, endgame_class dim, conv_dim, recov_dim).

## Deviations from Plan

- **`as_of` type (Plan 04 sample snippet vs Plan 03 schema).** The Plan 04 action text showed `as_of=datetime.date.today().isoformat()`; I used `datetime.datetime.now(datetime.UTC)` because Plan 03's `EndgameTabFindings.as_of` is typed `datetime.datetime` (the executor prompt and PATTERNS.md also specify datetime). This is consistency with the committed schema, not a drift from Plan 04's intent.

Every acceptance-criterion grep passes:

| Grep pattern                                         | Expected         | Actual |
| ---------------------------------------------------- | ---------------- | ------ |
| `from app.repositories`                              | 0                | 0 ✓    |
| `asyncio.gather`                                     | 0                | 0 ✓    |
| `get_endgame_overview`                               | >= 3             | 9 ✓    |
| `recency=None` + `recency="3months"`                 | both appear      | both ✓ |
| `sentry_sdk.set_context("insights"`                  | >= 1             | 1 ✓    |
| `sentry_sdk.capture_exception`                       | >= 1             | 1 ✓    |
| `def _compute_trend`                                 | 1                | 1 ✓    |
| `statistics.linear_regression(xs, points)`           | 1                | 1 ✓    |
| `def _compute_flags`                                 | 1                | 1 ✓    |
| `NEUTRAL_PCT_THRESHOLD` OR `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD` | >= 2 | 5 ✓ |
| Four FlagId strings                                  | >= 4             | 8 ✓    |
| `model_dump_json(exclude=`                           | >= 1             | 2 ✓    |
| `json.loads`                                         | >= 1             | 3 ✓    |
| `json.dumps.*sort_keys=True`                         | >= 1             | 3 ✓    |
| `hashlib.sha256`                                     | >= 1             | 2 ✓    |
| `D-06 resolution`                                    | 1                | 1 ✓    |
| `_endgame_skill_from_material_rows` OR `endgame_skill` | >= 2           | 23 ✓   |

## Issues Encountered

- **ty dict-value invariance surprise.** Initial draft inserted `MaterialBucket`-typed values into `dict` literals without explicit type annotations; ty rejected because `dict[str, Literal["conversion", "parity", "recovery"]]` does not widen to `dict[str, str]`. Resolved by adding explicit `dict[str, str]` annotations on all five dimension-dict locals. Added comments at each site documenting the rationale.
- **Docstring wording triggered grep-based acceptance-criterion false positives.** Initial docstrings used the literal phrase "never `asyncio.gather`" which caused `grep -c "asyncio.gather"` to return 2 instead of 0. Reworded to "never concurrent gather" — same meaning, no literal match against the banned symbol.
- **Both issues caught before commit.** Ty check and acceptance-criterion grep suite both green before the single Task 1 commit landed.

## User Setup Required

None — backend-only pure-compute service. No DB migrations, no env vars, no external services.

## Next Wave Readiness

Plan 63-05 (tests for compute_findings) can start immediately:

- `app.services.insights_service.compute_findings` is importable and type-safe.
- Private helpers `_compute_trend`, `_compute_flags`, `_compute_hash`, `_endgame_skill_from_material_rows`, `_empty_finding` are all reachable for unit testing (module-private, but test files already live in `tests/` and can import directly).
- Smoke-verified behaviors (count gate, ratio gate, stable-on-zero-stdev, weighted-mean aggregation, NaN round-trip, hash stability across `as_of` values) give Plan 05 a tight target surface.
- `AsyncMock` + `patch("app.services.insights_service.get_endgame_overview")` is the recommended test seam for verifying the two-call pattern and call_count == 2 assertion per plan acceptance criteria.

No blockers or concerns.

## Self-Check

Verifying every claim in this SUMMARY:

- FOUND: app/services/insights_service.py (1036 lines, confirmed via wc -l)
- FOUND: commit 3728ebf in git log (feat(63-04): implement compute_findings endgame insights service)
- PASS: `uv run ty check app/ tests/` → All checks passed!
- PASS: `uv run ruff check .` → All checks passed!
- PASS: `uv run python -c "from app.services.insights_service import compute_findings"` → exits 0
- PASS: `grep -c "from app.repositories" app/services/insights_service.py` → 0
- PASS: `grep -c "asyncio.gather" app/services/insights_service.py` → 0
- PASS: `grep -c "get_endgame_overview" app/services/insights_service.py` → 9 (>= 3)
- PASS: `grep -c 'sentry_sdk.set_context("insights"' app/services/insights_service.py` → 1
- PASS: `grep -c "D-06 resolution" app/services/insights_service.py` → 1
- PASS: `grep -c "hashlib.sha256" app/services/insights_service.py` → 2 (>= 1)
- PASS: `uv run pytest tests/services/test_endgame_zones.py tests/test_insights_schema.py -x -q` → 49 passed (no regressions)

## Self-Check: PASSED

---
*Phase: 63-findings-pipeline-zone-wiring*
*Completed: 2026-04-20*
