"""PGN header stamping for stored bot games (quick-260714-qaj).

This module is the SINGLE writer of the header block stamped onto a stored
`platform='flawchess'` bot game's PGN. Per D-01: the header block is stamped
SERVER-SIDE, from server-derived data only. Whatever the client sent for the
Seven Tag Roster (or any other header) is OVERWRITTEN, never trusted — see
`stamp_bot_game_headers`'s clear-then-rebuild recipe (F-1).

Per D-03/D-05/D-06: the target header block is a lichess-comparable Seven Tag
Roster plus GameId/UTCDate/UTCTime/Elo/Title/Variant/TimeControl/ECO/Opening/
Termination, followed by two non-standard tags (RatingSource, PlayStyleBlend)
LAST — D-06 requires these to come after every standard/lichess-recognized tag.
"""

import datetime
import io

import chess.pgn

from app.core.config import settings
from app.schemas.bots import RatingSource
from app.schemas.normalization import NormalizedGame

# Named constants for literal header VALUES (CLAUDE.md: no magic strings).
# Header KEY names are not hoisted into constants — they appear exactly once
# each inside the single ordered builder list in `_build_header_pairs`, and
# that list IS the spec.
PGN_EVENT = "FlawChess bot game"
PGN_ROUND = "-"
# F-2: python-chess's str(game) calls game.board(), which calls
# chess.variant.find_variant(headers["Variant"]) and RAISES on an unknown
# name. "Standard" is a valid python-chess alias — any other value would blow
# up serialization.
PGN_VARIANT = "Standard"
PGN_BOT_TITLE = "BOT"

_PGN_DATE_FORMAT = "%Y.%m.%d"
_PGN_TIME_FORMAT = "%H:%M:%S"
_PLAY_STYLE_BLEND_DECIMALS = 2
_SITE_PATH_TEMPLATE = "/analysis?game_id={game_id}"


def _build_header_pairs(
    *,
    normalized: NormalizedGame,
    game_id: int,
    tc_preset: str,
    rating_source: RatingSource | None,
    play_style_blend: float,
    played_at: datetime.datetime,
) -> list[tuple[str, str]]:
    """Build the D-03 ordered header pairs, omitting D-05 absent-value tags.

    `played_at` is passed in already non-None (the caller narrows it) so `ty`
    can verify the `.strftime` calls without a redundant guard here.
    """
    date_str = played_at.strftime(_PGN_DATE_FORMAT)
    site = settings.FRONTEND_URL.rstrip("/") + _SITE_PATH_TEMPLATE.format(game_id=game_id)

    pairs: list[tuple[str, str]] = [
        ("Event", PGN_EVENT),
        ("Site", site),
        ("Date", date_str),
        ("Round", PGN_ROUND),
        ("White", normalized.white_username),
        ("Black", normalized.black_username),
        ("Result", normalized.result),
        ("GameId", normalized.platform_game_id),
        ("UTCDate", date_str),
        ("UTCTime", played_at.strftime(_PGN_TIME_FORMAT)),
    ]

    if normalized.white_rating is not None:  # D-05: omit, never "?"/"0"
        pairs.append(("WhiteElo", str(normalized.white_rating)))
    if normalized.black_rating is not None:
        pairs.append(("BlackElo", str(normalized.black_rating)))

    # BOT title goes on the BOT's color only — the color OPPOSITE user_color.
    if normalized.user_color == "white":
        pairs.append(("BlackTitle", PGN_BOT_TITLE))
    else:
        pairs.append(("WhiteTitle", PGN_BOT_TITLE))

    pairs.append(("Variant", PGN_VARIANT))
    pairs.append(("TimeControl", tc_preset))  # F-3: NOT normalized.time_control_str

    if normalized.opening_eco is not None:
        pairs.append(("ECO", normalized.opening_eco))
    if normalized.opening_name is not None:
        pairs.append(("Opening", normalized.opening_name))

    # D-04: FlawChess closed vocab, NOT lichess's flat "Normal".
    pairs.append(("Termination", normalized.termination))

    if rating_source is not None:  # D-05: omit when no anchor
        pairs.append(("RatingSource", rating_source))
    pairs.append(("PlayStyleBlend", f"{play_style_blend:.{_PLAY_STYLE_BLEND_DECIMALS}f}"))

    return pairs


def stamp_bot_game_headers(
    *,
    normalized: NormalizedGame,
    game_id: int,
    tc_preset: str,
    rating_source: RatingSource | None,
    play_style_blend: float,
) -> str:
    """Return `normalized.pgn` re-serialized with the full D-03 header block.

    Re-parses `normalized.pgn`, clears every existing header (defeating any
    client-supplied Event/Site/White/Black/Elo/Title — T-qaj-01), then assigns
    the D-03-ordered header pairs and re-serializes via `str(game)` (F-1). The
    per-move `[%clk]` comments on the mainline survive unchanged.

    Args:
        normalized: The already-normalized bot game (server-derived fields
            only — this function never re-derives anything from raw request
            data).
        game_id: The row's real auto-increment `games.id`, known only
            post-INSERT (D-07) — used to build the `Site` deep link.
        tc_preset: The request's original `base+inc` seconds string (e.g.
            "600+0"). F-3: NOT `normalized.time_control_str`, which strips a
            zero increment.
        rating_source: The derived rating provenance, or None when the user
            has no rating anchor for this TC bucket (D-05).
        play_style_blend: The Maia/Stockfish blend in [0, 1].

    Returns:
        The re-serialized PGN string with the full header block.

    Raises:
        RuntimeError: `normalized.pgn` fails to re-parse, or `played_at` is
            None. Both are structurally unreachable — `normalize_flawchess_
            game` already parsed this exact PGN successfully and always sets
            `played_at` — so no variables are embedded in the message
            (Sentry grouping rule). The caller's existing try/except in
            `store_bot_game` captures this.
    """
    game = chess.pgn.read_game(io.StringIO(normalized.pgn))
    if game is None:
        raise RuntimeError("bot-game PGN failed to re-parse for header stamping")

    if normalized.played_at is None:
        raise RuntimeError("bot-game PGN has no played_at for header stamping")

    pairs = _build_header_pairs(
        normalized=normalized,
        game_id=game_id,
        tc_preset=tc_preset,
        rating_source=rating_source,
        play_style_blend=play_style_blend,
        played_at=normalized.played_at,
    )

    # F-1: clear every existing header (including the Seven Tag Roster) before
    # rebuilding, so non-STR client tags (e.g. TimeControl/Termination) don't
    # land ahead of the newly-added ones and break D-06's tag order.
    for key in list(game.headers.keys()):
        del game.headers[key]
    for key, value in pairs:
        game.headers[key] = value

    return str(game)
