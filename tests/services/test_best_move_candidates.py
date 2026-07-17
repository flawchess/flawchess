"""Unit tests for app/services/best_move_candidates.py (Phase 174 Plan 04).

Four behavior groups:
  1. pinned_elo_for_mover (GEMS-05): flawchess passthrough, `*_lichess_blitz ??
     raw` fallback, clamp to [600, 2600] (D-04) — matching the live board.
  2. passes_inaccuracy_gate (GEMS-02): best_es - second_es >= INACCURACY_DROP
     via the shared sigmoid + MATE_CP_EQUIVALENT Option-B mate mapping (D-05a).
  3. classify_best_move (GEMS-07): pure gem/great/neither from stored maia_prob
     + cp margin, using only module constants.
  4. Constants-only retune: the SAME stored inputs reclassify under different
     GEM_MAIA_MAX_PROB / MISTAKE_DROP with ZERO re-analysis (GEMS-07).

Every function is pure (no DB, no engine, no inference) and reuses the shared
sigmoid / ELO normalization / clamp verbatim (no re-derivation).
"""

from __future__ import annotations

import math
from typing import TypedDict

import pytest
from sqlalchemy import Float, Integer, String, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import best_move_candidates as bmc
from app.services.best_move_candidates import MoverColor
from app.services.eval_utils import LICHESS_K, eval_cp_to_expected_score
from app.services.flaws_service import INACCURACY_DROP, MISTAKE_DROP


class _MarginKwargs(TypedDict):
    """Typed cp/mate/mover margin so the ``**`` splat carries the ``mover_color``
    ``Literal`` through to classify_best_move (a plain ``dict`` literal widens the
    values to ``int | float | None | str`` and fails the arg-type check)."""

    best_cp: int | None
    best_mate: int | None
    second_cp: int | None
    second_mate: int | None
    mover_color: MoverColor


class _ClassifyKwargs(_MarginKwargs):
    """_MarginKwargs plus maia_prob — the full classify_best_move kwarg set."""

    maia_prob: float


# ─── Group 1: pinned_elo_for_mover (GEMS-05, D-04) ────────────────────────────


def test_flawchess_rating_passthrough_then_clamp() -> None:
    """A flawchess game's rating is already lichess-blitz-equivalent — passthrough
    (no normalization), then clamp."""
    assert (
        bmc.pinned_elo_for_mover(
            raw_rating=1800,
            platform="flawchess",
            time_control_bucket="blitz",
            is_correspondence=False,
        )
        == 1800.0
    )


def test_flawchess_rating_above_ladder_clamps_to_max() -> None:
    assert (
        bmc.pinned_elo_for_mover(
            raw_rating=2700,
            platform="flawchess",
            time_control_bucket="blitz",
            is_correspondence=False,
        )
        == 2600.0
    )


def test_flawchess_rating_below_ladder_clamps_to_min() -> None:
    assert (
        bmc.pinned_elo_for_mover(
            raw_rating=500,
            platform="flawchess",
            time_control_bucket="blitz",
            is_correspondence=False,
        )
        == 600.0
    )


def test_lichess_blitz_is_normalized_within_bounds() -> None:
    """A lichess blitz rating normalizes (identity for blitz) and stays in bounds."""
    result = bmc.pinned_elo_for_mover(
        raw_rating=1600, platform="lichess", time_control_bucket="blitz", is_correspondence=False
    )
    assert 600.0 <= result <= 2600.0
    assert result == 1600.0  # lichess blitz is the identity mapping


def test_none_normalized_falls_back_to_raw_then_clamps() -> None:
    """When normalize returns None (correspondence has no real-time analogue),
    fall back to the raw rating, then clamp."""
    # Correspondence -> normalize returns None -> fallback raw 2900 -> clamp 2600.
    assert (
        bmc.pinned_elo_for_mover(
            raw_rating=2900,
            platform="lichess",
            time_control_bucket="classical",
            is_correspondence=True,
        )
        == 2600.0
    )


def test_result_is_always_within_ladder_bounds() -> None:
    for raw in (100, 599, 600, 1500, 2600, 2601, 5000):
        result = bmc.pinned_elo_for_mover(
            raw_rating=raw,
            platform="flawchess",
            time_control_bucket="blitz",
            is_correspondence=False,
        )
        assert 600.0 <= result <= 2600.0


