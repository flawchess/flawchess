"""Build the features table the facepalm score is fitted on (Phase 250 D-01, D-02; Phase 254 D-16).

One row per labelled blunder (plus optional unlabelled extra rows such as Window 14):
the Maia played probability stored on game_flaws, the reply spread of the FULL Maia policy
one ply after the blunder at the blunderer's pinned Elo, the line material facts of the
stored refutation line (the played line) and, from Phase 254, the facts of the stored best
line plus the two pre-blunder Maia inputs (the best move's probability and the reply spread
of the position before the blunder, both from ONE pre-blunder policy call). Every value is
computed with the app's own functions (``replay_flaw_boards``, ``pinned_elo_for_mover``,
``reply_spread``, ``quiet_line_facts``, ``quiet_best_line_facts``), so the fit sees exactly what
the go-forward hook and the backfill will store.

The table is committed under ``reports/blunder-check/`` and ``fit_facepalm.py`` re-runs from
it alone (no cache, no DB, no Maia).

Usage (database access is read-only, see ``make_readonly_engine``)::

    uv run --group maia-inference python scripts/blunder_check/facepalm_features.py \
        --db prod --labels reports/blunder-check/facepalm-labels.tsv \
        --pv-cache temp/blunder-check \
        --extra 2099808:23 --out <features.tsv>

Phase 259 appends QUIET_FEATURE_COLUMNS (reply probability, loss / missed, raw lines);
``--skip-missing`` lists label rows whose game is gone instead of exiting 5. The committed tables
written before the drop release also carry the nine per-depth material slots of each line and the
shipped rule's loss / missed pair as history (the shipped rule is gone, so this
tool no longer writes them; the fit tool treats the shipped columns as optional).

``--labels`` may be given more than once (the rows of every file, in argument order, then the
``--extra`` rows). The best line always comes from the database (``game_positions.pv`` at the
flaw ply); ``--pv-cache`` only ever covered the refutation line.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, cast

import chess
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.schemas.normalization import Platform, TimeControlBucket  # noqa: E402
from app.services import maia_engine  # noqa: E402
from app.services.best_move_candidates import pinned_elo_for_mover  # noqa: E402
from app.services.facepalm_inputs import (  # noqa: E402
    MaterialInputs,
    material_inputs_from_facts,
)
from app.services.facepalm_score import loss_feature  # noqa: E402
from app.services.line_material import (  # noqa: E402
    LineFacts,
    quiet_best_line_facts,
    quiet_line_facts,
)
from app.services.maia_flaw_scoring import replay_flaw_boards  # noqa: E402
from app.services.maia_flaw_stats import reply_spread  # noqa: E402
from app.services.normalization import is_correspondence_time_control  # noqa: E402
from scripts.blunder_check.sample import make_readonly_engine  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

PvSource = Literal["cache", "cache_none", "db", "db_none"]

# The facts schema (Phase 254), the leading columns of the scalar table below.
FACTS_FEATURE_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "game_id",
    "ply",
    "label",
    "pinned_elo",
    "played_prob",
    "reply_spread",
    "best_prob",
    "pre_spread",
    "line_mate_ply",
    "best_mate_ply",
    "best_uci",
    "pv_source",
    "pv_plies",
    "best_pv_plies",
    "note",
)

# Phase 259 D-07, D-12: appended after the facts schema; `fit_facepalm.load_features` picks the
# scalar columns (`loss`, `missed`, `reply_prob` and the probabilities) by name. `reply_uci` /
# `reply_prob` are Maia's probability of the first token of the stored refutation line, from the same
# post-blunder policy call as `reply_spread`; `loss` / `missed` are the stored inputs under the quiet
# rule (`material_inputs_from_facts`); the last four are the raw inputs, so every material value is
# recomputable offline.
QUIET_FEATURE_COLUMNS: tuple[str, ...] = (
    "reply_uci",
    "reply_prob",
    "loss",
    "missed",
    "pre_fen",
    "played_uci",
    "played_line",
    "best_line",
)

FEATURE_COLUMNS: tuple[str, ...] = (*FACTS_FEATURE_COLUMNS, *QUIET_FEATURE_COLUMNS)

# Float cells are written with this many significant digits (the fit does not need more).
FLOAT_SIGNIFICANT_DIGITS: int = 6

# Policy source: (FEN, Elo) -> {uci: probability} or None (Maia unavailable / position unusable).
PolicyFn = Callable[[str, float], Mapping[str, float] | None]

PV_SEPARATOR: str = " "

NOTE_ILLEGAL_PLAYED: str = "illegal_played_move"
NOTE_NO_ELO: str = "rating_unknown"
NOTE_NO_POLICY: str = "no_policy"
NOTE_NO_PRE_POLICY: str = "no_pre_policy"
NOTE_REPLY_MISSING: str = "reply_missing"
NOTE_SEPARATOR: str = ";"
NOTE_GAME_OVER: str = "post_board_game_over"


@dataclass(frozen=True, slots=True)
class LabelRow:
    """One labelled (or extra, unlabelled) blunder. `label` is "1", "0", "0.5" or "" (extra)."""

    n: str
    set_id: str
    game_id: int
    ply: int
    label: str


@dataclass(frozen=True, slots=True)
class FeatureRow:
    """The fit inputs of one blunder; None means the value is not available (NULL)."""

    label_row: LabelRow
    pinned_elo: float | None
    played_prob: float | None
    reply_spread: float | None
    best_prob: float | None
    pre_spread: float | None
    facts: LineFacts
    best_facts: LineFacts
    best_uci: str | None
    pv_source: PvSource
    pv_plies: int
    best_pv_plies: int
    note: str
    # Phase 259 (D-07, D-12): the reply probability, the stored material inputs, and the raw inputs
    # they were computed from.
    reply_uci: str | None
    reply_prob: float | None
    quiet: MaterialInputs
    pre_fen: str
    played_uci: str
    played_line: str
    best_line: str


def _pv_plies(pv: str | None) -> int:
    return len(pv.split(PV_SEPARATOR)) if pv else 0


def _join_notes(*notes: str) -> str:
    """The distinct non-empty notes, in order, joined with NOTE_SEPARATOR."""
    return NOTE_SEPARATOR.join(dict.fromkeys(note for note in notes if note))


def _spread_for(
    post_board: chess.Board,
    pinned_elo: float | None,
    policy_fn: PolicyFn,
    reply_uci: str | None = None,
) -> tuple[float | None, float | None, str]:
    """(reply spread, reply probability, note) of the full policy after the blunder.

    One policy call gives both numbers (D-07). The reply probability is the policy's value for
    `reply_uci`, the first token of the stored refutation line; a missing line or a token the policy
    does not carry gives None and NOTE_REPLY_MISSING. A None spread keeps its own note.
    """
    if pinned_elo is None:
        return None, None, NOTE_NO_ELO
    if not any(post_board.legal_moves):
        return None, None, NOTE_GAME_OVER
    policy = policy_fn(post_board.fen(), pinned_elo)
    if not policy:
        return None, None, NOTE_NO_POLICY
    reply_prob = policy.get(reply_uci) if reply_uci else None
    return reply_spread(policy), reply_prob, "" if reply_prob is not None else NOTE_REPLY_MISSING


def best_uci_of(best_pv: str | None, best_move: str | None) -> str | None:
    """The best move: the first token of the stored best line, else game_positions.best_move.

    The two disagree on a handful of rows (research Pitfall 7); the line wins so the best-move
    probability and the best-line facts always describe the same move.
    """
    if best_pv:
        return best_pv.split(PV_SEPARATOR)[0]
    return best_move or None


def _pre_inputs(
    pre_board: chess.Board, best_uci: str | None, pinned_elo: float | None, policy_fn: PolicyFn
) -> tuple[float | None, float | None, str]:
    """(best_prob, pre_spread, note) from ONE policy call on the pre-blunder board (D-08)."""
    if pinned_elo is None:
        return None, None, NOTE_NO_ELO
    policy = policy_fn(pre_board.fen(), pinned_elo)
    if not policy:
        return None, None, NOTE_NO_PRE_POLICY
    best_prob = policy.get(best_uci) if best_uci else None
    # The pre-blunder spread is the 247 effective-moves formula on the pre-blunder policy. Plan
    # 254-16 adds `pre_blunder_spread` as a named wrapper of this same formula; until then the
    # app's `reply_spread` is the one implementation (it is the same `_effective_moves`).
    return best_prob, reply_spread(policy), ""


def build_feature_row(
    label_row: LabelRow,
    *,
    pre_board: chess.Board,
    played_uci: str,
    pinned_elo: float | None,
    played_prob: float | None,
    pv: str | None,
    pv_source: PvSource,
    policy_fn: PolicyFn,
    best_pv: str | None = None,
    best_move: str | None = None,
) -> FeatureRow:
    """Compute the features of one blunder from the replayed pre-board and the stored lines.

    `pre_board` is the position before the blunder (never mutated); `pv` is the stored
    refutation line from the position after it and `best_pv` the stored best line at the flaw
    ply (best move first). The reply spread comes from `policy_fn` on the post-blunder board at
    `pinned_elo`; the best-move probability and the pre-blunder spread from ONE `policy_fn`
    call on the pre-board; the line facts from the app's `quiet_line_facts` / `quiet_best_line_facts`.
    """
    best_uci = best_uci_of(best_pv, best_move)
    best_prob, pre_spread, pre_note = _pre_inputs(pre_board, best_uci, pinned_elo, policy_fn)
    post_board = pre_board.copy(stack=False)
    reply_uci = pv.split(PV_SEPARATOR)[0] if pv else None
    try:
        post_board.push_uci(played_uci)
    except ValueError:
        spread, reply_prob, note = None, None, NOTE_ILLEGAL_PLAYED
        facts = quiet_line_facts(pre_board, played_uci, None)
    else:
        spread, reply_prob, note = _spread_for(post_board, pinned_elo, policy_fn, reply_uci)
        facts = quiet_line_facts(pre_board, played_uci, pv)
    best_line = best_pv or best_move or ""
    best_facts = quiet_best_line_facts(pre_board, best_line)
    return FeatureRow(
        label_row=label_row,
        pinned_elo=pinned_elo,
        played_prob=played_prob,
        reply_spread=spread,
        best_prob=best_prob,
        pre_spread=pre_spread,
        facts=facts,
        best_facts=best_facts,
        best_uci=best_uci,
        pv_source=pv_source,
        pv_plies=_pv_plies(pv),
        best_pv_plies=_pv_plies(best_pv),
        note=_join_notes(note, pre_note),
        reply_uci=reply_uci,
        reply_prob=reply_prob,
        # The stored inputs: the writer's aggregation over the quiet facts computed above.
        quiet=material_inputs_from_facts(facts, best_facts),
        pre_fen=pre_board.fen(),
        played_uci=played_uci,
        played_line=pv or "",
        best_line=best_line,
    )


def _cell(value: object) -> str:
    """One TSV cell: None is an empty field, floats keep FLOAT_SIGNIFICANT_DIGITS digits."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{FLOAT_SIGNIFICANT_DIGITS}g}"
    return str(value).replace("\t", " ").replace("\n", " ")


