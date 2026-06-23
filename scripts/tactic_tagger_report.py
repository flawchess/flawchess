"""Generate the FlawChess tactic-tagger precision/recall + difficulty report.

Scores `detect_tactic_motif` (app/services/tactic_detector.py) against the committed
CC0 lichess puzzle fixtures (fixtures/tagger/detector_fixture_{train,test}.csv) and
writes a timestamped markdown report to reports/tactic-tagger/tactic-tagger-YYYY-MM-DD.md
with train-vs-held-out-test accuracy so overfitting is visible.

The report reuses the Phase 127 validation-harness modules as the single source of
truth for the motif->theme map, the unvalidated set, and the precision floors:
  - tests.scripts.tagger.conftest._load_split
  - tests.scripts.tagger.motif_theme_map.MOTIF_TO_THEMES / UNVALIDATED_MOTIFS
  - tests.scripts.tagger.precision_floors.SUPPRESSED_MOTIFS

This is read-only: no DB, no network. Same scoring (theme-intersection multi-label
credit, D-10) as tests/scripts/tagger/test_detector_precision.py, so the precision /
recall / TP / FP / FN numbers match the CI harness exactly.

Usage:
    uv run python scripts/tactic_tagger_report.py
    PYTHONPATH=. uv run python scripts/tactic_tagger_report.py   # if tests/ not on path

Goal-seeking mode (for `/loop` self-improvement):
    PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals
  Writes the report AND evaluates the per-motif GOALS table below. Exits 0 when
  every goal is met (the loop should STOP), exits 1 when any goal is unmet (the
  loop should fix the worst offender and re-run). The printed "NEXT" line names the
  single highest-leverage motif to work on next.
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import chess

from app.services.tactic_detector import _INT_TO_MOTIF, detect_tactic_motif
from tests.scripts.tagger.conftest import PuzzleRow, _load_split
from tests.scripts.tagger.motif_theme_map import MOTIF_TO_THEMES, UNVALIDATED_MOTIFS
from tests.scripts.tagger.precision_floors import SUPPRESSED_MOTIFS

# Dispatch tier + intra-tier priority order, mirroring detect_tactic_motif's
# registries (Tier 1 mates dominate -> 2 geometric -> 3 fuzzy -> 4 hanging-piece
# catch-all -> 5 move-type). Rows within a tier are listed in detector priority-rank
# order (the rank comments on _GEOMETRIC_REGISTRY / _MOVE_TYPE_REGISTRY in
# tactic_detector.py — keep this in sync when a registry rank changes).
_TIER_ORDER: list[tuple[int, list[str]]] = [
    (
        1,
        [
            "smothered-mate",
            "anastasia-mate",
            "hook-mate",
            "arabian-mate",
            "dovetail-mate",
            "boden-mate",
            "back-rank-mate",
            "mate",
        ],
    ),
    # Tier 2 in _GEOMETRIC_REGISTRY rank order (Phase 128.1-01 added discovered-check
    # rank 4 and trapped-piece rank 6).
    (
        2,
        [
            "fork",
            "skewer",
            "pin",
            "double-check",
            "discovered-check",
            "discovered-attack",
            "trapped-piece",
        ],
    ),
    (
        3,
        [
            "deflection",
            "attraction",
            "intermezzo",
            "x-ray",
            "interference",
            "clearance",
            "capturing-defender",
            "sacrifice",
        ],
    ),
    (4, ["hanging-piece"]),
    # Tier 5 move-type family in _MOVE_TYPE_REGISTRY rank order (Phase 128.1-02).
    (5, ["under-promotion", "promotion", "en-passant"]),
]

_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "tactic-tagger"

# ---------------------------------------------------------------------------
# Improvement GOALS (the /loop target). EDIT THESE to set the bar.
# ---------------------------------------------------------------------------
# These are ASPIRATIONAL targets that drive the self-improvement loop — distinct
# from tests/scripts/tagger/precision_floors.py, which are the "never regress below
# the last measured value" CI floors (D-09). Goals say "get BETTER to here"; floors
# say "don't get WORSE than here".
#
# A goal applies to a shipped (non-suppressed) motif. For each goal motif the loop
# must reach BOTH the precision and the recall target. Set a target to None to skip
# that dimension for that motif (e.g. generic `mate` recall is structurally low
# because named-mate subtypes win the dispatch — gating its recall is meaningless).
#
# Defaults below are precision-first (false positives are what hurt tag trust) with
# modest recall, and are intentionally reachable-but-not-trivial. Tune to taste; the
# loop stops the moment every goal here is satisfied.
GoalSpec = dict[str, float | None]
GOALS: dict[str, GoalSpec] = {
    # tier 1 — mates (mostly already strong; lock them in, no regressions)
    "smothered-mate": {"precision": 0.95, "recall": 0.90},
    # Phase 131 D-11: raise to 0.90 precision (anastasia/hook already near-there;
    # back-rank is the hard case — overfires badly at 0.27 TEST precision)
    "anastasia-mate": {"precision": 0.90, "recall": 0.90},
    "hook-mate": {"precision": 0.90, "recall": 0.85},
    "back-rank-mate": {"precision": 0.90, "recall": 0.90},
    "mate": {"precision": 0.95, "recall": None},
    # tier 2 — geometric workhorses (the main improvement surface)
    # Phase 131 D-11: all four raised to 0.90 precision (current TEST baselines:
    # fork 0.448, skewer 0.210, pin 0.472, discovered-attack 0.217)
    "fork": {"precision": 0.90, "recall": 0.60},
    "skewer": {"precision": 0.90, "recall": 0.30},
    "pin": {"precision": 0.90, "recall": 0.40},
    "discovered-attack": {"precision": 0.90, "recall": 0.30},
    "double-check": {"precision": 0.90, "recall": None},
    # tier 3 — Tier-3 in-scope motifs raised to 0.90 precision per Phase 132 D-01
    # (precision-first, recall explicitly ungated this phase). Six motifs targeted:
    # deflection (was 0.50), clearance (was 0.70), and four previously absent from
    # GOALS: capturing-defender, attraction, intermezzo, x-ray.
    # interference is the regression lock (0.986 TEST after Phase 132-04) — DO NOT raise.
    # attraction: SUPPRESSED (Phase 132-04, D-03 cutoff — 0 TP on TRAIN after cook port).
    # sacrifice: SUPPRESSED (Phase 132-04 — structural co-tag issue, never wins dispatch).
    # x-ray: SHIPPED (Phase 132-04 — 1.000 TRAIN / 1.000 TEST; goal satisfied and held).
    "deflection": {"precision": 0.90, "recall": None},
    "clearance": {"precision": 0.90, "recall": None},
    "capturing-defender": {"precision": 0.90, "recall": None},
    "intermezzo": {"precision": 0.90, "recall": None},
    "x-ray": {"precision": 0.90, "recall": None},
    "interference": {"precision": 0.80, "recall": None},
    "hanging-piece": {"precision": 0.90, "recall": None},
    # Phase 128.1-01 new Tier-2 real-geometry motifs (aspirational, precision-first)
    # discovered-check: TRAIN 0.880 — goal is to hold or exceed the current value
    "discovered-check": {"precision": 0.85, "recall": None},
    # trapped-piece: SUPPRESSED (only-FP in harness) — exclude from GOALS; its
    # precision is driven by the D-06 strict gate, not a detector-tuning loop.
}


class MotifStats:
    """Per-motif scoring + ground-truth difficulty distribution."""

    def __init__(self, motif: str) -> None:
        self.motif = motif
        self.tp = 0
        self.fp = 0
        self.fn = 0
        self.gt_ratings: list[int] = []  # ratings of ground-truth-themed puzzles
        self.tp_ratings: list[int] = []  # ratings of correctly-detected puzzles
        self.tp_depths: list[int] = []  # stored depth on correct detections

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else float("nan")

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else float("nan")


def _quantile(values: list[int], frac: float) -> float:
    """Linear-interpolated quantile (matches numpy default 'linear')."""
    if not values:
        return float("nan")
    ordered = sorted(values)
    idx = frac * (len(ordered) - 1)
    low = int(idx)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (idx - low)


def _score(rows: list[PuzzleRow]) -> tuple[dict[str, MotifStats], list[tuple[int, int]]]:
    """Score the detector against every fixture row.

    Returns per-motif stats and the (depth, rating) pairs for all correct
    detections with a known depth (the depth-vs-Rating correlation basis, D-06).
    """
    stats: dict[str, MotifStats] = {
        m: MotifStats(m) for m in MOTIF_TO_THEMES if m not in UNVALIDATED_MOTIFS
    }
    depth_rating_pairs: list[tuple[int, int]] = []

    for row in rows:
        board = chess.Board(row["fen"])
        motif_int, _piece, _confidence, depth = detect_tactic_motif(board, row["pv"])
        detected = _INT_TO_MOTIF.get(motif_int) if motif_int is not None else None
        puzzle_themes = set(row["themes"])

        for motif, lichess_themes in MOTIF_TO_THEMES.items():
            if motif in UNVALIDATED_MOTIFS:
                continue
            has_theme = any(t in puzzle_themes for t in lichess_themes)
            we_detected = detected == motif
            s = stats[motif]
            if has_theme:
                s.gt_ratings.append(row["rating"])
            if has_theme and we_detected:
                s.tp += 1
                s.tp_ratings.append(row["rating"])
                if depth is not None:
                    s.tp_depths.append(depth)
                    depth_rating_pairs.append((depth, row["rating"]))
            elif has_theme and not we_detected:
                s.fn += 1
            elif we_detected and not has_theme:
                s.fp += 1

    return stats, depth_rating_pairs


def _fmt(value: float, places: int = 3) -> str:
    return f"{value:.{places}f}" if not math.isnan(value) else "NaN"


def _status(motif: str) -> str:
    return "suppressed" if motif in SUPPRESSED_MOTIFS else "shipped"


def _build_report(
    train_rows: list[PuzzleRow],
    test_rows: list[PuzzleRow],
    generated: datetime,
) -> str:
    train, _ = _score(train_rows)
    test, _ = _score(test_rows)
    combined, depth_rating_pairs = _score(train_rows + test_rows)
    all_ratings = [r["rating"] for r in train_rows + test_rows]

    lines: list[str] = []
    lines.append("# FlawChess Tactic-Tagger Report")
    lines.append("")
    lines.append(f"**Generated:** {generated.strftime('%Y-%m-%d %H:%M:%SZ')} (UTC)")
    lines.append("**Detector:** `app/services/tactic_detector.py::detect_tactic_motif`")
    lines.append(
        "**Fixtures:** `fixtures/tagger/detector_fixture_{train,test}.csv` "
        "(CC0 lichess puzzles, deterministic PuzzleId-hash split)"
    )
    lines.append(f"**Train rows:** {len(train_rows)} &nbsp;|&nbsp; **Test rows:** {len(test_rows)}")
    lines.append("")
    lines.append(
        "Scored with the same theme-intersection multi-label credit (D-10) as the CI "
        "harness `tests/scripts/tagger/test_detector_precision.py`. **TRAIN** is the "
        "floor-gated optimization set (what the `/loop` improves); **TEST** is held out for "
        "honest validation. A large train-beats-test precision gap (ΔP) means overfitting."
    )
    lines.append("")

    # --- Column legend ---
    lines.append("## Columns")
    lines.append("")
    lines.append("| Column | Meaning |")
    lines.append("|---|---|")
    lines.append(
        "| **T** | Dispatch tier: 1 mates (short-circuit, always win) → 2 geometric → "
        "3 fuzzy/graded → 4 hanging-piece catch-all → 5 move-type "
        "(en-passant/promotion/under-promotion, lowest tier — fires only when no real "
        "tactic does). Rows within a tier are in detector priority-rank order. |"
    )
    lines.append(
        "| **P(train) / P(test)** | Precision = TP / (TP + FP) on each set. `NaN` = the "
        "detector never fired for this motif. |"
    )
    lines.append(
        "| **ΔP** | P(test) − P(train). Near 0 = generalizes; strongly negative = overfit "
        "to train. |"
    )
    lines.append(
        "| **R(train) / R(test)** | Recall = TP / (TP + FN) on each set. Printed for insight; "
        "NOT gated (under-tagging is acceptable, false positives are not — D-08). |"
    )
    lines.append(
        "| **n(train) / n(test)** | Ground-truth count per set: puzzles whose lichess themes "
        "match this motif (the recall denominator). |"
    )
    lines.append("| **n_gt** | Combined (train+test) ground-truth puzzle count for this motif. |")
    lines.append(
        "| **min / Q1 / Q2 / Q3 / max** | Puzzle-Rating (difficulty) distribution over the "
        "combined `n_gt` ground-truth puzzles. Q2 is the median. |"
    )
    lines.append(
        "| **TP depth** | Mean stored `tactic_depth` (half-moves into the refutation PV) on "
        "the correctly-detected train puzzles. |"
    )
    lines.append(
        "| **Status** | `shipped` = floor-gated and surfaced; `suppressed` = excluded from the "
        "floor gate and query-suppressed via the `_TACTIC_CHIP_CONFIDENCE_MIN` lever. |"
    )
    lines.append("")

    # --- Table A: precision/recall train vs test ---
    lines.append("## Accuracy per tactic — train vs held-out test")
    lines.append("")
    lines.append(
        "| T | Motif | P(train) | P(test) | ΔP | R(train) | R(test) | n(train) | n(test) | Status |"
    )
    lines.append("|:--|:--|---:|---:|---:|---:|---:|---:|---:|:--|")
    for tier, order in _TIER_ORDER:
        for motif in order:
            tr, te = train[motif], test[motif]
            pt, pv = tr.precision, te.precision
            dp = pv - pt if not (math.isnan(pt) or math.isnan(pv)) else float("nan")
            dp_str = f"{dp:+.3f}" if not math.isnan(dp) else "—"
            lines.append(
                f"| {tier} | {motif} | {_fmt(pt)} | {_fmt(pv)} | {dp_str} | "
                f"{_fmt(tr.recall)} | {_fmt(te.recall)} | "
                f"{len(tr.gt_ratings)} | {len(te.gt_ratings)} | {_status(motif)} |"
            )
    lines.append("")

    # --- Table B: difficulty distribution (combined) ---
    lines.append("## Difficulty distribution per tactic (combined train+test)")
    lines.append("")
    lines.append("| T | Motif | n_gt | min / Q1 / Q2 / Q3 / max | TP depth | Status |")
    lines.append("|:--|:--|---:|---|---:|:--|")
    for tier, order in _TIER_ORDER:
        for motif in order:
            s = combined[motif]
            g = s.gt_ratings
            dist = (
                f"{min(g)} / {_quantile(g, 0.25):.0f} / {statistics.median(g):.0f} / "
                f"{_quantile(g, 0.75):.0f} / {max(g)}"
                if g
                else "—"
            )
            tp_d = (
                f"{statistics.mean(train[motif].tp_depths):.1f}" if train[motif].tp_depths else "–"
            )
            lines.append(f"| {tier} | {motif} | {len(g)} | {dist} | {tp_d} | {_status(motif)} |")
    lines.append("")
    lines.append(
        f"**Overall fixture Rating (combined):** min {min(all_ratings)} / "
        f"Q1 {_quantile(all_ratings, 0.25):.0f} / Q2 {statistics.median(all_ratings):.0f} / "
        f"Q3 {_quantile(all_ratings, 0.75):.0f} / max {max(all_ratings)}."
    )
    lines.append("")

    # --- Depth-vs-Rating correlation (D-06) ---
    corr = float("nan")
    if len(depth_rating_pairs) >= 2:
        corr = statistics.correlation(
            [d for d, _ in depth_rating_pairs], [r for _, r in depth_rating_pairs]
        )
    lines.append(
        f"**Depth-vs-Rating Pearson correlation** (combined correct detections, "
        f"n={len(depth_rating_pairs)}): {_fmt(corr, 4)}. Stored depth is the Phase 129 "
        "difficulty proxy, so this relationship is load-bearing."
    )
    lines.append("")

    lines.append(_interpretation(train, test, corr))
    return "\n".join(lines) + "\n"


# Train precision must beat test precision by more than this to flag overfitting.
_OVERFIT_DELTA: float = 0.10


def _interpretation(
    train: dict[str, MotifStats],
    test: dict[str, MotifStats],
    corr: float,
) -> str:
    """Data-driven summary (train metrics + overfit signal) plus design notes."""
    shipped = [m for m, s in train.items() if m not in SUPPRESSED_MOTIFS]
    suppressed = [m for m in train if m in SUPPRESSED_MOTIFS]
    never_fire = [m for m in suppressed if (train[m].tp + train[m].fp) == 0]
    only_fp = [m for m in suppressed if train[m].tp == 0 and train[m].fp > 0]

    total_tp = sum(s.tp for s in train.values())
    total_fp = sum(s.fp for s in train.values())
    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else float("nan")

    firing_shipped = [m for m in shipped if (train[m].tp + train[m].fp) > 0]
    worst_prec = min(firing_shipped, key=lambda m: train[m].precision) if firing_shipped else None
    biggest_fp = max(train, key=lambda m: train[m].fp)

    # Overfit: shipped motifs where train precision beats test by > _OVERFIT_DELTA.
    overfit: list[tuple[str, float]] = []
    for m in firing_shipped:
        pt, pv = train[m].precision, test[m].precision
        if not (math.isnan(pt) or math.isnan(pv)) and (pt - pv) > _OVERFIT_DELTA:
            overfit.append((m, pt - pv))
    overfit.sort(key=lambda x: x[1], reverse=True)

    out: list[str] = []
    out.append("## Summary & interpretation")
    out.append("")
    out.append(
        f"- **Coverage:** {len(shipped)} shipped (floor-gated) motifs, "
        f"{len(suppressed)} suppressed ({len(never_fire)} never fire, "
        f"{len(only_fp)} fire only false positives). Micro-averaged TRAIN precision across "
        f"all firing motifs: **{_fmt(micro_prec)}** ({total_tp} TP / {total_fp} FP)."
    )
    if overfit:
        worst = ", ".join(f"`{m}` (ΔP −{d:.3f})" for m, d in overfit[:3])
        out.append(
            f"- **Overfit watch:** {len(overfit)} shipped motif(s) drop >"
            f"{_OVERFIT_DELTA:.2f} precision from train to test — worst: {worst}. Treat these "
            "train gains skeptically; prefer principled fixes over fixture-specific tuning."
        )
    else:
        out.append(
            "- **No overfit flagged:** every shipped motif holds train precision on the "
            f"held-out test set within {_OVERFIT_DELTA:.2f}. Train gains are generalizing."
        )
    if worst_prec is not None:
        out.append(
            f"- **Lowest-precision shipped motif (train):** `{worst_prec}` "
            f"({_fmt(train[worst_prec].precision)}). **Biggest false-positive source:** "
            f"`{biggest_fp}` ({train[biggest_fp].fp} FP) — over-fires relative to its base."
        )
    out.append(
        "- **Difficulty is deliberately flat across tactics.** The fixtures are stratified "
        "by Rating band per motif-theme (`scripts/select_tagger_fixtures.py`), so per-motif "
        "min/Q1/Q2/Q3/max cluster near the overall spread. These reflect the *sampled* "
        "difficulty, NOT the natural lichess-population difficulty of each tactic."
    )
    out.append(
        f"- **Depth tracks difficulty** (global Pearson r={_fmt(corr, 3)}): within the TP "
        "set, immediate motifs sit shallow (hanging-piece ≈ 0, fork/double-check ≈ 1) while "
        "mating nets run deeper. Stored depth feeds the Phase 129 difficulty filter."
    )
    out.append(
        "- **`mate` recall looks low by design.** Generic mate is the catch-all under the "
        "named-mate subtypes, which win the min-depth dispatch — those puzzles are tagged "
        "correctly under their specific motif, so they count as `mate` false negatives here."
    )
    out.append(
        "- **`pin` now ships at >0.93 precision.** Phase 131 restricted the pin scan to the "
        "boards that follow a winning-side move (the cook node set) instead of every PV board, "
        "removing the incidental pins that fired inside opponent forcing lines (0.819 -> 0.944 "
        "TEST)."
    )
    out.append("")
    out.append(
        "> Precision floors (`precision_floors.py`) are asserted on TRAIN only (D-08/D-09). "
        "TEST is held out — never used to set floors or tune detectors. The `/loop` optimizes "
        "TRAIN; judge real improvement by TEST and the ΔP overfit column."
    )
    return "\n".join(out)


class GoalMiss:
    """One unmet goal dimension for a motif (precision or recall)."""

    def __init__(self, motif: str, dim: str, current: float, target: float) -> None:
        self.motif = motif
        self.dim = dim  # "precision" | "recall"
        self.current = current
        self.target = target

    @property
    def gap(self) -> float:
        # NaN current (motif never fires) counts as the full target as the gap.
        cur = 0.0 if math.isnan(self.current) else self.current
        return self.target - cur


def _evaluate_goals(stats: dict[str, MotifStats]) -> list[GoalMiss]:
    """Return every unmet goal dimension across all GOALS motifs."""
    misses: list[GoalMiss] = []
    for motif, spec in GOALS.items():
        s = stats.get(motif)
        if s is None:  # goal names a motif that isn't validated — skip defensively
            continue
        for dim in ("precision", "recall"):
            target = spec.get(dim)
            if target is None:
                continue
            current = getattr(s, dim)
            # NaN current (never fires) is a miss; otherwise compare.
            if math.isnan(current) or current + 1e-9 < target:
                misses.append(GoalMiss(motif, dim, current, target))
    return misses


def _print_goal_check(
    stats: dict[str, MotifStats],
    misses: list[GoalMiss],
    eval_set: str,
    n_rows: int,
) -> None:
    """Print an actionable goal-gap summary for the /loop driver."""
    print()
    print("=" * 72)
    print(f"TACTIC-TAGGER GOAL CHECK — {eval_set.upper()} set ({n_rows} rows)")
    print("=" * 72)
    total_dims = sum(1 for spec in GOALS.values() for v in spec.values() if v is not None)
    met = total_dims - len(misses)
    print(f"Goals met: {met}/{total_dims} dimensions across {len(GOALS)} motifs.")
    if not misses:
        print("ALL GOALS MET — stop the loop.")
        print("=" * 72)
        return

    print(f"Unmet ({len(misses)}), worst gap first:")
    for m in sorted(misses, key=lambda x: x.gap, reverse=True):
        cur = "NaN" if math.isnan(m.current) else f"{m.current:.3f}"
        s = stats[m.motif]
        extra = f"(TP={s.tp} FP={s.fp} FN={s.fn})"
        print(
            f"  {m.motif:<19} {m.dim:<9} {cur:>6} -> need {m.target:.3f} (gap {m.gap:+.3f}) {extra}"
        )
    worst = max(misses, key=lambda x: x.gap)
    hint = (
        "raise precision = cut false positives (tighten the relevance gate / dispatch rank)"
        if worst.dim == "precision"
        else "raise recall = make the detector fire on more true cases (loosen without adding FPs)"
    )
    print()
    print(
        f"NEXT: work `{worst.motif}` {worst.dim} (gap {worst.gap:+.3f}) — {hint}. "
        "Edit app/services/tactic_detector.py, then re-run this check."
    )
    print(
        "Caution: if a motif's gap does not shrink across iterations, the goal may be "
        "unreachable without a redesign (cf. fork 0.80 in 127-03 / SEED-057) — lower the "
        "goal in GOALS or stop, do not churn."
    )
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tactic-tagger precision/recall report.")
    parser.add_argument(
        "--check-goals",
        action="store_true",
        help="Evaluate the GOALS table and exit non-zero if any goal is unmet "
        "(for /loop self-improvement). Still writes the markdown report.",
    )
    parser.add_argument(
        "--eval-set",
        choices=("train", "test"),
        default="train",
        help="Which split --check-goals evaluates. Default 'train' (the optimization set); "
        "use 'test' for a final held-out check before declaring the loop done.",
    )
    args = parser.parse_args()

    train_rows = _load_split("train")
    test_rows = _load_split("test")
    generated = datetime.now(timezone.utc)
    report = _build_report(train_rows, test_rows, generated)

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _REPORT_DIR / f"tactic-tagger-{generated.strftime('%Y-%m-%d')}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path} ({len(report.splitlines())} lines)")

    if args.check_goals:
        eval_rows = train_rows if args.eval_set == "train" else test_rows
        stats, _ = _score(eval_rows)
        misses = _evaluate_goals(stats)
        _print_goal_check(stats, misses, args.eval_set, len(eval_rows))
        # Exit 0 = all goals met (loop stops); 1 = unmet (loop keeps improving).
        sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
