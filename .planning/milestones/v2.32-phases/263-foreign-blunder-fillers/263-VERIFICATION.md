---
phase: 263-foreign-blunder-fillers
verified: 2026-11-24T00:10:00Z
status: passed
score: 13/13 must-haves verified
covered_files:
  - ".planning/phases/263-foreign-blunder-fillers/263-01-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-01-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-02-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-02-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-03-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-03-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-04-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-04-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-05-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-05-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-06-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-06-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-07-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-07-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-08-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-08-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-09-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-09-SUMMARY.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-10-PLAN.md"
  - ".planning/phases/263-foreign-blunder-fillers/263-10-SUMMARY.md"
  - "alembic/versions/20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py"
  - "alembic/versions/20261202_130000_c4e6a8b0d375_phase_263_retire_warmup_and_filler_identity.py"
  - "app/models/drill_solve.py"
  - "app/repositories/train_leaderboard_repository.py"
  - "app/repositories/train_repository.py"
  - "app/routers/train.py"
  - "app/schemas/train.py"
  - "app/services/activity_queries.py"
  - "app/services/train_foreign.py"
  - "app/services/train_pool.py"
  - "frontend/src/components/train/TrainRevealGameFooter.tsx"
  - "frontend/src/components/train/TrainSolveScreen.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/lib/trainBotCopy.ts"
  - "frontend/src/pages/activity/render.js"
  - "frontend/src/types/train.ts"
  - "tests/repositories/test_train_foreign.py"
  - "tests/repositories/test_train_legacy_filler.py"
  - "tests/routers/test_train_foreign.py"
  - "tests/services/test_train_foreign.py"
  - "tests/test_phase_263_migration.py"
covered_digest: "v4:sha256:66a5d0157b7d63686a312afa6121239a58ea44561782f3ee4b98bd2b858b3fdf"
behavior_unverified: 0
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Owner copy sign-off of every new string (263-HUMAN-UAT.md item 1, plus item 12 WR-04 text)"
    expected: "Each line approved or reworded: FOREIGN_TAIL, no-own welcome (owner-written), D-13 start sentence, no-own score notes, guest sign-up line, Welcome DELTA_2, foreign verdict fact, tour chips line, Accuracy not-entered line"
    why_human: "Wording is a product judgement; score-screen, guest and Welcome copy are proposals, not owner-written"
  - test: "Review WR-03 wording (open): score bubble for an established user with no own puzzles due (item 12)"
    expected: "The bubble no longer says the user's games are not analyzed yet when the start screen shows the D-13 sentence for the same session"
    why_human: "Needs owner-chosen wording; not a contradiction of a D-id, so recorded here and not as a gap"
  - test: "D-13 'established user' reading (item 2)"
    expected: "Owner confirms hasGames and modes.puzzles.first_session_done === true as the definition, or names another"
    why_human: "Interpretation of an owner decision"
  - test: "Research A5 and A6 (item 3)"
    expected: "Owner accepts that D-16 binds only with a foreign shortfall, and that the facepalm badge reads the owner's flaw row for a foreign move"
    why_human: "Product acceptance"
  - test: "Device layout at 375x667 (item 8)"
    expected: "The 155-character D-12 welcome fits the intro bubble without clipping; the Activity label 'Sharp filler (retired)' (shortened from the D-19 example) is accepted"
    why_human: "Needs a real viewport and the owner's eye"
  - test: "Dev DB upgrade then browser walk-through (items 5 and 7)"
    expected: "alembic current shows c4e6a8b0d375 (head); fresh account first session filled by foreign blunders with tail on every puzzle, neutral footer, Analyze opening the position only, D-13 sentence, Accuracy board excluding foreign, Activity source rows split"
    why_human: "Shared dev DB deliberately not migrated by executors; end-to-end UI behaviour needs a browser"
  - test: "Post-deploy prod EXPLAIN of the draw, incl. LIMIT 200 variant (item 4 after-deploy leg)"
    expected: "Band step at most 0.5 s cold, both steps at most 1.5 s cold"
    why_human: "Only reachable after the deploy; the pre-merge run (201 ms / 146 ms / 337 ms) passed"
  - test: "Old filler reveal right after the deploy (item 6)"
    expected: "Reveal of a lichess filler solved just before the deploy shows 'Couldn't load the full reveal details.' while the verdict stays usable; a few 404 events in Sentry"
    why_human: "Only reachable across the deploy"
