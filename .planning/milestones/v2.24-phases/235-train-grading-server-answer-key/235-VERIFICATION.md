---
phase: 235-train-grading-server-answer-key
verified: 2026-10-07T22:50:00Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - ".planning/phases/235-train-grading-server-answer-key/235-01-PLAN.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-01-SUMMARY.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-02-PLAN.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-02-SUMMARY.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-03-PLAN.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-03-SUMMARY.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-04-PLAN.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-04-SUMMARY.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-05-PLAN.md"
  - ".planning/phases/235-train-grading-server-answer-key/235-05-SUMMARY.md"
  - "alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py"
  - "app/models/drill_solve.py"
  - "app/repositories/train_repository.py"
  - "app/routers/train.py"
  - "app/schemas/train.py"
  - "app/services/train_pool.py"
  - "frontend/src/components/train/TrainReveal.tsx"
  - "frontend/src/components/train/TrainSolveScreen.tsx"
  - "frontend/src/components/train/trainBubbleState.ts"
  - "frontend/src/hooks/trainGradingSupport.ts"
  - "frontend/src/hooks/useTrainGradingEngine.ts"
  - "frontend/src/lib/trainBotCopy.ts"
  - "frontend/src/lib/trainGuessLabels.ts"
  - "frontend/src/lib/trainRecheck.ts"
  - "frontend/src/types/train.ts"
covered_digest: "v3:sha256:76ad7d3e1a778bd77bf9a6b2d0cfaa930562de520dd439d74234626359ac48e7"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 235: Train Grading Anchored to the Server Answer Key Verification Report

**Phase Goal:** A Train reveal never contradicts itself. The server's key becomes the single source of truth for the solution, the played move is graded against it apples to apples, and disagreements are recorded so answer-key quality can be judged from real prod solves.
**Verified:** 2026-10-07
**Status:** passed
**Re-verification:** Yes. The earlier report went stale when the code-review fixes (6fba4d350 WR-01, b1b7c9819 WR-02) changed covered files. This report re-reads the CURRENT code and folds in the completed browser UAT (235-UAT.md, 4/4 pass, commit 38cc3cfac).

## Goal Achievement

