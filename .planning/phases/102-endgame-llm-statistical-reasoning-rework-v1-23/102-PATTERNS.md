# Phase 102: Endgame LLM Statistical-Reasoning Rework — Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 5 modified files (no new files)
**Analogs found:** 5 / 5 (all are self-analogs — edits to existing files)

---

## D-07 Verification: Ground-Truth Findings (Live Code, Not Summaries)

This is the highest-value output of this mapping pass. The CONTEXT.md flags that prior agents
got payload/frontend claims wrong twice. Everything below is verified against live code.

### 1. `avg_clock_diff_pct` — status in payload

**Present as a scalar finding.**

`insights_service.py:_findings_time_pressure_at_entry` (lines 890-951) emits a `SubsectionFinding`
for `avg_clock_diff_pct` in subsection `time_pressure_at_entry`. It computes an **n-weighted mean**
of `ClockGapBullet.mean_diff_pct * 100` across all `TimePressureTcCard` cards (so it is a single
blended scalar, not a per-TC breakdown). The zone is assigned via `assign_zone("avg_clock_diff_pct", ...)`.

The prompt carries this scalar in `## Section: time_pressure` → `### Subsection: time_pressure_at_entry`.
The system prompt glossary (endgame_insights.md ~line 449-453) describes it and explicitly notes it
is a **weighted mean across TCs** — narrating it per-TC is forbidden.

**What's MISSING from the payload:** no per-TC granularity, no TPCTL percentile annotation, no
`clock_diff_timeline` finding (that helper was removed in Phase 88.1 alongside its data source).

### 2. `net_timeout_rate` — status in payload

**Present as an EMPTY (NaN) finding — always.**

`insights_service.py` line 947-949:
```python
# net_timeout_rate: not available in Phase 88 response shape (removed with
# ClockStatsRow / ClockPressureResponse migration). Always emit empty finding.
findings.append(_empty_finding("time_pressure_at_entry", window, "net_timeout_rate"))
```

The value is always `float("nan")` with `sample_quality="thin"`, so it is filtered OUT
in `_assemble_user_prompt` (the `not math.isnan(f.value)` gate at line ~1818). The LLM
sees no `net_timeout_rate` line at all.

**Source for the actual scalar:** `net_timeout_rate` is available on `TimePressureTcCard`
(endgames.py line 940: `net_timeout_rate: float = 0.0`). It is also on `ClockGapBullet`
style structures. The `_findings_time_pressure_at_entry` function has the `cards` list
available — it can be wired to read `card.net_timeout_rate` similarly to how
`avg_clock_diff_pct` is aggregated. This is a genuine plumbing task.

**What Phase 102 needs to do:** compute a real `net_timeout_rate` scalar (n-weighted across
TC cards, mirroring the `avg_clock_diff_pct` pattern) and assign zone via
`assign_zone("net_timeout_rate", ...)`. The zone band is already registered in
`endgame_zones.py` at `ZONE_REGISTRY["net_timeout_rate"]` (typical ±5%, higher_is_better).

### 3. Score Gap by Remaining Time (per-quintile decomposition) — status in payload

**ABSENT from the payload entirely.**

The `_assemble_user_prompt` function explicitly removed the 10-bucket time-pressure chart block
in Phase 88.1 (insights_llm.py comment at line 1795-1798). The `chart_blocks` dict has no
`time_pressure_vs_performance` key. The `_SECTION_LAYOUT` entry for `time_pressure` (lines 1490-1496)
only contains `("subsection", "time_pressure_at_entry")`.

**Bucket count — verified:** `TimePressureTcCard.quintiles` is typed as
`list[PressureQuintileBullet]  # always 5, ordered Q0..Q4` (endgames.py line 942).
`PressureQuintileBullet.quintile_index` is `0..4` and `quintile_label` is `"0-20%"`, `"20-40%"`,
`"40-60%"`, `"60-80%"`, `"80-100%"` (endgames.py lines 791-792). **CONFIRMED: 5 quintiles, not 4.**
The user said "4 quintiles" but the live code has 5. The CONTEXT.md correctly flagged this to verify.

**Per-quintile score data available:** `PressureQuintileBullet` carries `user_score` and `opp_score`
(the per-quintile Score-Delta), and `n` / `n_opp`. The neutral bands per `(TC, quintile)` are in
`endgame_zones.PRESSURE_BIN_SCORE_NEUTRAL_ZONES`.

