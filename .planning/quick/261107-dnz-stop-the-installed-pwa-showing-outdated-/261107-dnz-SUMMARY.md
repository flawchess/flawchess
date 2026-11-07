---
phase: quick-261107-dnz
plan: 01
subsystem: frontend-pwa
tags: [pwa, service-worker, caddy, sentry, cache, build-version]
status: complete
requirements: [QUICK-261107-dnz]
key-files:
  created:
    - frontend/src/lib/updateReload.ts
    - frontend/src/lib/buildVersionCheck.ts
    - frontend/src/lib/staleBuildDiagnostics.ts
    - frontend/src/lib/htmlShellCache.ts
    - frontend/scripts/check-pwa-build.mjs
    - frontend/src/lib/__tests__/updateReload.test.ts
    - frontend/src/lib/__tests__/buildVersionCheck.test.ts
    - frontend/src/lib/__tests__/staleBuildDiagnostics.test.ts
    - frontend/src/lib/__tests__/htmlShellCache.test.ts
  modified:
    - frontend/vite.config.ts
    - frontend/src/main.tsx
    - frontend/src/lib/swUpdate.ts
    - frontend/src/lib/playActive.ts
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/lib/__tests__/swUpdate.test.ts
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/__tests__/instrument.beforeSend.test.ts
    - frontend/package.json
    - .github/workflows/ci.yml
    - deploy/Caddyfile
    - CHANGELOG.md
decisions:
  - "Build ID generated once in vite.config.ts and shared by define (bundle literal) and an emitted version.json"
  - "One reload gate (updateReload.ts) for both build-mismatch and sw-update reloads, 5 min shared cooldown, session hold keyed on the playActive flag plus useHoldUpdateReload on the Train score screen"
  - "html-shell uses a single synthetic key /__html-shell__ with a file-like-path guard; legacy per-URL entries are left in place"
  - "Caddy: no-cache on /version.json, / and *.html, and an unconditional header in the SPA fallback handle"
commits: 5
plan_head_before: 40f03851bf82672f6af59ebb581dddbc1ef67a73
plan_head_after: afa8867b0efb7776cf5487986c95aa2dd393de51
actuals:
  tokens: 18300    # chars/4 over the added diff lines (73,324 chars); not a harness token count
  tasks: 3
  commits: 5
---

# Phase quick-261107-dnz Plan 01: Stop the installed PWA showing outdated builds Summary

A compiled-in build ID is compared with the deployed `/version.json` at startup and on every resume, a mismatch sends one bounded Sentry diagnostic and reloads through one shared gate that holds off during Train sessions and bot games, the service worker `controllerchange` listener now always exists, Caddy sends `no-cache` on all HTML and `version.json`, and the offline `html-shell` cache keeps a single shared entry.

## Tasks and commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (tracer) | An old bundle detects a new deploy, reports it, and reloads once | 27343bbbe |
| 2 | Sessions hold the reload; the service worker takeover goes through the same gate | 63e3eb16b |
| 3 | No-cache HTML/version.json, one-entry offline shell, invariants | b94b7e351 |
| 3 (test hardening) | Cache key plugin test now passes a real request (so M18 fails for the right reason) | 4e2584bae |
| 3 (test hardening) | Held-reload resume test now discriminates from the settle timer (found by M10) | afa8867b0 |

Tracer gate: interactive mode, `human_verify_mode` end-of-phase, `<verify>` automated only. The Task 1 verify command (4 test files, build, `check:pwa-build`) was re-run end to end and passed before continuing.

## Verification results

- Task 1 verify: 75 tests in the 4 files pass; `VITE_SENTRY_DSN= npm run build` then `check:pwa-build` OK (one ID in `dist/version.json` and the entry chunk). Baseline at HEAD: no `dist/version.json` is produced, and the script fails there ("dist/version.json is missing").
- Task 2 verify: 93 tests pass across `updateReload`, `buildVersionCheck`, `swUpdate`, `TrainScoreScreen` tests.
- Task 3 verify: `htmlShellCache.test.ts` (33 cases, original and revived-from-`toString()`), build, `check:pwa-build` (now also asserts `cacheKeyWillBeUsed`, `/__html-shell__`, `cacheName:"html-shell"` in `dist/sw.js`), Caddy fixture all pass.
- Frontend gate, run in the worktree: `npm run lint` clean, `npm run build` OK, `npm run check:pwa-build` OK, `npm test -- --run` 350 files / 5927 tests passed, `npm run knip` exit 0 (2 pre-existing configuration hints, no findings), `tsc -b` clean.
- The full backend pre-merge gate was not run (frontend, Caddy and CI-yaml changes only); the orchestrator owns it.

## Caddy fixture results (`temp/pwa-stale/check_caddy_headers.sh`, caddy:2.11.7)

