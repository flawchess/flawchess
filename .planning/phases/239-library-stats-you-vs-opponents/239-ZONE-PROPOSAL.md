# Phase 239 Zone Proposal (plan 239-06)

Registry proposal for plan 239-07, derived from one section 5 run on the full-analysis lane by the SKILL.md verdict-to-registry rule. **Nothing in `app/services/*_zones.py` has been changed.** The owner accepts, edits or holds at the plan 239-06 checkpoint; the outcome is recorded under `## Accepted` at the bottom.

## Snapshot

- Run: 2026-10-12T21:01Z, `uv run python -m scripts.benchmarks.chapter5 --db benchmark --out temp/239-benchmark/final` (about 50 s, foreground executor route).
- Lane state at the snapshot: classical 99.9% and rapid 99.9% (`best_moves_done / selected`); blitz 74.1% and bullet 0% are not used (D-08).
- Cohort basis: 138,104 analyzed games, 2,006 user×(ELO,TC) cells (2,004 cells in the pooled distributions after the per-metric floor), 1,590 distinct users. Armed `benchmark_selection` games, classical + rapid, full evals + PVs + blobs, equal-footing filter, at most 100 games per user per TC, per-user mean over at least 20 games.
- Full report: `reports/benchmark/benchmarks-latest.md` section 5 (rotated previous report: `benchmarks-2026-08-18.md`). Diff gate: `tests/scripts/benchmarks/test_chapter5_diff.py`, 4 passed, 0 skipped.
- Units: flaw bands are per 100 user moves; tactic bands are per 100 games. Negative = fewer flaws than the opponent = good. Bands are `p25 / p75` of the pooled distribution rounded outward to the 0.01 grid.

## Headline for the decision

1. **No metric reaches `keep separate` on either axis.** Largest TC |d| over all 50 metrics is 0.21 (hasty), largest ELO |d| is 0.44 (endgame_phase). By the rule that means **one pooled band per metric, shared by rapid and classical, and no Elo keying anywhere**.
2. **The bands are mostly sampling noise.** The noise-only IQR (what per-user means would spread to if every user had the same true gap) is 70% to 142% of the observed IQR for the 12 flaw metrics and 95% to 170% for the 9 viable tactic metrics. The lane caps each user at 100 games per TC, so per-user means are far noisier than the old 1000-game basis. The proposal ships the measured IQR as the rule says; it is the owner's call whether that is acceptable (hold = reopen the methodology, for example a shrinkage estimator).
3. **Every flaw band widens, by 1.5x to 3.5x versus the live band** (see 'What users will see move'). Wider bands mean fewer red/green verdicts and more 'typical' ones.
4. **9 of 38 tactic metrics are viable** (`has_zone = true`); the other 29 stay band-less. `low_clock` is a thin numerator (59.1% non-zero).
5. **D-12: keep `LOW_SAMPLE_MIN_FLAWS = 40`** (evidence below).

## Flaw registry (12 metrics, per 100 user moves)

Proposed rapid and classical bands are identical because the TC axis is `collapse` or `review` for all 12 (rule: pooled p25/p75 for both). Blitz and bullet read the rapid band (D-08/D-09).

| metric | TC verdict (d) | ELO verdict (d) | proposed rapid lo / hi | proposed classical lo / hi | live lo / hi | observed pooled IQR | noise-only IQR | noise share |
|---|---|---|---|---|---|---:|---:|---:|
| mistake | collapse (0.00) | collapse (0.18) | -0.66 / +0.39 | -0.66 / +0.39 | -0.23 / +0.20 | 1.041pp | 1.022pp | 98% |
| blunder | collapse (0.15) | collapse (0.14) | -0.83 / +0.31 | -0.83 / +0.31 | -0.31 / +0.25 | 1.133pp | 1.102pp | 97% |
| low_clock | collapse (0.03) | review (0.25) | -0.12 / +0.05 | -0.12 / +0.05 | -0.08 / +0.03 | 0.167pp | 0.238pp | 142% |
| hasty | review (0.21) | review (0.28) | -1.16 / +0.45 | -1.16 / +0.45 | -0.28 / +0.18 | 1.593pp | 1.126pp | 71% |
| unrushed | collapse (0.11) | review (0.36) | -0.94 / +0.74 | -0.94 / +0.74 | -0.38 / +0.36 | 1.672pp | 1.165pp | 70% |
| opening | review (0.20) | review (0.33) | -0.60 / +0.27 | -0.60 / +0.27 | -0.15 / +0.13 | 0.863pp | 1.080pp | 125% |
| middlegame | collapse (0.02) | review (0.34) | -0.62 / +0.35 | -0.62 / +0.35 | -0.27 / +0.23 | 0.957pp | 0.869pp | 91% |
| endgame_phase | collapse (0.09) | review (0.44) | -0.24 / +0.18 | -0.24 / +0.18 | -0.12 / +0.10 | 0.413pp | 0.421pp | 102% |
| miss | collapse (0.02) | collapse (0.16) | -0.32 / +0.28 | -0.32 / +0.28 | -0.11 / +0.11 | 0.584pp | 0.652pp | 112% |
| lucky | collapse (0.07) | collapse (0.09) | -0.23 / +0.26 | -0.23 / +0.26 | -0.09 / +0.09 | 0.474pp | 0.559pp | 118% |
| reversed | collapse (0.01) | collapse (0.13) | -0.12 / +0.11 | -0.12 / +0.11 | -0.04 / +0.04 | 0.217pp | 0.300pp | 138% |
| squandered | collapse (0.03) | collapse (0.11) | -0.17 / +0.19 | -0.17 / +0.19 | -0.07 / +0.08 | 0.356pp | 0.410pp | 115% |

