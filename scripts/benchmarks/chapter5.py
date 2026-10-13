"""Chapter 5 — Flaw-Delta Zones (SKILL.md §5).

Basis (Phase 239 D-07/D-08): the **Phase 212 full-analysis lane** only. A game counts when
it is an armed `benchmark_selection` row in the classical or rapid tranche AND carries full
evals, full PVs and tactic blobs. The blitz and bullet tranches never enter the basis (blitz
is half finished, bullet is empty); the app registries map those TCs to the rapid zones.

Computes, for each of the 12 flaw-delta metrics (blunder, mistake and the 10 context tags),
every cohort user's **you−opponent delta** on a **per-100-of-their-own-moves,
paired-per-game** basis (Phase 114 D-01 unified estimator), then emits Q1/Q3 quartiles + ELO/TC
marginals + the established Cohen's-d collapse verdict per axis (FLAWBMK-01/02/03), plus a
per-metric viability diagnostic (Phase 114 D-06) and a noise-only IQR diagnostic.

Phase 114 D-01 estimator: for each game, delta = (player_tag_count − opp_tag_count) / user_moves
(a proportion), where user_moves is derived from games.ply_count (Phase 114.1):
FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black (no game_positions scan). The
SQL stores the raw proportion; the ×100 scaling to "per-100-moves" display units is
applied at the render layer via the "pp" unit formatter (SKILL.md "Display formatting"
invariant: never bake scaling into SQL, apply at the rendering layer). Per-cohort-user
delta = mean of those per-game deltas.

The 12 metrics use integer/boolean column predicates — tag name strings do NOT appear
in the SQL (game_flaws encodes tempo/phase as integers, opportunity/impact as booleans).
The two combo metrics (hasty+miss, low-clock+miss) and the overall flaw rate were dropped
in Phase 239 (D-00f).

Tactic metrics (Phase 239 D-06): 38 = 19 tactic families x {missed, allowed}. Per game the
estimator is the raw count difference (player − opponent) of game_flaws rows whose motif for
that orientation is in the family's FAMILY_TO_MOTIF_INTS ints AND whose confidence is at least
MIN_TACTIC_CHIP_CONFIDENCE (both IMPORTED from the app, so the benchmark counts exactly what
the app counts). It is NOT divided by user moves; per-user mean over >= 20 games, shown per
100 games via the "per100g" render unit.

This is benchmark-computation ONLY: no endpoint, no UI, no committed zone constants,
no DB table, no migration (Phase 114 D-09). The zone registries are hand-authored from the report.

Fast refresh path (this chapter alone, minutes instead of the full generator run):
    uv run python -m scripts.benchmarks.chapter5 --db benchmark --out temp/239-benchmark/run
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import db_url_for_target
from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS
from app.services.library_service import MIN_TACTIC_CHIP_CONFIDENCE
from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql
from scripts.benchmarks.render import fmt_int, fmt_unsigned, fmt_value, markdown_table

SECTION = (
    "SKILL.md §5 — flaw-delta + tactic zones (12 flaw + 38 tactic metrics on the full-analysis lane: "
    "per-(ELO×TC) Q1/Q3 + collapse verdicts + viability + noise diagnostic)"
)

# Phase 239 D-08: the only benchmark_selection tranches whose full-analysis lane has
# finished. Blitz is half finished and bullet is empty; both read the rapid zones in the app
# registry (ZONE_TC_FOR) and are never computed here. Refresh = re-run §5 once they finish.
FULL_ANALYSIS_TRANCHES: Final[tuple[sql.TcBucket, ...]] = ("classical", "rapid")

# Per-user analyzed-games floor for flaw-delta metrics (Phase 114 D-08).
# Matches sql.ENDGAME_MIN_GAMES = 20 for endgame metrics — consistent uniform floor.
FLAW_DELTA_MIN_GAMES: int = 20

# SQL rounding digits for delta metrics (proportion scale, signed floats). Using 6 dp
# because proportion-scale values are ~100× smaller than the rendered "pp" values;
# 4 dp would collapse small metrics like low_clock to near-zero after percentile rounding.
# The ×100 scaling to per-100-moves display units is applied at render time via "pp" unit.
_DELTA_DIGITS: int = 6

# Per-cell contributor floor (Phase 114 D-07, Phase 239 D-10): a marginal level with fewer
# contributing user-cells than this is removed from the marginals and the verdicts inside
# compute() and listed as a thin level, so a registry author falls back to the pooled band.
_CELL_CONTRIBUTOR_FLOOR: int = 30

# IQR of a normal distribution = 1.349 SD. Turns a sampling-noise SD into a noise-only IQR.
_NORMAL_IQR_PER_SD: float = 1.349

# A metric is viable for a zone when its pooled IQR is not degenerate (p25 < p75) AND at
# least this share of user-cells have a non-zero player event count (research A2). The owner
# confirms the resulting has_zone set at the plan 239-06 checkpoint.
VIABILITY_MIN_PCT_NONZERO: float = 50.0

# The 12 flaw-delta metrics: (metric_key, delta_column_in_per_user_cte).
# Order: severity (2), tempo (3), phase (3), opportunity/impact (4).
FLAW_DELTA_METRICS: tuple[tuple[str, str], ...] = (
    ("mistake", "delta_mistake"),
    ("blunder", "delta_blunder"),
    ("low_clock", "delta_low_clock"),
    ("hasty", "delta_hasty"),
    ("unrushed", "delta_unrushed"),
    ("opening", "delta_opening"),
    ("middlegame", "delta_middlegame"),
    ("endgame_phase", "delta_endgame_phase"),
    ("miss", "delta_miss"),
    ("lucky", "delta_lucky"),
    ("reversed", "delta_reversed"),
    ("squandered", "delta_squandered"),
)

# Tag predicates over game_flaws integer/boolean columns (game_flaws_repository.py):
#   _TEMPO_INT = {"low-clock": 0, "hasty": 1, "unrushed": 2}
#   _PHASE_INT = {"opening": 0, "middlegame": 1, "endgame": 2}
#   severity: 1 = mistake, 2 = blunder; booleans is_miss / is_lucky / is_reversed / is_squandered.
# One module-level dict shared by compute() and the viability query (no drift).
_FLAW_TAG_PREDICATES: dict[str, str] = {
    "mistake": "gf.severity = 1",
    "blunder": "gf.severity = 2",
    "low_clock": "gf.tempo = 0",
    "hasty": "gf.tempo = 1",
    "unrushed": "gf.tempo = 2",
    "opening": "gf.phase = 0",
    "middlegame": "gf.phase = 1",
    "endgame_phase": "gf.phase = 2",
    "miss": "gf.is_miss = TRUE",
    "lucky": "gf.is_lucky = TRUE",
    "reversed": "gf.is_reversed = TRUE",
    "squandered": "gf.is_squandered = TRUE",
}

# Tactic orientations (Phase 239 D-06). `missed_tactic_*` / `allowed_tactic_*` on game_flaws
# are the motif (SmallInteger) and winner-confidence (0-100) of the tactic the flaw missed /
# allowed.
TACTIC_ORIENTATIONS: tuple[str, str] = ("missed", "allowed")

# The 38 tactic metrics (19 families x 2 orientations): (metric_key, delta_column). Key =
# `tactic_{family}_{orientation}`, in FAMILY_TO_MOTIF_INTS order, missed before allowed. The
# family -> motif-int mapping is IMPORTED (never copied) so a family remap in the app
# re-groups the benchmark automatically.
TACTIC_METRICS: tuple[tuple[str, str], ...] = tuple(
    (f"tactic_{family}_{orientation}", f"delta_tactic_{family}_{orientation}")
    for family in FAMILY_TO_MOTIF_INTS
    for orientation in TACTIC_ORIENTATIONS
)

# metric_key -> (family, orientation), for the compact tactic table and the predicates.
TACTIC_METRIC_PARTS: dict[str, tuple[str, str]] = {
    f"tactic_{family}_{orientation}": (family, orientation)
    for family in FAMILY_TO_MOTIF_INTS
    for orientation in TACTIC_ORIENTATIONS
}


def _tactic_predicate(family: str, orientation: str) -> str:
    """SQL predicate for one tactic metric.

    The orientation's motif IN the family's ints AND its confidence >= MIN_TACTIC_CHIP_CONFIDENCE:
    the exact gate the app's tactic comparison uses, so the benchmark counts what the app counts.

    Every interpolated identifier and int comes from closed in-code sets (FAMILY_TO_MOTIF_INTS
    keys/values, the two orientation literals, the imported confidence constant), never from
    input.
    """
    ints = ", ".join(str(i) for i in FAMILY_TO_MOTIF_INTS[family])
    return (
        f"gf.{orientation}_tactic_motif IN ({ints}) "
        f"AND gf.{orientation}_tactic_confidence >= {MIN_TACTIC_CHIP_CONFIDENCE}"
    )


_TACTIC_PREDICATES: dict[str, str] = {
    key: _tactic_predicate(family, orientation)
    for key, (family, orientation) in TACTIC_METRIC_PARTS.items()
}

# Every metric the SQL computes, flaw first. One predicate table feeds the zone query and the
# viability query.
_ALL_METRICS: tuple[tuple[str, str], ...] = FLAW_DELTA_METRICS + TACTIC_METRICS
_ALL_PREDICATES: dict[str, str] = {**_FLAW_TAG_PREDICATES, **_TACTIC_PREDICATES}

# Even ply = white mover, odd ply = black mover (canonical ply-parity convention).
# Player flaws: mover parity matches user_color.
_PLAYER_FILTER: str = (
    "(gf.ply % 2 = 0 AND bg.user_color = 'white') OR (gf.ply % 2 = 1 AND bg.user_color = 'black')"
)
# Opponent flaws: mover parity is the OTHER color (never flip the convention).
_OPP_FILTER: str = (
    "(gf.ply % 2 = 0 AND bg.user_color = 'black') OR (gf.ply % 2 = 1 AND bg.user_color = 'white')"
)


class MetricBlock(TypedDict):
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]  # only the axes whose verdict could be computed
    thin_levels: list[str]  # "<AXIS> <label>" of marginal levels dropped by the cell floor
    degenerate: bool  # pooled p25 == p75 (zero-width IQR)


class ViabilityRow(TypedDict):
    metric: str
    users_contributing: int  # user-cells where the player has >= 1 event of this metric
    users_total: int  # user×(ELO,TC) cells passing the FLAW_DELTA_MIN_GAMES floor
    pct_nonzero: float  # users_contributing / users_total * 100
    median_events_per_user: float  # median per-user numerator event count (unscaled)
    degenerate_iqr: bool  # pooled p25 == p75 (filled after the blocks are computed)
    zone_viable: bool  # not degenerate_iqr and pct_nonzero >= VIABILITY_MIN_PCT_NONZERO


class NoiseRow(TypedDict):
    """Noise-only IQR: the IQR per-user values would show if every user had the same true gap.

    `1.349 * sqrt(mean over user-cells of var(per-game delta) / n_games)`. Reported next to
    the observed IQR, never applied to the zones (a methodology change is an owner call).
    """

    metric: str
    pooled_noise_iqr: float
    tc_noise_iqr: dict[str, float]


class CohortSummary(TypedDict):
    n_analyzed_games: int  # total analyzed games feeding §5 (all qualifying user×cell rows)
    n_user_cells: int  # user×(ELO,TC) rows passing the floor (= the pooled `n`)
    n_distinct_users: int  # distinct cohort users (a user spanning buckets counts once)


class Chapter5Values(TypedDict):
    flaw: dict[str, MetricBlock]
    tactic: dict[str, MetricBlock]  # 38 tactic metrics, per 100 games (family x orientation)
    viability: list[ViabilityRow]
    noise: dict[str, NoiseRow]
    cohort: CohortSummary


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


def _base_games_cte() -> str:
    """The full-analysis `base_games` CTE, shared by `_per_user_cte()` and `_viability_sql()`.

    One definition, two call sites: the zone query and the viability query can never drift
    onto different games. Each predicate has a reason:
      - `bs.armed`: unarmed rows are invisible to every claim lane, so they cannot have been
        analyzed.
      - `bs.tc_tranche IN (...)`: D-08, only the finished tranches (FULL_ANALYSIS_TRANCHES).
      - BASE_GAME_FILTER: rated, human opponent, equal-footing, and the TC anchor
        `g.time_control_bucket::text = su.tc_bucket` that keeps ONE selected_users row per game.
      - `full_evals_completed_at` / `full_pv_completed_at`: the engine finished the game.
      - `blobs_completed_at`: tactic motifs are suppressed to NULL while a flaw blob is
        pending, so a game without it would contribute false zero tactic counts.
    `lichess_evals_at` is deliberately NOT used as a provenance filter: lichess-arm lane games
    keep it set even though their stored evals were homogenized to ours.
    """
    tranches = ", ".join(f"'{t}'" for t in FULL_ANALYSIS_TRANCHES)
    return (
        "base_games AS MATERIALIZED (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag,\n"
        "         su.tc_bucket AS tc,\n"
        # user_moves lives here (not in a self-joined helper CTE): with the lane's small
        # base the planner estimates 1 row, picks a nested loop and the helper self-join
        # went O(n^2) (a 10+ min run). Floor/ceil of ply_count/2 = the user's own moves.
        # KNOWN FLIP (PR #420 review): white moves first, so white should get CEIL and black
        # FLOOR (the app was fixed, library_service._user_moves_from_ply_count). Kept here so
        # the committed §5 run and its diff gate stay reproducible; fix it together with the
        # next §5 refresh and diff-gate regeneration. Off by at most one move per game.
        "         CASE WHEN g.user_color = 'white' THEN FLOOR(g.ply_count / 2.0)\n"
        "              ELSE CEIL(g.ply_count / 2.0) END AS user_moves\n"
        "  FROM benchmark_selection bs\n"
        "  JOIN games g ON g.id = bs.game_id\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE bs.armed AND bs.tc_tranche IN ({tranches})\n"
        f"    AND {sql.BASE_GAME_FILTER}\n"
        "    AND g.full_evals_completed_at IS NOT NULL\n"
        "    AND g.full_pv_completed_at IS NOT NULL\n"
        "    AND g.blobs_completed_at IS NOT NULL\n"
        ")"
    )


def _per_user_cte() -> str:
    """Per-user flaw-delta CTE chain for all metrics (one row per user per ELO×TC cell).

    CTE chain:
      selected_users  — canonical cohort filter (benchmark_selected_users + completed checkpoint)
      base_games      — the full-analysis lane games (`_base_games_cte()`); MATERIALIZED to
                        narrow the game_flaws scan. Carries `user_moves` derived from
                        games.ply_count (Phase 114.1): FLOOR(ply_count/2) for white,
                        CEIL(ply_count/2) for black (no game_positions scan; known flip,
                        see base_games).
      per_game_tags   — per-game player/opponent tag counts for all metrics, driven from
                        base_games (ALL analyzed games) LEFT JOIN game_flaws so clean games
                        count as a 0 delta (not dropped). The ≥20 floor below is therefore over
                        analyzed games, matching the documented estimator.
      per_game_delta  — per-game signed delta = (player − opp) / NULLIF(user_moves, 0)
                        (proportion unit — NOT ×100; ×100 applied at render layer via "pp"
                        unit); rows with user_moves = 0 are dropped.
      per_user        — mean delta per user per (game-time ELO, TC) cell plus the sampling
                        variance of that mean (`nv_<key>`, the noise diagnostic); HAVING
                        count(*) >= FLAW_DELTA_MIN_GAMES (Phase 114 D-08 floor = 20).
      pu              — MATERIALIZED with SPARSE_CELL_EXCLUSION (Phase 114 D-07 cell floor).
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")

    def player_count(predicate: str) -> str:
        """COUNT(*) FILTER for player flaws matching a tag predicate."""
        return f"COUNT(*) FILTER(WHERE ({_PLAYER_FILTER}) AND ({predicate}))"

    def opp_count(predicate: str) -> str:
        """COUNT(*) FILTER for opponent flaws matching a tag predicate."""
        return f"COUNT(*) FILTER(WHERE ({_OPP_FILTER}) AND ({predicate}))"

    # Build per_game_tags column list: one player column + one opponent column per metric.
    tag_cols = []
    for metric_key, _ in _ALL_METRICS:
        pred = _ALL_PREDICATES[metric_key]
        tag_cols.append(f"    {player_count(pred)} AS p_{metric_key}")
        tag_cols.append(f"    {opp_count(pred)} AS o_{metric_key}")
    tag_cols_sql = ",\n".join(tag_cols)

    # Build per_game_delta column list. Flaw metrics: (player − opp) / NULLIF(user_moves, 0),
    # proportion units (NOT ×100; the ×100 scaling to "per-100-moves" display units is applied
    # at the render layer via the "pp" unit formatter, per the SKILL.md "Display formatting"
    # invariant: never bake scaling into SQL). Tactic metrics: the raw per-game count
    # difference (player − opp), NOT divided by moves (research Pattern 2); the "per100g" unit
    # renders it times 100.
    delta_cols = []
    for metric_key, delta_col in FLAW_DELTA_METRICS:
        delta_cols.append(
            f"    (p_{metric_key} - o_{metric_key})::float"
            f" / NULLIF(pgt.user_moves, 0) AS {delta_col}"
        )
    for metric_key, delta_col in TACTIC_METRICS:
        delta_cols.append(f"    (p_{metric_key} - o_{metric_key})::float AS {delta_col}")
    delta_cols_sql = ",\n".join(delta_cols)

    # Build per_user column list: avg of each delta column, plus the variance of that mean
    # (var_samp / n) for the noise-only IQR diagnostic. HAVING count(*) >= 20 keeps var_samp
    # defined.
    avg_cols = []
    for metric_key, delta_col in _ALL_METRICS:
        avg_cols.append(f"    avg(pgd.{delta_col}) AS {delta_col}")
        avg_cols.append(f"    var_samp(pgd.{delta_col}) / count(*) AS nv_{metric_key}")
    avg_cols_sql = ",\n".join(avg_cols)

    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{_base_games_cte()},\n"
        # per_game_tags: per-game player/opponent tag counts for all metrics.
        # Driven from base_games (ALL analyzed games) with a LEFT JOIN to game_flaws, so a
        # clean game (zero detected flaws) still contributes a row with all counts = 0 and
        # therefore a delta of 0 — a clean game IS evidence of a zero you−opponent delta.
        # (A prior INNER JOIN to game_flaws silently dropped ~70% of analyzed games, inflating
        # every metric's magnitude and making the ≥20 floor "≥20 FLAWED games" rather than the
        # documented "≥20 analyzed games".) With the LEFT JOIN, gf.* is NULL on clean games, so
        # each COUNT(*) FILTER(...) predicate (which references gf.ply / gf.tempo / ...) excludes
        # the NULL row and yields 0.
        "per_game_tags AS (\n"
        "  SELECT\n"
        "    bg.game_id,\n"
        "    bg.user_id, bg.ueag, bg.tc, bg.user_color,\n"
        "    bg.user_moves,\n"
        f"{tag_cols_sql}\n"
        "  FROM base_games bg\n"
        "  LEFT JOIN game_flaws gf ON gf.game_id = bg.game_id AND gf.user_id = bg.user_id\n"
        "  GROUP BY bg.game_id, bg.user_id, bg.ueag, bg.tc, bg.user_color, bg.user_moves\n"
        "),\n"
        # per_game_delta: signed proportion delta per game (Phase 114 D-01 estimator).
        # Proportion unit — ×100 is applied at the render layer ("pp" unit formatter).
        # Games with user_moves = 0 are dropped (WHERE guard; NULLIF also handles division).
        "per_game_delta AS (\n"
        "  SELECT pgt.user_id, pgt.ueag, pgt.tc,\n"
        f"{delta_cols_sql}\n"
        "  FROM per_game_tags pgt\n"
        "  WHERE pgt.user_moves > 0\n"
        "),\n"
        # per_user: mean delta per user per (game-time ELO, TC) cell.
        # ELO floor drops sub-800 rows. HAVING floor = 20 analyzed games (Phase 114 D-08).
        "per_user AS (\n"
        f"  SELECT pgd.user_id, ({bucket_case}) AS elo_bucket, pgd.tc,\n"
        f"{avg_cols_sql}\n"
        "  FROM per_game_delta pgd\n"
        f"  WHERE pgd.ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY pgd.user_id, elo_bucket, pgd.tc\n"
        f"  HAVING count(*) >= {FLAW_DELTA_MIN_GAMES}\n"
        "),\n"
        # pu: sparse-cell excluded; Phase 114 D-07 cell floor enforced via SPARSE_CELL_EXCLUSION.
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


