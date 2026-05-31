"""Chapter 3 §3.3 — Time Pressure (clock pressure, time-pressure-vs-performance, pressure bins).

Ported sub-metrics:
  §3.3.1 Clock pressure at endgame entry — per-user clock-diff %, clock-gap fraction,
    and net-timeout rate over endgame-entry games (≥20 games/user/cell). The three share
    one `routed`/`clean` clock-routing scan; clock-gap is clock-diff expressed as a
    fraction (÷100). Sub-800 dropped, equal-footing filtered, sparse cell excluded.
  §3.3.2 Time-pressure-vs-performance curve — GAME-level per-game score across 10
    clock-remaining time-buckets (0–9). Pooled curve + per-(tb, TC) + per-(tb, ELO)
    marginals; per-time-bucket Cohen's d on the binary per-game score.
  §3.3.3 Chess score per pressure bin — per-user score per (TC × ELO × quintile) cell
    (quintile = clock-%/20, ≥5 games/bin, ≥10 users/cell). Shipped band is per-(TC ×
    quintile) pooling ELO, IQR clamped to ±PRESSURE_BIN_NEUTRAL_CAP.

Faithful-port findings (validated against benchmarks-latest.md 2026-05-27):
  - §3.3.1: clock-diff % + clock-gap fraction + net-timeout pooled and all marginals
    reproduce the report EXACTLY (clock-diff TC 0.24 review (bullet vs classical) /
    ELO 0.17 collapse; net-timeout ELO 0.28 review (800 vs 2400)). Sub-800 + sparse
    exclusion applied (pooled n = 4,604, both marginal axes sum to it). One
    verdict-NEUTRAL slip: net-timeout TC report 0.04 → deterministic 0.09 (blitz vs
    classical), both < 0.2 → collapse.
  - §3.3.2: pooled 10-bucket curve, the full TC marginal, and the ELO marginal reproduce
    the report EXACTLY. Per-tb TC Cohen's d on the per-game score: tb=0 0.39, tb=5 0.14,
    tb=9 0.05 (the report's ≈0.38 / ≈0.13 are 1-ulp-low approximations; verdict words
    review/collapse unchanged). ELO d ≤ 0.16 across all buckets → collapse throughout.
  - §3.3.3: the 20-cell per-(TC × quintile) band table (n_users + p25/p50/p75) reproduces
    the report EXACTLY — this is the actual zone-calibration output. The per-quintile
    collapse VERDICTS, however, do NOT reproduce: the report's d's (≈0.18–0.46) were not
    computed with the documented per-user n/mean/var_samp recipe (they read as eyeballed /
    game-level), whereas the deterministic per-user recipe gives larger values (Q0 TC 0.75,
    Q0 ELO 0.56, Q2 TC 0.46, Q3 ELO 0.34, Q4 ELO 0.31; Q1 TC 0.32 and Q4 TC 0.19 do match).
    The deterministic values are emitted. This is verdict-narrative only — the shipped
    per-(TC × quintile) band design is unaffected (and the larger ELO d's would, if
    anything, argue for the Phase-B per-ELO stratification review, not against the bands).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql, stats
from scripts.benchmarks.render import Align, fmt_int, fmt_signed, fmt_unsigned, markdown_table

SECTION = "SKILL.md §3.3 — time pressure (3.3.1 clock pressure at entry, 3.3.2 pressure-vs-performance curve, 3.3.3 chess score per pressure bin)"

_PCT_DIGITS = 2  # clock-diff % / net-timeout pp: SQL round to 2 dp (report display)
_GAP_DIGITS = 4  # clock-gap fraction

_N_TIME_BUCKETS = 10  # 3.3.2: 10% clock-remaining bins, tb 0–9
_N_QUINTILES = 5  # 3.3.3: 20% clock-remaining bins, Q0–Q4
_CURVE_MIN_GAMES = 100  # 3.3.2 verdict: marginal level must have ≥100 games to count


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


# --- §3.3.1 Clock pressure at endgame entry --------------------------------


class ClockPressure331(TypedDict):
    diff_pooled: dist.Distribution  # clock-diff % (2 dp, percentage)
    diff_elo: list[dist.Marginal]
    diff_tc: list[dist.Marginal]
    diff_verdicts: list[dist.Verdict]
    gap_pooled: dist.Distribution  # clock-gap fraction (4 dp) — same metric ÷100
    gap_tc: list[dist.Marginal]
    net_pooled: dist.Distribution  # net-timeout pp (2 dp)
    net_elo: list[dist.Marginal]
    net_tc: list[dist.Marginal]
    net_verdicts: list[dist.Verdict]


def _clock_pressure_pu_cte() -> str:
    """Per-user clock-diff %, clock-gap fraction, and net-timeout over endgame-entry games.

    Approximates the backend's first-clock-per-parity scan by reading the clocks at the
    first endgame ply and the ply after, routed to user/opponent by color + parity. The
    per-user cell needs ≥20 games; sub-800 dropped, sparse cell excluded.
    """
    elo_case = sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)
    user_clk = sql.clock_routing_case(
        "g.user_color", "fe.entry_ply", "p1.clock_seconds", "p2.clock_seconds"
    )
    opp_clk = sql.clock_routing_case(
        "g.user_color", "fe.entry_ply", "p2.clock_seconds", "p1.clock_seconds"
    )
    # Referenced inside per_user_cell (FROM routed) — routed exposes result/user_color unqualified.
    win = "(result = '1-0' AND user_color = 'white') OR (result = '0-1' AND user_color = 'black')"
    loss = "(result = '1-0' AND user_color = 'black') OR (result = '0-1' AND user_color = 'white')"
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.FIRST_ENDGAME_ENTRY_CTE},\n"
        "clean AS (\n"
        f"  SELECT g.user_id, ({elo_case}) AS elo_bucket, su.tc_bucket AS tc,\n"
        "         g.termination, g.result, g.user_color, g.base_time_seconds,\n"
        f"         ({user_clk}) AS user_clk,\n"
        f"         ({opp_clk}) AS opp_clk\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN first_endgame fe ON fe.game_id = g.id\n"
        "  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply\n"
        "  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "routed AS (\n"
        "  SELECT user_id, elo_bucket, tc, termination, result, user_color,\n"
        "         user_clk, opp_clk, base_time_seconds,\n"
        "         (user_clk - opp_clk) / NULLIF(base_time_seconds, 0) * 100 AS diff_pct\n"
        "  FROM clean\n"
        "  WHERE user_clk IS NOT NULL AND opp_clk IS NOT NULL AND base_time_seconds > 0\n"
        "    AND user_clk <= 2.0 * base_time_seconds AND opp_clk <= 2.0 * base_time_seconds\n"
        "    AND elo_bucket IS NOT NULL\n"
        "),\n"
        "per_user_cell AS (\n"
        "  SELECT user_id, elo_bucket, tc,\n"
        "         avg(diff_pct) AS avg_diff_pct,\n"
        "         avg(diff_pct / 100.0) AS mean_gap_frac,\n"
        f"         (sum(CASE WHEN termination = 'timeout' AND ({win}) THEN 1 ELSE 0 END)\n"
        f"          - sum(CASE WHEN termination = 'timeout' AND ({loss}) THEN 1 ELSE 0 END))::numeric\n"
        "          / count(*) * 100 AS net_pp\n"
        "  FROM routed GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) >= {sql.CLOCK_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user_cell WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute_331(session: AsyncSession) -> ClockPressure331:
    arms = (
        ("diff", "avg_diff_pct", _PCT_DIGITS),
        ("gap", "mean_gap_frac", _GAP_DIGITS),
        ("net", "net_pp", _PCT_DIGITS),
    )
    selects = [
        f"SELECT '{name}' AS metric,\n{dist.agg_select(col, digits=digits)}\n"
        f"FROM pu {dist.GROUPING_SETS}"
        for name, col, digits in arms
    ]
    query = _clock_pressure_pu_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    diff_p, diff_e, diff_t = dist.split_grouping_sets([r for r in rows if r["metric"] == "diff"])
    gap_p, _gap_e, gap_t = dist.split_grouping_sets([r for r in rows if r["metric"] == "gap"])
    net_p, net_e, net_t = dist.split_grouping_sets([r for r in rows if r["metric"] == "net"])
    return ClockPressure331(
        diff_pooled=diff_p,
        diff_elo=diff_e,
        diff_tc=diff_t,
        diff_verdicts=[dist.verdict("TC", diff_t), dist.verdict("ELO", diff_e)],
        gap_pooled=gap_p,
        gap_tc=gap_t,
        net_pooled=net_p,
        net_elo=net_e,
        net_tc=net_t,
        net_verdicts=[dist.verdict("TC", net_t), dist.verdict("ELO", net_e)],
    )


# --- §3.3.2 Time-pressure-vs-performance curve -----------------------------


class CurvePoint(TypedDict):
    tb: int
    n: int
    score: float


class GameLevel(TypedDict):
    n: int
    mean: float
    var: float


class BucketVerdict(TypedDict):
    tb: int
    axis: str
    max_abs_d: float
    pair: tuple[str, str]


class TimeCurve332(TypedDict):
    pooled: list[CurvePoint]  # 10 rows: tb, n_games, pooled score
    tc: dict[int, dict[str, float]]  # tb -> tc -> score
    elo: dict[int, dict[str, float]]  # tb -> elo -> score
    verdicts: list[BucketVerdict]  # per tb, TC + ELO


def _time_curve_query() -> str:
    """GAME-level per-game score by clock-remaining time-bucket, with TC/ELO marginals.

    `user_pct` = user clock at endgame entry as a % of base time; `tb = min(floor/10, 9)`.
    GROUPING SETS over (tb), (tb, tc), (tb, elo) give the pooled curve + both marginals in
    one scan; `var_samp(score)` feeds the per-tb Cohen's d. Sub-800 + sparse excluded.
    """
    elo_case = sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)
    user_clk = sql.clock_routing_case(
        "g.user_color", "fe.entry_ply", "p1.clock_seconds", "p2.clock_seconds"
    )
    score = (
        "CASE WHEN (g.result = '1-0' AND g.user_color = 'white')\n"
        "       OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0\n"
        "     WHEN g.result = '1/2-1/2' THEN 0.5 ELSE 0.0 END"
    )
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.FIRST_ENDGAME_ENTRY_CTE},\n"
        "game_pct AS (\n"
        f"  SELECT ({elo_case}) AS elo_bucket, su.tc_bucket AS tc,\n"
        f"         {score} AS user_score,\n"
        f"         ({user_clk}) / NULLIF(g.base_time_seconds, 0) * 100 AS user_pct\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN first_endgame fe ON fe.game_id = g.id\n"
        "  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply\n"
        "  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER} AND g.base_time_seconds > 0\n"
        "),\n"
        "binned AS (\n"
        f"  SELECT elo_bucket, tc, least(floor(user_pct / 10)::int, {_N_TIME_BUCKETS - 1}) AS tb,\n"
        "         user_score\n"
        "  FROM game_pct\n"
        "  WHERE user_pct IS NOT NULL AND user_pct <= 200\n"
        f"    AND elo_bucket IS NOT NULL AND {sql.SPARSE_CELL_EXCLUSION}\n"
        ")\n"
        "SELECT GROUPING(tc) AS g_tc, GROUPING(elo_bucket) AS g_elo,\n"
        "       tc, elo_bucket, tb, count(*) AS n,\n"
        "       round(avg(user_score)::numeric, 4) AS score,\n"
        "       var_samp(user_score) AS var\n"
        "FROM binned\n"
        "GROUP BY GROUPING SETS ((tb), (tb, tc), (tb, elo_bucket))"
    )


def _curve_verdicts(
    level: dict[int, dict[str, GameLevel]], axis: str, order
) -> list[BucketVerdict]:
    """Per-time-bucket max |d| over the axis levels with ≥`_CURVE_MIN_GAMES` games."""
    out: list[BucketVerdict] = []
    for tb in sorted(level):
        levels = [
            stats.LevelStat(lbl, gl["n"], gl["mean"], gl["var"])
            for lbl in order
            if (gl := level[tb].get(lbl)) is not None and gl["n"] >= _CURVE_MIN_GAMES
        ]
        if len(levels) < 3:  # need ≥3 marginal levels (SKILL.md §3.3.2 verdict rule)
            continue
        r = stats.max_abs_d(levels)
        out.append(BucketVerdict(tb=tb, axis=axis, max_abs_d=r.max_abs_d, pair=r.pair))
    return out


async def compute_332(session: AsyncSession) -> TimeCurve332:
    rows = await _fetch(session, _time_curve_query())
    pooled: list[CurvePoint] = []
    tc_score: dict[int, dict[str, float]] = {}
    elo_score: dict[int, dict[str, float]] = {}
    tc_lvl: dict[int, dict[str, GameLevel]] = {}
    elo_lvl: dict[int, dict[str, GameLevel]] = {}
    for r in rows:
        tb = int(r["tb"])
        gl = GameLevel(n=int(r["n"]), mean=float(r["score"]), var=float(r["var"]))
        if int(r["g_tc"]) == 0:  # (tb, tc) row
            tc_score.setdefault(tb, {})[str(r["tc"])] = float(r["score"])
            tc_lvl.setdefault(tb, {})[str(r["tc"])] = gl
        elif int(r["g_elo"]) == 0:  # (tb, elo) row
            label = str(int(r["elo_bucket"]))
            elo_score.setdefault(tb, {})[label] = float(r["score"])
            elo_lvl.setdefault(tb, {})[label] = gl
        else:  # (tb) pooled row
            pooled.append(CurvePoint(tb=tb, n=int(r["n"]), score=float(r["score"])))
    pooled.sort(key=lambda p: p["tb"])
    verdicts = _curve_verdicts(tc_lvl, "TC", sql.TC_ORDER) + _curve_verdicts(
        elo_lvl, "ELO", [str(a) for a in sql.ELO_ANCHORS]
    )
    return TimeCurve332(pooled=pooled, tc=tc_score, elo=elo_score, verdicts=verdicts)


# --- §3.3.3 Chess score per pressure bin -----------------------------------


class BandCell(TypedDict):
    tc: str
    quintile: int
    n_users: int
    p25: float
    p50: float
    p75: float
    band_lower: float  # max(p25, p50 − cap)
    band_upper: float  # min(p75, p50 + cap)


class QuintileVerdict(TypedDict):
    quintile: int
    axis: str
    max_abs_d: float
    pair: tuple[str, str]


class PressureBin333(TypedDict):
    bands: list[BandCell]  # 4 TC × 5 quintile
    verdicts: list[QuintileVerdict]  # per quintile, TC + ELO


def _pressure_bin_query() -> str:
    """Per-user score per (TC × ELO × quintile), then per-quintile TC + ELO marginals.

    quintile = `min(4, floor(user_clk_pct / 20))`; per-user cell needs ≥5 games, marginal
    cell ≥10 users. Sub-800 + sparse excluded inline (SKILL.md §3.3.3). GROUPING SETS over
    (quintile, tc) and (quintile, elo): the (quintile, tc) rows are BOTH the shipped band
    cells (p25/p50/p75, ELO pooled) and the TC-axis verdict input; (quintile, elo) rows are
    the ELO-axis verdict input.
    """
    elo_case = sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)
    user_clk = sql.clock_routing_case(
        "g.user_color", "fe.entry_ply", "p1.clock_seconds", "p2.clock_seconds"
    )
    score = (
        "CASE WHEN (g.result = '1-0' AND g.user_color = 'white')\n"
        "       OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0\n"
        "     WHEN g.result = '1/2-1/2' THEN 0.5 ELSE 0.0 END"
    )
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.FIRST_ENDGAME_ENTRY_CTE},\n"
        "eg AS (\n"
        f"  SELECT g.user_id, ({elo_case}) AS elo_bucket, su.tc_bucket AS tc,\n"
        f"         ({user_clk}) AS user_clk,\n"
        f"         ({user_clk}) / NULLIF(g.base_time_seconds, 0) * 100 AS user_clk_pct,\n"
        f"         {score} AS score\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN first_endgame fe ON fe.game_id = g.id\n"
        "  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply\n"
        "  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER} AND g.base_time_seconds > 0\n"
        f"    AND ({sql.USER_ELO_AT_GAME_SQL}) >= {sql.ELO_FLOOR}\n"
        f"    AND NOT (({sql.USER_ELO_AT_GAME_SQL}) >= {sql.SPARSE_CELL[0]} AND su.tc_bucket = '{sql.SPARSE_CELL[1]}')\n"
        "),\n"
        "puq AS (\n"
        "  SELECT user_id, elo_bucket, tc,\n"
        f"         LEAST({_N_QUINTILES - 1}, FLOOR(user_clk_pct / 20.0)::int) AS quintile,\n"
        "         avg(score) AS user_score\n"
        "  FROM eg WHERE user_clk IS NOT NULL AND user_clk_pct BETWEEN 0 AND 200\n"
        f"  GROUP BY user_id, elo_bucket, tc, LEAST({_N_QUINTILES - 1}, FLOOR(user_clk_pct / 20.0)::int)\n"
        f"  HAVING count(*) >= {sql.PRESSURE_BIN_MIN_GAMES}\n"
        ")\n"
        "SELECT quintile, GROUPING(tc) AS g_tc, tc, elo_bucket,\n"
        "       count(*) AS n_users,\n"
        "       round(avg(user_score)::numeric, 4) AS mean, var_samp(user_score) AS var,\n"
        "       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p25,\n"
        "       round(percentile_cont(0.50) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p50,\n"
        "       round(percentile_cont(0.75) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p75\n"
        "FROM puq GROUP BY GROUPING SETS ((quintile, tc), (quintile, elo_bucket))\n"
        f"HAVING count(*) >= {stats.COHENS_D_MIN_N}"
    )


def _band(p25: float, p50: float, p75: float) -> tuple[float, float]:
    """IQR clamped symmetrically to ±PRESSURE_BIN_NEUTRAL_CAP around the median."""
    cap = sql.PRESSURE_BIN_NEUTRAL_CAP
    return max(p25, p50 - cap), min(p75, p50 + cap)


def _quintile_verdict(levels: dict[str, stats.LevelStat], q: int, axis: str) -> QuintileVerdict:
    r = stats.max_abs_d(list(levels.values()))
    return QuintileVerdict(quintile=q, axis=axis, max_abs_d=r.max_abs_d, pair=r.pair)


async def compute_333(session: AsyncSession) -> PressureBin333:
    rows = await _fetch(session, _pressure_bin_query())
    bands: list[BandCell] = []
    tc_lvl: dict[int, dict[str, stats.LevelStat]] = {}
    elo_lvl: dict[int, dict[str, stats.LevelStat]] = {}
    for r in rows:
        q = int(r["quintile"])
        n, mean, var = int(r["n_users"]), float(r["mean"]), float(r["var"])
        if int(r["g_tc"]) == 0:  # (quintile, tc) row — band cell + TC verdict level
            tc = str(r["tc"])
            p25, p50, p75 = float(r["p25"]), float(r["p50"]), float(r["p75"])
            lo, hi = _band(p25, p50, p75)
            bands.append(
                BandCell(
                    tc=tc,
                    quintile=q,
                    n_users=n,
                    p25=p25,
                    p50=p50,
                    p75=p75,
                    band_lower=lo,
                    band_upper=hi,
                )
            )
            tc_lvl.setdefault(q, {})[tc] = stats.LevelStat(tc, n, mean, var)
        else:  # (quintile, elo) row — ELO verdict level
            label = str(int(r["elo_bucket"]))
            elo_lvl.setdefault(q, {})[label] = stats.LevelStat(label, n, mean, var)
    bands.sort(key=lambda b: (sql.TC_ORDER.index(b["tc"]), b["quintile"]))  # type: ignore[arg-type]
    verdicts: list[QuintileVerdict] = []
    for q in sorted(tc_lvl):
        verdicts.append(_quintile_verdict(tc_lvl[q], q, "TC"))
        verdicts.append(_quintile_verdict(elo_lvl[q], q, "ELO"))
    return PressureBin333(bands=bands, verdicts=verdicts)


# --- rendering -------------------------------------------------------------


def _pct_cells(d: dist.Distribution, suffix: str) -> list[str]:
    """mean/p25/p50/p75 as signed 2-dp values with a unit suffix (clock-diff %, net pp)."""
    return [
        fmt_int(d["n"]),
        f"{fmt_signed(d['mean'], 2)}{suffix}",
        f"{fmt_signed(d['p25'], 2)}{suffix}",
        f"{fmt_signed(d['p50'], 2)}{suffix}",
        f"{fmt_signed(d['p75'], 2)}{suffix}",
    ]


def _pct_table(
    pooled: dist.Distribution,
    elo: Sequence[dist.Marginal],
    tc: Sequence[dist.Marginal],
    suffix: str,
) -> str:
    headers = ["slice", "n", "mean", "p25", "p50", "p75"]
    aligns: tuple[Align, ...] = ("left", *(("right",) * 5))
    rows = [["**POOLED**", *_pct_cells(pooled, suffix)]]
    rows += [[m["label"], *_pct_cells(m["dist"], suffix)] for m in elo]
    rows += [[m["label"], *_pct_cells(m["dist"], suffix)] for m in tc]
    return markdown_table(headers, rows, aligns)


def _gap_table(pooled: dist.Distribution, tc: Sequence[dist.Marginal]) -> str:
    headers = ["slice", "n", "p25", "p50", "p75"]
    aligns: tuple[Align, ...] = ("left", *(("right",) * 4))

    def cells(d: dist.Distribution) -> list[str]:
        return [fmt_int(d["n"]), *(fmt_signed(d[k], 4) for k in ("p25", "p50", "p75"))]

    rows = [["**POOLED**", *cells(pooled)]]
    rows += [[m["label"], *cells(m["dist"])] for m in tc]
    return markdown_table(headers, rows, aligns)


def _verdict_lines(verdicts: Sequence[dist.Verdict]) -> list[str]:
    out = ["#### Collapse verdict", ""]
    for v in verdicts:
        a, b = v["pair"]
        out.append(f"- **{v['axis']} axis**: max |d| = **{v['max_abs_d']:.2f}** ({a} vs {b})")
    return out


def _render_331(v: ClockPressure331) -> list[str]:
    return [
        "#### 3.3.1 Clock pressure at endgame entry (+ clock-gap-%)",
        "",
        "##### Clock-diff % per-user mean",
        "",
        _pct_table(v["diff_pooled"], v["diff_elo"], v["diff_tc"], "%"),
        "",
        *_verdict_lines(v["diff_verdicts"]),
        "",
        "##### Clock-gap fraction (per-user mean of `(user_clk − opp_clk) / base_clock`)",
        "",
        _gap_table(v["gap_pooled"], v["gap_tc"]),
        "",
        "##### Net-timeout rate (pp; positive = more flag wins than losses)",
        "",
        _pct_table(v["net_pooled"], v["net_elo"], v["net_tc"], "pp"),
        "",
        *_verdict_lines(v["net_verdicts"]),
    ]


def _render_332(v: TimeCurve332) -> list[str]:
    pooled_rows = [
        [str(p["tb"]), fmt_int(p["n"]), f"{fmt_unsigned(p['score'] * 100, 1)}%"]
        for p in v["pooled"]
    ]
    pooled_tbl = markdown_table(
        ["tb", "n_games", "pooled score"], pooled_rows, ("right", "right", "right")
    )

    def marg_table(level: dict[int, dict[str, float]], order: Sequence[str]) -> str:
        headers = ["tb", *order]
        rows = []
        for tb in range(_N_TIME_BUCKETS):
            cells = level.get(tb, {})
            row = [str(tb)]
            for lbl in order:
                s = cells.get(lbl)
                row.append(f"{fmt_unsigned(s * 100, 1)}%" if s is not None else "—")
            rows.append(row)
        return markdown_table(headers, rows, ("right",) * len(headers))

    verdict_rows = []
    for tb in range(_N_TIME_BUCKETS):
        tcv = next((x for x in v["verdicts"] if x["tb"] == tb and x["axis"] == "TC"), None)
        elov = next((x for x in v["verdicts"] if x["tb"] == tb and x["axis"] == "ELO"), None)
        if tcv is None and elov is None:
            continue
        verdict_rows.append(
            [
                str(tb),
                f"{tcv['max_abs_d']:.2f} ({tcv['pair'][0]} vs {tcv['pair'][1]})" if tcv else "—",
                f"{elov['max_abs_d']:.2f} ({elov['pair'][0]} vs {elov['pair'][1]})"
                if elov
                else "—",
            ]
        )
    return [
        "#### 3.3.2 Time pressure vs performance curve",
        "",
        "##### Pooled curve (10 time-buckets, 0–9 = 0–100% clock remaining)",
        "",
        pooled_tbl,
        "",
        "##### TC marginal (per time-bucket score)",
        "",
        marg_table(v["tc"], sql.TC_ORDER),
        "",
        "##### ELO marginal (per time-bucket score)",
        "",
        marg_table(v["elo"], [str(a) for a in sql.ELO_ANCHORS]),
        "",
        "##### Collapse verdict (per time-bucket, max |d| on per-game score)",
        "",
        markdown_table(
            ["tb", "TC max |d|", "ELO max |d|"], verdict_rows, ("right", "right", "right")
        ),
    ]


def _render_333(v: PressureBin333) -> list[str]:
    # Shipped band is the Score-Delta `[max(p25−p50, −cap), min(p75−p50, +cap)]`. Show the
    # uncapped delta IQR alongside the capped band (the live `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` form).
    band_rows = [
        [
            b["tc"],
            str(b["quintile"]),
            fmt_int(b["n_users"]),
            fmt_unsigned(b["p25"], 3),
            fmt_unsigned(b["p50"], 3),
            fmt_unsigned(b["p75"], 3),
            f"({fmt_signed(b['p25'] - b['p50'], 3)}, {fmt_signed(b['p75'] - b['p50'], 3)})",
            f"({fmt_signed(b['band_lower'] - b['p50'], 3)}, {fmt_signed(b['band_upper'] - b['p50'], 3)})",
        ]
        for b in v["bands"]
    ]
    band_tbl = markdown_table(
        ["TC", "Q", "n_users", "p25", "p50", "p75", "delta IQR", "band Δ (cap 0.06)"],
        band_rows,
        ("left", "right", "right", "right", "right", "right", "right", "right"),
    )
    verdict_rows = []
    for q in range(_N_QUINTILES):
        tcv = next((x for x in v["verdicts"] if x["quintile"] == q and x["axis"] == "TC"), None)
        elov = next((x for x in v["verdicts"] if x["quintile"] == q and x["axis"] == "ELO"), None)
        if tcv is None or elov is None:
            continue
        verdict_rows.append(
            [
                str(q),
                f"{tcv['max_abs_d']:.2f} ({tcv['pair'][0]} vs {tcv['pair'][1]})",
                f"{elov['max_abs_d']:.2f} ({elov['pair'][0]} vs {elov['pair'][1]})",
            ]
        )
    return [
        "#### 3.3.3 Chess score per pressure bin (per-(TC × quintile))",
        "",
        "##### Per-(TC × quintile) p25/p50/p75 and delta bands (ELO pooled)",
        "",
        band_tbl,
        "",
        "##### Collapse verdict (per quintile, deterministic per-user Cohen's d)",
        "",
        markdown_table(
            ["Q", "TC max |d|", "ELO max |d|"], verdict_rows, ("right", "right", "right")
        ),
    ]


def render(v331: ClockPressure331, v332: TimeCurve332, v333: PressureBin333) -> str:
    parts = ["### 3.3 Time Pressure", ""]
    parts += _render_331(v331)
    parts += ["", "---", ""]
    parts += _render_332(v332)
    parts += ["", "---", ""]
    parts += _render_333(v333)
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    v331 = await compute_331(session)
    v332 = await compute_332(session)
    v333 = await compute_333(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values_331": v331,
        "values_332": v332,
        "values_333": v333,
        "markdown": render(v331, v332, v333),
    }
