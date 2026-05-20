---
id: SEED-023
status: ready (becomes Phase 91 — replaces the profiling phase originally drafted under SEED-022)
planted: 2026-05-20
planted_during: /gsd-explore session on 2026-05-20 questioning whether SEED-022's profile-then-mitigate path was worth pursuing. First-principles re-read of `app/services/import_service.py` and the 441-line `logs/import-stress-20k-each-2026-05-20.log` identified the import-time Stockfish eval pass *inside the per-batch transaction* as the structural OOM driver, making the SEED-022 profiling phase diagnostic-without-payoff.
trigger_when: Now (active). Plan as Phase 91 once SEED-022 is marked superseded.
scope: medium (single phase, ~5-7 plans: schema migration + hot-lane refactor + cold-lane drain + frontend CPU-icon header bar + per-metric pending-state plumbing + tests)
priority: high (gates concurrent multi-user adoption AND ships a UX improvement — user sees results within seconds instead of waiting for the full eval pass)
references:
  - SEED-022                                                 # the predecessor — diagnostic-led approach, now superseded
  - .planning/notes/2026-05-20-import-pipeline-rethink.md    # the /gsd-explore conversation that produced this seed
  - logs/import-stress-20k-each-2026-05-20.log               # the stress test that motivated both seeds
  - .planning/phases/90-import-pipeline-memory-leak-fix-resilience/   # the per-batch session lifecycle this builds on
---

# SEED-023: Two-lane import — defer Stockfish eval to an in-process cold drain

## Goal

Restructure the import pipeline so the hot path (fetch → parse → insert positions → commit) holds no Stockfish work, and a separate in-process cold-drain coroutine evaluates entry plies in the background. Two concurrent 20k-game imports must complete without OOM-killing Postgres, the user must see opening-explorer / raw endgame WDL / flag-rate / time-per-move stats within seconds of import start, and Stockfish-dependent stats (conversion, recovery, score-gap, time-pressure-vs-performance) must fill in over the following minutes with honest per-metric sample-size labels.

## First-Principles Rationale

The 2026-05-20 stress test was framed by SEED-022 as a memory-budgeting problem requiring profiling before mitigation. Direct code reading of `_flush_batch` in `import_service.py` makes the root cause unambiguous **without profiling**:

The import transaction wraps four workloads with wildly different rate characteristics:

| Stage | Bound by | Wall time per batch (12 games) |
|---|---|---|
| Fetch | network + platform rate limit | ~seconds |
| Parse + Zobrist hash + classify | CPU, single-threaded Python | ~600ms (12 × ~50ms) |
| DB write (positions) | Postgres I/O | <100ms |
| **Stockfish eval pass** | CPU, multi-process, depth-15 analysis | **~20-40s** (12 games × ~3 entry plies × 200-400ms wall with pool fan-out) |

The eval stage is 100-1000× slower than every other stage in the same transaction. Holding a transaction open for tens of seconds while N positions analyse causes WAL accumulation, page-cache eviction lag, and (under two concurrent importers) sustained anon-page pressure that monotonically fills swap until the OOM-killer picks Postgres. This is *visible in the log without any tracemalloc snapshots*: backend RSS plateaued at 1.36-1.42 GB while swap climbed monotonically from 317 MB to 4 GB exhausted over 25 minutes.

The structural fix is to move the eval pass out of the transaction entirely. Once batches commit in <1 second (parse + insert only), the WAL/page-cache pressure shape that filled swap disappears. Concurrent imports become I/O-light and naturally non-competitive. SEED-022's option C identified this; what this seed adds is the framing that **transaction-shortening is the win**, not "deferring eval" per se.

## Two-Lane Architecture

### Hot lane (the import endpoint)

`run_import` per-batch flow becomes:

1. Fetch batch of 12 normalized games from the platform iterator (unchanged).
2. `_collect_position_rows` — single PGN walk, builds position rows + per-ply metadata (hashes, classification, endgame_class, phase, clock, lichess `%eval` if present). Unchanged.
3. `bulk_insert_games` + `bulk_insert_positions` + bulk UPDATE `move_count` / `result_fen` via executemany (unchanged from Phase 90).
4. **New**: for each game in the batch, if every entry ply (midgame entry + each endgame-span entry) already has a populated `eval_cp` or `eval_mate` (from lichess `%eval`), set `games.evals_completed_at = NOW()` in the same UPDATE. Otherwise leave `evals_completed_at` NULL.
5. Commit. Bump per-job progress counter. Close session.
6. **Removed**: Stage 3a (`_collect_midgame_eval_targets` + `_collect_endgame_span_eval_targets`), Stage 4 (`asyncio.gather` over `engine.evaluate`), and the per-target `UPDATE GamePosition` in `_apply_eval_results`. All of this work moves to the cold lane.

Hot lane transactions become parse + insert only — sub-second per batch, same shape as a normal write workload.

### Cold lane (`run_eval_drain` — new in-process coroutine)

