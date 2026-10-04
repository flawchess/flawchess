---
phase: 232-frontend-major-dependency-upgrades
verified: 2026-10-04T12:54:20Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - .planning/phases/232-frontend-major-dependency-upgrades/232-01-PLAN.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-01-SUMMARY.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-02-PLAN.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-02-SUMMARY.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-03-PLAN.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-03-SUMMARY.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-04-PLAN.md
  - .planning/phases/232-frontend-major-dependency-upgrades/232-04-SUMMARY.md
  - frontend/package-lock.json
  - frontend/package.json
  - frontend/src/__tests__/instrument.beforeSend.test.ts
  - frontend/src/instrument.ts
  - frontend/tsconfig.app.json
  - frontend/tsconfig.json
  - renovate.json
covered_digest: "v2:sha256:1b4e3238b1c3ba4573a4768b49fdd34486397e2038b7a4a5fd87d583b988a7f8"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "D-03: a deliberate error produced by the browser SDK reaches the flawchess Sentry project (env development) with tag and context intact"
    reason: "Owner accepted the recorded orchestrator evidence in 232-UAT.md test 1 (result: pass). A fresh-profile headless Chrome drove the dev app, and the app's own @sentry/react 11.4.0 transport POSTed to ingest.de.sentry.io (sentry_client=sentry.javascript.react/11.4.0, HTTP 200). That produced event 256ca584f8fc4593b27cc10659230a64 in FLAWCHESS-CH with tag and context intact and no IP. The verifier did not observe this at runtime; the evidence basis is owner acceptance of the recorded orchestrator evidence."
    accepted_by: "Adrian Imfeld (owner, via 232-UAT.md)"
    accepted_at: "2026-10-04T12:40:40Z"
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed:
    - "D-03 in-browser SDK transport delivery (truth 10): resolved by owner-accepted UAT (232-UAT.md test 1 pass)"
    - "G-232-3 / prior advisory: the reset token leaked through navigation breadcrumb data.from/data.to. Fixed in 814a3c44c (scrubNavigationBreadcrumbs, called from sentryBeforeSend), with mutation proof and confirmation against the real SDK."
  gaps_remaining: []
  regressions: []
advisory: []
---

# Phase 232: Frontend Major Dependency Upgrades Verification Report

