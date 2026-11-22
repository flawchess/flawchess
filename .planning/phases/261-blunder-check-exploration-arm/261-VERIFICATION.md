---
phase: 261-blunder-check-exploration-arm
verified: 2026-11-22T17:45:00Z
status: passed
score: 12/12 decisions verified in code; 1 must-have (D-03 / D-04 in the running app) not observed
covered_files:
  - ".planning/phases/261-blunder-check-exploration-arm/261-01-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-01-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-02-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-02-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-03-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-03-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-04-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-04-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-05-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-05-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-06-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-06-SUMMARY.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-07-PLAN.md"
  - ".planning/phases/261-blunder-check-exploration-arm/261-07-SUMMARY.md"
  - "CHANGELOG.md"
  - "alembic/versions/20261130_120000_a7c3e5f9b261_phase_261_window_selection_snapshot.py"
  - "app/models/blunder_check.py"
  - "app/repositories/blunder_check_repository.py"
  - "app/routers/blunder_check.py"
  - "app/schemas/blunder_check.py"
  - "app/services/blunder_check_candidates.py"
  - "app/services/blunder_check_feedback.py"
  - "app/services/blunder_check_rules.py"
  - "app/services/blunder_check_selection.py"
  - "app/services/blunder_check_service.py"
  - "frontend/src/components/library/FacepalmBadgePopover.tsx"
  - "frontend/src/components/library/FacepalmChip.tsx"
  - "frontend/src/components/library/FacepalmExplanation.tsx"
  - "frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx"
  - "frontend/src/lib/blunderCheckSolution.ts"
  - "frontend/src/lib/facepalm.ts"
  - "frontend/src/types/blunderCheck.ts"
  - "reports/blunder-check/exploration-probe-explain-261.md"
  - "scripts/blunder_check/caught_rate.py"
covered_digest: "v4:sha256:7508722d1ad0ef89d496e6576c6d985ea74e922e66baaca86b4a813f5873d62b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Feedback paragraph on the desktop card (261-07 Task 3 steps 1 and 2)"
    expected: "Start dev stack (bin/run_local.sh, dev DB at revision a7c3e5f9b261), log in as a dev user with analysed games, Train -> Blunder check -> Start, play until a blunder window ends caught or missed. At desktop width, under the verdict sentence (data-testid blunder-check-solution-summary) the paragraph data-testid blunder-check-solution-feedback shows a grey 'Facepalm N%' chip, then the type line when there is one, then the hard-to-catch line when the score is below 50%. Opening the chip popover shows no facepalm type name and the score sentence reads 'a player at that level'."
    why_human: "No browser tool was available to the orchestrator; component tests (jsdom) and router tests cover the wire and DOM order but not the real rendering in the running app."
  - test: "Feedback paragraph on the 375 px phone strip (261-07 Task 3 step 3)"
    expected: "Resize to 375 px wide, unfold the verdict strip: the same paragraph follows the verdict sentence."
    why_human: "Visual layout of the strip in a real viewport."
  - test: "False alarm shows no feedback (261-07 Task 3 step 4)"
    expected: "If a false alarm occurs in the session, its solution shows no feedback paragraph and no case or blunder."
    why_human: "Only reachable in a live session; automated tests already cover the schema and component level (see D-05)."
  - test: "Owner decision on WR-01 (261-REVIEW.md)"
    expected: "Accept that the exploration pass runs before the main pass in _fill_from_pool (under thin supply a main slot can lose its only host game and redraw toward an easier shape), or ask for one rarest-first assign_windows call over both arms."
    why_human: "Disposition is open in 261-REVIEW-DISPOSITION.md; it is a product trade-off, not a must-have failure."
---

# Phase 261: Blunder-Check Exploration Arm Verification Report

**Phase Goal:** Serve about 20% of blunder windows from a random draw with no facepalm-score cut, record what was served, and show the score after the answer.
**Verified:** 2026-11-22
**Status:** passed (after UAT, see "Post-UAT amendment" below)
**Re-verification:** No. The verifier ran once, on 2026-11-22 before UAT. The amendment below was written by the orchestrator after the owner's UAT change; the verifier was not re-run.

## Goal Achievement