# ─── mover-color parity helper ────────────────────────────────────────────────


def test_mover_color_ply_parity() -> None:
    assert bmc.mover_color_for_ply(0) == "white"
    assert bmc.mover_color_for_ply(1) == "black"
    assert bmc.mover_color_for_ply(2) == "white"
    assert bmc.mover_color_for_ply(47) == "black"


# ─── Group 2: passes_inaccuracy_gate (GEMS-02, D-05a) ─────────────────────────


def test_gate_passes_when_margin_at_least_inaccuracy_drop() -> None:
    """A cp pair whose ES gap is >= INACCURACY_DROP (0.05) passes the gate."""
    # White POV: best +150cp, second +0cp. es gap ~ 0.636 - 0.5 = 0.136 >= 0.05.
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=150, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
        )
        is True
    )


def test_gate_fails_below_inaccuracy_drop() -> None:
    """A near-equal pair (< 0.05 ES gap) fails the gate."""
    # best +10cp vs second +0cp -> es gap ~ 0.009 < 0.05.
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=10, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
        )
        is False
    )


def test_gate_boundary_exactly_inaccuracy_drop_passes() -> None:
    """The gate is inclusive: an ES gap exactly == INACCURACY_DROP passes."""
    # Construct evals whose ES gap is exactly INACCURACY_DROP by using the sigmoid
    # directly, so the test tracks the shared implementation rather than a magic cp.
    from app.services.eval_utils import eval_cp_to_expected_score

    # second at 0 -> es 0.5; find a best_cp whose white es == 0.5 + INACCURACY_DROP.
    target = 0.5 + INACCURACY_DROP
    # invert the lichess sigmoid: cp = -ln(1/target - 1) / K
    import math

    from app.services.eval_utils import LICHESS_K

    # ceil (not round) so the integer-cp ES gap lands AT or ABOVE the threshold,
    # never just below it — an exact-boundary probe must not undershoot.
    best_cp = math.ceil(-math.log(1.0 / target - 1.0) / LICHESS_K)
    best_es = eval_cp_to_expected_score(best_cp, "white")
    assert best_es - 0.5 >= INACCURACY_DROP  # sanity on construction
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=best_cp, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
        )
        is True
    )


def test_gate_handles_mate_via_option_b() -> None:
    """A mate best vs a cp second is handled by the MATE_CP_EQUIVALENT mapping
    before the sigmoid (not a hard 1.0/0.0)."""
    # best = mate for white (+M2), second = +0cp. Option B maps mate -> +1000cp,
    # es ~ 0.976 vs 0.5 -> gap ~ 0.476 >> 0.05 -> passes.
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=None, best_mate=2, second_cp=0, second_mate=None, mover_color="white"
        )
        is True
    )


def test_gate_black_mover_sign_flips() -> None:
    """For a black mover, negative white-POV cp is good for the mover."""
    # best -150cp (good for black), second 0 -> black-POV es gap ~ 0.136 >= 0.05.
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=-150, best_mate=None, second_cp=0, second_mate=None, mover_color="black"
        )
        is True
    )


def test_gate_false_when_eval_missing() -> None:
    assert (
        bmc.passes_inaccuracy_gate(
            best_cp=None, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
        )
        is False
    )


# ─── Group 3: classify_best_move (GEMS-07) ────────────────────────────────────

# A cp pair with an ES gap comfortably >= MISTAKE_DROP (0.10) for a white mover:
# best +250cp (es ~0.71) vs second +0cp (es 0.5) -> gap ~0.21.
_WIDE_MARGIN: _MarginKwargs = dict(
    best_cp=250, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
)
# A cp pair whose ES gap is < MISTAKE_DROP: best +40cp (es ~0.536) vs 0 -> gap ~0.036.
_NARROW_MARGIN: _MarginKwargs = dict(
    best_cp=40, best_mate=None, second_cp=0, second_mate=None, mover_color="white"
)


def test_classify_gem_when_prob_at_or_below_gem_max() -> None:
    assert bmc.classify_best_move(maia_prob=0.15, **_WIDE_MARGIN) == "gem"