Per-TC marginal IQRs, for reference if the owner prefers per-TC bands on the two TC `review` metrics (hasty 0.21, opening 0.20); not part of the proposal:

| metric | rapid marginal lo / hi | classical marginal lo / hi |
|---|---|---|
| hasty | -0.97 / +0.44 | -1.66 / +0.53 |
| opening | -0.51 / +0.26 | -0.83 / +0.29 |

## Tactic registry (38 metrics, per 100 games)

`has_zone` = `zone_viable` (pooled IQR not degenerate AND at least 50% of user-cells non-zero). Proposed bands exist only where `has_zone` is true; both zone TCs share the pooled band (TC axis is `collapse` for all 38). No tactic family has a live band today (all band-less), so the live column reads `none`.

| family | side | has_zone | pct_nonzero | proposed rapid lo / hi | proposed classical lo / hi | live | TC verdict (d) | ELO verdict (d) | observed pooled IQR | noise-only IQR |
|---|---|---|---:|---|---|---|---|---|---:|---:|
| fork | missed | true | 79.2% | -2.21 / +2.13 | -2.21 / +2.13 | none | collapse (0.04) | collapse (0.05) | 4.33 | 5.37 |
| fork | allowed | true | 93.8% | -4.12 / +3.23 | -4.12 / +3.23 | none | collapse (0.01) | collapse (0.14) | 7.34 | 8.06 |
| skewer | missed | false | 23.1% | none | none | none | collapse (0.05) | collapse (0.04) | 0.00 | 1.78 |
| skewer | allowed | false | 35.6% | none | none | none | collapse (0.04) | collapse (0.07) | 0.00 | 2.38 |
| pin | missed | true | 66.1% | -1.42 / +1.89 | -1.42 / +1.89 | none | collapse (0.04) | collapse (0.08) | 3.30 | 3.95 |
| pin | allowed | true | 80.0% | -2.86 / +2.05 | -2.86 / +2.05 | none | collapse (0.05) | collapse (0.12) | 4.90 | 5.20 |
| x_ray | missed | false | 1.1% | none | none | none | collapse (0.02) | collapse (0.10) | 0.00 | 0.41 |
| x_ray | allowed | false | 1.5% | none | none | none | collapse (0.02) | collapse (0.10) | 0.00 | 0.39 |
| double_check | missed | false | 4.1% | none | none | none | collapse (0.06) | collapse (0.08) | 0.00 | 0.69 |
| double_check | allowed | false | 7.9% | none | none | none | collapse (0.00) | collapse (0.11) | 0.00 | 0.96 |
| discovered_check | missed | false | 25.8% | none | none | none | collapse (0.01) | collapse (0.12) | 0.00 | 1.92 |
| discovered_check | allowed | false | 41.7% | none | none | none | collapse (0.06) | collapse (0.06) | 2.00 | 2.60 |
| discovered_attack | missed | false | 37.3% | none | none | none | collapse (0.01) | collapse (0.09) | 0.00 | 2.40 |
| discovered_attack | allowed | true | 55.3% | -1.24 / +1.06 | -1.24 / +1.06 | none | collapse (0.01) | collapse (0.08) | 2.29 | 3.15 |
| trapped_piece | missed | false | 23.6% | none | none | none | collapse (0.06) | review (0.22) | 0.00 | 1.75 |
| trapped_piece | allowed | false | 37.4% | none | none | none | collapse (0.05) | collapse (0.18) | 0.25 | 2.30 |
| hanging | missed | true | 61.4% | -1.13 / +1.48 | -1.13 / +1.48 | none | collapse (0.00) | review (0.20) | 2.60 | 4.43 |
| hanging | allowed | true | 92.8% | -5.11 / +3.04 | -5.11 / +3.04 | none | collapse (0.05) | collapse (0.15) | 8.13 | 9.03 |
| mate | missed | true | 78.9% | -2.18 / +2.90 | -2.18 / +2.90 | none | collapse (0.06) | collapse (0.14) | 5.07 | 6.50 |
| mate | allowed | true | 95.8% | -7.00 / +4.09 | -7.00 / +4.09 | none | collapse (0.03) | collapse (0.06) | 11.09 | 10.55 |
| deflection | missed | false | 30.4% | none | none | none | collapse (0.04) | review (0.23) | 0.00 | 1.97 |
| deflection | allowed | false | 40.4% | none | none | none | collapse (0.06) | review (0.23) | 2.00 | 2.46 |
| intermezzo | missed | false | 11.7% | none | none | none | collapse (0.03) | collapse (0.15) | 0.00 | 1.15 |
| intermezzo | allowed | false | 18.3% | none | none | none | collapse (0.07) | review (0.22) | 0.00 | 1.43 |
| interference | missed | false | 5.4% | none | none | none | collapse (0.09) | collapse (0.12) | 0.00 | 0.74 |
| interference | allowed | false | 7.8% | none | none | none | collapse (0.03) | collapse (0.15) | 0.00 | 0.92 |
| capturing_defender | missed | false | 7.9% | none | none | none | collapse (0.04) | review (0.28) | 0.00 | 0.88 |
| capturing_defender | allowed | false | 13.0% | none | none | none | collapse (0.05) | review (0.23) | 0.00 | 1.28 |
| attraction | missed | false | 34.1% | none | none | none | collapse (0.07) | collapse (0.10) | 0.00 | 2.16 |
| attraction | allowed | false | 43.2% | none | none | none | collapse (0.13) | collapse (0.11) | 2.01 | 2.55 |
| sacrifice | missed | false | 33.3% | none | none | none | collapse (0.01) | collapse (0.11) | 0.00 | 2.16 |
| sacrifice | allowed | false | 32.5% | none | none | none | collapse (0.04) | collapse (0.11) | 0.00 | 2.15 |
| en_passant | missed | false | 6.1% | none | none | none | collapse (0.01) | collapse (0.08) | 0.00 | 0.72 |
| en_passant | allowed | false | 9.9% | none | none | none | collapse (0.05) | review (0.24) | 0.00 | 0.95 |
| under_promotion | missed | false | 0.2% | none | none | none | collapse (0.07) | collapse (0.10) | 0.00 | 0.20 |
| under_promotion | allowed | false | 0.5% | none | none | none | collapse (0.04) | collapse (0.10) | 0.00 | 0.29 |
| promotion | missed | false | 21.0% | none | none | none | collapse (0.07) | collapse (0.12) | 0.00 | 1.58 |
| promotion | allowed | false | 31.2% | none | none | none | collapse (0.05) | collapse (0.09) | 0.00 | 2.05 |

