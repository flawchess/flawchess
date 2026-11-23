---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 05
subsystem: facepalm-score
tags: [facepalm, refit-checkpoint, calibration, read-only-report, D-04, D-08]
requires:
  - phase: 262-02
    provides: "is_allowed_loss and fit_facepalm scalar_score(row, coefs, gate)"
  - phase: 262-04
    provides: "promotion_candidate_filter, CandidateRow, replay_inputs, as_real, candidate_page_stmt"
provides:
  - "scripts/blunder_check/refit_shift.py: read-only prod view of the refit for the owner checkpoint"
  - "caught_rate.py score-version split (FACEPALM_262_SWITCH_AT) and --rescore"
  - "D-08 note on the facepalm zone bands (no band value changed)"
affects: [262-06, 262-07]
tech-stack:
  added: []
  patterns:
    - "version split keyed on the snapshot moment (session start) through a correlated scalar subquery, no join"
    - "report scripts reuse the pass's own filter and replay so a checkpoint and the pass see the same rows"
key-files:
  created:
    - scripts/blunder_check/refit_shift.py
    - tests/scripts/test_refit_shift.py
  modified:
    - scripts/blunder_check/caught_rate.py
    - tests/scripts/test_caught_rate.py
    - app/services/facepalm_zones.py
  deleted:
    - .planning/phases/262-facepalm-promotions-and-key-move-gate/spike/promo_probe.py
    - .planning/phases/262-facepalm-promotions-and-key-move-gate/spike/promo_gate_probe_prod.py
key-decisions:
  - "refit_shift recomputes with the app rule as it is (no monkeypatch) and compares promotion pairs in 4-byte floats via as_real; a recomputed pair equal to the stored pair is not a change"
  - "caught_rate version split keys on blunder_check_sessions.started_at (when the snapshot was taken), legacy windows are labelled with the deployed model, 261 snapshots are never rewritten"
  - "--rescore bands snapshotted windows by the current model over their snapshot inputs and reports one unsplit table; legacy windows keep the live score"
  - "The two spike probes are deleted: they monkeypatched the victim lookup (double-counting promotions now that the rule lives in the function) and compared stored REAL values at 1e-9"
patterns-established:
  - "FACEPALM_262_SWITCH_AT is a module constant set by plan 07 right after the deploy; unset, the report is unsplit and says so"
requirements-completed: [D-04, D-08]
duration: 35min
completed: 2026-11-23
status: complete
actuals:
  tokens: 11000
  tasks: 3
  commits: 3
plan_head_before: f660a34b3e5ec758956c8dae4703bd1b2bde2a41
plan_head_after: e3a7498b600cd62ec28b62e8718bb652e4fea7cb
---

# Phase 262 Plan 05: Checkpoint tooling and score-version calibration Summary

`refit_shift.py` gives the owner checkpoint a read-only prod view of the refit (passers per D-15 cut, enter and leave at 0.70 by type, own blunders, rows that lose or gain a score, 20 newly passing rows with analysis links), `caught_rate.py` can now keep the Phase 259 and Phase 262 score versions apart and re-band by the current model, and the zone bands carry the D-08 note.

## What changed

- **Task 1 (tracer), `504bf706e`:** `scripts/blunder_check/refit_shift.py`. Samples games by `Game.id % mod == 0` (severity 2, line-stamped, with a played-move probability), selects promotion candidates with the pass's `candidate_page_stmt` (keyset pages, restricted to the sample), replays them with `replay_inputs` and scores every row twice with `fit_facepalm.scalar_score`: `PHASE_259_COEFS` with gate "loss" on the stored pair, and `candidate_coefs()` (the app's current FACEPALM_* values) with gate "type" on the recomputed pair. Report sections: versions and gates, passers per D-15 cut, enter / leave at 0.70 by new and by shipped type, own blunders (drill-pool proxy), inputs changed, lose / gain score, rows the new gate leaves unscored with a settled loss (D-04 NULL rule, scaled by mod), and a seeded newly-passing list with `https://flawchess.com/analysis?game_id=..&ply=..` links. One read-only connection through `make_readonly_engine`; no user ids or usernames are selected into a report row.
- **Task 2, `3d095ed8c`:** `tests/scripts/test_refit_shift.py` (8 tests: mixed row reply vs best-move term, mixed row without best prob losing its score, float32-equal recompute is not a change, a differing recompute replaces the pair, a NULL row that settles gains a score, summarize with scaling, newly-passing determinism and direction, report holds no identity). Mutation check: switching the candidate gate to "loss" fails both mixed-row tests. The two spike probes were removed with `git rm` (the now-empty `spike/` directory disappears with them).
- **Task 3, `e3a7498b6`:** `caught_rate.py` gains `FACEPALM_262_SWITCH_AT` (None), `ScoreVersion`, `version_of`, `WindowRow.version` (default "unsplit", the four leading fields unchanged), `SnapshotInputs`, and `--rescore`. `build_statement` adds the session start as a correlated scalar subquery plus the five snapshot inputs and still has no JOIN. The report names its score source, prints "Score versions: not split (FACEPALM_262_SWITCH_AT is not set)" when unset, and renders one table set per version when set. `facepalm_zones.py`: docstring note only, no band value moved (`test_registry_values_are_the_pinned_per_tc_bands` unchanged and green).

