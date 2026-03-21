---
phase: 22-ci-cd-monitoring
plan: 01
subsystem: infra
tags: [github-actions, ci-cd, docker, ssh, postgresql, pytest, ruff, eslint]

# Dependency graph
requires:
  - phase: 21-docker-deployment
    provides: docker-compose.yml and VPS deploy setup that CI pipeline targets
provides:
  - GitHub Actions CI/CD workflow that runs tests on every push/PR and auto-deploys to VPS on push to main
affects: [23-launch-readiness]

# Tech tracking
tech-stack:
  added: [appleboy/ssh-action@v1, actions/checkout@v4, actions/setup-python@v5, actions/setup-node@v4]
  patterns: [test-before-deploy workflow, postgres service container for CI tests, SSH deploy via GitHub Actions]

key-files:
  created:
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "pip install uv chosen over astral-sh/setup-uv action — simpler, avoids third-party action uncertainty"
  - "Health check hits public HTTPS domain (not localhost) — GitHub Actions runner cannot reach VPS localhost"
  - "command_timeout: 10m on SSH action — cold docker builds take 3-5 min and need headroom"
  - "quoted 'on' key in YAML — unquoted 'on' parses as boolean True in Python yaml.safe_load"

patterns-established:
  - "Pattern 1: test job always runs on push and PR; deploy job only on push to main via if: condition"
  - "Pattern 2: health check polls /api/health with 12x5s loop = 60s total timeout"

requirements-completed: [DEPLOY-07]

# Metrics
duration: 5min
completed: 2026-03-21
---

# Phase 22 Plan 01: GitHub Actions CI/CD Workflow Summary

**GitHub Actions CI/CD pipeline with postgres service container for pytest, ruff + eslint linting, SSH deploy via appleboy/ssh-action, and 60s health check polling https://flawchess.com/api/health**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T21:29:21Z
- **Completed:** 2026-03-21T21:34:00Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Single `.github/workflows/ci.yml` with test + deploy jobs covering full CI/CD pipeline
- Test job: pytest against postgres:18-alpine service container with correct TEST_DATABASE_URL, ruff check, npm lint
- Deploy job: SSH into VPS via appleboy/ssh-action, `docker compose up -d --build`, 60s post-deploy health check

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GitHub Actions CI/CD workflow** - `f0794d3` (feat)

**Plan metadata:** _(see final commit below)_

## Files Created/Modified

- `.github/workflows/ci.yml` - Complete CI/CD workflow with test + deploy jobs, postgres service, health check

## Decisions Made

- Used `pip install uv` rather than `astral-sh/setup-uv` action — simpler, avoids an extra third-party action
- Health check curl targets `https://flawchess.com/api/health` (not localhost) — GitHub Actions runner has no route to VPS localhost
- `command_timeout: 10m` on appleboy/ssh-action to accommodate cold docker build times
- Quoted `"on":` key in YAML to prevent Python's `yaml.safe_load` from parsing `on` as boolean `True` — GitHub Actions itself handles both forms correctly, but the quoted form is valid in both contexts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Quoted 'on' YAML key to fix boolean parsing**
- **Found during:** Task 1 (verification step)
- **Issue:** `on:` is a boolean keyword in YAML 1.1 — `yaml.safe_load` parsed it as `True` instead of the string `"on"`, causing the acceptance criteria checks for push/pull_request triggers to fail
- **Fix:** Changed `on:` to `"on":` — quoted form is valid GitHub Actions syntax and parses correctly in Python
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** All 17 acceptance criteria checks pass after fix
- **Committed in:** f0794d3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness of YAML validation. GitHub Actions runtime was unaffected (it handles both forms), but the CI verification script required the fix.

## Issues Encountered

None beyond the YAML boolean parsing fix documented above.

## User Setup Required

**External services require manual configuration before the workflow will succeed.** Three GitHub Actions secrets must be added:

| Secret | Value |
|--------|-------|
| `SSH_PRIVATE_KEY` | Private key from dedicated deploy keypair (contents of `~/.ssh/gh_deploy_key`) |
| `SSH_HOST` | VPS IP or hostname (e.g., `flawchess.com`) |
| `SSH_USER` | `deploy` (the deploy user on the VPS) |

**Steps:**
1. Generate keypair: `ssh-keygen -t ed25519 -C 'github-actions-deploy' -f ~/.ssh/gh_deploy_key`
2. Add public key to deploy user on VPS: `ssh-copy-id -i ~/.ssh/gh_deploy_key.pub deploy@<VPS_IP>`
3. Add each secret at: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

## Next Phase Readiness

- CI/CD pipeline is in place — push to main will trigger test + deploy once GitHub secrets are configured
- Phase 22 Plan 02 (Sentry monitoring) is independent and can proceed immediately
- VPS must have the deploy user's authorized_keys updated with the CI deploy key before the first automated deploy

---
*Phase: 22-ci-cd-monitoring*
*Completed: 2026-03-21*
