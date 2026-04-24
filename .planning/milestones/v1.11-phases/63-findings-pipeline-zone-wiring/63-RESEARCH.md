# Phase 63: Findings Pipeline & Zone Wiring - Research

**Researched:** 2026-04-20
**Domain:** Python pure-compute service over existing Pydantic data shapes; zone registry; codegen; Pydantic v2 hash stability
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Python is the authoritative home for gauge thresholds. Create `app/services/endgame_zones.py` exporting `ZONE_REGISTRY: Mapping[MetricId, ZoneSpec]` plus `assign_zone(metric_id, value) -> Zone`. Frontend gauge components currently hold these values inline; Python becomes source of truth.

**D-02:** Add `scripts/gen_endgame_zones_ts.py` that emits `frontend/src/generated/endgameZones.ts` from the Python registry. The generated TS file IS committed. CI re-runs the generator and uses `git diff --exit-code` on the generated file to block drift. A separate Python test parses the inline constants in `EndgameScoreGapSection.tsx` and `EndgameClockPressureSection.tsx` and asserts they equal the registry values.

**D-03:** FE consumers keep current inline imports in Phase 63. Switching them to import from `frontend/src/generated/endgameZones.ts` is a follow-up task or Phase 66.

**D-04:** Scope of constants moved: numeric thresholds only. Color tokens stay in `frontend/src/lib/theme.ts`. New constant: `NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = 100`.

**D-05:** `Zone = Literal["weak", "typical", "strong"]`. Three zones, NOT five.

**D-06:** `ZoneSpec` frozen dataclass with `typical_lower`, `typical_upper`, `direction`. `assign_zone(metric_id, value) -> Zone`. Score Gap, Clock Diff, Conv/Parity/Recov, Endgame Skill = `higher_is_better`; Net Timeout Rate = `lower_is_better`.

**D-07:** Registry covers all 10 subsection-level metrics. Bucket-keyed Conv/Parity/Recov via `(metric_id, bucket)` — `BUCKETED_ZONE_REGISTRY` as separate mapping.

**D-08:** `assign_zone` accepts `MetricId | tuple[MetricId, MaterialBucket]` (or two overloads). Planner picks cleanest.

**D-09:** FOUR cross-section flags. `FlagId = Literal["baseline_lift_mutes_score_gap", "clock_entry_advantage", "no_clock_entry_advantage", "notable_endgame_elo_divergence"]`. Thresholds referencing registry constants.

**D-10:** Recovery typical band re-centered to `[0.25, 0.35]` (was `[0.30, 0.40]`). Only band change in Phase 63. Touches both Python registry AND `frontend/src/components/charts/EndgameScoreGapSection.tsx` `FIXED_GAUGE_ZONES.recovery`.

**D-11:** Other band tightenings (Score Gap, Clock Diff, Endgame Skill) are NOT in Phase 63 scope.

**D-12:** Flag rules locked per SEED-003. All comparison thresholds reference registry constants.

**D-13:** `SubsectionFinding` carries `parent_subsection_id: str | None` and `is_headline_eligible: bool`.

**D-14:** Endgame ELO fans out per `(platform, time_control)` combo via `dimension: dict[str, str] | None`.

**D-15:** Trend gate: `weekly_points_in_window >= TREND_MIN_WEEKLY_POINTS` (default 20) AND `slope_to_volatility_ratio >= TREND_MIN_SLOPE_VOL_RATIO` (default 0.5). Either failure -> `trend = "n_a"`.

**D-16:** Sample-quality bands per-subsection in registry: `SAMPLE_QUALITY_BANDS: dict[SubsectionId, tuple[int, int]]`.

### Claude's Discretion

- File layout details (exact module structure, export surface)
- `findings_hash` implementation path (pydantic vs json.dumps)
- Empty-window null-value convention (NaN vs 0.0)
- Bucket-aware Conv/Parity/Recov findings emitted via `dimension` field
- `assign_zone` overload style

### Deferred Ideas (OUT OF SCOPE)

- 5-zone schema
- Benchmark-recommended band tightenings (Score Gap, Clock Diff, Endgame Skill upper)
- FE gauge components consuming `frontend/src/generated/endgameZones.ts`
- `lookback_behavior` / `lookback_role` schema field
- Per-game / per-position insights
- Cache-hit logging policy (Phase 65 concern)
- Info-popover text migration to Python module (Phase 65 concern)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIND-01 | `insights_service.py` computes `SubsectionFinding` per subsection × window by consuming `endgame_service.get_overview(filter_context)` — no direct repository access | Two sequential `get_endgame_overview` calls (one per window); all data comes from `EndgameOverviewResponse` fields |
| FIND-02 | Zone assignment uses the existing in-code gauge constants as single source of truth; insights narrative and chart visuals MUST agree by construction | `endgame_zones.py` registry initialised from current TS constants (verified below); Recovery band updated per D-10 |
| FIND-03 | Four cross-section flags precomputed deterministically | Exact comparison expressions documented below; all thresholds reference registry constants |
| FIND-04 | Trend quality gate — `n_a` when weekly-points-in-window below threshold or slope-to-volatility ratio below threshold | `_compute_weekly_rolling_series` reuse pattern documented; slope via linear regression, volatility via std |
| FIND-05 | `findings_hash` is stable SHA256 of canonical-JSON-serialized `EndgameTabFindings` with `as_of` excluded and keys sorted | NaN serialisation pitfall identified; safe two-step recipe documented |
</phase_requirements>

---

## Summary

Phase 63 is a backend-only pure-compute phase. It creates three new modules and one codegen script, calls the existing `endgame_service.get_endgame_overview` twice (once per window), transforms the composite `EndgameOverviewResponse` into a typed `EndgameTabFindings` object, and guards against future drift between Python and TypeScript constants via a codegen-and-commit pattern plus a consistency parsing test.

No new database tables, no new router endpoints, and no new frontend behaviour beyond a one-line Recovery-band edit in `EndgameScoreGapSection.tsx`. The phase is self-contained and has no v1.11 prerequisites — it consumes only existing v1.10 services.

The most subtle aspects are: (a) the two-call pattern needed to produce both windows, (b) the NaN serialisation trap when computing `findings_hash` (documented below with a verified fix), and (c) Pydantic v2's non-sorted key emission in `model_dump_json`, which means `findings_hash` must use the two-step `model_dump_json` → `json.loads` → `json.dumps(sort_keys=True)` approach.

**Primary recommendation:** Implement `endgame_zones.py` first (pure Python, no async), then `insights.py` schemas, then `insights_service.py` compute, then the codegen script, then the consistency test, then the unit tests. Each step is independently verifiable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Zone registry (thresholds) | API / Backend (`endgame_zones.py`) | CDN / Static (via codegen to `endgameZones.ts`) | Python is the source of truth per D-01; TS copy is generated |
| Findings computation | API / Backend (`insights_service.py`) | — | Pure Python over Pydantic data; no DB access |
| `findings_hash` | API / Backend (inside `insights_service.py`) | — | Deterministic SHA256, backend-only concern |
| Zone → TS codegen | Build tooling (`scripts/gen_endgame_zones_ts.py`) | CI step | One-way data flow: Python → generated TS file |
| FE gauge constant consumers | Browser / Client (unchanged in Phase 63) | — | Deferred to Phase 66 per D-03 |
| Recovery band edit | Browser / Client (`EndgameScoreGapSection.tsx`) + Backend | — | D-10: both sides updated simultaneously, consistency test enforces |

---

## Standard Stack

### Core (already in lockfile — no new dependencies needed for Phase 63)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Schemas (`insights.py`) | Project standard; v2 throughout |
| fastapi | 0.135.1 | Framework (routers) | Project standard |
| sqlalchemy (asyncio) | 2.0.48 | AsyncSession passed into compute entry point | Project standard |
| Python stdlib `hashlib` | 3.13.x | SHA256 for `findings_hash` | No extra dep needed |
| Python stdlib `json` | 3.13.x | `json.dumps(sort_keys=True)` for hash stability | No extra dep needed |
| Python stdlib `dataclasses` | 3.13.x | `ZoneSpec` frozen dataclass | No extra dep needed |
| Python stdlib `math` | 3.13.x | `math.isnan()` guard in zone assignment | No extra dep needed |

**Note on numpy/scipy:** Trend computation uses `statistics.linear_regression` (stdlib, Python 3.10+) for slope — no numpy required. `statistics.stdev` for volatility. This avoids a new dependency while producing deterministic output.

[VERIFIED: pyproject.toml — no scipy/numpy in current deps; using stdlib is correct]

**Installation:** No new packages needed.

---

## File Layout & Module Structure

### Files to Create

