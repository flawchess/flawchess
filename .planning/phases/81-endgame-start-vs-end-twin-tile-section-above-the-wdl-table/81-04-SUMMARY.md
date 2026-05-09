---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
plan: 04
subsystem: frontend
tags: [endgames, page-integration, twin-tile, accordion, react]
requires:
  - 81-03 (EndgameStartVsEndSection component)
  - 81-01 (backend EndgamePerformanceResponse fields)
provides:
  - Page-level wire-up of EndgameStartVsEndSection inside Endgames.tsx
  - Two new accordion concept paragraphs (entry-eval + absolute endgame score)
  - data-testid="endgame-performance-section" on EndgamePerformanceSection (additive)
  - Page-level integration test (DOM order, accordion paragraphs, D-21 negative scope)
affects:
  - frontend/src/pages/Endgames.tsx (modified)
  - frontend/src/components/charts/EndgamePerformanceSection.tsx (modified — testid only)
  - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx (NEW)
tech-stack:
  added: []
  patterns:
    - Page-level integration test with full-page render + targeted hook/component mocks
    - Radix accordion content opens via fireEvent.click on the accordion trigger in tests
    - "We can't tell" framing for non-significant statistical verdicts (CONTEXT specifics)
key-files:
  created:
    - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx
  modified:
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
decisions:
  - "Page-level test mocks heavy chart components (Conv/Recov, Score Gap, Clock Pressure, Time Pressure, ELO timeline, WDL chart, GameCardList) and the Insights block, but renders EndgameStartVsEndSection and EndgamePerformanceSection for real so the assertions read against the genuine DOM the user will see"
  - "Mocks data hooks (useEndgameOverview, useEndgameGames, useCachedEndgameInsights, useEndgameInsights, useActiveJobs) at the module level rather than wiring up TanStack Query — keeps the test deterministic and avoids the network-mocking surface area"
  - "Wraps the page in TooltipProvider in the test render — matches App.tsx's production wrapping so radix's TooltipPrimitive resolves its required context"
  - "Radix Accordion content is unmounted when collapsed; the D-13/D-14 paragraph tests open the accordion via fireEvent.click on its trigger before querying paragraph content"
  - "Used 'we can\\'t tell' framing in both new paragraphs (matching the CONTEXT specifics) rather than the colder default 'not statistically significant' phrasing — reads better in the explainer surface and ties the user back to the deliberate flat-verdict design choice"
  - "Tile 2 paragraph references 'Opponent Strength filter' as plain text only (no Link / anchor) per D-13 / WARNING 1; the existing rating-changes caveat already cross-references the same filter, keeping the language consistent"
metrics:
  duration_minutes: 12
  completed: 2026-05-09
---

# Phase 81 Plan 04: Endgames Page Wire-Up Summary

Wired the `EndgameStartVsEndSection` component (built in Plan 03) into `Endgames.tsx` directly above the existing WDL table, added two concept-explainer paragraphs to the existing `endgame-concepts-trigger` accordion, and added the `data-testid="endgame-performance-section"` anchor needed for the page-level DOM-order assertion. This lands the user-visible deliverable for Phase 81.

## What Was Built

- **`frontend/src/pages/Endgames.tsx`** (modified)
  - Added import for `EndgameStartVsEndSection` from `@/components/charts/EndgameStartVsEndSection`.
  - Rendered `<EndgameStartVsEndSection data={perfData} />` between `</Accordion>` and the existing `<div className="charcoal-texture rounded-md p-4"><EndgamePerformanceSection ...></div>`. The new section reuses the parent `showPerfSection` predicate, so it auto-hides when no endgame games exist (D-06 satisfied via inheritance).
  - Inserted two new `<p>` blocks into the `endgame-concepts-trigger` accordion content, immediately AFTER the Recovery `<p>` and BEFORE the rating-changes caveat (D-14 ordering). Both use bolded leads matching the section / popover labels:
    - `<strong>Avg eval at endgame entry:</strong>` describes the metric, mate exclusion, the 0-pawn baseline, and the "we can't tell" framing for non-significant verdicts.
    - `<strong>Absolute endgame score:</strong>` describes the metric, the 50% break-even baseline, and references the **Opponent Strength filter** as plain text (no anchor / link) per D-13 / WARNING 1. Same "we can't tell" framing.

