---
phase: 82-llm-prompt-awareness-of-endgame-start-vs-end-metrics
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app/prompts/endgame_insights.md
  - app/services/endgame_zones.py
  - app/services/insights_llm.py
  - app/services/insights_service.py
  - frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx
  - frontend/src/lib/endgameEntryEvalZones.ts
  - frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts
  - tests/services/test_endgame_zones.py
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service_series.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
  resolved: 7
status: resolved
resolution_notes: |
  CR-01 fixed in cdb36ac2 (entry_eval_pawns added to _NON_FRACTIONAL_METRICS,
  decimal precision plumbed through formatters, proximity + within-noise caps
  recalibrated for pawn scale, regression test asserts mean=+0.46 / band -0.50
  to +0.50).

  WR-01 (asymmetric tile narration), WR-02 (gate divergence doc), WR-03
  (_NO_BAND_METRICS constant + direct skip-list tests), IN-01 (drop dead None
  guard), IN-02 (test description rephrase), IN-03 (n=10 / n=50 boundary tests
  in both test_insights_service.py and test_endgame_zones.py) all addressed in
  fe9b9430.
---

# Phase 82: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The phase wires the Phase 81 `entry_eval_mean_pawns` and `endgame_score` metrics into the LLM payload via a new `endgame_start_vs_end` subsection, renames the `score_timeline` per-part metrics to `*_timeline` variants, fixes the `_SECTION_LAYOUT` wiring, and tightens the entry-eval neutral band to ±0.5 across backend, frontend, and prompt.

The headline defect is a **unit-mismatch BLOCKER on `entry_eval_pawns`**: the metric is documented to the LLM as decimal pawns ("+0.6 pawns", "±0.50 pawns") but the prompt assembler routes it through the default percent-scaling path (multiply by 100), so the LLM sees `mean=+62, (typical -50 to +50)` which directly contradicts the glossary it was given. This is the single-finding-payload metric Phase 82 was built to deliver, and what reaches the model is wrong by a factor of 100. Several supporting concerns (proximity-threshold mismatch on the same metric, narration template asymmetry when one tile is thin, dead-code defensive guard, unverified empty-tile rendering) follow from the same code path.

The renames, `_SECTION_LAYOUT` wiring, `_format_zone_bounds` skip-list update, and frontend ±0.5 tightening are otherwise consistent across files and have direct test coverage.

## Critical Issues

### CR-01: `entry_eval_pawns` is rendered to the LLM in centipawn-like units, contradicting the glossary

**File:** `app/services/insights_llm.py:100-107` (and the rendering call site at `_summary_window_line:973-980`, the appendix at `_build_zone_threshold_appendix:169-176`, and the proximity hint at `_proximity_hint:756-762`)

**Issue:**
`_NON_FRACTIONAL_METRICS` is `frozenset({"endgame_elo_gap", "avg_clock_diff_pct", "net_timeout_rate"})`. The new metric `entry_eval_pawns` is NOT in this set, so `_scale_for_metric("entry_eval_pawns")` returns 100.0 (the fractional default). The unit of `entry_eval_pawns` in `EndgamePerformanceResponse` is decimal pawns, not a 0..1 fraction:
```
entry_eval_mean_pawns: float = 0.0  # signed pawns, e.g. +0.62
```
Effects, all visible to the LLM:

1. `[summary entry_eval_pawns]` window line renders `mean=+{value*100:.0f}` — a true 0.62-pawn mean prints as `mean=+62`, no unit suffix. The glossary at `app/prompts/endgame_insights.md:312` instructs: *"Render as signed one-decimal value with the unit 'pawns' (e.g. '+0.6 pawns'). Do NOT convert to centipawns."* The data the LLM is given pre-converted to a centipawn-looking integer with no unit.
2. `_format_zone_bounds("entry_eval_pawns", None)` → ZoneSpec(-0.50, +0.50) → `(typical -50 to +50)`. The glossary says band is `±0.50 pawns`. The LLM sees `±50` and either treats it as 50 pawns (absurd), 50% (wrong concept), or correctly infers centipawns (style violation per "Do NOT convert to centipawns").
3. `_build_zone_threshold_appendix` emits `\`entry_eval_pawns\`: weak<-50, typical [-50, 50], strong>50` — same units bug, in the auto-appended `## Zone thresholds` block.
4. `_proximity_hint` uses `_PROXIMITY_PCT_THRESHOLD = 2.0`. The threshold is intended for percent-scale metrics (~2pp). On the now-scaled `entry_eval_pawns` it corresponds to 0.02 pawns of true value — much tighter than the ~0.05-pawn proximity feel implied by the glossary's "borderline" framing. `[near edge]` will fire on a wider range of inputs than the glossary leads the LLM to expect.

