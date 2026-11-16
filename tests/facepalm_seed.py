"""Facts-based seeding of facepalm scores for reader tests (Phase 254, D-01).

Readers compute the facepalm score at query time from the stored facts (`facepalm_expr`), so a
reader test must seed FACTS, never the stored `facepalm_score` column. `facepalm_fact_columns`
returns GameFlaw keyword values whose expression equals a requested target score.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import LOSS_CAP, PLAYED_PROB_OFFSET
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmFacts,
    FacepalmModel,
    facepalm_score,
)
from tests.conftest import ensure_test_user

_BLUNDER_SEVERITY: Final[int] = 2
_PHASE_MIDDLEGAME: Final[int] = 1

SEED_FACEPALM_TOLERANCE: Final[float] = 1e-5
# Band-edge tests seed a target plus or minus this margin: REAL inputs cannot hit an exact decimal.
SEED_FACEPALM_MARGIN: Final[float] = 1e-4
# Smallest played-move probability a seed may use (below it a probability is unrealistic).
SEED_PROB_MIN: Final[float] = 0.001
# Reply spreads of the search grid. Between 4 and 16 there must be a value (8): a low target
# (about 0.05) needs a spread above 4 so that played_prob stays inside (SEED_PROB_MIN, 1].
SEED_SPREADS: Final[tuple[float, ...]] = (1.0, 2.0, 4.0, 8.0, 16.0)
# Best-move probability of a scored seed row. Under best_prob_for_misses a no-loss grid point
# (played_3 0) reads the best-move term, and since 254 WR-01 / 256 D-04 an unknown best-move
# probability leaves that row unscored, so seeded rows carry one.
SEED_BEST_PROB: Final[float] = 0.2
# Played-move probability used to read the rest of the linear predictor off the Python twin.
_PROBE_PROB: Final[float] = 0.5
_ARRAY_SLOTS: Final[int] = 9


def _material_array(played_3: int) -> list[int | None]:
    """A 9-slot signed array with `played_3` at every odd slot and NULL at the even ones (D-17)."""
    return [played_3 if slot % 2 == 1 else None for slot in range(1, _ARRAY_SLOTS + 1)]


def _unscored_facts() -> dict[str, Any]:
    """Facts of an unscored row: no played line and no mate, so the loss input is unknown."""
    return {
        "maia_played_prob": SEED_PROB_MIN,
        "maia_reply_spread": SEED_SPREADS[0],
        "played_line_material": None,
        "line_mate_ply": None,
        "best_line_material": None,
        "best_line_mate_ply": None,
        "maia_best_prob": None,
        "maia_pre_spread": None,
    }


def _rest_of_z(model: FacepalmModel, lam: float, played_3: int, spread: float) -> float | None:
    """The linear predictor without the played-probability term, via the Python twin.

    Reading it off `facepalm_score` keeps the seed valid for every model shape: the twin owns
    the term rules. None when the twin leaves the row unscored.
    """
    # The probe reads the same array the seed stores, so it is valid under every material input.
    facts = FacepalmFacts(
        played_prob=_PROBE_PROB,
        reply_spread=spread,
        played_material=_material_array(played_3),
        mate_ply=None,
        best_prob=SEED_BEST_PROB,
    )
    score = facepalm_score(facts, lam=lam, model=model)
    if score is None:
        return None
    z_probe = math.log(score / (1.0 - score))
    return z_probe - model.played_coef * math.log(_PROBE_PROB + PLAYED_PROB_OFFSET)


def facepalm_fact_columns(
    target: float | None, *, lam: float, model: FacepalmModel = FACEPALM_MODEL
) -> dict[str, Any]:
    """GameFlaw keyword values whose `facepalm_expr(lam, model)` equals `target` (None = unscored).

    Reader tests seed facts, never the stored score, since readers use the expression from R2
    on (D-01). The best line and the pre-blunder spread stay NULL, so the missed term is 0 and
    `lam` does not move the value; the best-move probability is SEED_BEST_PROB (a no-loss row
    stays scored under best_prob_for_misses, 254 WR-01). Search: the played depth-3 material from 0 down to
    -LOSS_CAP, spreads from SEED_SPREADS, the first grid point whose solved played probability
    lies in [SEED_PROB_MIN, 1.0] wins; the probability is solved in closed form from the logit
    of the target. Raises ValueError when no grid point reaches the target (for example a refit
    that flips the sign of the played coefficient, or a target outside the model's range).
    """
    if target is None:
        return _unscored_facts()
    if not 0.0 < target < 1.0:
        raise ValueError("target must lie strictly between 0 and 1")
    if model.played_coef == 0.0:
        raise ValueError("a zero played coefficient cannot be solved for the probability")
    z_target = math.log(target / (1.0 - target))
    for played_3 in range(0, -LOSS_CAP - 1, -1):
        for spread in SEED_SPREADS:
            rest = _rest_of_z(model, lam, played_3, spread)
            if rest is None:
                continue
            probability = math.exp((z_target - rest) / model.played_coef) - PLAYED_PROB_OFFSET
            if SEED_PROB_MIN <= probability <= 1.0:
                return {
                    **_unscored_facts(),
                    "maia_played_prob": probability,
                    "maia_reply_spread": spread,
                    "played_line_material": _material_array(played_3),
                    "maia_best_prob": SEED_BEST_PROB,
                }
    raise ValueError("no seed grid point reaches the target score")


async def seed_flaw_rows(
    session: AsyncSession, fact_rows: Sequence[dict[str, Any]], *, user_id: int
) -> int:
    """Insert one game with one blunder flaw per fact row (ply = row index); return its game_id.

    For a rollback-scoped `db_session`: nothing outlives the test, so there is no lottery
    cleanup to do. `fact_rows` are GameFlaw keyword values (e.g. `facepalm_fact_columns`).
    """
    await ensure_test_user(session, user_id)
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=f"facepalm-seed-{uuid.uuid4().hex}",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="300+0",
        time_control_bucket="blitz",
        time_control_seconds=300,
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    for ply, facts in enumerate(fact_rows):
        session.add(
            GameFlaw(
                user_id=user_id,
                game_id=game.id,
                ply=ply,
                severity=_BLUNDER_SEVERITY,
                phase=_PHASE_MIDDLEGAME,
                is_miss=False,
                is_lucky=False,
                is_reversed=False,
                is_squandered=False,
                fen="8/8/8/8/8/8/8/8",
                **facts,
            )
        )
    await session.flush()
    return game.id
