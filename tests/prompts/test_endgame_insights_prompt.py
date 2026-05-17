"""Regression snapshot tests for `app/prompts/endgame_insights.md`.

Phase 87.5 (260517): the LLM prompt is rewritten end-to-end for the Endgame
ELO rebuild on Endgame Score Gap. The Phase 87.4 Conversion ELO framing is
inverted: every `conversion_elo*` identifier and the "Conversion ELO" label
flip back to `endgame_elo*` / "Endgame ELO", AND the glossary prose restores
the "lifts up / holds back" metaphor.

These assertions enforce:
- SC#1: no "Conversion ELO" string in the live prompt (regression-test gated
  separately at the repo level via `tests/test_no_conversion_elo_string.py`).
- SC#7: identifier renames, subsection-mapping move from `metrics_elo` →
  `overall`, and the prose metaphor restoration.

These are content-grep tests rather than full snapshot files because:
- The prompt is a large markdown blob (~1k lines); a full-file snapshot
  would be noisy on every unrelated copy edit.
- The Phase 87.5 contract is concretely about "this string MUST / MUST NOT
  appear", which grep-style assertions express directly.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
_PROMPT_TEXT: str = _PROMPT_PATH.read_text(encoding="utf-8")
_PROMPT_TEXT_LOWER: str = _PROMPT_TEXT.lower()


def test_no_conversion_elo_text() -> None:
    """SC#1: case-insensitive 'Conversion ELO' and literal 'conversion_elo' both gone."""
    assert "conversion elo" not in _PROMPT_TEXT_LOWER, (
        "'Conversion ELO' phrase still present in app/prompts/endgame_insights.md"
    )
    assert "conversion_elo" not in _PROMPT_TEXT, (
        "'conversion_elo' identifier still present in app/prompts/endgame_insights.md"
    )


def test_no_conversion_elo_timeline_id() -> None:
    """SC#7: legacy subsection identifier replaced."""
    assert "conversion_elo_timeline" not in _PROMPT_TEXT, (
        "Legacy subsection id 'conversion_elo_timeline' still present in prompt"
    )


def test_no_conversion_elo_gap_id() -> None:
    """SC#7: legacy metric identifier replaced."""
    assert "conversion_elo_gap" not in _PROMPT_TEXT, (
        "Legacy metric id 'conversion_elo_gap' still present in prompt"
    )


def test_endgame_elo_timeline_subsection_present() -> None:
    """SC#7: the restored subsection heading prose is in place."""
    assert "Endgame ELO Timeline" in _PROMPT_TEXT, (
        "Expected 'Endgame ELO Timeline' subsection heading in prompt"
    )


def test_endgame_elo_timeline_id_present() -> None:
    """SC#7: the restored subsection identifier wires up the series block."""
    assert "endgame_elo_timeline" in _PROMPT_TEXT, (
        "Expected restored subsection id 'endgame_elo_timeline' in prompt"
    )


def test_endgame_elo_gap_id_present() -> None:
    """SC#7: the restored metric identifier feeds the gap bullet."""
    assert "endgame_elo_gap" in _PROMPT_TEXT, (
        "Expected restored metric id 'endgame_elo_gap' in prompt"
    )


def test_lifts_up_metaphor_present() -> None:
    """SC#7: the 'lifts / lifting' headline metaphor is restored (Phase 87.4 traded it away)."""
    assert re.search(r"\blift", _PROMPT_TEXT, re.IGNORECASE) is not None, (
        "Expected at least one 'lift' / 'lifting' / 'lifts' token in prompt prose"
    )


def test_holds_back_metaphor_present() -> None:
    """SC#7: the 'holds back / holding back' headline metaphor is restored."""
    pattern = re.compile(r"\bholds?\s+back\b|\bholding\s+back\b", re.IGNORECASE)
    assert pattern.search(_PROMPT_TEXT) is not None, (
        "Expected at least one 'hold back' / 'holds back' / 'holding back' "
        "token in prompt prose"
    )


def test_no_delta_es_token() -> None:
    """Phase 87.4 D-10 forbidden-token rule inherited: no ΔES variants in user-facing narration."""
    forbidden = re.compile(r"ΔES|delta_es|conv_ΔES|Conv ΔES")
    matches = forbidden.findall(_PROMPT_TEXT)
    assert not matches, (
        f"Forbidden ΔES tokens present in prompt: {matches}. Phase 87.5 uses "
        "'Endgame Score Gap' as the user-facing series name."
    )


def test_section_mapping_assigns_endgame_elo_timeline_to_overall() -> None:
    """SC#7: section mapping table assigns endgame_elo_timeline to `overall`, not `metrics_elo`."""
    # Normalise to single spaces so a typo with extra spacing doesn't break the test.
    body_normalised = re.sub(r"[ \t]+", " ", _PROMPT_TEXT)
    assert "| endgame_elo_timeline | overall " in body_normalised, (
        "Section mapping table must assign `endgame_elo_timeline` to the "
        "`overall` section (Phase 87.5 D-07 subsection move from metrics_elo "
        "→ overall, lockstep with _SECTION_LAYOUT)."
    )
    # And the legacy row must not survive.
    assert "| endgame_elo_timeline | metrics_elo " not in body_normalised, (
        "Legacy `endgame_elo_timeline | metrics_elo` mapping row still in prompt"
    )
