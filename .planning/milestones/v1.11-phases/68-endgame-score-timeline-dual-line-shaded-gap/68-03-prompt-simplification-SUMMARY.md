---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 03
subsystem: insights
tags:
  - insights
  - endgame
  - prompt
  - cache-invalidation
requires:
  - _PROMPT_VERSION == "endgame_v12" (to bump)
  - app/prompts/endgame_insights.md score_gap framing rule + score_gap_timeline exception paragraph + old subsection-id references (to remove/rename)
  - Plan 01's suppress_summary carve-out already removed (precondition satisfied)
provides:
  - _PROMPT_VERSION = "endgame_v13" — cached LLM reports invalidate automatically
  - Simplified endgame prompt without score_gap framing rule or score_gap_timeline exception paragraph
  - New emitter-shape documentation for `score_timeline` (two-summary + two-series, weekly granularity)
  - TestPromptVersionAndBody regression class guarding the prompt body from future regressions
affects:
  - Plan 04 (snapshot + changelog) — prompt v13 is the new snapshot baseline
  - User-facing LLM insights quality — composition is now narrated from the two-line chart + per-part series instead of the deleted framing rule
tech-stack:
  added: []
  patterns:
    - Prompt-version cache invalidation via `_PROMPT_VERSION` bump (Phase 65 cache key)
    - Prompt-body regression testing via a test class that reads the file from disk and asserts negative + positive substring invariants
key-files:
  created: []
  modified:
    - app/prompts/endgame_insights.md
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py
decisions:
  - Kept `_compute_score_gap_timeline` (helper name in `app/services/endgame_service.py`) and the one-line docstring reference to it in `_series_granularity` unchanged — Plan 01's SUMMARY explicitly carved these out as incidental identifiers that never reach the LLM. Renaming the helper would exceed Plan 03's `files_modified:` scope and break wave-3 isolation. The plan's strict `grep -rn "score_gap_timeline" app/ tests/` zero-matches verification is not literally satisfied but the spirit (prompt body clean, subsection-id references renamed, no user-visible `score_gap_timeline` string) is.
  - Rewrote the deleted "exception" paragraph as a DETAILED emitter-shape description rather than leaving a bare line. The LLM needs explicit guidance on how to narrate the new two-line shape (endgame-first ordering, weekly grain across both windows, absolute Score percentages not signed gaps) — simply deleting the carve-out would leave the prompt silent about the subsection's new behaviour.
  - Regression test reads the prompt file from disk at test time rather than asserting against a snapshot. Snapshot would drift as copy-edits accumulate; disk reads pin the specific invariants (negative: no forbidden substrings; positive: required labels present) that v13 guarantees.
metrics:
  duration: ~20m
  completed: 2026-04-24
---

# Phase 68 Plan 03: Prompt Simplification Summary

**One-liner:** Dropped the `score_gap` framing rule, deleted the `score_gap_timeline` "only exception to summary-per-metric" carve-out, renamed every `score_gap_timeline` reference to `score_timeline`, rewrote the emitter-shape documentation to match Plan 01's two-summary + two-series reality, and bumped `_PROMPT_VERSION` to `endgame_v13` so cached LLM reports invalidate.

## What Changed

### 1. Removed the `score_gap_timeline` "only exception" paragraph

**Before** (line 139):
```
The `score_gap_timeline` subsection is the one exception to the summary-per-metric rule: it emits only the raw `[series ...]` block. Its scalar `value` is a weekly-latest bucket mislabeled as an aggregate; the authoritative score_gap aggregate lives in the `overall` subsection's `[summary score_gap]`.
```

