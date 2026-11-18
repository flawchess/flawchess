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

Filled by the planner with the real plan tasks (2026-11-18). Commands are the tasks' `<automated>` verify commands.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 251-01-T1 | 01 | 1 | D-02, D-03, D-07 tracer (puzzle-only completion waits for BC; BC off ticks); SHIELD_CAP gate | T-251-01, T-251-04 | DB CHECKs refuse impossible sizes | router + unit | `uv run alembic upgrade head && uv run alembic check`; `uv run pytest tests/routers/test_train_two_mode_streak.py tests/services/test_train_scheduler.py -x` | ❌ W0 (new file) | ⬜ pending |
| 251-01-T2 | 01 | 1 | D-01, D-02 (BC session day, expiry, done-in-window, finish completes the day once) | T-251-02 | lookups scoped by (session id, user id) | repository/router | `uv run pytest tests/repositories/test_blunder_check_session_day.py tests/repositories/test_blunder_check_repository.py tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py -x` | ❌ W0 (new file + seed helper) | ⬜ pending |
| 251-01-T3 | 01 | 1 | D-02 launch-day matrix: double credit, settled before launch, streak holder on launch day, off-day credit, pool eligibility by BC size | T-251-01 | idempotent credit per day | repository + unit | `uv run pytest tests/repositories/test_train_two_mode_streak.py tests/services/test_train_scheduler.py tests/repositories/test_train_repository.py -x` | ❌ W0 | ⬜ pending |
| 251-02-T1 | 02 | 2 | D-14, D-22, D-25 (live BC boards, 18-window Score %) | T-251-05, T-251-07 | guests and hidden users never on others' boards | service/router | `uv run pytest tests/services/test_train_leaderboard.py tests/routers/test_train_leaderboard.py -x` | ✅ (add) | ⬜ pending |
| 251-02-T2 | 02 | 2 | checkpoint:decision (board keys, feature-route step ID) | — | — | decision | n/a (human decision) | — | ⬜ pending |
| 251-02-T3 | 02 | 2 | D-14, D-15, D-23 (finalize four boards, unclaimed order, per-board tallies, claims) | T-251-06 | claims scoped to the caller | repository/service | `uv run pytest tests/repositories/test_train_medals_finalization.py tests/repositories/test_train_medals_repository.py tests/services/test_train_medals.py tests/routers/test_train_medals.py tests/services/test_train_leaderboard.py -x` | ✅ (add) | ⬜ pending |
| 251-03-T1 | 03 | 2 | D-18 (guests and non-beta users on every BC route), D-17 (stored level fallback) | T-251-09, T-251-10 | routes stay user-scoped after the gate is removed | router + unit | `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/services/test_blunder_check_selection.py -x` | ✅ (replace 403 tests) | ⬜ pending |
| 251-03-T2 | 03 | 2 | D-16 (cooldown both directions, waiting count mirrors composition, due date untouched) | — | N/A | repository | `uv run pytest tests/repositories/test_cross_mode_cooldown.py tests/repositories/test_train_repository.py tests/repositories/test_blunder_check_repository.py tests/services/test_blunder_check_selection.py tests/services/test_blunder_check_candidates.py -x` | ❌ W0 | ⬜ pending |
| 251-04-T1 | 04 | 3 | D-04, D-05, D-07, D-21 (settings round-trip, both-0 is 422, old-PWA body, notice cleared, off completes the day) | T-251-12 | input validated server-side and by DB CHECK | router | `uv run pytest tests/routers/test_train_settings_two_modes.py tests/routers/test_train.py -x` | ❌ W0 | ⬜ pending |
| 251-04-T2 | 04 | 3 | D-06, D-01 (resize: to 0, at or below done, shorten, extend, after completion, no re-serve) | T-251-15 | resize edits only the caller's open session | service | `uv run pytest tests/services/test_train_settings_service.py -k resize -x` | ❌ W0 | ⬜ pending |
| 251-04-T3 | 04 | 3 | D-04 (puzzles off: no compose, 0 waiting, open session closed, BC alone completes the day) | T-251-13 | N/A | service | `uv run pytest tests/services/test_train_settings_service.py -k puzzles_off -x` | ❌ W0 | ⬜ pending |
| 251-05-T1 | 05 | 3 | D-14, D-22, D-24, D-25 (mode switch, remembered mode, guest view) | T-251-16 | stored mode parsed against the union | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainLeaderboardCard.test.tsx src/lib/__tests__/trainLeaderboard.test.ts` | ✅ (add) | ⬜ pending |
| 251-05-T2 | 05 | 3 | D-15, D-24 (medal dialog grouped by week, score-screen link) | — | N/A | component | `npm --prefix frontend test -- src/components/train/medals src/lib/__tests__/trainMedals.test.ts src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx src/components/admin` | ❌ W0 (end-screen test) | ⬜ pending |
| 251-06-T1 | 06 | 4 | D-13, D-09 (per-mode state, pending sum, 0 on an unscheduled day) | T-251-19 | response carries only the caller's own counts | router | `uv run pytest tests/routers/test_train_progress_modes.py -k pending_count -x` | ❌ W0 | ⬜ pending |
| 251-06-T2 | 06 | 4 | D-09, D-10, D-17, D-19, D-20, D-21 (states, first-session flags, needs_level, notice and dismissal) | T-251-18 | dismiss writes only the caller's row | repository/router | `uv run pytest tests/repositories/test_train_progress_modes.py tests/routers/test_train_progress_modes.py tests/routers/test_train.py -x` | ❌ W0 | ⬜ pending |
| 251-06-T3 | 06 | 4 | Discretion: reminder fires while any required mode is pending | T-251-20 | N/A | service | `uv run pytest tests/services/test_train_reminder_service.py -x` | ✅ (add) | ⬜ pending |
| 251-07-T1 | 07 | 5 | D-18, D-20 retirement, D-11 (BC from the Today card, drill under Today) | T-251-21, T-251-22 | N/A | page | `npm --prefix frontend test -- src/pages/__tests__/Train.blunderCheckToday.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx` | ❌ W0 | ⬜ pending |
| 251-07-T2 | 07 | 5 | D-08, D-09, D-13 (launcher rows in four states, nav badge) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainStreakCard.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx src/pages/__tests__ src/components/train/blunder-check` | ✅ (add) | ⬜ pending |
| 251-07-T3 | 07 | 5 | D-11 (subnav, route), settings hook fields, analytics registry | T-251-23 | literal-only analytics values | unit | `npm --prefix frontend test -- src/lib/__tests__/trainRoute.test.ts src/pages/__tests__/Train.subnav.test.tsx src/hooks/__tests__/useTrainSettings.test.ts` | ✅ (update) | ⬜ pending |
| 251-08-T1 | 08 | 6 | D-20, D-17 (level step once, saved before compose) | T-251-24 | N/A | component | `npm --prefix frontend test -- src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckLevelStep.test.tsx` | ❌ W0 | ⬜ pending |
| 251-08-T2 | 08 | 6 | D-21 (launch notice and dismissal) | T-251-25 | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainStreakCard.test.tsx` | ✅ (add) | ⬜ pending |
| 251-09-T1 | 09 | 6 | D-08, D-04 (BC size slider through one shared draft) | T-251-26 | no lost settings edit | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeSettings.test.tsx src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx` | ❌ W0 | ⬜ pending |
| 251-09-T2 | 09 | 6 | D-05, D-09, D-10, D-17 (Off, clamp and hint, How it works, level picker, Turn on, desktop layout) | T-251-27 | UI never sends both sizes at 0 | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeSettings.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainStreakCard.test.tsx` | ❌ W0 | ⬜ pending |
| 251-10-T1 | 10 | 6 | D-12 (score-screen hand-off both ways) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainScoreScreen.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx src/components/admin` | ✅ (add) | ⬜ pending |
| 251-10-T2 | 10 | 6 | D-21 (feature-route step appended on both sides) | T-251-28 | step validated by the Literal | unit | `uv run pytest tests/test_feature_route.py -x`; `npm --prefix frontend test -- src/lib/__tests__/featureRoute.test.ts` | ✅ (add) | ⬜ pending |
| 251-10-T3 | 10 | 6 | D-19, D-21 (pitch line, discovery dot on the BC row) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeLauncherRow.test.tsx src/pages/__tests__` | ❌ W0 (if not created in 07) | ⬜ pending |
| 251-11-T1 | 11 | 7 | Pre-merge gate (all of the above, full suites) | T-251-30 | full gate green before merge | all | CLAUDE.md pre-merge gate (backend and frontend blocks) | ✅ | ⬜ pending |
| 251-11-T2 | 11 | 7 | D-18 launch walk (human-check), serial suite, validation record | — | N/A | manual + record | `grep -c "^## Gate Results" 251-VALIDATION.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/blunder_check_seed.py` — shared fixture to create a completed blunder-check session on a given local day (251-01-T2)
- [ ] `tests/repositories/test_train_two_mode_streak.py` — launch-day cases listed in CONTEXT Specifics (251-01-T3)
- [ ] `tests/repositories/test_cross_mode_cooldown.py` — cooldown tests for both modes (251-03-T2)
- [ ] `tests/repositories/test_train_medals_finalization.py` — finalization with blunder-check windows (251-02-T3)
- [ ] Frontend tests for the new Today card states, replacing the `BlunderCheckTab.test.tsx` start-screen cases (251-07-T1, 251-07-T2)

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
