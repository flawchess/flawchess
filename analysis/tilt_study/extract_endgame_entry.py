"""One-off extraction: eval at endgame entry (first phase=2 ply) per game, cached as parquet.

Used by the loss-anatomy section of the tilt story: was the previous loss a blown
winning endgame, a lost endgame, or a game that never reached an endgame? The eval
is taken from the entry-lane rows (SEED-145 convention: eval_cp at the entry ply is
the eval of that position, white-positive). Endgame-entry eval coverage is ~100%
over endgame-reaching games (benchmarks §1).

Run: uv run --project analysis python analysis/tilt_study/extract_endgame_entry.py
"""

import sys
import time
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from analysis import db  # noqa: E402  (sys.path insert above must run first)

OUT = REPO / "analysis/out/tilt/endgame_entry.parquet"
MATE_CP = 10_000
SQL = """
WITH e AS (
  SELECT game_id, MIN(ply) AS eg_ply
  FROM game_positions
  WHERE game_id BETWEEN %s AND %s AND phase = 2
  GROUP BY game_id
)
SELECT e.game_id, e.eg_ply,
       CASE WHEN p.eval_cp IS NOT NULL THEN p.eval_cp
            WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate)::int * %s END AS eg_cp
FROM e JOIN game_positions p ON p.game_id = e.game_id AND p.ply = e.eg_ply
"""
t0 = time.time()
with db.connect("benchmark") as conn:
    bounds = conn.execute("SELECT min(id), max(id) FROM games").fetchone()
    if bounds is None or bounds[0] is None:
        raise SystemExit("no games in the benchmark DB")
    lo, hi = bounds
    step = 200_000
    parts = []
    for a in range(lo, hi + 1, step):
        rows = conn.execute(SQL, (a, a + step - 1, MATE_CP)).fetchall()
        parts.append(pl.DataFrame(rows, schema=["game_id", "eg_ply", "eg_cp"], orient="row"))
        print(f"{a}..{a + step - 1} rows={parts[-1].height} t={time.time() - t0:.0f}s", flush=True)
df = pl.concat(parts)
df.write_parquet(OUT)
print(df.describe(), OUT, f"{time.time() - t0:.0f}s")
