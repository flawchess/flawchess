---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
plan: 01
subsystem: tactics
tags: [python-chess, tactic-detector, fen, en-passant, forced-mate, precision-gate]

# Dependency graph
requires:
  - phase: 141-147 (v1.30 Forcing-Line Tactic Gate)
    provides: detect_tactic_motif dispatcher, forcing-line gate, classify pipeline
provides:
  - has_forced_mate mate-fallback branch so truncated (PV_CAP_PLIES-capped) forced
    mates tag generic MATE instead of silently dropping
  - _recompute_fen_map full-FEN storage so ep/castling flaw positions replay correctly
affects: [tactic-detector, flaws-service, tagger precision gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Detector-internal fen_map is the one sanctioned exception to CLAUDE.md's board_fen()-only rule (D-02)"
    - "Persisted/API-facing FlawRecord.fen keeps the piece-placement-only contract by splitting the full FEN at the construction site"

key-files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - app/services/flaws_service.py
    - tests/services/test_tactic_detector.py
    - tests/services/test_flaws_service.py

key-decisions:
  - "D-01: truncated forced-mate PV tags generic MATE (not suppressed); named-mate subtypes skipped since geometry can't be verified on a truncated line"
  - "D-02: fen_map stores full board.fen() for detector-internal PV replay only; Zobrist/position-comparison call sites keep board_fen()"
  - "D-03: precision gate re-run is a regression check only for Bug A -- the gate harness never passes has_forced_mate=True, so the dedicated unit test is the real validation (per RESEARCH.md)"
  - "Deviation (Rule 1, scope preservation): FlawRecord.fen / persisted game_flaws.fen column must stay piece-placement-only (downstream library.py reconstructs side-to-move via ply parity) -- split the full FEN back to board_fen()-only at the FlawRecord construction site rather than changing that column's contract"

patterns-established:
  - "When a shared helper (fen_map) has two consumers with different FEN-format needs, split the format at the narrower consumer's construction site rather than changing the shared source's contract wholesale"

requirements-completed: [ITEM-1]

coverage:
  - id: D1
    description: "Truncated forced-mate PV tags generic MATE with has_forced_mate=True, and stays None with the flag off (flag-gate regression guard)"
    requirement: "ITEM-1"
    verification:
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestHasForcedMateFallback::test_truncated_mate_with_flag_tags_mate"
        status: pass
      - kind: unit
        ref: "tests/services/test_tactic_detector.py::TestHasForcedMateFallback::test_truncated_mate_without_flag_returns_none"
        status: pass
    human_judgment: false
  - id: D2
    description: "fen_map preserves side-to-move/castling/en-passant so an en-passant-capture flaw SAN parses and the captured pawn is removed"
    requirement: "ITEM-1"
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestFenMapEpCapture::test_ep_target_recorded_and_capture_replays"
        status: pass
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestFenMapEpCapture::test_detect_tactic_for_flaw_replays_ep_capture_without_parse_error"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tactic precision gate passes with no motif regressing below its floor after both fixes"
    requirement: "ITEM-1"
    verification:
      - kind: unit
        ref: "tests/scripts/tagger/test_detector_precision.py::test_detector_precision_and_recall"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-04
status: complete
---

# Phase 148 Plan 01: Tactic mate-fallback + fen_map ep/castling fix Summary

**Truncated forced-mate PVs now tag generic MATE (was silently dropped) and fen_map stores full FEN so en-passant/castling flaws replay correctly, without changing the persisted FlawRecord.fen API contract.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2 completed
- **Files modified:** 4

## Accomplishments

- Fixed Bug A: `detect_tactic_motif`'s `has_forced_mate=True` fallback previously reached every per-detector mate function, but each one bails via `if not boards[-1].is_checkmate()` when the PV is truncated at `PV_CAP_PLIES=12` — a genuine Stockfish-reported mate silently fell through untagged. Added a fallback branch that tags the generic `MATE` motif (skipping geometry-dependent subtypes, which can't be verified on a truncated line) when `has_forced_mate` is set and the PV hasn't reached checkmate.
- Fixed Bug B: `_recompute_fen_map` stored `board.board_fen()` (piece placement only), dropping side-to-move/castling/en-passant state. Reconstructing a `chess.Board` from that string made an en-passant-capture SAN illegal, corrupting PV replay for any flaw at or after an ep capture. Both storage sites now use `board.fen()`.
- Preserved the persisted/API-facing `FlawRecord.fen` (→ `game_flaws.fen` DB column) contract unchanged by splitting the piece-placement field off the full FEN at the `FlawRecord` construction site — this column is consumed downstream by `app/schemas/library.py`'s `position_fen` reconstruction (piece-placement + ply-parity side-to-move), which is out of scope per D-02 ("detector-internal map only").
- Added `TestHasForcedMateFallback` (2 tests: with-flag tags MATE, without-flag stays None) using a real 12-ply (`PV_CAP_PLIES`) truncated line already verified quiet by the existing `_HARD_NEGATIVES` fixture set.
- Inverted `TestFenRecompute`'s 4 pre-existing assertions to encode the fixed full-FEN contract (per 148-RESEARCH.md's inversion table) and added `TestFenMapEpCapture` with a real en-passant-capture PGN fixture, verifying both the raw FEN mechanics and the full `_detect_tactic_for_flaw` consumption path.
- Re-ran the tactic precision gate (green, no motif regression) and the full backend suite (3192 passed) to confirm no unrelated regressions from the `fen_map`/`FlawRecord.fen` split.

## Task Commits

Each task was committed atomically:

