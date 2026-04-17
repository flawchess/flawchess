---
phase: 62
slug: admin-user-impersonation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 62 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Populated by the planner during Step 8 and refined in revision loops.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend — if present) |
| **Config file** | `pyproject.toml` (pytest), `frontend/vitest.config.ts` (if exists) |
| **Quick run command** | `uv run pytest tests/ -k "impersonat" -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test` |
| **Estimated runtime** | TBD by planner |

---

## Sampling Rate

- **After every task commit:** Run the quick command above (filters to impersonation tests)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** planner to fill

---

## Per-Task Verification Map

Populated by the planner. Each task in each PLAN.md must have an entry here (or explicit reasoning for being Manual-Only).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 62-01-01 | 01 | 1 | D-01 | T-62-01 | JWT issued with act_as/admin_id/is_impersonation claims | unit | `uv run pytest tests/test_impersonation.py::test_impersonate_issues_token_with_claims -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_impersonation.py` — pytest test file stubs (token issuance, claim validation, on_after_login bypass)
- [ ] `tests/test_last_activity_middleware.py` — stubs for the is_impersonation skip
- [ ] `tests/test_admin_users_search.py` — stubs for search endpoint (superuser guard, match fields, limit, exclusion of superusers)
- [ ] Frontend test files if vitest is set up (planner confirms)

---

## Key Invariants (Phase 62)

1. **Admin X impersonating User A receives User A's data** — GET /stats/global returns aggregations filtered by user_id=A, not admin's. Regression test covering at least one per-user endpoint.
2. **last_login on User A is unchanged after admin impersonates** — snapshot before, impersonate, hit `/users/me/profile`, assert equal.
3. **last_activity on User A is unchanged after admin impersonates** — same pattern, verifies the `LastActivityMiddleware` skip (D-07 updated).
4. **Impersonation JWT is rejected when admin_id is no longer a superuser** — issue token, flip `admin.is_superuser=False`, re-use token → 401.
5. **Impersonation JWT is rejected when target_user.is_superuser=True** — POST /admin/impersonate/{superuser_id} → 403.
6. **Nested impersonation is rejected** — as impersonated user, POST /admin/impersonate/{other_id} → 403.
7. **Non-superuser calling /admin/** → 403.
8. **Impersonation TTL honored** — token issued with 1h exp; confirm from decoded claim.
9. **`/users/me/profile` reflects impersonation** — response includes `impersonation: { admin_id, target_email }` when act_as is active.
10. **Frontend: Admin tab not rendered when `profile.is_superuser === false`** — component test.
11. **Frontend: Header pill rendered when `profile.impersonation != null`; clicking × calls the logout path** — component test.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual — pill color/placement at mobile + desktop breakpoints | D-20 | Visual regression not automated in this project | Open dev server, log in as superuser, impersonate a test user, verify pill in header at 375px and 1280px breakpoints |
| Full user-flow smoke test | D-09, D-10 | End-to-end of login→select→impersonate→act→logout→re-login best checked in real browser | Manual browser steps per test plan |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
