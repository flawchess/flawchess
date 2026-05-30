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
