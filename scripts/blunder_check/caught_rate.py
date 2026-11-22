"""Phase 261 calibration report: the caught rate by facepalm-score band, and the served exploration share.

Reads ``blunder_check_windows`` and reports, per arm (exploration, main, legacy) and origin
(own, foreign, all), how often the user caught the blunder, by facepalm-score band, with 95%
Wilson intervals (``app.services.score_confidence.wilson_bounds``).

Denominator: reached windows, that is caught plus missed. A false alarm happens before the
blunder is reached, so it is counted beside each row and never in the denominator.

Score source (D-04): the serve-time snapshot ``blunder_check_windows.facepalm_score``. A legacy
window (``selection_arm`` NULL, composed before Phase 261) has no snapshot, so the live
``facepalm_expr(FACEPALM_DRILL_LAMBDA)`` of its ``game_flaws`` row is used while the game still
exists; otherwise the window is counted as unscored.

Share check (the phase's post-release acceptance): exploration windows over ended blunder
windows with a recorded arm, its 95% Wilson interval and a verdict. The rule is insufficient
below SHARE_MIN_WINDOWS windows, accept when the interval overlaps
[SHARE_ACCEPT_LOW, SHARE_ACCEPT_HIGH], fail when it lies entirely outside. Exploration slots
fill at least as easily as main slots (no cut, bigger pool), so a share below the low bound
points to an arm being dropped somewhere; main slots at the 0.70 cut can run short of supply
and push the share above 0.20, and above the high bound a quarter of the main slots would have
gone unserved relative to exploration.

The bands split at 0.5, so the "hard to catch" cut (D-06) can be re-read against the caught
rate on demand.

Read-only and anonymous: one read-only connection with a statement timeout
(``make_readonly_engine``); the output holds aggregates only, never user ids, usernames or game
ids. For prod, open the tunnel with ``bin/prod_db_tunnel.sh`` first; the script holds exactly one
connection because prod ``max_connections`` is 50.

Usage::

    uv run python scripts/blunder_check/caught_rate.py --db dev
    uv run python scripts/blunder_check/caught_rate.py --db prod --since 2026-11-23 --out <report.md>
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncConnection

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.blunder_check import (  # noqa: E402
    BlunderCheckWindow,
    WindowArm,
    WindowCase,
    WindowOutcome,
)
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA  # noqa: E402
from app.services.facepalm_score import facepalm_expr  # noqa: E402
from app.services.score_confidence import wilson_bounds  # noqa: E402
from scripts.blunder_check.sample import BLUNDER_SEVERITY, make_readonly_engine  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

DB_TARGETS: tuple[str, ...] = ("dev", "prod")

# (label, lower bound inclusive, upper bound exclusive); the last band includes 1.0.
SCORE_BANDS: tuple[tuple[str, float, float], ...] = (
    ("below 0.3", 0.0, 0.3),
    ("0.3-0.5", 0.3, 0.5),
    ("0.5-0.6", 0.5, 0.6),
    ("0.6-0.7", 0.6, 0.7),
    ("0.7-0.8", 0.7, 0.8),
    ("0.8-0.9", 0.8, 0.9),
    ("0.9-1.0", 0.9, 1.0),
)

# Served-share acceptance (Claude's discretion, owner-overridable); see the module docstring.
SHARE_ACCEPT_LOW: float = 0.18
SHARE_ACCEPT_HIGH: float = 0.26
SHARE_MIN_WINDOWS: int = 500

ArmLabel = Literal["exploration", "main", "legacy"]
OriginLabel = Literal["own", "foreign", "all"]
OutcomeLabel = Literal["caught", "missed", "false_alarm"]
ShareVerdict = Literal["accept", "fail", "insufficient"]

ARMS: tuple[ArmLabel, ...] = ("exploration", "main", "legacy")
ORIGINS: tuple[OriginLabel, ...] = ("own", "foreign", "all")

_OUTCOME_LABELS: dict[int, OutcomeLabel] = {
    WindowOutcome.CAUGHT: "caught",
    WindowOutcome.MISSED: "missed",
    WindowOutcome.FALSE_ALARM: "false_alarm",
}
_ARM_LABELS: dict[int, ArmLabel] = {
    WindowArm.MAIN: "main",
    WindowArm.EXPLORATION: "exploration",
}

EXIT_OK: int = 0
UNSCORED_BAND: str = "unscored"


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowRow:
    """One ended blunder window, reduced to what the report needs (no ids)."""

    arm: ArmLabel
    is_own: bool
    score: float | None
    outcome: OutcomeLabel


@dataclass(frozen=True)
class BandRow:
    """Caught rate of one (arm, origin, band) cell."""

    arm: ArmLabel
    origin: OriginLabel
    band: str
    reached: int
    caught: int
    rate: float | None
    low: float | None
    high: float | None
    false_alarms: int


@dataclass(frozen=True)
class ShareResult:
    """The served exploration share over ended blunder windows with a recorded arm."""

    n: int
    exploration: int
    share: float | None
    low: float | None
    high: float | None
    verdict: ShareVerdict


# ---------------------------------------------------------------------------
# Pure aggregation
# ---------------------------------------------------------------------------


def band_of(score: float | None) -> str | None:
    """The band label of a score; None for no score. Lower bound inclusive, 1.0 in the last band."""
    if score is None:
        return None
    for label, low, high in SCORE_BANDS[:-1]:
        if low <= score < high:
            return label
    return SCORE_BANDS[-1][0]


def window_row(
    arm: int | None,
    is_own: bool,
    snapshot: float | None,
    live: float | None,
    outcome: int,
) -> WindowRow:
    """Map one SQL row to a WindowRow: NULL arm is legacy, the snapshot wins over the live score."""
    arm_label: ArmLabel = "legacy" if arm is None else _ARM_LABELS[arm]
    score = snapshot if snapshot is not None else live
    return WindowRow(arm=arm_label, is_own=is_own, score=score, outcome=_OUTCOME_LABELS[outcome])


def _origins_of(row: WindowRow) -> tuple[OriginLabel, OriginLabel]:
    return ("own" if row.is_own else "foreign", "all")


def _band_row(arm: ArmLabel, origin: OriginLabel, band: str, rows: Sequence[WindowRow]) -> BandRow:
    caught = sum(r.outcome == "caught" for r in rows)
    reached = caught + sum(r.outcome == "missed" for r in rows)
    false_alarms = sum(r.outcome == "false_alarm" for r in rows)
    if reached == 0:
        return BandRow(arm, origin, band, 0, 0, None, None, None, false_alarms)
    rate = caught / reached
    low, high = wilson_bounds(rate, reached)
    return BandRow(arm, origin, band, reached, caught, rate, low, high, false_alarms)


def aggregate_caught_rate(rows: Sequence[WindowRow]) -> list[BandRow]:
    """One BandRow per (arm, origin, band); unscored windows are left out (see count_unscored)."""
    cells: dict[tuple[ArmLabel, OriginLabel, str], list[WindowRow]] = defaultdict(list)
    for row in rows:
        band = band_of(row.score)
        if band is None:
            continue
        for origin in _origins_of(row):
            cells[(row.arm, origin, band)].append(row)
    return [
        _band_row(arm, origin, label, cells.get((arm, origin, label), []))
        for arm in ARMS
        for origin in ORIGINS
        for label, _low, _high in SCORE_BANDS
    ]


def count_unscored(rows: Sequence[WindowRow]) -> dict[ArmLabel, int]:
    """Windows with no snapshot and no live score, per arm."""
    return {arm: sum(r.arm == arm and r.score is None for r in rows) for arm in ARMS}


def exploration_share(rows: Sequence[WindowRow]) -> ShareResult:
    """Exploration windows over ended blunder windows with a recorded arm, and the acceptance verdict."""
    armed = [r for r in rows if r.arm != "legacy"]
    n = len(armed)
    exploration = sum(r.arm == "exploration" for r in armed)
    if n == 0:
        return ShareResult(0, 0, None, None, None, "insufficient")
    share = exploration / n
    low, high = wilson_bounds(share, n)
    if n < SHARE_MIN_WINDOWS:
        verdict: ShareVerdict = "insufficient"
    elif low <= SHARE_ACCEPT_HIGH and high >= SHARE_ACCEPT_LOW:
        verdict = "accept"
    else:
        verdict = "fail"
    return ShareResult(n, exploration, share, low, high, verdict)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _ci(row: BandRow) -> str:
    if row.low is None or row.high is None:
        return "n/a"
    return f"{row.low * 100:.0f}-{row.high * 100:.0f}%"


def _share_section(share: ShareResult) -> list[str]:
    rule = (
        f"Rule: insufficient below {SHARE_MIN_WINDOWS} windows, accept when the 95% interval "
        f"overlaps [{SHARE_ACCEPT_LOW}, {SHARE_ACCEPT_HIGH}], fail when it lies entirely outside."
    )
    if share.share is None or share.low is None or share.high is None:
        counts = "No ended blunder windows with a recorded arm."
    else:
        counts = (
            f"{share.exploration} exploration of {share.n} ended blunder windows with a recorded "
            f"arm: share {share.share * 100:.1f}%, 95% CI "
            f"{share.low * 100:.1f}-{share.high * 100:.1f}%."
        )
    return ["## Exploration share", "", counts, "", f"Verdict: **{share.verdict}**. {rule}", ""]


def _arm_table(arm: ArmLabel, rows: Sequence[BandRow], unscored: int) -> list[str]:
    lines = [
        f"### Arm: {arm}",
        "",
        "| Band | Origin | Reached | Caught | Rate | 95% CI | False alarms |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row.arm != arm:
            continue
        lines.append(
            f"| {row.band} | {row.origin} | {row.reached} | {row.caught} | {_pct(row.rate)} "
            f"| {_ci(row)} | {row.false_alarms} |"
        )
    lines += ["", f"Unscored windows ({arm}): {unscored}", ""]
    return lines


def render_report(
    rows: Sequence[WindowRow],
    *,
    target: str,
    since: datetime.date | None,
    today: datetime.date,
) -> str:
    """The markdown report: share section, then one caught-rate table per arm."""
    band_rows = aggregate_caught_rate(rows)
    unscored = count_unscored(rows)
    since_text = since.isoformat() if since else "all time"
    lines = [
        "# Blunder check caught rate by facepalm-score band",
        "",
        f"Target: {target}; since: {since_text}; generated: {today.isoformat()}; "
        f"windows: {len(rows)}",
        "",
        *_share_section(exploration_share(rows)),
        "## Caught rate by score band",
        "",
        "Rate is caught over reached (caught + missed); false alarms happen before the blunder "
        "and are listed beside each row, never in the denominator.",
        "",
    ]
    for arm in ARMS:
        lines += _arm_table(arm, band_rows, unscored[arm])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Database access (read-only)
# ---------------------------------------------------------------------------


def build_statement(
    since: datetime.date | None,
) -> Select[tuple[Any, ...]]:
    """Ended blunder windows with their snapshot score and the live score of the flaw row.

    The live score is a correlated scalar subquery with LIMIT 1, never a join: game_flaws has no
    unique constraint on (game_id, ply) outside its composite PK with user_id, so a plain join
    could duplicate a window.
    """
    live_score = (
        select(facepalm_expr(FACEPALM_DRILL_LAMBDA))
        .where(
            GameFlaw.game_id == BlunderCheckWindow.game_id,
            GameFlaw.ply == BlunderCheckWindow.blunder_ply,
            GameFlaw.severity == BLUNDER_SEVERITY,
        )
        .limit(1)
        .scalar_subquery()
        .label("live_score")
    )
    stmt = select(
        BlunderCheckWindow.selection_arm,
        BlunderCheckWindow.is_own,
        BlunderCheckWindow.facepalm_score,
        live_score,
        BlunderCheckWindow.outcome,
    ).where(
        BlunderCheckWindow.window_case != WindowCase.HERRING,
        BlunderCheckWindow.outcome.in_(
            [WindowOutcome.CAUGHT, WindowOutcome.MISSED, WindowOutcome.FALSE_ALARM]
        ),
    )
    if since is not None:
        stmt = stmt.where(BlunderCheckWindow.ended_at >= since)
    return stmt


async def fetch_rows(conn: AsyncConnection, since: datetime.date | None) -> list[WindowRow]:
    """Run the statement and map each row; ids are never selected."""
    result = await conn.execute(build_statement(since))
    return [
        window_row(arm, is_own, snapshot, live, outcome)
        for arm, is_own, snapshot, live, outcome in result.all()
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Caught rate by facepalm-score band and the served exploration share."
    )
    parser.add_argument("--db", choices=DB_TARGETS, required=True, help="read-only source database")
    parser.add_argument(
        "--since",
        type=datetime.date.fromisoformat,
        default=None,
        help="only windows ended on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with engine.connect() as conn:
            rows = await fetch_rows(conn, args.since)
    finally:
        await engine.dispose()
    report = render_report(
        rows, target=args.db, since=args.since, today=datetime.datetime.now(datetime.UTC).date()
    )
    print(report)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report + "\n")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
