---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
verified: 2026-10-03T13:10:00Z
status: passed
score: 17/17 must-haves verified (1 via override)
covered_files:
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-01-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-01-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-02-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-02-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-03-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-03-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-04-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-04-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-05-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-05-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-06-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-06-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-07-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-07-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-08-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-08-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-09-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-09-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-10-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-10-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-11-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-11-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-12-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-12-SUMMARY.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-13-PLAN.md
  - .planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-13-SUMMARY.md
  - CHANGELOG.md
  - bin/preset-supervisor.sh
  - docs/flawchess-engine-explained-2026-07-06.md
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/useFlawChessEngine.ts
  - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/searchTestProviders.ts
  - frontend/src/lib/engine/__tests__/workerPool.test.ts
  - frontend/src/lib/engine/botBudget.ts
  - frontend/src/lib/engine/deadlineSearch.ts
  - frontend/src/lib/engine/gradingLadder.ts
  - frontend/src/lib/engine/mctsSearch.ts
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/engine/workerPoolState.ts
  - frontend/src/vitest.setup.ts
  - scripts/calibration-harness.mjs
  - scripts/engine-dispatch-stop-rule.mjs
  - scripts/engine-grading-depth-ab.mjs
  - scripts/engine-move-quality.mjs
  - scripts/engine-search-trace.mjs
  - scripts/engine-speed-probe.mjs
  - scripts/engine_dispatch_227_verdict.py
  - scripts/engine_interleave_227.py
  - scripts/lib/calibration-determinism.check.mjs
  - scripts/lib/calibration-ledger-schema.check.mjs
  - scripts/lib/calibration-providers.mjs
  - scripts/lib/dispatch-mode.check.mjs
  - scripts/lib/dispatch-mode.mjs
  - scripts/lib/maia-instrumentation.check.mjs
  - scripts/lib/maia-worker-thread.check.mjs
  - scripts/lib/maia-worker-thread.mjs
  - scripts/lib/node-engine-providers.mjs
  - scripts/lib/stockfish-pool.check.mjs
  - scripts/lib/stockfish-pool.mjs
  - tests/scripts/test_engine_dispatch_227_verdict.py
  - tests/scripts/test_engine_interleave_227.py
covered_digest: "v2:sha256:c4b20a051458537ccfc2df7cad2d00b104aa74bedff358885daa6fd3357758ad"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "Round-mode results with the new harness tooling (worker-thread Maia) stay byte-identical to Phase 226's committed a21s TSVs (D-18, 227-08 truth 1)"
    reason: "Off-thread Maia changes Stockfish hash warmth timing, so warm-hash round mode differs from a21s on 2/60 (stop off) and 5/60 (stop on) rows. Debugged to root cause (227-08-TRIPWIRE-DEBUG.md); at --hash clear the worker and main-thread sessions are identical (re-run here: TRIPWIRE off diffs=0, on diffs=0). Owner direction 2026-10-02: bit-identical round-mode results are not required with concurrent Maia inference, very similar is good enough. Recorded in accept-rule.md (section 1 item 4, line 288) before any gate data. In-app round mode is still bit-identical (pre-extraction goldens pass)."
    accepted_by: "owner (Adrian Imfeld)"
    accepted_at: "2026-10-02T12:00:00Z"
---

# Phase 227: Browser Engine Continuous Dispatch Against a Relaxed Determinism Target — Verification Report

**Phase Goal:** Overlap Maia and Stockfish by removing the round `Promise.all` barrier in `mctsSearch` (asynchronous tree search with virtual loss / pending marks, SEED-171 item 5), against a relaxed determinism target decided in Phase 226's discuss-phase (226-CONTEXT D-05..D-07). Size it on the idle profile Phase 226 leaves behind.
**Verified:** 2026-10-03
**Status:** passed
**Re-verification:** No, initial verification

