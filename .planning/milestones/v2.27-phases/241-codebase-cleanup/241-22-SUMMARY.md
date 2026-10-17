---
phase: 241-codebase-cleanup
plan: 22
subsystem: testing
tags: [cleanup, comments, tests, planning-tags, insights, endgame, percentile]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod/decision"
provides:
  - "19 tests/services files free of planning tags in comments, docstrings and test names"
affects: [241-54, 241-67]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: c493916b710b39bea7fa78dac00ab4a3d2d085b8
plan_head_after: 96996be1ea8294fefa49529da5f62241171a5363

key-files:
  created: []
  modified:
    - tests/services/test_insights_llm.py
    - tests/services/test_insights_service.py
    - tests/services/test_insights_service_series.py
    - tests/services/test_opening_insights_service.py
    - tests/services/test_opening_insights_arrow_consistency.py
    - tests/services/test_canonical_slice_sql.py
    - tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py
    - tests/services/test_endgame_ranked_parity.py
    - tests/services/test_endgame_ranked_service.py
    - tests/services/test_endgame_zones.py
    - tests/services/test_global_percentile_cdf.py
    - tests/services/test_percentile_compute_gate.py
    - tests/services/test_percentile_compute_registry.py
    - tests/services/test_score_confidence.py
    - tests/services/test_stats_service_phase_entry.py
    - tests/services/test_time_pressure_service.py
    - tests/services/test_user_benchmark_percentiles_service.py
    - tests/services/test_user_benchmark_percentiles_service_real_data.py
    - tests/services/ranked_payload_fixtures.py

key-decisions:
  - "Assertion messages, SQL provenance strings that are asserted, the pytest.skip reason and the golden prompt are strings and stay untouched (D-14/D-15), even where they still carry a tag such as (Pitfall 1) or (D-5)"
  - "Test labels that are local to a file (T5-T9, B1-B7, A1) were kept: they cross-reference test names and are not planning pointers"

patterns-established:
  - "Test cleanup loop: codemod -> git diff -U0 review -> scan -> apply-edits batch built by a temp/241-22 script that reads the old text from the file -> broad grep for shapes the scan misses -> scan --gate / diff / ruff / ty / pytest"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 100min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 22: Insights, opening, endgame, percentile and score test comments Summary

**Planning tags (Phase/Plan/Task/D-NN/WR-NN/Pitfall/quick-task IDs, requirement ids, UAT notes) are stripped from comments, docstrings and test names in 19 tests/services files, with the non-comment diff limited to 9 renamed tests/classes; 510 + 279 tests still collect and pass, golden prompt untouched.**

## Performance

- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 19 (no files created apart from this SUMMARY)
- **Diff vs PHASE base:** 528 insertions, 589 deletions, comments/docstrings/names only

## Accomplishments

- Task 1 (5 insights and opening-insights files): 456-line scope scan reduced to zero; test_insights_llm.py docstrings still name the five `_apply_*_filter` functions only where they did before (241-54 renames those later).
- Task 2 (14 endgame, canonical-slice, percentile, score and time-pressure files): scan reduced to zero; `tests/services/golden/insights_user_prompt.txt` untouched.
- Stale content fixed while there (STYLE-GUIDE 2.2): the "INTENDED RED / Wave 0" banner in test_canonical_slice_sql.py (the builders exist now), the "bumped to endgame_v30" guard text, a deprecation docstring that promised a replacement module which does not exist, history narration about removed tests.

## Renamed tests and classes (old -> new)

No reference to any old name remains outside `.planning` (`git grep`/`grep -r` checked).

| Old | New |
|---|---|
| `TestPhase874PromptVersion` (test_insights_llm.py) | `TestPromptVersionPinned` |
| `TestPhase876LLMPayloadExtension` (test_insights_llm.py) | `TestNonEndgameEloPayloadExtension` |
| `TestD15LlmPathInvariant` (test_insights_service.py) | `TestLlmTypeBreakdownPerTcPath` |
| `test_recovery_band_after_d10` (test_endgame_zones.py) | `test_recovery_band_contains_030_as_typical` |
| `test_existing_94_3_per_tc_pooled_body_byte_identical_after_pitfall_1` (parity file) | `test_existing_per_tc_pooled_body_byte_identical_after_user_id_widening` |
| `TestPitfall1UserIdWideningExistingBuilders` (test_canonical_slice_sql.py) | `TestUserIdWideningExistingBuilders` |
| `TestPitfall1UserIdWideningNewBuilders` | `TestUserIdWideningNewBuilders` |
| `test_per_user_values_has_pitfall_1_comment_for_existing_builders` | `test_per_user_values_has_user_id_widening_comment_for_existing_builders` |
| `test_pitfall_1_comment_present` (two classes, one each) | `test_user_id_widening_comment_present` |

