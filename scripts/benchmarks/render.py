"""Markdown rendering helpers for the benchmark report (GitHub-flavored tables).

Applies the SKILL.md "Display formatting" rules at the rendering layer (never in
SQL — scaling inside the query would corrupt `var_samp` for Cohen's d). Code emits
the numeric tables; the SKILL.md LLM narrates the surrounding prose (interpretation,
recommendations) and applies the fixed collapse-verdict thresholds.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Align = Literal["left", "right"]

# Typographic minus (U+2212) — the report uses it for negative eval/score values
# (verified against benchmarks-latest.md), ASCII "-" only inside code spans.
MINUS: str = "−"

# Thousands grouping kicks in at >= 1,000. The oracle report groups every count
# >= 1,000 (e.g. "11,609", "48,763", "114,933"); this matches the report rather
# than the looser ">= 100,000" wording in SKILL.md "Display formatting", which is
# reconciled in the SKILL.md rewrite step of the port.
_GROUP_FLOOR: int = 1000

_SEP: dict[Align, str] = {"left": "---", "right": "---:"}


def fmt_int(n: int) -> str:
    """Render an integer with thousands separators at or above 1,000."""
    return f"{n:,}" if abs(n) >= _GROUP_FLOOR else str(n)


def _round_half_up(value: float | Decimal | str, decimals: int) -> Decimal:
    """Round half-away-from-zero to `decimals` places.

    The report's eval tables round half-up (e.g. SQL-rounded mean 3.65 displays as
    +3.7), unlike Python's banker's rounding. Accepts the asyncpg Decimal verbatim
    (via str) so the SQL-rounded value isn't re-fuzzed through binary float.
    """
    quantum = Decimal(1).scaleb(-decimals)
    return Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)


def fmt_signed(value: float | Decimal | str, decimals: int = 0) -> str:
    """Signed value with a typographic minus (eval cp display). e.g. +89, −92, +3.7."""
    rounded = _round_half_up(value, decimals)
    if rounded == 0:  # collapse -0 to +0
        rounded = abs(rounded)
    sign = "+" if rounded >= 0 else MINUS
    return f"{sign}{abs(rounded):.{decimals}f}"


def fmt_unsigned(value: float | Decimal | str, decimals: int) -> str:
    """Unsigned fixed-decimal value (e.g. an SD column). 58.5, 237.2."""
    return f"{_round_half_up(value, decimals):.{decimals}f}"


# Per-metric display unit for distribution tables (SKILL.md "Display formatting"):
#   cp    — eval centipawns: mean/percentiles signed, percentiles as integer cp,
#           SD unsigned 1 dp; " cp" suffix on pooled rows only (marginals bare).
#   score — proportion rendered as percent: unsigned, 1 dp, "%" suffix everywhere.
#   pp    — signed proportion rendered as percentage points: 1 dp, "pp" everywhere
#           (SD unsigned).
Unit = Literal["cp", "score", "pp"]
Role = Literal["mean", "sd", "pct"]

_UNIT_SCALE: dict[Unit, int] = {"cp": 1, "score": 100, "pp": 100}


def fmt_value(value: float | Decimal | str, unit: Unit, role: Role, *, pooled: bool = False) -> str:
    """Format one distribution-table cell per its unit + role (SKILL.md "Display formatting").

    `pooled` controls only the cp unit's " cp" suffix (shown on pooled rows, omitted
    on marginal rows, matching benchmarks-latest.md).
    """
    scaled = float(value) * _UNIT_SCALE[unit]
    decimals = 0 if (unit == "cp" and role == "pct") else 1
    signed = unit in ("cp", "pp") and role != "sd"
    body = fmt_signed(scaled, decimals) if signed else fmt_unsigned(scaled, decimals)
    if unit == "score":
        return f"{body}%"
    if unit == "pp":
        return f"{body}pp"
    return f"{body} cp" if pooled else body  # cp


def markdown_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    aligns: Sequence[Align],
) -> str:
    """Render a GitHub-flavored markdown table.

    `aligns` is one entry per column (`"left"` -> `---`, `"right"` -> `---:`),
    matching the separator style in `benchmarks-latest.md`.
    """
    if len(headers) != len(aligns):
        raise ValueError(f"headers ({len(headers)}) and aligns ({len(aligns)}) length mismatch")
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(_SEP[a] for a in aligns) + "|"
    body = ["| " + " | ".join(cells) + " |" for cells in rows]
    return "\n".join([head, sep, *body])
