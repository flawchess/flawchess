---
phase: 259-facepalm-first-principles-refit
plan: 01
subsystem: backend
tags: [python-chess, facepalm, line-material, quiet-point, static-exchange]

requires:
  - phase: 250-254-256
    provides: "line replay (_replay_line, _Step), material_loss / material_missed with the decaying mean"
provides:
  - "quiet_line_facts / quiet_best_line_facts: odd depths read at the first quiet point (D-02)"
  - "facepalm_material_inputs: the single write-time function for the stored loss and missed (D-03, D-04)"
  - "D13_FIXTURE: game 2883555 ply 47 pinned end to end"
affects: [259-02, 259-03, hook, line-pass, features-pull, fit]

actuals:
  tokens: 7200
  tasks: 2
  commits: 2
plan_head_before: eb3e76cc39d662ce1b95a2b4d4e394ed51c7fa9c
plan_head_after: ced2485b06ba8ca0b71d1e47d8c28c00cc44c8ca
commits: 2

tech-stack:
  added: []
  patterns:
    - "one counting step (_count_step) shared by the old and the quiet walk, so the desperado rule exists once"
    - "write-time scalars computed by the unchanged aggregation applied to quiet per-depth arrays"

key-files:
  created:
    - app/services/facepalm_inputs.py
    - tests/services/test_facepalm_inputs.py
  modified:
    - app/services/line_material.py
    - tests/services/line_material_fixtures.py
    - tests/services/test_line_material.py

key-decisions:
  - "Quiet walk implemented as a copy of the spike's rule on top of _Step/_replay_line, with _count_step extracted from _net_loss; line_facts, best_line_facts, _facts_after_first_move, _loss_at_depth and _recapture_credit untouched (D-11)"
  - "A mating first move returns before the empty-steps check so a one-token mating best line still gives opponent_mate_ply 0 (Pitfall 2)"

patterns-established:
  - "Stored material inputs come only from facepalm_material_inputs (callers pass best_pv or best_move)"

requirements-completed: [D-02, D-03, D-04, D-13]

coverage:
  - id: D1
    description: "Quiet-point walk: each odd depth is read past every following capture, a line ending mid-exchange is settled by a static exchange on the last capture's square, desperado exclusion and mate rules kept"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/services/test_line_material.py#test_label_fixture_quiet_rule"
        status: pass
      - kind: unit
        ref: "tests/services/test_line_material.py#test_quiet_synthetic_rules"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stored loss and missed are the decaying mean over the odd depths via the unchanged material_loss / material_missed, with the NULL pair and unknown-best-line encodings"
    requirement: "D-03, D-04"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_inputs.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Game 2883555 ply 47 reads missed 0.0 and loss 91/31 (shipped rule 80/31)"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_inputs.py#test_d13_missed_gain_is_zero_under_the_quiet_rule"
        status: pass
      - kind: unit
        ref: "tests/services/test_facepalm_inputs.py#test_d13_shipped_rule_reads_a_missed_gain"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live arrays unchanged: every pre-existing old-rule test in test_line_material.py passes untouched"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "uv run pytest tests/services/test_line_material.py -k 'not quiet'"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 01: Quiet-point material rule and the stored material inputs Summary

**Quiet-point walk (`quiet_line_facts` / `quiet_best_line_facts`) plus the single writer `facepalm_material_inputs`, proven on game 2883555 ply 47 (loss 91/31, missed 0.0 where the shipped rule read 80/31).**

## Performance

- **Duration:** 22 min
- **Completed:** 2026-11-21T16:13Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- `_count_step` extracted from `_net_loss` (desperado rule exists once); the old walk returns exactly what it did.
- Quiet walk: `depth` plies, then on while the next move is a capture on any square; a line ending inside an exchange is settled by `_best_recapture` (opponent's last capture counts for the blunderer, the blunderer's last capture against them).
- New `app/services/facepalm_inputs.py`: `STORED_MATERIAL_INPUT = "decaying_mean"`, `MaterialInputs`, `material_inputs_from_facts` (works on either rule's facts, for the plan-02 baseline), `facepalm_material_inputs`.
- Fixtures: `expected_quiet_loss` on all 17 `LINE_FIXTURES` (13 copy `expected_loss`; 153/154/156/170 carry the spike values), `MaterialInputsFixture`, `D13_FIXTURE`.
- Tests: 17 fixture cases, a 6-row synthetic table (even four-capture trade, both settlement signs, desperado, too short), null/mutation guards, D-13 both rules, mating one-token best line, mate loss, NULL pair, unknown best line.

## Task Commits

1. **Task 1: Tracer, D-13 end to end** - `6307acd51` (feat)
2. **Task 2: Quiet walk on every fixture and D-02 edge case** - `ced2485b0` (test)

**Plan metadata:** the docs commit following this file.

## Files Created/Modified
- `app/services/line_material.py` - `_count_step`, `_quiet_walk_end`, `_ends_in_exchange`, `_quiet_loss`, `_quiet_facts_after_first_move`, `quiet_line_facts`, `quiet_best_line_facts`
- `app/services/facepalm_inputs.py` - the stored-inputs writer
- `tests/services/line_material_fixtures.py` - `expected_quiet_loss`, `MaterialInputsFixture`, `D13_FIXTURE`
- `tests/services/test_line_material.py`, `tests/services/test_facepalm_inputs.py` - tests above

## Decisions Made
- Followed the plan. The synthetic expectations were derived by hand from the rule (not by running the code) and all matched on the first run.

## Deviations from Plan

None - plan executed exactly as written. (Small addition within scope: `_ends_in_exchange` helper to keep `_quiet_loss` shallow.)

## Issues Encountered
None. Mutation check (done instead of trusting green): disabling the capture walk fails 8 tests, dropping the settlement sign fails 3; both reverted.

## Verification
- `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_inputs.py`: 112 passed
- `uv run pytest tests/services/test_line_material.py -k "not quiet"`: 63 passed (old rule untouched)
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check app/ tests/`, `check_function_size.py app/ --fail-over-depth 4`: clean
- Tracer gate: interactive, end-of-phase mode, automated-only verify: re-run green, expanded.

## Known Stubs
None.

## Threat Flags
None. T-259-01 mitigated (same `_parse_move` and legality guards, `test_quiet_unusable_input_gives_null_facts`); T-259-02 mitigated (live functions untouched, old-rule tests green).

## Next Phase Readiness
Ready for plan 02: `material_inputs_from_facts` accepts the shipped rule's facts for the D-12 baseline.

## Self-Check: PASSED
