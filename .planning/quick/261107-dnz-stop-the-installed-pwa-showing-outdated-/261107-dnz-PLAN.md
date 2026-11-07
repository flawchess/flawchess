---
phase: quick-261107-dnz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/vite.config.ts
  - frontend/src/main.tsx
  - frontend/src/lib/updateReload.ts
  - frontend/src/lib/buildVersionCheck.ts
  - frontend/src/lib/staleBuildDiagnostics.ts
  - frontend/src/lib/htmlShellCache.ts
  - frontend/src/lib/swUpdate.ts
  - frontend/src/lib/playActive.ts
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/lib/__tests__/updateReload.test.ts
  - frontend/src/lib/__tests__/buildVersionCheck.test.ts
  - frontend/src/lib/__tests__/staleBuildDiagnostics.test.ts
  - frontend/src/lib/__tests__/htmlShellCache.test.ts
  - frontend/src/lib/__tests__/swUpdate.test.ts
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/__tests__/instrument.beforeSend.test.ts
  - frontend/scripts/check-pwa-build.mjs
  - frontend/package.json
  - .github/workflows/ci.yml
  - deploy/Caddyfile
  - CHANGELOG.md
autonomous: true
requirements:
  - QUICK-261107-dnz

estimate:
  tokens: 100000
  raw_tokens: 100000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "An old bundle still running after a deploy reloads itself on its next startup or resume, at most once per cooldown window"
    - "A failed fetch, a non-200, non-JSON or missing-field /version.json response never reloads; the checker is inert in dev and in tests"
    - "Each mismatch reload is preceded by one Sentry event with a fixed message and the diagnostics; collection or flush failure or slowness cannot hold the reload past BEFORE_RELOAD_TIMEOUT_MS"
    - "During a Train session (solve screen or score screen) or a bot game, a resume mismatch or a service worker takeover holds the reload; it applies when the session ends or at the next resume; a startup mismatch always applies"
    - "The first service worker install never reloads; every later takeover reloads, including on a page that had no controller at load"
    - "Caddy sends Cache-Control no-cache on all HTML (/, /index.html, SPA fallback routes, prerendered pages) and /version.json; /assets/* stays immutable"
    - "html-shell serves one shared entry, the latest successful app-shell load, so the offline fallback can never be a weeks-old per-URL copy"
  artifacts:
    - path: "frontend/src/lib/updateReload.ts"
      provides: "Shared reload gate: cooldown, in-flight dedupe, session hold, bounded beforeReload"
      exports: ["requestUpdateReload", "applyHeldUpdateReload", "isUpdateSessionActive", "useHoldUpdateReload"]
    - path: "frontend/src/lib/buildVersionCheck.ts"
      provides: "Startup and resume check of /version.json against the compiled build ID"
      exports: ["installBuildVersionCheck", "createBuildVersionChecker", "parseDeployedBuildId"]
    - path: "frontend/src/lib/staleBuildDiagnostics.ts"
      provides: "One bounded Sentry event before a mismatch reload"
      exports: ["reportStaleBuild", "STALE_BUILD_SENTRY_MESSAGE"]
    - path: "frontend/src/lib/htmlShellCache.ts"
      provides: "Self-contained, serialization-safe route matcher and cache key plugin for html-shell"
      exports: ["HTML_SHELL_CACHE_NAME", "HTML_SHELL_CACHE_KEY", "isHtmlShellNavigation", "htmlShellCacheKeyPlugin"]
    - path: "frontend/scripts/check-pwa-build.mjs"
      provides: "Real-build invariants: version.json ID equals the entry chunk literal, sw.js precache and html-shell shape"
    - path: "deploy/Caddyfile"
      provides: "no-cache on all HTML and /version.json"
      contains: "/version.json"
  key_links:
    - from: "frontend/src/lib/swUpdate.ts"
      to: "frontend/src/lib/updateReload.ts"
      via: "controllerchange goes through the gate, never directly to reloadAutomatically"
      pattern: "requestUpdateReload"
    - from: "frontend/src/lib/buildVersionCheck.ts"
      to: "frontend/src/lib/updateReload.ts"
      via: "mismatch goes through the gate; resume applies a held reload before the debounce"
      pattern: "applyHeldUpdateReload"
    - from: "frontend/src/lib/updateReload.ts"
      to: "frontend/src/lib/playActive.ts"
      via: "session-active read and session-end subscription"
      pattern: "isPlayActive"
    - from: "frontend/vite.config.ts"
      to: "frontend/src/lib/htmlShellCache.ts"
      via: "runtimeCaching urlPattern, cacheName and plugins"
      pattern: "htmlShellCacheKeyPlugin"
    - from: "frontend/src/main.tsx"
      to: "frontend/src/lib/buildVersionCheck.ts"
      via: "installBuildVersionCheck at startup, outside the serviceWorker branch"
      pattern: "installBuildVersionCheck"
