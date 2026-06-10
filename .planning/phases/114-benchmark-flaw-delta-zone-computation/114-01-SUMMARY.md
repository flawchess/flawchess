---
phase: 114-benchmark-flaw-delta-zone-computation
plan: 01
subsystem: benchmarks
tags: [sql, cohen-d, flaw-delta, benchmark-generator, postgres, ctes]

# Dependency graph
requires:
  - phase: 113-materialized-opponent-flaws
    provides: opponent flaw rows in game_flaws (two-sided per-game flaw counts)
provides:
  - "§5 Flaw-Delta Zones benchmark chapter: per-cohort-user you−opponent delta for 15 metrics, per-(ELO×TC) Q1/Q3 + ELO/TC marginals + Cohen's-d collapse verdicts + per-metric viability diagnostic"
  - "Raw benchmark data (quartiles + marginals + verdicts + viability) that Phase 115 hand-authors into shipped flaw-delta zone constants"
  - "D-04 amendment fan-out: SEED-040 family split superseded by the unified per-100-moves paired-delta estimator; FLAWCMP-02 (Wilson diff-of-proportions) voided"
affects: [115-comparison-api-bullet-grid, benchmarks-skill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unified per-100-moves paired-per-game delta estimator for all 15 flaw metrics (no count-rate/proportion family split)"
    - "All-analyzed-games basis: base_games LEFT JOIN game_flaws so clean games contribute a 0 delta"
    - "Reuse of dist.agg_select / split_grouping_sets / verdict from the chapter3 multi-metric UNION-ALL pattern"

key-files:
  created:
    - scripts/benchmarks/chapter5.py
    - tests/scripts/benchmarks/test_chapter5_diff.py
  modified:
    - scripts/gen_benchmarks.py
    - .claude/skills/benchmarks/SKILL.md
    - .planning/REQUIREMENTS.md
    - reports/benchmark/benchmarks-latest.md

key-decisions:
  - "D-01 unified estimator: (player_tag − opp_tag) / user_moves_in_game × 100, paired per game, averaged per user — one estimator for all 15 metrics"
  - "All-analyzed-games basis (final fix): clean games count as a 0 delta (base_games LEFT JOIN game_flaws), ~4× more user×cell rows (3,725 → 4,644 pooled n), magnitudes compress toward zero"
  - "user_moves_in_game from game_positions ply-parity count (even ply=white, odd ply=black), NOT games.move_count"
  - "Named floors: FLAW_DELTA_MIN_GAMES=20 (D-08), _CELL_CONTRIBUTOR_FLOOR=30 (D-07), _DELTA_DIGITS=4"
  - "Benchmark-computation + narration ONLY — no endpoint, no UI, no committed zone constants, no DB table, no migration (D-09)"

patterns-established:
  - "chapter5 mirrors chapter3 build/compute/render + viability diagnostic seam"
  - "Code emits Cohen's-d value; SKILL.md narration supplies the collapse/review/keep words (code/LLM seam)"

# Metrics
duration: resumed (multi-session)
completed: 2026-06-10
requirements-completed: [FLAWBMK-01, FLAWBMK-02, FLAWBMK-03, FLAWBMK-04]
---

# Phase 114: Benchmark Flaw-Delta Zone Computation Summary

**Added a §5 Flaw-Delta Zones benchmark chapter computing the D-01 unified per-100-moves paired-delta for all 15 flaw metrics, with per-(ELO×TC) Q1/Q3 + ELO/TC marginals + Cohen's-d verdicts + a viability diagnostic, narrated into `benchmarks-latest.md` — the raw data Phase 115 hand-authors into shipped zone constants.**

## Performance

- **Duration:** resumed across sessions (closeout this session)
- **Completed:** 2026-06-10
- **Tasks:** 5 (4 implementation + 1 human-verify checkpoint)
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- **`scripts/benchmarks/chapter5.py`** — new §5 chapter: `build`/`compute`/`render`, the unified per-user CTE chain (`base_games` → `user_moves_per_game` → `per_game_tags` → `per_game_delta` → `per_user` → `pu`), and `_compute_viability`. 15 metrics: flaw_rate, low_clock, hasty, unrushed, opening, middlegame, endgame_phase, miss, lucky, reversed, squandered, hasty_miss, low_clock_miss, mistake, blunder.
- **Diff-gate** (`test_chapter5_diff.py`) — numeric acceptance gate for pooled + ELO + TC marginals + Cohen's-d verdicts across all 15 metrics; green against the live benchmark DB (2 passed, ~122s).
- **`gen_benchmarks.py`** — registered `5-flaw-delta-zones` in `CHAPTER_STUBS` + `_CHAPTER_BUILDERS`.
- **`SKILL.md`** — §5 narration section + report layout wiring + verdict-words seam.
- **`benchmarks-latest.md`** — §5 narrated with all 15 metrics, marginals, verdicts, and viability.
- **`REQUIREMENTS.md`** — D-04 amendment fan-out (SEED-040 split superseded; FLAWCMP-02 voided); FLAWBMK-01..04 marked complete.

## Closeout notes (resumed phase)

This phase was resumed from a partially-complete state. Tasks 1–4 were committed in a
prior session, but the final estimator fix (`08ab86d5`, all-analyzed-games basis) had
two uncommitted/incomplete downstream effects that were finished this session:

1. **Re-populated the §5 diff-gate** + committed the verified values (pooled n 3,725 → 4,644).
2. **Completed the §5 re-narration** — the prior re-narration had stopped after only 2 of 15
   metrics. §5.3–§5.15 distribution tables, the §5.16 viability table + interpretation, and
   the 15 §5 rows in the "Top-axis collapse summary" headline table still showed the old
   flawed-games-only basis (n=3,725). All refreshed from `chapter5.render(compute())` against
   the live benchmark DB. Notable verdict flips on the new basis: flaw_rate TC review(0.21) /
   ELO collapse(0.17); hasty & middlegame TC review at the 0.20 boundary; max |d| = 0.27
   (endgame_phase ELO). Viability: low_clock 67.4%, low_clock_miss 53.6% (rarest).

## Verification

- `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` → 2 passed.
- `uv run pytest -n auto -x` (standard suite, benchmark dir excluded) → green.
- `uv run ruff format --check` / `ruff check` / `ty check app/ tests/` → clean.
- HUMAN-UAT: §5 narrated correctly into `benchmarks-latest.md` (15 metrics, marginals, verdicts, viability).

## Follow-ups for Phase 115

- Hand-author shipped zone constants from §5 (D-10) — pooled global zones recommended for all metrics (mostly-collapse).
- `low_clock` (67.4% non-zero) and `low_clock_miss` (53.6%) need "N/A"/"insufficient data" display fallbacks.
- `endgame_phase` (ELO d=0.27) and `blunder` flagged for potential per-ELO refinement.
- `squandered`/`lucky` state-conditional residual disclosed via a Phase 115 tooltip (D-03).
