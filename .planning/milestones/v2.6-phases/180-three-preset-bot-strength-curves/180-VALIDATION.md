---
phase: 180
slug: three-preset-bot-strength-curves
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 180 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node `*.check.mjs` engine-free assertion scripts (existing calibration pattern) + Python `pytest` for the fitter |
| **Config file** | none — `.check.mjs` scripts are run directly via `node`; pytest via `uv run pytest` |
| **Quick run command** | `node scripts/lib/<module>.check.mjs` (per changed module) |
| **Full suite command** | run all `scripts/lib/*.check.mjs` calibration checks + `uv run pytest tests/ -k calibration_anchor_fit` |
| **Estimated runtime** | ~5–15 seconds (engine-free logic layer); the real-engine pilot is separate and operator-timed |

---

## Sampling Rate

- **After every task commit:** Run the relevant `.check.mjs` for the module touched
- **After every plan wave:** Run all calibration `.check.mjs` scripts + the fitter pytest selection
- **Before `/gsd-verify-work`:** Full engine-free logic layer must be green
- **Max feedback latency:** 15 seconds (logic layer). The real-engine pilot (D-02b) is HUMAN-UAT and not on the automated sampling path.

---

## Per-Task Verification Map

*Seeded draft — the planner/executor refines Task IDs to match the final PLAN.md task breakdown. Nyquist coverage rule: no 3 consecutive tasks without an automated verify.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 180-01-01 | 01 | 1 | TBD | — | N/A | unit | `node scripts/lib/calibration-harness-internal-scale.check.mjs` | ❌ W0 | ⬜ pending |
| 180-01-02 | 01 | 1 | TBD | — | N/A | unit | `node scripts/lib/calibration-bot-cell-schedule.check.mjs` | ❌ W0 | ⬜ pending |
| 180-02-01 | 02 | 2 | TBD | — | N/A | unit | `uv run pytest tests/ -k fit_bot_cell_rating` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/lib/*.check.mjs` — engine-free fabricated-provider tests for INTERNAL_RATING windowing + two-pass bot-cell selection (mirror existing `calibration-anchor-schedule.check.mjs` pattern)
- [ ] `tests/` pytest coverage for the new `fit_bot_cell_rating` MLE + `G_preset` output shape
- [ ] Fabricated deterministic providers (no real engines) for the logic layer

*Frameworks already exist (Node runtime for `.check.mjs`, pytest for Python); no install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-engine pilot: sane ratings, correct INTERNAL_RATING windowing, both anchor families firing, `--resume` integrity | D-02b | Requires real Maia/Stockfish engines and wall-clock game play — cannot run in CI | Run the harness on 1–2 real cells at low N per the pilot plan; inspect the TSV/JSON for internal-scale bracketing and both `maiaNNNN` + `sfN` anchor rows |
| Full ~1,440-game overnight sweep + fitted per-preset curves + `G_preset` + findings note | D-01 | ~18–22h operator run, off the interactive critical path (folded-in HUMAN-UAT) | Operator runs the validated harness overnight, then runs the extended fitter and writes the findings note mirroring the 173 note |

---

## Validation Sign-Off

- [ ] All logic-layer tasks have `.check.mjs` / pytest automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (logic layer)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
