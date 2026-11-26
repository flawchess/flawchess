---
phase: "251"
slug: "blunder-check-schedule-streak-and-leaderboards-seed-261108-d"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| 251-01-T1 | 01 | 1 | D-03, D-05, D-07, D-17, D-21 schema; tracer: a BC session started over HTTP carries the user's local session day; every BC fixture writes a session day | T-251-03, T-251-04 | DB CHECKs refuse impossible sizes | router + migration | `uv run alembic upgrade head && uv run alembic check`; `uv run pytest tests/routers/test_blunder_check_sessions.py tests/services/test_blunder_check_selection.py tests/repositories/test_blunder_check_repository.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py -x`; `uv run pytest tests/repositories/test_train_repository.py tests/routers/test_train.py tests/scripts/test_reset_train_state.py -k "settings or reset" -x` | ✅ (tracer added to an existing file) | ✅ green |
| 251-01-T2 | 01 | 1 | D-01 (BC session expiry keeps shown windows, done-in-window, complete_session reports the first close) | T-251-02 | lookups scoped by user id (and session id) | repository/router | `uv run pytest tests/repositories/test_blunder_check_session_day.py tests/repositories/test_blunder_check_repository.py tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/services/test_blunder_check_selection.py -x` | ✅ (created) (new file + seed helper) | ✅ green |
| 251-12-T1 | 12 | 2 | D-02, D-03 tracer (puzzle-only completion waits for BC; BC off ticks); day_is_complete truth table; SHIELD_CAP gate; pre-existing puzzle-only tests restated with BC size 0 | T-251-01 | idempotent credit per day | router + unit + regression | `uv run pytest tests/routers/test_train_two_mode_streak.py tests/services/test_train_scheduler.py -x`; `uv run pytest tests/repositories/test_train_repository.py tests/routers/test_train.py tests/test_guest_auth.py tests/services/test_train_reminder_service.py tests/routers/test_push.py -x` | ✅ (created) (new file) | ✅ green |
| 251-12-T2 | 12 | 2 | D-02, D-04 (BC compose uses the per-user size, size 0 is 409, BC finish completes the day once) | T-251-32 | finish credits only the caller's own session day | router + service | `uv run pytest tests/routers/test_train_two_mode_streak.py tests/repositories/test_train_two_mode_streak.py -x`; `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/services/test_blunder_check_selection.py tests/repositories/test_blunder_check_session_day.py -x` | ✅ (created) | ✅ green |
| 251-12-T3 | 12 | 2 | D-02, D-18 launch-day matrix: double credit, settled before launch, streak holder on launch day, off-day credit, pool eligibility by BC size; reset tool clears the credit key | T-251-01 | idempotent credit per day | repository | `uv run pytest tests/repositories/test_train_two_mode_streak.py tests/repositories/test_train_repository.py tests/routers/test_train.py tests/scripts/test_reset_train_state.py -x`; `uv run ty check app/ tests/ scripts/` | ✅ (created) | ✅ green |
| 251-02-T1 | 02 | 3 | D-14, D-22, D-25 (live BC boards, 18-window Score %) | T-251-05, T-251-07 | guests and hidden users never on others' boards | service/router | `uv run pytest tests/services/test_train_leaderboard.py tests/routers/test_train_leaderboard.py -x` | ✅ (add) | ✅ green |
| 251-02-T2 | 02 | 3 | checkpoint:decision (board keys, feature-route step ID) | — | — | decision | n/a (human decision) | — | ✅ green |
| 251-02-T3 | 02 | 3 | D-14, D-15, D-23 (finalize four boards, unclaimed order, per-board tallies, claims) | T-251-06 | claims scoped to the caller | repository/service | `uv run pytest tests/repositories/test_train_medals_finalization.py tests/repositories/test_train_medals_repository.py tests/services/test_train_medals.py tests/routers/test_train_medals.py tests/services/test_train_leaderboard.py -x` | ✅ (add) | ✅ green |
| 251-03-T1 | 03 | 3 | D-18 (guests and non-beta users on every BC route), D-17 (stored level fallback) | T-251-09, T-251-10 | routes stay user-scoped after the gate is removed | router + unit | `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/services/test_blunder_check_selection.py -x` | ✅ (replace 403 tests) | ✅ green |
| 251-03-T2 | 03 | 3 | D-16 (cooldown both directions, waiting count mirrors composition, due date untouched) | — | N/A | repository | `uv run pytest tests/repositories/test_cross_mode_cooldown.py tests/repositories/test_train_repository.py tests/repositories/test_blunder_check_repository.py tests/services/test_blunder_check_selection.py tests/services/test_blunder_check_candidates.py -x` | ✅ (created) | ✅ green |
| 251-04-T1 | 04 | 4 | D-04, D-05, D-07, D-21 (settings round-trip, both-0 is 422, old-PWA body, notice cleared, off completes the day); exact-dict settings tests updated | T-251-12 | input validated server-side and by DB CHECK | router | `uv run pytest tests/routers/test_train_settings_two_modes.py tests/routers/test_train.py -x`; `uv run pytest tests/repositories/test_train_repository.py tests/test_migration_244_sr_ladder_due_dates.py -x` | ✅ (created) | ✅ green |
| 251-04-T2 | 04 | 4 | D-06, D-01 (resize: to 0, at or below done, shorten, extend, after completion, no re-serve) | T-251-15 | resize edits only the caller's open session | service | `uv run pytest tests/services/test_train_settings_service.py -k resize -x` | ✅ (created) | ✅ green |
| 251-04-T3 | 04 | 4 | D-04 (puzzles off: no compose, 0 waiting, open session closed, BC alone completes the day) | T-251-13 | N/A | service | `uv run pytest tests/services/test_train_settings_service.py -k puzzles_off -x` | ✅ (created) | ✅ green |
| 251-05-T1 | 05 | 4 | D-14, D-22, D-24, D-25 (mode switch, remembered mode, guest view) | T-251-16 | stored mode parsed against the union | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainLeaderboardCard.test.tsx src/lib/__tests__/trainLeaderboard.test.ts` | ✅ (add) | ✅ green |
| 251-05-T2 | 05 | 4 | D-15, D-24 (medal dialog grouped by week, score-screen link) | — | N/A | component | `npm --prefix frontend test -- src/components/train/medals src/lib/__tests__/trainMedals.test.ts src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx src/components/admin` | ✅ (created) (end-screen test) | ✅ green |
| 251-06-T1 | 06 | 5 | D-13, D-09 (per-mode state, pending sum, 0 on an unscheduled day); progress key-set tests updated | T-251-19 | response carries only the caller's own counts | router | `uv run pytest tests/routers/test_train_progress_modes.py -k pending_count -x`; `uv run pytest tests/routers/test_train.py -k progress -x` | ✅ (created) | ✅ green |
| 251-06-T2 | 06 | 5 | D-09, D-10, D-17, D-19, D-20, D-21 (states, first-session flags, needs_level, notice and dismissal) | T-251-18 | dismiss writes only the caller's row | repository/router | `uv run pytest tests/repositories/test_train_progress_modes.py tests/routers/test_train_progress_modes.py tests/routers/test_train.py -x` | ✅ (created) | ✅ green |
| 251-06-T3 | 06 | 5 | Discretion: reminder fires while any required mode is pending | T-251-20 | N/A | service | `uv run pytest tests/services/test_train_reminder_service.py -x` | ✅ (add) | ✅ green |
| 251-07-T1 | 07 | 6 | D-18, D-20 retirement (BC from the Today card, drill under Today); page and card tests updated for the provider and plan 06 fields | T-251-21, T-251-22 | N/A | page | `npm --prefix frontend test -- src/pages/__tests__/Train.blunderCheckToday.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx src/pages/__tests__/Train.solveLoop.test.tsx src/pages/__tests__/Train.subnav.test.tsx src/components/train/__tests__/TrainStreakCard.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ (created) | ✅ green |
| 251-07-T2 | 07 | 6 | D-11 (subnav, route) | — | N/A | unit | `npm --prefix frontend test -- src/lib/__tests__/trainRoute.test.ts src/pages/__tests__/Train.subnav.test.tsx` | ✅ (update) | ✅ green |
| 251-13-T1 | 13 | 7 | D-08, D-09, D-13 (launcher rows in four states, nav badge) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeLauncherRow.test.tsx src/components/train/__tests__/TrainStreakCard.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx src/App.test.tsx src/pages/__tests__ src/components/train/blunder-check` | ✅ (created) (row test file) | ✅ green |
| 251-13-T2 | 13 | 7 | Settings hook optional fields, analytics registry | T-251-23, T-251-33 | literal-only analytics values; optional fields validated server-side | unit | `npm --prefix frontend test -- src/hooks/__tests__/useTrainSettings.test.ts` | ✅ (update) | ✅ green |
| 251-08-T1 | 08 | 8 | D-20, D-17 (level step once, saved before compose) | T-251-24 | N/A | component | `npm --prefix frontend test -- src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckLevelStep.test.tsx` | ✅ (created) | ✅ green |
| 251-08-T2 | 08 | 8 | D-21 (launch notice and dismissal) | T-251-25 | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainStreakCard.test.tsx` | ✅ (add) | ✅ green |
| 251-09-T1 | 09 | 9 | D-08, D-04 (BC size slider through one shared draft) | T-251-26 | no lost settings edit | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeSettings.test.tsx src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ (created) | ✅ green |
| 251-09-T2 | 09 | 9 | D-05, D-09, D-10, D-17 (Off, clamp and hint, How it works, level picker, Turn on, desktop layout) | T-251-27 | UI never sends both sizes at 0 | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeSettings.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx src/components/train/__tests__/TrainScheduleSettings.test.tsx src/components/train/__tests__/TrainStreakCard.test.tsx` | ✅ (created) | ✅ green |
| 251-10-T1 | 10 | 10 | D-12 (score-screen hand-off both ways) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainScoreScreen.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx src/components/admin` | ✅ (add) | ✅ green |
| 251-10-T2 | 10 | 10 | D-21 (feature-route step appended on both sides) | T-251-28 | step validated by the Literal | unit | `uv run pytest tests/test_feature_route.py -x`; `npm --prefix frontend test -- src/lib/__tests__/featureRoute.test.ts` | ✅ (add) | ✅ green |
| 251-10-T3 | 10 | 10 | D-19, D-21 (pitch line, discovery dot on the BC row) | — | N/A | component | `npm --prefix frontend test -- src/components/train/__tests__/TrainModeLauncherRow.test.tsx src/pages/__tests__` | ✅ (created by 13) | ✅ green |
| 251-11-T1 | 11 | 11 | Pre-merge gate (all of the above, full suites) | T-251-30 | full gate green before merge | all | CLAUDE.md pre-merge gate (backend and frontend blocks) | ✅ | ✅ green |
| 251-11-T2 | 11 | 11 | D-18 launch walk (human-check), serial suite, validation record | — | N/A | manual + record | `grep -c "^## Gate Results" 251-VALIDATION.md` | ✅ | ✅ green |