Hand-checked has_zone set (9 true): fork missed/allowed, pin missed/allowed, discovered_attack allowed, hanging missed/allowed, mate missed/allowed. The weakest viable members are `discovered_attack` allowed (55.3% non-zero, noise share 138%) and `hanging` missed (61.4%, noise share 170%, the noisiest of the viable set); the owner may prefer to drop those two from the has_zone set. `trapped_piece` allowed is not viable and shows a 918% noise share (observed IQR 0.25 per 100 games).

## Elo keying

**None.** No metric (flaw or tactic) has an ELO verdict of `keep separate` (largest ELO |d| = 0.44, `endgame_phase`). Metrics with an ELO `review` verdict (no keying triggered): low_clock (0.25), hasty (0.28), unrushed (0.36), opening (0.33), middlegame (0.34), endgame_phase (0.44); tactics: trapped_piece_missed (0.22), hanging_missed (0.20), deflection_missed (0.23), deflection_allowed (0.23), intermezzo_allowed (0.22), capturing_defender_missed (0.28), capturing_defender_allowed (0.23), en_passant_allowed (0.24).

## D-12 sanity check: `LOW_SAMPLE_MIN_FLAWS`

Method (RESEARCH queries 1 and 2, extended to all 12 context tags; READ ONLY on the dev DB): for each (user, TC, family, side) tactic cell and each (user, TC, tag) context cell with 30 to 60 total flaws (you + opponent), the CI half-width of the per-game paired delta (`1.96 * sd / sqrt(n_games)`, per 100 games or per 100 moves) divided by the proposed band width (`hi - lo` above). Tactic cells are scored only where the family has a proposed band. Rule (A7, owner confirms): typical ratio above 1.5 raises the constant, below 0.5 lowers it, otherwise keep 40. Note: the RESEARCH query 1 needed a `::numeric` cast on `round()` to run on Postgres (a query bug, not a data issue).

