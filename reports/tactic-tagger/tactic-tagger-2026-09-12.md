# FlawChess Tactic-Tagger Report

**Generated:** 2026-09-12 22:25:53Z (UTC)
**Detector:** `app/services/tactic_detector.py::detect_tactic_motif`
**Fixtures:** `fixtures/tagger/detector_fixture_{train,test}.csv` (CC0 lichess puzzles, deterministic PuzzleId-hash split)
**Train rows:** 18632 &nbsp;|&nbsp; **Test rows:** 8017

Scored with the same theme-intersection multi-label credit (D-10) as the CI harness `tests/scripts/tagger/test_detector_precision.py`. **TRAIN** is the floor-gated optimization set (what the `/loop` improves); **TEST** is held out for honest validation. A large train-beats-test precision gap (ΔP) means overfitting.

## Columns

| Column | Meaning |
|---|---|
| **T** | Dispatch tier: 1 mates (short-circuit, always win) → 2 geometric → 3 fuzzy/graded → 4 hanging-piece catch-all → 5 move-type (en-passant/promotion/under-promotion, lowest tier — fires only when no real tactic does). Rows within a tier are in detector priority-rank order. |
| **P(train) / P(test)** | Precision = TP / (TP + FP) on each set. `NaN` = the detector never fired for this motif. |
| **ΔP** | P(test) − P(train). Near 0 = generalizes; strongly negative = overfit to train. |
| **R(train) / R(test)** | Recall = TP / (TP + FN) on each set. Printed for insight; NOT gated (under-tagging is acceptable, false positives are not — D-08). |
| **n(train) / n(test)** | Ground-truth count per set: puzzles whose lichess themes match this motif (the recall denominator). |
| **n_gt** | Combined (train+test) ground-truth puzzle count for this motif. |
| **min / Q1 / Q2 / Q3 / max** | Puzzle-Rating (difficulty) distribution over the combined `n_gt` ground-truth puzzles. Q2 is the median. |
| **TP depth** | Mean stored `tactic_depth` (half-moves into the refutation PV) on the correctly-detected train puzzles. |
| **Status** | `shipped` = floor-gated and surfaced; `suppressed` = excluded from the floor gate and query-suppressed via the `_TACTIC_CHIP_CONFIDENCE_MIN` lever. |

## Accuracy per tactic — train vs held-out test

| T | Motif | P(train) | P(test) | ΔP | R(train) | R(test) | n(train) | n(test) | Status |
|:--|:--|---:|---:|---:|---:|---:|---:|---:|:--|
| 1 | smothered-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 474 | 242 | shipped |
| 1 | anastasia-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 460 | 219 | shipped |
| 1 | hook-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 602 | 213 | shipped |
| 1 | arabian-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 537 | 251 | shipped |
| 1 | dovetail-mate | 1.000 | 1.000 | +0.000 | 0.996 | 1.000 | 524 | 249 | shipped |
| 1 | boden-mate | 1.000 | 1.000 | +0.000 | 0.995 | 1.000 | 444 | 161 | shipped |
| 1 | back-rank-mate | 1.000 | 1.000 | +0.000 | 0.997 | 0.997 | 894 | 359 | shipped |
| 1 | mate | 1.000 | 1.000 | +0.000 | 0.393 | 0.392 | 6474 | 2789 | shipped |
| 2 | fork | 0.998 | 1.000 | +0.002 | 0.577 | 0.581 | 2076 | 888 | shipped |
| 2 | skewer | 1.000 | 1.000 | +0.000 | 0.669 | 0.685 | 731 | 330 | shipped |
| 2 | pin | 0.998 | 1.000 | +0.002 | 0.656 | 0.672 | 1499 | 631 | shipped |
| 2 | double-check | 1.000 | 1.000 | +0.000 | 0.235 | 0.186 | 987 | 420 | shipped |
| 2 | discovered-check | 0.953 | 0.936 | -0.018 | 0.338 | 0.323 | 1997 | 857 | shipped |
| 2 | discovered-attack | 1.000 | 1.000 | +0.000 | 0.245 | 0.255 | 1888 | 839 | shipped |
| 2 | trapped-piece | 1.000 | 1.000 | +0.000 | 0.868 | 0.871 | 748 | 317 | shipped |
| 3 | deflection | 0.997 | 0.996 | -0.001 | 0.419 | 0.397 | 1504 | 632 | shipped |
| 3 | attraction | 1.000 | 1.000 | +0.000 | 0.469 | 0.467 | 1819 | 830 | shipped |
| 3 | intermezzo | 1.000 | 1.000 | +0.000 | 0.618 | 0.611 | 751 | 324 | shipped |
| 3 | x-ray | 1.000 | 1.000 | +0.000 | 0.415 | 0.399 | 650 | 268 | shipped |
| 3 | interference | 0.997 | 1.000 | +0.003 | 0.563 | 0.572 | 604 | 283 | shipped |
| 3 | clearance | NaN | NaN | — | 0.000 | 0.000 | 873 | 354 | suppressed |
| 3 | capturing-defender | 1.000 | 1.000 | +0.000 | 0.562 | 0.495 | 623 | 277 | shipped |
| 3 | sacrifice | 1.000 | 1.000 | +0.000 | 0.128 | 0.127 | 3570 | 1549 | shipped |
| 4 | hanging-piece | 1.000 | 1.000 | +0.000 | 0.736 | 0.725 | 857 | 374 | shipped |
| 5 | under-promotion | 1.000 | 1.000 | +0.000 | 0.308 | 0.322 | 780 | 332 | shipped |
| 5 | promotion | 1.000 | 1.000 | +0.000 | 0.472 | 0.469 | 3731 | 1630 | shipped |
| 5 | en-passant | 1.000 | 1.000 | +0.000 | 0.629 | 0.639 | 1960 | 845 | shipped |

