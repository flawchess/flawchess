---
phase: 241-codebase-cleanup
plan: 26
subsystem: testing
tags: [cleanup, comments, tests, tagger, engine-verdict, rename]

requires:
  - phase: 241-03
    provides: "cleanup.py codemod / scan / diff / apply-edits toolkit"
provides:
  - "tests/scripts (40 scope files) free of planning tags in comments, docstrings and test names"
  - "13 tagged test functions renamed to the rule they pin"
affects: [241-52, 241-67]

actuals:
  tokens: 23000
  tasks: 2
  commits: 2
plan_head_before: 7c80f445b033b665489f2cd0d18319346e6e0268
plan_head_after: 56da30e78cdfffecdf01e18995711faf1a45516c

tech-stack:
  added: []
  patterns:
    - "Hand edits batched as line-range / substring specs applied atomically (temp/241-26/multi.py), then scan --gate and diff to prove comment-only change"

key-files:
  created: []
  modified:
    - tests/scripts/tagger/precision_floors.py
    - tests/scripts/test_engine_dispatch_227_verdict.py
    - tests/scripts/test_engine_throughput_226_verdict.py
    - tests/scripts/test_retag_flaws.py
    - tests/scripts/test_opening_cache_repair.py

key-decisions:
  - "precision_floors.py measurement history kept (tables, numbers, dates) but headings and prose lose phase/plan/decision ids; the persistence-rule retirement story is rewritten as a rule ('never re-introduce a persistence check on detect_sacrifice without ...') instead of D-05/D-13 narration"
  - "Seed pointers SEED-124/125/165 were all in seeds/closed, so they were dropped rather than kept as (see SEED-NNN)"
  - "Skip reasons, f-string assertion messages and the 'D-03' reason substring asserted in test_engine_dispatch_227_verdict.py are strings and stay unchanged (D-13/D-14)"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 90min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 26: tests/scripts comment and test-name cleanup Summary

**tests/scripts carries no planning tags in comments, docstrings or test names; 13 decision-id test names now say which rule they pin, with a token-identical non-comment diff and an unchanged collection count (535).**

## Accomplishments

- Scope scan: 420 tagged lines in 40 files before, 0 after (`cleanup.py scan --gate` exit 0). `cleanup.py diff` exits 0: only comments, docstrings and normalized test names changed.
- Codemod pass: 123 lines changed in 23 files (reviewed with `git diff -U0`; none reverted). Two codemod results needed a hand touch-up (`pin (131-02)` table row lost its column alignment, one `(Phase 221 ...)` clause left a half sentence). No `#:`-style punctuation-start artifacts (grep clean).
- Hand edits: 284 spec operations (substring or line-range) plus 6 one-line `sed` capitalizations, applied atomically.
- `precision_floors.py` (156 tagged lines, the bulk) rewritten: measurement tables kept; headings renamed to dates; D-NN/TAGFIX/plan references folded into the actual rule (clearance additions, sacrifice persistence rule retired because it cannot tell a delayed recapture from a real sacrifice).
- Stale test-scaffolding prose deleted: the "this import fails until Task 2 creates..." RED-state note in `test_calibration_anchor_fit.py`, "Task N behaviors" dividers, `<behavior>`-block pointers.

## Renamed tests (old -> new, rule referred to)

All in `tests/scripts/test_engine_dispatch_227_verdict.py` unless noted. The script keeps the `d01_passes` helper and `d01=`/`d03=` output tokens (D-13), so the tests still assert those.

| Old | New | Rule |
|---|---|---|
| `test_d01_exact_margin_passes` | `test_signed_point_estimate_exact_margin_passes` | signed point-estimate: D == -margin passes |
| `test_d01_just_below_margin_fails` | `test_signed_point_estimate_just_below_margin_fails` | same, just below margin fails |
| `test_d01_positive_difference_passes` | `test_signed_point_estimate_positive_difference_passes` | better continuous mode passes |
| `test_mq_cli_better_continuous_passes_d01` | `test_mq_cli_better_continuous_passes_signed_point_estimate` | CLI line for the same rule |
| `test_mq_cli_much_worse_continuous_fails_d01_and_still_exits_zero` | `test_mq_cli_much_worse_continuous_fails_signed_point_estimate_and_still_exits_zero` | failing verdict still exits 0 |
| `test_d01_uses_the_mean_over_repeats_of_each_arm` | `test_signed_point_estimate_uses_the_mean_over_repeats_of_each_arm` | repeats pooled before the position mean |
| `test_d03_net_uses_fractional_continuous_regression_rate` | `test_net_regressions_use_fractional_continuous_regression_rate` | net regressions with repeat-flip allowance |
| `test_d03_continuous_fix_lowers_net` | `test_net_regressions_continuous_fix_lowers_net` | a fix counts in continuous's favor |
| `test_d03_net_equal_to_allowance_passes_and_above_fails` | `test_net_regressions_equal_to_allowance_pass_and_above_fail` | net == allowance passes, above fails |
| `test_mq_cli_d03_failure_is_printed` | `test_mq_cli_net_regression_failure_is_printed` | CLI prints the net-regression failure |
| `test_gates_d03_failure_holds_and_triggers_virtual_loss` | `test_gates_net_regression_failure_holds_and_triggers_virtual_loss` | composed gates verdict |
| `test_d17_shares_055_045_at_50_nodes_mean_050_fires_cap` (`test_engine_throughput_226_verdict.py`) | `test_cap_arm_shares_055_045_at_50_nodes_mean_050_fires_cap` | candidate-cap arm fires at mean share 0.50 |
| `test_d17_shares_below_half_at_both_budgets_do_not_fire_cap` (same file) | `test_cap_arm_shares_below_half_at_both_budgets_do_not_fire_cap` | cap arm stays off below 0.5 at both budgets |

