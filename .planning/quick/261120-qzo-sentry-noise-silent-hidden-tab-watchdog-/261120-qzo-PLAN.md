---
quick_id: 261120-qzo
mode: quick
---

# Quick 261120-qzo: two Sentry noise fixes in the frontend

Source: Sentry triage on 2026-11-20.

## Task 1: silent hidden-tab watchdog kill (FLAWCHESS-9G)

- files: `frontend/src/lib/engine/workerPoolWatchdog.ts`, `frontend/src/lib/engine/__tests__/workerPool.test.ts`
- action: in `fireWatchdog`, skip `Sentry.captureException` when `document.visibilityState` is
  `hidden` at the kill path (only reachable there with `MAX_WATCHDOG_HIDDEN_REARMS` spent).
  Keep the kill and `replaceDeadSlot`. A visible fire still reports.
- verify: `npm test -- --run src/lib/engine/__tests__/workerPool.test.ts` (from `frontend/`)

## Task 2: ignore extension `runtime.sendMessage` rejections (FLAWCHESS-DH)

- files: `frontend/src/instrument.ts`, `frontend/src/__tests__/instrument.beforeSend.test.ts`
- action: add `/Invalid call to runtime\.sendMessage\(\)/` to `ignoreErrors`.
- verify: `npm test -- --run src/__tests__/instrument.beforeSend.test.ts`, then `npm run lint`
  and `npm run build`.
