---
phase: 257-facepalm-rate-library-stats
plan: 06
subsystem: ui
tags: [facepalm, react, library-stats, gap-bar, popover]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats (plan 04)
    provides: FACEPALM_HIGH_CUTOFF (70)
  - phase: 257-facepalm-rate-library-stats (plan 05)
    provides: FlawComparisonTc.facepalm_bullets, makeFacepalmBullet and the makeTcEntry facepalm option
provides:
  - GapCell.noVerdict (neutral zoneless cell, opt-in)
  - FACEPALM_METRICS, FACEPALM_GAP_META, facepalmMetricCell
  - GapPopover omitDirection and rangeNote props
  - ContextTagCards trailing slot
  - FacepalmCard in You vs. your opponents
affects: [257-07]

actuals:
  tokens: 7800
  tasks: 2
  commits: 4
plan_head_before: 7e6083cae356c77bb1b0db3d73f55dd1d4966e3f
plan_head_after: 09870d3e8bb67e009f32abbdc814c571dc9ef1fe
commits: 4

tech-stack:
  added: []
  patterns:
    - "Opt-in noVerdict flag on the shared GapCell: significant zoneless cells stay neutral, existing zoneless tactic cells keep their behaviour"
    - "Card slot via a trailing ReactNode on ContextTagCards, so the card shares the section gate, error state and TC switch"

key-files:
  created:
    - frontend/src/components/library/stats/FacepalmCard.tsx
    - frontend/src/components/library/stats/__tests__/FacepalmCard.test.tsx
  modified:
    - frontend/src/lib/gapBar.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/components/library/stats/GapPopover.tsx
    - frontend/src/components/library/stats/ContextTagCards.tsx
    - frontend/src/components/library/stats/LibraryStatsSections.tsx
    - frontend/src/lib/__tests__/gapBar.test.ts
    - frontend/src/components/library/stats/__tests__/GapBar.test.tsx
    - frontend/src/components/library/stats/__tests__/GapPopover.test.tsx
    - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx

key-decisions:
  - "Facepalm card sits last in the context-tag grid (one column from lg, last on phones); no new request, shares gate and TC switch"
  - "Significance sentences ('The gap is too large to be chance.', COPY_CHANCE) describe the gap and drive no colour; owner confirms the D-05 reading at UAT"
  - "The same-gap case (gapWords 'same') gets the no-range note only, no chance sentence"

requirements-completed: [D-04, D-05, D-11, D-12, D-13, D-14, D-15, D-16]

duration: 20 min
completed: 2026-11-20
---

# Phase 257 Plan 06: Facepalm blunders card Summary

**You vs. your opponents now shows a "Facepalm blunders" card with three neutral paired rows (total, missed wins, allowed losses) per 100 moves, no band, no verdict colour, no better / worse caption, following the page TC switch and the section gate.**

## Accomplishments

- `GapCell.noVerdict` short-circuits `effectiveVerdict` (so the bar dot, words and heatmap fill stay neutral); zoneless cells without the flag behave exactly as before.
- `FACEPALM_GAP_META` carries the D-14 labels and D-15 hints; the 70% in the total hint is interpolated from `FACEPALM_HIGH_CUTOFF`. `facepalmMetricCell` returns the bullet's cell with `noVerdict: true`, or null.
- `GapPopover` gained `omitDirection` (drops "Fewer is better.") and `rangeNote` (first list item replaces the typical-range line); defaults leave every existing caller unchanged.
- `FacepalmCard`: TreePalm header, intro sentence (D-16), three `GapRow`s with popovers that state "There is no typical range for facepalm blunders yet." plus the gap-significance sentence or COPY_CHANCE.
- `ContextTagCards` `trailing` slot; `VsOpponentsSection` passes `<FacepalmCard>`.

## Task Commits

1. `c128240e8` test(257-06): failing tests for neutral facepalm cells and direction-free popover (RED)
2. `ec1878db4` feat(257-06): neutral facepalm cells, labels and hints, direction-free popover (GREEN)
3. `8edf2bd5c` test(257-06): failing tests for the Facepalm blunders card (RED)
4. `09870d3e8` feat(257-06): Facepalm blunders card in You vs. your opponents (GREEN)

## TDD Gate Compliance

- RED 1 (`c128240e8`): 8 tests failed on the missing `noVerdict`, `FACEPALM_GAP_META`, `facepalmMetricCell`, `omitDirection` and `rangeNote` behaviour; the existing tests of the three files kept passing. GREEN 1 (`ec1878db4`): all 81 tests in the three files pass.
- RED 2 (`8edf2bd5c`): `FacepalmCard.test.tsx` failed to import the missing component; the new section tests failed on the absent card testids. GREEN 2 (`09870d3e8`): 63 tests across FacepalmCard, LibraryStatsSections and ContextTagCards pass.
- No REFACTOR commit.

## Deviations from Plan

None - plan executed as written. The facepalm metadata tests live in `gapBar.test.ts` (the plan named no separate meta test file).

## Verification

- `npm --prefix frontend run lint`, `run build` (tsc -b + vite), `run knip`: clean (knip prints only its two pre-existing configuration hints).
- `npm --prefix frontend test -- --run`: 6661 tests passed.
- `! grep -rqiE "chance blindness|threat blindness" frontend/src`: succeeds.

## Deferred / UAT items

- Human check (plan `<human-check>`, deferred to phase UAT, not run): dev stack as user 28, Stats tab, card placement at desktop and phone widths, three popovers (significant and not), neutral bars. The opponent side reads near zero on dev (expected); the prod read is plan 07.
- Owner confirms that "The gap is too large to be chance." and the COPY_CHANCE sentence read as statements about the gap (acceptable under D-05), or names replacement wording. No test settles this: the card-text regex checks `/probab|likel/` deliberately and not "chance".
- A zoneless bar places a non-zero gap at the saturated edge (today's tactic behaviour); proportional placement needs a scale, which arrives with the benchmark zones (SEED-261120-bzq).

## Known Stubs

None.

## Threat Flags

None. T-257-13 mitigated: `noVerdict` neutralises verdict colour and heatmap tint (gapBar.test.ts, GapBar colour-table row and no-band test, FacepalmCard no-band and neutral-dot tests).

## Self-Check: PASSED

- FOUND: frontend/src/components/library/stats/FacepalmCard.tsx, frontend/src/components/library/stats/__tests__/FacepalmCard.test.tsx
- FOUND commits (ancestors of HEAD): c128240e8, ec1878db4, 8edf2bd5c, 09870d3e8
