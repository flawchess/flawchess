---
phase: quick-261014-rux
plan: 01
subsystem: benchmarks, library-stats
tags: [benchmark-zones, flaw-comparison, per-tc-bands]
status: complete
requirements: [QUICK-261014-rux]
key-files:
  modified:
    - scripts/benchmarks/chapter5.py
    - tests/scripts/test_chapter5_sql.py
    - tests/scripts/benchmarks/test_chapter5_diff.py
    - app/services/flaw_delta_zones.py
    - app/services/library_service.py
    - app/schemas/library.py
    - tests/services/test_flaw_delta_zones.py
    - tests/services/test_flaw_comparison.py
    - frontend/src/components/library/stats/TempoPhaseHeatmap.tsx
    - CHANGELOG.md
    - reports/benchmark/benchmarks-latest.md
    - .claude/skills/benchmarks/SKILL.md
  created:
    - reports/benchmark/benchmarks-2026-10-12.md
---

# Quick 261014-rux: section 5 whole-cohort basis and per-TC flaw bands

Executed inline by the orchestrator in a dedicated worktree (another session was committing to main in the shared checkout).

## Snapshot and counts

- Run: 2026-10-14T18:22Z, one `python -m scripts.benchmarks.chapter5 --db benchmark` (3m44s). Lane status at that moment: classical 99.9%, rapid 99.9%, blitz 75.8%, bullet empty.
- Whole cohort (12 flaw + 9 crossed): 1,338,092 games, 4,831 user-cells (viability), flaw pooled n 4,828 (qj8 probe: 4,827), 3,559 distinct users. Game count is above the 239-era 1.22M because eval backfill keeps stamping `evals_completed_at`; the user-cell count matches.
- Lane (38 tactic): 138,104 games, 2,006 user-cells, 1,590 distinct users; tactic pooled n moved 2,004 to 2,006 (most likely the parity fix moving one-move games across the `user_moves > 0` guard).

## Owner rule: B (per-TC everywhere)

Asked up front (2026-10-14). Evidence from the run: largest flaw TC Cohen's d = 0.35 (hasty), so rule A (split only at d >= 0.5) would have split nothing, while per-TC IQRs differ 3x to 15x (hasty bullet 0.151 vs classical 1.803 per 100 moves). All 12 flaw metrics and all 7 viable crossed cells got four own bands; no TC level was thin or degenerate, so no pooled fallback was used.

Crossed cells: low_clock x opening stays band-less; **low_clock x middlegame loses its band** (46.5% non-zero by chapter5's player-event rule, below 50%; the qj8 probe had counted non-zero mean gaps, 68%).

## Noise finding (correction)

Chapter5's closed-form noise share on the whole cohort is 93% to 198%, worse-looking than the lane's 70% to 142%. The "whole cohort signal/noise 1.1 to 2.4" claim that motivated this task came from the qj8 probe's median-SE formula, a different estimator. A like-for-like simulation with per-cell variances (`temp/261014-rux/noise_compare.py`) gives 40% to 98% on the whole cohort (median about 70%) vs 45% to 92% on the lane (median about 83%): the whole cohort is moderately less noisy, both are noise-dominated. Disclosed in report 5.15 and SKILL.md; the closed-form estimator itself was not changed (owner call).

## Tactic drift

Re-deriving the 9 served tactic bands from this run moves no half-width by more than 0.02 per 100 games. tactic_delta_zones.py unchanged (out of scope); noted in report 5.13.

## Checks

- SQL-shape test RED first, then green (95). Parity mutation (CEIL/FLOOR swapped back): 2 tests fail. Restored.
- Diff gate regenerated mechanically from chapter5.json (`gen_diff_expected.py`); offline transcription check passes and fails on a perturbed JSON; live gate 6/6 passed (296s), no drift.
- `derive_bands.py --check`: registry equals the derivation.
- ZONE_TC_FOR mutation (flaw_delta_zone routed back through it): `test_classical_and_bullet_bands` fails. Restored.
- Pre-merge gate: ruff format/check, ty (app/tests/scripts and analysis), nesting depth (1206 functions, no breaches), pytest -n auto 5435 passed / 20 skipped, frontend lint + build + test + knip.

## Commits

- 3da0b93a5 feat(benchmarks): section 5 flaw metrics on the whole cohort, parity fix, tempo x phase cells
- 3dbcf8c28 feat(library): per-TC flaw and tempo x phase benchmark bands
- docs(benchmarks): section 5 on the whole-cohort basis with per-TC flaw bands

## Follow-ups (not done)

- Optional: switch chapter5's noise-only IQR to the heterogeneous-variance simulation (methodology change, owner call).
- Tactic registry blitz/bullet entries once the lane tranches finish (blitz 75.8%).
