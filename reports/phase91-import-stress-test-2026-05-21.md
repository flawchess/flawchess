# Phase 91 import-pipeline stress test — 2026-05-21

Repeat of the 2026-05-20 stress test that triggered a Postgres OOM-kill, now against the production deploy of **Phase 91 — Two-lane import: defer Stockfish eval to in-process cold drain** (PR [#130](https://github.com/flawchess/flawchess/pull/130)).

**Workload:** simultaneous import of ~20k games each from chess.com and lichess for a single user (user_id 95).
**Server:** Hetzner Cloud, 4 vCPU / 7.6 GB RAM / 4 GB swap.
**Log:** [`logs/import-stress-20k-each-2026-05-21.log`](../logs/import-stress-20k-each-2026-05-21.log) — sampled every ~33 s.

## TL;DR

Phase 91 works. Yesterday's same workload OOM-killed Postgres around the 25-min mark with swap pinned at the 4 GB cap. Today's run completed end-to-end in 73 min, with swap peaking at 2.52 GB and the system never coming close to thrashing. As a side benefit, decoupling Stockfish from the fetch loop **roughly doubled chess.com fetch throughput**.

## Timeline

**Duration:** 04:12:07 → 05:24:58 UTC — **1 h 12 min 51 s** total.

| Phase | Window (UTC) | Duration |
|---|---|---|
| Fetch (chess.com + lichess in parallel) | 04:12:30 → 04:45:00 | ~33 min |
| Drain tail (post-fetch eval drain) | 04:45:00 → 05:24:58 | ~40 min |

## Volume

| Platform | Games imported | Games evaluated | Pending at end |
|---|---|---|---|
| chess.com | 20,262 | 20,262 | 0 |
| lichess | 19,661 | 19,661 | 0 |
| **Total** | **39,923** | **39,923** | **0** |

## Throughput

| Lane | Today (Phase 91) | Yesterday (Phase 41.1, inline eval) | Change |
|---|---|---|---|
| Fetch — chess.com | ~11 g/s | ~5.5 g/s | **2× faster** |
| Fetch — lichess | ~11.5 g/s | ~11.6 g/s | flat (API-bound) |
| Eval rate during fetch | ~140 evals/min combined | inline (no separate lane) | decoupled |
| Eval rate during drain | ~700 evals/min combined | n/a | full CPU budget |

### Why chess.com doubled and lichess didn't

Lichess streams server-side evaluations directly in its NDJSON, so almost no local Stockfish work is needed per game and the fetch loop was never the bottleneck — both runs hit the same ~11.5 g/s NDJSON stream rate. Chess.com's API doesn't include evals, so every endgame position needs a local Stockfish call; under Phase 41.1, that ran inline in the fetch batch and serialised fetch behind eval. Phase 91 moves the Stockfish work to a parallel drain lane, freeing chess.com fetch to run at its natural API/CPU rate (~11 g/s), which happens to be roughly the lichess rate. The fact that the two converged is a coincidence of CPU contention between the two concurrent jobs, not API symmetry — a chess.com-only run would likely go faster still.

## Memory — peaks vs yesterday's OOM curve

| Metric | Today peak | Yesterday at OOM | Headroom today |
|---|---|---|---|
| backend RSS | 1.47 GiB | 1.56 GiB | comfortable, flat through run |
| db RSS | 5.35 GiB | 5.42 GiB | comparable |
| host mem used | 7.53 GB / 7.6 GB | 7.68 GB | ~150 MB |
| swap used | **2.52 GB** | **4.10 GB (cap)** | **1.6 GB unused** |
| `avail` | dipped to 212 MB once, recovered to 800+ MB | held at 62 MB before OOM | recovered cleanly |

### Memory shape — what the new design does well

- **Backend RSS stayed essentially flat** across the entire 73-minute run (1.30 → 1.47 GiB). The eval drain releases what it allocates each batch — no leak.
- **Swap stabilised, did not climb without bound.** During fetch, swap climbed steadily from 327 MB to ~1.9 GB and then **plateaued** in the 1.6–2.5 GB range for the rest of the run. Yesterday's curve was monotonic growth straight to the 4 GB cap.
- **`avail` recovered after each dip.** The kernel reclaimed page cache under pressure exactly as expected. Yesterday it stayed pinned in single-digit MB territory before Postgres got killed.

## CPU profile

| Phase | backend CPU | What it's doing |
|---|---|---|
| Idle baseline | ~0.5% | n/a |
| Fetch (Phase 91) | 100–200% | fetch coroutines + concurrent drain workers |
| Drain tail | 300–360% | 3+ cores on Stockfish workers, no fetch contention |
| Fetch (yesterday, Phase 41.1) | 200–330% | fetch + inline Stockfish, contended |

With the box having 4 vCPUs (400% total), Phase 91 actually uses more of the available CPU once fetch finishes — the drain lane finally gets the cores all to itself. That's why the drain phase is fast (~700 evals/min) even though the drain rate during fetch was only ~140/min.

## Verdict

1. **No OOM, no Postgres restart, no swap thrash.** The 2026-05-16 failure mode is fixed in production.
2. **Throughput improved.** chess.com fetch is ~2× faster than the same workload under Phase 41.1. Lichess unchanged (it was never the bottleneck).
3. **Failure surface is cleaner.** Backend RSS stays flat and swap reaches a steady state instead of climbing monotonically — the leading indicators that previously warned of imminent OOM no longer apply to this workload.
4. **Trade-off is acceptable.** Phase 91 extends the wall-clock end-to-end time with a ~40-min post-fetch drain tail, but the games_imported counter advances at fetch rate (not eval rate), so user-visible "import done" arrives sooner. CPU is consumed entirely on the box during the drain, but it's bounded and predictable.

## Next-step ideas (not part of this test)

If chasing more throughput becomes worthwhile:

- **Process-pool offload for position generation.** The fetch lane is now CPU-bound on a single asyncio thread doing python-chess parsing + Zobrist hashing. Spreading that across a `ProcessPoolExecutor` would unlock the 2–3 idle cores during fetch. Likely 2–3× chess.com fetch speedup.
- **Bump `_BATCH_SIZE` from 12 back toward 24–28.** Safe now that Stockfish is out of the batch path. Modest win (~3–5%) because db isn't commit-bound at the current scale — db CPU sat at 20–30% throughout.
- **`COPY` instead of `INSERT` for `game_positions`.** Worth checking if the import already uses it; the bulk-load protocol is 5–10× faster at this scale.

None of these are required — the existing pipeline is now well within the box's headroom.
