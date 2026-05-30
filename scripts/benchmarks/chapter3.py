"""Chapter 3 — Endgames (SKILL.md §3). §3.1 Endgame Overall Performance.

Ported sub-metrics so far:
  §3.1.1 Non-Endgame Score   — per-user non_eg_score distribution (score units).
  §3.1.2 Endgame-entry eval  — two-pass symmetric-baseline eval at EG entry (cp).
  §3.1.6 Endgame Score Gap   — per-user (eg_score − non_eg_score) distribution (pp).

§3.1.1/§3.1.6 derive from one shared per_user CTE (≥30 endgame AND ≥30 non-endgame
games per user, SKILL.md §3.1.6), computed in a single scan: per_user is materialized,
then each metric is aggregated via the canonical pooled+marginal GROUPING SETS. The
`eg_score` distribution is also computed (timeline overlay numbers, §3.1.6 prose).

§3.1.2 is the EG-entry twin of §2.1 (phase = 2 instead of 1) and reuses the shared
two-pass eval machinery in `entry_eval.py`. It additionally reports BOTH an uncentered
and a centered pooled row: the live tile is 0-centered, so calibration recommendations
read the uncentered distribution, while the centered one drives Cohen's d (parity with
§2.1). The two are nearly identical because the EG baseline (±10 cp) is tiny relative to
the ~119 cp per-user-mean SD.

Faithful-port findings (validated against benchmarks-latest.md):
  - Sub-800 drop applied (the inline §3.1.6 SQL omits `user_elo_at_game >= 800`, like
    §2.1; the report's ELO marginals sum to the pooled n=4,020, proving it was applied).
  - §3.1.1 pooled SD: the deterministic value is 8.8% (stddev_samp of the data, and
    consistent with the 7.5–9.4% marginal SDs). The prior report stated 8.3% — a
    transcription error (the percentiles, mean, and n all match exactly). Footnoted.
  - §3.1.2: pass 1, both pooled variants, all ELO/TC marginals (n/mean/SD), and both
    collapse verdicts (TC 0.14 bullet-vs-rapid, ELO 0.11 800-vs-2000) reproduce the
    report exactly. No transcription errors found.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import entry_eval
from scripts.benchmarks import sql
from scripts.benchmarks.entry_eval import Baseline
from scripts.benchmarks.render import fmt_int, fmt_signed, fmt_unsigned, markdown_table

SECTION = "SKILL.md §3.1 — endgame overall performance (3.1.1 Non-EG score, 3.1.2 EG-entry eval, 3.1.6 score gap)"

_SCORE_DIGITS = 4  # proportion metrics round to 4 dp in SQL (SKILL.md §3.1.x queries)
# §3.1.2 eval is a cp metric: mean at 2 dp (report double-rounds), sd/pct at 1 dp.
_CP_DIGITS = 1
_CP_MEAN_DIGITS = 2

# Per-user value expressions aggregated from the shared per_user CTE.
_METRICS: tuple[tuple[str, str], ...] = (
    ("non_eg", "non_eg_score"),
    ("diff", "eg_score - non_eg_score"),
    ("eg", "eg_score"),
)


class MetricBlock(TypedDict):
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]


class Chapter3Values(TypedDict):
    non_eg: MetricBlock  # §3.1.1
    diff: MetricBlock  # §3.1.6
    eg: MetricBlock  # timeline overlay (§3.1.6 recommendation prose)


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


def _per_user_cte() -> str:
    """Shared per_user CTE for §3.1.1/§3.1.6 — one row per (user, game-time ELO, TC).

    eg_score / non_eg_score over the user's selected-TC games, split on the 6-ply
    endgame rule, equal-footing filtered, sub-800 dropped, ≥30 games each side.
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.ENDGAME_GAME_IDS_CTE},\n"
        "rows AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
        f"         {sql.USER_SCORE_EXPR} AS score,\n"
        "         (eg.game_id IS NOT NULL) AS has_endgame\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  LEFT JOIN endgame_game_ids eg ON eg.game_id = g.id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "per_user AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc,\n"
        "         avg(score) FILTER (WHERE has_endgame) AS eg_score,\n"
        "         avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score\n"
        f"  FROM rows WHERE ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) FILTER (WHERE has_endgame) >= {sql.SCORE_GAP_MIN_GAMES}\n"
        f"     AND count(*) FILTER (WHERE NOT has_endgame) >= {sql.SCORE_GAP_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


def _metric_select(metric: str, value: str) -> str:
    return (
        f"SELECT '{metric}' AS metric,\n"
        f"{dist.agg_select(value, digits=_SCORE_DIGITS)}\n"
        f"FROM pu {dist.GROUPING_SETS}"
    )


async def compute(session: AsyncSession) -> Chapter3Values:
    query = (
        _per_user_cte()
        + "\n"
        + "\nUNION ALL\n".join(_metric_select(metric, value) for metric, value in _METRICS)
    )
    rows = await _fetch(session, query)

    blocks: dict[str, MetricBlock] = {}
    for metric, _ in _METRICS:
        metric_rows = [r for r in rows if r["metric"] == metric]
        pooled, elo, tc = dist.split_grouping_sets(metric_rows)
        blocks[metric] = MetricBlock(
            pooled=pooled,
            elo_marginal=elo,
            tc_marginal=tc,
            verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
        )
    return Chapter3Values(non_eg=blocks["non_eg"], diff=blocks["diff"], eg=blocks["eg"])


# --- §3.1.2 Endgame-entry eval (two-pass, phase = 2) -----------------------


