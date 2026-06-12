# Spike Manifest

## Idea

Resolve Q-008 (`.planning/research/questions.md`): pin the real throughput of
the SEED-012 server-side full-game eval drain at the Lichess-parity search
budget (1M nodes, NNUE, multiPV=1), and size the tier-2 automatic catch-up
queue from prod data. These numbers gate the milestone's automatic-window
size, UX copy, and the 15–30s tier-1 wall-clock target.

## Requirements

- Search budget is fixed at `nodes=1_000_000`, NNUE, multiPV=1, Threads=1 per
  worker (SEED-012 D-6 — Lichess fishnet parity; calibration requirement).
- Engine config mirrors `app/services/engine.py`: Hash=32MB (spike 001 showed
  64MB gains nothing at this budget), Threads=1, SCHED_IDLE on prod.
- Throughput projections assume ~60 evaluated plies/game (post book/forced skip).

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | sf-1m-node-latency-local | standard | 1M-node per-position latency on dev machine, real-game positions | VALIDATED | stockfish, throughput, seed-012, q-008 |
| 002 | sf-1m-node-latency-prod | standard | Same benchmark on prod CPX42 under SCHED_IDLE with live traffic; API latency unaffected | PENDING | stockfish, throughput, prod, seed-012, q-008 |
| 003 | catchup-queue-sizing | standard | Tier-2 catch-up queue size from prod DB (active users × recent games lacking evals) | PENDING | prod-db, queue-sizing, seed-012, q-008 |
