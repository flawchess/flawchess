---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 03
type: execute
wave: 3
depends_on:
  - 68-01
files_modified:
  - app/prompts/endgame_insights.md
  - app/services/insights_llm.py
autonomous: true
requirements: []
tags:
  - insights
  - endgame
  - prompt
must_haves:
  truths:
    - "The `score_gap` framing rule block at ~line 290 of `app/prompts/endgame_insights.md` is removed."
    - "The `score_gap_timeline` 'one exception to the summary-per-metric rule' paragraph at ~line 139 is removed."
    - "Every mention of `score_gap_timeline` in the prompt file is replaced with `score_timeline`, and the `Subsection → section_id mapping` table row is updated."
    - "The prompt's emitter-shape documentation describes the new `score_timeline` subsection as emitting TWO `[summary score_timeline]` blocks + TWO `[series score_gap, <window>, weekly, part=endgame|non_endgame]` blocks — matching the same fanned-out shape used by other per-dimension subsections."
    - "`_PROMPT_VERSION` in `app/services/insights_llm.py` is bumped from `endgame_v12` to `endgame_v13` with an updated comment describing the v13 change."
    - "Cached LLM reports from prior prompt versions do not surface — cache is keyed on prompt_version so the bump invalidates them naturally."
  artifacts:
    - path: "app/prompts/endgame_insights.md"
      provides: "Simplified prompt without the score_gap framing rule and without the score_gap_timeline exception; documents the new two-summary + two-series emitter shape"
    - path: "app/services/insights_llm.py"
      provides: "_PROMPT_VERSION = 'endgame_v13' with v13 change comment"
      contains: 'endgame_v13'
  key_links:
    - from: "app/services/insights_llm.py::_PROMPT_VERSION"
      to: "llm_logs cache key"
      via: "get_latest_log_by_hash(..., prompt_version, model) — Phase 65 cache key design"
      pattern: '_PROMPT_VERSION = "endgame_v13"'
---

<objective>
Simplify the endgame insights system prompt now that the two-line chart (Plan 02) makes gap composition self-evident, and update the prompt's subsection-id references to match the Plan 01 rename. Bump the prompt version so cached LLM reports invalidate.

Purpose: The prompt has carried a special `score_gap` framing rule ("read overall_wdl first, lead with strong non-endgame or weak endgame depending on which side is above/below thresholds") because the old single-line `score_gap` series hid composition. The new two-line chart renders composition directly, and the prompt's `overall_wdl` chart block + aggregate `[summary score_gap]` already give the LLM enough to narrate the gap neutrally. The rule becomes redundant scaffolding and should be removed.

Same for the `score_gap_timeline` "only exception to summary-per-metric" carve-out — Plan 01 (per B4 option c in the revision) makes the subsection emit TWO standard `[summary score_timeline]` blocks (one per `part`) via the existing per-dimension fanout, NOT via any custom emitter carve-out. The subsection now follows the same shape as every other fanned-out timeline (e.g. `endgame_elo` per-combo). Plan 03's claim "follows the same emitter shape" is accurate at the code level.

Output:
- Edited `app/prompts/endgame_insights.md` with the two removals, the subsection-id rename, the new emitter-shape documentation (two summaries + two series), and any narrative examples that referenced the old id.
- Bumped `_PROMPT_VERSION` in `app/services/insights_llm.py` with a comment describing the v13 delta (scaffolding removal, subsection rename, two-summary shape).
- A regression test in `tests/services/test_insights_llm.py` asserting the new version string.
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
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md
@app/prompts/endgame_insights.md
@CLAUDE.md

<interfaces>
<!-- Key locations the executor needs. Line numbers are approximate and may shift after Plan 01. -->

From app/prompts/endgame_insights.md (line 139):
```
The `score_gap_timeline` subsection is the one exception to the summary-per-metric rule: it emits only the raw `[series ...]` block. Its scalar `value` is a weekly-latest bucket mislabeled as an aggregate; the authoritative score_gap aggregate lives in the `overall` subsection's `[summary score_gap]`.
```
This whole paragraph must be deleted.

From app/prompts/endgame_insights.md (lines 297-298):
```
  - **Framing rule (important):** when narrating `score_gap`, first read the `overall_wdl` chart block. Compare the two `score_pct` values directly. If non-endgame `score_pct` is ≥ 58 (strong on its own), lead with "strong non-endgame play" before "weak endgame". If endgame `score_pct` is ≤ 42 (weak on its own), lead with endgame weakness. If both are moderate, describe the gap neutrally as a relative signal. Do NOT default to "weak endgame" just because `score_gap` is negative.
  - **Source of the aggregate:** quote `[summary score_gap]` in the `### Subsection: overall` block — its `mean` exactly matches the chart math (`endgame.score_pct - non_endgame.score_pct`). The `### Subsection: score_gap_timeline` block emits only a raw `[series ...]` block with no `[summary]` — narrate a specific bucket from that series only when pointing at that bucket explicitly, never as "the aggregate".
