---
phase: 162
slug: grading-run-authoritative-eval-reconciliation-precedence-fli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-10
---

# Phase 162 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest ^4.1.7 |
| **Config file** | `frontend/vite.config.ts` (vitest config colocated with Vite config) |
| **Quick run command** | `cd frontend && npx vitest run src/lib/engineEvalLookup.test.ts src/lib/__tests__/moveQuality.test.ts` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~5 s quick / ~60 s full |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (targeted lib tests)
- **After every plan wave:** Run `cd frontend && npm test -- --run` **plus** `cd frontend && npx tsc -b` (npm test does NOT type-check — esbuild strips types)
- **Before `/gsd-verify-work`:** Full suite + tsc must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner fills) | — | — | D-01 precedence flip (grading-wins-on-overlap, free-run-fills-gaps) | — | N/A | unit | `npx vitest run src/lib/engineEvalLookup.test.ts` | ✅ (assertions inverted) | ⬜ pending |
| TBD | — | — | D-03 mirror-image Best label (non-`bestSan` top eval → `best`) | — | N/A | unit | `npx vitest run src/lib/__tests__/moveQuality.test.ts` or new helper test file | ❌ W0 | ⬜ pending |
| TBD | — | — | D-09 unionSans extension gated on free-run bestmove commit | — | N/A | integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ (extend) | ⬜ pending |
| TBD | — | — | D-13 verdict Stockfish side is lookup-derived (same move, different value across sources) | — | N/A | integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ (extend — current test at :443 does not exercise this) | ⬜ pending |
| TBD | — | — | D-08 useGameOverlay off-main-line eval passthrough uses reconciled value | — | N/A | unit | `npx vitest run src/hooks/__tests__/useGameOverlay.test.ts` | ❓ verify at planning | ⬜ pending |
| TBD | — | — | D-07/D-12 arrow targets true global reconciled argmax | — | N/A | integration | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ❓ verify at planning | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test case (and possibly new test file) for the reconciled-argmax helper (`resolveReconciledBest` or equivalent) — mirror-image Best-label case
- [ ] Verify `useGameOverlay` test coverage for the eval passthrough; add stub if missing

*Existing vitest infrastructure covers everything else.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No visible label/arrow flicker when grading lands (~4 s) | D-10 | Timing/visual perception on a live board | On `/analysis`, load a position, watch Best/Good labels and green arrow settle once grading lands; confirm no higher number ever shows on a "Good" move than the "Best" move |
| Arrow may point at a move the Stockfish card doesn't list (accepted edge case) | D-12 | Requires a position where a Maia/FC-only candidate outranks the free run's top-2 | Confirm the divergence is understood/accepted, not a surprise |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
