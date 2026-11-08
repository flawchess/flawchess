---
phase: 242-openings-stats-insights-rework
plan: 07
subsystem: ui
tags: [react, openings, insights, findings, verdict, umami, vitest]

requires:
  - phase: 242-02
    provides: "POST /insights/openings 99%-gated card lists, *_not_clear lists and counts, is_current, ci99/eval_ci99 fields"
  - phase: 242-04
    provides: "openingVerdict primitives, VerdictBar, EvalVerdictPopover"
  - phase: 242-06
    provides: "StatsTab / RepertoireTable, ScoreVerdictPopover, formatScorePercent"
provides:
  - "FindingCard: move-led finding card (120px board arrow, score popover, WDL bar, baseline-centred eval bar, why line, Moves/Games links)"
  - "OpeningFindings: 'Moves that cost you' / 'Moves that work' for the selected colour above the repertoire table, phone Show more, collapsed 'Not clear yet (n)', empty-state copy, loading/error branches"
  - "whyLine, findingMoveText, findingArrows helpers; TS mirrors of the 242-02 insights fields"
  - "Umami panel target opening-findings-unclear"
affects: [242-08, 242-09]

actuals:
  tokens: 28000
  tasks: 2
  commits: 2
plan_head_before: 24a636d31756b2f0f53192febb2d8d07d2ee54b7
plan_head_after: b80165cc1c650aedc6dc4100a43351c8e9368cda

tech-stack:
  added: []
  patterns:
    - "Colour switch is client-side: one request with color 'all', section lists picked via a template-literal key (white_weaknesses, ..._not_clear, ..._not_clear_count)"
    - "Phone density via max-md:hidden on the wrapper of cards at index >= INITIAL_VISIBLE_PHONE plus a md:hidden button, no JS viewport detection"
    - "Testids carry only kind keys and indices so popover-open targets never contain SAN/FEN/names"

key-files:
  created:
    - frontend/src/components/openings/stats/FindingCard.tsx
    - frontend/src/components/openings/stats/OpeningFindings.tsx
    - frontend/src/components/openings/__tests__/OpeningFindings.test.tsx
  modified:
    - frontend/src/types/insights.ts
    - frontend/src/lib/openingVerdict.ts
    - frontend/src/lib/openingInsights.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/__tests__/openingVerdict.test.ts
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "findingMoveText and findingArrows live in lib/openingInsights.ts, not FindingCard.tsx: react-refresh/only-export-components forbids non-component exports from a component file"
  - "Verdict games floor for a finding uses n_games (cards always have >= 20), the eval z-test gate stays the backend eval_confidence"
  - "The 'Not clear yet' rows use ARROW_NEUTRAL and UNRELIABLE_OPACITY (never the red/green zone colours), per D-09/D-10"
  - "Cards render the full-line subtitle as entry sequence plus the candidate move, so the PGN matches the board arrow's move"
  - "Old Insights tab components (OpeningInsightsBlock, OpeningFindingCard) are untouched; plan 242-08 removes them"

patterns-established:
  - "Findings section mounted in StatsTab above RepertoireTable, fed by debouncedFilters and the existing handleOpenFinding / handleOpenFindingGames deep links"

requirements-completed: [D-00, D-04, D-08, D-09, D-10, D-11]

coverage:
  - id: D1
    description: "Stats tab shows Moves that cost you / Moves that work for the selected colour from the 99%-gated backend lists, card layout per D-00, deep links to Moves and Games"
    requirement: "D-00"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#shows only the selected colour and leads each card with the move"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#calls the Moves and Games callbacks with the finding"
        status: pass
    human_judgment: false
  - id: D2
    description: "Phone shows 2 cards then Show more, tracked once on expand only (opening-insights-more)"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#hides cards 3-5 on phones until Show more, and tracks the expand once"
        status: pass
    human_judgment: false
  - id: D3
    description: "Collapsed faded Not clear yet (n) list with the backend count, tracked on expand (opening-findings-unclear)"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#expands to the faded, uncoloured rows and tracks the expand once"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty-state copy with singular/plural lean text; older games chip on stale findings"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#OpeningFindings empty state"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/OpeningFindings.test.tsx#marks findings from older games with a chip and leaves current ones bare"
        status: pass
    human_judgment: false
  - id: D5
    description: "Visual fidelity of the card layout against sketch 012 and the pulse highlight on the Moves deep link in the real app"
    verification: []
    human_judgment: true
    rationale: "Layout, phone density and the pulse highlight need a browser pass (planned for /gsd-verify-work); jsdom cannot assess them"

duration: ~25min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 07: Findings on the Stats tab Summary

