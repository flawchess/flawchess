"""Sample and freeze a hand-labelled real-game tactic-tag gate (TAGFIX-07 / D-13).

Read-only: performs ZERO writes — no commit, no UPDATE, no INSERT, no DDL. One
`AsyncSession`-equivalent connection, sequential queries (never `asyncio.gather` on
a single session/connection).

This is the D-13 freeze point: it draws a stratified sample of ~150 already-tagged
`game_flaws` rows (motif x orientation) from a target database, BEFORE any detector
or gate predicate in this phase changes, so the before/after real-share comparison
is scored on IDENTICAL inputs. Once a detector predicate changes, the population of
tagged rows changes and this exact sample can never be re-drawn — see the module
docstring of `tests/scripts/tagger/precision_floors.py` for how the resulting
`REALGAME_REAL_SHARE_FLOOR` floors are seeded from this file's measurement.

Stratification: `OVERSAMPLED_MOTIF_INTS` (sacrifice, clearance, intermezzo, x-ray —
the four motifs this phase's fixes target) get `PER_STRATUM_OVERSAMPLED` rows per
(motif, orientation) stratum; `CONTROL_MOTIF_INTS` (fork, hanging-piece, mate — the
already-high-precision motifs a regression should be visible on) and every other
tagged motif get the smaller `PER_STRATUM_CONTROL` rate. Strata are ranked by
`md5(game_id::text || ply::text)`, NEVER `random()`: the md5 digest is a stable
SAMPLING hash (not a security primitive — it is never used for anything
cryptographic), so a re-run of this exact query against a growing table returns the
same rows rather than re-windowing them (see memory note `benchmark-db-not-static`).

The --db target is REQUIRED so this never silently runs against the wrong
database. dev=localhost:5432, benchmark=localhost:5433, prod=localhost:15432
(via bin/prod_db_tunnel.sh). This script performs ZERO writes regardless of target.

Usage:
    uv run python scripts/research/sample_realgame_tags.py --db dev --limit 5
    uv run python scripts/research/sample_realgame_tags.py --db prod \
        --out fixtures/tagger/realgame_tags.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path
from typing import Any, Literal

# Bootstrap project root so `app.*` / `scripts.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import chess  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import db_url_for_target  # noqa: E402
from app.services import tactic_detector as td  # noqa: E402
from app.services.flaws_service import _recompute_fen_map, _solver_color_for  # noqa: E402
from scripts.research.dev_probe import san_line  # noqa: E402

# ---------------------------------------------------------------------------
# Sampling constants (all named, per CLAUDE.md — no magic numbers)
# ---------------------------------------------------------------------------

# Column order committed to fixtures/tagger/realgame_tags.csv. Positive-equality
# checked by tests/scripts/tagger/test_detector_precision.py::test_realgame_fixture_schema
# — a column that is not in this constant can never silently slip into the fixture.
# Base URL for the display-only `board_url` column (D-13 operator review aid). The
# sample is stratified across ALL prod users, so a flawchess.com/analysis link only
# resolves for the handful of rows the reviewer happens to own — a lichess analysis
# board built from the pre-flaw FEN opens every row, for any reviewer, with no account.
BOARD_URL_BASE: str = "https://lichess.org/analysis/standard"

# Base URL for the display-only `analysis_url` column. The app opens a tactic on the
# FORK ply, which is the flaw ply for "allowed" but ply-1 for "missed" (mirrors
# frontend/src/lib/analysisTactics.ts::forkPlyForOrientation) — linking to the raw
# flaw ply lands one ply late on every missed row and shows no chip.
ANALYSIS_URL_BASE: str = "https://flawchess.com/analysis"

REALGAME_CSV_HEADER: list[str] = [
    "row_id",
    "game_id",
    "ply",
    "orientation",
    "pre_flaw_fen",
    "push_move_uci",
    "pv",
    "san_line",
    "motif",
    "motif_name",
    "depth",
    "solver_color",
    "eval_at_firing",
    "label",
    "rationale",
    "board_url",
    "analysis_url",
]

# Target total row count (D-13: "~150 prod tags"). Not a hard cap — the achieved
# count is printed and may differ slightly depending on live per-stratum row counts;
# the plan's acceptance bar is 120-200 rows.
TARGET_ROW_COUNT: int = 150

# The four motifs this phase's detector/gate fixes are about (D-05/D-07 sacrifice +
# clearance persistence/strengthening, D-01 winning floor hitting intermezzo/x-ray
# hardest per the dev acceptance-instrument table). Oversampled so their real-share
# floor has enough surviving rows to be meaningful (>= REALGAME_MIN_ROWS_FOR_FLOOR).
OVERSAMPLED_MOTIF_INTS: frozenset[int] = frozenset(
    {
        td.TacticMotifInt.SACRIFICE,
        td.TacticMotifInt.CLEARANCE,
        td.TacticMotifInt.INTERMEZZO,
        td.TacticMotifInt.X_RAY,
    }
)

# The already-high-precision motifs named as the "thin control" (D-13) — a
# regression on these should be visible in the printed real-game table even though
# they are not this phase's target. Every OTHER tagged motif (not in
# OVERSAMPLED_MOTIF_INTS) gets the SAME control rate as this named set (see
# PER_STRATUM_CONTROL below) — this constant exists for documentation, not because
# it is treated differently from the unnamed remainder.
CONTROL_MOTIF_INTS: frozenset[int] = frozenset(
    {
        td.TacticMotifInt.FORK,
        td.TacticMotifInt.HANGING_PIECE,
        td.TacticMotifInt.MATE,
    }
)

# Rows sampled per (motif, orientation) stratum for the four oversampled motifs.
# 4 motifs x 2 orientations x 8 rows = 64 rows.
PER_STRATUM_OVERSAMPLED: int = 8

# Rows sampled per (motif, orientation) stratum for every other tagged motif
# (CONTROL_MOTIF_INTS plus every remaining motif). 25 motifs x 2 orientations x 2
# rows = ~100 rows. Combined with the 64 oversampled rows this lands at ~148,
# inside the plan's 120-200 acceptance bar and close to TARGET_ROW_COUNT.
PER_STRATUM_CONTROL: int = 2

_INT_TO_MOTIF = td._INT_TO_MOTIF


def _per_stratum_cap(motif_int: int) -> int:
    """Rows to keep for one (motif, orientation) stratum (D-13 stratification)."""
    return PER_STRATUM_OVERSAMPLED if motif_int in OVERSAMPLED_MOTIF_INTS else PER_STRATUM_CONTROL


# The stratified sample query. Ranks BOTH orientations' strata in one pass so the
# games/game_positions/game_flaws join runs once. Ranking uses md5(game_id||ply) —
# a sampling hash, never a security primitive, and never random() (reproducibility;
# see memory note `benchmark-db-not-static` on why a rank window over a growing
# table must use a stable ORDER BY). Only the columns the detector/CSV need are
# projected: no user_id, username or player name crosses into the output (T-221-01).
_SAMPLE_SQL = """
WITH ranked AS (
    SELECT
        f.game_id, f.ply,
        f.allowed_tactic_motif am, f.allowed_tactic_depth ad, f.allowed_pv_lines ab,
        f.missed_tactic_motif mm, f.missed_tactic_depth md, f.missed_pv_lines mb,
        p1.move_san flaw_san, p1.pv missed_pv,
        p0.move_san prev_san,
        p2.pv allowed_pv,
        g.pgn,
        ROW_NUMBER() OVER (
            PARTITION BY f.allowed_tactic_motif
            ORDER BY md5(f.game_id::text || f.ply::text)
        ) AS rn_allowed,
        ROW_NUMBER() OVER (
            PARTITION BY f.missed_tactic_motif
            ORDER BY md5(f.game_id::text || f.ply::text)
        ) AS rn_missed
    FROM game_flaws f
    JOIN games g ON g.id = f.game_id
    JOIN game_positions p1
        ON p1.user_id = f.user_id AND p1.game_id = f.game_id AND p1.ply = f.ply
    LEFT JOIN game_positions p0
        ON p0.user_id = f.user_id AND p0.game_id = f.game_id AND p0.ply = f.ply - 1
    LEFT JOIN game_positions p2
        ON p2.user_id = f.user_id AND p2.game_id = f.game_id AND p2.ply = f.ply + 1
    WHERE f.allowed_tactic_motif IS NOT NULL OR f.missed_tactic_motif IS NOT NULL
)
SELECT * FROM ranked
WHERE (am IS NOT NULL AND rn_allowed <= :max_cap)
   OR (mm IS NOT NULL AND rn_missed <= :max_cap)
