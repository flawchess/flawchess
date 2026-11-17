"""Spike 007: rank correlation of the shipped facepalm score and its terms with puzzle rating.

Reads the feature tables written by ``build_features.py`` (no Maia, no database) and scores
every puzzle with the app's own ``facepalm_score`` under the shipped ``FACEPALM_MODEL``:

- loss view: the puzzle's blunder is the user's blunder (loss and spread terms);
- miss view: the solver's first move is the best move the user missed (missed and best-move
  probability terms). A puzzle has no played move on the solver's side, so the played line is
  a neutral quiet move (material 0 at every depth) and the played probability a constant.

A HIGH facepalm score means "obvious", a HIGH puzzle rating means "hard", so a term that works
has a NEGATIVE Spearman correlation with rating (the spread is the exception: positive).

Usage::

    uv run python .planning/spikes/007-facepalm-vs-puzzle-ratings/analyze.py \
        --features .planning/spikes/007-facepalm-vs-puzzle-ratings/features-elo1500.tsv.gz \
        --sensitivity .planning/spikes/007-facepalm-vs-puzzle-ratings/features-elo1100.tsv.gz \
                      .planning/spikes/007-facepalm-vs-puzzle-ratings/features-elo1900.tsv.gz
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from app.services.blunder_check_rules import (  # noqa: E402
    FACEPALM_LIBRARY_LAMBDA,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (  # noqa: E402
    FACEPALM_MODEL,
    FacepalmFacts,
    MaterialInput,
    facepalm_score,
    material_loss,
    material_missed,
)

MATERIAL_SLOTS: int = 9
MATERIAL_INPUTS: tuple[MaterialInput, ...] = ("depth_3", "decaying_mean", "first_stable")
# The solver has no played move: a quiet move that keeps material level, at a fixed probability
# (a constant, so it never changes a rank).
NEUTRAL_PLAYED_MATERIAL: tuple[int, ...] = (0,) * MATERIAL_SLOTS
NEUTRAL_PLAYED_PROB: float = 0.2
# Pre-registered criterion (README): the composite must reach this Spearman on the primary slice.
SIGNAL_THRESHOLD: float = 0.30
PRIMARY_MAX_SOLVER_MOVES: int = 2
CV_FOLDS: int = 5
CV_SEED: int = 261117
LENGTH_BUCKETS: tuple[int, ...] = (1, 2, 3, 4)  # solver moves; the last bucket is open-ended


@dataclass(frozen=True, slots=True)
class Puzzle:
    puzzle_id: str
    rating: int
    themes: frozenset[str]
    solver_moves: int
    played_prob: float
    pre_spread: float
    reply_spread: float
    punish_prob: float
    post_legal_moves: int
    punish_is_capture: bool
    punish_is_check: bool
    played_material: tuple[int | None, ...]
    mate_ply: int | None
    best_material: tuple[int | None, ...]
    best_mate_ply: int | None

    @property
    def is_mate(self) -> bool:
        return "mate" in self.themes


def _opt_int(cell: str) -> int | None:
    return int(cell) if cell else None


def load(path: Path) -> list[Puzzle]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return [
        Puzzle(
            puzzle_id=r["puzzle_id"],
            rating=int(r["rating"]),
            themes=frozenset(r["themes"].split()),
            solver_moves=int(r["n_moves"]) // 2,
            played_prob=float(r["played_prob"]),
            pre_spread=float(r["pre_spread"]),
            reply_spread=float(r["reply_spread"]),
            punish_prob=float(r["punish_prob"]),
            post_legal_moves=int(r["post_legal_moves"]),
            punish_is_capture=r["punish_is_capture"] == "1",
            punish_is_check=r["punish_is_check"] == "1",
            played_material=tuple(
                _opt_int(r[f"played_mat_{d}"]) for d in range(1, MATERIAL_SLOTS + 1)
            ),
            mate_ply=_opt_int(r["mate_ply"]),
            best_material=tuple(_opt_int(r[f"best_mat_{d}"]) for d in range(1, MATERIAL_SLOTS + 1)),
            best_mate_ply=_opt_int(r["best_mate_ply"]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Terms and scores (the app's functions under the shipped model)
# ---------------------------------------------------------------------------


def carry_forward(material: Sequence[int | None]) -> tuple[int | None, ...]:
    """Fill the slots after the last known one with its value (the puzzle ended, the win stands)."""
    filled: list[int | None] = []
    last: int | None = None
    for value in material:
        last = value if value is not None else last
        filled.append(last)
    return tuple(filled)


def loss_term(p: Puzzle, material_input: MaterialInput) -> float | None:
    return material_loss(
        p.played_material,
        p.mate_ply,
        material_input=material_input,
        loss_floor=FACEPALM_MODEL.loss_floor,
    )


def missed_term(p: Puzzle, material_input: MaterialInput, *, filled: bool = False) -> float:
    best = carry_forward(p.best_material) if filled else p.best_material
    return material_missed(
        NEUTRAL_PLAYED_MATERIAL,
        best,
        p.best_mate_ply,
        material_input=material_input,
        missed_floor=FACEPALM_MODEL.missed_floor,
        missed_cap=FACEPALM_MODEL.missed_cap,
        missed_mate=FACEPALM_MODEL.missed_mate,
    )


def loss_view_score(p: Puzzle, played_prob: float | None = None) -> float | None:
    """Shipped score of the puzzle's blunder; `played_prob` overrides the untestable term."""
    facts = FacepalmFacts(
        played_prob=p.played_prob if played_prob is None else played_prob,
        reply_spread=p.reply_spread,
        played_material=p.played_material,
        mate_ply=p.mate_ply,
    )
    return facepalm_score(facts, lam=FACEPALM_LIBRARY_LAMBDA)


