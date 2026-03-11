"""Tests for normalization utilities: parse_time_control, normalize_chesscom_game, normalize_lichess_game."""

import pytest


class TestParseTimeControl:
    """Tests for parse_time_control function."""

    def test_blitz_no_increment(self):
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("600+0")
        assert bucket == "blitz"
        assert seconds == 600

    def test_blitz_with_increment(self):
        """180+2 -> 180 + 2*40 = 260, which is blitz."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("180+2")
        assert bucket == "blitz"
        assert seconds == 260

    def test_bullet(self):
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("60+0")
        assert bucket == "bullet"
        assert seconds == 60

    def test_rapid_with_increment(self):
        """900+10 -> 900 + 10*40 = 1300, which is rapid."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("900+10")
        assert bucket == "rapid"
        assert seconds == 1300

    def test_daily_format(self):
        """Daily format '1/259200' should be classical with None seconds."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("1/259200")
        assert bucket == "classical"
        assert seconds is None

    def test_dash_returns_none(self):
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("-")
        assert bucket is None
        assert seconds is None

    def test_empty_string_returns_none(self):
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("")
        assert bucket is None
        assert seconds is None

    def test_bullet_boundary(self):
        """Exactly 180s -> bullet."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("180+0")
        assert bucket == "bullet"
        assert seconds == 180

    def test_blitz_boundary(self):
        """Exactly 600s -> blitz."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("600+0")
        assert bucket == "blitz"
        assert seconds == 600

    def test_rapid_boundary(self):
        """Exactly 1800s -> rapid."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("1800+0")
        assert bucket == "rapid"
        assert seconds == 1800

    def test_classical(self):
        """Over 1800s -> classical."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("3600+0")
        assert bucket == "classical"
        assert seconds == 3600

    def test_no_increment(self):
        """No '+' in string, treat as base+0."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("300")
        assert bucket == "blitz"
        assert seconds == 300

    def test_invalid_string(self):
        """Non-parseable string returns None, None."""
        from app.services.normalization import parse_time_control
        bucket, seconds = parse_time_control("abc")
        assert bucket is None
        assert seconds is None


