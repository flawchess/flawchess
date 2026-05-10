# Phase 82: LLM prompt awareness of Endgame Start vs End metrics — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 12 (new/modified)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/endgame_zones.py` | service/config | transform | self (additive) | exact |
| `app/services/insights_service.py` | service | transform | `_findings_time_pressure_at_entry` (two-finding pattern) | exact |
| `app/services/insights_llm.py` | service/config | request-response | self (one-line bump) | exact |
| `app/prompts/endgame_insights.md` | prompt/config | — | existing glossary + subsection blocks in same file | exact |
| `tests/services/test_insights_service.py` | test | — | `TestFindingsEndgameMetrics` class | exact |
| `tests/services/test_endgame_zones.py` | test | — | `TestAssignZone` + `TestRegistrySanity` classes | exact |
| `tests/services/test_insights_llm.py` | test | — | `TestPromptVersionAndBody` + `TestPromptAssembly` classes | exact |
| `frontend/src/lib/endgameEntryEvalZones.ts` | utility/config | — | self (constant change only) | exact |
| `frontend/src/components/charts/EndgameStartVsEndSection.tsx` | component | request-response | self (logic amendment) | exact |
| `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` | test | — | self (assertion update) | exact |
| `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | test | — | self (new cases + updates) | exact |
| `CHANGELOG.md` | docs | — | existing `## [Unreleased]` entries | exact |

---

## Pattern Assignments

### `app/services/endgame_zones.py` (service/config, transform)

**Analog:** self (all patterns already established within this file)

**MetricId Literal — current state** (lines 30–49):
```python
MetricId = Literal[
    "score_gap",
    "endgame_score",        # ← D-01: rename to "endgame_score_timeline"
    "non_endgame_score",    # ← D-02: rename to "non_endgame_score_timeline"
    "endgame_skill",
    "conversion_win_pct",
    "parity_score_pct",
    "recovery_save_pct",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    "endgame_elo_gap",
    "win_rate",
]
```

After Phase 82 Plan 1, the renamed values and two new entries must be added:
```python
MetricId = Literal[
    "score_gap",
    "entry_eval_pawns",           # D-04: NEW
    "endgame_score",              # D-03: repurposed (new subsection's Tile-2)
    "endgame_score_timeline",     # D-01: renamed from "endgame_score"
    "non_endgame_score_timeline", # D-02: renamed from "non_endgame_score"
    "endgame_skill",
    ...
]
```

**SubsectionId Literal — current state** (lines 51–61):
```python
SubsectionId = Literal[
    "overall",
    "score_timeline",
    "endgame_metrics",
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    "results_by_endgame_type",
    "conversion_recovery_by_type",
]
```

Add `"endgame_start_vs_end"` to this Literal (D-05).

**ZoneSpec registration pattern** (lines 125–198 — copy the `score_gap` and `endgame_skill` shape):
```python
# In ZONE_REGISTRY dict — add after "score_gap":
"entry_eval_pawns": ZoneSpec(
    # Phase 82 (D-08): editorial tightening from benchmark IQR (±0.75) to
    # ±0.50 — half-a-pawn average swing at EG entry is narratable. Single
    # global band justified (TC max d=0.22, ELO max d=0.28 — both "review",
    # not "keep separate").
    typical_lower=-0.50,
    typical_upper=0.50,
    direction="higher_is_better",
),
# Replaces the old no-op [0, 1] full-range entry. Calibrated to match
# the live SCORE_BULLET_NEUTRAL_MIN/MAX (±0.05 around 0.5). No per-ELO
# registry in this phase (D-10 / D-11 trade-off accepted).
"endgame_score": ZoneSpec(
    typical_lower=0.45,
    typical_upper=0.55,
    direction="higher_is_better",
),
```

**SAMPLE_QUALITY_BANDS — current state** (lines 241–256):
```python
SAMPLE_QUALITY_BANDS: Mapping[SubsectionId, tuple[int, int]] = {
    "overall": (50, 200),
    "score_timeline": (10, 52),
    "endgame_metrics": (30, 100),
    "endgame_elo_timeline": (10, 40),
    "time_pressure_at_entry": (10, 50),   # ← copy this band
    ...
}
```

Add: `"endgame_start_vs_end": (10, 50),` — same gate as `time_pressure_at_entry` (both are per-game aggregate sections with similar expected sample sizes per RESEARCH.md Open Question 1).

---

### `app/services/insights_service.py` — new `_findings_endgame_start_vs_end` emitter (service, transform)

**Analog:** `_findings_time_pressure_at_entry` (two-finding, non-timeline pattern at lines 744–797) AND `_finding_overall` (single non-timeline finding at lines 403–429) AND `endgame_skill` finding (lines 599–614)