```
app/services/endgame_zones.py            # Zone registry, ZoneSpec, assign_zone, sample-quality bands
app/schemas/insights.py                  # Pydantic schemas: all Literals + SubsectionFinding + EndgameTabFindings
app/services/insights_service.py         # compute_findings(filter_context, session, user_id) -> EndgameTabFindings
scripts/gen_endgame_zones_ts.py          # Reads registry, emits frontend/src/generated/endgameZones.ts
frontend/src/generated/endgameZones.ts   # Generated file — committed, CI-diff-guarded
tests/services/test_insights_service.py  # Unit tests: zone assign, flags, trend, hash stability
tests/services/test_endgame_zones_consistency.py  # Regex-parse TS sources, assert registry parity
```

### Files to Edit

```
frontend/src/components/charts/EndgameScoreGapSection.tsx
  # Line 90-94: change FIXED_GAUGE_ZONES.recovery from [0.30, 0.40] to [0.25, 0.35]
  # (D-10 Recovery re-center — single-line edit in the nested zone array)
.github/workflows/ci.yml
  # Add "Zone drift check" step after "Install Python dependencies" step
```

### `app/services/endgame_zones.py` Export Surface

```python
# Types
MetricId          # Literal type alias
MaterialBucket    # re-exported from endgames schema (or re-declared)
SubsectionId      # Literal type alias
ZoneSpec          # frozen dataclass
Zone              # Literal["weak", "typical", "strong"]
Trend             # Literal["improving", "declining", "stable", "n_a"]
SampleQuality     # Literal["thin", "adequate", "rich"]
Window            # Literal["all_time", "last_3mo"]

# Constants
ZONE_REGISTRY               # Mapping[MetricId, ZoneSpec] — scalar metrics
BUCKETED_ZONE_REGISTRY      # Mapping[MetricId, Mapping[MaterialBucket, ZoneSpec]]
SAMPLE_QUALITY_BANDS        # dict[SubsectionId, tuple[int, int]]
TREND_MIN_WEEKLY_POINTS     # int = 20
TREND_MIN_SLOPE_VOL_RATIO   # float = 0.5
NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD  # int = 100
NEUTRAL_PCT_THRESHOLD       # float = 10  (re-exported from FE inline constant)
NEUTRAL_TIMEOUT_THRESHOLD   # float = 5   (re-exported from FE inline constant)

# Functions
assign_zone(metric_id: MetricId, value: float) -> Zone
assign_bucketed_zone(metric_id: MetricId, bucket: MaterialBucket, value: float) -> Zone
```

### `app/schemas/insights.py` Export Surface

```python
# All Literal type aliases (re-export Zone/Trend/SampleQuality/Window from endgame_zones)
FlagId      # Literal["baseline_lift_mutes_score_gap", "clock_entry_advantage",
            #          "no_clock_entry_advantage", "notable_endgame_elo_divergence"]
SectionId   # Literal["overall", "metrics_elo", "time_pressure", "type_breakdown"]

# Pydantic models
FilterContext       # mirrors get_endgame_overview parameter surface
SubsectionFinding  # per-subsection-per-window finding
EndgameTabFindings # top-level output with findings list, flags list, hash, as_of
```

### `app/services/insights_service.py` Export Surface

```python
# Single public entry point
async def compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
) -> EndgameTabFindings:
    ...
```

---

## Zone Registry Data Model

### `ZoneSpec` Frozen Dataclass [VERIFIED: CLAUDE.md §Coding Guidelines]

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class ZoneSpec:
    typical_lower: float
    typical_upper: float
    direction: Literal["higher_is_better", "lower_is_better"]
```

### `MetricId` Literal [VERIFIED: CONTEXT.md §Specifics]

```python
MetricId = Literal[
    "score_gap",
    "endgame_skill",
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    "endgame_elo_gap",
]
```

### `SubsectionId` Literal [VERIFIED: SEED-003 §Sections in Scope + CONTEXT.md §Specifics]

```python
SubsectionId = Literal[
    "overall",
    "score_gap_timeline",
    "endgame_metrics",
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    "results_by_endgame_type",
    "conversion_recovery_by_type",
    "type_win_rate_timeline",
]
```

### Current Frontend Constants (Source of Truth for Initial Registry)

Read from source files on 2026-04-20:

**From `EndgameScoreGapSection.tsx` lines 79-105:**
[VERIFIED: direct file read]

```
FIXED_GAUGE_ZONES.conversion:
  danger: [0, 0.65)
  neutral (typical): [0.65, 0.75]
  success: (0.75, 1.0]

FIXED_GAUGE_ZONES.parity:
  danger: [0, 0.45)
  neutral (typical): [0.45, 0.55]
  success: (0.55, 1.0]

FIXED_GAUGE_ZONES.recovery (CURRENT — pre D-10 edit):
  danger: [0, 0.30)
  neutral (typical): [0.30, 0.40]
  success: (0.40, 1.0]
  -> D-10 changes this to [0.25, 0.35] in BOTH the TS file and the Python registry

ENDGAME_SKILL_ZONES:
  danger: [0, 0.45)
  neutral (typical): [0.45, 0.55]
  success: (0.55, 1.0]
```

**From `EndgameClockPressureSection.tsx` lines 18, 23:**
[VERIFIED: direct file read]

```
NEUTRAL_PCT_THRESHOLD = 10      (percentage of base clock time)
NEUTRAL_TIMEOUT_THRESHOLD = 5   (percentage points)
```

**From `EndgamePerformanceSection.tsx` lines 36-46:**
[VERIFIED: direct file read]

```
SCORE_GAP_NEUTRAL_MIN = -0.10   (0.0-1.0 scale, i.e. -10pp)
SCORE_GAP_NEUTRAL_MAX = +0.10   (0.0-1.0 scale, i.e. +10pp)
SCORE_GAP_TIMELINE_NEUTRAL_PCT = 10  (shown in percentage points, same threshold)
```

### Initial `ZONE_REGISTRY` Contents

```python
ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] = {
    # Score Gap: signed 0.0-1.0 scale (e.g. 0.05 = +5pp endgame advantage)
    # Typical = ±10pp = [-0.10, +0.10]
    "score_gap": ZoneSpec(
        typical_lower=-0.10,
        typical_upper=0.10,
        direction="higher_is_better",
    ),
    # Endgame Skill: simple average of Conv/Parity/Recov rates (0.0-1.0)
    "endgame_skill": ZoneSpec(
        typical_lower=0.45,
        typical_upper=0.55,
        direction="higher_is_better",
    ),
    # Clock diff at endgame entry (% of base time, signed)
    # Typical = ±10% of base time
    "avg_clock_diff_pct": ZoneSpec(
        typical_lower=-10.0,
        typical_upper=10.0,
        direction="higher_is_better",
    ),
    # Net timeout rate (percentage points, signed)
    # Typical = ±5pp — lower_is_better means
    # positive net_timeout_rate (user flags opponent more) is good
    # but convention: flag raises are bad for user, so use abs comparison
    # NOTE: see assign_zone implementation notes below
    "net_timeout_rate": ZoneSpec(
        typical_lower=-5.0,
        typical_upper=5.0,
        direction="lower_is_better",
    ),
    # Endgame ELO gap (endgame_elo - actual_elo, integer Elo)
    # No fixed zone for this — fanned out per combo, zone computed from |gap|
    # The NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = 100 is a flag threshold,
    # not a zone boundary. Zone assignment for ELO gap uses |gap|.
    "endgame_elo_gap": ZoneSpec(
        typical_lower=-100.0,
        typical_upper=100.0,
        direction="higher_is_better",
    ),
}

