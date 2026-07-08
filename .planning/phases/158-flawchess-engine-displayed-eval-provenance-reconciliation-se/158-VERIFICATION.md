---
phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se
verified: 2026-07-07T20:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Cross-card eval identity on a live position: on /analysis, find a move shown on all three cards (exd5/Bc5 class); confirm one identical number everywhere, including Maia chart line colors matching the displayed evals."
    expected: "The same cp/mate number renders on the SF card, FC card, and Maia chart for that move; the Maia line/SAN-label color matches the number's severity bucket."
    why_human: "Requires real WASM Stockfish engines streaming in a live browser session against real positions — no automated screenshot/visual-diff harness exists for /analysis's live-engine surfaces (VALIDATION.md Manual-Only Verifications; 158-03-SUMMARY.md D4, human_judgment: true, status: unknown)."
  - test: "Watch a fresh position settle with Maia and/or FlawChess Engine on; observe whether any displayed eval visibly flips between a grading-run value and the free-run value during progressive refinement."
    expected: "Evals settle monotonically (placeholder '…' -> final value); no flapping between two different numbers for the same move."
    why_human: "Streaming timing is browser-real-time and depends on live WASM search progress; not reproducible in a unit test (VALIDATION.md Manual-Only Verifications)."
---

# Phase 158: FlawChess Engine displayed-eval provenance reconciliation Verification Report