Started in `app/main.py` lifespan alongside the existing `run_periodic_reaper`. Runs continuously, in parallel with active imports (no admission gate — the lanes don't compete for any scarce resource once eval is out of the hot transaction).

Per drain tick:

1. `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id LIMIT 10`. If empty, sleep `_DRAIN_IDLE_SLEEP_SECONDS` (e.g. 5s) and loop.
2. For each game, load PGN and derive entry-ply targets using the existing `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` logic, lifted into a shared helper. Skip plies that already have a non-NULL `eval_cp`/`eval_mate` (same T-78-17 lichess-preservation contract as today).
3. Build one combined list of ~20-40 `_EvalTarget`s across the 10-game batch.
4. `asyncio.gather` across the existing `EnginePool` — same fan-out pattern as today's `_flush_batch`, just colocated in cold-lane code.
5. **Open one session late**, write all `UPDATE GamePosition` rows + 10 `UPDATE games SET evals_completed_at = NOW()`, commit, close.
6. Loop.

**Strict discipline**: the engine `gather` runs *outside* any session scope. The session is opened only as a short write window (<100ms even with 40 UPDATEs). Per-batch wall time ~2-4s of which the transaction holds for milliseconds. This mirrors the discipline `_flush_batch` already uses today — never `gather` inside a session.

Crash safety is unchanged: if the drain dies mid-batch before commit, all 10 games stay `evals_completed_at IS NULL` and are re-picked on the next tick. At most a few seconds of eval CPU is repeated.

### Schema migration

Add one column:

```sql
ALTER TABLE games ADD COLUMN evals_completed_at TIMESTAMPTZ NULL;
CREATE INDEX ix_games_evals_pending ON games (id) WHERE evals_completed_at IS NULL;
```

The partial index makes `WHERE evals_completed_at IS NULL ORDER BY id LIMIT 10` an instant index scan even with millions of rows in `games`.

Backfill on migration: for existing rows, set `evals_completed_at = COALESCE(updated_at, created_at, NOW())` so the cold lane doesn't try to re-eval the historical corpus. The historical corpus already has its evals (they were written by the in-transaction eval pass that this phase removes).

## UX

Driven by the existing per-user `<Cpu />` icon convention already used to mark Stockfish-dependent stats (per CLAUDE.md / existing component family).

**Header bar.** A small header element shown when a user has any pending evals:

```
<Cpu /> 87% Stockfish analysis complete (1,432 games pending)
```

Driven by a new endpoint or extension of the existing import-progress endpoint:

```python
total = SELECT COUNT(*) FROM games WHERE user_id = :uid
pending = SELECT COUNT(*) FROM games WHERE user_id = :uid AND evals_completed_at IS NULL
pct = 100 * (total - pending) / total
```

Hidden when `pending == 0`. Polled every ~10s while >0, stops polling at 100%.

**Per-metric.** Every Stockfish-dependent stat (conversion rate, recovery rate, score-gap, time-pressure-vs-performance, endgame entry eval) already shows a `<Cpu />` icon in the existing codebase. Extend the associated `EvalConfidenceTooltip` / `MetricStatPopover` body with a one-line caveat when `pending > 0` for that user:

> "Based on N of M eligible games. K still being evaluated — refresh in a minute to see updated values."

No new component family required; same Radix popover trigger as today.

## Acceptance Criteria

- Re-run the 2× 20k stress test on production: both imports complete with `status=completed` and `games_imported` within ~5 % of target.
- During the run: backend RSS plateaus ≤ 1.6 GB, Postgres `anon-rss + shmem-rss` stays ≤ 1.2 GB sustained, swap usage never exceeds 50 % of allocated swap. (These were SEED-022's acceptance criteria; carry them forward verbatim.)
- A third concurrent import (5k-game small account) triggered mid-run completes without OOM.
- User clicks "import" and sees the first opening-explorer / endgame-WDL data within ~30 s of import start (i.e. as soon as the first batch commits). Today they wait the full import duration (~28 min for 20k games).
- Eval coverage header bar reaches 100% within N minutes of import completion (N depends on game count and pool size; benchmark in dev to set expectations).
- No RAM upgrade (per user constraint 2026-05-20).
- Stockfish-dependent stats show honest "based on N of M" sample sizes while pending > 0.

## What This Seed Explicitly Does Not Pursue

- **Phase 91 import-memory profiling (SEED-022 option B).** Withdrawn. The architectural rewrite addresses the root cause directly; profiling would document a workload that no longer exists.
- **Concurrent-import admission control (SEED-022 option F).** Optional, deferred. Hot-lane batches are now too cheap to OOM under realistic concurrent load; revisit if production traffic surfaces a separate bottleneck.
- **Scope B "raw PGN first, derive everything lazily".** Considered and rejected during the discuss session — per-ply hash + classify is ~50ms/game, single-threaded Python, no I/O. Folding that into the hot lane keeps opening explorer and most endgame analytics instantly responsive. Only Stockfish earns its own lane.
- **External worker queue (Celery / arq / RQ).** Considered and rejected — significant new infra for one job type on a 7.6 GB box where the user has explicitly rejected hardware growth. In-process drain composes cleanly with the existing reaper pattern.
- **SEED-022 option G (scheduled backend restart cadence) and A′ (idempotent `on_game_fetched`).** Remain useful, independent, small. Can land any time as `/gsd-fast`. Not part of this seed.

## Suggested Sequence

1. **Phase 91 — Two-lane import: defer Stockfish eval to in-process cold drain** (this seed). Mandatory.
2. *(optional)* `/gsd-fast` for A′ (idempotent stream-retry `on_game_fetched`) if the `fetched > imported` UI discrepancy bothers users in practice.
3. *(optional)* `/gsd-fast` for G (scheduled backend restart) — small operational hardening regardless of code changes.
4. *(optional, much later)* SEED-022 option F (concurrent-import admission control) if production traffic surfaces a separate bottleneck once the lane split is in place.

The discuss-phase for Phase 91 should not need to debate the architecture — this seed locks the design (Scope A, in-process drain, parallel run with no admission gate, batch-of-10 cold transactions, CPU-icon header + per-metric caveat). Discuss-phase should focus on: exact endpoint contract for the header bar (extend existing import-progress endpoint vs new dedicated one), where the header sits in the layout (topbar vs page-level), and which metric components need the "based on N of M" extension.
