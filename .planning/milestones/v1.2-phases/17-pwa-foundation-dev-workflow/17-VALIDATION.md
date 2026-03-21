---
phase: 17
slug: pwa-foundation-dev-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend regression); no frontend test framework (build audits only) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `uv run pytest && cd frontend && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | PWA-03 | file presence | `ls frontend/public/icons/icon-192.png frontend/public/icons/icon-512.png` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | PWA-01 | build audit | `npm run build && ls frontend/dist/manifest.webmanifest` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | PWA-02 | build audit | `npm run build && grep -l "sw.js" frontend/dist/` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 1 | PWA-02 | config check | `grep "NetworkOnly" frontend/vite.config.ts` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | DEV-01 | script check | `grep "dev:mobile" frontend/package.json` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | DEV-02 | config check | `grep "allowedHosts" frontend/vite.config.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/public/icons/icon-192.png` — chess knight icon 192×192
- [ ] `frontend/public/icons/icon-512.png` — chess knight icon 512×512
- [ ] Backend test suite passes (`uv run pytest`) — regression guard
- [ ] `npm run build` succeeds before any changes — baseline

*No new test files needed — this phase adds build-time tooling and static assets, not business logic.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Android "Add to Home Screen" prompt appears | PWA-01 | Requires physical Android device or emulator | Build → preview → open in Android Chrome → verify install banner |
| Standalone mode (no browser chrome) | PWA-01 | Requires installed PWA on device | Install PWA → open from home screen → verify no URL bar |
| Static assets served from SW cache on repeat visit | PWA-02 | Requires Network tab inspection | Build → preview → load page → reload → check Network tab shows "(ServiceWorker)" for JS/CSS |
| API routes NOT served from SW cache | PWA-02 | Requires Network tab inspection | Build → preview → trigger API call → check Network tab does NOT show "(ServiceWorker)" for /analysis/ etc. |
| Chess knight icons visible on home screen | PWA-03 | Visual verification | Install PWA → check home screen shortcut shows knight icon, not Vite logo |
| Cloudflare Tunnel accessible from phone | DEV-02 | Requires phone on different network | Run `npm run dev:tunnel` → open tunnel URL on phone → verify page loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
