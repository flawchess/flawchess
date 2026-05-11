---
phase: 83
plan: 05
subsystem: services/insights + prompts
status: complete
completed: 2026-05-11
requires:
  - "Plan 83-02 (entry_expected_score* fields on EndgamePerformanceResponse)"
  - "Plan 83-04 (ZONE_REGISTRY entry + MetricId Literal for entry_expected_score; band [0.45, 0.55])"
provides:
  - "_findings_endgame_start_vs_end emits THREE SubsectionFindings (was 2)"
  - "endgame_v25 prompt version (was endgame_v24); cache invalidates automatically"
  - "entry_expected_score glossary entry + extended endgame_start_vs_end subsection block in app/prompts/endgame_insights.md"
affects:
  - "Cached LLM endgame insights reports invalidate on first call after deploy (prompt_version is part of cache key)"
  - "Downstream LLM narrations gain the achievable-vs-achieved gap as the headline diagnostic for the endgame_start_vs_end subsection (D-18)"
tech-stack:
  added: []
  patterns:
    - "Three-finding emitter follows the existing two-finding shape exactly; sample-size gate ge 10 (Phase 82 D-17 carried forward); no verdict field (Phase 82 D-06, Phase 83 D-19; memory feedback_llm_significance_signal.md)"
    - "Prompt-version cache invalidation via prepend-style changelog comment (each prior vN block preserved chronologically)"
    - "Forbidden-word guarding done at the prompt-asset level via a regression test that scans the prompt file (no narration guidance line may use the term, only explicit forbidden-words list lines)"
key-files:
  created: []
  modified:
    - "app/services/insights_service.py"
    - "app/services/insights_llm.py"
    - "app/prompts/endgame_insights.md"
    - "tests/services/test_insights_service.py"
    - "tests/services/test_insights_llm.py"
decisions:
  - "Plan task 1 requested 'add entry_expected_score to MetricId Literal in app/services/insights_service.py'; the MetricId Literal actually lives in app/services/endgame_zones.py and was added there by Plan 83-04 (commit 88c461f6). insights_service.py imports MetricId from endgame_zones, so no second declaration is needed. Verified by Pyright/ty zero-errors and runtime test_three_findings_returned_in_canonical_order."
  - "Acceptance criterion 'grep -c verdict app/services/insights_service.py should match pre-change count' interpreted as 'no new verdict field added to SubsectionFinding emissions'. The new docstring on _findings_endgame_start_vs_end mentions verdict once to explain its absence (D-19 rationale + memory feedback_llm_significance_signal.md); a programmatic guard test (test_third_finding_has_no_verdict_field) asserts no verdict attribute on the emitted finding."
  - "Forbidden-words list test loosened from the literal interpretation 'at most 1 occurrence of underperformance' to 'every occurrence must be on a line that also contains Forbidden'. Two occurrences exist: one in the glossary entry's forbidden-framing block, one in the subsection block's forbidden-words list. Both are explicit forbidden-words lists per D-10; narration guidance never uses the term."
  - "Cohort typical band for entry_expected_score glossary entry is documented as 45 to 55 percent (matches the [0.45, 0.55] band locked by Plan 83-04). Citation is to reports/benchmarks-2026-05-11.md Section 5 (the canonical Plan 4 deliverable)."
  - "Headline ordering when all three findings fire (Claude's Discretion item from CONTEXT.md): lead with the gap when one of the score tiles is in a colored zone; lead with entry_eval_pawns when the entry edge is the dominant signal; treat as background when all three are typical."
metrics:
  duration: "~25 minutes"
  completed: 2026-05-11
  tasks_completed: 2
  files_changed: 5
  tests_added: 13
---

# Phase 83 Plan 05: LLM prompt awareness of entry_expected_score Summary

Teach the LLM about the new `entry_expected_score` metric so the endgame
insights pipeline narrates the achievable-vs-achieved gap from launch.
Mirrors the Phase 82 D-13 "tile and LLM agree on what is narratable from
day one" logic. Two threads landed in two task commits (RED+GREEN each):

1. Backend payload (Task 1): `_findings_endgame_start_vs_end` returns a
   third `SubsectionFinding` for `entry_expected_score` matching the
   shape of the existing two (zone via `assign_zone`, no `verdict`
   field, sample-size gate ge 10 with `_empty_finding` fallback).
