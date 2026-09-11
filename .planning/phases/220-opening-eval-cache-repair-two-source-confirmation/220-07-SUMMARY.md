---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 07
subsystem: database
tags: [opening-cache, two-source-confirmation, stockfish, alembic, tdd]

# Dependency graph
requires:
  - phase: 220-06
    provides: "Production repair run complete; measured confirm_floor=0.029419322 (calibration_n=500, 2026-09-10 11:47:37Z, Stockfish 18) and the opening_cache_audit status trail this plan's migration reads"
provides:
  - "Seven provenance columns on opening_position_eval (confirmed, n_sources, disagreements, engine_version, written_at, confirmed_at, source_game_id) via a release-2 migration whose batched status-derived marking took ~1.3s on dev's 82,586-row cache"
  - "Candidate/promote/replace write path (_upsert_opening_cache) replacing first-write-wins: a position is trusted only once two different games agree within OPENING_CACHE_AGREE_MAX_SCORE_DELTA=0.03"
  - "Confirmed-only read paths (_fetch_dedup_evals / _fetch_cached_opening_hashes) -- a candidate is never transplanted or lease-omitted"
  - "scripts/opening_cache_repair.py demote --engine-version <v>, the operator escape hatch for a scale-changing engine bump"
  - "db-report Check C's two-source counters promoted from conditional to unconditional"
affects: [220-08]

# Actuals (#2632)
actuals:
  tokens: 27470
  tasks: 4
  commits: 6
  plan_head_before: 175fcc0bf7705abb25aac820703778d644566530

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Alembic keyset-walk batched status-derived UPDATE (no prior precedent in this repo) -- MARK_CONFIRMED_SQL run repeatedly with a nullable :cursor bind, exported as a module constant so a test executes the exact statement"
    - "Write-path partition/apply split (_partition_cache_writes / _apply_cache_writes) to stay under CLAUDE.md's nesting-depth/LOC limits on a 4-bucket (insert/skip/promote/replace) algorithm"
    - "Optimistic concurrency on cache promote/replace via `confirmed = false AND source_game_id IS NOT DISTINCT FROM :expected_source` -- a losing race is silently not counted, never retried"

key-files:
  created:
    - alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py
  modified:
    - app/models/opening_position_eval.py
    - app/services/eval_drain.py
    - app/services/eval_apply.py
    - scripts/opening_cache_repair.py
    - .claude/skills/db-report/SKILL.md
    - tests/models/test_opening_cache_audit_models.py
    - tests/services/test_eval_drain.py
    - tests/services/test_full_eval_drain.py
    - tests/test_eval_worker_endpoints.py
    - tests/scripts/test_opening_cache_repair.py

key-decisions:
  - "Checkpoint decision (Task 1, resolved by the operator via the continuation dispatch before this execution began): option id 'proceed' -- batched status-derived marking inside the release-2 migration, not an operator mark-confirmed subcommand -- decided 2026-09-11."
  - "OPENING_CACHE_AGREE_MAX_SCORE_DELTA = 0.03, rounded up from the prod-measured confirm_floor=0.029419322 (calibration_n=500, calibrated 2026-09-10T11:47:37Z, Stockfish 18; 220-06-SUMMARY.md)."
  - "Dev wall clock of the marking keyset walk: the full `alembic upgrade head` command (process startup + one ACCESS EXCLUSIVE metadata-only ALTER TABLE + 2 keyset-walk passes at 50k rows/batch over 82,586 opening_position_eval rows / 106,615 opening_cache_audit rows) completed in ~1.3s wall clock (0.83s user + 0.13s system, measured via `time`); the downgrade -1 / upgrade head round trip completed in a further ~1.3s. All 82,586 dev cache rows matched a post-repair audit status and were marked confirmed."
  - "Gate test changes (six-gate-test acceptance criterion): of the 7 tests executing OPENING_CACHE_BACKFILL_SQL as the gate, only the 3 asserting POSITIVE inclusion (test_dedup_hits_parity_source, test_wr02_engine_source_included, test_dedup_best_move_transplanted) needed an explicit confirm-the-seeded-row step; the 4 negative-exclusion tests and the donor-ordering test were unaffected by the confirmed filter (their seeded hash is either never inserted or never read through the filtered path). Added the plan-required reverse test (test_confirmed_only_candidate_not_returned_by_fetch_dedup_evals) plus a second confirmed_only test in tests/test_eval_worker_endpoints.py."
  - "_insert_opening_cache / _insert_opening_cache_with_pv (tests/test_eval_worker_endpoints.py) now default confirmed=True (n_sources=2) -- every pre-existing caller assumed an already-established, immediately-transplantable cache row; a confirmed=False keyword lets the two new confirmed_only tests seed a genuine candidate."

