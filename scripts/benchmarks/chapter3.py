"""Chapter 3 — Endgames (SKILL.md §3). §3.1 Endgame Overall + §3.2 Endgame Metrics vs ELO.

Ported sub-metrics so far:
  §3.1.1 Non-Endgame Score   — per-user non_eg_score distribution (score units).
  §3.1.2 Endgame-entry eval  — two-pass symmetric-baseline eval at EG entry (cp).
  §3.1.3 Achievable Score    — per-user entry_xs (Lichess sigmoid at EG entry, score).
  §3.1.4 Endgame Score       — per-user absolute eg_score over EG games (score).
  §3.1.5 Achievable Score Gap — per-user avg(actual − expected) paired gap (pp).
  §3.1.6 Endgame Score Gap   — per-user (eg_score − non_eg_score) distribution (pp).
  §3.2.1 Conv/Parity/Recovery — per-user bucket rates (+ retracted composite skill, score).
  §3.2.2 Section-2 ΔES Gap   — per-user per-bucket span gap, ES_exit − ES_entry (pp).
  §3.2.3 Rate-vs-gap divergence — derived cross-cut of §3.2.1/§3.2.2 (no new query).

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
  - §3.1.3: pooled, all ELO/TC marginals, and both verdicts (TC 0.12 bullet-vs-rapid,
    ELO 0.12 1600-vs-2400) reproduce the report exactly. No transcription errors found.
  - §3.1.4: pooled and all ELO/TC marginals reproduce the report exactly (the first
    non-collapse verdicts — TC 0.21 review, ELO 0.35 review; the LLM applies the words).
    ELO-axis pair corrected to (800, 2400): deterministic max |d|=0.34694 there edges
    out (800, 2000)'s 0.34679; both round to 0.35 / review, so magnitude and verdict are
    unchanged. The prior report labeled the runner-up (800, 2000) — a hand-computation
    pair-selection slip, same class as §2.1's (800,1200)→(800,1600). Footnoted.
  - §3.1.5: pooled and all ELO/TC marginals reproduce the report exactly. TC-axis pair
    corrected to (rapid, classical): the deterministic max |d|=0.134 is there, while the
    report's labeled (bullet, rapid) is only 0.08 — the report carried the right
    magnitude (0.13 → collapse) on the wrong pair label. ELO (800, 2400) 0.34 matches.
  - §3.2.1: conv/recov/skill pooled + all marginals + the conv/recov verdicts reproduce
    the report exactly (conv TC 0.93 / ELO 0.51; recov TC 0.90 / ELO 0.25). Parity carries
    two verdict-NEUTRAL pair-selection slips: TC report 0.08 → true 0.11 (rapid vs
    classical, both collapse); ELO report (800,2400) 0.20 → true (1200,2400) 0.22 (1200's
    smaller variance wins, both review). Classical conv mean 0.7545 renders 75.4% vs the
    report's 75.5% — a .5-boundary half-up display artifact (the 4 dp value is exact).
  - §3.2.2: conv/recov pooled + all marginals + verdicts reproduce the report exactly
    (conv TC 1.25 / ELO 1.35; recov TC 1.69 / ELO 0.95; parity ELO 0.31). One
    verdict-NEUTRAL parity slip: TC report 0.10 → true 0.18 (rapid vs classical, both
    collapse). The conv/recov bands that drive zone calibration are exact.
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
from scripts.benchmarks.render import (
    Align,
    Unit,
    fmt_int,
    fmt_signed,
    fmt_unsigned,
    fmt_value,
    markdown_table,
)

SECTION = "SKILL.md §3.1 — endgame overall (3.1.1–3.1.6: Non-EG, EG-entry eval, achievable, EG score, achievable gap, score gap)"

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


# --- §3.1.3 Achievable Score (entry_xs) ------------------------------------


def _entry_xs_per_user_cte() -> str:
    """Per-user `entry_xs = avg(expected_score)` over endgame-reaching games (SKILL.md §3.1.3).

    expected_score is the Lichess winning-chances sigmoid (mate forces 0/1) at the first
    endgame ply; ≥20 non-null entry games per (user, game-time ELO, TC) cell, sub-800
    dropped, equal-footing filtered, sparse cell excluded. Shares `entry_rows` with §3.1.5.
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.ENDGAME_GAME_IDS_CTE},\n"
        f"{sql.ENTRY_ROWS_CTE},\n"
        "rows AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
        f"         {sql.expected_score_sql()} AS expected_score\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "per_user AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc,\n"
        "         avg(expected_score) AS entry_xs\n"
        f"  FROM rows WHERE ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) FILTER (WHERE expected_score IS NOT NULL) >= {sql.ENDGAME_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute_313(session: AsyncSession) -> MetricBlock:
    query = (
        _entry_xs_per_user_cte()
        + "\nSELECT\n"
        + dist.agg_select("entry_xs", digits=_SCORE_DIGITS)
        + f"\nFROM pu {dist.GROUPING_SETS}"
    )
    rows = await _fetch(session, query)
    pooled, elo, tc = dist.split_grouping_sets(rows)
    return MetricBlock(
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


# --- §3.1.4 Endgame Score (per-user, EG-only) ------------------------------


def _eg_score_per_user_cte() -> str:
    """Per-user `eg_score = avg(score)` over endgame-reaching games (SKILL.md §3.1.4).

    Absolute EG-only score (no centering), ≥20 endgame games per (user, game-time ELO,
    TC) cell, sub-800 dropped, equal-footing filtered, sparse cell excluded. Simpler
    than §3.1.1/§3.1.6 (no non-endgame slice → a plain INNER JOIN on endgame_game_ids
    and a single ≥20 floor instead of the paired ≥30-both floor).
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.ENDGAME_GAME_IDS_CTE},\n"
        "rows AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
        f"         {sql.USER_SCORE_EXPR} AS score\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN endgame_game_ids eg ON eg.game_id = g.id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "per_user AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc, avg(score) AS eg_score\n"
        f"  FROM rows WHERE ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) >= {sql.ENDGAME_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute_314(session: AsyncSession) -> MetricBlock:
    query = (
        _eg_score_per_user_cte()
        + "\nSELECT\n"
        + dist.agg_select("eg_score", digits=_SCORE_DIGITS)
        + f"\nFROM pu {dist.GROUPING_SETS}"
    )
    rows = await _fetch(session, query)
    pooled, elo, tc = dist.split_grouping_sets(rows)
    return MetricBlock(
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


# --- §3.1.5 Achievable Score Gap (paired actual − expected) ----------------


def _achievable_gap_per_user_cte() -> str:
    """Per-user `achievable_gap = avg(actual − expected)` at EG entry (SKILL.md §3.1.5).

    Paired per-game gap: actual score (USER_SCORE_EXPR) minus the Lichess-sigmoid
    expected score at the first endgame ply (mate INCLUDED, |cp|≥2000 → NULL → dropped,
    both sides identically). ≥20 non-null pairs per (user, game-time ELO, TC) cell,
    sub-800 dropped, equal-footing filtered, sparse cell excluded. Shares the
    `entry_rows` + `expected_score` machinery with §3.1.3.
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    d_i = f"({sql.USER_SCORE_EXPR})\n         - ({sql.expected_score_sql()})"
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.ENDGAME_GAME_IDS_CTE},\n"
        f"{sql.ENTRY_ROWS_CTE},\n"
        "rows AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
        f"         {d_i} AS d_i\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "per_user AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc, avg(d_i) AS achievable_gap\n"
        f"  FROM rows WHERE ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= {sql.ENDGAME_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute_315(session: AsyncSession) -> MetricBlock:
    query = (
        _achievable_gap_per_user_cte()
        + "\nSELECT\n"
        + dist.agg_select("achievable_gap", digits=_SCORE_DIGITS)
        + f"\nFROM pu {dist.GROUPING_SETS}"
    )
    rows = await _fetch(session, query)
    pooled, elo, tc = dist.split_grouping_sets(rows)
    return MetricBlock(
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


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


# --- §3.2.1 Conversion / Parity / Recovery + Endgame Skill -----------------

# conv/par/recov are full MetricBlocks (verdict); skill is informational (retracted).
_CPR_METRICS: tuple[tuple[str, str], ...] = (
    ("conversion", "conv_rate"),
    ("parity", "par_rate"),
    ("recovery", "recov_rate"),
)


class ConvParRecov321(TypedDict):
    conversion: MetricBlock
    parity: MetricBlock
    recovery: MetricBlock
    # Endgame Skill — composite retracted Phase 87.4, reported for continuity (no verdict).
    skill_pooled: dist.Distribution
    skill_elo: list[dist.Marginal]
    skill_tc: list[dist.Marginal]


def _conv_par_recov_pu_cte() -> str:
    """Per-user conv/par/recov rates + composite skill per cell (SKILL.md §3.2.1).

    Each endgame-reaching game is bucketed by its first-endgame-ply eval
    (`endgame_bucket_case_sql`) into conversion/parity/recovery; the per-user per-bucket
    rate is the mean win/score/save contribution. `per_user_cell` pivots to wide form
    (conv/par/recov rate + unweighted-mean skill) over users with ≥20 total endgame games
    and ≥2 active buckets, sub-800 dropped, equal-footing filtered, sparse cell excluded.
    Reuses the §3.1.3/§3.1.5 `entry_rows` (rn = 1) for the first-endgame-ply eval.
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    bucket_expr = sql.endgame_bucket_case_sql("ec", "em", "color_sign")
    contrib_expr = sql.bucket_score_case_sql("ec", "em", "color_sign", "score")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.ENDGAME_GAME_IDS_CTE},\n"
        f"{sql.ENTRY_ROWS_CTE},\n"
        "bucketed AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
        f"         {sql.USER_SCORE_EXPR} AS score,\n"
        f"         {sql.USER_COLOR_SIGN_SQL} AS color_sign,\n"
        "         er.eval_cp AS ec, er.eval_mate AS em\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "classified AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc, score,\n"
        f"         {bucket_expr} AS bucket,\n"
        f"         {contrib_expr} AS contrib\n"
        f"  FROM bucketed WHERE ueag >= {sql.ELO_FLOOR}\n"
        "),\n"
        "per_user_bucket AS (\n"
        "  SELECT user_id, elo_bucket, tc, bucket,\n"
        "         count(*) AS games, avg(contrib) AS bucket_rate\n"
        "  FROM classified GROUP BY user_id, elo_bucket, tc, bucket\n"
        "),\n"
        "per_user_cell AS (\n"
        "  SELECT user_id, elo_bucket, tc,\n"
        "         max(bucket_rate) FILTER (WHERE bucket = 'conversion') AS conv_rate,\n"
        "         max(bucket_rate) FILTER (WHERE bucket = 'parity')     AS par_rate,\n"
        "         max(bucket_rate) FILTER (WHERE bucket = 'recovery')   AS recov_rate,\n"
        "         avg(bucket_rate) AS skill\n"
        "  FROM per_user_bucket GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING sum(games) >= {sql.ENDGAME_MIN_GAMES} AND count(*) >= 2\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user_cell WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute_321(session: AsyncSession) -> ConvParRecov321:
    """§3.2.1 — conv/par/recov MetricBlocks (with verdict) + informational skill block.

    With ~100% endgame-entry eval coverage every qualifying user has all three buckets,
    so `count(*)` equals each metric's non-null count (verified: pooled n = 4,616 for all
    four metrics) and the canonical `agg_select` n is faithful.
    """
    selects = [
        f"SELECT '{metric}' AS metric,\n{dist.agg_select(col, digits=_SCORE_DIGITS)}\n"
        f"FROM pu {dist.GROUPING_SETS}"
        for metric, col in (*_CPR_METRICS, ("skill", "skill"))
    ]
    query = _conv_par_recov_pu_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    def block(metric: str) -> MetricBlock:
        pooled, elo, tc = dist.split_grouping_sets([r for r in rows if r["metric"] == metric])
        return MetricBlock(
            pooled=pooled,
            elo_marginal=elo,
            tc_marginal=tc,
            verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
        )

    skill_pooled, skill_elo, skill_tc = dist.split_grouping_sets(
        [r for r in rows if r["metric"] == "skill"]
    )
    return ConvParRecov321(
        conversion=block("conversion"),
        parity=block("parity"),
        recovery=block("recovery"),
        skill_pooled=skill_pooled,
        skill_elo=skill_elo,
        skill_tc=skill_tc,
    )


# --- §3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket) -----------------


class Section2Gap322(TypedDict):
    conversion: MetricBlock
    parity: MetricBlock
    recovery: MetricBlock


def _section2_gap_per_user_bucket_cte() -> str:
    """Per-user per-bucket mean ΔES score gap over endgame-class spans (SKILL.md §3.2.2).

    One row per (game, endgame_class) span of ≥6 plies; `gap_span = ES_exit − ES_entry`
    where each ES is the win-chances expectation at the span's first ply (exit = the NEXT
    span's entry, or the game result for the final span). Spans are assigned to the
    conversion/parity/recovery bucket by their entry eval (`endgame_bucket_case_sql`).
    `per_user_bucket` keeps users with ≥20 qualifying spans per bucket per cell, sub-800
    dropped, equal-footing filtered, sparse cell excluded. The spans/spans_with_next/gap_rows
    chain is the shared `sql.span_gap_ctes()` (§3.4.2/§3.4.3 reuse it); here we group by bucket.
    """
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.span_gap_ctes()},\n"
        "per_user_bucket AS (\n"
        "  SELECT user_id, elo_bucket, tc, bucket, avg(gap_span) AS mean_gap\n"
        "  FROM gap_rows\n"
        f"  WHERE gap_span IS NOT NULL AND elo_bucket IS NOT NULL AND {sql.SPARSE_CELL_EXCLUSION}\n"
        "  GROUP BY user_id, elo_bucket, tc, bucket\n"
        f"  HAVING count(*) >= {sql.SECTION2_SPAN_MIN_SPANS}\n"
        ")"
    )


async def compute_322(session: AsyncSession) -> Section2Gap322:
    """§3.2.2 — per-bucket ΔES score-gap MetricBlocks (pp). One distribution per bucket."""
    buckets = ("conversion", "parity", "recovery")
    selects = [
        f"SELECT '{b}' AS metric,\n{dist.agg_select('mean_gap', digits=_SCORE_DIGITS)}\n"
        f"FROM per_user_bucket WHERE bucket = '{b}' {dist.GROUPING_SETS}"
        for b in buckets
    ]
    query = _section2_gap_per_user_bucket_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    def block(bucket: str) -> MetricBlock:
        pooled, elo, tc = dist.split_grouping_sets([r for r in rows if r["metric"] == bucket])
        return MetricBlock(
            pooled=pooled,
            elo_marginal=elo,
            tc_marginal=tc,
            verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
        )

    return Section2Gap322(
        conversion=block("conversion"),
        parity=block("parity"),
        recovery=block("recovery"),
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


def render(
    values: Chapter3Values,
    eval312: EntryEval312,
    xs313: MetricBlock,
    eg314: MetricBlock,
    gap315: MetricBlock,
) -> str:
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
        "#### 3.1.3 Achievable Score (entry_xs)",
        xs313,
        "score",
        pooled_label="Pooled distribution",
    )
    parts += ["", "---", ""]
    parts += _metric_section(
        "#### 3.1.4 Endgame Score (per-user, EG-only)",
        eg314,
        "score",
        pooled_label="Pooled distribution",
    )
    parts += ["", "---", ""]
    parts += _metric_section(
        "#### 3.1.5 Achievable Score Gap (paired actual − expected)",
        gap315,
        "pp",
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
    eval312 = await compute_312(session)
    xs313 = await compute_313(session)
    eg314 = await compute_314(session)
    gap315 = await compute_315(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values": values,
        "values_312": eval312,
        "values_313": xs313,
        "values_314": eg314,
        "values_315": gap315,
        "markdown": render(values, eval312, xs313, eg314, gap315),
    }


# --- §3.2 rendering + build ------------------------------------------------

SECTION_32 = "SKILL.md §3.2 — endgame metrics vs ELO (3.2.1 Conv/Parity/Recovery + retracted Skill, 3.2.2 Section-2 ΔES gap, 3.2.3 rate-vs-gap divergence)"


def _skill_section(v: ConvParRecov321) -> list[str]:
    """Endgame Skill informational block (no band, no verdict — composite retracted)."""
    return [
        "##### Endgame Skill (per-user) — informational only (composite retracted Phase 87.4)",
        "",
        "###### Pooled distribution",
        "",
        dist.pooled_table(v["skill_pooled"], "score"),
        "",
        "###### ELO marginal",
        "",
        dist.marginal_table("ELO", v["skill_elo"], "score"),
        "",
        "###### TC marginal",
        "",
        dist.marginal_table("TC", v["skill_tc"], "score"),
    ]


def _sweep(marginals: Sequence[dist.Marginal], unit: Unit) -> str:
    """Endpoint sweep `first → last` of marginal means in display order (§3.2.3)."""
    lo = fmt_value(marginals[0]["dist"]["mean"], unit, "mean")
    hi = fmt_value(marginals[-1]["dist"]["mean"], unit, "mean")
    return f"{lo} → {hi}"


def _axis_d(block: MetricBlock, axis: str) -> str:
    for ver in block["verdicts"]:
        if ver["axis"] == axis:
            return f"{ver['max_abs_d']:.2f}"
    raise KeyError(axis)


def _divergence_row(label: str, rate: MetricBlock, gap: MetricBlock) -> list[str]:
    """One §3.2.3 axis-driver row: raw-rate vs ΔES-gap sweeps + max |d| per axis.

    Derived entirely from the §3.2.1 rate block (score unit) and the §3.2.2 gap block
    (pp unit); the LLM narrator applies the collapse/review/keep word per the fixed
    threshold table (code emits the d-value only, per the SEED-029 code/LLM seam).
    """
    return [
        label,
        _sweep(rate["elo_marginal"], "score"),
        _axis_d(rate, "ELO"),
        _sweep(rate["tc_marginal"], "score"),
        _axis_d(rate, "TC"),
        _sweep(gap["elo_marginal"], "pp"),
        _axis_d(gap, "ELO"),
        _sweep(gap["tc_marginal"], "pp"),
        _axis_d(gap, "TC"),
    ]


def _render_323(cpr: ConvParRecov321, gap: Section2Gap322) -> list[str]:
    headers = [
        "Bucket",
        "Raw rate ELO sweep",
        "Raw ELO d",
        "Raw rate TC sweep",
        "Raw TC d",
        "Gap ELO sweep",
        "Gap ELO d",
        "Gap TC sweep",
        "Gap TC d",
    ]
    aligns: tuple[Align, ...] = ("left", *(("right",) * (len(headers) - 1)))
    rows = [
        _divergence_row("Conversion", cpr["conversion"], gap["conversion"]),
        _divergence_row("Recovery", cpr["recovery"], gap["recovery"]),
    ]
    return [
        "#### 3.2.3 Rate vs Score-Gap divergence (Conv & Recov cross-cut — derived)",
        "",
        "Derived from the §3.2.1 raw rates and §3.2.2 ΔES gaps (no new query). Sweep =",
        "first → last marginal mean in display order; d = max |Cohen's d| over the axis.",
        "",
        markdown_table(headers, rows, aligns),
    ]


def render_32(cpr: ConvParRecov321, gap: Section2Gap322) -> str:
    parts = ["### 3.2 Endgame Metrics and ELO", ""]
    parts += [
        "#### 3.2.1 Conversion / Parity / Recovery (+ retracted Endgame Skill)",
        "",
    ]
    parts += _metric_section(
        "##### Conversion (per-user)",
        cpr["conversion"],
        "score",
        pooled_label="Pooled distribution",
    )
    parts += ["", "##### Parity (per-user)", ""]
    parts += _metric_section(
        "###### Parity", cpr["parity"], "score", pooled_label="Pooled distribution"
    )
    parts += ["", "##### Recovery (per-user)", ""]
    parts += _metric_section(
        "###### Recovery", cpr["recovery"], "score", pooled_label="Pooled distribution"
    )
    parts += [""]
    parts += _skill_section(cpr)
    parts += ["", "---", ""]
    parts += ["#### 3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket)", ""]
    parts += _metric_section(
        "##### Conversion-bucket ΔES (per-user)",
        gap["conversion"],
        "pp",
        pooled_label="Pooled distribution",
    )
    parts += ["", ""]
    parts += _metric_section(
        "##### Parity-bucket ΔES (per-user)",
        gap["parity"],
        "pp",
        pooled_label="Pooled distribution",
    )
    parts += ["", ""]
    parts += _metric_section(
        "##### Recovery-bucket ΔES (per-user)",
        gap["recovery"],
        "pp",
        pooled_label="Pooled distribution",
    )
    parts += ["", "---", ""]
    parts += _render_323(cpr, gap)
    return "\n".join(parts)


async def build_32(session: AsyncSession) -> dict[str, Any]:
    cpr = await compute_321(session)
    gap = await compute_322(session)
    return {
        "status": "OK",
        "section": SECTION_32,
        "values_321": cpr,
        "values_322": gap,
        "markdown": render_32(cpr, gap),
    }