Must-haves derive from 227-CONTEXT D-00..D-20 plus the 13 plans' frontmatter (no REQ-IDs; all plans declare `requirements: []`; `.planning/REQUIREMENTS.md` does not exist, so there is nothing to cross-reference and no orphaned IDs).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Continuous mode removes the round barrier: fill, await one wake, drain in arrival order; Maia and SF overlap (SEED-171 item 5, D-08 apply order) | VERIFIED | `mctsSearch.ts:957-983` `runContinuousLoop` (no `Promise.all`), `fillContinuous` 830-865, `drainSettled` 884-895; dispatcher `mctsSearch.ts:998`. Tests `arrival order: ... settles first is applied first` and `fill: a slot freed ... is refilled while the other is still in flight` pass. Measured: all 4 Node configs 14-19% faster, interleaved. |
| 2 | Hard pending exclusion; no leaf dispatched twice; block flags scoped per fill pass, cleared in `finally`; virtual loss only on a D-01/D-03 failure (D-08) | VERIFIED | `leaf.isPending = true` at 851; `finally` clears `blockedThisPass` 862-864. Tests `pending exclusion` and `fill: a block set in one fill is cleared before the next` pass. `virtual_loss_trigger: false` reproduced; no VL code exists (correct per D-08). |
| 3 | No result applied after abort or early stop; inner AbortController cancels in-flight grades on stop/abort/rejection/exit; no drain (D-09, L-2) | VERIFIED | `drainSettled` 891 skip; `finally` aborts `dispatchController` 980-981. Independent mutation: removing the 891 skip fails 4 tests; removing the `finally` abort fails 3 tests (file restored, git clean). |
| 4 | Dispatch only while `nodesEvaluated + inFlight < maxNodes`; never overshoots; inFlight 0 at exhaustion (D-10) | VERIFIED | `mctsSearch.ts:840-844`. Independent mutation: dropping the budget term fails 24 of 73 continuous tests. MQ data: continuous `nodes_evaluated` mean 50 at max 50, never above. |
| 5 | c = 1 continuous is byte-identical to round; round mode (omitted/`'round'`) unchanged from A21S (D-11) | VERIFIED | Tests `c=1: continuous equals round and the pre-extraction golden under different jitter` (7 fixtures), `round mode matches the pre-extraction capture`, `omitted, explicit 'round' and the pre-extraction golden agree at c=4`. Engine suite: 34 files, 777 tests pass. |
| 6 | Harness Maia runs in `worker_threads` (D-18); round-mode content parity | PASSED (override) | `scripts/lib/maia-worker-thread.mjs` exists, wired via `createMaiaSession`. Clear-hash parity re-run: `TRIPWIRE off diffs=0 / on diffs=0 / PASS`. Warm-hash vs a21s differs 2/60 and 5/60 rows; owner direction recorded in accept rule before data (see override). |
| 7 | App SF queue tie-break is FIFO (D-19) | VERIFIED | `workerPoolState.ts:450-470` strict comparisons; tests `serves equal-priority, equal-depth requests FIFO` and `FIFO: an earlier request is never overtaken` pass. |
| 8 | Design doc dispositions X-1..X-12, Y-1..Y-14, N-1..N-4; two independent reviewers SOUND before any `mctsSearch.ts` edit (D-12, L-7) | VERIFIED | `design.md` has 30 disposition rows; `REVIEW-A/B: SOUND` (rounds 2 and 3) lines 1151-1154. Commit order: SOUND `7bb93b943` 14:06, accept rule `7fb704a65` 14:12, first `mctsSearch.ts` commit `58540ce43` 14:26. |
| 9 | Accept rule pre-registered before data, never edited; k = 1.5, margin 0.02520619 (D-01, pre-registration) | VERIFIED | `accept-rule.md` has exactly one commit (`7fb704a65`, 14:12); first gate-data commit `7090c3ce8` at 17:42. Later changes are separate docs (`override-2026-10-02-review-docs.md`, docs-only scope). `test_accept_rule_matches_twin_constants` passes. |
| 10 | D-01 one-sided non-inferiority and D-03 net regressions pass on the bot path, both stop cells, R = 5, warm hash, d20 (D-01, D-02, D-03) | VERIFIED | Re-ran `engine_dispatch_227_verdict.py gates`: rc 0, output byte-identical to committed `verdict.json` (timestamps aside). D = -0.00452 / -0.00117 vs margin 0.02521; net 0.0 / 0.4 vs allowance 1. TSVs carry 300 rows per arm per cell, `dispatch_mode` matching arm, repeats 1..5, `hash_mode=warm`, `maia_fifo=true`, depth 20. |
| 11 | D-04/D-17 ship bar on interleaved, probe-normalized raw wall; pool-2 no regression | VERIFIED | Reproduced: stop-p4 gain 0.1905 (bar 0.15), t400-p4 ratio 0.858, t50-p2 0.819, t400-p2 0.816; per-round ratios within 1.5 points. `THROUGHPUT-BAR passed=true`, POOL2 both pass. |
| 12 | D-07 WebGPU point: continuous not slower than round on the WebGPU machine | VERIFIED | `webgpu/continuous-leg.json`: 36 rows, all backend `webgpu`, 18 round->round and 18 continuous->continuous observed. Median ratio 0.676 vs 1.03. |
| 13 | D-14/D-15 harness parity and calibration: harness default = app constant; A0/A1 same session; refit only on powered shift | VERIFIED | `dispatch-mode.mjs:24,83-85` returns `FLAWCHESS_DISPATCH_MODE`; calibration harness/supervisor wired. Ledgers: 1000 rows a0=round, 1000 rows a1=continuous. Powered verdict valid, no real shift, `refit_if_shipped: no-refit`. |
| 14 | D-13 ship: flag flipped to `'continuous'`, both callers use it, rollback is a one-line flip | VERIFIED | `botBudget.ts:77` `= 'continuous'`; `useBotGame.ts:131` and `useFlawChessEngine.ts:383` pass `dispatchMode: FLAWCHESS_DISPATCH_MODE`. `owner-decision.md` says ship. Probe: `DISPATCH-PROBE round -> round`, `continuous -> continuous`. `mctsSearch.ts` unchanged since measured commit `f3d9ea2fe`, so the shipped loop is the measured loop. |
| 15 | D-16 CHANGELOG `[Unreleased]` bullet and engine doc describe continuous dispatch | VERIFIED | CHANGELOG line 12 ("Bot moves are about 19% faster again..."); engine doc line 158 "Several expansions at once" rewritten (arrival order, cancellation, non-reproducibility). |
| 16 | D-06 dev bench tool removed, never shipped, knip clean | VERIFIED | `frontend/src/dev/` absent; no `engine-bench` in `App.tsx`; `npm run knip` clean. |
| 17 | Sized on the idle profile 226 left behind (measured inputs, X-2 model confirmed or replaced) | VERIFIED | `design.md` section 4.1-4.5 (Node P/G from a21s TSVs, browser P from the 227-08 legs); report compares model vs measured (53-66% of ideal ceiling realized). |

