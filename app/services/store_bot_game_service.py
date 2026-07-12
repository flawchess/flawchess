"""Store-on-finish service for POST /bots/games (Phase 167, STORE-01/03/05/06).

Orchestrates: server-side rating derivation (D-05/D-06/D-07) -> PGN-only
normalization (normalize_flawchess_game) -> the existing hot-lane persistence
path (import_service._flush_batch, D-09) -> a game-id lookup (Pitfall 2, no id
in _flush_batch's return) -> the one-to-one bot_game_settings insert -> a single
commit (D-10). The service owns the transaction boundary; _flush_batch itself
never commits (WR-05).
"""

from typing import Literal

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_game_settings import BotGameSettings
from app.repositories import game_repository, user_rating_anchors_repository
from app.schemas.bots import StoreBotGameRequest, StoreBotGameResponse
from app.services.import_service import _flush_batch
from app.services.normalization import normalize_flawchess_game, parse_time_control

# Platform constant — the one value this service ever writes/looks up (D-04/D-17).
_FLAWCHESS_PLATFORM = "flawchess"

RatingSource = Literal["lichess", "chesscom", "blended"]


def _derive_rating_source(
    n_lichess_games: int,
    n_chesscom_games: int,
) -> RatingSource:
    """Derive rating_source from anchor provenance (D-07).

    Only called when an anchor row exists, so at least one of the two counts
    is guaranteed to be > 0 (fetch_anchors_for_user never persists a row with
    both zero).
    """
    if n_lichess_games > 0 and n_chesscom_games > 0:
        return "blended"
    if n_lichess_games > 0:
        return "lichess"
    return "chesscom"


async def store_bot_game(
    session: AsyncSession,
    user_id: int,
    request: StoreBotGameRequest,
) -> StoreBotGameResponse | None:
    """Persist one finished bot game as a platform='flawchess' Library game.

    Returns None when the PGN is invalid (unparseable, missing [%clk] on either
    color, or no recognized Result header) — this is an EXPECTED validation
    failure (STORE-02/D-15); the caller (bots router) maps None to a 422. No
    Sentry capture and no DB write happen on this path.

    Idempotent on request.game_uuid (D-11): re-invoking with the same
    game_uuid returns the existing game_id with created=False, and does NOT
    insert a second games row or a second bot_game_settings row.

    Args:
        session: AsyncSession. This function commits once (D-10) — the caller
            (router) must not also commit.
        user_id: Internal user PK, sourced from current_active_user (D-13),
            never from the request body (ASVS V4).
        request: The validated StoreBotGameRequest.

    Returns:
        StoreBotGameResponse with the (new or existing) game_id and a
        created flag, or None on invalid PGN input.
    """
    # D-05/D-06: player rating is server-computed from the user's rating
    # anchor for the game's TC bucket; NULL when no anchor (guest or no
    # imported games in that bucket). D-07: rating_source derived from the
    # anchor's platform provenance.
    tc_bucket, _ = parse_time_control(request.tc_preset)
    anchors = await user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=user_id)
    anchor_row = anchors.get(tc_bucket) if tc_bucket is not None else None

    player_rating: int | None
    rating_source: RatingSource | None
    if anchor_row is None:
        player_rating = None
        rating_source = None
    else:
        player_rating = anchor_row.anchor_rating
        rating_source = _derive_rating_source(
            anchor_row.n_lichess_games, anchor_row.n_chesscom_games
        )

    normalized = normalize_flawchess_game(
        request.pgn,
        request.game_uuid,
        user_id,
        request.user_color,
        request.bot_elo,
        player_rating,
        request.tc_preset,
    )
    if normalized is None:
        return None  # STORE-02/D-15 — expected, no Sentry capture, no commit

    try:
        inserted_count = await _flush_batch(session, [normalized], user_id)
        created = inserted_count == 1

        game_id = await game_repository.get_game_id_by_platform_game_id(
            session, user_id, _FLAWCHESS_PLATFORM, request.game_uuid
        )
        if game_id is None:
            # Should be unreachable: _flush_batch just inserted this row (or it
            # already existed as a duplicate) under the same platform_game_id.
            raise RuntimeError("flawchess game row not found after _flush_batch")

        if created:
            # D-11: guard so a duplicate re-submit (created=False) never
            # double-inserts the one-to-one settings row.
            session.add(
                BotGameSettings(
                    game_id=game_id,
                    nominal_elo=request.bot_elo,
                    play_style_blend=request.play_style_blend,
                    tc_preset=request.tc_preset,
                    rating_source=rating_source,
                )
            )
    except Exception:
        sentry_sdk.set_context(
            "store_bot_game", {"user_id": user_id, "game_uuid": request.game_uuid}
        )
        sentry_sdk.capture_exception()
        raise

    # D-10: this service owns the single transaction — _flush_batch never
    # commits (WR-05); commit the game + positions + settings row together.
    await session.commit()

    return StoreBotGameResponse(game_id=game_id, created=created)
