"""Tests for the offline material refresh of a facepalm features table (Phase 262 plan 03, D-01).

The refresh recomputes `loss` / `missed` from the raw lines of a committed features table with the
current rule (`facepalm_material_inputs`) and keeps the previous pair as `loss_shipped` /
`missed_shipped`. No database, no Maia.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.blunder_check import refresh_features_material as refresh
from scripts.blunder_check.fit_facepalm import load_features

# The D-03 position of plan 01: the blunderer (White) promotes at ply 3 and the rook takes the new
# queen at once, a net loss of one. The stored loss is 1.0 under the promotion rule; the Phase 259
# rule stored 0.
PROMOTION_FEN = "1r4k1/P7/8/8/8/8/8/6K1 w - - 0 1"
PROMOTION_PLAYED = "g1h1"
PROMOTION_LINE = "g8f7 a7a8q b8a8 h1g1 f7e6 g1f2 e6d5 f2e3 d5c4 e3d2"
# A queen hung on the next move: the stored loss is the cap, 5.0, under every rule.
HUNG_QUEEN_FEN = "3r2k1/8/8/8/8/8/8/3QK3 w - - 0 1"
HUNG_QUEEN_PLAYED = "d1d7"
HUNG_QUEEN_LINE = "d8d7"

INPUT_COLUMNS: tuple[str, ...] = (
    "n",
    "set",
    "label",
    "played_prob",
    "reply_spread",
    "best_prob",
    "reply_prob",
    "played_mat_1",
    "best_mat_1",
    "loss",
    "missed",
    "loss_shipped",
    "missed_shipped",
    "pre_fen",
    "played_uci",
    "played_line",
    "best_line",
)


def _record(**overrides: str) -> dict[str, str]:
    base = dict.fromkeys(INPUT_COLUMNS, "")
    base.update(n="1", set="1", label="1", played_prob="0.1", reply_spread="2", best_prob="0.3")
    base.update(reply_prob="0.2", played_mat_1="9", best_mat_1="9")
    base.update(overrides)
    return base


def _write(path: Path, records: list[dict[str, str]], columns: tuple[str, ...]) -> Path:
    lines = ["\t".join(columns), *("\t".join(rec[col] for col in columns) for rec in records)]
    path.write_text("\n".join(lines) + "\n")
    return path


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(path.read_text().splitlines(), delimiter="\t")
    return list(reader.fieldnames or ()), list(reader)


def _promotion_record() -> dict[str, str]:
    return _record(
        n="1",
        loss="0",
        missed="0",
        loss_shipped="9",
        missed_shipped="9",
        pre_fen=PROMOTION_FEN,
        played_uci=PROMOTION_PLAYED,
        played_line=PROMOTION_LINE,
    )


def _quiet_record() -> dict[str, str]:
    return _record(
        n="2",
        loss="5",
        missed="0",
        loss_shipped="9",
        missed_shipped="9",
        pre_fen=HUNG_QUEEN_FEN,
        played_uci=HUNG_QUEEN_PLAYED,
        played_line=HUNG_QUEEN_LINE,
    )


def test_refresh_row_recomputes_a_promotion_and_keeps_the_previous_pair() -> None:
    row = refresh.refresh_row(_promotion_record())

    assert (row["loss"], row["missed"]) == ("1", "0")
    # The previous pair is the input's loss / missed cells, never the input's older shipped columns.
    assert (row["loss_shipped"], row["missed_shipped"]) == ("0", "0")


def test_refresh_row_keeps_a_row_without_a_promotion_byte_identical() -> None:
    record = _quiet_record()

    row = refresh.refresh_row(record)

    assert (row["loss"], row["missed"]) == (record["loss"], record["missed"])
    assert (row["loss_shipped"], row["missed_shipped"]) == ("5", "0")


def test_refresh_row_without_raw_inputs_keeps_its_cells() -> None:
    record = _record(loss="1.5", missed="0.25", loss_shipped="7", missed_shipped="7")

    row = refresh.refresh_row(record)

    assert (row["loss"], row["missed"]) == ("1.5", "0.25")
    assert (row["loss_shipped"], row["missed_shipped"]) == ("1.5", "0.25")


def test_refresh_table_drops_stale_columns_and_the_fit_tool_loads_it(tmp_path: Path) -> None:
    src = _write(tmp_path / "in.tsv", [_promotion_record(), _quiet_record()], INPUT_COLUMNS)
    dst = tmp_path / "out.tsv"

    summary = refresh.refresh_table(src, dst)

    names, records = _read(dst)
    assert not [name for name in names if name.startswith(refresh.STALE_COLUMN_PREFIXES)]
    assert {"loss_shipped", "missed_shipped", *refresh.RAW_INPUT_COLUMNS} <= set(names)
    assert [rec["loss"] for rec in records] == ["1", "5"]
    assert summary.rows == 2
    assert summary.rows_without_raw_inputs == 0
    assert summary.changed_n == ["1"]
    assert load_features(dst).has_shipped is True


def test_refresh_table_adds_the_shipped_columns_when_the_input_lacks_them(tmp_path: Path) -> None:
    columns = tuple(c for c in INPUT_COLUMNS if not c.endswith("_shipped"))
    src = _write(tmp_path / "in.tsv", [_promotion_record()], columns)
    dst = tmp_path / "out.tsv"

    refresh.refresh_table(src, dst)

    names, records = _read(dst)
    assert names.index("loss_shipped") == names.index("missed") + 1
    assert names.index("missed_shipped") == names.index("missed") + 2
    assert (records[0]["loss_shipped"], records[0]["missed_shipped"]) == ("0", "0")


def test_a_row_with_an_empty_pre_fen_is_counted_and_kept(tmp_path: Path) -> None:
    keep = _record(n="3", loss="2", missed="1")
    src = _write(tmp_path / "in.tsv", [keep], INPUT_COLUMNS)
    dst = tmp_path / "out.tsv"

    summary = refresh.refresh_table(src, dst)

    _, records = _read(dst)
    assert (records[0]["loss"], records[0]["missed"]) == ("2", "1")
    assert summary.rows_without_raw_inputs == 1
    assert summary.changed_n == []


@pytest.mark.parametrize("dropped", refresh.RAW_INPUT_COLUMNS)
def test_a_table_missing_a_raw_input_exits_2_and_writes_nothing(
    tmp_path: Path, dropped: str
) -> None:
    columns = tuple(c for c in INPUT_COLUMNS if c != dropped)
    src = _write(tmp_path / "in.tsv", [_quiet_record()], columns)
    dst = tmp_path / "out.tsv"

    code = refresh.main(["--features", str(src), "--out", str(dst)])

    assert code == refresh.EXIT_BAD_TABLE
    assert not dst.exists()


def test_main_prints_a_summary_line_with_the_changed_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = _write(tmp_path / "in.tsv", [_promotion_record(), _quiet_record()], INPUT_COLUMNS)
    dst = tmp_path / "out.tsv"

    code = refresh.main(["--features", str(src), "--out", str(dst)])

    assert code == refresh.EXIT_OK
    assert "changed rows (n): 1" in capsys.readouterr().out
