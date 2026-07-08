---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
verified: 2026-07-07T21:06:10Z
status: passed
human_verified: 2026-07-08T15:48:57Z
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "D-03 @600 live case: at a real 600-ELO analysis position where Nb5 (~5% Maia) previously topped the FlawChess ranking with Qxf2 (~9%, Good) and Rxf2 (~57%, Mistake) as candidates, confirm the FlawChess card's top line is now Qxf2 — NOT Nb5, NOT Rxf2 — and the practical-score badge still reflects V(X) unchanged."
    expected: "Qxf2 ranks #1; Nb5 and Rxf2 do not top the list; practicalScore badge value is unchanged from pre-phase behavior for each move."
    why_human: "Requires a live browser session against real Maia/Stockfish worker output on /analysis; the committed unit tests use illustrative fixture priors/values (real FENs were never recovered per 159-RESEARCH.md Open Question 1), so this is the first check against the ACTUAL position."
  - test: "D-03 @1000 live case: at the position where Qb8 was a ~5%-prior tail move outside the plotted Maia chart set, confirm Qb8 does NOT top the FlawChess ranking at ELO 1000."
    expected: "Qb8 is not rankedLines[0]."
    why_human: "Same as above — real Maia distribution, not a fixture."
  - test: "Slider composition: on /analysis, drag the 'Play style' slider toward 'More human' (T>1); confirm the FlawChess ranking visibly reshapes (more-human moves gain), the numeric value updates, and the Maia 'Moves by Rating' chart continues to show RAW (unreshaped) Maia data. Return the slider to center and confirm it reads exactly 1.0 with the ranking matching the untouched default."
    expected: "Ranking changes with temperature; chart stays raw; center reads 1.0 exactly and matches default-temperature output."
    why_human: "Requires driving a real search re-run and visually comparing two live UI panels (ranking vs. chart); the P_REF_ANCHORS (findability.ts) and ROOT_CANDIDATE_HARD_CAP (policyTemperature.ts, =15) constants are both explicitly flagged in-code as unvalidated hypotheses pending this exact check."
  - test: "Verdict copy non-contradiction: find a safe-tier position where the FC pick is genuinely more findable and inside the plotted Maia chart set — confirm the verdict prose says 'far easier to find and play'. Find a safe-tier position where the FC pick is NOT in the plotted set (or below FINDABILITY_MARGIN) — confirm the fallback wording renders ('safer follow-ups' phrasing) with NO findability claim."
    expected: "Prose never asserts findability ease for a pick the chart shows as rare/absent."
    why_human: "Requires locating both qualifying live positions and visually cross-checking the rendered prose against the rendered Maia chart — this is exactly the self-contradiction defect Plan 02 fixes, and the plan's own verification defers the live check to this UAT."
  - test: "Mobile parity: repeat the slider-composition check (test 3) in the mobile Human tab (narrow viewport) — confirm the temperature slider is present, functional, and reshapes the ranking there too."
    expected: "Slider renders and functions identically in the mobile Human tab."
    why_human: "Structural code inspection confirms a single shared `eloSelector` JSX const is rendered at both the mobile humanTab (Analysis.tsx:1657) and desktop human-column (Analysis.tsx:1837) sites, which strongly implies parity — but actual rendering/interaction on a narrow viewport has not been visually driven."
---

# Phase 159: FlawChess Engine policy temperature + root-move findability Verification Report

**Phase Goal:** The FlawChess Engine recommends the best move the user will *plausibly find* ("best you'll likely find", not "best if you can find it"). Thread B (committed real fix): fold `P_you(X)` into the root ranking via a findability floor/soft weighting, auto-scaled by ELO, so a ~5%-findable tail move can no longer top the list while `V(X)` stays untouched, without collapsing into raw `P·V` ranking. Thread A (complementary knob): a Maia policy-temperature UI slider below the ELO slider, composing with the findability weighting via the temperature-adjusted distribution. Ride-along: the agreement-verdict "far easier to find and play" copy is gated on the pick's actual Maia probability so it can never contradict the Maia chart beneath it.

**Verified:** 2026-07-07T21:06:10Z
**Status:** passed (human verification completed 2026-07-08 — all 5 UAT items passed; see 159-UAT.md)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All 13 must-have truths declared across the phase's 4 plans (159-01 through 159-04 PLAN.md frontmatter) were checked against the actual source, not just the SUMMARY narrative.