def test_classify_great_between_gem_and_great_max() -> None:
    assert bmc.classify_best_move(maia_prob=0.35, **_WIDE_MARGIN) == "great"


def test_classify_neither_when_prob_above_great_max() -> None:
    assert bmc.classify_best_move(maia_prob=0.60, **_WIDE_MARGIN) == "neither"


def test_classify_neither_when_margin_below_mistake_drop() -> None:
    """C2 fails: even a very-hard-to-find move is 'neither' without the margin."""
    assert bmc.classify_best_move(maia_prob=0.15, **_NARROW_MARGIN) == "neither"


def test_classify_boundary_gem_max_is_inclusive() -> None:
    assert bmc.classify_best_move(maia_prob=bmc.GEM_MAIA_MAX_PROB, **_WIDE_MARGIN) == "gem"


def test_classify_boundary_great_max_is_inclusive() -> None:
    assert bmc.classify_best_move(maia_prob=bmc.GREAT_MAIA_MAX_PROB, **_WIDE_MARGIN) == "great"


# ─── Group 4: constants-only reclassification (GEMS-07 zero-re-analysis) ───────


def test_constants_only_retune_flips_classification() -> None:
    """The SAME stored (maia_prob, cp) inputs reclassify differently when the
    module constants change — proving a threshold retune needs ZERO re-analysis
    (no DB read, no engine call, no re-inference)."""
    stored: _ClassifyKwargs = dict(maia_prob=0.35, **_WIDE_MARGIN)

    # Under the shipped constants (gem<=0.20, great<=0.50): 0.35 -> great.
    assert bmc.classify_best_move(**stored) == "great"

    # Retune GEM_MAIA_MAX_PROB up to 0.40 -> the same 0.35 now clears gem.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bmc, "GEM_MAIA_MAX_PROB", 0.40)
        assert bmc.classify_best_move(**stored) == "gem"

    # Retune GREAT_MAIA_MAX_PROB down below 0.35 -> the same 0.35 falls to neither.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bmc, "GREAT_MAIA_MAX_PROB", 0.30)
        assert bmc.classify_best_move(**stored) == "neither"


def test_reuses_shared_thresholds_not_local_copies() -> None:
    """The gate/classification must reuse flaws_service's INACCURACY_DROP /
    MISTAKE_DROP, never re-declare them (single-source-of-truth guard)."""
    assert bmc.INACCURACY_DROP is INACCURACY_DROP
    assert bmc.MISTAKE_DROP is MISTAKE_DROP


# ─── Group 5: best_move_tier_sql agreement with classify_best_move (FILT-01) ───
#
# The SQL twin can only be proven correct by REAL SQL evaluation (func.exp() is
# a database function, not Python math) — a hand-computed expected value could
# silently drift from either side. Every case below derives its expected value
# by calling classify_best_move() with the SAME kwargs, then asserts the
# DB-evaluated SQL twin agrees, mirroring tests/services/test_flaws_service.py's
# is_opponent_expr live-DB-evaluation pattern (TestIsOpponentExpr).

# A cp margin whose white-mover ES gap lands exactly in [INACCURACY_DROP,
# MISTAKE_DROP) = [0.05, 0.10) — Pitfall 3: a stored row in this band must
# classify NEITHER/NULL regardless of maia_prob. Computed (not hand-picked) by
# inverting the shared sigmoid, ceiling so the integer cp never undershoots.
_NARROW_BAND_TARGET_ES_GAP = 0.07
_narrow_band_target_es = 0.5 + _NARROW_BAND_TARGET_ES_GAP
_NARROW_BAND_BEST_CP = math.ceil(-math.log(1.0 / _narrow_band_target_es - 1.0) / LICHESS_K)
_narrow_band_margin = eval_cp_to_expected_score(_NARROW_BAND_BEST_CP, "white") - 0.5
assert INACCURACY_DROP <= _narrow_band_margin < MISTAKE_DROP, (
    "fixture construction sanity: margin must land in [INACCURACY_DROP, MISTAKE_DROP)"
)

