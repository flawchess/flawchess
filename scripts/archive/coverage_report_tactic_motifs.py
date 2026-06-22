"""Read-only D-04 tactic-motif coverage report (Phase 125 Plan 01).

Prints four sections documenting tactic_motif coverage across all
mistake+blunder flaws on full-eval'd games:

  1. Overall: total M+B flaw rows, PV coverage, tagged count, percentages.
  2. By-motif: counts per motif name (uses _INT_TO_MOTIF mapping), ordered
     by count descending; suppressed motifs printed with "(0)" so absence is
     visible, not silent.
  3. NULL split: no_pv_null vs pv_no_fire breakdown with interpretation.
  4. Spot-check: small samples from each NULL bucket for human eyeballing.

The script is READ-ONLY — it issues only SELECT statements and never
calls session.commit() or any DML.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

Usage:
    uv run python scripts/coverage_report_tactic_motifs.py --db dev
    uv run python scripts/coverage_report_tactic_motifs.py --db prod
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402
from app.services.tactic_detector import _INT_TO_MOTIF  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants (CLAUDE.md no-magic-numbers)
# ---------------------------------------------------------------------------

# Severity values matching game_flaws.severity: 1=mistake, 2=blunder.
_MISTAKE_SEVERITY = 1
_BLUNDER_SEVERITY = 2
_MISTAKE_BLUNDER_SEVERITIES: tuple[int, int] = (_MISTAKE_SEVERITY, _BLUNDER_SEVERITY)

# Sample size per NULL bucket for the spot-check section.
_SPOT_CHECK_SAMPLE_SIZE = 3

# Motifs that lack ≥10 hand-confirmed prod fixtures and are therefore
# query-suppressed (D-11 — stored in DB but not surfaced in the UI until
# Q-011 validates them). Listed here so the report shows them with count=0
# when they did not fire, making absence explicit rather than silent.
# Source: tests/services/test_tactic_detector.py _QUERY_SUPPRESSED_MOTIFS.
_QUERY_SUPPRESSED_MOTIFS: frozenset[str] = frozenset(
    {
        "double-check",
        "interference",
        "smothered-mate",
        "self-interference",
        "sacrifice",
        "arabian-mate",
        "boden-mate",
        "double-bishop-mate",
    }
)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


async def _print_overall(conn: Any, db: str) -> None:
    """Section 1: overall M+B flaw counts and PV/tactic-tag percentages."""
    # _MISTAKE_BLUNDER_SEVERITIES = (1, 2) — fixed program constants, not user data.
    # Embedded directly in SQL to avoid asyncpg's lack of tuple-bind support.
    sql = text(
        f"""
        SELECT
            COUNT(*)                                                          AS total_mb_flaws,
            COUNT(gp_next.pv)                                                AS has_pv,
            COUNT(*) FILTER (
                WHERE gp_next.pv IS NOT NULL AND gf.tactic_motif IS NOT NULL
            )                                                                 AS tagged,
            COUNT(*) FILTER (
                WHERE gp_next.pv IS NOT NULL AND gf.tactic_motif IS NULL
            )                                                                 AS pv_no_fire,
            COUNT(*) FILTER (WHERE gp_next.pv IS NULL)                       AS no_pv_null
        FROM game_flaws gf
        JOIN games g
            ON g.id = gf.game_id AND g.user_id = gf.user_id
        LEFT JOIN game_positions gp_next
            ON gp_next.game_id = gf.game_id
            AND gp_next.user_id = gf.user_id
            AND gp_next.ply = gf.ply + 1
        WHERE g.full_evals_completed_at IS NOT NULL
          AND gf.severity IN {_MISTAKE_BLUNDER_SEVERITIES}
        """
    )
    row = (await conn.execute(sql)).one()
    total: int = row.total_mb_flaws
    has_pv: int = row.has_pv
    tagged: int = row.tagged
    pv_no_fire: int = row.pv_no_fire
    no_pv_null: int = row.no_pv_null

    pct_has_pv = (has_pv / total * 100.0) if total else 0.0
    pct_no_pv = (no_pv_null / total * 100.0) if total else 0.0
    pct_tagged_of_pv = (tagged / has_pv * 100.0) if has_pv else 0.0

    print()
    print("=== Tactic Motif Coverage Report ===")
    print(f"DB target: {db}")
    print("Scope: mistake+blunder flaws on full-eval'd games")
    print()
    print("Overall:")
    print(f"  Total M+B flaw rows:      {total:>10,}")
    print(f"  Flaws with PV at ply+1:   {has_pv:>10,}  ({pct_has_pv:.1f}%)  <- tactic-detectable")
    print(
        f"  Flaws without PV:         {no_pv_null:>10,}  ({pct_no_pv:.1f}%)  <- genuinely undetectable"
    )
    print()
    print("After Backfill:")
    print(f"  Non-NULL tactic_motif:    {tagged:>10,}  ({pct_tagged_of_pv:.1f}% of has-PV rows)")
    print(f"  PV present, no fire:      {pv_no_fire:>10,}  (honest low-confidence no-fires)")


async def _print_by_motif(conn: Any) -> None:
    """Section 2: per-motif flaw counts, ordered by count descending."""
    sql = text(
        f"""
        SELECT gf.tactic_motif, COUNT(*) AS count
        FROM game_flaws gf
        JOIN games g
            ON g.id = gf.game_id AND g.user_id = gf.user_id
        WHERE g.full_evals_completed_at IS NOT NULL
          AND gf.severity IN {_MISTAKE_BLUNDER_SEVERITIES}
          AND gf.tactic_motif IS NOT NULL
        GROUP BY gf.tactic_motif
        ORDER BY count DESC
        """
    )
    rows = (await conn.execute(sql)).fetchall()

    # Build name→count dict from query results.
    fired_counts: dict[str, int] = {}
    for row in rows:
        motif_name = _INT_TO_MOTIF.get(row.tactic_motif, f"unknown({row.tactic_motif})")
        fired_counts[motif_name] = row.count

    # Build display list: fired motifs first (desc count), then suppressed-but-silent ones.
    print()
    print("By-motif counts (non-NULL tactic_motif rows):")
    if not fired_counts:
        print("  (no rows tagged yet — run the backfill first)")
    else:
        # Sort fired by count descending, then by name for ties.
        for name, count in sorted(fired_counts.items(), key=lambda x: (-x[1], x[0])):
            suppressed_marker = " [query-suppressed]" if name in _QUERY_SUPPRESSED_MOTIFS else ""
            print(f"  {name:<30}  {count:>8,}{suppressed_marker}")

    # Show suppressed motifs that did NOT fire (count 0) to make absence explicit.
    for name in sorted(_QUERY_SUPPRESSED_MOTIFS - set(fired_counts)):
        print(f"  {name:<30}  {0:>8,}  [query-suppressed, did not fire]")


async def _print_null_split(conn: Any) -> None:
    """Section 3: NULL split — no_pv_null vs pv_no_fire with interpretation."""
    sql = text(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE gp_next.pv IS NULL)                       AS no_pv_null,
            COUNT(*) FILTER (
                WHERE gp_next.pv IS NOT NULL AND gf.tactic_motif IS NULL
            )                                                                 AS pv_no_fire
        FROM game_flaws gf
        JOIN games g
            ON g.id = gf.game_id AND g.user_id = gf.user_id
        LEFT JOIN game_positions gp_next
            ON gp_next.game_id = gf.game_id
            AND gp_next.user_id = gf.user_id
            AND gp_next.ply = gf.ply + 1
        WHERE g.full_evals_completed_at IS NOT NULL
          AND gf.severity IN {_MISTAKE_BLUNDER_SEVERITIES}
        """
    )
    row = (await conn.execute(sql)).one()
    no_pv_null: int = row.no_pv_null
    pv_no_fire: int = row.pv_no_fire

    print()
    print("NULL split:")
    print(f"  No PV at ply+1:           {no_pv_null:>10,}  <- no_pv_null bucket")
    print(f"  PV present, no fire:      {pv_no_fire:>10,}  <- pv_no_fire bucket")
    print()
    print("  Interpretation: NULL tactic_motif = honest (no PV available, or PV present")
    print("  but no detector reached confidence threshold). NOT skipped or missing data.")


