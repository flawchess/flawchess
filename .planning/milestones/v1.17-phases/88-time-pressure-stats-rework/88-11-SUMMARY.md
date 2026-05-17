---
phase: 88-time-pressure-stats-rework
plan: 11
subsystem: web
tags: [endgame-analytics, time-pressure, frontend, aria, codegen-consumer, gap-closure]

requires:
  - phase: 88
    provides: PressureQuintileBullet TS type, EndgameTimePressureCard + EndgameTimePressureSection components, getPressureBinBand codegen helper
  - phase: 88.1
    provides: 88-09 backend cohort_score → opp_score rename, 88-10 MIN_GAMES_* + getPressureBinBand codegen exports
provides:
  - PressureQuintileBullet.cohort_score → opp_score (frontend TS mirrors 88-09 backend Pydantic).
  - EndgameTimePressureCard now imports MIN_GAMES_PER_TC_CARD, MIN_GAMES_PER_PRESSURE_BIN, getPressureBinBand from @/generated/endgameZones. Local literals deleted.
  - QuintileRow band lookup uses getPressureBinBand(tc, bin.quintile_index) with early-return on null. Unsafe `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q as 0|1|2|3|4]!` pattern removed (CLAUDE.md noUncheckedIndexedAccess compliance).
  - Popover copy switched to "vs opponent" + new methodology block describing the same-game opp-quintile two-sample test (D-07).
  - EndgameTimePressureSection's broken `aria-labelledby="time-pressure-heading"` (no such id existed) replaced with self-contained `aria-label="Time pressure analysis"`.
  - 3 new RED tests in EndgameTimePressureCard.test.tsx assert (a) opp_score consumed in baselineLabel, (b) popover copy says "opponent" not "cohort", (c) out-of-range quintile_index handled gracefully.
  - 1 new IN-05 ARIA-wiring test in EndgameTimePressureSection.test.tsx asserts aria-label is set and aria-labelledby is absent.
  - Section test fixture renamed cohort_score → opp_score.
affects:
  - none (closes Phase 88.1 gap-closure waves; Plan 88-12 will recalibrate PRESSURE_BIN_SCORE_NEUTRAL_ZONES numerics independently)

tech-stack:
  added: []
  patterns:
    - "Codegen consumer-side pattern: importing the typed helper from `@/generated/endgameZones` instead of indexing the raw `Record<TC, Record<0|1|2|3|4, Band>>` with `!`. The helper hides the cast inside a defensive range check and lets the consumer early-return cleanly when the index is out of range — `noUncheckedIndexedAccess`-clean without per-call-site assertions."
    - "Self-contained section ARIA: when a `<section>` needs an accessible name but its visual heading lives in a parent file, prefer `aria-label` on the section over `aria-labelledby` pointing at a sibling id. `aria-labelledby` only works when both elements are in the same render tree and the id is unique; cross-file id wiring is fragile and breaks silently when the heading moves."

key-files:
  created: []
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx

key-decisions:
  - "Picked Plan 88-11 action option A for the ARIA fix (aria-label on the section, no <h2> id wiring) over option B (add id to the visible <h2> in Endgames.tsx). Option A is self-contained, doesn't depend on a sibling element in a parent file, and matches the existing aria-label patterns on other section wrappers — fewer moving parts."
  - "Used fireEvent.click on the MetricStatPopover trigger (rather than installing @testing-library/user-event) to drive Radix popover open-state in jsdom. Existing tests in this file already render Radix Portal content via the same approach."
  - "Static-source assertion (`grep` gate in the verify command + a runtime DOM assertion together) covered the popover-copy check rather than mocking the popover. The DOM-based check via fireEvent is more robust to future popover refactors than a `toString()`-style source-string match."
  - "Out-of-range quintile_index test uses a runtime-constructed PressureQuintileBullet with `quintile_index: 5`. The QuintileRow early-returns null (no glyph) rather than throwing — verified by both `expect(() => renderCard(...)).not.toThrow()` and the absence of the malformed bin's `-value` test-id in the DOM."

