---
phase: 138
slug: analysis-route-page-shell-entry-points
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-26
---

# Phase 138 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.x (jsdom) |
| **Config file** | `frontend/vite.config.ts` (vitest via Vite) |
| **Quick run command** | `cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Type/lint gate** | `cd frontend && npx tsc -b && npm run lint && npm run knip` |
| **Estimated runtime** | ~15 seconds (single file) / ~60s (full frontend suite) |

---

## Sampling Rate

- **After every task commit:** Run `npm test -- --run src/pages/__tests__/Analysis.test.tsx` + `npx tsc -b`
- **After every plan wave:** Run `npm test -- --run` (full frontend suite) + `npm run lint` + `npm run knip`
- **Before `/gsd-verify-work`:** Full frontend suite + lint green; plus the manual UAT gate below
- **Max feedback latency:** ~15 seconds (quick file)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 138-01-* | 01 | 0 | ROUTE-01/02 | — | N/A | unit (Wave 0 stubs) | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | ❌ W0 | ⬜ pending |
| 138-02-* | 02 | 1 | ROUTE-01 | — | `/analysis` renders shell, all testids present | unit (jsdom, mocked engine) | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | ❌ W0 | ⬜ pending |
| 138-02-* | 02 | 1 | ROUTE-02 | T-138-01 | `?fen=` seeds root; empty → start; malformed → start (no crash) | unit | same file | ❌ W0 | ⬜ pending |
| 138-02-* | 02 | 1 | ENGINE-04/D-06 | — | board interactive while `isReady===false`; "Loading engine…" shown | unit (mock engine `isReady:false`) | same file | ❌ W0 | ⬜ pending |
| 138-03-* | 03 | 1 | ROUTE-02 | — | "Analyze position" navigates with encoded FEN | unit (Openings) | `npm test -- --run src/pages/__tests__/Openings*.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 138-* | — | — | ROUTE-01 | — | stockfish JS/WASM only in Analysis chunk | build-output grep | `npm run build` then grep `dist/assets` | ❌ W0 (optional) | ⬜ pending |
| 138-* | — | — | PLAT-01/SC#4 | T-138-03 | no COOP/COEP headers; WASM MIME `application/wasm` | CI (already present) | `.github/workflows/ci.yml` header guard | ✅ exists (Phase 136) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> jsdom has no real `Worker` for the classic engine file. The page test **must mock `useStockfishEngine`** (`vi.mock('@/hooks/useStockfishEngine', …)` returning a fixed `StockfishEngineState`) to drive `isReady`/`pvLines` states deterministically. The real worker is exercised by Phase 136's integration test, not here.

---

## Wave 0 Requirements

- [ ] `frontend/src/pages/__tests__/Analysis.test.tsx` — covers ROUTE-01/02 + D-06 (mock engine + `MemoryRouter` + `QueryClientProvider`). Harness pattern: `Endgames.readinessGate.test.tsx`, `Openings.statsBoard.test.tsx`.
- [ ] Extend an Openings test (or add one) asserting the "Analyze position" button calls `navigate` with `/analysis?fen=<encoded>`.
- [ ] (optional) build-grep assertion or documented manual Network-tab check for the lazy boundary (ROUTE-01 SC#1) — jsdom cannot prove lazy fetch.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lazy-load boundary — no stockfish fetch on other routes | ROUTE-01 / SC#1 | jsdom cannot prove real lazy fetch | DevTools Network: visit `/library`, `/openings`, `/endgames` → confirm **no** request for `stockfish-18-lite-single.js`/`.wasm`; then `/analysis` → engine fetches fire exactly once |
| On-device eyeball (carried from Phase 137 — this is 138's gate) | SC#3 / D-06 | Real device rendering | iOS Safari / low-end Android: render `/analysis`, confirm EvalBar/EngineLines/VariationTree display, board+stepper interactive during WASM init, eval updates within ~3s |
| `window.crossOriginIsolated === false` on `/analysis` | SC#4 | Live browser console | Type `window.crossOriginIsolated` in console on `/analysis` → must be `false` |
| Full Google OAuth sign-in completes from any page | SC#4 / PLAT-01 | Live OAuth flow | Sign in via Google from `/analysis` and another page; CI header guard covers the static check, live flow is a manual confirm |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01 scaffolds `Analysis.test.tsx` RED)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-26 (plan-checker verified all tasks carry automated verify; Wave-0 scaffold present)

> `wave_0_complete` stays `false` until execution lands the RED scaffold; it flips during `/gsd-execute-phase`.
