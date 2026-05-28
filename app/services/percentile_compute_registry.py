"""In-memory registry of users whose Stage-B percentile compute is in progress.

This gates the Tier-2 endgame readiness signal while ``compute_stage_b`` writes
the eval-dependent percentile rows. It closes the race where the readiness
endpoint observes ``pending evals == 0`` (and a prior Stage-A ``score_gap`` row,
so ``has_any_rows`` is already True) BEFORE ``compute_stage_b`` has finished
rewriting the 7 eval-dependent metric families. Without this gate the endgame
page unlocks with missing badges on first import, or stale prior-import badges
on re-import.

A user_id is added to the set synchronously at the Stage-B trigger sites
(``eval_drain``, ``import_service``), immediately before
``asyncio.create_task(compute_stage_b(uid))``, and removed in a ``finally``
inside ``compute_stage_b`` that covers every exit path.

Concurrency: module-level state in a single-process asyncio backend. CPython's
GIL makes ``set.add`` / ``set.discard`` / membership tests atomic, so no lock is
needed. This module never performs I/O and cannot fail, so it has no Sentry
capture.

Restart semantics: in-memory state is lost on backend restart, mirroring the
import active-job registry caveat in ``import_service``. A restart mid-Stage-B
clears the mark and the next readiness poll unlocks the page. This is acceptable
because ``compute_stage_b`` is upsert-idempotent and rewrites the rows shortly
after; at worst the user briefly sees the prior-import badges, which the next
compute pass corrects.
"""

from __future__ import annotations

# Set of user_ids whose Stage-B compute is currently in progress.
_computing: set[int] = set()


def mark(user_id: int) -> None:
    """Mark a user as mid-Stage-B compute. Idempotent (set add)."""
    _computing.add(user_id)


def clear(user_id: int) -> None:
    """Clear a user's Stage-B-in-progress mark. Idempotent no-op if unmarked."""
    _computing.discard(user_id)


def is_computing(user_id: int) -> bool:
    """Return True while the user's Stage-B compute is in progress."""
    return user_id in _computing