---

# Phase 263: Similarly Rated Players' Blunders Replace the Lichess Fillers Verification Report

**Phase Goal:** When a personalized-puzzle session is short of own material, fill it with blunders from similarly rated non-guest players' games; delete the lichess filler serving path while keeping solved `source = 2` rows as inert history; retire the warm-up concept (`is_warmup` gone server and client); foreign puzzles stay off the Accuracy board, carry no SR state and never expose the stranger's game.
**Verified:** 2026-11-24
**Status:** human_needed
**Re-verification:** No, initial verification (the post-plan review fix pass was verified as part of the current code, HEAD 9e4624e3e)

The goal is achieved in the codebase. No FAILED truth, no stub, no unwired artifact, no blocker anti-pattern. Status is `human_needed` only because owner-only items (copy sign-off, one interpretation, device layout, browser walk-through, two post-deploy legs) are open by design.

## Requirement accounting (D-ids)

No REQUIREMENTS.md entries are mapped to this phase. The ten plans declare D-ids only. Union of the `requirements:` frontmatter across plans 01 to 10 = D-01 .. D-21, every id exists in 263-CONTEXT.md, and none is missing (plan 06 alone declares all 21). No orphans.

| D-id | Status | Evidence (code, verified by reading) |
|---|---|---|
| D-01 non-guest strangers, never solver | SATISFIED | `train_pool._foreign_sample_cte`: `sampled.c.user_id != solver_id`, `User.is_guest.is_(False)` |
| D-02 pure filler on shortfall | SATISFIED | `_assemble_session_items`: `foreign_shortfall = n - len(reconstructed)`, draw only if `> 0`; `HERRING_SHARE` untouched |
| D-03 delete path, keep history | SATISFIED | the three files absent; greps below; `LEGACY_SHARP_FILLER = 2` kept; leaderboard/session counts untouched |
| D-04 warm-up retired | SATISFIED | zero `is_warmup`/`isWarmup`/`sharp_puzzle_id` readers in app/scripts/analysis/frontend/src; migration `c4e6a8b0d375` drops both columns |
| D-05 level and band | SATISFIED | `_backfill_foreign_blunders` uses `user_level_elo(recent_rated_games, fallback=level_fallback_elo(...))`; `foreign_raw_bounds`; pinned-Elo band check in `_rank_candidates`; nearest-first step |
| D-06 same predicates | SATISFIED | one `servable_blunder_predicates` shared by `pool_entry_stmt` and the foreign stage-two statement, no extra predicate |
| D-07 live join | SATISFIED | no snapshot columns; key/type/graded set read from the owner's rows (`_classify_sr_solve(flaw_owner_id=owner_id)`, `_existing_owner_flaw_keys`) |
| D-08 deleted game dropped, never pins | SATISFIED | `load_session_puzzles` skips `game is None`; `_mark_session_complete_if_done` leniency covers `_OWNER_KEYED_SOURCES` and all unsolved `LEGACY_SHARP_FILLER` |
| D-09 solved keeps outcome, reveal not found | SATISFIED | `reveal_for_puzzle`: `game is None and source in _OWNER_KEYED_SOURCES` returns `not_found`; row stays |
| D-10 nothing marks it pre-solve | SATISFIED | `_wire_game_id` returns None for foreign; no client marker before solve; tests |
| D-11 neutral tail | SATISFIED (copy: owner sign-off) | `FOREIGN_TAIL` in `returnPhrase`, per puzzle regardless of session mix |
| D-12 two welcome lines | SATISFIED (copy: owner sign-off) | `INTRO_WELCOME_COPY` / `INTRO_NO_OWN_PUZZLES_WELCOME_COPY`, owner's exact wording, selected by `noOwnPuzzles` |
| D-13 exhausted-day sentence | SATISFIED (reading: owner confirm) | `NO_OWN_DUE_TODAY_COPY`, `showNoOwnDue` in `TrainStartScreen` |
| D-14 plain random draw | SATISFIED | `_rank_candidates` seeded shuffle; `ForeignCandidate` has no facepalm field |
| D-15 rating only | SATISFIED | no time-control input in the pick |
| D-16 first session has a sharp puzzle | SATISFIED | `want_sharp=first_ever`; review WR-01 fix keeps the sharp pick through the shortfall trim |
| D-17 never twice, one per game | SATISFIED | `_served_foreign_positions` + `MAX_ITEMS_PER_GAME_PER_SESSION` in the pick; herring games excluded |
| D-18 points/streak yes, Accuracy no | SATISFIED | `_ACCURACY_SOURCES` positive list `[SR_ITEM, RED_HERRING]`; no `drill_items` row |
| D-19 Activity rows | SATISFIED (label: owner sign-off) | `render.js` source 3 "Similar player's blunder", source 2 "Sharp filler (retired)", never merged; `fetch_puzzle_difficulty` groups by source |
| D-20 neutral played move | SATISFIED | separate `FOREIGN_BLUNDER` branch in `reveal_for_puzzle`; herring ownership gate unchanged; `fromForeignGame` client wording |
| D-21 neutral facts only | SATISFIED | `_foreign_game_info`: tc, bucket, date (UTC midnight, WR-02 fix), mover rating; `game_id` None on the wire; Analyze opens the position only; footer never fetches the library game for a foreign puzzle |

## Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A short session is filled with servable blunders of other, non-guest users near the solver's rating; a full own supply calls no draw | VERIFIED | `_assemble_session_items` (post-reconstruction, shortfall-gated); `test_full_own_supply_draws_no_foreign`, `test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key` pass |
| 2 | Never a guest's game, never the solver's own; same six predicates as an own puzzle | VERIFIED | `_foreign_sample_cte`, `servable_blunder_predicates` shared with `pool_entry_stmt`; `test_draw_excludes_guest_and_solver_games`, `test_foreign_candidate_rejects_each_pool_predicate` pass |
| 3 | Rating from `user_level_elo` with band, TABLESAMPLE prefilter and nearest-first fallback, two statements max | VERIFIED | `train_foreign.FOREIGN_FILLER_DRAW_STEPS` (0.1% band, 0.4% nearest), `_foreign_picks` loop capped at two steps; `test_level_passed_to_draw`, `test_nearest_step_reaches_outside_the_raw_band` pass |
| 4 | Per-user no-repeat, one puzzle per game, first-ever session gets a sharp puzzle | VERIFIED | `_served_foreign_positions`, `pick_foreign_candidates`, WR-01 trim fix; `test_foreign_never_served_twice_across_sessions`, `test_first_ever_session_keeps_sharp_pick_from_nearest_step` pass |
| 5 | Live join, no snapshot; an unsolved foreign puzzle of a deleted game or vanished flaw is dropped and never pins the session; a solved one keeps its outcome and its reveal is not_found | VERIFIED | `load_session_puzzles`, `_mark_session_complete_if_done`, `reveal_for_puzzle` read directly; `test_deleted_foreign_game_dropped_and_session_completes`, `test_vanished_foreign_flaw_dropped_and_never_pins_session`, `test_reveal_foreign_deleted_game_404_and_outcome_kept` pass |
| 6 | Lichess filler serving path deleted: CSV, service, generator gone, no composition, grading or reveal branch | VERIFIED | `ls` of the three paths fails; `git ls-files` shows no `sharp_filler` file besides the Phase 206 migration; remaining `LEGACY_SHARP_FILLER` references are only the inert-history handling (wire value, skip on resume, completion leniency, reveal `not_found`, leaderboard exclusion), no serving path |
| 7 | Solved `source = 2` rows stay as inert history: points, session counts, streaks untouched; reveal on an old filler returns not_found; unsolved filler never pins an open session | VERIFIED | migration touches no solved rows (it deletes only untouched open sessions holding an unsolved filler); `test_train_legacy_filler.py` (7 tests) and `test_foreign_and_legacy_filler_solves_count_on_points_but_not_on_accuracy` pass |
| 8 | Warm-up concept retired: `drill_sessions.is_warmup`, `TrainSessionResponse.is_warmup` and every `isWarmup` branch gone; no warm-up wording | VERIFIED | greps below (only migration code/tests and the retired-column docs mention the names); no warm-up wording in app or frontend/src outside unrelated engine/openings code; model has no `is_warmup` |
| 9 | Welcome line and exhausted-day sentence truthful without a persisted flag; label does not repeat on an all-foreign session | VERIFIED | `own_puzzle_count` derived per response in `_resume_session` and composition (`len(surviving_sr_keys)`), 0 on empty compositions, wired `schemas/train.py` -> `routers/train.py:169` -> `types/train.ts:106` -> `Train.tsx:110`, `TrainStartScreen.tsx:407`, `TrainSolveScreen.tsx:1652`; the tail is one neutral line per foreign puzzle (D-11) with no session-level marker |
| 10 | Foreign puzzles stay off the Accuracy board, count for points, day completion and streak, carry no SR state / `drill_items` row | VERIFIED | `_ACCURACY_SOURCES` positive list; `_resume_session` outer join yields NULL `item_status` for non-SR; tracer test and leaderboard test pass |
| 11 | Foreign puzzle never exposes the stranger's game: game_id null on the wire, neutral facts only, no names/ids/links, Analyze opens the position | VERIFIED | `_wire_game_id`; `_foreign_game_info` (date-only after WR-02); `has_tactic_lines = not foreign and ...`; `TrainRevealGameFooter` nulls the library fetch for foreign and renders `ForeignGameFooter` from `game_info`; `TrainSolveScreen` `analyzeOpens` gate; `test_reveal_foreign_game_info_names_nobody`, `test_reveal_foreign_played_at_is_date_only`, `test_foreign_puzzle_wire_has_no_game_id` pass |
| 12 | Activity source breakdown has a new foreign row and keeps the retired row, never merged | VERIFIED | `render.js` rows for sources 0, 1, 3, 2; `fetch_puzzle_difficulty` groups by raw source value; `tests/test_admin_activity_stats.py -k difficulty` is cited green by the validation audit |
| 13 | Schema change is safe: two migrations form a single alembic head, CHECK admits 3, columns dropped, downgrade round-trips | VERIFIED | `uv run alembic heads` prints only `c4e6a8b0d375 (head)`; chain `e5c1b7d3a9f2 -> b3d5f7a9c264 -> c4e6a8b0d375`; model CHECK `source IN (0, 1, 2, 3)`; `tests/test_phase_263_migration.py` passes in the test DBs (dev DB deliberately not touched) |

