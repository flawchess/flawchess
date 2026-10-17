"""Openings-only baseline-centred MG-entry eval finalizer (Phase 242, D-00 / D-13).

On the Openings surfaces the eval z-test runs against the per-colour engine
baseline (+25 cp White, -25 cp Black, ``opening_insights_constants.EVAL_BASELINE_*``),
not against 0 cp, so "typical for the colour" reads as neutral. ``avg_eval_pawns``
stays the RAW (uncentred) mean: labels keep the raw eval (SEED-204), only the verdict
inputs (p-value, confidence) are centred.

Openings-only by design. ``endgame_service`` must keep calling
``eval_confidence.compute_eval_confidence_bucket`` with its default ``baseline_cp=0``:
the endgame-entry eval is a different quantity and is NOT baseline-centred (Pitfall 1).
Do not change the primitive's default; this module passes the baseline explicitly.
"""

from typing import Literal, TypedDict

from app.repositories.stats_repository import OpeningPhaseEntryMetrics
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
    OPENING_INSIGHTS_CI_Z_95,
)
from app.services.score_confidence import VERDICT_CI_Z_99

CENTIPAWNS_PER_PAWN: float = 100.0

# The CI needs a sample variance, which needs at least two games.
MIN_EVAL_N_FOR_CI: int = 2


class OpeningEvalFields(TypedDict):
    """Finalized MG-entry eval fields for one opening row (all in pawns, user perspective)."""

    avg_eval_pawns: float | None
    eval_ci_low_pawns: float | None
    eval_ci_high_pawns: float | None
    eval_ci99_low_pawns: float | None
    eval_ci99_high_pawns: float | None
    eval_n: int
    eval_p_value: float | None
    eval_confidence: Literal["low", "medium", "high"]


def resolve_eval_baseline_pawns(color: Literal["white", "black"] | None) -> float:
    """Colour baseline in pawns. None means White, matching openings_service's convention."""
    if color == "black":
        return EVAL_BASELINE_PAWNS_BLACK
    return EVAL_BASELINE_PAWNS_WHITE


def empty_opening_eval_fields() -> OpeningEvalFields:
    """Fields for an opening with no usable MG-entry eval sample."""
    return OpeningEvalFields(
        avg_eval_pawns=None,
        eval_ci_low_pawns=None,
        eval_ci_high_pawns=None,
        eval_ci99_low_pawns=None,
        eval_ci99_high_pawns=None,
        eval_n=0,
        eval_p_value=None,
        eval_confidence="low",
    )


def finalize_opening_eval(
    pe: OpeningPhaseEntryMetrics | None, color: Literal["white", "black"] | None
) -> OpeningEvalFields:
    """Turn accumulated phase-entry sums into the eval verdict fields for one row.

    The z-test runs against the colour baseline (H0: mean == baseline). The 99% bounds
    reuse the same standard error as the 95% ones (ci99_half = ci_half * z99 / z95),
    so no second call to the primitive is needed.
    """
    if pe is None or pe.eval_n_mg <= 0:
        return empty_opening_eval_fields()

    baseline_cp = resolve_eval_baseline_pawns(color) * CENTIPAWNS_PER_PAWN
    confidence, p_value, mean_cp, ci_half_cp = compute_eval_confidence_bucket(
        pe.eval_sum_mg,
        pe.eval_sumsq_mg,
        pe.eval_n_mg,
        baseline_cp=baseline_cp,
    )
    fields = empty_opening_eval_fields()
    fields["avg_eval_pawns"] = mean_cp / CENTIPAWNS_PER_PAWN  # raw, uncentred
    fields["eval_n"] = pe.eval_n_mg
    fields["eval_p_value"] = p_value
    fields["eval_confidence"] = confidence
    if pe.eval_n_mg >= MIN_EVAL_N_FOR_CI:
        ci99_half_cp = ci_half_cp * VERDICT_CI_Z_99 / OPENING_INSIGHTS_CI_Z_95
        fields["eval_ci_low_pawns"] = (mean_cp - ci_half_cp) / CENTIPAWNS_PER_PAWN
        fields["eval_ci_high_pawns"] = (mean_cp + ci_half_cp) / CENTIPAWNS_PER_PAWN
        fields["eval_ci99_low_pawns"] = (mean_cp - ci99_half_cp) / CENTIPAWNS_PER_PAWN
        fields["eval_ci99_high_pawns"] = (mean_cp + ci99_half_cp) / CENTIPAWNS_PER_PAWN
    return fields
