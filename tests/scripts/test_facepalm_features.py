"""Tests for the facepalm features builder (Phase 250 plan 02, D-01 / D-02)."""

from __future__ import annotations

import io
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import chess
import chess.pgn
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.services.line_material import line_facts, null_line_facts
from app.services.maia_flaw_scoring import replay_flaw_boards
from app.services.maia_flaw_stats import reply_spread
from scripts.blunder_check import facepalm_features
from scripts.blunder_check.facepalm_features import (
    EXIT_CACHE_MISMATCH,
    EXIT_MAIA_UNAVAILABLE,
    EXIT_OK,
    EXIT_ROWS_MISSING,
    FEATURE_COLUMNS,
    CollectedRows,
    FeatureRow,
    GameInputs,
    LabelRow,
    build_feature_row,
    collect_rows,
    load_pv_cache,
    parse_extra,
    parse_labels,
    resolve_feature_row,
    write_features_tsv,
)
from scripts.blunder_check.sample import make_readonly_engine
from tests.blunder_check_seed import (
    SEED_PGN,
    SeedBlunder,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)
from tests.services.maia_fakes import fake_full_policy

# Plies of SEED_PGN used as stand-in blunders and how many following game moves form the line.
TRACER_PLIES: tuple[int, ...] = (10, 21, 33)
TRACER_LINE_PLIES: int = 5
TRACER_ELO: float = 1500.0
TRACER_PLAYED_PROB: float = 0.04


def _mainline_ucis() -> list[str]:
    game = chess.pgn.read_game(io.StringIO(SEED_PGN))
    assert game is not None
    return [node.move.uci() for node in game.mainline()]


def _feature_rows() -> list[tuple[FeatureRow, chess.Board, str, str | None]]:
    boards, error = replay_flaw_boards(SEED_PGN, TRACER_PLIES)
    assert error is None
    ucis = _mainline_ucis()
    built: list[tuple[FeatureRow, chess.Board, str, str | None]] = []
    for index, ply in enumerate(TRACER_PLIES):
        pre_board, played = boards[ply]
        pv = " ".join(ucis[ply + 1 : ply + 1 + TRACER_LINE_PLIES])
        label = LabelRow(n=str(index + 1), set_id="1", game_id=1000 + ply, ply=ply, label="1")
        row = build_feature_row(
            label,
            pre_board=pre_board,
            played_uci=played,
            pinned_elo=TRACER_ELO,
            played_prob=TRACER_PLAYED_PROB,
            pv=pv,
            pv_source="db",
            policy_fn=fake_full_policy,
        )
        built.append((row, pre_board, played, pv))
    return built


def test_tsv_header_and_spread_match_the_apps_functions(tmp_path: Path) -> None:
    built = _feature_rows()
    out = tmp_path / "features.tsv"
    write_features_tsv([row for row, *_ in built], out)

    lines = out.read_text().splitlines()
    assert lines[0].split("\t") == list(FEATURE_COLUMNS)
    assert len(lines) == 1 + len(TRACER_PLIES)

    for row, pre_board, played, pv in built:
        post_board = pre_board.copy(stack=False)
        post_board.push_uci(played)
        expected_spread = reply_spread(fake_full_policy(post_board.fen(), TRACER_ELO))
        assert row.reply_spread == expected_spread
        assert row.facts == line_facts(pre_board, played, pv)
        assert row.pv_plies == TRACER_LINE_PLIES
        assert row.pinned_elo == TRACER_ELO

    cells = lines[1].split("\t")
    assert len(cells) == len(FEATURE_COLUMNS)
    record = dict(zip(FEATURE_COLUMNS, cells))
    assert record["game_id"] == str(1000 + TRACER_PLIES[0])
    assert record["pv_source"] == "db"
    assert float(record["reply_spread"]) == float(f"{built[0][0].reply_spread:.6g}")


# ---------------------------------------------------------------------------
# Task 2: labels, pv cache, row resolution, CLI exits, read-only DB source
# ---------------------------------------------------------------------------

REAL_LABELS = (
    Path(__file__).resolve().parents[2] / "reports/blunder-check/leg2-labels-2026-11-11.tsv"
)
EXPECTED_LABEL_ROWS: int = 180
SEED_PLY: int = 20


def _seed_inputs(pv: str | None = None) -> GameInputs:
    return GameInputs(
        platform="lichess",
        time_control_bucket="blitz",
        time_control_str="300+0",
        white_rating=1500,
        black_rating=1500,
        pgn=SEED_PGN,
        played_prob=0.05,
        severity=2,
        pv=pv,
    )


def _seed_pre_board(ply: int = SEED_PLY) -> tuple[chess.Board, str]:
    boards, error = replay_flaw_boards(SEED_PGN, [ply])
    assert error is None
    return boards[ply]


def _seed_line(ply: int = SEED_PLY) -> str:
    return " ".join(_mainline_ucis()[ply + 1 : ply + 1 + TRACER_LINE_PLIES])


def _label(ply: int = SEED_PLY, n: str = "1") -> LabelRow:
    return LabelRow(n=n, set_id="1", game_id=7, ply=ply, label="1")