def feature_cells(row: FeatureRow) -> list[str]:
    """The cells of `row` in FEATURE_COLUMNS order (signed material, positive = blunderer up)."""
    label_row = row.label_row
    values: list[object] = [
        label_row.n,
        label_row.set_id,
        label_row.game_id,
        label_row.ply,
        label_row.label,
        row.pinned_elo,
        row.played_prob,
        row.reply_spread,
        row.best_prob,
        row.pre_spread,
        row.facts.mate_ply,
        row.best_facts.opponent_mate_ply,
        row.best_uci,
        row.pv_source,
        row.pv_plies,
        row.best_pv_plies,
        row.note,
        row.reply_uci,
        row.reply_prob,
        row.quiet.loss,
        row.quiet.missed,
        row.pre_fen,
        row.played_uci,
        row.played_line,
        row.best_line,
    ]
    return [_cell(value) for value in values]


def write_features_tsv(rows: Sequence[FeatureRow], path: Path) -> None:
    """Write the header and one line per row, tab separated."""
    lines = ["\t".join(FEATURE_COLUMNS)]
    lines.extend("\t".join(feature_cells(row)) for row in rows)
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Real sources: labels, pv cache, database
# ---------------------------------------------------------------------------

EXIT_OK: int = 0
EXIT_MAIA_UNAVAILABLE: int = 3
EXIT_CACHE_MISMATCH: int = 4
EXIT_ROWS_MISSING: int = 5