**Phase Goal:** Take the major frontend upgrades (vite-plugin-pwa 2, @sentry/react 11, TypeScript 7 via the side-by-side alias), one plan per dependency, keep the js-yaml/fast-uri security overrides in-major, and add a Renovate rule that stops offering their majors, without widening Sentry data collection.
**Verified:** 2026-10-04T12:54:20Z
**Status:** passed
**Re-verification:** Yes, second delta. Round 1 (commit 3ce5bf6df) re-verified the code-review fixes 2361acf86 (WR-01) and cd7f70dfe (WR-02). This round covers 814a3c44c, which fixes gap G-232-3: navigation breadcrumbs carried the reset token. Chrome-extension UAT found it, and round 1 had flagged it as an advisory. 814a3c44c touches only `frontend/src/instrument.ts` and `frontend/src/__tests__/instrument.beforeSend.test.ts`. `renovate.json`, both tsconfigs, `package.json`/lock, `vite.config.ts`, `main.tsx` and `Privacy.tsx` are unchanged since round 1.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DEP-PWA2: vite-plugin-pwa is 2.0.0 and the generated service worker is inert (same manifest/registerSW, same precache set, maia/ and engine/ excluded) | VERIFIED | Lock `vite-plugin-pwa` 2.0.0. `npm run build` in the real tree (re-run this round) exits 0 and prints `PWA v2.0.0`, `precache 19 entries`; `grep -c 'maia/\|engine/' dist/sw.js` = 0. The prior byte-identity evidence (`temp/phase-232/pwa/v1` vs `v2`: sw.js, manifest and registerSW.js identical, 19-entry precache) and the orchestrator's browser smoke still hold, since no fix touched the PWA config. Caveat: the 1.3.0 side rests on executor artifacts. |
| 2 | DEP-OVR: fast-uri override floor `^3.1.8`, every installed fast-uri is 3.1.8 (no 4.x), js-yaml stays 4.x | VERIFIED | `npm ls fast-uri js-yaml`: every ajv@8.20.0 consumer dedupes to fast-uri 3.1.8, and cosmiconfig resolves js-yaml 4.3.2. `npm ls --all` exits 0. Prior `audit-ci` pass stands (no dependency version changed). |
| 3 | DEP-OVR: `renovate.json` has a packageRule disabling majors for override-only js-yaml and fast-uri | VERIFIED | The rule is present: `matchManagers npm`, `matchDepTypes overrides`, `matchPackageNames [js-yaml, fast-uri]`, `matchUpdateTypes major`, `enabled false`, and the file parses as JSON. `--strict` validator acceptance rests on the executor's evidence. |
| 4 | DEP-SENTRY11: `@sentry/react`, `@sentry/browser`, `@sentry/core` all 11.4.0, no leftover 10.x | VERIFIED | `npm ls @sentry/core`: react, browser, browser-utils, feedback, replay and replay-canvas are all 11.4.0, with core deduped to 11.4.0. `tsc -b` passes inside `npm run build`. |
| 5 | D-02: `Sentry.init` pins a v10-equivalent `dataCollection` and `attachStacktrace: false`, and the real SDK honors it | VERIFIED | The block is intact in `instrument.ts` (userInfo false, cookies false, header and query deny lists, httpBodies [], attachStacktrace false). I ran the real unmocked `@sentry/react` 11.4.0 in jsdom with transport `send` spied: the event carries no `user`, the page URL is query-filtered, and the navigation crumbs are query-filtered. Prior evidence (infer_ip never, UA-only headers, no synthetic stack) is not affected by the additive beforeSend steps. |
| 6 | D-02: a unit test fails when the dataCollection block or `attachStacktrace` is removed (mutation-proven) | VERIFIED | Round 1 showed that removing `attachStacktrace: false` gives 1 failed / 30 passed. 814a3c44c only adds a beforeSend step and one test, so the baseline test is unchanged. The real tree now passes 32/32 (`npx vitest run src/__tests__/instrument.beforeSend.test.ts`). |
| 7 | D-02 no widening: the Privacy page and the `frontend/CLAUDE.md` Sentry rules stay unchanged and still true | VERIFIED | `git diff main...HEAD -- src/pages/Privacy.tsx` is empty. WR-01 and G-232-3 both narrow collection relative to v10.73.0: the page-URL query and the navigation-breadcrumb queries are now filtered, where v10 sent both. WR-02 does not touch runtime. |
| 8 | DEP-TS7: the build type-checks with native TS 7 while `require('typescript')` is still the TS 6 JS API; deprecated tsconfig options removed; the gate catches errors | VERIFIED | The alias is `"typescript": "npm:@typescript/typescript6@~6.0.2"` (WR-02). The installed 6.0.2 satisfies typescript-eslint 8.69.0's peer `>=4.8.4 <6.1.0`, and `npm ls --all` exits 0. `.bin/tsc --version` = 7.0.2, and `require('typescript')` = 6.0.3 with `createProgram` a function. `npm run build` (`tsc -b && vite build`), `npm run lint` and `npm run knip` all exit 0 (re-run this round). `baseUrl`/`ignoreDeprecations` are absent from both tsconfigs and `@/*` paths are kept. The prior negative control (an injected TS2322 fails `tsc -b`) stands. |
| 9 | Phase documentation closed: Phase 217 D-11 superseded, STATE.md TS7 thread replaced and Sentry deploy watch added, SEED-162 cluster 3 resolved, SEED-188/189 captured, CHANGELOG `[Unreleased]` bullet, no em-dash | VERIFIED | No doc files were touched by the fix commits, so the prior evidence holds. |
| 10 | D-03: a deliberate error produced by the browser SDK reaches the `flawchess` Sentry project (env development) with tag and context intact | PASSED (override) | Override: owner-accepted UAT (232-UAT.md test 1, result pass, 2026-10-04T12:40:40Z). Evidence basis: owner acceptance of recorded orchestrator evidence (a headless Chrome SDK-transport POST returned HTTP 200, producing event 256ca584f8fc4593b27cc10659230a64 in FLAWCHESS-CH with tag and context intact and no IP). It is not a runtime observation by this verifier. The envelope content was independently confirmed with the real SDK (truths 5 and 7). |

