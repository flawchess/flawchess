---
phase: 260422-tnb
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - app/services/insights_prompts/endgame_v1.md
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "The generated user prompt contains exactly ONE metric per endgame_metrics bucket (3 bucket rows total, plus 1 endgame_skill composite) — no cross-bucket fan-out."
    - "The generated user prompt contains no NaN values and no rows with `sample_size=0 AND sample_quality=thin`."
    - "Every LlmLog row has `response_json.model_used == settings.PYDANTIC_AI_MODEL_INSIGHTS` and `response_json.prompt_version == \"endgame_v2\"` — values set server-side, never from the LLM."
    - "Tier-1 cache misses for all previously cached endgame reports (prompt_version changed from endgame_v1 to endgame_v2). Intentional per CONTEXT.md D-08."
    - "Timeline series points with `n < 3` are filtered out before being serialized to the LLM."
    - "The system prompt contains an auto-generated zone-threshold appendix listing numeric bands for each metric, sourced from ZONE_REGISTRY / BUCKETED_ZONE_REGISTRY."
    - "The system prompt explicitly maps subsection_ids to SectionId enum values."
    - "The `time_pressure_vs_performance` subsection is not included in the user prompt (UI chart is self-contained — avoids metric-label confusion)."
  artifacts:
    - path: app/services/insights_service.py
      provides: "Bucket-matched metric emission in _findings_endgame_metrics (3 rows, not 9)"
    - path: app/services/insights_llm.py
      provides: "NaN/thin filter, server-side report field override, min-n series filter, grouped subsection headers, zone-threshold appendix generator, time_pressure_vs_performance skip, _PROMPT_VERSION='endgame_v2'"
    - path: app/services/insights_prompts/endgame_v1.md
      provides: "Rewritten system prompt: single length rule, tighter trend guidance, TC-weighting caveat, single-bucket glossary, subsection→section_id map, no echo-back instructions"
  key_links:
    - from: app/services/insights_llm.py
      to: app/services/endgame_zones.py
      via: "module-load import of ZONE_REGISTRY + BUCKETED_ZONE_REGISTRY to build zone appendix"
      pattern: "from app.services.endgame_zones import ZONE_REGISTRY"
    - from: app/services/insights_llm.py (generate_insights, post-_run_agent)
      to: EndgameInsightsReport.model_copy(update=...)
      via: "server-side override of model_used + prompt_version"
      pattern: "report.model_copy.*model_used"
---

<objective>
Fix the endgame insights pipeline so the LLM receives clean, semantically consistent data and returns reports with accurate metadata. Address fixes A1–A5, B1–B6, C1–C3 from the approved analysis at `/home/aimfeld/.claude/plans/let-s-look-at-the-synthetic-neumann.md`. Bump `_PROMPT_VERSION` to `endgame_v2` to invalidate tier-1 cache (intentional — old reports were generated from the broken prompt).

Purpose: The current `insights.endgame` output has three categorical defects — (1) fabricated `model_used` ("gpt-4o" appears in Gemini outputs), (2) self-contradictory bucket×metric fan-out causing the LLM to narrate "parity score rates are strong across several categories" for conversion/recovery data, (3) NaN leaks into the user prompt. This plan addresses all three plus seven prompt hygiene items in one cohesive change.

Output: Modified service + prompt files. Cache invalidation via prompt_version bump. Existing tests updated. New test coverage for the NaN filter, single-metric-per-bucket emission, and server-side metadata override.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@/home/aimfeld/.claude/plans/let-s-look-at-the-synthetic-neumann.md
@app/services/insights_prompts/endgame_v1.md
@app/services/insights_llm.py
@app/services/insights_service.py
@app/services/endgame_zones.py
@app/schemas/insights.py

<interfaces>
<!-- Key contracts the executor needs. -->

From app/schemas/insights.py:
```python
class SubsectionFinding(BaseModel):
    subsection_id: SubsectionId
    parent_subsection_id: SubsectionId | None = None
    window: Window
    metric: MetricId
    value: float  # may be float('nan') for empty findings
    zone: Zone
    trend: Trend
    weekly_points_in_window: int
    sample_size: int
    sample_quality: SampleQuality  # "thin" | "adequate" | "rich"
    is_headline_eligible: bool
    dimension: dict[str, str] | None = None
    series: list[TimePoint] | None = None

class TimePoint(BaseModel):
    bucket_start: str   # ISO YYYY-MM-DD
    value: float
    n: int

class EndgameInsightsReport(BaseModel):
    overview: str
    sections: list[SectionInsight] = Field(..., min_length=1, max_length=4)
    model_used: str
    prompt_version: str
```

