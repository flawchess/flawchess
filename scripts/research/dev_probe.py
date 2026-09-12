"""Real-game probe: replay every tagged flaw in a target DB through the detector.

Read-only: performs ZERO DB writes — no commits, no UPDATE statements.
Engine-free: zero Stockfish calls, no chess engine instantiation of any kind.
Analysis-only diagnostic script (Phase 221 review, TAGFIX-08 relocation) — the join
template (game_flaws x game_positions at ply-1/ply/ply+1 x games for the PGN) is
reused verbatim in shape by scripts/research/sample_realgame_tags.py.

The --db target is REQUIRED so this never silently runs against the wrong
database. dev=localhost:5432, benchmark=localhost:5433, prod=localhost:15432
(via bin/prod_db_tunnel.sh).

Usage:
    uv run python scripts/research/dev_probe.py --db dev
    uv run python scripts/research/dev_probe.py --db dev --out /tmp/dev_probe_out.json
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import random
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import chess  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import db_url_for_target  # noqa: E402
from app.services import tactic_detector as td  # noqa: E402
from app.services.flaws_service import _recompute_fen_map  # noqa: E402

_INT_TO_MOTIF: Mapping[int, str] = td._INT_TO_MOTIF
_DEFAULT_OUT = "dev_probe_out.json"

SQL = """
SELECT f.user_id, f.game_id, f.ply, f.severity,
       f.allowed_tactic_motif am, f.allowed_tactic_depth ad,
       f.missed_tactic_motif mm, f.missed_tactic_depth md,
       f.allowed_pv_lines ab, f.missed_pv_lines mb,
       p0.move_san prev_san, p1.move_san flaw_san, p1.pv missed_pv, p2.pv allowed_pv,
       p0.eval_cp pre_cp, p1.eval_cp post_cp, p1.eval_mate post_mate,
       p2.eval_mate p2_mate, p2.eval_cp p2_cp,
       g.pgn, g.user_color
FROM game_flaws f
JOIN games g ON g.id = f.game_id
JOIN game_positions p1 ON p1.user_id=f.user_id AND p1.game_id=f.game_id AND p1.ply=f.ply
LEFT JOIN game_positions p0
    ON p0.user_id=f.user_id AND p0.game_id=f.game_id AND p0.ply=f.ply-1
LEFT JOIN game_positions p2
    ON p2.user_id=f.user_id AND p2.game_id=f.game_id AND p2.ply=f.ply+1