# Per-bucket entries — looked up via assign_bucketed_zone(metric_id, bucket, value)
BUCKETED_ZONE_REGISTRY: Mapping[
    Literal["conversion_win_pct", "parity_score_pct", "recovery_save_pct"],
    Mapping[MaterialBucket, ZoneSpec],
] = {
    "conversion_win_pct": {
        "conversion": ZoneSpec(0.65, 0.75, "higher_is_better"),
        "parity":     ZoneSpec(0.65, 0.75, "higher_is_better"),  # same band used; bucket semantics differ
        "recovery":   ZoneSpec(0.65, 0.75, "higher_is_better"),  # same band
    },
    "parity_score_pct": {
        "conversion": ZoneSpec(0.45, 0.55, "higher_is_better"),
        "parity":     ZoneSpec(0.45, 0.55, "higher_is_better"),
        "recovery":   ZoneSpec(0.45, 0.55, "higher_is_better"),
    },
    "recovery_save_pct": {
        "conversion": ZoneSpec(0.25, 0.35, "higher_is_better"),  # D-10 re-center
        "parity":     ZoneSpec(0.25, 0.35, "higher_is_better"),  # D-10 re-center
        "recovery":   ZoneSpec(0.25, 0.35, "higher_is_better"),  # D-10 re-center
    },
}
```

**Important clarification on bucketed metrics:** The frontend `FIXED_GAUGE_ZONES` is keyed by `MaterialBucket` (conversion / parity / recovery). Each bucket has one set of zone bands. In `endgame_metrics`, the findings service emits one `SubsectionFinding` per `(material_bucket, metric)` combination — roughly 9 entries (3 buckets × 3 rate-metrics) plus 1 for `endgame_skill`. The `dimension` field carries `{"bucket": "conversion"}` etc.

**Clarification on metric values vs schema field units:** [VERIFIED: direct schema + FE code read]

- `conversion_win_pct`: from `MaterialRow.win_pct / 100` (schema stores 0-100, FE uses `win_pct / 100`) — range 0.0-1.0
- `parity_score_pct`: from `MaterialRow.score` (schema `score = (win_pct + draw_pct/2) / 100`) — range 0.0-1.0
- `recovery_save_pct`: from `(MaterialRow.win_pct + MaterialRow.draw_pct) / 100` — range 0.0-1.0 (i.e. FE uses `(row.win_pct + row.draw_pct) / 100`)
- `endgame_skill`: computed as arithmetic mean of non-empty bucket rates (mirrors `_endgame_skill_from_bucket_rows` / FE `endgameSkill()`) — range 0.0-1.0
- `score_gap`: `ScoreGapMaterialResponse.score_difference` (already 0.0-1.0 scale signed) — range approx -0.5 to +0.5
- `avg_clock_diff_pct`: `ClockStatsRow.avg_clock_diff_seconds / base_time * 100` or `ClockPressureTimelinePoint.avg_clock_diff_pct` (already in %) — signed
- `net_timeout_rate`: `ClockStatsRow.net_timeout_rate` (already in pp, signed) — range typically -20 to +20
- `endgame_elo_gap`: `EndgameEloTimelinePoint.endgame_elo - EndgameEloTimelinePoint.actual_elo` (signed Elo integer)

---

## Architecture Patterns

### System Architecture Diagram

```
FilterContext (from Phase 65 request body)
        |
        v
compute_findings(filter_context, session, user_id)
        |
        +-- get_endgame_overview(session, user_id, recency=None, ...)       [all_time window]
        |           |
        |           v
        |   EndgameOverviewResponse  -------+
        |                                   |
        +-- get_endgame_overview(session,    |
        |   user_id, recency="3months", ...) |  [last_3mo window]
        |           |                       |
        |           v                       |
        |   EndgameOverviewResponse  -------+
        |                                   |
        v                                   v
_extract_per_subsection_findings(all_time_resp, last_3mo_resp)
        |
        +-- for each SubsectionId × Window:
        |       - read metric value from response
        |       - assign_zone(metric_id, value) or assign_bucketed_zone(...)
        |       - compute trend (slope/vol from timeline series)
        |       - assign sample_quality from SAMPLE_QUALITY_BANDS
        |       -> SubsectionFinding
        |
        +-- _compute_flags(all_time_findings) -> list[FlagId]
        |
        v
EndgameTabFindings(
    as_of=today_iso,
    filters=filter_context,
    findings=[SubsectionFinding, ...],
    flags=[FlagId, ...],
    findings_hash=_compute_hash(...)
)
```

### Recommended Project Structure

```
app/services/
├── endgame_zones.py      # NEW — registry + assign_zone (no async, pure Python)
├── insights_service.py   # NEW — compute_findings (async, calls endgame_service)
├── endgame_service.py    # EXISTING — untouched (read-only input)
app/schemas/
├── insights.py           # NEW — FilterContext, SubsectionFinding, EndgameTabFindings
├── endgames.py           # EXISTING — untouched (read from)
scripts/
├── gen_endgame_zones_ts.py  # NEW — codegen script
frontend/src/generated/
├── endgameZones.ts          # NEW (generated) — committed to git
tests/services/
├── test_insights_service.py           # NEW
├── test_endgame_zones_consistency.py  # NEW
```

### `assign_zone` Signature and Behavior

**Recommendation: two separate functions** (cleaner for `ty` than union overloads):

```python
def assign_zone(metric_id: MetricId, value: float) -> Zone:
    """Assign a zone for a scalar metric.

    Raises KeyError if metric_id is not in ZONE_REGISTRY (programming error).
    Returns "typical" when value is NaN (math.isnan) — callers set
    is_headline_eligible=False independently when value is missing.
    """
    if math.isnan(value):
        return "typical"
    spec = ZONE_REGISTRY[metric_id]
    return _zone_from_spec(spec, value)


def assign_bucketed_zone(
    metric_id: Literal["conversion_win_pct", "parity_score_pct", "recovery_save_pct"],
    bucket: MaterialBucket,
    value: float,
) -> Zone:
    """Assign a zone for a per-bucket metric."""
    if math.isnan(value):
        return "typical"
    spec = BUCKETED_ZONE_REGISTRY[metric_id][bucket]
    return _zone_from_spec(spec, value)


def _zone_from_spec(spec: ZoneSpec, value: float) -> Zone:
    if spec.direction == "higher_is_better":
        if value >= spec.typical_upper:
            return "strong"
        if value >= spec.typical_lower:
            return "typical"
        return "weak"
    else:  # lower_is_better
        if value <= spec.typical_lower:
            return "strong"
        if value <= spec.typical_upper:
            return "typical"
        return "weak"
```

**Direction inversion for `lower_is_better`:** Net timeout rate uses `lower_is_better`. The registry has `typical_lower=-5.0, typical_upper=5.0`. Under `lower_is_better`: value <= typical_lower (-5) → strong (user outperforms); value <= typical_upper (5) → typical; value > typical_upper → weak. This is consistent with the semantic: a positive net_timeout_rate means opponent flags more often (user advantage), so high positive is "strong". Wait — this requires clarification:

**Net timeout rate semantics:** `net_timeout_rate = (timeout_wins - timeout_losses) / total * 100`. Positive = user wins more flagging battles = advantage for user. Therefore `higher_is_better` is actually correct for net_timeout_rate too. The FE uses `±5pp` as a neutral band. Both directions should use `higher_is_better`; only the band bounds matter.

**Revised:** `net_timeout_rate` should use `direction="higher_is_better"` with `typical_lower=-5.0, typical_upper=5.0`. The CONTEXT.md says "Net Timeout Rate = `lower_is_better`" which appears to be based on net_timeout_rate as "how much you time out more than opponent" (where lower = fewer timeouts = better). Check the actual formula in ClockStatsRow: `(timeout_wins - timeout_losses) / total_endgame_games * 100`. Positive = user wins more flagging battles. Planner should confirm direction with the user at plan-review, flagged as `[ASSUMED]`.

**Edge cases:**
- NaN value: returns `"typical"` — the `is_headline_eligible=False` flag signals the missing-data condition to callers
- Value exactly on boundary: >= typical_lower → typical (lower boundary is inclusive for "typical"); >= typical_upper → strong (upper boundary is inclusive for "strong")

---

## `compute_findings` Algorithm

### Two-Call Pattern [VERIFIED: endgame_service.py, SEED-003]

`get_endgame_overview` takes a `recency` string parameter. It does NOT return both windows in a single call. The findings service must make two sequential calls:

```python
async def compute_findings(
    filter_context: FilterContext,
    session: AsyncSession,
    user_id: int,
) -> EndgameTabFindings:
    # Call 1: all_time window (recency=None)
    all_time_resp = await get_endgame_overview(
        session=session,
        user_id=user_id,
        time_control=filter_context.time_controls or None,
        platform=filter_context.platforms or None,
        rated=filter_context.rated_only if filter_context.rated_only else None,
        opponent_type="human",
        recency=None,
        opponent_strength=filter_context.opponent_strength,
    )

    # Call 2: last_3mo window (recency="3months")
    last_3mo_resp = await get_endgame_overview(
        session=session,
        user_id=user_id,
        time_control=filter_context.time_controls or None,
        platform=filter_context.platforms or None,
        rated=filter_context.rated_only if filter_context.rated_only else None,
        opponent_type="human",
        recency="3months",
        opponent_strength=filter_context.opponent_strength,
    )
    ...
