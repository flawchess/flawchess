---
phase: 122
slug: in-app-feedback-button-seed-049
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 122 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, async) · vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) · `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_feedback.py` (single file, serial) |
| **Full suite command** | `uv run pytest -n auto` · `( cd frontend && npm test -- --run )` |
| **Estimated runtime** | backend full ~ minutes; single file ~seconds; frontend ~seconds |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (backend single test file or frontend file).
- **After every plan wave:** Run the full backend suite (`uv run pytest -n auto`) + frontend tests.
- **Before `/gsd-verify-work`:** Full suite must be green; `ruff format/check` + `ty check` clean.
- **Max feedback latency:** 60 seconds (single-file run).

---

## Per-Task Verification Map

> Plan IDs are provisional; the planner finalizes them. This map seeds the expected coverage.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 122-01-* | 01 | 1 | SEED-049 D-04/D-05 | — | feedback row persists with user_id FK + created_at | unit | `uv run pytest tests/test_feedback.py` | ❌ W0 | ⬜ pending |
| 122-01-* | 01 | 1 | SEED-049 D-05 | — | Sentry message emitted with source/platform/elo tags, no vars in message | unit | `uv run pytest tests/test_feedback.py -k sentry` | ❌ W0 | ⬜ pending |
| 122-01-* | 01 | 1 | SEED-049 D-07 | T-122-rate | per-user rate limit + max length rejects abuse (429/422) | unit | `uv run pytest tests/test_feedback.py -k rate` | ❌ W0 | ⬜ pending |
| 122-02-* | 02 | 2 | SEED-049 D-03/D-06 | — | modal submits required text + optional sentiment via mutation | component | `( cd frontend && npm test -- --run )` | ❌ W0 | ⬜ pending |
| 122-02-* | 02 | 2 | SEED-049 D-01/D-02 | — | scroll-direction hook hides/shows; yields to open overlay | component | `( cd frontend && npm test -- --run )` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feedback.py` — backend stubs: persist, Sentry tagging, rate-limit/length guard, guest acceptance.
- [ ] `frontend/src/.../FeedbackButton.test.tsx` (+ modal/hook tests) — scroll-hide, overlay-yield, modal submit.
- [ ] Existing fixtures cover async client + current-user injection (`tests/conftest.py`); no new framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iOS safe-area clearance in installed PWA | SEED-049 D-02 | `env(safe-area-inset-bottom)` only resolves on a real device/installed PWA | Install PWA on iPhone, scroll, confirm button clears the home indicator |
| Real mobile drawer ↔ button collision (yield-to-overlay) | SEED-049 D-02 | Visual overlap is device/viewport dependent | On mobile, open filter & bookmark drawers; confirm button hides/yields, never floats on top |
| Sentry submission ping arrives with correct cohort tags | SEED-049 D-05 | Requires live Sentry ingestion | Submit feedback on staging/prod; confirm event in Sentry with source/platform/elo_bucket tags |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
