---
quick_id: 260926-agm
mode: quick
---

# Quick 260926-agm: Fix Sentry noise (stale-chunk reload, aborted-XHR filter, per-attempt 429 captures)

Source: triage of unresolved production Sentry issues on 2026-09-26.

## Tasks
1. **FLAWCHESS-C0**: handle Vite's `vite:preloadError` in `main.tsx` (extracted to `lib/stalePreloadReload.ts`): reload once, with a sessionStorage cooldown so a reload that does not help reports instead of looping. Unit tests.
2. **FLAWCHESS-31**: `instrument.ts` drops axios `ECONNABORTED` + message `"Request aborted"` (browser-initiated abort; `apiClient` sets no timeout). A timeout message still reports. Fix the misleading comment. Tests.
3. **FLAWCHESS-BX**: remove the per-attempt `capture_message` on 429 in `lichess_client.py` and `chesscom_client.py`; retries only log, exhaustion still raises and `run_import()` captures once. Tests that a recovered 429 never reaches Sentry.

## Verify
Targeted tests, mutation check per fix, full frontend + backend suites, lint/ty/knip/build, Chrome UAT of the stale-chunk reload on a production build.