The goal is achieved in code. The exploration arm draws about 20% of blunder slots per window with no score cut, the serve-time record is written to `blunder_check_windows`, and the solution feedback is built from the snapshot. No contradiction of any D-01 to D-12 was found. The only open must-have is the visual check in the running app, which was not performed (no browser tool), plus the open owner disposition on review finding WR-01.

### Decision-by-decision (261-CONTEXT.md contract)

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| Seed | Share: one coin per blunder slot, one named constant (20%), own and foreign alike, per window | VERIFIED | `EXPLORATION_SHARE = 0.2` and `draw_slot_arm` (`blunder_check_rules.py:153`, `:348`); `draw_slot_plan` flips the coin only for blunder slots, herrings keep `main` (`:355-370`). `test_exploration_share_per_blunder_origin` (seeded, own and foreign, tolerance) passes. |
| Seed | Draw: game-first probe without the cut, scored rows only, random choice among eligible blunders, other judge filters kept | VERIFIED | `_unserved_qualifying_blunder_exists(min_score=None)` uses `score IS NOT NULL`, keeps owner-side gate, served-once, cooled pairs; `assign_windows` still `rng.choice` over options; `_blunder_candidate` keeps severity, undecided-position, classified-case, early-ply, position-fit gates. Mutation check: making the exploration pass use the 0.70 cut fails 6 tests (below-cut serve, tracer, own-to-foreign, counts-as-normal, no-arm-before-answer, cut-batch skip). |
| Seed | Main arm keeps 0.70 cut | VERIFIED | `FACEPALM_SCORE_MIN == 0.7` asserted in `test_blunder_check_rules.py`; main pass uses `FACEPALM_SCORE_MIN` in `_fill_from_pool`. See WR-01 for a thin-supply ordering side effect. |
| Seed | Counts as normal, no user-visible marker | VERIFIED | Points/streak/leaderboard code untouched; `test_exploration_window_counts_like_any_other` and `test_no_arm_or_score_before_the_answer` pass; arm is never on any wire schema (only `BlunderFeedback`: score, type_line, hard_to_catch). |
| Seed | Runs indefinitely, no gate or stop rule | VERIFIED | No gate code; lowering is the constant. |
| Seed | Score shown is the serve-time snapshot | VERIFIED | `_blunder_solution` builds feedback from `window.facepalm_*` columns only (`blunder_check_service.py:1163-1171`), never `game_flaws`. |
| Seed | Type line: facepalm-type side only, floor 2 or mate, floor not applied to stored means, stored on the window, no new `game_flaws` column | VERIFIED | `type_line_facts` branches on `facepalm_type`; `window_case` not read; `TYPE_LINE_MIN_SWING = 2` applied only in `blunder_feedback` (read time); migration adds columns only to `blunder_check_windows`; tests `test_allowed_loss_never_reports_the_best_line_mate`, `test_missed_win_never_reports_the_played_line_mate`, `test_floor_is_a_read_time_constant` pass. |
| D-01 | Score shown with the library `FacepalmChip` + popover, fed by the snapshot | SUPERSEDED in UAT (was VERIFIED in code) | `BlunderCheckSolution.tsx:253-258` renders `FacepalmChip score={copy.feedback.score}`; chip reuses `FacepalmBadgePopover`/`FacepalmExplanation`. Real rendering: human item 1. |
| D-02 | Popover explains the score only, neutral about whose blunder | SUPERSEDED in UAT (was VERIFIED, copy caveat) | Neutral form passes no type (`FacepalmChip` neutral props), `FacepalmExplanation` hides the type line when `type` is absent, neutral grey tint (`FACEPALM_NEUTRAL_STYLE`), `facepalmScoreMeaning('neutral')` says "that level". Typed Flaws-card form unchanged ("your"). Copy nit IN-04 (dangling "that level") is advisory. |
| D-03 | Second short paragraph after the verdict sentence, chip then type line then hard-to-catch, desktop card and phone strip | AMENDED in UAT: no chip, lines only (was VERIFIED in jsdom) | `SolutionVerdict` is the one renderer used for both the card (`:383`) and the strip (`:392`); tests assert DOM order after `blunder-check-solution-summary`. Browser check pending (human items 1 and 2). |
| D-04 | Every blunder window with a snapshot shows it, caught or missed, both arms; pre-phase windows show nothing | VERIFIED | `blunder_feedback` returns None only when `score is None`; both arms get the snapshot (`_selection_record` has no arm condition); `feedbackCopy` returns null for a null/absent `feedback`; tests cover `feedback: null`. |
| D-05 | False alarm shows nothing new | VERIFIED | `FalseAlarmSolution` schema and service path unchanged (`window_solution` routes FALSE_ALARM to `_false_alarm_solution`); `falseAlarmCopy` returns `feedback: null`; test "never shows on a false alarm or a herring" passes. |
| D-06 | Hard to catch = snapshotted score below 0.5, one named constant, tied to score not arm | VERIFIED | `HARD_TO_CATCH_SCORE_BELOW = 0.5`; `hard_to_catch=score < HARD_TO_CATCH_SCORE_BELOW`; parametrised boundary test passes. |
| D-07 | Wording as seed | VERIFIED | `HARD_TO_CATCH_COPY`: "This one was hard to catch." / "Well spotted, this one was hard to catch.", keyed on `solution.outcome`. |
| D-08 | Swing at deepest settled odd depth of the quiet walk, reusing Phase 259 functions | VERIFIED | `type_line_facts` uses `quiet_line_facts`, `quiet_best_line_facts`, `loss_by_depth`, `gain_by_depth`; `_deepest_settled` takes the last non-None; tests `test_allowed_swing_is_the_deepest_settled_depth`, `test_short_line_reads_the_last_settled_depth` pass. |
| D-09 | Mate wording only when the stored line reaches mate; mate beats material | VERIFIED | `mate = played.mate_ply is not None` (blunderer mated in played line) / `best.opponent_mate_ply is not None` (stored best line); mate precedence in `blunder_feedback`; copy strings match the seed ("allows a material loss", "allows checkmate", "misses a material win", "misses checkmate"). |
| D-10 | No new index; confirm foreign pick by EXPLAIN on prod | VERIFIED | Migration adds no index; `reports/blunder-check/exploration-probe-explain-261.md` records the four prod plans, no Seq Scan on `game_flaws`, scored warm medians 46.5 ms (foreign) and 339.1 ms (nearest) within the bounds, `verdict: pass`. (Orchestrator-run; report read, not re-run.) |
| D-11 | No special rule for served-once consumption | VERIFIED | No exploration-specific served-once logic; the shared `not_(already_served)` condition applies to both arms. |
| D-12 | Best-move line from `game_positions.pv` at the flaw ply, falling back to `best_move`; missing best line gives no "misses" line | VERIFIED | `_type_line_facts_for` uses `positions[blunder_ply].pv or .best_move`; `test_lone_non_mating_best_move_gives_no_missed_swing` passes. |
| Discretion | Pre-phase windows keep NULL arm, no backfill | VERIFIED | Migration adds nullable columns, no UPDATE; calibration script reports `legacy` arm. |
| Discretion | Snapshot and type-line facts stored on both arms, none on herrings | VERIFIED | `_new_window` sets `selection` only when `blunder_ply` is not None; CHECK `window_case <> 0 OR selection_arm IS NULL`. |
| Discretion | Calibration script under `scripts/blunder_check/` with Wilson bands, arm and `is_own` split, reached denominator, false alarms beside | VERIFIED | `scripts/blunder_check/caught_rate.py` (415 lines) uses `wilson_bounds`; 19 tests in `tests/scripts/test_caught_rate.py` pass. |
| Discretion | Share acceptance: seeded slot-draw test and a post-release prod count | VERIFIED (test) / OPEN THREAD (prod) | Seeded draw test passes; the script has a share verdict (n >= 500, interval overlaps [0.18, 0.26]); STATE.md carries the "Phase 261 share acceptance" thread (grep count 1). The prod count itself is post-release by design. |
| Discretion | Arm survives own-to-foreign conversion and redraws | VERIFIED | `replace(plan, ...)` at all three rewrite sites; `test_own_to_foreign_conversion_keeps_the_exploration_arm` passes. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| Alembic revision `a7c3e5f9b261` | VERIFIED | Ten nullable columns, eight CHECKs, no native ENUM, downgrade reverses; `alembic heads` shows it as the single head. |
| `app/models/blunder_check.py` (`WindowArm`, ten columns, CHECKs) | VERIFIED | Matches the migration. |
| `app/services/blunder_check_feedback.py` | VERIFIED | Substantive, imported by selection, service and router. |
| `app/repositories/blunder_check_repository.py` (`min_score`, `WindowSelectionRecord`, loader inputs) | VERIFIED | Both insert paths go through `_window_row`/`_selection_columns`. |
| `app/services/blunder_check_selection.py` / `_candidates.py` | VERIFIED | Probe-tagged batches, two-pass fill, arm-preserving rewrites. |
| Wire: `BlunderFeedback`, `BlunderSolution.feedback` (backend + `types/blunderCheck.ts`) | VERIFIED | Only the blunder solution carries it. |
| Frontend chip/lib/solution files | VERIFIED in code | See D-01 to D-07. |
| `scripts/blunder_check/caught_rate.py` | VERIFIED | Wired to `blunder_check_windows`; read-only engine. |
| `CHANGELOG.md` bullet | VERIFIED | Present under `[Unreleased]` / Added; does not announce the arm (owner-adjustable assumption in plan 07). |
| `reports/blunder-check/exploration-probe-explain-261.md` | VERIFIED | `verdict: pass`. |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| `draw_slot_plan` arm -> `_empty_plans` -> `_fill_from_pool` -> `_Filled.arm` -> `_selection_record` -> `NewWindow.selection` -> `_window_row` columns | WIRED |
| Window columns -> `blunder_feedback` -> `BlunderSolutionData.feedback` -> router `_feedback_schema` -> `BlunderSolution.feedback` | WIRED |
| `BlunderSolution.feedback` -> `feedbackCopy` -> `SolutionCopy.feedback` -> `SolutionVerdict` (card and strip) -> `FacepalmChip` | WIRED |

