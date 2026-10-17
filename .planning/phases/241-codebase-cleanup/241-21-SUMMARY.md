---
phase: 241-codebase-cleanup
plan: 21
subsystem: testing
tags: [cleanup, comments, tests, eval-pipeline, engine, maia]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff toolkit"
  - phase: 241-03
    provides: "cleanup.py codemod and decision commands"
provides:
  - "18 eval-pipeline, engine and Maia test files free of planning tags in comments, docstrings and test names"
affects: [241-52, 241-67, 241-70]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: 25c4a36a56d588ddc53d8fb9ecccb82909c167e9
plan_head_after: f4d355d8160e0fee5c0958e7200f598f876b32a4

tech-stack:
  added: []
  patterns:
    - "Hand edits batched through a compact line-spec turned into an apply-edits JSON (temp/241-21/mk.py), old text read from the file so a stale line number is rejected"

key-files:
  created: []
  modified:
    - tests/services/test_full_eval_drain.py
    - tests/services/test_eval_queue.py
    - tests/services/test_eval_drain.py
    - tests/services/test_eval_apply.py
    - tests/services/test_eval_drain_stage_b.py
    - tests/services/test_eval_utils.py
    - tests/services/test_eval_confidence.py
    - tests/services/test_eval_chart_service.py
    - tests/services/test_engine.py
    - tests/services/test_engine_nodes.py
    - tests/services/test_engine_pv.py
    - tests/services/test_best_move_candidates.py
    - tests/services/test_accuracy_acpl.py
    - tests/services/test_backfill_accuracy_acpl.py
    - tests/services/test_maia_encoding.py
    - tests/services/test_maia_engine.py
    - tests/services/test_maia_parity.py
    - tests/services/write_path_golden_scenarios.py

key-decisions:
  - "Sentry issue ids (FLAWCHESS-8W, -A0, -5V, -6B) in comments and docstrings are external pointers, not planning tags, and the scan does not match them; kept where they sit next to a still-true explanation, dropped together with an adjacent quick-task id"
  - "Tag-bearing strings (assert messages, 94 lines left in scope) are untouched per the plan prohibition on any string change"

patterns-established:
  - "Rename every tagged test class or function name to the behavior it checks, then verify via collect-only id diff that only the intended ids changed"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 100min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 21: Eval, Engine and Maia Test Comment Cleanup Summary

**All planning tags are gone from comments, docstrings and test names in 18 eval-pipeline, engine and Maia test files (470 tagged lines), with identical assertions, equal collection counts and a green run including the write-path golden scenarios.**

## Performance

- **Tasks:** 2
- **Files modified:** 18 (all under tests/services/)
- **Diff:** 522 insertions, 539 deletions, comments and docstrings only plus 9 renamed test ids

## Accomplishments

- First scan of scopes/241-21.txt: 470 tagged lines (8 of them test names). Final `scan --gate` over the scope: 0 matches, exit 0. `diff` over the scope: 18 changed, no residue, exit 0 (no token outside comments, docstrings and normalized test names differs from PHASE_BASE).
- Codemod rewrote 197 lines (136 in Task 1 files, 61 in Task 2 files); about 280 hand-edit spans (apply-edits batches of 30, 41, 120, 74 and 7, plus 8 single-line fixes) covered the rest and the provenance the scanner does not match (`D-7`, `Plan-03`, `Task 1`, `Pitfall-1`, `151-MAIA-CONTRACT.md`, `Wave 0`).
- History narration rewritten as present-tense rules or deleted (e.g. "Previously test_excludes_guests asserted the opposite", "is_analyzed renamed to is_lichess_eval_game", "moved to eval_apply.py").
- Canonical glossary terms used where prose was rewritten anyway: "entry-ply lane" (row 33), "flaw counts" (row 28), "PV-line blob" (row 29).

## Renamed tests (old -> new)

| File | Old | New |
|---|---|---|
| test_eval_apply.py | `TestCandidateGate::test_sparse_targets_book_depth_not_collapsed_cr01` | `test_sparse_targets_book_depth_not_collapsed` |
| test_eval_apply.py | `class TestPitfall1Fallback` | `class TestMissingSecondBestFallback` |
| test_full_eval_drain.py | `class TestWr02Repointed` | `class TestDedupGatesOnLichessEvalsAt` |
| test_full_eval_drain.py | `test_wr02_engine_source_included` | `test_dedup_engine_source_included` |
| test_full_eval_drain.py | `test_wr02_lichess_source_excluded` | `test_dedup_lichess_source_excluded` |
| test_full_eval_drain.py | `TestAccuracyAcplHook::test_seed125_clear_direction_reclassification_nulls_blob_stamp` | `test_clear_direction_reclassification_nulls_blob_stamp` |
| test_full_eval_drain.py | `TestAccuracyAcplHook::test_seed125_set_direction_refresh_stamps_blob_completed` | `test_set_direction_refresh_stamps_blob_completed` |
| test_full_eval_drain.py | `class TestSeed049GameEndingPly` | `class TestGameEndingPlyNotAHole` |

