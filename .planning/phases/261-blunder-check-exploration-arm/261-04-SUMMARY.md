---
phase: 261-blunder-check-exploration-arm
plan: 04
subsystem: frontend
tags: [blunder-check, facepalm, solution-screen, copy]
requires:
  - phase: 261-02
    provides: neutral FacepalmChip (score + testId)
provides:
  - BlunderSolution.feedback wire type (BlunderFeedback, BlunderTypeLine)
  - feedback paragraph in the blunder-check verdict (card and strip)
affects: [261-06]
tech-stack:
  added: []
  patterns: [copy model returns a feedback record; SolutionVerdict renders it]
key-files:
  created: []
  modified:
    - frontend/src/types/blunderCheck.ts
    - frontend/src/lib/blunderCheckSolution.ts
    - frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx
    - frontend/src/lib/__tests__/blunderCheckSolution.test.ts
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
key-decisions:
  - "Cached pre-release solutions are read with solution.feedback ?? null so they render no paragraph instead of crashing"
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 40a07df2960659f37732b7d0a3a68014c9cf150b
plan_head_after: 38abc532040ef73a357748b2c0c6b194fe1899d7
completed: 2026-11-22
---

# Phase 261 Plan 04: Avatar feedback paragraph Summary

After a caught or missed blunder, the verdict now carries a second paragraph under the points sentence: the neutral Facepalm chip (snapshotted score), the type line and the "hard to catch" line, on the desktop card and the phone / tablet strip.

## What was built

- Wire type: `BlunderTypeLine`, `BlunderFeedback`, and `BlunderSolution.feedback: BlunderFeedback | null` (last field). False-alarm and herring types are unchanged.
- Copy: `SolutionFeedback`, `SolutionCopy.feedback`, private `TYPE_LINE_COPY` and `HARD_TO_CATCH_COPY` (caught / missed), `feedbackCopy()`. False alarm and herring return `feedback: null` (D-05).
- Component: `SolutionVerdict` renders `<p data-testid="blunder-check-solution-feedback">` with `<FacepalmChip testId="blunder-check-facepalm-badge">` followed by the lines. One edit covers card and strip.
- Fixtures: `feedback: null` added to every `BlunderSolution` fixture in four test files.

## Tests

- Tracer: desktop missed blunder with feedback renders the paragraph after the summary with the chip and both lines.
- Copy: all four type lines, null type line, caught/missed hard-to-catch wording, order, unrounded score, null and absent-field feedback, unchanged verdict parts, false alarm and herring null.
- Component: strip after unfolding, caught blunder shows it, null feedback / false alarm / herring show nothing, chip popover names no type and neither "your" nor "their" level.
- Gate: lint, build (tsc -b), full vitest (6762 passed) and knip (exit 0, two pre-existing configuration hints) green.

## Deviations from Plan

None - plan executed exactly as written. Note: the chip's text content reads "Facepalm43%" (words are separate spans, the gap is CSS), so the tracer assertion checks that string rather than "Facepalm 43%"; the chip's aria-label is "Facepalm 43%".

## Known Stubs

None.

## Threat Flags

None. T-261-10 and T-261-11 are mitigated and tested (false alarm shows no paragraph; a solution with no `feedback` field does not crash).

## Self-Check: PASSED

All seven modified files present; commits 9cbcefefa and 38abc5320 are ancestors of HEAD.
