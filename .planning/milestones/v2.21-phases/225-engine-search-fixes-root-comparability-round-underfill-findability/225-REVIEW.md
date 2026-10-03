---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
reviewed: 2026-09-28T02:24:21Z
depth: deep
files_reviewed: 12
files_reviewed_list:
  - frontend/src/lib/engine/findability.ts
  - frontend/src/lib/engine/treeCommon.ts
  - frontend/src/lib/engine/__tests__/findability.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
  - frontend/src/lib/engine/__tests__/selectBotMove.test.ts
  - scripts/engine-dispatch-stop-rule.mjs
  - scripts/engine-move-quality.mjs
  - scripts/engine_search_fixes_allowance.py
  - scripts/engine_search_fixes_verdict.py
  - tests/scripts/test_engine_search_fixes_allowance.py
  - tests/scripts/test_engine_search_fixes_verdict.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 225: Code Review Report

**Reviewed:** 2026-09-28T02:24:21Z
**Depth:** deep
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Scope: `git diff $(git merge-base main HEAD) HEAD -- frontend/src scripts tests` on the
`gsd/phase-225-engine-search-fixes-root-comparability-round-underfill-findability` branch.

Per the phase's own report (`reports/engine-search-fixes-225/report.md`) and D-14, items 1
(root-comparability guard) and 2 (round-underfill fix) were implemented, gated, held (MQ-2
confirmed regression flip + a calibration decision-branch failure), and reverted from the phase
branch. I confirmed this by diffing directly and by grepping for residue: `frontend/src/lib/engine/mctsSearch.ts`
has an **empty diff** against `main`, and `isBlocked`/`blockedThisRound`/`rootGuardBoostAllowance`/
`ROOT_GUARD_BOOST_ALLOWANCE` appear **nowhere** under `frontend/src`, `scripts`, or `tests` (only
as historical-context prose inside `scripts/engine_search_fixes_allowance.py`'s docstring, which is
expected — that script computed the D-02 design input and is legitimately kept). The net diff is
exactly item 3 (`findability.ts` + `treeCommon.ts` + their four test files) plus the measurement
tooling (`scripts/engine-dispatch-stop-rule.mjs` extensions, `scripts/engine-move-quality.mjs`,
`scripts/engine_search_fixes_allowance.py`, `scripts/engine_search_fixes_verdict.py`, and their
tests) — matching the task's expectation and the plan's own D-2 revert-verification check.

**Item 3 correctness (primary focus):** I hand-verified the `rankScore`/`rankFallbackValue` math
against the invariants in `findability.ts`'s header (D-10a/D-10b):
- `rankScore <= value` always holds (the `min(value, fallbackValue)` clamp structurally forces
  this — the convex combination of `value` and something `<= value` can never exceed `value`).
- The `pRef <= 0` guard returns `value` unmodified, matching the pre-existing degenerate-case
  convention (never divides by zero, never produces `NaN`).
- `rankFallbackValue`'s `totalPrior <= 0` guard returns `0` *before* delegating to
  `backupExpectation` (whose own `0.5` degenerate default is therefore unreachable from this call
  site) — this is exactly the documented D-10b-amended behavior: a `0` fallback reduces the whole
  formula to the pre-Phase-225 `f * value`, never introducing a `NaN` or a spurious `0.5` pull.
- `buildRankedLines` computes `fallbackValue` once per call, over the *same* `child.uci !== null`
  filtered population the scoring loop iterates — verified by re-reading both loops side by side
  (`treeCommon.ts:432-450`).
- I re-derived the hand-computed numeric comments in the rewritten `findability.test.ts`,
  `mctsSearch.test.ts`, and `fallbackExpectimax.test.ts` fixtures (both D-03 regression cases and
  both T=1/T=2 composition cases) by hand; the arithmetic in the comments matches the formula, and
  I additionally ran all four affected vitest files — **87/87 pass**.
- I ran both new Python test suites — **34/34 pass** — and `ruff`/`ty` clean on the touched Python
  files.

No BLOCKER-level defects found. The findings below are quality/robustness gaps in the
newly-added measurement tooling (which decides ship/hold for a future re-run of items 1/2, so its
correctness matters, but a defect there cannot corrupt shipped product code — item 3 is the only
product-code change and it is sound).

## Warnings

### WR-01: `evaluate_throughput` divides by a possibly-zero sum with no guard, inconsistent with its own per-position guard

