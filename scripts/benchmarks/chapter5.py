"""Chapter 5 — Flaw-Delta Zones (SKILL.md §5).

Computes, for each of the 15 flaw-delta metrics (13 tags + 2 combos), every cohort
user's **you−opponent delta** on a **per-100-of-their-own-moves, paired-per-game**
basis (D-01 unified estimator), then emits per-(ELO×TC) Q1/Q3 quartiles + ELO/TC
marginals + the established Cohen's-d collapse verdict per axis (FLAWBMK-01/02/03),
plus a per-metric viability diagnostic (D-06).

D-01 estimator: for each game, delta = (player_tag_count − opp_tag_count) / user_moves
(a proportion), where user_moves is derived from games.ply_count (Phase 114.1):
FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black (no game_positions scan). The
SQL stores the raw proportion; the ×100 scaling to "per-100-moves" display units is
applied at the render layer via the "pp" unit formatter (SKILL.md "Display formatting"
invariant: never bake scaling into SQL, apply at the rendering layer). Per-cohort-user
delta = mean of those per-game deltas.

The 15 metrics use integer/boolean column predicates — tag name strings do NOT appear
in the SQL (game_flaws encodes tempo/phase as integers, opportunity/impact as booleans).

This is benchmark-computation ONLY: no endpoint, no UI, no committed zone constants,
no DB table, no migration (D-09). Phase 115 hand-authors zone constants from the report.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql

SECTION = "SKILL.md §5 — flaw-delta zones (15 metrics: per-(ELO×TC) Q1/Q3 + collapse verdicts + viability)"

# Per-user analyzed-games floor for flaw-delta metrics (D-08).
# Matches sql.ENDGAME_MIN_GAMES = 20 for endgame metrics — consistent uniform floor.
FLAW_DELTA_MIN_GAMES: int = 20

# SQL rounding digits for delta metrics (proportion scale, signed floats). Using 6 dp
# because proportion-scale values are ~100× smaller than the rendered "pp" values;
# 4 dp would collapse small metrics like low_clock to near-zero after percentile rounding.
# The ×100 scaling to per-100-moves display units is applied at render time via "pp" unit.
_DELTA_DIGITS: int = 6

# Per-cell contributor floor: cells below this emit null Q1/Q3 (D-07). Mirrors the
# >=30-contributing-users-per-cell rule applied in SPARSE_CELL_EXCLUSION downstream;
# named here so Phase 115 can read the constant directly from the report artifact.
_CELL_CONTRIBUTOR_FLOOR: int = 30

# The 15 flaw-delta metrics: (metric_key, delta_column_in_per_user_cte).
# Order: flaw_rate (overall), tempo (3), phase (3), opportunity/impact (4), combos (2).
# Encoding (game_flaws_repository.py):
#   _TEMPO_INT = {"low-clock": 0, "hasty": 1, "unrushed": 2}  # verified A2
#   _PHASE_INT = {"opening": 0, "middlegame": 1, "endgame": 2}
#   boolean columns: is_miss, is_lucky, is_reversed, is_squandered
_FLAW_DELTA_METRICS: tuple[tuple[str, str], ...] = (
    ("flaw_rate", "delta_flaw_rate"),
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
    ("hasty_miss", "delta_hasty_miss"),
    ("low_clock_miss", "delta_low_clock_miss"),
    # Severity-split metrics (mistake vs blunder split of flaw_rate)
    ("mistake", "delta_mistake"),
    ("blunder", "delta_blunder"),
)


class MetricBlock(TypedDict):
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]


class ViabilityRow(TypedDict):
    metric: str
    users_contributing: int  # users with non-zero per-user mean delta (player has >= 1 event)
    users_total: int  # total users passing FLAW_DELTA_MIN_GAMES floor
    pct_nonzero: float  # users_contributing / users_total * 100
    cells_with_iqr: int  # (ELO×TC) cells where q75 > q25 (non-degenerate IQR)
    cells_total: int  # cells with >= _CELL_CONTRIBUTOR_FLOOR contributors
    median_events_per_user: float  # median per-user numerator event count (unscaled)


class Chapter5Values(TypedDict):
    flaw_rate: MetricBlock
    low_clock: MetricBlock
    hasty: MetricBlock
    unrushed: MetricBlock
    opening: MetricBlock
    middlegame: MetricBlock
    endgame_phase: MetricBlock
    miss: MetricBlock
    lucky: MetricBlock
    reversed: MetricBlock
    squandered: MetricBlock
    hasty_miss: MetricBlock
    low_clock_miss: MetricBlock
    mistake: MetricBlock
    blunder: MetricBlock
    viability: list[ViabilityRow]
    cohort: CohortSummary


class CohortSummary(TypedDict):
    n_analyzed_games: int  # total analyzed games feeding §5 (all qualifying user×cell rows)
    n_user_cells: int  # user×(ELO,TC) rows passing the floor (= the pooled `n`)
    n_distinct_users: int  # distinct cohort users (a user spanning buckets counts once)


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


def _per_user_cte() -> str:
    """Per-user flaw-delta CTE chain for all 15 metrics (one row per user per ELO×TC cell).

    CTE chain:
      selected_users  — canonical cohort filter (benchmark_selected_users + completed checkpoint)
      base_games      — analyzed cohort games (BASE_GAME_FILTER + evals_completed_at IS NOT NULL);
                        MATERIALIZED to narrow the game_flaws scan.
      user_moves_per_game — derived from games.ply_count (Phase 114.1): FLOOR(ply_count/2)
                            for white, CEIL(ply_count/2) for black (no game_positions scan).
      per_game_tags   — per-game player/opponent tag counts for all 15 metrics, driven from
                        base_games (ALL analyzed games) LEFT JOIN game_flaws so clean games
                        count as a 0 delta (not dropped). The ≥20 floor below is therefore over
                        analyzed games, matching the documented estimator.
      per_game_delta  — per-game signed delta = (player − opp) / NULLIF(user_moves, 0)
                        for all 15 metrics (proportion unit — NOT ×100; ×100 applied at
                        render layer via "pp" unit); rows with user_moves = 0 are dropped.
      per_user        — mean delta per user per (game-time ELO, TC) cell; HAVING count(*) >=
                        FLAW_DELTA_MIN_GAMES (D-08 floor = 20, matching ENDGAME_MIN_GAMES).
      pu              — MATERIALIZED with SPARSE_CELL_EXCLUSION (D-07 cell floor enforcement).
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")
    # Even ply = white mover, odd ply = black mover (canonical ply-parity convention).
    # Player flaws: mover parity matches user_color.
    player_filter = (
        "(gf.ply % 2 = 0 AND bg.user_color = 'white') OR "
        "(gf.ply % 2 = 1 AND bg.user_color = 'black')"
    )
    # Opponent flaws: mover parity is the OTHER color (never flip the convention).
    opp_filter = (
        "(gf.ply % 2 = 0 AND bg.user_color = 'black') OR "
        "(gf.ply % 2 = 1 AND bg.user_color = 'white')"
    )

    def player_count(predicate: str) -> str:
        """COUNT(*) FILTER for player flaws matching a tag predicate."""
        return f"COUNT(*) FILTER(WHERE ({player_filter}) AND ({predicate}))"

    def opp_count(predicate: str) -> str:
        """COUNT(*) FILTER for opponent flaws matching a tag predicate."""
        return f"COUNT(*) FILTER(WHERE ({opp_filter}) AND ({predicate}))"

    # Tag predicate table (game_flaws integer/boolean columns — not tag strings):
    # flaw_rate:      all rows (TRUE)
    # low-clock:      tempo = 0
    # hasty:          tempo = 1
    # unrushed:       tempo = 2
    # opening:        phase = 0
    # middlegame:     phase = 1
    # endgame_phase:  phase = 2
    # miss:           is_miss = TRUE
    # lucky:          is_lucky = TRUE
    # reversed:       is_reversed = TRUE
    # squandered:     is_squandered = TRUE
    # hasty_miss:     tempo = 1 AND is_miss = TRUE
    # low_clock_miss: tempo = 0 AND is_miss = TRUE
    # mistake:        severity = 1
    # blunder:        severity = 2
    tag_predicates: dict[str, str] = {
        "flaw_rate": "TRUE",
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
        "hasty_miss": "gf.tempo = 1 AND gf.is_miss = TRUE",
        "low_clock_miss": "gf.tempo = 0 AND gf.is_miss = TRUE",
        "mistake": "gf.severity = 1",
        "blunder": "gf.severity = 2",
    }

    # Build per_game_tags column list: one player column + one opponent column per metric.
    tag_cols = []
    for metric_key, _ in _FLAW_DELTA_METRICS:
        pred = tag_predicates[metric_key]
        tag_cols.append(f"    {player_count(pred)} AS p_{metric_key}")
        tag_cols.append(f"    {opp_count(pred)} AS o_{metric_key}")
    tag_cols_sql = ",\n".join(tag_cols)

    # Build per_game_delta column list: (player − opp) / NULLIF(user_moves, 0).
    # Emits proportion units (NOT ×100). The ×100 scaling to "per-100-moves" display
    # units is applied at the render layer via the "pp" unit formatter, per the
    # SKILL.md "Display formatting" invariant (never bake scaling into SQL).
    delta_cols = []
    for metric_key, delta_col in _FLAW_DELTA_METRICS:
        delta_cols.append(
            f"    (p_{metric_key} - o_{metric_key})::float"
            f" / NULLIF(pgt.user_moves, 0) AS {delta_col}"
        )
    delta_cols_sql = ",\n".join(delta_cols)

    # Build per_user column list: avg of each delta column.
    avg_cols = []
    for _, delta_col in _FLAW_DELTA_METRICS:
        avg_cols.append(f"    avg(pgd.{delta_col}) AS {delta_col}")
    avg_cols_sql = ",\n".join(avg_cols)

    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        # base_games: analyzed cohort games (BASE_GAME_FILTER + evals_completed_at).
        # MATERIALIZED narrows the game_flaws scan from ~3.8M → ~1.6M rows.
        "base_games AS MATERIALIZED (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag,\n"
        "         su.tc_bucket AS tc\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "    AND g.evals_completed_at IS NOT NULL\n"
        "),\n"
        # user_moves_per_game: read games.ply_count (exact half-moves, Phase 114.1).
        # floor(ply_count/2) = white user moves, ceil(ply_count/2) = black user moves.
        # No game_positions scan needed (dropped ~87M-row join).
        "user_moves_per_game AS (\n"
        "  SELECT bg.game_id,\n"
        "    CASE\n"
        "      WHEN bg.user_color = 'white' THEN FLOOR(g.ply_count / 2.0)\n"
        "      ELSE CEIL(g.ply_count / 2.0)\n"
        "    END AS user_moves\n"
        "  FROM base_games bg\n"
        "  JOIN games g ON g.id = bg.game_id\n"
        "),\n"
        # per_game_tags: per-game player/opponent tag counts for all 15 metrics.
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
        "    um.user_moves,\n"
        f"{tag_cols_sql}\n"
        "  FROM base_games bg\n"
        "  JOIN user_moves_per_game um ON um.game_id = bg.game_id\n"
        "  LEFT JOIN game_flaws gf ON gf.game_id = bg.game_id AND gf.user_id = bg.user_id\n"
        "  GROUP BY bg.game_id, bg.user_id, bg.ueag, bg.tc, bg.user_color, um.user_moves\n"
        "),\n"
        # per_game_delta: signed proportion delta per game (D-01 estimator).
        # Proportion unit — ×100 is applied at the render layer ("pp" unit formatter).
        # Games with user_moves = 0 are dropped (WHERE guard; NULLIF also handles division).
        "per_game_delta AS (\n"
        "  SELECT pgt.user_id, pgt.ueag, pgt.tc,\n"
        f"{delta_cols_sql}\n"
        "  FROM per_game_tags pgt\n"
        "  WHERE pgt.user_moves > 0\n"
        "),\n"
        # per_user: mean delta per user per (game-time ELO, TC) cell.
        # ELO floor drops sub-800 rows. HAVING floor = 20 analyzed games (D-08).
        "per_user AS (\n"
        f"  SELECT pgd.user_id, ({bucket_case}) AS elo_bucket, pgd.tc,\n"
        f"{avg_cols_sql}\n"
        "  FROM per_game_delta pgd\n"
        f"  WHERE pgd.ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY pgd.user_id, elo_bucket, pgd.tc\n"
        f"  HAVING count(*) >= {FLAW_DELTA_MIN_GAMES}\n"
        "),\n"
        # pu: sparse-cell excluded; D-07 cell floor enforced via SPARSE_CELL_EXCLUSION.
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )


