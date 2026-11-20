---
id: SEED-261120-bzq
status: dormant
planted: 2026-11-20
planted_during: refinement of SEED-261114-iuv with the owner (split into a part built now and a deferred part)
trigger_when: after the Phase 252 repair has finished and Phases 252 and 254 plus the opponent scoring (SEED-261114-iuv Part A) have fully run in the benchmark DB. SEED-261114-iuv (facepalm rate in the library stats) should have shipped
scope: medium. Benchmark zones for the facepalm statistics, within-player bias, type-by-clock matrix, training weighting
---

# SEED-261120-bzq: Facepalm benchmark zones, within-player bias and clock matrix

The deferred half of SEED-261114-iuv. That seed ships the facepalm rate, the type split and the comparison
with opponents, none of which needs a benchmark. This seed holds everything that does, plus the ideas that
need more data checks first.

## Why This Matters

The comparison with opponents says whether a player facepalms more than the players they face. It does not say
whether a rate is typical for their rating and time control. That needs benchmarks from the benchmark DB.

## Scope

1. **Benchmarks per Elo bucket and time control** for facepalm blunders per game: total, missed win, allowed
   loss, and the you-minus-opponent paired deltas. Question to answer first: are there systematic differences
   by player level and time control?
2. **Benchmark zones** on the you-vs-opponents rows shipped by SEED-261114-iuv.
3. **Within-player bias** read against the benchmark for the player's Elo and time control.
4. **Type-by-clock matrix** like "Clock by game phase": under time pressure, do I allow more obvious losses or
   miss more easy wins than my opponents do, and when unrushed?
5. **Blunder-check training:** serve more of the type the player is worse at spotting.

## Constraints carried over from SEED-261114-iuv

- **Never compare the two types with each other.** The model weights lost material about three times as much
  as a missed gain (loss coefficient 1.16, missed 0.35 in the Phase 256 fit), so allowed losses pass the cut
  more easily (prod, 2026-11-20: 74% allowed loss, 24% missed win at the 0.7 cut). A type is compared only with
  the same type of opponents or of the benchmark cohort. A within-player missed share is valid only as a
  position inside the benchmark distribution of that same share, never against 50%.
- Stats cut 0.7 (separate constant), `FACEPALM_LIBRARY_LAMBDA`, type rule on the raw inputs: as defined in
  SEED-261114-iuv. The benchmarks must use the same cut, lambda and rule.
- Copy must not diagnose, and the score is a ranking, not a probability.
- The cut and the coefficients move with refits; benchmarks must be regenerated after a refit.
- Labels exist only below 2000; the 2000 and 2400 buckets are extrapolated.
- Facepalm blunders at 0.7 are not rare (32% of scored blunders), but type x clock x side cells can still get
  thin. Check counts before designing the matrix.
- The benchmark DB needs opponent scoring in the same order as prod (full mode, opponent backfill, line facts).
  Its state was not checked on 2026-11-20.

## Breadcrumbs

- `.planning/seeds/SEED-261114-iuv-facepalm-rate-library-stats.md` (decisions, measurements, history)
- `reports/benchmark/benchmarks-latest.md`, the `benchmarks` skill
- `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py`
- `app/services/maia_flaw_scoring.py`, `scripts/backfill_maia_flaws.py`
