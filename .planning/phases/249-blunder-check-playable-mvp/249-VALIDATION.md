---
phase: "249"
slug: "blunder-check-playable-mvp"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-10"
---

# Phase 249 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from 249-RESEARCH.md
> "Validation Architecture"; the per-task map is filled once plans exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py` (per-worker cloned DBs); `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/services/test_blunder_check_rules.py tests/routers/test_blunder_check.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `npm --prefix frontend test -- --run` |
| **Estimated runtime** | ~30 s quick, ~6 min full backend |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module
- **After every plan wave:** Run `uv run pytest -n auto -x` + `npm --prefix frontend test -- --run`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) must be green
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 249-TBD | TBD | TBD | D-01..D-19 | TBD | see RESEARCH test map | unit / integration / router / vitest | see RESEARCH "Phase Requirements -> Test Map" | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `seed_blunder_check_game(...)` test helper: game with contiguous `game_positions`, `full_evals_completed_at`,
      `best_move` at blunder plies, user-side severity-2 `game_flaws` with Maia pairs; `finally` cleanup; unique user ids
- [ ] Deterministic RNG injection point in the session composer
- [ ] Beta user fixture (register + flip `beta_enabled`)
- [x] Prod latency probe (done by the orchestrator, 249-RESEARCH "Prod Latency Probe")

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drill feel: lead-in pace, arrow prompt, timer, forfeit animation and sounds | D-12, D-13 | Visual/audio timing | Agent-run browser UAT with a beta-enabled dev user (project memory: run human-action checkpoints yourself) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
