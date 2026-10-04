# Phase 232: Frontend Major Dependency Upgrades (SEED-187) - Context

**Gathered:** 2026-10-04 (owner decisions taken during /gsd-plan-phase 232, after research; no discuss-phase run)
**Status:** Ready for planning

<domain>
## Phase Boundary

Take the major frontend upgrades Renovate (#338) lists under "Awaiting Schedule": vite-plugin-pwa 1 → 2,
@sentry/react 10 → 11, TypeScript 6 → 7, plus keep the js-yaml / fast-uri security overrides within
their current majors and stop Renovate from offering their majors. Scope is the ROADMAP.md Phase 232
section; technical detail is in 232-RESEARCH.md.

</domain>

<decisions>
## Implementation Decisions

### TypeScript 7
- **D-01:** Take TypeScript 7 now via Microsoft's official side-by-side install: `"typescript": "npm:@typescript/typescript6@^6.0.2"` (JS API for typescript-eslint, eslint-plugin-sonarjs, knip) plus `"@typescript/native": "npm:typescript@^7.0.2"` (native `tsc` used by `npm run build`). Remove `baseUrl` / `ignoreDeprecations` from `tsconfig.json` and `tsconfig.app.json`. This supersedes Phase 217 D-11 ("TypeScript 7 stays out"); record it as superseded and update STATE.md's "TS7 blocked upstream" note. Owner approved 2026-10-04, so no further decision checkpoint is needed for the alias itself.

### Sentry 11
- **D-02:** Pin an explicit v10-equivalent `dataCollection` baseline in `Sentry.init` (no IP/user info beyond what v10 sent, no cookies, no HTTP bodies/headers) and set `attachStacktrace: false`. Add a unit test that fails if the block is reverted (mutation-proven). Privacy page copy stays as-is because collection does not widen.
- **D-03:** The roadmap's "source maps resolving" criterion is replaced by "event arrives in the `flawchess` Sentry project with tags/contexts intact". We currently neither ship nor upload source maps; that gap is captured as a seed, not fixed here.

### Overrides / Renovate
- **D-04:** Keep both overrides within their current majors (`fast-uri` floor raised to `^3.1.8` to clear GHSA-hrr3-gc8f-f4qj; `js-yaml` stays 4.x). Add a `renovate.json` `packageRules` entry disabling major updates for overrides-only deps.

### Plan shape
- **D-05:** One plan per dependency, each in its own sequential wave (shared lockfile): PWA 2 → overrides + Renovate rule → Sentry 11 → TS7.

### Claude's Discretion
- Exact `dataCollection` option shape (follow the installed @sentry/react 11 types, per research).
- Whether a tiny ordering tweak between waves helps, as long as each plan stays independently revertable.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 232 section (scope, per-plan verification, out-of-scope list)
- `.planning/phases/232-frontend-major-dependency-upgrades/232-RESEARCH.md` — install recipes, pitfalls, validation architecture
- `.planning/phases/232-frontend-major-dependency-upgrades/232-PATTERNS.md` — analog files / commit conventions
- `frontend/CLAUDE.md` — frontend Sentry rules

</canonical_refs>

<deferred>
## Deferred Ideas

- Source-map generation + upload to Sentry (seed candidate).
- 6 high dev-only advisories via the shadcn CLI (braces, micromatch, ts-morph) (seed candidate).
- Out of scope per ROADMAP: Stockfish 19, onnxruntime-web 1.30, the grouped Renovate minor/patch branch.

</deferred>
