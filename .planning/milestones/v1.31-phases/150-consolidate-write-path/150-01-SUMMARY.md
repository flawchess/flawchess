---
phase: 150-consolidate-write-path
plan: 01
subsystem: testing
tags: [pytest, sqlalchemy-async, postgres-jsonb, golden-snapshot, eval-pipeline]

requires: []
provides:
  - "Committed reproducible generator (scripts/gen_write_path_golden.py) capturing the current (post-149, post-FLAWCHESS-8D) game_flaws write-path output as 7 golden JSON fixtures"
  - "Drift-check equivalence test (tests/services/test_flaw_upsert_equivalence.py) driving the production submit path (_apply_atomic_submit), green against HEAD"
  - "Shared scenario builders (tests/services/write_path_golden_scenarios.py) reused by both the generator and the test so they can never diverge"
affects: [150-04-consolidate-write-path-diff-upsert]

tech-stack:
  added: []
  patterns:
    - "Committed-generator + drift-check test (mirrors scripts/gen_global_percentile_cdf.py + tests/scripts/test_gen_global_percentile_cdf_unchanged.py), adapted for DB-round-trip game_flaws state instead of pure SQL strings"
    - "Ephemeral per-run test DB for a standalone script: reuses tests/conftest.py's private template-clone/drop helpers directly rather than duplicating them"
    - "Shared scenario-builder module imported by both a scripts/ generator and a tests/ equivalence test (extends the existing cross-file test-helper reuse pattern already used by tests/test_worker_heartbeats.py)"

key-files:
  created:
    - scripts/gen_write_path_golden.py
    - tests/services/write_path_golden_scenarios.py
    - tests/services/test_flaw_upsert_equivalence.py
    - tests/fixtures/write_path_golden/scenario_1_fresh_full_submit.json
    - tests/fixtures/write_path_golden/scenario_2_residual_hole_retry.json
    - tests/fixtures/write_path_golden/scenario_3_flip_out.json
    - tests/fixtures/write_path_golden/scenario_4_flip_in.json
    - tests/fixtures/write_path_golden/scenario_5_entry_pass_replaced.json
    - tests/fixtures/write_path_golden/scenario_6_dedup_transplant_no_sentinel.json
    - tests/fixtures/write_path_golden/scenario_7_blobs_pending_suppression.json
  modified: []

key-decisions:
  - "7 scenarios, not 8 (plan-authoring inconsistency reconciled — see Deviations)"
  - "All scenarios drive _apply_atomic_submit directly (the single stable production entry point), not _full_drain_tick — both call the same _classify_and_fill_oracle, and _apply_atomic_submit already runs with blobs_pending=True, so it alone covers every D-02 scenario including the ones the plan's read_first pointed at test_full_eval_drain.py"
  - "Generator spins up its own ephemeral per-run test DB (clone-and-drop of flawchess_test_template) by reusing tests/conftest.py's private helpers directly, rather than requiring a persistent flawchess_test database or touching bin/reset_db.sh"

patterns-established:
  - "Shared scenario/fixture-builder module (tests/services/write_path_golden_scenarios.py) as the single source of truth for both a committed regeneration script and its drift-check test"

requirements-completed: [WRITE-03]

coverage:
  - id: D1
    description: "Committed generator (scripts/gen_write_path_golden.py) regenerates 7 golden game_flaws fixtures byte-identically from current HEAD"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "uv run python -m scripts.gen_write_path_golden; git diff --exit-code tests/fixtures/write_path_golden/"
        status: pass
    human_judgment: false
  - id: D2
    description: "Equivalence test (tests/services/test_flaw_upsert_equivalence.py) drives the production submit path and asserts byte-for-byte match against each golden, including explicit is-None checks for NULL-expected blob columns"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "tests/services/test_flaw_upsert_equivalence.py::test_write_path_matches_golden (7 parametrized cases)"
        status: pass
      - kind: unit
        ref: "tests/services/test_flaw_upsert_equivalence.py::test_fixture_directory_covers_all_named_scenarios"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-04
status: complete
---

# Phase 150 Plan 01: Write-Path Golden-Snapshot Harness Summary

