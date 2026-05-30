"""Chapter 3 §3.4 — Endgame Type Breakdown (per-class score / conv / recov / ΔES gap).

Ported sub-metrics:
  §3.4.1 Per-class score / conversion / recovery — pooled-by-class game-level summary,
    per-(user, class) chess-score IQR, and per-class conv/recov TC + ELO marginals with
    per-(class × metric × axis) Cohen's d. The conv/recov bucket of each (game, class) span
    is fixed by the Stockfish eval at the span's FIRST ply (REFAC-02, mirrors §3.2.1 but
    per class span, not per game). Sub-800 dropped, equal-footing filtered, sparse excluded.
  §3.4.2 Per-span ΔES Score Gap by endgame type — per-(user, cell, class) mean(gap_span)
    over the shared `sql.span_gap_ctes()` machinery (≥20 spans/user/class/cell); pooled-by-
    class IQR + per-class ELO/TC marginal means + per-class collapse d. Same span chain as
    §3.2.2, grouped by endgame_class instead of conv/par/recov bucket.
  §3.4.3 Score vs Score-Gap redundancy — per-class Pearson r / sign- / zone-agreement of the
    per-card Score and ΔES Score-Gap bullets, IQR-derived zones. Inner-join of the §3.4.1
    score CTE and the §3.4.2 gap CTE; only classes with ≥30 joined users are reported.

Faithful-port findings (validated against benchmarks-latest.md 2026-05-27):
  - §3.4.1 pooled-by-class summary (games/users/score/conv/conv_n/recov/recov_n) and the
    conv/recov TC + ELO marginals (mean, p25, p75, n) reproduce the report EXACTLY for all
    6 / 5 classes. The class-axis spread (conv 69→79%, recov 20→33%) matches.
  - §3.4.1 per-class chess-score IQR reproduces EXACTLY for rook/minor/pawn/queen/pawnless
    (mean + p10–p90). The SKILL §3.4.1 IQR query's `GROUP BY user_id, user_elo_at_game,
    elo_bucket, tc, class` FRAGMENTS the per-user unit by exact rating (yields rook n=2);
    the report was computed with a `(user, class)` pooled unit, which this port reproduces.
    Mixed n_users = 3,599 vs the report's 3,597 (mean + all percentiles exact) — a 2-user
    transcription slip in an informational table; footnoted.
  - §3.4.1 conv/recov collapse d's reproduce the report's verdict table EXACTLY
    (rook 1.24/0.32/1.33/0.20 … mixed 1.19/0.49/1.28/0.22). FINDING: §3.4.1 uses a DIFFERENT
    Cohen's d recipe from §3.2/§3.3 — `(max_mean − min_mean) / sqrt(mean(group variances))`
    (`stats.spread_d`), the spread over the root-mean of ALL group variances, NOT the
    pairwise-pooled SD `max_abs_d` uses. The SKILL.md §3.4.1 verdict text specifies it; using
    the wrong recipe gives systematically lower d's (rook conv TC 1.09 vs the report's 1.24).
  - §3.4.2 pooled-by-class IQR (n/mean/p25/p50/p75) and the per-class ELO + TC marginal
    means reproduce the report EXACTLY (all 6 classes incl. pawnless n=12). The per-class
    collapse d's use the pairwise-pooled `max_abs_d` (§3.1.5 recipe, per the SKILL). Every
    verdict WORD matches the report (TC all collapse; ELO collapse for rook/pawn/queen,
    review for minor_piece/mixed); the d magnitudes carry pair-selection slips (the report
    eyeballed sub-max pairs — e.g. pawn TC 0.10 vs the true max-pair 0.18, queen TC 0.18 vs
    0.198, queen ELO 0.16 vs 0.17), all verdict-neutral. Generator emits the deterministic d.
  - §3.4.3 reproduces the report EXACTLY: only `mixed` clears the ≥30-user joint floor
    (n=5,274, r=+0.105, sign 46.3%, strict 42.2%, strong 9.0%, score SD 0.149, gap SD
    0.049). FINDING: §3.4.3's `per_user_class_score` fragments per (user, exact-rating,
    elo_bucket, tc, class) — the SKILL query as written — which is why the small classes
    fall below the floor. This is a DIFFERENT unit from §3.4.1's report-IQR (which pools
    per (user, class)); the SKILL comment claiming §3.4.3 "reuses the §3.4.1 CTE" is
    inaccurate. Each subchapter is reproduced as the report computed it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import sql, stats
from scripts.benchmarks.render import fmt_int, fmt_signed, fmt_unsigned, markdown_table

SECTION = "SKILL.md §3.4 — endgame type breakdown (3.4.1 per-class score/conv/recov, 3.4.2 per-span ΔES gap, 3.4.3 score-vs-gap redundancy)"

_SCORE_DIGITS = 4  # proportion / gap metrics round to 4 dp in SQL (report display)
_RATE_FLOOR = 10  # §3.4.1: ≥10 bucket-games per per-user conv/recov rate unit
_343_MIN_USERS = 30  # SKILL.md §3.4.3: ≥30 joined users for a stable per-class Pearson r

# Endgame class int → name (game_position.endgame_class). pawnless = 6 (hidden in live UI).
_CLASS_NAMES: dict[int, str] = {
    1: "rook",
    2: "minor_piece",
    3: "pawn",
    4: "queen",
    5: "mixed",
    6: "pawnless",
}
# Classes carried into the conv/recov per-axis marginals + collapse verdicts (§3.4.1) —
# pawnless excluded (n far below the per-user-rate floor; hidden in the live UI).
_VERDICT_CLASSES: tuple[int, ...] = (1, 2, 3, 4, 5)

# §3.4.3 independence baselines under IQR (25/50/25) zones, r = 0 (SKILL.md §3.4.3).
_INDEP_STRICT_AGREE = 0.375  # 0.25² + 0.50² + 0.25²
_INDEP_STRONG_DISAGREE = 0.125  # 2 × 0.25²


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


# === §3.4.1 Per-class score / conversion / recovery ========================


class ClassSummary(TypedDict):
    cls: int
    games: int
    users: int
    score: float
    conv: float
    conv_n: int
    recov: float
    recov_n: int


class ScoreIqr(TypedDict):
    cls: int
    n_users: int
    mean: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class RateStat(TypedDict):
    """One (class × axis-level) per-user conv/recov rate cell."""

    n: int  # users clearing the ≥10 bucket-games floor for this metric
    mean: float  # display (SQL-rounded)
    mean_raw: float  # unrounded, feeds Cohen's d
    var: float  # var_samp, feeds Cohen's d
    p25: float
    p75: float


class ClassVerdict(TypedDict):
    cls: int
    conv_tc_d: float
    conv_elo_d: float
    recov_tc_d: float
    recov_elo_d: float


# cls -> level -> RateStat
RateMap = dict[int, dict[str, RateStat]]


class PerClass341(TypedDict):
    summary: list[ClassSummary]
    iqr: list[ScoreIqr]
    conv_tc: RateMap
    conv_elo: RateMap
    recov_tc: RateMap
    recov_elo: RateMap
    verdicts: list[ClassVerdict]


def _341_base_ctes() -> str:
    """selected_users + class_span + bucketed + classified (shared by §3.4.1 summary + marginals).

    `bucketed`: one row per (game, endgame_class) span ≥6 plies, with the user's game score,
    game-time ELO bucket, TC, and the conv/parity/recovery bucket fixed by the Stockfish eval
    at the span's FIRST ply (REFAC-02). `classified` drops sub-800 and the sparse cell.
    """
    elo_case = sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)
    bucket_expr = sql.endgame_bucket_case_sql("ep.eval_cp", "ep.eval_mate", sql.USER_COLOR_SIGN_SQL)
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.CLASS_SPAN_CTE},\n"
        "bucketed AS (\n"
        f"  SELECT g.user_id, ({elo_case}) AS elo_bucket, su.tc_bucket AS tc,\n"
        "         cs.endgame_class AS cls,\n"
        f"         {sql.USER_SCORE_EXPR} AS score,\n"
        f"         {bucket_expr} AS bucket\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN class_span cs ON cs.game_id = g.id\n"
        "  JOIN game_positions ep ON ep.game_id = g.id AND ep.ply = cs.entry_ply\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "),\n"
        "classified AS (\n"
        "  SELECT user_id, elo_bucket, tc, cls, score, bucket\n"
        "  FROM bucketed\n"
        f"  WHERE elo_bucket >= {sql.ELO_FLOOR} AND {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


def _341_summary_query() -> str:
    """Pooled-by-class game-level summary (games/users/score/conv/recov), sparse excluded."""
    return (
        f"{_341_base_ctes()}\n"
        "SELECT cls, count(*) AS games, count(DISTINCT user_id) AS users,\n"
        f"  round(avg(score)::numeric, {_SCORE_DIGITS}) AS score,\n"
        "  round((avg(CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END)\n"
        f"         FILTER (WHERE bucket = 'conversion'))::numeric, {_SCORE_DIGITS}) AS conv,\n"
        "  count(*) FILTER (WHERE bucket = 'conversion') AS conv_n,\n"
        "  round((avg(CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END)\n"
        f"         FILTER (WHERE bucket = 'recovery'))::numeric, {_SCORE_DIGITS}) AS recov,\n"
        "  count(*) FILTER (WHERE bucket = 'recovery') AS recov_n\n"
        "FROM classified GROUP BY cls ORDER BY cls"
    )


def _341_iqr_query() -> str:
    """Per-(user, class) chess-score IQR (≥10 games/user/class), pooling TC + ELO.

    NB: the per-user unit is (user, class) — NOT the SKILL query's fragment-by-exact-rating
    GROUP BY (that yields rook n=2). This reproduces the report's n_users + percentiles.
    """
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.CLASS_SPAN_CTE},\n"
        "per_user_class AS (\n"
        "  SELECT g.user_id, cs.endgame_class AS cls,\n"
        f"         avg({sql.USER_SCORE_EXPR}) AS user_class_score\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN class_span cs ON cs.game_id = g.id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        f"    AND ({sql.USER_ELO_AT_GAME_SQL}) >= {sql.ELO_FLOOR}\n"
        "  GROUP BY g.user_id, cs.endgame_class\n"
        f"  HAVING count(*) >= {_RATE_FLOOR}\n"
        ")\n"
        "SELECT cls, count(*) AS n_users,\n"
        f"  round(avg(user_class_score)::numeric, {_SCORE_DIGITS}) AS mean,\n"
        f"  round(percentile_cont(0.10) WITHIN GROUP (ORDER BY user_class_score)::numeric, {_SCORE_DIGITS}) AS p10,\n"
        f"  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY user_class_score)::numeric, {_SCORE_DIGITS}) AS p25,\n"
        f"  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY user_class_score)::numeric, {_SCORE_DIGITS}) AS p50,\n"
        f"  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY user_class_score)::numeric, {_SCORE_DIGITS}) AS p75,\n"
        f"  round(percentile_cont(0.90) WITHIN GROUP (ORDER BY user_class_score)::numeric, {_SCORE_DIGITS}) AS p90\n"
        "FROM per_user_class GROUP BY cls ORDER BY cls"
    )


def _rate_aggs(metric: str) -> str:
    """conv/recov rate aggregates over a per-user-rate CTE (FILTER on the ≥10 floor)."""
    flt = f"FILTER (WHERE {metric}_n >= {_RATE_FLOOR})"
    return (
        f"  count(*) {flt} AS {metric}_users,\n"
        f"  round((avg({metric}_rate) {flt})::numeric, {_SCORE_DIGITS}) AS {metric}_mean,\n"
        f"  (avg({metric}_rate) {flt}) AS {metric}_mean_raw,\n"
        f"  (var_samp({metric}_rate) {flt}) AS {metric}_var,\n"
        f"  round((percentile_cont(0.25) WITHIN GROUP (ORDER BY {metric}_rate) {flt})::numeric, {_SCORE_DIGITS}) AS {metric}_p25,\n"
        f"  round((percentile_cont(0.75) WITHIN GROUP (ORDER BY {metric}_rate) {flt})::numeric, {_SCORE_DIGITS}) AS {metric}_p75"
    )


def _per_user_rate_cte(name: str, group_col: str) -> str:
    """A per-user conv/recov rate CTE grouped by (user, <axis level>, class)."""
    return (
        f"{name} AS (\n"
        f"  SELECT user_id, {group_col}, cls,\n"
        "    avg(CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END) FILTER (WHERE bucket = 'conversion') AS conv_rate,\n"
        "    count(*) FILTER (WHERE bucket = 'conversion') AS conv_n,\n"
        "    avg(CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END) FILTER (WHERE bucket = 'recovery') AS recov_rate,\n"
        "    count(*) FILTER (WHERE bucket = 'recovery') AS recov_n\n"
        f"  FROM classified GROUP BY user_id, {group_col}, cls\n"
        ")"
    )


def _341_marginals_query() -> str:
    """Per-class conv/recov TC + ELO marginals (per-user rate unit). One scan, UNION'd axes."""
    aggs = f"{_rate_aggs('conv')},\n{_rate_aggs('recov')}"
    return (
        f"{_341_base_ctes()},\n"
        f"{_per_user_rate_cte('per_user_tc', 'tc')},\n"
        f"{_per_user_rate_cte('per_user_elo', 'elo_bucket')}\n"
        "SELECT 'TC' AS axis, cls, tc AS level,\n"
        f"{aggs}\n"
        f"FROM per_user_tc WHERE cls <= {_VERDICT_CLASSES[-1]} GROUP BY cls, tc\n"
        "UNION ALL\n"
        "SELECT 'ELO' AS axis, cls, elo_bucket::text AS level,\n"
        f"{aggs}\n"
        f"FROM per_user_elo WHERE cls <= {_VERDICT_CLASSES[-1]} GROUP BY cls, elo_bucket"
    )