**What Phase 102 needs to do:** add a new chart block renderer (analogous to the removed
`_format_time_pressure_chart_block`) that renders the 5×TC per-quintile Score-Delta table, and
add it to `_SECTION_LAYOUT`'s `time_pressure` entry AND to `chart_blocks` in `_assemble_user_prompt`.

### 4. Percentile fields — current location on the API (LLM-05 data source)

Percentile data lives in `EndgameOverviewResponse` (endgames.py ~lines 520-1009), NOT in
`SubsectionFinding`. The planner must confirm which percentile fields are accessible at the
point `compute_findings()` is called (it receives `EndgameOverviewResponse`):

- **Page-level score_gap percentile:** `OverallPerformanceSection.score_gap_percentile` (endgames.py ~line 531)
- **Page-level achievable_score_gap percentile:** `OverallPerformanceSection.achievable_score_gap_percentile` (endgames.py ~line 340)
- **Per-(metric × TC) percentiles on time pressure cards:** `TimePressureTcCard.time_pressure_score_gap_percentile`, `.clock_gap_percentile`, `.net_flag_rate_percentile` (endgames.py ~lines 950-952)
- **Per-TC conv/recov/ΔES percentiles:** on `EndgameMetricsCardBullet` inside `EndgameMetricsCardsResponse` — `.percentile`, `.rate_percentile` (endgames.py ~lines 864-870)

**Key point for the planner:** `SubsectionFinding` has NO `percentile` field today. The percentile
data must either be (a) added as optional fields to `SubsectionFinding`, or (b) plumbed directly
from `EndgameOverviewResponse` in `_assemble_user_prompt` as a separate lookup dict, or (c) passed
via a new structure alongside `EndgameTabFindings`. Option (b) is the lowest-risk non-breaking
approach — it does not touch `SubsectionFinding` serialization or `findings_hash` stability.

---

## File Classification

| Modified File | Role | Data Flow | Pattern Source | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `app/services/insights_llm.py` | service/orchestration | request-response | Self (existing patterns in same file) | Self |
| `app/prompts/endgame_insights.md` | prompt/config | n/a | Self (existing structure) | Self |
| `app/services/insights_service.py` | service | CRUD/transform | Self (existing `_findings_time_pressure_at_entry`) | Self |
| `app/services/endgame_zones.py` | config/registry | n/a | Read-only for this phase | Reference only |
| `app/routers/insights.py` | router | request-response | Read-only for this phase | Reference only |

---

## Pattern Assignments

### `app/services/insights_llm.py` — primary edit site

#### 1. `_PROMPT_VERSION` bump (line 69)

**Existing pattern** (line 69, abbreviated for readability):
```python
_PROMPT_VERSION = "endgame_v35"  # v35 (260517 Phase 87.6 amendment — logistic-anchored stretch): <rationale>. v34 (...): <rationale>. v33 (...): <rationale>. ...
```

**Copy pattern:** Prepend `v36 (YYYYMMDD Phase 102 <one-line rationale>):` to the beginning of the
inline comment. The full prior history stays. Key facts to capture in the rationale:
- percentile annotations added (page-level weighted per metric, TPCTL per time-pressure TC)
- time-pressure narration wired: Score Gap by Remaining Time (per-quintile), Clock Gap, Net Flag Rate
- `overview` cap relaxed to ≤500 words / ≤5 paragraphs when ≥3 distinct narratable signals
- vocabulary audit pass against concepts accordion + tooltip popovers

#### 2. `_NON_FRACTIONAL_METRICS` (lines 103-107)

```python
_NON_FRACTIONAL_METRICS: frozenset[str] = frozenset(
    {"endgame_elo_gap", "avg_clock_diff_pct", "net_timeout_rate", "entry_eval_pawns"}
)
```

`net_timeout_rate` is already in this set (percentage points, not a fraction). New per-quintile
Score-Delta values are fractions (0.0–1.0 scale) and will be multiplied ×100 by the renderer, so
they should NOT be added here.

#### 3. `_SECTION_LAYOUT` (lines 1465-1506)

**Existing `time_pressure` entry** (lines 1490-1496):
```python
(
    "time_pressure",
    [
        ("subsection", "time_pressure_at_entry"),
        # Phase 88.1 (Plan 09, REVIEW.md WR-06): clock-diff timeline subsection
        # and time-pressure-vs-performance chart block removed alongside the
        # corresponding compose_findings entries and chart-block helper.
    ],
),
```