## Difficulty distribution per tactic (combined train+test)

| T | Motif | n_gt | min / Q1 / Q2 / Q3 / max | TP depth | Status |
|:--|:--|---:|---|---:|:--|
| 1 | smothered-mate | 716 | 617 / 1097 / 1364 / 1648 / 2557 | 2.0 | shipped |
| 1 | anastasia-mate | 679 | 492 / 1064 / 1475 / 1712 / 2595 | 2.8 | shipped |
| 1 | hook-mate | 815 | 508 / 1194 / 1580 / 1978 / 2786 | 2.3 | shipped |
| 1 | arabian-mate | 788 | 443 / 1191 / 1585 / 1938 / 2762 | 2.8 | shipped |
| 1 | dovetail-mate | 773 | 725 / 1188 / 1555 / 1951 / 2775 | 1.7 | shipped |
| 1 | boden-mate | 605 | 399 / 992 / 1365 / 1683 / 2313 | 1.5 | shipped |
| 1 | back-rank-mate | 1253 | 399 / 955 / 1350 / 1755 / 2680 | 3.2 | shipped |
| 1 | mate | 9263 | 399 / 1100 / 1431 / 1770 / 2786 | 2.4 | shipped |
| 2 | fork | 2964 | 542 / 1332 / 1714 / 2078 / 2968 | 1.0 | shipped |
| 2 | skewer | 1061 | 565 / 1251 / 1625 / 2009 / 3094 | 3.2 | shipped |
| 2 | pin | 2130 | 445 / 1395 / 1749 / 2105 / 2958 | 1.0 | shipped |
| 2 | double-check | 1407 | 502 / 1305 / 1651 / 2022 / 2961 | 1.2 | shipped |
| 2 | discovered-check | 2854 | 502 / 1347 / 1697 / 2060 / 3075 | 1.3 | shipped |
| 2 | discovered-attack | 2727 | 571 / 1369 / 1710 / 2062 / 3094 | 2.3 | shipped |
| 2 | trapped-piece | 1065 | 686 / 1210 / 1608 / 2010 / 3159 | 2.7 | shipped |
| 3 | deflection | 2136 | 680 / 1387 / 1757 / 2117 / 3018 | 3.1 | shipped |
| 3 | attraction | 2649 | 430 / 1436 / 1755 / 2099 / 3120 | 0.7 | shipped |
| 3 | intermezzo | 1075 | 787 / 1296 / 1666 / 2068 / 3159 | 2.1 | shipped |
| 3 | x-ray | 918 | 686 / 1258 / 1604 / 1970 / 2966 | 3.0 | shipped |
| 3 | interference | 887 | 786 / 1219 / 1633 / 2029 / 3018 | 2.5 | shipped |
| 3 | clearance | 1227 | 689 / 1332 / 1756 / 2108 / 3015 | – | suppressed |
| 3 | capturing-defender | 900 | 597 / 1219 / 1610 / 1995 / 2975 | 2.6 | shipped |
| 3 | sacrifice | 5119 | 399 / 1426 / 1750 / 2105 / 3171 | 2.3 | shipped |
| 4 | hanging-piece | 1231 | 400 / 1179 / 1591 / 2002 / 3045 | 0.0 | shipped |
| 5 | under-promotion | 1112 | 635 / 1610 / 2100 / 2360 / 3053 | 2.8 | shipped |
| 5 | promotion | 5361 | 400 / 1249 / 1676 / 2124 / 3171 | 4.5 | shipped |
| 5 | en-passant | 2805 | 743 / 1580 / 1866 / 2169 / 3120 | 1.8 | shipped |