def _rate_stat(row: RowMapping, metric: str) -> RateStat:
    return RateStat(
        n=int(row[f"{metric}_users"]),
        mean=float(row[f"{metric}_mean"]),
        mean_raw=float(row[f"{metric}_mean_raw"]),
        var=float(row[f"{metric}_var"]),
        p25=float(row[f"{metric}_p25"]),
        p75=float(row[f"{metric}_p75"]),
    )


def _axis_d(levels: dict[str, RateStat], order: Sequence[str]) -> float:
    """§3.4.1 spread-d over the axis levels (in display order) for one (class, metric).

    §3.4.1 uses the `(max−min)/sqrt(mean variance)` recipe (`stats.spread_d`), NOT the
    pairwise-pooled `max_abs_d` the other subchapters use — see SKILL.md §3.4.1.
    """
    stat_levels = [
        stats.LevelStat(lbl, rs["n"], rs["mean_raw"], rs["var"])
        for lbl in order
        if (rs := levels.get(lbl)) is not None
    ]
    return stats.spread_d(stat_levels).max_abs_d


async def compute_341(session: AsyncSession) -> PerClass341:
    summary_rows = await _fetch(session, _341_summary_query())
    iqr_rows = await _fetch(session, _341_iqr_query())
    marg_rows = await _fetch(session, _341_marginals_query())

    summary = [
        ClassSummary(
            cls=int(r["cls"]),
            games=int(r["games"]),
            users=int(r["users"]),
            score=float(r["score"]),
            conv=float(r["conv"]),
            conv_n=int(r["conv_n"]),
            recov=float(r["recov"]),
            recov_n=int(r["recov_n"]),
        )
        for r in summary_rows
    ]
    iqr = [
        ScoreIqr(
            cls=int(r["cls"]),
            n_users=int(r["n_users"]),
            mean=float(r["mean"]),
            p10=float(r["p10"]),
            p25=float(r["p25"]),
            p50=float(r["p50"]),
            p75=float(r["p75"]),
            p90=float(r["p90"]),
        )
        for r in iqr_rows
    ]

    conv_tc: RateMap = {}
    conv_elo: RateMap = {}
    recov_tc: RateMap = {}
    recov_elo: RateMap = {}
    for r in marg_rows:
        cls, level, axis = int(r["cls"]), str(r["level"]), str(r["axis"])
        conv_map = conv_tc if axis == "TC" else conv_elo
        recov_map = recov_tc if axis == "TC" else recov_elo
        conv_map.setdefault(cls, {})[level] = _rate_stat(r, "conv")
        recov_map.setdefault(cls, {})[level] = _rate_stat(r, "recov")

    elo_order = [str(a) for a in sql.ELO_ANCHORS]
    verdicts = [
        ClassVerdict(
            cls=cls,
            conv_tc_d=_axis_d(conv_tc[cls], sql.TC_ORDER),
            conv_elo_d=_axis_d(conv_elo[cls], elo_order),
            recov_tc_d=_axis_d(recov_tc[cls], sql.TC_ORDER),
            recov_elo_d=_axis_d(recov_elo[cls], elo_order),
        )
        for cls in _VERDICT_CLASSES
    ]
    return PerClass341(
        summary=summary,
        iqr=iqr,
        conv_tc=conv_tc,
        conv_elo=conv_elo,
        recov_tc=recov_tc,
        recov_elo=recov_elo,
        verdicts=verdicts,
    )