def _metric_select(metric: str, delta_col: str) -> str:
    """One metric's aggregation SELECT over `pu` (pooled + ELO + TC grouping sets).

    Appends `noise_iqr` to the canonical distribution columns: the IQR the per-user values
    would show from pure sampling noise (mean of `nv_<key>` over the grouped user-cells).
    Folded into the same scan as the distribution so the diagnostic costs no extra pass.
    """
    return (
        f"SELECT '{metric}' AS metric,\n"
        f"{dist.agg_select(delta_col, digits=_DELTA_DIGITS)},\n"
        f"  {_NORMAL_IQR_PER_SD} * sqrt(avg(nv_{metric})) AS noise_iqr\n"
        f"FROM pu {dist.GROUPING_SETS}"
    )


def _safe_verdict(axis: str, marginals: Sequence[dist.Marginal]) -> dist.Verdict | None:
    """`dist.verdict` that returns None when the verdict cannot be computed.

    `stats.max_abs_d` raises ValueError below two levels with n >= COHENS_D_MIN_N and divides
    by the pooled SD (ZeroDivisionError when every user-cell has the same value). Once the
    cell floor thins the marginals a few metrics legitimately have no verdict on an axis.
    """
    try:
        return dist.verdict(axis, marginals)
    except ValueError, ZeroDivisionError:
        return None