**Score:** 10/10 truths verified (1 via owner-accepted override; 0 present-but-behavior-unverified)

### Review-Fix and Gap-Fix Verification

| Fix | Claim | Verifier evidence | Status |
|-----|-------|-------------------|--------|
| WR-01 (2361acf86) | `sentryBeforeSend` scrubs the query from `event.request.url` for every kept event | `scrubUrlQuery()` runs after the axios block. Mutation in a scratch copy (round 1) fails 2 tests. With the real unmocked SDK 11.4.0 on `/reset-password?token=...`, the envelope `request.url` is `.../reset-password?[Filtered]`, and it reverts to the raw token when mutated. | HOLDS |
| WR-02 (cd7f70dfe) | The alias is capped at 6.0.x to match typescript-eslint `<6.1.0` | `package.json` and the lock root read `~6.0.2`, with 6.0.2 resolved. `npm ls --all` exits 0, and lint, build and knip all exit 0. | HOLDS |
| G-232-3 (814a3c44c) | `scrubNavigationBreadcrumbs()` (instrument.ts:195) filters the query from `data.from`/`data.to` on `category: "navigation"` crumbs. It is called from `sentryBeforeSend` after the request-URL scrub. | The new unit test passes (32/32). I mutated a scratch copy by removing the call: exactly that test fails (`1 failed / 31 passed`). Real unmocked SDK 11.4.0 in jsdom, spied transport: `pushState('/reset-password?token=…secret.jwt')` then `replaceState('/login?next=%2Fopenings')`, then `captureException`. The envelope has crumbs `{from:"/login", to:"/reset-password?[Filtered]"}` and `{from:"/reset-password?[Filtered]", to:"/login?[Filtered]"}`, and `request.url` `.../login?[Filtered]`; the serialized event contains no `secret.jwt`. With the call removed, the same real-SDK check fails. This matches the orchestrator's evidence from the owner's Chrome on a DSN-enabled dev server. | HOLDS |

### Resolved Advisory (from round 1)

| # | Finding | Resolution |
|---|---------|------------|
| 1 | The navigation breadcrumb `data.from`/`data.to` carried `/reset-password?token=<JWT>` into later events. This was pre-existing in v10.73.0. | Resolved by 814a3c44c (G-232-3). The `scrubUrlQuery` doc comment was corrected in the same commit to name both the page URL and navigation breadcrumbs. |
| 2 | TrainStreakCard count-up timing flake in the round-1 full run | Did not recur: the round-2 full run was 303/303 files and 4988/4988 tests. It stays a known load-dependent flake outside the phase. |

### Requirements Coverage

No REQUIREMENTS.md exists for this phase; the descriptive IDs come from 232-RESEARCH.md.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEP-PWA2 | 232-01 | vite-plugin-pwa 1 -> 2, SW inert | SATISFIED | Truth 1 |
| DEP-OVR | 232-02 | in-major overrides + Renovate majors-off rule | SATISFIED | Truths 2, 3 |
| DEP-SENTRY11 | 232-03 | Sentry 11, no widened collection | SATISFIED | Truths 4-7, 10 (owner-accepted) |
| DEP-TS7 | 232-04 | TS 7 via side-by-side alias | SATISFIED | Truths 8, 9 |