# === §3.4.2 Per-span ΔES Score Gap by endgame type =========================


class GapPooled(TypedDict):
    cls: int
    n: int
    mean: float
    p25: float
    p50: float
    p75: float


class GapLevel(TypedDict):
    n: int
    mean: float  # display (SQL-rounded)
    mean_raw: float
    var: float


# cls -> level -> GapLevel
GapMap = dict[int, dict[str, GapLevel]]


class GapClass342(TypedDict):
    pooled: list[GapPooled]
    elo: GapMap
    tc: GapMap
    elo_d: dict[int, float]
    tc_d: dict[int, float]


def _342_query() -> str:
    """Per-(user, cell, class) mean(gap_span), then pooled + ELO + TC via GROUPING SETS.

    Reuses the shared `sql.span_gap_ctes()` span chain (same as §3.2.2), grouped by
    endgame_class. Sparse cell excluded at the per-user-cell level; ≥20 spans per cell.
    """
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.span_gap_ctes()},\n"
        "per_user_class AS (\n"
        "  SELECT user_id, elo_bucket, tc, endgame_class AS cls, avg(gap_span) AS mean_gap\n"
        "  FROM gap_rows\n"
        f"  WHERE gap_span IS NOT NULL AND elo_bucket IS NOT NULL AND {sql.SPARSE_CELL_EXCLUSION}\n"
        "  GROUP BY user_id, elo_bucket, tc, endgame_class\n"
        f"  HAVING count(*) >= {sql.SECTION2_SPAN_MIN_SPANS}\n"
        ")\n"
        "SELECT cls, GROUPING(elo_bucket) AS g_elo, GROUPING(tc) AS g_tc,\n"
        "       elo_bucket, tc, count(*) AS n,\n"
        f"       round(avg(mean_gap)::numeric, {_SCORE_DIGITS}) AS mean,\n"
        "       avg(mean_gap) AS mean_raw, var_samp(mean_gap) AS var,\n"
        f"       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY mean_gap)::numeric, {_SCORE_DIGITS}) AS p25,\n"
        f"       round(percentile_cont(0.50) WITHIN GROUP (ORDER BY mean_gap)::numeric, {_SCORE_DIGITS}) AS p50,\n"
        f"       round(percentile_cont(0.75) WITHIN GROUP (ORDER BY mean_gap)::numeric, {_SCORE_DIGITS}) AS p75\n"
        "FROM per_user_class\n"
        "GROUP BY GROUPING SETS ((cls), (cls, elo_bucket), (cls, tc))"
    )


