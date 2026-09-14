---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 04
subsystem: database
tags: [postgresql, sqlalchemy, stockfish, opening-cache-repair, reporting, sanity-checks]

# Dependency graph
requires:
  - phase: 220-01
    provides: audit tables (opening_cache_audit, opening_cache_repair_rows,
      opening_cache_repair_games, opening_cache_repair_progress), the stage
      state machine (_stage_gate/_STAGE_ORDER), seed/calibrate/screen/orphans
  - phase: 220-03
    provides: confirm/propagate/rederive stages and their audit-row columns
      (delta_cp, best_move_replaced/pv_replaced, flaws_before/after_*,
      drill_items_pruned, herrings_touched, white/black_accuracy_before/after,
      white/black_acpl_before/after) that report's sections 1-5 read directly
provides:
  - "`report`: a read-only stage rendering opening_cache_audit and its
    companion tables into a committed, PII-free, dated markdown trail under
    reports/opening-cache-repair/, with a verification block restating the
    lichess cross-check, the delta-histogram-vs-lichess-internal-IQR-control
    (the phase's PRIMARY acceptance signal), the opening bounce rate,
    calibration floors, and the game-2356581/9-named-hash acceptance fixture
    next to their recorded 2026-09-09 baselines. --partial runs any time,
    skipping the rederive_finished_at gate."
  - "`legacy-sample`: D-07's 200-legacy/50-control cohort walk across ALL
    plies at depth 15, through the SAME per-row disagreement test `screen`
    uses, gated on calibrate_finished_at/screen_floor only. Prints a
    greppable BUILD/NO BUILD verdict per a pre-committed rule with both
    cohorts' rates, numerators and denominators."
affects: [220-05, 220-06]

# Actuals (#2632)
actuals:
  tokens: 17640
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Report builder split into one _report_section_* helper per section
      (9 sections), each independently unit-testable and each staying under
      the nesting-depth-4/complexity gates ruff enforces project-wide even
      though scripts/ is exempt from check_function_size.py's LOC gate."
    - "Dedicated gate bypassing the generic _STAGE_ORDER walk: legacy-sample
      checks calibrate_finished_at/screen_floor directly rather than calling
      _stage_gate(session, 'legacy_sample'), because the generic backward
      walk would find 'report' (now tracked, unlike orphans) as the nearest
      predecessor and incorrectly require report_finished_at -- D-07's real
      dependency is the calibration floor, not the report having run."
    - "Python-side histogram bucketing (_bucket_by_bands) mirrors PostgreSQL's
      own width_bucket(x, ARRAY[...]) semantics exactly, so the same band
      boundaries and labels are reused for the confirmed_bad delta_cp
      histogram (section 1, no control) and the lichess-median-vs-IQR
      histogram (section 7, WITH a control) without duplicating logic."

key-files:
  created: []
  modified:
    - scripts/opening_cache_repair.py
    - tests/scripts/test_opening_cache_repair.py

key-decisions:
  - "write_repair_report(session_maker, *, now, out_dir, db) takes an
    injectable session_maker (not a raw db_url) as its first parameter,
    consistent with every other stage in this script -- the plan's own
    'Artifacts this phase produces' table names the signature
    write_repair_report(db_url, now, out_dir), but every existing stage in
    this script (seed/calibrate/screen/confirm/propagate/rederive) takes an
    injectable session_maker, and a test needs to point the report at the
    per-worker test database, which only the session_maker parameter (not a
    bare db_url string) makes possible without duplicating _resolve_session_maker
    inside the report writer itself."
  - "legacy-sample's cohort sampling uses ORDER BY md5(games.id::text) LIMIT n
    (not ORDER BY id) -- a pure function of id, so a re-run against
    unchanged data selects the identical set (genuinely deterministic, per
    the plan's own 'pick one and state it' choice), while spreading the
    sample across the whole eligible population rather than only its
    earliest-inserted rows."
  - "Report section 4's user-facing header text says 'numeric only' rather
    than the more natural 'no email/username' phrasing, because the report's
    own generated markdown must never contain the literal tokens 'email' or
    'username' anywhere -- test_report_no_pii asserts their absence in the
    rendered file, so even a truthful disclaimer using those words would
    self-trip the PII check. The prohibition lives in the source-code comment
    instead."
  - "legacy-sample's per-row disagreement test treats a delta strictly
    greater than screen_floor as disagreeing (>, not >=) -- an exact match
    to screen_floor counts as agreeing, mirroring screen's own inclusive
    <= boundary (CACHEFIX-03) so both stages share one noise model."

patterns-established:
  - "Two histogram flavors from one bucketing primitive: _bucket_by_bands
    takes a plain value list and band tuple (no SQL, no control series),
    used both for a single-series histogram (section 1's confirmed_bad
    delta_cp) and, via a separate SQL query pairing n_cache/n_ctrl per
    bucket, for the two-series control comparison (section 7) -- the Python
    bucketing function itself never needs to know which case it's in."
  - "Decision-rule verdict as two literal greppable constants
    (_LEGACY_DECISION_BUILD / _LEGACY_DECISION_NO_BUILD) rather than an
    f-string assembling 'BUILD'/'NO BUILD' at runtime -- both full strings
    are physically present in the source, so a static grep for
    LEGACY-COHORT-DECISION always finds both possible outcomes regardless
    of which one a given run actually prints."

requirements-completed: []
# CACHEFIX-07 and CACHEFIX-10 are ALSO declared by 220-06-PLAN.md
# (which runs the prod acceptance queries and the real prod legacy-sample
# pass). Per the shared-ID gate (#2388), neither is marked Complete in
# REQUIREMENTS.md until 220-06 also finishes -- this plan implements both
# subcommands and proves them against dev/test fixtures + a real dev
# --partial report run; the prod run and acceptance evidence are 220-06's
# job.

coverage:
  - id: D1
    description: "report stage: read-only render of opening_cache_audit +
      companion tables into a dated, committed, PII-free markdown file under
      reports/opening-cache-repair/; --partial skips the rederive_finished_at
      gate for an any-time snapshot; nine sections including a verification
      block restating every observed value next to its 2026-09-09 baseline"
    requirement: CACHEFIX-07
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestReport (8 tests:
          read_only, empty, top30_order, no_pii, filename, partial_skips_gate,
          gate_without_partial)"
        status: pass
      - kind: other
        ref: "uv run python scripts/opening_cache_repair.py report --db dev --partial
          (real dev DB run; produced a well-formed, human-readable report,
          committed as reports/opening-cache-repair/opening-cache-repair-2026-09-09.md)"
        status: pass
    human_judgment: false
  - id: D2
    description: "legacy-sample stage: D-07's 200-legacy/50-control cohort
      walk across ALL plies at depth 15, gated on calibrate_finished_at/
      screen_floor only, per-row disagreement test identical to screen's own,
      greppable BUILD/NO BUILD verdict per the stated rule (ratio > 2x AND
      excess >= 1.0pp), fewer-than-requested-uses-all-available, zero-eligible
      exits non-zero with no verdict, read-only (writes nothing but its own
      progress timestamps)"
    requirement: CACHEFIX-10
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestLegacySample (9
          tests: gate, decision_rule x4 corners, boundary, short_cohort,
          empty_cohort, read_only)"
        status: pass
    human_judgment: false

# Metrics
duration: ~70min
completed: 2026-09-09
status: complete
---

# Phase 220 Plan 04: Repair Report & Legacy-Cohort Sample Summary

**`report` turns the audit tables into a committed, baseline-anchored markdown trail (the residual delta histogram vs. the lichess-internal IQR control is the phase's primary acceptance signal), and `legacy-sample` measures the pre-2026-06-18 cohort's disagreement rate beyond ply 20 against a like-for-like control, emitting a pre-committed BUILD/NO-BUILD verdict.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-09T21:40:00Z (approximate)
- **Completed:** 2026-09-09T22:50:08Z
- **Tasks:** 2
- **Files modified:** 2 (0 created), plus one generated report artifact committed

## Accomplishments

- `report`: a read-only stage (`write_repair_report`) that renders
  `opening_cache_audit` and its companion tables into
  `reports/opening-cache-repair/opening-cache-repair-YYYY-MM-DD.md`, built
  as nine independent `_report_section_*` helpers: (1) cache status
  breakdown with `pending` split into "no carrier" (orphan candidate) vs
  "has a carrier" (walk cut short), plus the `confirmed_bad` `delta_cp`
  histogram; (2) top-30 `confirmed_bad` positions by carrier count, a total
  order (carrier count DESC, `full_hash` ASC) with the reconstructed SAN
  line; (3) positions rewritten, `best_move`/`pv` replacement counted
  SEPARATELY; (4) games affected by platform and by user id (numeric only,
  no email/username anywhere in the output); (5) flaws before/after,
  spurious-flaws-removed, drill/herring counters, mean accuracy/ACPL shift;
  (6) the two provenance leaks plan 220-02 closed; (7) the verification
  block -- lichess cross-check, the delta histogram vs. the
  lichess-internal IQR control (labelled the **PRIMARY ACCEPTANCE SIGNAL**),
  the opening bounce rate (explicitly a coarse sanity check only), the
  measured calibration floors, and the game-2356581/9-named-hash acceptance
  fixture -- each restated next to its recorded 2026-09-09 prod baseline;
  (8) per-stage timings in canonical stage order; (9) provenance (`--db`
  target, generation timestamp, git short SHA, `engine_version`).
  `--partial` skips the `rederive_finished_at` gate so the stage can run at
  any point during a multi-day repair.
- `legacy-sample` (D-07/CACHEFIX-10): samples 200 games with
  `full_evals_completed_at < 2026-06-18` (deterministically, via
  `ORDER BY md5(games.id::text)`) and a like-for-like 50-game control with
  `full_evals_completed_at >= 2026-08-20`, walks ALL plies of every sampled
  game (not just the opening region) through the SAME hash-assertion +
  depth-15 + post-move-shift-aware disagreement test `screen` uses, and
  prints both cohorts' rates split at ply 20 with numerators/denominators
  plus one of two greppable verdict strings
  (`LEGACY-COHORT-DECISION: BUILD screen --legacy-cohort` /
  `LEGACY-COHORT-DECISION: NO BUILD`) per the rule `legacy_rate_ply_gt_20 >
  2 * control_rate_ply_gt_20 AND (legacy_rate - control_rate) >= 1.0pp`.
  Gated on `calibrate_finished_at`/`screen_floor` directly (not the generic
  `_STAGE_ORDER` walk, which would incorrectly require `report_finished_at`
  now that `report` is a tracked stage). Writes nothing but its own
  progress timestamps; `--append-report` appends the decision block to the
  dated report file when one exists.
- Verified `report --db dev --partial` against the real dev database: the
  generated file is well-formed and human-readable end to end, matches
  RESEARCH.md's independently-measured dev baseline (lichess cross-check
  2,137/0), and is committed as the first entry in the audit trail.

## Task Commits

Both tasks landed in one commit -- see Deviations below for why.

1. **Tasks 1-2: `report` + `legacy-sample` stages (CACHEFIX-07/CACHEFIX-10)**
   -- `9ba09e0fc` (feat)

**Plan metadata:** committed alongside this SUMMARY

## Files Created/Modified

- `scripts/opening_cache_repair.py` -- `report`/`legacy-sample` stages, their
  CLI subparsers/dispatch entries, and every private helper each needs
  (1,129 lines added)
- `tests/scripts/test_opening_cache_repair.py` -- `TestReport` (8 tests),
  `TestLegacySample` (9 tests) -- 17 new tests, 355 lines added
- `reports/opening-cache-repair/opening-cache-repair-2026-09-09.md` --
  the first committed report, generated by a real `--db dev --partial` run
  against the (pre-repair, mostly-empty) dev audit tables

## Decisions Made

- **`write_repair_report` takes an injectable `session_maker`, not a raw
  `db_url`** -- consistent with every other stage in this script and
  required for the test suite to point the report at the per-worker test
  database.
- **legacy-sample's cohort sampling is `ORDER BY md5(games.id::text)`**, a
  pure function of `id` so a re-run against unchanged data selects the
  identical set, spreading the sample across the whole eligible population
  rather than only its earliest rows.
- **Report section 4's header avoids the literal words "email"/"username"**
  even in a truthful disclaimer, because `test_report_no_pii` asserts those
  tokens' absence from the rendered file itself -- the prohibition lives in
  a source-code comment instead of report prose.
- **legacy-sample's disagreement test is strictly `>` `screen_floor`** (not
  `>=`), matching `screen`'s own inclusive `<=` "clean" boundary so both
  stages share one noise model.

## Deviations from Plan

### Process deviation (not a Rule 1-4 auto-fix, documented for transparency)

**Tasks 1 (`report`) and 2 (`legacy-sample`) committed together, not as 2
separate commits.** Both tasks were implemented as one continuous authoring
pass into `scripts/opening_cache_repair.py`: task 2's CLI wiring
(`_add_legacy_sample_subparser`, the `elif args.command == "legacy-sample"`
dispatch branch) was added in the same edit as task 1's equivalent CLI
wiring, and the test-file edit appended both `TestReport` and
`TestLegacySample` in a single pass. Splitting this into 2 clean git commits
after the fact would have required either temporarily removing task 2's code
to commit an artificial "report-only" intermediate state with zero
functional benefit, or manual patch-hunk surgery across a ~1,100-line
addition with no reliable automated split point at the CLI-wiring layer.
Each task's own acceptance criteria (grep-based symbol/constant checks,
`-k report`/`-k legacy_sample` test-selection counts: 8 and 9 respectively,
both clearing their "at least 5"/"at least 6" bars) were independently
verified to pass before moving to the next task, so the per-task coverage
table above still gives full, individually-verified attribution -- only the
git history granularity is coarser than 1:1. This mirrors the identical
situation and resolution documented in 220-03-SUMMARY.md.

