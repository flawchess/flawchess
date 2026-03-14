"""Platform-agnostic normalization utilities.

Converts chess.com and lichess game objects into dicts matching the Game model columns.
"""

import datetime
import re

from app.services.opening_lookup import find_opening


def parse_time_control(tc_str: str) -> tuple[str | None, int | None]:
    """Parse a time control string into (bucket, estimated_seconds).

    Examples:
        '600+0'   -> ('blitz', 600)
        '180+2'   -> ('blitz', 260)   # 180 + 2*40 = 260
        '60+0'    -> ('bullet', 60)
        '900+10'  -> ('rapid', 1300)  # 900 + 10*40 = 1300
        '1/259200' -> ('classical', None)  # daily format
        '-'       -> (None, None)
        ''        -> (None, None)

    Thresholds (estimated duration):
        <= 180s  -> bullet
        <= 600s  -> blitz
        <= 1800s -> rapid
        else     -> classical
    """
    if not tc_str or tc_str == "-":
        return None, None

    try:
        if "+" in tc_str:
            base_str, increment_str = tc_str.split("+", 1)
            base = int(base_str)
            increment = int(increment_str)
        elif "/" in tc_str:
            # Daily format like "1/259200" — classify as classical
            return "classical", None
        else:
            base = int(tc_str)
            increment = 0
    except (ValueError, AttributeError):
        return None, None

    estimated = base + increment * 40

    if estimated <= 180:
        return "bullet", estimated
    elif estimated <= 600:
        return "blitz", estimated
    elif estimated <= 1800:
        return "rapid", estimated
    else:
        return "classical", estimated


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


def _normalize_chesscom_result(white_result: str, black_result: str) -> str:
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


def normalize_chesscom_game(game: dict, username: str, user_id: int) -> dict | None:
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
        user_rating = white.get("rating")
        opponent_rating = black.get("rating")
        opponent_username = black_username
        opponent_player = black
    else:
        user_color = "black"
        user_rating = black.get("rating")
        opponent_rating = white.get("rating")
        opponent_username = white_username
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
    result = _normalize_chesscom_result(white.get("result", ""), black.get("result", ""))

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

    return {
        "user_id": user_id,
        "platform": "chess.com",
        "platform_game_id": game["uuid"],
        "platform_url": game.get("url"),
        "pgn": pgn_str,
        "variant": "Standard",
        "result": result,
        "user_color": user_color,
        "time_control_str": tc_str if tc_str else None,
        "time_control_bucket": tc_bucket,
        "time_control_seconds": tc_seconds,
        "rated": bool(game.get("rated", True)),
        "is_computer_game": is_computer_game,
        "white_username": white_username,
        "black_username": black_username,
        "white_rating": white.get("rating"),
        "black_rating": black.get("rating"),
        "opponent_username": opponent_username,
        "opponent_rating": opponent_rating,
        "user_rating": user_rating,
        "opening_name": opening_name,
        "opening_eco": opening_eco,
        "played_at": played_at,
    }


def normalize_lichess_game(game: dict, username: str, user_id: int) -> dict | None:
    """Normalize a lichess NDJSON game object to a dict matching Game model columns.

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
    white_user = white_player.get("user", {})
    black_user = black_player.get("user", {})

    white_username = white_user.get("name", "")
    black_username = black_user.get("name", "")

    # Determine user's color (case-insensitive)
    username_lower = username.lower()
    if white_username.lower() == username_lower:
        user_color = "white"
        user_rating = white_player.get("rating")
        opponent_rating = black_player.get("rating")
        opponent_username = black_username or None
        opponent_player = black_player
    else:
        user_color = "black"
        user_rating = black_player.get("rating")
        opponent_rating = white_player.get("rating")
        opponent_username = white_username or None
        opponent_player = white_player

    # Computer detection: check if opponent is a BOT account
    opponent_title = opponent_player.get("user", {}).get("title", "")
    is_computer_game = opponent_title.upper() == "BOT"

    # Result from winner field
    winner = game.get("winner")
    if winner == "white":
        result = "1-0"
    elif winner == "black":
        result = "0-1"
    else:
        result = "1/2-1/2"

    # Time control from clock
    clock = game.get("clock")
    if clock:
        clock_initial = clock.get("initial", 0)
        clock_increment = clock.get("increment", 0)
        tc_str = f"{clock_initial}+{clock_increment}"
        tc_bucket, tc_seconds = parse_time_control(tc_str)
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

    return {
        "user_id": user_id,
        "platform": "lichess",
        "platform_game_id": game_id,
        "platform_url": f"https://lichess.org/{game_id}",
        "pgn": pgn,
        "variant": "Standard",
        "result": result,
        "user_color": user_color,
        "time_control_str": tc_str,
        "time_control_bucket": tc_bucket,
        "time_control_seconds": tc_seconds,
        "rated": bool(game.get("rated", True)),
        "is_computer_game": is_computer_game,
        "white_username": white_username,
        "black_username": black_username,
        "white_rating": white_player.get("rating"),
        "black_rating": black_player.get("rating"),
        "opponent_username": opponent_username,
        "opponent_rating": opponent_rating,
        "user_rating": user_rating,
        "opening_name": opening_name,
        "opening_eco": opening_eco,
        "played_at": played_at,
    }