def _apply_floor(
    axis: str, marginals: Sequence[dist.Marginal]
) -> tuple[list[dist.Marginal], list[str]]:
    """Drop marginal levels below `_CELL_CONTRIBUTOR_FLOOR` contributors (D-10, Pitfall 4).

    Returns (kept levels, thin level labels "<AXIS> <label>"). Before Phase 239 the floor was
    only interpolated into report text; thin levels leaked into the marginals and verdicts.
    """
    kept: list[dist.Marginal] = []
    thin: list[str] = []
    for m in marginals:
        if m["dist"]["n"] < _CELL_CONTRIBUTOR_FLOOR:
            thin.append(f"{axis} {m['label']}")
        else:
            kept.append(m)
    return kept, thin


def _assemble_block(
    pooled: dist.Distribution,
    elo: Sequence[dist.Marginal],
    tc: Sequence[dist.Marginal],
) -> MetricBlock:
    """Floor the marginals, then compute the verdicts that can be computed."""
    elo_kept, elo_thin = _apply_floor("ELO", elo)
    tc_kept, tc_thin = _apply_floor("TC", tc)
    candidates = (_safe_verdict("TC", tc_kept), _safe_verdict("ELO", elo_kept))
    return MetricBlock(
        pooled=pooled,
        elo_marginal=elo_kept,
        tc_marginal=tc_kept,
        verdicts=[v for v in candidates if v is not None],
        thin_levels=[*tc_thin, *elo_thin],
        degenerate=pooled["p25"] == pooled["p75"],
    )


