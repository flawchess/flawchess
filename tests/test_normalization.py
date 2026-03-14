"""Tests for normalization utilities: parse_time_control, normalize_chesscom_game, normalize_lichess_game."""


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
                             uuid="test-uuid-123", rated=True,
                             white_is_computer=False, black_is_computer=False,
                             eco_url="https://www.chess.com/openings/Kings-Pawn-Opening-C40",
                             event="Live Chess"):
        white = {
            "username": white_user,
            "rating": 2800,
            "result": white_result,
        }
        black = {
            "username": black_user,
            "rating": 2750,
            "result": black_result,
        }
        if white_is_computer:
            white["is_computer"] = True
        if black_is_computer:
            black["is_computer"] = True
        game = {
            "uuid": uuid,
            "url": f"https://www.chess.com/game/live/{uuid}",
            "pgn": f'[Event "{event}"]\n[White "Magnus"]\n[Black "Hikaru"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 *',
            "rules": rules,
            "time_control": time_control,
            "rated": rated,
            "end_time": 1700000000,  # Unix seconds
            "white": white,
            "black": black,
        }
        if eco_url is not None:
            game["eco"] = eco_url
        return game

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

    def test_computer_opponent_flagged(self):
        """User plays white, opponent (black) has is_computer=True -> is_computer_game=True."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="Magnus", black_user="StockfishBot",
                                         black_is_computer=True)
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True

    def test_computer_opponent_as_black_flagged(self):
        """User plays black, opponent (white) has is_computer=True -> is_computer_game=True."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(white_user="StockfishBot", black_user="Magnus",
                                         white_result="checkmated", black_result="win",
                                         white_is_computer=True)
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True

    def test_human_opponent_not_flagged(self):
        """Neither player has is_computer field -> is_computer_game=False."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game()
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is False

    def test_play_vs_coach_pgn_event_flagged(self):
        """PGN Event 'Play vs Coach' without is_computer field -> is_computer_game=True."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(event="Play vs Coach")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True

    def test_play_vs_computer_pgn_event_flagged(self):
        """PGN Event 'Play vs Computer' without is_computer field -> is_computer_game=True."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(event="Play vs Computer")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True

    def test_opening_name_from_eco_url(self):
        """ECO URL with C40 suffix -> opening_name='Kings Pawn Opening'."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(eco_url="https://www.chess.com/openings/Kings-Pawn-Opening-C40")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["opening_name"] == "Kings Pawn Opening"

    def test_opening_name_no_eco_suffix(self):
        """ECO URL slug with no ECO code -> opening_name from slug with hyphens replaced."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(eco_url="https://www.chess.com/openings/Sicilian-Defense")
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["opening_name"] == "Sicilian Defense"

    def test_opening_name_none_when_no_eco(self):
        """No eco field -> opening_name=None."""
        from app.services.normalization import normalize_chesscom_game
        game = self._make_chesscom_game(eco_url=None)
        result = normalize_chesscom_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["opening_name"] is None


class TestNormalizeLichessGame:
    """Tests for normalize_lichess_game function."""

    def _make_lichess_game(self, white_user="Magnus", black_user="Hikaru",
                            winner=None, variant_key="standard",
                            clock_initial=600, clock_increment=0,
                            game_id="q7ZvsdUF", rated=True,
                            white_title=None, black_title=None):
        white_user_obj = {"name": white_user, "id": white_user.lower()}
        black_user_obj = {"name": black_user, "id": black_user.lower()}
        if white_title is not None:
            white_user_obj["title"] = white_title
        if black_title is not None:
            black_user_obj["title"] = black_title
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
                    "user": white_user_obj,
                    "rating": 2800,
                },
                "black": {
                    "user": black_user_obj,
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

    def test_bot_opponent_flagged(self):
        """Opponent (black) has title='BOT' -> is_computer_game=True."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(white_user="Magnus", black_user="Stockfish",
                                        black_title="BOT")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True

    def test_human_opponent_not_flagged(self):
        """No title field on opponent -> is_computer_game=False."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game()
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is False

    def test_bot_title_case_insensitive(self):
        """Opponent title='bot' (lowercase) -> is_computer_game=True."""
        from app.services.normalization import normalize_lichess_game
        game = self._make_lichess_game(white_user="Magnus", black_user="Stockfish",
                                        black_title="bot")
        result = normalize_lichess_game(game, "Magnus", user_id=1)
        assert result is not None
        assert result["is_computer_game"] is True


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


class TestChesscomEcoExtraction:
    """Tests for _extract_chesscom_eco and _extract_chesscom_opening_name functions.

    Covers standard ECO URLs, variation URLs with move notation, and edge cases.
    """

    def test_standard_eco_url_returns_code(self) -> None:
        """Standard URL with ECO code suffix returns the correct ECO code."""
        from app.services.normalization import _extract_chesscom_eco

        url = "https://www.chess.com/openings/Kings-Pawn-Opening-C40"
        result = _extract_chesscom_eco(url)
        assert result == "C40"

    def test_variation_url_with_move_notation_returns_none(self) -> None:
        """Variation URL containing move notation (e.g. '4.exd5') returns None.

        chess.com variation URLs like Kings-Gambit-Accepted-Modern-Defense-4.exd5
        contain move notation instead of ECO code — no A-E letter followed by 2 digits.
        """
        from app.services.normalization import _extract_chesscom_eco

        url = "https://www.chess.com/openings/Kings-Gambit-Accepted-Modern-Defense-4.exd5"
        result = _extract_chesscom_eco(url)
        assert result is None

    def test_url_with_no_eco_code_returns_none(self) -> None:
        """URL slug with no ECO code (e.g. 'Sicilian-Defense') returns None."""
        from app.services.normalization import _extract_chesscom_eco

        url = "https://www.chess.com/openings/Sicilian-Defense"
        result = _extract_chesscom_eco(url)
        assert result is None

    def test_none_input_returns_none(self) -> None:
        """None input returns None."""
        from app.services.normalization import _extract_chesscom_eco

        result = _extract_chesscom_eco(None)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string input returns None."""
        from app.services.normalization import _extract_chesscom_eco

        result = _extract_chesscom_eco("")
        assert result is None

    def test_another_eco_code_returned(self) -> None:
        """ECO code A00 is correctly extracted from a URL."""
        from app.services.normalization import _extract_chesscom_eco

        url = "https://www.chess.com/openings/Polish-Opening-A00"
        result = _extract_chesscom_eco(url)
        assert result == "A00"

    def test_opening_name_standard_url(self) -> None:
        """Standard URL with ECO suffix returns opening name without ECO code."""
        from app.services.normalization import _extract_chesscom_opening_name

        url = "https://www.chess.com/openings/Kings-Pawn-Opening-C40"
        result = _extract_chesscom_opening_name(url)
        assert result == "Kings Pawn Opening"

    def test_opening_name_variation_url(self) -> None:
        """Variation URL with move notation returns full slug as opening name.

        The slug includes move notation since there's no ECO code to strip.
        """
        from app.services.normalization import _extract_chesscom_opening_name

        url = "https://www.chess.com/openings/Kings-Gambit-Accepted-Modern-Defense-4.exd5"
        result = _extract_chesscom_opening_name(url)
        assert result == "Kings Gambit Accepted Modern Defense 4.exd5"

    def test_opening_name_no_eco_suffix(self) -> None:
        """URL slug with no ECO code returns opening name from slug."""
        from app.services.normalization import _extract_chesscom_opening_name

        url = "https://www.chess.com/openings/Sicilian-Defense"
        result = _extract_chesscom_opening_name(url)
        assert result == "Sicilian Defense"

    def test_opening_name_none_input_returns_none(self) -> None:
        """None input returns None."""
        from app.services.normalization import _extract_chesscom_opening_name

        result = _extract_chesscom_opening_name(None)
        assert result is None

    def test_opening_name_empty_string_returns_none(self) -> None:
        """Empty string input returns None."""
        from app.services.normalization import _extract_chesscom_opening_name

        result = _extract_chesscom_opening_name("")
        assert result is None
