---
phase: 236-train-phone-grade-instant-verdict
reviewed: 2026-10-08T22:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - CHANGELOG.md
  - alembic/versions/20261008_120000_d3a7f1c9e246_drill_solves_phone_grade.py
  - app/models/drill_solve.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/train_pool.py
  - frontend/src/api/client.ts
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/__tests__/trainBubbleState.test.ts
  - frontend/src/components/train/trainBubbleState.ts
  - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
  - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
  - frontend/src/hooks/trainGradingSupport.ts
  - frontend/src/hooks/useTrainGradingEngine.ts
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - frontend/src/lib/__tests__/trainPhoneGrade.test.ts
  - frontend/src/lib/__tests__/trainRecheck.test.ts
  - frontend/src/lib/trainPhoneGrade.ts
  - frontend/src/lib/trainRecheck.ts
  - frontend/src/types/train.ts
  - tests/repositories/test_train_repository.py
  - tests/routers/test_train.py
  - tests/schemas/test_train_phone_grade_schema.py
  - tests/services/test_train_pool.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 236: Code Review Report

**Reviewed:** 2026-10-08T22:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Reviewed the diff `4c0c4997a..HEAD` for the Phase 236 change set: the `drill_solves.phone_grade` JSONB column and migration, the `PhoneGrade` / `ReviewRequest` / `ServerGradedMove` schemas, the shared `server_graded_moves_for` derivation (composition and solve path now use one function), the write-once coalesce on the review route, and the frontend instant-verdict path (`solveInstantly` / `gradeInBackground`, the `gradingSettledRef` queueing, pending line cards, late phone-grade flush).

The backend is sound. The refactor of `_classify_sr_solve` / `_classify_herring_solve` onto `server_graded_moves_for` preserves the prior graded-set semantics (same source gating, same mover derivation, runner-up still appended after the vetted entries). The migration chains correctly off the previous head, the claim UPDATE omits the column when absent so it stays SQL NULL, `merge_solve_telemetry` enforces write-once atomically without turning a second flush into a 404, and `_resolve_grade` is untouched, so `phone_grade` is audit-only as D-02 requires. I verified with a local run: ruff, ty on `app/`, the nesting-depth gate, the 474 backend tests in the four touched test modules, and 794 frontend tests across the touched train suites all pass.

No security or data-loss defects were found. The two warnings are both on the frontend instant path and are cases where the shipped behavior contradicts or undermines a locked decision or the purpose of the audit column. No critical issues.

## Warnings

### WR-01: A grading-engine Worker error after the verdict hides the verdict bubble and its Next button (violates D-15)

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:2044-2056` (trigger at `frontend/src/hooks/useTrainGradingEngine.ts:558-560`)
**Issue:** D-15 states there is "no engine-error state blocking the reveal" on the instant path. But the verdict bubble, which holds the Solution/Analyze/Next row (`verdictActions`), is rendered only in the third arm of `engineFailed ? <error + Retry> : !isReady ? <Loading engine> : <TrainBotBubble ...>`. `engineFailed = hasError || engineTimedOut`, and `worker.onerror` sets `hasError = true` for any Worker failure, not only load failures. Before this phase the grading Worker was effectively idle once the verdict showed. Now, on roughly 17% of solves (the server-graded population), a 1.5 s to 3 s search is guaranteed to be running after the verdict is on screen. If the Worker errors then (for example a wasm out-of-memory crash on a constrained phone, a known failure class for this project), `gradeInBackground`'s rejection handler correctly degrades the card to `failed`, but the screen also swaps the verdict bubble for "Failed to load the grading engine" plus a Retry that calls `restartEngine()` and re-runs `startGrading` for an already-solved puzzle. The user loses the Next button on a puzzle whose verdict is already server-final. The existing tests only cover the background promise rejecting, not `hasError` flipping after the verdict.
**Fix:** Do not let the engine-error branch displace a landed verdict. For example, gate it on there being no verdict:
```tsx
const engineBlocksUi = engineFailed && verdict === null;
...
{engineBlocksUi ? ( <engine error + Retry> ) : !isReady && verdict === null ? ( <Loading engine> ) : ( <bubble> )}
```
and add a test that sets the mocked engine's `hasError` to true after a verdict landed on the instant path and asserts `train-next` (the verdict actions) is still rendered.

### WR-02: Analyze or Next pressed before the background grade lands silently drops the record, biasing the audit toward fast devices (and Analyze also loses the restorable reveal)

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:1750-1767` and `:1231-1237`
**Issue:** The late-reading design only delivers `phone_grade` if the grade settles while the puzzle is still on screen (`attempt !== instantAttemptRef.current` drops it, and `handleAnalyzeClick` returns early without caching when `gradeResult === null`). The code comment records this as an accepted gap sized at "~1.5 s after an instant verdict". Two problems with that sizing:
1. The window is not a fixed 1.5 s. It is the anchor wait plus the after-played search, and it is longest on exactly the slow devices the audit exists to measure. A fast Next or Analyze click is also more likely on the verdict screen than the author assumes, because the instant path removes the wait that used to occupy those seconds. So the missing records are correlated with device speed and user hurry, which skews "phone vs server tier" accuracy toward fast phones and undermines the stated purpose of SEED-193.
2. For Analyze specifically, an early click is not just a missing record: no reveal-cache entry is saved, so browser Back no longer restores the solved reveal (the comment at lines 1746-1749 says a resumed session no longer contains the solved puzzle). That is a user-visible regression that only exists on the new path.
**Fix:** Two independent options. (a) For Analyze, cache with whatever is known instead of bailing: allow `gradeResult === null` when `instantGrade !== null` by saving the entry with a minimal placeholder, or defer the navigation until the grade settles (it is bounded by `TRAIN_GRADING_TIMEOUT_MS`). (b) For Next, flush the review body, then keep the in-flight grade's late reading by posting a dedicated review flush when the promise settles for the previous `(sessionId, position)` (the captured `sessionId` and `position` are already closed over in `gradeInBackground`), rather than dropping it on the `attempt` mismatch. The write-once coalesce on the server makes a trailing second flush safe. At minimum, record the sizing assumption and the selection-bias caveat in the SEED-193 follow-up so the audit is not read as unbiased.

