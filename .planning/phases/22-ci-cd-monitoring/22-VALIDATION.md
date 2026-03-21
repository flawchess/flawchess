---
phase: 22
slug: ci-cd-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), ESLint (frontend) |
| **Config file** | `pyproject.toml` (pytest config), `frontend/eslint.config.js` |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm run lint` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | DEPLOY-07 | integration | `cat .github/workflows/ci-cd.yml` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | DEPLOY-07 | unit | `uv run pytest tests/test_health.py` | ✅ | ⬜ pending |
| 22-02-01 | 02 | 1 | MON-01 | unit | `uv run pytest -x` | ❌ W0 | ⬜ pending |
| 22-02-02 | 02 | 1 | MON-02 | manual | Browser console check | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.github/workflows/` directory — created during plan execution
- [ ] Sentry SDK packages — installed during plan execution

*Existing test infrastructure covers backend verification needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Actions triggers on push to main | DEPLOY-07 | Requires actual git push to GitHub | Push a commit to main, verify Actions tab shows running workflow |
| SSH deploy succeeds | DEPLOY-07 | Requires live VPS connection | Check Actions log for successful SSH + docker compose output |
| Backend error appears in Sentry | MON-01 | Requires Sentry account + live app | Trigger unhandled exception, check Sentry dashboard within 60s |
| Frontend error appears in Sentry | MON-02 | Requires Sentry account + live app | Throw JS error in browser, check Sentry dashboard within 60s |
| Post-deploy health check passes | DEPLOY-07 | Requires live deployment | Check Actions log for health check curl output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