**The Stats tab now opens with the selected colour's 99%-gated "Moves that cost you" and "Moves that work" finding cards (move-led, baseline-centred eval bar, why line, Moves/Games deep links), a phone "Show more" at 2 cards, a collapsed faded "Not clear yet (n)" list and the "Nothing clear yet as Black." empty state above the repertoire table.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 10 (3 created, 7 modified)

## Accomplishments
- FindingCard: header "After {move}" with an "older games" chip (title "Last seen {month year}"), opening name without ECO plus the full PGN line, 120 px board with a red (weakness) or green (strength) arrow, "You score X%" with ScoreVerdictPopover (99% CI, p vs 50%, n), MiniWDLBar, VerdictBar "Eval after opening" centred on the colour baseline with EvalVerdictPopover, the why sentence only when the eval verdict is better/worse, and Moves/Games link buttons.
- OpeningFindings: one `useOpeningInsights` request (colour 'all'), client-side colour pick, skeleton, error with retry, two subsections in a 1/2-column grid.
- D-08 to D-11: `INITIAL_VISIBLE_PHONE = 2`, md:hidden Show more with aria-expanded and a single `panel-open` `opening-insights-more` on expand; "Not clear yet (n)" using the backend `*_not_clear_count`, rows in backend order, faded and uncoloured, tracked as `opening-findings-unclear`; empty-state copy with singular/plural.
- TS mirrors for ci99/eval_ci99/is_current and the four not-clear lists, counts and cutoffs; `whyLine` helper; StatsTab/Openings wiring of the existing deep-link handlers.

## Task Commits

1. **Task 1: Tracer, 99%-gated finding cards above the repertoire table** - `8b6f2fbbb` (feat)
2. **Task 2: Show more, Not clear yet, empty state, tracking and tests** - `b80165cc1` (test)

The Task 2 behaviours (Show more, Not clear yet, empty state, tracking registration) were implemented in the Task 1 commit alongside the cards because they live in the same component; Task 2 added the test suite that locks them. The `opening-findings-unclear` target was registered in `analytics.ts` in the Task 1 commit.

## Files Created/Modified
- `frontend/src/components/openings/stats/FindingCard.tsx` - move-led finding card, OlderGamesChip, FindingSubtitle
- `frontend/src/components/openings/stats/OpeningFindings.tsx` - findings section with Show more, Not clear yet and empty state
- `frontend/src/components/openings/__tests__/OpeningFindings.test.tsx` - 15 behaviour tests
- `frontend/src/lib/openingVerdict.ts` - `whyLine`
- `frontend/src/lib/openingInsights.ts` - `findingMoveText`, `findingArrows`
- `frontend/src/types/insights.ts` - 242-02 field mirrors
- `frontend/src/lib/analytics.ts` - `opening-findings-unclear` panel target
- `frontend/src/pages/openings/StatsTab.tsx`, `frontend/src/pages/Openings.tsx` - mount and wiring

## Decisions Made
See key-decisions above. The old Insights tab, its block and card stay in place until 242-08.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Non-component exports moved out of FindingCard.tsx**
- **Found during:** Task 1 (lint)
- **Issue:** `react-refresh/only-export-components` rejected `findingMoveText` and `findingArrows` exported next to components.
- **Fix:** Moved both helpers to `frontend/src/lib/openingInsights.ts`; FindingCard and OpeningFindings import them from there.
- **Files modified:** frontend/src/lib/openingInsights.ts, FindingCard.tsx, OpeningFindings.tsx
- **Verification:** `npm run lint`, `npm run build`, `npm run knip` clean
- **Committed in:** 8b6f2fbbb

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** None; the contract surface (FindingCard, OpeningFindings, whyLine) is as specified.

## Issues Encountered
None. Full frontend suite: 5702 tests pass; lint, build (tsc -b) and knip exit 0 (knip prints two pre-existing config hints only).

## Known Stubs
None.

## Next Phase Readiness
- Ready for 242-08 (remove the Insights subtab, mobile tab, route and the now-unused OpeningInsightsBlock / OpeningFindingCard).
- Browser UAT outstanding for /gsd-verify-work: owner data shows the empty-state copy at 99%, phone shows 2 cards plus Show more, Moves link opens the Moves tab with the pulse highlight.

## Self-Check: PASSED
- FOUND: FindingCard.tsx, OpeningFindings.tsx, OpeningFindings.test.tsx
- FOUND commits 8b6f2fbbb, b80165cc1 (ancestors of HEAD)
- Acceptance greps: OpeningFindings in StatsTab (2), useOpeningInsights in OpeningFindings (2), `_not_clear_count` in insights.ts (4), "older games" in FindingCard (1), `opening_eco` in FindingCard (0), `opening-findings-unclear` in analytics (1), `opening-insights-more` in OpeningFindings (1), `INITIAL_VISIBLE_PHONE = 2` present, "Nothing clear yet" present