class TestNormalizeChesscomGame:
    """Tests for normalize_chesscom_game function."""

    def _make_chesscom_game(self, white_user="Magnus", black_user="Hikaru",
                             white_result="win", black_result="checkmated",
                             rules="chess", time_control="600+0",
                             uuid="test-uuid-123", rated=True):
        return {
            "uuid": uuid,
            "url": f"https://www.chess.com/game/live/{uuid}",
            "pgn": '[Event "Live Chess"]\n[White "Magnus"]\n[Black "Hikaru"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 *',
            "rules": rules,
            "time_control": time_control,
            "rated": rated,
            "end_time": 1700000000,  # Unix seconds
            "white": {
                "username": white_user,
                "rating": 2800,
                "result": white_result,
            },
            "black": {
                "username": black_user,
                "rating": 2750,
                "result": black_result,
            },
            "eco": "https://www.chess.com/openings/Kings-Pawn-Opening-C40",
        }

    def test_returns_dict_for_standard_game(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert isinstance(result, dict)

    def test_returns_none_for_chess960(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(rules="chess960")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is None

    def test_returns_none_for_bughouse(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(rules="bughouse")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is None

    def test_white_user_color(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", black_user="Hikaru")
        result = normalize_chesscom_game(game, "magnus", user_id=1)  # case insensitive
        assert result is not None
        assert result["user_color"] == "white"

    def test_black_user_color(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", black_user="Hikaru")
        result = normalize_chesscom_game(game, "hikaru", user_id=1)  # case insensitive
        assert result is not None
        assert result["user_color"] == "black"

    def test_win_on_white_gives_1_0(self):
        """When user plays white and result='win', result should be '1-0'."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", white_result="win", black_result="checkmated")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "1-0"

    def test_loss_on_white_gives_0_1(self):
        """When user plays white and result='checkmated', result should be '0-1'."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", white_result="checkmated", black_result="win")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "0-1"

    def test_draw_gives_1_2_1_2(self):
        """When result is a draw type, result should be '1/2-1/2'."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", white_result="agreed", black_result="agreed")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "1/2-1/2"

    def test_stalemate_is_draw(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", white_result="stalemate", black_result="stalemate")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "1/2-1/2"

    def test_timeout_loss_for_black(self):
        """When white times out and black wins, result should be '0-1'."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", black_user="Hikaru",
                                         white_result="timeout", black_result="win")
        # From Hikaru's (black) perspective: black wins
        result = normalize_chesscom_game(game, "Hikaru", user_id=1)
        assert result is not None
        # white timed out -> black wins -> "0-1" (black wins in standard chess notation)
        assert result["result"] == "0-1"

    def test_platform_is_chesscom(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["platform"] == "chess.com"

    def test_platform_game_id_is_uuid(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(uuid="abc123")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["platform_game_id"] == "abc123"

    def test_played_at_is_datetime(self):
        """end_time (Unix seconds) should be converted to a datetime."""
        import datetime
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert isinstance(result["played_at"], datetime.datetime)

    def test_time_control_parsed(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(time_control="600+0")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["time_control_str"] == "600+0"
        assert result["time_control_bucket"] == "blitz"
        assert result["time_control_seconds"] == 600

    def test_opening_eco_extracted(self):
        """ECO code should be extracted from the eco URL field."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        # ECO from URL "https://www.chess.com/openings/Kings-Pawn-Opening-C40"
        assert result["opening_eco"] == "C40"

    def test_user_id_included(self):
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=42)
        assert result is not None
        assert result["user_id"] == 42


class TestNormalizeLichessGame:
    """Tests for normalize_lichess_game function."""

    def _make_lichess_game(self, white_user="Magnus", black_user="Hikaru",
                            winner=None, variant_key="standard",
                            clock_initial=600, clock_increment=0,
                            game_id="q7ZvsdUF", rated=True):
        game = {
            "id": game_id,
            "rated": rated,
            "variant": {"key": variant_key, "name": variant_key.title()},
            "speed": "blitz",
            "perf": "blitz",
            "createdAt": 1700000000000,  # ms timestamp
            "lastMoveAt": 1700000600000,
            "status": "mate",
            "players": {
                "white": {
                    "user": {"name": white_user, "id": white_user.lower()},
                    "rating": 2800,
                },
                "black": {
                    "user": {"name": black_user, "id": black_user.lower()},
                    "rating": 2750,
                },
            },
            "opening": {
                "eco": "B20",
                "name": "Sicilian Defense",
                "ply": 2,
            },
            "moves": "e4 c5 Nf3",
            "pgn": '[Event "?"]\\n[White "Magnus"]\\n[Black "Hikaru"]\\n\\n1. e4 c5 2. Nf3 *',
            "clock": {
                "initial": clock_initial,
                "increment": clock_increment,
                "totalTime": clock_initial,
            },
        }
        if winner is not None:
            game["winner"] = winner
        return game

    def test_returns_dict_for_standard_game(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert isinstance(result, dict)

    def test_returns_none_for_chess960(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(variant_key="chess960")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is None

    def test_returns_none_for_crazyhouse(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(variant_key="crazyhouse")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is None

    def test_white_user_color(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(white_user="Magnus", black_user="Hikaru")
        result = normalize_lichess_game(game, "magnus", user_id=1)
        assert result is not None
        assert result["user_color"] == "white"

    def test_black_user_color(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(white_user="Magnus", black_user="Hikaru")
        result = normalize_lichess_game(game, "Hikaru", user_id=1)
        assert result is not None
        assert result["user_color"] == "black"

    def test_white_wins(self):
        """winner='white' -> result='1-0'."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(winner="white")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "1-0"

    def test_black_wins(self):
        """winner='black' -> result='0-1'."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(winner="black")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "0-1"

    def test_draw_no_winner(self):
        """No winner field -> result='1/2-1/2'."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(winner=None)  # No winner key
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["result"] == "1/2-1/2"

    def test_played_at_from_ms(self):
        """createdAt in ms should be converted to datetime."""
        import datetime
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert isinstance(result["played_at"], datetime.datetime)
        # 1700000000000 ms = 1700000000 s
        expected = datetime.datetime.fromtimestamp(1700000000, tz=datetime.timezone.utc)
        assert result["played_at"] == expected

    def test_platform_is_lichess(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["platform"] == "lichess"

    def test_platform_url_constructed(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(game_id="q7ZvsdUF")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["platform_url"] == "https://lichess.org/q7ZvsdUF"

    def test_platform_game_id(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(game_id="q7ZvsdUF")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["platform_game_id"] == "q7ZvsdUF"

    def test_time_control_str_formatted(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(clock_initial=600, clock_increment=5)
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["time_control_str"] == "600+5"

    def test_opening_eco_and_name(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["opening_eco"] == "B20"
        assert result["opening_name"] == "Sicilian Defense"

    def test_user_id_included(self):
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=99)
        assert result is not None
        assert result["user_id"] == 99

    def test_no_clock_handles_gracefully(self):
        """Games without clock info should still normalize (no crash)."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        del game["clock"]
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["time_control_str"] is None
        assert result["time_control_bucket"] is None


class TestNormalizeChesscomResult:
    """Tests for chess.com result string mapping."""

    def test_win_result_white_wins(self):
        """White has 'win' -> result '1-0'."""
        from app.services.normalization import normalize_chesscom_game
        game = {
            "uuid": "test",
            "url": "https://chess.com/test",
            "pgn": "",
            "rules": "chess",
            "time_control": "600+0",
            "rated": True,
            "end_time": 1700000000,
            "white": {"username": "Alice", "rating": 1500, "result": "win"},
            "black": {"username": "Bob", "rating": 1500, "result": "checkmated"},
        }
        result = normalize_chesscom_game(game, "Alice", user_id=1)
        assert result is not None
        assert result["result"] == "1-0"

    def test_resigned_as_loss(self):
        """Black has 'resigned' -> white wins -> '1-0'."""
        from app.services.normalization import normalize_chesscom_game
        game = {
            "uuid": "test",
            "url": "https://chess.com/test",
            "pgn": "",
            "rules": "chess",
            "time_control": "600+0",
            "rated": True,
            "end_time": 1700000000,
            "white": {"username": "Alice", "rating": 1500, "result": "win"},
            "black": {"username": "Bob", "rating": 1500, "result": "resigned"},
        }
        result = normalize_chesscom_game(game, "Bob", user_id=1)
        assert result is not None
        # Bob plays black and resigned -> white wins = "1-0"
        assert result["result"] == "1-0"

    def test_insufficient_material_is_draw(self):
        from app.services.normalization import normalize_chesscom_game
        game = {
            "uuid": "test",
            "url": "https://chess.com/test",
            "pgn": "",
            "rules": "chess",
            "time_control": "600+0",
            "rated": True,
            "end_time": 1700000000,
            "white": {"username": "Alice", "rating": 1500, "result": "insufficient"},
            "black": {"username": "Bob", "rating": 1500, "result": "insufficient"},
        }
        result = normalize_chesscom_game(game, "Alice", user_id=1)
        assert result is not None
        assert result["result"] == "1/2-1/2"

    def test_repetition_is_draw(self):
        from app.services.normalization import normalize_chesscom_game
        game = {
            "uuid": "test",
            "url": "https://chess.com/test",
            "pgn": "",
            "rules": "chess",
            "time_control": "600+0",
            "rated": True,
            "end_time": 1700000000,
            "white": {"username": "Alice", "rating": 1500, "result": "repetition"},
            "black": {"username": "Bob", "rating": 1500, "result": "repetition"},
        }
        result = normalize_chesscom_game(game, "Alice", user_id=1)
        assert result is not None
        assert result["result"] == "1/2-1/2"