def _noise_row(metric: str, metric_rows: Sequence[RowMapping]) -> NoiseRow:
    """Collect the `noise_iqr` column of a metric's pooled and per-TC grouping-set rows."""
    pooled_noise = 0.0
    tc_noise: dict[str, float] = {}
    for row in metric_rows:
        value = float(row["noise_iqr"] or 0.0)
        if row["elo_bucket"] is not None:
            continue
        if row["tc"] is not None:
            tc_noise[str(row["tc"])] = value
        else:
            pooled_noise = value
    return NoiseRow(metric=metric, pooled_noise_iqr=pooled_noise, tc_noise_iqr=tc_noise)


def _is_zone_viable(degenerate: bool, pct_nonzero: float) -> bool:
    """zone_viable rule (research A2): non-degenerate pooled IQR and enough non-zero cells."""
    return not degenerate and pct_nonzero >= VIABILITY_MIN_PCT_NONZERO


async def compute(session: AsyncSession) -> Chapter5Values:
    """Compute all metric blocks + viability + noise diagnostic.

    Builds the per-user CTE chain once, then runs one aggregation per metric in one UNION ALL
    query. Viability is a separate lightweight query (Phase 114 D-06).
    """
    selects = [_metric_select(metric, col) for metric, col in _ALL_METRICS]
    query = _per_user_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    blocks: dict[str, MetricBlock] = {}
    noise: dict[str, NoiseRow] = {}
    for metric, _ in _ALL_METRICS:
        metric_rows = [r for r in rows if r["metric"] == metric]
        pooled, elo, tc = dist.split_grouping_sets(metric_rows)
        blocks[metric] = _assemble_block(pooled, elo, tc)
        noise[metric] = _noise_row(metric, metric_rows)

    viability, cohort = await _compute_viability(session)
    # degenerate_iqr / zone_viable need the pooled IQR from the blocks computed above.
    for row in viability:
        degenerate = blocks[row["metric"]]["degenerate"]
        row["degenerate_iqr"] = degenerate
        row["zone_viable"] = _is_zone_viable(degenerate, row["pct_nonzero"])

    return Chapter5Values(
        flaw={key: blocks[key] for key, _ in FLAW_DELTA_METRICS},
        tactic={key: blocks[key] for key, _ in TACTIC_METRICS},
        viability=viability,
        noise=noise,
        cohort=cohort,
    )


