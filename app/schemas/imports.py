"""Pydantic v2 schemas for the import API endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    platform: Literal["chess.com", "lichess"]
    username: str = Field(min_length=1, max_length=100)


class ImportStartedResponse(BaseModel):
    job_id: str
    status: str


class ImportStatusResponse(BaseModel):
    job_id: str
    platform: str
    username: str
    status: str
    games_fetched: int
    games_imported: int
    error: str | None = None
    other_importers: int = 0  # Count of other users importing from same platform (D-23)

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


class EvalCoverageResponse(BaseModel):
    """Response for GET /imports/eval-coverage."""

    pending_count: int
    total_count: int
    pct_complete: int  # 0-100, rounded


class ReadinessResponse(BaseModel):
    """Response for GET /imports/readiness.

    Two-tier readiness signal for gating eval-dependent features:

    Tier 1 (tier1=True): no active import job in-flight for this user.
        False while a PENDING or IN_PROGRESS import exists in-memory.
        NOTE: In-memory only — orphaned DB jobs after server restart are not
        detected here (RESEARCH Open Question 1 / A3). Out of scope.

    Tier 2 (tier2=True): tier1 AND pending evals == 0 AND
        (user has no games OR at least one user_benchmark_percentiles row exists).
        The "no games" escape prevents a below-floor user from being locked out
        forever when Stage B has nothing to compute (Pitfall 1).
        Row existence is the post-commit Stage-B signal — computed_at is
        refreshed on every upsert, so no Stage-B race with create_task.
    """

    tier1: bool
    tier2: bool
    pending_count: int
    total_count: int
