---
phase: 241-codebase-cleanup
plan: 27
subsystem: testing
tags: [cleanup, comments, tests, planning-tags, codemod]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "tests/routers, tests/repositories, tests/schemas, tests/models, tests/integration, tests/prompts and tests/seed_fixtures.py (45 of the 48 files in scopes/241-27.txt) free of planning tags in comments, docstrings and test names"
affects: [241-66, 241-70]

actuals:
  tokens: 71600
  tasks: 2
  commits: 2
plan_head_before: 85740f66266ab2a808cad83a20a8a679da18ff66
plan_head_after: 0ab5b7aea463bb0a583ad35a4b402164a39f3439

tech-stack:
  added: []
  patterns:
    - "Compact edit specs (path, line, n_old_lines, new_text | (old_substring, new_substring)) turned into apply-edits JSON by a scratch helper (temp/241-27/mk.py, gitignored)"

key-files:
  created: []
  modified:
    - tests/repositories/test_train_repository.py
    - tests/routers/test_train.py
    - tests/repositories/test_opening_insights_repository.py
    - tests/integration/test_alembic_migrations.py
    - tests/integration/test_benchmark_metric_enum.py
    - "plus 40 more test files (45 of the 48 scoped files changed)"

key-decisions:
  - "Only one tagged test name existed in scope: test_resolve_grade_instant_payload_tier_d10 was renamed (listed below); every other test name is tag-free and stays"
  - "Assert messages, skip reasons and other string literals that still carry tags were left alone per the test-file rule"
  - "Local k-table / 'Plan 02 holds k 20-49' reservation notes in the medal and leaderboard tests were reworded to describe the reservation without plan references; the k numbers themselves are unchanged"

patterns-established:
  - "Leftover grep beyond the scan regex: Plan NN, Task N, Wave, SC-N, V4/IDOR, REQ-IDs (STORE-06, PASTE-07, PUSH-01), CR-02/WR-02, 'Quick NNNNNN-xxx', 'Finding C', 'UAT'"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 95min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 27: Test comments (routers, repositories, schemas, models, integration, prompts) Summary

**Planning tags are gone from comments, docstrings and test names across 45 test files (about 600 tagged lines plus the shapes the scan regex misses), with an empty token diff against PHASE_BASE and 785 tests collected before and after.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 2
- **Files modified:** 45 of the 48 scoped files (tests/integration/__init__.py, tests/repositories/__init__.py and tests/routers/__init__.py were already clean and stay untouched)

## Accomplishments

- Task 1 (`ae1c71e46`): tests/repositories (24 files), tests/models (4), tests/integration (2), tests/prompts (1) and tests/seed_fixtures.py. The largest file was tests/repositories/test_train_repository.py (97 scan hits after the codemod).
- Task 2 (`0ab5b7aea`): tests/routers (12 files with hits) and tests/schemas (7), the largest being tests/routers/test_train.py (64 hits after the codemod, including a 120-line module docstring rewritten to drop plan labels).
- Codemod vs hand edits:

| Task | Lines rewritten by the codemod | Lines flagged "needs hand edit" | Hand-edit spans (apply-edits) |
|---|---|---|---|
| 1 | 135 in 20 files | 205 | about 215 in 14 batches, plus a 5-hit regex pass for one repeated two-line shape |
| 2 | 182 in 18 files | 123 | 148 in 4 batches |

The codemod diff was reviewed line by line; none of its rewrites needed to be reverted. The hand edits also repaired what it leaves behind (a lowercase sentence start after a removed leading tag, for example "Pv can be NULL" and "# custom-start games ...").

## Renamed tests (old -> new)

| File | Old | New |
|---|---|---|
| tests/repositories/test_train_repository.py | `test_resolve_grade_instant_payload_tier_d10` | `test_resolve_grade_instant_payload_tier` |

