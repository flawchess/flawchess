---
quick_id: 260926-agm
status: complete
commit: 038a4280c
---

# Quick 260926-agm Summary: Fix Sentry noise

Executed inline (small change, no subagents).

## Done
- `decdb53a1` FLAWCHESS-31: `isBrowserAbortedRequest()` in `instrument.ts` drops `ECONNABORTED`/"Request aborted" (axios 1.20 raises it from XHR `onabort`, i.e. browser cancellation); timeouts ("timeout of Nms exceeded") still ship with the `api-timeout` fingerprint.
- `5bb9da010` FLAWCHESS-C0: `lib/stalePreloadReload.ts` + `installStalePreloadReload()` in `main.tsx`. One reload per 60s cooldown (`PRELOAD_RELOAD_COOLDOWN_MS`); no reload when sessionStorage is unavailable.
- `256b2170c` FLAWCHESS-BX: per-attempt 429 `capture_message` removed from both import clients.
- `038a4280c` refactor: the new branch pushed `sentryBeforeSend` to complexity 20 (baseline 19); drop conditions moved into `isDroppableAxiosError()`, and `instrument.ts` left the eslint complexity baseline.
- CHANGELOG `[Unreleased] → Fixed` bullet for the stale-tab reload.

## Verification
- Mutation checks: each new test fails with its fix reverted (beforeSend abort test, cooldown test, lichess + chess.com 429 tests).
- Full suites: frontend 4378 passed; backend 4750 passed / 19 skipped (`-n auto`). ruff, ty, eslint, knip, `npm run build` clean.
- Chrome UAT on a production build (`vite preview` with a temporary /api proxy config, removed afterwards): loaded build A as a guest, rebuilt so the Bots chunk hash changed, clicked Bots in the old tab → exactly one reload, build B's Bots chunk loaded, page rendered, no error screen. Within the cooldown a second `vite:preloadError` was left alone (no reload). A real browser-aborted axios request was dropped by `sentryBeforeSend` while a real 404 still reported. Dev route sweep (Train, Bots, Analysis, Library) had no console errors.

## Notes
- After deploy, resolve FLAWCHESS-C0, -31 and -BX in Sentry.
