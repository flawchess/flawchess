---
spike: 002
name: sf-1m-node-latency-prod
type: standard
validates: "Given the prod CPX42 under SCHED_IDLE with live traffic, when the same 1M-node benchmark runs there sequentially and with 6 concurrent workers, then per-position latency confirms the projection and API latency stays unaffected"
verdict: VALIDATED
related: [001-sf-1m-node-latency-local, 003-catchup-queue-sizing]
tags: [stockfish, eval-drain, throughput, prod, seed-012, q-008]
---

# Spike 002: Stockfish 1M-node latency (prod CPX42)

## What This Validates

Given the production Hetzner CPX42 (8 dedicated AMD EPYC vCPUs, 16 GB) running
live traffic, when the spike-001 position set (60 FENs from real games) is
analysed at 1M nodes / NNUE / multiPV=1 / Hash=32 / Threads=1 under
SCHED_IDLE, then we get the real prod per-position latency, the 6-worker
aggregate throughput, and proof that the API is unaffected at full tilt.

## How It Was Run

The benchmark ran **on the host, not inside the backend container** — 6 extra
Stockfish processes inside the container would count against its
`mem_limit: 4g` and risk an OOM-restart of the live backend. The Stockfish 18
binary was copied out of the backend image (`docker compose cp
backend:/usr/local/bin/stockfish`), runs fine on the host (embedded NNUE nets
confirmed active), and `prod_benchmark.py` is stdlib-only raw-UCI so the host
needs no python-chess. The script sets `SCHED_IDLE` on itself (children
inherit), matching `engine.py`'s prod worker scheduling. Files were cleaned
from the server afterwards.

```bash
# local: regenerate the FEN set (spike 001 script)
uv run python .planning/spikes/001-sf-1m-node-latency-local/benchmark.py \
    --dump-fens .planning/spikes/002-sf-1m-node-latency-prod/fens.txt
# server: seq + conc phases (see file header for exact commands)
```

## Results (prod CPX42, Stockfish 18, live traffic running)

| Phase | Workers | p50 s | p90 s | mean s | agg pos/s | games/day @60 plies |
|---|---|---|---|---|---|---|
| seq | 1 | 1.049 | 1.277 | 0.977 | 1.02 | 1,474 (×1 core) |
| conc | 6 | 1.053 | 1.230 | 0.966 | **5.83** | **8,388** |

API latency from outside (https://flawchess.com/api/health):

| Condition | p50 | mean | max |
|---|---|---|---|
| baseline | 65 ms | 70 ms | 101 ms |
| during 6-worker full tilt | 67 ms | 72 ms | 113 ms |

## Investigation Trail

1. **Prod core ≈ local desktop core.** Mean 0.977 s vs 0.893 s locally — only
   ~9% slower. The CPX line is dedicated-vCPU EPYC, so no burst-credit or
   steal-time cliffs to fear on sustained load.
2. **Near-perfect 6-way scaling.** Per-position latency under 6 concurrent
   workers is *identical* to sequential (0.966 vs 0.977 mean). 6 of 8 vCPUs
   saturated by SCHED_IDLE engines leaves the API untouched (Δp50 = 2 ms).
   The SEED-012 amendment's "~6 of 8 cores" capacity claim is confirmed
   empirically, kernel-level preemption included.
3. **Caveats recorded honestly:** the conc window was ~31 s, measured at one
   (light-traffic) time of day; a multi-hour sustained drain wasn't tested.
   No reason to expect degradation on dedicated vCPUs, but the milestone's
   first real catch-up run should watch host load + API latency.
4. **Memory note for the milestone:** the future drain runs *inside* the
   backend container (engine workers are child processes). 6 workers × (32 MB
   hash + working set; the 125 MiB NNUE net is file-backed and shared across
   processes from the same binary) needs explicit accounting against the
   backend's `mem_limit: 4g` before raising `STOCKFISH_POOL_SIZE` on prod.

## Results — Verdict

**VALIDATED.** Prod sustains ~5.8 positions/s on 6 workers → **~8.4k
games/day**, with zero measurable API impact. Tier-1 wall-clock for one game
fanned across 6 workers: **~10 s** — well inside the 15–30 s Lichess UX
reference. SEED-012's napkin "4–8k games/day" lands at the top of its range.
