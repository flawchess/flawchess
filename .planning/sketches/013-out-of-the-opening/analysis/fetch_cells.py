"""One-off: per-(user, game-time ELO, TC, color) MG-entry eval cell aggregates.

Same cohort recipe as benchmark §2.1 (entry_eval.per_user_color_with): selected users,
equal-footing, sub-800 drop, mate / |cp|>=2000 trim, centred on the symmetric ±25 cp
baseline. Adds within-cell SD, one-sided tail rates, mean win-chance and the actual
score so we can judge which player-level opening metric discriminates.

Run: uv run python .planning/sketches/013-out-of-the-opening/analysis/fetch_cells.py
"""

from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import db_url_for_target  # noqa: E402
from scripts.benchmarks import sql  # noqa: E402

CENTER_CP = 25
TAILS = (100, 200)
MIN_N = 20
OUT = Path(__file__).parent / "cells.csv"


def build_sql() -> str:
    bucket_case = sql.elo_bucket_case_sql("gf.ueag")
    centred = f"(CASE WHEN gf.user_color = 'white' THEN gp.eval_cp - {CENTER_CP} ELSE -gp.eval_cp + {CENTER_CP} END)"
    signed = "(CASE WHEN gf.user_color = 'white' THEN gp.eval_cp ELSE -gp.eval_cp END)"
    tail_cols = ",\n".join(
        f"  avg(CASE WHEN c <= -{t} THEN 1.0 ELSE 0.0 END) AS down{t},\n"
        f"  avg(CASE WHEN c >= {t} THEN 1.0 ELSE 0.0 END) AS up{t}"
        for t in TAILS
    )
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        "first_entry AS (\n"
        f"  SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = {sql.MIDDLEGAME_PHASE} GROUP BY game_id\n"
        "),\n"
        "games_filtered AS (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc, ({sql.USER_SCORE_EXPR}) AS score\n"
        "  FROM games g JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "rows AS (\n"
        f"  SELECT gf.user_id, ({bucket_case}) AS elo_bucket, gf.tc, gf.user_color, gf.score,\n"
        f"         {centred} AS c, {sql.win_chances_sigmoid_sql(signed)} AS wc\n"
        "  FROM games_filtered gf\n"
        "  JOIN first_entry fe ON fe.game_id = gf.game_id\n"
        "  JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fe.entry_ply\n"
        f"  WHERE gf.ueag >= {sql.ELO_FLOOR}\n"
        "    AND gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL\n"
        f"    AND abs(gp.eval_cp) < {sql.EVAL_OUTLIER_TRIM_CP}\n"
        ")\n"
        "SELECT user_id, elo_bucket, tc, user_color, count(*) AS n,\n"
        "  avg(c) AS mean_c, stddev_samp(c) AS sd_c, avg(wc) AS mean_wc, avg(score) AS score,\n"
        f"{tail_cols}\n"
        f"FROM rows WHERE {sql.SPARSE_CELL_EXCLUSION.replace('elo_bucket', 'elo_bucket')}\n"
        "GROUP BY user_id, elo_bucket, tc, user_color\n"
        f"HAVING count(*) >= {MIN_N}"
    )


async def main() -> None:
    engine = create_async_engine(db_url_for_target("benchmark"))
    async with engine.connect() as conn:
        await conn.execute(text("SET TRANSACTION READ ONLY"))
        result = await conn.execute(text(build_sql()))
        rows = result.mappings().all()
    await engine.dispose()
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int) else v) for k, v in r.items()})
    print(f"{len(rows)} cells -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
