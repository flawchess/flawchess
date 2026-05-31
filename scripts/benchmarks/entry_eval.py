"""Shared two-pass phase-entry eval machinery (SKILL.md §2.1 and §3.1.2).

Both the middlegame-entry (§2.1, phase 1) and endgame-entry (§3.1.2, phase 2) eval
subchapters use the identical two-pass symmetric-baseline recipe; only the `phase`
code and a few presentation details differ. This module owns the single
implementation so the cohort/equal-footing/trim logic cannot drift between them.

Pass 1 — symmetric engine baseline at phase entry, deduped to physical games, NO
         equal-footing filter (production-realistic regime). One white-POV number;
         the symmetric baseline is +X / −X (live `EVAL_BASELINE_CP_WHITE`).
Pass 2 — per-(user, color) signed mean eval at phase entry, over the cohort's
         selected-TC games (equal-footing filtered, sub-800 dropped, ≥20 plies per
         (user, color) cell). The `per_user_color` CTE this builds is then centered
         on the pass-1 baseline (and, for §3.1.2, also read uncentered) by the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import sql
from scripts.benchmarks.render import fmt_int, fmt_signed, fmt_unsigned, markdown_table

# Name of the per-(user, color) CTE that `per_user_color_with` terminates on. Callers
# append `, <derived> AS (... FROM per_user_color ...) SELECT ...`.
PER_USER_COLOR_CTE = "per_user_color"


class Baseline(TypedDict):
    n_games: int
    baseline_cp_white: float
    median_white_pov: float
    sd_white_pov: float
    centering_cp: float  # round(baseline) — the symmetric ±constant pass 2 centers on


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


async def baseline(session: AsyncSession, phase: int) -> Baseline:
    """Pass 1 — deduped symmetric engine baseline at `phase` entry (no equal-footing)."""
    row = (
        await _fetch(
            session,
            "WITH first_phase AS (\n"
            "  SELECT game_id, MIN(ply) AS entry_ply FROM game_positions\n"
            f"  WHERE phase = {phase} GROUP BY game_id\n"
            "),\n"
            "phase_entry AS (\n"
            "  SELECT g.platform, g.platform_game_id, gp.eval_cp AS raw_cp_white_pov\n"
            "  FROM games g\n"
            "  JOIN first_phase fp ON fp.game_id = g.id\n"
            "  JOIN game_positions gp ON gp.game_id = g.id AND gp.ply = fp.entry_ply\n"
            "  WHERE g.rated AND NOT g.is_computer_game\n"
            "    AND gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL\n"
            f"    AND abs(gp.eval_cp) < {sql.EVAL_OUTLIER_TRIM_CP}\n"
            "),\n"
            "deduped AS (\n"
            "  SELECT DISTINCT ON (platform, platform_game_id) raw_cp_white_pov\n"
            "  FROM phase_entry ORDER BY platform, platform_game_id\n"
            ")\n"
            "SELECT COUNT(*) AS n_games,\n"
            "  ROUND(AVG(raw_cp_white_pov)::numeric, 2) AS baseline_cp_white,\n"
            "  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY raw_cp_white_pov)::numeric, 1) AS median_white_pov,\n"
            "  ROUND(STDDEV_SAMP(raw_cp_white_pov)::numeric, 1) AS sd_white_pov\n"
            "FROM deduped",
        )
    )[0]
    baseline_cp = float(row["baseline_cp_white"])
    return Baseline(
        n_games=int(row["n_games"]),
        baseline_cp_white=baseline_cp,
        median_white_pov=float(row["median_white_pov"]),
        sd_white_pov=float(row["sd_white_pov"]),
        centering_cp=float(
            round(baseline_cp)
        ),  # symmetric ±constant (= live EVAL_BASELINE_CP_WHITE)
    )


def per_user_color_with(phase: int) -> str:
    """Pass-2 WITH clause through the `per_user_color` CTE for `phase` entry.

    Emits one row per (user, game-time ELO bucket, TC, color) with `mean_signed_cp` =
    the user-POV signed mean entry eval over their equal-footing selected-TC games
    (sub-800 dropped, ≥{EVAL_CONFIDENCE_MIN_N} plies per cell). Sparse-cell exclusion
    is NOT applied here — the caller applies it on the derived (centered/uncentered)
    CTE. Returns a WITH clause with no trailing comma; append `, <derived> AS (...)`.
    """
    bucket_case = sql.elo_bucket_case_sql("gf.ueag")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        "first_entry AS (\n"
        f"  SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = {phase} GROUP BY game_id\n"
        "),\n"
        "games_filtered AS (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc\n"
        "  FROM games g JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "entry_rows AS (\n"
        f"  SELECT gf.user_id, ({bucket_case}) AS elo_bucket, gf.tc, gf.user_color, gp.eval_cp AS raw_cp\n"
        "  FROM games_filtered gf\n"
        "  JOIN first_entry fe ON fe.game_id = gf.game_id\n"
        "  JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fe.entry_ply\n"
        f"  WHERE gf.ueag >= {sql.ELO_FLOOR}\n"
        "    AND gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL\n"
        f"    AND abs(gp.eval_cp) < {sql.EVAL_OUTLIER_TRIM_CP}\n"
        "),\n"
        f"{PER_USER_COLOR_CTE} AS (\n"
        "  SELECT user_id, elo_bucket, tc, user_color,\n"
        "         avg(CASE WHEN user_color = 'white' THEN raw_cp ELSE -raw_cp END) AS mean_signed_cp\n"
        "  FROM entry_rows GROUP BY user_id, elo_bucket, tc, user_color\n"
        f"  HAVING count(*) >= {sql.EVAL_CONFIDENCE_MIN_N}\n"
        ")"
    )


def centered_expr(centering_cp: float) -> str:
    """Signed-mean centered on the symmetric baseline (SKILL.md §2.1 / §3.1.2)."""
    return f"mean_signed_cp - (CASE WHEN user_color = 'white' THEN {centering_cp} ELSE -{centering_cp} END)"


def baseline_table(b: Baseline) -> str:
    """Pass-1 symmetric-baseline table (shared §2.1 / §3.1.2 layout)."""
    headers = ["n_games", "baseline_cp_white", "median_white_pov", "sd_white_pov"]
    row = [
        fmt_int(b["n_games"]),
        f"**{fmt_signed(b['baseline_cp_white'], 2)}**",
        fmt_signed(b["median_white_pov"], 1),
        fmt_unsigned(b["sd_white_pov"], 1),
    ]
    return markdown_table(headers, [row], ("right",) * 4)