**Committed generator + 7 golden `game_flaws` fixtures capturing the current (post-149, post-FLAWCHESS-8D) delete-then-insert write path, plus a drift-check equivalence test that drives the production `_apply_atomic_submit` entry point directly.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 10 (9 new + 0 modified, per commit diffstat)

## Accomplishments

- `scripts/gen_write_path_golden.py` spins up its own ephemeral per-run test database (cloned from `flawchess_test_template`, same machinery `tests/conftest.py` uses for every pytest run), runs 7 named scenarios through `app.routers.eval_remote._apply_atomic_submit`, and writes one committed JSON fixture per scenario. Confirmed byte-identical across three independent regenerations.
- `tests/services/write_path_golden_scenarios.py` factors the 7 scenario setups (game+position construction, monkeypatched tactic detection, submit sequencing) into one module imported by BOTH the generator and the equivalence test, so they can never drift apart.
- `tests/services/test_flaw_upsert_equivalence.py` parametrizes over the 7 fixtures, re-runs each scenario, and asserts exact equality — with an explicit `is None` branch for NULL-expected blob columns (`allowed_pv_lines`/`missed_pv_lines`), per the JSONB `None`-vs-`null::jsonb` landmine. A completeness-guard test fails if a fixture goes missing or a stale one is left behind.
- Full backend suite (3162 passed, 18 skipped), `ruff check .`, `ruff format --check`, and `ty check app/ tests/` all clean.

## Task Commits

1. **Task 1: Committed generator + 8 golden fixtures from current HEAD** - `aed26f5c` (feat)
2. **Task 2: Equivalence test + completeness guard, green against HEAD** - `51ffcd14` (test)

_Note: "8" in the plan's task name is the plan-authoring inconsistency documented below — 7 fixtures were produced, matching the plan's own concrete `artifacts` list._

## Files Created/Modified

- `scripts/gen_write_path_golden.py` - Reproducible generator; ephemeral per-run test DB; drives `_apply_atomic_submit` for all 7 scenarios; writes committed JSON fixtures.
- `tests/services/write_path_golden_scenarios.py` - Shared scenario builders (setup + monkeypatches + `game_flaws` dump) reused by both the generator and the test.
- `tests/services/test_flaw_upsert_equivalence.py` - Parametrized drift-check equivalence test + fixture-completeness guard.
- `tests/fixtures/write_path_golden/*.json` (7 files) - Committed golden fixtures, one per named scenario.

## Decisions Made