| Run | Result |
| --- | ------ |
| New `deploy/Caddyfile` | All 23 checks pass: `no-cache` on `/`, `/index.html`, `/train`, `/privacy`, `/privacy/`, `/privacy/index.html`, `/version.json`, `/sw.js`, `/registerSW.js`, `/manifest.webmanifest`, `/push-sw.js`, `/maia/maia-worker.js`; `/assets/app-abc123.js` exactly `public, max-age=31536000, immutable`; `/maia/model.onnx` and `/engine/x.wasm` exactly `public, max-age=2592000`; `/train` with If-Modified-Since is 304 and still carries `no-cache` and COEP; `/train`, `/privacy`, `/privacy/` bodies contain HOME and `/privacy/index.html` contains PRIVACYDOC; `/api/health` has no Cache-Control |
| Pre-fix `git show main:deploy/Caddyfile` (M23) | 8 FAIL: `/`, `/index.html`, `/train`, `/privacy`, `/privacy/`, `/privacy/index.html`, `/version.json` and the 304 `Cache-Control`. Matches the recorded baseline |
| Copy without the `@html` lines (M24) | 2 FAIL: `/index.html`, `/privacy/index.html` |

## Mutation proof

Each mutation was applied to committed code, the named check run, the failing case recorded, then restored with `git checkout -- <file>`. After each, `git status` was verified empty (scripted assertion). The driver is outside the repo.

| ID | Mutation | Failing check (first/representative) |
| -- | -------- | ------------------------------------ |
| M1 | buildVersionCheck: never request a reload on mismatch | buildVersionCheck.test: "reloads on mismatch, with one event sent BEFORE the reload..." (10 failing) |
| M2 | fetch helper returns `''` instead of null on rejection | buildVersionCheck.test: "malformed or failed responses never reload > fetch rejects" (8 failing, incl. "HTML body") |
| M3 | drop status check and field validation | buildVersionCheck.test: "non-200", "empty object", "non-string buildId", "empty buildId" (8 failing) |
| M4 | updateReload: remove the cooldown read | updateReload.test: "cooldown: a request within the window after a reload does nothing, for either reason"; buildVersionCheck.test: "a stamp inside the cooldown stops the reload..." |
| M5 | updateReload: remove the session-active hold | updateReload.test: "a runtime request while a session is active does not reload..." (14 failing) |
| M6 | updateReload: hold regardless of atStartup | updateReload.test: "a startup request while a session is active reloads" |
| M7 | updateReload: remove the session-end subscription | updateReload.test: "held, then the session ends: no reload before SESSION_END_SETTLE_MS, a reload after it" |
| M8 | updateReload: apply synchronously on the flag edge, no settle timer | updateReload.test: "held, then unmount and a new mount in one synchronous step (rematch)..." (8 failing) |
| M9 | updateReload: await beforeReload with no timeout, reload only after success | updateReload.test: "still reloads when beforeReload rejects", "...throws synchronously", "reloads at BEFORE_RELOAD_TIMEOUT_MS when beforeReload never settles" |
| M10 | buildVersionCheck: remove the applyHeldUpdateReload early return | First run PASSED (gap, see Deviations). After the test fix: buildVersionCheck.test "a resume mismatch makes no reload and no event; after the session ends a resume inside the debounce window applies it..." fails |
| M11 | swUpdate: register the listener only when a controller exists at load | swUpdate.test: "no controller and no registration: the first controllerchange (first install) does not reload, a later one does"; "no controller but an active registration..." |
| M12 | swUpdate: remove the first-install exemption | swUpdate.test: "no controller and no registration..." and "getRegistration rejecting is swallowed..." |
| M13 | swUpdate: call reloadAutomatically directly | swUpdate.test: "a controllerchange during a session holds, and applies when the session ends" |
| M14 | staleBuildDiagnostics: remove the collection timeout race | staleBuildDiagnostics.test: "sends a partial event at CACHE_COLLECT_TIMEOUT_MS when caches never settles" |
| M15 | report the full key URL | staleBuildDiagnostics.test: "reports pathnames only: a token in a legacy shell key never appears anywhere in the event" |
| M16 | report entries as objects | staleBuildDiagnostics.test: "reports html_shell_entries as strings (Sentry normalizes contexts to depth 3)" |
| M17 | TrainScoreScreen: remove useHoldUpdateReload | TrainScoreScreen.test: "holds update reloads while rendered and releases them on unmount" |
| M18 | htmlShellCache: return request.url as the key | htmlShellCache.test: "keys the request https://flawchess.com/ ... /?utm_source=pwa ... /train under the one shared entry" (original and revived) |
| M19 | htmlShellCache: remove the file-like path guard | htmlShellCache.test: "does not treat /privacy/index.html", "/google83883b0af640c73c.html", "/og-image.jpg", "/sw.js as an app-shell navigation" |
| M20 | htmlShellCache: key literal moved to a module const | htmlShellCache.test: "revived from toString() > keys the request ..." (ReferenceError; original variant passes) |
| M21 | vite.config: version.json gets a second freshly generated ID | Rebuilt: `check:pwa-build` FAILS: "entry chunk ... does not contain build ID 2f07ba651265" |
| M22 | main.tsx: remove installBuildVersionCheck call (and its now-unused import) | Rebuilt: `check:pwa-build` FAILS: entry chunk does not contain the build ID (literal tree-shaken) |
| M23 | Caddyfile: pre-fix file from main | Fixture: `/`, `/index.html`, `/train`, `/privacy`, `/privacy/`, `/privacy/index.html`, `/version.json`, 304 Cache-Control fail |
| M24 | Caddyfile: copy without the `@html` lines | Fixture: `/index.html`, `/privacy/index.html` fail |

