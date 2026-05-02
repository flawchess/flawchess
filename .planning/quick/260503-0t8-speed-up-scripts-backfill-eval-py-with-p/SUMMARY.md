---
type: quick-task-summary
slug: speed-up-scripts-backfill-eval-py-with-p
date: 2026-05-03
status: complete
---

# Speed up scripts/backfill_eval.py — Summary

## What changed

### `app/services/engine.py`
- Extracted `_score_to_cp_mate(info)` helper from the singleton's `evaluate()`. Both code paths now share the score-extraction + clamping logic byte-for-byte (no risk of future drift).
- Added `EnginePool` class. Spawns N independent UCI subprocesses, dispatches via `asyncio.Queue`, restarts a worker in place on per-process timeout/crash without affecting siblings. Reuses the same UCI option surface (`Hash=64`, `Threads=1`, `depth=15`, `timeout=2.0s`) — no new option grep gates.
- Singleton API (`start_engine`, `stop_engine`, `evaluate`) is unchanged. The prod import path uses it as before.

### `scripts/backfill_eval.py`
- Replaced the singleton-based eval loop with `EnginePool` + parallel chunked dispatch.
- New CLI flag `--workers N` (default `1`). At default 1, behavior is byte-identical to the legacy serial path.
- `_evaluate_and_write_rows` now:
  1. Calls `_resolve_boards_grouped(rows)` which uses `itertools.groupby` to parse each game's PGN once and resolves all of that game's plies in a single mainline walk.
  2. Processes the resolved boards in chunks of `EVAL_BATCH_SIZE` (raised to 500). `asyncio.gather` fans out `pool.evaluate(board)` calls; the pool's queue caps in-flight at `workers`.
  3. Flushes each chunk as a single batched `UPDATE … FROM (VALUES …)` round-trip instead of one UPDATE per row. Cuts SSH-tunnel round-trips by ~500×.
- Commit cadence preserved (D-09): one commit per chunk → resume semantics unchanged.

### `tests/scripts/test_backfill_eval.py`
- All five test classes now patch `scripts.backfill_eval.EnginePool` (the imported class) and configure `mock_pool.evaluate` instead of the removed module-level `evaluate` / `start_engine` / `stop_engine` names. Test invariants are preserved.

## Validation

- `uv run ruff check .` — clean
- `uv run ruff format .` — clean
- `uv run ty check app/services/engine.py scripts/backfill_eval.py tests/scripts/test_backfill_eval.py tests/services/test_engine.py` — clean
- `uv run pytest tests/services/test_engine.py tests/scripts/test_backfill_eval.py` — 7 passed, 6 skipped (Stockfish-dependent tests skip in CI by design)
- Live smoke test of `EnginePool` against `$HOME/.local/stockfish/sf`: 8 evals on 4 workers in 0.32s vs 1 worker in 0.76s (2.4× speedup on cheap initial-position evals; full-depth backfill positions will scale closer to N×).
- CLI smoke: `--dry-run --workers 4` works; `--workers 0` correctly rejected.

## Performance expectations

For the prod-DB backfill from a 16 vCPU local box via SSH tunnel:

- **Eval phase**: ~10× from parallel workers (10 engines × ~70ms/eval at depth 15 → ~140 evals/sec vs 14 evals/sec).
- **DB write phase**: ~500× round-trip reduction from batched UPDATE — particularly relevant over the SSH tunnel.
- **PGN reparse**: minor win on top, free, from group-by-game parsing.

Order-of-magnitude estimate for 500k rows: ~10 hours → ~1–1.5 hours.

## Constraints respected

- Singleton path (used by prod live import) untouched. Prod's 4 vCPU / 8 GB budget is not affected.
- `--workers` defaults to 1 (legacy behavior). Operator must opt in for parallelism.
- CLI rejects `--workers 0` and `--workers <0`.
- `EnginePool.__init__` raises `ValueError` for `size < 1`.

## Files changed

- `app/services/engine.py` (+102, -8)
- `scripts/backfill_eval.py` (+106, -39)
- `tests/scripts/test_backfill_eval.py` (test mocks updated)
- `.planning/quick/260503-0t8-speed-up-scripts-backfill-eval-py-with-p/PLAN.md` (new)
- `.planning/quick/260503-0t8-speed-up-scripts-backfill-eval-py-with-p/SUMMARY.md` (new)