| # | Truth (condensed) | Status | Evidence |
|---|---|---|---|
| 1 | Root ranking sorts by saturating `rankScore = min(1, P_you/P_ref(elo)) * V(X)`, root-only, `V(X)`/`practicalScore` byte-identical | ✓ VERIFIED | `findability.ts:73-76` (`rankScore`); `treeCommon.ts:185-210` (`buildRankedLines` — `sortRankScore` is a parallel local, `line.practicalScore: child.value` untouched); confirmed via real end-to-end `mctsSearch`/`fallbackExpectimax` test (`mctsSearch.test.ts:390-421`) proving `practicalScore` is unchanged while order flips |
| 2 | `P_ref(ELO)` monotonically decreases 600→2600; any move at/above `P_ref` saturates to factor 1 (greedy `P·V` engine impossible by construction) | ✓ VERIFIED | `findability.ts:32-63` (`P_REF_ANCHORS`, `pRefForElo`); unit tests assert monotonicity + strict saturation equality (`findability.test.ts:29-61`) |
| 3 | Three D-03 regression cases pass through `buildRankedLines`: Nb5@600 (5%) doesn't top; Qxf2@600 (9%) beats both Nb5 and Rxf2 (57%, Mistake); Qb8@1000 (~5% tail) doesn't top | ✓ VERIFIED (unit-fixture level) / see human-check below for the real-FEN case | `findability.test.ts:83-115` — passes, but fixture prior/V values are explicitly documented as *illustrative approximations*, not the real recovered FENs (Open Question 1 was never resolved) |
| 4 | Canonical ascending-UCI tie-break preserved; both runners produce identical findability-aware order via the single `buildRankedLines` seam | ✓ VERIFIED | `treeCommon.ts:207` (`a.line.rootMove < b.line.rootMove`); `fallbackExpectimax.test.ts` cross-runner identical-order assertion (per SUMMARY, confirmed passing in the 106-test run) |
| 5 | Findability-claim gate fires only when both raw-Maia-probability AND plotted-set conditions hold (D-10); D-11 fallback renders otherwise | ✓ VERIFIED | `flawChessVerdict.ts:157-164` (`computeFindabilityGate`); `FlawChessAgreementVerdict.tsx:180-186` (`closingClause` branches on `findabilityOk`); tests assert both branches render the correct phrase and never both (`FlawChessAgreementVerdict.test.tsx:122-172`) |
| 6 | Gate reads RAW Maia probability (same distribution the chart displays) — structurally cannot read the temperature-adjusted search-internal prior | ✓ VERIFIED | `flawChessVerdict.ts` imports nothing from `lib/engine` beyond `RankedLine` type (grep-confirmed); `RankedLine` (types.ts:50-61) has no `prior` field |
| 7 | `rawProbBySan`/`shownSans` computed ONCE in Analysis.tsx, passed as props; verdict component never calls `nearestByElo` independently | ✓ VERIFIED | `Analysis.tsx:703-706` (single memo); `FlawChessAgreementVerdict.tsx` has no `nearestByElo` import (grep-confirmed) |
| 8 | Policy-temperature transform (`p^(1/T)` renormalized) applied ONLY on root-mover's side, BEFORE truncation; T=1 is a true bit-identical no-op | ✓ VERIFIED | `policyTemperature.ts:57-69`; `mctsSearch.ts:304-308`, `fallbackExpectimax.ts:174-178` (`sideMatchesMover(...) && temperature !== DEFAULT_POLICY_TEMPERATURE` short-circuit); no-op regression test passes (`mctsSearch.test.ts:424-440`, snapshotA===snapshotB) |
| 9 | Temperature-adjusted distribution feeds BOTH the search policy AND (via `child.prior`) the findability `P_you` — composes automatically, no third combiner | ✓ VERIFIED | `treeCommon.ts` comment + code: `child.prior` set post-truncation, read directly by `rankScore`; D-06 composition test flips the low-ELO winner from T=1 to T=2 purely via `child.prior` (`mctsSearch.test.ts:500-520`) |
| 10 | Both `SearchRunner`s apply the identical transform via shared helpers; named root-candidate hard cap guards pathological flatness | ✓ VERIFIED | `sideMatchesMover`/`applyRootCandidateHardCap` both live in `treeCommon.ts` (shared, not duplicated) and are called identically in `mctsSearch.ts` and `fallbackExpectimax.ts` (grep-confirmed at matching line patterns) |
| 11 | Temperature slider renders below ELO slider in BOTH mobile Human tab and desktop human column, plain-language D-09 copy, testid/aria-label/thumbLabels | ✓ VERIFIED | `TemperatureSelector.tsx` (component); single shared `eloSelector` const (`Analysis.tsx:1644-1649`) rendered at both `{eloSelector}` sites (`Analysis.tsx:1673`, `Analysis.tsx:1852`) |
| 12 | Slider is log-symmetric 0.5–2.0, exact center=1.0 (strict), session-only state (no persistence) | ✓ VERIFIED | `TemperatureSelector.tsx:38,48-58` (`TEMPERATURE_DEFAULT = DEFAULT_POLICY_TEMPERATURE`, matching `2**x`/`log2` bases); `TemperatureSelector.test.tsx` strict `=== 1` assertions (per SUMMARY); `Analysis.tsx:538` plain `useState`, no localStorage/URL |
| 13 | Selected temperature threads through `useFlawChessEngine` into `SearchBudget.policyTemperature`, defaulted at the call site, re-runs search on change; Maia chart stays raw | ✓ VERIFIED | `useFlawChessEngine.ts:232` (`policyTemperature: policyTemperature ?? DEFAULT_POLICY_TEMPERATURE`), `useFlawChessEngine.ts:257` (effect deps include `policyTemperature`); Maia chart consumes `maia.perElo` via `nearestByElo`, an entirely separate hook (`useMaiaEngine`) untouched by this phase |

