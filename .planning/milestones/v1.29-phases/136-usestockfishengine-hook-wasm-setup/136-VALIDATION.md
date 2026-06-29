---
phase: 136
slug: usestockfishengine-hook-wasm-setup
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-26
---

# Phase 136 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (existing frontend test runner) |
| **Config file** | `frontend/vite.config.ts` (test block) |
| **Quick run command** | `cd frontend && npm test -- --run src/hooks/__tests__/` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run` |
| **Estimated runtime** | ~15–30 seconds (unit); integration test adds ~10s for WASM boot |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run src/hooks/__tests__/`
- **After every plan wave:** Run `cd frontend && npm run lint && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green; `npm run build` must succeed (CI COOP/COEP guard depends on a clean build/preview)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Filled by the planner against the final task breakdown. Each PLAN task must carry an `<automated>` verify command OR a Wave 0 dependency. The planner owns the concrete task IDs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 136-01 | 1 | PLAT-01 | T-136-SC | Package legitimacy gate before install | manual (human-verify) | n/a (blocking checkpoint) | n/a | ⬜ pending |
| 01-T2 | 136-01 | 1 | PLAT-02 | T-136-SC | Pinned dep + committed binaries (no runtime fetch) | build/assert | `cd frontend && node -e "..." && test -f public/engine/stockfish-18-lite-single.wasm` | ❌ W0 | ⬜ pending |
| 01-T3 | 136-01 | 1 | PLAT-01, PLAT-02 | T-136-01, T-136-02 | No COOP/COEP; wasm not precached; application/wasm MIME | CI guard + build | `cd frontend && npm run build` + CI `curl -I` step | ❌ W0 | ⬜ pending |
| 02-T1 | 136-02 | 2 | ENGINE-01, ENGINE-02, ENGINE-05 | — | UCI parse: bounds, mate signs, MultiPV | unit (node) | `cd frontend && npm test -- --run src/hooks/__tests__/uciParser.test.ts` | ❌ W0 | ⬜ pending |
| 02-T2 | 136-02 | 2 | ENGINE-01..05 | T-136-03, T-136-04 | State machine, stop-pending discard, tab-hide pause, teardown | unit (jsdom mock Worker) | `cd frontend && npm test -- --run src/hooks/__tests__/useStockfishEngine.test.ts && npx tsc -b` | ❌ W0 | ⬜ pending |
| 02-T3 | 136-02 | 2 | ENGINE-01, ENGINE-02, ENGINE-03 | T-136-V5 | Real-WASM FEN→bestmove (mate-in-1, deterministic) | integration (node) | `cd frontend && npm test -- --run src/hooks/__tests__/useStockfishEngine.integration.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/hooks/__tests__/uciParser.test.ts` — UCI parser unit-test stubs (ENGINE-01/02/05)
- [ ] `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` — headless WASM FEN→bestmove integration stub (node env via stockfish `initEngine`)
- [ ] `stockfish` npm dependency installed (gated behind a `checkpoint:human-verify` task — package flagged "too-new"/SUS by trust gate)
- [ ] Engine binaries vendored to `frontend/public/engine/`

*vitest itself is already installed — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| On-device (iOS Safari / low-end Android) live eval render | ENGINE-01..05 | No rendered UI ships in 136 (D-01); requires the /analysis page | Deferred to Phase 138 (D-02) — not a 136 gate |
| Real-device `movetime 1500` responsiveness calibration | ENGINE-05 / PLAT-02 | Needs budget hardware | Deferred to Phase 138 UAT smoke check |

*All in-phase behaviors (UCI parsing, engine boot, eval/PV/bestmove extraction, COOP/COEP absence, wasm non-precache) have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-26 (plan-checker VERIFICATION PASSED)
