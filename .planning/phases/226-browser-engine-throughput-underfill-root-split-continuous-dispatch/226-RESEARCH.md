# Phase 226: Browser Engine Throughput — Round Underfill Re-land & Root Grade Split - Research

**Researched:** 2026-09-28
**Domain:** Browser MCTS engine scheduling (`frontend/src/lib/engine`), Node measurement harness (`scripts/`), calibration statistics
**Confidence:** HIGH for code facts and existing-tooling facts (read this session, several empirically cross-checked against committed ledgers); MEDIUM for the root-split design recommendation; LOW/ASSUMED for the calibration power model constants and the cBFTV hypothesis

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Phase split & scope
- **D-01:** Split. Phase 226 = steps 0-2; Phase 227 = continuous dispatch (step 3), depending on
  226. Reason: 227 must be sized on the idle profile that exists after the underfill fix and root
  split ship, and it needs its own design doc, independent review (L-7) and accept rule. ROADMAP.md
  is updated to narrow 226 and add 227.
- **D-02:** The **WebGPU desktop Maia measurement** (SEED-171 item 3, L-6) is a **Phase 227
  prerequisite**, not 226 work. The root split is SF-bound and does not depend on it. (This
  Linux Chrome has no WebGPU adapter, so it needs another machine.)
- **D-03:** The **no-Clear-Hash arm** for `calibration-determinism.check.mjs` (SEED-130 Q2) is
  built **in 226**. The root split changes grade content (MultiPV subset searches, ±20 cp measured
  on cleared hashes only), so its gate must see the shipped warm-hash configuration; 227 reuses the
  arm.
- **D-04:** **Mobile (L-4):** a Node harness with the pool forced to 2 workers is the gating
  measurement; a real-phone run via the dev build is report-only.

#### Determinism contract (recorded for Phase 227; D-08 applies to 226)
- **D-05:** Continuous dispatch at c=4 drops bit-identity. The replacement contract is **expected
  score within a tolerance, checked statistically over a fixture**: the picked move's d20 expected
  score vs the round-mode baseline, plus no increase in move-quality regressions. Same top move and
  `rankedLines` order are not the contract (near-ties flip with no strength cost, and the shipped
  browser already diverges by a mean 0.0135 es from the warm hash alone). — **Reversibility:**
  costly — it becomes the contract 227's gate, tests and calibration are built against.
- **D-06:** The tolerance is **anchored to the measured shipped noise floor**: 227's accept rule
  measures round-mode vs round-mode divergence under a warm hash (the D-03 arm) and allows
  continuous dispatch at most k× that. No invented number; k is fixed in 227's accept rule before
  data.
- **D-07:** **Round mode is retained behind a budget flag** as the deterministic path
  (bit-identical at any c): existing c=4 unit and fixture gates stay exact, it is 227's A0 arm, and
  rollback is a flag flip (L-5). This narrows Phase 198 D-11 ("no retained second runner").
- **D-08 (226):** The root split **keeps harness bit-identity per concurrency level**. In the
  harness, round 1 always sees the whole pool idle, so the fan-out shape is deterministic and every
  existing determinism test and gate stays exact. Relaxed determinism starts in 227. Research must
  confirm the "whole pool idle at round 1" premise in the app too (e.g. that no other consumer
  holds a slot of the same `WorkerPool`), and the sizing from live idle slots (L-4) must still
  hold.

#### Calibration gate & A0 drift
Finding behind these decisions: Phase 225's arm-vs-arm attribution was underpowered. `a2-vs-a0`
had se 36.3 against a ±50 threshold (about 1.4 se), so a no-effect change fails one of the two
families roughly 30% of the time. Both "item 2 fails calibration" and the A0 drift (-81.4 vs
July-21, about 2.5 se) may be noise.

- **D-09:** **Run A0 twice in-session** (A0a, A0b) during step 0. A0a vs A0b is the empirical
  null distribution: it answers whether the July-21 drift is noise and sizes the arm-vs-A0
  thresholds. All calibration comparisons are against the same-session A0, never against the
  July-21 curves.
- **D-10:** **Powered checks.** Size games per cell so a no-effect change fails at most ~5% of the
  time (per family, derived from the A0a/A0b null), instead of reusing the Phase 199 five-cell
  thresholds verbatim. The sizing (games per cell, thresholds) is committed in the accept rule
  before any arm runs. Long sweeps run inline from the orchestrator (setsid nohup + Monitor) under
  the resume-on-crash supervisor.
- **D-11:** **On a real (powered) shift: ship + one refit in 226.** This reverses Phase 225 D-14
  for this phase. The underfill fix is a bug fix and personas were calibrated on the buggy loop;
  holding every tree-shape change on calibration means none ever ships. One sweep + strength-curve
  refit after all shipped items are individually attributed, not one refit per item. The refit is
  conditional: skip it if no item shifts beyond the powered threshold. — **Reversibility:** costly
  — a refit rewrites the committed persona curves; reverting an item afterwards costs another
  sweep.
- **D-12:** **Arms stacked** A0 → A2 (underfill fix) → A21 (+ root guard) → A21S (+ root split).
  Attribution: underfill = A2 vs A0, guard = A21 vs A2, root split = A21S vs A21. No guard-alone
  arm. A0 is the commit that lands harness tooling + accept rule (Phase 225 pattern); arms run from
  detached worktrees with content assertions on the diffs between arms.

### Claude's Discretion (underfill re-land verdict: not discussed, the user left it to Claude)
- **D-13:** **Explain `cBFTV` before re-landing:** trace the A0 vs A2 trees at that position
  (expansion order, where values diverge, why A2 settles on `e2g4`). If it is a bug in the fix
  (e.g. the block flag leaking across rounds or interacting wrongly with `isPending`), fix it and
  re-measure; if it is a tree-shape side effect of a different 50-node budget allocation, record
  that in the report.
- **D-14:** **Widen the move-quality fixture** to at least 50 positions with d20 ground truth
  (maia-blindness 12 plus positions from existing engine fixtures/position sets; research picks
  the source, the set is committed before any arm runs). The criterion is the **paired regression
  count difference** (arm vs A0 on the same positions), with an allowance taken from the A0a/A0b
  run-to-run flip rate, instead of "one flip = hold".
- **D-15:** **Move quality stays a blocking gate.** D-11's refit covers persona strength, not
  move-quality bugs; an item that fails move quality is held regardless of calibration.
- **D-16:** The root split's throughput criterion, grade-content bound (cp delta vs a single-call
  grade under both Clear-Hash and warm hash) and the stop-rule wall ceiling are fixed in the accept
  rule from the step-0 re-measurement. "Measured, not worth shipping" is a first-class outcome.
- **D-17:** The **non-root candidate cap** gets its own arm only if step-0 profiling shows grade
  CPU dominated by high-candidate non-root nodes; otherwise it stays out (as the roadmap says).
- Root guard design carries over unchanged from Phase 225 D-01/D-02 (boost-aware window,
  `ROOT_GUARD_BOOST_ALLOWANCE`, "settled" = `visits >= 1 || isClosed`), as does the underfill design
  (225 D-06/D-07/D-08, including the permanent round-fill unit test and its mutation check).

### Deferred Ideas (OUT OF SCOPE)
- **Continuous dispatch** → Phase 227 (with D-05..D-07 and the WebGPU prerequisite, D-02).
- **Cross-FEN Maia batching**: only with WebGPU numbers in hand (227 decides).
- Still out of scope per roadmap: Rust/WASM or chessops port, multithreaded SF, fp32/int8 Maia, Maia WDL leaf values, depth ladder / MultiPV tuning, guarding the near-tie stop or the deadline cut, server-side Maia (SEED-172).

#### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`: keyword-match noise, unrelated to engine throughput (same set Phase 225 reviewed).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs (phase_req_ids is null). The planner should map plans to CONTEXT decisions instead:

| Decision | What must be delivered | Research support (section) |
|----------|------------------------|----------------------------|
| D-01 | Only SEED-171 steps 0-2 + D-03 arm; nothing continuous-dispatch | Summary, Out-of-scope guard in Pitfalls |
| D-03 | No-Clear-Hash arm in `calibration-determinism.check.mjs` | Pattern 5 |
| D-04 | Node pool-of-2 gating runs (`--pool-size` flag decoupled from concurrency) | Pattern 7, Wave 0 gaps |
| D-05..D-07 | Recorded only; do not implement round-mode flag in 226 | Pitfall 9 |
| D-08 | Root split keeps harness bit-identity per (concurrency, pool size); app premise answered | Findings F-1..F-4, Pattern 1 |
| D-09 | A0a/A0b in step 0; seed choice matters | Finding F-7, Pattern 6 |
| D-10 | Powered games/cell, committed before any arm | Pattern 6 (power table) |
| D-11 | Conditional refit, one sweep, after attribution | Pattern 8 |
| D-12 | Stacked arms from detached worktrees, content assertions | Pattern 9 |
| D-13 | cBFTV trace before re-landing | Pattern 3 |
| D-14 | ≥50-position fixture with d20 ground truth, paired criterion | Pattern 4 |
| D-15 | MQ blocking for every item | Pattern 4, Pattern 9 |
| D-16 | Throughput, grade-content bound, stop-rule ceiling from step 0 | Pattern 2, Pattern 10 |
| D-17 | Profile histogram decides the candidate-cap arm | Pattern 10 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Frontend: TypeScript strict, `noUncheckedIndexedAccess`, no `any`, `max-depth` 4 is an eslint error; `npm run lint`/`npm test` do not type-check, so run `npm run build` (tsc -b) before integrating a shared-type change (the root split adds an optional member to `EngineProviders` in `types.ts`). [CITED: frontend/CLAUDE.md]
- Knip runs in CI: every new export (e.g. `rootSplit.ts` helpers, `WorkerPool.gradeRoot`) must be imported somewhere; dead exports fail CI. [CITED: frontend/CLAUDE.md]
- No magic numbers: shard cap, power sizes, thresholds, fixture gap thresholds are named constants. [CITED: CLAUDE.md]
- Comment bug fixes at the fix site (the underfill fix already carries its D-09 comment). [CITED: CLAUDE.md]
- Python scripts: ty-clean (`uv run ty check app/ tests/ scripts/`), explicit return types, `Literal` not bare `str` for fixed sets (arm labels, family names), TypedDict for internal structures. [CITED: CLAUDE.md]
- Nesting depth ≤ 4 (backend gate is `app/` only, but keep scripts shallow too). [CITED: CLAUDE.md]
- Pre-merge gate is mandatory before the squash-merge (ruff format/check, ty ×2, function-size gate, `pytest -n auto -x`, frontend lint+build+test+knip). [CITED: CLAUDE.md]
- CHANGELOG `[Unreleased]` bullets only for items that ship. [CITED: CLAUDE.md, CONTEXT specifics]
- No unplanned scope: continuous dispatch, WebGPU, Maia batching, candidate cap (unless D-17 fires) stay out. [CITED: CLAUDE.md Project Management]
- Memory rules that bind this phase: long runs from the orchestrator via `setsid nohup` + Monitor (Bash caps at 10 min); never background a measurement inside a gsd-executor subagent (Phase 197 wave 2 died that way); executors die on ~40-min DB/measurement-heavy plans, so measurement plans run inline; wasm OOB crash ~5-6 h into blend>0 sweeps → `bin/preset-supervisor.sh` mandatory; gap-fix tests must be mutation-checked by reverting the fix; no Stockfish 19 / no onnxruntime-web bump; no Maia WDL leaf values. [CITED: MEMORY.md entries]

