---
phase: "251"
slug: "blunder-check-schedule-streak-and-leaderboards-seed-261108-d"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-18"
---

# Phase 251 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `251-RESEARCH.md` § Validation Architecture. The planner fills the Per-Task Verification Map.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-xdist locally), vitest (frontend) |
| **Config file** | `pyproject.toml`, `tests/conftest.py` (per-worker DB cloned from a migrated template, auto-refreshes on a new Alembic head); `frontend/vite*.config` |
| **Quick run command** | `uv run pytest tests/services/test_train_scheduler.py tests/repositories/test_train_repository.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | quick ~30 seconds, full backend ~3-5 minutes, frontend block ~2-3 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module (single files, serial)
- **After every plan wave:** Run `uv run pytest -n auto -x` plus the frontend block
- **Before `/gsd-verify-work`:** Full pre-merge gate from CLAUDE.md must be green (ruff, ty, nesting-depth script, full backend suite, frontend block), plus one serial `uv run pytest` run before release
- **Max feedback latency:** 60 seconds for the per-task quick command

---

## Per-Task Verification Map

Decision-level map from research. Task IDs are assigned by the planner.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-02 | — | N/A | unit | `uv run pytest tests/services/test_train_scheduler.py -x` | ✅ (add cases) | ⬜ pending |
| TBD | TBD | TBD | D-02 (launch day: puzzles done, BC pending, no tick; BC done, tick) | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py -k day_completion -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | D-02 (second completion on a complete day mints no freeze) | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py -k double_credit -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04 / D-06 (resize: to 0, to <= done, shorten, extend, after completion) | — | N/A | repository/router | `uv run pytest tests/routers/test_blunder_check_sessions.py -k resize -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | D-05 (both 0 gives 422, DB CHECK holds) | — | Input validated server-side and by DB CHECK | router | `uv run pytest tests/routers/test_train.py -k settings -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | Discretion: day settled before launch stays as judged | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py -k settled_before_launch -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Discretion: no-puzzle-material user, eligibility stamped by BC size | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py -k pool_eligible_bc -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Discretion: reminder skips only when the day is complete | — | N/A | service | `uv run pytest tests/services/test_train_reminder_service.py -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | D-13 (pending sum, 0 on an unscheduled day) | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py -k pending_count -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-16 (cooldown both directions, due item resurfaces, waiting count mirrors composition) | — | N/A | repository | `uv run pytest tests/repositories/test_train_repository.py tests/repositories/test_blunder_check_repository.py -k cooldown -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-17 (stored level used as fallback, ignored with rated games) | — | N/A | unit | `uv run pytest tests/services/test_blunder_check_selection.py -k level -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | D-14 / D-22 (BC boards rank, 18-window qualify, finalization writes four boards, unclaimed and tally read back) | — | N/A | service/repository | `uv run pytest tests/services/test_train_leaderboard.py tests/repositories/test_train_medals_finalization.py -x` | ✅ (add) | ⬜ pending |
| TBD | TBD | TBD | D-18 (non-beta and guest users reach every BC route) | — | Routes stay user-scoped after the beta gate is removed | router | `uv run pytest tests/routers/test_blunder_check_sessions.py -k guest -x` | ✅ (replace 403 tests) | ⬜ pending |
| TBD | TBD | TBD | D-08..D-12, D-19..D-21, D-24 (Today card rows and states, level step once, notice dismiss, hand-off, mode memory) | — | N/A | component | `cd frontend && npx vitest run src/components/train` | ✅ partial | ⬜ pending |
| TBD | TBD | TBD | Gate: exactly one SHIELD_CAP clamp in `app/` | — | N/A | unit | `uv run pytest tests/services/test_train_scheduler.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/blunder_check_seed.py` — shared fixture to create a completed blunder-check session on a given local day
- [ ] `tests/repositories/test_train_repository.py` — launch-day cases listed in CONTEXT Specifics
- [ ] Cooldown tests for both modes (`test_train_repository.py`, `test_blunder_check_repository.py`)
- [ ] `tests/repositories/test_train_medals_finalization.py` — finalization with blunder-check windows
- [ ] Frontend tests for the new Today card states (replacing the `BlunderCheckTab.test.tsx` start-screen cases)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Today card on phone width across a day boundary | D-08..D-12, D-18 | Layout and dev-clock day rollover need a real browser; D-18 has no prod rehearsal | Run the app locally, set the dev clock, walk the Today card through pending, one mode done, both done, and next day, at phone width |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
