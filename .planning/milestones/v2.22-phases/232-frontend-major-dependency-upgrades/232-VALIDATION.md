---
phase: "232"
slug: "frontend-major-dependency-upgrades"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: true) (#2117)
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-10-04"
---

# Phase 232 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 5 (jsdom), ESLint 10, knip 6, tsc (6.0.3 now / 7.0.2 after the TS7 plan), audit-ci 7 |
| **Config file** | `frontend/vite.config.ts` (`test` block), `frontend/eslint.config.js`, `frontend/knip.json`, `frontend/audit-ci.jsonc` |
| **Quick run command** | Plan-specific subset (e.g. `cd frontend && npm run build` for TS7; `cd frontend && npx vitest run src/__tests__/instrument.beforeSend.test.ts` for Sentry) |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip && npx audit-ci --config audit-ci.jsonc && npm audit signatures` |
| **Estimated runtime** | ~90 seconds (vitest ~66 s, build ~8 s) |

---

## Sampling Rate

- **After every task commit:** Run the plan's quick subset
- **After every plan wave:** Run the full frontend suite command
- **Before `/gsd-verify-work`:** Full suite must be green, plus the CLAUDE.md pre-merge gate before squash-merge
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per plan. Behavior → test map from RESEARCH.md:

| Behavior | Test Type | Automated Command | File Exists | Status |
|----------|-----------|-------------------|-------------|--------|
| PWA: generated sw.js / manifest / registerSW.js unchanged | build-artifact diff | before/after `npx vite build` + `diff`, `grep -oE 'url:"[^"]+"' dist/sw.js` (19 entries, none under maia/ or engine/) | ✅ | ✅ green (19 entries, 0 maia/engine; 232-01 diff, re-run 2026-10-04 UAT build) |
| Overrides: fast-uri ≥3.1.8, js-yaml 4.x | npm ls / audit | `npm ls fast-uri js-yaml` + `npm audit --json` (no fast-uri entry) | ✅ | ✅ green (fast-uri 3.1.8, js-yaml 4.3.2) |
| Renovate rule valid | config validation | `npx -y --package renovate renovate-config-validator --strict` | ✅ | ✅ green (validator --strict OK; negative control in 232-02) |
| Sentry: privacy baseline + attachStacktrace kept | unit | `npx vitest run src/__tests__/instrument.beforeSend.test.ts` (mutation-proven) | ✅ | ✅ green (32/32 incl. WR-01 + G-232-3 scrubs, mutation-proven) |
| TS7 type-checks the app | build | `rm -rf node_modules/.tmp && npm run build` + `node_modules/.bin/tsc --version` | ✅ | ✅ green (tsc 7.0.2, npm run build exit 0) |
| TS7 type gate not a no-op | negative control | inject TS2322 error → `npx tsc -b` exits 1 → revert | ✅ | ✅ green (TS2322 → exit 1, 232-04) |
| Lint tools still get TS6 API | lint | `npm run lint` + `node -e 'console.log(typeof require("typescript").createProgram)'` = function | ✅ | ✅ green (createProgram = function, 6.0.3) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `frontend/src/__tests__/instrument.beforeSend.test.ts` — add dataCollection / attachStacktrace test case (Sentry plan, written before the init change, mutation-proven)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PWA registers, autoUpdate works, offline shell loads | DEP-PWA2 | Service worker lifecycle needs a real browser | `npm run build && npm run preview`, Chrome DevTools: SW activated, offline + reload serves cached shell. **Done 2026-10-04 (UAT test 2, owner's Chrome via extension): pass** |
| Sentry event arrives with tags/contexts | DEP-SENTRY11 | Needs Sentry dashboard + dev DSN; subagents lack Sentry access | Dev console snippet from RESEARCH.md Pitfall 8, confirm in Sentry `flawchess` project (env development), check envelope has no ip_address/cookies. **Done (UAT tests 1 + 3): pass, breadcrumb gap G-232-3 fixed in 814a3c44c** |
| Docker Alpine build with TS7 | DEP-TS7 | Container build | `docker build -f frontend/Dockerfile .` from repo root. **Done in 232-04 (T-232-14): builder tsc 7.0.2, full image built** |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-04 (/gsd-validate-phase 232)

## Validation Audit 2026-10-04
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
