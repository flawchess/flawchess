---
quick_id: 260420-je6
description: implement dependency management fix — Renovate + CI audits + digest-pin base images
status: complete
completed: 2026-04-20
commit: (uncommitted)
---

# Quick Task 260420-je6 — Summary

Addresses audit §4.14 (dependency management & supply chain, graded C+). Implements the automation + scanning + digest-pinning gaps identified in `~/.claude/plans/a-recent-code-audit-generic-spark.md`.

## Changes

### `renovate.json` (new, repo root)
- `config:recommended` + `:dependencyDashboard` preset
- Weekly schedule (Monday before 6am Europe/Zurich), `prConcurrentLimit: 5`, `prHourlyLimit: 2`
- `lockFileMaintenance.enabled: true` — weekly refresh of `uv.lock` + `package-lock.json` transitive deps (Dependabot can't do this)
- Grouped minor/patch PRs for `pep621` + `npm`; separate PRs for majors
- Grouped PRs for github-actions and dockerfile managers
- `vulnerabilityAlerts` labeled `security`, fast-tracked outside schedule

### `.github/workflows/ci.yml`
Added three vulnerability scanning steps inside the existing `test` job:
1. `pip-audit --strict` after `uv sync --locked`
2. `npm audit --audit-level=high --omit=dev` after `npm ci`
3. `docker build` + `aquasecurity/trivy-action@0.28.0` after all frontend steps (HIGH/CRITICAL, `ignore-unfixed: true`)

### `Dockerfile`
Digest-pinned all 3 base image references:
- `python:3.13-slim` → `@sha256:d168b8d9eb761f4d3fe305ebd04aeb7e7f2de0297cec5fb2f8f6403244621664` (builder + runtime stages, lines 1 + 17)
- `ghcr.io/astral-sh/uv:0.10.9` → `@sha256:10902f58a1606787602f303954cea099626a4adb02acbac4c69920fe9d278f82` (line 2)

Digests resolved 2026-04-20 via `docker buildx imagetools inspect`. Renovate's `dockerfile` manager will keep these fresh.

## Verification

- `jq . renovate.json` → valid JSON
- `docker build -t flawchess:ci-digest-test .` → builds successfully with pinned digests (test image removed after verification)
- CI yaml structure preserved; new steps ordered logically within `test` job

## Out of scope (manual user steps required)

These two steps cannot be done in code — user must complete them in the GitHub UI:

1. **Install Mend Renovate GitHub App** — https://github.com/apps/renovate → install on the `flawchess` repo. Renovate will open an onboarding PR which should be closed (we committed our own `renovate.json`).
2. **Enable Dependabot security alerts** — GitHub repo **Settings → Code security → Dependabot alerts → Enable**. Also enable "Dependabot security updates" for auto-PRs on CVE disclosures. Free; complements Renovate.

## Expected outcome

- Audit grade lift: §4.14 C+ → A- once manual steps are completed
- CI runtime impact: +30-60s (Trivy)
- Maintenance load: ~1 grouped Renovate PR per ecosystem per week + dependency dashboard issue

## No commit

User is on `main`. Per CLAUDE.md, commits on main require explicit user approval. Changes staged for user review.
