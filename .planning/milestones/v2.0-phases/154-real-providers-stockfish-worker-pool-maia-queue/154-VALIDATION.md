---
phase: 154
slug: real-providers-stockfish-worker-pool-maia-queue
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-06
---

# Phase 154 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vite.config.ts` |
| **Quick run command** | `cd frontend && npm test -- --run <target test file>` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run <target test file>`
- **After every plan wave:** Run `cd frontend && npm run lint && npm test -- --run && npx tsc -b`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 154-01 | 1 | POOL-02, POOL-04 | T-154-02 | N/A | unit | `cd frontend && npm test -- --run src/lib/engine/__tests__/workerPool.test.ts` | ❌ W0 (created by task) | ⬜ pending |
| 01-T2 | 154-01 | 1 | POOL-01 (+SC5) | T-154-01 | pv[0] keying / drop unparseable | unit | `cd frontend && npm test -- --run src/lib/engine/__tests__/workerPool.test.ts` | ❌ W0 (created by task) | ⬜ pending |
| 01-T3 | 154-01 | 1 | POOL-04 | T-154-02, T-154-03 | abort/lifecycle surface | unit + smoke | `cd frontend && npm test -- --run src/lib/engine/__tests__/workerPool.test.ts && grep -rn "\.multipv" frontend/src/lib/engine/workerPool.ts` | ❌ W0 (created by task) | ⬜ pending |
| 02-T1 | 154-02 | 1 | POOL-03 | T-154-04 | sanToUci try/catch containment | unit | `cd frontend && npm test -- --run src/lib/engine/__tests__/maiaQueue.test.ts` | ❌ W0 (created by task) | ⬜ pending |
| 02-T2 | 154-02 | 1 | POOL-04 | T-154-05, T-154-06 | Sentry error forwarding | unit | `cd frontend && npm test -- --run src/lib/engine/__tests__/maiaQueue.test.ts` | ❌ W0 (created by task) | ⬜ pending |
| SC4 | 154-01 | — | POOL-04 | T-154-02 | N/A | manual | N/A — HUMAN-UAT, deferred to Phase 155 (no UI to drive the pool in 154) | N/A | ⬜ deferred |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test files for `workerPool.ts` priority-queue ordering (POOL-02) and pool sizing heuristic (POOL-04)
- [ ] Test file for `maiaQueue.ts` FIFO dispatch and SAN→UCI conversion (POOL-03)

*Existing vitest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-position review session survives on real iPhone + mid-tier Android without tab reload/crash | POOL-04 | Real-device WASM memory behavior cannot be simulated in jsdom/CI | Run a multi-position review session on both devices; watch for tab reload or crash; verify pool size adapts (fewer workers on mobile) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (every task creates its own test file test-first, RED→GREEN)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (all 5 tasks have automated verify)
- [x] Wave 0 covers all MISSING references (both test files are authored as the first action of their plan's Task 1, before implementation)
- [x] No watch-mode flags (all commands use `--run`)
- [x] Feedback latency < 90s (per-task target ~60s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (SC4 real-device UAT is a documented HUMAN-UAT deferred to Phase 155, when a hook/UI first makes the pool runnable on-device)
