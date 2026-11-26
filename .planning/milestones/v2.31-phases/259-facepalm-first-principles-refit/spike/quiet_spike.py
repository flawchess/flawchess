"""Phase 259 discuss spike (throwaway, gitignored): quiet-point material for the labelled rows.

For every row of the committed features TSV, re-read the game and the stored lines from prod
(read-only), then write three features TSVs in the committed schema:

- ``baseline-today.tsv``: the shipped material rule on today's lines (the fair comparison);
- ``quiet-any.tsv``: each depth extended over every following capture until a quiet move;
- ``quiet-same.tsv``: each depth extended only over recaptures on the same square.

Plus ``reply-prob.tsv``: Maia's probability of the engine's best reply (first token of the
stored refutation line) at the blunderer's pinned Elo.

Run from the worktree root:
    (run with the working directory at a checkout that has the prod config; outputs went to temp/facepalm-259/)
"""

from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import db_url_for_target  # noqa: E402
from app.services import line_material as lm  # noqa: E402
from app.services import maia_engine  # noqa: E402
from app.services.maia_flaw_scoring import replay_flaw_boards  # noqa: E402
from scripts.blunder_check import facepalm_features as ff  # noqa: E402
from scripts.blunder_check.sample import make_readonly_engine  # noqa: E402

FEATURES = ROOT / "reports/blunder-check/facepalm-features-2026-11-16.tsv"
OUT = Path(__file__).resolve().parent
DEPTHS = lm.LINE_MATERIAL_DEPTHS


def _apply(loss: int, quiet_sq: int | None, step: lm._Step) -> tuple[int, int | None]:
    """One step of the shipped counting rule (`_net_loss` loop body)."""
    if step.opponent_move:
        if step.victim_value and step.to_square != quiet_sq:
            loss += step.victim_value
        return loss, None
    loss -= step.victim_value
    return loss, (step.to_square if step.victim_value == 0 else None)


def _chains(steps: list[lm._Step], j: int, same_square: bool) -> bool:
    """Whether step j continues the capture sequence after step j - 1."""
    if j >= len(steps) or steps[j].victim_value == 0:
        return False
    if not same_square:
        return True
    prev = steps[j - 1]
    return prev.victim_value > 0 and prev.to_square == steps[j].to_square


def quiet_loss(
    first_victim: int,
    steps: list[lm._Step],
    depth: int,
    end_board: chess.Board,
    same_square: bool,
) -> int | None:
    """Net loss at `depth`, read at the first quiet point at or after it."""
    if not steps:
        return None
    mated = any(s.blunderer_mated or s.opponent_mated for s in steps[:depth])
    last = steps[-1]
    ends_on_capture = bool(last.victim_value) and not (last.blunderer_mated or last.opponent_mated)
    if len(steps) < depth and not mated and not ends_on_capture:
        return None
    loss, quiet_sq = -first_victim, None
    j = 0
    while j < min(depth, len(steps)):
        loss, quiet_sq = _apply(loss, quiet_sq, steps[j])
        j += 1
    while _chains(steps, j, same_square):
        loss, quiet_sq = _apply(loss, quiet_sq, steps[j])
        j += 1
    if j == len(steps) and ends_on_capture:
        # The line stops inside an exchange: settle it with a static exchange on that square.
        swing = lm._best_recapture(end_board, last.to_square)
        loss += -swing if last.opponent_move else swing
    return loss


def quiet_array(
    pre_board: chess.Board, first_uci: str | None, rest: list[str], same_square: bool
) -> list[int | None]:
    if not first_uci or not rest:
        return [None] * len(DEPTHS)
    first = lm._parse_move(first_uci)
    if first is None or first not in pre_board.legal_moves:
        return [None] * len(DEPTHS)
    board = pre_board.copy(stack=False)
    blunderer = board.turn
    first_victim = lm._victim_value(board, first)
    board.push(first)
    if board.is_checkmate():
        return [first_victim] * len(DEPTHS)
    steps, end_board = lm._replay_line(board, rest, blunderer)
    out: list[int | None] = []
    for depth in DEPTHS:
        loss = quiet_loss(first_victim, steps, depth, end_board, same_square)
        out.append(None if loss is None else -loss)
    return out


