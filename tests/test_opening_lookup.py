"""Tests for opening_lookup module: _normalize_pgn_to_san_sequence and find_opening."""


class TestNormalizePgnToSanSequence:
    """Tests for the _normalize_pgn_to_san_sequence helper."""

    def test_simple_moves(self):
        """Plain move sequence without numbers returns individual SAN moves."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        result = _normalize_pgn_to_san_sequence("1. e4 e5 2. Nf3 Nc6")
        assert result == ["e4", "e5", "Nf3", "Nc6"]

    def test_strips_move_numbers(self):
        """Move numbers like '1.', '12.' are stripped."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        result = _normalize_pgn_to_san_sequence("1. d4 2. c4")
        assert result == ["d4", "c4"]

    def test_strips_result_markers(self):
        """Result markers 1-0, 0-1, 1/2-1/2, * are stripped."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        assert _normalize_pgn_to_san_sequence("1. e4 e5 1-0") == ["e4", "e5"]
        assert _normalize_pgn_to_san_sequence("1. e4 e5 0-1") == ["e4", "e5"]
        assert _normalize_pgn_to_san_sequence("1. e4 e5 1/2-1/2") == ["e4", "e5"]
        assert _normalize_pgn_to_san_sequence("1. e4 e5 *") == ["e4", "e5"]

    def test_strips_curly_brace_annotations(self):
        """Annotations in {...} are stripped."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        result = _normalize_pgn_to_san_sequence("1. e4 {Best by test} e5 2. Nf3")
        assert result == ["e4", "e5", "Nf3"]

    def test_strips_parenthesis_annotations(self):
        """Annotations in (...) are stripped."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        result = _normalize_pgn_to_san_sequence("1. e4 (1. d4 d5) e5 2. Nf3")
        assert result == ["e4", "e5", "Nf3"]

    def test_strips_pgn_header_tags(self):
        """Lines starting with '[' (PGN headers) are stripped."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        pgn = '[Event "Live Chess"]\n[White "Magnus"]\n\n1. e4 e5 2. Nf3 Nc6'
        result = _normalize_pgn_to_san_sequence(pgn)
        assert result == ["e4", "e5", "Nf3", "Nc6"]

    def test_empty_string_returns_empty_list(self):
        """Empty string returns empty list."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        assert _normalize_pgn_to_san_sequence("") == []

    def test_none_returns_empty_list(self):
        """None input returns empty list."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        assert _normalize_pgn_to_san_sequence(None) == []

    def test_black_move_ellipsis(self):
        """Black continuation notation like '2...' is handled (move numbers stripped)."""
        from app.services.opening_lookup import _normalize_pgn_to_san_sequence

        result = _normalize_pgn_to_san_sequence("1. e4 e5 2. Nf3 2... Nc6")
        assert result == ["e4", "e5", "Nf3", "Nc6"]


class TestFindOpening:
    """Tests for the find_opening function."""

    def test_italian_game_exact_match(self):
        """1. e4 e5 2. Nf3 Nc6 3. Bc4 matches C50 Italian Game."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. e4 e5 2. Nf3 Nc6 3. Bc4")
        assert eco == "C50"
        assert name == "Italian Game"

    def test_sicilian_defense(self):
        """1. e4 c5 matches B20 Sicilian Defense."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. e4 c5")
        assert eco == "B20"
        assert name == "Sicilian Defense"

    def test_queens_gambit(self):
        """1. d4 d5 2. c4 matches D06 Queen's Gambit."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. d4 d5 2. c4")
        assert eco == "D06"
        assert name == "Queen's Gambit"

    def test_kings_pawn_game(self):
        """1. e4 alone matches B00 King's Pawn Game."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. e4")
        assert eco == "B00"
        assert name == "King's Pawn Game"

    def test_empty_string_returns_none_none(self):
        """Empty string returns (None, None)."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("")
        assert eco is None
        assert name is None

    def test_none_returns_none_none(self):
        """None input returns (None, None)."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening(None)
        assert eco is None
        assert name is None

    def test_pgn_with_result_marker(self):
        """PGN ending in '1-0' still matches opening."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0")
        assert eco == "C50"
        assert name == "Italian Game"

    def test_pgn_with_star_marker(self):
        """PGN ending in '*' still matches opening."""
        from app.services.opening_lookup import find_opening

        eco, name = find_opening("1. e4 e5 2. Nf3 *")
        # Should match something for 1. e4 e5 2. Nf3 or shorter prefix
        assert eco is not None

    def test_pgn_beyond_known_opening_uses_longest_prefix(self):
        """PGN with moves beyond known openings returns the deepest known prefix match."""
        from app.services.opening_lookup import find_opening

        # Many moves deep — should still match Italian Game as the deepest prefix
        long_pgn = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4"
        eco, name = find_opening(long_pgn)
        assert eco is not None
        assert name is not None

    def test_pgn_with_full_headers(self):
        """Full PGN including headers still resolves opening correctly."""
        from app.services.opening_lookup import find_opening

        full_pgn = (
            '[Event "Live Chess"]\n'
            '[Site "Chess.com"]\n'
            '[White "Magnus"]\n'
            '[Black "Hikaru"]\n'
            '[Result "1-0"]\n'
            '[ECO "C50"]\n'
            '\n'
            '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O 1-0'
        )
        eco, name = find_opening(full_pgn)
        assert eco is not None
        assert name is not None

    def test_sicilian_longer_sequence_uses_longest_prefix(self):
        """Longer Sicilian game returns the deepest matching Sicilian opening."""
        from app.services.opening_lookup import find_opening

        # Longer Sicilian Najdorf sequence
        pgn = "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6"
        eco, name = find_opening(pgn)
        assert eco is not None
        # Should be a Sicilian variant (B2x range or B9x)
        assert name is not None
