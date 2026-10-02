---
id: SEED-171
status: active
promoted_to: Phase 226 (steps 0-2), Phase 227 (continuous dispatch)
planted: 2026-09-28
planted_during: v2.19, Phase 225 planned (SEED-170); standalone performance review session
trigger_when: whenever bot-move latency or analysis-board wall time becomes the priority, or the next engine milestone
scope: medium-to-large (likely two phases: root split plus the held round-underfill fix, then continuous dispatch against a relaxed determinism target). Re-measure first; read the calibration baseline drift and Phase 198 lessons sections before designing.
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

## Read first: calibration baseline drift (Phase 225)

Phase 225's calibration check found that **unchanged `main` (arm A0: engine code as shipped plus
harness tooling only) already fails parity against the committed July-21 persona curves**: Maia
pooled shift -71.9 (threshold ±85, within), SF pooled shift **-81.4** (se ~33, threshold ±50,
outside). This conflicts with the full 24-persona recalibration of 2026-08-01/02, which found no
shift. It may be noise (~2.5 se) or a harness-condition difference; nobody has investigated. Any
unit here with a calibration gate will hit the same drift, so either investigate it first or write
the accept rule to compare against a same-session A0 baseline (as Phase 225's decision branch did)
rather than against July-21. Numbers: `reports/engine-search-fixes-225/report.md`,
`verdict.json`.

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
   utilisation (items 1 and 6) matters even more. Measure in a real browser.
4. **Depth ladder / MultiPV width tuning** (depth 14 at tree plies 0-1): a strength trade-off
   owned by the grading-ladder study, not engineering. Listed for completeness.
5. **Retry continuous dispatch against a relaxed determinism target** (user decision
   2026-09-28; Phase 198 was attempted with a weaker model). Remove the round `Promise.all`
   barrier so Maia and SF overlap: standard asynchronous tree search with virtual loss / pending
   marks, as in Leela-style engines. Phase 198 measured 34.8% / 28.6% (pre-225 baseline); this
   session's model put the ceiling at 1.7-2.1x, realistic 1.3-1.6x. Re-measure after Phase 225
   and item 1, since both change the idle profile it recovers.
   - **Relaxed target, decided up front (answers SEED-130 Q1).** Drop browser/harness bit-identity
     as the contract. Candidates to pick from in discuss-phase: same top move; same
     `rankedLines` order within the top N; expected score within a stated tolerance, checked
     statistically over a fixture at c = 4. Most of 198's complexity (commit-ordered apply,
     slot release, head-of-line stalls, finding Y-6) existed only to keep bit-identity, so
     dropping it should shrink the design substantially.
   - **Keep a deterministic mode for tests and debugging:** c = 1 (or a round-mode flag) must stay
     bit-identical so unit tests and fixture gates remain exact. This is narrower than 198's
     "no retained second runner" (D-11); decide which it is.
   - **Honest gate:** add the no-Clear-Hash arm to `calibration-determinism.check.mjs` (SEED-130
     Q2) and assert the relaxed property against the shipped-like configuration, not the harness.
   - **Calibration:** the harness must run the same dispatch as the app (app == harness parity is
     about algorithm, no longer about bit-identity). Persona calibration becomes timing-dependent;
     it is already statistical, so check the persona curve shift with the SEED-170-style spot
     check and budget a refit if it moves.
   - **Still binding from 198:** abort applies zero results (L-2, finding Y-3); mobile pool of 2
     vs c = 4 (L-4); iOS stays on wasm Maia, so the win there does not shrink with WebGPU (L-6
     applies to desktop only).
   - **Process:** accept rule committed before measuring; design reviewed by independent-context
     reviewers told to attack named claims (L-7). Read `apply-order-design.md` §9b/§9d first: the
     14 undispositioned findings are a checklist of what the last design got wrong.

6. **Re-land the round underfill fix (Phase 225 item 2, held).** `selectPath` gives up instead of
   backtracking, collapsing a round to 1-2 effective concurrency on peaked positions. The fix is
   real and throughput-positive (T-50 ratio 0.945, T-400 0.953) but was held at Phase 225's gate
   by a single confirmed move-quality flip on the 12-position maia-blindness fixture (`cBFTV`:
   A0 plays `e4c6`, es 0.975; A2 plays `e2g4`, es 0.405) and by its own calibration attribution
   (`a2_vs_a0` SF shift +117.2). Reverted in `225-08`; arm A2 is `a9d5113ef`. Before re-landing,
   find out why `cBFTV` flips (tree-shape side effect vs. real bug in the fix) and use a wider
   move-quality fixture so one flip is not the whole verdict. It changes the idle profile, so
   land or reject it before sizing items 1 and 5.
   - **Root comparability guard (Phase 225 item 1, arm A21 `27beff12f`)** rides along: guards the
     bot's clear-winner early stop until every in-window root child has settled. It passed its
     own criteria (max wall 8.3 s vs 12.1 s ceiling, kept all 10 early stops, no move-quality
     flip) and was held only because it was stacked on item 2.
   - **Non-root candidate cap** (SEED-170 item 4, unmeasured): `truncateAndRenormalize` caps only
     the root (`ROOT_CANDIDATE_HARD_CAP = 15`); at policy temperature up to 2.0 a deep own-node can
     keep 20+ candidates, and MultiPV cost is ~linear in candidate count. A cap of ~6-8 is one
     constant but changes strength, so it needs its own arm. Only worth it if profiling shows
     grade CPU dominated by high-candidate non-root nodes.

## Already decided elsewhere (do not re-litigate without new evidence)

