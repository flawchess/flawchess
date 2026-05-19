---
phase: 88-time-pressure-stats-rework
plan: "02"
subsystem: benchmarks-skill
tags: [documentation, benchmarks, skill, time-pressure, zone-calibration]
dependency_graph:
  requires: []
  provides:
    - ".claude/skills/benchmarks/SKILL.md §3.3.3 — chess-score-per-pressure-bin SQL recipe and per-quintile collapse verdict methodology"
    - ".claude/skills/benchmarks/SKILL.md §3.3.1 clock-gap-% — clock gap metric recipe and ZONE_REGISTRY output destination"
  affects:
    - "Plan 08 — benchmark run to produce real Q1/Q3 values replacing PRESSURE_BIN_SCORE_NEUTRAL_ZONES placeholders"
    - "Plan 03 — zone-skeleton plan uses SKILL.md as calibration recipe reference"
tech_stack:
  added: []
  patterns:
    - "metric-with-sub-bins: per-user score aggregated per (TC x ELO x quintile) cell, 5 independent Cohen's d collapse verdicts per quintile"
key_files:
  created: []
  modified:
    - ".claude/skills/benchmarks/SKILL.md"
decisions:
  - "Per-quintile collapse verdict runs independently (5 verdicts), not as a single global verdict, because score distributions compress at extreme quintiles"
  - "ELO pooled by default for shipped band (20 entries: 4 TC x 5 quintile); any quintile with ELO d >= 0.5 promotes to per-(TC x ELO x quintile)"
  - "PRESSURE_BIN_NEUTRAL_CAP = 0.06 half-width cap applied if (p75 - p25) / 2 > 0.06, most likely activating at Q0 and Q4"
  - "clock-gap-% expected to collapse on both TC and ELO axes per prod-DB skew evidence (skew -0.05 to -0.09 = near-symmetric)"
  - "cohort_score is NOT precomputed in benchmark output — it comes from the live API mirror-bucket lookup"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-17T12:13:17Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 88 Plan 02: Benchmarks Skill — §3.3.3 and clock-gap-% Summary

## One-liner

Added §3.3.3 chess-score-per-pressure-bin (5-quintile per-user SQL recipe with per-quintile Cohen's d collapse verdicts and 4x5 IQR band) and clock-gap-% submetric to §3.3.1 in the benchmarks SKILL.md.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add §3.3.3 chess-score-per-pressure-bin | c33bb7c0 | .claude/skills/benchmarks/SKILL.md |
| 2 | Extend §3.3.1 with clock-gap-% submetric | c33bb7c0 | .claude/skills/benchmarks/SKILL.md |

## What Was Built

### §3.3.3 chess-score-per-pressure-bin

New subchapter appended after §3.3.2 in the benchmarks skill. Contains:

- **Shape statement**: metric-with-sub-bins, per-user `user_score = (W + 0.5D) / N` per `(user_id x TC x ELO x quintile)` where `quintile = LEAST(4, FLOOR(user_clk_pct / 20.0)::int)`.
- **Full SQL skeleton**: `endgame_games_with_clock` CTE with clock routing logic (mirrors `_compute_clock_pressure`), `per_user_quintile` CTE with HAVING `count(*) >= 5` per-bin floor, final SELECT with `percentile_cont(0.25/0.75)` for IQR bands. Includes sparse-cell exclusion `NOT (elo_bucket = 2400 AND tc = 'classical')` and equal-footing filter `abs(...) <= 100`.
- **Per-quintile collapse verdict template**: 5 rows (Q0..Q4), each with TC-axis d_max and ELO-axis d_max plus verdict thresholds. Explicitly states 5 independent verdicts.
- **Shipped band shape**: 20 entries (4 TC x 5 quintile), ELO pooled by default, with promotion path for quintiles with ELO d >= 0.5.
- **Output destination**: `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` in `app/services/endgame_zones.py`.
- **Editorial cap**: `PRESSURE_BIN_NEUTRAL_CAP = 0.06` applied as `max(p25, p50 - cap)` / `min(p75, p50 + cap)`.
- **Explicit note**: cohort_score is NOT in this output; it comes from the live API mirror-bucket lookup.

### §3.3.1 clock-gap-% extension

New `#### clock-gap-%` subsection appended within §3.3.1 (before §3.3.2). Contains:

- **Shape**: per-user mean `(my_clock - opp_clock) / base_clock` at endgame entry per `(user_id, TC, ELO)`.
- **SQL skeleton**: extends §3.3.1 `routed` CTE with a `per_user_gap` CTE, computing `avg((user_clk - opp_clk) / NULLIF(base_time_seconds, 0))` per user, final SELECT with full percentile distribution.
- **Expected verdict**: collapse on both TC and ELO axes, citing prod-DB skew evidence (skew -0.05 to -0.09, IQR approx ±10-16pp) from 88-RESEARCH.md §Q1.
- **Output destination**: `ZONE_REGISTRY["clock_gap_pct"]` ZoneSpec in `endgame_zones.py`, emitted as `CLOCK_GAP_NEUTRAL_MIN / CLOCK_GAP_NEUTRAL_MAX`.
- **Placeholder note**: initial values `(-0.05, 0.05)` to be replaced after benchmark run.

### Supporting table updates

- Live-threshold grep table: added rows for `3.3.1 clock-gap-%` and `§3.3.3` with their respective constants.
- Top-axis collapse summary: added 6 rows (clock-gap-% + 5 per-quintile chess-score entries).
- Report file layout skeleton: added `#### §3.3.3 chess-score-per-pressure-bin` entry.

## Deviations from Plan

None. Plan executed exactly as written. The report layout and top-axis collapse summary updates were minor additions for consistency (§3.3.3 needed entries in both reference tables so downstream benchmark runs have complete instructions).

## Known Stubs

None. This is documentation only. The zone constants themselves (`PRESSURE_BIN_SCORE_NEUTRAL_ZONES` placeholder values) are stubs that live in `endgame_zones.py` (Plan 03 scope), not in this skill file.

## Threat Flags

None. Documentation-only change; no new runtime surface introduced.

## Self-Check: PASSED

- SKILL.md modified: confirmed (c33bb7c0)
- `grep -c "### §3.3.3 chess-score-per-pressure-bin" .claude/skills/benchmarks/SKILL.md` = 2 (main + report layout) ✓
- `grep -c "PRESSURE_BIN_SCORE_NEUTRAL_ZONES" .claude/skills/benchmarks/SKILL.md` = 3 ✓
- `grep -c "LEAST(4, FLOOR" .claude/skills/benchmarks/SKILL.md` = 3 ✓
- `grep -c "PRESSURE_BIN_NEUTRAL_CAP" .claude/skills/benchmarks/SKILL.md` = 4 ✓
- `grep -c "NOT (elo_bucket = 2400 AND tc = 'classical')" .claude/skills/benchmarks/SKILL.md` = 10 (>=2) ✓
- 5 separate verdicts phrasing present ✓
- `grep -c "clock-gap-%" .claude/skills/benchmarks/SKILL.md` = 3 ✓
- `grep -c "clock_gap_pct\|CLOCK_GAP_NEUTRAL" .claude/skills/benchmarks/SKILL.md` = 2 ✓
- clock-gap-% heading (line 1791) appears before §3.3.2 (line 1838) ✓
- §3.3.2 heading count unchanged (2: main content + report layout) ✓
