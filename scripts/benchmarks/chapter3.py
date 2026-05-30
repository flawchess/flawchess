"""Chapter 3 — Endgames (SKILL.md §3). §3.1 Endgame Overall Performance.

Ported sub-metrics so far:
  §3.1.1 Non-Endgame Score   — per-user non_eg_score distribution (score units).
  §3.1.6 Endgame Score Gap   — per-user (eg_score − non_eg_score) distribution (pp).

Both derive from one shared per_user CTE (≥30 endgame AND ≥30 non-endgame games per
user, SKILL.md §3.1.6), computed in a single scan: per_user is materialized, then each
metric is aggregated via the canonical pooled+marginal GROUPING SETS. The `eg_score`
distribution is also computed (timeline overlay numbers, §3.1.6 recommendation prose).

Faithful-port findings (validated against benchmarks-latest.md):
  - Sub-800 drop applied (the inline §3.1.6 SQL omits `user_elo_at_game >= 800`, like
    §2.1; the report's ELO marginals sum to the pooled n=4,020, proving it was applied).
  - §3.1.1 pooled SD: the deterministic value is 8.8% (stddev_samp of the data, and
    consistent with the 7.5–9.4% marginal SDs). The prior report stated 8.3% — a
    transcription error (the percentiles, mean, and n all match exactly). Footnoted.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql

SECTION = "SKILL.md §3.1 — endgame overall performance (3.1.1 Non-EG score, 3.1.6 score gap)"

_SCORE_DIGITS = 4  # proportion metrics round to 4 dp in SQL (SKILL.md §3.1.x queries)

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


def render(values: Chapter3Values) -> str:
    parts = ["## 3. Endgames", "", "### 3.1 Endgame Overall Performance", ""]
    parts += _metric_section(
        "#### 3.1.1 Non-Endgame Score (per-user)",
        values["non_eg"],
        "score",
        pooled_label="Pooled distribution",
    )
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
    return {"status": "OK", "section": SECTION, "values": values, "markdown": render(values)}
