---
phase: 82
plan: 02
subsystem: insights-llm
tags: [endgame, llm, prompt, metrics, zones, tdd]
dependency_graph:
  requires: [82-01]
  provides: [endgame_v23-prompt, endgame_start_vs_end-subsection-block, entry_eval_pawns-glossary, endgame_score-glossary-v23, score_timeline-rename-prompt]
  affects: [insights_llm, endgame_insights_prompt, test_insights_llm]
tech_stack:
  added: []
  patterns: [tdd-red-green, prompt-versioning, cumulative-changelog]
key_files:
  created: []
  modified:
    - app/prompts/endgame_insights.md
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py
decisions:
  - Placed ### Subsection endgame_start_vs_end block before ## Endgame statistics concepts (closest natural anchor for narration-guide H3 blocks, consistent with document flow: read narration rules before concepts)
  - test_prompt_version_bump_misses test uses "endgame_v0" (not "endgame_v22") as the stale cache row — intentionally preserved so the test exercises cache invalidation without being tied to the previous current version
  - Added [summary endgame_score_timeline] / [summary non_endgame_score_timeline] positive assertions replacing the old [summary endgame_score] / [summary non_endgame_score] assertions — the line-125 paragraph now uses the _timeline variants exclusively
metrics:
  duration: ~25 minutes
  completed: 2026-05-10T19:15:00Z
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 82 Plan 02: Prompt side — glossary, subsection block, mapping table, version bump Summary

Wire the LLM prompt for Phase 82: renamed score_timeline metric identifiers in the line-125 paragraph and glossary, new glossary entries for `entry_eval_pawns` and `endgame_score` (repurposed), a new `### Subsection: endgame_start_vs_end` narration guide with setup-execution framing, mapping table row insertion, and `_PROMPT_VERSION` bump to `endgame_v23`.

## What Was Built

### Task 1: app/prompts/endgame_insights.md — five-step prompt update

**Step 1 — line-125 paragraph rename:**
- `[summary endgame_score]` → `[summary endgame_score_timeline]`
- `[summary non_endgame_score]` → `[summary non_endgame_score_timeline]`
- All bare metric name references within the paragraph updated to `_timeline` variants
- Tail clause added: "(Note: through endgame_v22 these metrics were named `endgame_score` and `non_endgame_score`; the bare `endgame_score` name now belongs to the `endgame_start_vs_end` subsection — see its glossary entry below.)"

**Step 2 — glossary rename (D-22 housekeeping):**
- `**endgame_score**` → `**endgame_score_timeline**` with migration note "(formerly named `endgame_score` through endgame_v22; the bare `endgame_score` name now belongs to the `endgame_start_vs_end` subsection.)"
- `**non_endgame_score**` → `**non_endgame_score_timeline**` with analogous note "(formerly named `non_endgame_score` through endgame_v22; the bare `non_endgame_score` name is retired.)"

**Step 3 — two new glossary entries (D-22):**
- `**entry_eval_pawns**` (UI label: "Endgame entry eval"): signed Stockfish eval at endgame entry in pawns, user-POV. ±0.50 typical band. LLM does NOT receive sig-test outcome — narrate from zone + sample_quality + [near edge]. Emitted in `endgame_start_vs_end`, dimension=None.
- `**endgame_score**` (UI label: "Endgame score"): repurposed for endgame_start_vs_end subsection. Score in endgame-reaching games on 0-100% scale, 50% baseline. 45-55% typical band. Wilson test not propagated to LLM. Explicit cross-reference to `endgame_score_timeline` (the old timeline variant).

**Step 4 — new subsection block (D-23):** `### Subsection: endgame_start_vs_end` inserted before `## Endgame statistics concepts`. Contains:
- "setup → execution" pair framing
- Five example narration patterns (strong+strong, strong+weak with Time Pressure cross-link, weak+strong, weak+weak, either-typical)
- Within-noise and borderline case rules ([near edge] narration guidance)
- Cross-section Time Pressure link: when entry_eval strong but endgame_score weak, look at `time_pressure_vs_performance` and `avg_clock_diff_pct`; `[low-time-gap]` is the authoritative verdict
- Both-thin-omit rule

