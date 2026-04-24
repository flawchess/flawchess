---
phase: 63-findings-pipeline-zone-wiring
plan: 05
subsystem: testing
tags: [python, pytest, async-mock, insights, endgame, test-suite, find-01, find-03, find-04, find-05]

# Dependency graph
requires:
  - "63-01 — endgame_zones.py registry + assign_zone / sample_quality helpers + named thresholds"
  - "63-03 — insights.py schemas: FilterContext, SubsectionFinding, EndgameTabFindings, FlagId"
  - "63-04 — insights_service.py: compute_findings + private helpers (_compute_trend, _compute_flags, _compute_hash, _empty_finding)"
provides:
  - "tests/services/test_insights_service.py — 45 tests across 5 classes covering FIND-01, FIND-03, FIND-04, FIND-05 + empty-window convention"
  - "Regression anchor for Phase 65 (LLM cache invariant: findings_hash stable across sessions)"
  - "Regression anchor for Phase 67 (validation phase builds on these invariants)"
affects:
  - "Phase 65 (LLM endpoint): _compute_hash stability is verified; prompt-assembly can rely on the 64-char lowercase-hex contract"
  - "Phase 67 (regression test): four cross-section flags are pinned with true/false branch coverage; trend gate's count-fail and ratio-fail paths are locked"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AsyncMock + patch.object pattern for mocking get_endgame_overview at the module import seam in insights_service — asserts await_count==2 with ordered recency kwargs"
    - "EndgameOverviewResponse.model_construct() bypass for minimal-valid synthetic instances when the test cares about the CALL pattern, not the composed-body shape"
    - "Registry-constant-as-assertion pattern: every flag/trend threshold test references NEUTRAL_PCT_THRESHOLD / NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD / TREND_MIN_WEEKLY_POINTS / TREND_MIN_SLOPE_VOL_RATIO — a registry retuning will not cascade into test-value maintenance"
    - "inspect.getsource() + substring assertion for FIND-01 layering guard (no `from app.repositories`, no `asyncio.gather`)"
    - "typing.cast(Literal, str) pattern in _make_finding factory — keeps the helper's call-site terse while preserving runtime Literal-validation via Pydantic"

key-files:
  created:
    - "tests/services/test_insights_service.py (653 lines, 45 tests, 5 classes)"
  modified: []

key-decisions:
  - "Declining/improving trend tests use explicit `min_slope_vol_ratio=0.1` override rather than trying to construct a linear series that passes the default 0.5 gate. A pure linear series of length n >= 20 has a FIXED ratio = sqrt(12/(n^2-1)) ~ 0.14 at n=25 — it is mathematically impossible to pass ratio >= 0.5 with a pure arithmetic progression at gate-clearing sample sizes. 63-04 SUMMARY confirmed this design by noting the rising [0..24] case returns n_a by design. The test demonstrates that WHEN the ratio gate passes, the improving/declining branch fires correctly — the REAL 0.5 gate's count-fail and ratio-fail branches are covered by `test_count_fail_returns_n_a` and `test_ratio_fail_returns_n_a` at their natural thresholds."
  - "Deferred seeded_user integration test. The plan's TestComputeFindingsIntegration section listed optional end-to-end hash-stability tests using the Phase 61 fixture and a monkeypatched datetime.date.today. Two reasons to skip for 63-05: (a) compute_findings uses `datetime.datetime.now(datetime.UTC)`, not `date.today()` — the monkeypatch target in the plan was wrong; (b) the synthetic TestComputeHash class already proves cross-invocation determinism, and Phase 65's LLM endpoint provides the natural end-to-end seam for FIND-05. The planner explicitly marked this as nice-to-have: 'rely on TestComputeHash for FIND-05 coverage'. SUMMARY documents the pivot."
  - "No integration test against seeded_user. Plan text suggested using the Phase 61 fixture for two-window validation and hash stability with real DB data; the infrastructure setup cost (session factory import + monkeypatch plumbing) is non-trivial and the synthetic coverage is already tight. Deferred to Phase 65 where the LLM endpoint naturally exposes the hash in the response body."
  - "Used `EndgameOverviewResponse.model_construct()` for layering-test mocks instead of building a fully-valid synthetic instance. model_construct skips Pydantic validation, so the mock returns an 'empty shell' response — this means compute_findings's subsection builders will likely raise AttributeError deep in the call chain. We wrap each await in `try/except Exception: pass` in the test and still assert `mocked.await_count == 2` — the invariant we care about (two sequential calls to get_endgame_overview, ordered recency kwargs) is observable via the mock's call history regardless of downstream failures."

