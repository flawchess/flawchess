"""Report-only check: does the eval source move the out-of-the-opening rates?

Phase 243. The worse/better classification reads the eval at the first middlegame ply,
and that eval comes from one of three sources: lichess analysis, a local full-game
Stockfish pass, or the entry-lane eval. Evals are not reproducible across sources, so
this script measures how far the per-user worse/better rate moves when the SAME user x
colour x TC is classified on one source versus another.

The comparison is PAIRED, never pooled (project memory: a pooled analysed-vs-unanalysed
split sign-flipped for blitz): for each (TC, user, colour) with at least
``MIN_GAMES_PER_SOURCE`` games on BOTH sources of a pair, take the rate difference, then
report the mean and standard error of those differences in percentage points.

It asserts nothing and exits 0: the numbers are recorded in the plan SUMMARY, never
used as a gate.

Usage::

    bin/benchmark_db.sh start
    uv run python scripts/opening_out_eval_source_report.py --target benchmark \\
        --tcs blitz,rapid --snapshot-date 2026-05-30
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Final, Literal, NamedTuple, get_args

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so ``app.*`` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402
from app.services.canonical_slice_sql import (  # noqa: E402
    TimeControlBucket,
    per_user_cte_opening_out_counts,
    selected_users_cte,
)
from scripts.gen_global_percentile_cdf import (  # noqa: E402
    BENCHMARK_DB_NAME_TOKEN,
    BENCHMARK_DB_PORT_TOKEN,
)

EvalSource = Literal["lichess", "local_full", "entry_lane"]

# Minimum qualifying games per (user, colour) on EACH source for a pair to count.
MIN_GAMES_PER_SOURCE: Final[int] = 20

# Source order defines the sign of every delta (first minus second).
EVAL_SOURCES: Final[tuple[EvalSource, ...]] = ("lichess", "local_full", "entry_lane")

# TCs whose benchmark games mix eval sources (bullet is entry-lane, classical sparse).
DEFAULT_TCS: Final[str] = "blitz,rapid"
DEFAULT_SNAPSHOT_DATE: Final[str] = "2026-05-30"

PERCENT: Final[float] = 100.0
MIN_PAIRS_FOR_SE: Final[int] = 2


class SourceRow(NamedTuple):
    """Counts for one (tc, user, colour, eval source) cell."""

    tc: TimeControlBucket
    user_id: int
    user_color: str
    source: EvalSource
    n: int
    worse_n: int
    better_n: int


class PairedDelta(NamedTuple):
    """Paired rate difference (first source minus second source) for one TC."""

    tc: TimeControlBucket
    source_a: EvalSource
    source_b: EvalSource
    n_pairs: int
    worse_mean_pp: float | None
    worse_se_pp: float | None
    better_mean_pp: float | None
    better_se_pp: float | None


def _mean_and_se(values: Sequence[float]) -> tuple[float | None, float | None]:
    """Mean and standard error of ``values`` (SE needs at least two values)."""
    n = len(values)
    if n == 0:
        return None, None
    mean = sum(values) / n
    if n < MIN_PAIRS_FOR_SE:
        return mean, None
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(variance / n)


def paired_source_deltas(rows: Sequence[SourceRow]) -> list[PairedDelta]:
    """Per (tc, source pair): the paired worse/better rate differences in pp.

    A (user, colour) pair counts only when BOTH sources have at least
    ``MIN_GAMES_PER_SOURCE`` qualifying games in that TC. Delta = first source minus
    second source in ``EVAL_SOURCES`` order.
    """
    cells: dict[tuple[TimeControlBucket, int, str], dict[EvalSource, SourceRow]] = defaultdict(dict)
    for r in rows:
        cells[(r.tc, r.user_id, r.user_color)][r.source] = r
    tcs = sorted({r.tc for r in rows})
    out: list[PairedDelta] = []
    for tc in tcs:
        for source_a, source_b in combinations(EVAL_SOURCES, 2):
            worse: list[float] = []
            better: list[float] = []
            for (cell_tc, _uid, _color), by_source in cells.items():
                a, b = by_source.get(source_a), by_source.get(source_b)
                if cell_tc != tc or a is None or b is None:
                    continue
                if a.n < MIN_GAMES_PER_SOURCE or b.n < MIN_GAMES_PER_SOURCE:
                    continue
                worse.append((a.worse_n / a.n - b.worse_n / b.n) * PERCENT)
                better.append((a.better_n / a.n - b.better_n / b.n) * PERCENT)
            worse_mean, worse_se = _mean_and_se(worse)
            better_mean, better_se = _mean_and_se(better)
            out.append(
                PairedDelta(
                    tc, source_a, source_b, len(worse), worse_mean, worse_se, better_mean, better_se
                )
            )
    return out


def source_shares(rows: Sequence[SourceRow]) -> dict[TimeControlBucket, dict[EvalSource, float]]:
    """Share of qualifying games per eval source, per TC (fractions summing to 1)."""
    totals: dict[TimeControlBucket, dict[EvalSource, int]] = defaultdict(
        lambda: dict.fromkeys(EVAL_SOURCES, 0)
    )
    for r in rows:
        totals[r.tc][r.source] += r.n
    shares: dict[TimeControlBucket, dict[EvalSource, float]] = {}
    for tc, by_source in totals.items():
        grand = sum(by_source.values())
        shares[tc] = {s: (n / grand if grand else 0.0) for s, n in by_source.items()}
    return shares


def _build_source_query(tc: TimeControlBucket, snapshot_date: date) -> str:
    """Per-(user, colour, eval source) counts over the SHARED classification CTE."""
    counts = per_user_cte_opening_out_counts(tc, source="benchmark", snapshot_date=snapshot_date)
    return f"""