def _resolved_row(inputs: GameInputs) -> FeatureRow:
    resolved = resolve_feature_row(_label(), inputs, None, fake_full_policy)
    assert resolved is not None
    return resolved[0]


def test_parse_labels_on_the_real_label_file() -> None:
    rows = parse_labels(REAL_LABELS)

    assert len(rows) == EXPECTED_LABEL_ROWS
    assert {row.label for row in rows} == {"1", "0", "0.5"}
    assert {row.set_id for row in rows} == {"1", "2", "3", "4", "5", "6"}
    first = rows[0]
    assert (first.n, first.game_id, first.ply, first.label) == ("1", 1940139, 21, "0")


def test_parse_extra_is_an_unlabelled_row() -> None:
    extra = parse_extra("2099808:23")

    assert (extra.n, extra.game_id, extra.ply, extra.label) == ("extra", 2099808, 23, "")
    with pytest.raises(ValueError):
        parse_extra("2099808")


def test_load_pv_cache_reads_the_real_shapes(tmp_path: Path) -> None:
    pre_board, played = _seed_pre_board()
    packed = f"{pre_board.fen()}|{played}"
    (tmp_path / "fens.json").write_text(json.dumps({"7:20": packed, "8:30": packed, "9:9": packed}))
    (tmp_path / "pvs.json").write_text(json.dumps({"7:20": "a1a2 b1b2", "8:30": None}))
    (tmp_path / "set6-lines.json").write_text(
        json.dumps({"10:40": [packed, "c1c2"], "11:41": [packed, None]})
    )

    cache = load_pv_cache(tmp_path)

    assert cache["7:20"] == (pre_board.fen(), played, "a1a2 b1b2")
    assert cache["8:30"] == (pre_board.fen(), played, None)
    assert "9:9" not in cache  # no entry in pvs.json
    assert cache["10:40"][2] == "c1c2"
    assert cache["11:41"][2] is None


def test_pv_source_selection() -> None:
    pre_board, played = _seed_pre_board()
    line = _seed_line()
    cached = (pre_board.fen(), played, line)
    cached_none = (pre_board.fen(), played, None)

    def source(inputs: GameInputs, entry: tuple[str, str, str | None] | None) -> str:
        resolved = resolve_feature_row(_label(), inputs, entry, fake_full_policy)
        assert resolved is not None
        return resolved[0].pv_source

    assert source(_seed_inputs(), cached) == "cache"
    assert source(_seed_inputs(), cached_none) == "cache_none"
    assert source(_seed_inputs(pv=line), None) == "db"
    assert source(_seed_inputs(pv=None), None) == "db_none"
    # A cache entry wins over a different stored line, and a null cached line is not replaced.
    assert source(_seed_inputs(pv=line), cached_none) == "cache_none"
    resolved = resolve_feature_row(_label(), _seed_inputs(pv=None), cached_none, fake_full_policy)
    assert resolved is not None
    assert resolved[0].pv_plies == 0
    assert resolved[0].facts == null_line_facts()


def test_cache_mismatch_is_detected() -> None:
    pre_board, played = _seed_pre_board()
    other_board, other_played = _seed_pre_board(SEED_PLY + 1)
    line = _seed_line()

    def mismatch(entry: tuple[str, str, str | None]) -> bool:
        resolved = resolve_feature_row(_label(), _seed_inputs(), entry, fake_full_policy)
        assert resolved is not None
        return resolved[1]

    assert not mismatch((pre_board.fen(), played, line))
    # Same board part with different clocks is not a mismatch.
    clocks = " ".join([*pre_board.fen().split()[:4], "9", "99"])
    assert not mismatch((clocks, played, line))
    assert mismatch((other_board.fen(), played, line))
    assert mismatch((pre_board.fen(), other_played, line))


def test_missing_ply_gives_no_row() -> None:
    too_far = _label(ply=500)

    assert resolve_feature_row(too_far, _seed_inputs(), None, fake_full_policy) is None


def test_unknown_rating_gives_a_null_spread_and_a_note() -> None:
    inputs = replace(_seed_inputs(), white_rating=None)

    resolved = resolve_feature_row(_label(), inputs, None, fake_full_policy)

    assert resolved is not None
    row = resolved[0]
    assert row.pinned_elo is None
    assert row.reply_spread is None
    assert row.note == "rating_unknown"


def test_pinned_elo_follows_the_mover_colour() -> None:
    inputs = replace(_seed_inputs(), white_rating=1400, black_rating=1800)

    white_row = resolve_feature_row(_label(ply=20), inputs, None, fake_full_policy)
    black_row = resolve_feature_row(_label(ply=21), inputs, None, fake_full_policy)

    assert white_row is not None and black_row is not None
    assert white_row[0].pinned_elo is not None and black_row[0].pinned_elo is not None
    assert white_row[0].pinned_elo < black_row[0].pinned_elo