def miss_view_score(p: Puzzle, *, filled: bool = False) -> float | None:
    """Shipped score of "the solver missed the solution" (neutral played move)."""
    facts = FacepalmFacts(
        played_prob=NEUTRAL_PLAYED_PROB,
        reply_spread=None,
        played_material=NEUTRAL_PLAYED_MATERIAL,
        mate_ply=None,
        best_material=carry_forward(p.best_material) if filled else p.best_material,
        best_mate_ply=p.best_mate_ply,
        best_prob=p.punish_prob,
    )
    return facepalm_score(facts, lam=FACEPALM_LIBRARY_LAMBDA)


def log_prob(prob: float) -> float:
    return math.log(prob + PLAYED_PROB_OFFSET)


Term = Callable[[Puzzle], float | None]

# name -> (function, expected sign of the Spearman correlation with rating)
TERMS: dict[str, tuple[Term, int]] = {
    "composite, loss view": (loss_view_score, -1),
    "composite, loss view, played prob fixed": (
        lambda p: loss_view_score(p, NEUTRAL_PLAYED_PROB),
        -1,
    ),
    "composite, miss view": (miss_view_score, -1),
    "composite, miss view, carried forward": (lambda p: miss_view_score(p, filled=True), -1),
    "loss, depth 3": (lambda p: loss_term(p, "depth_3"), -1),
    "loss, decaying mean (shipped)": (lambda p: loss_term(p, "decaying_mean"), -1),
    "loss, first stable": (lambda p: loss_term(p, "first_stable"), -1),
    "missed, depth 3": (lambda p: missed_term(p, "depth_3"), -1),
    "missed, decaying mean (shipped)": (lambda p: missed_term(p, "decaying_mean"), -1),
    "missed, decaying mean, carried forward": (
        lambda p: missed_term(p, "decaying_mean", filled=True),
        -1,
    ),
    "missed, first stable": (lambda p: missed_term(p, "first_stable"), -1),
    "reply spread (shipped)": (lambda p: p.reply_spread, 1),
    "ln P(punishing move) (Findable / best-move term)": (lambda p: log_prob(p.punish_prob), -1),
    "ln P(blunder) (played term, not testable)": (lambda p: log_prob(p.played_prob), 0),
    "pre-blunder spread": (lambda p: p.pre_spread, 0),
    "solver moves (length baseline)": (lambda p: float(p.solver_moves), 1),
}


# ---------------------------------------------------------------------------
# Statistics (numpy only)
# ---------------------------------------------------------------------------


def ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks (ties share their mean rank)."""
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    _, first, counts = np.unique(sorted_values, return_index=True, return_counts=True)
    mean_rank = first + (counts - 1) / 2.0
    out = np.empty(len(values), dtype=float)
    out[order] = np.repeat(mean_rank, counts)
    return out


def pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 3 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    return pearson(ranks(x), ranks(y)) if len(x) >= 3 else None


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float | None:
    """Spearman of x and y with the rank of z regressed out of both."""
    if len(x) < 4:
        return None
    rx, ry, rz = ranks(x), ranks(y), ranks(z)
    if np.std(rz) == 0.0:
        return pearson(rx, ry)
    design = np.column_stack([np.ones(len(rz)), rz])
    res_x = rx - design @ np.linalg.lstsq(design, rx, rcond=None)[0]
    res_y = ry - design @ np.linalg.lstsq(design, ry, rcond=None)[0]
    return pearson(res_x, res_y)


def term_stats(puzzles: Sequence[Puzzle], term: Term) -> dict[str, float | int | None]:
    pairs = [(value, p.rating, p.solver_moves) for p in puzzles if (value := term(p)) is not None]
    if not pairs:
        return {"n": 0, "coverage": 0.0, "rho": None, "rho_partial_length": None}
    x, y, z = (np.array(column, dtype=float) for column in zip(*pairs, strict=True))
    return {
        "n": len(pairs),
        "coverage": round(len(pairs) / len(puzzles), 4),
        "rho": _round(spearman(x, y)),
        "rho_partial_length": _round(partial_spearman(x, y, z)),
    }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


# ---------------------------------------------------------------------------
# Slices
# ---------------------------------------------------------------------------

Slice = Callable[[Puzzle], bool]


def _length_bucket(p: Puzzle) -> int:
    return min(p.solver_moves, LENGTH_BUCKETS[-1])


SLICES: dict[str, Slice] = {
    "all": lambda p: True,
    "primary: non-mate, solver moves <= 2": lambda p: (
        not p.is_mate and p.solver_moves <= PRIMARY_MAX_SOLVER_MOVES
    ),
    "non-mate": lambda p: not p.is_mate,
    "mate": lambda p: p.is_mate,
    "solver moves = 1": lambda p: _length_bucket(p) == 1,
    "solver moves = 2": lambda p: _length_bucket(p) == 2,
    "solver moves = 3": lambda p: _length_bucket(p) == 3,
    "solver moves >= 4": lambda p: _length_bucket(p) == 4,
    "hangingPiece": lambda p: "hangingPiece" in p.themes,
}


def correlation_tables(puzzles: Sequence[Puzzle]) -> dict[str, dict[str, object]]:
    tables: dict[str, dict[str, object]] = {}
    for slice_name, keep in SLICES.items():
        subset = [p for p in puzzles if keep(p)]
        tables[slice_name] = {
            "n": len(subset),
            "terms": {name: term_stats(subset, fn) for name, (fn, _sign) in TERMS.items()},
        }
    return tables


# ---------------------------------------------------------------------------
# Cross-validated linear model: how much of the rating do storable features recover?
# ---------------------------------------------------------------------------


def _length_onehot(p: Puzzle) -> list[float]:
    return [float(_length_bucket(p) == bucket) for bucket in LENGTH_BUCKETS[1:]]


def _loss_pair(p: Puzzle) -> list[float]:
    """The shipped loss term and a flag for the rows it cannot settle."""
    loss = loss_term(p, "decaying_mean")
    return [0.0 if loss is None else loss, float(loss is None)]


def _shipped_terms(p: Puzzle) -> list[float]:
    loss = loss_term(p, "decaying_mean")
    return [
        0.0 if loss is None else loss,
        float(loss is None),
        p.reply_spread,
        missed_term(p, "decaying_mean", filled=True),
        log_prob(p.punish_prob),
    ]


def _extras(p: Puzzle) -> list[float]:
    return [
        log_prob(p.played_prob),
        p.pre_spread,
        math.log(p.post_legal_moves),
        float(p.punish_is_capture),
        float(p.punish_is_check),
        float(p.mate_ply is not None),
        float(p.best_mate_ply is not None),
    ]


FEATURE_SETS: dict[str, Callable[[Puzzle], list[float]]] = {
    "length only": _length_onehot,
    "ln P(punishing move) only": lambda p: [log_prob(p.punish_prob)],
    "reply spread only": lambda p: [p.reply_spread],
    "reply spread + ln P(punishing move)": lambda p: [p.reply_spread, log_prob(p.punish_prob)],
    "loss + reply spread (shipped loss-view pair)": lambda p: [*_loss_pair(p), p.reply_spread],
    "loss + ln P(punishing move)": lambda p: [*_loss_pair(p), log_prob(p.punish_prob)],
    "loss + reply spread + ln P(punishing move)": lambda p: [
        *_loss_pair(p),
        p.reply_spread,
        log_prob(p.punish_prob),
    ],
    "shipped terms (loss, spread, missed, ln P(punish))": _shipped_terms,
    "shipped terms + length": lambda p: _shipped_terms(p) + _length_onehot(p),
    "shipped terms + length + extras": lambda p: _shipped_terms(p) + _length_onehot(p) + _extras(p),
}


def cv_linear(x: np.ndarray, y: np.ndarray) -> dict[str, float | None]:
    """K-fold out-of-fold OLS prediction of the rating: R^2, RMSE and Spearman."""
    rng = np.random.default_rng(CV_SEED)
    fold = rng.permutation(len(y)) % CV_FOLDS
    predicted = np.empty(len(y), dtype=float)
    for k in range(CV_FOLDS):
        train, test = fold != k, fold == k
        design = np.column_stack([np.ones(int(train.sum())), x[train]])
        coef = np.linalg.lstsq(design, y[train], rcond=None)[0]
        predicted[test] = np.column_stack([np.ones(int(test.sum())), x[test]]) @ coef
    residual = y - predicted
    return {
        "r2": _round(1.0 - float(residual.var()) / float(y.var())),
        "rmse": round(float(np.sqrt((residual**2).mean())), 1),
        "rho": _round(spearman(predicted, y)),
    }


def model_table(puzzles: Sequence[Puzzle]) -> dict[str, dict[str, float | None]]:
    y = np.array([p.rating for p in puzzles], dtype=float)
    return {
        name: cv_linear(np.array([build(p) for p in puzzles], dtype=float), y)
        for name, build in FEATURE_SETS.items()
    }


# ---------------------------------------------------------------------------
# Elo sensitivity
# ---------------------------------------------------------------------------

MAIA_TERMS: tuple[str, ...] = (
    "composite, loss view",
    "composite, miss view, carried forward",
    "reply spread (shipped)",
    "ln P(punishing move) (Findable / best-move term)",
    "ln P(blunder) (played term, not testable)",
)


def sensitivity(base: Sequence[Puzzle], others: dict[str, list[Puzzle]]) -> dict[str, object]:
    """The Maia-dependent correlations on the puzzles every Elo run shares."""
    shared = set.intersection(*({p.puzzle_id for p in rows} for rows in others.values()))
    runs = {"base": [p for p in base if p.puzzle_id in shared]}
    runs.update({name: [p for p in rows if p.puzzle_id in shared] for name, rows in others.items()})
    return {
        "n_shared": len(shared),
        "rho": {
            term: {name: term_stats(rows, TERMS[term][0])["rho"] for name, rows in runs.items()}
            for term in MAIA_TERMS
        },
    }


# ---------------------------------------------------------------------------
# Verdict and output
# ---------------------------------------------------------------------------


def verdict(tables: dict[str, dict[str, object]]) -> dict[str, object]:
    primary = tables["primary: non-mate, solver moves <= 2"]["terms"]
    assert isinstance(primary, dict)
    loss_rho = primary["composite, loss view"]["rho"]
    miss_rho = primary["composite, miss view, carried forward"]["rho"]
    loss_ok = loss_rho is not None and loss_rho <= -SIGNAL_THRESHOLD
    miss_ok = miss_rho is not None and miss_rho <= -SIGNAL_THRESHOLD
    label = (
        "VALIDATED" if loss_ok and miss_ok else "PARTIAL" if loss_ok or miss_ok else "INVALIDATED"
    )
    return {
        "threshold": -SIGNAL_THRESHOLD,
        "loss_view_rho": loss_rho,
        "miss_view_rho": miss_rho,
        "verdict": label,
    }


def _fmt(value: object) -> str:
    return "" if value is None else str(value)


def render_markdown(summary: dict[str, object]) -> str:
    lines = ["# Spike 007 results", ""]
    lines.append(f"Puzzles: {summary['n']}, Elo {summary['elo']}. Verdict: {summary['verdict']}")
    tables = summary["correlations"]
    assert isinstance(tables, dict)
    for slice_name, table in tables.items():
        lines += ["", f"## {slice_name} (n = {table['n']})", ""]
        lines += ["| term | expected | rho | rho, length partialled out | n scored | coverage |"]
        lines += ["|---|---|---|---|---|---|"]
        for name, stats in table["terms"].items():
            sign = {-1: "-", 1: "+", 0: "?"}[TERMS[name][1]]
            lines.append(
                f"| {name} | {sign} | {_fmt(stats['rho'])} | {_fmt(stats['rho_partial_length'])}"
                f" | {stats['n']} | {stats['coverage']} |"
            )
    lines += ["", "## Cross-validated linear model of the rating", ""]
    lines += ["| features | R^2 | RMSE | rho |", "|---|---|---|---|"]
    models = summary["models"]
    assert isinstance(models, dict)
    for name, stats in models.items():
        lines.append(f"| {name} | {stats['r2']} | {stats['rmse']} | {stats['rho']} |")
    sens = summary.get("sensitivity")
    if isinstance(sens, dict):
        lines += ["", f"## Elo sensitivity (n = {sens['n_shared']} shared puzzles)", ""]
        names = list(next(iter(sens["rho"].values())))
        lines += ["| term | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
        for term, by_run in sens["rho"].items():
            lines.append(f"| {term} | " + " | ".join(_fmt(by_run[n]) for n in names) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sensitivity", type=Path, nargs="*", default=[])
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    puzzles = load(args.features)
    tables = correlation_tables(puzzles)
    summary: dict[str, object] = {
        "n": len(puzzles),
        "elo": args.features.stem,
        "verdict": verdict(tables),
        "correlations": tables,
        "models": model_table(puzzles),
    }
    if args.sensitivity:
        others = {path.stem: load(path) for path in args.sensitivity}
        summary["sensitivity"] = sensitivity(puzzles, others)
    if args.markdown is not None:
        args.markdown.write_text(render_markdown(summary))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
