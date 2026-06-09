---
phase: 112-flaws-subtab-card-rework
plan: "03"
subsystem: library/flaws
tags: [frontend, component, tdd, eval-formatter, move-notation]
dependency_graph:
  requires:
    - "112-01 (FlawListItem with white_rating/black_rating + eval_cp/eval_mate before/after)"
    - "112-02 (GET /library/games/{game_id} backend endpoint)"
  provides:
    - "FlawCard component (sibling to LibraryGameCard) — header, 132px board, move+swing, badges, chips, metadata"
    - "formatFlawEval utility — user-POV eval swing formatter (Pitfall 3 fix)"
    - "formatMoveNotation shared primitive extracted from openingInsights.ts (D-04)"
  affects:
    - "frontend/src/lib/openingInsights.ts"
    - "frontend/src/components/library/FlawCard.tsx (new)"
    - "frontend/src/lib/formatFlawEval.ts (new)"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN/REFACTOR flow"
    - "user-POV eval negation for black (Pitfall 3)"
    - "shared move-notation primitive via delegation (D-04)"
    - "severity-colored card accent edge (SEV_BLUNDER/MISTAKE/INACCURACY)"
key_files:
  created:
    - frontend/src/lib/formatFlawEval.ts
    - frontend/src/lib/__tests__/formatFlawEval.test.ts
    - frontend/src/lib/__tests__/openingInsights.test.ts
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
  modified:
    - frontend/src/lib/openingInsights.ts
decisions:
  - "formatMoveNotation extracted as shared primitive; formatCandidateMove delegates to it (D-04) — no duplicated plyIndex/moveNumber logic"
  - "formatFlawEval negates both cp and mate for black users (Pitfall 3) — comment at negation site"
  - "BORDER_COLORS not used in FlawCard (accentColor is severity-based, not result-based)"
  - "formatTimeControl not copied to FlawCard: FlawListItem only has time_control_bucket, not time_control_str"
  - "View-game Button placeholder reserved in content stack for 112-04 (no button rendered in this plan)"
metrics:
  duration: "~7 minutes"
  completed: "2026-06-09"
  tasks_completed: 2
  files_changed: 5
---

# Phase 112 Plan 03: FlawCard component + formatFlawEval utility Summary

New `FlawCard` component (sibling to `LibraryGameCard`) with banded header, 132px miniboard with flaw-move arrow, standard-notation move + user-POV eval swing line, severity badge, family-colored tag chips, TagLegend, and metadata block. Shared `formatMoveNotation` primitive extracted from `openingInsights.ts`; `formatFlawEval` utility handles user-POV negation and mate-sign formatting (Pitfall 3).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests for formatFlawEval + formatMoveNotation | 7e76e2c3 | formatFlawEval.test.ts, openingInsights.test.ts |
| 1 GREEN | formatMoveNotation + formatFlawEval utilities | f96494aa | openingInsights.ts, formatFlawEval.ts |
| 2 RED | Failing tests for FlawCard component | cde6c4e7 | FlawCard.test.tsx |
| 2 GREEN | FlawCard component implementation | d7240e22 | FlawCard.tsx, FlawCard.test.tsx (updated) |

## Key Changes

### formatMoveNotation (openingInsights.ts)
Extracted as exported shared primitive (D-04):
- `formatMoveNotation(plyIndex: number, san: string): string` — even plyIndex = white mover ("N.san"), odd = black mover ("N...san")
- `formatCandidateMove` refactored to delegate: `return formatMoveNotation(entrySanSequence.length, candidateMoveSan)` — no behavior change, no duplicated logic

