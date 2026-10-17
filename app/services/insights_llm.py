"""LLM insights orchestration service for the endgame insights endpoint.

Scope:
- get_insights_agent(): singleton pydantic-ai Agent.
- generate_insights(user_id, session): sole orchestration entry point called by
  app/routers/insights.py. Handles tier-1 cache, fresh LLM call, and log-row
  write. Filter-free: one report per user.
- get_cached_insights_response(session, user_id): the regeneration cache rule
  (import invalidation + 30d max age) used by generate_insights.
- get_latest_insights_response(session, user_id): the display lookup behind
  GET /insights/endgame/cached (latest report, never invalidated).
- Custom exceptions map to HTTP status codes at the router layer.

Critical invariants:
- Sequential awaits on `session`; never asyncio.gather (CLAUDE.md constraint).
- _SYSTEM_PROMPT loaded at module import — module cannot import if the
  prompt file is missing. This is intentional: the app must fail to start
  if the system prompt is missing.
- Sentry set_context uses structured data (user_id, findings_hash, model,
  endpoint); NEVER f-string interpolation in exception messages (CLAUDE.md
  Sentry rules).
- Latency captured around `await agent.run(user_prompt)` only.
"""

import datetime
import functools
import math
import time
from pathlib import Path
from collections.abc import Callable, Sequence
from typing import Literal, cast

import sentry_sdk
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.import_job_repository import get_latest_completed_import_with_games_at
from app.repositories.llm_log_repository import (
    acquire_insights_generation_lock,
    create_llm_log,
    get_latest_successful_log_for_user,
)
from app.schemas.endgames import (
    EndgameCategoryStats,
    EndgameClass,
    RankedTcStats,
    RankStatus,
    TimeControlBucket,
)
from app.schemas.insights import (
    EndgameInsightsReport,
    EndgameInsightsResponse,
    EndgameTabFindings,
    MetricPercentileRecord,
    PlayerProfileEntry,
    RatingAnchorContext,
    SubsectionFinding,
    TimePoint,
)
from app.models.llm_log import LlmLog
from app.schemas.llm_log import LlmLogCreate, LlmLogEndpoint, LlmLogFilterContext
from app.services.endgame_zones import (
    MIN_GAMES_PER_TC_CARD,
    BUCKETED_ZONE_REGISTRY,
    PER_CLASS_GAUGE_ZONES,
    PER_CLASS_TC_GAUGE_ZONES,
    TC_METRIC_BANDS,
    ZONE_REGISTRY,
    TcBandMetricId,
    ZoneSpec,
    tc_metric_zone_spec,
)
from app.services.global_percentile_cdf import CdfMetricId
from app.services.insights_service import (
    SPARSE_COMBO_FLOOR,
    _sorted_type_categories,
    compute_findings,
)

# -- Module-level constants (CLAUDE.md: no magic numbers) --

# The five metrics_elo metrics whose inline zone band + proximity
# hint are per-TC (sourced from TC_METRIC_BANDS via the finding's `time_control`
# dimension). score_gap_parity is intentionally absent — its neutral band is
# global, so it falls through to the scalar ZONE_REGISTRY branch.
_TC_BAND_METRICS: frozenset[str] = frozenset(
    {
        "conversion_win_pct",
        "parity_score_pct",
        "recovery_save_pct",
        "score_gap_conv",
        "score_gap_recov",
    }
)

# The insights cache is one row per (user_id, prompt_version, model).
# `llm_logs.filter_context.opponent_strength` is kept as a column/JSON shape (no
# migration) and always written and matched as this constant.
INSIGHTS_CACHE_OPPONENT_STRENGTH: Literal["any"] = "any"

# v49: adds the 1-2 sentence `summary` field shown as the Insights block header.
# v48: findings come from the ranked sample (last 36 months, opponents within 100 Elo, up to 3000 games per TC), overall findings are per TC, no filter scoping; bumping invalidates every v47 cache row.
_PROMPT_VERSION = "endgame_v49"
_OUTPUT_RETRIES = 2  # structured-output validation retries before InsightsValidationFailure
_ENDPOINT: LlmLogEndpoint = "insights.endgame"

# Structural cache TTL safety net: bounds the sliding 3-month
# window narrative drift on cache hits. Lower to 14 if users complain about
# stale narratives.
INSIGHTS_CACHE_MAX_AGE_DAYS = 30
INSIGHTS_CACHE_MAX_AGE = datetime.timedelta(days=INSIGHTS_CACHE_MAX_AGE_DAYS)

# Series / prompt-assembly filter constants.
MIN_BUCKET_N: int = 3  # drop timeline points with n<3
_ACTIVITY_GAP_DAYS: int = 90  # insert gap markers between >90-day-apart points
_ALL_TIME_CUTOFF_DAYS: int = 90  # trim last 90d from all_time series when last_3mo exists
# Cap all_time series at the most-recent N monthly points. Older
# history rarely adds narrative value — Series interpretation rule already
# tells the LLM to focus on multi-bucket direction, not long history.
# 36 monthly points (3 years) lets the LLM speak about multi-year trajectories
# without overclaiming a 12-month window as a long-term arc.
_ALL_TIME_MAX_POINTS: int = 36
# Mirror frontend MIN_GAMES_FOR_RELIABLE_STATS (frontend/src/lib/theme.ts) so
# the LLM sees the same bucket gating as the rendered chart.
_MIN_GAMES_FOR_RELIABLE_BUCKET: int = 10

# Metrics already emitted on a non-fractional scale (Elo points or percentage points).
# Everything else is a fraction in [0, 1] (or signed [-1, +1] for score_gap) at the
# service layer and gets multiplied by 100 here so the LLM payload matches the UI's
# 0-100 percentage scale. Keeping the registry/service layer fractional
# keeps the frontend gauge codegen unchanged; the scale flip lives at the formatter only.
_NON_FRACTIONAL_METRICS: frozenset[str] = frozenset(
    # "endgame_elo_gap" must match the MetricId Literal in app/services/endgame_zones.py.
    # avg_clock_diff_pct and net_timeout_rate are absent: no page-level finding
    # carries them.
    {"endgame_elo_gap", "entry_eval_pawns"}
)

# Metrics whose ZONE_REGISTRY entry is a no-op `[0, 1]` placeholder (registered
# only so `assign_zone` does not raise). They must not render an inline
# `(typical ...)` band tag, since the band would be meaningless. The bare
# `endgame_score` (in subsection `endgame_start_vs_end`) DOES have a real
# [0.45, 0.55] band and is intentionally absent from this set.
_NO_BAND_METRICS: frozenset[str] = frozenset(
    {"endgame_score_timeline", "non_endgame_score_timeline"}
)

# Metrics whose raw payload value is already on the rendered scale AND should
# render with sub-integer precision. entry_eval_pawns renders
# at 2 decimals so values like `+0.47` survive the round-trip into the prompt
# instead of collapsing to `+0` under the default `:+.0f` format.
_VALUE_PRECISION: dict[str, int] = {"entry_eval_pawns": 2}


def _scale_for_metric(metric_id: str) -> float:
    """Multiplier applied to a raw metric value before rendering in the prompt."""
    return 1.0 if metric_id in _NON_FRACTIONAL_METRICS else 100.0


def _precision_for_metric(metric_id: str) -> int:
    """Decimal precision for rendering a metric's scaled value."""
    return _VALUE_PRECISION.get(metric_id, 0)


# Enrichment thresholds.
_STALE_SERIES_THRESHOLD_DAYS: int = 183  # ~6 months: a combo whose last bucket is this far behind the newest bucket across any series is flagged STALE.
_TREND_MIN_POINTS: int = 4  # minimum retained buckets before we emit trend fields in [summary]
_TREND_FLAT_THRESHOLD: float = (
    3.0  # on the 0-100 scale; |latest - mean(prior 3)| below this reads as flat
)
_DELTA_WITHIN_NOISE_SHIFT: float = (
    5.0  # |all_time → last_3mo| shift on 0-100 scale below this reads as within-noise
)
# |Elo delta| below this reads as within-noise for endgame_elo_gap
_DELTA_WITHIN_NOISE_ELO: float = 50.0
# Trend flat threshold for derived [summary endgame_elo] (absolute Elo
# scale). Roughly half the within-noise cap — bucket-to-bucket Elo drift below
# this reads as flat. Separate from _TREND_FLAT_THRESHOLD which is on the 0-100
# percent scale.
_TREND_FLAT_THRESHOLD_ELO: float = 25.0
_DELTA_SMALL_SAMPLE_RATIO: float = 0.20  # last_3mo_n / all_time_n below this → within-noise flag only fires with this much size mismatch

# Proximity hint thresholds: inline `[near edge]` marker on bullets whose
# value sits within this many points of a zone boundary. Different scales for
# percent-scale metrics (0-100) and Elo-scale metrics.
_PROXIMITY_PCT_THRESHOLD: float = 2.0
_PROXIMITY_ELO_THRESHOLD: float = 20.0
# entry_eval_pawns lives on a sub-integer scale (raw pawns).
# Distance-from-band-edge threshold is 5 cp ≈ 0.05 pawns — same eyeball
# proximity as ±2pp on a 0-100 scale.
_PROXIMITY_PAWN_THRESHOLD: float = 0.05

# Weakest-type tag: requires the lowest score_pct to be clearly separated
# from the next-lowest AND to have a meaningful sample (avoids noise calls).
_WEAKEST_TYPE_MIN_GAMES: int = 100
_WEAKEST_TYPE_MIN_SEPARATION: float = 2.0  # on 0-100 score_pct scale

# Recovery pattern tag: fires when Recovery sits weak across at least this
# many endgame types.
_RECOVERY_PATTERN_MIN_WEAK_TYPES: int = 4


_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _build_zone_threshold_appendix() -> str:
    """Render ZONE_REGISTRY + BUCKETED_ZONE_REGISTRY as a markdown appendix.

    Auto-generated at module load so the LLM always sees the current numeric
    bands. Kept separate from the hand-authored system-prompt markdown so
    prompt-version bumps aren't required when thresholds change (the cache
    key is findings_hash + prompt_version + model — threshold changes
    propagate via findings_hash since zones are baked into findings).
    """
    lines: list[str] = ["", "## Zone thresholds", ""]
    lines.append(
        "Numeric bands for each metric (auto-generated — do not contradict). "
        "These same bands are also inlined next to every finding bullet as "
        "`(typical LO to UP[, lower is better])`; this appendix is the full "
        "reference, the inline fragment is the per-bullet shorthand."
    )
    lines.append("")
    for metric_id, spec in ZONE_REGISTRY.items():
        scale = _scale_for_metric(metric_id)
        precision = _precision_for_metric(metric_id)
        lo = spec.typical_lower * scale
        hi = spec.typical_upper * scale
        if spec.direction == "higher_is_better":
            lines.append(
                f"- `{metric_id}`: weak<{lo:.{precision}f}, "
                f"typical [{lo:.{precision}f}, {hi:.{precision}f}], "
                f"strong>{hi:.{precision}f}"
            )
        else:
            lines.append(
                f"- `{metric_id}` (lower_is_better): strong<={lo:.{precision}f}, "
                f"typical [{lo:.{precision}f}, {hi:.{precision}f}], "
                f"weak>{hi:.{precision}f}"
            )
    lines.append("")
    lines.append("Bucketed metrics (one band per MaterialBucket):")
    for metric_id, buckets in BUCKETED_ZONE_REGISTRY.items():
        scale = _scale_for_metric(metric_id)
        precision = _precision_for_metric(metric_id)
        lines.append(f"- `{metric_id}`:")
        for bucket, spec in buckets.items():
            lo = spec.typical_lower * scale
            hi = spec.typical_upper * scale
            lines.append(
                f"  - {bucket}: weak<{lo:.{precision}f}, "
                f"typical [{lo:.{precision}f}, {hi:.{precision}f}], "
                f"strong>{hi:.{precision}f}"
            )
    return "\n".join(lines) + "\n"


_SYSTEM_PROMPT = (_PROMPTS_DIR / "endgame_insights.md").read_text(
    encoding="utf-8"
) + _build_zone_threshold_appendix()


# -- Custom exceptions (the router maps them to HTTP statuses) --


class InsightsProviderError(Exception):
    """pydantic-ai ModelAPIError or unknown exception. Router -> 502."""

    def __init__(self, error_marker: str) -> None:
        super().__init__(error_marker)
        self.error_marker = error_marker


class InsightsValidationFailure(Exception):
    """Structured-output validation exhausted output_retries. Router -> 502."""

    def __init__(self, error_marker: str) -> None:
        super().__init__(error_marker)
        self.error_marker = error_marker


# -- Agent singleton --

_GOOGLE_PREFIXES = ("google:", "google-cloud:")
_GEMINI3_MODEL_MARKER = "gemini-3"  # Gemini 3+ uses thinking_level; older uses thinking_budget


def _build_google_thinking_config(model_name: str) -> dict[str, object]:
    """Return the google_thinking_config dict appropriate for this model.

    Gemini 3+ models use `thinking_level: 'low' | 'high'`. Older Gemini
    models (e.g. gemini-2.5-flash) use `thinking_budget: int` where 0 disables
    thinking entirely. `include_thoughts=True` makes the provider return
    `usage_metadata.thoughts_token_count` so the service can persist it.
    """
    config: dict[str, object] = {"include_thoughts": settings.GEMINI_INCLUDE_THOUGHTS}
    if _GEMINI3_MODEL_MARKER in model_name:
        config["thinking_level"] = settings.GEMINI_THINKING_LEVEL
    else:
        config["thinking_budget"] = settings.GEMINI_THINKING_BUDGET
    return config


