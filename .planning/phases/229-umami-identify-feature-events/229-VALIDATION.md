---
phase: "229"
slug: "umami-identify-feature-events"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-03"
---

# Phase 229 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (+ @testing-library/react, jsdom per file) |
| **Config file** | `frontend/vite.config.ts` (test block, `setupFiles: ['src/vitest.setup.ts']`) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~120 seconds (full), ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** the touched component's test file plus `analytics.test.ts`
- **After every plan wave:** `cd frontend && npm test -- --run && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled by the planner from `229-RESEARCH.md` § Validation Architecture (Decision → Test Map).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 229-01-01 | 01 | 1 | D-08/D-11/D-16 | T-229-01 | impersonation tokens never identify; malformed tokens yield no id | unit | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/components/ui/__tests__/info-popover.test.tsx` — `useTrackedOpen` (D-13)
- [ ] `frontend/src/components/layout/__tests__/SidebarLayout.test.tsx` — `panel-open` (D-13)
- [ ] `frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx` — D-03
- [ ] `frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` — D-02
- [ ] `frontend/src/hooks/__tests__/useAuth.test.tsx` — logout hard navigation (D-07)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First `/api/send` pageview of a load carries `id` | D-09/D-16 | Needs the real tracker script in a browser | Dev build with tracker enabled, devtools network tab, reload a protected route, inspect the first pageview payload |
| `session.distinct_id` populated after ship | Phase goal | Prod Umami DB, post-deploy | Orchestrator runs the 5 SQL queries in `229-RESEARCH.md` via `flawchess-umami-db` MCP |
| Umami 3.4.0 actually running after deploy | D-17 | Prod infra | Check the deployed `script.js` contains `distinct-id` (3.4.0 marker) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