def _viability_sql() -> str:
    """Viability query: one row per user×(ELO,TC) cell with raw player event counts.

    Driven from the same `_base_games_cte()` as the zone query (ALL analyzed games, LEFT
    JOIN game_flaws) so the ≥20 floor is over analyzed games. The cell set is close to, but
    NOT identical with, the zone query's `pu` cells: it applies neither SPARSE_CELL_EXCLUSION
    (so the sparse (2400, classical) cell is included) nor the per_game_delta
    `user_moves > 0` guard (so a zero-move game still counts toward the floor).
    NOTE: users_total counts these user×cell rows, not distinct users (a user spanning
    ELO/TC buckets contributes one cell per bucket). COUNT(*) FILTER(...) is used directly
    (no outer SUM — nested aggregates are illegal in SQL); the GROUP BY (user_id,
    elo_bucket, tc) already scopes each count to one user's cell.
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    per_user_raw_cols = ",\n  ".join(
        f"COUNT(*) FILTER(WHERE ({_PLAYER_FILTER}) AND ({_ALL_PREDICATES[m]})) AS raw_{m}"
        for m, _ in _ALL_METRICS
    )
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        f"{_base_games_cte()},\n"
        "per_user_raw AS (\n"
        f"  SELECT bg.user_id, ({bucket_case}) AS elo_bucket, bg.tc,\n"
        "  COUNT(DISTINCT bg.game_id) AS n_games,\n"
        f"  {per_user_raw_cols}\n"
        "  FROM base_games bg\n"
        "  LEFT JOIN game_flaws gf ON gf.game_id = bg.game_id AND gf.user_id = bg.user_id\n"
        f"  WHERE bg.ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY bg.user_id, elo_bucket, bg.tc\n"
        f"  HAVING COUNT(DISTINCT bg.game_id) >= {FLAW_DELTA_MIN_GAMES}\n"
        ")\n"
        "SELECT * FROM per_user_raw"
    )


def _median(values: Sequence[int]) -> float:
    """Median of integer event counts (0.0 for an empty sequence)."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return float(ordered[n // 2])
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


