---
phase: 182-style-levers
plan: "01"
subsystem: frontend-engine
tags: [flawchess-engine, search-tree, style-levers, ranked-lines]
dependency-graph:
  requires: []
  provides:
    - "RankedLine.childScoreSpread"
    - "computeChildScoreSpread (private treeCommon helper)"
  affects:
    - "buildRankedLines"
    - "future STYLE-04 score-shaping lever (Plan(s) later in Phase 182)"
tech-stack:
  added: []
  patterns:
    - "Additive-optional public-contract field (D-10) — every existing RankedLine consumer stays untouched"
    - "Null-safe variance/spread proxy computed once at buildRankedLines time, never re-derived by consumers"
key-files:
  created: []
  modified:
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/treeCommon.ts
    - frontend/src/lib/engine/__tests__/treeCommon.test.ts
decisions:
  - "Task 1 (types.ts) and Task 2 (treeCommon.ts wiring + tests) committed together as one commit — RankedLine.childScoreSpread is a REQUIRED field (number | null, not optional ?:) per the plan's exact-type acceptance criterion, so adding it to the interface alone breaks tsc -b on treeCommon.ts's existing RankedLine object literal. A standalone Task-1-only commit could not pass its own tsc -b gate. Matches project precedent (Phase 155-04, Phase 158-03: combined interdependent tasks into one commit when a standalone commit wouldn't satisfy its own verification)."
  - "No pre-existing buildRankedLines/buildSnapshot test fixtures existed in treeCommon.test.ts (the plan's read_first pointer assumed some existed) — built a minimal self-referential TestNode fixture (SearchTreeNode<TestNode>) with makeNode/makeRootChild/makeRoot helpers directly in the test file, following the existing fixture style used in backup.test.ts and mctsSearch.test.ts."
  - "The regression case (plan's acceptance criterion: 'at least one pre-existing buildRankedLines/buildSnapshot test remains green') is satisfied by a new test asserting rootMove/practicalScore/visits are computed correctly and unchanged alongside the new field, since no dedicated pre-existing test of that shape existed to keep green as-is."
metrics:
  duration: "~25 min"
  completed: "2026-07-21"
status: complete
---

# Phase 182 Plan 01: RankedLine.childScoreSpread Summary

Added the variance/"sharpness" signal that STYLE-04's Light/Deep-rung score shaping will read: an additive optional `childScoreSpread: number | null` field on `RankedLine`, computed by `buildRankedLines` from the max−min spread of each root candidate's own children's backed-up expected-score values.

## What Was Built

- `frontend/src/lib/engine/types.ts`: `RankedLine` gains `childScoreSpread: number | null`, doc-commented per the file's per-field citation convention — cites D-10, states the exact max−min-of-grandchildren semantic, the 0/1-child null boundary, and the per-`budget.concurrency`-level comparability caveat.
- `frontend/src/lib/engine/treeCommon.ts`: new private `computeChildScoreSpread<N extends SearchTreeNode<N>>(node: N): number | null` helper (null when `node.children.size <= 1`, otherwise `max(child.value) − min(child.value)` over `node.children.values()`), wired into `buildRankedLines`'s `RankedLine` object literal as `childScoreSpread: computeChildScoreSpread(child)`. No other field, sort order, or `practicalScore` assignment touched.
- `frontend/src/lib/engine/__tests__/treeCommon.test.ts`: extended with a `buildRankedLines childScoreSpread` describe block covering: exact multi-grandchild max−min spread; null for a root child with 0 own children; null for a root child with exactly 1 own child (boundary); and a regression case proving `rootMove`/`practicalScore`/`visits` compute correctly and unchanged alongside the new field. New minimal `TestNode`/`makeNode`/`makeRootChild`/`makeRoot` fixture helpers (self-referential `SearchTreeNode<TestNode>`) built inline since no pre-existing node-builder fixture for `buildRankedLines`/`buildSnapshot` existed in this file.

## Verification

- `cd frontend && npx tsc -b --noEmit` — zero errors.
- `cd frontend && npx vitest run src/lib/engine/__tests__/treeCommon.test.ts` — 8/8 passing (4 pre-existing `sideMatchesMover` + 4 new `childScoreSpread` cases).
- `cd frontend && npx vitest run src/lib/engine/` — 196/196 passing across all 14 engine test files (no regression in any existing consumer: `mctsSearch`, `fallbackExpectimax`, `selectBotMove`, `botSampling`, etc.).
- `npm run lint` — 0 errors (3 pre-existing unrelated warnings in `coverage/` generated artifacts).
- Mutation-proof: temporarily reverted the `computeChildScoreSpread(child)` call to a literal `null` in `buildRankedLines` — the two spread-value-asserting new tests (multi-child spread, regression) failed as expected (`expected null to be close to 0.4`), confirming the assertions are behavioral, not symbol-presence. Restored the correct implementation immediately after, tsc + tests re-confirmed green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Combined Task 1 + Task 2 into a single commit**
- **Found during:** Task 1 verification (`npx tsc -b --noEmit`)
- **Issue:** The plan's Task 1 acceptance criterion requires `RankedLine.childScoreSpread` to be exactly `number | null` (a REQUIRED field, not `?:` optional) and requires `tsc -b` to report zero errors after Task 1 alone. Adding a required field to the `RankedLine` interface without also updating `buildRankedLines`'s object literal in `treeCommon.ts` (Task 2's scope) makes `tsc -b` fail on the now-incomplete object literal — Task 1 could not pass its own stated gate in isolation.
- **Fix:** Implemented Task 2's `computeChildScoreSpread` helper and its wiring into `buildRankedLines` immediately after Task 1's type addition, then committed both together as one `feat` commit. This is consistent with prior project precedent recorded in STATE.md decisions (Phase 155-04, Phase 158-03) for exactly this shape of interdependency.
- **Files modified:** `frontend/src/lib/engine/types.ts`, `frontend/src/lib/engine/treeCommon.ts`, `frontend/src/lib/engine/__tests__/treeCommon.test.ts`
- **Commit:** 864a0617

No other deviations — plan executed as written otherwise.

## Known Stubs

None.

## Threat Flags

None — this plan's only surface is an internal pure-function computation over an in-memory search tree (no new network endpoint, auth path, file access, or schema change).

## Self-Check: PASSED

All created/modified files found on disk; both commits (864a0617, d23a7d34) found in git log.