```
Both bullets must be removed.

From app/prompts/endgame_insights.md (line ~356):
```
| score_gap_timeline                   | overall        |
```
Rename the row label to `score_timeline` (content column unchanged).

From app/prompts/endgame_insights.md (line ~371):
```
- `overall_wdl` (2-row table: endgame vs non_endgame) → part of the `overall` section alongside `score_gap` / `score_gap_timeline`. Use it to frame whether a negative or positive `score_gap` is driven by endgame weakness, non-endgame strength, or both — see the `score_gap` framing rule above.
```
Rename `score_gap_timeline` → `score_timeline`. Drop the trailing clause "— see the `score_gap` framing rule above." since the framing rule is gone.

From app/services/insights_llm.py (line 60):
```python
_PROMPT_VERSION = "endgame_v12"  # v12 changes: (1) new `[anchor-combo ...]` ...
```
Bump to `endgame_v13` with a concise v13 change note.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Edit the prompt file and bump the version constant</name>
  <read_first>
    - app/prompts/endgame_insights.md (full file — line numbers listed in `<interfaces>` are approximate; verify before editing)
    - app/services/insights_llm.py (lines 50-75 — _PROMPT_VERSION site)
    - tests/services/test_insights_llm.py (search for `_PROMPT_VERSION` / `endgame_v12` — update any version-string assertion)
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md (created by Plan 01; confirms the new `score_timeline` subsection shape so the prompt's subsection-id references match the payload, including the TWO-summary + TWO-series shape per window)
  </read_first>
  <behavior>
    - Test 1: `_PROMPT_VERSION == "endgame_v13"` at module import.
    - Test 2: File `app/prompts/endgame_insights.md` does NOT contain any of the following substrings:
      - `score_gap_timeline`
      - `Framing rule (important)`
      - `one exception to the summary-per-metric rule`
      - `Score Gap over Time` (old chart title — guard against a future regression)
    - Test 3: File `app/prompts/endgame_insights.md` DOES contain:
      - `score_timeline` (at least once — renamed subsection id)
      - `[summary score_timeline]` (in the emitter-shape documentation)
      - `part=endgame` and `part=non_endgame` (documenting the series-block tags)
      - `weekly` (documenting that the score_timeline series granularity is weekly, not monthly — matches the actual backend)
    - Test 4: The `## Subsection → section_id mapping` table row maps `score_timeline` (not `score_gap_timeline`) to `overall`.
    - Test 5: No `test_insights_llm.py` test hard-asserts a `score_gap_timeline` or `score_gap` framing-rule string verbatim from the prompt body — if one did under v12, it's rewritten.
  </behavior>
  <action>
    1. **Verify line numbers** before editing — Plan 01 touches `app/services/insights_llm.py` but NOT `app/prompts/endgame_insights.md`, so the prompt-file line numbers from `<interfaces>` should be stable. Re-grep to confirm:
       ```bash
       grep -n "score_gap_timeline\|Framing rule\|summary-per-metric" app/prompts/endgame_insights.md
       ```
       Use the actual line numbers in the edits.

    2. **Delete the "exception" paragraph** at line ~139. Remove the entire paragraph starting `The \`score_gap_timeline\` subsection is the one exception` through the end of that sentence / paragraph block. Collapse any resulting double-blank-line.

    3. **Delete the `score_gap` framing rule bullets** at lines ~297-298. Remove both the `**Framing rule (important):**` bullet AND its sibling `**Source of the aggregate:**` bullet. If they sit inside a larger section about the `overall` section, leave the surrounding paragraph intact; only the two bullets go.

    4. **Rename subsection ids**:
       - `score_gap_timeline` → `score_timeline` in the mapping table (~line 356).
       - `score_gap_timeline` → `score_timeline` in the prose reference at ~line 371. Also drop the trailing clause about the framing rule ("— see the \`score_gap\` framing rule above") since the rule is gone. Resulting sentence should read approximately:
         `- \`overall_wdl\` (2-row table: endgame vs non_endgame) → part of the \`overall\` section alongside \`score_gap\` / \`score_timeline\`. Use it to frame whether a negative or positive \`score_gap\` is driven by endgame weakness, non-endgame strength, or both.`

    5. **Sweep the rest of the prompt file** for any remaining `score_gap_timeline` occurrences — update each to `score_timeline`. Narrative examples (if any cite the old subsection id in an example payload) must use the new id.

    6. **Update the emitter documentation** (around line 137-139 in the prompt — the block that lists which subsections emit `[series ...]` blocks) so the text reflects the new reality. Example replacement text:
       > The `score_timeline` subsection emits TWO standard `[summary score_timeline]` blocks per window (one for `part=endgame`, one for `part=non_endgame`, both carrying the same aggregate score_gap mean but framed from each side) followed by TWO `[series score_gap, <window>, weekly, part=endgame]` / `[series score_gap, <window>, weekly, part=non_endgame]` blocks. The `endgame` block emits first in both pairs. Narrate by comparing the two series; for the aggregate gap quote `[summary score_gap]` in the `### Subsection: overall` block.

       Keep the existing documentation for the other three timeline subsections (`clock_diff_timeline`, `endgame_elo_timeline`, `type_win_rate_timeline`) unchanged. **Note the granularity is `weekly`** (not monthly — CONTEXT.md's "monthly" was advisory; the real backend emits ISO-weekly points).

    7. **Bump the version constant** in `app/services/insights_llm.py` (line 60):
       ```python
       _PROMPT_VERSION = "endgame_v13"  # v13 changes: (1) Endgame Score Gap timeline renamed to `score_timeline` and now emits TWO `[summary score_timeline]` blocks + TWO `[series score_gap, ..., weekly, part=endgame|non_endgame]` blocks per window (no emitter carve-out — same fanned-out shape as endgame_elo per-combo); (2) dropped the `score_gap` framing rule — the two-line chart (UI) + overall_wdl chart block (payload) together make composition self-evident; (3) dropped the `score_gap_timeline` "only exception to summary-per-metric" carve-out — the subsection follows the standard per-dimension emitter shape. Cache invalidation is automatic via prompt_version cache key.
       ```

    8. **Update tests**: `tests/services/test_insights_llm.py`:
       - Search for `endgame_v12` — replace with `endgame_v13` in any version-string assertion.
       - Add a minimal regression test `test_prompt_file_does_not_contain_removed_framing_rule` that reads `app/prompts/endgame_insights.md` and asserts the four negative-substring invariants from `<behavior>` Test 2 plus the positive invariants from Test 3.

    9. Run the full insights test file and the deterministic snapshot coverage:
       ```bash
       uv run pytest tests/services/test_insights_llm.py -x
       uv run pytest tests/services/test_insights_service_series.py -x
       ```
       Every test that previously asserted on prompt text containing `score_gap_timeline` or the Framing rule string needs to be updated to match the new prompt.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py -x &amp;&amp; ! grep -n "score_gap_timeline\|Framing rule (important)\|one exception to the summary-per-metric" app/prompts/endgame_insights.md &amp;&amp; grep -q "endgame_v13" app/services/insights_llm.py</automated>
  </verify>
  <done>
    - `grep -n "score_gap_timeline" app/prompts/endgame_insights.md` returns zero matches.
    - `grep -n "Framing rule (important)" app/prompts/endgame_insights.md` returns zero matches.
    - `grep -n "one exception to the summary-per-metric" app/prompts/endgame_insights.md` returns zero matches.
    - `grep -n "score_timeline" app/prompts/endgame_insights.md` returns at least one match.
    - `grep -n "part=endgame\|part=non_endgame" app/prompts/endgame_insights.md` returns at least one match each (emitter-shape documentation).
    - `grep -n "weekly" app/prompts/endgame_insights.md` contains a match in the score_timeline documentation block.
    - `grep -n "endgame_v13" app/services/insights_llm.py` returns a match.
    - `uv run pytest tests/services/test_insights_llm.py -x` passes.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/services/test_insights_llm.py tests/services/test_insights_service_series.py -x` passes.
- `grep -rn "score_gap_timeline" app/ tests/` returns zero matches across the whole backend.
- `grep -n "endgame_v13" app/services/insights_llm.py` matches.
- Prompt file sweep: `grep -n "Framing rule\|summary-per-metric\|score_gap_timeline" app/prompts/endgame_insights.md` returns zero matches.
- Prompt file includes: `score_timeline`, `part=endgame`, `part=non_endgame`, `weekly` (emitter-shape documentation is in place).
</verification>

<success_criteria>
- Success Criterion 3 from ROADMAP.md satisfied: prompt no longer carries the `score_gap` framing rule; the `score_gap_timeline` "no [summary]" exception note is gone; all references to the old chart name / subsection id are updated; emitter-shape documentation matches Plan 01's two-summary + two-series reality.
- Prompt version bumped to `endgame_v13` so cached LLM reports invalidate (per Phase 65 cache-key design in `get_latest_log_by_hash`).
</success_criteria>

<output>
After completion, create `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-03-SUMMARY.md` documenting:
- The exact text removed (before/after snippets for the two deletions).
- The new `[summary score_timeline]` × 2 + `[series score_gap, ..., weekly, part=X]` × 2 emitter documentation block (copy the text as written into the prompt).
- The v13 change note.
</output>
