---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
verified: 2026-07-10T11:10:48Z
status: passed
human_verified: 2026-07-10 — all 4 human tests passed (see 162-UAT.md); test 2's initial issue resolved in-phase via D-14 card re-source
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "On /analysis, load a position, watch Best/Good labels and the green Stockfish arrow settle once grading lands (~4s)"
    expected: "No 'Good' labeled move ever shows a higher number than the 'Best' labeled move, at any instant during the settle (D-10 live-argmax-per-snapshot stance — flicker is accepted, contradiction is not)"
    why_human: "Timing/visual perception on a live board (grading arrives asynchronously over ~1.5-4s); not observable via static grep/unit assertions"
  - test: "On the SEED-089 screenshot position, confirm the Stockfish card, FC card prose, and Maia tooltip show identical numbers for the same moves; confirm the arrow may point at a move the Stockfish card doesn't list"
    expected: "Numbers agree across all three surfaces for the same move; the arrow-outside-card-lines case (D-12 accepted edge case) is understood, not a surprise"
    why_human: "Requires a live position where a Maia/FC-only candidate outranks the free run's own top-2; visual cross-surface comparison"
  - test: "Rapid game navigation (arrow-key through several moves quickly) — check for orphaned grades and confirm Stockfish card first paint stays <100ms"
    expected: "No stale-position grade leaks into the new position's display; free-run first paint remains fast"
    why_human: "Timing/perf characteristic on a live worker pool, not statically verifiable"
  - test: "With Maia OFF and FlawChess Engine ON, watch the SF arrow/verdict during the ~1.5-4s window right after the free run's own bestmove commits and the grading union widens to include it"
    expected: "The SF arrow and agreement verdict do not confidently claim 'agreement' with a move that isn't actually the free run's own graded top pick during this window (WR-01, 162-REVIEW.md — code review found a real gap: reconciledBestUci is computed only over grading.gradeMap's keyspace, which can transiently exclude the free run's own committed best when Maia is off, so the verdict/arrow can point at an FC-only candidate while claiming it is Stockfish's objective best)"
    why_human: "Narrow, timing-dependent configuration (Maia off + FC on) not covered by the phase's automated test fixtures, which all use fully-covered candidate sets"
---

# Phase 162: Grading-run-authoritative eval reconciliation — precedence flip Verification Report