def _gap_level(row: RowMapping) -> GapLevel:
    return GapLevel(
        n=int(row["n"]),
        mean=float(row["mean"]),
        mean_raw=float(row["mean_raw"]),
        var=float(row["var"]) if row["var"] is not None else 0.0,
    )


async def compute_342(session: AsyncSession) -> GapClass342:
    rows = await _fetch(session, _342_query())
    pooled: list[GapPooled] = []
    elo: GapMap = {}
    tc: GapMap = {}
    for r in rows:
        cls = int(r["cls"])
        if int(r["g_elo"]) == 0:  # (cls, elo) row
            elo.setdefault(cls, {})[str(int(r["elo_bucket"]))] = _gap_level(r)
        elif int(r["g_tc"]) == 0:  # (cls, tc) row
            tc.setdefault(cls, {})[str(r["tc"])] = _gap_level(r)
        else:  # (cls) pooled row
            pooled.append(
                GapPooled(
                    cls=cls,
                    n=int(r["n"]),
                    mean=float(r["mean"]),
                    p25=float(r["p25"]),
                    p50=float(r["p50"]),
                    p75=float(r["p75"]),
                )
            )
    pooled.sort(key=lambda p: p["cls"])

    def axis_d(level_map: GapMap, order: Sequence[str]) -> dict[int, float]:
        out: dict[int, float] = {}
        for cls, levels in level_map.items():
            stat_levels = [
                stats.LevelStat(lbl, gl["n"], gl["mean_raw"], gl["var"])
                for lbl in order
                if (gl := levels.get(lbl)) is not None and gl["n"] >= stats.COHENS_D_MIN_N
            ]
            if len(stat_levels) >= 2:
                out[cls] = stats.max_abs_d(stat_levels).max_abs_d
        return out

    elo_order = [str(a) for a in sql.ELO_ANCHORS]
    return GapClass342(
        pooled=pooled,
        elo=elo,
        tc=tc,
        elo_d=axis_d(elo, elo_order),
        tc_d=axis_d(tc, sql.TC_ORDER),
    )


