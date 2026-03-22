---
phase: 21
slug: docker-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_auth.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_auth.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | DEPLOY-01 | smoke | `docker build -f Dockerfile .` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | DEPLOY-01 | smoke | `docker build -f frontend/Dockerfile .` | ❌ W0 | ⬜ pending |
| 21-02-01 | 02 | 1 | DEPLOY-02 | smoke | `docker compose up -d && docker compose ps` | ❌ W0 | ⬜ pending |
| 21-03-01 | 03 | 2 | DEPLOY-03 | manual-only | `curl https://flawchess.com/api/health` | N/A | ⬜ pending |
| 21-03-02 | 03 | 2 | DEPLOY-04 | manual-only | `docker compose logs backend` | N/A | ⬜ pending |
| 21-03-03 | 03 | 2 | DEPLOY-05 | manual-only | `docker inspect` + repo scan | N/A | ⬜ pending |
| 21-03-04 | 03 | 2 | DEPLOY-06 | manual-only | `curl https://flawchess.com/api/health` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Dockerfile` — backend multi-stage build (required for DEPLOY-01)
- [ ] `frontend/Dockerfile` — frontend build + Caddy stage (required for DEPLOY-01)
- [ ] `docker-compose.yml` — 3-service orchestration (required for DEPLOY-02)
- [ ] `deploy/Caddyfile` — routing config (required for DEPLOY-03)
- [ ] `deploy/entrypoint.sh` — migration + uvicorn start (required for DEPLOY-04)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Caddy serves static files and proxies /api | DEPLOY-03 | Requires live domain with TLS | 1. `curl https://flawchess.com` → HTML response 2. `curl https://flawchess.com/api/health` → JSON response |
| Migrations run on startup | DEPLOY-04 | Requires running Docker Compose stack | 1. `docker compose up -d` 2. `docker compose logs backend` → shows "Running Alembic migrations..." |
| No secrets in images/repo | DEPLOY-05 | Requires image inspection | 1. `docker inspect backend` → no env vars with secrets 2. `git log --all -S PASSWORD` → no matches |
| App accessible over HTTPS | DEPLOY-06 | Requires live server with DNS | 1. `curl -I https://flawchess.com` → 200 with valid TLS 2. Certificate issuer is Let's Encrypt |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