async def _print_spot_check(conn: Any) -> None:
    """Section 4: small samples from each NULL bucket for human eyeballing."""
    # Sample from no_pv_null bucket: confirm pv IS NULL at ply+1.
    sql_no_pv = text(
        f"""
        SELECT gf.user_id, gf.game_id, gf.ply, gf.severity
        FROM game_flaws gf
        JOIN games g
            ON g.id = gf.game_id AND g.user_id = gf.user_id
        LEFT JOIN game_positions gp_next
            ON gp_next.game_id = gf.game_id
            AND gp_next.user_id = gf.user_id
            AND gp_next.ply = gf.ply + 1
        WHERE g.full_evals_completed_at IS NOT NULL
          AND gf.severity IN {_MISTAKE_BLUNDER_SEVERITIES}
          AND gp_next.pv IS NULL
        LIMIT :sample_size
        """
    )
    no_pv_rows = (
        await conn.execute(sql_no_pv, {"sample_size": _SPOT_CHECK_SAMPLE_SIZE})
    ).fetchall()

    # Sample from pv_no_fire bucket: show pv text so a human can check no detector
    # should have fired.
    sql_pv_no_fire = text(
        f"""
        SELECT gf.user_id, gf.game_id, gf.ply, gf.severity, gp_next.pv
        FROM game_flaws gf
        JOIN games g
            ON g.id = gf.game_id AND g.user_id = gf.user_id
        LEFT JOIN game_positions gp_next
            ON gp_next.game_id = gf.game_id
            AND gp_next.user_id = gf.user_id
            AND gp_next.ply = gf.ply + 1
        WHERE g.full_evals_completed_at IS NOT NULL
          AND gf.severity IN {_MISTAKE_BLUNDER_SEVERITIES}
          AND gp_next.pv IS NOT NULL
          AND gf.tactic_motif IS NULL
        LIMIT :sample_size
        """
    )
    pv_no_fire_rows = (
        await conn.execute(sql_pv_no_fire, {"sample_size": _SPOT_CHECK_SAMPLE_SIZE})
    ).fetchall()

    print()
    print(f"Spot-check samples ({_SPOT_CHECK_SAMPLE_SIZE} per bucket):")
    print()
    print("  no_pv_null bucket (pv IS NULL at ply+1):")
    if not no_pv_rows:
        print("    (no rows in this bucket)")
    else:
        for r in no_pv_rows:
            severity_label = "mistake" if r.severity == _MISTAKE_SEVERITY else "blunder"
            print(
                f"    user_id={r.user_id}, game_id={r.game_id}, ply={r.ply}, severity={severity_label}"
            )

    print()
    print("  pv_no_fire bucket (pv present, tactic_motif IS NULL):")
    if not pv_no_fire_rows:
        print("    (no rows in this bucket)")
    else:
        for r in pv_no_fire_rows:
            severity_label = "mistake" if r.severity == _MISTAKE_SEVERITY else "blunder"
            pv_preview = (r.pv[:60] + "...") if r.pv and len(r.pv) > 60 else r.pv
            print(
                f"    user_id={r.user_id}, game_id={r.game_id}, ply={r.ply}, "
                f"severity={severity_label}"
            )
            print(f"      pv: {pv_preview!r}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(db: str) -> None:
    """Run the four D-04 report sections against the chosen DB target."""
    url = db_url_for_target(db)
    engine = create_async_engine(url, pool_pre_ping=True)

    _log(f"Connecting to {db} DB…")
    try:
        async with engine.connect() as conn:
            await _print_overall(conn, db)
            await _print_by_motif(conn)
            await _print_null_split(conn)
            await _print_spot_check(conn)
            # Never commit — this script is read-only.
    finally:
        await engine.dispose()

    _log("Report complete.")


def _parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Read-only D-04 tactic-motif coverage report (Phase 125)"
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(db=args.db))
