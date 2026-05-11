"""Pure-math conversion: Stockfish eval (signed cp or mate-in-N) -> user expected score.

Used by Phase 83's Stockfish-baseline predicted endgame score (SEED-014, D-01..D-03).
The aggregator (Plan 2) and the benchmark CTE (Plan 4) convert each endgame's
entry-eval into a per-game expected score in [0, 1], then average to compare with
the user's actual endgame score.

Two converters, deliberately split (D-02):

  eval_cp_to_expected_score    Lichess winning-chances sigmoid over centipawns.
  eval_mate_to_expected_score  Direct 0/1 mapping (mate is not sigmoid-routed).

Sign convention mirrors app/services/endgame_service.py:_classify_endgame_bucket:
the raw eval is white-perspective, and a `sign = +1 if user_color == "white"
else -1` flip yields the user-perspective value. Verified by the symmetry test
f(+x, "white") + f(+x, "black") == 1.0.

Sigmoid constant:
  LICHESS_K = 0.00368208 is the published Lichess winning-chances coefficient
  used in their accuracy / winning-chances formula. See:
    https://lichess.org/page/accuracy
  i.e. winning_chances(cp) = 1 / (1 + exp(-K * cp)), centered at 0 -> 0.5,
  saturating to ~0.997 at +1500 cp and ~0.003 at -1500 cp.

Mate handling (D-02, Pitfall 1):
  Mate scores are NOT routed through the sigmoid. A mate-in-N for the side
  that is winning maps to 1.0 from that user's perspective; from the opposing
  user's perspective it maps to 0.0. The distance to mate (N) is irrelevant
  to the expected-score calculation.

No I/O, no DB, stdlib only. The module is unit-testable in isolation; see
tests/services/test_eval_utils.py.
"""

import math
from typing import Literal

# Lichess winning-chances sigmoid coefficient (sourced from Lichess accuracy page).
# Kept as a module-level named constant (CLAUDE.md "no magic numbers") so that
# Plan 4's SQL CTE and Plan 2's aggregator reference the same canonical value.
LICHESS_K: float = 0.00368208


def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float:
    """Convert a signed centipawn eval to a user-perspective expected score in (0, 1).

    Args:
        eval_cp: White-perspective centipawn eval (Stockfish / python-chess
            convention). Positive means white is ahead, negative means black.
        user_color: "white" or "black" — used to flip sign so positive output
            means the user is ahead. f(+100, "white") ~ 0.591;
            f(+100, "black") ~ 0.409.

    Returns:
        Expected score in (0, 1): 0.5 at cp == 0, saturating near 1.0 / 0.0
        at large positive / negative cp from the user's perspective.

    Sign convention matches app/services/endgame_service.py:_classify_endgame_bucket
    (sign = +1 for white user, -1 for black user). See the white/black symmetry
    test in tests/services/test_eval_utils.py.
    """
    sign = 1 if user_color == "white" else -1
    return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))


def eval_mate_to_expected_score(
    eval_mate: int,
    user_color: Literal["white", "black"],
) -> float:
    """Convert a mate-in-N eval to a user-perspective expected score (exactly 0.0 or 1.0).

    Args:
        eval_mate: White-perspective mate score. Positive (e.g. +5) means white
            has a forced mate; negative (e.g. -5) means black has one. The
            magnitude (distance to mate) is irrelevant for the expected score.
        user_color: "white" or "black".

    Returns:
        1.0 iff the side with the forced mate equals user_color, else 0.0.

    Mate is NOT routed through the sigmoid (D-02): a forced mate is a terminal
    evaluation, and the sigmoid would compress mate-in-1 and mate-in-30 to
    different values which is the wrong semantics for expected-score averaging.

    Pitfall 1 coverage: both `(eval_mate > 0, user_color == "white") -> 1.0`
    and `(eval_mate < 0, user_color == "black") -> 1.0` are exercised by
    tests/services/test_eval_utils.py::TestMate. Phase 82 was bitten by an
    asymmetric sign bug that single-color tests would have missed.
    """
    if eval_mate > 0 and user_color == "white":
        return 1.0
    if eval_mate < 0 and user_color == "black":
        return 1.0
    return 0.0
