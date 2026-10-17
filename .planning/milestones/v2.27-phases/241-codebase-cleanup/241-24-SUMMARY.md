---
phase: 241-codebase-cleanup
plan: 24
subsystem: testing
tags: [cleanup, comments, tests, planning-tags, codemod]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "tests/conftest.py and tests/test_[a-f]*.py (35 files in scopes/241-24.txt) free of planning tags in comments, docstrings and test names"
affects: [241-25, 241-26, 241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 1cee4f3aafad21ee45340b5560864b51abf3bf69
plan_head_after: 91f03dbe6889897176a1b94db4a85ad72b89fd4d

tech-stack:
  added: []
  patterns:
    - "Compact edit specs (path, line, find, repl | n-lines, text) turned into apply-edits JSON by a scratch helper (temp/241-24/mk.py, gitignored)"

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_eval_worker_endpoints.py
    - tests/test_endgame_service.py
    - tests/test_admin_activity_stats.py
    - tests/test_chesscom_client.py
    - tests/test_dependency_isolation.py
    - "plus 22 more tests/test_[a-f]*.py files (28 of the 35 scoped files changed)"

key-decisions:
  - "Gen-1 tombstone comments in test_eval_worker_endpoints.py, test_endgame_service.py and test_eval_remote_schema_bounds.py ('X was deleted, coverage ported to Y') are pure history narration and were deleted rather than rewritten"
  - "Tag-free names were chosen to say what the test checks; the 3 scan-flagged names plus 3 extra tag-bearing names (listed below) were renamed"
  - "Identifiers left alone because the diff gate forbids code-token changes: _SEED076_PGN, _PHASE_169_SHAPED_PGN, _SIX_PLY_PGN_142 / _BLUNDER_SUBMIT_EVALS_142 (tag-bearing module constants, flag for a later identifier plan)"
  - "assert messages and other string literals that still carry tags (e.g. '(Phase 112 D-07)', '(T-147-02)', '(D-06)') were not touched, per the test-file rule (comments, docstrings and test names only)"

patterns-established:
  - "Broader leftover grep beyond the scan regex: D1/D4/D-5 single-digit tags, SC-2, 'Task N', 'Quick NNN', 'UAT fix', dated review pointers, Nyquist/Wave 0"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 85min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 24: Test comments (conftest + test_[a-f]*) Summary

**All planning tags are gone from comments, docstrings and test names in tests/conftest.py and tests/test_[a-f]*.py (486 scanned matches plus about 40 shapes the scan regex misses), with an empty token diff against PHASE_BASE and 677 tests collected before and after.**

## Performance

- **Duration:** ~85 min
- **Tasks:** 2
- **Files modified:** 28 of the 35 scoped files (7 were already clean and stay untouched: tests/__init__.py, test_auth.py, test_backfill_multipv.py, test_bookmark_schema.py, test_bookmarks_router.py, test_dev_clock.py, test_email_case_uniqueness.py)

## Accomplishments

- Task 1 (`5cd3be611`): tests/conftest.py (comments and docstrings only, 18 spans), test_eval_worker_endpoints.py (the largest: 136 scan hits, 133 spans), test_endgame_service.py, test_eval_queue_service.py, test_eval_remote_schema_bounds.py.
- Task 2 (`91f03dbe6`): the other 23 files with hits. Ends with the plan gates over the whole scope.
- Codemod vs hand edits: the codemod rewrote 202 lines in 23 files (reviewed line by line, none reverted); the remaining 291 flagged lines and the shapes the scanner misses took about 305 hand-edit spans through `apply-edits` (18 + 129 + 4 + 28 + 107 + 10 + 2 + 6 + 1 across nine batches).
- Scan before: 486 matches in 35 files. After: 0.

## Renamed tests (old -> new)

| File | Old | New |
|---|---|---|
| test_endgame_service.py | `TestPhase872PerBucketDeltaES` (class, scan-flagged) | `TestPerBucketDeltaES` |
| test_endgame_service.py | `test_phase_87_1_outputs_unaffected_by_gaps_by_bucket` | `test_per_class_gap_outputs_unaffected_by_gaps_by_bucket` |
| test_admin_activity_stats.py | `test_resolve_window_d30_d90_end_today_inclusive` (scan-flagged; parametrized on the real range keys d30/d90, whose ids `[d30-30]`/`[d90-90]` are unchanged) | `test_resolve_window_30_and_90_day_ranges_end_today_inclusive` |
| test_admin_activity_stats.py | `test_fetch_guest_train_d11_d12_semantics` (scan-flagged) | `test_fetch_guest_train_promotion_cutoff_and_purged_exclusion` |
| test_bot_pgn_clk_roundtrip.py | `test_phase_169_shaped_pgn_normalizes` | `test_hmmss_clock_pgn_normalizes` |

The plan expected 5 tagged names; the scan flagged 3 (`TestPhase872PerBucketDeltaES`, `test_resolve_window_d30_d90_...`, `test_fetch_guest_train_d11_d12_semantics`) and two more carried obvious phase numbers (`test_phase_87_1_...`, `test_phase_169_...`). `git grep` for each old name outside `.planning` finds nothing. The `test_phase_opening_maps_to_*` and `test_phase_tags_*` names refer to the game phase, not a planning phase, and stay.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-24.txt` | exit 0 (35 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-24.txt` | exit 0 (35 selected, 28 changed, no residue) |
| `pytest --collect-only` over the 34 test files + conftest, before / after | 677 / 677; the id diff shows only the five renames above |
| `pytest -q` over the same files, serial (no `-n`, shared Postgres) | 677 passed |
| `ruff check tests`, `ruff format --check tests` | clean |
| `ty check app/ tests/ scripts/` | all checks passed |

Baseline before any edit: ruff check, ruff format --check and ty were all clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` (lockfile only, no new packages) before the baseline gates.

**2. [Plan adaptation] Tests run serially, not with `-n 4`**
- The parallel-execution notes for wave 3 forbid `-n` against the shared dev Postgres, so the plan's `pytest -n 4 -x` commands ran serially. No pre-existing order-dependent failure showed up; all 677 passed. `source_scan_tests.sh` was not run: no file under `app/` or `frontend/src` changed, and none of the 35 files here is read as source text by those tests.

**3. [Rule 2 - stale content, STYLE-GUIDE 2.2] Wording fixes next to removed tags**
- Several docstrings carried history narration next to the tag (for example "replacing the previous Conv/Recov peer-diff bullets", "no longer contains ANY third-party", "NO LONGER deferred"). These were rewritten in present tense or reduced to the rule. The Gen-1 `_apply_submit` reference in a `/atomic-submit` docstring pointed at a function that no longer exists; the sentence now states the guard directly.
- test_chesscom_client.py: the codemod had turned "NOT a skip - Pitfall 1 must not be reintroduced..." into a broken sentence; rewritten ("treating it as one would reintroduce an infinite re-fetch loop").

**Total deviations:** 1 blocking env prep, 1 plan adaptation, 1 wording group; none touch code, assertions, fixtures or strings.

## Issues Encountered

- The sandbox rejects compound shell lines with `git` or computed arguments; commands were issued one at a time.
- `ruff format` collapsed one docstring in test_eval_worker_endpoints.py after a deleted reference line; run once, diff gate still empty.

## Known Stubs

None.

## Threat Flags

None. Comment, docstring and test-name edits only; conftest.py code tokens are identical to PHASE_BASE (verified by `cleanup.py diff`, T-241-40 mitigated).

## Notes for downstream plans

- Left on purpose (string literals or code identifiers, outside the comment/docstring/test-name rule): assert messages in test_eval_worker_endpoints.py, test_flaws_materialization.py, test_flaws_repository.py, test_flaw_predicate.py, test_dependency_isolation.py that still say `(Phase 112 D-07)`, `(T-147-02)`, `(D-06)`, `(GEMS-06)`, `(PUSH-04)`; the constants `_SEED076_PGN` and `_PHASE_169_SHAPED_PGN`.
- `FLAWCHESS-39`, `FLAWCHESS-8B` and `FLAWCHESS-9J` Sentry issue ids in test_chesscom_client.py and test_eval_worker_endpoints.py were kept: they point at production issues, not planning artifacts.
- test_email_case_uniqueness.py keeps its "Security review 2026-10-14" paragraph: it explains the bug the tests guard against (comment-the-fix rule), no tag.
- `_cache_targets`, `_worker_evaluated_plies`, `_apply_eval_results` (241-52/241-68) and `_TACTIC_CHIP_CONFIDENCE_MIN` (241-67) comments were kept by name as the plan instructed.

## Self-Check: PASSED

Commits `5cd3be611` and `91f03dbe6` verified as ancestors of HEAD; scan/diff exit codes recorded above.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
