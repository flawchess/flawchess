"""Markdown rendering helpers for the benchmark report (GitHub-flavored tables).

Applies the SKILL.md "Display formatting" rules at the rendering layer (never in
SQL — scaling inside the query would corrupt `var_samp` for Cohen's d). Code emits
the numeric tables; the SKILL.md LLM narrates the surrounding prose (interpretation,
recommendations) and applies the fixed collapse-verdict thresholds.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

Align = Literal["left", "right"]

# Thousands grouping kicks in at >= 1,000. The oracle report groups every count
# >= 1,000 (e.g. "11,609", "48,763", "114,933"); this matches the report rather
# than the looser ">= 100,000" wording in SKILL.md "Display formatting", which is
# reconciled in the SKILL.md rewrite step of the port.
_GROUP_FLOOR: int = 1000

_SEP: dict[Align, str] = {"left": "---", "right": "---:"}


def fmt_int(n: int) -> str:
    """Render an integer with thousands separators at or above 1,000."""
    return f"{n:,}" if abs(n) >= _GROUP_FLOOR else str(n)


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