DB_TARGETS: tuple[str, ...] = ("dev", "prod")
DEFAULT_MAIA_THREADS: int = 4

# game_flaws.severity of a blunder (game_flaws_repository._SEVERITY_INT).
BLUNDER_SEVERITY: int = 2
NOTE_NOT_A_BLUNDER: str = "not_a_blunder"

EXTRA_N: str = "extra"
CACHE_FENS_FILE: str = "fens.json"
CACHE_PVS_FILE: str = "pvs.json"
CACHE_SET6_FILE: str = "set6-lines.json"
CACHE_PACK_SEPARATOR: str = "|"
# The first FEN fields (placement, side to move, castling, en passant); the clocks are not compared.
FEN_BOARD_FIELDS: int = 4

_LINK_RE = re.compile(r"game_id=(\d+)&ply=(\d+)")
_EXTRA_RE = re.compile(r"^(\d+):(\d+)$")

# (cached pre-board FEN, played UCI, stored line at label time or None)
CacheEntry = tuple[str, str, str | None]


@dataclass(frozen=True, slots=True)
class GameInputs:
    """Everything one label row reads from the database."""

    platform: str
    time_control_bucket: str | None
    time_control_str: str | None
    white_rating: int | None
    black_rating: int | None
    pgn: str
    played_prob: float | None
    severity: int
    pv: str | None
    # Stored best line (best move first) and best move at the flaw ply (Phase 254 D-16).
    best_pv: str | None = None
    best_move: str | None = None


