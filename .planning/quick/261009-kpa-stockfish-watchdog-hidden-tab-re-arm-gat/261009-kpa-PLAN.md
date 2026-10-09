---
quick_id: 261009-kpa
mode: quick
source: .planning/seeds/SEED-180-stockfish-watchdog-hidden-tab-gate.md
---

# Quick 261009-kpa: Stockfish grading watchdog hidden-tab re-arm gate (SEED-180, FLAWCHESS-9G third pass)

Trigger check (seed asked to re-read context before applying): the newest
FLAWCHESS-9G event (2026-10-03 18:34 UTC, Safari 26.4 / Mac, a different
session from the 2026-09-28 one) has the same shape: `elapsedMs` 60154 (on
time), `sinceLastInfoMs` 28600 (silent), grades 11/11, `visibilityState:
"hidden"`. Gate applies as planned.

## Task 1: hidden-tab gate in `fireWatchdog`

files: frontend/src/lib/engine/workerPoolWatchdog.ts, frontend/src/lib/engine/workerPoolState.ts,
frontend/src/lib/engine/workerPoolDispatch.ts, frontend/src/lib/engine/workerPoolLifecycle.ts,
frontend/src/lib/engine/workerPool.ts

- New `MAX_WATCHDOG_HIDDEN_REARMS` constant in `workerPoolState.ts` (re-exported via the
  `workerPool.ts` facade like its siblings).
- New `watchdogHiddenRearms` slot field; initialised in `workerPoolLifecycle.ts`, reset per
  dispatch in `sendGo` (`workerPoolDispatch.ts`) next to the other two counters.
- Third re-arm gate in `fireWatchdog`, after the liveness gate and before the kill path:
  `document.visibilityState === 'hidden'` and budget left -> increment and re-arm.
- `hiddenRearms` added to the `stockfishWatchdog` Sentry context.
- Out of scope: `fireStopWatchdog` / `armStopWatchdog`, `GRADING_WATCHDOG_TIMEOUT_MS`.

## Task 2: unit tests (`frontend/src/lib/engine/__tests__/workerPool.test.ts`)

- Hidden + silent + on-time fire re-arms (no stop, no capture), and a later bestmove delivers the grade.
- Bound: after `MAX_WATCHDOG_HIDDEN_REARMS` hidden fires the next one kills, with `hiddenRearms` in the context.
- Visible silent on-time fire still kills at the first fire (existing tests cover it; keep visibility reset in the describe hooks).

verify: `cd frontend && npx vitest run src/lib/engine/__tests__/workerPool.test.ts`, `npm run lint`, `npm run build`, `npm run knip`
