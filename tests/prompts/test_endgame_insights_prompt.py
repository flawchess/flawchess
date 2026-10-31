"""Regression snapshot tests for `app/prompts/endgame_insights.md`.

The LLM prompt frames the Endgame ELO on the Endgame Score Gap: the
"Conversion ELO" label and every `conversion_elo*` identifier are gone in favor
of `endgame_elo*` / "Endgame ELO", and the glossary prose uses the
"lifts up / holds back" metaphor.

These assertions enforce:
- no "Conversion ELO" string in the live prompt (regression-test gated
  separately at the repo level via `tests/test_no_conversion_elo_string.py`).
- identifier names, the subsection mapping from `metrics_elo` →
  `overall`, and the prose metaphor.

These are content-grep tests rather than full snapshot files because:
- The prompt is a large markdown blob (~1k lines); a full-file snapshot
  would be noisy on every unrelated copy edit.
- The prompt contract is concretely about "this string MUST / MUST NOT
  appear", which grep-style assertions express directly.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"
_PROMPT_TEXT: str = _PROMPT_PATH.read_text(encoding="utf-8")
_PROMPT_TEXT_LOWER: str = _PROMPT_TEXT.lower()


def test_no_conversion_elo_text() -> None:
    """Case-insensitive 'Conversion ELO' and literal 'conversion_elo' both gone."""
    assert "conversion elo" not in _PROMPT_TEXT_LOWER, (
        "'Conversion ELO' phrase still present in app/prompts/endgame_insights.md"
    )
    assert "conversion_elo" not in _PROMPT_TEXT, (
        "'conversion_elo' identifier still present in app/prompts/endgame_insights.md"
    )


def test_no_conversion_elo_timeline_id() -> None:
    """The legacy subsection identifier is replaced."""
    assert "conversion_elo_timeline" not in _PROMPT_TEXT, (
        "Legacy subsection id 'conversion_elo_timeline' still present in prompt"
    )


def test_no_conversion_elo_gap_id() -> None:
    """The legacy metric identifier is replaced."""
    assert "conversion_elo_gap" not in _PROMPT_TEXT, (
        "Legacy metric id 'conversion_elo_gap' still present in prompt"
    )


def test_endgame_elo_timeline_subsection_present() -> None:
    """The subsection heading prose is in place."""
    assert "Endgame ELO Timeline" in _PROMPT_TEXT, (
        "Expected 'Endgame ELO Timeline' subsection heading in prompt"
    )


def test_endgame_elo_timeline_id_present() -> None:
    """The subsection identifier wires up the series block."""
    assert "endgame_elo_timeline" in _PROMPT_TEXT, (
        "Expected restored subsection id 'endgame_elo_timeline' in prompt"
    )


def test_endgame_elo_gap_id_present() -> None:
    """The metric identifier feeds the gap bullet."""
    assert "endgame_elo_gap" in _PROMPT_TEXT, (
        "Expected restored metric id 'endgame_elo_gap' in prompt"
    )


def test_lifts_up_metaphor_present() -> None:
    """The 'lifts / lifting' headline metaphor is present."""
    assert re.search(r"\blift", _PROMPT_TEXT, re.IGNORECASE) is not None, (
        "Expected at least one 'lift' / 'lifting' / 'lifts' token in prompt prose"
    )


def test_holds_back_metaphor_present() -> None:
    """The 'holds back / holding back' headline metaphor is present."""
    pattern = re.compile(r"\bholds?\s+back\b|\bholding\s+back\b", re.IGNORECASE)
    assert pattern.search(_PROMPT_TEXT) is not None, (
        "Expected at least one 'hold back' / 'holds back' / 'holding back' token in prompt prose"
    )


def test_no_delta_es_token() -> None:
    """Forbidden-token rule: no ΔES variants in user-facing narration.

    The tokens may appear on lines that *declare* them as forbidden ("Do NOT use ΔES",
    "Forbidden internal coinages"); those are meta-narration to the LLM and are
    explicitly allowed. Every other line that uses the token is a violation.
    """
    forbidden = re.compile(r"ΔES|delta_es|conv_ΔES|Conv ΔES")
    offenders: list[str] = []
    for lineno, line in enumerate(_PROMPT_TEXT.splitlines(), start=1):
        if not forbidden.search(line):
            continue
        lowered = line.lower()
        if "forbidden" in lowered or "do not use" in lowered:
            continue
        offenders.append(f"L{lineno}: {line.strip()}")
    assert not offenders, (
        "Forbidden ΔES tokens present in prompt outside meta-narration:\n"
        + "\n".join(offenders)
        + "\nPhase 87.5 uses 'Endgame Score Gap' as the user-facing series name."
    )


def test_section_mapping_assigns_endgame_elo_timeline_to_overall() -> None:
    """The section mapping table assigns endgame_elo_timeline to `overall`, not `metrics_elo`."""
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


# ---------------------------------------------------------------------------
# Filter-free, per-TC, ranked-sample report (prompt v48).
# ---------------------------------------------------------------------------


def test_no_scoping_caveat_or_opponent_strength_scoping() -> None:
    """The report has no filters, so the scoping caveat and its section are gone."""
    assert "Scoping caveat" not in _PROMPT_TEXT
    assert "Opponent strength scoping" not in _PROMPT_TEXT
    assert "opponent strength filter" not in _PROMPT_TEXT_LOWER


def test_no_page_level_weighted_peer_rank() -> None:
    """Every pctl token is per TC; the game-count-weighted page-level rank is gone."""
    assert "weighted mean across TCs" not in _PROMPT_TEXT
    assert "game-count-weighted" not in _PROMPT_TEXT
    assert "Page-level tokens" not in _PROMPT_TEXT
    assert "Worked example — page-level" not in _PROMPT_TEXT


def test_granularity_rule_states_every_pctl_token_is_per_tc() -> None:
    """score_gap and achievable_score_gap tokens are per TC too."""
    assert "Every `pctl=` token is per time control" in _PROMPT_TEXT
    assert "including `score_gap` and `achievable_score_gap`" in _PROMPT_TEXT
    assert "never average or combine tokens across time controls" in _PROMPT_TEXT


def test_window_anchoring_describes_the_ranked_sample_not_gauges() -> None:
    """The page shows the ranked sample per TC; the gauges are gone."""
    assert "all_time` in the payload IS that ranked sample" in _PROMPT_TEXT
    assert "last 36 months" in _PROMPT_TEXT
    assert "headline gauges" not in _PROMPT_TEXT
    assert "the page's headline numbers" in _PROMPT_TEXT


def test_overall_subsections_are_narrated_per_time_control() -> None:
    """Overall findings carry time_control and are never averaged across TCs."""
    assert "**Per time control.**" in _PROMPT_TEXT
    assert "`| time_control=<tc>` dim" in _PROMPT_TEXT
    assert "never average across time controls" in _PROMPT_TEXT


def test_banned_vocabulary_and_peer_rank_phrasing_rules_survive() -> None:
    """The v48 edit must not touch the banned-vocabulary or peer-rank phrasing rules."""
    assert "Banned vocabulary" in _PROMPT_TEXT
    assert 'Never write "percentile"' in _PROMPT_TEXT
    assert "No parallel significance signal" in _PROMPT_TEXT
    assert "in the bottom N% of ~A-rated {tc} players" in _PROMPT_TEXT


def test_prompt_version_is_v48() -> None:
    """The version bump invalidates every v47 cache row."""
    from app.services import insights_llm

    assert insights_llm._PROMPT_VERSION == "endgame_v50"
