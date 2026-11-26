---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 01
subsystem: backend-services
tags: [line-material, facepalm, best-line, signed-material, tdd]
requires: []
provides:
  - "best_line_facts(pre_board, best_pv) with the 250 D-02 counting rules"
  - "LineFacts.material_at / material_array / opponent_mate_ply"
  - "material_at_depth(stored_array, depth) reader, LINE_MATERIAL_SLOTS / LINE_MATERIAL_DEPTHS"
  - "OWNER_MISS_FIXTURES (embedded, no DB dependency)"
affects: [254-02, 254-03, 254-04, 254-05, 254-15, 254-16]
tech-stack:
  added: []
  patterns: ["one shared counting helper for played and best line", "signed accessor at the output layer only"]
key-files:
  created: []
  modified:
    - app/services/line_material.py
    - tests/services/line_material_fixtures.py
    - tests/services/test_line_material.py
key-decisions:
  - "Shared _facts_after_first_move helper: line_facts and best_line_facts share one counting implementation; a first move that mates settles every depth at its capture value with opponent_mate_ply 0"
  - "A mate of either side within steps[:depth] settles the depth (opponent_mated added to _Step)"
  - "loss_by_depth is computed for depths 1..9; as_columns still emits only the legacy odd depths 1/3/5/7/9, so the legacy line_loss_* dual-write is unchanged"
requirements-completed: [D-05, D-09, D-17]
status: complete
duration: 25 min
completed: 2026-11-14
plan_head_before: 570fe693e14edac6e0d29e484121386b11a7ad68
plan_head_after: 1de05d5ea6c202421a13b2f3d039031c6a3d9fd9
commits: 3
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
---

# Phase 254 Plan 01: Best-line facts and signed 9-slot material arrays Summary

Line facts for both the played line and the best line as signed 9-slot material arrays, replaying the owner miss fixtures end to end through the real counting code.

## Accomplishments

- `best_line_facts(pre_board, best_pv)`: first token of `game_positions.pv` at the flaw ply is the best move, the rest is its line; same counting rules as `line_facts`, one shared private helper. Malformed, illegal, None or empty best line gives all-None facts and never raises; a non-mating one-token line is "too short" (None); a best move that mates settles every depth with `opponent_mate_ply == 0`.
- Opponent mate settles a depth (`_Step.opponent_mated`), `LineFacts.opponent_mate_ply` (first move = ply 0, so mate-in-2 = 2).
- Signed accessors: `material_at(depth) == -loss_at(depth)`, `material_array()` (9 slots, slot N-1 = depth N), `material_at_depth(stored, depth)` for stored arrays (None/empty/short gives None).
- Even depths documented as mid-exchange values (D-17, research Pitfall 14), computed with the existing rule.
- Owner fixtures (data copied read-only from the dev DB): game 817357 ply 24 gives played 0 / best +3, game 820181 ply 65 gives played +5 / best +10, matching the D-05 table (missed 3 and 5).

## Tests

`uv run pytest tests/services/test_line_material.py` : 63 passed (43 after Task 1, plus 20 new in Task 2 including parametrised 250 fixtures). The 17 Phase 250 fixture expected values are untouched. `ruff`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean.

## Deviations from Plan

None - plan executed exactly as written. Dev DB values matched the RESEARCH Pattern 2 values, so no fixture difference to record.

Minor notes: the per-plan commit ledger file under the git dir could not be written (worktree tooling refuses git-dir paths), so `plan_head_before` is the worktree base SHA the orchestrator dispatched with (verified equal to HEAD at start), and `commits: 3` was measured with `git rev-list --count` against it (TDD split Task 2 into a RED test commit and a GREEN feat commit).

## Known Stubs

None.

## Threat Flags

None. T-254-01 (worker-supplied pv tokens) mitigated: first token parsed via `_parse_move` and legality-checked, covered by `test_best_line_bad_tokens_null`.

## Commits

- 8e710dd42 feat(254-01): best-line facts and signed depth-3 material for both lines (Task 1)
- 47c90e190 test(254-01): nine-slot signed material array and stored-array reader (RED)
- 1de05d5ea feat(254-01): nine-slot signed material arrays and stored-array reader (GREEN)

## Self-Check: PASSED

Files exist (`app/services/line_material.py`, `tests/services/line_material_fixtures.py`, `tests/services/test_line_material.py`), all three commits are on HEAD, tests/ty/size gate pass.
