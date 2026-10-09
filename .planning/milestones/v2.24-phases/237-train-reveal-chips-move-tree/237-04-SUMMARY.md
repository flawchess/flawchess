---
phase: 237-train-reveal-chips-move-tree
plan: 04
subsystem: ui
tags: [react, train, chips, move-tree, variation-tree]
status: complete

requires:
  - phase: 237-02 (chip model + useTrainRevealTree)
    provides: "buildChipGroups, ChipGroup, TrainRevealTree (listView, selectChip, goToNode, deleteLine)"
provides:
  - "TrainLineChips: chips row (merged labels, active state, mark, eval, loading/failed, SAN-only game chip, optional ring)"
  - "TrainMoveTreeList + TRAIN_MOVE_TREE_HEIGHT_CLASS ('h-16'): the reveal move list over the tree's list view"
  - "VariationTree variant 'wrap': wrapping mobile renderer at every width"
affects: [237-05, 237-06, 237-11]

tech-stack:
  added: []
  patterns:
    - "Chip testids keyed on the primary role (train-chip-your/best/game), never on SAN"
    - "Tracer harness: real buildChipGroups + real useTrainRevealTree + both components, no module mocks"

key-files:
  created:
    - frontend/src/components/train/TrainLineChips.tsx
    - frontend/src/components/train/TrainMoveTreeList.tsx
    - frontend/src/components/train/__tests__/TrainLineChips.test.tsx
    - frontend/src/components/train/__tests__/TrainMoveTreeList.test.tsx
  modified:
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx

key-decisions:
  - "TrainMoveTreeList imports the hook's already-exported TrainRevealTree type, so no local ReturnType alias and no edit to useTrainRevealTree.ts"
  - "The SAN-only game chip is a plain div (data-interactive=false), rendered in the same grid row after the button chips"
  - "ChipGroup passes straight into useTrainRevealTree's chips option (structurally a RevealChipLine)"

patterns-established:
  - "Mutation proof: no-op onNodeClick, removed loading branch, and a hard-coded aria-pressed each turned their tests red"

requirements-completed: [D-01, D-02, D-03]

duration: 7 min
completed: 2026-10-09
actuals:
  tokens: 20000
  tasks: 2
  commits: 2
plan_head_before: 6d190697d0b34411f0e61def9f6decb1242b9127
plan_head_after: 28f68241bf808523ce922bca6aaf5bd6e0014f3d
commits: 2

coverage:
  - id: D1
    description: "With the real chip model and tree hook, a chip tap switches the list to that line, a tap from another chip's line returns the tree to the puzzle position (D-01), and a list token tap moves the tree (D-03)"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainMoveTreeList.test.tsx#tracer: a chip tap switches the list to its line and a list tap moves the tree"
        status: pass
    human_judgment: false
  - id: D2
    description: "Coinciding roles render as ONE chip labelled You = Best / You = Game, keyed on the primary role; the active chip is aria-pressed with the brand ring"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLineChips.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase 236 D-14/D-15 chip states: loading spinner in the eval slot, failed shows SAN and mark without eval, SAN-only game move is a non-interactive chip"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLineChips.test.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "VariationTree variant 'wrap' renders only the wrapping mobile list; responsive and vertical variants untouched"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx (1b + all existing cases)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The h-16 list height and chip layout look right on real devices"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 04: Chips Row and Wrapping Move List Summary

**`TrainLineChips` and `TrainMoveTreeList` exist and are proven against the real `buildChipGroups` and `useTrainRevealTree`: a chip tap switches the list line (jumping to the puzzle position first), a list token tap moves the tree, and `VariationTree` gained a `'wrap'` variant that renders the wrapping numbered list at every width.**

## Performance

- **Duration:** 7 min
- **Tasks:** 2 (1 tracer, 1 TDD-flagged auto)
- **Files:** 4 created, 2 modified (frontend only; no screen file touched)

## Accomplishments

- `VariationTree` `variant='wrap'`: mirrors the `'vertical'` branch but renders `MobileTree` inside the same `analysis-variation-tree` wrapper; `'responsive'` and `'vertical'` unchanged.
- `TrainMoveTreeList`: `VariationTree variant="wrap"` fed by `tree.listView`, `onNodeClick=tree.goToNode`, `onDeleteLine=tree.deleteLine`, optional `markers` and ring, height from the named `TRAIN_MOVE_TREE_HEIGHT_CLASS = 'h-16'`.
- `TrainLineChips`: grid row of one `<button>` per chip (`train-chip-{key}` with `-label/-san/-eval/-loading/-quality`, `aria-pressed`, `data-active`, `data-roles`, `data-line-status`), quality mark via `MoveQualityIcon`, eval pill in the old card's `BEST_MOVE_ARROW` styling, `Loader2` spinner while loading, nothing in the eval slot when failed, a non-interactive `train-chip-game` div for a SAN-only game move.
- Tracer harness test and 12 chip tests (one per Behavior bullet, plus ready/no-active cases).

## Task Commits

1. **Task 1 (tracer): chips row and wrapping move list over the real reveal tree** - `234b9e3b8` (feat)
2. **Task 2: chip quality mark, eval, loading/failed states and wrap-variant test** - `28f68241b` (feat)

Tracer gate: the `<verify>` set (tracer test, `npm run build`, plus eslint and knip on the touched files) passed after Task 1; expansion proceeded.

## Verification

- `TrainLineChips`, `TrainMoveTreeList`, `VariationTree` tests: 38 pass.
- `npm run lint`, `npm run build`, `npm run knip` clean; full frontend suite 320 files, 5408 tests pass.
- Acceptance greps: no SAN interpolated into any template literal (0), no `text-xs` outside comments (0), `data-interactive="false"` present.
- Only the six `files_modified` files changed (`git diff --name-only` over the plan's commits).

## Mutation proof

Each behavior was reverted, the tests seen failing, and the file restored from a backup:

- `onNodeClick` made a no-op: tracer test red.
- Loading branch removed from the eval slot: the loading-chip test red.
- `aria-pressed` hard-coded to false: the active-chip test and the tracer red.

## TDD Gate Compliance

Task 2 was flagged `tdd="true"` but the plan is `type: execute` and the component was extended together with its tests, so there is no separate RED commit. RED-equivalent evidence is the mutation runs above.

## Deviations from Plan

None - plan executed as written. Notes: the plan's optional local `TrainRevealTree` alias was unnecessary (the hook already exports the type); `sanOnlyGameMove` and its non-interactive chip landed in Task 1 with the prop, Task 2 tests it.

## Known Stubs

None.

## Threat Flags

None. T-237-08 holds: testids are role-keyed and no template literal interpolates a SAN (acceptance grep returns 0).

## Next Phase Readiness

Plan 05 can mount `TrainLineChips` and `TrainMoveTreeList` in `TrainReveal` in place of the line cards and re-point `buildChipFocusOverlay` at `tree.activeChip`. `TRAIN_MOVE_TREE_HEIGHT_CLASS` is re-measured in plan 11 UAT (D5 pending).

## Self-Check: PASSED

- FOUND: frontend/src/components/train/TrainLineChips.tsx, TrainMoveTreeList.tsx, both new test files, `variant?: 'responsive' | 'vertical' | 'wrap'` in VariationTree.tsx
- FOUND commits: 234b9e3b8, 28f68241b
