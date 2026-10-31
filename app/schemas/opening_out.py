"""Schemas for GET /api/openings/out-of-opening-stats (Phase 243).

The "out of the opening" section ranks two rates per colour against rating x TC peers:
the share of games the user leaves the opening clearly worse (primary) and clearly
better (secondary). The payload is filter-independent (canonical ranked slice only)
and carries everything the card and its popover render, so the frontend never
re-derives significance or orientation.

Units: ``rate`` and the peer bands are fractions 0..1. ``percentile_favorable`` is
0..100 where HIGHER IS BETTER FOR THE USER: for the worse rate it is 100 minus the raw
CDF percentile ("Fewer bad openings than N% of peers"), for the better rate it is the
raw percentile ("More good openings than N% of peers").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.endgames import RankStatus

TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]
OpeningOutSide = Literal["worse", "better"]


class OpeningOutTcOut(BaseModel):
    """One time control's worse (or better) rate for one colour (popover per-TC list).

    k / n: games classified worse (better) and qualifying games in this TC (n counts
        games that reached the middlegame with an eval, or ended early by result).
    rate: k / n as a fraction, None when n == 0.
    floor_n / floor_required: the binding count and its floor ("18 of 30"); the anchor
        floor applies first, exactly as on Endgames.
    percentile_favorable: set only when status == "ranked" (see module docstring).
    """

    tc: TimeControlBucket
    status: RankStatus
    k: int
    n: int
    rate: float | None
    floor_n: int
    floor_required: int
    percentile_favorable: float | None = None


class OpeningOutRateOut(BaseModel):
    """One colour x rate card row, collapsed over the time controls that qualify.

    status: "ranked" when at least one TC contributes. Otherwise pending when any TC is
        pending, else unranked when any TC is unranked, else below_floor.
    k / n / rate: pooled over the contributing TCs, or over every listed TC when none
        contributes (so a below-floor card still shows its raw rate).
    percentile_favorable: game-weighted mean of the contributing TCs' percentiles, after
        orientation. None unless status == "ranked".
    ci_low / ci_high: 95% Wilson bounds of the pooled rate (None unless ranked).
    p_value: two-sided Wilson score-test p of the pooled rate against peer_p50 (the
        inversion of the CI, so p < 0.05 iff the CI excludes it). None unless ranked.
    peer_p25 / peer_p50 / peer_p75: game-weighted peer band (same weights as the
        headline), fractions 0..1 (None unless ranked).
    significant: the 95% CI excludes the game-weighted peer median on the headline's
        side; the red/green verdict shows only when True.
    tcs: every listed time control (contributing or not), fastest to slowest.
    """

    status: RankStatus
    k: int
    n: int
    rate: float | None
    floor_n: int
    floor_required: int
    percentile_favorable: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    peer_p25: float | None = None
    peer_p50: float | None = None
    peer_p75: float | None = None
    significant: bool = False
    tcs: list[OpeningOutTcOut] = Field(default_factory=list)


class OpeningOutColorOut(BaseModel):
    """Both rates of one colour."""

    worse: OpeningOutRateOut
    better: OpeningOutRateOut


class OutOfOpeningStatsResponse(BaseModel):
    """Both colours' collapsed out-of-the-opening stats (the endpoint takes no filters)."""

    white: OpeningOutColorOut
    black: OpeningOutColorOut
