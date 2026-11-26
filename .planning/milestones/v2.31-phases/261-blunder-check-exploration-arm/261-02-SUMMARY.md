---
phase: 261-blunder-check-exploration-arm
plan: 02
subsystem: frontend
tags: [facepalm, chip, popover, theme, blunder-check]
requires: []
provides:
  - FacepalmChip neutral form (bare score + caller testId)
  - FacepalmAudience and facepalmScoreMeaning(audience)
  - FACEPALM_NEUTRAL / FACEPALM_NEUTRAL_BG theme tokens, FACEPALM_NEUTRAL_STYLE
affects: [261-04]
tech-stack:
  added: []
  patterns: [discriminated-union props for chip forms]
key-files:
  created:
    - frontend/src/components/library/__tests__/FacepalmChip.test.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/facepalm.ts
    - frontend/src/components/library/FacepalmChip.tsx
    - frontend/src/components/library/FacepalmBadgePopover.tsx
    - frontend/src/components/library/FacepalmExplanation.tsx
    - frontend/src/components/analysis/FacepalmMoveChip.tsx
    - frontend/src/components/library/__tests__/FacepalmExplanation.test.tsx
    - frontend/src/components/library/__tests__/FacepalmBadgePopover.test.tsx
    - frontend/src/lib/__tests__/facepalm.test.ts
key-decisions:
  - "Neutral drill chip uses the existing flaw-family grey (FACEPALM_NEUTRAL aliases FAM_NEUTRAL), so the type never shows through the tint (D-02)"
  - "Neutral wording: 'a player at that level'; popover keeps the 70% facepalm-blunder cut line"
requirements-completed: [D-01, D-02]
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: b9ebe962a4065cb8b7151f20c60220ac91d553c8
plan_head_after: aa9e126149383811c567c578aaaa6d1b47555369
duration: 20min
completed: 2026-11-22
---

# Phase 261 Plan 02: Neutral Facepalm chip Summary

The library Facepalm chip now has a neutral form fed by a bare score and a caller-supplied testid: same pill, Gauge icon and "Facepalm N%" (floored), same popover, but a grey tint, no facepalm-type line, and a score-meaning sentence saying "a player at that level".

## What was built

- `theme.ts`: `FACEPALM_NEUTRAL`, `FACEPALM_NEUTRAL_BG` (aliases of the private flaw-family grey).
- `facepalm.ts`: `FacepalmAudience = 'self' | 'opponent' | 'neutral'`; `facepalmScoreMeaning(audience = 'self')` replaces the boolean; `FACEPALM_NEUTRAL_STYLE`.
- `FacepalmExplanation` / `FacepalmBadgePopover`: optional `type`, `audience` (replaces `byOpponent` on the explanation). Without a type there is no type line and the aria-label is `Facepalm N%`.
- `FacepalmChip`: discriminated union of the typed form `{score, type, gameId, ply}` (output unchanged) and the neutral form `{score, testId}`. FlawCard.tsx is untouched.
- `FacepalmMoveChip` passes `audience={byOpponent ? 'opponent' : 'self'}`; its own `byOpponent` prop stays.
- Tests: new `FacepalmChip.test.tsx`; neutral cases in the explanation and popover tests; `facepalm.test.ts` opponent expectation moved from the boolean `true` to `'opponent'` (invisible to tsc), plus a `'neutral'` expectation.

Contract for plan 04: `<FacepalmChip score={feedback.score} testId="blunder-check-facepalm-badge" />`.

## Verification

Full frontend gate green in this worktree: `npm run lint`, `npm run build` (tsc -b), `npm test` (380 files, 6746 tests), `npm run knip` (exit 0).

## Deviations from Plan

None - plan executed exactly as written. (Between the two task commits the pre-existing explanation test that passed `byOpponent` was stale by design; Task 2 updated it, per the plan's task split.)

## Cross-phase note

The doc comment above `facepalmScoreMeaning` is the only expected conflict with Phase 260 (it rewrites the "Shared by" line, this plan the level-word/audience line). Keep Phase 260's "Shared by" line and this plan's audience line.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- All listed files exist; commits f796d9980 and aa9e12614 are ancestors of HEAD.