def _cells(values: list[int | None]) -> list[str]:
    return ["" if v is None else str(v) for v in values]


async def main() -> None:
    with FEATURES.open() as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = list(reader.fieldnames or [])
        records = list(reader)
    await maia_engine.start_maia(intra_op_num_threads=4)
    assert maia_engine.is_maia_available(), "Maia unavailable"
    outs = {name: [] for name in ("baseline-today", "quiet-any", "quiet-same")}
    reply_rows: list[list[str]] = []
    changed_lines = 0
    missing: list[str] = []
    engine = make_readonly_engine(db_url_for_target("prod"))
    try:
        async with engine.connect() as conn:
            for rec in records:
                game_id, ply = int(rec["game_id"]), int(rec["ply"])
                inputs = await ff.read_game_inputs(conn, game_id, ply)
                if inputs is None:
                    missing.append(rec["n"])
                    continue
                boards, _ = replay_flaw_boards(inputs.pgn, [ply])
                if ply not in boards:
                    missing.append(rec["n"])
                    continue
                pre_board, played_uci = boards[ply]
                pv_tokens = inputs.pv.split(" ") if inputs.pv else []
                best_tokens = inputs.best_pv.split(" ") if inputs.best_pv else []
                # Shipped rule on today's lines.
                facts = lm.line_facts(pre_board, played_uci, inputs.pv)
                best_facts = lm.best_line_facts(pre_board, inputs.best_pv or inputs.best_move)
                base = dict(rec)
                for col, v in zip(ff.PLAYED_MAT_COLUMNS, _cells(facts.material_array())):
                    base[col] = v
                for col, v in zip(ff.BEST_MAT_COLUMNS, _cells(best_facts.material_array())):
                    base[col] = v
                base["line_mate_ply"] = "" if facts.mate_ply is None else str(facts.mate_ply)
                base["best_mate_ply"] = (
                    "" if best_facts.opponent_mate_ply is None else str(best_facts.opponent_mate_ply)
                )
                if any(base[c] != rec[c] for c in (*ff.PLAYED_MAT_COLUMNS, *ff.BEST_MAT_COLUMNS)):
                    changed_lines += 1
                outs["baseline-today"].append(base)
                for name, same in (("quiet-any", False), ("quiet-same", True)):
                    row = dict(base)
                    played = quiet_array(pre_board, played_uci, pv_tokens, same)
                    best = quiet_array(
                        pre_board, best_tokens[0] if best_tokens else None, best_tokens[1:], same
                    )
                    for col, v in zip(ff.PLAYED_MAT_COLUMNS, _cells(played)):
                        row[col] = v
                    for col, v in zip(ff.BEST_MAT_COLUMNS, _cells(best)):
                        row[col] = v
                    outs[name].append(row)
                # Best-reply probability at the blunderer's pinned Elo.
                elo = ff._mover_elo(inputs, pre_board)
                prob = ""
                if elo is not None and pv_tokens:
                    post = pre_board.copy(stack=False)
                    post.push(chess.Move.from_uci(played_uci))
                    policy = maia_engine.full_policy(post.fen(), elo)
                    if policy and pv_tokens[0] in policy:
                        prob = f"{policy[pv_tokens[0]]:.6g}"
                reply_rows.append([rec["n"], str(game_id), str(ply), pv_tokens[0] if pv_tokens else "", prob])
    finally:
        await engine.dispose()
    for name, rows in outs.items():
        with (OUT / f"{name}.tsv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    with (OUT / "reply-prob.tsv").open("w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["n", "game_id", "ply", "reply_uci", "reply_prob"])
        writer.writerows(reply_rows)
    print(f"rows {len(records)}, missing {missing}, material differs from the committed TSV on {changed_lines}")


if __name__ == "__main__":
    asyncio.run(main())
