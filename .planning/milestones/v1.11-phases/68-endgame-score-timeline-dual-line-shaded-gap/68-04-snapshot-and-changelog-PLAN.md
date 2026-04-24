---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
plan: 04
type: execute
wave: 4
depends_on:
  - 68-01
  - 68-02
  - 68-03
files_modified:
  - tests/services/test_insights_service_series.py
  - tests/services/test_insights_llm.py
  - CHANGELOG.md
autonomous: true
requirements: []
tags:
  - insights
  - endgame
  - tests
  - changelog
must_haves:
  truths:
    - "The full backend insights test suite (`tests/services/test_insights_service.py`, `test_insights_service_series.py`, `test_insights_llm.py`) passes green end-to-end after Plans 01 + 03 land."
    - "The full frontend test suite passes green after Plan 02 lands."
    - "`ruff check`, `ty check`, `npm run lint`, `npm run build`, and `npm run knip` all clean."
    - "`CHANGELOG.md` under `## [Unreleased]` has a `### Changed` bullet describing Phase 68 (dual-line Score timeline + simplified prompt)."
  artifacts:
    - path: "tests/services/test_insights_service_series.py"
      provides: "One new integration test rendering a full user prompt through `_assemble_user_prompt` on a realistic fixture and asserting the new score_timeline shape end-to-end (TWO summary blocks + TWO series blocks per window)"
    - path: "CHANGELOG.md"
      provides: "## [Unreleased] → ### Changed bullet for Phase 68"
      contains: "Phase 68"
  key_links:
    - from: "tests/services/test_insights_service_series.py"
      to: "app/services/insights_llm.py::_assemble_user_prompt"
      via: "Full-prompt integration smoke: fixture → compute_findings → payload assembly → string assertions"
      pattern: "_assemble_user_prompt"
---

<objective>
End-to-end verification that the three upstream plans compose correctly, plus the user-facing CHANGELOG entry. This plan catches any cross-plan regression (e.g. backend rename + prompt text that still references the old id slipped through in a separate file).

Purpose: Plan 01 ships schema + backend (two findings per window); Plan 02 ships frontend (two-line chart); Plan 03 ships prompt text + version bump. Each plan has its own tests, but no single plan exercises the whole pipeline in a realistic scenario. This plan adds one integration test that spans `compute_findings → _assemble_user_prompt` and verifies the rendered prompt body for a realistic fixture looks right, plus the CHANGELOG bullet.

