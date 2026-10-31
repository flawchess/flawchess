"""On-read "out of the opening" worse/better stats (Phase 243).

``get_out_of_opening_stats`` serves ``GET /api/openings/out-of-opening-stats``: for each
colour and each of the two rates it ranks the user per time control (D-06), collapses the
passing time controls into one game-weighted headline (D-07) and decides the red/green
gate with a 95% Wilson interval against the game-weighted peer median (D-08).

Shape (pipeline seams, nesting depth <= 4):

* ``fetch_opening_out_inputs``: sequential DB reads (one AsyncSession, no gather).
* ``build_out_of_opening_stats``: pure, no DB.
* ``get_out_of_opening_stats``: the two composed.

The per-TC rank status reuses the Endgames order (``rank_status``: anchor floor, pending,
own 30-game floor, ranked, unranked) so both pages behave the same. The significance gate
does NOT reuse the Endgames 99% helpers: z is passed in as ``OPENING_INSIGHTS_CI_Z_95``
(CONTEXT D-08).

Orientation is applied last. Gate and direction guard use RAW values only; the worse rate's
favourable percentile is 100 minus the raw CDF percentile, the better rate's is the raw one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.benchmark_cohort_cdf_repository import load_cohort_cells
from app.repositories.endgame_ranked_repository import fetch_ranked_games
from app.repositories.opening_out_repository import OpeningOutCounts, fetch_opening_out_counts
from app.repositories.user_benchmark_percentiles_repository import (
    PercentileRow,
    fetch_opening_out_rows,
)
from app.repositories.user_rating_anchors_repository import (
    RatingAnchorRow,
    fetch_anchors_for_user,
)
from app.schemas.endgames import RankStatus
from app.schemas.normalization import Color
from app.schemas.opening_out import (
    OpeningOutColorOut,
    OpeningOutRateOut,
    OpeningOutSide,
    OpeningOutTcOut,
    OutOfOpeningStatsResponse,
)
from app.services.canonical_slice_sql import OPENING_OUT_MIN_GAMES_PER_COLOR, TimeControlBucket
from app.services.endgame_ranked_service import RANKED_TC_ORDER, is_anchor_game, rank_status
from app.services.global_percentile_cdf import (
    BREAKPOINT_PERCENTILES,
    OpeningOutMetricId,
    round_anchor_to_grid,
)
from app.services.opening_insights_constants import OPENING_INSIGHTS_CI_Z_95
from app.services.score_confidence import (
    ci_excludes,
    wilson_bounds,
    wilson_score_test_p_value,
)

_COLORS: Final[tuple[Color, ...]] = ("white", "black")
_SIDE_METRIC: Final[dict[OpeningOutSide, OpeningOutMetricId]] = {
    "worse": "opening_worse_rate",
    "better": "opening_better_rate",
}

# Indices of the footer band's breakpoints inside a CDF cell (p1..p99, index = pct - 1).
_P25_INDEX: Final[int] = BREAKPOINT_PERCENTILES.index(25.0)
_P50_INDEX: Final[int] = BREAKPOINT_PERCENTILES.index(50.0)
_P75_INDEX: Final[int] = BREAKPOINT_PERCENTILES.index(75.0)
_MEDIAN_PERCENTILE: Final[float] = 50.0
_PERCENTILE_MAX: Final[float] = 100.0


@dataclass(frozen=True)
class PeerBand:
    """Peer p25 / p50 / p75 of one rate at the user's rounded anchor, fractions 0..1."""

    p25: float
    p50: float
    p75: float


@dataclass(frozen=True)
class OpeningOutInputs:
    """Everything the pure builder needs, fetched once per request.

    ``counts[tc][colour]`` is absent for a colour with no slice game in that TC.
    ``anchor_games`` / ``eval_pending`` are per-TC counts over the ranked sample (as on
    Endgames). ``peer_bands`` is keyed (metric, tc); a missing key means no CDF cell.
    """

    counts: dict[TimeControlBucket, dict[Color, OpeningOutCounts]] = field(default_factory=dict)
    anchor_games: dict[TimeControlBucket, int] = field(default_factory=dict)
    eval_pending: dict[TimeControlBucket, int] = field(default_factory=dict)
    anchors: dict[TimeControlBucket, RatingAnchorRow] = field(default_factory=dict)
    percentile_rows: dict[tuple[OpeningOutMetricId, TimeControlBucket, Color], PercentileRow] = (
        field(default_factory=dict)
    )
    peer_bands: dict[tuple[OpeningOutMetricId, TimeControlBucket], PeerBand] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class _TcEntry:
    """One (colour, rate, TC): its Endgames-style status plus the raw (unoriented) percentile."""

    tc: TimeControlBucket
    status: RankStatus
    k: int
    n: int
    floor_n: int
    floor_required: int
    raw_percentile: float | None
    band: PeerBand | None

    @property
    def contributes(self) -> bool:
        """True when the TC enters the headline and the gate (ranked and has a CDF cell)."""
        return self.status == "ranked" and self.raw_percentile is not None and self.band is not None


