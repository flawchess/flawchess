---
id: SEED-171
status: dormant
planted: 2026-09-28
planted_during: v2.19, Phase 225 planned (SEED-170); standalone performance review session
trigger_when: after Phase 225 (SEED-170 round-underfill fix) ships, or whenever bot-move latency or analysis-board wall time becomes the priority
scope: medium (one phase; pick a subset in discuss-phase). Re-measure first; read the Phase 198 lessons section before designing.
---

# SEED-171: Browser FlawChess engine throughput (Stockfish/Maia scheduling, not a Rust port)

## Why This Matters

Bot moves take 1.7-14 s at the 50-node budget and the analysis search takes 43-98 s per
position at 400 nodes (Node measurement, see caveats). The question was whether porting parts
to Rust/WASM or C would give a big speedup. **It would not**: TS search + chess.js glue is
0.5-1.1% of wall time. Everything else is inside ORT-wasm (Maia) and Stockfish-wasm, which are
already C++ compiled to wasm with SIMD. The losses are in scheduling: Maia and most SF workers
idle a lot.

## Measured (2026-09-28, Node 24, Ryzen 7840HS, real `mctsSearch`, 4 positions)

**RE-MEASURE BEFORE ACTING.** The box was heavily loaded (load 14-21), so absolute ms are
inflated. Shares and ratios are more trustworthy than absolute numbers. Scripts:
`.planning/research/perf-profiling-2026-09-28/`.

| Budget | Wall | Maia | Stockfish | JS glue |
|---|---|---|---|---|
| Bot (50 nodes, c4, stop rule) | 27.1 s total, 1.7-14 s/move | 27% of wall (105 inferences, 48-89 ms each) | 48% pool utilisation; depth-14 calls = 70% of SF work (1.0-2.9 s each) | 0.5% |
| Analysis (400 nodes, c4) | 43-98 s/position | 59% of wall (1488 inferences, 82-139 ms each) | 37% pool utilisation | 1.1% |

Cache hit rates at 400 nodes were only 3-12%.

Critical-path model that fits the data: each round = 4 serialized Maia calls + slowest grade
(Italian: 100 rounds x (4 x 110 + 220 ms) ~ 66 s, measured 66.6 s).

Microbenchmarks:
- SF lite-single wasm: 430-485k nps. Cost ~linear in MultiPV: same 10 searchmoves at d14,
  MultiPV 1 = 103 ms vs MultiPV 10 = 2253 ms (d10: 23 vs 327 ms).
- Maia (`maia3_simplified.onnx`, 45.7 MB, fp16 weights, fp16 compute) per position, ort-web wasm:
  t=1 174 ms (b1) / 142 ms (b16); t=4 63 ms (b1) / 45 ms (b16). fp32 copy: no gain at t=4.
- chess.js: `expandChildPositions` 2.4 ms for 8 children; `encodeBoard` 4.6 us.

## Candidate work (decide in discuss-phase)

