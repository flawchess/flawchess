---
phase: 260426-pbo
plan: 01
subsystem: stats / openings
tags: [bug-fix, frontend, backend, sql, pre-v1.13, PRE-01]
requires: []
provides:
  - "OpeningWDL.display_name field (backend + frontend)"
  - "query_top_openings_sql_wdl returns rows for opponent-defined openings"
  - "Regression test parametrized over user color"
affects:
  - app/repositories/stats_repository.py
  - app/schemas/stats.py
  - app/services/stats_service.py
  - frontend/src/types/stats.ts
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/pages/Openings.tsx
tech_stack:
  added: []
  patterns:
    - "SQLAlchemy `case()` + `literal()` for SQL-side conditional string column"
key_files:
  created: []
  modified:
    - app/repositories/stats_repository.py
    - app/schemas/stats.py
    - app/services/stats_service.py
    - tests/test_stats_repository.py
    - tests/test_stats_service.py
    - frontend/src/types/stats.ts
    - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
    - frontend/src/pages/Openings.tsx
    - CHANGELOG.md
decisions:
  - "Use a SQL `CASE` column for `display_name` instead of computing it Python-side, so the prefix logic lives next to the parity check it replaces and the wire shape becomes self-describing."
  - "Add `ply_count` to GROUP BY (PostgreSQL requires it for the CASE expression). It is functionally determined by `(eco, name)` within `openings_dedup`, so it does not change the grouping result."
  - "Keep `opening_name` (canonical) and `label` unchanged. Only the row label site (desktop + mobile) renders `display_name`; tooltips and aria-labels still read `opening_name` so screen readers and hover text stay clean."
  - "Bookmark synthesizer in `Openings.tsx` mirrors `display_name` to `label` since bookmarks have no parity context."
metrics:
  duration_minutes: ~25
  completed_date: 2026-04-26
  tests_added: 1 parametrized (2 cases) + 1 assertion in existing service test
  tests_modified: 2 (tuple-shape updates)
  commits: 4
---

# Quick Task 260426-pbo: Drop Parity Filter on Top-10 Openings Summary

Removed the `ply_count % 2 == user_parity` filter from `query_top_openings_sql_wdl` and surfaced opponent-defined openings with a `vs. ` prefix via a new `display_name` SQL column propagated through `OpeningWDL` to the desktop and mobile MPO renderers.

## What Changed

### Backend
- `app/repositories/stats_repository.py::query_top_openings_sql_wdl`
  - Dropped the parity filter from the WHERE clause; kept the `min_ply` floor.
  - Added `display_name` SELECT column built with `case((ply_count % 2 != user_parity, literal("vs. ") + opening_name), else_=opening_name)`.
  - Added `_openings_dedup.c.ply_count` to GROUP BY so PostgreSQL can evaluate the CASE per group.
  - Added a multi-line bug-fix comment per CLAUDE.md "Comment bug fixes" rule.
  - Updated docstring to document the new tuple shape.
- `app/schemas/stats.py::OpeningWDL` — added `display_name: str`.
- `app/services/stats_service.py::get_most_played_openings`
  - Updated tuple unpacking in `rows_to_openings` to `(eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)`.
  - Bumped positional row index `[4]` → `[5]` for `full_hash` extractor (twice — white + black).
  - Passed `display_name=display_name` to the OpeningWDL constructor.

### Tests (TDD)
- `tests/test_stats_repository.py`
  - **New** parametrized regression test `test_top_openings_includes_off_color_with_vs_prefix` covering both `color="white"` and `color="black"`. Seeds `B00 King's Pawn Game` (ply=1, white-defined) + `B10 Caro-Kann Defense` (ply=2, black-defined); asserts both appear and asserts the `vs. ` prefix is on the off-color row only.
  - Updated `test_sql_wdl_returns_correct_counts` to unpack 10 fields and assert `display_name == "King's Pawn Game"` for the white-as-white case.
  - Updated `test_sql_wdl_filters_by_time_control` row index `[5]` → `[6]` for `total` (shifted by the new `display_name` column).
- `tests/test_stats_service.py::test_opening_wdl_fields_when_present`
  - Added `assert hasattr(opening, "display_name")` plus a value check that `display_name == opening_name` or `f"vs. {opening_name}"`.

