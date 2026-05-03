---
title: Benchmark equal-footing framing — calibrate zones on ±100 opponent-gap games
date: 2026-05-03
context: Captured during /gsd-explore session triggered by the 2026-05-03 benchmarks report. Inspecting the per-cell ELO Cohen's d values raised the question — is the apparent ELO skill ramp (e.g. d=1.18 on Endgame Skill, 800 vs 2400) genuine skill stratification, or is it partly an opponent-strength matchmaking artifact?
related_files:
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-2026-05-03.md
  - frontend/src/generated/endgameZones.ts
  - app/repositories/query_utils.py
related_todos:
  - .planning/todos/pending/2026-05-03-rerun-benchmarks-equal-footing.md
---

## The confound

The 2026-05-03 report's per-cell opponent-gap analysis revealed a strong matchmaking
asymmetry across rating cohorts (negative = user faces weaker opponents on average):

| ELO  | bullet | blitz | rapid | classical |
|------|--------|-------|-------|-----------|
| 800  | +16    | +16   | +18   | +47       |
| 1200 | +12    | +7    | +5    | +17       |
| 1600 | +1     | +6    | -2    | -18       |
| 2000 | -26    | -36   | -42   | -72       |
| 2400 | **-57**| **-80**| **-128**| **-372**|

The 2400 cohort consistently faces weaker opponents, especially in slower TCs where
the rating pool thins out. A 2400-rapid player faces opponents averaging 128 Elo
weaker — a meaningful chunk of their elevated conversion / endgame-skill metrics
likely comes from this matchmaking advantage rather than pure endgame skill.

## The decision

Benchmark population baselines (in `.claude/skills/benchmarks/SKILL.md`) are
calibrated on games where `abs(opponent_rating - user_rating) <= 100` — the
**"skill at equal footing"** baseline. This applies to:

- §2 Conversion / Parity / Recovery + Endgame Skill
- §3 Endgame ELO gap
- §6 Per-class breakdown

It does NOT apply to:

- §1 Score gap (eg vs non-eg) — measures whole-game outcome distribution
- §4 Time pressure stats — about clock behavior, not skill
- §5 Time pressure vs performance curves — same

## Rationale: framing (b) over framing (a)

Two framings were considered:

- **(a) "How well do you do compared to others *on the platform overall*"** — keep all
  games. Measured rate includes matchmaking advantage, which is real (the 2400
  user really does win at that rate in their actual games).
- **(b) "How well do you do compared to others *at equal footing*"** — apply ±100
  filter to the baseline only.

We picked **(b)** because:

1. The user's actual measured value in the live UI still uses unfiltered games
   (their real performance, including matchmaking advantage).
2. The gauge zones the value is compared against are confound-free.
3. Higher-rated players will naturally see green/above-zone gauges in the UI
   because their measurement (with matchmaking advantage) sits above the
   equal-footing baseline. This is the *intended* signal — "you do better than
   players at equal footing would, partly because you also play weaker
   opponents on average."
4. The in-app opponent-strength filter is the user-facing escape hatch for
   switching to skill-only views — if a user wants to remove the matchmaking
   contribution, they apply the filter and their measured value drops to match
   the equal-footing baseline.

## Empirical check (deferred to rerun todo)

The hypothesis we want to test by rerunning the benchmark report under the filter:
how much does the ELO Cohen's d ramp shrink? Predictions:

- If filtered ELO d on Endgame Skill drops from 1.18 → ~0.4, the unfiltered ramp
  was mostly matchmaking artifact. Per-ELO zones should be retired; pooled zones
  become correct.
- If filtered ELO d stays ≥ 0.7, the skill cohort effect is real even at equal
  footing. Per-ELO zones are still warranted but using filtered cell values.

The rerun and comparison are tracked in
`.planning/todos/pending/2026-05-03-rerun-benchmarks-equal-footing.md`.

## Sample-size cost (acceptable)

±100 filter retention per cell:

| ELO  | bullet | blitz | rapid | classical |
|------|--------|-------|-------|-----------|
| 800  | 83%    | 85%   | 82%   | 53%       |
| 1200 | 90%    | 89%   | 88%   | 72%       |
| 1600 | 86%    | 89%   | 88%   | 71%       |
| 2000 | 78%    | 78%   | 74%   | 57%       |
| 2400 | 67%    | 62%   | 51%   | **15%**   |

All non-sparse cells retain enough games to clear the per-user floors (≥20–30
endgame games/user). 2400-classical was already excluded as the sparse cell.
