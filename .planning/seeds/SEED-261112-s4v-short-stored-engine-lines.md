---
id: SEED-261112-s4v
status: dormant
planted: 2026-11-12
refined: 2026-11-12 (second investigation: root cause re-verified, dependency map, worker protocol, benchmark lane, sizing)
planted_during: Phase 250 context (facepalm-blunder rule reads the stored refutation line; set-6 label #176 exposed a 1-ply line)
trigger_when: Now for the code fix (every day adds more truncated rows). The repair backfill before Phase 250's prod backfill, or when tactic-tag quality or short solution lines come up again
scope: two parts. A (small): engine wrapper, lane version gate, worker redeploy, two frontend hooks. B (large, operator-run): line repair, blob re-walk, opening-cache repair, benchmark lane repair and zone refresh
---

# SEED-261112-s4v: Stored engine lines are truncated to 1-2 plies in about a quarter of rows

## Why This Matters

The owner has repeatedly seen Stockfish lines of only one or two plies on the analysis board and the puzzle solution
screen. The stored data shows the same, and the short lines feed tactic tagging, the training pool and the Phase 250
facepalm rule.

Evidence status: the first investigation (subagent, 2026-11-12) produced the prod sample and the 400-position
experiment. The second (same day) re-ran the repro in the orchestrating session, read python-chess's source, sized
the tables on prod and the benchmark DB, and mapped the code paths through three read-only subagents. Items marked
(inferred) were not read in code or measured.

## Findings (prod sample: 1% of games with `full_pv_completed_at`, 10,142 games, 115,492 `game_positions.pv` rows)

| Line length (plies) | Share |
|---|---|
| 1 | 17.6% |
| 2 | 11.4% |
| 3-5 | 1.5% |
| 6-11 | 2.5% |
| 12 (cap) | 67.0% |

- Of the 33,501 rows with <= 2 plies, 1,947 are legitimately short (mate score, line ends in mate, repetition or
  50-move, stalemate or insufficient material). Unexplained: 31,554, **27.3% of all stored lines**.
- No difference by lichess-eval vs own engine, platform or month (24-30% from 2026-06 to 2026-11). Both the server
  pool (21.1%) and remote workers (29.5%) are affected, on the roughly 4k games still in `eval_jobs`.
- More frequent in quiet positions: opening 36%, middlegame 28%, endgame 19%; |eval| below 100cp 41%, 600cp and
  above 9%, mate scores 0%.

## Root cause (reproduced twice)

`EnginePool._acquire_and_analyse` (`app/services/engine.py:511`) calls `protocol.analyse(board, Limit(nodes=1_000_000))`.
python-chess merges every info line per multipv index (`AnalysisResult.post` does `self.multipv[i].update(info)`) and
returns the merged state. When the node limit lands during an aspiration-window re-search, Stockfish's last info line
is a `lowerbound` / `upperbound` line with a one or two move PV, and it overwrites depth, score and PV.

- Re-run on game 483089 ply 68 (`8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34` after Re7, multipv 2): final line
  `depth 18, lowerbound, cp +365, pv h7e7`; the last exact line was depth 17, cp +302, 24 plies.
- 400 sampled positions: final line was a bound in 17% (multipv 2: 38 lower, 30 upper) and 26.5% (multipv 1: 54 lower,
  52 upper). Every bound line had a PV of 2 plies or fewer, and all but 2 short lines were bound lines. Taking the last
  exact line left 2 and 0 short lines and always cost exactly one depth.
- Chance per run (hash state, node timing), not a property of the position: stored-short rows came back short in only
  36 of 114 re-runs.
- Depth-limited searches (`evaluate`, depth 15, entry lane) should not be affected, since they stop on a completed
  iteration (inferred, not measured).

Implementation trap: the merged dict keeps a stale `lowerbound: True` key after a later exact line, because
`update()` never removes it. The fix must read the raw per-line infos from `protocol.analysis()` (`async for info`),
not `analysis.multipv`.

## What is wrong in storage

| Stored value | Where | Damage | Detectable in SQL |
|---|---|---|---|
| `game_positions.pv` | written only at flaw plies N and N+1; about 12M rows on prod (16% of 75M positions) | about 28% have 2 plies or fewer, about 3.4M rows | yes, token count (exclude mates and terminal positions; the mate check uses row k-1's `eval_mate`) |
| `game_flaws.allowed_pv_lines` / `missed_pv_lines` | 7.65M flaws, nearly all with blobs | the blob is a walk along the stored pv, so a 1-ply pv gives a 1-element blob and a 2-3 ply pv a 3-element blob; one element in 14.5% / 15.8% of rows | yes, `jsonb_array_length` |
| `opening_position_eval.pv` | 4.9M rows, 73% with a pv | about 38% of those short, about 1.4M rows. Confirmed rows are immutable and the atomic lane transplants their pv into new games, so the cache keeps spreading short lines | yes |
| `eval_cp` / `eval_mate` (own engine) | about 63M plies in 950k games | 17-26% are bounds: median 4cp from the last exact score, p90 14-22cp, max 265cp | no |
| blob node values (`b`, `s`, `su` ...), `game_best_moves.best_cp/second_cp` | every blob node, every best-move row | same bound noise | no |
| `best_move` | 92% of positions | first move of a bound line. On a fail-low it is the previous iteration's best move, which is what the fix returns too, so this should be near-unaffected (inferred) | no |

Nothing per row records depth, a bound flag, worker id or build, so there is no way to window the damage by worker or
date. It has been present since PV storage began.

Lichess-eval games (109k on prod) are affected for pv, blobs and best-move values, which come from our engine; their
evals are lichess's and are fine.

## Derived data

| Consumer | Reads | Effect of a short line | After repair |
|---|---|---|---|
| Tactic tags (8 `game_flaws` columns) | pv string plus blob through the forcing-line gate | 1-element blob fails the one-mover discard, so no tag unless forced mate; 2-ply pv blocks detectors needing 3+ moves. Mostly missing tags, not wrong ones | Re-derived by the server on every tier-4 `/flaw-blob-submit`. `scripts/retag_flaws.py` (engine-free, 3h17m on prod for 4.76M flaws) only as a final sweep |
| Maia flaw scoring (`maia_*`) | `best_move`, `missed_pv_lines[0].su`, refutation first move | node 0 exists even in short blobs, so near-unaffected | stamp is cleared on reclassify and re-scored automatically |
| Train pool, answer key, library tactic lines, blunder-check grading | live reads of `best_move`, pv, blob | short solution lines, flaws excluded from the pool | self-heal |
| `drill_items`, `drill_solves`, medals | stored at session time | graded against the data of the day | leave as is |
| Gem / great badges | stored `game_best_moves.best_cp/second_cp` | bound noise only | leave as is |
| Herring pool | own MultiPV-5 ladder through the same wrapper | bound noise in ladder evals (inferred) | regenerate only if it shows up |
| Benchmark §5 tactic zones (`tactic_delta_zones.py`) | tags on the classical + rapid lane (138k games) | missed-tactic rates understated | lane repair, then §5 re-run and hand-update of the constants |
| Benchmark §2/§3, flaw-delta zones, percentile CDF | `eval_cp` only | bound noise | leave as is |
| Phase 250 facepalm rule | 3 plies of the stored refutation line (pv at N+1) | a truncated line can only pass through the recapture credit (250 D-02), so the rule mostly misses blunders | needs the pv repair only, not the blob re-walk |

## Part A: stop the damage (small, ship first)

1. **Engine wrapper.** In `_acquire_and_analyse`, use `protocol.analysis()` and keep, per multipv index, the last raw
   info with a PV that is neither bound; fall back to the bound line only when no exact line exists (0 of 800 runs).
   Covers server pool, drains, scripts and remote workers. Add a real-Stockfish regression test on the example
   position and a unit test with a scripted info stream.
2. **Worker gate.** The worker imports `app/services/engine.py`, so `git pull` plus restart fixes it. There is no
   auto-update and no build id on the wire. Existing mechanism: `WORKER_SCHEMA_VERSION_MIN` on `/atomic-lease`
   returns 204 and old builds idle quietly (Phase 177 precedent). Bump the worker constant to 3 and the minimum to 3,
   and extend the same 204 gate to `/flaw-blob-lease` and `/bestmove-lease`, which have no version parameter today
   (default a missing parameter to 1). Leave `/entry-lease` (depth 15) ungated so old builds still do useful work.
   Do not reject on submit (old workers would burn a full game per cycle and crash-loop every 12 minutes) and do not
   rotate the token (cuts everyone, 401 crash-loop).
   Fleet on 2026-11-12: 5 workers on 4 IPs active in the last 7 days, all schema version 2, apparently all
   operator-owned (home LAN plus Hetzner). Third-party stragglers, if any return, idle on 204 until they update;
   add a line to `REMOTE_WORKER.md`. Order: deploy server with the gate, then update own boxes.
3. **Opening cache.** Stop new short transplants: prefer the longer pv on any cache write, and see Part B step 3.
4. **Frontend.** `uciParser.parseInfoLine` already reports `bound`. Two hooks accept bound lines:
   `useStockfishEngine.ts` (deliberately, comment at :466 and tests at `useStockfishEngine.test.ts:337-377` assert
   that bound lines paint) and `useStockfishGradingEngine.ts` (never reads `bound`, latest line wins per move, and
   its per-FEN cache re-serves the short line). These drive the analysis board's Stockfish card and the reveal tree
   on the puzzle and blunder-check solution screens, so the short lines seen on the puzzle screen are live WASM
   output, not stored data. `useTrainGradingEngine.ts:494` and the worker pool already filter on `exact` and are the
   template. Open choice: drop bound lines entirely, or let a bound line update the live score but never replace
   the PV. No stored frontend data to repair.

## Part B: repair (operator-run, large)

Recommended: targeted repair, not a full re-evaluation. A full re-eval of 950k games is about 63M ply searches plus
about 100M blob-walk searches, 3-4 months of the fleet, and it would reshuffle flaw sets and orphan drill items
through eval non-determinism. The existing re-queue path (`resweep_holed_games`) does not help: it selects only
games with eval holes, and the remote atomic lane re-searches only NULL plies.

1. **pv repair.** New script: select `game_positions` rows with a short non-terminal pv, re-search with the fixed
   wrapper, write pv (and `best_move` when the first move changes). Leave `eval_cp` alone so flaw sets stay stable.
   Dedupe by position hash and write the opening cache in the same pass.
2. **Blob re-walk.** NULL the blob column(s) of flaws whose line was repaired and clear `games.blobs_completed_at`.
   The existing tier-4 lane then re-walks them on the fleet and the server re-derives tactic tags and clears the
   Maia stamp on submit. Needs a selector tweak: tier 4 keys on `allowed_pv_lines IS NULL` only.
3. **Opening cache.** Either covered by step 1's hash dedupe, or one UPDATE that NULLs short cache pvs; the existing
   heal path fills a NULL pv and the local drain re-searches pv-less transplants.
4. **Benchmark DB.** Same code produced the lane (285k games with pv, about 3.1M pv rows, about 33% short, about 1M).
   Repair pv and blobs for the classical + rapid tranches that feed §5, run the benchmark retag sweep, re-run §5
   (`chapter5.compute()` fast path) and update `tactic_delta_zones.py`. Bullet is still in flight and picks up the
   fix once the lane's workers are updated. Eval-only outputs stay.
5. **Not repaired, by recommendation:** bound-valued evals, blob node values and best-move values (undetectable,
   median 4cp), `drill_solves`, gem badges. Before locking this, measure on a sample how many flaw classifications
   flip between bound and exact evals.

### Time estimates

Basis: about 1 search per engine-second at 1M nodes; fleet history about 600 games/h at about 78 engine-seconds per
game, so roughly 1.1M searches/day at typical load (peak about 1.3M); the local 8-engine box alone about 0.7M/day.
These are estimates from table samples, not a pilot. Run a 1% pilot first.

| Step | Searches | Fleet time |
|---|---|---|
| Prod pv repair | about 3.4M (less after hash dedupe) | 3 days on the fleet, 5 days on the local box alone |
| Prod blob re-walk | 26M (only repaired lines) to 42M (both lines of every affected flaw) | 3.5 to 5.5 weeks |
| Prod opening cache | 0 if NULLed, up to 1.4M if re-searched | 0 to 1.3 days |
| Benchmark pv repair | about 1M | 1 day |
| Benchmark blob re-walk, classical + rapid | 3M to 6M (inferred from about 7 flaws per game) | 3 to 6 days |
| Retag sweeps (engine-free) | 0 | about 3.5h prod, similar for benchmark |

Total about 5 to 8 weeks of fleet time if run back to back, competing with new imports (currently 1-5k games/day).
The pv repair is the short step and is the only one Phase 250 needs. The blob re-walk can be ordered by recently
active users.

## Sequencing and parallel work

- Part A is independent of the blunder-check work. Files: `app/services/engine.py`, `app/routers/eval_remote.py`,
  `scripts/remote_eval_worker.py`, two frontend hooks and their tests. The only overlap with Phase 249/250 is
  `useStockfishEngine.ts` (the reveal tree on the blunder-check solution screen uses it), a hook-internal change.
  Run it in a dedicated worktree off `main` and release it on its own.
- Part B is mostly waiting. Its scripts are new files; the runs go from the orchestrator (`setsid nohup`), under the
  prod connection budget (operator connections below about 25).
- Phase 250 can be built now against the truncated lines. Its prod backfill should run after Part B step 1 (or be
  re-run after it). The label study (SEED-261110-p7k) was run on the truncated lines as stored.

## Open questions for discuss-phase

- When a repaired pv's first move differs from the stored `best_move`, update `best_move` and `game_best_moves`, or
  keep them and accept the mismatch with the answer key?
- Re-walk only the repaired line of a flaw, or both lines (simpler selector, 60% more searches)?
- Frontend: drop bound lines, or keep live bound scores without their PV?
- Is the flaw-classification flip rate from bound evals small enough to leave the evals alone?
- Why remote workers run higher than the server pool (30% vs 21%); likely multipv 1 vs 2, not verified.

## Breadcrumbs

- Scratch scripts and pickled samples (gitignored, dev box only): `temp/short-pv/` (`repro.py`, `sample.py`,
  `analyze.py`, `experiment.py`, `experiment.out`, `q.py`).
- Backend: `app/services/engine.py` (`_acquire_and_analyse`, `_pv_to_uci_string`), `app/services/eval_apply.py`
  (`_write_flaw_pvs`, `_walk_pv_boards`, `_build_flaw_blob_lease_positions`, `_diff_upsert_flaw_rows`,
  `_refresh_blobs_completed`), `app/services/eval_drain.py` (`_upsert_opening_cache`, `_heal_cache_pv`,
  `resweep_holed_games`), `app/routers/eval_remote.py` (`WORKER_SCHEMA_VERSION_MIN` at :159, gate at :488,
  `_merge_dedup_pv_into_engine_map`), `app/services/eval_queue_service.py` (tier claims),
  `scripts/remote_eval_worker.py` (version constant at :112), `scripts/retag_flaws.py`, `REMOTE_WORKER.md`.
- Frontend: `frontend/src/hooks/uciParser.ts`, `useStockfishEngine.ts` (:546-556, :580-586),
  `useStockfishGradingEngine.ts` (:386-425), `useTrainGradingEngine.ts` (:481-504, the filter to copy).
- Benchmark: `docs/benchmark-lane-runbook.md`, `scripts/benchmarks/chapter5.py`, `app/services/tactic_delta_zones.py`.
