---
phase: 178-lichess-compatible-accuracy-acpl-computed-columns
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, postgres, migration, games]

# Dependency graph
requires: []
provides:
  - "Migration `60d9b72c0eaa` adding `white_accuracy_imported` / `black_accuracy_imported` / `white_acpl_imported` / `black_acpl_imported` to `games`, copying pre-migration platform values in and NULLing the canonical columns"
  - "`app/models/game.py` four new `*_imported` mapped_columns + corrected provenance comments on the canonical columns"
  - "Migration test proving the copy-then-null ordering via the shipped down migration round-trip"
affects: [178-02, 178-03, 178-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Add-column + op.execute data-copy migration pattern (cloned from the evals_completed_at migration), extended to a copy-then-null two-statement upgrade"

key-files:
  created:
    - alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py
    - tests/services/test_migration_178_accuracy_imported.py
  modified:
    - app/models/game.py

key-decisions:
  - "Copy-then-null implemented as two sequential UPDATE statements (not a single multi-column UPDATE with subselects) for auditability; both run in upgrade() in the correct order"
  - "Migration docstring rephrased to avoid the literal substrings `inaccuracies`/`mistakes`/`blunders` so the D-04 guardrail grep passes even against comments, not just code"

patterns-established:
  - "Copy-before-null migration pattern for repurposing a canonical column while preserving its old values under an `_imported` suffix — reusable for any future 'canonical name takes over' column migration"

requirements-completed: []

coverage:
  - id: D1
    description: "Migration adds four *_imported columns, copies platform values in, then NULLs canonical columns; downgrade reverses this"
    verification:
      - kind: integration
        ref: "tests/services/test_migration_178_accuracy_imported.py::test_copy_survives_downgrade_and_reupgrade_preserves_copy_before_null"
        status: pass
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head"
        status: pass
    human_judgment: false
  - id: D2
    description: "Model exposes the four *_imported columns with correct types (REAL/SmallInteger, nullable) and updated provenance comments; oracle severity-count columns untouched"
    verification:
      - kind: unit
        ref: "uv run ty check app/ (zero errors) + uv run python -c import check"
        status: pass
    human_judgment: false
  - id: D3
    description: "*_imported columns independently readable/writable; canonical + imported columns NULL on a fresh Game insert"
    verification:
      - kind: integration
        ref: "tests/services/test_migration_178_accuracy_imported.py::test_imported_columns_present_and_independently_writable"
        status: pass
      - kind: integration
        ref: "tests/services/test_migration_178_accuracy_imported.py::test_canonical_and_imported_columns_null_on_fresh_insert"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-18
status: complete
---

# Phase 178 Plan 01: Migration — accuracy/acpl imported columns Summary

**Alembic migration + SQLAlchemy model repurposing `games.white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl` as the future uniform lichess-formula columns, preserving platform-reported values in new `*_imported` columns.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-18T08:41:23Z
- **Completed:** 2026-07-18T08:46:07Z
- **Tasks:** 3
- **Files modified:** 3 (1 migration created, 1 model modified, 1 test created)

## Accomplishments
- Migration `60d9b72c0eaa` adds `white_accuracy_imported`/`black_accuracy_imported` (REAL) and `white_acpl_imported`/`black_acpl_imported` (SmallInteger, all nullable) to `games`, copies the pre-migration canonical values into them, then NULLs the canonical columns — verified reversible (`upgrade head` → `downgrade -1` → `upgrade head`, all clean).
- `app/models/game.py` gained the four `*_imported` mapped_columns and corrected provenance comments on the canonical `white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl` columns (now documented as "our uniform lichess-formula computed values, NULL until the compute path fills them"). Oracle severity-count columns (`is_analyzed` sentinel) left byte-for-byte unchanged.
- `tests/services/test_migration_178_accuracy_imported.py` behaviorally proves the copy-then-null ordering by round-tripping through the shipped `downgrade()`/`upgrade()`: seeds a post-migration-shape row, downgrades (asserts canonical restored from `*_imported`), then re-upgrades (asserts `*_imported` restored and canonical re-NULLed) — a copy-after-null ordering bug would fail this test. Also covers independent `*_imported` read/write and NULL-on-fresh-insert.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration — add *_imported columns, copy platform values in, NULL canonical** - `cd4dbe2d` (feat)
2. **Task 2: Model columns + provenance comments** - `efc837e3` (feat)
3. **Task 3: Migration upgrade/downgrade behavior test** - `e8664aed` (test), plus a small formatting fix on the migration file - `82222a99` (style)

**Plan metadata:** (this commit)

## Files Created/Modified
- `alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py` - The add-column + data-copy + null-canonical migration (Task 1)
- `app/models/game.py` - Four new `*_imported` mapped_column definitions + corrected provenance comments (Task 2)
- `tests/services/test_migration_178_accuracy_imported.py` - Upgrade/downgrade copy-survival behavior test (Task 3)

## Decisions Made
- Copy-then-null written as two sequential `op.execute("UPDATE ...")` statements in `upgrade()` for auditability — both read the pre-UPDATE row values correctly since PostgreSQL `UPDATE` statements are self-contained, and the copy statement is placed textually before the null statement per the acceptance criteria.
- Avoided the literal substrings `inaccuracies`/`mistakes`/`blunders` anywhere in the migration file (including the docstring, not just executable code) so the D-04 guardrail grep (`grep -v '^#' <file> | grep -c -E 'inaccuracies|mistakes|blunders'` == 0) holds unconditionally — the plan's acceptance criteria did not exempt comments/docstrings.
- Test user ID range 999_300-999_301 chosen for the new migration test suite to avoid FK collisions with existing migration test suites (116: 999_101-102, 117: 999_200-201, 91: 999_001-002).

## Deviations from Plan

None - plan executed exactly as written. The one minor addition (ruff-format pass on the generated migration file, committed separately as `82222a99`) is routine formatting hygiene, not a functional deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (compute module `app/services/accuracy_acpl.py`) can now target the canonical `white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl` columns knowing they are NULL and ready for refill on every dev-DB row.
- Plan 03 (live-hook wiring) and Plan 04 (backfill script) can rely on the `*_imported` columns as the untouched comparison/validation signal — verified preserved via the migration test.
- The dev database is currently at head with all canonical accuracy/acpl values NULL (migration was run/verified locally during this plan's execution) — this is the expected post-Plan-01 state for the rest of the phase.
- No blockers for Plan 02.

---
*Phase: 178-lichess-compatible-accuracy-acpl-computed-columns*
*Completed: 2026-07-18*

## Self-Check: PASSED

All created/modified files verified present on disk; all 5 task/summary commit hashes verified present in git log.
