---
phase: 236-train-phone-grade-instant-verdict
verified: 2026-10-08T22:10:00Z
status: gaps_found
score: 12/13 must-haves verified
covered_files:
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-01-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-01-SUMMARY.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-02-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-02-SUMMARY.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-03-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-03-SUMMARY.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-04-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-04-SUMMARY.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-05-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-05-SUMMARY.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-06-PLAN.md"
  - ".planning/phases/236-train-phone-grade-instant-verdict/236-06-SUMMARY.md"
  - "CHANGELOG.md"
  - "alembic/versions/20261008_120000_d3a7f1c9e246_drill_solves_phone_grade.py"
  - "app/models/drill_solve.py"
  - "app/repositories/train_repository.py"
  - "app/routers/train.py"
  - "app/schemas/train.py"
  - "app/services/train_pool.py"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/train/TrainReveal.tsx"
  - "frontend/src/components/train/TrainSolveScreen.tsx"
  - "frontend/src/components/train/trainBubbleState.ts"
  - "frontend/src/hooks/trainGradingSupport.ts"
  - "frontend/src/hooks/useTrainGradingEngine.ts"
  - "frontend/src/hooks/useTrainPuzzleTelemetry.ts"
  - "frontend/src/lib/trainPhoneGrade.ts"
  - "frontend/src/lib/trainRecheck.ts"
  - "frontend/src/types/train.ts"
covered_digest: "v3:sha256:71ddc359e2a56c5c01e7ce679c0dcc7f7842f390675d8833e80e2f3674de1ec7"
behavior_unverified: 0
overrides_applied: 0
re_verification: false
gaps:
  - truth: "D-15 (plans 05 and 06 must-have): if the background search times out or errors, the reveal stays open with the server verdict, the Your-move card shows the played move without a line/eval, and NO engine-error state appears"
    status: partial
    reason: "The timeout leg holds. The error leg does not in the real engine: the only way the grading hook rejects a search with an error is worker.onerror, which also sets hasError=true, and TrainSolveScreen renders `engineFailed ? <train-engine-error + Retry> : !isReady ? ... : <TrainBotBubble>` with no verdict gate. After an instant verdict, a Worker crash during the 1.5-3 s background search therefore replaces the verdict bubble (and its Solution/Analyze/Next row) with 'Failed to load the grading engine' + Retry. The component tests mock the hook and only reject the gradeMove promise, so they cannot see hasError flip. Recoverable (Retry restarts the engine and the bubble returns because the verdict lives in trainSession.lastSolveResponse), the verdict itself is intact and server-final, and the same exposure class pre-dates the phase (the post-verdict game-move search shares this Worker), but D-15 is a locked decision and a stated must-have."
    artifacts:
      - path: "frontend/src/components/train/TrainSolveScreen.tsx"
        issue: "line ~2044: engineFailed branch has no `verdict === null` gate, so it displaces a landed verdict bubble"
      - path: "frontend/src/hooks/useTrainGradingEngine.ts"
        issue: "line ~558: worker.onerror sets hasError for any Worker failure, including one that happens after the verdict"
    missing:
      - "Gate the engine-error and Loading-engine arms on `verdict === null` (or equivalent) so a landed verdict bubble is never displaced"
      - "Add a TrainSolveScreen test that flips the mocked engine's hasError to true after an instant-path verdict and asserts train-next is still rendered and train-engine-error is not"
deferred: []
behavior_unverified_items: []
coincidental_reliance_items: []
human_verification:
  - test: "Desktop Chrome: on a soft SR puzzle or herring with a known 'also fine' alternative, play that alternative"
    expected: "Verdict (points, guess card, board badge) appears within about one round trip with no 'Checking your move...' copy; the Your-move card shows 'Loading...' and fills about 1.5 s later; the eval bar appears after it; Next works"
    why_human: "Real timing and visual smoothness need a browser; vitest uses mocked timers and a FakeWorker"
  - test: "After that instant solve and a normal keyed solve (off-key phone-graded move), then a legacy no-key solve, run: SELECT move_quality, phone_grade, played_move FROM drill_solves WHERE user_id = <dev user> ORDER BY solved_at DESC LIMIT 3"
    expected: "phone_grade is a six-key object for the instant solve (arrives via the Next review flush) and for the phone-graded solve (via the POST); SQL NULL for the legacy no-key solve"
    why_human: "End-to-end through a real browser, real Stockfish Worker, real keepalive fetch and the dev DB; unit and integration tests cover each hop separately"
  - test: "Real phone: play a server-graded non-key move and watch the eval-bar slot and Your-move card"
    expected: "Report-only. The eval bar stays an empty frame until the background reading settles, then appears; inspect phone_grade key_depth/played_depth in prod after release to confirm no contention-induced shallow readings"
    why_human: "No phone hardware in CI (236-VALIDATION manual-only leg). Not required for the code gap above"