**Copy pattern for Phase 102 addition:** Add `("chart", "time_pressure_score_gap_by_time")` to
the `time_pressure` list alongside `("subsection", "time_pressure_at_entry")`. Also add `("subsection", "clock_diff_timeline")` if re-wiring Clock Gap timeline. Update the comment to reference Phase 102.

#### 4. `chart_blocks` dict in `_assemble_user_prompt` (lines 1797-1800)

**Existing pattern:**
```python
chart_blocks: dict[str, list[str]] = {
    "overall_wdl": overall_wdl_block,
    "results_by_endgame_type_wdl": type_wdl_block,
}
```

**Copy pattern:** Add a new pre-rendered block:
```python
time_pressure_score_gap_block = _format_time_pressure_score_gap_chart_block(findings)
chart_blocks: dict[str, list[str]] = {
    "overall_wdl": overall_wdl_block,
    "results_by_endgame_type_wdl": type_wdl_block,
    "time_pressure_score_gap_by_time": time_pressure_score_gap_block,
}
```

#### 5. New chart-block helper: `_format_time_pressure_score_gap_chart_block`

**Closest analog:** `_format_type_wdl_chart_block` (lines 576-645) — same pattern: iterate over
a collection, filter by minimum games, build a markdown table, prepend header + caption.

**Analog code excerpt** (lines 576-645, abbreviated):
```python
def _format_type_wdl_chart_block(findings: EndgameTabFindings) -> list[str]:
    categories = findings.type_categories
    if not categories:
        return []

    sorted_cats = sorted(...)
    rows: list[str] = []
    for cat in sorted_cats:
        if cat.total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        score_pct = ...
        rows.append(f"| {cat.endgame_class:<12} | ...")

    if not rows:
        return []

    lines: list[str] = [
        "### Chart: results_by_endgame_type_wdl (all_time)",
        "Per-endgame-type W/D/L and Score % for the user. ...",
        "| endgame_class | ... |",
        "| --- | ... |",
    ]
    lines.extend(rows)
    lines.append("")
    return lines
```

**New helper shape:** Iterate over `findings.time_pressure_cards.cards` (the `TimePressureCardsResponse`
on `EndgameTabFindings` — see §6 below). For each `TimePressureTcCard`, emit one sub-table per TC
with columns: `quintile | user_score | opp_score | score_delta | n | n_opp`. Emit the
`(typical LO to UP)` neutral band from `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][quintile_index]` as
inline metadata or a caption note. Skip quintiles where `bullet.user_score is None` (n-gate unmet
per `MIN_GAMES_PER_PRESSURE_BIN`).

**IMPORTANT:** `EndgameTabFindings` currently does NOT carry a `time_pressure_cards` field — it only
has `time_pressure_chart: TimePressureChartResponse | None`. The planner must decide whether to add
`time_pressure_cards` to `EndgameTabFindings`, or pass it separately through from
`compute_findings()` (which receives the full `EndgameOverviewResponse`). See `insights_service.py`
`compute_findings` for the bridging point.

#### 6. Percentile injection into payload bullets

**Existing emission pattern for one metric** — `_summary_window_line` (lines 1019-1067):
```python
parts: list[str] = [f"mean={value_scaled:+.{precision}f}", f"n={finding.sample_size}"]
# ... (bucket / zone / quality / trend / std / within-noise appended conditionally)
zone_part = f"zone={finding.zone}"
if bounds:
    zone_part += f" {bounds}"
parts.append(zone_part)
parts.append(f"quality={finding.sample_quality}")
```

**Copy pattern for adding percentile:** Append `pctl={N:.0f}` after `quality=` when a percentile
value is available for the metric. Because `SubsectionFinding` has no `percentile` field today, the
lookup must come from a separate dict passed into `_assemble_user_prompt` alongside `findings`.
The dict shape: `dict[tuple[str, str | None], float]` where key = `(metric_id, tc_or_None)`.

Example extended line (D-03, D-05):
```
  all_time: mean=+47, n=312, zone=weak (typical +45 to +55), quality=rich, pctl=23 (vs ~1500-rated blitz peers)
```

The cohort framing string `"(vs ~{anchor}-rated {tc} peers)"` should be derived from the
`rating_anchors` dict in `EndgameOverviewResponse` (endgames.py ~line 1003).

---

### `app/prompts/endgame_insights.md` — primary edit site

#### 1. `overview` cap (lines 9 and 190)

**Line 9 current text:**
```
- `overview`: 1-3 short paragraphs totalling at most ~300 words. ALWAYS populate this field...
```

