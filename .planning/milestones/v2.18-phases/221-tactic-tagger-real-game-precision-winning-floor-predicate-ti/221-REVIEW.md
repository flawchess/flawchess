---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
reviewed: 2026-09-13T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/services/flaws_service.py
  - app/services/forcing_line_gate.py
  - app/services/tactic_detector.py
  - frontend/src/lib/tacticComparisonMeta.ts
  - frontend/src/lib/tacticMotifDefinitions.ts
  - frontend/src/lib/theme.ts
  - scripts/research/dev_probe.py
  - scripts/research/oracle_compare.py
  - scripts/research/sample_realgame_tags.py
  - scripts/retag_flaws.py
  - scripts/tactic_tagger_report.py
  - tests/scripts/tagger/conftest.py
  - tests/scripts/tagger/precision_floors.py
  - tests/scripts/tagger/test_detector_precision.py
  - tests/scripts/test_ab_validate_gate.py
  - tests/scripts/test_retag_flaws.py
  - tests/services/test_flaws_service.py
  - tests/services/test_forcing_line_gate.py
  - tests/services/test_tactic_comparison_service.py
  - tests/services/test_tactic_detector.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 221: Code Review Report

**Reviewed:** 2026-09-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found (no blockers; minor findings only)

## Summary

Reviewed the phase-221 hunks (`git diff 3ceab603a d139075e8`) across the tactic-detector
gate/floor rewrite (D-01/D-04/D-06/D-07/D-09/D-11/D-12), the `retag_flaws.py` full-FEN
fix (TAGFIX-09), the clearance-family suppression sweep across backend/frontend, and the
new operator research scripts + their test/fixture scaffolding.

This is unusually well-instrumented work: every behavioral change is backed by a
docstring citing the specific measurement that motivated it, `SUPPRESSED_MOTIFS` /
`PRECISION_FLOOR` / `REALGAME_REAL_SHARE_FLOOR` track before/after numbers per motif, and
the riskiest changes (fen_map castling/en-passant fix, missed-orientation move-stack
parity, discovered-attack depth semantics, boden/double-bishop file test, the D-01 winning
floor) each have a dedicated behavioral test that fails on the old code path. I traced the
following specifically and found them internally consistent and correctly wired:

- `_build_missed_board_with_stack` / `flaws_service._classify_tactic_gated`'s new D-03
  blob-missing fallback and D-04 mate-derived already-winning reject — index arithmetic
  (`positions[n-1]` for missed, `positions[n]` for allowed) matches the pre-existing
  `_build_flaw_record` convention and is exercised by dedicated tests
  (`TestClassifyTacticGated`, `TestMissedOrientationParity`).
- `forcing_line_gate._solver_eval_at_firing` / `_passes_winning_floor` / the new
  `floor_cp_for_motif` map in `tactic_detector.py` — derived from the dispatcher's own
  tier registries (not hand-duplicated), verified with
  `test_floor_cp_for_motif_covers_every_registry_motif`.
- `scripts/retag_flaws.py`'s `_load_fen_maps_for_page` / `_worker_recompute` fen_map wiring
  — the previous single-entry placement-only `{ply: game_flaws.fen}` map is replaced with a
  real per-game full-FEN slice from `_recompute_fen_map(game.pgn)`, covered end-to-end by
  `test_castling_flaw_parity` / `test_en_passant_missed_parity`.
- The `except X, Y:` bare-tuple exception syntax appearing in several new/edited functions
  (`flaws_service._same_dest_as_best_line`, `_build_missed_board_with_stack`,
  `scripts/research/dev_probe.py`, `scripts/research/sample_realgame_tags.py`,
  `tests/scripts/tagger/conftest.py::build_realgame_board`) is **not** a bug — this project
  runs Python 3.14 (per `CLAUDE.md`), which accepts PEP 758's parenthesis-free
  multi-exception `except` clause; confirmed by executing the exact pattern under the
  project's `uv run python` interpreter.
- `ty check`, `ruff check`, and `scripts/check_function_size.py --fail-over-depth 4
  --fail-over-loc 200` all pass clean on every reviewed backend file.

No correctness, security, or data-loss defects were found in the reviewed hunks. The two
items below are genuine but low-impact.

## Warnings

### WR-01: Hardcoded developer-machine path in a committed research script

**File:** `scripts/research/oracle_compare.py:33`
**Issue:** `_PUZZLER_CLONE = Path("/home/aimfeld/Projects/Python/lichess-puzzler/tagger")`
is a literal absolute path into one specific developer's home directory. The script does
guard this with an `is_dir()` check and exits 0 when absent (so CI and other machines are
unaffected), but the path is not configurable via an environment variable or CLI flag, so
no other contributor (or a future CI job that *does* want to run this oracle comparison)
can point it at their own clone without editing committed source.
**Fix:** Read the path from an environment variable with the current literal as a
fallback default, e.g.:
```python
import os
_PUZZLER_CLONE = Path(
    os.environ.get("LICHESS_PUZZLER_TAGGER_PATH", "/home/aimfeld/Projects/Python/lichess-puzzler/tagger")
)
```

## Info

### IN-01: Redundant lower-bound check in `_build_missed_board_with_stack`

**File:** `app/services/flaws_service.py:445-452`
**Issue:** The function first returns `None` when `n < 1`, then later checks
`if not (1 <= n < len(positions)): return None`. The `1 <=` half of the second condition
is already guaranteed true by the first check and is dead weight (harmless, but slightly
obscures that the only new information the second check adds is the upper bound). This
mirrors the pre-existing `1 <= n < len(positions)` idiom used elsewhere in the same file
(e.g. line 789's `pre_flaw_eval_cp` guard), so it's a consistency choice rather than a
one-off mistake, but a single `if n >= len(positions): return None` would read more
directly given the leading `n < 1` guard already ran.
**Fix:** Optional simplification: `if n >= len(positions): return None` (drop the
already-proven `1 <=` half), or leave as-is for stylistic parity with the file's other
guards.

### IN-02: `dev_probe.py` / `sample_realgame_tags.py` load an unbounded result set into memory

**File:** `scripts/research/dev_probe.py:44-61`, `scripts/research/sample_realgame_tags.py:152-183`
**Issue:** Both scripts run `SELECT ... FROM game_flaws f JOIN games g ... WHERE
f.allowed_tactic_motif IS NOT NULL OR f.missed_tactic_motif IS NOT NULL` (or the
ROW_NUMBER()-windowed variant) with no `LIMIT`/pagination, and materialize `.mappings().all()`
plus per-game PGN replay into a Python dict for every matching row. Against prod's ~3.2M
tagged flaws this is a large single-shot memory allocation. This is explicitly out of scope
per the review's performance exclusion (not a correctness bug), and both scripts are
documented as manual, read-only, operator-invoked diagnostics rather than something that
runs unattended — noted here only because it's an easy trap for a future edit that adds a
tighter loop calling either script programmatically.
**Fix:** No action required for this phase; if either script grows a scheduled/automated
caller, add a `--limit`/keyset-paged variant like `retag_flaws.py` already has.

---

_Reviewed: 2026-09-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
