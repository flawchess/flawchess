---
phase: 239-library-stats-you-vs-opponents
plan: 01
subsystem: benchmarks
tags: [benchmarks, chapter5, sql, flaw-delta, tactic-zones, full-analysis-lane]

requires:
  - phase: 212
    provides: benchmark_selection full-analysis lane (armed rows, full evals/PVs/blobs completion columns)
provides:
  - "chapter5.py rebuilt on the full-analysis lane (classical + rapid): 12 flaw + 38 tactic paired-delta metrics"
  - "enforced 30 user-cell floor, safe verdicts, noise-only IQR diagnostic, zone_viable flag"
  - "python -m scripts.benchmarks.chapter5 --db --out: section-5-only fast refresh CLI"
  - "per100g render unit"
  - "SKILL.md section 5 documenting basis, estimators, floor, noise, zone_viable and the verdict-to-registry rule"
affects: [239-06 benchmark run and registry values, 239-07 registry authoring, 239-02 backend payloads]

plan_head_before: 58cb1ee58c2337595d829dfbbf0eac5d166be234
plan_head_after: 658c28d962aad68ac7892015e0e814a07d35d380

actuals:
  tokens: 17000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One base_games CTE helper shared by the zone query and the viability query"
    - "Metric lists derived from imported app constants (FAMILY_TO_MOTIF_INTS, MIN_TACTIC_CHIP_CONFIDENCE) so a family remap re-groups the benchmark"
    - "DB-free SQL-shape test outside tests/scripts/benchmarks so the normal suite pins the benchmark SQL"

key-files:
  created:
    - tests/scripts/test_chapter5_sql.py
  modified:
    - scripts/benchmarks/chapter5.py
    - scripts/benchmarks/render.py
    - tests/scripts/benchmarks/test_chapter5_diff.py
    - .claude/skills/benchmarks/SKILL.md

key-decisions:
  - "user_moves is a base_games column, not a self-joined helper CTE: with the lane's small base the planner estimates 1 row and the helper self-join went O(n^2) (a 10+ minute run); now 24-43 s"
  - "Noise-only IQR is computed in the same GROUPING SETS scan as the distribution (extra noise_iqr column per metric row) instead of a second query over pu: identical numbers, no second pass over the CTE chain"
  - "Dropped the dead cells_with_iqr / cells_total (-1 placeholder) fields from ViabilityRow while rewriting it"

requirements-completed: [D-00f, D-06, D-07, D-08, D-09, D-10]

duration: 55min
completed: 2026-10-12
status: complete
---

# Phase 239 Plan 01: Benchmarks Section 5 on the Full-Analysis Lane Summary

**Section 5 now reads only armed classical/rapid `benchmark_selection` games with full evals, PVs and blobs, computes 12 flaw + 38 tactic Missed/Allowed paired-delta metrics with an enforced 30-cell floor, a noise-only IQR diagnostic and a zone_viable flag, and has a one-minute section-5-only CLI.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 of 3
- **Files:** 1 created, 4 modified

## Accomplishments

- `_base_games_cte()` is the single `base_games` definition for `_per_user_cte()` and `_viability_sql()`: `bs.armed`, `bs.tc_tranche IN ('classical','rapid')` (`FULL_ANALYSIS_TRANCHES`), `BASE_GAME_FILTER` (TC anchor), and the three completion columns (`full_evals_completed_at`, `full_pv_completed_at`, `blobs_completed_at`). `lichess_evals_at` is deliberately not used.
- `FLAW_DELTA_METRICS` is exactly the 12 keys; flaw_rate, hasty_miss and low_clock_miss are gone from the code, the diff gate and SKILL.md.
- `TACTIC_METRICS` (38 = 19 families x missed/allowed, keyed `tactic_{family}_{orientation}`): per-game raw count difference, motif IN the imported `FAMILY_TO_MOTIF_INTS` ints and confidence >= imported `MIN_TACTIC_CHIP_CONFIDENCE`. One `game_flaws` LEFT JOIN serves all 50 metrics.
- Cell floor enforced in `compute()` (`_apply_floor`, thin levels listed); `_safe_verdict` returns None instead of raising; `MetricBlock` gained `thin_levels` and `degenerate`; `ViabilityRow` gained `degenerate_iqr` and `zone_viable` (not degenerate and pct_nonzero >= 50).
- Noise-only IQR (`1.349 * sqrt(avg(var_samp/n))`) per metric, pooled and per TC, rendered next to the observed IQR and in a summary table (5.15).
- `render.py`: `per100g` unit (signed mean/pct, unsigned SD, 2 dp, no suffix); all existing units pinned byte-identical by 45 `fmt_value` pins captured before the edit.
- Render: 5.1-5.12 flaw sections with the noise line, 5.13 compact 38-row tactic table, 5.14 viability (flaw + tactic tables), 5.15 noise summary.
- CLI: `uv run python -m scripts.benchmarks.chapter5 --db benchmark --out DIR` (READ ONLY transaction) writes `chapter5.md` + `chapter5.json`.
- SKILL.md section 5 rewritten (basis, stopgap `ZONE_TC_FOR`, estimators, floor, noise, zone_viable, verdict-to-registry rule, fast path, report structure); frontmatter and the two section-1 cross references updated.

## Verification

