"""Shared per-user distribution machinery (pooled + ELO/TC marginals + collapse verdict).

Every per-user metric subchapter (§2.1, §3.1.x, §3.2, §3.4) produces the same shape:
a pooled distribution and ELO + TC marginals over the game-time (ELO, TC) cells, plus
a TC/ELO Cohen's d collapse verdict. The canonical query computes them in one
`GROUP BY GROUPING SETS ((), (elo_bucket), (tc))` scan with SQL `percentile_cont` /
`stddev_samp` (faithful to the skill) and `var_samp` for the d. This module owns the
result types, the GROUPING-SETS row classification, the verdict, and the rendering;
each chapter supplies only its metric-specific per-user CTE + the display `Unit`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping

from scripts.benchmarks import sql, stats
from scripts.benchmarks.render import Align, Unit, fmt_int, fmt_value, markdown_table


class Distribution(TypedDict):
    """A single distribution row: n + mean/SD + five percentiles (SQL-rounded)."""

    n: int
    mean: float
    sd: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


class Marginal(TypedDict):
    """One marginal-axis level: its Distribution plus the raw mean/var feeding Cohen's d."""

    label: str
    dist: Distribution
    mean_raw: float
    var: float


class Verdict(TypedDict):
    axis: str
    max_abs_d: float
    pair: tuple[str, str]


# Canonical percentile set + the SELECT fragment that computes them (SQL percentile_cont,
# faithful to the skill). `value` is the per-user value column; `digits` the SQL rounding
# (4 for proportions, 1 for cp). Pair with `agg_select` to build a GROUPING SETS query.
_PERCENTILES: tuple[float, ...] = (0.05, 0.25, 0.50, 0.75, 0.95)


def agg_select(value: str, *, digits: int, mean_digits: int | None = None) -> str:
    """SELECT list for the canonical pooled+marginal aggregation over `value`.

    Emits: elo_bucket, tc, n, mean (rounded to `mean_digits`), mean_raw (unrounded, for
    d), sd + p05..p95 (rounded to `digits`), var (unrounded, for d). Caller wraps with
    FROM <cte> GROUP BY GROUPING SETS ((), (elo_bucket), (tc)).

    `mean_digits` defaults to `digits`; cp metrics pass `mean_digits=2, digits=1` so the
    SQL-rounded mean reproduces the report's 2-dp→display-1-dp double rounding (e.g.
    3.65 → +3.7). Proportion metrics use `digits=4` throughout.
    """
    md = digits if mean_digits is None else mean_digits
    pcts = ",\n".join(
        f"  round(percentile_cont({p}) WITHIN GROUP (ORDER BY {value})::numeric, {digits}) AS p{int(p * 100):02d}"
        for p in _PERCENTILES
    )
    return (
        "  elo_bucket, tc, count(*) AS n,\n"
        f"  round(avg({value})::numeric, {md}) AS mean,\n"
        f"  avg({value}) AS mean_raw,\n"
        f"  round(stddev_samp({value})::numeric, {digits}) AS sd,\n"
        f"  var_samp({value}) AS var,\n"
        f"{pcts}"
    )


def pooled_agg_select(value: str, *, digits: int, mean_digits: int | None = None) -> str:
    """`agg_select` column list for a single ungrouped pooled row (elo_bucket/tc → NULL).

    Use to UNION ALL a pooled-only distribution (e.g. §3.1.2's uncentered variant)
    against a `agg_select` + GROUPING SETS arm — the column lists line up so both arms
    parse via `dist_from_row` / `split_grouping_sets`.
    """
    md = digits if mean_digits is None else mean_digits
    pcts = ",\n".join(
        f"  round(percentile_cont({p}) WITHIN GROUP (ORDER BY {value})::numeric, {digits}) AS p{int(p * 100):02d}"
        for p in _PERCENTILES
    )
    return (
        "  NULL::int AS elo_bucket, NULL::text AS tc, count(*) AS n,\n"
        f"  round(avg({value})::numeric, {md}) AS mean,\n"
        f"  avg({value}) AS mean_raw,\n"
        f"  round(stddev_samp({value})::numeric, {digits}) AS sd,\n"
        f"  var_samp({value}) AS var,\n"
        f"{pcts}"
    )


