"""Platform-agnostic normalization utilities.

Converts chess.com and lichess game objects into NormalizedGame Pydantic models (D-01).
"""

import datetime
import re
from app.schemas.normalization import (
    Color,
    GameResult,
    NormalizedGame,
    Termination,
    TimeControlBucket,
)
from app.services.opening_lookup import find_opening


def _normalize_tc_str(tc_str: str) -> str | None:
    """Normalize time control string: drop +0 suffix when increment is 0."""
    if not tc_str or tc_str == "-":
        return None
    if "+" in tc_str:
        base, inc = tc_str.split("+", 1)
        if inc == "0":
            return base
    return tc_str


def parse_time_control(tc_str: str) -> tuple[TimeControlBucket | None, int | None]:
    """Parse a time control string into (bucket, estimated_seconds).

    Examples:
        '600+0'   -> ('rapid', 600)
        '180+2'   -> ('blitz', 260)   # 180 + 2*40 = 260
        '60+0'    -> ('bullet', 60)
        '900+10'  -> ('rapid', 1300)  # 900 + 10*40 = 1300
        '1/259200' -> ('classical', None)  # daily format
        '-'       -> (None, None)
        ''        -> (None, None)

    Thresholds (estimated duration):
        < 180s   -> bullet
        < 600s   -> blitz
        <= 1800s -> rapid
        else     -> classical
    """
    if not tc_str or tc_str == "-":
        return None, None

    try:
        if "+" in tc_str:
            base_str, increment_str = tc_str.split("+", 1)
            # Use float: chess.com emits fractional increments like "10+0.1" (0.1s bonus).
            # Previously `int("0.1")` raised ValueError, leaving the bucket NULL.
            base = float(base_str)
            increment = float(increment_str)
        elif "/" in tc_str:
            # Daily format like "1/259200" — classify as classical
            return "classical", None
        else:
            base = float(tc_str)
            increment = 0.0
    except (ValueError, AttributeError):
        return None, None

    estimated = int(base + increment * 40)

    if estimated < 180:
        return "bullet", estimated
    elif estimated < 600:
        return "blitz", estimated
    elif estimated <= 1800:
        return "rapid", estimated
    else:
        return "classical", estimated


# chess.com termination string mapping (losing player's result -> normalized termination)
_CHESSCOM_TERMINATION_MAP: dict[str, Termination] = {
    "checkmated": "checkmate",
    "resigned": "resignation",
    "timeout": "timeout",
    "timevsinsufficient": "draw",
    "agreed": "draw",
    "stalemate": "draw",
    "insufficient": "draw",
    "repetition": "draw",
    "50move": "draw",
    "abandoned": "abandoned",
}

# lichess game status -> normalized termination
_LICHESS_STATUS_MAP: dict[str, Termination] = {
    "mate": "checkmate",
    "resign": "resignation",
    "outoftime": "timeout",
    "draw": "draw",
    "stalemate": "draw",
    "threefoldRepetition": "draw",
    "fiftyMoves": "draw",
    "unknownFinish": "draw",
    "aborted": "abandoned",
    "timeout": "abandoned",
    "noStart": "abandoned",
    "cheat": "unknown",
}

# chess.com PGN Event tag values that indicate a game against a computer
_CHESSCOM_COMPUTER_EVENTS = {"Play vs Coach", "Play vs Computer"}

# chess.com result strings that mean the player won
_CHESSCOM_WIN_RESULTS = {"win"}

# chess.com result strings that mean the game was a draw
_CHESSCOM_DRAW_RESULTS = {
    "agreed",
    "stalemate",
    "insufficient",
    "repetition",
    "timevsinsufficient",
    "50move",
}


def _normalize_chesscom_result(white_result: str, black_result: str) -> GameResult:
    """Convert chess.com result strings to standard "1-0"/"0-1"/"1/2-1/2".

    chess.com stores results from each player's perspective:
    - "win" means that player won
    - "checkmated", "resigned", "timeout" etc. mean that player lost
    - "agreed", "stalemate", etc. mean draw

    The actual game outcome is "1-0" if white won, "0-1" if black won,
    "1/2-1/2" for draws.
    """
    if white_result in _CHESSCOM_WIN_RESULTS:
        return "1-0"
    elif black_result in _CHESSCOM_WIN_RESULTS:
        return "0-1"
    elif white_result in _CHESSCOM_DRAW_RESULTS or black_result in _CHESSCOM_DRAW_RESULTS:
        return "1/2-1/2"
    else:
        # Fallback: try to determine from result strings
        # If neither is "win" and neither is a draw, one must have lost
        # "checkmated", "resigned", "timeout", "abandoned" etc. = loss for that player
        return "1/2-1/2"  # safe fallback


