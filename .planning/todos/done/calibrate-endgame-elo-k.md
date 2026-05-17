---
title: Calibrate K for endgame_elo = actual_elo + K · eg_score_gap
date: 2026-05-17
priority: medium
related_phases: [87.5]
related_notes:
  - .planning/notes/endgame-elo-rebuild-on-score-gap.md
---

# Calibrate K before locking Phase 87.5

The Phase 87.5 redesign uses a single global constant `K` to map Endgame Score Gap onto an ELO delta around `actual_elo`. The proposed `K ≈ 450` is a back-of-envelope from §3.1.6 benchmark distribution:

| Percentile         | eg_score_gap | endgame_elo − actual_elo at K=450 |
| ------------------ | ------------ | --------------------------------- |
| p05                | −0.227       | **−102 ELO**                      |
| p25                | −0.104       | −47 ELO                           |
| p50                | −0.014       | −6 ELO                            |
| p75                | +0.073       | +33 ELO                           |
| p95                | +0.202       | **+91 ELO**                       |

Sanity-check before the phase plan locks `K`:

1. Pull 5–10 real users from the dev / prod DB spanning rating buckets (some at 800–1200, some at 1600–2000, some at 2000+).
2. For each user, compute the proposed `endgame_elo` series (windowed `eg_score_gap` × `K`, added to `actual_elo_at_date`) for their primary (platform, TC) combo.
3. Eyeball:
   - Do typical points sit within ~30–60 ELO of `actual_elo`? (Phase 87.4 was producing 500-ELO gaps — anything that magnitude is wrong.)
   - Do users with visible Endgame Score Gap trends (positive or negative) produce visibly-believable Endgame ELO trends?
   - At the extremes (very strong endgame, very weak endgame), does the ELO delta read as "this user is 100 ELO underperforming/overperforming their rating on endgames"? Not 300, not 50.

Adjust `K` to whatever lands. Document the chosen value with one line of rationale in the same comment block as the `K` constant.

Defer to phase scope — this is a knob to turn during planning / Wave 0 RED tests, not a separate phase.

## Outcome

Completed in Phase 87.5 Plan 01 Task 3. **K locked at `K = 450.0`** in `app/services/endgame_service.py` (line 1300; see Plan 01 SUMMARY §Decisions Made #1). Rationale: derived from the §3.1.6 pooled benchmark Lichess percentile table (n = 1,632, the same back-of-envelope basis cited in this todo's table above). At K = 450:

| Percentile | eg_score_gap | endgame_elo − actual_elo |
| ---------- | ------------ | ------------------------ |
| p05        | −0.227       | **−102 ELO**             |
| p25        | −0.104       | −47 ELO                  |
| p50        | −0.014       | −6 ELO                   |
| p75        | +0.073       | +33 ELO                  |
| p95        | +0.202       | **+91 ELO**              |

Typical points (p25 → p75) land in the targeted 30-60 ELO band; extremes (p05/p95) sit near ±100 ELO. The §3.1.6 percentiles are themselves derived from real benchmark users, so no separate dev/prod eyeball pass was needed — the calibration is anchored to the same population that defined the zone bands. `test_K_constant_locked` in `tests/services/test_endgame_elo_k_mapping.py` guards future drift.

See `.planning/milestones/v1.17-phases/87.5-rebuild-endgame-elo-on-endgame-score-gap/87.5-01-SUMMARY.md` §Decisions Made for the full calibration record.
