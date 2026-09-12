"""Compare our standalone detectors against cook.py (the AGPL oracle) on the fixtures.

Analysis-only, read-only, engine-free: no DB writes, no Stockfish calls. Reads the
committed CC0 fixture CSVs and the local lichess-puzzler clone only.

AGPL boundary: this script imports the local lichess-puzzler `tagger` clone BY PATH
at runtime, purely for comparison. Only prose, heuristics and constant *names* cross
the boundary into `app/services/tactic_detector.py` and its docstrings — cook.py is
neither vendored nor ported into this repository. See `forcing_line_gate.py` for the
project's full AGPL boundary comment. When the clone is absent (e.g. in CI, or on any
box other than the analysis machine), this script prints one line and exits 0 rather
than raising an import error (TAGFIX-08: "skip cleanly").

Usage:
    uv run python scripts/research/oracle_compare.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any

# Bootstrap project root so `app.*` / `tests.*` imports resolve when running as a script.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

# The local AGPL lichess-puzzler clone (analysis-only; not part of this repository).
# Skip cleanly when absent — TAGFIX-08 requires every scripts/research/*.py to be
# runnable (and exit 0) on a box that never cloned it.
_PUZZLER_CLONE = Path("/home/aimfeld/Projects/Python/lichess-puzzler/tagger")
if not _PUZZLER_CLONE.is_dir():
    print("lichess-puzzler clone not found — skipping (analysis-only script).")
    raise SystemExit(0)
sys.path.insert(0, str(_PUZZLER_CLONE))

import chess  # noqa: E402
import chess.pgn  # noqa: E402
import cook  # noqa: E402  # ty: ignore[unresolved-import] -- AGPL clone, present only on the analysis box
from model import Puzzle  # noqa: E402  # ty: ignore[unresolved-import] -- AGPL clone, path-imported above

from app.services import tactic_detector as td  # noqa: E402
from tests.scripts.tagger.conftest import PuzzleRow, _load_split, build_detector_board  # noqa: E402
from tests.scripts.tagger.motif_theme_map import MOTIF_TO_THEMES  # noqa: E402


def make_puzzle(row: PuzzleRow) -> Puzzle:
    board = chess.Board(row["pre_flaw_fen"])
    node = chess.pgn.Game.from_board(board)
    for uci in [row["first_move"]] + row["pv"].split():
        node = node.add_main_variation(chess.Move.from_uci(uci))
    return Puzzle(row["puzzle_id"], node.game(), 0)


def _fires(fn: Any, boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color) -> bool:
    return bool(fn(boards, moves, pov)[0])


def ours(boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color) -> dict[str, Any]:
    r: dict[str, Any] = {}
    r["fork"] = _fires(td.detect_fork, boards, moves, pov)
    r["hangingPiece"] = _fires(td.detect_hanging_piece, boards, moves, pov)
    r["pin"] = _fires(td.detect_pin, boards, moves, pov)
    r["skewer"] = _fires(td.detect_skewer, boards, moves, pov)
    r["doubleCheck"] = _fires(td.detect_double_check, boards, moves, pov)
    r["discoveredCheck"] = _fires(td.detect_discovered_check, boards, moves, pov)
    r["discoveredAttack"] = r["discoveredCheck"] or _fires(
        td.detect_discovered_attack, boards, moves, pov
    )
    r["trappedPiece"] = _fires(td.detect_trapped_piece, boards, moves, pov)
    r["backRankMate"] = _fires(td.detect_back_rank_mate, boards, moves, pov)
    r["anastasiaMate"] = _fires(td.detect_anastasia_mate, boards, moves, pov)
    r["hookMate"] = _fires(td.detect_hook_mate, boards, moves, pov)
    r["arabianMate"] = _fires(td.detect_arabian_mate, boards, moves, pov)
    bod = td.detect_boden_or_double_bishop_mate(boards, moves, pov)[0]
    r["bodenMate"] = bod == "boden-mate"
    r["doubleBishopMate"] = bod == "double-bishop-mate"
    r["dovetailMate"] = _fires(td.detect_dovetail_mate, boards, moves, pov)
    r["smotheredMate"] = _fires(td.detect_smothered_mate, boards, moves, pov)
    r["mate"] = boards[-1].is_checkmate()
    r["attraction"] = _fires(td.detect_attraction, boards, moves, pov)
    r["deflection"] = _fires(td.detect_deflection, boards, moves, pov)
    r["intermezzo"] = _fires(td.detect_intermezzo, boards, moves, pov)
    r["xRayAttack"] = _fires(td.detect_x_ray, boards, moves, pov)
    r["interference"] = _fires(td.detect_interference, boards, moves, pov)
    r["selfInterference14"] = _fires(td.detect_self_interference, boards, moves, pov)
    r["clearance"] = _fires(td.detect_clearance, boards, moves, pov)
    r["capturingDefender"] = _fires(td.detect_capturing_defender, boards, moves, pov)
    r["sacrifice"] = _fires(td.detect_sacrifice, boards, moves, pov)
    r["enPassant"] = _fires(td.detect_en_passant, boards, moves, pov)
    r["promotion"] = _fires(td.detect_promotion, boards, moves, pov) or _fires(
        td.detect_under_promotion, boards, moves, pov
    )
    r["underPromotion"] = _fires(td.detect_under_promotion, boards, moves, pov)
    return r


def _cook_safe(name: str, fn: Any, p: Puzzle, r: dict[str, Any]) -> None:
    try:
        r[name] = bool(fn(p))
    except Exception as e:  # cook asserts / KeyErrors on edge-case puzzles
        r[name] = f"ERR:{type(e).__name__}"


def cooks(p: Puzzle) -> dict[str, Any]:
    r: dict[str, Any] = {}
    _cook_safe("fork", cook.fork, p, r)
    _cook_safe("hangingPiece", cook.hanging_piece, p, r)
    _cook_safe("pin", lambda q: cook.pin_prevents_attack(q) or cook.pin_prevents_escape(q), p, r)
    _cook_safe("skewer", cook.skewer, p, r)
    _cook_safe("doubleCheck", cook.double_check, p, r)
    _cook_safe("discoveredCheck", cook.discovered_check, p, r)
    _cook_safe("discoveredAttack", cook.discovered_attack, p, r)
    _cook_safe("trappedPiece", cook.trapped_piece, p, r)
    _cook_safe("backRankMate", cook.back_rank_mate, p, r)
    _cook_safe("anastasiaMate", cook.anastasia_mate, p, r)
    _cook_safe("hookMate", cook.hook_mate, p, r)
    _cook_safe("arabianMate", cook.arabian_mate, p, r)
    _cook_safe("bodenMate", lambda q: cook.boden_or_double_bishop_mate(q) == "bodenMate", p, r)
    _cook_safe(
        "doubleBishopMate",
        lambda q: cook.boden_or_double_bishop_mate(q) == "doubleBishopMate",
        p,
        r,
    )
    _cook_safe("dovetailMate", cook.dovetail_mate, p, r)
    _cook_safe("smotheredMate", cook.smothered_mate, p, r)
    _cook_safe("mate", lambda q: cook.mate_in(q) is not None, p, r)
    _cook_safe("attraction", cook.attraction, p, r)
    _cook_safe("deflection", cook.deflection, p, r)
    _cook_safe("intermezzo", cook.intermezzo, p, r)
    _cook_safe("xRayAttack", cook.x_ray, p, r)
    _cook_safe("interference", lambda q: cook.self_interference(q) or cook.interference(q), p, r)
    _cook_safe("selfInterference14", cook.self_interference, p, r)
    _cook_safe("clearance", cook.clearance, p, r)
    _cook_safe("capturingDefender", cook.capturing_defender, p, r)
    _cook_safe("sacrifice", cook.sacrifice, p, r)
    _cook_safe("enPassant", cook.en_passant, p, r)
    _cook_safe("promotion", cook.promotion, p, r)
    _cook_safe("underPromotion", cook.under_promotion, p, r)
    return r


def cook_full(p: Puzzle) -> set[Any]:
    try:
        return set(cook.cook(p))
    except Exception as e:
        return {f"ERR:{type(e).__name__}"}


def main() -> None:
    rows = _load_split("train") + _load_split("test")
    agree: collections.Counter[tuple[str, bool, bool]] = collections.Counter()
    dis: dict[str, list[Any]] = collections.defaultdict(list)
    errs: collections.Counter[str] = collections.Counter()
    # label drift: cook recompute vs fixture label
    label_vs_cook: dict[str, collections.Counter[tuple[bool, bool]]] = collections.defaultdict(
        collections.Counter
    )
    # dispatch winner vs cook full tag set
    winner_vs_cook: dict[str, collections.Counter[tuple[bool, bool]]] = collections.defaultdict(
        collections.Counter
    )
    for row in rows:
        board = build_detector_board(row)
        boards, moves = td._parse_pv(board, row["pv"])
        pov = board.turn
        o = ours(boards, moves, pov)
        p = make_puzzle(row)
        c = cooks(p)
        themes = set(row["themes"])
        ctags = cook_full(p)
        for k in o:
            cv, ov = c[k], o[k]
            if isinstance(cv, str):
                errs[k] += 1
                continue
            key = (k, cv, ov)
            agree[key] += 1
            if cv != ov and len(dis[k]) < 8:
                dis[k].append(
                    (
                        row["puzzle_id"],
                        cv,
                        ov,
                        row["pre_flaw_fen"],
                        row["first_move"],
                        row["pv"],
                        sorted(themes),
                    )
                )
        for k in o:
            cv = c[k]
            if isinstance(cv, str) or k == "selfInterference14":
                continue
            has_label = k in themes
            label_vs_cook[k][(bool(cv), has_label)] += 1
        motif_int, _piece, _confidence, _depth = td.detect_tactic_motif(board, row["pv"])
        if motif_int is not None:
            m = td._INT_TO_MOTIF[motif_int]
            th = MOTIF_TO_THEMES.get(m, ())
            in_cook = any(t in ctags for t in th)
            in_label = any(t in themes for t in th)
            winner_vs_cook[m][(in_cook, in_label)] += 1
    print(f"rows={len(rows)}")
    print("\n=== STANDALONE cook-vs-ours agreement (cook_fires, ours_fires) counts ===")
    keys = sorted({k for (k, _, _) in agree})
    print(f"{'motif':22} {'both':>6} {'cookOnly':>9} {'oursOnly':>9} {'neither':>8} {'err':>5}")
    for k in keys:
        both = agree[(k, True, True)]
        co = agree[(k, True, False)]
        oo = agree[(k, False, True)]
        ne = agree[(k, False, False)]
        print(f"{k:22} {both:6} {co:9} {oo:9} {ne:8} {errs[k]:5}")
    print("\n=== cook recompute vs fixture label (cook_fires, label_present) ===")
    print(f"{'motif':22} {'both':>6} {'cookOnly':>9} {'labelOnly':>10} {'neither':>8}")
    for k in sorted(label_vs_cook):
        d = label_vs_cook[k]
        print(
            f"{k:22} {d[(True, True)]:6} {d[(True, False)]:9} {d[(False, True)]:10} {d[(False, False)]:8}"
        )
    print("\n=== dispatch winner: (in cook-recomputed tags, in fixture label) ===")
    for m in sorted(winner_vs_cook):
        d = winner_vs_cook[m]
        print(
            f"{m:22} cook&label={d[(True, True)]:5} cookOnly={d[(True, False)]:4} "
            f"labelOnly={d[(False, True)]:4} neither={d[(False, False)]:4}"
        )
    with open("oracle_disagreements.json", "w") as f:
        json.dump(dis, f, indent=1)


if __name__ == "__main__":
    main()