**Insertion point in `_compute_subsection_findings`** (lines 371–394):
```python
def _compute_subsection_findings(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    findings: list[SubsectionFinding] = []

    findings.append(_finding_overall(response, window))
    findings.extend(_findings_endgame_start_vs_end(response, window))  # ← INSERT HERE (D-16)
    findings.extend(_findings_score_timeline(response, window))
    findings.extend(_findings_endgame_metrics(response, window))
    ...
```

**New emitter — full implementation pattern** (copy `_findings_time_pressure_at_entry` shape, adapted):
```python
def _findings_endgame_start_vs_end(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_start_vs_end -> TWO findings (entry_eval_pawns, endgame_score).

    Phase 82 (D-16): wire Phase 81 entry_eval and endgame_score into the
    LLM payload. Both are single-aggregate, no series, no dimension (D-19,
    D-20). Empty-window convention: n < 10 -> _empty_finding (D-17).
    is_headline_eligible = sample_quality != "thin" (D-18).
    """
    perf = response.performance

    # Tile 1 — entry eval (D-17: gate on entry_eval_n >= 10)
    n_eval = perf.entry_eval_n
    if n_eval < 10:
        tile1 = _empty_finding("endgame_start_vs_end", window, "entry_eval_pawns")
    else:
        quality = sample_quality("endgame_start_vs_end", n_eval)
        tile1 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="entry_eval_pawns",
            value=perf.entry_eval_mean_pawns,
            zone=assign_zone("entry_eval_pawns", perf.entry_eval_mean_pawns),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=n_eval,
            sample_quality=quality,
            is_headline_eligible=quality != "thin",
            dimension=None,
        )

    # Tile 2 — endgame score vs 50% (D-17: gate on endgame_wdl.total >= 10)
    total = perf.endgame_wdl.total
    if total < 10:
        tile2 = _empty_finding("endgame_start_vs_end", window, "endgame_score")
    else:
        score = (perf.endgame_wdl.wins + 0.5 * perf.endgame_wdl.draws) / total
        quality = sample_quality("endgame_start_vs_end", total)
        tile2 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="endgame_score",
            value=score,
            zone=assign_zone("endgame_score", score),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=total,
            sample_quality=quality,
            is_headline_eligible=quality != "thin",
            dimension=None,
        )

    return [tile1, tile2]
```

**`_empty_finding` helper signature** (lines 1275–1303 — call this, never roll a custom NaN placeholder):
```python
def _empty_finding(
    subsection_id: SubsectionId,
    window: Window,
    metric: MetricId,
    parent: SubsectionId | None = None,
    dimension: dict[str, str] | None = None,
) -> SubsectionFinding:
    # value=NaN, zone="typical", trend="n_a", sample_size=0,
    # sample_quality="thin", is_headline_eligible=False
```

**MetricId rename in `_findings_score_timeline`** — four atomic changes required (lines 522–565, per RESEARCH.md Pitfall 2):
- Line 471: `_empty_finding("score_timeline", window, "endgame_score")` → `"endgame_score_timeline"`
- Line 472: `_empty_finding("score_timeline", window, "non_endgame_score")` → `"non_endgame_score_timeline"`
- Line 528: `metric="endgame_score"` → `metric="endgame_score_timeline"`
- Line 543: `metric="non_endgame_score"` → `metric="non_endgame_score_timeline"`
- Lines 529, 544: `assign_zone("endgame_score", ...)` → `assign_zone("endgame_score_timeline", ...)` and `assign_zone("non_endgame_score", ...)` → `assign_zone("non_endgame_score_timeline", ...)`

**Non-timeline SubsectionFinding constructor pattern** (lines 599–614 — `endgame_skill`, the closest single-aggregate non-dimension analog):
```python
SubsectionFinding(
    subsection_id="endgame_metrics",
    parent_subsection_id=None,
    window=window,
    metric="endgame_skill",
    value=skill_value,
    zone=assign_zone("endgame_skill", skill_value),
    trend="n_a",                    # non-timeline: always "n_a"
    weekly_points_in_window=0,      # non-timeline: always 0
    sample_size=total_games,
    sample_quality=quality,
    is_headline_eligible=is_headline and not math.isnan(skill_value),
    dimension=None,                 # D-19: no dimension for new findings
)
```

Note: new emitter uses `is_headline_eligible=quality != "thin"` (D-18), not the `and not math.isnan(skill_value)` form — the empty-window branch is handled before reaching the populated constructor, so NaN is never passed in.

---

### `app/services/insights_llm.py` (service/config, one-line change)

**Analog:** self — line 66

