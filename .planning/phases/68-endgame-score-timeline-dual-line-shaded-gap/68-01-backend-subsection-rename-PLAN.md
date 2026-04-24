---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - frontend/src/types/endgames.ts
  - tests/services/test_insights_service.py
  - tests/services/test_insights_service_series.py
  - tests/services/test_insights_llm.py
autonomous: true
requirements: []
tags:
  - insights
  - endgame
  - backend
  - schema
must_haves:
  truths:
    - "SubsectionId enum exposes `score_timeline` (not `score_gap_timeline`)."
    - "compute_findings emits TWO `score_timeline` findings per window, one with dimension={'part':'endgame'} and one with dimension={'part':'non_endgame'}; each carries its own series (endgame_score and non_endgame_score absolute per-bucket values)."
    - "The existing `overall` subsection still emits the aggregate `[summary score_gap]` unchanged."
    - "The rendered subsection payload contains TWO `[summary score_timeline]` blocks (one per `part`) and TWO `[series score_gap, ..., weekly, part=endgame|non_endgame]` blocks — no summary suppression carve-out remains."
    - "The TypeScript `ScoreGapTimelinePoint` interface in `frontend/src/types/endgames.ts` carries the new `endgame_score` and `non_endgame_score` fields so Plan 02 consumes them directly (no fallback arithmetic)."
  artifacts:
    - path: "app/services/endgame_zones.py"
      provides: "SubsectionId enum with `score_timeline` member (renamed from `score_gap_timeline`)"
      contains: 'score_timeline'
    - path: "app/services/insights_service.py"
      provides: "Updated `_findings_score_timeline` builder that returns TWO findings (endgame, non_endgame) per window"
      contains: 'score_timeline'
    - path: "app/services/insights_llm.py"
      provides: "Payload emitter renders `### Subsection: score_timeline` with two `[summary score_timeline]` blocks and two `[series ... part=endgame|non_endgame]` blocks"
      contains: 'score_timeline'
    - path: "frontend/src/types/endgames.ts"
      provides: "Hand-maintained ScoreGapTimelinePoint TS interface extended with endgame_score and non_endgame_score fields"
      contains: 'endgame_score'
  key_links:
    - from: "app/services/insights_service.py::_findings_score_timeline"
      to: "app/services/endgame_zones.py::SubsectionId"
      via: "Literal membership — builder emits subsection_id='score_timeline'"
      pattern: 'subsection_id="score_timeline"'
    - from: "app/services/insights_llm.py::_render_subsection_block"
      to: "compute_findings output"
      via: "score_timeline branch renders two `[series ...]` blocks tagged `part=endgame` / `part=non_endgame` via dimension grouping (same emitter shape as other fanned-out metrics like endgame_elo per-combo)"
      pattern: "part=endgame"
    - from: "frontend/src/types/endgames.ts::ScoreGapTimelinePoint"
      to: "app/schemas/endgames.py::ScoreGapTimelinePoint"
      via: "Hand-maintained mirror — extend both in the same atomic plan so data contracts don't drift"
      pattern: "endgame_score"
---

<objective>
Rename the `score_gap_timeline` subsection to `score_timeline` across the backend findings + LLM payload builder, switch from a single mislabeled `score_gap` series to TWO findings per window (one per `part`) each carrying its own absolute-score series, and extend the hand-maintained frontend TypeScript `ScoreGapTimelinePoint` interface with the two new fields. The `overall` subsection's authoritative `[summary score_gap]` stays untouched. This is the data-layer prerequisite for Plan 02 (frontend two-line chart) and Plan 03 (prompt simplification).

Purpose: The current `score_gap_timeline` series point carries `score_difference` (a subtraction) that's then narrated as if it were a scalar metric — this forced the prompt to carry a special "Framing rule" explaining that gap is a composition. Emitting both absolute series with a standard summary-per-finding shape lets the prompt treat them like every other fanned-out timeline (analogous to `endgame_elo` per-combo fanout).

