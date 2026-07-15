"""Schema tests for the bot-game store request/response (Phase 167 Plan 01).

Covers STORE-01..07 boundary contract: game_uuid UUID validation, play_style_blend
range, PGN size bound, and the absence of any server-owned field on the request
(T-167-01/T-167-02/T-167-03).
"""

from __future__ import annotations

import uuid
from typing import Any

import pydantic
import pytest

from app.schemas.bots import (
    MAX_BOT_PGN_LENGTH,
    _MAX_TC_PRESET_LENGTH,
    StoreBotGameRequest,
    StoreBotGameResponse,
)

# Typed as dict[str, Any] deliberately: these tests intentionally pass malformed
# values (wrong type/out-of-range) to assert Pydantic rejects them at runtime.
_VALID_KWARGS: dict[str, Any] = {
    "game_uuid": str(uuid.uuid4()),
    "pgn": '[Event "Test"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n',
    "user_color": "white",
    "bot_elo": 1400,
    "play_style_blend": 0.5,
    "tc_preset": "3+2",
}


def _kwargs_with(**overrides: Any) -> dict[str, Any]:
    """Return a copy of the valid kwargs with the given field(s) overridden."""
    merged: dict[str, Any] = dict(_VALID_KWARGS)
    merged.update(overrides)
    return merged


class TestStoreBotGameRequestValidation:
    """STORE request boundary contract."""

    def test_valid_request_parses(self) -> None:
        request = StoreBotGameRequest(**_VALID_KWARGS)
        assert request.game_uuid == _VALID_KWARGS["game_uuid"]
        assert request.bot_elo == 1400

    def test_non_uuid_game_uuid_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(game_uuid="not-a-uuid"))

    def test_play_style_blend_above_range_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(play_style_blend=1.5))

    def test_play_style_blend_below_range_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(play_style_blend=-0.1))

    def test_oversized_pgn_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(pgn="a" * (MAX_BOT_PGN_LENGTH + 1)))

    def test_bot_elo_out_of_range_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(bot_elo=100))

    def test_oversized_tc_preset_rejected(self) -> None:
        """CR-01: tc_preset must never overflow games.time_control_str String(50) —
        an unbounded value previously reached the INSERT unvalidated and crashed with
        an unhandled 500 (Postgres DataError) instead of a 422.
        """
        with pytest.raises(pydantic.ValidationError):
            StoreBotGameRequest(**_kwargs_with(tc_preset="a" * (_MAX_TC_PRESET_LENGTH + 1)))

    def test_no_server_owned_fields_on_request(self) -> None:
        """T-167-01: client cannot inject rating/platform/user_id/etc."""
        forbidden = {"rating", "platform", "user_id", "username", "is_computer_game"}
        present = forbidden & set(StoreBotGameRequest.model_fields.keys())
        assert present == set(), f"Server-owned fields leaked onto request: {present}"

    def test_game_uuid_canonicalized_across_spellings(self) -> None:
        """WR-01: differently-formatted representations of the same UUID (upper-case,
        braces, urn:uuid: prefix) must canonicalize to one identical stored value, or
        the D-11 "re-submit is a no-op" idempotency guarantee silently breaks.
        """
        raw = uuid.uuid4()
        canonical = str(raw)

        upper = StoreBotGameRequest(**_kwargs_with(game_uuid=canonical.upper()))
        braced = StoreBotGameRequest(**_kwargs_with(game_uuid=f"{{{canonical}}}"))
        urn = StoreBotGameRequest(**_kwargs_with(game_uuid=f"urn:uuid:{canonical}"))

        assert upper.game_uuid == canonical
        assert braced.game_uuid == canonical
        assert urn.game_uuid == canonical


class TestStoreBotGameResponse:
    def test_response_shape(self) -> None:
        response = StoreBotGameResponse(game_id=42, created=True)
        assert response.game_id == 42
        assert response.created is True