**Current state** (line 66):
```python
_PROMPT_VERSION = "endgame_v22"  # v22 (260503 eval-proxy cutover): ...
```

**Target state** (D-25):
```python
_PROMPT_VERSION = "endgame_v23"  # v23 (260510 endgame_start_vs_end): wire Phase 81 entry-eval
# and endgame-score metrics into the LLM payload via a new `endgame_start_vs_end` subsection
# under section_id `overall`. Renamed score_timeline `endgame_score` → `endgame_score_timeline`
# and `non_endgame_score` → `non_endgame_score_timeline` to free the clean `endgame_score` name
# for the new subsection. Tile color rule amended from sig-only to `zone × p<0.05`
# (Phase 81 D-09 amendment). EG-entry-eval neutral band tightened from ±0.75 to ±0.50
# for both tile and LLM. [prev v22 text continues...]
```

---

### `app/prompts/endgame_insights.md` (prompt/config)

**Analog:** existing glossary entries (lines 277–283) + existing subsection mapping table (lines 330–346)

**Score_timeline description update** (line 125 — rename `endgame_score` / `non_endgame_score` references to `_timeline` variants):
```
# Before (line 125):
The `score_timeline` subsection emits THREE summary blocks per window, one per metric,
in this deterministic order: `[summary endgame_score]`, `[summary non_endgame_score]`,
then `[summary score_gap]`.

# After:
The `score_timeline` subsection emits THREE summary blocks per window, one per metric,
in this deterministic order: `[summary endgame_score_timeline]`,
`[summary non_endgame_score_timeline]`, then `[summary score_gap]`.
```

**Glossary entries to add** (after line 283, before `conversion_win_pct`). Copy the `score_gap` and `endgame_skill` glossary entry format — definition, scale, band reference, emitter context, narration notes:
```markdown
- **entry_eval_pawns** (UI label: "Endgame entry eval"): user's mean Stockfish evaluation
  at endgame entry in pawns, signed user-perspective. Positive = user was ahead at the
  moment the endgame phase started; negative = user was behind. Mate positions are excluded
  from the mean (eval_cp is NULL for mate rows). Higher is better.
  - Scale: signed decimal pawns (e.g. `+0.62` = "entering endgames 0.62 pawns ahead on
    average"). Render as signed one-decimal value with the unit "pawns"
    (e.g. "+0.6 pawns"). Do NOT convert to centipawns.
  - Cohort typical band: **±0.50 pawns** (pooled benchmark-calibrated band; editorial
    tightening from IQR ±0.75 to ±0.50 to surface half-pawn average swings as narratable).
    A value inside ±0.50 is within-noise; outside the band with `[near edge]` suffix is
    borderline narratable.
  - The tile on the UI uses a significance test (Welch t-test vs H0 = 0 cp). The LLM does
    NOT receive the sig-test outcome — narrate strictly from `zone` + `sample_quality` +
    the `[near edge]` suffix for borderline cases. Do not mention p-values.
  - Emitted in subsection `endgame_start_vs_end`, `dimension=None`.

- **endgame_score** (UI label: "Endgame score"): user's Score in games that reached an
  endgame phase, on the 0–100% scale. Equal-footing baseline is 50% (random-play expectation).
  Computed as `(wins + 0.5 × draws) / total_endgame_games × 100`.
  - Scale: whole-number percentage in `[0, 100]` (e.g. `53` = "53%"). Attach `%` when
    narrating (e.g. `mean=53` → "53%").
  - Cohort typical band: **45–55%** (matches the live Openings score bullet band for visual
    parity; pooled benchmark IQR [0.46, 0.56] overlaps within rounding).
  - The tile on the UI uses a Wilson test vs 50%. The LLM does NOT receive the sig-test
    outcome — narrate strictly from `zone` + `sample_quality` + `[near edge]` for borderline.
  - This metric counts ALL endgame-reaching games in the filtered window — it is NOT
    conditional on eval bucket (Conversion / Parity / Recovery are the eval-conditional
    metrics). An "idle-combo" scoping caveat applies: the filter may mix time-controls /
    platforms with different skill levels.
  - Emitted in subsection `endgame_start_vs_end`, `dimension=None`. NOT the same as the
    `score_timeline` metric `endgame_score_timeline` (the rolling-window timeline variant
    formerly named `endgame_score` in v22 and earlier).
```

**Rename existing glossary entries** (lines 277–283):
- `**endgame_score**` → `**endgame_score_timeline**`, add note "formerly named `endgame_score` through endgame_v22"
- `**non_endgame_score**` → `**non_endgame_score_timeline**`, same note