There is no REQUIREMENTS.md for this milestone and ROADMAP has no separate SC list beyond the goal, so the truths are derived from the goal and CONTEXT D-01..D-20.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The pre-attempt payload carries the server key, puzzle type and sharp runner-up for all three sources, on fresh, resume and race-resume paths (D-05/D-06/D-07/D-19) | VERIFIED | `answer_key_for` / `legal_answer_key` in `app/services/train_pool.py`; `_answer_keys_by_position` + `_attach_answer_keys` funnel in `app/repositories/train_repository.py`; the router maps `key_move_uci`, `puzzle_type`, `runner_up_uci` (`app/routers/train.py:112-114`, plus `:186`, `:295` on the reveal/solve paths). Illegal key degrades to null. UAT test 1 saw `key_move_uci f4h4, puzzle_type sharp, runner_up_uci h1h7` in the live payload. `tests/services/test_train_pool.py` + schema tests re-run: 144 passed. |
| 2 | The solution arrow and BEST MOVE box name the server key, not the phone's mount pick (D-08/D-09) | VERIFIED | `startGrading(fen, keyUci)` (`useTrainGradingEngine.ts:586`) runs the think-time search on the after-key position and builds the anchor via `keyedAnchorFrom` (`:612`); `GradeResult.bestMoveUci` / `bestLine` come from `anchor.keyUci` / `anchor.keyLine` (`gradeMoveInner`, `:645-740`); `TrainSolveScreen.tsx:1089,1202` pass `puzzle.key_move_uci`. Live: UAT test 1 on the user-28 FEN (1r2r1k1/pq3pPp/...) read arrows from the board SVG, blue best `f4>h4`, BEST MOVE box "Qh4" +1.2, never the phone's b3; played b3 +0.6 and game Rxh7 +0.0, both at or below the key line. |
| 3 | The played move is graded apples to apples: key played = good with no search; otherwise after-played vs after-key at the same 1.5 s budget, never mixing server and client numbers (D-01) | VERIFIED | `gradeMoveInner`: `playedMoveUci === anchor.keyUci` fast path (`:669`), otherwise one `searchAfterMove(..., TRAIN_GRADING_MOVETIME_MS)` and `classifyLiveSeverity(anchor.es, esAfter)`. Terminal after-move positions score without a search (`terminalSearchResult`, `trainGradingSupport.ts:201`). `TRAIN_GRADING_MOVETIME_MS` 1500 and `TRAIN_GRADING_MAX_NODES` 2000000 unchanged (D-03). Behavior preserved by WR-02 (helpers moved verbatim; 681 targeted tests pass). |
| 4 | A missing, null or illegal key falls back to today's root-search grading (D-07) | VERIFIED | `startGrading` falls back to the root `search(...)` + `legacyAnchorFrom` when `keyUci` is null or the after-key FEN cannot be built (`:603-616`); `legacy: true` anchors are rejected by `planRecheck` (`trainGradingSupport.ts:324`). Backend sends null for an illegal/absent key; frontend `TrainPuzzle` fields are optional so stale bundles still work. |
| 5 | A played sharp runner-up (`su`) is graded server-side from the blob's b/s evals (D-02) | VERIFIED | `sharp_runner_up_graded_move` + `_classify_sr_solve` append it to `graded_moves`; `_resolve_grade` gives the server tier precedence; the display-only vetted list stays empty so `su` never renders as "also fine". Covered by repository/router tests (passed earlier at 414; schema and pool subsets re-run green now). |
| 6 | The sharp disagreement re-check fires only on the D-10 trigger, re-runs both after-move searches at 3 s sequentially with its own timeout and raised node cap, and its verdict replaces the 1.5 s grade (D-10/D-11/D-13) | VERIFIED | `shouldRecheck` in `lib/trainRecheck.ts` (sharp, key present, played not key, played not `su`, tier good), called from `TrainSolveScreen.tsx:1104`. `recheckMoveInner` (`useTrainGradingEngine.ts:758`) = `planRecheck` -> key search -> played search at `TRAIN_RECHECK_MOVETIME_MS` 3000 / `TRAIN_RECHECK_MAX_NODES` -> `finishRecheck` (`trainGradingSupport.ts:364`, same `classifyLiveSeverity`), under `TRAIN_RECHECK_TIMEOUT_MS` 12000. UAT test 2: three live re-checks showed "Checking your move…" ~1.5 s then "Taking a closer look…" for 6.0 s, then the verdict. Earlier mutation check (drop `su` exclusion) failed `trainRecheck.test.ts` and the screen test. |
| 7 | Timeout or engine error keeps the 1.5 s grade, sends no record, grants no credit; a timed-out re-check never dispatches its second search (D-20, WR-01) | VERIFIED | `recheckMove` (`:807`) goes through `raceWithTimeout` (`trainGradingSupport.ts:438`), which aborts an `AbortSignal` on timeout; `recheckMoveInner` returns null at `if (signal.aborted) return null;` (`:788`) before dispatching the played search. `recheckMove` never rejects (rejection mapped to null) and swaps the anchor only on success (`:817-821`). Unit test `(d2)` in `useTrainGradingEngine.test.ts:1518` covers the late-key-answer case (review fix report: reverting the guard fails it with `expected 4 to be 3`). Live: UAT test 2 timeout leg (3 s search swapped for `go infinite`) held "Taking a closer look…" 12.5 s, fell back to the 1.5 s verdict, only ONE 3 s search dispatched, `drill_solves.recheck` stayed NULL, reveal game line loaded. |
| 8 | Confirmed disagreement is credited server-side for BOTH guesses after sanity checks, and every re-check is recorded in `drill_solves.recheck` (D-14/D-17/D-18) | VERIFIED | `_disagreement_accepted` + `_resolve_grade` in `app/repositories/train_repository.py`; `record_solve` writes `{**recheck.model_dump(), "accepted": ...}` for confirmed AND resolved and omits the column otherwise (SQL NULL). Migration `c5e8a2d7b914` is the sole alembic head (`uv run alembic heads`). `SolveRecheck` is `extra="forbid"` with strict bounded floats; malformed value dropped to None (schema tests: pass). UAT test 4 on the dev DB: confirmed rows `{v:1, outcome:confirmed, accepted:true, ...four ES, four depths}`, resolved row `{outcome:resolved, accepted:false}`; across all solved rows 3 objects, 57 SQL NULL, 0 JSON null. |
| 9 | The reveal shows the D-15 line and phone-honest numbers on a confirmed disagreement, and the D-12 wait copy during the re-check (D-12/D-15/D-16) | VERIFIED | `guessFeedbackProse` returns "`${keySan} is the engine's first choice, but your move holds up too.`" when the SERVER `disagreement` flag is set (`lib/trainGuessLabels.ts:84-88`); wait copy `Taking a closer look…` via `resolveBubbleState`. `finishRecheck` leaves the played line unclamped and sets `anchor.unclamped` only on `confirmed`. UAT test 3 live: critical guess (Qe3 vs key Kg7) and several guess (Qb6 vs key Qe3) both show the D-15 line, both +1 guess, played line -4.3 shown better than key -2.6 (unclamped); resolved control downgraded to `??` with normal copy and no D-15 line. |
| 10 | The key and puzzle type are never displayed before the attempt (D-05 rule) | VERIFIED | Production reads of `key_move_uci` / `puzzle_type` / `runner_up_uci` are limited to grading and `shouldRecheck` call sites in `TrainSolveScreen.tsx`; the key SAN appears only in the post-attempt guess card. |

