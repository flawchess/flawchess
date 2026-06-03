---
phase: quick-260603-pgv
plan: 01
subsystem: frontend/openings
tags: [frontend, openings, insights, stats, confidence, dimming]
requires: []
provides:
  - "Per-row (score/eval) confidence dimming in OpeningFindingCard and OpeningStatsCard"
  - "Updated FindingsSection info-popover copy describing per-stat dimming"
affects:
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
tech-stack:
  added: []
  patterns:
    - "Per-cell opacity dim driven by isConfident(...) on each stat row, reusing UNRELIABLE_OPACITY"
key-files:
  created: []
  modified:
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/lib/theme.ts
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
decisions:
  - "Eval row dims only when an eval value exists (hasMgEval); the EvalCpuPlaceholder and no-eval '—' cases are never dimmed"
  - "Removed dead MIN_GAMES_OPENING_ROW from theme.ts (knip would otherwise fail on the unused export)"
metrics:
  duration: ~12m
  completed: 2026-06-03
---

# Quick Task 260603-pgv: Per-Row Confidence Dimming in Opening Cards Summary

Replaced whole-card opacity dimming with per-row dimming in the Openings Stats and Insights cards: the Score row dims only when score confidence is low, and the Eval row dims only when eval confidence is low, so a reliable stat stays at full opacity even when its sibling is noisy.

## What Changed

- **OpeningFindingCard.tsx** — removed the `isUnreliable` whole-card dim (and dropped `MIN_GAMES_FOR_RELIABLE_STATS` from the import, now unused). Added `dimScoreRow = !isConfident(finding.confidence)` and `dimEvalRow = hasMgEval && !isConfident(finding.eval_confidence)`, applied as `opacity: UNRELIABLE_OPACITY` to both cells of each row (bullet div + text span) inside the single shared `scoreEvalBlock` const (covers mobile + desktop).
- **OpeningStatsCard.tsx** — removed the `isCardMuted` whole-card dim and the `MIN_GAMES_OPENING_ROW` import. Added the same two per-row flags (score driven by `computeScoreConfidence(...)`, eval by the literal `eval_confidence` field) and applied the per-cell opacity style identically.
- **theme.ts** — removed the now-dead `MIN_GAMES_OPENING_ROW` export and its comment.
- **OpeningInsightsBlock.tsx** — rewrote the FindingsSection info-popover first paragraph to describe per-stat dimming ("The Score or Eval value is dimmed individually when that stat isn't statistically distinguishable from chance, or rests on too few games"). No em-dashes.
- **Tests** — replaced the three whole-card opacity tests in `OpeningFindingCard.test.tsx` and the two whole-card tests in `OpeningStatsCard.test.tsx` with per-row dimming tests (score row vs eval row vs card root), using `getAllByTestId(...)[0]` / `querySelector` for the duplicated mobile+desktop testids.

## Untouched (by design)

Border / left-spine accent (`isReliableScore`, `borderLeftColor`), the on-board arrow, `showScoreZoneFont` / `showEvalZoneFont` font-color gating, the `EvalCpuPlaceholder` branch, and `MIN_GAMES_FOR_RELIABLE_STATS`. The dim style composes with the existing font-color style (different elements, no conflict).

## Deviations from Plan

None - plan executed exactly as written. The plan's conditional ("keep `MIN_GAMES_FOR_RELIABLE_STATS` only if still referenced") resolved to removal in OpeningFindingCard (it was used solely by the removed `isUnreliable` block); it stays in OpeningStatsCard where `isReliableScore` still uses it.

## Verification

- `npm run lint` — clean
- `npm run knip` — clean (confirms no dead export remains after removing `MIN_GAMES_OPENING_ROW`, and no dangling import)
- `npx tsc --noEmit` — clean
- `npm test -- --run` on the three affected files — **3 files, 59 tests passed**
- `grep -rn MIN_GAMES_OPENING_ROW src/` — no remaining references

## Commits

- `7f5ea8a0` feat(quick-260603-pgv): per-row confidence dimming in opening cards
- `8eca530f` feat(quick-260603-pgv): per-row dimming tooltip copy + tests

## Self-Check: PASSED

- Files exist: OpeningFindingCard.tsx, OpeningStatsCard.tsx, OpeningInsightsBlock.tsx, theme.ts, both test files — all modified and committed.
- Commits `7f5ea8a0` and `8eca530f` present in git history.