```

**Sequential calls:** Both calls use the same `AsyncSession` — no `asyncio.gather` per CLAUDE.md critical constraint. The sequential nature is correct and cheap (endgame_service is already doing all the heavy work per call).

**`FilterContext` parameter mapping:** [VERIFIED: endgame router + openings_service.py]

| `FilterContext` field | `get_endgame_overview` parameter | Notes |
|---|---|---|
| `recency` | `recency` | "all_time" → None, "3months" → "3months" |
| `opponent_strength` | `opponent_strength` | direct pass |
| `time_controls` | `time_control` | list[str] or None |
| `platforms` | `platform` | list[str] or None |
| `rated_only` | `rated` | bool or None |
| `color` | NOT passed to endgame service | endgame service has no color filter |
| — | `opponent_type` | hardcoded `"human"` |

**Note on `opponent_type`:** The endgame router always defaults `opponent_type="human"` (from query param default). `FilterContext` does not carry this — it's an implicit constant in `compute_findings`. The CONTEXT.md shows `FilterContext` mirrors `apply_game_filters` arg surface, and the current endgame service uses `opponent_type: str = "human"` as default. [VERIFIED: endgame router line 36]

**Note on `color`:** `FilterContext.color` is included in the schema (per CONTEXT.md D-14/INS-03) but NOT passed to `get_endgame_overview` because the endgame service has no color filter parameter. This is correct per INS-03 ("color ... do NOT materially reshape the cross-section story").

### Subsection → `EndgameOverviewResponse` Field Mapping

[VERIFIED: endgame_service.py, endgames.py schemas, SEED-003 §Sections in Scope]

| SubsectionId | Source field on `EndgameOverviewResponse` | Primary metric(s) | Sample size |
|---|---|---|---|
| `overall` | `performance.endgame_wdl` + `performance.non_endgame_wdl` | `score_gap` = `score_gap_material.score_difference` | `performance.endgame_wdl.total + performance.non_endgame_wdl.total` |
| `score_gap_timeline` | `score_gap_material.timeline` | `score_gap` (trend over time) | `len(score_gap_material.timeline)` weekly points |
| `endgame_metrics` | `score_gap_material.material_rows` | `conversion_win_pct`, `parity_score_pct`, `recovery_save_pct`, `endgame_skill` | sum of `MaterialRow.games` per bucket |
| `endgame_elo_timeline` | `endgame_elo_timeline.combos` | `endgame_elo_gap` per combo | `EndgameEloTimelineCombo.points` length |
| `time_pressure_at_entry` | `clock_pressure.rows` | `avg_clock_diff_pct`, `net_timeout_rate` | `clock_pressure.total_clock_games` |
| `clock_diff_timeline` | `clock_pressure.timeline` | `avg_clock_diff_pct` (trend over time) | `len(clock_pressure.timeline)` weekly points |
| `time_pressure_vs_performance` | `time_pressure_chart.user_series`, `.opp_series` | time-pressure performance slope | `time_pressure_chart.total_endgame_games` |
| `results_by_endgame_type` | `stats.categories` | win_pct per endgame class | `EndgameCategoryStats.total` per type |
| `conversion_recovery_by_type` | `stats.categories[i].conversion.*` | per-type conversion + recovery rates | per-type game counts |
| `type_win_rate_timeline` | `timeline.per_type` | win_rate trend per endgame class | timeline point count per type |

**Headline-eligibility rules per SEED-003:**
- `score_gap_timeline`: headline-eligible only when trend-quality gate passes
- `clock_diff_timeline`: headline-eligible only when trend-quality gate passes
- `type_win_rate_timeline`: never headline-eligible (supporting only; `parent_subsection_id = "results_by_endgame_type"`)
- All others: default `is_headline_eligible=True` when sample_quality is not "thin"

**`endgame_elo_gap` per-combo `score_gap` calculation:**
The `endgame_elo_gap` metric value for one combo = most recent point's `endgame_elo - actual_elo`. This is the "current state" value. Use the last point of `EndgameEloTimelineCombo.points` (sorted by date ASC, so `points[-1]`). If `points` is empty, skip that combo (combos with zero qualifying points are already dropped from the response per schema docstring).

---

## Trend Computation

### Reusing `_compute_weekly_rolling_series` [VERIFIED: endgame_service.py line 1556]

The existing function signature:
```python
def _compute_weekly_rolling_series(
    rows: list[Row[Any]],
    window: int,
) -> list[dict]:  # dicts with keys: date, win_rate, game_count, per_week_game_count
```

This function takes raw `(played_at, result, user_color)` game rows, not pre-computed timeline points. The findings service operates on the **already-computed timeline data** from `EndgameOverviewResponse` — it does NOT have access to the raw rows.

**Consequence:** For timeline subsections (`score_gap_timeline`, `clock_diff_timeline`, `type_win_rate_timeline`), the findings service uses the pre-computed timeline points from the response, NOT a second call to `_compute_weekly_rolling_series`. The trend computation is:

```python
def _compute_trend(
    points: list[float],  # time-ordered metric values (one per weekly point)
    min_weekly_points: int = TREND_MIN_WEEKLY_POINTS,
    min_slope_vol_ratio: float = TREND_MIN_SLOPE_VOL_RATIO,
) -> tuple[Trend, int]:  # (trend, weekly_points_in_window)
    n = len(points)
    if n < min_weekly_points:
        return "n_a", n
    if n < 2:
        return "n_a", n

    import statistics
    xs = list(range(n))
    slope, _ = statistics.linear_regression(xs, points)
    stdev = statistics.stdev(points)

    if stdev == 0.0:
        # All values identical — technically stable with infinite ratio
        return "stable", n

    ratio = abs(slope) / stdev
    if ratio < min_slope_vol_ratio:
        return "n_a", n

    return ("improving" if slope > 0 else "declining"), n
```

**`weekly_points_in_window` for both windows:**
- `all_time`: number of weekly points in the all_time timeline (can be 0..hundreds)
- `last_3mo`: ~13 weekly points maximum (90 days / 7 ≈ 12.86). This is BELOW the default `TREND_MIN_WEEKLY_POINTS = 20`. Therefore `trend` will always be `"n_a"` for `last_3mo` by construction. This is correct per CONTEXT.md §Specifics — trend is an `all_time`-window concern; `last_3mo` provides "recent state" (zone value), not trend direction.

**Formula:** `slope_to_volatility_ratio = abs(linregress_slope) / stdev(values)`. Uses Python 3.10+ `statistics.linear_regression` (no numpy needed). [ASSUMED: adequate numeric stability for this use case]

**Stability guarantee:** `statistics.linear_regression` and `statistics.stdev` are deterministic — no random initialization, no floating-point non-determinism beyond float arithmetic.

---

## Cross-Section Flags

All four flags are computed over the `all_time` window findings (the authoritative set).

```python
def _compute_flags(findings: list[SubsectionFinding]) -> list[FlagId]:
    """Compute four cross-section flags from all_time findings.

    All comparison thresholds reference registry constants — no inline literals.
    """
    # Build lookup: (subsection_id, window, metric_id) -> SubsectionFinding
    by_key: dict[tuple[SubsectionId, Window, MetricId], SubsectionFinding] = {
        (f.subsection_id, f.window, f.metric): f
        for f in findings
        if f.window == "all_time"
    }

    flags: list[FlagId] = []

    # Flag 1: baseline_lift_mutes_score_gap
    # endgame_skill.zone == "strong" AND score_gap.zone in {"typical", "weak"}
    skill_f = by_key.get(("endgame_metrics", "all_time", "endgame_skill"))
    sg_f = by_key.get(("overall", "all_time", "score_gap"))
    if (
        skill_f is not None
        and sg_f is not None
        and skill_f.zone == "strong"
        and sg_f.zone in ("typical", "weak")
    ):
        flags.append("baseline_lift_mutes_score_gap")

    # Flag 2: clock_entry_advantage
    # avg_clock_diff_pct > NEUTRAL_PCT_THRESHOLD
    clock_f = by_key.get(("time_pressure_at_entry", "all_time", "avg_clock_diff_pct"))
    if (
        clock_f is not None
        and not math.isnan(clock_f.value)
        and clock_f.value > NEUTRAL_PCT_THRESHOLD
    ):
        flags.append("clock_entry_advantage")

    # Flag 3: no_clock_entry_advantage
    # abs(avg_clock_diff_pct) <= NEUTRAL_PCT_THRESHOLD
    if (
        clock_f is not None
        and not math.isnan(clock_f.value)
        and abs(clock_f.value) <= NEUTRAL_PCT_THRESHOLD
    ):
        flags.append("no_clock_entry_advantage")

    # Flag 4: notable_endgame_elo_divergence
    # max over (platform, tc) combos of abs(endgame_elo_gap) > NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD
    elo_findings = [
        f for f in findings
        if f.subsection_id == "endgame_elo_timeline"
        and f.window == "all_time"
        and f.metric == "endgame_elo_gap"
        and not math.isnan(f.value)
    ]
    if any(
        abs(f.value) > NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD
        for f in elo_findings
    ):
        flags.append("notable_endgame_elo_divergence")

    return flags
```

**Note on flags 2 and 3:** They are mutually exclusive by arithmetic: a value cannot simultaneously be > 10 AND have abs <= 10. The only case where neither fires is when `clock_f` is None (no clock data). This is intentional.

---

## `findings_hash` Implementation

### NaN Pitfall — CRITICAL [VERIFIED: live Python 3.13 test]

Pydantic v2 `model_dump_json()` serialises `float('nan')` as JSON `null`. BUT `model_dump(mode='json')` returns Python `float('nan')` unchanged, and `json.dumps({'v': float('nan')})` produces the invalid JSON string `{"v": NaN}` which `json.loads` cannot round-trip.

**Safe recipe:**

```python
import hashlib, json

