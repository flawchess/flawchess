"""Admin service layer: user search for the impersonation selector.

Phase 62. Superuser-only by callers (guarded at the router layer via
`current_superuser` — see app/users.py).
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import false as sa_false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

# D-13: cap results at 20 so the combobox stays lightweight.
USER_SEARCH_LIMIT = 20

# D-12: minimum query length. Below this, return empty. Keeps the endpoint
# from being used as an enumeration oracle for tiny prefixes.
USER_SEARCH_MIN_QUERY_LEN = 2


async def search_users(session: AsyncSession, query: str) -> Sequence[User]:
    """Return up to 20 non-superuser users matching ILIKE on email / usernames
    or exact numeric id match.

    Superusers are EXCLUDED from results — D-05 forbids impersonating another
    superuser, so surfacing them in the selector is pointless and leaks a tiny
    bit of roster info if the admin session is compromised.

    Ordering: most-recently-logged-in first, then ascending id (stable tiebreak).
    """
    if len(query) < USER_SEARCH_MIN_QUERY_LEN:
        return []

    like = f"%{query}%"

    # Build the or_ clauses conditionally so we don't mix SQLAlchemy
    # ColumnElement with a Python False literal — sa.false() keeps the
    # expression pure SQLAlchemy and avoids RESEARCH.md Open Question #4.
    # ty infers the Mapped columns as their Python types (`str`/`str | None`),
    # missing the SQLAlchemy operator overloads — suppress unresolved-attribute
    # on the .ilike() calls. See CLAUDE.md §"ty compliance".
    match_clauses: list[Any] = [
        User.email.ilike(like),  # ty: ignore[unresolved-attribute]  # SQLAlchemy column exposes .ilike; ty sees Mapped[str]
        User.chess_com_username.ilike(like),
        User.lichess_username.ilike(like),
    ]
    if query.isdigit():
        match_clauses.append(User.id == int(query))

    stmt = (
        select(User)
        .where(
            or_(*match_clauses),
            # hygiene: exclude superusers (D-05 forbids impersonating them).
            # ty collapses `Mapped[bool] == sa.false()` to Python bool; suppress.
            User.is_superuser == sa_false(),  # ty: ignore[invalid-argument-type]  # SQLAlchemy ColumnElement, not Python bool
        )
        .order_by(User.last_login.desc().nullslast(), User.id.asc())
        .limit(USER_SEARCH_LIMIT)
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())