`TestPitfall1Fallback` was not in the scan's `test-name` list (the scanner does not match `Pitfall`) but is a planning label, so it was renamed under D-14. `git grep` for every old name outside `.planning` finds nothing, and no new name collides with an existing one in its module.

## Collection counts (before -> after)

| Scope | Before | After |
|---|---|---|
| Task 1 files (full_eval_drain 66, eval_queue 60, eval_drain 39) | 165 | 165 |
| All 17 test files (write_path_golden_scenarios.py has no tests) | 406 | 406 |

A `collect-only` id diff shows exactly the 8 renames above (12 test ids affected, counting those under renamed classes) and nothing else.

## Gates

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-21.txt` | exit 0, 0 matches |
| `cleanup.py diff --scope scopes/241-21.txt` | exit 0, 18 changed, no residue |
| `ruff check tests/services`, `ruff format --check tests/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `pytest` (serial) on the 17 test files plus `test_flaw_upsert_equivalence.py` (the write-path golden scenarios) | 410 passed, 4 skipped |
| `source_scan_tests.sh` Python half, run serially | 95 + 5 passed (same as the 241-02 baseline) |
| `source_scan_tests.sh --fe` half | not run: this plan touches no frontend file and `frontend/node_modules` was not installed in this worktree |
| Codemod bug grep `^\s*(#\|//\|\*)\s*[:;,]\s` | no hits in scope |

## Task Commits

1. **Task 1: test_full_eval_drain.py, test_eval_queue.py, test_eval_drain.py** - `a33f1e59f`
2. **Task 2: the other 15 eval/engine/Maia test files** - `f4d355d81`

`commits: 2` above is measured with `git rev-list --count 25c4a36a5..HEAD` before the SUMMARY commit.

## Decisions Made

See `key-decisions` above. Beyond the plan text: a test-name pass over the scanner's blind spots (`Pitfall`, trailing `_cr01`-style suffixes) and unmatched provenance shapes was done by hand with targeted greps.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` (lockfile only, no new packages) before the ty baseline, which was clean before any edit. No tracked file changed.

**2. [Plan note] Serial pytest, no `-n 4`**
- Per the parallel-execution instruction (shared dev Postgres across sibling worktrees), every pytest run here is serial.

**3. [Plan note] `TestPitfall1Fallback` renamed although not in the scan's test-name list**
- See the rename table; the rename is the same D-14 treatment and the diff tool normalizes it.

**Total deviations:** 1 blocking env prep, 2 plan notes. No assertion, fixture, parametrize id, assert message, scenario value or fixture file changed.

## Issues Encountered

- **Order-dependent failures in the plan's literal pytest argument order (pre-existing, environmental).** Running `test_full_eval_drain.py` before `test_eval_queue.py` in one session makes `TestGuestExclusion::test_guest_exclusion`, `TestTier3Lottery::test_tier3_guest_excluded_from_lottery` and `TestTier3Step1PredicateShape::test_guest_needs_engine_only_never_picked` fail (a guest game is picked from the global lottery). The same three fail identically when the UNMODIFIED files from `HEAD` are run in that order (checked with temporary copies, removed afterwards), and all 165 pass in alphabetical file order and each file passes alone. This is the known global-and-random lottery isolation issue (a non-guest needs-engine game leaked by another test), not caused by this plan, and was not touched (out of scope).
- The scanner and the codemod do not see several provenance shapes (`D-7`, `Plan-03`, `Pitfall-1`, `151-MAIA-CONTRACT.md`, `Task 1`); a broad grep after the scan found and cleared them in comments and docstrings.
- Left on purpose: 94 lines in scope still hold tag text inside **string literals** (assert messages such as `"... (D-117-08)"`, `"... — SEED-054 ..."`), which the plan forbids changing, and 5 Sentry issue ids (`FLAWCHESS-8W`, `-A0`, `-5V`, `-6B` in comments and docstrings). A later plan that is allowed to change assert messages could finish these.

## Known Stubs

None.

## Threat Flags

None. Only comments, docstrings and test names changed (T-241-37 mitigated: `cleanup.py diff` plus equal collection ids plus a green run).

## Self-Check: PASSED

Files verified present: all 18 modified test files and this SUMMARY. Commits `a33f1e59f` and `f4d355d81` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
