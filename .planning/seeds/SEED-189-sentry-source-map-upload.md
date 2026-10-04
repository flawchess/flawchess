---
id: SEED-189
status: dormant
planted: 2026-10-04
planted_during: Phase 232 (SEED-187) Plan 03, Sentry 11 upgrade
trigger_when: a minified prod stack blocks diagnosing a real Sentry issue, or the next observability phase
scope: small-to-medium (build config, one upload step, one CI/Docker secret, one init option)
---

# SEED-189: Sentry source-map generation and upload

## Why This Matters

Frontend Sentry frames are minified in production. Every stack trace in
flawchess.sentry.io points at `index-<hash>.js:1:48213` style positions, so a
real error has to be diagnosed by guessing from the function names that
survive minification. Nothing in the project turns that around today.

Phase 232 had to work around it: under Sentry 11, `attachStacktrace` defaults to
true and would attach synthetic stacks to non-Error captures. Without
resolvable frames those stacks change on every deploy and split one issue into
one per release, so `Sentry.init` pins `attachStacktrace: false` (see
`frontend/src/instrument.ts`). Phase 232's live smoke also could not use
"source map resolves" as an acceptance criterion for the same reason; it was
replaced by "tags and contexts intact" (D-03).

## Today's Facts

- `vite-prerender-plugin` (used in `frontend/vite.config.ts` for the `/privacy`
  prerender) turns `build.sourcemap` on internally and deletes the generated
  maps after the build, so `dist/assets` has no `.map` files.
- Nothing in `bin/`, `deploy/`, `.github/`, either Dockerfile, or
  `frontend/vite.config.ts` uploads maps to Sentry. There is no `sentry-cli`,
  no Sentry Vite plugin, and no auth token anywhere in the build.
- `Sentry.init` sets no `release`, so even uploaded maps would have nothing to
  match events against.
- The only Sentry build inputs are the public `VITE_SENTRY_DSN` and
  `VITE_SENTRY_TRACES_SAMPLE_RATE`, passed as Docker build args
  (`frontend/Dockerfile`, `docker-compose.yml`).

## What A Fix Needs

1. Hidden source maps at build time (generated, not referenced by a
   `sourceMappingURL` comment), kept alive past the prerender plugin's cleanup.
2. An upload step (Sentry Vite plugin or `sentry-cli sourcemaps upload`) that
   authenticates with a Sentry auth token supplied as a Docker build secret or
   CI secret, never a baked-in `VITE_*` env var (those end up in the public
   bundle).
3. A release identifier on `Sentry.init` (for example the git SHA) shared
   between the build, the upload, and the init option so maps match events.
4. Deleting the maps from `dist` before Caddy serves them, so the source is not
   publicly downloadable.

## Follow-Up It Unlocks

Once frames resolve, revisit `attachStacktrace: false` from Phase 232 D-02:
synthetic stacks on non-Error captures become useful and stop splitting issues
per deploy. Also unlocks a "source map resolves" check in any future Sentry
smoke test.

## Breadcrumbs

- `frontend/src/instrument.ts` (`attachStacktrace: false` and its comment)
- `frontend/vite.config.ts` (`vitePrerenderPlugin` block)
- `frontend/Dockerfile` and `docker-compose.yml` (`VITE_SENTRY_*` build args)
- `.planning/phases/232-frontend-major-dependency-upgrades/` (D-02, D-03)
