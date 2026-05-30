"""Shared SQL building blocks + pure bucketing helpers for the benchmark generator.

These mirror the canonical fragments in `.claude/skills/benchmarks/SKILL.md`
("Cell anchoring", "Standard CTE — `selected_users`", "Equal-footing opponent
filter", "Sparse-cell exclusion"). Every chapter imports from here so the cohort
definition, ELO bucketing, and equal-footing filter cannot drift between queries.

FAITHFUL PORT (SEED-029 #1): the SQL strings reproduce the skill's blocks verbatim.
The one deliberate simplification vs SKILL.md is dropping the "current-DB-state
checkpoint exception" (the `lower()` join with no checkpoint filter): the benchmark
DB now has completed checkpoints for all five ELO buckets, so the canonical
checkpoint-join CTE is the only path and reproduces `benchmarks-latest.md` exactly.
"""

from __future__ import annotations

from typing import Literal

TcBucket = Literal["bullet", "blitz", "rapid", "classical"]

# ELO bucket anchors (400-wide). A rating falls in the highest anchor <= rating;
# ratings below the floor are dropped (NULL bucket). SKILL.md "Cell rules".
ELO_ANCHORS: tuple[int, ...] = (800, 1200, 1600, 2000, 2400)
ELO_FLOOR: int = ELO_ANCHORS[0]

# Report display order.
ELO_ORDER: tuple[int, ...] = ELO_ANCHORS
TC_ORDER: tuple[TcBucket, ...] = ("bullet", "blitz", "rapid", "classical")

# Structurally pool-exhausted cell: excluded from marginals / pooled / Cohen's d,
# kept in cell-level grids with a footnote. SKILL.md "Sparse-cell exclusion".
SPARSE_CELL: tuple[int, TcBucket] = (2400, "classical")

# SQL predicate that drops the sparse cell from marginal / pooled / Cohen's d
# aggregation (applied where `elo_bucket` and `tc` columns are in scope).
SPARSE_CELL_EXCLUSION: str = f"NOT (elo_bucket = {SPARSE_CELL[0]} AND tc = '{SPARSE_CELL[1]}')"

# Equal-footing opponent filter tolerance (Elo). SKILL.md "Equal-footing opponent filter".
EQUAL_FOOTING_TOLERANCE: int = 100

# Endgame-entry qualification: a game reaches the endgame when it has at least this
# many plies with a non-NULL endgame_class. SKILL.md "Eval coverage check".
MIN_ENDGAME_PLIES: int = 6

# game_positions.phase codes (app/models/game_position.py): 0=opening / 1=middlegame
# / 2=endgame. SKILL.md "Phase-entry definition".
MIDDLEGAME_PHASE: int = 1
ENDGAME_PHASE: int = 2

# Eval mate handling / outlier trim — match production exactly (SKILL.md "Mate handling
# and outlier trim"). Rows with |eval_cp| >= this are dropped (not clipped); mate rows
# (eval_mate IS NOT NULL) are dropped entirely.
EVAL_OUTLIER_TRIM_CP: int = 2000
# Per-user sample floor for entry-eval metrics (matches EVAL_CONFIDENCE_MIN_N, the live
# z-test gate). SKILL.md "Sample floor" / "Sample floors".
EVAL_CONFIDENCE_MIN_N: int = 20

# Lichess winning-chances sigmoid coefficient (SKILL.md §3.1.3/§3.1.5 expected_score).
LICHESS_WIN_CHANCES_K: float = 0.00368208

# Per-user game floors (SKILL.md "Sample floors").
SCORE_GAP_MIN_GAMES: int = 30  # §3.1.1/§3.1.6: >=30 endgame AND >=30 non-endgame
ENDGAME_MIN_GAMES: int = 20  # §3.1.3/§3.1.4/§3.1.5/§3.2.1: >=20 endgame games per cell

