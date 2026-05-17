"""Phase 87.5 regression (SC#1 + SC#9): no live 'Conversion ELO' string outside the allowlist.

Asserts the case-insensitive phrase 'Conversion ELO' (and the identifier 'conversion_elo')
does not appear in `app/` or `tests/` except where explicitly allowlisted:

- `CHANGELOG.md` (entire file — historical entries kept verbatim per project convention).
- This test file itself (its own string literals would otherwise self-fail).
- `app/services/insights_llm.py` — the `_PROMPT_VERSION` append-only changelog blob is
  the supersession history for LLM prompt versions (D-08 FRONT-prepend pattern). Prior
  vN entries (v32 Conversion ELO rewire, etc.) stay verbatim by design so the LLM
  prompt-version history reads chronologically. The rest of the file is verified by
  the prompt-snapshot tests (`tests/prompts/test_endgame_insights_prompt.py`) which
  scope to `app/prompts/endgame_insights.md` (the user-facing prompt body).
- `app/services/endgame_service.py` — the supersession comment block for the retired
  Phase 87.4 helpers (PIVOT/ALPHA, `_conversion_elo_from_skill`, etc.) lives here as
  documented in Plan 01 SUMMARY §Decisions Made. Plan 01 phrased the block to mention
  the Phase 87.4 helpers by name; the legacy phrase appears only inside that block.
- `tests/prompts/test_endgame_insights_prompt.py` and `tests/services/test_insights_llm.py`
  — these reference the legacy phrase as the *subject* of their assertions (e.g.
  `assert "conversion_elo" not in prompt`); allowlisting them prevents the regression
  test from self-failing on the very assertions it pairs with.

Scope:
- This backend-side test covers `app/` + `tests/` + `CHANGELOG.md`.
- Frontend-side regression (no "Conversion ELO" / `conversion_elo` in
  `frontend/src/`) is covered by a parallel Vitest assertion landed in Plan 02
  (analogous to the existing `noEndgameSkillString.test.tsx` pattern). The two
  tests together cover the SC#1/SC#9 invariant end-to-end.
- Planning documents under `.planning/` are explicitly out of scope (history lives there).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALLOWLIST_FILES = {
    "CHANGELOG.md",
    "tests/test_no_conversion_elo_string.py",
    # The _PROMPT_VERSION append-only changelog blob is the chronological
    # supersession history for LLM prompt versions (D-08 FRONT-prepend pattern).
    "app/services/insights_llm.py",
    # Plan 01 supersession comment block for retired Phase 87.4 helpers.
    "app/services/endgame_service.py",
    # These test files reference the legacy phrase/identifier as the
    # subject of their assertions ("assert 'conversion_elo' NOT in prompt"
    # or "Pydantic must reject {'conversion_elo': ...}"); allowlisting them
    # prevents the regression test from self-failing on its own paired tests.
    "tests/prompts/test_endgame_insights_prompt.py",
    "tests/services/test_insights_llm.py",
    "tests/schemas/test_endgames_schema.py",
}


def _git_grep(pattern: str) -> set[str]:
    """Return the set of file paths matching `pattern` (case-insensitive, filename-only).

    Scoped to `app/`, `tests/`, and `CHANGELOG.md`. Uses `git grep -il` so
    untracked files are not flagged (CHANGELOG history changes only land in
    tracked files). Frontend coverage lives in the parallel Vitest assertion.
    """
    result = subprocess.run(
        [
            "git",
            "grep",
            "-il",
            pattern,
            "--",
            "app/",
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