class EntryEval312(TypedDict):
    baseline: Baseline
    pooled_uncentered: dist.Distribution  # drives the live (0-centered) tile recommendation
    pooled_centered: dist.Distribution
    elo_marginal: list[dist.Marginal]  # centered
    tc_marginal: list[dist.Marginal]  # centered
    verdicts: list[dist.Verdict]


async def compute_312(session: AsyncSession) -> EntryEval312:
    """§3.1.2 — pass 1 baseline, then pooled (both variants) + centered marginals.

    One pass-2 scan: the centered arm is a GROUPING SETS aggregation (pooled + ELO +
    TC + Cohen's d), the uncentered arm a single pooled aggregate, UNION ALL'd.
    """
    baseline = await entry_eval.baseline(session, sql.ENDGAME_PHASE)
    centering = baseline["centering_cp"]
    query = (
        f"{entry_eval.per_user_color_with(sql.ENDGAME_PHASE)},\n"
        f"centered AS (\n"
        f"  SELECT {entry_eval.centered_expr(centering)} AS v, elo_bucket, tc\n"
        f"  FROM {entry_eval.PER_USER_COLOR_CTE} WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        "),\n"
        "uncentered AS (\n"
        f"  SELECT mean_signed_cp AS v, elo_bucket, tc\n"
        f"  FROM {entry_eval.PER_USER_COLOR_CTE} WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")\n"
        "SELECT 'centered' AS variant,\n"
        f"{dist.agg_select('v', digits=_CP_DIGITS, mean_digits=_CP_MEAN_DIGITS)}\n"
        f"FROM centered {dist.GROUPING_SETS}\n"
        "UNION ALL\n"
        "SELECT 'uncentered' AS variant,\n"
        f"{dist.pooled_agg_select('v', digits=_CP_DIGITS, mean_digits=_CP_MEAN_DIGITS)}\n"
        "FROM uncentered"
    )
    rows = await _fetch(session, query)
    centered_rows = [r for r in rows if r["variant"] == "centered"]
    uncentered_rows = [r for r in rows if r["variant"] == "uncentered"]
    pooled_centered, elo, tc = dist.split_grouping_sets(centered_rows)
    return EntryEval312(
        baseline=baseline,
        pooled_uncentered=dist.dist_from_row(uncentered_rows[0]),
        pooled_centered=pooled_centered,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


# --- rendering -------------------------------------------------------------


def _metric_section(
    title: str, block: MetricBlock, unit: dist.Unit, *, pooled_label: str
) -> list[str]:
    return [
        title,
        "",
        f"##### {pooled_label}",
        "",
        dist.pooled_table(block["pooled"], unit),
        "",
        "##### ELO marginal",
        "",
        dist.marginal_table("ELO", block["elo_marginal"], unit),
        "",
        "##### TC marginal",
        "",
        dist.marginal_table("TC", block["tc_marginal"], unit),
        "",
        dist.verdict_block(block["verdicts"]),
    ]


def _pooled_312_table(v: EntryEval312) -> str:
    """Two-row pooled table (uncentered + centered) — §3.1.2 display layout.

    Matches benchmarks-latest.md §3.1.2: mean/SD carry a ` cp` suffix, percentiles are
    bare integer cp. (This differs from §2.1's pooled table, which suffixes every cell —
    a hand-authored inconsistency in the prior report; the gate asserts values, not the
    suffix style.)
    """
    headers = ["variant", "n", "mean", "SD", "p05", "p25", "p50", "p75", "p95"]

    def row(label: str, d: dist.Distribution) -> list[str]:
        pct = (d["p05"], d["p25"], d["p50"], d["p75"], d["p95"])
        return [
            label,
            fmt_int(d["n"]),
            f"{fmt_signed(d['mean'], 1)} cp",
            f"{fmt_unsigned(d['sd'], 1)} cp",
            *(fmt_signed(p, 0) for p in pct),
        ]

    rows = [
        row("**uncentered**", v["pooled_uncentered"]),
        row("centered", v["pooled_centered"]),
    ]
    aligns: tuple[dist.Align, ...] = ("left", *(("right",) * (len(headers) - 1)))
    return markdown_table(headers, rows, aligns)


def _render_312(v: EntryEval312) -> list[str]:
    return [
        "#### 3.1.2 Endgame-entry eval (pawns)",
        "",
        "##### Pass 1 — symmetric EG-entry baseline (deduped game-level)",
        "",
        entry_eval.baseline_table(v["baseline"]),
        "",
        "##### Pass 2 — pooled distribution (uncentered drives the live tile recommendation)",
        "",
        _pooled_312_table(v),
        "",
        "##### ELO marginal (centered)",
        "",
        dist.marginal_table("ELO", v["elo_marginal"], "cp"),
        "",
        "##### TC marginal (centered)",
        "",
        dist.marginal_table("TC", v["tc_marginal"], "cp"),
        "",
        dist.verdict_block(v["verdicts"]),
    ]


def render(values: Chapter3Values, eval312: EntryEval312) -> str:
    parts = ["## 3. Endgames", "", "### 3.1 Endgame Overall Performance", ""]
    parts += _metric_section(
        "#### 3.1.1 Non-Endgame Score (per-user)",
        values["non_eg"],
        "score",
        pooled_label="Pooled distribution",
    )
    parts += ["", "---", ""]
    parts += _render_312(eval312)
    parts += ["", "---", ""]
    parts += _metric_section(
        "#### 3.1.6 Endgame Score Gap and Timeline",
        values["diff"],
        "pp",
        pooled_label="Pooled distribution (per-user `eg_score − non_eg_score`)",
    )
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    eval312 = await compute_312(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values": values,
        "values_312": eval312,
        "markdown": render(values, eval312),
    }