@functools.lru_cache(maxsize=1)
def get_insights_agent() -> Agent[None, EndgameInsightsReport]:
    """Return the singleton pydantic-ai Agent, constructing on first call.

    For Google-provider models ("google:" / "google-cloud:" prefix) the
    Agent is constructed from an explicit `GoogleModel` plus a
    `GoogleModelSettings` carrying `google_thinking_config`. This lets us cap
    thinking cost (thinking_level=low on Gemini 3; thinking_budget=0 on 2.5)
    and ask the provider to surface `thoughts_token_count` so the insights
    service can persist it to `llm_logs.thinking_tokens`.

    For all other providers (Anthropic, OpenAI, test) we keep the plain
    string-form Agent constructor — no thinking control surface, and
    pydantic-ai silently ignores the Google-specific settings anyway.

    Raises:
        UserError: empty PYDANTIC_AI_MODEL_INSIGHTS, unknown model suffix, or
            unknown provider prefix (e.g., "bogus-provider:foo"). The provider
            case raised a bare ValueError before pydantic-ai 2.39, which now
            wraps it in UserError (a RuntimeError subclass, not a ValueError).

    Called from (a) main.py lifespan for startup validation, and
    (b) generate_insights() at request time. lru_cache ensures one Agent
    instance across the app lifetime; pydantic-ai Agents are async-safe.
    """
    model_str = settings.PYDANTIC_AI_MODEL_INSIGHTS
    if model_str.startswith(_GOOGLE_PREFIXES):
        provider_prefix, _, model_name = model_str.partition(":")
        # provider_prefix is "google" (Gemini API) or "google-cloud" (Vertex) —
        # the current pydantic-ai GoogleModel provider names (the legacy
        # "google-gla"/"google-vertex" spellings were removed in 1.99.0). cast
        # to satisfy the Literal param; the startswith check above guarantees
        # provider_prefix is one of the two accepted values.
        provider_literal = cast(Literal["google", "google-cloud"], provider_prefix)
        google_model = GoogleModel(model_name, provider=provider_literal)
        google_settings = GoogleModelSettings(
            google_thinking_config=_build_google_thinking_config(model_name),  # ty: ignore[invalid-argument-type]
        )
        return Agent(
            google_model,
            output_type=EndgameInsightsReport,
            system_prompt=_SYSTEM_PROMPT,
            retries={"output": _OUTPUT_RETRIES},
            model_settings=google_settings,
        )
    return Agent(
        model_str,
        output_type=EndgameInsightsReport,
        system_prompt=_SYSTEM_PROMPT,
        retries={"output": _OUTPUT_RETRIES},
    )


# -- User-prompt assembly --

# Subsections that produce Series blocks in the prompt.
_TIMELINE_SUBSECTION_IDS: frozenset[str] = frozenset(
    {
        "score_timeline",
        "clock_diff_timeline",
        "endgame_elo_timeline",
    }
)


def _render_zone_spec(spec: ZoneSpec, metric_id: str) -> str:
    """Format a resolved `ZoneSpec` as '(typical LO to UP[, lower is better])'."""
    scale = _scale_for_metric(metric_id)
    precision = _precision_for_metric(metric_id)
    lo = spec.typical_lower * scale
    hi = spec.typical_upper * scale
    direction_note = ", lower is better" if spec.direction == "lower_is_better" else ""
    return f"(typical {lo:+.{precision}f} to {hi:+.{precision}f}{direction_note})"


def _format_zone_bounds(metric_id: str, dimension: dict[str, str] | None) -> str:
    """Render '(typical LO to UP[, lower is better])' for a finding bullet.

    Inline shorthand of the zone band for each finding,
    so the LLM can judge proximity to a zone edge without consulting the
    global appendix. Bucketed metrics (conversion_win_pct / parity_score_pct /
    recovery_save_pct) dispatch via `dimension['bucket']`; all other scalar
    metrics use ZONE_REGISTRY directly. Returns '' for unknown metric_ids
    (defensive — shouldn't fire for valid findings since MetricId is enumerated).

    When a conversion_win_pct / recovery_save_pct
    finding carries an `endgame_class` dimension, dispatch via
    PER_CLASS_GAUGE_ZONES so the inline bound matches the per-class zone the
    finding's `zone` label was computed against. Without this, every per-type
    Conv/Recov line printed the same global band and contradicted the table.

    endgame_score_timeline / non_endgame_score_timeline
    have no calibrated zone band — their registry entries span [0, 1] only so
    assign_zone does not raise. Skip the bounds render for those two so
    the prompt does not show a meaningless `(typical +0 to +100)` tag.
    The bare `endgame_score` (subsection `endgame_start_vs_end`) DOES have a
    calibrated [0.45, 0.55] band that should render. The skip-set lives in
    `_NO_BAND_METRICS`.
    """
    if metric_id in _NO_BAND_METRICS:
        return ""
    bucket = dimension.get("bucket") if dimension else None
    endgame_class = dimension.get("endgame_class") if dimension else None
    # metrics_elo findings carry a `time_control` dimension only;
    # their zone band is per-TC (TC_METRIC_BANDS). per-TC Endgame Type findings
    # carry BOTH endgame_class AND time_control — they band per-(class × TC) via
    # the PER_CLASS_TC_GAUGE_ZONES branch below (which precedes both the pooled
    # per-class and the TC_METRIC_BANDS branches).
    time_control = dimension.get("time_control") if dimension else None
    bucketed = cast("dict[str, dict[str, ZoneSpec]]", dict(BUCKETED_ZONE_REGISTRY))
    scalar = cast("dict[str, ZoneSpec]", dict(ZONE_REGISTRY))

    if (
        # Per-TC Endgame Type findings carry BOTH endgame_class and
        # time_control — band per-(class × TC) via PER_CLASS_TC_GAUGE_ZONES so the
        # inline bound matches the per-TC tile gauge. Must precede the pooled-class
        # branch below (which would otherwise win on endgame_class alone). Falls
        # through to the pooled-class branch when the (class, TC) cell is absent
        # (e.g. pawnless, omitted from PER_CLASS_TC_GAUGE_ZONES).
        metric_id
        in ("conversion_win_pct", "recovery_save_pct", "endgame_type_achievable_score_gap")
        and endgame_class is not None
        and time_control is not None
        and endgame_class in PER_CLASS_TC_GAUGE_ZONES
        and time_control in PER_CLASS_TC_GAUGE_ZONES[cast("EndgameClass", endgame_class)]
    ):
        tc_bands = PER_CLASS_TC_GAUGE_ZONES[cast("EndgameClass", endgame_class)][
            cast(TimeControlBucket, time_control)
        ]
        if metric_id == "conversion_win_pct":
            lo_hi = tc_bands.conversion
        elif metric_id == "recovery_save_pct":
            lo_hi = tc_bands.recovery
        else:
            lo_hi = tc_bands.achievable_score_gap
        return _render_zone_spec(ZoneSpec(lo_hi[0], lo_hi[1], "higher_is_better"), metric_id)

    if (
        metric_id in ("conversion_win_pct", "recovery_save_pct")
        and endgame_class is not None
        and endgame_class in PER_CLASS_GAUGE_ZONES
    ):
        bands = PER_CLASS_GAUGE_ZONES[cast("EndgameClass", endgame_class)]
        lo_hi = bands.conversion if metric_id == "conversion_win_pct" else bands.recovery
        return _render_zone_spec(ZoneSpec(lo_hi[0], lo_hi[1], "higher_is_better"), metric_id)

    if (
        # Per-class Score Gap bands (PER_CLASS_GAUGE_ZONES) override the global
        # ZONE_REGISTRY default.
        metric_id == "endgame_type_achievable_score_gap"
        and endgame_class is not None
        and endgame_class in PER_CLASS_GAUGE_ZONES
    ):
        bands = PER_CLASS_GAUGE_ZONES[cast("EndgameClass", endgame_class)]
        lo_hi = bands.achievable_score_gap
        return _render_zone_spec(ZoneSpec(lo_hi[0], lo_hi[1], "higher_is_better"), metric_id)

    if (
        # Per-TC band for the metrics_elo metrics.
        metric_id in _TC_BAND_METRICS
        and time_control is not None
        and time_control in TC_METRIC_BANDS
    ):
        spec = tc_metric_zone_spec(
            cast(TcBandMetricId, metric_id), cast(TimeControlBucket, time_control)
        )
        return _render_zone_spec(spec, metric_id)

    if metric_id in bucketed and bucket is not None:
        bucketed_spec = bucketed[metric_id].get(bucket)
        if bucketed_spec is None:
            return ""
        return _render_zone_spec(bucketed_spec, metric_id)

    if metric_id in scalar:
        return _render_zone_spec(scalar[metric_id], metric_id)

    return ""


def _render_player_profile_entry(entry: PlayerProfileEntry) -> list[str]:
    """Render one (platform, time_control) combo's `[summary actual_elo]` block.

    All_time line: current / min / max / mean / n / buckets / window / trend /
    std (plus `stale: ...` when the combo hasn't been played in >183 days).
    Last_3mo line: mean / n / buckets / trend / std, or `no data` when the
    combo has no calendar-recent activity. Sparse-history entries (Fix B)
    suppress trend/std on both lines — unreliable below ~20 weekly buckets.
    """
    is_sparse = entry.quality == "sparse"
    header = f"[summary actual_elo | platform={entry.platform}, time_control={entry.time_control}]"
    lines: list[str] = [header]

    at_parts = [
        f"current={entry.current_elo}",
        f"mean={entry.all_time_mean}",
        f"min={entry.min_elo}",
        f"max={entry.max_elo}",
        f"n={entry.all_time_n}",
        f"buckets={entry.all_time_buckets} (weekly)",
        f"window={entry.window_days}d",
    ]
    if not is_sparse:
        at_parts.append(f"trend={entry.all_time_trend}")
        at_parts.append(f"std={entry.all_time_std}")
    else:
        at_parts.append("quality=sparse")
    if entry.stale_last_bucket and entry.stale_months is not None:
        at_parts.append(f"stale: last {entry.stale_last_bucket} ({entry.stale_months} mo ago)")
    lines.append("  all_time: " + ", ".join(at_parts))

    if entry.last_3mo_mean is None:
        lines.append("  last_3mo: no data")
        return lines

    lm_parts = [
        f"mean={entry.last_3mo_mean}",
        f"n={entry.last_3mo_n}",
        f"buckets={entry.last_3mo_buckets} (weekly)",
    ]
    if not is_sparse and entry.last_3mo_trend is not None:
        lm_parts.append(f"trend={entry.last_3mo_trend}")
    if not is_sparse and entry.last_3mo_std is not None:
        lm_parts.append(f"std={entry.last_3mo_std}")
    if is_sparse:
        lm_parts.append("quality=sparse")
    lines.append("  last_3mo: " + ", ".join(lm_parts))
    return lines


def _player_profile_anchor_tag(profile: list[PlayerProfileEntry], *, all_sparse: bool) -> str:
    """Return the `[anchor-combo ...]` tag line for the player-profile block.

    Points at the most-played live combo (no stale marker). When every
    combo is stale, emits `all-stale` so the LLM frames the whole profile in
    past tense instead of fabricating a current-Elo read from a 27-month-old
    rating. Sparse-history profiles (Fix B) get their own cautionary variant.
    """
    if all_sparse:
        return (
            "[anchor-combo] sparse-history — narrate cautiously; only current Elo and "
            "basic range are reliable; do NOT claim trend, learning arc, or trajectory; "
            'use plain present-tense framing like "you play at ~<rating>"'
        )
    anchor: PlayerProfileEntry | None = next(
        (e for e in profile if e.stale_last_bucket is None),
        None,
    )
    if anchor is not None:
        return f"[anchor-combo platform={anchor.platform}, time_control={anchor.time_control}]"
    return "[anchor-combo] all-stale — narrate in past tense"


def _format_player_profile_block(
    profile: list[PlayerProfileEntry] | None,
) -> list[str]:
    """Render the `## Player profile` block as per-combo [summary actual_elo] blocks.

    Each qualifying (platform, time_control) combo emits one [summary] block
    (built by `_render_player_profile_entry`). Combos are already sorted by
    game count desc upstream in compute_player_profile. The leading
    `[anchor-combo ...]` tag (`_player_profile_anchor_tag`) frames which combo
    — or which caution — the LLM should anchor its narration to.
    """
    if not profile:
        return []
    lines: list[str] = ["## Player profile"]
    all_sparse = all(e.quality == "sparse" for e in profile)
    lines.append(_player_profile_anchor_tag(profile, all_sparse=all_sparse))
    for entry in profile:
        lines.extend(_render_player_profile_entry(entry))
    lines.append("")
    return lines