**Score:** 13/13 truths verified at the code/unit-test level (0 present-but-behavior-unverified — the composition and no-op invariants ARE exercised by real end-to-end `mctsSearch`/`fallbackExpectimax` test runs, not mere fixture-level `rankScore` calls).

**Important caveat carried into Human Verification:** truth #3 (the three D-03 regression cases) is verified only against *illustrative* fixture values, by the plan's own explicit admission — the real FENs from the SEED-085 discussion were never recovered this session. The plan itself designed this gap to be closed by a blocking live UAT checkpoint in 159-04's `<human-check>` block, which per `human_verify_mode=end-of-phase` was deliberately deferred rather than run inline. That live check has NOT yet been performed (confirmed: no `159-UAT.md` exists yet, and 159-04-SUMMARY.md explicitly lists it as "Outstanding"). This is why overall status is `human_needed` rather than `passed` despite a clean 13/13 code-level score.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/lib/engine/findability.ts` | `P_REF_ANCHORS`, `pRefForElo`, `rankScore` | ✓ VERIFIED | All three exported, tested, wired into `treeCommon.ts` |
| `frontend/src/lib/engine/__tests__/findability.test.ts` | pRefForElo shape + rankScore saturation + D-03 cases | ✓ VERIFIED | 10 tests, all pass |
| `frontend/src/lib/engine/policyTemperature.ts` | `DEFAULT_POLICY_TEMPERATURE`, `applyPolicyTemperature`, `ROOT_CANDIDATE_HARD_CAP` | ✓ VERIFIED | All three exported, tested |
| `frontend/src/lib/engine/treeCommon.ts` (edited) | `rootElo`-threaded `buildRankedLines`/`buildSnapshot`, `sideMatchesMover`, `applyRootCandidateHardCap` | ✓ VERIFIED | All present, tested |
| `frontend/src/lib/flawChessVerdict.ts` (edited) | `FINDABILITY_MARGIN`, `computeFindabilityGate` | ✓ VERIFIED | Both exported, tested, no new `lib/engine` import beyond `RankedLine` type |
| `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` (edited) | gate wired, D-11 fallback prose | ✓ VERIFIED | `findabilityOk` computed and threaded into `renderVerdictSentence` |
| `frontend/src/components/analysis/TemperatureSelector.tsx` | log-symmetric slider component + mapping helpers | ✓ VERIFIED | All exports present, 13 tests pass |
| `frontend/src/hooks/useFlawChessEngine.ts` (edited) | `policyTemperature` option on `SearchBudget`, effect deps | ✓ VERIFIED | Present, existing hook tests unaffected |
| `frontend/src/pages/Analysis.tsx` (edited) | session temperature state, dual-layout slider render, `rawProbBySan`/`shownSans` props | ✓ VERIFIED | Single shared render site used at both layouts |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `mctsSearch.ts`/`fallbackExpectimax.ts` `buildSnapshot` call sites | `treeCommon.ts` `buildRankedLines` | `rootElo = budget.elo[root.side]` | ✓ WIRED | Confirmed at all 4 call sites (2 per runner) |
| `dispatchExpansion`/`expandNode` | `policyTemperature.ts` `applyPolicyTemperature` | `sideMatchesMover(...) && temperature !== DEFAULT_POLICY_TEMPERATURE` guard | ✓ WIRED | Identical guard pattern in both runners |
| `FlawChessAgreementVerdict.tsx` | `flawChessVerdict.ts` `computeFindabilityGate` | `pYouFc/pYouSf` from `rawProbBySan`, `fcInPlottedSet` from `shownSans` | ✓ WIRED | `FlawChessAgreementVerdict.tsx:240-245` |
| `Analysis.tsx` | `FlawChessAgreementVerdict` | `rawProbBySan`/`shownSans` props (computed once) | ✓ WIRED | `Analysis.tsx:703-706`, `1627-1628` |
| `Analysis.tsx` `temperature` state | `useFlawChessEngine` | `policyTemperature: temperature` option | ✓ WIRED | `Analysis.tsx:550` |
| `Analysis.tsx` `eloSelector` const | mobile humanTab + desktop human column | Shared JSX const referenced at 2 render sites | ✓ WIRED | `Analysis.tsx:1644-1649`, used at `1673` and `1852` |