**New subsection block** (insert between `### Subsection: overall` and `### Subsection: score_timeline` blocks, following the existing H3 block pattern found throughout the prompt):
```markdown
### Subsection: endgame_start_vs_end

Two summary findings under section_id `overall`. Read them as a **setup → execution** pair:

- `entry_eval_pawns` = **where the user starts the endgame** (average position going in).
- `endgame_score` = **what the user does with it** (overall score once the endgame starts).

Together they answer: "given the positions this user reaches endgames from, are they converting / squandering / defending appropriately?"

**Example narration patterns:**
- `entry_eval_pawns` strong + `endgame_score` strong → "consistently enters endgames with an edge and capitalises on it"
- `entry_eval_pawns` strong + `endgame_score` weak → "often enters endgames ahead but squanders typical advantages — check the Time Pressure section for clock-management causes"
- `entry_eval_pawns` weak + `endgame_score` strong → "frequently starts endgames behind yet defends well above expectation"
- `entry_eval_pawns` weak + `endgame_score` weak → "starts from behind AND struggles to hold — may want to focus on middlegame before the endgame phase"
- Either metric `typical` → don't feature it as a headline; it is background context for the `score_gap` / `score_timeline` story

**Within-noise and borderline cases:**
- If `entry_eval_pawns` is `typical` (inside ±0.50): narrate as "entering endgames at roughly equal footing" or skip.
- If `endgame_score` is `typical` (inside 45–55%): skip or use as neutral context.
- `[near edge]` suffix: the value is just outside the typical band but the sample is still supporting (adequate or rich). Narrate as "a small but real pattern" rather than a clear strength/weakness signal.

**Cross-section link — Time Pressure causal story:**
When `entry_eval_pawns` is strong (or typical) but `endgame_score` is weak, look at the `time_pressure_vs_performance` chart and `avg_clock_diff_pct`. If the user enters endgames ahead on material but behind on clock, the clock deficit (not skill deficit) may explain the score gap. The `[low-time-gap]` caption tag in the time-pressure chart is the authoritative verdict for this cross-section reading.

**Both thin → omit from narration.** If both findings have `sample_quality="thin"`, skip this subsection entirely — there is no endgame data in this window.
```

**Mapping table update** (lines 334–346 — insert row between `overall` and `score_timeline`):
```markdown
| Subsection / Chart                   | section_id     |
| ------------------------------------ | -------------- |
| overall                              | overall        |
| endgame_start_vs_end                 | overall        |   ← INSERT (D-24)
| score_timeline                       | overall        |
| Chart: overall_wdl                   | overall        |
| endgame_metrics                      | metrics_elo    |
...
```

---

### `tests/services/test_insights_service.py` — `TestFindingsEndgameStartVsEnd` (test)

**Analog:** `TestFindingsEndgameMetrics` class (lines 542–712) — same pattern: `_make_overview_*` builder + per-test import of private function + assertion on `findings` list

**Import pattern to copy** (lines 24–55):
```python
from __future__ import annotations
import math
from typing import Any, cast
import pytest
from app.schemas.endgames import EndgameOverviewResponse
from app.schemas.insights import SubsectionFinding
```

**Test class skeleton — copy `TestFindingsEndgameMetrics` structure**:
```python
class TestFindingsEndgameStartVsEnd:
    """Unit tests for _findings_endgame_start_vs_end (Phase 82 D-16)."""

    def _make_overview_with_performance(
        self,
        entry_eval_mean_pawns: float,
        entry_eval_n: int,
        wins: int,
        draws: int,
        losses: int,
    ) -> Any:
        """Build a minimal EndgameOverviewResponse with given performance fields."""
        # Use EndgameOverviewResponse.model_construct (same as TestFindingsEndgameMetrics)
        # to avoid DB dependency. Populate `performance` field only.
        ...

    def test_populated_both_tiles_returns_two_findings(self) -> None:
        """n_eval >= 10 and total >= 10 -> two SubsectionFindings."""
        from app.services.insights_service import _findings_endgame_start_vs_end
        response = self._make_overview_with_performance(
            entry_eval_mean_pawns=0.62, entry_eval_n=50,
            wins=25, draws=10, losses=15
        )
        findings = _findings_endgame_start_vs_end(response, "all_time")
        assert len(findings) == 2
        assert findings[0].metric == "entry_eval_pawns"
        assert findings[1].metric == "endgame_score"

    def test_empty_tile1_when_n_eval_lt_10(self) -> None:
        """entry_eval_n < 10 -> Tile 1 is empty (NaN value, thin quality)."""
        ...

    def test_empty_tile2_when_total_lt_10(self) -> None:
        """endgame_wdl.total < 10 -> Tile 2 is empty."""
        ...

    def test_zone_strong_for_entry_eval_above_band(self) -> None:
        """entry_eval_mean_pawns=+0.80 -> zone='strong' (outside ±0.50 band)."""
        ...

    def test_zone_weak_for_entry_eval_below_band(self) -> None:
        """entry_eval_mean_pawns=-0.80 -> zone='weak'."""
        ...

    def test_zone_typical_for_entry_eval_inside_band(self) -> None:
        """entry_eval_mean_pawns=+0.30 -> zone='typical'."""
        ...

    def test_zone_strong_for_endgame_score_above_band(self) -> None:
        """score > 0.55 -> zone='strong'."""
        ...

    def test_zone_weak_for_endgame_score_below_band(self) -> None:
        """score < 0.45 -> zone='weak'."""
        ...

    def test_dimension_is_none(self) -> None:
        """Both findings carry dimension=None (D-19)."""
        ...

    def test_series_is_none(self) -> None:
        """Both findings carry series=None (D-20 — not timeline metrics)."""
        ...

    def test_empty_finding_is_not_headline_eligible(self) -> None:
        """Empty finding has is_headline_eligible=False."""
        ...

    def test_populated_adequate_quality_is_headline_eligible(self) -> None:
        """is_headline_eligible=True when sample_quality != 'thin'."""
        ...
```

