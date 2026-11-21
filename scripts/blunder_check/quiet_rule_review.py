"""Review what the quiet-point rule changes, grouped by cause (Phase 259 D-09).

Reads a features TSV written by ``facepalm_features.py`` (the Phase 259 columns ``pre_fen``,
``played_uci``, ``played_line``, ``best_line`` and the stored ``loss`` / ``missed``), applies the
shipped rule and the quiet rule to both stored lines at every odd depth with the app's own
functions, and writes a markdown report: counts by cause x line x depth, the rows whose stored
loss or missed moved, the reply-probability coverage and about ten before / after examples with
analysis links. Offline and read-only: no database, no Maia.

Usage::

    uv run python scripts/blunder_check/quiet_rule_review.py \
        --features <features.tsv> --out <review.md>

Exit codes: 0 report written, 2 the TSV is unusable (no ``pre_fen`` column or no rows).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import chess

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.services.facepalm_inputs import (  # noqa: E402
    MaterialInputs,
    facepalm_material_inputs,
    material_inputs_from_facts,
)

# The review must classify with the app's own replay and walk, never a copy of them.
from app.services.line_material import (  # noqa: E402
    LINE_LOSS_DEPTHS,
    LineFacts,
    _Step,  # noqa: PLC2701
    _parse_move,  # noqa: PLC2701
    _quiet_walk_end,  # noqa: PLC2701
    _replay_line,  # noqa: PLC2701
    best_line_facts,
    line_facts,
    quiet_best_line_facts,
    quiet_line_facts,
)

ChangeCause = Literal[
    "exchange_settled_at_end",
    "longer_exchange_settled",
    "later_capture_pulled_earlier",
    "other",
]
LineName = Literal["played", "best"]

CAUSES: Final[tuple[ChangeCause, ...]] = (
    "exchange_settled_at_end",
    "longer_exchange_settled",
    "later_capture_pulled_earlier",
    "other",
)
LINES: Final[tuple[LineName, ...]] = ("played", "best")

REVIEW_EXAMPLES: Final[int] = 10
# Tolerance for "the stored cell differs from the recomputed value": cells carry
# FEATURE_CELL_DIGITS significant digits, so the recomputed value is rounded the same way first.
REVIEW_EPSILON: Final[float] = 1e-6
# Mirrors facepalm_features.FLOAT_SIGNIFICANT_DIGITS (not imported: that module pulls in the
# database and Maia code, this tool stays offline; a test pins the two equal).
FEATURE_CELL_DIGITS: Final[int] = 6
# Labels of the four committed fixtures whose values change under the quiet rule.
FIXTURE_LABEL_NS: Final[tuple[str, ...]] = ("153", "154", "156", "170")
# The owner's D-13 example: game id and ply.
D13_GAME_PLY: Final[tuple[int, int]] = (2883555, 47)
ANALYSIS_LINK: Final[str] = "https://flawchess.com/analysis?game_id={game_id}&ply={ply}"

EXIT_OK: Final[int] = 0
EXIT_BAD_TSV: Final[int] = 2

PV_SEPARATOR: Final[str] = " "
QUARTILES: Final[int] = 4
REPORT_FLOAT_FORMAT: Final[str] = ".3f"
NONE_CELL: Final[str] = "-"


class ReviewError(Exception):
    """The features TSV cannot be reviewed (missing column or no rows)."""


@dataclass(frozen=True, slots=True)
class DepthChange:
    """One (line, depth) value the quiet rule changed, with its cause."""

    line: LineName
    depth: int
    old: int | None
    new: int | None
    cause: ChangeCause


@dataclass(frozen=True, slots=True)
class ReviewRow:
    """One features row with the old and quiet values of both lines and every change."""

    n: str
    set_id: str
    label: str
    game_id: int
    ply: int
    played_line: str
    best_line: str
    old_values: dict[tuple[LineName, int], int | None]
    new_values: dict[tuple[LineName, int], int | None]
    changes: tuple[DepthChange, ...]
    old_inputs: MaterialInputs
    new_inputs: MaterialInputs
    # The stored TSV cells differ from the recomputed quiet inputs (a drift; expected never).
    drift: bool
    reply_prob: float | None

    @property
    def link(self) -> str:
        return ANALYSIS_LINK.format(game_id=self.game_id, ply=self.ply)

    @property
    def is_d13(self) -> bool:
        return (self.game_id, self.ply) == D13_GAME_PLY

    @property
    def is_fixture(self) -> bool:
        return self.n in FIXTURE_LABEL_NS and self.set_id != "extra"

    @property
    def inputs_moved(self) -> bool:
        return _moved(self.old_inputs.loss, self.new_inputs.loss) or _moved(
            self.old_inputs.missed, self.new_inputs.missed
        )

    @property
    def impact(self) -> float:
        """|delta loss| + |delta missed|, a missing side counting as no movement."""
        return _delta(self.old_inputs.loss, self.new_inputs.loss) + _delta(
            self.old_inputs.missed, self.new_inputs.missed
        )


def _moved(old: float | None, new: float | None) -> bool:
    if old is None or new is None:
        return old is not new
    return abs(new - old) > REVIEW_EPSILON


def _delta(old: float | None, new: float | None) -> float:
    return 0.0 if old is None or new is None else abs(new - old)


def classify_change(steps: Sequence[_Step], depth: int) -> ChangeCause:
    """Why the quiet rule reads `depth` differently, from the replayed steps after the first move.

    The quiet walk is the app's own (`_quiet_walk_end`). "exchange_settled_at_end": the walk runs to
    the end of the line and the last step captured without mating (a static exchange settles it);
    "longer_exchange_settled": the walk went two or more plies past `depth`; "later_capture_pulled
    _earlier": it went exactly one ply past and that step is an opponent capture; anything else is
    "other", so an unexplained change stays visible.
    """
    if not steps:
        return "other"
    end = _quiet_walk_end(steps, depth)
    last = steps[-1]
    if (
        end == len(steps)
        and last.victim_value
        and not (last.blunderer_mated or last.opponent_mated)
    ):
        return "exchange_settled_at_end"
    if end - depth >= 2:
        return "longer_exchange_settled"
    if end - depth == 1 and steps[depth].opponent_move and steps[depth].victim_value:
        return "later_capture_pulled_earlier"
    return "other"


def _line_steps(pre_board: chess.Board, first_uci: str, rest: Sequence[str]) -> list[_Step]:
    """The replayed steps of a line after its first move; empty when the first move is not legal."""
    first = _parse_move(first_uci)
    if first is None or first not in pre_board.legal_moves:
        return []
    board = pre_board.copy(stack=False)
    blunderer = board.turn
    board.push(first)
    steps, _ = _replay_line(board, list(rest), blunderer)
    return steps


def _line_values(line: LineName, facts: LineFacts) -> dict[tuple[LineName, int], int | None]:
    """The compared value per odd depth: the played line's loss, the best line's signed material."""
    return {
        (line, depth): facts.loss_at(depth) if line == "played" else facts.material_at(depth)
        for depth in LINE_LOSS_DEPTHS
    }


def _changes(
    line: LineName,
    old: dict[tuple[LineName, int], int | None],
    new: dict[tuple[LineName, int], int | None],
    steps: Sequence[_Step],
) -> list[DepthChange]:
    return [
        DepthChange(
            line, depth, old[(line, depth)], new[(line, depth)], classify_change(steps, depth)
        )
        for depth in LINE_LOSS_DEPTHS
        if old[(line, depth)] != new[(line, depth)]
    ]


def _opt_float(cell: str) -> float | None:
    return float(cell) if cell else None


def _rounded(value: float | None) -> float | None:
    """`value` as a features cell stores it (FEATURE_CELL_DIGITS significant digits)."""
    return None if value is None else float(f"{value:.{FEATURE_CELL_DIGITS}g}")


def _drifted(stored: float | None, recomputed: float | None) -> bool:
    return _moved(stored, _rounded(recomputed))


def _review_row(record: dict[str, str]) -> ReviewRow:
    pre_board = chess.Board(record["pre_fen"])
    played_uci = record["played_uci"]
    played_line = record["played_line"]
    best_line = record["best_line"]
    old_facts = line_facts(pre_board, played_uci, played_line)
    new_facts = quiet_line_facts(pre_board, played_uci, played_line)
    old_best = best_line_facts(pre_board, best_line)
    new_best = quiet_best_line_facts(pre_board, best_line)
    old_values = {**_line_values("played", old_facts), **_line_values("best", old_best)}
    new_values = {**_line_values("played", new_facts), **_line_values("best", new_best)}
    best_tokens = best_line.split(PV_SEPARATOR) if best_line else [""]
    played_steps = _line_steps(pre_board, played_uci, played_line.split(PV_SEPARATOR))
    best_steps = _line_steps(pre_board, best_tokens[0], best_tokens[1:])
    changes = (
        *_changes("played", old_values, new_values, played_steps),
        *_changes("best", old_values, new_values, best_steps),
    )
    new_inputs = facepalm_material_inputs(pre_board, played_uci, played_line, best_line)
    return ReviewRow(
        n=record["n"],
        set_id=record["set"],
        label=record["label"],
        game_id=int(record["game_id"]),
        ply=int(record["ply"]),
        played_line=played_line,
        best_line=best_line,
        old_values=old_values,
        new_values=new_values,
        changes=changes,
        old_inputs=material_inputs_from_facts(old_facts, old_best),
        new_inputs=new_inputs,
        drift=_drifted(_opt_float(record.get("loss", "")), new_inputs.loss)
        or _drifted(_opt_float(record.get("missed", "")), new_inputs.missed),
        reply_prob=_opt_float(record.get("reply_prob", "")),
    )


def review_rows(path: Path) -> list[ReviewRow]:
    """Every row of the features TSV, reviewed; ReviewError when it cannot be reviewed."""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if "pre_fen" not in (reader.fieldnames or ()):
            raise ReviewError(
                "features file has no pre_fen column (pull it with the Phase 259 tool)"
            )
        rows = [_review_row(record) for record in reader if record["pre_fen"]]
    if not rows:
        raise ReviewError("features file has no rows with a pre_fen")
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _fmt_int(value: int | None) -> str:
    return NONE_CELL if value is None else str(value)


def _fmt_float(value: float | None) -> str:
    return NONE_CELL if value is None else format(value, REPORT_FLOAT_FORMAT)


def _n_key(n: str) -> tuple[int, int, str]:
    """Numeric labels first in numeric order, then the rest by text (deterministic)."""
    return (0, int(n), n) if n.isdigit() else (1, 0, n)


def _totals_section(rows: Sequence[ReviewRow]) -> list[str]:
    per_line = Counter(change.line for row in rows for change in row.changes)
    return [
        "## Totals",
        "",
        f"- rows: {len(rows)}",
        f"- rows with any changed value: {sum(bool(row.changes) for row in rows)}",
        *(f"- changed values, {line} line: {per_line[line]}" for line in LINES),
        f"- stored loss / missed cells that drift from the recomputed quiet value: "
        f"{sum(row.drift for row in rows)} (expected 0)",
        "",
    ]


def _cause_table(rows: Sequence[ReviewRow]) -> list[str]:
    counts = Counter((c.line, c.depth, c.cause) for row in rows for c in row.changes)
    lines = [
        "## Changed values by cause, line and depth",
        "",
        "| line | depth | " + " | ".join(CAUSES) + " | total |",
        "|---|---|" + "---|" * (len(CAUSES) + 1),
    ]
    for line in LINES:
        for depth in LINE_LOSS_DEPTHS:
            cells = [counts[(line, depth, cause)] for cause in CAUSES]
            lines.append(
                f"| {line} | {depth} | " + " | ".join(map(str, cells)) + f" | {sum(cells)} |"
            )
    per_cause = [sum(v for (_, _, cause), v in counts.items() if cause == c) for c in CAUSES]
    lines.append("| all | all | " + " | ".join(map(str, per_cause)) + f" | {sum(per_cause)} |")
    return [*lines, ""]


def _moved_section(rows: Sequence[ReviewRow]) -> list[str]:
    moved = sorted(
        (row for row in rows if row.inputs_moved), key=lambda r: (-r.impact, _n_key(r.n))
    )
    lines = [
        f"## Rows whose loss or missed moved by more than {REVIEW_EPSILON:g}",
        "",
        f"{len(moved)} of {len(rows)} rows.",
        "",
    ]
    lines.extend(
        f"- n={row.n} set={row.set_id} label={row.label or NONE_CELL} {row.link}: "
        f"loss {_fmt_float(row.old_inputs.loss)} -> {_fmt_float(row.new_inputs.loss)}, "
        f"missed {_fmt_float(row.old_inputs.missed)} -> {_fmt_float(row.new_inputs.missed)}"
        for row in moved
    )
    return [*lines, ""]


def _reply_section(rows: Sequence[ReviewRow]) -> list[str]:
    known = sorted(row.reply_prob for row in rows if row.reply_prob is not None)
    lines = [
        "## Reply probability coverage (information)",
        "",
        f"- known: {len(known)} of {len(rows)}",
    ]
    if len(known) >= 2:
        q1, median, q3 = statistics.quantiles(known, n=QUARTILES, method="inclusive")
        lines.append(f"- quartiles: {_fmt_float(q1)} / {_fmt_float(median)} / {_fmt_float(q3)}")
    elif known:
        lines.append(f"- single value: {_fmt_float(known[0])}")
    return [*lines, ""]


def _select_examples(rows: Sequence[ReviewRow]) -> list[ReviewRow]:
    """The fixture and D-13 rows always, filled to REVIEW_EXAMPLES with the largest movers."""
    forced = [row for row in rows if row.is_d13 or row.is_fixture]
    forced_ids = {id(row) for row in forced}
    others = sorted(
        (row for row in rows if id(row) not in forced_ids and row.changes),
        key=lambda r: (-r.impact, _n_key(r.n)),
    )
    chosen = [*forced, *others[: max(0, REVIEW_EXAMPLES - len(forced))]]
    return sorted(chosen, key=lambda r: (-r.impact, _n_key(r.n)))


def _depth_values(row: ReviewRow, line: LineName) -> str:
    causes = {(c.line, c.depth): c.cause for c in row.changes}
    parts: list[str] = []
    for depth in LINE_LOSS_DEPTHS:
        key = (line, depth)
        text = f"d{depth} {_fmt_int(row.old_values[key])} -> {_fmt_int(row.new_values[key])}"
        if key in causes:
            text += f" [{causes[key]}]"
        parts.append(text)
    return "; ".join(parts)


def _example(row: ReviewRow) -> list[str]:
    label = row.label or NONE_CELL
    return [
        f"### n={row.n} set={row.set_id} label={label}",
        "",
        f"- link: {row.link}",
        f"- played line: {row.played_line or NONE_CELL}",
        f"- best line: {row.best_line or NONE_CELL}",
        f"- played loss, shipped -> quiet: {_depth_values(row, 'played')}",
        f"- best material, shipped -> quiet: {_depth_values(row, 'best')}",
        f"- loss {_fmt_float(row.old_inputs.loss)} -> {_fmt_float(row.new_inputs.loss)}; "
        f"missed {_fmt_float(row.old_inputs.missed)} -> {_fmt_float(row.new_inputs.missed)}",
        "",
    ]


def render_review(rows: Sequence[ReviewRow]) -> str:
    """The deterministic markdown report (no usernames, no timestamps, no paths)."""
    lines = ["# Quiet-point rule review (Phase 259 D-09)", ""]
    lines.extend(_totals_section(rows))
    lines.extend(_cause_table(rows))
    lines.extend(_moved_section(rows))
    lines.extend(_reply_section(rows))
    lines.extend(["## Examples (shipped -> quiet)", ""])
    for row in _select_examples(rows):
        lines.extend(_example(row))
    return "\n".join(lines).rstrip("\n") + "\n"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review the quiet-point rule's changed values.")
    parser.add_argument(
        "--features", type=Path, required=True, help="features TSV (Phase 259 columns)"
    )
    parser.add_argument("--out", type=Path, required=True, help="markdown report to write")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = review_rows(args.features)
    except ReviewError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_BAD_TSV
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_review(rows))
    print(f"wrote {args.out}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
