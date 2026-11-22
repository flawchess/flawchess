---
phase: 260-facepalm-first-class-move-quality
plan: 09
subsystem: ui
tags: [react, typescript, vitest, facepalm, move-list, explain-bar, eval-chart-tooltip]
status: complete

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-08: facepalmScoreLabel, one severity chip on the Flaws card, solid Facepalm palette"
provides:
  - "FacepalmGlyphBadge: the '??' / '???' move-list icon of a scored blunder opens the facepalm score popover; the score chip is gone"
  - "ExplainHeadline.facepalmPct and the footer line 'Qf6+ ???: Facepalm N% · tactic'"
  - "Eval chart tooltip: one verdict line with the score, FlawTooltipDetail, neutral text, 95% opaque box, text-sm, 14px icons"
  - "FACEPALM_TYPE_STYLE and FacepalmTypeStyle removed (no reader left)"
affects: [uat]

requirements-completed: [D-11, D-18, D-26]

actuals:
  tokens: 30000
  tasks: 3
  commits: 3
plan_head_before: f461e47b4e5fd106f2f7bb3b8fbe9fa578907ff9
plan_head_after: ba6657b5fa6e80c85720ad4446415337f5d66005

tech-stack:
  added: []
  patterns:
    - "Icon colour only in the chart tooltip; every label is text-foreground"
    - "Glyph choice for a scored blunder goes through isFacepalmBlunder in both severityIcon and FacepalmGlyphBadge, so they cannot disagree"

key-files:
  created:
    - frontend/src/components/analysis/FacepalmGlyphBadge.tsx
  modified:
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/ExplainBar.tsx
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/library/FacepalmExplanation.tsx
    - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
    - frontend/src/lib/explainBar.ts
    - frontend/src/lib/facepalm.ts
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
    - frontend/src/components/analysis/__tests__/ExplainBar.test.tsx
    - frontend/src/components/library/__tests__/EvalChart.test.tsx
    - frontend/src/lib/__tests__/explainBar.test.ts
    - CHANGELOG.md
  deleted:
    - frontend/src/components/analysis/FacepalmMoveChip.tsx (renamed to FacepalmGlyphBadge.tsx, score chip removed)

key-decisions:
  - "260-G2: the move list shows one icon per blunder; the icon carries the popover on every scored blunder (score and type present)"
  - "260-G2: the footer line names the score for facepalms only; ordinary blunders show it in the icon popover and the tooltip"
  - "260-G1: tooltip verdict and score on one line; the type is named in words only when the flaw has no tactic row"
  - "Mistake and inaccuracy tooltip rows keep the dot glyph (the owner's table covers blunders only)"
  - "A flaw with a missed and an allowed tactic keeps both tactic rows with their depth lines"

patterns-established:
  - "FlawTooltipDetail: verdict, optional type line, tactic rows (orientation colour on the icon) and tag rows in one exported piece"

coverage:
  - id: D1
    description: "Move list: '??' / '???' icon per scored blunder opens the facepalm popover, no score chip, tap does not navigate"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/VariationTree.test.tsx#(10b), (10c)"
        status: pass
      - kind: manual_procedural
        ref: "Task 2 human-check (desktop hover, mobile tap, two-line footer)"
        status: unknown
  - id: D2
    description: "Footer line names the score of a facepalm: 'Qf6+ ???: Facepalm N% · tactic', in explain and got-it states"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/explainBar.test.ts (facepalmPct cases); frontend/src/components/analysis/__tests__/ExplainBar.test.tsx"
        status: pass
  - id: D3
    description: "Tooltip: one verdict line with score, type text only without a tactic row, neutral labels, near-opaque larger box"
    requirement: "D-18"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/EvalChart.test.tsx#FlawTooltipVerdict, FlawTooltipDetail"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 human-check (legibility, opacity, fit at 1280px and 390px)"
        status: unknown
---

# Phase 260 Plan 09: One-icon move list, facepalm footer score, one-line tooltip Summary

**The analysis move list shows one "??" or "???" icon per blunder that carries the facepalm popover, the footer line names a facepalm's score, and the eval chart tooltip states verdict and score on one neutral line on a near-opaque, larger box.**

## Accomplishments

