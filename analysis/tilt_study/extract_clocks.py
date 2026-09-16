"""One-off extraction: per-game clock endpoints of each side, cached as parquet.

clock_seconds at ply p is the mover's clock after the move (ply 0 = white's first
move, even = white). The end of a game is reconstructed in story_data.py from the
FIRST and LAST recorded clock of each side; the minimum is kept only as a diagnostic.

Bug fixed (methods review 2026-09-16): the first version took min(clock_seconds) per
side as the "last" clock. With an increment a clock rises again after its minimum, so
the minimum overstated the time used in 44% of increment games, which shortened every
break measured from the end of such a game and put thousands of negative gaps into the
under-a-minute break cells. The last clock is now taken by ply order.

Run: uv run --project analysis python analysis/tilt_study/extract_clocks.py
"""

import json
import sys
import time
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from analysis import db  # noqa: E402  (sys.path insert above must run first)

OUT = REPO / "analysis/out/tilt/clock_ends.parquet"
EXTRACT_VERSION = 2  # 1 = minimum clocks (buggy), 2 = ordered first/last clocks
CHUNK = 100_000
SQL = """
SELECT game_id,
       max(ply) FILTER (WHERE clock_seconds IS NOT NULL) AS last_ply,
       (array_agg(clock_seconds ORDER BY ply DESC)
          FILTER (WHERE ply %% 2 = 0 AND clock_seconds IS NOT NULL))[1] AS w_last_clk,
       (array_agg(clock_seconds ORDER BY ply DESC)
          FILTER (WHERE ply %% 2 = 1 AND clock_seconds IS NOT NULL))[1] AS b_last_clk,
       count(clock_seconds) AS n_clk,
       max(clock_seconds) FILTER (WHERE ply = 0) AS w_first_clk,
       max(clock_seconds) FILTER (WHERE ply = 1) AS b_first_clk,
       min(clock_seconds) FILTER (WHERE ply %% 2 = 0) AS w_min_clk,
       min(clock_seconds) FILTER (WHERE ply %% 2 = 1) AS b_min_clk
FROM game_positions
WHERE game_id BETWEEN %s AND %s
GROUP BY game_id
"""
SCHEMA = [
    "game_id",
    "last_ply",
    "w_last_clk",
    "b_last_clk",
    "n_clk",
    "w_first_clk",
    "b_first_clk",
    "w_min_clk",
    "b_min_clk",
]


def main() -> None:
    t0 = time.time()
    with db.connect("benchmark") as conn:
        # fetchone() is Optional per DB-API, so ty rejects unpacking it directly.
        # An aggregate-only SELECT always returns exactly one row, but the bounds
        # are NULL when games is empty — both cases mean "nothing to extract".
        bounds = conn.execute("SELECT min(id), max(id) FROM games").fetchone()
        if bounds is None or bounds[0] is None:
            raise SystemExit("no games in the benchmark DB — nothing to extract")
        lo, hi = bounds
        parts = []
        for a in range(lo, hi + 1, CHUNK):
            rows = conn.execute(SQL, (a, a + CHUNK - 1)).fetchall()
            parts.append(pl.DataFrame(rows, schema=SCHEMA, orient="row"))
            print(
                f"{a}..{a + CHUNK - 1} rows={parts[-1].height} t={time.time() - t0:.0f}s",
                flush=True,
            )
    df = pl.concat(parts)
    tmp = OUT.with_suffix(".tmp.parquet")
    df.write_parquet(tmp)
    tmp.replace(OUT)
    OUT.with_suffix(".json").write_text(
        json.dumps(
            {"version": EXTRACT_VERSION, "rows": df.height, "endpoints": "first/last by ply"},
            indent=2,
        )
    )
    print(df.describe(), OUT, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
