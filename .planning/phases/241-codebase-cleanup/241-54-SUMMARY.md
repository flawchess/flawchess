---
phase: 241-codebase-cleanup
plan: 54
subsystem: services-endgame-insights
tags: [cleanup, naming, renames]
requires: [241-02, 241-03, 241-17, 241-18, 241-22]
provides: ["Endgame and insights services use descriptive names; five insights_llm filter functions named for what they do"]
affects: [app/services/endgame_service.py, app/services/endgame_zones.py, app/services/insights_service.py, app/services/insights_llm.py, tests/services/test_insights_llm.py]
key-files:
  modified:
    - app/services/endgame_service.py
    - app/services/endgame_zones.py
    - app/services/insights_service.py
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-54.tsv
    - .planning/phases/241-codebase-cleanup/ledgers/241-54.txt
    - .planning/phases/241-codebase-cleanup/allow/241-54.tsv
decisions: []
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 0a69ccf64dac4d2453d85b2a99d391451c2803b2
actuals:
  tokens: 20000
  tasks: 3
  commits: 6
---

# Phase 241 Plan 54: Endgame and insights service renames Summary

Applied the INVENTORY section 5 renames for the endgame and insights services as six `refactor(naming)` commits (the G1 group as one), with no change to prompt text, prompt version, golden files or wire ids.

## Renames

| Old | New | Commit | Files |
| --- | --- | ------ | ----- |
| `neg_count` | `non_endgame_count` | 86d60ae36 | endgame_service.py |
| `shared_wdl_count` | `shared_quintile_count` | 2f65c696a | endgame_service.py |
| `TcConvRecovBands` | `TcMetricBands` | 293283894 | endgame_zones.py |
| `TcBucket` | `TimeControlBucket` (import from `app.schemas.endgames`; local alias deleted) | 05d51fa79 | endgame_zones.py, insights_service.py, insights_llm.py |
| `_METRICS_ELO_BUCKETS` | `_ENDGAME_METRICS_BUCKETS` | 190104c4a | insights_service.py |
| `_apply_c3_filter` | `_activity_gap_marker` | 0a69ccf64 (G1) | insights_llm.py, test_insights_llm.py |
| `_apply_c5_filter` | `_should_emit_series_block` | 0a69ccf64 (G1) | same |
| `_apply_c6_filter` | `_cap_all_time_points` | 0a69ccf64 (G1) | same |
| `_apply_c2_filter` | `_drop_points_covered_by_last_3mo` | 0a69ccf64 (G1) | same |
| `_apply_a2_filter` | `_visible_findings` | 0a69ccf64 (G1) | same |

The G1 commit also rewrote the `_assemble_user_prompt` filter catalog docstring and the "A4/C2/C6 filter chain" prose (`_retained_series_for_summary`, `_compute_all_time_series_pairs`, `_compute_stale_markers_and_live_metrics`) to describe what each stage does, and updated the two test docstrings in `tests/services/test_insights_llm.py`.

## INV-L637 status

APPLIED: `_visible_findings` docstring now reads "Drop NaN-valued findings, empty thin findings, and pawnless-class findings (the UI hides pawnless rows)." Re-verified against the body (NaN value, `sample_size == 0` with thin quality, `endgame_class == "pawnless"`); the old "hidden subsections" claim had no matching rule. Recorded in `ledgers/241-54.txt`.

## Allow-list entries (allow/241-54.tsv)

Four `diff` entries: three for the `TimeControlBucket` import line / removed alias residue in endgame_zones.py, insights_service.py and insights_llm.py (reason "TcBucket alias replaced by the schema import, INVENTORY section 5 M row"), and one for the `(` residue where `ruff format` wrapped the insights_llm.py schema import in parentheses after adding `TimeControlBucket`.

## Verification

- `uv run ty check app/ tests/ scripts/`: pass.
- `uv run ruff check app tests` and `ruff format`: clean.
- Endgame tests (227), insights tests (280 incl. golden user prompt), and `source_scan_tests.sh --py` (95 + 5): pass. `tests/services/golden` untouched.
- `cleanup.py absent --map rename-maps/241-54.tsv`: 10 rows, 0 hits. `cleanup.py diff --plan 241-54`: exit 0 on all touched files.
- `scripts/gen_endgame_zones_ts.py --check`: no drift.
- `scripts/benchmarks/sql.py` `TcBucket` untouched.

## Deviations from Plan

None to code. Notes:
- Tests were run serially, not `-n 4`: with many sibling executors sharing the dev Postgres, `-n 4` produced transient fixture errors (and one source-scan run showed 95 setup errors that passed on immediate retry). No test changed.
- The ledger tool check could not run (`scopes/241-54.txt` does not exist); the single INV-L637 line is recorded by hand.
- Remaining A2/A4/C2/C5/C6 shorthand in other `tests/services/test_insights_llm.py` docstrings/comments (lines ~704-727, 1075, 1137, 1219, 2269-2273) was left as-is: the plan scoped test edits to the two named docstrings; those belong to the comment-cleanup plans.

## Known Stubs

None.

## Self-Check: PASSED

Commits 86d60ae36, 2f65c696a, 293283894, 05d51fa79, 190104c4a, 0a69ccf64 present on the branch; rename-maps, ledgers and allow files present.