**Score:** 17/17 truths verified (1 via override, 0 present-but-behavior-unverified)

Note on the goal wording "virtual loss / pending marks": the shipped design is hard pending exclusion, the infinite-penalty limit of virtual loss (D-08). The virtual-loss arm was conditional on a D-01/D-03 failure, which did not happen, so its absence is correct.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/lib/engine/mctsSearch.ts` | `runRoundLoop`, `runContinuousLoop`, `fillContinuous`, `applyAndReport` | VERIFIED | Substantive, dispatched on `budget.dispatchMode` |
| `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts` | 73 invariant tests | VERIFIED | Pass; 3 independent mutations caught |
| `frontend/src/lib/engine/types.ts` | `DispatchMode`, `SearchBudget.dispatchMode?` | VERIFIED | lines 100, 125 |
| `frontend/src/lib/engine/botBudget.ts` | `FLAWCHESS_DISPATCH_MODE` | VERIFIED | `'continuous'` |
| `frontend/src/lib/engine/workerPoolState.ts` | FIFO tie-break | VERIFIED | D-19 |
| `scripts/lib/maia-worker-thread.mjs`, `stockfish-pool.mjs`, `dispatch-mode.mjs` | harness tooling | VERIFIED | wired into all gate scripts and the calibration harness |
| `scripts/engine_dispatch_227_verdict.py` + tests | verdict twin | VERIFIED | 132 tests (twin + interleave) pass; verdict reproduces |
| `scripts/engine_interleave_227.py`, `engine-speed-probe.mjs` | interleave driver | VERIFIED | manifest + 24 steps committed |
| `reports/continuous-dispatch-227/{design,accept-rule,report,owner-decision}.md`, `verdict.json` | contract, evidence, decision | VERIFIED | |
| `reports/data/continuous-dispatch-227/**`, `reports/data/sweep-227-*` | gate data | VERIFIED | layout matches accept rule |
| `227-UAT.md` | smoke + real-phone line | VERIFIED | `smoke: pass`, `real-phone: deferred` |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| `useBotGame.ts` / `useFlawChessEngine.ts` | `botBudget.ts` | `dispatchMode: FLAWCHESS_DISPATCH_MODE` | WIRED |
| `mctsSearch` | `runContinuousLoop` | `budget.dispatchMode === 'continuous'` | WIRED |
| `runContinuousLoop` | pool / Maia queue abort | `dispatchController.signal` passed to every `dispatchExpansion` | WIRED |
| `dispatch-mode.mjs defaultDispatchMode` | `botBudget.ts` | import | WIRED (app == harness) |
| gate scripts, `calibration-harness.mjs`, `preset-supervisor.sh` | `dispatch-mode.mjs` | `--dispatch-mode`, `assertDispatchModeLive`, `PRESET_SUPERVISOR_DISPATCH_MODE` | WIRED |
| `accept-rule.md` constants | twin constants | `test_accept_rule_matches_twin_constants` | WIRED |
| `verdict.json` | flip commit | owner-decision ship + `no-refit` | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|---|---|---|---|---|
| `verdict.json` | all criteria | committed TSVs/manifest/ledgers via twin `gates` | Yes, reproduced bit-for-bit | FLOWING |
| `report.md` criteria table | numbers | `verdict.json` | Yes, matches | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Verdict reproduces from committed data | `uv run python scripts/engine_dispatch_227_verdict.py gates --data-dir reports/data/continuous-dispatch-227 --out-json <tmp>` | rc 0, `GATES mechanical=ship-eligible`, JSON identical to committed | PASS |
| Engine unit suite | `npx vitest run src/lib/engine` | 34 files, 777 tests pass | PASS |
| Twin + interleave tests | `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py tests/scripts/test_engine_interleave_227.py` | 132 passed | PASS |
| Dispatch flag is a code path, not a label | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/dispatch-mode.check.mjs --mode {round,continuous}` | `round -> round`, `continuous -> continuous`, rc 0 | PASS |
| Clear-hash D-18 parity | `engine_dispatch_227_verdict.py tripwire --mq-dir .../parity-clear/worker --baseline-dir .../parity-clear/main` | 0/60 diffs both cells | PASS |
| Mutation: drop abort/early-stop skip in `drainSettled` | temporary edit + continuous test file | 4 tests fail | PASS (guarded) |
| Mutation: drop D-10 budget term in `fillContinuous` | temporary edit | 24 tests fail | PASS (guarded) |
| Mutation: drop `dispatchController.abort()` in `finally` | temporary edit | 3 tests fail | PASS (guarded) |
| knip | `npm run knip` | clean | PASS |

All mutations were reverted by copying back the saved original; `git status` on `mctsSearch.ts` is clean.

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared by this phase. The phase's runnable checks (dispatch-mode probe, tripwire, verdict twin) were run above.

### Requirements Coverage

Phase 227 has no REQ-IDs; all 13 plans declare `requirements: []`, and `.planning/REQUIREMENTS.md` does not exist. Nothing to account for, no orphans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (all changed impl files) | - | TBD/FIXME/XXX | none found | - |
| `frontend/src/lib/engine/workerPoolState.ts` | 434-437 | Stale comment: "Phase 198 ... is the consumer that will populate real priority values once in-flight expansions can exceed free worker slots" (Phase 227 shipped continuous dispatch and still activates no priorities) | Info | Comment only |

### Informational Observations (non-blocking)

- The report-only analysis-400 MQ cell shows D = 0.00000 with 0 differing bot and analysis picks between arms (60 positions, identical mean nodes 383.6). The rows are stamped `dispatch_mode=continuous`, the scripts assert the mode live before running, and continuous wall is 7% lower, so this reads as convergence at 400 nodes rather than a mislabeled arm. It is report-only (D-20) and cannot affect the verdict.
- The stop-off cell reports 0 vs 0 McNemar discordant pairs while the mean abs des is 0.0045. That is consistent with one position's pick flipping on a minority of repeats (fractional, below the McNemar majority threshold). Report-only.
- Real-phone UAT is owner-deferred and report-only by locked decision 226 D-04 (also stated in 227-UAT.md). Per that decision and the caller's instruction it is not a gating human-verification item.

### Human Verification Required

None that gates the phase. The browser smoke (analysis board + 7-move bot game, console clean) was run and recorded in 227-UAT.md. The owner's WebGPU hardware legs are committed and judged. The real-phone check stays owner-deferred and report-only (226 D-04).

### Gaps Summary

None. The continuous loop exists, is substantive and wired into both app callers and every harness script through one constant. Its load-bearing invariants (abort/stop zero-apply, budget bound, inner cancellation) are guarded by tests that I confirmed fail when the guards are removed. The pre-registered gate reproduces from committed data to the same `ship-eligible` / `no-refit` verdict. The accept rule predates all gate data and was never edited. The code shipped is the code measured (`mctsSearch.ts` unchanged since `f3d9ea2fe`). The one deviation, warm-hash harness round mode not byte-identical to 226's a21s after Maia moved off-thread, was debugged to root cause, replaced by an exact clear-hash parity check, and accepted by the owner before any data. It is recorded as an override.

---

_Verified: 2026-10-03T13:10:00Z_
_Verifier: Claude (gsd-verifier)_