**Phase Goal:** Every Stockfish eval displayed on the /analysis page — SF card, FlawChess card, Maia chart/quality bar, agreement verdict — resolves through one UCI-keyed lookup (authoritative free MultiPV run first, ONE shared analysis-grade searchmoves grading run second), so any move shown on two or more surfaces renders the identical number by construction, ending the three-independent-searches provenance mess.
**Verified:** 2026-07-07T20:15:00Z
**Status:** passed (human verification completed 2026-07-07 — both UAT items pass, see 158-UAT.md)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | A move displayed on two+ of SF/FC/Maia cards renders the same eval, sourced by UCI lookup, free-run > shared-grading precedence; MCTS pool grade (`objectiveEvalCp` from `workerPool.ts`) no longer a display source anywhere | ✓ VERIFIED | `frontend/src/lib/engineEvalLookup.ts:39-58` `buildEvalLookup` merges `pvLines` (free-run-first, `!lookup.has(uci)` guard) then `gradeMapBySan` (converted via `sanToUci`); no `objectiveEvalCp`/`RankedLine` param exists on the module (`grep -c "objectiveEvalCp\|RankedLine" engineEvalLookup.ts` = 0). `Analysis.tsx:741-758` builds `evalLookup` from `engine.pvLines`+`grading.gradeMap` and `reconciledRankedLines` swaps every displayed `objectiveEvalCp` for the lookup value; FC card (`FlawChessEngineLines.tsx:126`) and verdict (`FlawChessAgreementVerdict.tsx:101`) both read from `reconciledRankedLines`-sourced props, never raw `flawChessEngine.rankedLines`. Behavioral test `Analysis.test.tsx:387-403` seeds a move present in both sources with different values and asserts the rendered badge shows the free-run number, not the grading number. All 7 `engineEvalLookup.test.ts` unit tests pass. |
| 2 | `useStockfishGradingEngine` is the single shared fallback: candidate set = `shownSans ∪ displayed FC moves`, analysis-grade depth (depth-14/2500ms cap demonstrably lifted, budget from a real measurement), gated on `maiaEnabled \|\| flawChessEnabled` | ✓ VERIFIED | `useStockfishGradingEngine.ts:52` `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` (was 2500), `GRADING_TARGET_DEPTH` removed entirely (`grep -c "depth 14"` = 0); docstring cites the 158-01 headless-WASM measurement (2cp/23cp agreement deltas on middlegame/endgame). A genuine clause-order bug (`searchmoves` swallowing trailing `movetime`) was found and fixed in the same commit — confirmed present in the go-command build (`useStockfishGradingEngine.ts:252`, `movetime` before `searchmoves`). `Analysis.tsx:694-732` builds `unionSans` (deduplicated, sorted `shownSans ∪ flawChessDisplayedSans`, each gated on its own consumer) and `gradingEnabled = maiaEnabled \|\| flawChessEnabled`, pairing `fen`/`enabled` on the same condition. Behaviorally tested: `Analysis.test.tsx:355-383` drives real toggle clicks through all 4 `(maiaEnabled, flawChessEnabled)` combinations and asserts `enabled`/`fen` track the OR'd condition exactly (a genuine state-transition test, not presence-only). **Caveat (WARNING, not a truth failure):** the measured movetime=4000 budget was calibrated at candidate-union sizes 4/6/8, but the grading hook's own cache-union step (`allSans = [...cache.keys(), ...sans]`, `useStockfishGradingEngine.ts:230`) has no upper bound — an extended single-position session (e.g. repeated ELO-slider exploration) can grow the search union past the calibrated range and silently degrade grading depth below the free run's. Flagged as 158-REVIEW.md WR-03 (warning, not critical); does not falsify the truth as stated (the budget genuinely was measured, gating genuinely is OR'd) but is an unenforced assumption behind it. |
| 3 | Maia move-quality buckets (`classifyMoveQuality`) classify from the same reconciled evals they display | ✓ VERIFIED | `Analysis.tsx:769-790`: `qualityBySan` builds one `reconciledGradeMap` via `getBySan(evalLookup, position, san)` over `grading.gradeMap`'s keyspace, passes that SAME map to `classifyMoveQuality(...)` for bucket classification AND reads each merged entry's `evalCp`/`evalMate` from that SAME map (`const grade = reconciledGradeMap.get(san)`) — number and severity color are structurally the same data by construction, not independently computed. This `qualityBySan` map is threaded to `MovesByRatingChart.tsx` (line/SAN-label colors, `colorForQuality(qualityBySan.get(san)?.quality)`), `MaiaMoveQualityBar.tsx` (quality-bar segments via `bucketMovesByQuality`), and `computePositionVerdict` — all three confirmed via grep to consume the same `qualityBySan` prop passed from `Analysis.tsx:1640,1820`. `moveQuality.test.ts` unedited (0 diff) — signature-compatibility proof the reconciliation lives entirely in Analysis.tsx's memo chain. **Caveat (WARNING):** `qualityBySan`'s fallback for an unresolvable SAN (`{ evalCp: null, evalMate: null, depth: 0 }`, line 774) is not neutral — `evalToExpectedScore(null,null,...)` returns 0.5, which can transiently paint a real severity color (e.g. "blunder") off a fabricated even-position score during a brief stale-map window right after navigation (158-REVIEW.md WR-04). Narrow transient window; does not affect steady-state correctness. |
| 4 | The agreement verdict's FC-pick and SF-best evals both come from the lookup, making "FC pick grades higher than the objective best" impossible by construction | ✓ VERIFIED | `Analysis.tsx:1603-1605`: `flawChessLine={reconciledRankedLines[0] ?? null}`, `stockfishLine={engine.pvLines[0] ?? null}` — both sides resolve through the same `evalLookup` by construction (SF side was already free-run-sourced; FC side is now `evalLookup`-reconciled). Behavioral test `Analysis.test.tsx:406-423` seeds a raw `objectiveEvalCp: 999` (simulating the Qc7-class bug) on `flawChessState.rankedLines[0]` and asserts the rendered verdict sentence shows the grading-run-reconciled value (+0.4), never the inflated raw value (+10.0) — this is a genuine behavioral proof, not a presence check. |
| 5 | Practical scores (brown badges, MCTS backed-up expectation) and the locked Phase 153 search core are untouched — display/verdict overlay only | ✓ VERIFIED | `git diff --stat 786002e6..423f3a1d -- frontend/src/lib/engine/ frontend/src/hooks/useFlawChessEngine.ts` shows zero changes — the MCTS core, `RankedLine` type (`engine/types.ts`), and `workerPool.ts` are untouched by any phase-158 commit. `grep -c "reconciledEvalCp" engine/types.ts` = 0 (no field added to the frozen type). `Analysis.tsx:1314-1318` `topLine = flawChessEngine.rankedLines[0]` (raw, unreconciled) still feeds only `practicalScore` for the eval bar / brown badges — `reconciledRankedLines` is never substituted there. |

