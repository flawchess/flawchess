"""Chapter 2 — Openings (SKILL.md §2). Only metric: §2.1 Middlegame-entry eval.

Two passes (SKILL.md §2.1 "Query"):
  Pass 1 — symmetric engine baseline at MG entry, deduped to physical games, NO
           equal-footing filter (production-realistic regime). Yields one white-POV
           number `BASELINE_CP`; the symmetric baseline is +X / −X.
  Pass 2 — per-(user, color) signed eval at MG entry, centered on the symmetric
           baseline, pooled + marginalized over the game-time (ELO, TC) cells.

Emits the pass-1 baseline row, the pooled centered distribution, ELO + TC marginals,
and the TC/ELO Cohen's d collapse *numbers* (the LLM applies the verdict word).

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

from scripts.benchmarks import sql, stats
from scripts.benchmarks.render import Align, fmt_int, fmt_signed, fmt_unsigned, markdown_table

SECTION = "SKILL.md §2.1 — middlegame-entry eval (symmetric baseline + centered distribution)"


class Baseline(TypedDict):
    n_games: int
    baseline_cp_white: float
    median_white_pov: float
    sd_white_pov: float
    centering_cp: float  # round(baseline) — the symmetric ±constant pass 2 centers on


class Distribution(TypedDict):
    n: int
    mean: float  # SQL-rounded to 2 dp (display half-up rounds to 1 dp)
    sd: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


class Marginal(TypedDict):
    label: str
    dist: Distribution
    mean_raw: float  # unrounded mean, for Cohen's d
    var: float  # var_samp, for Cohen's d


class Verdict(TypedDict):
    axis: str
    max_abs_d: float
    pair: tuple[str, str]


class Chapter2Values(TypedDict):
    baseline: Baseline
    pooled: Distribution
    elo_marginal: list[Marginal]
    tc_marginal: list[Marginal]
    verdicts: list[Verdict]


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


def _f(value: Any) -> float:
    """Coerce a DB numeric (asyncpg Decimal) to float for JSON + stats."""
    return float(value)


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
    baseline_cp = _f(row["baseline_cp_white"])
    return Baseline(
        n_games=int(row["n_games"]),
        baseline_cp_white=baseline_cp,
        median_white_pov=_f(row["median_white_pov"]),
        sd_white_pov=_f(row["sd_white_pov"]),
        centering_cp=float(
            round(baseline_cp)
        ),  # symmetric ±constant (= live EVAL_BASELINE_CP_WHITE)
    )


def _dist(row: RowMapping) -> Distribution:
    return Distribution(
        n=int(row["n"]),
        mean=_f(row["mean"]),
        sd=_f(row["sd"]),
        p05=_f(row["p05"]),
        p25=_f(row["p25"]),
        p50=_f(row["p50"]),
        p75=_f(row["p75"]),
        p95=_f(row["p95"]),
    )


async def _pass2(session: AsyncSession, centering_cp: float) -> Sequence[RowMapping]:
    """Pass 2 — pooled + ELO + TC marginals in one GROUPING SETS scan over centered values."""
    bucket_case = sql.elo_bucket_case_sql("gf.ueag")
    percentiles = ",\n".join(
        f"  round(percentile_cont({p}) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p{int(p * 100):02d}"
        for p in (0.05, 0.25, 0.50, 0.75, 0.95)
    )
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
        "SELECT elo_bucket, tc, count(*) AS n,\n"
        "  round(avg(centered_cp)::numeric, 2) AS mean,\n"
        "  avg(centered_cp) AS mean_raw,\n"
        "  round(stddev_samp(centered_cp)::numeric, 1) AS sd,\n"
        "  var_samp(centered_cp) AS var,\n"
        f"{percentiles}\n"
        "FROM mc GROUP BY GROUPING SETS ((), (elo_bucket), (tc))"
    )
    return await _fetch(session, sql_text)


def _marginal(row: RowMapping, label: str) -> Marginal:
    return Marginal(label=label, dist=_dist(row), mean_raw=_f(row["mean_raw"]), var=_f(row["var"]))


def _verdict(axis: str, marginals: Sequence[Marginal]) -> Verdict:
    levels = [
        stats.LevelStat(m["label"], m["dist"]["n"], m["mean_raw"], m["var"]) for m in marginals
    ]
    result = stats.max_abs_d(levels)
    return Verdict(axis=axis, max_abs_d=result.max_abs_d, pair=result.pair)


async def compute(session: AsyncSession) -> Chapter2Values:
    baseline = await _baseline(session)
    rows = await _pass2(session, baseline["centering_cp"])

    pooled: Distribution | None = None
    elo: list[Marginal] = []
    tc: list[Marginal] = []
    for row in rows:
        if row["elo_bucket"] is not None:
            elo.append(_marginal(row, str(int(row["elo_bucket"]))))
        elif row["tc"] is not None:
            tc.append(_marginal(row, str(row["tc"])))
        else:
            pooled = _dist(row)
    if pooled is None:
        raise RuntimeError("pass-2 GROUPING SETS returned no pooled row")

    elo.sort(key=lambda m: int(m["label"]))
    tc.sort(key=lambda m: sql.TC_ORDER.index(m["label"]))  # type: ignore[arg-type]

    return Chapter2Values(
        baseline=baseline,
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[_verdict("TC", tc), _verdict("ELO", elo)],
    )


# --- rendering -------------------------------------------------------------

_DIST_HEADERS: tuple[str, ...] = ("n", "mean", "SD", "p05", "p25", "p50", "p75", "p95")
_DIST_ALIGNS: tuple[Align, ...] = ("right",) * len(_DIST_HEADERS)


def _dist_cells(d: Distribution, *, suffix: str = "") -> list[str]:
    """n / mean(1dp signed) / SD(1dp) / percentiles(int signed), eval-cp display."""
    return [
        fmt_int(d["n"]),
        f"{fmt_signed(d['mean'], 1)}{suffix}",
        f"{fmt_unsigned(d['sd'], 1)}{suffix}",
        *(f"{fmt_signed(d[k], 0)}{suffix}" for k in ("p05", "p25", "p50", "p75", "p95")),
    ]


def _baseline_table(b: Baseline) -> str:
    headers = ["n_games", "baseline_cp_white", "median_white_pov", "sd_white_pov"]
    row = [
        fmt_int(b["n_games"]),
        f"**{fmt_signed(b['baseline_cp_white'], 2)}**",
        fmt_signed(b["median_white_pov"], 1),
        fmt_unsigned(b["sd_white_pov"], 1),
    ]
    return markdown_table(headers, [row], ("right",) * 4)


def _pooled_table(d: Distribution) -> str:
    return markdown_table(_DIST_HEADERS, [_dist_cells(d, suffix=" cp")], _DIST_ALIGNS)


def _marginal_table(axis_label: str, marginals: Sequence[Marginal]) -> str:
    headers = [axis_label, *_DIST_HEADERS]
    aligns: tuple[Align, ...] = ("right",) * len(headers)
    rows = [[m["label"], *_dist_cells(m["dist"])] for m in marginals]
    return markdown_table(headers, rows, aligns)


def _verdict_block(verdicts: Sequence[Verdict]) -> str:
    lines = ["#### Collapse verdict", ""]
    for v in verdicts:
        a, b = v["pair"]
        lines.append(f"- **{v['axis']} axis**: max |d| = **{v['max_abs_d']:.2f}** ({a} vs {b})")
    return "\n".join(lines)


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
        _pooled_table(values["pooled"]),
        "",
        "##### ELO marginal (centered)",
        "",
        _marginal_table("ELO", values["elo_marginal"]),
        "",
        "##### TC marginal (centered)",
        "",
        _marginal_table("TC", values["tc_marginal"]),
        "",
        _verdict_block(values["verdicts"]),
    ]
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {"status": "OK", "section": SECTION, "values": values, "markdown": render(values)}
