---
phase: 149-retire-prune
plan: 02
subsystem: import
tags: [chess.com, normalization, sentry, wdl-integrity]

# Dependency graph
requires:
  - phase: 148-pipeline-correctness-fixes
    provides: per-game exception-based skip channel in chesscom_client.py (Phase 148 CORR-05)
provides:
  - Unknown chess.com result combinations skip the game instead of fabricating a draw
  - Sentry capture_message with grouping-safe set_context on the unknown branch
affects: [150-consolidate-write-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Internal helper signals an out-of-band None distinct from a public Literal type, so the Literal never needs widening (D-07)"

key-files:
  created: []
  modified:
    - app/services/normalization.py
    - tests/test_normalization.py

key-decisions:
  - "D-07 upheld: GameResult Literal NOT widened; _normalize_chesscom_result's return type widened to GameResult | None instead"
  - "Unknown-result skip reuses the existing `if normalized is not None: yield` gate in chesscom_client.py verbatim — zero caller change"

patterns-established:
  - "Sentry capture_message with a constant message string; variable data (white_result/black_result) only in set_context, never interpolated"

requirements-completed: [PRUNE-03]

coverage:
  - id: D1
    description: "Unrecognized chess.com white/black result pair no longer fabricates a draw — normalize_chesscom_game returns None and the game is skipped"
    requirement: "PRUNE-03"
    verification:
      - kind: unit
        ref: "tests/test_normalization.py::TestNormalizeChesscomResult::test_unrecognized_result_pair_returns_none"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unknown-result branch emits exactly one Sentry capture_message with white_result/black_result carried via set_context, never interpolated into the message string"
    requirement: "PRUNE-03"
    verification:
      - kind: unit
        ref: "tests/test_normalization.py::TestNormalizeChesscomResult::test_unrecognized_result_pair_captures_sentry_with_context_not_message"
        status: pass
    human_judgment: false
  - id: D3
    description: "A genuine draw still normalizes to '1/2-1/2' and is not captured to Sentry"
    requirement: "PRUNE-03"
    verification:
      - kind: unit
        ref: "tests/test_normalization.py::TestNormalizeChesscomResult::test_genuine_draw_is_not_captured_to_sentry"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-07-04
status: complete
---

# Phase 149 Plan 2: PRUNE-03 Unknown Chess.com Result Skip + Sentry Capture Summary

**Replaced `_normalize_chesscom_result`'s silent-draw fallback with an explicit "unknown" out-of-band signal, so an unrecognized chess.com outcome skips the game and Sentry-captures instead of polluting WDL stats with a fabricated draw.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-04T11:40:36Z
- **Completed:** 2026-07-04T11:46:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `_normalize_chesscom_result` return type widened to `GameResult | None`; the terminal `return "1/2-1/2"  # safe fallback` branch now returns `None` for genuinely unrecognized white/black result pairs, with a fix-site comment explaining what broke and why
- `normalize_chesscom_game` treats the `None` signal as a skip: emits `sentry_sdk.set_context("chesscom_result", {...})` + a constant `sentry_sdk.capture_message(...)` (no variable interpolation), then returns `None`
- The unknown skip flows through the pre-existing `if normalized is not None: yield` gate in `chesscom_client.py` with zero caller changes — confirmed by reading the gate, no edits made there
- 3 new regression tests added to the existing `TestNormalizeChesscomResult` class: unknown pair -> None, capture-shape assertion (set_context + capture_message, message contains no result values), genuine draw -> `1/2-1/2` with zero Sentry calls
- `GameResult` Literal (`app/schemas/normalization.py:13`) confirmed untouched — still exactly `["1-0", "0-1", "1/2-1/2"]`

## Task Commits

Each task was committed atomically:

1. **Task 1: Signal unknown result out-of-band, skip + Sentry-capture** - `57a9463a` (fix)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `app/services/normalization.py` - `_normalize_chesscom_result` returns `GameResult | None` (unknown -> `None`); `normalize_chesscom_game` skips + Sentry-captures on the unknown signal
- `tests/test_normalization.py` - 3 new tests in `TestNormalizeChesscomResult` covering the skip, the capture shape (set_context vs message), and the still-unaffected genuine-draw path

## Decisions Made
- Followed D-07 (RESEARCH.md / CONTEXT.md) exactly: widened the internal helper's return type rather than the public `GameResult` Literal.
- Reused the existing `chesscom_client.py` skip gate verbatim (no caller edits) — confirmed via read that `if normalized is not None: yield` already tolerates this extra skip case identically to the non-standard-variant skip.
- Used `unittest.mock.patch` on `app.services.normalization.sentry_sdk.{set_context,capture_message}`, matching the existing precedent in `tests/test_chesscom_client.py`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The plan's acceptance criteria required `grep -n "safe fallback" app/services/normalization.py` to return nothing. My first draft of the fix-site comment quoted the old code (`return "1/2-1/2"  # safe fallback`) verbatim, which still matched the grep. Reworded the comment to describe the old behavior without repeating the literal string, then reconfirmed the grep returns no match. No behavior change, single edit — not tracked as a Rule 1-3 deviation since it hit before any commit and just satisfies a plan-authored grep-based acceptance check.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PRUNE-03 fully closed: unknown chess.com results are skipped with a grouping-safe Sentry capture; `GameResult` untouched.
- Full backend suite (3208 passed, 18 skipped) confirms zero regressions from this change across the rest of the import/eval pipeline.
- No blockers for Phase 149's remaining plans (PRUNE-01/02/04/05/06) or Phase 150.

## Self-Check: PASSED

- FOUND: app/services/normalization.py
- FOUND: tests/test_normalization.py
- FOUND: commit 57a9463a

---
*Phase: 149-retire-prune*
*Completed: 2026-07-04*