The plan estimated 16 tagged names; the scan found 13 (11 + 2). `git grep` for the old names outside `.planning` is empty; no outside references existed.

## Collection and test results

- `pytest --collect-only tests/scripts tests/scripts/benchmarks tests/scripts/tagger`: 535 before, 535 after.
- Tagger (precision gate, real-game floors), engine dispatch/throughput/search-fixes verdict tests: 162 passed.
- Remaining script tests: 136 passed + 3 skipped, and 240 passed (generators, backfills, retag, opening cache repair, anchor fit, interleave, calibration).
- `ruff check tests/scripts` and `ruff format --check tests/scripts`: clean. `ty check app/ tests/ scripts/`: all checks passed.
- `cleanup.py scan --gate --scope scopes/241-26.txt`: 0 matches. `cleanup.py diff --scope scopes/241-26.txt`: exit 0.

## Deviations from Plan

### Environmental (not plan failures)

**1. Benchmark diff tests ran against a live benchmark DB and were not completed**
- `localhost:5433` accepts connections in this environment, so `tests/scripts/benchmarks/test_chapter*_diff.py` do not skip; they run the full ported §1/§3/§5 queries, which take many minutes each (`test_chapter1_diff.py` exceeded a 100 s cap; a combined run sat idle on the DB for several minutes and was killed).
- Only comments and docstrings changed in the four benchmark files touched (`conftest.py`, `test_chapter1_diff.py`, `test_chapter3_diff.py`, `test_chapter5_diff.py`); `cleanup.py diff` proves the code token stream is identical to PHASE_BASE and collection succeeds. Re-run them with the benchmark DB stopped (skip path) or in a long-timeout session if a pass is wanted.

**2. Serial pytest, no `-n 4`** (shared dev Postgres, per the parallel-execution notes). No pre-existing eval-lottery order failures reproduced.

**3. No spawn-time sentinel file** under `.git/worktrees/...`: writes to the shared git dir are blocked for this agent, so the per-commit cwd-drift sentinel (#3097) was not created; HEAD/branch/base assertions were verified by hand and all commits stayed in the worktree.

### Auto-fixed Issues

None. No assertion, fixture, parametrize id, string, precision floor, `SUPPRESSED_MOTIFS` entry or fixture path was edited.

## Notes for follow-up (outside this plan's scope)

- `test_opening_cache_repair.py` still names the memory file `project_eval_lottery_test_isolation` in its module docstring; it is not a planning tag, so the scan does not flag it.
- Strings still carrying old ids by design: `test_engine_dispatch_227_verdict.py:1486` asserts `"D-03"` in a script reason; `test_retag_flaws.py` ("SC4 ..." assertion messages), `test_detector_precision.py` (`D-08`/`D-10`/`D-13` in print and failure messages, `post-D-09`), `test_gen_global_percentile_cdf_unchanged.py` ("Phase 94.4 golden" message), and the skip reasons in `test_backfill_user_percentiles_classifier.py` and `test_gen_global_percentile_cdf_pooled.py`. These are strings (D-14), so they need a separate decision if they should change.

## Known Stubs

None.

## Threat Flags

None. T-241-42 mitigated: `cleanup.py diff` compares every code token against PHASE_BASE and exits 0; the tagger precision gate and the verdict tests pass.

## Task Commits

1. **Task 1: tagger, benchmark and engine-verdict tests** - `ee2063035` (`chore(comments): tests/scripts (tagger, benchmarks, engine verdicts)`)
2. **Task 2: generators, backfills, repair tests** - `56da30e78` (`chore(comments): tests/scripts (generators, backfills, repair)`)

## Self-Check: PASSED

Both commits are ancestors of HEAD; scan and diff gates re-run on the final tree (0 matches, exit 0).