---

<objective>
Stop the installed PWA showing outdated builds, without needing to know which cache caused it on the owner's phone (root cause on the device is unconfirmed, there is no cable to inspect it).

Purpose: the owner's installed PWA intermittently showed a weeks-old build until a manual reload. Nothing today repairs that: the only auto-reload triggers are controllerchange (listener registered only when a controller exists at load) and vite:preloadError, and /assets/* is immutable for a year, so an old shell's JS keeps loading without any error.

Output: a build-ID check that reloads on mismatch and reports why, one shared reload gate that protects active sessions, a controllerchange listener that always exists, no-cache on all HTML, and a one-entry offline shell.

No user-visible UI is added, so no trackFeature event or data-testid is needed. Reloads go through reloadAutomatically, so Umami already drops their pageview. Frontend has no Prettier: do not run it.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@frontend/vite.config.ts
@frontend/src/main.tsx
@frontend/src/instrument.ts
@frontend/src/lib/swUpdate.ts
@frontend/src/lib/stalePreloadReload.ts
@frontend/src/lib/autoReload.ts
@frontend/src/lib/playActive.ts
@frontend/src/lib/__tests__/swUpdate.test.ts
@frontend/src/lib/__tests__/stalePreloadReload.test.ts
@frontend/src/__tests__/instrument.beforeSend.test.ts
@deploy/Caddyfile
@frontend/Dockerfile
</context>

<design_decisions>
All of these were checked by the planner on 2026-11-07 against live prod, a local caddy:2.11.7 run and a trial build with a temporary config. Build on them; do not re-derive them.

**DD-1 Build ID.** Generated once at vite.config.ts module evaluation: compact UTC timestamp plus random hex (shape: 20261107T095912Z-a1b2c3). Git cannot supply it: `.dockerignore` lists `.git`, node:24-alpine ships no git, and docker-compose passes no commit build arg. It reaches the bundle through `define` key `import.meta.env.VITE_BUILD_ID` (trial build proved the literal lands in the entry chunk) and reaches `version.json` through a `generateBundle` `emitFile` from the same const. The timestamp also gives the running build's age in Sentry. Use the exact dotted expression in source: destructuring or aliasing `import.meta.env` defeats the replacement.

**DD-2 One gate for every update reload (frontend/src/lib/updateReload.ts).** Both the version mismatch and controllerchange go through it, because after a deploy the resume-time reg.update() installs the new service worker, whose skipWaiting and clientsClaim fire controllerchange. Deferring only the version reload would change nothing. The stale-chunk preload reload stays outside: it fires only when a navigation has already failed.

**DD-3 Session seam: the existing playActive flag, not a route check.** `useMarkPlayActive` is already set by `BotsGame` (live game, resume gate, result surface) and `TrainSolveScreen` (puzzle and reveal). A route check would be wrong: `/train` serves the idle landing as well as the solve loop (Train.tsx `hasEnteredLoop`), and `/bots` serves the roster as well as the game. One real gap: pressing Next on the final reveal unmounts TrainSolveScreen for TrainScoreScreen, whose state is local to Train.tsx, so a reload at that edge would destroy the score screen. `useMarkPlayActive` cannot cover it (ProtectedLayout hides the mobile header on that flag), hence a one-line `useHoldUpdateReload()` in TrainScoreScreen. Rematch and restored-reveal transitions flip the flag false then true inside one commit, hence a settle delay before applying at session end. Leaving a session for Analyze via the deep link reloads on the analysis page, which is safe: the reveal cache is in sessionStorage.

**DD-4 Shared cooldown.** Five minutes, one sessionStorage key across both reasons. It also suppresses the redundant second reload when a version reload is followed moments later by the new worker's controllerchange. Anything suppressed self-heals at the next resume check after the window. A startup check that is still mismatched right after a reload does nothing inside the window, which is the loop guard. On storage failure a mismatch reload fails closed (no loop guard, stalePreloadReload.ts pattern); a sw-update reload still proceeds (cannot loop, and that is today's behaviour).

**DD-5 First-install rule, race checked.** registerSW.js is injected and registers only on window `load`; main.tsx is a module script, so it evaluates before `load`. On a true first visit getRegistration therefore resolves undefined, or a registration whose `active` is null because install and precache take far longer than that callback. The rule: an update is meaningful if `navigator.serviceWorker.controller` existed at load or the registration already had `active` at startup; otherwise the first controllerchange is the first-install claim and is consumed without reloading, and every later one is meaningful. Losing the race costs at most one extra reload, never a loop.