**`_make_overview_with_performance` builder pattern** — copy `model_construct` shape from `TestFindingsEndgameMetrics._make_overview_with_material_rows` (lines 545–563):
```python
from app.schemas.endgames import EndgamePerformanceResponse, EndgameWDLSummary
perf = EndgamePerformanceResponse.model_construct(
    entry_eval_mean_pawns=entry_eval_mean_pawns,
    entry_eval_n=entry_eval_n,
    endgame_wdl=EndgameWDLSummary(
        wins=wins, draws=draws, losses=losses,
        total=wins+draws+losses,
        win_pct=..., draw_pct=..., loss_pct=...
    ),
    # other fields not needed by the emitter: use model_construct defaults
)
resp = EndgameOverviewResponse.model_construct(performance=perf)
```

---

### `tests/services/test_endgame_zones.py` — new zone boundary tests (test)

**Analog:** `TestAssignZone` class (lines 16–59) and `TestRegistrySanity` class (lines 105–144)

**New test class pattern** (mirror `TestAssignZone` boundary semantics):
```python
class TestNewMetricZones:
    """Phase 82: zone boundary tests for entry_eval_pawns and endgame_score (D-08, D-10)."""

    # --- entry_eval_pawns (±0.50 band, D-08) ---
    def test_entry_eval_above_upper_is_strong(self) -> None:
        assert assign_zone("entry_eval_pawns", 0.80) == "strong"

    def test_entry_eval_at_upper_boundary_is_strong(self) -> None:
        """Upper boundary is inclusive on the strong side (>= typical_upper)."""
        assert assign_zone("entry_eval_pawns", 0.50) == "strong"

    def test_entry_eval_just_inside_upper_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", 0.49) == "typical"

    def test_entry_eval_at_zero_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", 0.0) == "typical"

    def test_entry_eval_at_lower_boundary_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", -0.50) == "typical"

    def test_entry_eval_below_lower_is_weak(self) -> None:
        assert assign_zone("entry_eval_pawns", -0.80) == "weak"

    def test_entry_eval_nan_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", float("nan")) == "typical"

    # --- endgame_score ([0.45, 0.55] band, D-10) ---
    def test_endgame_score_above_upper_is_strong(self) -> None:
        assert assign_zone("endgame_score", 0.60) == "strong"

    def test_endgame_score_at_upper_boundary_is_strong(self) -> None:
        assert assign_zone("endgame_score", 0.55) == "strong"

    def test_endgame_score_in_typical_band_is_typical(self) -> None:
        assert assign_zone("endgame_score", 0.50) == "typical"

    def test_endgame_score_at_lower_boundary_is_typical(self) -> None:
        assert assign_zone("endgame_score", 0.45) == "typical"

    def test_endgame_score_below_lower_is_weak(self) -> None:
        assert assign_zone("endgame_score", 0.40) == "weak"

    def test_endgame_score_nan_is_typical(self) -> None:
        assert assign_zone("endgame_score", float("nan")) == "typical"
```

**`TestRegistrySanity.test_all_scalar_metrics_have_entries`** — update set assertion (lines 118–127) to replace `"endgame_score"`, `"non_endgame_score"` with the renamed+new set:
```python
assert set(ZONE_REGISTRY.keys()) == {
    "score_gap",
    "entry_eval_pawns",           # NEW
    "endgame_score",              # repurposed (was no-op [0,1])
    "endgame_score_timeline",     # renamed from "endgame_score"
    "non_endgame_score_timeline", # renamed from "non_endgame_score"
    "endgame_skill",
    "avg_clock_diff_pct",
    "net_timeout_rate",
    "endgame_elo_gap",
    "win_rate",
}
```

