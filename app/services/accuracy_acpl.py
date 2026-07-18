"""Pure stdlib port of Lichess's game accuracy + ACPL formulas (D-08..D-11).

This is the SINGLE shared compute path for the four canonical `games` columns
(`white_accuracy`, `black_accuracy`, `white_acpl`, `black_acpl`). Both the live
full-eval-completion hook (`eval_apply.py::_classify_and_fill_oracle`, Plan 03)
and the corpus backfill script (Plan 04) call `compute_game_accuracy_acpl` —
formula logic lives here exactly once (D-06/SEED-110 §4).

Sourced from scalachess/lila (see .planning/seeds/SEED-110-lichess-compatible-accuracy-acpl.md
and 178-RESEARCH.md § "Formula Port (D-08..D-11)" for citations):

  - Win% (D-08): centipawn -> winning-chances via the Lichess sigmoid
    (`LICHESS_K`, imported from `eval_utils` — single source, no re-declared
    magic number), ceiled to +/-CP_CEILING BEFORE the sigmoid, then the
    winning-chances value is clamped to [-1, 1] before scaling to [0, 100].
  - Per-move accuracy (D-09): an exponential decay of the Win% drop, with a
    trailing "+1" uncertainty bonus. A move that does not worsen the position
    scores exactly 100.
  - Game-level accuracy (D-10): a windowed-volatility-weighted aggregation —
    (weightedMean(accuracy, weight) + harmonicMean(accuracy)) / 2 per color,
    where each move's weight is the population stddev (clamped) of a sliding
    window over the *White-POV* Win% sequence (not the mover-POV values).
  - ACPL (D-11): a plain arithmetic mean of per-move centipawn losses
    (mover-POV, each eval capped +/-CP_CEILING first) — NOT the windowed
    aggregation used for accuracy.

Eval semantics (post-move shift, RESEARCH § "Eval Semantics"): `game_positions`
row `ply=P` stores the eval of the position AFTER the move departing from ply
P, i.e. the eval of position `P+1`. Position 0 (the initial position, before
any move) has no stored eval and is seeded at `INITIAL_SEED_CP` (15 cp, the
Stockfish-observed first-move advantage) with no mate. The move departing
from ply P is White's iff P is even (mirrors `flaws_service._pov_cp_or_zero`'s
White-POV -> mover-POV sign convention).

No DB/IO — pure `math` over caller-supplied position rows (duck-typed via
`PositionLike`, so tests can pass lightweight stand-ins without a DB session).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.services.eval_utils import LICHESS_K

# --- Named constants (CLAUDE.md "no magic numbers") -------------------------

# Lichess Cp.CEILING: the pre-sigmoid centipawn cap applied to both cp evals
# and mate-mapped evals (D-08). Also the ACPL per-move loss cap (D-11).
CP_CEILING = 1000

# Lichess AccuracyPercent coefficients (D-09). The trailing "+1" uncertainty
# bonus below is applied separately and is NOT baked into MOVE_ACC_C.
MOVE_ACC_A = 103.1668100711649
MOVE_ACC_B = -0.04354415386753951
MOVE_ACC_C = -3.166924740191411

# Seed White-POV cp for the initial position (before any move is played) —
# the empirically-required "before" of move 1's ACPL/accuracy computation.
# Without this seed, White's first-move loss (and Win% baseline) is undefined.
INITIAL_SEED_CP = 15

# D-10 sliding-window bounds (in moves) and per-window weight clamp bounds.
MIN_WINDOW = 2
MAX_WINDOW = 8
MIN_WEIGHT = 0.5
MAX_WEIGHT = 12.0

Color = Literal["white", "black"]


class PositionLike(Protocol):
    """Structural type for the rows this module consumes.

    Matches `app.models.game_position.GamePosition`'s relevant fields, but is
    a Protocol (not the ORM class) to keep this module DB-free — callers can
    pass real `GamePosition` rows or lightweight test stand-ins interchangeably.
    """

    ply: int
    eval_cp: int | None
    eval_mate: int | None


@dataclass(frozen=True)
class AccuracyAcplResult:
    """Per-color computed accuracy (D-10) and ACPL (D-11) for one game."""

    white_accuracy: float | None
    black_accuracy: float | None
    white_acpl: int | None
    black_acpl: int | None


# --- Small numeric helpers ---------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pop_stddev(xs: Sequence[float]) -> float:
    """Population standard deviation (divide by N, not N-1) — matches D-10."""
    mean = sum(xs) / len(xs)
    variance = sum((x - mean) ** 2 for x in xs) / len(xs)
    return math.sqrt(variance)


def _weighted_mean(xs: Sequence[float], weights: Sequence[float]) -> float:
    return sum(x * w for x, w in zip(xs, weights, strict=True)) / sum(weights)


def _harmonic_mean(xs: Sequence[float]) -> float:
    """Harmonic mean, guarded against a literal 0.0 accuracy (Pitfall 5 / T-178-02-D).

    A harmonic mean containing a true 0 is mathematically 0 in the limit, but
    the direct `len/sum(1/x)` formula raises ZeroDivisionError at x == 0.
    Reproduce Lichess's collapse-toward-0 semantics directly instead of a
    fragile epsilon substitution.
    """
    if not xs:
        return 0.0
    if any(x <= 0.0 for x in xs):
        return 0.0
    return len(xs) / sum(1.0 / x for x in xs)


def _other_color(color: Color) -> Color:
    return "black" if color == "white" else "white"


def _mover_at(ply: int, start_color: Color) -> Color:
    """The color moving FROM this ply (departure ply, not arrival)."""
    return start_color if ply % 2 == 0 else _other_color(start_color)


# --- D-08: Win% ---------------------------------------------------------------


def win_pct(cp: int) -> float:
    """White-POV Win% in [0, 100] from a White-POV centipawn eval (D-08).

    Ceils `cp` to +/-CP_CEILING BEFORE the sigmoid, then clamps the resulting
    winning-chances value to [-1, 1] before scaling — this is the dedicated
    clamped path lichess uses for accuracy/ACPL; it deliberately does NOT
    reuse `eval_utils.eval_cp_to_expected_score`, which has no pre-sigmoid
    ceiling and would diverge at large |cp| (RESEARCH § "Formula Port").
    """
    c = _clamp(cp, -CP_CEILING, CP_CEILING)
    winning_chances = 2.0 / (1.0 + math.exp(-LICHESS_K * c)) - 1.0
    return 50.0 + 50.0 * _clamp(winning_chances, -1.0, 1.0)


def _resolve_white_pov_cp(eval_cp: int | None, eval_mate: int | None) -> int:
    """Resolve a stored (eval_cp, eval_mate) pair to a capped White-POV cp.

    A mate eval maps to +/-CP_CEILING by sign BEFORE win_pct (never routed
    through the plain cp path — eval_cp is NULL whenever eval_mate is set).
    Caller guarantees at least one of the two is non-None.
    """
    if eval_mate is not None:
        return CP_CEILING if eval_mate > 0 else -CP_CEILING
    if eval_cp is None:
        # Caller-guaranteed invariant (documented above): unreachable in practice.
        raise ValueError("_resolve_white_pov_cp requires eval_cp or eval_mate to be set")
    return int(_clamp(eval_cp, -CP_CEILING, CP_CEILING))


# --- D-09: per-move accuracy ---------------------------------------------------


def move_accuracy(before_win: float, after_win: float) -> float:
    """Per-move accuracy in [0, 100] from mover-POV before/after Win% (D-09).

    A move that does not worsen the mover's position (after >= before) scores
    exactly 100. Otherwise an exponential decay of the Win% drop, with the
    trailing "+1" uncertainty bonus kept intact (Pitfall 3 — easy to drop and
    shifts results by 1-3 points).
    """
    if after_win >= before_win:
        return 100.0
    raw = MOVE_ACC_A * math.exp(MOVE_ACC_B * (before_win - after_win)) + MOVE_ACC_C + 1.0
    return _clamp(raw, 0.0, 100.0)


# --- D-10: windowed game-level accuracy ----------------------------------------


def compute_color_accuracy(win_seq_white_pov: Sequence[float], color: Color) -> float | None:
    """Windowed-volatility-weighted game accuracy for one color (D-10).

    `win_seq_white_pov` is the White-POV Win% at every position 0..n_moves
    (length n_moves + 1), seeded at position 0. Per-move weights are derived
    from a sliding window over this SAME White-POV sequence for both colors
    (RESEARCH: pinned by the lichess accuracy fixture — not an independent
    per-color window). Returns None if this color made zero moves.
    """
    n_moves = len(win_seq_white_pov) - 1
    if n_moves <= 0:
        return None

    window_size = int(_clamp(n_moves // 10, MIN_WINDOW, MAX_WINDOW))
    raw_windows = [win_seq_white_pov[k : k + window_size] for k in range(n_moves - window_size + 2)]
    pad_count = max(0, window_size - 2)
    first_window = raw_windows[0] if raw_windows else win_seq_white_pov[:window_size]
    windows = [first_window] * pad_count + raw_windows

    color_start = 0 if color == "white" else 1
    accuracies: list[float] = []
    weights: list[float] = []
    for p in range(color_start, n_moves, 2):
        before = win_seq_white_pov[p] if color == "white" else 100.0 - win_seq_white_pov[p]
        after = win_seq_white_pov[p + 1] if color == "white" else 100.0 - win_seq_white_pov[p + 1]
        accuracies.append(move_accuracy(before, after))
        weights.append(_clamp(_pop_stddev(windows[p]), MIN_WEIGHT, MAX_WEIGHT))

    if not accuracies:
        return None
    return (_weighted_mean(accuracies, weights) + _harmonic_mean(accuracies)) / 2.0


# --- D-11: ACPL -----------------------------------------------------------------


def compute_color_acpl(losses: list[int]) -> int | None:
    """Plain arithmetic-mean ACPL for one color, rounded to int (D-11).

    Deliberately NOT the windowed/harmonic aggregation used for accuracy.
    """
    if not losses:
        return None
    return round(sum(losses) / len(losses))


# --- Orchestrator ----------------------------------------------------------------


def _is_hole_free(
    eval_of_position: dict[int, tuple[int | None, int | None]], ply_count: int
) -> bool:
    """True iff every INTERIOR before/after eval is resolvable (Complete-Sequence Gate).

    Required positions are 1..ply_count-1 (each is simultaneously the "after"
    of one move and the "before" of the next). Position ply_count (terminal)
    may legitimately be NULL when the final move ends the game (checkmate).
    """
    for p in range(ply_count - 1):
        cp, mate = eval_of_position.get(p + 1, (None, None))
        if cp is None and mate is None:
            return False
    return True


def _resolve_after_cp(pair: tuple[int | None, int | None] | None, mover: Color) -> int:
    """Resolve the White-POV cp AFTER a move, with the terminal-mate fallback.

    A missing pair only occurs at the final move (guaranteed by the hole-free
    gate for every interior move): the mover's move ended the game, so treat
    it as a delivered mate in the mover's favor (RESEARCH § "Terminal /
    checkmate handling" — both the +/-CP_CEILING treatment and skipping the
    move give the same aggregate to <0.5%; this module takes the former).
    """
    cp, mate = pair if pair is not None else (None, None)
    if cp is None and mate is None:
        return CP_CEILING if mover == "white" else -CP_CEILING
    return _resolve_white_pov_cp(cp, mate)


def _walk_moves(
    eval_of_position: dict[int, tuple[int | None, int | None]],
    ply_count: int,
    start_color: Color,
) -> tuple[list[int], dict[Color, list[int]]]:
    """Walk every move, returning the White-POV cp sequence and per-color ACPL losses."""
    white_pov_cps = [_resolve_white_pov_cp(*eval_of_position[0])]
    losses: dict[Color, list[int]] = {"white": [], "black": []}

    for p in range(ply_count):
        mover = _mover_at(p, start_color)
        before_white_cp = white_pov_cps[p]
        after_white_cp = _resolve_after_cp(eval_of_position.get(p + 1), mover)
        white_pov_cps.append(after_white_cp)

        before_pov = before_white_cp if mover == "white" else -before_white_cp
        after_pov = after_white_cp if mover == "white" else -after_white_cp
        losses[mover].append(max(0, before_pov - after_pov))

    return white_pov_cps, losses


def compute_game_accuracy_acpl(
    positions: Sequence[PositionLike],
    *,
    start_color: Color = "white",
) -> AccuracyAcplResult | None:
    """Compute per-color accuracy (D-10) and ACPL (D-11) for one game, or None.

    `positions` must be ordered arbitrarily but keyed by explicit `.ply`
    (never by list index — a defensive habit that survives a rare missing
    row). Returns None (all four values NULL) when:
      - `positions` is empty or has zero moves (0-move game), or
      - any interior eval is missing (Complete-Sequence Gate, Pitfall 6 — a
        completion stamp does NOT guarantee hole-free; this gate is the only
        authority).

    `start_color` is always "white" for real games (standard chess always
    starts with White); parametrized for testability / future variants.
    """
    if not positions:
        return None

    eval_of_position: dict[int, tuple[int | None, int | None]] = {0: (INITIAL_SEED_CP, None)}
    for pos in positions:
        eval_of_position[pos.ply + 1] = (pos.eval_cp, pos.eval_mate)

    ply_count = max(pos.ply for pos in positions)
    if ply_count == 0:
        return None
    if not _is_hole_free(eval_of_position, ply_count):
        return None

    white_pov_cps, losses = _walk_moves(eval_of_position, ply_count, start_color)
    win_seq = [win_pct(cp) for cp in white_pov_cps]

    return AccuracyAcplResult(
        white_accuracy=compute_color_accuracy(win_seq, "white"),
        black_accuracy=compute_color_accuracy(win_seq, "black"),
        white_acpl=compute_color_acpl(losses["white"]),
        black_acpl=compute_color_acpl(losses["black"]),
    )