From app/services/endgame_zones.py:
```python
ZONE_REGISTRY: Mapping[MetricId, ZoneSpec]        # scalar metrics
BUCKETED_ZONE_REGISTRY: Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]]

@dataclass(frozen=True)
class ZoneSpec:
    typical_lower: float
    typical_upper: float
    direction: Literal["higher_is_better", "lower_is_better"]
```

`MetricId` Literal set (fixed — do NOT add new metric ids in this plan):
`"score_gap" | "endgame_skill" | "conversion_win_pct" | "parity_score_pct" | "recovery_save_pct" | "avg_clock_diff_pct" | "net_timeout_rate" | "endgame_elo_gap" | "win_rate"`

Current `_findings_endgame_metrics` (insights_service.py:272-398) emits for each MaterialRow:
1. conversion_win_pct (from row.win_pct / 100)
2. parity_score_pct (from row.score)
3. recovery_save_pct (from (row.win_pct + row.draw_pct) / 100)

This is the 3×3 fan-out bug. Per the glossary, each metric is tied to exactly ONE bucket. Fix: dispatch on `row.bucket` and emit only the matching metric.

`MIN_BUCKET_N = 3` — use this named constant for the A4 series filter.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Data-emission + prompt-assembly fixes (A1–A5, C1–C3)</name>
  <files>
    app/services/insights_service.py,
    app/services/insights_llm.py,
    tests/services/test_insights_service.py,
    tests/services/test_insights_llm.py
  </files>
  <behavior>
    - `_findings_endgame_metrics` emits endgame_skill (1 finding) + per-bucket matching metric (1 finding per MaterialRow). For an input with 3 MaterialRows (conversion/parity/recovery), it emits exactly 4 findings, not 10.
    - Empty-bucket path (bucket_games == 0) emits ONE empty finding for the bucket's matching metric, not three.
    - `_assemble_user_prompt` drops any finding f where `math.isnan(f.value)` OR `(f.sample_size == 0 AND f.sample_quality == "thin")`.
    - `_assemble_user_prompt` skips findings with `subsection_id == "time_pressure_vs_performance"` entirely (UI chart self-contained, metric label is misleading per A5).
    - `_assemble_user_prompt` groups findings by `subsection_id`: one `## Subsection: {id}` header, followed by each finding as a bullet under it. Series blocks (for timeline subsections) attach to their respective bullets.
    - Series points with `n < MIN_BUCKET_N` (= 3) are filtered out before rendering.
    - When two consecutive retained series points are >90 days apart, insert a comment line `# Activity gap: {prev.bucket_start} → {pt.bucket_start}` between them.
    - When a series has both `all_time` and `last_3mo` variants for the same metric+subsection, drop the last 3 months of the `all_time` series (points with bucket_start within 90 days of today). Implemented at serialize time since each finding carries its own series; use `datetime.date.today() - timedelta(days=90)` as the cutoff.
    - `generate_insights` overrides `report.model_used` and `report.prompt_version` server-side AFTER `_run_agent` returns successfully, via `report = report.model_copy(update={"model_used": model, "prompt_version": _PROMPT_VERSION})`. The override must happen before `create_llm_log` is called so the log row stores the corrected fields.
    - `_PROMPT_VERSION` constant in insights_llm.py is `"endgame_v2"`.
  </behavior>
  <action>
    **A1 — insights_service.py `_findings_endgame_metrics` (lines 272-398):**
    Replace the three-findings-per-row block (lines 315-396) with a dispatch on `row.bucket`:
    - `row.bucket == "conversion"` → emit ONE `conversion_win_pct` finding, value = `row.win_pct / 100.0`, zone = `assign_bucketed_zone("conversion_win_pct", "conversion", value)`.
    - `row.bucket == "parity"` → emit ONE `parity_score_pct` finding, value = `row.score`.
    - `row.bucket == "recovery"` → emit ONE `recovery_save_pct` finding, value = `(row.win_pct + row.draw_pct) / 100.0`.
    - For the `bucket_games == 0` branch: emit ONE `_empty_finding` for the bucket's matching metric (use the same dispatch). Retain `bucket_dim = {"bucket": bucket}`.

    Define a module-level helper near the top of the section:
    ```python
    _BUCKET_TO_METRIC: dict[MaterialBucket, BucketedMetricId] = {
        "conversion": "conversion_win_pct",
        "parity": "parity_score_pct",
        "recovery": "recovery_save_pct",
    }
    ```
    Import `BucketedMetricId` from `app.services.endgame_zones` if not already imported.

    **A2 + C1 + C2 + C3 + A4 + A5 — insights_llm.py `_assemble_user_prompt`:**
    Rewrite the function. Keep `_format_filters_for_prompt` unchanged. New structure:
    1. Add module-level constant `MIN_BUCKET_N: int = 3` and `_ALL_TIME_CUTOFF_DAYS: int = 90` and `_ACTIVITY_GAP_DAYS: int = 90` and `_SKIPPED_SUBSECTIONS: frozenset[str] = frozenset({"time_pressure_vs_performance"})`.
    2. Add `import math` and `import datetime` at module top if not already imported (datetime IS; add math).
    3. Filter findings first:
       ```python
       visible = [
           f for f in findings.findings
           if f.subsection_id not in _SKIPPED_SUBSECTIONS
           and not math.isnan(f.value)
           and not (f.sample_size == 0 and f.sample_quality == "thin")
       ]
       ```
    4. Group by `subsection_id` preserving first-seen order:
       ```python
       from collections import OrderedDict
       groups: OrderedDict[str, list[SubsectionFinding]] = OrderedDict()
       for f in visible:
           groups.setdefault(f.subsection_id, []).append(f)
       ```
    5. For each group: render `## Subsection: {subsection_id}` header once, then bullets. Include parent info parenthetically on the header when any finding in the group has a parent_subsection_id (take from first).
    6. Bullet format unchanged: `- {metric} ({window}): {value:+.2f} | {zone} | {sample_size} games | {sample_quality}{dim}`.
    7. For series rendering: keep the existing resolution logic. Filter points with `pt.n >= MIN_BUCKET_N`. For `window == "all_time"` series, additionally drop points with `bucket_start >= (today - 90 days).isoformat()` IF the same metric+subsection appears with `window == "last_3mo"` elsewhere in `visible`. Compute a set `{(f.metric, f.subsection_id) for f in visible if f.window == "last_3mo"}` once and reuse.
    8. Activity-gap markers: iterate retained series points pairwise, parse `bucket_start` via `datetime.date.fromisoformat`, if `(curr - prev).days > _ACTIVITY_GAP_DAYS`, insert `f"# Activity gap: {prev.bucket_start} → {pt.bucket_start}"` line between them.

    **A3 — insights_llm.py `generate_insights`:**
    Change `_PROMPT_VERSION = "endgame_v1"` to `_PROMPT_VERSION = "endgame_v2"` (line 54).

    After `_run_agent` returns (line 388-390), before `create_llm_log`, when report is not None, override metadata:
    ```python
    if report is not None:
        report = report.model_copy(update={
            "model_used": model,
            "prompt_version": _PROMPT_VERSION,
        })
    ```
    Insert this between the `_run_agent` call and the `create_llm_log` call so the log row persists the corrected values.

    **Tests — tests/services/test_insights_service.py:**
    Update any existing tests asserting `_findings_endgame_metrics` emits 9 bucket×metric findings. After the fix it emits 3 (plus 1 endgame_skill). Adjust count assertions. Add a focused test: given a fixture with 3 MaterialRows (one per bucket, each with non-zero games), assert the returned findings list has length 4, and that each (subsection_id="endgame_metrics", dimension={"bucket": X}) finding has `metric == _BUCKET_TO_METRIC[X]`.

    **Tests — tests/services/test_insights_llm.py:**
    Add three focused tests for `_assemble_user_prompt`:
    1. `test_assemble_user_prompt_drops_nan_findings`: input with one normal finding + one _empty_finding (NaN, thin, n=0). Output does NOT contain "nan" or "+nan". Output contains exactly one bullet line.
    2. `test_assemble_user_prompt_groups_by_subsection`: input with 3 findings all under `endgame_metrics`. Output contains exactly ONE `## Subsection: endgame_metrics` header, followed by 3 bullets.
    3. `test_assemble_user_prompt_filters_sparse_series_points`: input with a `score_gap_timeline` finding whose series has points with n=[1, 5, 2, 10]. Output series section contains only the n=5 and n=10 points.

    Add one test for `generate_insights` metadata override: mock `_run_agent` to return a report with `model_used="FABRICATED"` and `prompt_version="WRONG"`; assert the response's report has `model_used == settings.PYDANTIC_AI_MODEL_INSIGHTS` and `prompt_version == "endgame_v2"`. Use the same mocking pattern as existing generate_insights tests (check file for the established fixture style).

    **Important: DO NOT add a new MetricId for time_pressure_vs_performance in this task.** The `MetricId` Literal is locked per schema contract. The subsection is simply dropped from the LLM payload — the UI still renders its own chart from the raw data.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run ruff check . &amp;&amp; uv run ty check app/ tests/ &amp;&amp; uv run pytest tests/services/test_insights_service.py tests/services/test_insights_llm.py -x</automated>
  </verify>
  <done>
    - Ruff + ty pass with zero errors.
    - All existing + new tests pass.
    - Grepping the generated user prompt (via a test or manual script) for `parity_score_pct.*\[bucket=conversion` returns zero matches.
    - `_PROMPT_VERSION == "endgame_v2"` confirmed by grep.
    - `report.model_used` and `report.prompt_version` are overridden server-side (grep for `model_copy.*model_used` near generate_insights).
    - A round-trip integration: running the insights call in dev and checking the `llm_logs` row via `mcp__flawchess-db__query` shows `response_json->>'model_used'` equals the configured Gemini model (not a fabricated OpenAI string).
  </done>