async def _compute_viability(
    session: AsyncSession,
) -> tuple[list[ViabilityRow], CohortSummary]:
    """Per-metric viability diagnostic (Phase 114 D-06).

    For each metric: counts user-cells with at least one player event and the median raw
    event count per user-cell. Lets the registry author assess whether a metric is stable enough for
    zone calibration (e.g. low_clock at ~76% non-zero vs squandered at ~99.5%).
    `degenerate_iqr` / `zone_viable` are filled by compute() once the blocks exist.
    """
    raw_rows = await _fetch(session, _viability_sql())
    users_total = len(raw_rows)

    viability_rows: list[ViabilityRow] = []
    for metric_key, _ in _ALL_METRICS:
        raw_col = f"raw_{metric_key}"
        events = [int(r[raw_col] or 0) for r in raw_rows]
        nonzero_count = sum(1 for e in events if e > 0)
        pct_nonzero = nonzero_count / users_total * 100 if users_total > 0 else 0.0
        viability_rows.append(
            ViabilityRow(
                metric=metric_key,
                users_contributing=nonzero_count,
                users_total=users_total,
                pct_nonzero=round(pct_nonzero, 1),
                median_events_per_user=round(_median(events), 1),
                degenerate_iqr=False,  # filled by compute()
                zone_viable=False,  # filled by compute()
            )
        )

    cohort = CohortSummary(
        n_analyzed_games=sum(int(r["n_games"] or 0) for r in raw_rows),
        n_user_cells=users_total,
        n_distinct_users=len({r["user_id"] for r in raw_rows}),
    )
    return viability_rows, cohort


# Metric display names for section headings (5.1-5.12, same order as FLAW_DELTA_METRICS).
_FLAW_LABELS: dict[str, str] = {
    "mistake": "5.1 Mistakes (severity = 1)",
    "blunder": "5.2 Blunders (severity = 2)",
    "low_clock": "5.3 Low-Clock Flaws (tempo = 0)",
    "hasty": "5.4 Hasty Flaws (tempo = 1)",
    "unrushed": "5.5 Unrushed Flaws (tempo = 2)",
    "opening": "5.6 Opening-Phase Flaws (phase = 0)",
    "middlegame": "5.7 Middlegame Flaws (phase = 1)",
    "endgame_phase": "5.8 Endgame-Phase Flaws (phase = 2)",
    "miss": "5.9 Missed-Win Flaws (is_miss)",
    "lucky": "5.10 Lucky-Escape Flaws (is_lucky)",
    "reversed": "5.11 Reversed Advantage Flaws (is_reversed)",
    "squandered": "5.12 Squandered Win Flaws (is_squandered)",
}


def render(values: Chapter5Values) -> str:
    """Render the §5 Flaw-Delta Zones chapter as a markdown string."""
    tranches = " + ".join(FULL_ANALYSIS_TRANCHES)
    parts: list[str] = ["## 5. Flaw-Delta Zones", ""]
    parts += [
        f"> **Basis (Phase 239 D-07/D-08)**: the full-analysis lane only ({tranches} tranches of",
        "> `benchmark_selection`: armed games with full evals, full PVs and tactic blobs done).",
        "> Blitz and bullet are not computed here; the app registries map them to the rapid zones",
        "> (D-09 stopgap) until their full-analysis samples finish.",
        ">",
        "> **D-01 unified estimator**: per game, delta = (player_tag_count − opp_tag_count)",
        "> / user_moves_in_game (proportion); displayed as per-100-moves via ×100 at the",
        '> render layer ("pp" unit). user_moves derived from `games.ply_count` (Phase 114.1):',
        "> FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black — no game_positions scan.",
        "> Per-cohort-user delta = mean",
        f"> over ≥{FLAW_DELTA_MIN_GAMES} analyzed games. Negative delta means cohort",
        "> users commit fewer flaws of this type than equally-rated opponents.",
        ">",
        f"> **Cell floor**: marginal levels with <{_CELL_CONTRIBUTOR_FLOOR} contributing",
        "> user-cells are removed from the marginals and verdicts (listed as thin levels);",
        "> a registry author falls back to the pooled band for them (D-10).",
        "> **Sparse cell**: (2400, classical) excluded from marginals and verdicts (see §1).",
        "",
    ]

    for metric_key, _ in FLAW_DELTA_METRICS:
        block = values["flaw"][metric_key]
        parts += _metric_section(
            f"### {_FLAW_LABELS[metric_key]}",
            block,
            "pp3",  # pp with 3 dp percentile columns — §5 deltas are tiny; see render.Unit
            pooled_label="Pooled distribution (you − opponent delta, per 100 moves)",
            noise=values["noise"].get(metric_key),
        )
        parts += ["", "---", ""]

    parts += _render_tactic_table(values)
    parts += [""]
    parts += _render_viability(values["viability"], values["cohort"])
    parts += [""]
    parts += _render_noise_summary(values)
    return "\n".join(parts)