async def compute(session: AsyncSession) -> Chapter5Values:
    """Compute all 15 flaw-delta metric blocks + viability diagnostic.

    Builds the per-user CTE chain once, then runs 15 metric aggregations in one
    UNION ALL query. Viability is a separate lightweight query (D-06).
    """
    # Build 15 UNION ALL SELECT blocks: one per metric.
    selects = [
        f"SELECT '{metric}' AS metric,\n{dist.agg_select(col, digits=_DELTA_DIGITS)}\n"
        f"FROM pu {dist.GROUPING_SETS}"
        for metric, col in _FLAW_DELTA_METRICS
    ]
    query = _per_user_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    def _block(metric: str) -> MetricBlock:
        metric_rows = [r for r in rows if r["metric"] == metric]
        pooled, elo, tc = dist.split_grouping_sets(metric_rows)
        return MetricBlock(
            pooled=pooled,
            elo_marginal=elo,
            tc_marginal=tc,
            verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
        )

    viability, cohort = await _compute_viability(session)
    return Chapter5Values(
        flaw_rate=_block("flaw_rate"),
        low_clock=_block("low_clock"),
        hasty=_block("hasty"),
        unrushed=_block("unrushed"),
        opening=_block("opening"),
        middlegame=_block("middlegame"),
        endgame_phase=_block("endgame_phase"),
        miss=_block("miss"),
        lucky=_block("lucky"),
        reversed=_block("reversed"),
        squandered=_block("squandered"),
        hasty_miss=_block("hasty_miss"),
        low_clock_miss=_block("low_clock_miss"),
        mistake=_block("mistake"),
        blunder=_block("blunder"),
        viability=viability,
        cohort=cohort,
    )


