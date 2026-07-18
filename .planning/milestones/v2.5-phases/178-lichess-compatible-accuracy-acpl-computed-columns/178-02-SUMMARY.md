---
phase: 178-lichess-compatible-accuracy-acpl-computed-columns
plan: 02
subsystem: database
tags: [chess, stockfish, lichess, accuracy, acpl, formula-port, python]

# Dependency graph
requires:
  - phase: 178-01
    provides: "Migration adding *_imported columns, canonical white_accuracy/black_accuracy/white_acpl/black_acpl NULLed and repurposed for the uniform computed formula"
provides:
  - "app/services/accuracy_acpl.py — pure stdlib compute module implementing lichess's Win% (D-08), per-move accuracy (D-09), windowed game accuracy (D-10), and ACPL (D-11) formulas"
  - "compute_game_accuracy_acpl(positions, *, start_color='white') orchestrator with the post-move-shift eval mapping, mover-parity sign flip, and interior-hole completeness gate"
  - "Hand-checked lichess game 296343 fixture proving exact ACPL reproduction (18/61) and accuracy reconciliation within ±1 (84/61)"
affects: [178-03, 178-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single shared pure-compute module (no DB/IO) consumed by both the live hook (Plan 03) and the backfill script (Plan 04) — one formula implementation, never duplicated"
    - "Duck-typed PositionLike Protocol lets tests pass lightweight stand-ins instead of real GamePosition ORM rows"

key-files:
  created:
    - app/services/accuracy_acpl.py
    - tests/services/test_accuracy_acpl.py
  modified: []

key-decisions:
  - "Corrected the RESEARCH.md/PLAN.md game-296343 fixture array: it drops one of five consecutive zeros at plies 9-13 (24 values instead of 25). Re-verified directly against dev DB game_positions and used the DB-confirmed sequence in the test fixture instead of the doc's copy."
  - "Terminal-eval-missing (checkmate final move) resolved via the +/-CP_CEILING mate-delivered convention rather than skipping the move — matches RESEARCH's explicit 'both give the same aggregate to <0.5%' allowance, and is simpler to reason about (uniform per-move loop, no move-skip branch)."
  - "compute_color_accuracy is fully self-contained (recomputes accuracy internally from win_seq + color) rather than accepting a pre-computed accuracy list, matching the plan's exact `compute_color_accuracy(win_seq_white_pov, color)` signature."
  - "Harmonic-mean zero-accuracy guard returns 0.0 directly for any list containing a value <= 0.0, reproducing lichess's mathematical collapse-toward-zero semantics without a fragile epsilon substitution."

patterns-established:
  - "Pure-formula modules key eval lookups by explicit dict[ply] mapping, never by list index — defensive against gaps in the positions list."

requirements-completed: []

coverage:
  - id: D1
    description: "win_pct (D-08): pre-sigmoid ±1000 ceiling, clamped winning-chances, symmetric around 50"
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestWinPctAndMoveAccuracy"
        status: pass
    human_judgment: false
  - id: D2
    description: "move_accuracy (D-09): exponential decay with the +1 uncertainty bonus, 100 when position doesn't worsen"
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestWinPctAndMoveAccuracy"
        status: pass
    human_judgment: false
  - id: D3
    description: "compute_game_accuracy_acpl reproduces lichess game 296343 exactly: white_acpl=18, black_acpl=61"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestAcplFixture::test_acpl_fixture"
        status: pass
    human_judgment: false
  - id: D4
    description: "Windowed game accuracy (D-10) reconciles within ±1 of lichess's own imported accuracy (84/61)"
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestGameAccuracyFixture::test_game_accuracy_fixture"
        status: pass
    human_judgment: false
  - id: D5
    description: "Interior eval hole returns None (all four values NULL); terminal-only NULL is not a hole"
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestIncompleteSequenceReturnsNone"
        status: pass
    human_judgment: false
  - id: D6
    description: "Edge cases: 0-move game, 1-move game, mid-game mate routing, checkmate final move, harmonic-mean zero-accuracy guard"
    verification:
      - kind: unit
        ref: "tests/services/test_accuracy_acpl.py::TestEdgeCases"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-18
status: complete
---

# Phase 178 Plan 02: Pure Accuracy/ACPL Compute Module Summary

**`app/services/accuracy_acpl.py` — a pure stdlib port of lichess's Win%/per-move-accuracy/windowed-game-accuracy/ACPL formulas, proven against lichess game 296343's real eval sequence (exact ACPL match, accuracy within ±1).**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-18T10:50Z
- **Completed:** 2026-07-18T11:02Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- `app/services/accuracy_acpl.py`: `win_pct` (D-08), `move_accuracy` (D-09), `compute_color_accuracy` (D-10, windowed-stddev-weighted), `compute_color_acpl` (D-11, plain mean), and the public orchestrator `compute_game_accuracy_acpl` — all with named constants (`CP_CEILING`, `MOVE_ACC_A/B/C`, `INITIAL_SEED_CP`, `MIN_WINDOW`/`MAX_WINDOW`, `MIN_WEIGHT`/`MAX_WEIGHT`), importing `LICHESS_K` from `eval_utils` rather than re-declaring it.
- Correct post-move-shift eval mapping (`eval_of_position[ply+1] = row(ply).eval`), mover-parity sign flip (White departs even plies), and the interior-hole Complete-Sequence Gate (`_is_hole_free`) that authoritatively returns `None` regardless of any upstream completion stamp.
- 16 unit tests including the hand-checked game 296343 fixture (exact `white_acpl=18`/`black_acpl=61`) and a windowed-accuracy reconciliation against lichess's own imported `white_accuracy=84`/`black_accuracy=61` (both within ±1).
- Edge cases: 0-move game, 1-move game (White computed, Black `None`), mid-game `eval_mate` routing through the ±1000 ceiling (never the plain-cp path), a checkmating final move handled without error, and a literal 0.0 per-move accuracy proven not to raise in the harmonic-mean step.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure formula module — win%, per-move accuracy, windowed game accuracy, ACPL** - `2f3b3939` (feat)
2. **Task 2: Hand-checked fixture + edge-case unit tests** - `ca8922d1` (test)

## Files Created/Modified
- `app/services/accuracy_acpl.py` - Pure stdlib compute module (D-08..D-11) + `AccuracyAcplResult` dataclass + `PositionLike` Protocol.
- `tests/services/test_accuracy_acpl.py` - 16 DB-free unit tests (fixture + formula + edge cases).

## Decisions Made
- **Fixture correction:** RESEARCH.md/PLAN.md's embedded game-296343 eval sequence has only 24 values where 25 are needed — it silently drops one of five consecutive zeros at plies 9-13. Verified directly against dev DB `game_positions` (`docker exec flawchess-dev-db-1 psql ...`) and used the DB-confirmed 25-value sequence (five zeros, not four) in the test fixture. Reproduces the exact `white_acpl=18`/`black_acpl=61` and `white_accuracy≈84.01`/`black_accuracy≈61.18` lichess values, confirming both the formula and the correction.
- **Checkmate-final-move convention:** resolved via the `+/-CP_CEILING` mate-delivered treatment (uniform per-move loop, no skip-branch), per RESEARCH's explicit allowance that both treatments give the same aggregate to <0.5%.
- **`compute_color_accuracy` signature:** kept fully self-contained per the plan's exact spec (`win_seq_white_pov`, `color`) — it derives per-move accuracy internally rather than accepting an externally-computed list, avoiding an extra parameter/coupling point.
- **Harmonic-mean zero guard:** any accuracy `<= 0.0` in the list short-circuits to `0.0`, matching lichess's Scala `harmonicMean` collapse-toward-zero semantics exactly (not an epsilon-substitution workaround).

## Deviations from Plan

None beyond the fixture-array correction documented above (an auto-fixed Rule 1 bug in the *source documentation*, not the implementation — the plan's own acceptance criteria required exact `white_acpl=18`/`black_acpl=61`, and using the doc's literal 24-value array would have produced a different, wrong ACPL). No architectural changes, no scope creep.

## Issues Encountered
- The plan's embedded fixture array (`178-RESEARCH.md` § "Worked example" and `178-02-PLAN.md` Task 2) is missing one element (24 values instead of 25) — traced to a dropped zero in a run of five consecutive `0` values at plies 9-13. Resolved by querying the dev DB directly for the authoritative sequence rather than debugging the doc's copy further.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `compute_game_accuracy_acpl` is ready to be called from both the live full-eval-completion hook (Plan 03, `eval_apply.py::_classify_and_fill_oracle`) and the backfill script (Plan 04) — the single shared compute path is in place and proven.
- No blockers. The module is DB-free and imports cleanly; `uv run ty check app/ tests/` is zero-error.

---
*Phase: 178-lichess-compatible-accuracy-acpl-computed-columns*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: app/services/accuracy_acpl.py
- FOUND: tests/services/test_accuracy_acpl.py
- FOUND: .planning/phases/178-lichess-compatible-accuracy-acpl-computed-columns/178-02-SUMMARY.md
- FOUND commit: 2f3b3939 (feat)
- FOUND commit: ca8922d1 (test)
- FOUND commit: 63e47961 (docs: complete plan)