---

### `tests/services/test_insights_llm.py` — prompt version + metric-name updates (test)

**Analog:** `TestPromptVersionAndBody` class (lines 193–257)

**Version assertion to update** (line 207):
```python
# Before:
def test_prompt_version_is_v22(self) -> None:
    assert insights_llm._PROMPT_VERSION == "endgame_v22"

# After (rename test too):
def test_prompt_version_is_v23(self) -> None:
    assert insights_llm._PROMPT_VERSION == "endgame_v23"
```

**Metric-name assertions to update in `score_timeline` context** (lines 233, 270, 355, 361, 424 — per RESEARCH.md Pitfall 4):
```python
# Before (line 233):
assert "[summary endgame_score]" in body

# After:
assert "[summary endgame_score_timeline]" in body

# Before (line 234):
assert "[summary non_endgame_score]" in body

# After:
assert "[summary non_endgame_score_timeline]" in body
```

**Score_timeline subsection finding constructors** (lines 267–291, 354–426 — update metric= field):
```python
# Before:
SubsectionFinding(
    subsection_id="score_timeline",
    metric="endgame_score",
    ...
)
# After:
SubsectionFinding(
    subsection_id="score_timeline",
    metric="endgame_score_timeline",
    ...
)
```

**Mapping table test to extend** (lines 239–256 — add `endgame_start_vs_end` row check):
```python
def test_subsection_mapping_table_includes_endgame_start_vs_end(self) -> None:
    """New endgame_start_vs_end subsection must appear in the mapping table."""
    body = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
    with open(body) as f:
        content = f.read()
    found = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("| endgame_start_vs_end") and "overall" in stripped:
            found = True
            break
    assert found, "missing `| endgame_start_vs_end ... | overall |` row in mapping table"
```

**New subsection block assertion** (new test in `TestPromptVersionAndBody`):
```python
def test_prompt_contains_endgame_start_vs_end_subsection(self) -> None:
    body_path = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
    with open(body_path) as f:
        body = f.read()
    assert "### Subsection: endgame_start_vs_end" in body
    # Glossary entries for both new metrics
    assert "entry_eval_pawns" in body
    # endgame_score appears in both old (score_timeline) and new context;
    # check for the NEW subsection-specific text:
    assert "endgame_start_vs_end" in body
```

---

### `frontend/src/lib/endgameEntryEvalZones.ts` (utility/config, constant change)

**Analog:** self (lines 19–23)

**Current state** (lines 20, 23):
```typescript
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75;
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.75;
```

**Target state** (D-09):
```typescript
/** EG-entry: lower bound of the neutral zone in pawns. Phase 82 (D-09):
 * tightened from ±0.75 to ±0.50 to align with backend ZoneSpec and
 * narration threshold. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.50;
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.50;
```

The `endgameEntryEvalZoneColor` function (lines 36–40) requires no change — it already reads the constants:
```typescript
export function endgameEntryEvalZoneColor(value: number): string {
  if (value >= ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (value <= ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
```

---

### `frontend/src/components/charts/EndgameStartVsEndSection.tsx` (component, logic amendment)

**Analog:** self — the tile-color gate is at lines 67–71 and 86–90

**Current gate** (lines 69–71 — sig-only, Phase 81 D-09):
```typescript
const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
```

**Target gate** (D-12 — zone × sig): Per RESEARCH.md finding 4 and the Code Examples section, the existing `isConfident(evalLevel) && evalIsInColoredZone` pattern already implements `zone × p<0.05` ONCE the neutral-band constants are tightened from ±0.75 to ±0.50 (D-09). No structural logic change is needed beyond the constant update.

The logic at lines 86–90 for Tile 2 is identically structured and already correctly implements `zone × sig`:
```typescript
const scoreIsInColoredZone = scoreZoneHex !== ZONE_NEUTRAL;
const scoreShowZoneFontColor = isConfident(scoreLevel) && scoreIsInColoredZone;
const scoreColor: string | undefined = scoreShowZoneFontColor ? scoreZoneHex : undefined;
```

**Conclusion:** Updating `endgameEntryEvalZones.ts` constants is sufficient for Tile 1 to implement the D-12 rule. No changes needed to `EndgameStartVsEndSection.tsx` logic itself.

---

### `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` (test, constant updates)

**Analog:** self (lines 16–18)