- `uv run pytest tests/scripts/test_chapter5_sql.py -x`: 79 passed. `uv run ty check app/ tests/ scripts/`: clean. ruff format/check: clean.
- Mutation checks (reverted and confirmed failing): restoring the old `g.evals_completed_at` basis failed 3 tests; dropping the confidence predicate failed 2 tests. Both restored.
- Smoke CLI: `chapter5: 12 flaw + 38 tactic metrics; TC levels: rapid, classical; games: 138104`; `chapter5.json` has 38 tactic keys and all 50 viability rows carry `zone_viable`; `chapter5.md` contains the tactic table header with the zone_viable column.
- SKILL.md grep checks (FULL_ANALYSIS_TRANCHES, `python -m scripts.benchmarks.chapter5`, ZONE_TC_FOR, per100g) pass.

Smoke-run wall time: 24 s (12 flaw + 38 tactic metrics)

(The first 12-metric-only run took 43 s cold; the 50-metric run was measured once, warm cache. Plan 239-06 can run the executor route comfortably within the Bash 10-minute cap.)

## Observations for plan 239-06 (owner-relevant)

- **Bands are almost entirely sampling noise.** The noise-only IQR is 70-142% of the observed pooled IQR for all 12 flaw metrics (mistake 98%, blunder 97%, low_clock 142%, reversed 138%) and 95-170% for the 9 viable tactic metrics (e.g. mate_allowed 95%, fork_missed 124%). This confirms research Pitfall 1: at <=100 games per user per TC the per-user spread is mostly noise. Reported, not corrected (owner call at the 239-06 checkpoint).
- **zone_viable set on this run:** all 12 flaw metrics, and 9 of 38 tactic metrics: fork (missed/allowed), pin (missed/allowed), discovered_attack allowed, hanging (missed/allowed), mate (missed/allowed). The other 29 are degenerate (p25 == p75) or below 50% non-zero (x_ray, double_check, intermezzo, interference, capturing_defender, sacrifice, en_passant, under_promotion, promotion, skewer, ...). Not final: the owner confirms the has_zone set.
- **Verdicts on the lane:** across all 50 metrics the largest TC-axis |d| (rapid vs classical) is 0.21 and the largest ELO-axis |d| is 0.44 (endgame_phase). Nothing reaches the 0.5 keep-separate threshold, so on this run no Elo keying is triggered and the TC rule gives one pooled band per metric (a few TC/ELO verdicts are "review", 0.2-0.44).
- No marginal level fell below the 30-cell floor on this run (`thin_levels` empty for all 50 metrics, every metric has both verdicts); pooled n = 2,004 user-cells from 138,104 games (1,590 users).
- `tactic_trapped_piece_allowed` shows a 918% noise share (observed IQR is tiny, 0.25 per 100 games) and is not zone_viable.

## Task Commits

1. Task 1 (tracer): `995009ba0` feat: full-analysis basis for the 12 flaw metrics, floor, noise, CLI, SQL test; `2ba8a726d` fix: user_moves folded into base_games (O(n^2) plan fix)
2. Task 2: `eabb6a855` feat: 38 tactic metrics, compact table, per100g unit
3. Task 3: `658c28d96` docs: SKILL.md section 5 rewrite

(The SUMMARY.md docs commit follows and is not counted in `actuals.commits`.)

## Deviations from Plan

**1. [Rule 1 - Bug] Helper-CTE self-join made the first CLI run take 10+ minutes**
- **Found during:** Task 1 CLI run
- **Issue:** The inherited `user_moves_per_game` CTE self-joined `base_games`; with the lane's small base the planner estimated 1 row, chose a nested loop and the query went O(n^2). The run hit the Bash cap and was auto-backgrounded; I cancelled the orphaned backend query (`pg_cancel_backend`, own query only) and re-ran in the foreground.
- **Fix:** `user_moves` is now a `base_games` column; helper CTE removed; regression test `test_user_moves_lives_in_base_games_not_a_self_joined_helper_cte`.
- **Files modified:** scripts/benchmarks/chapter5.py, tests/scripts/test_chapter5_sql.py
- **Commit:** 2ba8a726d

**2. [Plan refinement] Noise diagnostic folded into the main scan**
- The plan asked for "one query over pu grouped by GROUPING SETS ((), (tc))". Each metric's existing GROUPING SETS select now carries a `noise_iqr` column (pooled and per-TC rows), same numbers, no second pass over the CTE chain. Data shape (`NoiseRow`) is as specified.

**3. [Cleanup] `ViabilityRow.cells_with_iqr` / `cells_total` removed** (permanent -1 placeholders, never rendered).

No other deviations.

## Known Stubs

None.

## Threat Flags

None. The SQL interpolates only closed in-code sets (FAMILY_TO_MOTIF_INTS keys/ints, `FULL_ANALYSIS_TRANCHES`, the two orientation literals, imported constants); the CLI's `--db` is an argparse `choices` value and `--out` only names the output directory; the session is `SET TRANSACTION READ ONLY`.

## Issues Encountered

- Fresh worktree needed `uv sync --group maia-inference` (done). `temp/239-benchmark/smoke/` output is gitignored scratch.

## Next Phase Readiness

Plan 239-06 can run `uv run python -m scripts.benchmarks.chapter5 --db benchmark --out <dir>` (about 25-45 s), regenerate the `test_chapter5_diff.py` EXPECTED_* numbers from that run (the current numbers are the pre-Phase-239 values and the gate will fail until regenerated; the gate is excluded from normal runs), narrate the report and author the registries.

## Self-Check: PASSED

Files verified: scripts/benchmarks/chapter5.py, scripts/benchmarks/render.py, tests/scripts/test_chapter5_sql.py, tests/scripts/benchmarks/test_chapter5_diff.py, .claude/skills/benchmarks/SKILL.md. Commits verified in history: 995009ba0, 2ba8a726d, eabb6a855, 658c28d96.