**File:** `scripts/engine_search_fixes_verdict.py:270-271`
**Issue:** `ratio = a2_wall_ms / a0_wall_ms` and `grade_cpu_ratio = ... if a0_grade_cpu_ms > 0 else
0.0` are computed right next to each other, but only the second is zero-guarded. If every A0
ladder row's `wall_ms` sums to `0` (corrupted/mocked data, or a future refactor that starts
recording `wall_ms` as an integer that can legitimately be `0`), `ratio = a2_wall_ms / a0_wall_ms`
raises an unhandled `ZeroDivisionError` that isn't caught by any `try/except ValueError` in
`run_gates` (only `ValueError` is caught there), crashing the whole `gates` invocation instead of
recording a clean `missing` entry. The per-position loop three lines below (`pos_ratio = ... if
a0_pos_wall > 0 else 0.0`) already establishes the right pattern for this exact quantity — the
aggregate-level computation just didn't copy it. Not observed in the actual gate run (real wall
times are always > 0), and no test exercises this path.
**Fix:**
```python
ratio = a2_wall_ms / a0_wall_ms if a0_wall_ms > 0 else 0.0
```
Also raise `ValueError` explicitly if `a0_wall_ms <= 0` (rather than silently returning `0.0`,
which would read as "A2 got infinitely faster") if that is truly an unreachable/corrupted-data
condition — either way, replace the raw division with something that can't raise
`ZeroDivisionError` out of `run_gates`'s `try/except ValueError` net.

### WR-02: `engine-move-quality.mjs`'s per-row grading errors leave spawned engines running

**File:** `scripts/engine-move-quality.mjs:404-425` (main loop), `scripts/engine-move-quality.mjs:508-511` (module entry point)
**Issue:** `gradePair` throws (e.g. `pick is null` when `argmaxLine`/`rankedLines[0]` return
`null`, or a missing grade) and is only caught to re-wrap the message with the row id
(`throw new Error(...)`) — it is never caught again. That rethrow propagates out of the `for`
loop, out of `main()`, and the top-level `const code = await main(); process.exit(code)` has no
`try/catch` either, so the process dies via an unhandled promise rejection. `pool.quitAll()` and
`gradeEngine.terminate()` (the cleanup at the end of `main()`) are skipped in this path, leaking
the Stockfish pool's child processes and the independent grading engine's child process. This is
an offline research tool run by a human operator, so the blast radius is a few orphaned Stockfish
processes rather than a production incident, but it's a real resource leak on every error path in
a script whose whole job is to run unattended for potentially all 12 fixture rows.
**Fix:** Wrap the per-row body (or at least the `gradePair` calls) in a `try/finally` that runs
`pool.quitAll()`/`gradeEngine.terminate()` before rethrowing, or wrap the entire measurement loop
in `main()` in `try { ... } finally { pool.quitAll(); gradeEngine.terminate(); }`.

### WR-03: `selectBotMove.test.ts`'s D-10d test proves order-invariance under permutation, not the literal "old vs new rankScore" comparison the context decisions specify

**File:** `frontend/src/lib/engine/__tests__/selectBotMove.test.ts:437-496`
**Issue:** D-10d (`225-CONTEXT.md`) says: "same search snapshot, old vs new rankScore,
`selectBotMove` picks the identical move for a fixed rng." The implemented test instead builds
four permutations of the same `rankedLines` array (identity/reversed/rotated/"findability-like")
and asserts `selectBotMove` picks the same move across all four, at `blend=1`, `blend=0.5`, and
with a style applied. This is a legitimate and arguably stronger proof of the same underlying
claim (bot play is `rankedLines`-order-independent, so item 3's sort-order-only change cannot
affect it) — I don't consider it a defect — but it is a silent deviation from the literal decision
text and the Plan 225-06 SUMMARY should be checked for whether this substitution was called out
explicitly as a deviation. Flagging so the phase's decision-traceability isn't quietly broken.
**Fix:** None required for correctness. If not already noted, add a one-line comment or SUMMARY
entry stating the permutation-based proof was substituted for the literal old-vs-new-rankScore
comparison and why (it's the more general claim).

## Info

### IN-01: Dead module-level constant in `engine_search_fixes_allowance.py`

**File:** `scripts/engine_search_fixes_allowance.py:41`
**Issue:** `_REPO_ROOT = Path(__file__).resolve().parent.parent` is assigned but never
referenced anywhere else in the file (confirmed via grep). The sibling file
`scripts/engine_search_fixes_verdict.py` defines the identical constant and *does* use it (for
`DEFAULT_DATA_DIR`/`DEFAULT_VERDICT_JSON`) — this file has no such defaults (both CLI args in
`engine_search_fixes_allowance.py` are `required=True` with no path defaults), so the constant is
pure copy-paste residue. Ruff doesn't flag it (F841 only covers local variables, not module-level
assignments).
**Fix:** Delete the line.

### IN-02: `engine-dispatch-stop-rule.mjs`'s D-04 exposure metric can count a closed (terminal) root child as "exposed" — documented, but worth a one-line pointer

**File:** `scripts/engine-dispatch-stop-rule.mjs:343-350`
**Issue:** The tracer's own docstring already calls this out ("a terminal root child ... can be
counted as 'unvisited and in-window' here even though the real engine would never need to guard
it — a known false positive, report-only, never a gate"), so this is not a defect — the report-only
D-04 exposure number in the accept rule and phase report should be read as an upper bound, not an
exact count. Recording as INFO only so a future reader of `reports/engine-search-fixes-225/report.md`'s
"18% exposure" figure (cited in the 225-08 SUMMARY) knows it's a conservative overcount, not a
precise measurement, without having to find this comment themselves.
**Fix:** None required — already correctly documented in the source. No action needed beyond this
pointer.

---

_Reviewed: 2026-09-28T02:24:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
