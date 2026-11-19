# Fleet throughput measurements, prod flaw-line re-walk (2026-11-19)

Measurements taken during the Phase 252 prod re-walk (tier-4 flaw-blob lane) while
rolling out worker lanes (`--lanes`, quick task 261119-k9s) and the backend Maia
single-thread change (`MAIA_INTRA_OP_THREADS=1`, quick task 261119-m4t, release #490).
All times UTC. "Games/h" means re-walk games (about 30 positions each at 1M nodes,
MultiPV 2), not full-game analyses.

## Summary

| Step | Fleet games/h | Note |
|---|---|---|
| Single lane everywhere (14:41 to 14:52) | about 2,500 to 2,700 | after the claim lease (#489) |
| Lanes on yousty-1 only (14:41 to 14:52 vs before) | 2,680 | |
| Lanes on amalie-pc, amalie-nb, yousty-1 (17:03 to 18:03) | 3,843 in the hour | includes `ai-slim` for 32 min (218 games) |
| Same, after the Maia thread change (18:26 to 18:41) | 3,692 | no `ai-slim`; import load present |

- Lanes gave the whole throughput gain: about +1,110 games/h from three machines.
- The Maia thread change removed the server CPU saturation but did not measurably
  change throughput (+2%, inside noise). The server was slow, not a hard cap.
- At about 3,700 games/h the remaining ~1.0M games take roughly 11 to 12 days.

## Per-worker rates

Source: `worker_heartbeats.submit_count` deltas, each divided by that worker's own
`last_seen` interval.

| Worker | Engines / lanes | Single lane | 12 min with lanes | 1 h with lanes | Change (1 h) |
|---|---|---|---|---|---|
| amalie-pc | 14 / 2 | 758 | 1,249 | 1,231 | +62% |
| amalie-nb | 28 / 4 | 543 | 700 | 1,001 | +84% |
| yousty-1 (was mqvsj27e) | 16 / 2 | 509 | 661, later 528 | 690 | +36% |
| 5weldaqh | ? / 1 | 466 to 484 | 368 | 472 | flat |
| 3cur1kzs | ? / 1 | 215 to 236 | 234 | 232 | flat |
| ai-slim | ? / ? | n/a | n/a | about 410 while running | n/a |

Windows: single lane 14:40:49 to 14:51:59 (amalie-nb, amalie-pc: 14:40 to 14:52
reading); 12 min 16:45:24 to 16:57:36; 1 h 17:03:16 to 18:03:22.

Lessons from these numbers:

- **12-minute windows are too short.** amalie-nb read +29% in 12 minutes and +84%
  over the hour; two Hetzner workers read -20% in 12 minutes and flat over the hour.
  Use at least an hour for a per-worker conclusion.
- **Lanes help in proportion to idle engines.** A 16-engine box needs about two
  search rounds per game, so it gained least.
- **Cross-check:** per-worker submit deltas summed to 3,844 against 3,843 games with
  `blobs_completed_at` in the hour. The server's own Stockfish pool contributed
  essentially nothing to this lane while Maia held the CPU.

## Server side (8 cores, one uvicorn process)

Source: `ssh flawchess` with `vmstat`, `top -H`, `docker stats`, and Caddy JSON
access logs aggregated per endpoint (`docker compose logs --since 15m caddy`, fields
`request.uri`, `status`, `duration`).

| Measure | Before (18:13, 15 min) | After (18:42, 15 min) |
|---|---|---|
| CPU busy | 99 to 100% | 65 to 75% |
| Load average | 15 | 7 |
| Backend Python process | about 750% of 800% | about 200% |
| Server Stockfish engines | idle | 8 at 50 to 60% |
| Postgres | 2 to 3% CPU, 1 active query | 3% |
| `flaw-blob-submit` median / p95 / max | 1.95 s / 5.18 s / 9.98 s | 1.28 s / 3.37 s / 7.03 s |
| `flaw-blob-submit` per minute | 62.3 | 53.5 (window starts 3 min after restart) |
| `flaw-blob-lease` median / p95 | 0.041 s / 0.098 s | 0.036 s / 0.082 s |
| `atomic-lease` (empty, 2 per cycle) median | 0.010 s | 0.011 s |
| `entry-lease` (empty) median | 0.007 s | n/a |
| Games with `blobs_completed_at` per hour | 3,626 | 3,692 |

- **Cause of the saturation:** each `flaw-blob-submit` runs the Maia re-score inline
  (`app/routers/eval_remote.py`), and the lifespan started the ONNX session with the
  ORT default thread count (one per core). Seven inference threads sat at 80 to 92%.
- **The empty ladder rungs are cheap:** the three empty lease requests before tier-4
  work cost about 27 ms per cycle in total. A combined "next work" endpoint would not
  pay for itself.
- **The after window is contaminated by imports:** 13 full-game analyses and 29
  `atomic-submit` calls (median 6.9 s) in 15 minutes, against 1 to 2 in earlier windows.

## Maia thread-count benchmark (dev machine, 16 cores, idle)

`full_policy` on three FENs, 120 positions per arm, three interleaved rounds.

| Intra-op threads | Concurrent callers | Positions/s | CPU per position |
|---|---|---|---|
| default (16) | 1 | 12.6 to 13.2 | 607 to 633 ms |
| default (16) | 3 | 23.5 to 30.1 | 332 to 424 ms |
| default (16) | 6 | 44.1 to 46.9 | 275 to 284 ms |
| 1 | 1 | 12.4 to 12.9 | 77 to 81 ms |
| 1 | 3 | 35.2 to 36.0 | 83 to 85 ms |
| 1 | 6 | 57.6 to 60.5 | 98 to 102 ms |
| 2 | 1 | 13.8 to 13.9 | 144 to 145 ms |
| 2 | 3 | 37.8 to 38.6 | 104 to 106 ms |
| 2 | 6 | 63.8 to 64.8 | 108 to 109 ms |

## How to control for import load

Count per window, on `games`: `full_evals_completed_at` in the window with
`lichess_evals_at IS NULL` (full-game analyses by us), `evals_completed_at` (entry
evals), and `blobs_completed_at` (re-walk output, fleet-wide, the cleanest throughput
metric). If imports are heavy, compare workers on `evals_submitted` per second instead
of games per hour.

## Remaining levers (not done)

- `--lanes 2` on 5weldaqh if it has at least 12 engines (the cap is one lane per 6).
  3cur1kzs is probably too small.
- `ai-slim` back on: about +400 games/h.
- Moving the Maia re-score out of the submit response: only shortens the cycle of
  single-lane workers (about 1.3 s of a 7.7 s cycle).
- Beyond that, throughput scales with engine count. The server now has about 30% idle
  CPU, so it should take a larger fleet.

## Open

- A clean hour-long throughput comparison after the Maia change, without import load.
- Whether interactive Maia latency (analysis board, blunder check) changed on prod;
  a single call measured the same wall time locally.