patterns-established:
  - "Class-per-concern test organization: TestComputeTrend (8 tests), TestComputeFlags (15 tests), TestComputeHash (8 tests), TestEmptyFinding (8 tests), TestComputeFindingsLayering (6 tests) = 45 total."
  - "Registry constants as test thresholds: no numeric literals for 10.0 / 100 / 20 / 0.5 in assertions — all flow from `from app.services.endgame_zones import ...`. A future calibration edit to the registry (e.g. NEUTRAL_PCT_THRESHOLD = 8) propagates to tests automatically without code changes."
  - "Helper factory `_make_finding` with keyword-only defaults. Callers specify the semantically-load-bearing fields (subsection_id, metric, value, zone) and optionally dimension/window/trend; non-load-bearing fields (sample_size, sample_quality, is_headline_eligible, weekly_points_in_window, parent_subsection_id) carry sensible test defaults."

requirements-completed:
  - FIND-01
  - FIND-03
  - FIND-04
  - FIND-05

# Metrics
duration: ~15min
completed: 2026-04-20
---

# Phase 63 Plan 05: Insights Service Test Suite Summary

**45 deterministic unit tests across 5 classes pin the `compute_findings` contract: FIND-01 layering (no repositories, no gather, two sequential get_endgame_overview awaits with recency=None / recency="3months"), FIND-03 four cross-section flags with true+false branches, FIND-04 trend gate (count-fail, ratio-fail, both-pass, stable), FIND-05 hash stability (64-char hex, as_of/findings_hash exclusion, dict-order invariance, NaN safety). Runtime 0.13s — well under the 30s VALIDATION.md gate.**

## Performance

- **Started:** 2026-04-20T19:40Z (approx)
- **Completed:** 2026-04-20T19:55Z (approx)
- **Duration:** ~15 min
- **Tasks:** 1
- **Files created:** 1 (`tests/services/test_insights_service.py`)
- **Files modified:** 0

## Test Count Per Class

| Class                          | Test Count | Requirement Coverage           |
| ------------------------------ | ---------- | ------------------------------ |
| TestComputeTrend               | 8          | FIND-04 (trend gate)           |
| TestComputeFlags               | 15         | FIND-03 (four flags × branches)|
| TestComputeHash                | 8          | FIND-05 (hash stability)       |
| TestEmptyFinding               | 8          | (empty-window convention)      |
| TestComputeFindingsLayering    | 6          | FIND-01 (service-only, no gather, two-call pattern) |
| **Total**                      | **45**     |                                |

## Runtime

- `uv run pytest tests/services/test_insights_service.py -x -v` — **45 passed in 0.13s** (wall-clock ~1.6s including interpreter startup)
- VALIDATION.md sampling-rate requirement: max feedback latency 30s — satisfied with 50x headroom.

## Task Commits

1. **Task 1: Test suite** — `0a1872d` (test)

## Files Created/Modified

- `tests/services/test_insights_service.py` (653 lines) — covers FIND-01, FIND-03, FIND-04, FIND-05 across 5 classes; uses `AsyncMock + patch.object` for the layering seam; all thresholds flow from `app.services.endgame_zones` constants.

## FIND Requirement Coverage Map

| Requirement | Test(s) |
|-------------|---------|
| FIND-01 (layering) | `test_no_repository_import_in_module_source`, `test_no_asyncio_gather_in_module_source`, `test_calls_get_endgame_overview_twice`, `test_first_call_uses_recency_none`, `test_second_call_uses_recency_3months`, `test_color_is_not_forwarded_to_endgame_service` |
| FIND-03 (flags) | Each of 4 flags has a true-branch + false-branch test (8 core tests), plus NaN guards (3), missing-finding guard (1), last_3mo exclusion (1), negative-side ELO divergence (1), weak-zone baseline_lift (1), strong-zone baseline suppression (1) — 15 total |
| FIND-04 (trend gate) | `test_count_fail_returns_n_a`, `test_empty_series_returns_n_a`, `test_both_pass_improving`, `test_both_pass_declining`, `test_flat_series_is_stable`, `test_ratio_fail_returns_n_a`, `test_ratio_gate_references_registry_constant`, `test_count_gate_references_registry_constant` |
| FIND-05 (hash stability) | `test_hash_is_64_char_lowercase_hex`, `test_hash_excludes_as_of`, `test_hash_excludes_findings_hash_itself`, `test_hash_differs_on_finding_value_change`, `test_hash_differs_on_filter_change`, `test_hash_stable_with_nan_value`, `test_hash_stable_across_dict_insertion_order`, `test_hash_stable_across_two_invocations` |

## Decision on seeded_user Integration

**Option (b): defer end-to-end integration to Phase 65.**

Rationale:
1. The plan's suggested monkeypatch target (`datetime.date.today`) was incorrect — `compute_findings` uses `datetime.datetime.now(datetime.UTC)` (per 63-04 SUMMARY). Patching `date.today` would have zero effect on the `as_of` field, making the "same inputs → same hash" integration assertion vacuous.
2. `TestComputeHash` already proves the core FIND-05 contract (cross-invocation determinism, as_of exclusion, NaN safety, dict-order canonicalization) on synthetic Pydantic instances — the same recipe the service uses.
3. Phase 65's LLM endpoint will naturally expose `findings_hash` in its response body, giving the integration layer a proper seam. End-to-end hash equivalence across two `httpx.AsyncClient` requests against the seeded user is a more honest integration test than a direct-session compute_findings call that would otherwise duplicate the synthetic coverage.