## Summary

The phase is mostly measurement design plus two small engine changes, and the codebase already has almost every tool it needs. The underfill fix and root guard from Phase 225 cherry-pick cleanly onto current HEAD (verified with a scratch worktree: all five commits `d428a0194 82b910bb2 a9d5113ef 4a13b2f3a 27beff12f` applied with no conflict; tests not run). `mctsSearch.ts` has not changed since Phase 225's A0, so the arm code is byte-reusable.

The root split is where the design work is. Four findings drive it. (1) Round 1 is structurally the root and only the root (`selectPath` returns null while the root is pending, `mctsSearch.ts:293`), so "round 1" = "the root grade". (2) The pool below `providers.grade` cannot tell a root grade from a depth-1 grade (both are depth 14, ladder `[14, 14]`), and "pool fully idle" is not a deterministic root signal (the first grade of every later round also sees an idle pool). (3) The Node harness does not use `WorkerPool` at all: it grades through `scripts/lib/stockfish-pool.mjs` (Clear Hash, calibration) or `engine-dispatch-stop-rule.mjs`'s `createGradePool` (warm hash, move quality/stop rule), so the split must exist on both sides. (4) Phase 225's content-assertion pattern requires arms to differ only in engine code, so the split's *activation* must live in engine code on a path every caller shares, which is `mctsSearch`. The recommended design is therefore: an optional `EngineProviders.gradeRoot` implemented by both the app pool and the harness pools (tooling lands in A0, unused until A21S), and a one-line routing choice in `dispatchExpansion` (`leaf.isRoot` → `gradeRoot`). This touches `mctsSearch.ts` by one selection line, which conflicts with the roadmap's literal "`mctsSearch.ts` untouched"; the planner must surface that as a confirmation checkpoint (Open Question 1), with the fen-equality wrapper as the no-touch fallback.

The calibration statistics also need correcting before the accept rule is written. The empirical record shows the harness is bit-reproducible for Maia-anchor games across two months (Phase 199 vs Phase 225-A0 ledgers: every matching `(pass, anchor, game_index)` Maia-anchor game identical, including across the onnxruntime 1.29 bump), while every Stockfish-anchor game differs run to run (Stockfish's Skill Level PRNG is seeded from `now()`). Consequences: A0a/A0b at the same `--seed 1` gives a degenerate (≈0) Maia-family null, so A0b should use a different seed; the "~30% false-fail" of Phase 225 comes from the SF family (≈17%) plus the Phase 199 shape guard (≈10.6% on its own); and sizing to ~50 games per (cell, anchor) brings the SF family to ≈5% false-fail at the ±50 product threshold. The shape guard should be redefined on shift z-scores. The move-quality A0a/A0b flip rate will almost certainly be 0 (Phase 225's rerun was byte-identical), so the D-14 allowance needs a floor.

**Primary recommendation:** Land all tooling first (commit T), run step 0 from T on an idle box (profiling, split_root in both hash modes, cBFTV trace, MQ A0a/A0b, powered A0a/A0b sweeps with A0b on seed 2), commit design inputs, then the accept rule (= A0), then the arm commits A2 → A21 → A21S, then the gate runs, verdict, conditional refit.

## Key Findings (answers to the delegated research questions)

**F-1. Round 1 = the root grade, exactly once.** `if (root.isPending || root.isClosed) return null;` [VERIFIED: frontend/src/lib/engine/mctsSearch.ts:293]. In round 1 the first `selectPath` returns `[root]`, the root is marked pending, the second call returns null, so round 1 dispatches exactly one expansion. The root is expanded exactly once per search (after apply, `isExpanded` is true). This also holds under the A2 underfill fix, which keeps that first line (`if (root.isPending || root.isClosed) return null;` [VERIFIED: git show a9d5113ef mctsSearch.ts diff]).