- **`frontend/src/components/charts/EndgamePerformanceSection.tsx`** (modified — additive only)
  - Added `data-testid="endgame-performance-section"` to the outermost `<div className="space-y-4">`. No behavior change. This anchors the page-level DOM-order assertion against the wire-up.

- **`frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`** (NEW)
  - 6 page-level integration tests covering D-01, D-13, D-14, and D-21 negative-scope:
    1. DOM order: `endgame-start-vs-end-section` appears BEFORE `endgame-performance-section` (verified via `compareDocumentPosition`).
    2. Section hidden when `perfData.endgame_wdl.total === 0` — `endgame-start-vs-end-section` is not in the DOM.
    3. Both new paragraph leads ("Avg eval at endgame entry:", "Absolute endgame score:") are present after the accordion is opened (radix collapses content when the accordion item is closed, so the test clicks the trigger first).
    4. Paragraph order: Recovery → Avg eval at endgame entry → Absolute endgame score → rating-changes caveat (queried via `querySelectorAll('p')` inside the accordion item, ordered by DOM index).
    5. D-21 negative scope: `perf-wdl-table` (or `perf-wdl-cards`), `score-gap-difference` (or its mobile variant), and `endgame-score-timeline-chart` are all still present.
    6. The literal phrase "Opponent Strength filter" appears in the rendered DOM (covered by both the new paragraph and the existing rating-changes caveat).
  - Mocks: `EndgameInsightsBlock`, `EndgameWDLChart`, `EndgameConvRecovChart`, `EndgameScoreGapSection`, `EndgameClockPressureSection` (incl. `ClockDiffTimelineChart`), `EndgameTimePressureSection`, `EndgameEloTimelineSection`, `GameCardList`. Hooks: `useEndgameOverview`, `useEndgameGames`, `useCachedEndgameInsights`, `useEndgameInsights`, `useActiveJobs`. Recharts' `ResponsiveContainer` swapped for a fixed-size shim so `EndgameScoreOverTimeChart` actually emits its testids inside jsdom.

## Tasks & Commits

| Task | Name                                                                              | Commit   |
| ---- | --------------------------------------------------------------------------------- | -------- |
| 1    | Wave 0 — write page-level integration test (RED)                                  | b8b3290a |
| 2    | Wire EndgameStartVsEndSection + accordion paragraphs + perf-section testid (GREEN) | dee00a2b |

## Verification

