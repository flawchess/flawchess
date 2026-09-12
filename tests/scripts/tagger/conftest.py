"""Shared fixtures for the tagger validation harness.

This harness is entirely offline: it reads the committed fixture CSVs
(fixtures/tagger/detector_fixture_train.csv and detector_fixture_test.csv) and
runs the detector against them. No database connection, no asyncio, no network.

Train/test split (anti-overfitting): the self-improvement loop and the CI floor
gate optimize/measure against the TRAIN set; the TEST set is held out for honest
validation (scored but never used to tune detectors or set floors). Both files are
produced by scripts/select_tagger_fixtures.py with a deterministic PuzzleId-hash
split, so a puzzle never leaks across the two sets.

CC0/AGPL boundary (SC#4, D-11): the puzzle data is CC0 / Public Domain
(database.lichess.org). The puzzle labels were produced by
lichess-puzzler/tagger/cook.py (AGPL-3.0). We use only the published CC0
dataset; cook.py is neither vendored nor ported here.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal, TypedDict

import chess
import pytest

Split = Literal["train", "test"]

# Paths to the committed fixture CSVs, relative to the project root.
_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "tagger"
_FIXTURE_PATHS: dict[Split, Path] = {
    "train": _FIXTURE_DIR / "detector_fixture_train.csv",
    "test": _FIXTURE_DIR / "detector_fixture_test.csv",
}


class PuzzleRow(TypedDict):
    """A single row from a committed fixture CSV."""

    puzzle_id: str
    fen: str  # board-after-flaw FEN (Moves[0] already applied)
    pre_flaw_fen: str  # published pre-blunder FEN (cook's game.board())
    first_move: str  # UCI string: the blunder that created the puzzle position
    pv: str  # space-joined UCI refutation moves (Moves[1:])
    themes: list[str]  # space-split theme names from the CSV Themes column
    rating: int


def _load_split(split: Split) -> list[PuzzleRow]:
    """Read a committed fixture CSV ('train' or 'test'). No DB, no network."""
    rows: list[PuzzleRow] = []
    with open(_FIXTURE_PATHS[split], newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                PuzzleRow(
                    puzzle_id=raw["PuzzleId"],
                    fen=raw["FEN"],
                    pre_flaw_fen=raw["PreFlawFEN"],
                    first_move=raw["FirstMove"],
                    pv=raw["PV"],
                    themes=raw["Themes"].split() if raw["Themes"] else [],
                    rating=int(raw["Rating"]),
                )
            )
    return rows


def build_detector_board(row: PuzzleRow) -> chess.Board:
    """Build the detector input board the SAME way production calls it.

    Production (flaws_service "allowed" pass) builds the board as board_before.copy()
    then push(flaw_move), so the flaw move sits on the board's move stack. The detector's
    cook-faithful predicates (hanging-piece recapture exclusion, first-move intermezzo)
    read that flaw move from boards[0].move_stack. Rebuilding from the pre-flaw FEN + the
    flaw move reproduces that exact board (position AND one-move stack), so the gate verifies
    the detector identically to production rather than on a bare, stackless FEN.

    Falls back to the post-flaw FEN (stackless) if the pre-flaw reconstruction is unavailable
    or illegal — matching production's "missed" pass, which passes a stackless board.
    """
    pre = row["pre_flaw_fen"]
    first_move = row["first_move"]
    if pre and first_move:
        try:
            board = chess.Board(pre)
            board.push(chess.Move.from_uci(first_move))
            return board
        except ValueError, chess.IllegalMoveError, AssertionError:
            pass
    return chess.Board(row["fen"])


def _load_fixture(split: Split = "train") -> list[PuzzleRow]:
    """Back-compat loader. Defaults to the TRAIN set (the optimization set)."""
    return _load_split(split)


@pytest.fixture(scope="session")
def detector_fixture_train() -> list[PuzzleRow]:
    """Session-scoped TRAIN fixture: the floor-gated optimization set."""
    return _load_split("train")


@pytest.fixture(scope="session")
def detector_fixture_test() -> list[PuzzleRow]:
    """Session-scoped held-out TEST fixture: scored for validation, not gated."""
    return _load_split("test")


# ---------------------------------------------------------------------------
# Real-game fixture (TAGFIX-07 / D-13) — a hand-labelled sample of prod tags,
# sampled BEFORE any detector/gate predicate in Phase 221 changed, so the
# before/after real-share comparison is scored on identical inputs. Committed at
# fixtures/tagger/realgame_tags.csv. See scripts/research/sample_realgame_tags.py
# for the sampler that produced it and REALGAME_CSV_HEADER for the column contract.
# ---------------------------------------------------------------------------

RealGameLabel = Literal["real", "incidental", "wrong"]

_REALGAME_PATH = _FIXTURE_DIR / "realgame_tags.csv"

# T-221-01: the committed real-game CSV must never carry a user-identifying column.
# The schema test asserts none of these names appear in the CSV header.
REALGAME_USER_IDENTITY_DENYLIST: frozenset[str] = frozenset(
    {"user_id", "username", "player", "player_name", "account_handle", "email"}
)


class RealGameRow(TypedDict):
    """A single row from the committed fixtures/tagger/realgame_tags.csv (TAGFIX-07)."""

    row_id: str  # stable zero-padded ordinal, unique within the file
    game_id: int
    ply: int  # the flaw ply (game_flaws.ply)
    orientation: Literal["allowed", "missed"]
    # Full FEN before push_move_uci: fen_map[ply] for "allowed", fen_map[ply-1] for
    # "missed" — the SAME pre-flaw position production reads (never game_flaws.fen,
    # which is piece-placement only).
    pre_flaw_fen: str
    push_move_uci: str  # the flaw move (allowed) or the opponent's previous move (missed)
    pv: str  # space-joined UCI PV read the same way the detector reads it
    san_line: str  # human-labelling aid: SAN rendering with the firing move bracketed
    motif: int  # the stored TacticMotifInt this row was tagged with
    motif_name: str  # _INT_TO_MOTIF[motif], frozen at sample time
    depth: int | None  # stored tactic depth; None only for a malformed/legacy row
    solver_color: Literal["white", "black"]
    eval_at_firing: str  # frozen solver-perspective eval ("M4" / "-M4" / a cp int / "none")
    label: RealGameLabel | None  # None only while unlabelled (task 2 fills every row)
    rationale: str  # one-clause justification for the label; "" while unlabelled
    # Display-only: opens the pre-flaw position on a lichess analysis board for the
    # D-13 operator review (the sample spans all prod users, so an in-app link only
    # resolves for rows the reviewer owns). Never read by the board build or any
    # measurement.
    board_url: str
    # Display-only: opens the tactic in the app on its FORK ply (flaw ply for
    # "allowed", ply-1 for "missed"). The app additionally hides a stored tag whose
    # pre-move position was already decisively lost, or whose confidence is under 70,
    # so a row can be correctly tagged here and still show no chip there.
    analysis_url: str


def _load_realgame() -> list[RealGameRow]:
    """Read the committed real-game fixture CSV. No DB, no network (D-13).

    A label outside {"real", "incidental", "wrong", ""} raises ValueError naming the
    offending row_id — never a bare str passthrough (CLAUDE.md: no bare `str` for a
    fixed set of values). An empty label/rationale means the row is not yet labelled.
    """
    rows: list[RealGameRow] = []
    with open(_REALGAME_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            label_raw = raw["label"]
            if label_raw not in ("", "real", "incidental", "wrong"):
                raise ValueError(
                    f"realgame_tags.csv row {raw['row_id']!r} has an invalid label "
                    f"{label_raw!r} — must be one of real/incidental/wrong, or empty "
                    "while unlabelled"
                )
            depth_raw = raw["depth"]
            rows.append(
                RealGameRow(
                    row_id=raw["row_id"],
                    game_id=int(raw["game_id"]),
                    ply=int(raw["ply"]),
                    orientation=_require_orientation(raw["row_id"], raw["orientation"]),
                    pre_flaw_fen=raw["pre_flaw_fen"],
                    push_move_uci=raw["push_move_uci"],
                    pv=raw["pv"],
                    san_line=raw["san_line"],
                    motif=int(raw["motif"]),
                    motif_name=raw["motif_name"],
                    depth=int(depth_raw) if depth_raw else None,
                    solver_color=_require_solver_color(raw["row_id"], raw["solver_color"]),
                    eval_at_firing=raw["eval_at_firing"],
                    label=label_raw or None,
                    rationale=raw["rationale"],
                    board_url=raw["board_url"],
                    analysis_url=raw["analysis_url"],
                )
            )
    return rows


def _require_orientation(row_id: str, value: str) -> Literal["allowed", "missed"]:
    if value not in ("allowed", "missed"):
        raise ValueError(f"realgame_tags.csv row {row_id!r} has invalid orientation {value!r}")
    return value


def _require_solver_color(row_id: str, value: str) -> Literal["white", "black"]:
    if value not in ("white", "black"):
        raise ValueError(f"realgame_tags.csv row {row_id!r} has invalid solver_color {value!r}")
    return value


def build_realgame_board(row: RealGameRow) -> chess.Board:
    """Build the detector input board the SAME way production builds it post-D-09.

    BOTH orientations push a move onto the board here: the flaw move for "allowed"
    (matching build_detector_board's allowed pass), and the opponent's PRECEDING
    move for "missed" — after D-09 the missed pass's board_before is built from
    fen_map[n-1] plus the previous move (positions[n-1].move_san), giving it a
    one-move stack exactly like the allowed pass. See flaws_service.py's TAGFIX-06
    board-construction site for the production rule this mirrors.

    Falls back to a stackless board (pre_flaw_fen only, no push) if the push is
    illegal or malformed — defensive only; every committed row is already tagged
    from a board that replayed cleanly in production.
    """
    try:
        board = chess.Board(row["pre_flaw_fen"])
        board.push(chess.Move.from_uci(row["push_move_uci"]))
        return board
    except ValueError, chess.IllegalMoveError, AssertionError:
        return chess.Board(row["pre_flaw_fen"])


@pytest.fixture(scope="session")
def realgame_fixture() -> list[RealGameRow]:
    """Session-scoped real-game fixture (TAGFIX-07 / D-13)."""
    return _load_realgame()
