---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
plan: 03
subsystem: ui
tags: [react, typescript, recharts, chess, maia]

requires:
  - phase: 163-01
    provides: "the 'gem' MoveQuality value and bucketKeyForQuality('gem') -> 'good' fold"
provides:
  - "colorForQuality('gem') -> MAIA_ACCENT in MovesByRatingChart (violet gem curve + SAN label)"
  - "UnifiedMovePopover isGem prop rendering a violet gem copy line"
  - "MaiaMoveQualityBar wiring isGem per hovered prose move via qualityBySan"
affects: [163-04]

tech-stack:
  added: []
  patterns:
    - "Single-branch switch-case extension (colorForQuality) rather than a parallel lookup table"
    - "Optional boolean prop gating a conditional table row (UnifiedMovePopover), matching the file's existing null-omits-line convention"

key-files:
  created: []
  modified:
    - frontend/src/components/analysis/MovesByRatingChart.tsx
    - frontend/src/components/analysis/UnifiedMovePopover.tsx
    - frontend/src/components/analysis/MaiaMoveQualityBar.tsx

key-decisions:
  - "Pitfall-5 audit recorded inline via commit message, not a new file: the only quality-string branch in MovesByRatingChart.tsx is colorForQuality's switch; stroke emphasis at ~line 576 keys off san === playedSan || san === bestSan (the SAN props), not the quality string, so it needed no change"
  - "isGem threaded through ProseMoveSpan as a new required boolean prop (not read from qualityBySan inside the child) — keeps ProseMoveSpan's existing prop-shape convention (parent computes, child renders) and avoids adding qualityBySan as a second data dependency to a component that otherwise only takes VerdictMove + mover"
  - "Gem copy row rendered as a single colSpan={2} table cell (not split across the label/value columns like the source rows) since it has no separate value — a plain declarative sentence, not a label+number pair"

requirements-completed: [D-07]

coverage:
  - id: D1
    description: "A gem candidate's curve + end-of-line SAN label render MAIA_ACCENT violet in MovesByRatingChart; qualityWord yields 'Gem'"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "cd frontend && npx vitest run src/components/analysis (151 tests, all pass, no regressions)"
        status: pass
      - kind: static
        ref: "grep -n \"case 'gem'\" MovesByRatingChart.tsx — exactly one match inside colorForQuality returning MAIA_ACCENT"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stroke emphasis (played/best) still fires for a gem move because it keys off SAN identity, not quality"
    requirement: "D-07"
    verification:
      - kind: static
        ref: "grep -n \"=== 'best'|case 'best'\" MovesByRatingChart.tsx — only the colorForQuality case 'best'; emphasis logic at ~line 576 unchanged (san === playedSan || san === bestSan)"
        status: pass
    human_judgment: false
  - id: D3
    description: "UnifiedMovePopover renders a violet gem copy line when isGem is true and omits it otherwise"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b && npm run lint (clean); grep -n \"players at your rating almost never find this\" UnifiedMovePopover.tsx"
        status: pass
      - kind: static
        ref: "no existing UnifiedMovePopover unit test file — coverage is via tsc/lint + the consuming MaiaMoveQualityBar test suite exercising ProseMoveSpan, which does not itself assert on popover DOM content"
        status: pass
    human_judgment: true
    rationale: "No dedicated UnifiedMovePopover render test exists (pre-existing gap, not introduced by this plan); the gem row's visual appearance (icon + violet text) is not screenshot-verified, only compiled/linted and grep-confirmed present in source."
  - id: D4
    description: "MaiaMoveQualityBar wires isGem per hovered candidate; bar segments fold gem into good unchanged"
    requirement: "D-07"
    verification:
      - kind: static
        ref: "grep -n \"qualityBySan.get(m.san)?.quality === 'gem'\" MaiaMoveQualityBar.tsx; grep -n \"QUALITY_BUCKET_ORDER|bucketMovesByQuality\" MaiaMoveQualityBar.tsx shows the unchanged segment loop"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-10
status: complete
---

# Phase 163 Plan 03: Gem-aware chart + popover surfaces Summary

