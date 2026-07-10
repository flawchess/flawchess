---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
plan: 02
subsystem: frontend-analysis-engine-verdict
tags: [flawchess-engine, verdict-copy, findability-gate, maia]
dependency-graph:
  requires: []
  provides:
    - computeFindabilityGate
    - FINDABILITY_MARGIN
    - "FlawChessAgreementVerdict rawProbBySan/shownSans props"
  affects:
    - frontend/src/lib/flawChessVerdict.ts
    - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
    - frontend/src/pages/Analysis.tsx
tech-stack:
  added: []
  patterns:
    - "Layered pure transforms (select.ts convention): computeFindabilityGate is a standalone, independently-testable pure function, never conflated with computeFlawChessVerdict"
    - "Compute-once-pass-down: raw probability lookup computed exactly once in Analysis.tsx (mirroring the existing shownSans memo) and threaded as props, never re-derived in the consuming component"
key-files:
  created: []
  modified:
    - frontend/src/lib/flawChessVerdict.ts
    - frontend/src/lib/flawChessVerdict.test.ts
    - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
    - frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx
    - frontend/src/pages/Analysis.tsx
decisions:
  - "[Phase 159-02]: rawProbBySan and shownSans made REQUIRED props (not optional) on FlawChessAgreementVerdictProps — Analysis.tsx always has this data available (mirrors the existing required flawChessLine/stockfishLine pattern); all 11 pre-existing component tests updated with the two new props rather than relying on optional defaults"
  - "[Phase 159-02]: D-11 fallback wording is tier-nearlySameEval-aware (two closingClause branches x two gate states = 4 total safe-tier variants), not a single flat fallback string — keeps the existing 'nearly the same eval' vs 'safe practical pick' distinction alive even when the findability claim is suppressed"
  - "[Phase 159-02]: computeFindabilityGate placed in the SAME flawChessVerdict.ts module as computeFlawChessVerdict (not a new file) — it's a small, tightly-scoped pure function that shares the module's existing 'no lib/engine import beyond RankedLine type' structural constraint and doc-comment conventions; a separate file was not warranted"
metrics:
  duration: 14min
  completed: 2026-07-07
status: complete
---

# Phase 159 Plan 02: SEED-085 verdict findability gate Summary

Gated the FlawChess-vs-Stockfish agreement verdict's "far easier to find and play" claim on the FC pick's actual raw Maia probability at the selected ELO, so the prose can never contradict the Maia "Moves by Rating" chart rendered directly beneath it.

## What Was Built

- **`computeFindabilityGate` + `FINDABILITY_MARGIN`** (`flawChessVerdict.ts`) — a pure function returning `true` iff both raw Maia probabilities are non-null, the FC pick's probability exceeds the SF pick's by more than `FINDABILITY_MARGIN` (0.05), AND the FC pick is inside the chart's plotted candidate set. Returns `false` (never throws) on any null input. The module still imports nothing from `lib/engine/` beyond the pre-existing `RankedLine` type — structurally incapable of reading the Phase 159-01 search-internal temperature-adjusted prior (D-12).
- **`FlawChessAgreementVerdict.tsx` wiring** — two new required props, `rawProbBySan: Record<string, number>` and `shownSans: string[]`. The component resolves `pYouFc`/`pYouSf`/`fcInPlottedSet` from these props (with `noUncheckedIndexedAccess`-safe `?? null` narrowing) and calls `computeFindabilityGate`. The safe tier's closing clause now has four variants (gate × `nearlySameEval`), with the two gate-false variants using D-11 fallback wording ("nearly as good an eval, with safer follow-ups." / "a safe, practical pick with safer follow-ups.") that makes no findability claim.
- **`Analysis.tsx` raw-probability wiring** — a new `rawProbBySan` memo computed once via `nearestByElo(maia.perElo, selectedElo)?.moveProbabilities ?? {}`, mirroring the existing `shownSans` memo's dependency shape. Both are passed to the single `FlawChessAgreementVerdict` render site inside the shared `flawChessCard` JSX (confirmed to flow to both the mobile `humanTab` and the desktop human column, since it's one shared const, not duplicated markup).

## Verification

- `npx vitest run src/lib/flawChessVerdict.test.ts src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` — 36/36 passing (22 in flawChessVerdict, including 7 new `computeFindabilityGate` cases; 14 in the component test, including 3 new gate-pass/gate-fail cases; all 11 pre-existing component tests updated with the two new props and still pass unchanged in substance).
- `npx tsc -b` — zero errors.
- `npm run lint` — zero errors (3 pre-existing unrelated `coverage/` warnings only).
- `npm run knip` — exit 0, no dead-export findings (both new exports are consumed).
- Grep-verified: `flawChessVerdict.ts` imports nothing from `@/lib/engine` beyond the pre-existing `import type { RankedLine }`; `FlawChessAgreementVerdict.tsx` never imports `nearestByElo`; `Analysis.tsx` computes `rawProbBySan` via `nearestByElo` exactly once and passes it to the verdict component.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their acceptance criteria without requiring Rule 1/2/3 fixes.

## Threat Flags

None — this plan's threat register items (T-159-03 repudiation, T-159-04 tampering) were both mitigated as designed: the gate reads the same `rawProbBySan` computed once in `Analysis.tsx` (no ELO-rung drift risk), and all `Record` index access uses `?? null` narrowing per `noUncheckedIndexedAccess`. No new network endpoints, auth paths, or trust-boundary-crossing surface was introduced.

## Self-Check: PASSED

- FOUND: frontend/src/lib/flawChessVerdict.ts (computeFindabilityGate, FINDABILITY_MARGIN present)
- FOUND: frontend/src/lib/flawChessVerdict.test.ts (7 new gate tests)
- FOUND: frontend/src/components/analysis/FlawChessAgreementVerdict.tsx (rawProbBySan/shownSans props wired)
- FOUND: frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx (14 tests, 3 new)
- FOUND: frontend/src/pages/Analysis.tsx (rawProbBySan memo + render-site props)
- FOUND commit 4bedfd49 (Task 1: computeFindabilityGate + FINDABILITY_MARGIN)
- FOUND commit 372c55c8 (Task 2: gate wiring + Analysis.tsx props)