def _format_rating_basis_block(
    cohort_anchors: "dict[str, RatingAnchorContext] | None",
) -> list[str]:
    """Render the `## Rating basis` block listing per-TC Lichess-equivalent anchors.

    Emitted once near the top of the user prompt (after the
    player profile, before the Section blocks) so the LLM has one clear place to
    learn the Lichess-equivalent framing for this user's time controls. Mirrors the
    disclosure branches of the RankedMetricPopover anchor disclosure:

      (a) Mixed user (n_chesscom_games > 0 AND n_lichess_games > 0):
          Both platforms listed with their native medians.
      (b) Pure-lichess user (n_chesscom_games == 0):
          No conversion note — anchor IS the native rating; label "native".
      (c) Pure-chess.com user (n_lichess_games == 0):
          Anchor is the Lichess-equivalent of the chess.com rating; label
          shows chesscom_median_native so the LLM can cite the concrete mapping.
      (d) Suppressed (both counts == 0): TC omitted (should not occur — the anchor
          is suppressed upstream before reaching cohort_anchors).

    The block is omitted entirely when cohort_anchors is None or empty.
    Em-dash avoided in output text per CLAUDE.md style preference.
    """
    if not cohort_anchors:
        return []

    lines: list[str] = ["## Rating basis"]
    lines.append(
        "The cohort anchor A in every `pctl=` token is a Lichess-equivalent rating. "
        "chess.com ratings (Glicko-1) are converted up to the Lichess scale (Glicko-2), "
        "which typically runs 100-200 Elo higher below ~1800. "
        "Use this block when explaining the anchor to a chess.com-heavy user: "
        "state ONCE (in the overview or first percentile mention) that their chess.com "
        "rating corresponds to the Lichess-equivalent below, and that is the cohort "
        "they are compared against. For a pure-lichess user, no conversion note is needed."
    )
    lines.append("")

    tc_order = ("bullet", "blitz", "rapid", "classical")
    for tc in tc_order:
        ctx = cohort_anchors.get(tc)
        if ctx is None:
            continue
        anchor = ctx.anchor_rating
        n_cc = ctx.n_chesscom_games
        n_li = ctx.n_lichess_games
        cc_med = ctx.chesscom_median_native
        li_med = ctx.lichess_median_native

        if n_cc == 0 and n_li == 0:
            # Suppressed TC — skip.
            continue

        parts: list[str] = [f"anchor ~{anchor} (Lichess-equivalent)"]

        if n_cc > 0 and n_li > 0:
            # Mixed user: both platforms, show native medians when available.
            cc_part = (
                f"chess.com median ~{cc_med}" if cc_med is not None else "chess.com median n/a"
            )
            li_part = f"lichess median ~{li_med}" if li_med is not None else "lichess median n/a"
            parts.append(f"{cc_part} (converted)")
            parts.append(li_part)
            parts.append(f"games: {n_cc} cc / {n_li} li")
        elif n_cc > 0:
            # Pure chess.com: show native median so LLM can cite the mapping.
            cc_part = (
                f"chess.com median ~{cc_med} (converted)"
                if cc_med is not None
                else "chess.com median n/a (converted)"
            )
            parts.append(cc_part)
            parts.append("lichess median n/a")
            parts.append(f"games: {n_cc} cc / 0 li")
        else:
            # Pure lichess: anchor is native; no conversion note needed.
            li_part = (
                f"lichess median ~{li_med} (native)"
                if li_med is not None
                else "lichess median n/a (native)"
            )
            parts.append("chess.com median n/a")
            parts.append(li_part)
            parts.append(f"games: 0 cc / {n_li} li")

        lines.append(f"[rating basis] {tc}: " + " | ".join(parts))

    lines.append("")
    return lines


def _format_overall_wdl_chart_block(findings: EndgameTabFindings) -> list[str]:
    """Render the endgame-vs-non-endgame WDL + Score % comparison, one table per TC.

    Built from each ranked TC's ``overall`` block, so the rows
    are exactly the games the Stats tab shows for that time control, and the TCs are
    never pooled. Emits one ``### Chart: overall_wdl ({tc}, all_time)`` header per TC
    followed by a 2-row markdown table (endgame, non_endgame) with win_pct / draw_pct /
    loss_pct / score_pct columns. score_pct = (wins + 0.5*draws) / total (matches the
    UI's Endgame Performance section). Rows with fewer than
    _MIN_GAMES_FOR_RELIABLE_BUCKET games are skipped; a TC with no row is omitted.
    Returns [] when no ranked TC has a row.
    """
    lines: list[str] = []
    for tc_stats in findings.ranked_tcs:
        perf = tc_stats.overall
        rows: list[str] = []
        for label, summary in (
            ("endgame", perf.endgame_wdl),
            ("non_endgame", perf.non_endgame_wdl),
        ):
            total = summary.total
            if total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
                continue
            score_pct = (summary.wins + 0.5 * summary.draws) / total * 100.0
            rows.append(
                f"| {label:<11} | {total:<5} | {summary.win_pct:.0f}     | "
                f"{summary.draw_pct:.0f}      | {summary.loss_pct:.0f}      | "
                f"{score_pct:.0f}       |"
            )
        if not rows:
            continue
        lines.extend(
            [
                f"### Chart: overall_wdl ({tc_stats.tc}, all_time)",
                f"Two-row WDL comparison for {tc_stats.tc} games that reached an Endgame Phase "
                "vs games that did not. All columns are whole-number percentages; score_pct "
                "uses wins=100, draws=50, losses=0.",
                "| series      | games | win_pct | draw_pct | loss_pct | score_pct |",
                "| ----------- | ----- | ------- | -------- | -------- | --------- |",
            ]
        )
        lines.extend(rows)
        lines.append("")
    return lines


def _format_type_wdl_table(tc: str, categories: Sequence["EndgameCategoryStats"]) -> list[str]:
    """Render the per-TC W/D/L + Score % table that leads an `endgame_type_<tc>` subsection.

    Mirrors the TypeTable row's WDL bar +
    score: one row per visible endgame type
    (rook / minor_piece / pawn / queen — mixed and pawnless are already excluded
    upstream by `aggregate_endgame_stats_by_tc`). score_pct uses wins=100,
    draws=50, losses=0; a value above 50 means the user outscores opponents in
    that type (both sides played the same games), so there are no opponent/diff
    columns.

    Sorted by `total` descending via `_sorted_type_categories` so the row order
    matches the Conv/Recov/Score-Gap bullet order below it. Rows with fewer than
    `_MIN_GAMES_FOR_RELIABLE_BUCKET` games are skipped. A per-TC weakest-type tag
    is emitted above the table when one type clearly stands out.
    """
    # Defensive: mixed + pawnless are excluded upstream by
    # aggregate_endgame_stats_by_tc, but drop them here too so the table can never
    # surface a type the UI hides (mirrors the bullet-level pawnless filter).
    sorted_cats = [
        c
        for c in _sorted_type_categories(list(categories))
        if c.endgame_class not in ("mixed", "pawnless")
    ]
    rows: list[str] = []
    for cat in sorted_cats:
        if cat.total < _MIN_GAMES_FOR_RELIABLE_BUCKET:
            continue
        score_pct_int = round((cat.wins + 0.5 * cat.draws) / cat.total * 100.0)
        rows.append(
            f"| {cat.endgame_class:<12} | {cat.total:<5} | {cat.win_pct:.0f}     | "
            f"{cat.draw_pct:.0f}      | {cat.loss_pct:.0f}      | {score_pct_int}       |"
        )
    if not rows:
        return []
    lines: list[str] = [
        f"[WDL table — {tc}] Per-endgame-type W/D/L and Score % for this time control. "
        "All columns are whole-number percentages. score_pct uses wins=100, draws=50, "
        "losses=0; a score_pct above 50 means you outscore your opponents in that type "
        "(both sides played the same games).",
    ]
    weakest_tag = _weakest_type_tag(sorted_cats)
    if weakest_tag:
        lines.append(weakest_tag)
    lines.append("| endgame_type | games | win_pct | draw_pct | loss_pct | score_pct |")
    lines.append("| ------------ | ----- | ------- | -------- | -------- | --------- |")
    lines.extend(rows)
    lines.append("")
    return lines


# Fixed TC order so the per-TC WDL tables (and their subsections) render
# bullet → blitz → rapid → classical, matching the UI accordion + _SECTION_LAYOUT.
_TYPE_WDL_TC_ORDER: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")


def _build_type_wdl_tables(
    categories_by_tc: dict[TimeControlBucket, list["EndgameCategoryStats"]] | None,
) -> dict[str, list[str]]:
    """Pre-render the per-TC Endgame Type WDL table for each eligible time control.

    Returns ``{subsection_id: table_lines}`` keyed by
    ``endgame_type_<tc>``. A TC is included only when its summed endgame-game count
    across the four visible classes clears ``MIN_GAMES_PER_TC_CARD`` — the same gate
    the findings producer (insights_service._findings_endgame_type_by_tc) applies,
    so every emitted subsection has both findings and a matching WDL table.
    """
    if not categories_by_tc:
        return {}
    tables: dict[str, list[str]] = {}
    for tc in _TYPE_WDL_TC_ORDER:
        cats = categories_by_tc.get(tc)
        if not cats or sum(c.total for c in cats) < MIN_GAMES_PER_TC_CARD:
            continue
        table = _format_type_wdl_table(tc, cats)
        if table:
            tables[f"endgame_type_{tc}"] = table
    return tables


# Score-Gap-by-time per-quintile block: n-gated per-quintile sub-table per TC.
# Modeled on the per-TC WDL table builder: iterate cards, skip n-gated quintiles,
# build per-TC sub-table with typical_band from PRESSURE_BIN_SCORE_NEUTRAL_ZONES.
# Q4 (80-100% clock = min pressure) is dropped — the UI chart only renders Q0-Q3
# and the min-pressure bucket carries no time-pressure signal. Per-TC percentile
# aggregates are appended below each quintile table so the LLM reads the
# PERFORMANCE-under-pressure signal (Time-Pressure Score Gap) and the
# FREQUENCY-of-pressure signals (Clock Gap, Net Flag Rate) together.
_MAX_NARRATED_QUINTILE_INDEX = 3  # Q0-Q3 only; Q4 (80-100% clock) is min pressure.


def _format_time_pressure_score_gap_chart_block(
    findings: EndgameTabFindings,
    per_tc_metric_percentiles: dict[str, "MetricPercentileRecord"] | None = None,
) -> list[str]:
    """Render per-TC Score-Gap-by-Remaining-Time chart (Q0-Q3) + percentile aggregates.

    Per-quintile Score-Delta decomposition: for each TC, emits a sub-table with
    Q0-Q3 quintile rows (Q0=0-20% clock remaining / max pressure, Q3=60-80%). Q4
    (80-100% / min pressure) is excluded. Rows where opp_score is None (n-gate
    unmet) are skipped.

    Reads ``findings.ranked_tcs`` (``time_pressure.quintiles`` plus the
    TC's ranked ``metrics``), so the tables are the ranked-sample curve the Stats tab
    shows. A TC is rendered when its ranked endgame game count reaches
    MIN_GAMES_PER_TC_CARD.

    Per-quintile user_score and opp_score are fractions (0..1) — multiplied by 100
    here for the 0-100 scale. The typical_band column is sourced from
    PRESSURE_BIN_SCORE_NEUTRAL_ZONES[(tc, quintile_index)] so the LLM sees the same
    neutral band bounds the UI tooltip shows.

    Below each TC's quintile table, three per-TC
    percentile aggregates are appended via _time_pressure_aggregate_lines — the
    Time-Pressure Score Gap (performance under pressure) and the Clock Gap + Net
    Flag Rate (frequency of pressure). per_tc_metric_percentiles supplies the
    enriched records (keyed "{metric}:{tc}").

    This helper is NOT a _NON_FRACTIONAL_METRICS site — quintile scores are fractions
    scaled here, not listed in that set (which controls SubsectionFinding scaling).
    """
    from app.services.endgame_zones import PRESSURE_BIN_SCORE_NEUTRAL_ZONES

    lines: list[str] = []
    for tc_stats in findings.ranked_tcs:
        tc = tc_stats.tc
        if tc_stats.overall.endgame_wdl.total < MIN_GAMES_PER_TC_CARD:
            continue
        tc_rows: list[str] = []
        for bullet in tc_stats.time_pressure.quintiles:
            # Q4 (min pressure) excluded — matches the UI chart, no time-pressure signal.
            if bullet.quintile_index > _MAX_NARRATED_QUINTILE_INDEX:
                continue
            # Skip quintiles where the n-gate is unmet (opp_score is None when
            # min(n_user, n_opp) < MIN_GAMES_PER_PRESSURE_BIN in build_quintile_bullets).
            if bullet.opp_score is None:
                continue
            user_score_pct = (
                bullet.delta + bullet.opp_score
            ) * 100.0  # delta = user_score - opp_score; derive user_score fraction
            opp_score_pct = bullet.opp_score * 100.0
            score_delta_pct = bullet.delta * 100.0
            band = PRESSURE_BIN_SCORE_NEUTRAL_ZONES.get(tc, {}).get(bullet.quintile_index)
            if band is not None:
                typical_band = f"{band.lower * 100:+.1f} to {band.upper * 100:+.1f}"
            else:
                typical_band = "n/a"
            tc_rows.append(
                f"| {bullet.quintile_label:<7} | {user_score_pct:5.1f}      | "
                f"{opp_score_pct:5.1f}      | {score_delta_pct:+6.1f}       | "
                f"{bullet.n:<5} | {bullet.n_opp:<5} | {typical_band} |"
            )

        if not tc_rows:
            continue

        lines.append(f"### Chart: time_pressure_score_gap_by_time ({tc}, all_time)")
        lines.append(
            f"Per-quintile Score % for user vs opponent in {tc} endgames, bucketed by "
            "remaining clock % at endgame entry (Q0=0-20% clock=max pressure, "
            "Q3=60-80%; Q4/min-pressure omitted). user_score and opp_score are 0-100 "
            "(wins=100, draws=50, losses=0). score_delta = user_score − opp_score. "
            "typical_band = neutral delta range (pct pts) from cohort data."
        )
        lines.append(
            "| quintile | user_score | opp_score | score_delta | n     | n_opp | typical_band |"
        )
        lines.append(
            "| -------- | ---------- | --------- | ----------- | ----- | ----- | ------------ |"
        )
        lines.extend(tc_rows)
        lines.append("")
        lines.extend(_time_pressure_aggregate_lines(tc_stats, tc, per_tc_metric_percentiles))

    return lines


# Rank statuses whose ranked value cleared its sample floor (see RankStatus).
_FLOOR_CLEARED_STATUSES: frozenset[RankStatus] = frozenset({"ranked", "unranked"})


def _aggregate_value_or_pctl(
    label: str, rec: "MetricPercentileRecord | None", fallback_fraction: float | None
) -> str | None:
    """Render one aggregate bullet: the pctl= token when a percentile record exists, else
    the raw ranked value, else nothing.

    `fallback_fraction` is the TC's ranked metric value as a fraction (×100 → signed %).
    The caller passes it only for cells that cleared their sample floor (status ranked or
    unranked), so a below-floor value is never narrated.
    Returns None when there is neither a percentile nor a value (nothing to narrate).
    """
    if rec is not None:
        return label + _build_pctl_token(rec)
    if fallback_fraction is not None:
        return label + f"value={fallback_fraction * 100:+.0f}% (no peer percentile yet)"
    return None


