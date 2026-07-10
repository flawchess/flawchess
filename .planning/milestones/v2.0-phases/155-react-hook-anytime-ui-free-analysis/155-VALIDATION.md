---
phase: 155
slug: react-hook-anytime-ui-free-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 155 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `155-RESEARCH.md` → ## Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.7 + `@testing-library/react` 16.3.2 (existing, no changes needed) |
| **Config file** | `frontend/vite.config.ts` (Vitest reads Vite's config; no separate `vitest.config.ts`) |
| **Quick run command** | `cd frontend && npx vitest run <changed-test-file>` |
| **Full suite command** | `cd frontend && npm test` (`vitest run`) |
| **Estimated runtime** | ~30–60 seconds (frontend suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run <changed-test-file>`
- **After every plan wave:** Run `cd frontend && npm test` (full suite)
- **Before `/gsd-verify-work`:** Full suite green + `npm run lint` + `npx tsc -b` (type-check — CLAUDE.md notes lint/test alone do NOT type-check shared property access)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

> Task IDs assigned by the planner. Rows below are the requirement→test seams the
> planner MUST bind to concrete task IDs when writing PLAN.md.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | DISPLAY-01 | — | First `onSnapshot` commits near-instantly; later snapshots **throttle** at ~150ms (never a debounce that delays first paint) | unit | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "throttle"` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | DISPLAY-01 | — | Navigating to a new FEN aborts the previous run AND calls `pool.stopAll()` (Pitfall 1 regression guard — abort signal does not propagate into the pool) | unit | `npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts -t "abort"` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | DISPLAY-02 | — | `FlawChessEngineLines` renders `modalPath` as SAN chips, first `MAX_PLIES=5` + expand chevron | unit | `npx vitest run src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | DISPLAY-03 | — | `expectedScoreToWhitePovCp` round-trips at both mate boundaries (`es<=0`/`es>=1`) and mid-range for both `rootMover` colors (Pitfall 2 regression guard) | unit | `npx vitest run src/lib/__tests__/expectedScoreToWhitePovCp.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DISPLAY-04 | — | Eval-bar left-slot precedence: FC when enabled, falls back to Maia when only Maia is on; right-slot source swaps to `topLine.objectiveEvalCp` while FC runs | unit/integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "FlawChess"` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/hooks/__tests__/useFlawChessEngine.test.ts` — DISPLAY-01 (throttle + abort/stopAll regression guard). Mirror `useStockfishEngine.test.ts`'s `driveInit`/fake-timer pattern; mock `WorkerPool`/`MaiaQueue`.
- [ ] `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` — DISPLAY-02, DISPLAY-03. Mirror `EngineLines.test.tsx` chip-rendering assertions.
- [ ] `frontend/src/lib/__tests__/expectedScoreToWhitePovCp.test.ts` — DISPLAY-03 mate-boundary correctness (pure-function table test; may co-locate with `liveFlaw.test.ts`).
- [ ] `frontend/src/pages/__tests__/Analysis.test.tsx` **already exists** (has the 151.1 eval-bar-perspective regression block) — extend with FC-precedence cases, do not create a new file. If precedence logic grows complex, extract it into a directly-testable pure function.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| On-by-default engine holds under real mobile Safari memory pressure (SC4, deferred from Phase 154) | DISPLAY-01 | Real-device memory behavior cannot be unit-tested; this is the gate for the on-by-default-everywhere decision (D-02) | On an iOS device, open `/analysis`, navigate through ~20 positions with all 3 engines ON; confirm no crash/OOM and lines keep refining. If it fails, fall back to device-adaptive default (on desktop / off mobile). |
| Live-refine reads smoothly (no jank/flicker) to a human eye | DISPLAY-01 | "Neither jank nor flicker faster than a human can read" is a perceptual property | Desktop + mobile: navigate to a middlegame position, watch lines appear immediately and reorder smoothly at the 150ms cadence. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