1. **Task 1: has_forced_mate mate-fallback branch (Bug A, D-01)** - `3c654437` (fix)
2. **Task 2: fen_map full-FEN storage + ep/castling fixture (Bug B, D-02)** - `ee206c9b` (fix)

_No plan-metadata commit yet — this SUMMARY/STATE/ROADMAP update is the final commit for this plan._

## Files Created/Modified

- `app/services/tactic_detector.py` - New `has_forced_mate` fallback branch inside `detect_tactic_motif`, after the Tier-1 mate cascade
- `app/services/flaws_service.py` - `_recompute_fen_map` now returns full `board.fen()`; `_build_flaw_record` (the `FlawRecord(...)` constructor) splits off the piece-placement field to preserve the persisted column's contract; stale comment at the `_detect_tactic_for_flaw` consumption site updated
- `tests/services/test_tactic_detector.py` - New `TestHasForcedMateFallback` class (2 tests)
- `tests/services/test_flaws_service.py` - `TestFenRecompute` inverted (4 tests + docstring + rename `test_board_fen_not_full_fen` → `test_full_fen_not_board_fen`); new `TestFenMapEpCapture` class (2 tests); updated `test_fen_is_decision_point_before_flawed_move` to account for the fen_map/FlawRecord.fen format split

## Decisions Made

- **D-01** (locked in CONTEXT.md): tag generic `mate` on a truncated forced-mate PV rather than suppressing — the flag derives from a genuine Stockfish `eval_mate` score, only the PV replay is capped.
- **D-02** (locked in CONTEXT.md): `fen_map`'s full-FEN fix is detector-internal only; Zobrist/position-comparison `board_fen()` call sites are untouched.
- **D-03** (locked in CONTEXT.md): the precision gate re-run is a regression check, not fix-validation, for Bug A — confirmed per RESEARCH.md, the gate harness never passes `has_forced_mate=True`.
- **New (this plan, Rule 1 scope preservation):** `fen_map` turned out to be dual-purpose — it also populates the persisted `FlawRecord.fen`/`game_flaws.fen` column, which `app/schemas/library.py` and `app/repositories/library_repository.py` consume as piece-placement-only + ply-parity side-to-move reconstruction. Changing that column's format was NOT part of D-02's scope and would have silently broken `TacticLinesResponse.position_fen` construction (confirmed by a failing test: `ValueError: fen string has more parts than expected`). Fixed by splitting the full FEN back to `board_fen()`-only at the `FlawRecord` construction site, so the DB column and downstream API consumers are byte-identical to before this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved FlawRecord.fen / game_flaws.fen piece-placement-only contract**
- **Found during:** Task 2 (fen_map full-FEN storage)
- **Issue:** `_recompute_fen_map`'s output feeds both the detector-internal PV replay (`_detect_tactic_for_flaw`, needs full FEN per D-02) AND the persisted `FlawRecord.fen` field (`fen=fen_map.get(n, "")` at the `FlawRecord` construction site), which is stored as `game_flaws.fen` and consumed downstream by `app/schemas/library.py`'s `TacticLinesResponse.position_fen` (piece-placement + ply-parity side-to-move) and `app/repositories/library_repository.py` (same reconstruction pattern). Simply switching `fen_map` to full FEN broke this downstream reconstruction — a pre-existing test (`test_fen_is_decision_point_before_flawed_move`) failed with `ValueError: fen string has more parts than expected` because the downstream code appended a second side-to-move field onto an already-full FEN.
- **Fix:** Split the piece-placement field off the full FEN (`fen_before_flaw.split(" ")[0]`) at the `FlawRecord(...)` construction site, so `FlawRecord.fen`/`game_flaws.fen` remains byte-identical to the pre-fix format while `fen_map`'s internal values (used only by `_detect_tactic_for_flaw`) carry the full FEN needed for correct ep/castling replay.
- **Files modified:** `app/services/flaws_service.py`
- **Verification:** Full backend suite (3192 passed), `tests/repositories/test_library_repository.py` (17 passed, unaffected), `tests/services/test_flaws_service.py` (143 passed)
- **Committed in:** `ee206c9b` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — scope-preservation bug prevention)
**Impact on plan:** Necessary to honor D-02's explicit "detector-internal map only" scope boundary and avoid silently corrupting the API-facing tactic-lines FEN contract. No scope creep — no new features, just preserved the existing contract that the plan's literal fix would have broken.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both item-1 tactic production defects fixed and verified; no blockers for the remaining 148-0x plans (items 2-5, per D-06 plan decomposition).
- Full backend suite green (3192 passed, 18 skipped); tagger precision gate green; `ty check` clean.

## Post-review follow-up (CR-01)

The phase code review (`148-REVIEW.md`) caught a sign-convention regression in this
plan's own wiring: `has_forced_mate` in `_detect_tactic_for_flaw` tested the raw
white-perspective-absolute `eval_mate` against 0, inverting the result for black-POV
flaws (~half of all plies) — dropping real Black forced mates and mis-firing on White
mates during Black's move. Fixed in commit `729f7961` by converting to the POV side
via the existing `_pov_mate`/`_solver_color_for` helpers, with a
`TestDetectTacticForFlawForcedMatePov` regression class. Also folded in the two
review doc caveats (WR-01 `FlawRecord.fen` split-back note, WR-02 truncated-mate
`tactic_depth` approximation caveat). Full suite green (3203 passed).

---
*Phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: app/services/tactic_detector.py
- FOUND: app/services/flaws_service.py
- FOUND: tests/services/test_tactic_detector.py
- FOUND: tests/services/test_flaws_service.py
- FOUND: 3c654437
- FOUND: ee206c9b
