---
phase: 241-codebase-cleanup
plan: 25
subsystem: testing
tags: [cleanup, comments, tests, planning-tags]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "tests/test_[g-m]*.py (32 of the 35 scoped files changed) free of planning tags in comments and docstrings, token diff against PHASE_BASE empty"
affects: [241-26, 241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 7a590075d8b088455b1951eb934cc6b337feb2f4
plan_head_after: 30f85be3401fe375aa67bf2b4c3526a2e252fbe4

key-files:
  modified:
    - tests/test_import_service.py
    - tests/test_library_repository.py
    - tests/test_library_router.py
    - tests/test_insights_schema.py
    - tests/test_guest_cleanup_service.py
    - tests/test_migration_117.py

key-decisions:
  - "Assertion messages and other string literals that still carry tags (for example 'guard broken (D-02)', 'after Phase 112') are left untouched, as the plan forbids any string change"
  - "Identifiers that carry a number (PHASE_116_REVISION in test_migration_116_full_evals.py, _compile_flaw_filter_sql_129 in test_library_repository.py) are not test function or class names, so the token diff rejects renaming them without an allow-list or rename-map; left and reported"
  - "TDD-staging narration in test_import_service.py docstrings and comments ('Currently: ...', 'After Task 2: ...', 'xfail against current code') was rewritten in present tense since the tests are no longer xfail"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 25: Tests g-m comment cleanup Summary

**Planning tags (Phase/Plan/D-NN/SEED/UAT/quick-task IDs, requirement and threat IDs) removed from comments and docstrings of the g-m root tests, with an empty token diff, identical test ids and 567 tests passing.**

## Accomplishments

- First scan of the 35 scoped files: 417 matches. Codemod rewrote 184 lines in 25 files; 242 matches needed hand edits, done as 9 `apply-edits` batches (257 spans) plus one direct edit. Final `scan --gate` and `scan --gate --advisory`: 0 matches.
- No test function or class name carried a tag, so there are no renames. The sorted `pytest --collect-only` id lists before and after are identical (567 tests).
- Comments that restated planning history were rewritten as the rule or deleted (STYLE-GUIDE 2.1/2.2): for example the TDD RED/GREEN staging paragraphs in `test_library_repository.py`, the `Currently:/After Task 2:` notes in `test_import_service.py`, the "retired in Phase 108" note in the library repository module docstring (now "there is no SQL<->kernel cross-check test"), and the stale `placeholder, implemented in 106-03` line (the `analyzed_denominator` tests exist).
- "per D-NN" replacements (decision stated in a clause): guest purge scope in `test_guest_cleanup_service.py` (guests only, registered users keep Train state), `test_impersonation.py` header (token claims, superuser and nested guards, revocation, last_login), `test_gen_vapid_keys.py` ("an empty key turns push off").
- Migration test strings (revision ids, table, column and constraint names, paths such as `alembic/versions/20260614_120000_phase_117_1_...py`) and the phase-numbered test file names are unchanged. Module docstrings now name migrations by what they do ("the full_evals_completed_at migration", "the eval-convention clean-slate migration").
- `test_google_link_takeover.py`, `test_insights_llm_thinking.py` and `test_migration_only_indexes_exist.py` were already clean and are untouched.

## Task Commits

1. **Task 1: import, library, insights, guest and integration tests** - `fa598a053` (12 files changed; `test_google_link_takeover.py` needed nothing)
2. **Task 2: game, migration, llm-log, lifespan and small root tests** - `30f85be34` (20 files changed; plan gates run over the whole scope)

`commits: 2` is measured with `git rev-list --count 7a590075d..HEAD` before this SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-25.txt` | exit 0, 0 matches |
| `cleanup.py diff --scope scopes/241-25.txt` | exit 0 (35 selected, 32 changed, no residue) |
| `ruff check tests`, `ruff format --check tests` | clean (one docstring pair re-wrapped by `ruff format` in test_library_repository.py) |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean before edits too) |
| `pytest --collect-only` on the 35 files | 567 before, 567 after, ids identical |
| `pytest -p no:warnings` on the 35 files, serial | 288 + 279 = 567 passed |

Step 0 baseline on the untouched tree: ruff check, ruff format --check and ty were clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fresh worktree environment**
- `uv sync --group maia-inference` (lockfile only) before ty; no tracked files changed.

### Plan-text adaptations

**2. Serial pytest.** The gate command used `-n 4`; as instructed for parallel wave-3 executors the scope was run serially without `-n` (two invocations covering all 35 files). Environmental, not a plan failure.

**3. Task 1 and Task 2 edited together.** The codemod and the broad provenance grep ran over the whole scope in one pass; the work was committed per task by staging each task's files separately. `test_insights_llm_thinking.py` (listed in files_modified but in neither task's file list) needed no edits.

**4. Leftover provenance beyond the scan regex.** A broad grep (Wave, Task N, UAT-nnn, TDD RED, `(phase 62)`, `CLAUDE.md V5`, `Phase-64-added`, `D-7`, `quick-NNN`) found and cleaned about 45 more comment and docstring lines that the scan regex does not match.

## Known residue (reported, not fixed; all outside "comments, docstrings, test names")

- Assertion messages still carrying tags (strings, off-limits per the plan): `test_game_flaws_model.py` (`after Phase 112`, `(D-02)`), `test_guest_cleanup_service.py` (`(D-08)`), `test_imports_router.py` (`(D-04)`), `test_import_service.py` (`Task 2`, `Pitfall 2, 90-RESEARCH.md`), `test_last_activity_middleware.py` (`(D-07)`, `(D-08 defensive)`), `test_library_repository.py` (`(D-04)`, `(D-05a)`, `(D-04, R3)`, `Quick 260717-gmg`), `test_library_router.py` (`per D-05`, `(D-04)`), `test_migration_240_reveal_tour_stage.py` (`The Phase 222 walkthrough ...`), `test_migration_suppress_ungated_tactic_tags.py` (`D-06 sentinel`).
- Identifiers with numbers: `PHASE_116_REVISION` (test_migration_116_full_evals.py:37, :301) and `_compile_flaw_filter_sql_129` (test_library_repository.py, 9 uses). A rename needs an allow-list entry or rename map for the token diff; candidates for a later naming plan.

## Known Stubs

None.

## Threat Flags

None. Only comment and docstring text changed; `cleanup.py diff` compared every code and string token against PHASE_BASE (T-241-41 mitigated).

## Self-Check: PASSED

Commits `fa598a053` and `30f85be34` are ancestors of HEAD; `scan --gate` and `diff` exit 0; collection ids identical.