# User's score in a game (SKILL.md "Shared SQL building blocks — user_score_expr").
USER_SCORE_EXPR: str = (
    "CASE\n"
    "  WHEN (g.result = '1-0' AND g.user_color = 'white')\n"
    "    OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0\n"
    "  WHEN g.result = '1/2-1/2' THEN 0.5\n"
    "  ELSE 0.0\n"
    "END"
)

# Games meeting the 6-ply endgame rule (SKILL.md "Shared SQL building blocks —
# endgame_game_ids"). A CTE body for inclusion in a WITH clause.
ENDGAME_GAME_IDS_CTE: str = (
    "endgame_game_ids AS (\n"
    "  SELECT game_id FROM game_positions\n"
    "  WHERE endgame_class IS NOT NULL\n"
    f"  GROUP BY game_id HAVING count(*) >= {MIN_ENDGAME_PLIES}\n"
    ")"
)


def elo_bucket(rating: int | None) -> int | None:
    """Game-time ELO bucket for a rating, or None if below the floor / missing.

    Pure mirror of `elo_bucket_case_sql()` so the Python and SQL paths share one
    anchor list and cannot drift. SKILL.md "Rating-lag selection bias".
    """
    if rating is None or rating < ELO_FLOOR:
        return None
    bucket = ELO_FLOOR
    for anchor in ELO_ANCHORS:
        if rating >= anchor:
            bucket = anchor
        else:
            break
    return bucket


def elo_bucket_case_sql(value_expr: str) -> str:
    """Build the canonical game-time ELO-bucket CASE from ELO_ANCHORS.

    Mirrors `elo_bucket()`; sub-floor ratings -> NULL (dropped downstream by the
    `>= ELO_FLOOR` guard in the query). `value_expr` is the SQL expression for the
    cohort user's rating at game time (see `USER_ELO_AT_GAME_SQL`).
    """
    whens = [f"WHEN {value_expr} < {ELO_FLOOR} THEN NULL"]
    for low, high in zip(ELO_ANCHORS, ELO_ANCHORS[1:]):
        whens.append(f"WHEN {value_expr} < {high} THEN {low}")
    whens.append(f"ELSE {ELO_ANCHORS[-1]}")
    return "CASE " + " ".join(whens) + " END"


# Cohort user's / opponent's rating at game time, from the user-POV color.
# SKILL.md "Rating-lag selection bias" + "Equal-footing opponent filter".
USER_ELO_AT_GAME_SQL: str = (
    "CASE WHEN g.user_color::text = 'white' THEN g.white_rating ELSE g.black_rating END"
)
OPP_ELO_AT_GAME_SQL: str = (
    "CASE WHEN g.user_color::text = 'white' THEN g.black_rating ELSE g.white_rating END"
)

# Equal-footing opponent filter predicate (SKILL.md "Equal-footing opponent filter").
EQUAL_FOOTING_FILTER: str = (
    f"abs(({USER_ELO_AT_GAME_SQL}) - ({OPP_ELO_AT_GAME_SQL})) <= {EQUAL_FOOTING_TOLERANCE}"
)

# Canonical cohort CTE (SKILL.md "Standard CTE — `selected_users`"). Join `su` on
# `g.user_id = su.user_id` and always filter `g.time_control_bucket::text = su.tc_bucket`.
# `selection_rating_bucket` / `median_elo` are LONGITUDINAL ONLY — the analysis ELO
# axis is derived per-game via `elo_bucket_case_sql(USER_ELO_AT_GAME_SQL)`.
SELECTED_USERS_CTE: str = """\
selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,
         bsu.median_elo, bsu.eval_game_count
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
)"""

# Base per-game filter shared by every Chapter 2/3 per-game CTE, including the
# universal equal-footing filter (SKILL.md "Equal-footing opponent filter").
# `su` is the `selected_users` CTE alias; `g` is `games`.
BASE_GAME_FILTER: str = (
    "g.rated AND NOT g.is_computer_game\n"
    "    AND g.time_control_bucket::text = su.tc_bucket\n"
    "    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL\n"
    f"    AND {EQUAL_FOOTING_FILTER}"
)
