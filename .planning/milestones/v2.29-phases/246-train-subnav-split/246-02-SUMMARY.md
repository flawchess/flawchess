---
phase: 246-train-subnav-split
plan: 02
subsystem: ui
tags: [react, react-router, radix-tabs, tanstack-query, vitest]

requires:
  - phase: 246-train-subnav-split
    provides: CONTEXT decisions D-01, D-03, D-06, D-15, D-16
provides:
  - "parseTrainRoute / TRAIN_TAB_PATHS / TrainTab / TrainRoute (frontend/src/lib/trainRoute.ts)"
  - "useTrainLoop hook: session, grading engine, loop flags, one-way todayVisited latch, immersive derivation, requestSessionReread"
  - "resolveTrainImmersive pure function"
  - "TrainSubnav nav-only responsive TabsList (train-tabs, tab-train-today, tab-train-leaderboard)"
  - "pages/Train.tsx as a layout: route parse, redirect, subnav, plain-div panels (train-today-panel, train-leaderboard-panel)"
affects: [246-03, 246-05, 246-06, 246-08]

actuals:
  tokens: 15200
  tasks: 2
  commits: 2
plan_head_before: 0c84cf49c8fb0fd6cfa04cc7fdb30c6f3882fa43
plan_head_after: 5e1a72e4f098c5e5832162ba83f929da38f4b6aa

tech-stack:
  added: []
  patterns:
    - "State-based one-way latch set during render (not a ref) so an effect sees it on the first pass and the StrictMode double-invoke recovery still works"
    - "Layout keeps a hidden-but-mounted panel; deferred side effects go through a stable flag-setting callback"
    - "Render-phase flag clearing when a view is left, with the re-read deferred to an effect gated on the owning tab"

key-files:
  created:
    - frontend/src/lib/trainRoute.ts
    - frontend/src/lib/__tests__/trainRoute.test.ts
    - frontend/src/hooks/useTrainLoop.ts
    - frontend/src/hooks/__tests__/useTrainLoop.test.ts
    - frontend/src/components/train/TrainSubnav.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx
  modified:
    - frontend/src/pages/Train.tsx

key-decisions:
  - "Layout-level latch (todayVisited) rather than moving the hooks to a Today route"
  - "One responsive TabsList and plain-div panels, no TabsContent"
  - "requestSessionReread (stable, flag-only) replaces passing startSession as onSettingsSaved"

patterns-established:
  - "Page-level Train tests drive Radix tabs with fireEvent.mouseDown and simulate Back via a captured navigate(-1)"

requirements-completed: [D-01, D-03, D-06, D-15, D-16]

status: complete
---

# Phase 246 Plan 02: Train tabs, latched session and engine Summary

**/train is now a layout with URL-routed Today and Leaderboard tabs; a Leaderboard-only visit creates no session and constructs no Worker, via a one-way `todayVisited` latch in a new `useTrainLoop` hook.**

## Accomplishments

- `parseTrainRoute` matches exact `/train` and `/train/leaderboard` (trailing slashes stripped); anything else redirects to `/train`.
- `useTrainLoop` owns everything `TrainPage` used to hold, with its comments (including the StrictMode no-ref-latch warning). The session read and the engine (`enabled: canTrain && todayVisited`) wait for Today's first visit.
- `TrainSubnav` is one responsive brand `TabsList`; panels are plain divs. The Leaderboard tab renders the existing `TrainLeaderboardCard` in a centered `max-w-2xl` column. Today stays mounted but hidden on the other tab so a 600 ms debounced settings save is not lost and the return shows no skeleton.
- Immersive states (loop, score screen, cached reveal from the first paint) hide `train-tabs` and swap the wrapper class on the same element.
- Back out of a running loop clears the loop flags during render and re-reads the session exactly once when Today is active again.

## Task Commits

1. Task 1 (tracer): `d2a0a9951` feat(246-02): URL-routed Train tabs with a latched session and engine
2. Task 2 (tdd): `5e1a72e4f` feat(246-02): immersive first paint, Back out of the loop, deferred session re-read