### Data-Flow Trace (Level 4)

The FlawChess ranked-lines list and verdict prose are both driven by real search/Maia output (not static/hardcoded), traced as follows:
- `rankedLines` ← `snapshot.rankedLines` ← `buildRankedLines(root, rootElo)` ← real `child.prior`/`child.value` populated by the live `mctsSearch`/`fallbackExpectimax` run against actual worker-pool/Maia-queue providers (`useFlawChessEngine.ts:234-237`). No static/empty fallback found.
- `rawProbBySan` ← `nearestByElo(maia.perElo, selectedElo)?.moveProbabilities` ← `useMaiaEngine`'s live per-ELO curve fetch, not a stub. FLOWING.
- Temperature ← `temperature` React state ← `TemperatureSelector` `onChange` ← user slider drag; defaults to `TEMPERATURE_DEFAULT` on load (session-only, no persistence). FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Findability re-ordering happens via a REAL `mctsSearch` run (not just a `rankScore` unit call) | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "Phase 159 D-01"` (enumerated via full suite run below) | e2e4 (low prior, high V) demoted below e2e3 at ELO 600; `practicalScore` unchanged | ✓ PASS |
| Temperature no-op short-circuit is bit-identical | `mctsSearch.test.ts` "omitting policyTemperature behaves identically to the default" | `snapshotB.rankedLines` deep-equals `snapshotA.rankedLines` | ✓ PASS |
| Composition (D-06): T=2 flips the findability winner via `child.prior` alone | `mctsSearch.test.ts` "Phase 159 policy temperature" describe block | e2e4 wins at T=2, loses at T=1, same fixture | ✓ PASS |
| Opponent-side untouched (D-05) | `mctsSearch.test.ts` exact-`candidateUcis`-at-`grade()` assertion | opponent candidate count stays truncated (2), root-mover side flattens (4) | ✓ PASS |
| Full targeted suite for this phase | `cd frontend && npx vitest run <8 phase-159 test files>` | 8 files, 106 tests, all pass | ✓ PASS |
| Type check | `cd frontend && npx tsc -b` | zero errors | ✓ PASS |
| Dead-export check | `cd frontend && npm run knip` | clean, no output | ✓ PASS |

Live-browser D-03 real-FEN cases and the verdict-copy-vs-chart visual cross-check are NOT run here (see Human Verification).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SEED-085 | 159-01, 159-02, 159-03, 159-04 | Threads A+B + verdict-copy consistency fix, all committed | ✓ SATISFIED (code-level) | All 13 must-have truths verified; sole traceability anchor is the seed file (`.planning/seeds/SEED-085-engine-policy-temperature-and-low-elo-realism.md`), confirmed NOT present in `.planning/REQUIREMENTS.md` — matches the phase's own documented note that SEED-085 is its sole anchor, not orphaned |

No orphaned requirements found: REQUIREMENTS.md maps nothing else to Phase 159.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | No TBD/FIXME/XXX/TODO/HACK debt markers found in any of the 11 modified/created source files | — | Clean |
| `frontend/src/lib/engine/types.ts:71` / `frontend/src/hooks/useFlawChessEngine.ts:71-72` | doc comment | `RankedLine`/`rankedLines` doc still says "pre-sorted descending by `practicalScore`" — now inaccurate; ranking is by findability-weighted `rankScore`, so `rankedLines[0]` can have a lower `practicalScore` than `rankedLines[1]` | ⚠️ WARNING (per 159-REVIEW.md WR-01) | Cosmetic/documentation-accuracy issue on a file explicitly marked "frozen contract"; also causes `FlawChessEngineLines.tsx`'s gold badge shading (labeled "by practical rank") to visually appear out of numeric order. Does not break the phase's own declared must-haves (none of which specify badge-shade semantics), but is a real drift a future consumer could trust incorrectly. Recommend a small follow-up fix (update 2 doc comments + 1 badge-shade label/aria string). |
| `frontend/src/lib/engine/findability.ts` docstring vs. `treeCommon.ts:202` call site | — | `P_REF_ANCHORS`/`pRefForElo` docstring frames `P_ref` in raw-Maia-probability terms, but `rankScore` is actually fed `child.prior` — the RENORMALIZED post-truncation prior, which is systematically inflated relative to raw probability (more so at high temperature) | ⚠️ WARNING (per 159-REVIEW.md WR-02) | Findability suppression is likely weaker in practice than the anchor curve's raw-probability framing implies. This directly affects how the pending live UAT (D-03 real-FEN cases) should be interpreted — if the UAT shows Nb5/Qb8 still ranking too high, the anchors need to be retuned in RENORMALIZED-prior space, not raw-probability space, or `rankScore` should be fed raw probability instead. Flagging this explicitly for whoever runs the deferred human-check. |

Both warnings are advisory/calibration-accuracy findings from the independent code review (159-REVIEW.md, 0 critical / 2 warning / 3 info), not violations of any of the phase's own declared must-haves — they do not block the `human_needed` → UAT path but should inform it.

## Human Verification Required

5 items, all harvested from 159-04-PLAN.md's `<verify><human-check>` block (deliberately deferred to end-of-phase UAT per `human_verify_mode=end-of-phase`, confirmed still outstanding — no `159-UAT.md` exists yet and 159-04-SUMMARY.md explicitly lists this as unresolved). See frontmatter `human_verification` for full detail. Summary:

1. **D-03 @600 live case** — Qxf2 tops the ranking over Nb5/Rxf2 at a real 600-ELO position.
2. **D-03 @1000 live case** — Qb8 does not top the ranking at a real 1000-ELO position.
3. **Slider composition** — dragging temperature reshapes the FlawChess ranking while the Maia chart stays raw; center reads exactly 1.0.
4. **Verdict copy non-contradiction** — the findability claim and its fallback each render in the position type they're designed for, never contradicting the chart.
5. **Mobile parity** — the slider is present and functional in the mobile Human tab (narrow viewport).

When running this UAT, also validate/retune `P_REF_ANCHORS` (findability.ts) and `ROOT_CANDIDATE_HARD_CAP` (policyTemperature.ts) against real observed behavior per the code's own explicit "hypothesis, not proven fact" framing — and take WR-02 above into account (the anchors may need to be recalibrated in renormalized-prior space, not raw-probability space).

## Gaps Summary

No code-level gaps. Every declared must-have truth across all 4 plans is backed by real source code, wired through both search runners, and covered by passing unit and integration-style tests (including tests that exercise real `mctsSearch`/`fallbackExpectimax` runs, not just isolated pure-function calls). `tsc -b`, `npm run lint`, and `npm run knip` are all clean; no debt markers were introduced.

The phase cannot be marked fully `passed` because its own plan (159-04) explicitly designed a blocking live-UAT checkpoint — the three D-03 regression cases against REAL Maia/Stockfish output, the slider/chart composition check, the verdict-copy-vs-chart cross-check, and mobile parity — that was deliberately deferred to end-of-phase and has not yet been executed. This is not a code gap; it is the planned, not-yet-run verification step the phase itself calls out as necessary before the `P_REF_ANCHORS`/`FINDABILITY_MARGIN`/`ROOT_CANDIDATE_HARD_CAP` constants can be considered validated rather than hypothesized.

---

_Verified: 2026-07-07T21:06:10Z_
_Verifier: Claude (gsd-verifier)_