def cache_key(game_id: int, ply: int) -> str:
    return f"{game_id}:{ply}"


def parse_labels(path: Path) -> list[LabelRow]:
    """The label rows of the owner's label TSV; game_id and ply come from the link column."""
    rows: list[LabelRow] = []
    with path.open(newline="") as handle:
        for record in csv.DictReader(handle, delimiter="\t"):
            match = _LINK_RE.search(record["link"])
            if match is None:
                raise ValueError("label row without a game_id / ply link")
            rows.append(
                LabelRow(
                    n=record["n"],
                    set_id=record["set"],
                    game_id=int(match.group(1)),
                    ply=int(match.group(2)),
                    label=record["label"],
                )
            )
    return rows


def parse_extra(spec: str) -> LabelRow:
    """`GAME:PLY` as an unlabelled extra row."""
    match = _EXTRA_RE.match(spec)
    if match is None:
        raise ValueError("--extra takes GAME:PLY")
    return LabelRow(
        n=EXTRA_N, set_id=EXTRA_N, game_id=int(match.group(1)), ply=int(match.group(2)), label=""
    )


def _unpack(packed: str) -> tuple[str, str]:
    fen, uci = packed.rsplit(CACHE_PACK_SEPARATOR, 1)
    return fen, uci


def load_pv_cache(cache_dir: Path) -> dict[str, CacheEntry]:
    """Label-time lines: fens.json + pvs.json (sets 1-5) and set6-lines.json when present.

    fens.json maps "game_id:ply" to "<pre-board FEN>|<played uci>", pvs.json maps the same key
    to the stored line (null when none was stored); set6-lines.json maps the key to
    ["<FEN>|<uci>", line-or-null].
    """
    fens: dict[str, str] = json.loads((cache_dir / CACHE_FENS_FILE).read_text())
    pvs: dict[str, str | None] = json.loads((cache_dir / CACHE_PVS_FILE).read_text())
    entries: dict[str, CacheEntry] = {}
    for key, packed in fens.items():
        if key in pvs:
            fen, uci = _unpack(packed)
            entries[key] = (fen, uci, pvs[key] or None)
    set6_path = cache_dir / CACHE_SET6_FILE
    if set6_path.exists():
        set6: dict[str, list[str | None]] = json.loads(set6_path.read_text())
        for key, (packed, line) in set6.items():
            fen, uci = _unpack(cast(str, packed))
            entries[key] = (fen, uci, line or None)
    return entries


def _board_part(fen: str) -> str:
    return " ".join(fen.split()[:FEN_BOARD_FIELDS])


def _mover_elo(inputs: GameInputs, pre_board: chess.Board) -> float | None:
    """Pinned Elo of the side to move on `pre_board` (board.turn, not ply parity)."""
    raw = inputs.white_rating if pre_board.turn == chess.WHITE else inputs.black_rating
    if raw is None:
        return None
    return pinned_elo_for_mover(
        raw_rating=raw,
        platform=cast(Platform, inputs.platform),
        time_control_bucket=cast(TimeControlBucket | None, inputs.time_control_bucket),
        is_correspondence=is_correspondence_time_control(inputs.time_control_str),
    )