# === §3.4.3 Score vs Score-Gap redundancy ==================================


class RedundancyRow(TypedDict):
    cls: str
    n_users: int
    pearson_r: float
    sign_agreement: float
    zone_strict: float
    strong_disagree: float
    score_stdev: float
    gap_stdev: float


def _343_query() -> str:
    """Per-class Score-vs-Gap redundancy stats (Pearson r, sign/zone agreement, SDs).

    Inner-join of a per-(user, exact-rating, elo_bucket, tc, class) score unit (the SKILL
    query's fragmented GROUP BY — reproduced verbatim) with the §3.4.2 per-(user, elo, tc,
    class) gap unit, paired on (user, elo_bucket, tc, class). Zones are per-class IQR-derived.
    Only classes with ≥30 joined users are returned. Sparse cell excluded in `joined`.
    """
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{sql.CLASS_SPAN_CTE},\n"
        "per_user_class_score AS (\n"
        f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS user_elo_at_game,\n"
        f"         ({sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)}) AS elo_bucket,\n"
        "         su.tc_bucket AS tc, cs.endgame_class AS cls,\n"
        f"         avg({sql.USER_SCORE_EXPR}) AS score\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        "  JOIN class_span cs ON cs.game_id = g.id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        f"    AND ({sql.USER_ELO_AT_GAME_SQL}) >= {sql.ELO_FLOOR}\n"
        "  GROUP BY g.user_id, user_elo_at_game, elo_bucket, su.tc_bucket, cs.endgame_class\n"
        f"  HAVING count(*) >= {_RATE_FLOOR}\n"
        "),\n"
        f"{sql.span_gap_ctes()},\n"
        "per_user_class_gap AS (\n"
        "  SELECT user_id, elo_bucket, tc, endgame_class AS cls, avg(gap_span) AS gap\n"
        "  FROM gap_rows WHERE gap_span IS NOT NULL AND elo_bucket IS NOT NULL\n"
        "  GROUP BY user_id, elo_bucket, tc, endgame_class\n"
        f"  HAVING count(*) >= {sql.SECTION2_SPAN_MIN_SPANS}\n"
        "),\n"
        "joined AS (\n"
        "  SELECT s.cls, s.score, gp.gap\n"
        "  FROM per_user_class_score s\n"
        "  JOIN per_user_class_gap gp\n"
        "    ON gp.user_id = s.user_id AND gp.elo_bucket = s.elo_bucket\n"
        "   AND gp.tc = s.tc AND gp.cls = s.cls\n"
        f"  WHERE NOT (s.elo_bucket = {sql.SPARSE_CELL[0]} AND s.tc = '{sql.SPARSE_CELL[1]}')\n"
        "),\n"
        "class_iqr AS (\n"
        "  SELECT cls,\n"
        "    percentile_cont(0.25) WITHIN GROUP (ORDER BY score) AS score_p25,\n"
        "    percentile_cont(0.75) WITHIN GROUP (ORDER BY score) AS score_p75,\n"
        "    percentile_cont(0.25) WITHIN GROUP (ORDER BY gap) AS gap_p25,\n"
        "    percentile_cont(0.75) WITHIN GROUP (ORDER BY gap) AS gap_p75\n"
        "  FROM joined GROUP BY cls\n"
        "),\n"
        "classified AS (\n"
        "  SELECT j.cls, j.score, j.gap,\n"
        "    CASE WHEN j.score < ci.score_p25 THEN 'red' WHEN j.score > ci.score_p75 THEN 'green' ELSE 'neutral' END AS score_zone,\n"
        "    CASE WHEN j.gap < ci.gap_p25 THEN 'red' WHEN j.gap > ci.gap_p75 THEN 'green' ELSE 'neutral' END AS gap_zone\n"
        "  FROM joined j JOIN class_iqr ci ON ci.cls = j.cls\n"
        ")\n"
        "SELECT cls, count(*) AS n_users,\n"
        "  round(corr(score, gap)::numeric, 3) AS pearson_r,\n"
        "  round(avg(CASE WHEN sign(score - 0.5) = sign(gap) THEN 1.0 ELSE 0.0 END)::numeric, 3) AS sign_agreement,\n"
        "  round(avg(CASE WHEN score_zone = gap_zone THEN 1.0 ELSE 0.0 END)::numeric, 3) AS zone_strict,\n"
        "  round(avg(CASE WHEN (score_zone='red' AND gap_zone='green') OR (score_zone='green' AND gap_zone='red')\n"
        "               THEN 1.0 ELSE 0.0 END)::numeric, 3) AS strong_disagree,\n"
        "  round(stddev_samp(score)::numeric, 3) AS score_stdev,\n"
        "  round(stddev_samp(gap)::numeric, 3) AS gap_stdev\n"
        "FROM classified GROUP BY cls\n"
        f"HAVING count(*) >= {_343_MIN_USERS} ORDER BY cls"
    )