1. **Split the root grade across idle SF workers, in the single-expansion first round only.**
   Round 1 always has exactly one expansion (the root), so 3 of 4 workers idle during the most
   expensive grade (depth 14, widest MultiPV). Measured 2.8x on that grade (12 cands d14:
   4.7 s -> 1.7 s; 8 cands: 5.7 s -> 2.0 s), cp deltas within +-20 (SF's own MultiPV noise).
   Expected ~10-25% of bot-move wall. Low-medium effort, fan-out + merge below the
   `providers.grade` boundary. **Deliberately not** "any node with more candidates than busy
   workers": that would put scheduling decisions inside rounds and walk straight back into
   Phase 198's apply-order/service-order problems (see lessons below). Scoped to round 1, the
   round barrier, apply order and `mctsSearch.ts` stay untouched. Unlike continuous dispatch,
   this win is SF-bound, so it does not shrink when Maia gets faster (WebGPU); it grows as a
   share. Constraints from Phase 198 that the design must meet: see L-2, L-3, L-4, L-5.
2. **Cross-FEN Maia batching** in `maiaQueue.ts` / `maia-worker.js`. Measured ~19% less Maia
   time at t=4 wasm (~10% of analysis wall). Phase 198 measured ~1.12x and called it not worth
   it; SEED-170 lists it out of scope. ORT logits also drift in the last bits across batch
   sizes, which is a content change for the policy cache (L-3). Only worth revisiting together
   with WebGPU (dispatch-bound, likely bigger win, unmeasured).
3. **WebGPU Maia on desktop** is unmeasured. If Maia stops being the bottleneck there, SF
   utilisation (item 1, SEED-170 item 2) matters even more. Measure in a real browser.
4. **Depth ladder / MultiPV width tuning** (depth 14 at tree plies 0-1): a strength trade-off
   owned by the grading-ladder study, not engineering. Listed for completeness.

## Already decided elsewhere (do not re-litigate without new evidence)

- **Continuous dispatch / removing the round `Promise.all` barrier**: SEED-127 / Phase 198 measured
  34.8%/28.6% but closed measured-not-shipped (apply-order design failed two independent reviews;
  determinism + calibration parity). This session's agent recommended it again as #1 without
  knowing that; its upper bound here was 1.7-2.1x, realistic 1.3-1.6x.
- **Round underfill** (`selectPath` gives up instead of backtracking): being fixed in Phase 225
  (SEED-170 item 2). It likely explains part of the measured low SF utilisation, so **re-run
  `profile_search.mjs` after Phase 225** before sizing item 1.

## Lessons from Phase 198 (continuous dispatch, closed measured-not-shipped 2026-07-31)

Phase 198 measured a real 34.8% / 28.6% throughput win and still did not ship. Why it
stopped (`reports/continuous-dispatch/report.md` §8, `apply-order-design.md` §9b/§9d,
SEED-130) and what that means for any engine concurrency work here:

- **L-1: Decide the determinism target first (SEED-130, still open).** The browser never clears
  the SF hash, and slot assignment is arrival-order dependent, so at c > 1 the shipped app is
  already not bit-deterministic (97% of d14 grades diverge warm vs cleared hash, worst case
  241 cp, but only 0.0135 mean expected-score difference). ENGINE-07 bit-identity is a
  harness-only property, and the parity gate (`calibration-determinism.check.mjs`) runs on
  Clear-Hash providers, so it cannot see browser divergence. Phase 198 paid its whole
  complexity budget to preserve a guarantee the browser does not have. Discuss-phase for this
  seed should pick the target explicitly (same top move? same `rankedLines` order? expected
  score within a tolerance?) and, ideally, add the cheap no-Clear-Hash arm to the gate
  (SEED-130 question 2) so the root split can be measured against the shipped configuration.
- **L-2: Abort semantics are a live production path (finding Y-3).** Today zero results apply
  after abort. `deadlineSearch` aborts an inner controller on every deadline-cut bot move, an
  aborted `WorkerPool.grade` settles with an empty Map, and a missing grade silently becomes
  `NEUTRAL_EXPECTED_SCORE`. A fan-out where some sub-grades finish and one is aborted would
  merge into a *partial* grade and quietly create neutral-scored root children. Rule: any
  missing sub-grade means the whole grade is treated as aborted/empty, never partially merged.
  Needs a unit test.
- **L-3: Scheduling order is a content change, not "just latency" (finding Y-2).** Service order
  decides when cache writes land relative to other reads, and (via L-1) which slot's TT serves
  which position. Phase 198's design claimed a priority queue could not affect output and
  contradicted itself in the same section. For the root split: sub-grades must be merged
  before the single grade-cache write (the cache is keyed `fen|depth`, not by candidate set,
  and already has a set-mixing issue, SEED-170 out-of-scope list), and the fan-out must only
  use idle slots so it never reorders other requests.
- **L-4: Pool size is not always 4 (correction X-4).** `computePoolSize()` can return 2 on mobile
  while search concurrency is pinned at 4, so there are fewer idle workers than assumed. Size the
  fan-out from live idle slots, and measure mobile separately.
- **L-5: Calibration sits on top of the engine.** Phase 199 calibrated personas on the current
  loop, so any grade-content change needs the SEED-170 spot-check (small persona sweep), and a
  revert after calibration costs a re-sweep. Prefer small, removable changes; no in-place
  rewrite of `mctsSearch.ts` without a retained old path.
- **L-6: Faster Maia changes the economics.** 198's win was contingent on slow wasm Maia; its
  own retraction computed that at a WebGPU-plausible policy cost it drops below the 25% build
  line. Evaluate WebGPU Maia (item 3) before anything whose value depends on Maia being slow
  (item 2, and continuous dispatch generally). Item 1 is SF-bound and survives this.
- **L-7: Process.** Commit an accept rule before measuring (`reports/continuous-dispatch/accept-rule.md`
  is the template; "measured, not worth shipping" is a first-class outcome). Get the design
  reviewed by independent-context reviewers told to attack named claims with file:line evidence:
  198's self-review passed a design that two independent reviews each returned NOT SOUND with
  3 high findings.

## Won't help

- Rust/WASM search, chessops/shakmaty instead of chess.js: cuts glue 5-10x, but glue is <1%.
  Only benefit is shorter 2-3 ms main-thread jank chunks.
- Multithreaded SF build: only helps the idle-root case, which item 1 covers without the extra
  shared-memory reservation iOS cannot afford (iOS wasm reservation budget ~3 per page).
- fp32/int8 Maia in the browser: no gain at t=4, and breaks MAIA-01 (unmodified model).

## Re-measurement plan

1. Idle box (stop local `remote_eval_worker`), after Phase 225 lands.
2. `profile_search.mjs` at `50 4 4 1` and `400 4 4 0`; compare SF utilisation to the table above.
3. `split_root.mjs` for item 1's gain on the new tree shape, in both the harness (Clear Hash)
   and a shipped-like warm-hash configuration (L-1): the ±20 cp delta was measured on cleared
   hashes only.
4. Real-browser run on desktop Chrome (WebGPU if an adapter exists) and on a phone (2 SF workers,
   slower cores): Node numbers clear the SF hash per grade; the browser keeps 8 MB.

## Breadcrumbs

- `frontend/src/lib/engine/mctsSearch.ts` (~437 policy, ~478 grade, ~597 round barrier). Line refs in the 198 docs predate the Phase 215 `workerPool` split; re-locate before citing
- `frontend/src/lib/engine/workerPoolDispatch.ts:50`, `workerPoolState.ts:94-106`, `gradingLadder.ts:114,130`
- `frontend/src/lib/engine/botBudget.ts`, `useFlawChessEngine.ts:40,368`, `select.ts:21`, `policyTemperature.ts:56`
- `frontend/public/maia/maia-worker.js:474,620`, `maiaQueue.ts:166`, `maiaWorkerHost.ts:418`
- SEED-127 (closed), SEED-130, SEED-170, `reports/continuous-dispatch/report.md`
- Server-side counterpart: SEED-172
