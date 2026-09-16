---
phase: "223"
slug: "bot-voice-immersive-bot-game-layout-seed-168-seed-167"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-15"
---

# Phase 223 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend only; this phase has no backend surface) |
| **Config file** | `frontend/vite.config.ts` (test block) + `frontend/src/vitest.setup.ts` |
| **Quick run command** | `( cd frontend && npx vitest run <changed test files> )` |
| **Full suite command** | `( cd frontend && npm run lint && npm run build && npm run knip && npm test -- --run )` |
| **Estimated runtime** | ~90 s for the vitest suite alone; ~4 min for the full frontend gate |

---

## Sampling Rate

- **After every task commit:** Run the changed test files with `npx vitest run`
- **After every plan wave:** Run the full frontend gate (lint, build, knip, test)
- **Before `/gsd-verify-work`:** Full suite must be green (last run at `5caa0454c`: 266 files / 4287 tests, all four legs exit 0)
- **Max feedback latency:** ~4 min (full gate)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 223-01-* | 01 | 1 | BOTVOICE-01/02 | — | N/A (no user input crosses a trust boundary) | unit | `npx vitest run src/lib/__tests__/botGameCopy.test.ts src/lib/__tests__/botLineTrigger.test.ts src/hooks/__tests__/useBotGameVoice.test.ts` | ✅ | ✅ green |
| 223-02-* | 02 | 2 | BOTVOICE-01/06 | — | N/A | unit | `npx vitest run src/lib/__tests__/botGameCopy.test.ts src/components/bots/__tests__/PersonaGrid.test.tsx` | ✅ | ✅ green |
| 223-03-* | 03 | 1 | BOTVOICE-07 | — | N/A | unit | (retired at UAT; `BoardSoundsSwitch` and its test deleted, see 223-06-SUMMARY deviation 5) | ❌ deleted | ⬜ n/a |
| 223-04-* | 04 | 3 | BOTVOICE-02/03 | — | N/A | unit | `npx vitest run src/lib/__tests__/botLineTrigger.test.ts src/hooks/__tests__/useBotGameVoice.test.ts` | ✅ | ✅ green |
| 223-05-* | 05 | 3 | BOTVOICE-04/05 | — | N/A | unit | `npx vitest run src/pages/__tests__/Bots.test.tsx src/components/bots/__tests__/BotGameMobileBar.test.tsx src/App.test.tsx` | ✅ | ✅ green |
| 223-06-01..03 | 06 | 4 | BOTVOICE-05 | T-223-06-02 | bot ELO rendered from `calibratedLabel`, never a rung (grep `rung` in BotGameDesktopLayout.tsx == 0) | unit + grep | `npx vitest run src/pages/__tests__/Bots.test.tsx src/components/board/__tests__/PlayerBar.test.tsx` | ✅ | ✅ green |
| 223-06-04 | 06 | 4 | BOTVOICE-04/05 | — | N/A | manual (browser UAT) | — | — | ✅ owner-verified 2026-09-16 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (vitest + testing-library already installed; 223-01 shipped its own Wave 0 contract tests in `d2bf9ae1b`).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 375px board is wider than before the phase; no vertical scrolling | BOTVOICE-04 | jsdom has no layout engine | 375x667 emulation, open a bot game, compare board width to the deployed build. Owner-verified by eye 2026-09-16, no numeric record. |
| Two-line copy budget never clips or grows the bubble slot | BOTVOICE-01 | pixel measurement | Render the longest line at 375px; slot must stay `min-h-12`. Verified; slot-growth defect fixed in `09abcebc1`. |
| Swing-line frequency and tone in a live game | BOTVOICE-02/03 | needs a real engine and a real game | Play a full game; expect a few swing lines, none mean, none claiming foresight. Verified across two fix rounds (`caa1208bc`, `2e4663d80`). |
| Bot draw offer accepted/declined from the bubble | BOTVOICE-05 | the offer gate (dead-equal past move 30) rarely fires | Not observed live; wiring unit-tested on both breakpoints. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 223s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (status stays `draft`; `/gsd-validate-phase 223` sets `validated`)