def _compute_hash(findings: EndgameTabFindings) -> str:
    # Step 1: Pydantic v2 model_dump_json handles NaN -> null, datetime -> str, etc.
    #         But it does NOT sort keys — nested dicts use field-declaration order.
    json_str = findings.model_dump_json(exclude={"findings_hash", "as_of"})

    # Step 2: Re-parse to Python dict, then re-serialize with sorted keys.
    #         This eliminates any ordering non-determinism in nested dicts
    #         (e.g., EndgameEloTimelineCombo dimension dicts).
    parsed = json.loads(json_str)  # NaN is already null here — safe
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(canonical.encode()).hexdigest()
```

**Why NOT `model_dump(mode='json') + json.dumps(sort_keys=True)`:**
`model_dump(mode='json')` returns Python `float('nan')` (not `None`) and `json.dumps` will output `NaN` (invalid JSON) or raise `ValueError` depending on settings. The `model_dump_json()` first-pass is essential for correct NaN handling.

[VERIFIED: live test — `model_dump(mode='json')` returns `float('nan')` unchanged; `model_dump_json()` returns `"null"`]

**Float representation stability:** Python's `repr(0.32)` and `json.dumps(0.32)` are stable across Python 3.x versions — floating-point uses IEEE 754 and the `Grisu3` algorithm. Registry constants like `0.25`, `0.35`, `0.65`, `0.75` are exact float representations. [VERIFIED: live test showing exact round-trip for all registry values]

**Pydantic v2 key ordering:** `model_dump_json()` emits fields in declaration order (NOT alphabetically sorted). [VERIFIED: live test — `Inner(b=2.0, a=1.0)` emits `{"b":2.0,"a":1.0}`, not sorted.] The `json.loads` + `json.dumps(sort_keys=True)` step handles this.

**Hash format:** Full SHA256 hex digest (64 characters). Do not truncate — Phase 65 uses it as a cache key and Phase 67 as a regression anchor.

**`as_of` exclusion:** `as_of` is the ISO date of the computation. Excluding it means the same findings on different days cache-hit, preventing daily cache churn (per FIND-05).

**`findings_hash` field on schema:** The field is populated after the rest of the `EndgameTabFindings` is computed. The field is excluded from its own hash computation via the `exclude={"findings_hash", "as_of"}` parameter.

---

## Codegen Script

### `scripts/gen_endgame_zones_ts.py`

```python
#!/usr/bin/env python3
"""
Generate frontend/src/generated/endgameZones.ts from the Python zone registry.

Run manually:
    uv run python scripts/gen_endgame_zones_ts.py

Run in CI (drift check):
    uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts
"""
import sys
from pathlib import Path

# Must import the registry from app module — requires running inside uv env
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.endgame_zones import (
    ZONE_REGISTRY,
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD,
)

OUTPUT = Path(__file__).parent.parent / "frontend/src/generated/endgameZones.ts"

# ... emit the TS file
```

**Generated TS file structure:** The file emits constants matching the names currently used in the FE inline constants, so future consumer switchover is a find-and-replace import:

```typescript
// AUTO-GENERATED — do not edit. Source: app/services/endgame_zones.py
// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py

export type MaterialBucket = "conversion" | "parity" | "recovery";
export interface GaugeZone { from: number; to: number; }

export const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {
  conversion: [
    { from: 0, to: 0.65 },
    { from: 0.65, to: 0.75 },
    { from: 0.75, to: 1.0 },
  ],
  parity: [
    { from: 0, to: 0.45 },
    { from: 0.45, to: 0.55 },
    { from: 0.55, to: 1.0 },
  ],
  recovery: [
    { from: 0, to: 0.25 },     // D-10 re-center
    { from: 0.25, to: 0.35 },  // D-10 re-center
    { from: 0.35, to: 1.0 },
  ],
};

export const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0, to: 0.45 },
  { from: 0.45, to: 0.55 },
  { from: 0.55, to: 1.0 },
];

export const NEUTRAL_PCT_THRESHOLD = 10;
export const NEUTRAL_TIMEOUT_THRESHOLD = 5;
export const SCORE_GAP_NEUTRAL_MIN = -0.10;
export const SCORE_GAP_NEUTRAL_MAX = 0.10;
export const NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = 100;
```

**Note:** The TS file does NOT include `color` (kept in `theme.ts`) per D-04.

### CI Wiring

Insert a new step in `.github/workflows/ci.yml` immediately after "Install Python dependencies":

```yaml
- name: Zone drift check
  run: |
    uv run python scripts/gen_endgame_zones_ts.py
    git diff --exit-code frontend/src/generated/endgameZones.ts
```

This step runs in the `test` job, before `Lint (ruff)`. The Python environment (`uv sync --locked`) is already installed by this point. The step imports `app.services.endgame_zones` — no special env vars needed since it's pure computation.

**Why before linting:** If the generated file has drifted, we want a clear drift-failure message before ruff errors obscure it. The step is also cheap (< 1s).

---

## FE-Drift Consistency Test

### `tests/services/test_endgame_zones_consistency.py`

Purpose: Assert that the FE inline constants match the Python registry. This test is throwaway — it deletes itself (or is deleted as a task) when FE consumers switch to importing from `endgameZones.ts` in Phase 66.

```python
"""Consistency guard: asserts FE inline constants match the Python zone registry.

This test parses the current inline constants in EndgameScoreGapSection.tsx and
EndgameClockPressureSection.tsx using regex, then compares against the Python
registry. It exists ONLY until Phase 66 switches FE consumers to import from
frontend/src/generated/endgameZones.ts. Delete this file when that switchover lands.
"""
import re
from pathlib import Path

import pytest

from app.services.endgame_zones import (
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    ZONE_REGISTRY,
)

_REPO_ROOT = Path(__file__).parent.parent.parent
_SCORE_GAP_TSX = _REPO_ROOT / "frontend/src/components/charts/EndgameScoreGapSection.tsx"
_CLOCK_TSX = _REPO_ROOT / "frontend/src/components/charts/EndgameClockPressureSection.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestFERegistryConsistency:

    def test_conversion_typical_lower(self) -> None:
        src = _read(_SCORE_GAP_TSX)
        # Match: conversion: [ ... { from: 0, to: 0.65 ... } ...
        # The first "to" value after "conversion:" is the weak/typical boundary
        m = re.search(r"conversion:\s*\[.*?from:\s*0,\s*to:\s*([\d.]+)", src, re.DOTALL)
        assert m, "Could not find conversion gauge zone in TSX"
        assert float(m.group(1)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["conversion_win_pct"]["conversion"].typical_lower
        )

    def test_conversion_typical_upper(self) -> None:
        src = _read(_SCORE_GAP_TSX)
        m = re.search(
            r"conversion:\s*\[.*?to:\s*[\d.]+.*?from:\s*([\d.]+),\s*to:\s*([\d.]+)",
            src, re.DOTALL,
        )
        assert m
        assert float(m.group(2)) == pytest.approx(
            BUCKETED_ZONE_REGISTRY["conversion_win_pct"]["conversion"].typical_upper
        )

    def test_recovery_typical_lower_d10(self) -> None:
        """Recovery band re-centered per D-10: must be 0.25 in both TS and Python."""
        src = _read(_SCORE_GAP_TSX)
        m = re.search(r"recovery:\s*\[.*?from:\s*0,\s*to:\s*([\d.]+)", src, re.DOTALL)
        assert m
        fe_val = float(m.group(1))
        py_val = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"].typical_lower
        assert fe_val == pytest.approx(py_val), (
            f"Recovery typical_lower mismatch: FE={fe_val}, Python={py_val}. "
            "Did D-10 edit land in both sources?"
        )

    def test_recovery_typical_upper_d10(self) -> None:
        """Recovery band upper: must be 0.35 after D-10."""
        src = _read(_SCORE_GAP_TSX)
        m = re.search(
            r"recovery:\s*\[.*?to:\s*[\d.]+.*?from:\s*([\d.]+),\s*to:\s*([\d.]+)",
            src, re.DOTALL,
        )
        assert m
        fe_val = float(m.group(2))
        py_val = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"].typical_upper
        assert fe_val == pytest.approx(py_val)

    def test_endgame_skill_zones(self) -> None:
        src = _read(_SCORE_GAP_TSX)
        # ENDGAME_SKILL_ZONES: [{ from: 0, to: 0.45 }, { from: 0.45, to: 0.55 }, ...]
        m = re.search(
            r"ENDGAME_SKILL_ZONES.*?from:\s*0,\s*to:\s*([\d.]+).*?"
            r"from:\s*([\d.]+),\s*to:\s*([\d.]+)",
            src, re.DOTALL,
        )
        assert m
        spec = ZONE_REGISTRY["endgame_skill"]
        assert float(m.group(1)) == pytest.approx(spec.typical_lower)
        assert float(m.group(2)) == pytest.approx(spec.typical_lower)
        assert float(m.group(3)) == pytest.approx(spec.typical_upper)

    def test_neutral_pct_threshold(self) -> None:
        src = _read(_CLOCK_TSX)
        m = re.search(r"NEUTRAL_PCT_THRESHOLD\s*=\s*([\d.]+)", src)
        assert m
        assert float(m.group(1)) == pytest.approx(NEUTRAL_PCT_THRESHOLD)

    def test_neutral_timeout_threshold(self) -> None:
        src = _read(_CLOCK_TSX)
        m = re.search(r"NEUTRAL_TIMEOUT_THRESHOLD\s*=\s*([\d.]+)", src)
        assert m
        assert float(m.group(1)) == pytest.approx(NEUTRAL_TIMEOUT_THRESHOLD)
