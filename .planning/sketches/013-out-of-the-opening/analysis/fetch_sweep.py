"""Threshold sweep for worse/better-out-of-the-opening rates, counting games that end in
the opening (resign/mate/timeout by result) and mate evals at MG entry.
Run: uv run python .planning/sketches/013-out-of-the-opening/analysis/fetch_sweep.py"""
from __future__ import annotations
import asyncio, csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from app.core.config import db_url_for_target  # noqa: E402
from scripts.benchmarks import sql  # noqa: E402

CENTER_CP = 25
BIG = 100000
THRESHOLDS = (50, 75, 100, 150, 200, 300)
DECISIVE_TERMINATIONS = "('resignation','checkmate','timeout')"
OUT = Path(__file__).parent / "sweep_cells.csv"

def build_sql() -> str:
    bucket_case = sql.elo_bucket_case_sql("gf.ueag")
    centred = f"(CASE WHEN gf.user_color = 'white' THEN gp.eval_cp - {CENTER_CP} ELSE -gp.eval_cp + {CENTER_CP} END)"
    mate_sign = "(CASE WHEN gf.user_color = 'white' THEN sign(gp.eval_mate) ELSE -sign(gp.eval_mate) END)"
    cols = ",\n".join(
        f"  avg(CASE WHEN c <= -{t} THEN 1.0 ELSE 0.0 END) AS down{t}, avg(CASE WHEN c >= {t} THEN 1.0 ELSE 0.0 END) AS up{t}"
        for t in THRESHOLDS)
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"first_entry AS (SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = {sql.MIDDLEGAME_PHASE} GROUP BY game_id),\n"
        "games_filtered AS (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color, g.termination::text AS term,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc, ({sql.USER_SCORE_EXPR}) AS score\n"
        f"  FROM games g JOIN selected_users su ON su.user_id = g.user_id WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "rows AS (\n"
        f"  SELECT gf.user_id, ({bucket_case}) AS elo_bucket, gf.tc, gf.user_color, gf.score, fe.entry_ply IS NULL AS ended_in_opening,\n"
        "    CASE\n"
        f"      WHEN fe.entry_ply IS NULL THEN CASE WHEN gf.term IN {DECISIVE_TERMINATIONS} AND gf.score = 0 THEN -{BIG}\n"
        f"                                          WHEN gf.term IN {DECISIVE_TERMINATIONS} AND gf.score = 1 THEN {BIG} END\n"
        f"      WHEN gp.eval_mate IS NOT NULL THEN {mate_sign} * {BIG}\n"
        f"      ELSE {centred}\n"
        "    END AS c\n"
        "  FROM games_filtered gf\n"
        "  LEFT JOIN first_entry fe ON fe.game_id = gf.game_id\n"
        "  LEFT JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fe.entry_ply\n"
        f"  WHERE gf.ueag >= {sql.ELO_FLOOR}\n"
        "),\n"
        f"kept AS (SELECT * FROM rows WHERE c IS NOT NULL AND {sql.SPARSE_CELL_EXCLUSION})\n"
        "SELECT user_id, elo_bucket, tc, user_color, count(*) AS n, avg(score) AS score,\n"
        "  avg(ended_in_opening::int) AS ended_in_opening,\n"
        f"  avg(CASE WHEN abs(c) < {sql.EVAL_OUTLIER_TRIM_CP} THEN c END) AS mean_c,\n"
        f"{cols}\n"
        "FROM kept GROUP BY user_id, elo_bucket, tc, user_color HAVING count(*) >= 20"
    )

async def main() -> None:
    engine = create_async_engine(db_url_for_target("benchmark"))
    async with engine.connect() as conn:
        await conn.execute(text("SET TRANSACTION READ ONLY"))
        rows = (await conn.execute(text(build_sql()))).mappings().all()
    await engine.dispose()
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (v if isinstance(v, (int, str)) or v is None else float(v)) for k, v in r.items()})
    print(f"{len(rows)} cells -> {OUT}")

if __name__ == "__main__":
    asyncio.run(main())
