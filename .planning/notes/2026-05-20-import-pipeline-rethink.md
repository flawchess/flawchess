---
date: 2026-05-20
context: /gsd-explore session questioning whether SEED-022's profile-then-mitigate path was worth pursuing. Triggered mid-implementation of the Phase 91 context-gathering for SEED-022's profiling phase.
outcome: Pivoted away from profiling-led approach. New SEED-023 + new Phase 91 = two-lane import architecture (defer Stockfish eval to an in-process cold drain). SEED-022 marked superseded.
participants: Adrian, Claude
---

# Import pipeline first-principles rethink — 2026-05-20

## Trigger

Mid-context-gathering for Phase 91 (SEED-022 import-memory profiling), Adrian asked: *"While this phase is being implemented, I'm starting to doubt if it's worth pursuing this rabbit hole. Let's rethink the import pipeline from first principles."*

Reasonable doubt. The SEED-022 sequence (Phase 91 profiling → Phase 92α/β tuning → Phase 93 admission control) was diagnostic engineering — measure first, then mitigate. Three phases to chase a problem whose root cause turned out to be identifiable from the code alone.

## What the import code actually does (per-batch, in a single transaction)

1. Fetch a batch of 12 games (network).
2. `_collect_position_rows` — one PGN walk per game, builds ~80 PlyData per game = ~960 dicts (CPU, fast).
3. `bulk_insert_games` + `bulk_insert_positions` + bulk UPDATE of move_count/result_fen (I/O, fast).
4. **`_collect_midgame_eval_targets` + `_collect_endgame_span_eval_targets`** — for each entry ply, re-parse the entire PGN via `_board_at_ply` and replay to the target ply.
5. **`asyncio.gather(engine.evaluate(t.board) for t in eval_targets)`** — fan out Stockfish analysis across the `EnginePool` (prod `STOCKFISH_POOL_SIZE=4` on 4 vCPUs).
6. `_apply_eval_results` — sequential `UPDATE GamePosition` for each target against the same session.
7. Commit.

Stages 1-3 are fast (<1s combined). Stages 4-6 are **20-40 seconds per batch** (12 games × ~3 entry plies × 200-400ms wall with pool fan-out). The transaction lives for the duration of the entire eval pass.

## Why the OOM happened (without needing tracemalloc)

The stress-test log (`logs/import-stress-20k-each-2026-05-20.log`) shows:
- Backend RSS plateaued at 1.36-1.42 GB for the full 25-minute run. **No backend leak.**
- Postgres cgroup-attributed memory oscillated 4.3-5.4 GB.
- **Swap monotonically climbed from 317 MB to 4 GB exhausted over the run.**
- OOM-killer fired at T+~28 min; Postgres lost the score.

The mechanism: two concurrent importers each held transactions open for 20-40s per batch while evals ran. WAL accumulated faster than checkpoints could flush; page-cache had to be evicted to make room for anon allocations; eviction couldn't keep up with the sustained pressure; swap filled monotonically; eventually the next anon allocation forced the OOM scorer to pick a victim.

This is a **transaction-shape problem**, not a per-allocation problem. SEED-022 framed it as "we don't know which allocations drive the pressure, profile first" — but the answer is structural and visible in the code: the eval pass should not be inside the transaction.

## The architectural fix (locked during this session)

**Two lanes.**

### Hot lane (import endpoint)
fetch → parse → insert positions → commit. No Stockfish. Batches commit in <1 second.

Per-game: if every entry ply already has a lichess `%eval`, set `games.evals_completed_at = NOW()` in the same write. Otherwise leave NULL — cold lane will pick it up.

### Cold lane (in-process `run_eval_drain` coroutine)
Started in `app/main.py` lifespan alongside `run_periodic_reaper`. Per tick:
1. `SELECT id FROM games WHERE evals_completed_at IS NULL ORDER BY id LIMIT 10`.
2. Derive entry-ply targets (lifted `_collect_*_eval_targets` helpers).
3. `asyncio.gather` across the engine pool — **outside any session scope**.
4. Open session, apply all UPDATEs + `evals_completed_at = NOW()`, commit, close.
5. Sleep ~5s if no work; otherwise loop immediately.

**Runs in parallel with active imports. No admission gate** — once eval is out of the hot tx, the lanes don't compete for any scarce resource. Stockfish workers already run SCHED_IDLE (kernel preempts for live API traffic); transactions are short on both sides.