```

**Regex approach rationale:** The TSX source has stable formatting (no minification in source); regex against the raw source is simpler and less fragile than AST parsing for this throwaway guard. The test file should include a comment directing the executor to delete it when Phase 66 wires the FE imports.

---

## `FilterContext` Schema

[VERIFIED: CONTEXT.md D-14, SEED-003 §FilterContext, endgame router query params]

```python
class FilterContext(BaseModel):
    """Filter context passed to compute_findings and forwarded in EndgameTabFindings.

    Mirrors the endgame router's query parameters. Note:
    - `color` and `rated_only` are included here for filter-faithfulness but are
      NOT forwarded to endgame_service (which has no color filter). Per INS-03,
      they are not fed into the LLM prompt either.
    - `opponent_type` is hardcoded "human" in compute_findings; not exposed here.
    """
    recency: Literal[
        "all_time", "week", "month", "3months", "6months", "year", "3years", "5years"
    ] = "all_time"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    color: Literal["all", "white", "black"] = "all"
    time_controls: list[str] = []
    platforms: list[str] = []
    rated_only: bool = False
```

**`recency` field:** `FilterContext.recency` describes the user's dashboard filter choice, which is separate from the window dimension. The findings service uses TWO windows (all_time and last_3mo) regardless of what `FilterContext.recency` says. The `recency` filter in `FilterContext` maps to a potential narrowing of which games count as the user's "recent" baseline (e.g., "show only last 6 months"). The `last_3mo` window in findings is ALWAYS `recency="3months"` — not parameterized by FilterContext.recency. [ASSUMED based on SEED-003 design — planner should verify this interpretation is consistent with Phase 65 prompt assembly intent]

---

## `SubsectionFinding` and `EndgameTabFindings` Schemas

```python
class SubsectionFinding(BaseModel):
    """Finding for one subsection and one time window.

    Empty-window convention: when a subsection has zero qualifying games for a window,
    emit value=NaN (serialized as JSON null), zone="typical", trend="n_a",
    sample_size=0, sample_quality="thin", is_headline_eligible=False.
    Phase 65 prompt-assembly skips findings where sample_quality=="thin" and value is null.
    """
    subsection_id: SubsectionId
    parent_subsection_id: SubsectionId | None = None  # None for top-level; e.g. "results_by_endgame_type" for type_win_rate_timeline
    window: Window
    metric: MetricId
    value: float  # NaN when no qualifying data; serialized as null by Pydantic v2
    zone: Zone
    trend: Trend
    weekly_points_in_window: int
    sample_size: int
    sample_quality: SampleQuality
    is_headline_eligible: bool
    dimension: dict[str, str] | None = None  # e.g. {"platform": "chess.com", "time_control": "blitz"} or {"bucket": "conversion"}


class EndgameTabFindings(BaseModel):
    """Deterministic findings for the Endgame tab, computed from EndgameOverviewResponse.

    findings_hash excludes as_of (so same findings on different days cache-hit).
    findings_hash is computed after all other fields are set.
    """
    as_of: str  # ISO date, e.g. "2026-04-20"
    filters: FilterContext
    findings: list[SubsectionFinding]
    flags: list[FlagId]
    findings_hash: str  # SHA256 hex of canonical JSON with as_of excluded
```

---

## Empty-Window Handling

**Recommendation: use `float('nan')` for `value`** — Pydantic v2 serializes this as JSON `null`, which is valid JSON. The `math.isnan` check in `assign_zone` returns `"typical"` for NaN, and `is_headline_eligible=False` signals the missing-data state. Phase 65 prompt-assembly skips findings where value is null (NaN).

**Convention document:** Add to `SubsectionFinding` docstring: "value=NaN when no qualifying data; serialized as null by Pydantic v2. Callers must check math.isnan(value) before numeric comparison."

---

## Sample Quality Bands

[VERIFIED: CONTEXT.md D-16]

`SAMPLE_QUALITY_BANDS: dict[SubsectionId, tuple[int, int]]` — `(thin_max, adequate_max)` where:
- `sample_size < thin_max` → `"thin"`
- `thin_max <= sample_size < adequate_max` → `"adequate"`
- `sample_size >= adequate_max` → `"rich"`

Initial values (planner fills in for subsections not listed in CONTEXT.md D-16):

| SubsectionId | thin_max | adequate_max | Rationale |
|---|---|---|---|
| `overall` | 50 | 200 | Per CONTEXT.md D-16; total endgame+non-endgame games |
| `score_gap_timeline` | 10 | 52 | Weekly point count; 10 weeks = thin, 1 year of data = adequate |
| `endgame_metrics` | 30 | 100 | Total endgame games (all buckets) |
| `endgame_elo_timeline` | 10 | 40 | Points in timeline for the combo |
| `time_pressure_at_entry` | 10 | 50 | Clock-eligible endgame games (MIN_GAMES_FOR_CLOCK_STATS = 10) |
| `clock_diff_timeline` | 10 | 52 | Weekly point count |
| `time_pressure_vs_performance` | 30 | 100 | `time_pressure_chart.total_endgame_games` |
| `results_by_endgame_type` | 10 | 40 | Per CONTEXT.md D-16 — "per-type" so 5x smaller than overall |
| `conversion_recovery_by_type` | 10 | 40 | Same rationale as results_by_endgame_type |
| `type_win_rate_timeline` | 5 | 20 | Per-type timeline is always thin — always supporting |

[ASSUMED: values for subsections not specified by D-16. Planner should verify against SEED-001 canonical user fixture.]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slope computation | Custom regression | `statistics.linear_regression` (stdlib) | Deterministic, zero-dependency |
| Standard deviation | Manual stdev | `statistics.stdev` (stdlib) | Correct Bessel-corrected stdev |
| Hash | Custom encoding | `hashlib.sha256` (stdlib) | Standard, stable |
| Zone assignment | Ad-hoc if/elif chains per subsection | `endgame_zones.assign_zone` | Single call site, testable |
| Filter semantics | Direct repo queries | `endgame_service.get_endgame_overview` | Inherits all filter logic; FIND-01 requirement |
| JSON serialization with NaN | Custom NaN-to-null replacer | `model_dump_json()` → `json.loads()` → `json.dumps()` | Pydantic v2 handles NaN correctly in model_dump_json |

---

## Common Pitfalls

### Pitfall 1: `model_dump(mode='json') + json.dumps` with NaN

**What goes wrong:** `model_dump(mode='json')` does NOT convert `float('nan')` to `None`. `json.dumps({'v': float('nan')})` produces `{"v": NaN}` (invalid JSON per RFC 8259) and `json.loads` will reject it.
**Why it happens:** Pydantic's `mode='json'` is for data schema coercion, not for JSON-safe serialization of float special values.
**How to avoid:** Always use `model_dump_json()` first, then `json.loads()`, then `json.dumps(sort_keys=True)`.
**Warning signs:** Tests pass in isolation but `json.loads(findings.model_dump_json())` raises `json.JSONDecodeError`.

[VERIFIED: live Python 3.13 test]

### Pitfall 2: Pydantic v2 Does Not Sort Keys in `model_dump_json`

**What goes wrong:** `findings.model_dump_json()` emits fields in field-declaration order, not alphabetically. `dimension: {"platform": "chess.com", "time_control": "blitz"}` may vary in key order if dict construction order varies.
**How to avoid:** Always pass through `json.loads` + `json.dumps(sort_keys=True)` before hashing.
**Warning signs:** Hash differs between two nominally identical `EndgameTabFindings` objects where inner dicts were built in different insertion order.

[VERIFIED: live Pydantic 2.12.5 test]

### Pitfall 3: Two-Call Async Pattern on Same Session

**What goes wrong:** Trying to `asyncio.gather` the two `get_endgame_overview` calls.
**Why it happens:** The function is async, so gather looks tempting.
**How to avoid:** Call sequentially (await first, then await second) per CLAUDE.md critical constraint. AsyncSession is not safe for concurrent coroutines.
**Warning signs:** `asyncpg` errors about concurrent use of a connection.

### Pitfall 4: `recency` Confusion — FilterContext.recency vs Window

**What goes wrong:** Passing `filter_context.recency` as the `recency` parameter to BOTH `get_endgame_overview` calls.
**Why it happens:** The `FilterContext.recency` field sounds like it should control which data is returned.
**How to avoid:** `all_time` window call always uses `recency=None`. `last_3mo` window call always uses `recency="3months"`. `FilterContext.recency` is the user's current dashboard filter state — it does NOT control the findings-service window logic.
**Warning signs:** The `all_time` findings are narrower than expected when the user has a recency filter active.

### Pitfall 5: Net Timeout Rate Direction

**What goes wrong:** Using `lower_is_better` for `net_timeout_rate` when the formula is `(timeout_wins - timeout_losses) / total * 100` (positive = good).
**Why it happens:** The CONTEXT.md D-06 lists "Net Timeout Rate = `lower_is_better`" but this conflicts with the formula semantics.
**How to avoid:** Verify with user at plan review. [ASSUMED: `higher_is_better` is correct per formula semantics. The flag `[A2]` in the Assumptions Log tracks this.]
**Warning signs:** Users who flag opponents more often than they get flagged show as "weak" on net timeout rate.

### Pitfall 6: `statistics.stdev` Raises on n=1

**What goes wrong:** `statistics.stdev([single_value])` raises `StatisticsError: variance requires at least two data points`.
**How to avoid:** The `min_weekly_points` gate (n >= 20) guarantees n >= 20 before trend computation. Add `if n < 2: return "n_a", n` as a safety guard.

### Pitfall 7: `endgame_skill` Not in `EndgameOverviewResponse` as a Direct Field

**What goes wrong:** Looking for an `endgame_skill` field on `EndgameOverviewResponse`.
**Why it happens:** Phase 59 removed aggregate conversion/recovery/skill fields from `EndgamePerformanceResponse`.
**How to avoid:** Compute `endgame_skill` from `score_gap_material.material_rows` using the same logic as `_endgame_skill_from_bucket_rows` / FE `endgameSkill()`. The findings service must recompute it from the bucket rows in the response.
**Warning signs:** `AttributeError` when accessing `overview.performance.endgame_skill`.

[VERIFIED: endgames.py schema and endgame_service.py Phase 59 comment]

### Pitfall 8: CI Codegen Step Needs `uv` Environment

**What goes wrong:** The CI step `uv run python scripts/gen_endgame_zones_ts.py` fails because `app.services.endgame_zones` is not importable without the uv environment.
**How to avoid:** The step must run after "Install Python dependencies" (which runs `uv sync --locked`). Use `uv run` not bare `python`. [VERIFIED: ci.yml structure]

### Pitfall 9: Knip Dead Export Check

**What goes wrong:** Adding a TS export to `endgameZones.ts` that is not imported anywhere in Phase 63 (since FE consumers are deferred to Phase 66) causes the `npm run knip` step to fail in CI.
**How to avoid:** Either (a) add a knip ignore for the generated file, or (b) do not export unused constants. The `endgameZones.ts` file is entirely new with no consumers in Phase 63 — knip will flag all its exports. **Recommendation:** add `frontend/src/generated/endgameZones.ts` to `knip.json` ignores (similar to the shadcn UI components that are pre-ignored). [ASSUMED: knip configuration is in `frontend/knip.json` or `frontend/package.json`]

---

## Code Examples

### Zone Assignment

```python
# Source: app/services/endgame_zones.py (to be created)
from app.services.endgame_zones import assign_zone, assign_bucketed_zone