**Score:** 13/13 truths verified, 0 present-but-behavior-unverified. The state-transition invariants (session never pinned open, lazy completion, sharp-first ordering, outcome kept after deletion) each have a passing named test.

## Behavioral spot-checks run by the verifier

| Check | Command | Result | Status |
|---|---|---|---|
| Foreign repo, pure pick, router wire and reveal, legacy filler, migration | `uv run pytest tests/repositories/test_train_foreign.py tests/services/test_train_foreign.py tests/routers/test_train_foreign.py tests/repositories/test_train_legacy_filler.py tests/test_phase_263_migration.py -q` (serial) | 57 passed | PASS |
| Client copy, start screen, reveal | `npx vitest run src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__/TrainStartScreen.test.tsx src/components/train/__tests__/TrainReveal.test.tsx` | 3 files, 238 tests passed | PASS |
| Single alembic head | `uv run alembic heads` | `c4e6a8b0d375 (head)` | PASS |
| Full suites | not re-run (orchestrator reports 7069 backend, 6862 frontend, lint, build, knip, ty, ruff, depth gate green after the last edit) | n/a | relied on |

## Phase-wide negative greps (run by the verifier)

| Grep | Result |
|---|---|
| `app/data/sharp_filler_puzzles.csv`, `app/services/sharp_filler.py`, `scripts/gen_sharp_filler_set.py` | absent |
| `is_warmup\|isWarmup\|sharp_puzzle_id` in app, scripts, analysis, frontend/src | zero hits (only tests/ and alembic/ carry the names, as migration subject matter) |
| "warm-up" wording in app and frontend/src | only unrelated engine, openings-baseline and analysis-study hits; CHANGELOG hits are history |
| `sharp_filler` | only the retired wire value, legacy-history handling, the Phase 206 migration and tests |
| `own_puzzle_count` | present from repository to schema, router, `types/train.ts` and the three client consumers |
| `DrillSource.FOREIGN_BLUNDER` switch sites | `_wire_source`, `answer_key_for` / `server_graded_moves_for` (SR branch), `_classify_and_certify_solve`, `_wire_game_id`, `_OWNER_KEYED_SOURCES` (load, completion, reveal), `reveal_for_puzzle` foreign branch, `_ACCURACY_SOURCES` positive list; `_wire_source` still raises on an unknown value |

