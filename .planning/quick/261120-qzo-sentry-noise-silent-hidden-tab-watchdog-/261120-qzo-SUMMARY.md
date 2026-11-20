---
quick_id: 261120-qzo
status: complete
completed: 2026-11-20
commit: e53159834
branch: main (direct commit, executed inline)
files_modified:
  - frontend/src/lib/engine/workerPoolWatchdog.ts
  - frontend/src/lib/engine/__tests__/workerPool.test.ts
  - frontend/src/instrument.ts
  - frontend/src/__tests__/instrument.beforeSend.test.ts
---

# Quick 261120-qzo summary: two Sentry noise fixes in the frontend

## What changed

- `workerPoolWatchdog.ts` (FLAWCHESS-9G, fourth pass): `fireWatchdog` no longer calls
  `Sentry.captureException` when the tab is still hidden at the kill path. That path is only
  reachable while hidden once `MAX_WATCHDOG_HIDDEN_REARMS` (10) is spent, i.e. a tab left in the
  background for over ten minutes. The slot is still stopped, marked dead and replaced.
- `workerPool.test.ts`: the bounded-re-arm test now asserts the kill happens with no capture
  (it asserted exactly one capture before, so it fails with the fix reverted). New test: a tab
  that turns visible after spending the hidden budget still reports, with `hiddenRearms: 10` and
  `visibilityState: "visible"` in context.
- `instrument.ts` (FLAWCHESS-DH): `/Invalid call to runtime\.sendMessage\(\)/` added to
  `ignoreErrors`, with a test against the production message.

## Evidence

Two of the three FLAWCHESS-9G events in the last 90 days (2026-11-18 and 2026-11-19, the same
Firefox/Mac session shape) carried `hiddenRearms: 10`, `visibilityState: "hidden"`. The third
(2026-11-05, Android, visible, depth 10, last `info` 0.4 s after arming, then 85 s of silence)
is a different shape and still reports after this change.

## Verification

- `npm test -- --run src/lib/engine/__tests__/workerPool.test.ts src/__tests__/instrument.beforeSend.test.ts`: 173 passed.
- `npm run lint`: clean. `npm run build`: succeeded.
- Full pre-merge gate not run (small direct `main` commit, frontend only).

## Not done

- No CHANGELOG entry: not user-facing.
- Sentry: FLAWCHESS-9G left unresolved until this is deployed; FLAWCHESS-DH is already archived.