# ---------------------------------------------------------------------------
# Fetch (DB)
# ---------------------------------------------------------------------------


async def fetch_opening_out_inputs(session: AsyncSession, *, user_id: int) -> OpeningOutInputs:
    """Read counts, ranked-sample facts, anchors, persisted percentiles and peer bands.

    Sequential awaits only: one AsyncSession is one connection (CLAUDE.md, never
    ``asyncio.gather`` on a session).
    """
    counts: dict[TimeControlBucket, dict[Color, OpeningOutCounts]] = {}
    anchor_games: dict[TimeControlBucket, int] = {}
    eval_pending: dict[TimeControlBucket, int] = {}
    for tc in RANKED_TC_ORDER:
        games = await fetch_ranked_games(session, user_id=user_id, tc=tc)
        anchor_games[tc] = sum(1 for g in games if is_anchor_game(g))
        eval_pending[tc] = sum(1 for g in games if g.eval_pending)
        counts[tc] = await fetch_opening_out_counts(session, user_id=user_id, tc=tc)
    anchors = await fetch_anchors_for_user(session, user_id=user_id)
    percentile_rows = await fetch_opening_out_rows(session, user_id=user_id)
    peer_bands = await _fetch_peer_bands(session, anchors)
    return OpeningOutInputs(
        counts=counts,
        anchor_games=anchor_games,
        eval_pending=eval_pending,
        anchors=anchors,
        percentile_rows=percentile_rows,
        peer_bands=peer_bands,
    )


async def _fetch_peer_bands(
    session: AsyncSession, anchors: dict[TimeControlBucket, RatingAnchorRow]
) -> dict[tuple[OpeningOutMetricId, TimeControlBucket], PeerBand]:
    """Peer p25 / p50 / p75 per (rate, TC) at the user's rounded anchor, one batched read."""
    rounded = {tc: round_anchor_to_grid(a.anchor_rating) for tc, a in anchors.items()}
    cells = await load_cohort_cells(session, sorted(set(rounded.values())), list(rounded))
    bands: dict[tuple[OpeningOutMetricId, TimeControlBucket], PeerBand] = {}
    for tc, anchor_elo in rounded.items():
        for metric in _SIDE_METRIC.values():
            table = cells.get((metric, anchor_elo, tc))
            if table is None:
                continue
            bands[(metric, tc)] = PeerBand(
                p25=table.breakpoints[_P25_INDEX],
                p50=table.breakpoints[_P50_INDEX],
                p75=table.breakpoints[_P75_INDEX],
            )
    return bands


# ---------------------------------------------------------------------------
# Pure builder
# ---------------------------------------------------------------------------


def _tc_entry(
    inputs: OpeningOutInputs, side: OpeningOutSide, color: Color, tc: TimeControlBucket
) -> _TcEntry | None:
    """Status and counts of one (colour, rate, TC); None when the colour has no slice game."""
    counts = inputs.counts.get(tc, {}).get(color)
    if counts is None:
        return None
    metric = _SIDE_METRIC[side]
    k = counts.count_for(metric)
    n = counts.n_games
    row = inputs.percentile_rows.get((metric, tc, color))
    status, floor_n, floor_required = rank_status(
        has_anchor=tc in inputs.anchors,
        anchor_games=inputs.anchor_games.get(tc, 0),
        eval_dependent=True,
        value=k / n if n > 0 else None,
        eval_pending=inputs.eval_pending.get(tc, 0),
        floor_n=n,
        floor_required=OPENING_OUT_MIN_GAMES_PER_COLOR,
        row=row,
    )
    raw_percentile = row.percentile if status == "ranked" and row is not None else None
    return _TcEntry(
        tc=tc,
        status=status,
        k=k,
        n=n,
        floor_n=floor_n,
        floor_required=floor_required,
        raw_percentile=raw_percentile,
        band=inputs.peer_bands.get((metric, tc)),
    )


def _oriented(side: OpeningOutSide, raw: float | None) -> float | None:
    """Favourable percentile: fewer bad openings is good (100 - raw), more good openings is good."""
    if raw is None:
        return None
    return _PERCENTILE_MAX - raw if side == "worse" else raw


def _tc_out(side: OpeningOutSide, entry: _TcEntry) -> OpeningOutTcOut:
    return OpeningOutTcOut(
        tc=entry.tc,
        status=entry.status,
        k=entry.k,
        n=entry.n,
        rate=entry.k / entry.n if entry.n > 0 else None,
        floor_n=entry.floor_n,
        floor_required=entry.floor_required,
        percentile_favorable=_oriented(side, entry.raw_percentile),
    )