**Score:** 10/10 truths verified (0 present, behavior-unverified). The behavior-dependent truths (6, 7, 8) have behavioral unit tests and live UAT evidence.

### Review-Fix Confirmation (the reason for re-verification)

- **WR-01 (6fba4d350):** confirmed in code. `raceWithTimeout` creates an `AbortController`, aborts on timeout (`trainGradingSupport.ts:447-451`); `recheckMoveInner` checks `signal.aborted` between the two searches (`useTrainGradingEngine.ts:788`) with a fix-site comment. The generation is deliberately not bumped on timeout so the reveal's anchor stays valid. Test `(d2)` exists and live UAT confirmed a single 3 s dispatch after a real overrun.
- **WR-02 (b1b7c9819):** hook 1251 -> 902 lines; new pure module `trainGradingSupport.ts` (468 lines) holds the search/grade types, `terminalSearchResult`, `keyedAnchorFrom`, `legacyAnchorFrom`, `clampLineEvalToBest`, `fenAfterUciMove`, `buildSearchResult`, `planRecheck`, `finishRecheck`, `raceWithTimeout`. The three hand-rolled settle-once wrappers (`gradeMove`, `recheckMove`, `startGameMoveSearch`) now share `raceWithTimeout` with identical timeout/failure messages. `GradeResult`, `RecheckResult`, `TrainEngineLine` are re-exported from the hook (`:80`), so importers are unchanged. Behavior preserved: targeted run of `useTrainGradingEngine`, `trainRecheck` and `components/train` = 25 files, 681 tests passed. (A first run under concurrent suite load hit one testing-library 3 s `waitFor` timeout; the immediate re-run was 681/681, so this is load-induced flake, consistent with the known heavy-test timeout flake, not a regression.)
- The reveal-time game-line search (`startGameMoveSearch`) still reuses the key line when the game move equals the key, clamps against the key line unless the anchor is `unclamped` (D-16), and rejects on a superseded generation.

### Decision Coverage (D-01..D-20)