**Phase Goal:** Every per-move eval displayed on the analysis page comes from one coherent Stockfish search, so a move labeled "Good" can never show a higher number than the move labeled "Best". Flip `buildEvalLookup` precedence to grading-first (free run only fills not-yet-graded moves), extend `unionSans` with the free run's top-2 root moves so the grading union covers every displayed move by construction, derive Best/Good labels from the reconciled map's own argmax (not the free-run `bestSan` pin), and route the Stockfish card's PV-line evals through the reconciled lookup. Frontend-only; both workers stay as configured today (no depth regression, no new fallback path).
**Verified:** 2026-07-10T11:10:48Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Must-haves merged from all 3 PLAN.md frontmatter blocks (13 truths, tracing to CONTEXT.md decisions D-01..D-13; ROADMAP.md carries no separate structured `success_criteria` list for this phase, its goal prose is the D-01..D-13 decision set per the phase's own tracking convention).

| # | Truth | Req | Status | Evidence |
|---|-------|-----|--------|----------|
| 1 | `buildEvalLookup` resolves a move present in BOTH sources to the grading value, not the free-run value | D-01 | ✓ VERIFIED | `engineEvalLookup.ts:52-56` (gradeMap loop runs first, unconditional set); `engineEvalLookup.test.ts` "grading-first precedence" describe block passes |
| 2 | `buildEvalLookup` still fills not-yet-graded moves from the free run | D-01 | ✓ VERIFIED | `engineEvalLookup.ts:58-62` (`!lookup.has(uci)` guard on the pvLines loop, runs second) |
| 3 | `resolveReconciledBest` returns the UCI with the highest reconciled expected score, tie-break toward the free-run pin | D-03 | ✓ VERIFIED | `engineEvalLookup.ts:95-115`; 5 unit tests incl. mirror-image case, exact-tie, all-absent, single-absent-skip — all pass |
| 4 | Free run's top-2 root SANs join the grading union only after the free run's bestmove commits | D-02, D-09 | ✓ VERIFIED | `Analysis.tsx:797,809-820` (`freeRunCommitted = pvLines.length>0 && !isAnalyzing`, gates `freeRunSans`); integration test at `Analysis.test.tsx:423` passes |
| 5 | A single `reconciledBestUci` is computed once per render over the grading gradeMap keyspace, tie-break toward free-run bestSan | D-03, D-11 | ✓ VERIFIED | `Analysis.tsx:864-872` (candidates from `grading.gradeMap.keys()`, not the broader `unionSans` — Pitfall 3 honored); `bestSan` (line 750) confirmed unchanged/still free-run-derived |
| 6 | Chart labels a move Best iff it is the reconciled argmax, not because it is the free-run bestSan | D-03, D-10 | ✓ VERIFIED | `Analysis.tsx:957-982` (`qualityBySan`'s `designatedBestSan` now sourced from `reconciledBestUci`); behavioral mirror-image test `Analysis.test.tsx:487-517` — Nf3 (reconciled top eval) renders "accurate move", e4 (free-run's own pick) renders "objectively looser" — passes |
| 7 | The green Stockfish best-move arrow targets the true global reconciled argmax, even outside the card's 2 lines | D-07, D-12 | ✓ VERIFIED | `Analysis.tsx:1406` (`reconciledBestUci ?? engine.pvLines[i]?.moves[0] ?? null`); arrow-provenance test `Analysis.test.tsx:588` (SVG path diff) passes — see WR-01 caveat below |
| 8 | The agreement verdict's Stockfish side names the reconciled-argmax move with its reconciled eval, not raw `engine.pvLines[0]` | D-13 | ✓ VERIFIED | `Analysis.tsx:884-894,2000` (`reconciledStockfishLine` fed to `stockfishLine` prop); same-move-different-value provenance test `Analysis.test.tsx:557` passes — see WR-01 caveat below |
| 9 | Off the main line, the eval bar refines once to the reconciled best's eval when grading lands | D-08 | ✓ VERIFIED | `Analysis.tsx:903-906,1118-1120` (`reconciledBestEval` threaded into `useGameOverlay`'s `engineEvalCp/Mate/Depth`); `useGameOverlay.ts` confirmed zero-diff (`git diff --quiet` exit 0 — caller-side only); passthrough unit tests pass |
| 10 | The Stockfish card's two lines read reconciled evals and re-sort by them; headline keeps free-run depth | D-04, D-05 | ✓ VERIFIED | `Analysis.tsx:936-947` (`reconciledPvLines`, re-sorted by expected score, `moves`/`depth` kept from free run); passed to BOTH desktop (`:2078`) and mobile (`:2404`) `EngineLines`; depth label at `:2261`-equivalent still reads `engine.depth` |
| 11 | Source C (MCTS pool grade) stays display-excluded | D-06 | ✓ VERIFIED | `buildEvalLookup`'s 3-param signature structurally excludes a pool-grade parameter (`engineEvalLookup.ts:45-49`); `reconciledRankedLines`/FC hover path reads only `evalLookup` (`Analysis.tsx:915-926`) |
| 12 | All 13 D-01..D-13 requirement IDs are accounted for across the 3 plans | — | ✓ VERIFIED | Plan 01: D-01,D-03; Plan 02: D-02,D-03,D-09,D-10,D-11; Plan 03: D-04,D-05,D-06,D-07,D-08,D-12,D-13 — union covers D-01 through D-13 with no gaps |
| 13 | No debt markers / stub code left in touched files | — | ✓ VERIFIED | `grep -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` on all 5 touched files returns 0 matches |