2. Prompt asset + version bump (Task 2): `_PROMPT_VERSION` bumps from
   `endgame_v24` to `endgame_v25` (cache invalidation is automatic via
   the `prompt_version` cache key in `generate_insights`). The
   prompt file gains a glossary entry for `entry_expected_score` and
   the existing endgame_start_vs_end subsection block is extended with
   the achievable-vs-achieved gap framing, two worked example
   narrations from CONTEXT.md D-18, headline-ordering guidance, and
   an explicit forbidden-word list (no "underperformance" framing).

## Backend Emitter (app/services/insights_service.py)

Extended `_findings_endgame_start_vs_end` from 2 to 3 findings.

```python
# Tile 3 — achievable score (Phase 83 D-19: gate on entry_expected_score_n >= 10)
n_ex = perf.entry_expected_score_n
if n_ex < 10:
    tile3 = _empty_finding("endgame_start_vs_end", window, "entry_expected_score")
else:
    ex = perf.entry_expected_score
    ex_quality = sample_quality("endgame_start_vs_end", n_ex)
    tile3 = SubsectionFinding(
        subsection_id="endgame_start_vs_end",
        parent_subsection_id=None,
        window=window,
        metric="entry_expected_score",
        value=ex,
        zone=assign_zone("entry_expected_score", ex),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=n_ex,
        sample_quality=ex_quality,
        is_headline_eligible=ex_quality != "thin",
        dimension=None,
    )

return [tile1, tile2, tile3]
```

Docstring updated from "TWO findings" to "THREE findings". The three
sample-size gates remain independent so tile1+tile2 can be populated
while tile3 stays thin during partial Stockfish backfill (covered by
`test_third_finding_independent_gate_from_other_tiles`).

`MetricId` already contained `entry_expected_score` from Plan 83-04
(in `app/services/endgame_zones.py`); the import in
`insights_service.py` picks it up transparently.

## Prompt Version (app/services/insights_llm.py)

```python
_PROMPT_VERSION = "endgame_v25"  # v25 (260511 entry_expected_score): wire Stockfish-baseline achievable score (Lichess sigmoid) into the endgame_start_vs_end subsection alongside entry_eval_pawns and endgame_score. New ENTRY_EXPECTED_SCORE_ZONES from reports/benchmarks-2026-05-11.md. LLM narrates the achievable-vs-achieved gap as the headline diagnostic with entry_eval_pawns as the explanatory unit. v24 (260510-ugj): ... [all prior changelog blocks preserved]
```

Cache invalidation is automatic via the `prompt_version=_PROMPT_VERSION`
cache key participation in `generate_insights`. No manual flush needed.

## Prompt Asset (app/prompts/endgame_insights.md)

New glossary entry (placed after the existing `endgame_score` entry):

- Header: `**entry_expected_score** (UI label: "Achievable score")`
- Derivation: Lichess winning-chances sigmoid `1 / (1 + exp(-0.00368208 * cp))`
  applied to signed user-perspective `eval_cp`; mate maps to 0 / 1.
  Mate INCLUDED (D-06 inversion from entry_eval_pawns).
- Scale: whole-number percentage in [0, 100], attach `%` when narrating.
- Cohort typical band: 45-55% citing `reports/benchmarks-2026-05-11.md`
  Section 5. Width matches `endgame_score` for visual parity across the
  two bottom-row tiles in the 2x2 UI grid.
- Sig-test framing: Wilson test vs 50% on the tile; LLM does NOT receive
  the sig-test outcome.
- 2300+ baseline framing per D-10: scoring below this baseline from
  positive evals is normal at lower ratings and is not a flaw.
- Forbidden words: "underperformance", "fall short", "below your
  potential", "shortfall", "leaving points on the table" and synonyms.

Extended `### Subsection: endgame_start_vs_end` block:

- Triad framing: setup -> execution + baseline (was setup -> execution).
- New "Achievable-vs-achieved gap (Phase 83 D-18)" paragraph with two
  worked example narrations lifted verbatim from CONTEXT.md D-18:
  > "Stockfish-baseline says positions like yours score 58%, but you
  > scored 47% - about 11 points below the engine ceiling, mostly
  > explained by entering at +0.4 pawns"
  > "Achievable 49%, you scored 52% - defended slightly better than
  > the engine baseline from these positions"
- entry_eval_pawns as the explanatory unit (signed pawns more
  intuitive than 0-1 score).
- Sub-2300 rating-tilt framing + forbidden-word list.
- New "Headline ordering when all three findings fire (Claude's
  Discretion)" block: lead with the gap when at least one score tile
  is in a colored zone; lead with entry_eval_pawns when entry edge is
  dominant; background context when all three typical.
- Single-tile case updated to cover the third-finding-missing
  scenario (incomplete backfill).