- `cd frontend && npm test -- --run src/pages/__tests__/Endgames.startVsEnd.test.tsx` — 6/6 passed
- `cd frontend && npm test -- --run` — 337/337 passed (full FE suite, no regressions; was 331 before this plan + 6 new = 337)
- `cd frontend && npm run lint` — 0 errors / 0 warnings (1 unused-eslint-disable directive caught and removed during execution)
- `cd frontend && npx tsc --noEmit` — 0 errors (strict, `noUncheckedIndexedAccess` enabled)
- `cd frontend && npm run knip` — 0 issues (Plan 03's exports are now consumed by the wire-up)
- `cd frontend && npm run build` — clean build (vite + PWA + prerender all green)
- Acceptance grep checks (all from `<acceptance_criteria>`):
  - `grep -c 'EndgameStartVsEndSection' frontend/src/pages/Endgames.tsx` → 2 (>= 2)
  - `grep -c 'Avg eval at endgame entry' frontend/src/pages/Endgames.tsx` → 1 (>= 1)
  - `grep -c 'Absolute endgame score' frontend/src/pages/Endgames.tsx` → 1 (>= 1)
  - `grep -c 'Opponent Strength filter' frontend/src/pages/Endgames.tsx` → 2 (>= 1; the new D-13 paragraph + the existing rating-changes caveat both reference it)
  - `grep -cE '<strong>(Conversion|Parity|Recovery):' frontend/src/pages/Endgames.tsx` → 3 (>= 3 — existing paragraphs unchanged, D-21 holds)
  - `grep -c 'data-testid="endgame-performance-section"' frontend/src/components/charts/EndgamePerformanceSection.tsx` → 1 (>= 1)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Page render needs TooltipProvider context**
- **Found during:** Task 1 (running the new test for the first time)
- **Issue:** Radix's `<Tooltip>` (used inside `EndgamesPage` for the mobile filter button) throws `'Tooltip' must be used within 'TooltipProvider'` at mount under jsdom because the test renders the page outside the App-level provider tree.
- **Fix:** Imported `TooltipProvider` from `@/components/ui/tooltip` and wrapped the page render helper. Mirrors what `App.tsx` does in production (line 593) — same provider, same context.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`
- **Commit:** Folded into Task 2 (b8b3290a was the RED commit; the fix landed before that test could go GREEN, on dee00a2b alongside the wire-up).

**2. [Rule 3 - Blocking] Radix Accordion does not mount AccordionContent when closed**
- **Found during:** Task 2 (first GREEN attempt — D-13 / D-14 / Opponent Strength tests still failing)
- **Issue:** Tests for accordion paragraph presence + ordering initially queried via `screen.getByText` against the closed accordion. Radix unmounts the AccordionContent subtree until the trigger is opened, so `Recovery:`, `Avg eval at endgame entry:`, and `Opponent Strength filter` were all absent from the DOM and the assertions failed.
- **Fix:** Added an `openConceptsAccordion(container)` helper that runs `fireEvent.click` (inside `act`) on the first `[data-testid="endgame-concepts-trigger"] [data-slot="accordion-trigger"]` button before any paragraph queries. Once the accordion is open, all 7 of the original `<p>` blocks plus the 2 new ones are in the DOM and the order assertion reads them via `querySelectorAll('p')`.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`
- **Commit:** dee00a2b (folded into Task 2's GREEN commit since the helper was added before any paragraph test could go green).

**3. [Rule 3 - Blocking] Page renders desktop + mobile layouts simultaneously in jsdom**
- **Found during:** Task 2 (second GREEN attempt)
- **Issue:** `EndgamesPage` ships separate desktop sidebar and mobile drawer layouts — both render at all times under jsdom (no media queries gating them at the React level — they're CSS-class hidden), so the same accordion content shows up twice. `screen.getByText(/Avg eval at endgame entry:/)` failed with "Found multiple elements".
- **Fix:** Switched D-13 / Opponent-Strength assertions to `getAllByText(...).length > 0` (any non-empty match is fine since both copies are valid). The D-14 ordering assertion already scopes its query to the FIRST `[data-testid="endgame-concepts-trigger"]` accordion item, so duplicate mounting is benign there.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`
- **Commit:** dee00a2b.

### Plan-deviation notes (no functional change)

- The plan's `<action>` block sketched the new paragraph wording inline. I tightened the prose slightly: dropped one em-dash per paragraph (CLAUDE.md communication-style guidance), kept the bolded leads / mate-exclusion / 50% baseline / "we can't tell" content the plan called for. The literal phrase "Opponent Strength filter" appears as plain text in the Tile 2 paragraph as required.
- The plan listed "TooltipProvider" wrapping as an optional fallback in the test setup. In practice the page mounts a `<Tooltip>` unconditionally on the mobile filter button, so the wrapper is mandatory under jsdom — there is no rendering path that avoids the missing-context error without it.

## TDD Gate Compliance

Per-task TDD cycle followed:
- Task 1 → `test(81-04)` commit (RED — 6/6 page tests fail because EndgameStartVsEndSection is not yet wired)
- Task 2 → `feat(81-04)` commit (GREEN — 6/6 page tests pass after wire-up + accordion paragraphs + data-testid)
- No REFACTOR commit needed — wire-up is small, accordion paragraphs are static prose, the testid-add on EndgamePerformanceSection is a one-line additive change.

## Known Stubs

None. The wire-up is fully functional. `EndgameStartVsEndSection` consumes real `EndgamePerformanceResponse` fields (Plan 01 backend, Plan 02 frontend types, Plan 03 component) and renders against live data. No mocks or placeholders in production code.

## Self-Check: PASSED

- `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — FOUND
- `frontend/src/pages/Endgames.tsx` — modified (verified by `git diff`)
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — modified (verified by `git diff`)
- Commit `b8b3290a` — FOUND on branch `worktree-agent-a80dd04a4a67a9851`
- Commit `dee00a2b` — FOUND on branch `worktree-agent-a80dd04a4a67a9851`
- All `<must_haves>` truths verified by passing tests + grep on the modified files
- All acceptance-criteria grep checks PASS (see Verification section above)
- Full FE test suite (337/337) + lint + tsc + knip + build all GREEN