**Line 190 current text:**
```
The overview is 1-3 short paragraphs totalling at most ~300 words. When a cross-section story...
```

**D-08 replacement:** Both occurrences must be updated consistently:
- Default: "~250-300 words, 1-3 paragraphs"
- Extended ceiling (conditional): "up to ~500 words / up to 5 short paragraphs ONLY when ≥3
  distinct, non-overlapping narratable signals exist (e.g. an overall-gap story + a time-pressure
  story + a type-weakness story, each in a non-typical zone)"
- All existing guards preserved: silence-is-not-valid, no-fabrication, within-noise, flat-trend.

#### 2. Percentile narration teaching (new section, placed near/after "Overview rule")

**Analog — existing zone-gate narration teaching:** the existing `[low-time-gap]` tag teaching at
endgame_insights.md ~line 172 (from grep output):
```
**`[low-time-gap] 0-30% buckets, weighted: user=U, opp=O, gap=G — <verdict>`** appears in the
`time_pressure_vs_performance` chart caption. This is the weighted user-vs-opponent Score delta...
Quote this when narrating composure — do not redo the bucket arithmetic yourself.
```

**Copy pattern for percentile teaching:**
- Where percentile appears: `pctl=N` appended after `quality=` on a `[summary]` window line
- Gate rule (D-04): "A `pctl=` value only tells you *where* in the population this metric sits.
  It is NOT a gate on whether to narrate the metric — that remains the `zone` field exclusively.
  A `pctl=5` inside a `zone=typical` finding does NOT open the gate or license narration.
  Percentile informs only *how* you phrase an already-gated finding."
- Framing rule (D-05): "Use cohort framing: 'vs other ~{N}-rated {tc} players' where the anchor
  comes from the payload's cohort disclosure. Do NOT use 'globally' or 'among all players'."
- Example: "Your Conversion sits at 68% — at the 31st percentile vs other ~1400-rated blitz players,
  near the lower edge of the typical 65-77% band."

#### 3. Time-pressure narration section (new teaching block)

**Surfaces to teach:**
1. `### Subsection: time_pressure_at_entry` — `avg_clock_diff_pct` (blended scalar) and
   `net_timeout_rate` (now a real scalar, not empty)
2. New chart block for Score Gap by Remaining Time (5 quintiles per TC)

**Analog — existing per-metric glossary entries** (endgame_insights.md ~lines 449-461 from grep):
```
- **avg_clock_diff_pct** (UI label: "Avg clock diff"): ...
  - Does NOT measure performance under time pressure. For the performance question, read
    the `time_pressure_vs_performance` chart block below.
- **net_timeout_rate** (UI label: "Net timeout rate"): (timeout_wins − timeout_losses) /
  total_endgame_games × 100. Positive = user wins more flag battles (strong)...
```

**What to update:** Remove the reference to `time_pressure_vs_performance` chart (removed in
Phase 88.1). Add teaching for the new Score-Gap-by-time chart. Clarify that `net_timeout_rate`
is now a real scalar (it was always present in the glossary but emitted as empty — now real).
Add TPCTL percentile framing rules for time-pressure metrics (D-06): use direct per-TC percentile,
no game-count weighting.

#### 4. Vocabulary audit targets (D-10)

Two read-only sources to audit against (planner reads these, does NOT modify them):
- `frontend/src/pages/Endgames.tsx` ~lines 382-580: concepts accordion (authoritative label/def source)
- Tooltip bodies: `MetricStatPopover`, `WdlConfidenceTooltip`, `EvalConfidenceTooltip`,
  `AchievableScorePopover`, percentile-chip tooltip

Known drift items to fix in the prompt (from note + prior work):
- The `avg_clock_diff_pct` glossary entry references `[low-time-gap]` verdict which was removed
  in Phase 88.1 — must be purged or replaced with the new quintile chart reference.
- "Endgame Type" vs "Endgame Class" — prompt currently uses both; audit against the accordion.

---

### `app/services/insights_service.py` — targeted edit

#### `_findings_time_pressure_at_entry` (lines 890-951)

