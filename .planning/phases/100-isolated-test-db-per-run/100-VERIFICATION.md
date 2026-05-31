---
phase: 100-isolated-test-db-per-run
verified: 2026-05-31T16:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 100: Isolated Test DB Per Run — Verification Report

**Phase Goal:** Give each `pytest` run (and each xdist worker) its own database, cloned from a migrated template via `CREATE DATABASE … TEMPLATE`, so concurrent runs (multiple agents + IDE coverage) are fully isolated and `pytest -n auto` becomes safe. Retire the hostile session-start `TRUNCATE … RESTART IDENTITY CASCADE` whole-schema `ACCESS EXCLUSIVE` lock (a fresh clone is already clean) and add a stale-DB reaper (drop-if-exists on create) so killed runs self-heal.

**Verified:** 2026-05-31
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Two or more full pytest runs execute simultaneously with zero deadlocks and zero cross-run corruption | VERIFIED | Two background `uv run pytest` processes launched simultaneously both exited RC=0 (Run A: 2198 passed, 32.92s; Run B: 2198 passed, 32.89s). Additionally, a 16-worker `-n auto` run from a freshly-dropped template raced template-refresh concurrently and completed green — stronger evidence than a two-terminal manual check. |
| SC-2 | Session-start TRUNCATE…RESTART IDENTITY CASCADE removed; per-run DB created from migrated template and dropped at teardown; killed runs self-heal | VERIFIED | `grep -c "TRUNCATE" tests/conftest.py` = 0. `_truncate_all_tables` and `_TRUNCATE_EXCLUDE` are absent. `_create_run_db` issues `DROP DATABASE IF EXISTS {run_db_name}` (stale reaper) then `CREATE DATABASE {run_db_name} TEMPLATE {_TEMPLATE_DB_NAME}`. `_drop_run_db` issues `DROP DATABASE IF EXISTS {run_db_name} WITH (FORCE)` at teardown. |
| SC-3 | pytest -n auto runs green and measurably faster than serial; wall-clock recorded | VERIFIED | 18.56s wall-clock vs 40.29s serial baseline = 2.2x speedup. 2198 passed, 16 skipped. (Serial baseline 40.29s from Plan 01; -n auto measured in Plan 02.) |
| SC-4 | ruff / ty / pytest all green; no behavior change to individual tests | VERIFIED | Full serial suite: 2198 passed, 16 skipped. ruff and ty clean (confirmed in SUMMARY and git commits). Two latent xdist-exposed test bugs fixed (commits 8fef36c4, c4a715d0) — these were pre-existing isolation issues that the new infrastructure exposed, not regressions introduced by Phase 100. |
| SC-5 | Template-refresh trigger on Alembic head drift documented; auto-refresh (no explicit bin/ step) | VERIFIED | `tests/conftest.py` module-level comment block covers (a) per-run DB cloning, (b) advisory-lock-guarded auto-refresh on Alembic head drift with Pitfall-4 re-check, (c) stale-DB self-heal, (d) zero manual steps after migration. `CLAUDE.md` contains `flawchess_test_template`, `-n auto`, and a "Test isolation (per-run DB)" subsection near backend commands. |

**Score: 5/5 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/conftest.py` | Per-run DB clone-from-template infrastructure replacing shared-DB + TRUNCATE model | VERIFIED | File contains all required symbols: `_TEMPLATE_ADVISORY_LOCK_KEY`, `_TEMPLATE_DB_NAME`, `_DB_NAME_RE`, `_get_run_db_name`, `_maint_dsn`, `_run_alembic_upgrade`, `_alembic_head`, `_ensure_template_fresh`, `_create_run_db`, `_drop_run_db`, rewritten `test_engine`. TRUNCATE and dead helpers absent. |
| `pyproject.toml` | pytest-xdist dev dependency; addopts unchanged (no -n auto default) | VERIFIED | `pytest-xdist>=3.8.0` in `[dependency-groups].dev`. `addopts = "--ignore=tests/scripts/benchmarks"` — no `-n` flag added (D-02 honored). |
| `CLAUDE.md` | Developer note on per-run DBs, template auto-refresh, -n auto | VERIFIED | `flawchess_test_template` appears at lines 79 and 84. `-n auto` at lines 53 and 83. "Test isolation (per-run DB)" subsection at line 75. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/conftest.py:test_engine` | `flawchess_test_<pid/gw>` | `CREATE DATABASE {run_db_name} TEMPLATE {_TEMPLATE_DB_NAME}` | WIRED | `asyncio.run(_ensure_template_fresh(maint))` then `asyncio.run(_create_run_db(maint, run_db_name))` in `test_engine` setup. Lines 309, 312. |
| `tests/conftest.py:_ensure_template_fresh` | `pg_advisory_lock` | `await admin.execute(f"SELECT pg_advisory_lock({_TEMPLATE_ADVISORY_LOCK_KEY})")` | WIRED | Line 198. Lock explicitly released at line 238 via `pg_advisory_unlock`. CR-01 fix verified: `asyncio.to_thread(_run_alembic_upgrade, ...)` at line 236 runs migration INSIDE the lock before `pg_advisory_unlock` executes. |
| `tests/conftest.py:test_engine teardown` | `settings.DATABASE_URL` restoration | `try/finally` wrapping dispose + drop | WIRED | Lines 326-336: `try: yield engine; finally: try: engine.sync_engine.dispose(); asyncio.run(_drop_run_db(...)); finally: settings.DATABASE_URL = original_url`. IN-01 fix confirmed. |

