# FlawChess Tactic-Tagger Report

**Generated:** 2026-06-22 21:43:09Z (UTC)
**Detector:** `app/services/tactic_detector.py::detect_tactic_motif`
**Fixtures:** `fixtures/tagger/detector_fixture_{train,test}.csv` (CC0 lichess puzzles, deterministic PuzzleId-hash split)
**Train rows:** 11855 &nbsp;|&nbsp; **Test rows:** 5164

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
| 1 | smothered-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 468 | 233 | shipped |
| 1 | anastasia-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 458 | 227 | shipped |
| 1 | hook-mate | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | 568 | 247 | shipped |
| 1 | arabian-mate | NaN | NaN | — | 0.000 | 0.000 | 553 | 241 | suppressed |
| 1 | dovetail-mate | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | 544 | 230 | suppressed |
| 1 | boden-mate | NaN | NaN | — | 0.000 | 0.000 | 437 | 168 | suppressed |
| 1 | back-rank-mate | 1.000 | 1.000 | +0.000 | 0.998 | 0.997 | 856 | 342 | shipped |
| 1 | mate | 1.000 | 1.000 | +0.000 | 0.586 | 0.567 | 5727 | 2442 | shipped |
| 2 | fork | 1.000 | 0.998 | -0.002 | 0.650 | 0.654 | 1557 | 628 | shipped |
| 2 | skewer | 1.000 | 1.000 | +0.000 | 0.661 | 0.638 | 672 | 304 | shipped |
| 2 | pin | 0.934 | 0.944 | +0.010 | 0.581 | 0.601 | 1203 | 536 | shipped |
| 2 | double-check | 1.000 | 1.000 | +0.000 | 0.224 | 0.214 | 747 | 308 | shipped |
| 2 | discovered-check | 0.913 | 0.884 | -0.030 | 0.095 | 0.096 | 1004 | 397 | shipped |
| 2 | discovered-attack | 0.995 | 1.000 | +0.005 | 0.411 | 0.414 | 1004 | 457 | shipped |
| 2 | trapped-piece | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | 28 | 11 | suppressed |
| 3 | deflection | 0.235 | 0.210 | -0.025 | 0.258 | 0.238 | 1177 | 501 | shipped |
| 3 | attraction | 0.060 | 0.043 | -0.017 | 0.016 | 0.012 | 1603 | 677 | suppressed |
| 3 | intermezzo | 0.100 | 0.167 | +0.067 | 0.003 | 0.006 | 702 | 324 | suppressed |
| 3 | x-ray | 0.033 | 0.000 | -0.033 | 0.002 | 0.000 | 642 | 274 | suppressed |
| 3 | interference | 0.990 | 1.000 | +0.010 | 0.169 | 0.202 | 596 | 257 | shipped |
| 3 | clearance | 0.348 | 0.371 | +0.023 | 0.090 | 0.138 | 725 | 334 | shipped |
| 3 | capturing-defender | 0.240 | 0.250 | +0.010 | 0.010 | 0.014 | 610 | 285 | suppressed |
| 3 | sacrifice | NaN | NaN | — | 0.000 | 0.000 | 3142 | 1377 | suppressed |
| 4 | hanging-piece | 0.910 | 0.885 | -0.025 | 0.688 | 0.706 | 734 | 306 | shipped |
| 5 | under-promotion | NaN | NaN | — | 0.000 | 0.000 | 4 | 4 | suppressed |
| 5 | promotion | 1.000 | 1.000 | +0.000 | 0.039 | 0.016 | 180 | 61 | shipped |
| 5 | en-passant | NaN | NaN | — | 0.000 | 0.000 | 12 | 7 | suppressed |

## Difficulty distribution per tactic (combined train+test)