The planner explicitly authorized this pivot: "if option (a) is not straightforward after 10 minutes of investigation, document the pivot in the 63-05-SUMMARY.md and rely on TestComputeHash for FIND-05 coverage."

## Key Decision: Trend "Improving/Declining" Tests Use min_slope_vol_ratio Override

For a pure linear series of length n, `|slope| / stdev(points)` is a FIXED, scale-invariant property:

```
ratio = sqrt(12 / (n^2 - 1))
```

Values:

| n  | ratio  |
|----|--------|
| 5  | 0.632  |
| 10 | 0.330  |
| 20 | 0.169  |
| 25 | 0.136  |

At the default count gate `n >= TREND_MIN_WEEKLY_POINTS = 20`, a pure arithmetic progression **mathematically cannot pass** the `TREND_MIN_SLOPE_VOL_RATIO = 0.5` ratio gate. The 63-04 SUMMARY confirmed this design: "rising [0..24] returns n_a by design — ratio 0.14 < 0.5 gate".

To deterministically exercise the improving / declining branch, `test_both_pass_improving` and `test_both_pass_declining` supply a permissive `min_slope_vol_ratio=0.1` override. This:

- Exercises the SAME `_compute_trend` function via its public signature argument (no private-API access).
- Proves that when the ratio gate passes, slope-sign correctly selects "improving" vs "declining".
- Keeps the default-gate coverage honest via separate `test_ratio_fail_returns_n_a` (noisy zero-slope series) and `test_count_fail_returns_n_a` (n=19) tests.

## Deviations from Plan

None auto-fixed during implementation — plan-exact execution.

**Minor pivots documented inline above:**

1. **Permissive ratio override** in the improving/declining tests (see "Key Decision" section) — the plan's sample snippet used `[float(i) for i in range(25)]` which fails the default ratio gate by design. No behaviour change to the service; the fix is in how the test exercises the branch.
2. **Deferred seeded_user integration** (see "Decision on seeded_user Integration" section) — planner explicitly authorized this pivot.
3. **One-line type annotation tweak** in `_make_finding` factory: used `cast(SampleQuality, ...)` instead of `cast("Literal['thin', 'adequate', 'rich']", ...)` — cleaner because `SampleQuality` is already imported from the schemas. Functionally equivalent.

No deviation rules invoked (no bugs found, no missing functionality discovered, no architectural changes).

## Issues Encountered

- **Pure linear series fails ratio gate.** Initial draft of the improving/declining tests used steep linear rises (e.g. `[float(i)*10 for i in range(25)]`). The test failed because `slope/stdev` is scale-invariant for linear progressions — 0.14 at n=25 regardless of magnitude. Resolved by passing `min_slope_vol_ratio=0.1` to exercise the branch, with a docstring explaining the mathematical constraint. No service-code change needed — the gate is working as designed per 63-04 SUMMARY.

## User Setup Required

None — pure backend test file, no migrations, no env vars, no external services.

## Verification

| Check | Outcome |
|-------|---------|
| `uv run pytest tests/services/test_insights_service.py -x -v` | 45 passed in 0.13s |
| `uv run pytest tests/services/ -x` | 77 passed (0 regressions in test_endgame_zones / test_endgame_zones_consistency) |
| `uv run pytest -q` (full suite) | 942 passed in 13.88s (no regressions) |
| `uv run ty check app/ tests/` | All checks passed! (project-wide) |
| `uv run ruff check .` | All checks passed! (project-wide) |
| Phase gate: `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | PHASE GATE PASSED |

## Threat Flags

None — this plan only added a test file; it introduces no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check

Verifying every claim in this SUMMARY:

- FOUND: tests/services/test_insights_service.py (653 lines, confirmed)
- FOUND: commit 0a1872d in git log ("test(63-05): add insights service test suite")
- PASS: 45 tests in TestComputeTrend (8) + TestComputeFlags (15) + TestComputeHash (8) + TestEmptyFinding (8) + TestComputeFindingsLayering (6) = 45
- PASS: `uv run pytest tests/services/test_insights_service.py -x -v` → 45 passed in 0.13s
- PASS: `uv run pytest tests/services/ -x` → 77 passed (includes this new file + 32 existing)
- PASS: `uv run pytest -q` → 942 passed in 13.88s (full project, no regressions)
- PASS: `uv run ty check app/ tests/` → All checks passed!
- PASS: `uv run ruff check .` → All checks passed!
- PASS: `scripts/gen_endgame_zones_ts.py && git diff --exit-code` → clean (phase gate green)
- PASS: Every FIND requirement (01, 03, 04, 05) has ≥1 dedicated test; requirements-completed frontmatter lists all four.

## Self-Check: PASSED

---
*Phase: 63-findings-pipeline-zone-wiring*
*Completed: 2026-04-20*
