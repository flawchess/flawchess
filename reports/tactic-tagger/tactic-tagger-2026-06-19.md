# FlawChess Tactic-Tagger Report

**Generated:** 2026-06-19 16:32:16Z (UTC)
**Detector:** `app/services/tactic_detector.py::detect_tactic_motif`
**Fixtures:** `fixtures/tagger/detector_fixture_{train,test}.csv` (CC0 lichess puzzles, deterministic PuzzleId-hash split)
**Train rows:** 11855 &nbsp;|&nbsp; **Test rows:** 5164

Scored with the same theme-intersection multi-label credit (D-10) as the CI harness `tests/scripts/tagger/test_detector_precision.py`. **TRAIN** is the floor-gated optimization set (what the `/loop` improves); **TEST** is held out for honest validation. A large train-beats-test precision gap (ΔP) means overfitting.

## Columns

| Column | Meaning |
|---|---|
| **T** | Dispatch tier: 1 mates (short-circuit, always win) → 2 geometric → 3 fuzzy/graded → 4 hanging-piece catch-all. Rows within a tier are in detector priority-rank order. |
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
| 1 | anastasia-mate | 0.822 | 0.857 | +0.034 | 1.000 | 1.000 | 458 | 227 | shipped |
| 1 | hook-mate | 0.840 | 0.841 | +0.001 | 0.931 | 0.943 | 568 | 247 | shipped |
| 1 | arabian-mate | NaN | NaN | — | 0.000 | 0.000 | 553 | 241 | suppressed |
| 1 | dovetail-mate | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | 544 | 230 | suppressed |
| 1 | boden-mate | NaN | NaN | — | 0.000 | 0.000 | 437 | 168 | suppressed |
| 1 | back-rank-mate | 0.281 | 0.271 | -0.010 | 0.998 | 0.997 | 856 | 342 | shipped |
| 1 | mate | 1.000 | 1.000 | +0.000 | 0.177 | 0.164 | 5727 | 2442 | shipped |
| 2 | fork | 0.437 | 0.400 | -0.038 | 0.782 | 0.768 | 1557 | 628 | shipped |
| 2 | skewer | 0.162 | 0.154 | -0.008 | 0.222 | 0.207 | 672 | 304 | shipped |
| 2 | pin | 0.440 | 0.439 | -0.000 | 0.279 | 0.271 | 1203 | 536 | shipped |
| 2 | discovered-attack | 0.200 | 0.205 | +0.005 | 0.217 | 0.225 | 1004 | 457 | shipped |
| 2 | double-check | 1.000 | 1.000 | +0.000 | 0.039 | 0.049 | 747 | 308 | shipped |
| 3 | deflection | 0.135 | 0.140 | +0.004 | 0.021 | 0.024 | 1177 | 501 | shipped |
| 3 | attraction | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | 1603 | 677 | suppressed |
| 3 | intermezzo | 0.000 | 0.500 | +0.500 | 0.000 | 0.003 | 702 | 324 | suppressed |
| 3 | x-ray | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | 642 | 274 | suppressed |
| 3 | interference | 1.000 | 1.000 | +0.000 | 0.035 | 0.054 | 596 | 257 | shipped |
| 3 | clearance | 0.419 | 0.833 | +0.414 | 0.018 | 0.045 | 725 | 334 | shipped |
| 3 | capturing-defender | 0.000 | NaN | — | 0.000 | 0.000 | 610 | 285 | suppressed |
| 3 | sacrifice | NaN | NaN | — | 0.000 | 0.000 | 3142 | 1377 | suppressed |
| 4 | hanging-piece | 0.990 | 0.952 | -0.037 | 0.132 | 0.131 | 734 | 306 | shipped |

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
| 1 | mate | 8169 | 399 / 1104 / 1440 / 1786 / 2786 | 2.1 | shipped |
| 2 | fork | 2185 | 403 / 1337 / 1682 / 2048 / 2897 | 1.1 | shipped |
| 2 | skewer | 976 | 562 / 1210 / 1622 / 2005 / 3094 | 2.8 | shipped |
| 2 | pin | 1739 | 572 / 1358 / 1724 / 2097 / 2978 | 0.7 | shipped |
| 2 | discovered-attack | 1461 | 617 / 1281 / 1695 / 2072 / 3094 | 1.9 | shipped |
| 2 | double-check | 1055 | 481 / 1294 / 1623 / 2002 / 2890 | 1.4 | shipped |
| 3 | deflection | 1678 | 617 / 1298 / 1726 / 2098 / 2985 | 2.3 | shipped |
| 3 | attraction | 2280 | 582 / 1421 / 1712 / 2062 / 2985 | – | suppressed |
| 3 | intermezzo | 1026 | 817 / 1274 / 1630 / 2010 / 3035 | – | suppressed |
| 3 | x-ray | 916 | 574 / 1258 / 1608 / 1966 / 2941 | – | suppressed |
| 3 | interference | 853 | 773 / 1223 / 1623 / 2011 / 3053 | 2.2 | shipped |
| 3 | clearance | 1059 | 582 / 1296 / 1707 / 2072 / 3053 | 2.0 | shipped |
| 3 | capturing-defender | 895 | 779 / 1224 / 1597 / 1990 / 2838 | – | suppressed |
| 3 | sacrifice | 4519 | 427 / 1406 / 1701 / 2059 / 3035 | – | suppressed |
| 4 | hanging-piece | 1040 | 404 / 1166 / 1566 / 1956 / 2913 | 0.0 | shipped |

**Overall fixture Rating (combined):** min 399 / Q1 1191 / Q2 1572 / Q3 1956 / max 3094.

**Depth-vs-Rating Pearson correlation** (combined correct detections, n=7753): 0.3238. Stored depth is the Phase 129 difficulty proxy, so this relationship is load-bearing.

## Summary & interpretation

- **Coverage:** 14 shipped (floor-gated) motifs, 8 suppressed (3 never fire, 5 fire only false positives). Micro-averaged TRAIN precision across all firing motifs: **0.465** (5428 TP / 6252 FP).
- **No overfit flagged:** every shipped motif holds train precision on the held-out test set within 0.10. Train gains are generalizing.
- **Lowest-precision shipped motif (train):** `deflection` (0.135). **Biggest false-positive source:** `back-rank-mate` (2182 FP) — over-fires relative to its base.
- **Difficulty is deliberately flat across tactics.** The fixtures are stratified by Rating band per motif-theme (`scripts/select_tagger_fixtures.py`), so per-motif min/Q1/Q2/Q3/max cluster near the overall spread. These reflect the *sampled* difficulty, NOT the natural lichess-population difficulty of each tactic.
- **Depth tracks difficulty** (global Pearson r=0.324): within the TP set, immediate motifs sit shallow (hanging-piece ≈ 0, fork/double-check ≈ 1) while mating nets run deeper. Stored depth feeds the Phase 129 difficulty filter.
- **`mate` recall looks low by design.** Generic mate is the catch-all under the named-mate subtypes, which win the min-depth dispatch — those puzzles are tagged correctly under their specific motif, so they count as `mate` false negatives here.
- **`pin` is the known weak point.** The pin relevance-gate has a parity bug and a depth-index mismatch tracked in **SEED-057** — fixing it needs a harness re-measure.

> Precision floors (`precision_floors.py`) are asserted on TRAIN only (D-08/D-09). TEST is held out — never used to set floors or tune detectors. The `/loop` optimizes TRAIN; judge real improvement by TEST and the ΔP overfit column.
