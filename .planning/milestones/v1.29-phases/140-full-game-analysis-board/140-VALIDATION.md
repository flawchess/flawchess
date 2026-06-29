---
phase: 140
slug: full-game-analysis-board
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-27
---

# Phase 140 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vitest.config.ts` (existing) |
| **Quick run command** | `cd frontend && npm test -- --run <changed test file>` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Estimated runtime** | ~60 seconds (full frontend suite + typecheck) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run <changed test file>`
- **After every plan wave:** Run `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite + `npx tsc -b` + `npm run knip` must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 140-XX-XX | useAnalysisBoard nesting | — | D-4 | — / — | N/A | unit | `cd frontend && npm test -- --run useAnalysisBoard` | ❌ W0 | ⬜ pending |
| 140-XX-XX | VariationTree 2-level | — | D-4 | — / — | N/A | unit/snapshot | `cd frontend && npm test -- --run VariationTree` | ❌ W0 | ⬜ pending |
| 140-XX-XX | Slider park/sync | — | D-4 | — / — | N/A | unit | `cd frontend && npm test -- --run Analysis` | ❌ W0 | ⬜ pending |

*Planner fills exact task IDs/plan numbers. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The validation seams from RESEARCH.md "## Validation Architecture":

- [ ] `frontend/src/hooks/useAnalysisBoard.test.ts` — `insertPvLine` / `clearPvLine` / `isOnPvLine` invariants (PV nodes chain to fork, mainLine unmutated, level-2 fork detection)
- [ ] `frontend/src/components/analysis/VariationTree.test.tsx` (or extend existing) — two-level nesting render + `buildVariationChain` level resolution
- [ ] Slider park/sync invariants — `sliderDisabled` true off main line, false on main line; slider value parks at fork ply

*If the existing frontend test infra already covers a seam, extend that file rather than adding a new one. Whether these are new files or extensions is the planner's call — record the decision in PLAN.md.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Click inline missed/allowed chip → PV unfolds as sideline, board navigates to fork, overlay activates contextually | D-02 / SC-4 | Multi-component interaction (fetch + tree graft + overlay + arrows) hard to assert headlessly | Load `/analysis?game_id=X&ply=Y` on an analyzed game with a tactic flaw; click the inline Missed/Allowed chip; verify PV unfolds indented, board parks at fork, TacticModeOverlay appears |
| Fork a sub-sideline within an expanded PV (two nesting levels) | SC-4 | Visual/interaction depth | Within an expanded PV, drag a board move; verify a Level-2 (`ml-16`) sub-sideline renders |
| Eval-chart slider parks/dims when a sideline is active, re-enables on return to main line | D-05 / SC-3 | Visual dim state + tooltip | Enter a sideline; verify slider is dimmed (`opacity-40`) + tooltip "Return to main game line to scrub"; return to main line; verify re-enabled |
| Mobile stacked equivalent renders in correct order | SC-5 | Responsive visual layout | View `/analysis?game_id=X&ply=Y` at <1024px; verify stack: Board+EvalBar → EvalChart → overlay → engine → move list → controls |
| Game-card / flaw-card single Analyze button replaces old pairs; Game modal gone | SC-1 / D-09 | Cross-page navigation + deletion verification | Confirm analyzed game card shows one `Search`-icon Analyze; flaw card shows one Analyze; no `Game` modal opens anywhere |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