async def compute_343(session: AsyncSession) -> list[RedundancyRow]:
    rows = await _fetch(session, _343_query())
    return [
        RedundancyRow(
            cls=_CLASS_NAMES[int(r["cls"])],
            n_users=int(r["n_users"]),
            pearson_r=float(r["pearson_r"]),
            sign_agreement=float(r["sign_agreement"]),
            zone_strict=float(r["zone_strict"]),
            strong_disagree=float(r["strong_disagree"]),
            score_stdev=float(r["score_stdev"]),
            gap_stdev=float(r["gap_stdev"]),
        )
        for r in rows
    ]


# === rendering =============================================================


def _pct(v: float, decimals: int = 1) -> str:
    """Unsigned percentage, half-up (e.g. 0.7117 → '71.2%')."""
    return f"{fmt_unsigned(v * 100, decimals)}%"


def _pp(v: float) -> str:
    """Signed percentage points, half-up (e.g. -0.0035 → '−0.4pp')."""
    return f"{fmt_signed(v * 100, 1)}pp"


def _iqr_pct(p25: float, p75: float) -> str:
    """Integer-percent IQR string, e.g. '56–75'."""
    return f"{fmt_unsigned(p25 * 100, 0)}–{fmt_unsigned(p75 * 100, 0)}"