Task 2's tests were written first and run RED (14 failures: missing exports, first-paint tabs, Back-out, deferred re-read) before the implementation.

## Mutation checks (each reverted before commit)

| Mutation | Failing tests |
|----------|---------------|
| Task 1: latch initial `useState(true)` instead of `useState(isToday)` | "a /train/leaderboard deep link ... no session POST and no Worker" (first failing assertion: compose called 1 time, expected 0; the Worker and `train-start-screen` assertions come after it in the same test) |
| Task 2: drop `input.session === null \|\|` from `resolveTrainImmersive` | truth-table case "a cached reveal with no session yet is immersive (first paint)"; page tests "shows no tabs on the first paint of a cached reveal ...", "shows the tabs and clears the cache when the cached reveal belongs to another session", "restored reveal, then Leaderboard ..." |
| Task 2: `if (!isToday) return null` in `TrainSessionViews` replaced with `if (false)` | "restored reveal, then Leaderboard: the solve screen is gone and the card shows" |
| Task 2: render-phase flag clearing for `!isToday` disabled | "Back out of a running loop removes the solve screen with no POST, and the return re-reads once" |

## Verification

- `npm test` (full frontend): 349 files, 5870 tests pass, including `Train.solveLoop.test.tsx` unchanged (it renders at `/` and is carried to `/train` by the redirect).
- `npm run lint`, `npm run build`, `npm run knip`: clean (knip prints two pre-existing configuration hints).
- Not done here, per the plan: the real-browser checks for tab geometry and Back live in plan 246-06; the medal and hidden-landing checks live in plan 246-08.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate history push from one tab click**
- **Found during:** Task 2 (Back-out test: `navigate(-1)` from Today landed on `/train` instead of `/train/leaderboard`)
- **Issue:** Radix calls `onValueChange` on mousedown and again from the trigger's focus handler, before the router re-renders `active`. `TrainSubnav` therefore pushed the same path twice, so Back needed two presses. Library's tabs have the same shape; this plan leaves them alone.
- **Fix:** `TrainSubnav` tracks the last requested tab in a ref (re-synced in an effect when `active` changes) and ignores a repeated value. A `value === active` guard was tried first and did not work, because `active` is stale at that moment.
- **Files modified:** frontend/src/components/train/TrainSubnav.tsx
- **Commit:** 5e1a72e4f
- **Note:** I reproduced it under jsdom only. Whether a real browser double-fires depends on render timing, so plan 246-06's browser check should confirm one Back press returns to the previous tab.

### Test-shape adjustments

- The Pitfall 2 test (no empty-state flash on the first Today click) cannot see the first commit through `fireEvent`, because `act` flushes the mount effect before the test looks. It watches DOM mutations with a `MutationObserver` and asserts `train-session-loading` was painted and `train-start-screen` was not.
- The deep-link test asserts the POST and Worker counts before the `train-start-screen` absence so the latch mutation fails on the counts the plan names.
- Held-open compose promises are created eagerly: TanStack calls `mutationFn` asynchronously, so resolving a lazily captured resolver after `render` resolved a no-op.

## Known Stubs

None.

## Threat Flags

None. The pathname is only matched against exact strings (T-246-10), the latch and `requestSessionReread` keep every POST on Today (T-246-09), and one Worker exists per page visit (T-246-08).

## Issues Encountered

None beyond the deviation above.

## Self-Check: PASSED

- FOUND: frontend/src/lib/trainRoute.ts, frontend/src/lib/__tests__/trainRoute.test.ts, frontend/src/hooks/useTrainLoop.ts, frontend/src/hooks/__tests__/useTrainLoop.test.ts, frontend/src/components/train/TrainSubnav.tsx, frontend/src/pages/Train.tsx, frontend/src/pages/__tests__/Train.subnav.test.tsx
- FOUND commits: d2a0a9951, 5e1a72e4f
