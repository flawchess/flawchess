"""Spike 007: facepalm facts of a rating-stratified sample of Lichess puzzles.

Every Lichess puzzle is a real-game blunder (``Moves[0]``, played from the published FEN)
followed by its punishment (``Moves[1:]``). This script samples puzzles with a settled rating,
evenly over rating bins, and computes the stored facepalm facts with the app's own functions:

- loss view (the blunderer's side): ``line_facts(pre_board, Moves[0], Moves[1:])``, the Maia
  probability of the blunder and the reply spread one ply later;
- miss view (the solver's side): ``best_line_facts(post_board, Moves[1:])`` and the Maia
  probability of the punishing move ``Moves[1]`` (the same policy call as the reply spread).

Two Maia policy calls per puzzle (before and after the blunder) at one fixed Elo.

Usage::

    uv run --group maia-inference python \
        .planning/spikes/007-facepalm-vs-puzzle-ratings/build_features.py \
        --puzzle-path ~/Downloads/lichess_db_puzzle.csv.zst --elo 1500 \
        --out .planning/spikes/007-facepalm-vs-puzzle-ratings/features-elo1500.tsv.gz
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import io
import json
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

import chess
import zstandard as zstd

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from app.services import maia_engine  # noqa: E402
from app.services.line_material import best_line_facts, line_facts  # noqa: E402
from app.services.maia_flaw_stats import reply_spread  # noqa: E402

# A puzzle rating counts as settled below this Glicko-2 deviation and above this play count.
MAX_RATING_DEVIATION: int = 80
MIN_PLAYS: int = 200
# Rating bins: [RATING_MIN, RATING_MIN + BIN_WIDTH), ..., the outer bins are open-ended.
RATING_MIN: int = 500
RATING_MAX: int = 2900
BIN_WIDTH: int = 100
DEFAULT_SAMPLE: int = 30_000
DEFAULT_SEED: int = 261117
DEFAULT_WORKERS: int = 12
CHUNK_SIZE: int = 64
MATERIAL_SLOTS: int = 9

COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "rating",
    "rating_deviation",
    "nb_plays",
    "popularity",
    "themes",
    "n_moves",
    "elo",
    "played_prob",
    "pre_spread",
    "reply_spread",
    "punish_prob",
    "post_legal_moves",
    "punish_is_capture",
    "punish_is_check",
    *(f"played_mat_{d}" for d in range(1, MATERIAL_SLOTS + 1)),
    "mate_ply",
    *(f"best_mat_{d}" for d in range(1, MATERIAL_SLOTS + 1)),
    "best_mate_ply",
)


def _bin_of(rating: int) -> int:
    clipped = min(max(rating, RATING_MIN), RATING_MAX - 1)
    return (clipped - RATING_MIN) // BIN_WIDTH


def sample_puzzles(path: Path, total: int, seed: int) -> list[dict[str, str]]:
    """Reservoir-sample the settled puzzles evenly over the rating bins (one pass, seeded)."""
    n_bins = (RATING_MAX - RATING_MIN) // BIN_WIDTH
    per_bin = total // n_bins
    rng = random.Random(seed)
    reservoirs: list[list[dict[str, str]]] = [[] for _ in range(n_bins)]
    seen = [0] * n_bins
    with path.open("rb") as raw:
        text = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(raw), encoding="utf-8")
        for row in csv.DictReader(text):
            if int(row["RatingDeviation"]) > MAX_RATING_DEVIATION:
                continue
            if int(row["NbPlays"]) < MIN_PLAYS:
                continue
            b = _bin_of(int(row["Rating"]))
            seen[b] += 1
            if len(reservoirs[b]) < per_bin:
                reservoirs[b].append(row)
                continue
            slot = rng.randrange(seen[b])
            if slot < per_bin:
                reservoirs[b][slot] = row
    rows = [row for reservoir in reservoirs for row in reservoir]
    rng.shuffle(rows)
    print(
        json.dumps({"settled_per_bin": seen, "sampled": len(rows), "per_bin": per_bin}),
        file=sys.stderr,
    )
    return rows


def _init_worker() -> None:
    asyncio.run(maia_engine.start_maia(intra_op_num_threads=1))
    if not maia_engine.is_maia_available():
        raise RuntimeError("Maia session unavailable (run with --group maia-inference)")


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def compute_row(job: tuple[dict[str, str], float]) -> list[str] | None:
    """The feature cells of one puzzle, or None when the puzzle does not replay."""
    row, elo = job
    moves = row["Moves"].split()
    if len(moves) < 2:
        return None
    pre_board = chess.Board(row["FEN"])
    try:
        blunder = chess.Move.from_uci(moves[0])
        punish = chess.Move.from_uci(moves[1])
    except ValueError:
        return None
    if blunder not in pre_board.legal_moves:
        return None
    post_board = pre_board.copy(stack=False)
    post_board.push(blunder)
    if punish not in post_board.legal_moves:
        return None
    pre_policy = maia_engine.full_policy(pre_board.fen(), elo)
    post_policy = maia_engine.full_policy(post_board.fen(), elo)
    if not pre_policy or not post_policy:
        return None
    solution = " ".join(moves[1:])
    played = line_facts(pre_board, moves[0], solution)
    best = best_line_facts(post_board, solution)
    values: list[object] = [
        row["PuzzleId"],
        row["Rating"],
        row["RatingDeviation"],
        row["NbPlays"],
        row["Popularity"],
        row["Themes"],
        len(moves),
        elo,
        pre_policy.get(moves[0]),
        reply_spread(pre_policy),
        reply_spread(post_policy),
        post_policy.get(moves[1]),
        post_board.legal_moves.count(),
        post_board.is_capture(punish),
        post_board.gives_check(punish),
        *played.material_array(),
        played.mate_ply,
        *best.material_array(),
        best.opponent_mate_ply,
    ]
    return [_cell(value) for value in values]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puzzle-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--elo", type=float, default=1500.0)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--limit", type=int, default=None, help="first N of the shuffled sample")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()

    rows = sample_puzzles(args.puzzle_path.expanduser(), args.sample, args.seed)
    if args.limit is not None:
        rows = rows[: args.limit]
    started = time.monotonic()
    written = 0
    skipped = 0
    jobs = [(row, args.elo) for row in rows]
    with (
        mp.get_context("spawn").Pool(args.workers, initializer=_init_worker) as pool,
        gzip.open(args.out, "wt", encoding="utf-8", newline="") as handle,
    ):
        handle.write("\t".join(COLUMNS) + "\n")
        for done, cells in enumerate(pool.imap(compute_row, jobs, chunksize=CHUNK_SIZE), start=1):
            if cells is None:
                skipped += 1
            else:
                handle.write("\t".join(cells) + "\n")
                written += 1
            if done % 2000 == 0:
                elapsed = time.monotonic() - started
                print(f"{done}/{len(jobs)} in {elapsed:.0f}s", file=sys.stderr, flush=True)
    summary = {
        "out": str(args.out),
        "elo": args.elo,
        "written": written,
        "skipped": skipped,
        "seconds": round(time.monotonic() - started, 1),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