**DD-6 /privacy needs no cache key of its own.** The prerender plugin writes `dist/privacy/index.html`, but Caddy never serves it at `/privacy` or `/privacy/`: both fall to the SPA fallback and return `dist/index.html`, the same document as `/` and `/train` (live prod: /, /privacy and /privacy/ are all 61895 bytes with the Home h1; local fixture agrees). Only the literal `/privacy/index.html` returns the prerendered page. So every route-like navigation is one document and shares one key. The route guard excludes file-like paths (last segment has a dot, except `/index.html`), which keeps `/privacy/index.html`, `/google83883b0af640c73c.html` and `/og-image.jpg` from overwriting the shared shell. That poisoning risk is new with a single key and is why the guard exists.

**DD-7 Legacy per-URL entries stay.** Cache name stays `html-shell`. Old entries become unreachable but are left in place: they are a handful of small HTML documents, deleting them needs new worker activate logic, and their `date` headers in the diagnostics are direct evidence for or against the stale-entry hypothesis. The shared key is synthetic (`/__html-shell__`) so it cannot collide with a legacy entry and is distinguishable in diagnostics.

**DD-8 Sentry details that would silently lose data.** Sentry normalizes `event.contexts` to `normalizeDepth` 3 (default, not overridden in instrument.ts), so an array of objects under `contexts.stale_build` arrives as `[Object]`: report shell entries as strings. Legacy html-shell keys can hold `/auth/reset-password?token=<JWT>`: report pathnames only. Do not set the stalePreloadReload pending flag on this path, since sentryBeforeSend drops everything while it is set. The fixed message must match none of the `ignoreErrors` patterns.
</design_decisions>

<tasks>