| T | Motif | n_gt | min / Q1 / Q2 / Q3 / max | TP depth | Status |
|:--|:--|---:|---|---:|:--|
| 1 | smothered-mate | 701 | 598 / 1098 / 1377 / 1649 / 2557 | 1.9 | shipped |
| 1 | anastasia-mate | 685 | 474 / 1039 / 1481 / 1715 / 2595 | 2.9 | shipped |
| 1 | hook-mate | 815 | 505 / 1194 / 1592 / 1988 / 2786 | 2.3 | shipped |
| 1 | arabian-mate | 794 | 400 / 1189 / 1558 / 1951 / 2762 | – | suppressed |
| 1 | dovetail-mate | 774 | 669 / 1191 / 1549 / 1937 / 2775 | – | suppressed |
| 1 | boden-mate | 605 | 399 / 974 / 1394 / 1683 / 2313 | – | suppressed |
| 1 | back-rank-mate | 1198 | 399 / 994 / 1357 / 1747 / 2680 | 3.3 | shipped |
| 1 | mate | 8169 | 399 / 1104 / 1440 / 1786 / 2786 | 2.3 | shipped |
| 2 | fork | 2185 | 403 / 1337 / 1682 / 2048 / 2897 | 1.1 | shipped |
| 2 | skewer | 976 | 562 / 1210 / 1622 / 2005 / 3094 | 3.0 | shipped |
| 2 | pin | 1739 | 572 / 1358 / 1724 / 2097 / 2978 | 0.9 | shipped |
| 2 | double-check | 1055 | 481 / 1294 / 1623 / 2002 / 2890 | 0.9 | shipped |
| 2 | discovered-check | 1401 | 481 / 1331 / 1712 / 2091 / 2890 | 0.0 | shipped |
| 2 | discovered-attack | 1461 | 617 / 1281 / 1695 / 2072 / 3094 | 1.3 | shipped |
| 2 | trapped-piece | 39 | 1048 / 1460 / 1685 / 2169 / 2751 | – | suppressed |
| 3 | deflection | 1678 | 617 / 1298 / 1726 / 2098 / 2985 | 2.9 | shipped |
| 3 | attraction | 2280 | 582 / 1421 / 1712 / 2062 / 2985 | 1.5 | suppressed |
| 3 | intermezzo | 1026 | 817 / 1274 / 1630 / 2010 / 3035 | 5.0 | suppressed |
| 3 | x-ray | 916 | 574 / 1258 / 1608 / 1966 / 2941 | 8.0 | suppressed |
| 3 | interference | 853 | 773 / 1223 / 1623 / 2011 / 3053 | 2.5 | shipped |
| 3 | clearance | 1059 | 582 / 1296 / 1707 / 2072 / 3053 | 2.3 | shipped |
| 3 | capturing-defender | 895 | 779 / 1224 / 1597 / 1990 / 2838 | 2.7 | suppressed |
| 3 | sacrifice | 4519 | 427 / 1406 / 1701 / 2059 / 3035 | – | suppressed |
| 4 | hanging-piece | 1040 | 404 / 1166 / 1566 / 1956 / 2913 | 0.0 | shipped |
| 5 | under-promotion | 8 | 1754 / 2102 / 2200 / 2293 / 2671 | – | suppressed |
| 5 | promotion | 241 | 670 / 1214 / 1651 / 2101 / 2842 | 0.0 | shipped |
| 5 | en-passant | 19 | 1564 / 1834 / 2097 / 2366 / 2859 | – | suppressed |

**Overall fixture Rating (combined):** min 399 / Q1 1191 / Q2 1572 / Q3 1956 / max 3094.

**Depth-vs-Rating Pearson correlation** (combined correct detections, n=13651): 0.3210. Stored depth is the Phase 129 difficulty proxy, so this relationship is load-bearing.

## Summary & interpretation

- **Coverage:** 16 shipped (floor-gated) motifs, 11 suppressed (5 never fire, 2 fire only false positives). Micro-averaged TRAIN precision across all firing motifs: **0.836** (9551 TP / 1879 FP).
- **No overfit flagged:** every shipped motif holds train precision on the held-out test set within 0.10. Train gains are generalizing.
- **Lowest-precision shipped motif (train):** `deflection` (0.235). **Biggest false-positive source:** `deflection` (991 FP) — over-fires relative to its base.
- **Difficulty is deliberately flat across tactics.** The fixtures are stratified by Rating band per motif-theme (`scripts/select_tagger_fixtures.py`), so per-motif min/Q1/Q2/Q3/max cluster near the overall spread. These reflect the *sampled* difficulty, NOT the natural lichess-population difficulty of each tactic.
- **Depth tracks difficulty** (global Pearson r=0.321): within the TP set, immediate motifs sit shallow (hanging-piece ≈ 0, fork/double-check ≈ 1) while mating nets run deeper. Stored depth feeds the Phase 129 difficulty filter.
- **`mate` recall looks low by design.** Generic mate is the catch-all under the named-mate subtypes, which win the min-depth dispatch — those puzzles are tagged correctly under their specific motif, so they count as `mate` false negatives here.
- **`pin` now ships at >0.93 precision.** Phase 131 restricted the pin scan to the boards that follow a winning-side move (the cook node set) instead of every PV board, removing the incidental pins that fired inside opponent forcing lines (0.819 -> 0.944 TEST).

> Precision floors (`precision_floors.py`) are asserted on TRAIN only (D-08/D-09). TEST is held out — never used to set floors or tune detectors. The `/loop` optimizes TRAIN; judge real improvement by TEST and the ΔP overfit column.
