"""In-process claim lease for the tier-4 flaw-blob lottery (SEED-261119-c7l).

`_claim_tier4_blob` is a plain-SELECT lottery with no lock. Before this lease, a game
handed to one worker stayed drawable by every other worker until the first submit
stamped it, and the second submit ended in `nothing_pending` with its engine work
discarded. The Phase 252 feeder keeps only 150 to 500 games pending and the lottery
weights concentrate on recently active users (an effective pool of about 15 games on
2026-11-19), so an estimated 20 to 30% of re-walks were done twice.

Why in-process and not a `games.blob_leased_until` column: prod serves the eval
endpoints and the server-pool drain from ONE uvicorn process (deploy/entrypoint.sh, no
--workers, a single backend container; verified with `docker compose top backend` on
2026-11-19). A module-level map is therefore authoritative. It is lost on restart, which
only means a handful of games can be drawn twice right after a deploy. If the backend is
ever scaled to several processes or replicas, this lease stops being exclusive and must
move to the database.

Exclusivity under asyncio: the lottery awaits the DB, so two coroutines can draw the same
game. `try_lease` checks and sets with no await in between (atomic on the event loop);
the loser re-draws with the winner's game excluded (see `_lease_tier4_blob`).
"""

import logging
import time

logger = logging.getLogger(__name__)

# Lease TTL. Matches the remote worker's watchdog (`STALL_THRESHOLD_S` = 720 s in
# scripts/remote_eval_worker.py): the worst legitimate cycle is about 620 s at
# --workers 1 (500 s first pass plus the 120 s retry pass), and the watchdog abandons a
# cycle at 720 s. A lease that outlives the last moment a live worker could still submit
# only delays recovery from a crashed worker, it never blocks a working one.
BLOB_LEASE_TTL_S: float = 720.0

# game_id -> (monotonic expiry, owner worker label).
_leases: dict[int, tuple[float, str]] = {}

# Submits that ended in `nothing_pending` since process start (discarded engine work).
_discarded_submit_count: int = 0


def active_leased_game_ids(now: float | None = None) -> list[int]:
    """Game ids with an unexpired lease, pruning expired entries as a side effect."""
    current = time.monotonic() if now is None else now
    expired = [game_id for game_id, (expiry, _owner) in _leases.items() if expiry <= current]
    for game_id in expired:
        del _leases[game_id]
    return sorted(_leases)


def try_lease(game_id: int, owner: str, now: float | None = None) -> bool:
    """Lease `game_id` to `owner` unless another unexpired lease holds it.

    No await inside, so check-and-set is atomic with respect to other coroutines.
    """
    current = time.monotonic() if now is None else now
    held = _leases.get(game_id)
    if held is not None and held[0] > current:
        return False
    _leases[game_id] = (current + BLOB_LEASE_TTL_S, owner)
    return True


def release_lease(game_id: int, owner: str, now: float | None = None) -> bool:
    """Drop `owner`'s lease on `game_id`. Returns True when `owner` held an unexpired lease.

    A lease held by someone else is left alone: a late submit from a worker whose lease
    expired must not free the game for a third worker while the current holder works.
    """
    current = time.monotonic() if now is None else now
    held = _leases.get(game_id)
    if held is None or held[1] != owner:
        return False
    del _leases[game_id]
    return held[0] > current


def holds_lease(game_id: int, owner: str, now: float | None = None) -> bool:
    """True when `owner` holds an unexpired lease on `game_id`."""
    current = time.monotonic() if now is None else now
    held = _leases.get(game_id)
    return held is not None and held[1] == owner and held[0] > current


def record_discarded_submit(game_id: int, source: str, owner: str, lease_held: bool) -> None:
    """Count and log a flaw-blob submit that found nothing pending.

    WARNING, not INFO: prod drops app-level INFO from the container log. After the lease
    this should be rare (a lease lost on restart, an expired lease, or a concurrent blob
    writer), so the line doubles as a collision alarm. `lease_held=False` means the
    submitter no longer held the lease when it submitted.
    """
    global _discarded_submit_count
    _discarded_submit_count += 1
    logger.warning(
        "flaw-blob: discarded submit, nothing pending (game_id=%s source=%s worker=%s "
        "lease_held=%s discarded_since_start=%s)",
        game_id,
        source,
        owner,
        lease_held,
        _discarded_submit_count,
    )


def discarded_submit_count() -> int:
    """Discarded submits since process start."""
    return _discarded_submit_count


def reset_for_tests() -> None:
    """Clear all leases and the counter (test isolation only)."""
    global _discarded_submit_count
    _leases.clear()
    _discarded_submit_count = 0