**After** (line 139 — replaced with new emitter-shape documentation):
```
The `score_timeline` subsection emits TWO standard `[summary score_timeline]` blocks per window (one for `part=endgame`, one for `part=non_endgame`, both carrying the same aggregate `score_gap` mean but framed from each side) followed by TWO series blocks: `[series score_gap, <window>, weekly, part=endgame]` and `[series score_gap, <window>, weekly, part=non_endgame]`. The `endgame` block emits first in both pairs. Per-part series values are absolute Score percentages (0-100), not signed gaps — compare the two lines directly (e.g. "endgame side trending up from 55% to 60%, non-endgame flat at 50%") rather than reading a signed difference bucket-by-bucket. For the aggregate score_gap, quote `[summary score_gap]` in the `### Subsection: overall` block. Granularity is `weekly` across BOTH `all_time` and `last_3mo` windows for this subsection — do not resample to monthly when narrating.
```

Also updated the `Four subsections additionally emit ...` line (line 137) to use `score_timeline` in place of `score_gap_timeline`.

### 2. Removed the `score_gap` framing rule bullets

**Before** (lines 297-298, inside the `score_gap` metric-glossary entry):
```
  - **Framing rule (important):** when narrating `score_gap`, first read the `overall_wdl` chart block. Compare the two `score_pct` values directly. If non-endgame `score_pct` is ≥ 58 (strong on its own), lead with "strong non-endgame play" before "weak endgame". If endgame `score_pct` is ≤ 42 (weak on its own), lead with endgame weakness. If both are moderate, describe the gap neutrally as a relative signal. Do NOT default to "weak endgame" just because `score_gap` is negative.
  - **Source of the aggregate:** quote `[summary score_gap]` in the `### Subsection: overall` block — its `mean` exactly matches the chart math (`endgame.score_pct - non_endgame.score_pct`). The `### Subsection: score_gap_timeline` block emits only a raw `[series ...]` block with no `[summary]` — narrate a specific bucket from that series only when pointing at that bucket explicitly, never as "the aggregate".
```

**After:** Both bullets deleted. The metric glossary now reads:
```
- **score_gap**: the user's Score in games that reached an endgame phase **minus** their Score in games that did not. Within-user, relative signal — NOT a user-vs-opponent comparison. Positive = endgame stronger; negative = non-endgame stronger.
  - Scale: signed whole-number percentage in `[-100, +100]` (e.g. `+8` = endgame Score is 8% higher than non-endgame, narrated as "+8%").
```

### 3. Subsection-id renames

- `## Subsection → section_id mapping` table row renamed (line ~354):
  ```
  | score_timeline                       | overall        |
  ```
- Chart note prose (line ~369) renamed and trailing framing-rule clause dropped:
  ```
  - `overall_wdl` (2-row table: endgame vs non_endgame) → part of the `overall` section alongside `score_gap` / `score_timeline`. Use it to frame whether a negative or positive `score_gap` is driven by endgame weakness, non-endgame strength, or both.
  ```

### 4. `_PROMPT_VERSION` bumped

`app/services/insights_llm.py` line 60:

```python
_PROMPT_VERSION = "endgame_v13"  # v13 changes: (1) Endgame Score Gap timeline renamed to `score_timeline` and now emits TWO `[summary score_timeline]` blocks + TWO `[series score_gap, ..., weekly, part=endgame|non_endgame]` blocks per window (no emitter carve-out — same fanned-out shape as endgame_elo per-combo); (2) dropped the `score_gap` framing rule — the two-line chart (UI) + overall_wdl chart block (payload) together make composition self-evident; (3) dropped the `score_gap_timeline` "only exception to summary-per-metric" carve-out — the subsection follows the standard per-dimension emitter shape. Cache invalidation is automatic via prompt_version cache key.
```

### 5. Regression test class (`TestPromptVersionAndBody`)

Added three tests in `tests/services/test_insights_llm.py` after `TestStartupValidation`:

- `test_prompt_version_is_v13` — asserts `insights_llm._PROMPT_VERSION == "endgame_v13"`.
- `test_prompt_file_does_not_contain_removed_framing_rule` — reads `app/prompts/endgame_insights.md` from disk, asserts neither `score_gap_timeline` nor `Framing rule (important)` nor `one exception to the summary-per-metric` nor `Score Gap over Time` appears; asserts `score_timeline`, `[summary score_timeline]`, `part=endgame`, `part=non_endgame`, and `weekly` all appear.
- `test_subsection_mapping_table_renames_to_score_timeline` — parses the mapping table and asserts the `score_timeline → overall` row is present.

