---
phase: 241-codebase-cleanup
plan: 66
subsystem: backend-naming
tags: [rename, naming, cross-layer, d-16-sweep]
requires: ["241-02", "241-55", "241-56"]
provides:
  - "import_scope_expanded public helper"
  - "users_with_no_pending_evals_or_imports gate"
  - "SolveTotals.non_filler_points / non_filler_puzzles"
affects: [app/repositories, app/routers/users.py, app/services, tests]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-66.tsv
    - .planning/phases/241-codebase-cleanup/allow/241-66.tsv
  modified:
    - app/repositories/user_import_settings_repository.py
    - app/routers/users.py
    - app/services/import_service.py
    - app/models/game.py
    - app/repositories/game_repository.py
    - app/services/eval_drain.py
    - app/repositories/train_leaderboard_repository.py
    - app/services/train_leaderboard.py
    - tests/test_import_service.py
    - tests/services/test_import_service.py
    - tests/repositories/test_game_repository_zero_pending.py
    - tests/repositories/test_train_leaderboard_repository.py
    - tests/services/test_train_leaderboard.py
key-decisions:
  - "Test file test_game_repository_zero_pending.py keeps its name so pytest node ids stay stable"
  - "Tagged test constants are reported, not renamed (D-14/D-16 scope)"
requirements-completed: [D-06, D-07, D-16, D-17]
status: complete
commits: 3
plan_head_before: 9e9a9b676a174dcccffa3d7c8de39741ef181b6f
plan_head_after: be92c587967e39dc48dda8e018a51191b2bba828
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
duration: 25 min
completed: 2026-10-16
---

# Phase 241 Plan 66: Cross-layer renames X1, X3, X5 and D-16 backend sweep Summary

Three cross-layer backend renames (X1, X3, X5) shipped as one `refactor(naming)` commit each with no behavior change, and the D-16 backend sweep over `app/` found nothing.

## Renames

| ID | Old to new | Commit | Files touched |
|----|------------|--------|---------------|
| X1 | `_import_scope_expanded` to `import_scope_expanded` | 132f5d8cf | user_import_settings_repository.py (def + `__all__`), routers/users.py, services/import_service.py, tests/test_import_service.py (2 comments) |
| X3 | `users_with_zero_pending` to `users_with_no_pending_evals_or_imports` (+ test fn `test_users_with_no_pending_evals_or_imports_issues_single_query`) | 77ad9322a | repositories/game_repository.py, services/eval_drain.py, services/import_service.py, models/game.py, tests/repositories/test_game_repository_zero_pending.py, tests/services/test_import_service.py (4 monkeypatch strings), tests/test_import_service.py |
| X5 | `nf_points`/`nf_puzzles` to `non_filler_points`/`non_filler_puzzles` | be92c5879 | repositories/train_leaderboard_repository.py, services/train_leaderboard.py, tests/repositories/test_train_leaderboard_repository.py, tests/services/test_train_leaderboard.py |

SolveTotals is not referenced by any schema or router (confirmed by grep), so no wire name changed. The X3 definition docstring already stated the active-import exclusion, so no docstring clause was added.

## D-16 backend sweep

`cleanup.py scan --identifiers app/` after the renames: 177 files, 0 matches. No finds, so no D-16 renames and no cross-layer candidates to list (the expected `_phase80_item_from_metrics` was already renamed by 241-55).

## Tagged test constants (owner decides)

`cleanup.py scan --identifiers tests/` reports (not renamed):
- `_PHASE_169_SHAPED_PGN` (tests/test_bot_pgn_clk_roundtrip.py:27,47)
- `_SEED076_PGN` (tests/test_eval_worker_endpoints.py:5037, 5154, 5169, 5184, 5221, 5275, 5323, 5361, 5456)
- `PHASE_116_REVISION` (tests/test_migration_116_full_evals.py:37,301)

## Deviations from Plan

None - plan executed exactly as written, with two mechanical notes:
- `uv sync --group maia-inference` was run in the fresh worktree (environment prep, baseline gates passed before edits).
- ruff format added magic trailing commas in two places after the X5 rename lengthened lines (train_leaderboard_repository.py:137, tests/services/test_train_leaderboard.py:466); recorded as two `diff` rows in allow/241-66.tsv.

## Verification

- ruff check, ruff format, `ty check app/ tests/ scripts/`: clean after each commit.
- Tests: X1 130 passed; X3 157 passed, 4 skipped; X5 242 passed.
- `absent` (4 rows, 0 hits) and `diff` (only allowed residue) pass. `git grep -c '"users_with_no_pending_evals_or_imports"' tests/services/test_import_service.py` prints 4.

## Self-Check: PASSED

All three commits exist on this branch; rename-maps/241-66.tsv and allow/241-66.tsv exist.
