---
phase: 241-codebase-cleanup
plan: 58
subsystem: frontend
tags: [naming, refactor, bots]
requires: [241-02, 241-03, 241-04, 241-28, 241-34, 241-39, 241-40, 241-48, 241-49, 241-50]
provides:
  - BotWelcomeBubble, useResultDialogHold, botDrawOfferPending naming
affects: [frontend bot-play code]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-58.tsv
  modified:
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/hooks/useResultDialogHold.ts
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/useBotGameDrawOffer.ts
    - frontend/src/pages/Bots.tsx
decisions:
  - "botDrawOffer is not a persisted snapshot key; renamed (T-241-80 check passed)"
metrics:
  completed: 2026-10-16
status: complete
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: b434e0838a662db04602143eda6202e9e9c6e894
---

# Phase 241 Plan 58: Bot-play renames Summary

Three bot-play renames from INVENTORY §5 applied with no behavior change, one `refactor(naming)` commit each.

## Renames

| Old | New | Commit | Files |
|-----|-----|--------|-------|
| `BotWelcomeCard` | `BotWelcomeBubble` | 50958e8c0 | PersonaGrid.tsx, botGameCopy.ts, botGameCopy.test.ts |
| `useWinCelebrationHold` (file + hook + test file + vi.mock path/factory key), Bots.tsx `celebrationHold` → `resultDialogHeld` | `useResultDialogHold` | 290505636 | hooks/useResultDialogHold.ts (+ test), useBotGameSnapshot.ts, useBotGameVoice.ts, botGameCopy.ts, confetti.ts, Bots.tsx, Bots.test.tsx |
| `botDrawOffer` / `botDrawOfferRef` / `setBotDrawOffer` | `botDrawOfferPending` / `botDrawOfferPendingRef` / `setBotDrawOfferPending` | b434e0838 | useBotGame.ts, useBotGameDrawOffer.ts, useBotGameMoves.ts, useBotGameVoice.ts, Bots.tsx, BotDrawOfferActions.tsx, useBotGame.test.ts, useBotGameVoice.test.ts, Bots.test.tsx |

## Snapshot check

`git grep botDrawOffer` over `useBotGameSnapshot.ts` and `lib/botGameSnapshot.ts` returned nothing: `botDrawOffer` is not a persisted snapshot key. Testid `bots-intro`, snapshot keys and Umami names untouched. No collision with the sibling `drawOfferPending`.

## Verification

Baseline gates clean before starting. After each task: `npm run build` (tsc), `npm run lint`, targeted vitest, `cleanup.py absent` (7 rows, 0 hits) and `cleanup.py diff` all passed; knip (task 2) clean apart from two pre-existing config hints; `source_scan_tests.sh` passed (131 tests).

## Deviations from Plan

None. The plan was executed as written. The rename map was created fresh (the `rename-maps/` directory did not exist in this worktree).

## Known Stubs

None.

## Self-Check: PASSED

Commits 50958e8c0, 290505636, b434e0838 exist on the worktree branch; useResultDialogHold.ts and rename-maps/241-58.tsv present.
