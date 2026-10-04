---
id: SEED-187
status: promoted
promoted_to: Phase 232
promoted: 2026-10-04
planted: 2026-10-04
planted_during: no open milestone; Renovate PR triage after Phase 231 (weekly leaderboard medals) released
trigger_when: next maintenance / chore phase, or before the Renovate majors pile up further
scope: medium (one plan per dependency so a blocked upgrade doesn't hold up the others)
---

# SEED-187: Frontend major dependency upgrades

Renovate dashboard (#338) lists major upgrades under "Awaiting Schedule". The owner wants all
of them except Stockfish 19 (stays unscheduled, see the "No Stockfish 19 / no onnxruntime-web
bump" memory):

| Package | Current (`frontend/package.json`) | Target | Kind |
|---|---|---|---|
| `typescript` | `~6.0.3` | 7.x | direct devDependency |
| `@sentry/react` | `^10.55.0` | 11.x | direct dependency |
| `vite-plugin-pwa` | `^1.3.0` | 2.x | direct devDependency |
| `js-yaml` | override `^4.3.1` | 5.x | **security override only** (transitive) |
| `fast-uri` | override `^3.1.5` | 4.x | **security override only** (transitive) |

## Why This Matters

- Majors left alone get harder to take later, and Renovate keeps re-listing them.
- Each of the first three touches something users notice when it breaks: the type-check
  gate, error reporting, and the service worker on installed clients.

## Per-dependency notes and risks

### TypeScript 7 (highest risk)
- Expected to be the native (Go) compiler port. Unverified for our setup: does
  `typescript-eslint` (`^8.60.0`) support it, does knip, does `tsc -b` in `npm run build`
  behave the same, and do any Vite/TS plugins rely on the JS compiler API.
- Research first. An acceptable outcome is "blocked on X, stay on 6.x" with the blocker
  recorded; don't force it through.
- Memory: `npm run lint` and `npm test` do NOT type-check, so `npm run build` is the real gate.

### @sentry/react 11
- Read the v10 → v11 migration guide; check `Sentry.init` options, integrations, and the
  helpers used by the rules in `frontend/CLAUDE.md` (frontend Sentry section).
- Failure mode is silent: errors stop reaching Sentry. Verify with a deliberate test error
  in dev that arrives in the `flawchess` Sentry project with tags/context intact, and that
  source maps still resolve.

### vite-plugin-pwa 2
- Touches service worker generation, precache manifest and update flow. A regression hits
  installed prod clients and stale SWs are hard to recover (compare the Cloudflare edge
  cache and stale runtime cache memories for `/maia/*` and `/engine/*`).
- Diff the generated SW and precache list before/after; check the update prompt / auto-update
  behaviour and that the Maia/engine runtime assets are still excluded or cached as before.
- Also pulls `workbox-build`, which is one of the `fast-uri` consumers (via `ajv`).

### js-yaml 5 and fast-uri 4 (likely: do NOT bump the override)
- Neither is used by our code. Both exist only in `"overrides"` to force patched versions of
  transitive deps:
  - `js-yaml` ← `cosmiconfig@9` ← `shadcn`
  - `fast-uri` ← `ajv@8` ← `shadcn` (`@dotenvx/dotenvx`, `@modelcontextprotocol/sdk`) and
    `workbox-build` (`vite-plugin-pwa`)
- Bumping an override across a major forces v5/v4 onto consumers that declare v4/v3 ranges,
  which can break them. The right move is to keep the override within the current major (or
  drop it once the consumers ship patched versions), and tell Renovate to ignore majors for
  these two (`packageRules` with `matchUpdateTypes: ["major"]`, `enabled: false`) so the
  dashboard stops offering them.
- Re-check after the vite-plugin-pwa 2 upgrade: workbox may move to a newer `ajv`, changing
  what the `fast-uri` override needs.

## Verification (every plan)
- Full frontend gate: `npm run lint && npm run build && npm test -- --run && npm run knip`.
- `npx audit-ci --config frontend/audit-ci.jsonc` (the CI vuln gate; drop allowlist entries
  that the upgrade fixes).
- Browser smoke on the dev build for Sentry and the PWA (update flow, offline load).

## Out of scope
- Stockfish 19, onnxruntime-web 1.30 (owner decisions, closed PR #351).
- The grouped Renovate minor/patch branch (separate; it also carries onnxruntime /
  onnxruntime-node 1.29 → 1.30, flag before merging).

## Breadcrumbs
- `frontend/package.json`: versions and `"overrides"`
- `renovate.json`: schedule (`before 6am on monday`, Europe/Zurich), packageRules
- `frontend/vite.config.ts`: PWA plugin config
- `frontend/audit-ci.jsonc`: vuln allowlist
- Renovate dashboard: issue #338