This is the headline metric Phase 82 was built to wire in. The findings layer is correct (`assign_zone("entry_eval_pawns", 0.62)` against the [-0.5, +0.5] band returns "strong"), but the prompt-rendering layer corrupts the value and band by 100× before the LLM ever sees them. There are no tests asserting the rendered text of an `entry_eval_pawns` summary block, so this slipped through.

**Fix:**
Add `entry_eval_pawns` to `_NON_FRACTIONAL_METRICS` so its raw decimal-pawn value passes through unmodified, then change the format strings on the entry-eval path from `:+.0f` to `:+.1f` (the glossary asks for "+0.6 pawns", not "+1 pawns"). Concrete patch:

```python
# app/services/insights_llm.py
_NON_FRACTIONAL_METRICS: frozenset[str] = frozenset(
    {"endgame_elo_gap", "avg_clock_diff_pct", "net_timeout_rate", "entry_eval_pawns"}
)
```

The format-precision fix is metric-specific. Either:
- Introduce a `_DECIMAL_PRECISION` map keyed by metric_id (default 0, `entry_eval_pawns` → 1) and thread it through `_summary_window_line`, `_build_zone_threshold_appendix`, `_format_zone_bounds`, and `_render_series_block` (entry-eval has no series today, so the last is unused), OR
- Render entry-eval through a separate code path that knows about pawn units.

Add a regression test under `tests/services/test_insights_llm.py` that builds a `SubsectionFinding(metric="entry_eval_pawns", value=0.62, dimension=None, ...)`, runs `_assemble_user_prompt`, and asserts the rendered `[summary entry_eval_pawns]` block contains `mean=+0.6` (or `+0.6 pawns`) and `(typical -0.5 to +0.5)` — NOT `+62` or `(typical -50 to +50)`.

Also add a sanity test for the proximity-threshold scale: a value of 0.49 pawns with the new unit handling should NOT fire `[near edge]` unless the threshold is explicitly recalibrated for pawn units (or document and accept the new 0.02-pawn proximity, which is unusually tight).

## Warnings

### WR-01: Narration template breaks when one tile is empty and the other is populated

**File:** `app/prompts/endgame_insights.md:250-274` and `app/services/insights_service.py:433-494`

**Issue:**
`_findings_endgame_start_vs_end` gates each tile independently (D-17). After `_assemble_user_prompt` filters NaN/thin findings, a window can legitimately render `### Subsection: endgame_start_vs_end` with only ONE of the two `[summary]` blocks present. The prompt's "setup → execution pair" framing and the four 2×2 example narration patterns all assume both tiles exist. There is no guidance for the asymmetric case, and no test exercises it. The most likely real-world manifestation: a fresh user with `entry_eval_n < 10` (Stockfish backfill not yet complete on imported games) but `endgame_wdl.total >= 10` will see the `endgame_score` tile narrated in isolation, with the LLM possibly forced into the "typical → skip" guidance applied to the wrong axis or fabricating a setup story to satisfy the pair template.

**Fix:**
Add one short paragraph to the `### Subsection: endgame_start_vs_end` block in `app/prompts/endgame_insights.md` covering the single-tile case, e.g. "When only one of the two tiles meets the n>=10 gate (the other is omitted), narrate that tile on its own without invoking the setup→execution pairing — the missing side should not be inferred." Add a unit test in `test_insights_llm.py` that builds a payload with only `endgame_score` populated for `endgame_start_vs_end` and asserts the rendered subsection has exactly one `[summary]` block under that header, so a future emitter regression cannot silently drop the populated tile.

