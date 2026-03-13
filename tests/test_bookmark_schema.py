"""Tests for BookmarkResponse Pydantic schema validation."""

import json
from unittest.mock import MagicMock

import pytest

from app.schemas.bookmarks import BookmarkResponse


class TestBookmarkResponseFromORM:
    """Test BookmarkResponse.model_validate with ORM-like objects (int target_hash)."""

    def _make_orm_bookmark(self, target_hash=123456789012345678, moves=None):
        """Create a mock ORM Bookmark object."""
        obj = MagicMock()
        obj.id = 1
        obj.label = "Queen's Gambit"
        obj.target_hash = target_hash
        obj.fen = "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1"
        obj.moves = json.dumps(moves or ["d4", "d5"])
        obj.color = "white"
        obj.match_side = "full"
        obj.sort_order = 0
        return obj

    def test_model_validate_with_int_target_hash_succeeds(self):
        """BookmarkResponse.model_validate with ORM object (int target_hash) must succeed."""
        orm_obj = self._make_orm_bookmark(target_hash=123456789012345678)
        response = BookmarkResponse.model_validate(orm_obj)
        assert response.target_hash == "123456789012345678"

    def test_model_validate_returns_str_target_hash(self):
        """target_hash in the response must be a str, not int."""
        orm_obj = self._make_orm_bookmark(target_hash=987654321098765432)
        response = BookmarkResponse.model_validate(orm_obj)
        assert isinstance(response.target_hash, str)
        assert response.target_hash == "987654321098765432"

    def test_model_validate_deserializes_moves(self):
        """moves field should be deserialized from JSON string."""
        orm_obj = self._make_orm_bookmark(moves=["e4", "e5", "Nf3"])
        response = BookmarkResponse.model_validate(orm_obj)
        assert response.moves == ["e4", "e5", "Nf3"]

    def test_model_validate_preserves_other_fields(self):
        """All other fields should be correctly extracted from ORM object."""
        orm_obj = self._make_orm_bookmark()
        response = BookmarkResponse.model_validate(orm_obj)
        assert response.id == 1
        assert response.label == "Queen's Gambit"
        assert response.fen == "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1"
        assert response.color == "white"
        assert response.match_side == "full"
        assert response.sort_order == 0


class TestBookmarkResponseFromDict:
    """Regression tests: BookmarkResponse.model_validate with dict input (str target_hash)."""

    def _make_dict_bookmark(self, target_hash="123456789012345678", moves=None):
        return {
            "id": 2,
            "label": "Sicilian Defense",
            "target_hash": target_hash,
            "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "moves": moves if moves is not None else ["e4", "c5"],
            "color": "black",
            "match_side": "full",
            "sort_order": 1,
        }

    def test_model_validate_with_str_target_hash_succeeds(self):
        """BookmarkResponse.model_validate with dict (str target_hash) must still work."""
        data = self._make_dict_bookmark(target_hash="123456789012345678")
        response = BookmarkResponse.model_validate(data)
        assert response.target_hash == "123456789012345678"

    def test_model_validate_with_list_moves_passes_through(self):
        """moves as list[str] in dict input must pass through unchanged."""
        data = self._make_dict_bookmark(moves=["e4", "c5", "Nf3"])
        response = BookmarkResponse.model_validate(data)
        assert response.moves == ["e4", "c5", "Nf3"]

    def test_model_validate_with_json_string_moves_in_dict(self):
        """moves as JSON string in dict input should also be deserialized."""
        data = self._make_dict_bookmark()
        data["moves"] = json.dumps(["e4", "c5"])
        response = BookmarkResponse.model_validate(data)
        assert response.moves == ["e4", "c5"]