No orphaned requirements.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `package.json` scripts.build `tsc -b && vite build` | native TS 7 `tsc` | `.bin/tsc -> @typescript/native/bin/tsc` | WIRED | `tsc --version` 7.0.2; `npm run build` exit 0 |
| typescript-eslint / sonarjs | TS 6 JS API | `typescript` alias (`~6.0.2`) -> `@typescript/typescript6` | WIRED | `createProgram` is a function; lint exit 0; peer range satisfied |
| `instrument.ts` `Sentry.init({dataCollection, beforeSend})` | `@sentry/core` options + event pipeline | real SDK | WIRED | the real-SDK envelope shows the scrubbed URL and crumbs, and no user |
| `sentryBeforeSend` | `scrubNavigationBreadcrumbs(event.breadcrumbs)` | direct call before `return event` | WIRED | the SDK merges scope breadcrumbs into the event before `beforeSend` (confirmed by the real-SDK run) |
| overrides.fast-uri | ajv@8 consumers | npm overrides | WIRED | all 3.1.8 |
| renovate rule | dashboard #338 override majors | depType overrides + major -> disabled | WIRED (config) | not observable until the next Renovate run |
| `vite.config.ts` `VitePWA({...})` | `dist/sw.js` | workbox generateSW | WIRED | PWA v2.0.0, 19 entries, 0 maia/engine |

### Data-Flow Trace (Level 4)

Not applicable: this is a dependency/config phase and adds no artifacts that render dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Lint | `npm run lint` | exit 0 | PASS |
| Type gate + prod build (PWA 2) | `npm run build` | exit 0, `PWA v2.0.0`, 19 precache entries, 0 maia/engine in sw.js | PASS |
| Full vitest | `npm test -- --run` (run once this round) | 303 files, 4988 passed, 0 failed (TrainStreakCard did not flake) | PASS |
| Unused exports/deps | `npm run knip` | exit 0 | PASS |
| Privacy/baseline/scrub test file | `npx vitest run src/__tests__/instrument.beforeSend.test.ts` | 32/32 | PASS |
| G-232-3 scrub is mutation-sensitive | scratch copy, `scrubNavigationBreadcrumbs` call removed | 1 failed / 31 passed (the new G-232-3 test) | PASS |
| Real SDK scrubs nav crumbs before transport | unmocked @sentry/react 11.4.0, jsdom, spied transport, pushState/replaceState | crumbs `?[Filtered]`, no token in event; mutated -> fails | PASS |
| WR-01 scrub is mutation-sensitive (round 1) | scratch copy, scrub removed | 2 failed / 29 passed | PASS |
| D-02 baseline mutation-sensitive (round 1) | scratch copy, `attachStacktrace: false` removed | 1 failed / 30 passed | PASS |
| Alias tree valid | `npm ls --all` | exit 0 | PASS |

### Probe Execution

SKIPPED: the phase declares no `probe-*.sh` and none exist for it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/instrument.ts` | n/a | no TBD/FIXME/XXX/TODO | none | clean |
| `frontend/src/instrument.ts` | 224-226 | the `Sentry.init` NOTE comment names only `event.request.url` as scrubbed in `sentryBeforeSend`, not the navigation breadcrumbs (the fix-site comment at 189-194 and the `scrubUrlQuery` doc are accurate) | Info | doc completeness only |
| `frontend/package.json` | n/a | `workbox-build`/`workbox-window` peers undeclared (IN-02, open) | Info | breaks only under `legacy-peer-deps` |
| `instrument.beforeSend.test.ts` | n/a | deny list only partly pinned; `SENTRY_PII_KEY_DENYLIST` mutable (IN-01, IN-03, open) | Info | hardening only |

No blockers.

### Human Verification Required

None outstanding. UAT is complete (232-UAT.md): test 1 (SDK transport) was owner-accepted, and the PWA test passed. The breadcrumb-leak issue (G-232-3) is resolved by 814a3c44c, and the orchestrator re-checked it in the owner's Chrome.

### Gaps Summary

No gaps. All four dependency goals hold:

- vite-plugin-pwa 2.0.0 with an inert precache that excludes maia/ and engine/.
- In-major fast-uri/js-yaml overrides, plus a Renovate rule that disables their majors.
- Sentry 11.4.0 with a v10-equivalent, mutation-proven privacy baseline. With WR-01 and G-232-3, it now sends strictly less than v10 did: query strings are filtered from both the page URL and the navigation breadcrumbs.
- TypeScript 7.0.2 as the build type gate, with the TS 6 alias capped at 6.0.x to match typescript-eslint.

Truth 10 counts via the owner's acceptance of the recorded orchestrator evidence.

---

_Verified: 2026-10-04T12:54:20Z_
_Verifier: Claude (gsd-verifier), re-verification round 2_
