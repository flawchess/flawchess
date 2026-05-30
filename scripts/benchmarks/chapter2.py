"""Chapter 2 — Openings (SKILL.md §2). Only metric: §2.1 Middlegame-entry eval.

Two passes (SKILL.md §2.1 "Query"):
  Pass 1 — symmetric engine baseline at MG entry, deduped to physical games, NO
           equal-footing filter (production-realistic regime). Yields one white-POV
           number `BASELINE_CP`; the symmetric baseline is +X / −X.
  Pass 2 — per-(user, color) signed eval at MG entry, centered on the symmetric
           baseline, pooled + marginalized over the game-time (ELO, TC) cells (the
           shared distribution machinery).

Two faithful-port decisions vs the SKILL.md §2.1 text (both validated against
benchmarks-latest.md):
  - The inline pass-2 SQL omits the canonical sub-800 drop (`user_elo_at_game >= 800`);
    the building-block text requires it and the report was generated with it (pooled
    n=9,109, not 9,215). We apply the drop.
  - The deterministic ELO-axis max |d| is between (800, 1600), not (800, 1200) as the
    prior report stated — a hand-computation pair-selection error. Magnitude (0.09)
    and the `collapse` verdict are unchanged. Footnoted in the report.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql
from scripts.benchmarks.render import fmt_int, fmt_signed, fmt_unsigned, markdown_table

SECTION = "SKILL.md §2.1 — middlegame-entry eval (symmetric baseline + centered distribution)"

# Centered eval is a cp metric: mean at 2 dp (report double-rounds to +3.7), sd/pct at 1 dp.
_CP_DIGITS = 1
_CP_MEAN_DIGITS = 2


class Baseline(TypedDict):
    n_games: int
    baseline_cp_white: float
    median_white_pov: float
    sd_white_pov: float
    centering_cp: float  # round(baseline) — the symmetric ±constant pass 2 centers on


class Chapter2Values(TypedDict):
    baseline: Baseline
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


async def _baseline(session: AsyncSession) -> Baseline:
    """Pass 1 — deduped symmetric engine baseline at MG entry (no equal-footing filter)."""
    row = (
        await _fetch(
            session,
            "WITH first_phase AS (\n"
            "  SELECT game_id, MIN(ply) AS entry_ply FROM game_positions\n"
            f"  WHERE phase = {sql.MIDDLEGAME_PHASE} GROUP BY game_id\n"
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


async def _pass2(session: AsyncSession, centering_cp: float) -> Sequence[RowMapping]:
    """Pass 2 — pooled + ELO + TC marginals in one GROUPING SETS scan over centered values."""
    bucket_case = sql.elo_bucket_case_sql("gf.ueag")
    sql_text = (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        "first_middlegame AS (\n"
        f"  SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = {sql.MIDDLEGAME_PHASE} GROUP BY game_id\n"
        "),\n"
        "games_filtered AS (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc\n"
        "  FROM games g JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "mid_entry AS (\n"
        f"  SELECT gf.user_id, ({bucket_case}) AS elo_bucket, gf.tc, gf.user_color, gp.eval_cp AS raw_cp\n"
        "  FROM games_filtered gf\n"
        "  JOIN first_middlegame fm ON fm.game_id = gf.game_id\n"
        "  JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fm.entry_ply\n"
        f"  WHERE gf.ueag >= {sql.ELO_FLOOR}\n"
        "    AND gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL\n"
        f"    AND abs(gp.eval_cp) < {sql.EVAL_OUTLIER_TRIM_CP}\n"
        "),\n"
        "mid_per_user_color AS (\n"
        "  SELECT user_id, elo_bucket, tc, user_color,\n"
        "         avg(CASE WHEN user_color = 'white' THEN raw_cp ELSE -raw_cp END) AS mean_signed_cp\n"
        "  FROM mid_entry GROUP BY user_id, elo_bucket, tc, user_color\n"
        f"  HAVING count(*) >= {sql.EVAL_CONFIDENCE_MIN_N}\n"
        "),\n"
        "mc AS (\n"
        f"  SELECT mean_signed_cp - (CASE WHEN user_color = 'white' THEN {centering_cp} ELSE -{centering_cp} END) AS centered_cp,\n"
        "         elo_bucket, tc\n"
        f"  FROM mid_per_user_color WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")\n"
        "SELECT\n"
        f"{dist.agg_select('centered_cp', digits=_CP_DIGITS, mean_digits=_CP_MEAN_DIGITS)}\n"
        f"FROM mc {dist.GROUPING_SETS}"
    )
    return await _fetch(session, sql_text)


async def compute(session: AsyncSession) -> Chapter2Values:
    baseline = await _baseline(session)
    rows = await _pass2(session, baseline["centering_cp"])
    pooled, elo, tc = dist.split_grouping_sets(rows)
    return Chapter2Values(
        baseline=baseline,
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


# --- rendering -------------------------------------------------------------


def _baseline_table(b: Baseline) -> str:
    headers = ["n_games", "baseline_cp_white", "median_white_pov", "sd_white_pov"]
    row = [
        fmt_int(b["n_games"]),
        f"**{fmt_signed(b['baseline_cp_white'], 2)}**",
        fmt_signed(b["median_white_pov"], 1),
        fmt_unsigned(b["sd_white_pov"], 1),
    ]
    return markdown_table(headers, [row], ("right",) * 4)


def render(values: Chapter2Values) -> str:
    parts = [
        "## 2. Openings",
        "",
        "### 2.1 Middlegame-entry eval",
        "",
        "#### Pass 1 — symmetric engine baseline (deduped to physical games)",
        "",
        _baseline_table(values["baseline"]),
        "",
        "#### Pass 2 — centered per-(user, color) pooled distribution",
        "",
        "##### Pooled centered distribution",
        "",
        dist.pooled_table(values["pooled"], "cp"),
        "",
        "##### ELO marginal (centered)",
        "",
        dist.marginal_table("ELO", values["elo_marginal"], "cp"),
        "",
        "##### TC marginal (centered)",
        "",
        dist.marginal_table("TC", values["tc_marginal"], "cp"),
        "",
        dist.verdict_block(values["verdicts"]),
    ]
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {"status": "OK", "section": SECTION, "values": values, "markdown": render(values)}
