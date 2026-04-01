"""lichess API client.

Fetches games for a user via NDJSON streaming and yields normalized game dicts.
Supports incremental sync via the ``since`` millisecond timestamp parameter.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable

import httpx

from app.core.rate_limiters import get_lichess_semaphore
from app.schemas.normalization import NormalizedGame
from app.services.normalization import normalize_lichess_game

logger = logging.getLogger(__name__)

LICHESS_API_URL = "https://lichess.org/api/games/user"

# Request standard time-control variants only (excludes correspondence/unlimited)
_PERF_TYPES = "ultraBullet,bullet,blitz,rapid,classical"

# Retry config for transient stream errors (e.g. "peer closed connection").
# Lichess NDJSON streams for large exports (10k+ games) can drop mid-transfer.
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE_SECONDS = 5


async def fetch_lichess_games(
    client: httpx.AsyncClient,
    username: str,
    user_id: int,
    since_ms: int | None = None,
    on_game_fetched: Callable[[], None] | None = None,
) -> AsyncIterator[NormalizedGame]:
    """Async generator that yields normalized NormalizedGame objects for a lichess user.

    Streams NDJSON from the lichess API line-by-line using httpx streaming,
    so large exports never need to be buffered in memory. Retries on transient
    connection drops — already-imported games are deduplicated downstream by
    bulk_insert_games.

    Args:
        client: Shared httpx.AsyncClient instance.
        username: The lichess username to fetch games for.
        user_id: Internal database user ID (denormalized into each game dict).
        since_ms: If provided, only games created at or after this Unix millisecond
            timestamp are returned (lichess ``since`` parameter).
        on_game_fetched: Optional callback called once per yielded game.

    Raises:
        ValueError: If ``username`` is not found on lichess (HTTP 404).
    """
    params: dict[str, str | bool] = {
        "pgnInJson": True,
        "perfType": _PERF_TYPES,
        "moves": True,
        "tags": True,
        "opening": True,
        "evals": True,  # include %eval annotations when prior computer analysis exists
        "accuracy": True,  # include per-player accuracy % for analyzed games
    }

    if since_ms is not None:
        params["since"] = str(since_ms)

    url = f"{LICHESS_API_URL}/{username}"
    headers = {"Accept": "application/x-ndjson"}

    # Initialize with a sentinel so raise always has a valid exception even if no
    # attempt captured a specific error (e.g., _MAX_RETRIES == 0).
    last_attempt_error: Exception = Exception("Exhausted retries without capturing an error")

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            backoff = _RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Lichess stream for %s dropped (attempt %d/%d), retrying in %ds: %s",
                username,
                attempt,
                _MAX_RETRIES,
                backoff,
                last_attempt_error,
            )
            await asyncio.sleep(backoff)

        try:
            # Semaphore held for entire stream duration. Lichess streams in one HTTP
            # connection per job, so the semaphore limits concurrent connections, not
            # individual requests.
            async with get_lichess_semaphore():
                async with client.stream(
                    "GET", url, params=params, headers=headers, timeout=300.0
                ) as response:
                    if response.status_code == 404:
                        raise ValueError(f"lichess user '{username}' not found")

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            game = json.loads(line)
                        except json.JSONDecodeError:
                            # Skip malformed lines without aborting the stream
                            continue

                        normalized = normalize_lichess_game(game, username, user_id)
                        if normalized is not None:
                            yield normalized
                            if on_game_fetched is not None:
                                on_game_fetched()

            # Stream completed successfully — no retry needed
            return

        except (httpx.RemoteProtocolError, httpx.ReadError) as exc:
            # Transient stream errors (e.g. "peer closed connection without
            # sending complete message body"). Safe to retry because
            # bulk_insert_games deduplicates already-imported games.
            last_attempt_error = exc
            continue

    # All retries exhausted — re-raise the last error
    raise last_attempt_error
