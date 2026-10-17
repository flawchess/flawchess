---
phase: 241-codebase-cleanup
plan: 55
subsystem: backend-naming
tags: [cleanup, rename, naming]
requires: [241-02, 241-03, 241-10, 241-17, 241-22]
provides: ["Stats/openings helpers named for what they return, no planning tag in production identifiers"]
affects: [app/services/stats_service.py, app/services/opening_insights_service.py, app/services/openings_service.py, app/repositories/openings_repository.py]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-55.tsv
  modified:
    - app/services/stats_service.py
    - app/services/opening_insights_service.py
    - app/services/openings_service.py
    - app/repositories/openings_repository.py
    - tests/services/test_opening_insights_service.py
decisions: []
requirements-completed: [D-06, D-07, D-08, D-17]
status: complete
commits: 3
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: fecb50ce5debcc3ebd37001dcffffcb75094c3db
actuals:
  tokens: 6000
  tasks: 2
  commits: 3
---

# Phase 241 Plan 55: Stats and openings renames Summary

Three INVENTORY §5 renames applied as printed, one `refactor(naming)` commit each, with no behavior, wire or test-assertion changes.

## Renames

| Old | New | Commit | Files |
| --- | --- | ------ | ----- |
| `_phase80_item_from_metrics` | `_bookmark_phase_entry_item` | f94bda4b3 | stats_service.py (def, call), opening_insights_service.py (docstring citation), rename-maps/241-55.tsv |
| `_collect_attribution_hashes` | `_fetch_attribution_context` | 020ccf183 | opening_insights_service.py (def, call, pipeline comment, docstring), openings_repository.py (docstring), tests/services/test_opening_insights_service.py (import and call) |
| `gc` | `move_game_count` | fecb50ce5 | openings_service.py (denominator loop local plus its comment; canon_paths scoped to this file) |

`trans_counts` was left unchanged (D-08). No alias added (D-17).

## Verification

- `uv run ty check app/ tests/ scripts/`: all checks passed after each rename.
- Tests: test_opening_insights_service, test_stats_service, test_stats_service_phase_entry, test_openings_repository (96 passed); test_openings_service (26 passed); source_scan_tests.sh --py (95 + 5 passed).
- `cleanup.py absent --map rename-maps/241-55.tsv`: 3 rows, 0 hits. `cleanup.py diff --plan 241-55`: passes. `cleanup.py scan --identifiers` on stats/opening_insights services: 0 matches.
- `ruff format --check` on openings_service.py: clean.

## Deviations from Plan

None - plan executed exactly as written.

Note: one `-n 4` pytest run errored in fixture setup (asyncpg "another operation in progress") from DB contention with sibling parallel executors; the identical tests passed when rerun serially. Not related to the rename.

## Known Stubs

None.

## Self-Check: PASSED

- rename-maps/241-55.tsv exists with three rows; commits f94bda4b3, 020ccf183, fecb50ce5 are on the branch.
