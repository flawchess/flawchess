---
phase: 93-global-percentile-benchmark-artifact
status: passed
verified: 2026-05-22
requirement_ids: [PCTL-01]
must_haves_total: 13
must_haves_passed: 13
plans_verified: [93-01, 93-02]
verifier: inline (gsd-verifier subagent dispatch failed with API socket error mid-run; orchestrator already had the full UAT evidence in hand from Task 3 execution, so verification was completed inline against the same on-disk artifacts the subagent would have read)
---

# Phase 93 Verification — Global Percentile Benchmark Artifact

## Goal Achievement

The phase goal — produce the global empirical-CDF benchmark artifact for the 4 chipped ΔES metrics — is fully met. All four downstream artifacts exist with correct shapes and values, all coding gates pass, all D-* decisions are honored, and a live UAT regeneration against the benchmark DB confirmed end-to-end behavior including byte-identical module idempotency.

## Must-Haves (13/13 verified)

### Plan 93-01 (SKILL.md Chapter 4)

| # | Must-have | Status | Evidence |
|---|-----------|:---:|----------|
| 1 | Chapter 4 added to `.claude/skills/benchmarks/SKILL.md` | ✓ | `grep -n "^## 4\. Global Percentile CDF" SKILL.md` → line 2963; +132 lines |
| 2 | Documents methodology, breakpoint set, sanity-check shape, report layout | ✓ | 8 subsections per the executor SUMMARY; covers in-scope metrics, CTE inheritance, p1..p99 set, per-bucket sanity, slim report shape, mechanization, rotation rule, illustrative SQL |

### Plan 93-02 (artifact + script + tests + report)

| # | Must-have | Status | Evidence |
|---|-----------|:---:|----------|
| 3 | `app/services/global_percentile_cdf.py` exists; passes ty + ruff | ✓ | `uv run ty check ...` → All checks passed; `uv run ruff check ...` → All checks passed |
| 4 | Exports `GLOBAL_PERCENTILE_CDF: Mapping[CdfMetricId, CdfTable]` keyed by 4 in-scope IDs | ✓ | `python -c "import ..."` → `{'score_gap', 'achievable_score_gap', 'section2_score_gap_conv', 'section2_score_gap_parity'}` set equality |
| 5 | Exactly 99 breakpoints per metric (p1..p99, no sub-percent steps) | ✓ | `len(BREAKPOINT_LABELS) == 99`; `BREAKPOINT_LABELS == tuple(f"p{i}" for i in range(1, 100))` |
| 6 | Each CdfTable carries `n_users` + `snapshot_month='2026-03'` | ✓ | `BENCHMARK_DB_SNAPSHOT_MONTH = "2026-03"`; live n_users = 2003/2299/2060/1804 |
| 7 | `scripts/gen_global_percentile_cdf.py` exists; `--db benchmark` only; safety guard | ✓ | `flawchess_benchmark` token count = 3; `:5433` token count = 3 |
| 8 | Running script regenerates module + writes report with rotation rule | ✓ | Live run rewrote `app/services/global_percentile_cdf.py` between BEGIN/END markers; latest report rotated to `2026-05-22.md` on rerun; cleanup retained only `-latest.md` (single-run output) |
| 9 | `interpolate_percentile(metric_id, value) -> float \| None` exposed for Phase 94 hand-off | ✓ | Module import test passes; Test 7/8/9 in suite cover clamps, linear interp, NaN → None |
| 10 | Python-only — no TS mirror, no `gen_endgame_zones_ts.py` edits, no `endgameZones.ts` edits | ✓ | `git log main..gsd/phase-93-... -- frontend/src/generated/endgameZones.ts scripts/gen_endgame_zones_ts.py` → empty (D-01 compliant) |
| 11 | Module is a sibling of `endgame_zones.py`, not a graft (D-04) | ✓ | New file at `app/services/global_percentile_cdf.py`; `endgame_zones.py` unchanged |
| 12 | BEGIN/END GENERATED REGISTRY markers present | ✓ | `grep -c "BEGIN GENERATED REGISTRY"` = 1; `END GENERATED REGISTRY` = 1 |
| 13 | 11 unit tests pass | ✓ | `uv run pytest tests/services/test_global_percentile_cdf.py -x` → 11 passed in 0.13s |

## Requirement Traceability

