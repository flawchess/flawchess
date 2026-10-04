# Phase 232: Frontend Major Dependency Upgrades - Pattern Map

**Mapped:** 2026-10-04
**Files analyzed:** 9
**Analogs found:** 8 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/package.json` | config | batch (install) | commit `6ca0f8ecd` (SEED-162 vitest/jsdom cluster) | exact |
| `frontend/package-lock.json` | config (generated) | batch | same commit; never hand-edit, `npm install`/`uninstall` only | exact |
| `renovate.json` | config | n/a | existing `packageRules` entries (renovate.json:12-30) | exact |
| `frontend/src/instrument.ts` | config/bootstrap | event-driven (telemetry) | itself, `Sentry.init` block (lines 170-198) | exact |
| `frontend/src/__tests__/instrument.beforeSend.test.ts` | test | n/a | itself, `describe('Sentry.init config ...')` (lines 355-396) | exact |
| `frontend/tsconfig.app.json` | config | n/a | itself lines 33-40 (delete-only edit) | exact |
| `frontend/tsconfig.json` | config | n/a | itself lines 8-15 (delete-only edit) | exact |
| `frontend/audit-ci.jsonc` | config | n/a | itself; allowlist already `[]`, likely untouched | exact |
| `CHANGELOG.md` | docs | n/a | `## [Unreleased]` `### Changed` section (line 9+) | role-match |

## Pattern Assignments

### `frontend/package.json` + lock (one dependency per commit)

**Analog:** commit `6ca0f8ecd` "chore(deps): bump vitest/@vitest-* to 5.x and jsdom to 30.x". Message convention: `chore(deps): ...`, body names the SEED/phase cluster and explains any override deleted or raised. Other precedent: `815089f68 chore(deps): drop obsolete ... override`.

Current lines to change:
```json
"@sentry/react": "^10.55.0",      // line 26
"typescript": "~6.0.3",           // line 74
"vite-plugin-pwa": "^1.3.0",      // line 77
"overrides": {                     // line 81
  "fast-uri": "^3.1.5",           // line 82 -> "^3.1.8"
```
TS7 target (RESEARCH Pattern 1, install via `npm uninstall typescript` first, Pitfall 1):
```json
"@typescript/native": "npm:typescript@^7.0.2",
"typescript": "npm:@typescript/typescript6@^6.0.2",
```

### `renovate.json`

**Analog:** existing rules, renovate.json:13-29, e.g.
```json
{
  "matchPackageNames": ["onnxruntime-web"],
  "groupName": "onnxruntime-web (run scripts/bench_maia_ort_wasm.mjs before merging — Phase 219)"
}
```
Append a 5th rule after line 29 (RESEARCH Code Examples, validated): `matchManagers: ["npm"]`, `matchDepTypes: ["overrides"]`, `matchPackageNames: ["js-yaml","fast-uri"]`, `matchUpdateTypes: ["major"]`, `enabled: false`, with a `description` string (plain JSON, no comments). Does not conflict with rule 1 (minor/patch group, lines 13-17).

### `frontend/src/instrument.ts`

**Analog:** its own `Sentry.init` (lines 170-198). Convention: every non-obvious option carries a comment explaining why (often with a FLAWCHESS-xx issue id):
```ts
Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) || 0,
  beforeSend: sentryBeforeSend,
  // Suppress DOM errors caused by browser extensions ...
  ignoreErrors: [ ... ],
  denyUrls: [ ... ],
});
```
Insert the `dataCollection` + `attachStacktrace: false` block (RESEARCH Pattern 3) with a comment, same commit as the 11.x bump (option does not exist in v10).

### `frontend/src/__tests__/instrument.beforeSend.test.ts`

**Analog:** lines 16-19 (mock) and 355-365 (init-config test):
```ts
vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  browserTracingIntegration: vi.fn(),
}));
...
describe('Sentry.init config (FLAWCHESS-24 / SEED-148 items 3)', () => {
  it('ignoreErrors matches the real prod ServiceWorker-update-failure string', async () => {
    const Sentry = await import('@sentry/react');
    await import('@/instrument');
    const initCall = vi.mocked(Sentry.init).mock.calls[0]?.[0];
    ...
```
Add the new `it(...)` inside this describe (RESEARCH Code Examples). Module is reset per test via `vi.resetModules()` in the file's beforeEach. Mutation-prove by reverting the init block.

### `frontend/tsconfig.app.json` / `frontend/tsconfig.json`

Delete-only: remove `"baseUrl": "."`, the 3-line `TODO(TS7)` comment and `"ignoreDeprecations": "6.0"`; keep `paths` (`"@/*": ["./src/*"]`). Identical block in both files (app 33-40, root 8-15). Works on TS6 too, so it can be task 1 of the TS7 plan regardless of go/no-go.

### `frontend/audit-ci.jsonc`

Allowlist is already `[]` (line 17); comment history style (lines 10-16) records dropped entries with date + GHSA id. Expect no edit; only touch if an upgrade introduces/clears an entry. Run from `frontend/` (Pitfall 6).

### `CHANGELOG.md`

Bullet under `## [Unreleased]` (line 9). Mostly internal; at most one `### Changed` maintenance bullet, owner's call.

## Shared Patterns

- **Gate per plan:** `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip && npx audit-ci --config audit-ci.jsonc && npm audit signatures`.
- **Commit hygiene:** one dependency per commit, `chore(deps):` prefix, sequential waves (lockfile coupling).
- **Comment at the site** for behavior pins (dataCollection/attachStacktrace), matching instrument.ts comment style.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| npm alias pair for TS7 | config | n/a | No existing `npm:` aliased devDependency in the repo; follow RESEARCH Pattern 1 + Pitfall 1 |

## Metadata

**Analog search scope:** frontend/package.json, renovate.json, frontend/audit-ci.jsonc, frontend/src/instrument.ts, its test, tsconfigs, git log of deps commits
**Files scanned:** 9
**Pattern extraction date:** 2026-10-04