def _select_pv(inputs: GameInputs, cache_entry: CacheEntry | None) -> tuple[str | None, PvSource]:
    if cache_entry is not None:
        line = cache_entry[2]
        return line, "cache" if line else "cache_none"
    return inputs.pv, "db" if inputs.pv else "db_none"


def resolve_feature_row(
    label_row: LabelRow,
    inputs: GameInputs,
    cache_entry: CacheEntry | None,
    policy_fn: PolicyFn,
) -> tuple[FeatureRow, bool] | None:
    """The feature row of one label row, and whether its cache entry disagrees with the replay.

    The pre-board and played move come from replaying the PGN (never from a FEN). A cache entry
    whose board part or played UCI differs from that replay is a mismatch (the cached line was
    computed for another position). None when the PGN never reaches the ply.
    """
    boards, _reason = replay_flaw_boards(inputs.pgn, [label_row.ply])
    if label_row.ply not in boards:
        return None
    pre_board, played_uci = boards[label_row.ply]
    mismatch = cache_entry is not None and (
        _board_part(cache_entry[0]) != _board_part(pre_board.fen()) or cache_entry[1] != played_uci
    )
    pv, pv_source = _select_pv(inputs, cache_entry)
    row = build_feature_row(
        label_row,
        pre_board=pre_board,
        played_uci=played_uci,
        pinned_elo=_mover_elo(inputs, pre_board),
        played_prob=inputs.played_prob,
        pv=pv,
        pv_source=pv_source,
        policy_fn=policy_fn,
        best_pv=inputs.best_pv,
        best_move=inputs.best_move,
    )
    if inputs.severity != BLUNDER_SEVERITY:
        row = replace(row, note=_join_notes(row.note, NOTE_NOT_A_BLUNDER))
    return row, mismatch


async def read_game_inputs(conn: AsyncConnection, game_id: int, ply: int) -> GameInputs | None:
    """The game, its flaw row at `ply`, the stored lines at ply + 1 (refutation) and ply (best).

    None when the game or the flaw row is missing.
    """
    game = (
        await conn.execute(
            select(
                Game.user_id,
                Game.pgn,
                Game.platform,
                Game.time_control_bucket,
                Game.time_control_str,
                Game.white_rating,
                Game.black_rating,
            ).where(Game.id == game_id)
        )
    ).first()
    if game is None:
        return None
    flaw = (
        await conn.execute(
            select(GameFlaw.maia_played_prob, GameFlaw.severity).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game_id,
                GameFlaw.ply == ply,
            )
        )
    ).first()
    if flaw is None:
        return None
    pv = (
        await conn.execute(
            select(GamePosition.pv).where(
                GamePosition.user_id == game.user_id,
                GamePosition.game_id == game_id,
                GamePosition.ply == ply + 1,
            )
        )
    ).scalar_one_or_none()
    best = (
        await conn.execute(
            select(GamePosition.pv, GamePosition.best_move).where(
                GamePosition.user_id == game.user_id,
                GamePosition.game_id == game_id,
                GamePosition.ply == ply,
            )
        )
    ).first()
    return GameInputs(
        platform=game.platform,
        time_control_bucket=game.time_control_bucket,
        time_control_str=game.time_control_str,
        white_rating=game.white_rating,
        black_rating=game.black_rating,
        pgn=game.pgn,
        played_prob=flaw.maia_played_prob,
        severity=flaw.severity,
        pv=pv,
        best_pv=None if best is None else best.pv,
        best_move=None if best is None else best.best_move,
    )


@dataclass(slots=True)
class CollectedRows:
    rows: list[FeatureRow]
    missing: list[str]
    mismatches: list[str]