**CONTEXT.md drift note (W7):** CONTEXT.md casually mentioned "monthly bucketing" and suggested per-bucket field names `bucket_start`, `value`, `n`. The real backend (`_compute_score_gap_timeline` in `app/services/endgame_service.py:529-631`) emits **ISO-weekly** points keyed on the Monday of each ISO week, and the existing schema uses `date`, `endgame_game_count`, `non_endgame_game_count`, `per_week_total_games`. Those CONTEXT.md suggestions are **advisory**; this plan preserves the existing **weekly** bucketing and the existing schema field names for minimal diff. All series-header examples below use `weekly`, not `monthly`.

**B4 decision note — summary shape (option c).** Plan 01 emits exactly two `[summary score_timeline]` blocks per subsection render, one per `part`, matching the same per-dimension fanout shape used by `endgame_elo_timeline`. This removes the Plan 03-claimed "only exception to summary-per-metric rule" carve-out at the emitter level (not in prose). No suppression mechanism. Plan 03's claim "subsection now follows the same emitter shape as every other timeline" becomes literally accurate.

**W5 decision note — MetricId.** `MetricId` already contains `"score_gap"` but NOT `"score"` (verified against `app/services/endgame_zones.py:30-41`). This plan keeps `metric="score_gap"` on BOTH findings to reuse the existing zone mapping (`assign_zone("score_gap", ...)` → `ZoneSpec` at line 119). Do NOT add a new `"score"` MetricId member. The two findings are distinguished by their `dimension={"part": ...}` tag, not by metric.

Output:
- `SubsectionId` enum updated in `app/services/endgame_zones.py` and all downstream type mappings.
- `ScoreGapTimelinePoint` Pydantic schema extended with `endgame_score: float` and `non_endgame_score: float` (both 0.0-1.0 fractional).
- `_compute_score_gap_timeline` in `app/services/endgame_service.py` populates the two new fields on every emitted weekly point.
- New `_findings_score_timeline` finding builder in `app/services/insights_service.py` producing TWO SubsectionFinding rows per window, each with its own per-side `series` and `dimension={"part": "endgame"|"non_endgame"}`.
- Updated `insights_llm.py` payload renderer: drops the `suppress_summary` carve-out, naturally emits two summary blocks + two series blocks via existing per-dimension grouping.
- Frontend TS type in `frontend/src/types/endgames.ts` extended with the two new fields so Plan 02 reads them directly (no defensive fallback).
- Backend unit tests updated so `test_insights_service_series.py` and `test_insights_llm.py` assert the new subsection name, two-findings-per-window shape, and the two-summary + two-series emitter output.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-CONTEXT.md
@CLAUDE.md

<interfaces>
<!-- Key existing types the executor needs. Extracted from codebase. -->

From app/services/endgame_zones.py (lines 30-41):
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
    "win_rate",
]
```
**W5 resolution:** Keep `metric="score_gap"` on both findings — no new `"score"` member needed.

From app/services/endgame_zones.py (line 42-54):
```python
SubsectionId = Literal[
    "overall",
    "score_gap_timeline",   # ← rename to "score_timeline"
    "endgame_metrics",
    "endgame_elo_timeline",
    "time_pressure_at_entry",
    "clock_diff_timeline",
    "time_pressure_vs_performance",
    "conversion_recovery_by_type",
    "type_win_rate_timeline",
    "results_by_endgame_type",
]
```

From app/services/endgame_zones.py (line 208):
```python
SAMPLE_QUALITY_BANDS: Mapping[SubsectionId, tuple[int, int]] = {
    ...
    "score_gap_timeline": (10, 52),   # ← rename key to "score_timeline"
    ...
}
```

From app/schemas/endgames.py (current ScoreGapTimelinePoint):
```python
class ScoreGapTimelinePoint(BaseModel):
    date: str                             # Monday of an ISO week (weekly bucketing)
    score_difference: float               # endgame_score - non_endgame_score (0.0-1.0, signed)
    endgame_game_count: int               # trailing-window n for endgame side
    non_endgame_game_count: int           # trailing-window n for non-endgame side
    per_week_total_games: int
    # NEW (this plan): add `endgame_score: float` and `non_endgame_score: float`
    # so the frontend chart and the insights series can read absolute per-side
    # values directly instead of reconstructing them.