### Frontend
- `frontend/src/types/stats.ts::OpeningWDL` — added `display_name: string` with JSDoc.
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` (desktop) — `formatName(o.opening_name)` → `formatName(o.display_name)`. Tooltip and aria-label keep `o.opening_name`.
- `frontend/src/pages/Openings.tsx`
  - Mobile MPO renderer renders `o.display_name` instead of `o.opening_name`.
  - `buildBookmarkRows` synthesizer populates `display_name: b.label` (bookmarks have no parity context).

### Docs
- `CHANGELOG.md` — added a `### Fixed` entry under `## [Unreleased]` referencing PRE-01.

## Test Results

- `uv run ruff check app/ tests/` → PASS
- `uv run ty check app/ tests/` → PASS
- `uv run pytest` → 1093 passed (full backend suite)
- `cd frontend && npx tsc --noEmit` → PASS
- `cd frontend && npm run lint` → 3 warnings (in pre-existing `coverage/` artifacts, unrelated)
- `cd frontend && npm run knip` → PASS
- `cd frontend && npm test -- --run` → 106 passed (9 files)
- `cd frontend && npm run build` → PASS

## Deviations from Plan

None. The plan was executed exactly as written, with two minor adjustments:

1. **Comment alignment in `app/schemas/stats.py`** — ruff format does not preserve the original column-aligned `#` comments on the `OpeningWDL` field block. The block was reformatted to single-space comments; semantics are unchanged.
2. **GROUP BY addition** — the plan called out adding `display_name_col` to GROUP BY; I added `_openings_dedup.c.ply_count` instead (the input to the CASE). This is the equivalent fix and avoids re-emitting the entire CASE expression in the GROUP BY clause. PostgreSQL is happy because `ply_count` is the only non-grouped column the CASE depends on.

## Auth Gates

None.

## Known Stubs

None.

## Commits

| # | Hash    | Type     | Message                                                                  |
| - | ------- | -------- | ------------------------------------------------------------------------ |
| 1 | 7cd69a6 | test     | add failing tests for display_name and parity-filter removal             |
| 2 | 9656187 | fix      | drop ply-parity filter on top-10 openings, add display_name              |
| 3 | c63e4bc | feat     | render display_name in top-10 openings (desktop + mobile)                |
| 4 | 3301ff5 | docs     | add CHANGELOG entry for PRE-01 top-10 openings fix                       |

## TDD Gate Compliance

RED (`7cd69a6 test:`) → GREEN (`9656187 fix:`) → no REFACTOR needed. Frontend follow-up (`c63e4bc feat:`) and CHANGELOG entry (`3301ff5 docs:`) are ancillary to the TDD-gated backend cycle.

## Pending: Task 3 (human-verify checkpoint)

Task 3 is a `checkpoint:human-verify` gate. Per the executor constraints, this remains for the user to perform manually:

1. `bin/run_local.sh` to bring up backend + frontend.
2. Log in as Adrian's account.
3. Open the Openings page → Black top-10. Confirm `vs. Caro-Kann Defense: Hillbilly Attack` (or similar white-defined opening with N games) renders with the `vs. ` prefix.
4. Confirm same-color rows render WITHOUT the `vs. ` prefix.
5. Confirm both behaviors on mobile width (Chrome devtools narrow viewport).

## Self-Check: PASSED

Verified that all listed files and commits exist:

- `app/repositories/stats_repository.py` → FOUND (modified)
- `app/schemas/stats.py` → FOUND (modified)
- `app/services/stats_service.py` → FOUND (modified)
- `frontend/src/types/stats.ts` → FOUND (modified)
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` → FOUND (modified)
- `frontend/src/pages/Openings.tsx` → FOUND (modified)
- `tests/test_stats_repository.py` → FOUND (modified)
- `tests/test_stats_service.py` → FOUND (modified)
- `CHANGELOG.md` → FOUND (modified)
- Commit `7cd69a6` → FOUND
- Commit `9656187` → FOUND
- Commit `c63e4bc` → FOUND
- Commit `3301ff5` → FOUND
