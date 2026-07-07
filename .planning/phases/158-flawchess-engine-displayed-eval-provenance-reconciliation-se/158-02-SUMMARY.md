---
phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se
plan: 02
subsystem: ui
tags: [typescript, chess, engine, eval, react-free-lib]

# Dependency graph
requires:
  - phase: 158-01
    provides: grading-run budget (movetime=4000ms, no depth clause) and searchmoves clause-order fix that the shared gradeMap this module reads is built with
provides:
  - "engineEvalLookup.ts: buildEvalLookup(pvLines, gradeMapBySan, baseFen) -> Map<string, MoveGrade>, UCI-keyed, free-run-first precedence"
  - "getByUci/getBySan accessors resolving a move's eval by identity regardless of which search (free run vs grading run) produced it"
  - "Structural exclusion of the MCTS pool grade as a display source (no pool-grade parameter exists on this module)"
affects: [158-03 (Analysis.tsx wiring — consumes buildEvalLookup/getByUci/getBySan to replace ad-hoc per-source eval reads)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure eval-lookup merge module: two ordered insertion loops with !lookup.has(key) guards implement source-precedence without a priority field or sort"
    - "SAN<->UCI conversion always delegates to sanToUci (@/lib/sanToSquares), never re-implemented per-consumer"

key-files:
  created:
    - frontend/src/lib/engineEvalLookup.ts
    - frontend/src/lib/engineEvalLookup.test.ts
  modified: []

key-decisions:
  - "buildEvalLookup takes exactly 3 params (pvLines, gradeMapBySan, baseFen) — no pool-grade parameter, making a shallow MCTS pool eval structurally impossible to surface through this lookup (CONTEXT.md LOCKED)"
  - "Both merge loops (free-run first, then grading) use !lookup.has(key) as the sole precedence mechanism — no explicit source-priority enum or sort needed"

patterns-established:
  - "Pure lookup-merge modules for the /analysis page live alongside moveQuality.ts/flawChessVerdict.ts as flat frontend/src/lib/*.ts files with *.test.ts siblings (not __tests__/), reusing MoveGrade/PvLine types rather than redeclaring"

requirements-completed: [SEED-087]

coverage:
  - id: D1
    description: "buildEvalLookup merges free-run pvLines and SAN-keyed gradeMapBySan into one UCI-keyed Map<string, MoveGrade>, with a move present in both sources resolving to the free-run value"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — free-run-first precedence (SEED-087 SC1) > a move present in BOTH pvLines and gradeMap resolves to the free-run value"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — free-run-first precedence (SEED-087 SC1) > precedence never regresses"
        status: pass
    human_judgment: false
  - id: D2
    description: "A move present only in the SAN-keyed gradeMap resolves via sanToUci conversion under its UCI key; an unresolvable SAN is skipped without throwing"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — gradeMap-only moves resolved via sanToUci > a move present ONLY in gradeMapBySan converts via sanToUci and is inserted under its UCI key"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — gradeMap-only moves resolved via sanToUci > a SAN in gradeMapBySan that sanToUci cannot resolve is skipped, no throw"
        status: pass
    human_judgment: false
  - id: D3
    description: "A move in neither source resolves to null via getByUci/getBySan — there is no pool-grade fallback parameter"
    requirement: "SEED-087"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#buildEvalLookup — no pool-grade fallback > a UCI in neither source resolves to null"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engineEvalLookup.test.ts#getBySan > an unresolvable SAN returns null, not a throw"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-07
status: complete
---

# Phase 158 Plan 02: FlawChess Engine Eval Lookup Summary

**Pure UCI-keyed eval-lookup module (`buildEvalLookup`/`getByUci`/`getBySan`) merging the free-run's `pvLines` and the grading-run's SAN-keyed `gradeMap` with strict free-run-first precedence, structurally excluding the MCTS pool grade as a display source**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-07T19:19:00Z (approx)
- **Completed:** 2026-07-07T19:33:19Z
- **Tasks:** 1 (TDD: RED then GREEN)
- **Files modified:** 2 (both new)

## Accomplishments
- `engineEvalLookup.ts` merges the authoritative free run's UCI-keyed `pvLines` and the shared grading run's SAN-keyed `gradeMap` into one `Map<string, MoveGrade>`, with the free-run loop running first and both loops guarded by `!lookup.has(key)` so a grading entry can never overwrite a free-run entry.
- Resolves the UCI/SAN key-space mismatch (RESEARCH Pitfall 1) by converting every grade-map SAN through `sanToUci(baseFen, san)` before insertion — no naive-compare silent drop.
- `getByUci`/`getBySan` give display sites a single move-identity-based accessor pair instead of reading from whichever source happened to produce the eval.
- No pool-grade parameter exists on `buildEvalLookup` at all (3-arg signature: `pvLines`, `gradeMapBySan`, `baseFen`) — the MCTS pool's `objectiveEvalCp` cannot be plumbed through this module even accidentally, satisfying CONTEXT.md's LOCKED structural-exclusion requirement.

## Task Commits

Each task was committed atomically (TDD RED then GREEN):

1. **Task 1 RED: failing tests** - `693dd296` (test)
2. **Task 1 GREEN: implementation** - `6f263c13` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/lib/engineEvalLookup.ts` - `buildEvalLookup`/`getByUci`/`getBySan`, pure module, no I/O, no pool-grade parameter
- `frontend/src/lib/engineEvalLookup.test.ts` - 7 vitest unit tests covering every `<behavior>` bullet, no jsdom/worker

## Decisions Made
- No new decisions beyond what the plan specified — the plan's exact 3-loop-guard design (`!lookup.has(uci)` on both merge loops) was implemented verbatim, so no `state add-decision` entry was needed beyond what's captured in `key-decisions` above.

## Deviations from Plan

None - plan executed exactly as written. TDD RED confirmed the module didn't exist (import error), GREEN made all 7 tests pass on the first implementation attempt.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `buildEvalLookup`/`getByUci`/`getBySan` are ready for plan 158-03 to wire into `Analysis.tsx`, replacing whatever ad-hoc per-source eval reads currently exist on the `/analysis` page.
- `npm run knip`'s "no new dead export" acceptance criterion is deferred to the wave-2 merge (per plan's own note) since these three exports are only consumed starting in 158-03 — expected, not a gap.
- `npx tsc -b` is clean at this plan's boundary; no cross-plan type drift introduced.

---
*Phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engineEvalLookup.ts
- FOUND: frontend/src/lib/engineEvalLookup.test.ts
- FOUND: 693dd296 (test commit)
- FOUND: 6f263c13 (feat commit)