**F-2. The pool cannot identify the root on its own.** The grade call is `gradeWithDepth(leaf.fen, candidateUcis, signal, gradingDepthForTreeDepth(leaf.depth))` [VERIFIED: mctsSearch.ts:477-483] and `export const GRADING_DEPTH_LADDER = [14, 14] as const;` [VERIFIED: gradingLadder.ts:114], so tree depths 0 and 1 both grade at 14. A "pool fully idle" heuristic would also fire for the first-arriving grade of every later round (Maia is FIFO in the app, so that grade arrives into an idle pool), which is exactly the in-round scheduling SEED-171 rejects. Root identity must be signalled explicitly or inferred from `fen === rootFen` (a transposition back to the root FEN string is impossible because the FEN's fullmove/halfmove counters differ at depth ≥ 1 and the side to move differs at depth 1) [ASSUMED: reasoning about FEN counters, not tested].

**F-3. App pool topology (D-08 premise).**
- Two separate `WorkerPool` instances, never shared: the analysis board's (`useFlawChessEngine.ts`, created once per enabled hook) and the bot game's (`useBotGameEngineDispatch.ts:294`). [VERIFIED: grep of `createWorkerPool` call sites]
- Analysis pool consumers: only `mctsSearch` (`const providers: EngineProviders = { policy: queue.policy, grade: pool.grade };` [VERIFIED: useFlawChessEngine.ts:381]). Gem sweep and the eval bar use their own `useStockfishGradingEngine`/`useStockfishEngine` engines, not the pool [VERIFIED: useGemSweep.ts:81 imports `useStockfishGradingEngine`], so they compete for CPU but never hold a pool slot.
- Analysis concurrency is `concurrency: computePoolSize(),` [VERIFIED: useFlawChessEngine.ts:368]. A new search runs `abortControllerRef.current?.abort();` then `pool.stopAll();` [VERIFIED: useFlawChessEngine.ts:350-351] and starts immediately, so at the new search's round 1 some slots can still be `'stopping'` (awaiting the `bestmove` answer to `stop`). The round-1 Maia call (~60-140 ms, longer if the Maia worker is still finishing an uninterruptible stale inference) usually covers that gap, but not always → the premise "whole pool idle at round 1" is **usually but not always true in the app**.
- Bot pool consumers: the search (`grade: pool.grade,` [VERIFIED: useBotGameEngineDispatch.ts:93]) and a post-commit one-off `.grade(fen, [uci])` [VERIFIED: useBotGameEngineDispatch.ts:479] for the resign/draw score. That one-off is normally a cache hit (the root grade was written at `fen|14`), but it misses when the root grade never completed (deadline cut during round 1) or the move was a `fallbackMove`; then it occupies one slot during the user's think time, and a fast user reply makes the next bot turn's round 1 see 3 idle slots. Deadline-cut aborts also leave slots `'stopping'` briefly.
- Bot concurrency is pinned: `export const FLAWCHESS_BOT_CONCURRENCY = 4;` [VERIFIED: botBudget.ts:50], but the bot pool size is `const size = computePoolSize();` [VERIFIED: workerPoolLifecycle.ts:218]: `export const MOBILE_POOL_SIZE = 2;` [VERIFIED: workerPoolState.ts:106], `export const DESKTOP_POOL_MAX = 4;` [VERIFIED: workerPoolState.ts:100], desktop = `Math.min(DESKTOP_POOL_MAX, Math.max(DESKTOP_POOL_MIN, cores - DESKTOP_HEADROOM_CORES))` [VERIFIED: workerPoolState.ts:474]. So app fan-out k ∈ {2, 3, 4} by device.
- **Conclusion:** size the fan-out from live idle-and-ready slots at call time (L-4) in the app; that already handles `'stopping'`, busy one-off and not-yet-ready slots. App determinism is not a goal (SEED-130). The harness premise holds (F-4).

**F-4. Harness premise holds, but the harness has its own pools.** The calibration harness wires `const providers = makeNodeProviders(maiaCtx.session, maiaCtx.ort, pool.grade);` [VERIFIED: calibration-harness.mjs:383] over `stockfish-pool.mjs`, whose `grade` runs `nodeGrade` with `stockfish.send('setoption name Clear Hash');` [VERIFIED: calibration-providers.mjs:447]. Move quality and stop rule use `createGradePool` → `runOneGo` without Clear Hash (warm hash, `pool.newGameAll()` between positions) [VERIFIED: engine-dispatch-stop-rule.mjs:318-337]. The throughput tool uses its own `gradeAtDepth`/`gradeAtLadder` closures, also without Clear Hash by default [VERIFIED: engine-grading-depth-ab.mjs header lines 35-39, 461-478]. Every harness plays games/positions sequentially and awaits all work (adjudication `await pool.evalPositionWithBest(fen)` [VERIFIED: calibration-game-loop.mjs:83]; game loop `await moverWhite/moverBlack` [VERIFIED: calibration-game-loop.mjs:172]), and every `mctsSearch` round awaits `Promise.all` before the next, so at round 1 all engines are free. With Clear Hash, a shard's grade is a pure function of (fen, shard, depth); with the MQ tool's warm hash, round 1 follows `newGameAll()` so shards also see fresh tables and `acquireEngine`'s first-free scan assigns shards to engines in array order. Harness bit-identity therefore becomes per **(concurrency, pool size)**: the determinism check uses `const DETERMINISM_STOCKFISH_PROCS = 2;` [VERIFIED: calibration-determinism.check.mjs:156] and the supervisor uses `--stockfish-procs 4` [VERIFIED: bin/preset-supervisor.sh:82].

**F-5. The shipped warm-hash configuration (D-03).** Per-worker `export const WORKER_HASH_MB = 8;` [VERIFIED: workerPoolState.ts:94], set once at `uciok` [VERIFIED: workerPoolDispatch.ts:88], never cleared: `grep -rn "ucinewgame\|Clear Hash" frontend/src` (excluding tests) returns zero hits [VERIFIED: grep this session]. The TT persists across searches and across games for the pool's lifetime (pool terminates on page unmount).

**F-6. Grade cache contract.** Key `` return `${fen}|${gradingDepth}`; `` [VERIFIED: workerPool.ts:242]. Reads are all-or-nothing over the requested UCIs; writes merge. The only write site is the `bestmove` branch: `state.gradeCache.write(req.fen, req.gradingDepth, slot.accumulator);` [VERIFIED: workerPoolDispatch.ts:153], with a comment forbidding writes from abort/stop/terminate paths.

**F-7. Harness reproducibility, measured from committed ledgers.** Comparing `reports/data/sweep-199-*` (2026-07-31/08-01) against `reports/data/sweep-225-a0-*` (2026-09-27) on matching `(pass, anchor, game_index)` keys: every Maia-anchor game identical in result, plies, reason and cp_loss_sum (e.g. light1300 maia1100 24/24, deep2300 maia1900 24/24); every SF-anchor game different (0/24 in all cells, including the blend-0 null cell where the bot's code path is identical). Across Phase 225 arms the blend-0 null cell's Maia-anchor games were 24/24 identical and SF-anchor games 0/24. [VERIFIED: python comparison of the committed ledgers this session]. Stockfish's skill picker uses `static PRNG rng(now());  // PRNG sequence should be non-deterministic` [CITED: github.com/official-stockfish/Stockfish sf_17 src/search.cpp `Skill::pick_best`; the vendored build is SF 18 lite, assumed unchanged]. The Phase 225 null cells confirm the CI-derived SE is about right for the SF family: null SF shifts -45.7 (se 79.9) and +34.8 (se 78.4) [VERIFIED: reports/data/engine-search-fixes-225/calibration/verdict-a2-vs-a0.json, verdict-a21-vs-a2.json].
Implications: the July-21/A0 SF drift is consistent with SF-anchor sampling noise; the Maia family is effectively paired (common random numbers) whenever two runs share a seed; and the Phase 199 report notes the July-21 curves were measured under a *different* engine configuration (flat depth 14 + 2500 ms movetime cap) [CITED: reports/bot-parity-199/report.md:305-318], which is another reason never to judge against July-21.

**F-8. Phase 225's underfill arm moved the SF family consistently.** `a2-vs-a0` SF per-cell shifts +111.0, +96.3, +128.7, +156.2 (pooled +117.2, se 36.3), Maia +4.0 [VERIFIED: verdict-a2-vs-a0.json]. All four exposed cells in the same direction at ~3.2 se is unlikely under the null, so plan for a **real** shift from item 2 → D-11's refit is likely, and should be budgeted, not treated as a tail case. [ASSUMED: interpretation]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Round underfill fix (`selectPath` block-and-restart) | Browser engine (`mctsSearch.ts`) | Node harness (imports the same TS via alias hook) | Tree selection is engine logic; harness measures the shipped code |
| Root comparability guard | Browser engine (`mctsSearch.ts`, `botBudget.ts`, `types.ts`) | — | Bot stop rule only (`useBotGame` budget) |
| Root grade fan-out + merge (app) | Browser worker pool (`workerPoolDispatch.ts` / `workerPool.ts`) | pure helpers `rootSplit.ts` | Below the `providers.grade` boundary (L-3); pool owns slots and cache |
| Root grade fan-out + merge (harness) | Node tooling (`stockfish-pool.mjs`, `createGradePool`, depth-ab closures) | same pure helpers (lazy import) | Harness does not use `WorkerPool`; must mirror for calibration parity |
| "This grade is the root" signal | Browser engine (`mctsSearch.ts` `dispatchExpansion`) | `types.ts` `EngineProviders.gradeRoot?` | Only the orchestrator knows `leaf.isRoot` (F-2) |
| No-Clear-Hash determinism arm | Node tooling (`calibration-determinism.check.mjs`, `calibration-providers.mjs`) | — | Measures shipped warm-hash noise floor for D-16 and Phase 227 |
| Accept rule, verdicts | `reports/` docs + Python `scripts/*_verdict.py` | pytest `tests/scripts/` | Pre-registered contract + machine twin |
| Calibration sweeps | Operator (orchestrator-inline) via `bin/preset-supervisor.sh` | Python fitters | Multi-hour, crash-supervised |

## Standard Stack

No new packages. Everything uses what is already in the repo.

### Core (existing, versions from the environment)
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| vitest | ^5.0.0 [VERIFIED: frontend/package.json:79] | Engine unit tests incl. `MockWorker` pool tests | Existing engine test infra (`workerPool.test.ts` MockWorker, `mctsSearch.roundFill.test.ts`) |
| Node | v24.19.0 [VERIFIED: `node --version`] | Harness runtime (`--import scripts/lib/frontend-alias-hook.mjs`) | All engine harnesses |
| Stockfish 18 lite single wasm | vendored `frontend/public/engine/stockfish-18-lite-single.{js,wasm}` [VERIFIED: ls] | Grading in app and harness | Same binary both sides; no SF 19 (user decision) |
| onnxruntime-web + `maia3_simplified.onnx` | vendored [VERIFIED: ls frontend/public/maia] | Maia policy | No ORT bump (user decision) |
| uv / Python 3.14 | uv 0.10.9 [VERIFIED] | Verdict scripts, fitters, pytest | Existing stdlib-only verdict convention |

### Supporting (existing tooling to reuse)
| Tool | Purpose | Reuse how |
|------|---------|-----------|
| `scripts/engine-grading-depth-ab.mjs` | Throughput T-50/T-400 (ladder rows, `maia_peak_inflight`) | Add `--pool-size`, `--self-test`, root-split grade closure |
| `scripts/engine-dispatch-stop-rule.mjs` | Stop-rule wall + nodes-at-stop, `createGradePool` (warm) | Add `--pool-size`, `gradeRoot` on `createGradePool` |
| `scripts/engine-move-quality.mjs` | MQ gate (`argmaxLine` pick, d18 re-grade) | Pass `--fixture` for the widened set; self-test currently asserts `defaultRows.length === 12` [VERIFIED: engine-move-quality.mjs:324], keep default fixture unchanged |
| `scripts/calibration_parity_verdict.py` | Pooled inverse-variance shift | Reuse `parity_verdict`/`fit_new_cells`; new thresholds live in the 226 verdict script |
| `bin/preset-supervisor.sh` | Resume-on-crash sweep driver | Add `PRESET_SUPERVISOR_SEED` (hard-codes `--seed 1` [VERIFIED: bin/preset-supervisor.sh:83]) |
| `.planning/research/perf-profiling-2026-09-28/{profile_search,split_root}.mjs` | Step-0 re-measure | Extend (throwaway scripts, absolute paths, fine to edit) |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages. `package-legitimacy check` was not run because there is nothing to check. Any executor that proposes a new dependency is off-plan.

## Architecture Patterns

### System Architecture Diagram

```
                          Bot turn (useBotGameEngineDispatch)        Analysis FEN (useFlawChessEngine)
                                     |                                          |
                         selectBotMove -> deadlineSearch                        |
                                     \                                          /
                                      v                                        v
                                   mctsSearch(rootFen, budget, providers{policy, grade, gradeRoot?})
                                      |
             round 1: selectPath -> [root] only (root pending blocks 2nd pick)   rounds >= 2: up to c leaves
                                      |                                                   |
                          dispatchExpansion(root)                                dispatchExpansion(leaf)
                          policy(root) -> candidates                             policy(leaf) -> candidates
                          leaf.isRoot && gradeRoot ? --------------------+       grade(leaf) (unchanged)
                                      |                                  |                |
                                      v                                  v                v
                     APP: WorkerPool.gradeRoot                 HARNESS: pool.gradeRoot    WorkerPool / harness pool
                       cache read (full set, fen|depth)          k = free engines          (per-request cache write,
                       hit -> return                             (== pool size at round 1)  unchanged)
                       k = idle&ready slots, pending empty      shards = partition(cands,k)
                       k<=1 -> plain grade path                 k x nodeGrade/runOneGo
                       shards = partition(cands, k)             all complete? merge : throw/empty
                       k sub-requests (no cache read/write)
                       any sub not completed / abort -> stop siblings, resolve EMPTY (L-2)
                       all completed -> merge in candidate order -> ONE cache write -> resolve
                                      |
                                      v
                     Promise.all barrier -> applyExpansion in canonical order (unchanged)
```

### Recommended file layout (new/changed)
```
frontend/src/lib/engine/
├── rootSplit.ts                      # NEW (A21S): partitionCandidates(), mergeShardGrades(), ROOT_SPLIT_MAX_SHARDS
├── workerPoolDispatch.ts             # A21S: gradeRoot() + internal enqueue with {readCache, writeCache}
├── workerPoolState.ts                # A21S: QueuedGradeRequest gains writeCache flag (or completion callback)
├── workerPool.ts                     # A21S: WorkerPool.gradeRoot on the interface + facade
├── types.ts                          # A21 (guard: rootGuardBoostAllowance) + A21S (EngineProviders.gradeRoot?)
├── mctsSearch.ts                     # A2 (underfill), A21 (guard), A21S (one routing line in dispatchExpansion)
└── __tests__/
    ├── mctsSearch.roundFill.test.ts  # A2 (cherry-picked)
    ├── rootSplit.test.ts             # NEW A21S
    └── workerPool.test.ts            # A21S: new "root split" describe block (MockWorker)
frontend/src/hooks/
├── useFlawChessEngine.ts             # A21S: providers gain gradeRoot: pool.gradeRoot
└── useBotGameEngineDispatch.ts       # A21S: buildBotMoveDeps gains gradeRoot: pool.gradeRoot
scripts/
├── lib/stockfish-pool.mjs            # T: freeCount(), gradeRoot (lazy-imports @/lib/engine/rootSplit)
├── lib/calibration-providers.mjs     # T: makeNodeProviders option gradeRootFn; nodeGrade {clearHash} option
├── lib/calibration-determinism.check.mjs  # T: --no-clear-hash arm (D-03)
├── calibration-harness.mjs           # T: selectBotMoveOnce passes gradeRoot; setupHarnessEngines gradeRoot
├── engine-dispatch-stop-rule.mjs     # T: --pool-size; createGradePool.gradeRoot
├── engine-grading-depth-ab.mjs       # T: --pool-size, --self-test, root-split closure
├── engine-move-quality.mjs           # T: --pool-size (optional), gradeRoot wiring
├── engine-search-trace.mjs           # NEW T: D-13 per-round tree trace
├── build-move-quality-fixture.mjs    # NEW T: D-14 d20 fixture builder
└── engine_throughput_226_verdict.py  # NEW (A0): frozen constants twin + tests/scripts/test_...py
bin/preset-supervisor.sh              # T: PRESET_SUPERVISOR_SEED (default 1)
fixtures/engine/move-quality-226.tsv  # NEW T: >= 50 rows (12 maia-blindness + puzzles)
reports/engine-throughput-226/        # design-inputs.md, accept-rule.md, report.md, verdict.json
```

### Pattern 1: Root split — signal in the engine, fan-out below the boundary (recommended)

**What:** `EngineProviders` gains an optional `gradeRoot` with the same signature as `grade`. `dispatchExpansion` calls it for `leaf.isRoot` when present, else `grade`. Every provider that lacks `gradeRoot` (all existing test fakes, `fallbackExpectimax`) behaves byte-identically, so every existing determinism test stays exact by construction. The fan-out/merge lives in the pool (app) and in the harness pools, sharing pure helpers from `rootSplit.ts`.

**Why this over the alternatives:**
- A pool-side heuristic ("pool fully idle") is not deterministic (F-2).
- A `fen === rootFen` wrapper applied at call sites needs wiring in `useFlawChessEngine`, `buildBotMoveDeps`, `selectBotMoveOnce` and each measurement script that calls `mctsSearch` directly (move quality, stop rule, depth-ab, profile_search). That puts the activation in tooling, so arm A21S would differ from A21 in `scripts/`, breaking the "arms differ only in engine code" content assertion, and a missed site silently measures an unsplit bot (T-168.5-04-01 failure shape). With the recommended design the tooling supplies `gradeRoot` from A0 onwards and it stays dormant until the A21S engine routes to it.
- **Conflict to surface:** the roadmap says "`mctsSearch.ts` untouched". The change is one provider-selection line in `dispatchExpansion`; the round barrier, apply order, selection and stop rule are untouched. Needs a user confirmation checkpoint (Open Question 1). Fallback if refused: the `fen === rootFen` wrapper at every seam listed above, with the content assertion rewritten to allow the listed `scripts/` wiring diff in A21→A21S.

**App side (`workerPoolDispatch.ts`):**
- Full-set cache read first (`gradeCache.read(fen, candidateUcis, depth)`); hit → return.
- `k = min(idle-and-ready slot count, candidateUcis.length, ROOT_SPLIT_MAX_SHARDS)`, counted as `slot.state === 'idle' && slot.isReady && slot.current === null && !slot.dead`, and only when `state.pending.length === 0`. `k <= 1` → the existing `grade()` path unchanged (this also covers the spawn-in-flight and dead-pool guards).
- Partition deterministically: round-robin by candidate index (`i % k`), as `split_root.mjs` does; candidate order is Maia prior descending from `truncateAndRenormalize`, so round-robin spreads high-prior moves across shards.
- Enqueue k sub-requests with `readCache: false, writeCache: false`; `dispatchNext` assigns them to the k idle slots synchronously (nothing else is pending), so no other request is reordered (L-3).
- **L-2:** resolve the whole grade to an empty Map if any sub-request did not *complete* (abort, watchdog fire, slot death, stopAll) or the outer signal aborted; on the first failed shard, stop the siblings (internal `AbortController` linked manually to the outer signal; do not rely on `AbortSignal.any`, which older iOS Safari lacks [ASSUMED]). Prefer an explicit "completed via bestmove" flag per sub-request over "map is non-empty": a shard whose candidates were all illegal completes with an empty map, and treating that as failure would diverge from the single-call path (SF silently drops illegal `searchmoves`, per the headless-verification memory note). Candidates are legal by construction (Maia mask), so this is an edge case, but the flag makes the rule exact.
- All completed → merge in original candidate order → exactly one `gradeCache.write(fen, depth, merged)` → resolve. Update the "bestmove is the ONLY caller of gradeCache.write" comment: the split group's success path becomes the second write site, still success-only.
- The root is exempt from 8XN-7 (`if (grades.size === 0 && !signal.aborted && !leaf.isRoot)` [VERIFIED: mctsSearch.ts:506]), so an empty root grade degrades to today's behavior (root children at `NEUTRAL_EXPECTED_SCORE`), same as a failed single-call root grade.

**Harness side:** `stockfish-pool.mjs` gains `freeCount()` and `gradeRoot(fen, cands, signal, depth)` = k from free engines, `Promise.all(shards.map(s => withEngine(pool, e => nodeGrade(e, fen, s, depth))))`, merge. `createGradePool` and the depth-ab closures get the same over `runOneGo`. The partition/merge helpers come from `await import('@/lib/engine/rootSplit')` inside the `gradeRoot` body, so A0..A21 tooling never touches the (absent) module; only A21S's engine calls `gradeRoot`. Add a harness tripwire: in `gradeRoot`, if `freeCount() !== size` at call time, record/print it (the D-08 premise is then violated for that run).

### Pattern 2: Grade-content bound for the split (D-16)

The SEED-171 "±20 cp" was measured on 2 positions with cleared hashes only [VERIFIED: split_root.mjs has two FENs and uses `pool.grade`, which clears hash]. Step 0 should extend `split_root.mjs`:
- Position set: the 16 throughput positions + the widened MQ fixture roots (~70 roots), root candidate sets from a real `policy()` + `truncateAndRenormalize` + hard cap (not hand-picked lists).
- Clear-Hash mode: split vs single, per-candidate |Δcp| and |Δes| (mover POV via `evalToExpectedScore`); single-vs-single is exactly 0 here, so this bound is absolute (report p50/p95/max).
- Warm mode: engines warmed by grading the preceding positions of a game line (or the previous search's grades) without Clear Hash; measure split vs single AND single vs single on two differently-warmed engines. The single-vs-single number is the shipped noise floor (Stage A measured mean |Δes| 0.0135 [CITED: SEED-130 / reports/grading-ladder/findings-stage-a.md:139-148]).
- Accept-rule form (numbers fixed after step 0): warm-hash mean |Δes|(split vs single) ≤ c × warm mean |Δes|(single vs single), plus root argmax-flip rate reported. [ASSUMED: criterion form]

### Pattern 3: cBFTV diagnosis (D-13)

**Code under test (A2):** a non-root node reached with zero selectable children is marked `isBlocked`, pushed to `blockedThisRound`, and the walk restarts from the root; the parent filter excludes blocked children; flags clear right after the fill loop, before `Promise.all`; `isBlocked` is a separate flag from `isPending` (D-07) [VERIFIED: git diff 1b5313b96 a9d5113ef -- mctsSearch.ts]. Static reading finds no leak: every blocked node is pushed to the per-round list and cleared unconditionally, including when the round dispatches nothing.

**Leading hypothesis [ASSUMED]:** a tree-shape side effect, not a bug. At a fixed 50-node budget, pre-fix underfill made peaked positions run more, smaller rounds (closer to c=1, more sequential information per node). The fix fills rounds with breadth from less-favored subtrees, so the 5-ply mating line behind the `e4c6` sacrifice gets fewer sequential refinements, and a depth-≥2 node graded at the d10 floor (`export const GRADING_DEPTH_FLOOR = 10;` [VERIFIED: gradingLadder.ts:130]) can miss the mate and pull `e4c6` below `e2g4`.

**Trace tool (`scripts/engine-search-trace.mjs`, lands in T):** real providers in the MQ configuration (`createGradePool` warm, `newGameAll()` first, elo 1500, 50 nodes, stop off, c=4). Wrap `policy`/`grade` and `onSnapshot`:
- Round id increments at the first `policy()` call after any `onSnapshot` (all policies of round r are issued after round r-1's apply loop; round 1 is the root's single policy call).
- Record per expansion: round, leaf FEN, candidate UCIs, grade depth, per-candidate cp. Reconstruct paths by recording child FEN → (parent FEN, uci) with chess.js when a grade's candidate list is seen.
- Record per snapshot: `nodesEvaluated`, root lines `(rootMove, visits, practicalScore)`.
- Output a TSV/JSON per run.
Runs: A0 and A2-candidate at c=4 (the gate config), plus c=1 and c=2 at A0 as references, on cBFTV and the other 11 maia-blindness rows as controls. The discriminating readouts: round-size sequence A0 vs A2; the round at which `e4c6`'s value drops below `e2g4`'s in A2 and which expansion caused it (a d10 grade missing a mate = side effect); whether A0 at c=1 plays `e4c6`. A bug signature would be: a node blocked in round r still excluded in round r+1, or a pending leaf re-selected.
Trace runs must happen from detached worktrees (see Pattern 9) because `@/` resolves relative to the alias hook's own location (`const FRONTEND_SRC = path.resolve(__dirname, '../../frontend/src');` [VERIFIED: scripts/lib/frontend-alias-hook.mjs]).

### Pattern 4: Widened move-quality fixture and paired criterion (D-14, D-15)

**Source (recommended):** 12 `maia-blindness.tsv` rows + 40-48 lichess CC0 puzzles from `fixtures/tagger/detector_fixture_test.csv` (8,017 puzzles, schema `PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating` [VERIFIED: head of the file; count per SEED-129]). SEED-129 already proposes this corpus as the engine-change instrument; `maia-blindness.tsv` itself sources 11 rows from the same corpus. The engine position sets (16 throughput/stop positions: openings and middlegames) are near-tie positions with no single correct move and would add rows that almost never regress; include none, or at most a few as controls.

**Pre-registered selection rule (committed before generation):** order candidates by SHA-1 of `PuzzleId` (never Python `hash()`, per the tagger re-seed memory note); stratify by rating band (e.g. 1000-2200 in 200-wide bands) and exclude PuzzleIds already in maia-blindness; for each candidate run headless Stockfish (vendored lite wasm via `spawnStockfish`; no native `stockfish` on the box [VERIFIED: `which stockfish` empty]) at depth 20 MultiPV 2 over all legal moves; keep iff the d20 top move equals `PV[0]` and `eval_gap_cp ≥ MIN_GAP_CP` (e.g. 150, mate at `MATE_CP_EQUIVALENT` 1000 per the fixture's own header convention); stop when the band quotas are filled. Write rows in the existing column shape (`id fen correct_move eval_gap_cp note source`) so `loadFixtureRows`/`validateFixtureIntegrity` read it unchanged. Budget: d20 on lite wasm is seconds to tens of seconds per position; run 4-8 processes in parallel, orchestrator-inline.

**Paired criterion (recommended form) [ASSUMED]:** per arm pair on identical positions, count flips `p→r` (pass to regression) and `r→p`. Hold iff `(p→r) − (r→p) > A`, where `A = max(1, d0)` and `d0` = positions whose verdict differs between the A0a and A0b MQ runs. Each `p→r` flip counts only if a fresh-process rerun reproduces it (Phase 225 Pitfall 8, `reruns` subcommand). Report McNemar's exact one-sided p on the discordant pairs alongside, report-only. Rationale for the floor: Phase 225's `a2/mq-off-rerun` reproduced every row byte-for-byte [VERIFIED: reports/engine-search-fixes-225/report.md §3], so `d0` will very likely be 0 and "allowance from the A0a/A0b flip rate" alone would recreate "one flip = hold". With ~55 rows, A = 1 tolerates a 1.8% net drift.

**Runs:** A2 vs A0 stop off; A21 vs A2 stop on; A21S vs A21 **both** stop on and off (the split changes root grade content, which both modes read).

### Pattern 5: No-Clear-Hash arm (D-03)

- `nodeGrade(stockfish, fen, candidateUcis, depth, { clearHash = true } = {})`; the arm passes `false`. Pool option `createStockfishPool({ size, hashMb: WORKER_HASH_MB, clearHash: false })` so a respawned engine is configured identically (the pool already pins `hashMb` for that reason).
- **Separate grading pool.** In the harness, the same engines also serve adjudication, whose `evalPositionCpWithBest` sends `Clear Hash` every ply [VERIFIED: calibration-providers.mjs:486], and anchor moves. A warm arm that shares that pool is not shipped-like. The arm needs a grading-only pool (as the browser's bot pool is), with adjudication/anchors on another pool.
- **What it asserts vs reports.** The existing Clear-Hash bit-identity assertion stays. The warm arm asserts only structure (no `Clear Hash` line sent on the grading pool, via a send spy; both runs complete) and **reports** divergence: plies where the bot's move differs between two fresh-pool runs of the same seeded game, first-divergence ply, and mean |Δes| of the two picks re-graded at depth ≥ 18. That number is the round-mode warm-hash noise floor Phase 227's D-06 needs, and it gives D-16 a warm-hash split-vs-noise comparison when run at A21 and A21S.
- Do not `ucinewgame` between games in the warm arm unless deliberately modelling SEED-130 Q4; the browser keeps the TT across games.

### Pattern 6: Powered calibration (D-09, D-10)

**Power model [ASSUMED: normal approximation; per-sweep SE scales as 1/√N; SEs from Phase 225's bootstrap CIs]:**

| Games per (cell, anchor) | SF se_diff | SF false-fail at ±50 | Maia se_diff | Maia false-fail at ±85 | Phase 199 shape guard alone |
|---|---|---|---|---|---|
| 24 (Phase 225) | 36.3 [VERIFIED: verdict-a2-vs-a0.json] | ≈16.9% | 38.3 [VERIFIED] | ≈2.6% | ≈10.6% |
| 48 | 25.7 | ≈5.1% | 27.1 | ≈0.2% | ≈10.6% (unchanged, see below) |
| 50 | 25.1 | ≈4.7% | 26.5 | ≈0.1% | ≈10.6% |
| 56 | 23.8 | ≈3.6% | 25.1 | <0.1% | ≈10.6% |

Combined at N = 24 ≈ 1 − (0.831 × 0.974 × 0.894) ≈ 28%, matching CONTEXT's "roughly 30%".

- **Shape guard.** Phase 199's guard flags a cell when the new rating falls outside the *old* CI in both families. Under the null with equal SEs that happens per family per cell with P(|Z| > 1.96/√2) ≈ 16.6%, ≈2.8% for both families, ≈10.6% over 4 cells, independent of N (it compares against a CI that shrinks at the same rate). It fired at 1500/0.5 in three of five Phase 225 verdicts [VERIFIED: report.md §7]. Replace it in 226 with a z-based guard: flag a cell iff `|shift| / se_shift > 1.96` in both families (≈0.25% per cell, ≈1% over 4 cells). [ASSUMED: independence of families]
- **Recommended sizing:** 50 games per (cell, anchor) (25 per color) for every cell, keeping the product thresholds ±85 Maia / ±50 SF, and the null-control validity gate. Compare A2 vs A0a, A21 vs A2, A21S vs A21 (D-12 attribution).
- **A0a/A0b and the seed.** With the same `--seed 1`, A0a and A0b produce identical Maia-anchor games (F-7), so the Maia-family null is exactly 0 and says nothing. Run **A0b with `--seed 2`** so both families get a real null; keep A0a and all arms on seed 1 so arm-vs-A0a comparisons are paired in the Maia family (conservative vs the unpaired SE model). `bin/preset-supervisor.sh` needs `PRESET_SUPERVISOR_SEED`. [ASSUMED: interpretation of D-09's intent; needs confirmation, Open Question 3]
- **How A0a/A0b enter the rule.** N must be fixed before A0a/A0b run (they take ~a day at N = 50), so the accept rule sizes N from the model and uses A0a/A0b as a model check with a pre-registered consequence, e.g. "if either family's A0a-vs-A0b |shift| exceeds 1.96 × its model se_diff, inflate that family's threshold to the observed |shift| (or stop and escalate)". Also add a drift cross-check that costs nothing: A0a's Maia-anchor games for game indices already present in `sweep-225-a0-*` should be byte-identical (engine for the bot is equivalent; item 3 is bot-invisible per Phase 225 D-10d).
- **Pooling trap.** `load_bot_cells` overwrites per (cell, anchor): `accum.wdl_vs_maia[anchor] = wdl` [VERIFIED: scripts/calibration_anchor_fit.py:565], and `fit_new_cells` overwrites per cell key. Concatenating two runs' `-cells.tsv` silently drops one. Any pooling (e.g. A0a+A0b) needs an explicit pre-sum by (cell, anchor).
- **Wall time.** Phase 225 per-cell summed game time at N = 24: 5.9-8.9 h for the four search cells, 0.6 h for the null cell, with ~10 harnesses concurrent [VERIFIED: elapsed_ms sums from the committed ledgers]. At N = 50 expect ~12-19 h per search cell. Sweeps needed: A0a, A0b, A2, A21, A21S = 25 cells. On the 16-core box [VERIFIED: nproc] with ~10-12 concurrent harnesses: roughly 2 days of sweeps, plus a possible refit (Pattern 8). Each harness averages about one busy core (runbook §2); the 2026-08 persona sweep at `--parallel 12` alongside the remote eval worker OOM-killed the box (memory), so stop the local `remote_eval_worker` first (it is not running now [VERIFIED: pgrep]).

### Pattern 7: Pool-of-2 measurement (D-04)

Every gating tool ties pool size to concurrency: depth-ab `--procs` is "Stockfish process pool size; also used as SearchBudget.concurrency" [VERIFIED: engine-grading-depth-ab.mjs:75], move quality likewise (`concurrency: args.procs` [VERIFIED: engine-move-quality.mjs measureRows]), and stop rule `createGradePool(args.procs)`. Add `--pool-size N` (default = `--procs`) to depth-ab, stop-rule and move-quality. Mobile configs to run: bot 50 nodes / c4 / pool 2 (the pinned bot concurrency on a 2-slot pool) and analysis 400 nodes / c2 / pool 2 (`computePoolSize()` sets both on mobile). With pool < concurrency, later rounds queue in `acquireEngine`'s FIFO; with a warm hash, content becomes arrival-order dependent — acceptable for throughput, not a determinism claim.

### Pattern 8: Conditional refit (D-11)

The shipped calibration chain [VERIFIED: grep of scripts/bin]:
- Curves: `bin/run_bot_curves_sweep.sh` (presets `human|0|700,...,2300`, `light|0.05|1100,...,1900`, `deep|0.5|1100,...,2600`) → combine `-cells.tsv` → `scripts/calibration_anchor_fit.py` → `reports/data/bot-curves-internal-scale.json` → `scripts/gen_bot_strength_curves.py` → `reports/data/bot-strength-lookup.json` + `frontend/src/generated/botStrengthCurves.ts` (CI drift-checked).
- Persona labels: `bin/run_persona_calibration_sweep.sh` → `scripts/calibration_persona_fit.py` → `reports/data/persona-calibration.json` → `scripts/gen_persona_calibration.py` → `frontend/src/generated/personaCalibration.ts` (CI drift-checked).
- The blend-0 human preset cannot move (no search on that path), so a refit only needs the 10 light/deep curve cells and the blend>0 personas. Traps (memory): the persona script skips any dir that already has `-cells.tsv` (use a fresh `PERSONA_SWEEP_DATA_DIR`); `gen_persona_calibration.py` hard-codes the canonical input path (promote before regenerating); PAVA makes label promotion all-or-nothing per style column; judge drift on raw `approx_blitz`, not labels (1800 ceiling, round-to-50).
- "One sweep" in D-11 is ambiguous between the curve grid and the persona sweep (Phase 199's own text says a refit means "refit the curves and persona labels" [CITED: reports/bot-parity-199/report.md:317]). Open Question 4.
- Decision rule: refit iff any item's powered attribution fails its threshold; run it once on the final shipped configuration, after the verdict.

### Pattern 9: Arm mechanics (D-12), reused from Phase 225

- Commits: **T** (tooling, fixture, trace tool, verdict skeleton) → step-0 runs from T → **design-inputs** doc → **A0** (accept rule + frozen verdict constants; engine identical to `main`) → **A2** (cherry-pick `d428a0194 82b910bb2 a9d5113ef`, plus any D-13 fix confined to `mctsSearch.ts`) → **A21** (cherry-pick `4a13b2f3a 27beff12f`) → **A21S** (root split). All five cherry-picks apply cleanly to current HEAD [VERIFIED: scratch worktree `git cherry-pick --no-commit` this session; tests not run].
- A0a/A0b run from T, not A0, because they are design inputs for the rule. Content assertion for that: T and A0 differ only in `reports/`, `.planning/`, `scripts/*_verdict.py`, `tests/scripts/`.
- Arm content assertions: tooling diff (`scripts/*.mjs`, `scripts/lib/`, `bin/`, `frontend/package*.json`) empty between every arm pair; A0 `frontend/src/lib/engine` identical to `git merge-base main A0`; A0→A2 limited to `mctsSearch.ts` + `__tests__/mctsSearch.roundFill.test.ts`; A2→A21 limited to `mctsSearch.ts`, `types.ts`, `botBudget.ts`, `__tests__/mctsSearch.test.ts`, `frontend/src/hooks/useFlawChessEngine.test.tsx` (Phase 225's lists [VERIFIED: accept-rule.md §1]); A21→A21S limited to `rootSplit.ts`, `workerPool*.ts`, `types.ts`, `mctsSearch.ts` (the `dispatchExpansion` hunk only), `useFlawChessEngine.ts`, `useBotGameEngineDispatch.ts` and their tests.
- Worktrees `../flawchess-226-{a0,a2,a21,a21s}` via `git worktree add --detach`, each with `( cd frontend && npm ci )`; copy all output back into the phase checkout and commit before removing a worktree (Phase 225 procedure). Calibration ledgers under `reports/data/sweep-226-*` are gitignored; force-add TSVs only (Phase 225 precedent).
- Verdict script: new `scripts/engine_throughput_226_verdict.py` with its own frozen constants (arms `a0a a0b a2 a21 a21s`, `EXPECTED_MQ_POSITIONS` = the new fixture's count, powered thresholds, z-based shape guard, paired MQ rule) importing the generic readers from `engine_search_fixes_verdict.py` (`read_single_tsv`, `_ladder_rows`, `cells_to_payload`, `evaluate_throughput` where the shape fits). Leave the 225 script read-only: it is the frozen twin of a published report.
- **Sequencing:** wall-clock runs (throughput, stop rule, profile) alone on an idle box, never concurrent with sweeps or test suites; MQ and calibration are node-deterministic and may overlap each other. Every long run from the orchestrator (`setsid nohup ... & disown` + Monitor), never inside or backgrounded by a gsd-executor subagent.

### Pattern 10: Step-0 profiling for D-16/D-17

`profile_search.mjs` already records `byDepth` (grading depth → calls, ms, mean candidates) [VERIFIED: profile_search.mjs]. Grading depth 14 covers tree depths 0 and 1, so it cannot answer D-17 as is. Add, inside its `grade` wrapper: `isRoot = (f === rootFen)`, and a histogram of grade ms by (isRoot, grading depth, candidate-count bucket ≤4 / 5-8 / 9-12 / 13+). D-17 decision metric: share of total grade ms from non-root grades with more than 8 candidates, at 50/c4/stop-on and 400/c4. Pre-register the threshold for "dominated" in the design-inputs doc before looking (e.g. ≥ 50%) [ASSUMED: threshold]. Also note `profile_search.mjs` grades through `stockfish-pool` (Clear Hash) and runs its own cache, so it is a relative-share instrument; the depth-ab tool is the gate instrument. Run each profile twice to see run-to-run spread.

### Anti-Patterns to Avoid
- **Splitting "any node when workers are idle":** puts scheduling inside rounds (Phase 198 Y-2); rejected by SEED-171.
- **Partial merge on abort:** an aborted shard's empty Map merged with finished shards creates neutral-scored root children (L-2, Y-3).
- **Writing sub-grades to the cache individually:** writes a partial `fen|depth` entry that a later subset read (the bot's post-commit `grade(fen,[uci])`) would hit (L-3).
- **Same seed for A0a and A0b:** degenerate Maia null (F-7).
- **Concatenating `-cells.tsv` to pool runs:** silently drops data (Pattern 6).
- **Judging against July-21:** different engine configuration and SF-anchor noise (F-7).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Crash-resumable sweeps | a new driver loop | `bin/preset-supervisor.sh` (+ `PRESET_SUPERVISOR_SEED`) | Proven under OOM and wasm-OOB crashes; append-mode ledger resume |
| Pooled shift arithmetic | new SE/pooling code | `calibration_parity_verdict.py` `_cell_shift`/`_pool_shifts`, `fit_new_cells` | One SE definition on both sides |
| Stockfish process pool in Node | private acquire/release | `stockfish-pool.mjs` (`run`, `withEngine`, dead-engine respawn) | Five scripts lost engines before it existed |
| Grade `go` line | string concatenation | `buildGradeGoCommand` | `searchmoves` must be last (158-01 landmine) |
| UCI info parsing | regex | `parseInfoLine` (`@/hooks/uciParser`) | Keyed by `pv[0]`, `bound === 'exact'` |
| Expected-score conversion | cp→es formula | `evalToExpectedScore` (`@/lib/liveFlaw`) | Same as MQ gate |
| Bot pick in harness | re-implement argmax | `argmaxLine` (`@/lib/engine/botSampling`) | The judged selector |
| Deterministic ordering in fixture selection | Python `hash()` | SHA-1 of the id | `hash()` is salted per process (memory note) |
| Pool fake in tests | new fake | `MockWorker` + `driveInit` in `workerPool.test.ts` | Drives UCI lines per slot synchronously |

## Common Pitfalls

### Pitfall 1: Root split measured in the harness but not in the app (or vice versa)
**What goes wrong:** app splits, harness doesn't (or the reverse), so calibration measures a bot that doesn't ship.
**How to avoid:** Pattern 1 (engine-side routing + `gradeRoot` on every harness pool from T). Add a harness check in the A21S worktree that `gradeRoot` is actually called once per search (counter) in each gate tool.
**Warning signs:** A21S grade_calls equal to A21's in depth-ab rows.

### Pitfall 2: Fan-out steals busy or stopping slots
**What goes wrong:** counting `slots.length` instead of idle-and-ready slots, or fanning out while `pending` is non-empty, reorders other requests (L-3).
**How to avoid:** count `state === 'idle' && isReady && current === null && !dead` with `pending.length === 0`; unit test with one slot busy.

### Pitfall 3: Empty-map-as-failure edge case
**What goes wrong:** a shard that completes with no exact lines (all its searchmoves illegal) collapses the whole root grade, while a single call would have returned a partial map.
**How to avoid:** track completion per sub-request (bestmove-settled) separately from contents.

### Pitfall 4: `AbortSignal` listener leaks per shard
**What goes wrong:** k listeners per root grade on the search's signal (WR-02 history: ~400 leaked listeners per analysis search once before).
**How to avoid:** reuse the existing settle-wrapper pattern in `grade()` for each sub-request; the group itself adds at most one listener and detaches it on settle.

### Pitfall 5: Degenerate nulls
**What goes wrong:** A0a/A0b same seed → Maia null 0; MQ A0a/A0b byte-identical → allowance 0 → "one flip = hold" again.
**How to avoid:** A0b on seed 2; MQ allowance floor `max(1, d0)`.

### Pitfall 6: Wall-clock contamination
**What goes wrong:** throughput/stop-rule runs overlap a sweep, a test suite, or the local remote eval worker (the SEED-171 numbers were taken at load 14-21 [CITED: SEED-171]).
**How to avoid:** stop the worker (not running now, [VERIFIED: pgrep]), check `/proc/loadavg` before each wall-clock run, run them in one sequential driver before launching sweeps.

### Pitfall 7: Arm output lost with the worktree
**How to avoid:** copy back and commit before `git worktree remove`; gate removal on `git ls-files` for every expected file (Phase 225 procedure).

### Pitfall 8: Executor-hosted long runs
**What goes wrong:** measurement dies with the subagent (Phase 197 wave 2), or the executor SSE-times out at ~40 min.
**How to avoid:** plans that run measurements are orchestrator-inline tasks; executors only write code, tests, docs.

### Pitfall 9: Scope creep into Phase 227
**What goes wrong:** adding a round-mode flag, continuous dispatch hooks, or a priority queue now.
**How to avoid:** D-05..D-07 are recorded, not implemented. The only 227-facing deliverable is the D-03 arm.

### Pitfall 10: Stale verification after doc edits
**What goes wrong:** editing a covered file after the verifier ran invalidates the fingerprint (memory note).
**How to avoid:** finish report/doc edits before dispatching the verifier.

### Pitfall 11: Knip and tsc on the new optional provider field
**What goes wrong:** `gradeRoot` on `WorkerPool` unused in some build, or `EngineProviders` shape change missed by `npm test` (no type-check).
**How to avoid:** `npm run build` and `npm run knip` in the A21S plan's verify step.

## Code Examples

### Engine-side routing (A21S, the only `mctsSearch.ts` change)
```typescript
// Source: pattern derived from mctsSearch.ts:477-483 (read this session)
// Round 1 is always the root, and the root is expanded exactly once (selectPath's
// root-pending guard), so this routes exactly one grade per search.
const gradeFn = (leaf.isRoot ? providers.gradeRoot : undefined) ?? providers.grade;
const grades = await (gradeFn as GradeWithLadderDepth)(
  leaf.fen,
  candidateUcis,
  signal,
  gradingDepthForTreeDepth(leaf.depth),
);
```

### Pure helpers (A21S, `rootSplit.ts`)
```typescript
// Source: partition shape from .planning/research/perf-profiling-2026-09-28/split_root.mjs
// (chunks[i % 4]); ROOT_SPLIT_MAX_SHARDS is an [ASSUMED] name/value.
export const ROOT_SPLIT_MAX_SHARDS = 4;

export function partitionCandidates(candidateUcis: readonly string[], shardCount: number): string[][] {
  const k = Math.max(1, Math.min(shardCount, candidateUcis.length));
  const shards: string[][] = Array.from({ length: k }, () => []);
  candidateUcis.forEach((uci, i) => shards[i % k]!.push(uci));
  return shards;
}

/** Merge completed shard grades in original candidate order. Callers must pass
 *  only shards that COMPLETED; any non-completed shard means the caller returns
 *  an empty Map instead (L-2). */
export function mergeShardGrades(
  candidateUcis: readonly string[],
  shards: readonly Map<string, MoveGrade>[],
): Map<string, MoveGrade> {
  const merged = new Map<string, MoveGrade>();
  for (const uci of candidateUcis) {
    for (const shard of shards) {
      const g = shard.get(uci);
      if (g) { merged.set(uci, g); break; }
    }
  }
  return merged;
}
```

### Harness `gradeRoot` (T, dormant until A21S routes to it)
```javascript
// Source: stockfish-pool.mjs withEngine/nodeGrade (read this session); lazy import so
// A0..A21 worktrees, which lack rootSplit.ts, never load it.
gradeRoot: async (fen, candidateUcis, signal, gradingDepth) => {
  const k = freeEngineCount(pool);
  if (k <= 1 || candidateUcis.length <= 1) {
    return withEngine(pool, (engine) => nodeGrade(engine, fen, candidateUcis, gradingDepth));
  }
  const { partitionCandidates, mergeShardGrades, ROOT_SPLIT_MAX_SHARDS } = await import('@/lib/engine/rootSplit');
  const shards = partitionCandidates(candidateUcis, Math.min(k, ROOT_SPLIT_MAX_SHARDS));
  const parts = await Promise.all(
    shards.map((s) => withEngine(pool, (engine) => nodeGrade(engine, fen, s, gradingDepth))),
  );
  return mergeShardGrades(candidateUcis, parts);
},
```
(`withEngine` throws on failure rather than resolving empty, so harness failure semantics are "the game errors", not a silent partial merge.)

### Unit tests to write (A21S, MockWorker)
- 4 idle slots, 10 candidates → 4 `go ... searchmoves` commands whose move sets are disjoint and cover all 10; merged result has all 10; a follow-up `grade(fen, allCands, …, 14)` is a cache hit (`cacheStats().hits` +1) and a follow-up `grade(fen, [oneCand])` also hits.
- Abort mid-flight → resolves empty Map, every thinking shard received `stop`, no cache entry (follow-up is a miss).
- One shard's slot watchdog-fires or errors → whole grade empty, siblings stopped.
- One slot busy with another request → k = 3, the busy request completes untouched.
- Pool of 2 (`stubDesktopSizing` to a mobile core count) → k = 2.
- 1 idle slot or 1 candidate → byte-identical command stream to plain `grade()`.
- `mctsSearch` with a `gradeRoot` spy: called once, with the root FEN and full root candidate set, never for non-root; without `gradeRoot`, existing ENGINE-07 determinism tests unchanged.
- Mutation checks (revert and confirm failure): partial merge instead of empty; per-shard cache writes; routing line removed.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Grade root with one MultiPV call on one worker | Fan out across idle workers, merge before one cache write | This phase (A21S) | ~2.8x on the root grade (SEED-171, cleared hash, loaded box); re-measure |
| Five-cell parity with 24 games/anchor, CI-overlap shape guard | Powered N (~50), z-based shape guard, same-session A0 | This phase | False-fail ≈28% → ≈5-6% |
| 12-position MQ fixture, one flip = hold | ≥50 positions, paired net-flip criterion with floor | This phase | One position no longer decides an item |

**Deprecated/outdated:**
- Comparing arms to July-21 curves: measured under flat-14 + movetime cap (199 report), and SF-anchor noise dominates.
- SEED-171's absolute timings: taken at load 14-21; re-measure.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fen === rootFen` uniquely identifies the root grade (FEN counters differ at depth ≥ 1) | F-2, Pattern 1 fallback | Fallback wrapper could split a non-root grade; only matters if the fallback is chosen |
| A2 | cBFTV flip is a tree-shape side effect (breadth vs sequential refinement, d10 floor missing a mate) | Pattern 3 | If it is a bug, A2 needs a code fix and re-measure before the accept rule's A2 lookup |
| A3 | Power model: normal approx, per-sweep SE ∝ 1/√N, families independent, CI-derived SE ≈ true SE | Pattern 6 | N=50 could still over- or under-power; A0a/A0b model check mitigates |
| A4 | A0b should use seed 2 to get a real Maia null | Pattern 6 | If the user wants a same-seed null, the Maia family null is 0 by construction |
| A5 | MQ paired rule `A = max(1, d0)` and McNemar report-only | Pattern 4 | Too lenient/strict allowance; user may prefer a different floor |
| A6 | Puzzle corpus (detector_fixture_test.csv) + d20 filter + gap ≥ 150 cp is a good widening source | Pattern 4 | Fixture could be too easy/hard at elo 1500 (low discordance, weak test) |
| A7 | D-17 "dominated" = ≥50% of grade CPU from non-root grades with >8 candidates | Pattern 10 | Wrong trigger for the candidate-cap arm |
| A8 | Warm-hash content criterion form `split ≤ c × single-vs-single` | Pattern 2 | Bound too loose/tight; c fixed after step 0 |
| A9 | Stockfish 18 lite keeps SF 17's time-seeded skill PRNG | F-7 | Only affects the explanation; the ledger evidence stands on its own |
| A10 | `AbortSignal.any` unavailable on some supported iOS Safari versions | Pattern 1 | Minor; manual linking works everywhere |
| A11 | Item 2's +117 SF shift in 225 is real, so a refit is likely | F-8 | Refit budget may be unused |
| A12 | `ROOT_SPLIT_MAX_SHARDS = 4` | Code examples | Cosmetic; k is bounded by pool size anyway |

## Open Questions

1. **May `mctsSearch.ts` get the one routing line?**
   - What we know: the roadmap and SEED-171 say "`mctsSearch.ts` untouched"; the intent is "no scheduling inside rounds". The only engine-controlled activation path shared by app and every harness is `mctsSearch` (F-2, Pattern 1).
   - Recommendation: add a `checkpoint:decision` before the A21S plan; default to the routing line; fallback is the `fen === rootFen` wrapper with a rewritten A21→A21S content assertion.
2. **Does the split need a minimum candidates-per-shard?**
   - What we know: MultiPV cost is ~linear in candidates with a small fixed part (d14 MultiPV 1 = 103 ms vs MultiPV 10 = 2253 ms [CITED: SEED-171]); extra total CPU across shards is unmeasured.
   - Recommendation: measure total shard CPU vs single-call CPU in step 0 (extended split_root); only add a minimum if mobile CPU cost looks material.
3. **Seed for A0b.** Recommend seed 2 (Pattern 6). Needs user confirmation since D-09 says "run A0 twice".
4. **Which refit?** Curves (10 light/deep cells), persona labels (blend>0 personas), or both. Phase 199 treated a refit as both. Recommend asking before the verdict plan; budget ~1 day of sweeps.
5. **Real-phone run (report-only).** Needs the owner's phone; per the "run human-action checkpoints yourself" memory, automate everything else and defer only this hardware leg.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | all harnesses | ✓ | v24.19.0 | — |
| Vendored SF 18 lite wasm | grading, d20 fixture build | ✓ | stockfish-18-lite-single | — (no native `stockfish` on PATH) |
| Maia ONNX | policy | ✓ | maia3_simplified.onnx | — |
| vitest / frontend node_modules | unit tests | ✓ | ^5.0.0 | — |
| uv / Python | verdict scripts, fitters | ✓ | uv 0.10.9 | — |
| 16 cores / 30 GB RAM | concurrent sweeps | ✓ | nproc 16, 30 GiB | fewer concurrent cells |
| Idle box | wall-clock gates | ✓ now (load ~1.0, no remote_eval_worker) | — | pause any worker (SIGSTOP with user approval, 225 precedent) |
| WebGPU adapter | not needed (D-02) | ✗ | — | out of scope |
| Real phone | report-only mobile run | owner's device | — | defer, report-only |

**Missing dependencies with no fallback:** none for gating work.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest ^5.0.0 (frontend); Node `--self-test`/`.check.mjs` harness checks; pytest (verdict script) |
| Config file | `frontend/vite.config.ts` `test` block (project-wide timeouts; never add per-file timeouts) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/mctsSearch.roundFill.test.ts src/lib/engine/__tests__/rootSplit.test.ts` |
| Full suite command | the CLAUDE.md pre-merge gate (ruff, ty ×2, function-size, `uv run pytest -n auto -x`, `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`) |

### Deliverable → Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-06/225 (A2) | Every non-tail round dispatches c expansions on peaked policies | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` | ❌ cherry-pick from a9d5113ef |
| A2 mutation | Reverting the restart fails the round-fill test | mutation | same, with fix reverted | — |
| A21 guard | Unsettled in-window child blocks clear-winner stop; closed top settles | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "stop rule"` | ❌ cherry-pick 4a13b2f3a/27beff12f |
| D-02/225 | `rootGuardBoostAllowance` present on `FLAWCHESS_BOT_STOP_RULE` | unit | `npx vitest run src/hooks/useFlawChessEngine.test.tsx` | ❌ cherry-pick |
| D-08 | Existing ENGINE-07 determinism tests unchanged | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "ENGINE-07"` | ✅ |
| L-2/L-3/L-4 | Split: disjoint cover, one cache write, abort/death → empty, idle-only, pool 2 | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "root split"` | ❌ Wave 0 |
| L-2 mutation | Partial merge / per-shard write reverts fail the tests | mutation | same, with fix reverted | — |
| Routing | `gradeRoot` called once per search for the root only | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "gradeRoot"` | ❌ Wave 0 |
| Helpers | partition/merge pure functions | unit | `npx vitest run src/lib/engine/__tests__/rootSplit.test.ts` | ❌ Wave 0 |
| D-08 harness | Same-seed blend=1 game byte-identical at pool 2 (with split in A21S) | real-engine check | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` | ✅ (run in A21S worktree) |
| D-03 | Warm arm sends no Clear Hash on grading pool; reports divergence | real-engine check | same file with `--no-clear-hash` | ❌ Wave 0 |
| D-04 tooling | `--pool-size` parses, defaults to `--procs` | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs --self-test` (new), `scripts/engine-dispatch-stop-rule.mjs --self-test` | ❌ depth-ab has no self-test [VERIFIED: grep count 0]; ✅ stop-rule |
| D-14 fixture | Every row legal, recorded move legal, ≥ 50 rows | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test` (+ a `--fixture fixtures/engine/move-quality-226.tsv` integrity case) and `scripts/build-move-quality-fixture.mjs --self-test` | ❌ Wave 0 |
| D-13 tool | Trace parses args, reconstructs round ids on a stub provider | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-search-trace.mjs --self-test` | ❌ Wave 0 |
| Verdict twin | Frozen constants, paired MQ rule, z shape guard, powered thresholds | unit | `uv run pytest tests/scripts/test_engine_throughput_226_verdict.py` | ❌ Wave 0 |
| Parity arithmetic | Pooled shift math unchanged | self-test | `uv run python scripts/calibration_parity_verdict.py --self-test` | ✅ |
| Gates | Throughput, stop rule, MQ, calibration | measurement (orchestrator-inline) | accept-rule command lines | — |

### Sampling Rate
- **Per task commit:** the quick run command (seconds) plus the touched tool's `--self-test`.
- **Per wave merge:** `cd frontend && npm test -- --run && npm run lint && npm run build`; `uv run pytest tests/scripts -x`.
- **Phase gate:** full pre-merge gate green and the accept-rule verdict rendered before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `frontend/src/lib/engine/__tests__/rootSplit.test.ts`
- [ ] "root split" describe block in `workerPool.test.ts`
- [ ] `gradeRoot` routing tests in `mctsSearch.test.ts`
- [ ] `scripts/engine-grading-depth-ab.mjs --self-test` + `--pool-size`
- [ ] `--pool-size` in stop-rule and move-quality tools (+ self-test cases)
- [ ] `scripts/engine-search-trace.mjs` + self-test
- [ ] `scripts/build-move-quality-fixture.mjs` + self-test; `fixtures/engine/move-quality-226.tsv`
- [ ] `--no-clear-hash` arm in `calibration-determinism.check.mjs` (+ `nodeGrade` `clearHash` option, grading-only pool)
- [ ] `PRESET_SUPERVISOR_SEED` in `bin/preset-supervisor.sh`
- [ ] `scripts/engine_throughput_226_verdict.py` + `tests/scripts/test_engine_throughput_226_verdict.py`

## Security Domain

Client-side engine scheduling and offline measurement tooling. No new endpoints, auth, persistence or user input paths.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | limited (tooling) | Fixture integrity check before any engine spawns (`validateFixtureIntegrity`); UCI move strings only from chess.js / Maia mask |
| V6 Cryptography | no | SHA-1 used only as a deterministic ordering key, not for security |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Resource exhaustion on low-end devices (k extra concurrent searches) | DoS | Fan-out bounded by live idle slots (already-spawned workers only); no new workers or memory reservations (iOS wasm budget unaffected) |
| Stale/partial grade cached and reused | Tampering (integrity) | Single success-only merged write; abort/death paths never write |
| Tampered fixture silently weakening the gate | Tampering | Fixture committed before any arm; integrity check; accept rule never edited, overrides as separate docs |

## Sources

### Primary (HIGH confidence, read this session)
- `frontend/src/lib/engine/{mctsSearch,workerPoolDispatch,workerPoolState,workerPool,workerPoolLifecycle,botBudget,gradingLadder,types,selectBotMove,deadlineSearch}.ts`
- `frontend/src/hooks/{useFlawChessEngine,useBotGameEngineDispatch,useGemSweep}.ts`
- `scripts/lib/{calibration-providers,stockfish-pool,calibration-determinism.check,frontend-alias-hook}.mjs`, `scripts/{calibration-harness,engine-move-quality,engine-dispatch-stop-rule,engine-grading-depth-ab}.mjs`, `scripts/{calibration_parity_verdict,calibration_anchor_fit,engine_search_fixes_verdict}.py`, `bin/{preset-supervisor,run_bot_curves_sweep}.sh`
- Git: A0→A2 and A2→A21 diffs (`1b5313b96`, `a9d5113ef`, `27beff12f`); cherry-pick dry run onto HEAD
- Committed ledgers: `reports/data/sweep-199-*`, `reports/data/sweep-225-{a0,a2,a21}-*`, `reports/data/engine-search-fixes-225/calibration/*.json`
- `.planning/seeds/SEED-171`, `SEED-130`, `SEED-129`; Phase 225 CONTEXT, 07/08 SUMMARY; `reports/engine-search-fixes-225/{accept-rule,report}.md`; `reports/bot-parity-199/{runbook,report}.md`; `.planning/research/perf-profiling-2026-09-28/`

### Secondary (MEDIUM)
- Stockfish `Skill::pick_best` PRNG seeding: github.com/official-stockfish/Stockfish (sf_17 `src/search.cpp`)

### Tertiary (LOW)
- Power-model constants and criterion forms (Assumptions A3, A5, A7, A8)

## Metadata

**Confidence breakdown:**
- Code/tooling facts: HIGH (read and quoted; several cross-checked against ledgers and a cherry-pick dry run)
- Root-split design: MEDIUM (design reasoning; Open Question 1 needs the user)
- Calibration statistics: MEDIUM for the diagnosis (ledger evidence), LOW for exact N/thresholds (model)
- cBFTV explanation: LOW until the trace runs

**Research date:** 2026-09-28
**Valid until:** 2026-10-28 (engine code is stable; re-verify if `mctsSearch.ts` or the pool changes)