patterns-established:
  - "ARIA accessible name on a sectioning element: when the section's name comes from a heading in a parent file or template, prefer `aria-label` over `aria-labelledby` (cross-file id wiring is fragile and silently degrades to no accessible name when the id is missing). Add a test asserting both that `aria-label` is set AND that `aria-labelledby` is null — catches the regression of swapping back to `aria-labelledby` without updating the consumer."
  - "Replacing unsafe Record index access: when CI mandates `noUncheckedIndexedAccess` but a hot path needs to look up by a runtime number, generate a typed helper from the same source-of-truth module rather than asking each call site to write `[i as ...]!`. The helper returns `T | null` and the call site early-returns — one extra line, one fewer foot-gun."

requirements-completed:
  - POLISH-01
  - POLISH-03

duration: ~25min
completed: 2026-05-17
---

# Phase 88.1 Plan 11: Frontend cohort_score → opp_score, codegen consumer, ARIA Summary

Frontend gap-closure mirror of the 88-09 schema rename and 88-10 codegen lift. Three concerns closed in two commits:

1. **Type rename + codegen consumption** (commit `d2e1e877`): `PressureQuintileBullet.cohort_score` → `opp_score`; card pulls `MIN_GAMES_PER_TC_CARD`, `MIN_GAMES_PER_PRESSURE_BIN`, `getPressureBinBand` from `@/generated/endgameZones`; unsafe `[q as 0|1|2|3|4]!` replaced; popover copy switched to "vs opponent" with new methodology block.
2. **ARIA fix + IN-05 test** (commit `89e88edc`): `aria-labelledby="time-pressure-heading"` was dangling (no such id existed in DOM); switched to self-contained `aria-label="Time pressure analysis"`; added the IN-05 test asserting both `aria-label` is set and `aria-labelledby` is absent.

Closes WR-02, WR-03, WR-04 (frontend side), IN-05, IN-06.

## Deviations from Plan

None — plan executed exactly as written. Picked option A for the ARIA fix as the plan recommended (lowest touch). All grep gates passed on first run.

## Verification

| Gate | Result |
|------|--------|
| `grep -v '^//' types/endgames.ts EndgameTimePressureCard.tsx \| grep -cE 'cohort_score\|cohortPct'` | 0 |
| `grep -c "getPressureBinBand" EndgameTimePressureCard.tsx` | 2 |
| `grep -cE "] as 0 \| 1 \| 2 \| 3 \| 4\]!" EndgameTimePressureCard.tsx` | 0 |
| `grep -cE "^const MIN_GAMES_PER_(TC_CARD\|PRESSURE_BIN)" EndgameTimePressureCard.tsx` | 0 |
| `grep -c "opp_score" types/endgames.ts` | 2 |
| `grep -c 'aria-label="Time pressure analysis"' EndgameTimePressureSection.tsx` | 1 |
| `grep -c 'aria-labelledby="time-pressure-heading"' EndgameTimePressureSection.tsx` | 0 |
| `grep -rn 'time-pressure-heading' frontend/src \| wc -l` | 0 |
| `npm test -- --run` | 494 passed (494) |
| `npx tsc --noEmit -p tsconfig.app.json` | exit 0 |
| `npm run lint` | exit 0 |
| `npm run knip` | exit 0 |
| `npm run build` | exit 0 |
| Codegen drift: `git diff --exit-code frontend/src/generated/endgameZones.ts` after re-running `gen_endgame_zones_ts.py` | clean |

## Commits

| Hash | Subject |
|------|---------|
| `d2e1e877` | `feat(88.1-11): rename cohort_score → opp_score and consume codegen exports in EndgameTimePressureCard` |
| `89e88edc` | `fix(88.1-11): replace dangling aria-labelledby with self-contained aria-label` |

## Self-Check: PASSED

- FOUND: frontend/src/types/endgames.ts (modified — `opp_score` field, retired D-05 comment)
- FOUND: frontend/src/components/charts/EndgameTimePressureCard.tsx (modified — codegen imports, getPressureBinBand consumer, "vs opponent" copy)
- FOUND: frontend/src/components/charts/EndgameTimePressureSection.tsx (modified — aria-label replaces aria-labelledby)
- FOUND: frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx (modified — 3 new opp-quintile tests, makeBin signature updated)
- FOUND: frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx (modified — IN-05 ARIA test, opp_score fixture)
- FOUND: commit d2e1e877
- FOUND: commit 89e88edc
