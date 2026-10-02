# Phase 226: Browser Engine Throughput — Round Underfill Re-land & Root Grade Split - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Cut bot-move latency and analysis wall time in `frontend/src/lib/engine` by fixing Stockfish
scheduling, behind a pre-committed measurement gate. **This phase covers SEED-171 steps 0-2 only**
(D-01):

0. Re-measure on an idle box (throughput profile, root-split gain, A0 calibration null).
1. Re-land the round underfill fix (Phase 225 arm A2 `a9d5113ef`) with the root comparability
   guard (arm A21 `27beff12f`) riding along.
2. Split the round-1 root grade across idle SF workers (SEED-171 item 1).

Plus the no-Clear-Hash arm in `scripts/lib/calibration-determinism.check.mjs` (D-03).

**Continuous dispatch (step 3) is Phase 227**, not this phase. Its determinism contract is
decided here (D-05..D-07) so 227 starts with it locked.

</domain>

<decisions>
## Implementation Decisions

### Phase split & scope
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

### Determinism contract (recorded for Phase 227; D-08 applies to 226)
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

### Calibration gate & A0 drift
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
### Post-research decisions (plan-phase, 2026-09-28; answers to 226-RESEARCH.md Open Questions 1, 3, 4)
- **D-18:** **Root split activates via an optional `EngineProviders.gradeRoot` plus one routing
  line in `mctsSearch.ts` `dispatchExpansion`** (root grade only). This narrows the roadmap's
  "`mctsSearch.ts` untouched" to "no scheduling change inside rounds": round barrier and apply
  order stay untouched. The app pool and every harness grade path (stockfish-pool, createGradePool,
  depth-ab closures) implement `gradeRoot`; the harness side lands in the A0 tooling commit and
  stays dormant until A21S. The `fen === rootFen` wrapper is rejected. — **Reversibility:**
  cheap (one line plus an optional provider field).
- **D-19:** **A0b runs on seed 2** (A0a on the default seed), via a `PRESET_SUPERVISOR_SEED`
  hook in `bin/preset-supervisor.sh`, so both the Maia and the SF families get a real empirical
  null (same-seed Maia games are byte-identical).
- **D-20:** **Refit scope, if D-11 triggers: both** the strength curves (10 light/deep cells) and
  the blend>0 persona labels, as Phase 199 did. Budget about 1 day of sweeps.
- Root guard design carries over unchanged from Phase 225 D-01/D-02 (boost-aware window,
  `ROOT_GUARD_BOOST_ALLOWANCE`, "settled" = `visits >= 1 || isClosed`), as does the underfill design
  (225 D-06/D-07/D-08, including the permanent round-fill unit test and its mutation check).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed and roadmap
- `.planning/seeds/SEED-171-browser-engine-throughput.md`: full measurements, L-1..L-7 Phase 198 lessons, candidate items, re-measurement plan, breadcrumbs
- `.planning/seeds/SEED-130-browser-grade-nondeterminism-uncleared-stockfish-hash.md`: Q1 (answered by D-05) and Q2 (D-03 arm)
- `.planning/ROADMAP.md` Phase 226 and Phase 227 entries

### Phase 225 (held items being re-landed)
- `.planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-CONTEXT.md`: guard and underfill designs (D-01/D-02/D-06..D-09), measurement gate pattern
- `.planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-RESEARCH.md`, `225-07-SUMMARY.md`, `225-08-SUMMARY.md`: arm execution, reverts
- `reports/engine-search-fixes-225/report.md`, `verdict.json`, `accept-rule.md`: `cBFTV` flip, calibration decision branch, A0 drift numbers
- Arm SHAs: A0 `1b5313b96`, A2 `a9d5113ef`, A21 `27beff12f`

### Profiling
- `.planning/research/perf-profiling-2026-09-28/README.md`, `profile_search.mjs` (`50 4 4 1`, `400 4 4 0`), `split_root.mjs`: re-measure scripts