"""


def _eval_at_firing_str(
    blob: list[dict[str, Any]] | None, depth: int | None, solver_white: bool
) -> str:
    """Frozen solver-perspective eval at the firing node — SAME rule as the phase's
    prod acceptance instrument (RESEARCH.md 'The acceptance instrument'): round an
    odd firing depth UP to the next solver node, read `bm` (mate) before `b` (cp).

    Returns "M<n>" / "-M<n>" for a mate, a signed cp integer as a string, or the
    literal "none" when the node is unreadable (no blob, no depth, or short blob).
    """
    if not blob or depth is None:
        return "none"
    idx = depth + (depth % 2)
    if idx < 0 or idx >= len(blob):
        return "none"
    node = blob[idx]
    bm = node.get("bm")
    if bm is not None:
        val = bm if solver_white else -bm
        return f"M{val}" if val >= 0 else f"-M{-val}"
    b = node.get("b")
    if b is None:
        return "none"
    val = b if solver_white else -b
    return str(val)


def _build_row(
    row_id: int,
    r: Any,
    fen_map: dict[int, str],
    orientation: Literal["allowed", "missed"],
) -> dict[str, str] | None:
    """Build one CSV row for one (flaw row, orientation) pair, or None if the flaw
    move / PV cannot be replayed (illegal SAN, missing PV, or an unparseable PV)."""
    n = r["ply"]
    motif = r["am"] if orientation == "allowed" else r["mm"]
    if motif is None:
        return None
    depth = r["ad"] if orientation == "allowed" else r["md"]
    blob = r["ab"] if orientation == "allowed" else r["mb"]
    pv = r["allowed_pv"] if orientation == "allowed" else r["missed_pv"]
    if not pv:
        return None

    pre_flaw_ply = n if orientation == "allowed" else n - 1
    pre_flaw_fen = fen_map.get(pre_flaw_ply, "")
    push_san = r["flaw_san"] if orientation == "allowed" else r["prev_san"]
    if not pre_flaw_fen or not push_san:
        return None
    try:
        board_before = chess.Board(pre_flaw_fen)
        push_move = board_before.parse_san(push_san)
        board_before.push(push_move)
    except ValueError, chess.IllegalMoveError:
        return None

    try:
        _boards, moves = td._parse_pv(board_before, pv)
    except ValueError:
        return None

    solver_color = _solver_color_for(n, orientation)
    solver_white = solver_color == "white"
    line = san_line(board_before, moves, depth if depth is not None else -1)

    return {
        "row_id": f"{row_id:04d}",
        "game_id": str(r["game_id"]),
        "ply": str(n),
        "orientation": orientation,
        "pre_flaw_fen": pre_flaw_fen,
        "push_move_uci": push_move.uci(),
        "pv": pv,
        "san_line": line,
        "motif": str(motif),
        "motif_name": _INT_TO_MOTIF[motif],
        "depth": "" if depth is None else str(depth),
        "solver_color": solver_color,
        "eval_at_firing": _eval_at_firing_str(blob, depth, solver_white),
        "label": "",
        "rationale": "",
        # Display-only convenience for the D-13 operator review: opens the pre-flaw
        # position on a lichess analysis board. Derived purely from pre_flaw_fen — it
        # is never read by the detector, the loader's board build, or any measurement.
        "board_url": f"{BOARD_URL_BASE}/{pre_flaw_fen.replace(' ', '_')}",
        "analysis_url": (
            f"{ANALYSIS_URL_BASE}?game_id={r['game_id']}"
            f"&ply={n if orientation == 'allowed' else n - 1}"
        ),
    }


def _write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    """Write `rows` as the committed fixture CSV. Injectable `out_path` so a test or
    a re-run targets a temp path and never clobbers the frozen fixture (D-13)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REALGAME_CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


