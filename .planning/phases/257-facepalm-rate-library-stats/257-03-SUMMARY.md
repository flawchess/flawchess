---
phase: 257-facepalm-rate-library-stats
plan: 03
subsystem: ui
tags: [facepalm, react, vitest, library-flaws, analysis]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats
    provides: FACEPALM_TYPE_STYLE, type-tinted FacepalmChip (plan 01), FlawMarker.facepalm_type (plan 02)
provides:
  - FACEPALM_TYPE_LABEL / FACEPALM_TYPE_SENTENCE and the facepalm-explanation-type line on every facepalm popover
  - move-list mini-chip tinted by type, rendered only with score and type
  - FacepalmTooltipLine: eval-chart tooltip line that names and tints the type
  - neutral FACEPALM_CHIP / FACEPALM_CHIP_BG deleted from theme.ts
affects: [257-04, 257-05]

actuals:
  tokens: 9000
  tasks: 2
  commits: 4
plan_head_before: 696cc0d0b029c9b051888e240bfeff69476fa3d5
plan_head_after: ae6dab21bf1c0df1105cd1ae141d69f0382dd9ba
commits: 4

tech-stack:
  added: []
  patterns:
    - "Type line is label + sentence lookups (Record<FacepalmType, string>), never the raw API string"
    - "Surfaces render only when score and type are both non-null (D-09)"

key-files:
  created: []
  modified:
    - frontend/src/lib/facepalm.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/library/FacepalmExplanation.tsx
    - frontend/src/components/library/FacepalmBadgePopover.tsx
    - frontend/src/components/library/FacepalmChip.tsx
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/analysis/FacepalmMoveChip.tsx
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
    - frontend/src/components/library/__tests__/FacepalmExplanation.test.tsx
    - frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
    - frontend/src/components/library/__tests__/EvalChart.test.tsx
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx

key-decisions:
  - "Type line is mover-neutral, so byOpponent keeps only its existing 'their level' switch"
  - "Eval-chart tooltip names the type in text ('Facepalm 95% · allowed loss'), lowercase like the tactic lines; confirmed at UAT"
  - "FacepalmTooltipLine is exported for its unit test only; knip accepts the in-file use"

requirements-completed: [D-05, D-08, D-09, D-10]

duration: 15 min
completed: 2026-11-20
---

# Phase 257 Plan 03: Type on every facepalm surface Summary

**The move-list mini-chip and the eval-chart tooltip line are now tinted teal (missed win) or crimson (allowed loss), both popovers name the type in one line, trigger aria-labels carry it, and the neutral facepalm chip colours are gone.**

## Accomplishments

- `FACEPALM_TYPE_LABEL` and `FACEPALM_TYPE_SENTENCE` in `frontend/src/lib/facepalm.ts` (D-10 wording, no probability words).
- `FacepalmExplanation` takes a required `type` and renders `facepalm-explanation-type` ("Missed win: the best move won material that was not taken." / "Allowed loss: the move gave away material.") right under the heading.
- `FacepalmBadgePopover` aria-label is "Facepalm 94%, allowed loss"; `FacepalmMoveChip` is tinted from `FACEPALM_TYPE_STYLE` and its aria-label names the type.
- `VariationTree` / `useAnalysisGemMarkers`: `FlawMarkerEntry.facepalmType`, set together with the score; the mini-chip renders only with both.
- `EvalChart` `FacepalmTooltipLine` reads "Facepalm NN% · missed win|allowed loss", coloured by type; the tooltip renders it only with score and type.
- `FACEPALM_CHIP` / `FACEPALM_CHIP_BG` deleted; `grep -rq FACEPALM_CHIP frontend/src` finds nothing; knip clean.

## Task Commits

1. **Task 1 RED:** `601c19323` (test) - failing popover, aria-label and mini-chip tint tests.
2. **Task 1 GREEN:** `fcf8d73d4` (feat) - type line, tinted mini-chip, VariationTree gate.
3. **Task 2 RED:** `848eae372` (test) - failing FacepalmTooltipLine tests.
4. **Task 2 GREEN:** `ae6dab21b` (feat) - hook, tooltip line, theme cleanup.

## TDD Gate Compliance

- RED commits `601c19323` and `848eae372` precede their GREEN commits. Task 1 RED run: 8 tests failed on assertions for the planned behavior (missing `facepalm-explanation-type` testid, old aria-label "Facepalm 94%", neutral mini-chip colour, missing type line in the FlawCard popover). Task 2 RED run: both `FacepalmTooltipLine` tests failed because the component export did not exist ("Element type is invalid ... got: undefined"), i.e. the planned feature was absent.
- The formal `gsd_run check tdd-red-evidence` record was not produced (vitest output was read directly); semantic assessment: every failing target executed and failed on the planned behavior, not on setup or syntax faults.
- No REFACTOR commit.

## Deviations from Plan

None - plan executed as written. The (10b) VariationTree test was extended to also pin "score without type renders no chip" (T-257-12 mitigation).

## Known Stubs

None.

## Threat Flags

None. Labels and colours come from `Record<FacepalmType, ...>` lookups; T-257-12 mitigation is covered by the score-without-type test.

## Verification Run

- `npm test -- --run` full suite: 375 files, 6630 tests passed.
- `npm run lint`, `npm run build` (tsc -b), `npm run knip`: clean.
- Human check (tint of the three surfaces on the dev stack, UAT) not run here; deferred to phase UAT.

## Self-Check: PASSED

- FOUND: all 14 modified files; `FACEPALM_TYPE_SENTENCE`, `facepalm-explanation-type`, `facepalmType: fm.facepalm_type`... (hook spreads `facepalmType: fm.facepalm_type`), `export function FacepalmTooltipLine`.
- FOUND commits: 601c19323, fcf8d73d4, 848eae372, ae6dab21b.