async def collect_rows(
    conn: AsyncConnection,
    labels: Sequence[LabelRow],
    cache: Mapping[str, CacheEntry],
    policy_fn: PolicyFn,
) -> CollectedRows:
    """Read and resolve every label row; rows that cannot be built are listed by n."""
    collected = CollectedRows(rows=[], missing=[], mismatches=[])
    for label_row in labels:
        inputs = await read_game_inputs(conn, label_row.game_id, label_row.ply)
        resolved = (
            None
            if inputs is None
            else resolve_feature_row(
                label_row, inputs, cache.get(cache_key(label_row.game_id, label_row.ply)), policy_fn
            )
        )
        if resolved is None:
            collected.missing.append(label_row.n)
            continue
        row, mismatch = resolved
        collected.rows.append(row)
        if mismatch:
            collected.mismatches.append(label_row.n)
    return collected


def _has_null_score_input(row: FeatureRow) -> bool:
    return (
        row.played_prob is None
        or row.reply_spread is None
        or loss_feature(row.facts.loss_at(3), row.facts.mate_ply, loss_floor=None) is None
    )


def _best_line_unknown(row: FeatureRow) -> bool:
    """No settled best-line fact at all: the missed term contributes 0 for this row (D-18)."""
    return row.best_facts.opponent_mate_ply is None and all(
        value is None for value in row.best_facts.material_array()
    )


def summary_line(collected: CollectedRows) -> str:
    """One line: rows, rows per pv_source, cache mismatches, NULL score inputs, NULL best lines."""
    sources: dict[str, int] = {}
    for row in collected.rows:
        sources[row.pv_source] = sources.get(row.pv_source, 0) + 1
    per_source = ", ".join(f"{name} {count}" for name, count in sorted(sources.items()))
    null_inputs = sum(_has_null_score_input(row) for row in collected.rows)
    null_best = sum(_best_line_unknown(row) for row in collected.rows)
    return (
        f"rows {len(collected.rows)}; pv_source: {per_source}; "
        f"cache mismatches {len(collected.mismatches)}; rows with a NULL score input {null_inputs}; "
        f"rows with a NULL best line {null_best}"
    )


def gather_labels(label_files: Sequence[Path], extras: Sequence[str]) -> list[LabelRow]:
    """Every label file's rows in argument order, then the --extra rows."""
    rows = [row for path in label_files for row in parse_labels(path)]
    return [*rows, *(parse_extra(spec) for spec in extras)]


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the facepalm features table.")
    parser.add_argument("--db", choices=DB_TARGETS, required=True, help="read-only source database")
    parser.add_argument(
        "--labels",
        type=Path,
        action="append",
        default=[],
        help="owner label TSV; repeatable (the 180 existing labels plus the miss set)",
    )
    parser.add_argument(
        "--pv-cache",
        type=Path,
        default=None,
        help="directory with fens.json, pvs.json and set6-lines.json (lines as stored at label time)",
    )
    parser.add_argument(
        "--extra", action="append", default=[], metavar="GAME:PLY", help="unlabelled extra row"
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="list label rows whose game or flaw row is gone and still write the table (exit 0)",
    )
    parser.add_argument("--out", type=Path, required=True, help="features TSV to write")
    parser.add_argument("--maia-threads", type=int, default=DEFAULT_MAIA_THREADS)
    args = parser.parse_args(argv)
    if not args.labels and not args.extra:
        parser.error("give at least one --labels file or --extra GAME:PLY")
    return args


async def _run(args: argparse.Namespace) -> int:
    labels = gather_labels(args.labels, args.extra)
    cache = load_pv_cache(args.pv_cache) if args.pv_cache else {}
    await maia_engine.start_maia(intra_op_num_threads=args.maia_threads)
    if not maia_engine.is_maia_available():
        print("Maia is unavailable (uv sync --group maia-inference?)", file=sys.stderr)
        return EXIT_MAIA_UNAVAILABLE
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with engine.connect() as conn:
            collected = await collect_rows(conn, labels, cache, maia_engine.full_policy)
    finally:
        await engine.dispose()
    print(summary_line(collected))
    if collected.mismatches:
        print(f"cache mismatch on rows: {', '.join(collected.mismatches)}", file=sys.stderr)
        return EXIT_CACHE_MISMATCH
    if collected.missing and not args.skip_missing:
        print(f"game or flaw row missing for rows: {', '.join(collected.missing)}", file=sys.stderr)
        return EXIT_ROWS_MISSING
    if collected.missing:
        # --skip-missing: a prod pull legitimately lacks games deleted since labelling (Pitfall 10).
        print(f"missing: {', '.join(collected.missing)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_features_tsv(collected.rows, args.out)
    print(f"wrote {args.out}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
