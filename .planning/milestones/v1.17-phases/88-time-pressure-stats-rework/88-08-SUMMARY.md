---
phase: 88-time-pressure-stats-rework
plan: "08"
subsystem: benchmarks
tags:
  - benchmarks
  - zone-calibration
  - time-pressure
  - chess-score-per-pressure-bin
  - clock-gap
  - cohen-d
dependency_graph:
  requires:
    - 88-02: SKILL.md §3.3.3 and §3.3.1 clock-gap-% query skeletons
    - 88-03: PRESSURE_BIN_SCORE_NEUTRAL_ZONES placeholder scaffold + ZONE_REGISTRY clock_gap_pct entry
  provides:
    - "reports/benchmarks-latest.md §3.3.3 with full per-quintile Cohen's d verdicts and 4x5 pooled band table"
    - "reports/benchmarks-latest.md §3.3.1 clock-gap-% with pooled IQR band [-0.0641, +0.0466]"
  affects:
    - Plan 08 continuation: endgame_zones.py calibrated values + codegen regeneration (blocked at checkpoint)
tech_stack:
  added: []
  patterns:
    - "Per-quintile independent Cohen's d: 5 separate TC and ELO verdicts, not a single global verdict"
key_files:
  created: []
  modified:
    - "reports/benchmarks-latest.md"
key_decisions:
  - "ELO does NOT collapse for any of the 5 quintiles (d=0.43–0.79); blocking checkpoint presented to user"
  - "TC keeps separate for Q0 (d=0.63, bullet vs classical) and Q2 (d=0.63); review for Q1/Q3/Q4"
  - "clock-gap-% both axes review (TC d=0.23, ELO d=0.21); pooled band [-0.065, +0.047] justified"
  - "12 of 20 cells require editorial cap activation (half-width > 0.06)"
requirements-completed: []
duration: ~25min
completed: "2026-05-17"
---

# Phase 88 Plan 08: Benchmark Calibration Summary

**Benchmark §3.3.3 run confirms ELO does not collapse for any pressure-bin quintile (d=0.43–0.79), requiring a human checkpoint decision before calibrated values can replace placeholders in endgame_zones.py**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-17T~15:30Z
- **Completed:** 2026-05-17 (stopped at checkpoint Task 2)
- **Tasks:** 1 of 3 completed (Task 1), stopped at Task 2 checkpoint:decision
- **Files modified:** 1

## Accomplishments

- Ran §3.3.3 chess-score-per-pressure-bin query against benchmark DB (2026-05-17 snapshot, n=1,912 completed users across 19 non-sparse cells)
- Computed per-quintile Cohen's d for TC and ELO axes (10 verdicts total)
- Ran §3.3.1 clock-gap-% submetric; derived pooled IQR band; collapse analysis complete
- Appended both new sections plus 4x5 pooled band table to `reports/benchmarks-latest.md`
- Updated top-axis collapse summary and recommended thresholds tables in the report

## Task Commits

1. **Task 1: Run /benchmarks §3.3.3 + clock-gap-%** - `1609fb2e` (docs)

## Files Created/Modified

- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-a0a01e0aaa98e8343/reports/benchmarks-latest.md` — Added §3.3.1 clock-gap-% submetric section and §3.3.3 chess-score-per-pressure-bin section with full per-(quintile, ELO, TC) cells, collapse verdicts, 4x5 band table, and ready-to-use Python dict

## Decisions Made

- ELO collapse not confirmed for any quintile — Q0 is the most extreme (d=0.79, 800 vs 2400); even Q1 (the mildest) is d=0.43 which is "review" not "collapse". This contradicts the research expectation that ELO would collapse (based on §3.3.2 pooled d=0.17).
- TC axis: Q0 and Q2 both hit "keep separate" (d=0.63 each, driven by bullet vs classical gap). Q1/Q3/Q4 are "review" (0.22–0.39).
- clock-gap-%: both TC and ELO are "review" (d=0.21–0.23). Pooled IQR [-0.0641, +0.0466] is a defensible single band. This submetric is ready to ship regardless of the §3.3.3 decision.

## Deviations from Plan

None — plan executed exactly as specified through Task 1. Task 2 is a planned checkpoint:decision, not a deviation.

## Issues Encountered

- MCP tool `mcp__flawchess-benchmark-db__query` was not available in this worktree agent context. Used `docker compose exec -T db psql` via the `flawchess_benchmark` user instead. Results are identical.
- Initial edits went to the main repo's `reports/benchmarks-latest.md` due to absolute-path drift (#3099); corrected by copying to the worktree path and reverting the main repo file.

## Checkpoint Reached: Task 2 (Collapse Verdict Decision)

**The §3.3.3 data contradicts the ELO-collapse assumption built into the Plan 03 scaffold.**

### Key findings

| Quintile | TC verdict (worst pair) | ELO verdict (worst pair) |
|---:|---:|---:|
| Q0 (0–20% clock) | **keep (0.63)** bullet vs classical | **keep (0.79)** 800 vs 2400 |
| Q1 (20–40%) | review (0.29) | review (0.43) |
| Q2 (40–60%) | **keep (0.63)** bullet vs classical | **keep (0.58)** 1200 vs 2400 |
| Q3 (60–80%) | review (0.39) | **keep (0.61)** 1200 vs 2400 |
| Q4 (80–100%) | review (0.22) | **keep (0.71)** 800 vs 2400 |

### What this means for the 4x5 shape

The Plan 03 scaffold assumes ELO collapses per quintile and ships a (TC, quintile) band with ELO pooled. The data shows ELO does NOT collapse for any quintile. The three options (from the plan) are:

1. **collapse-clean** — not valid (data contradicts)
2. **accept-pooled-with-caveat** — use the 4x5 bands from the report's pooled table (12/20 cells cap-activated); document the ELO gradient caveat in CHANGELOG
3. **promote-to-elo-faceting** — extend schema to (TC, ELO, quintile) for all 5 quintiles; requires `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` extension, codegen, and frontend lookup changes; out of scope for Phase 88

The 4x5 pooled bands (with editorial cap applied) are ready-to-use if option 2 is selected. See `reports/benchmarks-latest.md §3.3.3` for the full table and Python dict literal.

### clock-gap-% is unblocked

Regardless of the §3.3.3 decision, the `clock_gap_pct` ZoneSpec can be updated now:
```python
"clock_gap_pct": ZoneSpec(
    typical_lower=-0.065,
    typical_upper=0.047,
    direction="higher_is_better",
)
```

## Self-Check

- [x] `1609fb2e` exists: `git log --oneline -1` confirms `docs(88-08): run §3.3.3 chess-score-per-pressure-bin...`
- [x] `reports/benchmarks-latest.md` contains §3.3.3 and clock-gap-% sections
- [ ] Task 3 (endgame_zones.py calibration + codegen) not yet executed — pending checkpoint decision

## Self-Check: PARTIAL

Task 1 complete and committed. Stopped at Task 2 checkpoint:decision as required by the plan. Task 3 is blocked pending user decision on ELO faceting.

---
*Phase: 88-time-pressure-stats-rework*
*Stopped at checkpoint: 2026-05-17*
