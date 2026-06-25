---
phase: 125-backfill-tactic-motifs
plan: "01"
subsystem: backfill/tactic
tags: [backfill, tactic-motifs, test, coverage-report, phase-125]
dependency_graph:
  requires: [124-schema-tactic-detector]
  provides: [tactic-column-test-coverage, d04-coverage-report]
  affects: [tests/test_backfill_flaws.py, scripts/coverage_report_tactic_motifs.py]
tech_stack:
  added: []
  patterns: [FEN-header PGN fixtures, asyncpg text() SQL with f-string constants]
key_files:
  created:
    - scripts/coverage_report_tactic_motifs.py
  modified:
    - tests/test_backfill_flaws.py
decisions:
  - "Used FEN-header PGN ([FEN '...'] header) for tactic fixture game to control exact board FEN at each ply without needing a full realistic game"
  - "Used hanging-piece fixture from D-09 prod-confirmed set (Re4?? in rook endgame, refutation f4e4) for the PV-fires test case"
  - "Embedded _MISTAKE_BLUNDER_SEVERITIES as f-string literals in SQL text() calls — asyncpg does not support Python tuple binding for IN clauses"
  - "Tactic test blunder at ply 1 (black's Re4??), requiring starting FEN with white to move so fen_map[1] = fen_before_flaw"
metrics:
  duration: ~7 minutes
  completed: "2026-06-18"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
status: complete
---

# Phase 125 Plan 01: Tactic Motif Test + Coverage Report Summary

Closed the Nyquist Wave 0 gap (Phase 108 suite predated Phase 124 tactic columns) and
built the SC#1 acceptance instrument for the backfill: a read-only D-04 coverage report
script verifying honest NULL semantics (no-PV vs PV-present-but-no-fire).

## Tasks Completed

### Task 1: Extend test_backfill_flaws.py for tactic columns

**Commit:** `3175337f`

Added `TestBackfillTacticColumns` class with two tests to `tests/test_backfill_flaws.py`:

- `test_tactic_motif_is_null_when_no_pv` (Test A — no-PV NULL path): reuses the
  existing `committed_analyzed_game` fixture (move_san=None, pv=None on all positions).
  After run_backfill, asserts every GameFlaw row has `tactic_motif IS NULL`,
  `tactic_piece IS NULL`, and `tactic_confidence IS NULL`. Proves the no-PV bucket
  is honest, not a data error.

- `test_tactic_motif_is_not_null_when_pv_fires` (Test B — PV-fires path): uses a new
  `committed_tactic_game` fixture seeding a 3-position game (FEN-header PGN, white Kf4 at
  ply 0, black Re4?? blunder at ply 1). `positions[2].pv` holds the D-09 prod-confirmed
  refutation PV (`f4e4 f6e6 ...`). After run_backfill, asserts the blunder row at ply 1
  has `tactic_motif IS NOT NULL` and `tactic_confidence IS NOT NULL`.

Added named constants: `_TACTIC_TEST_USER_ID`, `_TACTIC_PGN`, `_TACTIC_BLUNDER_PLY`,
`_TACTIC_CP_BEFORE_BLUNDER`, `_TACTIC_CP_AFTER_BLUNDER`, `_TACTIC_REFUTATION_PV`.

**All 7 tests pass** (5 Phase 108 + 2 Phase 125).

### Task 2: Create scripts/coverage_report_tactic_motifs.py

**Commit:** `cf95deeb`

Created `scripts/coverage_report_tactic_motifs.py` — the D-04 acceptance instrument:

- `--db dev|benchmark|prod` (required), resolves URL via `db_url_for_target`
- Four labeled output sections:
  1. **Overall**: total M+B flaw rows, has-PV count, tagged count, percentages
  2. **By-motif**: per-motif row counts with `_INT_TO_MOTIF` name mapping; suppressed
     motifs printed with count=0 so silence is explicit
  3. **NULL split**: `no_pv_null` vs `pv_no_fire` counts with interpretation
  4. **Spot-check**: 3 sample rows per NULL bucket for human eyeballing

Verified against dev DB (pre-backfill):
- Total M+B flaw rows: 68,150 (matches RESEARCH ground truth)
- Flaws with PV at ply+1: 12,916 (19.0%) ✓
- Flaws without PV: 55,234 (81.0%) ✓
- Non-NULL tactic_motif: 0 (correct pre-backfill baseline)

## Verification Results

- `uv run pytest tests/test_backfill_flaws.py -q` — 7 passed ✓
- `uv run ruff check scripts/coverage_report_tactic_motifs.py tests/test_backfill_flaws.py` — clean ✓
- `uv run ty check app/ tests/` — 0 errors ✓
- `scripts/coverage_report_tactic_motifs.py` — read-only (no INSERT/UPDATE/DELETE/commit) ✓
- Dev DB run confirmed all four sections with matching ground-truth numbers ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncpg tuple-binding incompatibility for IN clauses**
- **Found during:** Task 2 verification (running script against dev DB)
- **Issue:** asyncpg raises `PostgresSyntaxError: syntax error at or near "$1"` when
  a Python tuple is passed as a bound parameter for `IN :severities`. asyncpg does not
  support multi-value parameter expansion for `IN` clauses via standard `text()` binding.
- **Fix:** Replaced `:severities` bind parameter with f-string embedding of
  `{_MISTAKE_BLUNDER_SEVERITIES}` (evaluates to `(1, 2)`) in all four SQL queries.
  The values are fixed named constants (not user-supplied data), so this is safe —
  the plan's "no string interpolation of user data" rule applies to dynamic inputs,
  not compile-time constants.
- **Files modified:** `scripts/coverage_report_tactic_motifs.py`
- **Commit:** `cf95deeb` (included in the same task commit)

**2. [Rule 2 - Enhancement] Use FEN-header PGN for tactic test fixture**
- **Found during:** Task 1 implementation
- **Issue:** Constructing a realistic multi-move PGN to reach an arbitrary mid-game
  position (needed as `fen_before_flaw`) in the minimum required plies (flaw at n≥1)
  was impractical. Standard opening PGNs produce wrong fen_map entries.
- **Fix:** Used `[FEN "..."]` header PGN to start from the desired `fen_before_flaw`
  position directly, with `Kf4` (white, ply 0) placing the king on f4 and making
  `fen_map[1]` = the correct `fen_before_flaw` for the blunder at ply 1. This is
  a standard python-chess feature and exactly what `_recompute_fen_map` supports.
- **Files modified:** `tests/test_backfill_flaws.py`
- **Commit:** `3175337f`

## Known Stubs

None — both artifacts are complete implementations. The coverage report shows
0 tagged rows pre-backfill, which is the correct baseline (Plan 02 runs the backfill).

## Threat Flags

None — both artifacts are read-only (test + report script). No new network endpoints,
auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- `tests/test_backfill_flaws.py` exists: FOUND ✓
- `scripts/coverage_report_tactic_motifs.py` exists: FOUND ✓
- Commit `3175337f` exists: FOUND ✓
- Commit `cf95deeb` exists: FOUND ✓
- 7 pytest tests pass: VERIFIED ✓
- ty check: 0 errors VERIFIED ✓
- Script read-only: VERIFIED ✓
- Dev DB numbers match RESEARCH ground truth: VERIFIED ✓