<task type="tracer">
  <name>Task 1: End to end: an old bundle detects a new deploy, reports it, and reloads once</name>
  <files>frontend/vite.config.ts, frontend/src/lib/htmlShellCache.ts, frontend/src/lib/updateReload.ts, frontend/src/lib/staleBuildDiagnostics.ts, frontend/src/lib/buildVersionCheck.ts, frontend/src/main.tsx, frontend/scripts/check-pwa-build.mjs, frontend/package.json, frontend/src/lib/__tests__/updateReload.test.ts, frontend/src/lib/__tests__/buildVersionCheck.test.ts, frontend/src/lib/__tests__/staleBuildDiagnostics.test.ts, frontend/src/__tests__/instrument.beforeSend.test.ts</files>
  <precondition>frontend/node_modules exists; if not, run `npm --prefix frontend ci` first.</precondition>
  <behavior>
    buildVersionCheck.test.ts (real gate and real diagnostics, @sentry/react mocked with captureMessage and flush, fetch stubbed, window.location stubbed as in stalePreloadReload.test.ts):
    - mismatch reloads, and captureMessage runs before location.reload (mock.invocationCallOrder); the reload carries the auto-reload marker
    - match does not reload and sends no event
    - fetch rejects, non-200, HTML body whose json() throws, `{}`, non-string buildId and empty buildId each do not reload
    - fetch is called with /version.json and cache 'no-store'
    - a hung fetch aborts at BUILD_VERSION_FETCH_TIMEOUT_MS without reloading, and the next check still runs
    - a stamp inside the cooldown stops the reload and sends no event; after the cooldown it reloads
    - resume: two checks inside SW_UPDATE_DEBOUNCE_MS make one fetch; a failed fetch does not consume the debounce; hidden visibilitychange makes no fetch
    - installBuildVersionCheck with defaults under vitest makes no fetch and adds no listeners (inert in dev and tests); with enabled true and a running ID it fetches at once
    updateReload.test.ts: two requests make one reload and one beforeReload; beforeReload rejecting, throwing synchronously or never settling still reloads (the last at BEFORE_RELOAD_TIMEOUT_MS, fake timers); a sw-update request within the cooldown after a mismatch reload does not reload again; storage throwing blocks build-mismatch and allows sw-update.
    staleBuildDiagnostics.test.ts: one captureMessage with exactly STALE_BUILD_SENTRY_MESSAGE and contexts.stale_build carrying every field below; a shell key with ?token=abc reports its pathname only and no string in the event contains the token; html_shell_entries are strings; entries are capped at MAX_REPORTED_SHELL_ENTRIES while the count is true; caches rejecting, performance throwing or getRegistration rejecting still send one event and resolve; caches never settling sends the event at CACHE_COLLECT_TIMEOUT_MS with collection 'timed_out'; captureMessage throwing, flush rejecting and flush never settling all resolve; CACHE_COLLECT_TIMEOUT_MS + SENTRY_FLUSH_TIMEOUT_MS is below BEFORE_RELOAD_TIMEOUT_MS.
    instrument.beforeSend.test.ts: sentryBeforeSend returns an event carrying STALE_BUILD_SENTRY_MESSAGE, and no pattern in the ignoreErrors passed to the mocked Sentry.init matches that message.
  </behavior>
  <action>
    Write tests first where practical; they exercise the modules below.

    frontend/vite.config.ts: add randomBytes to the crypto import, a named BUILD_ID_RANDOM_BYTES and a module-level BUILD_ID per DD-1, with a comment stating why git is unavailable. Add buildVersionPlugin() (apply 'build', generateBundle emits asset version.json with source JSON.stringify of an object with key buildId) to `plugins`, and `define` with key import.meta.env.VITE_BUILD_ID set to JSON.stringify(BUILD_ID). Do not touch runtimeCaching in this task.

    frontend/src/lib/htmlShellCache.ts: export HTML_SHELL_CACHE_NAME = 'html-shell' only. Task 3 extends this file.

    frontend/src/lib/updateReload.ts: export UPDATE_RELOAD_STORAGE_KEY ('flawchess:update-reload-at'), UPDATE_RELOAD_COOLDOWN_MS (5 minutes), BEFORE_RELOAD_TIMEOUT_MS (3 seconds), type UpdateReloadReason ('build-mismatch' | 'sw-update'), interface UpdateReloadRequest with reason, atStartup boolean and optional beforeReload returning Promise of void, and requestUpdateReload(request). Implement a single internal applyNow: return if a reload is already in flight; return if within the cooldown (read like stalePreloadReload.ts readLastReloadMs); stamp; if stamping failed and the reason is build-mismatch, return (DD-4); mark in flight; run beforeReload wrapped so a synchronous throw, a rejection or BEFORE_RELOAD_TIMEOUT_MS elapsing all continue; then always call reloadAutomatically. Task 2 adds the session hold in front of applyNow.

    frontend/src/lib/staleBuildDiagnostics.ts: export type BuildCheckTrigger ('startup' | 'resume'), STALE_BUILD_SENTRY_MESSAGE ('Stale frontend build detected by version check', no variables), CACHE_COLLECT_TIMEOUT_MS (800), SENTRY_FLUSH_TIMEOUT_MS (1200), MAX_REPORTED_SHELL_ENTRIES (20), and async reportStaleBuild with runningBuildId, deployedBuildId, trigger, which never rejects. Collect synchronous fields in a try/catch: page_age_ms from Date.now() minus performance.timeOrigin; navigation_type and transfer_size from the first performance.getEntriesByType('navigation') entry (guard the method, jsdom may lack it); sw_controller boolean. Collect async fields inside a timeout race on CACHE_COLLECT_TIMEOUT_MS: sw_active_state and sw_waiting_state from navigator.serviceWorker.getRegistration; html_shell_entry_count and html_shell_entries from the html-shell cache (guard `caches` existing, call caches.has(HTML_SHELL_CACHE_NAME) first so the read never creates the cache, then cache.keys and cache.match), each entry the string pathname then ' @ ' then the response `date` header, pathname only per DD-8, capped at MAX_REPORTED_SHELL_ENTRIES. Set collection to 'complete', 'timed_out' or 'failed'. Then in a try/catch call Sentry.captureMessage with the fixed message, level 'info' (this is expected after every deploy, not an error), tags source 'build-version-check' and trigger, contexts key stale_build with running_build_id, deployed_build_id and the fields above, and await Sentry.flush(SENTRY_FLUSH_TIMEOUT_MS) inside a timeout race of the same length. A partial event must still be sent when collection times out or fails; a late-resolving collection must not send a second event.

    frontend/src/lib/buildVersionCheck.ts: export parseDeployedBuildId(body: unknown) returning a non-empty buildId string or null; BUILD_VERSION_FETCH_TIMEOUT_MS (5 seconds); createBuildVersionChecker(runningBuildId) returning a check(trigger) promise that never rejects; installBuildVersionCheck(options with optional enabled and runningBuildId, defaulting to import.meta.env.PROD and import.meta.env.VITE_BUILD_ID). The fetch helper uses fetch('/version.json', cache 'no-store', AbortController signal cleared in finally), requires status exactly 200, parses JSON and returns null on any failure, with a comment that these failures are expected (offline, deploy window, the dev server's index.html) and deliberately skip Sentry per frontend/CLAUDE.md. check: on 'resume' return when within SW_UPDATE_DEBOUNCE_MS (import it from swUpdate.ts) of the last completed check; return if one is in flight; a null result returns without stamping, so the next resume retries; otherwise stamp; on mismatch call requestUpdateReload with reason 'build-mismatch', atStartup true only for the 'startup' trigger, beforeReload calling reportStaleBuild. install is a no-op when not enabled or the running ID is not a non-empty string; otherwise it adds visibilitychange (visible only) and focus listeners that call check('resume') and calls check('startup') once.

    frontend/src/main.tsx: import and call installBuildVersionCheck() directly after installStalePreloadReload(), outside the serviceWorker branch, with a short comment explaining that an already-current service worker means reg.update() finds nothing, so an old bundle could otherwise run indefinitely.

    frontend/scripts/check-pwa-build.mjs (Node built-ins only, model the header on check-activity-layout.mjs), with npm script check:pwa-build: fail non-zero unless dist/version.json parses with a non-empty buildId; dist/index.html references an entry matching src="/assets/index-*.js"; that entry file contains the ID literally (this also proves main.tsx wiring, since an unused literal is tree-shaken); the precache list parsed from dist/sw.js (url:"..." entries, minified form confirmed) is non-empty and has no .html entry and no version.json entry. Baseline at HEAD: a build produces no dist/version.json, so the script must fail there.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run src/lib/__tests__/updateReload.test.ts src/lib/__tests__/buildVersionCheck.test.ts src/lib/__tests__/staleBuildDiagnostics.test.ts src/__tests__/instrument.beforeSend.test.ts && npm --prefix frontend run build && npm --prefix frontend run check:pwa-build</automated>
  </verify>
  <done>A real build has one ID in dist/version.json and the entry chunk; a mismatch sends one fixed-message event then reloads once per cooldown; every malformed or failed response stays put; collection failure or hang never blocks the reload.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Sessions hold the reload, and the service worker takeover goes through the same gate</name>
  <files>frontend/src/lib/playActive.ts, frontend/src/lib/updateReload.ts, frontend/src/lib/buildVersionCheck.ts, frontend/src/lib/swUpdate.ts, frontend/src/main.tsx, frontend/src/components/train/TrainScoreScreen.tsx, frontend/src/lib/__tests__/updateReload.test.ts, frontend/src/lib/__tests__/buildVersionCheck.test.ts, frontend/src/lib/__tests__/swUpdate.test.ts, frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx</files>
  <behavior>
    updateReload.test.ts (real playActive via renderHook of useMarkPlayActive; vi.resetModules plus dynamic imports per test, since the gate is a singleton):
    - runtime request while active: no reload even after timers advance
    - startup request while active: reloads
    - held, then session ends: no reload before SESSION_END_SETTLE_MS, reload after it
    - held, unmount and a new mount in one synchronous step (rematch shape): no reload after the settle delay
    - held, play ends while useHoldUpdateReload is mounted (solve to score screen): no reload; hold unmounts: reload after the settle delay
    - applyHeldUpdateReload: returns false with nothing held; true and no reload while active; true and reload once inactive
    - a held sw-update is replaced by a later mismatch, whose beforeReload then runs; a held mismatch is not replaced by a later sw-update
    buildVersionCheck.test.ts: resume mismatch during a session makes no reload and no event; after the session ends a resume inside the debounce window applies it without a new fetch and sends the event; a startup mismatch during a session reloads.
    swUpdate.test.ts (navigator.serviceWorker stubbed as an EventTarget with controller and getRegistration):
    - no controller, no registration: first controllerchange does not reload; a second one reloads
    - no controller, registration.active present: first controllerchange reloads
    - controller at load: first controllerchange reloads
    - getRegistration rejecting: no unhandled rejection, first controllerchange does not reload
    - controllerchange during a session holds, and applies when the session ends
    TrainScoreScreen.test.tsx: isUpdateSessionActive is true while rendered and false after unmount.
  </behavior>
  <action>
    frontend/src/lib/playActive.ts: add exports isPlayActive() and subscribePlayActive (the existing subscribe). Do not change the hook behaviour or add a flag.

    frontend/src/lib/updateReload.ts: per DD-2 and DD-3 add SESSION_END_SETTLE_MS (1 second), a module-level held request and hold count, and exports isUpdateSessionActive() (isPlayActive or hold count above zero), applyHeldUpdateReload() returning whether a reload was held (applies it via applyNow when inactive), and useHoldUpdateReload() (effect increments the count; cleanup decrements and schedules the check). In requestUpdateReload: if not atStartup and a session is active, hold it (a mismatch replaces a held sw-update; a sw-update never replaces a held mismatch) and subscribe once to subscribePlayActive. Any play-flag change or hold release schedules one settle timer, whose callback applies the held request only if a session is still not active at that moment. Comment why the delay exists (same-commit remounts).

    frontend/src/lib/buildVersionCheck.ts: at the top of check, for 'resume' only and before the debounce, return if applyHeldUpdateReload() is true: nothing new can be learned from a fetch, and the debounce must not swallow a held reload.

    frontend/src/lib/swUpdate.ts: add installSwControllerReload() per DD-5: a local flag starts as whether navigator.serviceWorker.controller exists; getRegistration sets it when the registration has active, with a catch so it can never be an unhandled rejection (FLAWCHESS-91); the controllerchange listener is always registered, consumes the first event when the flag is false by setting it true and returning, and otherwise calls requestUpdateReload with reason 'sw-update', atStartup false. Move the existing bug-fix comment from main.tsx here and add at the fix site what broke: the listener was only added when a controller existed at load, so a page first opened without one never reloaded on later deploys.

    frontend/src/main.tsx: replace the controller check and inline listener with installSwControllerReload() inside the serviceWorker branch; remove the now-unused reloadAutomatically import. Leave createSwUpdateChecker wiring unchanged.

    frontend/src/components/train/TrainScoreScreen.tsx: call useHoldUpdateReload() near the top of the component, with a one-line comment that the score screen is local Train.tsx state, so a reload here would lose it (DD-3).
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run src/lib/__tests__/updateReload.test.ts src/lib/__tests__/buildVersionCheck.test.ts src/lib/__tests__/swUpdate.test.ts src/components/train/__tests__/TrainScoreScreen.test.tsx</automated>
  </verify>
  <done>Mid-session reloads are held and applied at session end or next resume; startup always applies; first install stays quiet; later takeovers reload even without a controller at load; the score screen is never lost to a reload.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Stop the server and offline shell handing out stale HTML, then prove every invariant</name>
  <files>deploy/Caddyfile, frontend/vite.config.ts, frontend/src/lib/htmlShellCache.ts, frontend/src/lib/__tests__/htmlShellCache.test.ts, frontend/scripts/check-pwa-build.mjs, .github/workflows/ci.yml, CHANGELOG.md</files>
  <precondition>Docker daemon reachable and caddy:2.11.7 available (matches frontend/Dockerfile; planner already pulled it locally).</precondition>
  <behavior>
    htmlShellCache.test.ts, each case run on the original function AND on a copy revived from its toString() with new Function, which is what generateSW serialization does and which fails on any closure:
    - isHtmlShellNavigation true for navigate mode on /, /?utm_source=pwa, /train, /privacy, /privacy/, /index.html, /auth/reset-password?token=x
    - false for /api/auth/google/callback, /privacy/index.html, /google83883b0af640c73c.html, /og-image.jpg, /sw.js, and any non-navigate mode on /train
    - htmlShellCacheKeyPlugin.cacheKeyWillBeUsed resolves to HTML_SHELL_CACHE_KEY for any request URL, including /?utm_source=pwa and /train
  </behavior>
  <action>
    frontend/src/lib/htmlShellCache.ts: add HTML_SHELL_CACHE_KEY ('/__html-shell__'), isHtmlShellNavigation typed structurally as request with mode string plus url URL (not DOM Request: tsconfig.node pulls this file in, and its lib has no DOM) and htmlShellCacheKeyPlugin with property cacheKeyWillBeUsed as an async ARROW function returning the literal key. generateSW serializes both with toString(), so they must reference nothing outside their own body, and method shorthand would serialize to a syntax error. Comment both constraints above the functions, since Workbox strips comments inside serialized functions, and record DD-6 including that if Caddy ever serves the prerendered privacy page at /privacy, this key needs revisiting. The test keeps the literal and the exported const in step.

    frontend/vite.config.ts: in the navigation route use urlPattern isHtmlShellNavigation, cacheName HTML_SHELL_CACHE_NAME, and add plugins with htmlShellCacheKeyPlugin beside cacheableResponse. Keep the /api NetworkOnly route first, keep networkTimeoutSeconds absent. Add a comment at the fix site: entries were keyed per full URL with no expiry, so /?utm_source=pwa could hold a weeks-old shell served whenever its network fetch threw. State DD-7 in the comment.

    frontend/scripts/check-pwa-build.mjs: add assertions that dist/sw.js contains cacheKeyWillBeUsed, the literal /__html-shell__ and cacheName:"html-shell". Add a CI step named "PWA build invariants" running npm run check:pwa-build (working-directory frontend) immediately after "Type check and build (tsc + vite)" in .github/workflows/ci.yml: a bundle/version.json ID split would reload every client on every resume, so it must not reach a release.

    deploy/Caddyfile, inside handle @static: append /version.json to the @nocache path list and add a second matcher `@html path / *.html` with header no-cache. In the SPA fallback handle, replace the path-matched header line with an unconditional `header Cache-Control "no-cache"` (this handle only ever serves index.html). Add a comment stating what broke: Caddy's directive order runs `header` before `try_files`, so a /index.html matcher sees the original path (/train) and never fires, and live /train had no Cache-Control at all, leaving freshness to the browser heuristic; `/` and `/index.html` were also uncovered in @static. Do not change @immutable, @maiaworker or @vendored_runtime. The planner proved this exact change on a scratch copy.

    CHANGELOG.md under [Unreleased] ### Fixed: "The installed app no longer gets stuck on an old version. It now checks for a new version when it opens and when you come back to it, and updates itself, waiting until you finish your puzzle session or bot game."

    Commit the task, then write temp/pwa-stale/check_caddy_headers.sh (gitignored; takes an optional Caddyfile path, default deploy/Caddyfile). It builds a fixture under temp/pwa-stale/srv with index.html containing HOME, privacy/index.html containing PRIVACYDOC, assets/app-abc123.js, version.json, sw.js, push-sw.js, registerSW.js, manifest.webmanifest, maia/maia-worker.js, maia/model.onnx, engine/x.wasm. It derives a test Caddyfile with sed: rewrite the three site addresses to http:// forms (flawchess.com; flawchess.org and www.flawchess.org; analytics.flawchess.com) and insert `auto_https off` as the first global option. It runs the caddy:2.11.7 container on 127.0.0.1:18099 with both mounted read-only, removes it via an EXIT trap, and curls with Host: flawchess.com, asserting:
    - Cache-Control no-cache: /, /index.html, /train, /privacy, /privacy/, /privacy/index.html, /version.json, /sw.js, /registerSW.js, /manifest.webmanifest, /push-sw.js, /maia/maia-worker.js
    - exactly public, max-age=31536000, immutable: /assets/app-abc123.js
    - exactly public, max-age=2592000: /maia/model.onnx, /engine/x.wasm
    - /train with If-Modified-Since from its Last-Modified: 304 that still carries no-cache and Cross-Origin-Embedder-Policy
    - bodies: /train, /privacy, /privacy/ contain HOME (DD-6); /privacy/index.html contains PRIVACYDOC
    - /api/health has no Cache-Control (the fallback header must not leak; it will be a 502 with no backend)
    It exits non-zero on any failure. Recorded baseline against the current Caddyfile: no Cache-Control on /, /index.html, /train, /privacy, /privacy/, /privacy/index.html, /version.json, so those must fail.

    Mutation proof (project feedback: grep or symbol presence is not proof). With all code committed, apply each mutation below, run the named check, confirm the named case FAILS, restore with `git checkout -- <file>`, and record the failing test name in the SUMMARY table. A mutation that does not fail is a gap: fix the test, do not drop the row.
    - M1 buildVersionCheck.ts: never request a reload on mismatch. buildVersionCheck.test: mismatch reloads.
    - M2 buildVersionCheck.ts: the fetch helper returns an empty string instead of null when the fetch rejects. buildVersionCheck.test: fetch rejects does not reload.
    - M3 buildVersionCheck.ts: drop the status check and field validation. buildVersionCheck.test: non-200 and garbage do not reload.
    - M4 updateReload.ts: remove the cooldown read. Both tests: cooldown stops the reload.
    - M5 updateReload.ts: remove the session-active hold. updateReload.test: runtime request while active.
    - M6 updateReload.ts: hold regardless of atStartup. updateReload.test: startup request while active.
    - M7 updateReload.ts: remove the session-end subscription. updateReload.test: held then session ends.
    - M8 updateReload.ts: apply synchronously on the flag edge, no settle timer. updateReload.test: rematch shape.
    - M9 updateReload.ts: await beforeReload with no timeout and reload only after it succeeds. updateReload.test: rejecting and never-settling beforeReload.
    - M10 buildVersionCheck.ts: remove the applyHeldUpdateReload early return. buildVersionCheck.test: resume inside the debounce window applies it.
    - M11 swUpdate.ts: register the listener only when a controller exists at load. swUpdate.test: second controllerchange reloads with no controller at load.
    - M12 swUpdate.ts: remove the first-install exemption. swUpdate.test: first controllerchange does not reload.
    - M13 swUpdate.ts: call reloadAutomatically directly. swUpdate.test: controllerchange during a session holds.
    - M14 staleBuildDiagnostics.ts: remove the collection timeout race. staleBuildDiagnostics.test: caches never settling.
    - M15 staleBuildDiagnostics.ts: report the full key URL. staleBuildDiagnostics.test: the token never appears.
    - M16 staleBuildDiagnostics.ts: report entries as objects. staleBuildDiagnostics.test: entries are strings.
    - M17 TrainScoreScreen.tsx: remove useHoldUpdateReload. TrainScoreScreen.test: holds while rendered.
    - M18 htmlShellCache.ts: return request.url as the key. htmlShellCache.test: key case.
    - M19 htmlShellCache.ts: remove the file-like path guard. htmlShellCache.test: /og-image.jpg and /privacy/index.html cases.
    - M20 htmlShellCache.ts: move the key literal to a module const the function reads. htmlShellCache.test: revived copy throws.
    - M21 vite.config.ts: write a freshly generated second ID to version.json. Rebuild, then check:pwa-build fails.
    - M22 main.tsx: remove the installBuildVersionCheck call. Rebuild, then check:pwa-build fails (literal tree-shaken).
    - M23 Caddyfile: run temp/pwa-stale/check_caddy_headers.sh against the pre-fix file from `git show main:deploy/Caddyfile` written to temp/pwa-stale/. /train and /version.json fail.
    - M24 Caddyfile: a temp/pwa-stale copy without the @html lines. /index.html and /privacy/index.html fail.

    Finish with the frontend gate: `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `npm --prefix frontend run check:pwa-build`, `npm --prefix frontend test -- --run`, `npm --prefix frontend run knip`. Run long commands in the foreground: a backgrounded run dies with the agent.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- --run src/lib/__tests__/htmlShellCache.test.ts && npm --prefix frontend run build && npm --prefix frontend run check:pwa-build && bash temp/pwa-stale/check_caddy_headers.sh</automated>
  </verify>
  <done>Caddy fixture passes against the new Caddyfile and fails against the pre-fix one; dist/sw.js carries the html-shell plugin; all 24 mutations recorded as failing; lint, build, tests and knip clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| network to browser | /version.json is a same-origin, public, unauthenticated response, possibly from an intermediary such as a captive portal |
| browser to Sentry | diagnostics leave the device and read device-local cache keys, which may contain credentials in their query strings |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261107-01 | Tampering | buildVersionCheck.ts response handling | low | mitigate | The body is only compared as a string and reported as a context value, never evaluated, so a forged response cannot inject code. Non-200, non-JSON and missing-field responses are rejected (M2, M3) |
| T-261107-02 | Denial of service | updateReload.ts reload loop from a persistent or forged mismatch | medium | mitigate | Five-minute sessionStorage cooldown on every update reload; mismatch reloads fail closed when storage is unavailable (M4) |
| T-261107-03 | Information disclosure | staleBuildDiagnostics.ts html-shell keys | high | mitigate | Legacy keys can hold /auth/reset-password?token=JWT; only pathnames are reported, and a test asserts the token appears nowhere in the event (M15) |
| T-261107-04 | Information disclosure | /version.json | low | accept | Carries only a build timestamp and random suffix; no secret, user or commit data |
| T-261107-05 | Tampering | html-shell shared key | low | mitigate | File-like navigations are excluded from the route, so a non-shell document cannot overwrite the shared offline shell (M19) |
| T-261107-SC | Tampering | npm/pip/cargo installs | low | accept | No new packages; `npm ci` installs only from the committed lockfile. No package-legitimacy checkpoint applies |
</threat_model>

<verification>
Task verify commands plus the frontend gate at the end of Task 3. The full pre-merge gate is run by the orchestrator.

Browser smoke (grep cannot prove the service worker runs the plugin). If this agent has no browser tool, record it as pending in the SUMMARY: the orchestrator runs it.
1. Build with Sentry off so no fake evidence reaches the production project: `VITE_SENTRY_DSN= npm --prefix frontend run build`, then `npm --prefix frontend run preview -- --port 4173`.
2. Load http://localhost:4173/train, then /library. In the page, read the keys of caches.open('html-shell'): exactly one, with pathname /__html-shell__.
3. Write a different buildId to frontend/dist/version.json and reload: one automatic reload (sessionStorage flawchess:update-reload-at is set), and the page then stays loaded for 10 seconds.
4. Clear that key, write garbage to frontend/dist/version.json and reload: no extra reload.
5. Stop preview and navigate to /library in the tab: the app shell still renders from html-shell.
</verification>

<success_criteria>
- A running old bundle self-repairs on next startup or resume, with one diagnostic event, without a reload loop.
- No update reload interrupts an active Train session or bot game; held reloads are applied afterwards.
- First install does not reload; later takeovers always do.
- All HTML and /version.json are no-cache on the real Caddy config; immutable and vendored rules are unchanged.
- The offline shell is one entry, the latest successful load.
- Every invariant has a recorded failing mutation.
- CHANGELOG bullet present under [Unreleased].
</success_criteria>

<output>
Create `.planning/quick/261107-dnz-stop-the-installed-pwa-showing-outdated-/261107-dnz-SUMMARY.md` when done, including the mutation table, the caddy fixture results and the browser smoke status.
</output>
