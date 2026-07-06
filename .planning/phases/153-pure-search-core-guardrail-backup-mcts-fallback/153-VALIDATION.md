---
phase: 153
slug: pure-search-core-guardrail-backup-mcts-fallback
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-05
---

# Phase 153 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (existing frontend setup) |
| **Config file** | frontend/vite.config.ts (vitest section) |
| **Quick run command** | `cd frontend && npm test -- --run src/lib/engine` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run src/lib/engine`
- **After every plan wave:** Run `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 153-01 | 1 | ENGINE-06 | T-153-01 | Frozen SearchRunner/types contract compiles | unit | `npx tsc -b` | ❌ Wave 0 | ⬜ pending |
| 01-T2 | 153-01 | 1 | ENGINE-05 | T-153-01 | Root-relative leaf sigmoid, both root colors | unit | `npx vitest run src/lib/engine/__tests__/leafScore.test.ts` | ❌ Wave 0 | ⬜ pending |
| 02-T1 | 153-02 | 1 | ENGINE-03 | T-153-02 | Prior independent of value/visits | unit | `npx tsc -b` | ❌ Wave 0 | ⬜ pending |
| 02-T2 | 153-02 | 1 | ENGINE-03 | T-153-02 | Expectation ≠ naive/visit-weighted; root=max | unit | `npx vitest run src/lib/engine/__tests__/backup.test.ts` | ❌ Wave 0 | ⬜ pending |
| 03-T1 | 153-03 | 2 | ENGINE-02 | T-153-03 | Truncation/PUCT split/floor scope | unit | `npx tsc -b` | ❌ Wave 0 | ⬜ pending |
| 03-T2 | 153-03 | 2 | ENGINE-02 | T-153-03 | 90% mass cut, canonical tie-break | unit | `npx vitest run src/lib/engine/__tests__/select.test.ts` | ❌ Wave 0 | ⬜ pending |
| 04-T1 | 153-04 | 3 | ENGINE-01,02,04,05,07 | T-153-04a/b | Color-keyed ELO; no wall-clock; canonical-order apply | unit | `npx tsc -b` | ❌ Wave 0 | ⬜ pending |
| 04-T2 | 153-04 | 3 | ENGINE-01,02,04,05 | T-153-04a | Both-color ELO oracle; truncation+leaf; terminal | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` | ❌ Wave 0 | ⬜ pending |
| 04-T3 | 153-04 | 3 | ENGINE-07 | T-153-04b | Bit-identical output + snapshot seq, concurrency 1&2 | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` | ❌ Wave 0 | ⬜ pending |
| 05-T1 | 153-05 | 4 | ENGINE-06 | T-153-06 | Fallback reuses shared primitives | unit | `npx tsc -b` | ❌ Wave 0 | ⬜ pending |
| 05-T2 | 153-05 | 4 | ENGINE-06 | T-153-06 | SC5 swap-in + full phase gate (lint/tsc/knip/suite) | unit | `npx vitest run src/lib/engine/__tests__/fallbackExpectimax.test.ts && npm run knip && npm test -- --run` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing vitest infrastructure covers all phase requirements (confirmed — no new framework install; every reused primitive already has a passing suite).
- [ ] `frontend/src/lib/engine/__tests__/` directory + 5 test files are net-new — created within their owning plans (each test file paired with its source task), not a separate Wave 0 plan (no shared fixture/conftest needed; vitest files are self-contained per project convention).

---

## Manual-Only Verifications

*None expected — all phase behaviors (deterministic search core against fabricated providers) have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