### Data-Flow Trace (Level 4)

| Value | Source | Real data | Status |
|-------|--------|-----------|--------|
| Chip score, type line, hard-to-catch | `blunder_check_windows.facepalm_score/loss/missed/type_swing/type_mate`, written from `game_flaws` rows loaded by `load_blunder_flaws` at composition | Yes (end-to-end tracer `test_tracer_exploration_window_end_to_end` exercises it against a real test DB) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase backend tests (selection, feedback, candidates, rules, snapshot, repository, exploration router, solution router, caught_rate) | `uv run pytest -n 4 -q` on those nine files | 239 passed | PASS |
| Phase frontend tests (solution copy, solution component, chip, explanation, facepalm lib) | `npx vitest run` on those files | 188 passed | PASS |
| Mutation: exploration pass uses 0.70 cut | edit then run selection + exploration router tests | 6 failed (reverted, tree clean) | PASS (tests have teeth) |
| Single alembic head | `uv run alembic heads` | `a7c3e5f9b261 (head)` | PASS |
| Full suites, lint, build, knip, ruff, ty, function-size | orchestrator-reported (6951 backend serial and parallel, 6762 frontend) | not re-run, `serial-pytest.log` ends `exit=0` | accepted as reported |

### Probe Execution

SKIPPED: the phase declares no `probe-*.sh` probes.

