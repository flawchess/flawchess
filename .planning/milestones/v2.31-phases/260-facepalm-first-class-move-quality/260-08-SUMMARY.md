---
phase: 260-facepalm-first-class-move-quality
plan: 08
subsystem: ui
tags: [react, typescript, vitest, facepalm, flaws-card, filter]
status: complete

requires:
  - phase: 260-facepalm-first-class-move-quality
    provides: "260-07: backend cleanup; facepalm popover, Facepalm filter tag and Flaws card chip from plans 03 to 05"
provides:
  - "Flaws card: one severity chip per blunder, 'Facepalm' or 'Blunder', that is the facepalm popover trigger for every scored blunder"
  - "facepalmScoreLabel(score, type): shared accessible name of a facepalm popover trigger"
  - "SEV_FACEPALM_ON light label; selected Facepalm tag and Facepalm chip are a solid SEV_FACEPALM fill"
  - "Filter divider moved between Flaws and Tactic Depth (testid filter-tactics-divider, only when the tactic section renders)"
affects: [260-09, uat]

requirements-completed: [D-08, D-11, D-27]

actuals:
  tokens: 12000
  tasks: 3
  commits: 3
plan_head_before: 75d1760c252dc9bf7f9ffab9fbe5815aa56af807
plan_head_after: 1da9f79623a856a1eb9e756c6ee6125203375212

tech-stack:
  added: []
  patterns:
    - "A badge variant (Facepalm) resolves label, aria-label and palette through one local flag and a badgePalette() helper"
    - "Popover trigger testid stays numeric-only so the Umami target facepalm-badge keeps its history"

key-files:
  created: []
  modified:
    - frontend/src/components/library/SeverityBadge.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/FacepalmBadgePopover.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/lib/facepalm.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/library/__tests__/SeverityBadge.test.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
    - frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/lib/__tests__/facepalm.test.ts
  deleted:
    - frontend/src/components/library/FacepalmChip.tsx

key-decisions:
  - "260-G2: the Flaws card shows one severity chip (Facepalm / Blunder / Mistake) and no score on its face; the popover hangs on that chip for scored blunders"
  - "260-G1: Facepalm tag and chip are a solid dark red with a near-white label held in theme.ts (SEV_FACEPALM_ON); the 14% tint constant is removed"
  - "260-G3: the divider follows Flaws and renders only with the tactic section, so Best Moves + Flaws (one OR group) are not split and the Context border is never doubled"

patterns-established:
  - "FlawSeverityChip: module-level wrapper in FlawCard that conditionally wraps the badge in the popover"

coverage:
  - id: D1
    description: "A Flaws card describes a blunder with one chip ('??? Facepalm' or '?? Blunder'), no score on the face, popover on the chip for scored blunders"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/FlawCard.test.tsx#One severity chip and the facepalm popover (260-G2)"
        status: pass
  - id: D2
    description: "Popover trigger accessible name: 'Facepalm N%, type' on a facepalm, 'Blunder, facepalm score N%, type' otherwise"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/facepalm.test.ts#facepalmScoreLabel"
        status: pass
  - id: D3
    description: "Selected Facepalm tag and Facepalm chip are a solid SEV_FACEPALM fill with SEV_FACEPALM_ON label; ring rule D-27 kept"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "SeverityBadge.test.tsx#palette (260-G1); FlawFilterControl.test.tsx#selected Facepalm tag is a solid SEV_FACEPALM fill"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 human-check 1 (contrast and visual weight at 1280px and 390px)"
        status: unknown
  - id: D4
    description: "Filter divider sits between Flaws and Tactic Depth, only when the tactic section renders"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "FlawFilterControl.test.tsx#filter divider between Flaws and the tactic filters (260-G3)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 human-check 2 (Games and Flaws tab, sidebar and drawer)"
        status: unknown
---

# Phase 260 Plan 08: Flaws card chip, solid Facepalm palette, filter divider Summary

**One "Facepalm" / "Blunder" severity chip per Flaws card that carries the facepalm popover, a solid dark red Facepalm tag and chip with a light theme-constant label, and the filter divider moved below Flaws.**

## Accomplishments