def _render_341(v: PerClass341) -> list[str]:
    sum_rows = [
        [
            _CLASS_NAMES[s["cls"]],
            fmt_int(s["games"]),
            fmt_int(s["users"]),
            _pct(s["score"]),
            _pct(s["conv"]),
            fmt_int(s["conv_n"]),
            _pct(s["recov"]),
            fmt_int(s["recov_n"]),
        ]
        for s in v["summary"]
    ]
    summary_tbl = markdown_table(
        [
            "class",
            "games",
            "users",
            "pooled score",
            "pooled conv",
            "conv_n",
            "pooled recov",
            "recov_n",
        ],
        sum_rows,
        ("left", *(("right",) * 7)),
    )
    iqr_rows = [
        [
            _CLASS_NAMES[i["cls"]],
            fmt_int(i["n_users"]),
            *(_pct(i[k]) for k in ("mean", "p10", "p25", "p50", "p75", "p90")),  # type: ignore[literal-required]
        ]
        for i in v["iqr"]
    ]
    iqr_tbl = markdown_table(
        ["class", "n_users", "mean", "p10", "p25", "p50", "p75", "p90"],
        iqr_rows,
        ("left", *(("right",) * 7)),
    )

    def marg_tbl(level_map: RateMap, order: Sequence[str], with_iqr: bool) -> str:
        headers = ["class", *order]
        rows = []
        for cls in _VERDICT_CLASSES:
            row = [_CLASS_NAMES[cls]]
            for lbl in order:
                rs = level_map[cls].get(lbl)
                if rs is None:
                    row.append("—")
                elif with_iqr:
                    row.append(f"{_pct(rs['mean'])} ({_iqr_pct(rs['p25'], rs['p75'])}, n{rs['n']})")
                else:
                    row.append(f"{_pct(rs['mean'])} ({rs['n']})")
            rows.append(row)
        return markdown_table(headers, rows, ("left", *(("left",) * len(order))))

    elo_order = [str(a) for a in sql.ELO_ANCHORS]
    verdict_rows = [
        [
            _CLASS_NAMES[vd["cls"]],
            f"{vd['conv_tc_d']:.2f}",
            f"{vd['conv_elo_d']:.2f}",
            f"{vd['recov_tc_d']:.2f}",
            f"{vd['recov_elo_d']:.2f}",
        ]
        for vd in v["verdicts"]
    ]
    verdict_tbl = markdown_table(
        ["class", "conv TC d", "conv ELO d", "recov TC d", "recov ELO d"],
        verdict_rows,
        ("left", *(("right",) * 4)),
    )
    return [
        "#### 3.4.1 Per-class score / conversion / recovery",
        "",
        "##### Pooled-by-class summary (sparse cell excluded)",
        "",
        summary_tbl,
        "",
        "##### Per-class chess-score IQR (per-user, ≥10 games/user/class)",
        "",
        iqr_tbl,
        "",
        "##### Per-class conversion — TC marginal (per-user, ≥10 bucket-games/user, sparse excluded)",
        "",
        marg_tbl(v["conv_tc"], sql.TC_ORDER, with_iqr=True),
        "",
        "##### Per-class recovery — TC marginal",
        "",
        marg_tbl(v["recov_tc"], sql.TC_ORDER, with_iqr=True),
        "",
        "##### Per-class conversion — ELO marginal (per-user, ≥10 bucket-games/user, pooling TC)",
        "",
        marg_tbl(v["conv_elo"], elo_order, with_iqr=False),
        "",
        "##### Per-class recovery — ELO marginal",
        "",
        marg_tbl(v["recov_elo"], elo_order, with_iqr=False),
        "",
        "##### Collapse verdict — TC and ELO axes (per-user Cohen's d; LLM applies the threshold word)",
        "",
        verdict_tbl,
    ]