### Requirements Coverage

No REQUIREMENTS.md and no mapped requirement IDs; the contract is D-01 to D-12 plus the seed and discretion items (all accounted for above). Plan frontmatter lists `SEED-261121-t50` and `D-10`, both covered.

### Anti-Patterns Found

No TBD/FIXME/XXX in the phase files (not blocking). Review findings, none a blocker:

| ID | Severity | Impact on must-haves |
|----|----------|----------------------|
| WR-01 | Warning | Exploration-first pass breaks cross-arm rarest-first ordering; under thin supply the main arm's shape mix can drift easier. The 0.70 cut itself is unchanged, so D-02/"main keeps cut" holds. Needs owner disposition. |
| IN-01 | Info | `--since` binds local midnight, not UTC. |
| IN-02 | Info | Dead constant `UNSCORED_BAND`. |
| IN-03 | Info | Type-line Literal defined twice. |
| IN-04 | Info | Neutral copy "that level" has no antecedent; D-02 neutrality holds, wording could be clearer. |
| IN-05 | Info | `_selection_record` returns None silently (unreachable today). |
| IN-06 | Info | `arm_probability` is the arm share only; fine for the current unweighted report. |
| IN-07 | Info | `type_swing >= 0` CHECK relies on floors being 0; hazard if a floor is later set to None. |