**Lines to update** (per RESEARCH.md Pitfall 5):
```typescript
// Before (line 16-18):
it('uses ±0.75 pawn neutral band (Q1/A1, benchmark v3 §3c)', () => {
  expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.75);
  expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS).toBe(0.75);
});

// After:
it('uses ±0.50 pawn neutral band (Phase 82 D-09: tightened from ±0.75)', () => {
  expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.50);
  expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS).toBe(0.50);
});
```

**`endgameEntryEvalZoneColor` tests** (lines 26–40) — update boundary values from 0.75 to 0.50:
```typescript
// Before (line 28-30): neutral cases include 0.5
expect(endgameEntryEvalZoneColor(0.5)).toBe(ZONE_NEUTRAL);  // still neutral at 0.49
// After: 0.5 is now at the boundary (returns ZONE_SUCCESS), change to 0.49:
expect(endgameEntryEvalZoneColor(0.49)).toBe(ZONE_NEUTRAL);

// Before (line 32-34): SUCCESS at and above +0.75
it('returns SUCCESS at and above +0.75 pawns', ...)
  expect(endgameEntryEvalZoneColor(0.75)).toBe(ZONE_SUCCESS);
// After: SUCCESS at and above +0.50
it('returns SUCCESS at and above +0.50 pawns', ...)
  expect(endgameEntryEvalZoneColor(0.50)).toBe(ZONE_SUCCESS);
  expect(endgameEntryEvalZoneColor(0.75)).toBe(ZONE_SUCCESS); // still true

// Before (line 36-39): DANGER at and below -0.75
// After: DANGER at and below -0.50
  expect(endgameEntryEvalZoneColor(-0.50)).toBe(ZONE_DANGER);
```

---

### `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` (test, updates + new cases)

**Analog:** self — existing test structure is the pattern to extend

**Critical update — Pitfall 5 (line 193 + 280–288):**

Test at line 189 "Tile 1 value text is unstyled when significant but inside the neutral band" uses `entry_eval_mean_pawns: 0.5`. After tightening to ±0.50, value `0.5` is exactly on the boundary (`>= NEUTRAL_MAX` → returns `ZONE_SUCCESS`), so it would show a color. Change input to clearly inside the band:
```typescript
// Before (lines 189-202):
it('Tile 1 value text is unstyled when significant but inside the neutral band', () => {
  render(
    <EndgameStartVsEndSection
      data={buildPerf({
        entry_eval_mean_pawns: 0.5,   // ← boundary case at ±0.50!
        ...
      })}
    />,
  );
  expect(valueSpan.style.color).toBe('');  // Would FAIL — 0.5 is now ZONE_SUCCESS
});

// After:
data={buildPerf({
  entry_eval_mean_pawns: 0.4,   // clearly inside ±0.50 band
  ...
})}
```

**Prop-forwarding assertion update** (line 283–288 — `neutralMin/Max` from ±0.75 to ±0.50):
```typescript
// Before:
expect(tile1Call?.[0]).toMatchObject({
  ...
  neutralMin: -0.75,
  neutralMax: 0.75,
  ...
});

// After:
expect(tile1Call?.[0]).toMatchObject({
  ...
  neutralMin: -0.50,
  neutralMax: 0.50,
  ...
});
```

**Test description update** (line 273):
```typescript
// Before:
// Find the call that came from Tile 1: identified by center=0 and the
// ±0.75 neutral band and the ±2.0 domain (D-15).
// After:
// Find the call that came from Tile 1: identified by center=0 and the
// ±0.50 neutral band (Phase 82 D-09) and the ±2.0 domain.
```

**New test cases to add** (D-12 tile-color rule verification with the tightened band):

These cases verify the `zone × sig` rule at the new ±0.50 boundary:
```typescript
it('Tile 1 value text is ZONE_SUCCESS when value is at the ±0.50 boundary + significant', () => {
  // 0.5 is now at the boundary (>= NEUTRAL_MAX) → ZONE_SUCCESS when sig
  render(
    <EndgameStartVsEndSection
      data={buildPerf({
        entry_eval_mean_pawns: 0.5,
        entry_eval_p_value: 0.001,
        entry_eval_n: 50,
      })}
    />,
  );
  const valueSpan = within(screen.getByTestId('tile-entry-eval'))
    .getByTestId('entry-eval-value');
  expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
});

it('Tile 1 value text is unstyled when value is just inside the ±0.50 band + significant', () => {
  render(
    <EndgameStartVsEndSection
      data={buildPerf({
        entry_eval_mean_pawns: 0.4,  // inside [-0.50, +0.50)
        entry_eval_p_value: 0.001,
        entry_eval_n: 50,
      })}
    />,
  );
  const valueSpan = within(screen.getByTestId('tile-entry-eval'))
    .getByTestId('entry-eval-value');
  expect(valueSpan.style.color).toBe('');
});
```