## Info

### IN-01: `TrainPuzzle` / `ServerGradedMove` docstrings overstate "exposes nothing beyond the key already sent"

**File:** `app/schemas/train.py:501-507` and `:536-542`
**Issue:** The key and `runner_up_uci` were already on the wire, but `server_graded_moves` also carries every vetted alternative for soft and herring puzzles (including the herring good band and the soft `su` with its `inaccuracy` tier). That is a new pre-attempt disclosure: a client can now read the full set of moves that earn full points, and which second-best move is a trap, before playing. The key alone already lets a tampering client score full points, so this is not a new capability for cheating, but the comment justifies the field by an equivalence that does not hold. Per D-03 the owner accepted putting the set in the payload, so this is a documentation accuracy issue only.
**Fix:** Reword to state what is actually new (the full certified good band and tiers, accepted in D-03) so a later reader does not treat the field as zero-information.

### IN-02: D-11 `serverGradedUcis` exclusion in `shouldRecheck` is unreachable from the only caller

**File:** `frontend/src/lib/trainRecheck.ts:58` and `frontend/src/components/train/TrainSolveScreen.tsx:1156`
**Issue:** `runRecheck` runs only on the non-instant path. `gradeAndSolve` sends every played move that is in the server-graded set (and not the key, with a non-null key) down `solveInstantly`, so the only way a played move could be in `serverGradedUcis` and still reach `runRecheck` is when the key is null, and `shouldRecheck` already returns false for a null key. The added `includes(...)` guard is therefore dead in production and only exercised by its unit test. It is harmless and arguably a good belt-and-braces check, but it is also a second source of truth for "is this move server-graded" next to `instantServerTier`.
**Fix:** Either keep it with a comment saying it is a defensive duplicate of the `instantServerTier` routing, or drop the extra `serverGradedUcis` input and its call-site `.map(...)` allocation.

### IN-03: Review route accepts a `phone_grade` for any solved row with no consistency check against the D-05/D-06 invariants

**File:** `app/repositories/train_repository.py:3301-3309` and `app/schemas/train.py:371-388`
**Issue:** `PhoneGrade` validates field ranges but not that `tier` agrees with `key_es - played_es`, and the review route writes it onto any solved row the user owns, including a legacy no-key solve (D-06: "no record") or a played == key solve whose pair is unequal. Because the column is audit-only and user-scoped, a stale or tampered client can only pollute that user's own rows, and the doc on the model already tells accuracy queries to filter. This is therefore robustness hardening, not a vulnerability.
**Fix:** Optional: add a `model_validator` on `PhoneGrade` asserting `tier == "good"` when `key_es == played_es`, and/or have the audit query guard on `key_move IS NOT NULL`. Not required for this phase.

### IN-04: Defensive-fallback `GradeResult` replaces the pending state on the instant path, making the best-move arrow vanish after the verdict

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:1231-1235` (with `frontend/src/hooks/useTrainGradingEngine.ts:681-696`)
**Issue:** If `gradeMoveInner` takes its "anchor missing or mismatched" fallback (resolves a fabricated `GradeResult` with `bestMoveUci: null`, empty lines, `phoneReading: null`), the instant path calls `setGradeResult(grade)` and `setInstantGrade(null)`. `revealBestUci` is `gradeResult?.bestMoveUci ?? instantGrade?.keyUci`, so it flips from the real key (while pending) to `null`: the best-move arrow and the Best-move card the user was just shown disappear, and the Your-move card becomes an empty-line card with a fabricated 0.5 eval. On the normal path this fabrication already existed but was never visible as a change from a correct earlier state. The condition is rare (generation or fen mismatch after a supersede), so this is cosmetic.
**Fix:** In `gradeInBackground`'s fulfilment handler, treat a result with `phoneReading == null && bestMoveUci == null` as a failure: `setInstantGrade(state => state && { ...state, status: 'failed' })` instead of `setGradeResult(grade)`, keeping the key-derived arrow and card.

---

_Reviewed: 2026-10-08T22:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