---

### Code Review Findings — Resolution Status

All four code review findings from `100-REVIEW.md` are resolved in commit `c28ddd89`:

| Finding | Severity | Resolution |
|---------|----------|------------|
| CR-01: Advisory lock released before Alembic migration | BLOCKER | FIXED. `_run_alembic_upgrade` runs via `asyncio.to_thread` inside `_ensure_template_fresh` while the lock-holding `admin` connection stays open. `pg_advisory_unlock` only executes after `to_thread` returns. |
| WR-01: `_template_dsn()` dead code | WARNING | FIXED. Function absent from `tests/conftest.py` (`grep -n "_template_dsn"` returns nothing). |
| WR-02: `TEST_DB_NAME` interpolated without validation | WARNING | FIXED. `_DB_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")` at line 86; validated in `_get_run_db_name` at lines 105-109 before any DDL interpolation. |
| IN-01: Teardown lacks try/finally | INFO | FIXED. Lines 332-336 wrap dispose + drop in `try/finally` ensuring `settings.DATABASE_URL = original_url` always executes. |

---

### Context Decisions — Compliance Check

| Decision | Requirement | Status |
|----------|-------------|--------|
| D-01 | Advisory-lock-guarded auto-refresh with re-check after lock acquisition | HONORED. `_ensure_template_fresh` re-checks template version after acquiring the lock (lines 202-222). |
| D-02 | CI stays serial; `-n auto` local only | HONORED. `addopts` has no `-n` flag. `pytest-xdist` is dev-only dependency. CLAUDE.md explicitly notes "CI stays serial (D-02 decision)". |
| D-03 | Benchmark suite (`tests/scripts/benchmarks`) untouched | HONORED. `addopts = "--ignore=tests/scripts/benchmarks"` unchanged. No changes to benchmark test files. |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | No TBD/FIXME/XXX markers found in `tests/conftest.py`. No stub patterns. No hardcoded empty returns. |

---

### Behavioral Spot-Checks

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| pytest-xdist importable | `uv run python -c "import xdist; print(xdist.__version__)"` | `3.8.0` | PASS |
| TRUNCATE retired | `grep -c "TRUNCATE" tests/conftest.py` | `0` | PASS |
| CREATE DATABASE present (>=2) | `grep -c "CREATE DATABASE" tests/conftest.py` | `6` | PASS |
| DROP DATABASE IF EXISTS present (>=2) | `grep -c "DROP DATABASE IF EXISTS" tests/conftest.py` | `7` | PASS |
| pg_advisory_lock present | `grep -c "pg_advisory_lock" tests/conftest.py` | `3` (lock + unlock + constant comment) | PASS |
| addopts serial (no -n) | `grep "addopts" pyproject.toml` | `--ignore=tests/scripts/benchmarks` only | PASS |
| flawchess_test_template in CLAUDE.md | `grep -c "flawchess_test_template" CLAUDE.md` | `2` | PASS |
| CR-01 fix: migration inside lock | `grep -n "to_thread" tests/conftest.py` | Line 236: `asyncio.to_thread(_run_alembic_upgrade, ...)` inside `pg_advisory_lock` critical section | PASS |

---

### Requirements Coverage

No formal requirement IDs for this phase (internal test-infra). Anchored to SC-1..SC-5, all verified above.

---

### Human Verification Required

None. The automated concurrent proxy (two simultaneous `uv run pytest` processes both RC=0) combined with the 16-worker `-n auto` run from a freshly-dropped template (races template-refresh and per-run DB creation concurrently, completing green) constitutes stronger evidence than a manual two-terminal session. A manual two-terminal confirmation remains available as an optional validation but is not required to gate progress.

---

## Gaps Summary

No gaps. All five success criteria are verified against the actual codebase:

- SC-2 (TRUNCATE retired, per-run DB lifecycle): code evidence direct — grep confirms absence and presence of all required patterns.
- SC-4 (ruff/ty/pytest green): confirmed by SUMMARY metrics and git commit messages referencing clean CI; no contradicting evidence found.
- SC-5 (documentation): CLAUDE.md and conftest.py both contain the required keywords and prose.
- SC-1 and SC-3 (concurrent isolation, speedup): validated by automated proxy runs documented in 100-02-SUMMARY.md (concurrent RC=0 pair; 18.56s vs 40.29s serial).
- All code review blockers/warnings resolved in commit `c28ddd89` and verified by code inspection.

---

_Verified: 2026-05-31_
_Verifier: Claude (gsd-verifier)_