```

From frontend/src/types/endgames.ts (lines 109-119, hand-maintained — no codegen):
```typescript
/** Single point in the score-gap rolling-window time series.
 *  `date` is the Monday of an ISO week (YYYY-MM-DD).
 *  `score_difference` is endgame_score - non_endgame_score on a 0-1 scale (signed). */
export interface ScoreGapTimelinePoint {
  date: string;
  score_difference: number;
  endgame_game_count: number;
  non_endgame_game_count: number;
  // Count of games (endgame + non-endgame) played in THIS specific ISO week.
  // Drives the muted volume-bar series on the Score Gap timeline.
  per_week_total_games: number;
  // NEW (this plan): endgame_score and non_endgame_score — 0-1 fractional.
}
```
**B3 resolution:** this TS interface is hand-maintained (no openapi codegen for it). Plan 01 extends it so Plan 02 can consume `p.endgame_score` / `p.non_endgame_score` directly without a self-referential fallback.

From app/services/endgame_service.py `_compute_score_gap_timeline` (lines 529-631):
- Already emits **weekly** points keyed on the Monday of an ISO week (NOT monthly).
- Inside the inner loop (around line 617) constructs a `data_by_week[(iso_year, iso_week)] = {...}` dict with `score_difference`, `endgame_game_count`, `non_endgame_game_count`, `per_week_total_games`. The `endgame_mean` and `non_endgame_mean` locals (around lines 613-614) are the absolute per-side scores — they already exist, they're just discarded. This plan persists them onto the emitted point.

From app/services/insights_service.py (line 379, 427):
```python
findings.append(_finding_score_gap_timeline(response, window))  # line 379 — replace with .extend(...)

def _finding_score_gap_timeline(response, window) -> SubsectionFinding:   # line 427 — delete, replace
    ...