## Dev run results (not prod; read with the caveat below)

`refit_shift.py --db dev --mod 1`: 21180 sampled blunders. Because plan 04's rehearsal already applied the promotion pass to dev, the stored inputs of promotion rows there are the new-rule values, so the promotion recompute delta is zero by construction. The dev report therefore shows the gate (and, at this point of the phase, unchanged coefficients: the app still holds the Phase 259 values until plan 07) only:

| cut | shipped | candidate |
|---|---|---|
| 0.50 | 9361 | 8958 |
| 0.55 | 8700 | 8323 |
| 0.60 | 8088 | 7719 |
| 0.65 | 7441 | 7100 |
| 0.70 | 6781 | 6480 |

- Enter at 0.70: 48, all missed-win rows under both types. Leave: 349, all missed-win rows (mixed rows that no longer read the reply term).
- Own blunders at 0.70 (drill-pool proxy): 3158 shipped, 2996 candidate.
- Inputs changed: 0 (rehearsal, see above). Lose score: 0, gain score: 0, gate-unscored with a settled loss: 0 (dev has the best-move probability on every sampled row; prod may differ, which is what the checkpoint run measures).
- Newly passing list: 20 rows, all "gate and coefficients" (no input change on dev).

`caught_rate.py --db dev --rescore`: runs clean on 20 dev windows (7 with a recorded arm); the output is one unsplit table with the score source line "rescored". `caught_rate.py --db dev` (unset switch) prints the unsplit note.

Report files (written to the main checkout, exempt from the worktree path rule per the orchestrator):
- `/home/aimfeld/Projects/Games/flawchess/temp/promotion-pass/refit-shift-dev.md`
- `/home/aimfeld/Projects/Games/flawchess/temp/promotion-pass/caught-rate-rescore-dev.md`

## Verification

- `uv run pytest tests/scripts/test_refit_shift.py tests/scripts/test_caught_rate.py tests/services/test_facepalm_zones.py`: 47 passed.
- `uv run ruff check scripts/ tests/ app/`, `ruff format --check`, `uv run ty check app/ tests/ scripts/` (after `uv sync --locked --group maia-inference`) and `scripts/check_function_size.py app/ --fail-over-depth 4`: clean.
- Acceptance greps: `PHASE_259_COEFS` x4, the backfill import x1, `_victim_value` x0, `FACEPALM_262_SWITCH_AT` x5, `"--rescore"` x1, `Phase 262` in facepalm_zones x1; spike directory gone.
- Not run: the full backend suite (the plan touches only report scripts, their tests and a docstring; no app logic).

## Deviations from Plan

None - plan executed exactly as written. Two small interpretation choices: (1) the version of a window keys on `selection_arm IS NOT NULL` as "has a snapshot" (the Phase 261 arm marker) rather than on a non-NULL score, so a snapshotted window whose old score was NULL still falls on the session-start side of the split and is scored by `--rescore` when its inputs allow; (2) `render_report` takes `switch_at` and `rescored` as keyword arguments (defaults None / False) so the 261 test calls are unchanged.

## Notes for plan 06 and 07

- plan 06 (owner checkpoint): run `refit_shift.py --db prod --mod 10 --out <report>` after pasting the candidate constants into the working tree. Open the tunnel first. Per the sample note, counts are raw sample counts followed by the count times mod. Run `caught_rate.py --db prod --rescore` to re-read `HARD_TO_CATCH_SCORE_BELOW` (0.5, Phase 259 units).
- plan 07: set `FACEPALM_262_SWITCH_AT` in `scripts/blunder_check/caught_rate.py` to the deploy time (timezone-aware UTC) right after the release.

## Known Stubs

None. `FACEPALM_262_SWITCH_AT = None` is an intentional unset value that plan 07 fills; documented in the module docstring and surfaced in the report.

## Threat Flags

None. The scripts are read-only, hold one connection and print aggregates plus at most 20 game links (T-262-11, T-262-12); the split keys on the session start (T-262-13).

## Self-Check: PASSED

- FOUND: scripts/blunder_check/refit_shift.py, tests/scripts/test_refit_shift.py, scripts/blunder_check/caught_rate.py, app/services/facepalm_zones.py
- FOUND commits: 504bf706e, 3d095ed8c, e3a7498b6 (ancestors of HEAD)
- MISSING: none
