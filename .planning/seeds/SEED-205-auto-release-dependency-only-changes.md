---
id: SEED-205
status: dormant
planted: 2026-10-27
planted_during: ad-hoc auto-update setup (no phase in flight); steps 1-3 of the plan below shipped the same day
trigger_when: Renovate automerge has run cleanly for a few weeks and the owner wants dependency-only releases to reach prod without running /deploy by hand
scope: small to medium (one scheduled workflow plus a guard script; the hard part is the "deps-only" gate and the failure path)
---

# SEED-205: Auto-release dependency-only changes to production

## Context

Auto-update plan agreed 2026-10-27, in four layers:

1. **Host OS** (DONE 2026-10-27): unattended-upgrades for Ubuntu security + updates and the Docker
   apt repo, an automatic reboot at 03:30 UTC when one is needed, Docker `live-restore`. See
   `docs/production-runbook.md` → "Automatic updates".
2. **Renovate automerge** (DONE 2026-10-27): non-major updates of stable (>= 1.0) packages, digests,
   GitHub Actions and lock file maintenance merge into `main` on their own once the required `test`
   check passes. Majors, 0.x packages, onnxruntime*, Postgres majors stay manual.
3. **Postgres image pin** (DONE 2026-10-27): `postgres:18.6-alpine@sha256:…` in prod, dev, benchmark
   and CI compose/workflow files, grouped in Renovate so all four move together.
4. **This seed:** automerge only reaches `main`. Prod still moves only when the owner runs
   `bin/deploy.sh` / `/deploy`, so dependency fixes (including security ones) sit undeployed until the
   next feature release.

## Idea

A weekly scheduled workflow (e.g. Tuesday 04:00 UTC, after Renovate's Monday window) that:

- checks whether every commit in `origin/production..origin/main` was authored by Renovate
  (`renovate[bot]`) and touches only dependency files (`uv.lock`, `pyproject.toml`,
  `frontend/package*.json`, `Dockerfile*`, `docker-compose*.yml`, `.github/workflows/*`);
- if yes, opens the `main → production` release PR, waits for CI on it, squash-merges it, dispatches
  `deploy.yml`, then does the forward-port step that `bin/deploy.sh` / the `/deploy` skill does today
  (see `docs/git-workflow.md`);
- if any non-Renovate commit is present, does nothing (feature work always waits for the owner).

## Open questions

- **Failure path.** A deploy that fails its health/header check leaves prod on the new commit. Today
  the owner is at the keyboard for that. Needs either an automatic rollback to the previous
  `production` SHA or at least a loud alert (GitHub notification is too quiet).
- **Things CI cannot see.** The onnxruntime >= 1.30 segfault and the iOS wasm issues would have passed a
  green CI. Those packages are excluded from automerge, but any frontend runtime dependency can break
  the in-browser engine on a device CI does not have. Consider limiting auto-release to backend +
  dev deps, or to security PRs only.
- **Changelog.** Dependency-only releases have no user-facing bullets; decide whether the release PR
  needs a CHANGELOG entry at all (CLAUDE.md says never cut a release without one).
- **Uptime monitoring** is a prerequisite either way: nothing pages the owner if prod is down after an
  unattended reboot or deploy. Sentry Uptime monitoring on `/api/health` is the cheapest option.

## Related drift spotted on 2026-10-27

- `ci.yml` validates the Caddyfile with `caddy:2.11.6` in a `docker run` step, while
  `frontend/Dockerfile` ships `caddy:2.11.7`. Renovate does not see image references inside `run:`
  scripts, so the CI version will keep lagging unless it gets a regex manager or an env var.