M22 note: removing only the call leaves an unused import, which fails `tsc -b` (noUnusedLocals) before vite runs, so the first attempt measured a stale `dist/`. It was redone with the import removed too, and that run is the one recorded.

## Browser smoke (done, not pending)

Chrome 157 headless was driven over CDP (Node built-in WebSocket) against `VITE_SENTRY_DSN= npm run build` output served by `vite preview --port 4173`. Script: `temp/pwa-stale/smoke.mjs` (gitignored). Result, SMOKE PASSED:

1. Service worker controlled the page after the first load; no update reload fired on the first install (stamp null, build matched).
2. After visiting `/train`, `/library`, `/train`, `caches.open('html-shell').keys()` held exactly one entry, pathname `/__html-shell__`.
3. With `dist/version.json` set to a different buildId and a reload: one automatic reload (2 navigations: the manual reload plus one), `flawchess:update-reload-at` set, then stable for 10 seconds.
4. With the stamp cleared and garbage written to `dist/version.json`: exactly 1 navigation, no stamp, no extra reload.
5. With the preview server stopped, navigating to `/library` rendered the app shell from `html-shell` (10 root children, FlawChess title).

`dist/version.json` was restored by the script. Sentry was off for the smoke build, so no evidence reached the production project. This was a headless run, not the owner's phone: the on-device root cause is still unconfirmed, which is what the new Sentry event is for.

## Deviations from Plan

**1. [Rule 1 - Test gap] Mutation M10 initially passed**
- **Found during:** Task 3 mutation proof
- **Issue:** the buildVersionCheck test for "resume applies a held reload without a new fetch" advanced timers past `SESSION_END_SETTLE_MS`, so the settle timer applied the reload even with the early return removed.
- **Fix:** the test now asserts the reload before `SESSION_END_SETTLE_MS` elapses, so only the resume path can satisfy it. M10 then fails as required.
- **Files modified:** `frontend/src/lib/__tests__/buildVersionCheck.test.ts`
- **Commit:** afa8867b0

**2. [Rule 1 - Test gap] M18 would have failed for the wrong reason**
- **Issue:** the key test called `cacheKeyWillBeUsed()` with no argument, so a request-derived key would crash on destructuring rather than return a wrong value.
- **Fix:** the test calls it with a Workbox-shaped `{ mode, request: { url } }` for `/`, `/?utm_source=pwa` and `/train`.
- **Files modified:** `frontend/src/lib/__tests__/htmlShellCache.test.ts`
- **Commit:** 4e2584bae

**3. [Rule 3 - Blocking] Explicit `.ts` extension on the vite.config import**
- `import ... from './src/lib/htmlShellCache'` made Vite warn that the config uses features unsupported by `configLoader: 'native'`. Added the `.ts` extension (allowed by tsconfig.node `allowImportingTsExtensions`). Part of the Task 3 commit.

**4. Scope placement:** the `check:pwa-build` html-shell assertions were added in Task 3 as planned; Task 1's version of the script checks only version.json, the entry chunk and the precache list, so the Task 1 verify command could pass before the html-shell plugin existed.

Otherwise the plan was executed as written.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. Mitigations present and test-covered: T-261107-01 (M2, M3), T-261107-02 (M4, fail-closed storage test), T-261107-03 (M15, pathname-only keys), T-261107-05 (M19).

## Notes for the orchestrator

- Nothing was pushed, merged or deployed. All five commits are on `quick/pwa-stale-build` in the worktree.
- `temp/pwa-stale/` (check_caddy_headers.sh, smoke.mjs, fixture, mutated Caddyfiles) is gitignored and lives in the worktree only.
- Docs artifacts (this SUMMARY, STATE.md, PLAN.md) are uncommitted by instruction; ROADMAP.md was not touched.
- After deploy, the Caddy change is only live once Caddy reloads the new Caddyfile (bin/deploy.sh path); `/version.json` does not exist in prod until the first deploy of this build, so the first clients to receive the new bundle see a 404 from the check and stay put (no reload), by design.
- Reload-time diagnostics appear in Sentry as the info-level message "Stale frontend build detected by version check" with context `stale_build`; expect one per client per deploy they were open across.

## Self-Check: PASSED

- Created files exist: updateReload.ts, buildVersionCheck.ts, staleBuildDiagnostics.ts, htmlShellCache.ts, check-pwa-build.mjs and the four new test files (all listed in the 21-file diff stat).
- Commits exist on the branch: 27343bbbe, 63e3eb16b, b94b7e351, 4e2584bae, afa8867b0 (`git rev-list --count 40f03851b..HEAD` = 5).
- Tracked tree clean after the mutation runs (`git status --short` empty).