```

From app/services/insights_llm.py:
- Line ~295: `_TIMELINE_SUBSECTION_IDS` frozenset — rename member.
- Line ~1224: `_SECTION_LAYOUT` overall section layout — rename member.
- Line ~1330: docstring mentions `score_gap_timeline` exception — delete the exception wording.
- Line ~1351: `suppress_summary = subsection_id == "score_gap_timeline"` — **delete this entire branch** (no replacement — the new subsection emits a standard per-finding summary, and two findings means two summaries naturally).
- Lines ~1509, ~1514: comments about score_gap_timeline scalar bullet suppression — scrub.

From app/services/insights_llm.py `_render_series_block` (~line 335):
```python
lines = [f"[series {finding.metric}, {finding.window}, {granularity}]"]
```
The granularity for this subsection is `weekly` (NOT `monthly`), sourced from `_granularity_for_subsection` or the equivalent lookup keyed on subsection_id. Grep confirms: ISO-week bucketing → `weekly`. The existing `_dim_key_for_finding` already folds `dimension={"part": "endgame"}` into a `part=endgame` suffix when the `part` key is present — verify before editing. If the helper does not natively append the `part=` tag on a solo-dim case, add a tiny branch so series headers become `[series score_gap, all_time, weekly, part=endgame]` and `[series score_gap, all_time, weekly, part=non_endgame]`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend ScoreGapTimelinePoint (Python + TS) with absolute per-bucket scores and rebuild the finding as two parts</name>
  <read_first>
    - app/schemas/endgames.py (lines 180-260 — ScoreGapTimelinePoint + sibling schemas)
    - app/services/endgame_service.py (lines 529-631: _compute_score_gap_timeline — verify weekly ISO-week bucketing and locate the endgame_mean / non_endgame_mean locals around lines 613-617)
    - app/services/insights_service.py (lines 90-105, 375-470: SubsectionId list + the score_gap_timeline finding builder)
    - app/services/endgame_zones.py (lines 30-70, 200-220: MetricId + SubsectionId Literals + SAMPLE_QUALITY_BANDS)
    - frontend/src/types/endgames.ts (lines 100-130: ScoreGapTimelinePoint hand-maintained interface)
    - tests/services/test_insights_service_series.py (lines 280-440: score_gap_timeline fixture + assertions)
  </read_first>
  <behavior>
    - Test 1: SubsectionId literal includes "score_timeline" and excludes "score_gap_timeline" (assert a new module-level literal lookup).
    - Test 2: SAMPLE_QUALITY_BANDS exposes "score_timeline" with (10, 52) bounds; "score_gap_timeline" key is gone.
    - Test 3: `_compute_score_gap_timeline` emits `ScoreGapTimelinePoint` entries whose `endgame_score` and `non_endgame_score` floats satisfy `abs((endgame_score - non_endgame_score) - score_difference) < 1e-9` per bucket (identity invariant). Series-header regex for this subsection is `^\[series score_gap, (all_time|last_3mo), weekly, part=(endgame|non_endgame)\]$` — note **weekly**, not monthly.
    - Test 4: `compute_findings(overall)` produces exactly TWO SubsectionFinding rows with `subsection_id="score_timeline"` per window invocation — one with `dimension={"part":"endgame"}`, one with `dimension={"part":"non_endgame"}`; each carries its own `series: list[TimePoint]` built from its own side's per-bucket score; both findings share `metric="score_gap"`.
    - Test 5: Both findings' `value` uses the aggregate `score_difference * 100` (so both zones match — same gap, narrated twice, once per part), derived via `assign_zone("score_gap", ...)`. Non-endgame finding sets `is_headline_eligible=False` so it never becomes a headline on its own.
    - Test 6: Frontend TypeScript compiles — `ScoreGapTimelinePoint` in `frontend/src/types/endgames.ts` has `endgame_score: number` and `non_endgame_score: number` fields. Verify via `cd frontend && npx tsc --noEmit` (or `npm run build`).
  </behavior>
  <action>
    1. **Extend the Pydantic `ScoreGapTimelinePoint` schema** in `app/schemas/endgames.py` (around line 195). Add two float fields with clear docstrings:
       ```python
       endgame_score: float    # 0.0-1.0, absolute rolling-window mean (endgame side)
       non_endgame_score: float  # 0.0-1.0, absolute rolling-window mean (non-endgame side)
       ```
       Keep `score_difference` — it remains a derived convenience field for chart tooltips.

    2. **Update `_compute_score_gap_timeline`** in `app/services/endgame_service.py` (lines 529-631). The per-week dict construction at lines 614-619 already has `endgame_mean` and `non_endgame_mean` locals:
       ```python
       endgame_mean = statistics.mean(endgame_window)
       non_endgame_mean = statistics.mean(non_endgame_window)
       ```
       Persist both onto the emitted point by adding two keys to the `data_by_week[...]` dict:
       ```python
       "endgame_score": round(endgame_mean, 4),
       "non_endgame_score": round(non_endgame_mean, 4),
       ```
       Add a `# sanity:` comment noting the identity `score_difference == endgame_score - non_endgame_score` (within 1e-9). Do NOT raise in production; this is a behavioral invariant covered by Test 3. **Do not change bucketing from weekly to monthly** — the existing ISO-week-keyed points are correct; CONTEXT.md's "monthly" mention was advisory.

    3. **Extend the hand-maintained TypeScript interface** in `frontend/src/types/endgames.ts` (lines 109-119):
       ```typescript
       export interface ScoreGapTimelinePoint {
         date: string;
         score_difference: number;
         endgame_game_count: number;
         non_endgame_game_count: number;
         per_week_total_games: number;
         endgame_score: number;      // 0.0-1.0 absolute endgame-side rolling mean
         non_endgame_score: number;  // 0.0-1.0 absolute non-endgame-side rolling mean
       }
       ```
       Note: both fields are **required** (not optional). Because Plan 02 depends on Plan 01 (wave 2), by the time Plan 02 runs, the backend is emitting them. No fallback needed.

    4. **Rename `SubsectionId` member** in `app/services/endgame_zones.py`:
       - Line 44: replace literal `"score_gap_timeline"` with `"score_timeline"`.
       - Line 210: rename the `SAMPLE_QUALITY_BANDS` key from `"score_gap_timeline"` to `"score_timeline"` (keep the `(10, 52)` tuple unchanged).
       - Scan the file for any docstring mention of `score_gap_timeline` and update.
       - **Do NOT add `"score"` to MetricId** (W5). The two new findings will use the existing `metric="score_gap"`.

    5. **Replace the finding builder** in `app/services/insights_service.py`:
       - Line 98: update the sibling subsection-order list entry `"score_gap_timeline"` → `"score_timeline"`.
       - Delete `_finding_score_gap_timeline` (around lines 427-463) and its single-series construction.
       - Add `_findings_score_timeline(response, window) -> list[SubsectionFinding]` returning a list of TWO findings per window (not one, per B4 option c). Each finding:
         - `subsection_id="score_timeline"`, `metric="score_gap"` (NOT a new `"score"` metric), `window=window`.
         - `value = response.score_gap_material.score_difference * 100` (the aggregate gap %, same on both findings — the summary blocks narrate the same gap twice, once tagged `part=endgame` and once tagged `part=non_endgame`).
         - `zone = assign_zone("score_gap", response.score_gap_material.score_difference * 100)` (same zone on both findings).
         - Finding A (`dimension={"part": "endgame"}`): `series` = list of TimePoint built from `[(p.date, p.endgame_score, p.endgame_game_count) for p in timeline]` via the existing weekly-points-to-time-points helper. `is_headline_eligible = trend != "n_a"` (keep the existing headline rule).
         - Finding B (`dimension={"part": "non_endgame"}`): mirror finding A with `non_endgame_score` and `non_endgame_game_count`. Explicitly set `is_headline_eligible=False` so the prompt never lifts non-endgame as a headline on its own.
       - In `compute_findings`, replace `findings.append(_finding_score_gap_timeline(response, window))` (line 379) with `findings.extend(_findings_score_timeline(response, window))`.

    6. **Type hints**: update any `Literal` reference sites where the old `"score_gap_timeline"` name is hard-coded. The `metric` stays `"score_gap"` so no MetricId Literal change needed.

    7. Run `uv run ty check app/ tests/` and `cd frontend && npx tsc --noEmit` to catch narrowing/type-shape issues before proceeding to Task 2.
  </action>
  <verify>
    <automated>uv run ty check app/ tests/ &amp;&amp; uv run pytest tests/services/test_insights_service.py tests/services/test_insights_service_series.py -x &amp;&amp; (cd frontend &amp;&amp; npx tsc --noEmit)</automated>
  </verify>
  <done>
    - `grep -n "score_timeline" app/services/endgame_zones.py` finds the renamed member and SAMPLE_QUALITY_BANDS key.
    - `grep -n "score_gap_timeline" app/services/endgame_zones.py app/services/insights_service.py` returns zero matches.
    - `grep -n "endgame_score\|non_endgame_score" app/schemas/endgames.py` shows the two new fields on `ScoreGapTimelinePoint`.
    - `grep -n "endgame_score\|non_endgame_score" frontend/src/types/endgames.ts` shows the two new fields on the TS interface.
    - `uv run ty check app/ tests/` exits 0.
    - `cd frontend &amp;&amp; npx tsc --noEmit` exits 0.
    - `uv run pytest tests/services/test_insights_service_series.py -k score_timeline` passes with the new two-findings-per-window assertion.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire the LLM payload emitter for the two-series + two-summary subsection</name>
  <read_first>
    - app/services/insights_llm.py (lines 280-360 for _TIMELINE_SUBSECTION_IDS, lines 1200-1360 for _SECTION_LAYOUT + _render_subsection_block + suppress_summary branch, line ~335 for _render_series_block header format)
    - app/services/insights_llm.py (lines 1470-1530, any comment block referencing score_gap_timeline scalar-bullet suppression)
    - app/services/insights_llm.py (`_dim_key_for_finding` helper — verify it already emits `part=X` on findings carrying `dimension={"part": ...}` so two findings naturally split into two groups)
    - tests/services/test_insights_llm.py (lines 195-260, 340-420, 800-1000, 1050-1150, 1460-1490: every score_gap_timeline reference)
  </read_first>
  <behavior>
    - Test 1: `_assemble_user_prompt(tab)` renders `### Subsection: score_timeline` (not `score_gap_timeline`).
    - Test 2: The rendered subsection contains **TWO** `[summary score_timeline]` blocks per window (one per `part`) — no suppression carve-out remains. Both blocks carry the same `mean` (the aggregate score_gap, narrated twice).
    - Test 3: The rendered subsection contains TWO `[series ...]` blocks per window, each with its `part=` tag: one line matches `^\[series score_gap, [a-z_0-9]+, weekly, part=endgame\]$` (note **weekly**) and another matches `part=non_endgame`. The `part=endgame` block emits first (deterministic order).
    - Test 4: No line in the full prompt output contains the substring `score_gap_timeline` (regression guard).
    - Test 5: The `_SECTION_LAYOUT` `overall` tuple still lists the renamed subsection in the same position.
  </behavior>
  <action>
    1. In `app/services/insights_llm.py`:
       - Line ~295: rename `"score_gap_timeline"` → `"score_timeline"` inside `_TIMELINE_SUBSECTION_IDS`.
       - Line ~1224: rename the `("subsection", "score_gap_timeline")` entry in `_SECTION_LAYOUT`'s `overall` section tuple to `("subsection", "score_timeline")`.
       - Line ~1351: **delete the exception** `suppress_summary = subsection_id == "score_gap_timeline"` entirely (no replacement — per B4 option (c), both findings emit their own summary, producing two `[summary score_timeline]` blocks naturally via the existing per-finding summary loop).
       - Scrub every remaining mention of `score_gap_timeline` in docstrings/comments (~lines 1330, 1509, 1514) to `score_timeline`; delete wording about "the one exception to the summary-per-metric rule" and "the scalar is a mislabeled weekly-latest bucket" — neither applies anymore.

    2. **Verify emitter naturally produces two summaries + two series blocks.** The existing `_render_subsection_block` iterates findings and (for each) emits one summary block and contributes its series to series-block rendering grouped by `(metric, dim_key)`. With two findings sharing `metric="score_gap"` but different `dimension={"part": ...}`:
       - Two findings → two per-finding summary blocks. No code change needed if the existing loop is per-finding (verify via read).
       - Two distinct `dim_key` values → two series groups → two `[series ...]` blocks.
       - **If `_dim_key_for_finding` does not already suffix `part=X` on findings carrying a `part` dimension key**, add a minimal override so series-block headers become `[series score_gap, <window>, weekly, part=endgame]` and `[series score_gap, <window>, weekly, part=non_endgame]`. Reuse the same pattern used by any other subsection that fans out by dimension.

    3. **Deterministic ordering:** ensure the `part=endgame` finding's summary + series emit BEFORE the `part=non_endgame` counterparts. The simplest path is to emit `_findings_score_timeline` in that order (already enforced in Task 1). If the emitter sorts by dim_key alphabetically (`endgame` < `non_endgame`), this is automatic. Add an explicit ordering comment in the finding builder: `# order matters: endgame first so prompt reads "your endgame side first", non_endgame is the partner`.

    4. Update `tests/services/test_insights_llm.py`: every literal assertion on `score_gap_timeline` (search file) must become `score_timeline`. Update the test that previously verified the `[summary]` block was suppressed inside this subsection — now assert TWO `[summary score_timeline]` blocks are present per window. Add a new test asserting:
       - exactly two `[summary score_timeline]` blocks (one per part),
       - exactly two `[series score_gap, ..., weekly, part=endgame|non_endgame]` blocks,
       - endgame block precedes the non_endgame block (deterministic order).

    5. Update `tests/services/test_insights_service_series.py` (lines 280-440) so the fixture builders match the new two-finding shape. Keep the existing coverage of `_TIMELINE_SUBSECTION_IDS` membership.

    6. Run the full insights test subset: `uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py tests/services/test_insights_service.py -x`.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py tests/services/test_insights_service.py -x &amp;&amp; ! grep -rn "score_gap_timeline" app/services/ app/schemas/ tests/services/</automated>
  </verify>
  <done>
    - Full insights test subset passes green.
    - `grep -rn "score_gap_timeline" app/ tests/` returns zero matches (prompt file is handled in Plan 03).
    - `_assemble_user_prompt` rendering of a `score_timeline` subsection contains TWO `[summary score_timeline]` blocks followed by two `[series score_gap, ..., weekly, part=endgame]` / `part=non_endgame` blocks (endgame first).
    - No `suppress_summary` branch remains in `insights_llm.py`.
  </done>
