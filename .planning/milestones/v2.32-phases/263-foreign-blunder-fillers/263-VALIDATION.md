---
phase: "263"
slug: "foreign-blunder-fillers"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-23"
validated: "2026-11-23"
---

# Phase 263 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from
> `263-RESEARCH.md` § Validation Architecture; the planner fills the per-task map.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest-asyncio, xdist) for the backend; vitest for the frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py` (template DB per xdist worker); `frontend/package.json` |
| **Quick run command** | `uv run pytest tests/repositories/test_train_foreign.py -x` (the touched test file, serial) |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | quick about 30 seconds; full backend suite a few minutes with `-n auto` |

---

## Sampling Rate

- **After every task commit:** run the touched test file(s) only, serial
- **After every plan wave:** `uv run pytest -n auto -x` plus `npm test -- --run` in `frontend/`
- **Before `/gsd-verify-work`:** the full pre-merge gate from `CLAUDE.md`, plus one serial run of
  `tests/routers/test_train.py` and the migration test (serial CI hides isolation bugs that
  `-n auto` does not)
- **Max feedback latency:** 60 seconds for the per-task sample

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 263-01-T1 | 01 | 1 | setup (worktree, seed helper) | T-263-SC | no `.env` read; lockfile-only install | infra | `uv run pytest tests/routers/test_blunder_check_points_migration.py -q` | ✅ | ✅ green |
| 263-01-T2 | 01 | 1 | D-01, D-05, D-06 (draw read path, suite seam) | T-263-03 | guests and own games never returned; stub on by default | repo integration | `uv run pytest tests/repositories/test_train_foreign.py tests/services/test_train_pool.py -x -q` | ❌ W0 (created by the task) | ✅ green |
| 263-01-T3 | 01 | 1 | D-01, D-02, D-05, D-06, D-07, D-14, D-15, D-17 | T-263-01, T-263-02, T-263-04, T-263-05 | wire game_id None; solver-scoped WHERE | repo integration (tracer, end to end) | `uv run pytest tests/repositories/test_train_foreign.py -x -q` | ✅ (after T2) | ✅ green |
| 263-02-T1 | 02 | 1 | D-04, D-11, D-12, D-13 | T-263-06 | neutral copy, nothing marks a puzzle pre-solve | vitest unit | `npm --prefix frontend test -- --run src/lib/__tests__/trainBotCopy.test.ts` | ✅ | ✅ green |
| 263-02-T2 | 02 | 1 | D-04, D-13 | T-263-07 | D-13 sentence only on loaded progress | vitest component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainStartScreen.test.tsx src/components/train/__tests__/TrainScoreScreen.test.tsx` | ✅ | ✅ green |
| 263-02-T3 | 02 | 1 | D-04, D-12 | — | — | lint + build + vitest + knip | `npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend test -- --run && npm --prefix frontend run knip` | ✅ | ✅ green |
| 263-03-T1 | 03 | 2 | D-07, D-08 | T-263-08, T-263-09 | owner-keyed reads only for the solver's own session rows | repo integration | `uv run pytest tests/repositories/test_train_foreign.py -x -q` | ✅ (after 263-01) | ✅ green |
| 263-03-T2 | 03 | 2 | D-01, D-02, D-05, D-06, D-14, D-15, D-16, D-17 | T-263-10 | guests' and the solver's games never drawn | unit + repo integration | `uv run pytest tests/services/test_train_foreign.py tests/repositories/test_train_foreign.py -x -q` | ❌ W0 (services file created by the task) | ✅ green |
| 263-04-T1 | 04 | 2 | D-21 | T-263-11 | neutral footer from game_info, no library fetch | vitest component | `npm --prefix frontend test -- --run src/components/train/__tests__/TrainReveal.test.tsx src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx` | ✅ | ✅ green |
| 263-04-T2 | 04 | 2 | D-10, D-20, D-21 | T-263-12, T-263-13 | Analyze opens the position only; neutral move labels | vitest + build | `npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend test -- --run && npm --prefix frontend run knip` | ✅ | ✅ green |
| 263-05-T1 | 05 | 2 | D-18 | T-263-14 | positive accuracy source list | repo | `uv run pytest tests/repositories/test_train_leaderboard_repository.py tests/services/test_train_leaderboard.py tests/routers/test_train_leaderboard.py -x -q` | ✅ | ✅ green |
| 263-05-T2 | 05 | 2 | D-19 | T-263-15 | aggregate counts only | repo + layout harness | `uv run pytest tests/test_admin_activity_stats.py -x -q -k difficulty` and `npm --prefix frontend run check:activity-layout` | ✅ | ✅ green |
| 263-06-T1 | 06 | 3 | D-09, D-20, D-21 | T-263-16, T-263-17 | — | ty + existing reveal tests | `uv run ty check app/ && uv run pytest tests/routers/test_train.py -x -q -k reveal` | ✅ | ✅ green |
| 263-06-T2 | 06 | 3 | D-09, D-10, D-20, D-21 | T-263-16, T-263-17, T-263-18 | no owner username, email or id in the reveal body; game_id null | router | `uv run pytest tests/routers/test_train_foreign.py -x -q` | ❌ W0 (created by the task) | ✅ green |
| 263-07-T1 | 07 | 4 | D-02 (tests onto the foreign stage, old code) | — | — | suite | `uv run pytest -n auto -x -q tests/repositories/test_train_repository.py tests/routers/test_train.py tests/routers/test_train_two_mode_streak.py tests/routers/test_train_settings_two_modes.py tests/repositories/test_train_foreign.py` | ✅ | ✅ green |
| 263-07-T2 | 07 | 4 | D-02, D-03 | T-263-22, T-263-29 | eligibility only for a written session | suite + mutation check | `uv run pytest -n auto -x -q tests/repositories/test_train_repository.py tests/routers/test_train.py tests/repositories/test_train_foreign.py tests/routers/test_train_foreign.py tests/routers/test_train_two_mode_streak.py tests/routers/test_train_settings_two_modes.py tests/repositories/test_cross_mode_cooldown.py tests/test_imports_router.py` | ✅ | ✅ green |
| 263-08-T1 | 08 | 5 | D-03, D-08 (legacy rows inert) | T-263-19, T-263-20, T-263-21 | — | repo + suites | `uv run pytest tests/repositories/test_train_legacy_filler.py -x -q` | ❌ W0 (created by the task) | ✅ green |
| 263-08-T2 | 08 | 5 | D-03 (files deleted) | — | — | file absence + suites | `uv run pytest -n auto -x -q tests/services tests/repositories tests/routers` | ✅ | ✅ green |
| 263-09-T1 | 09 | 6 | D-04, D-08, D-12, D-13 | T-263-25 | lazy completion only for the solver's own open session | repo + router | `uv run pytest -n auto -x -q tests/repositories/test_train_repository.py tests/routers/test_train.py tests/repositories/test_train_legacy_filler.py tests/repositories/test_train_foreign.py tests/routers/test_train_foreign.py` | ✅ | ✅ green |
| 263-09-T2 | 09 | 6 | D-03 / D-04 one-way confirm (sharp_puzzle_id) | T-263-23 | — | checkpoint:decision | n/a (owner answer) | — | ✅ green (owner answered drop, 2026-11-23) |
| 263-09-T3 | 09 | 6 | D-03, D-04 | T-263-23, T-263-24 | downgrade deletes source 3 rows first | migration round trip | `uv run pytest tests/test_phase_263_migration.py -x -q` then serial with `tests/routers/test_train.py` | ❌ W0 (created by the task) | ✅ green |
| 263-10-T1 | 10 | 7 | D-01 to D-21 (gate) | T-263-28 | — | full pre-merge gate + serial run + phase greps | CLAUDE.md pre-merge gate; `uv run pytest tests/routers/test_train.py tests/test_phase_263_migration.py tests/repositories/test_train_legacy_filler.py tests/routers/test_train_foreign.py -x -q` | ✅ | ✅ green |
| 263-10-T2 | 10 | 7 | docs (CHANGELOG, EXPLAIN SQL, UAT list) | T-263-26, T-263-27 | dev DB untouched by executors | file checks | `grep -c "EXPLAIN (ANALYZE, BUFFERS)" .planning/phases/263-foreign-blunder-fillers/263-PROD-EXPLAIN.sql` | ❌ (created by the task) | ✅ green |
| 263-V-T1 | validate | post | D-04, D-08 (T-263-25 negative: untouched open session with nothing servable stays open, no streak day) | T-263-25 | lazy completion needs at least one solve | repo integration | `uv run pytest tests/repositories/test_train_legacy_filler.py::test_resume_leaves_untouched_session_with_nothing_servable_open -q` | ✅ | ✅ green |
| 263-V-T2 | validate | post | test isolation (review IN-07): exact-count foreign tests run the band step alone | — | — | fixture `real_foreign_band_draw` | `uv run pytest tests/repositories/test_train_foreign.py tests/routers/test_train_foreign.py -q` | ✅ | ✅ green |

