---
title: Opponent-mirror as a self-calibrating cohort reference for rate/gap metrics
date: 2026-05-17
context: Captured during a /gsd-explore session on a proposed Conversion ΔES timeline (SEED-020). The user proposed computing opponents' Conv ΔES against the user as a reference line, instead of pulling from a /benchmarks-derived cohort band. The idea generalizes well beyond that one chart and is worth a standalone note so it can be reused across future endgame and time-management visualizations.
related_files:
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - reports/benchmarks-latest.md
related_seeds: [SEED-019, SEED-020]
related_phases: [87.2, 87.6, 88]
---

# Opponent-mirror as a self-calibrating cohort reference

## The idea in one sentence

For any rate or gap metric the user cares about, the user's *opponents'* value of that same metric, computed across the user's imported games, is a personalized, rating-matched, TC-matched, platform-correct reference cohort that requires no /benchmarks lookup and drifts with the user automatically.

## Why it works

Online chess matchmaking on both chess.com and lichess pairs players within a narrow rating window. Across a user's import:

- **Rating-matched.** Opponents cluster near the user's rating at the time of each game.
- **TC-matched.** Bullet games pair with bullet-rated opponents; rapid with rapid. The opponent pool for each TC is calibrated to the user's TC-specific rating.
- **Self-calibrating temporally.** As the user climbs in rating, opponents climb with them. The reference is anchored to *what the user is actually facing now*, not a frozen benchmark snapshot.
- **Platform-correct.** No Lichess-vs-chess.com sigmoid calibration question — the comparison is intra-platform per combo by construction.
- **No external dependency.** Everything derives from `game_positions` rows for the user's own games. No /benchmarks DB hit at request time, no `endgame_zones.py` table to maintain for this reference.

The same reference simultaneously addresses the cohort drift that makes raw ΔES/rate timelines hard to read: the user's line and the mirror line drift together, so deviation between them — not absolute level — is the signal.

## The interpretation caveat (must appear in any popover)

The opponent mirror is **not** "peer cohort average." It is **"this user's opponents' value of the metric, measured against this user specifically."** That folds in the user's *complementary* skill on the same axis:

| Primary metric                       | Mirror folds in user's…           | Composite reading                                                              |
|--------------------------------------|-----------------------------------|--------------------------------------------------------------------------------|
| Conversion ΔES (user up → ?)         | Recovery skill (user down → ?)    | "In winning positions, do I outscore my opponents in *their* winning positions?" |
| Recovery ΔES (user down → ?)         | Conversion skill (user up → ?)    | Mirror of the above; symmetric                                                  |
| Parity ΔES (user even → ?)           | Parity skill itself (same axis)   | Genuinely peer-vs-peer on the same kind of positions; cleanest case             |

For Conversion and Recovery, the mirror line is a *composite* reference, not a pure cohort. For Parity it is the cleanest. This is acceptable provided labeling is explicit ("your opponents' Recovery vs you," not "average recovery"). The composite reading is arguably what users intuitively want anyway: "in the kinds of positions where I excel, do I outscore the kinds of positions where my opponents excel?"

## Sets of positions: not algebraic negation

For any single position, `ES_opponent = 1 − ES_user`. It is tempting to conclude that "opponent ΔES" is just the negation of "user ΔES" and provides no new information. **This is wrong for the gap metrics.** The reason is that Conversion ΔES is conditioned on the *side being up material*. Therefore:

- User Conv ΔES is computed on the set `S_user = { games where user entered endgame up }`.
- Opponent (mirror) Conv ΔES is computed on the set `S_opp = { games where opponent entered endgame up }`.
- `S_user ∩ S_opp = ∅` in any single game one side is up (or it's a parity game in `S_parity`, disjoint from both).

So the two values are derived from disjoint subsets of the user's games and are independent samples. The same logic holds for Recovery (swap the conditioning). Parity is the one case where both are computed on the same set of positions, in which case the algebraic identity does kick in and the mirror line is exactly `−1 × user line`, which is useless. **Therefore: do not use opponent-mirror for Parity. Use a different reference (raw cohort or just the zero line).**

## Where this is reusable

| Surface                                  | Mirror metric                  | Notes                                                                    |
|------------------------------------------|--------------------------------|--------------------------------------------------------------------------|
| Conv ΔES timeline (SEED-020)             | Opponent Conv ΔES vs user      | The motivating use case.                                                 |
| Recov ΔES timeline (hypothetical)        | Opponent Recov ΔES vs user     | Mirror of SEED-020 on the other side. Same plumbing flipped.            |
| Conv raw rate timeline                   | Opponent conversion rate vs user | Less interesting because raw rate is mostly a rating proxy.             |
| Time-management metrics                  | Opponent's matching value      | Already partially in place (avg clock advantage *is* user − opponent).   |
| Endgame ELO timeline                     | Already covered                | Non-Endgame ELO is the self-baseline; mirror would duplicate it.        |

## When *not* to use this

- **Parity ΔES timelines.** Mirror = `−1 × user` algebraically. Use the zero line or a benchmark cohort band instead.
- **Sample-too-thin combos.** The same active-weeks gate that applies to the user's line must apply to the mirror, and the mirror sample can be smaller (e.g. weeks where opponents had no converting positions). Drop the combo, do not show only one line.
- **Metrics where user and opponent values come from the *same* positions.** For position-state metrics like Entry Eval, both sides see the same eval, and the mirror is again algebraic.
- **When the user's import is small.** Mirror lines are noisy below ~30 games per combo. The same threshold guidance that gates the user's line should gate the mirror.

## Why this is a better default than the global CDF (SEED-019) for *timelines*

SEED-019 produces a global empirical CDF for percentile annotations on scalar values. That is the right tool for "where do I rank against everyone" on a single number. For *timelines*, a percentile chip would have to annotate every weekly point, and the global pool is not rating-matched, so the chip would mostly track ELO rather than skill drift.

The opponent-mirror is the timeline-native analog: a line, not a chip; personalized, not global; rating-drift-aware by construction. The two approaches are complementary — scalar metrics get global percentile chips (SEED-019), time series get personalized opponent-mirror references (SEED-020 and successors).

## Implementation cost reuse

Once the opponent-side eval-baselined aggregator exists for SEED-020, mirroring it for Recovery is a flip of the conditioning. The frontend chart component (`ConversionScoreGapTimelineSection`) can be parameterized to render any (user, mirror) pair, reducing each new mirror chart to a backend aggregator + a thin component variant.

## Cross-references

- Motivating phase plan: SEED-020 (Conv ΔES timeline).
- Adjacent approach: SEED-019 (global percentile annotations for scalar metrics).
- Benchmark cohort effect anchor: `reports/benchmarks-latest.md` §3.2.2, §3.2.3.
- Visual / structural template: `frontend/src/components/charts/EndgameEloTimelineSection.tsx`.
- Popover discipline: project memory `feedback_popover_copy_minimalism.md`.