</task>

</tasks>

<verification>
- `uv run ruff check app/ tests/` clean.
- `uv run ty check app/ tests/` clean.
- `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_service_series.py tests/services/test_insights_llm.py -x` passes.
- `cd frontend && npx tsc --noEmit` clean (TS interface extension doesn't break consumers).
- `grep -rn "score_gap_timeline" app/services/ app/schemas/ tests/services/ frontend/src/` returns zero matches.
- `grep -n "score_timeline" app/services/endgame_zones.py` finds the SubsectionId member and SAMPLE_QUALITY_BANDS key.
- `grep -n "suppress_summary" app/services/insights_llm.py` returns zero matches (B4 carve-out deleted).
- The `overall` subsection continues to emit `[summary score_gap]` with the unchanged aggregate (regression guard).
</verification>

<success_criteria>
- Subsection id is `score_timeline` end-to-end (Python enum, Python builder, Python payload emitter, TS type, tests).
- Payload emits TWO `[summary score_timeline]` blocks + two `[series score_gap, ..., weekly, part=endgame|non_endgame]` blocks per window (no suppression carve-out).
- `[summary score_gap]` in the `overall` subsection is untouched.
- `ScoreGapTimelinePoint` Pydantic schema AND the hand-maintained TS interface both carry `endgame_score` and `non_endgame_score` — atomic data-contract rename with no drift.
- Plan 02 can consume `p.endgame_score` and `p.non_endgame_score` directly (no fallback arithmetic) because Plan 02 depends on Plan 01 (wave 2).
- Prompt file (Plan 03) is the only remaining place that still references `score_gap_timeline` — flagged for cleanup in Plan 03.
</success_criteria>

<output>
After completion, create `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md` documenting:
- What was renamed and where (Python + TS).
- The new two-findings payload shape (example snippet with two summary blocks + two series blocks, weekly granularity).
- The ScoreGapTimelinePoint schema extension (both Python and TS).
- Confirmation that no `suppress_summary` carve-out remains.
- Any tradeoffs or follow-ups for Plan 03 (prompt) and Plan 02 (frontend).
</output>