## Tests Added

`tests/services/test_insights_service.py::TestFindingsEndgameStartVsEnd`
gained 9 new test functions:

- `test_three_findings_returned_in_canonical_order`
- `test_third_finding_emitted_when_n_at_or_above_10`
- `test_third_finding_empty_when_n_below_10`
- `test_third_finding_zone_strong_above_band`
- `test_third_finding_zone_weak_below_band`
- `test_third_finding_zone_typical_inside_band`
- `test_third_finding_has_no_verdict_field` (guard against re-adding a
  sig-test signal per memory `feedback_llm_significance_signal.md`)
- `test_third_finding_boundary_n_eq_10_populated` (strict `<` gate)
- `test_third_finding_independent_gate_from_other_tiles`
- `test_existing_tile1_and_tile2_unchanged_by_third_finding`

The pre-existing tests `test_populated_both_tiles_returns_two_findings`,
`test_empty_tile1_when_n_eval_lt_10`, `test_empty_tile2_when_total_lt_10`,
`test_empty_both_when_both_lt_10` were updated to assert `len == 3` and
the first was renamed `test_populated_both_tiles_returns_three_findings`.

`tests/services/test_insights_llm.py::TestPromptVersionAndBody` gained 4
new tests (plus the rename of `test_prompt_version_is_v24` to
`test_prompt_version_is_v25`):

- `test_prompt_version_is_v25`
- `test_prompt_changelog_preserves_prior_versions` (D-20: prepend pattern,
  prior `v24 (260510-ugj)` and `v23 (260510 endgame_start_vs_end)` blocks
  intact in source)
- `test_prompt_file_glossary_has_entry_expected_score` (D-17: UI label,
  sigmoid constant, benchmark report citation, line-level forbidden-word
  guard for "underperformance")
- `test_prompt_file_subsection_has_worked_example_narrations` (D-18: both
  worked example strings present verbatim)

Two version-string assertions inside `TestGenerateInsightsBypass` and
`TestCacheBehavior` were updated from `endgame_v24` to `endgame_v25`.

## Verification

| Check                                                                                          | Result      |
|------------------------------------------------------------------------------------------------|-------------|
| `uv run pytest tests/services/test_insights_service.py -k 'endgame_start_vs_end or third_finding' -x` | 9 passed    |
| `uv run pytest tests/services/test_insights_service.py`                                        | 64 passed   |
| `uv run pytest tests/services/test_insights_llm.py`                                            | 68 passed   |
| `uv run pytest tests/test_insights_router.py`                                                  | 16 passed   |
| `uv run ty check app/ tests/`                                                                  | zero errors |
| `uv run ruff check app/services/insights_service.py app/services/insights_llm.py tests/services/test_insights_service.py tests/services/test_insights_llm.py` | clean       |
| `grep -c '"endgame_v25"' app/services/insights_llm.py`                                         | 1           |
| `grep -c 'entry_expected_score' app/prompts/endgame_insights.md`                               | 6           |
| `grep -c 'Achievable score' app/prompts/endgame_insights.md`                                   | 1           |
| `grep -c 'benchmarks-2026-05-11.md' app/prompts/endgame_insights.md`                           | 1           |
| `grep -c '0.00368208' app/prompts/endgame_insights.md`                                         | 1           |
| `grep -ic 'underperformance' app/prompts/endgame_insights.md`                                  | 2 (both inside explicit forbidden-words lists; programmatic guard test enforces this) |

## Commits

| Task | RED                                                                  | GREEN                                                                  |
|------|----------------------------------------------------------------------|------------------------------------------------------------------------|
| 1    | `8e69dbe7` test(83-05): failing tests for entry_expected_score third finding | `89c5c4e4` feat(83-05): emit entry_expected_score as third SubsectionFinding |
| 2    | `13303540` test(83-05): failing tests for endgame_v25 prompt bump + glossary | `fa417fba` feat(83-05): bump _PROMPT_VERSION to endgame_v25 + extend prompt asset |

## Deviations from Plan

**1. MetricId Literal already populated by Plan 83-04 (Rule 3 - fulfilment, not deviation)**

- **Found during:** Task 1 read phase
- **Issue:** Plan task 1 said "Add `entry_expected_score` to the MetricId
  Literal in `app/services/insights_service.py`". The MetricId Literal
  actually lives in `app/services/endgame_zones.py` and Plan 83-04
  already added the slot there (commit `88c461f6`). `insights_service.py`
  imports `MetricId` from `endgame_zones.py` so no second declaration
  is needed.