### WR-02: `_finding_overall` and `_findings_endgame_start_vs_end` use inconsistent empty-window gates

**File:** `app/services/insights_service.py:404-430` (overall) vs `app/services/insights_service.py:433-494` (endgame_start_vs_end)

**Issue:**
`_finding_overall` returns `_empty_finding(...)` when `sample_size == 0`, so any window with even 1 game emits a real finding. `_findings_endgame_start_vs_end` returns `_empty_finding(...)` when `total < 10` (Tile 2) or `n_eval < 10` (Tile 1). Both reference the same underlying `endgame_wdl.total`, so for `1 <= total <= 9`:
- The `overall` subsection emits a real `score_gap` finding with sample_quality classified by `SAMPLE_QUALITY_BANDS["overall"] = (50, 200)` — i.e. "thin" — and the prompt assembler will subsequently filter it out via the `sample_size == 0 AND quality == "thin"` check (line 1586).
- The `endgame_start_vs_end` subsection emits a NaN-valued `_empty_finding` for Tile 2, also filtered out.

The two paths reach the same outcome (no rendered block) for the 1-9 case, but they get there differently. The risk: any future change to the "drop NaN/thin/empty" filter chain (the line 1581 list comprehension) that loosens the predicate could let the `overall` finding through with `score_gap = NaN/0`-ish noise based on a 3-game sample, while `endgame_start_vs_end` would still suppress correctly. The two gates should match the same minimum-viable-narration threshold.

**Fix:**
Either (a) align `_finding_overall` to use a `< 10` gate, matching the new subsection's threshold and the documented "thin = n<10" convention used by `time_pressure_at_entry` and `endgame_start_vs_end`, OR (b) keep the divergence but add a comment in `_finding_overall` explaining why `== 0` is correct there (the `score_gap` denominator is endgame + non_endgame, so the floor is intentionally lower) and add a test asserting `1 <= total <= 9` payloads stay invisible to the LLM through whichever gate fires first. Document the chosen rationale at the call site.

### WR-03: `_format_zone_bounds` skip-list relies on string equality, no test guards future renames

**File:** `app/services/insights_llm.py:339-340` and `tests/services/test_insights_llm.py`

**Issue:**
The line `if metric_id in ("endgame_score_timeline", "non_endgame_score_timeline"): return ""` is the entire mechanism preventing the no-op `[0, 100]` band from leaking into the prompt for the timeline metrics. The Phase 82 rename (`endgame_score` / `non_endgame_score` → `*_timeline`) was applied here in lockstep with the `MetricId` rename in `endgame_zones.py`, but the linkage is name-string equality: a future rename of just one side (the `MetricId` Literal or this skip-list) silently re-enables the bogus `(typical +0 to +100)` tag for the timeline metrics. There is no test asserting `_format_zone_bounds("endgame_score_timeline", None) == ""`.