### formatFlawEval.ts (new)
User-POV eval swing formatter:
- `applyUserPov`: negates both `evalCp` and `evalMate` when `userColor === 'black'`
  (Pitfall 3 fix — without negation, a black user's blunder shows a "positive" swing)
- `formatFlawEvalPart`: mate takes priority over cp; mate = `#${N}`, cp = `formatSignedEvalPawns(cp/100)`, null = `—`
- Returns `"${before} → ${after}"` swing string

### FlawCard.tsx (new)
New card component following the LibraryGameCard visual language:
- `<Card as="article" accentColor={severityColor} overflowVisible>` with severity-based left accent edge
- Banded `CardHeader` with desktop single-line / mobile two-line names+ratings + exact-ply platform deep-link
- 132px `LazyMiniBoard` with flaw-move arrow (SEV_BLUNDER color), board flipped when user is black
- Move notation via `formatMoveNotation` (D-04 — no local helper); eval swing via `formatFlawEval` (Pitfall 3)
- `SeverityBadge` (count=1), `TagChip` row (`definition={false}`), `TagLegend`
- Desktop flex-wrap / mobile flex-col metadata (CLAUDE.md mobile parity)
- All colors from `theme.ts`; `text-sm` floor; `data-testid` per CLAUDE.md browser-automation rules
- Placeholder reserved at bottom of content stack for "View game" Button (112-04)
- T-112-06 mitigated: `rel="noopener noreferrer"` on external platform link

## TDD Gate Compliance

- RED commit (Task 1): `7e76e2c3` — `test(112-03): add failing tests for formatFlawEval + formatMoveNotation (RED)`
- GREEN commit (Task 1): `f96494aa` — `feat(112-03): implement formatMoveNotation + formatFlawEval utilities (GREEN)`
- RED commit (Task 2): `cde6c4e7` — `test(112-03): add failing tests for FlawCard component (RED)`
- GREEN commit (Task 2): `d7240e22` — `feat(112-03): implement FlawCard component (GREEN)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tooltip mock missing in FlawCard test**
- **Found during:** Task 2 test run
- **Issue:** Radix `Tooltip` requires a `TooltipProvider` ancestor; jsdom tests had none, throwing `"Tooltip must be used within TooltipProvider"`.
- **Fix:** Added `vi.mock('@/components/ui/tooltip', ...)` stub (same pattern as `GameCard.test.tsx`).
- **Files modified:** `FlawCard.test.tsx`
- **Commit:** d7240e22

**2. [Rule 1 - Bug] IntersectionObserver stub not a constructor**
- **Found during:** Task 2 test run
- **Issue:** `vi.fn().mockImplementation(...)` is not a class constructor; `LazyMiniBoard` uses `new IntersectionObserver(...)` which threw.
- **Fix:** Replaced with `class MockIntersectionObserver` using `vi.stubGlobal` (same pattern as `GameCard.test.tsx`).
- **Files modified:** `FlawCard.test.tsx`
- **Commit:** d7240e22

**3. [Rule 1 - Bug] BORDER_COLORS and formatTimeControl unused**
- **Found during:** Lint run after GREEN
- **Issue:** `BORDER_COLORS` (result-based) was copied from LibraryGameCard but FlawCard uses severity-based accentColor. `formatTimeControl` was copied but `FlawListItem` has no `time_control_str` field (only `time_control_bucket`).
- **Fix:** Removed both unused definitions; removed `WDL_BORDER_*` imports.
- **Files modified:** `FlawCard.tsx`
- **Commit:** d7240e22

## Known Stubs

- **"View game" Button placeholder** — `FlawCard.tsx` has a comment `{/* Placeholder: "View game" Button added in 112-04 */}` at the bottom of the content stack. This is intentional per the plan scope; 112-04 will add the button and modal. The FlawCard surface itself is fully functional.

## Threat Flags

None. T-112-06 (reverse-tabnabbing) mitigated via `rel="noopener noreferrer"` on the platform link. No new unplanned security surface introduced.

## Self-Check: PASSED

- [x] `frontend/src/lib/formatFlawEval.ts` exists with `formatFlawEval` export
- [x] `frontend/src/lib/openingInsights.ts` exports `formatMoveNotation`; `formatCandidateMove` calls `formatMoveNotation(entrySanSequence.length, candidateMoveSan)`
- [x] `frontend/src/components/library/FlawCard.tsx` exists with `flaw-card-{game_id}-{ply}` testid pattern
- [x] `frontend/src/types/library.ts` FlawListItem has `eval_cp_before`, `eval_mate_before`, `eval_cp_after`, `eval_mate_after`, `white_rating`, `black_rating` and no `es_before`/`es_after`
- [x] All tests pass: 870/870 (31 new tests added)
- [x] Lint clean
- [x] Commits 7e76e2c3, f96494aa, cde6c4e7, d7240e22 present in git log