Owner (dev user 28; rapid 1,841 and blitz 1,000 analyzed games) has 3 tactic cells and 0 context-tag cells in the 30 to 60 window (the owner's context-tag cells all have hundreds of flaws):

| cell (user 28) | n_games | total flaws | CI half-width (per 100 games) | proposed band width | ratio |
|---|---:|---:|---:|---:|---:|
| blitz pin_missed | 998 | 43 | 1.403 | 3.31 | 0.42 |
| blitz hanging_missed | 998 | 54 | 1.522 | 2.61 | 0.58 |
| blitz discovered_attack_allowed | 998 | 54 | 1.522 | 2.30 | 0.66 |

Because the owner has so few cells in the window, the same query was run over all 13 dev users (9,686 analyzed games) for a larger sample:

| sample | cells in 30-60 window | median ratio | min | max | share above 1.5 | share below 0.5 |
|---|---:|---:|---:|---:|---:|---:|
| owner, tactic cells | 3 | 0.58 | 0.42 | 0.66 | 0% | 33% |
| all dev users, tactic cells | 20 | 0.68 | 0.08 | 1.55 | 5% | 35% |
| all dev users, context-tag cells | 49 | 1.12 | 0.07 | 5.85 | 41% | 14% |
| all dev users, combined | 69 | 1.00 | 0.07 | 5.85 | 30% | 20% |

The ratio depends on how many games the cell spans (the CI is in events per game; a fixed flaw count over more games gives a narrower per-100 interval):

| n_games in the cell | cells | median ratio |
|---|---:|---:|
| 0 to 99 | 29 | 1.81 |
| 100 to 299 | 23 | 1.01 |
| 300 to 999 | 16 | 0.42 |
| 1000 to 9999 | 1 | 0.08 |

**Rule outcome**: the combined typical ratio is 1.00 (tactic 0.68, context 1.12; owner tactic 0.58), inside the 0.5 to 1.5 band, so the rule says **keep the constant**.

**Recommended `LOW_SAMPLE_MIN_FLAWS = 40`** (unchanged). Caveat for the owner: a flaw-count threshold cannot track game count; cells over fewer than 100 games run a median ratio of 1.81 (CI wider than the band even above 40 flaws) while cells over 300 or more games run a median of 0.42, so 40 is a compromise, not a sharp boundary. Changing it would only trade one side for the other.

## What users will see move

Largest band shifts versus the live flaw registry (live = whole-cohort Lichess-eval basis, up to 1000 games per user; proposed = full-analysis lane, at most 100 games per user per TC). Width = `hi - lo`:

| metric | live lo / hi | proposed lo / hi | live width | proposed width | width ratio | lower edge moves | upper edge moves |
|---|---|---|---:|---:|---:|---:|---:|
| hasty | -0.28 / +0.18 | -1.16 / +0.45 | 0.46 | 1.61 | 3.5x | -0.88 | +0.27 |
| opening | -0.15 / +0.13 | -0.60 / +0.27 | 0.28 | 0.87 | 3.1x | -0.45 | +0.14 |
| reversed | -0.04 / +0.04 | -0.12 / +0.11 | 0.08 | 0.23 | 2.9x | -0.08 | +0.07 |
| miss | -0.11 / +0.11 | -0.32 / +0.28 | 0.22 | 0.60 | 2.7x | -0.21 | +0.17 |
| lucky | -0.09 / +0.09 | -0.23 / +0.26 | 0.18 | 0.49 | 2.7x | -0.14 | +0.17 |
| mistake | -0.23 / +0.20 | -0.66 / +0.39 | 0.43 | 1.05 | 2.4x | -0.43 | +0.19 |
| squandered | -0.07 / +0.08 | -0.17 / +0.19 | 0.15 | 0.36 | 2.4x | -0.10 | +0.11 |
| unrushed | -0.38 / +0.36 | -0.94 / +0.74 | 0.74 | 1.68 | 2.3x | -0.56 | +0.38 |
| blunder | -0.31 / +0.25 | -0.83 / +0.31 | 0.56 | 1.14 | 2.0x | -0.52 | +0.06 |
| middlegame | -0.27 / +0.23 | -0.62 / +0.35 | 0.50 | 0.97 | 1.9x | -0.35 | +0.12 |
| endgame_phase | -0.12 / +0.10 | -0.24 / +0.18 | 0.22 | 0.42 | 1.9x | -0.12 | +0.08 |
| low_clock | -0.08 / +0.03 | -0.12 / +0.05 | 0.11 | 0.17 | 1.5x | -0.04 | +0.02 |

- Every flaw band widens (1.5x to 3.5x). The widest relative changes are hasty (3.5x), opening (3.1x) and reversed (2.9x).
- On mistake, blunder, hasty and unrushed the lower edge moves out much more than the upper edge (last two columns), so the new bands are asymmetric around zero.
- Tactic tiles go from band-less to banded on 9 of 38 metrics; the other 29 keep the band-less presentation (blue dot, no verdict).
- Blitz and bullet users see the rapid band silently (D-09).

## Options for the owner (task 4)

- **accept**: plan 239-07 writes exactly the values above (12 flaw bands both zone TCs, 9 tactic bands, `LOW_SAMPLE_MIN_FLAWS = 40`, no Elo keying).
- **accept with edits**: name the edits, for example per-TC bands on hasty/opening (marginals above), dropping `low_clock` or `discovered_attack allowed` / `hanging missed` from the banded set, or a different constant.
- **hold**: keep current values and reopen the methodology (for example a shrinkage estimator). Phase pause: 239-07 and 239-09 are not started; 239-08 may still run with band-less tactic tables.

## Accepted

**Decision: accept with edits** (owner, 2026-10-13, at the plan 239-06 Task 4 checkpoint).

**Edit (the only one):** the 12 flaw bands are NOT widened. They keep today's live values for both zone TCs (rapid and classical), which is what plan 239-02 already carried forward into the per-zone-TC registry. Reason: the proposed widening (1.5x to 3.5x) is driven by sampling noise from the lane's 100-games-per-TC cap (noise-only IQR 70% to 142% of the observed IQR), so the new bands would mostly measure noise and rarely flag users with a few hundred analyzed games. The live bands came from the older ~1000-game basis and are less noise-inflated; this also follows the standing preference for editorial judgement over raw IQR when small effects matter.

Everything else is accepted as proposed:

- **Structure:** one pooled band per metric, shared by rapid and classical; blitz and bullet read the rapid band silently (D-08/D-09). No per-TC split for hasty/opening.
- **Elo keying:** none.
- **`LOW_SAMPLE_MIN_FLAWS`:** stays 40.

Final flaw registry (per 100 user moves; identical for rapid and classical; unchanged from live):

| metric | lo / hi |
|---|---|
| mistake | -0.23 / +0.20 |
| blunder | -0.31 / +0.25 |
| low_clock | -0.08 / +0.03 |
| hasty | -0.28 / +0.18 |
| unrushed | -0.38 / +0.36 |
| opening | -0.15 / +0.13 |
| middlegame | -0.27 / +0.23 |
| endgame_phase | -0.12 / +0.10 |
| miss | -0.11 / +0.11 |
| lucky | -0.09 / +0.09 |
| reversed | -0.04 / +0.04 |
| squandered | -0.07 / +0.08 |

Final tactic registry (per 100 games; identical for rapid and classical; has_zone true for exactly these 9, the other 29 stay `None`):

| family | side | lo / hi |
|---|---|---|
| fork | missed | -2.21 / +2.13 |
| fork | allowed | -4.12 / +3.23 |
| pin | missed | -1.42 / +1.89 |
| pin | allowed | -2.86 / +2.05 |
| discovered_attack | allowed | -1.24 / +1.06 |
| hanging | missed | -1.13 / +1.48 |
| hanging | allowed | -5.11 / +3.04 |
| mate | missed | -2.18 / +2.90 |
| mate | allowed | -7.00 / +4.09 |

Note for plan 239-07: the flaw registry values need no change (only verify they equal the table above); the tactic registry gets the 9 bands; no Elo keying code.
