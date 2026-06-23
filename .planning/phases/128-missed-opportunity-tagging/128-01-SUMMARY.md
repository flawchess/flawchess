---
phase: 128-missed-opportunity-tagging
plan: "01"
subsystem: game_flaws schema + FlawRecord contract
tags: [schema, migration, tactic, alembic, flaws]
status: complete

dependency_graph:
  requires: []
  provides:
    - game_flaws 8 inline tactic columns (allowed_tactic_* + missed_tactic_*)
    - Alembic migration b6e2978df54f (data-preserving rename + add)
    - FlawRecord 8 tactic keys (allowed_tactic_motif_int/piece/confidence/depth + missed_*)
    - flaw_record_to_row writes all 8 DB columns
  affects:
    - app/repositories/library_repository.py (ORM attribute rename ripple)
    - app/repositories/query_utils.py (ORM attribute rename ripple)
    - app/services/library_service.py (ORM attribute rename ripple)
    - tests/* (FlawRecord key + ORM attribute rename ripple)

tech_stack:
  added: []
  patterns:
    - Data-preserving ALTER RENAME via op.alter_column(new_column_name=...) — no DROP+ADD
    - Dual-orientation 4-tuple FlawRecord keys with _int suffix for motif (avoids motif-name vs int ambiguity)
    - Defensive .get() mapping in flaw_record_to_row for forward-compat with older construction paths

key_files:
  created:
    - alembic/versions/20260619_173929_b6e2978df54f_rename_tactic_cols_to_allowed_add_.py
  modified:
    - app/models/game_flaw.py
    - app/services/flaws_service.py
    - app/repositories/game_flaws_repository.py
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/services/library_service.py
    - tests/test_flaws_repository.py
    - tests/test_flaws_materialization.py
    - tests/services/test_flaws_service.py
    - tests/services/test_tactic_comparison_service.py
    - tests/test_backfill_flaws.py

decisions:
  - D-01: Inline 8 columns on game_flaws (not child table); matches existing wide pattern; no join needed
  - D-02: 4 data-preserving ALTER RENAME (all 4 existing tactic_* become allowed_*); 4 ADD COLUMN for missed_*; migration revision b6e2978df54f
  - D-05: allowed_tactic_depth = loop index within flaw_ply+1 PV; missed_tactic_depth = loop index within flaw_ply PV; both documented in model comment
  - D-06: _build_flaw_record calls detection for allowed_* (existing); missed_* = None pending Plan 02 second-pass detector

metrics:
  duration: "~35 minutes"
  completed: "2026-06-19"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 11
---

# Phase 128 Plan 01: Schema + FlawRecord Storage Contract Summary

Established the storage contract for missed/allowed tactic orientations: renamed all 4 existing `tactic_*` columns to `allowed_tactic_*` (data preserved via ALTER RENAME), added 4 nullable `missed_tactic_*` SmallInteger columns, and extended the `FlawRecord` TypedDict + write-path row mapping so both 4-tuples flow to the DB.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rename + add 8 inline tactic columns (model + migration) | 5f9e28c9 | app/models/game_flaw.py, alembic/versions/b6e2978df54f |
| 2 (RED) | Failing tests for 8-column write-path | 679d34b3 | tests/test_flaws_repository.py |
| 2 (GREEN) | Extend FlawRecord + write-path for both orientations | 5f05cbb4 | app/services/flaws_service.py, app/repositories/game_flaws_repository.py, tests/ |

## Key Artifacts

### Alembic Migration (b6e2978df54f)

- Revision: `b6e2978df54f`
- Down revision: `9be5294cfe3c` (Phase 127 add_tactic_depth head)
- `upgrade()`: 4 `op.alter_column(..., new_column_name=...)` renames + 4 `op.add_column` for `missed_tactic_*`
- `downgrade()`: drop 4 `missed_*` + 4 `op.alter_column` back to `tactic_*`
- Round-trip verified: `upgrade head → downgrade -1 → upgrade head` exits 0
- Data preserved: 32,518 non-NULL `allowed_tactic_motif` rows after up→down→up (matches pre-migration `tactic_motif` count)

### Schema Changes

```
game_flaws before (Phase 127 head):         game_flaws after (b6e2978df54f):
  tactic_motif     SmallInteger NULL          allowed_tactic_motif      SmallInteger NULL  ← renamed
  tactic_piece     SmallInteger NULL          allowed_tactic_piece      SmallInteger NULL  ← renamed
  tactic_confidence SmallInteger NULL         allowed_tactic_confidence SmallInteger NULL  ← renamed
  tactic_depth     SmallInteger NULL          allowed_tactic_depth      SmallInteger NULL  ← renamed
                                              missed_tactic_motif       SmallInteger NULL  ← new
                                              missed_tactic_piece       SmallInteger NULL  ← new
                                              missed_tactic_confidence  SmallInteger NULL  ← new
                                              missed_tactic_depth       SmallInteger NULL  ← new
```

### FlawRecord TypedDict Keys

Renamed 4 keys + added 4 new keys in `app/services/flaws_service.py`:

| Old key | New key | DB column |
|---------|---------|-----------|
| `tactic_motif_int` | `allowed_tactic_motif_int` | `allowed_tactic_motif` |
| `tactic_piece` | `allowed_tactic_piece` | `allowed_tactic_piece` |
| `tactic_confidence` | `allowed_tactic_confidence` | `allowed_tactic_confidence` |
| `tactic_depth` | `allowed_tactic_depth` | `allowed_tactic_depth` |
| (new) | `missed_tactic_motif_int` | `missed_tactic_motif` |
| (new) | `missed_tactic_piece` | `missed_tactic_piece` |
| (new) | `missed_tactic_confidence` | `missed_tactic_confidence` |
| (new) | `missed_tactic_depth` | `missed_tactic_depth` |

`missed_*` keys are all `None` in `_build_flaw_record` pending Plan 02's second-pass detector.

### Write-Path (flaw_record_to_row)

Maps all 8 columns using `.get()` defensive pattern. Old `tactic_*` DB column keys removed.

## Deviations from Plan

### Auto-fixed Issues (Rule 3 — Blocking)

**1. [Rule 3 - Blocking] ORM attribute rename ripple to library_repository.py, query_utils.py, library_service.py**

- **Found during:** Task 1 (ty check after model rename)
- **Issue:** The plan's scope for Task 1 listed only `app/models/game_flaw.py` and `alembic/versions/`. After renaming ORM attributes to `allowed_tactic_motif` etc., three other files in `app/` still referenced `GameFlaw.tactic_motif`, `GameFlaw.tactic_confidence` as ORM class attributes — causing 12 `ty` errors and blocking the full suite.
- **Fix:** Updated `library_repository.py` (3 call sites: flaw filter clause, tactic chip read, tactic comparison query), `query_utils.py` (1 EXISTS filter), `library_service.py` (3 ORM attribute reads in eval-series tactic chip build).
- **Files modified:** app/repositories/library_repository.py, app/repositories/query_utils.py, app/services/library_service.py
- **Commit:** 5f9e28c9

**2. [Rule 3 - Blocking] Test file rename ripple to test_backfill_flaws.py, test_flaws_service.py, test_flaws_materialization.py, test_tactic_comparison_service.py**

- **Found during:** Task 2 (ty check after FlawRecord key rename)
- **Issue:** Five test files still constructed `FlawRecord` dicts with old keys or accessed old ORM attributes (`row.tactic_motif`, etc.), causing ty errors and potential runtime failures.
- **Fix:** Updated all test files to use renamed keys. `test_tactic_comparison_service.py` also had raw DB row dict using old column name `tactic_motif` → `allowed_tactic_motif` (insert would have silently failed or been ignored in a future DB test run).
- **Files modified:** tests/test_backfill_flaws.py, tests/services/test_flaws_service.py, tests/test_flaws_materialization.py, tests/services/test_tactic_comparison_service.py
- **Commit:** 5f05cbb4

## Verification Results

```
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
  → exit 0 (round-trip clean)

SELECT count(*) FROM game_flaws WHERE allowed_tactic_motif IS NOT NULL
  → 32518 (matches pre-migration tactic_motif non-NULL count — data preserved)

uv run pytest tests/test_flaws_repository.py tests/test_flaws_materialization.py
         tests/services/test_flaws_service.py tests/test_backfill_flaws.py
         tests/test_game_flaws_model.py -v
  → 168 passed

uv run pytest -n auto -x
  → 2802 passed, 15 skipped

uv run ty check app/ tests/  → All checks passed
uv run ruff check app/ tests/  → All checks passed
uv run ruff format app/ tests/  → 1 file reformatted (test_flaws_repository.py)
```

## Known Stubs

- `missed_tactic_motif_int`, `missed_tactic_piece`, `missed_tactic_confidence`, `missed_tactic_depth` in `FlawRecord` are all `None` in `_build_flaw_record` — stubs pending the Plan 02 detector second pass. This is intentional and documented in the FlawRecord docstring.

## Threat Flags

None. The new missed_tactic_* columns are nullable SmallInteger written only by the trusted classify/backfill path. No external input reaches them in this plan (T-128-02 accepted).

## Self-Check: PASSED

- `app/models/game_flaw.py` exists: FOUND
- `alembic/versions/20260619_173929_b6e2978df54f_rename_tactic_cols_to_allowed_add_.py` exists: FOUND
- Commits exist: 5f9e28c9, 679d34b3, 5f05cbb4, 516487c3 — all verified in git log
- `ty check app/ tests/` clean: PASSED
- `pytest -n auto`: 2802 passed
