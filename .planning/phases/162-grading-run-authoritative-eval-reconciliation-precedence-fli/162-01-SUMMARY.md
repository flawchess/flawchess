---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
plan: 01
subsystem: ui
tags: [react, typescript, stockfish, chess-eval, sigmoid]

# Dependency graph
requires:
  - phase: 158-flawchess-engine-eval-provenance-reconciliation
    provides: buildEvalLookup (free-run-first), the single UCI-keyed eval lookup for /analysis
provides:
  - buildEvalLookup flipped to grading-first precedence (overlapping moves resolve to the grading value)
  - resolveReconciledBest(evalLookup, candidateUcis, mover, tieBreakUci) — canonical reconciled argmax with tie-break
affects: [162-02, 162-03, Analysis.tsx wiring waves]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Grading-wins-on-overlap, free-run-fills-gaps: insert the higher-precedence source first with an unconditional set, layer the lower-precedence source second guarded by !lookup.has(uci)"
    - "Canonical argmax helper co-located with the Map it resolves against (engineEvalLookup.ts), reused by every downstream display consumer instead of each site re-deriving its own best-move loop"

key-files:
  created: []
  modified:
    - frontend/src/lib/engineEvalLookup.ts
    - frontend/src/lib/engineEvalLookup.test.ts

key-decisions:
  - "Loop reorder only (gradeMapBySan first, pvLines second) — kept the exact !lookup.has(uci) insertion-order-wins guard on both loops verbatim, per 162-PATTERNS.md's load-bearing-idiom instruction"
  - "resolveReconciledBest placed in engineEvalLookup.ts (co-located with buildEvalLookup, already imports MoveGrade) rather than moveQuality.ts, per PATTERNS.md's suggested home"
  - "resolveReconciledBest reuses evalToExpectedScore + MoverColor from @/lib/liveFlaw — no second sigmoid implementation"

patterns-established:
  - "Precedence-flip via loop reorder, not new branching logic — preserves the existing skip-silently-never-throw convention untouched"

requirements-completed: [D-01, D-03]

coverage:
  - id: D1
    description: "buildEvalLookup resolves a move present in BOTH pvLines and gradeMapBySan to the grading value, not the free-run value, while a move present ONLY in pvLines still resolves to the free-run value"
    requirement: D-01
    verification:
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — grading-first precedence (SEED-090, Phase 162 D-01)"
        status: pass
    human_judgment: false
  - id: D2
    description: "resolveReconciledBest returns the UCI with the highest reconciled expected score for the given mover, tie-breaking toward tieBreakUci, skipping candidates absent from the lookup, and returning null when nothing resolves"
    requirement: D-03
    verification:
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#resolveReconciledBest (Phase 162 D-03)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-10
status: complete
---

# Phase 162 Plan 01: Grading-run-authoritative eval reconciliation — pure-lib foundation Summary

**Flipped `buildEvalLookup` to grading-first precedence and added the canonical `resolveReconciledBest` argmax helper, both unit-proven, laying the pure-lib foundation the Wave 2-3 `Analysis.tsx` wiring plans will thread through.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-10T10:07:00Z (approx)
- **Completed:** 2026-07-10T10:19:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `buildEvalLookup` now resolves a move present in both the free run and the grading run to the grading value (the deeper, depth-parity search), while a move present only in the free run still resolves to the free-run placeholder value.
- Module and function docstrings rewritten to describe grading-first precedence, citing SEED-090/Phase 162, with every "free-run-first...LOCKED" statement removed.
- New exported `resolveReconciledBest(evalLookup, candidateUcis, mover, tieBreakUci)` — the single canonical reconciled-best-move resolver every downstream display consumer (arrow, verdict, eval bar, labels) will call instead of re-deriving its own argmax, per the Phase 158 anti-pattern this phase exists to kill.
- 5 new unit tests cover `resolveReconciledBest`'s argmax, the mandatory mirror-image best case (a non-tieBreak UCI with the strictly higher expected score wins), exact-tie tie-break, all-absent-candidates → null, and a single absent candidate being skipped.

## Task Commits

Each task was committed atomically:

1. **Task 1: Flip buildEvalLookup to grading-first precedence (D-01)** - `ddf7e4d8` (feat)
2. **Task 2: Add resolveReconciledBest canonical argmax helper (D-03)** - `47ed3efd` (feat)

_Note: both tasks are `tdd="true"` — implementation and test changes for each task were verified together (tests updated/added, `npx vitest run` confirmed green) before each atomic commit._

## Files Created/Modified
- `frontend/src/lib/engineEvalLookup.ts` - `buildEvalLookup` loop order swapped (grading first, free-run second); docstrings rewritten; new exported `resolveReconciledBest` argmax helper
- `frontend/src/lib/engineEvalLookup.test.ts` - overlap-precedence tests inverted to grading-first; new `describe('resolveReconciledBest ...)` block with 5 cases

## Decisions Made
- Kept the exact `!lookup.has(uci)` insertion-order-wins guard on both loops (only reordered which loop runs first) — the load-bearing idiom per 162-PATTERNS.md, not rewritten as an unconditional overwrite.
- `resolveReconciledBest` co-located in `engineEvalLookup.ts` rather than `moveQuality.ts`, matching the file that already owns the `MoveGrade`-keyed Map it resolves against.
- Reused `evalToExpectedScore`/`MoverColor` from `@/lib/liveFlaw` verbatim — no second sigmoid implementation, no re-derived SAN/UCI converter.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `resolveReconciledBest` and grading-first `buildEvalLookup` are ready for Waves 2-3 to wire into `Analysis.tsx` (`unionSans` extension, `qualityBySan` pin argument, `engineArrows` SF branch, `FlawChessAgreementVerdict` `stockfishLine` prop, `useGameOverlay` passthrough params) per 162-PATTERNS.md.
- No blockers. `npx vitest run src/lib/engineEvalLookup.test.ts` (12/12 pass), `npx tsc -b` clean, `npx eslint` clean on both touched files.

---
*Phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engineEvalLookup.ts
- FOUND: frontend/src/lib/engineEvalLookup.test.ts
- FOUND: ddf7e4d8
- FOUND: 47ed3efd
