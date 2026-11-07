---
phase: 246-train-subnav-split
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, train, archive, pagination]
status: complete

requires:
  - phase: 245-train
    provides: drill_items / drill_solves tables, _count_drill_items_by_status, fen_and_last_move_at_ply
provides:
  - "GET /api/train/archive (list=mastered|parked, limit, offset) returning {items, total}"
  - "TrainArchiveItem / TrainArchiveResponse / ArchiveList schemas"
  - "train_repository.get_archive_page, ArchiveItemRow, ArchivePage, ARCHIVE_LIST_STATUS"
  - "Confirmed by test: hidden and guest viewers carry an integer Points rank (D-11)"
affects: [246-04, 246-05]

actuals:
  tokens: 9000    # 36,129 chars of diff (base..HEAD of the two task commits) / 4
  tasks: 2
  commits: 2
plan_head_before: 0c84cf49c8fb0fd6cfa04cc7fdb30c6f3882fa43
plan_head_after: 1649ec47681ea86620f248c0fb4056855ee2aeff

tech-stack:
  added: []
  patterns:
    - "Sort and page in a subquery first, join games (and read pgn) only for the page's rows"
    - "One function returns rows and total together so one place owns the list-equals-count invariant"

key-files:
  created: []
  modified:
    - app/schemas/train.py
    - app/repositories/train_repository.py
    - app/routers/train.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
    - tests/routers/test_train_leaderboard.py

key-decisions:
  - "No game_flaws join: nothing selected comes from it, so evicted items stay listed (D-14 outcome honoured, wording not followed, as the plan states)"
  - "An unreplayable PGN keeps its row with fen and last_move_uci null instead of being dropped, so list length equals total"
  - "No migration: one grouped drill_solves scan, prod size check (P1/P2) was not run"

patterns-established:
  - "Archive query: LEFT JOIN of a grouped per-(game, ply) max(solved_at) subquery, ORDER BY NULLS LAST then game_id DESC then ply DESC"

requirements-completed: [D-04, D-07, D-08, D-11, D-13, D-14]

coverage:
  - id: D1
    description: "GET /api/train/archive lists mastered or parked puzzles, 20 per page by default, newest solve first"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_archive_lists_a_mastered_puzzle_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_archive_default_list_is_mastered"
        status: pass
  - id: D2
    description: "Sort by latest SR_ITEM solve of this user, NULLS LAST, stable game_id/ply tiebreak"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_archive_orders_by_latest_solve_newest_first"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_archive_tiebreak_is_stable_across_pages"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_archive_ignores_herring_filler_and_other_user_solves"
        status: pass
  - id: D3
    description: "Evicted game_flaws row and corrupt PGN keep the row listed; total equals the toggle count"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_archive_keeps_item_without_game_flaw_row"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_archive_corrupt_pgn_keeps_row_with_null_fen"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_archive_total_matches_progress_counts"
        status: pass
  - id: D4
    description: "Item carries exactly the 14 documented fields, no spoiler"
    requirement: "D-07, D-08"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_archive_lists_a_mastered_puzzle_end_to_end"
        status: pass
  - id: D5
    description: "Hidden and guest viewers have an integer Points rank"
    requirement: "D-11"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_guest_viewer_sees_ghost_row"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_leaderboard.py#test_hidden_viewer_sees_private_row"
        status: pass

duration: ~25min
completed: 2026-11-06
---

# Phase 246 Plan 01: Train Archive API Summary

**`GET /api/train/archive` pages a user's mastered or parked puzzles, newest SR solve first, with game details and no spoiler fields, backed by a single grouped `drill_solves` scan.**

## Accomplishments

- Schemas `ArchiveList`, `TrainArchiveItem` (14 fields, exact set pinned by test) and `TrainArchiveResponse`.
- `get_archive_page` in the repository: a `last_solve` subquery (`max(solved_at)` per game/ply, this user's `SR_ITEM` solves only), an outer-joined `page` subquery that sorts and limits before `games` is joined, then the outer join to `games` for `pgn` and game details. `total` comes from `_count_drill_items_by_status`, the function behind the toggle counts.
- Route `GET /train/archive` with `list` (mastered or parked, default mastered), `limit` (1..50, default 20) and `offset` (0..2^31-1). `list=active` is a 422.
- 7 repository tests, 5 router tests (one parametrized over 5 cases) and the guest rank assertion.

## Task Commits

1. Task 1 (tracer): `f26d3d075` feat(246-01): add GET /train/archive for mastered and parked puzzles
2. Task 2: `1649ec476` test(246-01): pin archive sort, evicted rows, corrupt PGN, ownership and bounds

## Tracer gate

The end-to-end test `test_archive_lists_a_mastered_puzzle_end_to_end` passed through the real ASGI app against the test DB before Task 2 expanded. `HUMAN_VERIFY_MODE`/gate was not `blocking-human` for this tracer and its `<verify>` is automated-only, so no checkpoint was raised.

## Mutation checks (Task 2 acceptance), each reverted before commit

Task 2 is a coverage task over code written in Task 1, so its new tests passed on the first run rather than failing RED first. The three mutations below are the evidence that they bite. After each, `git diff --stat app/` was empty, confirming the restore.

| Mutation (in `get_archive_page` code) | Result |
|---|---|
| Delete `DrillSolve.source == DrillSource.SR_ITEM` | `test_archive_ignores_herring_filler_and_other_user_solves` FAILED (1 failed, 6 passed) |
| Delete `DrillSolve.user_id == user_id` from `last_solve` | same test FAILED (1 failed, 6 passed) |
| Skip rows whose replay returned `None` (`continue`) | `test_archive_corrupt_pgn_keeps_row_with_null_fen` FAILED (1 failed, 6 passed) |

## Verification run

- `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py tests/routers/test_train_leaderboard.py -n auto`: 343 passed.
- `uv run ruff check app/ tests/`, `uv run ty check app/ tests/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: clean (1282 functions scanned, no breaches).
- No EXPLAIN was run: the plan does not gate on one, and dev has 135 `drill_solves` rows, too few to say anything about a prod plan (flagged assumption A4/P1/P2 remains unverified).

## Deviations from Plan

None - plan executed as written. The `game_flaws` join omission is the plan's own documented `decision_wording_deviation`.

## Known Stubs

None.

## Threat Flags

None. The route reads only the caller's rows; the threat register mitigations T-246-01 through T-246-06 are covered by `test_archive_other_user_items_absent`, `test_archive_ignores_herring_filler_and_other_user_solves`, `test_archive_rejects_bad_params` and the exact-key-set assertion. T-246-07 (prod check P5, foreign `drill_items`) was not run and stays with the orchestrator.

## Self-Check: PASSED

- `app/repositories/train_repository.py` contains `async def get_archive_page`; `app/routers/train.py` declares `@router.get("/archive", ...)`; `app/schemas/train.py` contains `class TrainArchiveResponse`.
- Commits `f26d3d075` and `1649ec476` are ancestors of HEAD.