The matching `endgame_score` (Phase 82's repurposed name) does NOT need to be in the skip-list and is correctly absent — it has a real `[0.45, 0.55]` band — but a future maintainer reading the skip-list cannot tell the two apart from this code alone. The only guardrail is a hand-authored comment at lines 333-337.

**Fix:**
Add direct unit tests:
```python
def test_format_zone_bounds_skips_no_op_timeline_metrics():
    assert _format_zone_bounds("endgame_score_timeline", None) == ""
    assert _format_zone_bounds("non_endgame_score_timeline", None) == ""

def test_format_zone_bounds_renders_for_endgame_score():
    # Phase 82: the repurposed `endgame_score` has a real [0.45, 0.55] band.
    result = _format_zone_bounds("endgame_score", None)
    assert "+45" in result and "+55" in result
```
Optionally, replace the inline tuple with a module-level constant `_NO_BAND_METRICS: frozenset[str]` so the intent is explicit and lint-discoverable.

## Info

### IN-01: Dead defensive guard `entry_eval is None` in `_findings_endgame_start_vs_end`

**File:** `app/services/insights_service.py:451-454`

**Issue:**
```python
n_eval = perf.entry_eval_n
entry_eval = perf.entry_eval_mean_pawns
if n_eval < 10 or entry_eval is None:
```
`EndgamePerformanceResponse.entry_eval_mean_pawns: float = 0.0` (Pydantic schema). The field is non-Optional with a `0.0` default, so `entry_eval is None` is statically False and ty/mypy may already flag it on a stricter run. The accompanying comment ("entry_eval is None only when n_eval < 10 — gate above covers both. Defensive: model_construct callers may omit the field") describes a hypothetical: even with `model_construct`, an omitted `float`-typed field with a `0.0` default produces `0.0`, not `None` — Pydantic does NOT make non-Optional fields None for `model_construct`.

**Fix:**
Drop `or entry_eval is None`. If you want a true defensive guard for `model_construct` paths, check for `0.0`-with-`n_eval < 10` (already covered) or, more useful, NaN: `import math; if math.isnan(entry_eval): ...`. The current guard is dead and the comment is misleading. Or change the schema to `entry_eval_mean_pawns: float | None = None` if "no data" actually needs to be representable separately from "0.0 pawns mean".

### IN-02: Frontend test comment claims `0.46` is "borderline-but-sig" but with a ±0.5 band 0.46 sits 0.04 from the boundary

**File:** `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx:223-241`

**Issue:**
Test name: `'Tile 1 value text is unstyled for value 0.46 + p<0.001 (Phase 82 D-14: user-28 borderline-but-sig case reads neutral, tile and LLM agree)'`. With the tightened ±0.5 band, 0.46 is fully inside the neutral band by 0.04 pawns — that's not "borderline" relative to the band, only relative to the previous ±0.75 / sig-only logic. The label "borderline" is left over from the wider-band era and now misleads anyone trying to understand why the case matters. Behaviorally the test is correct (0.46 < 0.5 → unstyled regardless of significance) but the comment makes it sound like a near-edge case when it is comfortably interior.

**Fix:**
Rephrase the test description: "Tile 1 value text is unstyled for value 0.46 + p<0.001 (Phase 82 D-14: 0.46 sits inside the tightened ±0.5 neutral band, so significance alone does not paint it; tile and LLM agree on neutral)". No code change required.

### IN-03: Boundary cases for tile gating at exactly 10 are not exercised

**File:** `tests/services/test_insights_service.py:759-810` (`TestFindingsEndgameStartVsEnd`)

**Issue:**
Tests cover `entry_eval_n=5` (empty), `entry_eval_n=25` and `entry_eval_n=50` (populated, adequate), and `wins+draws+losses` of 5 and 50. The boundary cases `entry_eval_n == 10` and `endgame_wdl.total == 10` (the exact threshold of the `< 10` gate) are not asserted. The gate uses strict `<`, so `n == 10` should produce a populated finding with sample_quality "adequate" (since `SAMPLE_QUALITY_BANDS["endgame_start_vs_end"] = (10, 50)` is also strict `<` for thin: `9 < 10` → thin, `10 < 50` → adequate). Off-by-one regressions on either gate would slip past the current tests.

**Fix:**
Add two boundary cases to `TestFindingsEndgameStartVsEnd`:
```python
def test_tile1_at_n_eval_10_is_populated_adequate(self) -> None:
    response = self._make_overview(entry_eval_n=10)
    findings = _findings_endgame_start_vs_end(response, "all_time")
    assert findings[0].sample_quality == "adequate"
    assert findings[0].is_headline_eligible is True

def test_tile2_at_total_10_is_populated_adequate(self) -> None:
    response = self._make_overview(wins=5, draws=2, losses=3)  # total=10
    findings = _findings_endgame_start_vs_end(response, "all_time")
    assert findings[1].sample_quality == "adequate"
```
Also add a `test_endgame_start_vs_end_thin_at_9` to `test_endgame_zones.py` to pin the bottom-edge sample_quality boundary (currently only `9` is asserted as thin, which is fine, but a paired `assert sample_quality("endgame_start_vs_end", 10) == "adequate"` would catch a future band shift).

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
