---
phase: 232-frontend-major-dependency-upgrades
reviewed: 2026-10-04T14:20:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - CHANGELOG.md
  - frontend/package.json
  - frontend/src/__tests__/instrument.beforeSend.test.ts
  - frontend/src/instrument.ts
  - frontend/tsconfig.app.json
  - frontend/tsconfig.json
  - renovate.json
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 232: Code Review Report

**Reviewed:** 2026-10-04
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

I verified the Sentry v11 options against the installed `@sentry/core` and `@sentry/browser` 11.4.0 sources, not just the types.

- `userInfo: false` is correct. `BrowserClient` sets `infer_ip: "never"` and skips the auto-IP session hook.
- `cookies: false`, `httpBodies: []` and `attachStacktrace: false` are valid and take effect.
- The `{ deny: [...] }` semantics are right. The deny terms are additive to the SDK's built-in sensitive snippets. Matching is a case-insensitive substring match. `User-Agent` and `Referer`, the only headers `HttpContext` reads, survive the filter.
- `tsc -b` (TS 7.0.2) is clean, and `paths` still resolves without `baseUrl`. Paths now resolve relative to each tsconfig, and `tsconfig.json` has `files: []`.
- `npm run build` succeeds (PWA v2.0.0 `generateSW`). `knip` is clean. The 28 instrument tests pass.
- The npm alias layout works: `.bin/tsc` points at `@typescript/native` (7.0.2), and `typescript` resolves to `@typescript/typescript6`, which provides `tsc6`.
- The `matchDepTypes: ["overrides"]` rule in `renovate.json` matches Renovate's depType for the npm `overrides` block.
- No Critical issues were found. One privacy gap predates this phase and is not covered by the new block. The rest is hardening.

## Warnings

### WR-01: `dataCollection.urlQueryParams` does not scrub `event.request.url`, so the password-reset JWT still reaches Sentry

**File:** `frontend/src/instrument.ts:182-200` (with `frontend/src/pages/ResetPasswordPage.tsx:13`)
**Issue:**
- `@sentry/browser`'s `HttpContext` integration sets `event.request.url` from `location.href` with the full query string. Its own source comment says "The URL isn't gated by `dataCollection`".
- `/reset-password?token=<JWT>` is a real route. Any error captured on that page ships the live reset token to Sentry.
- This is not a v11 regression, because v10 behaved the same. But the new comment says the block "keeps exactly what v10 sent, which is what the Privacy page discloses". The `urlQueryParams: { deny }` entry and the test make it look like query strings are protected. They are protected only in fetch breadcrumbs and spans.
- A reset token is a credential, so the gap is worth closing while this config is being touched.

**Fix:** Scrub the URL in `sentryBeforeSend`, and add a test next to the existing ones:
```ts
function scrubQuery(url: string): string {
  const q = url.indexOf("?");
  return q === -1 ? url : `${url.slice(0, q)}?[Filtered]`;
}
// in sentryBeforeSend, before the axios branch:
if (event.request?.url) event.request.url = scrubQuery(event.request.url);
```
Do this after the axios block, or apply it to the `event.request` the axios branch builds. That branch spreads `error.config.url`, which is an API path and not the page URL, so it is unaffected. Also clarify the `urlQueryParams` comment so it does not imply the event URL is covered.

### WR-02: `typescript` alias range was loosened from `~6.0.3` to `^6.0.2`, but typescript-eslint caps at `<6.1.0`

**File:** `frontend/package.json:75`
**Issue:**
- The old pin `~6.0.3` stayed in 6.0.x. The new `npm:@typescript/typescript6@^6.0.2` allows any 6.x.
- `typescript-eslint`'s peer range is `typescript >=4.8.4 <6.1.0`.
- `renovate.json` groups minor and patch updates for npm, so a 6.1 release of the alias would arrive in the grouped PR. It would then fail with ERESOLVE, or force a `legacy-peer-deps` workaround.
- The lock resolves the alias to 6.0.2, which is below the previous `~6.0.3` floor. `tsc6 --version` reports 6.0.3 only because of the inner `@typescript/old@^6`.

**Fix:**
```json
"typescript": "npm:@typescript/typescript6@~6.0.2",
```

## Info

### IN-01: The privacy-baseline test checks only the mocked init arguments, and the deny-list contents are only partly pinned

**File:** `frontend/src/__tests__/instrument.beforeSend.test.ts:397-428`
**Issue:**
- The test fails correctly if `userInfo`, `cookies`, `httpBodies`, `attachStacktrace` or the header and query deny shapes regress. I traced each assertion.
- It asserts only `-ip` and `-user` through `arrayContaining`. Dropping `forwarded`, `remote-` or `via` from `SENTRY_PII_KEY_DENYLIST` passes.
- Because `@sentry/react` is fully mocked, nothing proves the shape is accepted and applied by the real SDK.

**Fix:**
- Assert the full list with `toEqual`, or export the constant and compare against it.
- Optionally add one test against `@sentry/core`'s `resolveDataCollectionOptions` and `_INTERNAL_filterKeyValueData`. It should show that `Referer` and `User-Agent` stay unfiltered and that an `X-Forwarded-For` value becomes `[Filtered]`.

### IN-02: vite-plugin-pwa 2.x makes `workbox-build` and `workbox-window` peer dependencies that `package.json` does not declare

**File:** `frontend/package.json:77`
**Issue:**
- They are installed only through npm's automatic peer install, and the lock holds 7.4.1.
- Any install with `legacy-peer-deps`, or a switch of package manager, would silently drop them. The build breaks, since `virtual:pwa-register` imports `workbox-window` and the plugin loads `workbox-build`.
- The build is green today, so this is robustness only.

**Fix:** Add `workbox-build` and `workbox-window` (`^7.4.1`) as explicit devDependencies. Add them to the knip `ignoreDependencies` if knip flags them as unused.

### IN-03: The deny terms are broad substrings, and `SENTRY_PII_KEY_DENYLIST` is a mutable `string[]`

**File:** `frontend/src/instrument.ts:172`
**Issue:**
- Matching is substring-based, so `via` also redacts any key containing it, for example `aviation`. This only over-redacts, so it is harmless.
- The terms were copied from the migration guide and cannot be checked against this app's headers. The only headers `HttpContext` emits are `User-Agent` and `Referer`, so the list is effectively decorative here. It is still fine as defence in depth.
- A shared mutable array is passed into three config slots.

**Fix:** Declare it `as const` or `readonly string[]`, and note in the comment that it is defence in depth. The SDK's built-in sensitive snippets already do the real work.

---

_Reviewed: 2026-10-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