Plan order (revision 2026-11-18): plan 12 was split from plan 01 and plan 13 from plan 07; plans 07, 13, 08, 09 and 10 run
serially (one per wave) so no frontend plan's whole-tree lint, build or knip runs against a sibling's in-progress edits.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Status basis (251-11, 2026-11-19): every row is green because each plan's own summary recorded its focused command passing
and the final full backend suite (7094 passed, 19 skipped) and full frontend suite (373 files, 6605 tests) passed on the
phase tip. 251-02-T2 was a decision, recorded in the 251-02 summary (board keys, feature-route step ID `blunder-check`).
Every `-k` filter in the map was re-collected on the tip and selects tests (resize 7, puzzles_off 4, pending_count 5,
progress 3); no command needed a rename.

---

## Wave 0 Requirements

- [x] `tests/blunder_check_seed.py` — shared fixture `seed_completed_blunder_check_session` to create a completed blunder-check session on a given local day (251-01-T2)
- [x] `tests/repositories/test_train_two_mode_streak.py` — launch-day cases listed in CONTEXT Specifics (251-12-T3)
- [x] `tests/routers/test_train_two_mode_streak.py` — HTTP tracer for the both-modes rule (251-12-T1)
- [x] `frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx` — launcher row states (251-13-T1)
- [x] `tests/repositories/test_cross_mode_cooldown.py` — cooldown tests for both modes (251-03-T2)
- [x] `tests/repositories/test_train_medals_finalization.py` — finalization with blunder-check windows (251-02-T3)
- [x] Frontend tests for the new Today card states, replacing the `BlunderCheckTab.test.tsx` start-screen cases (251-07-T1, 251-07-T2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Today card on phone width across a day boundary | D-08..D-12, D-18 | Layout and dev-clock day rollover need a real browser; D-18 has no prod rehearsal | Run the app locally, set the dev clock, walk the Today card through pending, one mode done, both done, and next day, at phone width |

---

## Gate Results

Run by plan 251-11 on the phase tip (worktree branch, base `4d80b6ae1`), 2026-11-19. Fresh worktree set up with
`uv sync --locked --group maia-inference`, `uv sync --project analysis` and `npm ci`.

- 2026-11-19 `uv run ruff format app/ tests/ scripts/ analysis/`: 629 files left unchanged (PASS)
- 2026-11-19 `uv run ruff check . --fix`: All checks passed (PASS)
- 2026-11-19 `uv run ty check app/ tests/ scripts/`: All checks passed (PASS)
- 2026-11-19 `uv run --project analysis --with ty ty check analysis/`: All checks passed (PASS)
- 2026-11-19 `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: 1628 functions scanned, no breaches (PASS)
- 2026-11-19 `uv run pytest -n auto -x`: 7094 passed, 19 skipped in 184s (PASS)
- 2026-11-19 `npm --prefix frontend run lint`: clean (PASS)
- 2026-11-19 `npm --prefix frontend run build` (tsc -b plus vite): clean (PASS)
- 2026-11-19 `npm --prefix frontend test -- --run`: 373 files, 6605 tests passed (PASS)
- 2026-11-19 `npm --prefix frontend run knip`: exit 0, two pre-existing configuration hints (PASS)
- 2026-11-19 generated files: no `scripts/gen_*.py` source registry and nothing under `frontend/src/generated/` changed in this phase, so no regeneration was needed (PASS)
- NOT RUN here, orchestrator work: the serial `uv run pytest` and the browser launch walk (see Human Checks below).

No gate step modified a file; no gate fix was needed.

## Follow-ups

Open items carried from the plan summaries; none blocks the merge.

- 251-03: `drill_sessions` has no `(user_id, session_date)` index (only the primary key and the partial unique open
  index), so `puzzle_cooled_pairs` and `completed_session_in_window` scan by user. Low urgency; add an index in a later
  migration if the pg_stat_statements shapes show cost.
- 251-03: the dev DB has no foreign supply at levels 1000 and 2000 (0 of 18 windows), but a prod probe found about
  3.8k to 4.9k evaluated games per +-150 rating band in a 2% sample, so this is a dev artifact. Keep
  `FOREIGN_SAMPLE_PERCENT` as is. 251-03 also recommends keeping 18 as the slider maximum on latency grounds.
- 251-04: an extension can place a second, non-overlapping window on a game already used in the same session. D-01
  (serve-once) still holds across sessions.
- 251-12: accepted assumption A8. A user with a sparse weekday mask who splits modes across days can lose that day
  (about 3.6% of prod users). The owner should be aware of this at launch.
- 251-05 and 251-08: Phase 249's D-19 analytics-import scan in `BlunderCheckTab.test.tsx` now exempts
  `BlunderCheckEndScreen.tsx`, `BlunderCheckTab.tsx` and everything under `__tests__`. The Umami data-attribute check
  still covers them.
- 251-11: the CHANGELOG `[Unreleased]` entries are written; the `/gsd-ship` or merge step must keep them (docs/git-workflow.md).
- Visual layouts (launcher rows, settings two-column grid, medal dialog week grouping, level step, launch notice,
  continue button) are `human_judgment` items covered by the launch walk below.

## Human Checks (for the orchestrator to harvest)

1. Launch walk (browser MCP, orchestrator only). Start the dev stack, sign in as a registered non-beta user with a
   streak, set the phone viewport (390x844), and use the dev clock (TrainDevClock) to walk the Today card: both rows
   pending with red badges; Start Blunder Check runs the drill immersive and returns to Today; puzzles done shows the
   checkmark while the flame waits for blunder check; blunder check done ticks the streak once; advance the dev clock
   one day and confirm a missed day drains a freeze; set blunder check to Off in its settings row and confirm puzzles
   alone complete the next day; the launch notice shows and dismisses; the leaderboard switch opens Blunder check from
   the BC score screen; the nav badge equals the two rows' badges. Repeat the Start path as a fresh guest (level step
   once, then straight into the drill on the next Start). Desktop (1440 wide): Today card left, settings right.
   Screenshots go to `temp/251-uat/`.
2. Serial suite (orchestrator, long run): `uv run pytest` serially from its own shell (`setsid nohup` plus Monitor per
   project memory) before the release; serial CI catches isolation bugs that `-n auto` hides.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
