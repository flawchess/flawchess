---
id: SEED-169
status: parked
planted: 2026-09-16
planted_during: tilt study methods review (analysis/tilt_study/methods-review.md, Priority 3)
trigger_when: only if a reviewer or reader disputes that rating dynamics alone cannot produce the residual streak curve; the cheaper real-data checks (player x quarter intercepts, sensitivity ladder, tilt-report.md §2d–§2e) are already in place
scope: simulate no-carry-over player histories (fixed or slowly drifting strength, Glicko-style updates, realistic session and continuation structure), push them through story_data.py + gen_story.py unchanged, and report the residual curve the pipeline produces
---

# SEED-169: No-tilt simulation of the tilt-study pipeline

## Why parked

The methods review asked for a simulation under explicit no-tilt models to show whether
rating updates, slowly changing strength or session-level form can create a residual streak
curve on their own. Two reasons it was not built in the review response:

- For a constant-strength player, rating lag works *against* the observed pattern (under-rated
  after losses → should score above the benchmark), which the report now states with the
  Glicko arithmetic in §9.
- Slowly drifting strength is tested on real data instead: player x time-control x quarter
  intercepts in the within-player model move no contrast by more than 0.2 pp (§2d).

A simulation's result is fixed by its assumptions about opponents, continuation and session
boundaries (the review says so itself), so it adds little unless someone contests the two
points above.

## If promoted

- Generate per-player histories with the empirical session structure (reuse the real gap
  sequence per user, replace outcomes with draws from a strength-based Bernoulli/trinomial).
- Rating updates: Glicko-2 approximation with the same K as Lichess; opponents drawn from
  the real opponent ratings.
- Run the unchanged feature pipeline (`cached_games` on the synthetic parquet) and compare
  the residual curve to the observed one.