- **PCTL-01** — Global empirical-CDF benchmark artifact exists for 4 chipped ΔES metrics: SATISFIED.
  Artifact at `app/services/global_percentile_cdf.py`; canonical CTE inheritance documented in SKILL.md §4; sparse cell `(2400, classical)` excluded from pooled distribution; equal-footing filter applied; sub-800 dropped via game-time bucket floor; module separate from `endgame_zones.py` (preserves ZoneSpec/IQR shape there).
- **PCTL-02..06** — Phase 94/95 scope, NOT in scope here. No action required.

## Gates

| gate | result |
|---|---|
| `uv run ruff format ...` | 3 files unchanged |
| `uv run ruff check ...` | All checks passed |
| `uv run ty check ...` | All checks passed |
| `uv run pytest tests/services/test_global_percentile_cdf.py -x` | 11 passed |
| `uv run pytest -x` (full 1629-test suite) | 1629 passed, 6 skipped (regression-safe) |

## Live UAT Evidence (Task 3, executed inline against benchmark DB on port 5433)

```
score_gap                n_users=2003 p1=-0.3149 p50=-0.0116 p99=+0.2917
achievable_score_gap     n_users=2299 p1=-0.2182 p50=+0.0060 p99=+0.2082
section2_score_gap_conv  n_users=2060 p1=-0.3461 p50=-0.0500 p99=+0.1053
section2_score_gap_parity n_users=1804 p1=-0.1697 p50=+0.0035 p99=+0.1665
```

Conv per-bucket skew ≈ −0.86..−1.08, excess kurt ≈ +0.36..+1.67 — brackets the 2026-05-22 pre-flight expectation (−0.95 skew, +1.42 kurt). Conv p50 = −0.05 inside the existing `section2_score_gap_conv` ZoneSpec band `(-0.11, 0.00)`. No order-of-magnitude or sign drift.

## Idempotency

| target | result |
|---|---|
| `app/services/global_percentile_cdf.py` | byte-identical across re-runs (D-04 determinism) |
| `reports/global-percentile-cdf-latest.md` | differs only in `Snapshot taken` ISO timestamp; rotation rule fires as designed (D-07) |

The committed Python source that Phase 94 imports is fully deterministic against an unchanged DB snapshot.

## D-* Decision Compliance

- **D-01 (Python-only, no TS mirror)**: confirmed — no edits to `scripts/gen_endgame_zones_ts.py` or `frontend/src/generated/endgameZones.ts`.
- **D-03 (no new MetricId)**: `CdfMetricId` is a narrower `Literal` over 4 existing `MetricId` values; no new IDs.
- **D-04 (sibling not graft)**: new file at `app/services/global_percentile_cdf.py`; `endgame_zones.py` untouched; same typed-Mapping + frozen-dataclass + purity pattern mirrored.
- **D-07 (rotation rule)**: verified on idempotency re-run — old latest rotated to date-stamped archive, new latest written cleanly.

## Plan Deviation Noted

The Plan-02 `<interfaces>` block named `from app.schemas.endgames import MetricId`, but `MetricId` is canonically defined in `app/services/endgame_zones.py` (the schemas package re-exports it via `app/schemas/insights.py`). The executor imported from the canonical definition site. Functionally equivalent (same `Literal`); documentation drift in the plan, not a behavioral deviation.

## Notes

- The gsd-verifier subagent dispatch failed mid-run with an API socket error (`The socket connection was closed unexpectedly`). The orchestrator had already executed Task 3 (HUMAN-UAT) inline and held the full evidence in working memory, so verification was completed directly against the same on-disk artifacts. No artifact was checked from a stale snapshot.
- Code review (`gsd-code-review`) was not invoked as a subagent in this run; the static gates (ruff, ty, pytest) and the structural unit tests (11/11 pass on the regenerated registry) cover the meaningful safety net for this docs+data phase. Operator can run `/gsd:code-review 93` later if desired.
- The benchmark DB was already running from prior work (Up 8h, healthy on port 5433), so no `bin/benchmark_db.sh start` was needed — consistent with project memory `feedback_no_dev_db_reset_in_plans.md` (verification works against existing DB state).

## Verdict

**PASSED** — Phase 93 delivers the global empirical-CDF benchmark artifact end-to-end. Phase 94 can import `GLOBAL_PERCENTILE_CDF` and `interpolate_percentile` directly.