def normalize_chesscom_game(game: dict, username: str, user_id: int) -> NormalizedGame | None:
    """Normalize a chess.com JSON game object to a dict matching Game model columns.

    Returns None if the game is not a standard chess variant.

    Args:
        game: Raw chess.com game object from their API.
        username: The user's chess.com username (case-insensitive comparison).
        user_id: Internal user ID for the database.
    """
    # Filter non-standard variants
    if game.get("rules", "chess") != "chess":
        return None

    white = game["white"]
    black = game["black"]
    white_username = white["username"]
    black_username = black["username"]

    # Determine user's color (case-insensitive)
    username_lower = username.lower()
    if white_username.lower() == username_lower:
        user_color = "white"
        opponent_player = black
    else:
        user_color = "black"
        opponent_player = white

    # PGN string (used for both computer detection and opening lookup)
    pgn_str = game.get("pgn", "") or ""

    # Computer detection via API field
    is_computer_game = bool(opponent_player.get("is_computer", False))
    # Fallback: detect via PGN Event tag (e.g. "Play vs Coach", "Play vs Computer")
    if not is_computer_game:
        event_match = re.search(r'\[Event\s+"([^"]+)"\]', pgn_str)
        if event_match and event_match.group(1) in _CHESSCOM_COMPUTER_EVENTS:
            is_computer_game = True

    # Normalize result
    white_result_str = white.get("result", "")
    black_result_str = black.get("result", "")
    result = _normalize_chesscom_result(white_result_str, black_result_str)

    # Determine termination from the losing side's result string
    if result == "1/2-1/2":
        termination_raw = white_result_str  # both sides have same draw string
    elif result == "1-0":
        termination_raw = black_result_str  # loser's result describes termination
    else:  # 0-1
        termination_raw = white_result_str
    termination = _CHESSCOM_TERMINATION_MAP.get(termination_raw, "unknown")

    # Time control
    tc_str = game.get("time_control", "")
    tc_bucket, tc_seconds = parse_time_control(tc_str)

    # Timestamps
    end_time = game.get("end_time")
    played_at = None
    if end_time is not None:
        played_at = datetime.datetime.fromtimestamp(end_time, tz=datetime.timezone.utc)

    # Opening via longest-prefix match against openings.tsv
    opening_eco, opening_name = find_opening(pgn_str)

    # Engine analysis: game-level accuracy (only present for analyzed games)
    accuracies = game.get("accuracies", {})
    white_accuracy: float | None = accuracies.get("white")
    black_accuracy: float | None = accuracies.get("black")

    return NormalizedGame(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=game["uuid"],
        platform_url=game.get("url"),
        pgn=pgn_str,
        result=result,
        user_color=user_color,
        termination_raw=termination_raw,
        termination=termination,
        time_control_str=_normalize_tc_str(tc_str),
        time_control_bucket=tc_bucket,
        time_control_seconds=tc_seconds,
        rated=bool(game.get("rated", True)),
        is_computer_game=is_computer_game,
        white_username=white_username,
        black_username=black_username,
        white_rating=white.get("rating"),
        black_rating=black.get("rating"),
        opening_name=opening_name,
        opening_eco=opening_eco,
        white_accuracy=white_accuracy,
        black_accuracy=black_accuracy,
        played_at=played_at,
    )


