---
quick_id: 260616-rm6
title: Fix the Quick Scan and platform-count counter lag
date: 2026-06-16
status: complete
---

# Quick Task 260616-rm6 — Summary

## What changed

Frontend-only fix in `frontend/src/pages/Import.tsx` so the import-page counters
move together during an active import instead of the slower ones reading as
"stuck".

1. **Per-platform "N games" header now driven by the live import job.**
   `ImportProgressBar` gained an `onProgress(platform, gamesImported)` callback,
   fired from a `useEffect` while the job is active. `ImportPage` collects these
   into a `liveImported` record (max-seen per platform) and displays
   `Math.max(profile.<platform>_game_count, liveImported[platform] ?? 0)`. During
   a first import the header now climbs at the 2s import-poll cadence in lockstep
   with "saved"; for incremental syncs the full library COUNT still dominates the
   small new-games delta, so `Math.max` never shows a number below the true count.

2. **Quick Scan rescue cadence tightened.** `GAME_COUNT_REFRESH_INTERVAL_MS`
   lowered 5000 → 3000 so the `['imports','eval-coverage']` invalidation (the
   backstop that resumes the eval-coverage self-poll after it stops at a momentary
   `pct_complete === 100`) fires at the same 3s cadence as the self-poll, halving
   the worst-case Quick Scan stall window.

## Why (corrected diagnosis)

The original stress-test hypothesis ("queries snapshotted at page load, never
invalidated") was wrong — `Import.tsx` already invalidates `userProfile` /
`gameCount` / `eval-coverage` every 5s, and `main`/`production` are byte-identical
for these files. The real cause was three indicators on three cadences (2s import
poll, 5s profile COUNT, 3s eval-coverage self-poll) from three sources: the header
count is a backend `COUNT(*)` that legitimately trails the job's optimistic
`games_imported`, and the eval self-poll can briefly stop when helper workers
drive `pct_complete` to 100. Driving the header from the live job and tightening
the eval rescue interval makes everything move with "saved".

User-chosen scope: frontend-only ("Drive header from live job"). Backend
`COUNT(*)` visibility/latency was explicitly left out of scope.

## Verification

- `npm run lint` — clean
- `npx tsc --noEmit` — clean
- `npm run knip` — clean
- `npm test -- --run` — 84 files / 951 tests pass (incl. `Import.stateMachine`,
  `Import.endgameOverviewInvalidation`, `EvalCoverageHeader`)

Behavioral check: existing `Import.stateMachine` test renders with
`activeJobIds={[]}` and still sees `profile.chess_com_game_count` (100) — the
header falls back to the profile count when no live job is reporting.

## Files

- `frontend/src/pages/Import.tsx` (header count source + refresh interval)

## Follow-ups (not done, out of scope)

- Backend: investigate why `count_games_by_platform` (`COUNT(*)`) trails the
  import job's `games_imported` by ~75s under heavy import load (commit
  visibility / count cost under checkpoint I/O).
