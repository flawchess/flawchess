---
quick_id: 261009-kpa
status: complete
date: 2026-10-09
commit: 036b01d72
seed: SEED-180
sentry: FLAWCHESS-9G
---

# Quick 261009-kpa summary: Stockfish watchdog hidden-tab re-arm gate

## Trigger check

SEED-180 asked to re-read the Sentry context before applying the gate. The newest
FLAWCHESS-9G event (2026-10-03 18:34 UTC, Safari 26.4 / Mac, a different session from
the 2026-09-28 Chrome one) has the same shape: on time (60154ms), silent (28.6s),
11/11 grades accumulated, `visibilityState: "hidden"`. No visible-tab fire exists, so
the gate was applied as planned.

## What changed

- `workerPoolState.ts`: `MAX_WATCHDOG_HIDDEN_REARMS = 10` (re-exported via `workerPool.ts`),
  `watchdogHiddenRearms` slot field; worst-case abandonment doc updated.
- `workerPoolWatchdog.ts`: third re-arm gate in `fireWatchdog` after the liveness gate,
  before the kill path (`document.visibilityState === 'hidden'` and budget left);
  `hiddenRearms` added to the `stockfishWatchdog` Sentry context.
- `workerPoolDispatch.ts` / `workerPoolLifecycle.ts`: counter reset per `sendGo` and initialised per slot.
- `fireStopWatchdog`/`armStopWatchdog` and `GRADING_WATCHDOG_TIMEOUT_MS` untouched (out of scope).

Cap is 10 rather than 3 (the other two gates): re-arming in a hidden tab is close to free,
since nobody is watching the stalled search and the first visible fire skips the gate.

## Verification

- 3 new tests in `workerPool.test.ts`: hidden re-arm then real grade; bound reaches the kill
  path with `hiddenRearms: 10` in context; gate stops applying once visible. Context test now
  asserts `hiddenRearms: 0`.
- Mutation check: with the gate disabled (`false &&`), all 3 new tests fail; restored, 126/126 pass.
- Frontend gate: `npm run lint`, `npm run build`, `npm run knip`, `npm test -- --run` (5443 tests) all green.

## Follow-up

Watch FLAWCHESS-9G after the next release. A fire with `visibilityState: "visible"`, or a hidden
fire with `hiddenRearms: 10`, is a different shape and needs a fresh look.