</task>

<task type="auto">
  <name>Task 2: System-prompt rewrite (B1, B3, B4, B5, B6) + auto-generated zone appendix (B2)</name>
  <files>
    app/services/insights_prompts/endgame_v1.md,
    app/services/insights_llm.py
  </files>
  <behavior>
    - `endgame_v1.md` has a single length rule for `overview` (1-2 short paragraphs totalling ≤150 words).
    - `endgame_v1.md` glossary states each bucketed metric is tied to exactly one bucket (no cross-bucket fan-out claim).
    - `endgame_v1.md` includes a trend-strength rule: a trend requires ≥5 buckets AND the sum of n across the last 3-4 buckets must be ≥ ~20; single-bucket values must not be called alignment/direction.
    - `endgame_v1.md` includes a note that `avg_clock_diff_pct` is weighted across time controls — do not attribute to a single format unless a `time_control` filter is set.
    - `endgame_v1.md` maps subsection_ids → section_ids explicitly:
      - `overall` → `overall`
      - `score_gap_timeline`, `endgame_metrics`, `endgame_elo_timeline` → `metrics_elo`
      - `time_pressure_at_entry`, `clock_diff_timeline` → `time_pressure`
      - `results_by_endgame_type`, `conversion_recovery_by_type`, `type_win_rate_timeline` → `type_breakdown`
    - `endgame_v1.md` removes both `echo back` instructions from the output contract (server-side override handles them).
    - `_SYSTEM_PROMPT` at module load is the markdown file contents + a deterministic `## Zone thresholds` appendix auto-generated from `ZONE_REGISTRY` + `BUCKETED_ZONE_REGISTRY`.
    - The appendix format per metric: `- metric_id: weak<{low}, typical [{low}, {high}], strong>{high}` (or inverted for `lower_is_better`). Bucketed metrics list each bucket's band indented beneath.
  </behavior>
  <action>
    **Rewrite `app/services/insights_prompts/endgame_v1.md`:**

    Keep the v1 header. (File name stays `endgame_v1.md` — the cache key is `_PROMPT_VERSION` which is already bumped to `endgame_v2`, so renaming the file is optional and unnecessary. Document this decision inline with a comment at the top of the file: `<!-- Note: file name retained as endgame_v1.md; prompt_version constant in insights_llm.py is the authoritative cache key. -->`).

    Apply these edits:

    1. **B1 — Output contract (line 7-13):** Replace `overview: a single paragraph of at most 150 words...` with:
       > `overview`: 1-2 short paragraphs totalling at most 150 words. ALWAYS populate this field — never return an empty string, never return null. When no strong cross-section signal is present, summarize the per-section findings instead. Silence is not a valid output.

       Remove lines 12-13 (`model_used: echo back...` and `prompt_version: echo back...`). Keep the schema field in the JSON contract but note: `model_used` and `prompt_version`: populate with placeholder strings (server will override). Do not try to infer the real model name.

       Replace the "Overview rule" section (lines 25-27) with the same single 1-2-paragraph rule so it matches the output contract.

    2. **B3 — Series interpretation (lines 20-23):** Augment with:
       > Do NOT claim a trend, direction, or alignment from a single bucket, or from buckets that are mostly n<5. Sum the `n` of the last 3-4 buckets — if that total is under ~20, describe the metric as having insufficient recent data rather than inferring direction.

    3. **B4 — Glossary `avg_clock_diff_pct` entry (around line 60):** Add:
       > Note: `avg_clock_diff_pct` is a weighted mean across bullet/blitz/rapid/classical. Do NOT attribute the deficit or surplus to any single time control unless a `time_control` filter is set (check the `Filters:` header).

    4. **B5 — Glossary bucket metrics (lines 40-50):** Rewrite the three bucketed entries so each says "Tied to exactly one bucket":
       - `conversion_win_pct`: Tied to the **conversion** bucket only. The `dimension.bucket` field will always be `"conversion"` for this metric; other buckets' conversion performance is not emitted.
       - `parity_score_pct`: Tied to the **parity** bucket only.
       - `recovery_save_pct`: Tied to the **recovery** bucket only.
       Remove "Bucketed like conversion_win_pct" lines.

    5. **B6 — Add new section before "Tone":**
       ```
       ## Subsection → section_id mapping

       Each subsection in the user prompt belongs to exactly one output section. Emit at most one SectionInsight per section_id, aggregating insights from all its subsections:

       | Subsection | section_id |
       |---|---|
       | overall | overall |
       | score_gap_timeline | metrics_elo |
       | endgame_metrics | metrics_elo |
       | endgame_elo_timeline | metrics_elo |
       | time_pressure_at_entry | time_pressure |
       | clock_diff_timeline | time_pressure |
       | results_by_endgame_type | type_breakdown |
       | conversion_recovery_by_type | type_breakdown |
       | type_win_rate_timeline | type_breakdown |

       Subsections not in this table (e.g. `time_pressure_vs_performance`) will not appear in your user prompt; the frontend renders them directly.
       ```

    **B2 — insights_llm.py zone-threshold appendix:**

    Add a helper near the top of insights_llm.py (after `_PROMPTS_DIR` and before `_SYSTEM_PROMPT` load):

    ```python
    def _build_zone_threshold_appendix() -> str:
        """Render ZONE_REGISTRY + BUCKETED_ZONE_REGISTRY as a markdown appendix.

        Auto-generated at module load so the LLM always sees the current numeric
        bands. Kept separate from the hand-authored system-prompt markdown so
        prompt-version bumps aren't required when thresholds change (the cache
        key is findings_hash + prompt_version + model — threshold changes
        propagate via findings_hash since zones are baked into findings).
        """
        from app.services.endgame_zones import ZONE_REGISTRY, BUCKETED_ZONE_REGISTRY
        lines: list[str] = ["", "## Zone thresholds", ""]
        lines.append("Numeric bands for each metric (auto-generated — do not contradict).")
        lines.append("")
        for metric_id, spec in ZONE_REGISTRY.items():
            if spec.direction == "higher_is_better":
                lines.append(
                    f"- `{metric_id}`: weak<{spec.typical_lower:.2f}, "
                    f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                    f"strong>{spec.typical_upper:.2f}"
                )
            else:
                lines.append(
                    f"- `{metric_id}` (lower_is_better): strong<={spec.typical_lower:.2f}, "
                    f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                    f"weak>{spec.typical_upper:.2f}"
                )
        lines.append("")
        lines.append("Bucketed metrics (one band per MaterialBucket):")
        for metric_id, buckets in BUCKETED_ZONE_REGISTRY.items():
            lines.append(f"- `{metric_id}`:")
            for bucket, spec in buckets.items():
                lines.append(
                    f"  - {bucket}: weak<{spec.typical_lower:.2f}, "
                    f"typical [{spec.typical_lower:.2f}, {spec.typical_upper:.2f}], "
                    f"strong>{spec.typical_upper:.2f}"
                )
        return "\n".join(lines) + "\n"

    _SYSTEM_PROMPT = (
        (_PROMPTS_DIR / "endgame_v1.md").read_text(encoding="utf-8")
        + _build_zone_threshold_appendix()
    )
    ```

    Move the `ZONE_REGISTRY` / `BUCKETED_ZONE_REGISTRY` import to the top of the file alongside other imports (cleaner than the function-local import above — use the function-local version only if circular-import issues appear). Prefer the top-level import.

    **Verify no test regressions**: existing tests that assert `_SYSTEM_PROMPT` equals raw file contents need updating. Search:
    ```bash
    grep -rn "_SYSTEM_PROMPT\|endgame_v1.md" tests/
    ```
    If any test asserts equality with the file contents, update it to `assert _SYSTEM_PROMPT.startswith(file_contents)` and additionally `assert "## Zone thresholds" in _SYSTEM_PROMPT`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run ruff check . &amp;&amp; uv run ty check app/ tests/ &amp;&amp; uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service.py -x</automated>
  </verify>
  <done>
    - Ruff + ty pass.
    - All tests pass.
    - `grep -c "echo back" app/services/insights_prompts/endgame_v1.md` returns 0.
    - `grep -c "Zone thresholds" app/services/insights_llm.py` returns ≥1 (the appendix builder).
    - `grep -c "Subsection → section_id mapping" app/services/insights_prompts/endgame_v1.md` returns 1.
    - Running `python -c "from app.services.insights_llm import _SYSTEM_PROMPT; print(_SYSTEM_PROMPT)"` shows the rewritten prompt with the zone-threshold appendix appended.
    - A subsequent manual `/api/insights/endgame` call (cache-missed because of prompt_version bump) returns a report where `model_used` matches the configured Gemini model and no `[bucket=conversion]` fan-out appears in `llm_logs.user_prompt`.
  </done>
