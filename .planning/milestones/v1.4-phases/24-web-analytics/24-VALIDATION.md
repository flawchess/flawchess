---
phase: 24
slug: web-analytics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | ANLY-05 | smoke | `docker stats --no-stream \| grep umami` — verify < 300 MB | n/a | ⬜ pending |
| 24-01-02 | 01 | 1 | ANLY-01 | manual-only | n/a | n/a | ⬜ pending |
| 24-01-03 | 01 | 1 | ANLY-04 | smoke | `curl -sI https://flawchess.com \| grep -i set-cookie` — verify no tracking cookies | n/a | ⬜ pending |
| 24-02-01 | 02 | 2 | ANLY-01 | manual-only | n/a | n/a | ⬜ pending |
| 24-02-02 | 02 | 2 | ANLY-02 | manual-only | n/a | n/a | ⬜ pending |
| 24-02-03 | 02 | 2 | ANLY-03 | manual-only | n/a | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed — this phase is infrastructure/config only.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard shows visit counts and trends | ANLY-01 | Requires live Umami dashboard UI inspection | 1. Browse flawchess.com pages. 2. Open analytics.flawchess.com. 3. Verify pageview counts appear with trend charts. |
| Top pages visible | ANLY-02 | Requires Umami dashboard UI inspection | 1. Navigate multiple routes on flawchess.com. 2. Check Umami "Pages" section shows ranked list. |
| Referrer sources tracked | ANLY-03 | Requires Umami dashboard UI inspection | 1. Visit flawchess.com via a link from another site (or simulate with Referer header). 2. Verify referrer appears in Umami "Referrers" section. |
| No cookie consent needed | ANLY-04 | Privacy compliance verification | 1. Clear browser cookies. 2. Visit flawchess.com. 3. Check DevTools > Application > Cookies — no analytics cookies set. |
| Negligible RAM overhead | ANLY-05 | Requires production server access | 1. Run `docker stats --no-stream` on production. 2. Verify umami container uses < 300 MB RAM. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
