"""lichess API client.

Fetches games for a user via NDJSON streaming and yields normalized game dicts.
Supports incremental sync via the ``since`` millisecond timestamp parameter.
"""

import json
from collections.abc import AsyncIterator, Callable

import httpx

from app.services.normalization import normalize_lichess_game

LICHESS_API_URL = "https://lichess.org/api/games/user"

# Request standard time-control variants only (excludes correspondence/unlimited)
_PERF_TYPES = "ultraBullet,bullet,blitz,rapid,classical"


async def fetch_lichess_games(
    client: httpx.AsyncClient,
    username: str,
    user_id: int,
    since_ms: int | None = None,
    on_game_fetched: Callable[[], None] | None = None,
) -> AsyncIterator[dict]:
    """Async generator that yields normalized game dicts for a lichess user.

    Streams NDJSON from the lichess API line-by-line using httpx streaming,
    so large exports never need to be buffered in memory.

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
    }

    if since_ms is not None:
        params["since"] = str(since_ms)

    url = f"{LICHESS_API_URL}/{username}"
    headers = {"Accept": "application/x-ndjson"}

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