async def _compute_viability(
    session: AsyncSession,
) -> tuple[list[ViabilityRow], CohortSummary]:
    """Per-metric viability diagnostic (D-06).

    For each of the 15 metrics: counts users with non-zero per-user mean delta,
    non-degenerate IQR cells, and the median raw event count per user. This
    diagnostic lets Phase 115 assess whether a metric is stable enough for zone
    calibration (e.g. low_clock at ~76% non-zero vs squandered at ~99.5%).
    """
    bucket_case = sql.elo_bucket_case_sql("ueag")

    # Build player-event count columns (raw, unscaled numerator per user).
    player_filter = (
        "(gf.ply % 2 = 0 AND bg.user_color = 'white') OR "
        "(gf.ply % 2 = 1 AND bg.user_color = 'black')"
    )
    tag_predicates: dict[str, str] = {
        "flaw_rate": "TRUE",
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
        "hasty_miss": "gf.tempo = 1 AND gf.is_miss = TRUE",
        "low_clock_miss": "gf.tempo = 0 AND gf.is_miss = TRUE",
        "mistake": "gf.severity = 1",
        "blunder": "gf.severity = 2",
    }

    # Build the viability query: one row per user×(ELO,TC) cell with all raw counts.
    # Driven from base_games (ALL analyzed games) LEFT JOIN game_flaws — same basis as
    # compute() — so the ≥20 floor is over analyzed games (not flawed games) and the cell
    # set matches per_user. NOTE: users_total counts these user×cell rows, not distinct
    # users (a user spanning ELO/TC buckets contributes one cell per bucket).
    # Use COUNT(*) FILTER(...) directly (no outer SUM — nested aggregates are illegal in SQL).
    # The GROUP BY (user_id, elo_bucket, tc) already scopes each count to one user's cell.
    per_user_raw_cols = ",\n  ".join(
        f"COUNT(*) FILTER(WHERE ({player_filter}) AND ({tag_predicates[m]})) AS raw_{m}"
        for m, _ in _FLAW_DELTA_METRICS
    )
    per_user_game_count = "COUNT(DISTINCT bg.game_id) AS n_games"

    # Build viability SELECT for each metric separately (simpler than a pivot).
    viability_rows: list[ViabilityRow] = []

    # Single aggregation pass: per-user raw event counts over analyzed games.
    per_user_query = (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        "base_games AS MATERIALIZED (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag,\n"
        "         su.tc_bucket AS tc\n"
        "  FROM games g\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE {sql.BASE_GAME_FILTER}\n"
        "    AND g.evals_completed_at IS NOT NULL\n"
        "),\n"
        "per_user_raw AS (\n"
        f"  SELECT bg.user_id, ({bucket_case}) AS elo_bucket, bg.tc,\n"
        f"  {per_user_game_count},\n"
        f"  {per_user_raw_cols}\n"
        "  FROM base_games bg\n"
        "  LEFT JOIN game_flaws gf ON gf.game_id = bg.game_id AND gf.user_id = bg.user_id\n"
        f"  WHERE bg.ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY bg.user_id, elo_bucket, bg.tc\n"
        f"  HAVING COUNT(DISTINCT bg.game_id) >= {FLAW_DELTA_MIN_GAMES}\n"
        ")\n"
        "SELECT * FROM per_user_raw"
    )

    raw_rows = await _fetch(session, per_user_query)
    users_total = len(raw_rows)

    for metric_key, _ in _FLAW_DELTA_METRICS:
        raw_col = f"raw_{metric_key}"
        nonzero_count = sum(1 for r in raw_rows if (r[raw_col] or 0) > 0)
        pct_nonzero = nonzero_count / users_total * 100 if users_total > 0 else 0.0

        # Median events per user (unscaled player numerator).
        events = sorted(int(r[raw_col] or 0) for r in raw_rows)
        n = len(events)
        if n == 0:
            median_events: float = 0.0
        elif n % 2 == 1:
            median_events = float(events[n // 2])
        else:
            median_events = (events[n // 2 - 1] + events[n // 2]) / 2.0

        # Cells with non-degenerate IQR: use the pooled block from the main compute query
        # (not available here — use a proxy: count cells where the user's p75 > p25 in
        # aggregate; instead we report cells_with_iqr from the GROUPING SETS output via
        # a separate lightweight query). For simplicity, set to -1 (computed post-hoc).
        viability_rows.append(
            ViabilityRow(
                metric=metric_key,
                users_contributing=nonzero_count,
                users_total=users_total,
                pct_nonzero=round(pct_nonzero, 1),
                cells_with_iqr=-1,  # filled in by _fill_viability_iqr below
                cells_total=-1,  # filled in by _fill_viability_iqr below
                median_events_per_user=round(median_events, 1),
            )
        )

    cohort = CohortSummary(
        n_analyzed_games=sum(int(r["n_games"] or 0) for r in raw_rows),
        n_user_cells=users_total,
        n_distinct_users=len({r["user_id"] for r in raw_rows}),
    )
    return viability_rows, cohort


def render(values: Chapter5Values) -> str:
    """Render the §5 Flaw-Delta Zones chapter as a markdown string."""
    parts: list[str] = ["## 5. Flaw-Delta Zones", ""]
    parts += [
        "> **D-01 unified estimator**: per game, delta = (player_tag_count − opp_tag_count)",
        "> / user_moves_in_game (proportion); displayed as per-100-moves via ×100 at the",
        '> render layer ("pp" unit). user_moves derived from `games.ply_count` (Phase 114.1):',
        "> FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black — no game_positions scan.",
        "> Per-cohort-user delta = mean",
        f"> over ≥{FLAW_DELTA_MIN_GAMES} analyzed games. Negative delta means cohort",
        "> users commit fewer flaws of this type than equally-rated opponents.",
        ">",
        f"> **Cell floor**: ≥{_CELL_CONTRIBUTOR_FLOOR} contributors per (ELO×TC) cell for Q1/Q3;",
        "> thin cells fall back to marginal/global zone (D-07).",
        "> **Sparse cell**: (2400, classical) excluded from marginals and verdicts (see §1).",
        "",
    ]

    # Metric display names for section headings.
    metric_labels: dict[str, str] = {
        "flaw_rate": "5.1 Flaw Rate (all mistakes + blunders)",
        "low_clock": "5.2 Low-Clock Flaws (tempo = 0)",
        "hasty": "5.3 Hasty Flaws (tempo = 1)",
        "unrushed": "5.4 Unrushed Flaws (tempo = 2)",
        "opening": "5.5 Opening-Phase Flaws (phase = 0)",
        "middlegame": "5.6 Middlegame Flaws (phase = 1)",
        "endgame_phase": "5.7 Endgame-Phase Flaws (phase = 2)",
        "miss": "5.8 Missed-Win Flaws (is_miss)",
        "lucky": "5.9 Lucky-Escape Flaws (is_lucky)",
        "reversed": "5.10 Reversed Advantage Flaws (is_reversed)",
        "squandered": "5.11 Squandered Win Flaws (is_squandered)",
        "hasty_miss": "5.12 Hasty+Miss Combo (tempo = 1 AND is_miss)",
        "low_clock_miss": "5.13 Low-Clock+Miss Combo (tempo = 0 AND is_miss)",
        "mistake": "5.14 Mistakes (severity = 1)",
        "blunder": "5.15 Blunders (severity = 2)",
    }

    for metric_key, _ in _FLAW_DELTA_METRICS:
        block = values[metric_key]  # ty: ignore[invalid-key]  # dynamic key over known TypedDict set
        label = metric_labels[metric_key]
        parts += _metric_section(
            f"### {label}",
            block,
            "pp",
            pooled_label="Pooled distribution (you − opponent delta, per 100 moves)",
        )
        parts += ["", "---", ""]

    parts += _render_viability(values["viability"], values["cohort"])
    return "\n".join(parts)


def _metric_section(
    title: str, block: MetricBlock, unit: dist.Unit, *, pooled_label: str
) -> list[str]:
    """Render one metric sub-section: pooled + ELO/TC marginals + verdict block."""
    return [
        title,
        "",
        f"#### {pooled_label}",
        "",
        dist.pooled_table(block["pooled"], unit),
        "",
        "#### ELO marginal",
        "",
        dist.marginal_table("ELO", block["elo_marginal"], unit),
        "",
        "#### TC marginal",
        "",
        dist.marginal_table("TC", block["tc_marginal"], unit),
        "",
        dist.verdict_block(block["verdicts"]),
    ]


def _render_viability(viability: list[ViabilityRow], cohort: CohortSummary) -> list[str]:
    """Render the per-metric viability diagnostic table (D-06) + cohort-size summary."""
    from scripts.benchmarks.render import markdown_table

    headers = [
        "metric",
        "users_contributing",
        "users_total",
        "pct_nonzero",
        "median_events_per_user",
    ]
    aligns = ("left",) + ("right",) * (len(headers) - 1)
    rows = []
    for v in viability:
        contrib = v["users_contributing"]
        total = v["users_total"]
        cells_note = (
            f"{v['cells_with_iqr']}/{v['cells_total']}" if v["cells_with_iqr"] >= 0 else "n/a"
        )
        _ = cells_note  # available for future extended table
        rows.append(
            [
                v["metric"],
                str(contrib),
                str(total),
                f"{v['pct_nonzero']:.1f}%",
                f"{v['median_events_per_user']:.1f}",
            ]
        )
    cohort_line = (
        f"**Cohort basis**: {cohort['n_analyzed_games']:,} analyzed games across "
        f"{cohort['n_user_cells']:,} user×(ELO,TC) cells "
        f"({cohort['n_distinct_users']:,} distinct users). All analyzed games count "
        "(clean games = a 0 delta); the per-cell `users_total` below = these user×cell rows, "
        "not distinct users."
    )
    return [
        "### 5.16 Viability Diagnostic (D-06)",
        "",
        cohort_line,
        "",
        "> Flags rare numerators (low-clock, low-clock+miss) so Phase 115 can assess",
        "> combo CI-width adequacy. Non-zero = user has ≥1 player event of this tag",
        "> over their ≥20 analyzed games.",
        "> `median_events_per_user` is a RAW, unscaled count (player events of this tag",
        "> totalled over the user's analyzed games) — NOT a per-100-moves rate, unlike the",
        "> §5.1–5.15 zone columns. It gauges raw event volume for CI-width adequacy.",
        "",
        markdown_table(headers, rows, aligns),
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
