---
phase: 241-codebase-cleanup
plan: 56
subsystem: backend-services
tags: [naming, rename, flaws_service, import_service, tactic_detector, normalization, library_service]
requires: ["241-02", "241-03", "241-14", "241-15", "241-16", "241-20", "241-23"]
provides:
  - "mover_result, game, _insert_games_and_build_position_rows, pv_start_board, bot_rating, player_total/opp_total names"
affects: [app/services]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-56.tsv
  modified:
    - app/services/flaws_service.py
    - app/services/library_service.py
    - app/services/import_service.py
    - app/services/normalization.py
    - app/services/tactic_detector.py
    - tests/services/test_flaws_service.py
    - tests/services/test_import_service.py
key-decisions:
  - "Renames only: no aliases, no behavior change, no test assertion changes (D-17, D-08)"
requirements-completed: [D-02, D-06, D-07, D-17]
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 31a24da30c6d1ccfd0cb4b32737fa0bda49d71bd
actuals:
  tokens: 3000
  tasks: 3
  commits: 6
duration: 15 min
completed: 2026-10-16
---

# Phase 241 Plan 56: Import/train/tactics renames Summary

Six INVENTORY section 5 renames in the services layer, one `refactor(naming)` commit each, with wire names (`bot_elo`, `user_result` schema fields, `board_after_flaw` locals) untouched.

## Renames

| # | Old -> new | Commit | Files touched |
|---|-----------|--------|---------------|
| a | `user_result` -> `mover_result` (params of `_is_unpunished`, `_build_tags`) | c54e56662 | flaws_service.py (6 occurrences), library_service.py (comment :434), tests/services/test_flaws_service.py (comment :1881, :1886) |
| b | `p_total` / `o_total` -> `player_total` / `opp_total` (`_build_flaw_bullet`) | f0e7a7b24 | library_service.py |
| c | `game_dict` -> `game` (`_run_forward_pass` loop) | 3301c641a | import_service.py (3 occurrences; no outer `game` binding in scope, only the unrelated `Game` model import) |
| d | `_collect_position_rows` -> `_insert_games_and_build_position_rows` | a93e37f30 | import_service.py, normalization.py (comment), tests/services/test_import_service.py (comments); no mock.patch strings |
| e | `board_after_flaw` -> `pv_start_board` (params of `detect_tactic_motif`, `_parse_pv`) | 884174fd0 | tactic_detector.py (module docstring, both signatures, uses, param doc reworded for the missed pass) |
| f | `bot_elo` -> `bot_rating` (params of `normalize_flawchess_game[_or_reason]`) | 31a24da30 | normalization.py (all 7 occurrences); callers are positional |

`rename-maps/241-56.tsv` holds 7 rows (p_total and o_total are two rows), scoped by canon_paths to the edited file(s). Rows use absent_paths `-`, except row (d) which lists its three files.

## Scope proof (occurrence counts unchanged outside the scoped files)

- `git grep -c user_result`: app/repositories/library_repository.py 2, app/schemas/library.py 2, app/schemas/openings.py 1 (untouched; frontend not in this plan's files).
- `git grep -c bot_elo` app/schemas/bots.py: 2 (untouched).
- `git grep -c board_after_flaw`: flaws_service.py 9, library_repository.py 5 (untouched locals).
- Other test-file `user_result` comments (test_flaws_service.py :1371/:1427/:1429) refer to the game-level API concept and were left alone. Test fakes with their own `board_after_flaw` param names in test_flaws_service.py were left alone.

## Verification

- `uv run ty check app/ tests/ scripts/` clean after each rename.
- Pytest per task: flaws/library/flaw_comparison (256 passed serial), import service files (115 passed, 3 skipped), tactic_detector + normalization + store_bot_game_service + bots router/schema (all pass).
- `cleanup.py absent` 0 hits, `cleanup.py diff --plan 241-56` passes for every touched file; `source_scan_tests.sh --py` 5 passed.
- ruff format/check clean on touched files.

## Deviations from Plan

None - plan executed exactly as written. Two notes: INVENTORY line numbers were stale (re-located with `git grep -nw` as the plan directs), and the first `pytest -n 4` run of task 1 hit asyncpg `ConnectionDoesNotExistError` under load from sibling worktrees; rerunning serially passed (environmental, not related to the rename).

## Known Stubs

None.

## Self-Check: PASSED

All six commits are on this branch ahead of base de0c589be; rename-maps/241-56.tsv exists and contains `_insert_games_and_build_position_rows`; `def _insert_games_and_build_position_rows` exists in import_service.py.