**Score:** 13/13 truths verified (0 present-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/engineEvalLookup.ts` | grading-first `buildEvalLookup` + exported `resolveReconciledBest` | ✓ VERIFIED | Both present, substantive, unit-tested |
| `frontend/src/lib/engineEvalLookup.test.ts` | grading-first precedence tests + resolveReconciledBest block | ✓ VERIFIED | 12 tests, all pass |
| `frontend/src/pages/Analysis.tsx` | `freeRunCommitted`, `reconciledBestUci`, `reconciledStockfishLine`, `reconciledBestEval`, `reconciledPvLines` memos | ✓ VERIFIED | All 5 present, wired to their consumers (verdict, arrow, useGameOverlay, EngineLines x2, qualityBySan) |
| `frontend/src/pages/__tests__/Analysis.test.tsx` | D-09 gate, D-03 mirror-image, D-12 arrow, D-13 verdict provenance tests | ✓ VERIFIED | All present and pass (26/26 in file) |
| `frontend/src/hooks/__tests__/useGameOverlay.test.ts` | reconciled passthrough coverage on off-main-line branch | ✓ VERIFIED | 3 new tests (cp/mate passthrough, mate-only, on-main-line-still-wins), all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `resolveReconciledBest` | `evalToExpectedScore` (`@/lib/liveFlaw`) | direct import/call | ✓ WIRED | Single sigmoid source reused, not re-derived |
| `buildEvalLookup` | `!lookup.has(uci)` idiom | both loops | ✓ WIRED | Preserved verbatim on both loops per plan constraint |
| `reconciledBestUci` | `grading.gradeMap.keys()` | candidate keyspace | ✓ WIRED | Confirmed NOT `unionSans` (Pitfall 3 honored) |
| `qualityBySan` | `reconciledBestUci` (via `bestSanFromPv`) | `classifyMoveQuality` pin arg | ✓ WIRED | Raw free-run `bestSan` no longer passed as the pin |
| `engineArrows` SF branch | `reconciledBestUci` | fallback chain | ✓ WIRED | `reconciledBestUci ?? engine.pvLines[i]?.moves[0] ?? null` |
| `FlawChessAgreementVerdict.stockfishLine` | `reconciledStockfishLine` | JSX prop | ✓ WIRED | Fallback to `engine.pvLines[0]` pre-grading |
| `useGameOverlay` call site | `reconciledBestEval` | `engineEvalCp/Mate/Depth` params | ✓ WIRED | `useGameOverlay.ts` itself has zero diff (caller-side only, confirmed) |
| `EngineLines` (desktop + mobile) | `reconciledPvLines` | `pvLines` prop | ✓ WIRED | Both call sites confirmed (`:2078`, `:2404`) |
| `MovesByRatingChart.bestSan` (both call sites) | raw `bestSan` (free-run) | `emphasized` stroke calc | ⚠️ NOT RECONCILED | See WR-02 below — this consumer was NOT re-sourced to `reconciledBestUci`; the chart's bold-line "SF pick" emphasis can highlight a different move than the one carrying the reconciled "Best" quality color/label |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 162-01 | Precedence flip | ✓ SATISFIED | Code + tests |
| D-02 | 162-02 | Union extension | ✓ SATISFIED | Code + tests |
| D-03 | 162-01/02 | Best-label rule | ✓ SATISFIED | Code + tests |
| D-04 | 162-03 | Card reads lookup | ✓ SATISFIED | Code, desktop+mobile |
| D-05 | 162-03 | Depth label stays free-run | ✓ SATISFIED | `engine.depth` unchanged at label site |
| D-06 | 162-03 | Source C excluded | ✓ SATISFIED | Structural (no pool-grade param) |
| D-07 | 162-03 | Arrow follows reconciled (practical config caveat) | ✓ SATISFIED (see WR-01) | Code + test; edge-case gap flagged for human review |
| D-08 | 162-03 | Eval bar refine-once | ✓ SATISFIED | Code + tests, `useGameOverlay.ts` zero-diff |
| D-09 | 162-02 | Union-churn restart gate | ✓ SATISFIED | Code + tests |
| D-10 | 162-02 | Live-argmax-per-snapshot, no label pin | ✓ SATISFIED | No `useState`/`useRef` pin introduced (grep-confirmed); flicker itself is human-UAT (see Manual-Only Verifications) |
| D-11 | 162-02 | Anti-circularity (`bestSan` stays free-run-derived) | ✓ SATISFIED | Line 750 confirmed unchanged |
| D-12 | 162-03 | True-global-argmax scope | ✓ SATISFIED (see WR-01) | Code + test; edge-case gap flagged for human review |
| D-13 | 162-03 | Verdict re-sourcing | ✓ SATISFIED (see WR-01) | Code + test; edge-case gap flagged for human review |

No orphaned requirements — REQUIREMENTS.md does not exist for this milestone; CONTEXT.md's D-01..D-13 decision set is the full requirement ledger, and all 13 IDs are claimed and satisfied across the 3 plans.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full targeted suite (3 phase test files) | `npx vitest run src/lib/engineEvalLookup.test.ts src/pages/__tests__/Analysis.test.tsx src/hooks/__tests__/useGameOverlay.test.ts` | 43/43 pass | ✓ PASS |
| Full frontend suite (regression check) | `npm test -- --run` | 1702/1702 pass, 137 files | ✓ PASS |
| Type check | `npx tsc -b` | clean, 0 errors | ✓ PASS |
| Lint | `npm run lint` | 0 errors (3 pre-existing `coverage/` artifact warnings, unrelated) | ✓ PASS |
| `useGameOverlay.ts` caller-side-only claim | `git diff --quiet frontend/src/hooks/useGameOverlay.ts` | exit 0 | ✓ PASS |
| Mirror-image behavioral proof (D-03 core invariant) | `Analysis.test.tsx:487` — Nf3 (higher reconciled eval) renders "accurate move", free-run's own e4 renders "objectively looser" | assertions pass | ✓ PASS |

### Anti-Patterns Found

None blocking. Two code-review WARNINGS (0 critical) independently confirmed by direct code inspection during this verification — carried forward as human-verification items rather than blockers, since neither breaks an explicit PLAN.md must-have and both are narrow/edge-case:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/Analysis.tsx` | 864-872 (consumers at 1406, 2000, 903-906) | `reconciledBestUci`'s candidate set (`grading.gradeMap.keys()`) can transiently exclude the free run's own just-committed best when Maia is off and FlawChess is on, until the grading union re-runs on the widened set (~1.5-4s) | ⚠️ Warning | SF arrow/verdict/eval-bar can transiently name/point at a non-Stockfish-actual-best move as "Stockfish's pick" in that narrow config — confirmed by independent code reading (WR-01, 162-REVIEW.md); not covered by the phase's own test fixtures (all use fully-covered candidate sets) |
| `frontend/src/pages/Analysis.tsx` | 2038, 2306 (consumer: `MovesByRatingChart.tsx:576`) | `MaiaHumanPanel`/`MovesByRatingChart` still receive `bestSan={bestSan}` (raw free-run) for the chart's bold-stroke emphasis, while the SAME chart's quality color/label is `reconciledBestUci`-derived | ⚠️ Warning | In the exact mirror-image scenario the phase's own test proves (Nf3 reconciled-best, e4 free-run-pick), the chart could show a thick "SF pick" stroke on e4 while coloring Nf3 as "Best" — two different moves visually marked "Stockfish says this" on one chart (WR-02, 162-REVIEW.md, confirmed by grep at line 576) |

### Human Verification Required

1. **No number/label contradiction settles correctly**
   **Test:** On `/analysis`, load a position, watch Best/Good labels and the green arrow settle once grading lands (~4s).
   **Expected:** No "Good" move ever shows a higher number than "Best" at any instant (flicker itself is accepted per D-10; a contradiction is not).
   **Why human:** Timing/visual perception on a live board.

2. **Cross-surface number agreement + D-12 accepted edge case**
   **Test:** On the SEED-089 screenshot position, compare Stockfish card, FC card prose, and Maia tooltip numbers for the same moves; confirm the arrow may point outside the card's 2 lines.
   **Expected:** Numbers agree; the divergence is understood, not a surprise.
   **Why human:** Requires a specific live position and visual cross-surface comparison.

3. **Rapid navigation / first-paint perf**
   **Test:** Navigate rapidly through a game's moves.
   **Expected:** No orphaned grades leak across positions; card first paint stays <100ms.
   **Why human:** Timing/perf characteristic of a live worker pool.

4. **WR-01 edge case (Maia off / FlawChess on)**
   **Test:** Toggle Maia off, FlawChess Engine on; watch the SF arrow/verdict in the ~1.5-4s window right after the free run's own bestmove commits.
   **Expected:** The verdict/arrow should not misname a non-Stockfish-actual-best move as Stockfish's objective pick during this window.
   **Why human:** Narrow, timing-dependent config not covered by automated fixtures; code review (162-REVIEW.md WR-01) identified this as a real gap with a proposed one-line fix, not yet applied.

### Gaps Summary

No BLOCKER gaps. All 13 D-01..D-13 must-haves from the 3 PLAN.md frontmatter blocks are implemented, wired, and behaviorally proven by passing tests (43/43 targeted, 1702/1702 full suite, tsc clean, lint clean). The core roadmap invariant — "a move labeled Good can never show a higher number than the move labeled Best" — is directly demonstrated by the mirror-image test (`Analysis.test.tsx:487`), which is the load-bearing behavioral proof for this phase's stated goal.

Two non-blocking WARNINGS from `162-REVIEW.md` were independently re-confirmed by direct code inspection during this verification (not just trusted from the review doc):
- **WR-01** (Maia-off/FC-on transient candidate-set gap affecting arrow/verdict/eval-bar) — a real, narrow, timing-dependent edge case with a proposed fix in the review not yet applied.
- **WR-02** (chart emphasis stroke still keyed to raw `bestSan`, not the reconciled argmax) — a real visual-consistency gap on the same chart the phase targets, also not yet applied.

Additionally, the phase's own `162-VALIDATION.md` "Manual-Only Verifications" section and `162-03-PLAN.md`'s "Post-phase manual UAT" output block explicitly defer 3 live-board checks (label/arrow settle-without-contradiction, cross-surface number agreement, rapid-navigation orphan-grade check) to human UAT — these were never intended to be closed by automated verification and route to `human_needed` per the phase's own validation contract.

**Recommendation:** Given zero blockers and full automated coverage of every explicit must-have, this phase is ready to proceed pending the developer's own live-board UAT pass (items 1-3, pre-planned) and a decision on WR-01/WR-02 (item 4, discovered) — either apply the review's proposed fixes now (both are small, scoped, one-line-ish changes) or explicitly accept them as known residual edge cases before shipping.

---

_Verified: 2026-07-10T11:10:48Z_
_Verifier: Claude (gsd-verifier)_
