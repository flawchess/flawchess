"""Precision/recall harness for the Phase 127 tactic-motif detector (SC#2/D-08).

Scores `detect_tactic_motif` against the committed CC0 lichess puzzle fixtures
(fixtures/tagger/detector_fixture_train.csv and detector_fixture_test.csv).
Computes per-motif precision AND recall, plus the depth-vs-puzzle-Rating Pearson
correlation, and asserts a hard precision floor per shipped motif on the TRAIN set.

Train/test (anti-overfitting): floors are asserted on TRAIN only — the set the
self-improvement loop optimizes. The held-out TEST set is scored and printed
(including a train->test precision delta per motif) but NOT asserted, so a large
train-beats-test gap surfaces overfitting in CI output without blocking. Both sets
come from a deterministic PuzzleId-hash split (no leakage).

Precision gate (D-08): `assert precision_train[motif] >= PRECISION_FLOOR[motif]` for
each shipped (non-suppressed) motif. The test FAILS if train precision drops below
the floor — this blocks a CI merge if the detector regresses. Recall is printed but
never asserted (under-tagging is acceptable; false positives are not).

These numbers supersede the self-labeled fixtures in
`tests/services/test_tactic_detector.py` as the authoritative precision/recall
source (D-12 / SC#5). The fast-guard tests in that file remain as per-commit
regression guards (see Task 2 note in 127-03-PLAN.md).

CC0 / AGPL boundary (SC#4 / D-11):
  The puzzle data in the fixture CSVs is CC0 / Public Domain from
  database.lichess.org. The puzzle labels were produced by lichess-puzzler's
  tagger/cook.py (AGPL-3.0). We use only the published CC0 dataset; cook.py
  is neither vendored nor ported here. The Phase 124 detector was built from
  plain-English pseudocode, independent of cook.py.

Precision multi-label credit (D-10):
  A detection is a true positive when the detected motif's lichess theme set
  (from MOTIF_TO_THEMES in motif_theme_map.py) intersects the puzzle's Themes.
  A single puzzle can carry multiple themes; intersection credit handles this.

Depth-vs-Rating correlation (D-06):
  Pearson correlation between tactic_depth and puzzle Rating for rows where we
  detected a motif correctly. Reported as a first-class output. A correlation
  near 0 indicates depth is not tracking puzzle difficulty; the Phase 129 depth
  filter presets rely on this relationship.

Unvalidated motifs (D-10 / UNVALIDATED_MOTIFS):
  Motifs with no confirmed lichess theme equivalent are printed as 'unvalidated'
  in the output table. Their precision cannot be measured against the CC0 set.

Suppressed motifs (D-09 / SUPPRESSED_MOTIFS):
  Motifs excluded from the floor assertion: either they never fire (NaN precision)
  or have zero precision. Tier-3 suppressed motifs are filtered at query time via
  the `_TACTIC_CHIP_CONFIDENCE_MIN` lever in library_repository.py.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict

import pytest

from app.services.tactic_detector import _INT_TO_MOTIF, detect_tactic_motif
from tests.scripts.tagger.conftest import PuzzleRow, build_detector_board
from tests.scripts.tagger.motif_theme_map import MOTIF_TO_THEMES, UNVALIDATED_MOTIFS
from tests.scripts.tagger.precision_floors import PRECISION_FLOOR, SUPPRESSED_MOTIFS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_metrics(
    rows: list[PuzzleRow],
) -> tuple[
    dict[str, int],  # tp_count
    dict[str, int],  # fp_count
    dict[str, int],  # fn_count
    list[tuple[int, int]],  # (depth, rating) for correct detections
]:
    """Score the detector against all fixture rows.

    Returns per-motif TP/FP/FN counts and (depth, rating) pairs for correct
    detections with known depth.
    """
    tp_count: dict[str, int] = defaultdict(int)
    fp_count: dict[str, int] = defaultdict(int)
    fn_count: dict[str, int] = defaultdict(int)

    depth_rating_pairs: list[tuple[int, int]] = []

    for row in rows:
        # Build the board the SAME way production calls the detector (flaw move on the move
        # stack), so the floor gate verifies the detector identically to production.
        board = build_detector_board(row)
        motif_int, _piece, _confidence, depth = detect_tactic_motif(board, row["pv"])
        detected_motif = _INT_TO_MOTIF.get(motif_int) if motif_int is not None else None

        puzzle_themes = set(row["themes"])

        for motif_str, lichess_themes in MOTIF_TO_THEMES.items():
            if motif_str in UNVALIDATED_MOTIFS:
                continue
            has_theme = any(t in puzzle_themes for t in lichess_themes)
            we_detected = detected_motif == motif_str

            if has_theme and we_detected:
                tp_count[motif_str] += 1
                # Track depth-vs-Rating for correct detections (D-06)
                if depth is not None:
                    depth_rating_pairs.append((depth, row["rating"]))
            elif has_theme and not we_detected:
                fn_count[motif_str] += 1
            elif not has_theme and we_detected:
                fp_count[motif_str] += 1

    return tp_count, fp_count, fn_count, depth_rating_pairs


def _precision(tp: int, fp: int) -> float:
    """Precision = TP / (TP + FP). Returns NaN when no predictions."""
    return tp / (tp + fp) if (tp + fp) > 0 else float("nan")


def _recall(tp: int, fn: int) -> float:
    """Recall = TP / (TP + FN). Returns NaN when no ground-truth positives."""
    return tp / (tp + fn) if (tp + fn) > 0 else float("nan")


# ---------------------------------------------------------------------------
# Per-set scoring + printing
# ---------------------------------------------------------------------------


def _print_set_table(
    label: str,
    rows: list[PuzzleRow],
    assert_floors: bool,
) -> tuple[dict[str, float], list[str]]:
    """Score one fixture set, print its per-motif table, and return.

    Returns (precision_by_motif, floor_failures). `floor_failures` is always empty
    when `assert_floors` is False (the held-out TEST set is never gated).
    """
    tp, fp, fn, depth_rating_pairs = _compute_metrics(rows)
    validated_motifs = sorted(m for m in MOTIF_TO_THEMES if m not in UNVALIDATED_MOTIFS)

    col_w = 22
    print()
    print("=" * 80)
    print(f"TAGGER PRECISION / RECALL — {label} SET ({len(rows)} rows)")
    print("=" * 80)
    header = (
        f"{'Motif':<{col_w}} "
        f"{'TP':>5} {'FP':>5} {'FN':>5}  "
        f"{'Precision':>10}  {'Recall':>10}  "
        f"{'Floor':>8}  Status"
    )
    print(header)
    print("-" * len(header))

    precision_by_motif: dict[str, float] = {}
    floor_failures: list[str] = []

    for motif in validated_motifs:
        tp_m, fp_m, fn_m = tp[motif], fp[motif], fn[motif]
        prec = _precision(tp_m, fp_m)
        rec = _recall(tp_m, fn_m)
        precision_by_motif[motif] = prec

        if motif in SUPPRESSED_MOTIFS:
            floor_str, status = "suppressed", "SUPPRESSED"
        elif motif in PRECISION_FLOOR:
            floor_val = PRECISION_FLOOR[motif]
            floor_str = f"{floor_val:.3f}"
            if math.isnan(prec):
                status = "NO-PREDS"
            elif prec >= floor_val:
                status = "PASS"
            else:
                status = "FAIL"
                if assert_floors:
                    floor_failures.append(
                        f"  {motif}: measured {prec:.3f} < floor {floor_val:.3f}"
                        f" (TP={tp_m}, FP={fp_m})"
                    )
        else:
            floor_str, status = "—", "—"

        prec_str = f"{prec:.3f}" if not math.isnan(prec) else "NaN"
        rec_str = f"{rec:.3f}" if not math.isnan(rec) else "NaN"
        print(
            f"{motif:<{col_w}} "
            f"{tp_m:>5} {fp_m:>5} {fn_m:>5}  "
            f"{prec_str:>10}  {rec_str:>10}  "
            f"{floor_str:>8}  {status}"
        )

    # Depth-vs-Rating correlation (D-06 first-class output)
    print()
    if len(depth_rating_pairs) >= 2:
        try:
            corr = statistics.correlation(
                [d for d, _ in depth_rating_pairs],
                [r for _, r in depth_rating_pairs],
            )
            print(
                f"Depth-vs-Rating Pearson correlation ({label}, "
                f"n={len(depth_rating_pairs)}): {corr:.4f}"
            )
        except statistics.StatisticsError as exc:
            print(f"Depth-vs-Rating correlation ({label}): could not compute — {exc}")
    else:
        print(f"Depth-vs-Rating correlation ({label}): insufficient data")

    return precision_by_motif, floor_failures


# ---------------------------------------------------------------------------
# Harness test
# ---------------------------------------------------------------------------


def test_detector_precision_and_recall(
    detector_fixture_train: list[PuzzleRow],
    detector_fixture_test: list[PuzzleRow],
) -> None:
    """Score the detector on TRAIN (floor-gated) and TEST (held out, not gated).

    Prints a per-motif table for each set, the depth-vs-Rating correlation, and a
    train->test precision delta (the overfit signal). Asserts PRECISION_FLOOR only
    against the TRAIN set per D-08; recall is printed but never asserted.
    """
    prec_train, floor_failures = _print_set_table(
        "TRAIN", detector_fixture_train, assert_floors=True
    )
    prec_test, _ = _print_set_table("TEST", detector_fixture_test, assert_floors=False)

    # --- Overfit signal: train -> test precision delta per shipped motif ---
    print()
    print("=" * 80)
    print("OVERFIT CHECK — train -> test precision delta (held-out, not gated)")
    print("=" * 80)
    print(f"{'Motif':<22} {'train':>8} {'test':>8} {'Δ(test-train)':>14}")
    print("-" * 54)
    for motif in sorted(m for m in MOTIF_TO_THEMES if m not in UNVALIDATED_MOTIFS):
        if motif in SUPPRESSED_MOTIFS:
            continue
        pt, pv = prec_train.get(motif, float("nan")), prec_test.get(motif, float("nan"))
        if math.isnan(pt) and math.isnan(pv):
            continue
        delta = pv - pt if not (math.isnan(pt) or math.isnan(pv)) else float("nan")
        pt_s = f"{pt:.3f}" if not math.isnan(pt) else "NaN"
        pv_s = f"{pv:.3f}" if not math.isnan(pv) else "NaN"
        d_s = f"{delta:+.3f}" if not math.isnan(delta) else "—"
        print(f"{motif:<22} {pt_s:>8} {pv_s:>8} {d_s:>14}")

    # --- Unvalidated motifs ---
    print()
    print("Unvalidated motifs (no lichess theme equivalent — D-10):")
    for motif in sorted(UNVALIDATED_MOTIFS):
        print(f"  {motif}")
    print("=" * 80)

    # --- Precision floor assertions (D-08 gate, TRAIN only) ---
    if floor_failures:
        failure_text = "\n".join(floor_failures)
        pytest.fail(
            f"TRAIN precision floor(s) not met (D-08 gate — fix detector or lower floor "
            f"with a documented measurement):\n{failure_text}"
        )