def _fmt_magnitude(value: float, unit: dist.Unit) -> str:
    """Unsigned magnitude (an IQR width) in the metric's display unit."""
    if unit == "pp3":
        return f"{fmt_unsigned(value * 100, 3)}pp"
    return fmt_unsigned(value * 100, 2)


# TC levels shown as their own p25-to-p75 column in the compact tactic table.
_TACTIC_TABLE_TCS: tuple[str, str] = ("rapid", "classical")

_TACTIC_TABLE_HEADERS: tuple[str, ...] = (
    "family",
    "orientation",
    "n",
    "p25",
    "p50",
    "p75",
    *(f"{tc} p25 to p75" for tc in _TACTIC_TABLE_TCS),
    "TC max abs d",
    "ELO max abs d",
    "pct_nonzero",
    "noise-only IQR",
    "zone_viable",
)


def _tc_range(block: MetricBlock, tc: str) -> str:
    """`p25 to p75` of one TC marginal in per-100-games units, or n/a for a thin/absent level."""
    for m in block["tc_marginal"]:
        if m["label"] == tc:
            lo = fmt_value(m["dist"]["p25"], "per100g", "pct")
            hi = fmt_value(m["dist"]["p75"], "per100g", "pct")
            return f"{lo} to {hi}"
    return "n/a"


def _max_abs_d(block: MetricBlock, axis: str) -> str:
    """Max |Cohen's d| of one axis, or n/a when that verdict could not be computed."""
    for v in block["verdicts"]:
        if v["axis"] == axis:
            return f"{v['max_abs_d']:.2f}"
    return "n/a"


def _render_tactic_table(values: Chapter5Values) -> list[str]:
    """Compact tactic section: ONE table, one row per tactic metric (38 rows), per 100 games.

    38 full per-metric sections would bloat the report, so the tactic metrics share a single
    table carrying the pooled quartiles, the per-TC quartile bands, both collapse-verdict d's,
    the viability share, the noise-only IQR and the zone_viable flag. Values are the per-user
    mean of (you − opponent) tactic events per game, shown times 100 ("per100g" unit).
    """
    viability = {v["metric"]: v for v in values["viability"]}
    rows: list[list[str]] = []
    for key, block in values["tactic"].items():
        family, orientation = TACTIC_METRIC_PARTS[key]
        pooled = block["pooled"]
        noise = values["noise"].get(key)
        via = viability.get(key)
        rows.append(
            [
                family,
                orientation,
                fmt_int(pooled["n"]),
                fmt_value(pooled["p25"], "per100g", "pct"),
                fmt_value(pooled["p50"], "per100g", "pct"),
                fmt_value(pooled["p75"], "per100g", "pct"),
                *(_tc_range(block, tc) for tc in _TACTIC_TABLE_TCS),
                _max_abs_d(block, "TC"),
                _max_abs_d(block, "ELO"),
                f"{via['pct_nonzero']:.1f}%" if via else "n/a",
                _fmt_magnitude(noise["pooled_noise_iqr"], "per100g") if noise else "n/a",
                ("yes" if via["zone_viable"] else "no") if via else "n/a",
            ]
        )
    aligns = ("left", "left") + ("right",) * (len(_TACTIC_TABLE_HEADERS) - 2)
    return [
        "### 5.13 Tactic Missed/Allowed Zones (D-06)",
        "",
        "> One row per tactic family and orientation. Value = per-user mean over ≥"
        f"{FLAW_DELTA_MIN_GAMES} analyzed games of the per-game count difference",
        "> (your tactic flaws − opponent's) whose motif is in the family's `FAMILY_TO_MOTIF_INTS`",
        f"> ints and whose confidence is ≥ {MIN_TACTIC_CHIP_CONFIDENCE}; shown per 100 games",
        '> ("per100g" unit). Negative = you commit/allow fewer than equally-rated opponents.',
        "> `n/a` = a thin TC level (<"
        f"{_CELL_CONTRIBUTOR_FLOOR} user-cells) or a verdict that could not be computed.",
        "",
        markdown_table(_TACTIC_TABLE_HEADERS, rows, aligns),
    ]


def _render_noise_summary(values: Chapter5Values) -> list[str]:
    """Noise summary: observed pooled IQR vs the noise-only IQR, for every metric.

    A noise share near (or above) 100% means the observed band is mostly sampling noise at the
    lane's 100 games per user per TC; reported, never applied to the zones (owner call).
    """
    headers = ["metric", "observed IQR", "noise-only IQR", "noise share"]
    aligns = ("left", "right", "right", "right")
    rows: list[list[str]] = []
    blocks = {**values["flaw"], **values["tactic"]}
    for key, block in blocks.items():
        noise = values["noise"].get(key)
        if noise is None:
            continue
        unit: dist.Unit = "pp3" if key in values["flaw"] else "per100g"
        observed = block["pooled"]["p75"] - block["pooled"]["p25"]
        share = f"{noise['pooled_noise_iqr'] / observed * 100:.0f}%" if observed > 0 else "n/a"
        rows.append(
            [
                key,
                _fmt_magnitude(observed, unit),
                _fmt_magnitude(noise["pooled_noise_iqr"], unit),
                share,
            ]
        )
    return [
        "### 5.15 Noise-only IQR Summary",
        "",
        "> Noise-only IQR = `1.349 * sqrt(mean over user-cells of var(per-game delta) / n_games)`:",
        "> the IQR per-user values would show if every user had the same true gap. Flaw metrics",
        "> are per 100 moves (pp), tactic metrics per 100 games. Reported, not applied.",
        "",
        markdown_table(headers, rows, aligns),
    ]