def _render_342(v: GapClass342) -> list[str]:
    pooled_rows = [
        [
            _CLASS_NAMES[p["cls"]],
            fmt_int(p["n"]),
            _pp(p["mean"]),
            _pp(p["p25"]),
            _pp(p["p50"]),
            _pp(p["p75"]),
        ]
        for p in v["pooled"]
    ]
    pooled_tbl = markdown_table(
        ["class", "n_users", "mean", "p25", "p50", "p75"],
        pooled_rows,
        ("left", *(("right",) * 5)),
    )

    def marg_tbl(
        level_map: GapMap, order: Sequence[str], d_map: dict[int, float], d_label: str
    ) -> str:
        headers = ["class", *order, d_label]
        rows = []
        for cls in _VERDICT_CLASSES:
            row = [_CLASS_NAMES[cls]]
            for lbl in order:
                gl = level_map.get(cls, {}).get(lbl)
                row.append(_pp(gl["mean"]) if gl is not None else "—")
            d = d_map.get(cls)
            row.append(f"{d:.2f}" if d is not None else "—")
            rows.append(row)
        return markdown_table(headers, rows, ("left", *(("right",) * (len(order) + 1))))

    elo_order = [str(a) for a in sql.ELO_ANCHORS]
    return [
        "#### 3.4.2 Per-span ΔES Score Gap by endgame type",
        "",
        "##### Per-class pooled distribution (per-user `mean(gap_span)`, sparse cell excluded)",
        "",
        pooled_tbl,
        "",
        "##### Per-class ELO marginal (mean per cell + collapse d)",
        "",
        marg_tbl(v["elo"], elo_order, v["elo_d"], "ELO d"),
        "",
        "##### Per-class TC marginal (mean per cell + collapse d)",
        "",
        marg_tbl(v["tc"], sql.TC_ORDER, v["tc_d"], "TC d"),
    ]


def _render_343(rows: list[RedundancyRow]) -> list[str]:
    body = [
        [
            r["cls"],
            fmt_int(r["n_users"]),
            f"{fmt_signed(r['pearson_r'], 3)}",
            _pct(r["sign_agreement"]),
            _pct(r["zone_strict"]),
            _pct(r["strong_disagree"]),
            fmt_unsigned(r["score_stdev"], 3),
            fmt_unsigned(r["gap_stdev"], 3),
        ]
        for r in rows
    ]
    tbl = markdown_table(
        [
            "class",
            "n_users",
            "Pearson r",
            "sign_agree",
            "strict zone-agree",
            "strong disagree",
            "score SD",
            "gap SD",
        ],
        body,
        ("left", *(("right",) * 7)),
    )
    return [
        "#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy",
        "",
        "##### Per-class summary (classes clearing the ≥30 joined-user floor; IQR-derived zones)",
        "",
        tbl,
        "",
        "##### Independence baselines (per metric, 25/50/25 red/neutral/green under IQR zones)",
        "",
        f"- Strict zone-agreement under independence (r=0): {_pct(_INDEP_STRICT_AGREE)}",
        f"- Strong disagreement under independence (r=0): {_pct(_INDEP_STRONG_DISAGREE)}",
    ]


def render(v341: PerClass341, v342: GapClass342, v343: list[RedundancyRow]) -> str:
    parts = ["### 3.4 Endgame Type Breakdown", ""]
    parts += _render_341(v341)
    parts += ["", "---", ""]
    parts += _render_342(v342)
    parts += ["", "---", ""]
    parts += _render_343(v343)
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    v341 = await compute_341(session)
    v342 = await compute_342(session)
    v343 = await compute_343(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values_341": v341,
        "values_342": v342,
        "values_343": v343,
        "markdown": render(v341, v342, v343),
    }