---

# Phase 236: Train Phone Grade Record & Instant Server Verdict Verification Report

**Phase Goal:** Make Train grading accuracy measurable from stored data (record the phone's grade on every keyed solve in `drill_solves.phone_grade`, `move_quality` stays the effective tier) and stop making users wait ~1.5 s for a phone grade the server discards (instant verdict for server-graded moves, background search fills the Your-move card and supplies the phone reading).
**Verified:** 2026-10-08
**Status:** gaps_found (one narrow, cheaply closable gap; everything else verified against code and tests)
**Re-verification:** No, initial verification

## Goal Achievement

The goal is substantively achieved. Both ROADMAP deliverables exist, are wired end to end, and are covered by tests whose failure under reversion I confirmed myself. The single gap is a locked-decision edge (D-15, Worker-crash flavor) that the review flagged as WR-01 and that I confirmed in the code.

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | ROADMAP SC1 / D-01, D-05, D-06, D-07, D-13: `drill_solves.phone_grade` is a nullable JSONB column; keyed solves POST a six-key `{v,tier,key_es,played_es,key_depth,played_depth}` record; SQL NULL (never JSON null) when absent; malformed record dropped to None; legacy no-key path sends none | VERIFIED | Migration `d3a7f1c9e246` (down_revision `c5e8a2d7b914`, `JSONB(none_as_null=True)`), `alembic current` = `d3a7f1c9e246 (head)` on dev DB. `PhoneGrade` (`extra="forbid"`, reuses `RecheckExpectedScore`/`RecheckDepth`) and wrap validators on `SolveRequest` and `ReviewRequest` at `app/schemas/train.py`. Claim UPDATE adds the column only `if phone_grade is not None` (`train_repository.py:3472`). Client: `buildPhoneGradePayload` + `phoneReading` filled on keyed exits, `null` on legacy and fallback exits (`useTrainGradingEngine.ts`), `phone_grade` spread into the POST only when non-null (`TrainSolveScreen.tsx:1293`). 98 targeted backend tests pass. |
| 2  | D-02 / D-04: `move_quality` stays the effective tier; `phone_grade` is audit-only, never an input to `_resolve_grade`; always the 1.5 s reading, captured before a re-check can replace `grade` | VERIFIED | `_resolve_grade` / `_override_for_key_move` have no hunk in the phase diff (only the two classifiers and `record_solve` claim values changed). `record_solve` stores `phone_grade.model_dump()` without passing it to `_resolve_grade`. `phoneReading` captured at `TrainSolveScreen.tsx:~1270` before `runRecheck`. Router test asserts identical `move_quality`/`correct_guess` with and without a fabricated record. |
| 3  | D-12: review route accepts optional `phone_grade`, writes it to its own column write-once via `coalesce`, never into telemetry; unknown top-level key still 422; second flush keeps its telemetry and returns 204 | VERIFIED | `merge_solve_telemetry` uses `func.coalesce(DrillSolve.phone_grade, literal(..., JSONB))` inside the one UPDATE (no WHERE guard); router passes `exclude={"phone_grade"}` to the telemetry patch. **Mutation check by me:** replacing the coalesce with a plain overwrite made `test_review_flush_phone_grade_is_write_once` and `test_review_flush_never_overwrites_solve_time_phone_grade` fail; reverted. |
| 4  | D-03 / D-08 / parity: `TrainPuzzle.server_graded_moves` is on the pre-attempt payload (fresh and resumed), derived by ONE function `server_graded_moves_for` shared with the solve path; read client-side in exactly one non-type file after the move | VERIFIED | `server_graded_moves_for` in `train_pool.py`; called from `_answer_keys_by_position` (composition, line 2295) and both `_classify_sr_solve` / `_classify_herring_solve` (lines 2709, 2796). Router maps to wire `ServerGradedMove(uci,tier)`. Parity test (`graded_parity`) passes. Frontend grep: `server_graded_moves` appears in `types/train.ts`, `trainRecheck.ts` (doc comment only) and `TrainSolveScreen.tsx` (single `?? []` default at line 906). |
| 5  | ROADMAP SC2 / D-09, D-10, D-16: when the played move is a non-key member of the set, the solve POSTs immediately with the payload tier, before the after-played search answers; verdict renders from the SolveResponse; no 'Checking your move...' at any point | VERIFIED | `gradeAndSolve` branches on `instantServerTier(...)` before any grading wait (`TrainSolveScreen.tsx:1249`); `solveInstantly` posts without `phone_grade`/`recheck`, `isGrading` stays false, copy-less `train-submitting-indicator` spinner. **Mutation check by me:** forcing `instantServerTier` to return null failed 10 tests across `trainPhoneGrade.test.ts` and `TrainSolveScreen.test.tsx` (instant POST, copy-less spinner, D-09 never-render-payload-tier); reverted. |
| 6  | D-11: server-graded moves are never re-checked | VERIFIED | `shouldRecheck` excludes `serverGradedUcis` (`trainRecheck.ts`); instant path never calls `runRecheck`. Unit test in `trainRecheck.test.ts`. Review IN-02 (guard is a defensive duplicate of the instant routing) is accurate and harmless. |
| 7  | Pitfall 1 / D-14 prerequisite: the reveal's game-move search queues behind in-flight grading (no `stop`), and `gradeMove` hands the think-time key line over early via `onKeyLine` (never for a legacy anchor) | VERIFIED | `gradingSettledRef` set in `gradeMove`, awaited in `startGameMoveSearch`, reset in `startGrading`/`abortGrading`, superseded wait rejects; `options?.onKeyLine` gated by `!anchor.legacy`. FakeWorker-level and component-level tests pass (413 tests across the 7 touched suites re-run by me). |
| 8  | D-14 / D-16: reveal opens on the SolveResponse; Your-move card shows a loading state then fills; solution card shows the key line once the anchor settles; badge/arrow follow the server pair and the key while pending; eval bar waits for the grade; game search dispatched once | VERIFIED | `InstantGradeState`, `PendingLineCard`, `revealBestUci = gradeResult?.bestMoveUci ?? instantGrade?.keyUci`, `showEvalBar = showResultRow && instantGrade?.status !== 'pending'` all present and exercised by `TrainReveal.test.tsx` (5 instant-path tests) and `TrainSolveScreen.test.tsx`. Summary-reported mutation proofs (a-c plus Pitfall 5 bonus) not re-run by me; the independent instant-path mutation above corroborates the test-suite sensitivity. |
| 9  | D-15: a failed/timed-out background search leaves the reveal open with the server verdict, a header-only Your-move card, no `train-grading-error`, no `phone_grade`, **and no engine-error state** | FAILED (partial) | Timeout leg and `gradingError` leg verified. Error leg fails in the real engine: see Gaps. `worker.onerror` -> `hasError` -> `engineFailed` -> verdict bubble replaced by `train-engine-error` + Retry. Tests mock the hook, so they pass without exercising this. Confirmed review WR-01. |
| 10 | Pitfall 4: a background grade settling after the user moved on never writes the next puzzle's state and its record is never flushed for another position | VERIFIED | `instantAttemptRef` bumped on every puzzle change and compared in all three `gradeInBackground` callbacks; `setLatePhoneGrade` keyed on `(sessionId, position)` vs `keyRef`. Component test asserts puzzle B's Your-move card stays loading. |
| 11 | Late reading rides the review flush (Next and pagehide) while the puzzle is on screen; a flush sent before the search settled carries none (D-12 "send nothing") | VERIFIED | `buildReviewBody` spreads `latePhoneGradeRef` into both `postReviewKeepalive` call sites; `useTrainPuzzleTelemetry.test.ts` covers settle-before-flush, flush-before-settle and reset-on-puzzle-change. See WR-02 note below on selection-bias caveat (not a must-have failure). |
| 12 | "Not a grading change": no new engine search, no scoring effect, `_resolve_grade` decision order and solve-time `graded_moves` unchanged; pre-existing `record_solve`/`_resolve_grade` tests pass unmodified | VERIFIED | No hunk in `_resolve_grade`; classifiers only swap the graded-set derivation onto the shared function; D-10 path 1 / path 3 tests (`resolve_grade`) pass. The background search is the same search the old path ran, just not awaited before the POST. |
| 13 | CHANGELOG `[Unreleased]` Changed bullet exists and the pre-merge gate was run | VERIFIED | `CHANGELOG.md:31` bullet present. Orchestrator-reported full gate (5436 backend, 5288 frontend, lint/tsc/knip/ruff/ty clean) accepted; I independently re-ran the targeted backend (98) and frontend (413) suites green and confirmed Alembic head. |

**Score:** 12/13 truths verified (0 present-but-behavior-unverified)

### Gaps Summary

**Gap 1 (BLOCKER for D-15, small fix):** confirmed WR-01. This defeats exactly one must-have (D-15, "no engine-error state appears") and no ROADMAP success criterion: the verdict is still correct and server-final, the score/points are recorded, the `phone_grade` pipeline is unaffected, and Retry restores the bubble. The fix is a `verdict === null` gate on the two non-bubble arms plus one test. I did not downgrade it to a warning because the real engine-error path always sets `hasError`, so the shipped behavior contradicts a locked decision on the only error flavor that can occur, and nothing in the suite would catch it. It is a narrow edge (Worker crash within ~3 s after an instant verdict, ~17% of solves), not a goal failure; the orchestrator can reasonably choose to accept it via an `overrides:` entry instead of a closure plan if shipping speed matters (the exposure class pre-dates the phase).

**Not a must-have failure, advisory (review WR-02):** an early Next press drops the late reading by design (D-12: "If the search has not finished at flush time, send nothing for it"), and an early Analyze click skipping the reveal-cache write is an accepted, documented gap in plan 06's own must-haves (RESEARCH A2, comment at `handleAnalyzeClick`). Neither defeats a must-have or success criterion. The reviewer's selection-bias argument is a fair caveat for the follow-up audit (missing records skew toward fast Next/Analyze clickers and slow devices, whose search window is longest). Recommendation: note it in the SEED-193 follow-up so the 2026-10-22 audit does not read the record set as unbiased; optionally close it later by posting a trailing review flush when the captured `(sessionId, position)` settles late (server write-once makes that safe). Review IN-01 to IN-04 are documentation/robustness items with no effect on any must-have (IN-04, the vanishing best-move arrow on the defensive-fallback `GradeResult`, is cosmetic and rare).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `alembic/versions/20261008_120000_d3a7f1c9e246_drill_solves_phone_grade.py` | nullable JSONB add/drop | VERIFIED | Chained off `c5e8a2d7b914`; single head; applied to dev DB |
| `app/models/drill_solve.py` | `phone_grade` mapped column + D-04..D-06 docs | VERIFIED | `JSONB(none_as_null=True)`, documented accuracy-query filter |
| `app/schemas/train.py` | `PhoneGrade`, `ReviewRequest`, `ServerGradedMove`, `TrainPuzzle.server_graded_moves` | VERIFIED | Wrap validators drop malformed records |
| `app/repositories/train_repository.py` | claim write, coalesce write-once, shared composition | VERIFIED | See truths 1, 3, 4 |
| `app/services/train_pool.py` | `server_graded_moves_for`, `legal_server_graded_moves` | VERIFIED | Pure, exported, used at 3 call sites |
| `frontend/src/lib/trainPhoneGrade.ts` | payload builder, `instantServerTier` | VERIFIED | Substantive and wired (mutation-checked) |
| `frontend/src/hooks/useTrainGradingEngine.ts` | `phoneReading`, `gradingSettledRef`, `onKeyLine` | VERIFIED | Wired from `TrainSolveScreen` |
| `frontend/src/hooks/useTrainPuzzleTelemetry.ts` | `setLatePhoneGrade` + flush body | VERIFIED | Both flush paths |
| `frontend/src/components/train/TrainReveal.tsx` / `TrainSolveScreen.tsx` / `trainBubbleState.ts` | instant branch, pending cards, submitting state | VERIFIED (D-15 gap in `TrainSolveScreen` engine-error arm) | |
| `CHANGELOG.md` | Changed bullet | VERIFIED | line 31 |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `solve_puzzle` route | `record_solve` | `phone_grade=body.phone_grade` | WIRED |
| `record_solve` claim UPDATE | `drill_solves.phone_grade` | `claim_values["phone_grade"]` only when present | WIRED |
| review route | `merge_solve_telemetry` | `exclude={"phone_grade"}` + separate arg, coalesce | WIRED |
| `_answer_keys_by_position` / classifiers | `server_graded_moves_for` | shared function | WIRED |
| compose route | `TrainPuzzle.server_graded_moves` | `ServerGradedMove(uci,tier)` map | WIRED |
| `gradeAndSolve` | `instantServerTier` -> `solveInstantly` | branch before grading wait | WIRED |
| `gradeInBackground` | `setLatePhoneGrade` -> review flush | attempt-guarded | WIRED |
| `gradeMove` | `gradingSettledRef` -> `startGameMoveSearch` | await before dispatch | WIRED |
| `instantGrade` state | `TrainReveal` cards, `showEvalBar`, `revealBestUci` | props/derivations | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| -------- | ---- | ------ | --------- | ------ |
| `phone_grade` column | tier/ES/depths | engine `anchor.es`, `anchor.depth`, `afterRaw.depth` via `phoneReading` | Yes (null on legacy/fallback by design) | FLOWING |
| `server_graded_moves` | uci/tier | blob/ladder via `server_graded_moves_for` | Yes | FLOWING |
| Your-move card | line/eval | `gradeResult.playedLine` after background `gradeMove` | Yes (pending/failed states otherwise) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend phone_grade / parity / resolve_grade / review / pre-attempt | `uv run pytest tests/schemas/test_train_phone_grade_schema.py tests/routers/test_train.py tests/repositories/test_train_repository.py -k "phone_grade or graded_parity or resolve_grade or review or pre_attempt"` | 98 passed | PASS |
| Frontend phase suites (7 files) | `npx vitest run` on trainPhoneGrade, trainRecheck, useTrainGradingEngine, useTrainPuzzleTelemetry, TrainReveal, trainBubbleState, TrainSolveScreen | 413 passed | PASS |
| Write-once mutation (revert coalesce) | edit + pytest `-k "phone_grade or review"` | 2 failed as expected; reverted | PASS |
| Instant-path mutation (`instantServerTier` -> null) | edit + vitest | 10 failed as expected; reverted | PASS |
| Alembic single head | `uv run alembic current` / `heads` | `d3a7f1c9e246 (head)` both | PASS |

Working tree was restored to clean after both mutations (`git status` empty).

### Probe Execution

SKIPPED: the phase declares no probe scripts.

### Requirements Coverage

No requirement IDs registered (`requirements_path` null). Coverage is by locked decisions D-01..D-16 (all addressed above; D-07 and the optional device hint are explicitly deferred by CONTEXT) and the ROADMAP success criteria (record phone grade: truths 1-3; instant verdict: truths 4-8; not a grading change: truth 12). No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `TrainSolveScreen.tsx` | ~2044 | Engine-error arm not gated on landed verdict | Blocker (D-15, see gap) | Verdict bubble + Next hidden after Worker crash during background grade |
| `TrainSolveScreen.tsx` | ~1750-1767 | Early Analyze/Next drops record / reveal cache | Warning (accepted per D-12 / RESEARCH A2) | Mild selection bias in future audit |
| `app/schemas/train.py` | 501-507, 536-542 | Docstring overstates "nothing beyond the key" | Info (review IN-01) | Documentation accuracy only |
| `trainRecheck.ts` | 58 | Defensive duplicate of instant routing | Info (IN-02) | None |

No TBD/FIXME/XXX/TODO markers were added in app or frontend non-test code in the phase diff.

### Human Verification Required

Needed for goal sign-off (manual-only legs from 236-VALIDATION.md / 236-06-SUMMARY.md):

1. **Desktop instant-verdict timing.** Test: play a soft-vetted or herring good-band alternative in desktop Chrome. Expected: verdict at about one RTT, no 'Checking your move...', Your-move card 'Loading...' then fills ~1.5 s later, eval bar then appears, Next works. Why human: real timing and visuals.
2. **Dev DB end-to-end row check.** Test: `SELECT move_quality, phone_grade, played_move FROM drill_solves ... ORDER BY solved_at DESC LIMIT 3` after an instant solve, a phone-graded solve and a legacy no-key solve. Expected: six-key object (review flush) / six-key object (POST) / SQL NULL. Why human: crosses real browser, Worker, keepalive fetch and DB.
3. **Phone eval-bar contention (report-only, not a sign-off blocker).** Inspect prod `phone_grade` depths after release.

---

_Verified: 2026-10-08_
_Verifier: Claude (gsd-verifier)_