def normalize_lichess_game(game: dict, username: str, user_id: int) -> NormalizedGame | None:
    """Normalize a lichess NDJSON game object to a NormalizedGame model.

    Returns None if the game is not a standard chess variant.

    Args:
        game: Raw lichess NDJSON game object.
        username: The user's lichess username (case-insensitive comparison).
        user_id: Internal user ID for the database.
    """
    # Filter non-standard variants
    variant = game.get("variant", {})
    if isinstance(variant, dict):
        variant_key = variant.get("key", "standard")
    else:
        variant_key = str(variant)

    if variant_key != "standard":
        return None

    players = game.get("players", {})
    white_player = players.get("white", {})
    black_player = players.get("black", {})

    # Lichess AI opponents have no `user` object — only `aiLevel`. Surface them
    # with the same display name lichess uses in PGN headers ("lichess AI level N")
    # instead of an empty string.
    def _player_name(player: dict) -> str:
        user = player.get("user") or {}
        name = user.get("name", "")
        if name:
            return name
        ai_level = player.get("aiLevel")
        if ai_level is not None:
            return f"lichess AI level {ai_level}"
        return ""

    white_username = _player_name(white_player)
    black_username = _player_name(black_player)

    # Determine user's color (case-insensitive)
    username_lower = username.lower()
    if white_username.lower() == username_lower:
        user_color: Color = "white"
        opponent_player = black_player
    else:
        user_color = "black"
        opponent_player = white_player

    # Computer detection: opponent is either a BOT-titled account or an `aiLevel` bot.
    # Previously we only checked the BOT title, so stockfish aiLevel games leaked through
    # as human games.
    opponent_title = (opponent_player.get("user") or {}).get("title", "")
    is_computer_game = opponent_title.upper() == "BOT" or opponent_player.get("aiLevel") is not None

    # Result from winner field
    winner = game.get("winner")
    if winner == "white":
        result: GameResult = "1-0"
    elif winner == "black":
        result = "0-1"
    else:
        result = "1/2-1/2"

    # Termination from status field
    status = game.get("status", "unknown")
    termination_raw = status
    termination = _LICHESS_STATUS_MAP.get(status, "unknown")

    # Time control from clock
    clock = game.get("clock")
    tc_bucket: TimeControlBucket | None
    if clock:
        clock_initial = clock.get("initial", 0)
        clock_increment = clock.get("increment", 0)
        tc_str_raw = f"{clock_initial}+{clock_increment}"
        tc_bucket, tc_seconds = parse_time_control(tc_str_raw)
        tc_str = _normalize_tc_str(tc_str_raw)
    elif game.get("speed") == "correspondence":
        # Correspondence games have no clock field — lichess uses daysPerTurn instead.
        # Normalize to chess.com's PGN daily format (1/{seconds_per_move}) so both platforms
        # share a single representation, and bucket as classical (same as chess.com daily).
        days_per_turn = game.get("daysPerTurn")
        tc_str = f"1/{days_per_turn * 86400}" if days_per_turn else None
        tc_bucket = "classical"
        tc_seconds = None
    else:
        tc_str = None
        tc_bucket = None
        tc_seconds = None

    # Timestamp: createdAt is in milliseconds
    created_at_ms = game.get("createdAt")
    if created_at_ms is not None:
        played_at = datetime.datetime.fromtimestamp(created_at_ms / 1000, tz=datetime.timezone.utc)
    else:
        played_at = None

    # PGN (requires pgnInJson=true parameter on lichess request)
    pgn = game.get("pgn", "")

    # Opening via longest-prefix match against openings.tsv
    opening_eco, opening_name = find_opening(pgn)

    game_id = game["id"]

    # Engine analysis: per-player accuracy (only present for analyzed games)
    white_analysis = white_player.get("analysis", {})
    black_analysis = black_player.get("analysis", {})

    return NormalizedGame(
        user_id=user_id,
        platform="lichess",
        platform_game_id=game_id,
        platform_url=f"https://lichess.org/{game_id}",
        pgn=pgn,
        result=result,
        user_color=user_color,
        termination_raw=termination_raw,
        termination=termination,
        time_control_str=tc_str,
        time_control_bucket=tc_bucket,
        time_control_seconds=tc_seconds,
        rated=bool(game.get("rated", True)),
        is_computer_game=is_computer_game,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_player.get("rating"),
        black_rating=black_player.get("rating"),
        opening_name=opening_name,
        opening_eco=opening_eco,
        white_accuracy=white_analysis.get("accuracy"),
        black_accuracy=black_analysis.get("accuracy"),
        white_acpl=white_analysis.get("acpl"),
        black_acpl=black_analysis.get("acpl"),
        white_inaccuracies=white_analysis.get("inaccuracy"),
        black_inaccuracies=black_analysis.get("inaccuracy"),
        white_mistakes=white_analysis.get("mistake"),
        black_mistakes=black_analysis.get("mistake"),
        white_blunders=white_analysis.get("blunder"),
        black_blunders=black_analysis.get("blunder"),
        played_at=played_at,
    )