GROUPING_SETS = "GROUP BY GROUPING SETS ((), (elo_bucket), (tc))"


def _f(value: Any) -> float:
    return float(value)


def dist_from_row(row: RowMapping) -> Distribution:
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


def split_grouping_sets(
    rows: Sequence[RowMapping],
) -> tuple[Distribution, list[Marginal], list[Marginal]]:
    """Classify GROUPING SETS rows into (pooled, ELO marginals, TC marginals).

    Pooled = the all-NULL grouping row; ELO rows have elo_bucket set; TC rows have tc
    set. ELO marginals are sorted ascending; TC marginals in canonical TC order.
    """
    pooled: Distribution | None = None
    elo: list[Marginal] = []
    tc: list[Marginal] = []
    for row in rows:
        d = dist_from_row(row)
        if row["elo_bucket"] is not None:
            label = str(int(row["elo_bucket"]))
            elo.append(
                Marginal(label=label, dist=d, mean_raw=_f(row["mean_raw"]), var=_f(row["var"]))
            )
        elif row["tc"] is not None:
            tc.append(
                Marginal(
                    label=str(row["tc"]), dist=d, mean_raw=_f(row["mean_raw"]), var=_f(row["var"])
                )
            )
        else:
            pooled = d
    if pooled is None:
        raise RuntimeError("GROUPING SETS result missing the pooled (all-NULL) row")
    elo.sort(key=lambda m: int(m["label"]))
    tc.sort(key=lambda m: sql.TC_ORDER.index(m["label"]))  # type: ignore[arg-type]
    return pooled, elo, tc


def verdict(axis: str, marginals: Sequence[Marginal]) -> Verdict:
    levels = [
        stats.LevelStat(m["label"], m["dist"]["n"], m["mean_raw"], m["var"]) for m in marginals
    ]
    result = stats.max_abs_d(levels)
    return Verdict(axis=axis, max_abs_d=result.max_abs_d, pair=result.pair)


# --- rendering -------------------------------------------------------------

_HEADERS: tuple[str, ...] = ("n", "mean", "SD", "p05", "p25", "p50", "p75", "p95")
_ALIGNS: tuple[Align, ...] = ("right",) * len(_HEADERS)


def _cells(dist: Distribution, unit: Unit, *, pooled: bool) -> list[str]:
    pct = (dist["p05"], dist["p25"], dist["p50"], dist["p75"], dist["p95"])
    return [
        fmt_int(dist["n"]),
        fmt_value(dist["mean"], unit, "mean", pooled=pooled),
        fmt_value(dist["sd"], unit, "sd", pooled=pooled),
        *(fmt_value(v, unit, "pct", pooled=pooled) for v in pct),
    ]


def pooled_table(dist: Distribution, unit: Unit) -> str:
    return markdown_table(_HEADERS, [_cells(dist, unit, pooled=True)], _ALIGNS)


def marginal_table(axis_label: str, marginals: Sequence[Marginal], unit: Unit) -> str:
    headers = [axis_label, *_HEADERS]
    aligns: tuple[Align, ...] = ("right",) * len(headers)
    rows = [[m["label"], *_cells(m["dist"], unit, pooled=False)] for m in marginals]
    return markdown_table(headers, rows, aligns)


def verdict_block(verdicts: Sequence[Verdict]) -> str:
    lines = ["#### Collapse verdict", ""]
    for v in verdicts:
        a, b = v["pair"]
        lines.append(f"- **{v['axis']} axis**: max |d| = **{v['max_abs_d']:.2f}** ({a} vs {b})")
    return "\n".join(lines)