def _time_pressure_aggregate_lines(
    tc_stats: "RankedTcStats",
    tc: str,
    per_tc_metric_percentiles: dict[str, "MetricPercentileRecord"] | None,
) -> list[str]:
    """Per-TC time-pressure percentile aggregates appended below the quintile table.

    Three metrics, two stories the LLM must keep distinct:
      • Time-Pressure Score Gap — PERFORMANCE under pressure (how the player
        *scores* when short on the clock; Q0+Q1 combined, own clock < 40%).
      • Clock Gap + Net Flag Rate — FREQUENCY of pressure (how *often* the player
        is the one short on time / gets flagged).
    Each line cites the percentile vs equally-rated peers (value embedded in the
    pctl= token). Values come from the TC's ranked ``metrics``; a line is
    rendered when a percentile record or a floor-cleared ranked value exists, and
    omitted otherwise.
    """
    percentiles = per_tc_metric_percentiles or {}
    lines: list[str] = [
        f"Time-pressure aggregates ({tc}, all_time) — vs equally-rated peers. "
        "Time-Pressure Score Gap = PERFORMANCE under pressure (how you score); "
        "Clock Gap + Net Flag Rate = FREQUENCY of pressure (how often you are the one "
        "short on time). A weak score gap AND frequent pressure compound:"
    ]

    aggregates: tuple[tuple[CdfMetricId, str], ...] = (
        (
            "time_pressure_score_gap",
            "- Time-Pressure Score Gap (Q0+Q1 combined, own clock <40% remaining; "
            "higher is better): ",
        ),
        (
            "clock_gap",
            "- Clock Gap (your clock vs opponent's at endgame entry; higher is better): ",
        ),
        ("net_flag_rate", "- Net Flag Rate (flag wins − flag losses; higher is better): "),
    )
    for metric_key, label in aggregates:
        ranked_metric = tc_stats.metrics.get(metric_key)
        # RankedMetricOut.value is NOT floor-gated (a time-pressure score gap exists from
        # one pressured game per side), so falling back to it for a below_floor/pending
        # cell narrated values built from a handful of games. Only cells that cleared
        # their floor may fall back to the raw value.
        fallback = (
            ranked_metric.value
            if ranked_metric is not None and ranked_metric.status in _FLOOR_CLEARED_STATUSES
            else None
        )
        line = _aggregate_value_or_pctl(label, percentiles.get(f"{metric_key}:{tc}"), fallback)
        if line is not None:
            lines.append(line)
    lines.append("")
    return lines


# The per-span Score Gap is emitted directly by
# insights_service._endgame_type_class_findings as a real per-(class × TC)
# SubsectionFinding under the `endgame_type_<tc>` subsections (banded via
# assign_per_class_tc_zone), so the renderer does not synthesize it from the
# pooled `type_categories`.


# -- Enrichments: mechanical signals precomputed for the LLM --


def _newest_bucket_date(findings: list[SubsectionFinding]) -> datetime.date | None:
    """Return the most recent bucket date across every series in the payload."""
    newest: datetime.date | None = None
    for f in findings:
        if f.series is None:
            continue
        for pt in f.series:
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if newest is None or d > newest:
                newest = d
    return newest


def _cap_all_time_points(points: list[TimePoint]) -> list[TimePoint]:
    """Cap an `all_time` series at the last `_ALL_TIME_MAX_POINTS` buckets.

    Shared by `_all_time_window_bounds` and `_retained_series_for_summary` so
    the payload-summary window text and the actually-rendered series/summary
    data always agree on which buckets survived the cap.
    """
    return points[-_ALL_TIME_MAX_POINTS:]


def _all_time_window_bounds(
    findings: list[SubsectionFinding],
) -> tuple[datetime.date, datetime.date] | None:
    """Return (oldest, newest) bucket dates for all_time series after the all-time point cap.

    Walks every all_time series, applies the same MIN_BUCKET_N filter and
    _ALL_TIME_MAX_POINTS tail-cap that `_retained_series_for_summary` applies,
    and tracks the min/max bucket dates across the retained set. Used by the
    `## Payload summary` block to spell out the effective time window the LLM
    is reading.
    """
    oldest: datetime.date | None = None
    newest: datetime.date | None = None
    for f in findings:
        if f.series is None or f.window != "all_time":
            continue
        retained = _cap_all_time_points([pt for pt in f.series if pt.n >= MIN_BUCKET_N])
        for pt in retained:
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if oldest is None or d < oldest:
                oldest = d
            if newest is None or d > newest:
                newest = d
    if oldest is None or newest is None:
        return None
    return oldest, newest


def _stale_marker(series: list[TimePoint] | None, newest_payload_date: datetime.date | None) -> str:
    """Return 'stale: last YYYY-MM (N mo ago)' or '' if the series is live.

    Consumed inline in [summary] window lines — a short, bracket-compatible
    form. The threshold is _STALE_SERIES_THRESHOLD_DAYS.
    """
    if not series or newest_payload_date is None:
        return ""
    try:
        last_date = datetime.date.fromisoformat(series[-1].bucket_start)
    except ValueError:
        return ""
    delta_days = (newest_payload_date - last_date).days
    if delta_days < _STALE_SERIES_THRESHOLD_DAYS:
        return ""
    months = delta_days // 30
    return f"stale: last {last_date.strftime('%Y-%m')} ({months} mo ago)"