Decision to test mapping: see `263-RESEARCH.md` § Validation Architecture, "Phase Requirements -> Test Map".

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/conftest.py` — autouse stub of the foreign draw seam `_stub_foreign_draw` and the opt-in
      `real_foreign_draw` (sample percent 100) (263-01 T2); committed pool fixture `foreign_filler_pool` with
      finally-cleanup (263-07 T1, replaces the per-file sharp filler fixtures)
- [x] `tests/repositories/test_train_foreign.py` — draw seam (263-01 T2), tracer (263-01 T3), resume / completion / draw decisions (263-03)
- [x] `tests/services/test_train_foreign.py` — pure pick tests (263-03 T2)
- [x] `tests/routers/test_train_foreign.py` — wire and reveal tests (263-06 T2)
- [x] `tests/repositories/test_train_legacy_filler.py` — legacy filler rows (263-08 T1)
- [x] `tests/test_phase_263_migration.py` — both phase migrations: chain, round trips, data step (263-09 T3)
- [x] `tests/train_foreign_seed.py` — foreign qualifying blunder seed that sets the owner's rating (263-01 T1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Draw latency on prod | D-05, D-14 | cost depends on prod table size and cold pages; the dev DB cannot show it | the orchestrator runs `263-PROD-EXPLAIN.sql` (band step at level 1500 and 2600, nearest step at 2600) through the read-only prod MCP BEFORE the squash-merge against the budget (step one at most 0.5 s cold, both steps at most 1.5 s cold; a miss blocks the merge), and once more after the deploy as confirmation; compare with `263-RESEARCH.md` § Prod EXPLAIN results |
| Copy for a session with no own puzzles | D-11 to D-13, score screen | wording needs the owner's eye (ruling 5: score-screen and guest wording is a proposal) | solve an all-foreign session as a fresh user; read intro, tail line, start screen and score screen; list in `263-HUMAN-UAT.md` (263-10) |
| "Established user" reading for D-13 | D-13 | interpretation (has games and a completed puzzles session) | owner confirms or redefines; `263-HUMAN-UAT.md` |
| Old filler reveal right after the deploy | D-03, D-09 | only reachable across the deploy | a reveal of a lichess filler solved just before the deploy shows "Couldn't load the full reveal details." with the verdict still usable; a few 404 events in Sentry are expected |
| Dev DB at the phase head before browser UAT | ruling 9 (revised) | the dev DB is shared with the main checkout, whose backend breaks on Train endpoints until the merge, so no executor migrates it | just before browser UAT, from the worktree: `uv run alembic current`, then `uv run alembic upgrade head`; to undo, `uv run alembic downgrade e5c1b7d3a9f2` (also in `263-HUMAN-UAT.md`) |
| Phone layout at 375x667 | D-12, D-13, D-19 | needs a real viewport and the owner's eye (intro bubble fit, Activity label width) | `263-HUMAN-UAT.md` item 8 |
| Browser walk-through on the dev stack | D-10 to D-13, D-20, D-21 | end to end across compose, solve, reveal and score screen | `263-HUMAN-UAT.md` item 7, after item 5 |

---

## Decision Coverage (validate-phase audit, 2026-11-23)

The requirement set is the owner decisions D-01 to D-21 in `263-CONTEXT.md`. COVERED means an automated test
fails when the behaviour regresses. `repo` = `tests/repositories/test_train_foreign.py`, `svc` =
`tests/services/test_train_foreign.py`, `router` = `tests/routers/test_train_foreign.py`, `legacy` =
`tests/repositories/test_train_legacy_filler.py`, `fe` = `frontend/src`.

| Decision | Status | Tests |
|---|---|---|
| D-01 non-guest strangers only, never the solver's own game | COVERED | repo `test_draw_excludes_guest_and_solver_games`, `test_draw_returns_servable_stranger_blunder`, `test_draw_skips_guest_strangers` (own-game filter mutation-checked in this audit, see below) |
| D-02 pure filler, only on a shortfall | COVERED | repo `test_full_own_supply_draws_no_foreign`, `test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key`, `test_empty_foreign_pool_composes_no_foreign_puzzle` |
| D-03 serving path deleted, history kept | COVERED (file absence is a grep gate, 263-10) | legacy (all seven tests); `tests/repositories/test_train_leaderboard_repository.py::test_foreign_and_legacy_filler_solves_count_on_points_but_not_on_accuracy`; `tests/test_phase_263_migration.py::test_untouched_open_sessions_with_unsolved_legacy_filler_are_deleted` |
| D-04 warm-up retired | COVERED (wording is also a grep gate and owner sign-off) | `tests/test_phase_263_migration.py::test_retire_columns_round_trip`; fe `lib/__tests__/trainBotCopy.test.ts` (intro per no-own-puzzles flag), `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx` |
| D-05 solver level and rating band | COVERED | repo `test_level_passed_to_draw` (three cases), `test_nearest_step_reaches_outside_the_raw_band`; svc `test_pick_prefers_in_band_then_nearest`, `test_foreign_raw_bounds` |
| D-06 same servability predicates as an own puzzle | COVERED, one accepted non-gap (`answer_key_present`) | repo `test_foreign_candidate_rejects_each_pool_predicate` (control plus seven cases) |
| D-07 live join, no snapshot | COVERED | repo `test_resume_serves_foreign_puzzle_with_owner_key`, `test_composition_types_read_foreign_owner_blob`, the tracer |
| D-08 unsolved puzzle of a deleted game is dropped, never pins the session | COVERED | repo `test_deleted_foreign_game_dropped_and_session_completes`, `test_vanished_foreign_flaw_dropped_and_never_pins_session`; legacy `test_unsolved_legacy_filler_never_pins_session_open`, `test_resume_completes_session_whose_remaining_rows_are_unservable`, `test_resume_leaves_untouched_session_with_nothing_servable_open` |
| D-09 solved puzzle keeps its outcome, reveal not found | COVERED | router `test_reveal_foreign_deleted_game_404_and_outcome_kept` |
| D-10 nothing marks a foreign puzzle before the solve | COVERED | router `test_foreign_puzzle_wire_has_no_game_id`; fe `TrainSolveScreen.test.tsx` "a foreign verdict links Analyze to the position, never the game" |
| D-11 neutral return-tail line | COVERED (wording: owner sign-off) | fe `trainBotCopy.test.ts` "a foreign_blunder source returns the neutral foreign line", `TrainSolveScreen.test.tsx` per-puzzle tail |
| D-12 two welcome lines | COVERED (wording: owner sign-off) | fe `trainBotCopy.test.ts` "step 0 is Hilda and the welcome, verbatim, per no-own-puzzles flag" |
| D-13 exhausted-day start sentence | COVERED ("established user" reading: manual) | fe `TrainStartScreen.test.tsx` "an established user with a fresh no-own session reads the sentence", "is absent when the session holds own puzzles", "is absent for an account with no imported games" |
| D-14 plain random draw, no facepalm input | COVERED | svc `test_pick_is_seeded`; repo predicate control case (the seeded blunders carry no facepalm facts, so any facepalm cut drops them); `ForeignCandidate` carries no facepalm field |
| D-15 rating only, no time-control preference | COVERED | svc `test_pick_ignores_time_control` |
| D-16 first-ever session gets a sharp puzzle | COVERED | repo `test_first_ever_session_opens_on_sharp_foreign_blunder`, `test_first_ever_session_keeps_sharp_pick_from_nearest_step`, `test_later_session_draw_does_not_prefer_sharp`; svc `test_pick_prefers_sharp_only_when_wanted` |
| D-17 never served twice, one puzzle per game | COVERED | repo `test_foreign_never_served_twice_across_sessions`, `test_herring_game_excluded_from_foreign_pick`; svc `test_pick_skips_served_positions_and_excluded_games`, `test_pick_takes_one_puzzle_per_game` |
| D-18 points and streak yes, Accuracy board no, no SR state | COVERED | `test_train_leaderboard_repository.py::test_foreign_and_legacy_filler_solves_count_on_points_but_not_on_accuracy`; the tracer (no `drill_items` row, `item_status` None); `tests/routers/test_train_two_mode_streak.py` (foreign-filled sessions) |
| D-19 Activity: new row, old row kept as retired, never merged | COVERED (label text: owner sign-off) | `tests/test_admin_activity_stats.py -k difficulty`; `npm run check:activity-layout` |
| D-20 neutral "played in that game" move | COVERED | router `test_reveal_foreign_reports_owner_game_move_and_type`, `test_reveal_foreign_facepalm_reads_owner_flaw`; fe `trainBotCopy.test.ts` "a several-move fact on a foreign game says the game move" |
| D-21 neutral facts only, no names, ids or links | COVERED | router `test_reveal_foreign_game_info_names_nobody`, `test_reveal_foreign_played_at_is_date_only`, `test_foreign_puzzle_wire_has_no_game_id`; fe `TrainReveal.test.tsx` three "a foreign verdict ..." tests |

### Mutation checks run in this audit

| Mutation (temporary, restored) | Result |
|---|---|
| `_resume_session`: `and solved_results` dropped from the lazy-completion guard | new `test_resume_leaves_untouched_session_with_nothing_servable_open` fails: `assert 'completed' == 'open'` |
| `_foreign_sample_cte`: `sampled.c.user_id != solver_id` removed (D-01) | `test_draw_returns_servable_stranger_blunder` and `test_draw_excludes_guest_and_solver_games` fail (`assert 29 not in {29, 31}`); no new test needed |
| `servable_blunder_predicates`: `answer_key_present` removed | nothing fails in repo or `tests/services/test_train_pool.py` (179 passed): accepted non-gap below |
| `load_session_puzzles`: the explicit `LEGACY_SHARP_FILLER` skip removed | legacy file stays green (7 passed): accepted non-gap below |
| Test isolation (IN-07): a committed raw-1500 stranger blunder present during the tracer | under `real_foreign_draw` the tracer fails (`assert 2 == 1`); under `real_foreign_band_draw` it passes |

### Accepted non-gaps

- **`answer_key_present` in the foreign draw (263-03).** Not isolable by any input: `dead_band_admissible` requires
  `jsonb_typeof(missed_pv_lines -> 0) = 'object'`, which is false or NULL for SQL NULL, `null::jsonb`, `[]` and any
  non-array value, so every blob `answer_key_present` rejects is already rejected. The predicate is kept because
  `dead_band_admissible` documents it as its precondition. The `no-blob` and `empty-blob` cases stay as regression
  guards for the combined behaviour.
- **Explicit legacy-row skip in `load_session_puzzles` (263-08).** Behaviourally redundant: a legacy row carries
  `game_id` NULL (dropped by the no-game skip), and even with a game it is not an owner-keyed source, so the flaw-key
  check drops it. The only state that reaches the branch needs a legacy row pointing at a game that also backs an own
  puzzle of the same session, which nothing ever wrote. The observable behaviour (never served, never pins the
  session) is covered by `test_unsolved_legacy_filler_skipped_on_resume` and
  `test_unsolved_legacy_filler_never_pins_session_open`.
- **File deletions (D-03) and "no warm-up wording anywhere" (D-04).** Structural, checked by the 263-10 grep gates
  and by knip, ty and the import graph, not by a behavioural test.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-23 (validate-phase audit). All 21 decisions covered by automated tests; two
accepted non-gaps and the manual-only items above remain with the owner (`263-HUMAN-UAT.md`).
