"""Shared seeded-user fixture for router integration tests (Phase 61).

Provides a single authoritative test user with a deterministic portfolio of
games and positions, committed to flawchess_test so HTTP endpoints can observe
the data through the patched async_session_maker. The seeded_user fixture is
module-scoped: register+seed cost is paid once per test module, not once per
test function.

Portfolio (25 games):
- 15 "base" games covering platforms × time controls × colors × WDL, a
  rook→pawn endgame-class transition (game 15), and one unrated game.
- 10 additional chess.com blitz endgame games with clock_seconds populated
  (games 16–25). These take the blitz endgame-game count to 11 — enough to
  cross MIN_GAMES_FOR_CLOCK_STATS=10 so the clock-pressure and time-pressure
  router endpoints have data to return. They also diversify the endgame
  classes so all six (rook, pawn, minor_piece, queen, mixed, pawnless) are
  represented in stats.categories.

Expected aggregates are computed once and returned alongside the user data so
test assertions can reference them by name rather than hand-counting. The
`EXPECTED` dict is verified against the spec at module import time.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest_asyncio

from app.main import app
from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD

# Deterministic Zobrist hash used for every game's ply=0 position so
# /api/openings/next-moves queries at the starting position match all games.
STARTING_POSITION_HASH: int = 0x0123456789ABCDEF

# Base clock (starting time in seconds) per time control bucket. Used as
# Game.base_time_seconds AND as the scaling denominator for clock_seconds
# on endgame-entry plies.
_BASE_TIME_SECONDS: dict[str, int] = {
    "bullet": 60,
    "blitz": 600,
    "rapid": 1800,
    "classical": 3600,
}

# Default (signature, imbalance) per endgame_class int. Games that want a
# different signature/imbalance can override via the spec's `endgame_overrides`.
# Class ints follow the IntEnum in position_classifier: 1=rook, 2=minor_piece,
# 3=pawn, 4=queen, 5=mixed, 6=pawnless.
_CLASS_DEFAULT: dict[int, tuple[str, int]] = {
    1: ("KR_KR", 0),  # rook
    2: ("KN_KN", 0),  # minor_piece
    3: ("KPP_KP", 100),  # pawn — white up a pawn
    4: ("KQ_KQ", 0),  # queen
    5: ("KRBP_KRP", 0),  # mixed (rook + minor + pawn, both sides have pawns)
    6: ("KRN_KR", 300),  # pawnless (rook + minor, no pawns)
}

# String label for each class int (must match classify_endgame_class output).
_CLASS_LABEL: dict[int, str] = {
    1: "rook",
    2: "minor_piece",
    3: "pawn",
    4: "queen",
    5: "mixed",
    6: "pawnless",
}


@dataclass
class SeededUser:
    """Test user with a committed portfolio and derived expected aggregates."""

    id: int
    email: str
    auth_headers: dict[str, str]
    expected: dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Portfolio spec
# -----------------------------------------------------------------------------
#
# Each game dict carries:
#   platform, bucket, color, result, rated                    (always required)
#   endgame:       None | list[int]                           (class ints per span)
#   clocks:        None | (user_entry_clock, opp_entry_clock) (seconds, optional)
#   termination:   None | str                                 ("timeout", "checkmate", etc.)
#
# Ply-parity rule the service uses: at position ply N, clock_seconds is the
# clock of the player who just moved, so:
#   - even ply (30, 32, 34) → white's clock
#   - odd  ply (31, 33, 35) → black's clock
# At ply=30 (span entry), the first even-ply clock is white's and the first
# odd-ply clock is black's. For the user_color="black" games below, I swap
# the seeded (white_clock, black_clock) so user_entry_clock correctly maps
# to the ply-parity matching the user.

_GAMES_SPEC: list[dict[str, Any]] = [
    # --- Games 1-15: base portfolio (no clocks except where noted) ------------
    {"platform": "chess.com", "bucket": "blitz",     "color": "white", "result": "1-0",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "chess.com", "bucket": "blitz",     "color": "white", "result": "1-0",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "chess.com", "bucket": "blitz",     "color": "white", "result": "1/2-1/2", "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "chess.com", "bucket": "blitz",     "color": "black", "result": "0-1",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "chess.com", "bucket": "blitz",     "color": "black", "result": "1-0",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "chess.com", "bucket": "rapid",     "color": "white", "result": "0-1",     "rated": True,  "endgame": [1],    "clocks": (900, 880),   "termination": None},
    {"platform": "chess.com", "bucket": "rapid",     "color": "white", "result": "0-1",     "rated": True,  "endgame": [1],    "clocks": (850, 870),   "termination": None},
    {"platform": "lichess",   "bucket": "blitz",     "color": "white", "result": "1-0",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "lichess",   "bucket": "blitz",     "color": "white", "result": "1-0",     "rated": True,  "endgame": [1],    "clocks": (400, 390),   "termination": None},
    {"platform": "lichess",   "bucket": "bullet",    "color": "black", "result": "1/2-1/2", "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "lichess",   "bucket": "bullet",    "color": "black", "result": "1/2-1/2", "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "lichess",   "bucket": "classical", "color": "white", "result": "1-0",     "rated": True,  "endgame": [3],    "clocks": (2400, 2350), "termination": None},
    {"platform": "lichess",   "bucket": "classical", "color": "white", "result": "0-1",     "rated": True,  "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "lichess",   "bucket": "rapid",     "color": "white", "result": "1-0",     "rated": False, "endgame": None,   "clocks": None,         "termination": None},
    {"platform": "lichess",   "bucket": "rapid",     "color": "white", "result": "1/2-1/2", "rated": True,  "endgame": [1, 3], "clocks": (950, 900),   "termination": None},
    # --- Games 16-25: chess.com blitz endgame with clocks for time-pressure ---
    # Chosen to cover: all 6 endgame classes × varied user-vs-opp clock pairs
    # × 3 timeout terminations (2 wins, 1 loss → non-zero net timeout rate).
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "1-0",     "rated": True, "endgame": [1], "clocks": (300, 310), "termination": "timeout"},      # 16 user win via timeout
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "0-1",     "rated": True, "endgame": [1], "clocks": (50, 200),  "termination": "timeout"},      # 17 user loss via timeout
    {"platform": "chess.com", "bucket": "blitz", "color": "black", "result": "0-1",     "rated": True, "endgame": [1], "clocks": (200, 50),  "termination": "timeout"},      # 18 user win via timeout (opp flagged)
    {"platform": "chess.com", "bucket": "blitz", "color": "black", "result": "1-0",     "rated": True, "endgame": [3], "clocks": (250, 260), "termination": None},           # 19 user loss
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "1/2-1/2", "rated": True, "endgame": [2], "clocks": (400, 400), "termination": None},           # 20 minor_piece
    {"platform": "chess.com", "bucket": "blitz", "color": "black", "result": "1/2-1/2", "rated": True, "endgame": [2], "clocks": (200, 210), "termination": None},           # 21 minor_piece black
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "1-0",     "rated": True, "endgame": [4], "clocks": (350, 340), "termination": None},           # 22 queen
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "0-1",     "rated": True, "endgame": [5], "clocks": (100, 250), "termination": None},           # 23 mixed, user in pressure
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "0-1",     "rated": True, "endgame": [6], "clocks": (150, 200), "termination": None},           # 24 pawnless
    {"platform": "chess.com", "bucket": "blitz", "color": "white", "result": "1-0",     "rated": True, "endgame": [4], "clocks": (380, 370), "termination": None},           # 25 queen
]  # fmt: skip


# -----------------------------------------------------------------------------
# EXPECTED aggregates (hand-maintained; verified against spec at import time)
# -----------------------------------------------------------------------------

EXPECTED: dict[str, Any] = {
    "total_games": 25,
    "global_wdl": {"wins": 11, "draws": 6, "losses": 8},
    "by_platform": {"chess.com": 17, "lichess": 8},
    "by_time_control": {"bullet": 2, "blitz": 17, "rapid": 4, "classical": 2},
    "by_color": {
        "white": {"total": 18, "wins": 9, "draws": 3, "losses": 6},
        "black": {"total": 7, "wins": 2, "draws": 3, "losses": 2},
    },
    "rated_total": 24,
    # Endgame: 15 distinct games have at least one span (6,7,9,12,15,16–25).
    # Per-class counts are distinct-game counts; game 15 appears in both rook
    # and pawn because it has a class-1→class-3 transition.
    "endgame_games_distinct": 15,
    "endgame_by_class": {
        "rook": 7,  # 6, 7, 9, 15, 16, 17, 18
        "pawn": 3,  # 12, 15, 19
        "minor_piece": 2,  # 20, 21
        "queen": 2,  # 22, 25
        "mixed": 1,  # 23
        "pawnless": 1,  # 24
    },
    # Back-compat aliases used by existing router tests.
    "endgame_rook_games": 7,
    "endgame_pawn_games": 3,
    # Clock pressure: MIN_GAMES_FOR_CLOCK_STATS = 10 (endgame_service.py).
    # Only the blitz bucket clears it (11 blitz endgame games with clocks);
    # rapid has 3 (games 6, 7, 15), classical has 1 (game 12), bullet has 0.
    "clock_pressure_qualifying_buckets": ["blitz"],
    "clock_pressure_blitz_games": 11,  # 9, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
    "clock_pressure_blitz_timeout_wins": 2,  # games 16, 18
    "clock_pressure_blitz_timeout_losses": 1,  # game 17
    # Starting-position hash match — every game has a ply=0 position at the shared hash.
    "starting_position_game_count": 25,
}


def _verify_expected_matches_spec() -> None:
    """Recompute spec-derivable aggregates and cross-check EXPECTED.

    Runs at module import so any drift between _GAMES_SPEC and EXPECTED
    crashes pytest collection loudly rather than silently producing a
    misleading router-test failure.
    """
    games = _GAMES_SPEC
    assert len(games) == EXPECTED["total_games"], (
        f"spec has {len(games)} games, EXPECTED declares {EXPECTED['total_games']}"
    )

    # Platform totals
    from collections import Counter

    plat = Counter(g["platform"] for g in games)
    assert dict(plat) == EXPECTED["by_platform"], (
        f"platform mismatch: spec={dict(plat)} vs EXPECTED={EXPECTED['by_platform']}"
    )

    # Time-control totals
    tc = Counter(g["bucket"] for g in games)
    assert dict(tc) == EXPECTED["by_time_control"], (
        f"time_control mismatch: spec={dict(tc)} vs EXPECTED={EXPECTED['by_time_control']}"
    )

    # Rated total
    assert sum(1 for g in games if g["rated"]) == EXPECTED["rated_total"]

    # Per-color WDL from the user's perspective
    def _outcome(result: str, color: str) -> str:
        if result == "1/2-1/2":
            return "draw"
        white_won = result == "1-0"
        user_is_white = color == "white"
        return "win" if (white_won == user_is_white) else "loss"

    for col in ("white", "black"):
        col_games = [g for g in games if g["color"] == col]
        wdl = Counter(_outcome(g["result"], g["color"]) for g in col_games)
        expected_col = EXPECTED["by_color"][col]
        assert len(col_games) == expected_col["total"], f"{col} total mismatch"
        assert wdl["win"] == expected_col["wins"], f"{col} wins mismatch"
        assert wdl["draw"] == expected_col["draws"], f"{col} draws mismatch"
        assert wdl["loss"] == expected_col["losses"], f"{col} losses mismatch"

    # Endgame distinct count
    endgame_games = [g for g in games if g["endgame"] is not None]
    assert len(endgame_games) == EXPECTED["endgame_games_distinct"]

    # Endgame-by-class (distinct games per class label)
    by_class: dict[str, int] = {}
    for g in endgame_games:
        for class_int in g["endgame"]:
            by_class[_CLASS_LABEL[class_int]] = by_class.get(_CLASS_LABEL[class_int], 0) + 1
    assert by_class == EXPECTED["endgame_by_class"], (
        f"endgame_by_class mismatch: spec={by_class} vs EXPECTED={EXPECTED['endgame_by_class']}"
    )

    # Clock-pressure qualifying buckets: buckets with >= 10 endgame games that
    # have clock data. The service's threshold is MIN_GAMES_FOR_CLOCK_STATS=10.
    bucket_clock_games: dict[str, int] = {}
    for g in endgame_games:
        if g["clocks"] is not None:
            bucket_clock_games[g["bucket"]] = bucket_clock_games.get(g["bucket"], 0) + 1
    qualifying = sorted(b for b, n in bucket_clock_games.items() if n >= 10)
    assert qualifying == EXPECTED["clock_pressure_qualifying_buckets"], (
        f"clock_pressure qualifying buckets mismatch: "
        f"spec={qualifying} vs EXPECTED={EXPECTED['clock_pressure_qualifying_buckets']}"
    )
    assert bucket_clock_games.get("blitz", 0) == EXPECTED["clock_pressure_blitz_games"]


_verify_expected_matches_spec()


# -----------------------------------------------------------------------------
# Registration + seeding
# -----------------------------------------------------------------------------


async def _register_and_login(
    client: httpx.AsyncClient,
) -> tuple[int, str, dict[str, str]]:
    email = f"seed_{uuid.uuid4().hex[:10]}@example.com"
    password = "seededuserpw123"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    reg.raise_for_status()
    user_id = int(reg.json()["id"])

    login = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    return user_id, email, {"Authorization": f"Bearer {token}"}


def _clock_series_for_span(
    span_start_ply: int,
    user_color: str,
    user_entry_clock: float,
    opp_entry_clock: float,
) -> list[float]:
    """Return ENDGAME_PLY_THRESHOLD clock values for a span starting at
    `span_start_ply`, with the user/opp entry clocks landing on the correct
    ply parities.

    Ply convention (from app/services/zobrist.py:158 — ply 0 stores clock
    from move 1 = white's move): even ply → white's clock, odd ply → black's.
    So for user_color="white", user clocks sit at even plies; for "black",
    at odd plies. Clocks decay by 5s per ply to keep realistic monotone.
    """
    series: list[float] = []
    user_parity = 0 if user_color == "white" else 1
    user_ticks = 0  # how many user-side plies seen so far in this span
    opp_ticks = 0
    for offset in range(ENDGAME_PLY_THRESHOLD):
        ply = span_start_ply + offset
        if ply % 2 == user_parity:
            series.append(max(0.0, user_entry_clock - 5.0 * user_ticks))
            user_ticks += 1
        else:
            series.append(max(0.0, opp_entry_clock - 5.0 * opp_ticks))
            opp_ticks += 1
    return series


async def _seed_portfolio(user_id: int) -> None:
    """Commit all _GAMES_SPEC games + their positions for the registered user.

    Uses the patched async_session_maker (bound to flawchess_test by
    tests/conftest.py override_get_async_session) directly, so the writes
    land in the test DB and are visible to HTTP endpoints in the same run.
    """
    from app.core.database import async_session_maker
    from app.models.game import Game
    from app.models.game_position import GamePosition

    base_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)

    async with async_session_maker() as session:
        for idx, spec in enumerate(_GAMES_SPEC, start=1):
            color = spec["color"]
            bucket = spec["bucket"]
            base_time = _BASE_TIME_SECONDS[bucket]
            game = Game(
                user_id=user_id,
                platform=spec["platform"],
                platform_game_id=f"seed-{idx:02d}",
                platform_url=f"https://example.com/game/{idx}",
                pgn="1. e4 e5 *",
                result=spec["result"],
                user_color=color,
                time_control_str=f"{base_time}+0",
                time_control_bucket=bucket,
                time_control_seconds=base_time,
                base_time_seconds=base_time,
                rated=spec["rated"],
                is_computer_game=False,
                white_username="seededuser" if color == "white" else "opponent",
                black_username="opponent" if color == "white" else "seededuser",
                white_rating=1500,
                black_rating=1510,
                termination=spec["termination"],
            )
            game.played_at = base_dt + datetime.timedelta(days=idx)
            session.add(game)
            await session.flush()

            # Starting position (ply=0, shared hash across all games)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=0,
                    full_hash=STARTING_POSITION_HASH,
                    white_hash=STARTING_POSITION_HASH + 1,
                    black_hash=STARTING_POSITION_HASH + 2,
                    move_san="e4",
                )
            )
            # Game-specific ply=1 position (deterministic per-game hashes)
            session.add(
                GamePosition(
                    game_id=game.id,
                    user_id=user_id,
                    ply=1,
                    full_hash=STARTING_POSITION_HASH + 1000 + idx,
                    white_hash=STARTING_POSITION_HASH + 2000 + idx,
                    black_hash=STARTING_POSITION_HASH + 3000 + idx,
                    move_san="e5",
                )
            )

            # Endgame spans (if specified). Each class span covers
            # ENDGAME_PLY_THRESHOLD consecutive plies starting at ply=30.
            if spec["endgame"] is None:
                continue
            span_start_ply = 30
            clocks_spec = spec.get("clocks")
            for class_int in spec["endgame"]:
                sig, imbalance = _CLASS_DEFAULT[class_int]
                # Build the clock series only for the FIRST span of each game
                # (that's where endgame entry lies — _extract_entry_clocks only
                # reads entry plies, and query_clock_stats_rows collapses
                # multi-span to the earliest span).
                clock_series: list[float | None] = [None] * ENDGAME_PLY_THRESHOLD
                if clocks_spec is not None and span_start_ply == 30:
                    user_ec, opp_ec = clocks_spec
                    clock_series = [
                        float(v)
                        for v in _clock_series_for_span(
                            span_start_ply, color, user_ec, opp_ec
                        )
                    ]

                for offset in range(ENDGAME_PLY_THRESHOLD):
                    session.add(
                        GamePosition(
                            game_id=game.id,
                            user_id=user_id,
                            ply=span_start_ply + offset,
                            full_hash=STARTING_POSITION_HASH + 10_000 + idx * 100 + offset,
                            white_hash=STARTING_POSITION_HASH + 20_000 + idx * 100 + offset,
                            black_hash=STARTING_POSITION_HASH + 30_000 + idx * 100 + offset,
                            piece_count=2,
                            material_count=1000,
                            material_signature=sig,
                            material_imbalance=imbalance,
                            endgame_class=class_int,
                            clock_seconds=clock_series[offset],
                        )
                    )
                span_start_ply += ENDGAME_PLY_THRESHOLD

        await session.commit()


@pytest_asyncio.fixture(scope="module")
async def seeded_user() -> SeededUser:
    """Register one user + commit the deterministic portfolio; return handle."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, email, auth_headers = await _register_and_login(client)
    await _seed_portfolio(user_id)
    return SeededUser(
        id=user_id,
        email=email,
        auth_headers=auth_headers,
        expected=dict(EXPECTED),
    )