Output:
- One new integration test in `tests/services/test_insights_service_series.py` that builds a fixture `EndgameOverviewResponse`, runs `compute_findings`, passes the findings to `_assemble_user_prompt`, and asserts the rendered string contains `### Subsection: score_timeline`, TWO `[summary score_timeline]` blocks per window (per B4 option c), exactly two `[series score_gap, ..., weekly, part=endgame]` / `part=non_endgame` blocks, and does NOT contain `score_gap_timeline` or `Framing rule`.
- `CHANGELOG.md` `## [Unreleased]` → `### Changed` bullet describing the phase.
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
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-02-SUMMARY.md
@.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-03-SUMMARY.md
@CHANGELOG.md
@CLAUDE.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add end-to-end integration test covering findings → prompt assembly for the renamed subsection</name>
  <read_first>
    - tests/services/test_insights_service_series.py (full file — it already builds realistic fixtures for compute_findings; use the same fixture shape)
    - tests/services/test_insights_llm.py (the `_assemble_user_prompt` helper and its test fixtures; reuse the assembly helper)
    - app/services/insights_llm.py (function `_assemble_user_prompt` — note its exact import path and signature, including whether it's module-private)
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-03-SUMMARY.md
  </read_first>
  <behavior>
    - Test 1 (new): Given a handcrafted `EndgameOverviewResponse` fixture whose `score_gap_material.timeline` has 6 weekly points with mixed endgame-leads-vs-trails pattern, `compute_findings(...)` returns a `EndgameTabFindings` whose subsections include exactly TWO `SubsectionFinding` rows with `subsection_id="score_timeline"` per window (one `part=endgame`, one `part=non_endgame`).
    - Test 2 (new — **B4 option c assertion**): Passing the same findings through `_assemble_user_prompt(tab)` produces a string that:
      - contains `### Subsection: score_timeline` exactly once per window present in the tab (e.g. twice total if all_time + last_3mo are populated);
      - contains `[summary score_timeline]` **exactly twice per window** (once per `part`) — this is the post-B4 shape;
      - contains `part=endgame` and `part=non_endgame` (the series-block tags);
      - contains `, weekly,` as the granularity marker in score_timeline series headers (not `, monthly,`);
      - does NOT contain `score_gap_timeline`;
      - does NOT contain `Framing rule (important)`;
      - contains `[summary score_gap]` inside the `### Subsection: overall` block (regression guard — Plan 01 explicitly preserved the `overall` aggregate).
    - Test 3 (already passing — regression): `_PROMPT_VERSION == "endgame_v13"`.
  </behavior>
  <action>
    1. In `tests/services/test_insights_service_series.py`, add a new test class `TestScoreTimelineIntegration` (or extend an existing suite if it fits) with one test `test_score_timeline_end_to_end_payload`:
       - Build an `EndgameOverviewResponse` fixture reusing any existing builder helper in the same file. The `score_gap_material.timeline` field should carry 6 `ScoreGapTimelinePoint` entries with `endgame_score`, `non_endgame_score`, `score_difference` (identity `score_difference == endgame_score - non_endgame_score`), and positive `per_week_total_games`.
       - Call `compute_findings(response, overall_wdl=...)` (or whatever the current entry signature is per the file you read).
       - Import `_assemble_user_prompt` from `app.services.insights_llm` (matching whatever test fixtures already import — it may be module-private; prefix with `# ty: ignore[private-import]` if needed and add a brief justification comment).
       - Call `_assemble_user_prompt(findings)` and assert every string invariant listed in Test 2, including **the `[summary score_timeline]` count assertion: exactly 2 occurrences per window**. Use `rendered.count("[summary score_timeline]")` for a clean count assertion.

    2. Run the full backend insights test set:
       ```bash
       uv run pytest tests/services/test_insights_service.py tests/services/test_insights_service_series.py tests/services/test_insights_llm.py -x
       ```
       Then run the full project test suite to catch any stray `score_gap_timeline` reference in an unrelated test file:
       ```bash
       uv run pytest -x
       ```

    3. Run the frontend test suite:
       ```bash
       cd frontend && npm test -- --run
       ```

    4. **Fail-closed grep**: finally, assert zero occurrences of the old identifier anywhere outside the planning artifacts:
       ```bash
       grep -rn "score_gap_timeline" app/ tests/ frontend/src/ && echo "LEAK" || echo "OK"
       ```
       The expected output is `OK`. If `LEAK`, fix before declaring done.
  </action>
  <verify>
    <automated>uv run pytest -x &amp;&amp; cd frontend &amp;&amp; npm test -- --run &amp;&amp; cd .. &amp;&amp; ! grep -rn "score_gap_timeline" app/ tests/ frontend/src/</automated>
  </verify>
  <done>
    - Full backend test suite green.
    - Full frontend test suite green.
    - `grep -rn "score_gap_timeline" app/ tests/ frontend/src/` returns zero matches.
    - New integration test `test_score_timeline_end_to_end_payload` present in `tests/services/test_insights_service_series.py`, asserting the two-summary + two-series shape.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write the CHANGELOG bullet for Phase 68</name>
  <read_first>
    - CHANGELOG.md (lines 1-50 — format of `## [Unreleased]` + existing `### Changed` entries for v1.11 phases; use the same voice / prompt-version bump phrasing)
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-01-SUMMARY.md
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-02-SUMMARY.md
    - .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-03-SUMMARY.md
  </read_first>
  <acceptance_criteria>
    - `CHANGELOG.md` under `## [Unreleased]` contains a new `### Changed` bullet whose text starts with `Phase 68:` and mentions: the dual-line chart on the Endgame tab, the prompt bump to `endgame_v13`, and that the old single-line Score Gap chart is removed.
    - `grep -n "Phase 68" CHANGELOG.md` returns at least one match.
    - `grep -n "endgame_v13" CHANGELOG.md` returns at least one match.
    - No em-dashes added in the bullet (per CLAUDE.md communication style).
  </acceptance_criteria>
  <action>
    Append one bullet under the existing `## [Unreleased]` → `### Changed` section in `CHANGELOG.md` (the section already exists and lists prior `endgame_vN` bumps, so this bullet extends the series). Suggested copy (tune for voice — terse, user-facing):

    > - Phase 68: Endgame tab now shows a dual-line "Endgame vs Non-Endgame Score over Time" chart (both absolute Score series, shaded area between them: green when endgame leads, red when it trails) in place of the old single-line "Score Gap over Time" chart. Backend subsection renamed from `score_gap_timeline` to `score_timeline` emitting two `[series score_gap, part=endgame|non_endgame]` blocks under two standard `[summary score_timeline]` blocks per window; prompt bumped to `endgame_v13` dropping the now-redundant `score_gap` framing rule (the two-line chart makes gap composition self-evident). Info popover drops the "Score Gap is a comparison, not an absolute measure" caveat.

    Keep it to one bullet. No em-dashes.
  </action>
  <verify>
    <automated>grep -q "Phase 68" CHANGELOG.md &amp;&amp; grep -q "endgame_v13" CHANGELOG.md &amp;&amp; ! grep -P "Phase 68.*—" CHANGELOG.md</automated>
  </verify>
  <done>
    - `## [Unreleased]` section of `CHANGELOG.md` contains the new bullet.
    - No em-dash introduced in the Phase 68 bullet (PCRE grep returns nothing).
  </done>
</task>

</tasks>

<verification>
- `uv run pytest -x` green.
- `cd frontend && npm test -- --run` green.
- `uv run ty check app/ tests/` green.
- `uv run ruff check app/ tests/` green.
- `cd frontend && npm run lint && npm run build && npm run knip` all clean.
- `grep -rn "score_gap_timeline" app/ tests/ frontend/src/` zero matches.
- `grep -n "Phase 68\|endgame_v13" CHANGELOG.md` matches.
</verification>

<success_criteria>
- Success Criterion 5 from ROADMAP.md satisfied: existing insights snapshot tests pass (rename + prompt simplification does not change LLM narrative content).
- End-to-end integration test proves the full pipeline (findings → prompt assembly) renders the new subsection shape correctly — including the B4 option c two-summary-per-window shape.
- CHANGELOG bullet present under `## [Unreleased]` ready for milestone close.
</success_criteria>

<output>
After completion, create `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-04-SUMMARY.md` documenting:
- Test additions (including the `[summary score_timeline]` count = 2/window assertion).
- Final test suite status.
- CHANGELOG bullet text (copy-paste).
- Any surprises surfaced by the integration test that weren't caught by the per-plan tests.
</output>
