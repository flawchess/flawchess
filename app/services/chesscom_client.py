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
import sentry_sdk

from app.core.rate_limiters import get_chesscom_semaphore
from app.schemas.normalization import NormalizedGame
from app.services.normalization import normalize_chesscom_game

logger = logging.getLogger(__name__)

USER_AGENT = "FlawChess/1.0 (github.com/flawchess/flawchess)"
BASE_URL = "https://api.chess.com/pub/player"

_HEADERS = {"User-Agent": USER_AGENT}
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE_SECONDS = 5
_RATE_LIMIT_BACKOFF_SECONDS = 60

# Transient network errors worth retrying (same set as lichess client)
_RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError)

# Substring (case-insensitive) we expect in the chess.com 404 body when the user truly
# does not exist. Anything else on a 404 is treated as ambiguous and probed via the
# player endpoint. Avoids a magic string per CLAUDE.md "no magic numbers/strings".
_CHESSCOM_NOT_FOUND_MARKER = "not found"

# Status codes that represent transient server-side failures and should be retried
# with exponential backoff. We treat these like network errors — chess.com / Cloudflare
# occasionally returns 5xx for a single archive while the rest of the API is healthy.
_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})

# Status codes that mean "this archive is gone / not available" but the rest of the
# user's archives may still be fetchable. Skip the archive with a warning rather
# than failing the entire import.
_SKIPPABLE_ARCHIVE_STATUS_CODES = frozenset({404, 410})


async def _user_exists_on_chesscom(client: httpx.AsyncClient, api_username: str) -> bool | None:
    """Probe /pub/player/{username} to disambiguate a 404 on /games/archives.

    Returns:
        True  — player endpoint returned 200, user exists.
        False — player endpoint returned 404, user truly absent.
        None  — player endpoint returned anything else (5xx / network);
                caller should treat as 'request failed' so the import is
                marked failed and last_synced_at is preserved (f69842b).
    """
    url = f"{BASE_URL}/{api_username}"
    try:
        resp = await client.get(url, headers=_HEADERS)
    except _RETRYABLE_EXCEPTIONS:
        # Network-level error on the probe — surface as 'unknown'.
        return None
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    return None


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
        ValueError: Three distinct cases on archives-list failure:
            - "user not found" — 404 with body identifying the user as absent, or
              404 with ambiguous body and player endpoint confirms user is absent.
            - "couldn't return games right now" — 404 with ambiguous body and player
              endpoint confirms user exists (no public archives or transient error).
            - "request failed" — non-200 archives response, or ambiguous 404 where
              the player probe also failed; last_synced_at is preserved in both cases.
        RuntimeError: If a per-archive fetch fails persistently (5xx after retries, or
            429 after retries, or unexpected non-200). Raising halts the import so the
            job is marked ``failed`` and ``last_synced_at`` is preserved — preventing
            silent data loss when chess.com / Cloudflare hiccups for a single archive.
            See ``.planning/debug/prod-import-missed-games.md``.
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
                    "chess.com archives list for %s failed (attempt %d/%d), retrying in %ds: %s",
                    username,
                    attempt + 1,
                    _MAX_RETRIES,
                    backoff,
                    exc,
                )
                await asyncio.sleep(backoff)
            else:
                # Sentry capture omitted — last-attempt error re-raises to run_import()
                # top-level handler which calls capture_exception (per D-02).
                raise

    if archives_resp.status_code == 404:
        # chess.com returns 404 on /games/archives in TWO distinct cases:
        #   1. User truly absent — body: {"message": "User \"X\" not found."}
        #   2. Real user, archives unavailable (no public archives, or transient
        #      chess.com error) — body: {"message": "An internal error has occurred..."}
        # Pre-2026-04-25 this branch conflated both as "user not found", which sent
        # users with valid accounts on a fruitless typo hunt. We now parse the body
        # and, on ambiguity, probe /pub/player/{username} to disambiguate.
        # See .planning/quick/260425-lii-fix-misleading-chess-com-user-not-found-.
        try:
            body = archives_resp.json()
            message = str(body.get("message", "")) if isinstance(body, dict) else ""
        except ValueError:
            message = ""

        if _CHESSCOM_NOT_FOUND_MARKER in message.lower():
            raise ValueError(f"chess.com user '{username}' not found")

        # Ambiguous body — confirm existence via the player endpoint.
        exists = await _user_exists_on_chesscom(client, api_username)
        if exists is True:
            raise ValueError(
                f"chess.com couldn't return games for '{username}' right now "
                "(no public archives or temporary chess.com error). "
                "Try again in a few minutes."
            )
        if exists is False:
            raise ValueError(f"chess.com user '{username}' not found")
        # exists is None — player endpoint also failed; treat as transient.
        raise ValueError(
            f"chess.com request failed (status 404, player endpoint unreachable) "
            f"for user '{username}'"
        )
    if archives_resp.status_code != 200:
        raise ValueError(
            f"chess.com request failed (status {archives_resp.status_code}) for user '{username}'"
        )

    archive_urls: list[str] = archives_resp.json().get("archives", [])

    for archive_url in archive_urls:
        # Incremental sync: skip months that are entirely before since_timestamp
        if since_timestamp is not None and _archive_before_timestamp(archive_url, since_timestamp):
            continue

        # Shared rate limiter: limits concurrent archive fetches across all users
        async with get_chesscom_semaphore():
            resp = await _fetch_archive_with_retries(client, archive_url)

        # _fetch_archive_with_retries returns None only for skippable client errors
        # (404/410). Transient/persistent failures raise RuntimeError instead — this
        # is the fix for the silent-data-loss bug where a transient 5xx on one
        # archive completed the import with 0 games and advanced last_synced_at.
        if resp is None:
            continue

        games = resp.json().get("games", [])
        for game in games:
            normalized = normalize_chesscom_game(game, username, user_id)
            if normalized is not None:
                yield normalized
                if on_game_fetched is not None:
                    on_game_fetched()