- `FacepalmGlyphBadge` (renamed from the move-chip file, one exported component) renders `FacepalmBlunderIcon` or `BlunderIcon` through `isFacepalmBlunder`, as the trigger of the shared `InfoPopover` (testid `facepalm-glyph-popover`, aria-label `facepalmScoreLabel(score, type)` plus ", what the score means"). The click-swallowing wrapper stays, so a tap opens the popover instead of navigating. `MoveListMarker` returns it alone for a blunder with score and type; unscored or untyped blunders keep a plain "??".
- `ExplainHeadline.facepalmPct` (replaces the boolean flag); `Headline` shows "Facepalm N%" in `text-foreground` after the colon, then a middle dot, then the tactics. Ordinary blunders and mistakes read as before.
- Tooltip: `FlawTooltipVerdict` is one neutral line ("??? You · Facepalm 95%", "?? You · Blunder 12%"); new exported `FlawTooltipDetail` holds verdict, the `eval-chart-tooltip-facepalm-type` line (only with no tactic row), tactic rows (orientation colour on the icon, neutral text, depth line kept) and tag rows. Box is `bg-background/95 text-sm` with no blur; all tooltip icons share `TOOLTIP_ICON_CLASS` (14px); `MarkerGlyph` renders at 14px on a 12-unit viewBox. Gem/great row label is neutral.
- `FACEPALM_TYPE_STYLE`, `FacepalmTypeStyle`, `FacepalmTooltipLine` and the old move-list score chip are removed. CHANGELOG [Unreleased]: three new Changed bullets, plus three existing bullets amended in place (the Facepalm Score filter bullet's chip clause, the "tinted by type" bullet, the Tags panel divider clause).

## Task Commits

1. Task 1 (tracer): `0659e93ad` move-list icons open the facepalm popover, score chip removed
2. Task 2: `e5f1e8aff` footer line names the score of a facepalm
3. Task 3: `ba6657b5f` one-line tooltip, type tint removed, CHANGELOG

## Verification (real results)

- Task 1: vitest VariationTree + FacepalmExplanation, 2 files, 37 tests passed; `npm run build` OK.
- Task 2: vitest explainBar + ExplainBar, 2 files, 50 tests passed; `npm run lint` clean; `npm run build` no errors.
- Task 3: vitest EvalChart + facepalm, 2 files, 35 tests passed.
- Full gate `npm run lint && npm run build && npm test -- --run && npm run knip`: lint clean, build OK, 381 test files / 6795 tests passed, knip reported only the two pre-existing configuration hints (no unused files or exports).
- Acceptance greps (all `/usr/bin/grep`): `FacepalmMoveChip` files 0; `facepalm-move-popover` in non-test files 0 (test files keep absence assertions); `FacepalmGlyphBadge` import in VariationTree 1; `facepalmPct` in explainBar.ts >= 2; `analysis-explain-facepalm` 1 in ExplainBar.tsx; `bg-background/95` 1; `backdrop-blur` 0; `h-3 w-3` 0; `export function FlawTooltipDetail` 1; `eval-chart-tooltip-facepalm-type` 1; `FacepalmTooltipLine` files 0; `FACEPALM_TYPE_STYLE` files 0; CHANGELOG `??? Facepalm` 1, `below Flaws` 1, `pawn` 0.

## Pending human checks (run by the orchestrator, not executed here)

1. Task 2 human-check: /analysis at 1280px+ and 390px, a facepalm blunder and an ordinary scored blunder with tactics: one icon per blunder then the tactic chip, no percent chip, hover and tap open the popover, tap does not jump to the move, footer "{move} ???: Facepalm N% · {tactic}" within two lines with Best and Punish still in the row. Status: pending.
2. Task 3 human-check: scrub the eval chart on a Library game card and on /analysis over a facepalm of each side, a scored blunder with and without a tactic, a mistake and a gem: one verdict line, type line only without a tactic row, neutral readable text, colour on icons only, box opaque and fits at both widths. Status: pending.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 commit staged only the rename**
- **Found during:** Task 1 commit
- **Issue:** `git add` listed the already-renamed old path, which aborted the whole add, so the first commit held only the pure rename (no content).
- **Fix:** amended the same unpushed commit with the real changes before any further work; no history was rewritten beyond that one local commit.
- **Commit:** 0659e93ad

**2. [Rule 1 - Bug] Test expectation missed the icon text**
- **Found during:** Task 1 first vitest run
- **Issue:** the popover line's textContent includes the "???" of its icon.
- **Fix:** test expectation corrected (no source change).

**3. [Rule 1 - Bug] Headline rendered a trailing space on an ordinary blunder without tactics**
- **Found during:** Task 2 first vitest run
- **Issue:** the unconditional space after the nowrap span changed `Qh5??` to `Qh5?? `.
- **Fix:** the space renders only when a facepalm score or tactics follow, as before.

### Notes

- Umami: the `popover-open` target `facepalm-move-popover` is retired and `facepalm-glyph-popover` now covers every scored blunder (a history discontinuity, not a rename).
- Tooltip scope decisions from the plan were kept: mistakes and inaccuracies keep the dot glyph; both tactic rows stay when a flaw has a missed and an allowed tactic.
- Two untracked temporary files (`frontend/vite.uat.config.ts`, `frontend/public/uat-login.html`) were left untouched and uncommitted; knip did not flag them.

## Known Stubs

None.

## Threat Flags

None. T-260-20: the testid `facepalm-glyph-popover` is a fixed string (asserted through `getAllByTestId` in the VariationTree test).

## Self-Check: PASSED

- `FacepalmGlyphBadge.tsx` present, `FacepalmMoveChip.tsx` absent.
- Commits `0659e93ad`, `e5f1e8aff`, `ba6657b5f` are ancestors of HEAD.