## Data-flow and wiring

`_backfill_foreign_blunders` -> `_foreign_picks` -> `_draw_foreign_candidates` (real SQL via `foreign_band_candidates_stmt` / `foreign_nearest_candidates_stmt`, no static fallback; the test seam in `tests/conftest.py` stubs only in tests) -> PGN replay -> `_ReconstructedPuzzle(source=FOREIGN_BLUNDER)` -> `_materialize_session_rows` -> served and graded on the owner's live blob. All wired and FLOWING. The reveal's `game_info` flows from `_foreign_game_info` through `RevealedPuzzle` to `TrainRevealGameFooter` via the shared reveal query.

## Anti-patterns

No unreferenced TBD/FIXME/XXX debt markers in the phase's changed files; no stubs. Open review items are non-blocking: IN-01 (owner-key set defined three times), IN-04 (`non_filler_*` names), IN-05 (per-position no-repeat, the opponent's copy of the solver's own game can be drawn, same as blunder check), IN-06 (nav badge counts unservable rows until Train opens). None contradicts a D-id.

Informational, outside this phase and already recorded in 263-HUMAN-UAT.md item 12: the security audit found that red-herring rows still send another user's `game_id`, and the library game and tactic-lines endpoints are not owner-scoped by design, so the nulled wire `game_id` is the only control for a foreign puzzle. Cross-mode repeat (a foreign blunder later appearing in a blunder-check window) is outside D-17.

## Accepted non-gaps (confirmed)

- `answer_key_present` inside `servable_blunder_predicates` cannot be isolated by any test because `dead_band_admissible` already rejects every blob it rejects.
- The explicit legacy-row skip in `load_session_puzzles` is behaviourally redundant with the no-game skip; the observable behaviour is covered.

## Human Verification Required

See the `human_verification` frontmatter list; full steps in 263-HUMAN-UAT.md. In short: copy sign-off (items 1 and 12), WR-03 wording, the D-13 "established user" reading, A5/A6, 375x667 layout, manual dev DB upgrade plus browser walk-through, and the two post-deploy legs (prod EXPLAIN, old-filler reveal).

## Gaps Summary

None. All 21 owner decisions are honored in code, the serving path is deleted, the history is inert, the warm-up concept is gone end to end, the migrations form a single head, and the foreign puzzle exposes nothing of the stranger beyond neutral game facts.

---

_Verified: 2026-11-24_
_Verifier: Claude (gsd-verifier)_

## Addendum 2026-11-24 (orchestrator, at phase close)

Status moved from `human_needed` to `passed`: 263-UAT.md has 6 of 8 items passed (browser UAT plus the owner's
acceptance). Items 7 (prod EXPLAIN) and 8 (old-filler reveal) passed after release #508 on 2026-11-24.

`covered_digest` was recomputed without re-running the verifier. The only covered file that changed since the
verifier ran is `TrainStartScreen.tsx`, from merging `main` (quick task 261124-5f3: a Retry button in the error state).
The D-13 logic is unchanged, and the full backend and frontend suites passed on the merged tree.
