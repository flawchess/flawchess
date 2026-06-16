---
phase: quick-260616-kzb
plan: "01"
type: execute
status: complete
subsystem: eval_drain
tags: [performance, n-plus-one, batch-write, seed-052]
dependency_graph:
  requires: [batched-eval-write]  # 260616-jq1 precedent
  provides: [batched-entry-ply-eval-write]
  affects: [app/services/eval_drain.py, tests/services/test_eval_drain.py]
tech_stack:
  added: []
  patterns: [UPDATE ... FROM (VALUES ...) batched write spanning multiple game_ids, CAST() for asyncpg named-param compat]
key_files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_eval_drain.py
    - .planning/seeds/SEED-052-batch-entry-ply-eval-write.md
decisions:
  - "Sibling helper (_batch_update_entry_eval_rows), not reuse of _batch_update_eval_rows — the entry-ply lane spans MULTIPLE games per drain batch (game_id in the VALUES tuple), writes only eval_cp/eval_mate (no best_move), and carries the optional endgame_class predicate"
  - "endgame_class disambiguation preserved via (v.endgame_class IS NULL OR game_positions.endgame_class = v.endgame_class) — exactly the pre-batch per-row semantics (predicate added only when target.endgame_class was not None)"
  - "CAST(:p AS integer|smallint) not ::type — asyncpg rewrites :param to $N before the server parses, so :: adjacent to $N is a syntax error (same as 260616-jq1)"
  - "No CHANGELOG entry — pure internal N+1/consistency cleanup, no user-facing behavior change (CLAUDE.md exempts quick tasks that don't change behavior)"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-16"
  tasks_completed: 3
  files_changed: 3
---

# Quick Task 260616-kzb: Batch entry-ply eval write (SEED-052)

Closed the last per-row eval `UPDATE` loop in the cold-drain / entry-ply lane.
`_apply_eval_results` (`app/services/eval_drain.py`) now issues a single batched
`UPDATE … FROM (VALUES …)` round-trip per drain batch instead of one
`update(GamePosition)` per row, mirroring the full-ply lane's 260616-jq1 /
FLAWCHESS-6B fix.

## Tasks Completed

| Task | Name | Commit |
|------|------|--------|
| 1 | `_batch_update_entry_eval_rows` helper + rewrite `_apply_eval_results` | aea8c0e9 |
| 2 | Multi-game / multi-class batched-write regression test | 3d11dbb0 |
| 3 | Touched-area gates (ruff format/check, ty, full backend suite) | (in-line) |

## What Was Built

**Task 1** — New module-level helper `_batch_update_entry_eval_rows(session, rows)`
taking `rows: list[(game_id, ply, eval_cp, eval_mate, endgame_class)]`. It emits one
`UPDATE game_positions SET eval_cp = v.eval_cp, eval_mate = v.eval_mate FROM (VALUES …)
AS v(game_id, ply, eval_cp, eval_mate, endgame_class) WHERE game_positions.game_id =
v.game_id AND game_positions.ply = v.ply AND (v.endgame_class IS NULL OR
game_positions.endgame_class = v.endgame_class)`.

`_apply_eval_results` was rewritten to do one Python pass: count
`eval_calls_made`/`eval_calls_failed`, fire the existing `(None, None)` per-row Sentry
warning (`source="eval_drain"`, bounded ctx — game_id/ply[/endgame_class], no
PGN/FEN/user_id), and collect surviving write-rows; then a single helper call. The
`(eval_calls_made, eval_calls_failed)` return is unchanged.

**Key structural difference from 260616-jq1:** the full-ply helpers are per-game
(single `:game_id` param). The entry-ply lane's targets are collected across many games
in a drain batch (`_collect_eval_targets_from_db` over a `game_ids` list), so `game_id`
had to move into the VALUES tuple and the WHERE matches on `v.game_id`. That, plus the
endgame_class predicate and eval-only write set, is why a sibling helper rather than
reuse of `_batch_update_eval_rows`.

**Task 2** — `TestBatchedEntryEvalWrite.test_batched_write_multi_game_multi_class`:
two games, a `middlegame_entry` (endgame_class=None) row, an `endgame_span_entry`
(endgame_class=3) row, a `(None, None)` failure row, and a deliberate class-mismatch
row (target class=2 vs stored class=5) that must NOT be overwritten. Asserts eval_cp/mate
landed on the right `(game_id, ply)`, the failure row stayed NULL, the mismatch row was
untouched, and counts are `(made=4, failed=1)`.

## Correctness Preserved

- `(None, None)` skip → row stays NULL + per-row Sentry warning (message, `source`/
  `eval_kind` tags, bounded ctx) unchanged.
- Optional `endgame_class` WHERE disambiguation preserved (and now regression-guarded).
- `(eval_calls_made, eval_calls_failed)` return semantics unchanged.
- Empty input → no zero-row VALUES UPDATE (guarded).
- No `asyncio.gather`; sequential `await session.execute` on the caller-owned session.

## Verification

- New regression test passes; eval-drain + full-eval-drain + eval-worker-endpoints
  suites: 88 passed.
- Full backend suite: **2710 passed, 10 skipped** (`uv run pytest -n auto`).
- `ruff format`, `ruff check`, `ty check app/ tests/` all clean.
- Frontend untouched (backend-only change) — frontend gates not run.

## Deviations from Plan

None.

## Self-Check: PASSED

- app/services/eval_drain.py: modified (commit aea8c0e9)
- tests/services/test_eval_drain.py: modified (commit 3d11dbb0)
- SEED-052 marked `status: implemented`
