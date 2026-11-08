---
phase: "245"
slug: "analysis-explain-bar"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-05"
---

# Phase 245 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 5.0.5 + @testing-library/react 16.3.2 (jsdom per file via `// @vitest-environment jsdom`) |
| **Config file** | `frontend/vite.config.ts` `test` block (`testTimeout` 20s, `hookTimeout` 30s, `setupFiles: ['src/vitest.setup.ts']`) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/__tests__/explainBar.test.ts src/hooks/analysis/__tests__/useExplainBar.test.ts src/components/analysis/__tests__/ExplainBar.test.tsx` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~180 seconds (full frontend gate) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (only the touched test files)
- **After every plan wave:** Run `cd frontend && npm test -- --run && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds (quick run)

---

## Per-Task Verification Map

Decision → test mapping from 245-RESEARCH.md §Validation Architecture. Task IDs are filled in by the planner.

| Task | Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|------|----------|----------|-----------|-------------------|-------------|--------|
| 245-01-T1 | D-08 | `eligibleExplainMarker` M/B either side; null for inaccuracy / missing ply / null markers | unit | `npx vitest run src/lib/__tests__/explainBar.test.ts` | ✅ | ✅ green |
| 245-01-T1 | D-04/D-09/D-10 | `chooseExplainOrientation` preferred, fallback, null; `usableExplainLines` guards | unit | same | ✅ | ✅ green |
| 245-01-T1, 245-01-T2 | D-03/D-11 | `resolveExplainBarState` hidden / explain (pending) rules (T1) and got-it rule (T2) | unit | same | ✅ | ✅ green |
| 245-01-T1, 245-01-T2 | D-05/D-06 (page) | Desktop: Explain lands on `Nf3` (missed_moves[0]); opponent flaw lands on `Bc4` (allowed_moves[1]); Got it returns to the flaw move | page | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "Explain bar"` | ✅ (new describe) | ✅ green |
| 245-01-T3 | D-05 | Explain lands on `missed_moves[0]` (user) / `allowed_moves[1]` (opponent); D-09 fallback | hook integration | `npx vitest run src/hooks/analysis/__tests__/useExplainBar.test.ts` | ✅ | ✅ green |
| 245-01-T3 | D-06 | Back/Forward step in line; Got it removes subtree + key, lands on `mainLine[P]` | hook integration | same | ✅ | ✅ green |
| 245-01-T3 | D-07 | Re-entry navigates to existing root, no duplicate graft; shared chip key | hook integration | same | ✅ | ✅ green |
| 245-01-T3 | D-05 (chips) | Graft without `enter` still parks at fork | hook integration | same | ✅ | ✅ green |
| 245-02-T3 | D-11 hardening | `useTacticLines` maps 404 → `null`, other errors still error | unit | `npx vitest run src/hooks/__tests__/useLibrary.test.ts` | ✅ | ✅ green |
| 245-02-T2 | Overlay gate | Non-motif line: no tactic colours, unlabelled payoff arrow; motif line unchanged; `lineHasVisibleMotif` | unit | `npx vitest run src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts src/lib/__tests__/tacticOrientation.test.ts` | ✅ | ✅ green |
| 245-02-T1 | D-01/D-02 + UI | One button; label/testid per state; placements; no tracking inside the component | component | `npx vitest run src/components/analysis/__tests__/ExplainBar.test.tsx` | ✅ | ✅ green |
| 245-01-T1, 245-02-T1 | D-03 placement | Desktop inside `analysis-movelist-card` (01-T1); mobile right before `analysis-mobile-footer`, mid under board controls, inaccuracy and free play absent (02-T1) | page | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "Explain bar"` | ✅ | ✅ green |
| 245-01-T1, 245-01-T2 | Analytics registry | New `BOARD_TOOL_TARGETS` pass name checks | unit | `npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `frontend/src/lib/__tests__/explainBar.test.ts` — D-03/04/08/09/10/11 pure logic
- [x] `frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts` — D-05/06/07 harness (mock `@/lib/sounds`, `@/hooks/useLibrary`)
- [x] `frontend/src/components/analysis/__tests__/ExplainBar.test.tsx` — UI + tracking
- [x] Mutable tactic-lines fixture in `Analysis.test.tsx`'s `@/hooks/useLibrary` mock

No framework install needed. No separate Wave 0 plan: each test file above is created inside the task that
implements the behaviour it covers (245-01-T1 explainBar + page fixture, 245-01-T3 harness, 245-02-T1 component).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-browser flow | D-03/D-05/D-06/D-07 | Visual placement, move sounds, animation interplay | Claude-run browser UAT on dev build: Explain → line + first move, Back/Forward, Got it, Jump interplay, mobile 360px width, mid layout placement |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-05 (validate-phase: 13/13 rows green, 168 mapped tests + 7 page "Explain bar" tests)

## Validation Audit 2026-11-05

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
