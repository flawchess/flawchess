---
quick_id: 261004-rmc
status: complete
commit: d0a515bbf
---

# Quick 261004-rmc Summary: Suppress Umami pageview after automatic reloads

## What changed

- `frontend/src/lib/autoReload.ts` (new): `reloadAutomatically()` writes a
  sessionStorage marker then reloads; `consumeAutoReloadMarker()` reads and clears it.
- `main.tsx` SW `controllerchange` reload and `stalePreloadReload.ts` recovery
  reload now use `reloadAutomatically()`. User-initiated reloads (App.tsx error
  button, Analysis.tsx) untouched.
- `analytics.ts`: `installUmamiBeforeSend()` consumes the marker at boot and
  installs `umamiBeforeSend`, which returns `null` (cancels, per the tracker's
  `if(e)` check in script.js) for that page load's first pageview and otherwise
  delegates to `scrubUmamiPayload`. Identify and custom events always pass.
- Consuming at boot (not at send time) means a marker left behind by a blocked
  tracker can never swallow a later real pageview.

## Verification

- New/updated tests: autoReload (5), analytics (3 new), stalePreloadReload (1 new).
- Mutation check: disabling the drop made the 2 drop tests fail; restored.
- `npm run lint`, `npm run build`, `npm run knip`, full `npm test` (305 files, 5020 tests) green.

## Follow-up

- Effect is visible in Umami only after the next prod deploy, and only for tabs
  loaded on the new build (old tabs reload once more via the old code path).
