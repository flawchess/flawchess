---
slug: entry-submit-n-plus-1
status: fixed_awaiting_deploy
trigger: |
  Sentry FLAWCHESS-6G (issue 128345511): N+1 Query at POST /api/eval/remote/entry-submit.
  Per-game SELECT game_positions.* WHERE game_id AND user_id ORDER BY ply, 54 occurrences,
  source eval_drain, http 200 (perf-only, not an error). User flagged "thought it was fixed."
created: 2026-06-16
updated: 2026-06-16
---

# Debug Session: entry-submit-n-plus-1

## Symptoms

- Sentry performance issue (not an exception), HTTP 200, `source: eval_drain`, 54 occurrences,
  first/last seen 2026-06-16 15:45–17:30 UTC. Transaction `/api/eval/remote/entry-submit` ~1303ms.
- Offending span: full-entity `SELECT game_positions.* FROM game_positions WHERE game_id = $1
  AND user_id = $2 ORDER BY ply`, fired once per game.

## Root Cause (CONFIRMED)

`_classify_and_insert_flaws` (`app/services/eval_drain.py`) looped over the batch's games and ran a
**separate** `select(GamePosition).where(game_id == game.id, user_id == game.user_id).order_by(ply)`
per game — a classic N+1 (1 query per game × `_DRAIN_BATCH_SIZE` = 10). The helper is shared by two
callers: `entry_submit_eval` (the endpoint Sentry flagged) and `run_eval_drain` (the cold-lane
drain), so both paths had the N+1.

## Fix (APPLIED)

Batched the position load into a single query before the classify loop:
`select(GamePosition).where(GamePosition.game_id.in_([...])).order_by(game_id, ply)`, grouped into
`positions_by_game: dict[int, list[GamePosition]]` (defaultdict, already imported). The classify loop
now reads its group from the dict. N queries → 1.

- **Correctness:** the composite FK `(game_id, user_id) -> games(id, user_id)` on `game_positions`
  (model comment lines 56-60) guarantees a position's `user_id` equals its owning game's user, so
  filtering on `game_id IN (...)` is exactly equivalent to the old per-game `user_id == game.user_id`
  guard (T-108-05). `ORDER BY game_id, ply` preserves ply-ASC within each game, as
  `classify_game_flaws` requires.
- **Behavior delta (acceptable):** previously a position-load failure for one game was caught in the
  per-game `except` and skipped; now a failure of the single batch query aborts the batch. That query
  failing is a systemic/connection error, not per-game bad data, so aborting is reasonable. The
  per-game `try/except` still wraps `classify_game_flaws` + `bulk_insert_game_flaws` (T-108-04: one
  bad game can't abort the batch).

files_changed:
  - app/services/eval_drain.py (_classify_and_insert_flaws: per-game position SELECT → one batched IN query)

## Verification

- `ruff check` / `ruff format --check` / `ty check` on eval_drain.py: all pass.
- `pytest tests/services/test_eval_drain.py tests/test_flaws_materialization.py
  tests/test_eval_worker_endpoints.py tests/test_remote_eval_worker.py tests/test_backfill_flaws.py`:
  95 passed.
- Production confirmation pending next deploy (perf-only; verify FLAWCHESS-6G stops recurring in Sentry).

## Note on "thought it was fixed"

This is a distinct N+1 from any earlier one — it lives in the flaw-classification position load,
not the eval-target derivation. No prior fix touched this loop.
