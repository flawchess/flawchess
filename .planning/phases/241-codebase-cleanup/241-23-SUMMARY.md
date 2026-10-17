---
phase: 241-codebase-cleanup
plan: 23
subsystem: testing
tags: [cleanup, comments, tests, services, import, normalization, train, openings, stats]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff toolkit"
  - phase: 241-03
    provides: "cleanup.py codemod and decision commands"
provides:
  - "43 test files (22 in tests/services, 21 in tests/test_[n-z]*.py) free of planning tags in comments, docstrings and test names; the other 9 scope files were already clean and stay untouched"
affects: [241-52, 241-67, 241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: c1f8005b4aeea1f776bbdb9f93e5eac6d2b811b4
plan_head_after: e20683570b19c422b453c6ff5f037ad0db16f50b

tech-stack:
  added: []
  patterns:
    - "Hand edits batched through temp/241-23/ed.py: a compact {path, line, n, new} list that reads the old text from the file and feeds cleanup.py apply-edits, so a stale line number is rejected"

key-files:
  created: []
  modified:
    - tests/services/test_bot_game_pgn.py
    - tests/services/test_chesscom_to_lichess.py
    - tests/services/test_current_strength_service.py
    - tests/services/test_feedback_ask_service.py
    - tests/services/test_import_service.py
    - tests/services/test_import_service_queue.py
    - tests/services/test_import_service_stage_a.py
    - tests/services/test_library_include_pasted.py
    - tests/services/test_library_service.py
    - tests/services/test_migration_178_accuracy_imported.py
    - tests/services/test_normalization.py
    - tests/services/test_normalize_pasted_game.py
    - tests/services/test_sentry_capture_gaps.py
    - tests/services/test_sharp_filler.py
    - tests/services/test_store_bot_game_service.py
    - tests/services/test_store_paste_game_service.py
    - tests/services/test_train_leaderboard.py
    - tests/services/test_train_medals.py
    - tests/services/test_train_pool.py
    - tests/services/test_train_reminder_service.py
    - tests/services/test_train_scheduler.py
    - tests/services/test_train_score_parity.py
    - tests/test_normalization.py
    - tests/test_opening_lookup.py
    - tests/test_openings_repository.py
    - tests/test_openings_service.py
    - tests/test_openings_time_series.py
    - tests/test_password_reset.py
    - tests/test_push_send.py
    - tests/test_query_utils.py
    - tests/test_remote_eval_worker.py
    - tests/test_stats_repository.py
    - tests/test_stats_repository_phase_entry.py
    - tests/test_stats_router.py
    - tests/test_stats_schemas.py
    - tests/test_stats_service.py
    - tests/test_users_account_type_invariant.py
    - tests/test_users_profile_impersonation_field.py
    - tests/test_users_router.py
    - tests/test_worker_heartbeats.py
    - tests/test_zobrist.py
    - tests/test_no_conversion_elo_string.py
    - tests/test_reimport.py

key-decisions:
  - "Pointers to seeds (SEED-023, 042, 093, 121, 135, 147, 154, 191, 192) were dropped, not kept as (see SEED-NNN): every one marks shipped work, none points at deliberately deferred work (STYLE-GUIDE 2.1)"
  - "Tag-bearing strings inside test code (assert messages such as '(D-03)', and fixture strings such as 'SEED-138-repository-probe/1.0') are untouched per the plan prohibition on any string change; Sentry issue ids (FLAWCHESS-64, -96, -8B) are external pointers, not planning tags, and stay"
  - "History narration next to a removed tag was rewritten as the present-tense rule (e.g. 'Reverses the pre-260702-mnd behavior' became '_build_card has no severity gate ...'); 'oracle' wording that carried no tag was left alone (not tag text)"

patterns-established:
  - "Rename every tagged test class or function to the behavior it checks, then verify with git grep outside .planning and an unchanged collect-only count"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 23: Test comment cleanup (tests/services + tests/test_[n-z]*.py) Summary

**Planning tags are gone from comments, docstrings and test names in 43 test files; collection counts (650 + 648) and results are unchanged, and `cleanup.py diff` shows no non-comment change.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 2
- **Files modified:** 43 (of the 52 in scope; 9 were already clean)

## Accomplishments

- `cleanup.py scan --gate --scope scopes/241-23.txt` exits 0 (52 files, 0 matches), `cleanup.py diff --scope scopes/241-23.txt` exits 0 (52 selected, 43 changed, no residue).
- 4 tagged test names rewritten to say what they check; no other test, class or parametrize id changed.
- A broad grep beyond the scan regex (D-N, P-NN, T-NN, SC-N, WR-/CR-NN, Pitfall, RESEARCH, quick-task ids, `NNN-NN` plan ids, Wave-0, ROADMAP, gap closure) found leftovers in comments the scan misses (`P-02`, `Wave 0 scaffolding`, `ROADMAP SC 3`, `D-3`, `D-1`, `Task 3 checkpoint`, `Pitfall-1`, `P-01`, `TDD RED`); all fixed.

## Renamed tests (old -> new)

| File | Old | New |
|---|---|---|
| tests/services/test_bot_game_pgn.py | `TestHappyPath.test_full_d03_header_block` | `test_full_header_block` |
| tests/services/test_bot_game_pgn.py | `TestHappyPath.test_header_order_matches_d03_exactly` | `test_header_order_matches_expected_exactly` |
| tests/services/test_bot_game_pgn.py | `TestD05Omission` | `TestNoAnchorOmission` |
| tests/services/test_normalize_pasted_game.py | `test_returned_fields_match_d07_and_hash_contract` | `test_returned_fields_match_pasted_game_and_hash_contract` |

`git grep` of every old name outside `.planning` finds nothing, so no reference outside this plan's files needed an update. No pytest `-k` selector, `pyproject.toml` or CI config names any of them.

## Collection counts and test runs

| Set | Collected before | Collected after | Result |
|---|---|---|---|
| tests/services files (Task 1) | 650 | 650 | 646 passed, 4 skipped (the skips are the pre-existing "implementation pending" stage-A scaffolds) |
| tests/test_[n-z]*.py files (Task 2) | 648 | 648 | 648 passed |
| source-scan tests, python half (run serially, no `-n`) | | | 95 + 5 passed |

## Codemod vs hand edits

- `cleanup.py codemod` (written once over all 52 files): 242 lines changed in 40 files, 278 flagged "needs hand edit", 0 refused. `git diff -U0` was reviewed in full; none of the 242 rewrites needed to be reverted. The known codemod bug (line-leading tag collapsing to bare punctuation) did not occur; one `# -- the tie resolves ...` comment it left starting with a dash was reworded by hand.
- Hand edits: 287 `apply-edits` spans in 7 batches (31 + 48 + 76 + 9 + 106 + 12 + 5), covering the flagged lines, re-wraps of comments the codemod left short, and the leftovers found by the broad grep.
- Comments deleted as provenance only: the Phase/Plan/Task header lines in `test_import_service_stage_a.py`, `test_chesscom_to_lichess.py` banner tags, and the "Plan 01 SUMMARY" pointers in `test_no_conversion_elo_string.py`.

## Deviations from Plan

None - plan executed as written. The scope listed 8 tagged test names; the scan found 4 (the other shapes the plan's estimate counted did not exist in these files), and a name-shape grep (`_dNN`, `phaseNNN`, `seedNNN`, `_wrNN`, `quick`, `pitfall`, `planNN`) over the scope confirms none remain.

## Environmental notes

- Fresh worktree: `uv sync --group maia-inference` was run before ty; baseline `ruff check tests`, `ruff format --check tests` and `ty check app/ tests/ scripts/` were all clean before the edits and are clean after.
- Per the parallel-executor rules, pytest ran serially (no `-n`) against the shared dev Postgres, and the source-scan helper's frontend half was not needed (no frontend file changed). No pre-existing order-dependent failures reproduced.

## Known leftovers (intentional, strings in test code)

- Assert-message and fixture strings that still carry tags: `tests/test_openings_time_series.py` (lines ~54, 61, 69), `tests/test_remote_eval_worker.py` (assert messages naming D-03/D-04a/SEED-071), `tests/test_worker_heartbeats.py` (~202, 293), `tests/test_zobrist.py` (~298), `tests/test_push_send.py` (`"SEED-138-...-probe/1.0"` user-agent fixtures), `tests/services/test_import_service.py:214` (assert message "Phase 91 / SEED-023 requires ..."). Changing them would change a string in test code (D-14/D-15 prohibition); candidates for a later string-cleanup decision.

## Task Commits

1. **Task 1: the tests/services files** - `7119701cd` (`chore(comments): tests/services (import, normalization, train, store)`)
2. **Task 2: tests/test_[n-z]*.py and the plan gates** - `e20683570` (`chore(comments): tests (n-z)`)

## Threat Flags

None. Comment-only edits plus four test renames; no new endpoints, auth paths or schema changes.

## Self-Check: PASSED

- Both commits are ancestors of HEAD (`7119701cd`, `e20683570`).
- `scan --gate` and `diff` over scopes/241-23.txt exit 0; ruff check, ruff format --check and ty are clean; collection counts equal before and after.
