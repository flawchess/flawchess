"""Tests for the blind stratified miss sampler (Phase 254 plan 05, D-14 / D-15 / D-16)."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Collection, Sequence
from pathlib import Path

import chess
import pytest

from app.services.line_material import best_line_facts, line_facts
from scripts.blunder_check.facepalm_features import parse_labels
from scripts.blunder_check.metrics import MaterialType
from scripts.blunder_check.miss_labels import (
    BEST_PROB_TERTILES,
    BLIND_COLUMNS,
    DISAGREEMENT_SET_ID,
    LOSS_STRATUM_QUOTAS,
    MIN_STABLE_LINE_PLIES,
    MISS_SET_ID,
    MISSED_SIZE_BUCKETS,
    MIXED_STRATUM,
    MIXED_TARGET,
    PURE_MISS_TARGET,
    MissCandidate,
    RawCandidate,
    Selected,
    Tally,
    append_blind_rows,
    best_prob_tertile,
    build_candidate,
    collect_candidates,
    disagreement_group,
    is_stable_line,
    missed_size_bucket,
    stratify,
    stratify_disagreement,
    summary_line,
    tertile_cuts,
    write_blind_tsv,
    write_key,
)
from tests.services.maia_fakes import fake_full_policy

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REAL_LABELS = REPO_ROOT / "reports/blunder-check/facepalm-labels.tsv"

# White Qe4 against Qe7: Qxe7 wins a queen (best_3 +9), Qa8+ wins nothing (played_3 0).
MISS_FEN = "6k1/4q3/8/8/4Q3/8/8/6K1 w - - 0 1"
MISS_PLAYED = "e4a8"
MISS_BEST_PV = "e4e7 g8h8 g1f1 h8g8"
MISS_REFUTATION_PV = "g8h7 a8e4 h7g8"
# The same position as a one-ply game, so the PGN replay path is exercised too.
MISS_PGN = f'[FEN "{MISS_FEN}"]\n[SetUp "1"]\n\n1. Qa8+ Kh7 2. Qe4+ Kg8 *\n'
# White Rd1 mates on d8: a best line that is one ply long but ends in mate (stable).
MATE_FEN = "6k1/5ppp/8/8/8/8/8/3R2K1 w - - 0 1"

BELOW_CAP_RATING = 1500


def raw_miss(**overrides: object) -> RawCandidate:
    """A raw candidate for the MISS_FEN position (a pure miss of 9)."""
    fields: dict[str, object] = {
        "game_id": 5001,
        "ply": 0,
        "pgn": MISS_PGN,
        "platform": "lichess",
        "time_control_bucket": "blitz",
        "time_control_str": "300+0",
        "mover_rating": BELOW_CAP_RATING,
        "best_pv": MISS_BEST_PV,
        "best_move": "e4e7",
        "refutation_pv": MISS_REFUTATION_PV,
    }
    fields.update(overrides)
    return RawCandidate(**fields)


def fake_candidate(
    game_id: int,
    *,
    missed: int | None = 3,
    best_prob: float = 0.2,
    material: MaterialType = "misses",
    best_mate_ply: int | None = None,
) -> MissCandidate:
    """A derived candidate for the sheet / stratification tests (no board needed)."""
    return MissCandidate(
        game_id=game_id,
        ply=20,
        mover_rating=1400,
        move_san="Nf3",
        pinned_elo=1400.0,
        played_3=0,
        best_3=missed,
        missed=missed,
        played_mate_ply=None,
        best_mate_ply=best_mate_ply,
        best_prob=best_prob,
        pre_spread=6.5,
        material=material,
    )


def test_candidate_pipeline_on_fake_rows() -> None:
    """A fake row goes through line facts, material_type and a fake policy into a candidate."""
    tally = Tally()
    board = chess.Board(MISS_FEN)

    candidate = build_candidate(raw_miss(), board, MISS_PLAYED, fake_full_policy, tally)

    assert candidate is not None
    assert (candidate.played_3, candidate.best_3, candidate.missed) == (0, 9, 9)
    assert candidate.material == "misses"
    assert candidate.move_san == "Qa8+"
    assert candidate.mover_rating == BELOW_CAP_RATING
    # fake_full_policy weights the sorted UCIs n, n-1, ..., 1: e4e7 is one of Qe4's moves.
    expected_policy = fake_full_policy(board.fen(), 0.0)
    assert candidate.best_prob == expected_policy["e4e7"]
    assert candidate.pre_spread > 1.0
    assert tally.by_type["misses"] == 1
    assert tally.stable == 1
    assert board.fen() == MISS_FEN  # the pre-board is never mutated

    # The same row through the PGN replay path of collect_candidates.
    tally = Tally()
    collected = collect_candidates(
        [raw_miss()], excluded_games=set(), max_rating=2000, policy_fn=fake_full_policy, tally=tally
    )
    assert [(c.game_id, c.ply, c.missed) for c in collected] == [(5001, 0, 9)]


def test_blind_sheet_has_no_values(tmp_path: Path) -> None:
    rows = [Selected(fake_candidate(77, missed=3), "3-4 / hard"), Selected(fake_candidate(78), "x")]
    sheet = tmp_path / "sheet.tsv"

    write_blind_tsv(rows, sheet)

    with sheet.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        records = list(reader)
        assert tuple(reader.fieldnames or ()) == BLIND_COLUMNS
    assert BLIND_COLUMNS == ("n", "set", "elo", "move", "link", "label")
    assert [record["n"] for record in records] == ["1", "2"]
    assert all(record["label"] == "" for record in records)
    assert all(record["set"] == MISS_SET_ID == "7" for record in records)
    assert records[0]["link"] == "https://flawchess.com/analysis?game_id=77&ply=20"
    assert records[0]["elo"] == "1400"
    assert records[0]["move"] == "Nf3"
    text = sheet.read_text()
    for hidden in ("0.2", "6.5", "stratum", "misses", "3-4", "hard"):
        assert hidden not in text
    # The features script reads the sheet like any label file.
    parsed = parse_labels(sheet)
    assert [(row.set_id, row.game_id, row.ply, row.label) for row in parsed] == [
        ("7", 77, 20, ""),
        ("7", 78, 20, ""),
    ]


def test_key_file_holds_hidden_inputs(tmp_path: Path) -> None:
    rows = [Selected(fake_candidate(77, missed=5, best_prob=0.31), "5-8 / mid")]
    key_path = tmp_path / "nested" / "key.json"

    write_key(rows, key_path)

    key = json.loads(key_path.read_text())
    assert key == {
        "1": {
            "game_id": 77,
            "ply": 20,
            "played_3": 0,
            "best_3": 5,
            "missed": 5,
            "best_prob": 0.31,
            "pre_spread": 6.5,
            "material_type": "misses",
            "stratum": "5-8 / mid",
        }
    }


def test_filters_drop_unstable_and_high_rated() -> None:
    tally = Tally()
    board = chess.Board(MISS_FEN)

    # A 2-ply best line, a 2-ply refutation: dropped as unstable.
    assert (
        build_candidate(raw_miss(best_pv="e4e7 g8h8"), board, MISS_PLAYED, fake_full_policy, tally)
        is None
    )
    assert (
        build_candidate(
            raw_miss(refutation_pv="g8h7 a8e4"), board, MISS_PLAYED, fake_full_policy, tally
        )
        is None
    )
    assert tally.dropped["unstable_line"] == 2
    assert tally.by_type == {}  # an unstable row is not even classified

    # A mover rated at the cap or above, or a game from the exclude TSV, never reaches the replay.
    rows = [
        raw_miss(game_id=1, mover_rating=2000),
        raw_miss(game_id=2, mover_rating=2400),
        raw_miss(game_id=3),
        raw_miss(game_id=4),
    ]
    tally = Tally()
    kept = collect_candidates(
        rows, excluded_games={3}, max_rating=2000, policy_fn=fake_full_policy, tally=tally
    )
    assert [c.game_id for c in kept] == [4]
    assert tally.dropped["rating"] == 2
    assert tally.dropped["excluded_game"] == 1

    # A short line that ends in mate is complete, not truncated: kept.
    assert MIN_STABLE_LINE_PLIES == 3
    assert not is_stable_line("e2e4 e7e5")
    assert is_stable_line("e2e4 e7e5 g1f3")
    assert is_stable_line("d1d8", ends_in_mate=True)
    assert not is_stable_line(None, ends_in_mate=True)
    assert not is_stable_line("")


def test_mate_ended_short_best_line_is_kept() -> None:
    """A one-token best line that mates (Rd8#) is stable and a miss by the best mate."""
    tally = Tally()
    board = chess.Board(MATE_FEN)

    candidate = build_candidate(
        raw_miss(game_id=9, best_pv="d1d8", best_move="d1d8", refutation_pv="h7h6 d2d3 g8h7"),
        board,
        "d1d2",
        fake_full_policy,
        tally,
    )

    assert candidate is not None
    assert candidate.best_mate_ply == 0
    assert candidate.material == "misses"


def test_same_seed_same_sheet(tmp_path: Path) -> None:
    pool = cell_pool(supply=CELL_SUPPLY + 2) + mixed_pool()

    first = stratify(pool, pure_target=40, mixed_target=10, seed=254)
    second = stratify(list(reversed(pool)), pure_target=40, mixed_target=10, seed=254)
    other = stratify(pool, pure_target=40, mixed_target=10, seed=255)
    write_blind_tsv(first.rows, tmp_path / "a.tsv")
    write_blind_tsv(second.rows, tmp_path / "b.tsv")

    assert (tmp_path / "a.tsv").read_text() == (tmp_path / "b.tsv").read_text()
    assert [r.candidate.game_id for r in first.rows] != [r.candidate.game_id for r in other.rows]
    assert sum(r.stratum == MIXED_STRATUM for r in first.rows) == 10
    assert len(first.rows) == 50


def test_summary_line_names_rows_written_and_shortfall() -> None:
    tally = Tally(read=12, stable=9)
    tally.by_type["misses"] = 3
    result = stratify([fake_candidate(1), fake_candidate(2)], pure_target=3, mixed_target=1, seed=1)

    line = summary_line(tally, result)

    assert "rows written 2" in line
    assert "candidates read 12" in line
    assert "unfilled pure 1, mixed 1" in line


def test_help_exits_zero() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/blunder_check/miss_labels.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--sample-percent" in completed.stdout
    assert "--append-to" in completed.stdout
    assert "--mode" in completed.stdout


# ---------------------------------------------------------------------------
# Stratification (Task 2)
# ---------------------------------------------------------------------------

# One best-move probability per tertile; ties inside a tier keep the pool's tertile cuts exact.
TIER_PROBS: tuple[float, ...] = (0.05, 0.3, 0.7)
CELL_SUPPLY = 8


def _bucket_missed(bucket_index: int, i: int) -> tuple[int | None, int | None]:
    """A (missed, best_mate_ply) pair that lands in MISSED_SIZE_BUCKETS[bucket_index]."""
    low, high = MISSED_SIZE_BUCKETS[bucket_index]
    if high is None:
        # The open bucket: big gains and best-line mates (missed None) both belong to it.
        return (None, 2) if i % 4 == 0 else (low + i % 4, None)
    return low + i % (high - low + 1), None


def cell_pool(
    *, skip: Collection[tuple[int, int]] = (), supply: int = CELL_SUPPLY
) -> list[MissCandidate]:
    """Pure misses: `supply` per (size bucket, tertile) cell except the skipped cells."""
    pool: list[MissCandidate] = []
    game_id = 10_000
    for bucket_index in range(len(MISSED_SIZE_BUCKETS)):
        for tier in range(BEST_PROB_TERTILES):
            if (bucket_index, tier) in skip:
                continue
            for i in range(supply):
                missed, mate_ply = _bucket_missed(bucket_index, i)
                game_id += 1
                pool.append(
                    fake_candidate(
                        game_id, missed=missed, best_prob=TIER_PROBS[tier], best_mate_ply=mate_ply
                    )
                )
    return pool


def mixed_pool(count: int = 15) -> list[MissCandidate]:
    return [fake_candidate(90_000 + i, material="loses_and_misses") for i in range(count)]


def test_stratify_spreads_missed_size_and_best_prob() -> None:
    """40 pure misses over the 4 size buckets x 3 tertiles (3 or 4 per cell) plus 10 mixed rows."""
    pool = cell_pool() + mixed_pool()
    cells = len(MISSED_SIZE_BUCKETS) * BEST_PROB_TERTILES

    result = stratify(pool, pure_target=PURE_MISS_TARGET, mixed_target=MIXED_TARGET, seed=254)

    pure = [row for row in result.rows if row.candidate.material == "misses"]
    mixed = [row for row in result.rows if row.stratum == MIXED_STRATUM]
    assert len(pure) == PURE_MISS_TARGET
    assert len(mixed) == MIXED_TARGET
    per_cell = Counter(row.stratum for row in pure)
    assert len(per_cell) == cells
    fair_share = PURE_MISS_TARGET / cells
    assert all(fair_share - 1 < count < fair_share + 1 for count in per_cell.values())
    assert sum(per_cell.values()) == PURE_MISS_TARGET
    # Every size bucket and every best-move difficulty is present.
    sizes = {missed_size_bucket(row.candidate.missed, row.candidate.best_mate_ply) for row in pure}
    assert sizes == set(range(len(MISSED_SIZE_BUCKETS)))
    cuts = tertile_cuts([c.best_prob for c in pool if c.material == "misses"])
    assert {best_prob_tertile(row.candidate.best_prob, cuts) for row in pure} == set(
        range(BEST_PROB_TERTILES)
    )
    assert result.shortfall == {}
    assert (result.unfilled_pure, result.unfilled_mixed) == (0, 0)


def test_stratify_reports_shortfall() -> None:
    """An empty cell is filled from the same size bucket's other cells, and reported."""
    pool = cell_pool(skip={(1, 0)}) + mixed_pool()

    result = stratify(pool, pure_target=PURE_MISS_TARGET, mixed_target=MIXED_TARGET, seed=254)

    pure = [row for row in result.rows if row.candidate.material == "misses"]
    assert len(pure) == PURE_MISS_TARGET
    assert result.unfilled_pure == 0
    ((cell, missing),) = result.shortfall.items()
    assert "3-4" in cell and "hard" in cell
    assert missing >= PURE_MISS_TARGET // 12
    # The replacements stayed inside the 3-4 bucket.
    in_bucket = [
        row
        for row in pure
        if missed_size_bucket(row.candidate.missed, row.candidate.best_mate_ply) == 1
    ]
    assert len(in_bucket) >= 3 * (PURE_MISS_TARGET // 12)
    assert all("hard" not in row.stratum for row in in_bucket)


def test_stratify_reports_a_bucket_without_supply() -> None:
    """A size bucket with no candidates at all stays short and is reported, never padded."""
    pool = cell_pool(skip={(3, 0), (3, 1), (3, 2)}) + mixed_pool(count=4)

    result = stratify(pool, pure_target=PURE_MISS_TARGET, mixed_target=MIXED_TARGET, seed=254)

    pure = [row for row in result.rows if row.candidate.material == "misses"]
    assert len(pure) == PURE_MISS_TARGET - result.unfilled_pure
    assert result.unfilled_pure >= 3 * (PURE_MISS_TARGET // 12)
    assert len(result.shortfall) == BEST_PROB_TERTILES
    assert all("9+" in cell for cell in result.shortfall)
    assert result.unfilled_mixed == MIXED_TARGET - 4


def test_bucket_and_tertile_helpers() -> None:
    assert [missed_size_bucket(m, None) for m in (1, 2, 3, 4, 5, 8, 9, 25)] == [
        0,
        0,
        1,
        1,
        2,
        2,
        3,
        3,
    ]
    # A best-line mate within LINE_DEPTH counts in the open 9+ bucket whatever the material.
    assert missed_size_bucket(None, 2) == 3
    assert missed_size_bucket(1, 0) == 3
    with pytest.raises(ValueError):
        missed_size_bucket(0, None)
    with pytest.raises(ValueError):
        missed_size_bucket(None, None)

    probs = [0.01 * i for i in range(1, 10)]
    cuts = tertile_cuts(probs)
    assert len(cuts) == BEST_PROB_TERTILES - 1
    assert [best_prob_tertile(p, cuts) for p in probs] == [0, 0, 0, 1, 1, 1, 2, 2, 2]


# ---------------------------------------------------------------------------
# Set 8: the disagreement draw (SEED-261115-agg)
# ---------------------------------------------------------------------------

OLD_MAX_N = 240  # the real label file's last n (rows 1-20 and 31-240)


def odd9(*odd: int | None) -> tuple[int | None, ...]:
    """A 9-slot material array from five odd-depth values; even slots copy the previous odd."""
    slots: list[int | None] = []
    for index, value in enumerate(odd):
        slots.append(value)
        if index < len(odd) - 1:
            slots.append(value)
    return tuple(slots)


QUEEN_TRADE_BEST: tuple[int | None, ...] = (1, 1, 1, 1, 10, 10, 1, 1, 1)
ZEROS = odd9(0, 0, 0, 0, 0)


def test_disagreement_group_loss_shapes() -> None:
    def group(*played: int) -> tuple[str, str] | None:
        return disagreement_group(odd9(*played), None, ZEROS, None)

    assert group(-3, 0, 0, 0, 0) == ("loss", "loss_early")  # mean 1.548 vs 0
    assert group(0, 0, -5, -5, -5) == ("loss", "loss_late")  # mean 1.129 vs 0
    assert group(0, 0, -3, -3, -3) == ("loss", "loss_late")  # a piece from depth 5: mean 0.677
    assert group(0, -3, 0, 0, 0) == ("loss", "loss_spike")  # mean 0.774 vs 3
    assert group(0, -3, -3, -3, -3) == ("loss", "loss_other")  # mean 1.452 vs 3
    # Below the 0.5 threshold: a 2 pawn loss from depth 5 (mean 0.452), a one pawn blip at 5.
    assert group(0, 0, -2, -2, -2) is None
    assert group(0, 0, -1, 0, 0) is None
    assert group(0, 0, 0, 0, 0) is None


def test_disagreement_group_miss_shapes() -> None:
    def group(*best: int, best_mate_ply: int | None = None) -> tuple[str, str] | None:
        return disagreement_group(ZEROS, None, odd9(*best), best_mate_ply)

    assert group(3, 0, 0, 0, 0) == ("miss", "miss_early")
    assert group(0, 3, 0, 0, 0) == ("miss", "miss_spike")
    assert group(0, 3, 3, 3, 3) == ("miss", "miss_other")
    assert group(0, 0, 0, 0, 0, best_mate_ply=4) == ("miss", "miss_late")
    # The seed's queen trade: the capped spike at depth 5 moves the mean 0.516, over 0.5.
    assert disagreement_group(ZEROS, None, QUEEN_TRADE_BEST, None) == ("miss", "miss_spike")
    assert group(0, 0, 0, 0, 0) is None


def test_a_loss_whose_only_disagreement_is_the_gain_is_not_drawn() -> None:
    played = odd9(-1, -1, -1, -1, -1)
    assert disagreement_group(played, None, odd9(0, 3, 3, 3, 3), None) is None


def disagreement_candidate(
    game_id: int,
    played: Sequence[int | None],
    best: Sequence[int | None],
    *,
    played_mate_ply: int | None = None,
    best_mate_ply: int | None = None,
    best_prob: float = 0.2,
    material: MaterialType = "misses",
    missed: int | None = 3,
) -> MissCandidate:
    """A candidate carrying material arrays (depth-3 fields are the arrays' depth-3 slots)."""
    return MissCandidate(
        game_id=game_id,
        ply=20,
        mover_rating=1400 + game_id % 7,
        move_san="Nf3",
        pinned_elo=1400.0,
        played_3=played[2],
        best_3=best[2],
        missed=missed,
        played_mate_ply=played_mate_ply,
        best_mate_ply=best_mate_ply,
        best_prob=best_prob,
        pre_spread=6.5,
        material=material,
        played_material=tuple(played),
        best_material=tuple(best),
    )


def test_build_candidate_modes_and_arrays() -> None:
    board = chess.Board(MISS_FEN)
    expected_played = line_facts(board, MISS_PLAYED, MISS_REFUTATION_PV).material_array()
    expected_best = best_line_facts(board, MISS_BEST_PV).material_array()

    default = build_candidate(raw_miss(), board, MISS_PLAYED, fake_full_policy, Tally())
    disagreement = build_candidate(
        raw_miss(), board, MISS_PLAYED, fake_full_policy, Tally(), mode="disagreement"
    )

    assert default is not None and disagreement is not None
    assert (default.played_3, default.best_3, default.material) == (0, 9, "misses")
    assert disagreement.played_material == tuple(expected_played)
    assert disagreement.best_material == tuple(expected_best)
    assert (disagreement.played_3, disagreement.best_3) == (0, 9)


def tracer_pool() -> list[MissCandidate]:
    """At least one candidate per loss and miss stratum plus depth-3 pure misses."""
    pool: list[MissCandidate] = []
    game_id = 20_000
    loss_shapes = [(-3, 0, 0, 0, 0), (0, 0, -5, -5, -5), (0, -3, 0, 0, 0), (0, -3, -3, -3, -3)]
    miss_shapes = [(3, 0, 0, 0, 0), (0, 3, 0, 0, 0), (0, 3, 3, 3, 3)]
    for shape in loss_shapes:
        for _ in range(3):
            game_id += 1
            pool.append(
                disagreement_candidate(game_id, odd9(*shape), ZEROS, material="loses", missed=None)
            )
    for shape in miss_shapes:
        for _ in range(3):
            game_id += 1
            pool.append(disagreement_candidate(game_id, ZEROS, odd9(*shape)))
    for _ in range(3):
        game_id += 1
        pool.append(disagreement_candidate(game_id, ZEROS, ZEROS, best_mate_ply=4, missed=None))
    for i in range(12):
        game_id += 1
        pool.append(fake_candidate(game_id, missed=1 + i % 3, best_prob=TIER_PROBS[i % 3]))
    return pool


def sets_one_to_seven_copy(target: Path) -> bytes:
    """Copy the real label file's header and rows of sets 1-7 byte for byte (set 8 may follow)."""
    kept = [
        line
        for index, line in enumerate(REAL_LABELS.read_bytes().splitlines(keepends=True))
        if index == 0 or line.split(b"\t")[1] in {b"1", b"2", b"3", b"4", b"5", b"6", b"7"}
    ]
    target.write_bytes(b"".join(kept))
    return target.read_bytes()


def test_set_eight_tracer_appends_blind_rows_byte_identically(tmp_path: Path) -> None:
    """Pool -> stratify -> key -> append into a copy of sets 1-7 of the real label file."""
    target = tmp_path / "labels.tsv"
    before = sets_one_to_seven_copy(target)
    assert before.endswith(b"\n")

    draw = stratify_disagreement(tracer_pool(), plain_target=4, seed=7)
    numbers = append_blind_rows(draw.rows, target, set_id=DISAGREEMENT_SET_ID)
    write_key(draw.rows, tmp_path / "key.json", numbers=numbers, set_id=DISAGREEMENT_SET_ID)

    after = target.read_bytes()
    assert after.startswith(before)  # every old byte is unchanged
    assert numbers == list(range(OLD_MAX_N + 1, OLD_MAX_N + 1 + len(draw.rows)))
    new_lines = after[len(before) :].decode().splitlines()
    assert len(new_lines) == len(draw.rows) > 0
    for n, line, row in zip(numbers, new_lines, draw.rows, strict=True):
        fields = line.split("\t")
        assert len(fields) == 14  # no comment cell
        assert fields[:5] == [
            str(n),
            "8",
            str(row.candidate.mover_rating),
            row.candidate.move_san,
            f"https://flawchess.com/analysis?game_id={row.candidate.game_id}&ply=20",
        ]
        assert line.endswith("\t" * 9)  # eight hidden columns and the label, all empty
        assert all(cell == "" for cell in fields[5:])
    parsed = [r for r in parse_labels(target) if r.set_id == "8"]
    assert [int(r.n) for r in parsed] == numbers
    assert {r.label for r in parsed} == {""}

    key = json.loads((tmp_path / "key.json").read_text())
    assert sorted(key, key=int) == [str(n) for n in numbers]
    for n, row in zip(numbers, draw.rows, strict=True):
        entry = key[str(n)]
        assert entry["set"] == "8"
        assert (entry["game_id"], entry["stratum"]) == (row.candidate.game_id, row.stratum)
        assert entry["group"] == row.group
        assert entry["played_material"] == list(row.candidate.played_material)
    # The tracer draws every group and every loss stratum it had supply for.
    assert {row.group for row in draw.rows} == {"loss", "miss", "plain"}
    assert {row.stratum for row in draw.rows if row.group == "loss"} == set(LOSS_STRATUM_QUOTAS)
