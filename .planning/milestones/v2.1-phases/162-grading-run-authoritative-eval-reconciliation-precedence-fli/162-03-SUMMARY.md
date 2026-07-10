---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
plan: 03
subsystem: ui
tags: [react, typescript, stockfish, chess-eval, sigmoid]

# Dependency graph
requires:
  - phase: 162-01
    provides: buildEvalLookup flipped to grading-first precedence, resolveReconciledBest(evalLookup, candidateUcis, mover, tieBreakUci)
  - phase: 162-02
    provides: reconciledBestUci — the single canonical reconciled-argmax memo in Analysis.tsx
provides:
  - The green SF board arrow follows the TRUE global reconciled argmax (reconciledBestUci), not engine.pvLines[i] (D-07/D-12)
  - FlawChessAgreementVerdict's stockfishLine is a new reconciledStockfishLine memo (reconciled argmax + its eval), not raw engine.pvLines[0] (D-13)
  - useGameOverlay's off-main-line eval-bar passthrough params are sourced from a new reconciledBestEval memo, not raw engine.evalCp/evalMate/depth (D-08)
  - The Stockfish card's pvLines (desktop + mobile) are re-sourced through evalLookup and re-sorted via a new reconciledPvLines memo (D-04); the depth label stays free-run (D-05)
affects: [any future Analysis.tsx display consumer of Stockfish evals — must thread through evalLookup/reconciledBestUci, never re-derive]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single canonical reconciledBestUci memo (from 162-02) reused by every remaining display consumer (arrow, verdict, eval bar, card) via small per-consumer derived memos (reconciledStockfishLine, reconciledBestEval, reconciledPvLines) — never a fresh argmax re-derivation per call site"
    - "Caller-side-only reconciliation: useGameOverlay's own internals are untouched; only the params Analysis.tsx passes in (engineEvalCp/Mate/Depth) changed source, proven by an explicit zero-diff assertion on the hook file itself"

key-files:
  created: []
  modified:
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/hooks/__tests__/useGameOverlay.test.ts

key-decisions:
  - "Tasks 1+2 combined into one commit — the reconciled memo chain is interleaved in Analysis.tsx (reconciledStockfishLine sits directly beside reconciledBestEval, both threaded from the same reconciledBestUci), mirroring the established 155-04/158-03 precedent for combining tasks whose memos aren't cleanly separable in the same file"
  - "reconciledStockfishLine returns null (not a free-run fallback object) when reconciledBestUci is null — the fallback to engine.pvLines[0] lives at the JSX call site (stockfishLine={reconciledStockfishLine ?? (engine.pvLines[0] ?? null)}) so first paint still shows a value, while the verdict's own D-06 gating stays the single source of truth for 'nothing to show yet'"
  - "reconciledBestEval falls back to the raw free-run {evalCp, evalMate, depth} object when reconciledBestUci is null (pre-grading, or gradingEnabled false) — a natural lookup fallback requiring no special-casing, since resolveReconciledBest only ever returns a UCI present in evalLookup"
  - "reconciledPvLines keeps each line's own free-run eval when its root move hasn't resolved through evalLookup yet (a no-op pre-grading fallback), mirroring buildEvalLookup's free-run-fills-gaps precedent, rather than blanking the eval"
  - "Arrow-follows-reconciled-argmax test verified via SVG path-string diffing (baseline vs reconciled render) rather than decoding exact arrow geometry — jsdom's default 0 clientWidth degenerates ArrowOverlay's paths to NaN, so a scoped Element.prototype.clientWidth spy (restored in a finally block) forces real geometry without needing to duplicate ChessBoard's private arrow-shape constants in the test"

patterns-established:
  - "When jsdom's default 0-size layout blocks a DOM-geometry assertion (e.g. SVG arrow paths), prefer a scoped clientWidth spy + before/after path-string diff over either skipping the assertion or duplicating the component's private geometry constants in the test"

requirements-completed: [D-04, D-05, D-06, D-07, D-08, D-12, D-13]