### Phase 198 lessons and accept-rule precedents
- `reports/continuous-dispatch/apply-order-design.md` §9b/§9d: undispositioned findings (Y-2 scheduling = content change, Y-3 abort semantics)
- `reports/continuous-dispatch/accept-rule.md`, `reports/continuous-dispatch/report.md`: accept-rule template
- `reports/bot-parity-199/runbook.md`, `reports/bot-parity-199/accept-rule.md`: calibration sweep procedure (the powered version replaces its thresholds, D-10)
- `reports/grading-ladder/override-2026-07-31.md`: move-quality procedure

### Harness and gate tooling
- `scripts/lib/calibration-determinism.check.mjs`: gets the no-Clear-Hash arm (D-03)
- `scripts/engine-move-quality.mjs`, `scripts/engine-grading-depth-ab.mjs`, `scripts/engine-dispatch-stop-rule.mjs`, `scripts/engine_search_fixes_verdict.py`, `scripts/calibration_parity_verdict.py`, `scripts/calibration-harness.mjs`, `bin/run_persona_calibration_sweep.sh`
- `fixtures/engine/maia-blindness.tsv`: base of the widened fixture (D-14)

### Documentation to update
- `docs/flawchess-engine-explained-2026-07-06.md`: guard scope (if it ships) and the root split

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/engine/workerPoolDispatch.ts`: `dispatchNext` (~72) already scans idle, ready slots; `grade` (~161) is the public entry. The root split fans out and merges below this boundary (L-3), so `mctsSearch.ts` only sees one `providers.grade` result.
- `mctsSearch.ts` `dispatchExpansion`: the 8XN-7 empty-grade handling is the model for L-2. A fan-out with any missing or aborted sub-grade must resolve as an empty (aborted) grade, never a partial Map.
- Phase 225 arms A2/A21 hold the underfill and guard code plus tests (`__tests__/mctsSearch.roundFill.test.ts`), ready to cherry-pick.

### Established Patterns
- Accept rule committed before data, never edited, overrides as separate docs; stacked arms from detached worktrees with diff content assertions (Phase 225).
- Determinism per concurrency level over the canonical apply order (module header of `mctsSearch.ts`); D-08 keeps it for 226.
- Bot concurrency is pinned (`botBudget.ts` `FLAWCHESS_BOT_CONCURRENCY`); the analysis board uses `computePoolSize()` (`workerPoolState.ts:471`), which can be 2 on mobile (L-4).
- Gap-fix tests are mutation-checked by reverting the fix.

### Integration Points
- The root split applies to every `mctsSearch` caller (bot + analysis) at round 1; the guard only to `useBotGame` (stop rule); the underfill fix to every caller.
- Grade cache is keyed `fen|depth` (L-3): sub-grades merge before the single cache write.

</code_context>

<specifics>
## Specific Ideas

- Step 0 is a real idle-box re-measurement: stop the local `remote_eval_worker` first. The 2026-09-28 numbers were taken at load 14-21.
- Multi-hour sweeps run from the orchestrator, not inside a backgrounded executor subagent (Phase 197 lesson); wrap them in the resume-on-crash supervisor (wasm OOB crash ~5-6 h in on blend>0 presets).
- CHANGELOG `[Unreleased]`: faster bot moves / analysis search (only for items that ship).

</specifics>

<deferred>
## Deferred Ideas

- **Continuous dispatch** → Phase 227 (with D-05..D-07 and the WebGPU prerequisite, D-02).
- **Cross-FEN Maia batching**: only with WebGPU numbers in hand (227 decides).
- Still out of scope per roadmap: Rust/WASM or chessops port, multithreaded SF, fp32/int8 Maia, Maia WDL leaf values, depth ladder / MultiPV tuning, guarding the near-tie stop or the deadline cut, server-side Maia (SEED-172).

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`: keyword-match noise, unrelated to engine throughput (same set Phase 225 reviewed).

</deferred>

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Context gathered: 2026-09-28*