The scan's `test-name` kind flagged 4 of these (3 classes plus `test_recovery_band_after_d10`); the other 5 renames came from a name-shape grep (`pitfall`, `94_`, `phase`, `d\d\d`) because the scan does not flag them.

## Collection counts (before / after)

| Group | Before | After |
|---|---|---|
| Task 1 files (5) | 279 | 279 |
| Task 2 files (13 test files; ranked_payload_fixtures.py has no tests) | 510 | 510 |

## Codemod vs hand edits

| Task | Codemod lines rewritten | Hand-edit spans (apply-edits) | Small direct fixes |
|---|---|---|---|
| 1 | 151 (all kept after `git diff -U0` review) | 73 (llm) + 66 (4 other files) = 139 | 4 |
| 2 | 62 (all kept) | 93 (canonical-slice pair) + 71 (11 other files) = 164 | 4 |

The codemod flagged 120 "needs hand edit" lines in Task 2 and a few hundred in Task 1; most were keyword-led references ("per D-NN", "Plan 04") and single-digit tags (`D-5`, `D-1`, `T1`) that the scan regex misses. Those were found with a broad grep (`D-?\d{1,2}`, `Phase \d`, `Plan [A-Z0-9]`, `Phase-NN`, `SEC\d`, `SURGE`, `Pitfall`, `quick`, `UAT`, dates in task IDs).

## Gates (final tree, executed serially, no `-n`)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-22.txt` | exit 0 (19 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-22.txt` | exit 0, 19 files changed, no residue |
| `ruff check tests/services`, `ruff format --check tests/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed |
| pytest, Task 1 files | 279 passed |
| pytest, Task 2 files | 510 passed, 1 skipped (the deliberately skipped test_global_percentile_cdf module) in 117 s |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| `source_scan_tests.sh` python half, run serially | 95 + 5 passed |

Environmental: pytest was run without `-n` and the `source_scan_tests.sh` python commands were run without `-n 4`, because sibling executors share the dev Postgres and xdist worker DB names collide across checkouts. This is not a plan failure. `uv sync --group maia-inference` and `npm --prefix frontend ci` were run in this fresh worktree first.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Stale comment] Wrong or obsolete test text fixed while removing tags**
- **Found during:** both tasks
- **Issue:** several comments were contradicted by the code or described work that no longer exists (a "RED until Plan 02 ships" banner, `_PROMPT_VERSION is bumped to endgame_v30`, a deprecation note promising a replacement test module that is not in the repo).
- **Fix:** rewritten to the present tense or deleted; no code touched.
- **Files modified:** test_canonical_slice_sql.py, test_insights_llm.py, test_global_percentile_cdf.py
- **Commit:** 3647fccfc, 96996be1e

### Plan-text adaptations

**2. Plan expected 5 tagged test names; 9 renames were made.** D-14 says every tagged test name is rewritten, and a name-shape grep found `Pitfall1`/`94_3`/`pitfall_1` names the scan does not flag.

**3. Assertion messages with tags were left.** `"(Pitfall 1)"`, `"(D-5)"`, `"(SC-1 inclusion floor)"`, `"WR-01: ..."`, `"FIND-01 violation"`, the `pytest.skip` reason and the asserted app SQL comment `"user_id widened per Phase 94.4 Pitfall 1"` are string literals; the plan prohibits changing strings and `cleanup.py diff` verifies it. The app SQL comment itself is part of the golden SHA-256 pinned in test_canonical_slice_sql.py, so it stays until a plan that owns `app/services/canonical_slice_sql.py` and regenerates the golden decides otherwise.

## Findings for later plans (not acted on)

- `tests/services/test_global_percentile_cdf.py` holds no collectible tests (module-level `pytest.skip`) and its replacement module was never written; it can be deleted. The docstring now says so.
- `test_prompt_version_is_v33` (two classes in test_insights_llm.py) and `test_prompt_version_is_endgame_v39` / `test_version_is_endgame_v39` assert `endgame_v49`; the version in the name is stale. Not tag-shaped, so left (rename would be a naming finding for the audit).
- Assert-message and SQL-literal tags listed in deviation 3 remain in `tests/services` by design.

## Known Stubs

None.

## Issues Encountered

- A tool guard in this runtime refuses compound shell commands that mention git or use computed values; commands were split into plain separate calls.
- One accidental backgrounding of a long pytest run (120 s tool limit); it completed and was read from its output file before any further DB test run.

## Self-Check: PASSED

- 19 files in `files_modified` exist and are modified; commits `3647fccfc` and `96996be1e` are ancestors of HEAD.
- `tests/services/golden/insights_user_prompt.txt` unchanged (`git status` clean for that path).
- STATE.md and ROADMAP.md not modified.
