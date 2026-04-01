"""chess.com API client.

Fetches game archives for a user and yields normalized game dicts.
Rate limits are respected by sleeping 150ms between archive fetches,
with a 60-second backoff on 429 responses.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone

import httpx

from app.core.rate_limiters import get_chesscom_semaphore
from app.schemas.normalization import NormalizedGame
from app.services.normalization import normalize_chesscom_game

logger = logging.getLogger(__name__)

USER_AGENT = "FlawChess/1.0 (github.com/flawchess/flawchess)"
BASE_URL = "https://api.chess.com/pub/player"

_HEADERS = {"User-Agent": USER_AGENT}
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE_SECONDS = 5

# Transient network errors worth retrying (same set as lichess client)
_RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError)


def _archive_before_timestamp(archive_url: str, since: datetime) -> bool:
    """Return True if the archive month ends before ``since``.

    Chess.com archive URLs end in ``/YYYY/MM``, e.g.:
        https://api.chess.com/pub/player/testuser/games/2024/03

    A month "ends" at the start of the *following* month. So the 2024/03
    archive ends at 2024-04-01T00:00:00Z. If ``since`` is on or after that
    point, the archive contains no games we care about.
    """
    parts = archive_url.rstrip("/").split("/")
    # Expect last two path segments to be year and month
    year = int(parts[-2])
    month = int(parts[-1])

    # The archive covers games up to (but not including) the first day of the
    # next month. Compute that boundary naively.
    if month == 12:
        end_year, end_month = year + 1, 1
    else:
        end_year, end_month = year, month + 1

    # Make since timezone-aware if it isn't already
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)

    archive_end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)
    return archive_end <= since


async def fetch_chesscom_games(
    client: httpx.AsyncClient,
    username: str,
    user_id: int,
    since_timestamp: datetime | None = None,
    on_game_fetched: Callable[[], None] | None = None,
) -> AsyncIterator[NormalizedGame]:
    """Async generator that yields normalized NormalizedGame objects for a chess.com user.

    Args:
        client: Shared httpx.AsyncClient instance.
        username: The chess.com username to fetch games for.
        user_id: Internal database user ID (denormalized into each game dict).
        since_timestamp: If provided, skip archive months that ended before this time.
        on_game_fetched: Optional callback called once per yielded game (for progress tracking).

    Raises:
        ValueError: If ``username`` is not found on chess.com (HTTP 404).
    """
    # chess.com API requires lowercase usernames (returns 301 for mixed case)
    api_username = username.lower()
    archives_url = f"{BASE_URL}/{api_username}/games/archives"
    for attempt in range(_MAX_RETRIES):
        try:
            archives_resp = await client.get(archives_url, headers=_HEADERS)
            break
        except _RETRYABLE_EXCEPTIONS as exc:
            if attempt < _MAX_RETRIES - 1:
                backoff = _RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "chess.com archives list for %s failed (attempt %d/%d), "
                    "retrying in %ds: %s",
                    username, attempt + 1, _MAX_RETRIES, backoff, exc,
                )
                await asyncio.sleep(backoff)
            else:
                # Sentry capture omitted — last-attempt error re-raises to run_import()
                # top-level handler which calls capture_exception (per D-02).
                raise

    if archives_resp.status_code == 404:
        raise ValueError(f"chess.com user '{username}' not found")
    if archives_resp.status_code != 200:
        raise ValueError(
            f"chess.com request failed (status {archives_resp.status_code})"
            f" for user '{username}'"
        )

    archive_urls: list[str] = archives_resp.json().get("archives", [])

    for archive_url in archive_urls:
        # Incremental sync: skip months that are entirely before since_timestamp
        if since_timestamp is not None and _archive_before_timestamp(
            archive_url, since_timestamp
        ):
            continue

        # Shared rate limiter: limits concurrent archive fetches across all users
        async with get_chesscom_semaphore():
            # Rate-limit delay between requests
            await asyncio.sleep(0.15)

            resp = None
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = await client.get(archive_url, headers=_HEADERS)
                except _RETRYABLE_EXCEPTIONS as exc:
                    if attempt < _MAX_RETRIES - 1:
                        backoff = _RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
                        logger.warning(
                            "chess.com archive %s failed (attempt %d/%d), "
                            "retrying in %ds: %s",
                            archive_url, attempt + 1, _MAX_RETRIES, backoff, exc,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    # Sentry capture omitted — last-attempt error re-raises to run_import()
                    # top-level handler which calls capture_exception (per D-02).
                    raise

                if resp.status_code == 429:
                    logger.warning(
                        "chess.com 429 rate-limited on %s, backing off 60s",
                        archive_url,
                    )
                    await asyncio.sleep(60)
                    continue

                break

            # Skip non-200 archive responses rather than crashing on .json()
            if resp is None or resp.status_code != 200:
                continue

            games = resp.json().get("games", [])
            for game in games:
                normalized = normalize_chesscom_game(game, username, user_id)
                if normalized is not None:
                    yield normalized
                    if on_game_fetched is not None:
                        on_game_fetched()
