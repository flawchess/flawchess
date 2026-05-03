---
type: quick-task
slug: speed-up-scripts-backfill-eval-py-with-p
date: 2026-05-03
---

# Speed up scripts/backfill_eval.py

## Goal

Cut wall time of `scripts/backfill_eval.py` against the prod DB (run from local 16-CPU box via SSH tunnel) from sequential ~14 evals/sec to a parallel pool target of ~100+ evals/sec. The single Stockfish process and per-row UPDATE round-trip are the two bottlenecks.

## Constraints (carried over from chat)

- Prod server is small (4 vCPU / 8 GB RAM) and runs the existing `start_engine()` singleton via the import path. **Do not change the singleton's behavior.** Add a parallel `EnginePool` alongside it; only the backfill script imports the pool.
- Pool size is a CLI flag (`--workers N`, default `1`) so the script stays safe on smaller hosts. Default 1 = identical behavior to today.
- Same UCI options (`Hash=64`, `Threads=1`, `depth=15`, `timeout=2.0s`) apply per worker — `Threads=1` per engine because we want N×1 not 1×N for independent positions.

## Changes

### 1. `app/services/engine.py` (additive)

Add a new `EnginePool` class. Keeps the module's existing singleton (`start_engine`/`stop_engine`/`evaluate`) untouched.

```python
class EnginePool:
    """N independent UCI processes, dispatched via an asyncio.Queue.

    Each worker is its own subprocess with its own protocol. evaluate()
    grabs an idle worker, runs analyse(), releases. On timeout / crash,
    that worker is restarted in place; the others keep going.

    Use only for batch jobs that benefit from parallelism (backfill).
    Live FastAPI traffic uses the module-level singleton.
    """

    def __init__(self, size: int) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def evaluate(self, board: chess.Board) -> tuple[int | None, int | None]: ...
```

Reuses the same `_STOCKFISH_PATH`, `_HASH_MB`, `_THREADS`, `_DEPTH`, `_TIMEOUT_S`, score-clamping logic. No new UCI option surface (D-03 grep gate intact).

### 2. `scripts/backfill_eval.py`

- Add `--workers N` CLI flag, default `1`.
- Replace `start_engine()` / `stop_engine()` / `evaluate()` with `EnginePool(args.workers)`.
- Refactor `_evaluate_and_write_rows`:
  - Group rows by `game_id` (rows are already ordered by `game_id, ply`); parse each PGN **once** and replay the mainline collecting boards at all needed plies in a single walk.
  - Process in chunks of `EVAL_BATCH_SIZE`; within a chunk, `asyncio.gather` over `pool.evaluate(board)` calls — concurrency is naturally capped at `workers` by the pool's internal queue.
  - Replace per-row `UPDATE … WHERE id = :id` with one batched `UPDATE … FROM (VALUES …)` per chunk. Cuts SSH-tunnel round-trips by ~`EVAL_BATCH_SIZE`×.
  - Commit cadence stays at `EVAL_BATCH_SIZE` (one commit per chunk → identical resume semantics as D-09).

### 3. Tests

The existing tests for `engine.py` and `backfill_eval.py` cover the singleton path. Add minimal test for `EnginePool` lifecycle (start/stop without crashes, evaluates a position) using a mocked `popen_uci` if engine tests already mock it; otherwise gate behind the existing local-stockfish skip.

## Out of scope

- Tuning `_DEPTH` or `_TIMEOUT_S` (changes data semantics — needs phase scope)
- Per-game caching across different games (no benefit; PGNs are unique)
- Multi-process Python pool (asyncio + N subprocesses gets the same parallelism, simpler)
- Phase backfill SQL changes (already chunked, not the bottleneck)

## Risk

- Singleton path is unchanged — prod imports cannot regress.
- Default `--workers=1` keeps backfill behavior byte-identical for callers who don't opt in.
- Batched `UPDATE … FROM VALUES` is standard PostgreSQL; same idempotency guard (`WHERE eval_cp IS NULL AND eval_mate IS NULL`) is preserved by ordering: only rows newly evaluated this run are written.