- **Maia WDL leaf values (SEED-128 / Phase 197)**: rejected by the user 2026-09-28 (does not
  trust Maia's WDL head). Do not propose WDL-based leaf values or backup reweighting as a
  throughput lever.
- **Early-stop residuals left unguarded on purpose (Phase 225 D-03/D-04):** the near-tie
  (flatness) stop branch is low-stakes, and the wall-clock deadline cut must never wait (a guard
  could make the bot flag; `botBudget.ts` documents the deadline-cut bot as intentionally
  weaker). Measured deadline exposure: 18% of post-`minNodes` snapshots had an unsettled
  in-window root child, report-only, not judged against any bar.

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
  line. Evaluate WebGPU Maia (item 3) before sizing anything whose value depends on Maia being
  slow (item 2, item 5 on desktop). iOS stays on wasm Maia, so item 5's win there is unaffected.
  Item 1 is SF-bound and survives this.
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

1. Idle box (stop local `remote_eval_worker`). Phase 225 shipped only the findability fallback,
   so the tree shape still has round underfill (item 6).
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
- SEED-127 (closed), SEED-130, SEED-170 (closed), `reports/continuous-dispatch/report.md`,
  `reports/engine-search-fixes-225/report.md`
- Server-side counterpart: SEED-172

## Phase 226 outcome (2026-10-01)

Measured against a pre-registered accept rule (`reports/engine-throughput-226/accept-rule.md`);
mechanical verdict in `reports/engine-throughput-226/verdict.json`, narrative in
`reports/engine-throughput-226/report.md`. **Nothing shipped; all three items held; refit decision
no-refit.** The branch carries `main`'s engine behavior (arm commits reverted).

| Item | Outcome | Deciding numbers | Follow-up |
|---|---|---|---|
| Item 6a, round underfill fix (arm A2 `756d2a4a1`) | hold | t400-p2 wall ratio 1.1252 > 1.05 (t50-p4 1.0376, t400-p4 0.9918, t50-p2 0.9833 pass); MQ passes (net 1, allowance 1, `cBFTV` side effect) | SEED-176 |
| Item 6b, root comparability guard (arm A21 `29f543f27`) | hold (stacked on underfill) | its own S1 8,321 ms, S2 10 vs 10, MQ net 0 all pass | SEED-177 |
| Item 1, root grade split (arm A21S `f6c1f7a54`) | hold | Clear-Hash content 0.02092 > 0.01680 (warm 0.01548 passes); also stacked on underfill; T-50 0.9694 passes | SEED-178 |
| Candidate cap (A21SC) | not run | D-17: non-root >8-candidate grade share 0.463 (50 nodes), 0.359 (400 nodes), both < 0.5 | none |

- **Idle-box re-measurement versus the loaded-box table.** Shares reproduce, absolute time about
  halves. 50 nodes: Maia 26.8-26.9% of wall (27%), SF pool utilization 46.7-46.8% (48%), depth-14
  grades 69.6-69.8% of grade time (70%), wall 13.8-14.3 s for four positions (27.1 s loaded). 400
  nodes: Maia 55.4-55.6% of wall (59%), SF pool utilization 36.9-37.1% (37%), about 23 s per
  position (43-98 s loaded).
- **Calibration baseline drift.** Phase 225's July-21 drift is attributed to cross-session
  non-comparability (the same-session A0a-vs-July comparison is void, SF null control -177.4
  against 149), not to the underfill fix. Same-session A0b-vs-A0a noise is small (Maia +0.35 +-
  26.1, SF +11.5 +- 27.3). Powered thresholds Maia 85.0, SF 53.5.
- **Machine drift is the larger finding.** Raw wall in the gate runs tracks per-grade Stockfish
  CPU, which drifted up to 1.75x between runs of identical work; see
  `reports/engine-throughput-226/analysis-2026-10-01-cpu-normalized-throughput.md` (report-only).
  Normalized, the stack is about 7-9% faster on the desktop pool and about 1% at t400-p2. Future
  throughput gates should interleave A0 and the arm in one session so per-grade CPU cancels.
- **Refit decision:** no-refit (nothing shipped; powered calibration verdicts for all three items
  also show no real shift).
- **Step 3, continuous dispatch (item 5), is Phase 227.** Prerequisite: the desktop WebGPU Maia
  measurement (D-02), which needs a machine with a WebGPU adapter. Contract and inputs: expected
  score within a tolerance over a fixture (D-05); round mode retained behind a budget flag (D-07);
  the measured round-mode warm-hash noise floor is 0 of 60 plies differing (0.0 mean |des|) at A0,
  A21 and A21S, with a separate content-instrument floor of 0.0168 (D-06 input). Phase 227's
  baseline is `main`'s engine content unless the owner overrides the Phase 226 verdict.
- **Owner decisions pending** are listed in `reports/engine-throughput-226/report.md` (three
  override ratifications, whether to override the hold-everything verdict, the A21S shape-guard
  cell).

### Owner override (2026-10-02): all three items ship

The owner ratified the three overrides and overrode the hold verdict
(`reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md`). They reasoned from
first principles: the pre-226 engine is not a gold standard, and playing slightly differently is
fine for a substantial gain.
- An interleaved re-test (3 rounds, stop rule on) confirmed the root split cuts bot-move wall time
  to 0.82x of A21: about 8% from pure speed, about 10% from earlier confident stops.
- Underfill, guard and root split are all on the branch now (`frontend/src` equals A21S).
- SEED-176/177/178 are closed.
- **Phase 227's baseline is therefore A21S, not `main`.**