- `SeverityBadge` reads "Facepalm" (aria-label too) for a blunder with `facepalm`; testid stays `severity-blunder-{gameId}` (D-12). Colours resolve through a `badgePalette()` helper.
- `FlawCard` gets a module-level `FlawSeverityChip` that wraps the badge in `FacepalmBadgePopover` when the blunder has a score and a type; the trigger testid stays `facepalm-badge-{gameId}-{ply}`. The separate score chip component is deleted.
- `facepalmScoreLabel(score, type)` in `facepalm.ts` is the shared trigger name; `FacepalmBadgePopover` uses it.
- `SEV_FACEPALM_ON` added to `theme.ts`; the 14% Facepalm tint constant removed; the selected Facepalm filter tag (new `selectedText` config field) and the Facepalm chip use the solid fill. D-27 ring now rings in `SEV_FACEPALM`.
- The divider `filter-tactics-divider` renders directly after Flaws, only when `showTactics` is true; the old divider after Best Moves is removed.

## Task Commits

1. Task 1 (tracer): `3ef372452` one severity chip with the popover, Facepalm label, chip component removed
2. Task 2: `2bd5f0c6c` shared accessible name for the popover trigger
3. Task 3: `1da9f7962` solid Facepalm palette and divider move

## Verification (real results)

- `npx vitest run` on FlawCard, SeverityBadge, FacepalmBadgePopover (Task 1): 3 files, 77 tests passed; `npm run build` OK.
- Task 2 vitest (facepalm, FacepalmBadgePopover, FlawCard): 3 files, 70 tests passed; build OK.
- Task 3 vitest (FlawFilterControl, SeverityBadge, FlawCard, pages/library): 6 files, 159 passed.
- Plan verification `npx vitest run src/lib src/components/library src/components/filters src/components/train src/pages/library`: 207 files, 4290 tests passed.
- `npm run lint`: clean. `npm run build` (`tsc -b && vite build`): OK. `npm run knip`: exit 0 (only the two pre-existing configuration hints).
- Plan grep gates (all with `/usr/bin/grep`): FacepalmChip files 0; SEV_FACEPALM_BG files 0; filter-best-moves-divider files 0; `export function facepalmScoreLabel` 1; `export const FACEPALM_HIGH_CUTOFF = ` 1; `export const SEV_FACEPALM_ON` 1; `filter-tactics-divider` 1 in the component and 4 in the test; SEV_FACEPALM_ON present in SeverityBadge (3) and FlawFilterControl (2).

## Pending human checks (run by the orchestrator, not executed here)

1. Task 3 human-check 1: Flaws tab at 1280px+ and 390px, a facepalm card and an ordinary scored blunder card, hover and tap on the chips, select Facepalm, Blunder, Mistake in the Tags panel. Status: pending.
2. Task 3 human-check 2: Tags panel on the Games tab and the Flaws tab, desktop sidebar and mobile drawer, divider placement and no doubled border. Status: pending.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Local variable name tripped the plan's FacepalmChip gate**
- **Found during:** Task 1 acceptance greps
- **Issue:** the first draft of `SeverityBadge` named its flag `isFacepalmChip`, which matched the whole-tree `FacepalmChip` removal gate (count 1, expected 0).
- **Fix:** renamed to `isFacepalmBadge`; no trick, the identifier is simply not the removed one.
- **Files modified:** frontend/src/components/library/SeverityBadge.tsx
- **Commit:** 3ef372452

**2. [Rule 1 - Bug] Over-broad scripted replace in FlawFilterControl**
- **Found during:** Task 3 first vitest run (ReferenceError: selectedText is not defined)
- **Issue:** the `style=` replacement matched four sibling toggle components that share that line, not just `SeverityFilterButton`.
- **Fix:** reverted the three unintended copies; only `SeverityFilterButton` reads `selectedText`.
- **Commit:** 1da9f7962 (never committed in the broken state)

### Other notes

- In Task 1, the `FlawCard` test asserts the allowed-loss trigger name with `toFacepalmPct` inline, because `facepalmScoreLabel` only lands in Task 2. It could be switched to the helper later but already agrees with it.
- `normalizedColor` (jsdom oklch normalizer) is duplicated locally in the SeverityBadge and FlawFilterControl tests rather than exported to a shared helper, matching the plan's "file's existing idiom".
- The type-tint section of `facepalm.ts` (`FACEPALM_TYPE_STYLE`) is left in place as instructed; plan 260-09 removes it.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or schema surface; T-260-18 (testid shape) is covered by the FlawCard testid assertions and the unchanged FacepalmBadgePopover tracking test.

## Self-Check: PASSED

- Files: `FacepalmChip.tsx` absent; all modified files present.
- Commits `3ef372452`, `2bd5f0c6c`, `1da9f7962` are ancestors of HEAD.