| Decision | Disposition |
|----------|-------------|
| D-01, D-03, D-08 | Implemented (truths 2, 3) |
| D-02 | Implemented (truth 5) |
| D-04 | Honored: `classify_puzzle_type`, `SHARP_GAP_ES` and server budget unchanged |
| D-05, D-06, D-07, D-19 | Implemented (truths 1, 4, 10) |
| D-09, D-16 | Implemented (truths 2, 9) |
| D-10, D-11, D-13 | Implemented (truth 6) |
| D-12, D-15 | Implemented (truth 9) |
| D-14, D-17, D-18 | Implemented (truth 8) |
| D-20 | Implemented (truth 7, plus WR-01) |
| Deferred ideas (re-check on inaccuracy reading, server deep re-check queue, user-28 "several"+played-key case) | Correctly not implemented, per CONTEXT |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py` | VERIFIED | Nullable JSONB, sole alembic head |
| `app/models/drill_solve.py` `recheck` | VERIFIED | Mapped column, SQL NULL when absent (UAT: 0 JSON null) |
| `app/services/train_pool.py` | VERIFIED | `answer_key_for`, `legal_answer_key`, `sharp_runner_up_graded_move`, `graded_moves_from_vetted` |
| `app/repositories/train_repository.py` | VERIFIED | Funnel, `_resolve_grade`, `_disagreement_accepted`, recheck write |
| `app/schemas/train.py` | VERIFIED | `TrainPuzzle` fields, `SolveRecheck`, `SolveRequest.recheck`, `SolveResponse.disagreement` |
| `frontend/src/hooks/useTrainGradingEngine.ts` | VERIFIED | Key-anchored grading, `recheckMove`, abort-aware re-check |
| `frontend/src/hooks/trainGradingSupport.ts` | VERIFIED | New pure module from WR-02, imported by the hook; no orphan |
| `frontend/src/lib/trainRecheck.ts` | VERIFIED | `shouldRecheck`, `recheckOutcome`, `buildRecheckPayload` |
| `TrainSolveScreen.tsx`, `trainBubbleState.ts`, `trainBotCopy.ts`, `trainGuessLabels.ts`, `TrainReveal.tsx`, `types/train.ts` | VERIFIED | Wired as in truths 2, 6, 9 |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| Fresh/resume return paths -> `_attach_answer_keys` | WIRED |
| `_answer_keys_by_position` / solve-time classification -> `answer_key_for` | WIRED |
| `TrainSolveScreen` -> `startGrading(fen, key)` (mount + engine-retry effects) | WIRED (`:1089`, `:1202`) |
| `gradeAndSolve` -> `shouldRecheck` -> `recheckMove` -> POST `recheck` | WIRED (`:1104`-`:1116`) |
| `recheckMove` -> `raceWithTimeout` signal -> `recheckMoveInner` abort guard | WIRED (`:807-815`, `:788`) |
| `record_solve(recheck=...)` -> `SolveResponse.disagreement` -> `guessFeedbackProse` | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Grading hook, recheck rules, train components | `npx vitest run src/hooks/__tests__/useTrainGradingEngine src/lib/__tests__/trainRecheck src/components/train` | 25 files, 681 passed (one load-induced timeout on the first run, clean on re-run) | PASS |
| Pool + recheck schema | `uv run pytest tests/schemas/test_train_recheck_schema.py tests/services/test_train_pool.py` | 144 passed | PASS |
| Alembic head | `uv run alembic heads` | `c5e8a2d7b914 (head)` | PASS |
| Live browser UAT | 235-UAT.md (claude-in-chrome, dev build, user 28) | 4/4 pass, 0 issues | PASS |

The full backend and frontend suites were not run by this verifier; the orchestrator runs them concurrently.

### Probe Execution

Not applicable: the phase declares no probe scripts. `235-COVERAGE.md` declares no external API integration (first-party only); it is not a source file.

### Requirements Coverage

No REQUIREMENTS.md and no phase requirement IDs. The plans' `requirements:` lists are D-xx decision IDs, all accounted for above. No orphaned requirements.

### Anti-Patterns Found

No `TBD`, `FIXME` or `XXX` markers in the phase's backend or frontend source files (grep over the hook, support module, `trainRecheck.ts`, `train_pool.py`, `train_repository.py`, `schemas/train.py`). No stubs: all grading, re-check and key-attachment paths are substantive and data-flowing (keys come from `game_positions.best_move`, `herring_pool.ladder`, the filler CSV; numbers from the phone's engine).

| Finding | Severity | Detail |
|---------|----------|--------|
| WR-01, WR-02 | Resolved | Fixed (235-REVIEW-DISPOSITION.md: `fixed`); verified above. |
| IN-01..IN-04 | Info | Still `open` in the disposition: positional booleans in `ResolvedGrade(...)`, mangled header comment in `trainBubbleState.ts`, client-asserted ES numbers trusted for the D-14 credit (owner ruling in D-05: cheating is not a concern), `_classify_sr_solve` always reads `game_positions.best_move`. None affects the goal. |
| UAT observation | Info | The bubble flips back to "Checking your move…" for 60-100 ms (the solve POST) between "Taking a closer look…" and the verdict. Cosmetic; would last one POST round trip on prod. |
| Hook size | Info | `useTrainGradingEngine` is 902 lines after WR-02; the UCI `handleLine` dispatcher and Worker lifecycle stay in the hook by a recorded cohesion judgement. Soft guidance only; the depth gate passes. |

### Human Verification Required

None. The four former human items (reveal names the server key on the user-28 FEN, re-check wait copy and timeout fallback, D-15 guess card for both guesses, `drill_solves.recheck` rows) were exercised live in Chrome against the dev build and passed (235-UAT.md, commit 38cc3cfac). Nothing remains genuinely unverifiable; real-prod answer-key quality is the downstream purpose of the recorded `recheck` data, not a verification gate.

### Gaps Summary

No gaps. Every decision D-01..D-20 is implemented, deliberately deferred, or out of scope as recorded in CONTEXT. The review fixes WR-01 and WR-02 are present in the current code, behavior-preserving, and covered by tests and live UAT.

---

_Verified: 2026-10-07_
_Verifier: Claude (gsd-verifier)_
