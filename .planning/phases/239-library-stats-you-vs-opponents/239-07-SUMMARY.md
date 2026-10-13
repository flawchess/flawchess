---
phase: 239-library-stats-you-vs-opponents
plan: 07
subsystem: backend-zone-registries
tags: [zones, benchmarks, tactics, flaws]
requires: [239-02, 239-04, 239-06]
provides:
  - "TACTIC_DELTA_ZONES populated for 9 of 38 (family, side) pairs"
  - "FLAW_DELTA_ZONES verified equal to the owner-accepted values"
affects: [239-09]
key-files:
  modified:
    - app/services/flaw_delta_zones.py
    - app/services/tactic_delta_zones.py
    - tests/services/test_flaw_delta_zones.py
    - tests/services/test_tactic_delta_zones.py
    - tests/services/test_tactic_comparison_service.py
decisions:
  - "Followed ## Accepted (accept with edits): 12 flaw bands unchanged from live, 9 tactic bands as proposed, LOW_SAMPLE_MIN_FLAWS stays 40, no Elo keying"
status: complete
commits: 2
plan_head_before: 59bbd34b3c8fffb9e522c675a5b1dcecc59d0478
plan_head_after: see git log (task commit f1c4599a0, then this SUMMARY commit)
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
completed: 2026-10-13
---

# Phase 239 Plan 07: Accepted zone values into the registries Summary

The owner-accepted section 5 values are now what the API serves: 9 tactic bands (per 100 games, identical for rapid and classical) in `TACTIC_DELTA_ZONES`, the 12 flaw bands confirmed equal to the accepted table, and blitz/bullet bullets reading the rapid band silently.

## What was done

**Task 1 (commit f1c4599a0).**
- `tactic_delta_zones.py`: added `_both_tcs` helper and `_VIABLE_TACTIC_ZONES` with the 9 accepted bands (fork missed/allowed, pin missed/allowed, discovered_attack allowed, hanging missed/allowed, mate missed/allowed). `TACTIC_DELTA_ZONES` is built from it with `None` for the other 29. Docstring now states the basis (full-analysis lane, snapshot 2026-10-12), the rounding rule (lo down, hi up, 0.01 grid), the has_zone rule (pooled IQR non-degenerate and at least 50% non-zero user-cells), the accepted 9-of-38 set and the shared blitz/bullet to rapid stopgap.
- `flaw_delta_zones.py`: values NOT changed (verified equal to the `## Accepted` table, now pinned by a test). Docstring updated to state the basis, rounding, the single owner edit (live values kept instead of the proposed wider bands) and the stopgap.
- Tests: `test_flaw_delta_zones.py` pins all 12 bands for both zone TCs; `test_tactic_delta_zones.py` pins the viable set as a literal frozenset, the 9 band values and the 0.01 grid; `test_tactic_comparison_service.py` gained an end-to-end test (25 analyzed blitz games, no monkeypatch) asserting each viable bullet carries the registry rapid band and each unviable one has `has_zone` False with a 0.0/0.0 band. Two existing tests that assumed an all-None registry were updated to read the registry instead.
- Mutation check: changed `mate allowed` lo by 0.01 and `mistake` lo by 0.01 in turn; `test_viable_bands_equal_the_accepted_values` and `test_registry_values_equal_the_accepted_bands` both FAILED, then the source was restored and the suites passed (52 passed).

**Task 2 (no code change).**
- `LOW_SAMPLE_MIN_FLAWS` kept at 40 (`app/services/library_service.py:1353`), as accepted. The boundary tests (seeded from the constant) still pass.
- Elo keying not needed: `## Accepted` says "Elo keying: none" (largest ELO |d| = 0.44 on endgame_phase, no metric reached `keep separate` on either axis). No `ELO_BUCKETS`, `elo_bucket_for`, Elo registries, `elo_bucket` keyword or anchor lookup were added; the registries stay keyed by zone TC only.

## Deviations from Plan

**1. [Owner decision overrides plan text] Flaw bands not rewritten.**
- Plan truth 1 / task action step 1 assumed the 12 flaw bands change to the full-analysis values. `## Accepted` (authority per the dispatch) keeps today's live values, so the registry values are unchanged; only the docstring and integrity tests changed. No functional deviation beyond that.

**2. [Rule 1 - test fallout] Two existing tactic tests assumed an all-None registry.**
- `test_fixed_order_per_tc` and `test_zone_lookup_uses_each_bullets_tc` asserted `has_zone False` for all (other) bullets. They now compare against `tactic_delta_zone(...)` from the registry. Same file, same commit.

**3. Process slip, recovered.** After the mutation check I restored sources with `git checkout`, which also discarded the (uncommitted) real edits; I re-applied them verbatim and re-ran all suites. No effect on the final result.

## Verification

- `uv run pytest tests/services/test_flaw_delta_zones.py tests/services/test_tactic_delta_zones.py tests/services/test_tactic_comparison_service.py tests/services/test_flaw_comparison.py`: 52 passed.
- `uv run ty check app/ tests/`: all checks passed. `ruff check` / `ruff format` clean.
- `scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches.
- `grep -c "full-analysis"` in both registry modules is at least 1.

## Known Stubs

None.

## Threat Flags

None (no new endpoints, no DB or auth changes; T-239-15 not applicable since no anchor lookup was implemented).

## Self-Check: PASSED

- app/services/flaw_delta_zones.py, app/services/tactic_delta_zones.py: FOUND
- commit f1c4599a0: FOUND