def _trend_info(
    metric_id: str, points: list[TimePoint]
) -> tuple[str, float, float, int, bool] | None:
    """Return (direction, mean_scaled, std_scaled, n_total, within_noise) or None.

    Uses the full retained series (after the MIN_BUCKET_N, all-time-cutoff and
    _ALL_TIME_MAX_POINTS filtering). direction is
    computed over the last 4 buckets (latest vs mean of prior 3) — flat when
    |latest - prior-mean| < _TREND_FLAT_THRESHOLD, otherwise improving /
    regressing. std is the stddev across all retained points (0.0 when fewer
    than 2 points). within_noise is true when the last-4 shift is
    below the metric's noise cap even if direction is not flat. Returns None
    when fewer than _TREND_MIN_POINTS buckets remain — caller renders no
    trend field.
    """
    if len(points) < _TREND_MIN_POINTS:
        return None
    scale = _scale_for_metric(metric_id)
    values = [pt.value * scale for pt in points]
    latest = values[-1]
    prior_values = values[-4:-1]
    prior_mean = sum(prior_values) / len(prior_values)
    diff = latest - prior_mean
    if abs(diff) < _TREND_FLAT_THRESHOLD:
        direction = "flat"
    elif diff > 0:
        direction = "improving"
    else:
        direction = "regressing"
    series_mean = sum(values) / len(values)
    series_std = (
        (sum((v - series_mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5
        if len(values) >= 2
        else 0.0
    )
    n_total = sum(pt.n for pt in points)
    noise_cap = (
        _DELTA_WITHIN_NOISE_ELO if metric_id == "endgame_elo_gap" else _DELTA_WITHIN_NOISE_SHIFT
    )
    within_noise = direction != "flat" and abs(diff) < noise_cap
    return direction, series_mean, series_std, n_total, within_noise


def _proximity_hint(metric_id: str, value_scaled: float, dimension: dict[str, str] | None) -> str:
    """Return ' [near edge]' when the value sits within a proximity threshold of a zone boundary.

    Percent-scale metrics use _PROXIMITY_PCT_THRESHOLD; endgame_elo_gap uses
    _PROXIMITY_ELO_THRESHOLD. Returns '' for unknown metrics or when the value
    is comfortably inside one zone.
    """
    spec: ZoneSpec | None = None
    bucket = dimension.get("bucket") if dimension else None
    # metrics_elo findings dispatch their proximity band per-TC
    # (TC_METRIC_BANDS) so the `[near edge]` hint matches the per-TC gauge edge.
    time_control = dimension.get("time_control") if dimension else None
    bucketed = cast("dict[str, dict[str, ZoneSpec]]", dict(BUCKETED_ZONE_REGISTRY))
    scalar = cast("dict[str, ZoneSpec]", dict(ZONE_REGISTRY))
    if (
        metric_id in _TC_BAND_METRICS
        and time_control is not None
        and time_control in TC_METRIC_BANDS
    ):
        spec = tc_metric_zone_spec(
            cast(TcBandMetricId, metric_id), cast(TimeControlBucket, time_control)
        )
    elif metric_id in bucketed and bucket is not None:
        spec = bucketed[metric_id].get(bucket)
    elif metric_id in scalar:
        spec = scalar[metric_id]
    if spec is None:
        return ""
    scale = _scale_for_metric(metric_id)
    lo = spec.typical_lower * scale
    hi = spec.typical_upper * scale
    if metric_id == "endgame_elo_gap":
        threshold = _PROXIMITY_ELO_THRESHOLD
    elif metric_id == "entry_eval_pawns":
        threshold = _PROXIMITY_PAWN_THRESHOLD
    else:
        threshold = _PROXIMITY_PCT_THRESHOLD
    if abs(value_scaled - lo) <= threshold or abs(value_scaled - hi) <= threshold:
        return " [near edge]"
    return ""


def _weakest_type_tag(sorted_cats: Sequence[object]) -> str:
    """Emit a weakest-type tag across the per-type WDL chart.

    Three outcomes across the eligible types (>= _WEAKEST_TYPE_MIN_GAMES):

    1. Clear single winner — the lowest score_pct is separated from #2 by
       >= _WEAKEST_TYPE_MIN_SEPARATION. Emits `[weakest-type] <class> ...`.
    2. Tied-weakest pair — top 2 are within the separation threshold BUT
       the #3 type (when present) is separated from #2 by >= the threshold,
       so the two lowest stand out together. Emits
       `[weakest-types-tied] <a>, <b> score_pct=X, Y — next=<c> score_pct=Z`
       Releases pawn-ending recommendations the same way a clear
       `[weakest-type] pawn` would.
    3. No clear bottom — no tag emitted.
    """
    # EndgameCategoryStats is imported lazily to keep the helper cheap when no
    # type chart is emitted. Using `object` in the signature and casting here
    # keeps ty happy without a top-level import.
    from app.schemas.endgames import EndgameCategoryStats

    eligible: list[tuple[float, str]] = []
    for cat in sorted_cats:
        c = cast(EndgameCategoryStats, cat)
        if c.total < _WEAKEST_TYPE_MIN_GAMES:
            continue
        score_pct = (c.wins + 0.5 * c.draws) / c.total * 100.0
        eligible.append((score_pct, c.endgame_class))
    if len(eligible) < 2:
        return ""
    eligible.sort(key=lambda t: t[0])
    weakest_score, weakest_class = eligible[0]
    next_score, next_class = eligible[1]
    if next_score - weakest_score >= _WEAKEST_TYPE_MIN_SEPARATION:
        return (
            f"[weakest-type] {weakest_class} score_pct={weakest_score:.0f}, "
            f"next={next_class} score_pct={next_score:.0f}"
        )
    # Tied-weakest: require a #3 type that is clearly separated from #2,
    # else the whole field is bunched and no "weakest" story is defensible.
    if len(eligible) < 3:
        return ""
    third_score, third_class = eligible[2]
    if third_score - next_score < _WEAKEST_TYPE_MIN_SEPARATION:
        return ""
    return (
        f"[weakest-types-tied] {weakest_class}, {next_class} "
        f"score_pct={weakest_score:.0f}, {next_score:.0f} — "
        f"next={third_class} score_pct={third_score:.0f}"
    )


def _recovery_pattern_tag(members: list[SubsectionFinding], tc: str) -> str:
    """Emit a recovery-pattern hint when Recovery is weak across many types in one TC.

    Scoped per-TC: scans one `endgame_type_<tc>`
    subsection's members for `recovery_save_pct` with zone=weak. When
    ≥ _RECOVERY_PATTERN_MIN_WEAK_TYPES of the four visible types qualify, emits a
    hint so the LLM frames Recovery as a consistent pattern within that time
    control rather than a per-type crisis in each bullet.

    `members` spans both windows (all_time + last_3mo). Count all_time only —
    otherwise a class weak in both windows is counted twice, inflating the tally
    past the four visible types and falsely tripping the "consistent pattern"
    hint (e.g. 2 weak classes × 2 windows == "4 of 4").
    """
    weak_types: list[str] = []
    for f in members:
        if f.window != "all_time":
            continue
        if f.metric != "recovery_save_pct" or f.dimension is None:
            continue
        klass = f.dimension.get("endgame_class")
        if klass is None or klass == "pawnless":
            continue
        if f.zone == "weak":
            weak_types.append(klass)
    if len(weak_types) < _RECOVERY_PATTERN_MIN_WEAK_TYPES:
        return ""
    return (
        f"[recovery-pattern {tc}] weak across {len(weak_types)} of 4 types in {tc} — "
        "consistent defensive pattern, frame as one story not per-type crisis"
    )


def _asymmetry_lines(members: list[SubsectionFinding], tc: str) -> list[str]:
    """Detect per-type Conversion/Recovery zone splits (one strong + one weak) in one TC.

    Scoped per-TC: groups one `endgame_type_<tc>`
    subsection's members by endgame class. When the two metrics sit in opposing
    zones, emits a comment the LLM should lead with for that type — the "you
    close winning pawn endgames but bleed losing ones" story is easy to miss if
    both bullets are narrated flat. Pawnless never reaches here (excluded upstream).

    `members` spans both windows; restrict to all_time so the strong/weak split
    reflects the full-history baseline (not the smaller last_3mo sample, which
    would otherwise overwrite all_time in the per-class dicts below).
    """
    conv: dict[str, SubsectionFinding] = {}
    rec: dict[str, SubsectionFinding] = {}
    for f in members:
        if f.window != "all_time":
            continue
        if f.dimension is None:
            continue
        klass = f.dimension.get("endgame_class")
        if klass is None or klass == "pawnless":
            continue
        if f.metric == "conversion_win_pct":
            conv[klass] = f
        elif f.metric == "recovery_save_pct":
            rec[klass] = f
    lines: list[str] = []
    for klass in sorted(conv):
        c = conv.get(klass)
        r = rec.get(klass)
        if c is None or r is None:
            continue
        if {c.zone, r.zone} != {"strong", "weak"}:
            continue
        c_val = c.value * 100.0
        r_val = r.value * 100.0
        if c.zone == "strong":
            story = "closes winning endgames but bleeds losing ones"
        else:
            story = "defends losing endgames but mishandles winning ones"
        lines.append(
            f"[asymmetry type={klass} tc={tc}] conversion={c_val:.0f} {c.zone}, "
            f"recovery={r_val:.0f} {r.zone} — {story}"
        )
    return lines


def _dim_key_for_finding(f: SubsectionFinding) -> str:
    """Return the canonical dim-key string used to group findings across windows."""
    if f.dimension is None:
        return ""
    return ", ".join(f"{k}={v}" for k, v in sorted(f.dimension.items()))


# (metric, subsection_id, dim_key): the identity of ONE series across its two windows.
SeriesKey = tuple[str, str, str]


def _series_key(f: SubsectionFinding) -> SeriesKey:
    """Return the full series identity used by the window filters.

    score_timeline is per time control, so (metric, subsection_id) is shared by up
    to four TCs. Keying the window filters on that pair would let one TC's series
    state trim or suppress another TC's series (a new rapid with only recent games
    would lose its last_3mo series because blitz had an all_time one). The dim_key
    separates the combos.
    """
    return (f.metric, f.subsection_id, _dim_key_for_finding(f))


def _within_noise_shift(
    metric: str,
    all_time: SubsectionFinding,
    last_3mo: SubsectionFinding,
    shift: float,
) -> bool:
    """Shift is within-noise when it's below the metric cap AND the last_3mo window is much smaller."""
    if metric == "endgame_elo_gap":
        noise_cap = _DELTA_WITHIN_NOISE_ELO
    elif metric == "entry_eval_pawns":
        # 0.05 pawns is the within-noise cap for entry_eval_pawns
        # (matches the proximity threshold; ~5 cp is well inside the calibrated ±0.60 band).
        noise_cap = 0.05
    else:
        noise_cap = _DELTA_WITHIN_NOISE_SHIFT
    sample_mismatch = (
        all_time.sample_size > 0
        and (last_3mo.sample_size / all_time.sample_size) < _DELTA_SMALL_SAMPLE_RATIO
    )
    return abs(shift) < noise_cap and sample_mismatch


def _series_granularity(finding: SubsectionFinding) -> str:
    """Weekly for last_3mo; monthly for all_time.

    Exception: score_timeline is always weekly (ISO-week is the
    natural grain of the underlying `compute_score_gap_timeline`; the two-line
    chart reads weekly points directly and the insights series is built without
    monthly resampling — see `_findings_score_timeline`).
    """
    if finding.subsection_id == "score_timeline":
        return "weekly"
    return "weekly" if finding.window == "last_3mo" else "monthly"


def _build_pctl_token(rec: MetricPercentileRecord | None) -> str:
    """Build the pctl= token string from an enriched MetricPercentileRecord.

    The enriched format is
    `pctl=N (vs ~A-rated {tc} peers | n_games=M | value=V)`.
    Each context element is appended only when present so short-history users
    (no anchor or sparse n_games) still get a valid pctl= token.
    """
    if rec is None:
        return ""
    parts: list[str] = []
    if rec.anchor is not None and rec.tc is not None:
        parts.append(f"vs ~{rec.anchor}-rated {rec.tc} peers")
    elif rec.anchor is not None:
        parts.append(f"vs ~{rec.anchor}-rated peers")
    if rec.n_games is not None:
        parts.append(f"n_games={rec.n_games}")
    if rec.value is not None:
        parts.append(f"value={rec.value:+.0f}")
    token = f"pctl={rec.percentile:.0f}"
    if parts:
        token += f" ({' | '.join(parts)})"
    return token


def _summary_window_line(
    *,
    window: str,
    finding: SubsectionFinding,
    series_points: list[TimePoint] | None,
    stale_suffix: str,
    pctl_record: MetricPercentileRecord | None = None,
) -> str:
    """Render one `  <window>: ...` line inside a [summary] block.

    Pulls mean / zone / quality from the scalar finding, and (when series
    points are provided and qualifying) buckets / granularity / trend / std
    from the series. Appends `stale: ...` and `[near edge]` suffixes when
    applicable. All numbers on the UI 0-100 scale (or Elo points).

    Optional pctl_record appends a pctl= token after
    quality= when present. pctl= is metadata only; it never gates emission.
    Enriched token format includes anchor, n_games, value.
    """
    scale = _scale_for_metric(finding.metric)
    precision = _precision_for_metric(finding.metric)
    value_scaled = finding.value * scale
    bounds = _format_zone_bounds(finding.metric, finding.dimension)
    zone_part = f"zone={finding.zone}"
    if bounds:
        zone_part += f" {bounds}"

    # Enriched pctl= token carries anchor + n_games + value.
    pctl_part = _build_pctl_token(pctl_record)

    parts: list[str] = [f"mean={value_scaled:+.{precision}f}", f"n={finding.sample_size}"]
    if series_points and len(series_points) >= _TREND_MIN_POINTS:
        info = _trend_info(finding.metric, series_points)
        if info is not None:
            direction, _series_mean, series_std, _n_total, within_noise = info
            granularity = _series_granularity(finding)
            parts.append(f"buckets={len(series_points)} ({granularity})")
            parts.append(zone_part)
            parts.append(f"quality={finding.sample_quality}")
            parts.append(f"trend={direction}")
            parts.append(f"std={series_std:.{precision}f}")
            if within_noise:
                parts.append("within-noise")
            if pctl_part:
                parts.append(pctl_part)
            if stale_suffix:
                parts.append(stale_suffix)
            near = _proximity_hint(finding.metric, value_scaled, finding.dimension).strip()
            suffix = f" {near}" if near else ""
            return f"  {window}: " + ", ".join(parts) + suffix

    # Scalar (or too-short series) fallback.
    parts.append(zone_part)
    parts.append(f"quality={finding.sample_quality}")
    if pctl_part:
        parts.append(pctl_part)
    if stale_suffix:
        parts.append(stale_suffix)
    near = _proximity_hint(finding.metric, value_scaled, finding.dimension).strip()
    suffix = f" {near}" if near else ""
    return f"  {window}: " + ", ".join(parts) + suffix


def _summary_shift_line(
    metric: str,
    all_time: SubsectionFinding,
    last_3mo: SubsectionFinding,
) -> str:
    """Render `  shift=<Z>[, within-noise]` closing a [summary] block with paired windows."""
    scale = _scale_for_metric(metric)
    precision = _precision_for_metric(metric)
    shift = (last_3mo.value - all_time.value) * scale
    line = f"  shift={shift:+.{precision}f}"
    if _within_noise_shift(metric, all_time, last_3mo, shift):
        line += ", within-noise"
    return line


def _endgame_elo_per_bucket(points: list[TimePoint] | None) -> list[tuple[float, int]]:
    """Return [(endgame_elo_value, n), ...] derived from endgame_elo_gap series points.

    Endgame ELO per bucket = actual_elo + gap. The gap metric is non-fractional
    (scale=1.0), so `pt.value` is already in Elo units. Points missing
    `actual_elo` are skipped — the gap series carries it for endgame_elo_gap
    only (see _render_series_block).
    """
    out: list[tuple[float, int]] = []
    if not points:
        return out
    for pt in points:
        if pt.actual_elo is None:
            continue
        out.append((pt.actual_elo + pt.value, pt.n))
    return out


def _non_endgame_elo_per_bucket(points: list[TimePoint] | None) -> list[tuple[float, int]]:
    """Return [(non_endgame_elo_value, n), ...] from endgame_elo_gap series points.

    Points missing `non_endgame_elo` are skipped (only endgame_elo_timeline
    populates this field; see TimePoint docstring).

    Companion to `_endgame_elo_per_bucket`; reads pt.non_endgame_elo
    instead of deriving endgame_elo from pt.actual_elo + pt.value.
    """
    out: list[tuple[float, int]] = []
    if not points:
        return out
    for pt in points:
        if pt.non_endgame_elo is None:
            continue
        out.append((float(pt.non_endgame_elo), pt.n))
    return out


def _elo_variant_window_line(
    window_label: str,
    finding: SubsectionFinding | None,
    series: list[TimePoint] | None,
    *,
    per_bucket: Callable[[list[TimePoint] | None], list[tuple[float, int]]],
    stale_markers: dict[int, str],
) -> tuple[str | None, float | None]:
    """Return (rendered_line, weighted_mean) or (None, None) if no usable data.

    One window's line ("all_time" or "last_3mo") of an elo-variant summary
    block. Extracted to its own module-level function (not a closure inside
    `_render_elo_variant_summary_block`) so the function-size / complexity checks
    score it independently of the caller.
    """
    values = per_bucket(series)
    if not values:
        return None, None
    total_n = sum(n for _, n in values)
    if total_n == 0:
        return None, None
    weighted_mean = sum(v * n for v, n in values) / total_n
    elos = [v for v, _ in values]
    elo_mean = sum(elos) / len(elos)
    std = (
        (sum((v - elo_mean) ** 2 for v in elos) / (len(elos) - 1)) ** 0.5 if len(elos) >= 2 else 0.0
    )
    granularity = "weekly" if window_label == "last_3mo" else "monthly"
    parts: list[str] = [
        f"mean={weighted_mean:+.0f} Elo",
        f"n={finding.sample_size if finding is not None else total_n}",
        f"buckets={len(values)} ({granularity})",
    ]
    within_noise = False
    if len(elos) >= _TREND_MIN_POINTS:
        latest = elos[-1]
        prior_mean = sum(elos[-4:-1]) / 3
        diff = latest - prior_mean
        if abs(diff) < _TREND_FLAT_THRESHOLD_ELO:
            direction = "flat"
        elif diff > 0:
            direction = "improving"
        else:
            direction = "regressing"
        parts.append(f"trend={direction}")
        within_noise = direction != "flat" and abs(diff) < _DELTA_WITHIN_NOISE_ELO
    parts.append(f"std={std:.0f}")
    if within_noise:
        parts.append("within-noise")
    if finding is not None:
        stale = stale_markers.get(id(finding), "")
        if stale:
            parts.append(stale)
    return f"  {window_label}: " + ", ".join(parts), weighted_mean


def _render_elo_variant_summary_block(
    *,
    label: str,
    per_bucket: Callable[[list[TimePoint] | None], list[tuple[float, int]]],
    dim_key: str,
    all_time_finding: SubsectionFinding | None,
    last_3mo_finding: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
) -> list[str]:
    """Emit `[summary {label} | dim]` derived from an endgame_elo_gap series.

    Shared body for `_render_endgame_elo_summary_block` (`label="endgame_elo"`,
    `per_bucket=_endgame_elo_per_bucket`) and `_render_non_endgame_elo_summary_block`
    (`label="non_endgame_elo"`, `per_bucket=_non_endgame_elo_per_bucket`) — the
    two were byte-identical except for the header label and which per-bucket
    extractor they called. No zone / quality fields on either variant — the
    paired `[summary endgame_elo_gap]` block (rendered immediately after)
    carries the zone interpretation.
    """
    header = f"[summary {label}"
    if dim_key:
        header += f" | {dim_key}"
    header += "]"

    at_line, at_mean = _elo_variant_window_line(
        "all_time",
        all_time_finding,
        all_time_series,
        per_bucket=per_bucket,
        stale_markers=stale_markers,
    )
    lm_line, lm_mean = _elo_variant_window_line(
        "last_3mo",
        last_3mo_finding,
        last_3mo_series,
        per_bucket=per_bucket,
        stale_markers=stale_markers,
    )

    if at_line is None and lm_line is None:
        return []

    lines: list[str] = [header]
    if at_line is not None:
        lines.append(at_line)
    if lm_line is not None:
        lines.append(lm_line)
    elif at_line is not None:
        lines.append("  last_3mo: no data")

    if (
        at_line is not None
        and lm_line is not None
        and at_mean is not None
        and lm_mean is not None
        and all_time_finding is not None
        and last_3mo_finding is not None
    ):
        shift = lm_mean - at_mean
        sample_mismatch = (
            all_time_finding.sample_size > 0
            and (last_3mo_finding.sample_size / all_time_finding.sample_size)
            < _DELTA_SMALL_SAMPLE_RATIO
        )
        shift_line = f"  shift={shift:+.0f} Elo"
        if abs(shift) < _DELTA_WITHIN_NOISE_ELO and sample_mismatch:
            shift_line += ", within-noise"
        lines.append(shift_line)

    return lines


def _render_endgame_elo_summary_block(
    *,
    dim_key: str,
    all_time_finding: SubsectionFinding | None,
    last_3mo_finding: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
) -> list[str]:
    """Emit `[summary endgame_elo | dim]` derived from the endgame_elo_gap series.

    The chart's headline value is Endgame ELO (absolute Elo, score-gap-adjusted)
    not the gap. We derive a per-window aggregate from the same retained series
    points used by the gap summary so the LLM can cite the chart number directly
    without doing arithmetic. Thin wrapper over `_render_elo_variant_summary_block`
    — kept as its own named function because `monkeypatch`/test imports and the
    `_render_subsection_block` call site both pin this exact name.
    """
    return _render_elo_variant_summary_block(
        label="endgame_elo",
        per_bucket=_endgame_elo_per_bucket,
        dim_key=dim_key,
        all_time_finding=all_time_finding,
        last_3mo_finding=last_3mo_finding,
        all_time_series=all_time_series,
        last_3mo_series=last_3mo_series,
        stale_markers=stale_markers,
    )


def _render_non_endgame_elo_summary_block(
    *,
    dim_key: str,
    all_time_finding: SubsectionFinding | None,
    last_3mo_finding: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
) -> list[str]:
    """Emit `[summary non_endgame_elo | dim]` from the endgame_elo_gap series.

    Analogous to `_render_endgame_elo_summary_block` but reads pt.non_endgame_elo
    directly (Actual ELO stretched by the non-endgame score; see
    endgame_service._endgame_elo_logistic).
    Thin wrapper over `_render_elo_variant_summary_block` — kept as its own
    named function for the same reason as `_render_endgame_elo_summary_block`.

    One of THREE summary blocks per combo in the endgame_elo_timeline subsection.
    """
    return _render_elo_variant_summary_block(
        label="non_endgame_elo",
        per_bucket=_non_endgame_elo_per_bucket,
        dim_key=dim_key,
        all_time_finding=all_time_finding,
        last_3mo_finding=last_3mo_finding,
        all_time_series=all_time_series,
        last_3mo_series=last_3mo_series,
        stale_markers=stale_markers,
    )


def _lookup_pctl_record(
    metric: str,
    dim_key: str,
    per_tc_metric_percentiles: dict[str, "MetricPercentileRecord"] | None,
) -> "MetricPercentileRecord | None":
    """Look up a MetricPercentileRecord for a (metric, dim_key) pair.

    Every record is per TC (no page-level weighted record exists),
    keyed as "{metric}:{tc}". The dim_key typically encodes the TC as
    "time_control=blitz" — we parse out the tc part.
    This is metadata only and never gates emission.

    Only the per-TC Endgame Metrics subsections carry
    percentiles. The per-(class × TC) Endgame Type findings share the
    conversion_win_pct / recovery_save_pct metric names AND a time_control
    dimension, so without this guard a class-scoped finding (e.g. rook
    conversion in blitz) would resolve to the TC-aggregate percentile —
    attaching a misleading number whose value also contradicts the finding's
    own class-specific mean. Type Breakdown has no percentiles by design, so
    skip the per-TC lookup whenever the finding is class-scoped.
    """
    if "endgame_class=" in dim_key:
        # Class-scoped finding (Endgame Type Breakdown) — no percentile by design.
        return None
    if per_tc_metric_percentiles and dim_key:
        # Extract tc from dim_key (format is "bucket=X, time_control=Y" or
        # "platform=X, time_control=Y" or simply "time_control=Y").
        tc: str | None = None
        for part in dim_key.split(","):
            stripped = part.strip()
            if stripped.startswith("time_control="):
                tc = stripped[len("time_control=") :]
                break
        if tc is not None:
            key = f"{metric}:{tc}"
            if key in per_tc_metric_percentiles:
                return per_tc_metric_percentiles[key]
    return None


def _render_summary_block(
    metric: str,
    dim_key: str,
    *,
    all_time: SubsectionFinding | None,
    last_3mo: SubsectionFinding | None,
    all_time_series: list[TimePoint] | None,
    last_3mo_series: list[TimePoint] | None,
    stale_markers: dict[int, str],
    per_tc_metric_percentiles: dict[str, "MetricPercentileRecord"] | None = None,
    cohort_anchors: "dict[str, RatingAnchorContext] | None" = None,
) -> list[str]:
    """Emit `[summary <metric>[ | dim]]` with all_time / last_3mo / shift lines.

    The block's format is intentionally consistent across scalar, timeseries,
    and per-dim metrics so the system prompt only needs to document one
    shape. `no data` stands in on the last_3mo line when only the all_time
    window has a finding (keeps the paired-line visual consistent).

    Optional per_tc_metric_percentiles thread pctl= annotations
    into the all_time and last_3mo window lines. Percentile is
    metadata only and never gates emission.
    Enriched MetricPercentileRecord carries anchor +
    n_games + value; cohort_anchors is no longer needed for anchor resolution
    (the record already contains the resolved anchor). Kept in the signature
    for backwards compat but no longer used for framing.
    """
    header = f"[summary {metric}"
    if dim_key:
        header += f" | {dim_key}"
    header += "]"
    lines: list[str] = [header]

    # Resolve the enriched percentile record from the per-TC
    # dict. pctl is metadata only.
    pctl_record = _lookup_pctl_record(metric, dim_key, per_tc_metric_percentiles)

    if all_time is not None:
        stale = stale_markers.get(id(all_time), "")
        lines.append(
            _summary_window_line(
                window="all_time",
                finding=all_time,
                series_points=all_time_series,
                stale_suffix=stale,
                pctl_record=pctl_record,
            )
        )
    if last_3mo is not None:
        stale = stale_markers.get(id(last_3mo), "")
        lines.append(
            _summary_window_line(
                window="last_3mo",
                finding=last_3mo,
                series_points=last_3mo_series,
                stale_suffix=stale,
                pctl_record=pctl_record,
            )
        )
    elif all_time is not None:
        lines.append("  last_3mo: no data")

    if all_time is not None and last_3mo is not None:
        lines.append(_summary_shift_line(metric, all_time, last_3mo))
    return lines


def _count_activity_gaps(findings: list[SubsectionFinding]) -> int:
    """Count >90-day gaps between consecutive retained bucket pairs across all series."""
    count = 0
    for f in findings:
        if f.series is None:
            continue
        prev: datetime.date | None = None
        for pt in f.series:
            if pt.n < MIN_BUCKET_N:
                continue
            try:
                d = datetime.date.fromisoformat(pt.bucket_start)
            except ValueError:
                continue
            if prev is not None and (d - prev).days > _ACTIVITY_GAP_DAYS:
                count += 1
            prev = d
    return count


def _payload_summary_lines(
    findings: EndgameTabFindings,
    *,
    newest_date: datetime.date | None,
    stale_series_count: int,
    activity_gap_count: int,
    all_time_window: tuple[datetime.date, datetime.date] | None,
) -> list[str]:
    """Compact summary prepended to the prompt so macro context is always visible.

    Includes an `All-time series window: ... → ...` line so the LLM cannot
    overclaim a long-term trajectory beyond the actual cap.
    """
    lines: list[str] = ["## Payload summary"]
    # Games in the ranked sample, summed over the per-TC ranked payload.
    total_games = sum(t.ranked_games for t in findings.ranked_tcs)
    if total_games > 0:
        lines.append(f"- Total games in scope: {total_games}")
    if newest_date is not None:
        lines.append(f"- Newest bucket across all series: {newest_date.isoformat()}")
    if all_time_window is not None:
        oldest, newest = all_time_window
        lines.append(
            f"- All-time series window: {oldest.strftime('%Y-%m')} → "
            f"{newest.strftime('%Y-%m')} (capped at {_ALL_TIME_MAX_POINTS} "
            "monthly buckets per series)"
        )
    if activity_gap_count > 0:
        lines.append(
            f"- Activity gaps (>{_ACTIVITY_GAP_DAYS}d) across all series: {activity_gap_count}"
        )
    if stale_series_count > 0:
        lines.append(
            f"- Stale series (>{_STALE_SERIES_THRESHOLD_DAYS}d behind newest): {stale_series_count}"
        )
    if len(lines) == 1:  # only the header line
        return []
    lines.append("")
    return lines


# UI-ordered section layout. Each entry is (section_id, ordered blocks
# in UI top-to-bottom order). A block is ("subsection", id) or ("chart", id).
# The `section_id` strings match the `SectionId` enum on EndgameInsightsReport
# so the LLM can treat each `## Section:` header as the cue for which
# SectionInsight it is writing.
_SECTION_LAYOUT: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "overall",
        [
            ("chart", "overall_wdl"),
            # endgame_start_vs_end leads with the two score cards (endgame_score +
            # non_endgame_score), and the two gaps live in the dedicated `score_gap`
            # subsection, mirroring the UI's "Games with/without Endgame" cards and
            # "Endgame Score Differences" card.
            ("subsection", "endgame_start_vs_end"),
            ("subsection", "score_gap"),
            ("subsection", "score_timeline"),
            # endgame_elo_timeline sits in `overall` next to the Endgame Score Gap
            # timeline (its input series). The chart's UI position mirrors this:
            # it renders directly below the Endgame Score Gap over Time chart in
            # the Endgame Overall Performance section.
            ("subsection", "endgame_elo_timeline"),
        ],
    ),
    (
        "metrics_elo",
        [
            # Each eligible time control renders its own subsection mirroring the
            # UI's per-TC Endgame Metrics cards (bullet → blitz → rapid →
            # classical). Subsections with no qualifying card (TC below
            # MIN_GAMES_PER_TC_CARD) are skipped by the assembly loop.
            ("subsection", "endgame_metrics_bullet"),
            ("subsection", "endgame_metrics_blitz"),
            ("subsection", "endgame_metrics_rapid"),
            ("subsection", "endgame_metrics_classical"),
        ],
    ),
    (
        "time_pressure",
        [
            # Chart-only section: the per-TC block carries the quintile table plus
            # Clock Gap / Net Flag Rate percentiles; the assembly loop emits the
            # section header whenever the block has content.
            ("chart", "time_pressure_score_gap_by_time"),
        ],
    ),
    (
        "type_breakdown",
        [
            # Each eligible time control renders its own subsection mirroring the
            # UI's per-TC collapsible Endgame Type cards: a WDL table (built from
            # type_categories_by_tc) leads the subsection, followed by the per-class
            # Conversion / Recovery / Score-Gap [summary] blocks. Subsections with
            # no qualifying card (TC below MIN_GAMES_PER_TC_CARD) are skipped by the
            # assembly loop.
            ("subsection", "endgame_type_bullet"),
            ("subsection", "endgame_type_blitz"),
            ("subsection", "endgame_type_rapid"),
            ("subsection", "endgame_type_classical"),
        ],
    ),
]


# subsection_id → TC bucket for the per-TC Endgame Type subsections.
# Used by the renderer to look up the WDL table + scope the per-TC asymmetry /
# recovery-pattern hints.
_TYPE_SUBSECTION_TO_TC: dict[str, str] = {
    "endgame_type_bullet": "bullet",
    "endgame_type_blitz": "blitz",
    "endgame_type_rapid": "rapid",
    "endgame_type_classical": "classical",
}


def _drop_points_covered_by_last_3mo(
    points: list[TimePoint], *, drop_last_90_days: bool, all_time_cutoff: str
) -> list[TimePoint]:
    """For an `all_time` series, drop points within the last 90 days when
    a matching `last_3mo` series exists for the same series key (metric,
    subsection, dimension).

    `drop_last_90_days` is pre-computed by the caller (True only when this is
    an `all_time`-window finding whose series key also has a
    `last_3mo` finding) so this helper stays a pure points-in, points-out
    filter rather than re-deriving that condition from a `SubsectionFinding`.
    """
    if not drop_last_90_days:
        return points
    return [pt for pt in points if pt.bucket_start < all_time_cutoff]


def _retained_series_for_summary(
    finding: SubsectionFinding,
    *,
    last_3mo_pairs: set[SeriesKey],
    all_time_cutoff: str,
) -> list[TimePoint] | None:
    """Return the retained series points for a timeline finding, or None.

    Applies the same thin-bucket drop, last_3mo-overlap drop and all-time point
    cap used for series emission, so the [summary] block's buckets / trend / std
    all describe the exact window the LLM sees in the [series ...] block below
    it. Returns None for non-timeline subsections (scalar findings carry no
    series semantics).
    """
    if finding.series is None or finding.subsection_id not in _TIMELINE_SUBSECTION_IDS:
        return None
    points = [pt for pt in finding.series if pt.n >= MIN_BUCKET_N]  # drop thin buckets
    is_all_time = finding.window == "all_time"
    points = _drop_points_covered_by_last_3mo(
        points,
        drop_last_90_days=is_all_time and _series_key(finding) in last_3mo_pairs,
        all_time_cutoff=all_time_cutoff,
    )
    if is_all_time:
        points = _cap_all_time_points(points)
    return points


def _activity_gap_marker(
    prev_date: datetime.date | None,
    curr_date: datetime.date,
    prev_bucket_start: str | None,
    curr_bucket_start: str,
) -> str | None:
    """Return an `[activity-gap] ...` marker line for a >90-day gap between
    two consecutive retained series points, or None when there is no gap
    (or no prior point to compare against).
    """
    if (
        prev_date is not None
        and prev_bucket_start is not None
        and (curr_date - prev_date).days > _ACTIVITY_GAP_DAYS
    ):
        return f"[activity-gap] {prev_bucket_start} → {curr_bucket_start}"
    return None


def _render_series_block(finding: SubsectionFinding, points: list[TimePoint]) -> list[str]:
    """Render `[series metric, window, granularity[, dim_key]]` + raw points + `[activity-gap]` markers.

    When a finding carries a dimension (e.g. `{"time_control": "blitz"}`
    or `{"platform": "chess.com", "time_control": "blitz"}`), the series
    header gets a trailing dim_key suffix so two findings that share the
    same (metric, window, granularity) but different dims each get their
    own uniquely-labelled series block. This matches the grouping the
    `_dim_key_for_finding` helper already produces for summary blocks.

    When every point carries the same
    `n` — as happens for trailing-window series (e.g. score_timeline's
    rolling 100-game window) — the repetitive `(n=<N>)` suffix is noise.
    Emit a single `[n=<N> for every point]` disclosure line right after
    the series header and omit the suffix from each bucket line. The
    endgame_elo_gap variant (which also carries per-point `elo=`) always
    keeps the per-point `(n=<N>)` suffix because its `elo=` field can
    still vary per bucket — the disclosure shortcut would lose signal.
    """
    granularity = _series_granularity(finding)
    header = f"[series {finding.metric}, {finding.window}, {granularity}"
    dim_key = _dim_key_for_finding(finding)
    if dim_key:
        header += f", {dim_key}"
    header += "]"
    lines = [header]
    series_scale = _scale_for_metric(finding.metric)
    emit_elo = finding.metric == "endgame_elo_gap"
    # Constant-n suppression: only applies when every point
    # shares the same `n` AND this is NOT the endgame_elo_gap variant (whose
    # per-point `elo=` field is the reason the full per-point line exists).
    ns = [pt.n for pt in points]
    n_is_constant = bool(ns) and not emit_elo and len(set(ns)) == 1
    if n_is_constant:
        lines.append(f"[n={ns[0]} for every point]")
    prev_date: datetime.date | None = None
    prev_bucket_start: str | None = None
    for pt in points:
        try:
            curr_date = datetime.date.fromisoformat(pt.bucket_start)
        except ValueError:
            continue
        gap_marker = _activity_gap_marker(prev_date, curr_date, prev_bucket_start, pt.bucket_start)
        if gap_marker:
            lines.append(gap_marker)
        pt_value = pt.value * series_scale
        if emit_elo and pt.actual_elo is not None:
            # Extend series rows with non_eg_elo= when available.
            if pt.non_endgame_elo is not None:
                lines.append(
                    f"{pt.bucket_start}: gap={pt_value:+.0f}, elo={pt.actual_elo},"
                    f" non_eg_elo={pt.non_endgame_elo} (n={pt.n})"
                )
            else:
                lines.append(
                    f"{pt.bucket_start}: gap={pt_value:+.0f}, elo={pt.actual_elo} (n={pt.n})"
                )
        elif n_is_constant:
            lines.append(f"{pt.bucket_start}: {pt_value:+.0f}")
        else:
            lines.append(f"{pt.bucket_start}: {pt_value:+.0f} (n={pt.n})")
        prev_date = curr_date
        prev_bucket_start = pt.bucket_start
    return lines


def _group_findings_by_metric_dim(
    members: list[SubsectionFinding],
) -> tuple[dict[tuple[str, str], dict[str, SubsectionFinding]], list[tuple[str, str]]]:
    """Group `members` by (metric, dim_key) -> {window: finding}.

    Preserves the order in which metric/dim pairs first appear so the LLM
    sees them in the original payload order (matches the old bullet
    ordering). Returns (groups, order) — `order` is the group-first-seen
    sequence `_render_subsection_block` iterates over.
    """
    groups: dict[tuple[str, str], dict[str, SubsectionFinding]] = {}
    order: list[tuple[str, str]] = []
    for f in members:
        key = (f.metric, _dim_key_for_finding(f))
        if key not in groups:
            groups[key] = {}
            order.append(key)
        groups[key][f.window] = f
    return groups, order


def _should_emit_series_block(
    candidate_finding: SubsectionFinding | None,
    candidate_series: list[TimePoint] | None,
    *,
    all_time_series_pairs: set[SeriesKey],
    live_series_metrics: set[tuple[str, str]],
    stale_markers: dict[int, str],
) -> bool:
    """Should this candidate's raw `[series ...]` block be emitted?

    False when there is nothing to render, when this is a `last_3mo` series
    superseded by an `all_time` series for the same series key, or
    when this is a stale combo shadowed by a live twin for the same
    (metric, subsection) pair. The stale gate is deliberately cross-combo: a stale
    combo keeps its [summary] with the stale marker but drops its raw series
    whenever another combo is live (the prompt allows it one historical clause).
    """
    if candidate_finding is None or not candidate_series:
        return False
    if (
        candidate_finding.window == "last_3mo"
        and _series_key(candidate_finding) in all_time_series_pairs
    ):
        return False
    if (
        id(candidate_finding) in stale_markers
        and (candidate_finding.metric, candidate_finding.subsection_id) in live_series_metrics
    ):
        return False
    return True


def _render_subsection_block(
    *,
    subsection_id: str,
    members: list[SubsectionFinding],
    stale_markers: dict[int, str],
    live_series_metrics: set[tuple[str, str]],
    last_3mo_pairs: set[SeriesKey],
    all_time_series_pairs: set[SeriesKey],
    all_time_cutoff: str,
    type_wdl_table: list[str] | None = None,
    per_tc_metric_percentiles: dict[str, "MetricPercentileRecord"] | None = None,
    cohort_anchors: "dict[str, RatingAnchorContext] | None" = None,
) -> list[str]:
    """Render one subsection: header + inline tags + [summary] blocks + [series] raw data.

    Findings are grouped by (metric, dim_key) so each pair produces exactly
    one [summary] block carrying both windows plus optional shift. Timeline
    findings also emit a `[series ...]` raw-data block below the summary.
    """
    lines: list[str] = []
    header = f"### Subsection: {subsection_id}"
    parent = next(
        (m.parent_subsection_id for m in members if m.parent_subsection_id),
        None,
    )
    if parent:
        header += f" (parent: {parent})"
    lines.append(header)

    # Per-TC Endgame Type subsections lead with their WDL table
    # (mirrors the UI tile's WDL bar + score bullet), then the per-TC recovery-
    # pattern / asymmetry hints scoped to this time control's findings, then the
    # per-class Conv/Recov/Score-Gap [summary] blocks below.
    type_tc = _TYPE_SUBSECTION_TO_TC.get(subsection_id)
    if type_tc is not None:
        if type_wdl_table:
            lines.extend(type_wdl_table)
        recovery_pattern = _recovery_pattern_tag(members, type_tc)
        if recovery_pattern:
            lines.append(recovery_pattern)
        lines.extend(_asymmetry_lines(members, type_tc))

    groups, order = _group_findings_by_metric_dim(members)

    recovery_note_emitted = False
    for key in order:
        metric, dim_key = key
        windows = groups[key]
        all_time = windows.get("all_time")
        last_3mo = windows.get("last_3mo")

        all_time_series = (
            _retained_series_for_summary(
                all_time,
                last_3mo_pairs=last_3mo_pairs,
                all_time_cutoff=all_time_cutoff,
            )
            if all_time is not None
            else None
        )
        last_3mo_series = (
            _retained_series_for_summary(
                last_3mo,
                last_3mo_pairs=last_3mo_pairs,
                all_time_cutoff=all_time_cutoff,
            )
            if last_3mo is not None
            else None
        )

        # In endgame_elo_timeline, lead each combo with the derived absolute
        # Endgame ELO summary (the chart's headline value), then the Non-Endgame
        # ELO summary, then the gap summary (which carries the zone
        # interpretation): THREE blocks per combo.
        if subsection_id == "endgame_elo_timeline" and metric == "endgame_elo_gap":
            lines.extend(
                _render_endgame_elo_summary_block(
                    dim_key=dim_key,
                    all_time_finding=all_time,
                    last_3mo_finding=last_3mo,
                    all_time_series=all_time_series,
                    last_3mo_series=last_3mo_series,
                    stale_markers=stale_markers,
                )
            )
            lines.extend(
                _render_non_endgame_elo_summary_block(
                    dim_key=dim_key,
                    all_time_finding=all_time,
                    last_3mo_finding=last_3mo,
                    all_time_series=all_time_series,
                    last_3mo_series=last_3mo_series,
                    stale_markers=stale_markers,
                )
            )
        lines.extend(
            _render_summary_block(
                metric,
                dim_key,
                all_time=all_time,
                last_3mo=last_3mo,
                all_time_series=all_time_series,
                last_3mo_series=last_3mo_series,
                stale_markers=stale_markers,
                per_tc_metric_percentiles=per_tc_metric_percentiles,
                cohort_anchors=cohort_anchors,
            )
        )
        if not recovery_note_emitted and metric == "recovery_save_pct" and type_tc is not None:
            lines.append(
                "  [typical bands above are per (Endgame Type × time control) from cohort "
                "data; weak here means at/below the type's population average for this time "
                "control, not absolute crisis]"
            )
            recovery_note_emitted = True

        # Raw [series ...] block below the summary. _should_emit_series_block carries
        # the series-emission gates: skip last_3mo series
        # when an all_time series exists for the same series key;
        # skip stale combos when a live combo exists.
        for candidate_finding, candidate_series in (
            (all_time, all_time_series),
            (last_3mo, last_3mo_series),
        ):
            if not _should_emit_series_block(
                candidate_finding,
                candidate_series,
                all_time_series_pairs=all_time_series_pairs,
                live_series_metrics=live_series_metrics,
                stale_markers=stale_markers,
            ):
                continue
            # _should_emit_series_block's first check (candidate_finding is None or not
            # candidate_series) means both are non-None here; ty cannot narrow
            # across the function-call boundary, so assert to keep the
            # explicit-type-safety guarantee CLAUDE.md requires.
            assert candidate_finding is not None
            assert candidate_series is not None
            lines.extend(_render_series_block(candidate_finding, candidate_series))

    lines.append("")
    return lines


def _visible_findings(raw_findings: list[SubsectionFinding]) -> list[SubsectionFinding]:
    """Drop NaN-valued findings, empty thin findings, and pawnless-class findings (the UI hides pawnless rows)."""
    return [
        f
        for f in raw_findings
        if not math.isnan(f.value)
        and not (f.sample_size == 0 and f.sample_quality == "thin")
        and not (f.dimension is not None and f.dimension.get("endgame_class") == "pawnless")
    ]


def _compute_all_time_series_pairs(
    visible: list[SubsectionFinding],
    *,
    last_3mo_pairs: set[SeriesKey],
    all_time_cutoff: str,
) -> set[SeriesKey]:
    """Register a series key ONLY when the all_time series
    still has retained points after thin-bucket, last_3mo-overlap and all-time-cap filtering.

    For short-history users whose entire history fits inside the 90-day
    last_3mo-overlap cutoff, the all_time series filters to empty — without this gate the
    empty pair would silently suppress the last_3mo [series] block (see `_should_emit_series_block`) so
    the LLM would see [summary] lines pointing at no series data.
    """
    all_time_series_pairs: set[SeriesKey] = set()
    for f in visible:
        if f.window != "all_time" or f.series is None:
            continue
        retained = _retained_series_for_summary(
            f,
            last_3mo_pairs=last_3mo_pairs,
            all_time_cutoff=all_time_cutoff,
        )
        if retained:
            all_time_series_pairs.add(_series_key(f))
    return all_time_series_pairs


def _compute_stale_markers_and_live_metrics(
    visible: list[SubsectionFinding], *, newest_date: datetime.date | None
) -> tuple[dict[int, str], int, set[tuple[str, str]]]:
    """Return (stale_markers, stale_count, live_series_metrics) for `visible`.

    `stale_markers` keys by `id(finding)` (matches the `stale_markers.get(id(f))`
    lookups downstream); `live_series_metrics` carries the (metric, subsection)
    pairs of every NON-stale series, so a stale combo can be shadowed by a
    live twin for the same pair (`_should_emit_series_block`'s stale-live-twin gate).
    """
    stale_markers: dict[int, str] = {}
    stale_count = 0
    live_series_metrics: set[tuple[str, str]] = set()
    for f in visible:
        if f.series is None:
            continue
        marker = _stale_marker(f.series, newest_date)
        if marker:
            stale_markers[id(f)] = marker
            stale_count += 1
        else:
            live_series_metrics.add((f.metric, f.subsection_id))
    return stale_markers, stale_count, live_series_metrics


def _render_layout_item(
    kind: str,
    block_id: str,
    *,
    chart_blocks: dict[str, list[str]],
    groups: dict[str, list[SubsectionFinding]],
    type_wdl_tables: dict[str, list[str]],
    stale_markers: dict[int, str],
    live_series_metrics: set[tuple[str, str]],
    last_3mo_pairs: set[SeriesKey],
    all_time_series_pairs: set[SeriesKey],
    all_time_cutoff: str,
    findings: EndgameTabFindings,
) -> list[str]:
    """Render one `_SECTION_LAYOUT` entry (a "chart" or "subsection" block).

    Extracted from `_assemble_user_prompt`'s per-section render loop so the
    `if not members and not wdl_table: if block_id == ...:` special case (the
    `endgame_elo_timeline` sparse-history header) does not nest 5 levels deep
    inside the caller's own `for section_id / for kind, block_id` loops.
    """
    if kind == "chart":
        return list(chart_blocks.get(block_id, []))
    # subsection
    members = groups.get(block_id) or []
    wdl_table = type_wdl_tables.get(block_id)
    if not members and not wdl_table:
        # Keep the `endgame_elo_timeline` header visible even when
        # every (platform, time_control) combo is sparse (< SPARSE_COMBO_FLOOR
        # weekly buckets). Without this the whole subsection vanishes for
        # short-history users, and the LLM has no signal that the Endgame
        # ELO chart exists.
        if block_id == "endgame_elo_timeline":
            return [
                "### Subsection: endgame_elo_timeline",
                (
                    f"[no qualifying combo — every (platform, time_control) "
                    f"combo has fewer than {SPARSE_COMBO_FLOOR} weekly buckets; "
                    "no Endgame ELO trajectory available yet]"
                ),
                "",
            ]
        return []
    # A per-TC Endgame Type subsection still renders its WDL
    # table even when the TC has no Conv/Recov/Score-Gap findings (e.g. an
    # all-parity TC), mirroring the UI card that always shows the WDL bars.
    return _render_subsection_block(
        subsection_id=block_id,
        members=members,
        stale_markers=stale_markers,
        live_series_metrics=live_series_metrics,
        last_3mo_pairs=last_3mo_pairs,
        all_time_series_pairs=all_time_series_pairs,
        all_time_cutoff=all_time_cutoff,
        type_wdl_table=wdl_table,
        per_tc_metric_percentiles=findings.per_tc_metric_percentiles,
        cohort_anchors=findings.cohort_anchors,
    )


def _assemble_user_prompt(findings: EndgameTabFindings) -> str:
    """Render EndgameTabFindings as structured text for the LLM.

    Layout: payload summary + player profile (no filter block),
    then one `## Section:` block per UI section with subsection and chart
    blocks interleaved in UI order. Each section maps 1:1 to one `section_id`
    in the LLM output. Empty sections (no qualifying blocks) are omitted.

    Filters applied (each stage is a helper at the point in the pipeline where
    it actually runs -- not all of them execute inline in this function's own
    body; see each helper's docstring for its real call site):
    - Visible findings: skip findings where value is NaN, sample_size=0 with
      thin quality, or the endgame class is pawnless. Applied here, via
      `_visible_findings`.
    - Thin buckets: drop series points with n < MIN_BUCKET_N. Applied inside
      `_retained_series_for_summary`.
    - Last-3-months overlap: for `all_time` series, drop points within last 90
      days if a matching `last_3mo` series exists for the same series key
      (metric, subsection, dimension). Applied inside
      `_retained_series_for_summary`, via `_drop_points_covered_by_last_3mo`.
    - Activity gaps: insert `[activity-gap] ...` markers when consecutive
      retained series points are > _ACTIVITY_GAP_DAYS apart. Applied inside
      `_render_series_block`, via `_activity_gap_marker`.
    - Series emission: skip the `last_3mo` Series block when an `all_time`
      Series for the same series key is emitted (the last_3mo scalar stays),
      and skip stale combos shadowed by a live twin. Applied inside
      `_render_subsection_block`, via `_should_emit_series_block`.
    - All-time cap: cap `all_time` series at the last _ALL_TIME_MAX_POINTS
      buckets. Applied inside `_retained_series_for_summary` and
      `_all_time_window_bounds`, via `_cap_all_time_points`.
    - Inline zone bounds: every finding bullet includes a
      `(typical LO to UP[, lower is better])` fragment next to the zone token.
    """
    overall_wdl_block = _format_overall_wdl_chart_block(findings)
    time_pressure_score_gap_block = _format_time_pressure_score_gap_chart_block(
        findings, findings.per_tc_metric_percentiles
    )
    chart_blocks: dict[str, list[str]] = {
        "overall_wdl": overall_wdl_block,
        "time_pressure_score_gap_by_time": time_pressure_score_gap_block,
    }

    # Pre-render the per-TC Endgame Type WDL tables (one per eligible TC, gated on
    # MIN_GAMES_PER_TC_CARD) keyed by subsection_id. The matching table leads each
    # `endgame_type_<tc>` subsection.
    type_wdl_tables = _build_type_wdl_tables(findings.type_categories_by_tc)

    # The per-class Score Gap is a real per-(class × TC) finding emitted by
    # insights_service._endgame_type_class_findings under the `endgame_type_<tc>`
    # subsections, so no in-renderer synthesis is needed.
    raw_findings: list[SubsectionFinding] = list(findings.findings)

    visible: list[SubsectionFinding] = _visible_findings(raw_findings)

    last_3mo_pairs: set[SeriesKey] = {_series_key(f) for f in visible if f.window == "last_3mo"}
    today = datetime.datetime.now(datetime.UTC).date()
    all_time_cutoff = (today - datetime.timedelta(days=_ALL_TIME_CUTOFF_DAYS)).isoformat()
    all_time_series_pairs = _compute_all_time_series_pairs(
        visible, last_3mo_pairs=last_3mo_pairs, all_time_cutoff=all_time_cutoff
    )

    newest_date = _newest_bucket_date(visible)
    stale_markers, stale_count, live_series_metrics = _compute_stale_markers_and_live_metrics(
        visible, newest_date=newest_date
    )
    # The asymmetry / recovery-pattern hints are computed per-TC inside
    # _render_subsection_block from each endgame_type_<tc> subsection's own
    # members (no global pre-computation).
    activity_gap_count = _count_activity_gaps(visible)
    all_time_window = _all_time_window_bounds(visible)

    # Group findings by subsection_id for per-block rendering.
    groups: dict[str, list[SubsectionFinding]] = {}
    for f in visible:
        groups.setdefault(f.subsection_id, []).append(f)

    lines: list[str] = []
    lines.extend(
        _payload_summary_lines(
            findings,
            newest_date=newest_date,
            stale_series_count=stale_count,
            activity_gap_count=activity_gap_count,
            all_time_window=all_time_window,
        )
    )
    lines.append("")
    lines.extend(_format_player_profile_block(findings.player_profile))
    # Rating-basis block teaches the LLM about the
    # Lichess-equivalent framing. Emitted once after the player profile so
    # the context is available before any percentile annotation is encountered.
    lines.extend(_format_rating_basis_block(findings.cohort_anchors))

    # Emit one `## Section:` block per UI section, with subsections and
    # charts interleaved in UI order. Skip a whole section when none of its
    # blocks produce content.
    for section_id, layout in _SECTION_LAYOUT:
        section_body: list[str] = []
        for kind, block_id in layout:
            section_body.extend(
                _render_layout_item(
                    kind,
                    block_id,
                    chart_blocks=chart_blocks,
                    groups=groups,
                    type_wdl_tables=type_wdl_tables,
                    stale_markers=stale_markers,
                    live_series_metrics=live_series_metrics,
                    last_3mo_pairs=last_3mo_pairs,
                    all_time_series_pairs=all_time_series_pairs,
                    all_time_cutoff=all_time_cutoff,
                    findings=findings,
                )
            )
        if not section_body:
            continue
        lines.append(f"## Section: {section_id}")
        lines.append("")
        lines.extend(section_body)

    return "\n".join(lines).rstrip() + "\n"


# -- Overview gate --


def _maybe_strip_overview(report: EndgameInsightsReport) -> EndgameInsightsReport:
    """If INSIGHTS_HIDE_OVERVIEW is True, return a copy with overview=''.

    Full overview is still present in the llm_logs.response_json source of truth;
    only the client-facing copy is stripped. Frontend treats '' as 'hide section'.
    """
    if not settings.INSIGHTS_HIDE_OVERVIEW:
        return report
    return report.model_copy(update={"overview": ""})


# -- Agent invocation wrapper: exception -> (None, marker), success -> (report, ...) --

_THOUGHTS_DETAIL_KEY = "thoughts_tokens"  # pydantic-ai Google adapter key (models/google.py:2065)


async def _run_agent(
    user_prompt: str,
    user_id: int,
    findings_hash: str,
) -> tuple[EndgameInsightsReport | None, int, int, int | None, int, str | None]:
    """Run the Agent; return (report, input_tokens, output_tokens, thinking_tokens, latency_ms, error_marker).

    On success: (report, in_toks, out_toks, thinking_toks_or_None, latency_ms, None).
    On failure: (None, 0, 0, None, latency_ms, "<marker>") and Sentry capture.

    thinking_tokens is None for providers that don't surface a separate thought
    count (Anthropic, OpenAI, test). For Google models with include_thoughts=True
    it comes from `usage.details["thoughts_tokens"]` (populated by pydantic-ai's
    Google adapter from usage_metadata.thoughts_token_count).

    Latency is measured ONLY around agent.run().
    """
    agent = get_insights_agent()
    try:
        # Start the timer inside the try so latency
        # measures only the agent.run() call itself, not the small gap
        # between timer-start and the await.
        t0 = time.monotonic()
        result = await agent.run(user_prompt)
    except UnexpectedModelBehavior as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "validation_failure_after_retries"
    except ModelAPIError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "provider_error"
    except Exception as exc:
        # Defensive catch-all for unexpected exceptions (e.g. httpx connect errors
        # not wrapped as ModelAPIError). Map to the provider_error marker (router -> 502).
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context(
            "insights",
            {
                "user_id": user_id,
                "findings_hash": findings_hash,
                "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
                "endpoint": _ENDPOINT,
            },
        )
        sentry_sdk.capture_exception(exc)
        return None, 0, 0, None, latency_ms, "provider_error"
    latency_ms = int((time.monotonic() - t0) * 1000)
    usage = result.usage
    thinking = usage.details.get(_THOUGHTS_DETAIL_KEY) or None
    return result.output, usage.input_tokens, usage.output_tokens, thinking, latency_ms, None


# -- Orchestration entry point --


def _cache_hit_response(row: LlmLog) -> EndgameInsightsResponse:
    report = EndgameInsightsReport.model_validate(row.response_json)
    return EndgameInsightsResponse(
        report=_maybe_strip_overview(report),
        status="cache_hit",
    )


async def _latest_report_row(
    session: AsyncSession, user_id: int, max_age: datetime.timedelta | None
) -> LlmLog | None:
    return await get_latest_successful_log_for_user(
        session,
        user_id=user_id,
        prompt_version=_PROMPT_VERSION,
        model=settings.PYDANTIC_AI_MODEL_INSIGHTS,
        opponent_strength=INSIGHTS_CACHE_OPPONENT_STRENGTH,
        max_age=max_age,
    )


async def get_cached_insights_response(
    session: AsyncSession, user_id: int
) -> EndgameInsightsResponse | None:
    """Regeneration cache rule for POST /insights/endgame (generate_insights).

    A cached row is reused iff it is a successful row for (user, prompt_version,
    model, constant opponent_strength) younger than INSIGHTS_CACHE_MAX_AGE
    (30 days) AND no completed import with games_imported > 0 landed after it
    was written. Otherwise the caller regenerates.
    """
    cached = await _latest_report_row(session, user_id, INSIGHTS_CACHE_MAX_AGE)
    if cached is None:
        return None
    # games_imported=0 imports are excluded by the helper, so no-op resyncs do
    # not invalidate the cache.
    last_import_at = await get_latest_completed_import_with_games_at(session, user_id)
    if last_import_at is not None and last_import_at > cached.created_at:
        return None
    return _cache_hit_response(cached)


async def get_latest_insights_response(
    session: AsyncSession, user_id: int
) -> EndgameInsightsResponse | None:
    """Display lookup for GET /insights/endgame/cached: the user's latest report.

    Never invalidated by imports or age, so None means the user has no report for
    the current (prompt_version, model) yet. The frontend auto-generates only on
    None (only the first report is auto-generated; later
    refreshes go through the "Update Insights" button, i.e. generate_insights).
    A prompt_version or model bump therefore auto-generates one new report.
    """
    latest = await _latest_report_row(session, user_id, None)
    return None if latest is None else _cache_hit_response(latest)


async def generate_insights(
    user_id: int,
    session: AsyncSession,
) -> EndgameInsightsResponse:
    """Tier-1 structural cache -> fresh LLM call.

    Cache key: (user_id, prompt_version, model) plus the
    constant INSIGHTS_CACHE_OPPONENT_STRENGTH; there is no filter input, so exactly one
    report is cached per user.
    Validity rule (see get_cached_insights_response): row younger than
    INSIGHTS_CACHE_MAX_AGE, AND row.created_at >= MAX(import_jobs.completed_at
    WHERE games_imported > 0) for this user. Reordered so compute_findings only
    runs on miss.
    Generations for the same user are serialized by a per-user advisory xact
    lock, so a concurrent duplicate request waits and returns the first one's
    report as cache_hit instead of paying for a second LLM call.

    Returns EndgameInsightsResponse with status in {fresh, cache_hit}.
    Raises InsightsProviderError (router -> 502) or InsightsValidationFailure
    (router -> 502) on the respective failure paths.

    All DB work runs on the caller-supplied session (sequential awaits).
    create_llm_log opens its OWN session so log rows
    persist even if the caller's session rolls back.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS

    # Bug fix (prod llm_logs 2026-10-11/12): users 1242, 1277, 1282, 1287 each got two
    # fresh reports 20-60s apart with an identical findings_hash and no import between.
    # A second POST (page reload/remount) arrived while the first was still inside
    # compute_findings + the LLM call, before its llm_logs row existed, so both missed
    # the cache. This per-user advisory xact lock serializes same-user generations:
    # create_llm_log commits the row on its OWN session before the first request
    # returns, and the lock is released when the first request's transaction ends
    # (get_async_session's commit after yield, or close/rollback on the exception
    # path). The waiter's cache lookup below then sees the committed row under READ
    # COMMITTED and returns cache_hit. Cost: a waiting request holds one pooled
    # connection, which it already held for the whole LLM call before this change.
    # Deliberately NOT taken in GET /cached (read-only, must never block).
    await acquire_insights_generation_lock(session, user_id)

    # Tier-1 STRUCTURAL cache lookup: cheap query on
    # (user_id, prompt_version, model, constant opponent_strength) + freshness checks
    # (younger than 30 days, no import with new games since).
    # Runs BEFORE compute_findings so cache hits skip the heavy DB pipeline.
    # Bug-fix note: the previous findings_hash-based lookup was unstable across
    # days because EndgameTabFindings includes time-relative fields (sliding
    # 3-month window stats and stale_months markers), so the hash drifted even
    # with a frozen game corpus. The hash also wasn't user-scoped, a latent
    # cross-user collision risk that the structural helper closes by filtering on
    # user_id directly.
    cached_response = await get_cached_insights_response(session, user_id)
    if cached_response is not None:
        return cached_response

    # Cache miss path: now we pay for compute_findings.
    findings = await compute_findings(session, user_id)

    # Fresh call.
    user_prompt = _assemble_user_prompt(findings)
    report, in_tokens, out_tokens, thinking_tokens, latency_ms, marker = await _run_agent(
        user_prompt, user_id, findings.findings_hash
    )
    # Server-side override of model_used and prompt_version.
    # Previously the system prompt asked the LLM to echo these back, which
    # produced fabricated strings ("gpt-4o" in Gemini outputs). Overriding
    # here — before create_llm_log — ensures both the response AND the
    # persisted log row store the authoritative values.
    if report is not None:
        report = report.model_copy(
            update={
                "model_used": model,
                "prompt_version": _PROMPT_VERSION,
            }
        )
    await create_llm_log(
        LlmLogCreate(
            user_id=user_id,
            endpoint=_ENDPOINT,
            model=model,
            prompt_version=_PROMPT_VERSION,
            findings_hash=findings.findings_hash,
            filter_context=LlmLogFilterContext(opponent_strength=INSIGHTS_CACHE_OPPONENT_STRENGTH),
            user_prompt=user_prompt,
            response_json=report.model_dump() if report is not None else None,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            thinking_tokens=thinking_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
            error=marker,
        )
    )
    if marker == "validation_failure_after_retries":
        raise InsightsValidationFailure(marker)
    if marker is not None or report is None:
        raise InsightsProviderError(marker or "provider_error")
    return EndgameInsightsResponse(
        report=_maybe_strip_overview(report),
        status="fresh",
    )