def _fake_run_environment(
    monkeypatch: pytest.MonkeyPatch, collected: CollectedRows, *, maia_available: bool = True
) -> None:
    """Replace Maia, the engine and the row collection so the CLI runs without any service."""

    class _FakeEngine:
        def connect(self) -> "_FakeEngine":
            return self

        async def __aenter__(self) -> "_FakeEngine":
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            return None

        async def dispose(self) -> None:
            return None

    async def fake_start(**_: object) -> None:
        return None

    async def fake_collect(*_: object, **__: object) -> CollectedRows:
        return collected

    monkeypatch.setattr(facepalm_features.maia_engine, "start_maia", fake_start)
    monkeypatch.setattr(facepalm_features.maia_engine, "is_maia_available", lambda: maia_available)
    monkeypatch.setattr(facepalm_features, "make_readonly_engine", lambda _url: _FakeEngine())
    monkeypatch.setattr(facepalm_features, "db_url_for_target", lambda _target: "unused")
    monkeypatch.setattr(facepalm_features, "collect_rows", fake_collect)


def _write_label_file(path: Path) -> None:
    path.write_text(
        "n\tset\telo\tmove\tlink\tlabel\n1\t1\t1500\tNd2\thttps://x/analysis?game_id=7&ply=20\t1\n"
    )


def _cli(tmp_path: Path) -> tuple[list[str], Path]:
    labels = tmp_path / "labels.tsv"
    _write_label_file(labels)
    out = tmp_path / "out" / "features.tsv"
    return ["--db", "dev", "--labels", str(labels), "--out", str(out)], out


def test_cli_cache_mismatch_exits_4_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    row = _resolved_row(_seed_inputs())
    _fake_run_environment(monkeypatch, CollectedRows(rows=[row], missing=[], mismatches=["1"]))
    argv, out = _cli(tmp_path)

    assert facepalm_features.main(argv) == EXIT_CACHE_MISMATCH
    assert not out.exists()


def test_cli_missing_rows_exit_5(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_run_environment(monkeypatch, CollectedRows(rows=[], missing=["1"], mismatches=[]))
    argv, out = _cli(tmp_path)

    assert facepalm_features.main(argv) == EXIT_ROWS_MISSING
    assert not out.exists()


def test_cli_maia_unavailable_exits_3(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_run_environment(
        monkeypatch, CollectedRows(rows=[], missing=[], mismatches=[]), maia_available=False
    )
    argv, out = _cli(tmp_path)

    assert facepalm_features.main(argv) == EXIT_MAIA_UNAVAILABLE
    assert not out.exists()


def test_cli_success_writes_the_table_and_a_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    row = _resolved_row(_seed_inputs(pv=_seed_line()))
    _fake_run_environment(monkeypatch, CollectedRows(rows=[row], missing=[], mismatches=[]))
    argv, out = _cli(tmp_path)

    assert facepalm_features.main(argv) == EXIT_OK
    assert len(out.read_text().splitlines()) == 2
    assert "rows 1; pv_source: db 1; cache mismatches 0" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_read_only_database_source_end_to_end(test_engine: Any) -> None:
    """collect_rows reads a seeded game through the read-only engine and builds the row."""
    user_id, _ = await register_user("facepalm-features", beta=False, test_engine=test_engine)
    evals = with_user_blunder(flat_evals(61, 0), SEED_PLY, 500)
    game_id = await seed_judged_game(
        test_engine, user_id=user_id, evals_cp=evals, blunders=[SeedBlunder(ply=SEED_PLY)]
    )
    line = _seed_line()
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with maker() as session:
            await session.execute(
                update(GameFlaw)
                .where(GameFlaw.game_id == game_id, GameFlaw.ply == SEED_PLY)
                .values(maia_played_prob=0.03)
            )
            await session.execute(
                update(GamePosition)
                .where(GamePosition.game_id == game_id, GamePosition.ply == SEED_PLY + 1)
                .values(pv=line)
            )
            await session.commit()
        engine = make_readonly_engine(test_engine.url.render_as_string(hide_password=False))
        labels = [
            LabelRow(n="1", set_id="1", game_id=game_id, ply=SEED_PLY, label="1"),
            LabelRow(n="2", set_id="1", game_id=game_id, ply=SEED_PLY + 2, label="0"),
        ]
        try:
            async with engine.connect() as conn:
                collected = await collect_rows(conn, labels, {}, fake_full_policy)
        finally:
            await engine.dispose()

        assert collected.missing == ["2"]  # no flaw row at that ply
        assert collected.mismatches == []
        (row,) = collected.rows
        pre_board, played = _seed_pre_board()
        assert row.played_prob == pytest.approx(0.03)
        assert row.pv_source == "db"
        assert row.facts == line_facts(pre_board, played, line)
        assert row.pinned_elo is not None
        assert row.reply_spread is not None
    finally:
        await delete_games(test_engine, [game_id])


# Same pattern as the plan's acceptance grep: no ORM write constructs, no commit.
WRITE_PATH_RE = re.compile(
    r"\bsa\.(insert|update|delete)\(|\.commit\(\)|^from sqlalchemy import .*\b(insert|update|delete)\b",
    re.MULTILINE,
)


def test_builder_has_no_write_path() -> None:
    source = Path(facepalm_features.__file__).read_text()

    assert WRITE_PATH_RE.search(source) is None