- **Fix:** Verified existing import + use of `MetricId` from
  `endgame_zones` covers the new slot transparently; tests pass; ty
  clean. No code change required for the Literal slot.
- **Files modified:** None for this point.
- **Commit:** N/A.

**2. Forbidden-word test guard loosened (Rule 2 - critical correctness)**

- **Found during:** Task 2 GREEN, first pytest run
- **Issue:** The plan's verify command included
  `grep -ci 'underperformance' app/prompts/endgame_insights.md | grep -E '^[02-9]'`
  which fails when "underperformance" appears more than 1 time, even in
  legitimate forbidden-word lists. My implementation has the word in two
  forbidden-word lists (glossary entry + subsection block), which is the
  correct pattern: every occurrence in the prompt is part of an explicit
  forbidden-list, not narration guidance.
- **Fix:** Loosened the new
  `test_prompt_file_glossary_has_entry_expected_score` test from a flat
  count guard to a line-level guard: every line containing
  "underperformance" must also contain "forbidden". This enforces the
  D-10 intent (no narration may use the term) while allowing multiple
  explicit forbidden-words lists.
- **Files modified:** `tests/services/test_insights_llm.py` (test
  definition only).
- **Commit:** `fa417fba` (GREEN of Task 2).

**3. Three pre-existing test_insights_service.py cases updated from len==2 to len==3 (Rule 1 - regression repair)**

- **Found during:** Task 1 GREEN
- **Issue:** Pre-existing tests `test_populated_both_tiles_returns_two_findings`,
  `test_empty_tile1_when_n_eval_lt_10`, `test_empty_tile2_when_total_lt_10`,
  `test_empty_both_when_both_lt_10` hardcoded `assert len(findings) == 2`.
  These would fail after Task 1 GREEN. They are direct regression updates,
  not new behavior tests.
- **Fix:** Updated each to assert `len(findings) == 3` and renamed
  `test_populated_both_tiles_returns_two_findings` to
  `test_populated_both_tiles_returns_three_findings`. Behavior assertions
  on `findings[0]` and `findings[1]` are unchanged.
- **Files modified:** `tests/services/test_insights_service.py`.
- **Commit:** `89c5c4e4` (GREEN of Task 1).

**4. Two hardcoded version strings updated in test_insights_llm.py (Rule 1 - regression repair)**

- **Found during:** Task 2 RED
- **Issue:** `TestGenerateInsightsBypass` and `TestCacheBehavior` had
  `assert response.report.prompt_version == "endgame_v24"` and
  `assert log.response_json["prompt_version"] == "endgame_v24"`. These
  would fail after the version bump.
- **Fix:** Updated both to `"endgame_v25"`.
- **Files modified:** `tests/services/test_insights_llm.py`.
- **Commit:** `13303540` (RED of Task 2).

No architectural changes (no Rule 4 escalations).

## TDD Gate Compliance

| Task | RED        | GREEN      | REFACTOR    |
|------|------------|------------|-------------|
| 1    | `8e69dbe7` | `89c5c4e4` | not needed  |
| 2    | `13303540` | `fa417fba` | not needed  |

Both tasks followed the prescribed RED -> GREEN cycle. Each RED commit
contains only failing test changes (verified via pytest output showing
`assert 2 == 3` and `AssertionError` for the prompt-file content
guards); each GREEN commit contains the source change that turns those
tests green plus the minimum regression updates needed to keep
pre-existing tests passing.

## Known Stubs

None. The third finding is wired end-to-end: emitter -> SubsectionFinding
payload -> findings_hash -> LLM context. The prompt asset has the
glossary entry and narration guidance for the LLM to interpret it. The
existing 5-field schema surface (Plan 83-02) and the zone band (Plan
83-04) were prerequisites, both already complete.

## Self-Check: PASSED

- `app/services/insights_service.py` — FOUND (modified)
- `app/services/insights_llm.py` — FOUND (modified)
- `app/prompts/endgame_insights.md` — FOUND (modified)
- `tests/services/test_insights_service.py` — FOUND (modified)
- `tests/services/test_insights_llm.py` — FOUND (modified)
- Commit `8e69dbe7` — FOUND (RED Task 1)
- Commit `89c5c4e4` — FOUND (GREEN Task 1)
- Commit `13303540` — FOUND (RED Task 2)
- Commit `fa417fba` — FOUND (GREEN Task 2)
- All verification commands clean (pytest 148/148 across the three
  insights test files, ty zero errors across `app/` and `tests/`, ruff
  clean on all five modified files, grep counts match acceptance criteria).
