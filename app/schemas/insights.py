"""Pydantic v2 schemas for the endgame findings pipeline (Phase 63).

Defined per FIND-01 / FIND-05 — the schema is the contract consumed by
`insights_service.compute_findings` (Plan 04) and by the Phase 65 LLM endpoint's
prompt-assembly. Field names are LOCKED once this ships: renaming after
Phase 65 forces a prompt revision.

Re-exports `Zone`, `Trend`, `SampleQuality`, `Window`, `MetricId`, and
`SubsectionId` from `app.services.endgame_zones` so consumers only need one
import path. Plan 01 owns those type aliases; this module does not redefine
them.

Field declaration order matters for `findings_hash` determinism (FIND-05):
Pydantic v2's `model_dump_json` emits fields in declaration order, and the
service re-serialises with `json.dumps(sort_keys=True)` for cross-session
stability (see Plan 04 / RESEARCH.md §Hash Implementation).
"""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Re-import the Literal aliases owned by Plan 01 so `from app.schemas.insights
# import Zone` works and consumers do not need to know about
# `app.services.endgame_zones`.
from app.services.endgame_zones import (
    MetricId as MetricId,
)
from app.services.endgame_zones import (
    SampleQuality as SampleQuality,
)
from app.services.endgame_zones import (
    SubsectionId as SubsectionId,
)
from app.services.endgame_zones import (
    Trend as Trend,
)
from app.services.endgame_zones import (
    Window as Window,
)
from app.services.endgame_zones import (
    Zone as Zone,
)

__all__ = [
    "EndgameTabFindings",
    "FilterContext",
    "FlagId",
    "MetricId",
    "SampleQuality",
    "SectionId",
    "SubsectionFinding",
    "SubsectionId",
    "Trend",
    "Window",
    "Zone",
]


# ---------------------------------------------------------------------------
# Literal aliases owned by this module (cross-section concepts, not zone-level).
# ---------------------------------------------------------------------------

# Four cross-section flags precomputed deterministically by the findings
# service (CONTEXT.md D-09). The Phase 65 prompt references these IDs
# verbatim, so the set is locked: adding or renaming a flag requires a
# prompt-assembly update.
FlagId = Literal[
    "baseline_lift_mutes_score_gap",
    "clock_entry_advantage",
    "no_clock_entry_advantage",
    "notable_endgame_elo_divergence",
]

# Section grouping used by Phase 65 prompt-assembly. NOT stored on
# SubsectionFinding — section membership is derived at consumption time
# (CONTEXT.md §Specifics).
SectionId = Literal[
    "overall",
    "metrics_elo",
    "time_pressure",
    "type_breakdown",
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FilterContext(BaseModel):
    """User's active dashboard filter state, forwarded to `compute_findings`.

    Mirrors the endgame router's query-parameter surface. Three caveats:

    1. ``color`` is carried here for filter-faithfulness but is NOT forwarded
       to ``endgame_service.get_endgame_overview`` (which has no color filter).
       Per INS-03, ``color`` is also NOT fed into the LLM prompt — Phase 65
       treats it as context-only. Plan 63-03 defines the schema; wiring is a
       Plan 63-04 concern (the service must drop ``color`` before calling
       the endgame service).

    2. ``rated_only`` is included for filter-faithfulness and IS forwarded
       to the endgame service (as the ``rated`` parameter). Per INS-03 it is
       not fed into the LLM prompt.

    3. ``opponent_type`` is hardcoded to ``"human"`` inside
       ``compute_findings``; Phase 63 does not expose bot-filter findings.

    4. ``recency`` is the user's dashboard recency filter — SEPARATE from the
       two internal windows (``all_time``, ``last_3mo``) that
       ``compute_findings`` always produces (RESEARCH.md §Pitfall 4).
    """

    recency: Literal[
        "all_time",
        "week",
        "month",
        "3months",
        "6months",
        "year",
        "3years",
        "5years",
    ] = "all_time"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    color: Literal["all", "white", "black"] = "all"
    time_controls: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    rated_only: bool = False


class SubsectionFinding(BaseModel):
    """Finding for one subsection x one time window.

    Empty-window convention: when a subsection has zero qualifying games for
    the window, the service emits ``value=float('nan')`` (serialised as JSON
    ``null`` by Pydantic v2), ``zone="typical"``, ``trend="n_a"``,
    ``sample_size=0``, ``sample_quality="thin"``,
    ``is_headline_eligible=False``. Phase 65 prompt-assembly skips findings
    where ``sample_quality == "thin"`` AND ``value`` is null.

    ``dimension`` carries per-combo or per-bucket identity (e.g.
    ``{"platform": "chess.com", "time_control": "blitz"}`` for
    ``endgame_elo_timeline``, ``{"bucket": "conversion"}`` for
    ``endgame_metrics`` bucketed rows). Keeping combo identity in a dedicated
    ``dict[str, str] | None`` preserves the ``value: float`` contract.

    Field declaration order is load-bearing for ``findings_hash`` stability
    (Plan 04 re-serialises with ``json.dumps(sort_keys=True)`` for final
    determinism, but the declaration order is still the canonical shape).
    """

    subsection_id: SubsectionId
    parent_subsection_id: SubsectionId | None = None
    window: Window
    metric: MetricId
    value: float
    zone: Zone
    trend: Trend
    weekly_points_in_window: int
    sample_size: int
    sample_quality: SampleQuality
    is_headline_eligible: bool
    dimension: dict[str, str] | None = None


class EndgameTabFindings(BaseModel):
    """Deterministic findings for the Endgame tab.

    ``findings_hash`` is a 64-char lowercase hex SHA256 of the canonical JSON
    of this model with ``as_of`` and ``findings_hash`` itself excluded.
    Excluding ``as_of`` means identical findings on different days cache-hit
    (FIND-05).

    ``findings_hash`` is populated by ``compute_findings`` AFTER all other
    fields are set. Callers pass ``findings_hash=""`` as a placeholder during
    construction; the service computes the hash and returns a new model with
    the hash filled.
    """

    as_of: datetime.datetime
    filters: FilterContext
    findings: list[SubsectionFinding]
    flags: list[FlagId]
    findings_hash: str
