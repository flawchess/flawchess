---
phase: 260-facepalm-first-class-move-quality
plan: 04
subsystem: ui
tags: [react, typescript, eval-chart, facepalm, vitest]

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-02: flawMoveCategory, FlawMoveCategory and the split categoryPlies behind highlightedPlies"
provides:
  - "flawMarkerColor(marker) in lib/flawDotColor.ts: SEV_FACEPALM for a facepalm blunder, else the severity colour"
  - "EvalChart dot renderer and tooltip verdict on that colour; exported FlawTooltipVerdict with the ??? icon (D-17, D-18, D-26)"
affects: [260-05, 260-06]

requirements-completed: [D-17, D-18, D-19, D-26]

actuals:
  tokens: 6000
  tasks: 2
  commits: 2
plan_head_before: b6a0947b3fd275967744feb9ddc19e5a7e33733e
plan_head_after: 001e92a779f45c2bded9159159c7858e7316a4bd

tech-stack:
  added: []
  patterns:
    - "Pure, exported chart-colour helper in its own lib file (like bestMoveDot.ts), unit-tested without mounting recharts"
    - "Tooltip pieces that need no interaction are exported and tested directly (FacepalmTooltipLine, FlawTooltipVerdict)"

key-files:
  created:
    - frontend/src/lib/flawDotColor.ts
    - frontend/src/lib/__tests__/flawDotColor.test.ts
  modified:
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/library/__tests__/EvalChart.test.tsx

key-decisions:
  - "No new theme constant: SEV_FACEPALM (= FACEPALM_BAND_SWATCH) colours dots and the tooltip verdict; legibility of oklch 0.42 on the dark card is left to the owner's visual check"
  - "D-19 needed no chart change: the chart already reads highlightedPlies, which plan 02 derives from the split categoryPlies"

coverage:
  - id: D1
    description: "A facepalm blunder dot is SEV_FACEPALM on either side in every state; other blunders, mistakes and inaccuracies keep their severity colour"
    requirement: "D-17, D-07"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/flawDotColor.test.ts#flawMarkerColor (260 D-17)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The tooltip verdict reads You/Opponent · Facepalm with the ??? icon and SEV_FACEPALM; other flaws keep the dot glyph and severity word; the score line is unchanged"
    requirement: "D-18, D-26, D-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/EvalChart.test.tsx#FlawTooltipVerdict (260 D-18 / D-26)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The dark red dot and hollow square stay distinct from the brighter ?? red when dimmed by a cell hover, and the Facepalm label is legible on the near-black tooltip"
    requirement: "D-17, D-18"
    verification: []
    human_judgment: true
    rationale: "Colour legibility of SEV_FACEPALM is visual (research Pitfall 5); jsdom cannot judge it. Plan Task 2 human-check, after Phase 259's switch release."

duration: 10min
completed: 2026-11-22
status: complete
---

# Phase 260 Plan 04: Facepalm on the eval chart Summary

**Facepalm blunders are drawn dark red on the eval chart (circle and square, every dot state) and named "You/Opponent · Facepalm" with the ??? icon in its tooltip, all through the one `flawMoveCategory` classifier.**

## Performance

- **Duration:** about 10 min
- **Completed:** 2026-11-22
- **Tasks:** 2
- **Files modified:** 4 (2 new)

## Accomplishments

- `flawMarkerColor` maps `flawMoveCategory(marker)` through a closed `Record<FlawMoveCategory, string>` of theme constants (no new constant, no literal colours). It ignores `is_user`, so both sides read the same.
- `EvalChart` lost its private `severityColor`; `buildDotRenderer` computes one colour per marker for the normal, highlighted and dimmed states, and the tooltip uses the same helper. Unused `SEV_*` and `FlawSeverity` imports were removed.
- Exported `FlawTooltipVerdict({ marker })` (testid `eval-chart-tooltip-verdict`) renders `FacepalmBlunderIcon` in place of the dot glyph for a facepalm blunder with the label "Facepalm"; every other flaw keeps its glyph and capitalised severity. `FacepalmTooltipLine` and the tactic/tag list below are untouched (D-11).
- D-19 (cell hover emphasizes only "??" or only "???" dots) needed no chart change: it follows `highlightedPlies`, which plan 02 derives from the split cycle maps.

## Task Commits

1. **Task 1: Tracer, facepalm dot colour through the shared classifier** - `80731dd70` (feat)
2. **Task 2: Tooltip names a facepalm blunder with the ??? icon** - `001e92a77` (feat; tests and implementation in one commit so the tree stays buildable, the RED run failed on the missing export first)

The tracer feedback gate: the tracer `<verify>` is automated-only, was run after the commit (vitest and `npm run build` green) before the expansion task.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test bug] Verdict text assertion read the icon's svg text**
- **Found during:** Task 2
- **Issue:** the `FacepalmBlunderIcon` svg carries "???" as text, so `verdict.textContent` was "???You · Facepalm".
- **Fix:** the test reads the label span, and asserts the single svg's text is "???".
- **Files modified:** frontend/src/components/library/__tests__/EvalChart.test.tsx
- **Commit:** 001e92a77

**2. [Ordering] Task 2 RED and GREEN share one commit**
- The RED test run (4 failures on the missing export) was observed, but a test-only commit would leave `npm run build` red, so tests and implementation landed together.

**Total deviations:** 1 test fix, 1 ordering note. **Impact:** none on scope or behavior.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary; T-260-10 and T-260-SC accepted as planned.

## Verification

- `npx vitest run src/lib/__tests__/flawDotColor.test.ts src/components/library/__tests__/EvalChart.test.tsx`: 22 passed after Task 1; EvalChart.test.tsx 21 passed after Task 2.
- Full frontend suite `npm test -- --run`: 6734 passed. `npm run lint`: exit 0. `npm run build`: exit 0. `npm run knip`: exit 0.
- Acceptance greps: `function severityColor` 0; `flawMarkerColor(` 3 in EvalChart.tsx; `export function flawMarkerColor` 1; no colour literals in flawDotColor.ts (0); `export function FlawTooltipVerdict` 1; `FacepalmBlunderIcon` 2; `FlawTooltipVerdict` 6 in the test; `eval-chart-tooltip-facepalm` 1 (D-11 guard).
- Not run: the human colour check (dark red dot and square distinct from the "??" red, dimmed state, tooltip label legibility), see coverage D3. If the label is hard to read, report it to the owner rather than inventing a lighter tone (D-17).

## Next Phase Readiness

Plans 260-05 and 260-06 continue the frontend order; nothing here blocks them.

## Self-Check: PASSED

Created files exist (`frontend/src/lib/flawDotColor.ts`, `frontend/src/lib/__tests__/flawDotColor.test.ts`); commits 80731dd70 and 001e92a77 are ancestors of HEAD.
