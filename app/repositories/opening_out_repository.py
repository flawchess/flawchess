"""Repository for the on-read "out of the opening" worse/better counts.

Executes the shared canonical-slice builder (``per_user_cte_opening_out_counts``) for
one user and one time control. The SQL composes the same ``selected_users`` +
``recent_capped`` prelude and the same classification body the CDF script and the
Stage B percentile compute use, so the persisted rate, the CDF peers and the on-read
"k of n" counts cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.normalization import Color
from app.services.canonical_slice_sql import (
    TimeControlBucket,
    per_user_cte_opening_out_counts,
    selected_users_cte,
)
from app.services.global_percentile_cdf import OpeningOutMetricId


@dataclass(frozen=True)
class OpeningOutCounts:
    """Qualifying and worse/better game counts for one (colour, time control).

    ``n_games`` counts qualifying games only: games that reached the middlegame with
    an eval, or ended before it by resignation, checkmate or timeout with a decisive
    result. No floor is applied here.
    """

    n_games: int
    worse_n: int
    better_n: int

    def count_for(self, metric: OpeningOutMetricId) -> int:
        """The numerator of ``metric``: worse games for the worse rate, better for the better."""
        return self.worse_n if metric == "opening_worse_rate" else self.better_n


async def fetch_opening_out_counts(
    session: AsyncSession,
    *,
    user_id: int,
    tc: TimeControlBucket,
) -> dict[Color, OpeningOutCounts]:
    """Return the user's per-colour worse/better counts for one time control.

    A colour with no slice game is absent from the result. V4 Information Disclosure
    mitigation: the caller MUST pass the authenticated user's ID (from the
    FastAPI-Users dependency ``current_active_user.id``) or the Stage B user id; never
    accept ``user_id`` as a query parameter from the client. ``user_id`` is bound via
    ``.bindparams()`` only, never f-stringed into the SQL (V5).
    """
    sql = (
        f"WITH {selected_users_cte(source='single_user')},\n"
        f"{per_user_cte_opening_out_counts(tc, source='single_user')}\n"
        "SELECT user_color, n_games, worse_n, better_n\n"
        "FROM per_user_color_counts"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
    counts: dict[Color, OpeningOutCounts] = {}
    for row in result:
        color: Color = "white" if row.user_color == "white" else "black"
        counts[color] = OpeningOutCounts(
            n_games=int(row.n_games), worse_n=int(row.worse_n), better_n=int(row.better_n)
        )
    return counts