</task>

</tasks>

<verification>
Overall phase checks after both tasks:

1. `cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check .` — zero errors.
2. `cd /home/aimfeld/Projects/Python/flawchess && uv run ty check app/ tests/` — zero errors.
3. `cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service.py tests/services/test_insights_service_series.py -x` — all pass.
4. Manual smoke: start dev DB + backend, trigger `/api/insights/endgame` with a real user session, check the new `llm_logs` row:
   ```sql
   SELECT prompt_version, response_json->>'model_used', response_json->>'prompt_version'
   FROM llm_logs WHERE endpoint = 'insights.endgame' ORDER BY created_at DESC LIMIT 1;
   ```
   Expect: `prompt_version = 'endgame_v2'`, `response_json.model_used` = configured model string, `response_json.prompt_version = 'endgame_v2'`.
5. Inspect `llm_logs.user_prompt` of the same row:
   - No `+nan` substrings.
   - No `parity_score_pct.*\[bucket=conversion` or `recovery_save_pct.*\[bucket=conversion` matches.
   - One `## Subsection: endgame_metrics` header, followed by at most 4 bullets (1 endgame_skill + up to 3 bucket rows).
   - No `## Subsection: time_pressure_vs_performance` header.
6. Inspect `llm_logs.system_prompt` of the same row: contains `## Zone thresholds` section with `conversion_win_pct` bucketed entries.
</verification>

