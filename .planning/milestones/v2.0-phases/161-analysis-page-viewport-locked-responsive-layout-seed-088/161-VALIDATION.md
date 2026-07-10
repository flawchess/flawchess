---
phase: 161
slug: analysis-page-viewport-locked-responsive-layout-seed-088
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-09
---

# Phase 161 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm test -- --run <file>` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the affected vitest file (`npm test -- --run <file>`)
- **After every plan wave:** Run `cd frontend && npm run lint && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green + `npx tsc -b` clean (shared-type/prop changes)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Populated by the planner. Note (per RESEARCH.md): jsdom/Vitest cannot exercise real CSS
> layout, `100dvh`, media queries, or `ResizeObserver` callbacks — responsive/visual behavior
> is HUMAN-UAT, not automatable. Automated coverage is limited to component-render smoke tests
> and any extracted pure sizing/budget helper.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 161-01-01 | 01 | 1 | SEED-088 | T-161-01 / — | N/A (client layout) | unit | `cd frontend && npx vitest run src/components/board/__tests__/boardSize.test.ts` | ✅ | ⬜ pending |
| 161-01-02 | 01 | 1 | SEED-088 | T-161-01 / — | N/A (client layout) | build | `cd frontend && npm run build` (Tailwind token/variant compiles) | ✅ | ⬜ pending |
| 161-01-03 | 01 | 1 | SEED-088 | T-161-01 / — | N/A (client layout) | structural + manual | `cd frontend && npx vitest run src/pages/__tests__/Analysis.test.tsx && npx tsc -b && npm run lint` (real responsive behavior = HUMAN-UAT, see Manual-Only) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*If none: "Existing infrastructure covers all phase requirements."*

- [ ] Existing vitest infrastructure covers component-render smoke tests; no new framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `100dvh` frame lock, no page scroll on desktop | SEED-088 | jsdom has no layout/viewport engine | Load `/analysis` at ≥1200px width, ≥560px height; confirm no page scroll, inner regions scroll |
| Board sizes `clamp(420, min(w,h), 600)` fluidly | SEED-088 | `ResizeObserver`/CSS layout not exercised in jsdom | Shrink window height; board shrinks to ~420 floor then middle column scrolls |
| ~1200px breakpoint keeps 1280/1366 laptops in desktop 3-col | SEED-088 | Media queries not evaluated in jsdom | Resize across ~1200px; confirm 1280/1366 stay 3-col, below stacks to mobile |
| ~560px short-screen page-scroll fallback | SEED-088 | Height media query not evaluated in jsdom | Set window height <560px; confirm `100dvh` lock releases, page scrolls |
| Mobile (`<lg`) layout unchanged | SEED-088 | Visual parity check | Compare mobile `/analysis` before/after; no diff |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies or documented HUMAN-UAT
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (or documented as manual-only)
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-09