def _metric_section(
    title: str,
    block: MetricBlock,
    unit: dist.Unit,
    *,
    pooled_label: str,
    noise: NoiseRow | None = None,
) -> list[str]:
    """Render one metric sub-section: pooled + ELO/TC marginals + verdict block."""
    lines = [
        title,
        "",
        f"#### {pooled_label}",
        "",
        dist.pooled_table(block["pooled"], unit),
        "",
    ]
    if noise is not None:
        observed = block["pooled"]["p75"] - block["pooled"]["p25"]
        lines += [
            f"Noise-only IQR: {_fmt_magnitude(noise['pooled_noise_iqr'], unit)} "
            f"(observed IQR: {_fmt_magnitude(observed, unit)})",
            "",
        ]
    lines += [
        "#### ELO marginal",
        "",
        dist.marginal_table("ELO", block["elo_marginal"], unit),
        "",
        "#### TC marginal",
        "",
        dist.marginal_table("TC", block["tc_marginal"], unit),
        "",
    ]
    if block["thin_levels"]:
        lines += [
            f"Thin levels (<{_CELL_CONTRIBUTOR_FLOOR} user-cells): {', '.join(block['thin_levels'])}",
            "",
        ]
    lines.append(dist.verdict_block(block["verdicts"]))
    return lines


def _render_viability(viability: list[ViabilityRow], cohort: CohortSummary) -> list[str]:
    """Render the per-metric viability diagnostic table (Phase 114 D-06) + cohort-size summary."""
    headers = [
        "metric",
        "users_contributing",
        "users_total",
        "pct_nonzero",
        "median_events_per_user",
        "degenerate_iqr",
        "zone_viable",
    ]
    aligns = ("left",) + ("right",) * (len(headers) - 1)

    def table_for(metrics: tuple[tuple[str, str], ...]) -> str:
        keys = {key for key, _ in metrics}
        rows = [
            [
                v["metric"],
                str(v["users_contributing"]),
                str(v["users_total"]),
                f"{v['pct_nonzero']:.1f}%",
                f"{v['median_events_per_user']:.1f}",
                "yes" if v["degenerate_iqr"] else "no",
                "yes" if v["zone_viable"] else "no",
            ]
            for v in viability
            if v["metric"] in keys
        ]
        return markdown_table(headers, rows, aligns)

    cohort_line = (
        f"**Cohort basis**: {cohort['n_analyzed_games']:,} analyzed games across "
        f"{cohort['n_user_cells']:,} user×(ELO,TC) cells "
        f"({cohort['n_distinct_users']:,} distinct users). All analyzed games count "
        "(clean games = a 0 delta); the per-cell `users_total` below = these user×cell rows, "
        "not distinct users."
    )
    return [
        "### 5.14 Viability Diagnostic (D-06)",
        "",
        cohort_line,
        "",
        "> Flags rare numerators so the registry author can assess CI-width adequacy.",
        "> Non-zero = user has ≥1 player event of this tag over their ≥20 analyzed games.",
        f"> `zone_viable` = pooled IQR not degenerate (p25 < p75) AND pct_nonzero ≥ {VIABILITY_MIN_PCT_NONZERO:.0f}%.",
        "> `median_events_per_user` is a RAW, unscaled count (player events of this tag",
        "> totalled over the user's analyzed games) — NOT a per-100-moves rate, unlike the",
        "> §5.1–5.12 zone columns. It gauges raw event volume for CI-width adequacy.",
        "> Tactic rows count player events of that family and orientation over the user's games.",
        "",
        "#### Flaw metrics",
        "",
        table_for(FLAW_DELTA_METRICS),
        "",
        "#### Tactic metrics",
        "",
        table_for(TACTIC_METRICS),
    ]


async def build(session: AsyncSession) -> dict[str, Any]:
    """Build the §5 Flaw-Delta Zones chapter artifact."""
    values = await compute(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values": values,
        "markdown": render(values),
    }


# --- §5-only CLI (fast refresh path) ---------------------------------------


def _summary_line(values: Chapter5Values) -> str:
    """One-line run summary: metric counts, TC levels of the blunder block, game count."""
    tc_levels = ", ".join(m["label"] for m in values["flaw"]["blunder"]["tc_marginal"])
    return (
        f"chapter5: {len(values['flaw'])} flaw + {len(values['tactic'])} tactic metrics; "
        f"TC levels: {tc_levels}; games: {values['cohort']['n_analyzed_games']}"
    )


def _write_outputs(out_dir: Path, built: Mapping[str, Any]) -> None:
    """Write chapter5.md (markdown) and chapter5.json (values) into `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chapter5.md").write_text(built["markdown"] + "\n", encoding="utf-8")
    (out_dir / "chapter5.json").write_text(
        json.dumps(built["values"], default=str, indent=2) + "\n", encoding="utf-8"
    )


async def _main(argv: Sequence[str] | None = None) -> None:
    """Run §5 alone in a READ ONLY transaction and write chapter5.md + chapter5.json."""
    parser = argparse.ArgumentParser(description="Run benchmarks §5 alone (fast refresh path).")
    parser.add_argument("--db", choices=("benchmark", "dev"), default="benchmark")
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    args = parser.parse_args(argv)

    engine = create_async_engine(db_url_for_target(args.db), pool_pre_ping=True)
    try:
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            built = await build(session)
    finally:
        await engine.dispose()

    _write_outputs(args.out, built)
    print(_summary_line(built["values"]))


if __name__ == "__main__":
    asyncio.run(_main())
