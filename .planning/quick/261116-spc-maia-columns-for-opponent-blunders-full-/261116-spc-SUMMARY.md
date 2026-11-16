---
phase: quick-261116-spc
plan: 01
subsystem: maia-flaw-scoring
tags: [maia, facepalm, backfill, opponent-blunders, SEED-261114-iuv]
requires: []
provides:
  - full-mode hook scores opponent blunders (maia_reply_spread, maia_best_prob, maia_pre_spread)
  - "scripts/backfill_maia_flaws.py --mode opponent (row-selected, no stamp)"
  - "--status --mode opponent"
affects:
  - app/services/maia_flaw_scoring.py
  - scripts/backfill_maia_flaws.py
key-files:
  created: []
  modified:
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - app/models/game_flaw.py
    - docs/dev-tooling.md
    - tests/services/maia_fakes.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/scripts/test_backfill_maia_flaws.py
decisions:
  - "Opponent rows never get line facts, so facepalm_expr stays NULL there and the readers need no side gate."
  - "Opponent mode has no stamp column: the row predicate (opponent blunder, played prob set, reply spread NULL) is the checkpoint; the write gate selects a constant NULL stamp."
metrics:
  duration: ~1h
  completed: 2026-11-16
status: complete
commits: 3
plan_head_before: 887b8b3af0284129234a66fc031fe1c0a1294c86
plan_head_after: f58d8e90fd00cad585fcbec926863b47457548c8
actuals:
  tokens: 21000
  tasks: 3
  commits: 3
---

# Quick 261116-spc: Maia columns for opponent blunders Summary

Full-mode scoring now writes the three Maia columns (reply spread, best-move probability, pre spread) on opponent blunders at the opponent's pinned Elo, and a new stamp-free `--mode opponent` backfill fills them on existing rows, with line facts staying NULL on opponent rows.

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 | ffb44b806 | Full-mode hook scores opponent blunders (three Maia columns, no line facts); `assert_maia_lane_state` and existing tests updated |
| 2 | 32e7489ec | Scorer `opponent` mode, `OPPONENT_ROW_COLUMNS`, no-stamp write, `--mode opponent` script run, selector, report counters |
| 3 | f58d8e90f | `--status --mode opponent`, script docstring/usage, docs/dev-tooling.md, game_flaw.py comment |

## What changed

- `maia_flaw_scoring.py`: `_is_opponent_blunder`, `_opponent_maia_values` (shared by full and opponent modes; one post-blunder inference, pre inputs from the existing policy), early-return branch in `_derive_flaw_values`, `_scope_flaws`, `_is_opponent_target`, `_opponent_values`, `_opponent_row`, `OPPONENT_ROW_COLUMNS`, `"opponent": sa.null()` stamp slot. `GameMaiaScore` gained `opponent_blunders / opponent_spreads_scored / opponent_pre_scored`; the user counters now count user-blunder rows only so the report's user numbers do not change.
- `backfill_maia_flaws.py`: `_OPPONENT_IS_MOVER_SQL` compiled from `is_opponent_expr` with the asyncpg dialect (single `%`), `_OPPONENT_PENDING_CLAUSE` shared by selector and status, four new report counters, `_fetch_opponent_status`.
- No migration, reader, repository, router or frontend change (`git diff 887b8b3af -- app/repositories/ app/services/facepalm_score.py app/routers/ alembic/ frontend/` is empty). Phase 256 merge surface untouched: scorer lines 81-92 (`blunder_check_rules` / `line_material` imports) and `_row_score` unchanged; the only edit near the imports is `FACEPALM_PRE_COLUMNS` added to the 71-79 list.

## Dev smoke (dry run, dev DB, nothing written)

`--db dev --mode opponent --workers 1 --limit 20 --dry-run --report-dir temp/maia-opp-smoke` exited 0:

```
shard 0/1: 20 games selected (mode=opponent, dry_run=True, cutoff=None)
total: games_selected=20 games_scored=20 games_stamped=0 ... opponent_spreads_scored=66 opponent_spreads_null=0 opponent_pre_scored=66 opponent_pre_null=0 reason_best_move_missing=65
```

`--db dev --status --mode opponent`:

```
opponent_pending_games=8543 opponent_blunders_total=24839 opponent_blunders_with_played_prob=21160 opponent_blunders_with_spread=0 opponent_blunders_with_pre_spread=0 opponent_blunders_with_best_prob=0 opponent_blunders_pending=21160
```

The report is in gitignored `temp/maia-opp-smoke/`.

## Operator commands for a later benchmark / prod run (not run here)

Deploy the full-mode hook first (otherwise an old-hook full re-score NULLs the values again), then:

```
uv run python scripts/backfill_maia_flaws.py --db prod --status --mode opponent
PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode opponent --workers 8 --throttle-ms 50
uv run python scripts/backfill_maia_flaws.py --db prod --status --mode opponent
```

Same with `--db benchmark` (after `bin/benchmark_db.sh start`). Re-running resumes: a finished scope selects 0 games apart from the residue.

## Residue

Rows Maia cannot score keep a NULL reply spread and are selected again by every later run: stalemating blunders (`no_legal_reply`) and rows whose board cannot be rebuilt (`fen_mismatch`, `ply_beyond_mainline`, ...). One run never loops because each shard selects one snapshot and iterates it once. `--status --mode opponent` shows the residue as `opponent_blunders_pending`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test update] Two more existing tests encoded "opponent blunders spend one call"**
- **Found during:** Task 1 verification
- **Issue:** `test_replay_castling_and_ep_fen` (`len(seen) == 1`, ply 4 is the black user's opponent blunder, now 2 calls) and `test_mover_elo_pinned_from_board_turn` (spy keyed Elo by side to move; the opponent's post-blunder call overwrote the white entry) failed under the new rule. Neither was in the plan's list.
- **Fix:** First test now expects 2 calls; second looks up the Elo of each flaw's pre-blunder FEN instead of keying by side to move. Same intent, new rule.
- **Files modified:** tests/services/test_maia_flaw_scoring.py
- **Commit:** ffb44b806

**2. [Process] Tests written after the implementation, not strictly red-first**
- The new opponent tests were written after the code and passed on first run; the updated existing tests were the red-to-green proof for the changed behaviour. No mutation check of the new tests was run.

Otherwise the plan was executed as written. Nothing skipped.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or schema; the opponent pass writes the same table through the unchanged advisory-lock plus fingerprint write gate.

## Self-Check: PASSED

- Commits ffb44b806, 32e7489ec, f58d8e90f exist on `quick/maia-opponent-blunders`.
- ruff check/format, ty (zero errors), depth gate (1562 functions, no breaches) clean; 370 + 8 + 209 tests passed in the final run.