**`colorForQuality('gem')` renders MAIA_ACCENT violet in the Moves-by-Rating chart, and `UnifiedMovePopover` gains an `isGem` prop rendering a violet gem copy line, wired from `MaiaMoveQualityBar`'s hovered prose move.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-07-10T17:36:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `MovesByRatingChart.tsx`: `colorForQuality` gained a `case 'gem': return MAIA_ACCENT;` branch — a gem candidate's curve and end-of-line SAN label now render violet; `qualityWord` needed no change (its existing capitalize logic already produces 'Gem')
- Pitfall-5 audit performed: confirmed the only quality-string branch in the file is `colorForQuality`'s switch; the played/best stroke emphasis (~line 576) keys off `san === playedSan || san === bestSan`, so a gem move (by construction the reconciled best SAN) keeps its emphasized stroke with zero code change
- `UnifiedMovePopover.tsx`: added an optional `isGem?: boolean` prop; when true, renders a leading violet (`MAIA_ACCENT`) row with a lucide `Gem` icon and the copy "Gem — players at your rating almost never find this."; omitted when falsy
- `MaiaMoveQualityBar.tsx`: `ProseMoveSpan` gained an `isGem` prop forwarded to `UnifiedMovePopover`; `renderMove` computes it as `qualityBySan.get(m.san)?.quality === 'gem'`. The bar's SEGMENTS remain untouched — `bucketKeyForQuality('gem')` (Plan 01) already folds a gem-quality SAN into the existing green "Good Moves" segment via `bucketMovesByQuality`, confirmed unchanged in this plan

## Task Commits

Each task was committed atomically:

1. **Task 1: MovesByRatingChart colorForQuality/qualityWord gem handling + Pitfall-5 audit** - `eb227f33` (feat)
2. **Task 2: UnifiedMovePopover gem copy line (isGem prop) + wire it from MaiaMoveQualityBar** - `66655b3f` (feat)

## Files Created/Modified
- `frontend/src/components/analysis/MovesByRatingChart.tsx` - `colorForQuality` gem case added (MAIA_ACCENT)
- `frontend/src/components/analysis/UnifiedMovePopover.tsx` - `isGem` prop + gated violet gem copy row, `Gem` added to the lucide import
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` - `ProseMoveSpan` gained `isGem` prop; `renderMove` computes it from `qualityBySan`; `UnifiedMovePopover` call site passes it through

## Decisions Made
- `isGem` is threaded through `ProseMoveSpan` as an explicit required prop computed by the parent (`renderMove`), not read from `qualityBySan` inside the child — matches the existing "parent computes, child renders" shape of the component's other props
- The gem copy row spans both table columns (`colSpan={2}`) since it's a single declarative sentence, not a label+value pair like the source rows
- No new geometry/theme constants — reused `MAIA_ACCENT` (already imported in both files) verbatim per the phase's seed-lock

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their acceptance criteria on the first implementation pass; no auto-fixes (Rules 1–3) were needed.

## Known Stubs

None introduced by this plan. `GemIcon.tsx` (created in Plan 02) remains flagged as unused by knip — expected until Plan 04 wires it into `VariationTree.tsx`'s move-list icons, as documented in the 163-02-SUMMARY.md.

## Threat Flags

None. Presentational-only rendering of client-computed quality labels, consistent with the plan's threat model (T-163-03, accepted).

## Issues Encountered

None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `colorForQuality`'s gem branch and `UnifiedMovePopover`'s `isGem` prop are ready for Plan 04 to wire real gem-bearing quality data (`qualityBySanWithGem`) through `Analysis.tsx` → `MaiaHumanPanel` → both `MovesByRatingChart` and `MaiaMoveQualityBar`.
- No blockers. `tsc -b`, `npm run lint`, and `npx vitest run src/components/analysis` (151 tests) are all green.

---
*Phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/components/analysis/MovesByRatingChart.tsx
- FOUND: frontend/src/components/analysis/UnifiedMovePopover.tsx
- FOUND: frontend/src/components/analysis/MaiaMoveQualityBar.tsx
- FOUND commit: eb227f33
- FOUND commit: 66655b3f