### UX
- Header bar: `<Cpu /> 87% Stockfish analysis complete (1,432 games pending)`. Hidden when 0.
- Per-metric: existing `<Cpu />` icon convention already marks Stockfish-dependent stats. Extend the tooltip body with "based on N of M eligible games, K still being evaluated" when pending > 0.
- "Engines are flawless, humans play FlawChess" — every number on screen stays honest about its sample size.

### Schema
One column + one partial index:
```sql
ALTER TABLE games ADD COLUMN evals_completed_at TIMESTAMPTZ NULL;
CREATE INDEX ix_games_evals_pending ON games (id) WHERE evals_completed_at IS NULL;
```

## Alternatives considered and rejected

### Scope B — "raw PGN first, derive everything lazily" (true first-principles rewrite)

Hot lane would only persist raw PGN + game-level metadata. Cold lane would do ALL per-ply work: parse, hash, classify, eval.

**Rejected.** Per-ply hash + classify is ~50ms/game, single-threaded Python, no subprocess, no I/O. Folding it into the hot lane keeps opening explorer + raw endgame WDL + flag rates + time-per-move stats instantly responsive after import. Only Stockfish is 100-1000× slower than everything else — only Stockfish *earns* its own lane. Scope B would push every interesting feature behind the "filling in" UX phase for no real win.

### Out-of-process scheduled job (systemd timer / cron on host)

Reuse the existing `scripts/backfill_eval.py` as a periodic cron-driven worker.

**Rejected (close call).** Cleanest separation, but adds another place to look when something's stuck. In-process drain composes more cleanly with the existing reaper pattern, and the SCHED_IDLE protection in `engine.py` was *designed* for exactly this use case. Kept as a defensible fallback if in-process turns out to have unforeseen issues.

### External worker queue (Celery / arq / RQ)

**Rejected.** Significant new infra (broker, worker container, monitoring) for one job type on a 7.6 GB box where the user has explicitly rejected hardware growth. Textbook architecture for a workload 10× this size; over-engineered for ours.

### SEED-022 option F — concurrent-import admission control

**Deferred.** Hot-lane batches become so cheap that "two concurrent 20k imports" stops being the OOM-defining workload. F becomes optional, not required. Revisit if real production traffic surfaces a separate bottleneck.

## Cold-lane batching — why ~10 games per transaction, not per-game

Per-game tx overhead is ~10-15ms (commit + fsync). Per-game eval wall time is ~200-400ms. Per-game txs would waste ~5-10% on commit overhead and produce 12k pointless fsyncs for a 12k-game user.

But going too big re-introduces the original problem in a different lane. A batch of 100 games × 300ms = 30s held transaction — exactly the WAL-pressure shape that killed the stress test.

Sweet spot: ~10 games per cold transaction. Wall time ~2-4s; transaction itself held for <100ms (gather happens before the session opens); commit overhead amortised across 10 games; header bar moves in 0.08% ticks for a 12k import (visually smooth). The number lives in one constant for easy tuning.

## What this means for SEED-022 / Phase 91

SEED-022 is now **superseded** by SEED-023.

Phase 91 in ROADMAP is now "two-lane import: defer Stockfish eval to in-process cold drain", **not** "import memory profiling". This is documented in the ROADMAP entry; STATE.md should be updated when Phase 91 enters `/gsd-discuss-phase`.

Phase 91 context-gathering work done before this rethink (recorded in commit `48672484`, "docs(state): record phase 91 context session") can be retained as background — most of it is shared between the profiling phase and the new architectural phase. The CONTEXT block for the new Phase 91 should explicitly note that the goal pivoted on 2026-05-20.

## Honest assessment

The discuss-phase for Phase 91 (the new one) should be short. SEED-023 locks the architecture; remaining open questions are implementation details (exact endpoint contract for the header-bar poll, where it sits in the layout, which metric components need the "based on N of M" extension). Plan should be ~5-7 plans across schema migration / backend refactor / cold drain / frontend / tests.

Time saved vs the SEED-022 path: probably 1-2 weeks of attention. The profiling phase alone would have taken ~3-5 days of careful instrumentation + report writing, then we'd still have had to do most of this architectural work.

The misjudgement in SEED-022 was being too conservative — wanting evidence before action. Worth remembering: when the code makes the failure mode visible without measurement, don't insist on measurement.