<success_criteria>
- [ ] `_findings_endgame_metrics` emits 1 + N findings (N = number of non-zero MaterialRows), not 1 + 3N.
- [ ] `_assemble_user_prompt` drops NaN/thin-empty findings, skips `time_pressure_vs_performance`, groups by subsection, filters series points with `n < 3`, inserts activity-gap markers.
- [ ] `generate_insights` overrides `report.model_used` and `report.prompt_version` server-side before logging.
- [ ] `_PROMPT_VERSION == "endgame_v2"`.
- [ ] `endgame_v1.md` has a single length rule, single-bucket glossary entries, TC-weighting caveat, subsection→section_id map, no echo-back instructions, tighter trend guidance.
- [ ] `_SYSTEM_PROMPT` at module load includes auto-generated `## Zone thresholds` appendix sourced from ZONE_REGISTRY + BUCKETED_ZONE_REGISTRY.
- [ ] Ruff + ty + pytest all clean.
- [ ] Manual smoke confirms the reviewed user's next insights call is free of the 3 defects seen in the original report (no fabricated model_used, no "parity strong" hallucination from conversion data, no NaN rows).
</success_criteria>

<output>
No SUMMARY.md required (this is a `/gsd:quick` task, not a full GSD phase). After both tasks verify green, the work is complete. The prompt_version bump is the intended cache invalidation — users will pay a one-time tier-1 miss on their next endgame insights call.
</output>
