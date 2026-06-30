---
phase: 142-multipv-2-engine-pass-eval-drain-remote-worker
plan: "04"
subsystem: validation_tool
tags: [multipv, validation, margin-histogram, scripts, reports]
status: complete

dependency_graph:
  requires:
    - plans/142-02 (allowed_pv_lines / missed_pv_lines blobs populated by eval drain)
  provides:
    - scripts/validate_multipv_budget.py (SC4 committed re-runnable validation tool)
    - reports/multipv-validation/ (timestamped markdown reports)
  affects:
    - Phase 142 merge gate (HUMAN: run --check-goals against >=200 dev flaw positions)
    - Phase 144 (A/B): re-runs this tool against same stored evals to tune ONLY_MOVE_WIN_PROB_MARGIN
    - Phase 145 (rollout): re-runs after backfill to confirm corpus-wide margin distribution

tech_stack:
  added: []
  patterns:
    - _REPORT_DIR pattern (tactic_tagger_report.py line 96 analog)
    - argparse --db dev|benchmark|prod + --check-goals exit-code gate
    - Explicit column projection (Pitfall 4: never select(GameFlaw) for deferred cols)
    - Session closed before computation (CLAUDE.md hard rule)
    - eval_cp_to_expected_score / eval_mate_to_expected_score (no hand-rolled sigmoid)
    - ONLY_MOVE_WIN_PROB_MARGIN imported from forcing_line_gate (no magic numbers)

key_files:
  created:
    - scripts/validate_multipv_budget.py
    - reports/multipv-validation/.gitkeep
  modified: []

decisions:
  - "Mate nodes handled via eval_mate_to_expected_score (returns 0/1) rather than skipped -- they produce margins near 1.0 and never cluster near the band"
  - "Solver-color for allowed_pv_lines: flaw_ply%2==0 => solver=black (opponent punishes); flaw_ply%2==1 => solver=white"
  - "PV1-drift section is advisory-only (does not affect --check-goals exit code); authoritative guard is Plan 02 Task 3 test-suite flaw-count invariant"
  - "No second move (s=None, sm=None): counted as trivially-forced, excluded from band analysis"

metrics:
  duration_seconds: 900
  completed_date: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 142 Plan 04: MultiPV Budget Validation Tool Summary

Build the committed, re-runnable margin-histogram validation tool (D-07 / MPV-03). Reads
`game_flaws.allowed_pv_lines` JSONB blobs, computes win-prob margins at solver nodes,
writes a timestamped markdown report, and provides a `--check-goals` exit-code gate
for the human merge gate (SC4).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build validate_multipv_budget.py (margin histogram + exit-code gate) | 451d4c85 | scripts/validate_multipv_budget.py |
| 2 | Add PV1-drift spot-check section + create reports dir | 39ca8b6d | reports/multipv-validation/.gitkeep |

## What Was Built

**Task 1: Core validation script**

- `scripts/validate_multipv_budget.py` — `argparse` CLI with `--db {dev,benchmark,prod}`
  (required), `--limit N` (default 1000), `--check-goals` (store_true)
- `_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "multipv-validation"`
- Named constants: `_MARGIN_BAND=0.05`, `_MAX_FRACTION_IN_BAND=0.10`, `_MIN_POSITIONS=200`,
  `_HIST_BIN_WIDTH=0.05`
- Reads blobs via explicit column projection: `select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.allowed_pv_lines).where(GameFlaw.allowed_pv_lines.isnot(None)).limit(limit)` — never the whole ORM entity (Pitfall 4 / deferred cols)
- Session closed before computing (CLAUDE.md hard rule: no async gather inside AsyncSession)
- Solver-color derivation: `allowed_pv_lines` solver = "black" if `flaw_ply % 2 == 0` else "white" (mirrors `_detect_tactic_for_flaw` board_after_flaw.turn convention)
- Margin per solver node (even index): `eval_cp_to_expected_score(b, solver_color) - eval_cp_to_expected_score(s, solver_color)`, using `eval_mate_to_expected_score` for mate-scored nodes
- T-142-04-02: malformed dicts skipped and counted; trivially-forced nodes (no second move) counted separately and excluded from band analysis
- ASCII histogram table (bins 0..1 at width 0.05), in-band bins marked
- `--check-goals`: exits 1 if positions < `_MIN_POSITIONS` OR fraction-in-band > `_MAX_FRACTION_IN_BAND`; prints PASS/FAIL with actionable message

**Task 2: PV1-drift section + report directory**

- `_build_drift_section()` samples `game_positions.eval_cp` for Phase-142-analyzed games,
  reports mean absolute eval_cp, stdev, contested-zone fraction (|eval_cp| <= 150 cp),
  and decisive-zone fraction (|eval_cp| > 300 cp)
- Advisory note clearly states: authoritative PV1-drift guard is the Plan 02 Task 3
  test-suite flaw-count invariant; this section is a spot-check only
- Drift section does NOT affect `--check-goals` exit code
- `reports/multipv-validation/.gitkeep` committed so the directory is tracked

## Acceptance Criteria Verified

- `uv run python scripts/validate_multipv_budget.py --help` lists `--db`, `--limit`, `--check-goals` ✓
- `grep -n "select(GameFlaw)" scripts/validate_multipv_budget.py` returns NO match ✓
- `grep -n "eval_cp_to_expected_score|ONLY_MOVE_WIN_PROB_MARGIN"` shows 22 occurrences ✓
- `grep -n "_MARGIN_BAND|_MAX_FRACTION_IN_BAND|_MIN_POSITIONS"` shows named thresholds ✓
- `uv run ty check scripts/validate_multipv_budget.py` exits 0 ✓
- `uv run python scripts/validate_multipv_budget.py --db dev --limit 100` writes report (0 positions — no blobs yet; expected) ✓
- `--check-goals` exits 1 with clear FAIL message when 0 positions analyzed ✓
- Report includes "PV1 Drift Spot-Check" section header ✓
- `reports/multipv-validation/.gitkeep` exists ✓

## Deviations from Plan

None — plan executed exactly as written. The script was implemented in a single pass covering both Task 1 and Task 2 deliverables, with the PV1-drift section integrated into the main report builder.

## Known Stubs

None. The script is fully functional; it returns 0 positions because the dev DB currently has no `allowed_pv_lines` blobs (the Phase 142 eval drain needs to run on real games first). The `--check-goals` failure on 0 positions is the correct and expected behavior — it prompts the operator to run the drain before using the gate.

## HUMAN MERGE GATE (SC4)

After Plans 02/03 have populated dev blobs on at least 200 flaw positions, run:

```bash
uv run python scripts/validate_multipv_budget.py --db dev --check-goals
```

Inspect `reports/multipv-validation/*.md`. If `--check-goals` exits 0 (fraction-in-band <= 10%), the node budget is adequate and Phase 142 may merge. If it exits 1 with a budget-too-low FAIL, raise `_NODES_BUDGET` from 1M to 1.5-2M nodes (D-06) and re-run.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. Reports contain aggregate margin statistics only (no PII, no secrets).

## Self-Check: PASSED

- `scripts/validate_multipv_budget.py` FOUND ✓
- `reports/multipv-validation/.gitkeep` FOUND ✓
- Commit 451d4c85 FOUND ✓
- Commit 39ca8b6d FOUND ✓
