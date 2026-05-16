"""Regression snapshot tests for `app/prompts/endgame_insights.md`.

Phase 87.4 (260516): asserts the LLM prompt no longer mentions the retired
"Endgame Skill" concept, no longer uses the old `endgame_elo_*` identifiers,
and exposes the renamed `Conversion ELO` framing end-to-end.

These are content-grep tests rather than full snapshot files because:
- The prompt is a large markdown blob (~1k lines); a full-file snapshot
  would be noisy on every unrelated copy edit.
- The Phase 87.4 contract is concretely about "this string MUST / MUST NOT
  appear", which grep-style assertions express directly.
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
_PROMPT_TEXT: str = _PROMPT_PATH.read_text(encoding="utf-8")
_PROMPT_TEXT_LOWER: str = _PROMPT_TEXT.lower()


def test_no_endgame_skill_text() -> None:
    """SC#1: the Endgame Skill concept is fully dropped from the prompt."""
    assert "endgame skill" not in _PROMPT_TEXT_LOWER, (
        "'Endgame Skill' phrase still present in app/prompts/endgame_insights.md"
    )
    assert "endgame_skill" not in _PROMPT_TEXT, (
        "'endgame_skill' identifier still present in app/prompts/endgame_insights.md"
    )


def test_no_endgame_elo_timeline_id() -> None:
    """SC#3: the legacy subsection identifier is replaced everywhere."""
    assert "endgame_elo_timeline" not in _PROMPT_TEXT, (
        "Legacy subsection id 'endgame_elo_timeline' still present in prompt"
    )


def test_no_endgame_elo_gap_id() -> None:
    """SC#3: the legacy metric identifier is replaced everywhere."""
    assert "endgame_elo_gap" not in _PROMPT_TEXT, (
        "Legacy metric id 'endgame_elo_gap' still present in prompt"
    )


def test_conversion_elo_timeline_subsection_present() -> None:
    """SC#3: the new subsection heading prose is in place."""
    assert "Conversion ELO Timeline" in _PROMPT_TEXT, (
        "Expected 'Conversion ELO Timeline' subsection heading in prompt"
    )


def test_conversion_elo_timeline_id_present() -> None:
    """SC#3: the new subsection identifier wires up the series block."""
    assert "conversion_elo_timeline" in _PROMPT_TEXT, (
        "Expected new subsection id 'conversion_elo_timeline' in prompt"
    )


def test_conversion_elo_gap_id_present() -> None:
    """SC#3: the new metric identifier feeds the gap bullet."""
    assert "conversion_elo_gap" in _PROMPT_TEXT, (
        "Expected new metric id 'conversion_elo_gap' in prompt"
    )


def test_no_endgame_elo_phrase_in_prose() -> None:
    """SC#3: every user-visible 'Endgame ELO' phrase becomes 'Conversion ELO'.

    No historical Phase 57 attribution line is whitelisted. The Conversion ELO
    rewire keeps the same Phase 57 ``s → ELO`` formula but renames the metric
    end-to-end, so the prompt has no reason to mention the legacy 'Endgame ELO'
    string in prose. If a future edit needs the legacy term for historical
    accuracy, add a whitelist regex here AND document the exception in the
    Phase 87.4 SUMMARY.
    """
    assert "endgame elo" not in _PROMPT_TEXT_LOWER, (
        "'Endgame ELO' phrase still present in prompt prose (case-insensitive)"
    )
