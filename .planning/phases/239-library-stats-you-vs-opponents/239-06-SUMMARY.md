---
phase: 239-library-stats-you-vs-opponents
plan: 06
subsystem: benchmarks
tags: [benchmarks, zones, postgres, chapter5]

requires:
  - phase: 239-01
    provides: §5 on the full-analysis lane (12 flaw + 38 tactic metrics, zone_viable, noise-only IQR, CLI)
  - phase: 239-02
    provides: per-zone-TC flaw registry and LOW_SAMPLE_MIN_FLAWS
provides:
  - Pinned §5 diff gate on the full-analysis lane run
  - Narrated §5 in a rotated benchmarks-latest.md (2026-08-18 archived)
  - 239-ZONE-PROPOSAL.md with the owner's accepted registry values
affects: [239-07, 239-09]

actuals:
  tasks: 4
  commits: 4
  plan_head_before: 1b4ce6a6f65bd02bfe4dc4aa83988d87aa889369

key-files:
  created:
    - .planning/phases/239-library-stats-you-vs-opponents/239-ZONE-PROPOSAL.md
    - reports/benchmark/benchmarks-2026-08-18.md
  modified:
    - tests/scripts/benchmarks/test_chapter5_diff.py
    - reports/benchmark/benchmarks-latest.md

key-decisions:
  - "Owner accepted with one edit: the 12 flaw bands keep today's live values (no 1.5x-3.5x widening), because the proposed widening is driven by sampling noise from the lane's 100-games-per-TC cap"
  - "One pooled band per metric for rapid and classical, blitz/bullet read rapid, no Elo keying"
  - "9 tactic zones with the proposed bands: fork, pin, hanging and mate (missed and allowed) plus discovered_attack allowed; 29 stay band-less"
  - "LOW_SAMPLE_MIN_FLAWS stays 40"

requirements-completed: [D-06, D-07, D-08, D-09, D-10, D-12]

duration: ~15min executor + owner checkpoint
completed: 2026-10-13
---

# Phase 239 Plan 06: §5 run, report and zone decision Summary

**Outcome: accept with edits (keep live flaw bands); plan 239-07 writes the 9 tactic bands and verifies the flaw bands are unchanged.**

## Route and run

- Executor route (239-01 smoke 24 s); the §5 run ran in the foreground in 51 s wall time.
- Snapshot 2026-10-12T21:01Z. Lane: classical 99.9%, rapid 99.9% (blitz 74.1% and bullet 0% not used).
- Run output: `chapter5: 12 flaw + 38 tactic metrics; TC levels: rapid, classical; games: 138104`. Cohort: 138,104 games, 2,006 user×(ELO,TC) cells (2,004 pooled), 1,590 users.

## Tasks

| Task | Name | Commit |
|---|---|---|
| 1 | §5 run on the full-analysis lane, pinned in the diff gate | 6d1612b77 |
| 2 | Narrate §5 into rotated benchmarks-latest.md, rebuild both summaries | 321e3ecff |
| 3 | D-12 sanity check on dev data and the registry proposal | c5f6e0a4f |
| 4 | Owner decision recorded under ## Accepted (orchestrator, inline) | 60b019b05 |

## Verification

- `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q`: 4 passed (render scale guard, flaw delta, tactic delta, zone_viable set).
- ty and ruff clean. Report: §5.1-5.15 present, both summary tables rebuilt (flaw and tactic rows added to the recommended-thresholds table), §1-§4 unchanged except the §1 sentence about the §5 basis.
- No registry file edited, no DB writes (dev-DB SQL ran inside `BEGIN READ ONLY`).

## Findings

- Noise-only IQR is 70-142% of observed IQR for the flaw metrics and 95-170% for the 9 viable tactic metrics (the lane's 100-games-per-TC cap). Reported, not corrected.
- No metric reaches `keep separate` (largest TC |d| 0.21 hasty, largest ELO |d| 0.44 endgame_phase).
- D-12: median CI-half-width / band-width ratio 1.00 over 69 cells across 13 dev users (the owner has only 3 tactic cells in the window); keep 40. The ratio falls with game count (1.81 under 100 games, 0.42 at 300-999), so 40 is a compromise, not a sharp boundary.

## Deviations

- **[Rule 1] RESEARCH D-12 SQL:** queries 1 and 2 failed on Postgres (`round(double precision, integer)` does not exist); added `::numeric` casts.
- Task 4 continuation was done inline by the orchestrator (recording the decision is a two-minute job), not by a continuation agent.

## Self-Check: PASSED
