"""Phase 80.1 prod-DB sanity check (D-09). Read-only.

Usage:
    PROD_TUNNEL_DATABASE_URL=postgresql+asyncpg://flawchess_ro:<PASSWORD>@localhost:15432/flawchess \\
        uv run python scripts/prodcheck_80_1.py 4 18

Requires bin/prod_db_tunnel.sh to be running (forwards prod PG to localhost:15432).

Prints, per user, the count of OpeningInsightFinding strengths / weaknesses
surfaced under default request filters (color=all, opponent_type=human, no
recency / time_control / platform / rated narrowing) — i.e. the same shape
a fresh dashboard load uses.

Run the script once on a pre-Plan-02 checkout (typically `main`) to capture
PRE-SWITCH counts, then on the Phase 80.1 working tree to capture POST-SWITCH
counts. Compare per Plan 80.1-04 Task 3b's pass / investigate / hard-stop rules.

Read-only by construction:
- compute_insights performs no writes (verified Plan 80.1-03).
- DSN should use a read-only DB role (flawchess_ro) — the script does not
  enforce that, but the DSN is passed in via env var.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.schemas.opening_insights import OpeningInsightsRequest  # noqa: E402
from app.services.opening_insights_service import compute_insights  # noqa: E402


def _tunnel_open(host: str = "localhost", port: int = 15432) -> bool:
    """Cheap TCP probe to confirm bin/prod_db_tunnel.sh is running."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


async def _check_user(session_factory: async_sessionmaker, user_id: int) -> None:
    async with session_factory() as session:
        # Default filter set: mirrors POST /api/insights/openings with no
        # narrowing — color=all, opponent_type=human, all recency/TC/platform.
        request = OpeningInsightsRequest()
        result = await compute_insights(
            session=session,
            user_id=user_id,
            request=request,
        )
        sw = len(result.white_strengths)
        ww = len(result.white_weaknesses)
        sb = len(result.black_strengths)
        wb = len(result.black_weaknesses)
        print(
            f"user={user_id:>6}  "
            f"white: {sw} strengths / {ww} weaknesses    "
            f"black: {sb} strengths / {wb} weaknesses    "
            f"total: {sw + ww + sb + wb}",
            flush=True,
        )


async def main(user_ids: list[int]) -> int:
    if not _tunnel_open():
        print(
            "ERROR: prod-DB tunnel not open on localhost:15432. Run `bin/prod_db_tunnel.sh` first.",
            file=sys.stderr,
        )
        return 2
    dsn = os.environ.get("PROD_TUNNEL_DATABASE_URL")
    if not dsn:
        print(
            "ERROR: set PROD_TUNNEL_DATABASE_URL to the prod read-only DSN "
            "(e.g. postgresql+asyncpg://flawchess_ro:...@localhost:15432/flawchess).",
            file=sys.stderr,
        )
        return 2
    engine = create_async_engine(dsn, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        for uid in user_ids:
            await _check_user(session_factory, uid)
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: prodcheck_80_1.py <user_id> [<user_id> ...]", file=sys.stderr)
        sys.exit(2)
    uids = [int(a) for a in sys.argv[1:]]
    sys.exit(asyncio.run(main(uids)))