- **All 7 scenarios drive `_apply_atomic_submit` directly**, not `_full_drain_tick`. Both call the same `_classify_and_fill_oracle`, and `_apply_atomic_submit` already runs with `blobs_pending=True` (Phase 147 D-01/D-03), so it alone reproduces every D-02 scenario — including the two the plan's `read_first` pointed at `test_full_eval_drain.py` (entry-pass replacement, `blobs_pending` suppression). This gives the harness ONE stable entry point instead of two, simplifying Plan 04's future swap-in verification.
- **The generator creates its own ephemeral per-run database** (clone-and-drop of `flawchess_test_template`, reusing `tests/conftest.py`'s private helpers directly — `_ensure_template_fresh`, `_create_run_db`, `_drop_run_db`, `_maint_dsn`) rather than requiring a persistent `flawchess_test` database to already exist and be migrated. This makes `uv run python -m scripts.gen_write_path_golden` runnable standalone with zero setup beyond the dev Postgres container already being up, and keeps the "never `bin/reset_db.sh`, never production" prohibition trivially satisfiable.
- **`async engine.dispose()` instead of `sync_engine.dispose()`** at script teardown — the sync path deferred asyncpg connection close to a GC finalizer that fires after `asyncio.run()`'s loop closes, producing a benign-but-noisy `MissingGreenlet` traceback on every run. Awaiting `engine.dispose()` from inside the still-running loop closes cleanly.

## Deviations from Plan

### 1. [Plan-authoring inconsistency] 7 scenarios, not 8

- **Found during:** Task 1, while re-deriving the scenario list from CONTEXT.md D-02 and RESEARCH.md's own scenario table.
- **Issue:** The plan's `must_haves.truths` and `acceptance_criteria` both say "8 scenarios" / "8 golden fixtures," but the plan's own concrete `artifacts` list enumerates exactly 7 filenames (`scenario_1` through `scenario_7`), and RESEARCH.md's scenario table explicitly states scenario 4 ("flip IN") "is the inverse of scenario 3" — i.e. CONTEXT.md D-02's numbered list of 7 items ALREADY includes the flip-IN case as item 4; there is no separate 8th scenario anywhere in either source document.
- **Resolution:** Built exactly 7 scenarios/fixtures, matching the plan's own concrete `artifacts` list and RESEARCH.md's scenario table. Documenting here per Rule-4-adjacent transparency (a plan-text inconsistency, not a code bug) rather than silently reconciling it. If an 8th scenario was genuinely intended, it isn't identifiable from either CONTEXT.md D-02 or RESEARCH.md — a re-read of both turns up only 7 distinct cases.
- **Files affected:** None (documentation-level reconciliation only — `SCENARIO_NAMES` in `write_path_golden_scenarios.py` has 7 entries, matching the artifact list).
- **Verification:** `test_fixture_directory_covers_all_named_scenarios` enforces exactly-one-fixture-per-`SCENARIO_NAMES`-entry (7), so this is a locked invariant, not a one-off judgment call.

### 2. [Scope simplification] Did not modify `tests/test_eval_worker_endpoints.py`

- **Found during:** Task 1, following the plan's own `read_first` instruction to "check for import cycles between test files before" factoring out shared builders.
- **Issue:** The plan's frontmatter lists `tests/test_eval_worker_endpoints.py` under `files_modified`, anticipating that the builders needed (`_insert_game`, `_insert_game_positions`, `_atomic_request`, `_BLUNDER_SUBMIT_EVALS_142`, `_FLAT_SUBMIT_EVALS_142`, `_insert_opening_cache_with_pv`, `_delete_games`, `_delete_opening_cache`, `_SIX_PLY_PGN_142`, `_WALKABLE_PV_PLY2`/`_WALKABLE_PV_PLY3`) might need to be exposed/exported first.
- **Resolution:** All of these were already module-level (not nested inside a class) and therefore directly importable — `tests/test_worker_heartbeats.py` already establishes the precedent of importing these exact underscore-prefixed helpers cross-file. No changes to `tests/test_eval_worker_endpoints.py` were needed; `write_path_golden_scenarios.py` imports them directly.
- **Files affected:** None.
- **Verification:** `uv run pytest tests/test_eval_worker_endpoints.py tests/test_worker_heartbeats.py` still green (118 tests, no regressions from the additional import).

---

**Total deviations:** 2 (1 plan-text inconsistency reconciled, 1 scope simplification — no code changed beyond what was needed)
**Impact on plan:** No functional impact. Both are documentation/scope clarifications; the delivered harness satisfies every concrete artifact and acceptance criterion in the plan.

## Issues Encountered

- Standalone-script async-engine teardown produced a benign `MissingGreenlet` traceback on stderr (exit code still 0, fixtures still written correctly) — root-caused to `sync_engine.dispose()` deferring connection close past the `asyncio.run()` loop's lifetime; fixed by awaiting `engine.dispose()` instead. See Decisions above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 (R3 diff/upsert swap) can now re-run `tests/services/test_flaw_upsert_equivalence.py` unchanged as its equivalence proof — the same 7 scenarios, the same production entry point (`_apply_atomic_submit`), the same golden fixtures.
- No blockers. The harness is intentionally decoupled from Plans 02/03 (R1 completion-decision unification, R4 classify-preamble unification) — those may land before Plan 04 without touching this harness, since it drives the stable `_apply_atomic_submit` entry point rather than any of the internals being consolidated.

---
*Phase: 150-consolidate-write-path*
*Completed: 2026-07-04*

## Self-Check: PASSED

All 10 created files verified present on disk; all 3 commit hashes (`aed26f5c`, `51ffcd14`, `bb29421f`) verified present in git log.
