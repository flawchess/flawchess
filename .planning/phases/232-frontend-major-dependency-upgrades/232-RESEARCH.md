# Phase 232: Frontend Major Dependency Upgrades (SEED-187) - Research

**Researched:** 2026-10-04
**Domain:** Frontend toolchain/dependency maintenance (TypeScript compiler, Sentry browser SDK, Workbox PWA plugin, npm overrides, Renovate config)
**Confidence:** HIGH. Every upgrade was installed and run through the real gates in scratch copies of `frontend/`. No repo files were modified.

<user_constraints>
## User Constraints (from ROADMAP.md, no CONTEXT.md)

The user chose to continue without discuss-phase. The ROADMAP Phase 232 section is the scope contract, copied verbatim:

### Locked scope (ROADMAP.md lines 321-347)

**Goal**: Take the major frontend upgrades the Renovate dashboard (#338) lists under "Awaiting
Schedule", one plan per dependency so a blocked upgrade doesn't hold up the others, and stop Renovate
from offering the two security-override majors.

- **TypeScript 6 → 7 (highest risk, research first):** expected to be the native (Go) compiler port.
  Verify `typescript-eslint` (`^8.60.0`), knip, `tsc -b` in `npm run build`, and any Vite/TS plugins
  that use the JS compiler API. "Blocked on X, stay on 6.x" with the blocker recorded is an acceptable
  outcome; don't force it through. `npm run build` is the real type gate (lint and test don't type-check).
- **@sentry/react 10 → 11:** follow the v10 → v11 migration guide for `Sentry.init` options,
  integrations and the helpers the `frontend/CLAUDE.md` Sentry rules use. Failure is silent, so verify a
  deliberate dev test error arrives in the `flawchess` project with tags/context intact and source maps
  resolving.
- **vite-plugin-pwa 1 → 2:** diff the generated SW and precache list before/after; check the update
  prompt / auto-update flow, offline load, and that `/maia/*` and `/engine/*` runtime assets stay
  excluded or cached as before (stale SWs on installed clients are hard to recover).
- **js-yaml 5 / fast-uri 4 (overrides only, likely no bump):** both exist only in `"overrides"` to force
  patched transitive versions (`js-yaml` via `cosmiconfig` ← `shadcn`; `fast-uri` via `ajv@8` ← `shadcn`
  and `workbox-build`). Keep each override within its current major (or drop it once consumers ship
  patched versions) and add a `renovate.json` `packageRules` entry disabling majors for these two.
  Re-check after the vite-plugin-pwa upgrade, since workbox may move to a newer `ajv`.
- **Every plan:** `npm run lint && npm run build && npm test -- --run && npm run knip`, plus
  `npx audit-ci --config frontend/audit-ci.jsonc` (drop allowlist entries the upgrade fixes); browser
  smoke on the dev build for Sentry and the PWA.