WITH {selected_users_cte(source="benchmark")},
{counts}
SELECT
  c.user_id,
  c.user_color,
  CASE
    WHEN g.lichess_evals_at IS NOT NULL THEN 'lichess'
    WHEN g.full_evals_completed_at IS NOT NULL THEN 'local_full'
    ELSE 'entry_lane'
  END AS eval_source,
  count(c.side)::int AS n,
  (count(*) FILTER (WHERE c.side = -1))::int AS worse_n,
  (count(*) FILTER (WHERE c.side = 1))::int AS better_n
FROM opening_out_classified c
JOIN games g ON g.id = c.game_id
GROUP BY c.user_id, c.user_color, eval_source
""".strip()


async def _fetch_rows(
    session: AsyncSession, tc: TimeControlBucket, snapshot_date: date
) -> list[SourceRow]:
    result = await session.execute(text(_build_source_query(tc, snapshot_date)))
    return [
        SourceRow(
            tc=tc,
            user_id=int(r.user_id),
            user_color=str(r.user_color),
            source=_as_eval_source(str(r.eval_source)),
            n=int(r.n),
            worse_n=int(r.worse_n),
            better_n=int(r.better_n),
        )
        for r in result.all()
    ]


def _as_eval_source(raw: str) -> EvalSource:
    for source in EVAL_SOURCES:
        if source == raw:
            return source
    raise ValueError(f"Unexpected eval source label: {raw!r}")


def _format_pp(mean: float | None, se: float | None) -> str:
    if mean is None:
        return "n/a"
    return f"{mean:+.2f} ± {se:.2f}" if se is not None else f"{mean:+.2f}"


def render_markdown(rows: Sequence[SourceRow]) -> str:
    """Markdown for the per-TC source shares and the paired-delta table."""
    lines: list[str] = ["## Eval-source shares (qualifying games)", ""]
    lines += ["| TC | " + " | ".join(EVAL_SOURCES) + " |", "|---|" + "---:|" * len(EVAL_SOURCES)]
    for tc, shares in sorted(source_shares(rows).items()):
        lines.append(
            f"| {tc} | " + " | ".join(f"{shares[s] * PERCENT:.1f}%" for s in EVAL_SOURCES) + " |"
        )
    lines += [
        "",
        f"## Paired per-user x colour deltas, first minus second source (pp, mean ± SE; "
        f">= {MIN_GAMES_PER_SOURCE} games per source)",
        "",
        "| TC | source A | source B | pairs | worse delta (pp) | better delta (pp) |",
        "|---|---|---|---:|---:|---:|",
    ]
    for d in paired_source_deltas(rows):
        lines.append(
            f"| {d.tc} | {d.source_a} | {d.source_b} | {d.n_pairs} | "
            f"{_format_pp(d.worse_mean_pp, d.worse_se_pp)} | "
            f"{_format_pp(d.better_mean_pp, d.better_se_pp)} |"
        )
    return "\n".join(lines)


def _parse_tcs(raw: str) -> list[TimeControlBucket]:
    valid = get_args(TimeControlBucket)
    out: list[TimeControlBucket] = []
    for token in (t.strip() for t in raw.split(",")):
        match = next((tc for tc in valid if tc == token), None)
        if match is None:
            raise argparse.ArgumentTypeError(
                f"Invalid --tcs entry {token!r}: must be one of {', '.join(valid)}"
            )
        out.append(match)
    return out


def _parse_snapshot_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid --snapshot-date {raw!r}: must be YYYY-MM-DD ({exc})"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--target", choices=["benchmark"], required=True)
    parser.add_argument("--tcs", type=_parse_tcs, default=_parse_tcs(DEFAULT_TCS))
    parser.add_argument(
        "--snapshot-date",
        type=_parse_snapshot_date,
        default=_parse_snapshot_date(DEFAULT_SNAPSHOT_DATE),
        dest="snapshot_date",
        metavar="YYYY-MM-DD",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    url = db_url_for_target(args.target)
    if BENCHMARK_DB_NAME_TOKEN not in url or BENCHMARK_DB_PORT_TOKEN not in url:
        raise SystemExit(
            f"Refusing to run: resolved DB URL does not contain both "
            f"{BENCHMARK_DB_NAME_TOKEN!r} and {BENCHMARK_DB_PORT_TOKEN!r}."
        )
    all_rows: list[SourceRow] = []
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            for tc in args.tcs:
                all_rows.extend(await _fetch_rows(session, tc, args.snapshot_date))
    finally:
        await engine.dispose()
    print(render_markdown(all_rows))


if __name__ == "__main__":
    asyncio.run(main())