---

## Shared Patterns

### Empty-window finding convention
**Source:** `app/services/insights_service.py` lines 1275–1303 (`_empty_finding`)
**Apply to:** `_findings_endgame_start_vs_end` for both tiles when n < 10 gate fails

The canonical convention: `value=NaN`, `zone="typical"`, `trend="n_a"`, `sample_size=0`, `sample_quality="thin"`, `is_headline_eligible=False`. Never hand-roll this.

### Non-timeline SubsectionFinding constructor
**Source:** `app/services/insights_service.py` lines 403–429 (`_finding_overall`) and lines 599–614 (`endgame_skill`)
**Apply to:** both findings in `_findings_endgame_start_vs_end`

Always set `trend="n_a"`, `weekly_points_in_window=0`, `series` field absent (defaults to None), `dimension=None` for aggregate findings.

### `assign_zone` dispatch
**Source:** `app/services/endgame_zones.py` lines 313–323
**Apply to:** both new MetricId entries (`entry_eval_pawns`, `endgame_score`)

`assign_zone` returns `"typical"` for NaN automatically. Just register the `ZoneSpec` in `ZONE_REGISTRY` and call `assign_zone(metric_id, value)`.

### Tile-color gate pattern (frontend)
**Source:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx` lines 67–71
**Apply to:** both tiles — already uses `isConfident(level) && isInColoredZone`

```typescript
const zoneHex = zoneColorFn(value);
const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
const showZoneFontColor = isConfident(level) && isInColoredZone;
const color: string | undefined = showZoneFontColor ? zoneHex : undefined;
```

After the constant tightening, this pattern implements D-12 `(zone != neutral) AND p < 0.05` naturally.

### Test `model_construct` for partial schema construction (backend tests)
**Source:** `tests/services/test_insights_service.py` lines 560–562
**Apply to:** `TestFindingsEndgameStartVsEnd._make_overview_with_performance`

```python
resp = EndgameOverviewResponse.model_construct(performance=perf)
```

`model_construct` bypasses Pydantic validation — needed when only one field of a complex response is required for the unit under test.

### Prompt file assertions pattern (test_insights_llm.py)
**Source:** `tests/services/test_insights_llm.py` lines 210–233
**Apply to:** new mapping-table and subsection-block tests

```python
body_path = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
with open(body_path) as f:
    body = f.read()
assert "### Subsection: endgame_start_vs_end" in body
```

---

## No Analog Found

None — all files have established analogs in the codebase.

---

## Pitfall Summary (from RESEARCH.md — actionable for planner)

| Pitfall | Affected Plan | Guard |
|---------|--------------|-------|
| MetricId rename must update 4 sites atomically in `_findings_score_timeline` (lines 471–472, 528, 543) | Plan 1 | Run `ty check` + `pytest test_insights_llm.py -k score_timeline` |
| `ZONE_REGISTRY` old `"endgame_score"` key must be renamed AND repurposed — two edits in the same dict | Plan 1 | Run `pytest tests/services/test_endgame_zones.py` |
| `SAMPLE_QUALITY_BANDS` must include `"endgame_start_vs_end"` before `sample_quality()` is called | Plan 1 | Runtime `KeyError` if missing; caught by new emitter tests |
| `test_prompt_version_is_v22` (line 207) hard-fails until bumped in same commit as prompt changes | Plan 2 | Bump `_PROMPT_VERSION` and update test in same plan |
| All `metric="endgame_score"` in `score_timeline` context assertions (lines 233, 270, 355, 361, 424) need rename | Plan 2 | `pytest test_insights_llm.py -k score_timeline` |
| `EndgameStartVsEndSection.test.tsx` line 193 uses `0.5` as "inside band" — becomes boundary after tightening | Plan 3 | Change input to `0.4`; run `npm test` |
| `endgameEntryEvalZones.test.ts` lines 17–18, 28–34 assert ±0.75 — fail after constant change | Plan 3 | Update all boundary values to ±0.50 |
| Codegen (`gen_endgame_zones_ts.py`) does NOT output `entry_eval_pawns` or renamed `endgame_score_timeline` — no regen needed | Plan 1 | Do not run regen; CI drift check will pass |

---

## Metadata

**Analog search scope:** `app/services/`, `app/prompts/`, `tests/services/`, `frontend/src/lib/`, `frontend/src/components/charts/`
**Files read:** 12 source files + 4 test files
**Pattern extraction date:** 2026-05-10