coverage:
  - id: D1
    description: "The green Stockfish board arrow targets the reconciled-argmax UCI (which may be a move outside the Stockfish card's own top-2), falling back to the free run's own top line before grading has produced a reconciled best (D-07/D-12)"
    requirement: D-07
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Reconciled eval provenance (Phase 158, SEED-087) > the sf-0 board arrow follows the reconciled-argmax square, not the free run's own pick, when a Maia/FC-only candidate is the global argmax (D-12)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The agreement verdict's Stockfish side names the reconciled-argmax move with its reconciled eval (not raw engine.pvLines[0]); a move graded differently by the free run and the grading run shows the grading value in the sentence"
    requirement: D-13
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Reconciled eval provenance (Phase 158, SEED-087) > shows the grading (reconciled) value for the verdict's Stockfish side even when the SAME move is graded differently by the two sources (Phase 162 D-13 provenance)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Off the main line, useGameOverlay's engine-passthrough eval bar surfaces the caller-supplied (reconciled) engineEvalCp/Mate/Depth unchanged; on the main line the precomputed game eval still wins, ignoring the passthrough params (D-08); useGameOverlay.ts itself has zero diff (caller-side change only)"
    requirement: D-08
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useGameOverlay.test.ts#useGameOverlay eval-bar passthrough (off main line, Phase 162 D-08) > surfaces the caller-supplied engineEvalCp/Mate/Depth unchanged off the main line"
        status: pass
      - kind: other
        ref: "git diff --quiet frontend/src/hooks/useGameOverlay.ts (exit 0 — zero diff)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Stockfish card's two lines (desktop + mobile) display reconciled evals and are re-ordered by reconciled expected score, via a single reconciledPvLines memo passed to both EngineLines call sites; the header depth label stays engine.depth (D-05, unchanged)"
    requirement: D-04, D-05
    verification:
      - kind: other
        ref: "grep -n reconciledPvLines frontend/src/pages/Analysis.tsx (2 prop matches: desktop + mobile EngineLines); grep -n 'Depth ${engine.depth}' confirms the label is untouched"
        status: pass
      - kind: automated_ui
        ref: "npx vitest run src/pages/__tests__/Analysis.test.tsx (all pre-existing card/label assertions still pass)"
        status: pass
    human_judgment: false

# Metrics
duration: 22min
completed: 2026-07-10
status: complete
---

# Phase 162 Plan 03: Grading-run-authoritative eval reconciliation — final display-consumer wiring Summary

