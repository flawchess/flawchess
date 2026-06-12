---
spike: 001
name: sf-1m-node-latency-local
type: standard
validates: "Given the dev Stockfish 18 binary with engine.py's UCI config, when ~60 representative positions are analysed at nodes=1M NNUE multiPV=1, then p50/p90 sec/position and nps are measured, projecting games/day and tier-1 per-game wall-clock"
verdict: VALIDATED
related: [002-sf-1m-node-latency-prod, 003-catchup-queue-sizing]
tags: [stockfish, eval-drain, throughput, seed-012, q-008]
---

# Spike 001: Stockfish 1M-node latency (local)

## What This Validates

Given the dev Stockfish 18 binary configured like `app/services/engine.py`
(Hash=32MB, Threads=1), when ~60 positions sampled from 12 real dev-DB games
(opening-exit / middlegame / endgame) are analysed at the Lichess-fishnet
budget (`nodes=1_000_000`, NNUE, multiPV=1), then we get real per-position
latency to replace SEED-012's napkin throughput estimates.

## How to Run

```bash
# dev DB must be running
uv run python .planning/spikes/001-sf-1m-node-latency-local/benchmark.py \
    --json-out results-hash32.json
# variants: --hash 64 | --depth 15 (current engine.py convention, for comparison)
```

## Results (AMD Ryzen 7 7840HS, 16 threads, Stockfish 18)

**1M nodes, Hash=32 (the SEED-012 D-6 configuration):**

| Bucket | n | p50 s | p90 s | mean depth | mean nps |
|---|---|---|---|---|---|
| opening-exit | 22 | 1.113 | 1.191 | 21.3 | 920k |
| middlegame | 14 | 0.965 | 1.155 | 21.1 | 1.13M |
| endgame | 24 | 0.694 | 0.930 | 24.2 | 1.67M |
| **overall** | 60 | **0.965** | **1.173** | 22.4 | — |

- Mean 0.893 s/position; min 0.24, max 1.20 — tight tail, no pathological positions.
- Node budget is always fully consumed (min 1,000,008) — no early terminations.
- Depth reached: 18–61 (61 = forced endgame lines), mean 22.4 — **confirms the
  "1M nodes ≈ depth 20–23" claim** from the fishnet research.
- PV length p50 = 19 plies (min 1, at mate-adjacent positions) — far more than
  SEED-039's Tier 1–3 motif detectors need.

**Projections at 60 evaluated plies/game** (this machine; prod scaling in spike 002):

- ~54 core-seconds/game → **9,680 games/day on 6 workers**, 6,453 on 4.
- Tier-1 wall-clock (one game fanned across 6 workers): **~9 s** — comfortably
  under the 15–30 s Lichess UX reference.

## Investigation Trail

1. **Hash 32 vs 64 (fishnet uses ~64MiB/core):** statistically identical
   (mean 0.893 vs 0.900 s). At a 1M-node budget the table never gets hot enough
   to matter. → Keep the memory-lean 32MB given the project's OOM history.
2. **Node consumption check:** all 60 searches consumed the full budget; no
   mate-cutoff early exits in this sample (mates would terminate early — fine,
   they'd only make games cheaper).
3. **Depth-15 reference run (current `engine.py` convention):** mean 0.087 s
   /position — **the Lichess-parity budget costs ~10×, not the 3–5× SEED-012
   estimated.** Depth 15 would project to ~99k games/day on 6 workers vs ~9.7k.
   This sharpens the D-6 trade-off but does not overturn it: the calibration
   argument (flaw-delta zones are built on lichess %evals = fishnet 1M-node
   evals) is about correctness, not cost. Recorded so the cost of parity is
   never re-discovered as a surprise.
4. Hash persistence mirrors the planned drain (shared `game=` key within a
   game, `ucinewgame` between games). Tier-1 fan-out across workers would lose
   some intra-game hash reuse; given finding 1 (hash barely matters at this
   budget), that loss is negligible.

## Results — Verdict

**VALIDATED.** ~0.9–1.1 s/position single-threaded at 1M nodes on a fast
desktop core. The napkin estimate (0.7–1.5 M nps) was accurate; depth and PV
shape match the fishnet research. Open question for spike 002: the prod CPX42
(shared EPYC vCPUs) will be slower per core — measure the actual factor.
