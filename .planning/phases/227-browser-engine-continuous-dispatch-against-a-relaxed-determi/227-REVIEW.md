---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
reviewed: 2026-10-03T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - frontend/src/lib/engine/mctsSearch.ts
  - frontend/src/lib/engine/deadlineSearch.ts
  - frontend/src/lib/engine/botBudget.ts
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/engine/workerPoolState.ts
  - frontend/src/lib/engine/gradingLadder.ts
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/useFlawChessEngine.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts
  - frontend/src/lib/engine/__tests__/searchTestProviders.ts
  - frontend/src/lib/engine/__tests__/workerPool.test.ts
  - bin/preset-supervisor.sh
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
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 227: Code Review Report

**Reviewed:** 2026-10-03
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

I focused on the shipped continuous dispatch loop in `frontend/src/lib/engine/mctsSearch.ts` (`fillContinuous`, `drainSettled`, `runContinuousLoop`), on what it touches (`deadlineSearch.ts`, the `workerPoolState.ts` FIFO tie-break, the hook budgets), and on the abort/idle plumbing in the Node harness (`stockfish-pool.mjs` `withEngine`/`whenIdle`, `calibration-providers.mjs` `maiaFifoPolicy`/`whenMaiaIdle`, the Maia worker-thread session).

I traced every invariant the caller asked about against the code. I found no defect in the shipped frontend loop:

- **No apply after abort or stop.** `drainSettled` (mctsSearch.ts:902-913) checks `signal.aborted || st.earlyStop` right before `applyAndReport`, with no `await` in between. An abort raised inside `onSnapshot` (the deadline cut) or an early stop set mid-drain therefore drops every result queued behind it. The loop-top check (line 967) exits.
- **Budget.** The fill guard `nodesEvaluated + inFlight + dispatched < maxNodes` (line 858) and `inFlight` counting until drain (line 975) keep `nodesEvaluated <= maxNodes`. A degenerate (empty-candidate) result is drained and decrements `inFlight` without counting a node, which is correct.
- **Pending exclusion and closure.** A pending leaf is never closed, so `propagateClosure` cannot close an ancestor of in-flight work. The `path` captured at dispatch stays valid because the tree only grows. Block flags are cleared in the `finally` of every fill pass (line 878).
- **Missing wakeup.** The `settled.length === 0` check and the `wake = resolve` assignment run in one synchronous stretch (lines 970-973). A settlement or abort that lands while `wake` is null is caught by the queue check or by the `!signal.aborted && !st.earlyStop` guard.
- **Listener cleanup and rejections.** The outer listener is `{ once: true }` and removed in the `finally` (line 978). A rejection is captured as a value (line 874) and rethrown only while the search is live (line 909). After the loop exits, the inner `dispatchController.abort()` cancels the siblings.
- **Stale continuations after return.** A policy that settles after the loop returned calls `grade` with an already-aborted signal. The pool (`workerPoolDispatch.ts:211`, `:377`) and `maiaQueue.policy` (`maiaQueue.ts:301`) both short-circuit an already-aborted signal, and an aborted Maia request is never written to the policy cache.

All findings below are in measurement tooling or stale documentation. None affects shipped behavior.

## Warnings

### WR-01: Report-only MQ cell crashes the whole verdict on an empty arm instead of reporting `unreadable`

**File:** `scripts/engine_dispatch_227_verdict.py:663-688` (called from `:691-708`)
**Issue:** `run_mq_gate` describes the report-only cells as "lenient: never raise", and `_report_only_cell` turns errors into an `unreadable` status. But it only catches `ValueError`, and `evaluate_mq_report_only` can raise two other exception types:
- When both arms' TSVs have zero data rows (header only), `set.intersection(*())` raises `TypeError: unbound method set.intersection() needs an argument`.
- When only the continuous arm is empty, the intersection keeps the round ids and `/ len(cont_by)` raises `ZeroDivisionError`.

I confirmed both:

```
evaluate_mq_report_only([], [])                -> TypeError
evaluate_mq_report_only([<one round row>], []) -> ZeroDivisionError
```

Neither is a `ValueError`, so a malformed optional Clear-Hash or analysis-400 directory aborts `run_gates` with a traceback. It does not surface as a report-only `unreadable` cell, and the judged verdict is not emitted either.
**Fix:**
```python
def evaluate_mq_report_only(round_rows, cont_rows):
    round_by = _group_by_repeat(round_rows, "round")
    cont_by = _group_by_repeat(cont_rows, "continuous")
    if not round_by or not cont_by:
        raise IncompleteDataError("report-only cell: an arm has no rows")
    shared = set.intersection(*(set(rows) for rows in (*round_by.values(), *cont_by.values())))
    ...
```
Add a regression test for both shapes in `tests/scripts/test_engine_dispatch_227_verdict.py`.

## Info

### IN-01: Hook comments still say the dispatch mode "stays 'round'" after the ship flip

**File:** `frontend/src/hooks/useBotGame.ts:129-130`, `frontend/src/hooks/useFlawChessEngine.ts:381-382`
**Issue:** Both comments read "stays 'round' until the owner's ship decision". `botBudget.ts:77` now ships `FLAWCHESS_DISPATCH_MODE = 'continuous'`, so both app callers run the continuous loop and the comments describe the opposite of current behavior.
**Fix:** Reword to "the shared dispatch-mode constant (`'continuous'` since the Phase 227 ship decision; rollback = flip it to `'round'`)".

### IN-02: `FLAWCHESS_BOT_CONCURRENCY` doc still claims exact app == harness determinism

**File:** `frontend/src/lib/engine/botBudget.ts:63`
**Issue:** "bot play uses one fixed constant so app == harness determinism holds exactly". With continuous dispatch shipped at c=4, the module header (`mctsSearch.ts:68-79`) states the tree is timing-dependent and judged statistically, so this claim no longer holds.
**Fix:** Qualify it: "...so app and harness run the same budget (bit-identical only in round mode; continuous mode is judged statistically, Phase 227 D-11)".

### IN-03: Harness headers still say continuous "exits 3 until Plan 227-10"

**File:** `scripts/lib/dispatch-mode.mjs:19`, `scripts/lib/dispatch-mode.check.mjs:8-10`, `scripts/engine-dispatch-stop-rule.mjs` (module header, `--dispatch-mode` paragraph), `scripts/engine-move-quality.mjs:14-19`
**Issue:** These headers say requesting `continuous` exits 3 / prints CONTINUOUS-NOT-IMPLEMENTED until the loop exists. The loop has landed and ships by default, so the notes mislead an operator reading a probe failure.
**Fix:** Replace with "exit 3 if continuous is requested but the probe observes the round loop (a regression guard)".

### IN-04: `mq_allowance` docstring says "signed net" but the code takes the absolute value; `math.ceil` is a no-op

**File:** `scripts/engine_dispatch_227_verdict.py:402-418`
**Issue:** The docstring says "A signed net, so two repeats that swap one regression for another do not widen the allowance". The code computes `abs(gained - lost)`, so a net improvement between repeats widens the allowance as much as a net regression. That matches the `|N_rs|` formula in the same docstring, so the prose and the formula disagree. `math.ceil(worst)` on an `int` does nothing.
**Fix:** Make the prose match the formula, e.g. "the absolute net per pair (offsetting swaps cancel)", and drop the `ceil` or note that it is kept for parity with the D-03 formula.

---

_Reviewed: 2026-10-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