**Threaded the single canonical `reconciledBestUci` argmax into the last four display consumers — the SF board arrow, the agreement verdict's Stockfish side, the off-main-line eval bar (via `useGameOverlay`), and the Stockfish card's two PV lines — closing the two call sites (`stockfishLine` and `useGameOverlay`'s eval passthrough) that bypassed `evalLookup` entirely and would otherwise silently reintroduce the free-run-first bug this phase exists to kill.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-10T10:41:00Z (approx)
- **Completed:** 2026-07-10T10:49:17Z (approx)
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `engineArrows`' SF branch now resolves `reconciledBestUci ?? engine.pvLines[i]?.moves[0] ?? null` instead of reading `engine.pvLines[i]` raw — the green arrow follows the TRUE global reconciled argmax, which may target a move outside the Stockfish card's own top-2 (accepted D-12 edge case), falling back to the free run's own top line before grading lands (no regression on first paint).
- New `reconciledStockfishLine` memo builds a `PvLine`-shaped object from `reconciledBestUci` + `getByUci(evalLookup, reconciledBestUci)`, fed to `FlawChessAgreementVerdict`'s `stockfishLine` prop in place of raw `engine.pvLines[0]` (D-13) — this call site previously bypassed `evalLookup` entirely (RESEARCH Pitfall 1), a coverage gap that survived even the old free-run-first precedence. Falls back to `engine.pvLines[0]` pre-grading so first paint still resolves.
- New `reconciledBestEval` memo (reconciled eval when `reconciledBestUci` resolves, else the raw free-run `{evalCp, evalMate, depth}`) now feeds `useGameOverlay`'s `engineEvalCp`/`engineEvalMate`/`engineDepth` params — the off-main-line eval bar refines once to the reconciled best's eval when grading lands (D-08), closing RESEARCH Pitfall 1's second bypass. `useGameOverlay.ts` itself is byte-for-byte unchanged (confirmed via `git diff --quiet`).
- New `reconciledPvLines` memo maps `engine.pvLines` through `evalLookup` and re-sorts by reconciled expected score, passed to BOTH the desktop and mobile `EngineLines` (D-04, mobile parity) — the card's line 1 now agrees with the chart's Best crown on near-ties. PV move-sequence text (`moves`) and the header's `Depth ${engine.depth}` label stay sourced from the free run, unchanged (D-05).
- Source C (the MCTS pool grade) stays display-excluded (D-06) — no new code path reads it; verified by inspection, `buildEvalLookup`'s 3-param signature structurally excludes it (per 162-01).

## Task Commits

Tasks 1+2 were committed together (interleaved memo chain — see Decisions Made):

1. **Task 1+2: Thread reconciled-argmax into arrow, verdict, eval bar, card (D-04/05/07/08/12/13)** - `1a2bde4b` (feat)

_Note: both tasks are `tdd="true"` — implementation and test changes for each were verified together (`npx vitest run` confirmed green) before the combined commit._

## Files Created/Modified
- `frontend/src/pages/Analysis.tsx` - `engineArrows` SF branch re-sourced to `reconciledBestUci`; new `reconciledStockfishLine`, `reconciledBestEval`, `reconciledPvLines` memos; verdict `stockfishLine` prop + comment re-sourced; `useGameOverlay` call site's `engineEvalCp/Mate/Depth` re-sourced; desktop + mobile `EngineLines` `pvLines` prop re-sourced; new `PvLine` type import + `evalToExpectedScore` import
- `frontend/src/pages/__tests__/Analysis.test.tsx` - new same-move-different-value verdict provenance test (D-13); new arrow-follows-reconciled-argmax test (D-12, via a scoped `clientWidth` spy + SVG path diff); pre-existing SC4 test updated (Rule 1, see below)
- `frontend/src/hooks/__tests__/useGameOverlay.test.ts` - new off-main-line passthrough describe block (3 tests: cp/mate passthrough, mate-only passthrough, on-main-line precomputed still wins)

## Decisions Made
- Tasks 1+2 combined into one commit — `reconciledStockfishLine` (Task 1) and `reconciledBestEval` (Task 2) sit directly beside each other in the same memo chain derived from `reconciledBestUci`; splitting them into two commits would have required either an artificial partial-file patch or a temporarily-unused-variable lint failure on an intermediate commit. Mirrors the project's own established 155-04/158-03 precedent for exactly this situation.
- `reconciledStockfishLine` returns `null` (not a fallback object) when `reconciledBestUci` is null — the `engine.pvLines[0]` fallback lives at the JSX call site (`stockfishLine={reconciledStockfishLine ?? (engine.pvLines[0] ?? null)}`), keeping the verdict's own D-06 "nothing to show yet" gating as the single source of truth rather than duplicating it inside the memo.
- `reconciledBestEval` falls back to the raw free-run `{evalCp, evalMate, depth}` when `reconciledBestUci` is null — a natural lookup-miss fallback requiring no special-casing for the `gradingEnabled=false` case, since `resolveReconciledBest` only ever returns a UCI that's already present in `evalLookup`.
- `reconciledPvLines` keeps a line's own free-run eval when its root move hasn't resolved through `evalLookup` yet (a no-op pre-grading fallback), mirroring `buildEvalLookup`'s established free-run-fills-gaps precedent rather than blanking the eval to `…`.
- The D-12 arrow test verifies behavior via SVG path-string diffing (baseline render vs. reconciled render, asserting the paths differ) instead of decoding exact arrow endpoint geometry — jsdom performs no real layout, so the default 0 `clientWidth` degenerates `ArrowOverlay`'s computed paths to NaN. A scoped `Element.prototype.clientWidth` spy (restored in a `finally` block) forces real, non-degenerate geometry without needing to duplicate `ChessBoard.tsx`'s private arrow-shape constants (`MIN_SHAFT_WIDTH` etc.) in the test file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a pre-existing test broken by this plan's own D-13 change**
- **Found during:** Task 1 (running the plan's required `npx vitest run src/pages/__tests__/Analysis.test.tsx` verification)
- **Issue:** The existing SC4 test ("the verdict's FC-pick and SF-best evals both resolve through evalLookup...") set `engine.pvLines = [{ moves: ['g1f3'], ... }]` but only graded `'e4'` in `gradingState.gradeMap`. Under this plan's D-13 change, `stockfishLine` is now sourced from `reconciledBestUci` (the reconciled argmax over the grading union), not raw `engine.pvLines[0]` — with only `'e4'` graded, `reconciledBestUci` correctly resolved to `e2e4` instead of the free run's actual top pick `g1f3`, breaking the test's premise (which was about evalLookup resolution, not argmax selection).
- **Fix:** Added a second `gradeMap` entry for `'Nf3'` (matching the free run's own `g1f3` eval of 130) so the reconciled argmax still resolves to the free run's own top pick, restoring the test's original intent (proving the raw inflated `999` RankedLine eval never leaks through) without contradicting D-12's correct new behavior.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** `npx vitest run src/pages/__tests__/Analysis.test.tsx` — 26/26 pass (was 25/26 with 1 failure before the fix).
- **Committed in:** `1a2bde4b` (combined Task 1+2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — a bug fix to a test whose fixture was left inconsistent by this plan's own D-13 precedence change)
**Impact on plan:** Necessary for the plan's own required verification gate to pass; not scope creep — a narrow correction of a test fixture sitting directly adjacent to this plan's diff, following the exact same pattern 162-02 already established for the analogous 162-01 fallout.

## Issues Encountered

Testing the D-12 arrow-provenance case at the DOM level required working around jsdom's lack of real CSS layout: `ChessBoard`'s `ArrowOverlay` computes SVG path geometry from `containerRef.current.clientWidth`, which defaults to 0 in jsdom and produces degenerate `NaN` path strings regardless of which squares an arrow targets. Resolved with a scoped `Element.prototype.clientWidth` spy (returning a fixed 400px for the duration of the test, restored via `finally`) so the overlay computes real, non-degenerate geometry, then asserting the SF arrow's `d` attribute differs between a baseline render (`reconciledBestUci` null, arrow falls back to the free run's own pick) and a reconciled render (`reconciledBestUci` resolves to a different move) — proving the arrow moved without needing to decode or duplicate `ChessBoard.tsx`'s private arrow-shape constants in the test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 162 (all 3 plans) is complete: `buildEvalLookup` is grading-first (162-01), the shared grading union covers the free run's own top-2 (162-02), and every remaining display consumer — arrow, verdict, eval bar, card — now threads through the single canonical `reconciledBestUci`/`evalLookup` (162-03). No further wiring gaps remain per the RESEARCH.md Pitfall 1 call-site audit.
- No blockers. `npx vitest run src/hooks/__tests__/useGameOverlay.test.ts src/pages/__tests__/Analysis.test.tsx` (31/31 pass), `npm test -- --run` (full frontend suite, 1702/1702 pass), `npm run lint` (0 errors), `npx tsc -b` clean, `npm run knip` clean.
- Post-phase manual UAT items (D-10/D-12, from 162-VALIDATION.md, not blocking plan completion) remain for a human to verify live: Best/Good label settling on grading, arrow-outside-card-lines edge case, rapid-navigation orphan-grade check.

---
*Phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/pages/Analysis.tsx
- FOUND: frontend/src/pages/__tests__/Analysis.test.tsx
- FOUND: frontend/src/hooks/__tests__/useGameOverlay.test.ts
- FOUND: 1a2bde4b
