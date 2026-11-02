"""phase 244 SR ladder due-date push

Revision ID: e2a7c4f9b244
Revises: b7e4c2a9f013
Create Date: 2026-11-02 12:00:00.000000+00:00

Phase 244 (SEED-207 as amended by 244-CONTEXT), data only, no schema change.

The Train ladder now retries a correct solve after exactly 10 days and a wrong solve
after exactly 4 days, and masters after 2 consecutive correct solves. This revision
moves in-flight ACTIVE items onto the new spacing in the same release, so no item can
master on a repeat that was timed for the old (recall-friendly) 3-day step (D-05). It
sets ``drill_items.due_date`` to the item's floor, on three paths (D-07):

* ACTIVE, ``streak >= 1``: floor = UTC date of the latest SR correct solve + 10.
* ACTIVE, ``streak = 0`` with a failed SR solve: floor = UTC date of the latest SR fail
  + 4.
* ACTIVE, never attempted (no SR solve): untouched, stays due immediately.

A row moves only when its floor is later than its current ``due_date`` (never pulled
earlier) AND the floor is still in the future (D-09). An overdue item whose floor is
already past keeps its exact current ``due_date``, so composition (which orders SR
items by ``due_date`` ascending) keeps its original priority. MASTERED and PARKED rows
are never touched; there is no retroactive Door B parking.

Notes:

* D-06: no streak remap. With threshold 2, old streak 1 and old streak 2 both master on
  the next correct solve and both reset to 0 on a fail, so a remap would change
  nothing. Only ``due_date`` is written; streak, status, fail_count and ever_correct
  are unchanged.
* D-08: no weekday snapping and no read of ``train_settings`` (item due dates are
  schedule-independent).
* Dates are computed in UTC (solve day = ``solved_at AT TIME ZONE 'UTC'``, today =
  ``now() AT TIME ZONE 'UTC'``). That is off by at most one day for a non-UTC user, and
  unlike ``AT TIME ZONE`` on the stored ``train_settings.timezone`` it can never raise
  on an invalid IANA name and abort the deploy.
* D-10: items already composed into an open session are not special-cased. Unsolved
  ``drill_solves`` rows are ignored; ``drill_sessions`` / ``drill_solves`` are never
  written.
* Expected prod effect: about 436 rows on 2026-11-02 (drifts by deploy day). The
  upgrade logs the affected rowcount as the deploy-day sanity check.

One-way data change (D-05): pushed due dates cannot be restored by a downgrade. The
owner accepted this (items only resurface later), so the downgrade is a no-op.

The constants below are frozen literals: a migration is a point-in-time artifact and
must not import live application code.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2a7c4f9b244"
down_revision: Union[str, Sequence[str], None] = "b7e4c2a9f013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_logger = logging.getLogger("alembic.runtime.migration")

# Snapshot of app.services.train_scheduler.CORRECT_RETRY_DAYS / FAIL_RETRY_DAYS.
_CORRECT_RETRY_DAYS = 10
_FAIL_RETRY_DAYS = 4
# Snapshot of DrillSource.SR_ITEM and DrillStatus.ACTIVE.
_SR_SOURCE = 0
_ACTIVE_STATUS = 0

# Public so tests/test_migration_244_sr_ladder_due_dates.py runs this exact SQL.
# A NULL floor (no matching solve) fails both comparisons in the UPDATE, so
# never-attempted items are untouched structurally.
PUSH_DUE_DATES_SQL = f"""
WITH last_sr_solve AS (
    SELECT
        user_id,
        game_id,
        ply,
        max(solved_at) FILTER (WHERE correct_move) AS last_correct_at,
        max(solved_at) FILTER (WHERE correct_move = false) AS last_fail_at
    FROM drill_solves
    WHERE source = {_SR_SOURCE}
      AND game_id IS NOT NULL
      AND solved_at IS NOT NULL
    GROUP BY user_id, game_id, ply
),
floors AS (
    SELECT
        di.user_id,
        di.game_id,
        di.ply,
        CASE
            WHEN di.streak >= 1
                THEN (ls.last_correct_at AT TIME ZONE 'UTC')::date + {_CORRECT_RETRY_DAYS}
            ELSE (ls.last_fail_at AT TIME ZONE 'UTC')::date + {_FAIL_RETRY_DAYS}
        END AS floor_date
    FROM drill_items di
    JOIN last_sr_solve ls
      ON ls.user_id = di.user_id AND ls.game_id = di.game_id AND ls.ply = di.ply
    WHERE di.status = {_ACTIVE_STATUS}
)
UPDATE drill_items di
SET due_date = f.floor_date
FROM floors f
WHERE di.user_id = f.user_id
  AND di.game_id = f.game_id
  AND di.ply = f.ply
  AND di.status = {_ACTIVE_STATUS}
  AND f.floor_date > (now() AT TIME ZONE 'UTC')::date
  AND di.due_date < f.floor_date
"""


def upgrade() -> None:
    """Push in-flight ACTIVE items' due dates onto the Phase 244 spacing."""
    result = op.get_bind().execute(sa.text(PUSH_DUE_DATES_SQL))
    _logger.info("Phase 244: pushed due_date on %s active drill_items", result.rowcount)


def downgrade() -> None:
    """No-op: the due-date push is irreversible by design (D-05).

    The previous due dates are not recorded anywhere, so there is nothing to
    restore. The owner accepted this: pushed items only resurface later.
    """
    pass
