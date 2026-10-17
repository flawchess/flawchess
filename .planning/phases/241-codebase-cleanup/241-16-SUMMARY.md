---
phase: 241-codebase-cleanup
plan: 16
subsystem: backend-services
tags: [cleanup, comments, library, train, scheduler, reminders, leaderboard, medals]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger"
  - phase: 241-03
    provides: "cleanup.py codemod / decision"
provides:
  - "library_service.py and the six Train services free of planning tags, with ledgers/241-16.txt covering all 15 INVENTORY rows"
affects: [241-56, 241-66, 241-67]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 41ee842f0c77227853d89b94d8df68b15228ce42
plan_head_after: 1ba20b8ec10f428e536a1fcb6b6b3eba87d58866

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-16.txt
  modified:
    - app/services/library_service.py
    - app/services/train_pool.py
    - app/services/train_scheduler.py
    - app/services/train_reminder_service.py
    - app/services/train_leaderboard.py
    - app/services/train_medals.py
    - app/services/train_score.py

key-decisions:
  - "SEED-130 is the only seed pointer in scope that is still open (.planning/seeds/, not closed/); it is kept as `(see SEED-130)` in train_pool.dead_band_admissible, next to the rationale it supports. SEED-120, 137, 141, 121, 154, 135, 138 are all closed or no longer relevant and were dropped."
  - "INV-L837 narrowed: flaw-stats does not read game_flaws (it reads games-table oracle columns), so the rewritten library_service docstring names only GET /library/games."
  - "Streak buffer is called 'freezes' in prose (STYLE-GUIDE 3.3 row 13) while `shield_level` and `SHIELD_CAP` stay as the identifiers the comments reference."

patterns-established: []

duration: 60min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 16: library_service and the Train services Summary

**Planning tags are gone from library_service.py and six Train services (186 codemod-rewritten comment lines, about 190 hand edits), all 15 inventory rows are APPLIED, and the non-comment diff against PHASE_BASE is empty.**

## Accomplishments

- Task 1 (library_service.py, train_pool.py, 8 rows): the codemod rewrote 115 lines; `apply`-style exact-string edits covered the remaining 118 flagged lines plus the codemod's short-first-line leftovers. `_build_card` and `get_library_games` docstrings no longer claim "three"/"two" batch queries (six page-batched fetches actually run). The train_pool module, `pool_entry_stmt` and `blob_pending_stmt` docstrings name `_prior_position_lateral` instead of the retired `PriorPosition` self-join. `expected_score_sql`'s docstring points at `expected_score_for`. `SHARP_GAP_ES` points at `best_move_candidates.classify_best_move`.
- Task 2 (five Train services, 7 rows): the codemod rewrote 71 lines; the 55 flagged lines were hand edited. The scheduler module docstring now carries a single "Streak model" paragraph (SHIELD_CAP, both park doors, LEECH_FAIL_THRESHOLD all confirmed in code) in place of the Phase 189/191/193 and SEED-154 narration. The reminder module docstring describes the current tick and its load-bearing step order; the medals start-week comment keeps "read at call time so tests can monkeypatch it".

## Ledger (ledgers/241-16.txt)

15 rows, all APPLIED: INV-L776, L777, L778, L779, L780, L803, L813, L837 (task 1); INV-L761, L814, L824, L825, L828, L838, L839 (task 2). No SKIPPED, MOVED, LEFT or DEFERRED rows, and no `#` secondary-clause lines for rows owned by other plans.

## Task Commits

1. **Task 1: library_service.py and train_pool.py** - `0e2d4f255` (`chore(comments): app/services (library_service, train_pool)`)
2. **Task 2: train scheduler, reminders, leaderboard, medals, score** - `1ba20b8ec` (`chore(comments): app/services (train scheduler, reminders, leaderboard, medals)`)

## Deviations from Plan

### Non-inventoried fixes (all comment/docstring only)

- **[Rule 1 - stale comment] train_reminder_service.py** module docstring: step 3 said the real guard is "the claim in step 5", but the numbered list puts the claim at step 6; corrected.
- **[Rule 1 - stale comment] train_scheduler.py** `DEFAULT_PUZZLES_PER_SESSION`: the comment described a "3/6/9/12/15 preset ladder (was 6/12/18/24)"; the frontend settings UI replaced the presets with a 3-30 slider, so the comment now only states why 6 is the default. `session_window` no longer cites "the Tue/Fri example in 189-CONTEXT.md"; it says "a sparse mask (e.g. Tue/Fri)". `_judge_one_day`, `credit_only` and `is_scheduled_day` comments said "a later plan" for callers that now exist in train_repository.
- **train_pool.py**: removed planning-only labels the scanner does not tag (`P-03`, `P-04`, `P-05` and "CONTEXT.md Claude's Discretion"), pointers to `189-06-PLAN.md`, `192-03-SUMMARY.md`, `189-RESEARCH.md`, "plan 01/03/04", "Task 2/3 checkpoint round" and the "record_solve used to hold the collapse inline" narration. `VettedMove` docstring now says "Quality best marks the deep BEST move itself".
- **train_leaderboard.py**: the 2026-10-04 incident narration ("prod 2026-10-04, top 5 rows all 100% on 1 puzzle") became the rule "Don't rank tentative entries among qualified ones".
- **train_reminder_service.py**: "Deviation from the plan's literal ..." explanation was reduced to the one-sentence reason from INV-L825; `204-DECISIONS.md` pointer replaced by "a wider variant is deliberately deferred".
- **Codemod collapse bug** did not occur: the `^\s*(#|//|\*)\s*[:;,]\s` grep over the scope only matches the pre-existing Sphinx `#:` attribute comments in train_reminder_service.py and train_scheduler.py (hand-edited where they carried tags) and one `*, name: str` parameter line in train_pool.py.
- The codemod left several first lines lower-case or short (e.g. "# the per-scheduled-day tick + depletable", "# The herring_pool generation-time loose"); those were re-capitalised and re-wrapped by hand.

None of the prohibitions were touched: notification copy, leaderboard and medal strings are unchanged; `p_total`/`o_total`, `nf_points`/`nf_puzzles` and `MIN_TACTIC_CHIP_CONFIDENCE`/`_TACTIC_CHIP_CONFIDENCE_MIN` keep their current names in comments; no test file changed.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-16.txt` | exit 0 (7 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-16.txt` | exit 0 (7 selected, 7 changed, no residue) |
| `cleanup.py ledger --scope ... --ledger ledgers/241-16.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed |
| `source_scan_tests.sh` python half, run SERIALLY without `-n 4` (shared dev Postgres, sibling executors) | 95 passed + 5 passed |
| `source_scan_tests.sh --fe` | 131 passed (9 files); no frontend file changed |
| `pytest tests/services/test_train_scheduler.py test_train_leaderboard.py test_train_pool.py` | 298 passed |

The serial python run is an environmental choice per the parallel-executor instructions, not a plan failure.

## Known Stubs

None.

## Threat Flags

None. No code, request, Sentry message/tag/context-key or log text changed (T-241-30 mitigated by the empty token diff and the passing train score and leaderboard parity tests).

## Self-Check: PASSED

- ledgers/241-16.txt found; both task commits (`0e2d4f255`, `1ba20b8ec`) are ancestors of HEAD; `git rev-list --count PLAN_HEAD_BEFORE..HEAD` was 2 before this SUMMARY commit; no file deletions in either commit.
