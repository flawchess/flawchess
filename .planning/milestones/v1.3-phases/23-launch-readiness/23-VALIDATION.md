---
phase: 23
slug: launch-readiness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest/lint (frontend) |
| **Config file** | `pyproject.toml`, `frontend/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest && cd frontend && npm run lint && npm run build` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run lint && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CONT-01 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | CONT-02 | manual | OG preview check | N/A | ⬜ pending |
| TBD | TBD | TBD | CONT-03 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | STAB-01 | unit | `uv run pytest tests/test_rate_limiter.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BRAND-05 | manual | README review | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rate_limiter.py` — stubs for STAB-01 rate limiter concurrency tests
- [ ] Existing test infrastructure covers remaining requirements (frontend build, lint)

*Existing pytest + frontend build pipeline covers most phase requirements. Rate limiter is the only new testable backend component.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OG preview rendering | CONT-02 | Requires browser/social media preview | Share flawchess.com URL on Discord/Twitter, verify image and title appear |
| robots.txt served | CONT-02 | Static file serving via Caddy | `curl https://flawchess.com/robots.txt` returns valid content |
| sitemap.xml served | CONT-02 | Static file serving via Caddy | `curl https://flawchess.com/sitemap.xml` returns valid XML |
| Homepage visual review | CONT-01 | Layout/content quality | Visit `/` unauthenticated, verify USPs, FAQ, CTA visible |
| Privacy page content | CONT-03 | Content accuracy | Visit `/privacy`, verify all data processors named |
| README quality | BRAND-05 | Content review | Read README.md on GitHub, verify screenshots, badges, setup instructions |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
