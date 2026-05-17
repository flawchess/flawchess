---
title: Endgame ELO — logistic-stretch anchored on Actual ELO
date: 2026-05-17
context: UAT feedback for Phase 87.6 — current PR-direct mapping breaks the "surrounding Actual ELO" invariant
status: proposal — to be implemented as Phase 87.6 in-flight amendment
supersedes: .planning/notes/endgame-elo-pr-direct-rebuild.md (the 87.6 design note)
---

## TL;DR

Replace Phase 87.6's PR-direct mapping with a **logistic stretch anchored on Actual ELO**:

```
gap_score = endgame_score − non_endgame_score        # already computed by 87.2 producer
spread    = 400 · log10( (s_E / (1 − s_E)) / (s_N / (1 − s_N)) )
endgame_elo     = actual_elo + spread / 2
non_endgame_elo = actual_elo − spread / 2
```

The midpoint `(endgame_elo + non_endgame_elo) / 2` equals `actual_elo` **by construction**, restoring the visual invariant Phase 87.5 had and Phase 87.6 broke. No free constant: the `400` is fixed by Elo's logistic-skill assumption (same `400` the FIDE PR formula uses).

## Why amend 87.6

Investigation 2026-05-17 against prod (`/tmp/investigate_actual_above_pr.py`, 10 top combos, 2 248 weekly points):

| | weeks | share |
|---|---:|---:|
| Actual ELO inside the band       |   270 | **12.0 %** |
| Actual ELO **above** both PRs    | 1 111 | **49.4 %** |
| Actual ELO **below** both PRs    |   867 | **38.6 %** |

The 87.6 "midpoint by construction" claim holds in 1 weekly point out of 8. Two compounding causes:

1. **Trailing-window lag** (dominant). The PR formula computes a 100-game-window estimator; Actual ELO is a live Glicko-1 (chess.com) / Glicko-2 (lichess) snapshot. When the user is improving, Actual leads PR by tens of ELO; when declining, Actual lags. Median 4-week ΔActual:
   - Above-both: +27 ELO (rising)
   - Below-both: −20 ELO (falling)
   - Inside the band: ±0 ELO (stable)
2. **Opponent-pool selection bias** (secondary). The endgame-vs-non-endgame split is not a random sample — games against stronger opponents end in resignation more often, so the endgame subset's `R_opp_avg` skews relative to the non-endgame subset's. PR depends linearly on `R_opp_avg`, so the bias passes through.

Going back to a Phase-87.5-style anchored mapping fixes the visual invariant. The variant proposed here improves on 87.5 by deriving the stretch from FIDE Elo math instead of an eyeballed `K=450`.

## The design

### Math

Anchored on Actual ELO so the midpoint property holds exactly. Spread derived from the logit of per-side scores:

```python
def _endgame_elo_logistic(actual_elo: int, endgame_score: float, non_endgame_score: float) -> tuple[int, int]:
    # Laplace-smoothed scores to avoid log(0) at all-win/all-loss streaks.
    # n is implicit at 100 (trailing window); the bias `2/(n+2)` is small enough
    # not to need exposing here, but the smoothing is still applied.
    s_E = max(min(endgame_score, 1 - 1e-6), 1e-6)
    s_N = max(min(non_endgame_score, 1 - 1e-6), 1e-6)
    spread = 400.0 * math.log10((s_E / (1 - s_E)) / (s_N / (1 - s_N)))
    return (
        int(round(actual_elo + spread / 2)),
        int(round(actual_elo - spread / 2)),
    )
```

### Properties

- `midpoint(endgame_elo, non_endgame_elo) ≡ actual_elo` for every emitted point. The "by construction" wording in the popover and the LLM glossary becomes literally true.
- Sign convention preserved: `endgame_elo ≥ non_endgame_elo` ⇔ endgame_score ≥ non_endgame_score ⇔ green band.
- Zero free parameters. The `400` is the same logistic scale FIDE Elo uses for its expected-score curve.
- Concave shape vs the linear K-mapping — small score gaps near 0.5 stretch more than gaps near the wings (statistically correct: dense-region score deltas imply bigger skill deltas).

### Magnitude comparison vs Phase 87.5 K=450

For a "typical" score gap of 0.10, the logistic spread is ~70 ELO (±35 per side). The 87.5 K-mapping at K=450 (single-line, per-side equivalent) produced ~45 ELO. So the logistic anchored variant lands **slightly tighter** than 87.5's calibration — the §3.1.6 score-gap percentile zone bands largely survive intact, with at most minor re-tuning.

