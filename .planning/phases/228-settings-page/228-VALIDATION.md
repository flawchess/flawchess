---
phase: "228"
slug: "settings-page"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-03"
---

# Phase 228 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest + @testing-library/react (per-file `// @vitest-environment jsdom`) |
| **Config file** | `frontend/vite.config.ts` (`test` block) + `frontend/src/vitest.setup.ts` |
| **Quick run command** | `cd frontend && npx vitest run <files>` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~120 seconds (full), seconds per targeted file |

---

## Sampling Rate

- **After every task commit:** Run the task's own test files via the quick run command
- **After every plan wave:** Run `cd frontend && npm test -- --run && npm run lint && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green (incl. `npm run knip`)
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled by the planner per task. Decision-level map (from 228-RESEARCH.md § Validation Architecture):

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| store / D-08 | defaults 2/1/2/1, round-trip, invalid → default, subscribers re-render, reset | unit | `npx vitest run src/lib/__tests__/engineSettings.test.ts` | ❌ W0 | ⬜ pending |
| sound | Switch toggles `flawchess_bot_sound_muted`; legacy `'1'` reads muted | component | `npx vitest run src/components/settings/__tests__/SettingsPanel.test.tsx` | ❌ W0 | ⬜ pending |
| D-07/D-09/D-10 | 3 sections in order; toggle items; trackEvent per change; Reset | component | same file | ❌ W0 | ⬜ pending |
| D-01/D-02/route | `nav-settings`, `drawer-settings`, `/settings` title | component | `npx vitest run src/App.test.tsx` | ✅ extend | ⬜ pending |
| D-03/D-04/D-06 | cogwheel opens `settings-sheet` with full panel, no navigation | component | `npx vitest run src/components/settings/__tests__/SettingsSheetButton.test.tsx` | ❌ W0 | ⬜ pending |
| D-12 | MultiPV option sent at init and re-sent when idle; change re-searches | unit | `npx vitest run src/hooks/__tests__/useStockfishEngine.test.ts` | ✅ update | ⬜ pending |
| D-14/D-15 | SF arrows from reconciled ranking, no repeated move; 0 → none; widths | unit | `npx vitest run src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` | ❌ W0 | ⬜ pending |
| D-14 union | `unionSans` includes all free-run roots; MultiPV floor 2 | page | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ extend | ⬜ pending |
| D-16 / styling | cards render N rows; primary vs secondary badge tokens | component | `npx vitest run src/components/analysis/__tests__/` | ✅ update | ⬜ pending |
| D-11/D-13 | free-play multiPv = max(lines, arrows); legend arrows unaffected | unit | `npx vitest run src/lib/__tests__/trainArrows.test.ts src/hooks/__tests__/useTrainFreePlay.test.ts` | ✅ update | ⬜ pending |
| retire 2nd-best | `useGameOverlay` emits no second-best arrow | unit | `npx vitest run src/hooks/__tests__/useGameOverlay.test.ts` | ✅ update | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/__tests__/engineSettings.test.ts`
- [ ] `frontend/src/components/settings/__tests__/SettingsPanel.test.tsx`
- [ ] `frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx` (vaul jsdom shims from App.test.tsx)
- [ ] `frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts`
- [ ] Mutation-proof D-14: revert the arrow loop to `reconciledBestUci ?? …` and confirm the new arrow test fails

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Translucent non-primary colors legible (SF blue, FC gold) on badges and arrows | Styling | Visual tuning | Browser UAT on /analysis with 5 lines / 3 arrows per engine |
| Settings sheet on mobile /analysis and mobile bot game; sound off mid-game | D-03/D-04/D-06 | Real Drawer + audio behavior | Mobile viewport UAT; toggle sound during a bot game |
| Live MultiPV change re-searches under the sheet | D-06/D-12 | Real Stockfish WASM | Change SF lines with sheet open on /analysis and Train free-play |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