def _wilson_95(k: int, n: int) -> tuple[float, float]:
    """95% Wilson bounds of k / n (z passed in, never the Endgames 99% path)."""
    return wilson_bounds(k / n, n, z=OPENING_INSIGHTS_CI_Z_95)


def _weighted(weights: list[float], values: list[float]) -> float:
    return sum(w * v for w, v in zip(weights, values, strict=True))


def _ranked_card(side: OpeningOutSide, entries: list[_TcEntry]) -> OpeningOutRateOut:
    """Card for a colour with at least one contributing TC (D-07 headline, D-08 gate)."""
    contributing = [e for e in entries if e.contributes]
    k = sum(e.k for e in contributing)
    n = sum(e.n for e in contributing)
    weights = [e.n / n for e in contributing]
    bands = [e.band for e in contributing if e.band is not None]
    raw_headline = _weighted(weights, [e.raw_percentile or 0.0 for e in contributing])
    peer_p50 = _weighted(weights, [b.p50 for b in bands])
    ci_low, ci_high = _wilson_95(k, n)
    rate = k / n
    # Direction guard: the CI must exclude the peer median on the same side as the headline,
    # so a favourable verdict never rests on a rate significantly on the other side.
    significant = ci_excludes(peer_p50, ci_low, ci_high) and (rate > peer_p50) == (
        raw_headline > _MEDIAN_PERCENTILE
    )
    return OpeningOutRateOut(
        status="ranked",
        k=k,
        n=n,
        rate=rate,
        floor_n=n,
        floor_required=OPENING_OUT_MIN_GAMES_PER_COLOR,
        percentile_favorable=_oriented(side, raw_headline),
        ci_low=ci_low,
        ci_high=ci_high,
        # Same score test the Wilson CI inverts, so p < 0.05 iff the CI excludes peer_p50.
        p_value=wilson_score_test_p_value(rate, n, peer_p50),
        peer_p25=_weighted(weights, [b.p25 for b in bands]),
        peer_p50=peer_p50,
        peer_p75=_weighted(weights, [b.p75 for b in bands]),
        significant=significant,
        tcs=[_tc_out(side, e) for e in entries],
    )


def _unranked_status(entries: list[_TcEntry]) -> RankStatus:
    """Card status when no TC contributes: pending > unranked > below_floor."""
    statuses = {e.status for e in entries}
    if "pending" in statuses:
        return "pending"
    # Bug fix: a TC can be "ranked" (persisted percentile) yet contribute nothing because the
    # user's CURRENT anchor has no CDF cell (anchor moved after Stage B, sparse classical cell).
    # Without "ranked" here that case fell through to "below_floor" and rendered "0 of 30 games"
    # on a colour with hundreds of games. It is effectively not ranked yet.
    if "unranked" in statuses or "ranked" in statuses:
        return "unranked"
    return "below_floor"


def _unranked_card(side: OpeningOutSide, entries: list[_TcEntry]) -> OpeningOutRateOut:
    """Card when nothing contributes; k / n / rate are pooled over every listed TC."""
    status = _unranked_status(entries)
    k = sum(e.k for e in entries)
    n = sum(e.n for e in entries)
    matching = [e.floor_n for e in entries if e.status == status]
    return OpeningOutRateOut(
        status=status,
        k=k,
        n=n,
        rate=k / n if n > 0 else None,
        floor_n=max(matching, default=0),
        floor_required=OPENING_OUT_MIN_GAMES_PER_COLOR,
        tcs=[_tc_out(side, e) for e in entries],
    )


def _rate_card(inputs: OpeningOutInputs, side: OpeningOutSide, color: Color) -> OpeningOutRateOut:
    entries = [
        entry for tc in RANKED_TC_ORDER if (entry := _tc_entry(inputs, side, color, tc)) is not None
    ]
    if any(e.contributes for e in entries):
        return _ranked_card(side, entries)
    return _unranked_card(side, entries)


def build_out_of_opening_stats(inputs: OpeningOutInputs) -> OutOfOpeningStatsResponse:
    """Pure builder: both colours, both rates, collapsed over time controls."""
    cards = {
        color: OpeningOutColorOut(
            worse=_rate_card(inputs, "worse", color),
            better=_rate_card(inputs, "better", color),
        )
        for color in _COLORS
    }
    return OutOfOpeningStatsResponse(white=cards["white"], black=cards["black"])


async def get_out_of_opening_stats(
    session: AsyncSession, *, user_id: int
) -> OutOfOpeningStatsResponse:
    """Fetch the inputs and build the response.

    V4 Information Disclosure mitigation: ``user_id`` must come from the authenticated
    user (``current_active_user.id``), never from the request.
    """
    inputs = await fetch_opening_out_inputs(session, user_id=user_id)
    return build_out_of_opening_stats(inputs)