### Human Verification Required

1. **Desktop card, running app.** Start the dev stack (`bin/run_local.sh`, dev DB at `a7c3e5f9b261`), log in as a dev user with analysed games, Train -> Blunder check -> Start, play until a blunder window ends caught or missed. Under `blunder-check-solution-summary`, `blunder-check-solution-feedback` should show a grey "Facepalm N%" chip, then the type line when there is one, then the hard-to-catch line when the score is below 50%. The chip popover must not name the facepalm type and should say "a player at that level".
2. **Phone strip, 375 px.** Resize, unfold the verdict strip; the same paragraph follows the verdict sentence.
3. **False alarm (if one occurs).** No feedback paragraph.
4. **WR-01 disposition (owner).** Accept, or give `assign_windows` one rarest-first call over both arms.

### Gaps Summary

No gaps. All of D-01 to D-12, the seed decisions and the discretion defaults are implemented, wired and covered by tests with teeth. Status is `human_needed` only because the plan's browser check (261-07 Task 3 steps 1 to 4) was not performed and WR-01 awaits an owner decision. The prod share acceptance is a post-release step recorded in STATE.md.

---

_Verified: 2026-11-22_
_Verifier: Claude (gsd-verifier)_

## Post-UAT amendment (2026-11-22, orchestrator)

Written after the verifier ran. It records what the owner changed in UAT, so the rows above that describe the
Facepalm chip are history, not the shipped state. This is not a second verifier run.

**Owner changes in UAT (261-UAT.md, "UAT feedback"):**

- **D-01 and D-02 are superseded.** The Facepalm score chip and its neutral popover are no longer shown on the
  blunder check solution. The neutral chip form, the `'neutral'` audience, `FACEPALM_NEUTRAL_STYLE` and the
  `FACEPALM_NEUTRAL*` theme tokens were deleted. The phase goal's "show the score after the answer" is therefore
  met differently: the serve-time snapshot now only decides the "???" badge and the hard-to-catch line, and the
  number itself is not displayed.
- **D-03 is amended.** The second paragraph is the type line and the hard-to-catch line only, and is absent
  when a blunder has neither (`feedbackCopy` returns null for no lines).
- **New, outside the D-01 to D-12 contract.** A facepalm blunder (snapshot score of 70% or more,
  `isFacepalmBlunder`) is badged "???" on the board and the Game chip of the blunder check solution
  (`lineModel` in `blunderCheckSolution.ts`, `markerForQuality` in `trainArrows.ts`, `TrainLineChips.tsx`). The
  personalized-puzzle reveal does the same from a new boolean `game_move_facepalm` on `PuzzleRevealResponse`
  (`_game_move_is_facepalm` in `train_repository.py`: the user's own blunder, library lambda, at or above
  `FACEPALM_STATS_MIN`); the score stays server-side.
- D-04 to D-12, the seed decisions and the discretion items are untouched by the change. `BlunderFeedback`
  on the wire is unchanged (score, type_line, hard_to_catch).

**Evidence for the change:** frontend lint, `tsc -b` build, 6764 vitest tests and knip pass; backend ruff, ty,
the nesting-depth gate and the full suite (6952 passed, 8 skipped) pass. New tests:
`test_reveal_game_move_facepalm_flag` (high score true, low score false, a mistake false), the "facepalm
blunder badge" block in `blunderCheckSolution.test.ts`, the "???" cases in `BlunderCheckSolution.test.tsx`,
`trainRevealLines.test.ts` and `trainArrows.test.ts`.

**Human verification:** closed in 261-UAT.md, 6 of 6 passed. Tests 1, 2, 5 and 6 (the changed screens) were
marked passed by the owner; the orchestrator did not observe them in a browser. Test 3 was observed before the
change and is unaffected.

**WR-01:** accepted as is by the owner (261-REVIEW-DISPOSITION.md). IN-04 is moot, its copy was removed.