All nine existing `"endgame_v12"` string literals across the test suite were also bumped to `"endgame_v13"` (sample report fixture, `_make_log_row` default, two response-assertion sites, four seeded-row comment sites, and the validation-failure fixture's `custom_output_args`).

## Deviations from Plan

**Rule 3 — Deliberate scope boundary:** Plan 03's `<verification>` block claims `grep -rn "score_gap_timeline" app/ tests/` returns zero matches across the whole backend. The working tree still contains three incidental occurrences:

1. `app/services/endgame_service.py::_compute_score_gap_timeline` — the helper function computing the underlying per-week endgame vs non-endgame Score aggregates. Plan 01's SUMMARY explicitly calls out "only incidental variable names + one intentional Phase 68 docstring note remain" and leaves these as out-of-scope. Renaming this function falls outside Plan 03's declared `files_modified:` (`app/prompts/endgame_insights.md`, `app/services/insights_llm.py`).
2. `app/services/insights_llm.py::_series_granularity` docstring (line 904) — references `_compute_score_gap_timeline` by name while explaining the weekly-always rationale. Intentional per Plan 01; points at the actual helper.
3. `app/services/insights_llm.py::_PROMPT_VERSION` v13 change comment — necessarily mentions `score_gap_timeline` to describe what was deleted. Removing it would make the change log opaque.

None of these strings ever reach the LLM (only `app/prompts/endgame_insights.md` is read at prompt-assembly time) — the spirit of the verification (user-visible prompt clean) is satisfied. Flagged here so the orchestrator's verifier does not misread a literal grep as a failure.

## Follow-ups

- **Plan 04 (snapshot + changelog):** will re-snapshot the prompt at v13. The new `TestPromptVersionAndBody` regression class is already in place to guard future drift.
- **Phase 69+ cleanup (opt-in, out of scope here):** if a future phase wants the literal-zero-matches state, a rename of `_compute_score_gap_timeline` → `_compute_score_timeline` + the docstring reference would close the remaining incidental references. Low priority since these never touch the LLM prompt.

## Verification

- `uv run pytest tests/services/test_insights_llm.py -x` — **49 passed** (includes the 3 new regression tests + 9 bumped `endgame_v13` literals).
- `uv run pytest tests/services/test_insights_service_series.py -x` — **18 passed**.
- `uv run ruff check app/ tests/` — clean.
- `uv run ty check app/ tests/` — clean.
- `grep -n "score_gap_timeline\|Framing rule (important)\|one exception to the summary-per-metric\|Score Gap over Time" app/prompts/endgame_insights.md` — **zero matches**.
- `grep -c "score_timeline" app/prompts/endgame_insights.md` — 4 matches (timeline enumeration, emitter-shape paragraph, mapping table, chart note).
- `grep -c "part=endgame\|part=non_endgame" app/prompts/endgame_insights.md` — 1 each (emitter-shape paragraph).
- `grep "endgame_v13" app/services/insights_llm.py` — 1 match (the `_PROMPT_VERSION` line).

## Self-Check: PASSED

- a4d327f (Task 1 RED test commit) — FOUND
- e60aec5 (Task 1 GREEN implementation commit) — FOUND
- `app/prompts/endgame_insights.md` — MODIFIED (removals + renames + new emitter-shape paragraph)
- `app/services/insights_llm.py` — MODIFIED (`_PROMPT_VERSION = "endgame_v13"` with v13 change comment)
- `tests/services/test_insights_llm.py` — MODIFIED (`TestPromptVersionAndBody` class added; all `endgame_v12` literals bumped to `endgame_v13`)
- `TestPromptVersionAndBody::test_prompt_version_is_v13` — PASSING
- `TestPromptVersionAndBody::test_prompt_file_does_not_contain_removed_framing_rule` — PASSING
- `TestPromptVersionAndBody::test_subsection_mapping_table_renames_to_score_timeline` — PASSING
