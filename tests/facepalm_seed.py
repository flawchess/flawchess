"""Facts-based seeding of facepalm scores for reader tests (Phase 254, D-01; Phase 259 D-05).

Readers compute the facepalm score at query time from the stored facts (`facepalm_expr`), so a
reader test must seed FACTS, never the stored `facepalm_score` column. `facepalm_fact_columns`
returns GameFlaw keyword values over the five scalar columns (`maia_played_prob`,
`material_loss`, `material_missed`, `maia_best_prob`, `maia_best_reply_prob`) whose expression
equals a requested target score.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Iterator, Sequence
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.services.blunder_check_rules import (
    FACEPALM_MISSED_CAP,
    LINE_DEPTH,
    LOSS_CAP,
    PLAYED_PROB_OFFSET,
)
from app.services.facepalm_score import (
    FACEPALM_MODEL,
    FacepalmFacts,
    FacepalmModel,
    FacepalmType,
    facepalm_score,
    facepalm_type as facepalm_type_of_facts,
)
from app.services.line_material import LINE_MATERIAL_SLOTS
from tests.conftest import ensure_test_user

_BLUNDER_SEVERITY: Final[int] = 2
_PHASE_MIDDLEGAME: Final[int] = 1

SEED_FACEPALM_TOLERANCE: Final[float] = 1e-5
# Band-edge tests seed a target plus or minus this margin: REAL inputs cannot hit an exact decimal.
SEED_FACEPALM_MARGIN: Final[float] = 1e-4
# Smallest played-move probability a seed may use (below it a probability is unrealistic).
SEED_PROB_MIN: Final[float] = 0.001
# Key-move probability of a scored seed row (the reply on a losing row, the best move on a row that
# loses nothing). A scored row needs one, since an unknown key-move probability leaves it unscored
# (256 D-04). Searched in order: a likely key move reaches the higher targets, an unlikely one the low.
SEED_KEY_PROB: Final[float] = 0.2
SEED_KEY_PROBS: Final[tuple[float, ...]] = (SEED_KEY_PROB, 0.5, 0.9)
# Played-move probability used to read the rest of the linear predictor off the Python twin.
_PROBE_PROB: Final[float] = 0.5


def lone_depth_line(value: int | None, depth: int = LINE_DEPTH) -> tuple[int | None, ...]:
    """A 9-slot stored material array that knows only `depth` (test input for a legacy-shaped line)."""
    return tuple(value if slot == depth else None for slot in range(1, LINE_MATERIAL_SLOTS + 1))


def _unscored_facts() -> dict[str, Any]:
    """Facts of an unscored row: the loss (and with it the missed gain) is unknown."""
    return {
        "maia_played_prob": SEED_PROB_MIN,
        "material_loss": None,
        "material_missed": None,
        "maia_best_prob": None,
        "maia_best_reply_prob": None,
    }


def _seed_facts(played_prob: float, loss: float, missed: float, key_prob: float) -> dict[str, Any]:
    """The five stored scalars of a scored seed row; the key-move probability goes where the twin reads it."""
    return {
        "maia_played_prob": played_prob,
        "material_loss": loss,
        "material_missed": missed,
        "maia_best_prob": None if loss > 0 else key_prob,
        "maia_best_reply_prob": key_prob if loss > 0 else None,
    }


def _facts_of(facts: dict[str, Any]) -> FacepalmFacts:
    return FacepalmFacts(
        played_prob=facts["maia_played_prob"],
        loss=facts["material_loss"],
        missed=facts["material_missed"],
        best_prob=facts["maia_best_prob"],
        reply_prob=facts["maia_best_reply_prob"],
    )


def _rest_of_z(
    model: FacepalmModel, lam: float, loss: float, missed: float, key_prob: float
) -> float | None:
    """The linear predictor without the played-probability term, via the Python twin.

    Reading it off `facepalm_score` keeps the seed valid for every coefficient set: the twin owns
    the term rules. None when the twin leaves the row unscored.
    """
    score = facepalm_score(
        _facts_of(_seed_facts(_PROBE_PROB, loss, missed, key_prob)), lam=lam, model=model
    )
    if score is None:
        return None
    z_probe = math.log(score / (1.0 - score))
    return z_probe - model.played_coef * math.log(_PROBE_PROB + PLAYED_PROB_OFFSET)


def _seed_candidates(
    facepalm_type: FacepalmType | None,
) -> Iterator[tuple[float, float, float]]:
    """(loss, missed, key-move probability) grid points of a seed, in search order.

    Untyped: loss 0 (a non-losing row reading the best move) up to LOSS_CAP, missed 0, so `lam`
    does not move the value. allowed_loss: loss from 1 to LOSS_CAP with missed 0 (loss > 0 >= missed).
    missed_win: loss 0 and a missed gain from FACEPALM_MISSED_CAP down to 1.
    """
    if facepalm_type == "missed_win":
        for gain in range(FACEPALM_MISSED_CAP, 0, -1):
            for key_prob in SEED_KEY_PROBS:
                yield 0.0, float(gain), key_prob
        return
    first = 1 if facepalm_type == "allowed_loss" else 0
    for loss in range(first, LOSS_CAP + 1):
        for key_prob in SEED_KEY_PROBS:
            yield float(loss), 0.0, key_prob


def facepalm_fact_columns(
    target: float | None,
    *,
    lam: float,
    model: FacepalmModel = FACEPALM_MODEL,
    facepalm_type: FacepalmType | None = None,
) -> dict[str, Any]:
    """GameFlaw keyword values whose `facepalm_expr(lam, model)` equals `target` (None = unscored).

    Reader tests seed facts, never the stored score, since readers use the expression from R2
    on (D-01). Untyped (`facepalm_type=None`): the missed gain is 0, so `lam` does not move the
    value. Search: the loss from 0 up to LOSS_CAP and the key-move probability from SEED_KEY_PROBS,
    the first grid point whose solved played probability lies in [SEED_PROB_MIN, 1.0] wins; the
    probability is solved in closed form from the logit of the target. Raises ValueError when no
    grid point reaches the target (for example a refit that flips the sign of the played
    coefficient, or a target outside the model's range).

    Untyped high targets are allowed losses (257 research Pitfall 8): the first grid point that
    reaches them loses material. `facepalm_type` (257 D-02) pins the type of the seeded row:
    "allowed_loss" searches only losing grid points, "missed_win" keeps the loss at 0 and stores a
    missed gain. A typed seed is checked against the Python type twin and the search goes on until
    the type matches.
    """
    if target is None:
        return _unscored_facts()
    if not 0.0 < target < 1.0:
        raise ValueError("target must lie strictly between 0 and 1")
    if model.played_coef == 0.0:
        raise ValueError("a zero played coefficient cannot be solved for the probability")
    z_target = math.log(target / (1.0 - target))
    for loss, missed, key_prob in _seed_candidates(facepalm_type):
        rest = _rest_of_z(model, lam, loss, missed, key_prob)
        if rest is None:
            continue
        probability = math.exp((z_target - rest) / model.played_coef) - PLAYED_PROB_OFFSET
        if not SEED_PROB_MIN <= probability <= 1.0:
            continue
        facts = _seed_facts(probability, loss, missed, key_prob)
        if facepalm_type is None or facepalm_type_of_facts(_facts_of(facts)) == facepalm_type:
            return facts
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