async def _fetch_archive_with_retries(
    client: httpx.AsyncClient, archive_url: str
) -> httpx.Response | None:
    """Fetch a single monthly archive with retry policy.

    Returns:
        The 200 response on success, or ``None`` if the archive returned a permanent
        client error (404/410) that should be skipped without failing the import.

    Raises:
        RuntimeError: If retries are exhausted on a transient error (5xx or 429), or
            an unexpected non-200 status is returned. Raising halts the import so the
            job is marked failed and last_synced_at is preserved.
        Exception: Re-raises the last network exception if all retry attempts threw
            connection-level errors.
    """
    last_status: int | None = None
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        # Rate-limit delay between requests (also acts as inter-attempt pacing).
        await asyncio.sleep(0.15)

        try:
            resp = await client.get(archive_url, headers=_HEADERS)
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                backoff = _RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "chess.com archive %s failed (attempt %d/%d), retrying in %ds: %s",
                    archive_url,
                    attempt + 1,
                    _MAX_RETRIES,
                    backoff,
                    exc,
                )
                await asyncio.sleep(backoff)
                continue
            # Last attempt: re-raise so run_import() captures and fails the job.
            raise

        if resp.status_code == 200:
            return resp

        last_status = resp.status_code

        # Permanent client errors — skip this archive but keep going. Visible in logs
        # and Sentry (warning) so we can still notice if it becomes systemic.
        if resp.status_code in _SKIPPABLE_ARCHIVE_STATUS_CODES:
            logger.warning(
                "chess.com archive %s returned %d, skipping",
                archive_url,
                resp.status_code,
            )
            sentry_sdk.capture_message(
                "chess.com archive skipped",
                level="warning",
                tags={"source": "import", "platform": "chess.com"},
            )
            return None

        # Rate-limited: back off and retry.
        if resp.status_code == 429:
            logger.warning(
                "chess.com 429 rate-limited on %s (attempt %d/%d), backing off %ds",
                archive_url,
                attempt + 1,
                _MAX_RETRIES,
                _RATE_LIMIT_BACKOFF_SECONDS,
            )
            sentry_sdk.capture_message(
                "chess.com 429 rate limit hit",
                level="warning",
                tags={"source": "import", "platform": "chess.com"},
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RATE_LIMIT_BACKOFF_SECONDS)
                continue
            # Final attempt still 429 — fail loudly rather than silently dropping
            # the archive (would otherwise advance last_synced_at and lose games).
            raise RuntimeError(
                f"chess.com archive {archive_url} rate-limited after {_MAX_RETRIES} attempts"
            )

        # Transient server errors — retry with exponential backoff.
        if resp.status_code in _RETRYABLE_STATUS_CODES:
            if attempt < _MAX_RETRIES - 1:
                backoff = _RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "chess.com archive %s returned %d (attempt %d/%d), retrying in %ds",
                    archive_url,
                    resp.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                    backoff,
                )
                await asyncio.sleep(backoff)
                continue
            raise RuntimeError(
                f"chess.com archive {archive_url} returned "
                f"status {resp.status_code} after {_MAX_RETRIES} attempts"
            )

        # Any other unexpected non-200 (e.g. 401, 403). Don't silently skip — fail
        # loudly so a regression in chess.com's API surface is investigated rather
        # than masked as "0 games imported".
        raise RuntimeError(
            f"chess.com archive {archive_url} returned unexpected status {resp.status_code}"
        )

    # Loop exhausted without returning — shouldn't happen because each branch above
    # either returns, continues, or raises. Treat as failure for safety.
    raise RuntimeError(
        f"chess.com archive {archive_url} fetch exhausted retries "
        f"(last_status={last_status}, last_exc={last_exc!r})"
    )