async def _sample(db: str, out_path: Path, limit: int | None) -> None:
    url = db_url_for_target(db)
    resolved = make_url(url)
    # T-221-02 mitigation: print the resolved target BEFORE the first query, so a
    # wrong --db choice is visible immediately (Phase-220 T-220-02 precedent).
    print(f"target: {db} -> {resolved.host}:{resolved.port}/{resolved.database}")

    engine = create_async_engine(url)
    max_cap = max(PER_STRATUM_OVERSAMPLED, PER_STRATUM_CONTROL)
    async with engine.connect() as conn:
        result = await conn.execute(text(_SAMPLE_SQL), {"max_cap": max_cap})
        rows = result.mappings().all()

    fen_cache: dict[int, dict[int, str]] = {}
    csv_rows: list[dict[str, str]] = []
    for r in rows:
        gid = r["game_id"]
        if gid not in fen_cache:
            fen_cache[gid] = _recompute_fen_map(r["pgn"])
        fen_map = fen_cache[gid]
        for orientation, motif_key, rn_key in (
            ("allowed", "am", "rn_allowed"),
            ("missed", "mm", "rn_missed"),
        ):
            motif = r[motif_key]
            if motif is None or r[rn_key] > _per_stratum_cap(motif):
                continue
            built = _build_row(len(csv_rows) + 1, r, fen_map, orientation)
            if built is None:
                continue
            csv_rows.append(built)

    if limit is not None:
        csv_rows = csv_rows[:limit]

    _write_csv(csv_rows, out_path)

    # Report strata AFTER any --limit truncation, so the printed summary matches
    # what was actually written to out_path.
    per_stratum_seen: dict[tuple[str, str], int] = {}
    for written in csv_rows:
        key = (written["orientation"], written["motif_name"])
        per_stratum_seen[key] = per_stratum_seen.get(key, 0) + 1

    print(f"achieved rows: {len(csv_rows)} (target ~{TARGET_ROW_COUNT})")
    print(f"strata sampled: {len(per_stratum_seen)}")
    for (orientation, motif_name), count in sorted(per_stratum_seen.items()):
        print(f"  {orientation:8}{motif_name:20}{count:4}")
    print(f"wrote {out_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target. dev=localhost:5432, benchmark=localhost:5433, "
        "prod=localhost:15432 (via bin/prod_db_tunnel.sh). Read-only regardless.",
    )
    parser.add_argument(
        "--out",
        default="fixtures/tagger/realgame_tags.csv",
        help="Output CSV path (default: the committed fixture path).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap on total sampled rows (for a quick smoke run). Omit for the full sample.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    asyncio.run(_sample(_args.db, Path(_args.out), _args.limit))
