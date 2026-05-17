"""Phase 87.5 regression (SC#1 + SC#9): no live 'Conversion ELO' string outside the allowlist.

Asserts the case-insensitive phrase 'Conversion ELO' (and the identifier 'conversion_elo')
does not appear in `app/`, `frontend/src/`, or `tests/` except where explicitly allowlisted:

- `CHANGELOG.md` (entire file — historical entries kept verbatim per project convention).
- This test file itself (its own string literals would otherwise self-fail).

The supersession comment in `app/services/endgame_service.py` (introduced by Plan 01)
is rewritten to avoid the bare phrase, so it does not need a special-case parse here.

The grep is scoped to `app/`, `frontend/src/`, `tests/`, and `CHANGELOG.md`; planning
documents under `.planning/` are explicitly out of scope (history lives there).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALLOWLIST_FILES = {
    "CHANGELOG.md",
    "tests/test_no_conversion_elo_string.py",
}


def _git_grep(pattern: str) -> set[str]:
    """Return the set of file paths matching `pattern` (case-insensitive, filename-only).

    Scoped to `app/`, `frontend/src/`, `tests/`, and `CHANGELOG.md`. Uses
    `git grep -il` so untracked files are not flagged (CHANGELOG history changes
    only land in tracked files).
    """
    result = subprocess.run(
        [
            "git",
            "grep",
            "-il",
            pattern,
            "--",
            "app/",
            "frontend/src/",
            "tests/",
            "CHANGELOG.md",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def test_no_conversion_elo_phrase_in_live_source() -> None:
    """SC#1: case-insensitive 'Conversion ELO' phrase absent from live source."""
    hits = _git_grep("conversion elo")
    offenders = hits - _ALLOWLIST_FILES
    assert not offenders, (
        "Live 'Conversion ELO' references found outside allowlist: "
        f"{sorted(offenders)}. Allowlist: {sorted(_ALLOWLIST_FILES)}."
    )


def test_no_conversion_elo_identifier_in_live_source() -> None:
    """SC#1: literal 'conversion_elo' identifier absent from live source."""
    hits = _git_grep("conversion_elo")
    offenders = hits - _ALLOWLIST_FILES
    assert not offenders, (
        "Live 'conversion_elo' identifier references found outside allowlist: "
        f"{sorted(offenders)}. Allowlist: {sorted(_ALLOWLIST_FILES)}."
    )