patterns-established:
  - "Pattern: split a 4+-bucket write algorithm into partition (pure) + apply (I/O) functions, one write-helper per bucket, to stay under CLAUDE.md's nesting-depth-4 / LOC-200 gate on a single orchestrating function."

requirements-completed: [CACHEFIX-08]

coverage:
  - id: D1
    description: "Release-2 migration adds seven provenance columns to opening_position_eval in one metadata-only ALTER TABLE and marks the repair's verified rows confirmed via a batched keyset walk over opening_cache_audit.status"
    requirement: CACHEFIX-08
    verification:
      - kind: unit
        ref: "tests/models/test_opening_cache_audit_models.py::TestMigrationMarking#test_migration_marking_matches_status"
        status: pass
      - kind: integration
        ref: "uv run alembic upgrade head && downgrade -1 && upgrade head (dev DB round trip)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Candidate/promote/replace write path: a first write inserts a candidate, a second agreeing source from a different game promotes it, a disagreeing one replaces it and bumps disagreements, a same-source write neither promotes nor disagrees, a confirmed row is immutable except pv self-heal, and Sentry fires once at disagreements==2"
    requirement: CACHEFIX-08
    verification:
      - kind: unit
        ref: "tests/services/test_eval_drain.py::TestOpeningEvalCacheWrite (39 tests, incl. test_promote_confirms_on_agreement, test_agree_boundary_promotes_exactly_at_constant, test_disagree_replaces_unconfirmed_candidate, test_disagree_second_fires_sentry_at_two, test_confirmed_immutable_except_pv_heal, test_self_promotion_guarded_by_source_game_id, test_empty_targets_is_noop)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both read paths (transplant via _fetch_dedup_evals, lease-omit via _fetch_cached_opening_hashes) filter to confirmed rows only, enforced in exactly one place"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::test_confirmed_only_candidate_not_returned_by_fetch_dedup_evals; tests/test_eval_worker_endpoints.py::test_fetch_cached_opening_hashes_confirmed_only"
        status: pass
    human_judgment: false
  - id: D4
    description: "OPENING_CACHE_BACKFILL_SQL inserts rows with an explicit confirmed=false; the six pre-existing gate tests still pin the backfill's SELECT/JOIN/WHERE predicates"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "tests/services/test_full_eval_drain.py::TestDedupHitsParity (7 gate tests + 1 new reverse test)"
        status: pass
    human_judgment: false
  - id: D5
    description: "scripts/opening_cache_repair.py demote --engine-version <v> un-confirms rows recorded against that engine version, is dry-runnable, --limit-cappable, and takes no _STAGE_ORDER gate"
    requirement: CACHEFIX-08
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestDemote (4 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "db-report Check C's disagreements/unconfirmed counters (Query 12b) are unconditional output now that the columns exist"
    requirement: CACHEFIX-08
    verification: []
    human_judgment: true
    rationale: "Documentation-only change (no test asserts markdown prose); correctness verified by grep in acceptance criteria, but whether the guidance reads well is a human judgment call."
  - id: D7
    description: "Checkpoint decision: the release-2 migration was approved to proceed with batched marking inside the migration"
    requirement: CACHEFIX-08
    verification: []
    human_judgment: true
    rationale: "Human decision, already resolved by the operator via the continuation dispatch before this execution began (option 'proceed', 2026-09-11)."

# Metrics
duration: ~55min
completed: 2026-09-11
status: complete
---

# Phase 220 Plan 07: Two-Source Confirmation (CACHEFIX-08) Summary

**Two-source confirmation replaces first-write-wins on `opening_position_eval`: a position is trusted only after two different games agree on it within the prod-measured 0.03 expected-score noise floor, with a D-13 self-promotion guard, D-12 Sentry throttling, and an operator `demote` escape hatch.**

## Performance

- **Duration:** ~55 min (commit span 2026-09-11T15:59:30Z to 2026-09-11T16:30:25Z; the read/context-gathering phase before the first commit was not separately timestamped)
- **Completed:** 2026-09-11
- **Tasks:** 4 (1 pre-resolved checkpoint + 3 implementation tasks, 2 of them TDD)
- **Commits:** 6 (1 migration, RED+GREEN for Task 3, RED+GREEN for Task 4, 1 cross-task test-fallout fix)
- **Files modified:** 10 (1 created, 9 modified)

## Accomplishments

- **Release-2 migration** (`b7d4f5a60002`): seven provenance columns (`confirmed`, `n_sources`, `disagreements`, `engine_version`, `written_at`, `confirmed_at`, `source_game_id`) added to `opening_position_eval` in one metadata-only `ALTER TABLE`, followed by a batched keyset-walk `UPDATE` that derives `confirmed=true` from `opening_cache_audit.status IN ('screened_clean','confirmed_clean','repaired')` — the repair pipeline's own verified output. Measured on dev: the full round trip (upgrade → downgrade → upgrade) over 82,586 cache rows / 106,615 audit rows completed in ~1.3s each direction; every dev cache row matched a post-repair status and was marked confirmed.
- **Candidate/promote/replace write path** (`_upsert_opening_cache` in `app/services/eval_drain.py`): a first write for an unseen position inserts a `confirmed=false, n_sources=1` candidate; a second, agreeing result (within `OPENING_CACHE_AGREE_MAX_SCORE_DELTA=0.03` expected-score units) from a genuinely different game promotes it to `confirmed=true, n_sources=2`; a disagreeing one replaces the value and increments `disagreements`; a result from the SAME `source_game_id` (D-13) neither promotes nor disagrees; a confirmed row is immutable to both write lanes except the pre-existing pv self-heal; Sentry fires exactly once, when `disagreements` reaches 2 (D-12).
- **Confirmed-only read paths**: `eval_apply._fetch_dedup_evals` gained `.where(OpeningPositionEval.confirmed.is_(True))` — the only place the filter lives. `eval_remote._fetch_cached_opening_hashes` inherits it by delegation, with zero references to `OpeningPositionEval.confirmed` in the router (T-220-18).
- **Backfill candidacy**: `OPENING_CACHE_BACKFILL_SQL` now inserts `confirmed=false` explicitly — a one-time backfill donor is a single source, never confirmed on its own.
- **Demote escape hatch**: `scripts/opening_cache_repair.py demote --engine-version <v>` un-confirms rows recorded against a named engine version, records engine version without ever enforcing it at read time, supports `--dry-run` and `--limit`, and is deliberately NOT a `_STAGE_ORDER` member.
- **db-report Check C**: the `disagreements`/`unconfirmed` counters (Query 12b) are now unconditional output with a note that a large unconfirmed share right after the release is expected, not a regression.

## Task Commits

Each task was committed atomically (RED/GREEN split for the two TDD tasks):

1. **Task 2: Release-2 migration** — `8dbadd027` (feat)
2. **Task 3: Candidate/promote/replace write path — RED** — `4d7839f75` (test)
3. **Task 3: Candidate/promote/replace write path — GREEN** — `f269faf55` (feat)
4. **Task 4: Confirmed-only read paths + demote — RED** — `41318baae` (test)
5. **Task 4: Confirmed-only read paths + demote — GREEN** — `9bbe8bb9a` (feat)
6. **Cross-task test fallout fix** — `26fc4e9d3` (fix) — `tests/services/test_eval_drain.py::test_cache_backed_fetch_dedup_evals` (Task 3's own file, seeded via the plain pre-CACHEFIX-08 helper) started failing once Task 4's confirmed filter landed; switched it to seed a confirmed row.

_Task 1 (checkpoint:decision) was pre-resolved by the operator via the continuation dispatch before this execution began — see `<continuation_state>` in the dispatch prompt. No commit for it in this plan's range._

## Files Created/Modified

- `alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py` — the release-2 migration (seven columns, `MARK_CONFIRMED_SQL`, keyset-walk batching)
- `app/models/opening_position_eval.py` — seven new columns, docstring drops the false "Immutable" claim, D-13 Assumption Delta for the FK-free `source_game_id`
- `app/services/eval_drain.py` — `OPENING_CACHE_AGREE_MAX_SCORE_DELTA`, `_cache_values_agree`, `_partition_cache_writes`/`_apply_cache_writes` + four write helpers, `_capture_opening_cache_disagreement`, memoized `_get_cached_engine_version`, `OPENING_CACHE_BACKFILL_SQL` gains `confirmed=false`
- `app/services/eval_apply.py` — `_fetch_dedup_evals` confirmed filter; `apply_full_eval` threads `game_id` through as `source_game_id`
- `scripts/opening_cache_repair.py` — `run_demote` + `_add_demote_subparser` + dispatch wiring
- `.claude/skills/db-report/SKILL.md` — Check C's Query 12b promoted to unconditional
- `tests/models/test_opening_cache_audit_models.py` — `TestMigrationMarking` (2 tests)
- `tests/services/test_eval_drain.py` — `TestOpeningEvalCacheWrite` extended to 39 tests; one `TestOpeningEvalCacheRead` test updated for the confirmed filter
- `tests/services/test_full_eval_drain.py` — 3 gate tests taught to confirm their seeded row, 1 new reverse test, `_confirm_cache_row` helper
- `tests/test_eval_worker_endpoints.py` — 1 new confirmed_only test, 2 existing tests updated, `_insert_opening_cache`/`_insert_opening_cache_with_pv` gain a `confirmed=` keyword (default True)
- `tests/scripts/test_opening_cache_repair.py` — `TestDemote` (4 tests); NOT in the plan's Task 4 `<files>` list despite the action text explicitly requiring tests there (see Deviations)

## Decisions Made

See `key-decisions` in the frontmatter. Notably: the checkpoint's `proceed` option was already decided by the operator before this dispatch; `OPENING_CACHE_AGREE_MAX_SCORE_DELTA` is fixed at 0.03 per the 220-06 calibration; and only 3 of the plan's referenced "six gate tests" needed code changes (the rest were unaffected by the confirmed filter, which the SUMMARY explains rather than silently padding the count).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `gsd_run check tdd-red-evidence` cannot classify a pytest RED run**
- **Found during:** Task 3's RED phase
- **Issue:** The verb's parser (`parseNodeTestSummary`/`tapFailedTestNames` in `gsd-core/bin/lib/prohibition-enforcement.cjs`) is hardcoded to Node's `--test` TAP output (`# tests N`, `# pass N`, `not ok N - <name>`); pytest's `-q` output has none of those markers. Running the tool against a genuine, correctly-targeted pytest RED run returns `INVALID_RED (zero_tests_discovered)` regardless of the actual test outcome — a tooling-format gap, not a defect in the RED evidence itself.
- **Fix:** Verified RED manually instead: reverted the implementation-only diff (`git checkout --`), ran the target tests, confirmed each failed for the correct reason (TypeError for a missing new parameter, AttributeError for a not-yet-defined module constant/function, or file-level ImportError for a not-yet-written symbol imported at module scope), confirmed the surrounding tests in the same file kept passing (ruling out a fixture/import crash), then restored the implementation via `git apply` and re-verified GREEN.
- **Files affected:** none (process-only; documented here and in the RED commit messages)
- **Verification:** pytest output captured in the RED commit messages (`4d7839f75`, `41318baae`)
- **Impact:** No code impact. This is a standing gap for any Python/pytest GSD project using `check tdd-red-evidence`; worth flagging upstream (out of this phase's scope — `gsd-core` is not a FlawChess file).

**2. [Rule 3 - Blocking] Plan's Task 4 `<files>` list omitted `tests/scripts/test_opening_cache_repair.py`**
- **Found during:** Task 4
- **Issue:** Task 4's frontmatter `<files>` block lists `app/services/eval_apply.py, app/services/eval_drain.py, scripts/opening_cache_repair.py, .claude/skills/db-report/SKILL.md, tests/services/test_full_eval_drain.py, tests/test_eval_worker_endpoints.py` — but the action text and acceptance criteria explicitly require `-k demote` tests in `tests/scripts/test_opening_cache_repair.py`, which cannot be satisfied without editing that file.
- **Fix:** Added `TestDemote` (4 tests) to `tests/scripts/test_opening_cache_repair.py` as required by the acceptance criteria.
- **Files affected:** `tests/scripts/test_opening_cache_repair.py`
- **Verification:** `uv run pytest tests/scripts/test_opening_cache_repair.py -x -q -k demote` — 4 tests selected, all pass
- **Committed in:** `41318baae` (RED), `9bbe8bb9a` (GREEN — no production code in this file, so it landed in the RED commit only; GREEN commit made it pass)

**3. [Rule 1 - Bug] `tests/services/test_eval_drain.py::test_cache_backed_fetch_dedup_evals` broke as fallout from Task 4's read filter**
- **Found during:** the full-suite verification pass after Task 4's GREEN commit
- **Issue:** This test (in `TestOpeningEvalCacheRead`, a class Task 3 did not touch) seeded via the plain pre-CACHEFIX-08 `_seed_opening_eval_cache` helper (no `confirmed` column set, defaults to `false`). Once Task 4's `_fetch_dedup_evals` confirmed filter landed, the seeded rows became invisible candidates and the test's inclusion assertions failed.
- **Fix:** Switched the two seeded rows to `_seed_opening_eval_cache_full(..., confirmed=True, n_sources=2)`. Left `_seed_opening_eval_cache` itself unchanged — `test_disagree_replaces_unconfirmed_candidate` (in the same file) deliberately needs its unconfirmed/legacy-row default.
- **Files affected:** `tests/services/test_eval_drain.py`
- **Verification:** `uv run pytest tests/services/test_eval_drain.py -q` (39/39) and the full backend suite (`uv run pytest -n auto -x`: 4612 passed, 19 skipped)
- **Committed in:** `26fc4e9d3`

---

**Total deviations:** 3 auto-fixed (1 blocking tooling gap worked around, 1 blocking plan-file-list omission filled, 1 bug from cross-task test fallout fixed). **Impact on plan:** All three were necessary to satisfy the plan's own acceptance criteria and the phase's `<verification>` block; none expands scope beyond CACHEFIX-08.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CACHEFIX-08 is code-complete and test-covered on dev. `requirements.ready-ids` reports it as **not yet markable complete** in `REQUIREMENTS.md`: `220-08-PLAN.md` also declares `CACHEFIX-08` in its frontmatter and has no `SUMMARY.md` yet (the shared-ID gate, #2388) — this SUMMARY intentionally does not call `requirements.mark-complete`; it will resolve automatically once 220-08 finishes.
- **Production deploy is NOT part of this plan.** The migration has been verified only on dev (82,586 rows). Before shipping to prod (2.57M rows), the operator should re-run the dev wall-clock measurement's scaling expectation against actual prod row counts, per the checkpoint's `proceed` decision — this is presumably 220-08's concern.
- `OPENING_CACHE_AGREE_MAX_SCORE_DELTA=0.03` is now load-bearing in production write-path logic; any future recalibration of `confirm_floor` (a fresh `calibrate` run) should be followed by an explicit review of whether this constant needs to move.

---
*Phase: 220-opening-eval-cache-repair-two-source-confirmation*
*Completed: 2026-09-11*

## Self-Check: PASSED

- `alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py` — FOUND on disk
- Commits `8dbadd027`, `4d7839f75`, `f269faf55`, `41318baae`, `9bbe8bb9a`, `26fc4e9d3` — all FOUND in `git log --oneline`
- All 4 tasks' acceptance criteria re-verified passing (see task commit messages for per-task command output)
- Full backend suite (`uv run pytest -n auto -x`): 4612 passed, 19 skipped
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check .`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200`: all clean
