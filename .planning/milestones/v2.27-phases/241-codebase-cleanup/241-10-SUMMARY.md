---
phase: 241-codebase-cleanup
plan: 10
subsystem: repositories
tags: [cleanup, comments, repositories]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "16 repositories in app/repositories free of planning tags and stale references, with ledgers/241-10.txt covering all 37 INVENTORY rows"
affects: [241-52, 241-55, 241-66]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: f5f7c0c96f1ffd4063b384cadb03a76849a8344c
plan_head_after: 3ac8b77f5586aa2a3163014196852b45c2295267

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-10.txt
  modified:
    - app/repositories/benchmark_cohort_cdf_repository.py
    - app/repositories/current_strength_repository.py
    - app/repositories/endgame_ranked_repository.py
    - app/repositories/endgame_repository.py
    - app/repositories/game_repository.py
    - app/repositories/import_job_repository.py
    - app/repositories/llm_log_repository.py
    - app/repositories/openings_repository.py
    - app/repositories/stats_repository.py
    - app/repositories/user_benchmark_percentiles_repository.py
    - app/repositories/user_import_settings_repository.py
    - app/repositories/user_rating_anchors_repository.py
    - app/repositories/user_repository.py
    - app/repositories/worker_heartbeat_repository.py

key-decisions:
  - "INV-L490 is LEFT: deleting the PositionBookmarkRepository alias and `import sys as _sys` is a code change that needs owner approval"
  - "get_latest_log_by_hash (test-only callers) stays; its docstring is corrected and it remains a section 7 dead-code candidate"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 10: Remaining Repositories Comment Cleanup Summary

**Planning tags, stale line references and retired-function tombstones are gone from 14 of the 16 repositories in scope (position_bookmark_repository.py and `__init__.py` were already clean); the token diff against PHASE_BASE is empty, so only comments and docstrings changed.**

## Accomplishments

- `endgame_repository.py`: module docstring lists all five public query functions; stale `_compute_per_tc_metric_cards` / `_aggregate_bucket_counts` / `_compute_clock_pressure*` references now name the real consumers (endgame_ranked_service, endgame_service.extract_entry_clocks / iterate_clock_rows); the `query_cohort_clock_rows` tombstone is deleted; the `KeyError` comment now says what the code does (empty page).
- `game_repository.py`: `_record_backward_game` became `_admit_backward_game`; the column-list comment moved above `POSITION_COPY_COLUMNS`; the backlog-count docstring names its real consumer.
- `stats_repository.py`: the partition invariant uses the real field names (`eval_n_mg` and friends); the `endgame_repository.py:687-692` line reference is gone.
- `openings_repository.py`: return-shape docstring matches the 4-tuple, the PR #89 narrative and the deleted-function sentences are removed.
- Remaining 10 files: Phase/Plan/D-NN pointers rewritten in present tense; `user_benchmark_percentiles_repository.py` and `user_rating_anchors_repository.py` module docstrings describe the current schema instead of the amendment history.

## Ledger (ledgers/241-10.txt)

37 rows: 36 APPLIED, 1 LEFT (INV-L490). Per task: 24 rows in Task 1, 13 in Task 2.

## Codemod vs hand edits

- Codemod: 52 lines in the four Task 1 files, 43 lines in 10 Task 2 files (95 lines total), all reviewed with `git diff -U0`; none reverted. A few needed a follow-up reflow where the removed tag left a short first line.
- Hand edits: 49 flagged lines in Task 1, done as Edit-tool replacements (one per comment block), and 39 flagged lines in Task 2, done as 6 `apply-edits` batches (39 spans) plus 1 Edit-tool reflow; both include the inventory rows.

## Non-inventoried fixes

- `llm_log_repository.py`: removed `SC #4` pointers (success-criterion tags) and the Phase 64 smoke-test/commit pointer in `_compute_cost`.
- `stats_repository.py`: dropped the `2026-04-26:` date prefix left behind by the tag strip, and turned the "pre-PRE-01" history sentence into a rule.
- `user_import_settings_repository.py`: dropped the `UAT 186:` prefix in `reset_backfill_cursors`.
- `worker_heartbeat_repository.py`: dropped `WR-01 code review` / `260725-da3, FLAWCHESS-8B` tags.
- `game_repository.py`: fixed the grammar slip "and surfaced as a column-drift error" to "and surface".

## For the owner

- **INV-L490 (LEFT):** `position_bookmark_repository.py` keeps the `PositionBookmarkRepository` namespace alias, `import sys as _sys` and the "Namespace alias" comment. Removing all three is a dead-code removal; say so if you want it.
- `llm_log_repository.get_latest_log_by_hash` has only test callers (tests/test_llm_log_repository.py): a section 7 dead-code candidate, not removed here.

## Deviations from Plan

**1. [Plan note] INV-L479 `played_at` wording.** The inventory suggests "used for recency windows". I could not confirm a recency-window use of the clock rows' `played_at` (the recency filtering in endgame_ranked_service reads `played_at` on game and endgame/non-endgame rows), so the docstring only says "game start timestamp".

**2. [Plan note] INV-L460.** The inventory calls the dedup CTE "MATERIALIZED". The code uses a plain `.cte("dedup")` referenced twice, which Postgres materializes. The docstring says exactly that.

No Rule 1-4 deviations. No code changes.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-10.txt` | exit 0 (16 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-10.txt` | exit 0 (16 selected, 14 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-10.txt --ledger ledgers/241-10.txt` | exit 0 |
| `ruff check app/repositories`, `ruff format --check app/repositories` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `source_scan_tests.sh --py` equivalent | 95 passed + 5 passed |

Environmental: the python half of `source_scan_tests.sh` was run serially (the same two pytest commands without `-n 4`) because sibling executors share the dev Postgres. The `--fe` half was not run: this plan touches no frontend file and `frontend/node_modules` was not installed in this worktree.

## Known Stubs

None.

## Threat Flags

None. Comments and docstrings only, verified by `cleanup.py diff` (zero residue); no package installs beyond `uv sync --group maia-inference` from the lockfile.

## Self-Check: PASSED

Files verified present: ledgers/241-10.txt, this SUMMARY. Commits verified as ancestors of HEAD: 0a49a411a, 3ac8b77f5.
