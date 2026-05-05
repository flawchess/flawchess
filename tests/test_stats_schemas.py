"""Schema-additivity tests for OpeningWDL — Phase 80 fields are optional.

Verifies that:
- Existing callers with only the 14 legacy fields still parse correctly.
- The 6 Phase 80 MG-entry eval fields parse when present.
- Literal type for eval_confidence rejects invalid values.
- Optional fields default correctly when omitted.
"""

import pytest
from pydantic import ValidationError

from app.schemas.stats import MostPlayedOpeningsResponse, OpeningWDL

_LEGACY: dict[str, object] = dict(
    opening_eco="C50",
    opening_name="Italian Game",
    display_name="Italian Game",
    label="Italian Game (C50)",
    pgn="1. e4 e5 2. Nf3 Nc6 3. Bc4",
    fen="r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    full_hash="12345678901234567",
    wins=10,
    draws=2,
    losses=3,
    total=15,
    win_pct=66.7,
    draw_pct=13.3,
    loss_pct=20.0,
)


# --- Backward compatibility (legacy payload) -----------------------------


def test_opening_wdl_old_payload_still_parses() -> None:
    """Old payload without Phase 80 fields should parse and default correctly."""
    m = OpeningWDL.model_validate(_LEGACY)

    # MG-entry eval defaults
    assert m.eval_n == 0
    assert m.eval_confidence == "low"
    assert m.avg_eval_pawns is None
    assert m.eval_ci_low_pawns is None
    assert m.eval_ci_high_pawns is None
    assert m.eval_p_value is None


# --- Full Phase 80 payload (new fields) ----------------------------------


def test_opening_wdl_new_payload_parses() -> None:
    """All Phase 80 fields parse correctly and round-trip via model_dump."""
    payload: dict[str, object] = {
        **_LEGACY,
        # MG-entry eval
        "avg_eval_pawns": 0.15,
        "eval_ci_low_pawns": -0.05,
        "eval_ci_high_pawns": 0.35,
        "eval_n": 42,
        "eval_p_value": 0.032,
        "eval_confidence": "high",
    }
    m = OpeningWDL.model_validate(payload)

    # Round-trip: model_dump -> model_validate should produce identical object
    m2 = OpeningWDL.model_validate(m.model_dump())
    assert m2 == m

    # Spot-check new field values
    assert m.avg_eval_pawns == pytest.approx(0.15)
    assert m.eval_confidence == "high"


# --- Literal type enforcement -------------------------------------------


def test_eval_confidence_literal_rejects_invalid() -> None:
    """eval_confidence='bogus' should raise ValidationError."""
    payload: dict[str, object] = {**_LEGACY, "eval_confidence": "bogus"}
    with pytest.raises(ValidationError):
        OpeningWDL.model_validate(payload)


# --- Optional field defaults when omitted --------------------------------


def test_avg_eval_pawns_none_when_omitted() -> None:
    """avg_eval_pawns defaults to None when not supplied."""
    m = OpeningWDL.model_validate(_LEGACY)
    assert m.avg_eval_pawns is None


# --- MostPlayedOpeningsResponse: eval baselines (260504-my2) -------------


def test_most_played_response_carries_eval_baseline_pawns() -> None:
    """Wrapper carries per-color eval baselines in pawns (per-game mean,
    2026-05-04 Lichess benchmark) so the frontend can center the bullet
    chart on the same H0 the backend z-test uses.
    """
    resp = MostPlayedOpeningsResponse(
        white=[],
        black=[],
        eval_baseline_pawns_white=0.315,
        eval_baseline_pawns_black=-0.189,
    )
    assert resp.eval_baseline_pawns_white == pytest.approx(0.315)
    assert resp.eval_baseline_pawns_black == pytest.approx(-0.189)

    # Round-trip via model_dump preserves the baseline values.
    resp2 = MostPlayedOpeningsResponse.model_validate(resp.model_dump())
    assert resp2.eval_baseline_pawns_white == pytest.approx(0.315)
    assert resp2.eval_baseline_pawns_black == pytest.approx(-0.189)