---

**Total deviations:** 0 auto-fixed (1 process deviation, commit granularity
only -- no code, test, or behavior change).
**Impact on plan:** None on functionality or verification; both tasks'
acceptance criteria pass independently as designed.

## Issues Encountered

- **ty flagged four `dict(rows)` constructions** where `rows` is a
  SQLAlchemy `Row` sequence from `.all()` -- `dict()`'s overloads don't
  statically resolve a `Sequence[Row[tuple[K, V]]]` to
  `Iterable[tuple[K, V]]`. Fixed by replacing each with an explicit dict
  comprehension (`{k: v for k, v in rows}`), which `ty` resolves cleanly.
  No behavior change.
- **A generator expression containing `await` inside `tuple(...)`**
  (`_report_read_only_table_counts`'s first draft) is implicitly an async
  generator under PEP 525, which `tuple()` cannot consume synchronously --
  `ty` caught this before it became a runtime `TypeError`. Fixed with an
  explicit `async with` + loop appending to a list, then `tuple(list)`.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

Ready for plan 05 (release-2 provenance/hardening work, if scheduled next)
and plan 06 (prod acceptance: the real `--db prod` repair run, the 14
CACHEFIX-11 acceptance queries, and the real `legacy-sample --db prod`
pass that resolves the CACHEFIX-10 build/no-build verdict for real).

Notes for downstream plans:

- **Plan 06** runs `legacy-sample --db prod` (this plan only proves the
  subcommand against dev/test fixtures and a synthetic decision-rule table)
  and records the real verdict, whichever way it falls -- per D-07 and this
  plan's own explicit non-scope ("`screen --legacy-cohort` is NOT built in
  this plan").
- **Plan 06** also runs `report --db prod` (non-partial, after the full
  pipeline finishes) for the canonical acceptance report; this plan's
  committed dev report is a pre-repair, all-zero scaffold demonstrating the
  stage renders correctly end to end, not the phase's acceptance evidence.
- **CACHEFIX-07 and CACHEFIX-10 are NOT marked Complete in REQUIREMENTS.md
  by this plan** -- both are also declared by `220-06-PLAN.md`'s
  frontmatter, and the shared-ID gate (#2388) withholds `Complete` until
  every plan declaring an ID has its own SUMMARY. Plan 06 finishing will
  flip both.
- No blockers.

---
*Phase: 220-opening-eval-cache-repair-two-source-confirmation*
*Completed: 2026-09-09*

## Self-Check: PASSED

- `scripts/opening_cache_repair.py` confirmed present on disk with the expected changes.
- `tests/scripts/test_opening_cache_repair.py` confirmed present on disk with the expected changes.
- `reports/opening-cache-repair/opening-cache-repair-2026-09-09.md` confirmed present on disk.
- Commit `9ba09e0fc` confirmed in `git log`.
- `uv run pytest tests/scripts/test_opening_cache_repair.py -q` -- 56 passed.
- `uv run pytest tests/scripts/test_opening_cache_repair.py -x -q -k report` -- 8 selected, all pass (>= 5 required).
- `uv run pytest tests/scripts/test_opening_cache_repair.py -x -q -k legacy_sample` -- 9 selected, all pass (>= 6 required).
- `uv run pytest -n auto -x -q -p no:warnings` (full backend suite) -- 4589 passed, 19 skipped, 0 failed.
- `uv run ty check app/ tests/ scripts/` -- all checks passed.
- `uv run ruff check .` -- all checks passed.
- `uv run ruff format --check scripts/opening_cache_repair.py tests/scripts/test_opening_cache_repair.py` -- both clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` -- 1031 functions scanned, no breaches.
- All 9 named hashes, `LEGACY-COHORT-DECISION` (2 occurrences), `LEGACY_BUILD_RATIO`/`LEGACY_BUILD_MIN_EXCESS_PP` (8 occurrences), `write_repair_report` (1 definition), and `opening-cache-repair` (4 occurrences) grep-based acceptance criteria verified directly, all pass.
- `report --db dev --partial` re-verified readable end to end (committed file reviewed in full).
