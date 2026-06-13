"""Tests for evaluate_nodes_with_pv PV capture (Phase 117 EVAL-04).

TDD RED tests: verify the PV extractors and evaluate_nodes_with_pv function.
"""

from __future__ import annotations

import chess
import chess.engine

from app.services.engine import (
    PV_CAP_PLIES,
    _pv_to_best_move,
    _pv_to_uci_string,
)


# ─── _pv_to_best_move ─────────────────────────────────────────────────────────


class TestPvToBestMove:
    """Unit tests for the _pv_to_best_move extractor."""

    def test_empty_dict_returns_none(self) -> None:
        """InfoDict with no 'pv' key returns None."""
        result = _pv_to_best_move({})
        assert result is None, "Empty InfoDict should return None"

    def test_none_pv_returns_none(self) -> None:
        """InfoDict with pv=None returns None."""
        result = _pv_to_best_move({"pv": None})  # ty: ignore[invalid-argument-type]  # defensive: test pv=None handling
        assert result is None, "pv=None should return None"

    def test_empty_pv_returns_none(self) -> None:
        """InfoDict with empty pv list returns None."""
        result = _pv_to_best_move({"pv": []})  # type: ignore[arg-type]
        assert result is None, "Empty pv list should return None"

    def test_single_move_returns_uci(self) -> None:
        """InfoDict with one move returns its UCI string."""
        move = chess.Move.from_uci("e2e4")
        result = _pv_to_best_move({"pv": [move]})  # type: ignore[arg-type]
        assert result == "e2e4", f"Expected 'e2e4', got {result!r}"

    def test_multi_move_returns_first_uci(self) -> None:
        """InfoDict with multiple moves returns only the first move's UCI."""
        moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]
        result = _pv_to_best_move({"pv": moves})  # type: ignore[arg-type]
        assert result == "e2e4", f"Expected 'e2e4' (first move), got {result!r}"

    def test_promotion_move_returns_5char_uci(self) -> None:
        """Promotion moves return 5-char UCI (D-117-03: varchar(5) covers promotions)."""
        move = chess.Move.from_uci("e7e8q")
        result = _pv_to_best_move({"pv": [move]})  # type: ignore[arg-type]
        assert result == "e7e8q", f"Expected 'e7e8q', got {result!r}"


# ─── _pv_to_uci_string ────────────────────────────────────────────────────────


class TestPvToUciString:
    """Unit tests for the _pv_to_uci_string extractor."""

    def test_empty_dict_returns_none(self) -> None:
        """InfoDict with no 'pv' key returns None."""
        result = _pv_to_uci_string({})
        assert result is None, "Empty InfoDict should return None"

    def test_empty_pv_returns_none(self) -> None:
        """InfoDict with empty pv list returns None."""
        result = _pv_to_uci_string({"pv": []})  # type: ignore[arg-type]
        assert result is None, "Empty pv list should return None"

    def test_two_moves_space_joined(self) -> None:
        """Two moves are space-joined in UCI format."""
        moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]
        result = _pv_to_uci_string({"pv": moves})  # type: ignore[arg-type]
        assert result == "e2e4 e7e5", f"Expected 'e2e4 e7e5', got {result!r}"

    def test_cap_applies(self) -> None:
        """Moves beyond PV_CAP_PLIES are truncated."""
        # Build 15 moves (more than PV_CAP_PLIES=12)
        squares = list(chess.SQUARES)
        moves = [chess.Move(squares[i], squares[i + 1]) for i in range(15)]
        result = _pv_to_uci_string({"pv": moves})  # type: ignore[arg-type]
        assert result is not None
        parts = result.split(" ")
        assert len(parts) == PV_CAP_PLIES, (
            f"Expected {PV_CAP_PLIES} moves after cap, got {len(parts)}"
        )

    def test_custom_cap(self) -> None:
        """Custom cap parameter truncates at the specified count."""
        moves = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
            chess.Move.from_uci("g1f3"),
        ]
        result = _pv_to_uci_string({"pv": moves}, cap=2)  # type: ignore[arg-type]
        assert result == "e2e4 e7e5", f"Expected 2-move truncation, got {result!r}"

    def test_pv_cap_plies_is_12(self) -> None:
        """PV_CAP_PLIES constant is 12 (D-117-02: ~12-ply cap)."""
        assert PV_CAP_PLIES == 12, f"Expected PV_CAP_PLIES=12, got {PV_CAP_PLIES}"