**Score:** 5/5 truths verified (0 present-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/hooks/useStockfishGradingEngine.ts` | Revised named budget constants (movetime 4000, no depth cap) | ✓ VERIFIED | Constants present, docstring cites measurement, go-command clause order fixed |
| `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts` | Updated go-command shape assertions | ✓ VERIFIED | Test asserts exact new command string, `not.toContain('depth ')`, `toContain('movetime 4000')` |
| `frontend/src/lib/engineEvalLookup.ts` | Pure module: `buildEvalLookup`, `getByUci`, `getBySan` | ✓ VERIFIED | All 3 exports present, no pool-grade param, reuses `sanToUci` |
| `frontend/src/lib/engineEvalLookup.test.ts` | Vitest unit tests, no jsdom/worker | ✓ VERIFIED | 7 tests, all pass |
| `frontend/src/pages/Analysis.tsx` | `evalLookup`/`reconciledRankedLines`/reconciled `qualityBySan` memos | ✓ VERIFIED | All three memos present and wired to display sites |
| `frontend/src/components/analysis/FlawChessEngineLines.tsx` | Exported `MAX_LINES` constant | ✓ VERIFIED | `export const MAX_LINES = 2;` |
| `frontend/src/pages/__tests__/Analysis.test.tsx` | New gating + SC1/SC4 reconciliation assertions | ✓ VERIFIED | "Grading run gating" and "Reconciled eval provenance" describe blocks present and passing |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `engine.pvLines` + `grading.gradeMap` | `evalLookup` | `buildEvalLookup(engine.pvLines, grading.gradeMap, position)` memo | ✓ WIRED | `Analysis.tsx:741-745` |
| `evalLookup` | `reconciledRankedLines` | `getByUci(evalLookup, line.rootMove)?.evalCp ?? null` | ✓ WIRED | `Analysis.tsx:752-758` |
| `reconciledRankedLines` | `FlawChessEngineLines` (`rankedLines` prop) | direct prop | ✓ WIRED | `Analysis.tsx:1588` |
| `reconciledRankedLines` | `FlawChessAgreementVerdict` (`flawChessLine`, `flawChessRankedLines`) | direct props | ⚠️ WIRED (with regression) | `Analysis.tsx:1603,1605` — correct for eval display, but `flawChessRankedLines` was previously the FULL rankedLines list (used for a rank-agnostic D-10 "was SF's pick also FC-ranked at any rank" match); now truncated to top-`MAX_LINES`=2, silently dropping the match for the common case where SF's pick is FC-ranked 3+. Confirmed in code (`FlawChessAgreementVerdict.tsx:206-209`, `matchedFlawChessLineForSf`). Does not affect eval-number display (only `practicalScore` is read from the match), so it does not falsify SC1-SC5, but it is a genuine collateral behavioral regression from this phase's wiring change (158-REVIEW.md WR-01). |
| `evalLookup` | `qualityBySan` | `getBySan(evalLookup, position, san)` reconciled map, fed to both `classifyMoveQuality` and merged output | ✓ WIRED | `Analysis.tsx:769-790` |
| `qualityBySan` | `MovesByRatingChart`, `MaiaMoveQualityBar`, `computePositionVerdict` | direct prop / function calls | ✓ WIRED | grep-confirmed consumption in all three |
| `maiaEnabled \|\| flawChessEnabled` | `grading` hook `fen`/`enabled` | `gradingEnabled` paired condition | ✓ WIRED | `Analysis.tsx:719,730-732`; behaviorally tested across 4 toggle combinations |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SEED-087 | 158-01, 158-02, 158-03 | Displayed-eval provenance reconciliation (seed, amended 2026-07-07) | ✓ SATISFIED | Not tracked in REQUIREMENTS.md's REQ-ID table (expected — seed IDs aren't roadmap REQ-IDs per phase note); `grep -n "Phase 158\|158" .planning/REQUIREMENTS.md` returns nothing to cross-reference, consistent with the note. No orphaned REQ-IDs found for this phase. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across all 7 phase-touched files | none found | — | No debt markers in any file this phase modified. |
| `Analysis.tsx` / `FlawChessAgreementVerdict.tsx` | 1605 / 206-209 | D-10 "any-rank" verdict match silently truncated to top-2 by the `reconciledRankedLines` swap | ⚠️ Warning | Collateral regression, not an eval-display bug (158-REVIEW.md WR-01) |
| `useStockfishGradingEngine.ts` | 326-364 | Stale-position grade can commit to the displayed map during rapid navigation, now flowing through the reconciliation surfaces this phase built | ⚠️ Warning | Pre-existing invariant (D-05) amplified in blast radius by this phase (158-REVIEW.md WR-02) |
| `useStockfishGradingEngine.ts` | 230 | Candidate-union cache accumulation is unbounded; measured budget assumed 6-8 | ⚠️ Warning | Could silently degrade grading depth in extended single-position sessions (158-REVIEW.md WR-03) |
| `Analysis.tsx` | 774 | `qualityBySan` null/null fallback resolves to a real 0.5 expected score, not a neutral "unknown" | ⚠️ Warning | Transient phantom severity coloring possible right after navigation (158-REVIEW.md WR-04) |

None of the four warnings are classified `critical` by the independent code review (`158-REVIEW.md`: 0 critical / 4 warning / 3 info), and my own reading of the code confirms each is real but does not falsify any of the 5 stated roadmap truths — they are edge-case/collateral risks layered on top of a structurally-sound reconciliation.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `engineEvalLookup` unit tests | `npm test -- --run src/lib/engineEvalLookup.test.ts` | 7/7 pass | ✓ PASS |
| `useStockfishGradingEngine` unit tests (go-command shape, gating) | `npm test -- --run src/hooks/__tests__/useStockfishGradingEngine.test.ts` | pass | ✓ PASS |
| `Analysis.tsx` gating + reconciliation tests | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | pass (includes 4-combo gating + SC1/SC4 assertions) | ✓ PASS |
| `moveQuality.test.ts` unedited signature-compat | `npm test -- --run src/lib/__tests__/moveQuality.test.ts` | pass, 0 diff vs pre-phase | ✓ PASS |
| Type check | `npx tsc -b` | 0 errors | ✓ PASS |
| Dead-export check | `npm run knip` | no findings | ✓ PASS |
| Lint | `npm run lint` | 0 errors (3 warnings, all in generated `coverage/` artifacts, unrelated to this phase) | ✓ PASS |
| Full frontend suite | `npm test -- --run` (run once, per verifier constraints) | 130 files / 1563 tests passed | ✓ PASS |
| Scope fence (MCTS core / RankedLine untouched) | `git diff --stat 786002e6..423f3a1d -- frontend/src/lib/engine/ frontend/src/hooks/useFlawChessEngine.ts` | empty diff | ✓ PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` declared or conventional for this phase; a frontend TypeScript/React phase with vitest coverage, not a migration/tooling phase.

### Human Verification Required

Two items, both explicitly declared manual-only in `158-VALIDATION.md`'s "Manual-Only Verifications" table and carried forward as the one open item in `158-03-SUMMARY.md`'s coverage (D4, `human_judgment: true`, `status: unknown`):

### 1. Cross-card eval identity on a live position

**Test:** On `/analysis`, find a move shown on all three cards (the exd5/Bc5 class from the seed's live UAT evidence); confirm one identical number everywhere.
**Expected:** The SF card, FC card, and Maia chart all show the same cp/mate number for that move; the Maia chart's line/SAN-label color matches the number's severity bucket.
**Why human:** Requires real WASM Stockfish engines streaming in a live browser session on real positions — no automated screenshot/visual-diff harness exists for `/analysis`'s live-engine surfaces. The wiring-level equivalent (that the code path structurally guarantees this) is unit-verified above (SC1/SC4); this item confirms the end-to-end live rendering.

### 2. No precedence flapping during progressive refinement

**Test:** Watch a fresh position settle with Maia and/or FlawChess Engine enabled.
**Expected:** Displayed evals settle monotonically (`'…' → value`); no visible flip between a grading-run value and the free-run value for the same move.
**Why human:** Streaming timing is browser-real-time and depends on live WASM search progress interleaving; not reproducible deterministically in a unit test.

### Gaps Summary

No gaps block the phase goal. All 5 ROADMAP success criteria are structurally verified in the codebase with passing behavioral unit tests (not just presence/grep), the full frontend suite (1563 tests / 130 files), `tsc -b`, `knip`, and `lint` are all green at HEAD, and the scope fence (Phase 153 MCTS core / `RankedLine` / practical scores untouched) is confirmed via an empty `git diff` over the phase's commit range.

Status is `human_needed` rather than `passed` solely because two manual UAT items — cross-card visual eval identity on a live position, and no precedence-flapping during streaming — were deliberately deferred to a phase-gate human check (per `158-VALIDATION.md` and the plan's own `<verification>` section) since no automated harness exists for live-WASM-in-browser visual verification. This was a planned, not missed, deferral.

Additionally, 4 WARNING-level findings from the independent code review (`158-REVIEW.md`, 0 critical) were independently re-verified against the actual code in this pass and confirmed real but non-blocking: a D-10 verdict-match truncation regression (WR-01), a pre-existing stale-grade-commit race amplified in blast radius (WR-02), an unenforced candidate-union-size assumption behind the measured grading budget (WR-03), and a non-neutral null-fallback in `qualityBySan` that can transiently paint a fabricated severity color (WR-04). None of these falsify any of the phase's 5 stated success criteria; they are recommended follow-ups, not gaps in this phase's goal achievement.

---

*Verified: 2026-07-07T20:15:00Z*
*Verifier: Claude (gsd-verifier)*
