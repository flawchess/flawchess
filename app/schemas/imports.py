"""Pydantic v2 schemas for the import API endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.core.platform_usernames import extract_platform_username
from app.schemas.normalization import Color

# The five exhaustive values import_jobs.status can
# take. "queued" is in-memory only (import_service.JobStatus.QUEUED) -- never
# written to the DB row -- but flows through the same response fields as the
# other four, so it belongs in the same wire type. The only writers of
# import_jobs.status are the create path ("pending"), the first batch flush
# ("in_progress"), completion ("completed"), and the two failure paths plus
# the reaper ("failed").
ImportJobStatusLiteral = Literal["pending", "queued", "in_progress", "completed", "failed"]


class ImportRequest(BaseModel):
    platform: Literal["chess.com", "lichess"]
    username: str = Field(min_length=1, max_length=100)

    @field_validator("username", mode="before")
    @classmethod
    def _extract_username(cls, value: Any, info: ValidationInfo) -> Any:
        # mode="before" is load-bearing: it must run ahead of
        # max_length=100 so a long pasted profile URL is shortened to the bare
        # username instead of rejected. `platform` is declared before
        # `username`, so it is already validated and present here -- except
        # when `platform` itself failed validation, in which case we fall
        # back to accepting either platform's URL form.
        platform = info.data.get("platform")
        return extract_platform_username(value, platform)


class ImportStartedResponse(BaseModel):
    job_id: str
    status: ImportJobStatusLiteral


class ImportStatusResponse(BaseModel):
    job_id: str
    platform: str
    username: str
    status: ImportJobStatusLiteral
    games_fetched: int
    games_imported: int
    error: str | None = None
    other_importers: int = 0  # Count of other users importing from same platform

    @classmethod
    def from_dict(cls, data: dict) -> "ImportStatusResponse":
        return cls(
            job_id=data["job_id"],
            platform=data["platform"],
            username=data["username"],
            status=data["status"],
            games_fetched=data.get("games_fetched", 0),
            games_imported=data.get("games_imported", 0),
            error=data.get("error") or data.get("error_message"),
        )


class DeleteGamesResponse(BaseModel):
    """Response for DELETE /imports/games."""

    deleted_count: int


class EnqueueTier1Response(BaseModel):
    """Response for POST /imports/eval/tier1/{game_id} (and re-exported to admin).

    Shared by the internal/admin trigger and the user-facing endpoint. Lives
    here (not admin.py) so imports.py owns the full eval-enqueue schema set.
    """

    status: Literal["enqueued", "skipped_guest", "already_queued"]
    game_id: int


class EvalCoverageResponse(BaseModel):
    """Response for GET /imports/eval-coverage.

    pending_count, total_count and pct_complete feed the
    Endgames/Openings/GlobalStats readiness gates; analyzed_count is the number
    of fully analyzed games. There is no in-flight count: tier-3 derived picks
    have no eval_jobs rows, so such a count would be structurally blind to the
    dominant backlog drain and never an honest signal.
    """

    pending_count: int
    total_count: int
    pct_complete: int  # 0-100, rounded
    analyzed_count: int  # full_evals_completed_at IS NOT NULL (same column the Library cards use)


# Bounds the DoS surface of a client-POSTed pasted PGN —
# mirrors MAX_BOT_PGN_LENGTH's convention (app/schemas/bots.py). Rejected at
# schema validation, before any chess.pgn parse.
MAX_PASTED_PGN_LENGTH = 100_000


class SavePastedGameRequest(BaseModel):
    """Request body for POST /imports/paste.

    No owner field of any kind — the principal is server-derived from
    current_active_user (ASVS V4); a body carrying a foreign
    user_id-shaped field is simply ignored by the schema.
    """

    pgn: str = Field(min_length=1, max_length=MAX_PASTED_PGN_LENGTH)
    user_color: Color


class SavePastedGameResponse(BaseModel):
    """Response for POST /imports/paste.

    eval_status distinguishes four post-save outcomes: "enqueued" (a fresh
    tier-1 job was inserted), "already_queued" (an active job already
    existed, no-op), "already_analyzed" (the reused row was already
    fully analyzed, no re-enqueue), and "enqueue_failed" (the game row
    IS durably saved, but the post-commit enqueue_tier1_game call raised).
    "enqueue_failed" is still a 200 — the save genuinely succeeded.
    """

    game_id: int
    created: bool
    eval_status: Literal["enqueued", "already_queued", "already_analyzed", "enqueue_failed"]


class ReadinessResponse(BaseModel):
    """Response for GET /imports/readiness.

    Two-tier readiness signal for gating eval-dependent features:

    Tier 1 (tier1=True): no active import job in-flight for this user.
        False while a PENDING or IN_PROGRESS import exists in-memory.
        NOTE: In-memory only — orphaned DB jobs after server restart are not
        detected here. Out of scope.

    Tier 2 (tier2=True): tier1 AND pending evals == 0 AND not mid-Stage-B AND
        (no games OR a percentile row exists OR the settled-empty or
        below-anchor-floor escape applies). See get_readiness.
        The escapes prevent a below-floor user from being locked out
        forever when Stage B has nothing to compute.
        Row existence is the post-commit Stage-B signal — computed_at is
        refreshed on every upsert, so no Stage-B race with create_task.
    """

    tier1: bool
    tier2: bool
    pending_count: int
    total_count: int