zone = assign_zone("endgame_skill", 0.61)            # -> "strong"
zone = assign_zone("score_gap", -0.05)               # -> "typical"
zone = assign_zone("score_gap", float("nan"))        # -> "typical" (with is_headline_eligible=False)
zone = assign_bucketed_zone("recovery_save_pct", "recovery", 0.30)  # -> "typical" (post D-10)
```

### Hash Computation

```python
# Source: insights_service.py (to be created)
import hashlib, json

def _compute_hash(findings: EndgameTabFindings) -> str:
    json_str = findings.model_dump_json(exclude={"findings_hash", "as_of"})
    parsed = json.loads(json_str)
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

### Empty-Window Finding

```python
# Source: insights_service.py (to be created)
import math

def _empty_finding(
    subsection_id: SubsectionId,
    window: Window,
    metric: MetricId,
    parent: SubsectionId | None = None,
) -> SubsectionFinding:
    return SubsectionFinding(
        subsection_id=subsection_id,
        parent_subsection_id=parent,
        window=window,
        metric=metric,
        value=float("nan"),  # Pydantic v2 serializes as null
        zone="typical",
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=0,
        sample_quality="thin",
        is_headline_eligible=False,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Pydantic v1 `dict()` | Pydantic v2 `model_dump()` / `model_dump_json()` | Project-wide v2 adoption | `model_dump_json()` handles NaN as null; v1 did not |
| `json.dumps` directly on Pydantic output | Two-step `model_dump_json` → `json.loads` → `json.dumps(sort_keys=True)` | Phase 63 (new) | Hash stability across sessions |
| FE as source of truth for thresholds | Python registry as source of truth, FE generated | Phase 63 | Single maintenance point; codegen enforces parity |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `net_timeout_rate` direction is `higher_is_better` (positive = user wins flagging battles = good) | Zone Registry | Wrong zone assignment for users with net positive timeout rates |
| A2 | `statistics.linear_regression` provides adequate numeric stability for slope computation in this use case | Trend Computation | Potentially non-deterministic or inaccurate slope on edge-case float sequences |
| A3 | `FilterContext.recency` describes the user's dashboard filter, NOT the window dimension — `last_3mo` window always uses `recency="3months"` regardless of FilterContext.recency | `compute_findings` algorithm | Incorrect findings if recency interaction is more nuanced |
| A4 | `sample_quality` band values for subsections not specified by D-16 (time_pressure_at_entry, clock_diff_timeline, etc.) are plausible starting points | Sample Quality Bands | Bands too wide/narrow for the canonical fixture; revisit in Phase 67 |
| A5 | Knip will flag `endgameZones.ts` exports as dead — adding the file to `knip.json` ignore resolves this | CI Wiring pitfall | CI failure on `npm run knip` if not ignored |
| A6 | `per_week_endgame_games` (not `game_count`) is the "weekly points in window" count for timeline trend gating | Trend computation | Wrong trend gate denominator |

**Note A6 detail:** `_compute_weekly_rolling_series` returns dicts with `game_count` (rolling window size, max=50) and `per_week_game_count` (games in that specific week). For trend gating, `weekly_points_in_window` should be the count of distinct weekly data points in the timeline (i.e., `len(timeline_points)`), NOT the `game_count` rolling window. This is the correct interpretation per FIND-04: "weekly-points-in-window is below threshold."

---

## Open Questions

1. **`net_timeout_rate` direction**
   - What we know: formula is `(timeout_wins - timeout_losses) / total * 100`, positive = user wins more flagging battles
   - What's unclear: CONTEXT.md D-06 lists it as `lower_is_better` without explanation
   - Recommendation: confirm with user at plan-check; most likely `higher_is_better` (positive net = user advantage)

2. **`FilterContext.recency` interaction with the `last_3mo` window**
   - What we know: findings always produce both all_time and last_3mo windows
   - What's unclear: if the user's dashboard filter is e.g. `recency="6months"`, should the `last_3mo` window still use `recency="3months"` (giving data from last 3 months regardless of the 6-month filter)?
   - Recommendation: yes — the two windows are fixed architectural constructs, not parameterized by FilterContext.recency. Phase 65 prompt will label them clearly.

3. **Sample quality band values for subsections not in D-16**
   - What we know: D-16 specifies `score_gap (50, 200)` and `results_by_endgame_type (10, 40)` per-type
   - What's unclear: values for time_pressure, clock_diff_timeline, endgame_elo_timeline
   - Recommendation: use values in the Sample Quality Bands table above (planner pins); Phase 67 validates

4. **Knip ignore for `endgameZones.ts`**
   - What we know: the file will be generated with exports but have no consumers in Phase 63
   - Recommendation: executor adds `"frontend/src/generated/endgameZones.ts"` to knip ignore list in `frontend/knip.json`

---

## Environment Availability

Phase 63 is backend code-only with no new external services. All required tools are verified present.

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.13 | All backend code | ✓ | 3.13.12 | — |
| uv | `uv run`, codegen script | ✓ | 0.10.9 | — |
| pydantic 2.x | Schemas | ✓ | 2.12.5 | — |
| `statistics` stdlib | Trend computation (linear_regression) | ✓ | Python 3.13 | — |
| `hashlib` stdlib | `findings_hash` | ✓ | Python 3.13 | — |
| Node / npm | Codegen output (knip check) | ✓ | Node 24, npm via frontend | — |

[VERIFIED: live environment checks]

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest + pytest-asyncio (already in dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/services/test_insights_service.py tests/services/test_endgame_zones_consistency.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| FIND-01 | No direct repo access from insights_service | unit | `pytest tests/services/test_insights_service.py::test_no_direct_repo_access -x` | ❌ Wave 0 |
| FIND-02 | Zone assignment matches gauge constants | unit | `pytest tests/services/test_endgame_zones_consistency.py -x` | ❌ Wave 0 |
| FIND-02 | Recovery D-10 re-center (both Python and TS) | unit | `pytest tests/services/test_endgame_zones_consistency.py::TestFERegistryConsistency::test_recovery_typical_lower_d10 -x` | ❌ Wave 0 |
| FIND-03 | All 4 flags fire correctly on canonical fixture | unit | `pytest tests/services/test_insights_service.py::test_flags -x` | ❌ Wave 0 |
| FIND-04 | Trend = n_a when weekly_points < 20 | unit | `pytest tests/services/test_insights_service.py::test_trend_gating_count_fail -x` | ❌ Wave 0 |
| FIND-04 | Trend = n_a when slope/vol ratio < 0.5 | unit | `pytest tests/services/test_insights_service.py::test_trend_gating_ratio_fail -x` | ❌ Wave 0 |
| FIND-05 | findings_hash stable across two invocations | unit | `pytest tests/services/test_insights_service.py::test_hash_stability -x` | ❌ Wave 0 |
| FIND-05 | findings_hash changes when findings change | unit | `pytest tests/services/test_insights_service.py::test_hash_changes_on_different_findings -x` | ❌ Wave 0 |
| — | Zone drift check (CI) | integration | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code ...` | ❌ Wave 0 |

