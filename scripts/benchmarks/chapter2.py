"""Chapter 2 — Openings (SKILL.md §2). Only metric: §2.1 Middlegame-entry eval.

Two passes (SKILL.md §2.1 "Query"):
  Pass 1 — symmetric engine baseline at MG entry, deduped to physical games, NO
           equal-footing filter (production-realistic regime). Yields one white-POV
           number `BASELINE_CP`; the symmetric baseline is +X / −X.
  Pass 2 — per-(user, color) signed eval at MG entry, centered on the symmetric
           baseline, pooled + marginalized over the game-time (ELO, TC) cells (the
           shared distribution machinery).

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

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import entry_eval
from scripts.benchmarks import sql
from scripts.benchmarks.entry_eval import Baseline

SECTION = "SKILL.md §2.1 — middlegame-entry eval (symmetric baseline + centered distribution)"

# Centered eval is a cp metric: mean at 2 dp (report double-rounds to +3.7), sd/pct at 1 dp.
_CP_DIGITS = 1
_CP_MEAN_DIGITS = 2


class Chapter2Values(TypedDict):
    baseline: Baseline
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]


async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()


async def _pass2(session: AsyncSession, centering_cp: float) -> Sequence[RowMapping]:
    """Pass 2 — pooled + ELO + TC marginals in one GROUPING SETS scan over centered values."""
    sql_text = (
        f"{entry_eval.per_user_color_with(sql.MIDDLEGAME_PHASE)},\n"
        "mc AS (\n"
        f"  SELECT {entry_eval.centered_expr(centering_cp)} AS centered_cp, elo_bucket, tc\n"
        f"  FROM {entry_eval.PER_USER_COLOR_CTE} WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")\n"
        "SELECT\n"
        f"{dist.agg_select('centered_cp', digits=_CP_DIGITS, mean_digits=_CP_MEAN_DIGITS)}\n"
        f"FROM mc {dist.GROUPING_SETS}"
    )
    return await _fetch(session, sql_text)


async def compute(session: AsyncSession) -> Chapter2Values:
    baseline = await entry_eval.baseline(session, sql.MIDDLEGAME_PHASE)
    rows = await _pass2(session, baseline["centering_cp"])
    pooled, elo, tc = dist.split_grouping_sets(rows)
    return Chapter2Values(
        baseline=baseline,
        pooled=pooled,
        elo_marginal=elo,
        tc_marginal=tc,
        verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
    )


# --- rendering -------------------------------------------------------------


def render(values: Chapter2Values) -> str:
    parts = [
        "## 2. Openings",
        "",
        "### 2.1 Middlegame-entry eval",
        "",
        "#### Pass 1 — symmetric engine baseline (deduped to physical games)",
        "",
        entry_eval.baseline_table(values["baseline"]),
        "",
        "#### Pass 2 — centered per-(user, color) pooled distribution",
        "",
        "##### Pooled centered distribution",
        "",
        dist.pooled_table(values["pooled"], "cp"),
        "",
        "##### ELO marginal (centered)",
        "",
        dist.marginal_table("ELO", values["elo_marginal"], "cp"),
        "",
        "##### TC marginal (centered)",
        "",
        dist.marginal_table("TC", values["tc_marginal"], "cp"),
        "",
        dist.verdict_block(values["verdicts"]),
    ]
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {"status": "OK", "section": SECTION, "values": values, "markdown": render(values)}