**Step 5 — mapping table row (D-24):** Row `| endgame_start_vs_end | overall |` inserted at line 376, between `| overall | overall |` (line 375) and `| score_timeline | overall |` (line 377). D-05 ordering confirmed.

### Task 2: insights_llm.py + test_insights_llm.py — version bump + test updates

**_PROMPT_VERSION bump (D-25):**
```python
_PROMPT_VERSION = "endgame_v23"  # v23 (260510 endgame_start_vs_end): wire Phase 81 entry-eval
# and endgame-score metrics into the LLM payload via a new `endgame_start_vs_end` subsection
# under section_id `overall`. Renamed score_timeline `endgame_score` → `endgame_score_timeline`
# and `non_endgame_score` → `non_endgame_score_timeline` to free the clean `endgame_score` name
# for the new subsection. Tile color rule amended from sig-only to `zone × p<0.05`
# (Phase 81 D-09 amendment). EG-entry-eval neutral band tightened from ±0.75 to ±0.50
# for both tile and LLM. v22 (260503 eval-proxy cutover): [prior history retained verbatim]
```

**Test updates in test_insights_llm.py:**
- `test_prompt_version_is_v22` → `test_prompt_version_is_v23` (renamed + assertion updated)
- Class docstring updated to reference `endgame_v23` and Phase 82 additions
- `[summary endgame_score]` / `[summary non_endgame_score]` positive invariants → `_timeline` variants (line-125 paragraph now uses these)
- `response.report.prompt_version == "endgame_v22"` → `"endgame_v23"`
- `log.response_json["prompt_version"] == "endgame_v22"` → `"endgame_v23"`
- `test_prompt_version_bump_misses` cache row uses `"endgame_v0"` — intentionally NOT changed (tests cache invalidation with a stale version)

**Four new content tests added (inside `TestPromptVersionAndBody`):**
1. `test_prompt_contains_endgame_start_vs_end_subsection` — asserts `"### Subsection: endgame_start_vs_end"` and `"setup → execution"` in body
2. `test_prompt_glossary_contains_entry_eval_pawns` — asserts `"**entry_eval_pawns**"` in body
3. `test_prompt_glossary_renames_score_timeline_metrics` — asserts `"**endgame_score_timeline**"` and `"**non_endgame_score_timeline**"` in body
4. `test_prompt_mapping_table_includes_endgame_start_vs_end_row` — line-by-line scan for `| endgame_start_vs_end ... | overall |` row

## TDD Compliance

**Task 1:** Prompt content changes (not code). Tests are in Task 2.

**Task 2:**
- RED: Updated `test_prompt_version_is_v23` assertion before bumping `_PROMPT_VERSION`. Test FAILED (`endgame_v22 != endgame_v23`). Four new content tests PASSED (prompt file already updated in Task 1).
- GREEN: Bumped `_PROMPT_VERSION = "endgame_v23"`. All 60 tests in `test_insights_llm.py` PASSED.

## Verification Results

- `uv run pytest tests/services/test_insights_llm.py -x`: **60 passed** (4 more than v22 baseline of 56)
- `uv run pytest -x` (full suite): **1311 passed, 6 skipped**
- `uv run ty check app/ tests/`: **All checks passed**
- `uv run ruff check app/ tests/`: **All checks passed**

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- `1bce2a93`: `feat(82-02): update prompt — line-125 rename, glossary rename+new entries, subsection block, mapping row`
- `98414cac`: `test(82-02): update version assertion to v23, rename score_timeline metric refs, add new content tests`
- `df1b29d5`: `feat(82-02): bump _PROMPT_VERSION to endgame_v23 with cumulative changelog`

## Known Stubs

None — all changes are wired to the Plan 01 findings emitter (`_findings_endgame_start_vs_end`) and the live prompt system.

## Threat Flags

None — changes are entirely in prompt text and a version string constant. No new network endpoints, auth paths, file access patterns, or schema changes. The new prompt content (glossary + subsection block) is sent to the LLM provider with every endgame insights request — this matches T-82-04 (accepted disposition: metric semantics are user-derivable from the public UI).

## Self-Check

Files exist check:
- app/prompts/endgame_insights.md: present
- app/services/insights_llm.py: present
- tests/services/test_insights_llm.py: present

Commits exist:
- 1bce2a93: present
- 98414cac: present
- df1b29d5: present

## Self-Check: PASSED