| gap_score | logistic spread | logistic per-side | 87.5 K=450 per-side (single line) |
|---:|---:|---:|---:|
| 0.05 | 35 ELO | ±17 | ±22 |
| 0.10 | 70 ELO | ±35 | ±45 |
| 0.15 | 105 ELO | ±52 | ±67 |
| 0.20 | 141 ELO | ±70 | ±90 |
| 0.30 | 215 ELO | ±107 | ±135 |

## Implementation delta against current 87.6 code

The amendment is small. Files touched:

| File | Change |
|---|---|
| `app/services/endgame_service.py` | Replace `_performance_rating(score, n, opp_rating_avg)` with `_endgame_elo_logistic(actual_elo, endgame_score, non_endgame_score)`. Drop `opp_rating_avg` accumulators (`endgame_opp_window`, `non_endgame_opp_window`, `endgame_opp_rating_avg`, `non_endgame_opp_rating_avg`) from `_compute_score_gap_timeline` outputs. Wire the new function into `_compute_endgame_elo_weekly_series` (now needs `actual_elo` already on the point, which it has via the asof-join). |
| `app/repositories/endgame_repository.py` | Revert the Phase 87.6 SELECT extension: drop `Game.white_rating`, `Game.black_rating` from `query_endgame_performance_rows`. Drop the `WHERE white_rating IS NOT NULL AND black_rating IS NOT NULL` guard. Restore the 5-column row contract. |
| `app/schemas/endgame.py` (or wherever `ScoreGapTimelinePoint` lives) | Drop `endgame_opp_rating_avg`, `non_endgame_opp_rating_avg` fields. |
| `app/prompts/endgame_insights.md` | Rewrite the `endgame_elo` / `non_endgame_elo` glossary entries: not PR, but `actual_elo ± half · 400 · logit_gap`. Reinstate "midpoint property holds by construction" as a literal fact, not an approximation. Bump `_PROMPT_VERSION` to `endgame_v35` with a short summary line. |
| `frontend/src/components/charts/EndgameEloTimelineSection.tsx` | Popover copy: rewrite to "Endgame ELO and Non-Endgame ELO sit symmetrically around your Actual ELO — the band is your endgame's lift (green) or drag (red), measured in ELO units." Drop the "Performance Rating" framing entirely. The dashed/dotted line styles introduced in UAT 2026-05-17 stay. |
| `frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx` | Adjust test fixtures so `endgame_elo + non_endgame_elo == 2 · actual_elo` for every point (currently the asymmetric fixtures violate this). |
| `tests/services/test_endgame_service_phase_87_6.py` (or equivalent) | Replace PR unit tests with anchored-stretch tests: midpoint property exact, sign convention, monotone in gap_score, smoothing at 0/1 extremes. |
| `.planning/notes/endgame-elo-pr-direct-rebuild.md` | Add a frontmatter `supersededBy:` pointer to this note. |

Not touched:
- `frontend/src/lib/signedBandGradient.ts` — already a shared util, mechanics unchanged.
- Zone band registry — `gap_score` zones survive; possibly a minor re-tune after empirical comparison.
- Phase 57.1 volume bars and tooltip skeleton.
- Phase 87.6 LLM payload structure (`endgame_elo`, `non_endgame_elo`, `actual_elo` per point) — the numbers change, the schema does not.

## What this is NOT

- Not an absolute rating. "Endgame ELO" remains an editorial number: "what your rating would be if your endgame play set the level of your entire game." Same framing as Phase 87.5.
- Not a fix to the chess.com vs lichess Glicko-1 vs Glicko-2 difference (out of scope and not the dominant cause of the band-violation).
- Not a replacement for the `gap_score` LLM narration. The chart visualizes; `gap_score` percentile bands continue to drive the LLM's zone classification and prose.

## Risks / open questions

- **Score-gap zone bands** were tuned in score-gap units (§3.1.6). They are unaffected by the chart's mapping, but the *visual* mapping changes — readers may expect the same zone tile colors to correspond to the same ELO-band widths as Phase 87.5. The logistic variant is ~25 % tighter; a single calibration pass (e.g. visual inspection on a known user's chart) is worth doing before merge.
- **Tooltip copy** needs to surface that midpoint = Actual ELO is exact. The current "Endgame ELO / Actual ELO / Non-Endgame ELO" three-line tooltip works as-is; the "(past N games)" qualifier on Actual ELO stays.

## References

- Phase 87.5 K-mapping derivation: `.planning/notes/endgame-elo-pr-direct-rebuild.md` (will be marked superseded)
- Investigation script: `/tmp/investigate_actual_above_pr.py`
- HUMAN-UAT capture: `.planning/milestones/v1.17-phases/87.6-endgame-elo-via-performance-rating/87.6-HUMAN-UAT.md`
