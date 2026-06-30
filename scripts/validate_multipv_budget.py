"""Validate MultiPV=2 node budget: margin histogram + PV1-drift spot-check (MPV-03 / D-07).

Reads stored `game_flaws.allowed_pv_lines` JSONB blobs (populated by Phase 142 eval
drain) and computes the win-prob margin (p(best) - p(second)) at each solver node.
Produces a timestamped markdown report in `reports/multipv-validation/` with:

  - Margin histogram (bin counts across 0..1)
  - Fraction of solver nodes within +/-{_MARGIN_BAND} of ONLY_MOVE_WIN_PROB_MARGIN
  - Advisory PV1-drift spot-check (eval_cp distribution on Phase-142-analyzed positions)

SC4 exit-code gate (--check-goals): exits 1 if fewer than {_MIN_POSITIONS} positions
analyzed OR more than {_MAX_FRACTION_IN_BAND} of solver nodes fall in the margin band
(raise node budget to 1.5-2M per D-06 before merge). The PV1-drift section is advisory
and does not affect the exit code.

Blob schema (D-05, forcing_line_gate.PvNode):
  b  (int|null) -- best_cp, white-perspective
  bm (int|null) -- best_mate, white-perspective
  s  (int|null) -- second_cp, white-perspective (null = no second move or second is mate)
  sm (int|null) -- second_mate, white-perspective
  su (str)      -- second-best UCI, "" = no legal second move

Solver-color derivation (mirrors _detect_tactic_for_flaw convention):
  allowed_pv_lines starts at flaw_ply+1 (opponent's punishing line):
    solver_color = "black" if flaw_ply % 2 == 0 else "white"
  Solver nodes are at even indices (0, 2, 4, ...) in the blob list
  (line starts at a solver node; defender nodes are at odd indices).

Mate handling: mate nodes use eval_mate_to_expected_score (returns 0.0 or 1.0) rather
than being skipped — they always produce large margins and don't cluster near the band.
Nodes with no legal second move (s=None, sm=None) are counted separately as trivially
forced and excluded from the band analysis.

Pitfall 4 guard: reads blobs via EXPLICIT column projection
  select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.allowed_pv_lines)
  Never select the whole ORM entity -- deferred columns raise MissingGreenlet.

T-142-04-02 guard: malformed blob dicts (missing b/s, unexpected types) are skipped
and counted; a single malformed row does not abort the script.

Usage:
    uv run python scripts/validate_multipv_budget.py --db dev
    uv run python scripts/validate_multipv_budget.py --db dev --limit 5000
    uv run python scripts/validate_multipv_budget.py --db dev --check-goals
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# Bootstrap project root so app.* imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import db_url_for_target  # noqa: E402

# Register the FK chain so SQLAlchemy does not raise NoReferencedTableError
# when compiling queries against game_flaws (game_flaws -> games -> users).
from app.models.game import Game  # noqa: E402, F401
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.services.eval_utils import (  # noqa: E402
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.forcing_line_gate import ONLY_MOVE_WIN_PROB_MARGIN  # noqa: E402

# ---------------------------------------------------------------------------
# Constants -- no magic numbers (CLAUDE.md).
# ---------------------------------------------------------------------------

# Report output directory (mirrors tactic_tagger_report.py _REPORT_DIR pattern).
_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "multipv-validation"

# Margin band around ONLY_MOVE_WIN_PROB_MARGIN for the SC4 fraction check.
# Nodes with |margin - ONLY_MOVE_WIN_PROB_MARGIN| <= _MARGIN_BAND are "in-band".
_MARGIN_BAND: float = 0.05

# SC4 gate: if more than this fraction of solver nodes fall within +/-_MARGIN_BAND,
# the node budget is too low -- raise to 1.5-2M before merging (D-06).
_MAX_FRACTION_IN_BAND: float = 0.10

# Minimum flaw positions required for --check-goals to report a meaningful result.
_MIN_POSITIONS: int = 200

# Histogram bin width for the margin distribution display.
_HIST_BIN_WIDTH: float = 0.05

# Number of game_positions rows to sample for the PV1-drift spot-check.
_DRIFT_SAMPLE_LIMIT: int = 100

# Proxy for the ±15pp severity classification boundary in centipawns.
# Derived: eval_cp_to_expected_score(cp, "white") == 0.65 solves to ~168cp;
# 150cp is a conservative round number. Positions within this range are
# "contested" and most sensitive to PV1 drift between multipv=1 and multipv=2.
_SEVERITY_BOUNDARY_CP: int = 150

# Report filename slug.
_REPORT_SLUG = "validate-multipv-budget"


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FlawRow:
    """Minimal flaw data needed for margin computation."""

    game_id: int
    ply: int
    allowed_pv_lines: list[Any]


@dataclass
class _MarginStats:
    """Aggregated margin histogram statistics."""

    margins: list[float] = field(default_factory=list)
    n_trivially_forced: int = 0  # nodes with no second move (always forced)
    n_malformed: int = 0  # nodes with missing/invalid fields
    n_positions: int = 0  # distinct flaw rows examined


@dataclass(frozen=True)
class _DriftStats:
    """Aggregated PV1-drift spot-check statistics."""

    eval_cp_values: list[int]
    n_total: int


# ---------------------------------------------------------------------------
# Solver-color derivation
# ---------------------------------------------------------------------------


def _solver_color_for_allowed(flaw_ply: int) -> Literal["white", "black"]:
    """Return the solver color for an allowed_pv_lines blob.

    allowed_pv_lines starts at flaw_ply+1 (the opponent's punishing line).
    At flaw_ply, white is to move when flaw_ply is even (ply 0 = initial position,
    white to move). The opponent who punishes is therefore black when flaw_ply is
    even, white when flaw_ply is odd.

    Mirrors the convention in _detect_tactic_for_flaw where allowed_* pov =
    board_after_flaw.turn.
    """
    return "black" if flaw_ply % 2 == 0 else "white"


# ---------------------------------------------------------------------------
# Per-node margin computation
# ---------------------------------------------------------------------------


def _node_margin(
    node: dict[str, Any],
    solver_color: Literal["white", "black"],
) -> float | None:
    """Compute the win-prob margin for one PvNode dict.

    Returns None when the node should be excluded from the band analysis:
      - No legal second move (trivially forced; counted in n_trivially_forced)
      - Malformed dict (missing or invalid fields; counted in n_malformed)

    Mate handling (D-01 mirror): uses eval_mate_to_expected_score for mate-scored
    best/second rather than skipping -- mate nodes produce margins near 1.0 and
    never cluster near the ONLY_MOVE_WIN_PROB_MARGIN band.
    """
    b = node.get("b")
    bm = node.get("bm")
    s = node.get("s")
    sm = node.get("sm")

    # No legal second move: trivially forced (su == "" sentinel), not near boundary.
    if s is None and sm is None:
        return None

    # Compute p_best.
    if bm is not None:
        p_best = eval_mate_to_expected_score(bm, solver_color)
    elif b is not None:
        p_best = eval_cp_to_expected_score(b, solver_color)
    else:
        return None  # Malformed: no best eval at all.

    # Compute p_second.
    if sm is not None:
        p_second = eval_mate_to_expected_score(sm, solver_color)
    elif s is not None:
        p_second = eval_cp_to_expected_score(s, solver_color)
    else:
        # Should not reach here (s/sm None checked above), but guard defensively.
        return None

    return p_best - p_second


# ---------------------------------------------------------------------------
# Margin collection across all flaw blobs
# ---------------------------------------------------------------------------


def _collect_margins(flaw_rows: list[_FlawRow]) -> _MarginStats:
    """Collect win-prob margins from all solver nodes across all flaw blobs.

    Solver nodes are at even indices (0, 2, 4, ...) in the blob list.
    Defender nodes (odd indices) are skipped -- the gate applies uniqueness
    only to the solver's choices.
    """
    stats = _MarginStats(n_positions=len(flaw_rows))

    for row in flaw_rows:
        solver_color = _solver_color_for_allowed(row.ply)
        for idx, raw_node in enumerate(row.allowed_pv_lines):
            if idx % 2 != 0:
                continue  # Defender node: skip.
            if not isinstance(raw_node, dict):
                stats.n_malformed += 1
                continue
            margin = _node_margin(raw_node, solver_color)
            if margin is None:
                # Check whether it's trivially forced or malformed.
                s_val = raw_node.get("s")
                sm_val = raw_node.get("sm")
                if s_val is None and sm_val is None:
                    stats.n_trivially_forced += 1
                else:
                    stats.n_malformed += 1
            else:
                stats.margins.append(margin)

    return stats


# ---------------------------------------------------------------------------
# Histogram and fraction computation
# ---------------------------------------------------------------------------


def _count_in_band(margins: list[float]) -> tuple[int, float]:
    """Return (n_in_band, fraction_in_band) for the SC4 gate."""
    band_lo = ONLY_MOVE_WIN_PROB_MARGIN - _MARGIN_BAND
    band_hi = ONLY_MOVE_WIN_PROB_MARGIN + _MARGIN_BAND
    n_in_band = sum(1 for m in margins if band_lo <= m <= band_hi)
    fraction = n_in_band / len(margins) if margins else 0.0
    return n_in_band, fraction


def _build_histogram_table(margins: list[float]) -> str:
    """Build a markdown table showing margin distribution binned at _HIST_BIN_WIDTH."""
    if not margins:
        return "_No margins to histogram (0 solver nodes with a second move)._"

    n_bins = int(round(1.0 / _HIST_BIN_WIDTH))
    counts = [0] * n_bins
    n_negative = 0
    n_overflow = 0

    for m in margins:
        if m < 0.0:
            n_negative += 1
        elif m >= 1.0:
            n_overflow += 1
        else:
            bin_idx = min(int(m / _HIST_BIN_WIDTH), n_bins - 1)
            counts[bin_idx] += 1

    total = len(margins)
    band_lo = ONLY_MOVE_WIN_PROB_MARGIN - _MARGIN_BAND
    band_hi = ONLY_MOVE_WIN_PROB_MARGIN + _MARGIN_BAND

    lines: list[str] = [
        "| Bin | Margin range | Count | Fraction | Band? |",
        "|----:|:-------------|------:|---------:|:------|",
    ]

    for i in range(n_bins):
        lo = i * _HIST_BIN_WIDTH
        hi = lo + _HIST_BIN_WIDTH
        count = counts[i]
        frac = count / total
        # Mark bins that overlap with the [band_lo, band_hi] interval.
        in_band = lo < band_hi and hi > band_lo
        marker = " `** IN BAND **`" if in_band else ""
        lines.append(f"| {i:2d} | [{lo:.2f}, {hi:.2f}) | {count:6d} | {frac:.4f} |{marker} |")

    if n_negative:
        lines.append(
            f"| —  | [< 0.00)      | {n_negative:6d} |"
            f" {n_negative / total:.4f} | (negative margin) |"
        )
    if n_overflow:
        lines.append(f"| —  | [≥ 1.00)      | {n_overflow:6d} | {n_overflow / total:.4f} | |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_drift_section(drift: _DriftStats) -> str:
    """Build the advisory PV1-drift spot-check section of the report."""
    lines: list[str] = []
    lines.append("## PV1 Drift Spot-Check (Advisory)")
    lines.append("")
    lines.append(
        "> **Note:** This section is advisory only. It does not affect the `--check-goals` exit "
        "code. The authoritative PV1-drift guard is the test-suite flaw-count invariant verified "
        "in Plan 142-02 Task 3 (`uv run pytest tests/services/test_full_eval_drain.py -x`). "
        "That test confirms tactic tag counts are unchanged after switching to multipv=2, "
        "which is the practical safety net for PV1-eval boundary drift."
    )
    lines.append("")
    lines.append(
        "The concern (RESEARCH FLAG): switching the whole-game pass to multipv=2 uses less "
        "aggressive Stockfish pruning, which can cause PV1 eval_cp to drift slightly vs "
        "multipv=1 at the same node budget (~5-15 cp typical). A *systematic* shift that "
        "moves flaw classification boundaries (severity: 0 cp = equalized, blunder/mistake "
        "separation near ±150 cp proxy) would be the concern. Small per-position drift "
        "(<15-20 cp) falls within the accepted non-determinism window "
        "(memory: project_eval_nondeterminism)."
    )
    lines.append("")

    if drift.n_total == 0:
        lines.append(
            "_No game_positions rows found for Phase-142-analyzed games. "
            "Run the eval drain to populate blobs, then re-run this script._"
        )
        return "\n".join(lines)

    ev = drift.eval_cp_values
    if not ev:
        lines.append(
            f"_Queried {drift.n_total} game_positions rows but none had non-NULL eval_cp._"
        )
        return "\n".join(lines)

    mean_abs = statistics.mean(abs(x) for x in ev)
    stdev_val = statistics.stdev(ev) if len(ev) >= 2 else float("nan")
    n_contested = sum(1 for x in ev if abs(x) <= _SEVERITY_BOUNDARY_CP)
    n_decisive = sum(1 for x in ev if abs(x) > 300)  # ALREADY_WINNING_CP_THRESHOLD proxy
    frac_contested = n_contested / len(ev)
    frac_decisive = n_decisive / len(ev)

    lines.append(f"**Sample size:** {len(ev)} game_positions rows with non-NULL eval_cp")
    lines.append(
        f"(sampled from up to {_DRIFT_SAMPLE_LIMIT} positions in Phase-142-analyzed games)"
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Mean absolute eval_cp | {mean_abs:.1f} cp |")
    lines.append(f"| Stdev eval_cp | {stdev_val:.1f} cp |")
    lines.append(
        f"| Fraction within ±{_SEVERITY_BOUNDARY_CP} cp (contested zone) |"
        f" {frac_contested:.3f} ({n_contested}/{len(ev)}) |"
    )
    lines.append(
        f"| Fraction > ±300 cp (already-winning zone) |"
        f" {frac_decisive:.3f} ({n_decisive}/{len(ev)}) |"
    )
    lines.append("")
    lines.append(
        "**Interpretation:** Compare these values across Phase 142 boundary. A systematic "
        "multipv=2 PV1 shift of >15-20 cp would increase the contested-zone fraction "
        "significantly (more positions would be pushed into or out of the ±150 cp band). "
        "The values above represent the post-Phase-142 distribution; if a pre-Phase-142 "
        "snapshot is available, subtract means to estimate drift magnitude."
    )

    return "\n".join(lines)


def _build_report(
    flaw_rows: list[_FlawRow],
    stats: _MarginStats,
    drift: _DriftStats,
    db: str,
    limit: int,
    generated: datetime,
) -> str:
    """Assemble the full markdown report."""
    n_in_band, fraction_in_band = _count_in_band(stats.margins)
    gate_passes = stats.n_positions >= _MIN_POSITIONS and (
        fraction_in_band <= _MAX_FRACTION_IN_BAND if stats.margins else False
    )
    gate_verdict = "PASS" if gate_passes else "FAIL"
    gate_color = "" if gate_passes else " (action required)"

    lines: list[str] = []
    lines.append("# FlawChess MultiPV Budget Validation Report")
    lines.append("")
    lines.append(f"**Generated:** {generated.strftime('%Y-%m-%d %H:%M:%SZ')} (UTC)")
    lines.append(f"**DB target:** `{db}`")
    lines.append(f"**Query limit:** {limit}")
    lines.append("**Script:** `scripts/validate_multipv_budget.py`")
    lines.append(f"**Constant:** `ONLY_MOVE_WIN_PROB_MARGIN = {ONLY_MOVE_WIN_PROB_MARGIN}`")
    lines.append(f"**Margin band:** +/-{_MARGIN_BAND} around {ONLY_MOVE_WIN_PROB_MARGIN}")
    lines.append(
        f"**SC4 gate:** fraction-in-band <= {_MAX_FRACTION_IN_BAND} "
        f"AND positions >= {_MIN_POSITIONS}"
    )
    lines.append("")
    lines.append(
        "Reads `game_flaws.allowed_pv_lines` JSONB blobs (Phase 142 eval drain) and "
        "computes the win-prob margin (p(best) - p(second)) at each solver node "
        "(even index in the blob). The fraction of solver nodes within "
        f"+/-{_MARGIN_BAND} of `ONLY_MOVE_WIN_PROB_MARGIN` ({ONLY_MOVE_WIN_PROB_MARGIN}) "
        f"must be <= {_MAX_FRACTION_IN_BAND} for the node budget to be considered reliable "
        "(SC4). If more than 10% fall in the band, raise the node budget to 1.5-2M nodes "
        "(D-06) before merging Phase 142."
    )
    lines.append("")

    # --- Summary table ---
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Flaw positions examined | {stats.n_positions} |")
    lines.append(f"| Solver nodes with second move | {len(stats.margins)} |")
    lines.append(f"| Solver nodes trivially forced (no second move) | {stats.n_trivially_forced} |")
    lines.append(f"| Malformed nodes skipped (T-142-04-02) | {stats.n_malformed} |")
    lines.append(f"| Nodes in-band (+/-{_MARGIN_BAND} of margin) | {n_in_band} |")
    lines.append(
        f"| **Fraction in-band** | **{fraction_in_band:.4f}** "
        f"(gate threshold: <= {_MAX_FRACTION_IN_BAND}) |"
    )
    lines.append(
        f"| **SC4 gate verdict** | **{gate_verdict}{gate_color}** "
        f"(positions >= {_MIN_POSITIONS}: "
        f"{'YES' if stats.n_positions >= _MIN_POSITIONS else 'NO'}) |"
    )
    lines.append("")
    if not gate_passes:
        if stats.n_positions < _MIN_POSITIONS:
            lines.append(
                f"> **FAIL — insufficient data:** Only {stats.n_positions} positions analyzed "
                f"(need >= {_MIN_POSITIONS}). Run the eval drain on more games, then re-run "
                "this script."
            )
        else:
            lines.append(
                f"> **FAIL — budget too low:** {fraction_in_band:.1%} of solver nodes fall "
                f"within +/-{_MARGIN_BAND} of the margin (threshold: {_MAX_FRACTION_IN_BAND:.0%}). "
                "Raise the node budget from 1M to 1.5-2M nodes (D-06) and re-run this "
                "script before merging Phase 142."
            )
        lines.append("")

    # --- Histogram ---
    lines.append("## Margin Distribution Histogram")
    lines.append("")
    lines.append(
        f"Win-prob margin = p(best) - p(second) at each solver node. "
        f"Bins of width {_HIST_BIN_WIDTH}. "
        f"Bins overlapping the gate band "
        f"[{ONLY_MOVE_WIN_PROB_MARGIN - _MARGIN_BAND:.2f}, "
        f"{ONLY_MOVE_WIN_PROB_MARGIN + _MARGIN_BAND:.2f}] are marked `** IN BAND **`."
    )
    lines.append("")
    lines.append(_build_histogram_table(stats.margins))
    lines.append("")

    if stats.margins:
        mean_m = statistics.mean(stats.margins)
        stdev_m = statistics.stdev(stats.margins) if len(stats.margins) >= 2 else float("nan")
        med_m = statistics.median(stats.margins)
        lines.append(
            f"**Mean margin:** {mean_m:.4f} | **Median:** {med_m:.4f} | **Stdev:** {stdev_m:.4f}"
        )
        lines.append("")

    # --- Drift section ---
    lines.append(_build_drift_section(drift))
    lines.append("")

    # --- Methodology notes ---
    lines.append("## Methodology Notes")
    lines.append("")
    lines.append(
        "- **Explicit column projection:** `select(GameFlaw.game_id, GameFlaw.ply, "
        "GameFlaw.allowed_pv_lines)` — never select the whole ORM entity (Pitfall 4: "
        "deferred columns raise `MissingGreenlet`)."
    )
    lines.append(
        "- **Solver color:** `allowed_pv_lines` blob starts at `flaw_ply+1`. "
        "The solver is the opponent of the flaw-maker: black if `flaw_ply % 2 == 0` "
        "(white made the flaw), white if odd. Even indices in the blob are solver nodes."
    )
    lines.append(
        f"- **Margin constant:** `ONLY_MOVE_WIN_PROB_MARGIN = {ONLY_MOVE_WIN_PROB_MARGIN}` "
        "from `app/services/forcing_line_gate.py` (D-07 provisional; final value committed "
        "in Phase 144)."
    )
    lines.append(
        "- **Sigmoid:** `eval_cp_to_expected_score(cp, solver_color)` from "
        "`app/services/eval_utils.py` with `LICHESS_K = 0.00368208`. No hand-rolled sigmoid."
    )
    lines.append(
        "- **Mate nodes:** `eval_mate_to_expected_score` returns 0.0 or 1.0; mate nodes "
        "produce margins near 1.0 and never cluster near the gate band."
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# DB queries (async, session closed before any computation)
# ---------------------------------------------------------------------------


async def _load_data(
    db: str,
    limit: int,
) -> tuple[list[_FlawRow], _DriftStats]:
    """Load flaw blobs and drift sample from DB.

    Returns (flaw_rows, drift_stats). The session is fully closed before
    returning so no AsyncSession is held during the compute phase.
    """
    url = db_url_for_target(db)
    engine = create_async_engine(url, pool_pre_ping=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    flaw_rows: list[_FlawRow] = []
    eval_cp_sample: list[int] = []
    n_positions_queried: int = 0

    async with session_maker() as session:
        # Pitfall 4: explicit column projection (deferred cols; never select whole entity).
        result = await session.execute(
            select(
                GameFlaw.game_id,
                GameFlaw.ply,
                GameFlaw.allowed_pv_lines,
            )
            .where(GameFlaw.allowed_pv_lines.isnot(None))
            .limit(limit)
        )
        for row in result.all():
            if isinstance(row.allowed_pv_lines, list):
                flaw_rows.append(
                    _FlawRow(
                        game_id=row.game_id,
                        ply=row.ply,
                        allowed_pv_lines=row.allowed_pv_lines,
                    )
                )

        # PV1-drift spot-check: sample game_positions.eval_cp for Phase-142-analyzed games.
        if flaw_rows:
            sample_game_ids = list({r.game_id for r in flaw_rows})[:_DRIFT_SAMPLE_LIMIT]
            n_positions_queried = len(sample_game_ids)
            drift_result = await session.execute(
                select(GamePosition.eval_cp)
                .where(
                    GamePosition.game_id.in_(sample_game_ids),
                    GamePosition.eval_cp.isnot(None),
                )
                .limit(_DRIFT_SAMPLE_LIMIT)
            )
            eval_cp_sample = [
                row.eval_cp for row in drift_result.all() if isinstance(row.eval_cp, int)
            ]

    await engine.dispose()
    return flaw_rows, _DriftStats(
        eval_cp_values=eval_cp_sample,
        n_total=n_positions_queried,
    )


# ---------------------------------------------------------------------------
# --check-goals output
# ---------------------------------------------------------------------------


def _print_goal_check(
    n_positions: int,
    fraction_in_band: float,
    n_in_band: int,
    total_nodes: int,
) -> bool:
    """Print SC4 goal-check summary. Returns True if all goals met."""
    print()
    print("=" * 72)
    print("MULTIPV BUDGET GOAL CHECK — SC4 (MPV-03 / D-07)")
    print("=" * 72)

    ok_positions = n_positions >= _MIN_POSITIONS
    ok_fraction = (fraction_in_band <= _MAX_FRACTION_IN_BAND) if total_nodes > 0 else False
    all_pass = ok_positions and ok_fraction

    print(
        f"Positions analyzed:   {n_positions}"
        f"  (need >= {_MIN_POSITIONS})  {'PASS' if ok_positions else 'FAIL'}"
    )
    if total_nodes > 0:
        print(
            f"In-band fraction:     {fraction_in_band:.4f}"
            f"  (need <= {_MAX_FRACTION_IN_BAND})  {'PASS' if ok_fraction else 'FAIL'}"
        )
        print(
            f"  ({n_in_band} of {total_nodes} solver nodes within "
            f"+/-{_MARGIN_BAND} of {ONLY_MOVE_WIN_PROB_MARGIN})"
        )
    else:
        print("In-band fraction:     N/A (0 solver nodes with a second move)  FAIL")

    print()
    if all_pass:
        print("ALL GOALS MET -- node budget is adequate. Phase 142 may merge.")
    else:
        if not ok_positions:
            print(
                f"FAIL: Insufficient data ({n_positions} < {_MIN_POSITIONS} positions). "
                "Run the eval drain on more games and re-run."
            )
        if not ok_fraction:
            print(
                f"FAIL: {fraction_in_band:.1%} of solver nodes in band "
                f"(threshold: {_MAX_FRACTION_IN_BAND:.0%}). "
                "Raise node budget from 1M to 1.5-2M (D-06) and re-run."
            )
    print("=" * 72)
    return all_pass


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate MultiPV=2 node budget via margin histogram on stored game_flaws blobs. "
            "Writes a timestamped report to reports/multipv-validation/. "
            "SC4 gate (MPV-03): exits 0 when fraction of solver nodes within "
            f"+/-{_MARGIN_BAND} of ONLY_MOVE_WIN_PROB_MARGIN ({ONLY_MOVE_WIN_PROB_MARGIN}) "
            f"is <= {_MAX_FRACTION_IN_BAND} and >= {_MIN_POSITIONS} positions are analyzed."
        )
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (SSH tunnel).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of game_flaws rows to query (default: 1000).",
    )
    parser.add_argument(
        "--check-goals",
        action="store_true",
        help=(
            "Evaluate SC4 gate and exit non-zero if goals are unmet. "
            "Still writes the markdown report. "
            "Exit 0 = pass (budget adequate, Phase 142 may merge). "
            "Exit 1 = fail (raise node budget to 1.5-2M or add more dev eval data)."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()
    flaw_rows, drift = asyncio.run(_load_data(args.db, args.limit))

    # All computation happens after the session is closed.
    stats = _collect_margins(flaw_rows)
    n_in_band, fraction_in_band = _count_in_band(stats.margins)

    generated = datetime.now(timezone.utc)
    report = _build_report(flaw_rows, stats, drift, args.db, args.limit, generated)

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _REPORT_DIR / f"{_REPORT_SLUG}-{generated.strftime('%Y-%m-%d')}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path} ({len(report.splitlines())} lines)")
    print(
        f"Positions: {stats.n_positions} | "
        f"Solver nodes: {len(stats.margins)} | "
        f"In-band: {n_in_band} ({fraction_in_band:.4f})"
    )

    if args.check_goals:
        all_pass = _print_goal_check(
            stats.n_positions, fraction_in_band, n_in_band, len(stats.margins)
        )
        sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