### Unit Test Plan

**`tests/services/test_insights_service.py`** — all tests are pure unit tests (no DB, no async except for `compute_findings` integration smoke test):

```
TestZoneAssignment
    test_higher_is_better_below_lower_boundary     -> "weak"
    test_higher_is_better_at_lower_boundary        -> "typical" (boundary inclusive)
    test_higher_is_better_above_upper_boundary     -> "strong"
    test_lower_is_better_inverted_direction        -> verify direction flip
    test_nan_returns_typical                       -> NaN -> "typical"
    test_bucketed_zone_recovery_d10                -> [0.25, 0.35] after D-10

TestTrendGating
    test_count_fail_below_20_weekly_points         -> "n_a"
    test_ratio_fail_below_threshold                -> "n_a"
    test_both_pass_improving                       -> "improving"
    test_both_pass_declining                       -> "declining"
    test_stable_zero_stdev                         -> "stable"
    test_last_3mo_always_na                        -> n=13 < 20 -> "n_a"

TestFlagComputation
    test_baseline_lift_fires_when_skill_strong_gap_typical
    test_baseline_lift_does_not_fire_when_skill_typical
    test_clock_entry_advantage_fires_above_10pct
    test_no_clock_entry_advantage_fires_within_10pct
    test_flags_mutually_exclusive_clock
    test_notable_elo_divergence_fires_when_gap_gt_100
    test_notable_elo_divergence_no_fire_when_gap_lt_100
    test_notable_elo_divergence_uses_max_over_combos

TestHashStability
    test_hash_stable_across_two_constructions      -> same input -> same hash
    test_hash_changes_when_value_changes           -> different value -> different hash
    test_hash_excludes_as_of                       -> different as_of -> same hash
    test_hash_nan_stable                           -> NaN fields produce stable hash (null)

TestEmptyWindow
    test_empty_window_finding_shape                -> value=nan, zone=typical, trend=n_a, thin, not headline
```

**`seeded_user` fixture usage:** The `seeded_user` fixture (module-scoped, from `tests/seed_fixtures.py`) provides a real DB-backed user with 25 games. For most of the above tests, mocking `get_endgame_overview` is cleaner (no DB dependency). Use `seeded_user` only for the integration smoke test that calls `compute_findings` end-to-end.

```python
# Integration smoke test (uses seeded_user)
@pytest.mark.asyncio
async def test_compute_findings_integration(seeded_user: SeededUser, db_session: AsyncSession) -> None:
    """Smoke test: compute_findings returns a valid EndgameTabFindings for the seeded user."""
    filter_ctx = FilterContext()
    result = await compute_findings(filter_ctx, db_session, seeded_user.id)
    assert isinstance(result, EndgameTabFindings)
    assert len(result.findings) > 0
    assert len(result.findings_hash) == 64  # SHA256 hex
    assert result.as_of  # non-empty
```

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_insights_service.py tests/services/test_endgame_zones_consistency.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_insights_service.py` — covers FIND-01, FIND-03, FIND-04, FIND-05
- [ ] `tests/services/test_endgame_zones_consistency.py` — covers FIND-02 (FE drift)
- [ ] `frontend/src/generated/endgameZones.ts` — must be generated in Wave 0 (committed)
- [ ] `frontend/knip.json` — add `endgameZones.ts` to ignore list

---

## Security Domain

Phase 63 has no new user-facing endpoints, no new database access, and no authentication changes. The `compute_findings` function is an internal service entry point (no HTTP exposure in Phase 63). No ASVS categories are applicable.

The only security-adjacent concern is ensuring the `findings_hash` cannot be manipulated to serve incorrect cached insights in Phase 65. The hash is computed server-side from Pydantic-validated data — no user input influences the hash directly.

---

## Pattern Analogs (Recommended `<read_first>` for Executor)

The planner should direct the executor to read these before implementing:

1. **`app/services/stats_service.py`** — existing service with no direct DB access, TypedDicts for internal data, named constants (no magic numbers). Pattern for `insights_service.py`.
2. **`app/schemas/endgames.py`** — large schemas file with many `Literal[...]` types, `BaseModel` subclasses with docstrings. Pattern for `app/schemas/insights.py`.
3. **`tests/seed_fixtures.py`** — `seeded_user` fixture definition (module-scoped, returns `SeededUser` dataclass). Required for integration smoke test.
4. **`tests/test_endgame_service.py`** — pattern for unit-testing endgame service functions with `NamedTuple` mock rows and `AsyncMock.patch`. Pattern for `test_insights_service.py` mocking.
5. **`.github/workflows/ci.yml`** — CI YAML structure for inserting the "Zone drift check" step in the correct position (after "Install Python dependencies", before "Lint (ruff)").

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: direct file read] `app/services/endgame_service.py` lines 881-956, 1556-1611, 1895-2091 — `_endgame_skill_from_bucket_rows`, `_compute_weekly_rolling_series`, `get_endgame_overview` signatures and behavior
- [VERIFIED: direct file read] `app/schemas/endgames.py` — `EndgameOverviewResponse`, all child schemas
- [VERIFIED: direct file read] `frontend/src/components/charts/EndgameScoreGapSection.tsx` lines 79-105 — `FIXED_GAUGE_ZONES`, `ENDGAME_SKILL_ZONES` current values
- [VERIFIED: direct file read] `frontend/src/components/charts/EndgameClockPressureSection.tsx` lines 18, 23 — `NEUTRAL_PCT_THRESHOLD = 10`, `NEUTRAL_TIMEOUT_THRESHOLD = 5`
- [VERIFIED: direct file read] `frontend/src/components/charts/EndgamePerformanceSection.tsx` lines 36-46 — `SCORE_GAP_NEUTRAL_MIN = -0.10`, `SCORE_GAP_NEUTRAL_MAX = 0.10`
- [VERIFIED: live Python 3.13 test] Pydantic 2.12.5 NaN serialization — `model_dump_json()` → `null`; `model_dump(mode='json')` → `float('nan')`
- [VERIFIED: live Python 3.13 test] Pydantic 2.12.5 key ordering — `model_dump_json()` does NOT sort keys
- [VERIFIED: live Python 3.13 test] Float repr stability — `0.25`, `0.32`, `0.35`, `0.65`, `0.75` all round-trip cleanly through `json.dumps`/`json.loads`
- [VERIFIED: direct file read] `.github/workflows/ci.yml` — CI job structure
- [VERIFIED: direct file read] `tests/conftest.py`, `tests/seed_fixtures.py` — test infrastructure
- [VERIFIED: direct file read] `pyproject.toml` — no numpy/scipy in deps; stdlib statistics module is the correct choice
- [VERIFIED: direct file read] `.planning/phases/63-findings-pipeline-zone-wiring/63-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- [CITED: SEED-003-llm-based-insights.md] Architecture rationale, subsection list, flag definitions, prompt structure

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already in lockfile; stdlib-only additions
- Architecture: HIGH — all source files read directly; data flow verified
- Zone registry values: HIGH — read directly from TS source files
- NaN/hash behavior: HIGH — live tested in Python 3.13 + Pydantic 2.12.5
- Sample quality bands: MEDIUM — D-16 specifies two; others are planner estimates
- Trend formula: MEDIUM — `statistics.linear_regression` is correct but stability under adversarial float sequences is [ASSUMED]
- net_timeout_rate direction: LOW — conflicts between CONTEXT.md wording and formula semantics; flagged for user confirmation

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable stack; no fast-moving deps in scope)