### Deferred Ideas (OUT OF SCOPE)
- Stockfish 19 and onnxruntime-web 1.30 (owner decisions, closed PR #351).
- The grouped Renovate minor/patch branch (it also carries onnxruntime / onnxruntime-node 1.29 → 1.30).

### Prior decision that this phase revisits
- Phase 217 **D-11** (v2.16): "TypeScript 7 stays out. No published `typescript-eslint` ... accepts `typescript` >= 6.1. Renovate's `typescript-7.x` branch stays unmerged until a typescript-eslint release admits 7.x." (`.planning/milestones/v2.16-phases/217-.../217-CONTEXT.md:79-81`). STATE.md still says "SEED-162 cluster 3 (TypeScript 7) blocked upstream until a `typescript-eslint` release accepts it." This research found an official Microsoft side-by-side path that removes that blocker without waiting for typescript-eslint. **Taking it reverses D-11, so it is an owner decision** (see Open Question 1).
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped (ROADMAP says "TBD"). The planner should use the five ROADMAP bullets as de-facto requirements. Suggested IDs (planner may adopt or rename):

| ID | Description | Research Support |
|----|-------------|------------------|
| DEP-TS7 | TypeScript 6 → 7, or "stay on 6.x" with the blocker recorded | §TypeScript 7. The side-by-side alias passes every gate (probe evidence). |
| DEP-SENTRY11 | @sentry/react 10 → 11, events still arrive with tags/context | §Sentry 11. Type-check is clean. The `dataCollection` reversal is the real risk. |
| DEP-PWA2 | vite-plugin-pwa 1 → 2 with an unchanged SW/precache | §PWA 2. The generated `sw.js`, `manifest.webmanifest` and `registerSW.js` are byte-identical. |
| DEP-OVR | js-yaml/fast-uri overrides stay within their major, Renovate stops offering majors | §Overrides. fast-uri 3.1.7 has a live moderate advisory; bump the override floor to `^3.1.8`. |
</phase_requirements>

## Summary

All four upgrades were tested for real, not just read about. For each one, `frontend/` (without `node_modules`) was copied into a scratch directory, the upgrade was installed with npm, and the gates were run: `tsc -b`, `eslint`, `knip`, `vite build`, the full `vitest run` (303 files / 4983 tests), `audit-ci`, and for the PWA a byte-diff of the generated service worker. A combined probe with all upgrades applied together was also green.

**TypeScript 7 is unblocked by an official Microsoft workaround, not by typescript-eslint.** `typescript@7.0.2` (GA 2026-07-08) ships a native Go `tsc` binary. Its package root export is only `./lib/version.cjs`, which exports `{version, versionMajorMinor}`, so the JS compiler API is gone. typescript-eslint 8.71.0 (latest) still declares `typescript >=4.8.4 <6.1.0`, and its tracking issue typescript-eslint#10940 is OPEN. Microsoft's release post prescribes a side-by-side install: `"typescript": "npm:@typescript/typescript6@^6.0.2"` (the TS6 API, for tools) plus `"@typescript/native": "npm:typescript@^7.0.2"` (supplies the `tsc` binary). With that alias, plus removing `baseUrl`/`ignoreDeprecations` from two tsconfigs, the codebase type-checks clean under TS7. `tsc -b` drops from about 9.0 s to 1.2 s and `npm run build` from about 7.7 s to 4.0 s. Lint, lint:cognitive (same 41 baseline findings), knip and all tests pass, and the static Go binary runs on `node:24-alpine` (the Dockerfile builder).

**Sentry 11 compiles without changes, but its privacy defaults flipped silently.** `@sentry/react@11.4.0` type-checks and builds against our code. The only `Sentry.*` APIs we use are `init`, `browserTracingIntegration`, `captureException`, `addBreadcrumb`, `ErrorBoundary`, `reactErrorHandler` and the `ErrorEvent`/`EventHint` types, and none of them changed shape. The real break is behavioral. v11 replaces `sendDefaultPii` (unset meant restrictive) with `dataCollection` (unset means collect everything: user info/IP, cookies, all HTTP bodies, headers). `attachStacktrace` also now defaults to true for non-Error captures. We ship no source maps, so a synthetic stack of minified frames would regroup those issues on every deploy. Both need explicit settings in `instrument.ts`.

**vite-plugin-pwa 2.0.0 has no code changes.** The v1.3.0...v2.0.0 compare touches only workflows, README, package.json and lockfile. The breaking change is `engines.node >=20.19.0` plus allowing `@vite-pwa/assets-generator ^2`. workbox-build stays 7.4.1, so the `fast-uri` consumer graph is unchanged.

The `fast-uri` override currently resolves to 3.1.7, which `npm audit` flags as GHSA-hrr3-gc8f-f4qj (moderate, fixed in 3.1.8). Raising the override floor to `^3.1.8` clears it.

**Primary recommendation:** run four sequential single-plan waves, lowest risk first: PWA 2 → overrides + Renovate rule → Sentry 11 (with an explicit `dataCollection` + `attachStacktrace: false`) → TypeScript 7 via the official `@typescript/typescript6` alias, gated on an owner checkpoint because it reverses D-11.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Type checking (`tsc -b`) | Build toolchain (CI + Docker builder) | Editor (TS6 via alias) | Runs only at build time. It is the only real frontend type gate. |
| ESLint parsing (typescript-eslint, sonarjs) | Build toolchain | — | Needs the TS6 JS API through `require('typescript')`. |
| Error reporting (Sentry) | Browser / Client | Sentry SaaS (de region) | `instrument.ts` initialises it before the app. Data scrubbing is client config plus server project settings. |
| Service worker / precache | Browser / Client (SW) | CDN/Caddy static | Generated at build time by Workbox and served as static `sw.js`. Caddy serves `/maia/*` and `/engine/*` over HTTP cache. |
| Dependency hygiene (overrides, Renovate) | Repo config | GitHub (Renovate/Dependabot) | `package.json` overrides plus `renovate.json`. No runtime tier. |

## Standard Stack

### Target versions (verified against the npm registry, 2026-10-04)

| Package | Current (package.json → lock) | Target | Published | Notes |
|---------|-------------------------------|--------|-----------|-------|
| `typescript` | `~6.0.3` → 6.0.3 | **7.0.2** (only 7.x GA; next is `7.1.0-dev.*`) | 2026-07-08 | [VERIFIED: npm registry `npm view typescript`] |
| `@typescript/typescript6` | — | 6.0.2 (shim: `module.exports = require("@typescript/old")`, where `@typescript/old` = `npm:typescript@^6` → 6.0.3) | 2026-07-06 | [VERIFIED: tarball inspected] [CITED: devblogs.microsoft.com/typescript/announcing-typescript-7-0/] |
| `@sentry/react` | `^10.55.0` → 10.73.0 | **11.4.0** (11.0.0 GA 2026-09-23; 11.1/11.2/11.3/11.4 within 10 days) | 2026-10-02 | [VERIFIED: npm registry] |
| `vite-plugin-pwa` | `^1.3.0` → 1.3.0 | **2.0.0** | 2026-10-03 (1 day old) | [VERIFIED: npm registry + `gh api` compare] |
| `js-yaml` (override) | `^4.3.1` → 4.3.2 | stay 4.x (`v4-legacy` tag = 4.3.2) | — | [VERIFIED: npm registry] |
| `fast-uri` (override) | `^3.1.5` → 3.1.7 | **`^3.1.8`** (dist-tag `three` = 3.1.8) | 2026-09-15 | [VERIFIED: npm registry, `npm audit`] |

Context: `typescript-eslint` latest is 8.71.0, with peer `typescript: ">=4.8.4 <6.1.0"` (canary is the same). `knip` latest is 6.39.0 (lock 6.34.0). `workbox-build` latest is 7.4.1 (unchanged). [VERIFIED: npm registry]

### Who imports `typescript` programmatically (full node_modules scan)

Declared deps/peers on `typescript` (scan of every installed `package.json`):
```
@typescript-eslint/{eslint-plugin,parser,project-service,tsconfig-utils,type-utils,typescript-estree,utils}@8.69.0  peer: >=4.8.4 <6.1.0
typescript-eslint@8.69.0           peer: >=4.8.4 <6.1.0
eslint-plugin-sonarjs@4.2.0        dependency (not peer): >=5 <6.1.0
ts-api-utils@2.5.0                 peer: >=4.8.4
cosmiconfig@9.0.2                  peer: >=4.9.5 (optional)   ← shadcn CLI only
```
A source grep for `require('typescript')` / `from 'typescript'` / `import('typescript')` hits only `@typescript-eslint/*` (89 files), `eslint-plugin-sonarjs` (37) and `typescript-eslint` (1). [VERIFIED: node_modules scan this session]

**Not consumers:** knip 6 (depends on `oxc-parser`/`oxc-resolver`/`get-tsconfig`, no typescript dep), `@vitejs/plugin-react` 6, `vite` 8, `vitest` 5 (no `typecheck` configured), `vite-prerender-plugin`, `vite-plugin-pwa`. [VERIFIED: `npm view knip@6.39.0 dependencies` + scan]

### Installation (exact commands; each in its own plan)

```bash
cd frontend
# Plan: PWA
npm install -D vite-plugin-pwa@^2.0.0
# Plan: overrides — edit "overrides"."fast-uri" to "^3.1.8", then:
npm install            # lock moves fast-uri 3.1.7 -> 3.1.8
# Plan: Sentry
npm install @sentry/react@^11.4.0
# Plan: TS7 (MUST uninstall first, see Pitfall 1)
npm uninstall typescript
npm install -D "typescript@npm:@typescript/typescript6@^6.0.2" "@typescript/native@npm:typescript@^7.0.2"
```

## Package Legitimacy Audit

`gsd_run query package-legitimacy check --ecosystem npm ...` results:

| Package | Registry | Age (target version) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|----------------------|-----------|-------------|---------|-------------|
| typescript | npm | 7.0.2: ~3 mo | 354.8M/wk | github.com/microsoft/TypeScript | OK | Approved |
| @typescript/typescript6 | npm | 6.0.2: ~3 mo | 8.7M/wk | github.com/microsoft/TypeScript | OK | Approved (Microsoft-documented alias target) |
| @sentry/react | npm | 11.4.0: 2 days | 32.8M/wk | github.com/getsentry/sentry-javascript | SUS (`too-new`) | Flagged. Real package, fresh version. |
| vite-plugin-pwa | npm | 2.0.0: 1 day | 5.8M/wk | github.com/vite-pwa/vite-plugin-pwa | SUS (`too-new`) | Flagged. Real package, fresh version. Has SLSA provenance attestation. |
| fast-uri | npm | latest 4.2.1 too new; target 3.1.8: 19 days | 171M/wk | github.com/fastify/fast-uri | SUS (`too-new`, about latest) | Flagged. We stay on 3.x. |
| js-yaml | npm | (no version change) | — | github.com/nodeca/js-yaml | SUS (`too-new`, about latest 5.x) | No install. Override unchanged. |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `@sentry/react` [WARNING: flagged as suspicious — verify before using.], `vite-plugin-pwa` [WARNING: flagged as suspicious — verify before using.], `fast-uri` [WARNING: flagged as suspicious — verify before using.]. All are flagged only because they were published recently (supply-chain cool-down signal), not because the packages are fake. Postinstall scripts: none for `@sentry/react@11.4.0` or `vite-plugin-pwa@2.0.0` (`npm view ... scripts.postinstall` is empty). [VERIFIED]

**Planner action:** put a `checkpoint:human-verify` (or an automated equivalent) before each SUS install. The concrete check is `npm audit signatures` after install. It passed on the combined probe ("310 packages have verified attestations") once the alias lock was correct (Pitfall 1). Optionally pin `vite-plugin-pwa` exactly to `2.0.0` rather than `^2.0.0`, given it is one day old.

## Architecture Patterns

### Upgrade flow (per plan)

```
 Renovate dashboard (#338) item
          │
          ▼
 npm install <pkg>@<range>  ──► package.json + package-lock.json change
          │
          ▼
 code/config adaptation (tsconfig / instrument.ts / renovate.json)
          │
          ▼
 gate: lint → build (tsc -b + vite) → vitest → knip → audit-ci → npm audit signatures
          │                       │
          │                       └─► PWA plan only: diff dist/sw.js, manifest, registerSW.js vs baseline
          ▼
 runtime smoke (dev server / vite preview in Chrome)
          │   └─► Sentry plan only: deliberate event → Sentry (env=development), tags/contexts present
          ▼
 atomic commit (one dependency per commit, bisectable)
```

### Recommended plan/wave structure

All four plans edit `frontend/package.json` and `frontend/package-lock.json`, so **they cannot run in parallel without lockfile conflicts.** Put each in its own sequential wave. This follows the SEED-162/Phase 217 precedent: "One plan per cluster, each in its own sequential wave ... bisectability is the whole point". No upgrade technically blocks another; the combined probe was green.

| Wave | Plan | Files | Risk | Why this order |
|------|------|-------|------|----------------|
| 1 | vite-plugin-pwa 2 | package.json, lock | Lowest (byte-identical SW) | Settles the workbox/ajv graph first, as the roadmap asks ("re-check after the vite-plugin-pwa upgrade"). |
| 2 | js-yaml/fast-uri overrides + Renovate rule | package.json, lock, renovate.json | Low | Runs after PWA so the `ajv`/`fast-uri` consumer re-check reflects the final workbox. |
| 3 | @sentry/react 11 | package.json, lock, src/instrument.ts, src/__tests__/instrument.beforeSend.test.ts | Medium (silent) | Needs a dev Sentry round-trip. |
| 4 | TypeScript 7 (owner checkpoint first) | package.json, lock, tsconfig.json, tsconfig.app.json | Medium | Highest-risk and the only one with a "stay on 6.x" exit. Last, so a "no-go" leaves 1-3 shipped. |

Optional split for wave 4: removing `baseUrl`/`ignoreDeprecations` **works on TS 6.0.3 too** (probe: `tsc -b` with TS6 on the edited config exits 0, 9.0 s). It can land as task 1 of the TS7 plan even if the owner picks "stay on 6.x". That retires the `TODO(TS7)` comments either way.

### Pattern 1: TypeScript 7 side-by-side alias (official)

**What:** Keep TS6 under the package name `typescript`, so every `require('typescript')` gets the 6.0 JS API. Install TS7 under the alias `@typescript/native`, whose `bin` provides `tsc`.
**When to use:** Until TS 7.1 ships its new API **and** typescript-eslint releases support for it.
**Example (target `frontend/package.json` devDependencies):**
```json
"@typescript/native": "npm:typescript@^7.0.2",
"typescript": "npm:@typescript/typescript6@^6.0.2",
```
Source: [CITED: devblogs.microsoft.com/typescript/announcing-typescript-7-0/] ("For both TS6 and TS7" snippet). Verified result after a clean `npm ci`: `node_modules/.bin/tsc -> ../@typescript/native/bin/tsc` (Version 7.0.2), `node_modules/.bin/tsc6 -> ../typescript/bin/tsc6`, and `require("typescript").version === "6.0.3"` with `typeof createProgram === "function"`. [VERIFIED: probe]

`npm run build` (`"build": "tsc -b && vite build"`, package.json:13) needs **no script change**: `tsc` resolves to the native binary.

### Pattern 2: tsconfig migration off `baseUrl`

Current state [VERIFIED: frontend/tsconfig.app.json:33-40, frontend/tsconfig.json:8-15]:
```jsonc
    "baseUrl": ".",
    // TODO(TS7): `ignoreDeprecations: "6.0"` only silences the baseUrl deprecation
    // through the TS6 line. baseUrl is slated for removal in TS7 — migrate the
    // `@/*` paths off baseUrl (or to a supported resolution) before upgrading.
    "ignoreDeprecations": "6.0",
    "paths": {
      "@/*": ["./src/*"]
```
The change is to delete the `baseUrl` line, the `ignoreDeprecations` line and the 3-line TODO comment in **both** files, and keep `paths` unchanged. Since TS 4.1, `paths` without `baseUrl` resolve relative to the tsconfig. The Vite alias (`vite.config.ts` `resolve.alias['@']`) is independent and unchanged. knip resolves `@/` without `baseUrl` (probe: same single config hint as baseline, exit 0).

Actual TS7 error on the unmodified config [VERIFIED: probe output]:
```
tsconfig.app.json(33,5): error TS5102: Option 'baseUrl' has been removed. Please remove it from your configuration.
  Use '"paths": {"*": ["./*"]}' instead.
```
Ignore the suggested `"*": ["./*"]` mapping. It would make bare specifiers resolve to project files, and we only need `@/*`.

### Pattern 3: Sentry 11 `dataCollection` baseline (restore v10 privacy)

Add this to `Sentry.init` in `frontend/src/instrument.ts` (currently lines 170-198; no `sendDefaultPii` is set today, so v10 ran restrictive):
```ts
  // Sentry v11 reversed the default: unset `dataCollection` collects user info (IP),
  // cookies, all HTTP bodies and headers. v10 (no sendDefaultPii) collected none of
  // that. Keep the v10 baseline; the Privacy page only discloses IP/browser/action.
  dataCollection: {
    userInfo: false,
    cookies: false,
    httpHeaders: {
      request: { deny: ["forwarded", "-ip", "remote-", "via", "-user"] },
      response: { deny: ["forwarded", "-ip", "remote-", "via", "-user"] },
    },
    httpBodies: [],
    urlQueryParams: { deny: ["forwarded", "-ip", "remote-", "via", "-user"] },
  },
  // v11 attaches a synthetic stack to non-Error captures. We ship no source maps,
  // so those frames are minified and change every deploy, regrouping issues.
  attachStacktrace: false,
```
Source: the deny lists are verbatim from the official migration guide [CITED: docs.sentry.io/platforms/javascript/guides/react/migration/v10-to-v11/]. The field names and shapes match the installed `@sentry/core@11.4.0` `DataCollection` interface (`build/types/types/datacollection.d.ts`: `userInfo?: boolean; cookies?: CollectBehavior; httpHeaders?: CollectBehavior | HttpHeadersCollection; httpBodies?: HttpBodyCollectionTarget[]; urlQueryParams?: CollectBehavior; ...`). The SDK defaults (`resolveDataCollectionOptions.js`) are `userInfo: true, cookies: true, httpHeaders: { request: true, response: true }, httpBodies: ["incomingRequest", "outgoingRequest", "incomingResponse", "outgoingResponse"], urlQueryParams: true`. [VERIFIED: installed package read this session]. Probe: this block type-checks under Sentry 11 (exit 0), and a deliberately wrong value (`userInfo: "no"`) fails with TS2322, so the type is enforced. The guide's `genAI`/`databaseQueryData`/`graphQL` keys are server-only, so leave them out.

**`dataCollection` does not exist in v10.** It must land in the same commit as the version bump.

### Anti-Patterns to Avoid
- **Installing `typescript@7` under the `typescript` name** (what Renovate's `typescript-7.x` branch does). `require('typescript')` then returns only `{version, versionMajorMinor}` (exports `".": "./lib/version.cjs"`), so typescript-eslint, eslint-plugin-sonarjs (it has a hard `typescript` dependency `>=5 <6.1.0`) and `npm run lint` break, and npm raises an ERESOLVE peer conflict. **Close that Renovate PR/branch. Do not merge it.**
- **Bumping an override across a major** (`fast-uri` 4 / `js-yaml` 5). `ajv@8.20.0` declares `fast-uri: ^3.0.1` and `cosmiconfig@9.0.2` declares `js-yaml: ^4.1.0`. Forcing the next major breaks their declared contract. [VERIFIED: npm view]
- **Hand-editing `package-lock.json`.** Use `npm install`/`npm uninstall` so integrity hashes and `name` fields for aliases are correct.
- **Sentry smoke from a subagent.** Subagents lack project MCPs (memory: "Subagents lack project MCP"), so the Sentry-side confirmation must run in the orchestrator or inline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Running TS7 next to TS6-API tools | A custom wrapper script or a second `package.json` | The npm alias pair (`@typescript/typescript6` + `@typescript/native`) | Microsoft-documented. It keeps the bin `tsc`, so no script edits are needed. |
| Restricting Sentry PII | A `beforeSend` scrubber that strips cookies/IP/bodies | `dataCollection` init option | The SDK filters at collection time and covers spans/breadcrumbs `beforeSend` never sees. |
| Stopping Renovate majors for override-only deps | Deleting overrides to hide them, or ignoring the dashboard | A `packageRules` entry `matchDepTypes: ["overrides"]` + `matchUpdateTypes: ["major"]` + `enabled: false` | Declarative and validated by `renovate-config-validator`. Minor/patch floors still flow through the grouped branch. |
| SW regression check | A manual click-through only | A byte-diff of `dist/sw.js` + `manifest.webmanifest` + `registerSW.js`, and a precache URL list | Deterministic. It showed the v2 output is identical. |

## Runtime State Inventory

Not a rename phase, but one runtime-state item matters:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. No DB or storage keys reference these packages. | None |
| Live service config | **Renovate** branches `renovate/typescript-7.x`, `renovate/vite-plugin-pwa-2.x`, `renovate/major-sentry-javascript-monorepo`, `renovate/fast-uri-4.x`, `renovate/js-yaml-5.x` (from #338). The first three close by themselves once main carries the upgrade. The last two close once the new packageRule disables them. **Sentry project** issue grouping (attachStacktrace) and data scrubbing settings are server-side. | Watch #338 after merge. Close any Renovate PR that was opened manually. |
| OS-registered state | None | None |
| Secrets/env vars | `VITE_SENTRY_DSN`, `VITE_SENTRY_TRACES_SAMPLE_RATE` (build args, docker-compose.yml:147-148). Names unchanged. | None (code reads them unchanged) |
| Build artifacts | `frontend/node_modules/.tmp/tsconfig.{app,node}.tsbuildinfo` written by TS6. Installed PWAs hold the current `sw.js`. | Delete `node_modules/.tmp` once after the TS7 switch (Pitfall 5). No SW action: the v2 SW is byte-identical. |

## Common Pitfalls

### Pitfall 1: Stale lock entry makes the TS alias silently half-applied
**What goes wrong:** Editing `"typescript": "npm:@typescript/typescript6@^6.0.2"` into package.json and running `npm install` leaves the old lock entry `node_modules/typescript` → `typescript-6.0.3.tgz` with no `name` field. `npm ci` accepts it and every gate passes, but `npm audit signatures` then fails with `ETARGET No matching version found for @typescript/typescript6@6.0.3`, and the `tsc6` bin is missing.
**Why it happens:** npm treats the existing entry as satisfying the alias spec.
**How to avoid:** Run `npm uninstall typescript`, then `npm install -D "typescript@npm:@typescript/typescript6@^6.0.2" "@typescript/native@npm:typescript@^7.0.2"`. After that the lock shows `node_modules/typescript {"name":"@typescript/typescript6","version":"6.0.2"}`, `node_modules/@typescript/old {"name":"typescript","version":"6.0.3"}` and `node_modules/@typescript/native {"name":"typescript","version":"7.0.2"}`. [VERIFIED: both paths probed]
**Warning signs:** `ls node_modules/.bin/tsc6` missing, or `npm audit signatures` erroring.

### Pitfall 2: Sentry 11 `dataCollection` default reversal (silent privacy change)
**What goes wrong:** With no `dataCollection`, v11 collects IP/user info, all cookies, all request/response bodies and headers. FlawChess login/register POST bodies contain passwords. Scrubbing of keys like `password` is "best-effort" per the guide. The type-check cannot catch this.
**How to avoid:** Use Pattern 3, and add a unit test (see Validation) asserting `initCall.dataCollection.userInfo === false`, `cookies === false`, `httpBodies` is an empty array and `attachStacktrace === false`. The existing `instrument.beforeSend.test.ts` already mocks `init` and inspects `vi.mocked(Sentry.init).mock.calls[0]?.[0]`. Prove the test by reverting the block and seeing it fail (memory: mutation-test gap closures).
**Warning signs:** The envelope in the DevTools Network tab carries `user.ip_address` or `request.cookies`.

### Pitfall 3: "Source maps resolving" is not achievable today
**What goes wrong:** The ROADMAP asks to verify source maps resolve in Sentry. There are no source maps to resolve. `vite-prerender-plugin` turns `build.sourcemap = true` on internally and deletes the maps afterwards when the user didn't enable them (`node_modules/vite-prerender-plugin/src/plugins/prerender-plugin.js:141,170-172`). `dist/assets/` has 0 `.map` files, and nothing in `bin/`, `deploy/`, `.github/`, `Dockerfile` or `vite.config.ts` uploads maps (no `@sentry/vite-plugin`, no `sentry-cli`). [VERIFIED: grep + dist listing]
**How to avoid:** Change that verification criterion to "stack trace present (minified), message/tags/contexts intact". Record the missing source-map upload as a pre-existing gap and recommend a seed (do not add it to this phase).

### Pitfall 4: attachStacktrace regrouping without source maps
**What goes wrong:** v11 attaches a synthetic call-site stack to non-Error `captureException` values. With minified, hash-named bundles, grouping by those frames can split one issue per deploy.
**How to avoid:** `attachStacktrace: false`, which matches v10 behavior [CITED: migration guide: "Set `attachStacktrace: false` to restore previous behavior"]. Revisit once source maps exist.

### Pitfall 5: TS6 build-info files left in `node_modules/.tmp`
**What goes wrong:** `tsBuildInfoFile` points to `./node_modules/.tmp/*.tsbuildinfo` (tsconfig.app.json, tsconfig.node.json). In probes TS7 still detected new and changed files after a TS6 build. For certainty, though, the first TS7 run should be clean.
**How to avoid:** `rm -rf frontend/node_modules/.tmp` once after switching, or run `npx tsc -b --force` in the plan's verify step. CI and Docker always start clean.

### Pitfall 6: Wrong working directory for audit-ci
**What goes wrong:** The ROADMAP/seed command `npx audit-ci --config frontend/audit-ci.jsonc` (from the repo root) audits the wrong tree. The repo root has no frontend lockfile.
**How to avoid:** Use the CI form: `cd frontend && npx audit-ci --config audit-ci.jsonc` (ci.yml:152-157, `working-directory: frontend`).

### Pitfall 7: Editor and build checker diverge after the TS7 alias
**What goes wrong:** VS Code's "workspace TypeScript" resolves `node_modules/typescript`, which is TS6. The build checks with TS7, so an error could show in one and not the other (TS7 `stableTypeOrdering` can change the order of union members in messages).
**How to avoid:** Accept it, since the build is the gate, and note it in the plan summary. The TS7 editor experience is the "TypeScript (Native Preview)" VS Code extension [ASSUMED].

### Pitfall 8: Sentry dev smoke hits a second module instance
**What goes wrong:** In a Vite dev console, `await import('@sentry/react')` fails (bare specifier), and importing the deps file with a different `?v=` query creates a second, uninitialised SDK copy whose `getClient()` is `undefined`, so nothing is sent.
**How to avoid:** Import the exact URL the app loaded:
```js
const u = performance.getEntriesByType('resource').map(e => e.name)
  .find(n => n.includes('/node_modules/.vite/deps/@sentry_react.js'));
const S = await import(u);
console.assert(S.getClient() !== undefined, 'not the app instance');
S.captureException(new Error('phase232-sentry-v11-smoke'), {
  tags: { source: 'phase232-smoke' },
  contexts: { phase232: { plan: 'sentry-v11' } },
});
```
That module resource entries appear in Resource Timing is [ASSUMED]. The fallback is to copy the `@sentry_react.js?v=...` URL from the Network panel. **Do not** use `captureMaiaWorkerError()` for the smoke: issues are shared across environments, so a dev event would join the real prod "Maia worker inference error" issue.

## Code Examples

### Renovate rule (validated)
Add to `renovate.json` `packageRules` (after the existing four rules):
```json
{
  "description": "js-yaml and fast-uri exist only as npm overrides pinning patched transitive versions; a major would force v5/v4 onto consumers declaring ^4/^3 (cosmiconfig, ajv@8). Minor/patch still flow via the grouped branch.",
  "matchManagers": ["npm"],
  "matchDepTypes": ["overrides"],
  "matchPackageNames": ["js-yaml", "fast-uri"],
  "matchUpdateTypes": ["major"],
  "enabled": false
}
```
Renovate assigns depType `overrides` to package.json `overrides` entries [CITED: docs.renovatebot.com/modules/manager/npm/]. Validated with `npx --package renovate@44.132.5 renovate-config-validator --strict`, which printed "Config validated successfully". Negative control: `"enabled": "nope"` fails with "should be boolean". [VERIFIED: probe]. It does not conflict with rule 1 (`matchUpdateTypes: ["minor","patch"]`, renovate.json:13-17).

### Override edit
```json
"overrides": {
  "fast-uri": "^3.1.8",
  ...
  "js-yaml": "^4.3.1"
}
```
`fast-uri ^3.1.8` clears GHSA-hrr3-gc8f-f4qj ("inconsistent host case normalization via percent-encoded octets", `>=3.0.0 <3.1.8`, moderate). Combined probe: full `npm audit` went from `moderate:1, high:6` to `moderate:0, high:6`. [VERIFIED: npm audit]. `js-yaml` already resolves to 4.3.2, the latest 4.x. Leave it alone, or bump the floor to `^4.3.2` for clarity.

**Why keep the overrides instead of dropping them** (the ROADMAP allows either): the consumer ranges (`ajv` `^3.0.1`, `cosmiconfig` `^4.1.0`) admit the patched versions, so dropping is technically safe. Probe: dropping both and running `npm install` kept 3.1.7/4.3.2 from the lock. But fast-uri has needed three advisory bumps since May (3.1.2 → 3.1.5 → 3.1.8; commits 37a7cb88b, cbc1cf86a). The override is the floor that Renovate's grouped minor/patch branch raises when a patch drops. It is cheap insurance. Keep it and add the rule.

### Sentry init test addition (pattern from existing file)
```ts
it('keeps the v10 privacy baseline under Sentry v11 (dataCollection + attachStacktrace)', async () => {
  const Sentry = await import('@sentry/react');
  await import('@/instrument');
  const initCall = vi.mocked(Sentry.init).mock.calls[0]?.[0];
  expect(initCall?.dataCollection?.userInfo).toBe(false);
  expect(initCall?.dataCollection?.cookies).toBe(false);
  expect(initCall?.dataCollection?.httpBodies).toEqual([]);
  expect(initCall?.attachStacktrace).toBe(false);
});
```
(Mirrors `src/__tests__/instrument.beforeSend.test.ts` lines ~355-395, whose mock is `vi.mock('@sentry/react', () => ({ init: vi.fn(), browserTracingIntegration: vi.fn() }))`.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `typescript` = JS compiler + API | `typescript@7` = native Go `tsc`, **no API** (7.1 promises a new, different API) | 7.0 GA 2026-07-08 | Tools needing the API use the `@typescript/typescript6` alias. |
| `baseUrl` + `paths` | `paths` only (relative to tsconfig) | Deprecated in 6.0, removed in 7.0 (TS5102) | Two tsconfig edits. |
| TS7 new defaults: `types: []`, `rootDir: ./`, `strict: true`, `module: esnext`, `noUncheckedSideEffectImports: true`, `stableTypeOrdering` always on | — | 7.0 | No impact here: both tsconfigs set `types` explicitly, use `noEmit`, already have `strict`/`noUncheckedSideEffectImports`. Probe was clean. [CITED: TS 7 announcement] |
| Sentry `sendDefaultPii` (default restrictive) | `dataCollection` (default permissive) | Sentry 11.0.0, 2026-09-23 | Explicit baseline required. |
| Sentry transactions + `beforeSendTransaction` | Span streaming. `beforeSendTransaction`/`ignoreTransactions` removed. | Sentry 11 | Not used by us. If `VITE_SENTRY_TRACES_SAMPLE_RATE` > 0 in prod, span volume/quota may change (Open Question 3). |
| browserTracing without web vitals | Web Vitals auto-added to `browserTracingIntegration` | Sentry 11 | Only matters when traces are sampled. |
| Browser sessions `lifecycle: 'route'` | `'page'` default | Sentry 11 | Release-health session counts change. We set no `release`, so impact is low. |

**Deprecated/outdated:**
- Renovate's `renovate/typescript-7.x` branch: installs TS7 as `typescript`, which breaks lint. Never merge it.
- `TODO(TS7)` comments in both tsconfigs: resolved by this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ES-module resource entries for Vite deps appear in `performance.getEntriesByType('resource')` | Pitfall 8 | Low. Fall back to copying the URL from the Network panel. |
| A2 | The VS Code TS7 editor experience is the "TypeScript (Native Preview)" extension | Pitfall 7 | Cosmetic. Build remains the gate. |
| A3 | The local root `.env` defines `VITE_SENTRY_DSN`, so the dev build actually sends to Sentry | Validation (Sentry smoke) | Medium. If unset, `Sentry.init` has no DSN and the smoke sends nothing. Check `S.getClient()?.getDsn()` in the console first (the `.env` file itself is read-guarded). |
| A4 | Sentry server-side "prevent storing IP" and data scrubbing project settings are unknown | Security | Low. Client `userInfo: false` is the primary control anyway. |
| A5 | prod `VITE_SENTRY_TRACES_SAMPLE_RATE` is 0 (only `.env.example` shows `0`) | State of the Art | Low/Medium. If >0, span streaming changes quota. Check `.prod.env` (owner) before deploy. |

## Open Questions

1. **TS7 now via the alias, or stay on 6.x (reversing or keeping D-11)?**
   - What we know: the alias is Microsoft's documented path. Every gate passes, including on Alpine Docker. Build type-check runs 7.5x faster. Lint uses non-type-aware `tseslint.configs.recommended` (eslint.config.js), so lint never consumes type info and there is no checker-divergence risk inside lint.
   - What's unclear: whether the owner wants a non-standard two-package arrangement that must be unwound later (when TS 7.1 + a typescript-eslint release land, typescript-eslint#10940 OPEN as of 2026-09-29).
   - Recommendation: **adopt the alias** (go), with a plan-start `checkpoint:decision`. The no-go branch: land only the tsconfig `baseUrl` cleanup (works on TS6), close Renovate's `typescript-7.x` PR, and record the blocker ("typescript-eslint@8.71.0 peer `<6.1.0`; TS 7.0 has no JS API; tracking typescript-eslint#10940") in STATE.md.
2. **Sentry `attachStacktrace: false` vs the new default?** Recommendation: `false` now, because of minified frames and no source maps. Revisit with a source-map seed.
3. **Prod traces sample rate** (A5): verify before the deploy that ships Sentry 11.
4. **Bump fast-uri inside this phase although Renovate's grouped branch also carries it?** Recommendation: yes, it is the override this phase owns and it clears a live advisory. Renovate rebases the grouped branch automatically.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | all | ✓ | v24.19.0 (`.nvmrc` = 24; engines `>=24.15.0`; PWA 2 needs >=20.19.0) | — |
| npm | all | ✓ | 11.17.0 | — |
| Docker | optional Alpine `tsc` probe | ✓ | 29.8.2 | — |
| gh CLI | Renovate dashboard / CI watch | ✓ | authenticated | — |
| Chrome (claude-in-chrome) | Sentry/PWA browser smoke | ✓ (skill listed) | — | `vite preview` + curl for SW headers |
| Sentry access | Confirm smoke event arrived | Orchestrator only (subagents lack MCP) | — | Owner checks the dashboard |
| Root `.env` `VITE_SENTRY_DSN` | Sentry dev smoke | Unknown (read-guarded) | — | Owner confirms, or run the smoke against a `vite build --mode development` preview with the DSN exported |

Note: npm 11.17 prints `allow-scripts` warnings for `stockfish` and `protobufjs` postinstalls on fresh installs. These are pre-existing, not caused by this phase.

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 5 (jsdom 30), ESLint 10, knip 6, tsc (6.0.3 now / 7.0.2 after wave 4), audit-ci 7 |
| Config file | `frontend/vite.config.ts` (`test` block), `frontend/eslint.config.js`, `frontend/knip.json`, `frontend/audit-ci.jsonc` |
| Quick run command | `cd frontend && npx vitest run src/__tests__/instrument.beforeSend.test.ts` (Sentry plan) |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test && npm run knip && npx audit-ci --config audit-ci.jsonc && npm audit signatures` |
| Baseline timings (probe) | full vitest ~66 s; build ~7.7 s (TS6) / ~4.0 s (TS7) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEP-PWA2 | Generated SW/manifest/register script unchanged | build-artifact diff | Before bump: `npx vite build && cp dist/{sw.js,manifest.webmanifest,registerSW.js} $TMP/v1/`. After: rebuild, then `diff` each file (expect identical) and `grep -oE 'url:"[^"]+"' dist/sw.js` (expect 19 entries, none under `maia/` or `engine/`, no `.html`/`.wasm`/`.onnx`) | ✅ no new file |
| DEP-PWA2 | PWA registers, autoUpdate reload works, offline shell loads | browser smoke | `npm run build && npm run preview`, then in Chrome: SW `activated`, DevTools offline + reload shows cached shell | manual/agent-browser |
| DEP-OVR | fast-uri ≥3.1.8, js-yaml 4.x, no majors | unit-ish | `npm ls fast-uri js-yaml` (all 3.1.8 / 4.3.2) + `npm audit --json` (no fast-uri entry) | ✅ |
| DEP-OVR | Renovate rule valid | config validation | `npx -y --package renovate renovate-config-validator --strict` (from repo root) | ✅ |
| DEP-SENTRY11 | v10 privacy baseline + attachStacktrace kept | unit | `npx vitest run src/__tests__/instrument.beforeSend.test.ts` (new test, mutation-proven by reverting) | ❌ Wave 0: add test case |
| DEP-SENTRY11 | Existing beforeSend/fingerprint/ignoreErrors behavior | unit | same file (existing cases) | ✅ |
| DEP-SENTRY11 | Event reaches Sentry with tags/contexts | dev smoke | Pitfall 8 snippet in the dev console, then confirm in Sentry (env `development`, message `phase232-sentry-v11-smoke`, tag `source=phase232-smoke`, context `phase232`). Inspect the envelope for absence of `ip_address`/cookies. | manual/orchestrator |
| DEP-TS7 | TS7 type-checks the app | build | `rm -rf node_modules/.tmp && npm run build` + `node_modules/.bin/tsc --version` = 7.0.2 | ✅ |
| DEP-TS7 | Type gate still catches errors (not a no-op) | negative control | Temporarily add `const x: number = "nope"` → `npx tsc -b` must exit 1 with TS2322, then remove | ✅ (ad hoc) |
| DEP-TS7 | Lint tools get the TS6 API | lint | `npm run lint` + `npm run lint:cognitive` (41 findings = baseline) + `node -e 'console.log(typeof require("typescript").createProgram)'` = `function` | ✅ |
| DEP-TS7 | Docker (Alpine) build works | container | `docker build -f frontend/Dockerfile .` from repo root, or the CI Trivy step's `docker build` | ✅ |

### Sampling Rate
- **Per task commit:** the plan's relevant subset (e.g. `npm run build` for TS7; the instrument test for Sentry).
- **Per wave merge:** the full frontend suite above plus `npm audit signatures`.
- **Phase gate:** the full CLAUDE.md pre-merge gate (backend steps included) before the single squash-merge to `main`. Then `gh run watch <id> --exit-status` on the next CI run (not `gh pr checks --watch`).

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/instrument.beforeSend.test.ts`: add the dataCollection/attachStacktrace test case (Sentry plan, task 1, written before the init change, then mutation-proven).
- No framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | — |
| V6 Cryptography | no | — |
| V8 Data Protection | **yes** (Sentry telemetry) | Sentry `dataCollection` baseline (`userInfo:false`, `cookies:false`, `httpBodies:[]`, header/query deny lists). The Privacy page (`src/pages/Privacy.tsx:49-51`) discloses only "IP address, browser information, and the action that triggered the error", so v11 defaults would exceed the disclosed scope. |
| V14 Configuration / dependencies | **yes** | Override floors (`fast-uri ^3.1.8`), `audit-ci` prod gate (allowlist stays `[]`), `npm audit signatures`, cool-down checkpoint for too-new packages. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential/PII leakage into error telemetry (login POST bodies, Bearer `Authorization` header, cookies) | Information Disclosure | `dataCollection` explicit baseline. The SDK also always filters token-like keys, but treat that as best-effort. |
| Compromised fresh npm release (supply chain) | Tampering | `npm audit signatures` (registry signatures + provenance). Pin `vite-plugin-pwa@2.0.0` exactly. Human checkpoint for `too-new` packages. |
| Stale or poisoned service worker on installed clients | Tampering / DoS | Byte-identical SW diff; `autoUpdate` + `controllerchange` reload (`src/main.tsx:41-63`) unchanged. |
| Transitive URI parser host confusion (fast-uri) | Spoofing | Override floor `^3.1.8` (dev-only reachability: shadcn CLI, workbox-build at build time). |

Pre-existing, out of scope (note only): full `npm audit` still shows 6 high advisories (`braces`/`micromatch`/`fast-glob`/`ts-morph`/`@ts-morph/common`/`shadcn`), all via the `shadcn` CLI devDependency. They are dev-only, so the `skip-dev` audit-ci gate passes. Do not fix them in this phase; flag them as a candidate seed.

## Project Constraints (from CLAUDE.md)

- Full pre-merge gate before the squash-merge to `main`: `ruff format`, `ruff check --fix`, `ty check` ×2, `check_function_size.py`, `pytest -n auto -x`, then `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`. It runs once, right before the squash-merge, not per commit.
- `npm run lint`/`npm test` do not type-check. `npm run build` is the type gate (frontend/CLAUDE.md).
- Knip runs in CI. New devDeps (`@typescript/native`) must not trip it (verified: they don't).
- Frontend has no Prettier. Never run `prettier --write` (memory).
- Comment bug fixes / behavior pins at the site (applies to the `dataCollection`/`attachStacktrace` block).
- Sentry rules (frontend/CLAUDE.md): `captureException(error, { tags: { source } })` in manual catch blocks, no duplicate captures for TanStack Query. The v11 API is unchanged here.
- CHANGELOG: append under `## [Unreleased]` when the phase merges. Mostly internal; one user-facing line is plausible (e.g. "Faster builds" is not user-facing, so likely a `### Changed` maintenance bullet or none, owner's call per docs/git-workflow.md).
- Never add unplanned scope (source-map upload, the shadcn advisories): flag as seeds instead.
- Use em-dashes sparingly in commit messages and prose.
- Do not run `bin/reset_db.sh`. Not relevant here.
- Memory: don't spawn executors for tiny jobs. The PWA and overrides plans are each roughly 10-minute mechanical changes and are good candidates for inline execution.

## Sources

### Primary (HIGH confidence, tool-verified this session)
- npm registry (`npm view`) for typescript, @typescript/typescript6, @sentry/react, vite-plugin-pwa, js-yaml, fast-uri, typescript-eslint, knip, workbox-build, ajv, cosmiconfig, eslint-plugin-sonarjs: versions, dist-tags, peers, publish times, attestations.
- Tarball inspection of `typescript@7.0.2` (exports, `lib/version.cjs`, `bin/tsc`, static Go ELF) and `@typescript/typescript6@6.0.2` (`lib/typescript.js` shim, `tsc6` bin).
- Installed `@sentry/core@11.4.0` type and source files (`datacollection.d.ts`, `options.d.ts`, `resolveDataCollectionOptions.js`).
- Scratch probes: TS7 alias / Sentry 11 / PWA 2 / overrides / combined, with lint, build, vitest, knip, audit-ci, npm audit, npm audit signatures, Alpine docker `tsc -b`, renovate-config-validator.
- `gh api repos/vite-pwa/vite-plugin-pwa/compare/v1.3.0...v2.0.0` and `gh release view v2.0.0`.
- `gh issue view 338` (Renovate dashboard) and `gh issue view 10940 -R typescript-eslint/typescript-eslint` (OPEN, updated 2026-09-29).

### Secondary (MEDIUM, official docs fetched)
- [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/): no API in 7.0, side-by-side alias snippets, removed options (`baseUrl`, `moduleResolution: node10`, ...), new defaults.
- [Sentry JS v10 → v11 migration (React)](https://docs.sentry.io/platforms/javascript/guides/react/migration/v10-to-v11/): `dataCollection`, `attachStacktrace`, span streaming, browserTracing option moves, session lifecycle, removed APIs, TS ≥5.0.4.
- [Renovate npm manager docs](https://docs.renovatebot.com/modules/manager/npm/): depType `overrides`.

### Tertiary (LOW, web search only, corroborating)
- [InfoQ: TypeScript 7 released](https://www.infoq.com/news/2026/08/typescript-7-released/), [loke.dev side-by-side guide](https://loke.dev/writing/typescript-7-typescript-eslint-side-by-side), and several downstream "blocked on typescript-eslint" issues (e.g. [cybergrouch/skopeo#1039](https://github.com/cybergrouch/skopeo/issues/1039)).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Registry-verified and installed.
- Architecture / plan ordering: HIGH. Lockfile coupling observed, combined probe green.
- TypeScript 7 path: HIGH technically (every gate passes). The go/no-go is an owner decision.
- Sentry 11: HIGH for compile/build/tests. MEDIUM for the runtime smoke (needs a dev DSN and orchestrator-side Sentry access).
- PWA 2: HIGH. Byte-identical output plus a no-src-change upstream diff.
- Pitfalls: HIGH (1, 3, 5, 6 reproduced). MEDIUM (4, 7, 8 reasoned from docs).

**Research date:** 2026-10-04
**Valid until:** about 2026-10-18. Sentry 11 ships a minor every few days, and TS 7.1 beta / typescript-eslint TS7 support could land in October and would remove the need for the alias. Re-check `npm view typescript-eslint peerDependencies` at plan time.