**Existing pattern for `avg_clock_diff_pct`** (lines 910-944, copying to wire `net_timeout_rate`):
```python
# avg_clock_diff_pct: n-weighted mean of mean_diff_pct * 100 across TC cards.
diff_num = 0.0
diff_den = 0
for card in cards:
    n = card.clock_gap.n
    if n <= 0:
        continue
    diff_num += card.clock_gap.mean_diff_pct * 100.0 * n
    diff_den += n

if diff_den > 0:
    clock_diff_value = diff_num / diff_den
else:
    clock_diff_value = float("nan")

clock_diff_quality = sample_quality("time_pressure_at_entry", diff_den)
is_headline = clock_diff_quality != "thin"

findings.append(
    SubsectionFinding(
        subsection_id="time_pressure_at_entry",
        parent_subsection_id=None,
        window=window,
        metric="avg_clock_diff_pct",
        value=clock_diff_value,
        zone=assign_zone("avg_clock_diff_pct", clock_diff_value),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=diff_den,
        sample_quality=sample_quality("time_pressure_at_entry", diff_den),
        is_headline_eligible=is_headline and not math.isnan(clock_diff_value),
        dimension=None,
    )
)
```

**Copy this pattern exactly for `net_timeout_rate`.** Source field:
`card.net_timeout_rate` (fraction, already on `TimePressureTcCard`, line 940 of endgames.py).
The `net_timeout_rate` MetricId is in `_NON_FRACTIONAL_METRICS` in insights_llm.py so it is
already on the correct non-fractional scale; no ×100 conversion is needed (it is stored as
a percentage, `(timeout_wins - timeout_losses) / total * 100`). Zone via
`assign_zone("net_timeout_rate", value)`.

Replace the current "always emit empty finding" stub (lines 947-949) with the real computation.

---

### `app/services/endgame_zones.py` — READ ONLY for Phase 102

The zone registry is NOT modified by Phase 102 (D-04). All existing entries needed for the
new surfaces already exist:

| Metric | Registry entry | Band | Notes |
|--------|---------------|------|-------|
| `avg_clock_diff_pct` | `ZONE_REGISTRY` | ±5% (typical) | Already present |
| `net_timeout_rate` | `ZONE_REGISTRY` | ±5% (typical) | Already present |
| `clock_gap_pct` | `ZONE_REGISTRY` | (-6.5%, +4.7%) asymmetric | Already present (note: this is the per-TC clock-gap %, distinct from blended `avg_clock_diff_pct`) |
| `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | mapping by (TC, quintile) | per-cell asymmetric ±6% cap | Already calibrated (lines 648-700) |

---

## Shared Patterns

### Zone-as-gate (D-04) — applied everywhere

**Source:** `endgame_zones.py:assign_zone` (line 783-793) + existing prompt rule at
endgame_insights.md ~line 192 (`avg_clock_diff_pct` weak + low-time-gap verdict story).

The gate pattern throughout the existing code is: `is_headline_eligible = quality != "thin"` and
zone assigned via `assign_zone()`. Percentile informs only the *phrasing* after the gate fires.
The planner must not add any `if percentile < threshold: narrate` logic — it must not exist
anywhere in the payload or prompt.

### Empty finding sentinel

**Source:** `insights_service.py:_empty_finding` (called at lines 906-907). When a metric has no
data, a `value=nan, quality=thin, is_headline_eligible=False` finding is emitted and then filtered
out by the NaN gate in `_assemble_user_prompt` line ~1818. This is the correct "no data" pattern —
do not suppress by not emitting; emit + let the filter gate it.

### `_NON_FRACTIONAL_METRICS` (insights_llm.py lines 103-107)

Metrics on non-fractional scales (Elo, percentage points, pawns) are listed here and get
`scale=1.0` rather than ×100. Before adding any new metric to the payload, check whether it is
already a percentage (like `net_timeout_rate` and `avg_clock_diff_pct`) and add to this set if so.

### Comment header for Phase 88.1 removals (pattern for Phase 102 additions)

```python
# Phase 88.1 (Plan 09, REVIEW.md WR-06): <thing> removed alongside <reason>.
```

Use `# Phase 102 (Plan NN, ...): <thing> added. <one-line rationale>.` as the symmetric pattern
for additions. Every structural change has a comment citing the phase.

---

## No Analog Found

No files in this phase are genuinely new (no file without a codebase precedent). The two
functional additions (per-quintile chart block, net_timeout_rate real computation) both have
direct analogs as documented above.

---

## Metadata

**Analog search scope:** `app/services/`, `app/prompts/`, `app/schemas/`, `app/routers/`
**Files scanned:** `insights_llm.py` (2191 lines), `endgame_zones.py` (855 lines),
`insights_service.py` (partial, ~960 lines), `endgame_insights.md` (partial), `insights.py` schema
**Pattern extraction date:** 2026-06-01