_TIER_SQL_FIXTURE_MATRIX: list[tuple[str, _ClassifyKwargs]] = [
    (
        "gem_low_prob_wide_margin",
        dict(maia_prob=0.10, **_WIDE_MARGIN),
    ),
    (
        "great_mid_prob_wide_margin",
        dict(maia_prob=0.35, **_WIDE_MARGIN),
    ),
    (
        "neither_high_prob_wide_margin",
        dict(maia_prob=0.60, **_WIDE_MARGIN),
    ),
    (
        "gem_boundary_exactly_gem_max",
        dict(maia_prob=bmc.GEM_MAIA_MAX_PROB, **_WIDE_MARGIN),
    ),
    (
        "great_boundary_exactly_great_max",
        dict(maia_prob=bmc.GREAT_MAIA_MAX_PROB, **_WIDE_MARGIN),
    ),
    (
        "neither_margin_narrow_band_low_prob",
        dict(
            maia_prob=0.10,
            best_cp=_NARROW_BAND_BEST_CP,
            best_mate=None,
            second_cp=0,
            second_mate=None,
            mover_color="white",
        ),
    ),
    (
        "neither_margin_narrow_band_high_prob",
        dict(
            maia_prob=0.60,
            best_cp=_NARROW_BAND_BEST_CP,
            best_mate=None,
            second_cp=0,
            second_mate=None,
            mover_color="white",
        ),
    ),
    (
        "gem_mate_best_white_mover",
        dict(
            maia_prob=0.10,
            best_cp=None,
            best_mate=2,
            second_cp=0,
            second_mate=None,
            mover_color="white",
        ),
    ),
    (
        "gem_mate_best_black_mover",
        dict(
            maia_prob=0.10,
            best_cp=None,
            best_mate=-2,  # black has mate -> good for a black mover
            second_cp=0,
            second_mate=None,
            mover_color="black",
        ),
    ),
    (
        "neither_missing_best_eval",
        dict(
            maia_prob=0.10,
            best_cp=None,
            best_mate=None,
            second_cp=0,
            second_mate=None,
            mover_color="white",
        ),
    ),
    (
        "neither_narrow_margin_low_prob",
        dict(maia_prob=0.15, **_NARROW_MARGIN),
    ),
]


async def _eval_tier_sql(
    session: AsyncSession,
    *,
    maia_prob: float,
    best_cp: int | None,
    best_mate: int | None,
    second_cp: int | None,
    second_mate: int | None,
    mover_color: MoverColor,
) -> str | None:
    """Evaluate best_move_tier_sql(literal(...)) via a real DB query.

    Code-reading alone cannot prove func.exp()-based SQL agrees with the Python
    sigmoid — only a live evaluation closes the trap (mirrors TestIsOpponentExpr
    in tests/services/test_flaws_service.py).
    """
    expr = bmc.best_move_tier_sql(
        literal(maia_prob, type_=Float),
        literal(best_cp, type_=Integer),
        literal(best_mate, type_=Integer),
        literal(second_cp, type_=Integer),
        literal(second_mate, type_=Integer),
        literal(mover_color, type_=String),
    )
    result = await session.execute(select(expr))
    return result.scalar_one()


@pytest.mark.parametrize(
    "params", [p for _, p in _TIER_SQL_FIXTURE_MATRIX], ids=[i for i, _ in _TIER_SQL_FIXTURE_MATRIX]
)
@pytest.mark.asyncio
async def test_tier_sql_agrees_with_classify_best_move(
    db_session: AsyncSession, params: _ClassifyKwargs
) -> None:
    """best_move_tier_sql (SQL twin) agrees with classify_best_move (Python) on
    every fixture-matrix case, including the GEM/GREAT boundary, the narrow
    [0.05, 0.10) margin band (Pitfall 3 — NEITHER regardless of maia_prob), and
    mate-based bests for both mover colors.

    The expected value is DERIVED from classify_best_move itself (never a
    hand-computed literal), so the two implementations cannot silently drift
    apart — a hardcoded expected string would not catch that.
    """
    expected = bmc.classify_best_move(**params)
    expected_tier = None if expected == "neither" else expected

    actual = await _eval_tier_sql(db_session, **params)

    assert actual == expected_tier, (
        f"SQL twin disagreed with classify_best_move for {params}: "
        f"sql={actual!r} python={expected!r}"
    )