**Overall fixture Rating (combined):** min 399 / Q1 1246 / Q2 1628 / Q3 2015 / max 3171.

**Depth-vs-Rating Pearson correlation** (combined correct detections, n=26306): 0.2421. Stored depth is the Phase 129 difficulty proxy, so this relationship is load-bearing.

## Real-Game Gate (TAGFIX-07)

Hand-labelled sample of prod tags (~150 rows stratified by motif x orientation, frozen BEFORE any detector/gate predicate in this phase changed — D-13). Scored with the SAME scorer as the CI gate (`tests/scripts/tagger/test_detector_precision.py::_compute_realgame_metrics`), so the numbers here and the `REALGAME_REAL_SHARE_FLOOR` floor can never disagree.

Bucket semantics differ from the puzzle-fixture tables above: there is NO false-negative column. `surviving` = the row's stored motif is still detected by the current code; `real_surviving` = surviving AND labelled `real`; `suppressed` = the row's motif is no longer detected (a suppressed `incidental`/`wrong` row is a WIN, not a miss). `before_share` is the frozen label-only share (`before_real / before_total`, independent of any code change); `real_share` = `real_surviving / surviving` is the current-code measurement the never-regress floor asserts on.

The `missed`-orientation rows' board is built with the previous move pushed onto the stack (post-D-09 production behaviour), by design — see `tests/scripts/tagger/conftest.py::build_realgame_board`.

| Motif | before_n | before_share | surviving | real_surviving | suppressed | real_share |
|---|---:|---:|---:|---:|---:|---:|
| anastasia-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| arabian-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| attraction | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| back-rank-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| boden-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| capturing-defender | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| clearance | 16 | 0.438 | 0 | 0 | 16 | NaN |
| deflection | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| discovered-attack | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| discovered-check | 4 | 0.750 | 4 | 3 | 0 | 0.750 |
| double-bishop-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| double-check | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| dovetail-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| en-passant | 4 | 1.000 | 3 | 3 | 1 | 1.000 |
| fork | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| hanging-piece | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| hook-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| interference | 4 | 0.750 | 4 | 3 | 0 | 0.750 |
| intermezzo | 16 | 0.750 | 16 | 12 | 0 | 0.750 |
| mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| pin | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| promotion | 4 | 0.750 | 3 | 2 | 1 | 0.667 |
| sacrifice | 16 | 0.312 | 13 | 5 | 3 | 0.385 |
| self-interference | 4 | 0.750 | 0 | 0 | 4 | NaN |
| skewer | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| smothered-mate | 4 | 1.000 | 4 | 4 | 0 | 1.000 |
| trapped-piece | 4 | 0.750 | 4 | 3 | 0 | 0.750 |
| under-promotion | 4 | 0.750 | 4 | 3 | 0 | 0.750 |
| x-ray | 16 | 0.875 | 16 | 14 | 0 | 0.875 |

## Summary & interpretation

- **Coverage:** 26 shipped (floor-gated) motifs, 1 suppressed (1 never fire, 0 fire only false positives). Micro-averaged TRAIN precision across all firing motifs: **0.998** (18387 TP / 41 FP).
- **No overfit flagged:** every shipped motif holds train precision on the held-out test set within 0.10. Train gains are generalizing.
- **Lowest-precision shipped motif (train):** `discovered-check` (0.953). **Biggest false-positive source:** `discovered-check` (33 FP) — over-fires relative to its base.
- **Difficulty is deliberately flat across tactics.** The fixtures are stratified by Rating band per motif-theme (`scripts/select_tagger_fixtures.py`), so per-motif min/Q1/Q2/Q3/max cluster near the overall spread. These reflect the *sampled* difficulty, NOT the natural lichess-population difficulty of each tactic.
- **Depth tracks difficulty** (global Pearson r=0.242): within the TP set, immediate motifs sit shallow (hanging-piece ≈ 0, fork/double-check ≈ 1) while mating nets run deeper. Stored depth feeds the Phase 129 difficulty filter.
- **`mate` recall looks low by design.** Generic mate is the catch-all under the named-mate subtypes, which win the min-depth dispatch — those puzzles are tagged correctly under their specific motif, so they count as `mate` false negatives here.
- **`pin` now ships at >0.93 precision.** Phase 131 restricted the pin scan to the boards that follow a winning-side move (the cook node set) instead of every PV board, removing the incidental pins that fired inside opponent forcing lines (0.819 -> 0.944 TEST).

> Precision floors (`precision_floors.py`) are asserted on TRAIN only (D-08/D-09). TEST is held out — never used to set floors or tune detectors. The `/loop` optimizes TRAIN; judge real improvement by TEST and the ΔP overfit column.