WHERE f.allowed_tactic_motif IS NOT NULL OR f.missed_tactic_motif IS NOT NULL
"""


def san_line(board: chess.Board, moves: list[chess.Move], mark: int) -> str:
    """Render `moves` as a SAN line, bracketing the move at index `mark`."""
    b = board.copy()
    out: list[str] = []
    for i, m in enumerate(moves):
        s = b.san(m)
        b.push(m)
        out.append(f"[{s}]" if i == mark else s)
    return " ".join(out)


def solver_eval(
    blob: list[dict[str, Any]] | None, idx: int | None, solver_white: bool
) -> tuple[str, int] | None:
    """Read the solver-perspective eval at blob index `idx` ("M", mate) or ("cp", cp)."""
    if not blob or idx is None or idx >= len(blob):
        return None
    node = blob[idx]
    if node.get("bm") is not None:
        return ("M", node["bm"] if solver_white else -node["bm"])
    if node.get("b") is not None:
        return ("cp", node["b"] if solver_white else -node["b"])
    return None


def _count_where(xs: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]) -> int:
    """Count records in `xs` matching `pred` (replaces an assigned lambda, E731)."""
    return sum(1 for x in xs if pred(x))


def _build_record(
    r: Any, fm: dict[int, str], orient: str, board_before: chess.Board
) -> dict[str, Any] | None:
    """Score one (flaw row, orientation) pair. Returns None when the row can't be scored
    (no motif tagged, no PV, illegal flaw-move replay, or the PV fails to parse)."""
    n = r["ply"]
    motif = r["am"] if orient == "allowed" else r["mm"]
    if motif is None:
        return None
    depth = r["ad"] if orient == "allowed" else r["md"]
    blob = r["ab"] if orient == "allowed" else r["mb"]
    if orient == "allowed":
        try:
            b0 = board_before.copy()
            b0.push(board_before.parse_san(r["flaw_san"]))
        except ValueError, chess.IllegalMoveError:
            return None
        pv = r["allowed_pv"]
    else:
        b0 = board_before
        pv = r["missed_pv"]
    if not pv:
        return None
    try:
        boards, moves = td._parse_pv(b0, pv)
    except ValueError:
        return None
    pov = b0.turn
    re = td.detect_tactic_motif(b0, pv)
    init = td._material_diff(boards[0], pov)
    traj = [td._material_diff(b, pov) - init for b in boards]
    last_pov_idx = len(moves) - 1 if (len(moves) - 1) % 2 == 0 else len(moves) - 2
    solver_white = pov == chess.WHITE
    fire_idx = (
        depth
        if depth is not None and depth % 2 == 0
        else (depth + 1 if depth is not None else None)
    )
    ev_fire = solver_eval(blob, fire_idx, solver_white)
    ev_end = solver_eval(blob, last_pov_idx, solver_white) if blob else None
    ev0 = solver_eval(blob, 0, solver_white) if blob else None
    # Missed hanging-piece recapture check (D-10): a recapture is not a
    # "hanging piece" — cook's recapture exclusion also applies here.
    recapture = _missed_recapture(r, fm, n, orient, motif, moves)
    return dict(
        game_id=r["game_id"],
        ply=n,
        orient=orient,
        motif=_INT_TO_MOTIF[motif],
        depth=depth,
        redetect=_INT_TO_MOTIF.get(re[0]) if re[0] else None,
        redepth=re[3],
        pv_len=len(moves),
        last_pov_idx=last_pov_idx,
        fires_last_pov=(depth == last_pov_idx),
        capped=(len(moves) >= 11),
        traj=traj,
        mat_end=traj[-1],
        mat_min=min(traj),
        mate_end=boards[-1].is_checkmate(),
        last_capture=boards[-2].piece_at(moves[-1].to_square) is not None,
        blob=blob is not None,
        ev0=ev0,
        ev_fire=ev_fire,
        ev_end=ev_end,
        pre_cp=r["pre_cp"],
        flaw_san=r["flaw_san"],
        prev_san=r["prev_san"],
        line=san_line(b0, moves, depth if depth is not None else -1),
        recapture=recapture,
        severity=r["severity"],
        user_color=str(r["user_color"]),
        fen0=b0.fen(),
    )


def _missed_recapture(
    r: Any, fm: dict[int, str], n: int, orient: str, motif: int, moves: list[chess.Move]
) -> bool | None:
    if not (orient == "missed" and _INT_TO_MOTIF[motif] == "hanging-piece" and r["prev_san"]):
        return None
    try:
        pre = chess.Board(fm[n - 1])
        pm = pre.parse_san(r["prev_san"])
        return pre.is_capture(pm) and pm.to_square == moves[0].to_square
    except ValueError, chess.IllegalMoveError:
        return None


async def main(db: str, out_path: str) -> None:
    engine = create_async_engine(db_url_for_target(db))
    async with engine.connect() as conn:
        rows = (await conn.execute(text(SQL))).mappings().all()
    print(f"target: {db}")
    print("tagged flaws:", len(rows))
    fen_cache: dict[int, dict[int, str]] = {}
    recs: list[dict[str, Any]] = []
    for r in rows:
        gid = r["game_id"]
        if gid not in fen_cache:
            fen_cache[gid] = _recompute_fen_map(r["pgn"])
        fm = fen_cache[gid]
        fen_before = fm.get(r["ply"])
        if not fen_before:
            continue
        board_before = chess.Board(fen_before)
        for orient in ("allowed", "missed"):
            rec = _build_record(r, fm, orient, board_before)
            if rec is not None:
                recs.append(rec)
    with open(out_path, "w") as fh:
        json.dump(recs, fh)
    # ---- summaries
    by: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for x in recs:
        by[(x["orient"], x["motif"])].append(x)
    print(
        f"\n{'orient':8}{'motif':20}{'n':>5}{'redetect≠':>10}{'depth≥4':>8}"
        f"{'lastpov':>8}{'capped':>7}{'odd_d':>6}{'noblob':>7}"
        f"{'mat_end<=-2':>12}{'ev_end<0':>9}"
    )
    for (o, m), xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n_rows = len(xs)
        ev_end_negative = _count_where(
            xs,
            lambda x: (
                x["ev_end"] is not None
                and (
                    (x["ev_end"][0] == "cp" and x["ev_end"][1] < 0)
                    or (x["ev_end"][0] == "M" and x["ev_end"][1] < 0)
                )
            ),
        )
        print(
            f"{o:8}{m:20}{n_rows:5}"
            f"{_count_where(xs, lambda x: x['redetect'] != x['motif']):10}"
            f"{_count_where(xs, lambda x: (x['depth'] or 0) >= 4):8}"
            f"{_count_where(xs, lambda x: x['fires_last_pov']):8}"
            f"{_count_where(xs, lambda x: x['capped']):7}"
            f"{_count_where(xs, lambda x: x['depth'] is not None and x['depth'] % 2 == 1):6}"
            f"{_count_where(xs, lambda x: not x['blob']):7}"
            f"{_count_where(xs, lambda x: x['mat_end'] <= -2):12}"
            f"{ev_end_negative:9}"
        )
    print(
        "\nmissed hanging-piece recapture cases:",
        sum(1 for x in recs if x["recapture"]),
        "of",
        sum(1 for x in recs if x["orient"] == "missed" and x["motif"] == "hanging-piece"),
    )
    random.seed(7)
    sample_keys: list[tuple[tuple[str, str], int]] = [
        (("allowed", "sacrifice"), 14),
        (("missed", "sacrifice"), 8),
        (("allowed", "clearance"), 12),
        (("missed", "clearance"), 6),
        (("allowed", "capturing-defender"), 8),
        (("allowed", "deflection"), 8),
        (("allowed", "attraction"), 6),
        (("allowed", "skewer"), 6),
        (("allowed", "trapped-piece"), 6),
    ]
    for key, k in sample_keys:
        xs = by.get(key, [])
        print(f"\n===== SAMPLE {key} (n={len(xs)})")
        for x in random.sample(xs, min(k, len(xs))):
            print(
                f"g{x['game_id']} ply{x['ply']} flaw={x['flaw_san']} d={x['depth']} "
                f"len={x['pv_len']} traj={x['traj']} ev0={x['ev0']} evF={x['ev_fire']} "
                f"evEnd={x['ev_end']} preCp={x['pre_cp']} mate_end={x['mate_end']}\n"
                f"   {x['line']}\n   fen0={x['fen0']}"
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target. dev=localhost:5432, benchmark=localhost:5433, "
        "prod=localhost:15432 (via bin/prod_db_tunnel.sh).",
    )
    parser.add_argument(
        "--out",
        default=_DEFAULT_OUT,
        help=f"Output JSON path for the raw diagnostic records (default: {_DEFAULT_OUT}).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    asyncio.run(main(_args.db, _args.out))
