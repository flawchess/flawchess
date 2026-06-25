---
phase: 125-backfill-tactic-motifs
reviewed: 2026-06-18T05:13:28Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - scripts/coverage_report_tactic_motifs.py
  - tests/test_backfill_flaws.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues-found
---

# Phase 125: Code Review Report

**Reviewed:** 2026-06-18T05:13:28Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues-found

## Summary

Two files reviewed: a new read-only coverage report script and an extended test module. Both are non-production, low-blast-radius artifacts (a diagnostic script and pytest code). I verified the load-bearing claims against the actual implementation rather than trusting docstrings:

- `db_url_for_target`, `_INT_TO_MOTIF`, and `run_backfill`'s signature all match how the script/tests call them.
- The script's f-string `IN (1, 2)` tuple-literal renders correctly and the project context explicitly sanctions the fixed-severity-tuple-as-SQL-literal pattern (asyncpg lacks tuple binding); this is **not** an injection vector since `_MISTAKE_BLUNDER_SEVERITIES` is a program constant, never user data.
- The script is genuinely read-only: only `SELECT` statements, no DML, no `commit()`.
- The LEFT JOIN to `game_positions` on `(game_id, user_id, ply+1)` cannot fan out / inflate counts — the table PK is `(user_id, game_id, ply)`, so at most one row matches.
- The test premise holds end-to-end: tactic detection lives in `classify_game_flaws → _detect_tactic_for_flaw`, which reads `positions[n+1].pv` and `positions[n].move_san` and short-circuits to NULL when either is absent. The tactic fixture seeds both correctly; the no-PV fixture seeds neither. `classify_game_flaws` records BOTH movers' flaws (Phase 113 D-06), so the ply-1 black blunder materializes despite `user_color="white"`. Eval coverage for the 3-position fixture is 2/(3−1) = 1.0, comfortably above `EVAL_COVERAGE_MIN`.

No correctness or security defects found. Findings are one robustness gap in the test's positive assertion and three minor quality/convention notes.

## Warnings

### WR-01: PV-fires test does not pin the specific motif/piece, so a detector regression can pass silently

**File:** `tests/test_backfill_flaws.py:617-625`
**Issue:** `test_tactic_motif_is_not_null_when_pv_fires` asserts only `tactic_motif is not None` and `tactic_confidence is not None`. The fixture is built from a D-09 prod-confirmed *hanging-piece* fixture (`_TACTIC_REFUTATION_PV` = `f4e4 ...`, king captures the hanging rook), and the docstrings repeatedly assert "hanging-piece detector fires (motif=2, confidence=100)". But the test accepts *any* non-NULL motif. If a future change to the detector cascade made a *different* (wrong) detector fire first on this PV — e.g. the move were misclassified as `fork`/`mate`/`capturing-defender` — the test would still pass while the column is now wrong. Given the test exists specifically to validate the tactic-write path (Nyquist Wave 0 gap closure), an "any non-NULL" assertion under-tests the thing it was written to protect.

**Fix:** Pin the expected motif (and ideally the piece) so a misclassification regression is caught:
```python
from app.services.tactic_detector import TacticMotifInt, TACTIC_CONFIDENCE_HIGH

assert blunder_row.tactic_motif == TacticMotifInt.HANGING_PIECE, (
    f"Expected hanging-piece (motif={TacticMotifInt.HANGING_PIECE}) at ply "
    f"{blunder_ply}, got {blunder_row.tactic_motif}."
)
assert blunder_row.tactic_confidence == TACTIC_CONFIDENCE_HIGH
```
If pinning the exact value is deemed too brittle against intentional cascade reordering, at minimum assert the value is one of the small set the fixture can legitimately produce, and add a comment justifying why the loose assertion is acceptable.

## Info

### IN-01: `--db` typed as bare `str` instead of the existing `DbTarget` Literal

**File:** `scripts/coverage_report_tactic_motifs.py:297, 316-327`
**Issue:** `main(db: str)` and the argparse return use bare `str`, while CLAUDE.md prefers `Literal` for fixed value sets, and `app/core/config.py` already exports `DbTarget = Literal["dev", "test", "prod", "benchmark"]`. Runtime safety is fine (argparse `choices=["dev","benchmark","prod"]` enforces the set), so this is a typing/consistency nit, not a bug. Note: the sibling scripts (`backfill_flaws.py`, `backfill_eval.py`) also use bare `db: str`, so this new file is *consistent with the established project pattern* — flagging only because the Literal already exists and would be a strict-rule improvement.

**Fix:** Optional. If aligning with the strict CLAUDE.md rule, narrow to the script's own subset (note `DbTarget` includes `"test"`, which this script's `choices` excludes):
```python
from typing import Literal
ReportDbTarget = Literal["dev", "benchmark", "prod"]
async def main(db: ReportDbTarget) -> None: ...
```
Leaving it as `str` to match the sibling scripts is also defensible — pick one direction for the whole `scripts/` dir rather than diverging.

### IN-02: `conn: Any` discards type checking on every DB call in the report functions

**File:** `scripts/coverage_report_tactic_motifs.py:91, 144, 183, 220`
**Issue:** All five section functions take `conn: Any`. The actual type is `sqlalchemy.ext.asyncio.AsyncConnection` (from `engine.connect()`). `Any` silences ty across every `await conn.execute(...)` call, which is exactly the kind of "avoid `any`" the CLAUDE.md type-safety rule targets. Low impact in a one-shot diagnostic script, but trivially improvable.

**Fix:**
```python
from sqlalchemy.ext.asyncio import AsyncConnection
async def _print_overall(conn: AsyncConnection, db: str) -> None: ...
```

### IN-03: `datetime.utcnow`-style usage is fine, but the unused-row-field is worth a glance

**File:** `scripts/coverage_report_tactic_motifs.py:284-289`
**Issue:** Minor: in `_print_spot_check`, `pv_preview` is computed (`r.pv[:60] + "..."`) and printed, which is correct and None-safe. No defect — noting only that the `no_pv_null` spot-check query selects `gf.severity` and the ternary `"mistake" if r.severity == _MISTAKE_SEVERITY else "blunder"` is safe because the `WHERE gf.severity IN (1, 2)` filter guarantees severity is exactly 1 or 2. No action needed; included to document that the else-branch is provably reachable only for severity 2.

**Fix:** None required. (Listed for completeness of the severity-ternary audit.)

---

_Reviewed: 2026-06-18T05:13:28Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