`git grep` for the old name outside `.planning` finds nothing. The plan expected few tagged names; the scan flagged none, and a broader name grep (`phase_`, `seed_`, `wr_`, `cr_`, `_dNN`, `sc_`, `plan_`) found only this one. Names ending in HTTP status codes (`_200`, `_404`, `_422`) are not tags.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-27.txt` | exit 0 (48 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-27.txt` | exit 0 (48 selected, 45 changed, no residue) |
| `pytest --collect-only -q` over the six test directories, before / after | 785 / 785 (387 in repositories+models+integration+prompts, 398 in routers+schemas) |
| `pytest -q` serial: repositories, models, integration, prompts | 387 passed |
| `pytest -q` serial: routers, schemas | 398 passed (includes tests/schemas/test_train_telemetry_parity.py, which still matches the frontend caps) |
| `ruff check tests`, `ruff format --check tests` | clean |
| `ty check app/ tests/ scripts/` | all checks passed |

Baseline before any edit: ruff check, ruff format --check and ty were all clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` (lockfile only, no new packages) before the baseline gates.

**2. [Plan adaptation] Tests ran serially, not with `-n 4`**
- The wave-3 parallel-execution notes forbid `-n` against the shared dev Postgres, so the plan's `pytest -n 4 -x` commands ran serially. This is environmental, not a plan failure. No order-dependent failure showed up; all 785 passed.

**3. [Plan adaptation] `source_scan_tests.sh` not run**
- No file under `app/` or `frontend/src` changed, and none of the 48 files is read as source text by those tests, so neither half is affected.

**4. [Rule 2 - stale content, STYLE-GUIDE 2.2] Wording fixes next to removed tags**
- tests/integration/test_alembic_migrations.py: the docstring said the primary key is composite on `(user_id, metric)`; it now lists `time_control_bucket` as the code and its own assertion do.
- tests/models/test_user_benchmark_percentile.py: the "INTENDED RED ... fails until Plan 02" paragraph described a state that no longer exists; it now states what the test enforces.
- tests/repositories/test_opening_insights_repository.py: the SEED-035 PK docstring now states the current schema instead of the migration history.
- tests/routers/test_push.py: the "deviation from the plan's literal instruction" mocking note now states only why `httpx.AsyncClient.post` cannot be patched directly.
- Comments that said "cold drain" now say "entry-ply lane" (STYLE-GUIDE 3.3 row 33).

**Total deviations:** 1 blocking environment prep, 2 plan adaptations, 1 wording group; none touch code, assertions, fixtures or strings.

## Issues Encountered

- The sandbox rejects compound shell lines that mix `git` with computed arguments (`$(...)`, variables, `for` loops); files were staged by explicit literal paths.
- A first spec for tests/models/test_user_benchmark_percentile.py replaced one line too few and left a stray closing `"""`; caught on review and fixed before the commit. Tests were run after all edits, not before.

## Known Stubs

None.

## Threat Flags

None. Comment, docstring and test-name edits only; the token diff against PHASE_BASE is empty apart from the one rename (T-241-43 mitigated).

## Notes for downstream plans

- Left on purpose (string literals, outside the comment/docstring/test-name rule): assert messages and skip reasons that still say `(D-08)`, `(D-06)`, `per D-05`, `Plan 04`, `Phase 99 D-09 — Plan 02 must add it`, `Phase 87.5 D-07`, `SEED-035 migration`, `Pitfall 4` in tests/integration, tests/models, tests/prompts, tests/repositories/test_opening_insights_repository.py and tests/repositories/test_user_benchmark_percentiles_repository.py, `(D-02)` in tests/repositories/test_query_utils.py.
- `FLAWCHESS-64` in tests/routers/test_bots.py is a Sentry issue id and was kept.
- tests/repositories/test_game_repository_zero_pending.py and tests/repositories/test_train_leaderboard_repository.py were only touched for comments, as the plan states; the later X3/X5 renames (241-66) are untouched.
- `Stage B` and `Tier-2` in the zero-pending and benchmark-percentile tests are live domain terms (they appear in app/repositories/game_repository.py) and were kept.

## Self-Check: PASSED

Commits `ae1c71e46` and `0ab5b7aea` verified as ancestors of HEAD; scan/diff exit codes and the collection counts are recorded above.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
